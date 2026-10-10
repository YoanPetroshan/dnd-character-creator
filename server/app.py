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
from catalog.reference_data import SOURCE_NAMES, ruleset_allows, subclass_unlock_level
from engine.resolve import _source_allowed, _spell_visible, _subclass_visible, resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

app = Flask(__name__, static_folder=None)
DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"
app.config["FRONTEND_DIST"] = DIST
# A character draft is a few KB; 1 MB is generous and stops multi-MB junk bodies.
app.config["MAX_CONTENT_LENGTH"] = 1_000_000
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


def _catalog_sources() -> list[dict]:
    """Every book with at least one species, subspecies, background, feat or
    subclass in the UNFILTERED catalog (so toggling a book off never makes it vanish
    from the picker), with that record count. SRD content has no source and
    is always available, so it is not listed."""
    counts: dict[str, int] = {}
    for coll in (_catalog.races, _catalog.subraces, _catalog.backgrounds, _catalog.feats, _catalog.subclasses):
        for record in coll.values():
            src = record.get("source") or ""
            if src and src.upper() != "SRD":
                counts[src] = counts.get(src, 0) + 1
    return [
        {"id": src, "name": SOURCE_NAMES.get(src, src), "count": n}
        for src, n in sorted(counts.items(), key=lambda kv: SOURCE_NAMES.get(kv[0], kv[0]).lower())
    ]


@app.route("/api/catalog")
def api_catalog():
    """`?ruleset=2014|2024|mixed&sources=phb,xge` hides records the draft
    could not pick under that ruleset / source list. Both are visibility
    filters only (resolve() decides what is valid)."""
    ruleset = request.args.get("ruleset", "mixed")
    sources = [s for s in (request.args.get("sources") or "").split(",") if s]

    def visible(record: dict, kind: str) -> bool:
        return _source_allowed(record, sources) and ruleset_allows(record, kind, ruleset)

    backgrounds = [
        {"id": b["index"], "name": b["name"], "source": b.get("source", ""), "ruleset": b.get("ruleset", "2014")}
        for b in _catalog.backgrounds.values() if visible(b, "background")
    ]
    # Ruleset 2024 hides 2014 backgrounds, and the 2024 ones all live in books
    # the Sources filter may exclude ("Only SRD", phb+xge+tce): the picker would
    # be empty. Fall back to the source-allowed 2014 backgrounds (the SRD one);
    # resolve() already warns that a 2014 background grants no 2024 ASI/feat.
    backgrounds_fallback = False
    if not backgrounds and ruleset == "2024":
        backgrounds = [
            {"id": b["index"], "name": b["name"], "source": b.get("source", ""), "ruleset": b.get("ruleset", "2014")}
            for b in _catalog.backgrounds.values()
            if _source_allowed(b, sources) and not b.get("source")
        ]
        backgrounds_fallback = bool(backgrounds)

    return jsonify({
        "classes": [{"id": c["index"], "name": c["name"], "hitDie": c["hit_die"]} for c in _catalog.classes.values()],
        "backgrounds": backgrounds,
        "backgroundsFallback": backgrounds_fallback,
        "species": [
            {
                "id": r["index"], "name": r["name"], "source": r.get("source", ""), "ruleset": r.get("ruleset", "2014"),
                "subspecies": [
                    {"id": s["index"], "name": s["name"], "source": s.get("source", ""), "ruleset": s.get("ruleset", "2014")}
                    for s in _catalog.subraces_of(r["index"]) if visible(s, "species")
                ],
            }
            for r in _catalog.races.values() if visible(r, "species")
        ],
        "sources": _catalog_sources(),
    })


