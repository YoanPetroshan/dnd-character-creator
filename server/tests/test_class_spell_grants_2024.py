"""C6d: 2024 class spell grants - always prepared class spells, Bard Magical Secrets, Wizard Spell
Mastery and Signature Spells.

Rules (XPHB class data and feature texts, read from the catalog on 2026-10-10):
  XPHB `additionalSpells` of the class records (always prepared from that class level):
    Bard 20 Power Word Heal + Power Word Kill ("You therefore always have the Power Word Heal and Power
         Word Kill spells prepared")
    Druid 1 Speak with Animals (Druidic: "you always have the Speak with Animals spell prepared").
         Druid 2 Find Familiar is NOT granted (decision E9): Wild Companion only lets you cast it "As a
         Magic action, you can expend a spell slot or a use of Wild Shape"; the spell is not prepared.
    Paladin 2 Divine Smite (Paladin's Smite: "You always have the Divine Smite spell prepared"),
         Paladin 5 Find Steed (Faithful Steed)
    Ranger 1 Hunter's Mark (Favored Enemy), Warlock 9 Contact Other Plane (Contact Patron)
  Magical Secrets (Bard 10): "you can choose any of your new prepared spells from the Bard, Cleric,
    Druid, and Wizard spell lists, and the chosen spells count as Bard spells for you". XPHB expanded:
    class level 10 -> spell levels 1-5, keys s6..s9 -> spell slot level 6..9 (all of Cleric/Druid/Wizard).
  Spell Mastery (Wizard 18): "Choose a level 1 and a level 2 spell in your spellbook that have a casting
    time of an action. You always have those spells prepared".
  Signature Spells (Wizard 20): "Choose two level 3 spells in your spellbook as your signature spells.
    You always have these spells prepared".

Matrix: class (Bard, Druid, Paladin, Ranger, Warlock, Wizard) x class level (just below / at the grant level)
x ruleset (2024 / mixed / 2014) x multiclass (class level, not total level) x prepared card (option disabled
"always prepared (<Class>)") x subclass spells merged x Magical Secrets (levels 9/10/11/17, Bard list vs other
lists, label, stored pick, slot level cap, sources srd, mixed) x Spell Mastery (card ids, counts, book filter
"1 action", reaction excluded, empty book, level-down pruned, stale pick pruned, picks always prepared and
disabled in the prepared card, sheet keys) x Signature Spells (count 2, level 3 only) x sheet.features row x
Markdown/PDF lines x catalog (real / SRD-only) x timing."""
import time

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

BOOK, PREPARED = "class:wizard:spellbook", "class:wizard:spells-known"
MASTERY1, MASTERY2 = "class:wizard:18:spell-mastery-1", "class:wizard:18:spell-mastery-2"
SIGNATURE = "class:wizard:20:signature-spells"
BARD_KNOWN = "class:bard:spells-known"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", sources=(), subclasses=None):
    subclasses = subclasses or {}
    return resolve({
        "ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 16, "WIS": 14, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch, **({"subclassId": subclasses[c]} if c in subclasses else {})}
                    for c, lv, ch in classes],
    }, catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _sheet_spells(res, cls):
    return next((e for e in res["sheet"]["spells"] if e["classId"] == cls), None)


def _always(res, cls):
    entry = _sheet_spells(res, cls)
    return [s["id"] for s in entry["alwaysPrepared"]] if entry else []


def _option(card, sid):
    return next((o for o in card["options"] if o["id"] == sid), None)


