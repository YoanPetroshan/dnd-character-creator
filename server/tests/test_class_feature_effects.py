"""Slice 2 (derived-stat bugs): class-feature effects on AC, speed, HP,
ability scores, skills, initiative and passives. Every expected number is
hand-computed from the 5e rules, not from the code under test."""
import pytest

from catalog.loader import load
from engine import derived as derived_mod
from engine import equipment as equipment_mod
from engine.resolve import resolve

_SKIP_OFFICIAL = None


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, base, equipment=None, background="acolyte"):
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": background, "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **base}},
        "equipment": equipment or {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _worn(*item_ids):
    return {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in item_ids], "skipped": False}


def _cls(cid, level, subclass=None, choices=None):
    e = {"classId": cid, "level": level, "choices": choices or {}}
    if subclass:
        e["subclassId"] = subclass
    return e


# ---- pure unit tests -------------------------------------------------------

BARB = {"base": 10, "abilities": ["DEX", "CON"], "allows_shield": True}
MONK = {"base": 10, "abilities": ["DEX", "WIS"], "allows_shield": False}
DRAC = {"base": 13, "abilities": ["DEX"], "allows_shield": True}
MODS = {"STR": 0, "DEX": 3, "CON": 2, "INT": 0, "WIS": 1, "CHA": 0}
SHIELD = {"equipment_category": {"index": "armor"}, "armor_category": "Shield", "armor_class": {"base": 2}}
CHAIN = {"equipment_category": {"index": "armor"}, "armor_category": "Heavy", "armor_class": {"base": 16, "dex_bonus": False}}
LEATHER = {"equipment_category": {"index": "armor"}, "armor_category": "Light", "armor_class": {"base": 11, "dex_bonus": True}}


def test_formula_unit_barbarian_uses_con_and_allows_shield():
    assert equipment_mod.armor_class_from_gear([], 3, [BARB], MODS) == 15  # 10+3+2
    assert equipment_mod.armor_class_from_gear([SHIELD], 3, [BARB], MODS) == 17


def test_formula_unit_monk_loses_formula_with_shield():
    assert equipment_mod.armor_class_from_gear([], 3, [MONK], MODS) == 14  # 10+3+1
    assert equipment_mod.armor_class_from_gear([SHIELD], 3, [MONK], MODS) == 15  # plain 10+3+2


def test_formula_unit_takes_max_never_stacks():
    assert equipment_mod.armor_class_from_gear([], 3, [BARB, MONK], MODS) == 15
    assert equipment_mod.armor_class_from_gear([SHIELD], 3, [BARB, MONK], MODS) == 17
    assert equipment_mod.armor_class_from_gear([], 3, [BARB, DRAC], MODS) == 16  # 13+3 beats 15


def test_formula_unit_not_applied_with_body_armor():
    assert equipment_mod.armor_class_from_gear([CHAIN], 3, [BARB, MONK, DRAC], MODS) == 16
    assert equipment_mod.armor_class_from_gear([LEATHER], 3, [BARB], MODS) == 14  # 11+3


def test_armored_bonus_only_with_body_armor():
    assert equipment_mod.armor_class_from_gear([CHAIN], 3, armored_bonus=1) == 17
    assert equipment_mod.armor_class_from_gear([CHAIN, SHIELD], 3, armored_bonus=1) == 19
    assert equipment_mod.armor_class_from_gear([SHIELD], 3, armored_bonus=1) == 15  # shield is not armor
    assert equipment_mod.armor_class_from_gear([], 3, armored_bonus=1) == 13


def test_old_call_shape_still_works():
    assert equipment_mod.armor_class_from_gear([LEATHER, SHIELD], 3) == 16


def test_skill_scores_expertise_doubles_proficiency_only_when_proficient():
    mods = {"STR": 3, "DEX": 2, "CON": 0, "INT": 0, "WIS": 1, "CHA": 0}
    s = derived_mod.skill_scores(mods, ["skill-athletics", "skill-stealth"], 3, expertise_skills=["skill-athletics", "skill-arcana"])
    assert s["skill-athletics"] == 3 + 6
    assert s["skill-stealth"] == 2 + 3
    assert s["skill-arcana"] == 0  # expertise without proficiency does nothing


