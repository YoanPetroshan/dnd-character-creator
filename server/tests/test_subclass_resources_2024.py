"""RP11 (B3): 2024 subclass resource tail. XPHB subclass features whose text gives a use count, a recharge or a
number that spends an existing resource become class-resource entries (`reference_data.SUBCLASS_TAIL_2024`, source
kind "subclass", right after the class's own entries and the R6 subclass entries) or a sentence on that resource
(`reference_data.SUBCLASS_NOTES_2024`). Ruleset "2024" only; mixed and 2014 are untouched (the F0 golden guards the
bytes). Every entry's first level is the XPHB feature record's own level; nothing appears below it. Written before
the wiring.

Rule matrix (texts read from the catalog on 2026-10-23; `test_quotes_match_catalog` pins every quote). Uses:
"a number of times equal to your <X> modifier (minimum of once)" = max(1, X); "once ... can't use it again until you
finish a Long Rest" = 1 use, recharge long; "Short or Long Rest" = short-or-long. "unless you expend/spend ..."
(restores a use) stays in the note.

 Barbarian  Berserker Intimidating Presence (14) 1/long; Zealot Warrior of the Gods (3) pool of d12s, "four d12s ...
            levels 6 (5 dice), 12 (6 dice), and 17 (7 dice)", long; Zealous Presence (10) 1/long; Rage of the Gods (14)
            1/long.
 Bard       Glamour Beguiling Magic (3) 1/long, Mantle of Majesty (6) 1/long, Unbreakable Majesty (14) 1/short-or-long;
            Mantle of Inspiration (3): "up to a number equal to your Charisma modifier (minimum of one creature)",
            note on Bardic Inspiration.
 Cleric     Light Warding Flare (3) WIS (min 1)/long, "regain all expended uses ... Short or Long Rest" from 6; Corona of
            Light (17) WIS/long; War Priest (3) WIS/short-or-long. Channel Divinity notes: Preserve Life 5 x level,
            Radiance of the Dawn 2d10 + level, Guided Strike +10.
 Druid      Moon Moonlight Step (10) WIS/long; Stars Star Map (3) WIS/long, Cosmic Omen (6) WIS/long; Land Natural
            Recovery (6) 1/long twice (Circle Spell, slots); Wild Shape notes: Circle Forms (CR level/3, AC 13 + WIS,
            3 x level Temporary Hit Points), Land's Aid 2d6/3d6 (10)/4d6 (14), Wrath of the Sea WIS d6.
 Fighter    Battle Master Know Your Enemy (7) 1/long (note on Superiority Dice: Relentless d8); Psi Warrior Telekinetic
            Movement (3) and Psi-Powered Leap (7) 1/short-or-long, Bulwark of Force (15) INT (min 1)/long, Telekinetic
            Master (18) 1/long (notes on the dice: Protective Field, Psionic Strike, Telekinetic Thrust DC).
 Monk       Open Hand Wholeness of Body (6) WIS/long; Mercy Flurry of Healing and Harm (11) WIS/long, Hand of Ultimate
            Mercy (17) 1/long; Focus Points notes: Hand of Harm / Hand of Healing, Quivering Palm, Elemental Burst,
            Cloak of Shadows.
 Paladin    Glory Glorious Defense (15) CHA/long, Living Legend (20) 1/long; Devotion Holy Nimbus (20) 1/long; Ancients
            Undying Sentinel (15) and Elder Champion (20) 1/long; Vengeance Avenging Angel (20) 1/long; Channel Divinity
            notes: Sacred Weapon, Inspiring Smite.
 Ranger     Fey Wanderer Fey Reinforcements (11) 1/long, Misty Wanderer (15) WIS/long; Gloom Stalker Dread Ambusher (3)
            WIS/long.
 Rogue      Arcane Trickster Spell Thief (17) 1/long; Soulknife Psychic Veil (13) and Rend Mind (17) 1/long (notes on
            the dice: Psychic Whispers, Psychic Teleportation).
 Sorcerer   Clockwork Restore Balance (3) CHA/long, Trance of Order (14), Clockwork Cavalcade (18); Aberrant Warping
            Implosion (18); Draconic Dragon Wings (14), Dragon Companion (18); Wild Magic Tides of Chaos (3), Tamed
            Surge (18) (all 1/long); Sorcery Points notes: Bastion of Law, Bend Luck, Psionic Sorcery.
 Warlock    Archfey Steps of the Fey (3) CHA/long, Beguiling Defenses (10) 1/long; Celestial Healing Light (3) pool of
            1 + Warlock level d6s, Searing Vengeance (14) 1/long; Fiend Dark One's Own Luck (6) CHA/long, Hurl Through
            Hell (14) 1/long; Great Old One Clairvoyant Combatant (6) 1/short-or-long.
 Wizard     Abjurer Arcane Ward (3) 1/long, HP maximum 2 x level + INT; Diviner Portent (3) two d20s, three from Greater
            Portent (14); The Third Eye (10) 1/short-or-long; Illusionist Phantasmal Creatures (6) 2/long (each spell
            once), Illusory Self (10) 1/short-or-long.

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (RP11 section).
"""
import copy
import re

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


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _res(catalog, cls, level, sub, ruleset="2024", abilities=None, extra=None):
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


