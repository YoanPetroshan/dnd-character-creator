"""R3: Cleric, Paladin and Druid resources, with the Channel Divinity multiclass rule.

Governing rule (PHB 2014 p.164, Multiclassing, Channel Divinity): "If you
already have the Channel Divinity feature and gain a level in a class that also
grants the feature, you gain the effect options granted by that class, but
getting the feature again doesn't give you an additional use of it. You gain
additional uses only when you reach a class level that explicitly grants them
to you." So there is ONE combined `channel-divinity` resource: uses = the
maximum over the classes that grant it, `classId` = the class giving that
maximum (the first class in class order on a tie).

2024 (XPHB) rule (G1): the 2024 Multiclassing chapter has no Channel Divinity
merge rule, and each class text says "You can use this class's Channel Divinity
twice" (Cleric; Paladin "twice ... an additional use at level 11"). So under
ruleset == "2024" each class keeps its OWN resource (`cleric:channel-divinity`,
`paladin:channel-divinity`), with its own uses and recharge, and nothing is
merged. Under 2014 and mixed the PHB-2014 merge above applies.

Case matrix (Channel Divinity):
  Cleric 1 -> none | Cleric 2 -> 1 | Cleric 6 -> 2 | Cleric 18 -> 3 (2014 SRD
  `channel_divinity_charges`); 2024 table 2 (2-5), 3 (6-17), 4 (18-20).
  Paladin 2 -> none | Paladin 3 -> 1 (2014; the SRD level rows have no column
  and the feature text is empty, PHB oath text gives one use per short rest);
  2024 table 2 (3-10), 3 (11-20).
  Cleric 6 / Paladin 3 (2014) -> exactly ONE entry, uses 2, classId cleric.
  Cleric 2 / Paladin 3 (2014) -> ONE entry, uses 1 (tie: first class).
  Paladin 3 / Cleric 6 -> ONE entry, uses 2, classId cleric (max, not first).
  Cleric 2 / Paladin 2 -> ONE entry (only the cleric grants it yet).
  Cleric 6 / Paladin 3 (2024) -> ONE entry, uses 3 (max(3, 2)), not 5.
  Paladin 11 / Cleric 2 (2024) -> ONE entry, uses 3, classId paladin.

Verified numbers (script on the SRD level rows and XPHB data):
  Destroy Undead CR (2014 `destroy_undead_cr`, features destroy-undead-cr-*):
  0.5 at 5, 1 at 8, 2 at 11, 3 at 14, 4 at 17. 2024 Cleric has Sear Undead
  (no CR column): no Destroy Undead entry.
  Lay on Hands = 5 x paladin level, long rest, both editions (SRD and XPHB text).
  Divine Sense: 2014 only, 1 + CHA modifier uses (minimum 1), long rest. In 2024
  it is a Channel Divinity effect, not a resource.
  Wild Shape 2014: 2 uses, short or long rest (feature text); `wild_shape_max_cr`
  0.25 (2-3), 0.5 (4-6, swim), 1 (7+; fly from 8); unlimited at 20 (SRD feature
  `archdruid`: "use your Wild Shape an unlimited number of times").
  Wild Shape 2024: XPHB `wild-shape` column 2 (2-5), 3 (6-16), 4 (17-20); not
  unlimited at 20 (XPHB Archdruid regains a use on initiative); Beast Shapes
  table: CR 1/4 no fly (2), 1/2 no fly (4), 1 with fly (8); the Beast Shapes
  table is prose-only, hardcoded in reference_data.
"""
import copy

