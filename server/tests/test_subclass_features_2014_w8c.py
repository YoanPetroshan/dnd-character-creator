"""W8c (finding F4, book subclass half, part 2a: Monk, Paladin, Ranger and Rogue): the 2014 non-SRD subclass use-limit
tail. Same machinery as W8a / W8b (`reference_data.SUBCLASS_TAIL_2014_BOOKS` / `SUBCLASS_NOTES_2014_BOOKS`, source kind
"subclass", mixed / 2014 only, only the selected book subclass, 2024 byte-identical, every entry quotes its catalog text;
`test_quotes_match_catalog` of W8a pins them). Written before the data.

Rule matrix (texts read from the catalog on 2026-10-24; PB = proficiency bonus, "mod" = ability modifier, "ki DC" = the
Monk's Ki save DC 8 + PB + WIS, pinned from the `ki` record):

 Monk     Ascendant Dragon: Breath of the Dragon (3): PB uses, long rest, two rolls of the Martial Arts die (three from 11),
          ki DC, 2 ki to use it again (Augment Breath 4 rolls as an extra from 17); Draconic Presence (3) 1 use, long rest;
          Wings Unfurled (6) PB uses, long rest; Aspect of the Wyrm (11) 1 use, long rest or 3 ki (Explosive Fury 3d10 from
          17). Astral Self (note-only): Arms (3; 1 ki, two Martial Arts dice), Visage (6; 1 ki), Body (11; 1d10 + WIS mod,
          minimum 1), Awakened (17; 5 ki, +2 AC). Drunken Master: Tipsy Sway (6; 1 ki), Drunkard's Luck (11; 2 ki). Four
          Elements: Disciple of the Elements (3; ki cap 3 / 4 / 5 / 6 at 5 / 9 / 13 / 17). Kensei: Kensei's Shot (3; 1d4),
          Deft Strike (6; 1 ki, Martial Arts die), Sharpen the Blade (11; up to 3 ki). Long Death: Touch of Death (3; WIS mod
          + Monk level temporary hit points, minimum 1), Mastery of Death (11; 1 ki), Touch of the Long Death (17; 1 to 10 ki,
          2d10 per ki, ki DC). Mercy: Hand of Harm and Hand of Healing (3; 1 ki, one Martial Arts die + WIS mod), Hand of
          Ultimate Mercy (17; 1 use, long rest, 5 ki, 4d10 + WIS mod). Shadow: Shadow Arts (3; 2 ki). Sun Soul: Radiant Sun
          Bolt (3; DEX mod, Martial Arts die, 1 ki), Searing Arc Strike (6; 2 ki, at most half the Monk level in ki), Searing
          Sunburst (11; 2d6, +2d6 per ki up to 3, ki DC), Sun Shield (17; 5 + WIS mod radiant).
 Paladin  Undying Sentinel (Ancients 15), Elder Champion (20), Invincible Conqueror (Conquest 20), Exalted Champion (Crown 20),
          Living Legend (Glory 20), Dread Lord (Oathbreaker 20), Avenging Angel (Vengeance 20), Mortal Bulwark (Watchers 20):
          1 use, long rest. Glorious Defense (Glory 15): CHA mod (minimum 1) uses, long rest. Note-only: Aura of Conquest
          (7; half the Paladin level psychic damage, 10 feet, 30 from 18), Scornful Rebuke (15; CHA mod, minimum 1), Aura of
          Hate (7; CHA mod, minimum 1, 10 / 30 feet), Protective Spirit (15; 1d6 + half the level), Aura of the Sentinel (7; PB
          to initiative, 10 / 30 feet), Vigilant Rebuke (15; 2d8 + CHA mod). Channel Divinity sentences on
          `paladin:channel-divinity`: Nature's Wrath, Turn the Faithless, Conquering Presence, Guided Strike (+10), Champion
          Challenge, Turn the Tide (1d6 + CHA mod, minimum 1), Inspiring Smite (2d8 + level), Peerless Athlete, Control Undead
          (CR at least the level is immune), Dreadful Aspect, Emissary of Peace (+5), Rebuke the Violent, Abjure Enemy, Vow of
          Enmity, Abjure the Extraplanar, Watcher's Will (CHA mod, minimum 1, creatures).
 Ranger   Ranger's Companion (Beast Master 3; hit points 4 x level, PB), Drake Companion (Drakewarden 3; 1 use, long rest;
          Magic Fang and Empowered Bite as extras), Drake's Breath (11; 1 use, long rest, 8d6 / 10d6 from 15, spell DC),
          Reflexive Resistance (15; PB uses, long rest), Dreadful Strikes (Fey Wanderer 3; 1d4, 1d6 from 11), Otherworldly
          Glamour (3; WIS mod, minimum 1), Beguiling Twist (7; spell DC), Fey Reinforcements (11; 1 use, long rest), Misty
          Wanderer (15; WIS mod, minimum 1, long rest), Dread Ambusher (Gloom Stalker 3; WIS mod, 1d8), Detect Portal (Horizon
          Walker 3) and Ethereal Step (7): 1 use, short or long rest, Planar Warrior (3; 1d8, 2d8 from 11), Hunter's Sense
          (Monster Slayer 3; WIS mod, minimum 1, long rest), Slayer's Prey (3; 1d6; Supernatural Defense 1d6 as an extra from
          7), Magic-User's Nemesis (11; 1 use, short or long rest, spell DC), Gathered Swarm (Swarmkeeper 3; 1d6, 1d8 from 11,
          spell DC), Writhing Tide (7) and Swarming Dispersal (15): PB uses, long rest.
 Rogue    Spell Thief (Arcane Trickster 17; 1 use, long rest, spell DC with INT), Death Strike (Assassin 17; DC 8 + DEX mod +
          PB), Insightful Fighting (Inquisitive 3; Eye for Weakness 3d6 as an extra from 17), Unerring Eye (13; WIS mod,
          minimum 1, long rest), Wails from the Grave (Phantom 3; PB uses, long rest, half the Sneak Attack dice rounded up),
          Tokens of the Departed (9; PB trinkets), Ghost Walk (13; 1 use, long rest), Psychic Blades (Soulknife 3), Psychic Veil (13; 1 use, long rest), Rend Mind (17; 1
          use, long rest, DC 8 + PB + DEX mod); the R6 `rogue:psionic-energy-dice` resource keeps its builder and gets
          sentences (Psi-Bolstered Knack, Psychic Whispers, Homing Strikes, Psychic Teleportation); Rakish Audacity (Swashbuckler 3; CHA mod to
          initiative), Master Duelist (17; 1 use, short or long rest).

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (W8c section).
"""
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.class_resources import _slug
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

