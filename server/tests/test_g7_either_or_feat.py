"""G7: Haunted One / Investigator (RHW) "Survivor / Sharp Eye or a Dark Gift feat of your choice" as ONE pick card.

VERIFIED against the vendored backgrounds.json first (the data DOES encode the either-or):
  Haunted One   feats: [{"survivor|rhw": true}, {"anyFromCategory": {"category": ["DG"]}}]
                entry "Feat:" = "{@feat Survivor|RHW} or a {@filter Dark Gift feat of your choice|feats|category=DG}"
  Investigator  feats: [{"sharp eye|rhw": true}, {"anyFromCategory": {"category": ["DG"]}}]
                entry "Feat:" = "{@feat Sharp Eye|RHW} or a {@filter Dark Gift feat of your choice|feats|category=DG}"
Two entries of the `feats` array are alternatives (the shape Rewarded / Ruined use for their three-way choice), the second one
is the same wildcard Mist Wanderer / Spirit Medium carry alone.

Rule matrix:
  converter       feats [] / feat_refs [] / feat_options [], feat_grants [{count 1, category DG, include [<plain feat ref>]}]
  card            background:<id>:feat-0 (the W4 machinery), kind background, count 1, options = the plain feat FIRST, then the 9
                  Dark Gifts; description "Choose Survivor or a Dark Gift feat."
                  F1: NO stored pick = the plain feat (the card shows it selected, the sheet holds it), as before G7
  pick the plain feat   the sheet holds it (origin background); pick a Dark Gift   only that one (never both)
  sources without RHW   F1: the plain feat stays (flagged hiddenByFilters, the Dark Gifts are hidden): the character keeps it
  S2 taken map    the picked feat is disabled on the later species Origin card; all three rulesets alike
  untouched       Mist Wanderer / Spirit Medium (no `include`), every other background, ASI cards"""
from __future__ import annotations

import json

import pytest

from catalog.loader import load
from catalog.official_source import has_official
from catalog.official.paths import official_dir
from engine.resolve import resolve
from i18n.messages import msg, render

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

SOURCES = ["srd", "phb", "xphb", "rhw", "frhof"]
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
DG = ["aberrant-anatomy-rhw", "echoing-soul-rhw", "gathered-whispers-rhw", "living-shadow-rhw", "mist-walker-rhw",
      "second-skin-rhw", "symbiotic-being-rhw", "touch-of-death-rhw", "watchers-rhw"]
CASES = {"haunted-one-rhw": ("Haunted One", "survivor-rhw", "Survivor"),
         "investigator-rhw": ("Investigator", "sharp-eye-rhw", "Sharp Eye")}


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def raw():
    data = json.load(open(official_dir() / "backgrounds.json"))["background"]
    return {f"{r['name']}|{r['source']}": r for r in data if "_copy" not in r}


def _draft(bg, *, choices=None, sources=None, ruleset="2024", species="human", species_choices=None):
    return {
        "name": "T", "sources": SOURCES if sources is None else sources, "ruleset": ruleset,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": bg, "choices": choices or {}},
        "species": {"id": species, "choices": species_choices or {}},
        "abilities": {"method": "manual", "base": {a: 10 for a in ABS}},
        "equipment": {"added": [], "skipped": False}, "details": {},
        "preferences": {"usePrerequisites": {"feats": False}},
    }


def _card(res, bid):
    return next((c for c in res["choices"] if c["id"] == f"background:{bid}:feat-0"), None)


def _feat_ids(res):
    return [f["id"] for f in res["sheet"]["feats"]]


# ---- the data ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bid", sorted(CASES))
def test_raw_records_encode_the_either_or(raw, bid):
    name, feat, feat_name = CASES[bid]
    r = raw[f"{name}|RHW"]
    plain, wildcard = r["feats"]
    assert plain == {feat[:-len("-rhw")].replace("-", " ") + "|rhw": True}
    assert wildcard == {"anyFromCategory": {"category": ["DG"]}}
    entry = next(i["entry"] for i in r["entries"][0]["items"] if i["name"] == "Feat:")
    assert entry == "{@feat " + feat_name + "|RHW} or a {@filter Dark Gift feat of your choice|feats|category=DG}"


@pytest.mark.parametrize("bid", sorted(CASES))
def test_converter_output(catalog, bid):
    _name, feat, _fn = CASES[bid]
    bg = catalog.backgrounds[bid]
    assert bg["feats"] == [] and bg["feat_refs"] == [] and bg["feat_options"] == []
    assert bg["feat_grants"] == [{"count": 1, "category": "DG", "include": [feat]}]


