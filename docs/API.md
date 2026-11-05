# HTTP API

The routes are implemented in `server/service.py`, a framework-free entry point: `handle(method, path, query, body) -> (status, content_type, headers, body_bytes)` takes plain values, imports nothing from Flask and reproduces Flask's responses byte for byte (sorted keys, ASCII-escaped compact JSON with a trailing newline, the JSON error bodies, `Content-Disposition` on exports); `query` is a query string or a mapping, `body` is the raw JSON bytes / text, `None`, or a zero-argument callable that returns them (only the two draft routes call it, after their `lang` check). The Flask server (`server/app.py`) is a thin adapter over it: it registers the routes of `service.ROUTES`, passes the request through `service.handle`, and keeps the 1 MB limit (413), CORS, the static single-page app and the startup log line. A non-`/api/` path is not the service's (it answers a JSON 404); a method a route does not take is a 405 `{"error": "The method is not allowed for the requested URL."}`, except a GET of a POST-only path, which is the 404 below (as it always was). All API routes live under `/api`; every other GET serves the built single-page app (an unknown `/api/...` path is a JSON 404). All API responses are JSON except the three export downloads. There is no authentication or rate limiting. Requests are limited to 1 MB.

In the browser every call goes through `apiFetch` (`frontend/src/api/transport.ts`, fetch's signature): the Flask server answers it in `npm run dev` and in the default build; in the offline build (`npm run build:offline` / `dev:offline`, `VITE_OFFLINE_ENGINE=1`) a Web Worker running Pyodide calls `service.handle` with `{method, path, query, body}` and the reply becomes a real `Response` (status, `Content-Type`, `Content-Disposition`, body bytes), so this document describes both. The PDF libraries (fpdf2, Pillow, fonttools, defusedxml) are imported only when a PDF is rendered, so every other route works without them; the worker loads them on the first `POST /api/export/pdf` (the Export page shows "preparing PDF") or at boot when the build sets `VITE_OFFLINE_PDF=eager`. A GET or POST the worker answers never touches the network; the 1 MB limit, CORS and the SPA catch-all are Flask-only.

Contract versions are reported by `GET /api/health` (`apiVersion`, `draftVersion`). The client reads it once at start and shows a banner when the server's `draftVersion` is older than the app's.

## Conventions

- Query lists are comma separated: `sources=phb,xge`. `ruleset` is `2014`, `2024` or `mixed` (default `mixed`). Both are visibility filters only; `resolve` decides what is valid.
- `lang` (`bg` or `en`) is read by `/api/resolve` and `/api/export/<fmt>`; the client appends it to both. Missing means `en` for the engine messages (`/api/resolve`, the export gate); for the Markdown / PDF file of `/api/export/<fmt>` missing means `bg`, the language the exports had before they were bilingual (XL); any other value (including an empty, upper-case or comma-separated one) is a 400 `{"error": "'lang' must be 'bg' or 'en'"}`, checked before the body is read. It selects the language of the engine's messages (`problems`, `warnings`, `pruned`, option `disabledReason`, the export gate). Since I2 `problems` and `warnings` (and the export gate's own entries) the `reason` of every `pruned` entry (I3) and every option `disabledReason` (I4) come back in the requested language; since I5 so do the card `label` and `description` the engine writes ("Skill Proficiencies", "Spellbook", "Choose 2 cantrips from the Cleric list.", "Pact of the Blade: Pact Weapon" ...) and a card's `unavailableReason`, and a card label quoted inside a problem / pruned reason is localized with it. Text that comes from the data stays English whatever `lang` is: class feature / trait names ("Divine Order"), 5etools descriptions, a starting-equipment card's "(a) ... or (b) ..." description, option labels, and the engine's rule paraphrases (notes, resource text). Card ids, counts, statuses and `source` never depend on `lang`. No other route reads it, and the `{"error": ...}` texts below are always English.
- Ids are catalog ids (`fighter`, `acolyte`, `human`, spell and item indexes).

## Error shapes

There are exactly two shapes of error body:

| Shape | When | Example |
| --- | --- | --- |
| `{"error": "<text>"}` | every failure except the export gate | `{"error": "not found"}` |
| `{"problems": [{"id": "<id>", "message": "<text>"}]}` | the export gate (400 from `/api/export/<fmt>` only) | see below |

The texts are English and meant for humans; clients branch on the status code (and, for the gate, on the problem `id`).

| Status | Body | Cause |
| --- | --- | --- |
| 400 | `{"error": "draft must be a JSON object"}` | the body of `/api/resolve` or `/api/export/<fmt>` is JSON but not an object (list, string, number, boolean) |
| 400 | `{"error": "'level' must be an integer"}` | `/api/spells?level=` is not an integer |
| 400 | `{"error": "'lang' must be 'bg' or 'en'"}` | `/api/resolve` or `/api/export/<fmt>` with a `lang` other than `bg` / `en` |
| 400 | `{"problems": [...]}` | export gate, see below |
| 404 | `{"error": "not found"}` | unknown class / background / species / spell id, or an unknown `/api/...` path |
| 404 | `{"error": "unknown export format '<fmt>'"}` | `/api/export/<fmt>` with a format other than `yaml`, `markdown`, `pdf` |
| 413 | `{"error": "<text>"}` | request body over 1 MB |
| 500 | `{"error": "The server couldn't process this character. Check the draft and try again."}` | unexpected failure (logged on the server) |

