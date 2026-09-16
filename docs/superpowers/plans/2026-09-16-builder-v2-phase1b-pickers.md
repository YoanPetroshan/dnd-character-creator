# Builder v2 Phase 1b — Real Class/Background/Species/Abilities Pickers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the frontend up to the real engine Phase 1a built. Phase 0's `ClassPage`/`BackgroundPage`/`SpeciesPage` already render real `Choice` data correctly (via the existing `<ChoiceCard>`/`<ChoicePicker>` pair) but have no way to actually *pick* a class, background, or species — `draft.classes` stays `[]` forever, so there's nothing to render. This plan adds: the missing Draft reducer actions, a `GET /api/catalog`-backed picker on each of those three pages, wires every `ChoiceCard`'s `onChange` to real dispatch (finally exercising the wiring Phase 0 deliberately left as a `console.log` stub), a full three-method Abilities editor (Standard Array / Point Buy / Manual), and a working Export page that downloads the real YAML from Phase 1a's `/api/export/yaml`.

**Architecture:** Pure frontend work — no backend changes, no new endpoints (Phase 1a already shipped everything this plan needs: `GET /api/catalog`, `POST /api/resolve`, `POST /api/export/yaml`). A new `useCatalog()` hook fetches the lightweight catalog listing once; the `DraftProvider` reducer gains actions for every field a picker needs to set; each page dispatches those actions instead of doing nothing.

**Tech Stack:** Same as Phase 0/1a's frontend — React 19.3.0, TypeScript 7.0.2, no new dependencies.

## Global Constraints

