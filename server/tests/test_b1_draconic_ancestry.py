"""B1 (owner decision 2026-11-09, plan section B item 1): the PHB Dragonborn's Draconic Ancestry (dragon colour) card.

Facts, read from the vendored `races.json` (PHB Dragonborn, source PHB, 2014) before the code:

* the species entry "Draconic Ancestry": "Choose one type of dragon from the Draconic Ancestry table. Your breath weapon and
  damage resistance are determined by the dragon type", a 10-row table Dragon | Damage Type | Breath Weapon;
* "Breath Weapon": "Your draconic ancestry determines the size, shape, and damage type of the exhalation", "a saving throw,
  the type of which is determined by your draconic ancestry. The DC ... equals 8 + your Constitution modifier + your
  proficiency bonus";
* the record's `resist` is `choose one of acid, cold, fire, lightning, poison`: the damage type alone does not name the dragon
  (fire = Brass, Gold, Red), hence a card filtered by the resistance pick.

The SRD Dragonborn (ancestry subtrait card), the FTD Dragonborn (variants) and ruleset 2024 are untouched."""
import json
import re

import pytest

from catalog import reference_data as ref
from catalog.loader import load
from catalog.official.paths import has_official, has_official_classes, official_dir
from engine.resolve import resolve
from i18n.messages import render

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools official data not available")

RES = "species:dragonborn-phb:resistance"
ANC = "species:dragonborn-phb:draconic-ancestry"
TYPES = ("acid", "cold", "fire", "lightning", "poison")
BY_TYPE = {
    "acid": ["black", "copper"], "cold": ["silver", "white"], "fire": ["brass", "gold", "red"],
    "lightning": ["blue", "bronze"], "poison": ["green"],
}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(sub=None, choices=None, level=6, con=14, ruleset="2014", species="dragonborn-phb"):
    return {"ruleset": ruleset, "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 12, "CON": con, "INT": 10, "WIS": 10, "CHA": 10}},
            "species": {"id": species, **({"subspeciesId": sub} if sub else {}), **({"choices": choices} if choices else {})},
            "background": {"id": "acolyte"}, "equipment": {"choices": {}, "added": [], "skipped": True},
            "classes": [{"classId": "fighter", "level": level, "choices": {}}]}


def _bw(res):
    return next(r for r in res["derived"]["speciesResources"] if r["name"] == "Breath Weapon")


def _card(res, cid=ANC):
    return next((c for c in res["choices"] if c["id"] == cid), None)


# ---------------------------------------------------------------- the quote pin of the 10-row table

def _raw_phb_dragonborn():
    d = json.loads((official_dir() / "races.json").read_text(encoding="utf-8"))
    return next(r for r in d["race"] if r["name"] == "Dragonborn" and r["source"] == "PHB")


@needs_data
def test_the_ten_rows_equal_the_vendored_phb_record():
    entry = next(e for e in _raw_phb_dragonborn()["entries"] if e.get("name") == "Draconic Ancestry")
    table = next(e for e in entry["entries"] if isinstance(e, dict) and e.get("type") == "table")
    assert table["colLabels"] == ["Dragon", "Damage Type", "Breath Weapon"]
    assert [tuple(r) for r in table["rows"]] == [v["row"] for v in ref.DRACONIC_ANCESTRY_PHB.values()]
    assert len(table["rows"]) == 10


@needs_data
def test_the_read_fields_agree_with_the_row_text():
    for cid, v in ref.DRACONIC_ANCESTRY_PHB.items():
        dragon, damage, breath = v["row"]
        assert cid == dragon.lower() and v["name"] == dragon and v["damage"] == damage.lower()
        if breath.startswith("5 by 30 ft. line"):
            assert (v["shape"], v["length"], v["width"]) == ("line", 30, 5)
        else:
            assert breath.startswith("15 ft. cone") and (v["shape"], v["length"], v["width"]) == ("cone", 15, None)
        assert breath.endswith(f"({v['save'][0]}{v['save'][1:].lower()}. save)")


@needs_data
def test_the_resistance_options_are_the_five_damage_types_and_the_table_groups_them():
    assert _raw_phb_dragonborn()["resist"] == [{"choose": {"from": list(TYPES)}}]
    grouped = {}
    for cid, v in ref.DRACONIC_ANCESTRY_PHB.items():
        grouped.setdefault(v["damage"], []).append(cid)
    assert grouped == BY_TYPE and sorted(grouped) == sorted(TYPES)


