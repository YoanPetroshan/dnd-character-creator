import pytest

from app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_resolve_returns_stub_shape(client):
    resp = client.post("/api/resolve", json={"name": "Test"})
    assert resp.status_code == 200
    body = resp.get_json()
    for key in ("sheet", "choices", "derived", "problems", "warnings", "pruned"):
        assert key in body, f"missing top-level key: {key}"
    assert isinstance(body["choices"], list)
    assert len(body["choices"]) == 4
    first = body["choices"][0]
    for key in ("id", "source", "label", "description", "count", "options", "selected", "status"):
        assert key in first, f"missing Choice key: {key}"
    assert first["source"]["kind"] == "class"
    assert first["source"]["id"] == "fighter"


def test_resolve_choices_cover_every_source_kind_used_in_phase_0(client):
    resp = client.post("/api/resolve", json={})
    kinds = {c["source"]["kind"] for c in resp.get_json()["choices"]}
    assert kinds == {"class", "background", "species"}


def test_resolve_includes_one_pending_one_resolved_choice(client):
    resp = client.post("/api/resolve", json={})
    statuses = {c["status"] for c in resp.get_json()["choices"]}
    assert "pending" in statuses
    assert "resolved" in statuses


def test_resolve_accepts_empty_body(client):
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 200


def test_resolve_includes_a_disabled_option_with_a_reason(client):
    resp = client.post("/api/resolve", json={})
    body = resp.get_json()
    disabled = [
        opt
        for choice in body["choices"]
        for opt in choice["options"]
        if opt.get("disabled")
    ]
    assert len(disabled) == 1
    assert disabled[0]["disabledReason"]
