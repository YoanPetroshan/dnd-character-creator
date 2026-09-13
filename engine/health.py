"""Engine liveness signal and graceful pausing."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from engine import display
from engine.log import log_event
from engine.state import runtime_dir

# The pause is served from a worker thread, which makes it invisible to the
# event loop's signal handling: nothing can cancel a monolithic sleep. Waking
# up this often to re-check the stop flag keeps Ctrl-C responsive without
# busy-waiting.
PAUSE_SLICE_S = 5


def heartbeat_path() -> Path:
    return runtime_dir() / "engine_heartbeat.json"


def read_heartbeat() -> dict:
    p = heartbeat_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def heartbeat(state: str) -> None:
    try:
        heartbeat_path().write_text(json.dumps({"state": state, "ts": time.time()}))
    except OSError:
        pass
    display.push(autorun_waiting="true" if state == "waiting" else "false")


def pause_for_usage_limit(
    seconds: int,
    message: str,
    should_stop: Callable[[], bool] | None = None,
    slice_s: float = PAUSE_SLICE_S,
) -> bool:
    """Wait out a subscription limit, in slices, so shutdown stays responsive.

    The 5-minute pause runs in a worker thread (see turn_loop.run_once), which
    makes it uninterruptible by a signal — the handlers only set stop_event.
    With one monolithic sleep, Ctrl-C was silently ignored for up to five
    minutes. Sleeping in slices and checking the caller's stop predicate
    between them bounds that to one slice.

    Returns True when the full pause elapsed, False when it was cut short.
    """
    log_event("usage_limit_pause", seconds=seconds)
    display.send_system(message)
    heartbeat("paused")

    remaining = max(0, seconds)
    step = max(0.01, slice_s)
    while remaining > 0:
        if should_stop is not None and should_stop():
            log_event("usage_limit_pause_interrupted", remaining=round(remaining, 1))
            return False
        this_slice = min(step, remaining)
        time.sleep(this_slice)
        remaining -= this_slice
    return True
