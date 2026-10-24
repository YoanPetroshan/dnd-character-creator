"""RP10 (B1): 2024 class-feature numbers as notes. Where the XPHB feature text gives a number or a use rule, it is
attached to the existing class resource's `details.note` (`reference_data.RESOURCE_NOTES_2024`) or shown as a
note-only resource (`uses: None`, no recharge; new entries of `reference_data.RESOURCE_TAIL_2024`, R9 style).
Ruleset "2024" only; mixed and 2014 are untouched (the F0 golden guards the bytes). Written before the wiring.

Rule matrix (texts read from the catalog on 2026-10-23; `test_quotes_match_catalog` pins every quote):

 Barbarian  Relentless Rage (11): "DC 10 Constitution saving throw ... Hit Points instead change to a number equal
              to twice your Barbarian level. Each time you use this feature after the first, the DC increases by 5.
              When you finish a Short or Long Rest, the DC resets to 10." -> note-only resource, 2 x level.
            Brutal Strike (9): "extra 1d10 damage ... one Brutal Strike effect"; Improved Brutal Strike (17):
              "increases to 2d10 ... two different Brutal Strike effects"; (13) adds Staggering / Sundering Blow.
 Bard       Superior Inspiration (18): "you regain expended uses of Bardic Inspiration until you have two" -> note on
              Bardic Inspiration.
 Cleric     Channel Divinity (2): Divine Spark "Roll 1d8 and add your Wisdom modifier ... You roll an additional d8
              when you reach Cleric levels 7 (2d8), 13 (3d8), and 18 (4d8)"; Turn Undead; "the DC equals the spell save
              DC" -> note on Channel Divinity with the dice and DC 8 + PB + WIS.
            Sear Undead (5): "a number of d8s equal to your Wisdom modifier (minimum of 1d8)" -> note-only resource.
 Druid      Archdruid (20) Evergreen Wild Shape: "Whenever you roll Initiative and have no uses of Wild Shape left,
              you regain one expended use of it." -> note on Wild Shape.
 Fighter    Indomitable (9): "reroll it with a bonus equal to your Fighter level" -> note on Indomitable.
            Tactical Mind (2): "you roll 1d10 and add the number rolled to the ability check" -> note on Second Wind.
 Monk       Focus Points DC "8 plus your Wisdom modifier and Proficiency Bonus" (already the resource `dc`).
            Stunning Strike (5), Deflect Attacks (3) "1d10 plus your Dexterity modifier and Monk level", Slow Fall (4)
            "five times your Monk level", Heightened Focus (10) "two rolls of your Martial Arts die", Superior Defense
            (18) "expend 3 Focus Points" -> note-only resources; Perfect Focus (15) "until you have 4 if you have 3 or
            fewer" -> note on Focus Points.
 Paladin    Lay on Hands (1) "expend 5 Hit Points from the pool ... Poisoned"; Restoring Touch (14) 5 Hit Points of the
            pool per condition -> note on Lay on Hands. Abjure Foes (9): "a number of creatures equal to your Charisma
            modifier (minimum of one creature)" -> note-only resource.
 Ranger     Foe Slayer (20): "The damage die of your Hunter's Mark is a d10 rather than a d6." -> note on Favored Enemy.
 Rogue      Cunning Strike (5): "the DC equals 8 plus your Dexterity modifier and Proficiency Bonus"; die costs 1d6;
            Improved (11) two effects; Devious Strikes (14) Daze 2d6, Obscure 3d6, Knock Out 6d6 -> note-only resource.

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (RP10 section).
"""
import copy

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", abilities=None):
    base = {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": c, "level": lvl, "choices": {}} for c, lvl in classes]
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _note(res, rid):
    r = _entry(res, rid)
    return ((r or {}).get("details") or {}).get("note")


def _mod(res, ability):
    return res["derived"]["abilityModifiers"][ability]


def _pb(res):
    return res["derived"]["proficiencyBonus"]


def _text(catalog, fid):
    rec = catalog.features[fid]
    return " ".join([rec.get("name") or ""] + [x for x in rec["desc"] if isinstance(x, str)])


NEW_NOTE_ONLY = [  # (class, resource id, first level)
    ("barbarian", "barbarian:brutal-strike", 9),
    ("barbarian", "barbarian:relentless-rage", 11),
    ("cleric", "cleric:sear-undead", 5),
    ("monk", "monk:deflect-attacks", 3),
    ("monk", "monk:slow-fall", 4),
    ("monk", "monk:stunning-strike", 5),
    ("monk", "monk:heightened-focus", 10),
    ("monk", "monk:superior-defense", 18),
    ("paladin", "paladin:abjure-foes", 9),
    ("rogue", "rogue:cunning-strike", 5),
]

# (class, existing resource id, first level of the feature that adds the note)
ATTACHED = [
    ("bard", "bard:bardic-inspiration", 18),
    ("cleric", "cleric:channel-divinity", 2),
    ("druid", "druid:wild-shape", 20),
    ("fighter", "fighter:indomitable", 9),
    ("fighter", "fighter:second-wind", 2),
    ("monk", "monk:focus-points", 15),
    ("paladin", "paladin:lay-on-hands", 1),
    ("ranger", "ranger:favored-enemy-hunter-s-mark", 20),
]


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    """Every RP10 entry quotes the XPHB record text it was built from (verbatim substring of name + desc)."""
    specs = [s for s in reference_data.RESOURCE_TAIL_2024 if s.get("quotes")] + list(reference_data.RESOURCE_NOTES_2024)
    assert len(specs) == len(NEW_NOTE_ONLY) + len(ATTACHED)
    for spec in specs:
        for fid, quote in spec["quotes"]:
            assert quote in _text(catalog, fid), (spec["feature"], fid, quote)
        assert spec["feature"] in catalog.features
    # the scaling tables outside the specs
    spark = " ".join(x for x in catalog.features["xphb-cleric-2-divine-spark"]["desc"] if isinstance(x, str))
    assert "7 (2d8), 13 (3d8), and 18 (4d8)" in spark
    assert reference_data.DIVINE_SPARK_DICE_2024 == ((7, 2), (13, 3), (18, 4))


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for cls, rid, first in NEW_NOTE_ONLY:
        spec = next(s for s in reference_data.RESOURCE_TAIL_2024 if s["class"] == cls and s.get("quotes")
                    and s["name"].lower().replace(" ", "-") == rid.split(":")[1])
        assert catalog.features[spec["feature"]]["level"] == first, rid
        assert spec["uses"] is None and spec["recharge"] is None


# ---- note-only resources: appear at the record's level, with computed numbers ---------------------------

@needs_data
@pytest.mark.parametrize("cls,rid,first", NEW_NOTE_ONLY)
def test_note_only_resource_appears_at_the_feature_level(catalog, cls, rid, first):
    res = _res(catalog, [(cls, first)])
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "class"
    assert r["uses"] is None and r["recharge"] is None and "unlimited" not in r
    assert r["details"]["note"]
    assert _entry(_res(catalog, [(cls, first - 1)]), rid) is None


@needs_data
@pytest.mark.parametrize("cls,rid,first", NEW_NOTE_ONLY)
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_nothing_outside_ruleset_2024(catalog, ruleset, cls, rid, first):
    r = _entry(_res(catalog, [(cls, 20)], ruleset), rid)
    if r is not None:
        # W6: the SRD class feature of the same name has its own 2014 entry (same id); it must not carry the 2024 text
        assert rid in ("barbarian:relentless-rage", "monk:slow-fall", "monk:stunning-strike"), rid
        assert r["details"]["note"] != _note(_res(catalog, [(cls, 20)], "2024"), rid)


@needs_data
@pytest.mark.parametrize("level", [11, 14, 20])
def test_relentless_rage_hit_points_are_twice_the_level(catalog, level):
    n = _note(_res(catalog, [("barbarian", level)]), "barbarian:relentless-rage")
    assert "DC 10 Constitution" in n and "+5" in n and "resetting to 10" in n
    assert f"become {2 * level}" in n


@needs_data
def test_brutal_strike_die_and_effect_count_follow_the_records(catalog):
    n9 = _note(_res(catalog, [("barbarian", 9)]), "barbarian:brutal-strike")
    assert "1d10" in n9 and "2d10" not in n9 and "one effect" in n9 and "Forceful Blow" in n9 and "Hamstring Blow" in n9
    assert "Staggering Blow" not in n9
    n13 = _note(_res(catalog, [("barbarian", 13)]), "barbarian:brutal-strike")
    assert "Staggering Blow" in n13 and "Sundering Blow" in n13 and "1d10" in n13 and "2d10" not in n13
    n17 = _note(_res(catalog, [("barbarian", 17)]), "barbarian:brutal-strike")
    assert "2d10" in n17 and "1d10" not in n17 and "two different effects" in n17 and "one effect" not in n17


@needs_data
@pytest.mark.parametrize("level", [5, 10])
def test_sear_undead_rolls_wisdom_modifier_minimum_one_d8(catalog, level):
    res = _res(catalog, [("cleric", level)], abilities={"WIS": 6})  # modifier negative -> minimum 1
    assert _mod(res, "WIS") < 0 and "roll 1d8" in _note(res, "cleric:sear-undead")
    res = _res(catalog, [("cleric", level)], abilities={"WIS": 18})
    assert _mod(res, "WIS") == 4 and "roll 4d8" in _note(res, "cleric:sear-undead")


@needs_data
@pytest.mark.parametrize("level,die", [(3, "d6"), (5, "d8"), (10, "d8"), (11, "d10"), (17, "d12")])
def test_deflect_attacks_numbers(catalog, level, die):
    res = _res(catalog, [("monk", level)], abilities={"DEX": 16})
    n = _note(res, "monk:deflect-attacks")
    dex = _mod(res, "DEX")
    assert f"1d10{dex + level:+d}" in n
    assert f"2{die}{dex:+d}" in n and f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n
    assert ("any damage type" in n) == (level >= 13)


@needs_data
@pytest.mark.parametrize("level", [4, 9, 20])
def test_slow_fall_is_five_times_the_level(catalog, level):
    assert f"by {5 * level}" in _note(_res(catalog, [("monk", level)]), "monk:slow-fall")


@needs_data
def test_stunning_strike_and_superior_defense_costs(catalog):
    res = _res(catalog, [("monk", 18)], abilities={"WIS": 16})
    n = _note(res, "monk:stunning-strike")
    assert "1 Focus Point" in n and "Constitution save" in n and f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n
    d = _note(res, "monk:superior-defense")
    assert "3 Focus Points" in d and "all damage except Force" in d and "1 minute" in d


@needs_data
def test_heightened_focus_patient_defense_is_two_martial_arts_dice(catalog):
    # Martial Arts die at Monk 10 is d8 (XPHB), at 11 d10, at 17 d12
    assert "2d8" in _note(_res(catalog, [("monk", 10)]), "monk:heightened-focus")
    assert "2d10" in _note(_res(catalog, [("monk", 11)]), "monk:heightened-focus")
    assert "2d12" in _note(_res(catalog, [("monk", 17)]), "monk:heightened-focus")


@needs_data
@pytest.mark.parametrize("cha,expect", [(6, 1), (10, 1), (16, 3), (20, 5)])
def test_abjure_foes_targets_charisma_modifier_minimum_one(catalog, cha, expect):
    res = _res(catalog, [("paladin", 9)], abilities={"CHA": cha})
    n = _note(res, "paladin:abjure-foes")
    assert f"up to {expect} creature" in n and f"DC {8 + _pb(res) + _mod(res, 'CHA')}" in n
    assert "Channel Divinity" in n


@needs_data
def test_cunning_strike_dc_costs_and_growth(catalog):
    res = _res(catalog, [("rogue", 5)], abilities={"DEX": 18})
    n = _note(res, "rogue:cunning-strike")
    assert f"DC {8 + _pb(res) + _mod(res, 'DEX')}" in n and "Poison 1d6" in n and "Trip 1d6" in n and "Withdraw 1d6" in n
    assert "one effect" in n and "two effects" not in n and "Knock Out" not in n
    n11 = _note(_res(catalog, [("rogue", 11)]), "rogue:cunning-strike")
    assert "two effects" in n11 and "Knock Out" not in n11
    n14 = _note(_res(catalog, [("rogue", 14)]), "rogue:cunning-strike")
    assert "Daze 2d6" in n14 and "Obscure 3d6" in n14 and "Knock Out 6d6" in n14


# ---- notes attached to existing resources -----------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cls,rid,first", ATTACHED)
def test_attached_note_appears_at_its_feature_level(catalog, cls, rid, first):
    assert _note(_res(catalog, [(cls, first)]), rid)
    # the resource itself is the existing one: no duplicate id
    ids = [r["id"] for r in _res(catalog, [(cls, 20)])["derived"]["classResources"]]
    assert ids.count(rid) == 1


@needs_data
@pytest.mark.parametrize("cls,rid,first", ATTACHED)
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_attached_notes_only_under_2024(catalog, ruleset, cls, rid, first):
    res = _res(catalog, [(cls, 20)], ruleset)
    r = _entry(res, rid)
    if r:  # the resource may exist under the SRD chassis; it must carry no RP10 note (W6: its own 2014 note is allowed)
        n2024 = _note(_res(catalog, [(cls, 20)], "2024"), rid)
        assert n2024 and n2024 not in ((r.get("details") or {}).get("note") or "")


@needs_data
def test_superior_inspiration_note_on_bardic_inspiration(catalog):
    assert _note(_res(catalog, [("bard", 17)]), "bard:bardic-inspiration") is None
    r = _entry(_res(catalog, [("bard", 18)]), "bard:bardic-inspiration")
    assert "until you have two" in r["details"]["note"] and r["die"] == "d12"
    assert r["details"].get("spellSlotRegainsUse") is True  # the existing detail is kept


@needs_data
@pytest.mark.parametrize("level,dice", [(2, 1), (6, 1), (7, 2), (12, 2), (13, 3), (17, 3), (18, 4), (20, 4)])
def test_channel_divinity_note_has_divine_spark_dice_and_dc(catalog, level, dice):
    res = _res(catalog, [("cleric", level)], abilities={"WIS": 16})
    r = _entry(res, "cleric:channel-divinity")
    n = r["details"]["note"]
    wis = _mod(res, "WIS")
    assert f"{dice}d8{wis:+d}" in n and f"DC {8 + _pb(res) + wis}" in n and "Turn Undead" in n
    assert r["details"].get("shortRestRegains") == 1  # existing detail kept


@needs_data
def test_channel_divinity_note_not_on_a_non_cleric_pool(catalog):
    res = _res(catalog, [("paladin", 9)])
    assert "Divine Spark" not in (_note(res, "paladin:channel-divinity") or "")


@needs_data
def test_evergreen_wild_shape_note_only_at_20(catalog):
    assert _note(_res(catalog, [("druid", 19)]), "druid:wild-shape") is None
    n = _note(_res(catalog, [("druid", 20)]), "druid:wild-shape")
    assert "Initiative" in n and "no uses left" in n and "one expended use" in n


@needs_data
@pytest.mark.parametrize("level,uses", [(9, 1), (13, 2), (17, 3)])
def test_indomitable_note_adds_fighter_level(catalog, level, uses):
    r = _entry(_res(catalog, [("fighter", level)]), "fighter:indomitable")
    assert r["uses"] == uses and f"+{level}" in r["details"]["note"] and "new roll" in r["details"]["note"]
    assert _note(_res(catalog, [("fighter", 8)]), "fighter:indomitable") is None


@needs_data
def test_tactical_mind_note_on_second_wind_keeps_the_heal(catalog):
    assert _note(_res(catalog, [("fighter", 1)]), "fighter:second-wind") is None
    r = _entry(_res(catalog, [("fighter", 2)]), "fighter:second-wind")
    assert "1d10" in r["details"]["note"] and "ability check" in r["details"]["note"] and "isn't expended" in r["details"]["note"]
    assert r["details"]["heal"] == "1d10+2" and r["details"]["shortRestRegains"] == 1


@needs_data
def test_focus_points_dc_is_already_wisdom_plus_pb_and_perfect_focus_adds_a_note(catalog):
    res = _res(catalog, [("monk", 15)], abilities={"WIS": 16})
    r = _entry(res, "monk:focus-points")
    assert r["dc"] == 8 + _pb(res) + _mod(res, "WIS") and r["uses"] == 15
    assert "have 4" in r["details"]["note"] and "Uncanny Metabolism" in r["details"]["note"]
    assert _note(_res(catalog, [("monk", 14)]), "monk:focus-points") is None


@needs_data
def test_lay_on_hands_notes_poison_and_restoring_touch(catalog):
    r = _entry(_res(catalog, [("paladin", 13)]), "paladin:lay-on-hands")
    assert r["pool"] == 65 and "5 Hit Points" in r["details"]["note"] and "Poisoned" in r["details"]["note"]
    assert "Restoring Touch" not in r["details"]["note"]
    n14 = _entry(_res(catalog, [("paladin", 14)]), "paladin:lay-on-hands")["details"]["note"]
    assert "Restoring Touch" in n14 and "Paralyzed" in n14 and "per condition" in n14


@needs_data
def test_foe_slayer_note_on_favored_enemy(catalog):
    assert _note(_res(catalog, [("ranger", 19)]), "ranger:favored-enemy-hunter-s-mark") is None
    n = _note(_res(catalog, [("ranger", 20)]), "ranger:favored-enemy-hunter-s-mark")
    assert "d10" in n and "d6" in n and "Hunter's Mark" in n


# ---- merge, multiclass, order, degrade, exports, timing --------------------------------------------------

@needs_data
def test_existing_notes_are_kept_and_extended_not_replaced(catalog):
    """A resource that already carries a note (R9 / C6c) keeps it; the RP10 sentence follows after '; '."""
    saved = reference_data.RESOURCE_NOTES_2024
    probe = ({"class": "ranger", "target": "ranger:favored-enemy-hunter-s-mark", "feature": "xphb-ranger-1-favored-enemy",
              "note": "first"}, {"class": "ranger", "target": "ranger:favored-enemy-hunter-s-mark",
                                 "feature": "xphb-ranger-1-favored-enemy", "note": "second"})
    reference_data.RESOURCE_NOTES_2024 = probe
    try:
        n = _note(_res(catalog, [("ranger", 5)]), "ranger:favored-enemy-hunter-s-mark")
    finally:
        reference_data.RESOURCE_NOTES_2024 = saved
    assert n == "first; second"


@needs_data
def test_multiclass_each_class_reads_its_own_level_and_modifier(catalog):
    res = _res(catalog, [("monk", 5), ("rogue", 5), ("paladin", 9)], abilities={"CHA": 18, "DEX": 16})
    assert "1d10" in _note(res, "monk:deflect-attacks") and _note(res, "monk:stunning-strike")
    assert _note(res, "rogue:cunning-strike") and f"up to {_mod(res, 'CHA')} creature" in _note(res, "paladin:abjure-foes")
    # Monk level 5, not total level 19, drives Slow Fall
    assert f"by {5 * 5}" in _note(res, "monk:slow-fall")
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert ids.index("monk:slow-fall") < ids.index("rogue:cunning-strike") < ids.index("paladin:abjure-foes")


@needs_data
def test_monk_20_resource_order_keeps_the_class_builder_first(catalog):
    ids = [r["id"] for r in _res(catalog, [("monk", 20)])["derived"]["classResources"]]
    assert ids[:2] == ["monk:martial-arts", "monk:focus-points"] and ids.index("monk:uncanny-metabolism") > 1


@needs_data
def test_degrades_without_xphb_feature_records(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith("xphb-")}
    bare.class_2024_tables = {}
    for cls, rid, _ in NEW_NOTE_ONLY:
        assert _entry(_res(bare, [(cls, 20)]), rid) is None
    for cls, rid, _ in ATTACHED:
        r = _entry(_res(bare, [(cls, 20)]), rid)
        assert not r or "note" not in (r.get("details") or {}), rid


@needs_data
def test_exports_print_the_notes(catalog):
    res = _res(catalog, [("barbarian", 11)])
    line = resource_line(_entry(res, "barbarian:relentless-rage"))
    assert line.startswith("Relentless Rage: ") and "become 22" in line
    cd = resource_line(_entry(_res(catalog, [("cleric", 7)]), "cleric:channel-divinity"))
    assert "Divine Spark" in cd and "използване се възстановява при кратка почивка" in cd


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2024"])
def test_resolve_stays_fast_with_the_notes(catalog, ruleset):
    import time
    for cls in ("fighter", "wizard", "bard", "monk", "rogue", "paladin", "cleric", "barbarian"):
        d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}},
             "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": [{"classId": cls, "level": 20, "choices": {}}]}
        resolve(d, catalog)
        t = time.perf_counter()
        for _ in range(10):
            resolve(d, catalog)
        assert (time.perf_counter() - t) / 10 < 0.05, cls
