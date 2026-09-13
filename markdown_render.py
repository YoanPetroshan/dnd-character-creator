"""Fresh Markdown character-sheet renderer — takes a chargen.build() sheet
dict plus a sheet_derive.derive() dict, returns a Markdown string. Not a
port of dnd-app-bg-local's library.py::_render_markdown() (that function is
a fragile bridge into the play engine's char_state_sync module); this is a
self-contained renderer scoped to exactly what chargen + sheet_derive
produce.

Imports nothing outside the standard library.
"""
from __future__ import annotations


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _classes_line(sheet: dict) -> str:
    parts = []
    for c in sheet.get("classes") or []:
        piece = c.get("cls", "")
        if c.get("subclass"):
            piece += f" ({c['subclass']})"
        piece += f" {c.get('level', '')}"
        parts.append(piece.strip())
    return " / ".join(parts)


def render(sheet: dict, derived: dict) -> str:
    combat = sheet.get("combat") or {}
    scores = sheet.get("ability_scores") or {}
    mods = derived.get("ability_mods") or {}
    lines: list[str] = []

    lines.append(f"# {sheet.get('name', '')}")
    lines.append("")
    player = sheet.get("player") or "—"
    lines.append(f"**Player:** {player}  |  **Race:** {sheet.get('race', '')}  |  "
                 f"**Class:** {_classes_line(sheet)}  |  "
                 f"**Background:** {sheet.get('background', '')}  |  "
                 f"**Alignment:** {sheet.get('alignment', '')}")
    lines.append("")

    lines.append("## Combat")
    lines.append(f"- **HP:** {combat.get('hp_current', 1)} / {combat.get('hp_max', 1)}"
                 f" (temp {combat.get('hp_temp', 0)})")
    lines.append(f"- **AC:** {derived.get('ac', 10)}  |  "
                 f"**Initiative:** {_fmt_mod(derived.get('initiative', 0))}  |  "
                 f"**Speed:** {combat.get('speed', 30)}  |  "
                 f"**Passive Perception:** {derived.get('passive_perception', 10)}  |  "
                 f"**Proficiency Bonus:** {_fmt_mod(derived.get('proficiency_bonus', 2))}")
    lines.append("")

    lines.append("## Ability Scores")
    ability_line = "  ".join(
        f"**{a}** {scores.get(a, 10)} ({_fmt_mod(mods.get(a, 0))})"
        for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    )
    lines.append(ability_line)
    lines.append("")

    lines.append("## Saving Throws")
    saves = derived.get("saves") or {}
    lines.append("  ".join(f"**{a}** {_fmt_mod(v)}" for a, v in saves.items()))
    lines.append("")

    lines.append("## Skills")
    skills = derived.get("skills") or {}
    for name in sorted(skills):
        lines.append(f"- {name}: {_fmt_mod(skills[name])}")
    lines.append("")

    proficiencies = sheet.get("proficiencies") or {}
    lines.append("## Proficiencies & Languages")
    lines.append(f"- **Armor:** {', '.join(proficiencies.get('armor') or []) or '—'}")
    lines.append(f"- **Weapons:** {', '.join(proficiencies.get('weapons') or []) or '—'}")
    lines.append(f"- **Tools:** {', '.join(proficiencies.get('tools') or []) or '—'}")
    lines.append(f"- **Languages:** {', '.join(proficiencies.get('languages') or []) or '—'}")
    lines.append("")

    lines.append("## Equipment")
    for item in sheet.get("equipment") or []:
        tag = " (equipped)" if item.get("equipped") else ""
        qty = item.get("quantity", 1)
        qty_tag = f" x{qty}" if qty and qty != 1 else ""
        lines.append(f"- {item.get('name', '')}{qty_tag}{tag}")
    lines.append("")

    currency = sheet.get("currency") or {}
    lines.append("## Currency")
    lines.append(", ".join(f"{currency.get(k, 0)} {k.upper()}"
                           for k in ("cp", "sp", "ep", "gp", "pp")))
    lines.append("")

    spellcasting = derived.get("spellcasting")
    if spellcasting:
        lines.append("## Spellcasting")
        lines.append(f"- **Ability:** {spellcasting['ability']}  |  "
                     f"**Save DC** {spellcasting['save_dc']}  |  "
                     f"**Attack Bonus** {_fmt_mod(spellcasting['attack_bonus'])}")
        for spell in sheet.get("spells") or []:
            prepared_tag = " (prepared)" if spell.get("prepared") else ""
            lines.append(f"- {spell.get('name', '')}{prepared_tag}")
        lines.append("")

    lines.append("## Features & Traits")
    for feature in sheet.get("features_traits") or []:
        text = f" — {feature['description']}" if feature.get("description") else ""
        lines.append(f"- **{feature.get('name', '')}** ({feature.get('source', '')}){text}")
    lines.append("")

    personality = sheet.get("personality") or {}
    lines.append("## Personality")
    lines.append(f"- **Traits:** {personality.get('traits', '') or '—'}")
    lines.append(f"- **Ideals:** {personality.get('ideals', '') or '—'}")
    lines.append(f"- **Bonds:** {personality.get('bonds', '') or '—'}")
    lines.append(f"- **Flaws:** {personality.get('flaws', '') or '—'}")
    lines.append("")

    lines.append("## Backstory")
    lines.append(sheet.get("backstory") or "—")
    lines.append("")

    return "\n".join(lines)