def _text(catalog, fid):
    rec = catalog.features[fid]
    return " ".join([rec.get("name") or ""] + [x for x in rec["desc"] if isinstance(x, str)])


# (subclass, class, resource name, first level, uses, recharge)   uses: int or "wis" / "cha" / "int" (min 1)
RESOURCES = [
    ("berserker-xphb", "barbarian", "Intimidating Presence", 14, 1, "long"),
    ("zealot-xphb", "barbarian", "Warrior of the Gods", 3, 4, "long"),
    ("zealot-xphb", "barbarian", "Zealous Presence", 10, 1, "long"),
    ("zealot-xphb", "barbarian", "Rage of the Gods", 14, 1, "long"),
    ("glamour-xphb", "bard", "Beguiling Magic", 3, 1, "long"),
    ("glamour-xphb", "bard", "Mantle of Majesty", 6, 1, "long"),
    ("glamour-xphb", "bard", "Unbreakable Majesty", 14, 1, "short-or-long"),
    ("light-xphb", "cleric", "Warding Flare", 3, "wis", "long"),
    ("light-xphb", "cleric", "Corona of Light", 17, "wis", "long"),
    ("war-xphb", "cleric", "War Priest", 3, "wis", "short-or-long"),
    ("moon-xphb", "druid", "Moonlight Step", 10, "wis", "long"),
    ("stars-xphb", "druid", "Star Map", 3, "wis", "long"),
    ("stars-xphb", "druid", "Cosmic Omen", 6, "wis", "long"),
    ("land-xphb", "druid", "Natural Recovery (Circle Spell)", 6, 1, "long"),
    ("land-xphb", "druid", "Natural Recovery (Spell Slots)", 6, 1, "long"),
    ("battle-master-xphb", "fighter", "Know Your Enemy", 7, 1, "long"),
    ("psi-warrior-xphb", "fighter", "Telekinetic Movement", 3, 1, "short-or-long"),
    ("psi-warrior-xphb", "fighter", "Psi-Powered Leap", 7, 1, "short-or-long"),
    ("psi-warrior-xphb", "fighter", "Bulwark of Force", 15, "int", "long"),
    ("psi-warrior-xphb", "fighter", "Telekinetic Master", 18, 1, "long"),
    ("open-hand-xphb", "monk", "Wholeness of Body", 6, "wis", "long"),
    ("mercy-xphb", "monk", "Flurry of Healing and Harm", 11, "wis", "long"),
    ("mercy-xphb", "monk", "Hand of Ultimate Mercy", 17, 1, "long"),
    ("glory-xphb", "paladin", "Glorious Defense", 15, "cha", "long"),
    ("glory-xphb", "paladin", "Living Legend", 20, 1, "long"),
    ("devotion-xphb", "paladin", "Holy Nimbus", 20, 1, "long"),
    ("ancients-xphb", "paladin", "Undying Sentinel", 15, 1, "long"),
    ("ancients-xphb", "paladin", "Elder Champion", 20, 1, "long"),
    ("vengeance-xphb", "paladin", "Avenging Angel", 20, 1, "long"),
    ("fey-wanderer-xphb", "ranger", "Fey Reinforcements", 11, 1, "long"),
    ("fey-wanderer-xphb", "ranger", "Misty Wanderer", 15, "wis", "long"),
    ("gloom-stalker-xphb", "ranger", "Dread Ambusher", 3, "wis", "long"),
    ("arcane-trickster-xphb", "rogue", "Spell Thief", 17, 1, "long"),
    ("soulknife-xphb", "rogue", "Psychic Veil", 13, 1, "long"),
    ("soulknife-xphb", "rogue", "Rend Mind", 17, 1, "long"),
    ("clockwork-xphb", "sorcerer", "Restore Balance", 3, "cha", "long"),
    ("clockwork-xphb", "sorcerer", "Trance of Order", 14, 1, "long"),
    ("clockwork-xphb", "sorcerer", "Clockwork Cavalcade", 18, 1, "long"),
    ("aberrant-xphb", "sorcerer", "Warping Implosion", 18, 1, "long"),
    ("draconic-xphb", "sorcerer", "Dragon Wings", 14, 1, "long"),
    ("draconic-xphb", "sorcerer", "Dragon Companion", 18, 1, "long"),
    ("wild-magic-xphb", "sorcerer", "Tides of Chaos", 3, 1, "long"),
    ("wild-magic-xphb", "sorcerer", "Tamed Surge", 18, 1, "long"),
    ("archfey-xphb", "warlock", "Steps of the Fey", 3, "cha", "long"),
    ("archfey-xphb", "warlock", "Beguiling Defenses", 10, 1, "long"),
    ("celestial-xphb", "warlock", "Healing Light", 3, 4, "long"),
    ("celestial-xphb", "warlock", "Searing Vengeance", 14, 1, "long"),
    ("fiend-xphb", "warlock", "Dark One's Own Luck", 6, "cha", "long"),
    ("fiend-xphb", "warlock", "Hurl Through Hell", 14, 1, "long"),
    ("great-old-one-xphb", "warlock", "Clairvoyant Combatant", 6, 1, "short-or-long"),
    ("abjurer-xphb", "wizard", "Arcane Ward", 3, 1, "long"),
    ("diviner-xphb", "wizard", "Portent", 3, 2, "long"),
    ("diviner-xphb", "wizard", "The Third Eye", 10, 1, "short-or-long"),
    ("illusionist-xphb", "wizard", "Phantasmal Creatures", 6, 2, "long"),
    ("illusionist-xphb", "wizard", "Illusory Self", 10, 1, "short-or-long"),
]

