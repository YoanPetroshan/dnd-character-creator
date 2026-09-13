import asyncio

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    RateLimitEvent,
    RateLimitInfo,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from engine import agent as agent_module
from engine.agent import DMAgent, TurnResult, is_usage_limit_error
from engine.config import Config


class FakeText:
    def __init__(self, text):
        self.text = text


class FakeAssistant:
    def __init__(self, text):
        self.content = [FakeText(text)]


class FakeResult:
    def __init__(self, reason="end_turn"):
        self.terminal_reason = reason
        self.result = None


class FakeClient:
    """Stands in for ClaudeSDKClient."""

    def __init__(self, chunks, raises=None, delay=0.0):
        self.chunks = chunks
        self.raises = raises
        self.delay = delay
        self.queries = []

    async def connect(self, prompt=None):
        return None

    async def query(self, prompt):
        self.queries.append(prompt)

    async def receive_response(self):
        if self.raises:
            raise self.raises
        for chunk in self.chunks:
            await asyncio.sleep(self.delay)
            yield chunk

    async def disconnect(self):
        return None


def make_agent(client, cfg=None):
    agent = DMAgent(cfg or Config(turn_timeout_s=1, turn_retries=1), system_prompt="SP")
    agent._client = client  # bypass real SDK construction
    return agent


def fake_lifecycle(agent):
    """Replace agent.start/stop with async no-ops that only record calls.

    run_turn now reconnects (stop() then start()) between attempts when an
    attempt failed with a dead-connection error. The real start() constructs a
    ClaudeSDKClient and connects it — which in a unit test means spawning the
    `claude` CLI and issuing a real API call. These fakes keep the injected
    FakeClient in place (so the retry still runs against the fake stream) and
    let a test assert that the reconnect actually happened.

    Returns the call-order list, e.g. ["stop", "start"].
    """
    calls: list[str] = []

    async def fake_stop():
        calls.append("stop")

    async def fake_start():
        calls.append("start")

    agent.stop = fake_stop
    agent.start = fake_start
    return calls


def test_run_turn_collects_text(monkeypatch):
    client = FakeClient([FakeAssistant("Мракът се сгъстява."), FakeResult()])
    agent = make_agent(client)
    result = asyncio.run(agent.run_turn("ход"))
    assert isinstance(result, TurnResult)
    assert result.ok is True
    assert "Мракът" in result.text
    assert client.queries == ["ход"]


def test_run_turn_times_out_and_reports():
    client = FakeClient([FakeAssistant("бавно")], delay=5.0)
    agent = make_agent(client, Config(turn_timeout_s=1, turn_retries=0))
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is False
    assert "timeout" in (result.error or "")


def test_run_turn_retries_once_then_succeeds():
    """A mid-stream transport exception is a dead-connection failure, so the
    retry must go out on a REBUILT connection, not the dead one."""
    class Flaky(FakeClient):
        def __init__(self):
            super().__init__([FakeAssistant("ок"), FakeResult()])
            self.calls = 0

        async def receive_response(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient")
            for chunk in self.chunks:
                yield chunk

    client = Flaky()
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    lifecycle = fake_lifecycle(agent)
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True
    assert client.calls == 2
    # The reconnect must have happened BETWEEN the two attempts, in order.
    assert lifecycle == ["stop", "start"]


def test_run_turn_gives_up_after_retries():
    client = FakeClient([], raises=RuntimeError("permanent"))
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    fake_lifecycle(agent)
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is False
    assert "permanent" in (result.error or "")


@pytest.mark.parametrize("msg", [
    "Claude usage limit reached",
    "rate_limit_error: too many requests",
    "You have exceeded your usage limit",
])
def test_usage_limit_detection(msg):
    assert is_usage_limit_error(msg) is True


def test_non_limit_error_is_not_flagged():
    assert is_usage_limit_error("connection reset by peer") is False


def test_run_turn_stops_on_rejected_rate_limit_event():
    event = RateLimitEvent(
        rate_limit_info=RateLimitInfo(status="rejected", rate_limit_type="five_hour"),
        uuid="u1",
        session_id="sess-rl",
    )
    client = FakeClient([event])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is False
    assert is_usage_limit_error(result.error) is True
    # Retry loop must break immediately on a hard rate-limit rejection,
    # not burn every retry attempt.
    assert client.queries == ["ход"]
    assert agent.session_id == "sess-rl"


def test_run_turn_treats_assistant_billing_error_as_failure():
    assistant = AssistantMessage(
        content=[], model="claude-sonnet-5", error="billing_error", session_id="sess-be"
    )
    client = FakeClient([assistant])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is False
    assert "billing_error" in (result.error or "")
    assert is_usage_limit_error(result.error) is True
    assert client.queries == ["ход"]
    assert agent.session_id == "sess-be"


def test_run_turn_treats_result_is_error_as_failure():
    result_msg = ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=10,
        is_error=True,
        num_turns=1,
        session_id="sess-re",
        api_error_status=429,
    )
    client = FakeClient([result_msg])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is False
    assert "429" in (result.error or "")
    assert agent.session_id == "sess-re"


