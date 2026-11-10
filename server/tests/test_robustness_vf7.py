"""VF7.6 (final review S3): the service survives hostile but legal JSON.

(a) a name that is a lone surrogate (`"\\ud800"`, valid JSON) made every /api/export/* a 500 (`urllib.parse.quote` cannot encode it);
(b) a deeply nested body under the 1 MB limit (`'[' * 450000`) raised RecursionError inside `json.loads` and was reported as a 500.
Now: lone surrogates become U+FFFD before the exporters run, the download name is cut to 200 characters, and a body nested deeper
than 64 levels (a draft has about 8) is a 400 `{"error": ...}` (docs/API.md)."""
from __future__ import annotations

import json
import re
import urllib.parse

import pytest

import service
from service_requests import exportable_draft

needs_data = pytest.mark.skipif(not service._catalog.races, reason="catalog not loaded")


def _post(path: str, body, query=None):
    raw = body if isinstance(body, (bytes, str)) else json.dumps(body)
    return service.handle("POST", path, query, raw.encode("utf-8") if isinstance(raw, str) else raw)


def _disposition_name(headers) -> str:
    m = re.fullmatch(r"attachment; filename\*=UTF-8''(.+)", headers["Content-Disposition"])
    assert m
    assert m.group(1).isascii()
    return urllib.parse.unquote(m.group(1))


@pytest.mark.parametrize("fmt,ext", [("yaml", "yaml"), ("markdown", "md"), ("pdf", "pdf")])
def test_vf7_6a_lone_surrogate_name_exports(fmt, ext):
    raw = json.dumps(exportable_draft()).replace('"Torvin Bracewell"', '"\\ud800"')
    assert "\\ud800" in raw
    status, content_type, headers, body = _post(f"/api/export/{fmt}", raw)
    assert status == 200, body[:200]
    assert _disposition_name(headers) == f"�.{ext}"
    if fmt != "pdf":
        assert "�" in body.decode("utf-8")


def test_vf7_6a_surrogates_in_other_text_fields_do_not_break_the_export_either():
    draft = exportable_draft()
    draft["details"] = {"backstory": "before \udc00 after", "notes": "\ud83d"}
    status, _ct, _h, body = _post("/api/export/markdown", json.dumps(draft))  # json.dumps escapes them as \udc00
    assert status == 200 and "before � after" in body.decode("utf-8")


def test_vf7_6a_a_valid_surrogate_pair_is_kept():
    raw = json.dumps(exportable_draft()).replace('"Torvin Bracewell"', '"\\ud83d\\ude00 Hero"')
    status, _ct, headers, body = _post("/api/export/yaml", raw)
    assert status == 200 and _disposition_name(headers) == "\U0001F600 Hero.yaml"


@pytest.mark.parametrize("fmt", ["yaml", "markdown", "pdf"])
def test_vf7_6a_download_name_is_cut_to_200_characters(fmt):
    draft = exportable_draft(name="N" * 5000)
    status, _ct, headers, body = _post(f"/api/export/{fmt}", draft)
    assert status == 200
    name = _disposition_name(headers)
    assert name == "N" * 200 + "." + {"yaml": "yaml", "markdown": "md", "pdf": "pdf"}[fmt]
    assert len(headers["Content-Disposition"]) < 700
    if fmt == "markdown":
        assert body.decode("utf-8").startswith("# " + "N" * 5000)  # the sheet title keeps the whole name


def test_vf7_6a_short_names_are_unchanged():
    status, _ct, headers, _b = _post("/api/export/yaml", exportable_draft(name="a/b:c"))
    assert status == 200 and _disposition_name(headers) == "a_b_c.yaml"


@pytest.mark.parametrize("path", ["/api/resolve", "/api/export/yaml", "/api/export/markdown", "/api/export/pdf"])
def test_vf7_6b_deeply_nested_body_is_a_400(path):
    for body in (b"[" * 450000, b'{"a":' * 100000 + b"1" + b"}" * 100000, b'{"name":' + b"[" * 70 + b"]" * 70 + b"}"):
        status, content_type, headers, data = _post(path, body)
        assert status == 400 and content_type == "application/json", (path, status)
        err = json.loads(data)["error"]
        assert "nested" in err and "64" in err
        assert headers == {}


def test_vf7_6b_a_body_at_the_limit_depth_and_ordinary_drafts_still_work():
    ok = b'{"name":' + b"[" * 60 + b"]" * 60 + b"}"
    assert _post("/api/resolve", ok)[0] == 200  # 61 levels with the object, under the limit
    assert _post("/api/resolve", exportable_draft())[0] == 200
    assert _post("/api/resolve", b"not json")[0] == 200  # unparseable stays an empty draft
    assert _post("/api/resolve", b"[1,2]")[0] == 400  # a shallow non-object stays the old 400
    assert json.loads(_post("/api/resolve", b"[1,2]")[3])["error"] == "draft must be a JSON object"


def test_vf7_6b_the_depth_check_is_fast_for_a_big_flat_body():
    import time
    body = json.dumps({"name": "x", "details": {"notes": ["y" * 50] * 15000}}).encode("utf-8")
    t = time.perf_counter()
    assert _post("/api/resolve", body)[0] == 200
    assert time.perf_counter() - t < 2.0


def test_vf7_6c_body_over_the_limit_is_the_413_the_flask_server_gives():
    ok = b'{"name":"' + b"x" * 999_900 + b'"}'
    assert len(ok) <= service.MAX_BODY_BYTES and _post("/api/resolve", ok)[0] == 200
    big = b'{"name":"' + b"x" * 1_000_001 + b'"}'
    status, content_type, _h, data = _post("/api/resolve", big)
    assert status == 413 and content_type == "application/json"
    assert json.loads(data) == {"error": "The data value transmitted exceeds the capacity limit."}
    status = service.handle("POST", "/api/export/yaml", None, ("é" * 600_000))[0]  # 1.2 MB as UTF-8
    assert status == 413


@pytest.mark.parametrize("kind,status", [("too-large", 413), ("too-deep", 400)])
def test_vf7_6c_body_problem_callable_answers_only_the_two_draft_routes_after_the_lang_check(kind, status):
    problem = service.body_problem(kind)
    for path in ("/api/resolve", "/api/export/yaml"):
        got = service.handle("POST", path, None, problem)
        assert got[0] == status and got[1] == "application/json"
    assert service.handle("POST", "/api/resolve", "lang=fr", problem)[0] == 400  # the lang check comes first, as with Flask
    assert json.loads(service.handle("POST", "/api/resolve", "lang=fr", problem)[3])["error"] == "'lang' must be 'bg' or 'en'"
    assert service.handle("GET", "/api/health", None, problem)[0] == 200  # never called
    assert service.handle("POST", "/api/export/docx", None, problem)[0] == 404
    with pytest.raises(ValueError):
        service.body_problem("nope")


def test_vf7_6b_an_unparseable_body_nested_too_deeply_is_the_same_400():
    assert _post("/api/resolve", b"[" * 65)[0] == 400  # unbalanced: json.loads says "Expecting value", the raw nesting is 65
    assert _post("/api/resolve", b"[" * 64)[0] == 200  # at the limit, unparseable: still an empty draft
    assert _post("/api/resolve", b'{"a": "' + b"[" * 100 + b'" oops')[0] == 200  # brackets inside a string do not count
