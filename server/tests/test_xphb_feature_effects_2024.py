"""RP2 (B2): fixed numeric effects of XPHB class and subclass features, ruleset "2024" only.
Governing texts are the imported XPHB feature records; `reference_data.CLASS_FEATURE_EFFECTS_2024` carries a verbatim
quote per entry and `test_quotes_match_catalog` pins them.

Rule matrix (every row 2024; the same draft under mixed is unchanged):
  Monk 20 Body and Mind        "Your Dexterity and Wisdom scores increase by 4, to a maximum of 25." (+ a pruned note when lost)
  Barbarian 20 Primal Champion "Your Strength and Constitution scores increase by 4, to a maximum of 25." (replaces the SRD cap 24)
  Draconic (XPHB) Sorcerer 3+  HP +3, +1 per further Sorcerer level (= Sorcerer level); unarmored AC 10 + DEX + CHA
  Dance Unarmored Defense      base AC 10 + DEX + CHA; the parent Dazzling Footwork says no armor and no Shield (RPF)
  Archfey 10, Land 10          Charmed / Poisoned immunity (RPF); Gloom Stalker 3 adds WIS (min 0) to Initiative (RPF)
  Shadow / Gloom Stalker       Darkvision 60, or +60 when the character already has Darkvision
  Thief 3 climb, Sea 6 swim    equal to Speed
  Glory 7                      Speed +10 (unconditional)
  Resistances                  War 17 b/p/s, Psi Warrior 10 / Aberrant 6 / Great Old One 10 psychic, Celestial 6 radiant
  Mercy 3                      Insight, Medicine, Herbalism Kit
  Ranger 6 Roving, 18 Feral Senses  +10 unless Heavy armor and climb/swim = Speed; Blindsight 30
  Conditional wording          not an effect (CLASS_FEATURE_NOTES_ONLY_2024)
  Level / subclass gating      the record's own level; a subclass feature needs that subclass selected
  SRD-only catalog             nothing applies, SRD Primal Champion (cap 24) stays"""
import time

import pytest

from catalog import reference_data, official_source
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="official data not fetched")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
EFFECT_KEYS = {"quotes", "ability_bonus", "ability_cap", "supersedes", "hp_per_class_level", "ac_formula",
               "senses_additive", "sense_range", "climb_equals_walk", "swim_equals_walk", "speed_bonus_flat",
               "speed_bonus_unless_heavy_armor", "resist", "skills", "proficiencies", "parent_quotes",
               "condition_immune", "initiative_ability"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, base=None, ruleset="2024", added=(), species="human-xphb"):
    """classes: (classId, level[, subclassId])."""
    entries = []
    for spec in classes:
        e = {"classId": spec[0], "level": spec[1], "choices": {}}
        if len(spec) > 2:
            e["subclassId"] = spec[2]
        entries.append(e)
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": entries,
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": species, "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": False},
         "details": {}}
    return resolve(d, catalog)


def _ab(r):
    return r["sheet"]["abilities"]


def _notes(r, fid):
    return [p for p in r["pruned"] if p["choiceId"] == f"feature:{fid}"]


# ------------------------------------------------------------------ data pins

def test_quotes_match_catalog(catalog):
    for fid, entry in reference_data.CLASS_FEATURE_EFFECTS_2024.items():
        text = " ".join(x for x in catalog.features[fid]["desc"] if isinstance(x, str))
        assert entry["quotes"], fid
        for q in entry["quotes"]:
            assert q in text, (fid, q)
        assert set(entry) <= EFFECT_KEYS, fid


def test_each_record_is_xphb_and_has_its_class_and_subclass(catalog):
    for fid in reference_data.CLASS_FEATURE_EFFECTS_2024:
        rec = catalog.features[fid]
        assert rec["source"] == "XPHB" and rec["class"]["index"] in catalog.classes
        if rec.get("subclass"):
            assert rec["subclass"]["index"] in catalog.subclasses, fid


def test_notes_only_quotes_match_and_are_disjoint(catalog):
    assert not set(reference_data.CLASS_FEATURE_NOTES_ONLY_2024) & set(reference_data.CLASS_FEATURE_EFFECTS_2024)
    for fid, q in reference_data.CLASS_FEATURE_NOTES_ONLY_2024.items():
        assert q in " ".join(x for x in catalog.features[fid]["desc"] if isinstance(x, str)), fid


def test_supersedes_names_an_srd_effect():
    for entry in reference_data.CLASS_FEATURE_EFFECTS_2024.values():
        if "supersedes" in entry:
            assert entry["supersedes"] in reference_data.CLASS_FEATURE_EFFECTS


# ------------------------------------------------------------------ ability scores

