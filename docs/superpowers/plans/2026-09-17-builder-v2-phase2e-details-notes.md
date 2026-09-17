# Builder v2 Phase 2e — Character Details & Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the architecture spec's §8 BACKGROUND-step requirement — "Character Details / Physical / Personality / Notes collapsibles" — the last unimplemented piece of that step, and the last of Phase 2's "notes and details" scope item (§10). `Draft.details` already exists in the type system (`{alignment?, faith?, lifestyle?, backstory?}`) but has zero UI, zero reducer action, and is never read by `resolve()` or `export.py` — it's dead weight in the type today. This plan expands it to a complete, standard 5e field set, wires it end to end, and — since this plan already touches `export.py` for a directly related reason — also closes the separate, long-tracked gap where `sheet.equipment` is computed but never rendered into the YAML export (same one-line fix, same file, no reason to leave it for a third touch of this function).

**Architecture:** Pure data pass-through, no engine computation. `Draft.details` expands from 4 to 15 optional string fields, grouped into the spec's four named sections (Character Details / Physical / Personality / Notes). A single generic `SET_DETAIL` reducer action (field name + value) replaces the need for 15 separate action types. `BackgroundPage.tsx` gains four native HTML `<details>`/`<summary>` collapsible sections — no custom component, no JS-managed open/closed state, matching the spec's own word "collapsibles" literally and keeping this a zero-design-work phase (native `<details>` needs no styling to be usable; the paper/parchment pass can restyle it later without any structural rework). `resolve()` validates and passes `draft.details` through to `sheet.details` unchanged (same defensive-copy pattern already used for other optional draft sub-objects), and `export.py` renders it (plus, opportunistically, `sheet.equipment`, already computed since Phase 2a but never exported).

**Tech Stack:** Same as every prior phase — React 19.3.0, TypeScript 7.0.2 frontend; Flask backend; no new dependencies.

## Global Constraints

