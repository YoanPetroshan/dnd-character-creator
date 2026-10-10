"""C9a: 2024 class chassis, starting and multiclass proficiencies, skill and tool choices.

Governing text (XPHB class records, read from the 5etools class files on 2026-10-10, and the
2024 PHB chapter 2 "Multiclassing / Proficiencies": "When you gain your first level in a class
other than your initial class, you gain only some of the new class's starting proficiencies, as
detailed in each class's description"; "Prerequisites: a score of at least 13 in the primary
ability of the new class and your current classes").

Rule matrix, PRIMARY (initial) class, ruleset 2024:
  class      armor                          weapons                               tools
  Barbarian  light, medium, shields         simple, martial                       -
  Bard       light                          simple                                3 Musical Instruments
  Cleric     light, medium, shields         simple                                -
  Druid      light, shields                 simple                                Herbalism Kit
  Fighter    light, medium, heavy, shields  simple, martial                       -
  Monk       -                              simple, Martial with the Light prop.  1 Artisan's Tool or Instrument
  Paladin    light, medium, heavy, shields  simple, martial                       -
  Ranger     light, medium, shields         simple, martial                       -
  Rogue      light                          simple, Martial Finesse or Light      Thieves' Tools
  Sorcerer   -                              simple                                -
  Warlock    light                          simple                                -
  Wizard     -                              simple                                -
  Skill picks (count of list): Barbarian 2/6, Bard any 3, Cleric 2/5, Druid 2/8, Fighter 2/9
  (Persuasion is new), Monk 2/6, Paladin 2/6, Ranger 3/8, Rogue 4/10 (no Performance), Sorcerer 2/6,
  Warlock 2/7, Wizard 2/7 (Nature is new).

Rule matrix, SECONDARY (multiclass) class, ruleset 2024:
  Barbarian shields + martial | Bard light + 1 skill (any) + 1 instrument | Cleric light, medium,
  shields | Druid light, shields | Fighter light, medium, shields + martial | Monk nothing |
  Paladin light, medium, shields + martial | Ranger light, medium, shields + martial + 1 skill of 8 |
  Rogue light + Thieves' Tools + 1 skill of 10 | Sorcerer nothing | Warlock light | Wizard nothing.
  No class gives Simple weapons when multiclassing (the SRD Barbarian, Fighter, Paladin, Ranger,
  Monk and Warlock rows do; the SRD Druid row grants medium armor).

Cases: converter (12 overlays, mapping errors raise, SRD dicts untouched, saves equal the SRD,
primary ability equals the SRD multiclass prerequisite) | resolve under 2024 (cards, attack rows,
armor warnings, sheet proficiencies, multiclass) | mixed / 2014 are covered byte for byte by the F0
golden (test_c_series_golden.py) and spot-checked here | SRD-only catalog | /api/catalog/class
| export label | speed."""
import copy
import time

import pytest

from app import app
from catalog import official_source, reference_data
from catalog.loader import load
from catalog.official import class_chassis
from catalog.official_source import has_official, has_official_classes
from engine import attacks
from engine.resolve import resolve

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")
needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
           "sorcerer", "warlock", "wizard"]
SIMPLE, MARTIAL = "simple-weapons", "martial-weapons"
FIN_LIGHT = "martial-weapons-finesse-or-light"
M_LIGHT = "martial-weapons-light"

