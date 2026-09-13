"""Engine entrypoint: wire config, prompt, agent, and loop; supervise them."""
from __future__ import annotations

import argparse
import asyncio
import json
import signal
import subprocess
import sys
from pathlib import Path

import dataclasses
import urllib.error
import urllib.request

from engine import display, health, local_context, prompt, speaker, state, tts_trigger
from engine.agent import DMAgent
from engine.config import Config, load_config
from engine.lang import build_glossary
from engine.log import log_event
from engine.rules.index import load_index

REPO_ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_PATH = Path(__file__).resolve().parent / "lang" / "bg_glossary.json"
STARTUP_BANNER = "DM е онлайн. Изпратете действията си от телефона."


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dnd-engine", description="Local D&D DM engine")
    p.add_argument("--campaign", default=None, help="campaign folder name")
    # Default None, not "bg": an unconditional assignment would silently
    # override a saved `language` preference in engine_config.json on every
    # run. Only an explicitly passed --lang wins over the config file.
    p.add_argument("--lang", default=None, choices=["bg", "en"])
    p.add_argument("--backend", default=None, choices=["claude", "local"],
                   help="claude (Claude Agent SDK) or local (Ollama)")
    p.add_argument("--model", default=None,
                   help="override turn model id (Ollama model tag when --backend local)")
    p.add_argument("--max-turns", type=int, default=None, help="stop after N turns")
    p.add_argument("--check", action="store_true", help="run preflight checks and exit")
    return p


def resolve_campaign(cfg: Config, requested: str | None) -> str:
    name = requested or cfg.campaign or state.active_campaign()
    if not name:
        print("No campaign selected. Load one with /dm:dnd load, or pass --campaign.",
              file=sys.stderr)
        raise SystemExit(2)
    return name


