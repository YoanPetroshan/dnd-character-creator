# Builder v2 Phase 0 — Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the full skeleton of the v2 builder — a Vite/React/TypeScript
frontend with seven routed steps, a `DraftProvider`, a debounced
`POST /api/resolve` call against a new stub Flask backend, and a working
`<ChoiceCard>`/`<ChoicePicker>` pair rendering real (stub) choice data on the
Class step. Nothing here implements real D&D rules — the goal is that every
wire is connected and provably working, so Phase 1 only has to replace the
stub data with a real engine.

**Architecture:** New, separate `server/` (Python/Flask) and `frontend/`
(Vite/React/TS) directories at the repo root, alongside the existing v1 code
(`app.py`, `chargen/`, `templates/`, etc.), which stays untouched and keeps
working. `server/app.py` exposes `/api/resolve` returning a hardcoded
Resolution object matching the exact shape the design spec defines.
`frontend/` is a Vite dev server (port 5173) proxying `/api/*` to the Flask
server (port 8000).

**Tech Stack:** Python 3, Flask, flask-cors, pytest (backend). Node.js
v26 / npm v11, React 19.3.0, react-router-dom 7.18.4, TypeScript 7.0.2,
Vite 8.3.0, @vitejs/plugin-react 6.1.1 (frontend). All dependency versions
below are exact, verified-`latest`, pinned versions — not ranges.

## Global Constraints

- **Do not modify anything under `chargen/`, `app.py`, `storage.py`,
  `sheet_derive.py`, `markdown_render.py`, `pdf_fill.py`, or `templates/`** —
  the v1 app must keep working unmodified throughout this plan. This plan
  only adds new files under `server/` and `frontend/`.
- **The engine does not exist yet.** `/api/resolve` returns a hardcoded
  Resolution regardless of the request body. Do not attempt to implement any
  D&D rule, any catalog lookup, or any real choice-resolution logic in this
  plan — that is Phase 1 and later. Any task that finds itself writing rules
  logic has gone out of scope; stop and flag it instead.
- **Type shapes matter more than behavior in this phase.** The `Choice`,
  `Resolution`, `Draft` TypeScript interfaces defined in Task 3 are the
  interfaces every later phase builds on — copy them exactly as given, do not
  simplify or rename fields.
- **Every dependency version is pinned exactly** (e.g. `"react": "19.3.0"`,
  never `"^19.3.0"` or `"latest"`) — this was a deliberate choice verified
  against npm's `latest` dist-tag while writing this plan; keep it that way.
- **No design/CSS work in this phase.** The user is sourcing a visual design
  separately. Write only minimal, functional styling (enough to see
  structure — borders, spacing) via one small `index.css` in Task 2; no task
  in this plan should spend effort on visual polish.

---

### Task 1: Backend stub — `server/app.py`

**Files:**
- Create: `server/app.py`
- Create: `server/requirements.txt`
- Create: `server/tests/conftest.py`
- Create: `server/tests/test_resolve_stub.py`
- Create: `server/pytest.ini`
- Modify: `.gitignore` (repo root — add Python/venv/node ignores for the new dirs)

**Interfaces:**
- Produces: `POST /api/resolve` (accepts any JSON body, ignores it, returns
  a hardcoded Resolution JSON object — exact shape below) and
  `GET /api/health` (returns `{"ok": true}`) — every later task's frontend
  code calls `POST /api/resolve` expecting exactly this response shape.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_resolve_stub.py
import pytest

from app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_resolve_returns_stub_shape(client):
    resp = client.post("/api/resolve", json={"name": "Test"})
    assert resp.status_code == 200
    body = resp.get_json()
    for key in ("sheet", "choices", "derived", "problems", "warnings", "pruned"):
        assert key in body, f"missing top-level key: {key}"
    assert isinstance(body["choices"], list)
    assert len(body["choices"]) == 4
    first = body["choices"][0]
    for key in ("id", "source", "label", "description", "count", "options", "selected", "status"):
        assert key in first, f"missing Choice key: {key}"
    assert first["source"]["kind"] == "class"
    assert first["source"]["id"] == "fighter"


def test_resolve_choices_cover_every_source_kind_used_in_phase_0(client):
    resp = client.post("/api/resolve", json={})
    kinds = {c["source"]["kind"] for c in resp.get_json()["choices"]}
    assert kinds == {"class", "background", "species"}


def test_resolve_includes_one_pending_one_resolved_choice(client):
    resp = client.post("/api/resolve", json={})
    statuses = {c["status"] for c in resp.get_json()["choices"]}
    assert "pending" in statuses
    assert "resolved" in statuses


def test_resolve_accepts_empty_body(client):
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 200


