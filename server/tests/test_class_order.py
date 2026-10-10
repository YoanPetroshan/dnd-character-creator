"""C6a: 2024 Divine Order (Cleric) and Primal Order (Druid), level 1 choices with effects.

Rule (XPHB class features, text read from catalog.features on 2026-10-10):
Protector / Warden "proficiency with Martial weapons and training with Heavy / Medium armor";
Thaumaturge / Magician "You know one extra cantrip from the Cleric / Druid spell list" and a bonus
to Intelligence (Arcana or Religion / Arcana or Nature) checks "equal to your Wisdom modifier
(minimum of +1)". A level 1 class feature, so each Cleric / Druid entry of a multiclass character
grants its own (as Weapon Mastery, C2).

Matrix: ruleset (2024 / mixed / 2014) x class (Cleric, Druid, others) x option (4) x WIS (16, 8)
x level-down / option change (cantrip count and pruning) x multiclass (Cleric 1 / Fighter 1,
Cleric 1 / Druid 1) x catalog (real XPHB / SRD-only) x Weapon Mastery gate x sheet.features row."""
import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

PROTECTOR, THAUMATURGE = "xphb-cleric-1-protector", "xphb-cleric-1-thaumaturge"
MAGICIAN, WARDEN = "xphb-druid-1-magician", "xphb-druid-1-warden"
DIVINE, PRIMAL = "class:cleric:1:divine-order", "class:druid:1:primal-order"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", wis=10, choices=None):
    return resolve({
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": wis, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": (choices or {}).get(c, {})} for c, lv in classes],
    }, catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _cantrips(res, cls):
    return _card(res, f"class:{cls}:spells-cantrips")


def _wis_mod(res):
    return res["derived"]["abilityModifiers"]["WIS"]


@needs_data
@pytest.mark.parametrize("cls,cid,names", [
    ("cleric", DIVINE, ["Protector", "Thaumaturge"]), ("druid", PRIMAL, ["Magician", "Warden"])])
def test_card_is_required_and_has_the_xphb_options_under_2024(catalog, cls, cid, names):
    card = _card(_res(catalog, [(cls, 1)]), cid)
    assert card["status"] == "pending" and card["count"] == 1
    assert [o["label"] for o in card["options"]] == names
    assert card["source"] == {"kind": "class", "id": cls, "label": cls.title(), "level": 1}
    assert all(o["description"] for o in card["options"]) and card["description"]


@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_no_card_and_unchanged_outside_2024(catalog, ruleset):
    res = _res(catalog, [("cleric", 1), ("druid", 1)], ruleset=ruleset,
               choices={"cleric": {DIVINE: [THAUMATURGE]}, "druid": {PRIMAL: [WARDEN]}})
    assert _card(res, DIVINE) is None and _card(res, PRIMAL) is None
    # a stored pick is ignored like any stale card
    assert {p["choiceId"] for p in res["pruned"]} >= {DIVINE, PRIMAL}
    assert _cantrips(res, "cleric")["count"] == 3 and _cantrips(res, "druid")["count"] == 2
    assert "martial-weapons" not in res["sheet"]["proficiencies"]["weapons"]
    assert "heavy-armor" not in res["sheet"]["proficiencies"]["armor"]
    base = _res(catalog, [("cleric", 1)], ruleset=ruleset)
    assert res["derived"]["skills"]["skill-religion"] == base["derived"]["skills"]["skill-religion"]


@needs_data
def test_other_classes_get_no_card(catalog):
    res = _res(catalog, [("wizard", 1)])
    assert not [c for c in res["choices"] if c["id"].endswith(("divine-order", "primal-order"))]


