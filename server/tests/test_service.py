"""O0: ``service.handle`` is the framework-free API. It must answer exactly what the Flask adapter answers
(status, content type, headers, body bytes) for every request of ``service_requests.REQUESTS``, must not import
Flask, and engine + catalog + service must import with the standard library, pyyaml and fpdf2 only.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
import urllib.parse

import pytest

import service
from app import app
from service_requests import REQUESTS, exportable_draft
from test_service_baseline import normalise_pdf, send

SERVER = pathlib.Path(__file__).resolve().parent.parent
# GET /api (no trailing slash) is the SPA's catch-all in Flask, not an API path
NOT_API = {"api-root"}


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def call(method, url, body, ctype):
    """The adapter's job done by hand: split the url, hand the body over only when it is JSON."""
    parts = urllib.parse.urlsplit(url)
    sent = body if (body is not None and ctype is not None and "json" in ctype) else None
    return service.handle(method, urllib.parse.unquote(parts.path), parts.query, sent)


def norm(content_type, data):
    return normalise_pdf(data) if content_type == "application/pdf" else data


@pytest.mark.parametrize("name,method,url,body,ctype", [pytest.param(*r, id=r[0]) for r in REQUESTS if r[0] not in NOT_API])
def test_service_equals_flask(client, name, method, url, body, ctype):
    flask = send(client, method, url, body, ctype)
    status, content_type, headers, data = call(method, url, body, ctype)
    assert status == flask.status_code
    assert content_type == flask.headers["Content-Type"]
    assert headers.get("Content-Disposition") == flask.headers.get("Content-Disposition")
    # nothing but Content-Type / Content-Disposition is on the wire, besides what the adapter adds (Content-Length,
    # flask-cors' Access-Control-* / Vary)
    adapter = {"Content-Length", "Vary"}
    assert {h for h in flask.headers.keys() if h not in adapter and not h.startswith("Access-Control-")} == {"Content-Type", *headers}
    assert norm(content_type, data) == norm(content_type, flask.data)
    assert isinstance(data, bytes)


def test_request_list_covers_every_route_and_error_case():
    assert len(REQUESTS) >= 120
    statuses = {call(m, u, b, c)[0] for _, m, u, b, c in REQUESTS}
    assert {200, 400, 404, 405} <= statuses
    urls = " ".join(u for _, _, u, _, _ in REQUESTS)
    for rule, _, _ in service.ROUTES:
        assert rule.split("<")[0] in urls, rule


def test_every_flask_api_rule_comes_from_the_service_table():
    flask_rules = {r.rule for r in app.url_map.iter_rules() if r.rule.startswith("/api/")}
    assert flask_rules == {rule for rule, _, _ in service.ROUTES}
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            table = {r: set(m) for r, m, _ in service.ROUTES}[rule.rule]
            assert rule.methods - {"HEAD", "OPTIONS"} == table


# --- error handling -------------------------------------------------------------------------------------------------

def test_unhandled_exception_is_the_json_500_like_flask(client, monkeypatch):
    def boom(draft, catalog):
        raise RuntimeError("boom")

    monkeypatch.setattr("service.resolve", boom)
    for url in ("/api/resolve", "/api/export/yaml"):
        flask = client.post(url, json={})
        status, content_type, headers, data = service.handle("POST", url, None, b"{}")
        assert (status, content_type, headers, data) == (500, "application/json", {}, flask.data) and flask.status_code == 500
    assert data == ('{"error":"' + service.SERVER_ERROR + '"}\n').encode()


def test_exception_in_a_get_route_is_the_json_500(monkeypatch):
    monkeypatch.setattr(service, "_catalog_sources", lambda: 1 / 0)
    assert service.handle("GET", "/api/catalog")[0] == 500


def test_body_callable_is_lazy_and_only_called_by_the_draft_routes():
    def never():
        raise AssertionError("read")

    assert service.handle("GET", "/api/health", None, never)[0] == 200
    assert service.handle("POST", "/api/resolve", "lang=fr", never)[0] == 400  # lang is checked before the body
    assert service.handle("POST", "/api/export/docx", None, never)[0] == 404
    assert service.handle("POST", "/api/export/yaml", "lang=fr", never)[0] == 400
    assert service.handle("POST", "/api/resolve", None, lambda: b"{}")[0] == 200


