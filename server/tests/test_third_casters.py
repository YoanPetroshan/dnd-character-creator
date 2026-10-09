"""Third-caster (Eldritch Knight / Arcane Trickster) spell slots, Part 2 of
docs/superpowers/plans/2026-10-09-feat-eligibility-third-casters-2024-overlays.md.
Slot rows were verified by script against class-fighter.json / class-rogue.json."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine import spells as spells_mod

pytestmark = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

EK, AT = "eldritch-knight-phb", "arcane-trickster-phb"


@pytest.fixture(scope="module")
def catalog():
    return load()


def slots(catalog, entries):
    return spells_mod.spell_slots_for(catalog, entries)


@pytest.mark.parametrize("level,expected", [
    (2, {}), (3, {"1": 2}), (4, {"1": 3}), (7, {"1": 4, "2": 2}), (10, {"1": 4, "2": 3}),
    (13, {"1": 4, "2": 3, "3": 2}), (16, {"1": 4, "2": 3, "3": 3}),
    (19, {"1": 4, "2": 3, "3": 3, "4": 1}), (20, {"1": 4, "2": 3, "3": 3, "4": 1}),
])
def test_eldritch_knight_single_class_slots(catalog, level, expected):
    assert slots(catalog, [("fighter", level, EK)])[0] == expected
    assert spells_mod.single_class_spell_slots(catalog, "fighter", level, EK) == expected


def test_arcane_trickster_xphb_has_the_same_slots(catalog):
    assert spells_mod.single_class_spell_slots(catalog, "rogue", 7, "arcane-trickster-xphb") == {"1": 4, "2": 2}


def test_non_caster_subclass_and_missing_subclass_have_no_slots(catalog):
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9, "champion") == {}
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9) == {}
    assert spells_mod.single_class_spell_slots(catalog, "fighter", 9, "no-such-subclass") == {}


def test_two_tuple_entries_still_work(catalog):
    assert slots(catalog, [("wizard", 5)])[0] == {"1": 4, "2": 3, "3": 2}


def test_combined_caster_level_adds_a_third(catalog):
    assert spells_mod.combined_caster_level([("fighter", 3, EK), ("wizard", 1)], catalog) == 2
    assert spells_mod.combined_caster_level([("fighter", 9, EK), ("cleric", 1)], catalog) == 4
    assert spells_mod.combined_caster_level([("fighter", 6, EK), ("rogue", 6, AT)], catalog) == 4
    assert spells_mod.combined_caster_level([("fighter", 9, "champion"), ("wizard", 1)], catalog) == 1
    assert spells_mod.combined_caster_level([("fighter", 9, EK)]) == 0  # no catalog: unknown subclass contributes nothing


def test_multiclass_third_caster_with_wizard(catalog):
    assert slots(catalog, [("fighter", 3, EK), ("wizard", 1)])[0] == {"1": 3}


def test_multiclass_third_caster_with_cleric(catalog):
    assert slots(catalog, [("fighter", 9, EK), ("cleric", 1)])[0] == {"1": 4, "2": 3}


def test_two_third_casters_combine(catalog):
    assert slots(catalog, [("fighter", 6, EK), ("rogue", 6, AT)])[0] == {"1": 4, "2": 3}


def test_non_caster_subclass_next_to_a_wizard_uses_the_wizard_row(catalog):
    assert slots(catalog, [("fighter", 9, "champion"), ("wizard", 1)])[0] == {"1": 2}


def test_pact_slots_stay_separate(catalog):
    shared, pact = slots(catalog, [("fighter", 3, EK), ("warlock", 2)])
    assert shared == {"1": 2}
    assert pact == {"1": 2}  # verified by script: a level-2 Warlock has two 1st-level pact slots (the plan guessed {"2": 2})


# ------------------------------------------------------------- B3 resolve

from engine.resolve import resolve  # noqa: E402

_BASE = {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}


def _draft(cls, level, sub, ruleset="mixed", choices=None, extra=None):
    d = {
        "ruleset": ruleset, "sources": [],
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": choices or {}}],
        "abilities": {"method": "manual", "base": dict(_BASE)},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
    }
    d.update(extra or {})
    return d


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(choice, oid):
    return next((o for o in choice["options"] if o["id"] == oid), None)


# Option counts verified by script (wizard list, 0 / 1..max slot level): mixed 31 cantrips,
# 43 at max level 1, 107 at max level 2; 2014 30 / 41 / 101.
@pytest.mark.parametrize("ruleset,cantrips,spells", [("mixed", 31, 43), ("2014", 30, 41)])
def test_eldritch_knight_3_choices(catalog, ruleset, cantrips, spells):
    res = resolve(_draft("fighter", 3, EK, ruleset), catalog)
    cant = _choice(res, "class:fighter:spells-cantrips")
    known = _choice(res, "class:fighter:spells-known")
    assert cant["count"] == 2 and len(cant["options"]) == cantrips
    assert known["count"] == 3 and len(known["options"]) == spells
    assert known["label"] == "Spells Known"
    assert "Wizard spell list" in known["description"]
    assert res["derived"]["spellSlots"] == {"1": 2}


def test_eldritch_knight_7_known_count_and_options(catalog):
    mixed = resolve(_draft("fighter", 7, EK), catalog)
    known = _choice(mixed, "class:fighter:spells-known")
    assert known["count"] == 5 and len(known["options"]) == 107
    assert mixed["derived"]["spellSlots"] == {"1": 4, "2": 2}
    old = resolve(_draft("fighter", 7, EK, "2014"), catalog)
    assert len(_choice(old, "class:fighter:spells-known")["options"]) == 101


def test_eldritch_knight_save_dc_and_attack(catalog):
    res = resolve(_draft("fighter", 3, EK), catalog)
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "fighter")
    assert entry["spellSaveDC"] == 13 and entry["spellAttackBonus"] == 5  # INT 16 (+3), prof +2


def test_eldritch_knight_xphb_is_prepared(catalog):
    res = resolve(_draft("fighter", 3, "eldritch-knight-xphb"), catalog)
    assert _choice(res, "class:fighter:spells-known")["label"] == "Prepared Spells"


def test_eldritch_knight_picks_flow_into_the_sheet(catalog):
    picks = {"class:fighter:spells-cantrips": ["fire-bolt", "light"], "class:fighter:spells-known": ["shield", "magic-missile", "burning-hands"]}
    res = resolve(_draft("fighter", 3, EK, choices=picks), catalog)
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "fighter")
    assert {s["id"] for s in entry["cantrips"]} == {"fire-bolt", "light"}
    assert {s["id"] for s in entry["known"]} == {"shield", "magic-missile", "burning-hands"}
    assert _choice(res, "class:fighter:spells-known")["status"] == "resolved"


def test_arcane_trickster_mage_hand_is_always_prepared(catalog):
    res = resolve(_draft("rogue", 3, AT), catalog)
    cant = _choice(res, "class:rogue:spells-cantrips")
    assert cant["count"] == 2
    mh = _opt(cant, "mage-hand")
    assert mh["disabled"] and mh["disabledReason"] == "always prepared (Arcane Trickster)"
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "rogue")
    assert [s["name"] for s in entry["alwaysPrepared"]] == ["Mage Hand"]


def test_arcane_trickster_xphb_disables_the_mage_hand_twin(catalog):
    res = resolve(_draft("rogue", 3, "arcane-trickster-xphb"), catalog)
    cant = _choice(res, "class:rogue:spells-cantrips")
    disabled = {o["id"] for o in cant["options"] if o.get("disabled")}
    assert "mage-hand" in disabled
    assert "mage-hand-xphb" in disabled or _opt(cant, "mage-hand-xphb") is None


def test_fighter_2_with_eldritch_knight_set_has_no_spell_choices(catalog):
    res = resolve(_draft("fighter", 2, EK), catalog)
    assert _choice(res, "class:fighter:spells-cantrips") is None
    assert _choice(res, "class:fighter:spells-known") is None
    assert res["derived"]["spellSlots"] == {}


def test_champion_has_no_spell_choices_or_slots(catalog):
    res = resolve(_draft("fighter", 9, "champion"), catalog)
    assert _choice(res, "class:fighter:spells-known") is None
    assert res["derived"]["spellSlots"] == {}


def test_multiclass_slots_in_resolve(catalog):
    d = _draft("fighter", 9, EK)
    d["classes"].append({"classId": "cleric", "level": 1, "choices": {}})
    res = resolve(d, catalog)
    assert res["derived"]["spellSlots"] == {"1": 4, "2": 3}


def test_eldritch_knight_4_can_take_war_caster_under_2014(catalog):
    picks = {"class:fighter:4:asi": ["feat:war-caster-phb"]}
    d = _draft("fighter", 4, EK, "2014", choices=picks, extra={"preferences": {"usePrerequisites": {"feats": True}}})
    res = resolve(d, catalog)
    asi = _choice(res, "class:fighter:4:asi")
    assert not _opt(asi, "feat:war-caster-phb").get("disabled")
    assert "feat:war-caster-phb" in asi["selected"]
    champ = resolve(_draft("fighter", 4, "champion", "2014", extra={"preferences": {"usePrerequisites": {"feats": True}}}), catalog)
    assert _opt(_choice(champ, "class:fighter:4:asi"), "feat:war-caster-phb")["disabled"]


# --------------------------------------------------- B4: 2014 school limits
# Verified by script (2014 ruleset, wizard list, slot level 1 / 2): 41 / 101 spells,
# of which abjuration+evocation 15 / 26 and enchantment+illusion 9 / 23.

def _known(res):
    return _choice(res, "class:fighter:spells-known")


def test_school_limit_groups_options_and_counts(catalog):
    res = resolve(_draft("fighter", 3, EK, "2014"), catalog)
    known = _known(res)
    groups = [o["group"] for o in known["options"]]
    assert groups.count("school") == 15 and groups.count("any-school") == 41 - 15
    assert groups == sorted(groups, key=lambda g: g != "school")  # school options first, headings stay consecutive
    assert all(not o.get("disabled") for o in known["options"])  # nothing picked yet


def test_one_outside_pick_is_allowed_at_level_3_then_outside_options_lock(catalog):
    picks = {"class:fighter:spells-known": ["burning-hands", "charm-person"]}
    known = _known(resolve(_draft("fighter", 3, EK, "2014", choices=picks), catalog))
    catapult = _opt(known, "catapult")
    assert catapult["disabled"] and "1 spell(s) may come from outside abjuration or evocation" in catapult["disabledReason"]
    assert not _opt(known, "alarm").get("disabled")
    assert not _opt(known, "charm-person").get("disabled")  # the selected outside pick stays toggle-able


def test_level_8_allows_two_outside_picks(catalog):
    one = {"class:fighter:spells-known": ["charm-person"]}
    known = _known(resolve(_draft("fighter", 8, EK, "2014", choices=one), catalog))
    assert not _opt(known, "catapult").get("disabled")
    two = {"class:fighter:spells-known": ["charm-person", "catapult"]}
    known = _known(resolve(_draft("fighter", 8, EK, "2014", choices=two), catalog))
    assert _opt(known, "jump")["disabled"]
    assert "2 spell(s)" in _opt(known, "jump")["disabledReason"]
    assert not _opt(known, "alarm").get("disabled")


def test_levelling_down_past_the_limit_warns(catalog):
    two = {"class:fighter:spells-known": ["charm-person", "catapult", "burning-hands"]}
    res = resolve(_draft("fighter", 3, EK, "2014", choices=two), catalog)
    assert any(p["id"] == "subclass-spell-school-limit-fighter" for p in res["problems"])
    ok = resolve(_draft("fighter", 3, EK, "2014", choices={"class:fighter:spells-known": ["charm-person", "alarm", "burning-hands"]}), catalog)
    assert not any(p["id"] == "subclass-spell-school-limit-fighter" for p in ok["problems"])


def test_arcane_trickster_uses_enchantment_and_illusion(catalog):
    res = resolve(_draft("rogue", 3, AT, "2014"), catalog)
    groups = [o["group"] for o in _choice(res, "class:rogue:spells-known")["options"]]
    assert groups.count("school") == 9


def test_xphb_subclass_has_no_school_limit(catalog):
    picks = {"class:fighter:spells-known": ["charm-person", "catapult", "jump"]}
    known = _known(resolve(_draft("fighter", 3, "eldritch-knight-xphb", "2014", choices=picks), catalog))
    assert not any(o.get("disabled") for o in known["options"])
    assert all(o["group"].startswith("spell-level-") for o in known["options"])



# ------------------------------------------------------------- B5 pruning

def test_levelling_down_prunes_the_extra_known_spells(catalog):
    six = ["shield", "magic-missile", "burning-hands", "alarm", "mage-armor", "thunderwave"]
    ok = resolve(_draft("fighter", 8, EK, "mixed", choices={"class:fighter:spells-known": six}), catalog)
    assert _known(ok)["count"] == 6 and _known(ok)["status"] == "resolved"
    down = resolve(_draft("fighter", 3, EK, "mixed", choices={"class:fighter:spells-known": six}), catalog)
    assert _known(down)["count"] == 3 and _known(down)["selected"] == six[:3]
    assert any(p["choiceId"] == "class:fighter:spells-known" and "now allows 3" in p["reason"] for p in down["pruned"])


def test_switching_to_champion_prunes_the_spell_picks(catalog):
    picks = {"class:fighter:spells-known": ["shield"], "class:fighter:spells-cantrips": ["light", "fire-bolt"]}
    res = resolve(_draft("fighter", 3, "champion", choices=picks), catalog)
    assert _known(res) is None
    reasons = {p["choiceId"]: p["reason"] for p in res["pruned"]}
    assert "no longer applies" in reasons["class:fighter:spells-known"]
    assert "no longer applies" in reasons["class:fighter:spells-cantrips"]
