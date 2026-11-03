"""C7b: effects of the XPHB (2024) Eldritch Invocations, Magical Cunning and Contact Patron.

Every entry is checked against the XPHB invocation text in the catalog (quoted below, read 2026-10-10).

Rule matrix (text -> engine):
  Armor of Shadows   "You can cast Mage Armor on yourself without expending a spell slot."  -> innate mage-armor-xphb
                     at will + AC formula 13 + DEX (Mage Armor base AC; needs no armor worn, G2 worn.armor null).
  Ascendant Step / Mask of Many Faces / Master of Myriad Forms / Misty Visions / Otherworldly Leap / Visions of
  Distant Realms / Whispers of the Grave   "You can cast X ... without expending a spell slot."  -> innate, at will.
  Fiendish Vigor     False Life at will; "you automatically get the highest number on the die" -> note.
  One with Shadows   "While you're in an area of Dim Light or Darkness, you can cast Invisibility on yourself ..."
                     -> innate at will with the condition as a note.
  Gift of the Depths "You can breathe underwater, and you gain a Swim Speed equal to your Speed. ... cast Water
                     Breathing once ... regain ... Long Rest."  -> swim = walk, innate water-breathing 1/long rest.
  Pact of the Chain  "cast [Find Familiar] as a Magic action without expending a spell slot" -> innate at will (E6;
                     the data says "ritual"), note "Magic action".
  Devil's Sight      "see normally in Dim Light and Darkness ... within 120 feet" -> senses.devilsSight 120.
  Witch Sight        "Truesight with a range of 30 feet" -> senses.truesight 30 (carried by the data).
  Agonizing Blast    "add your Charisma modifier to that spell's damage rolls" -> resource bonus = CHA mod,
                     one per instance ("Agonizing Blast (2)"); the target cantrip is C7c.
  Eldritch Spear     "range increases by a number of feet equal to 30 times your Warlock level" -> note with N.
  Gift of the Protectors "a number of names equal to your Charisma modifier (minimum of one name)" -> note with N.
  Text-only (notes): Eldritch Mind, Pact of the Blade, Thirsting Blade (PHB 2024 Multiclassing: no extra attacks
  on top of Extra Attack), Devouring Blade, Eldritch Smite, Lifedrinker, Gaze of Two Minds, Investment of the
  Chain Master, Repelling Blast.
  Magical Cunning (2)  "regain expended Pact Magic spell slots but no more than a number equal to half your
                     maximum (round up) ... can't do so again until you finish a Long Rest" -> 1 use, long rest.
  Contact Patron (9)   "cast [Contact Other Plane] without expending a spell slot ... can't do so in this way again
                     until you finish a Long Rest" -> 1 use, long rest.
Deferred to C7c (no entry here): Pact of the Tome, Lessons of the First Ones.
Matrix: effect kind (innate / AC / senses / speeds / resource / note) x ruleset (2024 vs mixed/2014 unchanged) x
level gate (prerequisite lost -> effect gone) x repeat instances x SRD-only catalog x exhaustiveness x timing."""
from perf_helpers import assert_fast
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import class_choices_2024, features
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

INV = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
CANT = "class:warlock:spells-cantrips"
X = "opt-{}-xphb"
BLADE, CHAIN, TOME = X.format("pact-of-the-blade"), X.format("pact-of-the-chain"), X.format("pact-of-the-tome")
AGON, SPEAR, REPEL = X.format("agonizing-blast"), X.format("eldritch-spear"), X.format("repelling-blast")
DEFERRED_C7C = {TOME, X.format("lessons-of-the-first-ones")}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, picks, cantrips=None, cha=16, dex=14, worn=None, ruleset="2024"):
    ch = {INV: picks}
    if cantrips is not None:
        ch[CANT] = cantrips
    # C9b: 2024 Warlock package A (leather armor, daggers) stands in for the old automatic SRD kit
    package = {"class:warlock:1:equipment-choice-0": ["leather-armor+sickle+dagger+orb+book+scholars-pack+gp-15"]} if ruleset == "2024" else {}
    equipment = {"choices": package, "added": [], "skipped": False}
    if worn is not None:
        equipment["worn"] = worn
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": dex, "CON": 14, "INT": 10, "WIS": 10, "CHA": cha}},
        "species": {"id": "human"}, "background": {"id": "acolyte"}, "equipment": equipment,
        "classes": [{"classId": "warlock", "level": level, "choices": ch}],
    }


