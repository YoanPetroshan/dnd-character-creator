"""C6b-1: 2024 Expertise cards (Bard, Rogue, Ranger, Wizard) and the removal of the SRD Ranger cards.

Rules (XPHB class features, text read from catalog.features on 2026-10-10):
  Bard 2 / 9, Rogue 1 / 6   "You gain Expertise in two of your skill proficiencies of your choice."
  Ranger 9                  "Choose two of your skill proficiencies with which you lack Expertise."
  Ranger 2 Deft Explorer    "Choose one of your skill proficiencies with which you lack Expertise."
  Wizard 2 Scholar          "Choose one of the following skills in which you have proficiency: Arcana,
                             History, Investigation, Medicine, Nature, or Religion."
Decision E1: only Deft Explorer and Ranger 9 forbid a skill that already has Expertise; the other
cards allow a duplicate (wasted). 2024 Expertise is skills only (no thieves' tools).

Matrix: ruleset (2024 / mixed / 2014) x class (Bard 1/2/9, Rogue 1/6, Ranger 1/2/6/9/14, Wizard 1/2)
x proficiency (proficient / not) x duplicate source (earlier card, feat card) x flagged / unflagged
card x multiclass (Bard 9 / Rogue 6) x sheet.features attachment x derived.skills x stored 2014
picks (pruned) x catalog (real XPHB / SRD-only) x timing."""
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from catalog.reference_data import EXPERTISE_2024, SKILL_NAMES, SRD_CARDS_REPLACED_2024
from engine import class_choices_2024, sheet_features
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

