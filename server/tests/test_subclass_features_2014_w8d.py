"""W8d (finding F4, book subclass half, part 2b: Sorcerer, Warlock and Wizard): the 2014 non-SRD subclass use-limit tail.
Same machinery as W8a / W8b / W8c (`reference_data.SUBCLASS_TAIL_2014_BOOKS` / `SUBCLASS_NOTES_2014_BOOKS`, source kind
"subclass", mixed / 2014 only, only the selected book subclass, 2024 byte-identical, every entry quotes its catalog text;
`test_quotes_match_catalog` of W8a pins them). Written before the data.

Rule matrix (texts read from the catalog on 2026-10-24; PB = proficiency bonus, "mod" = ability modifier, "spell DC" = 8 +
PB + the class's spellcasting modifier (CHA for Sorcerer and Warlock, INT for Wizard)):

 Sorcerer Aberrant Mind: Telepathic Speech (1; CHA mod (min 1) miles, Sorcerer level minutes), Revelation in Flesh (14; 1+
          sorcery points, 10 minutes), Warping Implosion (18; 1 use, long rest or 5 sorcery points, 3d10, spell DC), Psionic
          Sorcery (sentence on Sorcery Points: spell level in sorcery points). Clockwork Soul: Restore Balance (1; PB uses, long
          rest), Bastion of Law (6; 1 to 5 sorcery points, d8s), Trance of Order (14; 1 use, long rest or 5 sp), Clockwork
          Cavalcade (18; 1 use, long rest or 7 sp, 100 hit points). Divine Soul: Favored by the Gods (1; 1 use, short or long
          rest, 2d4), Empowered Healing (6; 1 sp), Unearthly Recovery (18; 1 use, long rest). Lunar: Lunar Embodiment (1; 1 use,
          long rest), Lunar Boons (6; PB uses, long rest), Waxing and Waning (6; 1 sp), Lunar Phenomenon (18; 3d8, 3d10, spell
          DC, 5 sp). Pyromancer: Heart of Fire (1; half the level, min 1), Pyromancer's Fury (14; the level). Shadow: Eyes of the
          Dark (1; 120 feet, 2 sp), Strength of the Grave (1; 1 use, long rest, DC 5 + damage), Hound of Ill Omen (6; 3 sp, half the
          level temporary hit points), Umbral Form (18; 6 sp). Storm: Heart of the Storm (6; half the level), Storm's Fury (14; the
          level, spell DC), Wind Soul (18; 1 use, short or long rest, 3 + CHA mod creatures). Wild Magic: Tides of Chaos (1; 1
          use, long rest), Wild Magic Surge (1; d20 on 1), Bend Luck (6; 2 sp, 1d4).
 Warlock  Archfey: Fey Presence (1), Misty Escape (6), Dark Delirium (14): 1 use, short or long rest; Beguiling Defenses (10;
          spell DC). Celestial: Healing Light (1; 1 + Warlock level d6s, CHA mod (min 1) per use, long rest), Radiant Soul (6;
          CHA mod), Celestial Resilience (10; level + CHA mod, half level + CHA mod), Searing Vengeance (14; 1 use, long rest,
          2d8 + CHA mod). Fathomless: Tentacle of the Deeps (1; PB uses, long rest, 1d8, 2d8 from 10), Guardian Coil (6; 1d8 / 2d8),
          Grasping Tentacles (10; 1 use, long rest, level temporary hit points), Fathomless Plunge (14; 1 use, short or long
          rest). Genie: Bottled Respite (1; 1 use, long rest, 2 x PB hours; Sanctuary Vessel as an extra from 10), Genie's Wrath
          (1; PB damage), Elemental Gift (6; PB uses, long rest), Limited Wish (14; 1 use, 1d4 long rests, no recharge value).
          Great Old One: Entropic Ward (6; 1 use, short or long rest). Hexblade: Hexblade's Curse (1; 1 use, short or long rest,
          PB damage, level + CHA mod hit points), Accursed Specter (6; 1 use, long rest, half the level). Undead: Form of Dread
          (1; PB uses, long rest, 1d10 + level), Necrotic Husk (10; 1d4 long rests, 2d10 + level), Spirit Projection (14; 1 use,
          long rest). Undying: Among the Dead (1; spell DC), Defy Death (6; 1 use, long rest, 1d8 + CON mod), Indestructible Life
          (14; 1 use, short or long rest, 1d8 + level).
 Wizard   Abjuration: Arcane Ward (2; 1 use, long rest, 2 x level + INT mod), Improved Abjuration (10; PB). Bladesinging: Bladesong
          (2; PB uses, long rest, INT mod (min 1)), Song of Defense (10; 5 x slot level), Song of Victory (14; INT mod (min 1)).
          Chronurgy: Chronal Shift (2; 2 uses, long rest), Temporal Awareness (2; INT mod), Momentary Stasis (6; INT mod (min 1)
          uses, long rest, spell DC), Arcane Abeyance (10; 1 use, short or long rest). Conjuration: Benign Transposition (6; 1
          use, long rest). Divination: Portent (2; two d20s, three from 14, long rest), The Third Eye (10; 1 use, short or long
          rest). Enchantment: Hypnotic Gaze, Instinctive Charm (spell DC), Alter Memories (14; 1 + CHA mod hours). Graviturgy:
          Violent Attraction (10; INT mod (min 1) uses, long rest), Event Horizon (14; 1 use, long rest, 2d10, spell DC).
          Illusion: Illusory Self (10; 1 use, short or long rest). Necromancy: Grim Harvest (2), Undead Thralls (6; level, PB),
          Command Undead (14; spell DC). Scribes: Awakened Spellbook (2; 1 use, long rest), Manifest Mind (6; 1 use, long rest,
          PB casts), Master Scrivener (10), One with the Word (14; 1 use, long rest). Transmutation: Shapechanger (10; 1 use,
          short or long rest), Master Transmuter (14; 1 use, long rest). War Magic: Arcane Deflection (2; Deflecting Shroud half the
          level as an extra from 14), Tactical Wit (2; INT mod), Power Surge (6; INT mod (min 1) surges, half the level).

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (W8d section).
"""
from perf_helpers import assert_fast
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
CLASSES = {"sorcerer", "warlock", "wizard"}


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