def _res(catalog, level, picks, **kw):
    return resolve(_draft(level, picks, **kw), catalog)


def _innate(r, spell):
    return [e for e in r["sheet"]["innateSpells"] if e["spellId"] == spell]


def _resource(r, name):
    return next((x for x in r["derived"]["classResources"] if x["name"] == name), None)


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith(("xphb-", "opt-")) or k.startswith("opt-") and not k.endswith("-xphb")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- innate spells ----------------------------------------------------------------


@needs_data
def test_armor_of_shadows_ac_and_innate(catalog):
    r = _res(catalog, 1, [X.format("armor-of-shadows")], worn={"armor": None})
    assert r["derived"]["armorClass"] == 15  # 13 + DEX 2
    e = _innate(r, "mage-armor-xphb")
    assert len(e) == 1 and e[0]["uses"] == "at-will" and e[0]["level"] == 1
    assert e[0]["ability"] == "CHA" and e[0]["source"] == "Eldritch Invocation" and e[0]["name"] == "Mage Armor"


@needs_data
def test_armor_of_shadows_not_applied_when_leather_armor_is_worn(catalog):
    r = _res(catalog, 1, [X.format("armor-of-shadows")])  # default kit: leather armor counts as worn (D3)
    assert r["derived"]["armorClass"] == 13


@needs_data
@pytest.mark.parametrize("name,spell,level,min_level", [
    ("ascendant-step", "levitate", 2, 5), ("mask-of-many-faces", "disguise-self", 1, 2),
    ("master-of-myriad-forms", "alter-self", 2, 5), ("misty-visions", "silent-image", 1, 2),
    ("otherworldly-leap", "jump", 1, 2), ("visions-of-distant-realms", "arcane-eye", 4, 9),
    ("whispers-of-the-grave", "speak-with-dead", 3, 7), ("one-with-shadows", "invisibility", 2, 5),
    ("fiendish-vigor", "false-life", 1, 2),
])
def test_at_will_innate_spells(catalog, name, spell, level, min_level):
    r = _res(catalog, min_level, [X.format(name)])
    e = _innate(r, spell + "-xphb")
    assert len(e) == 1, name
    assert e[0]["uses"] == "at-will" and e[0]["level"] == level and e[0]["source"] == "Eldritch Invocation"
    below = _res(catalog, min_level - 1, [X.format(name)]) if min_level > 1 else None
    if below:
        assert _innate(below, spell + "-xphb") == []  # prerequisite lost: pruned, effect gone


@needs_data
def test_notes_on_conditional_innate_spells(catalog):
    r = _res(catalog, 5, [X.format("one-with-shadows"), X.format("fiendish-vigor")])
    assert "Dim Light or Darkness" in _innate(r, "invisibility-xphb")[0]["note"]
    assert "highest" in _innate(r, "false-life-xphb")[0]["note"]


@needs_data
def test_pact_of_the_chain_find_familiar_at_will_with_note(catalog):
    r = _res(catalog, 1, [CHAIN])
    e = _innate(r, "find-familiar-xphb")
    assert len(e) == 1 and e[0]["uses"] == "at-will" and e[0]["level"] == 1
    assert "Magic action" in e[0]["note"]


@needs_data
def test_gift_of_the_depths_swim_speed_and_water_breathing(catalog):
    r = _res(catalog, 5, [X.format("gift-of-the-depths")])
    assert r["derived"]["speeds"]["walk"] == 30 and r["derived"]["speeds"]["swim"] == 30
    e = _innate(r, "water-breathing-xphb")
    assert len(e) == 1 and e[0]["uses"] == "1/long rest" and e[0]["level"] == 3
    assert "breathe underwater" in e[0]["note"]
    assert "swim" not in _res(catalog, 5, [])["derived"]["speeds"]


