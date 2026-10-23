"""F3a: fixes from the whole-branch review of the 2024 work (C9a..R9). One section per finding.

Every test uses the real catalog; the 2024 ones skip without the 5etools data. mixed/2014 output is guarded by
test_c_series_golden.py (never regenerated for F3a)."""
import copy

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

_BASE = {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", species="human-xphb", background="soldier-xphb", equip=None, bg_choices=None,
           species_choices=None, base=None):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": dict(base or _BASE)},
        "species": {"id": species, "choices": species_choices or {}},
        "background": {"id": background, "choices": bg_choices or {}},
        "equipment": {"choices": equip or {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, **({"subclassId": s} if s else {}), "choices": dict(ch or {})}
                    for c, lv, s, ch in classes],
    }


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


# --- Finding 1: ruleset switch must report picks that are no longer offered ------------------------------------

@needs_data
def test_f1_equipment_pick_not_offered_after_ruleset_switch_is_pruned(catalog):
    cid = "class:barbarian:1:equipment-choice-0"
    d = _draft([("barbarian", 1, None, {cid: ["greataxe"]})], ruleset="2024")
    res = resolve(d, catalog)
    card = _card(res, cid)
    assert "greataxe" not in {o["id"] for o in card["options"]}
    entry = [p for p in res["pruned"] if p["choiceId"] == cid]
    assert len(entry) == 1 and "greataxe" in entry[0]["reason"].lower()
    # a valid pick produces no entry
    ok = card["options"][0]["id"]
    d["classes"][0]["choices"][cid] = [ok]
    assert not [p for p in resolve(d, catalog)["pruned"] if p["choiceId"] == cid]


@needs_data
def test_f1_2024_pick_pruned_when_switching_to_mixed(catalog):
    cid = "class:barbarian:1:equipment-choice-0"
    d = _draft([("barbarian", 1, None, {cid: ["greataxe+handaxe+explorers-pack+gp-15"]})], ruleset="mixed",
               species="human", background="acolyte")
    res = resolve(d, catalog)
    assert [p for p in res["pruned"] if p["choiceId"] == cid]
    assert _card(res, cid)["selected"] == []


# --- Finding 2a: repeat instances of the target invocations need as many eligible cantrips as instances ------------

from c7c_helpers import (AGON, BLADE_W, CANT, EB, INV, MI, REPEL, SPEAR, TOME, TOME_C, TTD, _card, _opt,  # noqa: E402
                         _pruned, _res, tcid)

SG = "shocking-grasp-xphb"


@needs_data
@pytest.mark.parametrize("base", [AGON, SPEAR, REPEL])
def test_f2a_second_instance_needs_a_second_eligible_cantrip(catalog, base):
    # Eldritch Blast is the only eligible cantrip (attack roll, damage, range 120) next to Minor Illusion
    r = _res(catalog, 5, [base, f"{base}~2"], [EB, MI])
    card = _card(r, INV)
    o2 = _opt(card, f"{base}~2")
    assert o2["disabled"] and o2["disabledReason"] == "needs another eligible cantrip"
    assert f"{base}~2" not in card["selected"] and base in card["selected"]
    assert "needs another eligible cantrip" in _pruned(r, INV) or "prerequisites" in _pruned(r, INV)
    assert _card(r, tcid(f"{base}~2", "cantrip")) is None  # no card that can never be completed
    # with a second qualifying cantrip the instance is open
    r2 = _res(catalog, 5, [base, f"{base}~2"], [EB, "poison-spray-xphb", MI])  # attack roll, damage, range 30
    assert not _opt(_card(r2, INV), f"{base}~2").get("disabled")