def _pruned(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


# ---- data -------------------------------------------------------------------------------------

@needs_data
def test_loader_keeps_the_raw_additional_spells_of_the_class_records(catalog):
    assert set(catalog.class_2024_records["ranger"]["additional_spells"][0]["prepared"]) == {"1"}
    assert catalog.class_2024_records["fighter"]["additional_spells"] == []


@needs_data
def test_class_spell_grants_always_are_resolved_to_xphb_ids_and_druid_skips_find_familiar(catalog):
    always = {cls: g["always"] for cls, g in catalog.class_2024_spell_grants.items()}
    assert always == {
        "bard": {20: ["power-word-heal-xphb", "power-word-kill-xphb"]},
        "druid": {1: ["speak-with-animals-xphb"]},  # E9: Find Familiar (level 2) is not always prepared
        "paladin": {2: ["divine-smite-xphb"], 5: ["find-steed-xphb"]},
        "ranger": {1: ["hunters-mark-xphb"]},
        "warlock": {9: ["contact-other-plane-xphb"]},
    }


@needs_data
def test_class_spell_grants_expanded_is_bards_magical_secrets(catalog):
    expanded = catalog.class_2024_spell_grants["bard"]["expanded"]
    assert set(expanded) == {"10", "s6", "s7", "s8", "s9"}
    assert expanded["10"] == {"level": [1, 2, 3, 4, 5], "class": ["cleric", "druid", "wizard"]}
    assert expanded["s9"] == {"level": [9], "class": ["cleric", "druid", "wizard"]}


# ---- always prepared class spells -----------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cls,level,present,absent", [
    ("ranger", 1, ["hunters-mark-xphb"], []),
    ("paladin", 1, [], ["divine-smite-xphb", "find-steed-xphb"]),
    ("paladin", 2, ["divine-smite-xphb"], ["find-steed-xphb"]),
    ("paladin", 4, ["divine-smite-xphb"], ["find-steed-xphb"]),
    ("paladin", 5, ["divine-smite-xphb", "find-steed-xphb"], []),
    ("druid", 1, ["speak-with-animals-xphb"], []),
    ("druid", 2, ["speak-with-animals-xphb"], ["find-familiar-xphb", "find-familiar"]),
    ("warlock", 8, [], ["contact-other-plane-xphb"]),
    ("warlock", 9, ["contact-other-plane-xphb"], []),
    ("bard", 19, [], ["power-word-heal-xphb", "power-word-kill-xphb"]),
    ("bard", 20, ["power-word-heal-xphb", "power-word-kill-xphb"], []),
])
def test_class_spells_are_always_prepared_from_their_class_level(catalog, cls, level, present, absent):
    always = _always(_res(catalog, [(cls, level, {})]), cls)
    for sid in present:
        assert sid in always
    for sid in absent:
        assert sid not in always


@needs_data
def test_always_prepared_spell_is_disabled_in_the_prepared_card_with_the_class_as_reason(catalog):
    res = _res(catalog, [("ranger", 1, {})])
    option = _option(_card(res, "class:ranger:spells-known"), "hunters-mark-xphb")
    assert option["disabled"] is True and option["disabledReason"] == "always prepared (Ranger)"
    assert _option(_card(res, "class:ranger:spells-known"), "cure-wounds-xphb").get("disabled") is None


@needs_data
def test_a_stored_pick_of_an_always_prepared_spell_is_dropped_not_counted(catalog):
    res = _res(catalog, [("ranger", 1, {"class:ranger:spells-known": ["hunters-mark-xphb", "cure-wounds-xphb"]})])
    card = _card(res, "class:ranger:spells-known")
    assert card["selected"] == ["cure-wounds-xphb"] and card["status"] == "pending"


@needs_data
def test_druid_find_familiar_is_still_a_normal_option_and_not_disabled(catalog):
    card = _card(_res(catalog, [("druid", 2, {})]), "class:druid:spells-known")
    option = _option(card, "find-familiar-xphb")
    assert option is None or option.get("disabled") is None  # not on the Druid list; never "always prepared"


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_class_spell_grants_outside_2024(catalog, ruleset):
    for cls, level in (("ranger", 5), ("paladin", 5), ("druid", 2), ("warlock", 9), ("bard", 20)):
        res = _res(catalog, [(cls, level, {})], ruleset=ruleset)
        assert _always(res, cls) == []
        entry = _sheet_spells(res, cls)
        assert entry is None or entry["alwaysPrepared"] == []


@needs_data
def test_multiclass_grants_follow_the_class_level_not_the_total_level(catalog):
    res = _res(catalog, [("paladin", 1, {}), ("ranger", 5, {})])
    assert _always(res, "paladin") == []  # Paladin 1: no Divine Smite until Paladin 2
    assert _always(res, "ranger") == ["hunters-mark-xphb"]
    res = _res(catalog, [("paladin", 2, {}), ("ranger", 1, {})])
    assert _always(res, "paladin") == ["divine-smite-xphb"]
    assert _always(res, "ranger") == ["hunters-mark-xphb"]


