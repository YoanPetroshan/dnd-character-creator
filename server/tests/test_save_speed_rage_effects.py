"""R5 (decision D5 = fold into derived): always-on save, speed and rage numbers.

Governing rules, quoted from the imported data (PHB / XPHB class files, read by
script on 2026-10-09):

* Aura of Protection, Paladin 6. PHB: "the creature gains a bonus to the saving
  throw equal to your Charisma modifier (with a minimum bonus of +1)". XPHB:
  "a bonus to saving throws equal to your Charisma modifier (minimum bonus of
  +1)". Same in both editions, applies to every save (not only proficient ones).
  Caveat not modelled: you must be conscious / not Incapacitated.
* Diamond Soul, Monk 14. PHB: "proficiency in all saving throws". XPHB renames
  it Disciplined Survivor (also level 14): "proficiency in all saving throws".
* Slippery Mind, Rogue 15. PHB: "You gain proficiency in Wisdom saving throws."
  XPHB: "You gain proficiency in Wisdom and Charisma saving throws." So the
  grant depends on the ruleset: 2014 and mixed (SRD numbers, decision D2) = WIS,
  2024 = WIS + CHA. It lives in code (engine/features.py), not in the static table.
* Fast Movement, Barbarian 5. PHB: "your speed increases by 10 feet while you
  aren't wearing heavy armor". XPHB: "...while you aren't wearing Heavy armor".
  Only Heavy armor (category "Heavy") turns it off; a shield, Light and Medium
  armor do not.
* Unarmored Movement, Monk 2+ (existing): needs no armor and no shield.
  Fast Movement and Unarmored Movement are different features, so for a
  Barbarian 5 / Monk 2 both apply when unarmored (PHB "Combining Game
  Effects": only effects with the SAME name do not combine).
* Rage resistances. PHB Rage: resistance to bludgeoning, piercing and slashing.
  PHB Totem Warrior, Totem Spirit, Bear: "While raging, you have resistance to
  all damage except psychic damage" (every PHB damage type but psychic). Eagle,
  Elk, Tiger, Wolf add no resistance. XPHB Path of the Wild Heart makes the
  choice per Rage activation (Rage of the Wilds: resistance to everything except
  Force, Necrotic, Psychic, Radiant, when that option is picked); not modelled.
* Rage damage: PHB "When you make a melee weapon attack using Strength, you gain
  a +2 bonus to the damage roll"; XPHB: an attack using Strength, weapon or
  unarmed. Sneak Attack: "The attack must use a finesse or a ranged weapon".

Case matrix:
  Paladin 5 vs 6 same scores: every save +CHA mod (17 CHA -> +3) at 6, none at 5
  Paladin 6, CHA mod -1 / 0 -> +1 (the minimum); CHA mod +5 -> +5
  Paladin 6 + Fighter 1: still applies (the feature is the paladin's)
  Monk 13 vs 14: 2 vs 6 proficient saves; same under 2024
  Rogue 14 / 15, rulesets 2014, mixed, 2024: WIS (+CHA only in 2024)
  Barbarian 4 / 5; unarmored, hide (Medium), chain mail (Heavy), shield only
  Barbarian 5 / Monk 2: unarmored 50, hide 40 (UM off), chain mail 30
  Bear / Wolf / no totem, 2014 and 2024 ruleset: Rage resistances
  Attack notes: Barbarian STR melee rows only; Rogue finesse/ranged rows only
"""
import pytest

from catalog.loader import load
from engine.resolve import resolve

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
TS = "totem-warrior-phb-3-totem-spirit"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, base=None, ruleset="mixed", added=(), picks=None, species="human"):
    """classes: (classId, level[, subclassId]); human gives +1 to every score."""
    entries = []
    for spec in classes:
        e = {"classId": spec[0], "level": spec[1], "choices": dict(picks or {}) if spec[0] == "barbarian" else {}}
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


def _saves(res):
    return res["derived"]["savingThrows"]


def _rage(res):
    return next(r for r in res["derived"]["classResources"] if r["id"] == "barbarian:rage")


# ------------------------------------------------------------ Aura of Protection

def test_aura_adds_cha_mod_to_every_save(catalog):
    base = {"CHA": 16}  # human 17 -> +3
    p5 = _saves(_res(catalog, [("paladin", 5)], base))
    p6 = _saves(_res(catalog, [("paladin", 6)], base))
    assert all(p6[a] - p5[a] == 3 for a in ABS)


@pytest.mark.parametrize("cha,bonus", [(8, 1), (9, 1), (10, 1), (14, 2), (20, 5)])
def test_aura_minimum_plus_one(catalog, cha, bonus):
    # human adds 1: CHA 8 -> 9 (mod -1), 9 -> 10 (0), 10 -> 11 (0), 14 -> 15 (+2), 20 -> 21 (+5)
    p5 = _saves(_res(catalog, [("paladin", 5)], {"CHA": cha}))
    p6 = _saves(_res(catalog, [("paladin", 6)], {"CHA": cha}))
    assert all(p6[a] - p5[a] == bonus for a in ABS)


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_aura_every_ruleset(catalog, ruleset):
    p5 = _saves(_res(catalog, [("paladin", 5)], {"CHA": 16}, ruleset))
    p6 = _saves(_res(catalog, [("paladin", 6)], {"CHA": 16}, ruleset))
    assert all(p6[a] - p5[a] == 3 for a in ABS)