- **No visual/design work.** Native `<details>`/`<summary>` needs no CSS to function; only minimal structural spacing (matching every prior phase's restraint) may be added. This waits for the separate paper/parchment design pass.
- **All 15 fields are optional strings** — nothing here is validated, computed, or cross-referenced against catalog data. There is no "wrong" value for a free-text alignment or a backstory paragraph; `resolve()`'s job is purely to pass the object through safely (guard against a malformed non-dict `details`, coerce non-string field values defensively), never to reject or transform content.
- **`SET_DETAIL` is one generic action**, not 15 specific ones — `{ type: "SET_DETAIL"; field: keyof Draft["details"]; value: string }`. This matches the codebase's existing preference for generic dispatch over per-field boilerplate (see `SET_CHOICE_SELECTION`'s single action handling every choice across every step).
- **Alignment is a fixed-vocabulary `<select>`, not free text** — the 9 standard D&D alignments are a well-known closed set (matching this project's existing preference for `<select>` over free text wherever a fixed vocabulary exists, e.g. `Preferences.advancementType`/`hitPointType`). Every other field is free text (`<input>` for short fields, `<textarea>` for longer ones — Personality Traits/Ideals/Bonds/Flaws/Backstory/Notes).
- **The equipment-export fix is one line, added alongside the details fix in the same function, not a separate task** — `sheet.equipment` has existed since Phase 2a; this plan doesn't change how it's computed, only that `export.py`'s `to_yaml()` finally includes it, closing a gap this project's own final reviews have flagged twice already (Phase 2a's and Phase 2c's final reviews both independently noted the export asymmetry).

---

### Task 1: `Draft.details` type expansion + reducer

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/DraftContext.tsx`

**Interfaces:**
- Produces: an expanded `Draft.details` shape and a new `SET_DETAIL` dispatchable action. Task 3 is the consumer.

- [ ] **Step 1: Expand `Draft.details` in `frontend/src/types.ts`**

Find this exact block:

```ts
  details: {
    alignment?: string;
    faith?: string;
    lifestyle?: string;
    backstory?: string;
  };
```

and replace it with:

```ts
  details: {
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
    notes?: string;
  };
```

- [ ] **Step 2: Add the `SET_DETAIL` action**

In `frontend/src/DraftContext.tsx`, add to the `Action` union (alongside `SET_ABILITY_SCORE`):

```ts
  | { type: "SET_DETAIL"; field: keyof Draft["details"]; value: string }
```

Add the reducer case (alongside `SET_ABILITY_SCORE`'s case):

```ts
    case "SET_DETAIL":
      return { ...state, details: { ...state.details, [action.field]: action.value } };
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/DraftContext.tsx
git commit -m "$(cat <<'EOF'
feat: expand Draft.details to the full Character Details/Physical/Personality/Notes field set

Draft.details grows from 4 fields to 15, grouped to match the
architecture spec's four BACKGROUND-step collapsibles. A single generic
SET_DETAIL action (field + value) handles all of them, matching the
codebase's existing preference for generic dispatch over per-field
action types.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend pass-through — `sheet.details`, and the equipment-export fix

**Files:**
- Modify: `server/engine/resolve.py`
- Modify: `server/export.py`
- Test: `server/tests/test_resolve.py`, `server/tests/test_export.py`

**Interfaces:**
- Consumes: `draft.get("details")` (a dict or absent/`None`).
- Produces: `sheet["details"]` — either `None` (no details submitted / malformed input) or a dict containing only the 15 known field names, each coerced to a string (non-string values dropped rather than crashing), unknown keys silently dropped. Also: `export.py`'s `to_yaml()` now includes `sheet["details"]` and `sheet["equipment"]` in the rendered document.

- [ ] **Step 1: Write failing `resolve()` tests**

Open `server/tests/test_resolve.py` first and match its existing draft-building/assertion conventions (read a handful of existing cases before writing new ones — this file has one consistent convention already established across ~600 lines, don't invent a different one). Add cases covering:
- A draft with `"details": {"alignment": "Chaotic Good", "backstory": "Раснал в Невървинтър."}` produces `sheet["details"] == {"alignment": "Chaotic Good", "backstory": "Раснал в Невървинтър."}` (only the submitted keys appear — this is NOT padded out to all 15 keys with `None` values; it's a sparse dict of whatever was actually submitted, matching the frontend's own optional-field `Draft.details` shape).
- A draft with no `"details"` key at all (or `"details": None`) produces `sheet["details"] is None`.
- A draft with `"details": "not a dict"` (malformed) produces `sheet["details"] is None` AND a problem is NOT raised (unlike `malformed-background`/`malformed-species`, which DO raise a problem — free-text notes are not load-bearing character data the way a class/background/species selection is; silently ignoring malformed details is the right failure mode here, not blocking the whole resolution with a problem the player can't act on).
- A draft with `"details": {"alignment": "Chaotic Good", "unknownField": "ignored", "faith": 12345}` produces `sheet["details"] == {"alignment": "Chaotic Good"}` — the unknown key is dropped, and the non-string `faith` value (`12345`) is ALSO dropped rather than crashing or being silently stringified (a defensive choice: coercing an accidental number to a string could mask a real frontend bug; dropping it is safer and the field simply doesn't appear, same as if it were never submitted).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k details`
Expected: FAIL (no `sheet["details"]` key exists yet).

- [ ] **Step 3: Implement in `server/engine/resolve.py`**

Add a module-level constant near the top of the file (alongside other module-level constants, if any exist — otherwise near the imports) listing the 15 known field names:

```python
_DETAIL_FIELDS = {
    "alignment", "faith", "lifestyle",
    "age", "height", "weight", "eyes", "skin", "hair",
    "personalityTraits", "ideals", "bonds", "flaws",
    "backstory", "notes",
}
```

Add a small helper function (near the other small helpers like `_join_desc`):

```python
def _sanitized_details(details_raw) -> dict | None:
    if not isinstance(details_raw, dict):
        return None
    result = {k: v for k, v in details_raw.items() if k in _DETAIL_FIELDS and isinstance(v, str)}
    return result if result else None
```

Note the last line: an empty dict (nothing valid survived sanitization, e.g. every key was unknown or non-string) collapses to `None` too — `sheet["details"]` is either "there's real content here" or `None`, never a pointless `{}`.

In `resolve()`, add the call (near where `equipment_dict`/`species` etc. are extracted from `draft`, following the same "extract once near the top" style already used for those):

```python
    details = _sanitized_details(draft.get("details"))
```

Add `"details": details,` to the existing `sheet = {...}` dict literal (alongside `"spells"`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k details`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all 127 existing plus your new cases, all green.

- [ ] **Step 5: Write failing export tests**

In `server/tests/test_export.py` (match its existing style), add cases:
- A resolution with `sheet["details"] = {"alignment": "Lawful Neutral"}` produces YAML containing `details:` with `alignment: Lawful Neutral` in it.
- A resolution with `sheet["details"] is None` produces YAML with `details: null` (matching the existing convention this file already uses for other optional `None` fields, e.g. `background: null` — confirm this convention by reading the file first, don't assume).
- A resolution with a non-empty `sheet["equipment"]` (e.g. `{"granted": [{"itemId": "chain-mail", "name": "Chain Mail", "qty": 1}], "chosen": [], "added": []}`) produces YAML containing the item name `Chain Mail` somewhere in the output — this is the equipment-export gap closing; write this test even though it's not new engine behavior, since `to_yaml()` itself is changing.

- [ ] **Step 6: Run to verify failure, then implement in `server/export.py`**

Run: `cd server && .venv/bin/python -m pytest tests/test_export.py -v`
Expected: FAIL.

Add two lines to the existing `doc = {...}` dict literal in `to_yaml()`:

```python
        "details": sheet["details"],
        "equipment": sheet["equipment"],
```

Place them in a sensible position in the dict (e.g. `details` near the other sheet-level identity fields like `name`/`background`; `equipment` near `proficiencies`/`spells`, which are the other "what does this character have" sections) — exact ordering doesn't matter functionally (YAML key order is preserved by `sort_keys=False` but has no semantic effect), just keep it readable.

- [ ] **Step 7: Run to verify tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_export.py -v`
Expected: PASS.

Then run the full backend suite once more: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 8: Empirically verify the equipment-export fix against a real character**

This closes a gap two separate final reviews (Phase 2a, Phase 2c) independently flagged — verify it for real, not just via the unit test. From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
catalog = load()
draft = {
    'classes': [{'classId': 'paladin', 'level': 1, 'choices': {}}],
    'details': {'alignment': 'Lawful Good', 'backstory': 'A wandering knight.'},
}
result = resolve(draft, catalog)
print(to_yaml(result))
"
```

Confirm the printed YAML shows Paladin's granted equipment (Chain Mail, etc. — Paladin has fixed starting gear, verified in Phase 2a) under an `equipment:` key, AND the submitted `details:` block with `alignment: Lawful Good` and the backstory text. If equipment is missing or details didn't come through, stop and investigate before committing.

- [ ] **Step 9: Commit**

```bash
git add server/engine/resolve.py server/export.py server/tests/test_resolve.py server/tests/test_export.py
git commit -m "$(cat <<'EOF'
feat: pass Draft.details through to sheet.details, include it and equipment in YAML export

resolve() now sanitizes and passes through the 15 optional character-
details fields (dropping unknown keys and non-string values defensively,
never raising a problem for malformed input — free-text notes aren't
load-bearing the way a class/background/species pick is). export.py now
renders both sheet.details and sheet.equipment — equipment has been
computed since Phase 2a but never appeared in the actual downloaded YAML,
a gap two separate final reviews (Phase 2a, Phase 2c) independently
flagged; this closes it in the same pass since export.py is already
being touched for the details fix.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: BackgroundPage collapsible sections

**Files:**
- Modify: `frontend/src/pages/BackgroundPage.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `useDraft()` (unchanged), `SET_DETAIL` (Task 1).

- [ ] **Step 1: Add four `<details>` sections to `frontend/src/pages/BackgroundPage.tsx`**

Add after the existing background-choice `ChoiceCard`s (at the end of the returned JSX, still inside the `<div className="page">`):

```tsx
      <details className="details-section">
        <summary>Данни за героя</summary>
        <label>
          Мирогледие
          <select value={draft.details.alignment ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "alignment", value: e.target.value })}>
            <option value="">—</option>
            <option value="Lawful Good">Законен добър</option>
            <option value="Neutral Good">Неутрален добър</option>
            <option value="Chaotic Good">Хаотичен добър</option>
            <option value="Lawful Neutral">Законен неутрален</option>
            <option value="True Neutral">Истински неутрален</option>
            <option value="Chaotic Neutral">Хаотичен неутрален</option>
            <option value="Lawful Evil">Законен зъл</option>
            <option value="Neutral Evil">Неутрален зъл</option>
            <option value="Chaotic Evil">Хаотичен зъл</option>
          </select>
        </label>
        <label>
          Вяра/Божество
          <input type="text" value={draft.details.faith ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "faith", value: e.target.value })} />
        </label>
        <label>
          Начин на живот
          <input type="text" value={draft.details.lifestyle ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "lifestyle", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Физически характеристики</summary>
        <label>
          Възраст
          <input type="text" value={draft.details.age ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "age", value: e.target.value })} />
        </label>
        <label>
          Височина
          <input type="text" value={draft.details.height ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "height", value: e.target.value })} />
        </label>
        <label>
          Тегло
          <input type="text" value={draft.details.weight ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "weight", value: e.target.value })} />
        </label>
        <label>
          Очи
          <input type="text" value={draft.details.eyes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "eyes", value: e.target.value })} />
        </label>
        <label>
          Кожа
          <input type="text" value={draft.details.skin ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "skin", value: e.target.value })} />
        </label>
        <label>
          Коса
          <input type="text" value={draft.details.hair ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "hair", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Личност</summary>
        <label>
          Черти на характера
          <textarea value={draft.details.personalityTraits ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "personalityTraits", value: e.target.value })} />
        </label>
        <label>
          Идеали
          <textarea value={draft.details.ideals ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "ideals", value: e.target.value })} />
        </label>
        <label>
          Връзки
          <textarea value={draft.details.bonds ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "bonds", value: e.target.value })} />
        </label>
        <label>
          Слабости
          <textarea value={draft.details.flaws ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "flaws", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Бележки</summary>
        <label>
          Предистория
          <textarea value={draft.details.backstory ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "backstory", value: e.target.value })} />
        </label>
        <label>
          Допълнителни бележки
          <textarea value={draft.details.notes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "notes", value: e.target.value })} />
        </label>
      </details>
