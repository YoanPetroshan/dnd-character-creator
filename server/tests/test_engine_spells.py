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


def test_spell_save_dc_is_eight_plus_prof_bonus_plus_ability_modifier():
    assert spell_save_dc(proficiency_bonus=2, ability_modifier=3) == 13


def test_spell_attack_bonus_is_prof_bonus_plus_ability_modifier():
    assert spell_attack_bonus(proficiency_bonus=2, ability_modifier=3) == 5
