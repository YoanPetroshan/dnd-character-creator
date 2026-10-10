"""Pure weapon-attack math from Equipment.json-shaped weapon dicts. No I/O and
no catalog access; callers pass ability modifiers, the proficiency bonus, the
set of proficiency ids and the fighting-style flags
(`engine.features.attack_styles`).

Dueling (S5, decision D3 = b): `damage` never includes the Dueling +2. A
separate `duelingDamage` (one-handed dice + mod + 2) is present only for
one-handed melee weapons when the character has Dueling; versatile weapons
get it too (Dueling applies to the one-handed grip, `versatileDamage` is the
two-handed grip and never gets it). Two-handed and ranged weapons get none.

Monk unarmed strike (R2): `unarmed_strike`, see below.

Weapon Mastery (C2) is chosen in resolve(); `annotate_mastery` adds `mastery` to rows.

Out of scope: the Dueling "no other weapon" hand check (there is no hands
model; the note tells the player), Weapon Mastery, magic items, Monk martial
arts for non-Monks, feat attacks, other unarmed strikes (R2 adds the Monk's row).
"""
from __future__ import annotations

from catalog import reference_data

_NOTE_ORDER = ("two-handed", "heavy", "ammunition", "loading", "reach", "thrown")
GWF_NOTE = "Great Weapon Fighting: reroll 1s and 2s"
DUELING_NOTE = "Dueling: only with no other weapon"


def _dice(dice: str, mod: int) -> str:
    return dice if mod == 0 else f"{dice}{mod:+d}"


def _range_text(item: dict) -> str | None:
    # Thrown weapons list their throwing range separately (dagger 20/60);
    # their `range` is the melee reach.
    r = item.get("throw_range") or item.get("range") or {}
    if "normal" not in r:
        return None
    return f"{r['normal']}/{r['long']}" if r.get("long") else str(r["normal"])


def weapon_is_proficient(item: dict, proficiency_ids) -> bool:
    """Category proficiency (simple/martial) or the weapon's own proficiency id."""
    return bool(
        (item.get("weapon_category") == "Simple" and "simple-weapons" in proficiency_ids)
        or (item.get("weapon_category") == "Martial" and "martial-weapons" in proficiency_ids)
        or reference_data.weapon_proficiency_id(item["index"]) in proficiency_ids
    )


def annotate_mastery(attacks: list[dict], masteries: list[dict]) -> list[dict]:
    """C2: `mastery` on every attack row = the mastery name when that weapon is
    one of the character's chosen masteries, else None."""
    by_item = {m["itemId"]: m["mastery"] for m in masteries}
    return [{**a, "mastery": by_item.get(a["itemId"])} for a in attacks]


def weapon_attack(item: dict, modifiers: dict, prof_bonus: int, proficiency_ids, styles: dict) -> dict | None:
    if item.get("equipment_category", {}).get("index") != "weapon":
        return None
    props = {p["index"] for p in item.get("properties", [])}
    ranged = item.get("weapon_range") == "Ranged"

    if "finesse" in props:
        ability = "DEX" if modifiers.get("DEX", 0) > modifiers.get("STR", 0) else "STR"
    elif ranged:
        ability = "DEX"
    else:
        ability = "STR"
    mod = modifiers.get(ability, 0)

    proficient = weapon_is_proficient(item, proficiency_ids)
    attack_bonus = mod + (prof_bonus if proficient else 0) + (styles.get("ranged_attack", 0) if ranged else 0)

    notes = [n for n in _NOTE_ORDER if n in props]
    dmg = item.get("damage")
    two_handed = "two-handed" in props
    dueling = 0 if ranged or two_handed else styles.get("one_handed_melee_damage", 0)

    damage = damage_type = versatile = offhand = dueling_damage = None
    if dmg:
        damage = _dice(dmg["damage_dice"], mod)
        damage_type = dmg["damage_type"]["index"]
        if "versatile" in props and item.get("two_handed_damage"):
            versatile = _dice(item["two_handed_damage"]["damage_dice"], mod)  # never Dueling
        if not ranged and "light" in props:
            offhand = _dice(dmg["damage_dice"], mod if styles.get("two_weapon_fighting") else min(mod, 0))
        if styles.get("great_weapon_fighting") and not ranged and (two_handed or "versatile" in props):
            notes.append(GWF_NOTE)
        if dueling:
            dueling_damage = _dice(dmg["damage_dice"], mod + dueling)
            notes.append(DUELING_NOTE)

    return {
        "itemId": item["index"], "name": item["name"], "ability": ability, "proficient": proficient,
        "attackBonus": attack_bonus, "damage": damage, "damageType": damage_type,
        "duelingDamage": dueling_damage, "versatileDamage": versatile, "offhandDamage": offhand, "range": _range_text(item), "notes": notes,
    }


def attacks_from_gear(items: list[dict], modifiers: dict, prof_bonus: int, proficiency_ids, styles: dict) -> list[dict]:
    out, seen = [], set()
    for item in items:
        if item["index"] in seen:
            continue
        a = weapon_attack(item, modifiers, prof_bonus, proficiency_ids, styles)
        if a:
            seen.add(item["index"])
            out.append(a)
    return out


UNARMED_STRIKE_ID = "unarmed-strike"  # no catalog item uses this id (verified by test)


def unarmed_strike(modifiers: dict, prof_bonus: int, martial_arts_die: str | None) -> dict:
    """The Monk's Martial Arts unarmed strike (SRD): the better of STR/DEX
    (tie STR), always proficient, damage = martial arts die + modifier ("1"
    when no die is given). Callers add the row only for Monk level >= 1."""
    ability = "DEX" if modifiers.get("DEX", 0) > modifiers.get("STR", 0) else "STR"
    mod = modifiers.get(ability, 0)
    die = martial_arts_die and (f"1{martial_arts_die}" if martial_arts_die.startswith("d") else martial_arts_die)
    return {
        "itemId": UNARMED_STRIKE_ID, "name": "Unarmed Strike", "ability": ability, "proficient": True,
        "attackBonus": mod + prof_bonus, "damage": _dice(die or "1", mod), "damageType": "bludgeoning",
        "duelingDamage": None, "versatileDamage": None, "offhandDamage": None, "range": "5", "notes": ["Martial Arts"],
    }
