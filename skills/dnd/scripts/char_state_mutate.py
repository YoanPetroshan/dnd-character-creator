#!/usr/bin/env python3
"""char_state_mutate.py — every push operation, as a pure function over a
Character. Each function either mutates and returns the same object, or
raises without touching it at all — callers (Task 7's CLI) can rely on
"raised = nothing changed."
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import char_state_validate as validate  # noqa: E402
from char_state_rules import (  # noqa: E402,F401
    ABILITY_PREREQS, MULTICLASS_PROFICIENCIES, check_ability_prereqs,
)
from char_state_schema import (  # noqa: E402
    Character, ClassLevel, EquipmentItem, MiscItem, SlotPool, SpellEntry,
)

_MAX_ATTUNEMENT = 3
_VALID_CURRENCY = ("cp", "sp", "ep", "gp", "pp")


def _same(a: str, b: str) -> bool:
    """Catalog-name equality: case- and surrounding-whitespace-insensitive.

    Names reaching this module come from two different places — a validated
    SRD record (canonical casing, e.g. "Scale Mail") and a DM typing a flag
    value (any casing, e.g. "scale mail"). Exact `==` matching made
    `--item-add "scale mail"` followed by `--equip "Scale Mail"` fail with
    "not in inventory", and let two rows differing only in case coexist.
    """
    return a.strip().lower() == b.strip().lower()


def hp_delta(char: Character, delta: int) -> Character:
    """Apply damage (delta < 0) or healing (delta > 0).

    Damage depletes temporary HP first; only the overflow past hp_temp
    reduces hp_current (PHB: "damage is subtracted from temporary hit points
    first"). Healing goes straight to hp_current and never restores hp_temp —
    temp HP only ever comes back from the specific effect that grants it,
    i.e. --temp-hp-set. This was previously applying the delta straight to
    hp_current and ignoring hp_temp entirely.
    """
    if delta < 0:
        damage = -delta
        absorbed = min(char.combat.hp_temp, damage)
        char.combat.hp_temp -= absorbed
        overflow = damage - absorbed
        char.combat.hp_current = max(0, char.combat.hp_current - overflow)
        return char
    char.combat.hp_current = min(char.combat.hp_max, char.combat.hp_current + delta)
    return char


def hp_set(char: Character, value: int) -> Character:
    char.combat.hp_current = max(0, min(char.combat.hp_max, value))
    return char


def temp_hp_set(char: Character, value: int) -> Character:
    char.combat.hp_temp = max(0, value)
    return char


def death_save_increment(char: Character, success: bool) -> Character:
    if success:
        char.combat.death_saves.successes = min(3, char.combat.death_saves.successes + 1)
    else:
        char.combat.death_saves.failures = min(3, char.combat.death_saves.failures + 1)
    return char


def death_save_reset(char: Character) -> Character:
    char.combat.death_saves.successes = 0
    char.combat.death_saves.failures = 0
    return char


def apply_rest(char: Character, kind: str) -> Character:
    if kind not in ("short", "long"):
        raise ValueError(f"rest kind must be 'short' or 'long', got {kind!r}")
    if kind == "long":
        char.combat.hp_current = char.combat.hp_max
        for level_pool in char.spell_slots.values():
            level_pool.used = 0
        for hd in char.combat.hit_dice:
            hd.used = 0
        char.conditions.exhaustion = max(0, char.conditions.exhaustion - 1)
    if char.pact_magic_slots:
        char.pact_magic_slots.used = 0  # Pact Magic recovers on ANY rest, short or long
    return char


def slot_use(char: Character, level: int) -> Character:
    pool = char.spell_slots.get(level)
    if not pool or pool.used >= pool.max:
        raise ValueError(f"no level-{level} slots remaining")
    pool.used += 1
    return char


def slot_restore(char: Character, level: int, count: int = 1) -> Character:
    pool = char.spell_slots.get(level)
    if not pool:
        raise ValueError(f"character has no level-{level} slots at all")
    pool.used = max(0, pool.used - count)
    return char


def pact_slot_use(char: Character) -> Character:
    if not char.pact_magic_slots or char.pact_magic_slots.used >= char.pact_magic_slots.max:
        raise ValueError("no pact magic slots remaining")
    char.pact_magic_slots.used += 1
    return char


def pact_slot_restore(char: Character, count: int = 1) -> Character:
    if not char.pact_magic_slots:
        raise ValueError("character has no pact magic slots")
    char.pact_magic_slots.used = max(0, char.pact_magic_slots.used - count)
    return char


def spell_add(char: Character, name: str, cls: str, prepared: bool = False, ruleset: str = "2014") -> Character:
    # Store the SRD record's own name, not whatever casing the DM typed.
    canonical = validate.validate_spell_name(name, ruleset=ruleset).name
    if any(_same(s.name, canonical) and _same(s.cls, cls) for s in char.spells):
        raise ValueError(f"{canonical} already known for {cls}")
    char.spells.append(SpellEntry(name=canonical, cls=cls, prepared=prepared))
    return char


def spell_remove(char: Character, name: str) -> Character:
    before = len(char.spells)
    char.spells = [s for s in char.spells if not _same(s.name, name)]
    if len(char.spells) == before:
        raise ValueError(f"{name} not known")
    return char


def spell_set_prepared(char: Character, name: str, prepared: bool) -> Character:
    for s in char.spells:
        if _same(s.name, name):
            s.prepared = prepared
            return char
    raise ValueError(f"{name} not known")


def item_add(char: Character, name: str, quantity: int = 1, ruleset: str = "2014") -> Character:
    if quantity < 1:
        raise ValueError(f"quantity must be a positive integer, got {quantity}")
    # Store the SRD record's own name ("Scale Mail"), never the raw user
    # string ("scale mail") — otherwise a later `--equip "Scale Mail"` can't
    # find the row this one just created.
    canonical = validate.validate_item_name(name, ruleset=ruleset).name
    for item in char.equipment:
        if _same(item.name, canonical):
            item.quantity += quantity
            return char
    char.equipment.append(EquipmentItem(name=canonical, equipped=False, quantity=quantity))
    return char


def item_remove(char: Character, name: str, quantity: int | None = None) -> Character:
    if quantity is not None and quantity < 1:
        raise ValueError(f"quantity must be a positive integer or None, got {quantity}")
    for item in char.equipment:
        if _same(item.name, name):
            if quantity is None or quantity >= item.quantity:
                char.equipment.remove(item)
            else:
                item.quantity -= quantity
            return char
    raise ValueError(f"{name} not in inventory")


def equip(char: Character, name: str) -> Character:
    for item in char.equipment:
        if _same(item.name, name):
            item.equipped = True
            return char
    raise ValueError(f"{name} not in inventory — add it first")


def unequip(char: Character, name: str) -> Character:
    for item in char.equipment:
        if _same(item.name, name):
            item.equipped = False
            return char
    raise ValueError(f"{name} not in inventory")


def misc_add(char: Character, name: str, quantity: int = 1, note: str = "") -> Character:
    if quantity < 1:
        raise ValueError(f"quantity must be a positive integer, got {quantity}")
    for item in char.misc_items:
        if _same(item.name, name):
            item.quantity += quantity
            return char
    char.misc_items.append(MiscItem(name=name, quantity=quantity, note=note))
    return char


def misc_remove(char: Character, name: str, quantity: int | None = None) -> Character:
    if quantity is not None and quantity < 1:
        raise ValueError(f"quantity must be a positive integer or None, got {quantity}")
    for item in char.misc_items:
        if _same(item.name, name):
            if quantity is None or quantity >= item.quantity:
                char.misc_items.remove(item)
            else:
                item.quantity -= quantity
            return char
    raise ValueError(f"{name} not in misc items")


def currency_delta(char: Character, denom: str, delta: int) -> Character:
    if denom not in _VALID_CURRENCY:
        raise ValueError(f"denom must be one of {_VALID_CURRENCY}, got {denom!r}")
    current = getattr(char.currency, denom)
    if current + delta < 0:
        raise ValueError(f"insufficient {denom}: has {current}, tried to remove {-delta}")
    setattr(char.currency, denom, current + delta)
    return char


def condition_add(char: Character, name: str, ruleset: str = "2014") -> Character:
    canonical = validate.validate_condition_name(name, ruleset=ruleset).name
    if not any(_same(c, canonical) for c in char.conditions.active):
        char.conditions.active.append(canonical)
    return char


def condition_remove(char: Character, name: str) -> Character:
    char.conditions.active = [c for c in char.conditions.active if not _same(c, name)]
    return char


def set_inspiration(char: Character, value: bool) -> Character:
    char.conditions.inspiration = value
    return char


def set_exhaustion(char: Character, level: int) -> Character:
    if not 0 <= level <= 6:
        raise ValueError("exhaustion must be 0-6")
    char.conditions.exhaustion = level
    return char


def attunement_add(char: Character, name: str) -> Character:
    if any(_same(a, name) for a in char.conditions.attunement):
        return char  # already attuned — not a slot-consuming no-op
    if len(char.conditions.attunement) >= _MAX_ATTUNEMENT:
        raise ValueError(f"already at max attunement ({_MAX_ATTUNEMENT} items)")
    char.conditions.attunement.append(name)
    return char


def attunement_remove(char: Character, name: str) -> Character:
    char.conditions.attunement = [a for a in char.conditions.attunement if not _same(a, name)]
    return char


def multiclass_add(char: Character, cls: str, subclass: str, level: int, force: bool = False) -> Character:
    if not 1 <= level <= 20:
        raise ValueError(f"level must be between 1 and 20, got {level}")
    for c in char.classes:
        # Case-insensitive: caster_category() lowercases before its own table
        # lookups, so an exact-match guard let "cleric" slip past an existing
        # "Cleric" and then double-counted BOTH entries' levels into the
        # shared effective-caster-level sum.
        if _same(c.cls, cls):
            raise ValueError(f"already has levels in {c.cls} — use level_set instead")
    total_level = sum(c.level for c in char.classes) + level
    if total_level > 20:
        raise ValueError(
            f"total character level would be {total_level}, exceeds the 20-level cap"
        )
    if not force:
        scores = {
            "STR": char.ability_scores.STR, "DEX": char.ability_scores.DEX,
            "CON": char.ability_scores.CON, "INT": char.ability_scores.INT,
            "WIS": char.ability_scores.WIS, "CHA": char.ability_scores.CHA,
        }
        pairs = [(c.cls, scores) for c in char.classes] + [(cls, scores)]
        failures = check_ability_prereqs(pairs)
        if failures:
            raise ValueError("multiclass prerequisite(s) not met: " + "; ".join(failures) + " (use --force to override)")
    char.classes.append(ClassLevel(cls=cls, subclass=subclass, level=level))
    _grant_multiclass_proficiencies(char, cls)
    return char


def _grant_multiclass_proficiencies(char: Character, cls: str) -> None:
    """Apply the PHB multiclassing proficiency grants for the class just added.

    char_state_rules.MULTICLASS_PROFICIENCIES was built and verified against
    the real PHB table but was never read by anything outside its own test
    file — multiclassing in granted no proficiencies at all.

    Only the armor/weapons/tools lists are auto-applied: they're concrete
    named proficiencies. The `skills` / `instruments` entries are COUNTS
    ("bard grants 1 skill, 1 musical instrument") that can't be resolved to
    a specific skill or instrument without asking the player, so they're
    deliberately left for the DM to add — see SKILL-commands.md.
    """
    grants = MULTICLASS_PROFICIENCIES.get(cls.strip().lower())
    if not grants:
        return
    for field_name in ("armor", "weapons", "tools"):
        existing = getattr(char.proficiencies, field_name)
        for prof in grants.get(field_name, []):
            if not any(_same(have, prof) for have in existing):
                existing.append(prof)


def level_set(char: Character, cls: str, level: int) -> Character:
    if not 1 <= level <= 20:
        raise ValueError(f"level must be between 1 and 20, got {level}")
    for c in char.classes:
        if _same(c.cls, cls):
            total_level = sum(other.level for other in char.classes if not _same(other.cls, cls)) + level
            if total_level > 20:
                raise ValueError(
                    f"total character level would be {total_level}, exceeds the 20-level cap"
                )
            c.level = level
            return char
    raise ValueError(f"no existing levels in {cls} — use multiclass_add first")