def test_skill_scores_jack_and_remarkable_athlete():
    mods = {"STR": 1, "DEX": 2, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}
    jack = derived_mod.skill_scores(mods, ["skill-athletics"], 3, jack_of_all_trades=True)
    assert jack["skill-athletics"] == 1 + 3  # proficient: full bonus, no half
    assert jack["skill-stealth"] == 2 + 1  # floor(3/2)
    assert jack["skill-arcana"] == 0 + 1
    rem = derived_mod.skill_scores(mods, [], 3, remarkable_athlete=True)
    assert rem["skill-stealth"] == 2 + 2  # ceil(3/2), DEX check
    assert rem["skill-athletics"] == 1 + 2
    assert rem["skill-arcana"] == 0  # not STR/DEX/CON
    both = derived_mod.skill_scores(mods, [], 3, jack_of_all_trades=True, remarkable_athlete=True)
    assert both["skill-stealth"] == 4 and both["skill-arcana"] == 1  # max of the two, never stacked


def test_initiative_unit():
    mods = {"STR": 0, "DEX": 2, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}
    assert derived_mod.initiative(mods, 3) == 2
    assert derived_mod.initiative(mods, 3, jack_of_all_trades=True) == 3
    assert derived_mod.initiative(mods, 3, remarkable_athlete=True) == 4


# ---- resolve() tests -------------------------------------------------------

def test_barbarian_unarmored_defense(catalog):
    # base DEX19 CON16 + Human +1 -> DEX20 (+5), CON17 (+3)
    r = resolve(_draft([_cls("barbarian", 19)], {"DEX": 19, "CON": 16}), catalog)
    assert r["sheet"]["abilities"]["DEX"] == 20 and r["sheet"]["abilities"]["CON"] == 17
    assert r["derived"]["armorClass"] == 10 + 5 + 3
    # shield allowed with Unarmored Defense
    r = resolve(_draft([_cls("barbarian", 19)], {"DEX": 19, "CON": 16}, _worn("shield")), catalog)
    assert r["derived"]["armorClass"] == 18 + 2
    # body armor switches the formula off: chain mail 16, no DEX
    r = resolve(_draft([_cls("barbarian", 19)], {"DEX": 19, "CON": 16}, _worn("chain-mail")), catalog)
    assert r["derived"]["armorClass"] == 16


def test_barbarian_level_one_gets_unarmored_defense(catalog):
    # DEX 14+1 -> +2, CON 14+1 -> +2: 10+2+2
    r = resolve(_draft([_cls("barbarian", 1)], {"DEX": 14, "CON": 14}), catalog)
    assert r["derived"]["armorClass"] == 14


def test_monk_unarmored_defense_and_movement(catalog):
    # base DEX16 WIS15 + 1 -> 17 (+3), 16 (+3)
    base = {"DEX": 16, "WIS": 15}
    r = resolve(_draft([_cls("monk", 5)], base), catalog)
    assert r["derived"]["armorClass"] == 10 + 3 + 3
    assert r["derived"]["speed"] == 30 + 10
    # shield: no Unarmored Defense (10+3+2) and no Unarmored Movement
    r = resolve(_draft([_cls("monk", 5)], base, _worn("shield")), catalog)
    assert r["derived"]["armorClass"] == 15
    assert r["derived"]["speed"] == 30
    # light armor: 11+3, no movement bonus
    r = resolve(_draft([_cls("monk", 5)], base, _worn("leather-armor")), catalog)
    assert r["derived"]["armorClass"] == 14
    assert r["derived"]["speed"] == 30


@pytest.mark.parametrize("level,bonus", [(1, 0), (2, 10), (5, 10), (6, 15), (9, 15), (10, 20), (14, 25), (17, 25), (18, 30), (20, 30)])
def test_monk_unarmored_movement_table(catalog, level, bonus):
    r = resolve(_draft([_cls("monk", level)], {"DEX": 14, "WIS": 14}), catalog)
    assert r["derived"]["speed"] == 30 + bonus


def test_draconic_sorcerer_resilience(catalog):
    # base CON14 DEX14 + 1 -> 15 (+2). HP 6+2 + 5*(4+2) = 38, +1/level = 44. AC 13+2.
    r = resolve(_draft([_cls("sorcerer", 6, "draconic")], {"CON": 14, "DEX": 14}), catalog)
    assert r["derived"]["hitPointMax"] == 38 + 6
    assert r["derived"]["armorClass"] == 15
    # armor replaces the 13+DEX formula (leather 11+2), HP bonus stays
    r = resolve(_draft([_cls("sorcerer", 6, "draconic")], {"CON": 14, "DEX": 14}, _worn("leather-armor")), catalog)
    assert r["derived"]["armorClass"] == 13
    assert r["derived"]["hitPointMax"] == 44


