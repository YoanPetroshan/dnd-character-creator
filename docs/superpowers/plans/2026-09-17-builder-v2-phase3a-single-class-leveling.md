# Builder v2 Phase 3a — Single-Class Leveling (1-20) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `resolve()` from level-1-only to levels 1-20 for a single class — cumulative per-level feature choices, subclass selection, ASI choices, and per-level HP growth — per the approved design spec `docs/superpowers/specs/2026-09-17-builder-v2-phase3a-single-class-leveling-design.md`.

**Architecture:** Fix a latent data-shape ambiguity in the SRD level-row lookup (base-class rows vs. subclass-feature rows share no other distinguishing marker than a `subclass` key). Add two small pure-math modules (`engine/asi.py` for the 21 ASI combinations + cap-checking, an extension to `engine/derived.py` for per-level HP). Make class-feature-choice generation loop over every reached level instead of just level 1, using real per-level ids so level-1 characters remain byte-identical (regression safety). Add subclass selection as a dedicated field (mirroring how species subspecies already works), not a generic Choice. Enrich the class catalog endpoint with per-level feature counts and the subclass unlock level, so the frontend has a single source of truth rather than a duplicated table. Wire a level selector, subclass dropdown, and HP display into `ClassPage.tsx` — ASI choices need **zero** new frontend choice-rendering code, since they're deliberately shaped to flow through the existing generic `<ChoiceCard>`/`<ChoicePicker>` machinery untouched.

**Tech Stack:** Same as every prior phase — Python/Flask backend, React/TypeScript frontend, no new dependencies.

## Global Constraints

- **Level 1 must remain byte-identical to today's behavior.** Every existing Phase 1/2 test exercises level 1 only — this is the regression safety net for this entire phase. Any change that alters a level-1 character's `resolve()` output (choice ids, sheet shape, derived stats) is a bug, not an acceptable side effect. Where a choice's id scheme changes (spell cantrips/known — see Task 4), verify explicitly that level 1's OTHER ids (proficiency choices, feature choices, equipment) are unaffected.
- **No feats.** The bundled SRD has no feat data. ASI choices are ability-score-only. Do not add a "or take a feat" branch anywhere in this phase.
- **Multiclassing stays rejected.** `resolve()`'s existing `multiclass-unsupported` problem for `len(classes) > 1` is untouched — this phase is single-class only, per the spec's explicit 3a/3b split.
- **No pruning logic needed or wanted in this phase.** Per the spec's §7, level-down (or a subclass change) is already safe without deleting or migrating any stored selection — a choice template simply isn't generated once its level/subclass no longer applies, so its stored (but now-irrelevant) selection sits inert in the Draft. Do not add code to delete or warn about stale selections — that's explicitly 3c's job, later.
- **Two independently-verified data findings ground this whole plan — re-verify them yourself at implementation time rather than trusting this document, since re-verification is cheap and this project's history has repeatedly found value in it:** (1) `5e-SRD-Levels.json` rows without a `subclass` key are base-class rows; rows with one are subclass-feature rows — same `class.index` value, no other reliable distinguishing marker. (2) `ability_score_bonuses` in a level row is a **cumulative count**, not a per-level flag — the actual ASI-granting levels are found by diffing consecutive levels, and Fighter (extra at 6, 14) and Rogue (extra at 10) genuinely differ from the other 10 classes' 4/8/12/16/19 pattern.

---

### Task 1: Fix `level_row` ambiguity, add `SUBCLASS_UNLOCK_LEVEL`

**Files:**
- Modify: `server/catalog/loader.py`
- Modify: `server/catalog/reference_data.py`
- Modify: `server/tests/test_loader.py`

**Interfaces:**
- Produces: `Catalog.class_level_row(class_id, level) -> dict | None` (replaces `Catalog.level_row`, now explicitly excludes subclass-tagged rows), `Catalog.subclass_level_row(subclass_id, level) -> dict | None` (new), `reference_data.SUBCLASS_UNLOCK_LEVEL: dict[str, int]` (new).

- [ ] **Step 1: Empirically re-verify the row-shape distinction**

Run from `server/`:

```bash
cd server && .venv/bin/python -c "
import json
levels = json.load(open('../chargen/data/srd/5e-SRD-Levels.json'))
wiz = [l for l in levels if l.get('class',{}).get('index')=='wizard']
print('total wizard rows:', len(wiz))
print('without subclass key:', len([l for l in wiz if 'subclass' not in l]))
print('with subclass key:', len([l for l in wiz if 'subclass' in l]))
"
```

Expected: `total wizard rows: 24`, `without subclass key: 20`, `with subclass key: 4`. If this doesn't match, stop and re-investigate the actual shape before writing code — the rest of this task depends on it.

- [ ] **Step 2: Write failing tests**

Open `server/tests/test_loader.py` first and read its existing `level_row` tests (there are a few, testing Fighter level 1 and two not-found cases) — you'll replace their method name, not their intent. Replace the file's `level_row` tests with:

```python
def test_class_level_row_returns_base_class_row_only():
    row = catalog.class_level_row("fighter", 1)
    assert row is not None
    assert row["level"] == 1
    assert "subclass" not in row


def test_class_level_row_excludes_subclass_rows_at_a_colliding_level():
    # Wizard's own level-2 row (arcane-tradition feature) and Evocation's
    # subclass-level-2 row (evocation-savant/sculpt-spells) both exist
    # with class.index == "wizard" and level == 2 — this is the exact
    # ambiguity this task fixes. class_level_row must return the base
    # row, never the subclass one.
    row = catalog.class_level_row("wizard", 2)
    assert row is not None
    assert "subclass" not in row
    assert any(f["index"] == "arcane-tradition" for f in row["features"])


def test_class_level_row_unknown_class_or_level_is_none():
    assert catalog.class_level_row("not-a-class", 1) is None
    assert catalog.class_level_row("fighter", 99) is None


def test_subclass_level_row_returns_the_subclass_specific_row():
    row = catalog.subclass_level_row("evocation", 2)
    assert row is not None
    assert row["level"] == 2
    assert any(f["index"] == "evocation-savant" for f in row["features"])


def test_subclass_level_row_unknown_subclass_or_level_is_none():
    assert catalog.subclass_level_row("not-a-subclass", 2) is None
    assert catalog.subclass_level_row("evocation", 99) is None
```

