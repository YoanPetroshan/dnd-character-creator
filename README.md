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

Optional, for the ~150 official (non-SRD) races, backgrounds and feats:

    .venv/bin/python -m chargen.sync --official

That downloads into `~/.claude/dnd/.data/official` (override the root with
`DND_CAMPAIGN_ROOT`); without it the app runs on the bundled SRD only.

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

**Official data and skips.** Most server tests need the official 5etools data synced (see Setup:
`python -m chargen.sync --official`). Without it the tests that need it are skipped. There are two skip reasons: tests that need the official
data, classes or spells (the W12 `needs_official` marker, built from `has_official()`, `has_official_classes()` and
`has_official_spells()` in `catalog.official_source`) skip with the reason "5etools data not available", and
older modules skip with "official data not fetched on this machine"; the SRD-only tests still run. To see the skip count on your machine, run `DND_CAMPAIGN_ROOT=/nonexistent` in front of the pytest
command (it hides the synced data) and read the summary line. Measured on 2026-11-03 (W12): with the data 7213 passed; without it 5503 tests skip and 1460 pass, with 0 failures and 0 errors (every test that assumes the data carries a skip marker). The repo-root suite does not depend on the data: 356 passed,
8 skipped (ported dead-by-design code).

**Timing.** The server suite takes about 105 s on the development machine (126 s when another suite runs in parallel); the root suite takes about 5 s. Run either in the background if your tool has a timeout.

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
