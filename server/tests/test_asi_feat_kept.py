"""F2: a feat that is already selected stays offered (and applied) when the
ruleset or sources hide it, with a warning, instead of silently vanishing."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

CID = "class:fighter:4:asi"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset="mixed", sources=None, pick=None, level=4, cid=CID):
    choices = {cid: [pick]} if pick else {}
    return {
        "ruleset": ruleset, "sources": sources or [],
        "classes": [{"classId": "fighter", "level": level, "choices": choices}],
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _tpl(r, cid=CID):
    return next(c for c in r["choices"] if c["id"] == cid)


def _wids(r):
    return [w["id"] for w in r["warnings"]]


@pytest.mark.parametrize("ruleset,sources", [("2014", []), ("mixed", ["phb"])])
def test_hidden_pick_stays_offered_applied_and_warned(catalog, ruleset, sources):
    r = resolve(_draft(ruleset, sources, "feat:actor-xphb"), catalog)
    opt = next(o for o in _tpl(r)["options"] if o["id"] == "feat:actor-xphb")
    assert opt["hiddenByFilters"] is True
    assert _tpl(r)["status"] == "resolved" and _tpl(r)["selected"] == ["feat:actor-xphb"]
    assert f"feat-hidden-by-filters-{CID}" in _wids(r)
    assert any("actor-xphb" in str(f) for f in r["sheet"]["feats"])
    # Actor's fixed +1 CHA is applied on top of the unpicked character.
    base = resolve(_draft(ruleset, sources), catalog)
    assert r["sheet"]["abilities"]["CHA"] == base["sheet"]["abilities"]["CHA"] + 1


def test_unselected_hidden_feat_not_offered(catalog):
    r = resolve(_draft("2014"), catalog)
    assert "feat:actor-xphb" not in [o["id"] for o in _tpl(r)["options"]]
    assert f"feat-hidden-by-filters-{CID}" not in _wids(r)


def test_offered_pick_is_not_flagged(catalog):
    r = resolve(_draft("2024", None, "feat:alert-xphb"), catalog)
    opt = next(o for o in _tpl(r)["options"] if o["id"] == "feat:alert-xphb")
    assert "hiddenByFilters" not in opt
    assert f"feat-hidden-by-filters-{CID}" not in _wids(r)


def test_structurally_ineligible_pick_is_pruned(catalog):
    r = resolve(_draft("2024", None, "feat:boon-of-combat-prowess-xphb"), catalog)
    assert "feat:boon-of-combat-prowess-xphb" not in [o["id"] for o in _tpl(r)["options"]]
    assert _tpl(r)["selected"] == []
    entry = next(p for p in r["pruned"] if p["choiceId"] == CID)
    assert "can't be taken at this Ability Score Improvement" in entry["reason"]
    assert not any("boon-of-combat-prowess" in str(f) for f in r["sheet"]["feats"])


def test_epic_boon_pick_at_19_stays_offered_under_2014(catalog):
    r = resolve(_draft("2014", None, "feat:boon-of-combat-prowess-xphb", 19, "class:fighter:19:asi"), catalog)
    # EB is not in the 2014 pool, but a slot-19 pick is structurally eligible (mixed) -> kept, flagged
    opt = next(o for o in _tpl(r, "class:fighter:19:asi")["options"] if o["id"] == "feat:boon-of-combat-prowess-xphb")
    assert opt["hiddenByFilters"] is True


def test_species_origin_feat_kept_when_sources_hide_it(catalog):
    cid = "species:human-xphb:feat-0"
    d = _draft("mixed", ["phb"])
    d["classes"][0]["level"] = 1
    d["species"] = {"id": "human-xphb", "choices": {cid: ["feat:alert-xphb"]}}
    r = resolve(d, catalog)
    tpl = _tpl(r, cid)
    opt = next(o for o in tpl["options"] if o["id"] == "feat:alert-xphb")
    assert opt["hiddenByFilters"] is True
    assert tpl["selected"] == ["feat:alert-xphb"]
    assert f"feat-hidden-by-filters-{cid}" in _wids(r)
    assert any("alert-xphb" in str(f) for f in r["sheet"]["feats"])
