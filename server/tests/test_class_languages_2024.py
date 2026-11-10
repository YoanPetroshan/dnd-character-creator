"""C6b-2: 2024 class languages (Thieves' Cant, Druidic, Deft Explorer) and Barbarian Primal Knowledge.

Rules (XPHB class features, text read from catalog.features on 2026-10-10):
  Rogue 1 Thieves' Cant   "You know Thieves' Cant and one other language of your choice, which you choose
                           from the language tables in chapter 2."
  Druid 1 Druidic         "You know Druidic, the secret language of Druids."
  Ranger 2 Deft Explorer  "Languages. You know two languages of your choice from the language tables in chapter 2."
  Barbarian 3 Primal Knowledge
                          "You gain proficiency in another skill of your choice from the skill list available
                           to Barbarians at level 1."
Decision E2: the language pool is the PHB 2024 chapter 2 Standard table (10) plus the Rare table (9), 19 ids,
including Druidic, Thieves' Cant and Common Sign Language. A language the character already knows (fixed
race / background / feat / class languages and the picks of every other language card) is disabled
"already known"; class cards yield to background / species / feat cards, and among class cards the
(class order, class level) walk decides who keeps a duplicate.

Matrix: ruleset (2024 / mixed / 2014) x class (Rogue 1, Druid 1, Ranger 1/2, Barbarian 2/3) x known source
(species fixed, background card, other class fixed, other class card) x stored duplicate (pruned) x
exports x sheet.features rows x Primal Knowledge options (6, L1 skill already proficient from the class
card / background, stored pick pruned) x catalog (real XPHB / SRD-only) x helper isolation x timing."""
from perf_helpers import assert_fast
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from catalog.reference_data import (
    CLASS_LANGUAGES_2024, LANGUAGE_NAMES, LANGUAGES, LANGUAGES_2024_RARE, LANGUAGES_2024_STANDARD,
    PRIMAL_KNOWLEDGE_2024,
)
from engine import class_choices_2024
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

