"""C6c-2: 2024 Blessed Strikes (Cleric 7 / Improved 14) and Elemental Fury (Druid 7 / Improved 15).

Rules (XPHB class features, text read from catalog.features on 2026-10-10):
  Blessed Strikes   "You gain one of the following options of your choice (if you get either option from a
                    Cleric subclass in an older book, use only the option you choose for this feature)."
    Divine Strike        "Once on each of your turns when you hit a creature with an attack roll using a weapon,
                         you can cause the target to take an extra 1d8 Necrotic or Radiant damage (your choice)."
    Potent Spellcasting  "Add your Wisdom modifier to the damage you deal with any Cleric cantrip."
  Improved Blessed Strikes (14)  Divine Strike "increases to 2d8"; Potent Spellcasting: a Cleric cantrip that deals
                    damage can give "Temporary Hit Points equal to twice your Wisdom modifier" (60 feet).
  Elemental Fury    "You gain one of the following options of your choice."
    Primal Strike        "... hit a creature with an attack roll using a weapon or a Beast form's attack in Wild Shape,
                         ... an extra 1d8 Cold, Fire, Lightning, or Thunder damage (choose when you hit)."
    Potent Spellcasting  "Add your Wisdom modifier to the damage you deal with any Druid cantrip."
  Improved Elemental Fury (15)   Potent: a Druid cantrip with range 10 ft or more gains +300 feet;
                    Primal Strike "increases to 2d8".
Decision E3: no cantrip damage rows exist, so the effects are class resources (dice / bonus / details.note)
and Divine / Primal Strike also add a note to weapon attack rows (as the Rage / Sneak Attack notes).

Matrix: class (Cleric, Druid, others) x level (6, 7, 13, 14, 15) x option (2 per class) x WIS (16, 8)
x ruleset (2024 / mixed / 2014) x stored pick (7 -> 6 prune, unknown option, unpicked = pending) x multiclass
(Cleric 7 / Druid 7, Cleric 7 / Fighter 1) x attack rows (weapon rows only, unarmed strike none) x
sheet.features row x export line x catalog (real / SRD-only) x C6a cards unchanged x timing."""
import time

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