# Notes added to an existing resource: (subclass, class, target resource id, name in the note, first level)
NOTES = [
    ("glamour-xphb", "bard", "bard:bardic-inspiration", "Mantle of Inspiration", 3),
    ("life-xphb", "cleric", "cleric:channel-divinity", "Preserve Life", 3),
    ("light-xphb", "cleric", "cleric:channel-divinity", "Radiance of the Dawn", 3),
    ("war-xphb", "cleric", "cleric:channel-divinity", "Guided Strike", 3),
    ("moon-xphb", "druid", "druid:wild-shape", "Circle Forms", 3),
    ("land-xphb", "druid", "druid:wild-shape", "Land's Aid", 3),
    ("sea-xphb", "druid", "druid:wild-shape", "Wrath of the Sea", 3),
    ("battle-master-xphb", "fighter", "fighter:superiority-dice", "Relentless", 15),
    ("psi-warrior-xphb", "fighter", "fighter:psionic-energy-dice", "Protective Field", 3),
    ("psi-warrior-xphb", "fighter", "fighter:psionic-energy-dice", "Psionic Strike", 3),
    ("psi-warrior-xphb", "fighter", "fighter:psionic-energy-dice", "Telekinetic Thrust", 7),
    ("soulknife-xphb", "rogue", "rogue:psionic-energy-dice", "Psychic Whispers", 3),
    ("soulknife-xphb", "rogue", "rogue:psionic-energy-dice", "Psychic Teleportation", 9),
    ("mercy-xphb", "monk", "monk:focus-points", "Hand of Harm", 3),
    ("mercy-xphb", "monk", "monk:focus-points", "Hand of Healing", 3),
    ("open-hand-xphb", "monk", "monk:focus-points", "Quivering Palm", 17),
    ("elements-xphb", "monk", "monk:focus-points", "Elemental Burst", 6),
    ("shadow-xphb", "monk", "monk:focus-points", "Cloak of Shadows", 17),
    ("devotion-xphb", "paladin", "paladin:channel-divinity", "Sacred Weapon", 3),
    ("glory-xphb", "paladin", "paladin:channel-divinity", "Inspiring Smite", 3),
    ("clockwork-xphb", "sorcerer", "sorcerer:sorcery-points", "Bastion of Law", 6),
    ("wild-magic-xphb", "sorcerer", "sorcerer:sorcery-points", "Bend Luck", 6),
    ("aberrant-xphb", "sorcerer", "sorcerer:sorcery-points", "Psionic Sorcery", 6),
]


