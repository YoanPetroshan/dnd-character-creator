"""Pure spellcasting math for a resolved single-class or multiclass character
at any level 1-20 (see class_level below). Most functions have no I/O and no
catalog access — matches engine/derived.py's and engine/equipment.py's style —
but multiclass_spell_slots requires a Catalog for SRD lookup. See the plan's
Global Constraints for the known-vs-prepared-caster simplification
(Wizard is treated as a prepared caster, not modeled with a separate
spellbook step).
"""
from __future__ import annotations

from catalog.loader import Catalog
from catalog.reference_data import FULL_CASTER_CLASSES, HALF_CASTER_CLASSES


def spellcasting_ability(cls: dict) -> str | None:
    spellcasting = cls.get("spellcasting")
    if not spellcasting:
        return None
    ability = spellcasting.get("spellcasting_ability", {}).get("index")
    return ability.upper() if ability else None


def known_spell_count(level_row: dict, ability_modifier: int, class_level: int, cls_id: str | None = None) -> int:
    spellcasting = level_row.get("spellcasting") or {}
    if not any(spellcasting.get(f"spell_slots_level_{n}", 0) > 0 for n in range(1, 10)):
        return 0
    spells_known = spellcasting.get("spells_known")
    if spells_known is not None:
        return spells_known
    if cls_id in HALF_CASTER_CLASSES:
        return max(1, ability_modifier + class_level // 2)
    return max(1, ability_modifier + class_level)


def spell_save_dc(proficiency_bonus: int, ability_modifier: int) -> int:
    return 8 + proficiency_bonus + ability_modifier


def spell_attack_bonus(proficiency_bonus: int, ability_modifier: int) -> int:
    return proficiency_bonus + ability_modifier


# Warlock's Pact Magic is the ONLY spell-slot progression in the bundled
# SRD data that is NOT part of the shared multiclass pool — it stays
# entirely separate per RAW. A set (not a single string) for the same
# reason HALF_CASTER_CLASSES is a set: extensible if a future data
# source adds another Pact-Magic-style class.
PACT_MAGIC_CLASSES = {"warlock"}

# Any full-caster class id works as a lookup anchor for the shared
# multiclass slot table below — verified empirically (Phase 3b-ii design
# spec) that the standard multiclass table is number-for-number
# identical to any full caster's own single-class slot progression at
# the same level. This class doesn't need to be present in the
# resolving character's own classes; it's a pure data-lookup anchor.
_MULTICLASS_SLOT_TABLE_ANCHOR_CLASS = "wizard"


def combined_caster_level(class_entries: list[tuple[str, int]]) -> int:
    """Sum each class's contribution to 5e's combined multiclass caster
    level: full casters contribute their own level, half casters
    (HALF_CASTER_CLASSES) contribute level // 2, Warlock (and any other
    PACT_MAGIC_CLASSES) and any non-caster class contribute 0."""
    total = 0
    for cls_id, level in class_entries:
        if cls_id in PACT_MAGIC_CLASSES:
            continue
        if cls_id in HALF_CASTER_CLASSES:
            total += level // 2
        elif cls_id in FULL_CASTER_CLASSES:
            total += level
    return total


def _nonzero_spell_slots(spellcasting: dict | None) -> dict[str, int]:
    """Extract the nonzero spell_slots_level_N entries from a single
    spellcasting dict (as found in a catalog class-level row), keyed by
    slot level as a string. Shared by multiclass_spell_slots,
    single_class_spell_slots, and warlock_pact_magic_slots so the
    filtering logic lives in exactly one place."""
    spellcasting = spellcasting or {}
    return {
        str(n): spellcasting[f"spell_slots_level_{n}"]
        for n in range(1, 10)
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0
    }


def multiclass_spell_slots(catalog: Catalog, combined_level: int) -> dict[str, int]:
    """The shared spell-slot pool for every non-Warlock caster, looked
    up at the combined caster level. Only nonzero slot levels are
    included. combined_level <= 0 (no full/half casters present, or
    they're all below their first spell-granting level) returns {}.

    Per RAW (PHB 164), this combined-level table is only the correct
    lookup when MORE THAN ONE class actually grants spell slots — callers
    with exactly one slot-granting class must use that class's own
    single_class_spell_slots row instead (see resolve()'s call site)."""
    if combined_level <= 0:
        return {}
    row = catalog.class_level_row(_MULTICLASS_SLOT_TABLE_ANCHOR_CLASS, combined_level)
    if not row:
        return {}
    return _nonzero_spell_slots(row.get("spellcasting"))


def single_class_spell_slots(catalog: Catalog, cls_id: str, class_level: int) -> dict[str, int]:
    """A single class's OWN spell-slot progression at its own class
    level, read directly from its class-level row — the correct lookup
    (per PHB 164) whenever exactly one class grants spell slots, even
    alongside other non-caster classes. Unlike the shared multiclass
    table, this is NOT a round-down onto a full caster's table, so a
    half caster (Paladin/Ranger) gets its real, non-halved progression
    at every level, including odd ones."""
    row = catalog.class_level_row(cls_id, class_level)
    if not row:
        return {}
    return _nonzero_spell_slots(row.get("spellcasting"))


def warlock_pact_magic_slots(level_row: dict | None) -> dict[str, int]:
    """Warlock's own Pact Magic slots, read directly from its OWN level
    row (not the shared multiclass table) — pass catalog.class_level_row
    ("warlock", <warlock's own class level>)["spellcasting"] as the level
    argument's dict, or None if no Warlock is present."""
    return _nonzero_spell_slots(level_row)


def spell_slots_for(catalog: Catalog, class_entries: list[tuple[str, int]]) -> tuple[dict[str, int], dict[str, int]]:
    """(shared slot pool, Warlock Pact Magic pool) for [(class_id, class_level)].

    Per PHB 164 the COMBINED multiclass table is only correct when MORE THAN
    ONE class actually grants spell slots; exactly one slot-granting class
    (even next to non-casters, e.g. Fighter/Paladin) uses its own single-class
    progression, so a lone half caster is not rounded down on odd levels.
    "Grants slots" is tested against the class's real table at its current
    level (a level-1 Paladin/Ranger has none), not by class-id membership.
    Pact Magic classes never join the shared pool; the Warlock is looked up at
    its own class level."""
    slot_granting = [
        (cls_id, level) for cls_id, level in class_entries
        if cls_id not in PACT_MAGIC_CLASSES and single_class_spell_slots(catalog, cls_id, level)
    ]
    if len(slot_granting) == 1:
        shared = single_class_spell_slots(catalog, *slot_granting[0])
    else:
        shared = multiclass_spell_slots(catalog, combined_caster_level(class_entries))
    warlock = next(((c, lvl) for c, lvl in class_entries if c in PACT_MAGIC_CLASSES), None)
    row = catalog.class_level_row(*warlock) if warlock else None
    return shared, warlock_pact_magic_slots(row["spellcasting"] if row else None)