@needs_data
def test_pending_until_chosen_then_resolved(catalog):
    res = _res(catalog, [("cleric", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    assert _card(res, DIVINE)["status"] == "resolved" and _card(res, DIVINE)["selected"] == [PROTECTOR]
    bad = _res(catalog, [("cleric", 1)], choices={"cleric": {DIVINE: ["xphb-druid-1-warden"]}})
    assert _card(bad, DIVINE)["status"] == "pending"
    assert _cantrips(bad, "cleric")["count"] == 3  # an invalid pick grants nothing


@needs_data
def test_protector_gives_martial_weapons_and_heavy_armor(catalog):
    plain = _res(catalog, [("cleric", 1)])["sheet"]["proficiencies"]
    assert "martial-weapons" not in plain["weapons"] and "heavy-armor" not in plain["armor"]
    res = _res(catalog, [("cleric", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    prof = res["sheet"]["proficiencies"]
    assert "martial-weapons" in prof["weapons"] and "heavy-armor" in prof["armor"]
    assert _cantrips(res, "cleric")["count"] == 3


@needs_data
def test_protector_has_no_skill_bonus(catalog):
    base = _res(catalog, [("cleric", 1)], wis=16)["derived"]["skills"]
    res = _res(catalog, [("cleric", 1)], wis=16, choices={"cleric": {DIVINE: [PROTECTOR]}})
    assert res["derived"]["skills"] == base


@needs_data
def test_warden_gives_martial_weapons_and_medium_armor_only(catalog):
    res = _res(catalog, [("druid", 1)], choices={"druid": {PRIMAL: [WARDEN]}})
    prof = res["sheet"]["proficiencies"]
    assert "martial-weapons" in prof["weapons"] and "medium-armor" in prof["armor"]
    assert "heavy-armor" not in prof["armor"]
    assert _cantrips(res, "druid")["count"] == 2


@needs_data
@pytest.mark.parametrize("wis,bonus", [(16, 3), (8, 1), (10, 1), (12, 1), (14, 2)])
def test_thaumaturge_cantrip_and_arcana_religion_bonus(catalog, wis, bonus):
    base = _res(catalog, [("cleric", 1)], wis=wis)
    res = _res(catalog, [("cleric", 1)], wis=wis, choices={"cleric": {DIVINE: [THAUMATURGE]}})
    assert _cantrips(base, "cleric")["count"] == 3 and _cantrips(res, "cleric")["count"] == 4
    assert max(1, _wis_mod(res)) == bonus
    for skill in ("skill-arcana", "skill-religion"):
        assert res["derived"]["skills"][skill] - base["derived"]["skills"][skill] == bonus
    other = {k for k in res["derived"]["skills"] if k not in ("skill-arcana", "skill-religion")}
    assert all(res["derived"]["skills"][k] == base["derived"]["skills"][k] for k in other)
    assert "martial-weapons" not in res["sheet"]["proficiencies"]["weapons"]


@needs_data
@pytest.mark.parametrize("wis,bonus", [(16, 3), (8, 1)])
def test_magician_cantrip_and_arcana_nature_bonus(catalog, wis, bonus):
    base = _res(catalog, [("druid", 1)], wis=wis)
    res = _res(catalog, [("druid", 1)], wis=wis, choices={"druid": {PRIMAL: [MAGICIAN]}})
    assert _cantrips(base, "druid")["count"] == 2 and _cantrips(res, "druid")["count"] == 3
    for skill in ("skill-arcana", "skill-nature"):
        assert res["derived"]["skills"][skill] - base["derived"]["skills"][skill] == bonus
    assert res["derived"]["skills"]["skill-religion"] == base["derived"]["skills"]["skill-religion"]


@needs_data
def test_bonus_applies_on_top_of_proficiency_and_expertise_style_totals(catalog):
    res = _res(catalog, [("cleric", 1)], wis=16, choices={"cleric": {DIVINE: [THAUMATURGE]}})
    # Acolyte is proficient in Religion: INT 0 + proficiency 2 + WIS bonus 3
    assert "skill-religion" in res["sheet"]["proficiencies"]["skills"]
    assert res["derived"]["skills"]["skill-religion"] == 0 + res["derived"]["proficiencyBonus"] + 3


@needs_data
def test_extra_cantrip_is_selectable_and_a_level_change_or_option_change_prunes_it(catalog):
    cantrips = [o["id"] for o in _cantrips(_res(catalog, [("cleric", 1)]), "cleric")["options"]][:4]
    picks = {"class:cleric:spells-cantrips": cantrips, DIVINE: [THAUMATURGE]}
    res = _res(catalog, [("cleric", 1)], choices={"cleric": picks})
    card = _cantrips(res, "cleric")
    assert card["count"] == 4 and card["selected"] == cantrips and card["status"] == "resolved"
    assert not [p for p in res["pruned"] if p["choiceId"] == card["id"]]
    # switch to Protector: 3 cantrips, the fourth is pruned (non-blocking), not a problem
    res = _res(catalog, [("cleric", 1)], choices={"cleric": {**picks, DIVINE: [PROTECTOR]}})
    card = _cantrips(res, "cleric")
    assert card["count"] == 3 and card["selected"] == cantrips[:3] and card["status"] == "resolved"
    assert [p for p in res["pruned"] if p["choiceId"] == card["id"]]
    assert not [p for p in res["problems"] if "over-selected" in p["id"]]
    # no order chosen at all: also 3
    res = _res(catalog, [("cleric", 1)], choices={"cleric": {"class:cleric:spells-cantrips": cantrips}})
    assert _cantrips(res, "cleric")["selected"] == cantrips[:3]


@needs_data
def test_extra_cantrip_scales_with_the_2024_cantrip_table(catalog):
    base = _cantrips(_res(catalog, [("cleric", 10)]), "cleric")["count"]
    res = _res(catalog, [("cleric", 10)], choices={"cleric": {DIVINE: [THAUMATURGE]}})
    assert _cantrips(res, "cleric")["count"] == base + 1
    base = _cantrips(_res(catalog, [("druid", 10)]), "druid")["count"]
    res = _res(catalog, [("druid", 10)], choices={"druid": {PRIMAL: [MAGICIAN]}})
    assert _cantrips(res, "druid")["count"] == base + 1


@needs_data
def test_multiclass_cleric_fighter_and_the_shared_proficiency_set(catalog):
    res = _res(catalog, [("fighter", 1), ("cleric", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    prof = res["sheet"]["proficiencies"]
    assert "martial-weapons" in prof["weapons"] and "heavy-armor" in prof["armor"]
    assert _card(res, DIVINE)["status"] == "resolved"
    # Cleric first, Fighter second: the Fighter's own multiclass grants add up, nothing is lost
    res = _res(catalog, [("cleric", 1), ("fighter", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    assert "heavy-armor" in res["sheet"]["proficiencies"]["armor"]
    # a secondary Cleric still gets its own required card
    res = _res(catalog, [("fighter", 1), ("cleric", 1)])
    assert _card(res, DIVINE)["status"] == "pending"


@needs_data
def test_weapon_mastery_gate_sees_martial_weapons_from_a_protector(catalog):
    # Rogue 1 / Cleric 1: the Rogue mastery filter still bars heavy martial weapons ("finesse or light"),
    # but a Fighter 1 / Cleric 1 gate depends on the shared set. Use Paladin (martial already) as control.
    res = _res(catalog, [("ranger", 1), ("cleric", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    card = _card(res, "class:ranger:weapon-mastery")
    assert not next(o for o in card["options"] if o["id"] == "longsword").get("disabled")
    # Rogue is proficient only in simple + finesse/light martial, so a Protector Cleric 1 makes a
    # martial weapon the Rogue filter allows (rapier, finesse) selectable via the shared set
    res = _res(catalog, [("rogue", 1), ("cleric", 1)], choices={"cleric": {DIVINE: [PROTECTOR]}})
    card = _card(res, "class:rogue:weapon-mastery")
    rapier = next(o for o in card["options"] if o["id"] == "rapier")
    assert not rapier.get("disabled")
    res = _res(catalog, [("rogue", 1), ("cleric", 1)], choices={"cleric": {DIVINE: [THAUMATURGE]}})
    card = _card(res, "class:rogue:weapon-mastery")
    assert next(o for o in card["options"] if o["id"] == "scimitar").get("disabledReason") == "not proficient"


@needs_data
def test_two_orders_in_one_character_stack_their_skill_bonuses(catalog):
    base = _res(catalog, [("cleric", 1), ("druid", 1)], wis=16)
    res = _res(catalog, [("cleric", 1), ("druid", 1)], wis=16,
               choices={"cleric": {DIVINE: [THAUMATURGE]}, "druid": {PRIMAL: [MAGICIAN]}})
    assert res["derived"]["skills"]["skill-arcana"] - base["derived"]["skills"]["skill-arcana"] == 6
    assert res["derived"]["skills"]["skill-religion"] - base["derived"]["skills"]["skill-religion"] == 3
    assert res["derived"]["skills"]["skill-nature"] - base["derived"]["skills"]["skill-nature"] == 3


@needs_data
def test_features_row_carries_the_chosen_order(catalog):
    res = _res(catalog, [("cleric", 1), ("druid", 1)],
               choices={"cleric": {DIVINE: [THAUMATURGE]}, "druid": {PRIMAL: [WARDEN]}})
    rows = {(f["source"]["id"], f["name"]): f for f in res["sheet"]["features"] if f["source"]["kind"] == "class"}
    assert rows[("cleric", "Divine Order")]["choice"] == ["Thaumaturge"]
    assert rows[("druid", "Primal Order")]["choice"] == ["Warden"]
    unchosen = _res(catalog, [("cleric", 1)])
    row = next(f for f in unchosen["sheet"]["features"] if f["name"] == "Divine Order")
    assert not row.get("choice")


def test_srd_only_catalog_has_no_card_and_does_not_crash(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    res = _res(cat, [("cleric", 1), ("druid", 1)],
               choices={"cleric": {DIVINE: [THAUMATURGE]}, "druid": {PRIMAL: [WARDEN]}})
    assert _card(res, DIVINE) is None and _card(res, PRIMAL) is None
    assert "martial-weapons" not in res["sheet"]["proficiencies"]["weapons"]


@needs_data
def test_resolve_speed_cleric_20(catalog):
    import time
    choices = {"cleric": {DIVINE: [THAUMATURGE]}}
    _res(catalog, [("cleric", 20)], choices=choices)
    start = time.perf_counter()
    for _ in range(20):
        _res(catalog, [("cleric", 20)], choices=choices)
    assert (time.perf_counter() - start) / 20 < 0.05
