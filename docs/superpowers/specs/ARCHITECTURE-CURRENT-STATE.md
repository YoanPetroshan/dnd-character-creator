# dnd-character-creator v2 — Current State Overview

**Written:** 2026-09-21, at the close of Phase 3b-i (multiclassing core). **Updated:** 2026-09-23, at the close of Phase 3b-ii (multiclass spell slots), and again the same day at the close of Phase 3c (pruning warnings) — **all of Phase 3 ("depth": leveling, multiclassing, spell slots, pruning) is now complete.**

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
- **`Resolution`**: `sheet` (the finished character — name/level/classes/background/species/abilities/proficiencies/equipment/spells/details), `choices` (every pending-or-resolved Choice, generic across every source), `derived` (ability modifiers, prof bonus, HP, AC, saves, skills, passive perception, `spellSlots`/`warlockSpellSlots` — see Multiclass Spellcasting below), `problems` (blocking issues — e.g. unknown class, over-selected choice), `warnings` (non-blocking — e.g. an equipment envelope that couldn't be represented), `pruned` (as of Phase 3c: one entry per selection that's still sitting in the Draft but no longer reachable — e.g. an ASI tied to a level the player leveled back down from, or a feature choice tied to a subclass the player cleared — see "Pruning" below; NOT populated for the case where a choice's id survives a level-down but its allowed count shrinks, e.g. a spellcaster's known-spells choice — that's a known, separate gap, tracked as follow-up work).
- **The generic Choice model**: every player decision — a class skill pick, a spell choice, an ASI, starting equipment — is represented the same way: `{id, source, label, description, count, options, selected, status}`. `resolve()` builds a `choice_templates` list from every source (class/background/species/equipment/ASI/spells), then applies whatever the Draft already submitted to produce the final `choices` list. The frontend's `<ChoiceCard>`/`<ChoicePicker>` components render ANY choice generically — new choice-producing features (like multiclass proficiency choices) need zero new frontend rendering code, only a new template-building function on the backend.

## Where the rules data comes from

`server/catalog/loader.py` loads the bundled SRD JSON (`chargen/data/srd/*.json` — the SAME data files the OLD "v1" `chargen` module uses, ported verbatim in Phase 1, never modified) into a `Catalog` dataclass: `classes`, `levels`, `features`, `subclasses`, `races`, `subraces`, `traits`, `backgrounds`, `items`, `spells` — each indexed by its SRD `index` field. This is the ONLY data source right now — no other sourcebooks, no 5etools adapter, no 2024-ruleset content (all planned for Phase 4, not started).

Where the bundled SRD data doesn't structurally carry an answer the engine needs (e.g. which ability governs which skill, which classes are half-casters), `server/catalog/reference_data.py` hardcodes it as an open 5e RAW fact, always with a comment explaining why it couldn't be read from the data.

## Backend layout (`server/`)

- `app.py` — Flask routes: `/api/health`, `/api/resolve`, `/api/catalog` (+ per-class/background/species detail endpoints), `/api/items`, `/api/spells`, `/api/export/<fmt>` (yaml/markdown/pdf, one parameterized route).
- `catalog/loader.py`, `catalog/choices.py` (generic `build_choice_template`/`build_choice_options` — turns a raw SRD "choose N from X" envelope into a Choice template, handling every `option_type` shape the bundled data uses: `reference`, `counted_reference`, `string`, `multiple`, `ability_bonus`), `catalog/reference_data.py`.
- `engine/resolve.py` (~1000 lines — the heart of the app, see below), `engine/derived.py` (pure HP/modifier/save/skill math, no I/O), `engine/asi.py` (pure ASI combination math), `engine/equipment.py`, `engine/spells.py`.
- `export.py` (YAML), `markdown_export.py`, `pdf_export.py` (via `fpdf2`, with a bundled DejaVu Sans font for Cyrillic support — the UI and exports are Bulgarian-language).
- `tests/` — pytest, run via `server/.venv/bin/python -m pytest`. Currently 312 tests, all passing. A separate repo-root test (`tests/test_chargen_isolation.py`) enforces that nothing outside `chargen/` (the ported v1 engine) or the declared dependencies ever imports the OLD v1 play-engine modules — this has bitten the project twice before and is checked on every phase.

### `resolve()`'s shape (the single most important function in the app)

Roughly: validate/normalize the Draft → resolve species/background/race → compute final ability scores (base + species bonuses + any Half-Elf-style ability choice + ASI progression, threaded per-class in array order) → **loop over every class in `draft.classes`** building each one's own choice templates (features, ASI, spell choices — reusing the same per-class helper functions Phase 3a built, now called once per class instead of once total) → apply background/species/equipment choice templates → resolve every choice against the Draft's submitted selections (with deduplication) → compute `derived` stats (prof bonus from TOTAL character level, HP via `hit_point_max_multiclass` which correctly applies "only your very first class's level 1 ever takes the max hit die") → assemble `sheet` (with `sheet["classes"]` as a list, one entry per class, `sheet["spells"]` as a list, one entry per resolved caster).

An `alias block` pattern is used throughout: a `primary`/`cls`/`cls_id` etc. alias always points at `resolved_classes[0]` for the (still-single-computation) parts of the pipeline — background/species resolution, starting equipment (never multiclassed), saving-throw proficiencies (RAW: primary-class-only).

### Multiclass spellcasting (`derived.spellSlots`/`warlockSpellSlots`, per-caster DC/attack)

Spell slots are tracked in the Resolution for the first time as of Phase 3b-ii (they weren't exposed anywhere before, not even for a single-class caster). The rule (not just the data) matters here and was the source of two real bugs during this phase, both fixed and re-verified — worth restating precisely for anyone touching this code:

- Per RAW (PHB 164), the shared "Multiclass Spellcaster" slot table only applies when a character has **more than one** class that actually grants spell slots **at its current level**. With exactly one slot-granting class, that class's own real single-class table applies directly — NOT a round-down combined-level lookup. `server/engine/resolve.py` counts `slot_granting_entries` by calling `spells_mod.single_class_spell_slots(catalog, cls_id, level)` per class (an ACTUAL grant check, not a class-id-set membership check) and branches accordingly. Getting this wrong (checking class-id set membership instead of an actual current-level grant) silently undercounts slots for a level-1 half caster (Paladin/Ranger) paired with anything — caught twice during this phase's own review process.
- The shared multiclass table itself needs no hardcoded data — it is number-for-number identical to any full caster's own single-class slot progression at the same level, so it's looked up via `catalog.class_level_row("wizard", combined_level)` (Wizard is an arbitrary anchor, not required to be present in the character).
- Warlock's Pact Magic is entirely separate — excluded from the shared pool and combined-level calculation, exposed via its own `derived.warlockSpellSlots`, looked up at Warlock's own class level (never the combined level).
- `spellSaveDC`/`spellAttackBonus` are per-caster values living inside each entry of `sheet.spells` (one entry per resolved caster) — not top-level `derived` scalars (that was the pre-3b-ii shape, primary-class-only, removed as a breaking change).

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
- Phase 3b-ii: multiclass spell slots — `derived.spellSlots`/`warlockSpellSlots`, per-caster `spellSaveDC`/`spellAttackBonus` inside each `sheet.spells` entry, all three export formats updated. See "Multiclass spellcasting" above for the RAW rule this phase implements.
- A large ad hoc cleanup pass (mid-September 2026): fixed several backend correctness bugs found by earlier phases' final reviews (species languages/proficiencies dropped from the sheet, Half-Elf permanently unexportable, duplicate choice selections not deduplicated, equipment envelope drops never signaled), two frontend cleanups (typed `Resolution.sheet`/`derived` properly, hoisted the catalog fetch into a shared provider), and a Preferences UI on the Home page (unlocking the manual-HP-roll UI that had been built but unreachable since Phase 3a).

- Phase 3c: pruning warnings — `Resolution.pruned` populated for the first time. Detection is a single set comparison (no new data structure): `all_selections`' keys with a non-empty selection, compared against the current `choice_templates`' ids. Only two real-world reducer actions can leave a stale-but-present selection behind — leveling a class down (an ASI/feature tied to a level no longer reached) and clearing a subclass selection (a subclass-gated feature choice) — every other reducer action (switching class/background/species, removing a class) resets or deletes the relevant `choices` data outright, so there's nothing left to go stale. Rendered on `HomePage.tsx`, mirroring the existing `warnings` list.

**Not yet started:**
- **Phase 4**: breadth — a 5etools adapter (more sourcebooks beyond bundled SRD), 2024-ruleset mechanics, a source switchboard letting a player pick which rules/sourcebooks apply. Likely the single largest remaining phase.
- **Visual design pass**: the UI has been deliberately unstyled/functional-only through every phase so far (a conscious decision to build correctness before aesthetics). The user's chosen direction (confirmed via a reviewed mockup) is an aged-parchment/leather-bound-grimoire look, structurally similar to a D&D Beyond character sheet but with entirely original decoration (no reproduction of D&D Beyond's actual trademarked artwork/wordmark). Not yet applied to the real app — only prototyped as a standalone mockup.
- **Deployment**: the app is meant to be self-hosted on the user's own home server eventually; not yet deployed anywhere.

## Known gaps / things a fresh reader should NOT assume are bugs

- Frontend `types.ts` types are hand-maintained, not generated — they periodically drift from the real backend shape until a review catches it (this has happened and been fixed multiple times; there's no structural guard against it happening again).
- No automated frontend test suite exists — all frontend verification is `tsc` type-checking plus manual/browser checks.
- The `_class_label()` string-formatting helper is intentionally duplicated (not shared) between `markdown_export.py` and `pdf_export.py`, matching this project's established convention of these two files mirroring each other's content-selection logic independently rather than sharing a common renderer.
- `sheet.proficiencies` gained `armor`/`weapons`/`tools` fields in Phase 3b-i; `markdown_export.py`/`pdf_export.py` do not yet render them (only `export.py`'s YAML dump surfaces them, since it passes the sheet through wholesale) — a known, small gap, not yet closed.
- A secondary (non-primary) class still shows its own level-1 proficiency-CHOICE card if that class has no `multi_classing.proficiency_choices` of its own — RAW says it should grant nothing when taken as a second class. Known, not yet fixed (flagged during Phase 3b-i's final review, not blocking since the fixed-grant path is already correctly gated).
- **Slot-selection logic is split across `server/engine/resolve.py` (the branch deciding single-class-table vs. combined-table) and `server/engine/spells.py` (the actual lookups)** — Phase 3b-ii's final review flagged this as the most likely friction point for future spell-related work; consolidating into one `spell_slots_for()` function in `spells.py` was recommended but not yet done.
- **`Resolution.pruned` doesn't detect count-shrink staleness** — a spellcaster leveling down with more spells selected than the lower level now allows currently produces a blocking `over-selected-*` problem (pre-existing, unrelated to Phase 3c), not a `pruned` entry. This was Phase 3c's own design spec's ORIGINAL motivating example before its final review found the example didn't match what got built — the spec was corrected, and this gap was spun off as its own follow-up (not yet started).

## Process notes for whoever picks this up

This project has followed a strict "subagent-driven development" workflow the whole way: brainstorm → design spec (committed to `main`) → implementation plan (`docs/superpowers/plans/`, on a feature branch) → per-task implementer/reviewer dispatch loop → final whole-branch review → merge. Every plan's tasks are grounded in direct empirical inspection of the real bundled SRD JSON before being written — this has repeatedly caught planning errors (wrong assumptions about which classes have which data shapes) that would otherwise have become code bugs.

**A sharper version of this lesson emerged from Phase 3b-ii specifically, worth stating precisely for future phases:** the "verify against real SRD data" discipline verifies DATA — are these the right numbers for this level? — but the bundled JSON does not encode multiclassing RULES — which table applies, and when? Phase 3b-ii's plan/design spec got a RAW rule wrong (applying the combined-caster-level round-down table even when only one class actually grants spell slots) DESPITE every number in the spec being individually verified against real Wizard data — because no amount of data verification can catch a rule-selection error; the data was never wrong, the CHOICE of which data to look up was wrong. This bug recurred in two different forms across the phase's fix rounds (once for "does this class count as slot-granting at all," once more precisely for "does it grant slots at its CURRENT level") before being fully closed. **Recommendation for any future phase that implements a RAW rule (not just RAW data): the design spec should quote the governing rule text verbatim and enumerate the cases it distinguishes as an explicit test matrix, kept visibly separate from the data-verification step** — so "which table/branch applies" gets the same scrutiny as "what number does the table return."

Phase 3b-i's own final review flagged a related, more general discipline: plans that ship copy-paste-ready code snippets tend to convert every planning error into an implementation defect plus a review cycle, whereas plans that specify the INVARIANT and let the implementer write the code (and verify against real data) fare better.
