"""Pure spellcasting math for a resolved single-class character at any
level 1-20 (see class_level below). No I/O, no catalog access — matches
engine/derived.py's and engine/equipment.py's style. See the plan's
Global Constraints for the known-vs-prepared-caster simplification
(Wizard is treated as a prepared caster, not modeled with a separate
spellbook step).
"""
from __future__ import annotations

from catalog.reference_data import HALF_CASTER_CLASSES


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