An absent, empty or unparseable body of the two POST routes counts as an empty draft `{}` (a valid draft), not an error.

## Endpoints

### `GET /api/health`

Liveness and versions.

```json
{"ok": true, "apiVersion": 1, "draftVersion": 2, "dataSource": "bundled", "bundleSha256": "<64 hex>"}
```

- `ok`: always `true` (the only field older servers sent; consumers that read just `ok` keep working).
- `apiVersion`: integer, bumped when a request or response shape changes incompatibly.
- `draftVersion`: the draft shape the server understands (`server/service.py` `DRAFT_VERSION`, pinned by a test to `frontend/src/logic/draft.ts`).
- `dataSource`: `bundled` (the vendored data in `server/data/official`), `srd-only` (`DND_OFFICIAL_DATA=none`), `explicit` (`DND_OFFICIAL_DATA=<path>`) or `campaign` (`DND_CAMPAIGN_ROOT` set and non-empty).
- `bundleSha256`: the full `bundle_sha256` of the vendored data when `dataSource` is `bundled`, else `null`.

### `POST /api/resolve`

Body: a draft object (see `frontend/src/types.ts` `Draft`). Returns the resolution: `{sheet, choices, derived, problems, warnings, pruned}`. `choices` are the cards the player may still fill (each with `id`, `status` `pending|resolved|unavailable`, `options`, `selected`, `count`, optional `optional`); `problems` block export, `warnings` do not; `pruned` lists selections the engine dropped. An unknown id inside a draft is reported as a problem in a 200 response, not as an HTTP error.

### `GET /api/catalog`

Query: `ruleset`, `sources`. Returns `{classes, backgrounds, backgroundsFallback, species, sources}` filtered for the draft's ruleset and sources (`sources` lists every book with its record count, unfiltered).

### `GET /api/catalog/class/<class_id>`

Query: `ruleset`, `sources`, `include=<subclassId>` (keeps the draft's current subclass in the list, marked `hidden: true`, when the filters would hide it). Returns the class record plus `subclasses`, `levelFeatureCounts` (level 1-20) and `subclassUnlockLevel`. 404 for an unknown class.

### `GET /api/catalog/background/<background_id>` and `GET /api/catalog/species/<species_id>`

The record (species also with `subspecies`). 404 when unknown.

### `GET /api/items`

Query: `category`, `q` (name substring, case-insensitive), `ruleset`, `sources`. Returns `{"items": [{id, name, category, source, ruleset}]}`.

### `GET /api/spells`

Query: `class` (class id; no value or an unknown class gives an empty list), `level` (integer), `q`, `ruleset`, `sources`. Returns `{"spells": [...]}` (slim rows). 400 when `level` is not an integer.

### `GET /api/spells/<spell_id>`

One spell with `desc`, `higherLevel`, `material`, `castingCondition`, `classes`, `sourceName`. 404 when unknown.

### `POST /api/export/<fmt>`

`fmt` is `yaml`, `markdown` or `pdf`. Body: a draft. The draft is resolved and the **export gate** is applied; when it passes the response is the file (`application/x-yaml`, `text/markdown`, `application/pdf`) with `Content-Disposition: attachment; filename*=UTF-8''<name>.<ext>`.

Export gate: the export is refused with 400 `{"problems": [...]}` when the resolution has any `problems`, or when:

- no class, species or background is chosen (`export-missing-class`, `export-missing-species`, `export-missing-background`), or
- a choice card is still `pending`, except equipment cards and `optional` cards (`unresolved-choice-<choice id>`, message `'<label>' isn't fully chosen yet.`).

The `problems` list is the resolution's problems first, then the gate's own entries, in the requested `lang` (see Conventions). The exported file follows `lang` (XL): `markdown` and `pdf` print every label (section headings, field names, the unnamed-character title "Безименен герой" / "Unnamed Character") in the requested language, `bg` or, when `lang` is missing, `bg` (byte-identical to the exports before they were bilingual); `en` uses the wording of the sources and the glossary. Names that come from the data (class, species, feat, spell, item, skill, language, feature names, rule notes) stay English in both languages, engine messages inside the sheet are localized with the same `lang`, and the character's own text (name, details) is printed as typed. `yaml` has no localized labels: it is the same for every `lang` (the `lang` is still validated, a bad one is a 400). A nameless draft downloads as `character.<ext>` when `lang` is missing (as before), `герой.<ext>` with `lang=bg` and `character.<ext>` with `lang=en`. The labels live in `server/export_labels.py`. The frontend mirrors the gate in `frontend/src/logic/exportReadiness.ts`, and a test keeps the two in step.
