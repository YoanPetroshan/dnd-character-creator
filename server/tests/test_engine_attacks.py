"""Slice 9a: weapon attacks. Every expected number is hand-computed from the
5e rules (STR 16 = +3, DEX 14 = +2, proficiency bonus 2), not from the code."""
import pytest

from catalog import reference_data
from catalog.loader import load
from engine import attacks as attacks_mod
from engine import features as features_mod


@pytest.fixture(scope="module")
def items():
    return load().items


def _mods(**kw):
    base = {"STR": 0, "DEX": 0, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}
    base.update(kw)
    return base


def _styles(*feature_ids):
    effects = features_mod.active_effects([("fighter", 1, f) for f in feature_ids])
    return features_mod.attack_styles(effects)


SIMPLE_MARTIAL = {"simple-weapons", "martial-weapons"}


def attack(items, item_id, modifiers, prof=2, profs=SIMPLE_MARTIAL, styles=None):
    return attacks_mod.weapon_attack(items[item_id], modifiers, prof, profs, styles or _styles())


def test_longsword_plain(items):
    a = attack(items, "longsword", _mods(STR=3, DEX=2))
    assert a["itemId"] == "longsword" and a["name"] == "Longsword"
    assert (a["ability"], a["proficient"], a["attackBonus"]) == ("STR", True, 5)
    assert (a["damage"], a["damageType"], a["versatileDamage"], a["offhandDamage"], a["range"]) == (
        "1d8+3", "slashing", "1d10+3", None, "5")
    assert a["notes"] == []


def test_dueling_adds_to_one_handed_melee_not_versatile(items):
    a = attack(items, "longsword", _mods(STR=3, DEX=2), styles=_styles("fighter-fighting-style-dueling"))
    assert a["damage"] == "1d8+5"
    assert a["versatileDamage"] == "1d10+3"
    assert "Dueling: only with no other weapon" in a["notes"]


def test_dueling_does_not_apply_to_two_handed_or_ranged(items):
    d = _styles("fighting-style-dueling")
    g = attack(items, "greatsword", _mods(STR=3), styles=d)
    assert g["damage"] == "2d6+3" and not any("Dueling" in n for n in g["notes"])
    b = attack(items, "longbow", _mods(DEX=2), styles=d)
    assert b["damage"] == "1d8+2"


def test_longbow_with_archery(items):
    a = attack(items, "longbow", _mods(STR=3, DEX=2), styles=_styles("ranger-fighting-style-archery"))
    assert (a["ability"], a["attackBonus"], a["damage"], a["range"]) == ("DEX", 6, "1d8+2", "150/600")
    assert a["versatileDamage"] is None and a["offhandDamage"] is None
    assert a["notes"] == ["two-handed", "heavy", "ammunition"]


def test_archery_does_not_boost_melee(items):
    a = attack(items, "longsword", _mods(STR=3), styles=_styles("fighter-fighting-style-archery"))
    assert a["attackBonus"] == 5


def test_finesse_picks_higher_modifier(items):
    # rapier, STR 10 (0) DEX 16 (+3), proficient: DEX, +3+2 = 5, 1d8+3
    a = attack(items, "rapier", _mods(STR=0, DEX=3), profs={"rapiers"})
    assert (a["ability"], a["attackBonus"], a["damage"]) == ("DEX", 5, "1d8+3")
    # tie goes to STR
    a = attack(items, "rapier", _mods(STR=2, DEX=2), profs={"rapiers"})
    assert a["ability"] == "STR"


def test_dagger_finesse_light_thrown(items):
    # STR 8 (-1), DEX 14 (+2), proficient with daggers
    a = attack(items, "dagger", _mods(STR=-1, DEX=2), profs={"daggers"})
    assert (a["ability"], a["attackBonus"], a["damage"], a["range"]) == ("DEX", 4, "1d4+2", "20/60")
    assert a["offhandDamage"] == "1d4"  # off hand: no positive modifier
    assert a["notes"] == ["thrown"]
    twf = attack(items, "dagger", _mods(STR=-1, DEX=2), profs={"daggers"}, styles=_styles("fighter-fighting-style-two-weapon-fighting"))
    assert twf["offhandDamage"] == "1d4+2"