def test_body_read_error_is_not_a_500():
    def cannot():
        raise service.BodyReadError

    with pytest.raises(service.BodyReadError):
        service.handle("POST", "/api/resolve", None, cannot)


# --- inputs ---------------------------------------------------------------------------------------------------------

def test_query_forms_are_equivalent():
    base = service.handle("GET", "/api/spells", "class=wizard&level=1&q=fire")
    assert base[0] == 200 and base[3]
    assert service.handle("GET", "/api/spells", "?class=wizard&level=1&q=fire") == base
    assert service.handle("GET", "/api/spells", b"class=wizard&level=1&q=fire") == base
    assert service.handle("GET", "/api/spells", {"class": "wizard", "level": "1", "q": "fire"}) == base
    assert service.handle("GET", "/api/spells", {"class": ["wizard", "cleric"], "level": 1, "q": "fire"}) == base
    assert service.handle("GET", "/api/spells", "class=wizard&class=cleric&level=1&q=fire") == base
    assert service.handle("GET", "/api/spells", "class=wizard&level=1&q=%66ire") == base


def test_body_forms_are_equivalent():
    draft = exportable_draft()
    import json
    raw = json.dumps(draft)
    a = service.handle("POST", "/api/resolve", None, raw)
    assert service.handle("POST", "/api/resolve", None, raw.encode()) == a
    assert service.handle("POST", "/api/resolve", None, bytearray(raw.encode())) == a
    assert service.handle("POST", "/api/resolve", None, lambda: raw) == a


def test_method_is_case_insensitive_and_head_is_get():
    assert service.handle("get", "/api/health") == service.handle("GET", "/api/health") == service.handle("HEAD", "/api/health")
    assert service.handle("post", "/api/resolve", None, b"{}")[0] == 200


def test_non_api_paths_are_not_the_services():
    for path in ("/", "/class", "/assets/a.js", "api/health", ""):
        assert service.handle("GET", path)[0] == 404


def test_json_is_flask_style():
    status, ctype, headers, data = service.handle("GET", "/api/items", "q=zzzzzz")
    assert (status, ctype, headers, data) == (200, "application/json", {}, b'{"items":[]}\n')
    # ensure_ascii and sort_keys
    status, _, _, data = service.handle("GET", "/api/catalog/class/%D0%BA")
    assert data == b'{"error":"not found"}\n'
    out = service._json({"b": "\u0416", "a": [1, {"d": 1, "c": 2}]})
    assert out[3] == b'{"a":[1,{"c":2,"d":1}],"b":"\\u0416"}\n'


def test_pretty_json_flag_matches_flask_debug(monkeypatch):
    monkeypatch.setattr(service, "pretty_json", True)
    assert service._json({"b": 1, "a": [1]})[3] == b'{\n  "a": [\n    1\n  ],\n  "b": 1\n}\n'


# --- no Flask in the service ----------------------------------------------------------------------------------------

