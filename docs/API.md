# HTTP API

The Flask server (`server/app.py`) is a thin shell over the catalog and the resolve engine. All API routes live under `/api`; every other GET serves the built single-page app (an unknown `/api/...` path is a JSON 404). All API responses are JSON except the three export downloads. There is no authentication or rate limiting. Requests are limited to 1 MB.

Contract versions are reported by `GET /api/health` (`apiVersion`, `draftVersion`). The client reads it once at start and shows a banner when the server's `draftVersion` is older than the app's.

## Conventions

- Query lists are comma separated: `sources=phb,xge`. `ruleset` is `2014`, `2024` or `mixed` (default `mixed`). Both are visibility filters only; `resolve` decides what is valid.
- The client appends `?lang=bg|en` to `/api/resolve` and `/api/export/<fmt>`. The server ignores it today.
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
- `draftVersion`: the draft shape the server understands (`server/app.py` `DRAFT_VERSION`, pinned by a test to `frontend/src/logic/draft.ts`).
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

The `problems` list is the resolution's problems first, then the gate's own entries. The frontend mirrors the gate in `frontend/src/logic/exportReadiness.ts`, and a test keeps the two in step.