def test_negative_modifier_offhand_keeps_the_penalty(items):
    # Light weapon, STR -1 and no finesse: off hand still takes -1
    a = attack(items, "sickle", _mods(STR=-1, DEX=-1), profs={"sickles"})
    assert a["damage"] == "1d4-1" and a["offhandDamage"] == "1d4-1"


def test_not_proficient_drops_the_proficiency_bonus(items):
    a = attack(items, "longsword", _mods(STR=-1), profs={"daggers"})
    assert (a["proficient"], a["attackBonus"], a["damage"]) == (False, -1, "1d8-1")


def test_thrown_melee_weapon_uses_strength(items):
    a = attack(items, "handaxe", _mods(STR=3, DEX=4), profs={"simple-weapons"})
    assert (a["ability"], a["attackBonus"], a["damage"], a["range"], a["offhandDamage"]) == ("STR", 5, "1d6+3", "20/60", "1d6")


def test_zero_modifier_gives_bare_dice(items):
    a = attack(items, "mace", _mods(STR=0), profs={"simple-weapons"})
    assert a["damage"] == "1d6" and a["versatileDamage"] is None


def test_great_weapon_fighting_note(items):
    g = attack(items, "greatsword", _mods(STR=3), styles=_styles("fighter-fighting-style-great-weapon-fighting"))
    assert g["notes"] == ["two-handed", "heavy", "Great Weapon Fighting: reroll 1s and 2s"]
    v = attack(items, "longsword", _mods(STR=3), styles=_styles("fighting-style-great-weapon-fighting"))
    assert "Great Weapon Fighting: reroll 1s and 2s" in v["notes"]
    plain = attack(items, "greatsword", _mods(STR=3))
    assert plain["notes"] == ["two-handed", "heavy"]


def test_net_has_no_damage(items):
    # ranged, no finesse -> DEX +2; martial-proficient +2 -> +4
    a = attack(items, "net", _mods(STR=3, DEX=2))
    assert a["damage"] is None and a["damageType"] is None
    assert a["attackBonus"] == 4 and a["range"] == "5/15"


def test_non_weapons_are_not_attacks(items):
    assert attacks_mod.weapon_attack(items["chain-mail"], _mods(), 2, set(), _styles()) is None
    assert attacks_mod.weapon_attack(items["shield"], _mods(), 2, set(), _styles()) is None


def test_reach_loading_ammunition_notes(items):
    a = attack(items, "crossbow-hand", _mods(DEX=2), profs={"martial-weapons"})
    assert a["notes"] == ["ammunition", "loading"] and a["offhandDamage"] is None
    # hand crossbow is Light but Ranged: no off-hand damage
    w = attack(items, "whip", _mods(STR=0, DEX=2))
    assert w["notes"] == ["reach"] and w["ability"] == "DEX"


def test_attacks_from_gear_dedupes_by_index_in_first_seen_order(items):
    gear = [items["dagger"], items["shield"], items["longsword"], items["dagger"]]
    out = attacks_mod.attacks_from_gear(gear, _mods(STR=3, DEX=2), 2, SIMPLE_MARTIAL, _styles())
    assert [a["itemId"] for a in out] == ["dagger", "longsword"]


# ---- proficiency ids -------------------------------------------------------


def test_weapon_proficiency_id_overrides_and_plurals():
    f = reference_data.weapon_proficiency_id
    assert f("crossbow-light") == "crossbows-light"
    assert f("crossbow-hand") == "hand-crossbows"
    assert f("crossbow-heavy") == "crossbows-heavy"
    assert f("longsword") == "longswords"
    assert f("light-hammer") == "light-hammers"


def test_every_known_specific_weapon_proficiency_id_maps_to_a_real_weapon(items):
    known = reference_data.SPECIFIC_WEAPON_PROFICIENCY_IDS
    assert len(known) == 21
    produced = {reference_data.weapon_proficiency_id(i) for i, v in items.items() if v.get("weapon_category")}
    assert known <= produced, sorted(known - produced)
