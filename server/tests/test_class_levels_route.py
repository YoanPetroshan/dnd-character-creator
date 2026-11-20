"""GET /api/catalog/class/<id>/levels: every class feature by level, for the Class page's "next levels" list."""
from __future__ import annotations

import pytest

from app import app
from catalog.official_source import has_official


@pytest.fixture
def client():
    return app.test_client()


def _rows(client, class_id, ruleset):
    r = client.get(f"/api/catalog/class/{class_id}/levels?ruleset={ruleset}")
    assert r.status_code == 200
    return r.get_json()["levelFeatures"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_the_levels_come_in_order_with_a_text_id_and_no_asi_rows(client):
    for ruleset in ("2014", "2024"):
        rows = _rows(client, "fighter", ruleset)
        assert rows, ruleset
        assert [r["level"] for r in rows] == sorted(r["level"] for r in rows)
        assert all(r["name"] and r["ref"] for r in rows)
        assert not any(r["name"].startswith("Ability Score Improvement") for r in rows)
    assert ("Action Surge" in [r["name"] for r in _rows(client, "fighter", "2024")])


def test_an_unknown_class_is_a_404(client):
    assert client.get("/api/catalog/class/nope/levels").status_code == 404
