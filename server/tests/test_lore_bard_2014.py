"""RPX1 (Extra 1, D4): SRD College of Lore Bard 3 Bonus Proficiencies and Bard 6 Additional Magical Secrets under
mixed and 2014 (2024 keeps its XPHB Lore card, test_subclass_picks_2024.py).

Governing texts (catalog.features, SRD ids, subclass `lore`; pinned verbatim below, read 2026-10-23):
  bonus-proficiencies (level 3)  "When you join the College of Lore at 3rd level, you gain proficiency with three
                                 skills of your choice."
  additional-magical-secrets (6) "At 6th level, you learn two spells of your choice from any class. A spell you choose
                                 must be of a level you can cast, as shown on the Bard table, or a cantrip. The chosen
                                 spells count as bard spells for you but don't count against the number of bard spells
                                 you know."

Rule matrix (ruleset mixed and 2014; the Bard class with the SRD subclass `lore`, the SRD feature records present):
  Bonus Proficiencies
    card        `class:bard:3:feature:bonus-proficiencies`, count 3, the 18 skills; absent below Bard 3, without Lore,
                with another subclass, under 2024, without the feature record
    position    the RP12 positioned gate: the card sees every proficiency gained at or before (class order, class
                level 3) - background, class skill cards, an earlier class' skills - disabled "already proficient",
                a stored duplicate is dropped with a non-blocking `pruned`; later cards (a multiclass skill card, the
                Expertise card sees the skill as proficient) see the picks
    effects     the skills reach derived.skills / sheet.proficiencies.skills and the Bonus Proficiencies row of
                sheet.features (`choice`)
    unavailable a card with every option disabled is `unavailable` (never blocks export)
  Additional Magical Secrets
    card        `class:bard:6:feature:additional-magical-secrets`, count 2; absent below Bard 6, without Lore, under
                2024, without the feature record
    options     every spell that sits on some class list (the Bard's own too: "any class"), ruleset / sources aware, of
                a level 1 .. the highest slot level of the BARD table (multiclass: the Bard's own table), plus
                cantrips of every class; a spell on no class list is not offered; groups `spell-level-N`
    not counted the known-spells card keeps its count (picks do not use Spells Known slots) and the RP16 Magical
                Secrets cap (10 / 14 / 18) does not count these picks
    duplicates  a spell picked on the Cantrips / Spells Known card is disabled "already known" here and a stored
                duplicate is dropped (`pruned`); a spell picked here is disabled on those two cards
    sheet       the picks list in sheet.spells[bard].known (a cantrip with level 0, as the RP16 secrets cantrips)
    stale       count-variable: a pick that stops being offered (level / sources) or exceeds the count is `pruned`"""
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from engine import class_choices_2024
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

BONUS = "class:bard:3:feature:bonus-proficiencies"
SECRETS = "class:bard:6:feature:additional-magical-secrets"
KNOWN = "class:bard:spells-known"
CANTRIPS = "class:bard:spells-cantrips"
BARD_SKILLS = "class:bard:1:prof-choice-0"
EXPERTISE = "class:bard:3:expertise-choice:bard-expertise-1"
RULESETS = pytest.mark.parametrize("ruleset", ["mixed", "2014"])


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", background="acolyte", sources=()):
    """classes: (classId, level, subclassId | None, {cid: [picks]})."""
    return resolve({
        "ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 16, "WIS": 14, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": background},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, **({"subclassId": sub} if sub else {}), "choices": ch}
                    for c, lv, sub, ch in classes],
    }, catalog)


def _lore(catalog, level, choices=None, ruleset="mixed", **kw):
    return _res(catalog, [("bard", level, "lore", choices or {})], ruleset, **kw)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next((o for o in card["options"] if o["id"] == oid), None)


def _skills(res):
    return set(res["sheet"]["proficiencies"]["skills"])


def _pruned(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


def _bard_known(res):
    return next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]


