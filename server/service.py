"""Framework-free implementation of the HTTP API (docs/API.md): every /api route of the Flask shell lives here.

``handle(method, path, query, body) -> (status, content_type, headers, body_bytes)`` takes plain values and returns
plain values, so the same code answers the Flask adapter (``app.py``) and, later, a browser worker running the engine
offline (docs/superpowers/plans/2026-11-04-offline-pyodide.md). It imports nothing from Flask / werkzeug: only the
engine, the catalog, the exporters and the standard library (plus pyyaml and fpdf2 through the exporters). It
reproduces what Flask did byte for byte (``jsonify`` defaults: ``sort_keys=True``, ``ensure_ascii=True``, compact
separators and a trailing newline; the JSON error bodies; ``Content-Disposition`` on exports); the Flask test client
and ``handle`` are compared over a fixed request list by ``tests/test_service.py`` and ``tests/test_service_baseline.py``.

Arguments (all already decoded by the caller):

* ``method``: ``"GET"``, ``"POST"``, ... (case-insensitive; ``HEAD`` is answered as ``GET``).
* ``path``: the URL path without the query string, percent-decoded (``/api/spells/fireball``).
* ``query``: ``None``, a query string (``"ruleset=2024&sources=phb"``, with or without a leading ``?``) or a mapping
  of name -> value (a list / tuple value contributes its first item). The first value of a repeated name wins.
* ``body``: ``None`` (no body, or a body that was not sent as JSON: Flask ignored those too), ``bytes`` / ``str``,
  or a zero-argument callable returning one of those. The callable is only called by the two POST routes, after
  their ``lang`` check, exactly when Flask first read the request body (so an adapter can map a too-large body
  to a 413 only where Flask did). If the callable cannot deliver the body it raises ``BodyReadError`` (from the
  real error), which ``handle`` lets through.

Whatever happens inside a route, ``handle`` answers: an unhandled exception is logged and becomes the JSON 500.
"""
from __future__ import annotations

import dataclasses
import datetime
import decimal
import email.utils
import json
import logging
import re
import urllib.parse
import uuid
from typing import Callable

from catalog.loader import load as load_catalog
from catalog.reference_data import SOURCE_NAMES, ruleset_allows, subclass_unlock_level
from engine.resolve import _source_allowed, _spell_visible, _subclass_visible, resolve
from export import to_yaml
from export_labels import DEFAULT_LANG as EXPORT_DEFAULT_LANG, label as export_label
from i18n.messages import localize, msg, parse_lang
from markdown_export import to_markdown
from pdf_export import to_pdf

log = logging.getLogger("service")

Response = tuple[int, str, dict[str, str], bytes]

_catalog = load_catalog()

# Contract versions reported by /api/health (docs/API.md). API_VERSION changes when a request or
# response shape changes incompatibly; DRAFT_VERSION is the draft shape this server understands and
# must equal DRAFT_VERSION in frontend/src/logic/draft.ts (a test pins the two together).
API_VERSION = 1
DRAFT_VERSION = 2

# Flask's debug mode pretty-prints its JSON; the adapter sets this from `app.debug`. Off everywhere else.
pretty_json = False

class BodyReadError(Exception):
    """Raised by a lazy `body` callable when the transport cannot deliver the body (Flask: over the 1 MB limit). `handle`
    does not turn it into a 500: it propagates, and the adapter re-raises its `__cause__` (the 413)."""


SERVER_ERROR = "The server couldn't process this character. Check the draft and try again."


# --- responses ------------------------------------------------------------------------------------------------------

def _json_default(o):
    """flask.json.provider._default: what Flask's jsonify could serialize beyond the JSON types."""
    if isinstance(o, datetime.date):
        return email.utils.format_datetime(
            o if isinstance(o, datetime.datetime) else datetime.datetime(o.year, o.month, o.day), usegmt=True)
    if isinstance(o, (decimal.Decimal, uuid.UUID)):
        return str(o)
    if dataclasses.is_dataclass(o):
        return dataclasses.asdict(o)
    if hasattr(o, "__html__"):
        return str(o.__html__())
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def _json(value, status: int = 200) -> Response:
    """`jsonify(value)` with Flask's defaults: sorted keys, ASCII only, compact, one trailing newline."""
    args = {"indent": 2} if pretty_json else {"separators": (",", ":")}
    text = json.dumps(value, default=_json_default, ensure_ascii=True, sort_keys=True, **args) + "\n"
    return status, "application/json", {}, text.encode("utf-8")


def _error(text: str, status: int) -> Response:
    return _json({"error": text}, status)


def _not_found() -> Response:
    return _error("not found", 404)


# --- request helpers ------------------------------------------------------------------------------------------------

def _args(query) -> dict[str, str]:
    """The query as {name: first value}: `request.args` semantics."""
    if query is None:
        return {}
    if isinstance(query, bytes):
        query = query.decode("utf-8", "replace")
    if isinstance(query, str):
        pairs = urllib.parse.parse_qsl(query.lstrip("?"), keep_blank_values=True, errors="replace")
        out: dict[str, str] = {}
        for k, v in pairs:
            out.setdefault(k, v)
        return out
    out = {}
    for k, v in query.items():
        if isinstance(v, (list, tuple)):
            if not v:
                continue
            v = v[0]
        out[str(k)] = v if isinstance(v, str) else str(v)
    return out


