"""RP16 (E11a): SRD Bard Magical Secrets (10 / 14 / 18) on the known-spells card under mixed and 2014.

Governing text (catalog.features magical-secrets-1/2/3, srd ids, level 10 / 14 / 18; pinned verbatim below, read 2026-10-23):
  "Choose two spells from any class, including this one. A spell you choose must be of a level you can cast, as
  shown on the Bard table, or a cantrip. The chosen spells count as bard spells for you and are included in the
  number in the Spells Known column of the Bard table. You learn two additional spells from any class at 14th
  level and again at 18th level."

Rule matrix (ruleset mixed and 2014; 2024 keeps its XPHB mechanism, test_class_spell_grants_2024.py):
  scope        Bard class level (multiclass: the Bard's own level and Bard table), SRD features present in the catalog
  offered      on `class:bard:spells-known`: every spell of every class list (ruleset / sources aware, a spell that is
               on no class list is not "from a class") of level 1 .. highest Bard slot level, plus the cantrips that
               are NOT Bard cantrips (those are on the Cantrips card). Labelled "<Spell> (Magical Secrets)" when not
               on the Bard list; groups stay `spell-level-N` (cantrips `spell-level-0`)
  count        unchanged: the chosen spells "are included in the number in the Spells Known column", so a cantrip
               picked this way (DECIDED, the feature's own sentence) takes one of the known slots
  cap          picks not on the Bard list <= 2 x features reached (10: 2, 14: 4, 18: 6). At the cap the other-class
               options are disabled "Magical Secrets: N of N used"; a stored pick over the cap is dropped (`pruned`,
               never blocking). No level-up history: the per-feature level limit is not enforced (as C6d)
  absent       Bard below 10, non-Bards, the other class of a multiclass Bard, a catalog without the SRD features"""
from perf_helpers import assert_fast
import copy
import time

import pytest

from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