# ---- data pins ---------------------------------------------------------------------------------

def test_srd_feature_texts_are_what_the_rules_quote(catalog):
    bonus, secrets = catalog.features["bonus-proficiencies"], catalog.features["additional-magical-secrets"]
    for feature, level in ((bonus, 3), (secrets, 6)):
        assert feature["level"] == level and feature["class"]["index"] == "bard" and feature["subclass"]["index"] == "lore"
    assert " ".join(bonus["desc"]) == ("When you join the College of Lore at 3rd level, you gain proficiency with three "
                                       "skills of your choice.")
    text = " ".join(secrets["desc"])
    assert "you learn two spells of your choice from any class" in text
    assert "of a level you can cast, as shown on the Bard table, or a cantrip" in text
    assert "count as bard spells for you but don't count against the number of bard spells you know" in text


def test_reference_data_quotes_match_the_catalog(catalog):
    for spec in reference_data.SUBCLASS_PICKS_2014:
        assert spec["quote"] in " ".join(catalog.features[spec["feature"]]["desc"]), spec["feature"]
    spec = reference_data.ADDITIONAL_SECRETS_2014
    assert spec["quote"] in " ".join(catalog.features[spec["feature"]]["desc"])
    assert catalog.subclasses[spec["subclass"]]["class"]["index"] == spec["class"] == "bard"


# ---- Bonus Proficiencies: the card -------------------------------------------------------------

@RULESETS
def test_bonus_proficiencies_card(catalog, ruleset):
    assert _card(_lore(catalog, 2, ruleset=ruleset), BONUS) is None
    assert _card(_res(catalog, [("bard", 3, None, {})], ruleset), BONUS) is None
    assert _card(_res(catalog, [("bard", 3, "valor-phb", {})], ruleset), BONUS) is None
    card = _card(_lore(catalog, 3, ruleset=ruleset), BONUS)
    assert card["count"] == 3 and card["status"] == "pending" and card["label"] == "Bonus Proficiencies"
    assert card["source"] == {"kind": "class", "id": "bard", "label": "Bard", "level": 3}
    assert {o["id"] for o in card["options"]} == set(reference_data.SKILL_NAMES) and len(card["options"]) == 18
    assert card["description"] == " ".join(catalog.features["bonus-proficiencies"]["desc"])


@needs_official
def test_bonus_proficiencies_is_absent_under_2024_and_xphb_lore_is_unchanged(catalog):
    res = _res(catalog, [("bard", 3, "lore", {})], "2024")
    assert _card(res, BONUS) is None
    xphb = _res(catalog, [("bard", 3, "lore-xphb", {})], "2024", background="sage-xphb")
    assert _card(xphb, "class:bard:3:feature:lore-xphb-3-bonus-proficiencies")["count"] == 3
    assert _card(xphb, BONUS) is None
    # a hidden stored XPHB Lore under mixed shows no card of either kind
    mixed = _res(catalog, [("bard", 3, "lore-xphb", {})], "mixed")
    assert _card(mixed, BONUS) is None and _card(mixed, "class:bard:3:feature:lore-xphb-3-bonus-proficiencies") is None


@RULESETS
def test_bonus_picks_are_proficiencies_and_row_choice(catalog, ruleset):
    picks = ["skill-arcana", "skill-history", "skill-nature"]
    res = _lore(catalog, 3, {BONUS: picks}, ruleset, background="criminal")
    base = _lore(catalog, 3, {}, ruleset, background="criminal")
    assert _card(res, BONUS)["status"] == "resolved"
    for s in picks:
        assert s in _skills(res) and s not in _skills(base)
        assert res["derived"]["skills"][s] - base["derived"]["skills"][s] == 1   # +2 proficiency instead of Jack's +1
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Bonus Proficiencies")
    assert row["choice"] == ["Arcana", "History", "Nature"]