RULESETS_2014 = ["mixed", "2014"]
CLASSES = {"monk", "paladin", "ranger", "rogue"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, cls, level, sub, ruleset="2014", abilities=None, extra=None):
    base = {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}] + (extra or [])
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _ids(res):
    return [r["id"] for r in res["derived"]["classResources"]]


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _note(res, rid):
    return ((_entry(res, rid) or {}).get("details") or {}).get("note")


def _mod(res, ability):
    return res["derived"]["abilityModifiers"][ability]


def _pb(res):
    return res["derived"]["proficiencyBonus"]


def _uses(res, uses):
    return {"pb": _pb(res), "wis1": max(1, _mod(res, "WIS")), "cha1": max(1, _mod(res, "CHA")),
            "two_pb": 2 * _pb(res)}.get(uses, uses)


def _dc(res, ability):
    return 8 + _pb(res) + _mod(res, ability)


# (subclass, class, resource id, first level, uses, recharge)
RESOURCES = [
    ("ascendant-dragon-ftd", "monk", "monk:breath-of-the-dragon", 3, "pb", "long"),
    ("ascendant-dragon-ftd", "monk", "monk:draconic-presence", 3, 1, "long"),
    ("ascendant-dragon-ftd", "monk", "monk:wings-unfurled", 6, "pb", "long"),
    ("ascendant-dragon-ftd", "monk", "monk:aspect-of-the-wyrm", 11, 1, "long"),
    ("astral-self-tce", "monk", "monk:arms-of-the-astral-self", 3, None, None),
    ("astral-self-tce", "monk", "monk:visage-of-the-astral-self", 6, None, None),
    ("astral-self-tce", "monk", "monk:body-of-the-astral-self", 11, None, None),
    ("astral-self-tce", "monk", "monk:awakened-astral-self", 17, None, None),
    ("drunken-master-xge", "monk", "monk:tipsy-sway", 6, None, None),
    ("drunken-master-xge", "monk", "monk:drunkard-s-luck", 11, None, None),
    ("four-elements-phb", "monk", "monk:disciple-of-the-elements", 3, None, None),
    ("kensei-xge", "monk", "monk:kensei-s-shot", 3, None, None),
    ("kensei-xge", "monk", "monk:deft-strike", 6, None, None),
    ("kensei-xge", "monk", "monk:sharpen-the-blade", 11, None, None),
    ("long-death-scag", "monk", "monk:touch-of-death", 3, None, None),
    ("long-death-scag", "monk", "monk:mastery-of-death", 11, None, None),
    ("long-death-scag", "monk", "monk:touch-of-the-long-death", 17, None, None),
    ("mercy-tce", "monk", "monk:hand-of-harm", 3, None, None),
    ("mercy-tce", "monk", "monk:hand-of-healing", 3, None, None),
    ("mercy-tce", "monk", "monk:hand-of-ultimate-mercy", 17, 1, "long"),
    ("shadow-phb", "monk", "monk:shadow-arts", 3, None, None),
    ("sun-soul-xge", "monk", "monk:radiant-sun-bolt", 3, None, None),
    ("sun-soul-xge", "monk", "monk:searing-arc-strike", 6, None, None),
    ("sun-soul-xge", "monk", "monk:searing-sunburst", 11, None, None),
    ("sun-soul-xge", "monk", "monk:sun-shield", 17, None, None),
    ("ancients-phb", "paladin", "paladin:undying-sentinel", 15, 1, "long"),
    ("ancients-phb", "paladin", "paladin:elder-champion", 20, 1, "long"),
    ("conquest-xge", "paladin", "paladin:aura-of-conquest", 7, None, None),
    ("conquest-xge", "paladin", "paladin:scornful-rebuke", 15, None, None),
    ("conquest-xge", "paladin", "paladin:invincible-conqueror", 20, 1, "long"),
    ("crown-scag", "paladin", "paladin:exalted-champion", 20, 1, "long"),
    ("glory-tce", "paladin", "paladin:glorious-defense", 15, "cha1", "long"),
    ("glory-tce", "paladin", "paladin:living-legend", 20, 1, "long"),
    ("oathbreaker-dmg", "paladin", "paladin:aura-of-hate", 7, None, None),
    ("oathbreaker-dmg", "paladin", "paladin:dread-lord", 20, 1, "long"),
    ("redemption-xge", "paladin", "paladin:protective-spirit", 15, None, None),
    ("vengeance-phb", "paladin", "paladin:avenging-angel", 20, 1, "long"),
    ("watchers-tce", "paladin", "paladin:aura-of-the-sentinel", 7, None, None),
    ("watchers-tce", "paladin", "paladin:vigilant-rebuke", 15, None, None),
    ("watchers-tce", "paladin", "paladin:mortal-bulwark", 20, 1, "long"),
    ("beast-master-phb", "ranger", "ranger:ranger-s-companion", 3, None, None),
    ("drakewarden-ftd", "ranger", "ranger:drake-companion", 3, 1, "long"),
    ("drakewarden-ftd", "ranger", "ranger:drake-s-breath", 11, 1, "long"),
    ("drakewarden-ftd", "ranger", "ranger:reflexive-resistance", 15, "pb", "long"),
    ("fey-wanderer-tce", "ranger", "ranger:dreadful-strikes", 3, None, None),
    ("fey-wanderer-tce", "ranger", "ranger:otherworldly-glamour", 3, None, None),
    ("fey-wanderer-tce", "ranger", "ranger:beguiling-twist", 7, None, None),
    ("fey-wanderer-tce", "ranger", "ranger:fey-reinforcements", 11, 1, "long"),
    ("fey-wanderer-tce", "ranger", "ranger:misty-wanderer", 15, "wis1", "long"),
    ("gloom-stalker-xge", "ranger", "ranger:dread-ambusher", 3, None, None),
    ("horizon-walker-xge", "ranger", "ranger:detect-portal", 3, 1, "short-or-long"),
    ("horizon-walker-xge", "ranger", "ranger:planar-warrior", 3, None, None),
    ("horizon-walker-xge", "ranger", "ranger:ethereal-step", 7, 1, "short-or-long"),
    ("monster-slayer-xge", "ranger", "ranger:hunter-s-sense", 3, "wis1", "long"),
    ("monster-slayer-xge", "ranger", "ranger:slayer-s-prey", 3, None, None),
    ("monster-slayer-xge", "ranger", "ranger:magic-user-s-nemesis", 11, 1, "short-or-long"),
    ("swarmkeeper-tce", "ranger", "ranger:gathered-swarm", 3, None, None),
    ("swarmkeeper-tce", "ranger", "ranger:writhing-tide", 7, "pb", "long"),
    ("swarmkeeper-tce", "ranger", "ranger:swarming-dispersal", 15, "pb", "long"),
    ("arcane-trickster-phb", "rogue", "rogue:spell-thief", 17, 1, "long"),
    ("assassin-phb", "rogue", "rogue:death-strike", 17, None, None),
    ("inquisitive-xge", "rogue", "rogue:insightful-fighting", 3, None, None),
    ("inquisitive-xge", "rogue", "rogue:unerring-eye", 13, "wis1", "long"),
    ("phantom-tce", "rogue", "rogue:wails-from-the-grave", 3, "pb", "long"),
    ("phantom-tce", "rogue", "rogue:tokens-of-the-departed", 9, None, None),
    ("phantom-tce", "rogue", "rogue:ghost-walk", 13, 1, "long"),
    ("soulknife-tce", "rogue", "rogue:psychic-blades", 3, None, None),
    ("soulknife-tce", "rogue", "rogue:psychic-veil", 13, 1, "long"),
    ("soulknife-tce", "rogue", "rogue:rend-mind", 17, 1, "long"),
    ("swashbuckler-xge", "rogue", "rogue:rakish-audacity", 3, None, None),
    ("swashbuckler-xge", "rogue", "rogue:master-duelist", 17, 1, "short-or-long"),
]

