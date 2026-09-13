"""Derived combat/skill numbers a printed character sheet needs that
chargen.build()'s sheet dict deliberately omits (AC and friends — the
source repo's play engine derives them live from equipped gear during
play; this app has no live engine, so it derives them once, at export
time, from the same sheet + the catalog/draft that built it).

Imports nothing outside chargen + the standard library.
"""
from __future__ import annotations

from chargen import rules
from chargen.catalog import Catalog

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# Fixed 5e SRD skill -> governing ability. Not derived from any catalog
# file because chargen has no such table; this is the standard, unchanging
# 5e SRD list (18 skills), safe to hardcode.
SKILL_ABILITY = {
    "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
    "Athletics": "STR", "Deception": "CHA", "History": "INT",
    "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
    "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
    "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
    "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS",
}

CASTING_ABILITY = {
    "Bard": "CHA", "Cleric": "WIS", "Druid": "WIS", "Paladin": "CHA",
    "Ranger": "WIS", "Sorcerer": "CHA", "Warlock": "CHA", "Wizard": "INT",
}


def _total_level(sheet: dict) -> int:
    classes = sheet.get("classes") or []
    return sum(int(c.get("level", 0) or 0) for c in classes if isinstance(c, dict))


def derive(sheet: dict, catalog: Catalog, draft: dict) -> dict:
    scores = sheet.get("ability_scores") or {}
    mods = {a: rules.ability_modifier(int(scores.get(a, 10))) for a in ABILITIES}

    level = _total_level(sheet) or 1
    prof = rules.proficiency_bonus(level)
    classes = sheet.get("classes") or []

    armor = None
    armor_id = draft.get("equipped_armor_id")
    if armor_id:
        armor = next((a for a in catalog.armor() if a["id"] == armor_id), None)
    shield = bool(draft.get("shield"))

    class_features = None
    if armor is None and classes:
        cls_name = classes[0].get("cls", "")
        if cls_name == "Barbarian":
            class_features = {"unarmored_defense_ability_mod": mods["CON"]}
        elif cls_name == "Monk":
            class_features = {"unarmored_defense_ability_mod": mods["WIS"]}
    ac = rules.armor_class(mods["DEX"], armor, shield, class_features)

    proficiencies = sheet.get("proficiencies") or {}
    prof_skills = set(proficiencies.get("skills") or [])
    prof_saves = set(proficiencies.get("saving_throws") or [])

    skills = {
        name: rules.skill_bonus(mods[ability], name in prof_skills, False, prof)
        for name, ability in SKILL_ABILITY.items()
    }
    saves = {
        a: mods[a] + (prof if a in prof_saves else 0)
        for a in ABILITIES
    }
    passive_perception = 10 + skills["Perception"]

    spellcasting = None
    if classes:
        cls_name = classes[0].get("cls", "")
        ability = CASTING_ABILITY.get(cls_name)
        if ability:
            spellcasting = {
                "ability": ability,
                "save_dc": rules.spell_save_dc(prof, mods[ability]),
                "attack_bonus": rules.spell_attack_bonus(prof, mods[ability]),
            }

    return {
        "ac": ac,
        "initiative": mods["DEX"],
        "proficiency_bonus": prof,
        "passive_perception": passive_perception,
        "ability_mods": mods,
        "skills": skills,
        "saves": saves,
        "spellcasting": spellcasting,
    }
