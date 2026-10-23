"""RPF: PHB - you can't gain the same proficiency twice; pick another. Generic skill duplicates between the ordinary
class / species / multiclass proficiency pick cards (all rulesets):

  order    (class order, class level); origin (species) first, then each class's cards, a multiclass card at
           (its class, 1). The LATER card loses the duplicate.
  effect   the option is disabled "already proficient"; a stored pick of it is dropped with a non-blocking `pruned`
           entry and the card turns pending (it has a free slot again); the earlier card keeps its pick.
  scope    skill ids only (a tool pick is not a skill), no expertise cards, no Keen Mind style cards, no feat or
           background cards, and the positioned subclass picks keep their own gate.
"""
import pytest

from catalog.loader import load
from engine.resolve import resolve

ROGUE = "class:rogue:1:prof-choice-0"
BARD_MC = "class:bard:multiclass-prof-choice-0"
HALF_ELF = "species:half-elf:trait:skill-versatility:proficiency-choice"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset, classes, species="human", sp_choices=None, bg="acolyte"):
    return {"name": "t", "ruleset": ruleset, "sources": [], "classes": classes,
            "background": {"id": bg, "choices": {}}, "species": {"id": species, "choices": sp_choices or {}},
            "abilities": {"method": "manual", "base": {k: 14 for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
            "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}}


def _rogue_bard(rogue_pick, bard_pick):
    return [{"classId": "rogue", "level": 1, "choices": {ROGUE: rogue_pick}},
            {"classId": "bard", "level": 1, "choices": {BARD_MC: bard_pick}}]


def _card(res, cid):
    return next(c for c in res["choices"] if c["id"] == cid)


def _notes(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_multiclass_card_loses_the_skill_the_first_class_took(catalog, ruleset):
    sp = "human-xphb" if ruleset == "2024" else "human"
    first = ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"]
    res = resolve(_draft(ruleset, _rogue_bard(first, ["skill-stealth"]), species=sp), catalog)
    assert _card(res, ROGUE)["selected"] == first and _card(res, ROGUE)["status"] == "resolved"
    bard = _card(res, BARD_MC)
    assert bard["selected"] == [] and bard["status"] == "pending"
    stealth = next(o for o in bard["options"] if o["id"] == "skill-stealth")
    assert stealth["disabled"] and stealth["disabledReason"] == "already proficient"
    assert len(_notes(res, BARD_MC)) == 1 and "Stealth" in _notes(res, BARD_MC)[0]["reason"]
    assert not any(BARD_MC in p["id"] for p in res["problems"])
    assert res["sheet"]["proficiencies"]["skills"].count("skill-stealth") == 1


def test_a_different_skill_is_untouched(catalog):
    first = ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"]
    res = resolve(_draft("mixed", _rogue_bard(first, ["skill-arcana"])), catalog)
    assert _card(res, BARD_MC)["selected"] == ["skill-arcana"] and _card(res, BARD_MC)["status"] == "resolved"
    assert not _notes(res, BARD_MC) and not _notes(res, ROGUE)
    assert not any(o.get("disabled") and o.get("disabledReason") == "already proficient" for o in _card(res, BARD_MC)["options"]
                   if o["id"] not in first)


def test_species_pick_comes_first_and_the_class_card_loses(catalog):
    classes = [{"classId": "rogue", "level": 1, "choices": {ROGUE: ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"]}}]
    res = resolve(_draft("mixed", classes, species="half-elf", sp_choices={HALF_ELF: ["skill-stealth", "skill-arcana"]}), catalog)
    assert _card(res, HALF_ELF)["selected"] == ["skill-stealth", "skill-arcana"]
    rogue = _card(res, ROGUE)
    assert "skill-stealth" not in rogue["selected"] and rogue["status"] == "pending"
    assert len(_notes(res, ROGUE)) == 1
    assert not _notes(res, HALF_ELF)


def test_the_first_class_never_loses_to_a_later_one(catalog):
    res = resolve(_draft("mixed", _rogue_bard(["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"],
                                              ["skill-stealth"])), catalog)
    assert _card(res, ROGUE)["selected"][0] == "skill-stealth" and not _notes(res, ROGUE)


def test_class_order_decides_who_loses(catalog):
    bard_first = [{"classId": "bard", "level": 1, "choices": {"class:bard:1:prof-choice-0": ["skill-stealth", "skill-arcana", "skill-history"]}},
                  {"classId": "rogue", "level": 1, "choices": {"class:rogue:multiclass-prof-choice-0": ["skill-stealth"]}}]
    res = resolve(_draft("mixed", bard_first), catalog)
    assert _card(res, "class:bard:1:prof-choice-0")["selected"][0] == "skill-stealth"
    mc = _card(res, "class:rogue:multiclass-prof-choice-0")
    assert mc["selected"] == [] and mc["status"] == "pending" and len(_notes(res, mc["id"])) == 1
    rogue_first = [{"classId": "rogue", "level": 1, "choices": {ROGUE: ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"]}},
                   {"classId": "bard", "level": 1, "choices": {BARD_MC: ["skill-stealth"]}}]
    assert _card(resolve(_draft("mixed", rogue_first), catalog), BARD_MC)["selected"] == []


def test_expertise_and_non_skill_picks_are_not_gated(catalog):
    # the second Bard multiclass card is a tool / instrument pick; a skill id coincidence must not matter
    res = resolve(_draft("mixed", _rogue_bard(["skill-stealth", "skill-acrobatics", "skill-perception", "skill-deception"],
                                              ["skill-arcana"])), catalog)
    assert not [p for p in res["pruned"] if "already proficient" in p["reason"]]
