"""Pure Armor Class math from a list of equipped items. No I/O, no catalog
access — every function here takes plain Equipment.json-shaped dicts and is
independently testable. Mirrors engine/derived.py's style.
"""
from __future__ import annotations

from i18n.messages import msg


def armor_class_from_gear(
    equipped_items: list[dict], dex_modifier: int, formulas=(), modifiers: dict | None = None, armored_bonus: int = 0,
    medium_dex_cap: int | None = None, species_ac=(),
) -> int:
    """equipped_items are raw catalog item dicts for whatever's worn/held.
    `formulas` are alternative unarmored AC formulas (class features:
    {"base", "abilities", "allows_shield"}); they apply only with no body
    armor, a formula that disallows shields is dropped when a shield is
    held, and the best candidate wins (never summed). `armored_bonus`
    (Fighting Style: Defense) applies only while wearing body armor. `medium_dex_cap`
    (Medium Armor Master) raises the DEX cap of Medium body armor to that value. `species_ac` (VF2.1, `species_ac_specs`):
    the AC a species trait states -- "unarmored" / "natural" formulas join `formulas` (no body armor), a "natural" one also
    competes with the worn armor, a "fixed" one (Tortle) makes body armor count for nothing, a "flat" one adds at the end."""
    flat = sum(s["base"] for s in species_ac if s["kind"] == "flat")
    natural = [s for s in species_ac if s["kind"] == "natural"]
    formulas = list(formulas) + [{"base": s["base"], "abilities": s["abilities"], "allows_shield": True}
                                 for s in species_ac if s["kind"] in ("unarmored", "natural", "fixed")]
    body_armor = None if any(s["kind"] == "fixed" for s in species_ac) else next(
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
        worn = base + shield_ac + armored_bonus
        mods = modifiers or {}
        return max([worn] + [s["base"] + sum(mods.get(ab, 0) for ab in s["abilities"]) + shield_ac for s in natural]) + flat

    best = 10 + dex_modifier + shield_ac
    mods = modifiers or {}
    for f in formulas:
        if shield and not f.get("allows_shield", True):
            continue
        value = f["base"] + sum(mods.get(ab, 0) for ab in f["abilities"]) + shield_ac
        best = max(best, value)
    return best + flat


def species_ac_specs(race: dict | None, subrace: dict | None) -> list[dict]:
    """VF2.1: the `reference_data.SPECIES_AC` rows of the traits the species holds (race traits and the subrace's own), minus the
    ones the subrace replaces (`overwrites_traits`, F1.2)."""
    from catalog import reference_data
    if not race:
        return []
    replaced = set((subrace or {}).get("overwrites_traits") or [])
    out, seen = [], set()
    for ref in list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or []):
        spec = reference_data.SPECIES_AC.get(ref.get("index"))
        if spec and ref["index"] not in seen and ref.get("name") not in replaced:
            seen.add(ref["index"])
            out.append(spec)
    return out


_ARMOR_PROFICIENCY = {"Light": "light-armor", "Medium": "medium-armor", "Heavy": "heavy-armor"}


def counted_body_armor_id(equipped_items: list[dict]) -> str | None:
    """WH: the suit the engine counts for AC and `slots.current.armor` -- the first body armor in the list."""
    for item in equipped_items:
        if item.get("equipment_category", {}).get("index") == "armor" and item.get("armor_category") != "Shield":
            return item.get("index")
    return None


def fly_armor_bans(race: dict | None, subrace: dict | None, equipped_items: list[dict], counted_body: str | None) -> list[dict]:
    """X1: the `reference_data.FLY_ARMOR_BAN` records the species holds (race + subrace trait refs) whose banned armor
    category is the counted body armor's (WH: the suit AC uses; a shield alone never counts). Each is a dict with `name`,
    `categories`. Empty without a counted suit."""
    from catalog import reference_data
    if not race or counted_body is None:
        return []
    category = next((i.get("armor_category") for i in equipped_items if i.get("index") == counted_body), None)
    refs = list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or [])
    out, seen = [], set()
    for ref in refs:
        spec = reference_data.FLY_ARMOR_BAN.get(ref.get("index"))
        if (not spec or ref["index"] in seen or spec["race"] != race.get("index")
                or spec.get("subrace") != ((subrace or {}).get("index") if spec.get("subrace") else None)
                or category not in spec["categories"]):
            continue
        seen.add(ref["index"])
        out.append({"id": f"fly-armor-{spec.get('subrace') or spec['race']}", "name": spec["name"],
                    "categories": spec["categories"]})
    return out


def fly_armor_warning(ban: dict) -> dict:
    return {"id": ban["id"], "message": msg("fly-armor", name=ban["name"], armor=_armor_category_msg(ban["categories"]))}


def _armor_category_msg(categories: list[str]):
    """The banned armor category as a nested message (it renders as "medium/heavy", "light", ... in English)."""
    if len(categories) > 1:
        return msg("armor-category-medium-heavy")
    category = categories[0].lower()
    if category == "light":
        return msg("armor-category-light")
    if category == "medium":
        return msg("armor-category-medium")
    if category == "heavy":
        return msg("armor-category-heavy")
    return category


def armor_speed_penalty(equipped_items: list[dict], scores: dict, counted_body: str | None = None) -> int:
    """W1: 10 ft when any worn body armor lists a Strength score above the wearer's (PHB 2014 and 2024: "that
    armor reduces the wearer's speed by 10 feet unless the wearer has a Strength score equal to or higher than the
    listed score"). Taken once even for several suits; shields have no requirement. WH: with `counted_body` only that
    suit is looked at (the one AC uses), so a second, uncounted suit cannot slow the wearer."""
    strength = scores.get("STR", 10)
    for item in equipped_items:
        if counted_body is not None and item.get("index") != counted_body:
            continue
        if (item.get("equipment_category", {}).get("index") == "armor" and item.get("armor_category") != "Shield"
                and (item.get("str_minimum") or 0) > strength):
            return 10
    return 0


def armor_warnings(
    equipped_items: list[dict], scores: dict, proficiency_ids, medium_armor_stealth_ok: bool = False,
    speed_exempt: bool = False, counted_body: str | None = None,
) -> tuple[list[dict], bool]:
    """Non-blocking warnings for worn armor and whether any of it imposes
    disadvantage on Stealth. Shields need `shields`; body armor needs its
    category proficiency or `all-armor`. Only the warning is raised for a
    Strength shortfall (W1: the -10 ft speed is applied by resolve(), not here; `speed_exempt` -- a dwarf whose
    speed is not reduced by heavy armor -- drops the warning, since nothing happens). `medium_armor_stealth_ok`
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
                "message": msg("armor-not-proficient", name=name),
            })
        minimum = item.get("str_minimum") or 0
        uncounted = (counted_body is not None and category != "Shield" and index != counted_body)  # WH
        if minimum > scores.get("STR", 10) and not speed_exempt and not uncounted:
            warnings.append({
                "id": f"armor-strength-{index}",
                "message": msg("armor-strength", name=name, minimum=minimum),
            })
    if sum(1 for i in armor if i.get("armor_category") != "Shield") > 1:
        warnings.append({"id": "armor-multiple-body", "message": msg("armor-multiple-body")})
    return warnings, any(i.get("stealth_disadvantage") for i in armor
                         if not (medium_armor_stealth_ok and i.get("armor_category") == "Medium"))