def _json_draft(body) -> dict | None:
    """The request's JSON body as a draft: an absent / unparseable / null body is an empty draft (as before),
    any other non-object value (list, string, number, bool) is None, which the callers answer with a 400."""
    if callable(body):
        body = body()
    if body is None:
        return {}
    try:
        parsed = json.loads(body)
    except ValueError:  # includes JSONDecodeError and UnicodeDecodeError, what get_json(silent=True) swallowed
        return {}
    if parsed is None:
        return {}
    return parsed if isinstance(parsed, dict) else None


def _request_lang(args: dict[str, str]):
    """The `?lang=` query parameter as (lang, None), or (None, a 400 response). Missing is "en"; anything but
    `bg` / `en` is rejected (docs/API.md). Engine messages are English until the I-series tags them."""
    try:
        return parse_lang(args.get("lang")), None
    except ValueError:
        return None, _error("'lang' must be 'bg' or 'en'", 400)


def _sources(args: dict[str, str]) -> list[str]:
    return [s for s in (args.get("sources") or "").split(",") if s]


# --- routes ---------------------------------------------------------------------------------------------------------

def _bundle_sha256() -> str | None:
    """Full bundle_sha256 of the vendored data when the bundle is the active source, else None."""
    from catalog.official.paths import BUNDLED_DIR, data_source

    if data_source() != "bundled":
        return None
    try:
        return json.loads((BUNDLED_DIR / "MANIFEST.json").read_text(encoding="utf-8"))["bundle_sha256"]
    except (OSError, ValueError, KeyError):
        return None


def health(args, body, **_):
    """Liveness plus the contract versions. `ok` is the original field; old consumers that read only it keep working."""
    from catalog.official.paths import data_source

    return _json({
        "ok": True,
        "apiVersion": API_VERSION,
        "draftVersion": DRAFT_VERSION,
        "dataSource": data_source(),
        "bundleSha256": _bundle_sha256(),
    })


def api_resolve(args, body, **_):
    lang, bad_lang = _request_lang(args)
    if bad_lang:
        return bad_lang
    draft = _json_draft(body)
    if draft is None:
        return _error("draft must be a JSON object", 400)
    return _json(localize(resolve(draft, _catalog), lang))


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


