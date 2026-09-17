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