BARD2, BARD9 = "class:bard:2:expertise-choice:xphb-bard-2-expertise", "class:bard:9:expertise-choice:xphb-bard-9-expertise"
ROGUE1, ROGUE6 = "class:rogue:1:expertise-choice:xphb-rogue-1-expertise", "class:rogue:6:expertise-choice:xphb-rogue-6-expertise"
DEFT = "class:ranger:2:expertise-choice:xphb-ranger-2-deft-explorer"
RANGER9 = "class:ranger:9:expertise-choice:xphb-ranger-9-expertise"
SCHOLAR = "class:wizard:2:expertise-choice:xphb-wizard-2-scholar"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", background="acolyte", scores=None):
    base = {"STR": 10, "DEX": 16, "CON": 12, "INT": 14, "WIS": 14, "CHA": 14}
    base.update(scores or {})
    return {
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
        "species": {"id": "human"}, "background": {"id": background},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _expertise_cards(res):
    return [c["id"] for c in res["choices"] if "expertise-choice" in c["id"]]


def _srd_only(catalog):
    """A catalog without any XPHB class data: no XPHB features, records or level lists."""
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith("xphb-")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- data -----------------------------------------------------------------------------------

def test_expertise_table_matches_the_rules():
    assert {fid: (e["class"], e["level"], e["count"], e["lacks_expertise"]) for fid, e in EXPERTISE_2024.items()} == {
        "xphb-bard-2-expertise": ("bard", 2, 2, False), "xphb-bard-9-expertise": ("bard", 9, 2, False),
        "xphb-rogue-1-expertise": ("rogue", 1, 2, False), "xphb-rogue-6-expertise": ("rogue", 6, 2, False),
        "xphb-ranger-2-deft-explorer": ("ranger", 2, 1, True), "xphb-ranger-9-expertise": ("ranger", 9, 2, True),
        "xphb-wizard-2-scholar": ("wizard", 2, 1, False),
    }
    assert EXPERTISE_2024["xphb-wizard-2-scholar"]["skills"] == [
        "skill-arcana", "skill-history", "skill-investigation", "skill-medicine", "skill-nature", "skill-religion"]
    assert set(SRD_CARDS_REPLACED_2024) == {"bard", "rogue", "ranger", "sorcerer", "warlock"}  # sorcerer: C6c-1 Metamagic, warlock: C7a invocations


@needs_data
def test_every_entry_matches_its_xphb_feature_and_class_level(catalog):
    for fid, e in EXPERTISE_2024.items():
        assert fid in catalog.features, fid
        assert fid in catalog.class_2024_level_features[e["class"]][e["level"]], fid
    for fid in ("xphb-ranger-2-deft-explorer", "xphb-ranger-9-expertise"):
        assert "lack Expertise" in " ".join(catalog.features[fid]["desc"])
    for fid, e in EXPERTISE_2024.items():
        if not e["lacks_expertise"]:
            assert "lack Expertise" not in " ".join(catalog.features[fid]["desc"]), fid


# ---- Bard -----------------------------------------------------------------------------------

@needs_data
def test_bard_cards_by_level(catalog):
    assert _expertise_cards(_res(catalog, [("bard", 1, {})])) == []
    res = _res(catalog, [("bard", 2, {})])
    card = _card(res, BARD2)
    assert _expertise_cards(res) == [BARD2]
    assert card["count"] == 2 and card["status"] == "pending" and card["label"] == "Expertise"
    assert card["source"] == {"kind": "class", "id": "bard", "label": "Bard", "level": 2}
    assert [o["id"] for o in card["options"]] == list(SKILL_NAMES) and len(card["options"]) == 18
    assert "thieves-tools" not in {o["id"] for o in card["options"]}
    assert "Expertise in two of your skill proficiencies" in card["description"]
    assert set(_expertise_cards(_res(catalog, [("bard", 9, {})]))) == {BARD2, BARD9}
    assert "lacksExpertise" not in card  # internal key, stripped from the output


@needs_data
def test_no_srd_bard_card_under_2024_and_stored_srd_pick_is_pruned(catalog):
    res = _res(catalog, [("bard", 10, {"class:bard:3:expertise-choice:bard-expertise-1": ["skill-persuasion"]})])
    assert not [c for c in res["choices"] if "bard-expertise" in c["id"]]
    assert "class:bard:3:expertise-choice:bard-expertise-1" in {p["choiceId"] for p in res["pruned"]}


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_bard_and_rogue_cards_are_the_srd_ones_outside_2024(catalog, ruleset):
    res = _res(catalog, [("bard", 3, {})], ruleset=ruleset)
    assert _expertise_cards(res) == ["class:bard:3:expertise-choice:bard-expertise-1"]
    res = _res(catalog, [("rogue", 1, {})], ruleset=ruleset)
    assert _expertise_cards(res) == ["class:rogue:1:expertise-choice:rogue-expertise-1"]
    assert "thieves-tools" in {o["id"] for o in _card(res, _expertise_cards(res)[0])["options"]}  # SRD: skill or tools
    res = _res(catalog, [("wizard", 2, {})], ruleset=ruleset)
    assert _card(res, SCHOLAR) is None
    res = _res(catalog, [("ranger", 2, {})], ruleset=ruleset)
    assert _card(res, DEFT) is None
    assert [c["id"] for c in res["choices"] if ":enemy-type:" in c["id"] or ":terrain-type:" in c["id"]]


# ---- Rogue ----------------------------------------------------------------------------------

@needs_data
def test_rogue_1_and_6(catalog):
    res = _res(catalog, [("rogue", 1, {})])
    card = _card(res, ROGUE1)
    assert _expertise_cards(res) == [ROGUE1] and card["count"] == 2
    assert "thieves-tools" not in {o["id"] for o in card["options"]}
    assert set(_expertise_cards(_res(catalog, [("rogue", 6, {})]))) == {ROGUE1, ROGUE6}


@needs_data
def test_expertise_requires_proficiency_and_derived_skills_add_it(catalog):
    """Rogue 1, DEX 16, prof bonus +2: Stealth proficient + Expertise = 3 + 2 * 2 = 7."""
    picks = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"]}
    res = _res(catalog, [("rogue", 1, picks)])
    card = _card(res, ROGUE1)
    assert _opt(card, "skill-stealth").get("disabled") is None
    athletics = _opt(card, "skill-athletics")  # Rogue list has it, but it was not picked
    assert athletics["disabled"] and athletics["disabledReason"] == "not proficient"
    assert _opt(card, "skill-religion").get("disabled") is None  # Acolyte grants it
    base = res["derived"]["skills"]["skill-stealth"]
    assert base == 3 + 2
    picks[ROGUE1] = ["skill-stealth", "skill-acrobatics"]
    res = _res(catalog, [("rogue", 1, picks)])
    assert _card(res, ROGUE1)["status"] == "resolved"
    assert res["derived"]["skills"]["skill-stealth"] == 3 + 4
    assert set(res["sheet"]["expertiseSkills"]) == {"skill-stealth", "skill-acrobatics"}
    # a pick the character is not proficient in is dropped with a pruned entry
    picks[ROGUE1] = ["skill-stealth", "skill-athletics"]
    res = _res(catalog, [("rogue", 1, picks)])
    assert _card(res, ROGUE1)["selected"] == ["skill-stealth"]
    assert any(p["choiceId"] == ROGUE1 and "no longer a proficient skill" in p["reason"] for p in res["pruned"])


@needs_data
def test_unflagged_cards_allow_a_duplicate_expertise(catalog):
    """E1: Rogue 6 may name a skill the level 1 card already doubled (it is simply wasted)."""
    picks = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
             ROGUE1: ["skill-stealth", "skill-acrobatics"], ROGUE6: ["skill-stealth", "skill-perception"]}
    res = _res(catalog, [("rogue", 6, picks)])
    assert _opt(_card(res, ROGUE6), "skill-stealth").get("disabled") is None
    assert _card(res, ROGUE6)["selected"] == ["skill-stealth", "skill-perception"]
    assert not [p for p in res["pruned"] if p["choiceId"] == ROGUE6]


