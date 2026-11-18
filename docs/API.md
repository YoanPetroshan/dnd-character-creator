# HTTP API

The routes are implemented in `server/service.py`, a framework-free entry point: `handle(method, path, query, body) -> (status, content_type, headers, body_bytes)` takes plain values, imports nothing from Flask and reproduces Flask's responses byte for byte (sorted keys, ASCII-escaped compact JSON with a trailing newline, the JSON error bodies, `Content-Disposition` on exports); `query` is a query string or a mapping, `body` is the raw JSON bytes / text, `None`, or a zero-argument callable that returns them (only the two draft routes call it, after their `lang` check). The Flask server (`server/app.py`) is a thin adapter over it: it registers the routes of `service.ROUTES`, passes the request through `service.handle`, and keeps the 1 MB limit (413), CORS, the static single-page app and the startup log line. A non-`/api/` path is not the service's (it answers a JSON 404); a method a route does not take is a 405 `{"error": "The method is not allowed for the requested URL."}`, except a GET of a POST-only path, which is the 404 below (as it always was). All API routes live under `/api`; every other GET serves the built single-page app (an unknown `/api/...` path is a JSON 404). All API responses are JSON except the three export downloads. There is no authentication or rate limiting. Requests are limited to 1 MB.

In the browser every call goes through `apiFetch` (`frontend/src/api/transport.ts`, fetch's signature): the Flask server answers it in `npm run dev` and in the default build; in the offline build (`npm run build:offline` / `dev:offline`, `VITE_OFFLINE_ENGINE=1`) a Web Worker running Pyodide calls `service.handle` with `{method, path, query, body}` and the reply becomes a real `Response` (status, `Content-Type`, `Content-Disposition`, body bytes), so this document describes both. The PDF libraries (fpdf2, Pillow, fonttools, defusedxml, pypdf) are imported only when a PDF is rendered, so every other route works without them; the worker loads them on the first `POST /api/export/pdf` or `/api/export/sheet` (the Export page shows "preparing PDF") or at boot when the build sets `VITE_OFFLINE_PDF=eager`. A GET or POST the worker answers never touches the network; the 1 MB limit, CORS and the SPA catch-all are Flask-only.

Contract versions are reported by `GET /api/health` (`apiVersion`, `draftVersion`). The client reads it once at start and shows a banner when the server's `draftVersion` is older than the app's.

## Conventions

- Query lists are comma separated: `sources=phb,xge`. `ruleset` is `2014`, `2024` or `mixed` (default `mixed`). Both are visibility filters only; `resolve` decides what is valid.
- `lang` (`bg` or `en`) is read by `/api/resolve` and `/api/export/<fmt>`; the client appends it to both. Missing means `en` for the engine messages (`/api/resolve`, the export gate); for the Markdown / PDF file of `/api/export/<fmt>` missing means `bg`, the language the exports had before they were bilingual (XL); any other value (including an empty, upper-case or comma-separated one) is a 400 `{"error": "'lang' must be 'bg' or 'en'"}`, checked before the body is read. It selects the language of the engine's messages (`problems`, `warnings`, `pruned`, option `disabledReason`, the export gate). Since I2 `problems` and `warnings` (and the export gate's own entries) the `reason` of every `pruned` entry (I3) and every option `disabledReason` (I4) come back in the requested language; since I5 so do the card `label` and `description` the engine writes ("Skill Proficiencies", "Spellbook", "Choose 2 cantrips from the Cleric list.", "Pact of the Blade: Pact Weapon" ...) and a card's `unavailableReason`, and a card label quoted inside a problem / pruned reason is localized with it. Text that comes from the data stays English whatever `lang` is: class feature / trait names ("Divine Order"), 5etools descriptions, a starting-equipment card's "(a) ... or (b) ..." description, option labels, and the engine's rule paraphrases (notes, resource text). Card ids, counts, statuses and `source` never depend on `lang`. No other route reads it, and the `{"error": ...}` texts below are always English.
- **What stays English with `lang=bg` on purpose (VF7.7, decision documented here).** Names from the books (class, feature, feat, spell, item, species, background names, skill names inside a description) are data and are not translated. The attack-row notes the engine writes itself are tagged messages and are translated (`derived.attacks[].notes`: the six weapon property words with the English term in brackets, Great Weapon Fighting, Thrown Weapon Fighting, Dueling, the pact weapon note, "Rage: +N damage", the natural-weapon notes); feature names with dice stay as they are (`Sneak Attack 3d6`, `Divine Strike: +1d8 necrotic or radiant (once per turn)`, `Martial Arts`, `Colossus Slayer ...`) and so do the long feat-rule rider sentences of the feat tables (Great Weapon Master, Savage Attacker, ...) and resource-line notes: they are rule text copied from the books, translated only if the owner asks for a Bulgarian rules text. A stale stored pick named in a `pruned` reason shows its label in Bulgarian (a feature or language name, "14 gp", else the option id spelled as words) and its raw id in English (the frozen English text). The 2024 class "Choose ..." descriptions (skills, tools) are translated with plural handling (the Bulgarian shows the count as a digit).
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
| 400 | `{"error": "The request body is nested too deeply (at most 64 levels)."}` | the body of `/api/resolve` or `/api/export/<fmt>` nests brackets deeper than 64 levels (a draft has about 8), parseable or not; checked on the raw text before parsing |
| 400 | `{"error": "draft must be a JSON object"}` | the body of `/api/resolve` or `/api/export/<fmt>` is JSON but not an object (list, string, number, boolean) |
| 400 | `{"error": "'level' must be an integer"}` | `/api/spells?level=` is not an integer |
| 400 | `{"error": "'lang' must be 'bg' or 'en'"}` | `/api/resolve` or `/api/export/<fmt>` with a `lang` other than `bg` / `en` |
| 400 | `{"problems": [...]}` | export gate, see below |
| 404 | `{"error": "not found"}` | unknown class / background / species / spell id, or an unknown `/api/...` path |
| 404 | `{"error": "unknown export format '<fmt>'"}` | `/api/export/<fmt>` with a format other than `yaml`, `markdown`, `pdf`, `sheet` |
| 413 | `{"error": "The data value transmitted exceeds the capacity limit."}` | request body over 1,000,000 bytes (the two draft routes, after their `lang` check); Flask enforces it, and so do `service.handle` and the offline worker (`frontend/src/api/bodyGuard.ts` checks size and depth before the bytes enter WebAssembly) |
| 500 | `{"error": "The server couldn't process this character. Check the draft and try again."}` | unexpected failure (logged on the server) |

