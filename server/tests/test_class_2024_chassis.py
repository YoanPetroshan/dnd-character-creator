"""C1: XPHB class data import (records, class features, weapon masteries). Data only;
no resolve behaviour reads any of it yet.

Numbers verified by script on 2026-10-10 over the real 5etools files: 12 XPHB class
records; 283 XPHB `classFeature` records of the 12 classes, of which 110 are
placeholders (35 "Subclass Feature", 12 "<Class> Subclass", 51 "Ability Score
Improvement", 12 "Epic Boon") leaving 173 imported; 150 of those are named by a class
record's `classFeatures` refs (the per-level list), the other 23 are option/child
records (Protector, Turn Undead, Flurry of Blows, ...). 40 XPHB base items carry a
mastery; 8 masteries. Of the 42 catalog weapons (37 SRD + 5 imported) all but Net,
Double-Bladed Scimitar, Hoopak and Yklwa get one (XPHB has no such base item)."""
import json

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official import items as items_mod
from catalog.official import subclasses as sub_mod
from catalog.official_source import has_official, has_official_classes

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")
needs_items = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

CLASSES = {"barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
           "sorcerer", "warlock", "wizard"}
IMPORTED_XPHB_CLASS_FEATURES = 173
LISTED_XPHB_CLASS_FEATURES = 150
NO_MASTERY_WEAPONS = {"net", "double-bladed-scimitar", "hoopak", "yklwa"}
MASTERIES = {"Cleave", "Graze", "Nick", "Push", "Sap", "Slow", "Topple", "Vex"}


@pytest.fixture(scope="module")
def catalog():
    return load()


# ----------------------------------------------------------------- unit tests

def _class_dir(tmp_path):
    d = tmp_path / "class"
    d.mkdir()
    (d / "index.json").write_text(json.dumps({"fighter": "class-fighter.json"}))
    (d / "class-fighter.json").write_text(json.dumps({
        "class": [
            {"name": "Fighter", "source": "PHB", "classFeatures": ["Old|Fighter||1"]},
            {"name": "Fighter", "source": "XPHB",
             "featProgression": [{"category": ["FS"], "progression": {"1": 1}}],
             "classFeatures": ["Second Wind|Fighter|XPHB|1",
                               {"classFeature": "Fighter Subclass|Fighter|XPHB|3", "gainSubclassFeature": True},
                               "Ability Score Improvement|Fighter|XPHB|4"],
             "startingProficiencies": {"armor": ["light"]}, "multiclassing": {"x": 1}, "startingEquipment": {"y": 2}},
            {"name": "Artificer", "source": "XPHB"}],
        "classFeature": [
            {"name": "Second Wind", "source": "XPHB", "className": "Fighter", "classSource": "XPHB", "level": 1,
             "entries": ["Heal."]},
            {"name": "Fighter Subclass", "source": "XPHB", "className": "Fighter", "classSource": "XPHB", "level": 3},
            {"name": "Subclass Feature", "source": "XPHB", "className": "Fighter", "classSource": "XPHB", "level": 7},
            {"name": "Ability Score Improvement", "source": "XPHB", "className": "Fighter", "classSource": "XPHB", "level": 4},
            {"name": "Epic Boon", "source": "XPHB", "className": "Fighter", "classSource": "XPHB", "level": 19},
            {"name": "Old", "source": "PHB", "className": "Fighter", "level": 1}]}))
    return d


def test_records_and_feature_conversion_from_a_class_dir(tmp_path):
    d = _class_dir(tmp_path)
    records = sub_mod.load_class_2024_records(d)
    assert set(records) == {"fighter"}
    rec = records["fighter"]
    assert rec["feat_progression"] == [{"category": ["FS"], "progression": {"1": 1}}]
    assert rec["features"][0] == {"name": "Second Wind", "level": 1, "ref": "Second Wind|Fighter|XPHB|1"}
    assert [f["name"] for f in rec["features"]] == ["Second Wind", "Fighter Subclass", "Ability Score Improvement"]
    assert rec["starting_proficiencies"] == {"armor": ["light"]} and rec["multiclassing"] == {"x": 1}
    assert rec["starting_equipment"] == {"y": 2}
    features, by_level = sub_mod.convert_class_features_2024(sub_mod.load_raw_class_features_2024(d), records)
    assert set(features) == {"xphb-fighter-1-second-wind"}
    assert features["xphb-fighter-1-second-wind"] == {
        "index": "xphb-fighter-1-second-wind", "name": "Second Wind", "level": 1,
        "class": {"index": "fighter", "name": "Fighter"}, "desc": ["Heal."], "source": "XPHB", "ruleset": "2024"}
    assert by_level == {"fighter": {1: ["xphb-fighter-1-second-wind"]}}
    assert sub_mod.load_class_2024_records(None) == {}
    assert sub_mod.load_class_2024_records(tmp_path / "nope") == {}
    assert sub_mod.convert_class_features_2024([], {}) == ({}, {})