# (subclass, class, existing resource id, first level, text the note must hold)
_CD = "paladin:channel-divinity"
_PD = "rogue:psionic-energy-dice"  # the R6 Soulknife resource (not duplicated here)
NOTES = [
    ("ancients-phb", "paladin", _CD, 3, "Nature's Wrath"), ("ancients-phb", "paladin", _CD, 3, "Turn the Faithless"),
    ("conquest-xge", "paladin", _CD, 3, "Conquering Presence"), ("conquest-xge", "paladin", _CD, 3, "Guided Strike"),
    ("crown-scag", "paladin", _CD, 3, "Champion Challenge"), ("crown-scag", "paladin", _CD, 3, "Turn the Tide"),
    ("glory-tce", "paladin", _CD, 3, "Inspiring Smite"), ("glory-tce", "paladin", _CD, 3, "Peerless Athlete"),
    ("oathbreaker-dmg", "paladin", _CD, 3, "Control Undead"), ("oathbreaker-dmg", "paladin", _CD, 3, "Dreadful Aspect"),
    ("redemption-xge", "paladin", _CD, 3, "Emissary of Peace"), ("redemption-xge", "paladin", _CD, 3, "Rebuke the Violent"),
    ("vengeance-phb", "paladin", _CD, 3, "Abjure Enemy"), ("vengeance-phb", "paladin", _CD, 3, "Vow of Enmity"),
    ("watchers-tce", "paladin", _CD, 3, "Abjure the Extraplanar"), ("watchers-tce", "paladin", _CD, 3, "Watcher's Will"),
    ("soulknife-tce", "rogue", _PD, 3, "Psi-Bolstered Knack"), ("soulknife-tce", "rogue", _PD, 3, "Psychic Whispers"),
    ("soulknife-tce", "rogue", _PD, 9, "Homing Strikes"), ("soulknife-tce", "rogue", _PD, 9, "Psychic Teleportation"),
]


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_tables_hold_the_matrix():
    ids = {f"{s['class']}:{_slug(s['name'])}" for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["class"] in CLASSES}
    assert ids >= {r[2] for r in RESOURCES}
    notes = {(s["subclass"], s["target"], s["name"]) for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["class"] in CLASSES}
    assert notes >= {(n[0], n[2], n[4]) for n in NOTES}
    # nothing beyond the matrix for these four classes (a new entry needs a matrix row)
    assert ids == {r[2] for r in RESOURCES}
    assert notes == {(n[0], n[2], n[4]) for n in NOTES}