@needs_data
def test_the_breath_weapon_quotes_hold_in_the_catalog_text(catalog):
    from catalog.reference_data import SPECIES_RESOURCES_2014 as table
    spec = table["dragonborn-phb-trait-3"]
    text = re.sub(r"\{@\w+ ([^}|]*)[^}]*\}", r"\1", " ".join(catalog.traits["dragonborn-phb-trait-3"]["desc"]))
    for q in spec["quotes"]:
        assert q in text, q
    assert "Your draconic ancestry determines the size, shape, and damage type" in text


# ---------------------------------------------------------------- the card

@needs_data
def test_the_card_follows_the_resistance_card_and_is_pending_when_nothing_is_picked(catalog):
    res = resolve(_draft(), catalog)
    ids = [c["id"] for c in res["choices"] if c["id"].startswith("species:")]
    assert ids == [RES, ANC]
    card = _card(res)
    assert card["status"] == "pending" and card["count"] == 1 and card["source"]["kind"] == "species"
    assert [o["id"] for o in card["options"]] == list(ref.DRACONIC_ANCESTRY_PHB)
    assert card["options"][0]["label"] == "Black: Acid, 5 by 30 ft. line (Dex. save)"
    assert card["options"][6]["label"] == "Green: Poison, 15 ft. cone (Con. save)"
    assert str(card["label"]) == "Dragon Colour (Draconic Ancestry)"
    assert render(card["label"], "bg") == "Цвят на дракона" and render(card["description"], "bg") != str(card["description"])


@needs_data
@pytest.mark.parametrize("damage", TYPES)
def test_the_resistance_pick_filters_the_colours(catalog, damage):
    res = resolve(_draft(choices={RES: [damage]}), catalog)
    assert [o["id"] for o in _card(res)["options"]] == BY_TYPE[damage]
    assert _card(res)["status"] == "pending"


@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("color", sorted(ref.DRACONIC_ANCESTRY_PHB))
def test_each_colour_gives_the_breath_weapon_its_damage_type_area_and_save(catalog, color, ruleset):
    row = ref.DRACONIC_ANCESTRY_PHB[color]
    for con in (8, 14, 20):
        res = resolve(_draft(choices={RES: [row["damage"]], ANC: [color]}, con=con, level=11, ruleset=ruleset), catalog)
        assert _card(res)["status"] == "resolved" and _card(res)["selected"] == [color]
        bw = _bw(res)
        d = res["derived"]
        assert bw["dc"] == 8 + d["abilityModifiers"]["CON"] + d["proficiencyBonus"]  # 8 + CON modifier + proficiency bonus
        assert bw["dice"] == "4d6" and bw["uses"] == 1 and bw["recharge"] == "short-or-long"
        assert bw["details"]["damageType"] == row["damage"] and bw["details"]["save"] == row["save"]
        shape = f"a {row['length']}-foot {row['shape']}" + (f" that is {row['width']} feet wide" if row["width"] else "")
        assert bw["details"]["shape"] == shape
        note = bw["details"]["note"]
        assert shape in note and row["damage"].capitalize() in note and "4d6" in note
        assert {"DEX": "Dexterity", "CON": "Constitution"}[row["save"]] in note
        assert not any("Breath" in a.get("name", "") for a in d["attacks"])  # D-2: never an attack row


@needs_data
@pytest.mark.parametrize("level,dice", [(1, "2d6"), (5, "2d6"), (6, "3d6"), (11, "4d6"), (16, "5d6"), (20, "5d6")])
def test_the_dice_progression_is_unchanged(catalog, level, dice):
    assert _bw(resolve(_draft(choices={RES: ["cold"], ANC: ["white"]}, level=level), catalog))["dice"] == dice


@needs_data
def test_a_colour_alone_decides_the_damage_type_while_the_resistance_card_is_pending(catalog):
    res = resolve(_draft(choices={ANC: ["green"]}), catalog)
    assert _card(res, RES)["status"] == "pending" and _card(res)["status"] == "resolved"
    assert _bw(res)["details"]["damageType"] == "poison" and _bw(res)["details"]["save"] == "CON"


@needs_data
def test_an_old_draft_keeps_its_resistance_pick_and_gets_one_new_pending_card(catalog):
    res = resolve(_draft(choices={RES: ["fire"]}), catalog)
    assert _card(res, RES)["selected"] == ["fire"] and _card(res, RES)["status"] == "resolved"
    assert _card(res)["status"] == "pending"
    assert [c["id"] for c in res["choices"] if c["status"] == "pending" and c["id"].startswith("species:")] == [ANC]
    details = _bw(res)["details"]  # as before B1: the damage type from the resistance pick, no area / save invented
    assert details["damageType"] == "fire" and "save" not in details and "shape" not in details
    assert res["sheet"]["damageModifiers"]["resistances"] == ["fire"]
    assert res["pruned"] == [] and res["problems"] == []


