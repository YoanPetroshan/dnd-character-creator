# Phase 3b-i — Multiclassing Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a character have 2+ classes. Each class levels and grants features/ASIs/spell-choices independently (reusing Phase 3a's existing per-class helpers, called once per class instead of once total). Proficiency bonus derives from total character level. HP correctly applies "only your very first class level ever takes the hit die's max." Multiclass-specific proficiency grants (fixed + choice) apply to every class after the first. Prerequisites are enforced as a `problem`, never a hidden option. The multiclass spell-slot table is explicitly OUT of scope (Phase 3b-ii).

**Architecture:** Per the design spec (`docs/superpowers/specs/2026-09-20-builder-v2-phase3b-i-multiclassing-core-design.md`), almost every per-class helper in `server/engine/resolve.py` is already parameterized by a single class's data (`cls`, `cls_id`, `level`, `subclass_id`) — the core of this phase is turning `resolve()`'s single call-per-helper into a loop over `draft.classes`, plus a handful of genuinely new cross-class computations (total-level prof bonus, multiclass HP, multiclass proficiency grants/choices, prerequisites). `sheet["class"]` (a single object) becomes `sheet["classes"]` (a list) — a breaking change, consistent with every prior phase's precedent of not maintaining backward-compat shims.

**Tech Stack:** Same as every prior phase — Python/Flask backend (`server/`), React+TypeScript frontend (`frontend/`), no new dependencies.

## Global Constraints

- **Every fact this plan relies on was verified against the real bundled SRD data while writing the design spec** — see the spec's "Confirmed empirically" callouts. Do not re-derive these from RAW/training-data memory; the spec's grounding IS the source of truth for this plan.
- **No new hardcoded reference tables** — every multiclass-specific value (`prerequisites`, `prerequisite_options`, `proficiencies`, `proficiency_choices`) is already present per-class in the bundled `5e-SRD-Classes.json` under a `multi_classing` key; this phase only reads it.
- **`sheet["class"]` → `sheet["classes"]: list[...]` is a breaking, non-backward-compatible shape change** — matches this project's established precedent (Phase 3a's spell-choice-id change, every earlier Draft-shape change). No migration path, no dual-shape support.
- **Every existing Phase 1/2/3a test must keep passing UNCHANGED** — a single-class draft (`len(classes) == 1`) must resolve identically to before this phase; it's just the `len == 1` case of the new general loop. If an existing test's expected VALUE needs to change, that's a signal of a real regression, not something to "fix" in the test.
- **The manual multiclass ASI-ordering decision** (per the design spec): ASI-granting levels are processed **in `draft.classes` array order** (class 0's ASI levels first, then class 1's, etc.), not interleaved by any notion of "historical" level-up order — the Draft only records each class's *current* level, never the order levels were taken in.
- **Prerequisites are a `problem`, never a hidden/removed option** — matches the architecture spec §4a and this project's established pattern.

---

### Task 1: `hit_point_max_multiclass` — HP across multiple classes

**Files:**
- Modify: `server/engine/derived.py`
- Test: `server/tests/test_derived.py`

**Interfaces:**
- Consumes: `hit_point_max(hit_die, con_modifier)` and `hit_point_gain_per_level(hit_die, con_modifier, hp_type, level, hp_rolls)` — both already exist, UNCHANGED by this task.
- Produces: `hit_point_max_multiclass(class_entries: list[dict], con_modifier: int, hp_type: str) -> int`, where each entry in `class_entries` is `{"hit_die": int, "level": int, "hp_rolls": dict[str, int]}`, in `draft.classes` array order.

- [ ] **Step 1: Write the failing tests**

Open `server/tests/test_derived.py` and read its existing conventions for `hit_point_max_at_level` tests. Add:

