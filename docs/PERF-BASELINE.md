# Performance baseline (S00)

Measured 2026-11-16 on the developer's Mac (Apple silicon, Node 22, Python 3.14), on the stack of branches up to S10
(`exec/S10`). Numbers are for comparing "before / after" of later slices, not absolute promises. Commands are given so a
number can be taken again.

## Bundle (offline build)

`cd frontend && npm run build:offline` (the pack must exist: `python scripts/build_offline.py`)

| Item | Size |
|---|---|
| `dist/` total (`du -sk`) | 23 392 KB (about 22.8 MB) |
| service worker precache (`[pwa] sw.js` line) | 34 files, 18.89 MB |
| `assets/index-*.js` | 458 175 B, gzip -9: 137 150 B |
| `assets/index-*.css` | 44 104 B |
| `assets/engine.worker-*.js` | gzip -9: 1 556 B |
| `pyodide/pyodide.asm.wasm` | 9 598 218 B |
| `pyodide/python_stdlib.zip` | 2 545 637 B |
| `pyodide/app.zip` (engine + data, pack of the server code) | 1 830 885 B |
| `pyodide/pyodide.asm.mjs` | 1 250 344 B |
| PDF stack: fonttools, pillow, fonts.zip, pypdf wheels | 1 152 647 + 1 037 806 + 732 749 + 394 327 B |

## Engine start and requests in Pyodide (Node, no browser)

`cd frontend && REQUIRE_PYTHON=1 npx vitest run src/offline/equivalence.test.mjs --disable-console-intercept`
prints a line `offline timings {...}` (two runs; the second one ran while the machine was busy):

| Item | Run 1 | Run 2 |
|---|---|---|
| Pyodide boot to `ready` (`boot_ms`) | 1 094 ms | 3 714 ms |
| boot + packages + app.zip mounted (`ready_ms`) | 1 201 ms | 4 096 ms |
| PDF stack on demand (`pdf_stack_ms`) | 99 ms | 353 ms |
| all 292 golden cases (`golden_s`) | 2.7 s | 8.3 s |
| the fixed request list (`requests_s`) | 7.7 s | 9.0 s |
| one fillable sheet export (`sheet_ms`) | 145 to 987 ms | 309 to 1 421 ms |

## `resolve()` natively

A level 1 fighter (`exportable_draft()` of `server/tests/service_requests.py`), warm, best of 20: 0.8 ms. The 2024 Bard 20
case is bounded by the 50 ms guards in `server/tests` (`perf_helpers.py`).

## Not measured here (needs a person or a device)

- Start of the engine on a phone (instructions: `docs/DEPLOY-PAGES.md`).
- React renders per keystroke when typing in "Name" (needs the React Profiler in a browser). Slice S11 needs this number
  for its "before / after"; until it is taken, S11 proves the change with the unit tests of the debouncing helper.

## After S11 (debounced saving, memoised draft context, no request for an unchanged draft)

What changed, measured by the unit tests rather than a profiler (see "Not measured" above):
- `localStorage` is written once per typing pause (400 ms) instead of once per key: `logic/debouncedSave.test.ts` (a run of
  keystrokes is one save; `pagehide` / `visibilitychange` flush the last text).
- The draft context value is memoised (`DraftContext.tsx`), so consumers of it no longer re-render when only the library
  context re-renders.
- `useResolution` depends on the draft's JSON text: a new draft object with the same content sends no request.
- The index write on each save stays (it also carries `updatedAt`), but it now happens once per pause, not per key.
React renders per key: still to be taken with the React Profiler (before: this branch at `exec/S10`).
