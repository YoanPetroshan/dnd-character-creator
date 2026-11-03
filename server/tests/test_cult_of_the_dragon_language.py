"""RP3 (A1, open question 13): Cult of the Dragon Initiate (FRHoF) replacement language.

Governing sentence (catalog `feats["cult-of-the-dragon-initiate-frhof"]["entries"]`, Dragon's Tongue):
  "You know Draconic. If you already know Draconic when you select this feat, you instead learn one language of
   your choice from the language tables in the Player's Handbook or Chapter 2 of this book."

Rule matrix (card `<feat cid prefix>:languages`, count 1, options = PHB 2024 Standard + Rare, 19; known languages
disabled "already known"; the fixed Draconic stays on the sheet):
  Dragon Cultist (origin feat) + Dragonborn (fixed Draconic)  -> card, Draconic disabled
  Dragon Cultist + Human XPHB (no Draconic)                   -> no card
  Dragon Cultist + C8 origin card pick Draconic               -> no card for the origin feat (the feat's fixed
                                                                  Draconic wins; the origin card disables Draconic)
  Cult via Lessons of the First Ones (Warlock 2) after an origin Draconic pick -> card
  Same, origin pick removed                                   -> no card, stored pick pruned
  Mixed / 2014 with the feat: same behaviour (FE policy: the feat's own text under every ruleset)
  A stored pick of an already known language is dropped (pruned, card pending)
  SRD-only catalog: nothing (feat absent)."""
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from catalog.reference_data import FEAT_LANGUAGE_REPLACEMENT, LANGUAGES_2024_RARE, LANGUAGES_2024_STANDARD
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

FEAT = "cult-of-the-dragon-initiate-frhof"
BG_CARD = f"feat:{FEAT}:languages"
INV = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
LESSONS = "class:warlock:invocation:opt-lessons-of-the-first-ones-xphb:feat"
LESSONS_CARD = f"{LESSONS}:{FEAT}:languages"
POOL = {l["index"] for l in LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", species="human-xphb", background="dragon-cultist-frhof", bg_choices=None,
           species_choices=None):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}},
        "species": {"id": species, "choices": species_choices or {}},
        "background": {"id": background, "choices": bg_choices or {}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": dict(ch or {})} for c, lv, ch in classes],
    }


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _lessons_choices(extra=None):
    inv = {INV: ["opt-lessons-of-the-first-ones-xphb", "opt-devils-sight-xphb", "opt-armor-of-shadows-xphb"],
           LESSONS: [f"feat:{FEAT}"]}
    inv.update(extra or {})
    return inv


@needs_official
def test_quote_matches_catalog(catalog):
    text = " ".join(e for e in catalog.feats[FEAT]["entries"][1]["entries"])
    assert FEAT_LANGUAGE_REPLACEMENT[FEAT]["quote"] in text
    assert FEAT_LANGUAGE_REPLACEMENT[FEAT]["language"] == catalog.feats[FEAT]["languages"][0]["index"]


@needs_data
def test_dragonborn_gets_a_replacement_card_with_draconic_disabled(catalog):
    res = resolve(_draft([("fighter", 1, None)], species="dragonborn", ), catalog)
    card = _card(res, BG_CARD)
    assert card and card["count"] == 1 and card["status"] == "pending"
    assert {o["id"] for o in card["options"]} == POOL
    dr = next(o for o in card["options"] if o["id"] == "draconic")
    assert dr["disabled"] and dr["disabledReason"] == "already known"
    assert "draconic" in res["sheet"]["proficiencies"]["languages"]


@needs_data
def test_dragonborn_pick_is_added_and_known_options_disabled(catalog):
    res = resolve(_draft([("fighter", 1, None)], species="dragonborn", bg_choices={BG_CARD: ["elvish"]}), catalog)
    card = _card(res, BG_CARD)
    assert card["status"] == "resolved" and card["selected"] == ["elvish"]
    langs = res["sheet"]["proficiencies"]["languages"]
    assert "draconic" in langs and "elvish" in langs
    assert next(o for o in card["options"] if o["id"] == "common")["disabled"]  # Dragonborn knows Common


