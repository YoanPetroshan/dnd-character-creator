"""R2: Fighter and Monk resources, attacks per action, the Monk unarmed strike.

Governing rule (PHB 2014 p.164, Extra Attack, multiclassing): "If you gain the
Extra Attack class feature from more than one class, the features don't add
together. You gain only the extra attack granted by the first one" -- in
practice the character makes the largest number of attacks any one source gives
(XPHB Multiclassing says the same: Extra Attack from several classes does not
stack). So attacksPerAction = 1 + max(extra attacks of each source); sources:
Fighter 1/2/3 extra at 5/11/20 (SRD `extra_attacks`); Barbarian, Monk, Paladin,
Ranger one extra at 5 (feature `*-extra-attack`); College of Valor / Swords
(bard 6) and Bladesinging (wizard 6) one extra at 6.
Case matrix (what each case tells apart):
  Fighter 4 -> 1 (not yet) | Fighter 5 -> 2 | Fighter 11 -> 3 | Fighter 20 -> 4
  Barbarian 5 / Monk 5 / Paladin 5 / Ranger 5 -> 2 (single source)
  Fighter 5 + Barbarian 5 -> 2 (no stacking, not 3)
  Fighter 11 + Monk 5 -> 3 (the larger source wins, not 2 and not 4)
  Paladin 5 + Ranger 5 -> 2 (two equal one-extra sources do not add)
  Fighter 4 + Barbarian 5 -> 2 (the second class supplies it)
  Bard 6 no subclass -> 1; Valor bard 6 -> 2; Valor bard 6 + Fighter 11 -> 3
  Wizard 5 -> 1; no Extra Attack classes -> 1

Monk unarmed strike (Martial Arts, SRD): use DEX instead of STR for the attack
and damage rolls of unarmed strikes; the damage is the martial arts die (not
1). So the row uses the better of STR/DEX (tie STR), damage = die + modifier,
the Monk is proficient. Only characters with Monk level >= 1 get the row.

Numbers (read from the SRD level rows and the XPHB tables by script):
  2014 Martial Arts d4 (1-4), d6 (5-10), d8 (11-16), d10 (17-20); Ki = level from 2.
  2024 Martial Arts d6 (1-4), d8 (5-10), d10 (11-16), d12 (17-20); Focus Points
  0 at level 1 then = level. Save DC = 8 + PB + WIS.
  Fighter Second Wind 2014: 1 use, 1d10 + fighter level. 2024 table: 2 (1-3),
  3 (4-9), 4 (10-20); heal 1d10 + fighter level. Action Surge 1 at 2, 2 at 17;
  Indomitable 1 at 9, 2 at 13, 3 at 17 (SRD rows; same in 2024).
"""
from perf_helpers import assert_fast
import io

