# Builder v2 Phase 2b — Equipment Browser UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the frontend up to Phase 2a's equipment engine, the same way Phase 1b wired it up to Phase 1a's rules engine. `EquipmentPage.tsx` already renders real `equipment`-kind `Choice`s (that part was generic from Phase 0) but its `onChange` is still a no-op stub, and there is no way to browse `GET /api/items`, add an item to the draft, or equip/unequip/remove it. This plan closes all three gaps.

**Architecture:** Pure frontend work — no backend changes, no new endpoints (Phase 2a already shipped `GET /api/items` and the real `equipment`-kind choices). A new `useItems()` hook (mirroring `useCatalog()`'s shape but with the debounced-fetch pattern `useResolution()` already established, since item search needs to re-query on every keystroke) fetches the item list. The `Draft` type and reducer gain an `equipment.choices` field (the one piece of the Phase 1b-era Draft type that Phase 2a's backend already expected but no frontend code could populate yet) plus `ADD_ITEM`/`REMOVE_ITEM`/`TOGGLE_EQUIPPED` actions for the "Current Inventory" section.

**Tech Stack:** Same as every prior frontend phase — React 19.3.0, TypeScript 7.0.2, no new dependencies.

## Global Constraints

- **No visual/design work.** Only the minimal structural CSS needed for the new item-browser list and inventory list — borders, spacing, matching every prior phase's exact minimal style. No colors, no typography, no branding.
- **`<ChoiceCard>`/`<ChoicePicker>` are reused unchanged**, same as every prior frontend phase.
- **Granted and chosen equipment (`sheet.equipment.granted`/`sheet.equipment.chosen`) are read-only informational displays, not editable.** Per Phase 2a's own established design, both are always treated as equipped with no toggle — there's nowhere in the `Draft` shape to store one, and inventing one is out of scope here too. Only `draft.equipment.added` (items from the item browser) gets add/remove/equip-toggle UI.
- **Item names for display come from `resolution.sheet.equipment.*`, never re-derived client-side.** Phase 2a's `resolve()` already resolves `granted`/`chosen`/`added` entries into `{itemId, name, qty, ...}` shapes with real names — the Current Inventory section reads from there, not from a second client-side name lookup against `useItems()`'s results. This avoids two sources of truth for the same data and matches how every other page already treats `resolution` as authoritative.
- **`ADD_ITEM` increments quantity if the item is already in `draft.equipment.added`, rather than creating a duplicate entry.** `REMOVE_ITEM` removes the whole entry (not a single unit) — there is no quantity-stepper UI in this phase (an explicit, documented simplification; the architecture spec's fuller "quantity stepper" vision is deferred).
- **Equipment `Choice`s dispatch through the existing generic `SET_CHOICE_SELECTION` action** (already handles `class`/`background`/`species`; this plan adds the `equipment` branch) — no new choice-dispatch action is invented.

---

### Task 1: Draft type + reducer extensions

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/DraftContext.tsx`

**Interfaces:**
- Produces: `Draft.equipment.choices: Record<string, string[]>` (the field Phase 2a's backend already reads defensively via `draft.get("equipment", {}).get("choices", {})`), and three new dispatchable actions — `ADD_ITEM`, `REMOVE_ITEM`, `TOGGLE_EQUIPPED` — plus a new `"equipment"` case in `SET_CHOICE_SELECTION`'s existing switch. Task 3 is the consumer of all of these.

- [ ] **Step 1: Add `choices` to `Draft.equipment` in `frontend/src/types.ts`**

Find this exact block:

```ts
  equipment: {
    startingChoice?: string;
    added: { itemId: string; qty: number; equipped: boolean }[];
    skipped: boolean;
  };
```

and replace it with:

```ts
  equipment: {
    startingChoice?: string;
    choices: Record<string, string[]>;
    added: { itemId: string; qty: number; equipped: boolean }[];
    skipped: boolean;
  };
```

- [ ] **Step 2: Update `emptyDraft` and the `Action`/`reducer` in `frontend/src/DraftContext.tsx`**

Find:

```ts
  equipment: { added: [], skipped: false },
```

and replace it with:

```ts
  equipment: { choices: {}, added: [], skipped: false },
```

Find the `Action` union's closing member:

```ts
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] };
```

and replace it with:

```ts
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] }
  | { type: "ADD_ITEM"; itemId: string }
  | { type: "REMOVE_ITEM"; itemId: string }
  | { type: "TOGGLE_EQUIPPED"; itemId: string };
