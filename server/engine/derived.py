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


_PHYSICAL = ("STR", "DEX", "CON")


def _half_bonus(prof_bonus: int, ability: str, jack: bool, remarkable: bool) -> int:
    best = 0
    if jack:
        best = prof_bonus // 2
    if remarkable and ability in _PHYSICAL:
        best = max(best, (prof_bonus + 1) // 2)
    return best


def skill_scores(
    modifiers: dict[str, int], proficient_skills: list[str], prof_bonus: int,
    expertise_skills=(), jack_of_all_trades: bool = False, remarkable_athlete: bool = False,
) -> dict[str, int]:
    out = {}
    for skill_id, ability in reference_data.SKILL_ABILITY.items():
        if skill_id in proficient_skills:
            bonus = prof_bonus * (2 if skill_id in expertise_skills else 1)
        else:
            bonus = _half_bonus(prof_bonus, ability, jack_of_all_trades, remarkable_athlete)
        out[skill_id] = modifiers[ability] + bonus
    return out


def initiative(
    modifiers: dict[str, int], prof_bonus: int, jack_of_all_trades: bool = False, remarkable_athlete: bool = False,
    bonus: int = 0, proficient: bool = False,
) -> int:
    """FE1: ``bonus`` is a flat modifier (Alert PHB); ``proficient`` adds the full Proficiency Bonus
    (Alert XPHB), which replaces the Jack of All Trades / Remarkable Athlete half bonus."""
    half = prof_bonus if proficient else _half_bonus(prof_bonus, "DEX", jack_of_all_trades, remarkable_athlete)
    return modifiers["DEX"] + half + bonus


def passive_perception(skills: dict[str, int]) -> int:
    return 10 + skills.get("skill-perception", 0)


def passive_skill(skills: dict[str, int], skill_id: str) -> int:
    return 10 + skills.get(skill_id, 0)


_SIZE_CAPACITY_MULTIPLIER = {"Tiny": 0.5, "Small": 1, "Medium": 1, "Large": 2}


def carrying_capacity(str_score: int, size: str | None) -> int | float:
    """Carrying capacity in pounds: STR x 15, halved for Tiny, doubled for
    Large; every other (or unknown) size counts as x1."""
    value = str_score * 15 * _SIZE_CAPACITY_MULTIPLIER.get(size or "Medium", 1)
    return int(value) if value == int(value) else value


def equipment_weight(entries: list[dict], items: dict, weights: dict | None = None) -> int | float:
    """Sum of quantity x weight (pounds) over {itemId, qty} entries. Unknown
    items, missing weights and non-numeric quantities count as 0. `weights` ({item id: lb}, RP8) overrides
    the catalog weight of those items (the 2024 pack table weights)."""
    total = 0.0
    for entry in entries:
        item = items.get(entry.get("itemId"))
        qty = entry.get("qty", 1)
        if not item or isinstance(qty, bool) or not isinstance(qty, (int, float)) or qty < 0:
            continue
        weight = (weights or {}).get(entry.get("itemId"), item.get("weight"))
        total += qty * (weight or 0)
    total = round(total, 2)
    return int(total) if total == int(total) else total


def pack_weights_from_contents(items: dict) -> dict:
    """RPX2: {pack id: lb} for catalog records with `weight` None and `contents` ([{item: {index}, quantity}]): the
    SRD / PHB 2014 equipment packs list no weight of their own, so a pack weighs the sum of its contents. A record
    with a weight keeps it; a pack with an unknown, weightless or malformed member is left out (no guessing)."""
    out = {}
    for pack_id, rec in items.items():
        contents = rec.get("contents")
        if rec.get("weight") is not None or not isinstance(contents, list) or not contents:
            continue
        total = 0.0
        for member in contents:
            ref = (member.get("item") or {}).get("index") if isinstance(member, dict) else None
            qty = member.get("quantity") if isinstance(member, dict) else None
            weight = (items.get(ref) or {}).get("weight")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)) or isinstance(weight, bool) \
                    or not isinstance(weight, (int, float)):
                break
            total += qty * weight
        else:
            total = round(total, 2)
            out[pack_id] = int(total) if total == int(total) else total
    return out


def carrying_summary(str_score: int, size: str | None, entries: list[dict], items: dict,
                     weights: dict | None = None) -> dict:
    capacity = carrying_capacity(str_score, size)
    carried = equipment_weight(entries, items, weights)
    return {"capacity": capacity, "pushDragLift": capacity * 2, "carried": carried, "overCapacity": carried > capacity}