(Match whatever fixture/`catalog` variable name the existing tests in this file already use — read them first, don't invent a different convention.)

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_loader.py -v`
Expected: FAIL (`AttributeError: 'Catalog' object has no attribute 'class_level_row'`, etc.)

- [ ] **Step 4: Implement in `server/catalog/loader.py`**

Find the existing `level_row` method:

```python
    def level_row(self, class_id: str, level: int) -> dict | None:
        for row in self.levels:
            if row.get("class", {}).get("index") == class_id and row.get("level") == level:
                return row
        return None
```

Replace it with:

```python
    def class_level_row(self, class_id: str, level: int) -> dict | None:
        for row in self.levels:
            if (row.get("class", {}).get("index") == class_id
                    and row.get("level") == level
                    and "subclass" not in row):
                return row
        return None

    def subclass_level_row(self, subclass_id: str, level: int) -> dict | None:
        for row in self.levels:
            if row.get("subclass", {}).get("index") == subclass_id and row.get("level") == level:
                return row
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_loader.py -v`
Expected: PASS, all cases.

- [ ] **Step 6: Add `SUBCLASS_UNLOCK_LEVEL` to `server/catalog/reference_data.py`**

Add near the end of the file (alongside `SKILL_NAMES`), with its own doc comment:

```python
# The level each class first grants its subclass-defining feature (e.g.
# Divine Domain, Primal Path) — read directly from each class's own
# features list in 5e-SRD-Levels.json. There is no structured "choose
# your subclass" envelope anywhere in the bundled data; the unlock level
# is identified only by which specifically-named feature first appears,
# so this table is hardcoded from that empirical reading — the same
# "open RAW fact the bundled JSON doesn't expose structurally" precedent
# as SKILL_ABILITY/LANGUAGES/SKILL_NAMES above. Verified against the
# actual per-class features lists at levels 1-3 while writing this plan.
SUBCLASS_UNLOCK_LEVEL: dict[str, int] = {
    "cleric": 1, "sorcerer": 1, "warlock": 1,
    "wizard": 2, "druid": 2,
    "barbarian": 3, "bard": 3, "fighter": 3, "monk": 3,
    "paladin": 3, "ranger": 3, "rogue": 3,
}
```

- [ ] **Step 7: Write a test for it**

In `server/tests/test_reference_data.py` (read its existing style first), add:

```python
def test_subclass_unlock_level_has_all_twelve_classes():
    from catalog.reference_data import SUBCLASS_UNLOCK_LEVEL
    assert set(SUBCLASS_UNLOCK_LEVEL) == {
        "barbarian", "bard", "cleric", "druid", "fighter", "monk",
        "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
    }
    assert SUBCLASS_UNLOCK_LEVEL["cleric"] == 1
    assert SUBCLASS_UNLOCK_LEVEL["wizard"] == 2
    assert SUBCLASS_UNLOCK_LEVEL["fighter"] == 3
```

- [ ] **Step 8: Run the full backend suite**

Run: `cd server && .venv/bin/python -m pytest -v`
Expected: all 168 existing tests (minus the 3 renamed `level_row` ones, replaced 1:1) plus your new cases — but note `resolve.py` still calls the OLD `catalog.level_row` name at this point in the plan, so this run WILL fail with an `AttributeError` from `resolve.py`'s own call site. That failure is expected and will be fixed in Task 4 — confirm the failure is exactly that one call site (`server/engine/resolve.py`), not something in loader.py or your new tests.

- [ ] **Step 9: Commit**

```bash
git add server/catalog/loader.py server/catalog/reference_data.py server/tests/test_loader.py server/tests/test_reference_data.py
git commit -m "$(cat <<'EOF'
fix: disambiguate base-class vs subclass-feature rows in Levels.json lookup

5e-SRD-Levels.json mixes two row shapes under the same class.index: base-
class rows (no 'subclass' key) and subclass-feature rows (has one). The
old level_row(class_id, level) had no way to tell them apart and was only
ever called with level=1, where no subclass row exists yet to collide —
this ambiguity has been latent since Phase 1a. class_level_row explicitly
excludes subclass rows; the new subclass_level_row looks up the other
shape. Also adds SUBCLASS_UNLOCK_LEVEL, a small hardcoded table (same
precedent as SKILL_ABILITY/LANGUAGES/SKILL_NAMES) since the bundled data
has no structured "choose your subclass" envelope — only the fact that a
specific named feature (Divine Domain, Primal Path, ...) first appears at
a given level.

Note: resolve.py still calls the old level_row name after this commit —
that's fixed in the next task, not this one.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Pure ASI module

**Files:**
- Create: `server/engine/asi.py`
- Test: `server/tests/test_engine_asi.py`

**Interfaces:**
- Consumes: `catalog.reference_data.ABILITIES` (existing, `["STR","DEX","CON","INT","WIS","CHA"]`).
- Produces: `asi_combinations() -> list[tuple[str, list[tuple[str, int]]]]`, `asi_exceeds_cap(deltas, current_scores) -> bool`, `apply_asi(deltas, scores) -> dict[str, int]`, `ASI_CAP = 20`.

- [ ] **Step 1: Write failing tests**

Create `server/tests/test_engine_asi.py`:

```python
from engine.asi import ASI_CAP, apply_asi, asi_combinations, asi_exceeds_cap


def test_produces_21_combinations():
    combos = asi_combinations()
    assert len(combos) == 21


def test_six_single_ability_plus_two_options():
    combos = dict(asi_combinations())
    assert combos["str-plus-2"] == [("STR", 2)]
    assert combos["cha-plus-2"] == [("CHA", 2)]
    single_options = [c for c in combos.values() if len(c) == 1]
    assert len(single_options) == 6


def test_fifteen_two_ability_plus_one_options_no_duplicate_pairs():
    combos = dict(asi_combinations())
    two_ability = {oid: deltas for oid, deltas in combos.items() if len(deltas) == 2}
    assert len(two_ability) == 15
    assert combos["str-dex-plus-1-1"] == [("STR", 1), ("DEX", 1)]
    # every two-ability option grants exactly +1/+1, no ability repeated within one option
    for deltas in two_ability.values():
        assert deltas[0][1] == 1 and deltas[1][1] == 1
        assert deltas[0][0] != deltas[1][0]


def test_asi_cap_is_20():
    assert ASI_CAP == 20


def test_exceeds_cap_true_when_a_plus_2_would_cross_20():
    assert asi_exceeds_cap([("STR", 2)], {"STR": 19}) is True
    assert asi_exceeds_cap([("STR", 2)], {"STR": 18}) is False


def test_exceeds_cap_checks_every_ability_in_a_two_ability_option():
    deltas = [("STR", 1), ("DEX", 1)]
    assert asi_exceeds_cap(deltas, {"STR": 20, "DEX": 10}) is True
    assert asi_exceeds_cap(deltas, {"STR": 10, "DEX": 20}) is True
    assert asi_exceeds_cap(deltas, {"STR": 19, "DEX": 19}) is False


def test_exceeds_cap_defaults_missing_ability_to_10():
    assert asi_exceeds_cap([("WIS", 2)], {}) is False


def test_apply_asi_increments_and_does_not_mutate_input():
    scores = {"STR": 14, "DEX": 12}
    result = apply_asi([("STR", 2)], scores)
    assert result == {"STR": 16, "DEX": 12}
    assert scores == {"STR": 14, "DEX": 12}  # original untouched


def test_apply_asi_two_ability_option():
    scores = {"STR": 10, "DEX": 10, "CON": 10}
    result = apply_asi([("STR", 1), ("DEX", 1)], scores)
    assert result == {"STR": 11, "DEX": 11, "CON": 10}


def test_apply_asi_defaults_missing_ability_to_10_before_adding():
    result = apply_asi([("CHA", 2)], {})
    assert result == {"CHA": 12}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_asi.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'engine.asi'`).

- [ ] **Step 3: Implement `server/engine/asi.py`**

```python
"""Pure ability-score-improvement (ASI) math: the 21 valid ASI
combinations for six abilities, and cap-checking/application against a
character's current final ability scores. No I/O, no catalog access —
matches engine/derived.py's and engine/equipment.py's style. See the
Phase 3a design spec §4 for why this fits the existing generic Choice
model rather than needing a new mechanism: options here are
pre-computed combination strings (a pure 5e rule, not SRD catalog
content), not resolved from any bundled JSON envelope.
"""
from __future__ import annotations

from catalog.reference_data import ABILITIES

ASI_CAP = 20


def asi_combinations() -> list[tuple[str, list[tuple[str, int]]]]:
    """Returns [(option_id, [(ability, delta), ...]), ...] — 6 "+2 to
    one ability" options plus 15 "+1 to two abilities" options
    (C(6,2)), 21 total, in a stable, deterministic order (single-ability
    options first, then two-ability options in ABILITIES order)."""
    combos: list[tuple[str, list[tuple[str, int]]]] = []
    for ab in ABILITIES:
        combos.append((f"{ab.lower()}-plus-2", [(ab, 2)]))
    for i, ab1 in enumerate(ABILITIES):
        for ab2 in ABILITIES[i + 1:]:
            combos.append((f"{ab1.lower()}-{ab2.lower()}-plus-1-1", [(ab1, 1), (ab2, 1)]))
    return combos


def asi_exceeds_cap(deltas: list[tuple[str, int]], current_scores: dict[str, int]) -> bool:
    return any(current_scores.get(ab, 10) + delta > ASI_CAP for ab, delta in deltas)


def apply_asi(deltas: list[tuple[str, int]], scores: dict[str, int]) -> dict[str, int]:
    result = dict(scores)
    for ab, delta in deltas:
        result[ab] = result.get(ab, 10) + delta
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_asi.py -v`
Expected: PASS, all 11 cases.

- [ ] **Step 5: Commit**

```bash
git add server/engine/asi.py server/tests/test_engine_asi.py
git commit -m "$(cat <<'EOF'
feat: add pure ASI math (21 combinations, 20-point cap check, apply)

Deliberately NOT a new Choice "kind" — asi_combinations()'s 21 options
are meant to be fed directly into a standard Choice's options list (see
Task 4), reusing the existing generic ChoiceCard/ChoicePicker machinery
unchanged, with cap-exceeding combos marked disabled the same way any
other option already can be.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Per-level HP in `derived.py`

**Files:**
- Modify: `server/engine/derived.py`
- Test: `server/tests/test_derived.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `hit_point_gain_per_level(hit_die, con_modifier, hp_type, level, hp_rolls) -> int`, `hit_point_max_at_level(hit_die, con_modifier, level, hp_type, hp_rolls) -> int`. The existing `hit_point_max(hit_die, con_modifier)` (level-1-only) is UNCHANGED and still called internally by the new function — this is the regression-safety anchor for level-1 characters.

