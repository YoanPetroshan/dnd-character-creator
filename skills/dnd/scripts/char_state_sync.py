#!/usr/bin/env python3
"""char_state_sync.py — the two things that must happen after every YAML
mutation: push the change to the live display (never breaks the caller if
the display is down, matching engine/tts_trigger.py's established
doctrine) and regenerate the human-readable markdown view.

Wire-format note (2026-08-17, Task 6): the brief this module was built
from sketched `push_to_display`'s payload as `{"players": {name: {...}}}`
— a dict keyed by character name. The REAL `/stats` route
(skills/dnd/display/dnd-display-app.py, ~line 1548) does
`for incoming in data["players"]: name = incoming.get("name")`, which
requires `players` to be a LIST of per-player dicts, matching exactly what
`send.py::_build_stats_payload()` builds (`{"players": list(players.values())}`,
around line 365). A dict payload would not raise on the display side in an
obviously-visible way — `incoming` would just be a string key with no
`.get()` — but would 500 out of the route silently as far as this module's
caller is concerned (push_to_display's broad except still returns False,
so the "never raises" contract holds, but the display would never actually
update). Fixed here to send a list, per the real route and send.py's own
established payload shape. `_validate_payload()` in send.py encodes the
same rule (`"players" is not a list` is a validation issue), which
corroborates this reading.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import paths  # noqa: E402
import char_state_derive as derive  # noqa: E402
from char_state_schema import (  # noqa: E402
    Character, atomic_write_text, character_markdown_path, save_character,
)


def _read_token() -> str:
    """Mirrors engine/tts_trigger.py::_read_token()'s exact contract:
    read `.token` from the runtime dir, strip it, and swallow every
    exception (missing file, bad encoding, permissions) as an empty
    string rather than ever raising."""
    try:
        return (paths.runtime_dir() / ".token").read_text().strip()
    except Exception:
        return ""


def push_to_display(character: Character, campaign: str, display_port: int = 5001) -> bool:
    """POST this character's stats to the display's /stats route, in the
    same payload shape send.py's --stat-* flags already build (a `players`
    LIST of per-player dicts — see module docstring for why this isn't a
    dict keyed by name). Never raises — a down display must never block a
    state mutation from being saved to the canonical YAML."""
    payload = {
        "players": [
            {
                "name": character.name,
                "hp": {
                    "current": character.combat.hp_current,
                    "max": character.combat.hp_max,
                    "temp": character.combat.hp_temp,
                },
            }
        ]
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        token = _read_token()
        if token:
            headers["X-DND-Token"] = token
        req = urllib.request.Request(
            f"http://localhost:{display_port}/stats", data=data, headers=headers, method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            # The route returns "", 204 on a normal successful update (and
            # on a couple of no-op early-outs) — 200 is never actually sent
            # for /stats, so the success check must accept the full 2xx
            # range, not assume 200 specifically.
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


# Ordinal labels for the Spell Slots table's Level column. session_recap.py's
# _LEVEL_TOKENS maps exactly these back to bare level numbers.
_SLOT_LEVEL_LABEL = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
    6: "6th", 7: "7th", 8: "8th", 9: "9th",
}


def _hit_dice_text(character: Character) -> str:
    """Render hit dice as session_recap.py's parser expects:
    `**Hit Dice:** 3d8 (remaining: 2)`.

    HitDieUsage stores only `used`, so the pool size comes from the matching
    class's level (a class of level N has N hit dice).
    """
    parts = []
    for hd in character.combat.hit_dice:
        total = next(
            (c.level for c in character.classes
             if c.cls.strip().lower() == hd.cls.strip().lower()),
            hd.used,
        )
        parts.append(f"{total}d{hd.die} (remaining: {max(0, total - hd.used)})")
    return ", ".join(parts)


def render_markdown(character: Character, ruleset: str = "2014") -> str:
    """Render the human-readable .md view of a character.

    Field formats here are NOT free choices: session_recap.py's
    parse_character_sheet() regex-scrapes this exact file to build its
    per-session state diffs. Level, hit dice, death saves, exhaustion,
    inspiration, conditions and the spell-slots table were all missing from
    this renderer, so every recap silently treated them as unchanged even
    when the YAML said otherwise. Any change to these labels must be made
    against session_recap.py's patterns, not by eye.
    """
    ac = derive.compute_ac(character, ruleset=ruleset)
    prof = derive.compute_proficiency_bonus(character)
    class_line = ", ".join(f"{c.cls}" + (f" ({c.subclass})" if c.subclass else "") + f" {c.level}" for c in character.classes)
    conditions = ", ".join(character.conditions.active) if character.conditions.active else "none"
    lines = [
        f"# {character.name}",
        f"<!-- GENERATED by char_state.py — do not hand-edit. Source of truth: {character.name.lower().replace(' ', '-')}.yaml -->",
        "",
        f"**Race:** {character.race} | **Class:** {class_line} | "
        f"**Level:** {derive.total_level(character)} | **Background:** {character.background}",
        f"**Alignment:** {character.alignment}",
        "",
        "## Combat Stats",
        f"- **HP:** {character.combat.hp_current} / {character.combat.hp_max} | **Temp HP:** {character.combat.hp_temp}",
        f"- **AC:** {ac} | **Speed:** {character.combat.speed} ft | **Proficiency Bonus:** +{prof}",
    ]
    hit_dice = _hit_dice_text(character)
    if hit_dice:
        lines.append(f"- **Hit Dice:** {hit_dice}")
    lines += [
        f"- **Death Saves:** Successes: {character.combat.death_saves.successes} "
        f"| Failures: {character.combat.death_saves.failures}",
        f"- **Exhaustion:** {character.conditions.exhaustion} | "
        f"**Inspiration:** {'yes' if character.conditions.inspiration else 'no'}",
        # Must be the last thing on its line — session_recap's Conditions
        # pattern captures to end-of-line.
        f"- **Conditions:** {conditions}",
        "",
        "## Ability Scores",
        "| STR | DEX | CON | INT | WIS | CHA |",
        "|-----|-----|-----|-----|-----|-----|",
        f"| {character.ability_scores.STR} | {character.ability_scores.DEX} | {character.ability_scores.CON} "
        f"| {character.ability_scores.INT} | {character.ability_scores.WIS} | {character.ability_scores.CHA} |",
        "",
    ]

    if character.spell_slots or character.pact_magic_slots:
        lines += [
            "## Spell Slots",
            "",
            "| Level | Total | Used |",
            "|-------|-------|------|",
        ]
        for lvl in sorted(character.spell_slots):
            pool = character.spell_slots[lvl]
            label = _SLOT_LEVEL_LABEL.get(lvl, str(lvl))
            lines.append(f"| {label} | {pool.max} | {pool.used} |")
        if character.pact_magic_slots:
            # Deliberately NOT a table row: session_recap's row parser would
            # mangle "Pact" into a bogus slot level.
            pact = character.pact_magic_slots
            lines.append("")
            lines.append(f"**Pact Magic:** {pact.used} / {pact.max} used")
        lines.append("")

    lines.append("## Equipment & Inventory")
    for item in character.equipment:
        lines.append(f"- {item.name}" + (" (equipped)" if item.equipped else "") + (f" x{item.quantity}" if item.quantity > 1 else ""))
    for item in character.misc_items:
        lines.append(f"- {item.name}" + (f" x{item.quantity}" if item.quantity > 1 else "") + (f" — {item.note}" if item.note else ""))
    lines.append(f"- **Currency:** {character.currency.gp}gp {character.currency.sp}sp {character.currency.cp}cp")
    lines += ["", "## Backstory & Notes", character.backstory]
    return "\n".join(lines) + "\n"


def write_all(campaign: str, slug: str, character: Character, ruleset: str = "2014", display_port: int = 5001) -> bool:
    """Persist the character everywhere, then push to the display.

    Returns whether the DISPLAY PUSH succeeded. A failed push is never an
    error — a down display must never block a real state save (an existing
    Global Constraint) — but the caller needs to know so it can say the panel
    may be stale instead of reporting a clean success. Both file writes are
    atomic; if either raises, that IS a real failure and propagates.
    """
    save_character(campaign, slug, character)
    atomic_write_text(
        character_markdown_path(campaign, slug),
        render_markdown(character, ruleset=ruleset),
    )
    return push_to_display(character, campaign=campaign, display_port=display_port)