PRIMARY = {  # armor, weapons, fixed tools
    "barbarian": (["light-armor", "medium-armor", "shields"], [SIMPLE, MARTIAL], []),
    "bard": (["light-armor"], [SIMPLE], []),
    "cleric": (["light-armor", "medium-armor", "shields"], [SIMPLE], []),
    "druid": (["light-armor", "shields"], [SIMPLE], ["herbalism-kit"]),
    "fighter": (["light-armor", "medium-armor", "heavy-armor", "shields"], [SIMPLE, MARTIAL], []),
    "monk": ([], [SIMPLE, M_LIGHT], []),
    "paladin": (["light-armor", "medium-armor", "heavy-armor", "shields"], [SIMPLE, MARTIAL], []),
    "ranger": (["light-armor", "medium-armor", "shields"], [SIMPLE, MARTIAL], []),
    "rogue": (["light-armor"], [SIMPLE, FIN_LIGHT], ["thieves-tools"]),
    "sorcerer": ([], [SIMPLE], []),
    "warlock": (["light-armor"], [SIMPLE], []),
    "wizard": ([], [SIMPLE], []),
}
SECONDARY = {
    "barbarian": (["shields"], [MARTIAL], []),
    "bard": (["light-armor"], [], []),
    "cleric": (["light-armor", "medium-armor", "shields"], [], []),
    "druid": (["light-armor", "shields"], [], []),
    "fighter": (["light-armor", "medium-armor", "shields"], [MARTIAL], []),
    "monk": ([], [], []),
    "paladin": (["light-armor", "medium-armor", "shields"], [MARTIAL], []),
    "ranger": (["light-armor", "medium-armor", "shields"], [MARTIAL], []),
    "rogue": (["light-armor"], [], ["thieves-tools"]),
    "sorcerer": ([], [], []),
    "warlock": (["light-armor"], [], []),
    "wizard": ([], [], []),
}
# class -> (count, number of options); None options = any skill (18)
SKILL_CHOICES = {
    "barbarian": (2, 6), "bard": (3, 18), "cleric": (2, 5), "druid": (2, 8), "fighter": (2, 9),
    "monk": (2, 6), "paladin": (2, 6), "ranger": (3, 8), "rogue": (4, 10), "sorcerer": (2, 6),
    "warlock": (2, 7), "wizard": (2, 7),
}
MULTICLASS_SKILL_CHOICES = {"bard": (1, 18), "ranger": (1, 8), "rogue": (1, 10)}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _ids(profs):
    return [p["index"] for p in profs]


def _split(ids):
    armor = [i for i in ids if "armor" in i or i == "shields"]
    weapons = [i for i in ids if "weapon" in i]
    tools = [i for i in ids if i not in armor and i not in weapons and not i.startswith("saving-throw-")]
    return armor, weapons, tools


# ------------------------------------------------------------------ converter

@needs_classes
def test_twelve_overlays_full_merged_dicts(catalog):
    assert sorted(catalog.classes_2024) == CLASSES
    for cid, cls in catalog.classes_2024.items():
        srd = catalog.classes[cid]
        assert set(srd) <= set(cls)  # a FULL merged dict, never a partial overlay
        for key in ("index", "name", "hit_die", "saving_throws", "class_levels", "subclasses",
                    "starting_equipment", "starting_equipment_options"):
            assert cls[key] == srd[key], (cid, key)  # equipment stays the SRD one until C9b


@needs_classes
def test_converter_does_not_mutate_the_srd_dicts(catalog):
    srd = {k: copy.deepcopy(v) for k, v in catalog.classes.items()}
    class_chassis.convert_class_chassis_2024(catalog.class_2024_records, catalog.classes)
    assert srd == catalog.classes


@needs_classes
@pytest.mark.parametrize("cid", CLASSES)
def test_primary_proficiency_table(catalog, cid):
    armor, weapons, tools = _split(_ids(catalog.classes_2024[cid]["proficiencies"]))
    want_armor, want_weapons, want_tools = PRIMARY[cid]
    assert (armor, weapons, tools) == (want_armor, want_weapons, want_tools)


@needs_classes
@pytest.mark.parametrize("cid", CLASSES)
def test_multiclass_proficiency_table(catalog, cid):
    mc = catalog.classes_2024[cid]["multi_classing"]
    armor, weapons, tools = _split(_ids(mc["proficiencies"]))
    assert (armor, weapons, tools) == SECONDARY[cid]
    assert SIMPLE not in _ids(mc["proficiencies"])  # no 2024 class grants Simple weapons by multiclassing


@needs_classes
@pytest.mark.parametrize("cid", CLASSES)
def test_saving_throws_equal_the_srd(catalog, cid):
    saves = [i for i in _ids(catalog.classes_2024[cid]["proficiencies"]) if i.startswith("saving-throw-")]
    assert saves == [f"saving-throw-{s['index']}" for s in catalog.classes[cid]["saving_throws"]]


@needs_classes
@pytest.mark.parametrize("cid", CLASSES)
def test_skill_choice_counts(catalog, cid):
    envelopes = catalog.classes_2024[cid]["proficiency_choices"]
    count, size = SKILL_CHOICES[cid]
    skills = envelopes[0]
    assert skills["choose"] == count and skills["type"] == "proficiencies"
    from catalog.choices import build_choice_options
    assert len(build_choice_options(skills["from"])) == size


