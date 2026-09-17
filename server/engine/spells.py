"""Pure spellcasting math for a resolved level-1 single-class character.
No I/O, no catalog access — matches engine/derived.py's and
engine/equipment.py's style. See the plan's Global Constraints for the
known-vs-prepared-caster simplification (Wizard is treated as a prepared
caster, not modeled with a separate spellbook step).
"""
from __future__ import annotations


def spellcasting_ability(cls: dict) -> str | None:
    spellcasting = cls.get("spellcasting")
    if not spellcasting:
        return None
    ability = spellcasting.get("spellcasting_ability", {}).get("index")
    return ability.upper() if ability else None


def known_spell_count(level_row: dict, ability_modifier: int, class_level: int) -> int:
    spellcasting = level_row.get("spellcasting") or {}
    if spellcasting.get("spell_slots_level_1", 0) <= 0:
        return 0
    spells_known = spellcasting.get("spells_known")
    if spells_known is not None:
        return spells_known
    return max(1, ability_modifier + class_level)


def spell_save_dc(proficiency_bonus: int, ability_modifier: int) -> int:
    return 8 + proficiency_bonus + ability_modifier


def spell_attack_bonus(proficiency_bonus: int, ability_modifier: int) -> int:
    return proficiency_bonus + ability_modifier
