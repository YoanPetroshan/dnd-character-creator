import asyncio
import json
import time

import pytest

from engine.agent import TurnResult
from engine.config import Config
from engine import dice, turn_loop


class StubAgent:
    def __init__(self, results):
        self.results = list(results)
        self.prompts = []

    async def run_turn(self, prompt):
        self.prompts.append(prompt)
        return self.results.pop(0)


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "state.md").write_text("## Live State Flags\n- Scene: crypt\n")
    (camp / "characters" / "falin.md").write_text("# Falin\n")
    (tmp_path / ".runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def quiet(monkeypatch):
    monkeypatch.setattr(turn_loop.display, "send_narration", lambda t: True)
    monkeypatch.setattr(turn_loop.display, "send_system", lambda t: True)
    monkeypatch.setattr(turn_loop.display, "push", lambda **kw: True)
    monkeypatch.setattr(turn_loop.health, "heartbeat", lambda s: None)
    # notify_thinking is a real network call by default (localhost:{port}) —
    # stub it here so every other test doesn't attempt one.
    monkeypatch.setattr(turn_loop.display, "notify_thinking", lambda port: True)
    # prewarm_tts is likewise a real network call (POST /tts on the display
    # port) fired for every successful TurnResult — stub it here for the same
    # reason, so tests that don't specifically exercise the trigger don't hit
    # a live display (or a real TTS backend) on every run.
    monkeypatch.setattr(turn_loop.tts_trigger, "prewarm_tts", lambda *a, **k: True)


def test_run_once_success_no_fallback(root, quiet, monkeypatch):
    # The newest entries changed → the model pushed to the display itself.
    marks = iter([(7, '[{"text": "старо"}]'), (9, '[{"text": "ново"}]')])
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: next(marks))
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "[Falin]: вървя", 1))
    assert outcome.ok is True
    assert outcome.fallback_used is False
    assert outcome.language_ok is True


def test_run_once_makes_no_real_network_call_for_tts_prewarm(root, quiet, monkeypatch):
    """The `quiet` fixture stubs tts_trigger.prewarm_tts at the module level
    -- this test relies on THAT stub alone (it adds no override of its own)
    and additionally asserts urllib.request.urlopen (what prewarm_tts uses
    under the hood to reach the display's /tts endpoint) is never invoked.
    Before the quiet fixture stubbed prewarm_tts, this exact scenario fired
    a real POST /tts at whatever was listening on cfg.display_port -- the
    live display in a default (non---lan) setup, since _token_ok() returns
    True unconditionally when _lan_token is None."""
    marks = iter([(7, '[{"text": "старо"}]'), (9, '[{"text": "ново"}]')])
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: next(marks))

    def _fail_if_called(*a, **k):
        raise AssertionError("urllib.request.urlopen must not be called -- prewarm_tts should be stubbed")

    monkeypatch.setattr(turn_loop.tts_trigger.urllib.request, "urlopen", _fail_if_called)

    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "[Falin]: вървя", 1))
    assert outcome.ok is True


def test_run_once_notifies_thinking_indicator(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    calls = []
    monkeypatch.setattr(turn_loop.display, "notify_thinking", lambda port: calls.append(port) or True)
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    cfg = Config()
    outcome = asyncio.run(turn_loop.run_once(cfg, agent, "demo", "[Falin]: вървя", 1))
    assert outcome.ok is True
    assert calls == [cfg.display_port]


def test_run_once_fires_display_fallback(root, quiet, monkeypatch):
    marks = iter([(7, '[{"text": "старо"}]'), (7, '[{"text": "старо"}]')])
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: next(marks))
    pushed = []
    monkeypatch.setattr(turn_loop.display, "send_narration", lambda t: pushed.append(t) or True)
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "[Falin]: вървя", 1))
    assert outcome.fallback_used is True
    assert pushed