```

Find the `SET_CHOICE_SELECTION` case's final fallback line:

```ts
      return state; // subclass/feature/equipment choices aren't dispatched from anywhere in Phase 1b
    }
```

and replace it with (adding a real `equipment` branch before the now-narrower fallback comment):

```ts
      if (action.source === "equipment") {
        return {
          ...state,
          equipment: {
            ...state.equipment,
            choices: { ...state.equipment.choices, [action.choiceId]: action.selected },
          },
        };
      }
      return state; // subclass/feature choices aren't dispatched from anywhere yet
    }
```

Finally, find the `SET_CHOICE_SELECTION` case's closing brace and the `default:` case right after it:

```ts
    default:
      return state;
  }
}
```

and insert the three new cases immediately before `default:`:

```ts
    case "ADD_ITEM": {
      const existing = state.equipment.added.find((e) => e.itemId === action.itemId);
      const added = existing
        ? state.equipment.added.map((e) => (e.itemId === action.itemId ? { ...e, qty: e.qty + 1 } : e))
        : [...state.equipment.added, { itemId: action.itemId, qty: 1, equipped: false }];
      return { ...state, equipment: { ...state.equipment, added } };
    }
    case "REMOVE_ITEM":
      return {
        ...state,
        equipment: { ...state.equipment, added: state.equipment.added.filter((e) => e.itemId !== action.itemId) },
      };
    case "TOGGLE_EQUIPPED":
      return {
        ...state,
        equipment: {
          ...state.equipment,
          added: state.equipment.added.map((e) => (e.itemId === action.itemId ? { ...e, equipped: !e.equipped } : e)),
        },
      };
    default:
      return state;
  }
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

Open the app, clear `localStorage` (so a fresh `emptyDraft` loads), and in the browser console run `JSON.parse(localStorage.getItem("dnd-builder-draft-v2")).equipment` — confirm it shows `{choices: {}, added: [], skipped: false}`, proving the new field is present in the persisted draft shape from a cold start.

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/types.ts frontend/src/DraftContext.tsx
git commit -m "$(cat <<'EOF'
feat: add Draft.equipment.choices + item add/remove/equip actions

Draft.equipment.choices is the one field Phase 2a's backend already
reads defensively but no frontend code could populate — this closes
that gap the same way Phase 1b closed Phase 1a's equivalent gaps for
class/background/species. ADD_ITEM increments quantity for an
already-added item rather than duplicating it; REMOVE_ITEM drops the
whole entry (no per-unit removal UI in this phase); TOGGLE_EQUIPPED
flips one entry's equipped flag.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `useItems` hook

**Files:**
- Create: `frontend/src/useItems.ts`

**Interfaces:**
- Produces: `useItems(category: string, query: string): { items: CatalogItem[], loading: boolean, error: string | null, retry: () => void }` — Task 3 is the consumer.

- [ ] **Step 1: Write `frontend/src/useItems.ts`**

```ts
import { useCallback, useEffect, useRef, useState } from "react";

export interface CatalogItem {
  id: string;
  name: string;
  category: string;
}

interface ItemsState {
  items: CatalogItem[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 150;

export function useItems(category: string, query: string): ItemsState & { retry: () => void } {
  const [state, setState] = useState<ItemsState>({ items: [], loading: true, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (query) params.set("q", query);
      fetch(`/api/items?${params.toString()}`)
        .then((resp) => {
          if (!resp.ok) throw new Error(`items fetch failed: ${resp.status}`);
          return resp.json() as Promise<{ items: CatalogItem[] }>;
        })
        .then((data) => {
          if (id !== requestId.current) return;
          setState({ items: data.items, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current) return;
          const message = err instanceof Error ? err.message : String(err);
          setState((s) => ({ ...s, loading: false, error: message }));
        });
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [category, query, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
```

