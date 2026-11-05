"""C2: 2024 Weapon Mastery choice and mastery on attack rows.

Rule (XPHB class features "Weapon Mastery", read from the 5etools class files on
2026-10-10): Barbarian "two kinds of Simple or Martial Melee weapons" (table column
2,2,2,3 from L4,4 from L10), Fighter "three kinds of Simple or Martial weapons"
(table 3, 4 at L4, 5 at L10, 6 at L16), Paladin / Ranger / Rogue "two kinds of
weapons ... with which you have proficiency" (fixed 2, no table column). The Rogue's
proficiency itself is simple + martial Finesse/Light weapons. The feature is a
level 1 class feature, so each class of a multiclass character grants its own.

Matrix: ruleset (2024 / mixed / 2014) x class (the five / others) x level (count)
x class filter (Barbarian ranged, Rogue heavy martial) x proficiency gate (SRD-chassis
Rogue lacks e.g. Scimitar) x level-down prune x equipped weapon -> attack row."""
from perf_helpers import assert_fast
import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", added=(), choices=None):
    return resolve({
        "ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": list(added), "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": (choices or {}).get(c, {})} for c, lv in classes],
    }, catalog)


def _card(res, cls):
    return next((c for c in res["choices"] if c["id"] == f"class:{cls}:weapon-mastery"), None)


def _opt(card, item_id):
    return next(o for o in card["options"] if o["id"] == item_id)


@needs_data
@pytest.mark.parametrize("level,count", [(1, 3), (3, 3), (4, 4), (9, 4), (10, 5), (15, 5), (16, 6), (20, 6)])
def test_fighter_counts(catalog, level, count):
    card = _card(_res(catalog, [("fighter", level)]), "fighter")
    assert card["count"] == count
    longsword = _opt(card, "longsword")
    assert longsword["label"] == "Longsword (Sap)" and not longsword.get("disabled")


@needs_data
@pytest.mark.parametrize("level,count", [(1, 2), (3, 2), (4, 3), (9, 3), (10, 4), (20, 4)])
def test_barbarian_counts(catalog, level, count):
    assert _card(_res(catalog, [("barbarian", level)]), "barbarian")["count"] == count


@needs_data
@pytest.mark.parametrize("cls", ["paladin", "ranger", "rogue"])
def test_fixed_two_for_paladin_ranger_rogue(catalog, cls):
    for level in (1, 10):
        assert _card(_res(catalog, [(cls, level)]), cls)["count"] == 2


@needs_data
def test_barbarian_ranged_weapon_disabled(catalog):
    card = _card(_res(catalog, [("barbarian", 1)]), "barbarian")
    longbow = _opt(card, "longbow")
    assert longbow["disabled"] and "melee" in longbow["disabledReason"]
    assert not _opt(card, "greataxe").get("disabled")


@needs_data
def test_rogue_filter_and_proficiency(catalog):
    card = _card(_res(catalog, [("rogue", 1)]), "rogue")
    assert _opt(card, "greatsword")["disabled"]
    assert not _opt(card, "rapier").get("disabled")
    assert not _opt(card, "dagger").get("disabled")
    # Longsword is martial without Finesse/Light: the Rogue is not proficient (F3a-8: no Rogue-specific filter)
    assert _opt(card, "longsword")["disabled"] and _opt(card, "longsword")["disabledReason"] == "not proficient"
    assert _opt(card, "greatsword")["disabledReason"] == "not proficient"
    # F1: the 2024 Rogue is proficient with martial Finesse/Light weapons, Scimitar included
    assert not _opt(card, "scimitar").get("disabled")


@needs_data
def test_non_mastery_weapons_are_not_offered(catalog):
    ids = {o["id"] for o in _card(_res(catalog, [("fighter", 1)]), "fighter")["options"]}
    assert "net" not in ids and "hoopak" not in ids
    assert "musket" in ids and "pistol" in ids  # D9: imported weapons with a mastery


@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_no_card_outside_2024(catalog, ruleset):
    res = _res(catalog, [("fighter", 1)], ruleset)
    assert _card(res, "fighter") is None
    assert res["sheet"]["weaponMasteries"] == []


@needs_data
def test_no_card_for_other_classes(catalog):
    assert _card(_res(catalog, [("wizard", 1)]), "wizard") is None