def test_resolve_includes_a_disabled_option_with_a_reason(client):
    resp = client.post("/api/resolve", json={})
    body = resp.get_json()
    disabled = [
        opt
        for choice in body["choices"]
        for opt in choice["options"]
        if opt.get("disabled")
    ]
    assert len(disabled) == 1
    assert disabled[0]["disabledReason"]
```

- [ ] **Step 2: Write `server/tests/conftest.py`** (so `from app import app`
  resolves regardless of the directory pytest is invoked from)

```python
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
```

- [ ] **Step 3: Write `server/pytest.ini`**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 4: Write `server/requirements.txt`**

```
flask
flask-cors
pytest
```

- [ ] **Step 5: Set up the venv**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 7: Write `server/app.py`**

```python
"""Phase 0 stub backend for the v2 character builder.

Serves exactly one real endpoint, /api/resolve, which currently returns a
hardcoded Resolution regardless of the request body — no rules engine
exists yet. Phase 1 replaces the hardcoded body with a real
resolve(draft, catalog) call; the route and the response shape stay
exactly the same, which is the whole point of nailing the shape now.

This file imports nothing from v1 (chargen/, app.py at the repo root,
etc.) — v2 is a from-scratch rewrite of everything except the bundled SRD
JSON data, and that data isn't even read yet in Phase 0.
"""
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})


def _stub_resolution() -> dict:
    """A hand-written Resolution covering every Choice shape Phase 0's
    frontend needs to prove out: a pending single-choice (Fighting Style),
    a resolved multi-choice (skill proficiencies, already picked), a
    pending multi-choice from a different source kind (background
    languages), and a choice with one disabled option carrying a reason
    (Draconic Ancestry — Gold disabled, simulating a 2024-only option not
    available from the currently enabled sources).
    """
    return {
        "sheet": {"name": "", "level": 0},
        "choices": [
            {
                "id": "class:fighter:1:fighting-style",
                "source": {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1},
                "label": "Fighting Style",
                "description": "You adopt a particular style of fighting as your specialty.",
                "count": 1,
                "options": [
                    {"id": "archery", "label": "Archery"},
                    {"id": "defense", "label": "Defense"},
                    {"id": "dueling", "label": "Dueling"},
                    {"id": "great-weapon-fighting", "label": "Great Weapon Fighting"},
                ],
                "selected": [],
                "status": "pending",
            },
            {
                "id": "class:fighter:1:prof-skills",
                "source": {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1},
                "label": "Skill Proficiencies",
                "description": "Choose two skills from the Fighter list.",
                "count": 2,
                "options": [
                    {"id": "acrobatics", "label": "Acrobatics"},
                    {"id": "athletics", "label": "Athletics"},
                    {"id": "intimidation", "label": "Intimidation"},
                    {"id": "perception", "label": "Perception"},
                ],
                "selected": ["athletics", "perception"],
                "status": "resolved",
            },
            {
                "id": "background:acolyte:languages",
                "source": {"kind": "background", "id": "acolyte", "label": "Acolyte"},
                "label": "Languages",
                "description": "Choose two languages of your choice.",
                "count": 2,
                "options": [
                    {"id": "celestial", "label": "Celestial"},
                    {"id": "draconic", "label": "Draconic"},
                    {"id": "dwarvish", "label": "Dwarvish"},
                ],
                "selected": [],
                "status": "pending",
            },
            {
                "id": "species:dragonborn:ancestry",
                "source": {"kind": "species", "id": "dragonborn", "label": "Dragonborn"},
                "label": "Draconic Ancestry",
                "description": "Choose the type of dragon you're descended from.",
                "count": 1,
                "options": [
                    {"id": "black", "label": "Black (Acid)"},
                    {"id": "blue", "label": "Blue (Lightning)"},
                    {
                        "id": "gold",
                        "label": "Gold (Fire)",
                        "disabled": True,
                        "disabledReason": "requires the 2024 species pack",
                    },
                ],
                "selected": [],
                "status": "pending",
            },
        ],
        "derived": {"ac": 10, "hp": 0, "profBonus": 2},
        "problems": [],
        "warnings": [
            {"id": "stub-warning", "message": "This is Phase 0 stub data — no rules engine runs yet."}
        ],
        "pruned": [],
    }


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/resolve", methods=["POST"])
def resolve():
    _draft = request.get_json(silent=True) or {}  # ignored in Phase 0
    return jsonify(_stub_resolution())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all 6 PASS