@pytest.mark.parametrize("msg", [
    "Your credit balance is too low to access the Anthropic API",
    "5-hour limit reached",
    "You've hit your usage cap for this session",
])
def test_usage_limit_detection_wider_phrasing(msg):
    assert is_usage_limit_error(msg) is True


def _spy_on_log_event(monkeypatch):
    """Wrap engine.agent.log_event to record every call while still
    delegating to the real implementation (same pattern used in
    engine/tests/test_turn_loop.py)."""
    events: list[tuple[str, dict]] = []
    real_log_event = agent_module.log_event

    def spying_log_event(event, **fields):
        events.append((event, fields))
        return real_log_event(event, **fields)

    monkeypatch.setattr(agent_module, "log_event", spying_log_event)
    return events


def test_tool_call_timing_is_logged_as_started_and_finished(monkeypatch, tmp_path):
    # log_event writes to the runtime dir; point it at a tmp dir so the test
    # doesn't touch the real campaign's log file.
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    tool_use = ToolUseBlock(
        id="tu-1", name="Bash", input={"command": "engine/dice.py roll 1d20 # attack roll"}
    )
    assistant = AssistantMessage(content=[tool_use], model="claude-sonnet-5")
    tool_result = UserMessage(
        content=[ToolResultBlock(tool_use_id="tu-1", content="17", is_error=False)]
    )
    # Small delay between messages so elapsed time is measurably positive
    # rather than possibly landing on the exact same time.time() tick.
    client = FakeClient([assistant, tool_result, FakeResult()], delay=0.01)
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    started = [f for e, f in events if e == "tool_call_started"]
    finished = [f for e, f in events if e == "tool_call_finished"]

    assert len(started) == 1
    assert started[0]["tool"] == "Bash"
    assert started[0]["tool_use_id"] == "tu-1"
    assert started[0]["command_prefix"].startswith("engine/dice.py roll 1d20")

    assert len(finished) == 1
    assert finished[0]["tool_use_id"] == "tu-1"
    assert finished[0]["is_error"] is False
    assert finished[0]["elapsed_s"] > 0