- [ ] **Step 1: Write failing tests**

Open `server/tests/test_derived.py` first (short file, read its existing `hit_point_max` tests for the exact style/fixture convention) and add:

```python
def test_hit_point_gain_per_level_fixed_mode_uses_average_rounded_up():
    # d10 average: 10//2 + 1 = 6, plus CON mod
    assert hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="fixed", level=2, hp_rolls={}) == 8
    # d6 average: 6//2 + 1 = 4
    assert hit_point_gain_per_level(hit_die=6, con_modifier=0, hp_type="fixed", level=3, hp_rolls={}) == 4
    # d12 average: 12//2 + 1 = 7
    assert hit_point_gain_per_level(hit_die=12, con_modifier=-1, hp_type="fixed", level=5, hp_rolls={}) == 6


def test_hit_point_gain_per_level_manual_mode_uses_the_roll():
    assert hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=2, hp_rolls={"2": 7}) == 9


def test_hit_point_gain_per_level_manual_mode_falls_back_to_average_when_roll_missing():
    assert hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=2, hp_rolls={}) == 8
    assert hit_point_gain_per_level(hit_die=10, con_modifier=2, hp_type="manual", level=3, hp_rolls={"2": 7}) == 8  # roll exists for a DIFFERENT level


def test_hit_point_gain_per_level_manual_mode_rejects_an_out_of_range_roll():
    # a roll of 0 or > hit_die is invalid input — fall back to average rather than trust it
    assert hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": 0}) == 6
    assert hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": 99}) == 6
    assert hit_point_gain_per_level(hit_die=8, con_modifier=1, hp_type="manual", level=2, hp_rolls={"2": "not a number"}) == 6


def test_hit_point_max_at_level_1_matches_the_existing_level_1_function_exactly():
    assert hit_point_max_at_level(hit_die=10, con_modifier=2, level=1, hp_type="fixed", hp_rolls={}) == hit_point_max(10, 2)
    assert hit_point_max_at_level(hit_die=10, con_modifier=2, level=1, hp_type="manual", hp_rolls={}) == hit_point_max(10, 2)


def test_hit_point_max_at_level_sums_level_1_plus_every_subsequent_gain():
    # d10, CON +2, fixed mode: level 1 = 10+2=12; levels 2-5 each add 6+2=8 -> 12 + 4*8 = 44
    assert hit_point_max_at_level(hit_die=10, con_modifier=2, level=5, hp_type="fixed", hp_rolls={}) == 44


def test_hit_point_max_at_level_none_hit_die_is_zero():
    assert hit_point_max_at_level(hit_die=None, con_modifier=2, level=5, hp_type="fixed", hp_rolls={}) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_derived.py -v -k "hit_point_gain or hit_point_max_at_level"`
Expected: FAIL (`NameError`/`ImportError` for the two new functions).

- [ ] **Step 3: Implement in `server/engine/derived.py`**

Find the existing `hit_point_max` function (leave it completely unchanged) and add these two functions directly after it:

```python
def hit_point_gain_per_level(hit_die: int, con_modifier: int, hp_type: str, level: int, hp_rolls: dict) -> int:
    if hp_type == "manual":
        roll = hp_rolls.get(str(level))
        if isinstance(roll, int) and 1 <= roll <= hit_die:
            return roll + con_modifier
    # fixed mode, or manual mode with a missing/invalid roll -> fall back
    # to the RAW "take the average" value rather than 0 or a blocking
    # problem — a defaulted estimate is always safer than garbage HP.
    return (hit_die // 2 + 1) + con_modifier


def hit_point_max_at_level(hit_die: int | None, con_modifier: int, level: int, hp_type: str, hp_rolls: dict) -> int:
    if hit_die is None:
        return 0
    total = hit_point_max(hit_die, con_modifier)
    for lvl in range(2, level + 1):
        total += hit_point_gain_per_level(hit_die, con_modifier, hp_type, lvl, hp_rolls)
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_derived.py -v`
Expected: PASS, all cases (existing + new).

- [ ] **Step 5: Commit**

```bash
git add server/engine/derived.py server/tests/test_derived.py
git commit -m "$(cat <<'EOF'
feat: add per-level hit point growth (fixed average or manual roll)

hit_point_max_at_level() sums level-1 HP (via the existing, unchanged
hit_point_max()) plus a per-level gain for every level above 1 — the RAW
"take the average" value in fixed mode, or the player's own roll in
manual mode, falling back to the average when a roll is missing/invalid
rather than blocking or defaulting to 0.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Wire leveling into `resolve()`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog.class_level_row`/`catalog.subclass_level_row` (Task 1), `reference_data.SUBCLASS_UNLOCK_LEVEL` (Task 1), `engine.asi.asi_combinations`/`asi_exceeds_cap`/`apply_asi` (Task 2), `engine.derived.hit_point_max_at_level` (Task 3).
- Produces: `resolve()` now accepts `classes[0].level` from 1 to 20 (previously rejected anything but 1), `classes[0].subclassId` is now a real, validated field (previously read but never trusted), `classes[0].hpRolls` is read when `preferences.hitPointType === "manual"`. `sheet["level"]` reflects the real level. Spell choice ids change from `class:<id>:1:spells-cantrips`/`class:<id>:1:spells-known` to `class:<id>:spells-cantrips`/`class:<id>:spells-known` (level-agnostic — see the rationale in Step 3 before implementing; this is a deliberate, documented id change, not an oversight).

This task is the most involved in the plan — it touches significant pre-existing, already-shipped logic. Read the ENTIRE current `server/engine/resolve.py` first, not just the excerpts below, before making any change. The excerpts show exact before/after for each piece, but the file's overall structure (order of operations, variable names) must still make sense as one coherent function when you're done.

- [ ] **Step 1: Write failing tests for the new leveling behavior**

Open `server/tests/test_resolve.py` first and read its existing draft-building convention (`_fighter_acolyte_human_draft(**overrides)`) — every new test below builds on it. Add these cases:

