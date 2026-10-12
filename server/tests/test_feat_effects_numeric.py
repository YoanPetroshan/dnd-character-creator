"""FE1: feat effects on initiative, hit point maximum, walking speed and climb speed
(docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its own edition's text under
every ruleset (effects are keyed by feat index). Governing sentences (catalog text, tags stripped):

  Alert (PHB)          "You gain a +5 bonus to initiative."  -> flat +5 on top of everything (JoaT too).
  Alert (XPHB)         "you can add your Proficiency Bonus to the roll"  -> initiative = DEX + PB; the
                       Jack of All Trades / Remarkable Athlete half bonus is replaced, not added.
  Tough (PHB)          "...twice your level when you gain this feat. Whenever you gain a level thereafter, your
                       hit point maximum increases by an additional 2 hit points."  -> +2 x current level.
  Tough (XPHB)         same with "character level".
  Boon of Fortitude    "Your Hit Point maximum increases by 40."
  Mobile (PHB)         "Your speed increases by 10 feet."   Speedy (XPHB): "Your Speed increases by 10 feet."
  Boon of Speed        "Your Speed increases by 30 feet."
  Squat Nimbleness     "Increase your walking speed by 5 feet."
  Mark of Passage      "Your Speed increases by 5 feet."    Transmuted Anatomy (AU): same.
  Athlete (XPHB)       "You gain a Climb Speed equal to your Speed."  -> climb = final walk speed.

Speed bonuses raise the walking speed only (F1-6 precedent), after Unarmored Movement and Fast Movement and
before the Gift of the Depths swim speed and the Athlete climb speed, which both read the final walk speed.
Matrix: rule (which feat applies) x number x source of the feat (ASI, background, species) x ruleset x
multiclass x hidden-by-filters x manual HP x no-feat identity x empty catalog x timing."""
import copy
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE1 = ("alert-phb", "alert-xphb", "tough-phb", "tough-xphb", "boon-of-fortitude-xphb", "mobile-phb",
       "speedy-xphb", "boon-of-speed-xphb", "squat-nimbleness-xge", "mark-of-passage-efa",
       "transmuted-anatomy-au", "athlete-xphb")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _asi(cls, lvl):
    return f"class:{cls}:{lvl}:asi"


def _res(catalog, classes, feats=(), ruleset="mixed", background="acolyte", species="human", added=(),
         base=None, hp=None, worn=None, extra=None):
    """classes: (classId, level). feats: ASI picks, assigned to the ASI slots (4, 8, ...) of the first class."""
    entries = []
    for n, (cls, level) in enumerate(classes):
        picks = {}
        if n == 0:
            slots = [lv for lv in (4, 8, 12, 16, 19) if lv <= level]
            if feats and str(feats[0]).startswith("boon-"):   # Epic Boons need level 19: use the last slot
                slots = slots[-1:]
            for slot, feat in zip(slots, feats):
                picks[_asi(cls, slot)] = [f"feat:{feat}"]
        entries.append({"classId": cls, "level": level, "choices": picks})
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": entries,
         "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                       "skipped": False},
         "details": {}, "preferences": {"hitPointType": hp} if hp else {}}
    if worn:
        d["equipment"]["worn"] = worn
    d.update(extra or {})
    return resolve(d, catalog)


def _d(r):
    return r["derived"]


def _feat_ids(r):
    return [f["id"] for f in r["sheet"]["feats"]]


# ---------------------------------------------------------------- data


def _plain(node):
    out = []

    def walk(n):
        if isinstance(n, str):
            out.append(n)
        elif isinstance(n, dict):
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(node)
    text = " ".join(out)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, text)


@pytest.mark.parametrize("index", FE1)
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    assert fed.FEAT_EFFECT_QUOTES[index] in _plain(catalog.feats[index]["entries"]), index


def test_entries_use_only_fe1_vocabulary_and_values():
    # (FE10 appended notes / a resource to some of these entries; the numbers are what this test pins.)
    assert {i: {k: v for k, v in fed.FEAT_EFFECTS[i].items() if k not in ("notes", "resources")}
            for i in FE1} == {
        "alert-phb": {"initiative": 5}, "alert-xphb": {"initiative": "pb"},
        "tough-phb": {"hp_per_level": 2}, "tough-xphb": {"hp_per_level": 2},
        "boon-of-fortitude-xphb": {"hp_flat": 40},
        "mobile-phb": {"walk_bonus": 10}, "speedy-xphb": {"walk_bonus": 10},
        "boon-of-speed-xphb": {"walk_bonus": 30}, "squat-nimbleness-xge": {"walk_bonus": 5},
        "mark-of-passage-efa": {"walk_bonus": 5}, "transmuted-anatomy-au": {"walk_bonus": 5},
        "athlete-xphb": {"climb_equals_walk": True},
    }


