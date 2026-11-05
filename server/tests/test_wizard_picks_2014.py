"""RP15 (E11b): SRD Wizard Spell Mastery (18) and Signature Spell (20) as pick cards under mixed and 2014.

Governing texts (catalog.features, srd ids; pinned verbatim below, read 2026-10-23):
  spell-mastery (Wizard 18): "Choose a 1st-level wizard spell and a 2nd-level wizard spell that are in your
    spellbook. You can cast those spells at their lowest level without expending a spell slot when you have them
    prepared." plus "By spending 8 hours in study, you can exchange one or both of the spells you chose".
  signature-spell (Wizard 20): "Choose two 3rd-level wizard spells in your spellbook as your signature spells. You
    always have these spells prepared, they don't count against the number of spells you have prepared, and you can
    cast each of them once at 3rd level without expending a spell slot. When you do so, you can't do so again until
    you finish a short or long rest."

Rule matrix (ruleset mixed and 2014 -> the SRD feature ids; 2024 keeps the C6d cards from the XPHB features):
  card ids (the SAME as 2024, so a pick survives a ruleset switch)
      class:wizard:18:spell-mastery-1 / -2 (one level 1 / one level 2 spell), class:wizard:20:signature-spells (two level 3)
  options            every book spell of the pick's level; NO casting-time condition in the SRD text (a reaction such
                     as Shield or Counterspell and a 1-minute spell such as Identify are all offered; 2024 requires
                     "a casting time of an action")
  Spell Mastery      NOT always prepared ("when you have them prepared"): not in alwaysPrepared, the prepared card
                     does not disable them; they list under sheet.spells[wizard].spellMastery
  Signature Spell    always prepared (alwaysPrepared, prepared-card option disabled "always prepared (Signature
                     Spells)"), under sheet.spells[wizard].signatureSpells, plus the resource `wizard:signature-spells`
                     (uses = picked spells, short-or-long, "once at 3rd level" note)
  sheet.features     rows "Spell Mastery" and "Signature Spell" (the SRD names) carry the picked spell names
  cascades           level-down, a pick that left the book, or too many picks -> non-blocking `pruned`; an empty book
                     or no eligible spell -> option-less card `unavailable` (never blocks export); the spellbook card
                     itself still blocks
  absent             below the class levels, for non-Wizards, in an SRD-only/empty catalog (no feature record), and the
                     2024 cards are untouched (test_class_spell_grants_2024.py)"""
from perf_helpers import assert_fast
import time

import pytest

from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

BOOK, PREPARED = "class:wizard:spellbook", "class:wizard:spells-known"
MASTERY1, MASTERY2 = "class:wizard:18:spell-mastery-1", "class:wizard:18:spell-mastery-2"
SIGNATURE = "class:wizard:20:signature-spells"