# ---- Ranger ---------------------------------------------------------------------------------

RANGER_SKILLS = ["skill-stealth", "skill-nature", "skill-survival"]


@needs_data
def test_ranger_has_no_srd_enemy_or_terrain_cards_under_2024(catalog):
    for level in (1, 6, 14):
        res = _res(catalog, [("ranger", level, {})])
        assert not [c for c in res["choices"] if ":enemy-type:" in c["id"] or ":terrain-type:" in c["id"]], level
    old = {"class:ranger:1:enemy-type:favored-enemy-1-type": ["undead"],
           "class:ranger:1:terrain-type:natural-explorer-1-terrain-type": ["forest"]}
    res = _res(catalog, [("ranger", 1, old)])
    assert set(old) <= {p["choiceId"] for p in res["pruned"]}


@needs_data
def test_deft_explorer_card_and_ranger_9_card(catalog):
    assert _card(_res(catalog, [("ranger", 1, {})]), DEFT) is None
    res = _res(catalog, [("ranger", 2, {"class:ranger:1:prof-choice-0": RANGER_SKILLS})])
    card = _card(res, DEFT)
    assert card["count"] == 1 and card["label"] == "Deft Explorer" and len(card["options"]) == 18
    assert "lack Expertise" in card["description"]
    assert _opt(card, "skill-stealth").get("disabled") is None
    assert _opt(card, "skill-arcana")["disabledReason"] == "not proficient"
    res = _res(catalog, [("ranger", 9, {})])
    assert _card(res, RANGER9)["count"] == 2
    assert [c for c in _expertise_cards(res)] == [DEFT, RANGER9]


@needs_data
def test_lacks_expertise_blocks_a_skill_already_expert_from_an_earlier_card(catalog):
    """Rogue 1 (Expertise Stealth) then Ranger 2: Deft Explorer cannot take Stealth again."""
    scores = {"DEX": 16, "WIS": 14}
    picks_rogue = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
                   ROGUE1: ["skill-stealth", "skill-acrobatics"]}
    picks_ranger = {"class:ranger:multiclass-prof-choice-0": ["skill-nature"]}
    res = _res(catalog, [("rogue", 1, picks_rogue), ("ranger", 2, picks_ranger)], scores=scores)
    deft = _card(res, DEFT)
    assert _opt(deft, "skill-stealth")["disabled"] and _opt(deft, "skill-stealth")["disabledReason"] == "already has Expertise"
    assert _opt(deft, "skill-perception").get("disabled") is None
    # a stored Stealth pick is dropped and reported
    picks_ranger[DEFT] = ["skill-stealth"]
    res = _res(catalog, [("rogue", 1, picks_rogue), ("ranger", 2, picks_ranger)], scores=scores)
    deft = _card(res, DEFT)
    assert deft["selected"] == [] and deft["status"] == "pending"
    assert any(p["choiceId"] == DEFT and "already has Expertise" in p["reason"] for p in res["pruned"])
    # another skill is fine, and the Rogue card is untouched
    picks_ranger[DEFT] = ["skill-perception"]
    res = _res(catalog, [("rogue", 1, picks_rogue), ("ranger", 2, picks_ranger)], scores=scores)
    assert _card(res, DEFT)["selected"] == ["skill-perception"]
    assert _card(res, ROGUE1)["selected"] == ["skill-stealth", "skill-acrobatics"]


@needs_data
def test_lacks_expertise_blocks_the_later_feat_pick_in_level_order(catalog):
    """F3a-3: Skill Expert (Ranger ASI at level 4) is walked at its real position, after Deft Explorer (level 2),
    so the feat pick is the duplicate (it used to win because every feat card was walked first)."""
    picks = {
        "class:ranger:1:prof-choice-0": RANGER_SKILLS,
        "class:ranger:4:asi": ["feat:skill-expert-xphb"],
        "class:ranger:4:asi:feat:skill-expert-xphb:proficiency-choice-0": ["skill-perception"],
        "class:ranger:4:asi:feat:skill-expert-xphb:expertise-choice-0": ["skill-stealth"],
        "class:ranger:4:asi:feat:skill-expert-xphb:ability-bonus": ["WIS"],
        DEFT: ["skill-stealth"],
    }
    res = _res(catalog, [("ranger", 4, picks)])
    feat_card = _card(res, "class:ranger:4:asi:feat:skill-expert-xphb:expertise-choice-0")
    assert feat_card["selected"] == [] and feat_card["status"] == "pending"
    assert _opt(feat_card, "skill-stealth")["disabledReason"] == "already has Expertise"
    deft = _card(res, DEFT)
    assert deft["selected"] == ["skill-stealth"]


