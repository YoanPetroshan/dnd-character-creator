from engine import derived


def test_ability_modifier_standard_table():
    assert derived.ability_modifier(10) == 0
    assert derived.ability_modifier(11) == 0
    assert derived.ability_modifier(16) == 3
    assert derived.ability_modifier(8) == -1
    assert derived.ability_modifier(20) == 5
    assert derived.ability_modifier(1) == -5


def test_ability_modifiers_maps_every_ability_defaulting_to_ten():
    mods = derived.ability_modifiers({"STR": 16, "DEX": 14})
    assert mods == {"STR": 3, "DEX": 2, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}


def test_hit_point_max_is_hit_die_plus_con_modifier_at_level_one():
    assert derived.hit_point_max(10, 2) == 12
    assert derived.hit_point_max(6, -1) == 5
    assert derived.hit_point_max(None, 2) == 0


def test_saving_throws_adds_prof_bonus_only_for_proficient_abilities():
    modifiers = {"STR": 3, "DEX": 2, "CON": 1, "INT": 0, "WIS": -1, "CHA": 0}
    saves = derived.saving_throws(modifiers, ["STR", "CON"], 2)
    assert saves == {"STR": 5, "DEX": 2, "CON": 3, "INT": 0, "WIS": -1, "CHA": 0}


def test_skill_scores_adds_prof_bonus_only_for_proficient_skills():
    modifiers = {"STR": 3, "DEX": 2, "CON": 1, "INT": 0, "WIS": -1, "CHA": 0}
    skills = derived.skill_scores(modifiers, ["skill-athletics", "skill-perception"], 2)
    assert skills["skill-athletics"] == 5  # STR 3 + prof 2
    assert skills["skill-perception"] == 1  # WIS -1 + prof 2
    assert skills["skill-stealth"] == 2  # DEX 2, not proficient
    assert len(skills) == 18


def test_passive_perception_is_ten_plus_perception_skill():
    skills = {"skill-perception": 3}
    assert derived.passive_perception(skills) == 13


def test_passive_perception_defaults_to_ten_when_perception_missing():
    assert derived.passive_perception({}) == 10


def test_hit_point_gain_per_level_fixed_mode_uses_average_rounded_up():
    # d10 average: 10//2 + 1 = 6, plus CON mod
    assert derived.hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="fixed", level=2, hp_rolls={}) == 8
    # d6 average: 6//2 + 1 = 4
    assert derived.hit_point_gain_per_level(hit_die=6, con_modifier=0, hp_type="fixed", level=3, hp_rolls={}) == 4
    # d12 average: 12//2 + 1 = 7
    assert derived.hit_point_gain_per_level(hit_die=12, con_modifier=-1, hp_type="fixed", level=5, hp_rolls={}) == 6


def test_hit_point_gain_per_level_manual_mode_uses_the_roll():
    assert derived.hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=2, hp_rolls={"2": 7}) == 9


def test_hit_point_gain_per_level_manual_mode_falls_back_to_average_when_roll_missing():
    assert derived.hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=2, hp_rolls={}) == 8
    assert derived.hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=3, hp_rolls={"2": 7}) == 8  # roll exists for a DIFFERENT level


def test_hit_point_gain_per_level_manual_mode_rejects_an_out_of_range_roll():
    # a roll of 0 or > hit_die is invalid input — fall back to average rather than trust it
    assert derived.hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": 0}) == 6
    assert derived.hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": 99}) == 6
    assert derived.hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": "not a number"}) == 6


def test_hit_point_max_at_level_1_matches_the_existing_level_1_function_exactly():
    assert derived.hit_point_max_at_level(hit_die=10, con_modifier=2, level=1, hp_type="fixed", hp_rolls={}) == derived.hit_point_max(10, 2)
    assert derived.hit_point_max_at_level(hit_die=10, con_modifier=2, level=1, hp_type="manual", hp_rolls={}) == derived.hit_point_max(10, 2)


def test_hit_point_max_at_level_sums_level_1_plus_every_subsequent_gain():
    # d10, CON +2, fixed mode: level 1 = 10+2=12; levels 2-5 each add 6+2=8 -> 12 + 4*8 = 44
    assert derived.hit_point_max_at_level(hit_die=10, con_modifier=2, level=5, hp_type="fixed", hp_rolls={}) == 44


def test_hit_point_max_at_level_none_hit_die_is_zero():
    assert derived.hit_point_max_at_level(hit_die=None, con_modifier=2, level=5, hp_type="fixed", hp_rolls={}) == 0


def test_hit_point_gain_per_level_never_goes_below_one():
    # RAW: minimum 1 HP gained per level, always. A very-low-CON character
    # (CON mod -4) with a d6 hit die would otherwise produce a
    # non-positive gain: d6 average 6//2+1=4, 4 + -4 = 0 (or worse for an
    # unlucky manual roll of 1).
    assert derived.hit_point_gain_per_level(hit_die=6, con_modifier=-4, hp_type="fixed", level=2, hp_rolls={}) == 1
    assert derived.hit_point_gain_per_level(hit_die=6, con_modifier=-4, hp_type="manual", level=2, hp_rolls={"2": 1}) == 1


