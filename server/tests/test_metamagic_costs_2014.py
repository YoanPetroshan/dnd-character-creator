"""G2: 2014 Metamagic costs on `sorcerer:sorcery-points` (`details.metamagicCosts`), and the two TCE options the SRD lacks.

Governing texts (the SRD Metamagic feature records and optionalfeatures.json MM records of PHB / TCE; each cost has a
verbatim quote in `reference_data.METAMAGIC_COSTS_2014`, pinned by `test_every_quote_is_in_its_record`):
  Careful 1, Distant 1, Empowered 1, Extended 1, Heightened 3, Quickened 2, Subtle 1 sorcery point(s)
  Twinned    "a number of sorcery points equal to the spell's level (1 sorcery point if the spell is a cantrip)"
             -> the exact text "spell level, 1 for a cantrip" (F1; the quoted sentence ends "(1 sorcery point if the spell is a cantrip)")
  Seeking Spell (TCE) 2, Transmuted Spell (TCE) 1: in the vendored optionalfeatures.json (20 MM records), absent from
             the SRD list, so they are imported (`convert_metamagic_options_2014`, ids `opt-seeking-spell-tce`,
             `opt-transmuted-spell-tce`) and offered by the three SRD Sorcerer cards and the Metamagic Adept feat.

Rule matrix:
  key       `details.metamagicCosts` {option id: cost} and `details.metamagic` [{name, cost}] (the 2024 shape, which the
            exports and the SPA already print), only for the options PICKED on the Sorcerer's Metamagic cards (card
            order, then pick order); nothing without a pick; a stale pick (level dropped) gives nothing
  rulesets  mixed / 2014 (mixed with a 2014 class equals 2014); 2024 keeps `details.metamagic` from the XPHB cards and
            gets no `metamagicCosts`
  SRD-only  the SRD catalog is unchanged (eight options)"""
import copy
import json

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official.paths import optionalfeatures_file
from catalog.official.subclasses import convert_metamagic_options_2014
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

C1 = "class:sorcerer:3:feature:metamagic-1"
C2 = "class:sorcerer:10:feature:metamagic-2"
C3 = "class:sorcerer:17:feature:metamagic-3"

# Independent expectation, from the books (not read from the table).
COSTS = {
    "metamagic-careful-spell": 1, "metamagic-distant-spell": 1, "metamagic-empowered-spell": 1,
    "metamagic-extended-spell": 1, "metamagic-heightened-spell": 3, "metamagic-quickened-spell": 2,
    "metamagic-subtle-spell": 1, "metamagic-twinned-spell": "spell level, 1 for a cantrip",
    "opt-seeking-spell-tce": 2, "opt-transmuted-spell-tce": 1,
}
NAMES = {"metamagic-careful-spell": "Careful Spell", "metamagic-distant-spell": "Distant Spell",
         "metamagic-empowered-spell": "Empowered Spell", "metamagic-extended-spell": "Extended Spell",
         "metamagic-heightened-spell": "Heightened Spell", "metamagic-quickened-spell": "Quickened Spell",
         "metamagic-subtle-spell": "Subtle Spell", "metamagic-twinned-spell": "Twinned Spell",
         "opt-seeking-spell-tce": "Seeking Spell", "opt-transmuted-spell-tce": "Transmuted Spell"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, picks, ruleset="2014", sources=()):
    return {"ruleset": ruleset, "sources": list(sources),
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 16}},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": "sorcerer", "level": level, "choices": dict(picks)}]}


def _sp(res):
    return next(r for r in res["derived"]["classResources"] if r["name"] == "Sorcery Points")


def _go(catalog, level, picks, ruleset="2014"):
    return resolve(_draft(level, picks, ruleset), catalog)


def _text(catalog, fid):
    return "\n".join(catalog.features[fid]["desc"])


# ---- data ----------------------------------------------------------------------------------------------------------

@needs_data
def test_every_quote_is_in_its_record(catalog):
    table = reference_data.METAMAGIC_COSTS_2014
    assert dict((k, v["cost"]) for k, v in table.items()) == COSTS
    for oid, spec in table.items():
        assert spec["quote"] in _text(catalog, oid), oid
        if isinstance(spec["cost"], int):  # the number is in the quoted sentence
            assert f"spend {spec['cost']} sorcery point" in spec["quote"], oid
        else:
            assert spec["cost"] == "spell level, 1 for a cantrip" and "equal to the spell's level" in spec["quote"] and "(1 sorcery point if the spell is a cantrip)" in spec["quote"], oid