@needs_data
def test_ranger_9_second_card_is_pruned_for_a_duplicate_of_the_first(catalog):
    picks = {"class:ranger:1:prof-choice-0": RANGER_SKILLS, DEFT: ["skill-stealth"],
             RANGER9: ["skill-stealth", "skill-nature"]}
    res = _res(catalog, [("ranger", 9, picks)])
    assert _card(res, DEFT)["selected"] == ["skill-stealth"]
    r9 = _card(res, RANGER9)
    assert r9["selected"] == ["skill-nature"] and r9["status"] == "pending"
    assert _opt(r9, "skill-stealth")["disabledReason"] == "already has Expertise"
    assert any(p["choiceId"] == RANGER9 and "Stealth" in p["reason"] for p in res["pruned"])
    picks[RANGER9] = ["skill-survival", "skill-nature"]
    res = _res(catalog, [("ranger", 9, picks)])
    assert _card(res, RANGER9)["status"] == "resolved"
    assert set(res["sheet"]["expertiseSkills"]) == {"skill-stealth", "skill-survival", "skill-nature"}


# ---- Wizard ---------------------------------------------------------------------------------

@needs_data
def test_scholar_options_and_proficiency(catalog):
    assert _card(_res(catalog, [("wizard", 1, {})]), SCHOLAR) is None
    picks = {"class:wizard:1:prof-choice-0": ["skill-arcana", "skill-history"]}
    res = _res(catalog, [("wizard", 2, picks)])
    card = _card(res, SCHOLAR)
    assert card["count"] == 1 and card["label"] == "Scholar"
    assert [o["id"] for o in card["options"]] == EXPERTISE_2024["xphb-wizard-2-scholar"]["skills"]
    enabled = {o["id"] for o in card["options"] if not o.get("disabled")}
    assert enabled == {"skill-arcana", "skill-history", "skill-religion"}  # Acolyte grants Religion
    assert _opt(card, "skill-nature")["disabledReason"] == "not proficient"
    picks_nature = {"class:wizard:1:prof-choice-0": ["skill-nature", "skill-history"], SCHOLAR: ["skill-nature"]}
    res = _res(catalog, [("wizard", 2, picks_nature)])
    assert _card(res, SCHOLAR)["status"] == "resolved"
    assert "skill-nature" in res["sheet"]["expertiseSkills"]
    assert res["derived"]["skills"]["skill-nature"] == 2 + 4  # INT 14 (+2), proficiency +2 doubled by Expertise


# ---- multiclass and sheet.features ----------------------------------------------------------

@needs_data
def test_bard_9_rogue_6_has_four_cards_attached_to_their_own_xphb_rows(catalog):
    scores = {"DEX": 16, "CHA": 16}
    picks_bard = {"class:bard:1:prof-choice-0": ["skill-stealth", "skill-persuasion", "skill-performance"],
                  BARD2: ["skill-persuasion", "skill-performance"], BARD9: ["skill-stealth", "skill-persuasion"]}
    picks_rogue = {"class:rogue:multiclass-prof-choice-0": ["skill-acrobatics"],
                   ROGUE1: ["skill-stealth", "skill-acrobatics"], ROGUE6: ["skill-acrobatics", "skill-persuasion"]}
    res = _res(catalog, [("bard", 9, picks_bard), ("rogue", 6, picks_rogue)], scores=scores)
    assert set(_expertise_cards(res)) == {BARD2, BARD9, ROGUE1, ROGUE6}
    rows = [f for f in res["sheet"]["features"] if f["name"] == "Expertise"]
    by = {(f["source"]["id"], f["level"]): f.get("choice") for f in rows}
    assert by == {
        ("bard", 2): ["Persuasion", "Performance"], ("bard", 9): ["Stealth", "Persuasion"],
        ("rogue", 1): ["Stealth", "Acrobatics"], ("rogue", 6): ["Acrobatics", "Persuasion"],
    }
    # no SRD fallback row is added beside the XPHB rows
    assert [f["level"] for f in rows if f["source"]["id"] == "bard"] == [2, 9]