@needs_data
def test_class_grants_are_merged_with_the_subclass_spells(catalog):
    res = _res(catalog, [("paladin", 3, {})], subclasses={"paladin": "devotion"})
    always = _always(res, "paladin")
    assert "divine-smite-xphb" in always and len(always) > 1  # Oath of Devotion spells + Divine Smite
    assert len(always) == len(set(always))


@needs_data
def test_always_prepared_spells_reach_the_exports(catalog):
    from markdown_export import to_markdown
    text = to_markdown(_res(catalog, [("ranger", 1, {})]))
    assert "Винаги подготвени заклинания" in text and "Hunter's Mark (ниво 1)" in text


# ---- Magical Secrets --------------------------------------------------------------------------

@needs_data
def test_bard_10_offers_cleric_druid_and_wizard_spells_labelled_magical_secrets(catalog):
    card = _card(_res(catalog, [("bard", 10, {})]), BARD_KNOWN)
    fireball = _option(card, "fireball-xphb")  # Wizard list
    assert fireball and fireball["label"] == "Fireball (Magical Secrets)" and fireball["group"] == "spell-level-3"
    assert _option(card, "spiritual-weapon-xphb")["label"] == "Spiritual Weapon (Magical Secrets)"  # Cleric list
    assert _option(card, "cure-wounds-xphb")["label"] == "Cure Wounds"  # already a Bard spell: no label
    assert _option(card, "disintegrate-xphb") is None  # level 6: needs a 6th-level slot (Bard 11)


@needs_data
def test_bard_9_does_not_offer_magical_secrets(catalog):
    card = _card(_res(catalog, [("bard", 9, {})]), BARD_KNOWN)
    assert _option(card, "fireball-xphb") is None and _option(card, "spiritual-weapon-xphb") is None


@needs_data
@pytest.mark.parametrize("level,sid,offered", [
    (10, "disintegrate-xphb", False), (11, "disintegrate-xphb", True),
    (16, "wish-xphb", False), (17, "wish-xphb", True)])
def test_magical_secrets_follows_the_highest_spell_slot_level(catalog, level, sid, offered):
    card = _card(_res(catalog, [("bard", level, {})]), BARD_KNOWN)
    assert (_option(card, sid) is not None) is offered


@needs_data
def test_a_magical_secrets_pick_resolves_into_the_sheet_and_is_pruned_below_level_10(catalog):
    picks = {BARD_KNOWN: ["fireball-xphb"]}
    res = _res(catalog, [("bard", 10, picks)])
    assert "fireball-xphb" in [s["id"] for s in _sheet_spells(res, "bard")["known"]]
    res = _res(catalog, [("bard", 9, picks)])
    assert "fireball-xphb" not in [s["id"] for s in _sheet_spells(res, "bard")["known"]]
    assert _pruned(res, BARD_KNOWN) and "Fireball" in _pruned(res, BARD_KNOWN)[0]["reason"]


@needs_data
def test_magical_secrets_xphb_grants_are_2024_only_and_bard_only(catalog):
    # RP16: mixed / 2014 now have the SRD Magical Secrets (test_magical_secrets_2014.py, SRD ids, cap, cantrips);
    # what stays 2024-only is the XPHB grant: no XPHB spell id is offered outside 2024, and non-Bards never get it.
    for ruleset in ("mixed", "2014"):
        card = _card(_res(catalog, [("bard", 11, {})], ruleset=ruleset), BARD_KNOWN)
        assert _option(card, "spiritual-weapon-xphb") is None
        assert _option(card, "spiritual-weapon")["label"] == "Spiritual Weapon (Magical Secrets)"
    card = _card(_res(catalog, [("cleric", 11, {})]), "class:cleric:spells-known")
    assert all("Magical Secrets" not in o["label"] for o in card["options"])


