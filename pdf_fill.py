"""Fills assets/character-sheet-template.pdf (the official Wizards of the
Coast fillable 2014-ruleset sheet) from a chargen.build() sheet dict + a
sheet_derive.derive() dict, via pypdf's AcroForm field API.

Field names below are copied verbatim from this exact PDF's own AcroForm
(inspected with pypdf.PdfReader.get_fields() against
assets/character-sheet-template.pdf) — including two real quirks in the
PDF itself: the Dex-modifier field is "DEXmod " (trailing space) and the
Charisma-modifier field is "CHamod" (lowercase "h"). These are not typos
in this module; changing them to the "obviously correct" spelling would
silently stop the fill from having any effect on those two fields.

Deliberately does not populate: per-spell-level slot boxes
("SlotsTotal 19".."SlotsTotal 27") or the individual spell-list rows
("Spells 10100".."Spells 1080") — their field-to-spell-level mapping isn't
documented anywhere and isn't safely inferrable without visually matching
widget positions on the rendered page; getting it wrong would silently put
a caster's 3rd-level spell in the 1st-level box. The Markdown export
(markdown_render.py) is the complete reference for spells; this PDF covers
everything else a printed sheet needs.

Imports nothing outside chargen + pypdf + the standard library.
"""
from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter

_TEMPLATE = Path(__file__).resolve().parent / "assets" / "character-sheet-template.pdf"

_SKILL_FIELD = {
    "Acrobatics": "Acrobatics", "Animal Handling": "Animal", "Arcana": "Arcana",
    "Athletics": "Athletics", "Deception": "Deception ", "History": "History ",
    "Insight": "Insight", "Intimidation": "Intimidation",
    "Investigation": "Investigation ", "Medicine": "Medicine", "Nature": "Nature",
    "Perception": "Perception ", "Performance": "Performance",
    "Persuasion": "Persuasion", "Religion": "Religion",
    "Sleight of Hand": "SleightofHand", "Stealth": "Stealth ", "Survival": "Survival",
}

_SAVE_FIELD = {
    "STR": "ST Strength", "DEX": "ST Dexterity", "CON": "ST Constitution",
    "INT": "ST Intelligence", "WIS": "ST Wisdom", "CHA": "ST Charisma",
}

# Real quirks in this specific PDF's field names — see module docstring.
_MOD_FIELD = {
    "STR": "STRmod", "DEX": "DEXmod ", "CON": "CONmod",
    "INT": "INTmod", "WIS": "WISmod", "CHA": "CHamod",
}


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _classlevel_text(sheet: dict) -> str:
    classes = sheet.get("classes") or []
    if not classes:
        return ""
    c = classes[0]
    text = c.get("cls", "")
    if c.get("subclass"):
        text += f" ({c['subclass']})"
    return f"{text} {c.get('level', '')}".strip()


def _equipment_text(sheet: dict) -> str:
    lines = []
    for item in sheet.get("equipment") or []:
        qty = item.get("quantity", 1)
        qty_tag = f" x{qty}" if qty and qty != 1 else ""
        tag = " (equipped)" if item.get("equipped") else ""
        lines.append(f"{item.get('name', '')}{qty_tag}{tag}")
    return "\n".join(lines)


def _features_text(sheet: dict) -> str:
    lines = []
    for feature in sheet.get("features_traits") or []:
        text = feature.get("name", "")
        if feature.get("description"):
            text += f": {feature['description']}"
        lines.append(text)
    return "\n".join(lines)


def _proficiencies_text(sheet: dict) -> str:
    p = sheet.get("proficiencies") or {}
    parts = []
    if p.get("armor"):
        parts.append("Armor: " + ", ".join(p["armor"]))
    if p.get("weapons"):
        parts.append("Weapons: " + ", ".join(p["weapons"]))
    if p.get("tools"):
        parts.append("Tools: " + ", ".join(p["tools"]))
    if p.get("languages"):
        parts.append("Languages: " + ", ".join(p["languages"]))
    return "\n".join(parts)


def fill(sheet: dict, derived: dict) -> bytes:
    reader = PdfReader(str(_TEMPLATE))
    writer = PdfWriter()
    writer.append(reader)

    scores = sheet.get("ability_scores") or {}
    mods = derived.get("ability_mods") or {}
    combat = sheet.get("combat") or {}
    currency = sheet.get("currency") or {}
    personality = sheet.get("personality") or {}
    skills = derived.get("skills") or {}
    saves = derived.get("saves") or {}

    values: dict[str, str] = {
        "CharacterName": sheet.get("name", ""),
        "PlayerName": sheet.get("player", ""),
        "Race ": sheet.get("race", ""),
        "Background": sheet.get("background", ""),
        "Alignment": sheet.get("alignment", ""),
        "ClassLevel": _classlevel_text(sheet),
        "AC": str(derived.get("ac", "")),
        "Initiative": _fmt_mod(derived.get("initiative", 0)),
        "Speed": str(combat.get("speed", "")),
        "HPMax": str(combat.get("hp_max", "")),
        "HPCurrent": str(combat.get("hp_current", "")),
        "HPTemp": str(combat.get("hp_temp", 0)),
        "HD": "".join(f"{h.get('die', '')}" for h in combat.get("hit_dice") or [])[:1]
              and f"1d{(combat.get('hit_dice') or [{}])[0].get('die', '')}",
        "HDTotal": str(sum(c.get("level", 0) for c in sheet.get("classes") or [])),
        "ProfBonus": _fmt_mod(derived.get("proficiency_bonus", 2)),
        "Passive": str(derived.get("passive_perception", 10)),
        "Inspiration": "1" if (sheet.get("conditions") or {}).get("inspiration") else "",
        "CP": str(currency.get("cp", 0)), "SP": str(currency.get("sp", 0)),
        "EP": str(currency.get("ep", 0)), "GP": str(currency.get("gp", 0)),
        "PP": str(currency.get("pp", 0)),
        "Equipment": _equipment_text(sheet),
        "Features and Traits": _features_text(sheet),
        "ProficienciesLang": _proficiencies_text(sheet),
        "PersonalityTraits ": personality.get("traits", ""),
        "Ideals": personality.get("ideals", ""),
        "Bonds": personality.get("bonds", ""),
        "Flaws": personality.get("flaws", ""),
        "Backstory": sheet.get("backstory", ""),
    }

    for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        values[ability] = str(scores.get(ability, 10))
        values[_MOD_FIELD[ability]] = _fmt_mod(mods.get(ability, 0))
        values[_SAVE_FIELD[ability]] = _fmt_mod(saves.get(ability, 0))

    for skill_name, field_name in _SKILL_FIELD.items():
        if skill_name in skills:
            values[field_name] = _fmt_mod(skills[skill_name])

    weapon_names = [i["name"] for i in (sheet.get("equipment") or [])][:3]
    wpn_fields = ["Wpn Name", "Wpn Name 2", "Wpn Name 3"]
    for name, field in zip(weapon_names, wpn_fields):
        values[field] = name

    spellcasting = derived.get("spellcasting")
    classes = sheet.get("classes") or []
    if spellcasting and classes:
        values["Spellcasting Class 2"] = classes[0].get("cls", "")
        values["SpellcastingAbility 2"] = spellcasting["ability"]
        values["SpellSaveDC  2"] = str(spellcasting["save_dc"])
        values["SpellAtkBonus 2"] = _fmt_mod(spellcasting["attack_bonus"])

    for page in writer.pages:
        writer.update_page_form_field_values(page, values)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