def _rid(cls, name):
    return f"{cls}:{_slug(name)}"


def _want_uses(res, uses):
    if isinstance(uses, int):
        return uses
    return max(1, _mod(res, uses.upper()))


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_table_sizes_match_the_documented_lists():
    assert len(reference_data.SUBCLASS_TAIL_2024) == len(RESOURCES)
    assert len(reference_data.SUBCLASS_NOTES_2024) == len(NOTES)


@needs_data
def test_quotes_match_catalog(catalog):
    """Every entry quotes the XPHB record text it was built from (verbatim substring of name + desc)."""
    for spec in list(reference_data.SUBCLASS_TAIL_2024) + list(reference_data.SUBCLASS_NOTES_2024):
        assert spec["quotes"], spec["feature"]
        for fid, quote in spec["quotes"]:
            assert quote in _text(catalog, fid), (spec["feature"], fid, quote)
        assert spec["feature"] in catalog.features
        record = catalog.features[spec["feature"]]
        assert record["subclass"]["index"] == spec["subclass"] and record["class"]["index"] == spec["class"]
    # tables outside the specs
    zealot = _text(catalog, "zealot-xphb-3-warrior-of-the-gods")
    assert "pool of four d12s" in zealot and "levels 6 (5 dice), 12 (6 dice), and 17 (7 dice)" in zealot
    assert reference_data.ZEALOT_WARRIOR_DICE_2024 == ((3, 4), (6, 5), (12, 6), (17, 7))
    lands = _text(catalog, "land-xphb-3-lands-aid")
    assert "2d6 Necrotic" in lands and "Druid levels 10 (3d6) and 14 (4d6)" in lands
    assert reference_data.LANDS_AID_DICE_2024 == ((3, 2), (10, 3), (14, 4))
    heal = _text(catalog, "celestial-xphb-3-healing-light")
    assert "equals 1 plus your Warlock level" in heal


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for sub, cls, name, first, _uses, _recharge in RESOURCES:
        spec = next(s for s in reference_data.SUBCLASS_TAIL_2024 if s["subclass"] == sub and s["name"] == name)
        assert spec["class"] == cls
        assert catalog.features[spec["feature"]]["level"] == first, name
    for sub, cls, target, name, first in NOTES:
        spec = next(s for s in reference_data.SUBCLASS_NOTES_2024 if s["subclass"] == sub and s["name"] == name)
        assert spec["target"] == target
        assert catalog.features[spec["feature"]]["level"] == first, name


# ---- resources: appear at the record's level, with the uses and recharge of the text -----------------------

def _sub_cases():
    return [pytest.param(*r, id=f"{r[0]}-{_slug(r[2])}") for r in RESOURCES]


@needs_data
@pytest.mark.parametrize("sub,cls,name,first,uses,recharge", _sub_cases())
def test_resource_at_its_level(catalog, sub, cls, name, first, uses, recharge):
    rid = _rid(cls, name)
    assert _entry(_res(catalog, cls, first - 1, sub), rid) is None, "no entry before the record's level"
    res = _res(catalog, cls, first, sub)
    r = _entry(res, rid)
    assert r, rid
    assert r["name"] == name and r["classId"] == cls
    assert r["source"] == {"kind": "subclass", "id": sub, "label": r["source"]["label"]} and r["source"]["label"]
    assert r["recharge"] == recharge and r["uses"] == _want_uses(res, uses)
    assert r["details"]["note"], "a one-sentence rule note is shown"


@needs_data
@pytest.mark.parametrize("sub,cls,name,first,uses", [(s, c, n, f, u) for s, c, n, f, u, _ in RESOURCES if isinstance(u, str)],
                         ids=lambda v: v if isinstance(v, str) else None)