@needs_data
def test_magical_secrets_respects_the_source_filter(catalog):
    # sources ["srd"] hides the XPHB records: the SRD (2014 id) spells are offered instead, same label.
    card = _card(_res(catalog, [("bard", 10, {})], sources=["srd"]), BARD_KNOWN)
    assert _option(card, "fireball")["label"] == "Fireball (Magical Secrets)"
    assert _option(card, "fireball-xphb") is None
    ranger = _card(_res(catalog, [("ranger", 1, {})], sources=["srd"]), "class:ranger:spells-known")
    assert _option(ranger, "hunters-mark")["disabled"] is True  # the twin of the granted hunters-mark-xphb


# ---- Spell Mastery / Signature Spells --------------------------------------------------------

BOOK_PICKS = ["shield-xphb", "magic-missile-xphb", "detect-magic-xphb", "identify-xphb", "mirror-image-xphb",
              "misty-step-xphb", "web-xphb", "counterspell-xphb", "fireball-xphb", "fly-xphb"]


def _wizard(level, extra=None, book=BOOK_PICKS):
    return ("wizard", level, {BOOK: list(book), **(extra or {})})


@needs_data
def test_no_mastery_or_signature_cards_below_the_levels(catalog):
    res = _res(catalog, [_wizard(17)])
    assert all(_card(res, cid) is None for cid in (MASTERY1, MASTERY2, SIGNATURE))
    assert "spellMastery" not in _sheet_spells(res, "wizard") and "signatureSpells" not in _sheet_spells(res, "wizard")
    res = _res(catalog, [_wizard(19)])
    assert _card(res, MASTERY1) and _card(res, MASTERY2) and _card(res, SIGNATURE) is None
    assert "signatureSpells" not in _sheet_spells(res, "wizard")


@needs_data
def test_wizard_18_cards_are_single_picks_from_the_book_spells_with_an_action_casting_time(catalog):
    res = _res(catalog, [_wizard(18)])
    one, two = _card(res, MASTERY1), _card(res, MASTERY2)
    assert one["count"] == 1 and two["count"] == 1 and one["status"] == two["status"] == "pending"
    assert one["source"] == {"kind": "class", "id": "wizard", "label": "Wizard", "level": 18}
    # Shield is a reaction, Identify takes a minute: neither is offered. Detect Magic (action) is.
    assert sorted(o["id"] for o in one["options"]) == ["detect-magic-xphb", "magic-missile-xphb"]
    # Misty Step is a bonus action: not offered. Mirror Image and Web (actions) are.
    assert sorted(o["id"] for o in two["options"]) == ["mirror-image-xphb", "web-xphb"]
    assert one["label"] == "Spell Mastery (level 1)" and two["label"] == "Spell Mastery (level 2)"
    assert one["id"] in [c["id"] for c in res["choices"] if c["status"] == "pending"]


@needs_data
def test_a_spell_outside_the_book_is_not_offered(catalog):
    card = _card(_res(catalog, [_wizard(18)]), MASTERY1)
    assert _option(card, "mage-armor-xphb") is None  # an action Wizard spell that is not in this book


@needs_data
def test_mastery_picks_are_always_prepared_disabled_in_the_prepared_card_and_on_the_sheet(catalog):
    picks = {MASTERY1: ["magic-missile-xphb"], MASTERY2: ["web-xphb"]}
    res = _res(catalog, [_wizard(18, picks)])
    assert _card(res, MASTERY1)["status"] == "resolved"
    assert _always(res, "wizard") == ["magic-missile-xphb", "web-xphb"]
    entry = _sheet_spells(res, "wizard")
    assert entry["spellMastery"] == [{"id": "magic-missile-xphb", "name": "Magic Missile", "level": 1},
                                     {"id": "web-xphb", "name": "Web", "level": 2}]
    prepared = _card(res, PREPARED)
    for sid in ("magic-missile-xphb", "web-xphb"):
        option = _option(prepared, sid)
        assert option["disabled"] is True and option["disabledReason"] == "always prepared (Spell Mastery)"
    assert _option(prepared, "detect-magic-xphb").get("disabled") is None


@needs_data
def test_without_picks_the_sheet_key_is_an_empty_list(catalog):
    assert _sheet_spells(_res(catalog, [_wizard(18)]), "wizard")["spellMastery"] == []