import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine.resolve import resolve

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", abilities=None):
    base = {"STR": 15, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": c, "level": lvl, "choices": {}} for c, lvl in classes]
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _cds(res):
    return [r for r in res["derived"]["classResources"] if r["name"] == "Channel Divinity"]


# ----------------------------------------------------------------- Cleric


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("level,uses", [(2, 1), (5, 1), (6, 2), (17, 2), (18, 3), (20, 3)])
def test_cleric_srd_channel_divinity(catalog, ruleset, level, uses):
    cd = _entry(_res(catalog, [("cleric", level)], ruleset), "cleric:channel-divinity")
    assert cd["uses"] == uses and cd["recharge"] == "short-or-long" and cd["classId"] == "cleric"


def test_cleric_1_has_nothing(catalog):
    assert _res(catalog, [("cleric", 1)], "2014")["derived"]["classResources"] == []


@pytest.mark.parametrize("level,cr", [(5, "1/2"), (7, "1/2"), (8, "1"), (11, "2"), (14, "3"), (17, "4"), (20, "4")])
def test_destroy_undead_cr(catalog, level, cr):
    du = _entry(_res(catalog, [("cleric", level)], "2014"), "cleric:destroy-undead")
    assert du["details"]["maxCr"] == cr and du["uses"] is None and du["recharge"] is None


def test_no_destroy_undead_before_5(catalog):
    assert _entry(_res(catalog, [("cleric", 4)], "2014"), "cleric:destroy-undead") is None


@needs_classes
@pytest.mark.parametrize("level,uses", [(2, 2), (5, 2), (6, 3), (17, 3), (18, 4), (20, 4)])
def test_cleric_2024_channel_divinity_table(catalog, level, uses):
    res = _res(catalog, [("cleric", level)], "2024")
    cd = _entry(res, "cleric:channel-divinity")
    assert cd["uses"] == uses and cd["recharge"] == "long" and cd["details"]["shortRestRegains"] == 1
    assert _entry(res, "cleric:destroy-undead") is None


@needs_classes
def test_cleric_2024_level_1_has_nothing_and_mixed_ignores_the_table(catalog):
    assert _res(catalog, [("cleric", 1)], "2024")["derived"]["classResources"] == []
    assert _entry(_res(catalog, [("cleric", 2)], "mixed"), "cleric:channel-divinity")["uses"] == 1


# ---------------------------------------------------------------- Paladin


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level,pool", [(1, 5), (2, 10), (10, 50), (20, 100)])
def test_lay_on_hands_pool(catalog, ruleset, level, pool):
    if ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    loh = _entry(_res(catalog, [("paladin", level)], ruleset), "paladin:lay-on-hands")
    assert loh["pool"] == pool and loh["recharge"] == "long" and loh["uses"] is None


def test_divine_sense_2014_is_one_plus_cha(catalog):
    res = _res(catalog, [("paladin", 1)], "2014", {"CHA": 16})  # human +1 -> 17, +3
    assert res["derived"]["abilityModifiers"]["CHA"] == 3
    ds = _entry(res, "paladin:divine-sense")
    assert ds["uses"] == 4 and ds["recharge"] == "long"


def test_divine_sense_minimum_one_use(catalog):
    res = _res(catalog, [("paladin", 1)], "mixed", {"CHA": 6})  # human +1 -> 7, -2
    assert res["derived"]["abilityModifiers"]["CHA"] == -2
    assert _entry(res, "paladin:divine-sense")["uses"] == 1


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_paladin_srd_channel_divinity(catalog, ruleset):
    assert _entry(_res(catalog, [("paladin", 2)], ruleset), "paladin:channel-divinity") is None
    for level in (3, 11, 20):
        cd = _entry(_res(catalog, [("paladin", level)], ruleset), "paladin:channel-divinity")
        assert cd["uses"] == 1 and cd["recharge"] == "short-or-long"


@needs_classes
def test_paladin_2024(catalog):
    r1 = _res(catalog, [("paladin", 1)], "2024")
    assert _entry(r1, "paladin:divine-sense") is None  # a Channel Divinity effect in 2024
    assert _entry(r1, "paladin:lay-on-hands")["pool"] == 5
    assert _entry(_res(catalog, [("paladin", 2)], "2024"), "paladin:channel-divinity") is None
    for level, uses in ((3, 2), (10, 2), (11, 3), (20, 3)):
        res = _res(catalog, [("paladin", level)], "2024")
        assert _entry(res, "paladin:channel-divinity")["uses"] == uses
        assert _entry(res, "paladin:divine-sense") is None


# ---------------------------------------------- Channel Divinity multiclass


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("classes,uses,class_id", [
    ([("cleric", 6), ("paladin", 3)], 2, "cleric"),
    ([("paladin", 3), ("cleric", 6)], 2, "cleric"),   # max, not first
    ([("cleric", 2), ("paladin", 3)], 1, "cleric"),   # tie -> first class
    ([("paladin", 3), ("cleric", 2)], 1, "paladin"),
    ([("cleric", 2), ("paladin", 2)], 1, "cleric"),   # paladin has none yet
    ([("cleric", 18), ("paladin", 10)], 3, "cleric"),
])
def test_channel_divinity_is_one_combined_resource_srd(catalog, ruleset, classes, uses, class_id):
    cds = _cds(_res(catalog, classes, ruleset))
    assert len(cds) == 1
    assert cds[0]["uses"] == uses and cds[0]["classId"] == class_id


def test_combined_channel_divinity_lists_the_contributing_classes(catalog):
    cd = _cds(_res(catalog, [("cleric", 6), ("paladin", 3)], "2014"))[0]
    assert cd["details"]["classes"] == ["cleric", "paladin"]
    assert "classes" not in (_cds(_res(catalog, [("cleric", 6)], "2014"))[0].get("details") or {})


@needs_classes
@pytest.mark.parametrize("classes,expected", [
    ([("cleric", 6), ("paladin", 3)], [("cleric", 3), ("paladin", 2)]),   # not max, not 5
    ([("paladin", 11), ("cleric", 2)], [("paladin", 3), ("cleric", 2)]),
    ([("paladin", 3), ("cleric", 2)], [("paladin", 2), ("cleric", 2)]),
])
def test_channel_divinity_is_separate_per_class_2024(catalog, classes, expected):
    """G1: XPHB Multiclassing (PHB 2024) has no Channel Divinity merge rule and
    each class text says "You can use this class's Channel Divinity twice", so
    under ruleset 2024 each class keeps its own resource (own uses, own recharge)."""
    cds = _cds(_res(catalog, classes, "2024"))
    assert [(r["classId"], r["uses"]) for r in cds] == expected
    assert len({r["id"] for r in cds}) == 2
    assert all("classes" not in (r.get("details") or {}) for r in cds)
    assert all(r["recharge"] == "long" for r in cds)


def test_other_resources_of_a_multiclass_stay_separate(catalog):
    res = _res(catalog, [("cleric", 6), ("paladin", 3)], "2014")
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert "paladin:lay-on-hands" in ids and "paladin:divine-sense" in ids
    assert "cleric:destroy-undead" in ids
    assert ids.index("cleric:channel-divinity") < ids.index("paladin:lay-on-hands")


# ------------------------------------------------------------------ Druid


def test_druid_1_has_nothing(catalog):
    assert _res(catalog, [("druid", 1)], "2014")["derived"]["classResources"] == []


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("level,cr,swim,fly", [
    (2, "1/4", False, False), (3, "1/4", False, False), (4, "1/2", True, False),
    (6, "1/2", True, False), (7, "1", True, False), (8, "1", True, True), (19, "1", True, True),
])
def test_druid_srd_wild_shape(catalog, ruleset, level, cr, swim, fly):
    ws = _entry(_res(catalog, [("druid", level)], ruleset), "druid:wild-shape")
    assert ws["uses"] == 2 and ws["recharge"] == "short-or-long" and "unlimited" not in ws
    assert ws["details"] == {"maxCr": cr, "swim": swim, "fly": fly}


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_druid_20_srd_is_unlimited(catalog, ruleset):
    ws = _entry(_res(catalog, [("druid", 20)], ruleset), "druid:wild-shape")
    assert ws["unlimited"] is True and ws["uses"] is None and ws["details"]["maxCr"] == "1"


@needs_classes
@pytest.mark.parametrize("level,uses,cr,fly", [
    (2, 2, "1/4", False), (3, 2, "1/4", False), (4, 2, "1/2", False), (6, 3, "1/2", False),
    (8, 3, "1", True), (16, 3, "1", True), (17, 4, "1", True), (20, 4, "1", True),
])
def test_druid_2024_wild_shape(catalog, level, uses, cr, fly):
    ws = _entry(_res(catalog, [("druid", level)], "2024"), "druid:wild-shape")
    assert ws["uses"] == uses and "unlimited" not in ws and ws["recharge"] == "long"
    assert ws["details"]["maxCr"] == cr and ws["details"]["fly"] is fly
    assert ws["details"]["shortRestRegains"] == 1 and "swim" not in ws["details"]


@needs_classes
def test_druid_2024_known_forms(catalog):
    forms = {lvl: _entry(_res(catalog, [("druid", lvl)], "2024"), "druid:wild-shape")["details"]["knownForms"]
             for lvl in (2, 4, 8)}
    assert forms == {2: 4, 4: 6, 8: 8}


# ----------------------------------------------------- degrade + exports


@pytest.mark.parametrize("classes", [[("cleric", 6)], [("paladin", 3)], [("druid", 4)]])
def test_2024_without_tables_falls_back_and_warns_once(catalog, classes):
    cat = copy.copy(catalog)
    cat.class_2024_tables = {}
    res = _res(cat, classes, "2024")
    assert [w["id"] for w in res["warnings"]].count("class-2024-tables-missing") == 1
    assert res["derived"]["classResources"]


def test_export_lines(catalog):
    from export_fields import resource_line
    res = _res(catalog, [("cleric", 5), ("druid", 4)], "2014")
    assert resource_line(_entry(res, "druid:wild-shape")).endswith("макс. CR 1/2")
    assert "макс. CR 1/2" in resource_line(_entry(res, "cleric:destroy-undead"))
    loh = _res(catalog, [("paladin", 5)], "2014")
    assert "пул 25" in resource_line(_entry(loh, "paladin:lay-on-hands"))
