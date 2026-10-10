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
    ("mixed", "human", "acolyte", "class:rogue:1:expertise-choice:rogue-expertise-1", False)])
def test_f3_skill_expert_lacks_expertise_only_under_2024(catalog, ruleset, species, bg, exp_cid, blocked):
    # Skill Expert (XPHB): "Choose one skill in which you have proficiency but lack Expertise." Rogue Expertise comes
    # first (level 1), the feat second (ASI 4). mixed/2014 keep allowing the (wasted) duplicate.
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