```python
def test_level_2_to_20_is_no_longer_a_problem(catalog):
    for level in (2, 5, 10, 20):
        draft = _fighter_acolyte_human_draft(
            classes=[{"classId": "fighter", "level": level, "choices": {}}],
        )
        resolution = resolve(draft, catalog)
        assert not any(p["id"] == "level-unsupported" for p in resolution["problems"])
        assert resolution["sheet"]["level"] == level


def test_level_0_or_above_20_is_still_a_problem(catalog):
    for bad_level in (0, 21, -1):
        draft = _fighter_acolyte_human_draft(
            classes=[{"classId": "fighter", "level": bad_level, "choices": {}}],
        )
        resolution = resolve(draft, catalog)
        assert any(p["id"] == "level-unsupported" for p in resolution["problems"])


def test_level_1_character_is_byte_identical_to_before_this_phase(catalog):
    # Regression anchor: every choice id, sheet shape, and derived stat
    # for a level-1 Fighter must be unchanged from Phase 2's behavior.
    draft = _fighter_acolyte_human_draft()
    resolution = resolve(draft, catalog)
    choice_ids = {c["id"] for c in resolution["choices"]}
    assert "class:fighter:1:prof-choice-0" in choice_ids  # proficiency choice, unchanged
    # feature choices at level 1 keep their level-1 id shape
    assert any(cid.startswith("class:fighter:1:feature:") for cid in choice_ids)
    assert resolution["derived"]["proficiencyBonus"] == 2
    assert resolution["derived"]["hitPointMax"] == 12  # d10 + CON mod 1, matches existing fixture's expected value
    assert resolution["derived"]["hitDice"] == "1d10"


def test_cumulative_feature_choices_appear_as_level_increases(catalog):
    # Wizard gains a feature choice-worthy pick at level 2 (arcane-tradition
    # triggers subclass selection, not a Choice — but other classes have
    # real per-level feature choices; use a level where a NEW choice
    # genuinely appears). Verify structurally: resolving at level 3 must
    # include every choice id that resolving at level 1 includes, plus
    # possibly more — never fewer.
    draft_l1 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 1, "choices": {}}])
    draft_l3 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 3, "choices": {}}])
    ids_l1 = {c["id"] for c in resolve(draft_l1, catalog)["choices"] if c["source"]["kind"] == "class"}
    ids_l3 = {c["id"] for c in resolve(draft_l3, catalog)["choices"] if c["source"]["kind"] == "class"}
    assert ids_l1.issubset(ids_l3)


def test_prof_bonus_scales_with_level(catalog):
    # SRD prof bonus table: +2 at 1-4, +3 at 5-8, +4 at 9-12, +5 at 13-16, +6 at 17-20
    expectations = {1: 2, 5: 3, 9: 4, 13: 5, 17: 6, 20: 6}
    for level, expected in expectations.items():
        draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": level, "choices": {}}])
        resolution = resolve(draft, catalog)
        assert resolution["derived"]["proficiencyBonus"] == expected, f"level {level}"


def test_asi_choices_appear_at_the_right_levels_for_fighter(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 19, "choices": {}}])
    resolution = resolve(draft, catalog)
    asi_ids = sorted(c["id"] for c in resolution["choices"] if c["id"].endswith(":asi"))
    assert asi_ids == [
        "class:fighter:12:asi", "class:fighter:14:asi", "class:fighter:16:asi",
        "class:fighter:19:asi", "class:fighter:4:asi", "class:fighter:6:asi", "class:fighter:8:asi",
    ]


def test_asi_choices_do_not_appear_above_the_selected_level(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    asi_ids = [c["id"] for c in resolution["choices"] if c["id"].endswith(":asi")]
    assert asi_ids == ["class:fighter:4:asi"]  # not 6 or 8, since level is only 5


def test_asi_option_disabled_when_it_would_exceed_the_cap(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 19, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    asi_choice = next(c for c in resolution["choices"] if c["id"] == "class:fighter:4:asi")
    str_plus_2 = next(o for o in asi_choice["options"] if o["id"] == "str-plus-2")
    assert str_plus_2.get("disabled") is True
    dex_plus_2 = next(o for o in asi_choice["options"] if o["id"] == "dex-plus-2")
    assert not dex_plus_2.get("disabled")


def test_selecting_an_asi_actually_increases_the_final_ability_score(catalog):
    # The fixture's Human species already gives +1 to every ability score
    # (verified directly against 5e-SRD-Races.json's human entry), so
    # final STR before any ASI is 16 (fixture base) + 1 (species) = 17,
    # not the base score alone — don't forget this term when computing
    # expected values for any ASI test that uses the standard fixture.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": ["str-plus-2"]}}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["abilities"]["STR"] == 19  # 16 base + 1 species + 2 from ASI


def test_asi_cap_check_uses_the_running_score_including_earlier_asis(catalog):
    # Fixture base STR 16 + Human's +1 = 17 final before any ASI. Pick
    # str-plus-2 at level 4 -> STR 19. At level 8, str-plus-2 must be
    # disabled (19+2=21 > 20) even though a check against only the
    # base+species score (17+2=19) would have wrongly shown it as still
    # available — this is the actual distinguishing case for "stacked
    # scores, not base scores" (a check using 19 as the starting override
    # would already be at/above the interesting boundary regardless of
    # stacking, so it wouldn't prove anything about the ordering bug this
    # test exists to catch).
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 8, "choices": {
            "class:fighter:4:asi": ["str-plus-2"],
        }}],
    )
    resolution = resolve(draft, catalog)
    asi_choice_8 = next(c for c in resolution["choices"] if c["id"] == "class:fighter:8:asi")
    str_plus_2_at_8 = next(o for o in asi_choice_8["options"] if o["id"] == "str-plus-2")
    assert str_plus_2_at_8.get("disabled") is True
    assert resolution["sheet"]["abilities"]["STR"] == 19  # 16 base + 1 species + 2 from the level-4 pick


def test_subclass_selection_at_the_correct_level(catalog):
    # Cleric unlocks its subclass at level 1
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "cleric", "level": 1, "subclassId": "life", "choices": {}}],
        background={"id": "acolyte", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "subclass-mismatch" for p in resolution["problems"])


def test_subclass_mismatch_is_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 3, "subclassId": "life", "choices": {}}],  # "life" belongs to cleric, not fighter
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "subclass-mismatch" for p in resolution["problems"])


def test_spell_choice_ids_are_level_agnostic_now(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 1, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    choice_ids = {c["id"] for c in resolution["choices"]}
    assert "class:wizard:spells-cantrips" in choice_ids
    assert "class:wizard:1:spells-cantrips" not in choice_ids  # old, level-suffixed id must be gone


def test_spell_options_expand_with_level(catalog):
    # A level-5 Wizard has 3rd-level slots — the "known" spell choice's
    # options must include 3rd-level spells, not just 1st-level ones.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    known_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-known")
    option_ids = {o["id"] for o in known_choice["options"]}
    fireball_present = "fireball" in option_ids  # fireball is a real 3rd-level wizard spell, verified earlier this session
    assert fireball_present


def test_hit_point_max_grows_with_level(catalog):
    draft_l1 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 1, "choices": {}}])
    draft_l5 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    hp_l1 = resolve(draft_l1, catalog)["derived"]["hitPointMax"]
    hp_l5 = resolve(draft_l5, catalog)["derived"]["hitPointMax"]
    assert hp_l5 > hp_l1


def test_manual_hp_rolls_are_used_when_present(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 2, "hpRolls": {"2": 10}, "choices": {}}],
        preferences={"advancementType": "milestone", "hitPointType": "manual", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    # CON mod is 2, not 1 — fixture base CON 14 + Human's +1 species bonus
    # = 15, and (15-10)//2 = 2 (matches the existing level-1 regression
    # test's own hitPointMax == 12 assertion: 10 + 2 = 12). Don't assume
    # the base score's own modifier without the species bonus applied.
    # level 1: 10 (d10 max) + 2 (CON mod) = 12; level 2 manual roll 10 + 2 = 12 -> 24
    assert resolution["derived"]["hitPointMax"] == 24


def test_hit_dice_string_reflects_the_level(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["hitDice"] == "5d10"
```

Adapt the exact `_fighter_acolyte_human_draft(**overrides)` call shapes to match whatever the helper's real current signature is (read it in the file first — in particular check whether `preferences`/`background`/`abilities` are override-able keys already, or need adding to the helper itself as part of this task if they aren't yet settable).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "level or asi or subclass or hit_point or spell_choice_ids or spell_options_expand"`
Expected: FAIL — most of these will fail with the current `level-unsupported` problem still firing, missing ASI/subclass logic, etc.

- [ ] **Step 3: Implement in `server/engine/resolve.py`**

**Why spell choice ids change (read before implementing):** `cantrips_known` and the "known/prepared" spell count both GROW monotonically as a spellcaster levels up — a level-5 Wizard doesn't lose their level-1 cantrips, they gain MORE on top. The correct model is ONE persistent choice per kind (cantrips, known spells) whose `count` grows with level, not a new distinct choice generated per level (which is correct for actual per-level FEATURE choices — those genuinely are one-time, level-anchored picks — but wrong for this cumulative aggregate). This means the id must drop its level segment: `class:<id>:1:spells-cantrips` becomes `class:<id>:spells-cantrips`. This is a deliberate, documented breaking change to the id shipped in Phase 2c/2d — there is no migration path for it and none is needed (this project has made non-backward-compatible Draft/choice-id shape changes in every phase so far with no migration system; localStorage drafts referencing the old id simply get a fresh, unresolved cantrip/spell choice next time they're opened, exactly like any other shape change this session).

**Step 3a — module docstring.** Update the top-of-file docstring's scope note to add:

```
Single-class leveling (1-20), subclass selection, and ASI choices ARE in
scope as of Phase 3a — see engine/asi.py, the _asi_choice_templates/
_apply_asi_progression functions, and SUBCLASS_UNLOCK_LEVEL in
catalog/reference_data.py. Multiclassing remains out of scope (Phase 3b).
```

**Step 3b — new imports.** Add alongside the existing `from . import spells as spells_mod`:

```python
from . import asi as asi_mod
from catalog.reference_data import SUBCLASS_UNLOCK_LEVEL
```

(`derived_mod` is already imported.)

**Step 3c — level extraction and validation.** Find:

```python
    cls_entry = classes[0] if classes else None
    cls_id = cls_entry.get("classId") if cls_entry else None
    subclass_id = cls_entry.get("subclassId") if cls_entry else None
    if cls_entry and cls_entry.get("level", 1) != 1:
        problems.append({"id": "level-unsupported", "message": "Only level 1 is supported in this version."})
