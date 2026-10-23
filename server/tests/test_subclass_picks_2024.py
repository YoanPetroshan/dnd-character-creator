"""RP12 (F1, E13): 2024 subclass proficiency picks. Ruleset "2024" only; mixed / 2014 are unchanged.

Governing texts (catalog.features, XPHB records; `reference_data.SUBCLASS_PICKS_2024` carries a verbatim quote per
entry and `test_quotes_match_catalog` pins them):
  Lore Bard 3 Bonus Proficiencies   "You gain proficiency with three skills of your choice."
  Battle Master 3 Student of War    "proficiency with one type of Artisan's Tools of your choice" and "one skill of
                                    your choice from the skills available to Fighters at level 1"
  Fey Wanderer 3 Otherworldly Glamour
                                    "proficiency in one of these skills of your choice: Deception, Performance, or
                                    Persuasion" (+ a note: Charisma checks gain max(1, WIS))
  Gloom Stalker 7 Iron Mind         "You gain proficiency in Wisdom saving throws. If you already have this
                                    proficiency, you instead gain proficiency in Intelligence or Charisma saving
                                    throws (your choice)."

Rule matrix:
  cards          one card per pick (`class:<cls>:<lvl>:feature:<fid>`; Student of War's tool pick is
                 `class:fighter:3:tool-choice:<fid>`); no card below the record's level, without the subclass, under
                 mixed / 2014 (a hidden stored XPHB subclass) or with an SRD-only catalog
  options        Lore: the 18 skills; Student of War: the Fighter's 2024 level 1 list (classes_2024) and the 17
                 Artisan's Tools; Fey Wanderer: Deception / Performance / Persuasion; Iron Mind: INT / CHA
  effects        skills reach derived.skills and proficiencies.skills, tools proficiencies.tools, saves
                 proficiencies.savingThrows; the pick attaches to its row in sheet.features
  position order (Primal Knowledge generalised) a pick sees every proficiency gained at or before its (class order,
                 class level) and later cards see the pick: already-proficient options are disabled, a stored
                 duplicate is pruned; a later grant never converts a pick
  Iron Mind      WIS is fixed (no card) unless the Wisdom save is already proficient at Ranger 7 (Cleric first, a
                 Resilient (WIS) feat at an earlier ASI, Monk 14 ...); then a card INT / CHA (count 1) appears
  unavailable    a card with every option disabled is `unavailable` (never blocks export)"""
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import class_choices_2024
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