def test_aura_multiclass_paladin_6(catalog):
    with_fighter = _saves(_res(catalog, [("paladin", 6), ("fighter", 1)], {"CHA": 16}))
    without = _saves(_res(catalog, [("paladin", 5), ("fighter", 1)], {"CHA": 16}))
    assert all(with_fighter[a] - without[a] == 3 for a in ABS)


# ------------------------------------------------------------ Diamond Soul

@pytest.mark.parametrize("ruleset", ["2014", "2024"])
def test_diamond_soul_all_saves(catalog, ruleset):
    m13 = _res(catalog, [("monk", 13)], ruleset=ruleset)
    m14 = _res(catalog, [("monk", 14)], ruleset=ruleset)
    assert sorted(m13["sheet"]["proficiencies"]["savingThrows"]) == ["DEX", "STR"]
    assert sorted(m14["sheet"]["proficiencies"]["savingThrows"]) == sorted(ABS)
    pb = m14["derived"]["proficiencyBonus"]
    mods = m14["derived"]["abilityModifiers"]
    assert all(_saves(m14)[a] == mods[a] + pb for a in ABS)


# ------------------------------------------------------------ Slippery Mind

@pytest.mark.parametrize("ruleset,expected", [("2014", ["DEX", "INT", "WIS"]), ("mixed", ["DEX", "INT", "WIS"]),
                                              ("2024", ["CHA", "DEX", "INT", "WIS"])])
def test_slippery_mind_depends_on_ruleset(catalog, ruleset, expected):
    r15 = _res(catalog, [("rogue", 15)], ruleset=ruleset)
    assert sorted(r15["sheet"]["proficiencies"]["savingThrows"]) == expected
    pb = r15["derived"]["proficiencyBonus"]
    mods = r15["derived"]["abilityModifiers"]
    for ab in expected:
        assert _saves(r15)[ab] == mods[ab] + pb


def test_slippery_mind_not_before_15(catalog):
    r14 = _res(catalog, [("rogue", 14)], ruleset="2024")
    assert sorted(r14["sheet"]["proficiencies"]["savingThrows"]) == ["DEX", "INT"]


def test_save_proficiency_no_duplicates(catalog):
    # a Rogue 15 / Monk 14 has every save once
    r = _res(catalog, [("rogue", 15), ("monk", 14)], ruleset="2024")
    assert sorted(r["sheet"]["proficiencies"]["savingThrows"]) == sorted(ABS)


# ------------------------------------------------------------ Fast Movement

def test_fast_movement_levels_and_armor(catalog):
    assert _res(catalog, [("barbarian", 4)])["derived"]["speed"] == 30
    assert _res(catalog, [("barbarian", 5)])["derived"]["speed"] == 40
    assert _res(catalog, [("barbarian", 5)], added=["hide-armor"])["derived"]["speed"] == 40  # Medium
    assert _res(catalog, [("barbarian", 5)], added=["shield"])["derived"]["speed"] == 40
    heavy = _res(catalog, [("barbarian", 5)], added=["chain-mail"], base={"STR": 13})  # W1: STR meets the requirement
    assert heavy["derived"]["speed"] == 30
    assert heavy["derived"]["speeds"]["walk"] == 30


@pytest.mark.parametrize("ruleset", ["2014", "2024"])
def test_fast_movement_every_ruleset(catalog, ruleset):
    assert _res(catalog, [("barbarian", 5)], ruleset=ruleset)["derived"]["speed"] == 40


def test_fast_movement_stacks_with_unarmored_movement(catalog):
    # Monk 2: +10 only without armor and shield; Barbarian 5: +10 unless Heavy armor
    assert _res(catalog, [("barbarian", 5), ("monk", 2)])["derived"]["speed"] == 50
    assert _res(catalog, [("barbarian", 5), ("monk", 2)], added=["hide-armor"])["derived"]["speed"] == 40
    assert _res(catalog, [("barbarian", 5), ("monk", 2)], added=["chain-mail"], base={"STR": 13})["derived"]["speed"] == 30
    assert _res(catalog, [("barbarian", 4), ("monk", 2)])["derived"]["speed"] == 40


def test_speed_bonuses_raise_only_the_walking_speed(catalog):
    """F1 (6): "Your speed increases by 10 feet" (Fast Movement, Unarmored Movement) is the
    walking speed. WF: a Triton's swim speed is "equal to your walking speed" (stored as true), so it
    follows the final walk (Fast Movement, Unarmored Movement included); numeric modes are not raised."""
    tri = _res(catalog, [("barbarian", 1)], species="triton-mpmm")["derived"]["speeds"]
    assert tri["walk"] == 30 and tri["swim"] == 30
    for classes, walk in (([("barbarian", 5)], 40), ([("monk", 2)], 40), ([("barbarian", 5), ("monk", 2)], 50)):
        got = _res(catalog, classes, species="triton-mpmm")["derived"]
        assert got["speeds"]["walk"] == walk and got["speed"] == walk, classes
        assert got["speeds"]["swim"] == walk, classes
    heavy = _res(catalog, [("barbarian", 5)], species="triton-mpmm", added=["chain-mail"], base={"STR": 13})["derived"]["speeds"]
    assert heavy["walk"] == 30 and heavy["swim"] == 30


