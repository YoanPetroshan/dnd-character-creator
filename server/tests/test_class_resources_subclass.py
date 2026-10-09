"""R6: subclass resources (Psi Warrior, Soulknife, Battle Master, Arcane Archer).

Rule matrix (verified by script against the imported feature texts and the XPHB
subclass tables; see ARCHITECTURE R6). Entries have source.kind "subclass" and
appear right after their class's own entries. A subclass resource exists only
once the class reaches the level of the subclass's first feature (3).

Psi Warrior / Soulknife, TCE (2014) `*-tce-3-psionic-power`: "a number of these
dice equal to twice your proficiency bonus"; d6, "at 5th level (d8), 11th level
(d10), and 17th level (d12)"; all dice back on a long rest, plus a bonus action
to regain one (once per short/long rest). PB is the character's (total level).
  Cases: L3 PB2 -> 4d6 | L5 PB3 -> 6d8 | L11 PB4 -> 8d10 | L17 PB6 -> 12d12
         | PB follows total level in a multiclass (Fighter 3 / Cleric 6 -> PB 4 -> 8d6)
Psi Warrior / Soulknife, XPHB (2024) "Energy Dice" table (subclass_2024_tables
`die-size` / `number`): 3-4 4xd6 | 5-8 6xd8 | 9-10 8xd8 | 11-12 8xd10 |
13-16 10xd10 | 17-20 12xd12; one die back on a short rest, all on a long rest.
  Cases: XPHB record under ruleset 2024 -> table (L9 8xd8, L13 10xd10).
         XPHB record under 2014/mixed -> never reads the 2024 table; falls back to
         the 2014 formula. TCE record under 2024 -> formula (the record's own edition).
         Empty subclass_2024_tables under 2024 -> formula plus the warning
         `subclass-2024-tables-missing`.

Battle Master (PHB `combat-superiority`; XPHB identical numbers): 4 superiority
dice (d8), 5 at fighter 7, 6 at 15; d10 at 10 ("Improved Combat Superiority"),
d12 at 18 (PHB) / XPHB "Ultimate Combat Superiority" d12 at 18; short or long
rest. Save DC = 8 + proficiency bonus + STR or DEX modifier (PHB abilityDc
str/dex; XPHB "your choice"), so the larger of the two. Same under every ruleset.
  Cases: L3 STR16 -> 4d8 DC 13 | L7 5 dice | L10 d10 | L15 6 dice | L18 d12
         | DEX better than STR -> DC from DEX | L2 (no subclass features yet) -> none.

Arcane Archer (XGE `arcane-shot`): "You have two uses of this ability, and you
regain all expended uses ... short or long rest." Cases: L3 2 uses
short-or-long, L18 still 2 uses; L2 none.

Not resources / skipped: see ARCHITECTURE R6 (Rune Knight, Bladesinging, ...).
"""
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
    """classes: (classId, level[, subclassId]) tuples."""
    base = {"STR": 10, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = []
    for c in classes:
        e = {"classId": c[0], "level": c[1], "choices": {}}
        if len(c) > 2:
            e["subclassId"] = c[2]
        entries.append(e)
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _dice(r):
    return (r["uses"], r["die"])


# ------------------------------------------------- Psi Warrior / Soulknife, 2014


@pytest.mark.parametrize("cls,sub", [("fighter", "psi-warrior-tce"), ("rogue", "soulknife-tce")])
@pytest.mark.parametrize("level,expected", [(3, (4, "d6")), (4, (4, "d6")), (5, (6, "d8")), (10, (8, "d8")),
                                            (11, (8, "d10")), (16, (10, "d10")), (17, (12, "d12")), (20, (12, "d12"))])
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_tce_psionic_dice_formula(catalog, cls, sub, level, expected, ruleset):
    r = _entry(_res(catalog, [(cls, level, sub)], ruleset), f"{cls}:psionic-energy-dice")
    # PB: 2 at 3-4, 3 at 5-8, 4 at 9-12, 5 at 13-16, 6 at 17-20 -> 2 x PB dice
    assert _dice(r) == expected
    assert r["recharge"] == "long"
    assert r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["details"]["bonusActionRegainsOne"] is True


def test_tce_dice_follow_total_level_proficiency_bonus(catalog):
    res = _res(catalog, [("fighter", 3, "psi-warrior-tce"), ("cleric", 6)], "mixed")
    assert res["derived"]["proficiencyBonus"] == 4
    assert _dice(_entry(res, "fighter:psionic-energy-dice")) == (8, "d6")  # die size by FIGHTER level


def test_psi_warrior_below_level_3_has_no_subclass_resource(catalog):
    res = _res(catalog, [("fighter", 2, "psi-warrior-tce")], "mixed")
    assert _entry(res, "fighter:psionic-energy-dice") is None


def test_soulknife_and_psi_warrior_both_present_in_multiclass(catalog):
    res = _res(catalog, [("fighter", 3, "psi-warrior-tce"), ("rogue", 3, "soulknife-tce")], "mixed")
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert "fighter:psionic-energy-dice" in ids and "rogue:psionic-energy-dice" in ids


# ------------------------------------------------- Psi Warrior / Soulknife, 2024


@needs_classes
@pytest.mark.parametrize("cls,sub", [("fighter", "psi-warrior-xphb"), ("rogue", "soulknife-xphb")])
@pytest.mark.parametrize("level,expected", [(3, (4, "d6")), (5, (6, "d8")), (8, (6, "d8")), (9, (8, "d8")),
                                            (11, (8, "d10")), (13, (10, "d10")), (16, (10, "d10")),
                                            (17, (12, "d12")), (20, (12, "d12"))])
def test_xphb_psionic_dice_table_under_2024(catalog, cls, sub, level, expected):
    r = _entry(_res(catalog, [(cls, level, sub)], "2024"), f"{cls}:psionic-energy-dice")
    assert _dice(r) == expected
    assert r["recharge"] == "long"
    assert r["details"] == {"shortRestRegains": 1}


@needs_classes
def test_xphb_table_matches_the_feature_text_table(catalog):
    text = "\n".join(catalog.features["psi-warrior-xphb-3-psionic-power"]["desc"])
    for lvl, die, n in [(3, "D6", 4), (5, "D8", 6), (9, "D8", 8), (11, "D10", 8), (13, "D10", 10), (17, "D12", 12)]:
        assert f"{lvl} | {die} | {n}" in text
        t = catalog.subclass_2024_tables["psi-warrior-xphb"]
        assert (t["number"][lvl - 1], t["die-size"][lvl - 1]) == (n, die.lower())


@needs_classes
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_xphb_record_never_reads_2024_table_outside_2024(catalog, ruleset):
    # Prove the table is never touched: count reads of the catalog attribute.
    class Spy:
        def __init__(self, c):
            self._c = c
            self.reads = 0

        def __getattr__(self, name):
            if name == "subclass_2024_tables":
                self.reads += 1
            return getattr(self._c, name)
    spy = Spy(catalog)
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": "fighter", "level": 7, "subclassId": "psi-warrior-xphb", "choices": {}}]}
    r = _entry(resolve(d, spy), "fighter:psionic-energy-dice")
    assert spy.reads == 0
    assert _dice(r) == (6, "d8")  # 2 x PB 3, formula


def test_tce_record_under_2024_uses_formula(catalog):
    r = _entry(_res(catalog, [("fighter", 5, "psi-warrior-tce")], "2024"), "fighter:psionic-energy-dice")
    assert _dice(r) == (6, "d8") and r["details"]["bonusActionRegainsOne"] is True


def test_xphb_degrades_to_formula_without_tables_and_warns_once(catalog):
    class NoTables:
        subclass_2024_tables = {}
    warns: list = []
    rc = {"cls_id": "fighter", "level": 9, "cls": {"name": "Fighter"}, "subclass_id": "psi-warrior-xphb",
          "subclass": {"name": "Psi Warrior"}, "level_row": {"class_specific": {}}}
    out = resources_for(NoTables(), [rc], {}, 4, "2024", None, warns)
    assert [(r["uses"], r["die"]) for r in out if r["source"]["kind"] == "subclass"] == [(8, "d8")]  # 2 x PB 4, d8 at 9
    assert [w["id"] for w in warns].count("subclass-2024-tables-missing") == 1  # once (the Fighter adds its own class warning)


# ------------------------------------------------------------- Battle Master


@pytest.mark.parametrize("sub,ruleset", [("battle-master-phb", "2014"), ("battle-master-phb", "mixed"),
                                         ("battle-master-xphb", "2024"), ("battle-master-xphb", "mixed")])
@pytest.mark.parametrize("level,n,die", [(3, 4, "d8"), (6, 4, "d8"), (7, 5, "d8"), (9, 5, "d8"), (10, 5, "d10"),
                                         (14, 5, "d10"), (15, 6, "d10"), (17, 6, "d10"), (18, 6, "d12"), (20, 6, "d12")])
def test_superiority_dice(catalog, sub, ruleset, level, n, die):
    if sub.endswith("xphb") and ruleset == "2024" and not has_official_classes():
        pytest.skip("5etools class files not available")
    r = _entry(_res(catalog, [("fighter", level, sub)], ruleset), "fighter:superiority-dice")
    assert _dice(r) == (n, die)
    assert r["recharge"] == "short-or-long"
    assert r["source"]["kind"] == "subclass" and r["source"]["id"] == sub


def test_maneuver_dc_uses_strength_when_better(catalog):
    # STR 16 (+1 human = 17, +3); fighter 3 -> PB 2 -> 8 + 2 + 3 = 13
    r = _entry(_res(catalog, [("fighter", 3, "battle-master-phb")], "2014", {"STR": 16}), "fighter:superiority-dice")
    assert r["dc"] == 13


def test_maneuver_dc_uses_dexterity_when_better(catalog):
    res = _res(catalog, [("fighter", 5, "battle-master-phb")], "2014", {"STR": 8, "DEX": 18})  # DEX 19 -> +4, PB 3
    assert _entry(res, "fighter:superiority-dice")["dc"] == 8 + 3 + 4


def test_maneuver_dc_follows_total_level_proficiency_bonus(catalog):
    res = _res(catalog, [("fighter", 3, "battle-master-phb"), ("cleric", 6)], "2014", {"STR": 16})
    assert res["derived"]["proficiencyBonus"] == 4
    assert _entry(res, "fighter:superiority-dice")["dc"] == 8 + 4 + 3


def test_battle_master_level_2_has_no_dice(catalog):
    assert _entry(_res(catalog, [("fighter", 2, "battle-master-phb")], "mixed"), "fighter:superiority-dice") is None


def test_champion_and_no_subclass_have_no_subclass_entries(catalog):
    for sub in ("champion-phb", None):
        c = ("fighter", 10, sub) if sub else ("fighter", 10)
        res = _res(catalog, [c], "mixed")
        assert all(r["source"]["kind"] == "class" for r in res["derived"]["classResources"])


# -------------------------------------------------------------- Arcane Archer


@pytest.mark.parametrize("level", [3, 7, 18, 20])
def test_arcane_shot_two_uses_short_or_long(catalog, level):
    r = _entry(_res(catalog, [("fighter", level, "arcane-archer-xge")], "mixed"), "fighter:arcane-shot")
    assert r["uses"] == 2 and r["recharge"] == "short-or-long"
    assert r["source"]["kind"] == "subclass" and r["source"]["id"] == "arcane-archer-xge"


def test_arcane_archer_level_2_has_none(catalog):
    assert _entry(_res(catalog, [("fighter", 2, "arcane-archer-xge")], "mixed"), "fighter:arcane-shot") is None


# ------------------------------------------------------------ order / timing


def test_subclass_entries_follow_their_class_entries(catalog):
    res = _res(catalog, [("fighter", 3, "battle-master-phb"), ("rogue", 3, "soulknife-tce")], "mixed")
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert ids == ["fighter:second-wind", "fighter:action-surge", "fighter:superiority-dice", "rogue:sneak-attack", "rogue:psionic-energy-dice"]


def test_subclass_resources_resolve_under_50_ms(catalog):
    for cls, lvl, sub in (("fighter", 11, "psi-warrior-tce"), ("fighter", 15, "battle-master-phb")):
        _res(catalog, [(cls, lvl, sub)], "mixed")
        t = time.perf_counter()
        for _ in range(20):
            _res(catalog, [(cls, lvl, sub)], "mixed")
        assert (time.perf_counter() - t) / 20 < 0.05
