# Phase 3c — Pruning Warnings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate `Resolution.pruned` for the first time (it has existed in the response shape since Phase 0 but always returns `[]`), so a player who leveled down, switched subclass, changed species/background, or removed a class sees WHY a previously-made choice silently stopped applying, instead of wondering in silence.

**Architecture:** Pure detection, no new data structure: `resolve()` already builds `all_selections` (every submitted choice selection across every source) right before the choice-resolution loop, and `choice_templates` (built just before that) is the complete set of choices that actually exist for the CURRENT Draft state. Any key in `all_selections` with a non-empty selection list that isn't among `choice_templates`'s ids is stale. One set comparison, placed right after `all_selections` is fully built. Frontend surfacing mirrors the EXISTING `resolution.warnings` rendering on `HomePage.tsx` exactly (same `<ul>`/`<li>` shape).

**Tech Stack:** Same as every prior phase — Python/Flask backend, React/TypeScript frontend, no new dependencies.

## Global Constraints

- **No Draft mutation.** `pruned` is purely informational output, exactly like `problems`/`warnings`. The stale selection stays in the Draft untouched — a player leveling back up should see their old selection silently resurface (this is the EXISTING, already-relied-upon architecture; this phase only adds visibility on top of it, never changes it).
- **No new hardcoded reason taxonomy.** One generic reason string naming the stale choice id, not a per-cause branching (leveled-down vs. switched-class vs. removed-class, etc.) — matches how `problems`/`warnings` already use a flat `{id/choiceId, message/reason}` shape with no cause classification.
- **No existing test currently asserts on `pruned`** (confirmed via `grep -n '"pruned"' server/tests/test_resolve.py` while writing this plan — zero hits), so this is a purely additive change with no expected fallout to any existing test.

---

### Task 1: Populate `Resolution.pruned` in `resolve()`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `all_selections` (already built), `choice_templates` (already built) — both already exist in `resolve()`, this task adds no new function, just a block of code using them.
- Produces: `pruned: list[{"choiceId": str, "reason": str}]`, replacing the hardcoded `"pruned": []` in the final return dict.

- [ ] **Step 1: Write the failing tests**

Read `server/tests/test_resolve.py`'s existing conventions first (the `catalog` fixture, `_fighter_acolyte_human_draft` helper). Add:

Both scenarios below were empirically confirmed reachable while writing this plan — run directly against the real bundled catalog, not guessed. A THIRD naively-plausible scenario (removing a whole class, or switching background/species) was checked and found NOT to produce genuinely orphaned `all_selections` data: `DraftContext.tsx`'s `REMOVE_CLASS` action deletes the whole class entry (its nested `choices` dict goes with it — nothing left to read as stale), and `SET_BACKGROUND`/`SET_SPECIES`/`SET_CLASS` all reset `choices: {}` on the new entry (confirmed by reading the reducer directly) — so those three actions can never leave a stale selection behind either. Only two reducer actions leave `choices` untouched while changing what's reachable: `SET_CLASS_LEVEL` (a level-gated choice can go out of reach) and `SET_SUBCLASS` (a subclass-gated choice can go out of reach when the subclass is cleared) — both covered below.