```

Replace with:

```python
    cls_entry = classes[0] if classes else None
    cls_id = cls_entry.get("classId") if cls_entry else None
    subclass_id = cls_entry.get("subclassId") if cls_entry else None
    level = 1
    if cls_entry:
        raw_level = cls_entry.get("level", 1)
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            problems.append({"id": "level-unsupported", "message": f"Level {raw_level!r} isn't a valid number; using 1 instead."})
            level = 1
        if not (1 <= level <= 20):
            problems.append({"id": "level-unsupported", "message": f"Level {level} is out of the 1-20 range; using 1 instead."})
            level = 1
```

**Step 3d — subclass validation.** Immediately after the class-lookup block (`cls = catalog.classes.get(cls_id) ...`), add:

```python
    subclass = catalog.subclasses.get(subclass_id) if subclass_id else None
    if subclass_id and not subclass:
        problems.append({"id": "unknown-subclass", "message": f"Unknown subclass '{subclass_id}'."})
        subclass_id = None
    elif subclass and cls_id and subclass.get("class", {}).get("index") != cls_id:
        problems.append({
            "id": "subclass-mismatch",
            "message": f"'{subclass['name']}' isn't a subclass of the selected class.",
        })
        subclass_id = None
```

(This mirrors the existing `subspecies-mismatch` block exactly — same pattern, same problem-then-reset-to-None handling.)

**Step 3e — ASI progression, computed BEFORE `modifiers`.** Find:

```python
    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        raw = base_scores.get(ab, 10)
        try:
            base_score = int(raw)
        except (TypeError, ValueError):
            problems.append({"id": f"ability-invalid-{ab}", "message": f"{ab} score {raw!r} isn't a valid number; using 10 instead."})
            base_score = 10
        final_scores[ab] = base_score + species_bonuses.get(ab, 0)
    for ab, score in final_scores.items():
        if not (1 <= score <= 30):
            problems.append({"id": f"ability-out-of-range-{ab}", "message": f"{ab} score {score} is out of the 1-30 range."})

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus = 2  # fixed at level 1 for every class, per the SRD level tables
```

Replace with:

```python
    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        raw = base_scores.get(ab, 10)
        try:
            base_score = int(raw)
        except (TypeError, ValueError):
            problems.append({"id": f"ability-invalid-{ab}", "message": f"{ab} score {raw!r} isn't a valid number; using 10 instead."})
            base_score = 10
        final_scores[ab] = base_score + species_bonuses.get(ab, 0)
    for ab, score in final_scores.items():
        if not (1 <= score <= 30):
            problems.append({"id": f"ability-out-of-range-{ab}", "message": f"{ab} score {score} is out of the 1-30 range."})

    class_choices_raw = cls_entry.get("choices") if cls_entry else None
    class_choices = class_choices_raw if isinstance(class_choices_raw, dict) else {}

    asi_levels: list[int] = []
    if cls and cls_id:
        asi_levels = _asi_granting_levels(catalog, cls_id, level)
    asi_scores_by_level, final_scores = _apply_asi_progression(final_scores, asi_levels, class_choices, cls_id)

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus_row = catalog.class_level_row(cls_id, level) if cls and cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2
```

Note `class_choices` is extracted here (early) specifically for ASI's own needs — it's the SAME dict `all_selections` reads later (`all_selections.update(cls_entry.get("choices") or {})`); reading it twice from the same source is harmless and avoids restructuring the existing `all_selections` assembly.

**Step 3f — the two new module-level functions.** Add near `_species_ability_bonuses` (top of the "pure helper functions" section):

```python
def _asi_granting_levels(catalog: Catalog, cls_id: str, max_level: int) -> list[int]:
    """ability_score_bonuses in a level row is a CUMULATIVE count, not a
    per-level flag — the actual ASI-granting levels are wherever the
    value increases from the previous level. Verified empirically while
    writing this plan: Fighter and Rogue both have real extra ASI levels
    (6/14 and 10) beyond the standard 4/8/12/16/19 every other class
    uses, and this diff-based approach correctly finds both."""
    levels: list[int] = []
    previous = 0
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        current = row.get("ability_score_bonuses", 0) if row else 0
        if current > previous:
            levels.append(lvl)
        previous = current
    return levels


def _apply_asi_progression(
    base_scores: dict[str, int], asi_levels: list[int], class_choices: dict, cls_id: str | None,
) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    """Walks ASI-granting levels in ascending order, applying each
    level's stored selection (if present and valid) to a running
    ability-score state. Returns (scores_by_level, final_scores):
    scores_by_level[lvl] is the state BEFORE that level's own ASI is
    applied (used by _asi_choice_templates to compute which options are
    disabled for that specific level's choice — a combo that's fine at
    level 4 might exceed the cap by level 8 once earlier ASIs stack),
    and final_scores is the state after every level's ASI has been
    applied — this becomes the actual final ability scores used for
    `modifiers` and everything derived from them."""
    combos = dict(asi_mod.asi_combinations())
    scores_by_level: dict[int, dict[str, int]] = {}
    running = dict(base_scores)
    for lvl in asi_levels:
        scores_by_level[lvl] = dict(running)
        cid = f"class:{cls_id}:{lvl}:asi"
        raw_selected = class_choices.get(cid) or []
        if isinstance(raw_selected, list) and len(raw_selected) == 1 and raw_selected[0] in combos:
            deltas = combos[raw_selected[0]]
            if not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
    return scores_by_level, running
```

**Step 3g — `_asi_choice_templates`.** Add near `_equipment_choice_templates`:

```python
def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
) -> list[dict]:
    templates = []
    for lvl in asi_levels:
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas)}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = "would exceed the ability score cap of 20"
            options.append(option)
        cid = f"class:{cls_id}:{lvl}:asi"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": "Ability Score Improvement",
            "description": "Increase one ability score by 2, or two ability scores by 1 each.",
            "count": 1,
            "options": options,
        })
    return templates
```

This bypasses `build_choice_template` entirely (the options aren't derived from an SRD envelope) but produces the exact same dict shape it normally returns, so it flows through the existing downstream selection-resolution loop (the `for tpl in choice_templates:` block) completely unchanged.

**Step 3h — cumulative feature refs.** Replace the current single-level feature-gathering with a level-spanning version. Find `_feature_choice_templates`:

```python
def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[dict], subclass_id: str | None,
) -> list[dict]:
    templates = []
    for ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated, and Phase 1 never has a trusted subclass pick
        envelope = (feature.get("feature_specific") or {}).get("subfeature_options")
        if not envelope:
            continue
        cid = f"class:{cls_id}:1:feature:{feature['index']}"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": 1}
        # The subfeature_options envelope itself has no 'desc' key — the
        # description text lives on the parent feature (verified directly
        # against 5e-SRD-Features.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, feature["name"], description=_join_desc(feature.get("desc")))
        if tpl:
            templates.append(tpl)
    return templates
```

Replace with:

```python
def _cumulative_feature_refs(
    catalog: Catalog, cls_id: str, subclass_id: str | None, max_level: int,
) -> list[tuple[int, dict]]:
    """Every class-level feature ref from level 1 through max_level, plus
    (once a subclass is selected) every subclass-level feature ref in the
    same range, each paired with the exact level it came from — needed so
    _feature_choice_templates can build a correctly level-suffixed choice
    id and source.level for each, not just always "1" as before Phase
    3a."""
    refs: list[tuple[int, dict]] = []
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        if row:
            refs.extend((lvl, ref) for ref in row.get("features", []))
    if subclass_id:
        for lvl in range(1, max_level + 1):
            srow = catalog.subclass_level_row(subclass_id, lvl)
            if srow:
                refs.extend((lvl, ref) for ref in srow.get("features", []))
    return refs


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
) -> list[dict]:
    templates = []
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated to a different subclass than the one selected (or none selected)
        envelope = (feature.get("feature_specific") or {}).get("subfeature_options")
        if not envelope:
            continue
        cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        # The subfeature_options envelope itself has no 'desc' key — the
        # description text lives on the parent feature (verified directly
        # against 5e-SRD-Features.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, feature["name"], description=_join_desc(feature.get("desc")))
        if tpl:
            templates.append(tpl)
    return templates