@needs_data
def test_empty_book_gives_option_less_unavailable_mastery_cards(catalog):
    # F3a-2b: an option-less new 2024 card is "unavailable" (non-blocking); the empty spellbook card still blocks
    res = _res(catalog, [_wizard(18, book=[])])
    for cid in (MASTERY1, MASTERY2):
        card = _card(res, cid)
        assert card["options"] == [] and card["status"] == "unavailable" and "spellbook" in card["description"].lower()


@needs_data
def test_a_pick_that_leaves_the_book_is_pruned(catalog):
    picks = {MASTERY1: ["magic-missile-xphb"]}
    book_without = [s for s in BOOK_PICKS if s != "magic-missile-xphb"]
    res = _res(catalog, [_wizard(18, picks, book=book_without)])
    card = _card(res, MASTERY1)
    assert card["selected"] == [] and card["status"] == "pending"
    assert _pruned(res, MASTERY1) and "Magic Missile" in _pruned(res, MASTERY1)[0]["reason"]
    assert _always(res, "wizard") == []


@needs_data
def test_a_stored_reaction_spell_is_not_accepted_for_mastery(catalog):
    res = _res(catalog, [_wizard(18, {MASTERY1: ["shield-xphb"]})])
    assert _card(res, MASTERY1)["selected"] == [] and _pruned(res, MASTERY1)
    assert "shield-xphb" not in _always(res, "wizard")


@needs_data
def test_level_down_below_18_prunes_the_mastery_picks_without_a_problem(catalog):
    picks = {MASTERY1: ["magic-missile-xphb"], MASTERY2: ["web-xphb"]}
    res = _res(catalog, [_wizard(17, picks)])
    assert {p["choiceId"] for p in res["pruned"]} >= {MASTERY1, MASTERY2}
    assert not [p for p in res["problems"] if "mastery" in p["id"]]
    assert _always(res, "wizard") == []


@needs_data
def test_wizard_20_signature_spells_are_two_level_3_book_spells_always_prepared(catalog):
    res = _res(catalog, [_wizard(20)])
    card = _card(res, SIGNATURE)
    assert card["count"] == 2 and card["status"] == "pending" and card["label"] == "Signature Spells"
    # Counterspell is a reaction but Signature Spells has no casting time condition: every level 3 book spell.
    assert sorted(o["id"] for o in card["options"]) == ["counterspell-xphb", "fireball-xphb", "fly-xphb"]
    res = _res(catalog, [_wizard(20, {SIGNATURE: ["fireball-xphb", "fly-xphb"]})])
    assert _card(res, SIGNATURE)["status"] == "resolved"
    assert _always(res, "wizard") == ["fireball-xphb", "fly-xphb"]
    assert _sheet_spells(res, "wizard")["signatureSpells"] == [
        {"id": "fireball-xphb", "name": "Fireball", "level": 3}, {"id": "fly-xphb", "name": "Fly", "level": 3}]
    prepared = _card(res, PREPARED)
    assert _option(prepared, "fireball-xphb")["disabledReason"] == "always prepared (Signature Spells)"
    assert _option(prepared, "counterspell-xphb").get("disabled") is None


@needs_data
def test_signature_spells_over_the_count_is_pruned_not_a_problem(catalog):
    picks = {SIGNATURE: ["fireball-xphb", "fly-xphb", "counterspell-xphb"]}
    res = _res(catalog, [_wizard(20, picks)])
    assert _card(res, SIGNATURE)["selected"] == ["fireball-xphb", "fly-xphb"]
    assert _pruned(res, SIGNATURE) and not [p for p in res["problems"] if "signature" in p["id"]]


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_outside_2024_the_cards_are_the_srd_ones_with_the_same_cids(catalog, ruleset):
    # RP15 (E11b) reversed the C6d "2024 only" rule: the SRD Spell Mastery / Signature Spell use the same cids but
    # no casting-time condition (tests/test_wizard_picks_2014.py). A book without an eligible spell gives
    # option-less cards (here the 2014 id "fireball" is level 3 only).
    res = _res(catalog, [("wizard", 20, {BOOK: ["fireball"]})], ruleset=ruleset)
    assert _card(res, MASTERY1)["options"] == [] and _card(res, MASTERY2)["options"] == []
    assert [o["id"] for o in _card(res, SIGNATURE)["options"]] == ["fireball"]
    entry = _sheet_spells(res, "wizard")
    assert entry["spellMastery"] == [] and entry["signatureSpells"] == []