def test_turn_tool_breakdown_summary_has_correct_counts_and_sums(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    assistant1 = AssistantMessage(
        content=[
            ToolUseBlock(id="tu-1", name="Bash", input={"command": "engine/dice.py roll 1d20"}),
            ToolUseBlock(id="tu-2", name="Read", input={"file_path": "campaign/state.json"}),
        ],
        model="claude-sonnet-5",
        usage={"input_tokens": 1000, "output_tokens": 250},
    )
    results1 = UserMessage(
        content=[
            ToolResultBlock(tool_use_id="tu-1", content="14", is_error=False),
            ToolResultBlock(tool_use_id="tu-2", content="{}", is_error=False),
        ]
    )
    assistant2 = AssistantMessage(
        content=[],
        model="claude-sonnet-5",
        usage={"input_tokens": 1200, "output_tokens": 80},
    )
    client = FakeClient([assistant1, results1, assistant2, FakeResult()], delay=0.005)
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    breakdowns = [f for e, f in events if e == "turn_tool_breakdown"]
    assert len(breakdowns) == 1
    breakdown = breakdowns[0]
    assert breakdown["tool_call_count"] == 2
    assert breakdown["total_tool_time_s"] > 0
    assert breakdown["total_output_tokens"] == 330  # 250 + 80


def test_unexpected_block_shape_does_not_crash_the_turn(monkeypatch, tmp_path):
    """A ToolUseBlock/ToolResultBlock with an unhashable id is a shape the
    instrumentation didn't anticipate (dict lookups require hashable keys).
    The turn must still complete normally, just without instrumentation for
    that one anomalous message."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    malformed_assistant = AssistantMessage(
        content=[ToolUseBlock(id={"unexpected": "shape"}, name="Bash", input={"command": "x"})],
        model="claude-sonnet-5",
    )
    from claude_agent_sdk import TextBlock

    normal_assistant = AssistantMessage(
        content=[TextBlock(text="Продължаваме напред.")], model="claude-sonnet-5"
    )
    client = FakeClient([malformed_assistant, normal_assistant, FakeResult()])
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is True
    assert "Продължаваме" in result.text
    # No tool_call_started should have been logged for the malformed block —
    # the exception happens before the log_event call is reached.
    started = [f for e, f in events if e == "tool_call_started"]
    assert started == []
    # The summary event must still be emitted despite the anomaly.
    breakdowns = [f for e, f in events if e == "turn_tool_breakdown"]
    assert len(breakdowns) == 1


def test_non_bash_tool_use_has_no_command_prefix(monkeypatch, tmp_path):
    """A ToolUseBlock whose input isn't a dict, or is a dict without a
    "command" key, must not crash and must simply omit command_prefix."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    assistant = AssistantMessage(
        content=[
            ToolUseBlock(id="tu-read", name="Read", input={"file_path": "state.json"}),
            ToolUseBlock(id="tu-weird", name="Bash", input="not a dict"),
        ],
        model="claude-sonnet-5",
    )
    client = FakeClient([assistant, FakeResult()])
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    started = [f for e, f in events if e == "tool_call_started"]
    assert len(started) == 2
    read_event = next(f for f in started if f["tool_use_id"] == "tu-read")
    bash_event = next(f for f in started if f["tool_use_id"] == "tu-weird")
    assert "command_prefix" not in read_event
    assert "command_prefix" not in bash_event


def test_tool_result_with_no_matching_start_still_logs_finished_with_null_elapsed(
    monkeypatch, tmp_path
):
    """A ToolResultBlock whose tool_use_id was never seen in a
    tool_call_started (e.g. a truncated stream) must still be logged, just
    with elapsed_s=None instead of a computed duration."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    orphan_result = UserMessage(
        content=[ToolResultBlock(tool_use_id="never-started", content="x", is_error=False)]
    )
    client = FakeClient([orphan_result, FakeResult()])
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    finished = [f for e, f in events if e == "tool_call_finished"]
    assert len(finished) == 1
    assert finished[0]["tool_use_id"] == "never-started"
    assert finished[0]["elapsed_s"] is None

    breakdown = next(f for e, f in events if e == "turn_tool_breakdown")
    assert breakdown["tool_call_count"] == 1
    assert breakdown["total_tool_time_s"] == 0.0


# ── Item 1: a turn must never silently succeed with empty content ──────────


def _result(session_id="sess-ok", usage=None, cost=None):
    return ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=10,
        is_error=False,
        num_turns=1,
        session_id=session_id,
        usage=usage,
        total_cost_usd=cost,
    )


def test_stream_without_result_message_is_not_a_success(monkeypatch, tmp_path):
    """The real failure mode: a retry on a client whose reader task died
    drains a leftover end-of-stream sentinel — zero messages, no exception.
    That used to fall through to ok=True with empty text (the player's action
    silently vanished). It must now be a reported failure."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    client = FakeClient([])  # stream ends with no terminal message at all
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert result.error == "no_result_message_received"


