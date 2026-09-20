# Preferences UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Preferences section to the Home page so `draft.preferences` (already present in the `Draft` type and `emptyDraft` default since an earlier phase, but with no UI ever able to change it) becomes actually settable. This closes a specific, previously-identified gap: Phase 3a built a real manual-HP-roll UI in `ClassPage.tsx` (one roll input per level, gated on `hitPointType === "manual"`) that has been completely unreachable since it shipped, because nothing anywhere lets a player switch `hitPointType` away from its `"fixed"` default.

**Architecture:** Three new reducer actions (`SET_HIT_POINT_TYPE`, `SET_ADVANCEMENT_TYPE`, `SET_USE_PREREQUISITE`) added to `frontend/src/DraftContext.tsx`, each mirroring the existing `SET_ABILITY_METHOD` action's exact shape (a simple single-field replace, no cascading resets — switching HP type or advancement type doesn't invalidate any other part of the draft, unlike `SET_CLASS`/`SET_SPECIES`). A new `PreferencesSection` block added to `frontend/src/pages/HomePage.tsx` — two radio-button groups (Hit Point Type, Advancement Type) and two checkboxes (Use Prerequisites: Feats, Multiclass), each dispatching its own action.

**Tech Stack:** React + TypeScript (Vite), same as every other frontend phase. No test framework configured — verification is `tsc -b` (via `npm run build`) plus manual browser verification, specifically confirming the previously-unreachable manual-HP-roll UI becomes reachable through this new toggle.

## Global Constraints

