"""W1 (gap audit F1, F3): Dwarven Toughness for official dwarves and the heavy-armor speed penalty.

Governing sentences (catalog text, tags stripped; the quote pins below read them from `catalog.traits`):

  SRD Dwarven Toughness            "Your hit point maximum increases by 1, and it increases by 1 every time you gain a level."
  Dwarf (XPHB) dwarf-xphb-trait-2  "maximum increases by 1, and it increases by 1 again whenever you gain a level."
  Dwarf (PHB) Hill                 dwarf-phb-hill-phb-trait-0: same text as the SRD
  Dwarf (Kaladesh)                 dwarf-(kaladesh)-psk-trait-6: same text as the SRD
  Stensia Tough (Innistrad)        "Your hit point maximum increases by 2, and it increases by 2 every time you gain a level."
                                   (+2 per level, not +1: the plan said "+level", the catalog text says 2)
  PHB 2014 / SRD armor table       a Strength column entry: "If the Strength column shows a score, the armor reduces
                                   the wearer's speed by 10 feet unless the wearer has a Strength score equal to or higher"
  PHB 2024 ch. 6 armor rules       "that armor reduces the wearer's speed by 10 feet unless the wearer has a Strength
                                   score equal to or higher than the listed score."
  Dwarf (PHB) dwarf-phb-trait-2    "Your speed is not reduced by wearing heavy armor."
  Dwarf (Kaladesh) psk-trait-3     "Your base walking speed is 25 feet. Your speed is not reduced by wearing heavy armor."
  SRD Dwarf                        same sentence (the SRD race record has no trait for it: pinned by race id)
  Dwarf (XPHB)                     no such trait (verified: traits 0..3 are Darkvision, Resilience, Toughness, Stonecunning).

Matrix:
  HP:    dwarf-xphb / SRD hill dwarf / dwarf-phb + hill-phb / Kaladesh / Stensia  x levels  x human control (no bonus)
         + a catalog scan: every trait whose text matches the HP-per-level sentence has an entry with that number.
  Speed: plate (STR 15) and chain mail (STR 13)  x  STR below / at the requirement  x  exempt (SRD dwarf, dwarf-phb,
         Kaladesh) vs not (dwarf-xphb, human)  x  Monk Unarmored Movement (not armor)  x  Fast Movement (+10 first,
         then -10) x floor 0 x worn=null (armor in the pack) x warning text.
"""
from __future__ import annotations

import re

import pytest

from catalog import reference_data as ref
from catalog.loader import load
from catalog.official_source import has_official
from engine.equipment import armor_warnings
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
HP_SENTENCE = re.compile(r"hit points?\|?[^}]*\}? maximum increases by (\d+), and it increases by (\d+)|"
                         r"hit point maximum increases by (\d+), and it increases by (\d+)", re.I)


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(node):
    text = " ".join(node) if isinstance(node, list) else str(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, text)


def _res(catalog, species="human", sub=None, cls="fighter", level=5, ruleset="mixed", base=None, added=(), worn=None,
         background="acolyte"):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    sp = {"id": species, "choices": {}}
    if sub:
        sp["subspeciesId"] = sub
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": background, "choices": {}}, "species": sp,
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                       "skipped": True},
         "details": {}, "preferences": {}}
    if worn is not None:
        d["equipment"]["worn"] = worn
    return resolve(d, catalog)


def _hp(r):
    return r["derived"]["hitPointMax"]


def _walk(r):
    return r["derived"]["speed"]


# ---------------------------------------------------------------- data pins

HP_TRAITS = {
    "dwarven-toughness": (1, "maximum increases by 1, and it increases by 1 every time you gain a level."),
    "dwarf-xphb-trait-2": (1, "maximum increases by 1, and it increases by 1 again whenever you gain a level."),
    "dwarf-phb-hill-phb-trait-0": (1, "maximum increases by 1, and it increases by 1 every time you gain a level."),
    "dwarf-(kaladesh)-psk-trait-6": (1, "maximum increases by 1, and it increases by 1 every time you gain a level."),
    "human-(innistrad)-psi-stensia-psi-trait-1": (2, "maximum increases by 2, and it increases by 2 every time you gain a level."),
}


