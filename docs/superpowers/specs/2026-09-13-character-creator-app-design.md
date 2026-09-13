# Character Creator App — Design

**Goal:** A fully standalone application for creating D&D 5e characters, split
out of `dnd-app-bg-local`'s play app, producing a canonical YAML character
sheet plus PDF and Markdown exports — usable with or without the AI DM.

**Architecture:** A thin Flask app wrapping the already-isolated `chargen`
rules/content engine (ported verbatim, zero changes). Three export formats
share one canonical in-memory `sheet` dict: YAML (the format the play app
already reads), a fresh Markdown renderer, and a PDF filled into the official
Wizards of the Coast fillable character sheet via `pypdf`.

**Tech Stack:** Python 3, Flask, flask-cors (optional, for future cross-origin
calls from the play app), PyYAML, pypdf. No frontend framework — `builder.html`
is a single self-contained file (inline CSS/JS), same pattern as the source repo.

## Global Constraints

- **No dependency on the play app's engine.** Nothing may `import` from
  `char_state_schema`, `char_state_sync`, `char_state_derive`, `character`,
  `lookup`, or any other module that lives in `dnd-app-bg-local`'s
  `skills/dnd/scripts/`. Those modules assume a live campaign/engine context
  this app does not have. `chargen/` itself already follows this rule
  ("imports nothing outside chargen and the standard library") — every new
  module in this app follows the same rule.
- **The YAML sheet shape is the one `chargen.build()` already produces** — the
  same shape `skills/dnd/scripts/library.py` in the source repo saves and the
  running game reads (confirmed in `chargen/build.py`'s docstring). Do not
  invent a new/different character schema.
- **AC and other derived combat/play stats are not stored on the sheet** —
  `chargen.build()` deliberately omits them (the play engine derives them
  live from equipped gear). This app needs some of them for a complete
  printed sheet (AC, passive perception, skill/save bonuses, spell save DC),
  so it computes them itself in a **small, new, dependency-free module**
  (`sheet_derive.py`) — not by porting `char_state_derive.py`, which would
  drag in the play engine's dependency chain. Reimplement the handful of
  needed 5e SRD formulas fresh, from `chargen`'s own catalog/model data.
- **The PDF template is the official Wizards of the Coast fillable 5e
  character sheet**, downloaded from
  `https://media.wizards.com/2022/dnd/downloads/DnD_5E_CharacterSheet_FormFillable.pdf`
  and committed at `assets/character-sheet-template.pdf`. Its 334 AcroForm
  field names were inspected directly (via `pypdf.PdfReader.get_fields()`)
  and confirmed to match the field-name convention already assumed by the
  source repo's `sheet_import.py` (`CharacterName`, `ClassLevel`, `HPMax`,
  `STR`, etc.) — extend that same `_PDF_MAP`-style convention in reverse
  (fill instead of read), don't invent new field names.
- **Markdown export is a fresh renderer**, not a port of the source repo's
  `library.py::_render_markdown()`. That function is a fragile bridge into
  the play engine's `char_state_sync.render_markdown()` with a bare-bones
  fallback — exactly the coupling this app avoids per the constraint above.
