"""R1: class resources (derived.classResources), Barbarian and Rogue.

Rules quoted (SRD 5.1 / XPHB), and the cases the tests tell apart:
* Rage (Barbarian): uses per long rest and a damage bonus that grow with level.
  2014: rage_count 2,2,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6 and "unlimited" at 20
  (the SRD row stores 9999); damage +2 (1-8), +3 (9-15), +4 (16-20).
  2024 (XPHB table): the same uses but 6 at level 20 (no unlimited), the same damage.
* Sneak Attack (Rogue): ceil(level / 2) d6 in both editions (verified equal).
* Ruleset rule (U9): 2024 numbers only under ruleset "2024"; "mixed" and "2014"
  use the SRD rows. With no 2024 tables the engine falls back to the SRD rows
  and warns once (`class-2024-tables-missing`).
Expected numbers were read from the SRD level rows and the XPHB class tables by
script on 2026-10-09.
"""
import copy
import io
import json

import pytest
import yaml
from pypdf import PdfReader

from catalog.loader import load
from catalog.official import subclasses as sub_mod
from catalog.official_source import has_official_classes
from engine import class_resources as cr
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

_BASE = {"STR": 15, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed"):
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": dict(_BASE)},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": c, "level": lv, "choices": {}} for c, lv in classes]}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


# ------------------------------------------------------------------ loader


