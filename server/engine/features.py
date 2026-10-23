"""Collects the class-feature effects (reference_data.CLASS_FEATURE_EFFECTS)
that apply to a resolved character. Pure: callers pass feature indices."""
from __future__ import annotations

from catalog import reference_data
from engine import class_choices_2024

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# Feature index -> ruleset -> save proficiencies, for features whose grant
# differs by edition. PHB Slippery Mind: Wisdom. XPHB Slippery Mind: Wisdom and
# Charisma. "mixed" uses the 2014/SRD numbers (decision D2).
RULESET_SAVE_PROFICIENCIES: dict[str, dict[str, list[str]]] = {
    "slippery-mind": {"2014": ["WIS"], "mixed": ["WIS"], "2024": ["WIS", "CHA"]},
}


def xphb_effects_2024(catalog, resolved_classes: list[dict], ruleset: str) -> list[tuple[str, int, dict]]:
    """RP2: the CLASS_FEATURE_EFFECTS_2024 entries that apply (ruleset "2024" only): the XPHB record is in the
    catalog, the character's level in its class has reached the record's own level and, for a subclass feature, the
    record's subclass is the selected one. Same triple shape as `active_effects`; each effect also carries
    `feature_id` and `feature_name`."""
    if ruleset != "2024":
        return []
    out = []
    for fid, entry in reference_data.CLASS_FEATURE_EFFECTS_2024.items():
        rec = catalog.features.get(fid)
        if not rec:
            continue
        cls_id = (rec.get("class") or {}).get("index")
        sub_id = (rec.get("subclass") or {}).get("index")
        for rc in resolved_classes:
            if rc.get("cls") and rc.get("cls_id") == cls_id and rc["level"] >= (rec.get("level") or 1) \
                    and (not sub_id or rc.get("subclass_id") == sub_id):
                out.append((cls_id, rc["level"], {**entry, "feature_id": fid, "feature_name": rec["name"]}))
                break
    return out


def active_effects(class_features: list[tuple[str, int, str]], skip=()) -> list[tuple[str, int, dict]]:
    """class_features: (class_id, class_level, feature_index) for every
    feature the character has. Returns (class_id, class_level, effect).
    `skip` (RP2): SRD feature ids replaced by an XPHB entry (Primal Champion)."""
    out = []
    for cls_id, lvl, idx in class_features:
        if idx in skip:
            continue
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


def superseded_ids(xphb_effects) -> set[str]:
    return {e["supersedes"] for _, _, e in xphb_effects if "supersedes" in e}


def class_effects(class_features, xphb_effects) -> list[tuple[str, int, dict]]:
    """SRD effects (minus the ones an XPHB entry replaces) plus the XPHB entries."""
    return active_effects(class_features, skip=superseded_ids(xphb_effects)) + list(xphb_effects)


def ability_bonus_losses(scores: dict[str, int], effects) -> list[dict]:
    """RP2: the part of an XPHB ability increase that the cap cut off, for the non-blocking `pruned` note."""
    out, running = [], dict(scores)
    for _, _, e in effects:
        cap = e.get("ability_cap")
        if "feature_id" not in e:
            continue
        for ab, bonus in (e.get("ability_bonus") or {}).items():
            cur = running.get(ab, 10)
            applied = max(cur, min(cur + bonus, cap)) - cur if cap else bonus
            running[ab] = cur + applied
            if applied < bonus:
                reason = (f"{e['feature_name']}: {ab} is already at maximum ({cap}) and the increase was ignored."
                          if applied == 0 else
                          f"{e['feature_name']}: {ab} is capped at {cap}; only +{applied} of +{bonus} applied.")
                out.append({"choiceId": f"feature:{e['feature_id']}", "reason": reason})
    return out


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


def selected_invocation_instances(choices: list[dict]) -> list[tuple[str, str]]:
    """(class_id, option id) for every selected Eldritch Invocation, keeping the `~k` repeat-instance suffix
    (C7a, for per-instance dependents). Call after `_gate_invocation_choices`."""
    return [(c["source"]["id"], sel) for c in choices
            if c["source"]["kind"] == "class" and ":invocations:" in c["id"] for sel in c["selected"]]


def selected_invocation_ids(choices: list[dict]) -> list[tuple[str, str]]:
    """(class_id, invocation feature id) for every selected Eldritch Invocation, instance suffix stripped
    (effect lookup). Call after `_gate_invocation_choices`, so unmet picks are already gone."""
    return [(cls, sel.split("~", 1)[0]) for cls, sel in selected_invocation_instances(choices)]