@needs_data
def test_f2a_eldritch_spear_counts_only_cantrips_with_range_ten_or_more(catalog):
    # Shocking Grasp (Touch) comes from Pact of the Tome: it deals damage but cannot be the Spear's target
    extra = {TOME_C: [SG, "guidance-xphb", "light-xphb"]}
    r = _res(catalog, 5, [TOME, SPEAR, f"{SPEAR}~2"], [EB, MI], extra=extra)
    assert _opt(_card(r, INV), f"{SPEAR}~2")["disabledReason"] == "needs another eligible cantrip"
    # Agonizing Blast accepts it (damage only)
    r2 = _res(catalog, 5, [TOME, AGON, f"{AGON}~2"], [EB, MI], extra=extra)
    assert not _opt(_card(r2, INV), f"{AGON}~2").get("disabled")


@needs_data
def test_f2a_first_instance_without_any_eligible_target_is_disabled(catalog):
    # a damaging cantrip exists (Shocking Grasp via the Tome) but none with range 10+: Spear can never get a target
    extra = {TOME_C: [SG, "guidance-xphb", "light-xphb"]}
    r = _res(catalog, 5, [TOME, SPEAR], [MI, "mage-hand-xphb"], extra=extra)
    assert _opt(_card(r, INV), SPEAR).get("disabled")
    assert SPEAR not in _card(r, INV)["selected"]


# --- Finding 2b: a new 2024 class card with no enabled option is unavailable, not blocking -------------------------

from engine import class_choices_2024  # noqa: E402

BOOK, MASTERY1, MASTERY2 = "class:wizard:spellbook", "class:wizard:18:spell-mastery-1", "class:wizard:18:spell-mastery-2"
SIGNATURE = "class:wizard:20:signature-spells"


def _wizard(level, book):
    return _draft([("wizard", level, None, {BOOK: book})], species="human-xphb", background="sage-xphb")


def _card_dict(cid, options, status="pending", count=1, kind="class"):
    return {"id": cid, "source": {"kind": kind, "id": "wizard", "level": 18}, "label": "L", "description": "d",
            "count": count, "options": options, "selected": [], "status": status}


@needs_data
def test_f2b_card_without_enabled_options_is_unavailable_and_does_not_block_export(catalog):
    from app import _pending_export_problems
    res = resolve(_wizard(18, ["alarm-xphb"]), catalog)  # Alarm: 1 minute, so no Spell Mastery candidate
    card = _card(res, MASTERY1)
    assert card["status"] == "unavailable" and card["unavailableReason"]
    ids = [p["id"] for p in _pending_export_problems(res)]
    assert f"unresolved-choice-{MASTERY1}" not in ids and f"unresolved-choice-{SIGNATURE}" not in ids
    # the spellbook itself is still pending and still blocks
    assert f"unresolved-choice-{BOOK}" in ids


def test_f2b_helper_marks_only_new_2024_cards_with_zero_enabled_options():
    off = [{"id": "a", "label": "A", "disabled": True, "disabledReason": "x"}]
    mastery = _card_dict(MASTERY1, [])
    expert = _card_dict("class:rogue:1:expertise-choice:xphb-rogue-1-expertise", off)
    languages = _card_dict("class:rogue:1:languages:xphb-rogue-1-thieves-cant", off)
    target = _card_dict("class:warlock:invocation:opt-agonizing-blast-xphb:cantrip", [])
    srd = _card_dict("class:ranger:1:feature:favored-enemy", [])  # SRD id: untouched
    has_enabled = _card_dict(MASTERY2, [{"id": "a", "label": "A"}])
    done = _card_dict(SIGNATURE, [], status="resolved")
    cards = [mastery, expert, languages, target, srd, has_enabled, done]
    out = class_choices_2024.mark_unavailable(copy.deepcopy(cards), "2024")
    assert [c["status"] for c in out] == ["unavailable"] * 4 + ["pending", "pending", "resolved"]
    assert all(c.get("unavailableReason") for c in out[:4])
    # other rulesets: untouched
    assert class_choices_2024.mark_unavailable(copy.deepcopy(cards), "mixed") == cards


# --- Finding 3: Expertise walk order and Skill Expert "lack Expertise" --------------------------------------------

DEFT = "class:ranger:2:expertise-choice:xphb-ranger-2-deft-explorer"
SE = "class:ranger:4:asi:feat:skill-expert-xphb"


