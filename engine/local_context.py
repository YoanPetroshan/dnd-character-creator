"""Deterministic context gathering for the local-model backend.

DMAgent lets Claude read whatever campaign files it wants via the Bash/Read
tools, on its own judgment, each turn. A 4B local model can't be trusted to
do that kind of open-ended exploration reliably, so this module does it in
plain Python instead: pull the same handful of facts a human DM would keep
in their head, and hand them to the model pre-assembled.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from engine.state import campaign_dir, character_name, runtime_dir

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
_ROOM_HEADING_RE = re.compile(r"^#{1,4}\s+([A-Za-z]?\d+)[.\s]")
_HP_RE = re.compile(r"(\*\*HP:\*\*\s*)(-?\d+)(\s*/\s*)(\d+)")
_ROOM_CODE_RE = re.compile(r"\b([A-Za-z]\d{1,3})\b")


def _state_text(campaign: str) -> str:
    f = campaign_dir(campaign) / "state.md"
    return f.read_text(errors="replace") if f.exists() else ""


def state_section(campaign: str, heading: str, max_chars: int = 1500) -> str:
    """Full text of one top-level ("## Heading") section of state.md."""
    text = _state_text(campaign)
    lines = text.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        m = _SECTION_RE.match(line)
        if m:
            inside = m.group(1).strip().casefold() == heading.casefold()
            continue
        if inside:
            out.append(line)
    body = "\n".join(out).strip()
    return body[:max_chars]


def arc_pointer(campaign: str) -> dict | None:
    """Parse the ```yaml fenced block under "## Campaign Arc", if present.

    Covers both the structured (imported-module) and dynamic/sandbox arc
    shapes; callers should treat missing keys as "not available" rather than
    assuming the structured shape.
    """
    text = _state_text(campaign)
    m = re.search(r"##\s+Campaign Arc\s*\n```ya?ml\s*\n(.*?)\n```", text, re.DOTALL)
    if not m:
        return None
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


_NAMED_ROOM_CODE_RE = re.compile(r",\s*([A-Za-z]\d{1,3})\)")


def _room_codes_in(text: str) -> list[str]:
    """Room codes mentioned in `text`, most-likely-current first.

    State prose tends to write the room the party is actually IN as
    "(the Patio, M2)" — a name followed by a comma and the code — and a
    room merely referenced in passing (seen through a door, remembered from
    earlier) as a bare "(M1)". Preferring the comma form first is what keeps
    "left hallway off the Foyer (M1), at the first door (the Patio, M2)"
    from matching the Foyer the party is walking past instead of the Patio
    they've actually stopped at.
    """
    text = text or ""
    named = _NAMED_ROOM_CODE_RE.findall(text)
    bare = _ROOM_CODE_RE.findall(text)
    seen: set[str] = set()
    ordered: list[str] = []
    for code in named + bare:
        key = code.upper()
        if key not in seen:
            seen.add(key)
            ordered.append(code)
    return ordered


def chapter_excerpt(campaign: str, max_chars: int = 3000) -> str:
    """The current room/scene's text from the module source file, if the
    campaign has one. Falls back to the arc pointer's own summary fields
    (title/key_beats/telegraph_scene) when there's no source file, no room
    code, or the room heading can't be found — never raises, worst case
    returns an empty string and the turn proceeds on state alone.
    """
    arc = arc_pointer(campaign)
    if not arc:
        return ""
    detail = arc.get("current_chapter_detail") or {}
    source_ref = detail.get("source_ref")
    location = detail.get("location", "") or ""
    situation = state_section(campaign, "Current Situation")

    fallback_parts = []
    if detail.get("title"):
        fallback_parts.append(f"Глава: {detail['title']}")
    if location:
        fallback_parts.append(f"Място: {location}")
    beats = detail.get("key_beats")
    if isinstance(beats, list) and beats:
        fallback_parts.append("Ключови моменти:\n" + "\n".join(f"- {b}" for b in beats))
    fallback = "\n".join(fallback_parts)

    if not source_ref:
        return fallback[:max_chars]

    src_path = campaign_dir(campaign) / source_ref
    if not src_path.exists():
        return fallback[:max_chars]

    text = src_path.read_text(encoding="utf-8", errors="replace")
    codes = _room_codes_in(situation) or _room_codes_in(location)
    if not codes:
        return fallback[:max_chars]

    lines = text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, code)
    for i, line in enumerate(lines):
        m = _ROOM_HEADING_RE.match(line)
        if m:
            level = len(line) - len(line.lstrip("#"))
            headings.append((i, level, m.group(1).upper()))

    for code in codes:
        for idx, (line_idx, level, room_code) in enumerate(headings):
            if room_code != code.upper():
                continue
            end = len(lines)
            for j in range(idx + 1, len(headings)):
                if headings[j][1] <= level:
                    end = headings[j][0]
                    break
            excerpt = "".join(lines[line_idx:end]).strip()
            if excerpt:
                return excerpt[:max_chars]
    return fallback[:max_chars]


def recent_narration_tail(campaign: str, n: int = 6, max_chars: int = 2000) -> str:
    """The last few things actually shown on the display, for continuity.

    Reads the same text_log.json the display itself maintains (and that
    engine.state.text_log_fingerprint() already keys off of) rather than
    session-log.md, which is a per-session summary written after the fact,
    not a turn-by-turn transcript.
    """
    f = runtime_dir() / "text_log.json"
    if not f.exists():
        return ""
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, list):
        return ""
    lines = []
    for entry in data[-n:]:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        if isinstance(text, str) and text.strip():
            lines.append(text.strip())
    return "\n".join(lines)[-max_chars:]


def party_line(campaign: str) -> str:
    """The one-line party roster already maintained by hand in state.md's
    Current Situation ("Name — race class level | HP x/y | AC z | ..."),
    reused as-is rather than re-derived from character sheets."""
    situation = state_section(campaign, "Current Situation")
    for line in situation.splitlines():
        stripped = line.strip()
        if stripped.startswith("- **Party:**") or stripped.startswith("**Party:**"):
            return stripped.split(":**", 1)[-1].strip()
    return ""


_QUEST_LINE_RE = re.compile(
    r"^\s*[-*]\s*\*\*(?P<name>.+?):?\*\*:?\s*(?P<body>.*?)\s*$"
)
# "— status: pending" / "- status: active", at the end of the line.
_QUEST_STATUS_RE = re.compile(r"[—–-]\s*status:\s*(?P<status>[A-Za-zА-Яа-я ]+)\s*$", re.I)
# state.md tracks progress with words the display's quest tracker doesn't
# know; it renders anything unrecognised in a washed-out "unknown" style.
_QUEST_STATUS_MAP = {
    "pending": "active",
    "in progress": "active",
    "active": "active",
    "open": "active",
    "done": "resolved",
    "complete": "resolved",
    "completed": "resolved",
    "resolved": "resolved",
    "failed": "failed",
    "lost": "failed",
    "threat": "threat",
}


def quests(campaign: str) -> list[dict]:
    """Quests from state.md's "## Active Quests", as the display's tracker
    wants them: [{"name", "status", "detail"}, ...].

    The section is prose the DM maintains by hand, so parsing is forgiving:
    a line that doesn't match the "- **Name:** description — status: x"
    shape is skipped rather than raising, and a line with no trailing
    status is kept as "active" (it's listed under *Active* Quests).

    `detail` is what makes the sidebar entry expandable — the descriptions
    already existed here, they just never reached the display, which is why
    the quest list was three names and nothing to click.
    """
    out: list[dict] = []
    for line in state_section(campaign, "Active Quests", max_chars=8000).splitlines():
        m = _QUEST_LINE_RE.match(line)
        if not m:
            continue
        name = m.group("name").strip()
        body = m.group("body").strip()
        if not name:
            continue
        status = "active"
        sm = _QUEST_STATUS_RE.search(body)
        if sm:
            status = _QUEST_STATUS_MAP.get(sm.group("status").strip().casefold(), "active")
            body = body[: sm.start()].strip()
        out.append({"name": name, "status": status, "detail": body.rstrip(" —–-")})
    return out


def character_sheet_path(campaign: str, name: str) -> Path | None:
    """The character .md file whose own "# Name" heading matches `name`
    case-insensitively — the same identity engine.state.party_names() uses,
    just inverted (name -> path instead of path -> name)."""
    d = campaign_dir(campaign) / "characters"
    if not d.exists():
        return None
    for path in sorted(d.glob("*.md")):
        if character_name(path).casefold() == name.strip().casefold():
            return path
    return None


def read_hp(campaign: str, name: str) -> tuple[int, int] | None:
    """(current, max) HP from a PC's own sheet, or None if either the sheet
    or its "**HP:** X / Y" Combat Stats line can't be found."""
    path = character_sheet_path(campaign, name)
    if path is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _HP_RE.search(text)
    if not m:
        return None
    return int(m.group(2)), int(m.group(4))


def apply_hp_delta(campaign: str, name: str, delta: int) -> tuple[int, int] | None:
    """Add `delta` (negative for damage, positive for healing) to a PC's HP,
    clamped to [0, max], and persist it back to their sheet.

    This is the one piece of world state this backend writes back at all,
    deliberately narrow: PC HP is numeric and safety-critical (a death save
    misfire is a real consequence), so it's worth the harness doing the
    arithmetic itself rather than trusting the model's. Everything else a PC
    sheet tracks (spell slots, inventory, conditions) stays untouched here —
    same as monster HP, which this project narrates rather than tracks
    numerically by design (see state.md's own DM Notes convention).

    Returns the new (current, max) on success, or None if the sheet/field
    couldn't be found (the caller logs this rather than crashing the turn).
    """
    path = character_sheet_path(campaign, name)
    if path is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _HP_RE.search(text)
    if not m:
        return None
    current, max_hp = int(m.group(2)), int(m.group(4))
    new_current = max(0, min(max_hp, current + delta))
    new_text = text[: m.start()] + f"{m.group(1)}{new_current}{m.group(3)}{max_hp}" + text[m.end() :]
    path.write_text(new_text, encoding="utf-8")
    return new_current, max_hp
