# Frontend Cleanups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two independently-diagnosed frontend cleanups deferred from earlier phases: `Resolution.sheet`/`Resolution.derived` are still typed `Record<string, unknown>` (forcing ad hoc casts wherever a page reads a sheet field), and `useCatalog()` is called independently in three separate pages, causing three duplicate `/api/catalog` fetches for the same effectively-static data.

**Architecture:** Task 1 replaces the two `Record<string, unknown>` fields in `frontend/src/types.ts`'s `Resolution` interface with real, precisely-shaped interfaces derived directly from `server/engine/resolve.py`'s actual return value (empirically re-read while writing this plan, not assumed) — and removes the one local, duplicate `SheetEquipment` interface + cast this gap already forced into existence (`frontend/src/pages/EquipmentPage.tsx`). Task 2 hoists the existing `useCatalog()` hook into a `CatalogProvider`/`useCatalogContext()` pair, mirroring the exact pattern `frontend/src/ResolutionContext.tsx` already established for `useResolution()`, and mounts it in `App.tsx` alongside `ResolutionProvider`.

**Tech Stack:** React + TypeScript (Vite). No test framework is configured for the frontend (`frontend/package.json` has no test script) — verification is `tsc -b` (via `npm run build`) passing with zero type errors, plus a manual dev-server check in the browser, per this project's established practice for frontend-only changes.

## Global Constraints

- **No behavior change.** Both tasks are structural-only: Task 1 adds compile-time types to data that already flows through the app unchanged at runtime; Task 2 changes WHERE a fetch happens (once, shared) not WHAT it fetches or how a page renders it. If `tsc -b` reveals a *real* type mismatch against actual runtime data, treat that as new information to fix carefully — but do not go looking for unrelated improvements.
- **Every new interface field must be traceable to a real field in `server/engine/resolve.py`'s current return value** (re-read directly while writing this plan — see the Sheet/Derived shape below) — no speculative fields for future phases.
- **`npm run build` (which runs `tsc -b && vite build`) must succeed with zero errors after each task**, run from `frontend/`.

---

### Task 1: Type `Resolution.sheet` and `Resolution.derived`

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/EquipmentPage.tsx`
- Modify: `frontend/src/pages/ClassPage.tsx` (verify only — likely no change needed, see Step 4)

**Interfaces:**
- Consumes: nothing new.
- Produces: `Resolution.sheet: Sheet` and `Resolution.derived: Derived` (both newly exported interfaces from `types.ts`), replacing `Record<string, unknown>`.

**The exact current shape**, re-read directly from `server/engine/resolve.py`'s `resolve()` function's final `sheet`/`derived` dict construction (lines ~709-776 as of this writing) while writing this plan:

```python
derived = {
    "abilityModifiers": modifiers,        # dict[Ability, int]
    "proficiencyBonus": prof_bonus,       # int
    "hitPointMax": ...,                   # int
    "hitDice": f"{level}d{hit_die}" if hit_die else None,  # str | None
    "armorClass": ...,                    # int
    "speed": race.get("speed") if race else None,          # int | None
    "savingThrows": saves,                # dict[Ability, int]
    "skills": skills,                     # dict[str, int]  (skill-id -> score)
    "passivePerception": ...,             # int
    "spellSaveDC": spell_save_dc,         # int | None
    "spellAttackBonus": spell_attack_bonus,  # int | None
}