@needs_data
def test_deft_explorer_and_scholar_choices_show_on_their_rows(catalog):
    picks = {"class:ranger:1:prof-choice-0": RANGER_SKILLS, DEFT: ["skill-stealth"]}
    res = _res(catalog, [("ranger", 2, picks)])
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Deft Explorer")
    assert row["level"] == 2 and row["choice"] == ["Stealth"]
    res = _res(catalog, [("wizard", 2, {"class:wizard:1:prof-choice-0": ["skill-arcana", "skill-history"], SCHOLAR: ["skill-arcana"]})])
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Scholar")
    assert row["choice"] == ["Arcana"]


@needs_data
def test_ranger_favored_enemy_row_has_no_leftover_srd_rows(catalog):
    res = _res(catalog, [("ranger", 9, {})])
    names = [f["name"] for f in res["sheet"]["features"] if f["source"]["kind"] == "class"]
    assert not [n for n in names if n.startswith("Natural Explorer")]
    assert names.count("Favored Enemy") == 1 and names.count("Expertise") == 1


def test_generic_attach_rule_takes_any_card_ending_in_an_xphb_feature_id(catalog):
    """C6b-1: cids of kind `languages` (C6b-2) and any `<kind>:<xphb feature id>` attach to that row."""
    assert sheet_features._CLASS_CHOICE_ID.match("class:ranger:2:languages:xphb-ranger-2-deft-explorer")
    rc = {"cls": {"name": "Ranger"}, "cls_id": "ranger", "level": 2, "subclass_id": None, "subclass": None}
    choice = {"id": "class:ranger:2:languages:xphb-ranger-2-deft-explorer",
              "source": {"kind": "class", "id": "ranger", "label": "Ranger", "level": 2},
              "options": [{"id": "elvish", "label": "Elvish"}, {"id": "dwarvish", "label": "Dwarvish"}],
              "selected": ["elvish", "dwarvish"]}
    feats = sheet_features.build_features(catalog, [rc], {}, None, None, None, None, None, [], [choice], ruleset="2024")
    deft = next(f for f in feats if f["name"] == "Deft Explorer")
    assert deft["choice"] == ["Elvish", "Dwarvish"]
    # the same card under mixed has no XPHB rows to attach to: nothing is listed (no crash)
    assert not [f for f in sheet_features.build_features(
        catalog, [rc], {}, None, None, None, None, None, [], [choice], ruleset="mixed") if f["name"] == "Deft Explorer"]


# ---- degrade, helper, ruleset isolation -----------------------------------------------------

@needs_data
def test_srd_only_catalog_keeps_the_srd_cards(catalog):
    bare = _srd_only(catalog)
    res = _res(bare, [("bard", 3, {})])
    assert _expertise_cards(res) == ["class:bard:3:expertise-choice:bard-expertise-1"]
    res = _res(bare, [("rogue", 1, {})])
    assert _expertise_cards(res) == ["class:rogue:1:expertise-choice:rogue-expertise-1"]
    res = _res(bare, [("ranger", 6, {})])
    assert [c["id"] for c in res["choices"] if ":enemy-type:" in c["id"]]
    assert _card(_res(bare, [("wizard", 2, {})]), SCHOLAR) is None
    assert _card(_res(bare, [("ranger", 2, {})]), DEFT) is None


@needs_data
def test_helper_returns_nothing_outside_2024_and_without_data(catalog):
    assert class_choices_2024.expertise_entries(catalog, "bard", "mixed") == []
    assert class_choices_2024.replaced_srd_features(catalog, "ranger", "2014") == set()
    assert class_choices_2024.replaced_srd_features(catalog, "fighter", "2024") == set()
    bare = _srd_only(catalog)
    assert class_choices_2024.expertise_entries(bare, "bard", "2024") == []
    assert class_choices_2024.replaced_srd_features(bare, "bard", "2024") == set()
    assert class_choices_2024.replaced_srd_features(bare, "ranger", "2024") == set()
    assert class_choices_2024.replaced_srd_features(catalog, "ranger", "2024") == set(SRD_CARDS_REPLACED_2024["ranger"])


@needs_data
def test_resolve_timing(catalog):
    drafts = [
        _draft([("bard", 9, {}), ("rogue", 6, {})], scores={"CHA": 16}),
        _draft([("ranger", 9, {})]), _draft([("wizard", 20, {})]), _draft([("fighter", 20, {})]),
        _draft([("wizard", 20, {})], ruleset="mixed"), _draft([("fighter", 20, {})], ruleset="mixed"),
    ]
    for d in drafts:
        resolve(d, catalog)
        start = time.perf_counter()
        for _ in range(20):
            resolve(d, catalog)
        assert (time.perf_counter() - start) / 20 < 0.05
