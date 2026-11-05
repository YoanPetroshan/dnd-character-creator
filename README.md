# D&D Character Creator

A web app that builds D&D 5e (2014 SRD) characters and exports them as YAML,
Markdown or PDF. The UI, the engine's messages and the Markdown/PDF exports come in Bulgarian and English
(Bulgarian is the default); see "Languages and names" below.

The current app is the **v2 builder**: `server/` (Flask JSON API + engine) and
`frontend/` (React/TypeScript, Vite). The character being built is a
*Draft* kept in the browser (`localStorage`: a character library under `dnd-builder-library-v1`, one draft per character under `dnd-builder-draft-v2:<id>`);
every change is sent to `POST /api/resolve`, which returns the finished sheet,
the open choices and any problems. Nothing is stored on the server.
`chargen/` holds the bundled SRD JSON (`chargen/data/srd/`) and the official-data
helpers (`chargen.sync`, `chargen.sources`) that v2 reads.

*History:* the first-generation app (repo-root `app.py`, `storage.py`, `sheet_derive.py`,
`markdown_render.py`, `pdf_fill.py`, `templates/`, `static/`, `assets/`) was removed on
2026-11-03 (D-5); see git history before the D-5 commit (`git log --diff-filter=D -- app.py`).

For how the v2 engine works, read
`docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`.

## Languages and names

The app speaks Bulgarian (default) and English. Rules texts follow the 2024 Player's Handbook (then the SRD) in English; the
Bulgarian is the wording the app has always used. Game content from the data (class, species, feat, spell and item names,
feature names, 5etools descriptions) stays English in both languages on purpose.

**How the switch works.** The BG / EN buttons in the header set a per-device preference
(`localStorage["dnd-builder-lang-v1"]` = `bg` or `en`; anything else or blocked storage means `bg`) and `<html lang>`. The
choice survives a reload. The page texts come from the frontend copy catalog (`frontend/src/copy/`); everything the server
writes comes back in the same language because the frontend appends `?lang=` to its requests.

**`?lang=`.** `POST /api/resolve?lang=bg|en` returns the problems, warnings, pruned reasons, option `disabledReason`s and
the card labels / descriptions the engine writes in that language (card ids, counts and statuses never change).
`POST /api/export/<markdown|pdf|yaml>?lang=bg|en` prints the file's labels in that language. Missing `lang` is English for
`/api/resolve` and the export gate, and Bulgarian for the Markdown / PDF file (the language the exports had before they
were bilingual). Any other value is a 400. Details: `docs/API.md`.

**Where to add things.**

| To add | Where |
|---|---|
| a rules term (Armor Class, Short Rest ...) | `server/i18n/glossary.json` (`en`, `bg`, a citation), then regenerate with `cd server && ../.venv/bin/python -m i18n.glossary` (writes `docs/GLOSSARY.md` and `frontend/src/copy/glossary.gen.ts`) |
| a text the server writes (problem, warning, pruned reason, disabled reason, card label / description) | a key with `en` and `bg` in `server/i18n/catalog/{problems,warnings,pruned,disabled,labels}.py`, emitted with `msg("<key>", **params)` (never an f-string) |
| an export label | `server/export_labels.py`, the same key in both `_BG` and `_EN` |
| a web UI text | the same key in `frontend/src/copy/bg.ts` and `en.ts` (`en.ts` is typed as `Copy`, so a missing key fails `npm run build`); rules terms in `en.ts` read `g.<term>.en` from the glossary |
| a wording you are unsure about | add it to the flag list in `server/i18n/review_table.py` and regenerate `docs/I18N-REVIEW.md` |

`server/tests/test_i18n_completeness.py` checks all of these layers against each other (both languages complete, glossary
and copy in step, no plain English left in `?lang=bg` output). `docs/I18N-REVIEW.md` lists the wordings the project owner
should confirm. The overview with the test map and the known English leftovers is the "i18n" section of
`docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`.

