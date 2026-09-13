"""Append-only JSONL event log for the engine."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from engine.state import runtime_dir


def log_path() -> Path:
    return runtime_dir() / "engine.log"


def log_event(event: str, **fields: Any) -> None:
    record = {"ts": time.time(), "event": event}
    record.update(fields)
    try:
        with log_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def read_events(limit: int = 50) -> list[dict]:
    p = log_path()
    if not p.exists():
        return []
    events: list[dict] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events[-limit:]
