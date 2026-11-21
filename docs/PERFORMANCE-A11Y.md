# Speed and accessibility check (2026-11-21)

## Speed

What the first visit downloads (offline build, `scripts/build_offline.py` + `npm run build:offline`):

| Part | Size | Compressed | Needed for the first screen |
|---|---|---|---|
| Page: `index-*.js` + `index-*.css` | 504 KB + 64 KB | 153 KB + 12 KB | yes (a single JS chunk) |
| Fonts (Golos, Piazzolla), 10 files | ~150 KB | | swap, so text shows at once |
| Engine: `pyodide.asm.wasm` + `.mjs`, `python_stdlib.zip`, lock, `pyyaml` | ~13 MB | ~6.2 MB | yes (the first calculation waits for it) |
| `app.zip` (the Python engine and the data, with the Bulgarian texts) | 2.75 MB | 2.74 MB (already a zip) | yes |
| PDF stack (`fonts.zip`, `fpdf2`, `pillow`, `fonttools`, `pypdf`, `defusedxml`) | ~3.6 MB | | no, only for the first PDF export |
| Everything the service worker precaches | 19.95 MB (34 files) | ~12.3 MB | no, it is for offline use |

Finding: the service worker used to start its 20 MB precache at the same time as the engine's own downloads, so on a first
visit the two competed for the same bandwidth and the engine (the thing the user waits for) came later than it had to.
Change: `main.tsx` now starts the service worker only when the engine has booted (or after 45 s): `whenEngineSettled`
(`api/whenEngineSettled.ts`, with tests). The worker's `no-cache` fetches then find the files the page already downloaded
(a 304) instead of downloading them a second time.

Not changed (measured as small next to the 13 MB engine): splitting the 504 KB script into page chunks (about 50-100 KB
saved), preloading the engine files (the worker starts about 60 ms after the page script).
Not measured: a real cold start on a slow phone network (the pane has the files cached after the first visit); please try
the first open on mobile data once.

## Accessibility

Checked with axe-core 4.10 (WCAG 2.x A/AA and best practices) on Home, Class (cards open, "Available at higher levels" open),
Background, Species, Abilities, Equipment, Sheet and Help, in the light theme at desktop width and in the dark theme at 375 px.
Found and fixed:

- `region` (every page): the "Next unfinished step" and "New choices" links were outside a landmark. They are `<nav>` now
  with the label "Next step".
- `list` (Species): the group headings were `<li role="presentation">`. Now plain `<li>`.
- `definition-list` (Sheet): the hit-dice line was a `<span>` inside the definition-list group. Now a `<dd>`.
- `color-contrast` (Sheet, dark theme, 8 places): section titles used the border green (4.1:1). They use the label colour now
  (the light theme looks the same: both are the same green there).

After the fixes axe reports no violation on any of these pages in either theme. The page language switches with the
language button (`<html lang>`), the focus rules exist, and no page scrolls sideways at 375 px.

Not checked: a real screen reader (VoiceOver / TalkBack), the contrast of the print theme.
