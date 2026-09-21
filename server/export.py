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
        "spellSaveDC": derived["spellSaveDC"],
        "spellAttackBonus": derived["spellAttackBonus"],
        "proficiencies": sheet["proficiencies"],
        "equipment": sheet["equipment"],
        "spells": sheet["spells"],
    }
    # allow_unicode=True: character names in this app are routinely
    # Cyrillic (the app's own examples are Bulgarian) — without this,
    # PyYAML escapes them as \uXXXX, which is technically valid YAML but
    # unreadable to a human opening the file.
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
