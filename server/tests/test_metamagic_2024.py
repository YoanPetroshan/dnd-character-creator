"""C6c-1: XPHB optional-feature import (Eldritch Invocations + Metamagic) and the 2024 Metamagic card.

Rules (XPHB, read from optionalfeatures.json / the class record on 2026-10-10):
  Sorcerer Metamagic   optionalfeatureProgression {"2": 2, "10": 4, "17": 6}: you know 2 options at level 2,
                       4 at level 10 and 6 at level 17. Costs: Heightened 2 SP, Quickened 2 SP, the other
                       eight options 1 SP each (`consumes.amount`, default 1).
  Eldritch Invocations 28 XPHB records; prerequisites are a Warlock level, other invocations (Pact of the
                       Blade / Chain / Tome, Thirsting Blade) and a Warlock cantrip that deals damage (Agonizing
                       Blast, Eldritch Spear) or does so via an attack roll (Repelling Blast). Repeatable:
                       Agonizing Blast, Eldritch Spear, Repelling Blast, Lessons of the First Ones.
                       Data carried: innate spells, senses (Witch Sight truesight 30), featProgression.

Matrix: converter (38 records, repeatable, prerequisite shapes, spells, senses, costs, bad input) x spell damage /
attack helpers (XPHB, SRD) x ruleset (2024 / mixed / 2014) x Sorcerer level (1, 2, 10, 17, 10 -> 9 prune) x
SRD cards skipped under 2024 x sheet.features row x Sorcery Points resource detail x export line x
catalog (real / SRD-only) x timing."""
import copy
import time

import pytest

from catalog.loader import load
from catalog.official.subclasses import convert_class_optional_features_2024
from catalog.official_source import has_official, has_official_classes
from engine import class_choices_2024
from engine.resolve import resolve
from engine.spells import spell_attack_roll, spell_deals_damage
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