def api_catalog(args, body, **_):
    """`?ruleset=2014|2024|mixed&sources=phb,xge` hides records the draft
    could not pick under that ruleset / source list. Both are visibility
    filters only (resolve() decides what is valid)."""
    ruleset = args.get("ruleset", "mixed")
    sources = _sources(args)

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

    return _json({
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


def api_catalog_class(args, body, class_id: str):
    """The SRD class plus `subclasses`: the class's subclasses visible under
    `?ruleset=&sources=` as {index, name, source, ruleset}, SRD first, then by
    name. `?include=<subclassId>` adds the draft's current selection with
    `hidden: true` when the filters would hide it (or it is not in the list)."""
    cls = _catalog.classes.get(class_id)
    if not cls:
        return _error("not found", 404)
    ruleset = args.get("ruleset", "mixed")
    cls_2024 = _catalog.classes_2024.get(class_id) if ruleset == "2024" else None  # C9a
    if cls_2024:
        cls = cls_2024
    sources = _sources(args)
    include = args.get("include") or ""
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
    return _json({
        **cls,
        "subclasses": rows,
        "levelFeatureCounts": level_feature_counts,
        "subclassUnlockLevel": subclass_unlock_level(class_id, ruleset),
    })


def api_catalog_background(args, body, background_id: str):
    bg = _catalog.backgrounds.get(background_id)
    if not bg:
        return _error("not found", 404)
    return _json(bg)


def api_catalog_species(args, body, species_id: str):
    race = _catalog.races.get(species_id)
    if not race:
        return _error("not found", 404)
    return _json({**race, "subspecies": _catalog.subraces_of(species_id)})


def api_items(args, body, **_):
    category = args.get("category")
    query = (args.get("q") or "").lower()
    ruleset = args.get("ruleset", "mixed")
    sources = _sources(args)
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
    return _json({"items": results})


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


def api_spells(args, body, **_):
    """`?class=&level=&q=` plus `?ruleset=2014|2024|mixed&sources=phb,xge`
    (the draft's, default mixed and every book): the spells the draft could
    pick, one record per spell (see resolve._spell_visible)."""
    class_id = args.get("class") or ""
    level_param = args.get("level")
    query = (args.get("q") or "").lower()
    ruleset = args.get("ruleset", "mixed")
    sources = _sources(args)
    level_filter = None
    if level_param:
        try:
            level_filter = int(level_param)
        except ValueError:
            return _error("'level' must be an integer", 400)
    results = []
    for spell in _spells_by_class.get(class_id, ()):
        if level_filter is not None and spell["level"] != level_filter:
            continue
        if query and query not in spell["name"].lower():
            continue
        if not _spell_visible(_catalog, spell, sources, ruleset):
            continue
        results.append(_spell_items[spell["index"]])
    return _json({"spells": results})


def api_spell_detail(args, body, spell_id: str):
    sid = _catalog.resolve_spell_id(spell_id)
    if sid is None:
        return _error("not found", 404)
    spell = _catalog.spells[sid]
    source = spell.get("source", "SRD")
    return _json({
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
        {"id": pid, "message": text}
        for pid, text, present in (
            ("export-missing-class", msg("export-missing-class"), sheet.get("classes")),
            ("export-missing-species", msg("export-missing-species"), sheet.get("species")),
            ("export-missing-background", msg("export-missing-background"), sheet.get("background")),
        )
        if not present
    ]
    return missing + [
        {"id": f"unresolved-choice-{c['id']}", "message": msg("unresolved-choice", label=c["label"])}
        for c in resolution["choices"]
        if c["status"] == "pending" and c["source"]["kind"] != "equipment" and not c.get("optional")
        # RPF: an `optional` card (cosmetic table pick, e.g. Feywild Gifts) stays selectable but never blocks.
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
    "markdown": (to_markdown, "text/markdown; charset=utf-8", "md"),
    "pdf": (to_pdf, "application/pdf", "pdf"),
}


def api_export(args, body, fmt: str):
    entry = _EXPORT_RENDERERS.get(fmt)
    if entry is None:
        return _error(f"unknown export format '{fmt}'", 404)
    renderer, content_type, extension = entry
    lang, bad_lang = _request_lang(args)
    if bad_lang:
        return bad_lang
    draft = _json_draft(body)
    if draft is None:
        return _error("draft must be a JSON object", 400)
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return _json(localize({"problems": all_problems}, lang), 400)
    # XL: the Markdown / PDF labels follow `lang`; a request without it keeps the language the exports always had
    # (Bulgarian), unlike the engine messages above, which are English then. YAML has no localized labels.
    file_lang = lang if args.get("lang") is not None else EXPORT_DEFAULT_LANG
    # a nameless draft downloads as "character" (no lang, as before XL) or as the language's word (lang given)
    fallback = export_label(lang, "filenameFallback") if args.get("lang") is not None else "character"
    name = re.sub(r'[\\/:*?"<>|]', "_", str(draft.get("name") or fallback))
    filename = urllib.parse.quote(f"{name}.{extension}", safe="")
    if fmt == "yaml":  # the YAML document is the data as it is: no localized labels, nothing to translate
        out = renderer(resolution)
    else:
        out = renderer(localize(resolution, file_lang), file_lang)
    if isinstance(out, str):
        out = out.encode("utf-8")
    return 200, content_type, {"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}, bytes(out)




# --- routing --------------------------------------------------------------------------------------------------------

# (rule, methods, view). The rules use Flask's `<name>` syntax with its default converter (one non-empty path
# segment); `app.py` registers exactly these with Flask, and `handle` matches them itself.
ROUTES: tuple[tuple[str, tuple[str, ...], Callable[..., Response]], ...] = (
    ("/api/health", ("GET",), health),
    ("/api/resolve", ("POST",), api_resolve),
    ("/api/catalog", ("GET",), api_catalog),
    ("/api/catalog/class/<class_id>", ("GET",), api_catalog_class),
    ("/api/catalog/background/<background_id>", ("GET",), api_catalog_background),
    ("/api/catalog/species/<species_id>", ("GET",), api_catalog_species),
    ("/api/items", ("GET",), api_items),
    ("/api/spells", ("GET",), api_spells),
    ("/api/spells/<spell_id>", ("GET",), api_spell_detail),
    ("/api/export/<fmt>", ("POST",), api_export),
)

_COMPILED = tuple(
    (re.compile("^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", rule) + "$"), methods, view)
    for rule, methods, view in ROUTES
)


def _dispatch(method: str, path: str, args: dict[str, str], body) -> Response:
    method = method.upper()
    if method == "HEAD":
        method = "GET"
    if not path.startswith("/api/"):
        return _not_found()  # the SPA (index.html, assets) is the adapter's, not the API's
    for rx, methods, view in _COMPILED:
        m = rx.match(path)
        if m and method in methods:
            return view(args, body, **m.groupdict())
    # What Flask answered: a GET that no route took fell to the SPA catch-all, whose unknown /api/ paths are a
    # JSON 404; any other method (a POST to a GET-only route included) is a 405.
    if method == "GET":
        return _not_found()
    return _error("The method is not allowed for the requested URL.", 405)


def handle(method: str, path: str, query=None, body=None) -> Response:
    """Answer one API request: (status, content_type, headers, body_bytes). See the module docstring."""
    try:
        return _dispatch(method, path, _args(query), body)
    except BodyReadError:
        raise
    except Exception:
        log.exception("unhandled error")
        return _error(SERVER_ERROR, 500)
