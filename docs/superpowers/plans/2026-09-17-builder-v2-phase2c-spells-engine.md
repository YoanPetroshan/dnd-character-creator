# Phase 2c: Spells Engine (Backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the `resolve()` engine real spellcasting support for level-1 single-class characters — cantrips and known/prepared spells as `Choice`s, plus spell save DC / spell attack bonus in `derived`, and a `sheet.spells` summary — matching the architecture spec's §8 CLASS-step "SPELLS tab" and §10 Phase 2 scope ("spells step"). Backend only; the frontend UI to actually pick spells is Phase 2d, the same split Phase 2a/2b used for equipment.

**Architecture:** New `server/engine/spells.py` holds pure spellcasting math (spell save DC, spell attack bonus, known/prepared spell count). `server/catalog/loader.py` gains a `spells` index. `server/engine/resolve.py` gains `_spell_choice_templates`, generating synthetic "choose N of..." envelopes (same shape `catalog/choices.py`'s `build_choice_template` already consumes for every other choice) filtered from the spell catalog by class and level, then wires selections into `sheet.spells` and `derived.spellSaveDC`/`derived.spellAttackBonus`.

**Tech Stack:** Python 3, Flask, pytest — no new dependencies.

## Global Constraints

- **Level 1 only**, matching every other part of this engine (`resolve.py`'s own docstring: "Phase 1 scope: single class, level 1 only"). Only 1st-level spells and cantrips are ever offered; `spell_slots_level_2` and above are always 0 at character level 1 in the bundled SRD data (verified empirically — see Task 1), so this needs no explicit gating beyond filtering spells by `level <= 1`.
- **8 of the SRD's 12 classes have any spellcasting at all**: Bard, Cleric, Druid, Paladin, Ranger, Sorcerer, Warlock, Wizard. Of those, **Paladin and Ranger have zero spell slots and zero cantrips at level 1** (verified empirically against `5e-SRD-Levels.json` — this matches real 5e rules, where both classes' spellcasting starts at level 2). For those two classes, no spell `Choice`s are generated and `sheet.spells`/`derived.spellSaveDC`/`derived.spellAttackBonus` are all `None` — there is nothing to cast yet, so nothing is shown, the same "genuinely nothing to choose" pattern already used elsewhere (e.g. Fighter's equipment).
- **Two spell-count mechanics, both real 5e rules, collapsed into one uniform formula per class:**
  - **Known casters** (Bard, Sorcerer, Warlock — Ranger too, but it's 0 at level 1): the SRD's own `5e-SRD-Levels.json` gives an explicit `spells_known` integer per level. Use it directly.
  - **Prepared casters** (Cleric, Druid): the SRD data has **no** `spells_known` field for these — by RAW, they prepare `ability modifier + class level` spells each day (minimum 1) from their *entire* class spell list, with no separate "known" restriction. This formula is 5e core-rules text, not present as a number anywhere in the bundled JSON — it must be hardcoded in code, the same way the Point Buy cost table and Standard Array values were hardcoded reference data in earlier phases.
  - **Wizard is a documented simplification**: by RAW, a Wizard has a *spellbook* (6 fixed 1st-level spells at level 1, prose-only in the SRD JSON, not a number anywhere in the data) and then *prepares* a subset of it daily (`INT modifier + level`, same formula as Cleric/Druid). This plan does **not** model the separate spellbook-vs-daily-prep two-step. Wizard is treated exactly like Cleric/Druid: one `Choice` for `INT modifier + level (min 1)` spells "known", full stop. This is a real, deliberate departure from RAW (a Wizard's actual spellbook capacity can differ from what they prepare on a given day), scoped this way because Phase 2 builds a character *sheet*, not a day-to-day spell-prep simulator — revisit only if a future phase's requirements demand the distinction.
  - Cantrips are always "known" outright (never prepared) for every class that has any — this is uniform across all 6 SRD classes with a `cantrips_known` field, so no per-class branching is needed there.
- **No subclass-granted spells** (e.g. a Cleric domain's "always prepared" spells). Subclass selection itself is already out of scope per `resolve.py`'s existing docstring ("subclass selection is out of scope... `subclassId` is read but never trusted to gate a feature choice unless it actually matches") — spells inherit that same boundary.
- **No ritual casting, no spellcasting focus/component tracking, no multiclass spell-slot table.** These are real 5e mechanics but out of scope for a level-1 single-class sheet; nothing in this plan references them.
- Every new function is pure and independently testable against hand-computed SRD values, matching `engine/derived.py`'s and `engine/equipment.py`'s existing style (no I/O, no catalog access inside the pure math functions).
- Follow the existing choice-envelope pattern exactly: a spell `Choice`'s options are built by calling the *existing* `catalog.choices.build_choice_template(envelope, cid, source, label, description=...)` with a **synthesized** envelope shaped exactly like every other "choose N of..." envelope in this codebase (`{"choose": N, "from": {"option_set_type": "options_array", "options": [{"option_type": "reference", "item": {"index": ..., "name": ...}}, ...]}}`). Do not add new branches to `build_choice_options` — the existing `options_array`/`reference` handling already produces exactly the right `{id, label}` shape when fed spell data this way.

---

### Task 1: Catalog spell index + empirical data verification

**Files:**
- Modify: `server/catalog/loader.py`
- Test: `server/tests/test_loader.py`

**Interfaces:**
- Produces: `Catalog.spells: dict[str, dict]` — every SRD spell indexed by its `index` field (319 entries as of the bundled data), and `Catalog.level_row(class_id, level)` (already exists, unchanged) as the source of per-class-level spellcasting stats.

- [ ] **Step 1: Add the spells index to `Catalog`**

In `server/catalog/loader.py`, add a field to the `Catalog` dataclass:

```python
    spells: dict[str, dict] = field(default_factory=dict)
```

Add it to `load()`'s constructor call:

```python
        spells=_index_by(_load("5e-SRD-Spells.json")),
```

- [ ] **Step 2: Write the loader test**

In `server/tests/test_loader.py`, follow the existing test style for other indexed collections (open the file and match its pattern for e.g. `catalog.items` or `catalog.backgrounds`) and add:

```python
def test_spells_indexed_by_index():
    catalog = load_catalog()
    assert len(catalog.spells) == 319
    assert catalog.spells["fireball"]["name"] == "Fireball"
    assert catalog.spells["fireball"]["level"] == 3
```

- [ ] **Step 3: Run the test**

Run: `cd server && .venv/bin/python -m pytest tests/test_loader.py -v`
Expected: PASS, including the new test.

- [ ] **Step 4: Commit**

```bash
git add server/catalog/loader.py server/tests/test_loader.py
git commit -m "feat: index SRD spells into the catalog"
```

---

### Task 2: Pure spellcasting math

**Files:**
- Create: `server/engine/spells.py`
- Test: `server/tests/test_engine_spells.py`

**Interfaces:**
- Consumes: nothing from earlier tasks except the general shape of `5e-SRD-Levels.json` level rows (each has a `"spellcasting"` dict with integer keys like `cantrips_known`, `spells_known`, `spell_slots_level_1`, present only for classes that have that stat at that level — e.g. Cleric's level-1 row has `cantrips_known` and `spell_slots_level_1` but no `spells_known` key at all, not even `0`).
- Produces:
  - `spellcasting_ability(cls: dict) -> str | None` — returns the class's spellcasting ability as an **uppercase** key (e.g. `"INT"`) matching `engine/derived.py`'s `ABILITIES`/modifier dict convention, or `None` if the class has no `"spellcasting"` field at all.
  - `known_spell_count(level_row: dict, ability_modifier: int, class_level: int) -> int` — the number of 1st-level-or-higher spells this class knows/prepares at this level. Returns `0` if the class has no spell slots at this level.
  - `spell_save_dc(proficiency_bonus: int, ability_modifier: int) -> int`
  - `spell_attack_bonus(proficiency_bonus: int, ability_modifier: int) -> int`

- [ ] **Step 1: Empirically verify the exact `spellcasting` dict shape for every spellcasting class's level-1 row**

Before writing any code, run this from the repo root to confirm the exact keys present (this data was already spot-checked during planning, but re-verify at implementation time in case anything drifted):

```bash
cd server && .venv/bin/python -c "
import json
levels = json.load(open('../chargen/data/srd/5e-SRD-Levels.json'))
for idx in ['bard','cleric','druid','paladin','ranger','sorcerer','warlock','wizard']:
    row = next(l for l in levels if l['class']['index']==idx and l['level']==1)
    print(idx, row.get('spellcasting'))
"
```

Expected output (already verified during planning — confirm it still matches):
```
bard {'cantrips_known': 2, 'spells_known': 4, 'spell_slots_level_1': 2, ...}
cleric {'cantrips_known': 3, 'spell_slots_level_1': 2, ...}  # no 'spells_known' key
druid {'cantrips_known': 2, 'spell_slots_level_1': 2, ...}  # no 'spells_known' key
paladin {'spell_slots_level_1': 0, ...}  # no cantrips_known, no spells_known
ranger {'spells_known': 0, 'spell_slots_level_1': 0, ...}  # spells_known present but 0
sorcerer {'cantrips_known': 4, 'spells_known': 2, 'spell_slots_level_1': 2, ...}
warlock {'cantrips_known': 2, 'spells_known': 2, 'spell_slots_level_1': 1, ...}
wizard {'cantrips_known': 3, 'spell_slots_level_1': 2, ...}  # no 'spells_known' key
```

If your output differs from this, stop and reconcile before writing code — the rest of this task's logic depends on these exact shapes.

- [ ] **Step 2: Write the failing tests**

Create `server/tests/test_engine_spells.py`:

```python
from engine.spells import (
    known_spell_count,
    spell_attack_bonus,
    spell_save_dc,
    spellcasting_ability,
)

_WIZARD = {"spellcasting": {"spellcasting_ability": {"index": "int", "name": "INT"}}}
_FIGHTER = {}

_BARD_ROW = {"spellcasting": {"cantrips_known": 2, "spells_known": 4, "spell_slots_level_1": 2}}
_CLERIC_ROW = {"spellcasting": {"cantrips_known": 3, "spell_slots_level_1": 2}}
_PALADIN_ROW = {"spellcasting": {"spell_slots_level_1": 0}}
_RANGER_ROW = {"spellcasting": {"spells_known": 0, "spell_slots_level_1": 0}}
_NO_SPELLCASTING_ROW = {}


def test_spellcasting_ability_reads_and_uppercases_the_index():
    assert spellcasting_ability(_WIZARD) == "INT"


def test_spellcasting_ability_is_none_for_a_non_caster():
    assert spellcasting_ability(_FIGHTER) is None


def test_known_caster_uses_the_explicit_spells_known_count():
    assert known_spell_count(_BARD_ROW, ability_modifier=3, class_level=1) == 4


def test_prepared_caster_uses_ability_modifier_plus_level():
    assert known_spell_count(_CLERIC_ROW, ability_modifier=3, class_level=1) == 4  # 3 + 1


def test_prepared_caster_minimum_is_one_even_with_a_negative_modifier():
    assert known_spell_count(_CLERIC_ROW, ability_modifier=-2, class_level=1) == 1  # max(1, -2+1)


def test_zero_spell_slots_means_zero_known_spells_even_with_a_spells_known_field():
    assert known_spell_count(_RANGER_ROW, ability_modifier=3, class_level=1) == 0


def test_zero_spell_slots_means_zero_known_spells_with_no_spells_known_field_either():
    assert known_spell_count(_PALADIN_ROW, ability_modifier=3, class_level=1) == 0


def test_a_class_row_with_no_spellcasting_key_at_all_returns_zero():
    assert known_spell_count(_NO_SPELLCASTING_ROW, ability_modifier=3, class_level=1) == 0


def test_spell_save_dc_is_eight_plus_prof_bonus_plus_ability_modifier():
    assert spell_save_dc(proficiency_bonus=2, ability_modifier=3) == 13


def test_spell_attack_bonus_is_prof_bonus_plus_ability_modifier():
    assert spell_attack_bonus(proficiency_bonus=2, ability_modifier=3) == 5
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_spells.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.spells'`

- [ ] **Step 4: Implement `server/engine/spells.py`**

```python
"""Pure spellcasting math for a resolved level-1 single-class character.
No I/O, no catalog access — matches engine/derived.py's and
engine/equipment.py's style. See the plan's Global Constraints for the
known-vs-prepared-caster simplification (Wizard is treated as a prepared
caster, not modeled with a separate spellbook step).
"""
from __future__ import annotations


def spellcasting_ability(cls: dict) -> str | None:
    spellcasting = cls.get("spellcasting")
    if not spellcasting:
        return None
    ability = spellcasting.get("spellcasting_ability", {}).get("index")
    return ability.upper() if ability else None


def known_spell_count(level_row: dict, ability_modifier: int, class_level: int) -> int:
    spellcasting = level_row.get("spellcasting") or {}
    if spellcasting.get("spell_slots_level_1", 0) <= 0:
        return 0
    spells_known = spellcasting.get("spells_known")
    if spells_known is not None:
        return spells_known
    return max(1, ability_modifier + class_level)


def spell_save_dc(proficiency_bonus: int, ability_modifier: int) -> int:
    return 8 + proficiency_bonus + ability_modifier


def spell_attack_bonus(proficiency_bonus: int, ability_modifier: int) -> int:
    return proficiency_bonus + ability_modifier
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_spells.py -v`
Expected: PASS, all 10 tests.

- [ ] **Step 6: Commit**

```bash
git add server/engine/spells.py server/tests/test_engine_spells.py
git commit -m "feat: add pure spellcasting math (save DC, attack bonus, known-spell count)"
```

---

### Task 3: Wire spell choices, sheet, and derived stats into `resolve()`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `Catalog.spells` (Task 1), `engine.spells.spellcasting_ability`/`known_spell_count`/`spell_save_dc`/`spell_attack_bonus` (Task 2), `catalog.choices.build_choice_template` (existing, unchanged), `catalog.level_row(cls_id, 1)` (existing, unchanged — already called once in `resolve()` for feature templates; reuse that same call rather than calling it twice).
- Produces:
  - Two new `Choice`s per spellcasting class (when applicable): `class:<cls_id>:1:spells-cantrips` (label `"Cantrips Known"`) and `class:<cls_id>:1:spells-known` (label `"Spells Known"` if the class has an explicit `spells_known` field, else `"Prepared Spells"` — Cleric/Druid/Wizard get "Prepared Spells", Bard/Sorcerer/Warlock get "Spells Known").
  - `sheet["spells"]`: `{"cantrips": [{"id", "name", "level"}], "known": [{"id", "name", "level"}]}` or `None` if the class has no spellcasting at level 1 (Fighter, Rogue, etc.) or has spellcasting but zero cantrips/slots at level 1 (Paladin, Ranger).
  - `derived["spellSaveDC"]` and `derived["spellAttackBonus"]`: integers, or `None` under the same conditions as `sheet["spells"]` being `None`.

- [ ] **Step 1: Write failing resolve() tests**

Open `server/tests/test_resolve.py` first and match its existing fixture/helper style (look for how it currently builds a minimal draft dict and calls `resolve(draft, catalog)` — reuse whatever helper or fixture pattern is already there rather than inventing a new one). Add these cases (adapt exact draft-building code to match the file's existing conventions once you've read it):

```python
def test_wizard_gets_cantrip_and_prepared_spell_choices():
    draft = {"classes": [{"classId": "wizard", "level": 1, "choices": {}}], "abilities": {"base": {"INT": 16}}}
    result = resolve(draft, catalog)
    cantrip_choice = next(c for c in result["choices"] if c["id"] == "class:wizard:1:spells-cantrips")
    assert cantrip_choice["count"] == 3
    assert cantrip_choice["label"] == "Cantrips Known"
    assert all(opt["id"] in catalog.spells for opt in cantrip_choice["options"])
    known_choice = next(c for c in result["choices"] if c["id"] == "class:wizard:1:spells-known")
    assert known_choice["count"] == 4  # INT mod +3, class level 1 -> max(1, 3+1)
    assert known_choice["label"] == "Prepared Spells"


def test_wizard_cantrip_options_are_level_zero_wizard_spells_only():
    draft = {"classes": [{"classId": "wizard", "level": 1, "choices": {}}], "abilities": {"base": {}}}
    result = resolve(draft, catalog)
    cantrip_choice = next(c for c in result["choices"] if c["id"] == "class:wizard:1:spells-cantrips")
    for opt in cantrip_choice["options"]:
        spell = catalog.spells[opt["id"]]
        assert spell["level"] == 0
        assert any(c["index"] == "wizard" for c in spell["classes"])


def test_bard_known_choice_uses_explicit_spells_known_not_a_formula():
    draft = {"classes": [{"classId": "bard", "level": 1, "choices": {}}], "abilities": {"base": {}}}
    result = resolve(draft, catalog)
    known_choice = next(c for c in result["choices"] if c["id"] == "class:bard:1:spells-known")
    assert known_choice["count"] == 4  # bard's level-1 spells_known, regardless of CHA modifier
    assert known_choice["label"] == "Spells Known"


def test_paladin_gets_no_spell_choices_at_level_1():
    draft = {"classes": [{"classId": "paladin", "level": 1, "choices": {}}], "abilities": {"base": {}}}
    result = resolve(draft, catalog)
    spell_choice_ids = [c["id"] for c in result["choices"] if "spells" in c["id"]]
    assert spell_choice_ids == []
    assert result["sheet"]["spells"] is None
    assert result["derived"]["spellSaveDC"] is None
    assert result["derived"]["spellAttackBonus"] is None


def test_fighter_has_no_spell_choices_or_derived_spell_stats():
    draft = {"classes": [{"classId": "fighter", "level": 1, "choices": {}}], "abilities": {"base": {}}}
    result = resolve(draft, catalog)
    spell_choice_ids = [c["id"] for c in result["choices"] if "spells" in c["id"]]
    assert spell_choice_ids == []
    assert result["sheet"]["spells"] is None
    assert result["derived"]["spellSaveDC"] is None


def test_selected_cantrips_and_known_spells_appear_in_the_sheet():
    # Fireball is level 3, so it's never offered at level 1 — look up real
    # level-appropriate wizard spells/cantrips programmatically rather than
    # hardcoding names you haven't verified against the loaded data.
    cantrip_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 0 and any(c["index"] == "wizard" for c in s["classes"])
    )
    spell_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 1 and any(c["index"] == "wizard" for c in s["classes"])
    )
    draft = {
        "classes": [{
            "classId": "wizard", "level": 1,
            "choices": {
                "class:wizard:1:spells-cantrips": [cantrip_id],
                "class:wizard:1:spells-known": [spell_id],
            },
        }],
        "abilities": {"base": {"INT": 16}},
    }
    result = resolve(draft, catalog)
    assert result["sheet"]["spells"]["cantrips"][0]["id"] == cantrip_id
    assert result["sheet"]["spells"]["known"][0]["id"] == spell_id


def test_derived_spell_save_dc_and_attack_bonus_use_the_spellcasting_ability():
    draft = {"classes": [{"classId": "wizard", "level": 1, "choices": {}}], "abilities": {"base": {"INT": 16}}}
    result = resolve(draft, catalog)
    # INT 16 -> +3 modifier, prof bonus 2 at level 1
    assert result["derived"]["spellSaveDC"] == 13  # 8 + 2 + 3
    assert result["derived"]["spellAttackBonus"] == 5  # 2 + 3
```

Adjust every draft dict's exact shape (in particular the `abilities`/`classes` structure) to match whatever `resolve()` actually expects **as already used by the surrounding tests in this same file** — read a handful of existing `test_resolve.py` cases first and mirror their draft-building convention exactly; do not guess at the shape independently, since the two must stay consistent within one file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k spell`
Expected: FAIL (no spell choices generated yet, `sheet["spells"]` key doesn't exist, `derived["spellSaveDC"]` key doesn't exist).

- [ ] **Step 3: Implement `_spell_choice_templates` in `server/engine/resolve.py`**

Add near the other `_*_choice_templates` helper functions (after `_equipment_choice_templates`), and add the import at the top of the file:

```python
from . import spells as spells_mod
```

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

- [ ] **Step 4: Wire it into `resolve()`'s choice-template assembly**

In `resolve()`, the class feature templates are built inside the existing block:

```python
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.level_row(cls_id, 1)
        if level_row:
            choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], level_row.get("features", []), subclass_id)
```

`level_row` is computed here but currently goes out of scope after this `if` block. Change it so it survives for later use (both for the new spell templates below AND for the sheet/derived section further down, which needs it too). Initialize `level_row = None` before this block (alongside the other pre-`if` declarations near the top of `resolve()`), then inside the block just assign to it (drop the `if level_row:` local redeclaration, since it's now the outer variable):

```python
    level_row = None
    ...
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.level_row(cls_id, 1)
        if level_row:
            choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], level_row.get("features", []), subclass_id)
```

The spell templates need `ability_modifier`, which requires knowing the spellcasting ability first. Add this right after `level_row` is set (still inside the `if cls and cls_id:` block, after the feature-templates line):

```python
        spell_ability = spells_mod.spellcasting_ability(cls)
        if spell_ability and level_row:
            choice_templates += _spell_choice_templates(catalog, cls, cls_id, level_row, modifiers[spell_ability])
```

This reads `modifiers`, which is computed earlier in `resolve()` (the `modifiers = derived_mod.ability_modifiers(final_scores)` line) — confirm it precedes the choice-template assembly block already (it does, per the existing code you're editing) and do not move it.

- [ ] **Step 5: Populate `sheet["spells"]` and the derived spell stats**

Near where `sheet["equipment"]` is built, add a spells section. First, gather the resolved cantrip/known choices (place this near the other `[c for c in choices if ...]` filters, e.g. right after `equipment_choices = [c for c in choices if c["source"]["kind"] == "equipment"]`):

```python
    cantrip_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:1:spells-cantrips"), None) if cls_id else None
    known_spells_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:1:spells-known"), None) if cls_id else None

    def _spell_summaries(choice: dict | None) -> list[dict]:
        if not choice:
            return []
        return [
            {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]}
            for sid in choice["selected"] if sid in catalog.spells
        ]

    spell_ability = spells_mod.spellcasting_ability(cls) if cls else None
    has_spellcasting_this_level = bool(cantrip_choice or known_spells_choice)
    spells_summary = None
    spell_save_dc = None
    spell_attack_bonus = None
    if has_spellcasting_this_level and spell_ability:
        spells_summary = {"cantrips": _spell_summaries(cantrip_choice), "known": _spell_summaries(known_spells_choice)}
        spell_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[spell_ability])
        spell_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[spell_ability])
```

Add the two new keys to the existing `derived = {...}` dict literal (alongside `"passivePerception"`):

```python
        "spellSaveDC": spell_save_dc,
        "spellAttackBonus": spell_attack_bonus,
```

Add the new key to the existing `sheet = {...}` dict literal (alongside `"equipment"`):

```python
        "spells": spells_summary,
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k spell`
Expected: PASS, all new cases.

Then run the full backend suite to confirm nothing else broke:

Run: `cd server && .venv/bin/python -m pytest -v`
Expected: PASS, previous 106 (96 + 10 from Task 2) plus the new `test_resolve.py` cases, all green.

- [ ] **Step 7: Empirically sweep every spellcasting class**

Before committing, run this quick manual check from `server/` (adapt the draft-building call to match whatever helper `test_resolve.py` actually uses) to confirm every one of the 8 spellcasting classes produces sane output — this is exactly the kind of cross-class sweep that caught real bugs in Phase 2a's equipment work:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
for cls_id in ['barbarian','bard','cleric','druid','fighter','monk','paladin','ranger','rogue','sorcerer','warlock','wizard']:
    draft = {'classes': [{'classId': cls_id, 'level': 1, 'choices': {}}], 'abilities': {'base': {}}}
    r = resolve(draft, catalog)
    spell_choices = [c['id'] for c in r['choices'] if 'spells' in c['id']]
    print(cls_id, '| spell choices:', spell_choices, '| sheet.spells:', r['sheet']['spells'], '| DC:', r['derived']['spellSaveDC'])
"
```

Confirm: the 4 non-casters (Barbarian, Fighter, Monk, Rogue) and Paladin/Ranger all show `[]`/`None`/`None`; the other 6 (Bard, Cleric, Druid, Sorcerer, Warlock, Wizard) each show 1-2 spell choice ids and non-`None` `sheet.spells`/DC. If anything doesn't match this pattern, stop and investigate before committing — don't paper over a surprise with a broader `try`/`except` or a silently-narrower filter.

- [ ] **Step 8: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "feat: wire spell choices, sheet.spells, and spell save DC/attack bonus into resolve()"
```

---

### Task 4: Export support

**Files:**
- Modify: `server/export.py`
- Test: `server/tests/test_export.py`

**Interfaces:**
- Consumes: `sheet["spells"]` (Task 3, may be `None`).
- Produces: the YAML export body includes a `spells:` section when `sheet["spells"]` is not `None`.

Read `server/export.py` first — it's short (per the file listing, ~47 lines of tests exist for it, so the source itself is likely under 40 lines). Confirm how it currently renders `sheet["equipment"]` (added in Phase 2a but — per this session's tracked follow-up chip `task_05216a5a` — actually NOT yet included in the exported YAML body; equipment is computed but invisible in the download). **Do not silently copy that same gap for spells** — this task explicitly requires `sheet["spells"]` to actually appear in the rendered YAML, unlike equipment's current state.

- [ ] **Step 1: Write the failing test**

Match `test_export.py`'s existing style (read it first) and add a case asserting that a resolution with a non-`None` `sheet["spells"]` produces YAML containing the cantrip/known spell names, and that a resolution with `sheet["spells"] is None` (e.g. a Fighter) produces YAML with no `spells:` section (or an empty one — match whatever convention the file already uses for other optional sections, e.g. how it currently handles `sheet["background"]` being `None`).

- [ ] **Step 2: Run to verify it fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_export.py -v`

- [ ] **Step 3: Implement**

Add spell rendering to `to_yaml()` following the exact pattern already used for the other optional sheet sections in that function.

- [ ] **Step 4: Run to verify it passes**

Run: `cd server && .venv/bin/python -m pytest tests/test_export.py -v`
Expected: PASS.

Then run the full suite once more: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 5: Commit**

```bash
git add server/export.py server/tests/test_export.py
git commit -m "feat: include spells in the YAML export"
```

---

## Self-Review Notes (for whoever executes this plan)

- This plan's biggest judgment call is the Wizard-as-prepared-caster simplification (Global Constraints, 3rd bullet) — it is a deliberate, documented departure from RAW, not an oversight. Don't "fix" it mid-implementation without flagging it; if a reviewer disagrees with the simplification, that's exactly the kind of plan-vs-finding conflict that goes to the human, not a silent implementer decision.
- Task 3's `level_row` variable-scoping change (Step 4) touches existing, already-shipped code (`resolve()`'s class-template block) — this is the one place this plan modifies pre-existing logic rather than purely adding new code. Be precise about it: the behavior for feature templates must be byte-for-byte unchanged, only the variable's lifetime extends.
