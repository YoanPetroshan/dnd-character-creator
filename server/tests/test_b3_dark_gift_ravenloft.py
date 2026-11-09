"""B3 (owner decision 2026-11-09): Dark Gift feats (RHW) officially need a Ravenloft campaign. The app has no campaign setting,
so the only check is the book: a NON-BLOCKING warning `dark-gift-needs-ravenloft-<feat>` when a Dark Gift feat is held while
RHW is switched off in `sources` (an empty list = every book on). Nothing is removed or disabled.

VERIFIED against the vendored feats.json first: all nine RHW Dark Gift feats (category DG) carry `prerequisite:
[{"campaign": ["Ravenloft"]}]`, and no other feat does. Survivor / Sharp Eye (the plain feats of Haunted One / Investigator)
carry no such prerequisite, so the F1.3 default never warns."""
from __future__ import annotations

import json

import pytest

from catalog.loader import load
from catalog.official_source import has_official
from catalog.official.paths import official_dir
from engine.resolve import resolve
from i18n.messages import msg, render

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
DG = ["aberrant-anatomy-rhw", "echoing-soul-rhw", "gathered-whispers-rhw", "living-shadow-rhw", "mist-walker-rhw",
      "second-skin-rhw", "symbiotic-being-rhw", "touch-of-death-rhw", "watchers-rhw"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(*, bg="acolyte", bg_choices=None, asi=None, sources=None, ruleset="mixed"):
    classes = [{"classId": "fighter", "level": 4 if asi else 1, "choices": {"class:fighter:4:asi": asi} if asi else {}}]
    return {
        "name": "T", "sources": [] if sources is None else sources, "ruleset": ruleset, "classes": classes,
        "background": {"id": bg, "choices": bg_choices or {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {a: 12 for a in ABS}},
        "equipment": {"added": [], "skipped": False}, "details": {},
        "preferences": {"usePrerequisites": {"feats": False}},
    }


def _mw(feat="mist-walker-rhw", **kw):
    """Mist Wanderer with a Dark Gift pick on its W4 card (the ASI pool never offers Dark Gifts)."""
    return _draft(bg="mist-wanderer-rhw", bg_choices={"background:mist-wanderer-rhw:feat-0": [f"feat:{feat}"]}, **kw)


def _ids(res):
    return [w["id"] for w in res["warnings"] if w["id"].startswith("dark-gift-needs-ravenloft")]


def test_data_only_the_nine_dark_gifts_need_ravenloft(catalog):
    raw = json.load(open(official_dir() / "feats.json"))["feat"]
    need = sorted(f["name"] for f in raw if any("Ravenloft" in (p.get("campaign") or []) for p in f.get("prerequisite") or []))
    assert len(need) == 9
    dg = sorted(f["name"] for f in raw if f.get("category") == "DG")
    assert need == dg
    from engine.resolve import _needs_ravenloft
    assert sorted(i for i, f in catalog.feats.items() if _needs_ravenloft(f)) == DG
    assert all(catalog.feats[i].get("category") == "DG" and catalog.feats[i]["source"] == "RHW" for i in DG)
    for plain in ("survivor-rhw", "sharp-eye-rhw"):
        assert not _needs_ravenloft(catalog.feats[plain])


@pytest.mark.parametrize("sources", [[], ["rhw"], ["RHW", "srd"], ["srd", "phb", "xphb", "rhw"]])
def test_rhw_on_means_no_warning(catalog, sources):
    res = resolve(_mw(sources=sources), catalog)
    assert "mist-walker-rhw" in [f["id"] for f in res["sheet"]["feats"]]
    assert _ids(res) == []


@pytest.mark.parametrize("sources", [["srd"], ["srd", "phb", "xphb"], ["xphb"]])
@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_rhw_off_with_a_dark_gift_warns_without_blocking(catalog, sources, ruleset):
    res = resolve(_mw(sources=sources, ruleset=ruleset), catalog)
    assert _ids(res) == ["dark-gift-needs-ravenloft-mist-walker-rhw"]
    assert "mist-walker-rhw" in [f["id"] for f in res["sheet"]["feats"]]  # still held and applied
    w = next(w for w in res["warnings"] if w["id"].startswith("dark-gift-needs-ravenloft"))
    assert render(w["message"], "en") == ("Mist Walker is a Dark Gift feat, which officially needs a Ravenloft campaign, and the RHW "
                                          "book is switched off in Sources; it is still applied.")
    assert "Ravenloft" in render(w["message"], "bg") and "(Feat)" in render(w["message"], "bg")
    assert not [p for p in res["problems"] if "ravenloft" in p["id"]]


def test_picked_through_the_background_card_toggles_with_the_source(catalog):
    on = resolve(_mw("watchers-rhw", sources=["srd", "rhw"]), catalog)
    off = resolve(_mw("watchers-rhw", sources=["srd"]), catalog)
    assert _ids(on) == []
    assert _ids(off) == ["dark-gift-needs-ravenloft-watchers-rhw"]


def test_no_dark_gift_means_no_warning(catalog):
    for sources in ([], ["srd"]):
        res = resolve(_draft(asi=["feat:lucky-xphb"] if sources == [] else ["feat:alert-phb"], sources=sources), catalog)
        assert _ids(res) == []
    assert _ids(resolve(_draft(), catalog)) == []


@pytest.mark.parametrize("bid,sources", [("haunted-one-rhw", ["srd"]), ("investigator-rhw", ["srd", "xphb"]),
                                         ("haunted-one-rhw", ["srd", "rhw"]), ("haunted-one-rhw", [])])
def test_the_f1_3_default_plain_feat_never_warns(catalog, bid, sources):
    """Survivor / Sharp Eye is the default of the either-or card; with RHW off it is kept (hiddenByFilters) and only the old
    `feat-hidden-by-filters` warning appears, never the Ravenloft one."""
    res = resolve(_draft(bg=bid, sources=sources), catalog)
    assert [f["id"] for f in res["sheet"]["feats"]] in (["survivor-rhw"], ["sharp-eye-rhw"])
    assert _ids(res) == []


def test_an_either_or_dark_gift_pick_with_rhw_off_warns(catalog):
    cid = "background:haunted-one-rhw:feat-0"
    res = resolve(_draft(bg="haunted-one-rhw", bg_choices={cid: ["feat:second-skin-rhw"]}, sources=["srd"]), catalog)
    assert _ids(res) == ["dark-gift-needs-ravenloft-second-skin-rhw"]


def test_one_warning_per_held_dark_gift(catalog):
    """Mist Wanderer holds exactly one Dark Gift: one warning, whatever the pick."""
    for gift in DG:
        assert _ids(resolve(_mw(gift, sources=["srd"]), catalog)) == [f"dark-gift-needs-ravenloft-{gift}"]


def test_message_catalog_entry_has_both_languages():
    m = msg("dark-gift-needs-ravenloft", feat="Mist Walker")
    assert "Mist Walker" in render(m, "en") and "Mist Walker" in render(m, "bg") and render(m, "bg") != render(m, "en")
