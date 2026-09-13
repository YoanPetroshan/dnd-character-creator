"""Fire-and-forget TTS pre-warm for the display's narration audio.

After a successful turn, the narration text is already known here — several
seconds before the player clicks the display's speaker button. This module
POSTs that text to the display's existing `/tts` endpoint ahead of time so the
synthesis is already cached by the time the click happens, turning a multi-second
wait into an instant play.

Two hard constraints shape everything below:

1. **This must never be able to break, stall, or slow a turn.** Every public
   entry point swallows every exception and logs instead. `turn_loop` calls it
   un-awaited; a raise here would otherwise surface as an unretrieved-task
   warning at best and a broken turn at worst.

2. **The pre-warm key must match what the browser will later send**, or the
   cache never hits and we have merely doubled the synthesis load. The browser
   does not send the raw narration text — it sends the *rendered DOM's*
   `textContent`, put through `_ttsExtractText()`. `_browser_normalize()` below
   is a deliberate port of that render-then-extract pipeline; see its docstring
   for the exact correspondence. The display keeps a second, looser cache key as
   a safety net for any residual divergence, but the intent is that this
   function reproduces the browser string exactly.

This module deliberately does not import anything from `skills/dnd/` — it talks
to the display over its documented HTTP API only, mirroring `engine/display.py`.
"""
from __future__ import annotations

import json
import queue
import re
import threading
import urllib.request

from engine.log import log_event
from engine.state import runtime_dir

# Matches skills/dnd/display/tts.py's MAX_TEXT_CHARS and the browser's
# _ttsExtractText() .slice(0, 2000). Kept as a literal rather than imported so
# this module stays free of any skills/dnd/ dependency.
MAX_TEXT_CHARS = 2000

# Overall timeout for the whole request (urllib.request.urlopen only takes a
# single timeout — there is no separate connect/read split without a custom
# opener, which isn't worth the complexity here). Bounded by measured local
# synthesis times (12-28s across the three models tried, see
# docs/tts-research.md) with headroom, and matching tts.py's own
# LOCAL_TIMEOUT — NOT the old 120s, which could stall engine shutdown: an
# in-flight asyncio.to_thread prewarm holds a thread in the default executor,
# and asyncio.run() joins that executor during its own teardown, so Ctrl-C
# right after a turn ends could hang for the full timeout.
PREWARM_TIMEOUT = 45.0

# Control characters and ANSI CSI remnants, mirroring the frontend's streaming
# cleanup (templates/index.html, the `_cleanStream` step). \t becomes two
# spaces there, not one — reproduced below.
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_CSI = re.compile(r"\[[\d;?]*[a-zA-Z]")
_WS = re.compile(r"\s+")


def _strip_inline_md(line: str) -> str:
    """Port of `_mdParseInline()` (templates/index.html), text-content only.

    The frontend turns `**x**` into a `<strong>` element and `*x*` into an
    `<em>` element; the delimiters themselves are consumed and never become
    text nodes, so from `textContent`'s point of view the transformation is
    simply "drop the delimiters". An *unterminated* delimiter is pushed as a
    literal character instead — that asymmetry is real and reproduced here,
    because narration legitimately contains lone asterisks.

    Deliberately handles ONLY `**` and `*`. The real `_mdParseInline` has no
    backtick or underscore branch — an earlier draft of this work assumed it
    did, which would have silently corrupted the cache key for any narration
    containing an underscore.
    """
    out: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "*" and i + 1 < n and line[i + 1] == "*":
            end = line.find("**", i + 2)
            if end == -1:
                out.append(line[i])
                i += 1
                continue
            out.append(line[i + 2:end])
            i = end + 2
            continue
        if line[i] == "*":
            end = line.find("*", i + 1)
            if end == -1:
                out.append(line[i])
                i += 1
                continue
            out.append(line[i + 1:end])
            i = end + 1
            continue
        out.append(line[i])
        i += 1
    return "".join(out)