def test_bonus_overlap_with_the_background_is_disabled_and_a_stored_duplicate_ignored(catalog):
    res = _lore(catalog, 3, {BONUS: ["skill-insight", "skill-arcana"]})           # Acolyte grants Insight + Religion
    card = _card(res, BONUS)
    assert _opt(card, "skill-insight")["disabled"] and _opt(card, "skill-religion")["disabled"]
    assert _opt(card, "skill-arcana").get("disabled") is None
    assert card["selected"] == ["skill-arcana"] and card["status"] == "pending"
    assert _opt(card, "skill-insight")["disabledReason"] == "already granted by Acolyte"   # the generic reason, as under 2024
    assert not [p for p in res["problems"] if "bonus" in p["id"]]


def test_a_class_skill_pick_made_before_the_card_disables_it_there(catalog):
    res = _lore(catalog, 3, {BARD_SKILLS: ["skill-stealth", "skill-arcana", "skill-nature"], BONUS: ["skill-stealth"]})
    card = _card(res, BONUS)
    for s in ("skill-stealth", "skill-arcana", "skill-nature"):
        assert _opt(card, s)["disabled"] is True
    assert card["selected"] == [] and _pruned(res, BONUS)


def test_the_bonus_picks_are_seen_by_the_expertise_card(catalog):
    res = _lore(catalog, 3, {BONUS: ["skill-arcana", "skill-history", "skill-nature"]})
    exp = _card(res, EXPERTISE)
    assert _opt(exp, "skill-arcana").get("disabled") is None            # proficient through Lore: eligible
    assert _opt(exp, "skill-medicine")["disabled"] is True              # not proficient: not eligible


def test_an_earlier_class_skill_is_seen_by_the_card_and_the_card_by_a_later_multiclass_card(catalog):
    # Rogue first (Stealth), then Bard 3 Lore: Stealth is held at the Bard card's position
    res = _res(catalog, [("rogue", 1, None, {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics",
                                                                            "skill-perception", "skill-deception"]}),
                         ("bard", 3, "lore", {BONUS: ["skill-stealth"]})])
    card = _card(res, BONUS)
    assert _opt(card, "skill-stealth")["disabled"] is True and card["selected"] == []
    # Bard 3 Lore first, a Rogue as the second class: the multiclass skill card sees the Lore picks
    res = _res(catalog, [("bard", 3, "lore", {BONUS: ["skill-stealth", "skill-arcana", "skill-nature"]}),
                         ("rogue", 1, None, {"class:rogue:multiclass-prof-choice-0": ["skill-stealth"]})])
    multi = _card(res, "class:rogue:multiclass-prof-choice-0")
    assert _opt(multi, "skill-stealth")["disabled"] is True and multi["selected"] == []
    assert _opt(multi, "skill-stealth")["disabledReason"] == "already proficient" and _pruned(res, multi["id"])


def test_a_full_set_of_proficiencies_makes_the_card_unavailable_not_blocking():
    choices = [{"id": BONUS, "source": {"kind": "class", "id": "bard", "label": "Bard", "level": 3}, "label": "Bonus Proficiencies",
                "count": 3, "selected": [], "status": "pending",
                "options": [{"id": "skill-arcana", "label": "Arcana", "disabled": True}]}]
    for ruleset in ("mixed", "2014", "2024"):
        out = class_choices_2024.mark_unavailable(copy.deepcopy(choices), ruleset)
        assert out[0]["status"] == "unavailable", ruleset


def test_bonus_card_degrades_without_the_feature_record(catalog):
    patched = copy.copy(catalog)
    patched.features = {k: v for k, v in catalog.features.items() if k != "bonus-proficiencies"}
    assert _card(_lore(patched, 6), BONUS) is None
    assert _card(_lore(patched, 6), SECRETS) is not None      # the other feature is independent


# ---- Additional Magical Secrets: the card ------------------------------------------------------

