"""C8: 2024 origin languages (Common + two Standard languages).

Rule (Player's Handbook 2024, ch. 2 "Choose Languages", read from the user's markdown on 2026-10-11):
  "Your character knows at least three languages: Common plus two languages you roll or choose from the
   Standard Languages table. ... Your class and other features might also give you languages."
Decision E10: Common is fixed, plus ONE card of 2 picks from the Standard table (Common excluded: 9 options).
Language grants of 2014 records used under 2024 (SRD Human's extra language, SRD race fixed languages) still
apply on top (no removal). Data check (2026-10-11): no 2024 species and no 2024 background record carries a
`languages` / `language_options` field, so the book text decides: the origin card is the only 2024 origin source
(Cult of the Dragon Initiate, FRHoF, is a fixed Draconic feat and just makes Draconic "already known").

Card: cid `origin:languages`, source kind `background` (BackgroundPage renders kind background|feat and not
`class:` / `species:`; the export gate counts every pending non-equipment card). Stored under background.choices.
Priority for "already known": fixed languages, then picks of species/feat/other background cards, then the origin
card, then class language cards (Thieves' Cant, Deft Explorer).

Matrix: ruleset (2024 / mixed / 2014) x background (acolyte 2014 / Criminal XPHB / none) x species (SRD Human with
its own extra language / XPHB Human) x stored picks (valid / duplicate of another card / not Standard / more than 2)
x class cards (Rogue Thieves' Cant, Ranger Deft Explorer) x export gate x exports x catalog (real / SRD-only) x
helper isolation x timing."""
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from catalog.reference_data import LANGUAGES_2024_STANDARD
from engine import class_choices_2024
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ORIGIN = "origin:languages"
THIEVES = "class:rogue:1:languages:xphb-rogue-1-thieves-cant"
DEFT = "class:ranger:2:languages:xphb-ranger-2-deft-explorer"
STANDARD_NO_COMMON = {l["index"] for l in LANGUAGES_2024_STANDARD} - {"common"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", background="criminal-xphb", species="human-xphb", bg_choices=None,
           species_choices=None):
    bg = {"id": background, "choices": bg_choices or {}} if background else {}
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}},
        "species": {"id": species, "choices": species_choices or {}}, "background": bg,
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _langs(res):
    return res["sheet"]["proficiencies"]["languages"]


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith("xphb-")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- the card -------------------------------------------------------------------------------

@needs_data
def test_2024_character_knows_common_and_gets_a_two_pick_standard_card(catalog):
    res = _res(catalog, [("rogue", 1, {})])
    assert "common" in _langs(res)
    card = _card(res, ORIGIN)
    assert card["count"] == 2 and card["status"] == "pending"
    assert card["source"] == {"kind": "background", "id": "criminal-xphb", "label": card["source"]["label"]}
    assert {o["id"] for o in card["options"]} == STANDARD_NO_COMMON and len(card["options"]) == 9
    assert all(not o.get("disabled") for o in card["options"])
    assert "Common plus two languages" in card["description"] or "two languages" in card["description"]


@needs_data
def test_picks_land_in_languages_and_resolve_the_card(catalog):
    res = _res(catalog, [("rogue", 1, {})], bg_choices={ORIGIN: ["dwarvish", "orc"]})
    card = _card(res, ORIGIN)
    assert card["status"] == "resolved" and card["selected"] == ["dwarvish", "orc"]
    assert {"common", "dwarvish", "orc"} <= set(_langs(res))


@needs_data
def test_pending_origin_card_blocks_export_until_picked(catalog):
    import app as app_module
    res = _res(catalog, [("fighter", 1, {})])
    ids = {p["id"] for p in app_module._pending_export_problems(res)}
    assert f"unresolved-choice-{ORIGIN}" in ids
    res = _res(catalog, [("fighter", 1, {})], bg_choices={ORIGIN: ["dwarvish", "orc"]})
    assert f"unresolved-choice-{ORIGIN}" not in {p["id"] for p in app_module._pending_export_problems(res)}


@needs_data
def test_works_with_2014_background_and_species_records_and_stacks_on_their_grants(catalog):
    """SRD Human (2014 record) still fixes Common and offers its own extra-language card; both stay, on top."""
    res = _res(catalog, [("fighter", 1, {})], background="acolyte", species="human",
               bg_choices={ORIGIN: ["dwarvish", "orc"]}, species_choices={"species:human:languages": ["elvish"]})
    assert {"common", "dwarvish", "orc", "elvish"} <= set(_langs(res))
    assert _card(res, ORIGIN)["source"]["id"] == "acolyte"
    assert _card(res, "species:human:languages") is not None


@needs_data
def test_no_background_no_card_but_common_is_still_known(catalog):
    res = _res(catalog, [("fighter", 1, {})], background=None)
    assert _card(res, ORIGIN) is None
    assert "common" in _langs(res)


# ---- already known ----------------------------------------------------------------------------

@needs_data
def test_origin_card_yields_to_other_background_species_feat_picks(catalog):
    """SRD Human's extra language card (species kind) has priority; the same id on the origin card is disabled."""
    res = _res(catalog, [("fighter", 1, {})], background="acolyte", species="human",
               species_choices={"species:human:languages": ["elvish"]}, bg_choices={ORIGIN: ["elvish", "orc"]})
    card = _card(res, ORIGIN)
    assert _opt(card, "elvish")["disabledReason"] == "already known"
    assert card["selected"] == ["orc"] and card["status"] == "pending"
    assert ORIGIN in {p["choiceId"] for p in res["pruned"]}


