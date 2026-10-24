"""W4 (gap audit F5): three ruleset-2024 backgrounds showed no origin feat on the sheet.

VERIFIED against the raw 5etools backgrounds.json (the catalog text is the rule; quoted below, tags kept):

  Genie Touched (FRHoF)  raw record has NO `feats` field at all (a data gap in the file), but its own entry reads
                         "Feat: {@feat Magic Initiate|XPHB} (Wizard)". Same shape as the 4 backgrounds that grant
                         "magic initiate; cleric|xphb" etc., so the converter restores that grant from the record's text.
  Mist Wanderer (RHW)    `feats: [{"anyFromCategory": {"category": ["DG"]}}]`, text "A {@filter Dark Gift feat of your
                         choice|feats|category=DG} ({@feat Mist Walker|RHW} is recommended)". Not a fixed feat: a pick.
  Spirit Medium (RHW)    same shape, "({@feat Gathered Whispers|RHW} is recommended)".
  Haunted One / Investigator (RHW) carry the SAME wildcard beside a plain grant (Survivor / Sharp Eye) and the text says
                         "{@feat Survivor|RHW} or a {@filter Dark Gift feat ...}": an alternative, already served by the
                         plain grant; they get no pick card (deferred, listed in ARCHITECTURE).

Matrix: raw pins | converter output | card (cid `background:<id>:feat-0`, kind background, 9 Dark Gift options) |
  the pick reaches the sheet (origin background) and its cascaded choices live under the same cid prefix |
  S2 duplicate map both ways (a feat already taken is disabled here; an ASI pick of it is the duplicate) |
  sources without RHW -> `unavailable`, never pending | no-origin-feat warning gone | other backgrounds untouched.
"""
from __future__ import annotations

import json

import pytest

from catalog import reference_data as ref
from catalog.loader import load
from catalog.official_source import has_official
from catalog.official.paths import official_dir
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

SOURCES = ["srd", "phb", "xphb", "rhw", "frhof"]
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
DG = {"aberrant-anatomy-rhw", "echoing-soul-rhw", "gathered-whispers-rhw", "living-shadow-rhw", "mist-walker-rhw",
      "second-skin-rhw", "symbiotic-being-rhw", "touch-of-death-rhw", "watchers-rhw"}


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def raw():
    data = json.load(open(official_dir() / "backgrounds.json"))["background"]
    return {f"{r['name']}|{r['source']}": r for r in data if "_copy" not in r}


def _draft(bg, *, choices=None, sources=None, ruleset="2024", fighter=1, fighter_choices=None, species="human"):
    return {
        "name": "T", "sources": SOURCES if sources is None else sources, "ruleset": ruleset,
        "classes": [{"classId": "fighter", "level": fighter, "choices": fighter_choices or {}}],
        "background": {"id": bg, "choices": choices or {}},
        "species": {"id": species, "choices": {}},
        "abilities": {"method": "manual", "base": {a: 10 for a in ABS}},
        "equipment": {"added": [], "skipped": False}, "details": {},
        "preferences": {"usePrerequisites": {"feats": False}},
    }


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


MIST = "background:mist-wanderer-rhw:feat-0"
SPIRIT = "background:spirit-medium-rhw:feat-0"


# --- raw data pins ----------------------------------------------------------------------------------------------

def test_raw_genie_touched_has_no_feats_field_but_names_magic_initiate(raw):
    r = raw["Genie Touched|FRHoF"]
    assert "feats" not in r
    assert "{@feat Magic Initiate|XPHB} (Wizard)" in json.dumps(r)


@pytest.mark.parametrize("key,recommended", [("Mist Wanderer|RHW", "Mist Walker"), ("Spirit Medium|RHW", "Gathered Whispers")])
def test_raw_dark_gift_backgrounds_carry_only_a_category_wildcard(raw, key, recommended):
    r = raw[key]
    assert r["feats"] == [{"anyFromCategory": {"category": ["DG"]}}]
    text = json.dumps(r)
    assert "Dark Gift feat of your choice" in text and recommended in text


@pytest.mark.parametrize("key", ["Haunted One|RHW", "Investigator|RHW"])
def test_raw_haunted_one_and_investigator_are_alternatives(raw, key):
    r = raw[key]
    assert r["feats"][0].get(next(iter(r["feats"][0]))) is True and "anyFromCategory" in r["feats"][1]
    assert "{@feat" in json.dumps(r) and "} or a {@filter Dark Gift feat" in json.dumps(r)