def test_run_once_flags_english_narration(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    agent = StubAgent([TurnResult(
        text="The darkness gathers over the crypt and the air turns cold and still.",
        ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))
    assert outcome.language_ok is False


def test_run_once_reports_agent_failure_and_tells_players(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    sent = []
    monkeypatch.setattr(turn_loop.display, "send_system", lambda t: sent.append(t) or True)
    agent = StubAgent([TurnResult(ok=False, error="timeout after 180s")])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))
    assert outcome.ok is False
    assert sent, "players must be told the turn failed"


def test_run_once_pauses_on_usage_limit(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    paused = []
    monkeypatch.setattr(turn_loop.health, "pause_for_usage_limit",
                        lambda s, m, should_stop=None: paused.append((s, m)))
    agent = StubAgent([TurnResult(ok=False, error="Claude usage limit reached")])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))
    assert outcome.ok is False
    assert paused, "hitting the subscription limit must pause, not just report"


def test_run_once_offloads_usage_limit_pause_from_event_loop(root, quiet, monkeypatch):
    """health.pause_for_usage_limit does a blocking time.sleep() internally. If
    run_once called it directly (synchronously) from a coroutine, that sleep
    would freeze the whole event loop for its duration, and a concurrent
    coroutine scheduled via asyncio.gather could not make any progress until
    the pause finished — the two would run back-to-back instead of overlapping.

    This test proves the offload (e.g. via asyncio.to_thread) actually happens
    by running the pause alongside a dummy coroutine that ticks on its own
    asyncio.sleep, and observing — from inside the blocking call itself —
    whether the ticker advanced WHILE the pause was in progress. A synchronous
    call site freezes the loop, so the tick count cannot move between the
    pause's entry and exit; an offloaded one lets it climb. Merely asserting
    pause_for_usage_limit was called with the right args would NOT catch the
    regression, since a synchronous call satisfies that too.

    Deliberately NOT a wall-clock threshold: elapsed-time assertions of the
    form "total < serialized/2" silently assume time.sleep(0.1) takes 0.1s,
    which stops being true on a loaded machine (measured: a 0.1s sleep in a
    worker thread taking 0.2s while another process saturated a core), making
    the test fail even though the offload was working correctly. Observing the
    interleaving directly is both load-independent and a more direct statement
    of the property under test.
    """
    import time

    pause_seconds = 0.1
    tick_interval = 0.02
    tick_count = 5  # 5 * 0.02s = 0.1s of ticking

    ticks = []
    observed = {}

    def fake_pause(seconds, message, should_stop=None):
        observed["ticks_at_entry"] = len(ticks)
        time.sleep(pause_seconds)
        observed["ticks_at_exit"] = len(ticks)

    monkeypatch.setattr(turn_loop.health, "pause_for_usage_limit", fake_pause)
    agent = StubAgent([TurnResult(ok=False, error="Claude usage limit reached")])

    async def dummy_ticker():
        for i in range(tick_count):
            await asyncio.sleep(tick_interval)
            ticks.append(i)

    async def scenario():
        outcome, _ = await asyncio.gather(
            turn_loop.run_once(Config(), agent, "demo", "x", 1),
            dummy_ticker(),
        )
        return outcome

    outcome = asyncio.run(scenario())
    assert outcome.ok is False
    assert len(ticks) == tick_count

    progressed = observed["ticks_at_exit"] - observed["ticks_at_entry"]
    assert progressed > 0, (
        "the ticker made no progress while pause_for_usage_limit was running "
        "— the pause is blocking the event loop instead of running via "
        "asyncio.to_thread"
    )