@needs_data
def test_non_wizard_classes_with_the_wizard_list_get_no_mastery_cards(catalog):
    res = _res(catalog, [("fighter", 18, {}), ("rogue", 2, {})], subclasses={"fighter": "eldritch-knight"})
    assert all(c["id"] not in (MASTERY1, MASTERY2, SIGNATURE) for c in res["choices"])


@needs_data
def test_wizard_multiclass_uses_the_wizard_class_level(catalog):
    res = _res(catalog, [("fighter", 2, {}), _wizard(18)])
    assert _card(res, MASTERY1) is not None
    res = _res(catalog, [("fighter", 3, {}), _wizard(17)])
    assert _card(res, MASTERY1) is None


@needs_data
def test_sheet_features_rows_carry_the_mastery_and_signature_picks(catalog):
    picks = {MASTERY1: ["magic-missile-xphb"], MASTERY2: ["web-xphb"], SIGNATURE: ["fireball-xphb", "fly-xphb"]}
    res = _res(catalog, [_wizard(20, picks)])
    rows = {f["name"]: f for f in res["sheet"]["features"] if f["source"]["kind"] == "class"}
    assert rows["Spell Mastery"]["choice"] == ["Magic Missile", "Web"]
    assert rows["Signature Spells"]["choice"] == ["Fireball", "Fly"]


# ---- exports ----------------------------------------------------------------------------------

def _pdf_text(res):
    import io
    from pypdf import PdfReader
    from pdf_export import to_pdf
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(to_pdf(res))).pages)


@needs_data
def test_markdown_and_pdf_print_the_mastery_and_signature_lines(catalog):
    from markdown_export import to_markdown
    picks = {MASTERY1: ["magic-missile-xphb"], MASTERY2: ["web-xphb"], SIGNATURE: ["fireball-xphb", "fly-xphb"]}
    res = _res(catalog, [_wizard(20, picks)])
    md, pdf = to_markdown(res), _pdf_text(res)
    assert "**Майсторство със заклинания:** Magic Missile (ниво 1), Web (ниво 2)" in md
    assert "**Запазени заклинания:** Fireball (ниво 3), Fly (ниво 3)" in md
    assert "Майсторство със заклинания: Magic Missile (ниво 1), Web (ниво 2)" in pdf
    assert "Запазени заклинания: Fireball (ниво 3), Fly (ниво 3)" in pdf
    res = _res(catalog, [_wizard(17)])
    assert "Майсторство" not in to_markdown(res) and "Запазени" not in to_markdown(res)
    assert "Майсторство" not in _pdf_text(res)


# ---- degrade and timing ----------------------------------------------------------------------

def test_srd_only_catalog_has_no_grants_and_does_not_crash(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    assert cat.class_2024_spell_grants == {}
    res = _res(cat, [("ranger", 5, {}), ("bard", 10, {})])
    assert _always(res, "ranger") == []
    assert all("Magical Secrets" not in o["label"] for o in _card(res, BARD_KNOWN)["options"])
    res = _res(cat, [("wizard", 20, {BOOK: ["fireball"]})])
    assert all(_card(res, cid) is None for cid in (MASTERY1, MASTERY2, SIGNATURE))


@needs_data
def test_resolve_stays_fast(catalog):
    drafts = {
        "wizard20": [_wizard(20, {MASTERY1: ["magic-missile-xphb"], SIGNATURE: ["fireball-xphb", "fly-xphb"]})],
        "bard20": [("bard", 20, {})], "paladin5": [("paladin", 5, {})], "ranger5": [("ranger", 5, {})],
        "druid2": [("druid", 2, {})], "warlock9": [("warlock", 9, {})],
        "fighter20": [("fighter", 20, {})],
    }
    for name, classes in drafts.items():
        for ruleset in ("mixed", "2024"):
            _res(catalog, classes, ruleset=ruleset)
            start = time.perf_counter()
            for _ in range(10):
                _res(catalog, classes, ruleset=ruleset)
            assert (time.perf_counter() - start) / 10 < 0.05, (name, ruleset)