def test_ability_uses_have_a_minimum_of_one(catalog, sub, cls, name, first, uses):
    """"equal to your X modifier (minimum of once)": WIS / CHA / INT 8 gives 1 use; 16 gives the modifier (>= 3)."""
    ability = uses.upper()
    low = _entry(_res(catalog, cls, first, sub, abilities={ability: 8}), _rid(cls, name))
    assert low["uses"] == 1
    res = _res(catalog, cls, first, sub, abilities={ability: 16})
    assert _entry(res, _rid(cls, name))["uses"] == _mod(res, ability) >= 3


# ---- values that follow the level ---------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,dice", [(3, 4), (5, 4), (6, 5), (11, 5), (12, 6), (16, 6), (17, 7), (20, 7)])
def test_zealot_warrior_of_the_gods_pool(catalog, level, dice):
    r = _entry(_res(catalog, "barbarian", level, "zealot-xphb"), "barbarian:warrior-of-the-gods")
    assert (r["uses"], r["die"], r["recharge"]) == (dice, "d12", "long")


@needs_data
@pytest.mark.parametrize("level", [3, 6, 10, 14, 20])
def test_celestial_healing_light_pool_is_one_plus_level(catalog, level):
    res = _res(catalog, "warlock", level, "celestial-xphb", abilities={"CHA": 16})
    r = _entry(res, "warlock:healing-light")
    assert (r["uses"], r["die"]) == (1 + level, "d6")
    assert f"{_mod(res, 'CHA')} dice" in r["details"]["note"]  # "maximum number of dice you can expend at once"


@needs_data
def test_celestial_healing_light_minimum_one_die_at_once(catalog):
    res = _res(catalog, "warlock", 3, "celestial-xphb", abilities={"CHA": 8})
    assert "1 die " in _note(res, "warlock:healing-light") + " "


@needs_data
@pytest.mark.parametrize("level,rolls", [(3, 2), (13, 2), (14, 3), (20, 3)])
def test_diviner_portent_dice(catalog, level, rolls):
    r = _entry(_res(catalog, "wizard", level, "diviner-xphb"), "wizard:portent")
    assert (r["uses"], r["die"], r["recharge"]) == (rolls, "d20", "long")


@needs_data
@pytest.mark.parametrize("level,recharge", [(3, "long"), (5, "long"), (6, "short-or-long"), (20, "short-or-long")])
def test_warding_flare_recharge_follows_improved_warding_flare(catalog, level, recharge):
    """"You regain all expended uses of your Warding Flare when you finish a Short or Long Rest" (Improved, 6)."""
    r = _entry(_res(catalog, "cleric", level, "light-xphb"), "cleric:warding-flare")
    assert r["recharge"] == recharge
    note = r["details"]["note"]
    assert ("2d6" in note) == (level >= 6)


@needs_data
def test_arcane_ward_maximum_scales_with_level_and_intelligence(catalog):
    for level in (3, 11):
        res = _res(catalog, "wizard", level, "abjurer-xphb", abilities={"INT": 16})
        assert f"{2 * level + _mod(res, 'INT')} Hit Points" in _note(res, "wizard:arcane-ward")