```

- [ ] **Step 2: Add minimal structural CSS**

Add to `frontend/src/index.css`:

```css
.details-section {
  margin: 12px 0;
  border: 1px solid #ccc;
  padding: 8px 12px;
}

.details-section summary {
  cursor: pointer;
  font-weight: bold;
}

.details-section label {
  display: block;
  margin: 8px 0 4px;
}

.details-section input,
.details-section select,
.details-section textarea {
  display: block;
  width: 100%;
  max-width: 480px;
  box-sizing: border-box;
}

.details-section textarea {
  min-height: 60px;
}
```

- [ ] **Step 3: Typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: no errors.

- [ ] **Step 4: Manual verification**

```bash
cd server && .venv/bin/python app.py &
sleep 1
cd ../frontend && npm run dev &
sleep 2
```

On `/background`, select any background. Confirm four collapsible sections appear below the existing background choices, all closed by default: "Данни за героя", "Физически характеристики", "Личност", "Бележки". Click each to expand — confirm it stays open independently of the others (native `<details>` behavior, no accordion-style mutual exclusion needed or implemented). Fill in a few fields across different sections (e.g. alignment dropdown, age text field, a personality-traits textarea). Navigate away to `/equipment` and back to `/background` — confirm the filled values persisted (survives page-component remount via Draft context, same as every other field in this app) and the sections are collapsed again by default (native `<details>` doesn't persist open/closed state across a remount, which is expected and fine — the DATA persists, only the UI's open/closed display state resets, matching how every `<ChoiceCard>` elsewhere in this app already behaves on remount). Reload the whole page — confirm the filled values survived via localStorage. Go to `/export`, download YAML — confirm the filled details fields (and, separately, confirm equipment) both appear in the downloaded file.

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/BackgroundPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: add Character Details/Physical/Personality/Notes collapsibles to BackgroundPage

Implements the last unimplemented piece of the architecture spec's
BACKGROUND step. Uses native <details>/<summary> elements rather than a
custom accordion component — zero JS state needed for open/closed
behavior, and it needs no styling to be usable, keeping this a
zero-visual-design-work phase per the project's established convention
of deferring styling to the dedicated paper/parchment pass.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- Task 2's `_sanitized_details` deliberately does NOT raise a `problems` entry for malformed `details` input, unlike `malformed-background`/`malformed-species`/`malformed-equipment-choices` elsewhere in `resolve.py`, which DO raise problems. This is a considered inconsistency, not an oversight: a class/background/species selection is structurally load-bearing (derived stats depend on it), so silent failure there would hide a real bug from the player. Free-text notes are cosmetic — if a browser extension or a future API client sends `"details": 42`, silently treating it as "no details submitted" is strictly better UX than surfacing a scary "problem" banner for a field nobody's blocked on. Don't "fix" this into consistency with the other malformed-input handlers without re-reading this rationale.
- Task 2's equipment-export fix is deliberately bundled into this plan rather than spun off as its own follow-up (unlike how it was handled twice before — Phase 2a's and Phase 2c's final reviews both flagged it and both times it was correctly left for later, since neither of those phases had any other reason to touch `export.py`'s equipment path). This plan already needs `export.py` open for the details fix, so bundling avoids a third separate touch of the same function for what is structurally the same kind of one-line fix. If the assigned implementer feels this is scope creep, it isn't — it's explicitly authorized by this plan's Goal and Global Constraints sections; don't skip it.