def _browser_normalize(text: str, npc_name: str | None = None) -> str:
    """Reproduce the exact string the browser's `_ttsExtractText()` will send.

    The pipeline being reproduced, for a DM narration block:

        item.text.split('\\n').forEach(line => {
          const p = document.createElement('p');
          _appendInlineSegments(p, _mdParse(line));   // per-line: inline md only
          block.appendChild(p);
        });

    then

        (clone.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 2000)

    Two non-obvious consequences, both of which cost real cache hits if missed:

    * `textContent` of `<p>a</p><p>b</p>` is `"ab"`, **not** `"a b"` — sibling
      elements introduce no separator. Joining lines with a space here (the
      naive reading) diverges on every multi-line turn, which is to say almost
      every turn.
    * Lines are **not** individually trimmed on the DM path, so a line's
      trailing spaces survive into `textContent` and are only collapsed by the
      final `\\s+` pass. Trimming per line here would diverge wherever a line
      ends in whitespace.

    `_mdParse(line)` is called with a single line, so its table branch (which
    needs a header *and* a separator line) can never fire; it degrades to
    `_mdParseInline`, which is what `_strip_inline_md` ports.

    Third consequence, and the reason the DM branch below drops the last line
    entirely: on the browser's *live* typewriter path (as opposed to
    `renderReplay`), `flushNewBlock()` runs before `_addTtsBar()` calls
    `_ttsExtractText()`, and `flushNewBlock()` removes `currentCursor` — the
    block's LAST `<p>` — before extraction happens. So the final line of a
    fresh narration is never actually part of what the browser sends to
    `/tts`. This was verified by replaying the full server-clean -> JS-clean
    -> `_mdParse` -> typewriter -> `flushNewBlock` -> `_ttsExtractText` chain
    against real campaign narration: every miss was an entry not ending in a
    trailing newline (i.e. one whose last "line" was real content, not an
    empty string from a trailing `\\n`).

    This makes the port correct for FRESH turns — which is all `prewarm_tts`
    ever targets, since prewarm only fires right after a turn completes — but
    it is deliberately wrong for `renderReplay` (which keeps every `<p>`, no
    `flushNewBlock`). That divergence is an accepted trade-off: prewarm never
    runs against replayed history, and the cache TTL is short (30 min), so a
    stale/incorrect prewarm for a replay-only scenario isn't worth the
    complexity of branching this function on caller intent.

    The NPC branch is different in the frontend — it trims each line, skips
    blank lines, and prepends a `div.npc-name` whose text lands in
    `textContent` — and is reproduced faithfully when `npc_name` is given.
    """
    s = _CTRL.sub("", text or "")
    s = _CSI.sub("", s)
    s = s.replace("\r", "").replace("\t", "  ")

    if npc_name:
        # NPC path: per-line .trim(), blank lines skipped, speaker name first.
        # renderNPCBlock() (templates/index.html) assigns p.textContent =
        # trimmed directly — it never calls _mdParseInline/_mdParse for NPC
        # lines, unlike the DM path. So inline markdown delimiters are NOT
        # stripped here; doing so would diverge from the browser's actual
        # textContent for any NPC line containing a literal `*`.
        body = "".join(
            ln.strip() for ln in s.strip().split("\n") if ln.strip()
        )
        body = npc_name + body
    else:
        # DM path: every line becomes a <p>, untrimmed; blanks contribute "".
        # Drop the last line: on a live turn, flushNewBlock() removes it as
        # `currentCursor` before _ttsExtractText() ever reads textContent —
        # see the docstring above for the measured justification.
        lines = s.split("\n")[:-1]
        body = "".join(_strip_inline_md(ln) for ln in lines)

    return _WS.sub(" ", body).strip()[:MAX_TEXT_CHARS]


def _read_token() -> str:
    """Read the display's auth token.

    Mirrors `engine/display.py::_read_token()` exactly, including its
    deliberately broad except: a token file that isn't valid UTF-8 raises
    UnicodeDecodeError (a ValueError, *not* an OSError) from `.read_text()`,
    and this must never propagate into a turn.
    """
    try:
        return (runtime_dir() / ".token").read_text().strip()
    except Exception:
        return ""


