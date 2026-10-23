"""RPF: a stored ASI pick whose option is still offered but disabled (cap 20 after a ruleset or species switch)
was dropped silently and the card just turned pending. It now also leaves a non-blocking `pruned` entry whose reason is
the option's own disabled reason. A valid pick, an unpicked card and a pick that is not offered at all
(the existing passes) are unchanged."""
import pytest

from catalog.loader import load
from engine.resolve import resolve

CID = "class:barbarian:4:asi"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, pick, str_base=18, ruleset="mixed"):
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": "barbarian", "level": 4,
         "choices": {CID: [pick]} if pick else {}}],
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
         "abilities": {"method": "manual", "base": {"STR": str_base, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
         "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}}
    return resolve(d, catalog)


def _card(res):
    return next(c for c in res["choices"] if c["id"] == CID)


def test_disabled_stored_option_is_reported(catalog):
    res = _res(catalog, "str-plus-2")  # SRD Human +1 makes STR 19, +2 would be 21
    opt = next(o for o in _card(res)["options"] if o["id"] == "str-plus-2")
    assert opt["disabled"]
    assert _card(res)["selected"] == [] and _card(res)["status"] == "pending"
    notes = [p for p in res["pruned"] if p["choiceId"] == CID]
    assert len(notes) == 1 and opt["disabledReason"] in notes[0]["reason"]
    assert not any(CID in p["id"] for p in res["problems"])  # non-blocking


def test_valid_unpicked_and_foreign_picks_are_not_reported(catalog):
    assert not [p for p in _res(catalog, "str-plus-2", str_base=15)["pruned"] if p["choiceId"] == CID]
    assert not [p for p in _res(catalog, None)["pruned"] if p["choiceId"] == CID]
    gone = [p for p in _res(catalog, "bogus-option")["pruned"] if p["choiceId"] == CID]
    assert len(gone) == 1  # the existing "no longer offered" entry only


def test_same_pick_is_valid_under_2024_where_the_species_adds_nothing(catalog):
    # the barbarian20-2024 -> mixed switch: SRD Human +1 (mixed) pushes STR 18 -> 19, +2 over the cap; 2024 has no species +1
    ok = _res(catalog, "str-plus-2", str_base=18, ruleset="2024")
    assert _card(ok)["selected"] == ["str-plus-2"] and not [p for p in ok["pruned"] if p["choiceId"] == CID]
    assert [p for p in _res(catalog, "str-plus-2", str_base=18, ruleset="mixed")["pruned"] if p["choiceId"] == CID]