def ollama_reachable(host: str) -> bool:
    """True if the local model backend answers.

    A named function rather than an inline try/except so preflight's own
    tests can stub it: without that, whether the suite passes depends on
    whether ollama happens to be running on the machine at the time.
    """
    try:
        req = urllib.request.Request(f"{host}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=5):
            return True
    except (urllib.error.URLError, OSError):
        return False


def preflight(cfg: Config, campaign: str) -> list[str]:
    """Boot sequence, per Project Instructions v4.1: refuse to start without
    character sheets, a campaign, a display, and a usable rules index."""
    problems = []
    camp_dir = state.campaign_dir(campaign)

    if not camp_dir.exists():
        problems.append(f"campaign folder missing: {camp_dir}")
    elif not state.party_names(campaign):
        problems.append(
            f"no character sheet in {camp_dir / 'characters'} — "
            "add one .md per character before starting"
        )

    if not display.is_running(cfg.display_port):
        problems.append(f"display not reachable on port {cfg.display_port}")

    if cfg.language == "bg" and not GLOSSARY_PATH.exists():
        problems.append(f"glossary missing: {GLOSSARY_PATH}")

    if load_index().get("count", 0) == 0:
        problems.append(
            "rules index is empty — run: .venv/bin/python -m engine.rules.index"
        )

    if cfg.backend == "local" and not ollama_reachable(cfg.local_host):
        problems.append(
            f"local backend selected but Ollama isn't reachable at "
            f"{cfg.local_host} — start the game with ./scripts/start_engine.sh "
            f"(it starts ollama itself), or run `ollama serve` and "
            f"`ollama pull {cfg.local_model}` by hand"
        )

    return problems


def ensure_ruleset(cfg: Config, campaign: str) -> None:
    """Migrate a legacy campaign to the configured ruleset, then pin the flag.

    The ruleset comes from cfg (validated to the supported set at load time),
    not a literal, so state.md and the prompt header can never disagree.

    The migration subprocess is wrapped the way turn_loop.run_autosave is: a
    hung or unlaunchable migration must not take the engine down on boot, and
    its exit code and stderr are logged rather than discarded.
    """
    script = REPO_ROOT / "skills" / "dnd" / "scripts" / "migrate_ruleset.py"
    if script.exists():
        try:
            proc = subprocess.run(
                [sys.executable, str(script), campaign, "--ruleset", cfg.ruleset, "--yes"],
                capture_output=True, text=True, timeout=60,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            log_event("ruleset_migration_failed", campaign=campaign, error=str(exc))
        else:
            if proc.returncode == 0:
                log_event("ruleset_migrated", campaign=campaign, ruleset=cfg.ruleset)
            else:
                log_event("ruleset_migration_failed", campaign=campaign,
                          returncode=proc.returncode, stderr=(proc.stderr or "")[:500])
    state.set_session_flag(campaign, "ruleset", cfg.ruleset)
    log_event("ruleset_pinned", campaign=campaign, ruleset=cfg.ruleset)


def push_quests(campaign: str) -> None:
    """Send the campaign's quest list to the display's tracker.

    state.md has always carried a description for every quest; the display
    only ever received names and statuses, which is why the sidebar's quest
    entries had nothing to open. Pushed once at startup — quest text changes
    at the pace of the story, not the turn.

    Best-effort, like every other display call: a failure here costs the
    sidebar its quest text, never the session.
    """
    try:
        entries = local_context.quests(campaign)
    except Exception as exc:  # noqa: BLE001 -- never block startup on a parse
        log_event("quest_push_failed", error=str(exc))
        return
    if not entries:
        return
    display.push(quests=json.dumps(entries, ensure_ascii=False))


async def serve(cfg: Config, campaign: str, max_turns: int | None = None) -> int:
    from engine.turn_loop import run_loop

    glossary = build_glossary(out_path=GLOSSARY_PATH) if cfg.language == "bg" else {}

    if cfg.backend == "local":
        from engine.local_agent import LocalDMAgent
        from engine.local_prompt import build_local_system_prompt, build_local_turn_prompt

        system_prompt = build_local_system_prompt(cfg, glossary)
        on_narration = on_turn_end = None
        if cfg.local_stream:
            # Push narration to the display as it streams rather than once the
            # whole turn is done: measured, a turn runs ~35-45s and the player
            # previously saw nothing at all until the end of it. With this,
            # first text lands in ~9s.
            #
            # The same chunks are read aloud in Bulgarian by the display
            # itself (POST /speak), so the DM starts *speaking* the scene at
            # that same ~9s mark instead of after the whole turn. Silently
            # inert when the display isn't running.
            if cfg.local_speak:
                speaker_url = speaker.resolve_url(cfg.local_speaker_url, cfg.display_port)

                def on_narration(chunk: str, _url=speaker_url) -> None:
                    display.send_narration(chunk)
                    speaker.speak(chunk, _url)

                if speaker.is_available(speaker_url):
                    log_event("speaker_connected", url=speaker_url)
                else:
                    print(f"→ Дисплеят не отговаря на {speaker_url} — "
                          f"играта върви без глас (пусни ./scripts/start_engine.sh)",
                          file=sys.stderr)
            else:
                on_narration = display.send_narration
            if cfg.tts_prewarm and not cfg.local_speak:
                # Streaming changes what the display's TTS cache keys are --
                # one per pushed block instead of one for the whole turn -- so
                # turn_loop's whole-text prewarm would now warm a key nothing
                # asks for. Warm the real blocks instead, serially and only
                # once the turn is done (local TTS shares the GPU with the
                # model). turn_loop's own prewarm is disabled just below.
                def on_turn_end(blocks, _port=cfg.display_port):
                    tts_trigger.queue_prewarm(blocks, _port)
            # Pre-warming is pointless -- and actively harmful on an 8GB
            # machine -- when the audio connector is already speaking every
            # block: it would synthesise the same Bulgarian text a second
            # time, on the same GPU the model is using. The display's own
            # speaker button still works, synthesising on demand.
            cfg = dataclasses.replace(cfg, tts_prewarm=False)
        agent = LocalDMAgent(
            cfg, system_prompt, campaign,
            host=cfg.local_host, model=cfg.local_model, num_ctx=cfg.local_num_ctx,
            on_narration=on_narration, on_turn_end=on_turn_end,
        )
        build_turn_prompt = build_local_turn_prompt
        model_label = cfg.local_model
    else:
        system_prompt = prompt.build_system_prompt(cfg, glossary)
        agent = DMAgent(cfg, system_prompt)
        build_turn_prompt = prompt.build_turn_prompt
        model_label = cfg.turn_model

    # The dice protocol's first rule is non-negotiable for this app.
    state.set_session_flag(campaign, "roll_mode", "players")
    ensure_ruleset(cfg, campaign)

    await agent.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    display.send_system(STARTUP_BANNER)
    push_quests(campaign)
    log_event("engine_start", campaign=campaign, backend=cfg.backend, model=model_label, lang=cfg.language)

    try:
        return await run_loop(
            cfg, agent, campaign, stop_event,
            max_turns=max_turns, build_turn_prompt=build_turn_prompt,
        )
    finally:
        await agent.stop()
        health.heartbeat("paused")
        log_event("engine_stop", campaign=campaign)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    if args.lang:
        cfg.language = args.lang
    if args.backend:
        cfg.backend = args.backend
    if args.model:
        if cfg.backend == "local":
            cfg.local_model = args.model
        else:
            cfg.turn_model = args.model

    campaign = resolve_campaign(cfg, args.campaign)
    problems = preflight(cfg, campaign)

    if args.check:
        for problem in problems:
            print("PROBLEM:", problem)
        print("OK" if not problems else "NOT READY")
        return 0 if not problems else 1

    if problems:
        for problem in problems:
            print("PROBLEM:", problem, file=sys.stderr)
        return 1

    turns = asyncio.run(serve(cfg, campaign, max_turns=args.max_turns))
    print(f"Turns completed: {turns}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