def prewarm_tts(text: str, display_port: int, voice: str | None = None) -> bool:
    """POST narration text to the display's /tts endpoint to warm its cache.

    Returns True if the display accepted the request, False on any failure.
    Never raises.

    The `prewarm: true` flag is load-bearing on the display side: it selects a
    separate, higher rate-limit bucket so these calls cannot exhaust the real
    player's budget — and, just as importantly, so the player's browser (also
    loopback, also token-authenticated, therefore indistinguishable by address
    or credentials alone) stays fully rate-limited. It is an explicit opt-in to
    a *different bounded* budget, not a bypass.
    """
    try:
        normalized = _browser_normalize(text)
        if not normalized:
            return False

        payload: dict[str, object] = {"text": normalized, "prewarm": True}
        if voice:
            payload["voice"] = voice
        data = json.dumps(payload).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        token = _read_token()
        if token:
            headers["X-DND-Token"] = token

        req = urllib.request.Request(
            f"http://localhost:{display_port}/tts",
            data=data,
            headers=headers,
            method="POST",
        )
        # The response body is the synthesized audio; we want it cached on the
        # display, not here. Read and discard so the connection closes cleanly
        # rather than being reset mid-transfer.
        with urllib.request.urlopen(req, timeout=PREWARM_TIMEOUT) as resp:
            resp.read()
            cache = resp.headers.get("X-Audio-Cache")
            log_event("tts_prewarm", cache=cache, chars=len(normalized))
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception as exc:
        # Deliberately broad, matching display.notify_thinking(): urllib raises
        # URLError/HTTPError for the network cases, but http.client.HTTPException
        # escapes unwrapped from a malformed local response, and the token read
        # or JSON encode could raise something else entirely. A pre-warm is pure
        # latency optimisation — every failure mode is "the player waits as long
        # as they do today", never a broken turn.
        log_event("tts_prewarm_failed", error=str(exc))
        return False


# ── Serial pre-warm queue (streaming backend) ─────────────────────────────
#
# The local backend pushes narration to the display in several blocks per
# turn instead of one, and the player's speaker button warms one block at a
# time -- so pre-warming has to follow the same shape or it warms cache keys
# nobody asks for (see _browser_normalize above for why the key must match
# exactly).
#
# Strictly serial, and strictly one worker: local TTS on this machine runs
# slower than real time and shares the GPU with the model. Firing a thread
# per block would have several synthesis jobs competing with each other and
# with the next turn's generation -- turning a latency optimisation into a
# latency regression. A queue with a single consumer keeps the GPU doing one
# thing at a time, in the order the player will actually click.
_PREWARM_QUEUE: "queue.Queue" = queue.Queue(maxsize=64)
_PREWARM_WORKER: "threading.Thread | None" = None
_PREWARM_LOCK = threading.Lock()


def _prewarm_worker() -> None:
    while True:
        text, port, voice = _PREWARM_QUEUE.get()
        try:
            prewarm_tts(text, port, voice)
        except Exception as exc:  # noqa: BLE001 -- the worker must never die
            log_event("tts_prewarm_worker_error", error=str(exc))
        finally:
            _PREWARM_QUEUE.task_done()


def queue_prewarm(blocks: list[str], display_port: int, voice: str | None = None) -> int:
    """Queue narration blocks for background pre-warming, in order.

    Returns how many were accepted. Drops silently (and logs) when the queue
    is full rather than blocking: a backed-up synthesis queue must never
    stall the turn loop that fed it.
    """
    global _PREWARM_WORKER
    with _PREWARM_LOCK:
        if _PREWARM_WORKER is None or not _PREWARM_WORKER.is_alive():
            _PREWARM_WORKER = threading.Thread(
                target=_prewarm_worker, name="tts-prewarm", daemon=True
            )
            _PREWARM_WORKER.start()

    accepted = 0
    for block in blocks:
        if not (block or "").strip():
            continue
        try:
            _PREWARM_QUEUE.put_nowait((block, display_port, voice))
            accepted += 1
        except queue.Full:
            log_event("tts_prewarm_queue_full", dropped=len(blocks) - accepted)
            break
    return accepted