# ---------------------------------------------------------------- initiative


def test_alert_phb_adds_a_flat_five(catalog):
    base = _res(catalog, [("fighter", 4)], base={"DEX": 14})
    r = _res(catalog, [("fighter", 4)], ["alert-phb"], base={"DEX": 14})
    assert "alert-phb" in _feat_ids(r)
    assert _d(r)["initiative"] == _d(base)["initiative"] + 5 == 7   # DEX 14 = +2, then +5


def test_alert_phb_stacks_with_jack_of_all_trades(catalog):
    r = _res(catalog, [("fighter", 4), ("bard", 2)], ["alert-phb"], base={"DEX": 14})
    assert _d(r)["initiative"] == 2 + 1 + 5 == 8   # DEX +2, Jack of All Trades +1 (PB 2 // 2), Alert +5


def test_alert_xphb_background_adds_the_proficiency_bonus(catalog):
    r = _res(catalog, [("rogue", 1)], ruleset="2024", background="criminal-xphb", species="human-xphb",
             base={"DEX": 14})
    assert "alert-xphb" in _feat_ids(r)
    assert _d(r)["initiative"] == 2 + 2 == 4


def test_alert_xphb_replaces_the_jack_of_all_trades_half_bonus(catalog):
    r = _res(catalog, [("bard", 2)], ruleset="mixed", background="criminal-xphb", base={"DEX": 14})
    assert "alert-xphb" in _feat_ids(r)
    assert _d(r)["initiative"] == 4          # DEX + PB, not DEX + PB + 1
    no_alert = _res(catalog, [("bard", 2)], ruleset="mixed", background="acolyte", base={"DEX": 14})
    assert _d(no_alert)["initiative"] == 3   # Jack of All Trades alone


def test_alert_xphb_replaces_the_remarkable_athlete_half_bonus(catalog):
    champ = lambda choices: {"classes": [{"classId": "fighter", "level": 7, "subclassId": "champion",
                                          "choices": choices}]}
    with_alert = _res(catalog, [("fighter", 7)], base={"DEX": 14},
                      extra=champ({_asi("fighter", 4): ["feat:alert-xphb"]}))
    without = _res(catalog, [("fighter", 7)], base={"DEX": 14}, extra=champ({}))
    assert "alert-xphb" in _feat_ids(with_alert)
    assert _d(without)["initiative"] == 2 + 2     # Remarkable Athlete: half PB (3) rounded up = 2
    assert _d(with_alert)["initiative"] == 2 + 3  # DEX + PB (3), not 2 + 3 + 2


def test_alert_xphb_follows_the_proficiency_bonus(catalog):
    r = _res(catalog, [("fighter", 5)], ["alert-xphb"], base={"DEX": 14})
    assert _d(r)["proficiencyBonus"] == 3 and _d(r)["initiative"] == 2 + 3


def test_alert_xphb_is_kept_under_ruleset_2014_when_hidden(catalog):
    r = _res(catalog, [("fighter", 4)], ["alert-xphb"], ruleset="2014", base={"DEX": 14})
    assert "alert-xphb" in _feat_ids(r)
    assert any(w["id"].startswith("feat-hidden-by-filters") for w in r["warnings"])
    assert _d(r)["initiative"] == 2 + 2


def test_alert_via_lessons_of_the_first_ones_and_species_feat(catalog):
    r = _res(catalog, [("fighter", 1)], ruleset="2024", background="acolyte-xphb", species="human-xphb",
             extra={"species": {"id": "human-xphb", "choices": {"species:human-xphb:feat-0": ["feat:alert-xphb"]}},
                    "abilities": {"method": "manual", "base": {**{a: 10 for a in ABS}, "DEX": 14}}})
    assert "alert-xphb" in _feat_ids(r) and _d(r)["initiative"] == 2 + 2


# ---------------------------------------------------------------- hit points


def _hp(r):
    return _d(r)["hitPointMax"]


def test_tough_xphb_from_a_background_adds_two_per_level(catalog):
    base = _res(catalog, [("fighter", 1)], ruleset="2024", background="acolyte-xphb", species="human-xphb",
                base={"CON": 14})
    r = _res(catalog, [("fighter", 1)], ruleset="2024", background="farmer-xphb", species="human-xphb",
             base={"CON": 14})
    assert "tough-xphb" in _feat_ids(r)
    assert _hp(r) == _hp(base) + 2
    r5 = _res(catalog, [("fighter", 5)], ruleset="2024", background="farmer-xphb", species="human-xphb",
              base={"CON": 14})
    b5 = _res(catalog, [("fighter", 5)], ruleset="2024", background="acolyte-xphb", species="human-xphb",
              base={"CON": 14})
    assert _hp(r5) == _hp(b5) + 10