@pytest.mark.parametrize("trait_id", list(HP_TRAITS))
def test_hp_trait_quote_matches_catalog_text(catalog, trait_id):
    amount, quote = HP_TRAITS[trait_id]
    assert quote in _plain(catalog.traits[trait_id]["desc"]), trait_id
    assert ref.SRD_TRAIT_EFFECTS[trait_id]["hp_per_level"] == amount
    assert ref.TRAIT_EFFECT_QUOTES[trait_id] in _plain(catalog.traits[trait_id]["desc"])


def test_every_catalog_trait_with_the_hp_per_level_sentence_is_mapped(catalog):
    found = {}
    for tid, t in catalog.traits.items():
        m = re.search(r"maximum increases by (\d+),? and it increases by (\d+)", _plain(t.get("desc", [])), re.I)
        if m:
            assert m.group(1) == m.group(2), tid
            found[tid] = int(m.group(1))
    assert set(found) == set(HP_TRAITS), set(found) ^ set(HP_TRAITS)
    for tid, amount in found.items():
        assert ref.SRD_TRAIT_EFFECTS[tid]["hp_per_level"] == amount


def test_heavy_armor_exemption_quotes_match_catalog_text(catalog):
    sentence = "speed is not reduced by wearing heavy armor."
    for tid in ("dwarf-phb-trait-2", "dwarf-(kaladesh)-psk-trait-3"):
        assert sentence in _plain(catalog.traits[tid]["desc"]).lower(), tid
    exempt = {tid for tid, t in catalog.traits.items() if sentence in _plain(t.get("desc", [])).lower()}
    assert exempt == {"dwarf-phb-trait-2", "dwarf-(kaladesh)-psk-trait-3"}  # every trait with the sentence is pinned
    assert set(ref.HEAVY_ARMOR_SPEED_EXEMPT_TRAITS) == exempt
    assert "dwarf" in ref.HEAVY_ARMOR_SPEED_EXEMPT_RACES  # SRD dwarf: no trait in the SRD record
    # dwarf-xphb has no such trait
    assert not any(sentence in _plain(catalog.traits[r["index"]]["desc"]).lower()
                   for r in catalog.races["dwarf-xphb"]["traits"])


def test_armor_strength_requirements(catalog):
    assert catalog.items["plate-armor"]["str_minimum"] == 15
    assert catalog.items["chain-mail"]["str_minimum"] == 13


# ---------------------------------------------------------------- Dwarven Toughness


def test_fighter5_con14_srd_hill_dwarf_is_49(catalog):
    r = _res(catalog, "dwarf", "hill-dwarf", base={"CON": 12})  # +2 CON racial -> 14
    assert r["sheet"]["abilities"]["CON"] == 14
    assert _hp(r) == 49


def test_fighter5_con14_dwarf_xphb_matches_srd_hill_dwarf(catalog):
    r = _res(catalog, "dwarf-xphb", ruleset="2024", base={"CON": 14})
    assert r["sheet"]["abilities"]["CON"] == 14
    assert _hp(r) == 49
    ctl = _res(catalog, "human-xphb", ruleset="2024", base={"CON": 14})
    assert _hp(r) - _hp(ctl) == 5


def test_dwarf_phb_hill_phb_gets_plus_level(catalog):
    hill = _res(catalog, "dwarf-phb", "dwarf-phb-hill-phb", base={"CON": 14})
    mountain = _res(catalog, "dwarf-phb", "dwarf-phb-mountain-phb", base={"CON": 14})
    # same CON modifier on both: the difference is exactly Dwarven Toughness
    assert hill["derived"]["abilityModifiers"]["CON"] == mountain["derived"]["abilityModifiers"]["CON"]
    assert _hp(hill) - _hp(mountain) == 5


def test_dwarf_phb_hill_toughness_scales_with_level(catalog):
    hill = _res(catalog, "dwarf-phb", "dwarf-phb-hill-phb", level=9)
    mountain = _res(catalog, "dwarf-phb", "dwarf-phb-mountain-phb", level=9)
    assert _hp(hill) - _hp(mountain) == 9


def test_kaladesh_dwarf_gets_plus_level(catalog):
    kal = _res(catalog, "dwarf-(kaladesh)-psk", level=4)
    plain = _res(catalog, "dwarf-phb", "dwarf-phb-mountain-phb", level=4)
    assert kal["derived"]["abilityModifiers"]["CON"] == plain["derived"]["abilityModifiers"]["CON"]
    assert _hp(kal) - _hp(plain) == 4


