"""C4: Wizard spellbook (both rulesets, decision D7).

Rule, XPHB Wizard "Spellbook" (read from class-wizard.json, 2026-10-10): "It starts with six
level 1 Wizard spells of your choice." / "Whenever you gain a Wizard level after 1, add two
Wizard spells of your choice to your spellbook. Each of these spells must be of a level for
which you have spell slots". "Prepared Spells of Level 1+": "choose four spells from your
spellbook. The chosen spells must be of a level for which you have spell slots." The PHB text
(6 at level 1, +2 per level) is not in the bundled data; the SRD only says the wizard has a
spellbook, so the 2014 count is taken from the plan (same rule).
Prepared counts: 2014/mixed = max(1, INT mod + level); 2024 = XPHB table (level 1: 4).
Cases: book count by level, options up to the highest slot level, prepared options == the
stored (valid, truncated) book, prepared pick outside the book -> pruned (non-blocking), level
down -> book pruned with "now allows N", third casters (EK/AT) are not wizards, SRD-only catalog."""
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine.resolve import resolve

BOOK, PREP, CANT = "class:wizard:spellbook", "class:wizard:spells-known", "class:wizard:spells-cantrips"
_BASE = {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, choices=None, ruleset="mixed", cls="wizard", sub=None, sources=()):
    return {"ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": dict(_BASE)},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": choices or {}}]}


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _lvl(catalog, sid):
    return catalog.spells[sid]["level"]


def _book(catalog, level, n):
    """First n book candidates of the real option list (lowest spell levels first)."""
    return [o["id"] for o in _choice(resolve(_draft(level), catalog), BOOK)["options"]][:n]


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_wizard_1_book_is_six_level_1_spells(catalog, ruleset):
    res = resolve(_draft(1, ruleset=ruleset), catalog)
    book = _choice(res, BOOK)
    assert book["count"] == 6 and book["label"] == "Spellbook"
    assert book["options"] and all(_lvl(catalog, o["id"]) == 1 for o in book["options"])
    prep = _choice(res, PREP)
    assert prep["options"] == [] and prep["description"] == "Choose spells for your spellbook first."


def test_prepared_options_are_the_stored_book(catalog):
    stored = _book(catalog, 1, 6)
    res = resolve(_draft(1, {BOOK: stored}), catalog)
    assert _choice(res, BOOK)["status"] == "resolved"
    prep = _choice(res, PREP)
    assert {o["id"] for o in prep["options"]} == set(stored)
    assert prep["count"] == 4  # 2014/mixed: INT 16 (+3) + level 1
    picked = stored[:4]
    res = resolve(_draft(1, {BOOK: stored, PREP: picked}), catalog)
    assert _choice(res, PREP)["selected"] == picked and _choice(res, PREP)["status"] == "resolved"
    assert res["pruned"] == [] and res["problems"] == []
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "wizard")
    assert entry["spellbook"] == [{"id": s, "name": catalog.spells[s]["name"], "level": 1} for s in stored]
    assert [k["id"] for k in entry["known"]] == picked


def test_wizard_5_book_is_fourteen_up_to_level_3(catalog):
    res = resolve(_draft(5), catalog)
    book = _choice(res, BOOK)
    assert book["count"] == 14
    levels = {_lvl(catalog, o["id"]) for o in book["options"]}
    assert levels == {1, 2, 3}
    assert _choice(res, PREP)["options"] == []  # empty book


def test_prepared_pick_not_in_book_is_pruned(catalog):
    stored = _book(catalog, 1, 6)
    outside = next(o["id"] for o in _choice(resolve(_draft(1), catalog), BOOK)["options"] if o["id"] not in stored)
    res = resolve(_draft(1, {BOOK: stored, PREP: [stored[0], outside]}), catalog)
    prep = _choice(res, PREP)
    assert prep["selected"] == [stored[0]] and prep["status"] == "pending"
    assert [p["choiceId"] for p in res["pruned"]] == [PREP]
    assert catalog.spells[outside]["name"] in res["pruned"][0]["reason"]
    assert res["problems"] == []


def test_empty_book_prunes_every_stored_prepared_pick(catalog):
    stored = _book(catalog, 1, 4)
    res = resolve(_draft(1, {PREP: stored}), catalog)
    assert _choice(res, PREP)["selected"] == []
    assert [p["choiceId"] for p in res["pruned"]] == [PREP]
    assert res["problems"] == []


