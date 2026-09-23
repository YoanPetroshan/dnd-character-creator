import pytest
from catalog.loader import load
from engine.spells import (
    combined_caster_level,
    known_spell_count,
    multiclass_spell_slots,
    spell_attack_bonus,
    spell_save_dc,
    spellcasting_ability,
    warlock_pact_magic_slots,
)


@pytest.fixture(scope="module")
def catalog():
    return load()

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


def test_combined_caster_level_single_full_caster_equals_its_own_level():
    assert combined_caster_level([("wizard", 5)]) == 5


def test_combined_caster_level_two_full_casters_sums_directly():
    assert combined_caster_level([("wizard", 3), ("sorcerer", 2)]) == 5


def test_combined_caster_level_half_caster_contributes_floor_half():
    assert combined_caster_level([("paladin", 5)]) == 2  # 5 // 2 == 2
    assert combined_caster_level([("paladin", 1)]) == 0  # 1 // 2 == 0, no special-case needed


def test_combined_caster_level_full_plus_half_caster():
    assert combined_caster_level([("cleric", 4), ("paladin", 4)]) == 4 + (4 // 2)  # == 6


def test_combined_caster_level_excludes_warlock_entirely():
    assert combined_caster_level([("wizard", 3), ("warlock", 5)]) == 3


def test_combined_caster_level_excludes_non_caster_classes():
    assert combined_caster_level([("wizard", 3), ("fighter", 5)]) == 3


def test_combined_caster_level_empty_list_is_zero():
    assert combined_caster_level([]) == 0


def test_multiclass_spell_slots_matches_a_full_caster_own_table(catalog):
    # Regression anchor: at combined level 5, the shared pool must equal
    # Wizard's own real level-5 slots from the bundled SRD data — not a
    # hand-typed guess, read directly from the catalog.
    wizard_lvl5 = catalog.class_level_row("wizard", 5)["spellcasting"]
    expected = {str(n): wizard_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl5[f"spell_slots_level_{n}"] > 0}
    assert multiclass_spell_slots(catalog, 5) == expected


def test_multiclass_spell_slots_zero_combined_level_is_empty(catalog):
    assert multiclass_spell_slots(catalog, 0) == {}


def test_warlock_pact_magic_slots_reads_directly_from_its_own_level_row(catalog):
    # Confirmed directly against the bundled data while writing this plan:
    # Warlock at character level 3 has 2 slots at 2nd spell level, zero
    # elsewhere — Pact Magic's real, non-obvious curve (fewer, higher-level
    # slots than a full caster of the same level), not a hand-typed guess.
    warlock_lvl3 = catalog.class_level_row("warlock", 3)["spellcasting"]
    result = warlock_pact_magic_slots(warlock_lvl3)
    assert result == {"2": 2}
    assert result == {"2": warlock_lvl3["spell_slots_level_2"]}


def test_warlock_pact_magic_slots_none_row_is_empty():
    assert warlock_pact_magic_slots(None) == {}