def test_partial_text_without_result_message_is_still_a_failure(monkeypatch, tmp_path):
    """Even with some text collected, a stream that never reached a terminal
    result is a truncated turn, not a success."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    client = FakeClient([FakeAssistant("началото на сцена")])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert result.error == "no_result_message_received"


def test_transport_exception_is_structured_not_propagated(monkeypatch, tmp_path):
    """The real incident raised a bare Exception ("Failed to decode JSON: JSON
    message exceeded maximum buffer size of 1048576 bytes") from the iteration
    itself. It must be caught at the loop level and turned into a classifiable
    error string, not escape to run_turn's generic catch."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    boom = Exception(
        "Failed to decode JSON: JSON message exceeded maximum buffer size of 1048576 bytes"
    )
    client = FakeClient([], raises=boom)
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert (result.error or "").startswith("transport_error:")
    assert "maximum buffer size" in (result.error or "")


def test_both_dead_connection_shapes_are_classified():
    assert agent_module.is_dead_connection_error("transport_error:Exception: boom") is True
    assert agent_module.is_dead_connection_error("no_result_message_received") is True
    # Ordinary failures must NOT be treated as a dead connection.
    assert agent_module.is_dead_connection_error("timeout after 300s") is False
    assert agent_module.is_dead_connection_error("result_error: api_error_status=500") is False
    assert agent_module.is_dead_connection_error("") is False
    assert agent_module.is_dead_connection_error(None) is False


def test_transport_error_reconnects_with_resume_before_retrying(monkeypatch, tmp_path):
    """A dead-connection attempt must be followed by a real stop()/start()
    reconnect, and the rebuilt connection must resume the SAME Claude session
    rather than silently starting a fresh one."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))

    class DeadThenAlive(FakeClient):
        def __init__(self):
            super().__init__([FakeAssistant("продължаваме"), _result("sess-live")])
            self.calls = 0

        async def receive_response(self):
            self.calls += 1
            if self.calls == 1:
                # Session id is learned before the transport dies, exactly as
                # in the real incident.
                yield _result("sess-live")
                raise Exception("JSON message exceeded maximum buffer size of 1048576 bytes")
            for chunk in self.chunks:
                yield chunk

    client = DeadThenAlive()
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))

    calls: list[str] = []
    resumed: list[str | None] = []

    async def fake_stop():
        calls.append("stop")

    async def fake_start():
        calls.append("start")
        # Capture what the rebuilt client WOULD be constructed with.
        resumed.append(agent._options().resume)

    agent.stop = fake_stop
    agent.start = fake_start

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is True
    assert client.calls == 2
    assert calls == ["stop", "start"]
    assert resumed == ["sess-live"], "reconnect must resume the same session"


def test_no_result_message_also_triggers_a_reconnect(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))

    class EmptyThenAlive(FakeClient):
        def __init__(self):
            super().__init__([FakeAssistant("ок"), _result()])
            self.calls = 0

        async def receive_response(self):
            self.calls += 1
            if self.calls == 1:
                return  # empty stream, no exception — the silent-failure shape
                yield  # pragma: no cover — makes this an async generator
            for chunk in self.chunks:
                yield chunk

    client = EmptyThenAlive()
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    lifecycle = fake_lifecycle(agent)

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is True
    assert lifecycle == ["stop", "start"]


def test_ordinary_failure_does_not_reconnect(monkeypatch, tmp_path):
    """A plain API-level result error is not a dead connection — reconnecting
    would throw away a perfectly good session for nothing."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    failing = ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=10,
        is_error=True,
        num_turns=1,
        session_id="sess-err",
        api_error_status=500,
    )
    client = FakeClient([failing])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    lifecycle = fake_lifecycle(agent)

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert "500" in (result.error or "")
    assert lifecycle == []