An absent, empty (or `null`) body of the two POST routes counts as an empty draft `{}` (a valid draft), not an error. A body that is not readable JSON (invalid text or UTF-8, a number over 4300 digits) is a 400 `{"error": "The request body is not readable JSON."}`.

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

The record (species also with `subspecies`, `fluff`, `traitDetails`). 404 when unknown. The species route takes `lang=bg|en` (a bad value is a 400): with `bg` the `fluff` paragraphs and each `traitDetails[i].desc` are the Bulgarian text from the content overlay when its hash matches the current English, else English; trait names stay English. The species body always carries `textLang` (`"bg"` when the Bulgarian text was applied, else `"en"`).

### `GET /api/items`

Query: `category`, `q` (name substring, case-insensitive), `ruleset`, `sources`. Returns `{"items": [{id, name, category, source, ruleset}]}`.

### `GET /api/items/<item_id>`

One item with everything the item eye shows: `{id, name, category, source, ruleset, cost: {quantity, unit}, weight, damage: {dice, type} | null, twoHandedDamage: {dice, type} | null, range: {normal, long?} | null, throwRange | null, properties: [{id, name, desc: [text]}], mastery: {name, desc: [text]} | null, armor: {base, dexBonus, maxBonus | null, strMinimum, stealthDisadvantage} | null, contents: [{id, name, qty}], desc: [text], special: [text], textLang}`. `armor` is set for armor and shields, `contents` for equipment packs, `desc` / `special` hold the SRD text of the item (Net and Lance have `special`). 404 when the id is unknown.