def invocation_effects(choices: list[dict], class_levels: dict[str, int], catalog=None) -> list[tuple[str, int, dict]]:
    """Same triple shape as `active_effects`, so ac_formulas() etc. read both. `catalog` (C7b) lets XPHB
    invocations merge the innate spells / senses their record carries."""
    out = []
    for cls_id, fid in selected_invocation_ids(choices):
        eff = class_choices_2024.invocation_effect(catalog, fid)
        if eff:
            out.append((cls_id, class_levels.get(cls_id, 0), eff))
    by_id = {c["id"]: c for c in choices}
    for c in choices:  # FE9 Eldritch Adept: the feat's pick, cast with the ability chosen with the feat
        if c["source"]["kind"] != "feat" or not c["id"].endswith(":invocation"):
            continue
        ability = ((by_id.get(c["id"] + "-ability") or {}).get("selected") or [None])[0]
        for fid in c["selected"]:
            eff = class_choices_2024.invocation_effect(catalog, fid)
            if eff:
                out.append(("warlock", class_levels.get("warlock", 0),
                            {**eff, "source_label": c["source"]["label"], **({"ability": ability.upper()} if ability else {})}))
    return out


def invocation_senses(effects) -> dict[str, int]:
    out: dict[str, int] = {}
    for _, _, e in effects:
        for kind, rng in (e.get("senses") or {}).items():
            out[kind] = max(out.get(kind, 0), rng)
    return out


def swim_equals_walk(effects) -> bool:
    """Gift of the Depths: "a Swim Speed equal to your Speed"."""
    return any(e.get("swim_equals_walk") for _, _, e in effects)


def invocation_skills(effects) -> list[str]:
    return [s for _, _, e in effects for s in e.get("skills") or []]


def invocation_innate_entries(effects) -> list[dict]:
    """Raw innate-spell entries (catalog shape, plus `source`) for resolve to turn into sheet entries."""
    return [{"spell_id": e["innate_spell"]["spell"], "name": e["innate_spell"]["spell"].removesuffix("-xphb").replace("-", " ").title(),
             "level": e["innate_spell"]["level"], "uses": e["innate_spell"]["uses"], "ability": e.get("ability", "CHA"),
             "variant": None, "note": e.get("note"), "source_label": e.get("source_label", "Eldritch Invocation")}
            for _, _, e in effects if "innate_spell" in e]


def climb_equals_walk(effects) -> bool:
    return any(e.get("climb_equals_walk") for _, _, e in effects)


def speed_bonus_flat(effects) -> int:
    return sum(e["speed_bonus_flat"] for _, _, e in effects if "speed_bonus_flat" in e)


def class_senses(senses: dict[str, int], effects) -> dict[str, int]:
    """RP2: `sense_range` raises a sense to at least that range; `senses_additive` adds to the final range of the
    sense (Darkvision: "If you already have Darkvision, its range increases by 60 feet"), else is the range itself.
    Call after every other source."""
    out = dict(senses)
    for _, _, e in effects:
        for sense, rng in (e.get("sense_range") or {}).items():
            out[sense] = max(out.get(sense, 0), rng)
    for _, _, e in effects:
        for sense, rng in (e.get("senses_additive") or {}).items():
            out[sense] = out.get(sense, 0) + rng
    return out


def class_resistances(effects) -> list[str]:
    return [t for _, _, e in effects for t in e.get("resist") or []]


def class_condition_immunities(effects) -> list[str]:
    """RPF: unconditional condition immunities of XPHB class / subclass features (Archfey, Nature's Ward)."""
    return [c for _, _, e in effects for c in e.get("condition_immune") or []]


def class_initiative_bonus(effects, modifiers: dict[str, int]) -> int:
    """RPF: Gloom Stalker Dread Ambusher adds the Wisdom modifier to Initiative (never negative)."""
    return sum(max(0, modifiers.get(e["initiative_ability"], 0)) for _, _, e in effects if e.get("initiative_ability"))


def class_skill_proficiencies(effects) -> list[str]:
    return [s for _, _, e in effects for s in e.get("skills") or [] if "feature_id" in e]


def class_other_proficiencies(effects) -> list[str]:
    return [p for _, _, e in effects for p in e.get("proficiencies") or []]
