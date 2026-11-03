"""B4 deployment guards: WSGI callable, thread-safety of the shared catalog, start scripts, opt-in waitress run."""
import hashlib
import json
import os
import pathlib
import socket
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

import app as app_module
from app import DIST, app
from catalog.loader import load
from test_resolve_fuzz import gen_draft

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def test_app_is_wsgi_callable_and_serves_index(tmp_path):
    (tmp_path / "index.html").write_text("<html>SPA</html>")
    app.config["FRONTEND_DIST"] = tmp_path
    try:
        assert callable(app) and callable(app.wsgi_app)
        captured = {}

        def start_response(status, headers, exc_info=None):
            captured["status"] = status

        body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/", "SERVER_NAME": "x", "SERVER_PORT": "80",
                             "wsgi.url_scheme": "http", "wsgi.input": __import__("io").BytesIO(),
                             "wsgi.errors": __import__("sys").stderr}, start_response))
        assert captured["status"].startswith("200") and b"SPA" in body
    finally:
        app.config["FRONTEND_DIST"] = DIST


def _catalog_hash(cat) -> str:
    # _row_index style lazy caches are not part of the check if present
    state = {k: v for k, v in vars(cat).items() if not k.startswith("_row_index")}
    return hashlib.sha256(json.dumps(state, default=str, sort_keys=True).encode()).hexdigest()


def test_concurrent_resolves_do_not_mutate_shared_catalog():
    cat = app_module._catalog
    # warm lazy caches once so the before/after comparison sees a stable shape
    app.test_client().post("/api/resolve", json=gen_draft(0, cat))
    before = _catalog_hash(cat)

    drafts = [gen_draft(1000 + i, load()) for i in range(20)]

    def run(d):
        return app.test_client().post("/api/resolve", json=d).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(run, drafts))
    assert statuses == [200] * 20
    assert _catalog_hash(cat) == before


@pytest.mark.parametrize("name", ["start.sh", "setup.sh"])
def test_scripts_are_valid_bash_and_executable(name):
    path = SCRIPTS / name
    assert os.access(path, os.X_OK)
    subprocess.run(["bash", "-n", str(path)], check=True)


def test_start_script_never_sets_flask_debug():
    text = (SCRIPTS / "start.sh").read_text()
    assert "FLASK_DEBUG" not in text and "waitress-serve" in text


@pytest.mark.skipif(os.environ.get("RUN_WAITRESS_TEST") != "1", reason="opt-in: RUN_WAITRESS_TEST=1")
def test_waitress_serves_through_start_script(tmp_path):
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        pytest.skip("frontend not built")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = {**os.environ, "HOST": "127.0.0.1", "PORT": str(port)}
    proc = subprocess.Popen([str(SCRIPTS / "start.sh")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(base + "/api/health", timeout=1).read()
                break
            except OSError:
                assert proc.poll() is None, "server exited early"
                time.sleep(0.3)
        else:
            pytest.fail("server did not come up")
        assert b"<div" in urllib.request.urlopen(base + "/", timeout=5).read()
        req = urllib.request.Request(base + "/api/resolve", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            assert r.status == 200 and isinstance(json.loads(r.read()), dict)
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
