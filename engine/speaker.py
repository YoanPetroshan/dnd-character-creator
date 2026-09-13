"""Speak narration aloud in Bulgarian, through the display companion.

Anthropic's models have no Bulgarian TTS, so speech is synthesised locally
(BgTTS via `skills/dnd/display/tts.py`). That synthesis lives in the display
companion, which already owns a browser tab, a synthesis cache, chunked
local streaming and voice selection — so the display is also where narration
is spoken. The engine POSTs narration to its `/speak` endpoint and forgets
about it; nothing about synthesis, ordering or playback lives here.

This used to point at a second Flask process (`dnd-mcp/audio/`, on :5057,
with its own SSE channel and its own browser tab) that called into that very
same tts.py. Folding it into the display removed a process, a port and a
tab, and let live narration share the cache the per-block speaker button
fills.

Two consequences of the endpoint's design are worth stating:

* `/speak` only *queues* text — synthesis happens when the browser fetches
  the audio — so the POST returns fast and cannot stall a turn on synthesis.
* The display runs the sentence buffer, so it is safe to feed it the same
  partial-paragraph chunks the display's text pane gets. Text split
  mid-sentence is joined with the next chunk rather than spoken as a
  fragment.

Everything here is best-effort: a display that isn't running, is slow, or
errors must cost the table its audio and nothing else. No exception from
this module ever reaches a turn.
"""
from __future__ import annotations

import json
import queue
import threading
import urllib.error
import urllib.request

from engine.log import log_event
from engine.state import runtime_dir

DEFAULT_SPEAKER_PORT = 5001
# The POST only enqueues text (see the module docstring), so this bounds a
# hung or wedged display rather than a synthesis run.
REQUEST_TIMEOUT_S = 5.0

_QUEUE: "queue.Queue" = queue.Queue(maxsize=128)
_WORKER: "threading.Thread | None" = None
_LOCK = threading.Lock()


def resolve_url(configured: str | None, display_port: int = DEFAULT_SPEAKER_PORT) -> str:
    """Where to POST narration.

    An empty `local_speaker_url` — the default — means "wherever the display
    is", so the two can never drift apart when the display port is changed.
    An explicit value still wins, for a setup that puts speech elsewhere.
    """
    configured = (configured or "").strip()
    return configured or f"http://127.0.0.1:{display_port}"


def _read_token() -> str:
    """The display's LAN token, or "" when it isn't running in LAN mode.

    Deliberately broad: a missing file raises OSError but a half-written or
    non-UTF-8 one raises ValueError, and neither may reach a turn.
    """
    try:
        return (runtime_dir() / ".token").read_text().strip()
    except Exception:  # noqa: BLE001
        return ""


def _post_speak(text: str, base_url: str) -> bool:
    data = json.dumps({"text": text}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = _read_token()
    if token:
        headers["X-DND-Token"] = token
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/speak", data=data, headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, OSError) as exc:
        # By far the most common case is "the display isn't running", which
        # is a perfectly normal way to play — silent, not broken.
        log_event("speaker_unavailable", error=str(exc))
        return False
    except Exception as exc:  # noqa: BLE001 -- audio must never break a turn
        log_event("speaker_failed", error=str(exc))
        return False


def _worker() -> None:
    while True:
        text, base_url = _QUEUE.get()
        try:
            _post_speak(text, base_url)
        except Exception as exc:  # noqa: BLE001 -- the worker must never die
            log_event("speaker_worker_error", error=str(exc))
        finally:
            _QUEUE.task_done()


def speak(text: str, base_url: str | None = None) -> bool:
    """Queue `text` to be spoken. Returns False if it was not accepted.

    Ordering matters — this is narration being read aloud — so a single
    worker drains the queue in submission order. Never blocks the caller:
    a full queue drops the text and logs rather than stalling the turn that
    produced it.
    """
    if not (text or "").strip():
        return False
    target = resolve_url(base_url)

    global _WORKER
    with _LOCK:
        if _WORKER is None or not _WORKER.is_alive():
            _WORKER = threading.Thread(target=_worker, name="bg-speaker", daemon=True)
            _WORKER.start()

    try:
        _QUEUE.put_nowait((text, target))
        return True
    except queue.Full:
        log_event("speaker_queue_full", chars=len(text))
        return False


def is_available(base_url: str | None = None) -> bool:
    """True if the speech host answers. Used for a startup notice only —
    never as a gate, since the display can be started mid-session."""
    target = resolve_url(base_url)
    try:
        req = urllib.request.Request(f"{target.rstrip('/')}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            resp.read()
        return True
    except Exception:  # noqa: BLE001
        return False
