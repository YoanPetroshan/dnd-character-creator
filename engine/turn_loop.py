"""The deterministic turn cycle. This is what the model can no longer forget."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from engine import display, guards, health, prompt, state, tts_trigger
from engine.agent import is_usage_limit_error
from engine.config import Config
from engine.log import log_event, read_events

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTOSAVE_SCRIPT = REPO_ROOT / "skills" / "dnd" / "scripts" / "autosave_checkpoint.py"

TURN_FAILED_MESSAGE = (
    "DM се препъна за момент. Повтори последното си действие."
)
USAGE_LIMIT_MESSAGE = (
    "Достигнат е лимитът на абонамента. Играта е на пауза и ще продължи "
    "автоматично. Не затваряйте дисплея."
)
USAGE_LIMIT_PAUSE_S = 300
WAIT_FOR_ACTIONS_ERROR_BACKOFF_S = 0.3

# Strong references to in-flight TTS pre-warm tasks.
#
# asyncio only holds a WEAK reference to a running task. A task created and
# never awaited — exactly what a fire-and-forget pre-warm is — can therefore be
# garbage-collected mid-flight, cancelling the synthesis at an arbitrary point
# for no visible reason and with no error. Holding the task here until its own
# done-callback removes it is the documented fix, not defensive padding.
_PREWARM_TASKS: set[asyncio.Task] = set()


@dataclass
class TurnOutcome:
    ok: bool = False
    text: str = ""
    fallback_used: bool = False
    language_ok: bool = True
    autorolls: list[str] = field(default_factory=list)
    error: str | None = None


async def wait_for_actions(poll_interval: float = 0.3, stop_event: asyncio.Event | None = None) -> str:
    """Block until a player submits from the phone. No artificial timeout."""
    # heartbeat() shells out to push_stats.py with a 30s timeout — a slow or
    # hung display must not stall the event loop, so every blocking display /
    # subprocess call in this module goes through asyncio.to_thread.
    await asyncio.to_thread(health.heartbeat, "waiting")
    while True:
        if stop_event is not None and stop_event.is_set():
            return ""
        actions = state.take_input_queue()
        if actions:
            return actions
        await asyncio.sleep(poll_interval)


def run_autosave(campaign: str) -> None:
    if not AUTOSAVE_SCRIPT.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(AUTOSAVE_SCRIPT)],
            capture_output=True, text=True, timeout=60,
        )
        log_event("autosave", campaign=campaign)
    except (subprocess.TimeoutExpired, OSError) as exc:
        log_event("autosave_failed", error=str(exc))


def requested_rolls_since(since_ts: float, limit: int = 500) -> set[str]:
    """Characters whose roll the engine itself legitimately requested.

    `engine.dice`'s CLI runs in the agent's own Bash subprocess, so the only
    channel back to this process is the shared JSONL event log: a successful
    request_pc_roll writes `pc_roll` with the character name. Anything logged
    at or after the turn's start belongs to this turn, so the autoroll guard
    must not flag those names.
    """
    names: set[str] = set()
    for event in read_events(limit=limit):
        if event.get("event") != "pc_roll":
            continue
        ts = event.get("ts")
        if not isinstance(ts, (int, float)) or ts < since_ts:
            continue
        character = event.get("character")
        if isinstance(character, str) and character.strip():
            names.add(character.strip())
    return names


async def run_once(
    cfg: Config,
    agent,
    campaign: str,
    actions: str,
    turn_index: int,
    stop_event: asyncio.Event | None = None,
    build_turn_prompt=prompt.build_turn_prompt,
) -> TurnOutcome:
    turn_started = time.time()
    log_event("turn_start", turn=turn_index, campaign=campaign, actions=actions[:200])
    await asyncio.to_thread(health.heartbeat, "thinking")
    await asyncio.to_thread(display.notify_thinking, cfg.display_port)

    before = state.text_log_fingerprint()
    turn_prompt = build_turn_prompt(campaign, actions)
    result = await agent.run_turn(turn_prompt)

    if not result.ok:
        if is_usage_limit_error(result.error or ""):
            # pause_for_usage_limit does a blocking time.sleep() internally.
            # Calling it directly here would freeze the whole event loop for
            # the pause duration (5 minutes by default), so we offload it to
            # a worker thread instead of awaiting it in-line. The offload also
            # puts the pause out of reach of the signal handlers, which only
            # set stop_event — hence the stop predicate, which lets the pause
            # cut itself short instead of ignoring Ctrl-C for five minutes.
            await asyncio.to_thread(
                health.pause_for_usage_limit, USAGE_LIMIT_PAUSE_S, USAGE_LIMIT_MESSAGE,
                stop_event.is_set if stop_event is not None else None,
            )
        else:
            await asyncio.to_thread(display.send_system, TURN_FAILED_MESSAGE)
        log_event("turn_failed", turn=turn_index, error=result.error)
        return TurnOutcome(ok=False, error=result.error)

    after = state.text_log_fingerprint()
    # ensure_display_pushed may shell out to send.py; keep it off the loop.
    fallback = await asyncio.to_thread(
        guards.ensure_display_pushed, before, after, result.text
    )
    # Pre-warm the display's TTS cache with this turn's narration. Launched
    # un-awaited so the turn does not pay for synthesis: the player typically
    # spends several seconds reading before reaching for the speaker button,
    # and that gap is exactly the budget this call spends. prewarm_tts itself
    # never raises, and the blocking HTTP call goes through to_thread so a slow
    # or hung TTS backend cannot stall the event loop.
    if cfg.tts_prewarm:
        _prewarm = asyncio.create_task(
            asyncio.to_thread(tts_trigger.prewarm_tts, result.text, cfg.display_port)
        )
        _PREWARM_TASKS.add(_prewarm)
        _prewarm.add_done_callback(_PREWARM_TASKS.discard)

    language_ok = guards.check_language(result.text, expect=cfg.language)
    requested = requested_rolls_since(turn_started)
    autorolls = guards.find_pc_autorolls(
        result.text, state.party_names(campaign), requested=requested
    )

    log_event(
        "turn_end", turn=turn_index, ok=True, fallback=fallback,
        language_ok=language_ok, autorolls=autorolls,
        requested=sorted(requested),
    )
    return TurnOutcome(
        ok=True, text=result.text, fallback_used=fallback,
        language_ok=language_ok, autorolls=autorolls,
    )


async def run_loop(
    cfg: Config,
    agent,
    campaign: str,
    stop_event: asyncio.Event,
    max_turns: int | None = None,
    build_turn_prompt=prompt.build_turn_prompt,
) -> int:
    turns = 0
    while not stop_event.is_set():
        if max_turns is not None and turns >= max_turns:
            break

        try:
            actions = await wait_for_actions(stop_event=stop_event)
        except Exception as exc:  # noqa: BLE001 — a corrupt queue must not kill the loop
            # e.g. non-UTF-8 bytes written to .runtime/.input_queue raise
            # UnicodeDecodeError out of state.take_input_queue(), which
            # wait_for_actions does not itself guard against. This must not
            # count as a completed turn — just log it and keep waiting.
            #
            # The failure can be permanent (the bad file is never cleaned up,
            # since take_input_queue's read fails before it reaches its own
            # unlink()), and it happens synchronously — before wait_for_actions
            # ever reaches its own internal `await asyncio.sleep(...)`. A bare
            # `continue` here would therefore never yield control back to the
            # event loop at all, turning a permanent failure into a
            # synchronous, CPU-bound, unkillable spin. The explicit await
            # below is a genuine yield point that degrades a persistent
            # failure to a slow poll instead.
            log_event("wait_for_actions_crashed", error=f"{type(exc).__name__}: {exc}")
            await asyncio.sleep(WAIT_FOR_ACTIONS_ERROR_BACKOFF_S)
            continue
        if not actions:
            continue

        turns += 1
        try:
            await run_once(
                cfg, agent, campaign, actions, turns,
                stop_event=stop_event, build_turn_prompt=build_turn_prompt,
            )
        except Exception as exc:  # noqa: BLE001 — the loop must never die
            log_event("turn_crashed", turn=turns, error=f"{type(exc).__name__}: {exc}")
            await asyncio.to_thread(display.send_system, TURN_FAILED_MESSAGE)

        if cfg.autosave_every and turns % cfg.autosave_every == 0:
            try:
                # 60s subprocess — never on the event loop.
                await asyncio.to_thread(run_autosave, campaign)
            except Exception as exc:  # noqa: BLE001 — a failed save must not block the game
                log_event("autosave_crashed", turn=turns, error=f"{type(exc).__name__}: {exc}")

    await asyncio.to_thread(health.heartbeat, "waiting")
    return turns