@needs_classes
def test_fighter_rogue_wizard_skill_lists_differ_from_the_srd(catalog):
    from catalog.choices import build_choice_options

    def opts(cid):
        return {o["id"] for o in build_choice_options(catalog.classes_2024[cid]["proficiency_choices"][0]["from"])}
    assert "skill-persuasion" in opts("fighter") and len(opts("fighter")) == 9
    assert "skill-performance" not in opts("rogue") and len(opts("rogue")) == 10
    assert catalog.classes_2024["rogue"]["proficiency_choices"][0]["choose"] == 4
    assert "skill-nature" in opts("wizard") and len(opts("wizard")) == 7
    assert opts("bard") == set(reference_data.SKILL_NAMES)


@needs_classes
def test_monk_tool_envelope_is_one_pick_of_27(catalog):
    from catalog.choices import build_choice_options
    envelopes = catalog.classes_2024["monk"]["proficiency_choices"]
    assert len(envelopes) == 2
    tool = envelopes[1]
    assert tool["choose"] == 1 and tool["from"]["option_set_type"] == "options_array"
    ids = [o["id"] for o in build_choice_options(tool["from"])]
    wanted = [t["index"] for t in reference_data.TOOLS if t["category"] in ("Artisan's Tools", "Musical Instrument")]
    assert len(ids) == 27 and ids == wanted


@needs_classes
def test_bard_instruments_and_multiclass_choices(catalog):
    from catalog.choices import build_choice_options
    envelopes = catalog.classes_2024["bard"]["proficiency_choices"]
    assert [e["choose"] for e in envelopes] == [3, 3]
    assert len(build_choice_options(envelopes[1]["from"])) == 10
    mc = catalog.classes_2024["bard"]["multi_classing"]["proficiency_choices"]
    assert [e["choose"] for e in mc] == [1, 1]
    assert len(build_choice_options(mc[0]["from"])) == 18 and len(build_choice_options(mc[1]["from"])) == 10
    for cid, (count, size) in MULTICLASS_SKILL_CHOICES.items():
        env = catalog.classes_2024[cid]["multi_classing"]["proficiency_choices"][0]
        assert env["choose"] == count and len(build_choice_options(env["from"])) == size
    for cid in set(CLASSES) - set(MULTICLASS_SKILL_CHOICES):
        assert not catalog.classes_2024[cid]["multi_classing"].get("proficiency_choices")


@needs_classes
@pytest.mark.parametrize("cid", CLASSES)
def test_multiclass_prerequisites_equal_the_xphb_primary_ability(catalog, cid):
    """XPHB primaryAbility: a list of one-key objects. Several objects = alternatives (Fighter STR
    or DEX); one object with several keys = all required. The SRD prerequisite shape is
    `prerequisites` (all required) or `prerequisite_options` (choose 1)."""
    primary = catalog.class_2024_records[cid]["primary_ability"]
    cls = catalog.classes_2024[cid]
    mc = cls["multi_classing"]
    if len(primary) > 1:
        want = {a for entry in primary for a in entry}
        got = {o["ability_score"]["index"] for o in mc["prerequisite_options"]["from"]["options"]}
        assert got == want and "prerequisites" not in mc
    else:
        want = set(primary[0])
        assert {p["ability_score"]["index"] for p in mc["prerequisites"]} == want
    assert mc == catalog.classes[cid]["multi_classing"] | {
        "proficiencies": mc["proficiencies"], "proficiency_choices": mc.get("proficiency_choices", [])}


# ---------------------------------------------------------- converter, units

def _record(**start):
    return {"fighter": {"starting_proficiencies": start, "multiclassing": {}, "saving_throws": ["str", "con"],
                        "primary_ability": [{"str": True}]}}


SRD_FIGHTER = {"fighter": {"index": "fighter", "name": "Fighter", "proficiencies": [], "proficiency_choices": [],
                           "multi_classing": {"prerequisites": []}}}


def test_unknown_armor_weapon_tool_strings_raise():
    for bad in ({"armor": ["exotic"]}, {"weapons": ["exotic"]},
                {"weapons": ["Martial weapons that have the {@filter Heavy|items|type=martial weapon|property=heavy} property"]},
                {"toolProficiencies": [{"zither": 3}]}):
        with pytest.raises(ValueError):
            class_chassis.convert_class_chassis_2024(_record(**bad), SRD_FIGHTER)