**Random names.** The dice button next to the character name on Home fills in a random Bulgarian name (first name and a
surname of the same gender) in Bulgarian, and its official Latin transliteration in English (for example
"Драгана Вутова" / "Dragana Vutova"). The name lists are in `frontend/src/names/bgNames.ts` (each name carries an origin tag; the
`christian` origin is excluded by default through `DEFAULT_ORIGINS`), the transliteration in `frontend/src/logic/translit.ts`.

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r server/requirements.txt
    cd frontend && npm install     # or: scripts/setup.sh (venv, deps, frontend build)

The full data ships in the repo: the SRD JSON in `chargen/data/srd/` and the official 5etools data (the ~150 non-SRD
races, backgrounds, feats, spells, subclasses) in `server/data/official`. A fresh clone runs the whole app with no
sync step and nothing outside the repository. Which data the server reads (decided at call time):
`DND_OFFICIAL_DATA=none` gives SRD-only; `DND_OFFICIAL_DATA=<dir>` uses that directory; an explicitly set
`DND_CAMPAIGN_ROOT` with a non-empty `.data/official` uses that one; otherwise the bundle. The implicit
`~/.claude/dnd/.data/official` is not read. Where the data comes from: `DATA-SOURCES.md`.

## Run

Development, two terminals (the Vite dev server proxies `/api` to the backend):

    # backend, http://127.0.0.1:8000
    cd server && ../.venv/bin/python app.py
    # frontend, http://localhost:5173
    cd frontend && npm run dev

Single origin, as it would be deployed (Flask serves the built frontend and the API):

    cd frontend && npm run build
    cd ../server && ../.venv/bin/python app.py     # http://127.0.0.1:8000

Backend settings: `HOST` (default `127.0.0.1`), `PORT` (default `8000`),
`FLASK_DEBUG=1` for the debugger.

## Hosting for friends

Run it (builds the frontend on first start; `--rebuild` forces a rebuild; `scripts/setup.sh` does the one-time venv and
npm setup):

    scripts/start.sh

This starts [waitress](https://docs.pylonsproject.org/projects/waitress/) (a production WSGI server, not the Flask
dev server; `FLASK_DEBUG` is never set). Settings: `HOST` (default `127.0.0.1`), `PORT` (default `8000`), `THREADS`
(default `4`), for example `env HOST=0.0.0.0 PORT=9000 scripts/start.sh`.

It is a single origin: Flask serves the built frontend and the API (`/api/*`) from the same port. CORS only matters for
the Vite dev origin (`http://localhost:5173`).

**HTTPS.** The app speaks plain HTTP; put TLS in front of it:

1. **Tailscale (recommended).** Keep the default `127.0.0.1:8000` and run `tailscale serve --bg 8000` (the exact flags
   depend on your Tailscale version). You get HTTPS inside your tailnet only; nothing is exposed publicly. Friends join
   your tailnet (or you share the node) and open the `https://<machine>.<tailnet>.ts.net` URL.
2. **A VPS or home server behind Caddy.** Run the app on `127.0.0.1:8000` and let Caddy proxy to it with automatic
   HTTPS (`example.com { reverse_proxy 127.0.0.1:8000 }`).

**Things to know.**

- There is **no authentication**: anyone who can reach the URL can use the app. Request bodies are limited to 1 MB
  (`MAX_CONTENT_LENGTH`). Do not expose it to the open internet unless that is what you want.
- Nothing is stored on the server. Each friend's draft lives in their own browser's `localStorage`, **per origin**:
  changing the host, port or scheme makes the draft "disappear" (it is still under the old origin). Export the draft
  first.
- The data ships in the repository, so no sync step is needed on the host.
- A `Dockerfile` and `.dockerignore` are included, but **untested** (Docker is not installed on the development
  machine).

## Offline pack (Pyodide)

