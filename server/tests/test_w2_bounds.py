"""W2 (F6, F7, F8): manual ability scores clamp to 1..30 (warning above 20), class levels stay bounded
and a total over 20 is reported, a non-object JSON body is a 400. normalize stays idempotent."""
import copy

import pytest

from app import app
from catalog.loader import load
from engine.normalize import normalize_draft
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _draft(base=None, classes=None):
    return {
        "name": "T", "sources": ["srd"], "ruleset": "2014",
        "classes": classes or [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8, **(base or {})}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }


def _ids(items):
    return [p["id"] for p in items]


@pytest.mark.parametrize("raw,clamped", [(99999999999999999999, 30), (31, 30), (-5, 1), (0, 1), (30, 30), (1, 1)])
def test_base_score_is_clamped_to_1_30(raw, clamped):
    clean, problems = normalize_draft(_draft({"STR": raw}))
    assert clean["abilities"]["base"]["STR"] == clamped
    assert ("ability-out-of-range-STR" in _ids(problems)) == (raw != clamped)


def test_in_range_scores_are_untouched_and_unreported():
    clean, problems = normalize_draft(_draft({"STR": 20}))
    assert clean["abilities"]["base"]["STR"] == 20 and not problems


def test_huge_score_resolves_with_a_bounded_modifier_and_a_problem(catalog):
    r = resolve(_draft({"STR": 99999999999999999999}), catalog)
    assert "ability-out-of-range-STR" in _ids(r["problems"])
    assert r["sheet"]["abilities"]["STR"] <= 31  # clamped base 30 + the human +1
    assert _ids(r["problems"]).count("ability-out-of-range-STR") == 1


def test_non_numeric_score_is_ten_with_the_existing_invalid_problem():
    clean, problems = normalize_draft(_draft({"STR": "lots"}))
    assert clean["abilities"]["base"]["STR"] == 10 and "ability-invalid-STR" in _ids(problems)


@pytest.mark.parametrize("score,warns", [(20, False), (21, True), (30, True)])
def test_score_above_20_is_a_non_blocking_warning(catalog, score, warns):
    r = resolve(_draft({"STR": score}), catalog)
    assert ("ability-above-20-STR" in _ids(r["warnings"])) == warns
    assert "ability-above-20-STR" not in _ids(r["problems"])


def test_normalize_is_idempotent_for_out_of_range_values():
    d = _draft({"STR": 10 ** 20, "DEX": -3}, [{"classId": "fighter", "level": 999, "choices": {}}])
    once, _ = normalize_draft(copy.deepcopy(d))
    twice, problems2 = normalize_draft(copy.deepcopy(once))
    assert once == twice and not problems2


# F7: what resolve already did (and keeps doing): an invalid level is reported and the class falls back to 1.
@pytest.mark.parametrize("level", [999, 21, 0, -1, 10 ** 30])
def test_out_of_range_level_is_reported_and_bounded(catalog, level):
    r = resolve(_draft(classes=[{"classId": "fighter", "level": level, "choices": {}}]), catalog)
    assert "level-unsupported" in _ids(r["problems"])
    assert 1 <= r["sheet"]["level"] <= 20


def test_total_level_over_20_is_reported(catalog):
    r = resolve(_draft(classes=[{"classId": "fighter", "level": 15, "choices": {}}, {"classId": "wizard", "level": 10, "choices": {}}]), catalog)
    assert "total-level-exceeded" in _ids(r["problems"])


# F8
@pytest.mark.parametrize("path", ["/api/resolve", "/api/export/yaml", "/api/export/markdown", "/api/export/pdf"])
@pytest.mark.parametrize("body", [[1, 2], "x", 5, True])
def test_non_object_body_is_400(client, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 400 and r.get_json() == {"error": "draft must be a JSON object"}


def test_object_bodies_still_work(client):
    assert client.post("/api/resolve", json=_draft()).status_code == 200
    assert client.post("/api/resolve", json={}).status_code == 200