@RULESETS
def test_secrets_card_appears_at_bard_6_with_lore_only(catalog, ruleset):
    assert _card(_lore(catalog, 5, ruleset=ruleset), SECRETS) is None
    assert _card(_res(catalog, [("bard", 6, None, {})], ruleset), SECRETS) is None
    assert _card(_res(catalog, [("bard", 6, "valor-phb", {})], ruleset), SECRETS) is None
    card = _card(_lore(catalog, 6, ruleset=ruleset), SECRETS)
    assert card["count"] == 2 and card["status"] == "pending" and card["label"] == "Additional Magical Secrets"
    assert card["source"] == {"kind": "class", "id": "bard", "label": "Bard", "level": 6}
    assert "don't count against the number of bard spells you know" in card["description"]


@needs_official
@RULESETS
def test_secrets_options_are_any_class_up_to_the_bard_slot_level_plus_cantrips(catalog, ruleset):
    card = _card(_lore(catalog, 6, ruleset=ruleset), SECRETS)           # Bard 6: 3rd-level slots
    fireball = _opt(card, "fireball")
    assert fireball["label"] == "Fireball" and fireball["group"] == "spell-level-3"
    assert _opt(card, "fire-bolt")["group"] == "spell-level-0"           # another class' cantrip
    assert _opt(card, "vicious-mockery")["group"] == "spell-level-0"     # "any class", including the Bard
    assert _opt(card, "cure-wounds") is not None                          # the Bard's own list
    assert _opt(card, "wall-of-fire") is None                             # level 4: no 4th-level slots yet
    orphans = [s for s in catalog.spells.values() if not s.get("classes") and s["level"] <= 3 and s["ruleset"] != "2024"]
    assert orphans and all(_opt(card, s["index"]) is None for s in orphans)
    levels = [catalog.spells[o["id"]]["level"] for o in card["options"]]
    assert levels == sorted(levels) and max(levels) == 3 and levels[0] == 0
    assert len({o["id"] for o in card["options"]}) == len(card["options"])


def test_secrets_levels_follow_the_bard_table(catalog):
    assert _opt(_card(_lore(catalog, 7), SECRETS), "wall-of-fire") is not None
    assert _opt(_card(_lore(catalog, 7), SECRETS), "cone-of-cold") is None
    assert _opt(_card(_lore(catalog, 20), SECRETS), "wish") is not None


@needs_official
def test_secrets_sources_srd_filter_and_kept_hidden_pick(catalog):
    srd = _card(_lore(catalog, 6, sources=["srd"]), SECRETS)
    assert _opt(srd, "fireball") is not None
    assert all(catalog.spells[o["id"]].get("source") in (None, "SRD") for o in srd["options"])
    assert len(srd["options"]) < len(_card(_lore(catalog, 6), SECRETS)["options"])
    book_only = next(s for s in catalog.spells.values()
                     if s.get("source") not in (None, "SRD") and s["ruleset"] != "2024" and s["level"] == 3 and s.get("classes"))
    assert _opt(srd, book_only["index"]) is None
    kept = _card(_lore(catalog, 6, {SECRETS: [book_only["index"]]}, sources=["srd"]), SECRETS)
    assert kept["selected"] == [book_only["index"]] and _opt(kept, book_only["index"]) is not None


def test_secrets_card_uses_the_bard_table_in_a_multiclass(catalog):
    res = _res(catalog, [("wizard", 8, None, {}), ("bard", 6, "lore", {})])    # combined slots reach 4th level
    card = _card(res, SECRETS)
    assert _opt(card, "fireball") is not None and _opt(card, "wall-of-fire") is None
    res = _res(catalog, [("bard", 6, "lore", {}), ("wizard", 3, None, {})])
    assert _card(res, SECRETS) is not None and _card(res, "class:wizard:spells-known") is not None


# ---- Additional Magical Secrets: not counted, duplicates, sheet --------------------------------