```python
def test_hit_point_max_multiclass_single_class_matches_hit_point_max_at_level():
    # A single-entry list must produce EXACTLY what hit_point_max_at_level
    # already produces — this is the regression-safety anchor: multiclass
    # HP for one class is not a new formula, it's the existing one.
    entries = [{"hit_die": 10, "level": 5, "hp_rolls": {}}]
    result = hit_point_max_multiclass(entries, con_modifier=2, hp_type="fixed")
    expected = hit_point_max_at_level(10, con_modifier=2, level=5, hp_type="fixed", hp_rolls={})
    assert result == expected


def test_hit_point_max_multiclass_only_first_class_level_1_gets_the_max():
    # Fighter (d10) taken first at level 1, then Wizard (d6) multiclassed
    # in at level 1 — Wizard's OWN level 1 must NOT take d6's max (6),
    # it must use the fixed/average method like any level above 1.
    entries = [
        {"hit_die": 10, "level": 1, "hp_rolls": {}},
        {"hit_die": 6, "level": 1, "hp_rolls": {}},
    ]
    result = hit_point_max_multiclass(entries, con_modifier=1, hp_type="fixed")
    # Fighter L1: 10 (max) + 1 (con) = 11
    # Wizard's own "L1" (its first level, but NOT the character's first
    # level overall): average (6//2+1=4) + 1 (con) = 5
    assert result == 11 + 5


def test_hit_point_max_multiclass_sums_every_class_correctly():
    # Fighter 3 (d10) / Wizard 2 (d6), fixed mode.
    entries = [
        {"hit_die": 10, "level": 3, "hp_rolls": {}},
        {"hit_die": 6, "level": 2, "hp_rolls": {}},
    ]
    result = hit_point_max_multiclass(entries, con_modifier=2, hp_type="fixed")
    # Fighter: L1 max (10+2=12) + L2 avg (6+2=8) + L3 avg (6+2=8) = 28
    # Wizard: "L1" avg (4+2=6) + "L2" avg (4+2=6) = 12
    assert result == 28 + 12


def test_hit_point_max_multiclass_manual_mode_uses_per_class_rolls():
    entries = [
        {"hit_die": 10, "level": 2, "hp_rolls": {"2": 7}},
        {"hit_die": 8, "level": 2, "hp_rolls": {"2": 5}},
    ]
    result = hit_point_max_multiclass(entries, con_modifier=1, hp_type="manual")
    # Fighter: L1 max (10+1=11) + L2 roll (7+1=8) = 19
    # Rogue-shaped d8 secondary: "L1" avg (8//2+1=5, +1 con=6) + "L2" roll (5+1=6) = 12
    assert result == 19 + 12


def test_hit_point_max_multiclass_empty_list_is_zero():
    assert hit_point_max_multiclass([], con_modifier=0, hp_type="fixed") == 0
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_derived.py -v -k multiclass`
Expected: FAIL (`hit_point_max_multiclass` doesn't exist).

- [ ] **Step 3: Implement**

In `server/engine/derived.py`, add after `hit_point_max_at_level`:

```python
def hit_point_max_multiclass(class_entries: list[dict], con_modifier: int, hp_type: str) -> int:
    """Sums HP across every class in draft.classes order. Only the very
    first level of the very FIRST class entry takes the hit die's flat
    max (hit_point_max) — every other level, including every OTHER
    class's own level 1 when multiclassing into it, uses
    hit_point_gain_per_level's roll/average logic. This is 5e RAW's
    "you only take the max at 1st level, period" rule, not per-class."""
    total = 0
    for i, entry in enumerate(class_entries):
        hit_die = entry["hit_die"]
        level = entry["level"]
        hp_rolls = entry.get("hp_rolls") or {}
        start_level = 1
        if i == 0:
            total += hit_point_max(hit_die, con_modifier)
            start_level = 2
        for lvl in range(start_level, level + 1):
            total += hit_point_gain_per_level(hit_die, con_modifier, hp_type, lvl, hp_rolls)
    return total
```

Update the module docstring at the top of `derived.py` (currently says "Pure derived-stat math for a resolved single-class character") to also mention multiclass HP, e.g. append: `Multiclass HP (hit_point_max_multiclass) reuses hit_point_max/hit_point_gain_per_level unchanged — see Phase 3b-i design spec for the "only your very first class level ever takes the max" rule.`

- [ ] **Step 4: Run to verify the tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_derived.py -v`
Expected: PASS, all cases including existing ones (no existing test should need a changed expected value — `hit_point_max`/`hit_point_gain_per_level`/`hit_point_max_at_level` are untouched).

- [ ] **Step 5: Commit**

```bash
git add server/engine/derived.py server/tests/test_derived.py
git commit -m "$(cat <<'EOF'
feat: hit_point_max_multiclass — HP across multiple classes

Sums HP for every class in draft.classes order, reusing the existing
hit_point_max/hit_point_gain_per_level functions completely unchanged.
The one new rule: only the very first level of the very first class
entry ever takes the hit die's flat max — every other level, including
every OTHER class's own level 1 when multiclassing into it, uses the
roll/average method. A common correctness bug in DIY 5e builders,
called out explicitly per the Phase 3b-i design spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `resolve()` — validation and the per-class loop

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `_class_choice_templates`, `_cumulative_feature_refs`, `_feature_choice_templates`, `_asi_granting_levels`, `_apply_asi_progression`, `_asi_choice_templates`, `_spell_choice_templates` — ALL UNCHANGED, called once per class instead of once total.
- Produces: `resolve()` now accepts any number of entries in `draft.classes` (validated, capped at total level 20); `choice_templates`, `final_scores` (after ASI), and `modifiers` correctly reflect ALL classes, not just `classes[0]`.

This is the largest task in the plan — it restructures the central ~120 lines of `resolve()`. Read `server/engine/resolve.py` in full before starting (the whole function, `resolve.py:457` through roughly `resolve.py:600`) to see the exact current code you're restructuring; line numbers below are from the version at the start of this plan and may drift slightly as earlier tasks in this same plan land — re-read before each edit.

- [ ] **Step 1: Write failing tests for the new validation rules**

Add to `server/tests/test_resolve.py`:

```python
def test_two_classes_no_longer_produce_multiclass_unsupported(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])


def test_total_level_over_20_is_a_problem_not_silently_truncated(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 15, "choices": {}},
            {"classId": "wizard", "level": 10, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "total-level-exceeded" for p in resolution["problems"])


def test_duplicate_class_id_is_a_problem_and_only_first_occurrence_counted(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "fighter", "level": 5, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "duplicate-class" for p in resolution["problems"])
    # Only ONE Fighter's worth of level-1 proficiency choices should exist
    # — not two — confirming the duplicate was dropped, not merged/summed.
    prof_choices = [c for c in resolution["choices"] if c["id"] == "class:fighter:1:prof-choice-0"]
    assert len(prof_choices) == 1
```

- [ ] **Step 2: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "multiclass_unsupported or total_level_over_20 or duplicate_class"`
Expected: FAIL (`multiclass-unsupported` currently DOES appear for 2 classes; `total-level-exceeded`/`duplicate-class` don't exist yet).

- [ ] **Step 3: Replace the single-class collapse with real validation**

Find:

```python
    if len(classes) > 1:
        problems.append({"id": "multiclass-unsupported", "message": "Multiclassing isn't supported yet — pick a single class."})
        classes = classes[:1]
```

Replace with:

```python
    seen_class_ids: set[str] = set()
    deduped_classes: list[dict] = []
    for c in classes:
        cid_check = c.get("classId")
        if cid_check in seen_class_ids:
            problems.append({"id": "duplicate-class", "message": f"'{cid_check}' appears more than once in classes — only the first entry is used."})
            continue
        if cid_check is not None:
            seen_class_ids.add(cid_check)
        deduped_classes.append(c)
    classes = deduped_classes

    total_level = 0
    for c in classes:
        raw_lvl = c.get("level", 1)
        try:
            total_level += int(raw_lvl)
        except (TypeError, ValueError):
            pass  # per-entry level validation (below) already reports this
    if total_level > 20:
        problems.append({"id": "total-level-exceeded", "message": f"Total character level {total_level} exceeds the 20-level cap."})
```

- [ ] **Step 4: Restructure `cls_entry`/`cls_id`/`level` into a per-class loop**

This is the core of the task. Find the block starting at `cls_entry = classes[0] if classes else None` and running through the choice-template assembly (roughly `resolve.py:476` to `resolve.py:596` in the pre-task version — the exact block covering per-entry level validation, `cls`/`subclass` lookup, ASI progression, prof bonus, and all `if cls and cls_id:` choice-template appends).

The restructuring shape: everything that currently reads `cls_entry`/`cls_id`/`level`/`subclass_id`/`cls`/`subclass` a SINGLE time becomes a loop over `classes`, accumulating into: `choice_templates` (already a list, just append more), `final_scores` (threaded through each class's ASI progression in sequence), and a NEW `resolved_classes: list[dict]` collecting each class's resolved info (`{cls_id, cls, cls_name, level, subclass_id, subclass, class_choices}`) for later use by prof bonus / HP / proficiency / prerequisite computation (later tasks in this plan) and by the final `sheet["classes"]` assembly (Task 5).

Write it as:

```python
    resolved_classes: list[dict] = []
    for idx, entry in enumerate(classes):
        entry_cls_id = entry.get("classId")
        entry_subclass_id = entry.get("subclassId")
        entry_level = 1
        raw_level = entry.get("level", 1)
        try:
            entry_level = int(raw_level)
        except (TypeError, ValueError):
            problems.append({"id": "level-unsupported", "message": f"Level {raw_level!r} for '{entry_cls_id}' isn't a valid number; using 1 instead."})
            entry_level = 1
        if not (1 <= entry_level <= 20):
            problems.append({"id": "level-unsupported", "message": f"Level {entry_level} for '{entry_cls_id}' is out of the 1-20 range; using 1 instead."})
            entry_level = 1

        entry_cls = catalog.classes.get(entry_cls_id) if entry_cls_id else None
        if entry_cls_id and not entry_cls:
            problems.append({"id": "unknown-class", "message": f"Unknown class '{entry_cls_id}'."})

        entry_subclass = catalog.subclasses.get(entry_subclass_id) if entry_subclass_id else None
        if entry_subclass_id and not entry_subclass:
            problems.append({"id": "unknown-subclass", "message": f"Unknown subclass '{entry_subclass_id}'."})
            entry_subclass_id = None
        elif entry_subclass and entry_cls_id and entry_subclass.get("class", {}).get("index") != entry_cls_id:
            problems.append({
                "id": "subclass-mismatch",
                "message": f"'{entry_subclass['name']}' isn't a subclass of '{entry_cls_id}'.",
            })
            entry_subclass_id = None

        entry_choices_raw = entry.get("choices")
        entry_class_choices = entry_choices_raw if isinstance(entry_choices_raw, dict) else {}

        resolved_classes.append({
            "index": idx, "cls_id": entry_cls_id, "cls": entry_cls, "level": entry_level,
            "subclass_id": entry_subclass_id, "subclass": entry_subclass, "class_choices": entry_class_choices,
        })
```

Keep `cls_entry`, `cls_id`, `subclass_id`, `level`, `cls`, `subclass`, `class_choices` as ALIASES to `resolved_classes[0]`'s fields immediately after this loop, so every OTHER piece of `resolve()` that hasn't been touched yet in this task (background, species, equipment, and the final sheet-assembly code that Task 5 will update) keeps working unchanged for now:

```python
    cls_entry = classes[0] if classes else None
    primary = resolved_classes[0] if resolved_classes else None
    cls_id = primary["cls_id"] if primary else None
    cls = primary["cls"] if primary else None
    subclass_id = primary["subclass_id"] if primary else None
    subclass = primary["subclass"] if primary else None
    level = primary["level"] if primary else 1
    class_choices = primary["class_choices"] if primary else {}
```

(This alias step is deliberate and temporary-in-spirit but permanent-in-code: it lets this task land as a self-contained, testable unit without also having to rewrite prof-bonus/HP/proficiency/prerequisite/sheet code in the same task — those are Tasks 3-5. Every one of those later tasks replaces a specific alias's USE with real multi-class logic; none of them undo this aliasing block itself except where explicitly noted.)

- [ ] **Step 5: Loop the choice-template generation and ASI progression over every class**

Find the block:

```python
    asi_levels: list[int] = []
    if cls and cls_id:
        asi_levels = _asi_granting_levels(catalog, cls_id, level)
    asi_scores_by_level, final_scores = _apply_asi_progression(final_scores, asi_levels, class_choices, cls_id)

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus_row = catalog.class_level_row(cls_id, level) if cls and cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2

    # Choice templates from every source.
    choice_templates: list[dict] = []
    level_row = None
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.class_level_row(cls_id, level)
        feature_refs = _cumulative_feature_refs(catalog, cls_id, subclass_id, level)
        choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], feature_refs, subclass_id)
        choice_templates += _asi_choice_templates(cls_id, cls["name"], asi_levels, asi_scores_by_level)
        spell_ability = spells_mod.spellcasting_ability(cls)
        if spell_ability and level_row:
            choice_templates += _spell_choice_templates(catalog, cls, cls_id, level_row, modifiers[spell_ability], class_level=level)