- **No visual/design work.** Only the minimal structural CSS needed to make new elements (radio lists, a `<select>`, an ability-score table, point-buy +/- steppers) legible and organized — borders, spacing, simple table rules — matching the exact minimal-structural style Phase 0's `index.css` already established. No colors, no typography choices, no branding. The user is sourcing a real visual design separately (see the aged-paper/parchment reference screenshots already shared) for a dedicated later pass — do not anticipate it here.
- **Single class, level 1 only, still.** Phase 1a's engine only supports this. `SET_CLASS` always replaces `draft.classes` with a single fresh entry `{classId, level: 1, choices: {}}` — no level selector, no subclass picker, no "add another class" UI. This matches the engine's own scope exactly; adding UI for something the engine can't process would just produce confusing `problems[]` output.
- **Equipment is untouched.** `EquipmentPage.tsx` stays exactly as Phase 0 left it (still correctly shows "no choices yet," since the engine never produces `equipment`-kind choices — Phase 2 scope per the architecture spec's phasing).
- **`<ChoiceCard>`/`<ChoicePicker>` are reused unchanged.** They already handle expand/collapse, disabled options, and multi-select correctly (built in Phase 0, exercised for real against Phase 1a's engine data in this plan for the first time). No task in this plan modifies `frontend/src/components/ChoiceCard.tsx` or `ChoicePicker.tsx`.
- **Picking a new class/background/species/subspecies resets that source's `choices` to `{}`.** A choice id from the *previous* selection (e.g. a Fighter's `class:fighter:1:feature:fighter-fighting-style`) is meaningless once the user switches to Wizard — stale entries in `draft` would just be silently ignored by `resolve()` (harmless, since the engine only reads choice ids that match its own generated templates) but leaving them around is confusing state to carry forever. Every `SET_CLASS`/`SET_BACKGROUND`/`SET_SPECIES`/`SET_SUBSPECIES` reducer case must rebuild that field's `choices` as a fresh `{}`, not merge into the old one.
- **The debounced `useResolution` hook (Phase 0/1a) is not modified.** Every page in this plan reads `resolution`/`loading`/`error`/`retry` from the existing `useResolutionContext()` exactly as Phase 0's pages already do — dispatching a Draft action changes `draft`, which the existing hook already re-resolves automatically.

---

### Task 1: Draft reducer actions

**Files:**
- Modify: `frontend/src/DraftContext.tsx`

**Interfaces:**
- Consumes: `Draft`, `Ability`, `ChoiceSourceKind` types (`frontend/src/types.ts`, unchanged from Phase 0)
- Produces: five new dispatchable actions — `SET_CLASS`, `SET_BACKGROUND`, `SET_SPECIES`, `SET_SUBSPECIES`, `SET_ABILITY_METHOD`, `SET_ABILITY_SCORE`, `SET_CHOICE_SELECTION` — every later task in this plan dispatches these by exact type name and payload shape.

- [ ] **Step 1: Write the new `Action` union and reducer cases**

Replace the existing `Action` type and `reducer` function in `frontend/src/DraftContext.tsx` with:

```ts
import { createContext, useContext, useReducer, useEffect, type Dispatch, type ReactNode } from "react";
import type { Ability, ChoiceSourceKind, Draft } from "./types";

const STORAGE_KEY = "dnd-builder-draft-v2";

export const emptyDraft: Draft = {
  name: "",
  sources: ["srd"],
  preferences: {
    advancementType: "milestone",
    hitPointType: "fixed",
    usePrerequisites: { feats: true, multiclass: true },
  },
  classes: [],
  background: { choices: {} },
  species: { choices: {} },
  abilities: {
    method: "standard",
    base: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
  },
  equipment: { added: [], skipped: false },
  details: {},
};

type Action =
  | { type: "SET_NAME"; name: string }
  | { type: "SET_DRAFT"; draft: Draft }
  | { type: "RESET" }
  | { type: "SET_CLASS"; classId: string }
  | { type: "SET_BACKGROUND"; backgroundId: string }
  | { type: "SET_SPECIES"; speciesId: string }
  | { type: "SET_SUBSPECIES"; subspeciesId: string | undefined }
  | { type: "SET_ABILITY_METHOD"; method: Draft["abilities"]["method"] }
  | { type: "SET_ABILITY_SCORE"; ability: Ability; value: number }
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] };

function reducer(state: Draft, action: Action): Draft {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_DRAFT":
      return action.draft;
    case "RESET":
      return emptyDraft;
    case "SET_CLASS":
      // A fresh single-entry array with empty choices — Phase 1 supports
      // exactly one class at level 1, and any choices tied to a previous
      // class selection are meaningless for the new one.
      return { ...state, classes: [{ classId: action.classId, level: 1, choices: {} }] };
    case "SET_BACKGROUND":
      return { ...state, background: { id: action.backgroundId, choices: {} } };
    case "SET_SPECIES":
      // Switching species clears any subspecies pick too — a subspecies id
      // from the old species is never valid for the new one.
      return { ...state, species: { id: action.speciesId, choices: {} } };
    case "SET_SUBSPECIES":
      return {
        ...state,
        species: { ...state.species, subspeciesId: action.subspeciesId, choices: {} },
      };
    case "SET_ABILITY_METHOD":
      return { ...state, abilities: { ...state.abilities, method: action.method } };
    case "SET_ABILITY_SCORE":
      return {
        ...state,
        abilities: {
          ...state.abilities,
          base: { ...state.abilities.base, [action.ability]: action.value },
        },
      };
    case "SET_CHOICE_SELECTION": {
      if (action.source === "class") {
        if (state.classes.length === 0) return state; // no class picked yet — ignore
        const [cls] = state.classes;
        return {
          ...state,
          classes: [{ ...cls, choices: { ...cls.choices, [action.choiceId]: action.selected } }],
        };
      }
      if (action.source === "background") {
        return {
          ...state,
          background: {
            ...state.background,
            choices: { ...state.background.choices, [action.choiceId]: action.selected },
          },
        };
      }
      if (action.source === "species") {
        return {
          ...state,
          species: {
            ...state.species,
            choices: { ...state.species.choices, [action.choiceId]: action.selected },
          },
        };
      }
      return state; // subclass/feature/equipment choices aren't dispatched from anywhere in Phase 1b
    }
    default:
      return state;
  }
}

function loadInitial(): Draft {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...emptyDraft, ...(JSON.parse(raw) as Partial<Draft>) };
  } catch {
    // corrupt or inaccessible storage — fall through to a fresh draft
  }
  return emptyDraft;
}

interface DraftContextValue {
  draft: Draft;
  dispatch: Dispatch<Action>;
}

const DraftContext = createContext<DraftContextValue | null>(null);

export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, dispatch] = useReducer(reducer, undefined, loadInitial);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // storage unavailable (private mode, quota) — the draft still works
      // in-memory for this session, it just won't survive a reload
    }
  }, [draft]);

  return <DraftContext.Provider value={{ draft, dispatch }}>{children}</DraftContext.Provider>;
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error("useDraft must be used within a DraftProvider");
  return ctx;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors. (No page dispatches these new actions yet — that's fine, an unused union member is not a TypeScript error.)

- [ ] **Step 3: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/DraftContext.tsx
git commit -m "$(cat <<'EOF'
feat: add Draft reducer actions for class/background/species/abilities/choices

SET_CLASS, SET_BACKGROUND, SET_SPECIES, and SET_SUBSPECIES each reset
that source's choices to {} — a choice id from a previous selection is
meaningless once the underlying class/background/species changes.
SET_CHOICE_SELECTION is the one action every ChoiceCard's onChange
will dispatch, routed to the right Draft field by source kind.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `useCatalog` hook

**Files:**
- Create: `frontend/src/useCatalog.ts`

**Interfaces:**
- Produces: `useCatalog(): { classes: CatalogClass[], backgrounds: CatalogBackground[], species: CatalogSpecies[], loading: boolean, error: string | null, retry: () => void }` — Tasks 3, 4, 5 are the consumers.

- [ ] **Step 1: Write `frontend/src/useCatalog.ts`**

```ts
import { useCallback, useEffect, useState } from "react";

export interface CatalogClass {
  id: string;
  name: string;
  hitDie: number;
}

export interface CatalogBackground {
  id: string;
  name: string;
}

export interface CatalogSpeciesSubspecies {
  id: string;
  name: string;
}

export interface CatalogSpecies {
  id: string;
  name: string;
  subspecies: CatalogSpeciesSubspecies[];
}

interface CatalogState {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  loading: boolean;
  error: string | null;
}

const EMPTY_STATE: CatalogState = { classes: [], backgrounds: [], species: [], loading: true, error: null };

export function useCatalog(): CatalogState & { retry: () => void } {
  const [state, setState] = useState<CatalogState>(EMPTY_STATE);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetch("/api/catalog")
      .then((resp) => {
        if (!resp.ok) throw new Error(`catalog fetch failed: ${resp.status}`);
        return resp.json() as Promise<Omit<CatalogState, "loading" | "error">>;
      })
      .then((data) => {
        if (cancelled) return;
        setState({ ...data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setState((s) => ({ ...s, loading: false, error: message }));
      });
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
curl -s http://127.0.0.1:8000/api/catalog | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['classes']), len(d['backgrounds']), len(d['species']))"
kill %1
```

Expected: `12 1 9` — confirms the exact shape `useCatalog` expects is what the already-shipped Phase 1a endpoint actually returns (no live browser check needed yet; Task 3 exercises the hook for real).

- [ ] **Step 4: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/useCatalog.ts
git commit -m "$(cat <<'EOF'
feat: add useCatalog hook for GET /api/catalog

One-shot fetch (the catalog is static for the lifetime of a session —
no debounce needed, unlike useResolution) with the same retry-on-nonce
pattern already established for resolve() failures.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Class picker

**Files:**
- Modify: `frontend/src/pages/ClassPage.tsx`
- Modify: `frontend/src/index.css` (add `.picker-list` rules)

**Interfaces:**
- Consumes: `useDraft()` (Task 1), `useCatalog()` (Task 2), `useResolutionContext()` (Phase 0, unchanged), `<ChoiceCard>` (Phase 0, unchanged)
- Produces: nothing new consumed elsewhere — this is a leaf page.

- [ ] **Step 1: Rewrite `frontend/src/pages/ClassPage.tsx`**

```tsx
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedClassId = draft.classes[0]?.classId;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

  const classChoices = resolution ? resolution.choices.filter((c) => c.source.kind === "class") : [];

  return (
    <div className="page">
      <h1>Клас {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане на класовете: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="picker-list">
        {catalog.classes.map((c) => (
          <li key={c.id}>
            <label>
              <input
                type="radio"
                name="class"
                checked={selectedClassId === c.id}
                onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
              />
              {c.name} (d{c.hitDie})
            </label>
          </li>
        ))}
      </ul>
      {selectedClassId && !loading && classChoices.length === 0 && <p>Няма избори за този клас.</p>}
      {classChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Add `.picker-list` rules to `frontend/src/index.css`**

Add at the end of the file:

```css
.picker-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
}

.picker-list li {
  padding: 2px 0;
}
```

- [ ] **Step 3: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/class`. Confirm 12 class radio buttons render (Barbarian through Wizard, each showing its hit die). Click "Fighter" — confirm the URL doesn't change but "Fighting Style" and "Skill Proficiencies" choice cards appear below the radio list (this is Phase 1a's real engine output, not Phase 0's stub — Fighting Style should be genuinely empty/pending with 4 real options). Click a Fighting Style option — confirm it becomes checked and, after the ~150ms debounce, the choice card's header updates (no more `!` pending dot once both choices in this class are satisfied — Skill Proficiencies needs 2 picks too). Reload the page — confirm the class selection and Fighting Style pick both survived (localStorage persistence, unchanged from Phase 0).

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/ClassPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: wire ClassPage to a real class picker + live choice dispatch

Replaces the console.log-only onChange stub from Phase 0 with a real
SET_CHOICE_SELECTION dispatch, and adds the missing class picker
(GET /api/catalog) that Phase 0 had no way to drive at all — draft.classes
stayed [] forever until now. Verified live against Phase 1a's real
engine: picking Fighter renders genuine Fighting Style / Skill
Proficiencies choices, not Phase 0's hardcoded stub data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Background picker

**Files:**
- Modify: `frontend/src/pages/BackgroundPage.tsx`

**Interfaces:**
- Consumes: `useDraft()` (Task 1), `useCatalog()` (Task 2), `useResolutionContext()`, `<ChoiceCard>`

- [ ] **Step 1: Rewrite `frontend/src/pages/BackgroundPage.tsx`**

```tsx
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function BackgroundPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedBackgroundId = draft.background.id;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "background", choiceId, selected });
  }

  const choices = resolution ? resolution.choices.filter((c) => c.source.kind === "background") : [];

  return (
    <div className="page">
      <h1>Background {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <select
        value={selectedBackgroundId ?? ""}
        onChange={(e) => {
          if (e.target.value) dispatch({ type: "SET_BACKGROUND", backgroundId: e.target.value });
        }}
      >
        <option value="">— избери background —</option>
        {catalog.backgrounds.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
      </select>
      {selectedBackgroundId && !loading && choices.length === 0 && <p>Няма избори за този background.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/background`. Confirm the dropdown shows "Acolyte" as the only real option (Phase 1's SRD data has exactly one background). Select it — confirm a "Languages" choice card appears (2 choices, 16 real language options — not Phase 0's hardcoded Celestial/Draconic/Dwarvish). Pick two languages — confirm the card shows as resolved.

```bash
kill %1 %2
```

- [ ] **Step 4: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/BackgroundPage.tsx
git commit -m "$(cat <<'EOF'
feat: wire BackgroundPage to a real background picker + live choice dispatch

Same pattern as ClassPage — a real GET /api/catalog-backed dropdown
(currently just Acolyte, since that's the only background in the
bundled SRD data) replacing the no-op onChange stub.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Species picker + subspecies

**Files:**
- Modify: `frontend/src/pages/SpeciesPage.tsx`

**Interfaces:**
- Consumes: `useDraft()` (Task 1), `useCatalog()` (Task 2), `useResolutionContext()`, `<ChoiceCard>`

- [ ] **Step 1: Rewrite `frontend/src/pages/SpeciesPage.tsx`**

```tsx
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function SpeciesPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedSpeciesId = draft.species.id;
  const selectedSpecies = catalog.species.find((s) => s.id === selectedSpeciesId);

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "species", choiceId, selected });
  }

  const choices = resolution ? resolution.choices.filter((c) => c.source.kind === "species") : [];

  return (
    <div className="page">
      <h1>Species {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="picker-list">
        {catalog.species.map((s) => (
          <li key={s.id}>
            <label>
              <input
                type="radio"
                name="species"
                checked={selectedSpeciesId === s.id}
                onChange={() => dispatch({ type: "SET_SPECIES", speciesId: s.id })}
              />
              {s.name}
            </label>
          </li>
        ))}
      </ul>
      {selectedSpecies && selectedSpecies.subspecies.length > 0 && (
        <>
          <h2>Subspecies</h2>
          <select
            value={draft.species.subspeciesId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBSPECIES", subspeciesId: e.target.value || undefined })}
          >
            <option value="">— none —</option>
            {selectedSpecies.subspecies.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.name}
              </option>
            ))}
          </select>
        </>
      )}
      {selectedSpeciesId && !loading && choices.length === 0 && <p>Няма избори за този species.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/species`. Confirm 9 species radios render. Select "Dwarf" — confirm a "Subspecies" dropdown appears with "Hill Dwarf" as an option (Dwarf is one of the 4 races with a bundled subrace). Select "Human" instead — confirm the Subspecies dropdown disappears (Human has none) and a "Bonus Language" choice card appears (Phase 1a's final-fix-wave feature — Human's own bonus-language choice, 16 real language options). Select "Dragonborn" — confirm a "Draconic Ancestry" choice card appears with real dragon-color options (including "Gold (Fire)" with no `disabled` flag this time — Phase 0's stub hardcoded Gold as disabled; the real engine doesn't).

```bash
kill %1 %2
```

- [ ] **Step 4: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/SpeciesPage.tsx
git commit -m "$(cat <<'EOF'
feat: wire SpeciesPage to a real species/subspecies picker + live dispatch

Adds the subspecies dropdown (shown only when the selected species has
bundled subraces) alongside the same GET /api/catalog-backed radio
list pattern as Class/Background. Picking a species now genuinely
drives the engine's real trait/language choices instead of nothing.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Abilities editor (Standard Array / Point Buy / Manual)

**Files:**
- Modify: `frontend/src/pages/AbilitiesPage.tsx`
- Modify: `frontend/src/index.css` (add ability-table rules)

**Interfaces:**
- Consumes: `useDraft()` (Task 1), `useResolutionContext()`, `Ability` type (`frontend/src/types.ts`)

- [ ] **Step 1: Rewrite `frontend/src/pages/AbilitiesPage.tsx`**

```tsx
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import type { Ability, Draft } from "../types";

const ABILITIES: Ability[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const POINT_BUY_COST: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
const POINT_BUY_BUDGET = 27;

export function AbilitiesPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const { method, base } = draft.abilities;
  const derived = resolution?.derived as { abilityModifiers?: Record<string, number> } | undefined;
  const modifiers = derived?.abilityModifiers;

  function setAbility(ability: Ability, value: number) {
    dispatch({ type: "SET_ABILITY_SCORE", ability, value });
  }

  function setMethod(next: Draft["abilities"]["method"]) {
    dispatch({ type: "SET_ABILITY_METHOD", method: next });
  }

  const usedInStandardArray = ABILITIES.map((a) => base[a]);
  const pointBuySpent = ABILITIES.reduce((sum, a) => sum + (POINT_BUY_COST[base[a]] ?? 0), 0);

  return (
    <div className="page">
      <h1>Abilities {loading && "…"}</h1>
      <div className="ability-method-selector">
        <label>
          <input type="radio" name="ability-method" checked={method === "standard"} onChange={() => setMethod("standard")} />
          Standard Array
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "pointbuy"} onChange={() => setMethod("pointbuy")} />
          Point Buy
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "manual"} onChange={() => setMethod("manual")} />
          Manual
        </label>
      </div>

      {method === "pointbuy" && <p>Points Remaining: {POINT_BUY_BUDGET - pointBuySpent}</p>}

      <table className="ability-table">
        <thead>
          <tr>
            <th>Ability</th>
            <th>Score</th>
            <th>Modifier</th>
          </tr>
        </thead>
        <tbody>
          {ABILITIES.map((ability) => {
            const score = base[ability];
            const currentCost = POINT_BUY_COST[score] ?? 0;
            const nextCost = POINT_BUY_COST[score + 1];
            const canIncrement = score < 15 && nextCost !== undefined && pointBuySpent - currentCost + nextCost <= POINT_BUY_BUDGET;
            const modifier = modifiers?.[ability];
            return (
              <tr key={ability}>
                <td>{ability}</td>
                <td>
                  {method === "standard" && (
                    <select value={score} onChange={(e) => setAbility(ability, Number(e.target.value))}>
                      <option value={score}>{score}</option>
                      {STANDARD_ARRAY.filter((v) => !usedInStandardArray.includes(v)).map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  )}
                  {method === "pointbuy" && (
                    <span className="point-buy-stepper">
                      <button type="button" disabled={score <= 8} onClick={() => setAbility(ability, score - 1)}>
                        −
                      </button>
                      <span className="point-buy-stepper__value">{score}</span>
                      <button type="button" disabled={!canIncrement} onClick={() => setAbility(ability, score + 1)}>
                        +
                      </button>
                    </span>
                  )}
                  {method === "manual" && (
                    <input
                      type="number"
                      value={score}
                      onChange={(e) => setAbility(ability, Number(e.target.value))}
                    />
                  )}
                </td>
                <td>{modifier === undefined ? "—" : modifier >= 0 ? `+${modifier}` : modifier}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Add ability-table rules to `frontend/src/index.css`**

Add at the end of the file:

```css
.ability-method-selector {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.ability-table {
  border-collapse: collapse;
}

.ability-table th,
.ability-table td {
  border: 1px solid #ccc;
  padding: 6px 12px;
  text-align: left;
}

.point-buy-stepper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.point-buy-stepper__value {
  min-width: 1.5em;
  text-align: center;
  display: inline-block;
}
```

- [ ] **Step 3: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/abilities`. Confirm the table shows 6 rows, "Standard Array" selected by default, every score `<select>` initially showing 10 with 15/14/13/12/8 as the other options (all six abilities start at 10 in `emptyDraft`, which isn't itself a Standard Array value in five of six slots). Pick 15 for STR — confirm 15 disappears from the other five dropdowns' option lists (can't be double-assigned) and the Modifier column shows `+2` for STR after the debounce. Switch to "Point Buy" — confirm "Points Remaining: 27" (all scores reset visually to whatever `base` currently holds — the method switch doesn't reset scores, only which editor drives them) and that clicking `+` on an 8 costs 1 point, deducted from the remaining total; confirm `+` disables once the budget would be exceeded. Switch to "Manual" — confirm a plain number input per ability, editable to any value.

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/AbilitiesPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: add real Abilities editor (Standard Array / Point Buy / Manual)

All three methods are purely client-side UI over draft.abilities.base
— the engine only ever consumes the final numbers, regardless of how
they were produced, so no backend change was needed. Modifiers shown
in the table come straight from resolution.derived.abilityModifiers
(Phase 1a), not recomputed client-side.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Export page

**Files:**
- Modify: `frontend/src/pages/ExportPage.tsx`

**Interfaces:**
- Consumes: `useDraft()` (Task 1), `useResolutionContext()`

- [ ] **Step 1: Rewrite `frontend/src/pages/ExportPage.tsx`**

```tsx
import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  const pendingChoices = resolution.choices.filter((c) => c.status === "pending");
  const canExport = resolution.problems.length === 0 && pendingChoices.length === 0;

  async function handleExport() {
    setExporting(true);
    setExportError(null);
    try {
      const resp = await fetch("/api/export/yaml", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!resp.ok) {
        const body = (await resp.json()) as { problems?: { message: string }[] };
        throw new Error(body.problems?.map((p) => p.message).join("; ") ?? `export failed: ${resp.status}`);
      }
      const text = await resp.text();
      const blob = new Blob([text], { type: "application/x-yaml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${draft.name || "character"}.yaml`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="page">
      <h1>Export {loading && "…"}</h1>
      {resolution.problems.length > 0 && (
        <div>
          <h2>Problems</h2>
          <ul>
            {resolution.problems.map((p) => (
              <li key={p.id}>{p.message}</li>
            ))}
          </ul>
        </div>
      )}
      {pendingChoices.length > 0 && (
        <div>
          <h2>Unresolved choices</h2>
          <ul>
            {pendingChoices.map((c) => (
              <li key={c.id}>{c.label}</li>
            ))}
          </ul>
        </div>
      )}
      {canExport && <p>Всичко е готово за експорт.</p>}
      {exportError && <p style={{ color: "red" }}>{exportError}</p>}
      <button type="button" disabled={!canExport || exporting} onClick={handleExport}>
        {exporting ? "Изтегляне…" : "Изтегли YAML"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/export` with an empty/default draft. Confirm the "Unresolved choices" section is empty (no class/background/species picked means no choices exist at all — this is Phase 1a's "empty draft resolves gracefully" guarantee showing through) but the "Изтегли YAML" button is enabled anyway (`resolution.problems.length === 0 && pendingChoices.length === 0` — both true for a totally empty draft). Click it — confirm a `character.yaml` file downloads (or whatever the current draft name is) containing minimal/empty-ish data. Now go build out a real character (pick Fighter, Acolyte, Human, an ability method, but leave Fighting Style unpicked) and return to `/export` — confirm "Unresolved choices" now lists "Fighting Style" and the button is disabled. Pick a Fighting Style, wait for the debounce, return to `/export` — confirm the list clears and the button re-enables; click it and confirm the downloaded YAML contains the real character data (class, background, species, abilities, derived stats).

```bash
kill %1 %2
```

- [ ] **Step 4: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/ExportPage.tsx
git commit -m "$(cat <<'EOF'
feat: add real Export page — validation summary + YAML download

Surfaces resolution.problems and any still-pending choices, and only
enables the download once both are clear. POSTs the current Draft to
Phase 1a's /api/export/yaml and triggers a real browser download via
a Blob + object URL — no server-side file storage involved.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: End-to-end verification

**Files:** none created or modified — this task is pure verification, run by the controller (not dispatched to an implementer), the same way Phase 0's and Phase 1a's closing verification tasks were.

**Interfaces:** none — consumes the finished Task 1-7 system as a whole.

- [ ] **Step 1: Run the full test suite one more time (frontend typecheck/build + backend pytest)**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck && npm run build
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -q
cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/ -q
```

Expected: all clean — frontend build succeeds, server's 63 tests pass, v1's 396 tests pass (unaffected by a frontend-only plan, but confirm nothing else regressed).

- [ ] **Step 2: Full live click-through building one complete character start to finish**

Start both servers, open the app in a real browser, and build a complete Fighter/Acolyte/Human level-1 character end to end: set a name on Home, pick Fighter and its Fighting Style + 2 skills on Class, pick Acolyte and 2 languages on Background, pick Human and its Bonus Language on Species, pick a Point Buy allocation on Abilities, confirm StepNav's pending-choice badges drop to zero on every completed step, visit Export and confirm zero problems/pending choices, and download the YAML — read the downloaded file and confirm it reflects every choice actually made (class, background, species, ability scores and modifiers, HP, AC, proficiencies).

- [ ] **Step 3: Confirm no stray server process is left running**

```bash
ps aux | grep -E "app\.py|vite" | grep -v grep
```

Expected: empty output.