THIEVES = "class:rogue:1:languages:xphb-rogue-1-thieves-cant"
DEFT_LANG = "class:ranger:2:languages:xphb-ranger-2-deft-explorer"
PRIMAL = "class:barbarian:3:feature:xphb-barbarian-3-primal-knowledge"
BARB_SKILLS = {"skill-animal-handling", "skill-athletics", "skill-intimidation", "skill-nature",
               "skill-perception", "skill-survival"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", background="acolyte", species="human"):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}},
        "species": {"id": species}, "background": {"id": background},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _lang_cards(res):
    # the 2014 SRD Ranger's Favored Enemy language cards (VF7.3, `...:languages:favored-enemy-*`) are not 2024 class languages
    return [c["id"] for c in res["choices"] if c["source"]["kind"] == "class" and ":languages:" in c["id"]
            and ":languages:favored-enemy-" not in c["id"]]


def _langs(res):
    return res["sheet"]["proficiencies"]["languages"]


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith("xphb-")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


# ---- data -----------------------------------------------------------------------------------

def test_language_tables_match_phb_2024_chapter_2():
    assert [l["index"] for l in LANGUAGES_2024_STANDARD] == [
        "common", "common-sign-language", "draconic", "dwarvish", "elvish", "giant", "gnomish", "goblin",
        "halfling", "orc"]
    assert [l["index"] for l in LANGUAGES_2024_RARE] == [
        "abyssal", "celestial", "deep-speech", "druidic", "infernal", "primordial", "sylvan", "thieves-cant",
        "undercommon"]
    assert LANGUAGE_NAMES["thieves-cant"] == "Thieves' Cant" and LANGUAGE_NAMES["druidic"] == "Druidic"
    assert LANGUAGE_NAMES["common-sign-language"] == "Common Sign Language"
    # the mixed / 2014 list is not extended (it drives every 2014 language choice)
    assert len(LANGUAGES) == 16 and not {"druidic", "thieves-cant", "common-sign-language"} & {l["index"] for l in LANGUAGES}
    assert {l["index"] for l in LANGUAGES} <= set(LANGUAGE_NAMES)


def test_class_language_table():
    assert CLASS_LANGUAGES_2024 == {
        "xphb-rogue-1-thieves-cant": {"class": "rogue", "level": 1, "fixed": ["thieves-cant"], "choose": 1},
        "xphb-druid-1-druidic": {"class": "druid", "level": 1, "fixed": ["druidic"], "choose": 0},
        "xphb-ranger-2-deft-explorer": {"class": "ranger", "level": 2, "fixed": [], "choose": 2},
    }
    assert PRIMAL_KNOWLEDGE_2024 == {"feature": "xphb-barbarian-3-primal-knowledge", "class": "barbarian", "level": 3}


@needs_data
def test_entries_match_xphb_feature_ids_and_levels(catalog):
    for fid, e in CLASS_LANGUAGES_2024.items():
        assert fid in catalog.class_2024_level_features[e["class"]][e["level"]], fid
    assert PRIMAL_KNOWLEDGE_2024["feature"] in catalog.class_2024_level_features["barbarian"][3]


# ---- Rogue / Druid / Ranger -----------------------------------------------------------------

@needs_data
def test_rogue_1_knows_thieves_cant_and_picks_one_language(catalog):
    res = _res(catalog, [("rogue", 1, {})])
    assert "thieves-cant" in _langs(res)
    card = _card(res, THIEVES)
    assert card["count"] == 1 and card["status"] == "pending" and card["label"] == "Thieves' Cant"
    assert card["source"] == {"kind": "class", "id": "rogue", "label": "Rogue", "level": 1}
    assert len(card["options"]) == 19
    assert {o["id"] for o in card["options"]} == {l["index"] for l in LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE}
    assert _opt(card, "thieves-cant")["disabledReason"] == "already known"
    assert _opt(card, "common")["disabledReason"] == "already known"  # Human fixes Common
    assert _opt(card, "draconic").get("disabled") is None
    assert "language tables in chapter 2" in card["description"]
    res = _res(catalog, [("rogue", 1, {THIEVES: ["draconic"]})])
    assert _card(res, THIEVES)["status"] == "resolved"
    assert {"thieves-cant", "draconic", "common"} <= set(_langs(res))


@needs_data
def test_druid_1_knows_druidic_without_a_card(catalog):
    res = _res(catalog, [("druid", 1, {})])
    assert "druidic" in _langs(res) and _lang_cards(res) == []


@needs_data
def test_ranger_deft_explorer_languages(catalog):
    assert _lang_cards(_res(catalog, [("ranger", 1, {})])) == []
    res = _res(catalog, [("ranger", 2, {})], species="elf")
    card = _card(res, DEFT_LANG)
    assert card["count"] == 2 and card["label"] == "Deft Explorer" and len(card["options"]) == 19
    assert _opt(card, "elvish")["disabledReason"] == "already known"  # Elf
    assert _opt(card, "giant").get("disabled") is None
    res = _res(catalog, [("ranger", 2, {DEFT_LANG: ["giant", "goblin"]})], species="elf")
    assert _card(res, DEFT_LANG)["status"] == "resolved"
    assert {"giant", "goblin", "elvish"} <= set(_langs(res))


@needs_data
def test_stored_known_language_is_pruned_and_card_goes_pending(catalog):
    res = _res(catalog, [("ranger", 2, {DEFT_LANG: ["elvish", "giant"]})], species="elf")
    card = _card(res, DEFT_LANG)
    assert card["selected"] == ["giant"] and card["status"] == "pending"
    assert [p for p in res["pruned"] if p["choiceId"] == DEFT_LANG]
    assert "Elvish" in next(p for p in res["pruned"] if p["choiceId"] == DEFT_LANG)["reason"]


@needs_data
def test_class_card_yields_to_background_species_and_feat_cards(catalog):
    bg_cid = "background:acolyte:languages"
    res = _res(catalog, [("rogue", 1, {THIEVES: ["draconic"]})])
    bg = _card(res, bg_cid)
    pick = [o["id"] for o in bg["options"] if o["id"] == "draconic"]
    assert pick  # acolyte offers any language
    d = _draft([("rogue", 1, {THIEVES: ["draconic"]})])
    d["background"] = {"id": "acolyte", "choices": {bg_cid: ["draconic", "giant"]}}
    res = resolve(d, catalog)
    card = _card(res, THIEVES)
    assert _opt(card, "draconic")["disabledReason"] == "already known"
    assert card["selected"] == [] and card["status"] == "pending"
    assert [p for p in res["pruned"] if p["choiceId"] == THIEVES]


@needs_data
def test_other_class_fixed_and_card_picks_count_as_known(catalog):
    res = _res(catalog, [("druid", 1, {}), ("rogue", 1, {})])
    assert _opt(_card(res, THIEVES), "druidic")["disabledReason"] == "already known"
    # two class cards: the earlier one in class order keeps a duplicate, the later one is pruned
    res = _res(catalog, [("rogue", 1, {THIEVES: ["giant"]}), ("ranger", 2, {DEFT_LANG: ["giant", "orc"]})])
    assert _card(res, THIEVES)["selected"] == ["giant"]
    deft = _card(res, DEFT_LANG)
    assert deft["selected"] == ["orc"] and deft["status"] == "pending"
    assert _opt(deft, "giant")["disabledReason"] == "already known"
    assert [p for p in res["pruned"] if p["choiceId"] == DEFT_LANG]


@needs_data
def test_sheet_features_rows_list_languages(catalog):
    res = _res(catalog, [("rogue", 1, {THIEVES: ["draconic"]}), ("ranger", 2, {DEFT_LANG: ["giant", "orc"]})])
    rows = {f["name"]: f for f in res["sheet"]["features"]}
    assert rows["Thieves' Cant"]["choice"] == ["Draconic"]
    assert rows["Deft Explorer"]["choice"] == ["Giant", "Orc"]


@needs_data
def test_deft_explorer_row_lists_expertise_and_languages(catalog):
    exp = "class:ranger:2:expertise-choice:xphb-ranger-2-deft-explorer"
    res = _res(catalog, [("ranger", 2, {"class:ranger:1:prof-choice-0": ["skill-stealth", "skill-nature", "skill-survival"],
                                        exp: ["skill-stealth"], DEFT_LANG: ["giant", "orc"]})])
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Deft Explorer")
    assert set(row["choice"]) == {"Stealth", "Giant", "Orc"}


@needs_data
def test_exports_print_the_new_language_names(catalog):
    from markdown_export import to_markdown
    from pdf_export import to_pdf
    res = _res(catalog, [("druid", 1, {}), ("rogue", 1, {THIEVES: ["common-sign-language"]})])
    md = to_markdown(res)
    assert "Thieves' Cant" in md and "Druidic" in md and "Common Sign Language" in md
    assert to_pdf(res)[:4] == b"%PDF"


# ---- ruleset isolation, degrade, helper -----------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_class_languages_outside_2024(catalog, ruleset):
    for classes in ([("rogue", 1, {})], [("druid", 1, {})], [("ranger", 2, {})]):
        res = _res(catalog, classes, ruleset=ruleset)
        assert _lang_cards(res) == []
        assert not {"thieves-cant", "druidic"} & set(_langs(res))
    assert _card(_res(catalog, [("barbarian", 3, {})], ruleset=ruleset), PRIMAL) is None


@needs_data
def test_stored_2024_picks_fall_into_pruned_under_mixed(catalog):
    res = _res(catalog, [("rogue", 1, {THIEVES: ["draconic"]})], ruleset="mixed")
    assert THIEVES in {p["choiceId"] for p in res["pruned"]}


@needs_data
def test_srd_only_catalog_degrades(catalog):
    bare = _srd_only(catalog)
    for classes in ([("rogue", 1, {})], [("druid", 1, {})], [("ranger", 2, {})], [("barbarian", 3, {})]):
        res = _res(bare, classes)
        assert _lang_cards(res) == [] and _card(res, PRIMAL) is None
        assert not {"thieves-cant", "druidic"} & set(_langs(res))


@needs_data
def test_helpers_return_nothing_outside_2024_and_without_data(catalog):
    rcs = [{"cls": {"name": "Rogue"}, "cls_id": "rogue", "level": 5}]
    assert class_choices_2024.fixed_class_languages(catalog, rcs, "2024") == ["thieves-cant"]
    assert class_choices_2024.fixed_class_languages(catalog, rcs, "mixed") == []
    assert class_choices_2024.fixed_class_languages(_srd_only(catalog), rcs, "2024") == []
    rc = {"cls": {"name": "Rogue"}, "cls_id": "rogue", "level": 5}
    assert class_choices_2024.language_templates(catalog, rc, "2014") == []
    assert class_choices_2024.primal_knowledge_templates(catalog, {"cls": {"name": "Barbarian"}, "cls_id": "barbarian", "level": 3}, "mixed") == []


# ---- Primal Knowledge -----------------------------------------------------------------------

BARB1 = "class:barbarian:1:prof-choice-0"


@needs_data
def test_primal_knowledge_card_by_level(catalog):
    assert _card(_res(catalog, [("barbarian", 2, {})]), PRIMAL) is None
    res = _res(catalog, [("barbarian", 3, {})])
    card = _card(res, PRIMAL)
    assert card["count"] == 1 and card["status"] == "pending" and card["label"] == "Primal Knowledge"
    assert card["source"] == {"kind": "class", "id": "barbarian", "label": "Barbarian", "level": 3}
    assert {o["id"] for o in card["options"]} == BARB_SKILLS and len(card["options"]) == 6
    assert all(o.get("disabled") is None for o in card["options"])
    assert "skill list available to Barbarians at level 1" in card["description"]


@needs_data
def test_primal_knowledge_disables_skills_already_proficient(catalog):
    res = _res(catalog, [("barbarian", 3, {BARB1: ["skill-athletics", "skill-perception"]})])
    card = _card(res, PRIMAL)
    assert _opt(card, "skill-athletics")["disabledReason"] == "already proficient"
    assert _opt(card, "skill-perception")["disabledReason"] == "already proficient"
    assert _opt(card, "skill-survival").get("disabled") is None
    # a background grant counts too (Soldier: Athletics, Intimidation)
    res = _res(catalog, [("barbarian", 3, {})], background="soldier-xphb")
    card = _card(res, PRIMAL)
    assert _opt(card, "skill-intimidation")["disabled"] is True  # generic "already granted by <background>" reason


@needs_data
def test_primal_knowledge_pick_is_a_proficiency_and_row_choice(catalog):
    res = _res(catalog, [("barbarian", 3, {BARB1: ["skill-athletics", "skill-perception"], PRIMAL: ["skill-survival"]})])
    assert _card(res, PRIMAL)["status"] == "resolved"
    assert "skill-survival" in res["sheet"]["proficiencies"]["skills"]
    base = _res(catalog, [("barbarian", 3, {BARB1: ["skill-athletics", "skill-perception"]})])
    assert res["derived"]["skills"]["skill-survival"] - base["derived"]["skills"]["skill-survival"] == 2
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Primal Knowledge")
    assert row["choice"] == ["Survival"]


@needs_data
def test_primal_knowledge_stored_duplicate_is_pruned(catalog):
    res = _res(catalog, [("barbarian", 3, {BARB1: ["skill-athletics", "skill-perception"], PRIMAL: ["skill-athletics"]})])
    card = _card(res, PRIMAL)
    assert card["selected"] == [] and card["status"] == "pending"
    assert [p for p in res["pruned"] if p["choiceId"] == PRIMAL]
    # the L1 pick is not double counted: Athletics is still proficient exactly once
    assert res["sheet"]["proficiencies"]["skills"].count("skill-athletics") == 1


@needs_data
def test_primal_knowledge_multiclass_barbarian_uses_the_level_1_list(catalog):
    res = _res(catalog, [("fighter", 1, {}), ("barbarian", 3, {})])
    assert {o["id"] for o in _card(res, PRIMAL)["options"]} == BARB_SKILLS


# ---- timing ---------------------------------------------------------------------------------

@needs_data
def test_resolve_timing(catalog):
    drafts = [
        _draft([("rogue", 1, {})]), _draft([("druid", 1, {})]), _draft([("ranger", 2, {})], species="elf"),
        _draft([("barbarian", 3, {})]), _draft([("rogue", 6, {}), ("ranger", 2, {})]),
        _draft([("fighter", 20, {})]), _draft([("wizard", 20, {})]),
        _draft([("fighter", 20, {})], ruleset="mixed"), _draft([("wizard", 20, {})], ruleset="mixed"),
    ]
    for d in drafts:
        resolve(d, catalog)
        laps = []
        for _ in range(20):
            t_run = time.perf_counter()
            resolve(d, catalog)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps)
