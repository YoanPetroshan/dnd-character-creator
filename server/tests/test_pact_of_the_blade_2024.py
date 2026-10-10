"""C7c-2: Pact of the Blade pact weapon pick (decision E5) under ruleset 2024 (XPHB).

XPHB text: "As a Bonus Action, you can conjure a pact weapon in your hand - a Simple or Martial Melee weapon of your
choice with which you bond ... Until the bond ends, you have proficiency with the weapon ... Whenever you attack with
the bonded weapon, you can use your Charisma modifier for the attack and damage rolls instead of using Strength or
Dexterity". Thirsting Blade: Extra Attack with the pact weapon only.

Rule matrix (text -> engine):
  card      class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon, count 1, options = the Simple / Martial Melee
            weapons of the inventory (granted + chosen + added), built early and narrowed late (the inventory is only
            known after the choice pass); a pick no longer in the inventory is pruned.
  row       the picked weapon's attack row: proficient, ability CHA when the CHA modifier beats its normal ability
            (a tie keeps the normal one), note "Pact weapon"; Thirsting Blade adds a note to that row; the row exists
            even when the item is not marked equipped; with equipment.wielded the row carries wielded / CHA as usual.
Matrix: ability (CHA better / worse / tie) x finesse x equipped x wielded x inventory change x ruleset x SRD-only."""
import io

import pytest

from catalog.loader import load
from c7c_helpers import (  # noqa: F401
    AGON, BLADE, BLADE_W, CANT, CHAIN, EB, FB, INV, KNOWN, LESSONS, LONGSWORD, MI, REPEL, SPEAR, THIRST, TOME, TOME_C, TOME_R,
    TTD, X, _card, _dependent_ids, _draft, _l, _opt, _problem_ids, _pruned, _res, _resource, _srd_only, needs_data, tcid,
    time_resolve,
)
from engine import class_choices_2024
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


# ---- Pact of the Blade -----------------------------------------------------------------------------------------------


@needs_data
def test_blade_card_offers_the_melee_weapons_of_the_inventory(catalog):
    r = _res(catalog, 5, [BLADE], [EB, MI], added=LONGSWORD + [{"itemId": "shortbow", "qty": 1, "equipped": False}])
    card = _card(r, BLADE_W)
    ids = {o["id"] for o in card["options"]}
    assert "longsword" in ids and "dagger" in ids  # the Warlock kit has a dagger
    assert "shortbow" not in ids and "greatsword" not in ids  # not melee / not in the inventory
    assert card["count"] == 1
    assert _card(_res(catalog, 5, [CHAIN], [EB, MI]), BLADE_W) is None


@needs_data
def test_pact_weapon_is_proficient_and_uses_charisma(catalog):
    plain = next(a for a in _res(catalog, 5, [CHAIN], [EB, MI], added=LONGSWORD)["derived"]["attacks"] if a["itemId"] == "longsword")
    assert plain["proficient"] is False and plain["ability"] == "STR"  # Warlock: simple weapons only
    r = _res(catalog, 5, [BLADE], [EB, MI], added=LONGSWORD, extra={BLADE_W: ["longsword"]})
    row = next(a for a in r["derived"]["attacks"] if a["itemId"] == "longsword")
    assert row["proficient"] is True and row["ability"] == "CHA"
    assert row["attackBonus"] == 3 + 3 and row["damage"] == "1d8+3"  # CHA 16, proficiency bonus 3 at level 5
    assert any("Pact weapon" in n for n in row["notes"])
    other = next(a for a in r["derived"]["attacks"] if a["itemId"] == "dagger")
    assert other["ability"] == "DEX"  # other weapons are unchanged


@needs_data
def test_pact_weapon_keeps_the_better_ability(catalog):
    r = _res(catalog, 5, [BLADE], [EB, MI], added=LONGSWORD, cha=8, strength=16, extra={BLADE_W: ["longsword"]})
    row = next(a for a in r["derived"]["attacks"] if a["itemId"] == "longsword")
    assert row["ability"] == "STR" and row["proficient"] is True
    rapier = [{"itemId": "rapier", "qty": 1, "equipped": True}]
    r2 = _res(catalog, 5, [BLADE], [EB, MI], added=rapier, cha=16, dex=14, extra={BLADE_W: ["rapier"]})
    assert next(a for a in r2["derived"]["attacks"] if a["itemId"] == "rapier")["ability"] == "CHA"
    r3 = _res(catalog, 5, [BLADE], [EB, MI], added=rapier, cha=14, dex=14, extra={BLADE_W: ["rapier"]})
    assert next(a for a in r3["derived"]["attacks"] if a["itemId"] == "rapier")["ability"] == "DEX"  # a tie keeps the normal one


@needs_data
def test_pact_weapon_not_equipped_still_gets_a_row_and_thirsting_blade_is_noted(catalog):
    added = [{"itemId": "greatsword", "qty": 1, "equipped": False}]
    r = _res(catalog, 5, [BLADE, THIRST], [EB, MI], added=added, extra={BLADE_W: ["greatsword"]})
    row = next(a for a in r["derived"]["attacks"] if a["itemId"] == "greatsword")
    assert row["ability"] == "CHA" and any("Thirsting Blade" in n for n in row["notes"])
    plain = next(a for a in _res(catalog, 5, [BLADE], [EB, MI], added=added, extra={BLADE_W: ["greatsword"]})["derived"]["attacks"]
                 if a["itemId"] == "greatsword")
    assert not any("Thirsting" in n for n in plain["notes"])
    dagger = next(a for a in r["derived"]["attacks"] if a["itemId"] == "dagger")
    assert not any("Pact weapon" in n for n in dagger["notes"])


@needs_data
def test_pact_weapon_gone_from_the_inventory_is_pruned(catalog):
    r = _res(catalog, 5, [BLADE], [EB, MI], extra={BLADE_W: ["greatsword"]})  # not in the inventory
    card = _card(r, BLADE_W)
    assert card["selected"] == [] and card["status"] == "pending"
    assert _pruned(r, BLADE_W)
    assert not [p for p in r["problems"] if "over-selected" in p["id"]]


@needs_data
def test_pact_weapon_with_the_wielded_model(catalog):
    r = _res(catalog, 5, [BLADE], [EB, MI], added=LONGSWORD, wielded={"main": "longsword", "off": None},
             extra={BLADE_W: ["longsword"]})
    row = next(a for a in r["derived"]["attacks"] if a["itemId"] == "longsword")
    assert row["wielded"] is True and row["ability"] == "CHA" and row["proficient"] is True


# ---- ruleset isolation, degrade -----------------------------------------------------------------------------------------


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_pact_weapon_outside_ruleset_2024(catalog, ruleset):
    r = _res(catalog, 5, [BLADE], [EB, MI], extra={BLADE_W: ["longsword"]}, ruleset=ruleset, bg="acolyte", added=LONGSWORD)
    assert _dependent_ids(r) == []
    assert all(a["itemId"] != "longsword" or (a["ability"] == "STR" and not a["proficient"]) for a in r["derived"]["attacks"])


@needs_data
def test_srd_only_catalog_degrades(catalog):
    r = _res(_srd_only(catalog), 5, [BLADE], [EB, MI], extra={BLADE_W: ["longsword"]}, added=LONGSWORD)
    assert _dependent_ids(r) == []