Query: `ruleset` (`2024`: the property texts of the 2024 Player's Handbook; anything else: those of the 2014 one; the `mastery` is left out under `2014`, otherwise it is the 2024 weapon mastery of the weapon). `properties[].desc` is `[]` for `special` and `monk` (the books give them no text) and when the official data is not installed (SRD-only mode: the property and mastery texts are then empty). `lang` (`bg` or `en`, missing is `en`; anything else is a 400). With `lang=bg` each text (the item's own `desc` / `special`, every property text, the mastery text) comes from the Bulgarian overlay (kind `items` for the item text, kind `item-rules` for the property and mastery texts) when it has an entry whose `hash` still matches; every other text stays English. Item, property and mastery names stay English. `textLang` is `bg` only when `lang=bg` and no English prose is left in the response (every non-empty text came from the overlay, or there is none); one missing or stale text makes it `en`, and the pieces that did come from the overlay are still Bulgarian. Overlay format and workflow: `server/data/i18n/README.md`.

### `GET /api/feats/<feat_id>`

One feat as the choice pickers' eye shows it: `{id, name, prerequisite, desc: [text], textLang}`. `id` is the catalog feat index, the `<idx>` of the option ids `feat:<idx>`. `prerequisite` is the feat's prerequisite as readable English (`"Level 4, Strength 13; or Level 4, Dexterity 13"`, alternatives joined by `; or `), `""` when it has none. `desc` is the feat text flattened to paragraphs. 404 when the id is unknown. Query: `lang` (`bg` or `en`, missing is `en`; anything else is a 400). With `lang=bg` `desc` comes from the Bulgarian overlay (kind `feats`) when it has an entry whose `hash` still matches the English paragraphs; otherwise English. `prerequisite` is rendered in Bulgarian too (catalog keys `feat-prereq-*`, e.g. `"Ниво 4 или по-високо, Strength 13 или повече"`); names (abilities, classes, species, feats, features) and free text the data carries stay English. `textLang` is `bg` or `en`. Overlay format and workflow: `server/data/i18n/README.md`.

### `GET /api/features/<feature_id>`

One feature text for the feature eye: `{id, name, level, className, subclassName, source, desc: [text], textLang}`. `id` is one of: a catalog feature id (SRD `rage`, XPHB `berserker-xphb-3-frenzy`, any subclass feature; `level`, `className`, `subclassName` are the catalog's, `subclassName` is `null` for a class feature); a species trait ref `trait:<species id>:<trait index>` (the ref the character sheet carries for a species trait; `level`, `className` and `subclassName` are `null`; `desc` is the trait text, Bulgarian from the species overlay when the trait is one of the species' own listed traits and the species entry is fresh, English for a subspecies trait); `background:<background id>` (the background feature: `name` and the English `desc` from the catalog, `[]` and `""` when the background has no feature text). 404 when the id (or the species / trait / background) is unknown. Query: `lang` (`bg` or `en`, missing is `en`; anything else is a 400). With `lang=bg` a catalog feature's `desc` comes from the Bulgarian overlay (kind `features`, keyed by the feature id) when its `hash` still matches the English paragraphs; otherwise English. Names stay English. `source` is `SRD` for the SRD features. `textLang` is `bg` or `en`. Overlay format and workflow: `server/data/i18n/README.md`.

### `GET /api/subclasses/<subclass_id>`

One subclass with all its features: `{id, name, source, ruleset, desc: [text], features: [{id, name, level, desc: [text]}], textLang}`. `desc` is the subclass's own intro (only the SRD subclasses have one; `[]` otherwise, the intro of the other books is their first feature). `features` follow the subclass level table (level order, then row order), `id` is the catalog feature id, so the same id works with `/api/features/<id>`; each feature is overlaid on its own (kind `features`). 404 when the id is unknown. Query: `lang` (`bg` or `en`, missing is `en`; anything else is a 400). `textLang` is `bg` only when `lang=bg` and no English prose is left (every non-empty text, the intro included, is Bulgarian); one English text makes it `en`, and the features that did come from the overlay are still Bulgarian. The subclass intro has no overlay yet, so a subclass that has one answers `en`.

### `GET /api/spells`

Query: `class` (class id; no value or an unknown class gives an empty list), `level` (integer), `q`, `ruleset`, `sources`. Returns `{"spells": [...]}` (slim rows). 400 when `level` is not an integer.