def _ranger4(deft, feat_exp, ruleset="2024"):
    ch = {"class:ranger:1:prof-choice-0": ["skill-athletics", "skill-insight", "skill-nature"],
          "class:ranger:4:asi": ["feat:skill-expert-xphb"], f"{SE}:proficiency-choice-0": ["skill-acrobatics"],
          f"{SE}:expertise-choice-0": feat_exp}
    if deft is not None:
        ch[DEFT] = deft
    d = _draft([("ranger", 4, None, ch)], background="sage-xphb")
    d["ruleset"] = ruleset
    return d


@needs_data
def test_f3_earlier_deft_explorer_wins_the_duplicate_and_the_later_feat_pick_is_blamed(catalog):
    res = resolve(_ranger4(["skill-athletics"], ["skill-athletics"]), catalog)
    deft, feat = _card(res, DEFT), _card(res, f"{SE}:expertise-choice-0")
    assert deft["selected"] == ["skill-athletics"] and deft["status"] == "resolved"
    assert feat["selected"] == [] and feat["status"] == "pending"
    athletics = next(o for o in feat["options"] if o["id"] == "skill-athletics")
    assert athletics["disabled"] and "already has Expertise" in athletics["disabledReason"]
    pruned = [p for p in res["pruned"] if "Expertise" in p["reason"]]
    assert [p["choiceId"] for p in pruned] == [f"{SE}:expertise-choice-0"]
    assert res["sheet"]["expertiseSkills"] == ["skill-athletics"]


@needs_data
@pytest.mark.parametrize("ruleset,species,bg,exp_cid,blocked", [
    ("2024", "human-xphb", "sage-xphb", "class:rogue:1:expertise-choice:xphb-rogue-1-expertise", True),
    ("mixed", "human", "acolyte", "class:rogue:1:expertise-choice:rogue-expertise-1", True)])
def test_f3_skill_expert_lacks_expertise_under_every_ruleset(catalog, ruleset, species, bg, exp_cid, blocked):
    # Skill Expert (XPHB): "Choose one skill in which you have proficiency but lack Expertise." Rogue Expertise comes
    # first (level 1), the feat second (ASI 4). FE6 (B7): the feat's own rule applies under every ruleset (it used to be
    # 2024 only; the SRD Rogue card itself still allows a duplicate outside 2024).
    feat_exp = "class:rogue:4:asi:feat:skill-expert-xphb:expertise-choice-0"
    ch = {"class:rogue:1:prof-choice-0": ["skill-athletics", "skill-stealth", "skill-insight", "skill-perception"],
          exp_cid: ["skill-athletics", "skill-stealth"], "class:rogue:4:asi": ["feat:skill-expert-xphb"],
          "class:rogue:4:asi:feat:skill-expert-xphb:proficiency-choice-0": ["skill-acrobatics"], feat_exp: ["skill-athletics"]}
    res = resolve(_draft([("rogue", 4, None, ch)], ruleset=ruleset, species=species, background=bg), catalog)
    feat = _card(res, feat_exp)
    if blocked:
        assert feat["selected"] == [] and feat["status"] == "pending"
        assert next(o for o in feat["options"] if o["id"] == "skill-athletics")["disabledReason"] == "already has Expertise"
    else:
        assert feat["selected"] == ["skill-athletics"] and feat["status"] == "resolved"


@needs_data
def test_f3_feat_expertise_is_checked_at_its_real_position_not_first(catalog):
    # Skill Expert at ASI 4 is walked AFTER Ranger 2 (before: every feat card came first, so the feat won)
    res = resolve(_ranger4(["skill-athletics"], ["skill-insight"]), catalog)
    assert _card(res, DEFT)["selected"] == ["skill-athletics"]
    assert _card(res, f"{SE}:expertise-choice-0")["selected"] == ["skill-insight"]
    assert not [p for p in res["pruned"] if "Expertise" in p["reason"]]


# --- Finding 4: Primal Knowledge only yields to proficiencies gained at or before Barbarian 3 ---------------------

