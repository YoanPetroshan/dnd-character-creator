#!/usr/bin/env python3
"""char_state_derive.py — every value that must NEVER be stored, because it
is always cheaply recomputable from raw inputs (AC, attacks, passive
skills, proficiency bonus, spell slots). Nothing here writes anything;
every function is a pure read of a Character plus (where needed) a
lookup.py SRD query.

Item-shape note (2026-08-17, Task 3): the brief this module was built from
assumed `lookup_record(..., category="item", ...)` would return structured
fields like `ac_base` / `dex_cap` / `armor_category` / `ac_bonus` /
`weapon_category`. The REAL dnd5e_srd.json equipment records (verified by
reading skills/dnd/data/dnd5e_srd.json directly) look nothing like that:

    {"name": "Chain Mail", "category": "Armor", "ac": "AC 16 + DEX",
     "str_minimum": 13, "properties": [], "damage": "", ...}
    {"name": "Longsword", "category": "Weapon", "damage": "1d8 Slashing",
     "properties": ["Versatile"], "ac": "", ...}

`ac` is a free-text string (even for the Shield, which is stored as
"AC 2 + DEX" despite shields not actually taking a DEX bonus — a dataset
quirk we work around by only ever reading the shield's leading number).
There is no `armor_category` (light/medium/heavy) or DEX-cap field at all,
and no `weapon_category` (simple/martial) field. Those classifications are
canonical, static SRD facts that don't change record-to-record, so — per
this project's own "encode static tables, verified once, never recalled
from memory" doctrine (see char_state_rules.py) — they're hardcoded below
as `_ARMOR_DEX_CAP` and `_WEAPON_CATEGORY` rather than invented at read
time. This is a real divergence from the brief worth flagging to later
tasks: don't assume `lookup_record("item", ...)` hands back structured
AC/proficiency-category fields — it doesn't.
"""
from __future__ import annotations

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import lookup  # noqa: E402
from character import PROF_BONUS, SKILLS, mod  # noqa: E402
from char_state_schema import Character, SlotPool  # noqa: E402
from char_state_rules import (  # noqa: E402
    FULL_CASTER_SLOT_TABLE, caster_category, half_caster_effective_level,
    third_caster_effective_level,
)


def total_level(char: Character) -> int:
    return sum(c.level for c in char.classes)


def compute_proficiency_bonus(char: Character) -> int:
    lvl = max(1, min(20, total_level(char)))
    return PROF_BONUS[lvl]


# ─── Static SRD armor/weapon classification ──────────────────────────────
# lookup_record's "item" records carry no armor-category or weapon-category
# field (see module docstring), so these are hardcoded from the PHB/SRD
# equipment tables (unchanged 2014→2024) and keyed by normalized item name.

_ARMOR_DEX_CAP: dict[str, "int | None"] = {
    # Light armor: full DEX applies (cap = None = uncapped)
    "padded armor": None,
    "leather armor": None,
    "studded leather armor": None,
    # Medium armor: DEX capped at +2
    "hide armor": 2,
    "chain shirt": 2,
    "scale mail": 2,
    "breastplate": 2,
    "half plate armor": 2,
    "half plate": 2,
    # Heavy armor: no DEX bonus at all
    "ring mail": 0,
    "chain mail": 0,
    "splint armor": 0,
    "splint": 0,
    "plate armor": 0,
    "plate": 0,
}

_WEAPON_CATEGORY: dict[str, str] = {
    # Simple weapons
    "club": "simple", "dagger": "simple", "greatclub": "simple",
    "handaxe": "simple", "javelin": "simple", "light hammer": "simple",
    "mace": "simple", "quarterstaff": "simple", "sickle": "simple",
    "spear": "simple", "crossbow, light": "simple", "dart": "simple",
    "shortbow": "simple", "sling": "simple",
    # Martial weapons
    "battleaxe": "martial", "flail": "martial", "glaive": "martial",
    "greataxe": "martial", "greatsword": "martial", "halberd": "martial",
    "lance": "martial", "longsword": "martial", "maul": "martial",
    "morningstar": "martial", "pike": "martial", "rapier": "martial",
    "scimitar": "martial", "shortsword": "martial", "trident": "martial",
    "war pick": "martial", "warhammer": "martial", "whip": "martial",
    "blowgun": "martial", "crossbow, hand": "martial",
    "crossbow, heavy": "martial", "longbow": "martial", "net": "martial",
}

_AC_NUMBER_RE = re.compile(r"(\d+)")


def _parse_ac_number(ac_text: str) -> "int | None":
    """Pull the leading base-AC number out of a free-text ac field like
    'AC 16 + DEX' or 'AC 2 + DEX' (shields). Returns None if unparseable."""
    if not ac_text:
        return None
    m = _AC_NUMBER_RE.search(ac_text)
    return int(m.group(1)) if m else None


