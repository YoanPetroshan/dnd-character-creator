"""R7: Warlock Mystic Arcanum (decision D11).

RAW (PHB 2014 and XPHB 2024, identical levels): at Warlock 11/13/15/17 the
character picks one 6th/7th/8th/9th-level spell from the Warlock list as an
arcanum. Rule matrix: Warlock 10 has none; 11 has one (6th level); 17 has
four; the cids are `class:warlock:{11,13,15,17}:mystic-arcanum-{6..9}`;
levels come from the SRD `mystic_arcanum_level_N` columns (checked by script
2026-10-10: 11/13/15/17, XPHB feature levels 11/13/15/17 too); spell options
follow the same `sources`/`ruleset` visibility as other spell options and an
already stored pick stays offered; options are always the WARLOCK list even
when another caster class is in the draft; going down a level prunes the
picks whose cid no longer exists. Real data: true-seeing is a level-6
Warlock spell (SRD), twin true-seeing-xphb.
"""
import dataclasses
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official_spells
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

needs_spells = pytest.mark.skipif(not has_official_spells(), reason="5etools spell files not available")

_BASE = {"STR": 10, "DEX": 10, "CON": 12, "INT": 14, "WIS": 10, "CHA": 16}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="mixed", sources=None, choices=None):
    d = {"ruleset": ruleset, "abilities": {"method": "manual", "base": dict(_BASE)},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": c, "level": lv, "choices": dict((choices or {}).get(c, {}))} for c, lv in classes]}
    if sources is not None:
        d["sources"] = sources
    return d


def _arcanum(res):
    return [c for c in res["choices"] if ":mystic-arcanum-" in c["id"]]


def _ids(choice):
    return [o["id"] for o in choice["options"]]


def _levels(catalog, choice):
    return {catalog.spells[i]["level"] for i in _ids(choice)}


def _warlock_ids(catalog, level):
    return {s["index"] for s in catalog.spells.values()
            if s["level"] == level and any(c["index"] == "warlock" for c in s.get("classes", []))}


def test_warlock_10_has_no_arcanum(catalog):
    assert _arcanum(resolve(_draft([("warlock", 10)]), catalog)) == []


def test_non_warlock_never_has_arcanum(catalog):
    assert _arcanum(resolve(_draft([("wizard", 20)]), catalog)) == []


def test_warlock_11_has_one_level_6_template(catalog):
    chs = _arcanum(resolve(_draft([("warlock", 11)]), catalog))
    assert [c["id"] for c in chs] == ["class:warlock:11:mystic-arcanum-6"]
    ch = chs[0]
    assert ch["count"] == 1 and ch["status"] == "pending" and ch["source"]["kind"] == "class"
    assert _levels(catalog, ch) == {6}
    assert set(_ids(ch)) <= _warlock_ids(catalog, 6) and _ids(ch)
    assert {o["group"] for o in ch["options"]} == {"spell-level-6"}


@pytest.mark.parametrize("level,cids", [
    (12, ["class:warlock:11:mystic-arcanum-6"]),
    (13, ["class:warlock:11:mystic-arcanum-6", "class:warlock:13:mystic-arcanum-7"]),
    (16, ["class:warlock:11:mystic-arcanum-6", "class:warlock:13:mystic-arcanum-7", "class:warlock:15:mystic-arcanum-8"]),
    (17, [f"class:warlock:{lv}:mystic-arcanum-{n}" for lv, n in ((11, 6), (13, 7), (15, 8), (17, 9))]),
    (20, [f"class:warlock:{lv}:mystic-arcanum-{n}" for lv, n in ((11, 6), (13, 7), (15, 8), (17, 9))]),
])
def test_template_count_follows_the_level_columns(catalog, level, cids):
    chs = _arcanum(resolve(_draft([("warlock", level)]), catalog))
    assert [c["id"] for c in chs] == cids
    for c, n in zip(chs, (6, 7, 8, 9)):
        assert _levels(catalog, c) == {n} and {o["group"] for o in c["options"]} == {f"spell-level-{n}"}


def test_the_columns_agree_with_the_fixed_levels(catalog):
    for lv in range(1, 21):
        cs = catalog.class_level_row("warlock", lv)["class_specific"]
        got = [n for n in range(6, 10) if cs.get(f"mystic_arcanum_level_{n}", 0) >= 1]
        assert got == [n for n, at in ((6, 11), (7, 13), (8, 15), (9, 17)) if lv >= at]


@needs_spells
def test_true_seeing_is_a_real_warlock_6th_level_option(catalog):
    assert "true-seeing" in _warlock_ids(catalog, 6)
    ch = _arcanum(resolve(_draft([("warlock", 11)], "mixed"), catalog))[0]
    assert "true-seeing" in _ids(ch) and "true-seeing-xphb" not in _ids(ch)  # mixed offers the 2014 twin
    ch = _arcanum(resolve(_draft([("warlock", 11)], "2024"), catalog))[0]
    assert "true-seeing-xphb" in _ids(ch) and "true-seeing" not in _ids(ch)


def test_pick_appears_in_the_sheet(catalog):
    res = resolve(_draft([("warlock", 11)], choices={"warlock": {"class:warlock:11:mystic-arcanum-6": ["true-seeing"]}}), catalog)
    ch = _arcanum(res)[0]
    assert ch["selected"] == ["true-seeing"] and ch["status"] == "resolved"
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
    assert entry["mysticArcanum"] == [{"level": 6, "id": "true-seeing", "name": "True Seeing"}]


def test_sheet_entry_has_an_empty_list_below_11_and_unpicked_levels_are_skipped(catalog):
    res = resolve(_draft([("warlock", 5)]), catalog)
    assert next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")["mysticArcanum"] == []
    res = resolve(_draft([("warlock", 13)], choices={"warlock": {"class:warlock:13:mystic-arcanum-7": ["forcecage"]}}), catalog)
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
    assert [m["level"] for m in entry["mysticArcanum"]] == [7]


def test_pending_arcanum_is_pending_not_a_problem(catalog):
    res = resolve(_draft([("warlock", 17)]), catalog)
    assert all(c["status"] == "pending" for c in _arcanum(res))
    assert not [p for p in res["problems"] if "arcanum" in p["id"]]


def test_level_down_prunes_the_stale_picks(catalog):
    picks = {"class:warlock:11:mystic-arcanum-6": ["true-seeing"],
             "class:warlock:13:mystic-arcanum-7": ["forcecage"],
             "class:warlock:15:mystic-arcanum-8": ["feeblemind"],
             "class:warlock:17:mystic-arcanum-9": ["foresight"]}
    res = resolve(_draft([("warlock", 17)], choices={"warlock": picks}), catalog)
    assert [c["status"] for c in _arcanum(res)] == ["resolved"] * 4
    res = resolve(_draft([("warlock", 12)], choices={"warlock": picks}), catalog)
    pruned = {p["choiceId"] for p in res["pruned"]}
    assert {"class:warlock:13:mystic-arcanum-7", "class:warlock:15:mystic-arcanum-8", "class:warlock:17:mystic-arcanum-9"} <= pruned
    assert "class:warlock:11:mystic-arcanum-6" not in pruned
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
    assert entry["mysticArcanum"] == [{"level": 6, "id": "true-seeing", "name": "True Seeing"}]
    assert not res["problems"] or not [p for p in res["problems"] if "arcanum" in p["id"]]


def test_a_pick_of_the_wrong_spell_level_is_not_accepted(catalog):
    res = resolve(_draft([("warlock", 11)], choices={"warlock": {"class:warlock:11:mystic-arcanum-6": ["forcecage"]}}), catalog)
    ch = _arcanum(res)[0]
    assert ch["selected"] == [] and ch["status"] == "pending"


def test_multiclass_with_a_wizard_offers_only_warlock_spells(catalog):
    res = resolve(_draft([("warlock", 11), ("wizard", 5)]), catalog)
    chs = _arcanum(res)
    assert [c["id"] for c in chs] == ["class:warlock:11:mystic-arcanum-6"]
    wiz6 = {s["index"] for s in catalog.spells.values()
            if s["level"] == 6 and any(c["index"] == "wizard" for c in s["classes"])}
    assert set(_ids(chs[0])) <= _warlock_ids(catalog, 6)
    assert wiz6 - _warlock_ids(catalog, 6)  # the wizard list really has others
    assert not (set(_ids(chs[0])) & (wiz6 - _warlock_ids(catalog, 6)))
    # Wizard 5 contributes no arcanum of its own and the warlock keeps its entry.
    assert {e["classId"] for e in res["sheet"]["spells"]} == {"warlock", "wizard"}


def test_only_the_warlock_levels_count_in_a_multiclass(catalog):
    # Warlock 10 + Wizard 10 is character level 20 but has no arcanum.
    assert _arcanum(resolve(_draft([("warlock", 10), ("wizard", 10)]), catalog)) == []


@needs_spells
def test_sources_filter_the_options_and_a_stored_pick_stays_offered(catalog):
    res = resolve(_draft([("warlock", 11)], sources=["srd"]), catalog)
    ids = _ids(_arcanum(res)[0])
    assert ids == ["circle-of-death", "conjure-fey", "create-undead", "eyebite", "flesh-to-stone", "mass-suggestion", "true-seeing"]
    # soul-cage is XGE: hidden by sources=srd, but kept when already stored.
    res = resolve(_draft([("warlock", 11)], sources=["srd"],
                         choices={"warlock": {"class:warlock:11:mystic-arcanum-6": ["soul-cage"]}}), catalog)
    ch = _arcanum(res)[0]
    assert "soul-cage" in _ids(ch) and ch["selected"] == ["soul-cage"]
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
    assert entry["mysticArcanum"][0]["id"] == "soul-cage"


@needs_spells
def test_ruleset_visibility_matches_other_spell_options(catalog):
    n = {rs: len(_ids(_arcanum(resolve(_draft([("warlock", 11)], rs), catalog))[0])) for rs in ("mixed", "2014", "2024")}
    assert n == {"mixed": 18, "2014": 17, "2024": 15}  # verified by script 2026-10-10
    # A stored 2014 pick survives a switch to 2024.
    res = resolve(_draft([("warlock", 11)], "2024", choices={"warlock": {"class:warlock:11:mystic-arcanum-6": ["conjure-fey"]}}), catalog)
    assert _arcanum(res)[0]["selected"] == ["conjure-fey"]


@needs_official
def test_srd_only_catalog(catalog):
    srd = dataclasses.replace(catalog, spells={k: v for k, v in catalog.spells.items() if v.get("source") == "SRD"})
    res = resolve(_draft([("warlock", 17)]), srd)
    chs = _arcanum(res)
    assert [c["id"] for c in chs] == [f"class:warlock:{lv}:mystic-arcanum-{n}" for lv, n in ((11, 6), (13, 7), (15, 8), (17, 9))]
    assert _ids(chs[0]) == ["circle-of-death", "conjure-fey", "create-undead", "eyebite", "flesh-to-stone", "mass-suggestion", "true-seeing"]
    assert len(_ids(chs[3])) == 7 and "weird" in _ids(chs[3])


def test_resolve_stays_fast_for_warlock_17(catalog):
    d = _draft([("warlock", 17)])
    resolve(d, catalog)
    t = time.perf_counter()
    for _ in range(20):
        resolve(d, catalog)
    assert (time.perf_counter() - t) / 20 < 0.05