@needs_data
def test_fixed_feat_language_is_disabled_on_the_origin_card(catalog):
    """Dragon Cultist (FRHoF) grants the Cult of the Dragon Initiate feat, which fixes Draconic."""
    res = _res(catalog, [("fighter", 1, {})], background="dragon-cultist-frhof")
    assert "draconic" in _langs(res)
    assert _opt(_card(res, ORIGIN), "draconic")["disabledReason"] == "already known"


@needs_data
def test_class_language_cards_yield_to_the_origin_card(catalog):
    """Rogue Thieves' Cant (class) walks after the origin card: a language chosen at origin is disabled there."""
    res = _res(catalog, [("rogue", 1, {THIEVES: ["dwarvish"]})],
               bg_choices={ORIGIN: ["dwarvish", "orc"]})
    t = _card(res, THIEVES)
    assert _opt(t, "dwarvish")["disabledReason"] == "already known"
    assert _opt(t, "common")["disabledReason"] == "already known"  # Common is now fixed under 2024
    assert t["selected"] == [] and t["status"] == "pending"
    assert THIEVES in {p["choiceId"] for p in res["pruned"]}
    assert _card(res, ORIGIN)["selected"] == ["dwarvish", "orc"]


@needs_data
def test_ranger_deft_explorer_sees_origin_picks_and_common(catalog):
    res = _res(catalog, [("ranger", 2, {})], bg_choices={ORIGIN: ["elvish", "giant"]})
    d = _card(res, DEFT)
    assert _opt(d, "common")["disabledReason"] == "already known"
    assert _opt(d, "elvish")["disabledReason"] == "already known"
    assert _opt(d, "giant")["disabledReason"] == "already known"
    assert _opt(d, "draconic").get("disabled") is None


# ---- stored picks -----------------------------------------------------------------------------

@needs_data
def test_non_standard_and_extra_picks_are_ignored(catalog):
    res = _res(catalog, [("fighter", 1, {})], bg_choices={ORIGIN: ["infernal", "dwarvish"]})
    card = _card(res, ORIGIN)  # Infernal is Rare, not on the Standard card
    assert card["selected"] == ["dwarvish"] and card["status"] == "pending"
    assert "infernal" not in _langs(res)
    res = _res(catalog, [("fighter", 1, {})], bg_choices={ORIGIN: ["common"]})
    assert _card(res, ORIGIN)["selected"] == []


@needs_data
def test_stored_picks_fall_into_pruned_when_the_origin_card_goes_away(catalog):
    res = _res(catalog, [("fighter", 1, {})], ruleset="mixed", background="acolyte", species="human",
               bg_choices={ORIGIN: ["dwarvish", "orc"]})
    assert ORIGIN in {p["choiceId"] for p in res["pruned"]}


# ---- other rulesets unchanged -------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_have_no_origin_card_and_no_forced_common(catalog, ruleset):
    res = _res(catalog, [("fighter", 1, {})], ruleset=ruleset, background="acolyte", species="elf")
    assert _card(res, ORIGIN) is None
    assert "common" in _langs(res)  # from the SRD Elf record itself, as before
    res = _res(catalog, [("fighter", 1, {})], ruleset=ruleset, background="criminal-phb", species="elf-phb")
    assert _card(res, ORIGIN) is None


# ---- exports ------------------------------------------------------------------------------------

@needs_data
def test_markdown_prints_the_origin_languages(catalog):
    from markdown_export import to_markdown
    res = _res(catalog, [("fighter", 1, {})], bg_choices={ORIGIN: ["common-sign-language", "orc"]})
    md = to_markdown(res)
    assert "Common Sign Language" in md and "Orc" in md and "Common" in md


# ---- degrade / helpers -----------------------------------------------------------------------------

@needs_data
def test_srd_only_catalog_does_not_crash_and_keeps_the_book_rule(catalog):
    """Languages are reference data, not catalog records: under 2024 the rule applies without XPHB data."""
    bare = _srd_only(catalog)
    res = _res(bare, [("fighter", 1, {})], background="acolyte", species="human")
    assert "common" in _langs(res)
    assert _card(res, ORIGIN)["count"] == 2


def test_helpers_are_ruleset_isolated():
    bg = {"name": "Criminal"}
    assert class_choices_2024.fixed_origin_languages("2024") == ["common"]
    assert class_choices_2024.fixed_origin_languages("mixed") == []
    assert class_choices_2024.fixed_origin_languages("2014") == []
    assert class_choices_2024.origin_language_templates(bg, "criminal-xphb", "mixed") == []
    assert class_choices_2024.origin_language_templates(bg, "criminal-xphb", "2014") == []
    assert class_choices_2024.origin_language_templates(None, "", "2024") == []
    (tpl,) = class_choices_2024.origin_language_templates(bg, "criminal-xphb", "2024")
    assert tpl["id"] == ORIGIN and tpl["count"] == 2 and len(tpl["options"]) == 9


def test_gate_without_any_language_card_is_a_noop():
    choices = [{"id": "x", "source": {"kind": "class", "id": "fighter"}, "options": [], "selected": [], "count": 1}]
    assert class_choices_2024.gate_languages(choices, ["common"], ["fighter"]) == []


# ---- timing ----------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["2024", "mixed"])
def test_resolve_stays_fast(catalog, ruleset):
    draft = _draft([("rogue", 1, {})], ruleset=ruleset, background="acolyte", species="human")
    resolve(draft, catalog)
    t0 = time.perf_counter()
    for _ in range(20):
        resolve(draft, catalog)
    assert (time.perf_counter() - t0) / 20 < 0.05