(This mirrors `useResolution.ts`'s exact debounce + stale-response-guard idiom — a request-id ref, not a boolean `cancelled` flag, since search-as-you-type can fire several overlapping requests the same way resolve() can.)

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
curl -s "http://127.0.0.1:8000/api/items?category=armor" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['items']))"
kill %1
```

Expected: `13` — confirms the exact shape `useItems` expects is what Phase 2a's already-shipped endpoint actually returns (no live browser check needed yet; Task 3 exercises the hook for real).

- [ ] **Step 4: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/useItems.ts
git commit -m "$(cat <<'EOF'
feat: add useItems hook for GET /api/items

Debounced (150ms) with the same request-id stale-response guard
useResolution.ts already established — search-as-you-type can fire
several overlapping requests the same way resolve() can.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Real EquipmentPage — starting-kit choices, item browser, inventory

**Files:**
- Modify: `frontend/src/pages/EquipmentPage.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `useDraft()` (Phase 1b), `useResolutionContext()` (Phase 1a/1b, unchanged), `useItems()` (Task 2), `<ChoiceCard>` (Phase 0, unchanged), `ADD_ITEM`/`REMOVE_ITEM`/`TOGGLE_EQUIPPED`/`SET_CHOICE_SELECTION` (Task 1)

- [ ] **Step 1: Rewrite `frontend/src/pages/EquipmentPage.tsx`**

```tsx
import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useItems } from "../useItems";
import { ChoiceCard } from "../components/ChoiceCard";

const CATEGORIES = [
  { value: "", label: "Всички" },
  { value: "weapon", label: "Оръжия" },
  { value: "armor", label: "Брони" },
  { value: "adventuring-gear", label: "Снаряжение" },
  { value: "tools", label: "Инструменти" },
  { value: "mounts-and-vehicles", label: "Превозни средства" },
];

interface SheetEquipment {
  granted: { itemId: string; name: string; qty: number }[];
  chosen: { itemId: string; name: string; qty: number }[];
  added: { itemId: string; name: string; qty: number; equipped: boolean }[];
}

export function EquipmentPage() {
  const { dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const items = useItems(category, query);

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

  const equipmentChoices = resolution.choices.filter((c) => c.source.kind === "equipment");

  function handleChoiceChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "equipment", choiceId, selected });
  }

  const sheetEquipment = resolution.sheet.equipment as SheetEquipment | undefined;

  return (
    <div className="page">
      <h1>Equipment {loading && "…"}</h1>

      {equipmentChoices.length === 0 && <p>Няма избори за стартова екипировка.</p>}
      {equipmentChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChoiceChange} />
      ))}

      {sheetEquipment && sheetEquipment.granted.length > 0 && (
        <div className="equipment-section">
          <h2>Получена екипировка</h2>
          <ul>
            {sheetEquipment.granted.map((g) => (
              <li key={g.itemId}>
                {g.name} ×{g.qty}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sheetEquipment && sheetEquipment.chosen.length > 0 && (
        <div className="equipment-section">
          <h2>Избрана екипировка</h2>
          <ul>
            {sheetEquipment.chosen.map((c) => (
              <li key={c.itemId}>{c.name}</li>
            ))}
          </ul>
        </div>
      )}

      <h2>Предмети</h2>
      <input type="text" placeholder="Търсене…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select value={category} onChange={(e) => setCategory(e.target.value)}>
        {CATEGORIES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
      {items.error && (
        <p>
          Грешка: {items.error}{" "}
          <button type="button" onClick={items.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="item-browser-list">
        {items.items.map((item) => (
          <li key={item.id}>
            <span>{item.name}</span>
            <button type="button" onClick={() => dispatch({ type: "ADD_ITEM", itemId: item.id })}>
              Add
            </button>
          </li>
        ))}
      </ul>

      <h2>Инвентар</h2>
      {(!sheetEquipment || sheetEquipment.added.length === 0) && <p>Няма добавени предмети.</p>}
      {sheetEquipment && sheetEquipment.added.length > 0 && (
        <ul className="inventory-list">
          {sheetEquipment.added.map((entry) => (
            <li key={entry.itemId}>
              <span>
                {entry.name} ×{entry.qty}
              </span>
              <label>
                <input
                  type="checkbox"
                  checked={entry.equipped}
                  onChange={() => dispatch({ type: "TOGGLE_EQUIPPED", itemId: entry.itemId })}
                />
                Екипиран
              </label>
              <button type="button" onClick={() => dispatch({ type: "REMOVE_ITEM", itemId: entry.itemId })}>
                Премахни
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add item-browser/inventory CSS rules to `frontend/src/index.css`**

Add at the end of the file:

```css
.equipment-section {
  margin-bottom: 16px;
}

