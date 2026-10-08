"""Turns a Resolution (see engine/resolve.py) into a portable YAML
character sheet — a flat document with the fields a player would actually
want to keep, not the internal choices/problems bookkeeping.
"""
from __future__ import annotations

import yaml


def to_yaml(resolution: dict) -> str:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    doc = {
        "name": sheet["name"],
        "level": sheet["level"],
        "classes": sheet["classes"],
        "background": sheet["background"],
        "species": sheet["species"],
        "details": sheet["details"],
        "abilities": sheet["abilities"],
        "abilityModifiers": derived["abilityModifiers"],
        "proficiencyBonus": derived["proficiencyBonus"],
        "hitPointMax": derived["hitPointMax"],
        "hitDice": derived["hitDice"],
        "armorClass": derived["armorClass"],
        "speed": derived["speed"],
        "savingThrows": derived["savingThrows"],
        "skills": derived["skills"],
        "passivePerception": derived["passivePerception"],
        # spellSaveDC/spellAttackBonus moved off `derived` and into each
        # sheet["spells"][i] entry as of Phase 3b-ii (see engine/resolve.py) —
        # a multiclass character's casters each use their own spellcasting
        # ability, so there's no longer one meaningful top-level scalar for
        # either. They already round-trip via "spells": sheet["spells"]
        # below, so no separate top-level key is added for them. The new
        # combined slot pool (and Warlock's separate Pact Magic pool) ARE
        # still single, character-wide values, so they get their own
        # top-level keys here like every other `derived` field in this doc.
        "spellSlots": derived["spellSlots"],
        "warlockSpellSlots": derived["warlockSpellSlots"],
        "proficiencies": sheet["proficiencies"],
        "equipment": sheet["equipment"],
        "spells": sheet["spells"],
        "innateSpells": sheet.get("innateSpells", []),
    }
    # allow_unicode=True: character names in this app are routinely
    # Cyrillic (the app's own examples are Bulgarian) — without this,
    # PyYAML escapes them as \uXXXX, which is technically valid YAML but
    # unreadable to a human opening the file.
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
