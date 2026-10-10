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
