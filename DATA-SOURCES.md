# Data sources

Facts about where the data in this repository came from. This file records provenance only; it makes no legal claims.
The repository is private and the app is shared with a few close friends (as the project owner stated on 2026-11-03).

## SRD data (`chargen/data/srd/`)

Ten JSON files, pulled from the 5e-bits/5e-database repository (branch main, directory src/2014/en/) on
2026-08-24 15:59 UTC. Per-file `url` and `pulled_at` are in `chargen/data/srd/meta.json`; the URL pattern is
`https://raw.githubusercontent.com/5e-bits/5e-database/main/src/2014/en/<file>`:

`5e-SRD-Spells.json`, `5e-SRD-Levels.json`, `5e-SRD-Classes.json`, `5e-SRD-Subclasses.json`, `5e-SRD-Features.json`,
`5e-SRD-Races.json`, `5e-SRD-Subraces.json`, `5e-SRD-Traits.json`, `5e-SRD-Equipment.json`, `5e-SRD-Backgrounds.json`.

The docstring of `chargen/sync.py` describes the source as "the open 5e-bits/5e-database repo (MIT + OGL licensed)".
That is the wording of the code; this file does not verify it.

## Official 5etools data (`server/data/official/`)

40 raw JSON files (5,868,057 bytes) plus `server/data/official/MANIFEST.json`, which records for every file its size,
sha256, record counts, and (where known) url and pull date, and a `bundle_sha256` over all files. The files were
copied byte for byte from the local sync folder (`~/.claude/dnd/.data/official`, filled by `chargen.sync --official`);
the bundle builder is `server/catalog/official/bundle.py`. The upstream repository is 5etools-mirror-3/5etools-src.

### Files with recorded provenance (4)

Pulled from `https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/<file>`:

| File | URL | Pulled at |
|---|---|---|
| `server/data/official/races.json` | https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/races.json | 2026-08-24 23:55 UTC |
| `server/data/official/backgrounds.json` | https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/backgrounds.json | 2026-08-24 23:55 UTC |
| `server/data/official/feats.json` | https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/feats.json | 2026-09-27 19:05 UTC |
| `server/data/official/items-base.json` | https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data/items-base.json | 2026-10-09 09:37 UTC |

These four were fetched from the main branch on the dates shown; the upstream commit was not recorded.

### Files with no per-file url or pull date (36)

The manifest has `url: null` and `pulled_at: null` for these, because the sync folder's metadata does not list them.
Groups:

- `server/data/official/spells/` (19 files: index.json, sources.json and 17 spell books, one per source code in the index)
- `server/data/official/class/` (16 files: index.json and 15 class files)
- `server/data/official/optionalfeatures.json`

Provenance statement, verified on 2026-11-03 by comparing sha256 of these 36 files with the same relative paths under
`~/Documents/5etools-src/data` (a local checkout whose package.json version is 2.25.4 and whose HEAD is the commit below;
all 36 matched; they also match the blobs at that checkout's HEAD commit, git show HEAD:data/<file>): the spells, class and optionalfeatures files are byte-identical to 5etools-src v2.25.4, commit
d2a2616867c2e435b37e465d64cc01e2fc075ace (2026-03-25). The same comparison for the four files with recorded
provenance showed that races.json, backgrounds.json and feats.json differ from that checkout (they come from a
later main), and items-base.json does not exist there.

### Licence as recorded in the 5etools repository

The checkout's LICENSE.md reads "MIT License" with the line "Copyright (c) 2017 TheGiddyLimit and contributors".
The `_meta` blocks inside the data files record no licence.

### Game content and source codes

The game content (races, backgrounds, feats, spells, classes, items) is taken from Wizards of the Coast publications.
The `source` codes found in the vendored records (derived by script from all records of all bundled files):

AAG, ABH, AI, AU, AWM, AitFR-AVT, BGDIA, BGG, BMT, DMG, DSotDQ, EEPC, EFA, EGW, ERLW, FRHoF, FTD, GGR, GoS, IDRotF,
LFL, LLK, LR, MOT, MPMM, MTF, OGA, OotA, PHB, PSA, PSD, PSI, PSK, PSX, PSZ, RHW, SCAG, SCC, SatO, TCE, TTP, ToA,
UATheMysticClass, VGM, VRGR, WBtW, XDMG, XGE, XPHB.

The 17 spell books (index `server/data/official/spells/index.json`) use AAG, AI, AitFR-AVT, BMT, EFA, EGW, FRHoF, FTD,
GGR, IDRotF, LLK, PHB, SCC, SatO, TCE, XGE, XPHB.

## Fonts (`server/assets/fonts/`)

DejaVu Sans fonts used by the PDF export. Their licence text is in `server/assets/fonts/LICENSE`.

## Refreshing the data

See "Refreshing the official data" in `README.md`: `chargen.sync --official --force` (or a 5etools-src checkout), then
`python -m catalog.official.bundle --from <dir>` from `server/`, then the full test suites and the golden. After a
refresh, update the tables above. `server/tests/test_data_sources_doc.py` checks that every path quoted in this file
exists and that every file in the manifest is covered here.