@RULESETS
def test_secrets_picks_do_not_use_known_spell_slots(catalog, ruleset):
    base = _lore(catalog, 6, ruleset=ruleset)
    known_card = _card(base, KNOWN)
    own = [o["id"] for o in known_card["options"]][:known_card["count"]]
    res = _lore(catalog, 6, {KNOWN: own, SECRETS: ["fireball", "fire-bolt"]}, ruleset)
    assert _card(res, KNOWN)["count"] == known_card["count"] == len(_card(res, KNOWN)["selected"])
    assert _card(res, SECRETS)["status"] == "resolved" and _card(res, SECRETS)["selected"] == ["fireball", "fire-bolt"]
    assert not _pruned(res, SECRETS) and not _pruned(res, KNOWN) and not res["problems"]
    known = _bard_known(res)
    assert {s["id"] for s in known} == set(own) | {"fireball", "fire-bolt"}
    assert next(s for s in known if s["id"] == "fire-bolt")["level"] == 0
    assert next(s for s in known if s["id"] == "fireball")["level"] == 3
    assert len(known) == known_card["count"] + 2


def test_the_rp16_cap_ignores_these_picks(catalog):
    # Bard 10 Lore: the known card still allows its two Magical Secrets picks after both Additional picks are taken
    own = [o["id"] for o in _card(_lore(catalog, 10), KNOWN)["options"] if "(Magical Secrets)" not in o["label"]][:12]
    res = _lore(catalog, 10, {KNOWN: own + ["counterspell", "spiritual-weapon"], SECRETS: ["fireball", "fire-bolt"]})
    known, secrets = _card(res, KNOWN), _card(res, SECRETS)
    assert known["selected"] == own + ["counterspell", "spiritual-weapon"] and secrets["selected"] == ["fireball", "fire-bolt"]
    assert not res["pruned"] and not res["problems"]
    assert _opt(known, "lightning-bolt")["disabled"] is True        # RP16's own cap (2 of 2) is intact
    assert _opt(known, "lightning-bolt")["disabledReason"] == "Magical Secrets: 2 of 2 used"


def test_a_spell_known_elsewhere_is_disabled_here_and_a_stored_duplicate_pruned(catalog):
    own_spell = next(o["id"] for o in _card(_lore(catalog, 6), KNOWN)["options"])
    res = _lore(catalog, 6, {KNOWN: [own_spell], CANTRIPS: ["vicious-mockery"],
                             SECRETS: [own_spell, "fireball"]})
    card = _card(res, SECRETS)
    assert _opt(card, own_spell)["disabled"] is True and _opt(card, own_spell)["disabledReason"] == "already known"
    assert _opt(card, "vicious-mockery")["disabled"] is True
    assert card["selected"] == ["fireball"] and card["status"] == "pending"
    assert catalog.spells[own_spell]["name"] in " ".join(p["reason"] for p in _pruned(res, SECRETS))
    cantrip = _lore(catalog, 6, {CANTRIPS: ["vicious-mockery"], SECRETS: ["vicious-mockery", "fireball"]})
    assert _card(cantrip, SECRETS)["selected"] == ["fireball"]
    assert "Vicious Mockery" in " ".join(p["reason"] for p in _pruned(cantrip, SECRETS))
    assert _card(res, KNOWN)["selected"] == [own_spell] and _card(res, CANTRIPS)["selected"] == ["vicious-mockery"]
    assert not res["problems"]


def test_a_spell_taken_here_is_disabled_on_the_known_and_cantrip_cards(catalog):
    res = _lore(catalog, 6, {SECRETS: ["cure-wounds", "vicious-mockery"]})
    known, cantrips = _card(res, KNOWN), _card(res, CANTRIPS)
    assert _opt(known, "cure-wounds")["disabled"] is True
    assert "Additional Magical Secrets" in _opt(known, "cure-wounds")["disabledReason"]
    assert _opt(cantrips, "vicious-mockery")["disabled"] is True
    assert _opt(known, "healing-word").get("disabled") is None
    assert _card(res, SECRETS)["selected"] == ["cure-wounds", "vicious-mockery"]
    # a duplicate stored on both cards: the earlier cards win, the Additional pick is dropped
    both = _lore(catalog, 6, {KNOWN: ["cure-wounds"], SECRETS: ["cure-wounds"]})
    assert _card(both, KNOWN)["selected"] == ["cure-wounds"] and _card(both, SECRETS)["selected"] == []