def test_body_and_mind(catalog):
    r = _res(catalog, [("monk", 20)], {"DEX": 14, "WIS": 14})
    assert (_ab(r)["DEX"], _ab(r)["WIS"]) == (18, 18)
    assert _notes(r, "xphb-monk-20-body-and-mind") == []
    r19 = _res(catalog, [("monk", 19)], {"DEX": 14, "WIS": 14})
    assert (_ab(r19)["DEX"], _ab(r19)["WIS"]) == (14, 14)


def test_body_and_mind_cap_25_with_pruned_note(catalog):
    r = _res(catalog, [("monk", 20)], {"DEX": 22, "WIS": 25})
    assert (_ab(r)["DEX"], _ab(r)["WIS"]) == (25, 25)
    notes = _notes(r, "xphb-monk-20-body-and-mind")
    assert len(notes) == 2 and all("Body and Mind" in n["reason"] and "25" in n["reason"] for n in notes)
    assert r["problems"] == []


def test_body_and_mind_mixed_unchanged(catalog):
    r = _res(catalog, [("monk", 20)], {"DEX": 14, "WIS": 14}, ruleset="mixed")
    assert (_ab(r)["DEX"], _ab(r)["WIS"]) == (14, 14)


def test_primal_champion_cap_25_replaces_srd_24(catalog):
    r = _res(catalog, [("barbarian", 20)], {"STR": 22, "CON": 10})
    assert (_ab(r)["STR"], _ab(r)["CON"]) == (25, 14)  # one application, not stacked with the SRD entry
    assert len(_notes(r, "xphb-barbarian-20-primal-champion")) == 1
    m = _res(catalog, [("barbarian", 20)], {"STR": 22, "CON": 10}, ruleset="mixed")
    assert (_ab(m)["STR"], _ab(m)["CON"]) == (24, 14)


# ------------------------------------------------------------------ HP and AC

def _hp(r):
    return r["derived"]["hitPointMax"]


@pytest.mark.parametrize("lvl", [3, 6, 20])
def test_draconic_xphb_hp_is_sorcerer_level(catalog, lvl):
    base = _res(catalog, [("sorcerer", lvl)])
    sub = _res(catalog, [("sorcerer", lvl, "draconic-xphb")])
    assert _hp(sub) - _hp(base) == lvl


def test_draconic_xphb_below_level_3_nothing(catalog):
    assert _hp(_res(catalog, [("sorcerer", 2, "draconic-xphb")])) == _hp(_res(catalog, [("sorcerer", 2)]))


def test_draconic_xphb_ac_matrix(catalog):
    sc = {"DEX": 14, "CHA": 16}  # human-xphb gives no species bonus: +2 / +3
    assert _res(catalog, [("sorcerer", 3, "draconic-xphb")], sc)["derived"]["armorClass"] == 15
    assert _res(catalog, [("sorcerer", 3)], sc)["derived"]["armorClass"] == 12
    assert _res(catalog, [("sorcerer", 3, "draconic-xphb")], sc, added=["shield"])["derived"]["armorClass"] == 17
    # body armor replaces the formula
    assert _res(catalog, [("sorcerer", 3, "draconic-xphb")], sc, added=["chain-mail"])["derived"]["armorClass"] == 16
    assert _res(catalog, [("sorcerer", 3, "draconic-xphb")], sc, ruleset="mixed")["derived"]["armorClass"] == 12


def test_draconic_with_barbarian_takes_the_best_formula_not_the_sum(catalog):
    r = _res(catalog, [("sorcerer", 3, "draconic-xphb"), ("barbarian", 1)], {"DEX": 14, "CHA": 12, "CON": 18})
    assert r["derived"]["armorClass"] == 10 + 2 + 4  # Barbarian (CON +4) beats 10 + DEX + CHA (+1)
    r2 = _res(catalog, [("sorcerer", 3, "draconic-xphb"), ("barbarian", 1)], {"DEX": 14, "CHA": 18, "CON": 10})
    assert r2["derived"]["armorClass"] == 10 + 2 + 4  # Draconic (CHA +4) beats CON +0


def test_dance_unarmored_defense(catalog):
    sc = {"DEX": 14, "CHA": 16}
    dance = [("bard", 3, "dance-xphb")]
    assert _res(catalog, dance, sc)["derived"]["armorClass"] == 15  # 10 + DEX 2 + CHA 3
    # Parent Dazzling Footwork: "aren't wearing armor or wielding a Shield" - a shield removes the formula.
    assert _res(catalog, dance, sc, added=["shield"])["derived"]["armorClass"] == 10 + 2 + 2
    assert _res(catalog, dance, sc, added=["chain-mail"])["derived"]["armorClass"] == 16
    m = _res(catalog, [("bard", 3)], sc, ruleset="mixed")["derived"]["armorClass"]
    assert _res(catalog, dance, sc, ruleset="mixed")["derived"]["armorClass"] == m  # mixed: no formula