def test_other_backgrounds_are_not_either_or(catalog):
    withs = sorted(i for i, b in catalog.backgrounds.items() if any(g.get("include") for g in b.get("feat_grants") or []))
    assert withs == ["haunted-one-rhw", "investigator-rhw"]
    for bid in ("mist-wanderer-rhw", "spirit-medium-rhw"):
        assert catalog.backgrounds[bid]["feat_grants"] == [{"count": 1, "category": "DG"}]
    # the rewarded / ruined three-way alternatives keep their own shape
    assert catalog.backgrounds["rewarded-bmt"]["feat_options"] and not catalog.backgrounds["rewarded-bmt"]["feat_grants"]


# ---- the card ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bid", sorted(CASES))
@pytest.mark.parametrize("ruleset", ["2024", "mixed", "2014"])
def test_card_offers_the_plain_feat_first_then_the_dark_gifts(catalog, bid, ruleset):
    _name, feat, feat_name = CASES[bid]
    res = resolve(_draft(bid, ruleset=ruleset), catalog)
    card = _card(res, bid)
    assert card["source"]["kind"] == "background" and card["count"] == 1 and card["status"] == "resolved"
    assert card["selected"] == [f"feat:{feat}"]  # F1: the default
    assert [o["id"] for o in card["options"]] == [f"feat:{feat}"] + [f"feat:{d}" for d in DG]
    assert str(card["description"]) == f"Choose {feat_name} or a Dark Gift feat."
    assert _feat_ids(res) == [feat]
    assert res["warnings"] == [] or all("origin-feat" not in w["id"] for w in res["warnings"])


@pytest.mark.parametrize("bid", sorted(CASES))
def test_pick_the_plain_feat(catalog, bid):
    _name, feat, _fn = CASES[bid]
    cid = f"background:{bid}:feat-0"
    res = resolve(_draft(bid, choices={cid: [f"feat:{feat}"]}), catalog)
    assert _feat_ids(res) == [feat]
    assert next(f for f in res["sheet"]["feats"] if f["id"] == feat)["origin"] == "background"
    assert _card(res, bid)["status"] == "resolved" and res["sheet"]["grantedFeats"] == [feat]


@pytest.mark.parametrize("bid", sorted(CASES))
def test_pick_a_dark_gift_instead(catalog, bid):
    _name, feat, _fn = CASES[bid]
    cid = f"background:{bid}:feat-0"
    res = resolve(_draft(bid, choices={cid: ["feat:mist-walker-rhw"]}), catalog)
    assert _feat_ids(res) == ["mist-walker-rhw"] and feat not in _feat_ids(res)
    assert next(f for f in res["sheet"]["feats"])["origin"] == "background"


@pytest.mark.parametrize("bid", sorted(CASES))
def test_only_one_pick_counts(catalog, bid):
    _name, feat, _fn = CASES[bid]
    cid = f"background:{bid}:feat-0"
    res = resolve(_draft(bid, choices={cid: [f"feat:{feat}", "feat:mist-walker-rhw"]}), catalog)
    assert _feat_ids(res) == [feat]


@pytest.mark.parametrize("bid", sorted(CASES))
@pytest.mark.parametrize("sources", [["srd", "xphb"], ["srd"], ["xphb"]])
def test_sources_without_rhw_keep_the_plain_feat(catalog, bid, sources):
    """F1 (was: the card was `unavailable` with 0 options and the character had no feat at all)."""
    _name, feat, _fn = CASES[bid]
    res = resolve(_draft(bid, sources=sources), catalog)
    card = _card(res, bid)
    assert [o["id"] for o in card["options"]] == [f"feat:{feat}"] and card["options"][0]["hiddenByFilters"] is True
    assert card["status"] == "resolved" and card["selected"] == [f"feat:{feat}"] and not card.get("unavailableReason")
    assert _feat_ids(res) == [feat]
    assert not [c for c in res["choices"] if c["status"] == "pending" and c["id"].endswith(":feat-0")]
    assert any(w["id"] == f"feat-hidden-by-filters-background:{bid}:feat-0" for w in res["warnings"])  # the warning, not a loss


