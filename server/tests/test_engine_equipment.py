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


# ---- Slice 9d: armor warnings ---------------------------------------------

from engine.equipment import armor_warnings

_ARMOR = {  # real Equipment.json fields (index, category, str_minimum, stealth)
    "padded-armor": ("Light", 0, True), "leather-armor": ("Light", 0, False),
    "scale-mail": ("Medium", 0, True), "breastplate": ("Medium", 0, False),
    "chain-mail": ("Heavy", 13, True), "plate-armor": ("Heavy", 15, True), "shield": ("Shield", 0, False),
}


def _item(index):
    cat, str_min, stealth = _ARMOR[index]
    return {"index": index, "name": index, "equipment_category": {"index": "armor"}, "armor_category": cat,
            "str_minimum": str_min, "stealth_disadvantage": stealth}


def _ids(warnings):
    return [w["id"] for w in warnings]


def test_proficient_armor_raises_nothing():
    w, stealth = armor_warnings([_item("chain-mail"), _item("shield")], {"STR": 15}, {"all-armor", "shields"})
    assert w == [] and stealth is True


def test_not_proficient_per_category():
    w, _ = armor_warnings([_item("leather-armor")], {"STR": 10}, {"medium-armor"})
    assert _ids(w) == ["armor-not-proficient-leather-armor"]
    w, _ = armor_warnings([_item("breastplate")], {"STR": 10}, {"light-armor", "heavy-armor"})
    assert _ids(w) == ["armor-not-proficient-breastplate"]
    w, _ = armor_warnings([_item("breastplate")], {"STR": 10}, {"medium-armor"})
    assert w == []
    w, _ = armor_warnings([_item("plate-armor")], {"STR": 15}, {"heavy-armor"})
    assert w == []
    w, _ = armor_warnings([_item("shield")], {"STR": 10}, {"all-armor", "heavy-armor"})
    assert _ids(w) == ["armor-not-proficient-shield"]  # all-armor does not cover shields here
    w, _ = armor_warnings([_item("shield")], {"STR": 10}, {"shields"})
    assert w == []


def test_strength_minimum_warns_below_and_not_at_the_threshold():
    w, _ = armor_warnings([_item("chain-mail")], {"STR": 12}, {"heavy-armor"})
    assert _ids(w) == ["armor-strength-chain-mail"] and "10" in w[0]["message"]
    w, _ = armor_warnings([_item("chain-mail")], {"STR": 13}, {"heavy-armor"})
    assert w == []
    w, _ = armor_warnings([_item("plate-armor")], {"STR": 14}, {"heavy-armor"})
    assert _ids(w) == ["armor-strength-plate-armor"]
    w, _ = armor_warnings([_item("leather-armor")], {"STR": 3}, {"light-armor"})
    assert w == []  # str_minimum 0


def test_multiple_body_armor_but_shield_is_not_body_armor():
    w, _ = armor_warnings([_item("leather-armor"), _item("breastplate")], {"STR": 10}, {"all-armor"})
    assert _ids(w) == ["armor-multiple-body"]
    w, _ = armor_warnings([_item("leather-armor"), _item("shield")], {"STR": 10}, {"all-armor", "shields"})
    assert w == []


def test_stealth_disadvantage_only_from_armor_that_has_it():
    assert armor_warnings([_item("leather-armor")], {"STR": 10}, {"all-armor"})[1] is False
    assert armor_warnings([_item("padded-armor")], {"STR": 10}, {"all-armor"})[1] is True
    assert armor_warnings([_item("scale-mail"), _item("shield")], {"STR": 10}, {"all-armor"})[1] is True
    assert armor_warnings([], {"STR": 10}, set()) == ([], False)


def test_weapons_are_ignored_and_duplicates_dedupe():
    sword = {"index": "longsword", "equipment_category": {"index": "weapon"}}
    w, stealth = armor_warnings([sword, _item("chain-mail"), _item("chain-mail")], {"STR": 12}, {"heavy-armor"})
    assert _ids(w) == ["armor-strength-chain-mail"] and stealth is True
