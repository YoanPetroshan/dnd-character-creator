"""Slice 9e: attacks, carrying capacity and armor warnings through resolve().
Species is Human (+1 to every ability), so base scores are one lower than the
final numbers in the comments."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, base, added=(), species="human", background="acolyte"):
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **base}},
        "equipment": {"choices": {}, "added": list(added), "skipped": False}, "details": {},
    }


def _cls(cid, level=1, choices=None):
    return {"classId": cid, "level": level, "choices": choices or {}}


def _added(item_id, qty=1, equipped=True):
    return {"itemId": item_id, "qty": qty, "equipped": equipped}


def _ids(r):
    return [w["id"] for w in r["warnings"]]


def test_rogue_granted_daggers_make_one_attack(catalog):
    # DEX 16 -> 17 (+3), prof +2; the two granted daggers are one entry
    r = resolve(_draft([_cls("rogue")], {"DEX": 16}), catalog)
    daggers = [a for a in r["derived"]["attacks"] if a["itemId"] == "dagger"]
    assert len(daggers) == 1
    assert (daggers[0]["attackBonus"], daggers[0]["damage"], daggers[0]["ability"]) == (5, "1d4+3", "DEX")
    assert r["derived"]["stealthDisadvantage"] is False  # leather armor


def test_paladin_chain_mail_strength_warning_and_stealth(catalog):
    r = resolve(_draft([_cls("paladin")], {"STR": 11}), catalog)  # STR 12 < 13
    assert "armor-strength-chain-mail" in _ids(r)
    assert not [i for i in _ids(r) if i.startswith("armor-not-proficient")]
    assert r["derived"]["stealthDisadvantage"] is True
    assert r["derived"]["speed"] == 30  # not reduced
    r = resolve(_draft([_cls("paladin")], {"STR": 12}), catalog)  # STR 13
    assert "armor-strength-chain-mail" not in _ids(r)


def test_no_class_gear_weight_capacity_and_proficiency_warning(catalog):
    added = [_added("chain-mail"), _added("longsword"), _added("dart", 10)]
    r = resolve(_draft([], {"STR": 14}, added, background=None), catalog)  # STR 15
    assert r["derived"]["carryingCapacity"] == {"capacity": 225, "pushDragLift": 450, "carried": 60.5, "overCapacity": False}
    assert "armor-not-proficient-chain-mail" in _ids(r)
    assert "armor-strength-chain-mail" not in _ids(r)
    assert r["derived"]["stealthDisadvantage"] is True


def test_background_starting_gear_is_counted(catalog):
    # Acolyte grants common clothes (3 lb) and a pouch (1 lb)
    r = resolve(_draft([], {"STR": 14}, [_added("longsword")]), catalog)
    assert r["derived"]["carryingCapacity"]["carried"] == 3 + 3 + 1


def test_unequipped_added_gear_still_weighs_but_is_not_an_attack(catalog):
    r = resolve(_draft([], {"STR": 14}, [_added("longsword", 1, equipped=False)], background=None), catalog)
    assert r["derived"]["attacks"] == []
    assert r["derived"]["carryingCapacity"]["carried"] == 3


def test_over_capacity(catalog):
    r = resolve(_draft([], {"STR": 0 + 7}, [_added("chain-mail", 4)], background=None), catalog)  # STR 8: 120 lb capacity, 220 lb carried
    assert r["derived"]["carryingCapacity"] == {"capacity": 120, "pushDragLift": 240, "carried": 220, "overCapacity": True}


def test_fighter_archery_longbow(catalog):
    # DEX 13 -> 14 (+2); prof 2; Archery 2 -> +6; damage 1d8+2
    cid = "class:fighter:1:feature:fighter-fighting-style"
    r = resolve(_draft([_cls("fighter", 1, {cid: ["fighter-fighting-style-archery"]})], {"DEX": 13}, [_added("longbow")]), catalog)
    bow = next(a for a in r["derived"]["attacks"] if a["itemId"] == "longbow")
    assert (bow["attackBonus"], bow["damage"], bow["range"]) == (6, "1d8+2", "150/600")


def test_strength_30_capacity(catalog):
    r = resolve(_draft([], {"STR": 29}), catalog)
    assert r["derived"]["carryingCapacity"]["capacity"] == 450


def test_species_size_feeds_capacity(catalog):
    # Halfling is Small (x1), same as Medium; the size lookup must not crash without a species
    assert resolve(_draft([], {"STR": 10}, species="halfling"), catalog)["derived"]["carryingCapacity"]["capacity"] == 150
    d = _draft([], {"STR": 10})
    d["species"] = {"id": None, "choices": {}}
    assert resolve(d, catalog)["derived"]["carryingCapacity"]["capacity"] == 150  # STR 10, no species: Medium