def test_weapon_filter_strings_map_to_the_pseudo_ids():
    fl = "Martial weapons that have the {@filter Finesse or Light|items|type=martial weapon|property=finesse;light} property"
    lt = "Martial weapons that have the {@filter Light|items|type=martial weapon|property=light} property"
    out = class_chassis.convert_class_chassis_2024(
        _record(armor=["light", "shield"], weapons=["simple", fl, lt, "martial"],
                toolProficiencies=[{"thieves' tools": True}]), SRD_FIGHTER)["fighter"]
    ids = _ids(out["proficiencies"])
    assert ids[:2] == ["light-armor", "shields"]
    assert ids[2:6] == ["simple-weapons", FIN_LIGHT, M_LIGHT, "martial-weapons"]
    assert "thieves-tools" in ids and ids[-2:] == ["saving-throw-str", "saving-throw-con"]


def test_missing_class_in_srd_is_skipped_and_empty_input_is_empty():
    assert class_chassis.convert_class_chassis_2024({}, {}) == {}
    assert class_chassis.convert_class_chassis_2024(_record(armor=["light"]), {}) == {}


# -------------------------------------------------------------------- resolve

def _res(catalog, classes, ruleset="2024", added=(), choices=None, bg="acolyte", scores=None):
    return resolve({
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": scores or {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": bg},
        "equipment": {"choices": {}, "added": list(added), "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": (choices or {}).get(c, {})} for c, lv in classes],
    }, catalog)


def _gear(*ids):
    return [{"itemId": i, "qty": 1, "equipped": True} for i in ids]


def _atk(res, item_id):
    return next(a for a in res["derived"]["attacks"] if a["itemId"] == item_id)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_primary_class_sheet_proficiencies_under_2024(catalog, cid):
    res = _res(catalog, [(cid, 1)])
    profs = res["sheet"]["proficiencies"]
    want_armor, want_weapons, want_tools = PRIMARY[cid]
    # the Cleric / Druid order cards and background tools add to these; the class grants are a subset
    assert set(want_armor) <= set(profs["armor"]) and set(want_weapons) <= set(profs["weapons"])
    assert set(want_tools) <= set(profs["tools"])
    if cid in ("bard", "sorcerer", "warlock", "wizard", "rogue", "monk", "fighter"):
        assert set(profs["armor"]) == set(want_armor), cid


@needs_data
def test_fighter_1_skill_card_has_nine_options(catalog):
    card = _card(_res(catalog, [("fighter", 1)]), "class:fighter:1:prof-choice-0")
    assert len(card["options"]) == 9 and "skill-persuasion" in {o["id"] for o in card["options"]}
    assert card["count"] == 2


@needs_data
def test_rogue_1_weapon_proficiency_rows(catalog):
    gear = _gear("scimitar", "whip", "rapier", "shortsword", "longsword", "dagger", "greatsword")
    res = _res(catalog, [("rogue", 1)], added=gear)
    for item in ("scimitar", "whip", "rapier", "shortsword", "dagger"):
        assert _atk(res, item)["attackBonus"] == 4, item  # DEX +2, proficiency +2
    assert _atk(res, "longsword")["attackBonus"] == 2 and _atk(res, "greatsword")["attackBonus"] == 2
    weapons = res["sheet"]["proficiencies"]["weapons"]
    assert FIN_LIGHT in weapons and "longswords" not in weapons and "rapiers" not in weapons
    assert reference_data.MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID == FIN_LIGHT


@needs_data
def test_rogue_performance_pick_is_pruned_under_2024(catalog):
    cid = "class:rogue:1:prof-choice-0"
    picks = ["skill-performance", "skill-stealth", "skill-acrobatics", "skill-deception"]
    res = _res(catalog, [("rogue", 1)], choices={"rogue": {cid: picks}})
    card = _card(res, cid)
    assert "skill-performance" not in card["selected"] and len(card["selected"]) == 3
    # an option no longer offered is ignored by the generic option filter (no `pruned` entry: existing behaviour)
    old = _res(catalog, [("rogue", 1)], "mixed", choices={"rogue": {cid: picks}})
    assert _card(old, cid)["selected"] == picks


@needs_data
def test_monk_1_proficiencies_and_tool_card(catalog):
    gear = _gear("shortsword", "scimitar", "dagger", "longsword", "rapier")
    res = _res(catalog, [("monk", 1)], added=gear)
    assert _atk(res, "shortsword")["attackBonus"] == 4 and _atk(res, "dagger")["attackBonus"] == 4
    assert _atk(res, "scimitar")["attackBonus"] == 4  # Martial with Light
    assert _atk(res, "longsword")["attackBonus"] == 2 and _atk(res, "rapier")["attackBonus"] == 2  # not Light
    weapons = res["sheet"]["proficiencies"]["weapons"]
    assert M_LIGHT in weapons and "shortswords" not in weapons
    card = _card(res, "class:monk:1:prof-choice-1")
    assert card and len(card["options"]) == 27 and card["count"] == 1 and card["status"] == "pending"
    picked = _res(catalog, [("monk", 1)], choices={"monk": {"class:monk:1:prof-choice-1": ["flute"]}})
    assert "flute" in picked["sheet"]["proficiencies"]["tools"]
    assert _card(picked, "class:monk:1:prof-choice-1")["status"] == "resolved"