def test_stensia_tough_is_two_per_level(catalog):
    stensia = _res(catalog, "human-(innistrad)-psi", "human-(innistrad)-psi-stensia-psi", level=5)
    base = _res(catalog, "human-(innistrad)-psi", None, level=5)
    con_delta = stensia["derived"]["abilityModifiers"]["CON"] - base["derived"]["abilityModifiers"]["CON"]
    assert _hp(stensia) - _hp(base) == 10 + con_delta * 5


def test_species_without_the_trait_gain_nothing(catalog):
    a = _res(catalog, "human")
    b = _res(catalog, "dwarf-phb", "dwarf-phb-mountain-phb")
    mod = b["derived"]["abilityModifiers"]["CON"] - a["derived"]["abilityModifiers"]["CON"]
    assert _hp(b) - _hp(a) == mod * 5


def test_empty_trait_catalog_degrades(catalog, monkeypatch):
    monkeypatch.setitem(catalog.races["dwarf-xphb"], "traits", [])
    r = _res(catalog, "dwarf-xphb", ruleset="2024", base={"CON": 14})
    assert _hp(r) == 44


# ---------------------------------------------------------------- heavy armor speed

PLATE = ["plate-armor"]


def test_plate_with_str_13_walk_20(catalog):
    assert _walk(_res(catalog, base={"STR": 13}, added=PLATE)) == 20


def test_plate_with_str_15_walk_30(catalog):
    assert _walk(_res(catalog, base={"STR": 15}, added=PLATE)) == 30


def test_chain_mail_threshold_is_13(catalog):
    # (human +1 STR: base 11 -> 12 final, base 12 -> 13 final)
    assert _walk(_res(catalog, base={"STR": 11}, added=["chain-mail"])) == 20
    assert _walk(_res(catalog, base={"STR": 12}, added=["chain-mail"])) == 30


def test_armor_without_a_requirement_does_not_slow(catalog):
    assert _walk(_res(catalog, base={"STR": 8}, added=["ring-mail"])) == 30
    assert _walk(_res(catalog, base={"STR": 8}, added=["leather-armor", "shield"])) == 30


def test_final_strength_counts_not_the_base(catalog):
    # Half-Orc +2 STR: base 13 -> 15 meets plate's requirement.
    assert _walk(_res(catalog, "half-orc", base={"STR": 13}, added=PLATE)) == 30


def test_srd_dwarf_is_not_slowed(catalog):
    assert _walk(_res(catalog, "dwarf", "hill-dwarf", base={"STR": 6}, added=PLATE)) == 25


def test_dwarf_phb_and_kaladesh_are_not_slowed(catalog):
    assert _walk(_res(catalog, "dwarf-phb", "dwarf-phb-hill-phb", base={"STR": 6}, added=PLATE)) == 25
    assert _walk(_res(catalog, "dwarf-(kaladesh)-psk", base={"STR": 6}, added=PLATE)) == 25


def test_dwarf_xphb_is_slowed(catalog):
    r = _res(catalog, "dwarf-xphb", ruleset="2024", base={"STR": 10}, added=PLATE)
    assert _walk(r) == 20
    assert _walk(_res(catalog, "dwarf-xphb", ruleset="2024", base={"STR": 15}, added=PLATE)) == 30


def test_2024_ruleset_applies_the_penalty_too(catalog):
    assert _walk(_res(catalog, "human-xphb", ruleset="2024", base={"STR": 10}, added=PLATE)) == 20


def test_speeds_other_modes_keep_their_values(catalog):
    # X1: the Aarakocra's fly 50 is now removed in plate (see test_x1_fly_armor.py); a fixed swim speed shows the same rule
    r = _res(catalog, "bullywug-dmg", base={"STR": 10}, added=PLATE)
    assert r["derived"]["speeds"]["walk"] == 10
    assert r["derived"]["speeds"].get("swim") == 40
    assert "fly" not in _res(catalog, "aarakocra-eepc", base={"STR": 10}, added=PLATE)["derived"]["speeds"]


def test_monk_unarmored_movement_unaffected(catalog):
    r = _res(catalog, cls="monk", level=6, base={"STR": 10, "DEX": 16, "WIS": 14})
    walk_unarmored = _walk(r)
    assert walk_unarmored == 45  # 30 + 15 Unarmored Movement at level 6
    r2 = _res(catalog, cls="monk", level=6, base={"STR": 10}, added=PLATE)
    assert _walk(r2) == 30 - 10  # worn plate: no Unarmored Movement, then -10 for plate


