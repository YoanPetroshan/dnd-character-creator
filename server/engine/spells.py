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


def _third_caster_block(catalog: Catalog | None, subclass_id: str | None) -> dict | None:
    """The `spellcasting` block of a 1/3-caster subclass (Eldritch Knight,
    Arcane Trickster), or None."""
    if catalog is None or not subclass_id:
        return None
    block = (catalog.subclasses.get(subclass_id) or {}).get("spellcasting")
    return block if isinstance(block, dict) and block.get("progression") == "1/3" else None


def _entry_parts(entry: tuple) -> tuple[str, int, str | None]:
    """(class id, class level, subclass id or None) of a `(cls, level)` or
    `(cls, level, subclass)` entry."""
    return entry[0], entry[1], (entry[2] if len(entry) > 2 else None)


def combined_caster_level(class_entries: list[tuple], catalog: Catalog | None = None, ruleset: str = "mixed") -> int:
    """Sum each class's contribution to 5e's combined multiclass caster
    level: full casters contribute their own level, half casters
    (HALF_CASTER_CLASSES) contribute level // 2, third casters (an Eldritch
    Knight / Arcane Trickster subclass on a class without spellcasting of its
    own; entries `(cls, level, subclass_id)` plus the `catalog` to look the
    subclass up) contribute level // 3, Warlock (and any other
    PACT_MAGIC_CLASSES) and any non-caster class contribute 0. Under ruleset
    "2024" the half casters (the XPHB `artificer` progression) round UP:
    (level + 1) // 2."""
    total = 0
    for entry in class_entries:
        cls_id, level, subclass_id = _entry_parts(entry)
        if cls_id in PACT_MAGIC_CLASSES:
            continue
        if cls_id in HALF_CASTER_CLASSES:
            total += (level + 1) // 2 if ruleset == "2024" else level // 2
        elif cls_id in FULL_CASTER_CLASSES:
            total += level
        elif _third_caster_block(catalog, subclass_id):
            total += level // 3
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


def single_class_spell_slots(
    catalog: Catalog, cls_id: str, class_level: int, subclass_id: str | None = None, ruleset: str = "mixed",
) -> dict[str, int]:
    """A single class's OWN spell-slot progression at its own class
    level, read directly from its class-level row — the correct lookup
    (per PHB 164) whenever exactly one class grants spell slots, even
    alongside other non-caster classes. Unlike the shared multiclass
    table, this is NOT a round-down onto a full caster's table, so a
    half caster (Paladin/Ranger) gets its real, non-halved progression
    at every level, including odd ones. A class row without spell slots
    falls back to the subclass's own third-caster slot table (Eldritch
    Knight, Arcane Trickster). Under ruleset "2024" a Paladin/Ranger uses the
    full-caster row at caster level ceil(level / 2) (slots from level 1)."""
    if ruleset == "2024" and cls_id in HALF_CASTER_CLASSES and 1 <= class_level <= 20:
        return multiclass_spell_slots(catalog, (class_level + 1) // 2)
    row = catalog.class_level_row(cls_id, class_level)
    own = _nonzero_spell_slots(row.get("spellcasting")) if row else {}
    if own:
        return own
    block = _third_caster_block(catalog, subclass_id)
    table = block.get("slots") if block else None
    if not table or not 1 <= class_level <= len(table):
        return {}
    return {str(n): count for n, count in enumerate(table[class_level - 1], start=1) if count > 0}


def warlock_pact_magic_slots(level_row: dict | None) -> dict[str, int]:
    """Warlock's own Pact Magic slots, read directly from its OWN level
    row (not the shared multiclass table) — pass catalog.class_level_row
    ("warlock", <warlock's own class level>)["spellcasting"] as the level
    argument's dict, or None if no Warlock is present."""
    return _nonzero_spell_slots(level_row)


def spell_slots_for(catalog: Catalog, class_entries: list[tuple], ruleset: str = "mixed") -> tuple[dict[str, int], dict[str, int]]:
    """(shared slot pool, Warlock Pact Magic pool) for [(class_id, class_level)]
    or [(class_id, class_level, subclass_id)].

    Per PHB 164 the COMBINED multiclass table is only correct when MORE THAN
    ONE class actually grants spell slots; exactly one slot-granting class
    (even next to non-casters, e.g. Fighter/Paladin) uses its own single-class
    progression, so a lone half caster is not rounded down on odd levels.
    "Grants slots" is tested against the class's real table at its current
    level (a level-1 Paladin/Ranger has none), not by class-id membership; a
    third-caster subclass grants slots from its own table (level 3 on).
    Pact Magic classes never join the shared pool; the Warlock is looked up at
    its own class level."""
    parts = [_entry_parts(e) for e in class_entries]
    slot_granting = [
        (cls_id, level, sub) for cls_id, level, sub in parts
        if cls_id not in PACT_MAGIC_CLASSES and single_class_spell_slots(catalog, cls_id, level, sub, ruleset)
    ]
    if len(slot_granting) == 1:
        shared = single_class_spell_slots(catalog, *slot_granting[0], ruleset)
    else:
        shared = multiclass_spell_slots(catalog, combined_caster_level(parts, catalog, ruleset))
    warlock = next(((c, lvl) for c, lvl, _ in parts if c in PACT_MAGIC_CLASSES), None)
    row = catalog.class_level_row(*warlock) if warlock else None
    return shared, warlock_pact_magic_slots(row["spellcasting"] if row else None)