@needs_data
def test_swim_equals_walk_after_speed_bonuses_and_keeps_a_faster_swim(catalog):
    d = _draft(5, [X.format("gift-of-the-depths")])
    d["classes"].append({"classId": "barbarian", "level": 5, "choices": {}})  # Fast Movement +10 (no armor worn)
    d["equipment"]["worn"] = {"armor": None}
    r = resolve(d, catalog)
    assert r["derived"]["speeds"]["walk"] == 40 and r["derived"]["speeds"]["swim"] == 40
    d = _draft(5, [X.format("gift-of-the-depths")])
    d["species"] = {"id": "triton"}  # swim 30 = walk 30; keep the larger of the two if swim were higher
    r = resolve(d, catalog)
    if r["derived"]["speeds"].get("swim") is not None:
        assert r["derived"]["speeds"]["swim"] >= r["derived"]["speeds"]["walk"]


# ---- senses -----------------------------------------------------------------------


@needs_data
def test_devils_sight_and_witch_sight(catalog):
    r = _res(catalog, 2, [X.format("devils-sight")])
    assert r["sheet"]["senses"]["devilsSight"] == 120 and "darkvision" not in r["sheet"]["senses"]
    r = _res(catalog, 15, [X.format("witch-sight"), X.format("devils-sight")])
    assert r["sheet"]["senses"]["truesight"] == 30 and r["sheet"]["senses"]["devilsSight"] == 120
    r = _res(catalog, 14, [X.format("witch-sight")])
    assert "truesight" not in r["sheet"]["senses"]


# ---- resources --------------------------------------------------------------------


@needs_data
def test_agonizing_blast_instances_each_add_charisma(catalog):
    c = ["eldritch-blast-xphb", "toll-the-dead-xphb"]
    r = _res(catalog, 5, [AGON, AGON + "~2"], cantrips=c, cha=16)  # CHA 16 + human 1 = 17 -> +3
    first, second = _resource(r, "Agonizing Blast"), _resource(r, "Agonizing Blast (2)")
    assert first["bonus"] == 3 and second["bonus"] == 3
    assert first["id"] != second["id"]
    assert "damage" in first["details"]["note"] and "spell" not in first["details"]  # target pick is C7c
    assert _resource(_res(catalog, 5, [AGON], cantrips=c), "Agonizing Blast (2)") is None


@needs_data
def test_agonizing_blast_negative_charisma_keeps_the_raw_modifier(catalog):
    r = _res(catalog, 2, [AGON], cantrips=["eldritch-blast-xphb"], cha=8)  # 8 -> -1
    assert _resource(r, "Agonizing Blast")["bonus"] == -1


@needs_data
def test_eldritch_spear_range_note(catalog):
    # F3a-2a: instance 2 needs a second eligible cantrip
    r = _res(catalog, 5, [SPEAR, SPEAR + "~2"], cantrips=["eldritch-blast-xphb", "toll-the-dead-xphb"])
    assert "150 feet" in _resource(r, "Eldritch Spear")["details"]["note"]  # 30 x 5
    assert _resource(r, "Eldritch Spear (2)") is not None
    assert "300 feet" in _resource(_res(catalog, 10, [SPEAR], cantrips=["eldritch-blast-xphb"]), "Eldritch Spear")["details"]["note"]


@needs_data
def test_repelling_blast_note(catalog):
    r = _res(catalog, 2, [REPEL], cantrips=["eldritch-blast-xphb"])
    note = _resource(r, "Repelling Blast")["details"]["note"]
    assert "10 feet" in note and "Large or smaller" in note


@needs_data
def test_gift_of_the_protectors_names_are_charisma_minimum_one(catalog):
    picks = [TOME, X.format("gift-of-the-protectors")]
    assert "3 names" in _resource(_res(catalog, 9, picks, cha=16), "Gift of the Protectors")["details"]["note"]  # 17 -> +3
    assert "1 name" in _resource(_res(catalog, 9, picks, cha=4), "Gift of the Protectors")["details"]["note"]  # 5 -> -3 -> 1


