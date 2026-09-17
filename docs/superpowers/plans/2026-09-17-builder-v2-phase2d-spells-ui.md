# Builder v2 Phase 2d — Spells UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the frontend up to Phase 2c's spell engine, the same way Phase 2b wired it up to Phase 2a's equipment engine. Cantrip/spell `Choice`s (`source.kind === "class"`, ids ending `:spells-cantrips`/`:spells-known`) already render today — generically, mixed in with every other class choice, since `ClassPage.tsx` has never distinguished them. This plan splits the CLASS step into `CLASS FEATURES` / `SPELLS` tabs per the architecture spec's §8 step description, and adds a searchable spell-reference library so a player can actually read what a spell *does* before picking it — right now `<ChoicePicker>` shows only a spell's bare name.

**Architecture:** A new `GET /api/spells` endpoint (mirrors Phase 2a's `GET /api/items` exactly) exposes full spell detail (school, casting time, range, components, duration, concentration/ritual flags, description) filtered by class/level/search — Phase 2c's `Catalog.spells` already has this data indexed, it's just never been exposed over HTTP. A new `useSpells()` hook (mirrors `useItems()`'s debounced-fetch/stale-response-guard pattern exactly) consumes it. `ClassPage.tsx` gains a tab split: existing class-feature/proficiency choices stay under `CLASS FEATURES` (default tab, unchanged rendering), spell choices move to a new `SPELLS` tab alongside the new spell-library browser. `<ChoiceCard>`/`<ChoicePicker>` are reused unchanged — actual spell selection still happens through them exactly as it does today; the library is a read-only reference panel next to them, the same split Phase 2b used for equipment (real choices via the generic picker, a separate browsable list for anything the picker's bare-label options can't show).

**Tech Stack:** Same as every prior frontend phase — React 19.3.0, TypeScript 7.0.2, no new dependencies. Backend: Flask, same style as every existing route in `server/app.py`.

## Global Constraints

