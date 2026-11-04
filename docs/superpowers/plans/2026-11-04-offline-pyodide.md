# Plan: offline engine in the browser (Pyodide in a Web Worker, PWA)

Opus feasibility spike of 2026-11-04 (nothing changed in the repo; prototype and measurements in the scratchpad `offline-spike/`). Result: **GO**.

## Requirement and decisions

The user (2026-11-04): the app MUST WORK OFFLINE on the devices (the user has an iPhone, no Android; friends may have either). Link sharing is cancelled (sharing is by file). Hosting is a static HTTPS site (no server needed); the Flask server stays as the dev/LAN option and the reference implementation for tests.

Decisions needing the user (recommended defaults, executors use the defaults unless told otherwise): (1) static host: Cloudflare Pages or Netlify (GitHub Pages on a private repo needs a paid plan); (2) Flask stays for dev/LAN and tests: yes; (3) first download about 7.3 MB plus about 3 MB on the first PDF: acceptable; (4) precache the PDF stack for full offline from day one: yes by default (about 10.5 MB total), load lazily only if the user prefers a smaller first download; (5) Pyodide upgrades only deliberately, pinned, golden-checked; (6) a draft export/backup reminder because iOS can evict Safari storage after 7 days without use unless the PWA is installed to the home screen.

## Spike results (measured)

- The unchanged engine, catalog and exports run under Pyodide 314.0.7 (CPython 3.14.2) and match native: 251/251 golden cases (canonical JSON with STRIP applied) in Node and in a browser Web Worker; YAML and Markdown byte-identical for 5 kitchen-sink drafts; PDF identical after normalising CreationDate and the `/ID`.
- Imports: engine and catalog are stdlib-only (they need `chargen/{__init__,sources}.py` and `chargen/data/srd` shipped too); exports need pyyaml, fpdf2 + Pillow + fonttools + defusedxml. Pyodide ships pyyaml, pillow, fonttools; fpdf2 and defusedxml are pure-Python wheels bundled locally (micropip not needed). pypdf is tests-only.
- Sizes: Pyodide core + pyyaml about 5.6 MB (brotli), engine+catalog+data+fonts `app.zip` 2.4 MB (1.7 MB without fonts), PDF stack 2.5 MB. First download about 10.5 MB (7.3 MB without PDF stack and fonts).
- Speed: cold start to first resolve about 1.55 s in Node and 5-6.5 s in a (hidden-pane, likely throttled) Chromium worker; warm resolve about 7.5-12 ms (2.1-2.2x native); one PDF 104-123 ms; WASM heap 108-130 MB. iPhone cold start is unmeasured (guess 2-6 s): the UI needs an "engine starting" state.
- iOS rules (not measured): module Web Workers and WASM need Safari 15+; **Lockdown Mode disables WebAssembly** (the app cannot work there); Safari evicts script-writable storage (Cache Storage, IndexedDB, service worker, localStorage) after 7 days without use unless the PWA is added to the home screen (so "install to home screen" is part of the instructions; call `navigator.storage.persist()`); HTTPS and `application/wasm` required; Workbox/vite-plugin-pwa default `maximumFileSizeToCacheInBytes` is 2 MiB and must be raised for the 9.6 MB wasm.
- Alternatives rejected: port to TypeScript (25,871 lines of engine+catalog, 47k lines of Python tests; months; two engines drift), Capacitor/native wrapper (paid Apple program for sharing), cached server responses (impossible: resolve takes a new draft each time).

## Integration surface

The SPA calls: POST /api/resolve (useResolution.ts), GET /api/catalog (useCatalog.ts), GET /api/catalog/class/<id> (ClassPage.tsx), GET /api/items (useItems.ts), GET /api/spells and /api/spells/<id> (useSpells.ts), POST /api/export/{yaml,markdown,pdf} (ExportPage.tsx). Adapter: `frontend/src/api/transport.ts` exports `apiFetch(input, init) => Promise<Response>` with fetch's signature; implementations: plain fetch (dev/Flask) and a worker transport that posts `{method, path, query, body}` and builds a real `Response`; only the 7 call sites change. Python side: extract every route body of `server/app.py` into a framework-free `server/service.py`: `handle(method, path, query, body) -> (status, content_type, headers, body_bytes)` reproducing Flask details (jsonify defaults sort_keys=True/ensure_ascii=True; `_json_draft` rules; 404 for unknown ids and /api paths; 400 when `level` is not an integer; JSON 500 for unhandled exceptions); Flask keeps the 1 MB limit (413), CORS, static SPA serving and the startup log line.

## Slices (Sonnet executes one at a time; TDD; gates after each; golden untouched)

- **O0 service extraction:** `server/service.py`, thin `server/app.py`, `server/tests/test_service.py` (every endpoint through `service.handle` equals the Flask test client byte for byte incl. error cases). All existing tests green.
- **O1 offline build + Node equivalence:** `scripts/build_offline.py` builds `app.zip` (no `__pycache__`; fonts split out) and fetches the pinned Pyodide files and wheels into `frontend/public/pyodide/` (gitignored, sha256-pinned); Node golden test (251 cases, 5 export drafts, `service.handle` equality for a fixed request list); sizes printed. Also a throwaway page to measure cold start on the user's iPhone.
- **O2 worker + transport:** `frontend/src/api/{transport,workerTransport}.ts`, `frontend/src/engine.worker.ts`; 7 call sites to `apiFetch`; vitest for the Response mapping; the app works with the dev server stopped; 30 s timeout starts after engine boot; abort drops the reply.
- **O3 lazy PDF (or precache) with a progress state.**
- **O4 PWA:** manifest, icons, service worker precache with version busting and the raised size limit, `storage.persist()`, update prompt, "engine starting" state, fallback to fetch when WASM is unavailable; install-to-home-screen instructions; airplane-mode check on an iPhone.
- **O5 hosting + CI:** static deploy (host per decision 1) and GitHub Actions jobs (Node equivalence test, precache manifest lists every file, wheel sha256 pins).

Risks: iOS cold start (unmeasured), Lockdown Mode, storage eviction (drafts share it: export reminder), Pyodide upgrades changing output (pin + golden), Pillow/fonttools skew in PDFs (zero difference today), first download size, Python updates reaching installed devices only through a service-worker update flow.