def _write_class_dir(tmp_path):
    d = tmp_path / "class"
    d.mkdir()
    (d / "index.json").write_text(json.dumps({"barbarian": "class-barbarian.json", "rogue": "class-rogue.json"}))
    rows = [[str(i), {"type": "bonus", "value": 2 + i // 10}, {"type": "bonusSpeed", "value": 5}, 7, "{@dice D6}"]
            for i in range(20)]
    (d / "class-barbarian.json").write_text(json.dumps({"class": [
        {"name": "Barbarian", "source": "PHB", "classTableGroups": [{"colLabels": ["Ignored"], "rows": [[1]] * 20}]},
        {"name": "Barbarian", "source": "XPHB", "classTableGroups": [
            {"colLabels": ["Rages", "Rage Damage", "{@tip Unarmored Movement|x}", "{@filter Cantrips|spells|level=0|class=barbarian}",
                           "{@filter Invocations|optionalfeatures|feature type=ei}"], "rows": rows},
            {"title": "Spell Slots per Spell Level", "colLabels": ["{@filter 1st|spells|level=1}"],
             "rowsSpellProgression": [[1]] * 20},
            {"colLabels": ["Spell Slots", "Slot Level"], "rows": [[1, 1]] * 20},
        ]}]}))
    (d / "class-rogue.json").write_text(json.dumps({
        "class": [{"name": "Rogue", "source": "XPHB", "classTableGroups": [
            {"colLabels": ["Sneak Attack"], "rows": [[{"type": "dice", "toRoll": [{"number": (i // 2) + 1, "faces": 6}]}]
                                                       for i in range(20)]}]}],
        "subclass": [{"name": "Soulknife", "shortName": "Soulknife", "source": "XPHB", "className": "Rogue",
                      "classSource": "XPHB", "subclassTableGroups": [
                          {"colLabels": ["{@tip Die Size|Soulknife Energy Die Size}", "{@tip Number|n}"],
                           "rows": [["{@dice D6}", 4]] * 20},
                          {"colLabels": ["{@filter Spells|spells|subclass=x}"], "rows": [[3]] * 20}]}]}))
    return d


def test_loader_reads_the_xphb_class_tables_from_a_class_dir(tmp_path):
    d = _write_class_dir(tmp_path)
    tables = sub_mod.load_class_2024_tables(d)
    assert set(tables) == {"barbarian", "rogue"}
    barb = tables["barbarian"]
    assert barb["rages"][:3] == [0, 1, 2] and barb["rages"][19] == 19  # digit strings become ints, 0 stays 0
    assert barb["rage-damage"][0] == 2 and barb["rage-damage"][19] == 3  # {type: bonus} -> value
    assert barb["unarmored-movement"][0] == 5  # {type: bonusSpeed} -> value, {@tip X|y} -> slug of X
    assert barb["invocations"][0] == "d6"  # a non-spell {@filter} column is kept; {@dice D6} -> "d6"
    assert "cantrips" not in barb and "spell-slots" not in barb and "slot-level" not in barb  # spell columns skipped
    assert "ignored" not in barb  # PHB records are not read
    assert tables["rogue"]["sneak-attack"][0] == "1d6" and tables["rogue"]["sneak-attack"][19] == "10d6"
    assert sub_mod.load_class_2024_tables(None) == {}
    assert sub_mod.load_class_2024_tables(tmp_path / "nope") == {}


def test_loader_reads_the_xphb_subclass_tables(tmp_path):
    d = _write_class_dir(tmp_path)
    sub = sub_mod.load_subclass_2024_tables(d)
    assert set(sub) == {"soulknife-xphb"}
    assert sub["soulknife-xphb"]["die-size"][0] == "d6" and sub["soulknife-xphb"]["number"][0] == 4
    assert "spells" not in sub["soulknife-xphb"]
    assert sub_mod.load_subclass_2024_tables(None) == {}


@needs_classes
def test_real_catalog_class_tables(catalog):
    t = catalog.class_2024_tables
    assert t["barbarian"]["rages"][19] == 6 and t["barbarian"]["rage-damage"][8] == 3
    assert t["fighter"]["weapon-mastery"][15] == 6
    assert t["cleric"]["channel-divinity"][17] == 4
    assert t["rogue"]["sneak-attack"][4] == "3d6" and t["monk"]["martial-arts"][19] == "1d12"
    assert "cantrips" not in t["cleric"] and "prepared-spells" not in t["cleric"]
    sub = catalog.subclass_2024_tables
    assert sub["psi-warrior-xphb"]["die-size"][2] == "d6" and sub["psi-warrior-xphb"]["number"][19] == 12
    assert sub["soulknife-xphb"]["number"][4] == 6


# ------------------------------------------------------------ Barbarian


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("level,uses,bonus", [(1, 2, 2), (3, 3, 2), (8, 4, 2), (9, 4, 3), (12, 5, 3), (15, 5, 3), (16, 5, 4), (19, 6, 4)])
def test_barbarian_rage_uses_srd_numbers_outside_2024(catalog, ruleset, level, uses, bonus):
    rage = _entry(_res(catalog, [("barbarian", level)], ruleset), "barbarian:rage")
    assert rage["name"] == "Rage" and rage["classId"] == "barbarian" and rage["recharge"] == "long"
    assert rage["uses"] == uses and "unlimited" not in rage
    assert rage["details"]["damageBonus"] == bonus
    assert rage["details"]["resistances"] == ["bludgeoning", "piercing", "slashing"]
    assert rage["source"] == {"kind": "class", "id": "barbarian", "label": "Barbarian"}


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_barbarian_20_has_unlimited_rages_outside_2024(catalog, ruleset):
    rage = _entry(_res(catalog, [("barbarian", 20)], ruleset), "barbarian:rage")
    assert rage["unlimited"] is True and rage["uses"] is None and rage["details"]["damageBonus"] == 4


@needs_classes
@pytest.mark.parametrize("level,uses,bonus", [(1, 2, 2), (9, 4, 3), (16, 5, 4), (17, 6, 4), (20, 6, 4)])
def test_barbarian_rage_2024_uses_the_xphb_table(catalog, level, uses, bonus):
    rage = _entry(_res(catalog, [("barbarian", level)], "2024"), "barbarian:rage")
    assert rage["uses"] == uses and "unlimited" not in rage and rage["details"]["damageBonus"] == bonus


@needs_classes
def test_mixed_does_not_use_the_2024_tables(catalog):
    assert _entry(_res(catalog, [("barbarian", 20)], "mixed"), "barbarian:rage")["unlimited"] is True


# ---------------------------------------------------------------- Rogue


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
@pytest.mark.parametrize("level,dice", [(1, "1d6"), (2, "1d6"), (3, "2d6"), (5, "3d6"), (11, "6d6"), (19, "10d6"), (20, "10d6")])
def test_rogue_sneak_attack_dice_all_rulesets(catalog, ruleset, level, dice):
    sneak = _entry(_res(catalog, [("rogue", level)], ruleset), "rogue:sneak-attack")
    assert sneak["name"] == "Sneak Attack" and sneak["dice"] == dice and sneak["uses"] is None
    assert sneak["recharge"] is None and sneak["classId"] == "rogue"


@needs_classes
def test_rogue_2024_table_equals_the_srd_rows_at_every_level(catalog):
    table = catalog.class_2024_tables["rogue"]["sneak-attack"]
    for lv in range(1, 21):
        cs = catalog.class_level_row("rogue", lv)["class_specific"]["sneak_attack"]
        assert table[lv - 1] == f"{cs['dice_count']}d{cs['dice_value']}"


@needs_classes
def test_barbarian_2024_table_matches_the_srd_except_level_20(catalog):
    for lv in range(1, 21):
        cs = catalog.class_level_row("barbarian", lv)["class_specific"]
        assert catalog.class_2024_tables["barbarian"]["rage-damage"][lv - 1] == cs["rage_damage_bonus"]
        if lv < 20:
            assert catalog.class_2024_tables["barbarian"]["rages"][lv - 1] == cs["rage_count"]
    assert catalog.class_level_row("barbarian", 20)["class_specific"]["rage_count"] == 9999


# ------------------------------------------------------ multiclass, none


def test_multiclass_barbarian_rogue_gets_one_entry_per_class_in_class_order(catalog):
    res = _res(catalog, [("barbarian", 3), ("rogue", 3)])
    ids = [(r["id"], r["classId"]) for r in res["derived"]["classResources"]]
    assert ids == [("barbarian:rage", "barbarian"), ("rogue:sneak-attack", "rogue")]
    assert _entry(res, "barbarian:rage")["uses"] == 3 and _entry(res, "rogue:sneak-attack")["dice"] == "2d6"
    swapped = _res(catalog, [("rogue", 3), ("barbarian", 3)])
    assert [r["classId"] for r in swapped["derived"]["classResources"]] == ["rogue", "barbarian"]


def test_class_without_a_builder_has_no_entries(catalog):
    assert _res(catalog, [("wizard", 1)])["derived"]["classResources"] == []
    assert _res(catalog, [("fighter", 5)])["derived"]["classResources"] == []  # until R2


def test_unknown_class_does_not_crash(catalog):
    res = resolve({"classes": [{"classId": "nonsense", "level": 1, "choices": {}}]}, catalog)
    assert res["derived"]["classResources"] == []


# --------------------------------------------- graceful degradation (2024)


def _empty_tables(catalog):
    cat = copy.copy(catalog)
    cat.class_2024_tables = {}
    cat.subclass_2024_tables = {}
    return cat


def test_2024_without_tables_falls_back_to_srd_and_warns_once(catalog):
    cat = _empty_tables(catalog)
    res = _res(cat, [("barbarian", 20), ("rogue", 5)], "2024")
    assert _entry(res, "barbarian:rage")["unlimited"] is True  # SRD number
    assert _entry(res, "rogue:sneak-attack")["dice"] == "3d6"
    assert [w["id"] for w in res["warnings"]].count("class-2024-tables-missing") == 1


def test_missing_tables_warning_only_under_2024_and_only_with_a_table_class(catalog):
    cat = _empty_tables(catalog)
    assert "class-2024-tables-missing" not in [w["id"] for w in _res(cat, [("barbarian", 5)], "mixed")["warnings"]]
    assert "class-2024-tables-missing" not in [w["id"] for w in _res(cat, [("wizard", 5)], "2024")["warnings"]]


def test_resources_for_is_pure_and_reports_through_warnings_out(catalog):
    cat = _empty_tables(catalog)
    rc = {"index": 0, "cls_id": "barbarian", "cls": {"name": "Barbarian"}, "level": 4, "subclass_id": None, "subclass": None,
          "level_row": catalog.class_level_row("barbarian", 4)}
    out: list = []
    result = cr.resources_for(cat, [rc], {}, 2, "2024", {}, warnings_out=out)
    assert result[0]["uses"] == 3 and [w["id"] for w in out] == ["class-2024-tables-missing"]


# ---------------------------------------------------------------- exports


def test_yaml_carries_class_resources(catalog):
    res = _res(catalog, [("barbarian", 5)])
    doc = yaml.safe_load(to_yaml(res))
    assert doc["classResources"] == res["derived"]["classResources"]
    assert doc["classResources"][0]["name"] == "Rage"


def test_markdown_and_pdf_list_class_resources(catalog):
    res = _res(catalog, [("barbarian", 5), ("rogue", 3)])
    md = to_markdown(res)
    assert "## Ресурси на класа" in md
    assert "- Rage: 3 (дълга почивка), щета +2" in md
    assert "- Sneak Attack: 2d6" in md
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "Ресурси на класа" in text and "Rage: 3" in text


def test_unlimited_rage_is_printed_as_unlimited(catalog):
    md = to_markdown(_res(catalog, [("barbarian", 20)]))
    assert "- Rage: без ограничение (дълга почивка), щета +4" in md


def test_no_resources_block_for_a_non_resource_class(catalog):
    assert "Ресурси на класа" not in to_markdown(_res(catalog, [("wizard", 1)]))