def test_timeout_does_not_reconnect(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    client = FakeClient([FakeAssistant("бавно")], delay=5.0)
    agent = make_agent(client, Config(turn_timeout_s=1, turn_retries=1))
    lifecycle = fake_lifecycle(agent)

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert "timeout" in (result.error or "")
    assert lifecycle == []


def test_failed_reconnect_is_reported_not_raised(monkeypatch, tmp_path):
    """If stop()/start() themselves fail, run_turn must return a normal failed
    TurnResult — not crash, and not retry onto a half-torn-down client."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    client = FakeClient([], raises=Exception("buffer size exceeded"))
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))

    async def fake_stop():
        return None

    async def fake_start():
        raise ConnectionError("cannot respawn claude")

    agent.stop = fake_stop
    agent.start = fake_start

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert (result.error or "").startswith("reconnect_failed:ConnectionError")


# ── Item 1, fix round: a failed reconnect must not wedge the agent ─────────


class FailingSDKClient:
    """Stands in for ClaudeSDKClient when connect() is the thing that fails —
    the realistic reconnect hiccup (the `claude` CLI respawn stumbles once)."""

    constructed = 0

    def __init__(self, options=None):
        type(self).constructed += 1
        self.options = options

    async def connect(self, prompt=None):
        raise ConnectionError("claude CLI respawn failed")

    async def disconnect(self):
        return None


def _patch_sdk_client(monkeypatch, cls):
    """Patch ClaudeSDKClient where start() looks it up (it imports lazily from
    the claude_agent_sdk module at call time)."""
    import claude_agent_sdk

    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", cls)


def test_start_discards_the_client_when_connect_fails(monkeypatch, tmp_path):
    """If connect() raises, the half-built client must NOT stay in
    self._client — start()'s `if self._client is not None: return` guard would
    then make every future start() a silent no-op, wedging the agent for the
    rest of the process."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    FailingSDKClient.constructed = 0
    _patch_sdk_client(monkeypatch, FailingSDKClient)

    agent = DMAgent(Config(turn_timeout_s=5, turn_retries=1), system_prompt="SP")

    with pytest.raises(ConnectionError):
        asyncio.run(agent.start())
    assert agent._client is None, "a client that never connected must not be kept"

    # And a SUBSEQUENT start() must genuinely try to rebuild, not early-return.
    with pytest.raises(ConnectionError):
        asyncio.run(agent.start())
    assert FailingSDKClient.constructed == 2, "the second start() must rebuild, not no-op"


def test_agent_recovers_on_a_later_turn_after_a_failed_reconnect(monkeypatch, tmp_path):
    """End-to-end shape of the wedge: turn 1 hits a dead transport, the
    reconnect fails, and the client is gone. Turn 2 must still be able to come
    back to life on its own — no manual whole-stack restart."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))

    healthy = FakeClient([FakeAssistant("живи сме"), _result("sess-back")])

    class FlakyThenWorkingSDKClient:
        attempts = 0

        def __init__(self, options=None):
            type(self).attempts += 1
            self.options = options

        async def connect(self, prompt=None):
            if type(self).attempts == 1:
                raise ConnectionError("claude CLI respawn failed")

        async def query(self, prompt):
            await healthy.query(prompt)

        def receive_response(self):
            return healthy.receive_response()

        async def disconnect(self):
            return None

    _patch_sdk_client(monkeypatch, FlakyThenWorkingSDKClient)

    agent = make_agent(
        FakeClient([], raises=Exception("JSON message exceeded maximum buffer size")),
        Config(turn_timeout_s=5, turn_retries=0),
    )

    # Turn 1: dead transport, and with no retries left the reconnect is not even
    # attempted — but a reconnect failure elsewhere leaves the same state, so
    # simulate the wedge directly.
    first = asyncio.run(agent.run_turn("ход 1"))
    assert first.ok is False
    agent._client = None  # what a failed reconnect leaves behind

    # Turn 2: the first rebuild attempt fails, the second (on the retry) works.
    agent.cfg = Config(turn_timeout_s=5, turn_retries=1)
    second = asyncio.run(agent.run_turn("ход 2"))

    assert second.ok is True, "the agent must heal itself on a later turn"
    assert "живи сме" in second.text
    assert FlakyThenWorkingSDKClient.attempts >= 2


def test_failed_reconnect_leaves_no_client_behind(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    client = FakeClient([], raises=Exception("buffer size exceeded"))
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))

    async def fake_stop():
        agent._client = None

    async def fake_start():
        # Mimic the real failure mode: a client instance exists but connect()
        # blew up. start() must not leave it in the slot; run_turn must not
        # either.
        agent._client = object()
        raise ConnectionError("cannot respawn claude")

    agent.stop = fake_stop
    agent.start = fake_start

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert (result.error or "").startswith("reconnect_failed:ConnectionError")
    assert agent._client is None, "a wedged, unconnected client must never be kept"


# ── Item 1, fix round: the WRITE side of the connection ────────────────────


def test_query_failure_is_classified_as_a_dead_connection(monkeypatch, tmp_path):
    """A dead connection surfaces on the write side too. Left unguarded, the
    CLIConnectionError escaped to run_turn's generic catch as an unclassified
    string and the reconnect never fired."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))

    class DeadOnWrite(FakeClient):
        async def query(self, prompt):
            raise RuntimeError("Not connected. Call connect() first.")

    agent = make_agent(DeadOnWrite([]), Config(turn_timeout_s=5, turn_retries=0))
    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is False
    assert (result.error or "").startswith("transport_error:")
    assert agent_module.is_dead_connection_error(result.error) is True


def test_query_failure_triggers_a_reconnect_before_the_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))

    class DeadOnWriteThenAlive(FakeClient):
        def __init__(self):
            super().__init__([FakeAssistant("отново тук"), _result("sess-w")])
            self.write_attempts = 0

        async def query(self, prompt):
            self.write_attempts += 1
            if self.write_attempts == 1:
                raise RuntimeError("Not connected. Call connect() first.")
            self.queries.append(prompt)

    client = DeadOnWriteThenAlive()
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=1))
    lifecycle = fake_lifecycle(agent)

    result = asyncio.run(agent.run_turn("ход"))

    assert result.ok is True
    assert client.write_attempts == 2
    assert lifecycle == ["stop", "start"], "the write-side failure must reconnect"