def test_run_once_offloads_the_failure_notice_from_event_loop(root, quiet, monkeypatch):
    """Same shape as the usage-limit offload test, for the other blocking
    display call on the failure path. display.send_system shells out to
    send.py with a 30s timeout; called inline from a coroutine, a slow or hung
    display stalls the whole loop for up to that long, every turn.

    Asserts on the interleaving observed from inside the blocking call rather
    than on total wall time — see the usage-limit test's docstring for why a
    wall-clock threshold is the wrong instrument here.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))

    send_seconds = 0.1
    tick_interval = 0.02
    tick_count = 5

    ticks = []
    observed = {}

    def slow_send_system(text):
        observed["ticks_at_entry"] = len(ticks)
        time.sleep(send_seconds)
        observed["ticks_at_exit"] = len(ticks)
        return True

    monkeypatch.setattr(turn_loop.display, "send_system", slow_send_system)
    agent = StubAgent([TurnResult(ok=False, error="timeout after 180s")])

    async def dummy_ticker():
        for i in range(tick_count):
            await asyncio.sleep(tick_interval)
            ticks.append(i)

    async def scenario():
        outcome, _ = await asyncio.gather(
            turn_loop.run_once(Config(), agent, "demo", "x", 1),
            dummy_ticker(),
        )
        return outcome

    outcome = asyncio.run(scenario())
    assert outcome.ok is False
    assert len(ticks) == tick_count

    progressed = observed["ticks_at_exit"] - observed["ticks_at_entry"]
    assert progressed > 0, (
        "the ticker made no progress while display.send_system was running "
        "— it is blocking the event loop instead of running via to_thread"
    )


def test_run_once_passes_the_stop_event_into_the_usage_limit_pause(root, quiet, monkeypatch):
    """The signal handlers only set stop_event, and the pause runs in a worker
    thread where a signal cannot reach it — so the pause needs the flag itself
    to be able to cut short."""
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    captured = {}

    def fake_pause(seconds, message, should_stop=None, **kw):
        captured["should_stop"] = should_stop

    monkeypatch.setattr(turn_loop.health, "pause_for_usage_limit", fake_pause)
    stop = asyncio.Event()
    agent = StubAgent([TurnResult(ok=False, error="Claude usage limit reached")])
    asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1, stop_event=stop))

    predicate = captured["should_stop"]
    assert predicate is not None, "the pause cannot observe shutdown without it"
    assert predicate() is False
    stop.set()
    assert predicate() is True


def test_run_once_does_not_flag_a_roll_the_engine_itself_requested(root, quiet, monkeypatch):
    """Closes the loop between engine.dice and the autoroll guard.

    engine.dice's CLI runs in the agent's own Bash subprocess and logs a
    `pc_roll` event on a successful resolve. run_once must read those events
    back and treat those characters as legitimately requested — otherwise,
    now that party_names returns the real space-separated names, the guard
    would flag the engine's own sanctioned roll as a protocol violation.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(
        turn_loop.state, "party_names",
        lambda campaign: ["Falin", "Sylwen Nightbrook"],
    )

    narration = (
        "Мракът се сгъстява над криптата и въздухът застива.\n"
        "Falin: d20(14) + 3 = 17 vs DC 15 — УСПЕХ\n"
        "Sylwen Nightbrook: d20(9) + 5 = 14 vs DC 15 — ПРОВАЛ"
    )

    class RollingAgent:
        """Stands in for the DM invoking `engine.dice pc --character Falin`."""

        async def run_turn(self, prompt):
            dice.log_event("pc_roll", character="Falin", label="Stealth", total=17)
            return TurnResult(text=narration, ok=True)

    outcome = asyncio.run(
        turn_loop.run_once(Config(), RollingAgent(), "demo", "x", 1)
    )
    assert outcome.ok is True
    assert "Falin" not in outcome.autorolls, (
        "a roll the engine requested this turn must not be reported as a violation"
    )
    assert outcome.autorolls == ["Sylwen Nightbrook"], (
        "an unrequested PC roll must still be flagged"
    )


