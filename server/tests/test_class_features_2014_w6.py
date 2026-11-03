"""W6 (finding F4, class half): the 2014 (SRD) class-feature use-limit tail. SRD class features whose text gives a use
count, a rest rule or a number the character's sheet can compute become class-resource entries
(`reference_data.RESOURCE_TAIL_2014`, note-only when the text has no use count) or a sentence on the existing resource
that the feature spends (`reference_data.RESOURCE_NOTES_2014`). Rulesets "mixed" and "2014" only; "2024" stays
byte-identical. Every entry quotes the catalog text it was built from. Written before the wiring.

Rule matrix (texts read from the catalog on 2026-10-24; `test_quotes_match_catalog` pins every quote):

 Barbarian  Brutal Critical (9/13/17): "roll one additional weapon damage die ... two additional dice at 13th level and
              three additional dice at 17th level" -> note-only, 1 / 2 / 3 dice.
            Relentless Rage (11): "DC 10 Constitution saving throw ... drop to 1 hit point ... after the first, the DC
              increases by 5 ... short or long rest, the DC resets to 10" -> note-only.
 Bard       Song of Rest (2): "extra 1d6 hit points ... 1d8 at 9th level, 1d10 at 13th level, 1d12 at 17th level" ->
              note-only resource with the die. Superior Inspiration (20): note on Bardic Inspiration.
 Cleric     Divine Intervention (10): 1 use, a long rest, "equal to or lower than your cleric level", 7 days after a
              success, automatic at 20. Channel Divinity (2): note with Turn Undead and "the DC equals your cleric spell
              save DC" (8 + PB + WIS).
 Druid      Wild Shape (2): "a number of hours equal to half your druid level (rounded down)" -> note.
 Monk       Deflect Missiles (3) "1d10 + your Dexterity modifier + your monk level", Slow Fall (4) "five times your monk
              level", Stunning Strike (5) 1 ki + Ki save DC "8 + your proficiency bonus + your Wisdom modifier", Empty
              Body (18) 4 / 8 ki: note-only. Ki notes: Flurry of Blows / Patient Defense / Step of the Wind 1 ki (2),
              Diamond Soul 1 ki reroll (14), Perfect Self "regain 4 ki points" (20).
 Paladin    Cleansing Touch (14): "a number of times equal to your Charisma modifier (a minimum of once)", long rest.
            Divine Smite (2): "2d8 for a 1st-level spell slot, plus 1d8 for each spell level higher than 1st, to a
              maximum of 5d8", +1d8 undead / fiend; Improved Divine Smite (11) +1d8. Lay on Hands (1): "expend 5 hit
              points from your pool" for a disease or poison. Channel Divinity (3): "the DC equals your paladin spell
              save DC" (8 + PB + CHA).
 Ranger     Foe Slayer (20): "add your Wisdom modifier to the attack roll or the damage roll".
 Rogue      Stroke of Luck (20): once, "until you finish a short or long rest".
 Sorcerer   Sorcerous Restoration (20): "regain 4 expended sorcery points whenever you finish a short rest" -> note.
 Warlock    Eldritch Master (20): once, a long rest. Mystic Arcanum (11/13/15/17): one cast of each arcanum spell,
              "regain all uses ... long rest" -> uses 1 / 2 / 3 / 4.

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (W6 section).
"""
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

