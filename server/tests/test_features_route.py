"""GET /api/features/<id> and /api/subclasses/<id> (?lang=), the `features` overlay kind and its tool (tmp overlays only)."""
from __future__ import annotations

import json

import pytest

import service
from i18n.content import store, tool

needs_official = pytest.mark.skipif("berserker-xphb-3-frenzy" not in service._catalog.features, reason="needs the official data")


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


def write(overlay_dir, kind, data):
    (overlay_dir / "bg" / f"{kind}.json").write_text(json.dumps(data), encoding="utf-8")
    store.load_overlay.cache_clear()


def test_srd_feature_shape_and_errors():
    status, body = get("/api/features/rage")
    assert status == 200
    assert set(body) == {"id", "name", "level", "className", "subclassName", "source", "desc", "textLang"}
    assert (body["id"], body["name"], body["level"], body["className"], body["source"], body["textLang"]) == ("rage", "Rage", 1, "Barbarian", "SRD", "en")
    assert body["subclassName"] is None and body["desc"]
    assert get("/api/features/no-such-feature")[0] == 404
    assert get("/api/features/rage", "lang=de")[0] == 400
    assert get("/api/features/trait:dwarf:no-such-trait")[0] == 404
    assert get("/api/features/trait:nobody:darkvision")[0] == 404
    assert get("/api/features/background:no-such-bg")[0] == 404


@needs_official
def test_subclass_feature_names_its_subclass():
    body = get("/api/features/berserker-xphb-3-frenzy")[1]
    assert (body["className"], body["subclassName"], body["source"], body["level"]) == ("Barbarian", "Path of the Berserker", "XPHB", 3)


def test_background_feature():
    body = get("/api/features/background:acolyte")[1]
    assert body["name"] == "Shelter of the Faithful" and body["desc"] and body["level"] is None


def test_feature_overlay_applies_only_while_fresh(overlay_dir):
    english = get("/api/features/rage")[1]["desc"]
    write(overlay_dir, "features", {"rage": {"hash": store.source_hash("features", {"desc": english}), "desc": ["Ярост."]}})
    assert get("/api/features/rage", "lang=bg")[1]["desc"] == ["Ярост."]
    assert get("/api/features/rage", "lang=bg")[1]["textLang"] == "bg"
    assert get("/api/features/rage")[1]["desc"] == english
    write(overlay_dir, "features", {"rage": {"hash": "stale", "desc": ["Ярост."]}})
    assert get("/api/features/rage", "lang=bg")[1]["textLang"] == "en"


def test_trait_ref_uses_the_species_overlay(overlay_dir):
    race = service._catalog.races["dwarf"]
    payload = service._species_payload("dwarf", race)
    details = payload["traitDetails"]
    pos = next(i for i, d in enumerate(details) if d["name"] == "Darkvision")
    english = get("/api/features/trait:dwarf:darkvision")[1]
    assert english["desc"] == details[pos]["desc"] and english["textLang"] == "en" and english["level"] is None
    write(overlay_dir, "species", {"dwarf": {
        "hash": store.source_hash("species", store.species_fields(payload)), "fluff": payload["fluff"],
        "traits": [{"desc": [f"БГ {i}"]} for i in range(len(details))]}})
    # the species entry carries the same paragraph count only when each trait has one paragraph; the route does not care
    bg = get("/api/features/trait:dwarf:darkvision", "lang=bg")[1]
    assert bg["desc"] == [f"БГ {pos}"] and bg["textLang"] == "bg"


def test_subclass_route_order_and_overlay(overlay_dir):
    status, body = get("/api/subclasses/champion")
    assert status == 200
    assert set(body) == {"id", "name", "source", "ruleset", "desc", "features", "textLang"}
    assert body["name"] == "Champion" and body["source"] == "SRD" and body["ruleset"] == "2014" and body["desc"]
    levels = [f["level"] for f in body["features"]]
    assert levels == sorted(levels) and body["features"][0]["id"] == "improved-critical"
    assert set(body["features"][0]) == {"id", "name", "level", "desc"}
    assert body["textLang"] == "en"
    first = body["features"][0]
    write(overlay_dir, "features", {first["id"]: {"hash": store.source_hash("features", {"desc": first["desc"]}), "desc": ["Подобрен критичен."]}})
    bg = get("/api/subclasses/champion", "lang=bg")[1]
    assert bg["features"][0]["desc"] == ["Подобрен критичен."] and bg["features"][1]["desc"] == body["features"][1]["desc"]
    assert bg["textLang"] == "en"  # the intro and the other features are still English
    assert get("/api/subclasses/no-such-subclass")[0] == 404
    assert get("/api/subclasses/champion", "lang=de")[0] == 400


@needs_official
def test_xphb_subclass_has_no_intro_text():
    body = get("/api/subclasses/berserker-xphb")[1]
    assert body["desc"] == [] and body["ruleset"] == "2024"
    assert [f["level"] for f in body["features"]][:2] == [3, 3]


def test_tool_records_filters_and_validation():
    records = tool.load_records("features")
    assert records["rage"]["source"] == "SRD" and isinstance(records["rage"]["desc"], list)
    assert all(r["desc"] for r in records.values())
    out = tool.export_records(records, {}, kind="features", class_id="barbarian", source="SRD")
    assert out and all(r["source"] == "SRD" for r in out) and {r["id"] for r in out} >= {"rage"}
    english = {"desc": ["Gain 2d6 HP.", "Twice."]}
    rec = {"id": "f", "hash": store.source_hash("features", english), "desc": ["Получаваш 2d6 ПЖ.", "Два пъти."]}
    assert tool.validate(english, rec, "features") == []
    assert tool.validate(english, {**rec, "desc": ["Получаваш 2d6 ПЖ."]}, "features")
    assert tool.validate(english, {**rec, "desc": ["Получаваш ПЖ.", "Два пъти."]}, "features")


def test_seed_copies_matching_choice_texts():
    records = {"a": {"name": "A", "source": "SRD", "desc": ["One.", "Two 3."]}, "b": {"name": "B", "source": "SRD", "desc": ["Other."]},
               "c": {"name": "C", "source": "SRD", "desc": ["Same."]}}
    texts = {store.text_hash("One. Two 3."): {"en": "One. Two 3.", "bg": "Едно. Две 3."}, store.text_hash("Same."): {"en": "Same.", "bg": ""}}
    merged = tool.seed_features(records, {}, texts)
    assert merged == {"a": {"hash": store.source_hash("features", {"desc": ["One.", "Two 3."]}), "desc": ["Едно. Две 3."]}}
    assert tool.seed_features(records, merged, texts) == merged
