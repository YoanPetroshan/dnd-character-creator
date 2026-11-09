"""F1 finding 4: Magic Connoisseur ("Choose a level 1 and a level 2 spell from the same list you selected for the Magic
Initiate feat's cantrips") and the Magic Initiate holders.

G5 took the list of the FIRST Magic Initiate holder. Now:
  * one holder           unchanged: the Connoisseur follows it, no list card of its own, no spell cards until the list is
                         picked; a holder whose list is FIXED by its background (Sage: Wizard, the single-option card) counts
                         as picked though it was never clicked
  * two or more holders  (XPHB Magic Initiate is repeatable, a different list each time) the Connoisseur gets its own
                         `:spell-variant` card limited to the lists the holders picked; the spell cards and the ability follow
                         that pick (the ability of the holder whose list it is)"""
import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools official data not available")

MI = "feat:magic-initiate-xphb"
ASI_MI = {"class:wizard:4:asi": [MI]}
ASI_MC = {"class:wizard:8:asi": ["feat:magic-connoisseur-au"], "class:wizard:8:asi:feat:magic-connoisseur-au:ability-bonus": ["int"]}
MC_VARIANT = "class:wizard:8:asi:feat:magic-connoisseur-au:spell-variant"
ASI_MI_CLERIC = {**ASI_MI, f"class:wizard:4:asi:{MI}:spell-variant": ["cleric-spells"]}
ASI_MI_ABILITY = f"class:wizard:4:asi:{MI}:spell-ability"
SAGE_ABILITY = f"{MI}:spell-ability"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(bg, class_choices, bg_choices=None):
    return {"ruleset": "2024", "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}},
            "species": {"id": "human-xphb"}, "background": {"id": bg, "choices": dict(bg_choices or {})},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": "wizard", "level": 8, "choices": dict(class_choices)}]}


def _cards(res, marker):
    return {c["id"]: c for c in res["choices"] if marker in c["id"]}


def _mc_spell_cards(res):
    return _cards(res, "magic-connoisseur-au:spell-choice-")


@needs_data
def test_a_fixed_single_option_list_counts_as_picked_without_a_click(catalog):
    res = resolve(_draft("sage-xphb", ASI_MC), catalog)  # Sage: Magic Initiate (Wizard), card has one option, never clicked
    assert _cards(res, "feat:magic-initiate-xphb:spell-variant")[f"{MI}:spell-variant"]["status"] == "pending"
    assert not [i for i in _cards(res, "magic-connoisseur-au") if i.endswith(":spell-variant")]
    cards = _mc_spell_cards(res)
    assert len(cards) == 2
    for card in cards.values():
        for o in card["options"]:
            assert "wizard" in {c["index"] for c in catalog.spells[o["id"]].get("classes", [])}


@needs_data
def test_one_free_holder_that_has_not_picked_leaves_the_connoisseur_waiting(catalog):
    res = resolve(_draft("soldier-xphb", {**ASI_MI, **ASI_MC}), catalog)
    mc = _cards(res, "magic-connoisseur-au")
    assert not [i for i in mc if i.endswith(":spell-variant") or ":spell-choice-" in i]


@needs_data
def test_two_holders_give_the_connoisseur_its_own_list_card_limited_to_the_held_lists(catalog):
    res = resolve(_draft("sage-xphb", {**ASI_MI_CLERIC, **ASI_MC}), catalog)
    card = _cards(res, "magic-connoisseur-au")[MC_VARIANT]
    assert [o["id"] for o in card["options"]] == ["cleric-spells", "wizard-spells"] and card["status"] == "pending" and card["count"] == 1
    assert not _mc_spell_cards(res)  # no spell cards until the player chooses among the held lists


@needs_data
@pytest.mark.parametrize("pick, klass", [("cleric-spells", "cleric"), ("wizard-spells", "wizard")])
def test_the_pick_decides_the_spell_cards(catalog, pick, klass):
    res = resolve(_draft("sage-xphb", {**ASI_MI_CLERIC, **ASI_MC, MC_VARIANT: [pick]}), catalog)
    assert _cards(res, "magic-connoisseur-au")[MC_VARIANT]["status"] == "resolved"
    cards = _mc_spell_cards(res)
    assert len(cards) == 2
    for card in cards.values():
        for o in card["options"]:
            assert klass in {c["index"] for c in catalog.spells[o["id"]].get("classes", [])}, (pick, o["id"])


@needs_data
def test_a_list_nobody_holds_is_not_accepted(catalog):
    res = resolve(_draft("sage-xphb", {**ASI_MI_CLERIC, **ASI_MC, MC_VARIANT: ["druid-spells"]}), catalog)
    assert not _mc_spell_cards(res)
    assert any(p["choiceId"] == MC_VARIANT for p in res["pruned"])
    assert _cards(res, "magic-connoisseur-au")[MC_VARIANT]["status"] == "pending"


@needs_data
@pytest.mark.parametrize("pick, expected", [("cleric-spells", "INT"), ("wizard-spells", "WIS")])
def test_the_ability_is_that_of_the_holder_whose_list_it_is(catalog, pick, expected):
    """Sage's Magic Initiate (Wizard list) casts with WIS here, the free copy taken at level 4 (Cleric list) with INT."""
    choices = {**ASI_MI_CLERIC, **ASI_MC, MC_VARIANT: [pick], ASI_MI_ABILITY: ["int"]}
    first = resolve(_draft("sage-xphb", choices, {SAGE_ABILITY: ["wis"]}), catalog)
    picks = {cid: [card["options"][0]["id"]] for cid, card in _mc_spell_cards(first).items()}
    res = resolve(_draft("sage-xphb", {**choices, **picks}, {SAGE_ABILITY: ["wis"]}), catalog)
    rows = [r for r in res["sheet"]["innateSpells"] if r.get("featId") == "magic-connoisseur-au"]
    assert len(rows) == 2 and all(r["ability"] == expected for r in rows), (pick, rows)


@needs_data
def test_the_connoisseur_alone_keeps_its_own_card(catalog):
    """No Magic Initiate held: the Connoisseur is not a follower and keeps its own list card (G5)."""
    res = resolve(_draft("soldier-xphb", ASI_MC), catalog)
    assert MC_VARIANT in _cards(res, "magic-connoisseur-au")