def test_dance_parent_sentence_is_pinned(catalog):
    entry = reference_data.CLASS_FEATURE_EFFECTS_2024["dance-xphb-3-unarmored-defense"]
    assert entry["ac_formula"]["allows_shield"] is False
    for pid, quote in entry["parent_quotes"].items():
        assert quote in " ".join(catalog.features[pid]["desc"])


def test_archfey_beguiling_defenses_charmed_immunity(catalog):
    fid = "archfey-xphb-10-beguiling-defenses"
    assert "You are immune to the Charmed condition." in " ".join(catalog.features[fid]["desc"])
    wl = lambda lvl, rs="2024": _res(catalog, [("warlock", lvl, "archfey-xphb")], ruleset=rs)["sheet"]["conditionImmunities"]
    assert "charmed" in wl(10)
    assert "charmed" not in wl(9)
    assert "charmed" not in wl(10, "mixed")
    assert "charmed" not in _res(catalog, [("warlock", 10, "fiend-xphb")])["sheet"]["conditionImmunities"]


def test_land_natures_ward_poisoned_immunity(catalog):
    imm = lambda lvl, rs="2024": _res(catalog, [("druid", lvl, "land-xphb")], ruleset=rs)["sheet"]["conditionImmunities"]
    assert "poisoned" in imm(10) and "poisoned" not in imm(9) and "poisoned" not in imm(10, "mixed")


def test_conditional_immunities_stay_notes(catalog):
    # Aura of Courage / Devotion (in your Aura), Mindless Rage (while raging) are not sheet immunities.
    assert _res(catalog, [("paladin", 10, "devotion-xphb")])["sheet"]["conditionImmunities"] == []
    assert _res(catalog, [("barbarian", 6, "berserker-xphb")])["sheet"]["conditionImmunities"] == []


def test_gloom_stalker_dread_ambusher_initiative(catalog):
    ini = lambda sc, lvl=3, rs="2024", sub="gloom-stalker-xphb": _res(
        catalog, [("ranger", lvl, sub)], sc, ruleset=rs)["derived"]["initiative"]
    assert ini({"DEX": 14, "WIS": 16}) == 2 + 3
    assert ini({"DEX": 14, "WIS": 8}) == 2  # never negative
    assert ini({"DEX": 14, "WIS": 16}, rs="mixed") == 2
    assert ini({"DEX": 14, "WIS": 16}, sub="hunter-xphb") == 2
    assert ini({"DEX": 14, "WIS": 16}, lvl=2, sub=None) == 2


# ------------------------------------------------------------------ senses

def _dv(r):
    return r["sheet"]["senses"].get("darkvision")


@pytest.mark.parametrize("cls,sub", [("monk", "shadow-xphb"), ("ranger", "gloom-stalker-xphb")])
def test_darkvision_60_and_plus_60(catalog, cls, sub):
    assert _dv(_res(catalog, [(cls, 3, sub)])) == 60
    assert _dv(_res(catalog, [(cls, 3)])) is None
    assert _dv(_res(catalog, [(cls, 2, sub)])) is None
    assert _dv(_res(catalog, [(cls, 3, sub)], species="dwarf")) == 120  # SRD dwarf 60 + 60
    assert _dv(_res(catalog, [(cls, 3, sub)], species="dwarf-xphb")) == 180  # XPHB dwarf 120 + 60


def test_two_darkvision_features_add_in_turn(catalog):
    r = _res(catalog, [("monk", 3, "shadow-xphb"), ("ranger", 3, "gloom-stalker-xphb")])
    assert _dv(r) == 120


def test_darkvision_mixed_unchanged(catalog):
    assert _dv(_res(catalog, [("monk", 3, "shadow-xphb")], ruleset="mixed")) is None


def test_feral_senses(catalog):
    assert _res(catalog, [("ranger", 18)])["sheet"]["senses"].get("blindsight") == 30
    assert "blindsight" not in _res(catalog, [("ranger", 17)])["sheet"]["senses"]
    assert "blindsight" not in _res(catalog, [("ranger", 18)], ruleset="mixed")["sheet"]["senses"]


# ------------------------------------------------------------------ speeds

def _speeds(r):
    return r["derived"]["speeds"]


def test_thief_climb(catalog):
    s = _speeds(_res(catalog, [("rogue", 3, "thief-xphb")]))
    assert s.get("climb") == s["walk"]
    assert "climb" not in _speeds(_res(catalog, [("rogue", 2, "thief-xphb")]))
    assert "climb" not in _speeds(_res(catalog, [("rogue", 3, "thief-xphb")], ruleset="mixed"))