@needs_data
def test_selection_and_level_down_prune(catalog):
    picks = ["longsword", "greataxe", "dagger", "rapier"]
    res = _res(catalog, [("fighter", 4)], choices={"fighter": {"class:fighter:weapon-mastery": picks}})
    assert _card(res, "fighter")["status"] == "resolved"
    assert [m["itemId"] for m in res["sheet"]["weaponMasteries"]] == picks
    assert res["sheet"]["weaponMasteries"][0] == {"itemId": "longsword", "name": "Longsword", "mastery": "Sap"}
    res = _res(catalog, [("fighter", 3)], choices={"fighter": {"class:fighter:weapon-mastery": picks}})
    assert _card(res, "fighter")["selected"] == picks[:3]
    assert any(p["choiceId"] == "class:fighter:weapon-mastery" and "now allows 3" in p["reason"]
               for p in res["pruned"])
    assert not any(p["id"].startswith("over-selected") for p in res["problems"])


@needs_data
def test_stale_disabled_pick_is_dropped(catalog):
    res = _res(catalog, [("barbarian", 1)], choices={"barbarian": {"class:barbarian:weapon-mastery": ["longbow", "greataxe"]}})
    assert _card(res, "barbarian")["selected"] == ["greataxe"]
    assert [m["itemId"] for m in res["sheet"]["weaponMasteries"]] == ["greataxe"]


@needs_data
def test_attack_row_gets_mastery(catalog):
    res = _res(catalog, [("fighter", 1)], added=[{"itemId": "longsword", "qty": 1, "equipped": True}],
               choices={"fighter": {"class:fighter:weapon-mastery": ["longsword", "dagger", "rapier"]}})
    rows = {a["itemId"]: a for a in res["derived"]["attacks"]}
    assert rows["longsword"]["mastery"] == "Sap"
    other = _res(catalog, [("fighter", 1)], added=[{"itemId": "longsword", "qty": 1, "equipped": True}])
    assert next(a for a in other["derived"]["attacks"] if a["itemId"] == "longsword")["mastery"] is None


@needs_data
def test_fighter_and_rogue_get_two_cards(catalog):
    res = _res(catalog, [("fighter", 1), ("rogue", 1)])
    assert _card(res, "fighter")["count"] == 3 and _card(res, "rogue")["count"] == 2
    # a secondary Rogue gets no weapon proficiency from multiclassing, but Fighter's covers martial
    assert not _opt(_card(res, "rogue"), "rapier").get("disabled")


@needs_data
def test_secondary_rogue_alone_lacks_proficiency(catalog):
    res = _res(catalog, [("wizard", 1), ("rogue", 1)])
    assert _opt(_card(res, "rogue"), "rapier")["disabled"]


@needs_data
def test_exports_carry_masteries(catalog):
    from export_fields import extra_blocks
    res = _res(catalog, [("fighter", 1)], added=[{"itemId": "longsword", "qty": 1, "equipped": True}],
               choices={"fighter": {"class:fighter:weapon-mastery": ["longsword", "dagger", "rapier"]}})
    blocks = extra_blocks(res)
    assert ("h2", "Майсторство с оръжия (Weapon Mastery)") in blocks
    assert ("bullet", "Longsword: Sap") in blocks
    assert any(k == "bullet" and t.startswith("Longsword: +") and "майсторство Sap" in t for k, t in blocks)


def test_srd_only_catalog_has_no_card(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    monkeypatch.setattr(official_source, "items_base_file", lambda: None)
    cat = load()
    res = _res(cat, [("fighter", 1), ("barbarian", 1)])
    assert _card(res, "fighter") is None and _card(res, "barbarian") is None
    assert res["sheet"]["weaponMasteries"] == []


@needs_data
def test_resolve_speed_fighter_20(catalog):
    import time
    _res(catalog, [("fighter", 20)])
    laps = []
    for _ in range(20):
        t_run = time.perf_counter()
        _res(catalog, [("fighter", 20)])
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)


def _gear(*ids):
    return [{"itemId": i, "qty": 1, "equipped": True} for i in ids]


def _atk(res, item_id):
    return next(a for a in res["derived"]["attacks"] if a["itemId"] == item_id)