def test_fast_movement_is_added_before_the_penalty(catalog):
    free = _walk(_res(catalog, cls="barbarian", level=5, base={"STR": 15}))
    assert free == 40
    # Heavy armor cancels Fast Movement; the penalty then applies to the base walk speed.
    assert _walk(_res(catalog, cls="barbarian", level=5, base={"STR": 10}, added=PLATE)) == 20
    # Chain mail under the requirement is still Heavy: no Fast Movement, -10.
    assert _walk(_res(catalog, cls="barbarian", level=5, base={"STR": 11}, added=["chain-mail"])) == 20


def test_penalty_applies_after_feat_bonuses(catalog):
    """Mobile (PHB): +10 walk. Plate under its requirement: 30 + 10 - 10 (order is irrelevant for the sum; the
    floor is what the order protects, pinned by test_floor_at_zero_unit)."""
    def fighter(added):
        d_args = dict(base={"STR": 10}, added=added)
        return _res_feat(catalog, "mobile-phb", **d_args)
    assert _walk(fighter([])) == 40
    assert _walk(fighter(PLATE)) == 30


def _res_feat(catalog, feat, **kw):
    scores = {a: 10 for a in ABS}
    scores.update(kw.get("base") or {})
    d = {"name": "t", "ruleset": "mixed", "sources": [],
         "classes": [{"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": [f"feat:{feat}"]}}],
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in kw.get("added", [])],
                       "skipped": True},
         "details": {}, "preferences": {}}
    return resolve(d, catalog)


def test_armor_in_the_pack_does_not_slow(catalog):
    r = _res(catalog, base={"STR": 10}, added=PLATE, worn={"armor": None})
    assert _walk(r) == 30


def test_worn_armor_id_slows(catalog):
    r = _res(catalog, base={"STR": 10}, added=["plate-armor", "leather-armor"], worn={"armor": "plate-armor"})
    assert _walk(r) == 20
    r = _res(catalog, base={"STR": 10}, added=["plate-armor", "leather-armor"], worn={"armor": "leather-armor"})
    assert _walk(r) == 30


def test_floor_at_zero_unit():
    from engine.resolve import _heavy_armor_speed_penalty
    assert _heavy_armor_speed_penalty({"walk": 5, "fly": 30}, 10)["walk"] == 0
    assert _heavy_armor_speed_penalty({"walk": 30}, 0) == {"walk": 30}
    assert _heavy_armor_speed_penalty({}, 10) == {}


# ---------------------------------------------------------------- warning text


def test_warning_text_no_longer_says_not_applied():
    plate = {"index": "plate-armor", "name": "Plate", "equipment_category": {"index": "armor"},
             "armor_category": "Heavy", "str_minimum": 15, "stealth_disadvantage": True}
    warnings, _ = armor_warnings([plate], {"STR": 10}, {"heavy-armor"})
    msg = next(w["message"] for w in warnings if w["id"] == "armor-strength-plate-armor")
    assert "not applied" not in msg
    assert "speed is reduced by 10 ft" in msg


def test_warning_is_not_raised_for_the_exempt_dwarf_but_is_for_others(catalog):
    ids = lambda r: [w["id"] for w in r["warnings"]]  # noqa: E731
    assert "armor-strength-plate-armor" not in ids(_res(catalog, "dwarf", "hill-dwarf", base={"STR": 6}, added=PLATE))
    assert "armor-strength-plate-armor" in ids(_res(catalog, "dwarf-xphb", ruleset="2024", base={"STR": 6}, added=PLATE))
    assert "armor-strength-plate-armor" in ids(_res(catalog, base={"STR": 6}, added=PLATE))


# ---------------------------------------------------------------- WH: speed penalty follows the suit AC counts

def test_wh_two_suits_no_pick_penalty_follows_first_suit(catalog):
    r = _res(catalog, base={"STR": 13}, added=["chain-mail", "plate-armor"])  # human +1: STR 14
    assert _walk(r) == 30
    ids = [w["id"] for w in r["warnings"]]
    assert "armor-strength-plate-armor" not in ids
    assert "armor-multiple-body" in ids
    assert r["derived"]["armorClass"] == 16  # chain mail


def test_wh_explicit_worn_plate_slows(catalog):
    r = _res(catalog, base={"STR": 13}, added=["chain-mail", "plate-armor"], worn={"armor": "plate-armor"})
    assert _walk(r) == 20
    assert "armor-strength-plate-armor" in [w["id"] for w in r["warnings"]]