@app.route("/api/catalog/class/<class_id>")
def api_catalog_class(class_id: str):
    """The SRD class plus `subclasses`: the class's subclasses visible under
    `?ruleset=&sources=` as {index, name, source, ruleset}, SRD first, then by
    name. `?include=<subclassId>` adds the draft's current selection with
    `hidden: true` when the filters would hide it (or it is not in the list)."""
    cls = _catalog.classes.get(class_id)
    if not cls:
        return jsonify({"error": "not found"}), 404
    ruleset = request.args.get("ruleset", "mixed")
    cls_2024 = _catalog.classes_2024.get(class_id) if ruleset == "2024" else None  # C9a
    if cls_2024:
        cls = cls_2024
    sources = [s for s in (request.args.get("sources") or "").split(",") if s]
    include = request.args.get("include") or ""
    level_feature_counts = {}
    xphb_levels = _catalog.class_2024_level_features.get(class_id) if cls_2024 else None
    for lvl in range(1, 21):
        if xphb_levels:
            level_feature_counts[str(lvl)] = len(xphb_levels.get(lvl, []))
            continue
        row = _catalog.class_level_row(class_id, lvl)
        level_feature_counts[str(lvl)] = len(row.get("features", [])) if row else 0
    chosen = [s for s in _catalog.subclasses.values() if s.get("class", {}).get("index") == class_id]
    rows = []
    for sub in chosen:
        visible = _subclass_visible(_catalog, sub, sources, ruleset)
        if visible or sub["index"] == include:
            row = {"index": sub["index"], "name": sub["name"],
                   "source": sub.get("source", "SRD"), "ruleset": sub.get("ruleset", "2014")}
            if not visible:
                row["hidden"] = True
            rows.append(row)
    rows.sort(key=lambda r: (r["source"] != "SRD", r["name"].lower()))
    return jsonify({
        **cls,
        "subclasses": rows,
        "levelFeatureCounts": level_feature_counts,
        "subclassUnlockLevel": subclass_unlock_level(class_id, ruleset),
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
    ruleset = request.args.get("ruleset", "mixed")
    sources = [s for s in (request.args.get("sources") or "").split(",") if s]
    results = []
    for item in _catalog.items.values():
        item_category = item.get("equipment_category", {}).get("index")
        if category and item_category != category:
            continue
        if query and query not in item["name"].lower():
            continue
        if not (_source_allowed(item, sources) and ruleset_allows(item, "item", ruleset)):
            continue
        results.append({"id": item["index"], "name": item["name"], "category": item_category,
                        "source": item.get("source", "SRD"), "ruleset": item.get("ruleset", "2014")})
    return jsonify({"items": results})


def _spell_list_item(spell: dict) -> dict:
    """The slim list row; the description, material text and class names live
    in GET /api/spells/<id> (a wizard list with descriptions was 233 KB)."""
    return {
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
        "source": spell.get("source", "SRD"),
        "ruleset": spell.get("ruleset", "2014"),
    }


def _build_spell_indexes() -> tuple[dict[str, list[dict]], dict[str, dict]]:
    """Built once at import: class id -> spells of that class sorted by name
    (the "" key holds every spell), and spell id -> its pre-built list row."""
    items = {sid: _spell_list_item(spell) for sid, spell in _catalog.spells.items()}
    by_class: dict[str, list[dict]] = {"": []}
    for spell in sorted(_catalog.spells.values(), key=lambda sp: sp["name"]):
        by_class[""].append(spell)
        for cls in spell.get("classes", []):
            by_class.setdefault(cls["index"], []).append(spell)
    return by_class, items


_spells_by_class, _spell_items = _build_spell_indexes()


@app.route("/api/spells")
def api_spells():
    """`?class=&level=&q=` plus `?ruleset=2014|2024|mixed&sources=phb,xge`
    (the draft's, default mixed and every book): the spells the draft could
    pick, one record per spell (see resolve._spell_visible)."""
    class_id = request.args.get("class") or ""
    level_param = request.args.get("level")
    query = (request.args.get("q") or "").lower()
    ruleset = request.args.get("ruleset", "mixed")
    sources = [s for s in (request.args.get("sources") or "").split(",") if s]
    level_filter = None
    if level_param:
        try:
            level_filter = int(level_param)
        except ValueError:
            return jsonify({"error": "'level' must be an integer"}), 400
    results = []
    for spell in _spells_by_class.get(class_id, ()):
        if level_filter is not None and spell["level"] != level_filter:
            continue
        if query and query not in spell["name"].lower():
            continue
        if not _spell_visible(_catalog, spell, sources, ruleset):
            continue
        results.append(_spell_items[spell["index"]])
    return jsonify({"spells": results})


@app.route("/api/spells/<spell_id>")
def api_spell_detail(spell_id: str):
    sid = _catalog.resolve_spell_id(spell_id)
    if sid is None:
        return jsonify({"error": "not found"}), 404
    spell = _catalog.spells[sid]
    source = spell.get("source", "SRD")
    return jsonify({
        **_spell_items[sid],
        "material": spell.get("material"),
        "desc": spell.get("desc", []),
        "higherLevel": spell.get("higher_level", []),
        "castingCondition": spell.get("casting_condition"),
        "classes": [{"id": c["index"], "name": c["name"]} for c in spell.get("classes", [])],
        "sourceName": SOURCE_NAMES.get(source, source),
    })


def _pending_export_problems(resolution: dict) -> list[dict]:
    sheet = resolution.get("sheet") or {}
    missing = [
        {"id": pid, "message": msg}
        for pid, msg, present in (
            ("export-missing-class", "Choose a class first.", sheet.get("classes")),
            ("export-missing-species", "Choose a species first.", sheet.get("species")),
            ("export-missing-background", "Choose a background first.", sheet.get("background")),
        )
        if not present
    ]
    return missing + [
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
