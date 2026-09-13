"""Claude Agent SDK wrapper. The only module that imports the SDK."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from engine.config import Config, campaign_root
from engine.log import log_event

REPO_ROOT = Path(__file__).resolve().parent.parent

_LIMIT_MARKERS = (
    "usage limit",
    "rate_limit",
    "rate limit",
    "quota",
    "exceeded your usage",
    "credit balance",
    "limit reached",
    "usage cap",
    "5-hour",
    "seven-day",
    "billing_error",
)


def is_usage_limit_error(message: str) -> bool:
    low = (message or "").lower()
    return any(marker in low for marker in _LIMIT_MARKERS)


# Structured error strings produced by _one_attempt for the two failure shapes
# that mean "the persistent client's connection is dead — retrying on it is
# futile." Both are constructed by this module, so classification matches on
# the string shape we ourselves emit rather than on an SDK exception type: the
# real, already-observed incident surfaced as a bare `Exception` ("Failed to
# decode JSON: JSON message exceeded maximum buffer size of 1048576 bytes"),
# with no distinguishable subclass to match on.
TRANSPORT_ERROR_PREFIX = "transport_error:"
NO_RESULT_ERROR = "no_result_message_received"

# Belt-and-braces: markers of "this client is not connected" that could reach
# run_turn as a plain, unstructured error string from anywhere outside
# _one_attempt's own guard. _one_attempt now wraps both the write (query) and
# the read (iteration) sides, so these should already arrive as
# transport_error:..., but a connection-dead failure must be reconnect-eligible
# no matter which path produced the string.
_DEAD_CONNECTION_MARKERS = (
    "not connected",
    "cliconnectionerror",
)


def is_dead_connection_error(message: str) -> bool:
    """True if this failure means the SDK client's connection is dead.

    The SDK's background reader task can die on a transport-level exception
    (e.g. a single JSON message from the `claude` CLI exceeding the 1MB buffer).
    A retry issued on the SAME client then drains a leftover end-of-stream
    sentinel and yields zero messages with no exception at all — which is how a
    turn used to "succeed" with empty text. The write side fails just as hard,
    with a CLIConnectionError. All of these shapes call for a full
    stop()/start() reconnect before retrying.
    """
    msg = message or ""
    if msg.startswith(TRANSPORT_ERROR_PREFIX) or msg == NO_RESULT_ERROR:
        return True
    low = msg.lower()
    return any(marker in low for marker in _DEAD_CONNECTION_MARKERS)


@dataclass
class TurnResult:
    text: str = ""
    ok: bool = False
    error: str | None = None
    terminal_reason: str | None = None


class DMAgent:
    """One persistent Claude session that answers one turn at a time."""

    def __init__(self, cfg: Config, system_prompt: str):
        self.cfg = cfg
        self.system_prompt = system_prompt
        self._client = None
        self.session_id: str | None = None
        # ResultMessage.usage / .total_cost_usd are CUMULATIVE for the whole
        # persistent session (they only reset on a conversation reset), so a
        # per-turn figure is the diff against what the previous turn's
        # ResultMessage reported. See _diff_usage().
        self._last_usage_snapshot: dict = {}
        self._last_cost_snapshot: float = 0.0

    def _options(self):
        from claude_agent_sdk import ClaudeAgentOptions

        return ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            model=self.cfg.turn_model,
            cwd=str(campaign_root()),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            setting_sources=[],
            env={"API_TIMEOUT_MS": str(self.cfg.turn_timeout_s * 1000)},
            # Reconnecting after a dead transport must not silently drop the
            # conversation: without `resume`, start() would open a BRAND NEW
            # Claude session and the DM would lose every bit of in-session
            # context. self.session_id is tracked off each message during
            # normal turns; it is None on the very first start(), where
            # resume=None is a no-op.
            resume=self.session_id,
        )

    async def start(self) -> None:
        if self._client is not None:
            return
        from claude_agent_sdk import ClaudeSDKClient

        # A partially-constructed client must NEVER end up in self._client.
        # If connect() fails (a `claude` CLI respawn hiccup during a reconnect
        # is the realistic case), leaving the unconnected instance in the slot
        # would make the `if self._client is not None: return` guard above turn
        # every FUTURE start() into a silent no-op — nothing would ever rebuild
        # it, and every subsequent turn would fail with "Not connected. Call
        # connect() first." until the whole stack was restarted by hand. So the
        # instance is built locally and only published after connect() succeeds.
        client = ClaudeSDKClient(options=self._options())
        try:
            await client.connect()
        except BaseException:
            self._client = None
            raise
        self._client = client
        log_event("agent_started", model=self.cfg.turn_model)

    async def stop(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.disconnect()
        finally:
            self._client = None
            log_event("agent_stopped")

    async def _one_attempt(self, prompt: str) -> TurnResult:
        from claude_agent_sdk import (
            AssistantMessage,
            RateLimitEvent,
            ResultMessage,
            TextBlock,
            ToolResultBlock,
            ToolUseBlock,
            UserMessage,
        )

        chunks: list[str] = []
        reason: str | None = None
        error: str | None = None

        # Diagnostic instrumentation only — tracks per-tool-call timing and
        # output-token volume so we can see where a turn's wall-clock time
        # actually goes (tool round-trips vs. text generation). Purely
        # additive: never affects control flow, timeout, retry, or the
        # returned TurnResult.
        tool_start_times: dict[str, float] = {}
        tool_call_count = 0
        total_tool_time_s = 0.0
        total_output_tokens = 0
        have_usage = False
        turn_usage: dict | None = None
        turn_cost_usd: float | None = None

        # A turn is only a genuine success if we actually observed a terminal
        # result message. Without this, a dead reader task (see
        # is_dead_connection_error) yields zero messages, no exception, and the
        # attempt falls through to ok=True with empty text — the player's
        # action vanishes with nothing visibly wrong. Confirmed to have
        # happened once in real play.
        result_seen = False

        try:
            # query() is inside the guard on purpose: a dead connection can
            # surface on the WRITE side just as easily as on the read side
            # (CLIConnectionError, "Not connected. Call connect() first."). Left
            # outside, it escaped to run_turn's generic catch as an unclassified
            # error string, so the retry went back out on the same dead client
            # and the reconnect never fired.
            await self._client.query(prompt)

            async for message in self._client.receive_response():
                now = time.time()
                session_id = getattr(message, "session_id", None)
                if session_id:
                    self.session_id = session_id

                if isinstance(message, RateLimitEvent) or hasattr(message, "rate_limit_info"):
                    info = getattr(message, "rate_limit_info", None)
                    status = getattr(info, "status", None)
                    if status == "rejected":
                        rl_type = getattr(info, "rate_limit_type", None)
                        error = f"rate_limit_rejected:{rl_type}"
                        break

                if isinstance(message, AssistantMessage) or hasattr(message, "content"):
                    msg_error = getattr(message, "error", None)
                    if msg_error:
                        error = f"assistant_error:{msg_error}"
                        break
                    for block in getattr(message, "content", []):
                        text = getattr(block, "text", None)
                        if isinstance(text, str) and text.strip():
                            chunks.append(text)

                # --- diagnostic instrumentation (see comment above) ---
                try:
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, ToolUseBlock):
                                # Per-block try/except: one malformed ToolUseBlock
                                # in a multi-block message must not cost its
                                # sibling blocks their tool_call_started log.
                                try:
                                    tool_start_times[block.id] = now
                                    fields: dict = {"tool": block.name, "tool_use_id": block.id}
                                    if block.name == "Bash" and isinstance(block.input, dict):
                                        command = block.input.get("command")
                                        if isinstance(command, str):
                                            fields["command_prefix"] = command[:150]
                                    log_event("tool_call_started", **fields)
                                except Exception:  # noqa: BLE001 — never break a turn
                                    pass
                        usage = message.usage
                        if isinstance(usage, dict):
                            output_tokens = usage.get("output_tokens")
                            if isinstance(output_tokens, (int, float)):
                                total_output_tokens += output_tokens
                                have_usage = True
                    elif isinstance(message, UserMessage):
                        content = message.content
                        for block in content if isinstance(content, list) else []:
                            if isinstance(block, ToolResultBlock):
                                try:
                                    start = tool_start_times.pop(block.tool_use_id, None)
                                    elapsed = (now - start) if start is not None else None
                                    tool_call_count += 1
                                    if elapsed is not None:
                                        total_tool_time_s += elapsed
                                    log_event(
                                        "tool_call_finished",
                                        tool_use_id=block.tool_use_id,
                                        is_error=block.is_error,
                                        elapsed_s=elapsed,
                                    )
                                except Exception:  # noqa: BLE001 — never break a turn
                                    pass
                except Exception:  # noqa: BLE001 — diagnostics must never break a turn
                    pass
                # --- end diagnostic instrumentation ---

                if isinstance(message, ResultMessage) or hasattr(message, "terminal_reason"):
                    reason = getattr(message, "terminal_reason", None)
                    if getattr(message, "is_error", False):
                        status_code = getattr(message, "api_error_status", None)
                        if status_code == 429:
                            error = f"rate_limit: api_error_status={status_code}"
                        elif status_code is not None:
                            error = f"result_error: api_error_status={status_code}"
                        else:
                            error = "result_error"
                        break
                    # A genuine, non-error terminal message: this attempt
                    # really did reach the end of a turn. Deliberately the SAME
                    # duck-typed condition as the branch above (isinstance OR
                    # terminal_reason attribute) — a stricter isinstance check
                    # would reject perfectly valid terminal messages that only
                    # duck-type as ResultMessage.
                    result_seen = True
                    turn_usage, turn_cost_usd = self._diff_usage(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — iteration itself can fail
            # The `async for` iteration (not just the per-message body) can
            # raise when the SDK's background reader task dies — the real
            # incident was a bare Exception carrying "Failed to decode JSON:
            # JSON message exceeded maximum buffer size of 1048576 bytes".
            # Report it as a structured, classifiable error instead of letting
            # it propagate into run_turn's generic catch, where it was
            # indistinguishable from any other failure and got retried on the
            # same, now-dead client.
            error = f"{TRANSPORT_ERROR_PREFIX}{type(exc).__name__}: {exc}"

        try:
            breakdown_fields: dict = {
                "tool_call_count": tool_call_count,
                "total_tool_time_s": total_tool_time_s,
            }
            if have_usage:
                # Approximation, kept for continuity: sums output_tokens off
                # AssistantMessage.usage only. The arithmetic is right (those
                # are per-message, not cumulative) but it has known blind
                # spots — it misses task-progress/notification messages and
                # silently drops any AssistantMessage without a populated
                # usage. turn_usage/turn_cost_usd below are the accurate
                # figures; this stays as a cross-check, not a replacement.
                breakdown_fields["total_output_tokens"] = total_output_tokens
            if turn_usage is not None:
                breakdown_fields["turn_usage"] = turn_usage
            if turn_cost_usd is not None:
                breakdown_fields["turn_cost_usd"] = turn_cost_usd
            log_event("turn_tool_breakdown", **breakdown_fields)
        except Exception:  # noqa: BLE001 — diagnostics must never break a turn
            pass

        if error is not None:
            return TurnResult(
                text="\n".join(chunks).strip(), ok=False, error=error, terminal_reason=reason
            )

        if not result_seen:
            # The stream ended without a terminal result and without raising:
            # the signature of a retry issued on a client whose reader task is
            # already dead. Never report this as a success — that is exactly
            # how a turn used to silently produce nothing at all.
            return TurnResult(
                text="\n".join(chunks).strip(),
                ok=False,
                error=NO_RESULT_ERROR,
                terminal_reason=reason,
            )

        return TurnResult(text="\n".join(chunks).strip(), ok=True, terminal_reason=reason)

    def _diff_usage(self, message) -> tuple[dict | None, float | None]:
        """Per-turn usage/cost from a terminal ResultMessage.

        `ResultMessage.usage` and `.total_cost_usd` are cumulative for the
        whole persistent session, so the per-turn figure is (new - snapshot),
        with the snapshot advanced afterwards. A negative diff means the
        session's counters were reset underneath us (conversation reset, or a
        reconnect onto a fresh session), in which case the raw new value IS
        the turn's own usage. Never raises: accounting must not break a turn.
        """
        turn_usage: dict | None = None
        turn_cost: float | None = None
        try:
            usage = getattr(message, "usage", None)
            if isinstance(usage, dict):
                diffed: dict = {}
                snapshot: dict = {}
                for key, value in usage.items():
                    # Skip non-numeric entries (nested cache/server-tool dicts,
                    # strings) — they aren't meaningfully diffable.
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        continue
                    previous = self._last_usage_snapshot.get(key, 0)
                    if not isinstance(previous, (int, float)) or isinstance(previous, bool):
                        previous = 0
                    delta = value - previous
                    diffed[key] = value if delta < 0 else delta
                    snapshot[key] = value
                turn_usage = diffed
                self._last_usage_snapshot = snapshot

            cost = getattr(message, "total_cost_usd", None)
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                delta_cost = cost - self._last_cost_snapshot
                turn_cost = cost if delta_cost < 0 else delta_cost
                self._last_cost_snapshot = float(cost)
        except Exception:  # noqa: BLE001 — accounting must never break a turn
            return turn_usage, turn_cost
        return turn_usage, turn_cost

    async def run_turn(self, prompt: str) -> TurnResult:
        attempts = max(1, self.cfg.turn_retries + 1)
        last_error = "unknown"

        for attempt in range(attempts):
            try:
                if self._client is None:
                    # Self-heal. start() is otherwise called exactly once, at
                    # engine boot (engine/main.py) — nothing re-runs it per
                    # turn. So if a previous turn's reconnect failed and left no
                    # client, without this the agent would stay dead for the
                    # whole rest of the process, failing every player action
                    # until someone restarted the stack by hand. Timeout-guarded
                    # like the attempt itself so a hung connect() can't stall the
                    # loop; a failure here is just this attempt's error.
                    await asyncio.wait_for(self.start(), timeout=self.cfg.turn_timeout_s)
                result = await asyncio.wait_for(
                    self._one_attempt(prompt), timeout=self.cfg.turn_timeout_s
                )
            except asyncio.TimeoutError:
                last_error = f"timeout after {self.cfg.turn_timeout_s}s"
            except Exception as exc:  # noqa: BLE001 — the loop must survive anything
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if result.ok:
                    return result
                last_error = result.error or "unknown"

            log_event("turn_attempt_failed", attempt=attempt + 1, error=last_error)
            if is_usage_limit_error(last_error):
                break

            # A dead transport is not retryable on the same client — its reader
            # task is gone, so the next attempt would drain an empty stream and
            # come back with nothing. Rebuild the connection first, reusing the
            # existing lifecycle methods. _options() carries resume=session_id,
            # so the rebuilt client continues the same Claude session.
            if is_dead_connection_error(last_error) and attempt + 1 < attempts:
                try:
                    await self.stop()
                    await self.start()
                    log_event("agent_reconnected", after_error=last_error[:200])
                except Exception as exc:  # noqa: BLE001 — never crash run_turn
                    # Whichever step failed, self._client must end up None, so
                    # that a LATER start() (this turn's caller, or the next
                    # turn) genuinely rebuilds the client instead of
                    # early-returning on a broken one:
                    #   * stop() failing at disconnect() — its own finally
                    #     already clears the slot;
                    #   * start() failing at connect() — start() discards the
                    #     unconnected instance rather than publishing it.
                    # The assignment below just makes that invariant local and
                    # unconditional. Retrying this turn on a None client would
                    # only raise AttributeError, so stop here and report the
                    # reconnect failure as this turn's error; the NEXT turn gets
                    # a clean rebuild attempt rather than a wedged agent.
                    self._client = None
                    last_error = f"reconnect_failed:{type(exc).__name__}: {exc}"
                    log_event("agent_reconnect_failed", error=last_error)
                    break

        return TurnResult(ok=False, error=last_error)