# ------------------------------------------------------------ Rage resistances

ALL_TYPES = ["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
             "poison", "psychic", "radiant", "slashing", "thunder"]


def test_plain_rage_resistances_unchanged(catalog):
    assert _rage(_res(catalog, [("barbarian", 3)]))["details"]["resistances"] == ["bludgeoning", "piercing", "slashing"]


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_bear_totem_resists_everything_but_psychic(catalog, ruleset):
    r = _res(catalog, [("barbarian", 3, "totem-warrior-phb")], ruleset=ruleset,
             picks={f"class:barbarian:3:feature:{TS}": [f"{TS}--bear"]})
    res = _rage(r)["details"]["resistances"]
    assert "fire" in res and "psychic" not in res
    assert sorted(res) == sorted(t for t in ALL_TYPES if t != "psychic")


def test_other_totems_and_no_pick_keep_plain_resistances(catalog):
    wolf = _res(catalog, [("barbarian", 3, "totem-warrior-phb")], picks={f"class:barbarian:3:feature:{TS}": [f"{TS}--wolf"]})
    none = _res(catalog, [("barbarian", 3, "totem-warrior-phb")])
    for r in (wolf, none):
        assert _rage(r)["details"]["resistances"] == ["bludgeoning", "piercing", "slashing"]


# ------------------------------------------------------------ Attack notes

def _attack(res, item):
    return next(a for a in res["derived"]["attacks"] if a["itemId"] == item)


def test_rage_note_on_strength_melee_rows(catalog):
    r = _res(catalog, [("barbarian", 3)], {"STR": 16, "DEX": 12}, added=["greataxe", "shortbow", "rapier"])
    assert "Rage: +2 damage" in _attack(r, "greataxe")["notes"]
    assert not any("Rage" in n for n in _attack(r, "shortbow")["notes"])
    assert _attack(r, "rapier")["ability"] == "STR"  # STR 17 > DEX 13: finesse uses STR
    assert "Rage: +2 damage" in _attack(r, "rapier")["notes"]
    r9 = _res(catalog, [("barbarian", 9)], {"STR": 16}, added=["greataxe"])
    assert "Rage: +3 damage" in _attack(r9, "greataxe")["notes"]


def test_rage_note_skips_dex_finesse_row(catalog):
    r = _res(catalog, [("barbarian", 3)], {"STR": 10, "DEX": 18}, added=["rapier"])
    assert _attack(r, "rapier")["ability"] == "DEX"
    assert not any("Rage" in n for n in _attack(r, "rapier")["notes"])


def test_no_rage_note_for_other_classes(catalog):
    r = _res(catalog, [("fighter", 3)], {"STR": 16}, added=["greataxe"])
    assert not any("Rage" in n for n in _attack(r, "greataxe")["notes"])


def test_sneak_attack_note_on_finesse_and_ranged_rows(catalog):
    r = _res(catalog, [("rogue", 3)], {"DEX": 16}, added=["rapier", "shortbow", "greataxe", "dagger"])
    assert "Sneak Attack 2d6" in _attack(r, "rapier")["notes"]
    assert "Sneak Attack 2d6" in _attack(r, "shortbow")["notes"]
    assert "Sneak Attack 2d6" in _attack(r, "dagger")["notes"]
    assert not any("Sneak" in n for n in _attack(r, "greataxe")["notes"])
    assert "Sneak Attack 10d6" in _attack(_res(catalog, [("rogue", 20)], {"DEX": 16}, added=["rapier"]), "rapier")["notes"]
    assert "Sneak Attack 1d6" in _attack(_res(catalog, [("rogue", 1)], {"DEX": 16}, added=["rapier"]), "rapier")["notes"]


def test_no_sneak_note_for_non_rogue(catalog):
    r = _res(catalog, [("fighter", 3)], {"DEX": 16}, added=["rapier"])
    assert not any("Sneak" in n for n in _attack(r, "rapier")["notes"])


def test_barbarian_rogue_multiclass_gets_both_notes_on_the_right_rows(catalog):
    r = _res(catalog, [("barbarian", 3), ("rogue", 3)], {"STR": 16, "DEX": 14}, added=["greataxe", "shortbow"])
    assert "Rage: +2 damage" in _attack(r, "greataxe")["notes"]
    assert not any("Sneak" in n for n in _attack(r, "greataxe")["notes"])
    assert "Sneak Attack 2d6" in _attack(r, "shortbow")["notes"]
    assert not any("Rage" in n for n in _attack(r, "shortbow")["notes"])