@needs_data
def test_stored_pick_of_draconic_is_dropped(catalog):
    res = resolve(_draft([("fighter", 1, None)], species="dragonborn", bg_choices={BG_CARD: ["draconic"]}), catalog)
    card = _card(res, BG_CARD)
    assert card["selected"] == [] and card["status"] == "pending"
    assert [p for p in res["pruned"] if p["choiceId"] == BG_CARD and "already known" in p["reason"]]


@needs_data
def test_human_xphb_has_no_card(catalog):
    res = resolve(_draft([("fighter", 1, None)]), catalog)
    assert _card(res, BG_CARD) is None
    assert "draconic" in res["sheet"]["proficiencies"]["languages"]


@needs_data
def test_stored_pick_without_a_card_is_pruned(catalog):
    res = resolve(_draft([("fighter", 1, None)], bg_choices={BG_CARD: ["elvish"]}), catalog)
    assert _card(res, BG_CARD) is None
    assert [p for p in res["pruned"] if p["choiceId"] == BG_CARD]
    assert "elvish" not in res["sheet"]["proficiencies"]["languages"]


@needs_data
def test_origin_card_pick_of_draconic_does_not_trigger_the_origin_feat_card(catalog):
    res = resolve(_draft([("fighter", 1, None)], bg_choices={"origin:languages": ["draconic", "elvish"]}), catalog)
    assert _card(res, BG_CARD) is None
    origin = _card(res, "origin:languages")
    assert next(o for o in origin["options"] if o["id"] == "draconic")["disabled"]


@needs_data
def test_lessons_feat_after_origin_draconic_pick_gets_card(catalog):
    d = _draft([("warlock", 2, _lessons_choices())], background="criminal-xphb",
               bg_choices={"origin:languages": ["draconic", "elvish"]})
    res = resolve(d, catalog)
    card = _card(res, LESSONS_CARD)
    assert card and card["count"] == 1
    assert next(o for o in card["options"] if o["id"] == "draconic")["disabled"]
    assert next(o for o in card["options"] if o["id"] == "elvish")["disabled"]
    assert not [p for p in res["pruned"] if p["choiceId"] == "origin:languages"]
    d["classes"][0]["choices"][LESSONS_CARD] = ["abyssal"]
    res2 = resolve(d, catalog)
    assert "abyssal" in res2["sheet"]["proficiencies"]["languages"]
    assert _card(res2, LESSONS_CARD)["status"] == "resolved"


@needs_data
def test_lessons_feat_without_earlier_draconic_has_no_card_and_prunes_pick(catalog):
    d = _draft([("warlock", 2, _lessons_choices({LESSONS_CARD: ["abyssal"]}))], background="criminal-xphb",
               bg_choices={"origin:languages": ["elvish", "dwarvish"]})
    res = resolve(d, catalog)
    assert _card(res, LESSONS_CARD) is None
    assert [p for p in res["pruned"] if p["choiceId"] == LESSONS_CARD]
    assert "abyssal" not in res["sheet"]["proficiencies"]["languages"]
    assert "draconic" in res["sheet"]["proficiencies"]["languages"]


@needs_data
def test_removing_the_earlier_source_drops_the_card(catalog):
    d = _draft([("warlock", 2, _lessons_choices({LESSONS_CARD: ["abyssal"]}))], background="criminal-xphb",
               bg_choices={"origin:languages": ["draconic", "elvish"]})
    assert _card(resolve(d, catalog), LESSONS_CARD)
    d["background"]["choices"]["origin:languages"] = ["elvish", "dwarvish"]
    res = resolve(d, catalog)
    assert _card(res, LESSONS_CARD) is None
    assert [p for p in res["pruned"] if p["choiceId"] == LESSONS_CARD]


