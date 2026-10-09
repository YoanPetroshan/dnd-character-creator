"""Pure Armor Class math from a list of equipped items. No I/O, no catalog
access — every function here takes plain Equipment.json-shaped dicts and is
independently testable. Mirrors engine/derived.py's style.
"""
from __future__ import annotations


def armor_class_from_gear(
    equipped_items: list[dict], dex_modifier: int, formulas=(), modifiers: dict | None = None, armored_bonus: int = 0,
) -> int:
    """equipped_items are raw catalog item dicts for whatever's worn/held.
    `formulas` are alternative unarmored AC formulas (class features:
    {"base", "abilities", "allows_shield"}); they apply only with no body
    armor, a formula that disallows shields is dropped when a shield is
    held, and the best candidate wins (never summed). `armored_bonus`
    (Fighting Style: Defense) applies only while wearing body armor."""
    body_armor = next(
        (i for i in equipped_items if i.get("equipment_category", {}).get("index") == "armor" and i.get("armor_category") != "Shield"),
        None,
    )
    shield = next((i for i in equipped_items if i.get("armor_category") == "Shield"), None)
    shield_ac = shield["armor_class"]["base"] if shield else 0  # a shield's "base" is a flat bonus

    if body_armor:
        ac_data = body_armor["armor_class"]
        base = ac_data["base"]
        if ac_data.get("dex_bonus"):
            max_bonus = ac_data.get("max_bonus")
            base += dex_modifier if max_bonus is None else min(dex_modifier, max_bonus)
        return base + shield_ac + armored_bonus

    best = 10 + dex_modifier + shield_ac
    mods = modifiers or {}
    for f in formulas:
        if shield and not f.get("allows_shield", True):
            continue
        value = f["base"] + sum(mods.get(ab, 0) for ab in f["abilities"]) + shield_ac
        best = max(best, value)
    return best