- [ ] **Step 9: Start the server and smoke-test it manually**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server
.venv/bin/python3 app.py &
sleep 1
curl -s http://127.0.0.1:8000/api/health
curl -s -X POST http://127.0.0.1:8000/api/resolve -H "Content-Type: application/json" -d '{}' | head -c 300
kill %1
```

Expected: `{"ok":true}` then the start of the stub JSON.

- [ ] **Step 10: Update the repo-root `.gitignore`**

Add (if not already present):
```
server/.venv/
server/__pycache__/
server/**/__pycache__/
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 11: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/app.py server/requirements.txt server/tests/conftest.py \
        server/tests/test_resolve_stub.py server/pytest.ini .gitignore
git commit -m "feat: add v2 stub backend with /api/resolve

New server/ directory, fully independent from v1 (app.py, chargen/) —
returns a hardcoded Resolution covering every Choice shape (pending
single-choice, resolved multi-choice, disabled option with a reason)
Phase 0's frontend needs to prove the pipeline end to end.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend scaffold — Vite + React + TypeScript + Router

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Interfaces:**
- Consumes: nothing from Task 1 yet (this task only proves routing renders;
  the proxy config points at Task 1's server but nothing calls it yet)
- Produces: a working `npm run dev` at `http://localhost:5173` with 7 routed
  pages; `App` component (default export from `./App`) that Task 3 wraps
  with `DraftProvider`

- [ ] **Step 1: Write `frontend/package.json`**

```json
{
  "name": "dnd-builder-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "19.3.0",
    "react-dom": "19.3.0",
    "react-router-dom": "7.18.4"
  },
  "devDependencies": {
    "@types/react": "19.3.0",
    "@types/react-dom": "19.3.0",
    "@vitejs/plugin-react": "6.1.1",
    "typescript": "7.0.2",
    "vite": "8.3.0"
  }
}
```

- [ ] **Step 2: Write `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 3: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Write `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="bg">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Character Builder</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write `frontend/src/index.css`** (minimal — structure only,
  no visual design; the user is sourcing a design separately)

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, sans-serif;
  color: #222;
  background: #fafafa;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.step-nav {
  display: flex;
  gap: 4px;
  padding: 8px;
  background: #eee;
  border-bottom: 1px solid #ccc;
}

.step-nav a {
  padding: 8px 12px;
  text-decoration: none;
  color: #333;
  border-radius: 4px;
  position: relative;
}

.step-nav a.active {
  background: #333;
  color: #fff;
}

.step-nav__badge {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 10px;
  background: #c0392b;
  color: #fff;
  font-size: 11px;
}

main {
  flex: 1;
  padding: 16px;
}

.page {
  max-width: 800px;
}

.choice-card {
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-bottom: 8px;
  background: #fff;
}

.choice-card__header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
}

.choice-card[data-status="pending"] .choice-card__header {
  border-left: 3px solid #2980b9;
}

.choice-card__pending-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2980b9;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
}

.choice-card__label {
  font-weight: 600;
  flex: 1;
}

.choice-card__level,
.choice-card__count {
  font-size: 12px;
  color: #666;
}

.choice-card__body {
  padding: 0 12px 12px;
}

.choice-picker {
  list-style: none;
  margin: 0;
  padding: 0;
}

.choice-picker li {
  padding: 2px 0;
}

.choice-picker__option--disabled {
  color: #999;
}

