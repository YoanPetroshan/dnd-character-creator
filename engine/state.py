"""Read/write access to the runtime queue and campaign markdown files."""
from __future__ import annotations

import json
import re
from pathlib import Path

from engine.config import campaign_root

_FLAG_RE = re.compile(r"^([a-zA-Z0-9_]+):\s*(.+?)\s*$")
# The character sheet's own top-level heading, e.g. "# Sylwen Nightbrook".
# `#` followed by whitespace, so "## Section" can never match.
_SHEET_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")


def runtime_dir() -> Path:
    d = campaign_root() / ".runtime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def active_campaign() -> str | None:
    f = runtime_dir() / ".campaign"
    if not f.exists():
        return None
    name = f.read_text().strip()
    return name or None


def campaign_dir(name: str) -> Path:
    return campaign_root() / "campaigns" / name


def take_input_queue() -> str:
    f = runtime_dir() / ".input_queue"
    if not f.exists():
        return ""
    try:
        content = f.read_text()
    except OSError:
        return ""
    try:
        f.unlink()
    except OSError:
        pass
    return content.strip()


def text_log_count() -> int:
    f = runtime_dir() / "text_log.json"
    if not f.exists():
        return 0
    try:
        data = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return 0
    return len(data) if isinstance(data, list) else 0


def text_log_fingerprint(tail: int = 3) -> tuple[int, str]:
    """Identity of the display's text log, not just its length.

    The display persists `_text_log` as a deque(maxlen=60), so once an evening
    of play saturates it, `len(after) > len(before)` can never be true again —
    a length comparison would report "the agent never pushed" on every
    subsequent turn and double-push the narration. Comparing the last few
    entries instead keeps working after saturation: a genuine push always
    changes the newest entries, whether or not the count moves.
    """
    f = runtime_dir() / "text_log.json"
    if not f.exists():
        return (0, "")
    try:
        data = json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return (0, "")
    if not isinstance(data, list):
        return (0, "")
    newest = data[-max(1, tail):]
    return (len(data), json.dumps(newest, ensure_ascii=False, sort_keys=True))


def _section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.strip().startswith("## "):
            inside = line.strip().lower() == f"## {heading}".lower()
            continue
        if inside:
            out.append(line)
    return out


def session_flags(campaign: str) -> dict[str, str]:
    f = campaign_dir(campaign) / "state.md"
    if not f.exists():
        return {}
    flags: dict[str, str] = {}
    for line in _section(f.read_text(errors="replace"), "Session Flags"):
        m = _FLAG_RE.match(line.strip())
        if m:
            flags[m.group(1)] = m.group(2)
    return flags


def set_session_flag(campaign: str, key: str, value: str) -> None:
    f = campaign_dir(campaign) / "state.md"
    text = f.read_text(errors="replace") if f.exists() else "## Session Flags\n"
    # Check if header exists using the same logic as the loop below
    has_header = any(line.strip().lower() == "## session flags" for line in text.splitlines())
    if not has_header:
        text = text.rstrip() + "\n\n## Session Flags\n"

    lines = text.splitlines()
    out: list[str] = []
    inside = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if inside and not replaced:
                out.append(f"{key}: {value}")
                replaced = True
            inside = stripped.lower() == "## session flags"
            out.append(line)
            continue
        if inside and stripped.startswith(f"{key}:"):
            out.append(f"{key}: {value}")
            replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f"{key}: {value}")
    f.write_text("\n".join(out).rstrip() + "\n")


def character_name(path: Path) -> str:
    """The character's REAL name, as written on their own sheet.

    The filename is a slug ("sylwen-nightbrook.md"); the name that actually
    appears in narration is the sheet's first `# ` heading
    ("# Sylwen Nightbrook"). Deriving the name from the slug produced
    "Sylwen-Nightbrook", which never matches the narration — that broke both
    the PC-autoroll guard's name matching and the party list in the DM's own
    turn prompt. Falls back to a space-joined slug for a malformed sheet.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for line in text.splitlines():
        m = _SHEET_HEADING_RE.match(line.strip())
        if m and m.group(1).strip():
            return m.group(1).strip()
    return " ".join(part.capitalize() for part in path.stem.split("-"))


def party_names(campaign: str) -> list[str]:
    d = campaign_dir(campaign) / "characters"
    if not d.exists():
        return []
    return [character_name(path) for path in sorted(d.glob("*.md"))]


def state_header(campaign: str, max_chars: int = 4000) -> str:
    f = campaign_dir(campaign) / "state.md"
    if not f.exists():
        return ""
    text = f.read_text(errors="replace")
    live = "\n".join(line for line in _section(text, "Live State Flags") if line.strip())
    header = f"## Живо състояние на света\n{live}".strip()
    return header[:max_chars]