- **No visual/design work.** Only the minimal structural CSS needed for the tab bar and spell-library list — borders, spacing, matching every prior phase's exact minimal style (see `frontend/src/index.css`'s existing `.item-browser-list`/`.inventory-list` rules from Phase 2b for the level of restraint expected). No colors, no typography, no branding — this waits for the separate paper/parchment design pass.
- **`<ChoiceCard>`/`<ChoicePicker>` are reused unchanged**, same as every prior frontend phase. The spell library is supplementary reference content, not a second selection mechanism — a spell is picked exactly once, through the existing generic checkbox list; the library never dispatches a selection itself.
- **Spell choices are distinguished from other class choices by parsing the existing, already-stable choice id suffix** (`:spells-cantrips` / `:spells-known`, set by Phase 2c's `_spell_choice_templates`) — no new `source.kind` value, no new field on `Choice`. This matches this codebase's established pattern of parsing structured ids rather than inventing new discriminator fields (e.g. equipment bundle ids are already parsed by splitting on `"+"`).
- **The `SPELLS` tab only appears for a class that actually has spell choices at level 1** (6 of 12 SRD classes — Bard, Cleric, Druid, Sorcerer, Warlock, Wizard; Paladin and Ranger have real `spellcasting` data but zero slots at level 1 per Phase 2c, so they correctly show no `SPELLS` tab, same as any non-caster). Do not show an empty tab for a class with nothing in it.
- **The spell library is scoped to the currently selected class** (`GET /api/spells?class=<id>`) — it is a reference for "what could I pick from *my* class list," not a browse-all-319-spells tool. `useSpells()` must not fetch at all when there is no class selected or the class has no spell choices (an empty `class` query param is a wasted 319-row fetch nobody asked for; the hook skips fetching entirely rather than sending one).
- **No new endpoints touch `resolve()` or the `Draft` shape.** This phase adds one new read-only catalog-browsing route (`/api/spells`), following `/api/items`'s exact precedent — no engine changes, no new `Draft` fields, no new reducer actions. Unlike equipment (which needed `Draft.equipment.added`/`choices` for free-form item adding), there is nothing analogous to "add an extra spell outside a Choice" in scope here.

---

### Task 1: `GET /api/spells` endpoint

**Files:**
- Modify: `server/app.py`
- Test: `server/tests/test_app.py`

**Interfaces:**
- Consumes: `Catalog.spells` (Phase 2c, already loaded — 319 SRD spells indexed by `index`).
- Produces: `GET /api/spells?class=<id>&level=<0-9>&q=<substring>` → `{"spells": [{"id","name","level","school","castingTime","range","components","duration","concentration","ritual","desc"}]}`, sorted by name. All three query params are optional; omitting all of them returns every SRD spell (mirrors `/api/items`'s behavior with no `category`/`q`).

- [ ] **Step 1: Add the route**

Find `api_items()` in `server/app.py` (it's the existing precedent for this exact shape) and add a new route directly after it:

```python
@app.route("/api/spells")
def api_spells():
    class_id = request.args.get("class")
    level_param = request.args.get("level")
    query = (request.args.get("q") or "").lower()
    level_filter = None
    if level_param is not None:
        try:
            level_filter = int(level_param)
        except ValueError:
            return jsonify({"error": "'level' must be an integer"}), 400
    results = []
    for spell in _catalog.spells.values():
        if class_id and not any(c["index"] == class_id for c in spell.get("classes", [])):
            continue
        if level_filter is not None and spell["level"] != level_filter:
            continue
        if query and query not in spell["name"].lower():
            continue
        results.append({
            "id": spell["index"],
            "name": spell["name"],
            "level": spell["level"],
            "school": spell.get("school", {}).get("name"),
            "castingTime": spell.get("casting_time"),
            "range": spell.get("range"),
            "components": spell.get("components", []),
            "duration": spell.get("duration"),
            "concentration": spell.get("concentration", False),
            "ritual": spell.get("ritual", False),
            "desc": " ".join(spell.get("desc", [])),
        })
    results.sort(key=lambda s: s["name"])
    return jsonify({"spells": results})
```

- [ ] **Step 2: Write tests**

Open `server/tests/test_app.py` first and find the existing tests for `/api/items` — match their exact style (fixture/client setup, assertion shape) rather than inventing a different convention. Add cases covering:
- No query params returns all 319 spells.
- `?class=wizard` filters to only spells whose `classes` list contains `{"index": "wizard", ...}` — assert a known wizard spell (e.g. `fireball`) is present and a spell wizards can't cast (find one empirically, e.g. `cure-wounds` is cleric/druid/paladin/ranger/bard but not wizard) is absent.
- `?class=wizard&level=0` filters to only wizard cantrips — assert every returned spell has `level == 0`.
- `?q=fire` filters by case-insensitive substring match on name — assert `Fire Bolt` and `Fireball` both appear, and a non-matching spell doesn't.
- `?level=notanumber` returns a 400 with an `error` key.
- A single returned spell's full shape matches the expected keys (`id`, `name`, `level`, `school`, `castingTime`, `range`, `components`, `duration`, `concentration`, `ritual`, `desc`) — pick a real spell (e.g. `fireball`) and assert concrete values for at least `school` ("Evocation"), `level` (3), and that `components` is a list containing `"V"`.

- [ ] **Step 3: Run tests**

Run: `cd server && .venv/bin/python -m pytest tests/test_app.py -v`
Expected: PASS, including all new cases.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all 119 existing plus your new tests, all green.

- [ ] **Step 4: Commit**

```bash
git add server/app.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: add GET /api/spells for browsing the SRD spell catalog

Mirrors GET /api/items exactly: filter by class/level/search query,
sorted by name. Exposes full spell detail (school, casting time, range,
components, duration, concentration/ritual, description) that Phase 2c's
spell Choices can't show — ChoicePicker only ever renders a bare label.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `useSpells` hook

**Files:**
- Create: `frontend/src/useSpells.ts`

**Interfaces:**
- Consumes: `GET /api/spells` (Task 1).
- Produces: `useSpells(classId: string, level: string, query: string): { spells: CatalogSpell[], loading: boolean, error: string | null, retry: () => void }`. An empty `classId` means "don't fetch" (see Global Constraints) — `spells` stays `[]`, `loading` stays `false`, no request is sent.

- [ ] **Step 1: Create `frontend/src/useSpells.ts`**

Read `frontend/src/useItems.ts` first (Phase 2b) — this is a near-exact mirror of it, with one behavioral addition (skip fetching on an empty `classId`) that `useItems` doesn't need (an empty *category* is a legitimate "browse everything" query there; an empty *class* here is not — see Global Constraints).

```ts
import { useCallback, useEffect, useRef, useState } from "react";

export interface CatalogSpell {
  id: string;
  name: string;
  level: number;
  school: string | null;
  castingTime: string | null;
  range: string | null;
  components: string[];
  duration: string | null;
  concentration: boolean;
  ritual: boolean;
  desc: string;
}

interface SpellsState {
  spells: CatalogSpell[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 150;

export function useSpells(classId: string, level: string, query: string): SpellsState & { retry: () => void } {
  const [state, setState] = useState<SpellsState>({ spells: [], loading: false, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!classId) {
      setState({ spells: [], loading: false, error: null });
      return;
    }
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      const params = new URLSearchParams();
      params.set("class", classId);
      if (level) params.set("level", level);
      if (query) params.set("q", query);
      fetch(`/api/spells?${params.toString()}`)
        .then((resp) => {
          if (!resp.ok) throw new Error(`spells fetch failed: ${resp.status}`);
          return resp.json() as Promise<{ spells: CatalogSpell[] }>;
        })
        .then((data) => {
          if (id !== requestId.current) return;
          setState({ spells: data.spells, loading: false, error: null });
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
  }, [classId, level, query, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors (this file has no consumer yet, but must still typecheck standalone).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/useSpells.ts
git commit -m "$(cat <<'EOF'
feat: add useSpells hook for GET /api/spells

Mirrors useItems.ts's debounce/stale-response-guard pattern exactly, with
one addition: an empty classId means "don't fetch" rather than "fetch
everything" — the spell library is always scoped to a selected class, so
there is no legitimate empty-class query the way an empty item category
(browse everything) is legitimate for useItems.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: ClassPage tab split + spell library

**Files:**
- Modify: `frontend/src/pages/ClassPage.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `useDraft()`, `useResolutionContext()`, `useCatalog()` (all unchanged, Phase 1b), `useSpells()` (Task 2), `<ChoiceCard>` (Phase 0, unchanged).

- [ ] **Step 1: Rewrite `frontend/src/pages/ClassPage.tsx`**

The existing file renders the class-radio-list, then a flat list of every `source.kind === "class"` choice. This rewrite keeps the radio list identical, splits the choice list into two tabs, and adds the spell library under the `SPELLS` tab.

**A note on hook ordering, since this is easy to get wrong**: `useSpells()` must be called unconditionally, on every render, in the same position — React's rules of hooks forbid calling it after an early `return` (the existing file has one, for the `error` case). The rewrite below computes `hasSpells`/`selectedClassId` and calls `useSpells()` *before* that early return, passing an empty string as `classId` when there's nothing to fetch (Task 2's hook already treats that as "don't fetch").

**A second note on tab/data desync**: if the user has the `SPELLS` tab active and then switches to a class with no spellcasting, `hasSpells` becomes `false` but React state `tab` doesn't automatically reset — naively guarding the spells panel on `tab === "spells" && hasSpells` would then render *neither* tab's content (blank page) until the user manually clicks back to `Способности`. The rewrite below avoids this with a derived `effectiveTab` (`hasSpells ? tab : "features"`) used for all render decisions, so losing spell access self-heals to the features tab immediately rather than needing a `useEffect`.

```tsx
import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { useSpells } from "../useSpells";
import { ChoiceCard } from "../components/ChoiceCard";

type ClassTab = "features" | "spells";

function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known");
}

const SPELL_LEVELS = [
  { value: "", label: "Всички нива" },
  { value: "0", label: "Трикове" },
  { value: "1", label: "1-во ниво" },
];

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();
  const [tab, setTab] = useState<ClassTab>("features");
  const [spellLevel, setSpellLevel] = useState("");
  const [spellQuery, setSpellQuery] = useState("");

  const selectedClassId = draft.classes[0]?.classId;
  const classChoices = resolution ? resolution.choices.filter((c) => c.source.kind === "class") : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";
  const spells = useSpells(hasSpells ? (selectedClassId ?? "") : "", spellLevel, spellQuery);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

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

      {selectedClassId && (
        <div className="tab-bar" role="tablist">
          <button type="button" role="tab" aria-selected={effectiveTab === "features"} onClick={() => setTab("features")}>
            Способности
          </button>
          {hasSpells && (
            <button type="button" role="tab" aria-selected={effectiveTab === "spells"} onClick={() => setTab("spells")}>
              Заклинания
            </button>
          )}
        </div>
      )}

      {selectedClassId && effectiveTab === "features" && (
        <>
          {!loading && featureChoices.length === 0 && <p>Няма избори за този клас.</p>}
          {featureChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
        </>
      )}

      {selectedClassId && effectiveTab === "spells" && (
        <>
          {spellChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}

          <h2>Списък със заклинания</h2>
          <input
            type="text"
            placeholder="Търсене…"
            value={spellQuery}
            onChange={(e) => setSpellQuery(e.target.value)}
          />
          <select value={spellLevel} onChange={(e) => setSpellLevel(e.target.value)}>
            {SPELL_LEVELS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
          {spells.error && (
            <p>
              Грешка: {spells.error}{" "}
              <button type="button" onClick={spells.retry}>
                Опитай пак
              </button>
            </p>
          )}
          <ul className="spell-library-list">
            {spells.spells.map((spell) => (
              <li key={spell.id} className="spell-library-card">
                <div className="spell-library-card__header">
                  <span className="spell-library-card__name">{spell.name}</span>
                  <span className="spell-library-card__level">{spell.level === 0 ? "Трик" : `${spell.level} ниво`}</span>
                </div>
                <div className="spell-library-card__meta">
                  {spell.school && <span>{spell.school}</span>}
                  {spell.castingTime && <span>{spell.castingTime}</span>}
                  {spell.range && <span>{spell.range}</span>}
                  {spell.components.length > 0 && <span>{spell.components.join(", ")}</span>}
                  {spell.duration && <span>{spell.duration}</span>}
                  {spell.concentration && <span>Концентрация</span>}
                  {spell.ritual && <span>Ритуал</span>}
                </div>
                <p className="spell-library-card__desc">{spell.desc}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add tab-bar and spell-library CSS to `frontend/src/index.css`**

Add at the end of the file:

```css
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  border-bottom: 1px solid #ccc;
}

.tab-bar button {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-bottom: none;
  background: #f5f5f5;
  cursor: pointer;
}

.tab-bar button[aria-selected="true"] {
  background: #fff;
  font-weight: bold;
}

.spell-library-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #ccc;
}

.spell-library-card {
  padding: 8px;
  border-bottom: 1px solid #eee;
}

.spell-library-card:last-child {
  border-bottom: none;
}

.spell-library-card__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-weight: bold;
}

.spell-library-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 0.85em;
  color: #555;
  margin: 4px 0;
}

.spell-library-card__desc {
  margin: 4px 0 0;
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Manual verification**

```bash
cd server && .venv/bin/python app.py &
sleep 1
cd ../frontend && npm run dev &
sleep 2
```

On `/class`, select **Fighter**. Confirm: no `Заклинания` tab button appears (Fighter has zero spell choices); the `Способности` tab shows Fighter's usual 2 choices exactly as before this phase (byte-for-byte same content, just now under a tab). Switch to **Wizard**. Confirm: a `Заклинания` tab button now appears; clicking it shows Wizard's 2 spell `ChoiceCard`s (Cantrips Known, Prepared Spells) followed by the spell library; the library initially lists all Wizard spells across both levels sorted by name; selecting level filter "Трикове" narrows it to only Wizard cantrips; typing "fire" in the search box narrows it further (e.g. to Fire Bolt if it's a Wizard cantrip); each listed spell shows school/casting time/range/components/duration and its description text, not just a bare name. Pick a cantrip and a 1st-level spell via the `ChoicePicker` checkboxes (not the library) — confirm the choice cards become resolved and, after the debounce, the choice reflects the pick. Switch back to `Способности` — confirm Wizard's class-feature choices (if any) still render there, unaffected. Switch to **Paladin** — confirm no `Заклинания` tab appears (zero spell slots at level 1, per Phase 2c) even though Paladin has real `spellcasting` data in the SRD. Reload the page — confirm the draft (including the picked cantrip/spell) survived via localStorage and the correct tab set re-renders once resolution reloads.

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ClassPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: split ClassPage into Class Features / Spells tabs, add spell library

Spell choices (cantrips/known-or-prepared spells) move out of the flat
class-choice list into their own SPELLS tab, shown only for the 6 SRD
classes that actually cast at level 1. The tab now also surfaces a
searchable spell-reference library (school, casting time, range,
components, duration, description) backed by GET /api/spells, since
ChoicePicker's bare-label checkboxes give no way to see what a spell
actually does before picking it. ChoiceCard/ChoicePicker are unchanged —
selection still happens through them exactly as before.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- Task 3's `effectiveTab` derivation exists specifically to avoid a blank-page state when switching from a caster to a non-caster class mid-session with the Spells tab active. Don't simplify it back to reading `tab` directly without re-checking that class-switch scenario live — it's exactly the kind of state-desync bug this project's history (Phase 2b's `SET_CLASS`-doesn't-clear-`equipment.choices` finding) has caught before in a final review, and it's cheaper to get right here than to catch later.
- This plan deliberately does not touch `frontend/src/DraftContext.tsx` or `frontend/src/types.ts` at all — every prior frontend phase in this project modified the `Draft` shape or reducer; this one doesn't need to, because spell selections already flow through the existing generic `SET_CHOICE_SELECTION`/`class` path with no new state to track. If an implementer feels tempted to add Draft fields for the spell library's local UI state (search query, level filter), that's a bug in the temptation, not a gap in the plan — that state is page-local `useState`, not draft state, exactly like the equipment page's `category`/`query` filters in Phase 2b.