@needs_data
def test_ki_save_dc_is_pinned_from_the_ki_record(catalog):
    """The Monk entries that name the ki save DC quote the class rule it comes from (a record without a subclass)."""
    quoted = [s for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["class"] == "monk"
              and any(fid == "ki" for fid, _q in s["quotes"])]
    assert {s["name"] for s in quoted} >= {"Breath of the Dragon", "Aspect of the Wyrm", "Touch of the Long Death", "Searing Sunburst"}


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for sub, cls, rid, first, _u, _r in RESOURCES:
        spec = next(s for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["subclass"] == sub and s["class"] == cls
                    and f"{cls}:{_slug(s['name'])}" == rid)
        assert catalog.features[spec["feature"]]["level"] == first, (sub, rid)
    for sub, cls, rid, first, text in NOTES:
        spec = next(s for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["subclass"] == sub and s["name"] == text)
        assert catalog.features[spec["feature"]]["level"] == first, (sub, text)


# ---- resources: appear at the record's level for the selected book subclass --------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_appears_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["uses"] == _uses(res, uses) and r["recharge"] == recharge and "unlimited" not in r
    assert r["details"]["note"] and r["id"] == f"{cls}:{_slug(r['name'])}"
    if first > 3:
        assert _entry(_res(catalog, cls, first - 1, sub, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_needs_its_subclass(catalog, sub, cls, rid, first, uses, recharge):
    assert _entry(_res(catalog, cls, 20, None, "mixed"), rid) is None
    other = {"monk": "open-hand", "paladin": "devotion", "ranger": "hunter", "rogue": "thief"}[cls]  # an SRD subclass
    assert _entry(_res(catalog, cls, 20, other, "mixed"), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,text", NOTES)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, text):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    assert text not in (_note(_res(catalog, cls, 20, None, ruleset), rid) or "")  # no subclass: no note
    assert text not in (_note(_res(catalog, cls, 20, "devotion", ruleset), rid) or "")  # an SRD subclass: no note


# ---- numbers: Monk ---------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,rolls", [(3, 2), (10, 2), (11, 3), (16, 3), (17, 3), (20, 3)])
def test_breath_of_the_dragon_rolls_and_dc(catalog, level, rolls):
    res = _res(catalog, "monk", level, "ascendant-dragon-ftd", abilities={"WIS": 16})
    die = _entry(res, "monk:martial-arts")["die"]
    n = _note(res, "monk:breath-of-the-dragon")
    assert f"takes {rolls}{die} damage" in n and f"ki save DC {_dc(res, 'WIS')}" in n and "2 ki points" in n
    assert ("Augment Breath" in n) == (level >= 17)
    if level >= 17:
        assert f"deals 4{die}" in n and "60-foot cone" in n
    wyrm = _note(res, "monk:aspect-of-the-wyrm") if level >= 11 else None
    if wyrm:
        assert f"ki save DC {_dc(res, 'WIS')}" in wyrm and "3 ki points" in wyrm
        assert ("Explosive Fury" in wyrm) == (level >= 17) and ("3d10" in wyrm) == (level >= 17)


@needs_data
def test_dragon_flat_rules(catalog):
    assert "reroll" in _note(_res(catalog, "monk", 3, "ascendant-dragon-ftd"), "monk:draconic-presence")
    assert "flying speed" in _note(_res(catalog, "monk", 6, "ascendant-dragon-ftd"), "monk:wings-unfurled")


@needs_data
@pytest.mark.parametrize("wis", [6, 18])
def test_astral_self_numbers(catalog, wis):
    res = _res(catalog, "monk", 17, "astral-self-tce", abilities={"WIS": wis})
    die = _entry(res, "monk:martial-arts")["die"]
    arms = _note(res, "monk:arms-of-the-astral-self")
    assert "1 ki point" in arms and f"(2{die})" in arms and f"ki save DC {_dc(res, 'WIS')}" in arms and "10 minutes" in arms
    assert "1 ki point" in _note(res, "monk:visage-of-the-astral-self") and "120 feet" in _note(res, "monk:visage-of-the-astral-self")
    body = _note(res, "monk:body-of-the-astral-self")
    assert f"1d10 {_mod(res, 'WIS'):+d} (minimum reduction 1 in total)" in body and f"(1{die})" in body
    awakened = _note(res, "monk:awakened-astral-self")
    assert "5 ki points" in awakened and "+2 bonus to Armor Class" in awakened and "three attacks" in awakened


@needs_data
def test_drunken_master_and_shadow_costs(catalog):
    res = _res(catalog, "monk", 11, "drunken-master-xge")
    assert "1 ki point" in _note(res, "monk:tipsy-sway") and "5 feet" in _note(res, "monk:tipsy-sway")
    assert "2 ki points" in _note(res, "monk:drunkard-s-luck")
    assert "2 ki points" in _note(_res(catalog, "monk", 3, "shadow-phb"), "monk:shadow-arts")


@needs_data
@pytest.mark.parametrize("level,cap", [(3, "can't raise"), (4, "can't raise"), (5, "up to 3 ki"), (8, "up to 3 ki"), (9, "up to 4 ki"),
                                       (12, "up to 4 ki"), (13, "up to 5 ki"), (16, "up to 5 ki"), (17, "up to 6 ki"), (20, "up to 6 ki")])
def test_disciple_of_the_elements_ki_cap_follows_the_table(catalog, level, cap):
    n = _note(_res(catalog, "monk", level, "four-elements-phb"), "monk:disciple-of-the-elements")
    assert cap in n and "picks are not tracked" in n


@needs_data
def test_kensei_numbers(catalog):
    res = _res(catalog, "monk", 11, "kensei-xge")
    die = _entry(res, "monk:martial-arts")["die"]
    assert "1d4" in _note(res, "monk:kensei-s-shot")
    assert "1 ki point" in _note(res, "monk:deft-strike") and f"(1{die})" in _note(res, "monk:deft-strike")
    assert "up to 3 ki points" in _note(res, "monk:sharpen-the-blade") and "1 minute" in _note(res, "monk:sharpen-the-blade")


@needs_data
@pytest.mark.parametrize("level,wis", [(3, 3), (3, 16), (11, 10), (20, 18)])
def test_touch_of_death_temporary_hit_points(catalog, level, wis):
    res = _res(catalog, "monk", level, "long-death-scag", abilities={"WIS": wis})
    assert f"gain {max(1, _mod(res, 'WIS') + level)} temporary hit points" in _note(res, "monk:touch-of-death")


@needs_data
def test_long_death_costs_and_dc(catalog):
    res = _res(catalog, "monk", 17, "long-death-scag", abilities={"WIS": 16})
    assert "1 ki point" in _note(res, "monk:mastery-of-death")
    n = _note(res, "monk:touch-of-the-long-death")
    assert "1 to 10 ki points" in n and "2d10" in n and "20d10" in n and f"ki save DC {_dc(res, 'WIS')}" in n


@needs_data
@pytest.mark.parametrize("wis", [6, 18])
def test_mercy_numbers(catalog, wis):
    res = _res(catalog, "monk", 17, "mercy-tce", abilities={"WIS": wis})
    die = _entry(res, "monk:martial-arts")["die"]
    m = _mod(res, "WIS")
    assert f"(1{die}{m:+d})" in _note(res, "monk:hand-of-harm") and "1 ki point" in _note(res, "monk:hand-of-harm")
    assert f"(1{die}{m:+d})" in _note(res, "monk:hand-of-healing") and "1 ki point" in _note(res, "monk:hand-of-healing")
    u = _note(res, "monk:hand-of-ultimate-mercy")
    assert "5 ki points" in u and f"4d10{m:+d} hit points" in u and "24 hours" in u


@needs_data
@pytest.mark.parametrize("level", [3, 6, 11, 17, 20])
def test_sun_soul_numbers(catalog, level):
    res = _res(catalog, "monk", level, "sun-soul-xge", abilities={"DEX": 16, "WIS": 14})
    die = _entry(res, "monk:martial-arts")["die"]
    bolt = _note(res, "monk:radiant-sun-bolt")
    assert "30 feet" in bolt and f"({die})" in bolt and f"{_mod(res, 'DEX'):+d}" in bolt and "1 ki point" in bolt
    if level >= 6:
        arc = _note(res, "monk:searing-arc-strike")
        assert "2 ki points" in arc and f"{level // 2} ki points in total" in arc and "burning hands" in arc
    if level >= 11:
        sun = _note(res, "monk:searing-sunburst")
        assert "150 feet" in sun and "2d6" in sun and "8d6" in sun and f"ki save DC {_dc(res, 'WIS')}" in sun
    if level >= 17:
        assert f"deal {5 + _mod(res, 'WIS')} radiant damage" in _note(res, "monk:sun-shield")


# ---- numbers: Paladin ------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level", [7, 17, 18, 20])
def test_paladin_auras_follow_the_level(catalog, level):
    feet = 30 if level >= 18 else 10
    res = _res(catalog, "paladin", level, "conquest-xge")
    n = _note(res, "paladin:aura-of-conquest")
    assert f"extends {feet} feet" in n and f"takes {level // 2} psychic damage" in n
    assert f"within {feet} feet of you gain a bonus to melee" in _note(_res(catalog, "paladin", level, "oathbreaker-dmg"), "paladin:aura-of-hate")
    sentinel = _res(catalog, "paladin", level, "watchers-tce")
    assert f"within {feet} feet of you gain a bonus to initiative equal to your proficiency bonus (+{_pb(sentinel)})" in _note(sentinel, "paladin:aura-of-the-sentinel")


@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_charisma_numbers(catalog, cha):
    c = {"CHA": cha}
    res = _res(catalog, "paladin", 20, "conquest-xge", abilities=c)
    assert f"takes {max(1, _mod(res, 'CHA'))} psychic damage" in _note(res, "paladin:scornful-rebuke")
    res = _res(catalog, "paladin", 20, "oathbreaker-dmg", abilities=c)
    assert f"+{max(1, _mod(res, 'CHA'))}" in _note(res, "paladin:aura-of-hate")
    assert f"3d10{_mod(res, 'CHA'):+d} necrotic" in _note(res, "paladin:dread-lord") and "4d10 psychic" in _note(res, "paladin:dread-lord")
    res = _res(catalog, "paladin", 20, "glory-tce", abilities=c)
    r = _entry(res, "paladin:glorious-defense")
    assert r["uses"] == max(1, _mod(res, "CHA")) and f"+{max(1, _mod(res, 'CHA'))}" in r["details"]["note"]
    res = _res(catalog, "paladin", 20, "watchers-tce", abilities=c)
    assert f"2d8{_mod(res, 'CHA'):+d} force" in _note(res, "paladin:vigilant-rebuke")
    assert f"DC {_dc(res, 'CHA')}" in _note(res, "paladin:mortal-bulwark") and "120 feet" in _note(res, "paladin:mortal-bulwark")
    assert f"up to {max(1, _mod(res, 'CHA'))} creatures" in _note(res, _CD)
    res = _res(catalog, "paladin", 20, "crown-scag", abilities=c)
    assert f"1d6 {_mod(res, 'CHA'):+d} hit points (minimum 1" in _note(res, _CD)


@needs_data
@pytest.mark.parametrize("level", [3, 9, 20])
def test_level_numbers_on_the_paladin_options(catalog, level):
    assert f"totalling 2d8 + {level}" in _note(_res(catalog, "paladin", level, "glory-tce"), _CD)
    assert f"challenge rating of {level} or higher" in _note(_res(catalog, "paladin", level, "oathbreaker-dmg"), _CD)
    if level >= 15:
        assert "1d6 + 10 hit points" in _note(_res(catalog, "paladin", level, "redemption-xge"), "paladin:protective-spirit")
    else:
        assert _entry(_res(catalog, "paladin", level, "redemption-xge"), "paladin:protective-spirit") is None


@needs_data
def test_paladin_capstones_and_options(catalog):
    assert "10 hit points" in _note(_res(catalog, "paladin", 20, "ancients-phb"), "paladin:elder-champion")
    assert "19 or 20" in _note(_res(catalog, "paladin", 20, "conquest-xge"), "paladin:invincible-conqueror")
    assert "1 hour" in _note(_res(catalog, "paladin", 20, "crown-scag"), "paladin:exalted-champion")
    assert "5th-level spell slot" in _note(_res(catalog, "paladin", 20, "glory-tce"), "paladin:living-legend")
    assert "60 feet" in _note(_res(catalog, "paladin", 20, "vengeance-phb"), "paladin:avenging-angel")
    assert "1 hit point" in _note(_res(catalog, "paladin", 15, "ancients-phb"), "paladin:undying-sentinel")
    n = _note(_res(catalog, "paladin", 3, "vengeance-phb"), _CD)
    assert "60 feet" in n and "speed is halved" in n and "10 feet" in n
    assert "+10 bonus" in _note(_res(catalog, "paladin", 3, "conquest-xge"), _CD)
    assert "+5 bonus" in _note(_res(catalog, "paladin", 3, "redemption-xge"), _CD)
    assert "24 hours" in _note(_res(catalog, "paladin", 3, "oathbreaker-dmg"), _CD)


@needs_data
def test_paladin_options_follow_the_w6_channel_divinity_note(catalog):
    n = _note(_res(catalog, "paladin", 3, "vengeance-phb", abilities={"CHA": 16}), _CD)
    assert n.index("save DC") < n.index("Abjure Enemy") < n.index("Vow of Enmity")


# ---- numbers: Ranger -------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level", [3, 10, 20])
def test_rangers_companion_hit_points_and_proficiency(catalog, level):
    res = _res(catalog, "ranger", level, "beast-master-phb")
    n = _note(res, "ranger:ranger-s-companion")
    assert f"{4 * level} (four times your Ranger level)" in n and f"+{_pb(res)}" in n and "1/4" in n


@needs_data
@pytest.mark.parametrize("level,dice", [(11, "8d6"), (14, "8d6"), (15, "10d6"), (20, "10d6")])
def test_drakes_breath_dice_and_dc(catalog, level, dice):
    res = _res(catalog, "ranger", level, "drakewarden-ftd", abilities={"WIS": 16})
    r = _entry(res, "ranger:drake-s-breath")
    assert r["dice"] == dice and f"takes {dice} damage" in r["details"]["note"]
    assert f"DC {_dc(res, 'WIS')}" in r["details"]["note"] and "30-foot cone" in r["details"]["note"]


@needs_data
def test_drake_companion_extras(catalog):
    assert "Magic Fang" not in _note(_res(catalog, "ranger", 6, "drakewarden-ftd"), "ranger:drake-companion")
    seven = _note(_res(catalog, "ranger", 7, "drakewarden-ftd"), "ranger:drake-companion")
    assert "Magic Fang" in seven and "1d6" in seven and "Empowered Bite" not in seven
    fifteen = _note(_res(catalog, "ranger", 15, "drakewarden-ftd"), "ranger:drake-companion")
    assert "Empowered Bite" in fifteen and "2d6" in fifteen
    assert "30 feet" in seven and "1st level" in seven


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "1d4"), (10, "1d4"), (11, "1d6"), (20, "1d6")])
def test_dreadful_strikes_dice(catalog, level, dice):
    r = _entry(_res(catalog, "ranger", level, "fey-wanderer-tce"), "ranger:dreadful-strikes")
    assert r["dice"] == dice and f"extra {dice} psychic" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("wis", [6, 18])