```

Replace with a loop that runs this exact logic once per RESOLVED class (not just the primary), threading `final_scores` through each class's ASI progression in array order (per the Global Constraints' explicit ASI-ordering decision):

```python
    choice_templates: list[dict] = []
    for rc in resolved_classes:
        rc_cls, rc_cls_id, rc_level, rc_subclass_id = rc["cls"], rc["cls_id"], rc["level"], rc["subclass_id"]
        rc_class_choices = rc["class_choices"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_asi_levels = _asi_granting_levels(catalog, rc_cls_id, rc_level)
        rc_asi_scores_by_level, final_scores = _apply_asi_progression(final_scores, rc_asi_levels, rc_class_choices, rc_cls_id)
        rc["asi_levels"] = rc_asi_levels  # stashed for Task 4's prerequisite check convenience, and for sheet assembly

        choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        rc_level_row = catalog.class_level_row(rc_cls_id, rc_level)
        rc["level_row"] = rc_level_row
        feature_refs = _cumulative_feature_refs(catalog, rc_cls_id, rc_subclass_id, rc_level)
        choice_templates += _feature_choice_templates(catalog, rc_cls_id, rc_cls["name"], feature_refs, rc_subclass_id)
        choice_templates += _asi_choice_templates(rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level)

    modifiers = derived_mod.ability_modifiers(final_scores)

    # Spell choices need `modifiers` (for spellcasting-ability-driven known-
    # spell counts), which isn't final until EVERY class's ASI progression
    # has run — hence this is a SECOND loop over resolved_classes, not
    # merged into the loop above.
    for rc in resolved_classes:
        rc_cls, rc_cls_id, rc_level, rc_level_row = rc["cls"], rc["cls_id"], rc["level"], rc.get("level_row")
        if not (rc_cls and rc_cls_id):
            continue
        spell_ability = spells_mod.spellcasting_ability(rc_cls)
        if spell_ability and rc_level_row:
            choice_templates += _spell_choice_templates(catalog, rc_cls, rc_cls_id, rc_level_row, modifiers[spell_ability], class_level=rc_level)
```

Update the aliases block from Step 4 to also alias `asi_levels`/`level_row` from `primary` (now that they're only set inside the loop, on the `resolved_classes` entries):

```python
    asi_levels = primary.get("asi_levels", []) if primary else []
    level_row = primary.get("level_row") if primary else None
```

(Place this right after the existing alias block from Step 4 — Python dict ordering means `primary` already has these keys by the time this runs, since the loop above runs before any code that reads these aliases.)

**Note on `level_row`/`asi_levels` being stashed onto `resolved_classes` entries via `rc["level_row"] = ...` / `rc["asi_levels"] = ...` mid-loop**: this mutates the dicts already appended to `resolved_classes` in Step 4 — Python dicts are mutable references, so this is safe and intentional, not a bug; it avoids a third pass over `resolved_classes` just to re-attach these two fields.

- [ ] **Step 6: Run to verify Step 1's tests pass, plus the full existing suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "multiclass_unsupported or total_level_over_20 or duplicate_class"`
Expected: PASS.

Then run the FULL backend suite: `cd server && .venv/bin/python -m pytest -v`
Expected: every existing test still passes UNCHANGED (single-class drafts are the `len(resolved_classes) == 1` case of the new loop — `resolved_classes[0]` behaves identically to the old single-computation code, since the loop body IS that same code, just callable per-entry now). If ANY existing test's assertion value needs to change to pass, STOP — that means the restructuring introduced a real behavior change for the single-class case, which this task must not do. Investigate before proceeding.

- [ ] **Step 7: Empirically sweep a real two-class character**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'name': 'Multiclass Test', 'sources': ['srd'],
    'classes': [
        {'classId': 'fighter', 'level': 3, 'choices': {}},
        {'classId': 'wizard', 'level': 2, 'choices': {}},
    ],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 14, 'WIS': 12, 'CHA': 8}},
    'equipment': {'added': [], 'skipped': False},
    'details': {},
}
r = resolve(draft, catalog)
print('problems:', r['problems'])
class_choice_ids = sorted(c['id'] for c in r['choices'] if c['source']['kind'] == 'class')
print('class choice ids:', class_choice_ids)
"
```

Confirm: no `multiclass-unsupported`/`total-level-exceeded`/`duplicate-class` problems; choice ids include BOTH Fighter's (`class:fighter:...`) and Wizard's (`class:wizard:...`) entries, including Wizard's own spell choices (`class:wizard:spells-cantrips`/`spells-known`) and ASI choices at whichever levels each class grants them.

- [ ] **Step 8: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: resolve() loops per-class choice generation and ASI progression

Replaces the artificial "classes[1:] is truncated with a
multiclass-unsupported problem" collapse with real validation
(duplicate class ids dropped with a problem, total level capped at 20
with a problem — never silently truncated) and turns the single-class
computation of choice templates and ASI progression into a loop over
every class in draft.classes, threading final_scores through each
class's ASI progression in array order. Every per-class helper
(_class_choice_templates, _cumulative_feature_refs,
_feature_choice_templates, _asi_choice_templates,
_spell_choice_templates) is unchanged — only the calling loop is new.
A `resolved_classes` list plus a temporary alias block keeps every
other part of resolve() (background, species, equipment, prof bonus,
HP, proficiencies, the final sheet) working against `classes[0]`
unchanged for now — Tasks 3-5 replace those alias USES one at a time.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Total-level proficiency bonus and multiclass HP wiring

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `hit_point_max_multiclass` (Task 1), `resolved_classes` (Task 2).
- Produces: `derived["proficiencyBonus"]` from total level; `derived["hitPointMax"]` via `hit_point_max_multiclass`; `derived["hitDice"]` reflects every class (e.g. `"3d10 + 2d6"`).

- [ ] **Step 1: Write failing tests**

```python
def test_multiclass_proficiency_bonus_comes_from_total_level(catalog):
    # Fighter 1 alone -> prof bonus 2. Add Wizard 4 -> total level 5 ->
    # prof bonus 3, even though Fighter's OWN level (1) would only be 2.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 1, "choices": {}},
            {"classId": "wizard", "level": 4, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["proficiencyBonus"] == 3


def test_multiclass_hit_point_max_matches_hit_point_max_multiclass(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    con_mod = (14 - 10) // 2
    expected = hit_point_max_multiclass(
        [{"hit_die": 10, "level": 3, "hp_rolls": {}}, {"hit_die": 6, "level": 2, "hp_rolls": {}}],
        con_modifier=con_mod, hp_type="fixed",
    )
    assert resolution["derived"]["hitPointMax"] == expected


def test_multiclass_hit_dice_lists_every_class(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["hitDice"] == "3d10 + 2d6"
```

(Import `hit_point_max_multiclass` at the top of `test_resolve.py` alongside the existing `resolve` import.)

- [ ] **Step 2: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "proficiency_bonus_comes_from_total or hit_point_max_matches or hit_dice_lists"`
Expected: FAIL.

- [ ] **Step 3: Implement**

Find:

```python
    prof_bonus_row = catalog.class_level_row(cls_id, level) if cls and cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2
```

Replace with (computed from any available class's level table at TOTAL level — prof bonus is confirmed class-agnostic per the design spec's empirical check):

```python
    total_level = sum(rc["level"] for rc in resolved_classes if rc["cls"])
    prof_bonus_lookup_cls_id = next((rc["cls_id"] for rc in resolved_classes if rc["cls"]), None)
    prof_bonus_row = catalog.class_level_row(prof_bonus_lookup_cls_id, total_level) if prof_bonus_lookup_cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2
```

(Note: `total_level` here is recomputed from `resolved_classes` — the SAME quantity Task 2 Step 3 already computed as a plain sum over raw `classes` entries for the `total-level-exceeded` check, but that earlier computation ran BEFORE per-entry level clamping/validation. This `total_level` uses each entry's CLAMPED, validated `level`, which is the correct one to feed into a real level-row lookup — don't reuse the earlier raw sum here.)

Find the `derived` dict construction:

```python
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_at_level(hit_die, modifiers["CON"], level, hp_type, hp_rolls),
        "hitDice": f"{level}d{hit_die}" if hit_die else None,
```

Replace the `hitPointMax`/`hitDice` lines. First, build the multiclass HP input list right before the `derived` dict (near where `hit_die`/`hp_type`/`hp_rolls` are currently computed for the primary class only — read the surrounding code to find `hit_die = cls.get("hit_die") if cls else None` and the `hp_rolls_raw = cls_entry.get("hpRolls")` lines, and replace THOSE with a loop building one entry per resolved class):

```python
    hp_type = (draft.get("preferences") or {}).get("hitPointType")
    if hp_type not in ("fixed", "manual"):
        hp_type = "fixed"
    hp_class_entries = []
    for idx, rc in enumerate(resolved_classes):
        if not rc["cls"]:
            continue
        rc_hit_die = rc["cls"].get("hit_die")
        if rc_hit_die is None:
            continue
        rc_hp_rolls_raw = classes[rc["index"]].get("hpRolls") if rc["index"] < len(classes) else None
        rc_hp_rolls = {k: v for k, v in rc_hp_rolls_raw.items() if isinstance(v, int)} if isinstance(rc_hp_rolls_raw, dict) else {}
        hp_class_entries.append({"hit_die": rc_hit_die, "level": rc["level"], "hp_rolls": rc_hp_rolls})
```

Then in the `derived` dict:

```python
        "hitPointMax": derived_mod.hit_point_max_multiclass(hp_class_entries, modifiers["CON"], hp_type),
        "hitDice": " + ".join(f"{rc['level']}d{rc['cls']['hit_die']}" for rc in resolved_classes if rc["cls"] and rc["cls"].get("hit_die")) or None,
```

Remove the now-dead single-class `hit_die`/`hp_rolls_raw`/`hp_rolls` variables that used to feed the old `hitPointMax`/`hitDice` lines (search for their OTHER usages first — `hit_die` may still be referenced elsewhere, e.g. nowhere else currently, but re-check the full file before deleting to avoid an `unbound variable` error).

- [ ] **Step 4: Run to verify the tests pass, plus the full suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "proficiency_bonus_comes_from_total or hit_point_max_matches or hit_dice_lists"`
Expected: PASS.

Then: `cd server && .venv/bin/python -m pytest -v` — expect everything green, including every existing single-class HP/prof-bonus/hitDice test (a single-class draft's `hitDice` was `"{level}d{hit_die}"` before — confirm the new `" + ".join(...)` produces the IDENTICAL string for a one-class list, e.g. `"5d10"` not `"5d10 + "` or similar off-by-one join artifact; if an existing test on `hitDice`'s exact string format breaks, this is a real formatting regression to fix, not a test to update).

- [ ] **Step 5: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: total-level proficiency bonus and multiclass HP/hit-dice

proficiencyBonus now reads from the character's TOTAL level (summed
across every class) rather than any single class's own level — matches
the design spec's empirically-confirmed fact that prof_bonus is
identical across every class's level table at a given level. hitPointMax
now goes through hit_point_max_multiclass (Task 1), and hitDice lists
every class's own hit-dice string joined with " + ".

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Multiclass proficiency grants (fixed + choice) and prerequisites

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `build_choice_template` (unchanged), `resolved_classes` (Task 2).
- Produces: a new `_multiclass_proficiency_choice_templates(cls, cls_id) -> list[dict]` function (mirrors `_class_choice_templates` exactly, sourced from `multi_classing.proficiency_choices`); `sheet["proficiencies"]` gains `armor`/`weapons`/`tools` fields; a new `problems` entry `multiclass-prerequisite-unmet-{cls_id}` when `usePrerequisites.multiclass` is on and a class's requirement isn't met.

- [ ] **Step 1: Write failing tests**

```python
def test_secondary_class_multiclass_proficiency_choice_is_generated(catalog):
    # Rogue's multi_classing.proficiency_choices grants a skill choice
    # when taken as a SECONDARY class (confirmed empirically: choose 1
    # from an 11-skill list) — distinct from Rogue's own level-1
    # proficiency_choices (a bigger 4-skill choice), which only applies
    # when Rogue is the FIRST class.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    mc_choice = next((c for c in resolution["choices"] if c["id"] == "class:rogue:multiclass-prof-choice-0"), None)
    assert mc_choice is not None
    assert mc_choice["count"] == 1
    assert any(o["id"] == "skill-stealth" for o in mc_choice["options"])


def test_primary_class_does_not_get_a_multiclass_proficiency_choice(catalog):
    # Rogue as the FIRST class should NOT also get the multiclass-only
    # choice template — only its normal level-1 prof-choice-0.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "rogue", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert not any(c["id"] == "class:rogue:multiclass-prof-choice-0" for c in resolution["choices"])


def test_secondary_class_fixed_multiclass_proficiencies_appear_on_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    profs = resolution["sheet"]["proficiencies"]
    assert "light-armor" in profs["armor"]
    assert "thieves-tools" in profs["tools"]
    # Fighter (primary) should contribute ITS full level-1 grant too:
    assert "martial-weapons" in profs["weapons"]


def test_multiclass_prerequisite_unmet_is_a_problem_when_preference_on(catalog):
    # Wizard requires INT >= 13 to multiclass in/out of. Give a low INT.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "wizard", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 8, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "multiclass-prerequisite-unmet-wizard" for p in resolution["problems"])
    # The class must still be FULLY resolved despite the unmet prerequisite:
    assert resolution["sheet"]["classes"][1]["id"] == "wizard"


def test_multiclass_prerequisite_check_skipped_when_preference_off(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "wizard", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 8, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": False}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"].startswith("multiclass-prerequisite-unmet") for p in resolution["problems"])


def test_fighter_secondary_class_prerequisite_options_str_or_dex(catalog):
    # Fighter's multiclass prereq is "choose 1 of STR>=13 / DEX>=13" —
    # confirm meeting DEX alone (not STR) is sufficient.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 2, "choices": {}},
            {"classId": "fighter", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 8, "DEX": 14, "CON": 14, "INT": 14, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "multiclass-prerequisite-unmet-fighter" for p in resolution["problems"])
```

(**Confirmed**: `_fighter_acolyte_human_draft(**overrides)` merges via `draft.update(overrides)` — passing `preferences={...}` as shown above works directly, no adjustment needed. The fixture's default draft has no `preferences` key at all, so tests that don't override it get `draft.get("preferences")` as `None`, matching every existing test's implicit "prerequisites off" behavior.)

- [ ] **Step 2: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "multiclass_prof or multiclass_prerequisite or fighter_secondary"`
Expected: FAIL.

- [ ] **Step 3: Implement the multiclass proficiency-choice template function**

Add near `_class_choice_templates` in `server/engine/resolve.py`:

```python
def _multiclass_proficiency_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    """Mirrors _class_choice_templates exactly, but sourced from
    multi_classing.proficiency_choices instead of the class's own
    top-level proficiency_choices — this is the EXTRA skill/tool choice
    a class grants when taken as a SECOND-OR-LATER class (confirmed
    empirically: Bard, Ranger, Rogue each have this; Bard has two
    envelopes — a skill choice and a musical-instrument choice)."""
    templates = []
    for i, envelope in enumerate(cls.get("multi_classing", {}).get("proficiency_choices", [])):
        cid = f"class:{cls_id}:multiclass-prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"]}
        provisional_label = "Skill Proficiencies" if envelope.get("type") == "proficiencies" else (envelope.get("type") or "Choice").title()
        tpl = build_choice_template(envelope, cid, source, provisional_label)
        if not tpl:
            continue
        if tpl["options"] and tpl["label"] == "Skill Proficiencies" and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = "Tool Proficiencies"
        templates.append(tpl)
    return templates
```

In the loop from Task 2 Step 5 that appends `_class_choice_templates(rc_cls, rc_cls_id)`, add right after it (only for non-primary classes):

```python
        choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        if rc["index"] > 0:
            choice_templates += _multiclass_proficiency_choice_templates(rc_cls, rc_cls_id)
```

- [ ] **Step 4: Extend `sheet.proficiencies` with `armor`/`weapons`/`tools`**

Find the `proficient_skills` block (now needs a sibling for non-skill proficiencies):

```python
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
```

Add right after this block (still before the `bg`/`race` skill-grant additions, or after — order doesn't matter for a set union, place it wherever reads cleanly):

```python
    proficient_armor: set[str] = set()
    proficient_weapons: set[str] = set()
    proficient_tools: set[str] = set()

    def _categorize_proficiency(prof_id: str) -> None:
        if prof_id.startswith("skill-"):
            return  # handled by proficient_skills elsewhere
        if "armor" in prof_id or prof_id == "shields":
            proficient_armor.add(prof_id)
        elif "weapon" in prof_id or prof_id in ("shortswords",):  # bundled data's one non-generic weapon-category id (Monk)
            proficient_weapons.add(prof_id)
        else:
            proficient_tools.add(prof_id)

    for c in choices:
        if c["source"]["kind"] == "class":
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)

    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        if rc["index"] == 0:
            for p in rc["cls"].get("proficiencies", []):
                _categorize_proficiency(p["index"])
        else:
            for p in rc["cls"].get("multi_classing", {}).get("proficiencies", []):
                _categorize_proficiency(p["index"])
```

(The `"weapon" in prof_id or prof_id in ("shortswords",)` categorization is a pragmatic, data-driven heuristic — confirmed correct against every value seen in the design spec's empirical scan of `multi_classing.proficiencies` (`light-armor`, `medium-armor`, `shields`, `simple-weapons`, `martial-weapons`, `shortswords`, `thieves-tools`) plus every level-1 `proficiencies` entry a class might have. If a future bundled-data update introduces a proficiency id this heuristic miscategorizes, that's a data-driven bug to fix with a real test case, not something to guess-proof further right now.)

Find the `sheet["proficiencies"]` dict construction and add the three new fields:

```python
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + chosen_languages)),
            "armor": sorted(proficient_armor),
            "weapons": sorted(proficient_weapons),
            "tools": sorted(proficient_tools),
        },
```

- [ ] **Step 5: Implement the prerequisite check**

Add a new function near the other validation helpers in `resolve.py`:

```python
def _multiclass_prerequisite_problems(resolved_classes: list[dict], final_scores: dict[str, int], use_prerequisites: bool) -> list[dict]:
    if not use_prerequisites:
        return []
    problems = []
    for rc in resolved_classes:
        cls, cls_id = rc["cls"], rc["cls_id"]
        if not (cls and cls_id):
            continue
        mc = cls.get("multi_classing", {})
        prereqs = mc.get("prerequisites")
        prereq_options = mc.get("prerequisite_options")
        if prereqs:
            met = all(final_scores.get(p["ability_score"]["index"].upper(), 0) >= p["minimum_score"] for p in prereqs)
        elif prereq_options:
            options = prereq_options.get("from", {}).get("options", [])
            choose = prereq_options.get("choose", 1)
            met_count = sum(
                1 for opt in options
                if final_scores.get(opt["ability_score"]["index"].upper(), 0) >= opt["minimum_score"]
            )
            met = met_count >= choose
        else:
            met = True  # no prerequisite data at all — nothing to fail
        if not met:
            problems.append({
                "id": f"multiclass-prerequisite-unmet-{cls_id}",
                "message": f"{cls['name']}'s multiclassing prerequisite isn't met.",
            })
    return problems
```

Call it after `final_scores`/`modifiers` are fully computed (after Task 2's per-class ASI-progression loop, and after `resolved_classes` is fully populated) and after `problems` is in scope — append its results:

```python
    use_prereqs = bool((draft.get("preferences") or {}).get("usePrerequisites", {}).get("multiclass"))
    problems += _multiclass_prerequisite_problems(resolved_classes, final_scores, use_prereqs)
```

Place this call right after the choice-template generation loops (Task 2 Step 5) — `final_scores` is stable by then, and this ordering keeps prerequisite problems appended in a predictable position relative to other problems for anyone reading raw problem-list order (not semantically required, just tidy).

- [ ] **Step 6: Run to verify the tests pass, plus the full suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "multiclass_prof or multiclass_prerequisite or fighter_secondary"`
Expected: PASS.

Then: `cd server && .venv/bin/python -m pytest -v` — expect everything green. **Confirmed**: no existing test in `test_resolve.py` does a full-dict `==` comparison against `sheet["proficiencies"]` or `sheet` as a whole (checked via grep while writing this plan), so the new `armor`/`weapons`/`tools` keys should not break any existing assertion by their mere presence. If this has changed by execution time (a test added between this plan's writing and its execution), update that test's expected dict to include the new fields' real values (e.g. Fighter's own armor/weapon proficiencies from its level-1 grant), not empty lists.

- [ ] **Step 7: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: multiclass proficiency grants (fixed + choice) and prerequisites

Secondary classes (index > 0 in draft.classes) now generate a
_multiclass_proficiency_choice_templates choice (Bard/Ranger/Rogue each
grant an extra skill/instrument choice when multiclassed into — mirrors
_class_choice_templates exactly, sourced from
multi_classing.proficiency_choices) and contribute their fixed
multi_classing.proficiencies grant. sheet.proficiencies gains
armor/weapons/tools fields, populated from the primary class's full
level-1 grant plus every secondary class's multiclass-only grant.
Prerequisites (draft.preferences.usePrerequisites.multiclass) are
checked against final ability scores for every class — Fighter's
choose-1-of-STR/DEX shape and every other class's all-must-be-met shape
both handled — producing a problem, never hiding the class.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `sheet["class"]` → `sheet["classes"]` and export consumers

**Files:**
- Modify: `server/engine/resolve.py`
- Modify: `server/export.py`
- Modify: `server/markdown_export.py`
- Modify: `server/pdf_export.py`
- Test: `server/tests/test_resolve.py`, `server/tests/test_export.py`, `server/tests/test_markdown_export.py`, `server/tests/test_pdf_export.py` (adjust test names to whatever the real existing test files are called — check `server/tests/` for the exact filenames before writing this task's steps in full).

**Interfaces:**
- Produces: `sheet["classes"]: list[{"id": str, "name": str, "level": int, "subclass": {"id", "name"} | None}]`, replacing the single `sheet["class"]` object. This is a breaking change — no dual-shape support, per the Global Constraints.

- [ ] **Step 1: Read the three export consumers first**

Read `server/export.py` around its `"class": sheet["class"]` line, `server/markdown_export.py` around its `cls = sheet["class"]` line, and `server/pdf_export.py` around its `cls = sheet["class"]` line — each in enough surrounding context (10-20 lines before/after) to see exactly how the single class object's fields (`id`, `name`, `subclass`) are currently used in each file, before changing any of them.

- [ ] **Step 2: Write failing tests for the new sheet shape**

```python
def test_sheet_classes_is_a_list_with_one_entry_per_class(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    classes = resolution["sheet"]["classes"]
    assert len(classes) == 2
    assert classes[0]["id"] == "fighter" and classes[0]["level"] == 3
    assert classes[1]["id"] == "wizard" and classes[1]["level"] == 2


def test_sheet_classes_is_empty_list_when_no_class_selected(catalog):
    resolution = resolve(_empty_draft(), catalog)
    assert resolution["sheet"]["classes"] == []


def test_sheet_classes_single_class_still_carries_subclass(catalog):
    # Regression check: a single-class draft's subclass info (already
    # tested elsewhere for the OLD sheet["class"] shape) must survive
    # the list-shape change identically.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 3, "subclassId": "champion", "choices": {}}],
    )
    resolution = resolve(draft, catalog)
    classes = resolution["sheet"]["classes"]
    assert len(classes) == 1
    assert classes[0]["subclass"] == {"id": "champion", "name": "Champion"}
```

- [ ] **Step 3: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "sheet_classes"`
Expected: FAIL (`sheet["classes"]` doesn't exist; `sheet["class"]` does).

- [ ] **Step 4: Implement the sheet shape change**

Find:

```python
        "class": {
            "id": cls_id, "name": cls["name"],
            "subclass": {"id": subclass_id, "name": subclass["name"]} if subclass_id and subclass else None,
        } if cls else None,
```

Replace with:

```python
        "classes": [
            {
                "id": rc["cls_id"], "name": rc["cls"]["name"], "level": rc["level"],
                "subclass": {"id": rc["subclass_id"], "name": rc["subclass"]["name"]} if rc["subclass_id"] and rc["subclass"] else None,
            }
            for rc in resolved_classes if rc["cls"]
        ],
```

Also find `"level": level if cls else 0,` (the top-level `sheet["level"]` field, which should now be the character's TOTAL level, not the primary class's level) and replace with:

```python
        "level": total_level if resolved_classes else 0,
```

(`total_level` here is the SAME variable Task 3 computed for the prof-bonus lookup — confirm it's in scope at this point in the function; if the sheet-assembly code runs before Task 3's `total_level` computation in file order, either move Task 3's `total_level` computation earlier or recompute it locally here as `sum(rc["level"] for rc in resolved_classes if rc["cls"])` — check the real current file order before deciding which.)

- [ ] **Step 5: Run to verify the new tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "sheet_classes"`
Expected: PASS.

Then run the FULL suite: `cd server && .venv/bin/python -m pytest -v` — expect MANY existing tests to fail here, since `sheet["class"]` no longer exists anywhere. This is expected at this point in the task — do NOT treat this as a regression to avoid; it's the reason Steps 6-8 exist. Note every failure's file (should cluster in `test_resolve.py` and the three export test files) before proceeding, so Steps 6-8's changes can be checked against a known failure set rather than re-discovering it test-by-test.

- [ ] **Step 6: Update the three export consumers**

In `server/export.py`, find:

```python
        "class": sheet["class"],
```

Replace with:

```python
        "classes": sheet["classes"],
```

(Confirm no other part of `export.py` reads `sheet["class"]`/the exported `"class"` key elsewhere — search the file for `class` before finalizing.)

In `server/markdown_export.py`, find the `cls = sheet["class"]` line and its surrounding usage (likely something like rendering `f"{cls['name']}"` and `cls.get('subclass')` for a header line). Change `cls = sheet["class"]` to `classes = sheet["classes"]`, and update whatever renders the class name/subclass to loop over `classes`, joining multiple class names with `" / "` (e.g. `"Fighter 3 / Wizard 2"` — read the exact current single-class rendering format first, then produce the natural multi-class extension of that SAME format, not a new one; if the current single-class line is e.g. `f"**Class:** {cls['name']}" + (f" ({cls['subclass']['name']})" if cls.get('subclass') else "")`, the multi-class version should read `f"**Class:** " + " / ".join(f"{c['name']} {c['level']}" + (f" ({c['subclass']['name']})" if c.get('subclass') else "") for c in classes)`).

In `server/pdf_export.py`, find the equivalent `cls = sheet["class"]` line and apply the SAME rendering-format extension logic (this file and `markdown_export.py` intentionally mirror each other's content-selection logic per this project's established pattern — keep them in sync here too).

- [ ] **Step 7: Run to verify no test still references the old shape**

Run: `cd server && .venv/bin/python -m pytest -v`
Expected: every test green. If any test file still asserts against `sheet["class"]` or an export's old single-class rendering, update ITS expected value to the new multi-class-aware format (for a single-class draft, this should produce an equivalent — not necessarily byte-identical, since the format may now include the level number where it didn't before — rendering; read what the OLD single-class test expected, and write the new expected string precisely, don't guess).

- [ ] **Step 8: Empirically verify a real multi-class export**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
catalog = load()
draft = {
    'name': 'Multiclass Test', 'sources': ['srd'],
    'classes': [
        {'classId': 'fighter', 'level': 3, 'choices': {}},
        {'classId': 'wizard', 'level': 2, 'choices': {}},
    ],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 14, 'WIS': 12, 'CHA': 8}},
    'equipment': {'added': [], 'skipped': False},
    'details': {},
}
r = resolve(draft, catalog)
print(to_yaml(r)[:500])
print('---markdown---')
print(to_markdown(r)[:500])
"
```

Confirm both outputs show BOTH classes correctly (Fighter 3 and Wizard 2), not just one.

- [ ] **Step 9: Commit**

```bash
git add server/engine/resolve.py server/export.py server/markdown_export.py server/pdf_export.py server/tests/
git commit -m "$(cat <<'EOF'
feat: sheet.class -> sheet.classes (breaking change) for multiclassing

sheet["class"] (a single object) becomes sheet["classes"] (a list, one
entry per class in draft.classes, each carrying its own level and
subclass) — a breaking change with no dual-shape support, matching
every prior phase's precedent for Draft/sheet-shape changes.
sheet["level"] is now the character's TOTAL level, not the primary
class's own level. export.py/markdown_export.py/pdf_export.py updated
to render every class, extending each file's existing single-class
format naturally (multiple classes joined, each with its own level and
subclass) rather than introducing a new format.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Frontend — reducer actions for adding/removing/addressing classes

**Files:**
- Modify: `frontend/src/DraftContext.tsx`

**Interfaces:**
- Produces: `ADD_CLASS { classId: string }`, `REMOVE_CLASS { classId: string }`. `SET_CLASS_LEVEL`, `SET_SUBCLASS`, `SET_HP_ROLL`, and `SET_CHOICE_SELECTION` (when `source === "class"`) all gain a required `classId: string` field and now target the matching entry in `draft.classes` instead of always `classes[0]`.

This is a breaking change to those four actions' payload shape, per the Global Constraints — every dispatch site across the frontend must be updated in the SAME task (Task 7 does this for `ClassPage.tsx`, the only consumer of these actions today — confirmed by the design spec's grounding).

- [ ] **Step 1: Update the `Action` union type**

Find:

```typescript
  | { type: "SET_CLASS"; classId: string }
  | { type: "SET_BACKGROUND"; backgroundId: string }
  | { type: "SET_SPECIES"; speciesId: string }
  | { type: "SET_SUBSPECIES"; subspeciesId: string | undefined }
  | { type: "SET_CLASS_LEVEL"; level: number }
  | { type: "SET_SUBCLASS"; subclassId: string | undefined }
  | { type: "SET_HP_ROLL"; level: number; value: number }
```

Replace with:

```typescript
  | { type: "SET_CLASS"; classId: string }
  | { type: "ADD_CLASS"; classId: string }
  | { type: "REMOVE_CLASS"; classId: string }
  | { type: "SET_BACKGROUND"; backgroundId: string }
  | { type: "SET_SPECIES"; speciesId: string }
  | { type: "SET_SUBSPECIES"; subspeciesId: string | undefined }
  | { type: "SET_CLASS_LEVEL"; classId: string; level: number }
  | { type: "SET_SUBCLASS"; classId: string; subclassId: string | undefined }
  | { type: "SET_HP_ROLL"; classId: string; level: number; value: number }
```

Find `SET_CHOICE_SELECTION`'s type:

```typescript
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] }
```

This stays UNCHANGED at the type level — `classId` for the class case is embedded in `choiceId` already (e.g. `class:fighter:1:prof-choice-0`), so the reducer case (Step 3 below) needs to derive which class entry to update from the choice id's own class-id segment, not from a new field. (Confirmed: every class-sourced choice id already starts with `class:{cls_id}:` per Task 2/4's ids — parseable.)

- [ ] **Step 2: Update `SET_CLASS`'s reducer case (documented narrowing, no behavior change)**

The existing `SET_CLASS` case already replaces the WHOLE `classes` array with a single fresh entry — this is now explicitly "set/replace the primary class," unchanged behavior, just add a one-line comment clarifying its narrowed role now that `ADD_CLASS` exists as a sibling:

```typescript
    case "SET_CLASS":
      // Sets/replaces the PRIMARY class (classes[0]) — clears the whole
      // array, since a new primary class invalidates every existing
      // class's choices (equipment/background choices are anchored to
      // the primary class too). Adding a SECOND-OR-LATER class is
      // ADD_CLASS below, which does NOT clear anything.
      return {
        ...state,
        classes: [{ classId: action.classId, level: 1, choices: {} }],
        equipment: { ...state.equipment, choices: {} },
      };
```

(This is the EXISTING code, unchanged — only the comment is new. Confirm by reading the current file before editing that this is really still byte-identical logic; if Task 1-5's backend changes somehow required a frontend-visible behavior change here, that would be a sign something drifted — flag it rather than silently adjusting.)

- [ ] **Step 3: Add `ADD_CLASS`/`REMOVE_CLASS` and re-scope the four existing per-class cases**

Add right after `SET_CLASS`'s case:

```typescript
    case "ADD_CLASS": {
      if (state.classes.some((c) => c.classId === action.classId)) return state; // already present — no-op
      return {
        ...state,
        classes: [...state.classes, { classId: action.classId, level: 1, choices: {} }],
      };
    }
    case "REMOVE_CLASS":
      return {
        ...state,
        classes: state.classes.filter((c) => c.classId !== action.classId),
      };
```

Find `SET_CLASS_LEVEL`'s existing case:

```typescript
    case "SET_CLASS_LEVEL": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      const level = Math.min(20, Math.max(1, action.level));
      return { ...state, classes: [{ ...cls, level }] };
    }
```

Replace with:

```typescript
    case "SET_CLASS_LEVEL": {
      const level = Math.min(20, Math.max(1, action.level));
      return {
        ...state,
        classes: state.classes.map((c) => (c.classId === action.classId ? { ...c, level } : c)),
      };
    }
```

Find `SET_SUBCLASS`'s existing case:

```typescript
    case "SET_SUBCLASS": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      return { ...state, classes: [{ ...cls, subclassId: action.subclassId }] };
    }
```

Replace with:

```typescript
    case "SET_SUBCLASS":
      return {
        ...state,
        classes: state.classes.map((c) => (c.classId === action.classId ? { ...c, subclassId: action.subclassId } : c)),
      };
```

Find `SET_HP_ROLL`'s existing case:

```typescript
    case "SET_HP_ROLL": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      return {
        ...state,
        classes: [{ ...cls, hpRolls: { ...(cls.hpRolls ?? {}), [String(action.level)]: action.value } }],
      };
    }
```

Replace with:

```typescript
    case "SET_HP_ROLL":
      return {
        ...state,
        classes: state.classes.map((c) =>
          c.classId === action.classId
            ? { ...c, hpRolls: { ...(c.hpRolls ?? {}), [String(action.level)]: action.value } }
            : c
        ),
      };
```

Find `SET_CHOICE_SELECTION`'s `"class"` branch:

```typescript
      if (action.source === "class") {
        if (state.classes.length === 0) return state; // no class picked yet — ignore
        const [cls] = state.classes;
        return {
          ...state,
          classes: [{ ...cls, choices: { ...cls.choices, [action.choiceId]: action.selected } }],
        };
      }
```

Replace with (deriving the target class from the choice id's own `class:{classId}:...` prefix, per Step 1's note):

```typescript
      if (action.source === "class") {
        const targetClassId = action.choiceId.split(":")[1];
        return {
          ...state,
          classes: state.classes.map((c) =>
            c.classId === targetClassId ? { ...c, choices: { ...c.choices, [action.choiceId]: action.selected } } : c
          ),
        };
      }
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npm run build`
Expected: FAIL — `frontend/src/pages/ClassPage.tsx` dispatches `SET_CLASS_LEVEL`/`SET_SUBCLASS`/`SET_HP_ROLL` without the now-required `classId` field. This is EXPECTED at this point; Task 7 fixes `ClassPage.tsx`. Confirm the errors are ONLY in `ClassPage.tsx` (no other file references these actions — already confirmed by this plan's own grounding) before moving to Task 7.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/DraftContext.tsx
git commit -m "$(cat <<'EOF'
feat: DraftContext actions for adding/removing/addressing classes

ADD_CLASS/REMOVE_CLASS let draft.classes grow past one entry.
SET_CLASS_LEVEL/SET_SUBCLASS/SET_HP_ROLL/SET_CHOICE_SELECTION (class
source) now target a specific classId instead of always classes[0] — a
breaking change to their payload shape, matching this project's
established precedent for Draft-shape changes. ClassPage.tsx (the only
dispatch site) is updated in the next task; this commit intentionally
leaves the frontend build red in between the two commits.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

(This task deliberately lands a build-breaking commit, fixed by the immediately next task — flag this expectation clearly to whoever reviews Task 6 in isolation, so a red `npm run build` isn't mistaken for a Task 6 failure. If your SDD process's task-reviewer would flag a red build as an automatic Critical finding regardless of this note, consider merging Tasks 6 and 7 into one task instead — a judgment call for whoever executes this plan, not a hard requirement of the plan itself.)

---

### Task 7: Frontend — `ClassPage.tsx` multi-class UI

**Files:**
- Modify: `frontend/src/pages/ClassPage.tsx`

**Interfaces:**
- Consumes: `ADD_CLASS`/`REMOVE_CLASS` and the re-scoped `SET_CLASS_LEVEL`/`SET_SUBCLASS`/`SET_HP_ROLL` (Task 6).
- Produces: a per-class-entry block (level input, subclass select, HP rolls, feature/spell choice cards) rendered once per `draft.classes` entry, plus an "+ Add Another Class" picker for classes not yet taken, plus a "✕ Remove" control per non-primary class block.

This task restructures `ClassPage.tsx` from a single-class-shaped page into one that renders a list of class blocks. Read the CURRENT `frontend/src/pages/ClassPage.tsx` in full before starting — Task 6 may have landed with slightly different surrounding code than shown below if anything drifted; treat this task's code as the target shape, adapted to whatever the real current file looks like.

- [ ] **Step 1: Extract the existing single-class UI into a `ClassBlock` component**

Everything from the current file's level input (`{selectedClassId && (<label>Ниво...`) through the end of the spells tab panel is effectively "one class's own UI block," keyed by `selectedClassId`/`classLevel`/`classDetail` (all currently derived from `classes[0]`). Extract this into a new component in the SAME file (no need for a separate file — `ClassPage.tsx` is not yet large enough to warrant a split, per this project's "follow existing patterns, don't split preemptively" convention), parameterized by `classId: string` and `isPrimary: boolean`:

```tsx
interface ClassDetail {
  subclasses: { index: string; name: string }[];
  levelFeatureCounts: Record<string, number>;
  subclassUnlockLevel: number | null;
  hit_die?: number;
}

function ClassBlock({ classId, isPrimary }: { classId: string; isPrimary: boolean }) {
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const [tab, setTab] = useState<ClassTab>("features");
  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);

  const classEntry = draft.classes.find((c) => c.classId === classId);
  const classLevel = classEntry?.level ?? 1;

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/catalog/class/${classId}`)
      .then((r) => r.json())
      .then((data: ClassDetail) => {
        if (!cancelled) setClassDetail(data);
      })
      .catch(() => {
        if (!cancelled) setClassDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [classId]);

  const classChoices = resolution
    ? resolution.choices.filter((c) => c.source.kind === "class" && c.id.startsWith(`class:${classId}:`))
    : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

  return (
    <div className="class-block">
      <h2>
        {classId} {!isPrimary && (
          <button type="button" onClick={() => dispatch({ type: "REMOVE_CLASS", classId })}>
            ✕ Премахни
          </button>
        )}
      </h2>

      <label>
        Ниво
        <input
          type="number"
          min={1}
          max={20}
          value={classLevel}
          onChange={(e) => {
            const parsed = parseInt(e.target.value, 10);
            if (!Number.isNaN(parsed)) dispatch({ type: "SET_CLASS_LEVEL", classId, level: parsed });
          }}
        />
      </label>

      {classDetail && classDetail.subclassUnlockLevel !== null && classLevel >= classDetail.subclassUnlockLevel && (
        <label>
          Подклас
          <select
            value={classEntry?.subclassId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBCLASS", classId, subclassId: e.target.value || undefined })}
          >
            <option value="">— избери подклас —</option>
            {classDetail.subclasses.map((s) => (
              <option key={s.index} value={s.index}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {classDetail && (
        <p className="higher-levels-teaser">
          Способности на по-високи нива:{" "}
          {Object.entries(classDetail.levelFeatureCounts)
            .filter(([lvl]) => Number(lvl) > classLevel)
            .reduce((sum, [, count]) => sum + count, 0)}
        </p>
      )}

      {draft.preferences.hitPointType === "manual" && classLevel >= 2 && (
        <div className="hp-rolls">
          <h3>Хвърляния за точки живот</h3>
          {Array.from({ length: classLevel - 1 }, (_, i) => i + 2).map((lvl) => (
            <label key={lvl}>
              Ниво {lvl}
              <input
                type="number"
                min={1}
                placeholder={
                  classDetail?.hit_die !== undefined ? String(Math.floor(classDetail.hit_die / 2) + 1) : undefined
                }
                value={classEntry?.hpRolls?.[String(lvl)] ?? ""}
                onChange={(e) => {
                  const parsed = parseInt(e.target.value, 10);
                  if (!Number.isNaN(parsed)) dispatch({ type: "SET_HP_ROLL", classId, level: lvl, value: parsed });
                }}
              />
            </label>
          ))}
        </div>
      )}

      <div className="tab-bar" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={effectiveTab === "features"}
          onClick={() => setTab("features")}
        >
          Способности
        </button>
        {hasSpells && (
          <button
            type="button"
            role="tab"
            aria-selected={effectiveTab === "spells"}
            onClick={() => setTab("spells")}
          >
            Заклинания
          </button>
        )}
      </div>

      {effectiveTab === "features" && (
        <div role="tabpanel">
          {!loading && featureChoices.length === 0 && <p>Няма избори за този клас.</p>}
          {featureChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
        </div>
      )}

      {effectiveTab === "spells" && (
        <div role="tabpanel">
          {spellChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
          <SpellLibrary key={classId} classId={classId} />
        </div>
      )}
    </div>
  );
}
```

(The `role="tab"`/`role="tabpanel"` `id`/`aria-controls` pairing from the original single-class markup is simplified here since there are now potentially MANY tab-bars on one page — one per class block — and the original `id="tab-features"`/`id="panel-features"` literal ids would collide across blocks. If strict ARIA `aria-controls` wiring matters to this project's accessibility bar, give each tab/panel pair an id scoped by `classId` instead of dropping the wiring entirely — a call for whoever implements this task to make based on how strictly the rest of the app treats ARIA wiring elsewhere; check `BackgroundPage.tsx`'s native `<details>` pattern and other pages for the project's real accessibility bar before deciding.)

- [ ] **Step 2: Rewrite `ClassPage` itself to render the class picker + one `ClassBlock` per entry**

```tsx
export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { error, retry } = useResolutionContext();
  const catalog = useCatalogContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const takenClassIds = new Set(draft.classes.map((c) => c.classId));
  const primaryClassId = draft.classes[0]?.classId;

  return (
    <div className="page">
      <h1>Клас</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане на класовете: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}

      {!primaryClassId && (
        <ul className="picker-list">
          {catalog.classes.map((c) => (
            <li key={c.id}>
              <label>
                <input
                  type="radio"
                  name="class"
                  checked={false}
                  onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
                />
                {c.name} (d{c.hitDie})
              </label>
            </li>
          ))}
        </ul>
      )}

      {draft.classes.map((c, i) => (
        <ClassBlock key={c.classId} classId={c.classId} isPrimary={i === 0} />
      ))}

      {primaryClassId && (
        <div className="add-class">
          <h3>+ Добави клас</h3>
          <ul className="picker-list">
            {catalog.classes
              .filter((c) => !takenClassIds.has(c.id))
              .map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => dispatch({ type: "ADD_CLASS", classId: c.id })}>
                    {c.name} (d{c.hitDie})
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

(The `<h1>Клас {loading && "…"}</h1>` loading-indicator suffix from the original file is dropped here since `loading` now belongs inside each `ClassBlock`, not the page shell — if a page-level loading indicator is still wanted, thread `resolution`'s loading state through from `useResolutionContext()` at the page level too; a minor polish call, not required for this task's core goal.)

- [ ] **Step 3: Type-check**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors (this is what fixes Task 6's intentionally-red build).

- [ ] **Step 4: Manual browser verification**

Start the backend and `frontend-dev` (per `.claude/launch.json`, as in every prior frontend task this project has done). Navigate to `/class`:

1. Pick a primary class (e.g. Fighter) — confirm its `ClassBlock` renders with level input, feature choices, etc., exactly as before this plan.
2. Confirm "+ Добави клас" now shows every OTHER class (Fighter itself excluded from the add-list).
3. Click to add a second class (e.g. Wizard) — confirm a SECOND `ClassBlock` renders, with its own independent level input, its own feature/spell choices, and a "✕ Премахни" button (the primary Fighter block should NOT have a remove button).
4. Set Wizard's level to 2, confirm Wizard's own spell choices appear and are independently selectable from Fighter's feature choices.
5. Click "✕ Премахни" on the Wizard block — confirm it disappears and `draft.classes` reverts to just Fighter (check via the page re-rendering the single-class state, or via `localStorage`'s persisted draft).
6. Confirm the resolved HP/prof-bonus/derived stats elsewhere in the app (e.g. on the `/abilities` or `/export` page) reflect the MULTI-class totals while both classes are present — this is the end-to-end proof that the whole backend chain (Tasks 1-5) is actually wired to this UI, not just independently correct in isolation.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ClassPage.tsx
git commit -m "$(cat <<'EOF'
feat: ClassPage renders one block per class, with add/remove

Extracts the existing single-class UI into a ClassBlock component
(level input, subclass select, HP rolls, feature/spell tabs) rendered
once per draft.classes entry. A "+ Добави клас" picker lists every
class not yet taken; each non-primary block gets a "✕ Премахни" button
dispatching REMOVE_CLASS. This is the UI-side half of Task 6's
DraftContext actions — the two together make the whole multiclassing
feature reachable end-to-end.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- **Tasks 6 and 7 deliberately land as two commits with a red build in between** — this is a documented, intentional exception to "every commit should leave things working," made because Task 6's reducer changes and Task 7's UI changes are tightly coupled (the UI is meaningless without the actions, the actions are meaningless without a UI to dispatch them) and splitting them lets each be reviewed/tested at a reasonable granularity rather than one enormous frontend task. If the SDD process executing this plan treats a red build as an automatic per-task blocker, merge Tasks 6 and 7 into one task instead.
- **Task 2 is the largest and highest-risk task in this plan** — it restructures the center of `resolve()`. Its "alias block" approach (Step 4) is deliberately chosen so Tasks 3-5 can each be reviewed independently against a stable, working Task 2 baseline, rather than requiring one monolithic "rewrite all of resolve() at once" task. If a reviewer finds the alias block itself objectionable (e.g. "why not just delete `cls`/`cls_id`/etc. and update every downstream reference in one task"), that's a legitimate simplification for a LATER cleanup pass, not a defect in Task 2 itself — weigh review-loop cost against code tidiness here.
- **The `_categorize_proficiency` heuristic in Task 4** (armor/weapon/tool bucketing by substring match) is explicitly flagged as pragmatic-not-bulletproof — verified correct against every value that currently EXISTS in the bundled data, not proven correct for hypothetical future data. This is consistent with this project's general stance (react to real data, don't over-engineer for hypothetical shapes) but is worth a reviewer's extra scrutiny given it's the one piece of this plan without a fully closed-form data source to check against.
- **3b-ii (multiclass spell slots) is a separate future spec/plan** — nothing in this plan should be read as attempting it. A multiclass character's spell-slot COUNT during this phase will simply be wrong/absent-of-a-shared-pool (each class's own cantrip/known-spell CHOICES still resolve correctly per-class, since those were never touched — only the shared SLOT POOL computation, which doesn't exist yet at all, either single- or multi-class, is out of scope here and in every prior phase).