def _uses(res, uses, level):
    return {"pb": _pb(res), "int1": max(1, _mod(res, "INT")), "level1": level + 1,
            "portent": 3 if level >= 14 else 2}.get(uses, uses)


def _dc(res, ability):
    return 8 + _pb(res) + _mod(res, ability)


# (subclass, class, resource id, first level, uses, recharge)
RESOURCES = [
    ("aberrant-mind-tce", "sorcerer", "sorcerer:telepathic-speech", 1, None, None),
    ("aberrant-mind-tce", "sorcerer", "sorcerer:revelation-in-flesh", 14, None, None),
    ("aberrant-mind-tce", "sorcerer", "sorcerer:warping-implosion", 18, 1, "long"),
    ("clockwork-soul-tce", "sorcerer", "sorcerer:restore-balance", 1, "pb", "long"),
    ("clockwork-soul-tce", "sorcerer", "sorcerer:bastion-of-law", 6, None, None),
    ("clockwork-soul-tce", "sorcerer", "sorcerer:trance-of-order", 14, 1, "long"),
    ("clockwork-soul-tce", "sorcerer", "sorcerer:clockwork-cavalcade", 18, 1, "long"),
    ("divine-soul-xge", "sorcerer", "sorcerer:favored-by-the-gods", 1, 1, "short-or-long"),
    ("divine-soul-xge", "sorcerer", "sorcerer:empowered-healing", 6, 1, "turn"),  # X2
    ("divine-soul-xge", "sorcerer", "sorcerer:unearthly-recovery", 18, 1, "long"),
    ("lunar-dsotdq", "sorcerer", "sorcerer:lunar-embodiment", 1, 1, "long"),
    ("lunar-dsotdq", "sorcerer", "sorcerer:lunar-boons", 6, "pb", "long"),
    ("lunar-dsotdq", "sorcerer", "sorcerer:waxing-and-waning", 6, None, None),
    ("lunar-dsotdq", "sorcerer", "sorcerer:lunar-phenomenon", 18, None, None),
    ("pyromancer-psk", "sorcerer", "sorcerer:heart-of-fire", 1, None, None),
    ("pyromancer-psk", "sorcerer", "sorcerer:pyromancer-s-fury", 14, None, None),
    ("shadow-xge", "sorcerer", "sorcerer:eyes-of-the-dark", 1, None, None),
    ("shadow-xge", "sorcerer", "sorcerer:strength-of-the-grave", 1, 1, "long"),
    ("shadow-xge", "sorcerer", "sorcerer:hound-of-ill-omen", 6, None, None),
    ("shadow-xge", "sorcerer", "sorcerer:umbral-form", 18, None, None),
    ("storm-xge", "sorcerer", "sorcerer:heart-of-the-storm", 6, None, None),
    ("storm-xge", "sorcerer", "sorcerer:storm-s-fury", 14, None, None),
    ("storm-xge", "sorcerer", "sorcerer:wind-soul", 18, 1, "short-or-long"),
    ("wild-phb", "sorcerer", "sorcerer:tides-of-chaos", 1, 1, "long"),
    ("wild-phb", "sorcerer", "sorcerer:wild-magic-surge", 1, None, None),
    ("wild-phb", "sorcerer", "sorcerer:bend-luck", 6, None, None),
    ("wild-phb", "sorcerer", "sorcerer:spell-bombardment", 18, 1, "turn"),  # X2: "only once per turn"
    ("archfey-phb", "warlock", "warlock:fey-presence", 1, 1, "short-or-long"),
    ("archfey-phb", "warlock", "warlock:misty-escape", 6, 1, "short-or-long"),
    ("archfey-phb", "warlock", "warlock:beguiling-defenses", 10, None, None),
    ("archfey-phb", "warlock", "warlock:dark-delirium", 14, 1, "short-or-long"),
    ("celestial-xge", "warlock", "warlock:healing-light", 1, "level1", "long"),
    ("celestial-xge", "warlock", "warlock:radiant-soul", 6, None, None),
    ("celestial-xge", "warlock", "warlock:celestial-resilience", 10, None, None),
    ("celestial-xge", "warlock", "warlock:searing-vengeance", 14, 1, "long"),
    ("fathomless-tce", "warlock", "warlock:tentacle-of-the-deeps", 1, "pb", "long"),
    ("fathomless-tce", "warlock", "warlock:guardian-coil", 6, None, None),
    ("fathomless-tce", "warlock", "warlock:grasping-tentacles", 10, 1, "long"),
    ("fathomless-tce", "warlock", "warlock:fathomless-plunge", 14, 1, "short-or-long"),
    ("genie-tce", "warlock", "warlock:bottled-respite", 1, 1, "long"),
    ("genie-tce", "warlock", "warlock:genie-s-wrath", 1, 1, "turn"),  # X2
    ("genie-tce", "warlock", "warlock:elemental-gift", 6, "pb", "long"),
    ("genie-tce", "warlock", "warlock:limited-wish", 14, 1, None),
    ("great-old-one-phb", "warlock", "warlock:entropic-ward", 6, 1, "short-or-long"),
    ("hexblade-xge", "warlock", "warlock:hexblade-s-curse", 1, 1, "short-or-long"),
    ("hexblade-xge", "warlock", "warlock:accursed-specter", 6, 1, "long"),
    ("undead-vrgr", "warlock", "warlock:form-of-dread", 1, "pb", "long"),
    ("undead-vrgr", "warlock", "warlock:necrotic-husk", 10, 1, None),
    ("undead-vrgr", "warlock", "warlock:spirit-projection", 14, 1, "long"),
    ("undying-scag", "warlock", "warlock:among-the-dead", 1, None, None),
    ("undying-scag", "warlock", "warlock:defy-death", 6, 1, "long"),
    ("undying-scag", "warlock", "warlock:indestructible-life", 14, 1, "short-or-long"),
    ("abjuration-phb", "wizard", "wizard:arcane-ward", 2, 1, "long"),
    ("abjuration-phb", "wizard", "wizard:improved-abjuration", 10, None, None),
    ("bladesinging-tce", "wizard", "wizard:bladesong", 2, "pb", "long"),
    ("bladesinging-tce", "wizard", "wizard:song-of-defense", 10, None, None),
    ("bladesinging-tce", "wizard", "wizard:song-of-victory", 14, None, None),
    ("chronurgy-egw", "wizard", "wizard:chronal-shift", 2, 2, "long"),
    ("chronurgy-egw", "wizard", "wizard:temporal-awareness", 2, None, None),
    ("chronurgy-egw", "wizard", "wizard:momentary-stasis", 6, "int1", "long"),
    ("chronurgy-egw", "wizard", "wizard:arcane-abeyance", 10, 1, "short-or-long"),
    ("conjuration-phb", "wizard", "wizard:benign-transposition", 6, 1, "long"),
    ("divination-phb", "wizard", "wizard:portent", 2, "portent", "long"),
    ("divination-phb", "wizard", "wizard:the-third-eye", 10, 1, "short-or-long"),
    ("enchantment-phb", "wizard", "wizard:hypnotic-gaze", 2, None, None),
    ("enchantment-phb", "wizard", "wizard:instinctive-charm", 6, None, None),
    ("enchantment-phb", "wizard", "wizard:alter-memories", 14, None, None),
    ("graviturgy-egw", "wizard", "wizard:violent-attraction", 10, "int1", "long"),
    ("graviturgy-egw", "wizard", "wizard:event-horizon", 14, 1, "long"),
    ("illusion-phb", "wizard", "wizard:illusory-self", 10, 1, "short-or-long"),
    ("necromancy-phb", "wizard", "wizard:grim-harvest", 2, 1, "turn"),  # X2
    ("necromancy-phb", "wizard", "wizard:undead-thralls", 6, None, None),
    ("necromancy-phb", "wizard", "wizard:command-undead", 14, None, None),
    ("scribes-tce", "wizard", "wizard:awakened-spellbook", 2, 1, "long"),
    ("scribes-tce", "wizard", "wizard:manifest-mind", 6, 1, "long"),
    ("scribes-tce", "wizard", "wizard:master-scrivener", 10, None, None),
    ("scribes-tce", "wizard", "wizard:one-with-the-word", 14, 1, "long"),
    ("transmutation-phb", "wizard", "wizard:shapechanger", 10, 1, "short-or-long"),
    ("transmutation-phb", "wizard", "wizard:master-transmuter", 14, 1, "long"),
    ("war-xge", "wizard", "wizard:arcane-deflection", 2, None, None),
    ("war-xge", "wizard", "wizard:tactical-wit", 2, None, None),
    ("war-xge", "wizard", "wizard:power-surge", 6, None, None),
]

