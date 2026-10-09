"""Slice 12: server-side validation of the ability-score methods."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(method, scores):
    ab = dict(zip(["STR", "DEX", "CON", "INT", "WIS", "CHA"], scores))
    return {
        "name": "t", "sources": ["srd"], "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": method, "base": ab},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _ids(items):
    return {i["id"] for i in items}


def test_point_buy_valid_27_points(catalog):
    r = resolve(_draft("pointbuy", [15, 15, 15, 8, 8, 8]), catalog)  # 9+9+9
    assert not [p for p in r["problems"] if "point-buy" in p["id"]]


def test_point_buy_under_budget_is_fine(catalog):
    r = resolve(_draft("pointbuy", [8, 8, 8, 8, 8, 8]), catalog)
    assert not [p for p in r["problems"] if "point-buy" in p["id"]]


def test_point_buy_all_fifteens_is_over_budget(catalog):
    r = resolve(_draft("pointbuy", [15] * 6), catalog)  # 54 points
    assert "point-buy-over-budget" in _ids(r["problems"])
    assert "54" in next(p for p in r["problems"] if p["id"] == "point-buy-over-budget")["message"]


def test_point_buy_scores_outside_8_to_15(catalog):
    r = resolve(_draft("pointbuy", [16, 8, 8, 8, 8, 7]), catalog)
    assert "point-buy-out-of-range" in _ids(r["problems"])


def test_point_buy_default_all_tens_ok(catalog):
    r = resolve(_draft("pointbuy", [10] * 6), catalog)  # 12 points
    assert not [p for p in r["problems"] if "point-buy" in p["id"]]


def test_standard_array_valid_permutation(catalog):
    r = resolve(_draft("standard", [8, 15, 12, 13, 14, 10]), catalog)
    assert "standard-array-mismatch" not in _ids(r["warnings"] + r["problems"])


def test_standard_array_wrong_values_is_a_blocking_problem(catalog):
    r = resolve(_draft("standard", [15] * 6), catalog)
    assert "standard-array-mismatch" in _ids(r["problems"])


def test_standard_array_untouched_default_is_not_flagged(catalog):
    r = resolve(_draft("standard", [10] * 6), catalog)
    assert "standard-array-mismatch" not in _ids(r["warnings"] + r["problems"])


def test_roll_range(catalog):
    assert "roll-out-of-range" not in _ids(resolve(_draft("roll", [18, 3, 10, 12, 9, 14]), catalog)["problems"])
    assert "roll-out-of-range" in _ids(resolve(_draft("roll", [19, 3, 10, 12, 9, 14]), catalog)["problems"])


def test_manual_is_unchecked(catalog):
    r = resolve(_draft("manual", [30, 1, 20, 3, 25, 4]), catalog)
    assert not [p for p in r["problems"] if p["id"].startswith(("point-buy", "standard", "roll"))]