def test_sea_swim(catalog):
    s = _speeds(_res(catalog, [("druid", 6, "sea-xphb")]))
    assert s.get("swim") == s["walk"]
    assert "swim" not in _speeds(_res(catalog, [("druid", 5, "sea-xphb")]))
    assert "swim" not in _speeds(_res(catalog, [("druid", 6, "sea-xphb")], ruleset="mixed"))


def test_glory_speed_plus_10_even_in_heavy_armor(catalog):
    base = _speeds(_res(catalog, [("paladin", 6, "glory-xphb")]))["walk"]
    assert _speeds(_res(catalog, [("paladin", 7, "glory-xphb")]))["walk"] == base + 10
    assert _speeds(_res(catalog, [("paladin", 7, "glory-xphb")], added=["chain-mail"], base={"STR": 13}))["walk"] == base + 10
    assert _speeds(_res(catalog, [("paladin", 7, "glory-xphb")], ruleset="mixed", base={"STR": 13}))["walk"] == base  # (mixed kit holds chain mail)


def test_roving(catalog):
    base = _speeds(_res(catalog, [("ranger", 5)]))["walk"]
    r = _speeds(_res(catalog, [("ranger", 6)]))
    assert (r["walk"], r["climb"], r["swim"]) == (base + 10,) * 3
    h = _speeds(_res(catalog, [("ranger", 6)], added=["plate-armor"], base={"STR": 15}))
    assert h["walk"] == base and h["climb"] == base and h["swim"] == base
    assert "climb" not in _speeds(_res(catalog, [("ranger", 6)], ruleset="mixed"))


# ------------------------------------------------------------------ resistances and proficiencies

RESISTS = [("cleric", 17, "war-xphb", ["bludgeoning", "piercing", "slashing"]),
           ("fighter", 10, "psi-warrior-xphb", ["psychic"]), ("sorcerer", 6, "aberrant-xphb", ["psychic"]),
           ("warlock", 10, "great-old-one-xphb", ["psychic"]), ("warlock", 6, "celestial-xphb", ["radiant"])]


@pytest.mark.parametrize("cls,lvl,sub,types", RESISTS)
def test_resistances(catalog, cls, lvl, sub, types):
    got = _res(catalog, [(cls, lvl, sub)])["sheet"]["damageModifiers"]["resistances"]
    assert set(types) <= set(got)
    below = _res(catalog, [(cls, lvl - 1, sub)])["sheet"]["damageModifiers"]["resistances"]
    assert not set(types) & set(below)
    mixed = _res(catalog, [(cls, lvl, sub)], ruleset="mixed")["sheet"]["damageModifiers"]["resistances"]
    assert not set(types) & set(mixed)


def test_resistance_merges_with_species_without_duplicates(catalog):
    got = _res(catalog, [("fighter", 10, "psi-warrior-xphb")], species="dwarf")["sheet"]["damageModifiers"]["resistances"]
    assert got.count("psychic") == 1 and "poison" in got


def test_mercy_proficiencies(catalog):
    p = _res(catalog, [("monk", 3, "mercy-xphb")])["sheet"]["proficiencies"]
    assert {"skill-insight", "skill-medicine"} <= set(p["skills"]) and "herbalism-kit" in p["tools"]
    p2 = _res(catalog, [("monk", 2, "mercy-xphb")])["sheet"]["proficiencies"]
    assert "herbalism-kit" not in p2["tools"]
    pm = _res(catalog, [("monk", 3, "mercy-xphb")], ruleset="mixed")["sheet"]["proficiencies"]
    assert "herbalism-kit" not in pm["tools"]


# ------------------------------------------------------------------ degrade and speed

def test_srd_only_catalog_applies_nothing_and_keeps_srd_primal_champion(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    r = _res(cat, [("barbarian", 20)], {"STR": 22, "CON": 10})
    assert (_ab(r)["STR"], _ab(r)["CON"]) == (24, 14)
    assert _res(cat, [("monk", 20)], {"DEX": 14, "WIS": 14})["sheet"]["abilities"]["DEX"] == 14


@pytest.mark.parametrize("classes", [[("fighter", 20)], [("wizard", 20)], [("bard", 20)],
                                     [("monk", 20, "shadow-xphb")], [("sorcerer", 6, "draconic-xphb")]])
def test_resolve_speed(catalog, classes):
    _res(catalog, classes)
    start = time.perf_counter()
    for _ in range(20):
        _res(catalog, classes)
    assert (time.perf_counter() - start) / 20 < 0.05