@pytest.mark.parametrize("bid", sorted(CASES))
def test_a_saved_complete_draft_without_a_pick_still_has_the_plain_feat(catalog, bid):
    """The G7 migration: a draft saved before G7 holds the background with no `:feat-0` key (its choices object is empty or
    holds other keys) and must resolve to the feat the background always granted."""
    _name, feat, _fn = CASES[bid]
    for ruleset in ("2014", "mixed", "2024"):
        for choices in ({}, {"background:other:feat-0": ["feat:x"]}, {f"background:{bid}:feat-0": []}):
            res = resolve(_draft(bid, choices=choices, ruleset=ruleset), catalog)
            assert _feat_ids(res) == [feat], (ruleset, choices)
            assert res["sheet"]["grantedFeats"] == [feat]


@pytest.mark.parametrize("bid", sorted(CASES))
def test_a_dark_gift_replaces_the_default_and_never_adds_to_it(catalog, bid):
    _name, feat, _fn = CASES[bid]
    res = resolve(_draft(bid, choices={f"background:{bid}:feat-0": ["feat:watchers-rhw"]}), catalog)
    assert _feat_ids(res) == ["watchers-rhw"]
    assert _card(res, bid)["selected"] == ["feat:watchers-rhw"]
    # with RHW off the Dark Gift is hidden: the stored pick is kept by the filter exception and still wins
    res = resolve(_draft(bid, choices={f"background:{bid}:feat-0": ["feat:watchers-rhw"]}, sources=["srd"]), catalog)
    assert _feat_ids(res) == ["watchers-rhw"]


@pytest.mark.parametrize("bid", sorted(CASES))
def test_the_default_is_not_taken_when_the_plain_feat_is_disabled(catalog, bid):
    """Prerequisites on (the Dark Gifts and the plain feat have none): the default is the plain feat; a stale stored id is
    left alone (no default is invented over a stored value)."""
    _name, feat, _fn = CASES[bid]
    res = resolve(_draft(bid, choices={f"background:{bid}:feat-0": ["feat:no-such-feat"]}), catalog)
    assert _feat_ids(res) == []


def test_the_default_only_applies_to_the_either_or_backgrounds(catalog):
    res = resolve(_draft("mist-wanderer-rhw"), catalog)
    card = _card(res, "mist-wanderer-rhw")
    assert card["status"] == "pending" and card["selected"] == [] and _feat_ids(res) == []


def test_kitchen_sink_filler_path(catalog):
    """The filler path of the kitchen-sink sinks (tests/kitchen_sink.py `fill`, which stores the first option of a pending
    card) is unaffected: the card is already resolved by the default, with Survivor, and the filled sink holds it once."""
    import kitchen_sink
    res = resolve(kitchen_sink.build("haunted-one-fighter3-2014", catalog, resolve), catalog)
    assert [f["id"] for f in res["sheet"]["feats"]] == ["survivor-rhw"]
    assert _card(res, "haunted-one-rhw")["selected"] == ["feat:survivor-rhw"]


@pytest.mark.parametrize("bid", sorted(CASES))
def test_picked_feat_is_taken_on_the_later_species_card(catalog, bid):
    """Survivor / Sharp Eye are Origin feats: the Human (XPHB) Origin card must read "already taken" for the background's pick."""
    _name, feat, _fn = CASES[bid]
    res = resolve(_draft(bid, species="human-xphb", choices={f"background:{bid}:feat-0": [f"feat:{feat}"]}), catalog)
    opt = next(o for o in _card_species(res)["options"] if o["id"] == f"feat:{feat}")
    assert opt["disabled"] and "already taken" in str(opt["disabledReason"])


def _card_species(res):
    return next(c for c in res["choices"] if c["id"] == "species:human-xphb:feat-0")


def test_unrelated_backgrounds_are_unchanged(catalog):
    res = resolve(_draft("acolyte"), catalog)
    assert not [c for c in res["choices"] if c["id"].startswith("background:") and ":feat-" in c["id"]]
    res = resolve(_draft("mist-wanderer-rhw"), catalog)
    card = _card(res, "mist-wanderer-rhw")
    assert [o["id"] for o in card["options"]] == [f"feat:{d}" for d in DG]
    assert str(card["description"]) == "Choose a Dark Gift feat."


# ---- messages ------------------------------------------------------------------------------------------------------

def test_description_message_has_both_languages():
    m = msg("desc-feat-or-dark-gift", name="Survivor")
    assert render(m, "en") == "Choose Survivor or a Dark Gift feat."
    bg = render(m, "bg")
    assert bg == "Изберете Survivor или талант (Feat) Dark Gift."  # T1: the Bulgarian term, then the English in brackets