@needs_data
def test_computed_numbers_in_resource_notes(catalog):
    res = _res(catalog, "paladin", 20, "ancients-xphb", abilities={"CHA": 16})
    assert "60 Hit Points" in _note(res, "paladin:undying-sentinel") or f"{3 * 20} Hit Points" in _note(res, "paladin:undying-sentinel")
    res = _res(catalog, "paladin", 20, "devotion-xphb", abilities={"CHA": 16})
    assert f"{_mod(res, 'CHA') + _pb(res)} Radiant" in _note(res, "paladin:holy-nimbus")
    res = _res(catalog, "monk", 17, "mercy-xphb", abilities={"WIS": 16})
    assert f"4d10{_mod(res, 'WIS'):+d}" in _note(res, "monk:hand-of-ultimate-mercy")
    res = _res(catalog, "monk", 6, "open-hand-xphb", abilities={"WIS": 16})
    die = _entry(res, "monk:martial-arts")["die"]  # level 6: d8
    assert die == "d8" and f"1{die}{_mod(res, 'WIS'):+d}" in _note(res, "monk:wholeness-of-body")
    res = _res(catalog, "warlock", 14, "celestial-xphb", abilities={"CHA": 16})
    assert f"2d8{_mod(res, 'CHA'):+d}" in _note(res, "warlock:searing-vengeance")
    res = _res(catalog, "barbarian", 14, "berserker-xphb", abilities={"STR": 18})
    assert f"DC {8 + _pb(res) + _mod(res, 'STR')}" in _note(res, "barbarian:intimidating-presence")
    res = _res(catalog, "rogue", 17, "soulknife-xphb", abilities={"DEX": 18})
    assert f"DC {8 + _pb(res) + _mod(res, 'DEX')}" in _note(res, "rogue:rend-mind")
    res = _res(catalog, "ranger", 3, "gloom-stalker-xphb", abilities={"WIS": 16})
    note = _note(res, "ranger:dread-ambusher")
    assert "2d6" in note and f"{_mod(res, 'WIS'):+d}" in note
    assert "2d8" not in note and "2d8" in _note(_res(catalog, "ranger", 11, "gloom-stalker-xphb"), "ranger:dread-ambusher")
    assert "100 Hit Points" in _note(_res(catalog, "sorcerer", 18, "clockwork-xphb"), "sorcerer:clockwork-cavalcade")
    assert "3d10" in _note(_res(catalog, "sorcerer", 18, "aberrant-xphb"), "sorcerer:warping-implosion")
    assert "8d10" in _note(_res(catalog, "warlock", 14, "fiend-xphb"), "warlock:hurl-through-hell")


# ---- notes on existing resources ----------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("sub,cls,target,name,first", NOTES, ids=[f"{n[0]}-{_slug(n[3])}" for n in NOTES])
def test_note_attached_at_its_level(catalog, sub, cls, target, name, first):
    if first > 3:
        assert name not in (_note(_res(catalog, cls, first - 1, sub), target) or "")
    res = _res(catalog, cls, first, sub)
    r = _entry(res, target)
    assert r, target
    assert name in (r["details"]["note"] or ""), (name, r["details"])
    assert not any(x["name"] == name for x in res["derived"]["classResources"]), "a note, not a new resource"


@needs_data
def test_note_numbers(catalog):
    res = _res(catalog, "cleric", 7, "life-xphb")
    assert f"{5 * 7} Hit Points" in _note(res, "cleric:channel-divinity")
    res = _res(catalog, "cleric", 7, "light-xphb")
    assert "2d10 + 7" in _note(res, "cleric:channel-divinity")
    assert "+10" in _note(_res(catalog, "cleric", 3, "war-xphb"), "cleric:channel-divinity")
    res = _res(catalog, "bard", 6, "glamour-xphb", abilities={"CHA": 16})
    assert f"up to {_mod(res, 'CHA')} creatures" in _note(res, "bard:bardic-inspiration")
    res = _res(catalog, "bard", 6, "glamour-xphb", abilities={"CHA": 8})
    assert "up to 1 creature" in _note(res, "bard:bardic-inspiration")
    res = _res(catalog, "druid", 9, "moon-xphb", abilities={"WIS": 16})
    note = _note(res, "druid:wild-shape")
    assert "maximum CR is 3" in note and f"({13 + _mod(res, 'WIS')})" in note and f"{3 * 9} Temporary Hit Points" in note
    for level, dice in ((3, "2d6"), (9, "2d6"), (10, "3d6"), (13, "3d6"), (14, "4d6"), (20, "4d6")):
        assert dice in _note(_res(catalog, "druid", level, "land-xphb"), "druid:wild-shape"), (level, dice)
    res = _res(catalog, "druid", 3, "sea-xphb", abilities={"WIS": 16})
    assert f"{_mod(res, 'WIS')}d6" in _note(res, "druid:wild-shape")
    assert "1d6" in _note(_res(catalog, "druid", 3, "sea-xphb", abilities={"WIS": 8}), "druid:wild-shape")
    assert "1d8" in _note(_res(catalog, "fighter", 15, "battle-master-xphb"), "fighter:superiority-dice")
    res = _res(catalog, "fighter", 7, "psi-warrior-xphb", abilities={"INT": 16})
    note = _note(res, "fighter:psionic-energy-dice")
    assert f"{_mod(res, 'INT'):+d}" in note and f"DC {8 + _pb(res) + _mod(res, 'INT')}" in note
    res = _res(catalog, "rogue", 3, "soulknife-xphb")
    assert f"up to {_pb(res)} creatures" in _note(res, "rogue:psionic-energy-dice")
    assert "10 times" in _note(_res(catalog, "rogue", 9, "soulknife-xphb"), "rogue:psionic-energy-dice")
    res = _res(catalog, "monk", 3, "mercy-xphb", abilities={"WIS": 16})
    assert f"d6{_mod(res, 'WIS'):+d}" in _note(res, "monk:focus-points")
    assert "10d12" in _note(_res(catalog, "monk", 17, "open-hand-xphb"), "monk:focus-points")
    assert "2 Focus Points" in _note(_res(catalog, "monk", 6, "elements-xphb"), "monk:focus-points")
    assert "3 Focus Points" in _note(_res(catalog, "monk", 17, "shadow-xphb"), "monk:focus-points")
    res = _res(catalog, "paladin", 3, "devotion-xphb", abilities={"CHA": 8})
    assert "+1" in _note(res, "paladin:channel-divinity")
    res = _res(catalog, "paladin", 3, "devotion-xphb", abilities={"CHA": 16})
    assert f"+{_mod(res, 'CHA')}" in _note(res, "paladin:channel-divinity")
    assert "2d8 + 9" in _note(_res(catalog, "paladin", 9, "glory-xphb"), "paladin:channel-divinity")
    assert "1 to 5 Sorcery Points" in _note(_res(catalog, "sorcerer", 6, "clockwork-xphb"), "sorcerer:sorcery-points")
    assert "1d4" in _note(_res(catalog, "sorcerer", 6, "wild-magic-xphb"), "sorcerer:sorcery-points")