def test_run_once_ignores_pc_roll_events_from_earlier_turns(root, quiet, monkeypatch):
    """A roll requested during turn 1 must not excuse an auto-roll in turn 2."""
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop.state, "party_names", lambda campaign: ["Falin"])

    dice.log_event("pc_roll", character="Falin", label="Stealth", total=17)
    time.sleep(0.01)  # the stale event must be strictly before the turn start

    agent = StubAgent([TurnResult(
        text="Falin: d20(14) + 3 = 17 vs DC 15 — УСПЕХ", ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))
    assert outcome.autorolls == ["Falin"]


def test_run_once_does_not_double_push_into_a_saturated_display_log(root, quiet, monkeypatch):
    """End-to-end version of the deque(maxlen=60) regression, against the real
    state.text_log_fingerprint and a real text_log.json on disk — no stubbing
    of the before/after markers.

    With the old length comparison, every turn after the log saturated
    reported "the agent never pushed" and fired the fallback, sending the raw
    model response (references and OOC block included) on top of narration the
    agent had already delivered correctly.
    """
    log_file = root / ".runtime" / "text_log.json"
    entries = [{"text": f"ред {i}"} for i in range(60)]
    log_file.write_text(json.dumps(entries, ensure_ascii=False))

    pushed = []
    monkeypatch.setattr(turn_loop.display, "send_narration",
                        lambda t: pushed.append(t) or True)

    class PushingAgent:
        """Stands in for the DM correctly calling send.py itself."""

        async def run_turn(self, prompt):
            rolled = entries[1:] + [{"text": "Мракът се сгъстява над криптата."}]
            log_file.write_text(json.dumps(rolled, ensure_ascii=False))
            return TurnResult(text="Мракът се сгъстява над криптата.", ok=True)

    outcome = asyncio.run(turn_loop.run_once(Config(), PushingAgent(), "demo", "x", 1))
    assert len(json.loads(log_file.read_text())) == 60, "log stays saturated"
    assert outcome.fallback_used is False
    assert pushed == [], "narration already reached the display; do not push it twice"


def test_run_once_still_falls_back_when_saturated_and_nothing_pushed(root, quiet, monkeypatch):
    log_file = root / ".runtime" / "text_log.json"
    log_file.write_text(json.dumps([{"text": f"ред {i}"} for i in range(60)]))

    pushed = []
    monkeypatch.setattr(turn_loop.display, "send_narration",
                        lambda t: pushed.append(t) or True)
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))
    assert outcome.fallback_used is True
    assert pushed == ["Мракът се сгъстява над криптата."]


def test_requested_rolls_since_reads_the_shared_event_log(root):
    """The CLI is a separate process; the JSONL log is the only channel."""
    start = time.time()
    dice.log_event("pc_roll", character="Sylwen Nightbrook", label="Save", total=12)
    dice.log_event("dice_request", character="Torvin Bracewell", ok=True)
    assert turn_loop.requested_rolls_since(start) == {"Sylwen Nightbrook"}


def test_run_loop_stops_after_max_turns(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "wait_for_actions",
                        lambda **kw: _immediate("[Falin]: действие"))
    monkeypatch.setattr(turn_loop, "run_autosave", lambda campaign: None)
    agent = StubAgent([TurnResult(text="Мрак и тишина в криптата навсякъде.", ok=True)
                       for _ in range(3)])
    stop = asyncio.Event()
    turns = asyncio.run(turn_loop.run_loop(Config(), agent, "demo", stop, max_turns=3))
    assert turns == 3


def test_run_loop_survives_a_failing_turn(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "wait_for_actions",
                        lambda **kw: _immediate("[Falin]: действие"))
    monkeypatch.setattr(turn_loop, "run_autosave", lambda campaign: None)
    agent = StubAgent([
        TurnResult(ok=False, error="boom"),
        TurnResult(text="Мрак и тишина в криптата навсякъде.", ok=True),
    ])
    stop = asyncio.Event()
    turns = asyncio.run(turn_loop.run_loop(Config(), agent, "demo", stop, max_turns=2))
    assert turns == 2, "a failed turn must not kill the loop"