sheet = {
    "name": draft.get("name") or "",      # str
    "level": level if cls else 0,         # int
    "class": {                            # {id, name, subclass} | None
        "id": cls_id, "name": cls["name"],
        "subclass": {"id": subclass_id, "name": subclass["name"]} if subclass_id and subclass else None,
    } if cls else None,
    "background": {"id": bg_id, "name": bg["name"]} if bg else None,   # {id, name} | None
    "species": {                          # {id, name, subspecies} | None
        "id": race_id, "name": race["name"],
        "subspecies": {"id": subrace_id, "name": subrace["name"]} if subrace else None,
    } if race else None,
    "abilities": final_scores,            # dict[Ability, int]
    "proficiencies": {
        "skills": sorted(proficient_skills),         # str[]  (skill-ids)
        "savingThrows": proficient_save_abilities,   # str[]  (ability names, e.g. "STR")
        "languages": sorted(set(fixed_languages + chosen_languages)),  # str[]
    },
    "equipment": {"granted": granted_equipment, "chosen": chosen_equipment, "added": added_resolved},
    "spells": spells_summary,             # {cantrips, known} | None — see below
    "details": details,                   # dict | None — see below
}
```

Equipment entry shapes (from `_fixed_equipment`/`_chosen_equipment`/the `added_resolved` build loop, all in `resolve.py`):
- `granted` and `chosen` entries: `{"itemId": str, "name": str, "qty": int}`.
- `added` entries: `{"itemId": str, "name": str, "qty": int, "equipped": bool}` (one extra field vs. the other two).

Spell summary shape (from `_spell_summaries` in `resolve.py`): `spells_summary` is `None`, or `{"cantrips": [...], "known": [...]}` where each list entry is `{"id": str, "name": str, "level": int}`.

Details shape (from `_sanitized_details`/`_DETAIL_FIELDS` in `resolve.py`): `None`, or a dict containing a SUBSET of these 18 optional string keys (only non-empty ones survive sanitization) — `alignment`, `faith`, `lifestyle`, `age`, `height`, `weight`, `eyes`, `skin`, `hair`, `personalityTraits`, `ideals`, `bonds`, `flaws`, `backstory`, `organizations`, `allies`, `enemies`, `notes`. This is the exact same field set as `Draft["details"]`, already defined in `types.ts` — reuse that shape rather than redefining it (see Step 1).

- [ ] **Step 1: Add the new interfaces to `frontend/src/types.ts`**

Open `frontend/src/types.ts`. The existing `Draft` interface's `details` field (lines 94-117) already has the exact 18-key shape needed for `Sheet["details"]` — extract it into its own named interface so both `Draft` and `Sheet` can reference it, rather than duplicating the 18 fields a second time:

```typescript
export interface CharacterDetails {
  // Character Details
  alignment?: string;
  faith?: string;
  lifestyle?: string;
  // Physical Characteristics
  age?: string;
  height?: string;
  weight?: string;
  eyes?: string;
  skin?: string;
  hair?: string;
  // Personality
  personalityTraits?: string;
  ideals?: string;
  bonds?: string;
  flaws?: string;
  // Notes
  backstory?: string;
  organizations?: string;
  allies?: string;
  enemies?: string;
  notes?: string;
}
```

Then change `Draft`'s own `details` field (currently a large inline object type spanning lines 94-117) to just:

```typescript
  details: CharacterDetails;
```

Now add the new Sheet/Derived interfaces (place them right before the `Resolution` interface, which is currently at line 54):

```typescript
export interface SheetEquipmentEntry {
  itemId: string;
  name: string;
  qty: number;
}

export interface SheetAddedEquipmentEntry extends SheetEquipmentEntry {
  equipped: boolean;
}

export interface SheetSpellSummary {
  id: string;
  name: string;
  level: number;
}

export interface SheetSpells {
  cantrips: SheetSpellSummary[];
  known: SheetSpellSummary[];
}

export interface SheetClassSubclass {
  id: string;
  name: string;
}

export interface SheetClass {
  id: string;
  name: string;
  subclass: SheetClassSubclass | null;
}

export interface SheetBackground {
  id: string;
  name: string;
}

export interface SheetSubspecies {
  id: string;
  name: string;
}

export interface SheetSpecies {
  id: string;
  name: string;
  subspecies: SheetSubspecies | null;
}

export interface SheetProficiencies {
  skills: string[];
  savingThrows: string[];
  languages: string[];
}

export interface SheetEquipment {
  granted: SheetEquipmentEntry[];
  chosen: SheetEquipmentEntry[];
  added: SheetAddedEquipmentEntry[];
}

export interface Sheet {
  name: string;
  level: number;
  class: SheetClass | null;
  background: SheetBackground | null;
  species: SheetSpecies | null;
  abilities: Record<Ability, number>;
  proficiencies: SheetProficiencies;
  equipment: SheetEquipment;
  spells: SheetSpells | null;
  details: CharacterDetails | null;
}