@needs_data
def test_notes_on_a_class_pool_join_in_order_and_keep_existing_text(catalog):
    """Several notes on one resource join with "; " after what the resource already says."""
    note = _note(_res(catalog, "monk", 3, "mercy-xphb"), "monk:focus-points")
    assert note.index("Hand of Harm") < note.index("Hand of Healing") and "; " in note
    # the Fighter's Psionic Energy Dice keep their R6 numbers
    r = _entry(_res(catalog, "fighter", 7, "psi-warrior-xphb"), "fighter:psionic-energy-dice")
    assert (r["uses"], r["die"]) == (6, "d8") and r["details"]["shortRestRegains"] == 1


# ---- gating, order, multiclass, degrade ---------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_only_ruleset_2024_adds_anything(catalog, ruleset):
    """The same draft under mixed / 2014 shows none of the new entries or notes (D2: gate on 2024 only)."""
    for sub, cls, name, first, _u, _r in RESOURCES:
        res = _res(catalog, cls, 20, sub, ruleset=ruleset)
        assert _entry(res, _rid(cls, name)) is None, (ruleset, name)
    for sub, cls, target, name, first in NOTES:
        res = _res(catalog, cls, 20, sub, ruleset=ruleset)
        assert name not in (_note(res, target) or ""), (ruleset, name)


@needs_data
def test_no_subclass_entry_at_all_without_the_xphb_subclass_under_mixed(catalog):
    res = _res(catalog, "cleric", 20, "light-phb", ruleset="mixed")
    # W8b: the 2014 Light Domain has its own book entries (2014 text), but none of the XPHB ones
    subs = {r["id"] for r in res["derived"]["classResources"] if r["source"]["kind"] == "subclass"}
    assert subs == {"cleric:warding-flare", "cleric:corona-of-light"}
    assert "can't be blinded" in _note(res, "cleric:warding-flare") and _entry(res, "cleric:radiance-of-the-dawn") is None


@needs_data
def test_a_twin_2014_subclass_under_2024_shows_nothing_new(catalog):
    """The 2014 Light Domain is not an XPHB record: no Warding Flare (XPHB), no Corona of Light entry."""
    res = _res(catalog, "cleric", 20, "light-phb", ruleset="2024")
    assert _entry(res, "cleric:warding-flare") is None and _entry(res, "cleric:corona-of-light") is None
    assert "Radiance of the Dawn" not in (_note(res, "cleric:channel-divinity") or "")