The engine can also run in the browser (Pyodide, the same Python code). Slice O1 builds the pack and proves it equal to
the native engine; O2 runs it in the app (O3 loads the PDF part lazily, the PWA comes in O4).

    .venv/bin/python scripts/build_offline.py          # builds app.zip + fonts.zip, fetches the pinned runtime
    .venv/bin/python scripts/build_offline.py --check  # verify only, no network
    cd frontend && npm run test:offline                # the Node equivalence test (also part of `npm test`)

Output goes to `frontend/public/pyodide/` (gitignored, about 18 MB raw, about 11 MB gzip). The only network use is the
list of pinned downloads in `scripts/offline_manifest.json` (Pyodide 314.0.7 from `cdn.jsdelivr.net/pyodide/v314.0.7/full/`,
fpdf2 and defusedxml wheels from `files.pythonhosted.org`); each file must match its pinned size and sha256 or the
script stops. `app.zip` is deterministic. `npm test` skips the offline test when the pack is absent. To measure the
cold start on a phone: `cd frontend && npm run dev:lan`, open `http://<Mac LAN IP>:5173/offline-probe.html`, tap Run
(throwaway page, not in the build).

Running the app on the in-browser engine (no server at all): build the pack, then `cd frontend && npm run build:offline
&& npm run preview` (or `npm run dev:offline`). The default `npm run dev` / `npm run build` still talk to the Flask server;
the offline build asks for the engine through `VITE_OFFLINE_ENGINE=1` (`frontend/.env.offline`) and still falls back to
the server when the pack is not served or WebAssembly is missing. Details: `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`, section O1.

## Test

Clean-clone smoke (proves the committed tree alone runs the app: fresh `git clone` of HEAD, empty `HOME`, no `DND_*`
variables, network blocked; commit first, it refuses tracked changes):

    .venv/bin/python scripts/smoke_clean_clone.py [--frontend] [--full-suite] [--keep]

It reuses the main checkout's `.venv` (dependencies are not data). A true fresh-venv check needs `pip download` once
while online, then `pip install --no-index --find-links <dir>`. `RUN_CLONE_SMOKE=1` also runs it from pytest.

    # v2 server (the main suite)
    cd server && ../.venv/bin/python -m pytest -q
    # repo-root tests (the chargen package + the import-isolation guard that covers server/ too)
    .venv/bin/python -m pytest -q
    # frontend: type-check and build, then the unit tests of the pure logic modules
    cd frontend && npm run build && npm test

**Frontend tests.** `cd frontend && npm test` runs vitest (pinned, node environment, no DOM) over `frontend/src/logic/*.test.ts`:
the pure modules the pages call (export gate parity with `server/app.py` `_pending_export_problems`, step status, spell-card
routing, source toggling, file names, ability math, draft merge/sanitize and the draft reducer). There are no component or
browser tests; the pages are checked by hand at 375 px (see `docs/superpowers/specs/REAL-DEVICE-CHECKLIST.md`).

Python dependencies are pinned in `server/requirements.txt` (the repo-root `requirements.txt` only includes it, so one install covers both suites). The frontend is locked by
`frontend/package-lock.json`.

**Official data and skips.** The server tests run against the bundled data by default, so none of them skip for a data
reason: 7449 passed, 2 skipped (both opt-in: `RUN_WAITRESS_TEST=1` and `RUN_CLONE_SMOKE=1`). To run the SRD-only subset put `env DND_OFFICIAL_DATA=none` in front of the pytest
command; the tests that need the official data, classes or spells (the W12 `needs_official` marker, built from
`has_official()`, `has_official_classes()` and `has_official_spells()` in `catalog.official_source`, plus older modules
with "official data not fetched on this machine") then skip, giving 1493 passed / 5708 skipped, 0 failed:

    cd server && env DND_OFFICIAL_DATA=none ../.venv/bin/python -m pytest -q

