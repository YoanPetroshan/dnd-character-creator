"""Third-caster (Eldritch Knight / Arcane Trickster) spell slots, Part 2 of
docs/superpowers/plans/2026-10-09-feat-eligibility-third-casters-2024-overlays.md.
Slot rows were verified by script against class-fighter.json / class-rogue.json."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine import spells as spells_mod

pytestmark = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

EK, AT = "eldritch-knight-phb", "arcane-trickster-phb"


@pytest.fixture(scope="module")
def catalog():
    return load()


def slots(catalog, entries):
    return spells_mod.spell_slots_for(catalog, entries)


@pytest.mark.parametrize("level,expected", [
    (2, {}), (3, {"1": 2}), (4, {"1": 3}), (7, {"1": 4, "2": 2}), (10, {"1": 4, "2": 3}),
    (13, {"1": 4, "2": 3, "3": 2}), (16, {"1": 4, "2": 3, "3": 3}),
    (19, {"1": 4, "2": 3, "3": 3, "4": 1}), (20, {"1": 4, "2": 3, "3": 3, "4": 1}),
])
def test_eldritch_knight_single_class_slots(catalog, level, expected):
    assert slots(catalog, [("fighter", level, EK)])[0] == expected
    assert spells_mod.single_class_spell_slots(catalog, "fighter", level, EK) == expected


def test_arcane_trickster_xphb_has_the_same_slots(catalog):
    assert spells_mod.single_class_spell_slots(catalog, "rogue", 7, "arcane-trickster-xphb") == {"1": 4, "2": 2}


def test_non_caster_subclass_and_missing_subclass_have_no_slots(catalog):
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9, "champion") == {}
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9) == {}
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9, "no-such-subclass") == {}


def test_two_tuple_entries_still_work(catalog):
    assert slots(catalog, [("wizard", 5)])[0] == {"1": 4, "2": 3, "3": 2}


def test_combined_caster_level_adds_a_third(catalog):
    assert spells_mod.combined_caster_level([("fighter", 3, EK), ("wizard", 1)], catalog) == 2
    assert spells_mod.combined_caster_level([("fighter", 9, EK), ("cleric", 1)], catalog) == 4
    assert spells_mod.combined_caster_level([("fighter", 6, EK), ("rogue", 6, AT)], catalog) == 4
    assert spells_mod.combined_caster_level([("fighter", 9, "champion"), ("wizard", 1)], catalog) == 1
    assert spells_mod.combined_caster_level([("fighter", 9, EK)]) == 0  # no catalog: unknown subclass contributes nothing


def test_multiclass_third_caster_with_wizard(catalog):
    assert slots(catalog, [("fighter", 3, EK), ("wizard", 1)])[0] == {"1": 3}


def test_multiclass_third_caster_with_cleric(catalog):
    assert slots(catalog, [("fighter", 9, EK), ("cleric", 1)])[0] == {"1": 4, "2": 3}


def test_two_third_casters_combine(catalog):
    assert slots(catalog, [("fighter", 6, EK), ("rogue", 6, AT)])[0] == {"1": 4, "2": 3}


def test_non_caster_subclass_next_to_a_wizard_uses_the_wizard_row(catalog):
    assert slots(catalog, [("fighter", 9, "champion"), ("wizard", 1)])[0] == {"1": 2}


def test_pact_slots_stay_separate(catalog):
    shared, pact = slots(catalog, [("fighter", 3, EK), ("warlock", 2)])
    assert shared == {"1": 2}
    assert pact == {"1": 2}  # verified by script (the plan guessed {"2": 2}): warlock 2 stores 2 slots under spell_slots_level_1 per catalog row
