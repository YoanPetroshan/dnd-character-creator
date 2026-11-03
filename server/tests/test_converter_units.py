"""W12: focused unit tests for pure modules that were only exercised through resolve():
catalog/official/languages.py, catalog/official/innate_spells.py and engine/worn.py (pure, no 5etools data needed)."""
from catalog.official.innate_spells import (
    _clean_innate_spell_name, _innate_spell_ability, _innate_spell_uses_and_names, _innate_spells_from_5etools)
from catalog.official.languages import _language_grants_from_5etools, _language_ref_from_key
from engine import worn


# ---- languages ----
def test_language_ref_known_and_unknown():
    assert _language_ref_from_key("Deep Speech")["index"] == "deep-speech"
    assert _language_ref_from_key("klingon") is None


def test_fixed_language_only():
    fixed, env = _language_grants_from_5etools({"languageProficiencies": [{"giant": True}]})
    assert [f["index"] for f in fixed] == ["giant"] and env is None


def test_any_standard_is_a_resource_list_choice():
    fixed, env = _language_grants_from_5etools({"languageProficiencies": [{"anyStandard": 2}]})
    assert fixed == [] and env["choose"] == 2 and env["from"]["option_set_type"] == "resource_list"


def test_enumerated_choose_with_other_option():
    raw = {"languageProficiencies": [{"choose": {"from": ["elvish", "other"], "count": 1}}]}
    fixed, env = _language_grants_from_5etools(raw)
    assert env["choose"] == 1 and env["from"]["option_set_type"] == "options_array"
    assert [o["item"]["index"] for o in env["from"]["options"]] == ["elvish", "other"]


def test_fixed_plus_wildcard_on_same_entry_is_additive():
    fixed, env = _language_grants_from_5etools({"languageProficiencies": [{"giant": True, "anyStandard": 1}]})
    assert [f["index"] for f in fixed] == ["giant"] and env["choose"] == 1


def test_split_entries_fixed_then_wildcard_keeps_only_the_fixed_grant():
    raw = {"languageProficiencies": [{"dwarvish": True}, {"anyStandard": 1}]}
    fixed, env = _language_grants_from_5etools(raw)
    assert [f["index"] for f in fixed] == ["dwarvish"] and env is None


def test_no_language_field():
    assert _language_grants_from_5etools({}) == ([], None)


# ---- innate spells ----
def test_clean_innate_spell_name():
    assert _clean_innate_spell_name("light|xphb") == "light"
    assert _clean_innate_spell_name("hellish rebuke#2") == "hellish rebuke"


def test_uses_and_names_shapes():
    assert _innate_spell_uses_and_names(["a", "b"]) == ("at-will", ["a", "b"])
    assert _innate_spell_uses_and_names({"daily": {"1": ["a"]}}) == ("1/day", ["a"])
    assert _innate_spell_uses_and_names({"rest": {"1": ["a"]}}) == ("1/day", ["a"])
    assert _innate_spell_uses_and_names({"weird": 1}) == ("at-will", [])


def test_ability_shapes():
    assert _innate_spell_ability("cha") == "CHA"
    assert _innate_spell_ability({"choose": ["int", "wis"]}) == {"choose": ["INT", "WIS"]}
    assert _innate_spell_ability({"choose": []}) is None
    assert _innate_spell_ability(None) is None


def test_innate_spells_from_5etools_variants_and_levels():
    raw = {"additionalSpells": [
        {"name": "Drow", "ability": "cha", "innate": {"1": ["dancing lights"], "3": {"daily": {"1": ["faerie fire"]}}}},
        {"name": "High", "innate": {"x": ["skip"]}},
        "junk",
    ]}
    out = _innate_spells_from_5etools(raw)
    assert [(s["spell_id"], s["level"], s["uses"], s["ability"], s["variant"]) for s in out] == [
        ("dancing-lights", 1, "at-will", "CHA", "Drow"), ("faerie-fire", 3, "1/day", "CHA", "Drow")]
    assert _innate_spells_from_5etools({}) == []


# ---- worn (pure helpers and warnings) ----
SHIELD = {"index": "shield", "name": "Shield", "equipment_category": {"index": "armor"}, "armor_category": "Shield"}
PLATE = {"index": "plate", "name": "Plate", "equipment_category": {"index": "armor"}, "armor_category": "Heavy"}
GREATSWORD = {"index": "greatsword", "name": "Greatsword", "equipment_category": {"index": "weapon"},
              "properties": [{"index": "two-handed"}]}
DAGGER = {"index": "dagger", "name": "Dagger", "equipment_category": {"index": "weapon"}, "properties": []}
LOOKUP = {i["index"]: i for i in (SHIELD, PLATE, GREATSWORD, DAGGER)}


def _inv(*items):
    return {i["index"]: {"item": i, "qty": 1} for i in items}


def test_classifiers():
    assert worn.is_shield(SHIELD) and not worn.is_body_armor(SHIELD)
    assert worn.is_body_armor(PLATE) and worn.is_weapon(DAGGER)
    assert worn.is_two_handed(GREATSWORD) and not worn.is_two_handed(DAGGER)


def test_slot_options_lists_hands_and_armor():
    opts = worn.slot_options(_inv(SHIELD, PLATE, GREATSWORD))
    assert [a["itemId"] for a in opts["armor"]] == ["plate"]
    assert [s["itemId"] for s in opts["shield"]] == ["shield"]
    assert {h["itemId"]: h["twoHanded"] for h in opts["hands"]} == {"shield": False, "greatsword": True}


def test_apply_without_slots_is_auto():
    gear = worn.apply([PLATE, SHIELD], {}, _inv(PLATE, SHIELD), LOOKUP)
    assert gear.worn is None and gear.wielded is None and gear.warnings == []
    assert gear.slots["current"] == {"armor": "plate", "shield": True}


def test_worn_armor_null_removes_body_armor():
    gear = worn.apply([PLATE], {"worn": {"armor": None}}, _inv(PLATE), LOOKUP)
    assert gear.items == [] and gear.worn == {"armor": None, "shield": False, "manual": True}


def test_worn_shield_missing_and_not_in_inventory():
    gear = worn.apply([], {"worn": {"shield": True, "armor": "plate"}}, _inv(DAGGER), LOOKUP)
    ids = {w["id"] for w in gear.warnings}
    assert ids == {"worn-shield-missing", "worn-armor-not-in-inventory"}
    assert gear.pruned[0]["choiceId"] == "equipment:worn:armor"


def test_wielded_two_handed_conflict_and_unknown_item():
    gear = worn.apply([GREATSWORD, DAGGER], {"wielded": {"main": "greatsword", "off": "dagger"}},
                      _inv(GREATSWORD, DAGGER), LOOKUP)
    assert "wielded-two-handed-conflict" in {w["id"] for w in gear.warnings}
    assert gear.hands == {"main": "greatsword", "off": "dagger", "dueling_ok": False}
    gear = worn.apply([], {"wielded": {"main": "nope"}}, {}, LOOKUP)
    assert gear.warnings[0]["id"] == "wielded-main-unknown-item"
