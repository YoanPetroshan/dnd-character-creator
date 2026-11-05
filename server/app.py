"""Thin Flask adapter over ``service.handle`` (the framework-free API, see service.py and docs/API.md).

No rules logic and no route body lives here: this module only wires HTTP onto the service and keeps what is
Flask's job: the 1 MB request limit (413), CORS for the Vite dev server, serving the built single-page app, the
JSON error pages, the startup log line and the dev/waitress entry points.
"""
from __future__ import annotations

import os
import pathlib

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

import service
from service import (  # noqa: F401  (re-exported: tests and tools read these from `app`)
    API_VERSION,
    DRAFT_VERSION,
    _catalog,
    _pending_export_problems,
    _spell_items,
    _spells_by_class,
)

app = Flask(__name__, static_folder=None)
DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
app.config["FRONTEND_DIST"] = DIST
# A character draft is a few KB; 1 MB is generous and stops multi-MB junk bodies.
app.config["MAX_CONTENT_LENGTH"] = 1_000_000
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})
service.pretty_json = bool(app.debug)  # Flask's jsonify pretty-prints in debug mode (see also __main__)


@app.errorhandler(Exception)
def handle_unexpected(exc):
    """Every failure is JSON so the SPA can show a readable message
    instead of choking on an HTML error page. (Failures inside a route are answered by service.handle.)"""
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return jsonify({"error": exc.description or exc.name}), exc.code
    app.logger.exception("unhandled error")
    return jsonify({"error": service.SERVER_ERROR}), 500


def _read_body() -> bytes:
    try:
        return request.get_data()
    except Exception as exc:
        raise service.BodyReadError from exc


def _api_view(**_):
    """Every /api route: the service answers, Flask only carries the bytes. The body is handed over lazily and only
    when the request is JSON (Flask's get_json ignored any other body), so the 1 MB limit raises a 413 exactly
    where it always did: when a route reads the draft."""
    body = _read_body if request.is_json else None
    try:
        status, content_type, headers, data = service.handle(request.method, request.path, request.query_string, body)
    except service.BodyReadError as exc:
        raise exc.__cause__ from None  # e.g. RequestEntityTooLarge: the errorhandler answers the JSON 413
    return Response(data, status=status, headers={**headers, "Content-Type": content_type})


for _rule, _methods, _view in service.ROUTES:
    app.add_url_rule(_rule, endpoint=_view.__name__, view_func=_api_view, methods=_methods)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    """Serve the built SPA (single origin, no CORS). Registered after all
    /api routes; unknown /api/* paths stay JSON 404s."""
    if path.startswith("api/"):
        return jsonify({"error": "not found"}), 404
    dist = pathlib.Path(app.config["FRONTEND_DIST"])
    if path and (dist / path).is_file():
        return send_from_directory(dist, path)
    if (dist / "index.html").is_file():
        return send_from_directory(dist, "index.html")
    return jsonify({"error": "frontend not built"}), 404


def _log_data_source() -> None:
    """One stderr line at start: which catalog data the server will use."""
    import json
    import sys
    from catalog.official.paths import BUNDLED_DIR, data_source, official_dir

    src = data_source()
    if src == "bundled":
        try:
            sha = json.loads((BUNDLED_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["bundle_sha256"][:12]
        except (OSError, ValueError, KeyError):
            sha = "no manifest"
        print(f"catalog data: bundled ({sha})", file=sys.stderr)
    else:
        print(f"catalog data: {src} ({official_dir()})", file=sys.stderr)


if __name__ == "__main__":
    _log_data_source()
    service.pretty_json = os.environ.get("FLASK_DEBUG") == "1"
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
