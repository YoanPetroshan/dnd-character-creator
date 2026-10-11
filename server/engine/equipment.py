"""Pure Armor Class math from a list of equipped items. No I/O, no catalog
access — every function here takes plain Equipment.json-shaped dicts and is
independently testable. Mirrors engine/derived.py's style.
"""
from __future__ import annotations


def armor_class_from_gear(
    equipped_items: list[dict], dex_modifier: int, formulas=(), modifiers: dict | None = None, armored_bonus: int = 0,
    medium_dex_cap: int | None = None,
) -> int:
    """equipped_items are raw catalog item dicts for whatever's worn/held.
    `formulas` are alternative unarmored AC formulas (class features:
    {"base", "abilities", "allows_shield"}); they apply only with no body
    armor, a formula that disallows shields is dropped when a shield is
    held, and the best candidate wins (never summed). `armored_bonus`
    (Fighting Style: Defense) applies only while wearing body armor. `medium_dex_cap`
    (Medium Armor Master) raises the DEX cap of Medium body armor to that value."""
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
            if medium_dex_cap is not None and max_bonus is not None and body_armor.get("armor_category") == "Medium":
                max_bonus = max(max_bonus, medium_dex_cap)
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


_ARMOR_PROFICIENCY = {"Light": "light-armor", "Medium": "medium-armor", "Heavy": "heavy-armor"}


def armor_warnings(
    equipped_items: list[dict], scores: dict, proficiency_ids, medium_armor_stealth_ok: bool = False,
) -> tuple[list[dict], bool]:
    """Non-blocking warnings for worn armor and whether any of it imposes
    disadvantage on Stealth. Shields need `shields`; body armor needs its
    category proficiency or `all-armor`. Only the warning is raised for a
    Strength shortfall; speed (-10 ft) is not applied to derived stats. `medium_armor_stealth_ok`
    (Medium Armor Master, PHB) drops the Stealth disadvantage of Medium armor."""
    armor, seen = [], set()
    for item in equipped_items:
        if item.get("equipment_category", {}).get("index") == "armor" and item.get("index") not in seen:
            seen.add(item.get("index"))
            armor.append(item)
    warnings: list[dict] = []
    for item in armor:
        index, name, category = item["index"], item.get("name", item["index"]), item.get("armor_category")
        if category == "Shield":
            proficient = "shields" in proficiency_ids
        else:
            proficient = "all-armor" in proficiency_ids or _ARMOR_PROFICIENCY.get(category) in proficiency_ids
        if not proficient:
            warnings.append({
                "id": f"armor-not-proficient-{index}",
                "message": f"Not proficient with {name}: disadvantage on STR/DEX ability checks, saves and attack rolls, and no spellcasting while it is worn.",
            })
        minimum = item.get("str_minimum") or 0
        if minimum > scores.get("STR", 10):
            warnings.append({
                "id": f"armor-strength-{index}",
                "message": f"{name} needs Strength {minimum}; below that, speed is reduced by 10 ft (not applied to the sheet).",
            })
    if sum(1 for i in armor if i.get("armor_category") != "Shield") > 1:
        warnings.append({"id": "armor-multiple-body", "message": "More than one suit of body armor is equipped; only one can be worn."})
    return warnings, any(i.get("stealth_disadvantage") for i in armor
                         if not (medium_armor_stealth_ok and i.get("armor_category") == "Medium"))