def test_non_draconic_sorcerer_unchanged(catalog):
    r = resolve(_draft([_cls("sorcerer", 6)], {"CON": 14, "DEX": 14}), catalog)
    assert r["derived"]["hitPointMax"] == 38
    assert r["derived"]["armorClass"] == 12


def test_draconic_resilience_hp_counts_only_sorcerer_levels(catalog):
    # Sorcerer 2 (draconic) / Fighter 1, CON 15 (+2): sorcerer d6: 6+2, +(4+2)=14; fighter d10 avg 6+2=8 -> 22; +2 = 24
    r = resolve(_draft([_cls("sorcerer", 2, "draconic"), _cls("fighter", 1)], {"CON": 14, "CHA": 14, "STR": 14}), catalog)
    assert r["derived"]["hitPointMax"] == 22 + 2


FS = "class:fighter:1:feature:fighter-fighting-style"


def test_fighting_style_defense_adds_ac_only_when_armored(catalog):
    chain = {"choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]}, "added": [], "skipped": False}
    defense = [_cls("fighter", 1, choices={FS: ["fighter-fighting-style-defense"]})]
    dueling = [_cls("fighter", 1, choices={FS: ["fighter-fighting-style-dueling"]})]
    assert resolve(_draft(defense, {"DEX": 14}, chain), catalog)["derived"]["armorClass"] == 17
    assert resolve(_draft(dueling, {"DEX": 14}, chain), catalog)["derived"]["armorClass"] == 16
    # no armor: bonus does not apply (10 + DEX 15 -> +2)
    assert resolve(_draft(defense, {"DEX": 14}), catalog)["derived"]["armorClass"] == 12
    # shield alone is not armor
    assert resolve(_draft(defense, {"DEX": 14}, _worn("shield")), catalog)["derived"]["armorClass"] == 14


def test_paladin_defense_style(catalog):
    cid = "class:paladin:2:feature:paladin-fighting-style"
    plain = resolve(_draft([_cls("paladin", 2)], {}), catalog)["derived"]["armorClass"]
    assert plain == 16  # granted chain mail
    r = resolve(_draft([_cls("paladin", 2, choices={cid: ["fighting-style-defense"]})], {}), catalog)
    assert r["derived"]["armorClass"] == 17


def test_barbarian_monk_multiclass_takes_max_not_sum(catalog):
    # base DEX14 CON16 WIS14 + 1: DEX15(+2) CON17(+3) WIS15(+2). Barbarian 10+2+3=15, Monk 10+2+2=14.
    classes = [_cls("barbarian", 1), _cls("monk", 1)]
    base = {"STR": 14, "DEX": 14, "CON": 16, "WIS": 14}
    assert resolve(_draft(classes, base), catalog)["derived"]["armorClass"] == 15
    # shield kills the monk formula only; barbarian's survives
    assert resolve(_draft(classes, base, _worn("shield")), catalog)["derived"]["armorClass"] == 17


def test_normal_armored_characters_unchanged(catalog):
    # Fighter with chain mail, Paladin granted chain mail, Rogue-ish leather: regression on existing numbers
    chain = {"choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]}, "added": [], "skipped": False}
    assert resolve(_draft([_cls("fighter", 1)], {"DEX": 14}, chain), catalog)["derived"]["armorClass"] == 16
    assert resolve(_draft([_cls("fighter", 1)], {"DEX": 14}), catalog)["derived"]["armorClass"] == 12
    assert resolve(_draft([_cls("fighter", 1)], {"DEX": 14}, _worn("leather-armor", "shield")), catalog)["derived"]["armorClass"] == 15
    assert resolve(_draft([_cls("fighter", 1)], {"DEX": 14}), catalog)["derived"]["speed"] == 30


def test_primal_champion_raises_str_con_and_cap(catalog):
    # base STR10 CON10 + Human 1 = 11 each -> 15 each
    r = resolve(_draft([_cls("barbarian", 20)], {}), catalog)
    assert r["sheet"]["abilities"]["STR"] == 15 and r["sheet"]["abilities"]["CON"] == 15
    assert r["derived"]["abilityModifiers"]["STR"] == 2
    # base STR20 + 1 = 21 -> 25 capped at 24
    r = resolve(_draft([_cls("barbarian", 20)], {"STR": 20, "CON": 19}), catalog)
    assert r["sheet"]["abilities"]["STR"] == 24
    assert r["sheet"]["abilities"]["CON"] == 24  # 20 + 4
    # Barbarian 19 does not get it
    r = resolve(_draft([_cls("barbarian", 19)], {}), catalog)
    assert r["sheet"]["abilities"]["STR"] == 11


def test_primal_champion_feeds_unarmored_defense(catalog):
    # Barbarian 20: DEX 10+1 -> +0, CON 11+4 = 15 -> +2 : AC 12
    r = resolve(_draft([_cls("barbarian", 20)], {}), catalog)
    assert r["derived"]["armorClass"] == 10 + 0 + 2
    # HP uses the raised CON: d12 -> 12+2 + 19*(7+2) = 185
    assert r["derived"]["hitPointMax"] == 14 + 19 * 9


def test_primal_champion_requires_barbarian_level_20_not_total_level(catalog):
    r = resolve(_draft([_cls("barbarian", 10), _cls("fighter", 10)], {"STR": 14, "CON": 14}), catalog)
    assert r["sheet"]["abilities"]["STR"] == 15


def test_initiative_and_extra_passives(catalog):
    # Fighter, Acolyte (Insight, Religion). DEX 14+1 -> +2; WIS 10+1 -> 0 ... use WIS 12 -> 13 (+1); INT 10 -> 11 (+0)
    r = resolve(_draft([_cls("fighter", 1)], {"DEX": 14, "WIS": 12}), catalog)
    d = r["derived"]
    assert d["initiative"] == 2
    assert d["passiveInsight"] == 10 + 1 + 2  # Acolyte is proficient in Insight
    assert d["passiveInvestigation"] == 10
    assert d["passivePerception"] == 10 + 1


def test_bard_jack_of_all_trades(catalog):
    # Bard 2: prof +2. Human +1 everywhere: DEX 11 (+0), INT 11 (+0), WIS 11 (+0)
    r = resolve(_draft([_cls("bard", 2)], {}), catalog)
    d = r["derived"]
    assert d["skills"]["skill-stealth"] == 0 + 1  # half of 2
    assert d["skills"]["skill-insight"] == 0 + 2  # proficient (Acolyte): full, not half
    assert d["initiative"] == 0 + 1
    assert d["passiveInvestigation"] == 10 + 1
    # level 1 bard has no Jack of All Trades yet
    r = resolve(_draft([_cls("bard", 1)], {}), catalog)
    assert r["derived"]["skills"]["skill-stealth"] == 0
    assert r["derived"]["initiative"] == 0


def test_champion_remarkable_athlete(catalog):
    # Champion Fighter 7: prof +3 ; all 11 -> +0. Athletics/Acrobatics/CON-ability not proficient -> +ceil(3/2)=2
    r = resolve(_draft([_cls("fighter", 7, "champion")], {}), catalog)
    d = r["derived"]
    assert d["skills"]["skill-athletics"] == 2
    assert d["skills"]["skill-acrobatics"] == 2
    assert d["skills"]["skill-arcana"] == 0
    assert d["initiative"] == 2
    # non-champion fighter 7 gets nothing
    r = resolve(_draft([_cls("fighter", 7)], {}), catalog)
    assert r["derived"]["skills"]["skill-athletics"] == 0 and r["derived"]["initiative"] == 0


def test_expertise_reaches_derived_skills(catalog, monkeypatch):
    import engine.resolve as rmod
    monkeypatch.setattr(rmod, "_feat_expertise_skills", lambda feats: ["skill-insight", "skill-arcana"])
    # Acolyte is proficient in Insight (+2 at level 1): WIS 11 -> 0 + 2*2 = 4 ; Arcana not proficient -> 0
    r = resolve(_draft([_cls("fighter", 1)], {}), catalog)
    assert r["sheet"]["expertiseSkills"][0] == "skill-insight"
    assert r["derived"]["skills"]["skill-insight"] == 4
    assert r["derived"]["skills"]["skill-arcana"] == 0
    assert r["derived"]["passiveInsight"] == 14
