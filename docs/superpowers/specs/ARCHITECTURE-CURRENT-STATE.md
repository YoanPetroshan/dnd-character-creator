# dnd-character-creator v2 — Current State Overview

**Written:** 2026-09-21, at the close of Phase 3b-i (multiclassing core).

**Audience:** a fresh reader — human or AI — with zero session history on this project. This is a snapshot, not a changelog: it describes what the app IS right now, not how it got here. For history, read `docs/superpowers/specs/*-design.md` (one per phase, dated) and `docs/superpowers/plans/*.md` (one implementation plan per phase). For the original ground-up architecture decisions, read `docs/superpowers/specs/2026-09-16-builder-v2-architecture.md` first — this document assumes you've read that or will, and only restates what has since changed or been added.

**Why this document exists:** the user wants periodic snapshots like this one so that if they switch to a different AI assistant (or just come back after a long gap), the new reader can get oriented without re-deriving the whole project from dozens of individual phase specs, plans, and ledgers.

---

## What this app is

A from-scratch rebuild of a D&D 5e (2014/SRD 5.1 ruleset) character-creator web app. Separate repo from an earlier "v1" (a different, older character builder in a sibling repo, `dnd-app-bg` — not this one). Python/Flask backend, React/TypeScript (Vite) frontend, no database — the character being built lives entirely in the browser's `localStorage` as a JSON "Draft," and the server is a pure, stateless function: `POST /api/resolve` takes a Draft, returns a fully-computed "Resolution" (derived stats, resolved choices, problems, warnings). Every screen re-POSTs the whole Draft and re-renders from the fresh Resolution — there is no incremental/patch API.

## Core data flow

```
Draft (JSON, in browser localStorage)
  → POST /api/resolve
  → resolve(draft, catalog) in server/engine/resolve.py
  → Resolution: { sheet, choices, derived, problems, warnings, pruned }
  → rendered by the frontend, or fed into an export renderer
```