.equipment-section ul {
  margin: 4px 0;
  padding-left: 20px;
}

.item-browser-list,
.inventory-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #ccc;
}

.item-browser-list li,
.inventory-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
  border-bottom: 1px solid #eee;
}

.item-browser-list li:last-child,
.inventory-list li:last-child {
  border-bottom: none;
}

.item-browser-list li span,
.inventory-list li span {
  flex: 1;
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

Build a Fighter character on `/class` first (pick Fighter, resolve its 2 skill/feature choices), then open `/equipment`. Confirm 3 real "Starting Equipment" choice cards render (armor choice, ranged-weapon-or-handaxes choice, pack choice — matching Phase 2a's confirmed 3-of-4-resolvable Fighter envelopes). Pick "Chain Mail" for the armor choice — confirm the card becomes resolved and, after the debounce, visiting `/abilities` or checking the response shows `derived.armorClass` reflecting heavy armor (16, ignoring DEX). Back on `/equipment`, confirm a "Получена екипировка" (granted) section is NOT shown for Fighter (Fighter has no fixed starting_equipment — this is expected, matches Phase 2a's own finding that Fighter is the one class with none) but a "Избрана екипировка" (chosen) section IS shown listing "Chain Mail". In the item browser, search "torch" — confirm the list filters to matching items; click "Add" on it — confirm it appears in "Инвентар" with an unchecked "Екипиран" checkbox and qty 1; click "Add" again — confirm qty becomes 2, not a duplicate row; check the "Екипиран" checkbox — confirm it toggles; click "Премахни" — confirm the row disappears. Reload the page — confirm the draft (including equipment choices and inventory) survived via localStorage.

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/EquipmentPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: wire EquipmentPage to real starting-kit choices + item browser

Replaces the console.log-free-but-still-no-op onChange stub with real
SET_CHOICE_SELECTION dispatch (mirroring Class/Background/Species from
Phase 1b), adds a searchable/filterable item browser backed by Phase
2a's GET /api/items, and a Current Inventory section with add/equip-
toggle/remove wired to the new Draft actions. Granted and chosen
equipment (fixed starting gear, resolved kit choices) are shown as
read-only informational lists, sourced from resolution.sheet.equipment
rather than re-derived client-side.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: End-to-end verification

**Files:** none created or modified — this task is pure verification, run by the controller.

**Interfaces:** none — consumes the finished Task 1-3 system as a whole.

- [ ] **Step 1: Run the full test suite one more time (frontend typecheck/build + backend pytest + v1 pytest)**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck && npm run build
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -q
cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/ -q
```

Expected: all clean — frontend build succeeds, server's 96 tests pass, v1's 396 tests pass.

- [ ] **Step 2: Full live click-through building one complete character with equipment, start to finish**

Start both servers, open the app in a real browser, and build a complete Fighter/Acolyte/Human level-1 character end to end (name, class + its choices, background + its choices, species + its choice, abilities), then on Equipment: resolve all 3 starting-kit choices, add and equip a torch from the browser, then visit Export — confirm zero problems, zero pending choices (equipment-kind included), and download the YAML. Read the downloaded file and confirm it reflects the chosen armor's effect on `armorClass` and (once the separately-flagged `task_05216a5a` follow-up lands) eventually the equipment list itself — for now, just confirm the numeric derived stats are correct and the export succeeds without error.

- [ ] **Step 3: Confirm no stray server process is left running**

```bash
ps aux | grep -E "app\.py|vite" | grep -v grep
```

Expected: empty output.
