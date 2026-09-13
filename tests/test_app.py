import io
import json

import pytest

from app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _human_fighter_draft():
    # ids/casing verified directly against chargen/data/srd/*.json: only
    # "acolyte" exists in the bundled SRD backgrounds (no "soldier"); race
    # id "human" and class id "fighter" are confirmed lowercase index
    # values; skill_picks values are Title Case ("Athletics", not
    # "athletics") because chargen.normalise.class_from_5ebits strips the
    # "Skill: " prefix off the raw SRD name and keeps its casing as-is.
    return {
        "name": "Torvin Bracewell", "player": "Yoan",
        "race_id": "human", "background_id": "acolyte",
        "class_id": "fighter", "level": 1,
        "ability_method": "roll",
        "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                           "INT": 10, "WIS": 12, "CHA": 8},
        "skill_picks": ["Athletics", "Intimidation"],
        "alignment": "Lawful Good",
    }


def test_index_serves_builder_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"chargen" in resp.data.lower() or b"builder" in resp.data.lower()


def test_catalog_endpoint(client):
    resp = client.get("/api/chargen/catalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "races" in body and "classes" in body and "backgrounds" in body


def test_preview_does_not_save(client, tmp_path):
    resp = client.post("/api/chargen/preview", json=_human_fighter_draft())
    assert resp.status_code == 200
    assert not (tmp_path / "characters").exists()


def test_build_with_illegal_draft_returns_400(client):
    resp = client.post("/api/chargen/build", json={"name": "Nobody"})
    assert resp.status_code == 400
    assert "problems" in resp.get_json()


def test_build_saves_all_three_formats(client, tmp_path):
    resp = client.post("/api/chargen/build", json=_human_fighter_draft())
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["ok"] is True
    assert body["name"] == "Torvin Bracewell"
    assert body["level"] == 1
    yaml_path = tmp_path / "characters" / "Torvin Bracewell" / "current.yaml"
    md_path = tmp_path / "characters" / "Torvin Bracewell" / "character.md"
    pdf_path = tmp_path / "characters" / "Torvin Bracewell" / "character.pdf"
    assert yaml_path.exists() and yaml_path.stat().st_size > 0
    assert md_path.exists() and md_path.stat().st_size > 0
    assert pdf_path.exists() and pdf_path.read_bytes()[:4] == b"%PDF"


def test_build_same_name_twice_is_refused_without_overwrite(client, tmp_path):
    draft = _human_fighter_draft()
    first = client.post("/api/chargen/build", json=draft)
    assert first.status_code == 201, first.get_json()

    yaml_path = tmp_path / "characters" / "Torvin Bracewell" / "current.yaml"
    original_yaml = yaml_path.read_text(encoding="utf-8")

    # A second build under the same name, no ?overwrite=1: refused, and the
    # first character's saved sheet must be untouched (C1 — this used to
    # silently destroy it).
    changed_draft = dict(draft)
    changed_draft["player"] = "SomeoneElse"
    second = client.post("/api/chargen/build", json=changed_draft)
    assert second.status_code == 409
    assert "already exists" in second.get_json()["error"]
    assert yaml_path.read_text(encoding="utf-8") == original_yaml

    # With ?overwrite=1, the build proceeds normally.
    third = client.post("/api/chargen/build?overwrite=1", json=changed_draft)
    assert third.status_code == 201, third.get_json()
    assert yaml_path.read_text(encoding="utf-8") != original_yaml


def test_characters_list_endpoint(client):
    client.post("/api/chargen/build", json=_human_fighter_draft())
    resp = client.get("/api/characters")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.get_json()]
    assert "Torvin Bracewell" in names


def test_spells_endpoint_filters_by_class(client):
    unfiltered = client.get("/api/chargen/spells")
    assert unfiltered.status_code == 200
    all_spells = unfiltered.get_json()["spells"]

    filtered = client.get("/api/chargen/spells?class=Wizard")
    assert filtered.status_code == 200
    wizard_spells = filtered.get_json()["spells"]

    assert len(wizard_spells) < len(all_spells)
    wizard_names = {s["name"] for s in wizard_spells}
    assert "Cure Wounds" not in wizard_names  # Cleric/Druid/Bard/Paladin/Ranger only


def test_download_endpoints(client):
    client.post("/api/chargen/build", json=_human_fighter_draft())
    for fmt, prefix in (("yaml", b"name:"), ("md", b"#"), ("pdf", b"%PDF")):
        resp = client.get(f"/api/characters/Torvin Bracewell/{fmt}")
        assert resp.status_code == 200, (fmt, resp.get_json() if resp.is_json else resp.data)
        assert resp.data.startswith(prefix) or prefix in resp.data[:200]