```

Note: for a level-1 character, `_cumulative_feature_refs` produces exactly the same `(1, ref)` pairs the old single-level call would have, so `cid`/`source["level"]` come out identical to today — this is the regression-safety property the Global Constraints call for.

**Step 3i — spell choice ids and option range.** Find `_spell_options`, `_spell_choice_templates`:

```python
def _spell_options(catalog: Catalog, cls_id: str, spell_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int,
) -> list[dict]:
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    templates = []
    source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, cls_id, spell_level=0),
        }}
        cid = f"class:{cls_id}:1:spells-cantrips"
        description = f"Choose {cantrips_known} cantrip{'s' if cantrips_known != 1 else ''} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, "Cantrips Known", description=description)
        if tpl:
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=1)
    if known_count > 0:
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, cls_id, spell_level=1),
        }}
        cid = f"class:{cls_id}:1:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None
        label = "Spells Known" if is_known_caster else "Prepared Spells"
        verb = "know" if is_known_caster else "prepare"
        description = f"Choose {known_count} 1st-level spell{'s' if known_count != 1 else ''} to {verb} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            templates.append(tpl)

    return templates
```

Replace with:

```python
def _spell_options(catalog: Catalog, cls_id: str, spell_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _spell_options_up_to(catalog: Catalog, cls_id: str, max_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if 1 <= s["level"] <= max_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _highest_spell_slot_level(spellcasting: dict) -> int:
    highest = 0
    for n in range(1, 10):
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0:
            highest = n
    return highest


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
) -> list[dict]:
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    templates = []
    # No `level` in source — these choices span every level a spellcaster
    # has reached (count grows as they level up), so they're not anchored
    # to one specific level the way a feature/ASI choice is.
    source = {"kind": "class", "id": cls_id, "label": cls["name"]}

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, cls_id, spell_level=0),
        }}
        cid = f"class:{cls_id}:spells-cantrips"
        description = f"Choose {cantrips_known} cantrip{'s' if cantrips_known != 1 else ''} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, "Cantrips Known", description=description)
        if tpl:
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=class_level)
    if known_count > 0:
        max_spell_level = _highest_spell_slot_level(spellcasting)
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": _spell_options_up_to(catalog, cls_id, max_spell_level),
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None
        label = "Spells Known" if is_known_caster else "Prepared Spells"
        verb = "know" if is_known_caster else "prepare"
        level_word = "spell" if max_spell_level == 1 else f"level-{max_spell_level}-or-lower spell"
        description = f"Choose {known_count} {level_word}{'s' if known_count != 1 else ''} to {verb} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            templates.append(tpl)

    return templates
```

**Step 3j — the main `resolve()` choice-template assembly.** Find:

```python
    # Choice templates from every source.
    choice_templates: list[dict] = []
    level_row = None
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.level_row(cls_id, 1)
        if level_row:
            choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], level_row.get("features", []), subclass_id)
        spell_ability = spells_mod.spellcasting_ability(cls)
        if spell_ability and level_row:
            choice_templates += _spell_choice_templates(catalog, cls, cls_id, level_row, modifiers[spell_ability])
```

Replace with:

```python
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

**Step 3k — sheet.spells lookup ids.** Find:

```python
    cantrip_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:1:spells-cantrips"), None) if cls_id else None
    known_spells_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:1:spells-known"), None) if cls_id else None
```

Replace with:

```python
    cantrip_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:spells-cantrips"), None) if cls_id else None
    known_spells_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:spells-known"), None) if cls_id else None
```

**Step 3l — HP and hit dice.** Find:

```python
    hit_die = cls.get("hit_die") if cls else None
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max(hit_die, modifiers["CON"]),
        "hitDice": f"1d{hit_die}" if hit_die else None,
```

Replace with:

```python
    hit_die = cls.get("hit_die") if cls else None
    hp_type = (draft.get("preferences") or {}).get("hitPointType")
    if hp_type not in ("fixed", "manual"):
        hp_type = "fixed"
    hp_rolls_raw = cls_entry.get("hpRolls") if cls_entry else None
    hp_rolls = {k: v for k, v in hp_rolls_raw.items() if isinstance(v, int)} if isinstance(hp_rolls_raw, dict) else {}
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_at_level(hit_die, modifiers["CON"], level, hp_type, hp_rolls),
        "hitDice": f"{level}d{hit_die}" if hit_die else None,
```

**Step 3m — sheet.level.** Find:

```python
        "name": draft.get("name") or "",
        "level": 1 if cls else 0,
```

Replace with:

```python
        "name": draft.get("name") or "",
        "level": level if cls else 0,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v`
Expected: PASS, all cases including every new one from Step 1. Pay particular attention to `test_level_1_character_is_byte_identical_to_before_this_phase` — if this fails, something in this task broke the regression-safety guarantee and must be fixed before moving on, not worked around.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all pre-existing tests plus every new one from Tasks 1-4, all green. This is the first point where Task 1's `catalog.level_row` rename fully resolves (no more `AttributeError`).

- [ ] **Step 5: Empirically sweep all 12 classes at multiple levels**

This project's history has repeatedly found real bugs only a full-class sweep catches (Phase 2a's granted-armor bug was invisible to every class except the one that structurally couldn't hide it; Phase 2c's Paladin/Ranger zero-slots case). Run from `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
classes = ['barbarian','bard','cleric','druid','fighter','monk','paladin','ranger','rogue','sorcerer','warlock','wizard']
for cls_id in classes:
    for level in (1, 4, 8, 12, 20):
        draft = {'classes': [{'classId': cls_id, 'level': level, 'choices': {}}], 'abilities': {'base': {}}}
        r = resolve(draft, catalog)
        problems = [p['id'] for p in r['problems'] if p['id'] not in ('species-ability-choice-unsupported',)]
        asi_count = len([c for c in r['choices'] if c['id'].endswith(':asi')])
        print(cls_id, level, '| prof_bonus:', r['derived']['proficiencyBonus'], '| HP:', r['derived']['hitPointMax'], '| asi_choices:', asi_count, '| problems:', problems)
"
```

