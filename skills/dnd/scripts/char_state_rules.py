#!/usr/bin/env python3
"""char_state_rules.py — static D&D 5e multiclassing reference tables.

Encoded here so they're identical every session, per this project's
established doctrine (see engine/rules_2024.py's own docstring) — never
recalled from memory. Verified against the 2024 PHB rules via web search
during design (2026-08-17); 2014 SRD differences are called out inline.
Reuses character.py's tables rather than duplicating them.
"""
from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from character import HIT_DICE, PROF_BONUS, SAVE_PROFS, SKILLS, mod  # noqa: F401,E402

# Ability score(s) required at 13+ to multiclass INTO each class. A class with
# two entries requires both (2014 and 2024 PHB agree on this list; unchanged
# between rulesets — only the half-caster slot rounding differs, see below).
ABILITY_PREREQS: dict[str, list[str]] = {
    "artificer": ["INT"],
    "barbarian": ["STR"],
    "bard": ["CHA"],
    "cleric": ["WIS"],
    "druid": ["WIS"],
    "fighter": ["STR", "DEX"],  # either STR or DEX satisfies this one
    "monk": ["DEX", "WIS"],
    "paladin": ["STR", "CHA"],
    "ranger": ["DEX", "WIS"],
    "rogue": ["DEX"],
    "sorcerer": ["CHA"],
    "warlock": ["CHA"],
    "wizard": ["INT"],
}

# Proficiencies granted when multiclassing INTO a class — smaller than a
# fresh level-1 start in that class. Empty lists mean "grants nothing beyond
# what class features/spellcasting already provide."
# Verified against the real PHB multiclassing proficiencies table (2026-08-17
# fix round; cross-checked via web search against multiple independent
# sources after a review found the original table wrong for 8/13 classes).
MULTICLASS_PROFICIENCIES: dict[str, dict[str, list]] = {
    "artificer":  {"armor": ["light", "medium", "shields"], "weapons": [], "tools": ["thieves' tools", "tinker's tools"], "skills": 0},
    "barbarian":  {"armor": ["shields"], "weapons": ["simple", "martial"], "tools": [], "skills": 0},
    "bard":       {"armor": ["light"], "weapons": [], "tools": [], "skills": 1, "instruments": 1},
    "cleric":     {"armor": ["light", "medium", "shields"], "weapons": [], "tools": [], "skills": 0},
    "druid":      {"armor": ["light", "medium", "shields"], "weapons": [], "tools": [], "skills": 0},
    "fighter":    {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": [], "skills": 0},
    "monk":       {"armor": [], "weapons": ["simple", "shortsword"], "tools": [], "skills": 0},
    "paladin":    {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": [], "skills": 0},
    "ranger":     {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": [], "skills": 1},
    "rogue":      {"armor": ["light"], "weapons": [], "tools": ["thieves' tools"], "skills": 1},
    "sorcerer":   {"armor": [], "weapons": [], "tools": [], "skills": 0},
    "warlock":    {"armor": ["light"], "weapons": ["simple"], "tools": [], "skills": 0},
    "wizard":     {"armor": [], "weapons": [], "tools": [], "skills": 0},
}

_FULL_CASTERS = {"bard", "cleric", "druid", "sorcerer", "wizard"}
_HALF_CASTERS = {"paladin", "ranger", "artificer"}
_THIRD_CASTER_SUBCLASSES = {"eldritch knight", "arcane trickster"}  # fighter/rogue only, subclass-gated


def caster_category(cls: str, subclass: str = "") -> str:
    c = cls.lower()
    if c == "warlock":
        return "pact"
    if c in _FULL_CASTERS:
        return "full"
    if c in _HALF_CASTERS:
        return "half"
    if c in ("fighter", "rogue") and subclass.strip().lower() in _THIRD_CASTER_SUBCLASSES:
        return "third"
    return "none"


def half_caster_effective_level(level: int, ruleset: str, cls: str = "") -> int:
    """2014 SRD rounds a half-caster's contributed level DOWN; the 2024 PHB
    changed this to round UP (verified via web search, not assumed — this is
    a real, easy-to-get-backwards rules change between the two editions).

    Artificer is a documented exception: it always rounds UP in both
    rulesets (verified via web search), unlike Paladin/Ranger whose
    rounding direction depends on which ruleset is active."""
    if cls.strip().lower() == "artificer":
        return math.ceil(level / 2)
    if ruleset == "2024":
        return math.ceil(level / 2)
    return level // 2


def third_caster_effective_level(level: int) -> int:
    """Unchanged between rulesets: round down."""
    return level // 3


# The standard single-class full-caster spell-slots-per-level table (PHB,
# both editions — unchanged 2014→2024). The multiclass table is this exact
# table, indexed by the character's *effective* combined caster level
# instead of raw character level (PHB, Multiclassing: "look up this total
# level in the ... Multiclass Spellcaster table" — confirmed via web search
# to be the same table a single-class full caster uses).
FULL_CASTER_SLOT_TABLE: dict[int, dict[int, int]] = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}


def check_ability_prereqs(classes_and_scores: list[tuple[str, dict]]) -> list[str]:
    """For each (class, ability_scores_dict) pair the character already has
    or is adding, return a list of human-readable failures (empty = OK)."""
    failures = []
    for cls, scores in classes_and_scores:
        needed = ABILITY_PREREQS.get(cls.lower(), [])
        if not needed:
            continue
        # fighter/ranger/monk-style entries with 2 abilities require BOTH;
        # this table has no "either/or" pairs among the two-entry classes
        # except fighter (STR or DEX) — handle that one case explicitly.
        if cls.lower() == "fighter":
            if scores.get("STR", 0) < 13 and scores.get("DEX", 0) < 13:
                failures.append(f"{cls}: needs STR 13+ or DEX 13+")
            continue
        for ability in needed:
            if scores.get(ability, 0) < 13:
                failures.append(f"{cls}: needs {ability} 13+")
    return failures
