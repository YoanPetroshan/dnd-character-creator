"""Slice 1: malformed-draft robustness. resolve() must never raise on any
JSON-shaped draft, silent coercions must be reported as problems, and the
Flask app must answer unexpected errors with JSON (never an HTML 500)."""
import copy

import pytest

import app as app_module
from app import app
from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _base():
    return {
        "name": "T", "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def _mut(fn):
    d = _base()
    fn(d)
    return d


MALFORMED = {
    "array": [1, 2], "string": "x", "none": None, "number": 5,
    "prefs_bool": _mut(lambda d: d.update(preferences={"usePrerequisites": True})),
    "prefs_str": _mut(lambda d: d.update(preferences="x")),
    "prefs_list": _mut(lambda d: d.update(preferences=[])),
    "prefs_hp_list": _mut(lambda d: d.update(preferences={"hitPointType": ["x"]})),
    "abilities_list": _mut(lambda d: d.update(abilities=[])),
    "base_list": _mut(lambda d: d["abilities"].update(base=[1])),
    "sources_int": _mut(lambda d: d.update(sources=5)),
    "name_list": _mut(lambda d: d.update(name=["a"])),
    "classid_list": _mut(lambda d: d["classes"][0].update(classId=["a"])),
    "subclass_list": _mut(lambda d: d["classes"][0].update(subclassId=["a"])),
    "bgid_list": _mut(lambda d: d["background"].update(id=["a"])),
    "spid_list": _mut(lambda d: d["species"].update(id=["a"])),
    "subsp_dict": _mut(lambda d: d["species"].update(subspeciesId={"a": 1})),
    "choices_list": _mut(lambda d: d["classes"][0].update(choices=[])),
    "sel_str": _mut(lambda d: d["classes"][0].update(choices={"x": "abc"})),
    "sel_nested": _mut(lambda d: d["classes"][0].update(choices={"x": [[1], {"a": 1}]})),
    "equip_list": _mut(lambda d: d.update(equipment=[])),
    "added_itemid_list": _mut(lambda d: d["equipment"].update(added=[{"itemId": ["a"]}])),
    "level_list": _mut(lambda d: d["classes"][0].update(level=[1])),
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_resolve_never_raises_on_malformed_draft(catalog, name):
    res = resolve(copy.deepcopy(MALFORMED[name]), catalog)
    assert isinstance(res["problems"], list)


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_api_resolve_malformed_is_json_not_500(client, name):
    resp = client.post("/api/resolve", json=MALFORMED[name])
    assert resp.status_code == 200
    assert "problems" in resp.get_json()


def _ids(res):
    return [p["id"] for p in res["problems"]]


def test_top_level_array_reports_problem(catalog):
    assert "malformed-draft" in _ids(resolve([1, 2], catalog))


def test_use_prerequisites_bool_reports_problem(catalog):
    res = resolve(MALFORMED["prefs_bool"], catalog)
    assert "malformed-use-prerequisites" in _ids(res)


def test_fractional_level_is_reported_not_truncated(catalog):
    res = resolve(_mut(lambda d: d["classes"][0].update(level=2.5)), catalog)
    assert "level-unsupported" in _ids(res)
    assert res["sheet"]["classes"][0]["level"] == 1


def test_integral_float_and_numeric_string_level_are_accepted(catalog):
    res = resolve(_mut(lambda d: d["classes"][0].update(level=3.0)), catalog)
    assert res["sheet"]["classes"][0]["level"] == 3
    res = resolve(_mut(lambda d: d["classes"][0].update(level="4")), catalog)
    assert res["sheet"]["classes"][0]["level"] == 4
    assert "level-unsupported" not in _ids(res)


def test_numeric_string_ability_is_accepted(catalog):
    res = resolve(_mut(lambda d: d["abilities"]["base"].update(STR="15")), catalog)
    assert "ability-invalid-STR" not in _ids(res)


@pytest.mark.parametrize("bad", [15.5, "abc", True, None, [3]])
def test_invalid_ability_value_is_reported(catalog, bad):
    res = resolve(_mut(lambda d: d["abilities"]["base"].update(STR=bad)), catalog)
    assert "ability-invalid-STR" in _ids(res)


@pytest.mark.parametrize("bad", ["x", -3, 0, 1.5, True])
def test_invalid_equipment_qty_is_reported(catalog, bad):
    d = _mut(lambda d: d["equipment"].update(added=[{"itemId": "longsword", "qty": bad}]))
    res = resolve(d, catalog)
    assert "equipment-qty-invalid" in _ids(res)
    added = res["sheet"]["equipment"]["added"]
    assert added and added[0]["qty"] == 1


def test_valid_equipment_qty_untouched(catalog):
    d = _mut(lambda d: d["equipment"].update(added=[{"itemId": "longsword", "qty": 3}]))
    res = resolve(d, catalog)
    assert "equipment-qty-invalid" not in _ids(res)
    assert res["sheet"]["equipment"]["added"][0]["qty"] == 3


def test_unexpected_exception_returns_json_error(client, monkeypatch):
    def boom(draft, catalog):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(app_module, "resolve", boom)
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 500
    assert resp.is_json
    assert "error" in resp.get_json()


def test_unknown_api_route_stays_json_404(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404 and resp.is_json


def test_export_with_malformed_draft_is_json(client):
    resp = client.post("/api/export/yaml", json=[1, 2])
    assert resp.is_json
    assert resp.status_code in (200, 400)