def test_mastery_attachment_normalizes_names():
    raw = [{"name": "Light Crossbow", "source": "XPHB", "type": "R|XPHB", "mastery": ["Slow|XPHB"]},
           {"name": "Longsword", "source": "XPHB", "type": "M|XPHB", "mastery": ["Sap|XPHB"]},
           {"name": "Longsword", "source": "PHB", "type": "M|PHB", "mastery": ["Wrong|PHB"]},
           {"name": "Net", "source": "XPHB", "type": "R|XPHB"}]
    items = {"crossbow-light": {"name": "Crossbow, light", "equipment_category": {"index": "weapon"}},
             "longsword": {"name": "Longsword", "equipment_category": {"index": "weapon"}},
             "net": {"name": "Net", "equipment_category": {"index": "weapon"}},
             "plate": {"name": "Longsword", "equipment_category": {"index": "armor"}}}
    assert items_mod.attach_masteries(items, raw, {"Slow": [], "Sap": []}) == 2
    assert items["crossbow-light"]["mastery"] == "Slow" and items["longsword"]["mastery"] == "Sap"
    assert "mastery" not in items["net"] and "mastery" not in items["plate"]


def test_srd_only_catalog_has_empty_new_fields(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    monkeypatch.setattr(official_source, "items_base_file", lambda: None)
    cat = load()
    assert cat.class_2024_records == {} and cat.class_2024_level_features == {} and cat.weapon_masteries == {}
    assert len(cat.classes) == 12
    assert not any(i.get("mastery") for i in cat.items.values())
    assert not any(f.startswith("xphb-") for f in cat.features)


# ----------------------------------------------------------------- real data

@needs_classes
def test_twelve_class_records(catalog):
    assert set(catalog.class_2024_records) == CLASSES
    for name, rec in catalog.class_2024_records.items():
        assert set(rec) == {"feat_progression", "features", "starting_proficiencies", "multiclassing",
                            "starting_equipment", "saving_throws", "primary_ability"}  # last two: C9a
        assert rec["features"] and rec["starting_proficiencies"] and rec["starting_equipment"]
        # XPHB gives monk, sorcerer and wizard an empty multiclassing record (no extra proficiencies)
        assert bool(rec["multiclassing"]) == (name not in {"monk", "sorcerer", "wizard"})


@needs_classes
def test_fighter_feat_progression(catalog):
    prog = {tuple(p["category"]): p["progression"] for p in catalog.class_2024_records["fighter"]["feat_progression"]}
    assert prog[("FS",)] == {"1": 1}
    assert prog[("EB",)] == {"19": 1}
    paladin = {tuple(p["category"]) for p in catalog.class_2024_records["paladin"]["feat_progression"]}
    assert ("FS", "FS:P") in paladin


@needs_classes
def test_imported_class_feature_count_and_shape(catalog):
    imported = {k: f for k, f in catalog.features.items() if k.startswith("xphb-")}
    assert len(imported) == IMPORTED_XPHB_CLASS_FEATURES
    assert not any(f["name"] in ("Subclass Feature", "Ability Score Improvement", "Epic Boon")
                   or f["name"].endswith(" Subclass") for f in imported.values())
    for k, f in imported.items():
        assert f["index"] == k and f["source"] == "XPHB" and f["ruleset"] == "2024"
        assert k.startswith(f"xphb-{f['class']['index']}-{f['level']}-") and f["desc"]
    sw = catalog.features["xphb-fighter-1-second-wind"]
    assert sw["name"] == "Second Wind" and sw["level"] == 1 and sw["class"]["index"] == "fighter"


@needs_classes
def test_no_id_collisions_with_srd_features(catalog):
    srd_ids = {f["index"] for f in load_srd_features()}
    imported = {k for k in catalog.features if k.startswith("xphb-")}
    assert not srd_ids & imported
    assert srd_ids <= set(catalog.features)
    assert all(not catalog.features[i].get("source", "SRD") == "XPHB" for i in srd_ids)


def load_srd_features():
    import catalog.loader as loader
    return loader._load_srd("5e-SRD-Features.json")


@needs_classes
def test_class_2024_level_features(catalog):
    lf = catalog.class_2024_level_features
    assert set(lf) == CLASSES
    assert sum(len(ids) for by in lf.values() for ids in by.values()) == LISTED_XPHB_CLASS_FEATURES
    assert all(i in catalog.features and catalog.features[i]["level"] == lvl for by in lf.values()
               for lvl, ids in by.items() for i in ids)
    assert "xphb-fighter-2-action-surge" in lf["fighter"][2]
    assert "xphb-cleric-2-protector" not in lf["cleric"][1]  # option records are catalog.features only
    assert 3 not in lf["fighter"]  # subclass placeholder at 3 skipped


@needs_items
def test_weapon_masteries_on_items(catalog):
    assert catalog.items["longsword"]["mastery"] == "Sap"
    assert catalog.items["crossbow-light"]["mastery"] == "Slow"
    assert catalog.items["crossbow-hand"]["mastery"] == "Vex"
    assert catalog.items["musket"]["mastery"] == "Slow" and catalog.items["pistol"]["mastery"] == "Vex"
    weapons = {k for k, v in catalog.items.items() if v.get("equipment_category", {}).get("index") == "weapon"}
    assert len(weapons) == 42
    assert {k for k in weapons if not catalog.items[k].get("mastery")} == NO_MASTERY_WEAPONS
    assert {catalog.items[k]["mastery"] for k in weapons - NO_MASTERY_WEAPONS} <= MASTERIES
    assert not any("mastery" in v for k, v in catalog.items.items() if k not in weapons)


@needs_items
def test_weapon_masteries_table(catalog):
    assert set(catalog.weapon_masteries) == MASTERIES
    assert len(catalog.weapon_masteries) == 8
    assert all(isinstance(d, list) and d for d in catalog.weapon_masteries.values())
