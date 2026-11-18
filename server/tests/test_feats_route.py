"""GET /api/feats/<id>?lang=: the feat text for the choice pickers' eye, and the `feats` overlay kind (tmp overlay only)."""
from __future__ import annotations

import json

import pytest

import service
from i18n.content import store, tool
from sheet_data import feat_prerequisite_text

needs_official = pytest.mark.skipif("tough-xphb" not in service._catalog.feats, reason="needs the official data")


def get(path, query=None):
    status, _ct, _h, body = service.handle("GET", path, query)
    return status, json.loads(body)


@pytest.fixture
def overlay_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "I18N_DIR", tmp_path)
    store.load_overlay.cache_clear()
    (tmp_path / "bg").mkdir()
    yield tmp_path
    store.load_overlay.cache_clear()


@needs_official
def test_feat_detail_shape_and_errors():
    status, body = get("/api/feats/tough-xphb")
    assert status == 200
    assert set(body) == {"id", "name", "prerequisite", "desc", "textLang"}
    assert body["id"] == "tough-xphb" and body["textLang"] == "en" and body["desc"]
    assert get("/api/feats/no-such-feat")[0] == 404
    assert get("/api/feats/tough-xphb", "lang=de")[0] == 400


@needs_official
def test_prerequisite_text():
    feats = service._catalog.feats
    assert feat_prerequisite_text(feats["athlete-xphb"], feats) == "Level 4, Strength 13; or Level 4, Dexterity 13"
    assert feat_prerequisite_text(feats["tough-xphb"], feats) == ""
    assert get("/api/feats/archery-xphb")[1]["prerequisite"] == "Fighting Style feature"


def test_overlay_applies_only_while_fresh(overlay_dir):
    english = {"id": "f", "name": "F", "prerequisite": "", "desc": ["Gain 2d6 HP.", "Twice."]}
    entry = {"hash": store.source_hash("feats", {"desc": english["desc"]}), "desc": ["Получаваш 2d6 ПЖ.", "Два пъти."]}
    (overlay_dir / "bg" / "feats.json").write_text(json.dumps({"f": entry}), encoding="utf-8")
    assert store.overlay_feats("f", english, "bg")["desc"] == entry["desc"]
    assert store.overlay_feats("f", english, "bg")["textLang"] == "bg"
    assert store.overlay_feats("f", english, "en") == {**english, "textLang": "en"}
    stale = {**english, "desc": ["changed"]}
    assert store.overlay_feats("f", stale, "bg") == {**stale, "textLang": "en"}


def test_tool_validates_feats():
    english = {"desc": ["Gain 2d6 HP.", "Twice."]}
    rec = {"id": "f", "hash": store.source_hash("feats", english), "desc": ["Получаваш 2d6 ПЖ.", "Два пъти."]}
    assert tool.validate(english, rec, "feats") == []
    assert tool.validate(english, {**rec, "desc": ["Получаваш 2d6 ПЖ."]}, "feats")
    assert tool.validate(english, {**rec, "desc": ["Получаваш ПЖ.", "Два пъти."]}, "feats")
    assert tool.export_records({"f": {"name": "F", "source": "XPHB", **english}}, {}, kind="feats")[0]["desc"] == english["desc"]