def test_only_these_two_dark_gift_wildcards_have_no_plain_feat(raw):
    bare = sorted(k for k, r in raw.items()
                  if r.get("edition") == "one" and not any(v is True for e in r.get("feats") or [] for v in e.values()))
    assert bare == ["Genie Touched|FRHoF", "Mist Wanderer|RHW", "Spirit Medium|RHW"]


def test_text_pin_for_the_restored_grant(raw):
    key = "genie touched|frhof"
    assert ref.BACKGROUND_FEATS_FROM_TEXT[key]["grant"] == [{"magic initiate; wizard|xphb": True}]
    assert ref.BACKGROUND_FEATS_FROM_TEXT[key]["quote"] in json.dumps(raw["Genie Touched|FRHoF"])


# --- converter / catalog ----------------------------------------------------------------------------------------

def test_genie_touched_grants_magic_initiate_wizard(catalog):
    bg = catalog.backgrounds["genie-touched-frhof"]
    assert bg["feats"] == ["magic-initiate"] and bg["feat_refs"] == ["magic-initiate-xphb"]
    assert bg["feat_variant_hints"] == {"magic-initiate-xphb": "Wizard Spells"}
    assert not bg.get("feat_grants")


@pytest.mark.parametrize("bid", ["mist-wanderer-rhw", "spirit-medium-rhw"])
def test_dark_gift_backgrounds_carry_a_feat_grant(catalog, bid):
    bg = catalog.backgrounds[bid]
    assert bg["feat_grants"] == [{"count": 1, "category": "DG"}] and bg["feats"] == []


def test_exactly_two_backgrounds_carry_feat_grants(catalog):
    assert sorted(i for i, b in catalog.backgrounds.items() if b.get("feat_grants")) == ["mist-wanderer-rhw", "spirit-medium-rhw"]


def test_every_2024_background_now_has_an_origin_feat_or_a_pick(catalog):
    bare = [i for i, b in catalog.backgrounds.items()
            if b.get("ruleset") == "2024" and not (b.get("feats") or b.get("feat_options") or b.get("feat_grants"))]
    assert bare == []


# --- the sheet ---------------------------------------------------------------------------------------------------

def test_genie_touched_sheet_has_the_feat_and_no_warning(catalog):
    res = resolve(_draft("genie-touched-frhof"), catalog)
    feats = {f["id"]: f for f in res["sheet"]["feats"]}
    assert feats["magic-initiate-xphb"]["origin"] == "background"
    assert "ruleset-2024-background-no-origin-feat" not in {w["id"] for w in res["warnings"]}
    assert "feat:magic-initiate-xphb:spell-variant" in {c["id"] for c in res["choices"]}


@pytest.mark.parametrize("bid,cid", [("mist-wanderer-rhw", MIST), ("spirit-medium-rhw", SPIRIT)])
def test_dark_gift_card_is_pending_with_the_nine_dark_gifts(catalog, bid, cid):
    res = resolve(_draft(bid), catalog)
    card = _card(res, cid)
    assert card["status"] == "pending" and card["count"] == 1 and card["source"]["kind"] == "background"
    assert {o["id"] for o in card["options"]} == {f"feat:{i}" for i in DG}
    assert not any(o.get("disabled") for o in card["options"])
    assert res["sheet"]["feats"] == []
    assert "ruleset-2024-background-no-origin-feat" not in {w["id"] for w in res["warnings"]}


def test_dark_gift_pick_reaches_the_sheet_as_a_background_feat(catalog):
    res = resolve(_draft("mist-wanderer-rhw", choices={MIST: ["feat:mist-walker-rhw"]}), catalog)
    card = _card(res, MIST)
    assert card["status"] == "resolved" and card["selected"] == ["feat:mist-walker-rhw"]
    assert [(f["id"], f["origin"]) for f in res["sheet"]["feats"]] == [("mist-walker-rhw", "background")]
    assert "mist-walker-rhw" in res["sheet"]["grantedFeats"] if "grantedFeats" in res["sheet"] else True


def test_pick_of_a_non_dark_gift_feat_is_not_applied(catalog):
    res = resolve(_draft("spirit-medium-rhw", choices={SPIRIT: ["feat:alert-xphb"]}), catalog)
    assert res["sheet"]["feats"] == [] and _card(res, SPIRIT)["status"] == "pending"


