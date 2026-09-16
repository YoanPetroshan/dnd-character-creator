"""Pure Armor Class math from a list of equipped items. No I/O, no catalog
access — every function here takes plain Equipment.json-shaped dicts and is
independently testable. Mirrors engine/derived.py's style.
"""
from __future__ import annotations


def armor_class_from_gear(equipped_items: list[dict], dex_modifier: int) -> int:
    """equipped_items are raw catalog item dicts (the same shape
    Catalog.items values have) for whatever's actually worn/held —
    resolve() is responsible for gathering that list; this function only
    does the arithmetic.
    """
    body_armor = next(
        (i for i in equipped_items if i.get("equipment_category", {}).get("index") == "armor" and i.get("armor_category") != "Shield"),
        None,
    )
    shield = next((i for i in equipped_items if i.get("armor_category") == "Shield"), None)

    if body_armor:
        ac_data = body_armor["armor_class"]
        base = ac_data["base"]
        if ac_data.get("dex_bonus"):
            max_bonus = ac_data.get("max_bonus")
            dex_contribution = dex_modifier if max_bonus is None else min(dex_modifier, max_bonus)
            base += dex_contribution
    else:
        base = 10 + dex_modifier

    if shield:
        base += shield["armor_class"]["base"]  # a shield's own "base" (2) is a flat bonus, not a base AC

    return base