export interface Derived {
  abilityModifiers: Record<Ability, number>;
  proficiencyBonus: number;
  hitPointMax: number;
  hitDice: string | null;
  armorClass: number;
  speed: number | null;
  savingThrows: Record<Ability, number>;
  skills: Record<string, number>;
  passivePerception: number;
  spellSaveDC: number | null;
  spellAttackBonus: number | null;
}
```

Now update the `Resolution` interface (currently lines 54-61) to use the new types:

```typescript
export interface Resolution {
  sheet: Sheet;
  choices: Choice[];
  derived: Derived;
  problems: Problem[];
  warnings: WarningItem[];
  pruned: Pruned[];
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npm run build`
Expected: this will likely FAIL at this point — `frontend/src/pages/EquipmentPage.tsx` currently declares its own local `SheetEquipment` interface (a duplicate of the one just added to `types.ts`, both exported, causing a name collision since `EquipmentPage.tsx` doesn't currently import `SheetEquipment` from `types.ts` — it's a same-named LOCAL interface) and does `resolution.sheet.equipment as SheetEquipment | undefined` — a cast that is no longer needed now that `resolution.sheet.equipment` is genuinely typed as `SheetEquipment`. Fix this in Step 3 before re-running.

- [ ] **Step 3: Remove the now-redundant local type and cast in `EquipmentPage.tsx`**

Open `frontend/src/pages/EquipmentPage.tsx`. Find:

```typescript
interface SheetEquipment {
  granted: { itemId: string; name: string; qty: number }[];
  chosen: { itemId: string; name: string; qty: number }[];
  added: { itemId: string; name: string; qty: number; equipped: boolean }[];
}
```

Delete this entire local interface — it's now provided by `types.ts`.

Find:

```typescript
  const sheetEquipment = resolution.sheet.equipment as SheetEquipment | undefined;
```

Replace with:

```typescript
  const sheetEquipment = resolution.sheet.equipment;
```

(`resolution.sheet` is no longer `Record<string, unknown>`, so `resolution.sheet.equipment` is now directly and correctly typed as `SheetEquipment` — no cast needed, and it's never `undefined` since `Sheet.equipment` isn't optional. If any code below this line was written assuming `sheetEquipment` could be `undefined` — e.g. an `if (sheetEquipment)` guard or `sheetEquipment?.` optional chaining — read that code and simplify it now that the type guarantees the value is always present; don't leave a dead undefined-check in place.)

- [ ] **Step 4: Type-check and manually verify `ClassPage.tsx`'s existing `derived.hitPointMax` read**

Run: `cd frontend && npm run build`
Expected: should now PASS. If it fails on `frontend/src/pages/ClassPage.tsx`'s line reading `resolution.derived.hitPointMax` (currently `{resolution ? String(resolution.derived.hitPointMax ?? "—") : "—"}`), read that line — `hitPointMax` is now typed `number`, and `number ?? "—"` still type-checks fine as `number | string` fed into `String(...)`, so this should need NO changes. If `tsc` reports an actual error here, read it carefully and fix minimally (it would mean this plan's shape derivation missed something — re-check against the real `resolve.py` output before guessing at a fix).

- [ ] **Step 5: Full repo-wide type-check**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors, and the Vite build step completes (confirms no other file in the frontend was relying on the old loose `Record<string, unknown>` shape in a way that silently broke).

- [ ] **Step 6: Manual verification in the browser**

Start the dev server (`cd frontend && npm run dev`, or however this project's dev server is normally started — check for an existing `.claude/launch.json` entry first) and open the app. Navigate to the Equipment page and the Class page (the two pages this task touched) with a resolved character (pick a class, background, species first if the app requires it to reach a non-empty resolution) and confirm:
- The Equipment page still renders granted/chosen/added equipment exactly as before (no visual change expected — this task is type-only).
- The Class page's HP summary still renders a number, not "—" or a crash.

This is a structural/type-only change with no intended behavior change, so the manual check is a regression guard, not a new-feature check.

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/types.ts frontend/src/pages/EquipmentPage.tsx
git commit -m "$(cat <<'EOF'
refactor: type Resolution.sheet and Resolution.derived precisely

Both fields were Record<string, unknown> since Phase 0, forcing every
consumer to either cast or lose type safety — EquipmentPage.tsx had
already grown its own local, duplicate SheetEquipment interface plus an
`as` cast to work around this. Replaced with real interfaces derived
directly from resolve.py's actual return shape (Sheet, Derived, and
their nested types), and removed the now-redundant local workaround.
Draft["details"] and the new Sheet["details"] now share one
CharacterDetails interface instead of two copies of the same 18 fields.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Hoist `useCatalog()` into a shared `CatalogProvider`

**Files:**
- Create: `frontend/src/CatalogContext.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/ClassPage.tsx`
- Modify: `frontend/src/pages/BackgroundPage.tsx`
- Modify: `frontend/src/pages/SpeciesPage.tsx`

**Interfaces:**
- Consumes: the existing `useCatalog()` hook from `frontend/src/useCatalog.ts` (unchanged) and its exported types `CatalogClass`, `CatalogBackground`, `CatalogSpecies`, `CatalogSpeciesSubspecies` (unchanged).
- Produces: `CatalogProvider` (a component wrapping `children`) and `useCatalogContext(): CatalogState & { retry: () => void }` (a hook throwing if used outside the provider) — exported from the new `frontend/src/CatalogContext.tsx`.

This task is a direct structural mirror of the EXISTING `frontend/src/ResolutionContext.tsx` (already read in full while writing this plan — reproduced below for the exact pattern to follow):

```typescript
import { createContext, useContext, type ReactNode } from "react";
import { useDraft } from "./DraftContext";
import { useResolution } from "./useResolution";
import type { Resolution } from "./types";

interface ResolutionContextValue {
  resolution: Resolution | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

const ResolutionContext = createContext<ResolutionContextValue | null>(null);

export function ResolutionProvider({ children }: { children: ReactNode }) {
  const { draft } = useDraft();
  const state = useResolution(draft);
  return <ResolutionContext.Provider value={state}>{children}</ResolutionContext.Provider>;
}

export function useResolutionContext(): ResolutionContextValue {
  const ctx = useContext(ResolutionContext);
  if (!ctx) throw new Error("useResolutionContext must be used within a ResolutionProvider");
  return ctx;
}
```

`useCatalog()` takes no arguments (unlike `useResolution(draft)`), so `CatalogProvider` is simpler — it doesn't need to read from `DraftContext`.

- [ ] **Step 1: Create `frontend/src/CatalogContext.tsx`**

```typescript
import { createContext, useContext, type ReactNode } from "react";
import { useCatalog, type CatalogClass, type CatalogBackground, type CatalogSpecies } from "./useCatalog";

interface CatalogContextValue {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  loading: boolean;
  error: string | null;
  retry: () => void;
}

const CatalogContext = createContext<CatalogContextValue | null>(null);

export function CatalogProvider({ children }: { children: ReactNode }) {
  const state = useCatalog();
  return <CatalogContext.Provider value={state}>{children}</CatalogContext.Provider>;
}

export function useCatalogContext(): CatalogContextValue {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error("useCatalogContext must be used within a CatalogProvider");
  return ctx;
}
```

(Confirm `useCatalog.ts` actually exports `CatalogClass`, `CatalogBackground`, `CatalogSpecies` as named exports before writing this import — they were confirmed exported while writing this plan, but re-check since the file may have changed.)

- [ ] **Step 2: Mount `CatalogProvider` in `App.tsx`**

Open `frontend/src/App.tsx`. Current structure:

```typescript
import { Routes, Route, Navigate } from "react-router-dom";
import { ResolutionProvider } from "./ResolutionContext";
import { StepNav } from "./components/StepNav";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ExportPage } from "./pages/ExportPage";

export default function App() {
  return (
    <div className="app">
      <ResolutionProvider>
        <StepNav />
        <main>
          <Routes>
            ...
          </Routes>
        </main>
      </ResolutionProvider>
    </div>
  );
}
```

Add the import and wrap `ResolutionProvider`'s children with `CatalogProvider` (order between the two providers doesn't matter — neither depends on the other — but nest `CatalogProvider` OUTSIDE `ResolutionProvider` since catalog data is more foundational/static):

```typescript
import { Routes, Route, Navigate } from "react-router-dom";
import { CatalogProvider } from "./CatalogContext";
import { ResolutionProvider } from "./ResolutionContext";
import { StepNav } from "./components/StepNav";
import { HomePage } from "./pages/HomePage";
import { ClassPage } from "./pages/ClassPage";
import { BackgroundPage } from "./pages/BackgroundPage";
import { SpeciesPage } from "./pages/SpeciesPage";
import { AbilitiesPage } from "./pages/AbilitiesPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ExportPage } from "./pages/ExportPage";

export default function App() {
  return (
    <div className="app">
      <CatalogProvider>
        <ResolutionProvider>
          <StepNav />
          <main>
            <Routes>
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/class" element={<ClassPage />} />
              <Route path="/background" element={<BackgroundPage />} />
              <Route path="/species" element={<SpeciesPage />} />
              <Route path="/abilities" element={<AbilitiesPage />} />
              <Route path="/equipment" element={<EquipmentPage />} />
              <Route path="/export" element={<ExportPage />} />
            </Routes>
          </main>
        </ResolutionProvider>
      </CatalogProvider>
    </div>
  );
}
```

- [ ] **Step 3: Switch `ClassPage.tsx` from `useCatalog()` to `useCatalogContext()`**

Open `frontend/src/pages/ClassPage.tsx`. Find the import of `useCatalog` and the line `const catalog = useCatalog();` (currently around line 24). Replace the import:

```typescript
import { useCatalogContext } from "../CatalogContext";
```

(remove the old `import { useCatalog } from "../useCatalog";` — but check first whether this file also imports TYPES from `useCatalog.ts` like `CatalogClass`; if so, keep that half of the import, e.g. `import type { CatalogClass } from "../useCatalog";`, and only remove the `useCatalog` function import.)

Replace `const catalog = useCatalog();` with `const catalog = useCatalogContext();`. No other changes needed — `useCatalogContext()` returns the exact same shape (`classes`, `backgrounds`, `species`, `loading`, `error`, `retry`) that `useCatalog()` did, so every existing `catalog.error`, `catalog.retry`, `catalog.classes` read in this file keeps working unchanged.

- [ ] **Step 4: Switch `BackgroundPage.tsx` from `useCatalog()` to `useCatalogContext()`**

Open `frontend/src/pages/BackgroundPage.tsx`. Same change as Step 3: replace the `useCatalog` import with `useCatalogContext` from `../CatalogContext`, and `const catalog = useCatalog();` (currently around line 9) with `const catalog = useCatalogContext();`.

- [ ] **Step 5: Switch `SpeciesPage.tsx` from `useCatalog()` to `useCatalogContext()`**

Open `frontend/src/pages/SpeciesPage.tsx`. Same change as Step 3: replace the `useCatalog` import with `useCatalogContext` from `../CatalogContext`, and `const catalog = useCatalog();` (currently around line 9) with `const catalog = useCatalogContext();`.

- [ ] **Step 6: Type-check**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors.

- [ ] **Step 7: Manual verification in the browser**

Start the dev server and open the app. Open the browser's network tab (or use `read_network_requests` if using the Claude Browser tool). Navigate between the Class, Background, and Species pages in sequence. Confirm:
- `GET /api/catalog` fires exactly ONCE for the whole session (on first mount of `CatalogProvider`, i.e. app load), not once per page visit — this is the actual behavior change this task delivers, so verify it directly rather than trusting the type-check alone.
- Each of the three pages still renders its class/background/species list correctly, and each page's own "retry on error" button (if you can trigger an error, e.g. by briefly stopping the backend) still works — confirms the shared `retry()` still works from any consuming page.

- [ ] **Step 8: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/CatalogContext.tsx frontend/src/App.tsx frontend/src/pages/ClassPage.tsx frontend/src/pages/BackgroundPage.tsx frontend/src/pages/SpeciesPage.tsx
git commit -m "$(cat <<'EOF'
refactor: hoist useCatalog() into a shared CatalogProvider

ClassPage, BackgroundPage, and SpeciesPage each called useCatalog()
independently, causing three duplicate GET /api/catalog fetches for the
same session-static data. CatalogProvider/useCatalogContext mirrors the
existing ResolutionProvider/useResolutionContext pattern exactly — one
fetch per app load, shared across every consuming page.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- Task 1's Step 3 removal of `EquipmentPage.tsx`'s local `SheetEquipment` interface is not optional cleanup — leaving both the local interface AND the new `types.ts` one would be a duplicate-name compile error (both exported... actually the local one isn't exported, so no naming collision, but it would still be genuinely redundant dead code sitting right next to the real, now-authoritative type). Remove it.
- Task 2 is a pure hoist — do not add any new catalog-fetching logic, caching strategy, or loading-state UI beyond what `useCatalog.ts` already provides. The provider is structural plumbing, not a redesign.
- These two tasks touch disjoint files (Task 1: `types.ts` + `EquipmentPage.tsx`; Task 2: a new file + `App.tsx` + 3 page files) except that both tasks touch `ClassPage.tsx` — Task 1 only VERIFIES it (Step 4, likely no edit), Task 2 actually edits it (Step 3). If executed via subagent-driven-development, dispatch Task 1 to completion (including its Step 4 verification) before starting Task 2, so there's no risk of two implementers touching `ClassPage.tsx` concurrently.
