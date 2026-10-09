"""R4: Bard, Sorcerer, Wizard and 2024 Ranger resources.

Rule matrix (verified by script against the SRD level rows, the SRD feature
texts and the XPHB class data; see ARCHITECTURE R4):

Bard / Bardic Inspiration (SRD `bardic-inspiration-d6`, XPHB "Number of Uses"):
  "a number of times equal to your Charisma modifier (a minimum of once)", long
  rest. Font of Inspiration (SRD `font-of-inspiration`, XPHB, bard level 5): "you
  regain all of your expended uses ... when you finish a short or long rest".
  Die: SRD `bardic_inspiration_die` 6/8/10/12 at 1/5/10/15; the XPHB "Bardic
  Die" column is identical (checked level by level). Cases: CHA mod +3 -> 3,
  CHA 8 (mod -1) -> 1, CHA 10 -> 1; level 4 recharge long, level 5 short-or-long
  (both editions); die d6 (1-4), d8 (5-9), d10 (10-14), d12 (15-20).
  2024 only: Font of Inspiration also lets a spell slot restore one use
  (`details.spellSlotRegainsUse`).

Sorcerer / Sorcery Points (SRD `font-of-magic`, XPHB "Font of Magic"): points =
SRD `sorcery_points` / XPHB column (0 at 1, then = level), long rest. Creating
Spell Slots costs (SRD `creating_spell_slots`, XPHB table): level 1/2/3/4/5 slot
= 2/3/5/6/7 points. XPHB adds a minimum sorcerer level per slot (2/3/5/7/9,
prose table, hardcoded in reference_data); the 2014 text has none, so the 2014
and mixed rulesets list all five costs from level 2, the 2024 ruleset only the
slots the level allows. Cases: L1 no entry; L2 2 points; L20 20 (every ruleset).

Wizard / Arcane Recovery (SRD `arcane-recovery`, XPHB): spell slots with a
combined level of no more than half the wizard level rounded up (none of level
6 or higher), once per day after a short rest. SRD `arcane_recovery_levels`
equals ceil(level/2) at all 20 levels (checked); XPHB has no table column, so
2024 uses the formula. Resource: `pool` = that number, recharge long.
Cases: L1 1, L2 1, L3 2, L4 2, L5 3, L15 8, L20 10; same in every ruleset.

Ranger / Favored Enemy: 2024 only (XPHB: Hunter's Mark always prepared, castable
a number of times without a slot, regained on a long rest, the Favored Enemy
column 2/2/2/2/3/3/3/3/4/4/4/4/5/5/5/5/6/6/6/6). 2014 Favored Enemy is a choice
(already modelled), so no resource under 2014 or mixed. With the 2024 tables
missing, no entry and the `class-2024-tables-missing` warning.
"""
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine.class_resources import resources_for
from engine.resolve import resolve

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", abilities=None):
    base = {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": c, "level": lvl, "choices": {}} for c, lvl in classes]
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


# ------------------------------------------------------------------- Bard


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level,die", [(1, "d6"), (4, "d6"), (5, "d8"), (9, "d8"), (10, "d10"), (14, "d10"),
                                       (15, "d12"), (20, "d12")])
def test_bardic_die(catalog, ruleset, level, die):
    if ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    assert _entry(_res(catalog, [("bard", level)], ruleset), "bard:bardic-inspiration")["die"] == die


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level,recharge", [(1, "long"), (4, "long"), (5, "short-or-long"), (20, "short-or-long")])
def test_bardic_inspiration_recharge_font_of_inspiration(catalog, ruleset, level, recharge):
    if ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    assert _entry(_res(catalog, [("bard", level)], ruleset), "bard:bardic-inspiration")["recharge"] == recharge


@pytest.mark.parametrize("cha,uses", [(16, 3), (8, 1), (10, 1), (20, 5)])
def test_bardic_inspiration_uses_is_cha_modifier_minimum_one(catalog, cha, uses):
    res = _res(catalog, [("bard", 3)], "2014", {"CHA": cha})
    assert _entry(res, "bard:bardic-inspiration")["uses"] == uses


def test_bardic_inspiration_cha16_human_is_plus_three(catalog):
    res = _res(catalog, [("bard", 1)], "2014", {"CHA": 16})  # human +1 -> 17, +3
    assert res["derived"]["abilityModifiers"]["CHA"] == 3
    assert _entry(res, "bard:bardic-inspiration")["uses"] == 3


@needs_classes
def test_bardic_die_2024_table_matches_srd_row_by_row(catalog):
    for level in range(1, 21):
        srd = catalog.class_level_row("bard", level)["class_specific"]["bardic_inspiration_die"]
        assert catalog.class_2024_tables["bard"]["bardic-die"][level - 1] == f"1d{srd}"


