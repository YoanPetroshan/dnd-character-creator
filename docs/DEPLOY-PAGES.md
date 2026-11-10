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

The installed copy keeps working. In the background the new version downloads only the files that changed (the big
runtime file does not change between normal updates). When it is ready the app shows "Има нова версия на приложението" with
**Обнови сега / Update now**; the new version starts when you press it (the page reloads). The old files are then deleted.
Nothing changes under a person who is in the middle of editing a character.

## Troubleshooting

- **"Двигателят на приложението не може да стартира" / engine unavailable.** The browser has no WebAssembly. On iPhone this
  is **Lockdown Mode** (Settings > Privacy & Security > Lockdown Mode): the app cannot work in it; turn it off for Safari or
  use another device. Otherwise the files did not download: open the app once with a working connection.
- **Data disappeared on iPhone.** Safari clears a website's storage after 7 days without use unless the app is added to the
  home screen. Add it to the home screen and keep a `.json` backup (Home > Изтегли всички).
- **The app does not update.** Close it fully and reopen it with internet; the update prompt appears after the new version
  has downloaded. A stuck copy can be reset: remove the home-screen icon and clear the site's data (Safari: Settings >
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
