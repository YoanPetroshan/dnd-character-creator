"""RP4 (A4, open question 16): under ruleset 2024 a Fighting Initiate style is seen by a LATER Fighting Style feat card.

Governing sentences (catalog text, pinned by `test_quotes_match_catalog_text`):

  Fighting Initiate (TCE)   "If you already have a style, the one you choose must be different."
  XPHB Fighter Fighting Style  "gain a Fighting Style feat of your choice."

Rule: in the F1 ordered walk (origin feats, then (class index, class level), a card before the ASI of its level) a
Fighting Initiate pick adds ``name:<style>`` to ``seen`` at its position, so the LATER holder is the duplicate: a
2024 Fighting Style feat card disables the same-named FS feat ("already taken (Dueling, Fighting Initiate)") and a
stored duplicate gives the usual ``feat-duplicate-*`` problem (once, no extra ``pruned`` entry). Under mixed / 2014
nothing changes (FE9 ``pruned`` path for SRD style cards).

Matrix: FI first x FS card (other class / same class later card / later ASI) | FS first x FI (unchanged FE9) |
different style | origin (species) FI | invalid FI pick | mixed guard | empty feat catalog."""
import copy

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FI = "fighting-initiate-tce"
DUEL = "fighter-fighting-style-dueling"
ARCH = "fighter-fighting-style-archery"
FS1 = "class:fighter:1:fighting-style"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", species=None, subclass=None):
    d = {"name": "t", "ruleset": ruleset, "sources": [],
         "classes": [{"classId": c, "level": lv, "choices": ch, **({"subclassId": subclass[c]} if subclass and c in subclass else {})}
                     for c, lv, ch in classes],
         "background": {"id": "acolyte", "choices": {}}, "species": species or {"id": "human"},
         "abilities": {"method": "manual", "base": {a: 12 for a in ABS}},
         "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}, "preferences": {}}
    return d


def fi_cid(cls, lvl):
    return f"class:{cls}:{lvl}:asi:feat:{FI}:fighting-style"


def rogue_fi(style=DUEL, lvl=4):
    return {f"class:rogue:{lvl}:asi": [f"feat:{FI}"], fi_cid("rogue", lvl): [style]}


def _card(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _dups(r):
    return [p["id"] for p in r["problems"] if p["id"].startswith("feat-duplicate-")]


def test_quotes_match_catalog_text(catalog):
    fi = " ".join(catalog.feats[FI]["entries"][:1])
    assert "If you already have a style, the one you choose must be different." in fi
    assert "gain a Fighting Style feat of your choice" in " ".join(catalog.features["xphb-fighter-1-fighting-style"]["desc"])


def test_fi_first_disables_the_same_fs_feat_in_a_later_class_card(catalog):
    r = resolve(_draft([("rogue", 4, rogue_fi()), ("fighter", 1, {})]), catalog)
    card = _card(r, FS1)
    o = _opt(card, "feat:dueling-xphb")
    assert o["disabled"] and o["disabledReason"] == "already taken (Dueling, Fighting Initiate)"
    assert not _opt(card, "feat:archery-xphb").get("disabled")


def test_stored_duplicate_gives_one_problem_and_is_not_applied(catalog):
    ch = {FS1: ["feat:dueling-xphb"]}
    r = resolve(_draft([("rogue", 4, rogue_fi()), ("fighter", 1, ch)]), catalog)
    assert _dups(r) == [f"feat-duplicate-dueling-xphb-{FS1}"]
    assert _card(r, FS1)["selected"] == []
    assert not any(f["id"] == "dueling-xphb" for f in r["sheet"]["feats"])
    assert len([p for p in r["pruned"] if p["choiceId"] == FS1]) == 0  # no double reporting
    assert _card(r, fi_cid("rogue", 4))["selected"] == [DUEL]


def test_different_style_is_fine(catalog):
    r = resolve(_draft([("rogue", 4, rogue_fi(ARCH)), ("fighter", 1, {FS1: ["feat:dueling-xphb"]})]), catalog)
    assert _dups(r) == [] and _card(r, FS1)["selected"] == ["feat:dueling-xphb"]
    assert any(f["id"] == "dueling-xphb" for f in r["sheet"]["feats"])


def test_fs_first_then_fi_is_the_fe9_behaviour(catalog):
    """Fighter 1 Dueling, FI at 4 picks Dueling: the FI card is the duplicate (unchanged)."""
    ch = {FS1: ["feat:dueling-xphb"], "class:fighter:4:asi": [f"feat:{FI}"],
          fi_cid("fighter", 4): [DUEL]}
    r = resolve(_draft([("fighter", 4, ch)]), catalog)
    c = _card(r, fi_cid("fighter", 4))
    assert _opt(c, DUEL)["disabledReason"] == "already taken (Dueling, XPHB)"
    assert c["selected"] == [] and _dups(r) == []
    assert len([p for p in r["pruned"] if p["choiceId"] == fi_cid("fighter", 4)]) == 1


def test_champion_additional_card_and_later_asi_see_the_fi_style(catalog):
    ch = {"class:fighter:4:asi": [f"feat:{FI}"], fi_cid("fighter", 4): [DUEL],
          "class:fighter:8:asi": ["feat:dueling-xphb"]}
    r = resolve(_draft([("fighter", 10, ch)], subclass={"fighter": "champion-xphb"}), catalog)
    asi8 = _card(r, "class:fighter:8:asi")
    o = _opt(asi8, "feat:dueling-xphb")
    assert o["disabled"] and o["disabledReason"] == "already taken (Dueling, Fighting Initiate)"
    assert _dups(r) == ["feat-duplicate-dueling-xphb-class:fighter:8:asi"]


def test_invalid_fi_pick_adds_nothing(catalog):
    r = resolve(_draft([("rogue", 4, rogue_fi("not-a-style")), ("fighter", 1, {})]), catalog)
    assert not _opt(_card(r, FS1), "feat:dueling-xphb").get("disabled")


def test_unpicked_fi_adds_nothing(catalog):
    ch = {"class:rogue:4:asi": [f"feat:{FI}"]}
    r = resolve(_draft([("rogue", 4, ch), ("fighter", 1, {})]), catalog)
    assert not any(o.get("disabled") for o in _card(r, FS1)["options"] if o["id"].endswith("-xphb"))


def test_origin_fi_species_pick_is_seen(catalog):
    vh = "species:human-phb:subspecies:human-phb-variant-phb:feat-0"
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb",
               "choices": {vh: [f"feat:{FI}"], f"{vh}:feat:{FI}:fighting-style": [DUEL]}}
    r = resolve(_draft([("fighter", 1, {})], species=species), catalog)
    if _card(r, f"{vh}:feat:{FI}:fighting-style") is None:
        pytest.skip("Variant Human is not offered under 2024 in this catalog")
    o = _opt(_card(r, FS1), "feat:dueling-xphb")
    assert o["disabled"] and o["disabledReason"] == "already taken (Dueling, Fighting Initiate)"


def test_mixed_is_unchanged(catalog):
    srd = "class:fighter:1:feature:fighter-fighting-style"
    r = resolve(_draft([("rogue", 4, rogue_fi()), ("fighter", 1, {srd: [DUEL]})], ruleset="mixed"), catalog)
    assert not [p for p in r["problems"] if "duplicate" in p["id"]]
    assert _opt(_card(r, srd), DUEL)["disabledReason"] == "already taken (Dueling, Fighting Initiate)"
    assert any(p["choiceId"] == srd for p in r["pruned"])


def test_empty_feat_catalog_degrades(catalog):
    bare = copy.copy(catalog)
    bare.feats = {}
    r = resolve(_draft([("rogue", 4, rogue_fi()), ("fighter", 1, {})]), bare)
    assert _dups(r) == []
