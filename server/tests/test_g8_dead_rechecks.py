"""G8: the two re-checks `resolve()` repeated after `normalize_draft` are gone.

`resolve()` starts with `normalize_draft(draft)`, which coerces every class level and ability score to an int (a value it
cannot coerce becomes 1 / 10 with `level-invalid-whole` / `ability-invalid-<AB>` "isn't a valid whole number"). Two checks
further down (`level-invalid-number`: "Level ... isn't a valid number; using 1 instead", `ability-invalid-number`: "... score
... isn't a valid number; using 10 instead") could therefore never fire. The range checks (`level-out-of-range`,
`ability-out-of-range*`) are NOT dead (normalize does not clamp a level, and the final score adds bonuses) and stay.

This file proves: normalize coerces first (a value matrix), resolve never emits the removed keys for that matrix, the keys
are in no code and no catalog, resolve.py has no other caller of the removed checks, and the live ones still work."""
import ast
import pathlib

import pytest

from catalog.loader import load
from engine.normalize import normalize_draft
from engine.resolve import resolve
from i18n.catalog import MESSAGES

REMOVED = ("level-invalid-number", "ability-invalid-number")
SERVER = pathlib.Path(__file__).resolve().parent.parent

@pytest.fixture(scope="module")
def catalog():
    return load()


LEVELS = ["many", "", None, True, [3], {"a": 1}, 2.5, "2.5", 0, 21, -4, 3.0, "4", 5]
SCORES = ["lots", "", None, True, [3], {"a": 1}, 15.5, "12", 0, 99, -1, 12.0, 8]


def _draft(level=3, **abilities):
    base = {"STR": 10, "DEX": 14, "CON": 12, "INT": 12, "WIS": 12, "CHA": 8}
    base.update(abilities)
    return {"ruleset": "2014", "sources": [], "abilities": {"method": "manual", "base": base},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": "fighter", "level": level, "choices": {}}]}


def _keys(res):
    return [p["message"].key for p in res["problems"]]


@pytest.mark.parametrize("raw", LEVELS, ids=repr)
def test_normalize_hands_resolve_an_int_level(raw):
    clean, problems = normalize_draft(_draft(level=raw))
    assert type(clean["classes"][0]["level"]) is int
    bad = [p for p in problems if p["id"] == "level-unsupported"]
    assert all(p["message"].key == "level-invalid-whole" for p in bad)  # the only level problem normalize makes
    assert bool(bad) == (raw in ("many", "", "2.5", None, [3], 2.5) or raw is True or raw == {"a": 1})


@pytest.mark.parametrize("raw", LEVELS, ids=repr)
def test_resolve_never_emits_the_removed_level_message(catalog, raw):
    res = resolve(_draft(level=raw), catalog)
    assert "level-invalid-number" not in _keys(res)
    assert set(_keys(res)) >= ({"level-invalid-whole"} if raw in ("many", "", None, True, [3], {"a": 1}, 2.5, "2.5") else set())
    assert set(_keys(res)) >= ({"level-out-of-range"} if raw in (0, 21, -4) else set())


@pytest.mark.parametrize("raw", SCORES, ids=repr)
def test_normalize_hands_resolve_an_int_score(raw):
    clean, problems = normalize_draft(_draft(STR=raw))
    assert type(clean["abilities"]["base"]["STR"]) is int
    assert all(p["message"].key in ("ability-invalid-whole", "ability-out-of-range-clamped")
               for p in problems if p["id"].endswith("-STR"))


@pytest.mark.parametrize("raw", SCORES, ids=repr)
def test_resolve_never_emits_the_removed_ability_message(catalog, raw):
    res = resolve(_draft(STR=raw), catalog)
    assert "ability-invalid-number" not in _keys(res)
    invalid = [p for p in res["problems"] if p["id"] == "ability-invalid-STR"]
    assert all(p["message"].key == "ability-invalid-whole" for p in invalid)
    assert isinstance(res["sheet"]["abilities"]["STR"], int)


def test_a_missing_level_or_score_still_defaults(catalog):
    d = _draft()
    del d["classes"][0]["level"]
    del d["abilities"]["base"]["WIS"]
    res = resolve(d, catalog)
    assert res["sheet"]["classes"][0]["level"] == 1 and res["sheet"]["abilities"]["WIS"] == 11  # 10 + Human's +1
    assert not [k for k in _keys(res) if "invalid" in k]


def test_the_live_checks_keep_working(catalog):
    res = resolve(_draft(level="many", STR="lots"), catalog)
    by_id = {p["id"]: p["message"].key for p in res["problems"]}
    assert by_id["level-unsupported"] == "level-invalid-whole" and by_id["ability-invalid-STR"] == "ability-invalid-whole"
    assert res["sheet"]["classes"][0]["level"] == 1 and res["sheet"]["abilities"]["STR"] == 11
    res = resolve(_draft(level=25), catalog)
    assert "level-out-of-range" in _keys(res) and res["sheet"]["classes"][0]["level"] == 1


def test_the_removed_keys_are_in_no_code_and_no_catalog():
    for key in REMOVED:
        assert key not in MESSAGES, key
    for path in list((SERVER / "engine").glob("*.py")) + [SERVER / "service.py", SERVER / "app.py"]:
        text = path.read_text(encoding="utf-8")
        for key in REMOVED:
            assert key not in text, (path.name, key)
    from i18n.review_sheet import MESSAGE_SAMPLES
    assert not set(REMOVED) & set(MESSAGE_SAMPLES)


def test_only_the_normalize_and_range_sites_emit_these_ids():
    """The remaining emitters of the two problem ids (AST scan of the engine): normalize (whole-number) and the level range."""
    emitters = {}
    for path in (SERVER / "engine").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Dict):
                keys = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
                idv, m = keys.get("id"), keys.get("message")
                text = ast.unparse(idv) if idv is not None else ""
                if ("level-unsupported" in text or "ability-invalid" in text) and isinstance(m, ast.Call):
                    emitters.setdefault(path.name, []).append(m.args[0].value)
    assert {k: sorted(v) for k, v in emitters.items()} == {
        "normalize.py": ["ability-invalid-whole", "level-invalid-whole"], "resolve.py": ["level-out-of-range"]}