@needs_data
def test_a_stored_colour_of_another_damage_type_is_pruned_and_the_card_is_pending(catalog):
    res = resolve(_draft(choices={RES: ["cold"], ANC: ["red"]}), catalog)
    assert _card(res)["status"] == "pending" and _card(res)["selected"] == []
    assert [p["choiceId"] for p in res["pruned"]] == [ANC]
    assert _bw(res)["details"]["damageType"] == "cold" and "save" not in _bw(res)["details"]


@needs_data
def test_a_junk_stored_value_is_just_pending(catalog):
    res = resolve(_draft(choices={ANC: ["purple"]}), catalog)
    assert _card(res)["status"] == "pending" and len(_card(res)["options"]) == 10
    assert _bw(res)["details"]["damageType"] is None


# ---------------------------------------------------------------- what stays as it was

@needs_data
@pytest.mark.parametrize("sub", ["dragonborn-phb-draconblood-egw", "dragonborn-phb-ravenite-egw"])
def test_the_egw_subraces_get_the_card_with_all_ten_colours(catalog, sub):
    """Their subrace entry replaces "Damage Resistance" and "Draconic Ancestry" ("Your breath weapon is determined by the
    dragon type, as shown in the table") and keeps the race's Breath Weapon: the ancestry table still decides it."""
    res = resolve(_draft(sub=sub, choices={RES: ["fire"], ANC: ["green"]}), catalog)
    assert [o["id"] for o in _card(res)["options"]] == list(ref.DRACONIC_ANCESTRY_PHB)  # not filtered by the resistance
    assert _card(res)["status"] == "resolved"
    assert _bw(res)["details"]["damageType"] == "poison" and _bw(res)["details"]["save"] == "CON"
    assert {r["name"] for r in res["derived"]["speciesResources"]} == {
        "Breath Weapon", "Forceful Presence" if "draconblood" in sub else "Vengeful Assault"}


@needs_data
@pytest.mark.parametrize("sub", ["dragonborn-phb-draconblood-egw", "dragonborn-phb-ravenite-egw"])
def test_the_egw_resistance_card_is_gone(catalog, sub):
    """VF1.4 (was pinned as "unchanged" in B1): the data replaces Damage Resistance for these subraces (`data.overwrite`), so the
    card is not offered and a stored pick grants no resistance (it is reported as a stale pick). The breath weapon still
    uses the Draconic Ancestry card."""
    res = resolve(_draft(sub=sub, choices={RES: ["fire"], ANC: ["gold"]}), catalog)
    assert _card(res, RES) is None
    assert res["sheet"]["damageModifiers"]["resistances"] == []
    assert any(p["choiceId"] == RES for p in res["pruned"])
    assert _bw(res)["details"]["damageType"] == "fire" and _bw(res)["details"]["shape"] == "a 15-foot cone"


@needs_data
def test_the_srd_ftd_and_2024_dragonborn_have_no_such_card(catalog):
    for species in ("dragonborn", "dragonborn-xphb", "dragonborn-(chromatic)-ftd", "dragonborn-(gem)-ftd", "dragonborn-(metallic)-ftd"):
        rs = "2024" if species.endswith("xphb") else "2014"
        res = resolve(_draft(species=species, ruleset=rs), catalog)
        assert not [c for c in res["choices"] if c["id"].endswith(":draconic-ancestry") and c["id"].startswith("species:dragonborn-phb")], species
        assert _card(res) is None, species


def test_the_srd_dragonborn_keeps_its_ancestry_subtrait_card(catalog):
    res = resolve(_draft(species="dragonborn", choices={"species:dragonborn:trait:draconic-ancestry": ["draconic-ancestry-red"]}),
                  catalog)
    assert _bw(res)["details"]["shape"] == "a 15-foot cone" and _card(res) is None


@needs_data
def test_exports_print_the_picked_area_and_save(catalog):
    import export_fields
    res = resolve(_draft(choices={RES: ["acid"], ANC: ["black"]}), catalog)
    lines = [t for kind, t in export_fields.extra_blocks(res) if kind == "bullet" and t.startswith("Breath Weapon:") and "exhale" in t]
    assert len(lines) == 1 and "30-foot line that is 5 feet wide" in lines[0] and "Dexterity saving throw" in lines[0]


@needs_data
def test_resolve_stays_fast(catalog):
    import time
    d = _draft(choices={RES: ["fire"], ANC: ["gold"]})
    resolve(d, catalog)
    start = time.perf_counter()
    for _ in range(10):
        resolve(d, catalog)
    assert (time.perf_counter() - start) / 10 < 0.05