def test_tough_is_retroactive_for_a_feat_taken_at_level_four(catalog):
    base = _res(catalog, [("fighter", 8)], base={"CON": 14})
    r = _res(catalog, [("fighter", 8)], ["tough-phb"], base={"CON": 14})
    assert "tough-phb" in _feat_ids(r)
    assert _hp(r) == _hp(base) + 16   # twice the level (8): 8 at level 4 + 2 for each of the 4 later levels


def test_tough_counts_every_class_level(catalog):
    base = _res(catalog, [("fighter", 4), ("wizard", 3)], base={"CON": 14})
    r = _res(catalog, [("fighter", 4), ("wizard", 3)], ["tough-phb"], base={"CON": 14})
    assert _hp(r) == _hp(base) + 14


def test_tough_adds_to_dwarven_toughness(catalog):
    dwarf = _res(catalog, [("fighter", 4)], species="dwarf", base={"CON": 14},
                 extra={"species": {"id": "dwarf", "subraceId": "hill-dwarf", "choices": {}}})
    both = _res(catalog, [("fighter", 4)], ["tough-phb"], species="dwarf", base={"CON": 14},
                extra={"species": {"id": "dwarf", "subraceId": "hill-dwarf", "choices": {}}})
    assert _hp(both) == _hp(dwarf) + 8


def test_boon_of_fortitude_adds_forty_flat(catalog):
    base = _res(catalog, [("fighter", 19)], ruleset="2024", background="acolyte-xphb", species="human-xphb")
    r = _res(catalog, [("fighter", 19)], ["boon-of-fortitude-xphb"], ruleset="2024", background="acolyte-xphb",
             species="human-xphb")
    assert "boon-of-fortitude-xphb" in _feat_ids(r)
    assert _hp(r) == _hp(base) + 40


def test_feat_hit_points_apply_in_manual_hp_mode(catalog):
    base = _res(catalog, [("fighter", 4)], hp="manual")
    r = _res(catalog, [("fighter", 4)], ["tough-phb"], hp="manual")
    assert _hp(r) == _hp(base) + 8


# ---------------------------------------------------------------- speed


def _speeds(r):
    return _d(r)["speeds"]


def test_mobile_raises_the_walking_speed_only(catalog):
    r = _res(catalog, [("fighter", 4)], ["mobile-phb"])
    assert _d(r)["speed"] == 40 and _speeds(r)["walk"] == 40


def test_mobile_with_unarmored_movement_and_fast_movement(catalog):
    monk = _res(catalog, [("monk", 6)], ["mobile-phb"], base={})
    # Monk 6 Unarmored Movement +15, Mobile +10 (the ASI slot at 4 is the feat).
    assert _d(monk)["speed"] == 30 + 15 + 10
    armored = _res(catalog, [("monk", 6)], ["mobile-phb"], added=["chain-mail"])
    assert _d(armored)["speed"] == 30 + 10        # no Unarmored Movement in armor, Mobile still applies
    barb = _res(catalog, [("barbarian", 5)], ["mobile-phb"])
    assert _d(barb)["speed"] == 30 + 10 + 10      # Fast Movement +10 and Mobile +10


def test_speedy_and_mobile_both_add(catalog):
    r = _res(catalog, [("fighter", 8)], ["mobile-phb", "speedy-xphb"])
    assert {"mobile-phb", "speedy-xphb"} <= set(_feat_ids(r))
    assert _d(r)["speed"] == 50


@pytest.mark.parametrize("feat,bonus", [("speedy-xphb", 10), ("boon-of-speed-xphb", 30),
                                        ("transmuted-anatomy-au", 5)])
def test_walk_bonus_feats(catalog, feat, bonus):
    level = 19 if feat.startswith("boon") else 4
    r = _res(catalog, [("fighter", level)], [feat])
    assert feat in _feat_ids(r), feat
    assert _d(r)["speed"] == 30 + bonus


def test_squat_nimbleness_for_a_dwarf(catalog):
    # Prerequisite: Dwarf or a Small race.
    r = _res(catalog, [("fighter", 4)], ["squat-nimbleness-xge"], species="dwarf",
             extra={"species": {"id": "dwarf", "subraceId": "hill-dwarf", "choices": {}}})
    assert "squat-nimbleness-xge" in _feat_ids(r), r["pruned"]
    assert _d(r)["speed"] == 25 + 5


def test_mark_of_passage_is_not_offered_by_any_pick_so_its_effect_is_checked_on_the_instance(catalog):
    # Dragonmark feats are not reachable through the ASI gate or any species grant in this app, so the
    # data entry is exercised through the pure engine on the real catalog record.
    inst = fe.instances([catalog.feats["mark-of-passage-efa"]], fed.FEAT_EFFECTS)
    assert fe.walk_bonus(inst) == 5


