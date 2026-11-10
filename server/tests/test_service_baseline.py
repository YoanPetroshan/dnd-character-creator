"""O0 baseline: what the Flask app answered for a fixed list of requests BEFORE the routes moved into
``service.py``. ``service_baseline.json`` holds, per request, the status, the headers that matter (Content-Type,
Content-Disposition, Allow) and the sha256 + length of the body bytes (PDFs after normalising /CreationDate and
/ID, the only parts fpdf2 varies between runs). The Flask test client must keep producing exactly these.

The hashes are those of the bundled data (``DND_OFFICIAL_DATA`` unset); the test is skipped for any other data
source. Regenerate only on purpose: ``WRITE_SERVICE_BASELINE=1 pytest tests/test_service_baseline.py``.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re

import pytest

import app as app_module
from app import app
from catalog.official.paths import data_source
from service_requests import REQUESTS

BASELINE = pathlib.Path(__file__).with_name("service_baseline.json")
HEADERS = ("Content-Type", "Content-Disposition", "Allow")


def normalise_pdf(data: bytes) -> bytes:
    data = re.sub(rb"/CreationDate\s*\(D:[^)]*\)", b"/CreationDate (D:X)", data)
    # the fillable sheet (pypdf) writes its date escaped, "(D\\07220261110120000Z)", and stamps the time of the request
    data = re.sub(rb"/(CreationDate|ModDate)\s*\(D\\072[^)]*\)", rb"/\1 (D:X)", data)
    data = re.sub(rb"/ID\s*\[\s*<[0-9a-fA-F]*>\s*<[0-9a-fA-F]*>\s*\]", b"/ID [<X> <X>]", data)
    return data


def record(response) -> dict:
    body = response.data
    if response.mimetype == "application/pdf":
        body = normalise_pdf(body)
    return {
        "status": response.status_code,
        "headers": {h: response.headers[h] for h in HEADERS if h in response.headers},
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "bodyLength": len(body),
    }


def send(client, method, url, body, ctype):
    kwargs = {"method": method}
    if body is not None:
        kwargs["data"] = body
    if ctype is not None:
        kwargs["content_type"] = ctype
    return client.open(url, **kwargs)


# GET /api is answered by Flask's SPA catch-all with frontend/dist/index.html, whose bytes change with every frontend
# build (content-hashed asset names). The baseline pins the index.html of the O0 build, kept here, so a frontend change
# does not move this test: it serves that fixed file instead of the live dist.
SPA_FIXTURE = pathlib.Path(__file__).with_name("spa_dist")


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    before = app.config.get("FRONTEND_DIST")
    app.config["FRONTEND_DIST"] = str(SPA_FIXTURE)
    try:
        with app.test_client() as c:
            yield c
    finally:
        app.config["FRONTEND_DIST"] = before


def _current(client) -> dict:
    return {name: record(send(client, m, url, body, ctype)) for name, m, url, body, ctype in REQUESTS}


def test_request_names_are_unique():
    names = [r[0] for r in REQUESTS]
    assert len(names) == len(set(names)) and len(names) > 120


@pytest.mark.skipif(data_source() != "bundled", reason="the baseline hashes are those of the bundled data")
def test_flask_responses_match_the_baseline(client):
    current = _current(client)
    if os.environ.get("WRITE_SERVICE_BASELINE") == "1":
        BASELINE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert sorted(current) == sorted(baseline)
    for name in sorted(baseline):
        assert current[name] == baseline[name], name


@pytest.mark.skipif(data_source() != "bundled", reason="the baseline hashes are those of the bundled data")
def test_unhandled_exception_is_the_json_500(client, monkeypatch):
    def boom(draft, catalog):
        raise RuntimeError("boom")

    monkeypatch.setattr("service.resolve", boom)
    r = client.post("/api/resolve", json={})
    assert r.status_code == 500
    assert r.get_json() == {"error": "The server couldn't process this character. Check the draft and try again."}
    assert r.headers["Content-Type"] == "application/json"


def test_oversized_body_is_the_json_413(client):
    r = client.post("/api/resolve", json={"name": "x" * 1_200_000})
    assert r.status_code == 413 and r.headers["Content-Type"] == "application/json"
    assert isinstance(r.get_json()["error"], str)
