"""Thin Flask shell around the v2 catalog + resolve engine + YAML/Markdown
export. No rules logic lives here — this module only wires HTTP onto
catalog.loader / engine.resolve / export / markdown_export.
"""
from __future__ import annotations

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from catalog.loader import load as load_catalog
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

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
        # Shared by both /api/export/yaml and /api/export/markdown (Phase
        # 2f) so the two formats can never drift on what counts as
        # export-ready.
    ]


_EXPORT_RENDERERS = {
    "yaml": (to_yaml, "application/x-yaml"),
    "markdown": (to_markdown, "text/markdown"),
    "pdf": (to_pdf, "application/pdf"),
}


@app.route("/api/export/<fmt>", methods=["POST"])
def api_export(fmt: str):
    entry = _EXPORT_RENDERERS.get(fmt)
    if entry is None:
        return jsonify({"error": f"unknown export format '{fmt}'"}), 404
    renderer, mimetype = entry
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    return Response(renderer(resolution), mimetype=mimetype)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