@needs_data
@pytest.mark.parametrize("name,words,level,extra", [
    ("eldritch-mind", "Concentration", 1, []),
    ("pact-of-the-blade", "pact weapon", 1, []),
    ("thirsting-blade", "Extra Attack", 5, [BLADE]),
    ("devouring-blade", "two extra attacks", 12, [BLADE, X.format("thirsting-blade")]),
    ("eldritch-smite", "Force", 5, [BLADE]),
    ("lifedrinker", "Hit Point Die", 9, [BLADE]),
    ("gaze-of-two-minds", "willing creature", 5, []),
    ("investment-of-the-chain-master", "familiar", 5, [CHAIN]),
])
def test_text_only_invocations_become_notes(catalog, name, words, level, extra):
    r = _res(catalog, level, extra + [X.format(name)])
    label = catalog.features[X.format(name)]["name"]
    res = _resource(r, label)
    assert res is not None and words in res["details"]["note"], name


@needs_data
def test_thirsting_blade_note_does_not_stack_with_extra_attack(catalog):
    r = _res(catalog, 5, [BLADE, X.format("thirsting-blade")])
    assert "doesn't give additional attacks" in _resource(r, "Thirsting Blade")["details"]["note"]


@needs_data
def test_magical_cunning_note_half_the_pact_slots_rounded_up(catalog):
    for level, slots, half in [(2, 2, 1), (5, 2, 1), (11, 3, 2), (17, 4, 2)]:
        res = _resource(_res(catalog, level, []), "Magical Cunning")
        assert res["uses"] == 1 and res["recharge"] == "long"
        assert f"half your maximum Pact Magic slots ({slots}) rounded up = {half}" in res["details"]["note"], level
    assert _resource(_res(catalog, 1, []), "Magical Cunning") is None


@needs_data
def test_magical_cunning_at_warlock_20_regains_all_slots_eldritch_master(catalog):
    # F3a-7: Eldritch Master (Warlock 20): "When you use your Magical Cunning feature, you regain all your expended
    # Pact Magic spell slots."
    note = _resource(_res(catalog, 20, []), "Magical Cunning")["details"]["note"]
    assert "ALL your expended Pact Magic slots" in note and "half" not in note
    assert "half" in _resource(_res(catalog, 19, []), "Magical Cunning")["details"]["note"]


@needs_data
def test_contact_patron_from_level_9(catalog):
    assert _resource(_res(catalog, 8, []), "Contact Patron") is None
    res = _resource(_res(catalog, 9, []), "Contact Patron")
    assert res["uses"] == 1 and res["recharge"] == "long" and "Contact Other Plane" in res["details"]["note"]


@needs_data
def test_no_tome_or_lessons_entries_yet(catalog):
    r = _res(catalog, 2, [TOME, X.format("lessons-of-the-first-ones")])
    assert [x["name"] for x in r["derived"]["classResources"]] == ["Magical Cunning"]
    assert r["sheet"]["innateSpells"] == []


# ---- ruleset isolation / degrade ----------------------------------------------------


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_other_rulesets_have_no_2024_resources(catalog, ruleset):
    r = _res(catalog, 9, [], ruleset=ruleset)
    names = {x["name"] for x in r["derived"]["classResources"]}
    assert not names & {"Magical Cunning", "Contact Patron"}


@needs_data
def test_srd_only_catalog_degrades(catalog):
    r = _res(_srd_only(catalog), 9, [BLADE])
    assert not {x["name"] for x in r["derived"]["classResources"]} & {"Magical Cunning", "Contact Patron"}
    assert r["sheet"]["innateSpells"] == []


def test_effect_lookup_without_catalog_data_returns_table_only():
    assert class_choices_2024.invocation_effect(None, X.format("devils-sight")) == {"senses": {"devilsSight": 120}}
    assert class_choices_2024.invocation_effect(None, "eldritch-invocation-devils-sight") == {"senses": {"devilsSight": 120}}
    assert class_choices_2024.invocation_effect(None, "opt-not-an-invocation-xphb") is None
    assert features.invocation_effects([], {"warlock": 3}) == []