@needs_data
def test_the_vendored_consumes_amounts_agree():
    """optionalfeatures.json (PHB / TCE MM records): where `consumes.amount` exists it equals the table."""
    raw = json.load(open(optionalfeatures_file(), encoding="utf-8"))["optionalfeature"]
    by_name = {"Heightened Spell": 3, "Quickened Spell": 2, "Seeking Spell": 2, "Extended Spell": 1}
    seen = set()
    for rec in raw:
        if "MM" in rec.get("featureType", []) and rec["source"] in ("PHB", "TCE") and "amount" in (rec.get("consumes") or {}):
            assert rec["consumes"]["amount"] == by_name[rec["name"]], rec["name"]
            seen.add(rec["name"])
    assert seen == set(by_name)
    twinned = next(r for r in raw if r["name"] == "Twinned Spell" and r["source"] == "PHB")
    assert (twinned["consumes"]["amountMin"], twinned["consumes"]["amountMax"]) == (1, 9)  # "spell level", cantrip 1


@needs_data
def test_tce_options_are_imported_from_the_record(catalog):
    """Seeking Spell and Transmuted Spell exist among the 20 MM records and were missing from the option list."""
    raw = json.load(open(optionalfeatures_file(), encoding="utf-8"))["optionalfeature"]
    assert sum("MM" in r.get("featureType", []) for r in raw) == 20
    for oid, name in (("opt-seeking-spell-tce", "Seeking Spell"), ("opt-transmuted-spell-tce", "Transmuted Spell")):
        rec = catalog.features[oid]
        assert (rec["name"], rec["source"], rec["ruleset"], rec["feature_types"]) == (name, "TCE", "2014", ["MM"])
        assert "prerequisite_level" not in rec and rec["desc"]
        assert "sorcery point" in _text(catalog, oid) and _text(catalog, oid).startswith(("If you make", "When you cast"))


def test_converter_skips_srd_twins_xphb_and_other_types():
    raw = [
        {"name": "Careful Spell", "source": "PHB", "featureType": ["MM"], "entries": ["x"]},   # SRD twin
        {"name": "Seeking Spell", "source": "TCE", "featureType": ["MM"], "entries": ["a", "b"]},
        {"name": "Seeking Spell", "source": "XPHB", "featureType": ["MM"], "entries": ["x"]},  # 2024
        {"name": "Ambush", "source": "TCE", "featureType": ["MV:B"], "entries": ["x"]},         # not Metamagic
        {"name": "Nameless", "source": "TCE", "featureType": ["MM"]},
        {"source": "TCE", "featureType": ["MM"]},
        "junk",
    ]
    out = convert_metamagic_options_2014(raw, {"metamagic-careful-spell": {}})
    assert list(out) == ["opt-seeking-spell-tce", "opt-nameless-tce"]
    assert out["opt-seeking-spell-tce"]["desc"] == ["a", "b"] and out["opt-seeking-spell-tce"]["ruleset"] == "2014"
    assert convert_metamagic_options_2014(None, {}) == {}


def test_srd_only_catalog_is_unchanged(monkeypatch):
    monkeypatch.setenv("DND_OFFICIAL_DATA", "none")
    bare = load()
    assert not [k for k in bare.features if k.endswith("-tce") and k.startswith("opt-")]
    res = resolve(_draft(3, {C1: ["metamagic-quickened-spell", "metamagic-twinned-spell"]}), bare)
    card = next(c for c in res["choices"] if c["id"] == C1)
    assert len(card["options"]) == 8
    assert _sp(res)["details"]["metamagicCosts"] == {"metamagic-quickened-spell": 2, "metamagic-twinned-spell": "spell level, 1 for a cantrip"}


# ---- cards -----------------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_the_three_sorcerer_cards_offer_ten_options_with_a_source(catalog, ruleset):
    res = _go(catalog, 17, {}, ruleset)
    for cid in (C1, C2, C3):
        card = next(c for c in res["choices"] if c["id"] == cid)
        assert [o["id"] for o in card["options"]] == [
            "metamagic-careful-spell", "metamagic-distant-spell", "metamagic-empowered-spell", "metamagic-extended-spell",
            "metamagic-heightened-spell", "metamagic-quickened-spell", "opt-seeking-spell-tce", "metamagic-subtle-spell",
            "opt-transmuted-spell-tce", "metamagic-twinned-spell"], cid
        by_id = {o["id"]: o for o in card["options"]}
        assert {k: by_id[k]["source"] for k in by_id} == {k: ("TCE" if k.endswith("-tce") else "SRD") for k in by_id}
        assert by_id["opt-seeking-spell-tce"]["label"] == "Metamagic: Seeking Spell"
        assert "reroll the d20" in by_id["opt-seeking-spell-tce"]["description"]


