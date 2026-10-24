"""W8b (finding F4, book subclass half, part 1: Cleric, Druid and Fighter): the 2014 non-SRD subclass use-limit tail. The
catalog holds no Artificer. Same machinery as W8a (`reference_data.SUBCLASS_TAIL_2014_BOOKS` /
`SUBCLASS_NOTES_2014_BOOKS`, source kind "subclass", mixed / 2014 only, only the selected book subclass, 2024
byte-identical, every entry quotes its catalog text). Written before the data.

Rule matrix (texts read from the catalog on 2026-10-24; `test_quotes_match_catalog` of W8a pins every quote; PB =
proficiency bonus, "mod" = ability modifier):

 Cleric   Warding Flare (Ambition, Light 1), War Priest (War 1), Priest of Zeal (Zeal 1), Solidarity's Action (1), Wrath of
          the Storm (Tempest 1), Eyes of the Grave (Grave 1), Sentinel at Death's Door (Grave 6), Embodiment of the Law
          (Order 6): WIS mod (minimum 1) uses, long rest. Emboldening Bond (Peace 1) and Steps of Night (Twilight 6): PB uses,
          long rest. Blessing of the Forge (1), Eyes of Night (Twilight 1), Blaze of Glory (Zeal 17): 1 use, long rest.
          Visions of the Past (Knowledge 17): 1 use, short or long rest. Divine Strike (8): 1d8 of the domain's damage, 2d8
          from 14 (Death necrotic, Forge fire, Nature cold / fire / lightning, Order psychic, Solidarity / Strength / War /
          Zeal the weapon's type, Tempest thunder, Trickery poison, Twilight radiant). Note-only: Keeper of Souls (Grave
          17), Corona of Light (Light 17), Dampen Elements (Nature 6), Order's Wrath (Order 17, 2d8 psychic).
          Channel Divinity sentences on `cleric:channel-divinity` (level 2 or 6): Invoke Duplicity (Ambition, Trickery; four
          duplicates from 17), Cloak of Shadows (Ambition, Trickery 6), Arcane Abjuration (Arcana; banishment CR 1/2, 1, 2, 3, 4 at
          5, 8, 11, 14, 17), Touch of Death (5 + twice the Cleric level), Artisan's Blessing (100 gp), Path to the Grave,
          Knowledge of the Ages (10 minutes), Read Thoughts (60 feet, 1 minute), Radiance of the Dawn (2d10 + Cleric level),
          Charm Animals and Plants, Order's Demand, Balm of Peace (2d6 + WIS mod, minimum 1), Preserve Life (5 x Cleric
          level), Oketra's / Rhonas's / War God's Blessing (+10), Feat of Strength (+10), Guided Strike (+10), Destructive
          Wrath, Consuming Fervor, Twilight Sanctuary (1d6 + Cleric level temporary hit points).
 Druid    Balm of the Summer Court (Dreams 2): Druid level d6 dice, long rest, half the level spendable; Hidden Paths (10):
          WIS mod (minimum 1) uses, long rest; Walker in Dreams (14): 1 use, long rest; Spirit Totem (Shepherd 2): 1 use, short
          or long rest (bear 5 + level, unicorn level, Guardian Spirit half level from 10); Faithful Summons (14): 1 use,
          long rest; Halo of Spores (Spores 2): 1d4 / 1d6 / 1d8 / 1d10 at 2 / 6 / 10 / 14, spell save DC; Fungal Infestation
          (6): WIS mod (minimum 1) uses, long rest; Star Map (Stars 2) and Cosmic Omen (6): PB uses, long rest; Cauterizing
          Flames (Wildfire 10): PB uses, long rest, 2d10 + WIS mod; Blazing Revival (14): 1 use, long rest. Sentences on Wild
          Shape: Combat Wild Shape, Circle Forms (CR 1, 2, 3, 4, 5, 6 at 2, 6, 9, 12, 15, 18), Elemental Wild Shape (Moon),
          Symbiotic Entity (4 x level temporary hit points; Spreading Spores DC), Starry Form (1d8 + WIS mod, 2d8 from 10),
          Summon Wildfire Spirit (spell save DC, 2d6 fire).
 Fighter  Unwavering Mark (Cavalier 3): STR mod (minimum 1) uses, long rest, half the Fighter level; Warding Maneuver (7): CON
          mod (minimum 1) uses, long rest; Ferocious Charger (15): DC 8 + PB + STR; Manifest Echo (Echo Knight 3): AC 14 + PB;
          Unleash Incarnation (3) and Reclaim Potential (15): CON mod (minimum 1) uses, long rest, 2d6 + CON mod; Echo
          Avatar (7); Shadow Martyr (10): 1 use, short or long rest; Rune Carver (Rune Knight 3): 2 / 3 / 4 / 5 runes at 3 / 7 / 10 /
          15, DC 8 + PB + CON; Giant's Might (3): PB uses, long rest, 1d6 / 1d8 / 1d10 at 3 / 10 / 18; Runic Shield (7): PB uses,
          long rest; Fighting Spirit (Samurai 3): 3 uses, long rest, 5 / 10 / 15 temporary hit points at 3 / 10 / 15; Strength
          before Death (18): 1 use, long rest. Sentences on Second Wind (Rallying Cry: Fighter level), Action Surge (Inspiring
          Surge), Indomitable (Bulwark) for the Purple Dragon Knight.

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (W8 section).
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
CLASSES = {"cleric", "druid", "fighter"}


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
    return {"pb": _pb(res), "wis1": max(1, _mod(res, "WIS")), "con1": max(1, _mod(res, "CON")),
            "str1": max(1, _mod(res, "STR"))}.get(uses, uses)


_DS = [("death-dmg", "Death"), ("forge-xge", "Forge"), ("nature-phb", "Nature"), ("order-tce", "Order"),
       ("solidarity-psa", "Solidarity"), ("strength-psa", "Strength"), ("tempest-phb", "Tempest"),
       ("trickery-phb", "Trickery"), ("twilight-tce", "Twilight"), ("war-phb", "War"), ("zeal-psa", "Zeal")]

# (subclass, class, resource id, first level, uses, recharge)
RESOURCES = [
    ("ambition-psa", "cleric", "cleric:warding-flare", 1, "wis1", "long"),
    ("light-phb", "cleric", "cleric:warding-flare", 1, "wis1", "long"),
    ("war-phb", "cleric", "cleric:war-priest", 1, "wis1", "long"),
    ("zeal-psa", "cleric", "cleric:priest-of-zeal", 1, "wis1", "long"),
    ("solidarity-psa", "cleric", "cleric:solidarity-s-action", 1, "wis1", "long"),
    ("tempest-phb", "cleric", "cleric:wrath-of-the-storm", 1, "wis1", "long"),
    ("grave-xge", "cleric", "cleric:eyes-of-the-grave", 1, "wis1", "long"),
    ("grave-xge", "cleric", "cleric:sentinel-at-death-s-door", 6, "wis1", "long"),
    ("grave-xge", "cleric", "cleric:keeper-of-souls", 17, None, None),
    ("order-tce", "cleric", "cleric:embodiment-of-the-law", 6, "wis1", "long"),
    ("order-tce", "cleric", "cleric:order-s-wrath", 17, None, None),
    ("peace-tce", "cleric", "cleric:emboldening-bond", 1, "pb", "long"),
    ("twilight-tce", "cleric", "cleric:steps-of-night", 6, "pb", "long"),
    ("forge-xge", "cleric", "cleric:blessing-of-the-forge", 1, 1, "long"),
    ("twilight-tce", "cleric", "cleric:eyes-of-night", 1, 1, "long"),
    ("zeal-psa", "cleric", "cleric:blaze-of-glory", 17, 1, "long"),
    ("knowledge-phb", "cleric", "cleric:visions-of-the-past", 17, 1, "short-or-long"),
    ("knowledge-psa", "cleric", "cleric:visions-of-the-past", 17, 1, "short-or-long"),
    ("light-phb", "cleric", "cleric:corona-of-light", 17, None, None),
    ("nature-phb", "cleric", "cleric:dampen-elements", 6, None, None),
    *[(sub, "cleric", f"cleric:divine-strike-{dom.lower()}-domain", 8, None, None) for sub, dom in _DS],
    ("dreams-xge", "druid", "druid:balm-of-the-summer-court", 2, "level", "long"),
    ("dreams-xge", "druid", "druid:hidden-paths", 10, "wis1", "long"),
    ("dreams-xge", "druid", "druid:walker-in-dreams", 14, 1, "long"),
    ("shepherd-xge", "druid", "druid:spirit-totem", 2, 1, "short-or-long"),
    ("shepherd-xge", "druid", "druid:faithful-summons", 14, 1, "long"),
    ("spores-tce", "druid", "druid:halo-of-spores", 2, None, None),
    ("spores-tce", "druid", "druid:fungal-infestation", 6, "wis1", "long"),
    ("stars-tce", "druid", "druid:star-map", 2, "pb", "long"),
    ("stars-tce", "druid", "druid:cosmic-omen", 6, "pb", "long"),
    ("wildfire-tce", "druid", "druid:cauterizing-flames", 10, "pb", "long"),
    ("wildfire-tce", "druid", "druid:blazing-revival", 14, 1, "long"),
    ("cavalier-xge", "fighter", "fighter:unwavering-mark", 3, "str1", "long"),
    ("cavalier-xge", "fighter", "fighter:warding-maneuver", 7, "con1", "long"),
    ("cavalier-xge", "fighter", "fighter:ferocious-charger", 15, None, None),
    ("echo-knight-egw", "fighter", "fighter:manifest-echo", 3, None, None),
    ("echo-knight-egw", "fighter", "fighter:unleash-incarnation", 3, "con1", "long"),
    ("echo-knight-egw", "fighter", "fighter:echo-avatar", 7, None, None),
    ("echo-knight-egw", "fighter", "fighter:shadow-martyr", 10, 1, "short-or-long"),
    ("echo-knight-egw", "fighter", "fighter:reclaim-potential", 15, "con1", "long"),
    ("rune-knight-tce", "fighter", "fighter:rune-carver", 3, None, None),
    ("rune-knight-tce", "fighter", "fighter:giant-s-might", 3, "pb", "long"),
    ("rune-knight-tce", "fighter", "fighter:runic-shield", 7, "pb", "long"),
    ("samurai-xge", "fighter", "fighter:fighting-spirit", 3, 3, "long"),
    ("samurai-xge", "fighter", "fighter:strength-before-death", 18, 1, "long"),
]

# (subclass, class, existing resource id, first level, text the note must hold)
_CD = "cleric:channel-divinity"
NOTES = [
    ("ambition-psa", "cleric", _CD, 2, "Invoke Duplicity"), ("ambition-psa", "cleric", _CD, 6, "Cloak of Shadows"),
    ("arcana-scag", "cleric", _CD, 2, "Arcane Abjuration"), ("death-dmg", "cleric", _CD, 2, "Touch of Death"),
    ("forge-xge", "cleric", _CD, 2, "Artisan's Blessing"), ("grave-xge", "cleric", _CD, 2, "Path to the Grave"),
    ("knowledge-phb", "cleric", _CD, 2, "Knowledge of the Ages"), ("knowledge-phb", "cleric", _CD, 6, "Read Thoughts"),
    ("knowledge-psa", "cleric", _CD, 2, "Knowledge of the Ages"), ("knowledge-psa", "cleric", _CD, 6, "Read Thoughts"),
    ("light-phb", "cleric", _CD, 2, "Radiance of the Dawn"), ("nature-phb", "cleric", _CD, 2, "Charm Animals and Plants"),
    ("order-tce", "cleric", _CD, 2, "Order's Demand"), ("peace-tce", "cleric", _CD, 2, "Balm of Peace"),
    ("solidarity-psa", "cleric", _CD, 2, "Preserve Life"), ("solidarity-psa", "cleric", _CD, 6, "Oketra's Blessing"),
    ("strength-psa", "cleric", _CD, 2, "Feat of Strength"), ("strength-psa", "cleric", _CD, 6, "Rhonas's Blessing"),
    ("tempest-phb", "cleric", _CD, 2, "Destructive Wrath"), ("trickery-phb", "cleric", _CD, 2, "Invoke Duplicity"),
    ("trickery-phb", "cleric", _CD, 6, "Cloak of Shadows"), ("twilight-tce", "cleric", _CD, 2, "Twilight Sanctuary"),
    ("war-phb", "cleric", _CD, 2, "Guided Strike"), ("war-phb", "cleric", _CD, 6, "War God's Blessing"),
    ("zeal-psa", "cleric", _CD, 2, "Consuming Fervor"),
    ("moon-phb", "druid", "druid:wild-shape", 2, "Combat Wild Shape"), ("moon-phb", "druid", "druid:wild-shape", 2, "Circle Forms"),
    ("moon-phb", "druid", "druid:wild-shape", 10, "Elemental Wild Shape"),
    ("spores-tce", "druid", "druid:wild-shape", 2, "Symbiotic Entity"), ("stars-tce", "druid", "druid:wild-shape", 2, "Starry Form"),
    ("wildfire-tce", "druid", "druid:wild-shape", 2, "Summon Wildfire Spirit"),
    ("purple-dragon-knight-scag", "fighter", "fighter:second-wind", 3, "Rallying Cry"),
    ("purple-dragon-knight-scag", "fighter", "fighter:action-surge", 10, "Inspiring Surge"),
    ("purple-dragon-knight-scag", "fighter", "fighter:indomitable", 15, "Bulwark"),
]
# the two Purple Dragon Knight notes need the Fighter resources: Action Surge is level 2, Indomitable level 9


# ---- data pins -----------------------------------------------------------------------------------------------

@needs_data
def test_tables_hold_the_matrix():
    ids = {f"{s['class']}:{_slug(s['name'])}" for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["class"] in CLASSES}
    assert ids >= {r[2] for r in RESOURCES}
    notes = {(s["subclass"], s["target"], s["name"]) for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["class"] in CLASSES}
    assert notes >= {(n[0], n[2], n[4]) for n in NOTES}
    for sub, _cls, _rid, _f, _u, _r in RESOURCES:
        assert sub in {s["subclass"] for s in reference_data.SUBCLASS_TAIL_2014_BOOKS}


@needs_data
def test_every_entry_is_a_non_srd_2014_book_subclass_of_the_three_classes(catalog):
    for spec in reference_data.SUBCLASS_TAIL_2014_BOOKS + reference_data.SUBCLASS_NOTES_2014_BOOKS:
        sub = catalog.subclasses[spec["subclass"]]
        assert sub["ruleset"] == "2014" and sub["source"] != "SRD"
        assert spec["class"] in {"barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
                                 "sorcerer", "warlock", "wizard"}, spec["subclass"]  # W8c / W8d add the rest


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
    expected = max(first, 3) if uses == "level" else _uses(res, uses)
    assert r["uses"] == expected and r["recharge"] == recharge and "unlimited" not in r
    assert r["details"]["note"] and r["id"] == f"{cls}:{_slug(r['name'])}"
    if first > 3:
        assert _entry(_res(catalog, cls, first - 1, sub, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_needs_its_subclass(catalog, sub, cls, rid, first, uses, recharge):
    assert _entry(_res(catalog, cls, 20, None, "mixed"), rid) is None
    other = {"cleric": "life", "druid": "land", "fighter": "champion"}[cls]  # an SRD subclass of the same class
    assert _entry(_res(catalog, cls, 20, other, "mixed"), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,text", NOTES)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, text):
    level = max(first, 3, 9 if rid == "fighter:indomitable" else 0)
    res = _res(catalog, cls, level, sub, ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    if first > 3 and level == first:
        assert text not in (_note(_res(catalog, cls, first - 1, sub, ruleset), rid) or "")
    assert text not in (_note(_res(catalog, cls, 20, None, ruleset), rid) or "")  # no subclass: no note


# ---- numbers: Cleric ---------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("wis", [6, 10, 18])
def test_wisdom_use_counts(catalog, wis):
    for sub, rid in (("light-phb", "cleric:warding-flare"), ("war-phb", "cleric:war-priest"), ("tempest-phb", "cleric:wrath-of-the-storm")):
        res = _res(catalog, "cleric", 6, sub, abilities={"WIS": wis})
        assert _entry(res, rid)["uses"] == max(1, _mod(res, "WIS")), (sub, wis)


@needs_data
@pytest.mark.parametrize("level,dice", [(8, "1d8"), (13, "1d8"), (14, "2d8"), (20, "2d8")])
@pytest.mark.parametrize("sub,dom", _DS)
def test_divine_strike_dice_follow_the_text(catalog, sub, dom, level, dice):
    r = _entry(_res(catalog, "cleric", level, sub), f"cleric:divine-strike-{dom.lower()}-domain")
    assert r["dice"] == dice and f"extra {dice}" in r["details"]["note"]
    assert r["name"] == f"Divine Strike ({dom} Domain)"


@needs_data
@pytest.mark.parametrize("sub,word", [("death-dmg", "necrotic"), ("forge-xge", "fire"), ("nature-phb", "cold, fire or lightning"),
                                       ("order-tce", "psychic"), ("solidarity-psa", "weapon's type"), ("strength-psa", "weapon's type"),
                                       ("tempest-phb", "thunder"), ("trickery-phb", "poison"), ("twilight-tce", "radiant"),
                                       ("war-phb", "weapon's type"), ("zeal-psa", "weapon's type")])
def test_divine_strike_damage_type(catalog, sub, word):
    res = _res(catalog, "cleric", 8, sub)
    n = next(_note(res, r["id"]) for r in res["derived"]["classResources"] if r["name"].startswith("Divine Strike"))
    assert word in n


@needs_data
def test_divine_strike_does_not_feed_the_2024_attack_notes(catalog):
    for sub, _dom in _DS:
        res = _res(catalog, "cleric", 14, sub)
        assert _entry(res, "cleric:divine-strike") is None
        assert all("Divine Strike" not in note for a in res["derived"]["attacks"] for note in a["notes"])


@needs_data
@pytest.mark.parametrize("level", [2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 20])
def test_arcane_abjuration_banishment_follows_the_cr_table(catalog, level):
    n = _note(_res(catalog, "cleric", level, "arcana-scag"), _CD)
    assert "Arcane Abjuration" in n and "turned for 1 minute" in n
    cr = None
    for first, value in ((5, "1/2"), (8, "1"), (11, "2"), (14, "3"), (17, "4")):
        if level >= first:
            cr = value
    if cr is None:
        assert "banished" not in n
    else:
        assert f"challenge rating is {cr} or lower" in n and "banished for 1 minute" in n


@needs_data
@pytest.mark.parametrize("level", [2, 9, 20])
def test_touch_of_death_radiance_and_twilight_sanctuary_use_the_cleric_level(catalog, level):
    assert f"necrotic damage equal to {5 + 2 * level}" in _note(_res(catalog, "cleric", level, "death-dmg"), _CD)
    assert f"radiant damage of 2d10 + {level}" in _note(_res(catalog, "cleric", level, "light-phb"), _CD)
    assert f"grant it 1d6 + {level} temporary hit points" in _note(_res(catalog, "cleric", level, "twilight-tce"), _CD)


@needs_data
@pytest.mark.parametrize("level", [2, 5, 20])
def test_preserve_life_pool_is_five_times_the_level(catalog, level):
    n = _note(_res(catalog, "cleric", max(level, 3), "solidarity-psa"), _CD)
    assert f"{5 * max(level, 3)} hit points" in n and "half" in n and "Preserve Life" in n


@needs_data
@pytest.mark.parametrize("wis", [6, 18])
def test_balm_of_peace_adds_wisdom(catalog, wis):
    res = _res(catalog, "cleric", 3, "peace-tce", abilities={"WIS": wis})
    assert f"2d6 {_mod(res, 'WIS'):+d} hit points (minimum 1 hit point in total)" in _note(res, _CD)


@needs_data
def test_plus_ten_blessings_and_maximum_damage_options(catalog):
    for sub, name in (("solidarity-psa", "Oketra's"), ("strength-psa", "Rhonas's"), ("war-phb", "War God's")):
        n = _note(_res(catalog, "cleric", 6, sub), _CD)
        assert f"{name} Blessing (reaction, 30 feet)" in n and "+10 bonus" in n
    for sub, text in (("strength-psa", "Feat of Strength"), ("war-phb", "Guided Strike")):
        assert "+10 bonus" in _note(_res(catalog, "cleric", 3, sub), _CD).split(text)[1]
    assert "maximum damage" in _note(_res(catalog, "cleric", 3, "tempest-phb"), _CD)
    assert "fire or thunder" in _note(_res(catalog, "cleric", 3, "zeal-psa"), _CD)


@needs_data
def test_improved_duplicity_and_improved_flare_are_extras(catalog):
    for sub in ("ambition-psa", "trickery-phb"):
        assert "four duplicates" not in _note(_res(catalog, "cleric", 16, sub), _CD)
        n = _note(_res(catalog, "cleric", 17, sub), _CD)
        assert "four duplicates" in n and "120 feet" in n
        assert "30 feet" in n.split("Invoke Duplicity")[1]
    assert "Improved Flare" not in _note(_res(catalog, "cleric", 5, "light-phb"), "cleric:warding-flare")
    assert "Improved Flare" in _note(_res(catalog, "cleric", 6, "light-phb"), "cleric:warding-flare")


@needs_data
@pytest.mark.parametrize("wis", [6, 18])
def test_eyes_of_night_and_visions(catalog, wis):
    res = _res(catalog, "cleric", 17, "twilight-tce", abilities={"WIS": wis})
    n = _note(res, "cleric:eyes-of-night")
    assert "300 feet" in n and f"{max(1, _mod(res, 'WIS'))} willing" in n and "1 hour" in n and "spell slot of any level" in n
    v = _note(_res(catalog, "cleric", 17, "knowledge-phb"), "cleric:visions-of-the-past")
    assert "50-foot cube" in v and "Wisdom score" in v


@needs_data
def test_cleric_note_only_resources(catalog):
    assert "Hit Dice" in _note(_res(catalog, "cleric", 17, "grave-xge"), "cleric:keeper-of-souls")
    assert "60-foot radius" in _note(_res(catalog, "cleric", 17, "light-phb"), "cleric:corona-of-light")
    assert "2d8 psychic" in _note(_res(catalog, "cleric", 17, "order-tce"), "cleric:order-s-wrath")
    assert "cold" in _note(_res(catalog, "cleric", 6, "nature-phb"), "cleric:dampen-elements")
    assert "5d10 fire" in _note(_res(catalog, "cleric", 17, "zeal-psa"), "cleric:blaze-of-glory")
    assert "100 gp" in _note(_res(catalog, "cleric", 3, "forge-xge"), _CD)
    assert "+1" in _note(_res(catalog, "cleric", 3, "forge-xge"), "cleric:blessing-of-the-forge")


@needs_data
@pytest.mark.parametrize("level", [3, 10, 20])
def test_emboldening_bond_targets_the_proficiency_bonus(catalog, level):
    res = _res(catalog, "cleric", level, "peace-tce")
    assert f"up to {_pb(res)} willing creatures" in _note(res, "cleric:emboldening-bond")


# ---- numbers: Druid --------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level", [2, 3, 9, 20])
def test_balm_of_the_summer_court_dice_pool(catalog, level):
    r = _entry(_res(catalog, "druid", level, "dreams-xge"), "druid:balm-of-the-summer-court")
    assert r["uses"] == level and r["die"] == "d6" and r["recharge"] == "long"
    assert f"up to {level // 2} of your d6s" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("level,dice", [(2, "1d4"), (5, "1d4"), (6, "1d6"), (9, "1d6"), (10, "1d8"), (13, "1d8"), (14, "1d10"), (20, "1d10")])
def test_halo_of_spores_dice_follow_the_text(catalog, level, dice):
    res = _res(catalog, "druid", level, "spores-tce", abilities={"WIS": 16})
    r = _entry(res, "druid:halo-of-spores")
    assert r["dice"] == dice and f"takes {dice} necrotic" in r["details"]["note"]
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("level,cr,limit", [(2, "1", "no flying or swimming"), (3, "1", "no flying or swimming"), (4, "1", "no flying speed"),
                                           (6, "2", "no flying speed"), (8, "2", "no other limitation"), (9, "3", "no other"),
                                           (12, "4", "no other"), (15, "5", "no other"), (18, "6", "no other"), (20, "6", "no other")])
def test_circle_forms_follow_the_beast_shapes_table(catalog, level, cr, limit):
    n = _note(_res(catalog, "druid", level, "moon-phb"), "druid:wild-shape")
    assert f"challenge rating {cr} or lower ({limit}" in n
    assert n.index("hours") < n.index("Combat Wild Shape") < n.index("Circle Forms")  # the W6 note first


@needs_data
@pytest.mark.parametrize("level", [2, 10, 20])
def test_symbiotic_entity_and_spreading_spores(catalog, level):
    res = _res(catalog, "druid", level, "spores-tce", abilities={"WIS": 18})
    n = _note(res, "druid:wild-shape")
    assert f"{4 * level} temporary hit points" in n and "10 minutes" in n
    assert ("Spreading Spores" in n) == (level >= 10)
    if level >= 10:
        assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n.split("Spreading Spores")[1] and "10-foot cube" in n


@needs_data
@pytest.mark.parametrize("level,dice", [(2, "1d8"), (9, "1d8"), (10, "2d8"), (20, "2d8")])
def test_starry_form_dice(catalog, level, dice):
    res = _res(catalog, "druid", level, "stars-tce", abilities={"WIS": 18})
    n = _note(res, "druid:wild-shape")
    assert f"{dice}{_mod(res, 'WIS'):+d} radiant damage" in n and f"{dice}{_mod(res, 'WIS'):+d} hit points" in n
    assert ("flying speed of 20 feet" in n) == (level >= 10)


@needs_data
def test_wildfire_spirit_cauterizing_flames_and_enhanced_bond(catalog):
    res = _res(catalog, "druid", 10, "wildfire-tce", abilities={"WIS": 18})
    n = _note(res, "druid:wild-shape")
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n and "2d6 fire" in n and "Enhanced Bond" in n
    assert f"damage of 2d10{_mod(res, 'WIS'):+d}" in _note(res, "druid:cauterizing-flames")
    assert "Enhanced Bond" not in _note(_res(catalog, "druid", 5, "wildfire-tce"), "druid:wild-shape")


@needs_data
@pytest.mark.parametrize("level", [2, 10, 20])
def test_spirit_totem_numbers(catalog, level):
    n = _note(_res(catalog, "druid", level, "shepherd-xge"), "druid:spirit-totem")
    assert f"{5 + level} temporary hit points" in n and f"regains {level} hit points" in n and "60 feet" in n
    assert ("Guardian Spirit" in n) == (level >= 10)
    if level >= 10:
        assert f"regains {level // 2} hit points" in n


@needs_data
def test_druid_flat_rules(catalog):
    assert "four beasts" in _note(_res(catalog, "druid", 14, "shepherd-xge"), "druid:faithful-summons")
    assert "60 feet" in _note(_res(catalog, "druid", 10, "dreams-xge"), "druid:hidden-paths")
    assert "scrying" in _note(_res(catalog, "druid", 14, "dreams-xge"), "druid:walker-in-dreams")
    assert "1 hit point" in _note(_res(catalog, "druid", 6, "spores-tce"), "druid:fungal-infestation")
    assert "guiding bolt" in _note(_res(catalog, "druid", 2, "stars-tce"), "druid:star-map")
    assert "d6" in _note(_res(catalog, "druid", 6, "stars-tce"), "druid:cosmic-omen")
    assert "half your hit points" in _note(_res(catalog, "druid", 14, "wildfire-tce"), "druid:blazing-revival")


# ---- numbers: Fighter ------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,str_", [(3, 8), (3, 18), (10, 14), (20, 20)])
def test_unwavering_mark_extra_damage_is_half_the_level(catalog, level, str_):
    res = _res(catalog, "fighter", level, "cavalier-xge", abilities={"STR": str_})
    r = _entry(res, "fighter:unwavering-mark")
    assert r["uses"] == max(1, _mod(res, "STR")) and f"({level // 2})" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("str_", [8, 20])
def test_ferocious_charger_dc(catalog, str_):
    res = _res(catalog, "fighter", 15, "cavalier-xge", abilities={"STR": str_})
    assert f"DC {8 + _pb(res) + _mod(res, 'STR')}" in _note(res, "fighter:ferocious-charger")
    assert "10 feet" in _note(res, "fighter:ferocious-charger")


@needs_data
def test_warding_maneuver(catalog):
    res = _res(catalog, "fighter", 7, "cavalier-xge", abilities={"CON": 18})
    r = _entry(res, "fighter:warding-maneuver")
    assert r["uses"] == _mod(res, "CON") and "1d8" in r["details"]["note"] and "5 feet" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("level", [3, 6, 20])
def test_manifest_echo_armor_class(catalog, level):
    res = _res(catalog, "fighter", level, "echo-knight-egw")
    n = _note(res, "fighter:manifest-echo")
    assert f"AC {14 + _pb(res)}" in n and "15 feet" in n and "30 feet" in n and "1 hit point" in n


@needs_data
@pytest.mark.parametrize("con", [6, 18])
def test_echo_knight_constitution_numbers(catalog, con):
    res = _res(catalog, "fighter", 18, "echo-knight-egw", abilities={"CON": con})
    assert _entry(res, "fighter:unleash-incarnation")["uses"] == max(1, _mod(res, "CON"))
    assert "Legion of One" in _note(res, "fighter:unleash-incarnation")
    assert f"2d6{_mod(res, 'CON'):+d} temporary" in _note(res, "fighter:reclaim-potential")
    assert "Legion of One" not in _note(_res(catalog, "fighter", 17, "echo-knight-egw"), "fighter:unleash-incarnation")


@needs_data
@pytest.mark.parametrize("level,runes", [(3, 2), (6, 2), (7, 3), (9, 3), (10, 4), (14, 4), (15, 5), (20, 5)])
def test_rune_carver_runes_known(catalog, level, runes):
    res = _res(catalog, "fighter", level, "rune-knight-tce", abilities={"CON": 16})
    n = _note(res, "fighter:rune-carver")
    assert f"up to {runes} objects" in n and f"DC {8 + _pb(res) + _mod(res, 'CON')}" in n
    assert ("Master of Runes" in n) == (level >= 15)


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "1d6"), (9, "1d6"), (10, "1d8"), (17, "1d8"), (18, "1d10"), (20, "1d10")])
def test_giants_might_dice(catalog, level, dice):
    r = _entry(_res(catalog, "fighter", level, "rune-knight-tce"), "fighter:giant-s-might")
    assert r["dice"] == dice and f"extra {dice} damage" in r["details"]["note"]
    assert ("Runic Juggernaut" in r["details"]["note"]) == (level >= 18)


@needs_data
@pytest.mark.parametrize("level,thp", [(3, 5), (9, 5), (10, 10), (14, 10), (15, 15), (20, 15)])
def test_fighting_spirit_temporary_hit_points(catalog, level, thp):
    r = _entry(_res(catalog, "fighter", level, "samurai-xge"), "fighter:fighting-spirit")
    assert r["uses"] == 3 and f"{thp} temporary hit points" in r["details"]["note"]
    assert ("Tireless Spirit" in r["details"]["note"]) == (level >= 10)


@needs_data
def test_purple_dragon_knight_notes_follow_the_class_notes(catalog):
    res = _res(catalog, "fighter", 18, "purple-dragon-knight-scag")
    assert "18 hit points" in _note(res, "fighter:second-wind") and "up to three allies" in _note(res, "fighter:second-wind")
    surge = _note(res, "fighter:action-surge")
    assert "one ally within 60 feet" in surge and "two allies within 60 feet" in surge
    assert "Intelligence, Wisdom or Charisma" in _note(res, "fighter:indomitable")
    low = _res(catalog, "fighter", 10, "purple-dragon-knight-scag")
    assert "two allies" not in _note(low, "fighter:action-surge")
    assert _note(low, "fighter:indomitable") is None or "Bulwark" not in _note(low, "fighter:indomitable")


# ---- gates -----------------------------------------------------------------------------------------------------

@needs_data
def test_2024_output_is_independent_of_the_2014_book_tables(catalog, monkeypatch):
    def snapshot():
        return {(sub, cls): copy.deepcopy(_res(catalog, cls, 20, sub, "2024")["derived"]["classResources"])
                for sub, cls in {(r[0], r[1]) for r in RESOURCES} | {(n[0], n[1]) for n in NOTES}}
    before = snapshot()
    monkeypatch.setattr(reference_data, "SUBCLASS_TAIL_2014_BOOKS", ())
    monkeypatch.setattr(reference_data, "SUBCLASS_NOTES_2014_BOOKS", ())
    assert snapshot() == before
    assert _entry(_res(catalog, "druid", 20, "stars-tce", "2014"), "druid:cosmic-omen") is None  # 2014 reads them


@needs_data
def test_srd_xphb_and_unmodelled_book_subclasses_get_no_w8b_entries(catalog):
    new = {r[2] for r in RESOURCES}
    for cls, sub in (("cleric", "life"), ("cleric", "life-xphb"), ("cleric", "light-xphb"), ("druid", "land"), ("druid", "moon-xphb"),
                     ("fighter", "champion"), ("fighter", "battle-master-phb"), ("fighter", "psi-warrior-tce"),
                     ("fighter", "arcane-archer-xge"), ("fighter", "eldritch-knight-phb")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & new, (sub, set(_ids(res)) & new)


@needs_data
def test_multiclass_keeps_each_subclass_with_its_class(catalog):
    res = _res(catalog, "cleric", 6, "war-phb", extra=[{"classId": "druid", "level": 6, "subclassId": "stars-tce", "choices": {}}])
    ids = _ids(res)
    assert "cleric:war-priest" in ids and "druid:cosmic-omen" in ids
    assert ids.index("cleric:war-priest") < ids.index("druid:star-map")


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls, sub in (("cleric", "twilight-tce"), ("cleric", "war-phb"), ("druid", "stars-tce"), ("druid", "moon-phb"),
                     ("fighter", "rune-knight-tce"), ("fighter", "echo-knight-egw")):
        _res(catalog, cls, 20, sub, ruleset)  # warm
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, cls, 20, sub, ruleset)
        assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls, sub)