# ---- the table is verified against the XPHB text -------------------------------------


def _records(catalog):
    return {r["index"]: r for r in class_choices_2024.invocation_records(catalog)}


@needs_data
def test_table_is_exhaustive_and_has_no_stray_keys(catalog):
    recs = _records(catalog)
    assert len(recs) == 28
    table = reference_data.INVOCATION_EFFECTS_2024
    assert set(table) <= set(recs)
    for fid, rec in recs.items():
        data_only = bool((rec.get("spells") or {}).get("innate")) or bool(rec.get("senses"))
        assert fid in table or data_only or fid in DEFERRED_C7C, fid
    assert not DEFERRED_C7C & set(table)  # deferred ids are not half-modelled
    for fid in DEFERRED_C7C:
        assert class_choices_2024.invocation_effect(catalog, fid) is None


@needs_data
def test_innate_spells_match_text_ids_and_levels(catalog):
    for fid, rec in _records(catalog).items():
        innate = (rec.get("spells") or {}).get("innate") or []
        assert len(innate) <= 1, fid
        eff = class_choices_2024.invocation_effect(catalog, fid)
        if not innate:
            assert not eff or "innate_spell" not in eff, fid
            continue
        spell = eff["innate_spell"]
        sp = catalog.spells[spell["spell"]]
        assert spell["spell"] == innate[0]["spell"] and spell["level"] == sp["level"]
        text = " ".join(rec["desc"]) if isinstance(rec["desc"], list) else rec["desc"]
        assert f"cast {sp['name']}" in text or fid == CHAIN, fid  # Chain: "learn the Find Familiar spell and can cast it"
        if fid == X.format("gift-of-the-depths"):
            assert spell["uses"] == "1/long rest" and "once" in text and "Long Rest" in text
        else:
            assert spell["uses"] == "at-will" and "Long Rest" not in text, fid
        if fid == CHAIN:
            assert "Magic action" in text and "without expending a spell slot" in text  # E6


@needs_data
def test_senses_and_notes_quote_the_text(catalog):
    recs = _records(catalog)
    assert "120 feet" in " ".join(recs[X.format("devils-sight")]["desc"])
    assert "Truesight with a range of 30 feet" in " ".join(recs[X.format("witch-sight")]["desc"])
    assert class_choices_2024.invocation_effect(catalog, X.format("witch-sight"))["senses"] == {"truesight": 30}
    assert "30 times your Warlock level" in " ".join(recs[SPEAR]["desc"])
    assert "minimum of one name" in " ".join(recs[X.format("gift-of-the-protectors")]["desc"])
    assert "swim" in " ".join(recs[X.format("gift-of-the-depths")]["desc"]).lower()


@needs_data
def test_warlock_feature_texts(catalog):
    cunning = " ".join(catalog.features["xphb-warlock-2-magical-cunning"]["desc"])
    assert "half your maximum (round up)" in cunning and "Long Rest" in cunning
    patron = " ".join(catalog.features["xphb-warlock-9-contact-patron"]["desc"])
    assert "Contact Other Plane" in patron and "without expending a spell slot" in patron and "Long Rest" in patron


@needs_data
def test_timing_warlock_20_with_ten_invocations(catalog):
    picks = [BLADE, X.format("thirsting-blade"), X.format("devouring-blade"), CHAIN, AGON, AGON + "~2", X.format("gift-of-the-depths"),
             X.format("witch-sight"), X.format("devils-sight"), X.format("armor-of-shadows")]
    c = ["eldritch-blast-xphb", "toll-the-dead-xphb"]
    r = _res(catalog, 20, picks, cantrips=c)
    assert len(r["derived"]["classResources"]) > 5
    laps = []
    for _ in range(20):
        t_run = time.perf_counter()
        _res(catalog, 20, picks, cantrips=c)
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