def test_wisdom_numbers_of_the_fey_wanderer_gloom_stalker_and_slayer(catalog, wis):
    res = _res(catalog, "ranger", 15, "fey-wanderer-tce", abilities={"WIS": wis})
    assert f"+{max(1, _mod(res, 'WIS'))}" in _note(res, "ranger:otherworldly-glamour")
    assert f"DC {_dc(res, 'WIS')}" in _note(res, "ranger:beguiling-twist") and "120 feet" in _note(res, "ranger:beguiling-twist")
    assert _entry(res, "ranger:misty-wanderer")["uses"] == max(1, _mod(res, "WIS"))
    res = _res(catalog, "ranger", 11, "gloom-stalker-xge", abilities={"WIS": wis})
    n = _note(res, "ranger:dread-ambusher")
    assert f"({_mod(res, 'WIS'):+d})" in n and "10 feet" in n and "1d8" in n
    res = _res(catalog, "ranger", 11, "monster-slayer-xge", abilities={"WIS": wis})
    assert _entry(res, "ranger:hunter-s-sense")["uses"] == max(1, _mod(res, "WIS")) and "60 feet" in _note(res, "ranger:hunter-s-sense")
    assert f"DC {_dc(res, 'WIS')}" in _note(res, "ranger:magic-user-s-nemesis") and "60 feet" in _note(res, "ranger:magic-user-s-nemesis")


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "1d8"), (10, "1d8"), (11, "2d8"), (20, "2d8")])
def test_planar_warrior_dice(catalog, level, dice):
    r = _entry(_res(catalog, "ranger", level, "horizon-walker-xge"), "ranger:planar-warrior")
    assert r["dice"] == dice and f"extra {dice} force" in r["details"]["note"] and "30 feet" in r["details"]["note"]