KNOWN = "class:bard:spells-known"
CANTRIPS = "class:bard:spells-cantrips"
RULESETS = pytest.mark.parametrize("ruleset", ["mixed", "2014"])


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", sources=()):
    return resolve({
        "ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 16, "WIS": 14, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }, catalog)


def _bard(catalog, level, picks=None, ruleset="mixed", sources=()):
    return _res(catalog, [("bard", level, {KNOWN: list(picks)} if picks is not None else {})], ruleset, sources)


def _card(res, cid=KNOWN):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, sid):
    return next((o for o in card["options"] if o["id"] == sid), None)


def _pruned(res, cid=KNOWN):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


def _bard_spells(catalog, level, count, ruleset="mixed"):
    """`count` ordinary Bard-list picks from the real known card."""
    card = _card(_bard(catalog, level, None, ruleset))
    return [o["id"] for o in card["options"] if "(Magical Secrets)" not in o["label"]][:count]


# ---- data pins ---------------------------------------------------------------------------------

def test_srd_feature_texts_are_what_the_rules_below_quote(catalog):
    for fid, level in (("magical-secrets-1", 10), ("magical-secrets-2", 14), ("magical-secrets-3", 18)):
        feature = catalog.features[fid]
        text = " ".join(feature["desc"])
        assert feature["level"] == level and feature["class"]["index"] == "bard"
        assert "Choose two spells from any class, including this one." in text
        assert "of a level you can cast, as shown on the Bard table, or a cantrip" in text
        assert "included in the number in the Spells Known column of the Bard table" in text
        assert "two additional spells from any class at 14th level and again at 18th level" in text


# ---- offered -----------------------------------------------------------------------------------

@RULESETS
def test_bard_9_has_no_magical_secrets(catalog, ruleset):
    card = _card(_bard(catalog, 9, ruleset=ruleset))
    assert _opt(card, "fireball") is None and _opt(card, "sacred-flame") is None
    assert all("Magical Secrets" not in o["label"] for o in card["options"])
    assert "Magical Secrets" not in card["description"]


@RULESETS
def test_bard_10_offers_other_class_spells_and_cantrips_labelled(catalog, ruleset):
    card = _card(_bard(catalog, 10, ruleset=ruleset))
    fireball = _opt(card, "fireball")
    assert fireball["label"] == "Fireball (Magical Secrets)" and fireball["group"] == "spell-level-3"
    assert _opt(card, "spiritual-weapon")["label"] == "Spiritual Weapon (Magical Secrets)"
    assert _opt(card, "cure-wounds")["label"] == "Cure Wounds"                     # already a Bard spell: no label
    assert _opt(card, "disintegrate") is None                                       # level 6: Bard 10 has 5th-level slots
    fire_bolt = _opt(card, "fire-bolt")                                             # another class's cantrip
    assert fire_bolt["label"] == "Fire Bolt (Magical Secrets)" and fire_bolt["group"] == "spell-level-0"
    assert _opt(card, "vicious-mockery") is None                                    # a Bard cantrip: the Cantrips card
    assert "Magical Secrets" in card["description"]


@RULESETS
def test_secrets_spells_follow_the_highest_bard_slot_level(catalog, ruleset):
    assert _opt(_card(_bard(catalog, 11, ruleset=ruleset)), "disintegrate")["label"] == "Disintegrate (Magical Secrets)"
    assert _opt(_card(_bard(catalog, 16, ruleset=ruleset)), "wish") is None
    assert _opt(_card(_bard(catalog, 17, ruleset=ruleset)), "wish")["label"] == "Wish (Magical Secrets)"


@needs_official
def test_a_spell_on_no_class_list_is_not_offered(catalog):
    orphans = [s for s in catalog.spells.values() if not s.get("classes") and s["level"] <= 5]
    assert orphans, "the catalog should hold class-less spells for this test to mean something"
    card = _card(_bard(catalog, 10))
    assert all(_opt(card, s["index"]) is None for s in orphans if s["ruleset"] != "2024")


def test_each_offered_spell_is_unique_and_the_list_is_sorted_by_level_then_name(catalog):
    options = _card(_bard(catalog, 20))["options"]
    ids = [o["id"] for o in options]
    assert len(ids) == len(set(ids))
    levels = [catalog.spells[i]["level"] for i in ids]
    assert levels == sorted(levels) and levels[0] == 0


@needs_official
def test_sources_srd_offers_only_srd_spells(catalog):
    card = _card(_bard(catalog, 10, sources=["srd"]))
    assert _opt(card, "fireball")["label"] == "Fireball (Magical Secrets)"
    assert all(catalog.spells[o["id"]].get("source") in (None, "SRD") for o in card["options"])
    assert len(card["options"]) < len(_card(_bard(catalog, 10))["options"])


@needs_official
def test_a_stored_pick_hidden_by_the_sources_filter_stays_offered(catalog):
    book_only = next(s for s in catalog.spells.values()
                     if s.get("source") not in (None, "SRD") and not s.get("ruleset") == "2024" and s["level"] == 3
                     and s.get("classes") and not any(c["index"] == "bard" for c in s["classes"]))
    card = _card(_bard(catalog, 10, [book_only["index"]], sources=["srd"]))
    assert book_only["index"] in card["selected"]
    assert _opt(card, book_only["index"])["label"].endswith("(Magical Secrets)")


# ---- count ---------------------------------------------------------------------------------------

@RULESETS
def test_count_is_unchanged_and_a_secrets_cantrip_takes_one_known_slot(catalog, ruleset):
    own = _bard_spells(catalog, 10, 13, ruleset)
    base = _card(_bard(catalog, 10, own, ruleset))
    assert base["count"] == 14                                                      # SRD Bard table, level 10
    res = _bard(catalog, 10, own + ["fire-bolt", "sacred-flame"], ruleset)
    card = _card(res)
    assert card["count"] == 14 and card["selected"] == own + ["fire-bolt"]           # the 15th pick is over the count
    assert _pruned(res) and "Sacred Flame" in _pruned(res)[0]["reason"]
    known = next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]
    assert "fire-bolt" in [s["id"] for s in known] and next(s for s in known if s["id"] == "fire-bolt")["level"] == 0


# ---- cap -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("level,cap", [(10, 2), (13, 2), (14, 4), (17, 4), (18, 6), (20, 6)])
def test_cap_is_two_per_magical_secrets_feature_reached(catalog, level, cap):
    others = ["fireball", "spiritual-weapon", "fire-bolt", "sacred-flame", "fly", "haste"]
    own = _bard_spells(catalog, level, 3)
    res = _bard(catalog, level, own + others[:cap])
    card = _card(res)
    assert card["selected"] == own + others[:cap] and not _pruned(res)
    over = _opt(card, others[cap] if cap < len(others) else "counterspell")
    assert over["disabled"] is True and over["disabledReason"] == f"Magical Secrets: {cap} of {cap} used"
    ordinary = next(o for o in card["options"] if "(Magical Secrets)" not in o["label"] and o["id"] not in own)
    assert not ordinary.get("disabled")                                             # Bard-list spells stay open


