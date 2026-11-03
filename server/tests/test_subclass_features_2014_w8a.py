"""W8a (finding F4, book subclass half, part 1: Barbarian and Bard): the 2014 non-SRD subclass use-limit tail.
Book subclass features (PHB / XGE / TCE / SCAG / VRGR / BGG ...) whose text gives a use count, a rest rule, dice, a DC or
a number the sheet can compute become subclass resources (`reference_data.SUBCLASS_TAIL_2014_BOOKS`, source kind "subclass",
after the class's own entries and the R6 subclass entries) or a sentence on the resource the feature spends
(`reference_data.SUBCLASS_NOTES_2014_BOOKS`). Rulesets "mixed" and "2014" only, only for the selected book subclass; "2024"
stays byte-identical. Every entry quotes the catalog text it was built from. Written before the wiring.

Rule matrix (texts read from the catalog on 2026-10-24; `test_quotes_match_catalog` pins every quote; PB = proficiency
bonus; "mod" = ability modifier):

 Ancestral Guardian   Spirit Shield (6): reaction, 2d6, 3d6 at 10, 4d6 at 14; Vengeful Ancestors (14) force damage equal to the
                      damage prevented. Consult the Spirits (10): 1 use, short or long rest.
 Battlerager          Battlerager Armor (3): 1d4 piercing, grapple 3 piercing; Reckless Abandon (6): CON mod (minimum 1)
                      temporary hit points; Spiked Retribution (14): 3 piercing.
 Beast                Form of the Beast (3): bite 1d8 + PB hit points, claws 1d6, tail 1d8 + d8 AC; Infectious Fury (10):
                      PB uses, long rest, DC 8 + CON + PB, 2d12 psychic; Call the Hunt (14): PB uses, long rest, CON mod
                      (minimum 1) creatures, 5 temporary hit points each, d6.
 Giant                Elemental Cleaver (6): 1d6, 2d6 at 14; Mighty Impel (10): DC 8 + PB + STR.
 Storm Herald         Storm Aura (3): DC 8 + PB + CON; desert 2/3/4/5/6 at 3/5/10/15/20, sea 1d6/2d6/3d6/4d6 at 3/10/15/20,
                      tundra 2/3/4/5/6; Raging Storm (14) desert: half the Barbarian level.
 Wild Magic           Magic Awareness (3): PB uses, long rest; Wild Surge (3): DC 8 + PB + CON; Bolstering Magic (6): PB uses,
                      long rest.
 Zealot               Divine Fury (3): 1d6 + half the Barbarian level; Fanatical Focus (6): once per rage; Zealous Presence
                      (10): 1 use, long rest.
 Creation (Bard)      Performance of Creation (3): 1 use, long rest, 20 x Bard level gp, PB hours, Medium / Large 6 / Huge 14,
                      Creative Crescendo (14): CHA mod (minimum 2) items; Animating Performance (6): 1 use, long rest;
                      Mote of Potential (3): note on Bardic Inspiration (DC 8 + PB + CHA, CHA mod temporary hit points).
 Eloquence            Unsettling Words (3): note on Bardic Inspiration; Universal Speech (6): 1 use, long rest, CHA mod
                      (minimum 1) creatures; Infectious Inspiration (14): CHA mod (minimum 1) uses, long rest.
 Glamour              Mantle of Inspiration (3): note on Bardic Inspiration (5 / 8 / 11 / 14 temporary hit points at
                      3 / 5 / 10 / 15, CHA mod creatures); Enthralling Performance (3): 1 use, short or long rest;
                      Mantle of Majesty (6): 1 use, long rest; Unbreakable Majesty (14): 1 use, short or long rest.
 Spirits              Tales from Beyond (3): note on Bardic Inspiration (DC 8 + PB + CHA); Spirit Session (6): 1 use, long rest,
                      PB creatures.
 Swords               Blade Flourish (3) + Master's Flourish (14): notes on Bardic Inspiration.
 Whispers             Psychic Blades (3): note on Bardic Inspiration, 2d6 / 3d6 / 5d6 / 8d6 at 3 / 5 / 10 / 15; Words of Terror
                      (3): 1 use, short or long rest; Mantle of Whispers (6): 1 use, short or long rest; Shadow Lore (14):
                      1 use, long rest.

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
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

RULESETS_2014 = ["mixed", "2014"]
CLASSES = {"barbarian", "bard"}


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


def _text(catalog, fid):
    rec = catalog.features[fid]
    return " ".join([rec.get("name") or ""] + [x for x in rec["desc"] if isinstance(x, str)])


# (subclass, class, resource id, first level, uses, recharge)
#   uses: an int, None, "pb", "cha1" (max(1, CHA modifier)), "level" ...
RESOURCES = [
    ("ancestral-guardian-xge", "barbarian", "barbarian:spirit-shield", 6, None, None),
    ("ancestral-guardian-xge", "barbarian", "barbarian:consult-the-spirits", 10, 1, "short-or-long"),
    ("battlerager-scag", "barbarian", "barbarian:battlerager-armor", 3, None, None),
    ("battlerager-scag", "barbarian", "barbarian:reckless-abandon", 6, None, None),
    ("battlerager-scag", "barbarian", "barbarian:spiked-retribution", 14, None, None),
    ("beast-tce", "barbarian", "barbarian:form-of-the-beast", 3, None, None),
    ("beast-tce", "barbarian", "barbarian:infectious-fury", 10, "pb", "long"),
    ("beast-tce", "barbarian", "barbarian:call-the-hunt", 14, "pb", "long"),
    ("giant-bgg", "barbarian", "barbarian:elemental-cleaver", 6, None, None),
    ("giant-bgg", "barbarian", "barbarian:mighty-impel", 10, None, None),
    ("storm-herald-xge", "barbarian", "barbarian:storm-aura", 3, None, None),
    ("wild-magic-tce", "barbarian", "barbarian:magic-awareness", 3, "pb", "long"),
    ("wild-magic-tce", "barbarian", "barbarian:wild-surge", 3, None, None),
    ("wild-magic-tce", "barbarian", "barbarian:bolstering-magic", 6, "pb", "long"),
    ("zealot-xge", "barbarian", "barbarian:divine-fury", 3, None, None),
    ("zealot-xge", "barbarian", "barbarian:fanatical-focus", 6, 1, "rage"),  # X2
    ("zealot-xge", "barbarian", "barbarian:zealous-presence", 10, 1, "long"),
    ("creation-tce", "bard", "bard:performance-of-creation", 3, 1, "long"),
    ("creation-tce", "bard", "bard:animating-performance", 6, 1, "long"),
    ("eloquence-tce", "bard", "bard:universal-speech", 6, 1, "long"),
    ("eloquence-tce", "bard", "bard:infectious-inspiration", 14, "cha1", "long"),
    ("glamour-xge", "bard", "bard:enthralling-performance", 3, 1, "short-or-long"),
    ("glamour-xge", "bard", "bard:mantle-of-majesty", 6, 1, "long"),
    ("glamour-xge", "bard", "bard:unbreakable-majesty", 14, 1, "short-or-long"),
    ("spirits-vrgr", "bard", "bard:spirit-session", 6, 1, "long"),
    ("whispers-xge", "bard", "bard:words-of-terror", 3, 1, "short-or-long"),
    ("whispers-xge", "bard", "bard:mantle-of-whispers", 6, 1, "short-or-long"),
    ("whispers-xge", "bard", "bard:shadow-lore", 14, 1, "long"),
]

# (subclass, class, existing resource id, first level, text the note must hold)
NOTES = [
    ("creation-tce", "bard", "bard:bardic-inspiration", 3, "Mote of Potential"),
    ("eloquence-tce", "bard", "bard:bardic-inspiration", 3, "Unsettling Words"),
    ("glamour-xge", "bard", "bard:bardic-inspiration", 3, "Mantle of Inspiration"),
    ("spirits-vrgr", "bard", "bard:bardic-inspiration", 3, "Tales from Beyond"),
    ("swords-xge", "bard", "bard:bardic-inspiration", 3, "Blade Flourish"),
    ("whispers-xge", "bard", "bard:bardic-inspiration", 3, "Psychic Blades"),
]


def _uses(res, uses):
    if uses == "pb":
        return _pb(res)
    if uses == "cha1":
        return max(1, _mod(res, "CHA"))
    return uses


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_tables_hold_exactly_the_matrix():
    ids = {f"{s['class']}:{_slug(s['name'])}" for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["class"] in CLASSES}
    assert ids >= {r[2] for r in RESOURCES}
    notes = {(s["subclass"], s["target"], s["name"]) for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["class"] in CLASSES}
    assert notes >= {(n[0], n[2], n[4]) for n in NOTES}


@needs_data
def test_quotes_match_catalog(catalog):
    """Every W8 entry quotes the record text it was built from (verbatim substring of name + desc), names a non-SRD 2014
    book subclass of its class, and the level tables that live only in the text are pinned."""
    specs = list(reference_data.SUBCLASS_TAIL_2014_BOOKS) + list(reference_data.SUBCLASS_NOTES_2014_BOOKS)
    assert specs
    keys = [(s["subclass"], s["name"], s.get("target")) for s in specs]
    assert len(keys) == len(set(keys)), "duplicate W8 entry"
    for spec in specs:
        assert spec["quotes"], spec["feature"]
        sub = catalog.subclasses[spec["subclass"]]
        assert sub["ruleset"] == "2014" and sub["source"] != "SRD", spec["subclass"]
        assert sub["class"]["index"] == spec["class"], spec["subclass"]
        rec = catalog.features[spec["feature"]]
        assert rec["subclass"]["index"] == spec["subclass"] and rec["class"]["index"] == spec["class"], spec["feature"]
        for fid, quote in spec["quotes"]:
            assert quote in _text(catalog, fid), (spec["feature"], fid, quote)
            other = catalog.features[fid]
            owner = (other.get("subclass") or {}).get("index")  # W8c: a rule of the class itself (the Monk's Ki save DC) may be quoted
            assert owner == spec["subclass"] or (owner is None and other["class"]["index"] == spec["class"]), (spec["feature"], fid)
        for extra_id, _t in spec.get("extras") or ():
            assert catalog.features[extra_id]["subclass"]["index"] == spec["subclass"], extra_id
    for name, pins in reference_data.BOOK_TABLE_PINS_2014.items():
        table = getattr(reference_data, name)
        for fid, quote in pins:
            assert quote in _text(catalog, fid), (name, fid, quote)
        assert table, name


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for sub, cls, rid, first, _u, _r in RESOURCES:
        spec = next(s for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["subclass"] == sub and s["class"] == cls
                    and f"{cls}:{_slug(s['name'])}" == rid)
        assert catalog.features[spec["feature"]]["level"] == first, rid
    for sub, cls, rid, first, text in NOTES:
        spec = next(s for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["subclass"] == sub and s["name"] == text)
        assert catalog.features[spec["feature"]]["level"] == first, text


# ---- resources: appear at the record's level for the selected book subclass --------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_appears_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["uses"] == _uses(res, uses) and r["recharge"] == recharge and "unlimited" not in r
    assert r["details"]["note"]
    assert r["id"] == f"{cls}:{_slug(r['name'])}"
    if first > 3:
        assert _entry(_res(catalog, cls, first - 1, sub, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_needs_its_subclass(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    assert _entry(_res(catalog, cls, 20, None, ruleset), rid) is None
    other = "totem-warrior-phb" if cls == "barbarian" else "valor-phb"
    assert _entry(_res(catalog, cls, 20, other, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,text", NOTES)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, text):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    if first > 3:
        assert text not in (_note(_res(catalog, cls, first - 1, sub, ruleset), rid) or "")
    assert text not in (_note(_res(catalog, cls, 20, None, ruleset), rid) or "")  # no subclass: no note


@needs_data
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_line_prints(catalog, sub, cls, rid, first, uses, recharge):
    r = _entry(_res(catalog, cls, 20, sub), rid)
    assert r["name"] in resource_line(r)


# ---- numbers: Barbarian -----------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,dice", [(6, "2d6"), (9, "2d6"), (10, "3d6"), (13, "3d6"), (14, "4d6"), (20, "4d6")])
def test_spirit_shield_dice_follow_the_text(catalog, level, dice):
    r = _entry(_res(catalog, "barbarian", level, "ancestral-guardian-xge"), "barbarian:spirit-shield")
    assert r["dice"] == dice and f"reduce that damage by {dice}" in r["details"]["note"]
    assert "raging" in r["details"]["note"] and "30 feet" in r["details"]["note"]
    assert ("Vengeful Ancestors" in r["details"]["note"]) == (level >= 14)


@needs_data
def test_consult_the_spirits_note(catalog):
    n = _note(_res(catalog, "barbarian", 10, "ancestral-guardian-xge"), "barbarian:consult-the-spirits")
    assert "augury" in n and "clairvoyance" in n and "Wisdom" in n


@needs_data
def test_battlerager_numbers(catalog):
    res = _res(catalog, "barbarian", 14, "battlerager-scag")
    assert "1d4 piercing" in _note(res, "barbarian:battlerager-armor") and "3 piercing" in _note(res, "barbarian:battlerager-armor")
    assert "3 piercing damage" in _note(res, "barbarian:spiked-retribution")


@needs_data
@pytest.mark.parametrize("con", [6, 10, 14, 20])
def test_reckless_abandon_temporary_hit_points_are_constitution_minimum_one(catalog, con):
    res = _res(catalog, "barbarian", 6, "battlerager-scag", abilities={"CON": con})
    assert f"{max(1, _mod(res, 'CON'))} temporary hit points" in _note(res, "barbarian:reckless-abandon")


@needs_data
def test_form_of_the_beast_numbers(catalog):
    res = _res(catalog, "barbarian", 3, "beast-tce")
    n = _note(res, "barbarian:form-of-the-beast")
    assert "1d8 piercing" in n and "1d6 slashing" in n and f"regain {_pb(res)} hit points" in n
    assert "less than half" in n and "d8" in n.split("Tail")[1]


@needs_data
@pytest.mark.parametrize("level,con", [(10, 6), (10, 18), (14, 14), (20, 20)])
def test_infectious_fury_and_call_the_hunt_numbers(catalog, level, con):
    res = _res(catalog, "barbarian", level, "beast-tce", abilities={"CON": con})
    n = _note(res, "barbarian:infectious-fury")
    assert f"DC {8 + _pb(res) + _mod(res, 'CON')}" in n and "2d12 psychic" in n
    assert _entry(res, "barbarian:infectious-fury")["uses"] == _pb(res)
    if level >= 14:
        h = _note(res, "barbarian:call-the-hunt")
        assert f"up to {max(1, _mod(res, 'CON'))} other willing creature" in h and "5 temporary hit points" in h and "d6" in h


@needs_data
@pytest.mark.parametrize("level,dice", [(6, "1d6"), (13, "1d6"), (14, "2d6"), (20, "2d6")])
def test_elemental_cleaver_dice_follow_the_text(catalog, level, dice):
    r = _entry(_res(catalog, "barbarian", level, "giant-bgg"), "barbarian:elemental-cleaver")
    assert r["dice"] == dice and f"extra {dice}" in r["details"]["note"]
    assert "acid, cold, fire, thunder, or lightning" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("str_", [8, 20])
def test_mighty_impel_dc(catalog, str_):
    res = _res(catalog, "barbarian", 10, "giant-bgg", abilities={"STR": str_})
    n = _note(res, "barbarian:mighty-impel")
    assert f"DC {8 + _pb(res) + _mod(res, 'STR')}" in n and "30 feet" in n and "Medium" in n


@needs_data
@pytest.mark.parametrize("level,desert,sea,tundra", [
    (3, 2, "1d6", 2), (4, 2, "1d6", 2), (5, 3, "1d6", 3), (9, 3, "1d6", 3), (10, 4, "2d6", 4),
    (14, 4, "2d6", 4), (15, 5, "3d6", 5), (19, 5, "3d6", 5), (20, 6, "4d6", 6)])
def test_storm_aura_numbers_follow_the_level(catalog, level, desert, sea, tundra):
    res = _res(catalog, "barbarian", level, "storm-herald-xge", abilities={"CON": 16})
    n = _note(res, "barbarian:storm-aura")
    assert f"DC {8 + _pb(res) + _mod(res, 'CON')}" in n and "10 feet" in n
    assert f"{desert} fire damage" in n and f"{sea} lightning damage" in n and f"{tundra} temporary hit points" in n
    assert ("Raging Storm" in n) == (level >= 14)
    if level >= 14:
        assert f"fire damage equal to half your barbarian level ({level // 2})" in n


@needs_data
@pytest.mark.parametrize("con", [6, 18])
def test_wild_magic_dc_and_uses(catalog, con):
    res = _res(catalog, "barbarian", 6, "wild-magic-tce", abilities={"CON": con})
    assert f"DC {8 + _pb(res) + _mod(res, 'CON')}" in _note(res, "barbarian:wild-surge")
    for rid, text in (("barbarian:magic-awareness", "60 feet"), ("barbarian:bolstering-magic", "d3")):
        assert _entry(res, rid)["uses"] == _pb(res) and text in _note(res, rid)


@needs_data
@pytest.mark.parametrize("level", [3, 4, 9, 20])
def test_divine_fury_adds_half_the_level(catalog, level):
    n = _note(_res(catalog, "barbarian", level, "zealot-xge"), "barbarian:divine-fury")
    assert f"1d6 + {level // 2}" in n and "necrotic or radiant" in n and "raging" in n


@needs_data
def test_fanatical_focus_and_zealous_presence(catalog):
    res = _res(catalog, "barbarian", 10, "zealot-xge")
    assert "once per rage" in _note(res, "barbarian:fanatical-focus")
    assert "ten other creatures" in _note(res, "barbarian:zealous-presence") and "60 feet" in _note(res, "barbarian:zealous-presence")
    assert _entry(res, "barbarian:fanatical-focus")["recharge"] == "rage"  # X2: a rage is not a rest, "rage" is its own recharge


# ---- numbers: Bard ---------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,size,cha", [(3, "Medium", 10), (5, "Medium", 10), (6, "Large", 10), (13, "Large", 14),
                                               (14, "Huge", 6), (14, "Huge", 18), (20, "Huge", 18)])
def test_performance_of_creation_numbers(catalog, level, size, cha):
    res = _res(catalog, "bard", level, "creation-tce", abilities={"CHA": cha})
    n = _note(res, "bard:performance-of-creation")
    assert (f"{20 * level} gp" in n) == (level < 14) and ("no gp limit" in n) == (level >= 14) and f"{_pb(res)} hours" in n and f"{size} or smaller" in n
    assert ("Creative Crescendo" in n) == (level >= 14)
    if level >= 14:
        assert f"up to {max(2, _mod(res, 'CHA'))} items" in n
    r = _entry(res, "bard:performance-of-creation")
    assert r["uses"] == 1 and r["recharge"] == "long" and "2nd level or higher" in n


@needs_data
def test_animating_performance_and_mote_of_potential(catalog):
    res = _res(catalog, "bard", 6, "creation-tce", abilities={"CHA": 18})
    n = _note(res, "bard:animating-performance")
    assert "1 hour" in n and "30 feet" in n and f"PB {_pb(res)}" in n and "3rd level or higher" in n
    bi = _note(res, "bard:bardic-inspiration")
    assert f"DC {8 + _pb(res) + _mod(res, 'CHA')}" in bi and f"roll {_mod(res, 'CHA'):+d} (minimum 1 temporary hit point in total)" in bi
    assert "thunder damage" in bi


@needs_data
def test_unsettling_words_spends_a_use(catalog):
    n = _note(_res(catalog, "bard", 3, "eloquence-tce"), "bard:bardic-inspiration")
    assert "expend a use" in n.split("Unsettling Words")[1] and "60 feet" in n


@needs_data
@pytest.mark.parametrize("cha", [6, 10, 18])
def test_universal_speech_and_infectious_inspiration_scale_with_charisma(catalog, cha):
    res = _res(catalog, "bard", 14, "eloquence-tce", abilities={"CHA": cha})
    assert f"{max(1, _mod(res, 'CHA'))} creature" in _note(res, "bard:universal-speech")
    assert "1 hour" in _note(res, "bard:universal-speech")
    r = _entry(res, "bard:infectious-inspiration")
    assert r["uses"] == max(1, _mod(res, "CHA")) and "60 feet" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("level,thp", [(3, 5), (4, 5), (5, 8), (9, 8), (10, 11), (14, 11), (15, 14), (20, 14)])
def test_mantle_of_inspiration_temporary_hit_points(catalog, level, thp):
    res = _res(catalog, "bard", level, "glamour-xge", abilities={"CHA": 18})
    n = _note(res, "bard:bardic-inspiration")
    assert f"{thp} temporary hit points" in n and f"up to {max(1, _mod(res, 'CHA'))} creature" in n
    assert "expend a use" in n.split("Mantle of Inspiration")[1]


@needs_data
def test_glamour_resources(catalog):
    res = _res(catalog, "bard", 14, "glamour-xge", abilities={"CHA": 18})
    dc = 8 + _pb(res) + _mod(res, "CHA")
    e = _note(res, "bard:enthralling-performance")
    assert f"DC {dc}" in e and f"{_mod(res, 'CHA')} humanoid" in e and "1 hour" in e
    assert "command" in _note(res, "bard:mantle-of-majesty") and "1 minute" in _note(res, "bard:mantle-of-majesty")
    assert f"DC {dc}" in _note(res, "bard:unbreakable-majesty")


@needs_data
def test_tales_from_beyond_and_spirit_session(catalog):
    res = _res(catalog, "bard", 6, "spirits-vrgr", abilities={"CHA": 16})
    assert f"DC {8 + _pb(res) + _mod(res, 'CHA')}" in _note(res, "bard:bardic-inspiration")
    assert "Tales from Beyond" in _note(res, "bard:bardic-inspiration")
    n = _note(res, "bard:spirit-session")
    assert f"up to {_pb(res)} willing creatures" in n and "divination or necromancy" in n


@needs_data
def test_blade_flourish_and_masters_flourish(catalog):
    n3 = _note(_res(catalog, "bard", 3, "swords-xge"), "bard:bardic-inspiration")
    assert "10 feet" in n3 and "Defensive" in n3 and "Slashing" in n3 and "Mobile" in n3 and "Master's Flourish" not in n3
    n14 = _note(_res(catalog, "bard", 14, "swords-xge"), "bard:bardic-inspiration")
    assert "Master's Flourish" in n14 and "d6" in n14.split("Master's Flourish")[1]
    assert n14.index("Blade Flourish") < n14.index("Master's Flourish")


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "2d6"), (4, "2d6"), (5, "3d6"), (9, "3d6"), (10, "5d6"), (14, "5d6"), (15, "8d6"), (20, "8d6")])
def test_psychic_blades_dice_follow_the_text(catalog, level, dice):
    n = _note(_res(catalog, "bard", level, "whispers-xge"), "bard:bardic-inspiration")
    assert f"extra {dice} psychic" in n and "once per round" in n


@needs_data
def test_whispers_resources(catalog):
    res = _res(catalog, "bard", 14, "whispers-xge", abilities={"CHA": 18})
    dc = 8 + _pb(res) + _mod(res, "CHA")
    assert f"DC {dc}" in _note(res, "bard:words-of-terror") and "1 hour" in _note(res, "bard:words-of-terror")
    assert "+5" in _note(res, "bard:mantle-of-whispers") and "1 hour" in _note(res, "bard:mantle-of-whispers")
    s = _note(res, "bard:shadow-lore")
    assert f"DC {dc}" in s and "8 hours" in s and "30 feet" in s


@needs_data
def test_notes_follow_the_existing_bardic_inspiration_note(catalog):
    """The W6 / W7 notes come first; a book subclass sentence is appended with "; "."""
    n = _note(_res(catalog, "bard", 20, "whispers-xge"), "bard:bardic-inspiration")
    assert n.index("Superior Inspiration") < n.index("Psychic Blades")


# ---- gates -----------------------------------------------------------------------------------------------------

@needs_data
def test_2024_output_is_independent_of_the_2014_book_tables(catalog, monkeypatch):
    """Under ruleset 2024 the 2014 book tables are never read, even for a held 2014 book subclass."""
    def snapshot():
        return {(sub, cls): copy.deepcopy(_res(catalog, cls, 20, sub, "2024")["derived"]["classResources"])
                for sub, cls in {(r[0], r[1]) for r in RESOURCES} | {(n[0], n[1]) for n in NOTES}}
    before = snapshot()
    monkeypatch.setattr(reference_data, "SUBCLASS_TAIL_2014_BOOKS", ())
    monkeypatch.setattr(reference_data, "SUBCLASS_NOTES_2014_BOOKS", ())
    assert snapshot() == before
    assert _entry(_res(catalog, "barbarian", 20, "zealot-xge", "2014"), "barbarian:zealous-presence") is None  # 2014 reads them


@needs_data
def test_srd_and_unmodelled_book_subclasses_get_no_w8a_entries(catalog):
    """SRD subclasses keep their W7 entries only; Totem Warrior (picks, no use limit) and Valor (no number) get none."""
    new = {r[2] for r in RESOURCES}
    for cls, sub in (("barbarian", "berserker"), ("barbarian", "totem-warrior-phb"), ("bard", "lore"), ("bard", "valor-phb")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & new, (sub, set(_ids(res)) & new)
        for n in NOTES:
            if n[1] == cls:
                assert n[4] not in (_note(res, n[2]) or ""), (sub, n[4])


@needs_data
def test_xphb_twins_get_nothing(catalog):
    for cls, sub in (("barbarian", "zealot-xphb"), ("bard", "glamour-xphb")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & {r[2] for r in RESOURCES}


@needs_data
def test_multiclass_keeps_each_subclass_with_its_class(catalog):
    res = _res(catalog, "barbarian", 6, "zealot-xge", extra=[{"classId": "bard", "level": 6, "subclassId": "whispers-xge", "choices": {}}])
    ids = _ids(res)
    assert "barbarian:fanatical-focus" in ids and "bard:mantle-of-whispers" in ids
    assert ids.index("barbarian:divine-fury") < ids.index("bard:words-of-terror")


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls, sub in (("barbarian", "storm-herald-xge"), ("barbarian", "beast-tce"), ("bard", "creation-tce"),
                     ("bard", "whispers-xge"), ("bard", "glamour-xge")):
        _res(catalog, cls, 20, sub, ruleset)  # warm
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, cls, 20, sub, ruleset)
        assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls, sub)
