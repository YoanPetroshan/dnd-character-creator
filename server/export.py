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
        # `.get()` (not direct indexing) is a deliberate, minimal stopgap so
        # this doesn't KeyError against the new Resolution shape; surfacing
        # the new derived["spellSlots"]/["warlockSpellSlots"] and per-caster
        # values properly in the YAML export is Task 3's job, not this one's.
        "spellSaveDC": derived.get("spellSaveDC"),
        "spellAttackBonus": derived.get("spellAttackBonus"),
        "proficiencies": sheet["proficiencies"],
        "equipment": sheet["equipment"],
        "spells": sheet["spells"],
    }
    # allow_unicode=True: character names in this app are routinely
    # Cyrillic (the app's own examples are Bulgarian) — without this,
    # PyYAML escapes them as \uXXXX, which is technically valid YAML but
    # unreadable to a human opening the file.
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
