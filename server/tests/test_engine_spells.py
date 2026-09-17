from engine.spells import (
    known_spell_count,
    spell_attack_bonus,
    spell_save_dc,
    spellcasting_ability,
)

_WIZARD = {"spellcasting": {"spellcasting_ability": {"index": "int", "name": "INT"}}}
_FIGHTER = {}

_BARD_ROW = {"spellcasting": {"cantrips_known": 2, "spells_known": 4, "spell_slots_level_1": 2}}
_CLERIC_ROW = {"spellcasting": {"cantrips_known": 3, "spell_slots_level_1": 2}}
_PALADIN_ROW = {"spellcasting": {"spell_slots_level_1": 0}}
_RANGER_ROW = {"spellcasting": {"spells_known": 0, "spell_slots_level_1": 0}}
_NO_SPELLCASTING_ROW = {}

# Warlock uses Pact Magic — slots move up out of level 1 as the character
# levels, so a real level row can have spell_slots_level_1: 0 while still
# having slots (and a spells_known count) at a higher spell level.
_WARLOCK_L3_ROW = {"spellcasting": {"cantrips_known": 2, "spells_known": 4, "spell_slots_level_1": 0, "spell_slots_level_2": 2}}
_WARLOCK_L11_ROW = {"spellcasting": {"cantrips_known": 4, "spells_known": 11, "spell_slots_level_1": 0, "spell_slots_level_5": 3}}
_WARLOCK_L20_ROW = {"spellcasting": {"cantrips_known": 4, "spells_known": 15, "spell_slots_level_1": 0, "spell_slots_level_5": 4}}

# Paladin is a half-caster: ability_modifier + floor(class_level / 2), not
# the full-caster ability_modifier + class_level formula.
_PALADIN_L20_ROW = {"spellcasting": {"spell_slots_level_1": 4}}


def test_spellcasting_ability_reads_and_uppercases_the_index():
    assert spellcasting_ability(_WIZARD) == "INT"


def test_spellcasting_ability_is_none_for_a_non_caster():
    assert spellcasting_ability(_FIGHTER) is None


def test_known_caster_uses_the_explicit_spells_known_count():
    assert known_spell_count(_BARD_ROW, ability_modifier=3, class_level=1) == 4


def test_prepared_caster_uses_ability_modifier_plus_level():
    assert known_spell_count(_CLERIC_ROW, ability_modifier=3, class_level=1) == 4  # 3 + 1


def test_prepared_caster_minimum_is_one_even_with_a_negative_modifier():
    assert known_spell_count(_CLERIC_ROW, ability_modifier=-2, class_level=1) == 1  # max(1, -2+1)


def test_zero_spell_slots_means_zero_known_spells_even_with_a_spells_known_field():
    assert known_spell_count(_RANGER_ROW, ability_modifier=3, class_level=1) == 0


def test_zero_spell_slots_means_zero_known_spells_with_no_spells_known_field_either():
    assert known_spell_count(_PALADIN_ROW, ability_modifier=3, class_level=1) == 0


def test_a_class_row_with_no_spellcasting_key_at_all_returns_zero():
    assert known_spell_count(_NO_SPELLCASTING_ROW, ability_modifier=3, class_level=1) == 0


def test_warlock_level_3_keeps_its_spells_known_choice_despite_zero_level_1_slots():
    # Regression for the Critical finding: gating on spell_slots_level_1
    # specifically broke Warlock (Pact Magic), which has zero 1st-level
    # slots from level 3 onward even though it's still very much a caster.
    assert known_spell_count(_WARLOCK_L3_ROW, ability_modifier=3, class_level=3) == 4


def test_warlock_level_11_keeps_its_spells_known_choice():
    assert known_spell_count(_WARLOCK_L11_ROW, ability_modifier=3, class_level=11) == 11


def test_warlock_level_20_keeps_its_spells_known_choice():
    assert known_spell_count(_WARLOCK_L20_ROW, ability_modifier=3, class_level=20) == 15


def test_paladin_uses_the_half_caster_formula_not_the_full_caster_formula():
    # CHA mod +3, level 20 -> 3 + 20//2 = 13, NOT 3 + 20 = 23.
    assert known_spell_count(_PALADIN_L20_ROW, ability_modifier=3, class_level=20, cls_id="paladin") == 13


def test_full_caster_is_unaffected_by_the_half_caster_table():
    # Cleric (a full caster, not in HALF_CASTER_CLASSES) still uses
    # ability_modifier + class_level, same as before.
    assert known_spell_count(_CLERIC_ROW, ability_modifier=3, class_level=20, cls_id="cleric") == 23


def test_spell_save_dc_is_eight_plus_prof_bonus_plus_ability_modifier():
    assert spell_save_dc(proficiency_bonus=2, ability_modifier=3) == 13


def test_spell_attack_bonus_is_prof_bonus_plus_ability_modifier():
    assert spell_attack_bonus(proficiency_bonus=2, ability_modifier=3) == 5