Confirm: no unexpected problems for any class/level combination (only expected ones, if any — e.g. nothing tied to species/equipment since those aren't set in this minimal draft); `proficiencyBonus` matches the SRD table (2/2/3/4/6 at levels 1/4/8/12/20); `hitPointMax` increases monotonically with level for every class; `asi_choices` count matches each class's known ASI-level list up to the given level (e.g. Fighter at level 8 should show 3: levels 4, 6, 8; Rogue at level 8 should show 2: levels 4, 8). If anything doesn't match, stop and investigate before committing — don't paper over a surprise.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: wire single-class leveling 1-20 into resolve()

Cumulative per-level feature choices (correctly level-suffixed via
_cumulative_feature_refs, using class_level_row/subclass_level_row from
the ambiguity fix), a validated subclass field (mismatch now a real
problem, mirroring subspecies-mismatch), ASI choices at the correct
levels per class (computed via a diff over the cumulative
ability_score_bonuses field, catching Fighter's and Rogue's real extra
ASI levels), and per-level HP growth (fixed average or manual roll).

Spell cantrip/known choice ids drop their level segment
(class:<id>:1:spells-cantrips -> class:<id>:spells-cantrips) since the
underlying counts grow monotonically with level rather than being a
distinct per-level pick — a deliberate, documented id change with no
migration path (consistent with every prior phase's Draft-shape
changes). Spell options now expand to every spell level the character
has slots for, not just 1st level.

Level 1 remains byte-identical to pre-Phase-3a behavior — verified by a
dedicated regression test plus a full 12-class x 5-level empirical sweep.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Enrich `/api/catalog/class/<id>` for the frontend

**Files:**
- Modify: `server/app.py`
- Modify: `server/tests/test_app.py`

**Interfaces:**
- Consumes: `catalog.class_level_row` (Task 1), `reference_data.SUBCLASS_UNLOCK_LEVEL` (Task 1).
- Produces: `GET /api/catalog/class/<id>` now includes `levelFeatureCounts: Record<string, number>` (level 1-20 as string keys, each the raw count of that level's `features` list — a simple, cheap teaser count, not a fully-resolved choice count) and `subclassUnlockLevel: int | None`. This is the single source of truth the frontend reads from directly — there is deliberately no duplicated copy of `SUBCLASS_UNLOCK_LEVEL` anywhere in the frontend codebase.

- [ ] **Step 1: Write failing tests**

Open `server/tests/test_app.py` and find the existing `api_catalog_class` tests — match their style. Add:

```python
def test_catalog_class_includes_level_feature_counts(client):
    resp = client.get("/api/catalog/class/fighter")
    body = resp.get_json()
    assert "levelFeatureCounts" in body
    assert body["levelFeatureCounts"]["1"] == 2  # fighter-fighting-style, second-wind
    assert body["levelFeatureCounts"]["3"] == 1  # martial-archetype
    assert len(body["levelFeatureCounts"]) == 20


def test_catalog_class_includes_subclass_unlock_level(client):
    resp = client.get("/api/catalog/class/cleric")
    assert resp.get_json()["subclassUnlockLevel"] == 1
    resp = client.get("/api/catalog/class/fighter")
    assert resp.get_json()["subclassUnlockLevel"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_app.py -v -k "level_feature_counts or subclass_unlock_level"`
Expected: FAIL (`KeyError`).

- [ ] **Step 3: Implement in `server/app.py`**

Add the import (alongside the existing `from catalog.loader import load as load_catalog`):

```python
from catalog.reference_data import SUBCLASS_UNLOCK_LEVEL
```

Find:

```python
@app.route("/api/catalog/class/<class_id>")
def api_catalog_class(class_id: str):
    cls = _catalog.classes.get(class_id)
    if not cls:
        return jsonify({"error": "not found"}), 404
    return jsonify(cls)
```

Replace with:

```python
@app.route("/api/catalog/class/<class_id>")
def api_catalog_class(class_id: str):
    cls = _catalog.classes.get(class_id)
    if not cls:
        return jsonify({"error": "not found"}), 404
    level_feature_counts = {}
    for lvl in range(1, 21):
        row = _catalog.class_level_row(class_id, lvl)
        level_feature_counts[str(lvl)] = len(row.get("features", [])) if row else 0
    return jsonify({
        **cls,
        "levelFeatureCounts": level_feature_counts,
        "subclassUnlockLevel": SUBCLASS_UNLOCK_LEVEL.get(class_id),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_app.py -v`
Expected: PASS, all cases.

Then run the full backend suite once more: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 5: Commit**

```bash
git add server/app.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: expose per-level feature counts and subclass unlock level in the class catalog endpoint

GET /api/catalog/class/<id> now carries levelFeatureCounts (a cheap raw
per-level feature-count teaser, not a resolved-choice count — enough for
an "Available at Higher Levels (N)" UI counter without re-implementing
choice resolution client-side) and subclassUnlockLevel. The frontend
reads both directly from this response rather than maintaining its own
copy of SUBCLASS_UNLOCK_LEVEL — single source of truth, no cross-language
sync-check test needed because there's nothing to keep in sync.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Draft type + reducer for leveling

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/DraftContext.tsx`

**Interfaces:**
- Produces: `ClassSelection.hpRolls?: Record<string, number>`, and three new dispatchable actions: `SET_CLASS_LEVEL`, `SET_SUBCLASS`, `SET_HP_ROLL`.

- [ ] **Step 1: Add `hpRolls` to `ClassSelection` in `frontend/src/types.ts`**

Find:

```ts
export interface ClassSelection {
  classId: string;
  level: number;
  subclassId?: string;
  choices: Record<string, string[]>;
}
```

Replace with:

```ts
export interface ClassSelection {
  classId: string;
  level: number;
  subclassId?: string;
  hpRolls?: Record<string, number>;
  choices: Record<string, string[]>;
}
```

- [ ] **Step 2: Add the three actions to `frontend/src/DraftContext.tsx`**

Add to the `Action` union (alongside `SET_SUBSPECIES`):

```ts
  | { type: "SET_CLASS_LEVEL"; level: number }
  | { type: "SET_SUBCLASS"; subclassId: string }
  | { type: "SET_HP_ROLL"; level: number; value: number }
```

Add the reducer cases (alongside the existing `SET_SUBSPECIES` case — read it first for the exact pattern to match, since `classes` is an array with exactly 0 or 1 entries, same shape `SET_SUBSPECIES` already navigates for `species`):

```ts
    case "SET_CLASS_LEVEL": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      return { ...state, classes: [{ ...cls, level: action.level }] };
    }
    case "SET_SUBCLASS": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      return { ...state, classes: [{ ...cls, subclassId: action.subclassId }] };
    }
    case "SET_HP_ROLL": {
      if (state.classes.length === 0) return state;
      const [cls] = state.classes;
      return {
        ...state,
        classes: [{ ...cls, hpRolls: { ...(cls.hpRolls ?? {}), [String(action.level)]: action.value } }],
      };
    }
```

Note: per the design spec §7, none of these three actions clear any other field — a level change, subclass change, or HP roll edit is always safe without clearing `choices`, since `resolve()`'s template-generation-is-the-source-of-truth architecture already makes any now-irrelevant stored selection simply unused rather than corrupting anything (see the design spec's §7 for the full reasoning). Do not add clearing logic here even if it looks similar to `SET_CLASS`'s existing clear-on-change pattern — that pattern exists because `SET_CLASS` changes the class ENTIRELY (a different class's choice ids are meaningless), not because changing level/subclass/HP within the SAME class needs it.

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/DraftContext.tsx
git commit -m "$(cat <<'EOF'
feat: add level/subclass/HP-roll fields and actions to Draft

hpRolls joins the existing level/subclassId fields ClassSelection already
had (anticipated since early in this project, unused until now).
SET_CLASS_LEVEL/SET_SUBCLASS/SET_HP_ROLL are all deliberately
non-clearing — per the Phase 3a design spec, changing any of these three
is already safe without touching `choices`, since resolve()'s choice-
template generation already treats a now-irrelevant stored selection as
simply unused, not something that needs active cleanup.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Level selector, subclass dropdown, HP display, and verification

**Files:**
- Modify: `frontend/src/pages/ClassPage.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `useDraft()`, `useResolutionContext()`, `useCatalog()` (all unchanged), `SET_CLASS_LEVEL`/`SET_SUBCLASS`/`SET_HP_ROLL` (Task 6), `levelFeatureCounts`/`subclassUnlockLevel` from `GET /api/catalog/class/<id>` (Task 5).

`useCatalog()` currently only fetches the flat class LIST (`GET /api/catalog`) — this task additionally needs the single-class DETAIL endpoint (`GET /api/catalog/class/<id>`) for the currently-selected class, to read `levelFeatureCounts`/`subclassUnlockLevel`. Check whether a hook for this already exists (search the codebase for any existing fetch of `/api/catalog/class/`) before writing a new one — if `api_catalog_class`'s existing raw class object is already fetched somewhere in a prior phase, extend that fetch/hook rather than duplicating it.

**Note on ASI choices needing zero new rendering code:** ASI choices carry `source.kind === "class"` and don't match `isSpellChoiceId` (they end in `:asi`, not `:spells-cantrips`/`:spells-known`), so they automatically land in `ClassPage.tsx`'s existing `featureChoices` filter (from Phase 2d) and render via the unmodified `<ChoiceCard>`/`<ChoicePicker>` on the existing "Способности" tab — confirm this live in Step 4 rather than assuming it; if an ASI choice does NOT show up there for some reason, that's a bug to investigate, not a signal to add new rendering code.

- [ ] **Step 1: Add a level selector, subclass dropdown, and HP display to `ClassPage.tsx`**

Read the current file first (it has the class radio list, the Features/Spells tab split from Phase 2d, and the feature/spell choice rendering). Add a level selector and subclass dropdown near the top (after the class radio list, before the tab bar), and an HP summary section. Sketch (adapt to the file's actual current structure — variable names, existing hooks, exact JSX nesting — since this is describing the ADDITIONS, not a full-file replacement the way earlier simpler pages could be):

```tsx
// New state/fetch for the class detail (levelFeatureCounts, subclassUnlockLevel):
const [classDetail, setClassDetail] = useState<{
  subclasses: { index: string; name: string }[];  // "index", not "id" — see note below
  levelFeatureCounts: Record<string, number>;
  subclassUnlockLevel: number | null;
} | null>(null);