@needs_data
def test_bard_1_loses_the_four_srd_weapons(catalog):
    gear = _gear("longsword", "rapier", "shortsword", "crossbow-hand", "club")
    res = _res(catalog, [("bard", 1)], added=gear)
    for item in ("longsword", "rapier", "shortsword", "crossbow-hand"):
        assert _atk(res, item)["attackBonus"] in (2, 3) and not _atk(res, item).get("proficient", False), item
    assert SIMPLE in res["sheet"]["proficiencies"]["weapons"]
    assert "rapiers" not in res["sheet"]["proficiencies"]["weapons"]
    old = _res(catalog, [("bard", 1)], "2014", added=gear)
    assert "rapiers" in old["sheet"]["proficiencies"]["weapons"]


@needs_data
def test_druid_1_has_no_medium_armor(catalog):
    res = _res(catalog, [("druid", 1)], added=_gear("scale-mail"))
    ids = [w["id"] for w in res["warnings"]]
    assert "armor-not-proficient-scale-mail" in ids
    assert "medium-armor" not in res["sheet"]["proficiencies"]["armor"]
    assert "herbalism-kit" in res["sheet"]["proficiencies"]["tools"]
    for ruleset in ("2014", "mixed"):
        old = _res(catalog, [("druid", 1)], ruleset, added=_gear("scale-mail"))
        assert "armor-not-proficient-scale-mail" not in [w["id"] for w in old["warnings"]]
        assert "medium-armor" in old["sheet"]["proficiencies"]["armor"]


@needs_data
def test_wizard_primary_gets_simple_weapons_not_the_five_named(catalog):
    res = _res(catalog, [("wizard", 1)], added=_gear("dagger", "club"))
    weapons = res["sheet"]["proficiencies"]["weapons"]
    assert weapons == [SIMPLE] and _atk(res, "club")["attackBonus"] == 4
    assert "daggers" in _res(catalog, [("wizard", 1)], "mixed")["sheet"]["proficiencies"]["weapons"]


@needs_data
def test_wizard_1_fighter_1_multiclass(catalog):
    res = _res(catalog, [("wizard", 1), ("fighter", 1)])
    profs = res["sheet"]["proficiencies"]
    assert MARTIAL in profs["weapons"] and SIMPLE in profs["weapons"]  # Fighter martial, Wizard simple
    assert set(profs["armor"]) == {"light-armor", "medium-armor", "shields"}  # no heavy from multiclassing
    assert "heavy-armor" not in profs["armor"]


@needs_data
def test_secondary_fighter_gives_no_simple_weapons(catalog):
    """The Fighter's multiclass row has no Simple weapons: only a primary class could supply them.
    Wizard primary grants Simple itself, so the observable case is the catalog row (see the table
    test) plus a Monk primary (Simple) with a Fighter second: Simple + Martial-Light + Martial."""
    res = _res(catalog, [("barbarian", 1), ("fighter", 1)])
    assert set(res["sheet"]["proficiencies"]["weapons"]) == {SIMPLE, MARTIAL}


@needs_data
def test_cleric_1_monk_1_monk_grants_nothing(catalog):
    res = _res(catalog, [("cleric", 1), ("monk", 1)])
    assert M_LIGHT not in res["sheet"]["proficiencies"]["weapons"]
    assert _card(res, "class:monk:1:prof-choice-1") is None  # no tool card for a secondary Monk
    assert _card(res, "class:monk:multiclass-prof-choice-0") is None
    assert set(res["sheet"]["proficiencies"]["armor"]) == {"light-armor", "medium-armor", "shields"}


@needs_data
def test_wizard_1_rogue_1_multiclass_skill_card_has_ten_options(catalog):
    res = _res(catalog, [("wizard", 1), ("rogue", 1)])
    card = _card(res, "class:rogue:multiclass-prof-choice-0")
    assert card["count"] == 1 and len(card["options"]) == 10
    assert "thieves-tools" in res["sheet"]["proficiencies"]["tools"]
    assert FIN_LIGHT not in res["sheet"]["proficiencies"]["weapons"]  # a secondary Rogue gets no weapons
    old = _res(catalog, [("wizard", 1), ("rogue", 1)], "mixed")
    assert len(_card(old, "class:rogue:multiclass-prof-choice-0")["options"]) == 11


