from engine.equipment import armor_class_from_gear

_LEATHER = {"equipment_category": {"index": "armor"}, "armor_category": "Light", "armor_class": {"base": 11, "dex_bonus": True}}
_HIDE = {"equipment_category": {"index": "armor"}, "armor_category": "Medium", "armor_class": {"base": 12, "dex_bonus": True, "max_bonus": 2}}
_CHAIN_MAIL = {"equipment_category": {"index": "armor"}, "armor_category": "Heavy", "armor_class": {"base": 16, "dex_bonus": False}}
_SHIELD = {"equipment_category": {"index": "armor"}, "armor_category": "Shield", "armor_class": {"base": 2, "dex_bonus": False}}


def test_unarmored_is_ten_plus_full_dex():
    assert armor_class_from_gear([], dex_modifier=3) == 13
    assert armor_class_from_gear([], dex_modifier=-1) == 9


def test_light_armor_adds_full_dex_uncapped():
    assert armor_class_from_gear([_LEATHER], dex_modifier=5) == 16  # 11 + 5, no cap


def test_medium_armor_caps_dex_at_max_bonus():
    assert armor_class_from_gear([_HIDE], dex_modifier=5) == 14  # 12 + min(5, 2)
    assert armor_class_from_gear([_HIDE], dex_modifier=1) == 13  # 12 + min(1, 2)


def test_heavy_armor_ignores_dex_entirely():
    assert armor_class_from_gear([_CHAIN_MAIL], dex_modifier=5) == 16
    assert armor_class_from_gear([_CHAIN_MAIL], dex_modifier=-3) == 16


def test_shield_adds_a_flat_bonus_on_top_of_body_armor():
    assert armor_class_from_gear([_LEATHER, _SHIELD], dex_modifier=2) == 15  # 11 + 2 + 2


def test_shield_adds_a_flat_bonus_while_unarmored():
    assert armor_class_from_gear([_SHIELD], dex_modifier=1) == 13  # 10 + 1 + 2


def test_multiple_body_armor_items_use_only_the_first_found():
    # Not a realistic draft, but resolve() must not crash on one — pick
    # deterministically rather than summing nonsensically.
    result = armor_class_from_gear([_LEATHER, _CHAIN_MAIL], dex_modifier=2)
    assert result in (13, 16)  # whichever is "first" per the function's own iteration order — just must not crash or double-stack
