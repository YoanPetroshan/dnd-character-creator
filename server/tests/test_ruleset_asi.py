"""Slice 10.3: draft.ruleset decides which ability-score-increase sources
apply (species / background), and which feats the pickers offer."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

BASE = {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}
SOLDIER_CID = "background:soldier-xphb:ability-bonus"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species="dwarf", sub="hill-dwarf", bg="soldier-xphb", ruleset=None, choices=None, species_choices=None, classes=None):
    d = {
        "name": "T", "sources": [],
        "classes": classes or [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": bg, "choices": choices if choices is not None else {SOLDIER_CID: ["str-2+con-1"]}},
        "species": {"id": species, "subspeciesId": sub, "choices": species_choices or {}},
        "abilities": {"method": "manual", "base": dict(BASE)},
    }
    if ruleset is not None:
        d["ruleset"] = ruleset
    return d


def _wids(r):
    return [w["id"] for w in r["warnings"]]


def _cids(r):
    return [c["id"] for c in r["choices"]]


def test_mixed_prevents_double_dip(catalog):
    r = resolve(_draft(ruleset="mixed"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["CON"], a["WIS"]) == (12, 11, 10)
    assert "asi-double-dip-prevented" in _wids(r)
    assert r["problems"] == []


def test_missing_ruleset_is_mixed(catalog):
    r = resolve(_draft(), catalog)
    assert r["sheet"]["abilities"]["CON"] == 11
    assert "asi-double-dip-prevented" in _wids(r)
    assert "ruleset-invalid" not in _wids(r)


def test_2014_ignores_background_asi(catalog):
    r = resolve(_draft(ruleset="2014"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["CON"], a["WIS"]) == (10, 12, 11)
    assert SOLDIER_CID not in _cids(r)
    assert "ruleset-2014-background-asi-ignored" in _wids(r)
    assert r["problems"] == []


def test_2024_ignores_species_asi(catalog):
    r = resolve(_draft(ruleset="2024"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["CON"], a["WIS"]) == (12, 11, 10)
    assert "ruleset-2024-species-asi-ignored" in _wids(r)
    assert "ruleset-2024-background-no-asi" not in _wids(r)


def test_2024_with_srd_background_warns(catalog):
    r = resolve(_draft(ruleset="2024", bg="acolyte", choices={}), catalog)
    assert {"ruleset-2024-background-no-asi", "ruleset-2024-background-no-origin-feat"} <= set(_wids(r))
    assert r["problems"] == []


def test_hill_dwarf_with_2014_background_keeps_species_asi(catalog):
    r = resolve(_draft(ruleset="mixed", bg="acolyte", choices={}), catalog)
    a = r["sheet"]["abilities"]
    assert (a["CON"], a["WIS"]) == (12, 11)
    assert not [w for w in _wids(r) if w.startswith(("ruleset-", "asi-"))]


def test_species_choice_template_suppressed_and_pruned(catalog):
    cid = "species:half-elf:ability-bonus"
    r = resolve(_draft(species="half-elf", sub=None, ruleset="mixed", species_choices={cid: ["str", "dex"]}), catalog)
    assert cid not in _cids(r)
    assert any(p["choiceId"] == cid for p in r["pruned"])
    a = r["sheet"]["abilities"]
    assert (a["CHA"], a["STR"], a["DEX"]) == (10, 12, 10)  # no +2 CHA, no +1/+1


def test_half_elf_choice_present_without_background_asi(catalog):
    cid = "species:half-elf:ability-bonus"
    r = resolve(_draft(species="half-elf", sub=None, bg="acolyte", choices={}, ruleset="mixed"), catalog)
    assert cid in _cids(r)


def test_2024_suppresses_vrgr_lineage_asi(catalog):
    lineage = next(
        k for k, v in catalog.races.items()
        if v.get("ability_bonus_options") and not v.get("ability_bonuses") and v.get("source") == "VRGR"
    )
    cid = f"species:{lineage}:ability-bonus"
    r2024 = resolve(_draft(species=lineage, sub=None, bg="acolyte", choices={}, ruleset="2024"), catalog)
    assert cid not in _cids(r2024)
    assert "ruleset-2024-species-asi-ignored" in _wids(r2024)
    r2014 = resolve(_draft(species=lineage, sub=None, bg="acolyte", choices={}, ruleset="2014"), catalog)
    assert cid in _cids(r2014)


def test_2024_suppresses_subrace_asi_options(catalog):
    sub = next(
        k for k, v in catalog.subraces.items()
        if v.get("ability_bonus_options") and v["race"]["index"] in catalog.races
    )
    race = catalog.subraces[sub]["race"]["index"]
    cid = f"species:{race}:ability-bonus"
    r = resolve(_draft(species=race, sub=sub, bg="acolyte", choices={}, ruleset="2024"), catalog)
    assert cid not in _cids(r)
    assert "ruleset-2024-species-asi-ignored" in _wids(r)


def test_invalid_ruleset_falls_back_to_mixed(catalog):
    r = resolve(_draft(ruleset="banana"), catalog)
    assert "ruleset-invalid" in _wids(r)
    assert "asi-double-dip-prevented" in _wids(r)
    assert r["problems"] == []


def test_2014_does_not_offer_or_apply_2024_asi_feat(catalog):
    cid = "class:fighter:4:asi"
    classes = [{"classId": "fighter", "level": 4, "choices": {cid: ["feat:athlete-xphb"]}}]
    for ruleset, offered in (("2014", False), ("mixed", True), ("2024", True)):
        r = resolve(_draft(species="human", sub=None, bg="acolyte", choices={}, ruleset=ruleset, classes=classes), catalog)
        tpl = next(c for c in r["choices"] if c["id"] == cid)
        assert ("feat:athlete-xphb" in [o["id"] for o in tpl["options"]]) is offered
        assert ("feat:athlete-xphb" in tpl["selected"]) is offered
    r = resolve(_draft(species="human", sub=None, bg="acolyte", choices={}, ruleset="2014", classes=classes), catalog)
    # (2014 pool = the category-less PHB/XGE/TCE... feats plus the General
    # Unearthed Arcana ones.)
    ids = [o["id"] for o in next(c for c in r["choices"] if c["id"] == cid)["options"]]
    assert "feat:abjuration-adept-au" in ids
    assert "feat:great-weapon-master-phb" in ids
