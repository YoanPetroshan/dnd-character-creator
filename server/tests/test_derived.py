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


def test_armor_class_unarmored_is_ten_plus_dex():
    assert derived.armor_class(2) == 12
    assert derived.armor_class(-1) == 9


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
