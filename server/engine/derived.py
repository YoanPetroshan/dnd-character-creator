"""Pure derived-stat math for a resolved level-1 single-class character.
No I/O, no catalog access — every function here is independently testable
against hand-computed 5e SRD values. All ability-keyed dicts use the same
UPPERCASE ability keys as frontend/src/types.ts's Ability type
("STR"/"DEX"/"CON"/"INT"/"WIS"/"CHA").
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


def armor_class(dex_modifier: int) -> int:
    # No armor/shield yet — equipment is Phase 2. Unarmored AC = 10 + DEX mod.
    return 10 + dex_modifier


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