@needs_data
def test_other_subclass_of_the_same_class_gets_nothing(catalog):
    res = _res(catalog, "cleric", 20, "life-xphb")
    assert _entry(res, "cleric:warding-flare") is None and _entry(res, "cleric:war-priest") is None
    assert "Preserve Life" in _note(res, "cleric:channel-divinity")
    assert "Radiance of the Dawn" not in _note(res, "cleric:channel-divinity")


@needs_data
def test_no_subclass_selected_gives_nothing(catalog):
    res = _res(catalog, "cleric", 20, None)
    assert not [r for r in res["derived"]["classResources"] if r["source"]["kind"] == "subclass"]


@needs_data
def test_order_class_then_r6_then_the_tail(catalog):
    ids = _ids(_res(catalog, "fighter", 18, "psi-warrior-xphb"))
    assert ids.index("fighter:second-wind") < ids.index("fighter:psionic-energy-dice") < ids.index("fighter:telekinetic-movement")
    assert ids.index("fighter:telekinetic-movement") < ids.index("fighter:psi-powered-leap") < ids.index("fighter:bulwark-of-force")
    ids = _ids(_res(catalog, "cleric", 17, "light-xphb"))
    assert ids.index("cleric:channel-divinity") < ids.index("cleric:warding-flare") < ids.index("cleric:corona-of-light")
    res = _res(catalog, "cleric", 17, "light-xphb")
    assert _entry(res, "cleric:warding-flare")["source"]["kind"] == "subclass"
    assert _entry(res, "cleric:channel-divinity")["source"]["kind"] == "class"


@needs_data
def test_multiclass_each_class_reads_its_own_subclass_and_modifier(catalog):
    extra = [{"classId": "druid", "level": 6, "subclassId": "stars-xphb", "choices": {}}]
    res = _res(catalog, "cleric", 5, "light-xphb", abilities={"WIS": 16}, extra=extra)
    wis = _mod(res, "WIS")
    assert _entry(res, "cleric:warding-flare")["uses"] == wis
    assert _entry(res, "druid:star-map")["uses"] == wis and _entry(res, "druid:cosmic-omen")["uses"] == wis
    ids = _ids(res)
    assert ids.index("cleric:warding-flare") < ids.index("druid:star-map")
    # Channel Divinity note is only on the Cleric pool
    assert "Radiance of the Dawn" in _note(res, "cleric:channel-divinity")


@needs_data
def test_degrades_without_subclass_feature_records(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-xphb-" not in k}
    for sub, cls, name, _f, _u, _r in RESOURCES:
        assert _entry(_res(bare, cls, 20, sub), _rid(cls, name)) is None, name
    for sub, cls, target, name, _f in NOTES:
        r = _entry(_res(bare, cls, 20, sub), target)
        assert name not in ((r or {}).get("details") or {}).get("note", ""), name


@needs_data
def test_exports_print_the_entries_and_notes(catalog):
    res = _res(catalog, "cleric", 7, "light-xphb", abilities={"WIS": 16})
    line = resource_line(_entry(res, "cleric:warding-flare"))
    assert line.startswith("Warding Flare: ") and "кратка или дълга почивка" in line
    cd = resource_line(_entry(res, "cleric:channel-divinity"))
    assert "Radiance of the Dawn" in cd
    pool = resource_line(_entry(_res(catalog, "barbarian", 3, "zealot-xphb"), "barbarian:warrior-of-the-gods"))
    assert "4" in pool and "d12" in pool


@needs_data
def test_resolve_stays_fast_with_the_tail(catalog):
    import time
    cases = [("fighter", "battle-master-xphb"), ("wizard", "diviner-xphb"), ("bard", "glamour-xphb"),
             ("cleric", "light-xphb"), ("warlock", "celestial-xphb"), ("monk", "mercy-xphb"),
             ("paladin", "glory-xphb"), ("druid", "land-xphb"), ("sorcerer", "clockwork-xphb")]
    for ruleset in ("mixed", "2024"):
        for cls, sub in cases:
            d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}},
                 "species": {"id": "human"}, "background": {"id": "acolyte"},
                 "classes": [{"classId": cls, "level": 20, "subclassId": sub, "choices": {}}]}
            resolve(d, catalog)
            t = time.perf_counter()
            for _ in range(10):
                resolve(d, catalog)
            assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls)
