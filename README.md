# D&D Character Creator

A web app that builds D&D 5e (2014 SRD) characters and exports them as YAML,
Markdown or PDF. The UI and the Markdown/PDF exports are in Bulgarian.

There are two generations of code in this repo:

- **v2 builder (current)**: `server/` (Flask JSON API + engine) and
  `frontend/` (React/TypeScript, Vite). The character being built is a
  *Draft* kept in the browser (`localStorage` key `dnd-builder-draft-v2`);
  every change is sent to `POST /api/resolve`, which returns the finished sheet,
  the open choices and any problems. Nothing is stored on the server.
- **v1 (legacy)**: the repo-root `app.py`, `storage.py`, `sheet_derive.py`,
  `markdown_render.py`, `pdf_fill.py`, `templates/`, `static/`. Not used by v2;
  kept for reference (it serves on port 5300). `chargen/` holds the bundled SRD
  JSON (`chargen/data/srd/`) and the official-data helpers that v2 reads too.

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

## Testing on a phone

Phone and computer must be on the same Wi-Fi. Find the computer's LAN IP with
`ipconfig getifaddr en0` (macOS may show a firewall prompt).

- One origin (closest to production): build the frontend, then
  `cd server && HOST=0.0.0.0 ../.venv/bin/python app.py` and open
  `http://<LAN-IP>:8000`.
- Hot reload: run the backend with `HOST=0.0.0.0` as above, then
  `cd frontend && npm run dev:lan` and open `http://<LAN-IP>:5173`.

The draft lives in the phone browser's `localStorage`, which iOS Safari may evict
after about a week of inactivity: use "Download draft" on the home page to keep a
copy, and "Upload draft" to restore it. Exports download through the browser.

## Test

    # v2 server (the main suite)
    cd server && ../.venv/bin/python -m pytest -q
    # repo-root tests (v1 engine + the import-isolation guard that covers server/ too)
    .venv/bin/python -m pytest -q tests
    # frontend: type-check and build (there is no frontend test runner)
    cd frontend && npm run build

Some server tests only run when the official data has been synced (see Setup).