- **`Draft`** (`frontend/src/types.ts`): what the player has chosen so far. Includes `name`, `sources`, `preferences` (hitPointType/advancementType/usePrerequisites), `classes: ClassSelection[]` (now a real array — see Multiclassing below), `background`, `species`, `abilities`, `equipment`, `details`.
- **`Resolution`**: `sheet` (the finished character — name/level/classes/background/species/abilities/proficiencies/equipment/spells/details), `choices` (every pending-or-resolved Choice, generic across every source), `derived` (ability modifiers, prof bonus, HP, AC, saves, skills, passive perception, spell DC/attack), `problems` (blocking issues — e.g. unknown class, over-selected choice), `warnings` (non-blocking — e.g. an equipment envelope that couldn't be represented), `pruned` (reserved for Phase 3c, currently always `[]`).
- **The generic Choice model**: every player decision — a class skill pick, a spell choice, an ASI, starting equipment — is represented the same way: `{id, source, label, description, count, options, selected, status}`. `resolve()` builds a `choice_templates` list from every source (class/background/species/equipment/ASI/spells), then applies whatever the Draft already submitted to produce the final `choices` list. The frontend's `<ChoiceCard>`/`<ChoicePicker>` components render ANY choice generically — new choice-producing features (like multiclass proficiency choices) need zero new frontend rendering code, only a new template-building function on the backend.

## Where the rules data comes from

`server/catalog/loader.py` loads the bundled SRD JSON (`chargen/data/srd/*.json` — the SAME data files the OLD "v1" `chargen` module uses, ported verbatim in Phase 1, never modified) into a `Catalog` dataclass: `classes`, `levels`, `features`, `subclasses`, `races`, `subraces`, `traits`, `backgrounds`, `items`, `spells` — each indexed by its SRD `index` field. This is the ONLY data source right now — no other sourcebooks, no 5etools adapter, no 2024-ruleset content (all planned for Phase 4, not started).

Where the bundled SRD data doesn't structurally carry an answer the engine needs (e.g. which ability governs which skill, which classes are half-casters), `server/catalog/reference_data.py` hardcodes it as an open 5e RAW fact, always with a comment explaining why it couldn't be read from the data.

## Backend layout (`server/`)

- `app.py` — Flask routes: `/api/health`, `/api/resolve`, `/api/catalog` (+ per-class/background/species detail endpoints), `/api/items`, `/api/spells`, `/api/export/<fmt>` (yaml/markdown/pdf, one parameterized route).
- `catalog/loader.py`, `catalog/choices.py` (generic `build_choice_template`/`build_choice_options` — turns a raw SRD "choose N from X" envelope into a Choice template, handling every `option_type` shape the bundled data uses: `reference`, `counted_reference`, `string`, `multiple`, `ability_bonus`), `catalog/reference_data.py`.
- `engine/resolve.py` (~1000 lines — the heart of the app, see below), `engine/derived.py` (pure HP/modifier/save/skill math, no I/O), `engine/asi.py` (pure ASI combination math), `engine/equipment.py`, `engine/spells.py`.
- `export.py` (YAML), `markdown_export.py`, `pdf_export.py` (via `fpdf2`, with a bundled DejaVu Sans font for Cyrillic support — the UI and exports are Bulgarian-language).
- `tests/` — pytest, run via `server/.venv/bin/python -m pytest`. Currently 273 tests, all passing. A separate repo-root test (`tests/test_chargen_isolation.py`) enforces that nothing outside `chargen/` (the ported v1 engine) or the declared dependencies ever imports the OLD v1 play-engine modules — this has bitten the project twice before and is checked on every phase.

### `resolve()`'s shape (the single most important function in the app)

Roughly: validate/normalize the Draft → resolve species/background/race → compute final ability scores (base + species bonuses + any Half-Elf-style ability choice + ASI progression, threaded per-class in array order) → **loop over every class in `draft.classes`** building each one's own choice templates (features, ASI, spell choices — reusing the same per-class helper functions Phase 3a built, now called once per class instead of once total) → apply background/species/equipment choice templates → resolve every choice against the Draft's submitted selections (with deduplication) → compute `derived` stats (prof bonus from TOTAL character level, HP via `hit_point_max_multiclass` which correctly applies "only your very first class's level 1 ever takes the max hit die") → assemble `sheet` (with `sheet["classes"]` as a list, one entry per class, `sheet["spells"]` as a list, one entry per resolved caster).

An `alias block` pattern is used throughout: a `primary`/`cls`/`cls_id` etc. alias always points at `resolved_classes[0]` for the (still-single-computation) parts of the pipeline — background/species resolution, starting equipment (never multiclassed), saving-throw proficiencies (RAW: primary-class-only).

## Frontend layout (`frontend/src/`)

- `App.tsx` mounts `CatalogProvider` (shared `/api/catalog` fetch, hoisted so 3 pages don't each fetch it separately) wrapping `ResolutionProvider` (calls `/api/resolve` on every Draft change) wrapping `DraftProvider` (the `useReducer`-based Draft state, persisted to `localStorage`) wrapping the routed pages.
- `DraftContext.tsx` — the reducer. Every mutation is a plain action (`SET_NAME`, `SET_CLASS`/`ADD_CLASS`/`REMOVE_CLASS`, `SET_CLASS_LEVEL`/`SET_SUBCLASS`/`SET_HP_ROLL` (all now `classId`-scoped since multiclassing), `SET_ABILITY_METHOD`/`SET_ABILITY_SCORE`, `SET_DETAIL`, `SET_CHOICE_SELECTION`, equipment actions, preferences actions).
- Pages: `HomePage` (name + preferences), `ClassPage` (one "class block" per selected class + "+ Add Another Class", per Phase 3b-i), `BackgroundPage`, `SpeciesPage`, `AbilitiesPage`, `EquipmentPage`, `ExportPage`.
- `types.ts` — hand-written TypeScript types mirroring the backend's actual `Resolution`/`Draft`/`Sheet`/`Derived` shapes (kept manually in sync, not code-generated — this has been a recurring source of "stale type" bugs across phases, since nothing enforces the mirror).
- No test framework configured for the frontend. Verification is `npm run build` (`tsc -b && vite build`) plus manual/browser verification for anything UI-behavioral.

## What's implemented vs. not, against the original phasing

(See `docs/superpowers/specs/2026-09-16-builder-v2-architecture.md` §10 for the original phase plan.)

**Done:**
- Phase 0 (skeleton), Phase 1 (vertical slice — level 1, single class, class/background/species/abilities).
- Phase 2a-g (completeness): starting equipment, spellcasting, derived combat stats, YAML export, Markdown export, PDF export, character notes/details.
- Phase 3a: single-class leveling 1-20, subclasses, ASI.
- Phase 3b-i: multiclassing CORE — multiple classes, independent per-class progression, total-level-derived stats (prof bonus, HP), multiclass proficiency grants/choices, prerequisite enforcement, breaking `sheet.classes`/`sheet.spells` shape changes, full frontend multi-class UI.
- A large ad hoc cleanup pass (mid-September 2026): fixed several backend correctness bugs found by earlier phases' final reviews (species languages/proficiencies dropped from the sheet, Half-Elf permanently unexportable, duplicate choice selections not deduplicated, equipment envelope drops never signaled), two frontend cleanups (typed `Resolution.sheet`/`derived` properly, hoisted the catalog fetch into a shared provider), and a Preferences UI on the Home page (unlocking the manual-HP-roll UI that had been built but unreachable since Phase 3a).

**Not yet started:**
- **Phase 3b-ii**: the combined multiclass spell-slot table (shared slot pool across full/half casters, computed from combined caster level; Warlock's Pact Magic stays separate per RAW). `derived.spellSaveDC`/`spellAttackBonus` are still single scalars (primary-class-only) — this will need reshaping into per-caster values, deliberately deferred rather than done twice.
- **Phase 3c**: pruning warnings (when leveling down or switching class/subclass leaves a stale-but-inert selection in the Draft, surface a warning instead of silence). The architecture already makes this SAFE (stale selections are simply never read again, never corrupt anything) — 3c is purely about user-facing visibility, not correctness.
- **Phase 4**: breadth — a 5etools adapter (more sourcebooks beyond bundled SRD), 2024-ruleset mechanics, a source switchboard letting a player pick which rules/sourcebooks apply. Likely the single largest remaining phase.
- **Visual design pass**: the UI has been deliberately unstyled/functional-only through every phase so far (a conscious decision to build correctness before aesthetics). The user's chosen direction (confirmed via a reviewed mockup) is an aged-parchment/leather-bound-grimoire look, structurally similar to a D&D Beyond character sheet but with entirely original decoration (no reproduction of D&D Beyond's actual trademarked artwork/wordmark). Not yet applied to the real app — only prototyped as a standalone mockup.
- **Deployment**: the app is meant to be self-hosted on the user's own home server eventually; not yet deployed anywhere.

## Known gaps / things a fresh reader should NOT assume are bugs

- Frontend `types.ts` types are hand-maintained, not generated — they periodically drift from the real backend shape until a review catches it (this has happened and been fixed multiple times; there's no structural guard against it happening again).
- No automated frontend test suite exists — all frontend verification is `tsc` type-checking plus manual/browser checks.
- The `_class_label()` string-formatting helper is intentionally duplicated (not shared) between `markdown_export.py` and `pdf_export.py`, matching this project's established convention of these two files mirroring each other's content-selection logic independently rather than sharing a common renderer.
- `sheet.proficiencies` gained `armor`/`weapons`/`tools` fields in Phase 3b-i; `markdown_export.py`/`pdf_export.py` do not yet render them (only `export.py`'s YAML dump surfaces them, since it passes the sheet through wholesale) — a known, small gap, not yet closed.

## Process notes for whoever picks this up

This project has followed a strict "subagent-driven development" workflow the whole way: brainstorm → design spec (committed to `main`) → implementation plan (`docs/superpowers/plans/`, on a feature branch) → per-task implementer/reviewer dispatch loop → final whole-branch review → merge. Every plan's tasks are grounded in direct empirical inspection of the real bundled SRD JSON before being written — this has repeatedly caught planning errors (wrong assumptions about which classes have which data shapes) that would otherwise have become code bugs. Phase 3b-i's own final review flagged this discipline explicitly: plans that ship copy-paste-ready code snippets tend to convert every planning error into an implementation defect plus a review cycle, whereas plans that specify the INVARIANT and let the implementer write the code (and verify against real data) fare better. Worth keeping in mind for Phase 3b-ii onward.
