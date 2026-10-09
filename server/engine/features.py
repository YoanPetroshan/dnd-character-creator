"""Collects the class-feature effects (reference_data.CLASS_FEATURE_EFFECTS)
that apply to a resolved character. Pure: callers pass feature indices."""
from __future__ import annotations

from catalog import reference_data


def active_effects(class_features: list[tuple[str, int, str]]) -> list[tuple[str, int, dict]]:
    """class_features: (class_id, class_level, feature_index) for every
    feature the character has. Returns (class_id, class_level, effect)."""
    out = []
    for cls_id, lvl, idx in class_features:
        eff = reference_data.CLASS_FEATURE_EFFECTS.get(idx)
        if eff:
            out.append((cls_id, lvl, eff))
    return out


def ac_formulas(effects) -> list[dict]:
    return [e["ac_formula"] for _, _, e in effects if "ac_formula" in e]


def armored_ac_bonus(effects) -> int:
    return max([e["ac_bonus_armored"] for _, _, e in effects if "ac_bonus_armored" in e], default=0)


def speed_bonus(effects, class_levels: dict[str, int]) -> int:
    best = 0
    for cls_id, _, e in effects:
        for lvl, ft in (e.get("speed_bonus_by_class_level") or {}).items():
            if class_levels.get(cls_id, 0) >= lvl:
                best = max(best, ft)
    return best


def hp_bonus(effects, class_levels: dict[str, int]) -> int:
    return sum(e["hp_per_class_level"] * class_levels.get(cls_id, 0) for cls_id, _, e in effects if "hp_per_class_level" in e)


def half_proficiency(effects) -> tuple[bool, bool]:
    kinds = {e["half_proficiency"] for _, _, e in effects if "half_proficiency" in e}
    return "floor" in kinds, "ceil" in kinds


def apply_ability_bonuses(scores: dict[str, int], effects) -> dict[str, int]:
    out = dict(scores)
    for _, _, e in effects:
        cap = e.get("ability_cap")
        for ab, bonus in (e.get("ability_bonus") or {}).items():
            cur = out.get(ab, 10)
            out[ab] = max(cur, min(cur + bonus, cap)) if cap else cur + bonus
    return out