RULESETS_2014 = ["mixed", "2014"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2014", abilities=None, sources=None):
    base = {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": c, "level": lvl, "choices": {}} for c, lvl in classes]
    d = {"ruleset": ruleset, "sources": sources or [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _note(res, rid):
    return ((_entry(res, rid) or {}).get("details") or {}).get("note")


def _mod(res, ability):
    return res["derived"]["abilityModifiers"][ability]


def _pb(res):
    return res["derived"]["proficiencyBonus"]


def _text(catalog, fid):
    rec = catalog.features[fid]
    return " ".join([rec.get("name") or ""] + [x for x in rec["desc"] if isinstance(x, str)])


# (class, resource id, first level, uses, recharge, die)   uses: int, "cha" (max(1, CHA modifier)) or None
NEW = [
    ("barbarian", "barbarian:brutal-critical", 9, None, None, None),
    ("barbarian", "barbarian:relentless-rage", 11, None, None, None),
    ("bard", "bard:song-of-rest", 2, None, None, "d6"),
    ("cleric", "cleric:divine-intervention", 10, 1, "long", None),
    ("monk", "monk:deflect-missiles", 3, None, None, None),
    ("monk", "monk:slow-fall", 4, None, None, None),
    ("monk", "monk:stunning-strike", 5, None, None, None),
    ("monk", "monk:empty-body", 18, None, None, None),
    ("paladin", "paladin:divine-smite", 2, None, None, None),
    ("paladin", "paladin:cleansing-touch", 14, "cha", "long", None),
    ("ranger", "ranger:foe-slayer", 20, 1, "turn", None),  # X2: "Once on each of your turns"
    ("rogue", "rogue:stroke-of-luck", 20, 1, "short-or-long", None),
    ("warlock", "warlock:mystic-arcanum", 11, 1, "long", None),
    ("warlock", "warlock:eldritch-master", 20, 1, "long", None),
]

# (class, existing resource id, first level of the feature that adds the note, text the note must hold)
ATTACHED = [
    ("bard", "bard:bardic-inspiration", 20, "Superior Inspiration"),
    ("cleric", "cleric:channel-divinity", 2, "Turn Undead"),
    ("druid", "druid:wild-shape", 2, "hours"),
    ("monk", "monk:ki", 2, "Flurry of Blows"),
    ("monk", "monk:ki", 14, "Diamond Soul"),
    ("monk", "monk:ki", 20, "Perfect Self"),
    ("paladin", "paladin:lay-on-hands", 1, "disease"),
    ("paladin", "paladin:channel-divinity", 3, "spell save DC"),
    ("sorcerer", "sorcerer:sorcery-points", 20, "Sorcerous Restoration"),
]


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    """Every W6 entry quotes the SRD record text it was built from (verbatim substring of name + desc) and names an
    SRD feature (2014 API url), so no 2024 or book record can leak in."""
    specs = list(reference_data.RESOURCE_TAIL_2014) + list(reference_data.RESOURCE_NOTES_2014)
    assert len(reference_data.RESOURCE_TAIL_2014) == len(NEW)
    assert len(reference_data.RESOURCE_NOTES_2014) == len(ATTACHED)
    for spec in specs:
        assert spec["quotes"], spec["feature"]
        rec = catalog.features[spec["feature"]]
        assert rec["url"].startswith("/api/2014/features/"), spec["feature"]
        for fid, quote in spec["quotes"]:
            assert quote in _text(catalog, fid), (spec["feature"], fid, quote)
            assert catalog.features[fid]["url"].startswith("/api/2014/features/"), fid
        for extra_id, _text_ in spec.get("extras") or ():
            assert catalog.features[extra_id]["url"].startswith("/api/2014/features/"), extra_id
        assert spec["class"] == rec["class"]["index"], spec["feature"]


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for cls, rid, first, _u, _r, _d in NEW:
        spec = next(s for s in reference_data.RESOURCE_TAIL_2014
                    if s["class"] == cls and s["name"].lower().replace(" ", "-") == rid.split(":")[1])
        assert catalog.features[spec["feature"]]["level"] == first, rid
    # the staged records: Brutal Critical 13 / 17, Song of Rest 9 / 13 / 17, Mystic Arcanum 13 / 15 / 17
    for fid, level in (("brutal-critical-2-dice", 13), ("brutal-critical-3-dice", 17), ("song-of-rest-d8", 9),
                       ("song-of-rest-d10", 13), ("song-of-rest-d12", 17), ("mystic-arcanum-7th-level", 13),
                       ("mystic-arcanum-8th-level", 15), ("mystic-arcanum-9th-level", 17)):
        assert catalog.features[fid]["level"] == level, fid


# ---- the new resources: appear at the record's level, with the documented uses -------------------------------

def _expected_uses(res, uses):
    return max(1, _mod(res, "CHA")) if uses == "cha" else uses


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("cls,rid,first,uses,recharge,die", NEW)
def test_resource_appears_at_the_feature_level(catalog, ruleset, cls, rid, first, uses, recharge, die):
    res = _res(catalog, [(cls, first)], ruleset, abilities={"CHA": 16})
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "class"
    assert r["uses"] == _expected_uses(res, uses) and r["recharge"] == recharge and "unlimited" not in r
    assert r.get("die") == die
    assert r["details"]["note"]
    assert _entry(_res(catalog, [(cls, first - 1)], ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("cls,rid,first,text", [(c, r, f, t) for c, r, f, t in ATTACHED])
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, cls, rid, first, text):
    res = _res(catalog, [(cls, first)], ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    if first > 1 and rid not in ("monk:ki", "cleric:channel-divinity", "druid:wild-shape"):
        before = _res(catalog, [(cls, first - 1)], ruleset)
        assert text not in (_note(before, rid) or ""), rid


@needs_data
def test_monk_ki_notes_stack_in_level_order(catalog):
    n2 = _note(_res(catalog, [("monk", 2)]), "monk:ki")
    assert "Flurry of Blows" in n2 and "Patient Defense" in n2 and "Step of the Wind" in n2 and "Diamond Soul" not in n2
    n20 = _note(_res(catalog, [("monk", 20)]), "monk:ki")
    assert n20.index("Flurry of Blows") < n20.index("Diamond Soul") < n20.index("Perfect Self")
    assert "4 ki" in n20  # Perfect Self regains 4


# ---- numbers ---------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,words", [(9, "one additional weapon damage die"), (12, "one additional weapon damage die"),
                                         (13, "two additional weapon damage dice"), (16, "two additional weapon damage dice"),
                                         (17, "three additional weapon damage dice"), (20, "three additional weapon damage dice")])
def test_brutal_critical_dice_follow_the_records(catalog, level, words):
    n = _note(_res(catalog, [("barbarian", level)]), "barbarian:brutal-critical")
    assert words in n
    for other in ("one additional weapon damage die", "two additional weapon damage dice", "three additional weapon damage dice"):
        assert (other in n) == (other == words), (level, n)


@needs_data
def test_relentless_rage_dc_is_ten_plus_five_per_use(catalog):
    n = _note(_res(catalog, [("barbarian", 11)]), "barbarian:relentless-rage")
    assert "DC 10" in n and "+5" in n and "resets to 10" in n and "1 hit point" in n


@needs_data
@pytest.mark.parametrize("level,die", [(2, "d6"), (8, "d6"), (9, "d8"), (12, "d8"), (13, "d10"), (16, "d10"), (17, "d12"), (20, "d12")])
def test_song_of_rest_die_follows_the_records(catalog, level, die):
    res = _res(catalog, [("bard", level)])
    r = _entry(res, "bard:song-of-rest")
    assert r["die"] == die and f"1{die}" in r["details"]["note"] and "short rest" in r["details"]["note"]
    assert "Song of Rest" in resource_line(r) and die in resource_line(r)


@needs_data
@pytest.mark.parametrize("level", [10, 15, 20])
def test_divine_intervention_roll_is_the_cleric_level(catalog, level):
    n = _note(_res(catalog, [("cleric", level)]), "cleric:divine-intervention")
    assert f"{level} or lower" in n and "7 days" in n and "long rest" in n
    assert ("succeeds automatically" in n) == (level == 20)


@needs_data
def test_channel_divinity_turn_undead_dc_uses_wisdom(catalog):
    res = _res(catalog, [("cleric", 5)], abilities={"WIS": 18})
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in _note(res, "cleric:channel-divinity")
    res = _res(catalog, [("paladin", 5)], abilities={"CHA": 16})
    assert f"DC {8 + _pb(res) + _mod(res, 'CHA')}" in _note(res, "paladin:channel-divinity")


@needs_data
@pytest.mark.parametrize("level", [2, 3, 11, 20])
def test_wild_shape_duration_is_half_the_druid_level(catalog, level):
    n = _note(_res(catalog, [("druid", level)]), "druid:wild-shape")
    assert f"lasts {level // 2} hours" in n


@needs_data
@pytest.mark.parametrize("level", [3, 9, 20])
def test_deflect_missiles_numbers(catalog, level):
    res = _res(catalog, [("monk", level)], abilities={"DEX": 16})
    n = _note(res, "monk:deflect-missiles")
    assert f"1d10{_mod(res, 'DEX') + level:+d}" in n and "1 ki point" in n and "20/60" in n


@needs_data
@pytest.mark.parametrize("level", [4, 9, 20])
def test_slow_fall_is_five_times_the_level(catalog, level):
    assert f"by {5 * level}" in _note(_res(catalog, [("monk", level)]), "monk:slow-fall")


@needs_data
@pytest.mark.parametrize("wis", [8, 10, 18])
def test_stunning_strike_dc_is_the_ki_dc(catalog, wis):
    res = _res(catalog, [("monk", 5)], abilities={"WIS": wis})
    n = _note(res, "monk:stunning-strike")
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n and "1 ki point" in n
    assert _entry(res, "monk:ki")["dc"] == 8 + _pb(res) + _mod(res, "WIS")  # the same DC as the Ki resource


@needs_data
def test_empty_body_costs(catalog):
    n = _note(_res(catalog, [("monk", 18)]), "monk:empty-body")
    assert "4 ki points" in n and "8 ki points" in n and "astral projection" in n and "force" in n


@needs_data
@pytest.mark.parametrize("cha", [6, 10, 18])
def test_cleansing_touch_uses_are_the_charisma_modifier_minimum_one(catalog, cha):
    res = _res(catalog, [("paladin", 14)], abilities={"CHA": cha})
    assert _entry(res, "paladin:cleansing-touch")["uses"] == max(1, _mod(res, "CHA"))
    assert "end one spell" in _note(res, "paladin:cleansing-touch")


@needs_data
def test_divine_smite_dice_and_improved_smite(catalog):
    n2 = _note(_res(catalog, [("paladin", 2)]), "paladin:divine-smite")
    assert "2d8" in n2 and "5d8" in n2 and "undead or a fiend" in n2 and "Improved" not in n2
    n11 = _note(_res(catalog, [("paladin", 11)]), "paladin:divine-smite")
    assert "Improved Divine Smite" in n11 and "1d8" in n11


@needs_data
def test_lay_on_hands_note_keeps_the_pool(catalog):
    r = _entry(_res(catalog, [("paladin", 4)]), "paladin:lay-on-hands")
    assert r["pool"] == 20 and r["recharge"] == "long" and "5 hit points" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("wis", [6, 10, 18])
def test_foe_slayer_adds_the_wisdom_modifier(catalog, wis):
    res = _res(catalog, [("ranger", 20)], abilities={"WIS": wis})
    assert f"{_mod(res, 'WIS'):+d}" in _note(res, "ranger:foe-slayer") and "favored enem" in _note(res, "ranger:foe-slayer")


@needs_data
def test_stroke_of_luck_and_eldritch_master_rest_rules(catalog):
    n = _note(_res(catalog, [("rogue", 20)]), "rogue:stroke-of-luck")
    assert "turn the miss into a hit" in n and "treat the d20 roll as a 20" in n
    res = _res(catalog, [("warlock", 20)])
    n = _note(res, "warlock:eldritch-master")
    assert "1 minute" in n and "all your expended Pact Magic" in n and "4" in n  # four slots at 20


@needs_data
@pytest.mark.parametrize("level,uses,spells", [(11, 1, "6th level"), (12, 1, "6th level"), (13, 2, "6th and 7th level"),
                                               (15, 3, "6th, 7th and 8th level"), (17, 4, "6th, 7th, 8th and 9th level"),
                                               (20, 4, "6th, 7th, 8th and 9th level")])
def test_mystic_arcanum_uses_follow_the_records(catalog, level, uses, spells):
    r = _entry(_res(catalog, [("warlock", level)]), "warlock:mystic-arcanum")
    assert r["uses"] == uses and r["recharge"] == "long" and spells in r["details"]["note"]


# ---- gates -----------------------------------------------------------------------------------------------------

@needs_data
def test_2024_output_is_independent_of_the_2014_tables(catalog, monkeypatch):
    """Under ruleset 2024 the 2014 tables are never read: emptying them changes nothing for any class at 20."""
    def snapshot():
        out = {}
        for cls in ("barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer",
                    "warlock", "wizard"):
            out[cls] = copy.deepcopy(_res(catalog, [(cls, 20)], "2024")["derived"]["classResources"])
        return out
    before = snapshot()
    monkeypatch.setattr(reference_data, "RESOURCE_TAIL_2014", ())
    monkeypatch.setattr(reference_data, "RESOURCE_NOTES_2014", ())
    assert snapshot() == before
    # and the 2014 ruleset really reads them (the emptied tables remove the new entries)
    assert _entry(_res(catalog, [("rogue", 20)], "2014"), "rogue:stroke-of-luck") is None


@needs_data
def test_2024_has_no_2014_text(catalog):
    for cls, lvl in (("monk", 20), ("barbarian", 20), ("cleric", 20), ("warlock", 20), ("paladin", 20)):
        res = _res(catalog, [(cls, lvl)], "2024")
        for r in res["derived"]["classResources"]:
            assert "Mystic Arcanum" != r["name"] and "Eldritch Master" != r["name"]
            assert "spell save DC" not in ((r.get("details") or {}).get("note") or "")


@needs_data
def test_multiclass_each_class_gets_its_own_entries(catalog):
    res = _res(catalog, [("rogue", 20), ("bard", 2)])
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert "rogue:stroke-of-luck" in ids and "bard:song-of-rest" in ids
    assert "monk:slow-fall" not in ids


@needs_data
def test_sources_filter_does_not_remove_srd_entries(catalog):
    res = _res(catalog, [("paladin", 14)], "2014", sources=["srd"])
    assert _entry(res, "paladin:cleansing-touch") and _entry(res, "paladin:divine-smite")


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls in ("fighter", "wizard", "bard", "cleric", "warlock"):
        _res(catalog, [(cls, 20)], ruleset)  # warm
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, [(cls, 20)], ruleset)
        assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls)
