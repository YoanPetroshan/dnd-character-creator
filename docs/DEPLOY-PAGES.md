# Publishing the app on GitHub Pages (owner steps)

The app is a static site: the character engine runs inside the browser (Pyodide), so no server is needed. GitHub Pages
hosts it for free from the public repository. Everything is built by `.github/workflows/pages.yml`.

Address after the first deploy: **https://yoanpetroshan.github.io/dnd-character-creator/**

## One-time setup (you do these; nothing here is automated)

1. Make the repository public: GitHub > repository `dnd-character-creator` > Settings > General > Danger Zone >
   Change visibility > Make public. (GitHub Pages on a private repository needs a paid plan.) Before you do: the repository
   holds the official D&D data files the app bundles (`server/data/official`); anything in the history is public from then
   on. Check you are comfortable with that.
2. Settings > Pages > Build and deployment > Source = **GitHub Actions**.
3. Push to `main` (or Actions > pages > Run workflow). The `pages` workflow builds the site and deploys it. The first run
   asks you to approve the `github-pages` environment if protection rules are on; the default needs nothing.
4. Open the address above. The first visit downloads the app (see "Size") and shows "Готово: приложението работи и без интернет".

## How to update

Push to `main`. The `pages` workflow rebuilds and redeploys (about 3-5 minutes). Nothing is uploaded by hand. If the
change touches `server/` or `chargen/`, the pack is rebuilt in CI from the repository, so the site always matches `main`.
`ci.yml` (tests) is separate; Pages does not wait for it, so push only what is green locally (or use Run workflow on a
commit you checked).

## What friends do

- **iPhone / iPad:** open the address in **Safari**, tap the Share button, **Add to Home Screen**, Add. Start the app from
  the icon. The first start needs internet; after that it works in airplane mode.
- **Android:** open it in Chrome, menu (three dots) > **Install app** (or Add to Home screen).
- **Computer:** Chrome or Edge, install icon in the address bar, or just use a tab.

The same steps are in the app under **Помощ / Help** (header). Characters are stored only on the device; the app tells
people to download a backup (Home > "Изтегли всички (.json)"). iOS may delete a website's data after 7 days without use
unless the app was added to the home screen.

## Size

First download: about **18.3 MB** of files (the app 0.5 MB, the engine runtime and the Python standard library about 12 MB,
the engine code and data 1.8 MB, the PDF support and fonts about 4 MB); GitHub Pages compresses text-like files, so the
transfer is smaller (about 11 MB measured as gzip locally, not measured on Pages). It is downloaded once, in the background,
while the app is already usable online.

## What happens on an update

The installed copy keeps working while the new version downloads in the background (only the changed files; the big runtime
file does not change between normal updates). The new version is applied **by itself** when the app is opened, or shown
again after being in the background (a 60-second window after that; it checks `sw.js`, which the browser never takes from
its HTTP cache), and the page reloads once. A download that began inside the window keeps the right to apply itself when it
ends, even on a slow network (the window restarts when the version is ready); one that began later waits for the next open. The characters are not touched: they live in the browser's `localStorage`,
which a service worker or cache update never clears, and every change is written to it at once.

It is **not** applied silently when data could be at risk. Then the banner "update-needs-backup" asks the person to press
"Изтегли всички герои (.json)" first, and only then enables "Обнови сега". That happens when:

1. **The storage schema differs.** `frontend/src/storageSchema.json` holds a number that goes into `dist/sw.js`. Raise it by
   one in any release whose code cannot read what an older release stored (a new `DRAFT_VERSION` or library `version`
   without a lossless migration), or whose data an older release cannot read. The page asks the waiting worker for its
   number (`GET_VERSION`); a worker that does not state one counts as different. `pwa/storageSchema.test.ts` pins what each number
   stands for (draft version and storage keys) and fails when a format changes without the number being raised.
2. **The last save failed** (full or blocked storage): that draft exists only in memory and a reload would lose it.

Other rules: the first update after this feature is installed still needs the button (the old page has no such code); an
update found while the person is already working waits (button) and is applied at the next open; a reload guard
(`sessionStorage`, 30 s) prevents loops. Logic: `frontend/src/pwa/register.ts`; tests: `register.test.ts`, `sw.test.mjs`,
`precache.test.mjs`, `offline/precache.dist.test.mjs`.

### Manual check after a deploy (two versions needed)

1. On a phone/browser open the live address once (version A), wait for "Готово", create a character with a name.
2. Push a visible change (e.g. a text) so Pages deploys version B. Wait for the `pages` workflow to finish.
3. Close the app fully (or switch away for a minute), open it again with internet. Expected: for a few seconds A, then one
   reload to B, without a button; the character is still there. DevTools > Application > Cache Storage shows only the new
   `dnd-builder-precache-<version>` cache.
4. Backup path: deploy a version C with `storageSchema.json` raised by one. Open the app on B: the banner asks for the
   download, "Обнови сега" is disabled until the file is made; after the download press it, the app reloads to C. Check the
   characters exist (if not: Home > upload the file).
5. Airplane mode after step 3: the app still opens (offline). In DevTools, with "Offline" on, reopen: no error.
6. Full-storage case (optional): fill `localStorage` (DevTools console) until a save fails, then deploy a new version: the
   banner must ask for the backup even with the same schema.

## Troubleshooting

- **"Двигателят на приложението не може да стартира" / engine unavailable.** The browser has no WebAssembly. On iPhone this
  is **Lockdown Mode** (Settings > Privacy & Security > Lockdown Mode): the app cannot work in it; turn it off for Safari or
  use another device. Otherwise the files did not download: open the app once with a working connection.
- **Data disappeared on iPhone.** Safari clears a website's storage after 7 days without use unless the app is added to the
  home screen. Add it to the home screen and keep a `.json` backup (Home > Изтегли всички).
- **The app does not update.** Close it fully and reopen it with internet; the update is applied by itself after it has
  downloaded (or the banner asks for a backup first). A stuck copy can be reset: remove the home-screen icon and clear the site's data (Safari: Settings >
  Safari > Advanced > Website Data > search "github.io" > delete; Chrome: site settings > Clear data) then open the
  address again. This also deletes the characters stored in the browser: download them first.
- **Deep links (a page address typed directly) show a blank flash.** GitHub Pages answers unknown paths with `404.html`,
  which is a copy of the app, so it still loads; this is expected.
- **The `pages` workflow fails at `build_offline.py`.** A pinned download changed or is unreachable (the script verifies the
  size and sha256 of every file and stops): run `.venv/bin/python scripts/build_offline.py` locally; see the README, "Offline pack".
- **Wrong address / blank page.** The site must be opened under `/dnd-character-creator/`. If the repository is renamed, change
  `VITE_BASE` in `.github/workflows/pages.yml` (and `.github/workflows/ci.yml`, `tests/test_ci_workflow.py`).

## Local rehearsal (no GitHub)

    .venv/bin/python scripts/build_offline.py
    cd frontend
    VITE_BASE=/dnd-character-creator/ VITE_SERVERLESS=1 npm run build:offline
    npx vite preview --base /dnd-character-creator/ --port 4180
    # open http://localhost:4180/dnd-character-creator/ ; stop the server afterwards

The service worker only works on `localhost` or HTTPS.