def test_level_down_prunes_the_book_and_the_prepared_list(catalog):
    book14 = _book(catalog, 5, 14)
    prep = book14[:5]
    ok = resolve(_draft(5, {BOOK: book14, PREP: prep}), catalog)
    assert ok["pruned"] == [] and ok["problems"] == []
    down = resolve(_draft(3, {BOOK: book14, PREP: prep}), catalog)  # level 3: 10 spells, slots up to 2
    assert _choice(down, BOOK)["count"] == 10
    reasons = {p["choiceId"]: p["reason"] for p in down["pruned"]}
    assert "now allows 10" in reasons[BOOK]
    assert not [p for p in down["problems"] if p["id"].startswith("over-selected")]
    kept_book = _choice(down, BOOK)["selected"]
    assert len(kept_book) <= 10 and all(_lvl(catalog, s) <= 2 for s in kept_book)
    # prepared picks that fell out of the (truncated) book are pruned too
    assert all(s in kept_book for s in _choice(down, PREP)["selected"])


def test_2024_wizard_1_prepared_count_is_the_table_value(catalog):
    stored = _book(catalog, 1, 6)
    res = resolve(_draft(1, {BOOK: stored}, ruleset="2024"), catalog)
    prep = _choice(res, PREP)
    assert prep["count"] == 4 and prep["label"] == "Prepared Spells"
    assert {o["id"] for o in prep["options"]} == set(stored)


def test_2014_prepared_count_is_int_plus_level(catalog):
    res = resolve(_draft(5, ruleset="2014"), catalog)
    assert _choice(res, PREP)["count"] == 8  # INT 16 (+3) + 5


def test_cantrips_and_other_features_are_untouched(catalog):
    res = resolve(_draft(1), catalog)
    cant = _choice(res, CANT)
    assert cant["count"] == 3 and cant["label"] == "Cantrips Known"
    assert any(f["name"] == "Arcane Recovery" for f in resolve(_draft(2), catalog)["sheet"]["features"])


def test_multiclass_only_the_wizard_gets_a_spellbook(catalog):
    d = _draft(3)
    d["classes"].append({"classId": "cleric", "level": 2, "choices": {}})
    res = resolve(d, catalog)
    assert _choice(res, BOOK)["count"] == 10  # Wizard levels only
    assert _choice(res, "class:cleric:spellbook") is None
    assert _choice(res, "class:cleric:spells-known") is not None


@pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")
@pytest.mark.parametrize("cls,sub", [("fighter", "eldritch-knight-phb"), ("rogue", "arcane-trickster-phb")])
def test_third_casters_have_no_spellbook(catalog, cls, sub):
    res = resolve(_draft(3, cls=cls, sub=sub), catalog)
    assert not [c for c in res["choices"] if c["id"].endswith(":spellbook")]
    known = _choice(res, f"class:{cls}:spells-known")
    assert known["count"] == 3 and len(known["options"]) > 30  # whole wizard list, not a book


def test_book_spells_above_the_slot_level_are_pruned_after_a_level_down(catalog):
    only_l3 = [o["id"] for o in _choice(resolve(_draft(5), catalog), BOOK)["options"] if _lvl(catalog, o["id"]) == 3][:2]
    res = resolve(_draft(3, {BOOK: only_l3}), catalog)
    assert _choice(res, BOOK)["selected"] == []
    assert [p["choiceId"] for p in res["pruned"]] == [BOOK]


def test_srd_only_catalog_still_builds_the_book(catalog):
    res = resolve(_draft(1, sources=["SRD"]), catalog)
    assert _choice(res, BOOK)["count"] == 6 and len(_choice(res, BOOK)["options"]) > 6


def test_resolve_wizard_20_with_a_full_book_is_fast(catalog):
    book = _book(catalog, 20, 44)
    assert len(book) == 44
    d = _draft(20, {BOOK: book, PREP: book[:20]})
    resolve(d, catalog)
    t = time.perf_counter()
    for _ in range(5):
        res = resolve(d, catalog)
    ms = (time.perf_counter() - t) / 5 * 1000
    print(f"wizard 20 full book resolve: {ms:.1f} ms")
    assert ms < 50
    assert _choice(res, BOOK)["count"] == 44