useEffect(() => {
  if (!selectedClassId) {
    setClassDetail(null);
    return;
  }
  fetch(`/api/catalog/class/${selectedClassId}`)
    .then((r) => r.json())
    .then(setClassDetail)
    .catch(() => setClassDetail(null));
}, [selectedClassId]);

// Level selector:
{selectedClassId && (
  <label>
    Ниво
    <input
      type="number"
      min={1}
      max={20}
      value={draft.classes[0]?.level ?? 1}
      onChange={(e) => {
        const parsed = parseInt(e.target.value, 10);
        if (!Number.isNaN(parsed)) dispatch({ type: "SET_CLASS_LEVEL", level: parsed });
      }}
    />
  </label>
)}

// Subclass dropdown, only once unlocked:
{selectedClassId && classDetail && classDetail.subclassUnlockLevel !== null
  && (draft.classes[0]?.level ?? 1) >= classDetail.subclassUnlockLevel && (
  <label>
    Подклас
    <select
      value={draft.classes[0]?.subclassId ?? ""}
      onChange={(e) => {
        if (e.target.value) dispatch({ type: "SET_SUBCLASS", subclassId: e.target.value });
      }}
    >
      <option value="">— избери подклас —</option>
      {classDetail.subclasses.map((s) => (
        <option key={s.index} value={s.index}>{s.name}</option>
      ))}
    </select>
  </label>
)}

// "Available at Higher Levels (N)" teaser:
{selectedClassId && classDetail && (
  <p className="higher-levels-teaser">
    Налични на по-високи нива:{" "}
    {Object.entries(classDetail.levelFeatureCounts)
      .filter(([lvl]) => Number(lvl) > (draft.classes[0]?.level ?? 1))
      .reduce((sum, [, count]) => sum + count, 0)}
  </p>
)}
```

**Empirically confirmed while writing this plan** (no need to re-derive this): the raw SRD class object `api_catalog_class` already returns (via `jsonify(cls)`, spread in Task 5's enriched response) already carries its own `subclasses` field — e.g. Cleric's is `[{"index": "life", "name": "Life", "url": "/api/2014/subclasses/life"}]`. Note the key is `index`, not `id` — unlike `/api/catalog`'s own class list (which explicitly remaps `index` → `id` when building its response), `api_catalog_class` returns the RAW class object unmapped, so `subclasses` entries keep their raw SRD field names. The `classDetail` state's TypeScript shape and the JSX above both already use `s.index` for this reason — don't "fix" it to `s.id` to match the rest of the codebase's convention, that would break against the actual API response.

- [ ] **Step 2: Add HP display**

For a spellcaster or any class, HP now depends on `preferences.hitPointType`. Add a small section showing `resolution.derived.hitPointMax` (already computed correctly server-side per Task 4 — do NOT recompute HP client-side, this page only displays and, in manual mode, collects roll inputs), and when `draft.preferences.hitPointType === "manual"`, one number input per level from 2 to the current level:

```tsx
{selectedClassId && draft.preferences.hitPointType === "manual" && (draft.classes[0]?.level ?? 1) >= 2 && (
  <div className="hp-rolls">
    <h3>Хвърляния за точки живот</h3>
    {Array.from({ length: (draft.classes[0]?.level ?? 1) - 1 }, (_, i) => i + 2).map((lvl) => (
      <label key={lvl}>
        Ниво {lvl}
        <input
          type="number"
          min={1}
          value={draft.classes[0]?.hpRolls?.[String(lvl)] ?? ""}
          onChange={(e) => {
            const parsed = parseInt(e.target.value, 10);
            if (!Number.isNaN(parsed)) dispatch({ type: "SET_HP_ROLL", level: lvl, value: parsed });
          }}
        />
      </label>
    ))}
  </div>
)}
```

- [ ] **Step 3: Minimal structural CSS**

Add to `frontend/src/index.css` (structural only, matching every prior phase's restraint):

```css
.higher-levels-teaser {
  font-size: 0.9em;
  color: #555;
}

.hp-rolls label {
  display: inline-block;
  margin-right: 12px;
}

.hp-rolls input {
  width: 60px;
}
```

- [ ] **Step 4: Typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: no errors.

- [ ] **Step 5: Manual end-to-end verification**

```bash
cd server && .venv/bin/python app.py &
sleep 1
cd ../frontend && npm run dev &
sleep 2
```

On `/class`, select **Fighter**. Confirm the level input defaults to 1 and no subclass dropdown appears (unlock level 3). Set level to 3 — confirm the subclass dropdown now appears with Fighter's real subclass option(s). Set level to 4 — confirm a new "Ability Score Improvement" choice card appears under "Способности" (the EXISTING tab, not a new one), rendered via the unmodified `<ChoiceCard>` — pick "STR +2" and confirm the ability score on `/abilities` reflects it. Set level to 8 with STR already at 19+ from the level-4 pick — confirm the "STR +2" option is now shown disabled in the level-8 ASI card. Set level back down to 2 — confirm the level-4/8 ASI cards disappear (not shown, per §7 of the design — the template just isn't generated for a level that low) but the ability score increase you already picked persists (STR stays increased, since applying an already-selected level-4 ASI doesn't depend on being AT level 4, only on level being AT LEAST 4 — re-verify this is actually true by reading `_asi_granting_levels`'s behavior: at level 2, `asi_levels` would be `[]` since 4 > 2, so the level-4 selection is NOT applied at level 2 — confirm which of these two behaviors you actually observe and make sure it matches `_asi_granting_levels`' real logic, which only includes ASI levels up to the CURRENT level; don't assume, check).

Switch to **Cleric** — confirm the subclass dropdown appears immediately at level 1. Switch to **Wizard**, set INT high via `/abilities`, set level to 5 — go to the Spells tab, confirm the "Prepared Spells"/"Cantrips Known" choice ids no longer have a level segment (inspect via browser dev tools if needed) and that a real 3rd-level spell (e.g. Fireball) appears in the spell library / choice options, not just 1st-level ones. If `preferences.hitPointType` is "manual" in your test draft, confirm HP roll inputs appear for levels 2 through the selected level and that leaving one blank still produces a sensible (non-zero, non-garbage) total HP via the average fallback.

```bash
kill %1 %2
```

- [ ] **Step 6: Run the full test suite one more time**

```bash
cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/python -m pytest -q
cd server && .venv/bin/python -m pytest -q
cd ../frontend && npm run typecheck && npm run build
```

Expected: everything green — this is the same three-suite check every prior phase's finishing step has run before merge.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ClassPage.tsx frontend/src/index.css
git commit -m "$(cat <<'EOF'
feat: level selector, subclass dropdown, HP display in ClassPage

Level input (1-20) and a subclass <select> that only appears once the
selected class actually unlocks it (per subclassUnlockLevel from the
enriched catalog endpoint) — mirrors the existing subspecies dropdown
pattern exactly, since subclass selection uses the same dedicated-field
design, not a generic Choice. An "Available at Higher Levels (N)" teaser
sums levelFeatureCounts for levels above the current one. HP display
reads resolution.derived.hitPointMax (never recomputed client-side);
manual hit-point-type mode adds one roll input per level above 1.

ASI choices needed zero new rendering code — confirmed live that they
flow through the existing, unmodified ChoiceCard/ChoicePicker exactly
like every other class-kind choice already does.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- **Task 4 is the load-bearing task of this whole plan.** Its `test_level_1_character_is_byte_identical_to_before_this_phase` test is the single most important assertion in the plan — every other task's correctness is secondary to not silently breaking every existing level-1 character. If a reviewer or implementer is under time pressure, that is the one test not to skip or weaken.
- **The ASI sequential-application design (§3e-3f in Task 4) is genuinely more complex than anything else in this plan** — it's the one place `resolve()`'s otherwise-clean "build all templates, then apply all selections in one pass" structure has to become order-dependent (each ASI level's disabled options depend on every EARLIER ASI level's actual selection, applied in level order). This is intentional and matches real 5e rules (stacking ASIs can cross the cap in an order-dependent way) — don't simplify it into a single-pass check against only the BASE scores; that would silently allow a character to exceed 20 by picking a high-value ASI after already-applied lower ones, per the spec's explicit ambiguity resolution in its own §11.
- **Do not add pruning/warning logic anywhere in this plan.** Every task deliberately avoids it, per the Global Constraints and Task 6's explicit note on the three new actions being non-clearing. This is 3c's job, later, not an oversight here.