def test_bare_not_connected_string_is_reconnect_eligible():
    """Belt-and-braces: even an unstructured error string that never went
    through _one_attempt's guard must be recognised."""
    assert agent_module.is_dead_connection_error(
        "CLIConnectionError: Not connected. Call connect() first."
    ) is True
    assert agent_module.is_dead_connection_error("Not connected. Call connect() first.") is True
    # ...without over-matching ordinary failures.
    assert agent_module.is_dead_connection_error("connection reset by peer") is False
    assert agent_module.is_dead_connection_error("timeout after 300s") is False


def test_options_carry_resume_only_once_a_session_is_known():
    agent = DMAgent(Config(turn_timeout_s=1, turn_retries=0), system_prompt="SP")
    assert agent._options().resume is None  # first start(): safe no-op
    agent.session_id = "sess-42"
    assert agent._options().resume == "sess-42"


# ── Item 2: per-turn token/cost accounting ─────────────────────────────────


def test_first_turn_logs_cumulative_usage_verbatim(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    client = FakeClient([
        _result(usage={"input_tokens": 1200, "output_tokens": 400}, cost=0.05)
    ])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    breakdown = next(f for e, f in events if e == "turn_tool_breakdown")
    assert breakdown["turn_usage"] == {"input_tokens": 1200, "output_tokens": 400}
    assert breakdown["turn_cost_usd"] == pytest.approx(0.05)


def test_second_turn_logs_only_the_delta(monkeypatch, tmp_path):
    """ResultMessage.usage/total_cost_usd are cumulative for the whole
    persistent session — reading them raw would over-count every turn after
    the first."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    agent = make_agent(
        FakeClient([_result(usage={"input_tokens": 1000, "output_tokens": 300}, cost=0.04)]),
        Config(turn_timeout_s=5, turn_retries=0),
    )
    assert asyncio.run(agent.run_turn("ход 1")).ok is True

    agent._client = FakeClient(
        [_result(usage={"input_tokens": 2500, "output_tokens": 750}, cost=0.11)]
    )
    assert asyncio.run(agent.run_turn("ход 2")).ok is True

    breakdowns = [f for e, f in events if e == "turn_tool_breakdown"]
    assert len(breakdowns) == 2
    assert breakdowns[1]["turn_usage"] == {"input_tokens": 1500, "output_tokens": 450}
    assert breakdowns[1]["turn_cost_usd"] == pytest.approx(0.07)


def test_session_reset_logs_the_raw_value_not_a_negative(monkeypatch, tmp_path):
    """A cumulative value LOWER than the snapshot means the session's counters
    were reset (conversation reset, or a reconnect onto fresh counters). The
    turn's own usage is then the raw new value — never a negative number."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    agent = make_agent(
        FakeClient([_result(usage={"input_tokens": 9000, "output_tokens": 2000}, cost=0.90)]),
        Config(turn_timeout_s=5, turn_retries=0),
    )
    assert asyncio.run(agent.run_turn("ход 1")).ok is True

    agent._client = FakeClient(
        [_result(usage={"input_tokens": 500, "output_tokens": 120}, cost=0.02)]
    )
    assert asyncio.run(agent.run_turn("ход 2")).ok is True

    breakdown = [f for e, f in events if e == "turn_tool_breakdown"][1]
    assert breakdown["turn_usage"] == {"input_tokens": 500, "output_tokens": 120}
    assert breakdown["turn_cost_usd"] == pytest.approx(0.02)
    assert all(v >= 0 for v in breakdown["turn_usage"].values())