@needs_data
def test_the_2024_card_is_the_xphb_one_and_unchanged(catalog):
    res = _go(catalog, 17, {}, "2024")
    assert not [c for c in res["choices"] if c["id"] in (C1, C2, C3)]
    assert not [o for c in res["choices"] for o in c["options"] if o["id"].endswith("-tce")]


# ---- resolve ---------------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("oid", sorted(COSTS))
def test_each_pick_gives_its_cost(catalog, oid):
    res = _go(catalog, 3, {C1: [oid, "metamagic-subtle-spell" if oid != "metamagic-subtle-spell" else "metamagic-careful-spell"]})
    d = _sp(res)["details"]
    assert d["metamagicCosts"][oid] == COSTS[oid]
    assert {m["name"]: m["cost"] for m in d["metamagic"]}[NAMES[oid]] == COSTS[oid]
    assert d["slotCosts"] == {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}  # unchanged (the SRD rows)


@needs_data
def test_cards_and_pick_order_and_only_picked(catalog):
    res = _go(catalog, 17, {C1: ["opt-transmuted-spell-tce", "metamagic-heightened-spell"],
                            C2: ["metamagic-twinned-spell"], C3: ["opt-seeking-spell-tce"]})
    d = _sp(res)["details"]
    assert list(d["metamagicCosts"]) == ["opt-transmuted-spell-tce", "metamagic-heightened-spell",
                                         "metamagic-twinned-spell", "opt-seeking-spell-tce"]
    assert d["metamagicCosts"] == {"opt-transmuted-spell-tce": 1, "metamagic-heightened-spell": 3,
                                   "metamagic-twinned-spell": "spell level, 1 for a cantrip", "opt-seeking-spell-tce": 2}
    assert d["metamagic"] == [{"name": "Transmuted Spell", "cost": 1}, {"name": "Heightened Spell", "cost": 3},
                              {"name": "Twinned Spell", "cost": "spell level, 1 for a cantrip"}, {"name": "Seeking Spell", "cost": 2}]


@needs_data
def test_no_pick_no_key_and_stale_picks_give_nothing(catalog):
    d = _sp(_go(catalog, 3, {}))["details"]
    assert "metamagicCosts" not in d and "metamagic" not in d
    d = _sp(_go(catalog, 3, {C1: ["metamagic-careful-spell"]}))["details"]  # one of two picks
    assert d["metamagicCosts"] == {"metamagic-careful-spell": 1}
    # the level-10 card is not offered at level 5: its stored pick is dropped, the cost with it
    d = _sp(_go(catalog, 5, {C1: ["metamagic-careful-spell", "metamagic-distant-spell"], C2: ["metamagic-heightened-spell"]}))["details"]
    assert d["metamagicCosts"] == {"metamagic-careful-spell": 1, "metamagic-distant-spell": 1}


@needs_data
def test_mixed_equals_2014_and_2024_has_no_costs_key(catalog):
    picks = {C1: ["metamagic-quickened-spell", "opt-seeking-spell-tce"]}
    a = _sp(_go(catalog, 3, picks, "2014"))
    b = _sp(_go(catalog, 3, picks, "mixed"))
    assert a == b
    r24 = _go(catalog, 3, {"class:sorcerer:2:feature:xphb-sorcerer-2-metamagic": ["opt-quickened-spell-xphb", "opt-twinned-spell-xphb"]}, "2024")
    d = _sp(r24)["details"]
    assert "metamagicCosts" not in d and d["metamagic"] == [{"name": "Quickened Spell", "cost": 2}, {"name": "Twinned Spell", "cost": 1}]


@needs_data
def test_multiclass_other_class_does_not_matter(catalog):
    draft = _draft(3, {C1: ["metamagic-careful-spell", "metamagic-subtle-spell"]})
    draft["classes"].append({"classId": "wizard", "level": 2, "choices": {}})
    d = _sp(resolve(draft, catalog))["details"]
    assert d["metamagicCosts"] == {"metamagic-careful-spell": 1, "metamagic-subtle-spell": 1}