Skip markers evaluate at collection time, so the variable must be set before pytest starts.
`DND_CAMPAIGN_ROOT=/nonexistent` no longer hides anything: it now means "use the bundle" (superseded by
`DND_OFFICIAL_DATA=none`). The repo-root suite does not depend on the data: 356 passed, 8 skipped (ported dead-by-design code). With an empty `HOME` the server suite gives 7448 passed / 3 skipped (the third is the bundle-vs-synced-copy comparison, which needs a real synced copy).

**Timing.** The wall-clock "resolve() under 50 ms" tests are warm and take the best of N runs (`server/tests/perf_helpers.py`), so a busy machine does not fail them; the bound itself is unchanged. The server suite takes about 105 s on the development machine (126 s when another suite runs in parallel); the root suite takes about 5 s. Run either in the background if your tool has a timeout.

**Parallel run (opt-in).** `pytest-xdist` is installed from `server/requirements.txt`. Serial `pytest -q` stays the default (no `-n` in `pytest.ini`); to use all cores run `cd server && ../.venv/bin/python -m pytest -q -n auto` (or `-n 4`). Pass/skip counts are identical to the serial run (7449 passed / 2 skipped with the data; 1493 passed / 5708 skipped with `DND_OFFICIAL_DATA=none`). Measured on 2026-11-03 on an 8-CPU Mac: serial about 110 s, `-n 4` about 40 s, `-n auto` (8 workers) about 45 s; with `DND_OFFICIAL_DATA=none` parallel is not faster (serial 10 s, `-n auto` 12 s). The repo-root suite (about 2 s) does not benefit.

**Refreshing the official data.** The bundle is a frozen byte copy; refresh it only on purpose.

1. Fetch current 5etools data into the local sync folder: `.venv/bin/python -m chargen.sync --official --force`
   (or skip this step and point step 2 at a `5etools-src` checkout's `data/` directory).
2. Rebuild the bundle: `cd server && ../.venv/bin/python -m catalog.official.bundle --from <dir>`
   (`<dir>` is the synced folder, `~/.claude/dnd/.data/official`, or the checkout's data directory).
   `--check` instead prints what would change and writes nothing.
3. Run the full server suite and the golden (`tests/test_c_series_golden.py`), then the root suite.

A golden diff after a refresh is EXPECTED (the data changed) and needs its own named `--rebaseline` slice; never use
`--regenerate`. Commit `server/data/official/**` (including `MANIFEST.json`) and update `DATA-SOURCES.md`.
Note: the docstrings in `chargen/sync.py` and `chargen/sources.py` that say the official data is "never committed" are
historical. `chargen/` is not edited here (it must stay byte-identical to its source repo, see
`tests/test_chargen_isolation.py`), so those sentences were left as they are; the data now ships in `server/data/official`.

**Fuzz.** `server/tests/test_resolve_fuzz.py` runs 60 seeded random drafts by default. For a bigger run set `FUZZ_N`
(and `FUZZ_SEED0` for the first seed): `FUZZ_N=2000 FUZZ_SEED0=0 .venv/bin/python -m pytest server/tests/test_resolve_fuzz.py -q`.

**Golden policy.** `server/tests/test_c_series_golden.py` pins the resolved output of about 250 filled drafts
under the `mixed` and `2014` rulesets, which must not change by accident. A slice that deliberately changes it adds
an allowlisted entry to `REBASELINES` and runs `tests/test_c_series_golden.py --rebaseline <SLICE>` (use `--dry-run`
first); new cases are added only with `--append`; `--regenerate` is never used. Details are in the module docstring.

**Data overrides.** `DATA_OVERRIDES` in `server/catalog/reference_data.py` lists every correction of a 5etools data
defect; `server/tests/test_data_overrides.py` fails when an upstream record is fixed, so the override can be removed.

More: `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md` (how the engine works, where to find what, known gaps)
and `docs/superpowers/specs/REAL-DEVICE-CHECKLIST.md` (the manual phone check).