def test_cascaded_choices_of_the_picked_feat_live_under_the_card_prefix(catalog):
    res = resolve(_draft("spirit-medium-rhw", choices={SPIRIT: ["feat:echoing-soul-rhw"]}), catalog)
    ids = {c["id"] for c in res["choices"]}
    assert any(i.startswith(f"{SPIRIT}:feat:echoing-soul-rhw:") for i in ids), sorted(ids)
    skill = next(c for c in res["choices"] if c["id"].startswith(f"{SPIRIT}:feat:echoing-soul-rhw:"))
    pick = skill["options"][0]["id"]
    res2 = resolve(_draft("spirit-medium-rhw", choices={SPIRIT: ["feat:echoing-soul-rhw"], skill["id"]: [pick]}), catalog)
    assert _card(res2, skill["id"])["status"] == "resolved"


def test_other_backgrounds_have_no_background_feat_card(catalog):
    res = resolve(_draft("acolyte-xphb"), catalog)
    assert not [c for c in res["choices"] if c["id"].startswith("background:") and ":feat-" in c["id"]]


# --- S2 duplicate map ------------------------------------------------------------------------------------------

def test_dark_gifts_are_outside_every_other_feat_pool(catalog):
    """A Dark Gift (category DG) is not an Origin / General / category-less feat, so the Human (XPHB) Origin feat card
    and the ASI pool never offer it: the background pick cannot be duplicated by those (nothing to disable)."""
    res = resolve(_draft("mist-wanderer-rhw", species="human-xphb", fighter=4, choices={MIST: ["feat:mist-walker-rhw"]}), catalog)
    species_card = _card(res, "species:human-xphb:feat-0")
    assert not any(o["id"] in {f"feat:{i}" for i in DG} for o in species_card["options"])
    asi = [c for c in res["choices"] if c["id"].startswith("class:fighter:") and any(o["id"].startswith("feat:") for o in c["options"])]
    assert asi and not any(o["id"] in {f"feat:{i}" for i in DG} for c in asi for o in c["options"])


def test_background_pick_is_in_the_taken_map_of_later_cards(catalog, monkeypatch):
    """The background card runs before the species card and joins `taken`: make the Human card's pool contain the
    picked Dark Gift (a patched pool) and it must read "already taken"."""
    import engine.resolve as r
    real = r._species_feat_pool

    def widened(cat, category, sources, ruleset="mixed", keep=()):
        return real(cat, category, sources, ruleset, keep) + ([cat.feats["mist-walker-rhw"]] if category == "O" else [])

    monkeypatch.setattr(r, "_species_feat_pool", widened)
    res = resolve(_draft("mist-wanderer-rhw", species="human-xphb", choices={MIST: ["feat:mist-walker-rhw"]}), catalog)
    opt = next(o for o in _card(res, "species:human-xphb:feat-0")["options"] if o["id"] == "feat:mist-walker-rhw")
    assert opt["disabled"] and opt["disabledReason"] == "already taken"


# --- sources / empty pool ---------------------------------------------------------------------------------------

def test_sources_without_the_book_make_the_card_unavailable_not_pending(catalog):
    res = resolve(_draft("mist-wanderer-rhw", sources=["srd", "xphb"]), catalog)
    card = _card(res, MIST)
    assert card["status"] == "unavailable" and card["unavailableReason"]


def test_hidden_pick_stays_applied_with_a_warning(catalog):
    res = resolve(_draft("mist-wanderer-rhw", sources=["srd", "xphb"], choices={MIST: ["feat:mist-walker-rhw"]}), catalog)
    assert [f["id"] for f in res["sheet"]["feats"]] == ["mist-walker-rhw"]
    assert any(w["id"] == f"feat-hidden-by-filters-{MIST}" for w in res["warnings"])


# --- unrelated records stay put ---------------------------------------------------------------------------------

@pytest.mark.parametrize("bid", ["haunted-one-rhw", "investigator-rhw"])
def test_alternative_backgrounds_keep_their_plain_grant_only(catalog, bid):
    bg = catalog.backgrounds[bid]
    assert len(bg["feats"]) == 1 and not bg.get("feat_grants")
    res = resolve(_draft(bid), catalog)
    assert len(res["sheet"]["feats"]) == 1


def test_mixed_and_2014_output_for_an_unrelated_background_is_unchanged(catalog):
    for rs in ("mixed", "2014"):
        res = resolve(_draft("acolyte", ruleset=rs), catalog)
        assert not [c for c in res["choices"] if ":feat-" in c["id"] and c["id"].startswith("background:")]
