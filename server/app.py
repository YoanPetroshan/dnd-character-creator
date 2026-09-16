"""Thin Flask shell around the v2 catalog + resolve engine + YAML export.
No rules logic lives here — this module only wires HTTP onto
catalog.loader / engine.resolve / export.
"""
from __future__ import annotations

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from catalog.loader import load as load_catalog
from engine.resolve import resolve
from export import to_yaml

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

_catalog = load_catalog()


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
        "backgrounds": [{"id": b["index"], "name": b["name"]} for b in _catalog.backgrounds.values()],
        "species": [
            {
                "id": r["index"], "name": r["name"],
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
    return jsonify(cls)


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


@app.route("/api/export/yaml", methods=["POST"])
def api_export_yaml():
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    pending_problems = [
        {"id": f"unresolved-choice-{c['id']}", "message": f"'{c['label']}' isn't fully chosen yet."}
        for c in resolution["choices"] if c["status"] == "pending"
    ]
    all_problems = resolution["problems"] + pending_problems
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    return Response(to_yaml(resolution), mimetype="application/x-yaml")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