def compute_ac(char: Character, ruleset: str = "2014") -> int:
    dex_mod = mod(char.ability_scores.DEX)
    base = 10
    dex_cap = None  # None = uncapped
    shield_bonus = 0

    for item in char.equipment:
        if not item.equipped:
            continue
        rec = lookup.lookup_record(item.name, category="item", ruleset=ruleset)
        if not rec or rec.get("category") != "Armor":
            continue
        name_key = (rec.get("name") or item.name).strip().lower()
        ac_num = _parse_ac_number(rec.get("ac") or "")
        if ac_num is None:
            continue
        if name_key == "shield":
            # Shields grant a flat bonus, never a DEX-scaling base — the
            # dataset's "+ DEX" suffix on the shield record is a quirk we
            # deliberately ignore (see module docstring).
            shield_bonus += ac_num
            continue
        base = ac_num
        dex_cap = _ARMOR_DEX_CAP.get(name_key)

    effective_dex = dex_mod if dex_cap is None else min(dex_mod, dex_cap)
    return base + effective_dex + shield_bonus


def compute_attacks(char: Character, ruleset: str = "2014") -> list[dict]:
    prof_bonus = compute_proficiency_bonus(char)
    str_mod = mod(char.ability_scores.STR)
    dex_mod = mod(char.ability_scores.DEX)
    weapon_profs = [w.lower() for w in char.proficiencies.weapons]
    attacks = []

    for item in char.equipment:
        if not item.equipped:
            continue
        rec = lookup.lookup_record(item.name, category="item", ruleset=ruleset)
        if not rec or rec.get("category") != "Weapon" or not rec.get("damage"):
            continue  # not a weapon, or a weapon record with no damage die (e.g. Net)

        properties = [p.lower() for p in (rec.get("properties") or [])]
        finesse = "finesse" in properties
        # Ranged weapons (bows) always use DEX, never STR, regardless of
        # finesse — "Ammunition" is the SRD's own marker for these (there is
        # no separate weapon_category/range-type field to check instead, see
        # this module's docstring). Melee/thrown weapons keep the existing
        # STR-unless-finesse rule; a thrown weapon like a Handaxe or Dagger
        # is not "Ammunition" and correctly falls through to that branch.
        ranged = "ammunition" in properties
        if ranged:
            ability_mod = dex_mod
        else:
            ability_mod = max(str_mod, dex_mod) if finesse else str_mod

        name_key = (rec.get("name") or item.name).strip().lower()
        weapon_cat = _WEAPON_CATEGORY.get(name_key)  # "simple" | "martial" | None
        proficient = (
            name_key in weapon_profs
            or (weapon_cat is not None and weapon_cat in weapon_profs)
        )
        atk_bonus = ability_mod + (prof_bonus if proficient else 0)

        dice, _, damage_type = rec["damage"].rpartition(" ")
        attacks.append({
            "name": item.name,
            "attack_bonus": atk_bonus,
            "damage": dice or rec["damage"],
            "damage_type": damage_type,
        })
    return attacks


def compute_passive_skill(char: Character, skill: str) -> int:
    ability = SKILLS.get(skill, "WIS")
    ability_mod = mod(getattr(char.ability_scores, ability))
    proficient = skill in char.proficiencies.skills
    return 10 + ability_mod + (compute_proficiency_bonus(char) if proficient else 0)


def compute_spell_slots(char: Character, ruleset: str = "2014") -> dict[int, SlotPool]:
    effective_level = 0
    for c in char.classes:
        category = caster_category(c.cls, c.subclass)
        if category == "full":
            effective_level += c.level
        elif category == "half":
            # cls is passed through so Artificer's always-round-up rule
            # (verified during Task 2's fix round) is honored regardless
            # of which ruleset is active — Paladin/Ranger still branch on
            # `ruleset` inside half_caster_effective_level itself.
            effective_level += half_caster_effective_level(c.level, ruleset, cls=c.cls)
        elif category == "third":
            effective_level += third_caster_effective_level(c.level)
        # "pact" and "none" contribute nothing to the shared pool

    effective_level = max(0, min(20, effective_level))
    if effective_level == 0:
        return {}

    table_row = FULL_CASTER_SLOT_TABLE.get(effective_level, {})
    # Preserve `used` counts already recorded for each level; only `max`
    # is ever recomputed here.
    result: dict[int, SlotPool] = {}
    for spell_level, max_count in table_row.items():
        previous = char.spell_slots.get(spell_level)
        used = previous.used if previous else 0
        result[spell_level] = SlotPool(max=max_count, used=min(used, max_count))
    return result


def compute_pact_magic_slots(char: Character) -> "SlotPool | None":
    warlock_level = next((c.level for c in char.classes if c.cls.lower() == "warlock"), 0)
    if warlock_level == 0:
        return None
    # PHB Pact Magic table: slot count and slot level by Warlock level.
    # (1-2:1 slot lvl1, 3-4:2 slots lvl2, 5-6:2 slots lvl3, 7-8:2 slots lvl4,
    #  9-10:2 slots lvl5, 11-16:3 slots lvl5, 17-20:4 slots lvl5.)
    if warlock_level < 3:
        max_slots = 1 if warlock_level < 2 else 2
    elif warlock_level < 11:
        max_slots = 2
    elif warlock_level < 17:
        max_slots = 3
    else:
        max_slots = 4
    previous = char.pact_magic_slots
    used = previous.used if previous else 0
    return SlotPool(max=max_slots, used=min(used, max_slots))