def test_run_loop_survives_wait_for_actions_crash(root, quiet, monkeypatch):
    """A crash while waiting for player input (e.g. a corrupted input queue)
    must not kill run_loop, and must not count as a completed turn — the loop
    should log it and keep waiting.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "run_autosave", lambda campaign: None)

    calls = {"n": 0}

    async def flaky_wait(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("simulated corrupted input queue")
        return "[Falin]: действие"

    monkeypatch.setattr(turn_loop, "wait_for_actions", flaky_wait)
    agent = StubAgent([TurnResult(text="Мрак и тишина в криптата навсякъде.", ok=True)])
    stop = asyncio.Event()
    turns = asyncio.run(turn_loop.run_loop(Config(), agent, "demo", stop, max_turns=1))
    assert turns == 1, "the loop must recover and still complete the requested turn"
    assert calls["n"] == 2, "the crashed wait must not have counted as a turn"


def test_run_loop_survives_autosave_crash(root, quiet, monkeypatch):
    """A crash inside run_autosave (belt-and-suspenders beyond its own internal
    handling) must not kill run_loop — a failed save shouldn't block the game.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "wait_for_actions",
                        lambda **kw: _immediate("[Falin]: действие"))

    def bad_autosave(campaign):
        raise RuntimeError("disk full")

    monkeypatch.setattr(turn_loop, "run_autosave", bad_autosave)
    agent = StubAgent([TurnResult(text="Мрак и тишина в криптата навсякъде.", ok=True)
                       for _ in range(2)])
    cfg = Config()
    cfg.autosave_every = 1  # trigger the (crashing) autosave every turn
    stop = asyncio.Event()
    turns = asyncio.run(turn_loop.run_loop(cfg, agent, "demo", stop, max_turns=2))
    assert turns == 2, "an autosave crash must not stop the loop from completing turns"


def test_run_loop_survives_non_utf8_input_queue(root, quiet, monkeypatch):
    """Reproduces the reviewer's exact real-world trigger: non-UTF-8 bytes in
    .runtime/.input_queue make the real (unmonkeypatched) state.take_input_queue
    raise UnicodeDecodeError — a ValueError subclass that state.take_input_queue's
    own `except OSError` does not catch — and the real wait_for_actions has no
    handling of its own around that call. run_loop must catch this at its call
    site and keep running instead of dying.

    take_input_queue's read fails before it ever reaches its own unlink()
    call, so the bad file is NEVER cleaned up — every subsequent read fails
    identically. This test lets run_loop actually retry against that same
    permanently-corrupted file several times (not just survive a single crash
    on the very first attempt) before signaling stop, so it would catch a
    regression where later retries behave differently than the first (e.g. a
    busy-loop that only a repeated failure would expose).
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "run_autosave", lambda campaign: None)
    # Keep the retry backoff short so the test runs fast while still
    # requiring a real await between retries (see the dedicated starvation
    # test below for the case where this is asserted directly).
    monkeypatch.setattr(turn_loop, "WAIT_FOR_ACTIONS_ERROR_BACKOFF_S", 0.01)

    queue_path = root / ".runtime" / ".input_queue"
    queue_path.write_bytes(b"\xff\xfe not valid utf-8 \xff")

    # Confirm the underlying trigger really does raise against the real,
    # unmonkeypatched implementation — keeps this test honest about what it's
    # regression-testing rather than only exercising a stand-in.
    with pytest.raises(UnicodeDecodeError):
        turn_loop.state.take_input_queue()
    # take_input_queue's read fails before it ever reaches the unlink() call,
    # so the bad file is still sitting on disk for wait_for_actions to hit
    # for real, repeatedly, inside run_loop below.
    assert queue_path.exists()

    REQUIRED_CONSECUTIVE_CRASHES = 3
    crashed = []
    real_log_event = turn_loop.log_event
    stop = asyncio.Event()

    def spying_log_event(event, **fields):
        if event == "wait_for_actions_crashed":
            crashed.append(fields)
            # Only stop after several consecutive failures against the same
            # corrupted file — proving repeated retries are handled safely,
            # not just a single crash caught on the very first attempt.
            if len(crashed) >= REQUIRED_CONSECUTIVE_CRASHES:
                stop.set()
        return real_log_event(event, **fields)

    monkeypatch.setattr(turn_loop, "log_event", spying_log_event)
    agent = StubAgent([])
    turns = asyncio.run(turn_loop.run_loop(Config(), agent, "demo", stop, max_turns=None))
    assert turns == 0, "a permanently corrupted queue must never be counted as a turn"
    assert len(crashed) >= REQUIRED_CONSECUTIVE_CRASHES, (
        "run_loop must keep retrying — and keep logging each attempt — "
        "against a persistently corrupted input queue, not just survive the "
        "first crash"
    )
    # take_input_queue never cleans up the bad file, so every attempt must
    # have failed with the same root cause.
    assert all("UnicodeDecodeError" in c["error"] for c in crashed)


def test_run_loop_does_not_starve_event_loop_on_persistent_wait_failures(root, quiet, monkeypatch):
    """The second-round regression this fix addresses: wait_for_actions's
    except branch in run_loop did a bare `continue` with no await in between,
    so a permanently failing wait_for_actions (exactly what a corrupted
    .input_queue produces) turned the while loop into a fully synchronous,
    CPU-bound spin that never yields control back to the event loop.

    This reproduces the re-reviewer's live probe: run the real run_loop with
    a persistently-failing wait_for_actions concurrently, via asyncio.gather,
    with a sibling ticker coroutine that only advances via its own
    asyncio.sleep — wrapped in a bounded asyncio.wait_for(). If run_loop
    starves the event loop, the ticker gets zero iterations and the bounded
    wait_for's own timeout callback cannot even be serviced (this is the
    "uncancellable, unkillable" failure mode the re-reviewer observed) — so
    merely asserting run_loop "eventually returns" would NOT catch this;
    the assertion has to be on the ticker's own independent progress, the
    same pattern test_run_once_offloads_usage_limit_pause_from_event_loop
    already uses for the asyncio.to_thread fix.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    monkeypatch.setattr(turn_loop, "run_autosave", lambda campaign: None)
    monkeypatch.setattr(turn_loop, "WAIT_FOR_ACTIONS_ERROR_BACKOFF_S", 0.01)

    async def always_fails(**kw):
        raise ValueError("permanently corrupted input queue")

    monkeypatch.setattr(turn_loop, "wait_for_actions", always_fails)

    ticks = {"n": 0}
    stop = asyncio.Event()

    async def ticker():
        for _ in range(20):
            await asyncio.sleep(0.01)
            ticks["n"] += 1
        stop.set()  # let run_loop terminate once we've proven it didn't starve us

    agent = StubAgent([])

    async def scenario():
        await asyncio.wait_for(
            asyncio.gather(
                turn_loop.run_loop(Config(), agent, "demo", stop, max_turns=None),
                ticker(),
            ),
            timeout=5.0,
        )

    asyncio.run(scenario())
    assert ticks["n"] >= 15, (
        f"ticker only advanced {ticks['n']}/20 times — run_loop's retry on a "
        "persistently failing wait_for_actions is starving the event loop "
        "instead of yielding via a genuine await"
    )


