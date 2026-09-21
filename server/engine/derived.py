"""Pure derived-stat math for a resolved character, single-class or
multiclass, including per-level HP growth across levels 1-20 (see
hit_point_gain_per_level/hit_point_max_at_level below). No I/O, no catalog
access — every function here is independently testable against
hand-computed 5e SRD values. All ability-keyed dicts use the same
UPPERCASE ability keys as frontend/src/types.ts's Ability type
("STR"/"DEX"/"CON"/"INT"/"WIS"/"CHA").
Multiclass HP (hit_point_max_multiclass) reuses hit_point_max/hit_point_gain_per_level
unchanged — see Phase 3b-i design spec for the "only your very first class level
ever takes the max" rule.
"""
from __future__ import annotations

from catalog import reference_data

ABILITIES = reference_data.ABILITIES


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def ability_modifiers(scores: dict[str, int]) -> dict[str, int]:
    return {ab: ability_modifier(scores.get(ab, 10)) for ab in ABILITIES}


def hit_point_max(hit_die: int | None, con_modifier: int) -> int:
    # Level 1 always takes the hit die's maximum, never rolled — matches
    # every published 5e level-1 HP rule.
    if hit_die is None:
        return 0
    return hit_die + con_modifier


def hit_point_gain_per_level(hit_die: int, con_modifier: int, hp_type: str, level: int, hp_rolls: dict) -> int:
    if hp_type == "manual":
        roll = hp_rolls.get(str(level))
        if isinstance(roll, int) and 1 <= roll <= hit_die:
            return max(1, roll + con_modifier)
    # fixed mode, or manual mode with a missing/invalid roll -> fall back
    # to the RAW "take the average" value rather than 0 or a blocking
    # problem — a defaulted estimate is always safer than garbage HP.
    return max(1, (hit_die // 2 + 1) + con_modifier)


def hit_point_max_at_level(hit_die: int | None, con_modifier: int, level: int, hp_type: str, hp_rolls: dict) -> int:
    if hit_die is None:
        return 0
    total = hit_point_max(hit_die, con_modifier)
    for lvl in range(2, level + 1):
        total += hit_point_gain_per_level(hit_die, con_modifier, hp_type, lvl, hp_rolls)
    return total


def hit_point_max_multiclass(class_entries: list[dict], con_modifier: int, hp_type: str) -> int:
    """Sums HP across every class in draft.classes order. Only the very
    first level of the very FIRST class entry takes the hit die's flat
    max (hit_point_max) — every other level, including every OTHER
    class's own level 1 when multiclassing into it, uses
    hit_point_gain_per_level's roll/average logic. This is 5e RAW's
    "you only take the max at 1st level, period" rule, not per-class."""
    total = 0
    for i, entry in enumerate(class_entries):
        hit_die = entry["hit_die"]
        level = entry["level"]
        hp_rolls = entry.get("hp_rolls") or {}
        start_level = 1
        if i == 0:
            total += hit_point_max(hit_die, con_modifier)
            start_level = 2
        for lvl in range(start_level, level + 1):
            total += hit_point_gain_per_level(hit_die, con_modifier, hp_type, lvl, hp_rolls)
    return total


def saving_throws(
    modifiers: dict[str, int], proficient_abilities: list[str], prof_bonus: int,
) -> dict[str, int]:
    return {
        ab: modifiers[ab] + (prof_bonus if ab in proficient_abilities else 0)
        for ab in ABILITIES
    }


def skill_scores(
    modifiers: dict[str, int], proficient_skills: list[str], prof_bonus: int,
) -> dict[str, int]:
    return {
        skill_id: modifiers[ability] + (prof_bonus if skill_id in proficient_skills else 0)
        for skill_id, ability in reference_data.SKILL_ABILITY.items()
    }


def passive_perception(skills: dict[str, int]) -> int:
    return 10 + skills.get("skill-perception", 0)