```python
def test_leveling_down_prunes_a_now_unreachable_asi_choice(catalog):
    # Fighter's ASI-granting levels include level 4. A level-4 ASI
    # selection, then leveled back down to 3, should be pruned. Confirmed
    # directly against the real catalog while writing this plan: at
    # level 4 the choice class:fighter:4:asi exists in `choices`; at
    # level 3 it doesn't, while the raw selection is still sitting in
    # classes[0]["choices"] (SET_CLASS_LEVEL never touches `choices`).
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {
            "class:fighter:4:asi": ["str-plus-2"],
        }}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []  # not stale yet, level 4 is current

    draft["classes"][0]["level"] = 3  # level back down, selection left in place
    resolution = resolve(draft, catalog)
    pruned_ids = [p["choiceId"] for p in resolution["pruned"]]
    assert "class:fighter:4:asi" in pruned_ids
    pruned_entry = next(p for p in resolution["pruned"] if p["choiceId"] == "class:fighter:4:asi")
    assert "class:fighter:4:asi" in pruned_entry["reason"]


def test_clearing_a_subclass_prunes_its_subclass_gated_feature_choice(catalog):
    # Champion (Fighter's only bundled subclass) grants a SECOND Fighting
    # Style choice at level 10 (class:fighter:10:feature:additional-
    # fighting-style) on top of the base class's level-1 one — confirmed
    # directly against the real catalog while writing this plan. Clearing
    # subclassId (SET_SUBCLASS with undefined, e.g. re-picking "no
    # subclass") leaves the old selection in place but the level-10
    # feature choice stops being generated, since it's subclass-gated;
    # the base level-1 Fighting Style choice (not subclass-specific)
    # correctly stays reachable and unpruned.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 10, "subclassId": "champion", "choices": {
            "class:fighter:1:feature:fighter-fighting-style": ["fighting-style-defense"],
            "class:fighter:10:feature:additional-fighting-style": ["fighting-style-dueling"],
        }}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []

    draft["classes"][0]["subclassId"] = None  # clear the subclass, selections left in place
    resolution = resolve(draft, catalog)
    pruned_ids = [p["choiceId"] for p in resolution["pruned"]]
    assert "class:fighter:10:feature:additional-fighting-style" in pruned_ids
    assert "class:fighter:1:feature:fighter-fighting-style" not in pruned_ids  # base class feature, still reachable
```

- [ ] **Step 2: Confirm the empirical grounding above still holds**

From `server/`, run the exact scenario each test encodes to reconfirm the numbers before implementing (they were already verified once while writing this plan, but re-confirm since Task 1's own implementation hasn't landed yet and this is the last check before writing code):

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()