def test_athlete_xphb_gives_a_climb_speed_equal_to_the_walk_speed(catalog):
    plain = _res(catalog, [("fighter", 4)], ["athlete-xphb"])
    assert "athlete-xphb" in _feat_ids(plain)
    assert _speeds(plain)["climb"] == 30 and "climb" not in _speeds(_res(catalog, [("fighter", 4)]))
    both = _res(catalog, [("fighter", 8)], ["athlete-xphb", "mobile-phb"])
    assert _speeds(both)["walk"] == 40 and _speeds(both)["climb"] == 40


def test_athlete_keeps_a_faster_existing_climb_speed(catalog):
    # Tabaxi: walk 30, climb 20 -> Athlete raises the climb to 30; a faster own climb is kept.
    r = _res(catalog, [("fighter", 4)], ["athlete-xphb"], species="tabaxi-mpmm")
    walk, climb = _speeds(r)["walk"], _speeds(r)["climb"]
    assert climb == max(walk, 20)


def test_triton_barbarian_with_mobile_swim_stays_and_walk_grows(catalog):
    r = _res(catalog, [("barbarian", 5)], ["mobile-phb"], species="triton-mpmm")
    assert _speeds(r)["walk"] == 30 + 10 + 10 and _speeds(r)["swim"] == 30


def test_gift_of_the_depths_swim_includes_the_feat_bonus(catalog):
    d_inv = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
    entries = [
        {"classId": "warlock", "level": 5, "choices": {d_inv: ["opt-gift-of-the-depths-xphb"]}},
    ]
    r = _res(catalog, [("fighter", 4)], ["mobile-phb"], extra={"classes": [
        {"classId": "fighter", "level": 4, "choices": {_asi("fighter", 4): ["feat:mobile-phb"]}}, *entries]},
        ruleset="2024")
    assert _speeds(r)["walk"] == 40 and _speeds(r).get("swim") == 40


# ---------------------------------------------------------------- identity, degrade, stacking helpers


def test_a_featless_character_is_unchanged(catalog):
    r = _res(catalog, [("fighter", 4)], base={"DEX": 14, "CON": 14})
    assert _d(r)["initiative"] == 2 and _d(r)["speed"] == 30 and "climb" not in _speeds(r)


def test_empty_catalog_is_a_no_op():
    bare = load()
    bare = copy.copy(bare)
    bare.feats = {}
    r = _res(bare, [("fighter", 4)], ["alert-phb"], base={"DEX": 14})
    assert _d(r)["initiative"] == 2


def test_numeric_effects_are_deduplicated_by_feat_name():
    table = fed.FEAT_EFFECTS
    feats = [{"index": "alert-phb", "name": "Alert (PHB)", "_asi_cid": "a"},
             {"index": "alert-xphb", "name": "Alert (XPHB)", "_asi_cid": "b"}]
    assert fe.initiative_parts(fe.instances(feats, table)) == (5, False)
    tough = [{"index": "tough-phb", "name": "Tough (PHB)"}, {"index": "tough-xphb", "name": "Tough (XPHB)"}]
    assert fe.hp_bonus(fe.instances(tough, table), 6) == 12


def test_instances_report_the_origin_and_skip_unlisted_feats():
    feats = [{"index": "mobile-phb", "name": "Mobile", "_asi_cid": "c", "_asi_origin": "x:1"},
             {"index": "tough-xphb", "name": "Tough (XPHB)", "_species_origin": "species:s:feat-0"},
             {"index": "alert-xphb", "name": "Alert (XPHB)"},
             {"index": "no-such-feat", "name": "None"}]
    got = fe.instances(feats, fed.FEAT_EFFECTS)
    assert [(i["index"], i["origin"], i["prefix"]) for i in got] == [
        ("mobile-phb", "asi", "x:1"), ("tough-xphb", "species", "species:s:feat-0"),
        ("alert-xphb", "background", "feat:alert-xphb")]


def test_resolve_stays_fast_with_feats(catalog):
    for ruleset, bg in (("mixed", "acolyte"), ("2024", "farmer-xphb")):
        classes = [("fighter", 20)]
        feats = ["alert-phb", "tough-phb", "mobile-phb", "squat-nimbleness-xge"] if ruleset == "mixed" else \
            ["alert-xphb", "speedy-xphb", "athlete-xphb"]
        _res(catalog, classes, feats, ruleset=ruleset, background=bg)
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, classes, feats, ruleset=ruleset, background=bg)
        assert (time.perf_counter() - t) / 10 < 0.05
