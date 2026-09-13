"""Thin Flask shell around chargen + sheet_derive + the two export
renderers + storage. All character-mechanics logic lives in chargen;
this module only wires HTTP onto it.
"""
from __future__ import annotations

import dataclasses

from flask import Flask, jsonify, request, render_template, Response

from chargen.build import build
from chargen.catalog import Catalog
import sheet_derive
import markdown_render
import pdf_fill
import storage

app = Flask(__name__)

_CATALOG = Catalog.load()


@app.route("/")
def index():
    return render_template("builder.html")


@app.route("/api/chargen/catalog")
def api_catalog():
    # Catalog.races()/classes()/backgrounds() all return frozen dataclasses
    # (Race/CharClass/Background) — dataclasses.asdict() recurses through
    # their nested Trait/Subrace/ClassLevelRow fields too, which a plain
    # .__dict__ would not (frozen dataclasses still expose .__dict__, but
    # it only shallow-copies top-level fields, leaving nested dataclass
    # instances un-serializable by jsonify).
    return jsonify({
        "races": [dataclasses.asdict(r) for r in _CATALOG.races()],
        "classes": [dataclasses.asdict(c) for c in _CATALOG.classes()],
        "backgrounds": [dataclasses.asdict(b) for b in _CATALOG.backgrounds()],
    })


@app.route("/api/chargen/spells")
def api_spells():
    return jsonify({"spells": [dataclasses.asdict(s) for s in _CATALOG.spells()]})


@app.route("/api/chargen/equipment")
def api_equipment():
    # armor() already returns plain dicts (see chargen/catalog.py's
    # _armor_from_5ebits) — no asdict() needed there, unlike weapons/gear.
    return jsonify({
        "armor": _CATALOG.armor(),
        "weapons": [dataclasses.asdict(w) for w in _CATALOG.weapons()],
        "gear": [dataclasses.asdict(g) for g in _CATALOG.gear()],
    })


@app.route("/api/chargen/preview", methods=["POST"])
def api_preview():
    draft = request.get_json(silent=True) or {}
    sheet, problems, warnings = build(draft, _CATALOG)
    if problems:
        return jsonify({"problems": problems, "warnings": warnings}), 400
    return jsonify({"sheet": sheet, "warnings": warnings})


@app.route("/api/chargen/build", methods=["POST"])
def api_build():
    draft = request.get_json(silent=True) or {}
    sheet, problems, warnings = build(draft, _CATALOG)
    if problems:
        return jsonify({"problems": problems, "warnings": warnings}), 400

    derived = sheet_derive.derive(sheet, _CATALOG, draft)
    yaml_path = storage.save_yaml(sheet["name"], sheet)
    md_text = markdown_render.render(sheet, derived)
    md_path = storage.save_markdown(sheet["name"], md_text)
    pdf_bytes = pdf_fill.fill(sheet, derived)
    pdf_path = storage.save_pdf(sheet["name"], pdf_bytes)

    return jsonify({
        "ok": True, "warnings": warnings,
        "yaml_path": str(yaml_path), "md_path": str(md_path), "pdf_path": str(pdf_path),
    }), 201


@app.route("/api/characters")
def api_characters():
    return jsonify(storage.list_characters())


_FMT_CONTENT_TYPE = {
    "yaml": "application/x-yaml", "md": "text/markdown", "pdf": "application/pdf",
}
_FMT_FILENAME = {"yaml": "current.yaml", "md": "character.md", "pdf": "character.pdf"}


@app.route("/api/characters/<name>/<fmt>")
def api_character_download(name: str, fmt: str):
    if fmt not in _FMT_FILENAME:
        return jsonify({"error": f"unknown format {fmt!r}"}), 400
    path = storage.char_dir(name) / _FMT_FILENAME[fmt]
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    mode = "rb" if fmt == "pdf" else "r"
    encoding = None if fmt == "pdf" else "utf-8"
    with open(path, mode, encoding=encoding) as f:
        data = f.read()
    return Response(data, mimetype=_FMT_CONTENT_TYPE[fmt])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5300, debug=True)