@needs_data
def test_rogue_2024_weapon_proficiency_rule(catalog):
    """F1 (C2). XPHB Rogue startingProficiencies.weapons: Simple + "Martial weapons that have
    the Finesse or Light property"; its multiclassing proficienciesGained lists no weapons.
    Cases: 2024 primary Rogue (scimitar, whip, rapier, shortsword: proficient; longsword,
    greatsword: not) | 2014 / mixed Rogue = SRD list (longsword, rapier yes; scimitar no) |
    secondary Rogue (no weapon proficiency from multiclassing) | Rogue + Fighter (Fighter's
    martial covers all) | attack rows follow the same proficiency (+2 proficiency bonus)."""
    gear = _gear("scimitar", "whip", "rapier", "shortsword", "longsword", "dagger")
    res = _res(catalog, [("rogue", 1)], added=gear)
    plain = {i: _atk(res, i)["attackBonus"] for i in ("scimitar", "whip", "rapier", "shortsword", "longsword", "dagger")}
    assert plain["longsword"] == 2  # DEX 14 is not used (longsword is not finesse): STR 14 = +2, no proficiency
    for i in ("scimitar", "whip", "rapier", "shortsword", "dagger"):
        assert plain[i] == 4, i  # DEX +2 + proficiency 2
    weapons = res["sheet"]["proficiencies"]["weapons"]
    assert "martial-weapons-finesse-or-light" in weapons and "longswords" not in weapons
    for ruleset in ("2014", "mixed"):
        old = _res(catalog, [("rogue", 1)], ruleset, added=gear)
        assert _atk(old, "longsword")["attackBonus"] == 4 and _atk(old, "rapier")["attackBonus"] == 4
        assert _atk(old, "scimitar")["attackBonus"] == 2 and _atk(old, "whip")["attackBonus"] == 2
        assert "martial-weapons-finesse-or-light" not in old["sheet"]["proficiencies"]["weapons"]
    sec = _res(catalog, [("wizard", 1), ("rogue", 1)], added=gear)
    assert _atk(sec, "rapier")["attackBonus"] == 2 and "martial-weapons-finesse-or-light" not in sec["sheet"]["proficiencies"]["weapons"]
    both = _res(catalog, [("fighter", 1), ("rogue", 1)], added=gear)
    assert _atk(both, "longsword")["attackBonus"] == 4 and _atk(both, "scimitar")["attackBonus"] == 4


@needs_data
def test_rogue_mastery_has_no_class_filter_proficiency_alone_limits_it(catalog):
    """F3a-8: XPHB Rogue "two kinds of weapons of your choice with which you have proficiency". A Rogue who is
    also proficient with every martial weapon (Fighter 1) may pick a heavy one."""
    cid = "class:rogue:weapon-mastery"
    res = _res(catalog, [("fighter", 1), ("rogue", 1)], choices={"rogue": {cid: ["greatsword", "longsword"]}})
    card = _card(res, "rogue")
    assert not _opt(card, "greatsword").get("disabled")
    assert card["selected"] == ["greatsword", "longsword"] and card["status"] == "resolved"


@needs_data
def test_rogue_2024_mastery_accepts_scimitar_and_whip(catalog):
    cid = "class:rogue:weapon-mastery"
    res = _res(catalog, [("rogue", 1)], choices={"rogue": {cid: ["scimitar", "whip"]}})
    assert _card(res, "rogue")["selected"] == ["scimitar", "whip"] and _card(res, "rogue")["status"] == "resolved"
    assert res["pruned"] == []


@needs_data
def test_proficiency_gate_runs_before_count_truncation(catalog):
    """F1 (5): a stored pick the character is not proficient with must not use up a slot.
    Wizard 1 / Rogue 1 (a secondary Rogue has no martial proficiency), count 2, stored
    [scimitar, dagger, quarterstaff]: scimitar is not proficient, so the result is [dagger, quarterstaff]
    (not [dagger]) and each prune message names its real reason."""
    cid = "class:rogue:weapon-mastery"
    res = _res(catalog, [("wizard", 1), ("rogue", 1)], choices={"rogue": {cid: ["scimitar", "dagger", "quarterstaff"]}})
    card = _card(res, "rogue")
    assert card["selected"] == ["dagger", "quarterstaff"] and card["status"] == "resolved"
    reasons = [p["reason"] for p in res["pruned"] if p["choiceId"] == cid]
    assert len(reasons) == 1 and "Scimitar" in reasons[0] and "no longer a proficient weapon" in reasons[0]
    assert "now allows" not in reasons[0]
    # a plain over-count (all proficient) still says so, and drops the LAST picks
    over = _res(catalog, [("rogue", 1)], choices={"rogue": {cid: ["scimitar", "rapier", "dagger"]}})
    assert _card(over, "rogue")["selected"] == ["scimitar", "rapier"]
    reasons = [p["reason"] for p in over["pruned"] if p["choiceId"] == cid]
    assert len(reasons) == 1 and "now allows 2" in reasons[0] and "Dagger" in reasons[0]
    # a class-filter exclusion (Rogue, Longsword) is not blamed on the count
    filt = _res(catalog, [("rogue", 1)], choices={"rogue": {cid: ["longsword", "rapier", "dagger"]}})
    assert _card(filt, "rogue")["selected"] == ["rapier", "dagger"]
    reasons = [p["reason"] for p in filt["pruned"] if p["choiceId"] == cid]
    assert len(reasons) == 1 and "now allows" not in reasons[0] and "Longsword" in reasons[0]
