"""SK9: the HTTP contract documented in docs/API.md (health versions, error shapes)."""
import json
import pathlib
import re

import pytest

import app as app_module
from app import app
from catalog.official.paths import BUNDLED_DIR

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_keys_and_versions(client):
    body = client.get("/api/health").get_json()
    assert set(body) == {"ok", "apiVersion", "draftVersion", "dataSource", "bundleSha256"}
    assert body["ok"] is True
    assert body["apiVersion"] == 1
    assert isinstance(body["draftVersion"], int)


def test_health_draft_version_matches_the_frontend(client):
    src = (ROOT / "frontend" / "src" / "logic" / "draft.ts").read_text(encoding="utf-8")
    frontend = int(re.search(r"export const DRAFT_VERSION = (\d+);", src).group(1))
    assert client.get("/api/health").get_json()["draftVersion"] == frontend == app_module.DRAFT_VERSION


def test_health_data_source_bundled(client, monkeypatch):
    monkeypatch.delenv("DND_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("DND_CAMPAIGN_ROOT", raising=False)
    body = client.get("/api/health").get_json()
    manifest = json.loads((BUNDLED_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    assert body["dataSource"] == "bundled"
    assert body["bundleSha256"] == manifest["bundle_sha256"]
    assert re.fullmatch(r"[0-9a-f]{64}", body["bundleSha256"])


def test_health_data_source_srd_only(client, monkeypatch):
    monkeypatch.setenv("DND_OFFICIAL_DATA", "none")
    body = client.get("/api/health").get_json()
    assert body["dataSource"] == "srd-only"
    assert body["bundleSha256"] is None


def test_health_data_source_explicit(client, monkeypatch, tmp_path):
    monkeypatch.setenv("DND_OFFICIAL_DATA", str(tmp_path))
    body = client.get("/api/health").get_json()
    assert body["dataSource"] == "explicit"
    assert body["bundleSha256"] is None


@pytest.mark.parametrize("payload", [[], [1, 2], "text", 5, True])
def test_non_object_body_is_a_400_with_error_string(client, payload):
    for url in ("/api/resolve", "/api/export/yaml"):
        r = client.post(url, json=payload)
        assert r.status_code == 400
        assert r.get_json() == {"error": "draft must be a JSON object"}


def test_unknown_catalog_class_is_404_error(client):
    r = client.get("/api/catalog/class/no-such-class")
    assert r.status_code == 404
    assert r.get_json() == {"error": "not found"}


def test_unknown_export_format_is_404_error(client):
    r = client.post("/api/export/docx", json={})
    assert r.status_code == 404
    assert r.get_json() == {"error": "unknown export format 'docx'"}


def test_bad_level_parameter_is_400_error(client):
    r = client.get("/api/spells?class=wizard&level=x")
    assert r.status_code == 400
    assert r.get_json() == {"error": "'level' must be an integer"}


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.get_json() == {"error": "not found"}


def test_oversized_body_is_413_error(client):
    r = client.post("/api/resolve", json={"name": "x" * 1_200_000})
    assert r.status_code == 413
    assert isinstance(r.get_json()["error"], str)


def test_export_gate_is_400_with_a_problems_list(client):
    r = client.post("/api/export/yaml", json={})
    assert r.status_code == 400
    body = r.get_json()
    assert list(body) == ["problems"]
    ids = [p["id"] for p in body["problems"]]
    assert ids[:3] == ["export-missing-class", "export-missing-species", "export-missing-background"]
    for p in body["problems"]:
        assert set(p) == {"id", "message"} and all(isinstance(v, str) for v in p.values())


def test_api_doc_mentions_every_api_route():
    doc = (ROOT / "docs" / "API.md").read_text(encoding="utf-8")
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            assert rule.rule in doc, rule.rule