async def _immediate(value):
    return value


# ─── TTS pre-warm trigger (engine/tts_trigger.py) ───────────────────────────

def test_run_once_fires_tts_prewarm_exactly_once_on_success(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    calls = []
    monkeypatch.setattr(
        turn_loop.tts_trigger, "prewarm_tts",
        lambda text, display_port, voice=None: calls.append((text, display_port)) or True,
    )
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    cfg = Config()
    outcome = asyncio.run(turn_loop.run_once(cfg, agent, "demo", "[Falin]: вървя", 1))

    assert outcome.ok is True
    assert calls == [("Мракът се сгъстява над криптата.", cfg.display_port)]


def test_run_once_does_not_fire_tts_prewarm_when_turn_fails(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    calls = []
    monkeypatch.setattr(
        turn_loop.tts_trigger, "prewarm_tts",
        lambda text, display_port, voice=None: calls.append(1) or True,
    )
    agent = StubAgent([TurnResult(ok=False, error="timeout after 180s")])
    outcome = asyncio.run(turn_loop.run_once(Config(), agent, "demo", "x", 1))

    assert outcome.ok is False
    assert calls == [], "a failed turn has no result.text to pre-warm with and must not call it"


def test_run_once_does_not_fire_tts_prewarm_when_disabled(root, quiet, monkeypatch):
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))
    calls = []
    monkeypatch.setattr(
        turn_loop.tts_trigger, "prewarm_tts",
        lambda text, display_port, voice=None: calls.append(1) or True,
    )
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])
    cfg = Config()
    cfg.tts_prewarm = False
    outcome = asyncio.run(turn_loop.run_once(cfg, agent, "demo", "x", 1))

    assert outcome.ok is True
    assert calls == [], "cfg.tts_prewarm=False must suppress the pre-warm call entirely"