def _imported_roots(path: pathlib.Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            roots.add((node.module or "").split(".")[0])
    return roots


def test_service_source_imports_no_framework():
    roots = _imported_roots(SERVER / "service.py")
    assert not roots & {"flask", "flask_cors", "werkzeug", "waitress", "jinja2", "pypdf", "pytest", "app"}
    third_party = roots - set(sys.stdlib_module_names) - {"catalog", "engine", "export", "export_labels", "i18n", "markdown_export", "pdf_export"}
    assert third_party == set(), third_party


_PROBE = r"""
import sys
BLOCKED = ("flask", "flask_cors", "werkzeug", "jinja2", "itsdangerous", "click", "blinker", "waitress", "pypdf", "pytest", "markupsafe")
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError("blocked: " + name)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
import service
for method, path, body in (("GET", "/api/health", None), ("POST", "/api/resolve", b"{}"), ("GET", "/api/spells/fireball", None),
                           ("POST", "/api/export/pdf", None), ("GET", "/api/nope", None)):
    status = service.handle(method, path, None, body)[0]
    print(method, path, status)
loaded = sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED)
assert not loaded, loaded
"""


def test_engine_catalog_service_import_without_flask_or_pypdf():
    done = subprocess.run([sys.executable, "-c", _PROBE, str(SERVER)], capture_output=True, text=True, timeout=300, cwd=str(SERVER))
    assert done.returncode == 0, done.stderr[-2000:]
    assert "GET /api/health 200" in done.stdout and "POST /api/resolve 200" in done.stdout
    assert "POST /api/export/pdf 400" in done.stdout  # the gate: the whole export path ran without Flask


_NO_PDF_STACK_PROBE = r"""
import json, sys
BLOCKED = ("fpdf", "PIL", "fontTools", "defusedxml", "pypdf")
class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError("blocked: " + name)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[1] + "/tests")
import service
from service_requests import exportable_draft
body = json.dumps(exportable_draft()).encode()
checks = [
    ("GET", "/api/health", None, 200), ("GET", "/api/catalog", None, 200), ("GET", "/api/catalog/class/wizard", None, 200),
    ("GET", "/api/items", None, 200), ("GET", "/api/spells?class=wizard", None, 200), ("GET", "/api/spells/fireball", None, 200),
    ("POST", "/api/resolve", body, 200), ("POST", "/api/export/yaml", body, 200), ("POST", "/api/export/markdown", body, 200),
    ("POST", "/api/export/markdown?lang=en", body, 200),
    ("POST", "/api/export/pdf", b"{}", 400),   # the export gate answers before any PDF is rendered
    ("GET", "/api/nope", None, 404),
]
for method, url, data, want in checks:
    path, _, query = url.partition("?")
    status = service.handle(method, path, query, data)[0]
    assert status == want, (method, url, status)
loaded = sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED)
assert not loaded, loaded
# a real PDF render is the one thing that needs the stack: with it blocked it is the JSON 500, not a crash
assert service.handle("POST", "/api/export/pdf", "", body)[0] == 500
print("ok")
"""


def test_everything_but_a_pdf_works_without_the_pdf_stack():
    """O3: fpdf2, Pillow, fonttools and defusedxml are imported only when a PDF is rendered (the browser worker loads
    them lazily); pypdf (the fillable sheet's form step, SHEET-S1) joins the blocked list. With the five blocked, every
    other route answers, and a PDF render fails as the JSON 500."""
    done = subprocess.run([sys.executable, "-c", _NO_PDF_STACK_PROBE, str(SERVER)], capture_output=True, text=True, timeout=300, cwd=str(SERVER))
    assert done.returncode == 0, done.stdout[-1000:] + done.stderr[-2000:]
    assert done.stdout.strip().endswith("ok")


def test_service_does_not_import_the_pdf_stack_at_module_level():
    tree = ast.parse((SERVER / "service.py").read_text(encoding="utf-8"))
    top = {(n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
           for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert "pdf_export" not in top and not top & {"fpdf", "PIL", "fontTools", "defusedxml", "pypdf"}


_OLD_PDF_NEVER_LOADS_PYPDF = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[1] + "/tests")
import service
from service_requests import exportable_draft
body = json.dumps(exportable_draft()).encode()
status, ctype, _headers, data = service.handle("POST", "/api/export/pdf", "", body)
assert status == 200 and ctype == "application/pdf" and data[:5] == b"%PDF-", (status, ctype)
assert "fpdf" in sys.modules  # the PDF stack really was loaded for the render
assert "pypdf" not in sys.modules, "the simple PDF route must not load pypdf"
print("ok")
"""


def test_the_old_pdf_route_never_loads_pypdf():
    """SHEET-S1: pypdf is the fillable sheet's form step only; the existing simple PDF (frozen baselines) renders
    without importing it (in the browser the worker would then not need the wheel for that route)."""
    done = subprocess.run([sys.executable, "-c", _OLD_PDF_NEVER_LOADS_PYPDF, str(SERVER)], capture_output=True, text=True, timeout=300, cwd=str(SERVER))
    assert done.returncode == 0, done.stdout[-1000:] + done.stderr[-2000:]
    assert done.stdout.strip().endswith("ok")