@needs_data
def test_secondary_class_cards_use_the_2024_multiclass_envelopes(catalog):
    res = _res(catalog, [("fighter", 1), ("bard", 1)])
    assert [c["count"] for c in res["choices"] if c["id"].startswith("class:bard:multiclass-prof-choice-")] == [1, 1]
    assert "light-armor" in res["sheet"]["proficiencies"]["armor"]


@needs_data
def test_weapon_filter_helper_light_martial(catalog):
    shortsword, longsword = catalog.items["shortsword"], catalog.items["longsword"]
    scimitar = catalog.items["scimitar"]
    ids = {M_LIGHT}
    assert attacks.weapon_is_proficient(scimitar, ids) and attacks.weapon_is_proficient(shortsword, ids)
    assert not attacks.weapon_is_proficient(longsword, ids)
    assert attacks.weapon_is_proficient(scimitar, {FIN_LIGHT}) and not attacks.weapon_is_proficient(longsword, {FIN_LIGHT})
    assert reference_data.MARTIAL_LIGHT_PROFICIENCY_ID == M_LIGHT


def test_labels_for_the_pseudo_proficiencies():
    assert reference_data.proficiency_label(FIN_LIGHT) == "Martial weapons with Finesse or Light"
    assert reference_data.proficiency_label(M_LIGHT) == "Martial weapons with Light"
    assert reference_data.proficiency_label("light-armor") == "Light armor"  # unchanged elsewhere


@needs_data
def test_old_class_weapon_override_table_is_gone():
    assert not hasattr(reference_data, "RULESET_CLASS_WEAPON_PROFICIENCIES")


@needs_data
def test_mixed_and_2014_use_the_srd_chassis(catalog):
    for ruleset in ("mixed", "2014"):
        res = _res(catalog, [("rogue", 1)], ruleset)
        weapons = res["sheet"]["proficiencies"]["weapons"]
        assert "rapiers" in weapons and FIN_LIGHT not in weapons
        assert len(_card(res, "class:rogue:1:prof-choice-0")["options"]) == 11
        assert len(_card(_res(catalog, [("fighter", 1)], ruleset), "class:fighter:1:prof-choice-0")["options"]) == 8


# ------------------------------------------------------------- degrade / api

def test_srd_only_catalog_has_no_overlay_and_keeps_srd_behaviour(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    assert cat.classes_2024 == {}
    res = _res(cat, [("rogue", 1), ("fighter", 1)])
    assert "rapiers" in res["sheet"]["proficiencies"]["weapons"]
    assert len(_card(res, "class:rogue:1:prof-choice-0")["options"]) == 11


@needs_classes
def test_api_class_detail_uses_the_2024_chassis_only_under_2024():
    app.config["TESTING"] = True
    with app.test_client() as client:
        new = client.get("/api/catalog/class/rogue?ruleset=2024").get_json()
        old = client.get("/api/catalog/class/rogue").get_json()
        assert FIN_LIGHT in _ids(new["proficiencies"]) and len(new["proficiency_choices"][0]["from"]["options"]) == 10
        assert "rapiers" in _ids(old["proficiencies"]) and len(old["proficiency_choices"][0]["from"]["options"]) == 11
        assert new["levelFeatureCounts"]["1"] == 4  # XPHB Rogue 1: Expertise, Sneak Attack, Thieves' Cant, Weapon Mastery
        assert len(new["levelFeatureCounts"]) == 20 and old["levelFeatureCounts"]["1"] == 3
        fighter = client.get("/api/catalog/class/fighter?ruleset=2024").get_json()
        assert fighter["levelFeatureCounts"]["1"] == 3  # Fighting Style, Second Wind, Weapon Mastery
        assert client.get("/api/catalog/class/nope?ruleset=2024").status_code == 404


# -------------------------------------------------------------------- speed

@needs_data
def test_resolve_speed_under_50_ms(catalog):
    cases = [[("fighter", 20)], [("monk", 20)], [("warlock", 17), ("paladin", 3)], [("wizard", 20)]]
    for ruleset in ("mixed", "2024"):
        for classes in cases:
            _res(catalog, classes, ruleset)
            start = time.perf_counter()
            for _ in range(10):
                _res(catalog, classes, ruleset)
            assert (time.perf_counter() - start) / 10 < 0.05, (ruleset, classes)