def test_run_once_returns_promptly_even_when_tts_prewarm_is_slow(root, quiet, monkeypatch):
    """prewarm_tts is launched via asyncio.create_task(asyncio.to_thread(...))
    and deliberately NOT awaited by run_once. If run_once instead awaited
    that task (directly or indirectly), its own return would be delayed by
    the prewarm's full duration.

    Measures the elapsed time of `await run_once(...)` ALONE, captured from
    inside the still-running event loop, before the coroutine returns —
    deliberately not the wall time of the surrounding asyncio.run() call.
    asyncio.run() cancels-and-awaits any still-pending tasks during its own
    shutdown before returning to the caller, so a wrapping measurement would
    include that unavoidable teardown wait for the (still-sleeping) prewarm
    task and would time out regardless of whether run_once itself blocked on
    it — that is a property of asyncio.run's cleanup phase, not of run_once,
    and asserting on it would make this test fail for the wrong reason.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))

    sleep_seconds = 0.2

    def slow_prewarm(text, display_port, voice=None):
        time.sleep(sleep_seconds)
        return True

    monkeypatch.setattr(turn_loop.tts_trigger, "prewarm_tts", slow_prewarm)
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])

    async def scenario():
        t0 = time.time()
        outcome = await turn_loop.run_once(Config(), agent, "demo", "x", 1)
        return outcome, time.time() - t0

    outcome, run_once_elapsed = asyncio.run(scenario())

    assert outcome.ok is True
    assert run_once_elapsed < sleep_seconds / 2, (
        f"run_once took {run_once_elapsed:.3f}s to return -- uncomfortably "
        f"close to the prewarm's own {sleep_seconds}s sleep, suggesting it "
        "is waiting on the pre-warm task instead of firing it un-awaited"
    )


def test_run_once_holds_a_strong_reference_to_the_prewarm_task(root, quiet, monkeypatch):
    """asyncio only holds a WEAK reference to a running task; an unawaited,
    unreferenced task can be garbage-collected mid-flight. turn_loop keeps
    _PREWARM_TASKS as a module-level strong-reference set specifically to
    prevent that -- this proves run_once actually populates it (even if
    only transiently, since the done-callback discards it once complete).

    Waits for the task to finish and be discarded from WITHIN the same
    running event loop (via short polling asyncio.sleep(0) calls, not a
    fixed sleep) before asserting on the empty-set postcondition --
    asyncio.run() tearing down right after run_once() returns would
    otherwise race the worker thread's completion and its done-callback,
    since the prewarm call is deliberately un-awaited.
    """
    monkeypatch.setattr(turn_loop.state, "text_log_fingerprint", lambda: (7, "[]"))

    observed_during_run = {}

    def prewarm_that_checks_the_set(text, display_port, voice=None):
        # Called from a worker thread (via asyncio.to_thread) while the task
        # is still in flight -- the task must already be in the set by then.
        observed_during_run["size"] = len(turn_loop._PREWARM_TASKS)
        return True

    monkeypatch.setattr(turn_loop.tts_trigger, "prewarm_tts", prewarm_that_checks_the_set)
    agent = StubAgent([TurnResult(text="Мракът се сгъстява над криптата.", ok=True)])

    async def scenario():
        outcome = await turn_loop.run_once(Config(), agent, "demo", "x", 1)
        for _ in range(200):  # bounded wait, ~2s worst case
            if not turn_loop._PREWARM_TASKS:
                break
            await asyncio.sleep(0.01)
        return outcome

    outcome = asyncio.run(scenario())

    assert outcome.ok is True
    assert observed_during_run.get("size", 0) >= 1, (
        "the prewarm task must be held in _PREWARM_TASKS while it is running"
    )
    # The done-callback must clean up afterward — the set must not grow
    # unboundedly across turns.
    assert len(turn_loop._PREWARM_TASKS) == 0