@needs_data
def test_horizon_walker_flat_rules(catalog):
    res = _res(catalog, "ranger", 7, "horizon-walker-xge")
    assert "1 mile" in _note(res, "ranger:detect-portal") and "etherealness" in _note(res, "ranger:ethereal-step")


@needs_data
def test_slayers_prey_and_supernatural_defense(catalog):
    assert "Supernatural Defense" not in _note(_res(catalog, "ranger", 6, "monster-slayer-xge"), "ranger:slayer-s-prey")
    n = _note(_res(catalog, "ranger", 7, "monster-slayer-xge"), "ranger:slayer-s-prey")
    assert "extra 1d6" in n and "60 feet" in n and "Supernatural Defense: add 1d6" in n


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "1d6"), (10, "1d6"), (11, "1d8"), (20, "1d8")])
def test_gathered_swarm_dice_and_dc(catalog, level, dice):
    res = _res(catalog, "ranger", level, "swarmkeeper-tce", abilities={"WIS": 16})
    r = _entry(res, "ranger:gathered-swarm")
    assert r["dice"] == dice and f"{dice} piercing" in r["details"]["note"] and f"DC {_dc(res, 'WIS')}" in r["details"]["note"]
    assert ("Mighty Swarm" in r["details"]["note"]) == (level >= 11)