# SRD (2014) ids: Shield (reaction) / Magic Missile and Detect Magic (action) / Identify (1 minute) at level 1;
# Mirror Image and Web (action) / Misty Step (bonus action) at 2; Counterspell (reaction) / Fireball / Fly at 3.
BOOK_PICKS = ["shield", "magic-missile", "detect-magic", "identify", "mirror-image", "misty-step", "web",
              "counterspell", "fireball", "fly"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2014", sources=()):
    return resolve({
        "ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 16, "WIS": 14, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }, catalog)


def _wizard(level, extra=None, book=BOOK_PICKS):
    return ("wizard", level, {BOOK: list(book), **(extra or {})})


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _entry(res):
    return next((e for e in res["sheet"]["spells"] if e["classId"] == "wizard"), None)


def _always(res):
    entry = _entry(res)
    return [s["id"] for s in entry["alwaysPrepared"]] if entry else []


def _option(card, sid):
    return next((o for o in card["options"] if o["id"] == sid), None)


def _pruned(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


def _resource(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


RULESETS = pytest.mark.parametrize("ruleset", ["mixed", "2014"])


# ---- data pins ---------------------------------------------------------------------------------

def test_srd_feature_texts_are_what_the_rules_below_quote(catalog):
    mastery = " ".join(catalog.features["spell-mastery"]["desc"])
    assert "Choose a 1st-level wizard spell and a 2nd-level wizard spell that are in your spellbook" in mastery
    assert "without expending a spell slot when you have them prepared" in mastery
    assert "casting time" not in mastery  # the 2014 text has no casting-time condition
    signature = " ".join(catalog.features["signature-spell"]["desc"])
    assert "Choose two 3rd-level wizard spells in your spellbook" in signature
    assert "You always have these spells prepared, they don't count against the number of spells you have prepared" in signature
    assert "cast each of them once at 3rd level without expending a spell slot" in signature
    assert catalog.features["spell-mastery"]["level"] == 18 and catalog.features["signature-spell"]["level"] == 20


# ---- cards -------------------------------------------------------------------------------------

@RULESETS
def test_no_cards_below_the_class_levels(catalog, ruleset):
    res = _res(catalog, [_wizard(17)], ruleset)
    assert all(_card(res, cid) is None for cid in (MASTERY1, MASTERY2, SIGNATURE))
    assert "spellMastery" not in _entry(res) and "signatureSpells" not in _entry(res)
    res = _res(catalog, [_wizard(19)], ruleset)
    assert _card(res, MASTERY1) and _card(res, MASTERY2) and _card(res, SIGNATURE) is None
    assert "signatureSpells" not in _entry(res)


@RULESETS
def test_wizard_18_cards_offer_every_book_spell_of_the_level_with_no_casting_time_rule(catalog, ruleset):
    res = _res(catalog, [_wizard(18)], ruleset)
    one, two = _card(res, MASTERY1), _card(res, MASTERY2)
    assert one["count"] == 1 and two["count"] == 1 and one["status"] == two["status"] == "pending"
    assert one["source"] == {"kind": "class", "id": "wizard", "label": "Wizard", "level": 18}
    assert one["label"] == "Spell Mastery (level 1)" and two["label"] == "Spell Mastery (level 2)"
    # Shield is a reaction and Identify takes a minute: both are offered (2024 would exclude them).
    assert sorted(o["id"] for o in one["options"]) == ["detect-magic", "identify", "magic-missile", "shield"]
    assert sorted(o["id"] for o in two["options"]) == ["mirror-image", "misty-step", "web"]
    assert one["id"] in [c["id"] for c in res["choices"] if c["status"] == "pending"]


@RULESETS
def test_a_reaction_spell_is_accepted_for_spell_mastery(catalog, ruleset):
    res = _res(catalog, [_wizard(18, {MASTERY1: ["shield"]})], ruleset)
    assert _card(res, MASTERY1)["selected"] == ["shield"] and _card(res, MASTERY1)["status"] == "resolved"
    assert not _pruned(res, MASTERY1)


@RULESETS
def test_a_spell_outside_the_book_is_not_offered(catalog, ruleset):
    assert _option(_card(_res(catalog, [_wizard(18)], ruleset), MASTERY1), "mage-armor") is None


@RULESETS
def test_spell_mastery_picks_are_not_always_prepared(catalog, ruleset):
    picks = {MASTERY1: ["magic-missile"], MASTERY2: ["web"]}
    res = _res(catalog, [_wizard(18, picks)], ruleset)
    assert _always(res) == []  # "when you have them prepared": prepared normally
    assert _entry(res)["spellMastery"] == [{"id": "magic-missile", "name": "Magic Missile", "level": 1},
                                           {"id": "web", "name": "Web", "level": 2}]
    prepared = _card(res, PREPARED)
    for sid in ("magic-missile", "web"):
        assert _option(prepared, sid).get("disabled") is None


@RULESETS
def test_without_picks_the_sheet_key_is_an_empty_list(catalog, ruleset):
    assert _entry(_res(catalog, [_wizard(18)], ruleset))["spellMastery"] == []


@RULESETS
def test_wizard_20_signature_spells_are_two_level_3_book_spells_always_prepared(catalog, ruleset):
    res = _res(catalog, [_wizard(20)], ruleset)
    card = _card(res, SIGNATURE)
    assert card["count"] == 2 and card["status"] == "pending" and card["label"] == "Signature Spells"
    assert sorted(o["id"] for o in card["options"]) == ["counterspell", "fireball", "fly"]  # no casting-time rule
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball", "fly"]})], ruleset)
    assert _card(res, SIGNATURE)["status"] == "resolved"
    assert _always(res) == ["fireball", "fly"]
    assert _entry(res)["signatureSpells"] == [{"id": "fireball", "name": "Fireball", "level": 3},
                                              {"id": "fly", "name": "Fly", "level": 3}]
    prepared = _card(res, PREPARED)
    assert _option(prepared, "fireball")["disabledReason"] == "always prepared (Signature Spells)"
    assert _option(prepared, "counterspell").get("disabled") is None


@RULESETS
def test_signature_resource_counts_the_picked_spells(catalog, ruleset):
    assert _resource(_res(catalog, [_wizard(20)], ruleset), "wizard:signature-spells") is None
    r = _resource(_res(catalog, [_wizard(20, {SIGNATURE: ["fireball", "fly"]})], ruleset), "wizard:signature-spells")
    assert r["uses"] == 2 and r["recharge"] == "short-or-long" and r["classId"] == "wizard"
    assert "Fireball, Fly" in r["details"]["note"] and "once at 3rd level" in r["details"]["note"]
    r = _resource(_res(catalog, [_wizard(20, {SIGNATURE: ["fireball"]})], ruleset), "wizard:signature-spells")
    assert r["uses"] == 1
    assert _resource(_res(catalog, [_wizard(19, {SIGNATURE: ["fireball"]})], ruleset), "wizard:signature-spells") is None
    # Arcane Recovery is still there, first
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball"]})], ruleset)
    assert [r["id"] for r in res["derived"]["classResources"] if r["classId"] == "wizard"][:1] == ["wizard:arcane-recovery"]


@RULESETS
def test_sheet_features_rows_use_the_srd_feature_names(catalog, ruleset):
    picks = {MASTERY1: ["magic-missile"], MASTERY2: ["web"], SIGNATURE: ["fireball", "fly"]}
    res = _res(catalog, [_wizard(20, picks)], ruleset)
    rows = {f["name"]: f for f in res["sheet"]["features"] if f["source"]["kind"] == "class"}
    assert rows["Spell Mastery"]["choice"] == ["Magic Missile", "Web"]
    assert rows["Signature Spell"]["choice"] == ["Fireball", "Fly"]
    assert "Signature Spells" not in rows


# ---- cascades: prune, never block --------------------------------------------------------------

@RULESETS
def test_a_pick_that_leaves_the_book_is_pruned(catalog, ruleset):
    book_without = [s for s in BOOK_PICKS if s != "magic-missile"]
    res = _res(catalog, [_wizard(18, {MASTERY1: ["magic-missile"]}, book=book_without)], ruleset)
    assert _card(res, MASTERY1)["selected"] == [] and _card(res, MASTERY1)["status"] == "pending"
    assert _pruned(res, MASTERY1) and "Magic Missile" in _pruned(res, MASTERY1)[0]["reason"]
    assert not [p for p in res["problems"] if "mastery" in p["id"]]


@RULESETS
def test_level_down_prunes_the_picks_without_a_problem(catalog, ruleset):
    picks = {MASTERY1: ["magic-missile"], MASTERY2: ["web"], SIGNATURE: ["fireball", "fly"]}
    res = _res(catalog, [_wizard(17, picks)], ruleset)
    assert {p["choiceId"] for p in res["pruned"]} >= {MASTERY1, MASTERY2, SIGNATURE}
    assert not [p for p in res["problems"] if "mastery" in p["id"] or "signature" in p["id"]]
    res = _res(catalog, [_wizard(19, picks)], ruleset)
    assert _pruned(res, SIGNATURE) and not _pruned(res, MASTERY1)
    assert _resource(res, "wizard:signature-spells") is None and _always(res) == []


@RULESETS
def test_signature_spells_over_the_count_is_pruned_not_a_problem(catalog, ruleset):
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball", "fly", "counterspell"]})], ruleset)
    assert _card(res, SIGNATURE)["selected"] == ["fireball", "fly"]
    assert _pruned(res, SIGNATURE) and not [p for p in res["problems"] if "signature" in p["id"]]


@RULESETS
def test_removing_a_spell_from_the_book_drops_the_signature_pick_and_its_resource(catalog, ruleset):
    book_without = [s for s in BOOK_PICKS if s != "fireball"]
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball", "fly"]}, book=book_without)], ruleset)
    assert _card(res, SIGNATURE)["selected"] == ["fly"] and _pruned(res, SIGNATURE)
    assert _always(res) == ["fly"] and _resource(res, "wizard:signature-spells")["uses"] == 1
    assert _option(_card(res, PREPARED), "fireball") is None  # not in the book any more


@RULESETS
def test_empty_book_or_no_eligible_spell_gives_unavailable_cards_that_do_not_block_export(catalog, ruleset):
    from app import _pending_export_problems
    res = _res(catalog, [_wizard(20, book=[])], ruleset)
    for cid in (MASTERY1, MASTERY2, SIGNATURE):
        card = _card(res, cid)
        assert card["options"] == [] and card["status"] == "unavailable" and "spellbook" in card["description"].lower()
    ids = [p["id"] for p in _pending_export_problems(res)]
    assert not [i for i in ids if "spell-mastery" in i or "signature-spells" in i]
    assert f"unresolved-choice-{BOOK}" in ids  # the empty spellbook itself still blocks
    # no spell of the level in the book: unavailable too (a different description)
    res = _res(catalog, [_wizard(20, book=["shield"])], ruleset)
    assert _card(res, MASTERY2)["status"] == "unavailable" and _card(res, SIGNATURE)["status"] == "unavailable"
    assert _card(res, MASTERY1)["status"] == "pending"


@RULESETS
def test_a_card_with_options_is_pending_and_blocks_export(catalog, ruleset):
    from app import _pending_export_problems
    res = _res(catalog, [_wizard(18)], ruleset)
    assert f"unresolved-choice-{MASTERY1}" in [p["id"] for p in _pending_export_problems(res)]


# ---- scope -------------------------------------------------------------------------------------

def test_non_wizard_classes_with_the_wizard_list_get_no_cards(catalog):
    res = _res(catalog, [("fighter", 18, {}), ("rogue", 2, {})])
    assert all(c["id"] not in (MASTERY1, MASTERY2, SIGNATURE) for c in res["choices"])


def test_wizard_multiclass_uses_the_wizard_class_level(catalog):
    assert _card(_res(catalog, [("fighter", 2, {}), _wizard(18)]), MASTERY1) is not None
    assert _card(_res(catalog, [("fighter", 3, {}), _wizard(17)]), MASTERY1) is None


@needs_official
def test_2024_cards_keep_their_casting_time_rule_and_always_prepared_mastery(catalog):
    book = ["shield-xphb", "magic-missile-xphb", "detect-magic-xphb", "identify-xphb"]
    res = _res(catalog, [_wizard(18, {MASTERY1: ["magic-missile-xphb"]}, book=book)], "2024")
    assert sorted(o["id"] for o in _card(res, MASTERY1)["options"]) == ["detect-magic-xphb", "magic-missile-xphb"]
    assert _always(res) == ["magic-missile-xphb"]
    rows = {f["name"] for f in res["sheet"]["features"] if f["source"]["kind"] == "class"}
    assert "Spell Mastery" in rows and "Signature Spell" not in rows


@needs_official
def test_a_stored_pick_keeps_its_cid_across_a_ruleset_switch(catalog):
    picks = {MASTERY1: ["magic-missile"]}
    mixed = _res(catalog, [_wizard(18, picks)], "mixed")
    assert _card(mixed, MASTERY1)["selected"] == ["magic-missile"]
    # under 2024 the id belongs to the other edition's list: pruned, not blocking, and the same cid is the card
    to_2024 = _res(catalog, [_wizard(18, picks)], "2024")
    assert _card(to_2024, MASTERY1) is not None and not [p for p in to_2024["problems"] if "mastery" in p["id"]]


# ---- degrade, exports, timing ------------------------------------------------------------------

def test_cards_are_absent_without_the_srd_feature_records(catalog, monkeypatch):
    features = {k: v for k, v in catalog.features.items() if k not in ("spell-mastery", "signature-spell")}
    monkeypatch.setattr(catalog, "features", features)
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball", "fly"]})])
    assert all(_card(res, cid) is None for cid in (MASTERY1, MASTERY2, SIGNATURE))
    assert _resource(res, "wizard:signature-spells") is None
    assert "signatureSpells" not in _entry(res)


def _pdf_text(res):
    import io
    from pypdf import PdfReader
    from pdf_export import to_pdf
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(to_pdf(res))).pages)


def test_markdown_and_pdf_print_the_mastery_and_signature_lines_under_2014(catalog):
    from markdown_export import to_markdown
    picks = {MASTERY1: ["magic-missile"], MASTERY2: ["web"], SIGNATURE: ["fireball", "fly"]}
    res = _res(catalog, [_wizard(20, picks)])
    md, pdf = to_markdown(res), _pdf_text(res)
    assert "**Майсторство със заклинания (Spell Mastery):** Magic Missile (ниво 1), Web (ниво 2)" in md
    assert "**Запазени заклинания:** Fireball (ниво 3), Fly (ниво 3)" in md
    assert "Запазени заклинания: Fireball (ниво 3), Fly (ниво 3)" in pdf


def test_resolve_stays_fast(catalog):
    picks = {MASTERY1: ["magic-missile"], MASTERY2: ["web"], SIGNATURE: ["fireball", "fly"]}
    for ruleset in ("mixed", "2014"):
        _res(catalog, [_wizard(20, picks)], ruleset)
        laps = []
        for _ in range(10):
            t_run = time.perf_counter()
            _res(catalog, [_wizard(20, picks)], ruleset)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps, str(ruleset))