### `GET /api/spells/<spell_id>`

One spell with `desc`, `higherLevel`, `material`, `castingCondition`, `classes`, `sourceName`. 404 when unknown.

Query: `lang` (`bg` or `en`, missing is `en`; anything else is a 400). With `lang=bg` the long texts (`desc`, `higherLevel`, `material`, `castingCondition`) come from the Bulgarian overlay `server/data/i18n/bg/spells.json` when it has an entry whose `hash` still matches the English text; otherwise the English text is served. `textLang` (`bg` or `en`) says which language the texts are in. The list route `/api/spells` does not take `lang`. Overlay format and workflow: `server/data/i18n/README.md`.

### `POST /api/export/sheet` (the fillable character sheet)

Same gate, `lang` handling (missing means `bg`), name rule (200 characters, `.pdf`) and error bodies as the other formats; the response is `application/pdf`: an A4 character sheet in the layout of the D&D Beyond sheet (own plain frames, no D&D Beyond / WotC artwork or footer) whose boxes are editable form fields (AcroForm, `/NeedAppearances false`). Fields have ASCII names; the six identity fields are one field shown on pages 1-3 (CharacterName also on page 4). Pages: 1 combat, 2-3 features flow / coins / equipment, continuation pages as needed (features, equipment, notes), page 4 story, spell pages (50 rows each, one group per spellcasting class and the innate spells). Footer: `Лист на героя (Character Sheet) · <name> · стр. N/M` (`Character Sheet · <name> · p. N/M`). A character the font has no glyph for (emoji, CJK) prints as `?`. The creation date is the time of the request, so the bytes differ between requests; the rest is deterministic. In the browser the worker loads the PDF stack (now including pypdf) before the first `sheet` or `pdf` export.

### `POST /api/export/<fmt>`

`fmt` is `yaml`, `markdown`, `pdf` or `sheet`. Body: a draft. The draft is resolved and the **export gate** is applied; when it passes the response is the file (`application/x-yaml`, `text/markdown`, `application/pdf`) with `Content-Disposition: attachment; filename*=UTF-8''<name>.<ext>`. `<name>` is the draft's `name` (`character`, or the language's word with `lang`, when it is empty) with `\ / : * ? " < > |` replaced by `_`, control and bidi-override characters (`U+0000-001F`, `U+007F`, `U+202A-202E`, `U+2066-2069`) dropped, cut to the first 200 characters, trailing dots and spaces removed (nothing left: the fallback) and a reserved Windows device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) given a leading `_` (the sheet title inside the Markdown / PDF keeps the whole name) and percent-encoded; a lone UTF-16 surrogate (`"\ud800"`, valid JSON) in any text of the draft becomes U+FFFD before the export is written (it used to be a 500).

Export gate: the export is refused with 400 `{"problems": [...]}` when the resolution has any `problems`, or when:

- no class, species or background is chosen (`export-missing-class`, `export-missing-species`, `export-missing-background`), or
- a choice card is still `pending`, except equipment cards and `optional` cards (`unresolved-choice-<choice id>`, message `'<label>' isn't fully chosen yet.`).

The `problems` list is the resolution's problems first, then the gate's own entries, in the requested `lang` (see Conventions). The exported file follows `lang` (XL): `markdown` and `pdf` print every label (section headings, field names, the unnamed-character title "Безименен герой" / "Unnamed Character") in the requested language, `bg` or, when `lang` is missing, `bg` (byte-identical to the exports before they were bilingual); `en` uses the wording of the sources and the glossary. Names that come from the data (class, species, feat, spell, item, skill, language, feature names, rule notes) stay English in both languages, engine messages inside the sheet are localized with the same `lang`, and the character's own text (name, details) is printed as typed. `yaml` has no localized labels: it is the same for every `lang` (the `lang` is still validated, a bad one is a 400). A nameless draft downloads as `character.<ext>` when `lang` is missing (as before), `герой.<ext>` with `lang=bg` and `character.<ext>` with `lang=en`. The labels live in `server/export_labels.py`. The frontend mirrors the gate in `frontend/src/logic/exportReadiness.ts`, and a test keeps the two in step.