# ---- numbers: Rogue --------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("int_", [8, 18])
def test_spell_thief_and_death_strike_dcs(catalog, int_):
    res = _res(catalog, "rogue", 17, "arcane-trickster-phb", abilities={"INT": int_})
    n = _note(res, "rogue:spell-thief")
    assert f"DC {_dc(res, 'INT')}" in n and "8 hours" in n
    res = _res(catalog, "rogue", 17, "assassin-phb", abilities={"DEX": 18})
    assert f"DC {_dc(res, 'DEX')}" in _note(res, "rogue:death-strike") and "doubled" in _note(res, "rogue:death-strike")


@needs_data
def test_inquisitive_numbers(catalog):
    assert "3d6" not in _note(_res(catalog, "rogue", 16, "inquisitive-xge"), "rogue:insightful-fighting")
    n = _note(_res(catalog, "rogue", 17, "inquisitive-xge"), "rogue:insightful-fighting")
    assert "1 minute" in n and "Eye for Weakness" in n and "3d6" in n
    assert "30 feet" in _note(_res(catalog, "rogue", 13, "inquisitive-xge"), "rogue:unerring-eye")


@needs_data
@pytest.mark.parametrize("level", [3, 4, 5, 9, 11, 13, 17, 19, 20])
def test_wails_from_the_grave_is_half_the_sneak_attack_dice_rounded_up(catalog, level):
    res = _res(catalog, "rogue", level, "phantom-tce")
    sneak = int(_entry(res, "rogue:sneak-attack")["dice"].split("d")[0])
    half = (sneak + 1) // 2
    r = _entry(res, "rogue:wails-from-the-grave")
    assert r["dice"] == f"{half}d6" and f"takes {half}d6 necrotic" in r["details"]["note"] and "30 feet" in r["details"]["note"]
    assert ("Death's Friend" in r["details"]["note"]) == (level >= 17)


