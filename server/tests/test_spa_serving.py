import pytest

from app import DIST, app


@pytest.fixture
def client(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>SPA</html>")
    (tmp_path / "assets" / "a.js").write_text("console.log('a')")
    app.config["FRONTEND_DIST"] = tmp_path
    yield app.test_client()
    app.config["FRONTEND_DIST"] = DIST


def test_root_serves_index(client):
    r = client.get("/")
    assert r.status_code == 200 and b"SPA" in r.data


def test_deep_link_falls_back_to_index(client):
    r = client.get("/class")
    assert r.status_code == 200 and b"SPA" in r.data


def test_static_asset_served(client):
    r = client.get("/assets/a.js")
    assert r.status_code == 200 and b"console.log" in r.data


def test_api_routes_unaffected(client):
    assert client.get("/api/health").get_json() == {"ok": True}
    assert client.post("/api/resolve", json={}).status_code == 200


def test_unknown_api_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json() == {"error": "not found"}


def test_missing_build_is_json_404(tmp_path):
    app.config["FRONTEND_DIST"] = tmp_path
    try:
        r = app.test_client().get("/")
        assert r.status_code == 404 and r.get_json()["error"] == "frontend not built"
    finally:
        app.config["FRONTEND_DIST"] = DIST