@needs_data
def test_species_fixed_draconic_before_lessons_feat(catalog):
    d = _draft([("warlock", 2, _lessons_choices())], species="dragonborn", background="criminal-xphb")
    card = _card(resolve(d, catalog), LESSONS_CARD)
    assert card and next(o for o in card["options"] if o["id"] == "draconic")["disabled"]


@needs_data
def test_earlier_class_language_pick_counts(catalog):
    # Rogue 1 Thieves' Cant picks Draconic, then Warlock 2 takes the feat via Lessons: the card appears.
    thieves = "class:rogue:1:languages:xphb-rogue-1-thieves-cant"
    d = _draft([("rogue", 1, {thieves: ["draconic"]}), ("warlock", 2, _lessons_choices())], background="criminal-xphb")
    res = resolve(d, catalog)
    assert _card(res, LESSONS_CARD)
    assert _card(res, thieves)["selected"] == ["draconic"]


@needs_data
def test_later_class_language_pick_of_draconic_is_the_duplicate(catalog):
    thieves = "class:rogue:1:languages:xphb-rogue-1-thieves-cant"
    d = _draft([("warlock", 2, _lessons_choices()), ("rogue", 1, {thieves: ["draconic"]})], background="criminal-xphb")
    res = resolve(d, catalog)
    assert _card(res, LESSONS_CARD) is None
    assert _card(res, thieves)["selected"] == []


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_behave_the_same(catalog, ruleset):
    res = resolve(_draft([("fighter", 1, None)], ruleset=ruleset, species="dragonborn"), catalog)
    card = _card(res, BG_CARD)
    assert card and next(o for o in card["options"] if o["id"] == "draconic")["disabled"]
    res2 = resolve(_draft([("fighter", 1, None)], ruleset=ruleset, species="human"), catalog)
    assert _card(res2, BG_CARD) is None


@needs_data
def test_note_no_longer_says_add_it_by_hand(catalog):
    res = resolve(_draft([("fighter", 1, None)], species="dragonborn"), catalog)
    notes = " ".join(n for f in res["sheet"]["feats"] if f["id"] == FEAT for n in f.get("notes", []))
    assert "by hand" not in notes and "Dragon's Tongue" in notes


@needs_data
def test_output_unchanged_for_characters_without_the_feat(catalog):
    d = _draft([("fighter", 1, None)], background="criminal-xphb")
    assert not [c for c in resolve(d, catalog)["choices"] if c["id"].endswith(f"{FEAT}:languages")]


def test_srd_only_catalog_degrades(catalog):
    cat = copy.copy(catalog)
    cat.feats = {k: v for k, v in catalog.feats.items() if k != FEAT}
    res = resolve(_draft([("fighter", 1, None)], species="dragonborn"), cat)
    assert not [c for c in res["choices"] if FEAT in c["id"]]


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2024"])
def test_timing(catalog, ruleset):
    for cls in ("fighter", "wizard", "bard"):
        d = _draft([(cls, 20, None)], ruleset=ruleset, species="dragonborn")
        resolve(d, catalog)
        t = time.perf_counter()
        for _ in range(10):
            resolve(d, catalog)
        assert (time.perf_counter() - t) / 10 < 0.05


@needs_data
def test_species_origin_feat_alone_has_no_card_and_origin_pick_does_not_trigger_it(catalog):
    sp = "species:human-xphb:feat-0"
    d = _draft([("fighter", 1, None)], background="criminal-xphb", species_choices={sp: [f"feat:{FEAT}"]},
               bg_choices={"origin:languages": ["draconic", "elvish"]})
    res = resolve(d, catalog)
    assert not [c for c in res["choices"] if c["id"].endswith(f"{FEAT}:languages")]
    assert "draconic" in res["sheet"]["proficiencies"]["languages"]
    origin = _card(res, "origin:languages")
    assert next(o for o in origin["options"] if o["id"] == "draconic")["disabled"]
