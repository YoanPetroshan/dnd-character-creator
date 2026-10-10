"""G1-3: under `mixed`/`2014` the SRD Fighting Style subfeature (e.g. "Fighting Style:
Dueling") and the same-named Fighting Style feat (dueling-xphb, taken at an ASI) are the
same Fighting Style option, and RAW a character can't take the same option twice (PHB
Fighter: "You can't take a Fighting Style option more than once, even if you later get to
choose again"; XPHB feat rule: a feat once unless Repeatable). Identity is the S2 name key.

Order decides the duplicate (first holder wins, as in F1): class order, then class level.
Matrix: SRD first then feat (feat disabled + problem) | feat first then SRD Champion
"Additional Fighting Style" (SRD option disabled + problem, pick not applied) | different
styles (both fine) | two SRD cards of different classes (Fighter 1 / Paladin 2) | 2024
unchanged (cards are feats, S2 already covers them)."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", subclass=None):
    draft = {
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch,
                     **({"subclassId": subclass[c]} if subclass and c in subclass else {})}
                    for c, lv, ch in classes],
    }
    return resolve(draft, catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


SRD1 = "class:fighter:1:feature:fighter-fighting-style"


def test_srd_style_blocks_same_named_feat_at_asi(catalog):
    res = _res(catalog, [("fighter", 4, {SRD1: ["fighter-fighting-style-dueling"],
                                          "class:fighter:4:asi": ["feat:dueling-xphb"]})])
    o = _opt(_card(res, "class:fighter:4:asi"), "feat:dueling-xphb")
    assert o["disabled"] and o["disabledReason"].startswith("already taken (Dueling")
    assert any(p["id"] == "feat-duplicate-dueling-xphb-class:fighter:4:asi" for p in res["problems"])
    assert not any(f["id"] == "dueling-xphb" for f in res["sheet"]["feats"])


def test_different_style_is_allowed(catalog):
    res = _res(catalog, [("fighter", 4, {SRD1: ["fighter-fighting-style-archery"],
                                          "class:fighter:4:asi": ["feat:dueling-xphb"]})])
    assert not _opt(_card(res, "class:fighter:4:asi"), "feat:dueling-xphb").get("disabled")
    assert not [p for p in res["problems"] if "duplicate" in p["id"]]
    assert any(f["id"] == "dueling-xphb" for f in res["sheet"]["feats"])


def test_feat_first_blocks_champion_additional_srd_style(catalog):
    cid10 = "class:fighter:10:feature:additional-fighting-style"
    res = _res(catalog, [("fighter", 10, {"class:fighter:4:asi": ["feat:dueling-xphb"],
                                           cid10: ["fighter-fighting-style-dueling"]})],
               subclass={"fighter": "champion"})
    card = _card(res, cid10)
    o = _opt(card, "fighter-fighting-style-dueling")
    assert o["disabled"] and "already taken" in o["disabledReason"]
    assert card["selected"] == []
    assert any(p["id"] == f"fighting-style-duplicate-fighter-fighting-style-dueling-{cid10}" for p in res["problems"])
    assert any(f["id"] == "dueling-xphb" for f in res["sheet"]["feats"])


def test_two_srd_cards_cannot_repeat_a_style(catalog):
    res = _res(catalog, [("fighter", 1, {SRD1: ["fighter-fighting-style-dueling"]}),
                         ("paladin", 2, {"class:paladin:2:feature:paladin-fighting-style": ["fighting-style-dueling"]})])
    card = _card(res, "class:paladin:2:feature:paladin-fighting-style")
    assert _opt(card, "fighting-style-dueling")["disabled"]
    assert not _opt(card, "fighting-style-defense").get("disabled")
    assert card["selected"] == []


def test_2014_has_no_fs_feats_so_no_change(catalog):
    res = _res(catalog, [("fighter", 4, {SRD1: ["fighter-fighting-style-dueling"]})], "2014")
    assert _card(res, SRD1)["selected"] == ["fighter-fighting-style-dueling"]
    assert not [p for p in res["problems"] if "duplicate" in p["id"]]


def test_2024_cards_unchanged(catalog):
    res = _res(catalog, [("fighter", 4, {"class:fighter:1:fighting-style": ["feat:dueling-xphb"],
                                          "class:fighter:4:asi": ["feat:dueling-xphb"]})], "2024")
    assert any(p["id"].startswith("feat-duplicate-dueling-xphb") for p in res["problems"])