def test_hit_point_max_multiclass_single_class_matches_hit_point_max_at_level():
    # A single-entry list must produce EXACTLY what hit_point_max_at_level
    # already produces — this is the regression-safety anchor: multiclass
    # HP for one class is not a new formula, it's the existing one.
    entries = [{"hit_die": 10, "level": 5, "hp_rolls": {}}]
    result = derived.hit_point_max_multiclass(entries, con_modifier=2, hp_type="fixed")
    expected = derived.hit_point_max_at_level(10, con_modifier=2, level=5, hp_type="fixed", hp_rolls={})
    assert result == expected


def test_hit_point_max_multiclass_only_first_class_level_1_gets_the_max():
    # Fighter (d10) taken first at level 1, then Wizard (d6) multiclassed
    # in at level 1 — Wizard's OWN level 1 must NOT take d6's max (6),
    # it must use the fixed/average method like any level above 1.
    entries = [
        {"hit_die": 10, "level": 1, "hp_rolls": {}},
        {"hit_die": 6, "level": 1, "hp_rolls": {}},
    ]
    result = derived.hit_point_max_multiclass(entries, con_modifier=1, hp_type="fixed")
    # Fighter L1: 10 (max) + 1 (con) = 11
    # Wizard's own "L1" (its first level, but NOT the character's first
    # level overall): average (6//2+1=4) + 1 (con) = 5
    assert result == 11 + 5


def test_hit_point_max_multiclass_sums_every_class_correctly():
    # Fighter 3 (d10) / Wizard 2 (d6), fixed mode.
    entries = [
        {"hit_die": 10, "level": 3, "hp_rolls": {}},
        {"hit_die": 6, "level": 2, "hp_rolls": {}},
    ]
    result = derived.hit_point_max_multiclass(entries, con_modifier=2, hp_type="fixed")
    # Fighter: L1 max (10+2=12) + L2 avg (6+2=8) + L3 avg (6+2=8) = 28
    # Wizard: "L1" avg (4+2=6) + "L2" avg (4+2=6) = 12
    assert result == 28 + 12


def test_hit_point_max_multiclass_manual_mode_uses_per_class_rolls():
    entries = [
        {"hit_die": 10, "level": 2, "hp_rolls": {"2": 7}},
        {"hit_die": 8, "level": 2, "hp_rolls": {"2": 5}},
    ]
    result = derived.hit_point_max_multiclass(entries, con_modifier=1, hp_type="manual")
    # Fighter: L1 max (10+1=11) + L2 roll (7+1=8) = 19
    # Rogue-shaped d8 secondary: "L1" avg (8//2+1=5, +1 con=6) + "L2" roll (5+1=6) = 12
    assert result == 19 + 12


def test_hit_point_max_multiclass_empty_list_is_zero():
    assert derived.hit_point_max_multiclass([], con_modifier=0, hp_type="fixed") == 0


# ---- Slice 9b: carrying capacity (STR x 15, size multiplier) ---------------


def test_carrying_capacity_by_size():
    assert derived.carrying_capacity(15, "Medium") == 225
    assert derived.carrying_capacity(15, "Small") == 225
    assert derived.carrying_capacity(16, "Large") == 480  # 16 x 15 x 2
    assert derived.carrying_capacity(16, "Tiny") == 120  # 16 x 15 x 0.5
    assert derived.carrying_capacity(7, "Tiny") == 52.5
    assert derived.carrying_capacity(10, "Gargantuan") == 1200  # PHB p.176: Huge x4, Gargantuan x8 (VF2.3; an unknown size is Medium)
    assert derived.carrying_capacity(10, "Colossal") == 150
    assert derived.carrying_capacity(30, "Medium") == 450


def test_equipment_weight_sums_quantity_times_weight():
    items = {"chain-mail": {"weight": 55}, "longsword": {"weight": 3}, "dart": {"weight": 0.25}, "sling": {"weight": None}}
    entries = [
        {"itemId": "chain-mail", "qty": 1}, {"itemId": "longsword", "qty": 1},
        {"itemId": "dart", "qty": 10}, {"itemId": "sling", "qty": 3}, {"itemId": "ghost", "qty": 9},
    ]
    assert derived.equipment_weight(entries, items) == 60.5
    assert derived.equipment_weight([], items) == 0
    assert derived.equipment_weight([{"itemId": "dart", "qty": 3}], items) == 0.75
    assert derived.equipment_weight([{"itemId": "dart", "qty": "x"}], items) == 0  # junk quantity ignored


def test_carrying_capacity_block():
    items = {"anvil": {"weight": 100}}
    out = derived.carrying_summary(15, "Medium", [{"itemId": "anvil", "qty": 2}], items)
    assert out == {"capacity": 225, "pushDragLift": 450, "carried": 200, "overCapacity": False}
    assert derived.carrying_summary(15, "Medium", [{"itemId": "anvil", "qty": 3}], items)["overCapacity"] is True
