"""Collects the class-feature effects (reference_data.CLASS_FEATURE_EFFECTS)
that apply to a resolved character. Pure: callers pass feature indices."""
from __future__ import annotations

from catalog import reference_data

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# Feature index -> ruleset -> save proficiencies, for features whose grant
# differs by edition. PHB Slippery Mind: Wisdom. XPHB Slippery Mind: Wisdom and
# Charisma. "mixed" uses the 2014/SRD numbers (decision D2).
RULESET_SAVE_PROFICIENCIES: dict[str, dict[str, list[str]]] = {
    "slippery-mind": {"2014": ["WIS"], "mixed": ["WIS"], "2024": ["WIS", "CHA"]},
}


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


def attack_styles(effects) -> dict:
    """Fighting-style effects the attack math reads: Archery's ranged attack
    bonus, Dueling's one-handed melee damage bonus, and the Two-Weapon / Great
    Weapon Fighting flags."""
    return {
        "ranged_attack": max([e["attack_bonus"].get("ranged", 0) for _, _, e in effects if "attack_bonus" in e], default=0),
        "one_handed_melee_damage": max([e["damage_bonus"].get("one_handed_melee", 0) for _, _, e in effects if "damage_bonus" in e], default=0),
        "two_weapon_fighting": any(e.get("two_weapon_fighting") for _, _, e in effects),
        "great_weapon_fighting": any(e.get("great_weapon_fighting") for _, _, e in effects),
        "great_weapon_fighting_2024": any(e.get("great_weapon_fighting_2024") for _, _, e in effects),
        "thrown_damage": max([e["damage_bonus"].get("thrown", 0) for _, _, e in effects if "damage_bonus" in e], default=0),
    }


def save_proficiencies(effects, feature_indexes, ruleset: str) -> list[str]:
    """Extra saving-throw proficiencies from class features: Diamond Soul /
    Disciplined Survivor ("all" in the effects table) and the ruleset-dependent
    grants (Slippery Mind). `feature_indexes` is every feature id the character has."""
    out: list[str] = []
    for _, _, e in effects:
        grant = e.get("save_proficiency")
        out += list(ABILITIES) if grant == "all" else list(grant or [])
    for idx in feature_indexes:
        by_ruleset = RULESET_SAVE_PROFICIENCIES.get(idx)
        if by_ruleset:
            out += by_ruleset.get(ruleset) or by_ruleset["mixed"]
    return list(dict.fromkeys(out))


def save_bonus(effects, modifiers: dict[str, int]) -> int:
    """Aura of Protection: the ability modifier (minimum +1) added to every
    saving throw. Several auras do not add up (a creature benefits from one)."""
    return max([max(e.get("save_bonus_min", 0), modifiers.get(e["save_bonus_ability"], 0))
                for _, _, e in effects if "save_bonus_ability" in e], default=0)


def speed_bonus_unless_heavy(effects, equipped_items) -> int:
    """Fast Movement: +10 unless an equipped armor is Heavy. A different feature
    from Unarmored Movement, so the two add up."""
    if any(i.get("armor_category") == "Heavy" for i in equipped_items):
        return 0
    return sum(e["speed_bonus_unless_heavy_armor"] for _, _, e in effects if "speed_bonus_unless_heavy_armor" in e)


def selected_invocation_ids(choices: list[dict]) -> list[tuple[str, str]]:
    """(class_id, invocation feature id) for every selected Eldritch Invocation.
    Call after `_gate_invocation_choices`, so unmet picks are already gone."""
    return [(c["source"]["id"], sel) for c in choices
            if c["source"]["kind"] == "class" and ":invocations:" in c["id"] for sel in c["selected"]]


def invocation_effects(choices: list[dict], class_levels: dict[str, int]) -> list[tuple[str, int, dict]]:
    """Same triple shape as `active_effects`, so ac_formulas() etc. read both."""
    out = []
    for cls_id, fid in selected_invocation_ids(choices):
        eff = reference_data.INVOCATION_EFFECTS.get(fid)
        if eff:
            out.append((cls_id, class_levels.get(cls_id, 0), eff))
    return out


def invocation_senses(effects) -> dict[str, int]:
    out: dict[str, int] = {}
    for _, _, e in effects:
        for kind, rng in (e.get("senses") or {}).items():
            out[kind] = max(out.get(kind, 0), rng)
    return out


def invocation_skills(effects) -> list[str]:
    return [s for _, _, e in effects for s in e.get("skills") or []]


def invocation_innate_entries(effects) -> list[dict]:
    """Raw innate-spell entries (catalog shape, plus `source`) for resolve to turn into sheet entries."""
    return [{"spell_id": e["innate_spell"]["spell"], "name": e["innate_spell"]["spell"].replace("-", " ").title(),
             "level": e["innate_spell"]["level"], "uses": e["innate_spell"]["uses"], "ability": "CHA",
             "variant": None, "note": e.get("note")}
            for _, _, e in effects if "innate_spell" in e]
