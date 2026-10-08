"""Thin Flask shell around the v2 catalog + resolve engine + YAML/
Markdown/PDF export. No rules logic lives here — this module only wires
HTTP onto catalog.loader / engine.resolve / export / markdown_export /
pdf_export.
"""
from __future__ import annotations

import os
import pathlib
import re
import urllib.parse

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from catalog.loader import load as load_catalog
from catalog.reference_data import SUBCLASS_UNLOCK_LEVEL
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

app = Flask(__name__, static_folder=None)
DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
app.config["FRONTEND_DIST"] = DIST
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

_catalog = load_catalog()


@app.errorhandler(Exception)
def handle_unexpected(exc):
    """Every failure is JSON so the SPA can show a readable message
    instead of choking on an HTML error page."""
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return jsonify({"error": exc.description or exc.name}), exc.code
    app.logger.exception("unhandled error")
    return jsonify({"error": "The server couldn't process this character. Check the draft and try again."}), 500


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    draft = request.get_json(silent=True) or {}
    return jsonify(resolve(draft, _catalog))


@app.route("/api/catalog")
def api_catalog():
    return jsonify({
        "classes": [{"id": c["index"], "name": c["name"], "hitDie": c["hit_die"]} for c in _catalog.classes.values()],
        "backgrounds": [
            {"id": b["index"], "name": b["name"], "source": b.get("source", "")} for b in _catalog.backgrounds.values()
        ],
        "species": [
            {
                "id": r["index"], "name": r["name"], "source": r.get("source", ""),
                "subspecies": [{"id": s["index"], "name": s["name"]} for s in _catalog.subraces_of(r["index"])],
            }
            for r in _catalog.races.values()
        ],
    })


@app.route("/api/catalog/class/<class_id>")
def api_catalog_class(class_id: str):
    cls = _catalog.classes.get(class_id)
    if not cls:
        return jsonify({"error": "not found"}), 404
    level_feature_counts = {}
    for lvl in range(1, 21):
        row = _catalog.class_level_row(class_id, lvl)
        level_feature_counts[str(lvl)] = len(row.get("features", [])) if row else 0
    return jsonify({
        **cls,
        "levelFeatureCounts": level_feature_counts,
        "subclassUnlockLevel": SUBCLASS_UNLOCK_LEVEL.get(class_id),
    })


@app.route("/api/catalog/background/<background_id>")
def api_catalog_background(background_id: str):
    bg = _catalog.backgrounds.get(background_id)
    if not bg:
        return jsonify({"error": "not found"}), 404
    return jsonify(bg)


@app.route("/api/catalog/species/<species_id>")
def api_catalog_species(species_id: str):
    race = _catalog.races.get(species_id)
    if not race:
        return jsonify({"error": "not found"}), 404
    return jsonify({**race, "subspecies": _catalog.subraces_of(species_id)})


@app.route("/api/items")
def api_items():
    category = request.args.get("category")
    query = (request.args.get("q") or "").lower()
    results = []
    for item in _catalog.items.values():
        item_category = item.get("equipment_category", {}).get("index")
        if category and item_category != category:
            continue
        if query and query not in item["name"].lower():
            continue
        results.append({"id": item["index"], "name": item["name"], "category": item_category})
    return jsonify({"items": results})


@app.route("/api/spells")
def api_spells():
    class_id = request.args.get("class")
    level_param = request.args.get("level")
    query = (request.args.get("q") or "").lower()
    level_filter = None
    if level_param:
        try:
            level_filter = int(level_param)
        except ValueError:
            return jsonify({"error": "'level' must be an integer"}), 400
    results = []
    for spell in _catalog.spells.values():
        if class_id and not any(c["index"] == class_id for c in spell.get("classes", [])):
            continue
        if level_filter is not None and spell["level"] != level_filter:
            continue
        if query and query not in spell["name"].lower():
            continue
        results.append({
            "id": spell["index"],
            "name": spell["name"],
            "level": spell["level"],
            "school": spell.get("school", {}).get("name"),
            "castingTime": spell.get("casting_time"),
            "range": spell.get("range"),
            "components": spell.get("components", []),
            "duration": spell.get("duration"),
            "concentration": spell.get("concentration", False),
            "ritual": spell.get("ritual", False),
            "material": spell.get("material"),
            "desc": " ".join(spell.get("desc", [])),
        })
    results.sort(key=lambda s: s["name"])
    return jsonify({"spells": results})


def _pending_export_problems(resolution: dict) -> list[dict]:
    return [
        {"id": f"unresolved-choice-{c['id']}", "message": f"'{c['label']}' isn't fully chosen yet."}
        for c in resolution["choices"]
        if c["status"] == "pending" and c["source"]["kind"] != "equipment"
        # Equipment choices are excluded from this gate until a frontend
        # exists that can resolve them (Phase 2b) — otherwise every
        # character the currently-shipped UI builds would be permanently
        # unexportable, which is a regression this phase must not cause.
        #
        # Spell choices (source.kind == "class", added in Phase 2c) are
        # deliberately NOT carved out here, unlike equipment above: the
        # shipped Class-step UI (ChoiceCard/ChoicePicker) already renders
        # and resolves any source.kind == "class" choice generically,
        # spell choices included, so gating export on unresolved
        # cantrip/spell picks is the same correct behavior class/
        # background/species choices already get — not a lockout.
        #
        # Shared by every format behind /api/export/<fmt> (introduced in
        # Phase 2f for yaml/markdown, extended in Phase 2g to also cover
        # pdf) so no format can ever drift on what counts as export-ready.
    ]


_EXPORT_RENDERERS = {
    "yaml": (to_yaml, "application/x-yaml", "yaml"),
    "markdown": (to_markdown, "text/markdown", "md"),
    "pdf": (to_pdf, "application/pdf", "pdf"),
}


@app.route("/api/export/<fmt>", methods=["POST"])
def api_export(fmt: str):
    entry = _EXPORT_RENDERERS.get(fmt)
    if entry is None:
        return jsonify({"error": f"unknown export format '{fmt}'"}), 404
    renderer, mimetype, extension = entry
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    name = re.sub(r'[\\/:*?"<>|]', "_", str(draft.get("name") or "character"))
    filename = urllib.parse.quote(f"{name}.{extension}", safe="")
    return Response(
        renderer(resolution),
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


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


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
