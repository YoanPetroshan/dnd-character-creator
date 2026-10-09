"""O3: 2024 (XPHB) spell counts and the half-caster round-up, only under ruleset
"2024". Expected numbers were read off the XPHB class records
(cantripProgression / preparedSpellsProgression, class-*.json in the 5etools
data) and the Paladin slot table was checked against ceil(level/2) of the
full-caster table for all 20 levels, by script on 2026-10-09."""
import json

import pytest

from catalog.loader import load
from catalog.official import subclasses as sub_mod
from catalog.official_source import has_official_classes
from engine import spells as spells_mod
from engine.resolve import resolve

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def test_loader_reads_the_xphb_progressions_from_a_class_dir(tmp_path):
    d = tmp_path / "class"
    d.mkdir()
    (d / "index.json").write_text(json.dumps({"wizard": "class-wizard.json", "fighter": "class-fighter.json"}))
    (d / "class-wizard.json").write_text(json.dumps({"class": [
        {"name": "Wizard", "source": "PHB", "cantripProgression": [3] * 20},
        {"name": "Wizard", "source": "XPHB", "casterProgression": "full", "cantripProgression": [3] * 20,
         "preparedSpellsProgression": list(range(4, 24))}]}))
    (d / "class-fighter.json").write_text(json.dumps({"class": [{"name": "Fighter", "source": "XPHB"}]}))
    prog = sub_mod.load_class_2024_progressions(d)
    assert set(prog) == {"wizard"}
    assert prog["wizard"] == {"caster": "full", "cantrips": [3] * 20, "prepared": list(range(4, 24))}
    assert sub_mod.load_class_2024_progressions(None) == {}
    assert sub_mod.load_class_2024_progressions(tmp_path / "nope") == {}


@needs_classes
def test_real_catalog_has_the_eight_casters(catalog):
    prog = catalog.class_2024_progressions
    assert set(prog) == {"bard", "cleric", "druid", "paladin", "ranger", "sorcerer", "warlock", "wizard"}
    assert prog["wizard"]["prepared"][4] == 9 and prog["wizard"]["cantrips"][0] == 3
    assert prog["paladin"]["caster"] == "artificer" and prog["paladin"]["cantrips"] == []
    assert prog["ranger"]["prepared"] == [2, 3, 4, 5, 6, 6, 7, 7, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 15, 15]
    assert all(len(p["prepared"]) == 20 for p in prog.values())


_BASE = {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 14, "CHA": 12}


def _res(catalog, classes, ruleset):
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": dict(_BASE)},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": c, "level": lv, "choices": {}} for c, lv in classes]}
    return resolve(d, catalog)


def _counts(res, cls):
    def pick(suffix):
        ch = next((c for c in res["choices"] if c["id"] == f"class:{cls}:spells-{suffix}"), None)
        return (ch["count"], ch["label"]) if ch else None
    return pick("cantrips"), pick("known")


@needs_classes
@pytest.mark.parametrize("cls,level,cantrips,prepared", [
    ("wizard", 1, 3, 4), ("wizard", 5, 4, 9), ("wizard", 20, 5, 25),
    ("cleric", 1, 3, 4), ("cleric", 5, 4, 9),
    ("sorcerer", 1, 4, 2), ("sorcerer", 5, 5, 9),
    ("bard", 10, 4, 15), ("druid", 3, 2, 6),
    ("warlock", 1, 2, 2), ("warlock", 10, 4, 10),
])
def test_2024_counts_come_from_the_xphb_tables(catalog, cls, level, cantrips, prepared):
    cant, known = _counts(_res(catalog, [(cls, level)], "2024"), cls)
    assert cant == (cantrips, "Cantrips Known")
    assert known == (prepared, "Prepared Spells")  # every 2024 caster prepares


@needs_classes
@pytest.mark.parametrize("cls,level,prepared", [
    ("paladin", 1, 2), ("paladin", 2, 3), ("paladin", 5, 6), ("paladin", 9, 9), ("paladin", 20, 15),
    ("ranger", 1, 2), ("ranger", 9, 9),
])
def test_2024_half_casters_prepare_from_level_1(catalog, cls, level, prepared):
    cant, known = _counts(_res(catalog, [(cls, level)], "2024"), cls)
    assert cant is None and known == (prepared, "Prepared Spells")


@needs_classes
@pytest.mark.parametrize("level,slots", [
    (1, {"1": 2}), (2, {"1": 2}), (3, {"1": 3}), (4, {"1": 3}), (5, {"1": 4, "2": 2}),
    (9, {"1": 4, "2": 3, "3": 2}), (20, {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2}),
])
def test_2024_paladin_and_ranger_slots_round_up(catalog, level, slots):
    for cls in ("paladin", "ranger"):
        assert _res(catalog, [(cls, level)], "2024")["derived"]["spellSlots"] == slots


@needs_classes
def test_2024_multiclass_rounds_half_casters_up(catalog):
    res = _res(catalog, [("paladin", 3), ("wizard", 3)], "2024")
    assert res["derived"]["spellSlots"] == {"1": 4, "2": 3, "3": 2}  # 2 + 3 = caster level 5
    res = _res(catalog, [("ranger", 1), ("cleric", 1)], "2024")
    assert res["derived"]["spellSlots"] == {"1": 3}  # 1 + 1 = 2
    assert spells_mod.combined_caster_level([("paladin", 3), ("wizard", 3)], catalog, "2024") == 5
    assert spells_mod.combined_caster_level([("paladin", 3), ("wizard", 3)], catalog) == 4


@needs_classes
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_other_rulesets_are_unchanged(catalog, ruleset):
    cant, known = _counts(_res(catalog, [("wizard", 5)], ruleset), "wizard")
    assert cant == (4, "Cantrips Known") and known == (8, "Prepared Spells")  # INT 16 (+3) + level 5
    cant, known = _counts(_res(catalog, [("bard", 10)], ruleset), "bard")
    assert known == (14, "Spells Known")
    assert _res(catalog, [("paladin", 1)], ruleset)["derived"]["spellSlots"] == {}
    assert _res(catalog, [("paladin", 3), ("wizard", 3)], ruleset)["derived"]["spellSlots"] == {"1": 4, "2": 3}
    _, known = _counts(_res(catalog, [("paladin", 5)], ruleset), "paladin")
    assert known == (3, "Prepared Spells")  # CHA 12 (+1) + 5 // 2


@needs_classes
def test_2024_third_casters_are_unaffected(catalog):
    d = {"ruleset": "2024", "sources": [], "abilities": {"method": "manual", "base": dict(_BASE)},
         "classes": [{"classId": "fighter", "level": 3, "subclassId": "eldritch-knight-xphb", "choices": {}}]}
    res = resolve(d, catalog)
    assert res["derived"]["spellSlots"] == {"1": 2}
    assert _counts(res, "fighter") == ((2, "Cantrips Known"), (3, "Prepared Spells"))