- **No campaign integration in this phase.** No `copy_to_campaign` /
  `import_from_campaign` equivalent, no linking back to the play app's
  campaign structure, no `/menu` or "back to the game" links in the ported
  `builder.html` (those pages don't exist here). This is explicitly deferred
  to a future phase where the play app is wired to consume this app's output.
- **Character storage is local to this app**: a `library/` directory at the
  repo root (or `DND_CHARACTER_ROOT` env override), one subdirectory per
  character, holding `character.yaml` + generated `character.md` +
  `character.pdf`. Not the source repo's campaign-rooted library layout.

## Components

### 1. `chargen/` (ported, unchanged)

Copied verbatim from `dnd-app-bg-local/chargen/`: `catalog.py`, `model.py`,
`normalise.py`, `rules.py`, `validate.py`, `build.py`, `sources.py`, `sync.py`,
`cli.py`, `__main__.py`, `__init__.py`, and its bundled `chargen/data/srd/*`
(the same 1.6MB of SRD JSON — races, classes, spells, equipment, backgrounds,
features, levels, subclasses, subraces, traits). Zero code changes — this
package already has zero dependencies outside the standard library.

### 2. `app.py` — the thin Flask shell

Routes (same shape as the source repo's `/api/chargen/*`, minus anything
campaign-related):

- `GET /` → renders `builder.html`
- `GET /api/chargen/catalog`
- `GET /api/chargen/spells`
- `GET /api/chargen/equipment`
- `POST /api/chargen/preview` — calls `chargen.build.build(draft)`, returns
  `(sheet, problems, warnings)` without saving (same as source)
- `POST /api/chargen/build` — calls `build()`, and on success:
  1. computes derived print stats via `sheet_derive.py`
  2. saves `library/<slug>/character.yaml`
  3. renders and saves `library/<slug>/character.md`
  4. fills and saves `library/<slug>/character.pdf`
  5. returns `{ok, warnings, yaml_path, md_path, pdf_path}`
- `GET /api/characters` — list saved characters (name, race/class/level, path)
- `GET /api/characters/<slug>/<fmt>` — download one export (`yaml`/`md`/`pdf`)

### 3. `templates/builder.html` (ported, trimmed)

Copied from the source repo's `skills/dnd/display/templates/builder.html`.
Changes:
- Remove the three links to `/menu` and `/` (the play app's pages — they
  don't exist in this repo). Replace with nothing, or a static "character
  saved — see the library" confirmation state after a successful build.
- Everything else (the 7-step stepper, its JS calling `/api/chargen/*`,
  its inline CSS) stays as-is — it already only talks to endpoints this app
  provides.

### 4. `sheet_derive.py` — new, small, dependency-free

Pure functions operating on a `chargen.build()` sheet dict plus the
`chargen.catalog.Catalog` (for class/race data already loaded for that
build), computing exactly what a printed sheet needs that the sheet doesn't
store:
- `armor_class(sheet) -> int` — 10 + Dex mod + equipped armor bonus + shield,
  reading the `equipment` list's `equipped: True` items (mirrors what the
  source repo's `compute_ac()` does, reimplemented standalone)
- `proficiency_bonus(level) -> int` — standard 5e table
- `skill_bonuses(sheet) -> dict[str, int]` — ability mod + proficiency (if
  proficient) per skill
- `save_bonuses(sheet) -> dict[str, int]` — ability mod + proficiency (if
  proficient) per saving throw
- `passive_perception(sheet) -> int`
- `spell_save_dc(sheet) -> int | None`, `spell_attack_bonus(sheet) -> int | None`
  (only when the class casts spells)

### 5. `markdown_render.py` — new

Renders a `chargen.build()` sheet (plus `sheet_derive` outputs) into a clean
Markdown character sheet: identity, ability scores + mods, saves, skills, AC/
HP/speed/initiative, proficiencies & languages, equipment, features & traits,
spells (if any). Self-contained — takes plain dicts in, returns a string.

### 6. `pdf_fill.py` — new

Fills `assets/character-sheet-template.pdf` using `pypdf.PdfWriter`'s
`update_page_form_field_values()`. Field-name map extends the source repo's
`_PDF_MAP` convention (same names, same lookup style: lowercase + strip
spaces) to cover, in addition to the identity/ability fields already mapped
there:
- `AC`, `Initiative`, `Speed`, `PP` (passive perception), `ProfBonus`
- Per-skill fields (`Acrobatics`, `Athletics`, ... — 18 skill fields) and
  per-save fields (`ST Strength`, `ST Dexterity`, ...)
- `Equipment`, `Features and Traits`, `ProficienciesLang`, `PersonalityTraits `,
  `Ideals`, `Bonds`, `Flaws`, `Backstory`
- Spellcasting fields (`Spellcasting Class 2`, `SpellcastingAbility 2`,
  `SpellSaveDC  2`, `SpellAtkBonus 2`, `Spells 10xx` slots) — only populated
  for casters; left blank otherwise, matching how the blank form behaves.

### 7. `requirements.txt`

```
flask
flask-cors
PyYAML
pypdf
```

## Testing

- Port the source repo's 7 existing `chargen` test files verbatim:
  `test_chargen_sync.py`, `test_chargen_catalog.py`, `test_chargen_rules.py`,
  `test_chargen_cli.py`, `test_chargen_build.py`, `test_chargen_normalise.py`,
  `test_chargen_isolation.py` (the last one specifically enforces the
  "chargen imports nothing outside chargen + stdlib" rule — keep it, it's
  exactly the invariant this whole design leans on).
- New unit tests for `sheet_derive.py` (known ability-score/level/equipment
  combos → expected AC/skill/save numbers), `markdown_render.py` (snapshot-
  style: known sheet in → expected Markdown substrings out), and `pdf_fill.py`
  (fill a sheet, re-read the PDF's fields with `pypdf`, assert values match).
- Integration test: `POST /api/chargen/build` with a full legal draft →
  assert all three files exist on disk and are non-empty/parseable.

## Explicitly out of scope (this phase)

- Any link back to `dnd-app-bg-local` (no shared HTTP calls, no shared
  filesystem paths, no campaign linking).
- Multiclassing, Warlock pact magic slots — same scope limits `chargen.build()`
  already documents.
- Syncing "official" (non-SRD) supplemental content
  (`chargen.sync --official`) — SRD-only content for now.
- A 2024-ruleset PDF template — the downloaded template is the 2014-ruleset
  official sheet, matching what `sheet_import.py` already assumes. Revisit
  if/when 2024-ruleset characters need their own export.