import pytest
import yaml
from pypdf import PdfReader

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine import attacks as attacks_mod
from engine import class_resources as cr
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", abilities=None):
    """classes: (classId, level[, subclassId]) tuples."""
    base = {"STR": 15, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = []
    for spec in classes:
        e = {"classId": spec[0], "level": spec[1], "choices": {}}
        if len(spec) > 2:
            e["subclassId"] = spec[2]
        entries.append(e)
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _apa(res):
    return res["derived"]["attacksPerAction"]


# --------------------------------------------------------------- Fighter


def test_fighter_1_second_wind_only(catalog):
    res = _res(catalog, [("fighter", 1)])
    assert [r["id"] for r in res["derived"]["classResources"]] == ["fighter:second-wind"]
    sw = _entry(res, "fighter:second-wind")
    assert sw["uses"] == 1 and sw["recharge"] == "short-or-long" and sw["details"]["heal"] == "1d10+1"
    assert sw["classId"] == "fighter" and sw["source"]["kind"] == "class"


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_fighter_srd_numbers(catalog, ruleset):
    assert _entry(_res(catalog, [("fighter", 2)], ruleset), "fighter:action-surge")["uses"] == 1
    r17 = _res(catalog, [("fighter", 17)], ruleset)
    assert _entry(r17, "fighter:action-surge")["uses"] == 2 and _entry(r17, "fighter:action-surge")["recharge"] == "short-or-long"
    ind = _entry(r17, "fighter:indomitable")
    assert ind["uses"] == 3 and ind["recharge"] == "long"
    assert _entry(r17, "fighter:second-wind")["uses"] == 1  # 2014: one use at every level
    assert _entry(r17, "fighter:second-wind")["details"]["heal"] == "1d10+17"
    assert _entry(_res(catalog, [("fighter", 8)], ruleset), "fighter:indomitable") is None
    assert _entry(_res(catalog, [("fighter", 9)], ruleset), "fighter:indomitable")["uses"] == 1
    assert _entry(_res(catalog, [("fighter", 13)], ruleset), "fighter:indomitable")["uses"] == 2
    assert _entry(_res(catalog, [("fighter", 1)], ruleset), "fighter:action-surge") is None


@needs_classes
@pytest.mark.parametrize("level,uses", [(1, 2), (3, 2), (4, 3), (9, 3), (10, 4), (20, 4)])
def test_fighter_2024_second_wind_table(catalog, level, uses):
    assert _entry(_res(catalog, [("fighter", level)], "2024"), "fighter:second-wind")["uses"] == uses


@needs_classes
def test_fighter_second_wind_recharge_by_ruleset(catalog):
    """F1 (3): XPHB "You regain one expended use when you finish a Short Rest, and you regain
    all expended uses when you finish a Long Rest" -> 2024 recharge long + shortRestRegains 1;
    2014 / mixed stay one use that returns on a short or long rest."""
    sw = _entry(_res(catalog, [("fighter", 4)], "2024"), "fighter:second-wind")
    assert sw["recharge"] == "long" and sw["details"]["shortRestRegains"] == 1 and sw["details"]["heal"] == "1d10+4"
    for ruleset in ("2014", "mixed"):
        sw = _entry(_res(catalog, [("fighter", 4)], ruleset), "fighter:second-wind")
        assert sw["recharge"] == "short-or-long" and "shortRestRegains" not in sw["details"]


@needs_classes
def test_fighter_mixed_ignores_the_2024_table(catalog):
    assert _entry(_res(catalog, [("fighter", 10)], "mixed"), "fighter:second-wind")["uses"] == 1


def test_fighter_2024_without_tables_falls_back_and_warns_once(catalog):
    import copy
    cat = copy.copy(catalog)
    cat.class_2024_tables = {}
    res = _res(cat, [("fighter", 10)], "2024")
    assert _entry(res, "fighter:second-wind")["uses"] == 1
    assert [w["id"] for w in res["warnings"]].count("class-2024-tables-missing") == 1


# ------------------------------------------------------------------ Monk


def test_monk_1_has_no_ki_and_the_martial_arts_die(catalog):
    res = _res(catalog, [("monk", 1)], "2014")
    assert [r["id"] for r in res["derived"]["classResources"]] == ["monk:martial-arts"]
    assert _entry(res, "monk:martial-arts")["die"] == "d4"


@needs_classes
def test_monk_1_2024_has_no_focus_points_and_a_d6(catalog):
    res = _res(catalog, [("monk", 1)], "2024")
    assert [r["id"] for r in res["derived"]["classResources"]] == ["monk:martial-arts"]
    assert _entry(res, "monk:martial-arts")["die"] == "d6"


def test_monk_5_2014_ki_dc_and_die(catalog):
    res = _res(catalog, [("monk", 5)], "2014", {"WIS": 16, "DEX": 16})  # human +1 -> WIS 17 (+3), DEX 17
    assert res["derived"]["abilityModifiers"]["WIS"] == 3 and res["derived"]["proficiencyBonus"] == 3
    ki = _entry(res, "monk:ki")
    assert (ki["name"], ki["uses"], ki["dc"], ki["recharge"]) == ("Ki", 5, 14, "short")  # 8 + 3 + 3
    assert _entry(res, "monk:martial-arts")["die"] == "d6"


@needs_classes
def test_monk_5_2024_focus_points_and_die(catalog):
    res = _res(catalog, [("monk", 5)], "2024", {"WIS": 16, "DEX": 16})
    fp = _entry(res, "monk:focus-points")
    assert (fp["name"], fp["uses"], fp["dc"], fp["recharge"]) == ("Focus Points", 5, 14, "short")
    assert _entry(res, "monk:ki") is None
    assert _entry(res, "monk:martial-arts")["die"] == "d8"


@pytest.mark.parametrize("ruleset,level,die", [
    ("2014", 4, "d4"), ("2014", 5, "d6"), ("2014", 11, "d8"), ("2014", 17, "d10"), ("mixed", 20, "d10"),
])
def test_monk_srd_martial_arts_die(catalog, ruleset, level, die):
    assert _entry(_res(catalog, [("monk", level)], ruleset), "monk:martial-arts")["die"] == die


@needs_classes
@pytest.mark.parametrize("level,die", [(4, "d6"), (5, "d8"), (10, "d8"), (11, "d10"), (16, "d10"), (17, "d12")])
def test_monk_2024_martial_arts_die(catalog, level, die):
    assert _entry(_res(catalog, [("monk", level)], "2024"), "monk:martial-arts")["die"] == die


def test_monk_2024_without_tables_uses_the_srd_numbers(catalog):
    import copy
    cat = copy.copy(catalog)
    cat.class_2024_tables = {}
    res = _res(cat, [("monk", 5)], "2024")
    assert _entry(res, "monk:ki")["uses"] == 5 and _entry(res, "monk:martial-arts")["die"] == "d6"
    assert [w["id"] for w in res["warnings"]].count("class-2024-tables-missing") == 1


# ------------------------------------------------------ attacks per action


@pytest.mark.parametrize("classes,expected", [
    ([("fighter", 1)], 1), ([("fighter", 4)], 1), ([("fighter", 5)], 2), ([("fighter", 10)], 2),
    ([("fighter", 11)], 3), ([("fighter", 19)], 3), ([("fighter", 20)], 4),
    ([("barbarian", 4)], 1), ([("barbarian", 5)], 2), ([("monk", 5)], 2), ([("paladin", 5)], 2), ([("ranger", 5)], 2),
    ([("fighter", 5), ("barbarian", 5)], 2),
    ([("fighter", 11), ("monk", 5)], 3),
    ([("paladin", 5), ("ranger", 5)], 2),
    ([("fighter", 4), ("barbarian", 5)], 2),
    ([("wizard", 5)], 1), ([("bard", 6)], 1), ([("rogue", 20)], 1),
])
def test_attacks_per_action_does_not_stack(catalog, classes, expected):
    assert _apa(_res(catalog, classes)) == expected


@needs_official
@pytest.mark.parametrize("classes,expected", [
    ([("bard", 6, "valor-phb")], 2), ([("bard", 5, "valor-phb")], 1),
    ([("bard", 6, "swords-xge")], 2), ([("bard", 6, "valor-phb"), ("fighter", 11)], 3),
    ([("wizard", 6, "bladesinging-tce")], 2),
])
def test_attacks_per_action_subclass_sources(catalog, classes, expected):
    assert _apa(_res(catalog, classes, "2014")) == expected


@needs_classes
def test_attacks_per_action_xphb_valor(catalog):
    assert _apa(_res(catalog, [("bard", 6, "valor-xphb")], "2024")) == 2


@needs_official
def test_extra_attack_feature_ids_exist_in_the_catalog(catalog):
    for fid in cr.EXTRA_ATTACK_FEATURES:
        if fid.endswith("-xphb-6-extra-attack") or fid.endswith("frhof-6-extra-attack") or "-tce-" in fid or "-xge-" in fid:
            continue  # official-only ids may be absent without the 5etools files
        assert fid in catalog.features, fid


@needs_classes
def test_every_extra_attack_feature_in_the_catalog_is_in_the_table(catalog):
    fighter = {"extra-attack-1"}  # the Fighter's own 5/11/20 come from the level-row `extra_attacks`
    # C1 imported XPHB class features (`xphb-*`) are 2024 chassis data, not read by the 2014 table
    named = {fid for fid, f in catalog.features.items()
             if f["name"] == "Extra Attack" and not fid.startswith("xphb-")} - fighter
    assert named == set(cr.EXTRA_ATTACK_FEATURES)


# ---------------------------------------------------- Monk unarmed strike


def test_unarmed_strike_function_picks_the_better_ability():
    m = {"STR": 1, "DEX": 3, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}
    a = attacks_mod.unarmed_strike(m, 3, "d6")
    assert (a["itemId"], a["ability"], a["proficient"], a["attackBonus"], a["damage"], a["damageType"]) == (
        "unarmed-strike", "DEX", True, 6, "1d6+3", "bludgeoning")
    # tie goes to STR; no die -> 1 + modifier
    t = attacks_mod.unarmed_strike({"STR": 2, "DEX": 2}, 2, None)
    assert t["ability"] == "STR" and t["damage"] == "1+2" and t["attackBonus"] == 4


def test_monk_gets_an_unarmed_strike_row(catalog):
    res = _res(catalog, [("monk", 5)], "2014", {"DEX": 18, "WIS": 16})
    row = next(a for a in res["derived"]["attacks"] if a["itemId"] == "unarmed-strike")
    assert (row["ability"], row["attackBonus"], row["damage"]) == ("DEX", 7, "1d6+4")  # DEX 19 (+4) + PB 3 > STR 16 (+3)
    assert row["name"] == "Unarmed Strike" and row["proficient"] is True and row["damageType"] == "bludgeoning"


@needs_classes
def test_monk_2024_unarmed_strike_uses_the_2024_die(catalog):
    res = _res(catalog, [("monk", 5)], "2024", {"DEX": 18})
    row = next(a for a in res["derived"]["attacks"] if a["itemId"] == "unarmed-strike")
    assert row["damage"] == "1d8+4"


def test_monk_1_unarmed_strike(catalog):
    res = _res(catalog, [("monk", 1)], "2014", {"DEX": 18})
    row = next(a for a in res["derived"]["attacks"] if a["itemId"] == "unarmed-strike")
    assert row["damage"] == "1d4+4" and row["attackBonus"] == 6  # DEX 19 (+4) + PB 2


def test_strength_monk_uses_strength(catalog):
    res = _res(catalog, [("monk", 1)], "2014", {"STR": 17, "DEX": 8})
    row = next(a for a in res["derived"]["attacks"] if a["itemId"] == "unarmed-strike")
    assert row["ability"] == "STR"


def test_non_monks_have_no_unarmed_strike_row(catalog):
    for classes in ([("fighter", 5)], [("barbarian", 3)], [("rogue", 1)]):
        assert not any(a["itemId"] == "unarmed-strike" for a in _res(catalog, classes)["derived"]["attacks"])


def test_multiclass_monk_level_1_gets_the_row_with_its_die(catalog):
    res = _res(catalog, [("fighter", 5), ("monk", 1)], "2014", {"DEX": 18})
    row = next(a for a in res["derived"]["attacks"] if a["itemId"] == "unarmed-strike")
    assert row["damage"].startswith("1d4")


def test_no_catalog_item_is_called_unarmed_strike(catalog):
    assert "unarmed-strike" not in catalog.items
    assert not any("unarmed" in k or "unarmed" in (v.get("name") or "").lower() for k, v in catalog.items.items())


def test_unarmed_row_is_alongside_weapons_not_deduped(catalog):
    res = _res(catalog, [("monk", 3)], "2014")
    ids = [a["itemId"] for a in res["derived"]["attacks"]]
    assert ids.count("unarmed-strike") == 1 and ids[-1] == "unarmed-strike"


# ---------------------------------------------------------------- exports


def test_exports_carry_attacks_per_action_and_resources(catalog):
    res = _res(catalog, [("fighter", 5), ("monk", 5)], "2014")
    doc = yaml.safe_load(to_yaml(res))
    assert doc["attacksPerAction"] == 2
    md = to_markdown(res)
    assert "- Атаки на действие: 2" in md
    assert "- Ki: 5, ТС 12, кратка почивка (Short Rest)" in md and "- Second Wind: 1, кратка почивка (Short Rest) или дълга почивка (Long Rest), лекуване 1d10+5" in md
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "Атаки на действие: 2" in text


def test_attacks_per_action_line_for_a_single_attack_character(catalog):
    assert "- Атаки на действие: 1" in to_markdown(_res(catalog, [("monk", 1)]))


# ---------------------------------------------------------------- timing


@pytest.mark.parametrize("classes", [[("fighter", 20)], [("monk", 20)]])
def test_level_20_resolve_is_fast(catalog, classes):
    import time
    _res(catalog, classes)  # warm up
    laps = []
    for _ in range(10):
        t_run = time.perf_counter()
        _res(catalog, classes, "2024")
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