PK = "class:barbarian:3:feature:xphb-barbarian-3-primal-knowledge"
BSE = "class:barbarian:4:asi:feat:skill-expert-xphb"


def _barb4(pk, feat_prof):
    ch = {"class:barbarian:1:prof-choice-0": ["skill-athletics", "skill-intimidation"], PK: pk,
          "class:barbarian:4:asi": ["feat:skill-expert-xphb"], f"{BSE}:proficiency-choice-0": feat_prof}
    return _draft([("barbarian", 4, "berserker-xphb", ch)], background="sage-xphb")


@needs_data
def test_f4_primal_knowledge_keeps_its_skill_and_the_later_feat_card_shows_it_as_proficient(catalog):
    res = resolve(_barb4(["skill-perception"], ["skill-perception"]), catalog)
    pk = _card(res, PK)
    assert pk["selected"] == ["skill-perception"] and pk["status"] == "resolved"
    feat = _card(res, f"{BSE}:proficiency-choice-0")
    opt = next(o for o in feat["options"] if o["id"] == "skill-perception")
    assert opt["disabled"] and opt["disabledReason"] == "already proficient"
    assert feat["selected"] == [] and feat["status"] == "pending"
    assert [p["choiceId"] for p in res["pruned"] if "proficient" in p["reason"]] == [f"{BSE}:proficiency-choice-0"]
    assert "skill-perception" in res["sheet"]["proficiencies"]["skills"]


@needs_data
def test_f4_primal_knowledge_still_yields_to_earlier_sources(catalog):
    res = resolve(_barb4(["skill-athletics"], ["skill-acrobatics"]), catalog)  # Athletics: the level 1 skill pick
    pk = _card(res, PK)
    assert pk["selected"] == [] and pk["status"] == "pending"
    assert next(o for o in pk["options"] if o["id"] == "skill-athletics")["disabledReason"] == "already proficient"
    assert any(p["choiceId"] == PK for p in res["pruned"])


# --- Finding 5: language duplicates are blamed on the later source -------------------------------------------------

THIEVES = "class:rogue:1:languages:xphb-rogue-1-thieves-cant"


@needs_data
def test_f5_rogue_pick_before_multiclass_druid_keeps_druidic(catalog):
    d = _draft([("rogue", 1, None, {THIEVES: ["druidic"]}), ("druid", 1, None, {})])
    res = resolve(d, catalog)
    card = _card(res, THIEVES)
    assert card["selected"] == ["druidic"] and card["status"] == "resolved"  # Druid comes LATER in the build
    assert not [p for p in res["pruned"] if p["choiceId"] == THIEVES]
    assert "druidic" in res["sheet"]["proficiencies"]["languages"]


@needs_data
def test_f5_rogue_pick_after_the_druid_is_the_duplicate(catalog):
    d = _draft([("druid", 1, None, {}), ("rogue", 1, None, {THIEVES: ["druidic"]})])
    res = resolve(d, catalog)
    card = _card(res, THIEVES)
    assert card["selected"] == [] and card["status"] == "pending"
    assert next(o for o in card["options"] if o["id"] == "druidic")["disabledReason"] == "already known"
    assert [p["choiceId"] for p in res["pruned"] if "already known" in p["reason"]] == [THIEVES]


LESSONS_CID = "class:warlock:invocation:opt-lessons-of-the-first-ones-xphb:feat"


@needs_data
def test_f5_origin_pick_before_a_later_lessons_feat_keeps_its_language(catalog):
    inv = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
    ch = {inv: ["opt-lessons-of-the-first-ones-xphb", "opt-devils-sight-xphb", "opt-armor-of-shadows-xphb"],
          LESSONS_CID: ["feat:cult-of-the-dragon-initiate-frhof"]}
    d = _draft([("warlock", 2, None, ch)], bg_choices={"origin:languages": ["draconic", "elvish"]})
    res = resolve(d, catalog)
    origin = _card(res, "origin:languages")
    assert origin["selected"] == ["draconic", "elvish"] and origin["status"] == "resolved"
    assert "draconic" in res["sheet"]["proficiencies"]["languages"]
    assert not [p for p in res["pruned"] if p["choiceId"] == "origin:languages"]


