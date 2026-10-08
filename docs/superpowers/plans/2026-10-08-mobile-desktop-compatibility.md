# Plan: functional phone (Android/iPhone) + desktop compatibility — NOT visual design

(Opus planner, 2026-10-08. The user will restyle on another platform later: keep CSS structural/minimal. Verify with `cd server && ../.venv/bin/python -m pytest -q`, `cd frontend && npm run build`, and the browser tools (preview_start names "backend" and "frontend-dev"; resize_window presets mobile 375x812 / tablet; custom 360x740; reset with preset "desktop" at the end). Commit per slice, message ending `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.)

## Measured findings
- The ONLY horizontal overflow at 375/360px is `.step-nav` (7 NavLinks reach x=606px → page 605px wide). Everything inside `<main>` fits.
- All inputs/selects/textareas render at 13.33px (index.css never sets a size) → iOS Safari zooms on focus.
- Checkboxes/radios are 13x13px; buttons 22–29px tall (point-buy steppers, item add/remove, export, tab-bar).
- `.app { min-height: 100vh }` only use of vh.
- Viewport meta present (`width=device-width, initial-scale=1.0`), no `viewport-fit=cover`.
- localStorage access in `frontend/src/DraftContext.tsx` already try/catch-safe; iOS may evict after ~7 days (docs only).
- ExportPage.tsx lines ~47–55: fetch → Blob → createObjectURL → `a.download` → `URL.revokeObjectURL(url)` IMMEDIATELY (can break iOS/Android WebView downloads; Safari may ignore `a.download` for PDF/text and navigate away).
- `server/app.py:182` binds 127.0.0.1; CORS hard-coded to http://localhost:5173 (irrelevant: frontend uses relative /api); Vite has no `host`; Flask does not serve `frontend/dist`; app uses BrowserRouter so deep links need SPA fallback.
- PWA: skip (iOS standalone breaks blob downloads; service worker stale-cache risk).

## Slices

### Slice 1 — Flask serves built frontend on one origin
`server/app.py`: `app = Flask(__name__, static_folder=None)`; `DIST = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "dist"`; overridable via `app.config["FRONTEND_DIST"]`. Catch-all registered AFTER all /api routes: `@app.route("/", defaults={"path": ""})` + `@app.route("/<path:path>")`: if path startswith "api/" → `jsonify({"error":"not found"}), 404`; if `(dist/path).is_file()` → `send_from_directory`; elif `dist/index.html` exists → send index.html; else `jsonify({"error":"frontend not built"}), 404`. `__main__`: `app.run(host=os.environ.get("HOST","127.0.0.1"), port=int(os.environ.get("PORT",8000)), debug=os.environ.get("FLASK_DEBUG")=="1")` (default loopback; LAN is opt-in; debug off by default). Leave CORS.
Tests: new `server/tests/test_spa_serving.py` using tmp_path (index.html containing "SPA", assets/a.js), set `app.config["FRONTEND_DIST"]`, reset in teardown: `/` 200 "SPA"; `/class` 200 "SPA"; `/assets/a.js` body; `/api/health` → {"ok": True} (verify the real health route name in app.py); `/api/nope` 404 JSON not HTML; `POST /api/resolve` with `{}` 200.

### Slice 2 — LAN dev option + docs
`frontend/package.json` script `"dev:lan": "vite --host"`. README (or architecture doc) section "Testing on a phone": option A `npm run build` + `HOST=0.0.0.0 ../.venv/bin/python app.py` from server/, open `http://<LAN-IP>:8000` (`ipconfig getifaddr en0`; macOS firewall may prompt); option B `npm run dev:lan` then `http://<LAN-IP>:5173`.

### Slice 3 — step nav overflow
index.css `.step-nav`: `overflow-x: auto; -webkit-overflow-scrolling: touch; flex-wrap: nowrap; scrollbar-width: thin;`; `.step-nav a`: `flex: 0 0 auto; white-space: nowrap; min-height: 44px; display: inline-flex; align-items: center;`. No body overflow-x:hidden. Optional (StepNav.tsx): useEffect on location.pathname → `navRef.current?.querySelector('.active')?.scrollIntoView({inline:'nearest', block:'nearest'})`.
Verify: mobile preset, /home and /export: `document.documentElement.scrollWidth` must equal 375 (was 605); repeat 360x740 and tablet; screenshot.

### Slice 4 — iOS zoom + touch targets (structural CSS in index.css)
`input, select, textarea, button { font-size: 16px; }`; `input[type="checkbox"], input[type="radio"] { width:20px; height:20px; margin:0 8px 0 0; flex:0 0 auto; }`; `.choice-picker li, .picker-list li, .item-browser-list li, .inventory-list li { min-height:44px; display:flex; align-items:center; }` (check real class names in index.css/components first); `label { display:inline-flex; align-items:center; min-height:44px; }` scoped to those lists + `.ability-method-selector` + HomePage fieldsets, NOT all labels; `button, .tab-bar button, .point-buy-stepper button, .choice-card__header { min-height:44px; min-width:44px; }`; `.ability-method-selector { flex-wrap: wrap; }`; `.app { min-height:100vh; min-height:100dvh; }`; ability table wrapper `display:block; overflow-x:auto; max-width:100%;`; `html { -webkit-text-size-adjust:100%; }`; `overscroll-behavior: contain;` on `.item-browser-list`, `.inventory-list`, `.spell-library-list`.
Verify at mobile size on each route (/home /class /background /species /abilities /equipment /export): `[...document.querySelectorAll('input,select,textarea')].filter(e=>parseFloat(getComputedStyle(e).fontSize)<16).length === 0`; count of checkboxes/buttons with `getBoundingClientRect().height < 20` is 0; re-run slice 3 overflow check at 360px on all 7 routes with tab-bar buttons and choice-card headers clicked open.

### Slice 5 — export download robustness (frontend/src/pages/ExportPage.tsx + server)
Replace immediate revoke with `setTimeout(() => URL.revokeObjectURL(url), 60_000)`. Before the anchor path, on touch devices only: `const file = new File([blob], filename, {type: blob.type}); if (navigator.canShare?.({files:[file]}) && matchMedia('(pointer: coarse)').matches) { await navigator.share({files:[file]}); return; }` — catch `AbortError` silently (not shown as exportError). Keep `a.download`; set `a.rel="noopener"`; do NOT set target="_blank". Sanitize filename: `(draft.name || "character").replace(/[\\/:*?"<>|]/g, "_")`. Server `api_export`: add `Content-Disposition: attachment; filename*=UTF-8''<urllib.parse.quote(name)>` header for yaml/markdown/pdf; assert the header in a test (test_app.py or test_export.py).
Verify: desktop Chrome: click each of the 3 export buttons → downloads with correct names; `navigator.canShare` absent on desktop so fallback runs. Manual real-device check on iPhone/Android is left to the user (say so in the report).

### Slice 6 — safe area (cheap)
index.html meta → `width=device-width, initial-scale=1, viewport-fit=cover` (NO maximum-scale/user-scalable=no); add `<meta name="theme-color" content="#eeeeee">`. index.css: `.step-nav { padding-left: max(8px, env(safe-area-inset-left)); padding-right: max(8px, env(safe-area-inset-right)); padding-top: max(8px, env(safe-area-inset-top)); }`, `main { padding-bottom: max(16px, env(safe-area-inset-bottom)); }`. Verify `npm run build`.

### Slice 7 — PWA: SKIP. Final docs: add a short "Mobile/desktop compatibility" section to docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md (what was done, iOS localStorage eviction note, PWA deliberately skipped and why, real-device export check outstanding).
