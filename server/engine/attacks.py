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

C7c: `attacks_from_gear(..., pact_weapon=<item id>)` makes that weapon's row proficient and lets it use Charisma
when the CHA modifier beats the weapon's normal ability (Pact of the Blade, ruleset 2024).

G2: with `hands` ({"main", "off", "dueling_ok"}, built by engine.worn from
`equipment.wielded`) Dueling is evaluated: the +2 goes into `damage` of the
main-hand weapon only when the off hand holds no weapon, `duelingDamage` stays
None and rows get `wielded: bool`. Without `hands` the S5 behavior is unchanged.
Two-Weapon Fighting's `offhandDamage` is still per light weapon (not hand-aware).

FE5 (feat attacks): `styles` may carry `offhand_non_light` / `offhand_dw2024` (Dual Wielder: an off-hand `offhandDamage`
for one-handed or non-Two-Handed melee weapons), `offhand_light_crossbow_mod` (Crossbow Expert XPHB: the modifier on the
Light crossbow's extra attack) and `finesse_items` (Revenant Blade); `unarmed_strike(..., feat=, monk=)` builds the Unarmed
Strike row a feat improves. Optional riders (Great Weapon Master, Savage Attacker, ...) are row notes added by
`engine.feat_effects.annotate_attacks`, never part of `damage` (F-D2).

Out of scope: magic items, Monk martial arts for non-Monks, other unarmed strikes (R2 adds the Monk's row).
"""
from __future__ import annotations

from catalog import reference_data

_NOTE_ORDER = ("two-handed", "heavy", "ammunition", "loading", "reach", "thrown")
GWF_NOTE = "Great Weapon Fighting: reroll 1s and 2s"
GWF_2024_NOTE = "Great Weapon Fighting: treat 1s and 2s as 3"
DUELING_NOTE = "Dueling: only with no other weapon"
PACT_WEAPON_NOTE = "Pact weapon: proficient; Charisma for attack and damage; Necrotic, Psychic or Radiant damage allowed"  # C7c (2024)


def _dice(dice: str, mod: int) -> str:
    return dice if mod == 0 else f"{dice}{mod:+d}"


def _range_text(item: dict) -> str | None:
    # Thrown weapons list their throwing range separately (dagger 20/60);
    # their `range` is the melee reach.
    r = item.get("throw_range") or item.get("range") or {}
    if "normal" not in r:
        return None
    return f"{r['normal']}/{r['long']}" if r.get("long") else str(r["normal"])


FIREARM_ITEM_IDS = frozenset({"musket", "pistol"})  # the DMG firearms in the catalog; Gunner grants the "firearms" id


def weapon_is_proficient(item: dict, proficiency_ids) -> bool:
    """Category proficiency (simple/martial) or the weapon's own proficiency id."""
    return bool(
        (item["index"] in FIREARM_ITEM_IDS and "firearms" in proficiency_ids)  # FE5: Gunner (TCE)
        or (item.get("weapon_category") == "Simple" and "simple-weapons" in proficiency_ids)
        or (item.get("weapon_category") == "Martial" and "martial-weapons" in proficiency_ids)
        or reference_data.weapon_proficiency_id(item["index"]) in proficiency_ids
        # F1: 2024 Rogue, "Martial weapons that have the Finesse or Light property"
        or (item.get("weapon_category") == "Martial"
            and reference_data.MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID in proficiency_ids
            and {p["index"] for p in item.get("properties", [])} & {"finesse", "light"})
        # C9a: 2024 Monk, "Martial weapons that have the Light property"
        or (item.get("weapon_category") == "Martial"
            and reference_data.MARTIAL_LIGHT_PROFICIENCY_ID in proficiency_ids
            and "light" in {p["index"] for p in item.get("properties", [])})
    )


def annotate_mastery(attacks: list[dict], masteries: list[dict]) -> list[dict]:
    """C2: `mastery` on every attack row = the mastery name when that weapon is
    one of the character's chosen masteries, else None."""
    by_item = {m["itemId"]: m["mastery"] for m in masteries}
    return [{**a, "mastery": by_item.get(a["itemId"])} for a in attacks]


def weapon_attack(item: dict, modifiers: dict, prof_bonus: int, proficiency_ids, styles: dict, hands: dict | None = None,
                  pact: bool = False) -> dict | None:
    if item.get("equipment_category", {}).get("index") != "weapon":
        return None
    props = {p["index"] for p in item.get("properties", [])}
    ranged = item.get("weapon_range") == "Ranged"

    if "finesse" in props or item["index"] in styles.get("finesse_items", ()):  # FE5: Revenant Blade
        ability = "DEX" if modifiers.get("DEX", 0) > modifiers.get("STR", 0) else "STR"
    elif ranged:
        ability = "DEX"
    else:
        ability = "STR"
    mod = modifiers.get(ability, 0)
    if pact and modifiers.get("CHA", 0) > mod:  # C7c: the Pact of the Blade weapon uses Charisma when that is better
        ability, mod = "CHA", modifiers["CHA"]

    proficient = True if pact else weapon_is_proficient(item, proficiency_ids)
    attack_bonus = mod + (prof_bonus if proficient else 0) + (styles.get("ranged_attack", 0) if ranged else 0)

    notes = [n for n in _NOTE_ORDER if n in props]
    if pact:
        notes.append(PACT_WEAPON_NOTE)
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
        elif not ranged and not two_handed and (styles.get("offhand_non_light") or styles.get("offhand_dw2024")):
            # FE5 Dual Wielder: the off-hand attack with a weapon that is not Light (F-D5: Two-Weapon Fighting adds the modifier)
            offhand = _dice(dmg["damage_dice"], mod if styles.get("two_weapon_fighting") else min(mod, 0))
        elif ranged and "light" in props and styles.get("offhand_light_crossbow_mod") and "crossbow" in item["index"]:
            offhand = _dice(dmg["damage_dice"], mod)  # FE5 Crossbow Expert (XPHB): add the modifier to the extra attack
        if not ranged and (two_handed or "versatile" in props):
            if styles.get("great_weapon_fighting"):
                notes.append(GWF_NOTE)
            if styles.get("great_weapon_fighting_2024"):
                notes.append(GWF_2024_NOTE)
        if styles.get("thrown_damage") and "thrown" in props:
            notes.append(f"Thrown Weapon Fighting: +{styles['thrown_damage']} damage when thrown")
        if dueling and hands is None:
            dueling_damage = _dice(dmg["damage_dice"], mod + dueling)
            notes.append(DUELING_NOTE)
        elif dueling and item["index"] == hands.get("main") and hands.get("dueling_ok"):
            # G2: the hands are known, so the +2 goes straight into `damage` (one-handed grip)
            damage = _dice(dmg["damage_dice"], mod + dueling)
            notes.append("Dueling: +2 damage")

    row = {
        "itemId": item["index"], "name": item["name"], "ability": ability, "proficient": proficient,
        "attackBonus": attack_bonus, "damage": damage, "damageType": damage_type,
        "duelingDamage": dueling_damage, "versatileDamage": versatile, "offhandDamage": offhand, "range": _range_text(item), "notes": notes,
    }
    if hands is not None:  # G2: only when `equipment.wielded` is set
        row["wielded"] = item["index"] in (hands.get("main"), hands.get("off"))
    return row


def attacks_from_gear(items: list[dict], modifiers: dict, prof_bonus: int, proficiency_ids, styles: dict, hands: dict | None = None,
                      pact_weapon: str | None = None) -> list[dict]:
    out, seen = [], set()
    for item in items:
        if item["index"] in seen:
            continue
        a = weapon_attack(item, modifiers, prof_bonus, proficiency_ids, styles, hands, pact=item["index"] == pact_weapon)
        if a:
            seen.add(item["index"])
            out.append(a)
    return out


UNARMED_STRIKE_ID = "unarmed-strike"  # no catalog item uses this id (verified by test)


def unarmed_strike(modifiers: dict, prof_bonus: int, martial_arts_die: str | None, feat: dict | None = None,
                   monk: bool = True) -> dict:
    """The Monk's Martial Arts unarmed strike (SRD): the better of STR/DEX
    (tie STR), always proficient, damage = martial arts die + modifier ("1"
    when no die is given). Callers add the row only for Monk level >= 1.

    FE5 (F-D6): `feat` = `feat_effects.unarmed_spec(...)` = {die, type, notes}: a feat's die and damage type replace
    the Martial Arts die when they are better (`die` None = Martial Arts stays), the notes list the alternatives.
    `monk=False` (a non-Monk with such a feat) uses Strength only. Without `feat` the output is the R2 row."""
    ability = "DEX" if monk and modifiers.get("DEX", 0) > modifiers.get("STR", 0) else "STR"
    mod = modifiers.get(ability, 0)
    die = (feat or {}).get("die") or (martial_arts_die and (f"1{martial_arts_die}" if martial_arts_die.startswith("d") else martial_arts_die))
    return {
        "itemId": UNARMED_STRIKE_ID, "name": "Unarmed Strike", "ability": ability, "proficient": True,
        "attackBonus": mod + prof_bonus, "damage": _dice(die or "1", mod), "damageType": (feat or {}).get("type", "bludgeoning"),
        "duelingDamage": None, "versatileDamage": None, "offhandDamage": None, "range": "5",
        "notes": list(feat["notes"]) if feat else ["Martial Arts"],
    }