def test_non_numeric_usage_entries_are_skipped_without_crashing(monkeypatch, tmp_path):
    """Real usage dicts carry nested/non-numeric entries (cache breakdowns,
    server_tool_use). They must be ignored, not crash the accounting."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    client = FakeClient([
        _result(
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "server_tool_use": {"web_search_requests": 2},
                "service_tier": "standard",
            },
            cost=0.01,
        )
    ])
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    assert asyncio.run(agent.run_turn("ход")).ok is True
    breakdown = next(f for e, f in events if e == "turn_tool_breakdown")
    assert breakdown["turn_usage"] == {"input_tokens": 100, "output_tokens": 50}


def test_result_without_usage_omits_the_new_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    client = FakeClient([FakeResult()])  # duck-typed terminal, no usage/cost
    agent = make_agent(client, Config(turn_timeout_s=5, turn_retries=0))

    assert asyncio.run(agent.run_turn("ход")).ok is True
    breakdown = next(f for e, f in events if e == "turn_tool_breakdown")
    assert "turn_usage" not in breakdown
    assert "turn_cost_usd" not in breakdown


def test_usage_without_output_tokens_is_not_reported(monkeypatch, tmp_path):
    """An AssistantMessage.usage dict that doesn't carry output_tokens (or
    carries a non-numeric value for it) must not be summed in, and
    total_output_tokens must be omitted from the summary entirely rather
    than reported as a misleading 0."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    events = _spy_on_log_event(monkeypatch)

    assistant = AssistantMessage(
        content=[],
        model="claude-sonnet-5",
        usage={"input_tokens": 500},  # no output_tokens key at all
    )
    client = FakeClient([assistant, FakeResult()])
    agent = make_agent(client)

    result = asyncio.run(agent.run_turn("ход"))
    assert result.ok is True

    breakdown = next(f for e, f in events if e == "turn_tool_breakdown")
    assert "total_output_tokens" not in breakdown
