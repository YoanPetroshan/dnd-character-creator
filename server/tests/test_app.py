import yaml

from app import app


import pytest


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _fighter_acolyte_human_draft():
    return {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_resolve_empty_draft_is_valid_not_an_error(client):
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["choices"] == []


def test_resolve_real_draft_returns_computed_values(client):
    resp = client.post("/api/resolve", json=_fighter_acolyte_human_draft())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["sheet"]["class"]["id"] == "fighter"
    assert body["derived"]["hitPointMax"] == 12
    assert body["derived"]["armorClass"] == 12
    skill_choice = next(c for c in body["choices"] if c["label"] == "Skill Proficiencies")
    insight = next(o for o in skill_choice["options"] if o["id"] == "skill-insight")
    assert insight["disabled"] is True


def test_catalog_endpoint_lists_all_classes_backgrounds_species(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["classes"]) == 12
    assert len(body["backgrounds"]) == 1
    assert len(body["species"]) == 9
    fighter = next(c for c in body["classes"] if c["id"] == "fighter")
    assert fighter["hitDie"] == 10
    dwarf = next(s for s in body["species"] if s["id"] == "dwarf")
    assert dwarf["subspecies"] == [{"id": "hill-dwarf", "name": "Hill Dwarf"}]


def test_catalog_class_detail_endpoint(client):
    resp = client.get("/api/catalog/class/fighter")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Fighter"


def test_catalog_class_detail_endpoint_404s_for_unknown_id(client):
    resp = client.get("/api/catalog/class/not-a-class")
    assert resp.status_code == 404


def test_catalog_background_detail_endpoint(client):
    resp = client.get("/api/catalog/background/acolyte")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Acolyte"


def test_catalog_species_detail_endpoint_includes_subspecies(client):
    resp = client.get("/api/catalog/species/dwarf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Dwarf"
    assert [s["index"] for s in body["subspecies"]] == ["hill-dwarf"]


def test_export_yaml_endpoint_returns_valid_yaml(client):
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    resp = client.post("/api/export/yaml", json=draft)
    assert resp.status_code == 200
    assert resp.mimetype == "application/x-yaml"
    doc = yaml.safe_load(resp.data.decode("utf-8"))
    assert doc["name"] == "Torvin Bracewell"
    assert doc["hitPointMax"] == 12


def test_export_yaml_rejects_a_draft_with_problems(client):
    resp = client.post("/api/export/yaml", json={
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}, {"classId": "wizard", "level": 1, "choices": {}}],
    })
    assert resp.status_code == 400
    assert any(p["id"] == "multiclass-unsupported" for p in resp.get_json()["problems"])


def test_export_yaml_rejects_when_a_choice_is_still_pending(client):
    resp = client.post("/api/export/yaml", json=_fighter_acolyte_human_draft())
    # Fighting Style is never pre-selected in this fixture, so it stays pending
    assert resp.status_code == 400
    assert any("unresolved-choice" in p["id"] for p in resp.get_json()["problems"])