BLESSED = "class:cleric:7:feature:xphb-cleric-7-blessed-strikes"
FURY = "class:druid:7:feature:xphb-druid-7-elemental-fury"
DIVINE_STRIKE, CLERIC_POTENT = "xphb-cleric-7-divine-strike", "xphb-cleric-7-potent-spellcasting"
PRIMAL_STRIKE, DRUID_POTENT = "xphb-druid-7-primal-strike", "xphb-druid-7-potent-spellcasting"
DIVINE_ORDER, PRIMAL_ORDER = "class:cleric:1:divine-order", "class:druid:1:primal-order"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", wis=10, added=()):
    return resolve({
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": wis, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                      "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }, catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _resource(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _cleric(level, pick=DIVINE_STRIKE):
    return ("cleric", level, {BLESSED: [pick]} if pick else {})


def _druid(level, pick=PRIMAL_STRIKE):
    return ("druid", level, {FURY: [pick]} if pick else {})


# ---- the card -------------------------------------------------------------------------------

@needs_data
def test_no_card_below_level_7(catalog):
    assert _card(_res(catalog, [_cleric(6, None)]), BLESSED) is None
    assert _card(_res(catalog, [_druid(6, None)]), FURY) is None


@needs_data
@pytest.mark.parametrize("cls,cid,names", [
    ("cleric", BLESSED, ["Divine Strike", "Potent Spellcasting"]),
    ("druid", FURY, ["Potent Spellcasting", "Primal Strike"])])
def test_card_at_level_7_is_required_with_two_options(catalog, cls, cid, names):
    res = _res(catalog, [(cls, 7, {})])
    card = _card(res, cid)
    assert card["status"] == "pending" and card["count"] == 1
    assert sorted(o["label"] for o in card["options"]) == names
    assert card["source"] == {"kind": "class", "id": cls, "label": cls.title(), "level": 7}
    assert card["label"] in ("Blessed Strikes", "Elemental Fury") and card["description"]
    assert all(o["description"] for o in card["options"])
    assert cid in [c["id"] for c in res["choices"] if c["status"] == "pending"]


@needs_data
def test_card_stays_after_level_7_and_resolves_when_picked(catalog):
    card = _card(_res(catalog, [_cleric(14)]), BLESSED)
    assert card["status"] == "resolved" and card["selected"] == [DIVINE_STRIKE]


@needs_data
def test_unknown_or_foreign_option_is_ignored(catalog):
    res = _res(catalog, [_cleric(7, PRIMAL_STRIKE)])
    card = _card(res, BLESSED)
    assert card["selected"] == [] and card["status"] == "pending"
    assert _resource(res, "cleric:divine-strike") is None


@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_no_card_and_no_resource_outside_2024(catalog, ruleset):
    res = _res(catalog, [_cleric(14), _druid(15)], ruleset=ruleset)
    assert _card(res, BLESSED) is None and _card(res, FURY) is None
    assert {p["choiceId"] for p in res["pruned"]} >= {BLESSED, FURY}  # stored picks are stale
    ids = {r["id"] for r in res["derived"]["classResources"]}
    assert not ids & {"cleric:divine-strike", "cleric:potent-spellcasting",
                      "druid:primal-strike", "druid:potent-spellcasting"}


@needs_data
def test_other_classes_get_no_card(catalog):
    res = _res(catalog, [("fighter", 7, {}), ("wizard", 7, {})])
    assert not [c for c in res["choices"] if "blessed-strikes" in c["id"] or "elemental-fury" in c["id"]]


@needs_data
def test_level_down_with_a_stored_pick_is_pruned(catalog):
    res = _res(catalog, [_cleric(6), _druid(6)])
    assert {p["choiceId"] for p in res["pruned"]} >= {BLESSED, FURY}
    assert _resource(res, "cleric:divine-strike") is None and _resource(res, "druid:primal-strike") is None


@needs_data
def test_c6a_orders_are_unchanged(catalog):
    res = _res(catalog, [("cleric", 7, {DIVINE_ORDER: ["xphb-cleric-1-thaumaturge"]}),
                         ("druid", 1, {PRIMAL_ORDER: ["xphb-druid-1-warden"]})])
    assert _card(res, DIVINE_ORDER)["selected"] == ["xphb-cleric-1-thaumaturge"]
    assert _card(res, PRIMAL_ORDER)["selected"] == ["xphb-druid-1-warden"]
    assert _card(res, DIVINE_ORDER)["source"]["level"] == 1


# ---- resources --------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,dice", [(7, "1d8"), (13, "1d8"), (14, "2d8"), (20, "2d8")])
def test_divine_strike_dice_by_level(catalog, level, dice):
    r = _resource(_res(catalog, [_cleric(level)]), "cleric:divine-strike")
    assert r["dice"] == dice and r["name"] == "Divine Strike" and r["uses"] is None and r["recharge"] is None
    assert r["source"] == {"kind": "class", "id": "cleric", "label": "Cleric"}
    assert "once" in r["details"]["note"].lower() and "necrotic or radiant" in r["details"]["damageTypes"].lower()


@needs_data
@pytest.mark.parametrize("level,dice", [(7, "1d8"), (14, "1d8"), (15, "2d8"), (20, "2d8")])
def test_primal_strike_dice_by_level(catalog, level, dice):
    r = _resource(_res(catalog, [_druid(level)]), "druid:primal-strike")
    assert r["dice"] == dice and r["name"] == "Primal Strike"
    assert "once" in r["details"]["note"].lower()
    assert "cold, fire, lightning, or thunder" in r["details"]["damageTypes"].lower()


@needs_data
@pytest.mark.parametrize("wis,bonus", [(16, 3), (8, -1), (10, 0)])
def test_cleric_potent_spellcasting_adds_the_wisdom_modifier(catalog, wis, bonus):
    res = _res(catalog, [_cleric(7, CLERIC_POTENT)], wis=wis)
    r = _resource(res, "cleric:potent-spellcasting")
    assert r["bonus"] == bonus == res["derived"]["abilityModifiers"]["WIS"]
    assert "cleric cantrip" in r["details"]["note"].lower()
    assert _resource(res, "cleric:divine-strike") is None


@needs_data
def test_cleric_potent_spellcasting_at_14_adds_twice_wisdom_temp_hp(catalog):
    res = _res(catalog, [_cleric(14, CLERIC_POTENT)], wis=16)
    note = _resource(res, "cleric:potent-spellcasting")["details"]["note"]
    assert "temporary hit points" in note.lower() and "6" in note
    low = _resource(_res(catalog, [_cleric(13, CLERIC_POTENT)], wis=16), "cleric:potent-spellcasting")
    assert "temporary" not in low["details"]["note"].lower()


@needs_data
def test_druid_potent_spellcasting_and_range_at_15(catalog):
    res = _res(catalog, [_druid(14, DRUID_POTENT)], wis=16)
    r = _resource(res, "druid:potent-spellcasting")
    assert r["bonus"] == 3 and "druid cantrip" in r["details"]["note"].lower()
    assert "300" not in r["details"]["note"]
    assert _resource(res, "druid:primal-strike") is None
    r15 = _resource(_res(catalog, [_druid(15, DRUID_POTENT)], wis=16), "druid:potent-spellcasting")
    assert "300 feet" in r15["details"]["note"]


@needs_data
def test_resource_order_follows_the_class(catalog):
    names = [r["name"] for r in _res(catalog, [_druid(7)])["derived"]["classResources"] if r["classId"] == "druid"]
    assert names == ["Wild Shape", "Primal Strike"]
    names = [r["name"] for r in _res(catalog, [_cleric(7)])["derived"]["classResources"] if r["classId"] == "cleric"]
    assert names == ["Channel Divinity", "Divine Strike"]


@needs_data
def test_multiclass_cleric_and_druid_get_both_cards_and_resources(catalog):
    res = _res(catalog, [_cleric(7), _druid(7, DRUID_POTENT)])
    assert _card(res, BLESSED)["selected"] == [DIVINE_STRIKE] and _card(res, FURY)["selected"] == [DRUID_POTENT]
    assert _resource(res, "cleric:divine-strike") and _resource(res, "druid:potent-spellcasting")


@needs_data
def test_a_low_level_cleric_in_a_multiclass_has_no_card(catalog):
    res = _res(catalog, [("fighter", 7, {}), _cleric(6, None)])
    assert _card(res, BLESSED) is None


# ---- attack rows -------------------------------------------------------------------------------

@needs_data
def test_weapon_rows_carry_the_divine_strike_note(catalog):
    res = _res(catalog, [_cleric(7)], added=["longsword", "longbow"])
    rows = res["derived"]["attacks"]
    assert rows
    for row in rows:
        assert "Divine Strike: +1d8 necrotic or radiant (once per turn)" in row["notes"]
    res14 = _res(catalog, [_cleric(14)], added=["longsword"])
    assert "Divine Strike: +2d8 necrotic or radiant (once per turn)" in res14["derived"]["attacks"][0]["notes"]


@needs_data
def test_weapon_rows_carry_the_primal_strike_note(catalog):
    rows = _res(catalog, [_druid(7)], added=["quarterstaff"])["derived"]["attacks"]
    assert "Primal Strike: +1d8 cold, fire, lightning, or thunder (once per turn)" in rows[0]["notes"]
    rows15 = _res(catalog, [_druid(15)], added=["quarterstaff"])["derived"]["attacks"]
    assert any(n.startswith("Primal Strike: +2d8") for n in rows15[0]["notes"])


@needs_data
def test_potent_spellcasting_adds_no_attack_note(catalog):
    rows = _res(catalog, [_cleric(7, CLERIC_POTENT)], added=["longsword"])["derived"]["attacks"]
    assert not [n for n in rows[0]["notes"] if "Strike" in n]


@needs_data
def test_no_note_without_the_pick_or_in_mixed(catalog):
    assert not [n for n in _res(catalog, [_cleric(7, None)], added=["longsword"])["derived"]["attacks"][0]["notes"]
                if "Divine" in n]
    mixed = _res(catalog, [_cleric(14)], ruleset="mixed", added=["longsword"])["derived"]["attacks"][0]
    assert not [n for n in mixed["notes"] if "Divine" in n]


# ---- sheet and export ------------------------------------------------------------------------

@needs_data
def test_features_rows_carry_the_choice(catalog):
    res = _res(catalog, [_cleric(7), _druid(7, DRUID_POTENT)])
    rows = {(f["source"]["id"], f["name"]): f for f in res["sheet"]["features"] if f["source"]["kind"] == "class"}
    assert rows[("cleric", "Blessed Strikes")]["choice"] == ["Divine Strike"]
    assert rows[("druid", "Elemental Fury")]["choice"] == ["Potent Spellcasting"]
    unchosen = _res(catalog, [_cleric(7, None)])
    row = next(f for f in unchosen["sheet"]["features"] if f["name"] == "Blessed Strikes")
    assert not row.get("choice")


@needs_data
def test_export_line_prints_dice_and_note(catalog):
    res = _res(catalog, [_cleric(14)])
    line = resource_line(_resource(res, "cleric:divine-strike"))
    assert "2d8" in line and "once per turn" in line.lower()
    bonus = resource_line(_resource(_res(catalog, [_cleric(7, CLERIC_POTENT)], wis=16), "cleric:potent-spellcasting"))
    assert "+3" in bonus


# ---- degrade and speed ---------------------------------------------------------------------------

def test_srd_only_catalog_has_no_card_and_does_not_crash(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    res = _res(cat, [_cleric(14), _druid(15)], added=["longsword"])
    assert _card(res, BLESSED) is None and _card(res, FURY) is None
    assert _resource(res, "cleric:divine-strike") is None and _resource(res, "druid:primal-strike") is None


@needs_data
@pytest.mark.parametrize("classes", [[("cleric", 20)], [("druid", 20)]])
def test_resolve_speed(catalog, classes):
    choices = {"cleric": _cleric(20)[2], "druid": _druid(20)[2]}
    spec = [(c, lv, choices[c]) for c, lv in classes]
    _res(catalog, spec, added=["longsword"])
    start = time.perf_counter()
    for _ in range(20):
        _res(catalog, spec, added=["longsword"])
    assert (time.perf_counter() - start) / 20 < 0.05