def test_below_the_cap_other_class_options_stay_enabled(catalog):
    card = _card(_bard(catalog, 10, ["fireball"]))
    assert not _opt(card, "spiritual-weapon").get("disabled") and not _opt(card, "fire-bolt").get("disabled")
    assert not _opt(card, "fireball").get("disabled")                               # a picked one is never disabled


def test_a_stored_pick_over_the_cap_is_pruned_and_never_blocks(catalog):
    res = _bard(catalog, 10, ["fireball", "spiritual-weapon", "fire-bolt"])
    assert _card(res)["selected"] == ["fireball", "spiritual-weapon"]
    pruned = _pruned(res)
    assert len(pruned) == 1 and "Fire Bolt" in pruned[0]["reason"]
    assert res["problems"] == _bard(catalog, 10)["problems"]                        # nothing blocking was added


def test_level_down_below_10_prunes_the_secrets_picks_but_keeps_bard_spells(catalog):
    own = _bard_spells(catalog, 9, 3)
    res = _bard(catalog, 9, own + ["fireball", "fire-bolt"])
    assert _card(res)["selected"] == own
    assert "Fireball" in _pruned(res)[0]["reason"] and "Fire Bolt" in _pruned(res)[0]["reason"]


def test_level_down_14_to_10_keeps_two_secrets_picks(catalog):
    picks = ["fireball", "spiritual-weapon", "fire-bolt", "sacred-flame"]
    assert _card(_bard(catalog, 14, picks))["selected"] == picks
    res = _bard(catalog, 10, picks)
    assert _card(res)["selected"] == picks[:2] and _pruned(res)


@RULESETS
def test_a_secrets_pick_lands_on_the_sheet_as_a_known_spell(catalog, ruleset):
    res = _bard(catalog, 10, ["fireball"], ruleset)
    known = next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]
    assert "fireball" in [s["id"] for s in known]


# ---- scope -----------------------------------------------------------------------------------------

def test_non_bards_are_unaffected(catalog):
    res = _res(catalog, [("cleric", 11, {})])
    assert all("Magical Secrets" not in o["label"] for o in _card(res, "class:cleric:spells-known")["options"])
    res = _res(catalog, [("sorcerer", 11, {})])
    assert all("Magical Secrets" not in o["label"] for o in _card(res, "class:sorcerer:spells-known")["options"])


def test_a_multiclass_bard_secrets_do_not_touch_the_other_class(catalog):
    res = _res(catalog, [("bard", 10, {}), ("wizard", 3, {})])
    assert _opt(_card(res), "fireball")["label"] == "Fireball (Magical Secrets)"
    wizard = _card(res, "class:wizard:spells-known")
    assert wizard and all("Magical Secrets" not in o["label"] for o in wizard["options"])
    assert "Magical Secrets" not in wizard["description"]


def test_a_multiclass_bard_uses_the_bard_level_not_the_total_level(catalog):
    res = _res(catalog, [("wizard", 8, {}), ("bard", 6, {})])                      # total level 14, Bard 6
    assert all("Magical Secrets" not in o["label"] for o in _card(res)["options"])


def test_degrades_without_the_srd_features(catalog):
    cat = copy.copy(catalog)
    cat.features = {k: v for k, v in catalog.features.items() if not k.startswith("magical-secrets-")}
    card = _card(_bard(cat, 10))
    assert all("Magical Secrets" not in o["label"] for o in card["options"]) and _opt(card, "fireball") is None


# ---- 2024 unchanged ----------------------------------------------------------------------------------

@needs_official
def test_2024_keeps_its_own_mechanism(catalog):
    card = _card(_bard(catalog, 10, ruleset="2024"))
    assert _opt(card, "fireball-xphb")["label"] == "Fireball (Magical Secrets)"
    assert all(catalog.spells[o["id"]]["level"] >= 1 for o in card["options"])     # no cantrips, no cap
    res = _bard(catalog, 10, ["fireball-xphb", "fly-xphb", "haste-xphb"], "2024")
    assert len(_card(res)["selected"]) == 3 and not _pruned(res)


# ---- speed ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_bard_20_resolves_under_50_ms(catalog, ruleset):
    picks = ["fireball", "fly", "haste"] if ruleset != "2024" else ["fireball-xphb", "fly-xphb", "haste-xphb"]
    _bard(catalog, 20, picks, ruleset)
    laps = []
    for _ in range(20):
        t_run = time.perf_counter()
        _bard(catalog, 20, picks, ruleset)
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