# --- Finding 6: "Arrows (20)" is ONE catalog `arrow` item (already a 20-pack) ----------------------------------------

@needs_data
def test_f6_ranger_package_a_arrows_are_one_pack_and_the_carried_weight_is_91(catalog):
    cid = "class:ranger:1:equipment-choice-0"
    d = _draft([("ranger", 1, None, {})])
    base = resolve(d, catalog)
    option = next(o for o in _card(base, cid)["options"] if "arrow" in o["id"])
    assert "Arrows (20)" in option["label"] and "arrow" not in option.get("quantities", {})
    d["classes"][0]["choices"][cid] = [option["id"]]
    bg_cid = "background:soldier-xphb:equipment-choice-0"
    d["background"]["choices"][bg_cid] = [_card(base, bg_cid)["options"][0]["id"]]
    res = resolve(d, catalog)
    assert next(e for e in res["sheet"]["equipment"]["chosen"] if e["itemId"] == "arrow")["qty"] == 1
    # RP8 (deliberate): 35 lb of gear plus the 2024 Explorer's Pack table weight (55 lb); it was 35 when packs counted 0
    # RP9 (deliberate): Soldier A's "20 Arrows" is now the real catalog `arrow` pack (+1 lb; it was a narrative placeholder)
    assert res["derived"]["carryingCapacity"]["carried"] == 35 + 55 + 1


def test_f6_arrow_and_bolt_catalog_items_are_packs_of_twenty(catalog):
    assert catalog.items["arrow"]["quantity"] == 20 and catalog.items["crossbow-bolt"]["quantity"] == 20


# --- Finding 9: level-down cuts the 2024 invocation list AFTER the prerequisite check ------------------------------

from c7c_helpers import BLADE, THIRST  # noqa: E402


@needs_data
def test_f9_level_down_keeps_the_valid_pick_that_sat_behind_invalid_ones(catalog):
    # Warlock 2 knows 3 invocations. Thirsting Blade (Warlock 5 + Blade), Ascendant Step (5) and Whispers of the Grave
    # (7) are stored before Pact of the Tome: all invalid at level 2, so the Tome must survive (it used to be cut).
    stored = [THIRST, "opt-ascendant-step-xphb", "opt-whispers-of-the-grave-xphb", TOME, "opt-devils-sight-xphb"]
    res = _res(catalog, 2, stored, [EB, MI])
    card = _card(res, INV)
    assert card["selected"] == [TOME, "opt-devils-sight-xphb"] and card["count"] == 3 and card["status"] == "pending"
    assert _card(res, tcid(TOME, "cantrips")) is not None  # the Tome's own cards exist
    assert "prerequisites" in _pruned(res, INV)


@needs_data
def test_f9_overflow_after_the_gate_is_still_cut_and_reported(catalog):
    stored = [TOME, BLADE, "opt-devils-sight-xphb", "opt-armor-of-shadows-xphb", "opt-eldritch-mind-xphb"]
    res = _res(catalog, 2, stored, [EB, MI])
    card = _card(res, INV)
    assert card["selected"] == stored[:3] and card["status"] == "resolved"
    assert "now allows 3 selection(s)" in _pruned(res, INV)
    assert not [p for p in res["problems"] if "over-selected" in p["id"]]


@needs_data
def test_f9_cutting_a_pact_drops_the_invocation_that_needs_it(catalog):
    # Level 5 knows 5; Thirsting Blade needs the Blade. [A, B, C, D, BLADE-after-the-cut ...] must not keep Thirsting.
    stored = [TOME, "opt-devils-sight-xphb", "opt-armor-of-shadows-xphb", "opt-eldritch-mind-xphb", "opt-fiendish-vigor-xphb", BLADE, THIRST]
    res = _res(catalog, 5, stored, [EB, MI])
    card = _card(res, INV)
    assert BLADE not in card["selected"] and THIRST not in card["selected"] and len(card["selected"]) == 5