draft = {
    'classes': [{'classId': 'fighter', 'level': 4, 'choices': {'class:fighter:4:asi': ['str-plus-2']}}],
    'background': {'id': 'acolyte', 'choices': {}}, 'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
print('level 4:', any(c['id']=='class:fighter:4:asi' for c in r['choices']))
draft['classes'][0]['level'] = 3
r = resolve(draft, catalog)
print('level 3:', any(c['id']=='class:fighter:4:asi' for c in r['choices']))

draft2 = {
    'classes': [{'classId': 'fighter', 'level': 10, 'subclassId': 'champion', 'choices': {}}],
    'background': {'id': 'acolyte', 'choices': {}}, 'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft2, catalog)
print('with champion:', [c['id'] for c in r['choices'] if ':feature:' in c['id']])
draft2['classes'][0]['subclassId'] = None
r = resolve(draft2, catalog)
print('subclass cleared:', [c['id'] for c in r['choices'] if ':feature:' in c['id']])
"
```

- [ ] **Step 3: Run to verify the tests fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "prune"`
Expected: FAIL (all `pruned` lists come back empty since the code hasn't changed yet).

- [ ] **Step 4: Implement**

Find, in `server/engine/resolve.py`, right after `all_selections` is fully built (search for `all_selections.update(equipment_choices_raw or {})` — the last of the four `.update()` calls):

```python
    all_selections.update(equipment_choices_raw or {})
```

Add immediately after it:

```python
    # A selection stored in the Draft for a choice id that no longer
    # exists among the CURRENTLY reachable choice_templates (because the
    # player leveled down, switched subclass, removed a class, or changed
    # species/background) is stale — it was never deleted from the Draft
    # (the architecture deliberately never mutates the Draft — see Phase
    # 3a design spec §7), so it just silently stopped being read. This is
    # the first time anything surfaces that to the player instead of
    # leaving it invisible.
    current_template_ids = {tpl["id"] for tpl in choice_templates}
    pruned = [
        {"choiceId": choice_id, "reason": f"'{choice_id}' no longer applies to the current character and was ignored."}
        for choice_id, selected in all_selections.items()
        if selected and choice_id not in current_template_ids
    ]
```

Find the final return dict (search for `"pruned": [],`) and replace:

```python
        "pruned": [],
```

with:

```python
        "pruned": pruned,
```

- [ ] **Step 5: Run to verify the tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "prune"`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all 308 existing plus your new tests, all green, since no existing test asserts on `pruned` (confirmed empirically before writing this plan).

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: populate Resolution.pruned — surface stale-but-inert selections

pruned has existed in the response shape since Phase 0 but always
returned []. The architecture has always made a stale selection SAFE
(a choice template is only generated for what's currently reachable,
so a stale selection just silently stops being read — never deleted,
never corrupts anything, per Phase 3a design spec §7's "no pruning
needed" argument). This phase adds VISIBILITY on top of that existing
safety: one set comparison (all_selections' keys against the current
choice_templates' ids), no new data structure, no Draft mutation.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Render `pruned` on the Home page

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

**Interfaces:**
- Consumes: `resolution.pruned` (already typed as `Pruned[]` in `frontend/src/types.ts`, unchanged by this plan).

- [ ] **Step 1: Read the existing `warnings` rendering**

Read `frontend/src/pages/HomePage.tsx` in full — confirm the exact current JSX for `resolution.warnings` (currently: `<ul>{resolution.warnings.map((w) => <li key={w.id}>{w.message}</li>)}</ul>`, right after the loading/error block for the `/api/resolve` call).

- [ ] **Step 2: Add a mirrored block for `pruned`**

Add, immediately after the existing `warnings` `<ul>` block (inside the same `{resolution && (...)}` conditional), a small heading and list, matching this project's Bulgarian-language, plain-register convention:

```tsx
      {resolution && resolution.pruned.length > 0 && (
        <>
          <h3>Отпаднали избори</h3>
          <ul>
            {resolution.pruned.map((p) => (
              <li key={p.choiceId}>{p.reason}</li>
            ))}
          </ul>
        </>
      )}
```

(Only render the heading/list when `pruned` is non-empty — unlike `warnings`, which always renders its `<ul>` even when empty per the existing code; check the existing `warnings` block's exact behavior first and decide whether to match it exactly or use this cleaner non-empty-only gate — your judgment, but be deliberate about the choice rather than copying blindly if the two should arguably behave the same way.)

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors.

- [ ] **Step 4: Manual browser verification**

Start the backend (check if already running: `curl -s http://127.0.0.1:8000/api/health`; if not, `cd server && .venv/bin/python app.py > /tmp/dnd-backend.log 2>&1 &`) and the frontend dev server (`.claude/launch.json` has a `frontend-dev` config — use `preview_start` with `name: "frontend-dev"`). Build a Fighter at level 4 with a level-4 ASI selected via the Class page, confirm the resolution updates, then lower the level back to 3 and confirm:
1. The "Отпаднали избори" section appears on the Home page.
2. It names `class:fighter:4:asi` in its message.
3. Raising the level back to 4 makes the section disappear again and the ASI choice re-resolves correctly (confirming the Draft's old selection genuinely resurfaced, per the architecture's existing undo-friendly design).

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add frontend/src/pages/HomePage.tsx
git commit -m "$(cat <<'EOF'
feat: render Resolution.pruned on the Home page

Mirrors the existing resolution.warnings rendering exactly — a small
list naming every stale-but-inert selection so a player who leveled
down, switched subclass, or otherwise invalidated a past choice can
see why it silently stopped applying, instead of wondering in silence.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- Task 1's two tests were fully grounded while writing this plan, not left as placeholders — both scenarios (level-down leaving an ASI choice stale; clearing a subclass leaving its subclass-gated feature choice stale) were run directly against the real bundled catalog before being written into the plan, and a third naively-plausible scenario (background/species/class switching, or class removal) was checked and confirmed NOT reachable, since those reducer actions all reset or delete the relevant `choices` data outright — there's nothing left to go stale.
- This is a small, two-task plan (matching this phase's own design spec framing as "purely about visibility, not correctness" and explicitly smaller than Phase 3b) — no fix-loop-heavy complexity is expected, but the empirical grounding in Task 1 Step 2 is still mandatory, not optional, since this project's history shows skipping it is exactly how RAW/data-shape bugs slip through.