# (subclass, class, existing resource id, first level, text the note must hold)
NOTES = [
    ("aberrant-mind-tce", "sorcerer", "sorcerer:sorcery-points", 6, "Psionic Sorcery"),
]


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_tables_hold_the_matrix():
    ids = {f"{s['class']}:{_slug(s['name'])}" for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["class"] in CLASSES}
    assert ids == {r[2] for r in RESOURCES}
    notes = {(s["subclass"], s["target"], s["name"]) for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["class"] in CLASSES}
    assert notes == {(n[0], n[2], n[4]) for n in NOTES}


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for sub, cls, rid, first, _u, _r in RESOURCES:
        spec = next(s for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["subclass"] == sub and s["class"] == cls
                    and f"{cls}:{_slug(s['name'])}" == rid)
        assert catalog.features[spec["feature"]]["level"] == first, (sub, rid)
    for sub, cls, rid, first, text in NOTES:
        spec = next(s for s in reference_data.SUBCLASS_NOTES_2014_BOOKS if s["subclass"] == sub and s["name"] == text)
        assert catalog.features[spec["feature"]]["level"] == first, (sub, text)


@needs_data
def test_every_modelled_subclass_is_a_book_subclass_of_the_three_classes(catalog):
    subs = {(r[0], r[1]) for r in RESOURCES}
    assert len(subs) == 28
    for sub, cls in subs:
        rec = catalog.subclasses[sub]
        assert rec["ruleset"] == "2014" and rec["source"] != "SRD" and rec["class"]["index"] == cls


