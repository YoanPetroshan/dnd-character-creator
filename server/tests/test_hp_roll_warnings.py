"""Round-2 audit F11: manual HP rolls outside 1..hit die fall back to the
average (unchanged) but now say so with a warning."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, hp_type="manual"):
    return {
        "preferences": {"hitPointType": hp_type},
        "classes": classes,
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _ids(r):
    return [w["id"] for w in r["warnings"] if w["id"].startswith("hp-roll-invalid")]


def test_out_of_range_rolls_warn_and_fall_back_to_average(catalog):
    r = resolve(_draft([{"classId": "fighter", "level": 4, "choices": {}, "hpRolls": {"2": 7, "3": 0, "4": 11}}]), catalog)
    assert _ids(r) == ["hp-roll-invalid-fighter-3", "hp-roll-invalid-fighter-4"]
    assert r["derived"]["hitPointMax"] == 10 + 7 + 6 + 6  # level 1 max, roll 7, two averages (d10 -> 6)
    assert r["problems"] == []


def test_valid_and_missing_rolls_do_not_warn(catalog):
    r = resolve(_draft([{"classId": "fighter", "level": 4, "choices": {}, "hpRolls": {"2": 10}}]), catalog)
    assert _ids(r) == []


def test_fixed_mode_ignores_rolls_silently(catalog):
    r = resolve(_draft([{"classId": "fighter", "level": 3, "choices": {}, "hpRolls": {"2": 99}}], "fixed"), catalog)
    assert _ids(r) == []


def test_secondary_class_level_1_roll_is_checked_and_used(catalog):
    r = resolve(_draft([
        {"classId": "fighter", "level": 1, "choices": {}},
        {"classId": "wizard", "level": 2, "choices": {}, "hpRolls": {"1": 6, "2": 9}},
    ]), catalog)
    assert _ids(r) == ["hp-roll-invalid-wizard-2"]  # d6: 9 is invalid, 6 is fine
