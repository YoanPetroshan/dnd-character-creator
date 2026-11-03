# D&D Character Creator

A web app that builds D&D 5e (2014 SRD) characters and exports them as YAML,
Markdown or PDF. The UI and the Markdown/PDF exports are in Bulgarian.

The current app is the **v2 builder**: `server/` (Flask JSON API + engine) and
`frontend/` (React/TypeScript, Vite). The character being built is a
*Draft* kept in the browser (`localStorage` key `dnd-builder-draft-v2`);
every change is sent to `POST /api/resolve`, which returns the finished sheet,
the open choices and any problems. Nothing is stored on the server.
`chargen/` holds the bundled SRD JSON (`chargen/data/srd/`) and the official-data
helpers (`chargen.sync`, `chargen.sources`) that v2 reads.

*History:* the first-generation app (repo-root `app.py`, `storage.py`, `sheet_derive.py`,
`markdown_render.py`, `pdf_fill.py`, `templates/`, `static/`, `assets/`) was removed on
2026-11-03 (D-5); see git history before the D-5 commit (`git log --diff-filter=D -- app.py`).

For how the v2 engine works, read
`docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`.

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r server/requirements.txt
    cd frontend && npm install

The official 5etools data (the ~150 non-SRD races, backgrounds, feats, spells, subclasses) is vendored in the repo at
`server/data/official`, so no sync step is needed. Which data the server reads (read at call time):
`DND_OFFICIAL_DATA=none` gives SRD-only; `DND_OFFICIAL_DATA=<dir>` uses that directory; an explicitly set
`DND_CAMPAIGN_ROOT` with a non-empty `.data/official` uses that one; otherwise the bundle. The implicit
`~/.claude/dnd/.data/official` is no longer read. (B3 will document refreshing the bundle.)

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

## Test

    # v2 server (the main suite)
    cd server && ../.venv/bin/python -m pytest -q
    # repo-root tests (the chargen package + the import-isolation guard that covers server/ too)
    .venv/bin/python -m pytest -q
    # frontend: type-check and build (there is no frontend test runner)
    cd frontend && npm run build

Python dependencies are pinned in `server/requirements.txt` (the repo-root `requirements.txt` only includes it, so one install covers both suites). The frontend is locked by
`frontend/package-lock.json`.

**Official data and skips.** The server tests run against the vendored bundle by default, so none of them skip for a data reason. Two skip reasons exist for the case where the data is hidden: tests that need the official
data, classes or spells (the W12 `needs_official` marker, built from `has_official()`, `has_official_classes()` and
`has_official_spells()` in `catalog.official_source`) skip with "5etools data not available", and
older modules skip with "official data not fetched on this machine". Skip markers evaluate at collection time, so set the variable before pytest starts: to run the SRD-only subset, put `env DND_OFFICIAL_DATA=none` in front of the pytest
command (`DND_CAMPAIGN_ROOT=/nonexistent` no longer hides anything: it now means "use the bundle"). Measured on 2026-11-03: with the bundle 7415+ tests pass; with `DND_OFFICIAL_DATA=none` about 5705 skip and about 1460 pass, with 0 failures and 0 errors. The repo-root suite does not depend on the data: 356 passed,
8 skipped (ported dead-by-design code).

**Timing.** The server suite takes about 105 s on the development machine (126 s when another suite runs in parallel); the root suite takes about 5 s. Run either in the background if your tool has a timeout.

**Parallel run (opt-in).** `pytest-xdist` is installed from `server/requirements.txt`. Serial `pytest -q` stays the default (no `-n` in `pytest.ini`); to use all cores run `cd server && ../.venv/bin/python -m pytest -q -n auto` (or `-n 4`). Pass/skip counts are identical to the serial run (7415 passed with the data; 1460 passed / 5705 skipped with `DND_OFFICIAL_DATA=none`). Measured on 2026-11-03 on an 8-CPU Mac: serial about 110 s, `-n 4` about 40 s, `-n auto` (8 workers) about 45 s; with `DND_OFFICIAL_DATA=none` parallel is not faster (serial 10 s, `-n auto` 12 s). The repo-root suite (about 2 s) does not benefit.

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