@needs_data
def test_metamagic_adept_pool_has_the_tce_options(catalog):
    draft = _draft(4, {})
    draft["classes"][0]["choices"] = {"class:sorcerer:4:asi": ["feat:metamagic-adept-tce"]}
    res = resolve(draft, catalog)
    card = next(c for c in res["choices"] if c["id"].endswith(":metamagic") and "metamagic-adept-tce" in c["id"])
    assert [o["label"] for o in card["options"]] == [
        "Careful Spell", "Distant Spell", "Empowered Spell", "Extended Spell", "Heightened Spell", "Quickened Spell",
        "Seeking Spell", "Subtle Spell", "Transmuted Spell", "Twinned Spell"]


# ---- surfaces ---------------------------------------------------------------------------------------------------------

@needs_data
def test_export_line_prints_the_costs_in_both_languages(catalog):
    res = _go(catalog, 3, {C1: ["metamagic-twinned-spell", "opt-seeking-spell-tce"]})
    sp = _sp(res)
    assert "metamagic: Twinned Spell (spell level, 1 for a cantrip), Seeking Spell (2)" in resource_line(sp, "en")
    assert "метамагия: Twinned Spell (spell level, 1 for a cantrip), Seeking Spell (2)" in resource_line(sp, "bg")


@needs_data
def test_resolve_stays_fast(catalog):
    draft = _draft(17, {C1: ["opt-transmuted-spell-tce", "metamagic-heightened-spell"], C2: ["metamagic-twinned-spell"],
                        C3: ["opt-seeking-spell-tce"]})
    resolve(copy.deepcopy(draft), catalog)
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "sorcerer 17 with four Metamagic picks")


# ---- F1 (review of G2) ---------------------------------------------------------------------------------------------

ADEPT = "class:sorcerer:4:asi:feat:metamagic-adept-tce:metamagic"


@needs_data
def test_twinned_spell_cost_text_carries_the_cantrip_rule(catalog):
    """SRD / PHB text: "equal to the spell's level to target a second creature in range with the same spell (1 sorcery
    point if the spell is a cantrip)": the cost is the spell's level, 1 for a cantrip."""
    assert "(1 sorcery point if the spell is a cantrip)" in _text(catalog, "metamagic-twinned-spell")
    res = _go(catalog, 3, {C1: ["metamagic-twinned-spell"]})
    assert _sp(res)["details"]["metamagicCosts"] == {"metamagic-twinned-spell": "spell level, 1 for a cantrip"}
    assert _sp(res)["details"]["metamagic"] == [{"name": "Twinned Spell", "cost": "spell level, 1 for a cantrip"}]


@needs_data
def test_metamagic_adept_picks_join_the_sorcerer_costs_2014(catalog):
    draft = _draft(8, {C1: ["metamagic-careful-spell", "metamagic-distant-spell"], "class:sorcerer:4:asi": ["feat:metamagic-adept-tce"],
                       ADEPT: ["metamagic-quickened-spell", "metamagic-twinned-spell"]})
    details = _sp(resolve(draft, catalog))["details"]
    assert details["metamagicCosts"] == {"metamagic-careful-spell": 1, "metamagic-distant-spell": 1, "metamagic-quickened-spell": 2,
                                         "metamagic-twinned-spell": "spell level, 1 for a cantrip"}
    assert [m["name"] for m in details["metamagic"]] == ["Careful Spell", "Distant Spell", "Quickened Spell", "Twinned Spell"]


@needs_data
def test_a_metamagic_adept_pick_that_repeats_a_sorcerer_pick_is_listed_once(catalog):
    draft = _draft(8, {C1: ["metamagic-careful-spell", "metamagic-distant-spell"], "class:sorcerer:4:asi": ["feat:metamagic-adept-tce"],
                       ADEPT: ["metamagic-careful-spell"]})
    names = [m["name"] for m in _sp(resolve(draft, catalog))["details"]["metamagic"]]
    assert names.count("Careful Spell") == 1


@needs_data
def test_metamagic_adept_without_a_pick_or_under_2024_adds_nothing(catalog):
    draft = _draft(8, {C1: ["metamagic-careful-spell"], "class:sorcerer:4:asi": ["feat:metamagic-adept-tce"]})
    assert _sp(resolve(draft, catalog))["details"]["metamagicCosts"] == {"metamagic-careful-spell": 1}
    res = resolve(_draft(8, {}, ruleset="2024"), catalog)
    assert "metamagicCosts" not in (_sp(res).get("details") or {})