# ---- resources: appear at the record's level for the selected book subclass --------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_appears_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    level = max(first, 3)
    res = _res(catalog, cls, level, sub, ruleset)
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["uses"] == _uses(res, uses, level) and r["recharge"] == recharge and "unlimited" not in r
    assert r["details"]["note"] and r["id"] == f"{cls}:{_slug(r['name'])}"
    if first > 3:
        assert _entry(_res(catalog, cls, first - 1, sub, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_needs_its_subclass(catalog, sub, cls, rid, first, uses, recharge):
    assert _entry(_res(catalog, cls, 20, None, "mixed"), rid) is None
    other = {"sorcerer": "draconic", "warlock": "fiend", "wizard": "evocation"}[cls]  # an SRD subclass of the same class
    assert _entry(_res(catalog, cls, 20, other, "mixed"), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,text", NOTES)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, text):
    res = _res(catalog, cls, first, sub, ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    assert text not in (_note(_res(catalog, cls, first - 1, sub, ruleset), rid) or "")
    assert text not in (_note(_res(catalog, cls, 20, "draconic", ruleset), rid) or "")  # an SRD subclass: no note


# ---- numbers: Sorcerer -----------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,cha", [(3, 6), (3, 18), (14, 10), (20, 20)])
def test_aberrant_mind_numbers(catalog, level, cha):
    res = _res(catalog, "sorcerer", level, "aberrant-mind-tce", abilities={"CHA": cha})
    n = _note(res, "sorcerer:telepathic-speech")
    assert f"{max(1, _mod(res, 'CHA'))} mile(s)" in n and f"for {level} minutes" in n and "30 feet" in n
    if level >= 14:
        assert "10 minutes" in _note(res, "sorcerer:revelation-in-flesh") and "60 feet" in _note(res, "sorcerer:revelation-in-flesh")
    if level >= 18:
        w = _note(res, "sorcerer:warping-implosion")
        assert f"DC {_dc(res, 'CHA')}" in w and "3d10" in w and "120 feet" in w and "5 sorcery points" in w


@needs_data
def test_psionic_sorcery_follows_the_sorcery_points_note(catalog):
    six = _note(_res(catalog, "sorcerer", 6, "aberrant-mind-tce"), "sorcerer:sorcery-points")
    assert six.startswith("Psionic Sorcery") and "equal to the spell's level" in six  # no earlier note to extend
    n = _note(_res(catalog, "sorcerer", 20, "aberrant-mind-tce"), "sorcerer:sorcery-points")
    assert n.index("Sorcerous Restoration") < n.index("Psionic Sorcery")  # the W6 note first, then "; "


@needs_data
def test_clockwork_soul_numbers(catalog):
    res = _res(catalog, "sorcerer", 18, "clockwork-soul-tce")
    assert "60 feet" in _note(res, "sorcerer:restore-balance")
    b = _note(res, "sorcerer:bastion-of-law")
    assert "1 to 5 sorcery points" in b and "d8s" in b and "30 feet" in b
    assert "5 sorcery points" in _note(res, "sorcerer:trance-of-order") and "9 or lower" in _note(res, "sorcerer:trance-of-order")
    c = _note(res, "sorcerer:clockwork-cavalcade")
    assert "100 hit points" in c and "7 sorcery points" in c and "30-foot cube" in c


@needs_data
def test_divine_soul_numbers(catalog):
    res = _res(catalog, "sorcerer", 18, "divine-soul-xge")
    r = _entry(res, "sorcerer:favored-by-the-gods")
    assert r["dice"] == "2d4" and "2d4" in r["details"]["note"]
    assert "1 sorcery point" in _note(res, "sorcerer:empowered-healing") and "5 feet" in _note(res, "sorcerer:empowered-healing")
    assert "half your hit point maximum" in _note(res, "sorcerer:unearthly-recovery")


@needs_data
@pytest.mark.parametrize("level,pb_uses", [(1, 2), (6, 3), (18, 6)])
def test_lunar_numbers(catalog, level, pb_uses):
    res = _res(catalog, "sorcerer", level, "lunar-dsotdq", abilities={"CHA": 16})
    assert _entry(res, "sorcerer:lunar-embodiment")["uses"] == 1
    if level >= 6:
        assert _entry(res, "sorcerer:lunar-boons")["uses"] == _pb(res) == pb_uses
        assert "1 sorcery point" in _note(res, "sorcerer:waxing-and-waning")
    if level >= 18:
        n = _note(res, "sorcerer:lunar-phenomenon")
        assert n.count(f"DC {_dc(res, 'CHA')}") == 2 and "3d8" in n and "3d10" in n and "60 feet" in n and "5 sorcery points" in n


@needs_data
@pytest.mark.parametrize("level", [1, 2, 3, 6, 14, 20])
def test_pyromancer_damage_follows_the_level(catalog, level):
    res = _res(catalog, "sorcerer", level, "pyromancer-psk")
    assert f"take {max(1, level // 2)} fire damage" in _note(res, "sorcerer:heart-of-fire")
    if level >= 14:
        assert f"deal {level} fire damage" in _note(res, "sorcerer:pyromancer-s-fury")
    else:
        assert _entry(res, "sorcerer:pyromancer-s-fury") is None


@needs_data
@pytest.mark.parametrize("level", [3, 6, 18, 20])
def test_shadow_numbers(catalog, level):
    res = _res(catalog, "sorcerer", level, "shadow-xge")
    assert "120 feet" in _note(res, "sorcerer:eyes-of-the-dark") and "2 sorcery points" in _note(res, "sorcerer:eyes-of-the-dark")
    assert "DC 5 + the damage taken" in _note(res, "sorcerer:strength-of-the-grave")
    if level >= 6:
        h = _note(res, "sorcerer:hound-of-ill-omen")
        assert "3 sorcery points" in h and f"{level // 2} temporary hit points" in h and "120 feet" in h and "5 minutes" in h
    if level >= 18:
        u = _note(res, "sorcerer:umbral-form")
        assert "6 sorcery points" in u and "5 force damage" in u and "1 minute" in u


@needs_data
@pytest.mark.parametrize("level,cha", [(6, 10), (14, 18), (18, 18), (20, 6)])
def test_storm_numbers(catalog, level, cha):
    res = _res(catalog, "sorcerer", level, "storm-xge", abilities={"CHA": cha})
    assert f"take {level // 2} lightning or thunder damage" in _note(res, "sorcerer:heart-of-the-storm")
    if level >= 14:
        n = _note(res, "sorcerer:storm-s-fury")
        assert f"deal {level} lightning damage" in n and f"DC {_dc(res, 'CHA')}" in n and "20 feet" in n
    if level >= 18:
        w = _note(res, "sorcerer:wind-soul")
        assert f"{3 + _mod(res, 'CHA')} creatures" in w and "flying speed of 60 feet" in w


@needs_data
def test_wild_magic_numbers(catalog):
    res = _res(catalog, "sorcerer", 6, "wild-phb")
    assert "advantage" in _note(res, "sorcerer:tides-of-chaos")
    assert "d20" in _note(res, "sorcerer:wild-magic-surge") and "once per turn" in _note(res, "sorcerer:wild-magic-surge")
    b = _note(res, "sorcerer:bend-luck")
    assert "2 sorcery points" in b and "1d4" in b


# ---- numbers: Warlock ------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_archfey_numbers(catalog, cha):
    res = _res(catalog, "warlock", 14, "archfey-phb", abilities={"CHA": cha})
    assert "10-foot cube" in _note(res, "warlock:fey-presence") and f"DC {_dc(res, 'CHA')}" in _note(res, "warlock:fey-presence")
    assert "60 feet" in _note(res, "warlock:misty-escape")
    assert f"DC {_dc(res, 'CHA')}" in _note(res, "warlock:beguiling-defenses")
    d = _note(res, "warlock:dark-delirium")
    assert f"DC {_dc(res, 'CHA')}" in d and "60 feet" in d and "1 minute" in d


@needs_data
@pytest.mark.parametrize("level,cha", [(3, 6), (6, 14), (10, 18), (14, 18), (20, 20)])
def test_celestial_numbers(catalog, level, cha):
    res = _res(catalog, "warlock", level, "celestial-xge", abilities={"CHA": cha})
    m = _mod(res, "CHA")
    r = _entry(res, "warlock:healing-light")
    assert r["uses"] == level + 1 and r["die"] == "d6" and f"at most {max(1, m)} {'die' if max(1, m) == 1 else 'dice'}" in r["details"]["note"]
    if level >= 6:
        assert f"({m:+d})" in _note(res, "warlock:radiant-soul")
    if level >= 10:
        n = _note(res, "warlock:celestial-resilience")
        assert f"gain {level + m} temporary hit points" in n and f"each gain {level // 2 + m}" in n and "five creatures" in n
    if level >= 14:
        assert f"2d8{m:+d} radiant" in _note(res, "warlock:searing-vengeance")


@needs_data
@pytest.mark.parametrize("level,dice", [(3, "1d8"), (9, "1d8"), (10, "2d8"), (20, "2d8")])
def test_fathomless_numbers(catalog, level, dice):
    res = _res(catalog, "warlock", level, "fathomless-tce")
    r = _entry(res, "warlock:tentacle-of-the-deeps")
    assert r["dice"] == dice and f"{dice} cold damage" in r["details"]["note"] and "60 feet" in r["details"]["note"]
    if level >= 6:
        assert f"by {dice}" in _note(res, "warlock:guardian-coil")
    if level >= 10:
        assert f"gain {level} temporary hit points" in _note(res, "warlock:grasping-tentacles")
    if level >= 14:
        assert "five other willing creatures" in _note(res, "warlock:fathomless-plunge") and "1 mile" in _note(res, "warlock:fathomless-plunge")


@needs_data
@pytest.mark.parametrize("level", [3, 10, 14])
def test_genie_numbers(catalog, level):
    res = _res(catalog, "warlock", level, "genie-tce", abilities={"CHA": 16})
    n = _note(res, "warlock:bottled-respite")
    assert f"AC equal to your spell save DC {_dc(res, 'CHA')}" in n and f"= {level + _pb(res)}" in n
    assert f"for up to {2 * _pb(res)} hours" in n and "20-foot-radius" in n
    assert ("Sanctuary Vessel" in n) == (level >= 10) and (f"+{_pb(res)} (your proficiency bonus)" in n) == (level >= 10)
    assert f"equal to your proficiency bonus (+{_pb(res)})" in _note(res, "warlock:genie-s-wrath")
    if level >= 14:
        w = _note(res, "warlock:limited-wish")
        assert "6th level or lower" in w and "1d4 long rests" in w
        assert _entry(res, "warlock:limited-wish")["recharge"] is None


@needs_data
@pytest.mark.parametrize("cha", [4, 18])
def test_hexblade_numbers(catalog, cha):
    res = _res(catalog, "warlock", 6, "hexblade-xge", abilities={"CHA": cha})
    n = _note(res, "warlock:hexblade-s-curse")
    assert f"(+{_pb(res)})" in n and "19 or 20" in n and f"regain {max(1, 6 + _mod(res, 'CHA'))} hit points" in n
    s = _note(res, "warlock:accursed-specter")
    assert "3 temporary hit points" in s and f"+{max(0, _mod(res, 'CHA'))}" in s


@needs_data
@pytest.mark.parametrize("level", [3, 10, 14, 20])
def test_undead_numbers(catalog, level):
    res = _res(catalog, "warlock", level, "undead-vrgr")
    assert f"1d10 + {level} temporary hit points" in _note(res, "warlock:form-of-dread")
    if level >= 10:
        n = _note(res, "warlock:necrotic-husk")
        assert f"2d10 + {level} necrotic" in n and "30 feet" in n and "1d4 long rests" in n
        assert _entry(res, "warlock:necrotic-husk")["recharge"] is None
    if level >= 14:
        s = _note(res, "warlock:spirit-projection")
        assert "1 hour" in s and "1d10 force" in s


@needs_data
@pytest.mark.parametrize("level,con", [(6, 6), (14, 18)])
def test_undying_numbers(catalog, level, con):
    res = _res(catalog, "warlock", level, "undying-scag", abilities={"CHA": 16, "CON": con})
    assert f"DC {_dc(res, 'CHA')}" in _note(res, "warlock:among-the-dead") and "24 hours" in _note(res, "warlock:among-the-dead")
    assert f"1d8 {_mod(res, 'CON'):+d} hit points (minimum 1 hit point in total)" in _note(res, "warlock:defy-death")
    if level >= 14:
        assert f"1d8 + {level} hit points" in _note(res, "warlock:indestructible-life")


# ---- numbers: Wizard -------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,int_", [(2, 8), (10, 18), (20, 20)])
def test_abjuration_numbers(catalog, level, int_):
    res = _res(catalog, "wizard", level, "abjuration-phb", abilities={"INT": int_})
    assert f"maximum is {2 * level + _mod(res, 'INT')} (twice" in _note(res, "wizard:arcane-ward")
    if level >= 10:
        assert f"(+{_pb(res)})" in _note(res, "wizard:improved-abjuration")


@needs_data
@pytest.mark.parametrize("int_", [6, 18])
def test_bladesinging_numbers(catalog, int_):
    res = _res(catalog, "wizard", 14, "bladesinging-tce", abilities={"INT": int_})
    m = max(1, _mod(res, "INT"))
    b = _note(res, "wizard:bladesong")
    assert f"AC +{m}" in b and f"+{m} to Constitution saving throws" in b and "+10 feet" in b
    assert "five times the slot's level" in _note(res, "wizard:song-of-defense")
    assert f"+{m}" in _note(res, "wizard:song-of-victory")


@needs_data
@pytest.mark.parametrize("int_", [6, 18])
def test_chronurgy_numbers(catalog, int_):
    res = _res(catalog, "wizard", 10, "chronurgy-egw", abilities={"INT": int_})
    assert _entry(res, "wizard:chronal-shift")["uses"] == 2 and "30 feet" in _note(res, "wizard:chronal-shift")
    assert f"({_mod(res, 'INT'):+d})" in _note(res, "wizard:temporal-awareness")
    s = _note(res, "wizard:momentary-stasis")
    assert f"DC {_dc(res, 'INT')}" in s and "60 feet" in s and "Large or smaller" in s
    a = _note(res, "wizard:arcane-abeyance")
    assert "AC 15" in a and "1 hour" in a and "4th level or lower" in a


@needs_data
@pytest.mark.parametrize("level,portent", [(2, 2), (13, 2), (14, 3), (20, 3)])
def test_portent_dice_follow_greater_portent(catalog, level, portent):
    r = _entry(_res(catalog, "wizard", level, "divination-phb"), "wizard:portent")
    assert r["uses"] == portent and f"roll {portent} d20s" in r["details"]["note"] and r["recharge"] == "long"


@needs_data
def test_divination_conjuration_and_illusion_flat_rules(catalog):
    n = _note(_res(catalog, "wizard", 10, "divination-phb"), "wizard:the-third-eye")
    assert "60 feet" in n and "10 feet" in n
    assert "30 feet" in _note(_res(catalog, "wizard", 6, "conjuration-phb"), "wizard:benign-transposition")
    assert "automatically misses" in _note(_res(catalog, "wizard", 10, "illusion-phb"), "wizard:illusory-self")


@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_enchantment_numbers(catalog, cha):
    res = _res(catalog, "wizard", 14, "enchantment-phb", abilities={"INT": 16, "CHA": cha})
    assert f"DC {_dc(res, 'INT')}" in _note(res, "wizard:hypnotic-gaze") and "5 feet" in _note(res, "wizard:hypnotic-gaze")
    assert f"DC {_dc(res, 'INT')}" in _note(res, "wizard:instinctive-charm") and "30 feet" in _note(res, "wizard:instinctive-charm")
    a = _note(res, "wizard:alter-memories")
    assert f"DC {_dc(res, 'INT')}" in a and f"loses {max(1, 1 + _mod(res, 'CHA'))} hour(s)" in a


@needs_data
@pytest.mark.parametrize("int_", [6, 18])
def test_graviturgy_numbers(catalog, int_):
    res = _res(catalog, "wizard", 14, "graviturgy-egw", abilities={"INT": int_})
    assert _entry(res, "wizard:violent-attraction")["uses"] == max(1, _mod(res, "INT"))
    v = _note(res, "wizard:violent-attraction")
    assert "1d10" in v and "2d10" in v and "60 feet" in v
    e = _note(res, "wizard:event-horizon")
    assert f"DC {_dc(res, 'INT')}" in e and "2d10 force" in e and "30 feet" in e and "3rd level or higher" in e


@needs_data
@pytest.mark.parametrize("level", [2, 6, 14])
def test_necromancy_numbers(catalog, level):
    res = _res(catalog, "wizard", level, "necromancy-phb", abilities={"INT": 16})
    assert "twice the spell's level" in _note(res, "wizard:grim-harvest") and "three times" in _note(res, "wizard:grim-harvest")
    if level >= 6:
        t = _note(res, "wizard:undead-thralls")
        assert f"increased by {level}" in t and f"(+{_pb(res)})" in t
    if level >= 14:
        c = _note(res, "wizard:command-undead")
        assert f"DC {_dc(res, 'INT')}" in c and "60 feet" in c and "8 or higher" in c and "12 or higher" in c


@needs_data
@pytest.mark.parametrize("level", [2, 6, 10, 14])
def test_scribes_numbers(catalog, level):
    res = _res(catalog, "wizard", level, "scribes-tce")
    assert "same level as the slot" in _note(res, "wizard:awakened-spellbook")
    if level >= 6:
        m = _note(res, "wizard:manifest-mind")
        assert f"{_pb(res)} times per day" in m and "60 feet" in m and "300 feet" in m and "spell slot of any level" in m
    if level >= 10:
        assert "1st or 2nd level" in _note(res, "wizard:master-scrivener")
    if level >= 14:
        assert "3d6" in _note(res, "wizard:one-with-the-word") and "1d6 long rests" in _note(res, "wizard:one-with-the-word")


@needs_data
def test_transmutation_numbers(catalog):
    res = _res(catalog, "wizard", 14, "transmutation-phb")
    assert "challenge rating 1 or lower" in _note(res, "wizard:shapechanger")
    t = _note(res, "wizard:master-transmuter")
    assert "5-foot cube" in t and "3d10 years" in t and "minimum of 13" in t


@needs_data
@pytest.mark.parametrize("level,int_", [(2, 8), (6, 18), (14, 20), (20, 12)])
def test_war_magic_numbers(catalog, level, int_):
    res = _res(catalog, "wizard", level, "war-xge", abilities={"INT": int_})
    d = _note(res, "wizard:arcane-deflection")
    assert "+2 bonus to your AC" in d and "+4" in d and ("Deflecting Shroud" in d) == (level >= 14)
    if level >= 14:
        assert f"each take {level // 2} force damage" in d
    assert f"({_mod(res, 'INT'):+d})" in _note(res, "wizard:tactical-wit")
    if level >= 6:
        p = _note(res, "wizard:power-surge")
        assert f"at most {max(1, _mod(res, 'INT'))} power surges" in p and f"equal to {level // 2} (half" in p


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
    assert _entry(_res(catalog, "wizard", 20, "war-xge", "2014"), "wizard:power-surge") is None  # 2014 reads them


@needs_data
def test_srd_xphb_and_frhof_subclasses_get_no_w8d_entries(catalog):
    new = {r[2] for r in RESOURCES}
    for cls, sub in (("sorcerer", "draconic"), ("sorcerer", "wild-magic-xphb"), ("sorcerer", "aberrant-xphb"), ("sorcerer", "spellfire-frhof"),
                     ("warlock", "fiend"), ("warlock", "archfey-xphb"), ("warlock", "great-old-one-xphb"),
                     ("wizard", "evocation"), ("wizard", "evoker-xphb"), ("wizard", "bladesinger-frhof")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & new, (sub, set(_ids(res)) & new)
    assert "Psionic Sorcery" not in (_note(_res(catalog, "sorcerer", 20, "aberrant-xphb", "mixed"), "sorcerer:sorcery-points") or "")


@needs_data
def test_multiclass_keeps_each_subclass_with_its_class(catalog):
    res = _res(catalog, "sorcerer", 6, "storm-xge", extra=[{"classId": "warlock", "level": 6, "subclassId": "hexblade-xge", "choices": {}},
                                                           {"classId": "wizard", "level": 6, "subclassId": "chronurgy-egw", "choices": {}}])
    ids = _ids(res)
    assert "sorcerer:heart-of-the-storm" in ids and "warlock:accursed-specter" in ids and "wizard:momentary-stasis" in ids
    assert ids.index("sorcerer:heart-of-the-storm") < ids.index("warlock:accursed-specter") < ids.index("wizard:momentary-stasis")
    assert "warlock:spirit-projection" not in ids and "wizard:arcane-abeyance" not in ids


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls, sub in (("sorcerer", "lunar-dsotdq"), ("sorcerer", "shadow-xge"), ("warlock", "genie-tce"), ("warlock", "celestial-xge"),
                     ("warlock", "undead-vrgr"), ("wizard", "scribes-tce"), ("wizard", "graviturgy-egw"), ("wizard", "war-xge")):
        _res(catalog, cls, 20, sub, ruleset)  # warm
        laps = []
        for _ in range(10):
            t_run = time.perf_counter()
            _res(catalog, cls, 20, sub, ruleset)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps, str((ruleset, cls, sub)))


@needs_data
@pytest.mark.parametrize("cha,hours", [(1, 1), (6, 1), (8, 1), (10, 1), (12, 2), (16, 4)])
def test_alter_memories_minimum_applies_to_total(catalog, cha, hours):
    """WG: '1 + your Charisma modifier (minimum of 1)' - the minimum is on the total, so CHA 6 (-2) gives 1, not 2."""
    res = _res(catalog, "wizard", 14, "enchantment-phb", abilities={"INT": 16, "CHA": cha})
    assert f"loses {hours} hour(s)" in _note(res, "wizard:alter-memories")


@needs_data
def test_healing_light_dice_wording(catalog):
    res = _res(catalog, "warlock", 3, "celestial-xge", abilities={"CHA": 8})
    n = _note(res, "warlock:healing-light")
    assert "at most 1 die at once" in n and "1 dice" not in n