@needs_data
def test_phantom_flat_rules(catalog):
    res = _res(catalog, "rogue", 13, "phantom-tce")
    assert f"at most {_pb(res)} soul trinkets" in _note(res, "rogue:tokens-of-the-departed")
    g = _note(res, "rogue:ghost-walk")
    assert "10 minutes" in g and "1d10 force" in g and "flying speed of 10 feet" in g


@needs_data
@pytest.mark.parametrize("level", [3, 5, 9, 17])
def test_psionic_energy_dice_stay_the_r6_resource_with_the_powers_as_notes(catalog, level):
    """R6 owns the die resource (twice PB, d6 to d12); W8c only adds the powers' sentences, once."""
    res = _res(catalog, "rogue", level, "soulknife-tce")
    r = _entry(res, "rogue:psionic-energy-dice")
    assert r["uses"] == 2 * _pb(res) and r["details"]["bonusActionRegainsOne"] is True
    assert _ids(res).count("rogue:psionic-energy-dice") == 1
    n = r["details"]["note"]
    assert f"up to {_pb(res)} creatures" in n and "Psi-Bolstered Knack" in n and "1 mile" in n
    assert ("Homing Strikes" in n) == (level >= 9) and ("10 times the number rolled" in n) == (level >= 9)


@needs_data
def test_soulknife_features(catalog):
    res = _res(catalog, "rogue", 17, "soulknife-tce", abilities={"DEX": 18})
    b = _note(res, "rogue:psychic-blades")
    assert "1d6" in b and "1d4" in b and "60 feet" in b
    v = _note(res, "rogue:psychic-veil")
    assert "1 hour" in v and "Psionic Energy die" in v
    m = _note(res, "rogue:rend-mind")
    assert f"DC {_dc(res, 'DEX')}" in m and "three Psionic Energy dice" in m and "1 minute" in m


@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_rakish_audacity_initiative_bonus(catalog, cha):
    res = _res(catalog, "rogue", 3, "swashbuckler-xge", abilities={"CHA": cha})
    n = _note(res, "rogue:rakish-audacity")
    assert f"({_mod(res, 'CHA'):+d})" in n and "within 5 feet" in n


# ---- gates -----------------------------------------------------------------------------------------------

@needs_data
def test_2024_output_is_independent_of_the_2014_book_tables(catalog, monkeypatch):
    def snapshot():
        return {(sub, cls): copy.deepcopy(_res(catalog, cls, 20, sub, "2024")["derived"]["classResources"])
                for sub, cls in {(r[0], r[1]) for r in RESOURCES} | {(n[0], n[1]) for n in NOTES}}
    before = snapshot()
    monkeypatch.setattr(reference_data, "SUBCLASS_TAIL_2014_BOOKS", ())
    monkeypatch.setattr(reference_data, "SUBCLASS_NOTES_2014_BOOKS", ())
    assert snapshot() == before
    assert _entry(_res(catalog, "rogue", 20, "phantom-tce", "2014"), "rogue:ghost-walk") is None  # 2014 reads them


@needs_data
def test_srd_xphb_and_unmodelled_book_subclasses_get_no_w8c_entries(catalog):
    new = {r[2] for r in RESOURCES}
    for cls, sub in (("monk", "open-hand"), ("monk", "mercy-xphb"), ("monk", "shadow-xphb"), ("paladin", "devotion"),
                     ("paladin", "glory-xphb"), ("paladin", "noble-genies-frhof"), ("ranger", "hunter"),
                     ("ranger", "gloom-stalker-xphb"), ("ranger", "winter-walker-frhof"), ("rogue", "thief"),
                     ("rogue", "assassin-xphb"), ("rogue", "scout-xge"), ("rogue", "mastermind-xge")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & new, (sub, set(_ids(res)) & new)
    for n in NOTES:
        assert n[4] not in (_note(_res(catalog, "paladin", 20, "glory-xphb", "mixed"), n[2]) or "")


@needs_data
def test_multiclass_keeps_each_subclass_with_its_class(catalog):
    res = _res(catalog, "monk", 6, "mercy-tce", extra=[{"classId": "rogue", "level": 6, "subclassId": "phantom-tce", "choices": {}},
                                                       {"classId": "ranger", "level": 6, "subclassId": "swarmkeeper-tce", "choices": {}}])
    ids = _ids(res)
    assert "monk:hand-of-harm" in ids and "rogue:wails-from-the-grave" in ids and "ranger:gathered-swarm" in ids
    assert ids.index("monk:hand-of-harm") < ids.index("rogue:wails-from-the-grave")
    assert "rogue:ghost-walk" not in ids and "monk:hand-of-ultimate-mercy" not in ids


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls, sub in (("monk", "astral-self-tce"), ("monk", "ascendant-dragon-ftd"), ("paladin", "oathbreaker-dmg"),
                     ("paladin", "watchers-tce"), ("ranger", "drakewarden-ftd"), ("ranger", "swarmkeeper-tce"),
                     ("rogue", "soulknife-tce"), ("rogue", "phantom-tce")):
        _res(catalog, cls, 20, sub, ruleset)  # warm
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, cls, 20, sub, ruleset)
        assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls, sub)