- **No behavior change to anything except making `preferences` settable.** `draft.preferences`'s shape, `emptyDraft`'s defaults, and every downstream consumer (`server/engine/resolve.py` already reads `draft.get("preferences")` — unchanged by this plan) all stay exactly as they are.
- **Bulgarian UI text**, matching every other page in this app (see `HomePage.tsx`'s existing "Зареждане…", "Грешка", "Опитай пак" for tone/register).
- **`npm run build` (from `frontend/`) must succeed with zero errors** after the task.
- **The manual-HP-roll UI in `ClassPage.tsx` must become genuinely reachable and confirmed working** via a real browser check — this is the whole point of the task, not just "the toggle exists."

---

### Task 1: Preferences UI and reducer actions

**Files:**
- Modify: `frontend/src/DraftContext.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`

**Interfaces:**
- Consumes: `Draft["preferences"]` (already defined in `frontend/src/types.ts` as `{ advancementType: "milestone" | "xp"; hitPointType: "fixed" | "manual"; usePrerequisites: { feats: boolean; multiclass: boolean } }` — unchanged by this task).
- Produces: `SET_HIT_POINT_TYPE`, `SET_ADVANCEMENT_TYPE`, `SET_USE_PREREQUISITE` reducer actions.

- [ ] **Step 1: Add the three new actions to `frontend/src/DraftContext.tsx`**

Find the `Action` union type (currently lines 25-42). Add three new variants, placed near `SET_ABILITY_METHOD` since they're the same kind of simple-preference action:

```typescript
  | { type: "SET_HIT_POINT_TYPE"; hitPointType: Draft["preferences"]["hitPointType"] }
  | { type: "SET_ADVANCEMENT_TYPE"; advancementType: Draft["preferences"]["advancementType"] }
  | { type: "SET_USE_PREREQUISITE"; field: keyof Draft["preferences"]["usePrerequisites"]; value: boolean }
```

Find the `reducer` function's `switch` statement. Add three new cases, right after the existing `SET_ABILITY_METHOD` case (currently lines 99-100), mirroring its exact single-field-replace shape:

```typescript
    case "SET_HIT_POINT_TYPE":
      return { ...state, preferences: { ...state.preferences, hitPointType: action.hitPointType } };
    case "SET_ADVANCEMENT_TYPE":
      return { ...state, preferences: { ...state.preferences, advancementType: action.advancementType } };
    case "SET_USE_PREREQUISITE":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          usePrerequisites: { ...state.preferences.usePrerequisites, [action.field]: action.value },
        },
      };
```

- [ ] **Step 2: Add a Preferences section to `frontend/src/pages/HomePage.tsx`**

Read the current file in full first (it's short, ~35 lines) to match its existing structure exactly — a `<label>`-wrapped `<input>` for the character name, then a `<h2>Resolution (from /api/resolve)</h2>` section showing loading/error/warnings.

Add a new `<h2>Preferences</h2>` section, placed between the name `<label>` and its explanatory `<p>` (or right after that `<p>`, before the Resolution `<h2>` — either placement is fine, pick whichever reads more naturally once you see the real file). Use native `<fieldset>`/`<legend>` for each radio group (accessible, zero extra JS, consistent with this project's established "prefer native HTML controls" pattern already used elsewhere — e.g. `BackgroundPage.tsx`'s native `<details>`/`<summary>` collapsibles):

```tsx
      <h2>Preferences</h2>
      <fieldset>
        <legend>Точки живот на ниво</legend>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "fixed"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "fixed" })}
          />
          Фиксирани (средна стойност)
        </label>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "manual"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "manual" })}
          />
          Хвърляне на зарове (ръчно въвеждане)
        </label>
      </fieldset>

      <fieldset>
        <legend>Тип напредък</legend>
        <label>
          <input
            type="radio"
            name="advancementType"
            checked={draft.preferences.advancementType === "milestone"}
            onChange={() => dispatch({ type: "SET_ADVANCEMENT_TYPE", advancementType: "milestone" })}
          />
          Ключови моменти
        </label>
        <label>
          <input
            type="radio"
            name="advancementType"
            checked={draft.preferences.advancementType === "xp"}
            onChange={() => dispatch({ type: "SET_ADVANCEMENT_TYPE", advancementType: "xp" })}
          />
          Опит (XP)
        </label>
      </fieldset>

      <fieldset>
        <legend>Изисквания</legend>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.feats}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "feats", value: e.target.checked })}
          />
          Прояви на дарби
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.multiclass}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "multiclass", value: e.target.checked })}
          />
          Смяна на класове
        </label>
      </fieldset>
```

(These Bulgarian labels are a reasonable direct translation — if any read awkwardly once you see them rendered, adjust the wording, but keep the same meaning and keep every other page's existing register: short, plain, no jargon.)

- [ ] **Step 3: Type-check**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors.

- [ ] **Step 4: Manual browser verification — the actual point of this task**

Start the backend (`cd server && .venv/bin/python app.py`, if not already running) and the frontend dev server (`preview_start` with the `frontend-dev` launch.json config, or `cd frontend && npm run dev` if no server tool is available). Navigate to `/home`:

1. Confirm both new radio groups and both checkboxes render, with the "Fixed"/"Milestone" options checked by default (matching `emptyDraft`'s defaults) — unless a persisted `localStorage` draft from earlier testing already has different values, in which case whatever it has is what should show as checked (that's correct behavior, not a bug).
2. Click "Хвърляне на зарове (ръчно въвеждане)" to switch `hitPointType` to `"manual"`.
3. Navigate to `/class`, pick Fighter (or any class) at a level ≥ 2 if not already set.
4. **Confirm the manual HP-roll input boxes (one per level 2..current) are now visible** — this is the specific, previously-unreachable UI this task exists to unlock. Confirm typing a value into one of them updates the character's `derived.hitPointMax` (check via the page's own HP summary, or via `read_network_requests` on the `/api/resolve` call).
5. Navigate back to `/home`, switch back to "Фиксирани (средна стойност)", confirm the roll inputs disappear again on `/class` (the existing `ClassPage.tsx` gating logic, untouched by this task, should already handle this correctly).
6. Reload the page — confirm the preferences you set persisted (via the existing `localStorage` draft-persistence mechanism, untouched by this task).

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/DraftContext.tsx frontend/src/pages/HomePage.tsx
git commit -m "$(cat <<'EOF'
feat: add a Preferences section to the Home page

draft.preferences has existed in the Draft type and emptyDraft's
defaults since an early phase, but nothing anywhere could ever change
it — in particular, Phase 3a's manual-HP-roll UI in ClassPage.tsx
(gated on hitPointType === "manual") has been completely unreachable
since it shipped. Three new reducer actions (SET_HIT_POINT_TYPE,
SET_ADVANCEMENT_TYPE, SET_USE_PREREQUISITE) mirror the existing
SET_ABILITY_METHOD action's simple single-field-replace shape; a new
Preferences section on the Home page exposes them via native
fieldset/radio/checkbox controls.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- This plan is intentionally a single task — the UI and its reducer actions are too small and too tightly coupled (the UI is meaningless without the actions, the actions are meaningless without the UI) to split further, per the writing-plans skill's task-sizing guidance ("split only where a reviewer could meaningfully reject one task while approving its neighbor").
- `advancementType`/`usePrerequisites` don't yet have any real backend consumer (only `hitPointType` is read by `resolve.py` today) — that's fine and expected, matching this project's established pattern of building the full `Draft` shape ahead of every consumer catching up (e.g. `sources: string[]` has existed since Phase 0 for the same forward-looking reason). This task's job is only to make the field settable, not to wire up features that don't exist yet.