.choice-picker__reason {
  font-style: italic;
  font-size: 12px;
}
```

- [ ] **Step 7: Write `frontend/src/App.tsx`** (placeholder routing — Task 6
  replaces the placeholder pages with real ones)

```tsx
import { Routes, Route, Navigate } from "react-router-dom";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<StepPlaceholder name="Home" />} />
          <Route path="/class" element={<StepPlaceholder name="Class" />} />
          <Route path="/background" element={<StepPlaceholder name="Background" />} />
          <Route path="/species" element={<StepPlaceholder name="Species" />} />
          <Route path="/abilities" element={<StepPlaceholder name="Abilities" />} />
          <Route path="/equipment" element={<StepPlaceholder name="Equipment" />} />
          <Route path="/export" element={<StepPlaceholder name="Export" />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 8: Write `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("#root element not found");

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Step 9: Install dependencies**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend
npm install
```

- [ ] **Step 10: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 11: Start the dev server and verify routing**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend
npm run dev &
sleep 2
curl -s http://localhost:5173/ | grep -o '<title>[^<]*</title>'
kill %1
```

Expected: `<title>Character Builder</title>` (confirms the dev server serves
`index.html`; full route rendering is a client-side SPA behavior verified
visually in Task 6's final check, not via curl).

- [ ] **Step 12: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig.json \
        frontend/tsconfig.node.json frontend/index.html frontend/src/main.tsx \
        frontend/src/App.tsx frontend/src/index.css
git commit -m "feat: scaffold the v2 frontend (Vite + React 19 + Router 7 + TS)

Seven placeholder routes, proxying /api to the Task 1 stub backend.
All dependency versions pinned exactly (verified against npm's latest
dist-tag while planning this task) rather than left as ranges.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

  Note: `frontend/package-lock.json` will also be created by `npm install`
  in Step 9 — include it in this commit too (`git add frontend/package-lock.json`)
  so installs are reproducible.

---

### Task 3: Types + DraftProvider

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/DraftContext.tsx`
- Modify: `frontend/src/main.tsx` (wrap `App` with `DraftProvider`)
- Modify: `frontend/src/App.tsx` (Home placeholder becomes a real, minimal
  page reading/writing `draft.name` via `useDraft()`, to prove the context
  works end to end)

**Interfaces:**
- Produces: every type in `types.ts` (`Ability`, `Choice`, `ChoiceOption`,
  `ChoiceSource`, `ChoiceSourceKind`, `ChoiceStatus`, `Problem`,
  `WarningItem`, `Pruned`, `Resolution`, `Draft`, `ClassSelection`,
  `Preferences`) — every later task imports from this file, exact field
  names, no renaming. `useDraft()` hook and `DraftProvider` component from
  `DraftContext.tsx` — Task 4 and later consume `useDraft()`.

- [ ] **Step 1: Write `frontend/src/types.ts`**

```ts
export type Ability = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA";

export interface ChoiceOption {
  id: string;
  label: string;
  description?: string;
  disabled?: boolean;
  disabledReason?: string;
}

export type ChoiceSourceKind =
  | "class"
  | "subclass"
  | "background"
  | "species"
  | "feature"
  | "equipment";

export interface ChoiceSource {
  kind: ChoiceSourceKind;
  id: string;
  label: string;
  level?: number;
}

export type ChoiceStatus = "pending" | "resolved" | "invalid";

export interface Choice {
  id: string;
  source: ChoiceSource;
  label: string;
  description: string;
  count: number;
  options: ChoiceOption[];
  selected: string[];
  status: ChoiceStatus;
}

export interface Problem {
  id: string;
  message: string;
}

export interface WarningItem {
  id: string;
  message: string;
}

export interface Pruned {
  choiceId: string;
  reason: string;
}

export interface Resolution {
  sheet: Record<string, unknown>;
  choices: Choice[];
  derived: Record<string, unknown>;
  problems: Problem[];
  warnings: WarningItem[];
  pruned: Pruned[];
}

export interface ClassSelection {
  classId: string;
  level: number;
  subclassId?: string;
  choices: Record<string, string[]>;
}

export interface Preferences {
  advancementType: "milestone" | "xp";
  hitPointType: "fixed" | "manual";
  usePrerequisites: { feats: boolean; multiclass: boolean };
}

export interface Draft {
  name: string;
  sources: string[];
  preferences: Preferences;
  classes: ClassSelection[];
  background: { id?: string; choices: Record<string, string[]> };
  species: { id?: string; subspeciesId?: string; choices: Record<string, string[]> };
  abilities: {
    method: "standard" | "roll" | "pointbuy" | "manual";
    base: Record<Ability, number>;
  };
  equipment: {
    startingChoice?: string;
    added: { itemId: string; qty: number; equipped: boolean }[];
    skipped: boolean;
  };
  details: {
    alignment?: string;
    faith?: string;
    lifestyle?: string;
    backstory?: string;
  };
}
```

- [ ] **Step 2: Write `frontend/src/DraftContext.tsx`**

```tsx
import { createContext, useContext, useReducer, useEffect, type Dispatch, type ReactNode } from "react";
import type { Draft } from "./types";

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
  | { type: "RESET" };

function reducer(state: Draft, action: Action): Draft {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_DRAFT":
      return action.draft;
    case "RESET":
      return emptyDraft;
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

- [ ] **Step 3: Update `frontend/src/main.tsx`** to wrap `App` with
  `DraftProvider`

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { DraftProvider } from "./DraftContext";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("#root element not found");

createRoot(rootElement).render(
  <StrictMode>
    <BrowserRouter>
      <DraftProvider>
        <App />
      </DraftProvider>
    </BrowserRouter>
  </StrictMode>,
);
```

- [ ] **Step 4: Update `frontend/src/App.tsx`** — replace the `/home` route's
  placeholder with a real minimal page proving `useDraft()` round-trips
  through localStorage. Leave the other six routes as `StepPlaceholder` for
  now (Task 6 replaces them).

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import { useDraft } from "./DraftContext";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

function HomePlaceholder() {
  const { draft, dispatch } = useDraft();
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<HomePlaceholder />} />
          <Route path="/class" element={<StepPlaceholder name="Class" />} />
          <Route path="/background" element={<StepPlaceholder name="Background" />} />
          <Route path="/species" element={<StepPlaceholder name="Species" />} />
          <Route path="/abilities" element={<StepPlaceholder name="Abilities" />} />
          <Route path="/equipment" element={<StepPlaceholder name="Equipment" />} />
          <Route path="/export" element={<StepPlaceholder name="Export" />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 6: Manual verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend
npm run dev &
sleep 2
```

Open `http://localhost:5173/home` in a browser, type a name into the
Character Name field, reload the page, and confirm the name is still there
(proves the reducer + localStorage round-trip). Then:

```bash
kill %1
```

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/types.ts frontend/src/DraftContext.tsx \
        frontend/src/main.tsx frontend/src/App.tsx
git commit -m "feat: add v2 Draft types and DraftProvider (context + localStorage)

Types copied exactly from the architecture spec's central abstraction —
every later phase builds on these without renaming fields.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `useResolution` hook + `ResolutionProvider`

**Files:**
- Create: `frontend/src/useResolution.ts`
- Create: `frontend/src/ResolutionContext.tsx`
- Modify: `frontend/src/App.tsx` (wrap routes with `ResolutionProvider`;
  Home page shows `resolution.warnings` to prove the round trip)

**Interfaces:**
- Consumes: `useDraft()` from Task 3, `Draft`/`Resolution` types from Task 3
- Produces: `useResolutionContext()` hook returning
  `{ resolution: Resolution | null, loading: boolean, error: string | null }`
  — Task 5's `ClassPage` and Task 6's `StepNav` both consume this.

- [ ] **Step 1: Write `frontend/src/useResolution.ts`**

```ts
import { useEffect, useRef, useState } from "react";
import type { Draft, Resolution } from "./types";

const DEBOUNCE_MS = 150;

interface ResolutionState {
  resolution: Resolution | null;
  loading: boolean;
  error: string | null;
}

export function useResolution(draft: Draft): ResolutionState {
  const [state, setState] = useState<ResolutionState>({
    resolution: null,
    loading: false,
    error: null,
  });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      fetch("/api/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      })
        .then((resp) => {
          if (!resp.ok) throw new Error(`resolve failed: ${resp.status}`);
          return resp.json() as Promise<Resolution>;
        })
        .then((resolution) => {
          if (id !== requestId.current) return; // a newer request already won
          setState({ resolution, loading: false, error: null });
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
  }, [draft]);

  return state;
}
```

- [ ] **Step 2: Write `frontend/src/ResolutionContext.tsx`**

```tsx
import { createContext, useContext, type ReactNode } from "react";
import { useDraft } from "./DraftContext";
import { useResolution } from "./useResolution";
import type { Resolution } from "./types";

interface ResolutionContextValue {
  resolution: Resolution | null;
  loading: boolean;
  error: string | null;
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

- [ ] **Step 3: Update `frontend/src/App.tsx`** — wrap the routed content
  with `ResolutionProvider`, and have `HomePlaceholder` display
  `resolution.warnings` (proves data actually reaches the browser from the
  Task 1 stub backend, not just that the fetch resolves)

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import { useDraft } from "./DraftContext";
import { ResolutionProvider, useResolutionContext } from "./ResolutionContext";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

function HomePlaceholder() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>
      <h2>Resolution (from /api/resolve)</h2>
      {loading && <p>Зареждане…</p>}
      {error && <p style={{ color: "red" }}>Грешка: {error}</p>}
      {resolution && (
        <ul>
          {resolution.warnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <ResolutionProvider>
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/home" element={<HomePlaceholder />} />
            <Route path="/class" element={<StepPlaceholder name="Class" />} />
            <Route path="/background" element={<StepPlaceholder name="Background" />} />
            <Route path="/species" element={<StepPlaceholder name="Species" />} />
            <Route path="/abilities" element={<StepPlaceholder name="Abilities" />} />
            <Route path="/equipment" element={<StepPlaceholder name="Equipment" />} />
            <Route path="/export" element={<StepPlaceholder name="Export" />} />
          </Routes>
        </main>
      </ResolutionProvider>
    </div>
  );
}
```

  Note: `ResolutionProvider` calls `useDraft()` internally, so it must be
  rendered *inside* `DraftProvider` (already true — `main.tsx` wraps `App`
  with `DraftProvider`, and `App` renders `ResolutionProvider` as a child of
  that).

- [ ] **Step 4: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 5: Manual end-to-end verification**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python3 app.py &
sleep 1
cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run dev &
sleep 2
```

Open `http://localhost:5173/home`. Confirm the "Resolution" section shows
the warning text *"This is Phase 0 stub data — no rules engine runs
yet."* — this proves the full chain: React state change → debounced
fetch → Vite proxy → Flask → JSON → React render.

```bash
kill %1 %2
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/useResolution.ts frontend/src/ResolutionContext.tsx frontend/src/App.tsx
git commit -m "feat: add useResolution hook + ResolutionProvider

Debounced (150ms) POST /api/resolve, stale-response guard via a request
id ref. Home page renders the stub backend's warning text end to end —
proves the full chain works before any real rule is written.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `ChoiceCard` + `ChoicePicker`, wired into a real Class page

**Files:**
- Create: `frontend/src/components/ChoiceCard.tsx`
- Create: `frontend/src/components/ChoicePicker.tsx`
- Create: `frontend/src/pages/ClassPage.tsx`
- Modify: `frontend/src/App.tsx` (use `ClassPage` for `/class` instead of
  the placeholder)

**Interfaces:**
- Consumes: `Choice`/`ChoiceOption` types (Task 3), `useResolutionContext()`
  (Task 4)
- Produces: `<ChoiceCard choice={choice} onChange={fn} />` and
  `<ChoicePicker choice={choice} onChange={fn} />` — Task 6's other step
  pages (Background, Species, Equipment) and every later phase reuse these
  unchanged; this is the single reusable choice-rendering component the
  whole app leans on (see spec §2).

- [ ] **Step 1: Write `frontend/src/components/ChoicePicker.tsx`**

```tsx
import type { Choice } from "../types";

interface ChoicePickerProps {
  choice: Choice;
  onChange: (choiceId: string, selected: string[]) => void;
}

export function ChoicePicker({ choice, onChange }: ChoicePickerProps) {
  function toggle(optionId: string) {
    const isSelected = choice.selected.includes(optionId);
    let next: string[];
    if (isSelected) {
      next = choice.selected.filter((id) => id !== optionId);
    } else if (choice.selected.length >= choice.count) {
      // At capacity for a single-choice (count=1) card: picking a
      // different option replaces the previous one, matching how a
      // radio-style choice behaves. For count>1 this drops the oldest
      // pick — acceptable for Phase 0's read-only-round-trip demo; Phase 1
      // can swap this for an explicit "deselect one first" UX if desired.
      next = [...choice.selected.slice(1), optionId];
    } else {
      next = [...choice.selected, optionId];
    }
    onChange(choice.id, next);
  }

  return (
    <ul className="choice-picker">
      {choice.options.map((option) => (
        <li key={option.id}>
          <label className={option.disabled ? "choice-picker__option--disabled" : ""}>
            <input
              type="checkbox"
              checked={choice.selected.includes(option.id)}
              disabled={option.disabled}
              onChange={() => toggle(option.id)}
            />
            {option.label}
            {option.disabled && option.disabledReason && (
              <span className="choice-picker__reason"> — {option.disabledReason}</span>
            )}
          </label>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/ChoiceCard.tsx`**

```tsx
import { useState } from "react";
import type { Choice } from "../types";
import { ChoicePicker } from "./ChoicePicker";

interface ChoiceCardProps {
  choice: Choice;
  onChange: (choiceId: string, selected: string[]) => void;
}

export function ChoiceCard({ choice, onChange }: ChoiceCardProps) {
  const [expanded, setExpanded] = useState(choice.status === "pending");

  return (
    <div className="choice-card" data-status={choice.status}>
      <button
        type="button"
        className="choice-card__header"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {choice.status === "pending" && (
          <span className="choice-card__pending-dot" aria-label="pending choice">
            !
          </span>
        )}
        <span className="choice-card__label">{choice.label}</span>
        {choice.source.level != null && (
          <span className="choice-card__level">{choice.source.level} level</span>
        )}
        <span className="choice-card__count">
          {choice.count} {choice.count === 1 ? "Choice" : "Choices"}
        </span>
      </button>
      {expanded && (
        <div className="choice-card__body">
          <p>{choice.description}</p>
          <ChoicePicker choice={choice} onChange={onChange} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/pages/ClassPage.tsx`**

```tsx
import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function ClassPage() {
  const { resolution, loading, error } = useResolutionContext();

  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;

  const classChoices = resolution.choices.filter((c) => c.source.kind === "class");

  function handleChange(choiceId: string, selected: string[]) {
    // Phase 0: this is intentionally not wired back into the Draft yet.
    // The stub backend ignores the request body and always returns the
    // same hardcoded choices, so there is nothing for a real selection to
    // affect until Phase 1's engine exists to validate against. Logging
    // here is the deliberate, documented extent of this task's scope —
    // do not add draft-mutation wiring in this task.
    console.log("choice changed", choiceId, selected);
  }

  return (
    <div className="page">
      <h1>Клас {loading && "…"}</h1>
      {classChoices.length === 0 && <p>Няма избори за клас все още.</p>}
      {classChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Update `frontend/src/App.tsx`** — import and use `ClassPage`
  for the `/class` route instead of `StepPlaceholder`

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import { useDraft } from "./DraftContext";
import { ResolutionProvider, useResolutionContext } from "./ResolutionContext";
import { ClassPage } from "./pages/ClassPage";

function StepPlaceholder({ name }: { name: string }) {
  return (
    <div className="page">
      <h1>{name}</h1>
    </div>
  );
}

function HomePlaceholder() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>
      <h2>Resolution (from /api/resolve)</h2>
      {loading && <p>Зареждане…</p>}
      {error && <p style={{ color: "red" }}>Грешка: {error}</p>}
      {resolution && (
        <ul>
          {resolution.warnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function App() {
  return (
    <div className="app">
      <ResolutionProvider>
        <main>
          <Routes>
            <Route path="/" element={<Navigate to="/home" replace />} />
            <Route path="/home" element={<HomePlaceholder />} />
            <Route path="/class" element={<ClassPage />} />
            <Route path="/background" element={<StepPlaceholder name="Background" />} />
            <Route path="/species" element={<StepPlaceholder name="Species" />} />
            <Route path="/abilities" element={<StepPlaceholder name="Abilities" />} />
            <Route path="/equipment" element={<StepPlaceholder name="Equipment" />} />
            <Route path="/export" element={<StepPlaceholder name="Export" />} />
          </Routes>
        </main>
      </ResolutionProvider>
    </div>
  );
}
```

- [ ] **Step 5: Typecheck**

Run: `cd /Users/yoanpetrov/dnd-character-creator/frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 6: Manual verification**

With both servers running (same commands as Task 4 Step 5), open
`http://localhost:5173/class`. Confirm you see two choice cards under
"Клас": **"Fighting Style"** (blue `!` pending dot, "1 Choice", expanded by
default since it's pending, showing 4 checkbox options) and **"Skill
Proficiencies"** (no `!` dot, "2 Choices", collapsed by default since it's
resolved — click its header to expand and confirm Athletics and Perception
show as already checked). Click a Fighting Style checkbox and confirm the
browser console logs `choice changed class:fighter:1:fighting-style [...]`.

```bash
kill %1 %2
```

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/components/ChoiceCard.tsx frontend/src/components/ChoicePicker.tsx \
        frontend/src/pages/ClassPage.tsx frontend/src/App.tsx
git commit -m "feat: add ChoiceCard/ChoicePicker, wire real Class page

The one reusable choice-rendering pair the whole app leans on (spec §2) —
pending vs resolved status, level tag, choice-count badge, disabled
options with reasons. Verified live against the Task 1 stub data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `StepNav` + remaining page stubs + final wiring

**Files:**
- Create: `frontend/src/components/StepNav.tsx`
- Create: `frontend/src/pages/HomePage.tsx` (promoted from `App.tsx`'s
  `HomePlaceholder`)
- Create: `frontend/src/pages/BackgroundPage.tsx`
- Create: `frontend/src/pages/SpeciesPage.tsx`
- Create: `frontend/src/pages/AbilitiesPage.tsx`
- Create: `frontend/src/pages/EquipmentPage.tsx`
- Create: `frontend/src/pages/ExportPage.tsx`
- Modify: `frontend/src/App.tsx` (final version — renders `StepNav`, routes
  to the seven real page components, no more inline placeholders)

**Interfaces:**
- Consumes: `ChoiceCard` (Task 5), `useResolutionContext()` (Task 4),
  `useDraft()` (Task 3), `ChoiceSourceKind` type (Task 3)
- Produces: the complete Phase 0 app shell — this is the last task in the
  plan; nothing later in this plan depends on it, but every later phase
  starts from this `App.tsx`.

- [ ] **Step 1: Write `frontend/src/pages/HomePage.tsx`** (moved out of
  `App.tsx`, unchanged behavior from Task 4)

```tsx
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function HomePage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>
      <h2>Resolution (from /api/resolve)</h2>
      {loading && <p>Зареждане…</p>}
      {error && <p style={{ color: "red" }}>Грешка: {error}</p>}
      {resolution && (
        <ul>
          {resolution.warnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write the four remaining page stubs**, each filtering
  `resolution.choices` by its own source kind and rendering them with
  `ChoiceCard` (mirroring `ClassPage` exactly, so Phase 1 finds identical
  patterns in every step). `AbilitiesPage` has no `source.kind` in Phase 0's
  stub data, so it stays a plain placeholder.

```tsx
// frontend/src/pages/BackgroundPage.tsx
import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function BackgroundPage() {
  const { resolution, loading, error } = useResolutionContext();
  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;
  const choices = resolution.choices.filter((c) => c.source.kind === "background");
  return (
    <div className="page">
      <h1>Background {loading && "…"}</h1>
      {choices.length === 0 && <p>Няма избори за background все още.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={() => {}} />
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/pages/SpeciesPage.tsx
import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function SpeciesPage() {
  const { resolution, loading, error } = useResolutionContext();
  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;
  const choices = resolution.choices.filter((c) => c.source.kind === "species");
  return (
    <div className="page">
      <h1>Species {loading && "…"}</h1>
      {choices.length === 0 && <p>Няма избори за species все още.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={() => {}} />
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/pages/EquipmentPage.tsx
import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function EquipmentPage() {
  const { resolution, loading, error } = useResolutionContext();
  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;
  const choices = resolution.choices.filter((c) => c.source.kind === "equipment");
  return (
    <div className="page">
      <h1>Equipment {loading && "…"}</h1>
      {choices.length === 0 && <p>Няма избори за equipment все още.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={() => {}} />
      ))}
    </div>
  );
}
```

```tsx
// frontend/src/pages/AbilitiesPage.tsx
export function AbilitiesPage() {
  return (
    <div className="page">
      <h1>Abilities</h1>
      <p>Phase 1+ — no ability-score UI yet.</p>
    </div>
  );
}
```

```tsx
// frontend/src/pages/ExportPage.tsx
export function ExportPage() {
  return (
    <div className="page">
      <h1>Export</h1>
      <p>Phase 2+ — no export UI yet.</p>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/StepNav.tsx`**

```tsx
import { NavLink } from "react-router-dom";
import { useResolutionContext } from "../ResolutionContext";
import type { ChoiceSourceKind } from "../types";

interface Step {
  path: string;
  label: string;
  kind: ChoiceSourceKind | null;
}

const STEPS: Step[] = [
  { path: "/home", label: "Home", kind: null },
  { path: "/class", label: "Клас", kind: "class" },
  { path: "/background", label: "Background", kind: "background" },
  { path: "/species", label: "Species", kind: "species" },
  { path: "/abilities", label: "Abilities", kind: null },
  { path: "/equipment", label: "Equipment", kind: "equipment" },
  { path: "/export", label: "Export", kind: null },
];

export function StepNav() {
  const { resolution } = useResolutionContext();

  function pendingCount(kind: ChoiceSourceKind | null): number {
    if (!kind || !resolution) return 0;
    return resolution.choices.filter((c) => c.source.kind === kind && c.status === "pending").length;
  }

  return (
    <nav className="step-nav">
      {STEPS.map((step) => {
        const count = pendingCount(step.kind);
        return (
          <NavLink key={step.path} to={step.path} className={({ isActive }) => (isActive ? "active" : "")}>
            {step.label}
            {count > 0 && <span className="step-nav__badge">{count}</span>}
          </NavLink>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4: Write the final `frontend/src/App.tsx`**

```tsx
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
    </div>
  );
}
```

  Note: `StepNav` is now a sibling of `<main>`, both inside
  `ResolutionProvider` (it calls `useResolutionContext()` for the pending
  badges, so it must be inside the provider — same reasoning as Task 4's
  note about `ResolutionProvider` needing to be inside `DraftProvider`).

- [ ] **Step 5: Typecheck and build**

```bash
cd /Users/yoanpetrov/dnd-character-creator/frontend
npm run typecheck
npm run build
```

Expected: both succeed with no errors. `npm run build` additionally proves
the production bundle compiles, not just the dev server.

- [ ] **Step 6: Run the backend test suite once more** (confirm Task 1's
  work is still intact after five more tasks of frontend changes)

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v
```

Expected: all 6 PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/components/StepNav.tsx frontend/src/pages/*.tsx frontend/src/App.tsx
git commit -m "feat: add StepNav + remaining page stubs — Phase 0 skeleton complete

Every one of the seven steps is now routed and backed by a real (if
mostly empty) page component. StepNav shows a live pending-choice count
per step, sourced from the same Resolution every page reads. This is the
full skeleton the design spec's Phase 0 describes: nothing implements a
D&D rule yet, but every wire — routing, state, debounced resolve,
choice rendering — is connected and provably working.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Leave both dev servers stopped**

Confirm no `app.py` or `vite` processes are left running in the background
(`ps aux | grep -E "app.py|vite"` should show nothing from this session) —
the final live click-through verification (starting both servers fresh and
visiting all seven tabs in a real browser) is done by the controller after
this task, not by you.