META = "class:sorcerer:2:feature:xphb-sorcerer-2-metamagic"
ALL_MM = ["opt-careful-spell-xphb", "opt-distant-spell-xphb", "opt-empowered-spell-xphb",
          "opt-extended-spell-xphb", "opt-heightened-spell-xphb", "opt-quickened-spell-xphb",
          "opt-seeking-spell-xphb", "opt-subtle-spell-xphb", "opt-transmuted-spell-xphb", "opt-twinned-spell-xphb"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024"):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith(("xphb-", "opt-"))}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- converter (synthetic input, no data files) -----------------------------------------------

def _raw(name, types, **extra):
    return {"name": name, "source": "XPHB", "featureType": types, "entries": ["Text."], **extra}


def test_converter_skips_other_sources_and_types_and_survives_bad_input():
    raw = [
        _raw("Good Spell", ["MM"]),
        {**_raw("Old Spell", ["MM"]), "source": "PHB"},
        _raw("Maneuver", ["MV:B"]),
        {"name": "No types", "source": "XPHB"},
        "junk", None,
        _raw("Bad Prereq", ["EI"], prerequisite=["x", {"level": "n"}, {"spell": "n"}]),
        _raw("Bad Spells", ["EI"], additionalSpells=["x", {"innate": {"_": [3, "nonexistent spell|xphb"]}}]),
    ]
    out = convert_class_optional_features_2024(raw, lambda sid: sid if sid == "known-xphb" else None)
    assert set(out) == {"opt-good-spell-xphb", "opt-bad-prereq-xphb", "opt-bad-spells-xphb"}
    rec = out["opt-good-spell-xphb"]
    assert rec["ruleset"] == "2024" and rec["source"] == "XPHB" and rec["feature_types"] == ["MM"]
    assert rec["cost"] == 1 and rec["repeatable"] is False
    assert rec["prerequisite_2024"] == {"level": None, "optional_features": [], "cantrip": None}
    assert out["opt-bad-spells-xphb"]["spells"]["innate"] == []  # unresolvable names are dropped


def test_converter_prerequisite_and_spell_shapes():
    raw = [
        _raw("Blade Thing", ["EI"], prerequisite=[{"level": {"level": 5, "class": {"name": "Warlock"}},
                                                  "optionalfeature": ["pact of the blade|xphb"]}]),
        _raw("Blast Thing", ["EI"], prerequisite=[{"spell": [{"choose": "level=0|class=Warlock",
                                                              "entry": "a Warlock Cantrip That Deals Damage via an Attack Roll"}],
                                                   "level": {"level": 2, "class": {"name": "Warlock"}}}]),
        _raw("Dmg Thing", ["EI"], prerequisite=[{"spell": [{"choose": "level=0|class=Warlock",
                                                            "entry": "a Warlock Cantrip That Deals Damage"}]}]),
        _raw("Tome Thing", ["EI"], additionalSpells=[{"ability": "cha", "known": {"_": [{"choose": "level=0", "count": 3}]},
                                                      "prepared": {"_": [{"choose": "level=1|components & miscellaneous=ritual", "count": 2}]}}]),
        _raw("Daily Thing", ["EI"], additionalSpells=[{"innate": {"_": {"daily": {"1e": ["water breathing|xphb"]}}}}]),
        _raw("Ritual Thing", ["EI"], additionalSpells=[{"innate": {"_": {"ritual": ["find familiar|xphb"]}}}]),
        _raw("Sight Thing", ["EI"], senses=[{"truesight": 30}]),
        _raw("Rep Thing", ["EI"], entries=["x", {"type": "entries", "entries": [{"type": "entries", "name": "Repeatable", "entries": ["y"]}]}]),
        _raw("Cost Thing", ["MM"], consumes={"name": "Sorcery Point", "amount": 2}),
    ]
    out = convert_class_optional_features_2024(raw, lambda sid: sid if sid.endswith("-xphb") else None)
    assert out["opt-blade-thing-xphb"]["prerequisite_2024"] == {
        "level": 5, "optional_features": ["opt-pact-of-the-blade-xphb"], "cantrip": None}
    assert out["opt-blast-thing-xphb"]["prerequisite_2024"]["cantrip"] == "attack"
    assert out["opt-dmg-thing-xphb"]["prerequisite_2024"]["cantrip"] == "damage"
    tome = out["opt-tome-thing-xphb"]["spells"]
    assert tome["known_choose"] == [{"filter": {"level": [0]}, "count": 3}]
    assert tome["prepared_choose"] == [{"filter": {"level": [1], "ritual": True}, "count": 2}]
    assert tome["ability"] == "cha"
    assert out["opt-daily-thing-xphb"]["spells"]["innate"] == [{"spell": "water-breathing-xphb", "uses": "1/long rest"}]
    assert out["opt-ritual-thing-xphb"]["spells"]["innate"] == [{"spell": "find-familiar-xphb", "uses": "ritual"}]
    assert out["opt-sight-thing-xphb"]["senses"] == {"truesight": 30}
    assert out["opt-rep-thing-xphb"]["repeatable"] is True
    assert out["opt-cost-thing-xphb"]["cost"] == 2


# ---- real data -------------------------------------------------------------------------------

@needs_data
def test_xphb_optional_features_are_in_the_catalog(catalog):
    xphb = {k: v for k, v in catalog.features.items() if k.startswith("opt-") and k.endswith("-xphb")
            and set(v.get("feature_types") or []) & {"EI", "MM"}}
    assert len(xphb) == 38
    assert sum("EI" in v["feature_types"] for v in xphb.values()) == 28
    assert sum("MM" in v["feature_types"] for v in xphb.values()) == 10
    assert {v["name"] for v in xphb.values() if v["repeatable"]} == {
        "Agonizing Blast", "Eldritch Spear", "Repelling Blast", "Lessons of the First Ones"}
    assert all(v["ruleset"] == "2024" and v["source"] == "XPHB" for v in xphb.values())


@needs_data
def test_xphb_optional_feature_data(catalog):
    f = catalog.features
    assert f["opt-thirsting-blade-xphb"]["prerequisite_2024"] == {
        "level": 5, "optional_features": ["opt-pact-of-the-blade-xphb"], "cantrip": None}
    assert f["opt-agonizing-blast-xphb"]["prerequisite_2024"]["cantrip"] == "damage"
    assert f["opt-agonizing-blast-xphb"]["prerequisite_2024"]["level"] == 2
    assert f["opt-repelling-blast-xphb"]["prerequisite_2024"]["cantrip"] == "attack"
    assert f["opt-devouring-blade-xphb"]["prerequisite_2024"]["optional_features"] == ["opt-thirsting-blade-xphb"]
    assert f["opt-witch-sight-xphb"]["senses"] == {"truesight": 30}
    assert {"spell": "water-breathing-xphb", "uses": "1/long rest"} in f["opt-gift-of-the-depths-xphb"]["spells"]["innate"]
    assert {"spell": "find-familiar-xphb", "uses": "ritual"} in f["opt-pact-of-the-chain-xphb"]["spells"]["innate"]
    assert f["opt-armor-of-shadows-xphb"]["spells"]["innate"] == [{"spell": "mage-armor-xphb", "uses": "at-will"}]
    assert f["opt-pact-of-the-tome-xphb"]["spells"]["known_choose"][0]["count"] == 3
    assert f["opt-lessons-of-the-first-ones-xphb"]["feat_progression"]
    # nothing but the 38 new records changed in the opt-* family (76 existed before)
    assert len([k for k in f if k.startswith("opt-")]) == 76 + 38


@needs_data
def test_metamagic_costs(catalog):
    costs = {k: catalog.features[k]["cost"] for k in ALL_MM}
    assert costs == {k: (2 if k in ("opt-heightened-spell-xphb", "opt-quickened-spell-xphb") else 1) for k in ALL_MM}


@needs_data
def test_class_record_keeps_the_optional_feature_progression(catalog):
    prog = catalog.class_2024_records["sorcerer"]["optional_feature_progression"]
    assert prog[0]["progression"] == {"2": 2, "10": 4, "17": 6}
    assert catalog.class_2024_records["fighter"]["optional_feature_progression"] == []


@needs_data
def test_spell_damage_and_attack_helpers(catalog):
    s = catalog.spells
    assert spell_deals_damage(s["eldritch-blast-xphb"]) and spell_attack_roll(s["eldritch-blast-xphb"])
    assert spell_deals_damage(s["toll-the-dead-xphb"]) and not spell_attack_roll(s["toll-the-dead-xphb"])
    assert not spell_deals_damage(s["minor-illusion-xphb"]) and not spell_attack_roll(s["minor-illusion-xphb"])
    assert spell_deals_damage(s["eldritch-blast"]) and spell_attack_roll(s["eldritch-blast"])  # SRD keys
    assert not spell_deals_damage({}) and not spell_attack_roll({})


# ---- Metamagic card ---------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,count", [(2, 2), (9, 2), (10, 4), (16, 4), (17, 6), (20, 6)])
def test_metamagic_count_follows_the_progression(catalog, level, count):
    card = _card(_res(catalog, [("sorcerer", level, {})]), META)
    assert card["count"] == count and card["status"] == "pending"
    assert [o["id"] for o in card["options"]] == ALL_MM
    assert card["source"] == {"kind": "class", "id": "sorcerer", "label": "Sorcerer", "level": 2}
    assert "count_by_level" not in card


@needs_data
def test_no_metamagic_card_at_level_1_and_labels_show_costs(catalog):
    assert _card(_res(catalog, [("sorcerer", 1, {})]), META) is None
    card = _card(_res(catalog, [("sorcerer", 2, {})]), META)
    labels = {o["id"]: o["label"] for o in card["options"]}
    assert labels["opt-careful-spell-xphb"] == "Careful Spell (1 SP)"
    assert labels["opt-quickened-spell-xphb"] == "Quickened Spell (2 SP)"
    assert all(o.get("description") for o in card["options"])


@needs_data
def test_stored_picks_resolve_and_level_down_prunes(catalog):
    picks = ["opt-careful-spell-xphb", "opt-quickened-spell-xphb", "opt-twinned-spell-xphb", "opt-subtle-spell-xphb"]
    res = _res(catalog, [("sorcerer", 10, {META: picks})])
    assert _card(res, META)["status"] == "resolved" and _card(res, META)["selected"] == picks
    res = _res(catalog, [("sorcerer", 9, {META: picks})])
    card = _card(res, META)
    assert card["selected"] == picks[:2] and card["status"] == "resolved"
    pruned = [p for p in res["pruned"] if p["choiceId"] == META]
    assert pruned and "now allows 2" in pruned[0]["reason"]
    assert not [p for p in res["problems"] if META in p.get("id", "") or META in p.get("message", "")]


@needs_data
def test_unknown_stored_option_is_ignored(catalog):
    res = _res(catalog, [("sorcerer", 2, {META: ["opt-careful-spell-xphb", "metamagic-careful-spell"]})])
    assert _card(res, META)["selected"] == ["opt-careful-spell-xphb"]


@needs_data
def test_srd_metamagic_cards_are_gone_under_2024_only(catalog):
    res = _res(catalog, [("sorcerer", 17, {})])
    assert not [c["id"] for c in res["choices"] if "metamagic-" in c["id"] and "xphb" not in c["id"]]
    for ruleset in ("mixed", "2014"):
        res = _res(catalog, [("sorcerer", 17, {})], ruleset=ruleset)
        ids = [c["id"] for c in res["choices"]]
        assert META not in ids
        assert any(i.endswith(":feature:metamagic-1") or i.endswith("metamagic-1") for i in ids)


@needs_data
def test_stored_srd_metamagic_picks_land_in_pruned_under_2024(catalog):
    srd = "class:sorcerer:3:feature:metamagic-1"
    res = _res(catalog, [("sorcerer", 3, {srd: ["metamagic-careful-spell", "metamagic-distant-spell"]})])
    assert srd in {p["choiceId"] for p in res["pruned"]}


@needs_data
def test_multiclass_uses_the_sorcerer_class_level(catalog):
    res = _res(catalog, [("wizard", 8, {}), ("sorcerer", 2, {})])
    assert _card(res, META)["count"] == 2


@needs_data
def test_sheet_features_row_lists_the_picks(catalog):
    res = _res(catalog, [("sorcerer", 2, {META: ["opt-quickened-spell-xphb", "opt-twinned-spell-xphb"]})])
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Metamagic")
    assert row["level"] == 2
    assert row["choice"] == ["Quickened Spell (2 SP)", "Twinned Spell (1 SP)"]


@needs_data
def test_sorcery_points_resource_lists_metamagic_costs(catalog):
    res = _res(catalog, [("sorcerer", 2, {META: ["opt-quickened-spell-xphb", "opt-twinned-spell-xphb"]})])
    sp = next(r for r in res["derived"]["classResources"] if r["name"] == "Sorcery Points")
    assert sp["details"]["metamagic"] == [{"name": "Quickened Spell", "cost": 2}, {"name": "Twinned Spell", "cost": 1}]
    assert "метамагия: Quickened Spell (2), Twinned Spell (1)" in resource_line(sp)
    bare = next(r for r in _res(catalog, [("sorcerer", 2, {})])["derived"]["classResources"] if r["name"] == "Sorcery Points")
    assert "metamagic" not in (bare.get("details") or {})


@needs_data
def test_mixed_resource_has_no_metamagic_detail(catalog):
    srd = "class:sorcerer:3:feature:metamagic-1"
    res = _res(catalog, [("sorcerer", 3, {srd: ["metamagic-careful-spell", "metamagic-distant-spell"]})], ruleset="mixed")
    sp = next(r for r in res["derived"]["classResources"] if r["name"] == "Sorcery Points")
    assert "metamagic" not in (sp.get("details") or {})


# ---- degrade and isolation -------------------------------------------------------------------

@needs_data
def test_srd_only_catalog_keeps_the_srd_cards(catalog):
    bare = _srd_only(catalog)
    res = _res(bare, [("sorcerer", 3, {})])
    ids = [c["id"] for c in res["choices"]]
    assert META not in ids and any("metamagic-1" in i for i in ids)
    assert class_choices_2024.metamagic_templates(bare, {"cls": {"name": "Sorcerer"}, "cls_id": "sorcerer", "level": 10}, "2024") == []


def test_helper_is_inert_outside_2024_and_for_other_classes(catalog):
    rc = {"cls": {"name": "Sorcerer"}, "cls_id": "sorcerer", "level": 10}
    assert class_choices_2024.metamagic_templates(catalog, rc, "mixed") == []
    assert class_choices_2024.metamagic_templates(catalog, rc, "2014") == []
    assert class_choices_2024.metamagic_templates(catalog, {**rc, "cls_id": "wizard"}, "2024") == []
    assert class_choices_2024.replaced_srd_features(catalog, "sorcerer", "mixed") == set()


@needs_data
def test_resolve_timing(catalog):
    drafts = [_draft([("sorcerer", 2, {})]), _draft([("sorcerer", 17, {})]), _draft([("warlock", 17, {}), ("paladin", 3, {})]),
              _draft([("fighter", 20, {})]), _draft([("wizard", 20, {})]),
              _draft([("fighter", 20, {})], ruleset="mixed"), _draft([("wizard", 20, {})], ruleset="mixed")]
    for d in drafts:
        resolve(d, catalog)
        start = time.perf_counter()
        for _ in range(20):
            resolve(d, catalog)
        assert (time.perf_counter() - start) / 20 < 0.05