@needs_classes
def test_font_of_inspiration_slot_note_only_in_2024(catalog):
    assert _entry(_res(catalog, [("bard", 5)], "2024"), "bard:bardic-inspiration")["details"]["spellSlotRegainsUse"]
    assert "details" not in _entry(_res(catalog, [("bard", 5)], "2014"), "bard:bardic-inspiration")
    assert "details" not in _entry(_res(catalog, [("bard", 4)], "2024"), "bard:bardic-inspiration")


# --------------------------------------------------------------- Sorcerer


def test_sorcerer_1_has_nothing(catalog):
    for rs in ("2014", "mixed"):
        assert _res(catalog, [("sorcerer", 1)], rs)["derived"]["classResources"] == []


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level", [2, 3, 10, 20])
def test_sorcery_points_equal_level(catalog, ruleset, level):
    if ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    sp = _entry(_res(catalog, [("sorcerer", level)], ruleset), "sorcerer:sorcery-points")
    assert sp["uses"] == level and sp["recharge"] == "long" and sp["classId"] == "sorcerer"


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_creating_spell_slots_costs_srd(catalog, ruleset):
    sp = _entry(_res(catalog, [("sorcerer", 2)], ruleset), "sorcerer:sorcery-points")
    assert sp["details"]["slotCosts"] == {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}


@needs_classes
@pytest.mark.parametrize("level,slots", [(2, {1: 2}), (3, {1: 2, 2: 3}), (5, {1: 2, 2: 3, 3: 5}),
                                         (7, {1: 2, 2: 3, 3: 5, 4: 6}), (9, {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}),
                                         (20, {1: 2, 2: 3, 3: 5, 4: 6, 5: 7})])
def test_creating_spell_slots_2024_minimum_levels(catalog, level, slots):
    sp = _entry(_res(catalog, [("sorcerer", level)], "2024"), "sorcerer:sorcery-points")
    assert sp["details"]["slotCosts"] == slots


# ----------------------------------------------------------------- Wizard


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level", list(range(1, 21)))
def test_arcane_recovery_is_half_level_rounded_up(catalog, ruleset, level):
    if ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    ar = _entry(_res(catalog, [("wizard", level)], ruleset), "wizard:arcane-recovery")
    assert ar["pool"] == -(-level // 2) and ar["recharge"] == "long" and ar["uses"] is None
    assert ar["details"]["maxSlotLevel"] == 5


def test_srd_arcane_recovery_row_equals_the_formula(catalog):
    for level in range(1, 21):
        assert catalog.class_level_row("wizard", level)["class_specific"]["arcane_recovery_levels"] == -(-level // 2)


# ----------------------------------------------------------------- Ranger


@needs_classes
@pytest.mark.parametrize("level,uses", [(1, 2), (4, 2), (5, 3), (9, 4), (13, 5), (17, 6), (20, 6)])
def test_ranger_2024_favored_enemy_hunters_mark(catalog, level, uses):
    fe = _entry(_res(catalog, [("ranger", level)], "2024"), "ranger:favored-enemy-hunter-s-mark")
    assert fe["name"] == "Favored Enemy (Hunter's Mark)" and fe["uses"] == uses and fe["recharge"] == "long"


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_ranger_srd_has_no_resource(catalog, ruleset):
    assert _res(catalog, [("ranger", 10)], ruleset)["derived"]["classResources"] == []


def test_ranger_2024_degrades_without_tables_and_warns_once(catalog):
    class NoTables:
        class_2024_tables = {}
    warns: list = []
    rc = {"cls_id": "ranger", "level": 5, "cls": {"name": "Ranger"}, "level_row": {"class_specific": {}}}
    assert resources_for(NoTables(), [rc], {}, 3, "2024", None, warns) == []
    assert [w["id"] for w in warns] == ["class-2024-tables-missing"]


def test_bard_2024_without_tables_uses_srd_numbers(catalog):
    class NoTables:
        class_2024_tables = {}
    warns: list = []
    rc = {"cls_id": "bard", "level": 10, "cls": {"name": "Bard"},
          "level_row": {"class_specific": {"bardic_inspiration_die": 10}}}
    out = resources_for(NoTables(), [rc], {"CHA": 2}, 4, "2024", None, warns)
    assert out[0]["die"] == "d10" and out[0]["uses"] == 2 and out[0]["recharge"] == "short-or-long"
    assert len(warns) == 1


# ------------------------------------------------------- multiclass, speed


def test_multiclass_bard_wizard_gets_one_entry_each_in_class_order(catalog):
    res = _res(catalog, [("bard", 5), ("wizard", 4)], "2014", {"CHA": 16})
    assert [r["id"] for r in res["derived"]["classResources"]] == ["bard:bardic-inspiration", "wizard:arcane-recovery"]
    assert _entry(res, "wizard:arcane-recovery")["pool"] == 2  # wizard level 4, not total 9


def test_bard_and_sorcerer_20_resolve_under_50_ms(catalog):
    for cls in ("bard", "sorcerer"):
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, [(cls, 20)], "mixed")
        assert (time.perf_counter() - t) / 10 < 0.05