LORE = "class:bard:3:feature:lore-xphb-3-bonus-proficiencies"
SOW_SKILL = "class:fighter:3:feature:battle-master-xphb-3-student-of-war"
SOW_TOOL = "class:fighter:3:tool-choice:battle-master-xphb-3-student-of-war"
FEY = "class:ranger:3:feature:fey-wanderer-xphb-3-otherworldly-glamour"
IRON = "class:ranger:7:feature:gloom-stalker-xphb-7-iron-mind"
PK = "class:barbarian:3:feature:xphb-barbarian-3-primal-knowledge"
ARTISAN_TOOLS = {t["index"] for t in reference_data.TOOLS if t["category"] == "Artisan's Tools"}
FIGHTER_SKILLS = {"skill-acrobatics", "skill-animal-handling", "skill-athletics", "skill-history", "skill-insight",
                  "skill-intimidation", "skill-persuasion", "skill-perception", "skill-survival"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", background="sage-xphb", species="human-xphb", wis=12):
    """classes: (classId, level, subclassId | None, {cid: [picks]})."""
    entries = []
    for cls_id, level, sub, choices in classes:
        e = {"classId": cls_id, "level": level, "choices": choices}
        if sub:
            e["subclassId"] = sub
        entries.append(e)
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": wis, "CHA": 12}},
        "species": {"id": species}, "background": {"id": background},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": entries,
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _pruned(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


def _skills(res):
    return res["sheet"]["proficiencies"]["skills"]


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-xphb-" not in k}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- data -----------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    assert reference_data.SUBCLASS_PICKS_2024
    for spec in reference_data.SUBCLASS_PICKS_2024:
        rec = catalog.features[spec["feature"]]
        text = rec["name"] + " " + " ".join(rec["desc"])
        assert spec["quote"] in text, spec["feature"]
        assert spec.get("note_quote", "") in text, spec["feature"]
        assert (rec["subclass"] or {}).get("index") == spec["subclass"]
        assert (rec["class"] or {}).get("index") == spec["class"]
    assert {s["feature"] for s in reference_data.SUBCLASS_PICKS_2024} == {
        "lore-xphb-3-bonus-proficiencies", "battle-master-xphb-3-student-of-war",
        "fey-wanderer-xphb-3-otherworldly-glamour", "gloom-stalker-xphb-7-iron-mind"}


@needs_data
def test_fixed_numbers_match_catalog_text(catalog):
    lore = catalog.features["lore-xphb-3-bonus-proficiencies"]["desc"][0]
    assert "three skills of your choice" in lore
    glamour = " ".join(catalog.features["fey-wanderer-xphb-3-otherworldly-glamour"]["desc"])
    assert "bonus to the check equal to your Wisdom modifier (minimum of +1)" in glamour
    assert "Deception, Performance, or Persuasion" in glamour


# ---- the cards -------------------------------------------------------------------------------

@needs_data
def test_lore_bonus_proficiencies_card(catalog):
    assert _card(_res(catalog, [("bard", 2, "lore-xphb", {})]), LORE) is None
    assert _card(_res(catalog, [("bard", 3, None, {})]), LORE) is None
    assert _card(_res(catalog, [("bard", 3, "valor-xphb", {})]), LORE) is None
    res = _res(catalog, [("bard", 3, "lore-xphb", {})])
    card = _card(res, LORE)
    assert card["count"] == 3 and card["status"] == "pending" and card["label"] == "Bonus Proficiencies"
    assert card["source"] == {"kind": "class", "id": "bard", "label": "Bard", "level": 3}
    assert len(card["options"]) == 18 and {o["id"] for o in card["options"]} == set(reference_data.SKILL_NAMES)
    assert card["description"] == "\n\n".join(catalog.features["lore-xphb-3-bonus-proficiencies"]["desc"])


@needs_data
def test_lore_picks_are_proficiencies_and_row_choice(catalog):
    picks = ["skill-arcana", "skill-history", "skill-nature"]
    res = _res(catalog, [("bard", 3, "lore-xphb", {LORE: picks})], background="criminal-xphb")
    assert _card(res, LORE)["status"] == "resolved"
    base = _res(catalog, [("bard", 3, "lore-xphb", {})], background="criminal-xphb")
    for s in picks:
        assert s in _skills(res) and s not in _skills(base)
        # +2 proficiency instead of Jack of All Trades' +1 (Bard 2+)
        assert res["derived"]["skills"][s] - base["derived"]["skills"][s] == 1
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Bonus Proficiencies")
    assert row["choice"] == ["Arcana", "History", "Nature"]


@needs_data
def test_lore_overlap_with_background_uses_the_generic_reason(catalog):
    res = _res(catalog, [("bard", 3, "lore-xphb", {LORE: ["skill-arcana"]})], background="sage-xphb")
    assert _opt(_card(res, LORE), "skill-arcana")["disabledReason"] == "already granted by Sage"
    assert _card(res, LORE)["selected"] == []


@needs_data
def test_student_of_war_cards(catalog):
    assert _card(_res(catalog, [("fighter", 2, "battle-master-xphb", {})]), SOW_SKILL) is None
    res = _res(catalog, [("fighter", 3, "battle-master-xphb", {})])
    skill, tool = _card(res, SOW_SKILL), _card(res, SOW_TOOL)
    assert skill["count"] == 1 and tool["count"] == 1
    assert {o["id"] for o in skill["options"]} == FIGHTER_SKILLS
    assert _opt(skill, "skill-history")["disabledReason"] == "already granted by Sage"
    assert {o["id"] for o in tool["options"]} == ARTISAN_TOOLS and len(tool["options"]) == 17
    assert skill["label"] != tool["label"]
    assert skill["source"]["level"] == tool["source"]["level"] == 3


@needs_data
def test_student_of_war_list_is_the_2024_fighter_level_1_list(catalog):
    fighter = catalog.classes_2024["fighter"]
    expected = {(o["item"] or {})["index"] for ch in fighter["proficiency_choices"] for o in ch["from"]["options"]}
    res = _res(catalog, [("fighter", 3, "battle-master-xphb", {})], background="soldier-xphb")
    assert {o["id"] for o in _card(res, SOW_SKILL)["options"]} == expected


@needs_data
def test_student_of_war_picks_reach_the_sheet(catalog):
    ch = {"class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-survival"],
          SOW_SKILL: ["skill-insight"], SOW_TOOL: ["smiths-tools"]}
    res = _res(catalog, [("fighter", 3, "battle-master-xphb", ch)])
    assert _card(res, SOW_SKILL)["status"] == _card(res, SOW_TOOL)["status"] == "resolved"
    assert "skill-insight" in _skills(res)
    assert "smiths-tools" in res["sheet"]["proficiencies"]["tools"]
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Student of War")
    assert sorted(row["choice"]) == ["Insight", "Smith's Tools"]


@needs_data
def test_student_of_war_tool_already_proficient_is_disabled(catalog):
    res = _res(catalog, [("fighter", 3, "battle-master-xphb", {SOW_TOOL: ["carpenters-tools"]})],
               background="farmer-xphb")
    tool = _card(res, SOW_TOOL)
    assert _opt(tool, "carpenters-tools")["disabledReason"] == "already proficient"
    assert tool["selected"] == [] and tool["status"] == "pending"
    assert _pruned(res, SOW_TOOL)
    assert res["sheet"]["proficiencies"]["tools"].count("carpenters-tools") == 1


@needs_data
def test_fey_wanderer_card_and_note(catalog):
    assert _card(_res(catalog, [("ranger", 2, "fey-wanderer-xphb", {})]), FEY) is None
    res = _res(catalog, [("ranger", 3, "fey-wanderer-xphb", {FEY: ["skill-persuasion"]})], wis=8)
    card = _card(res, FEY)
    assert card["count"] == 1 and {o["id"] for o in card["options"]} == {
        "skill-deception", "skill-performance", "skill-persuasion"}
    assert "skill-persuasion" in _skills(res) and card["status"] == "resolved"
    note = next(r for r in res["derived"]["classResources"] if r["name"] == "Otherworldly Glamour")
    assert note["source"]["kind"] == "subclass" and note["uses"] is None
    assert "Charisma check" in note["details"]["note"] and "+1" in note["details"]["note"]  # WIS 8 -> minimum +1
    high = _res(catalog, [("ranger", 3, "fey-wanderer-xphb", {})], wis=18)
    note = next(r for r in high["derived"]["classResources"] if r["name"] == "Otherworldly Glamour")
    assert "+4" in note["details"]["note"]


@needs_data
def test_fey_wanderer_card_with_every_option_taken_is_unavailable(catalog):
    # Entertainer grants Acrobatics and Performance; Rogue 1 took Deception and Persuasion
    ch = {"class:rogue:1:prof-choice-0": ["skill-deception", "skill-persuasion", "skill-stealth", "skill-insight"]}
    res = _res(catalog, [("rogue", 1, None, ch), ("ranger", 3, "fey-wanderer-xphb", {})], background="entertainer-xphb")
    card = _card(res, FEY)
    assert all(o.get("disabled") for o in card["options"])
    assert card["status"] == "unavailable" and card["unavailableReason"]
    assert not [p for p in res["problems"] if "pending" in p.get("message", "")]


# ---- Iron Mind -----------------------------------------------------------------------------

@needs_data
def test_iron_mind_grants_wisdom_for_a_plain_ranger(catalog):
    res = _res(catalog, [("ranger", 6, "gloom-stalker-xphb", {})])
    assert _card(res, IRON) is None and "WIS" not in res["sheet"]["proficiencies"]["savingThrows"]
    res = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", {})])
    assert _card(res, IRON) is None
    assert res["sheet"]["proficiencies"]["savingThrows"] == ["STR", "DEX", "WIS"]


@needs_data
def test_iron_mind_wisdom_adds_the_proficiency_bonus(catalog):
    with_feature = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", {})])
    without = _res(catalog, [("ranger", 7, None, {})])
    assert with_feature["derived"]["savingThrows"]["WIS"] - without["derived"]["savingThrows"]["WIS"] == 3


@needs_data
def test_iron_mind_card_when_wisdom_is_already_proficient(catalog):
    # Cleric 1 first: Wisdom save from the class; Ranger 7 second
    res = _res(catalog, [("cleric", 1, None, {}), ("ranger", 7, "gloom-stalker-xphb", {})])
    card = _card(res, IRON)
    assert card is not None and card["count"] == 1 and card["status"] == "pending"
    assert {o["id"] for o in card["options"]} == {"int", "cha"}
    assert _opt(card, "cha")["disabledReason"] == "already proficient"  # the Cleric's own Charisma save
    assert not _opt(card, "int").get("disabled")
    res = _res(catalog, [("cleric", 1, None, {}), ("ranger", 7, "gloom-stalker-xphb", {IRON: ["int"]})])
    assert _card(res, IRON)["status"] == "resolved"
    assert res["sheet"]["proficiencies"]["savingThrows"] == ["WIS", "CHA", "INT"]
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Iron Mind")
    assert row["choice"] == ["Intelligence"]
    # a Paladin first (WIS + CHA) is the same; a Druid first (INT + WIS) leaves only Charisma
    res = _res(catalog, [("druid", 1, None, {}), ("ranger", 7, "gloom-stalker-xphb", {})])
    card = _card(res, IRON)
    assert _opt(card, "int")["disabledReason"] == "already proficient" and not _opt(card, "cha").get("disabled")


@needs_data
def test_iron_mind_card_when_an_earlier_resilient_feat_took_wisdom(catalog):
    asi = "class:ranger:4:asi:feat:resilient-xphb"
    ch = {"class:ranger:4:asi": ["feat:resilient-xphb"], f"{asi}:save-choice-0": ["wis"]}
    res = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", ch)])
    assert _card(res, IRON) is not None  # Resilient (WIS) at Ranger 4 comes before Iron Mind at 7
    ch[f"{asi}:save-choice-0"] = ["con"]
    assert _card(_res(catalog, [("ranger", 7, "gloom-stalker-xphb", ch)]), IRON) is None
    # Resilient taken at 8, after Iron Mind (the position of the card is Ranger 7): WIS is still granted outright
    asi8 = "class:ranger:8:asi:feat:resilient-xphb"
    res = _res(catalog, [("ranger", 8, "gloom-stalker-xphb", {"class:ranger:8:asi": ["feat:resilient-xphb"], f"{asi8}:save-choice-0": ["wis"]})])
    assert _card(res, IRON) is None


@needs_data
def test_iron_mind_position_cleric_after_ranger_does_not_add_a_card(catalog):
    # a second class grants no saving throws, and the Ranger comes first: WIS is not proficient at Ranger 7
    res = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", {}), ("cleric", 1, None, {})])
    assert _card(res, IRON) is None and "WIS" in res["sheet"]["proficiencies"]["savingThrows"]


@needs_data
def test_iron_mind_saves_already_held_are_disabled_and_dropped(catalog):
    # Monk 14 first (Disciplined Survivor: all saves), then Ranger 7: both alternatives are taken
    res = _res(catalog, [("monk", 14, None, {}), ("ranger", 7, "gloom-stalker-xphb", {IRON: ["int"]})])
    card = _card(res, IRON)
    assert card["status"] == "unavailable" and all(o.get("disabledReason") == "already proficient" for o in card["options"])
    assert card["selected"] == [] and _pruned(res, IRON)


@needs_data
def test_iron_mind_stored_pick_without_a_card_is_reported(catalog):
    res = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", {IRON: ["int"]})])
    assert _card(res, IRON) is None
    assert "INT" not in res["sheet"]["proficiencies"]["savingThrows"]
    assert _pruned(res, IRON)


@needs_data
def test_iron_mind_level_down_removes_the_card_and_prunes(catalog):
    res = _res(catalog, [("cleric", 1, None, {}), ("ranger", 6, "gloom-stalker-xphb", {IRON: ["int"]})])
    assert _card(res, IRON) is None and _pruned(res, IRON)
    assert "INT" not in res["sheet"]["proficiencies"]["savingThrows"]


# ---- positioned proficiency picks --------------------------------------------------------------

@needs_data
def test_earlier_class_skill_disables_the_lore_option(catalog):
    # Rogue 1 (class 0) takes Stealth; Bard 3 Lore is later in the build
    ch = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-insight", "skill-perception", "skill-acrobatics"]}
    res = _res(catalog, [("rogue", 1, None, ch), ("bard", 3, "lore-xphb", {LORE: ["skill-stealth", "skill-arcana"]})],
               background="soldier-xphb")
    card = _card(res, LORE)
    assert _opt(card, "skill-stealth")["disabledReason"] == "already proficient"
    assert card["selected"] == ["skill-arcana"] and card["status"] == "pending"
    assert _pruned(res, LORE) and "Stealth" in _pruned(res, LORE)[0]["reason"]
    assert _skills(res).count("skill-stealth") == 1


@needs_data
def test_lore_is_seen_by_a_later_multiclass_skill_card(catalog):
    # Bard 3 Lore (class 0) takes Stealth; the Rogue multiclass skill card comes after it
    rogue = "class:rogue:multiclass-prof-choice-0"
    res = _res(catalog, [("bard", 3, "lore-xphb", {LORE: ["skill-stealth", "skill-arcana", "skill-nature"]}),
                         ("rogue", 1, None, {rogue: ["skill-stealth"]})], background="soldier-xphb")
    card = _card(res, rogue)
    assert _opt(card, "skill-stealth")["disabledReason"] == "already proficient"
    assert card["selected"] == [] and _pruned(res, rogue)
    assert _card(res, LORE)["selected"] == ["skill-stealth", "skill-arcana", "skill-nature"]  # the earlier pick stays


@needs_data
def test_multiclass_skill_card_before_lore_wins_the_duplicate(catalog):
    rogue = "class:rogue:multiclass-prof-choice-0"
    res = _res(catalog, [("fighter", 1, None, {}), ("rogue", 1, None, {rogue: ["skill-stealth"]}),
                         ("bard", 3, "lore-xphb", {LORE: ["skill-stealth", "skill-arcana", "skill-nature"]})],
               background="soldier-xphb")
    card = _card(res, LORE)
    assert _opt(card, "skill-stealth")["disabledReason"] == "already proficient"
    assert card["selected"] == ["skill-arcana", "skill-nature"] and card["status"] == "pending"
    assert _card(res, rogue)["selected"] == ["skill-stealth"]


@needs_data
def test_a_later_asi_feat_card_sees_the_lore_picks(catalog):
    asi = "class:bard:4:asi:feat:skill-expert-xphb"
    ch = {LORE: ["skill-arcana", "skill-history", "skill-nature"], "class:bard:4:asi": ["feat:skill-expert-xphb"],
          f"{asi}:proficiency-choice-0": ["skill-arcana"]}
    res = _res(catalog, [("bard", 4, "lore-xphb", ch)], background="soldier-xphb")
    feat = _card(res, f"{asi}:proficiency-choice-0")
    assert _opt(feat, "skill-arcana")["disabledReason"] == "already proficient"
    assert feat["selected"] == [] and _pruned(res, f"{asi}:proficiency-choice-0")
    assert _card(res, LORE)["selected"] == ["skill-arcana", "skill-history", "skill-nature"]


@needs_data
def test_lore_after_barbarian_primal_knowledge_and_the_reverse(catalog):
    # Barbarian 3 (class 0) takes Athletics; Lore (class 1) sees it
    res = _res(catalog, [("barbarian", 3, None, {PK: ["skill-nature"]}),
                         ("bard", 3, "lore-xphb", {LORE: ["skill-nature", "skill-arcana", "skill-history"]})],
               background="soldier-xphb")
    assert _opt(_card(res, LORE), "skill-nature")["disabledReason"] == "already proficient"
    assert _card(res, PK)["selected"] == ["skill-nature"]
    # the Bard first: Primal Knowledge now yields to the Lore pick
    res = _res(catalog, [("bard", 3, "lore-xphb", {LORE: ["skill-nature", "skill-arcana", "skill-history"]}),
                         ("barbarian", 3, None, {PK: ["skill-nature"]})], background="soldier-xphb")
    pk = _card(res, PK)
    assert _opt(pk, "skill-nature")["disabledReason"] == "already proficient"
    assert pk["selected"] == [] and _pruned(res, PK)
    assert _card(res, LORE)["selected"] == ["skill-nature", "skill-arcana", "skill-history"]


@needs_data
def test_mercy_skills_count_for_a_later_pick_only(catalog):
    # Monk 3 Mercy (class 0) grants Insight + Medicine; the later Lore pick cannot repeat them
    res = _res(catalog, [("monk", 3, "mercy-xphb", {}), ("bard", 3, "lore-xphb", {LORE: ["skill-insight"]})],
               background="soldier-xphb")
    card = _card(res, LORE)
    assert _opt(card, "skill-insight")["disabledReason"] == "already proficient"
    assert _opt(card, "skill-medicine")["disabledReason"] == "already proficient"
    assert card["selected"] == []
    # Lore first: its pick stays (a later grant never converts a pick) and the skill is listed once
    res = _res(catalog, [("bard", 3, "lore-xphb", {LORE: ["skill-insight"]}), ("monk", 3, "mercy-xphb", {})],
               background="soldier-xphb")
    assert _card(res, LORE)["selected"] == ["skill-insight"]
    assert _skills(res).count("skill-insight") == 1 and "skill-medicine" in _skills(res)


@needs_data
def test_primal_knowledge_behaviour_is_unchanged(catalog):
    ch = {"class:barbarian:1:prof-choice-0": ["skill-athletics", "skill-perception"], PK: ["skill-athletics"]}
    res = _res(catalog, [("barbarian", 3, None, ch)])
    assert _card(res, PK)["selected"] == [] and _pruned(res, PK)
    assert class_choices_2024.is_primal_knowledge_card(_card(res, PK))
    assert class_choices_2024.is_positioned_proficiency_card(_card(res, PK))


# ---- rulesets and degradation ------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_card_outside_2024_with_a_hidden_stored_subclass(catalog, ruleset):
    for cls, level, sub in (("bard", 3, "lore-xphb"), ("fighter", 3, "battle-master-xphb"),
                            ("ranger", 7, "fey-wanderer-xphb"), ("ranger", 7, "gloom-stalker-xphb")):
        res = _res(catalog, [(cls, level, sub, {LORE: ["skill-nature"], FEY: ["skill-persuasion"]})], ruleset=ruleset)
        assert not [c for c in res["choices"] if c["id"] in (LORE, SOW_SKILL, SOW_TOOL, FEY, IRON)], (cls, ruleset)
        assert "skill-nature" not in _skills(res) and "skill-persuasion" not in _skills(res)
        stale = [p for p in res["pruned"] if p["choiceId"] in (LORE, FEY)]  # the generic "no longer applies" entries
        assert {p["choiceId"] for p in stale} <= {LORE, FEY}
        bare = _res(catalog, [(cls, level, sub, {})], ruleset=ruleset)
        assert res["sheet"] == bare["sheet"] and res["derived"] == bare["derived"]
        assert "Otherworldly Glamour" not in {r["name"] for r in res["derived"]["classResources"]}


@needs_data
def test_srd_only_catalog_has_no_pick_cards(catalog):
    bare = _srd_only(catalog)
    for cls, level, sub in (("bard", 3, "lore-xphb"), ("fighter", 3, "battle-master-xphb"),
                            ("ranger", 7, "fey-wanderer-xphb"), ("ranger", 7, "gloom-stalker-xphb")):
        res = resolve(_draft([(cls, level, sub, {})]), bare)
        assert not [c for c in res["choices"] if c["id"] in (LORE, SOW_SKILL, SOW_TOOL, FEY, IRON)]


@needs_data
def test_helper_isolation():
    assert class_choices_2024.pick_spec_for_card({"id": LORE, "source": {"kind": "class"}})["kind"] == "skills"
    assert class_choices_2024.pick_spec_for_card({"id": SOW_TOOL, "source": {"kind": "class"}})["kind"] == "tool"
    assert class_choices_2024.pick_spec_for_card({"id": "class:fighter:3:feature:xphb-fighter-3-x", "source": {"kind": "class"}}) is None
    assert class_choices_2024.pick_spec_for_card({"id": LORE, "source": {"kind": "feat"}}) is None
    order = ["rogue", "bard"]
    pos = class_choices_2024.proficiency_position
    assert pos({"id": "class:bard:multiclass-prof-choice-0", "source": {"kind": "class"}}, order) == (1, 1)
    assert pos({"id": LORE, "source": {"kind": "class"}}, order) == (1, 3)
    assert pos({"id": "species:x:proficiency-choice", "source": {"kind": "species"}}, order) == (-1, 0)


@needs_data
def test_mark_unavailable_covers_the_pick_cards():
    for cid in (LORE, SOW_SKILL, SOW_TOOL, FEY, IRON):
        card = {"id": cid, "source": {"kind": "class"}, "status": "pending", "count": 1, "selected": [],
                "options": [{"id": "a", "disabled": True}]}
        assert class_choices_2024.is_new_2024_class_card(card)
        assert class_choices_2024.mark_unavailable([card], "2024")[0]["status"] == "unavailable"
        assert class_choices_2024.mark_unavailable([card], "mixed")[0]["status"] == "pending"


# ---- timing ---------------------------------------------------------------------------------

@needs_data
def test_resolve_timing(catalog):
    drafts = [
        _draft([("fighter", 20, "battle-master-xphb", {})]), _draft([("wizard", 20, None, {})]),
        _draft([("bard", 20, "lore-xphb", {})]), _draft([("ranger", 20, "gloom-stalker-xphb", {})]),
        _draft([("cleric", 1, None, {}), ("ranger", 7, "gloom-stalker-xphb", {})]),
        _draft([("ranger", 20, "fey-wanderer-xphb", {})]),
        _draft([("fighter", 20, None, {})], ruleset="mixed"), _draft([("bard", 20, None, {})], ruleset="mixed"),
    ]
    for d in drafts:
        resolve(d, catalog)
        start = time.perf_counter()
        for _ in range(20):
            resolve(d, catalog)
        assert (time.perf_counter() - start) / 20 < 0.05