@RULESETS
def test_sheet_exports_and_features_row(catalog, ruleset):
    res = _lore(catalog, 6, {SECRETS: ["fireball", "fire-bolt"]}, ruleset)
    assert {"fireball", "fire-bolt"} <= {s["id"] for s in _bard_known(res)}
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Additional Magical Secrets")
    assert row["choice"] == ["Fireball", "Fire Bolt"]
    from markdown_export import to_markdown  # the existing export path reads sheet.spells[].known
    assert "Fireball" in to_markdown(res) and "Fire Bolt" in to_markdown(res)
    assert _lore(catalog, 6, ruleset=ruleset)["sheet"]["spells"][0]["known"] == []


def test_secrets_are_count_variable_so_stale_picks_are_pruned_not_blocking(catalog):
    # too many stored, an unaffordable level after a level-down, a spell hidden by the sources filter
    res = _lore(catalog, 6, {SECRETS: ["fireball", "fire-bolt", "counterspell"]})
    assert _card(res, SECRETS)["selected"] == ["fireball", "fire-bolt"] and _pruned(res, SECRETS)
    assert not res["problems"] and not [p for p in res["problems"] if "over-selected" in p["id"]]
    down = _lore(catalog, 6, {SECRETS: ["wall-of-fire", "fireball"]})                 # level 4: not at Bard 6
    assert _card(down, SECRETS)["selected"] == ["fireball"] and _pruned(down, SECRETS) and not down["problems"]
    below = _lore(catalog, 5, {SECRETS: ["fireball", "fire-bolt"]})                  # Bard 5: no card
    assert _card(below, SECRETS) is None and not below["problems"]
    assert any(SECRETS in (p.get("choiceId") or "") or "no longer applies" in p["reason"] for p in below["pruned"])


def test_hidden_secrets_pick_does_not_block_and_the_card_never_blocks_export(catalog):
    res = _lore(catalog, 6)
    assert _card(res, SECRETS)["status"] == "pending"
    assert not [p for p in res["problems"] if "magical-secrets" in p["id"]]


def test_secrets_card_degrades_without_the_feature_record(catalog):
    patched = copy.copy(catalog)
    patched.features = {k: v for k, v in catalog.features.items() if k != "additional-magical-secrets"}
    assert _card(_lore(patched, 6), SECRETS) is None


def test_secrets_2024_and_non_lore_are_unchanged(catalog):
    assert _card(_res(catalog, [("bard", 6, "lore", {})], "2024"), SECRETS) is None
    xphb = _res(catalog, [("bard", 6, "lore-xphb", {})], "2024", background="sage-xphb")
    assert not [c for c in xphb["choices"] if "additional-magical-secrets" in c["id"]]
    other = _res(catalog, [("wizard", 6, None, {})])
    assert not [c for c in other["choices"] if "additional-magical-secrets" in c["id"]]


# ---- speed -------------------------------------------------------------------------------------

@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_bard_20_lore_resolves_under_50_ms(catalog, ruleset):
    sub = "lore-xphb" if ruleset == "2024" else "lore"
    bg = "sage-xphb" if ruleset == "2024" else "acolyte"
    _res(catalog, [("bard", 20, sub, {})], ruleset, background=bg)
    t = time.perf_counter()
    for _ in range(20):
        _res(catalog, [("bard", 20, sub, {BONUS: ["skill-arcana"], SECRETS: ["fireball"]})], ruleset, background=bg)
    assert (time.perf_counter() - t) / 20 * 1000 < 50
