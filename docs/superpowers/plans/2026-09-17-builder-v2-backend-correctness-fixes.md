# Backend Correctness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five real, independently-diagnosed correctness bugs in `resolve()`, all discovered as follow-up findings from earlier phases' final reviews and spun off as separate work rather than blocking those phases. None of these require new design — each has a concrete, data-grounded fix already identified.

**Architecture:** All five fixes live in or near `server/engine/resolve.py`. Three are narrow, independent logic corrections (species languages, species proficiencies, selection deduplication). One (Half-Elf's ability-score choice) is a genuine new mechanic — a species-sourced ability bonus Choice, following the exact pattern Phase 3a's ASI already established (compute the choice's effect on final ability scores BEFORE `modifiers` is derived, since everything downstream depends on it). One (equipment-envelope-drop signaling) populates the `warnings` list, which has existed in the `Resolution` shape since Phase 0 but has never once been written to.

**Tech Stack:** Same as every prior phase — Python/Flask backend, no new dependencies.

## Global Constraints

- **Every fix must be verified against real bundled SRD data, not hand-typed fixtures alone** — this project's history has repeatedly found real bugs only a full-class/full-species empirical sweep catches. Each task below includes the specific empirical check to run.
- **Level 1 and every existing Phase 1/2/3a test must remain passing.** These are correctness fixes to code paths that were previously silently wrong, not behavior changes to anything currently correct — no existing test should need to change its EXPECTED VALUE because of this plan (a test might need a new assertion added, but an existing passing assertion changing from one value to another is a signal something is wrong with the fix, not the old test).
- **No new hardcoded reference tables where the bundled data already has the answer structurally.** Verified empirically while writing this plan: SRD traits already carry a `proficiencies` field (e.g. Elf's "Keen Senses" trait has `"proficiencies": [{"index": "skill-perception", ...}]`) — species-granted proficiencies are a pure data read, not a table like `SKILL_ABILITY`/`SUBCLASS_UNLOCK_LEVEL` needed to be.
- **Half-Elf is the only race/subrace in the bundled data with `ability_bonus_options`** (verified by scanning every race and subrace in `5e-SRD-Races.json`/`5e-SRD-Subraces.json`) — but the fix must be written generically (reading whichever of race/subrace has the field, matching the existing code's already-generic pattern for `ability_bonus_options`'s sibling checks), not hardcoded to the string `"half-elf"`.

---

### Task 1: Species-chosen languages reach the sheet

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `sheet.proficiencies.languages` now includes species-sourced language choices (e.g. a Human's or Half-Elf's bonus-language pick), not just background-sourced ones.

- [ ] **Step 1: Empirically confirm the bug**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'species': {'id': 'human', 'choices': {'species:human:languages': ['draconic']}},
}
result = resolve(draft, catalog)
langs = result['sheet']['proficiencies']['languages']
print('languages:', langs)
assert 'draconic' not in langs, 'if this fails, the bug is already fixed'
print('confirmed: draconic is missing despite being a valid, resolved choice')
"
```

- [ ] **Step 2: Write a failing test**

Open `server/tests/test_resolve.py` and find the existing `_fighter_acolyte_human_draft` helper's conventions. Add:

```python
def test_species_chosen_languages_appear_on_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "human", "choices": {"species:human:languages": ["draconic"]}},
    )
    resolution = resolve(draft, catalog)
    assert "draconic" in resolution["sheet"]["proficiencies"]["languages"]


def test_background_chosen_languages_still_appear_no_regression(catalog):
    # Acolyte's own language choice — confirm this plan's fix doesn't
    # accidentally drop background-sourced languages while adding
    # species-sourced ones.
    draft = _fighter_acolyte_human_draft(
        background={"id": "acolyte", "choices": {"background:acolyte:languages": ["celestial", "infernal"]}},
    )
    resolution = resolve(draft, catalog)
    languages = resolution["sheet"]["proficiencies"]["languages"]
    assert "celestial" in languages and "infernal" in languages
```

(Verify the exact choice id strings — `species:human:languages`, `background:acolyte:languages` — against the real `_species_choice_templates`/`_background_choice_templates` functions in `resolve.py` before trusting these; adjust if the real ids differ.)

- [ ] **Step 3: Run to verify the new test fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k species_chosen_languages`
Expected: FAIL.

- [ ] **Step 4: Implement**

Find:

```python
    chosen_languages = [s for c in choices if c["source"]["kind"] == "background" for s in c["selected"]]
```

Replace with:

```python
    chosen_languages = [
        s for c in choices
        if c["source"]["kind"] in ("background", "species") and c["id"].endswith(":languages")
        for s in c["selected"]
    ]
```

The `c["id"].endswith(":languages")` guard matters: `source.kind == "species"` also covers subtrait choices (e.g. a Dragonborn's draconic-ancestry pick) which are NOT languages and must not be swept into this list — read `_species_choice_templates` first to confirm every species-sourced Choice id that legitimately ends in `:languages` is a real language choice (both the base bonus-language envelope `species:{race_id}:languages` and the subspecies one `species:{race_id}:subspecies:{id}:languages`), and that no non-language species choice could ever coincidentally end that way.

- [ ] **Step 5: Run to verify it passes**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "chosen_languages"`
Expected: PASS, both new cases.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all 219 existing plus your 2 new, all green.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: include species-chosen languages on the resolved sheet

chosen_languages only ever filtered on source.kind == "background" —
a species-sourced bonus-language pick (Human, Half-Elf, and any
subspecies with its own language envelope) was fully resolved and
validated by the choice-resolution pipeline, then silently dropped when
building sheet.proficiencies.languages. Widened to also include
source.kind == "species" choices whose id ends in ":languages" (guarding
against sweeping in a non-language species choice like a subtrait pick).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Species-granted (trait) proficiencies are applied

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog.traits` (already loaded).
- Produces: `sheet.proficiencies.skills` (and thus `derived.skills`' proficiency bonus application) now includes skill proficiencies a race/subrace grants automatically via a trait (e.g. Elf's Keen Senses → Perception), not just class/background-sourced ones.

- [ ] **Step 1: Empirically confirm the bug and the fix's data source**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'classes': [{'classId': 'rogue', 'level': 1, 'choices': {}}],
    'species': {'id': 'elf', 'choices': {}},
}
result = resolve(draft, catalog)
skills = result['sheet']['proficiencies']['skills']
print('skills:', skills)
assert 'skill-perception' not in skills, 'if this fails, the bug is already fixed'
print('confirmed: Elf does not automatically get Perception proficiency from Keen Senses')

keen = catalog.traits['keen-senses']
print('keen-senses proficiencies field:', keen.get('proficiencies'))
"
```

Confirm the trait's own `proficiencies` field is a list of `{"index": "skill-...", ...}` dicts — the same shape `bg.get("starting_proficiencies")` already uses, which `resolve()` already knows how to filter for `skill-` prefixed entries.

- [ ] **Step 2: Write a failing test**

```python
def test_species_trait_proficiencies_are_applied(catalog):
    # Elf's Keen Senses trait grants Perception proficiency automatically,
    # with no choice involved.
    draft = _fighter_acolyte_human_draft(species={"id": "elf", "choices": {}})
    resolution = resolve(draft, catalog)
    assert "skill-perception" in resolution["sheet"]["proficiencies"]["skills"]


def test_a_race_with_no_automatic_skill_grant_gets_none(catalog):
    # Human has no trait granting an automatic skill proficiency — confirm
    # this fix doesn't spuriously grant one. With the fixture's default
    # empty choices, Fighter's own skill-proficiency choice is left
    # unresolved (pending) and Acolyte's own two FIXED skills (Insight,
    # Religion — background.starting_proficiencies, not a choice) are the
    # only ones that resolve — confirmed empirically while writing this
    # plan. Nothing should be attributable to Human.
    draft = _fighter_acolyte_human_draft()  # already uses Human
    resolution = resolve(draft, catalog)
    assert set(resolution["sheet"]["proficiencies"]["skills"]) == {"skill-insight", "skill-religion"}
```

- [ ] **Step 3: Run to verify the new test fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k species_trait_proficiencies`
Expected: FAIL.

- [ ] **Step 4: Implement**

Find:

```python
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
```

Replace with:

```python
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            proficient_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
```

Note this reads `race.get("traits")`/`subrace.get("racial_traits")` the same way `_species_choice_templates` already does — you're not inventing a new way to enumerate a race's traits, just adding a second pass over the same list for a different purpose (fixed proficiency grants instead of choice-envelope detection).

- [ ] **Step 5: Run to verify it passes**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "trait_proficiencies or automatic_skill_grant"`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 6: Empirically sweep all 9 SRD races + subraces**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
for race_id in catalog.races:
    draft = {'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}], 'species': {'id': race_id, 'choices': {}}}
    r = resolve(draft, catalog)
    skills = r['sheet']['proficiencies']['skills']
    print(race_id, '->', skills)
"
```

Confirm every race's output matches its real SRD traits (Elf → Perception; Half-Orc → none automatic at the race level in SRD, though check; etc.) — spot-check 2-3 against the actual trait data in `5e-SRD-Traits.json` rather than assuming the sweep output is correct just because it ran without crashing.

- [ ] **Step 7: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: apply automatic skill proficiencies a race/subrace grants via a trait

proficient_skills only ever read from class choice selections and
background.starting_proficiencies — never from the selected species,
even though a trait like Elf's Keen Senses grants Perception outright
with no choice involved, and the bundled SRD data already carries this
as a structured `proficiencies` field on the trait itself (the same
shape backgrounds already use). Pure data read, no new reference table
needed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Half-Elf's ability-score choice — from unblockable problem to a real Choice

**Files:**
- Modify: `server/catalog/choices.py`
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_choices.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: `build_choice_options` now handles `option_type == "ability_bonus"` (Half-Elf's `ability_bonus_options` envelope shape). `resolve()` builds a real Choice for it, applies the player's validated selection to `species_bonuses` BEFORE `final_scores`/`modifiers` are computed (mirroring exactly how Phase 3a's ASI progression is computed before `modifiers`, for the same reason — everything downstream depends on the final scores). The old `species-ability-choice-unsupported` **problem** (which permanently blocked export for any Half-Elf character, with no UI able to resolve it) is removed entirely for the case this task now handles.

**Empirically confirmed data shape** (verified while writing this plan): Half-Elf's `ability_bonus_options` is `{"choose": 2, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": [{"option_type": "ability_bonus", "ability_score": {"index": "str", "name": "STR", ...}, "bonus": 1}, ...]}}` — 5 options (every ability except CHA, which Half-Elf already gets fixed +2 elsewhere), each granting `bonus` (always `1` in the bundled data) to one ability. No other race or subrace in the bundled data has this field — verified by scanning all of `5e-SRD-Races.json`/`5e-SRD-Subraces.json` — but write the fix generically (don't hardcode "half-elf").

- [ ] **Step 1: Write failing tests for the catalog-layer change**

Open `server/tests/test_choices.py` and read its existing `build_choice_options`/`_option_label` test conventions. Add:

```python
def test_ability_bonus_option_type_produces_a_readable_label_and_stable_id():
    from_field = {
        "option_set_type": "options_array",
        "options": [
            {"option_type": "ability_bonus", "ability_score": {"index": "str", "name": "STR"}, "bonus": 1},
            {"option_type": "ability_bonus", "ability_score": {"index": "dex", "name": "DEX"}, "bonus": 1},
        ],
    }
    options = build_choice_options(from_field)
    assert options is not None
    assert options[0] == {"id": "str", "label": "STR +1"}
    assert options[1] == {"id": "dex", "label": "DEX +1"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_choices.py -v -k ability_bonus`
Expected: FAIL (`_option_label` returns `None` for `option_type == "ability_bonus"`, so the option is silently dropped — confirm the test fails with an empty/wrong list, not a crash).

- [ ] **Step 3: Implement the catalog-layer change**

In `server/catalog/choices.py`, find `_option_label`:

```python
def _option_label(option: dict) -> str | None:
    option_type = option.get("option_type")
    if option_type == "reference":
        return option["item"]["name"]
    if option_type == "counted_reference":
        return option["of"]["name"]
    if option_type == "string":
        return option["string"]
    return None  # score_prerequisite, multiple, etc. — not used by any Phase 1 choice
```

Add a branch:

```python
def _option_label(option: dict) -> str | None:
    option_type = option.get("option_type")
    if option_type == "reference":
        return option["item"]["name"]
    if option_type == "counted_reference":
        return option["of"]["name"]
    if option_type == "string":
        return option["string"]
    if option_type == "ability_bonus":
        return f"{option['ability_score']['name']} +{option.get('bonus', 1)}"
    return None  # score_prerequisite, multiple, etc. — not used by any Phase 1 choice
```

Find the main loop in `build_choice_options` (the `options_array` branch):

```python
        for opt in from_field.get("options", []):
            if opt.get("option_type") == "multiple":
                bundle = _bundle_label_and_id(opt.get("items", []))
                if bundle is None:
                    continue
                label, option_id = bundle
                options.append({"id": option_id, "label": label})
                continue
            label = _option_label(opt)
            if label is None:
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
```

The fallback `label.lower().replace(" ", "-")` would turn "STR +1" into the ugly, fragile id `"str-+1"` — add an explicit id derivation for this option type instead, right after computing `label`:

```python
            label = _option_label(opt)
            if label is None:
                continue
            if opt.get("option_type") == "ability_bonus":
                option_id = opt["ability_score"]["index"]
                options.append({"id": option_id, "label": label})
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
```

- [ ] **Step 4: Run to verify the catalog-layer tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_choices.py -v`
Expected: PASS, all cases including the new one.

- [ ] **Step 5: Write failing tests for the resolve()-layer change**

Add to `server/tests/test_resolve.py`:

```python
def test_half_elf_ability_bonus_choice_no_longer_blocks_export(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "half-elf", "choices": {"species:half-elf:ability-bonus": ["str", "dex"]}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "species-ability-choice-unsupported" for p in resolution["problems"])


def test_half_elf_selected_ability_bonuses_are_applied(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "half-elf", "choices": {"species:half-elf:ability-bonus": ["str", "dex"]}},
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    scores = resolution["sheet"]["abilities"]
    assert scores["STR"] == 15  # 14 base + 1 from the ability-bonus choice
    assert scores["DEX"] == 13  # 12 base + 1
    assert scores["CHA"] == 10  # 8 base + 2 fixed Half-Elf bonus (unrelated to this choice, unaffected)


def test_half_elf_choice_is_pending_when_unresolved(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "half-elf", "choices": {}})
    resolution = resolve(draft, catalog)
    choice = next(c for c in resolution["choices"] if c["id"] == "species:half-elf:ability-bonus")
    assert choice["status"] == "pending"
    assert choice["count"] == 2
```

(Verify the exact choice id `species:half-elf:ability-bonus` matches whatever you actually implement in Step 6 below — pick a clear, conventional id following this codebase's existing `species:{race_id}:{suffix}` pattern, and keep the test's id in sync with it.)

- [ ] **Step 6: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k half_elf`
Expected: FAIL.

- [ ] **Step 7: Implement the resolve()-layer change**

This mirrors Phase 3a's ASI progression pattern: the choice's effect on ability scores must be computed BEFORE `modifiers` is derived. Read the current `resolve()` around where `species_bonuses`/`final_scores` are computed (the block starting near `species_bonuses = _species_ability_bonuses(race, subrace)`) — this is BEFORE `choice_templates`/`choices` are built, so you need a small early helper, not a change to the main choice-application loop.

Add a new function near `_species_ability_bonuses`:

```python
def _species_ability_bonus_choice_template(race: dict | None, subrace: dict | None, race_id: str | None) -> dict | None:
    """Half-Elf's ability_bonus_options (the only race/subrace in the
    bundled data with this field) needs a real Choice — this builds its
    template. Race is checked before subrace since ability_bonus_options
    could in principle appear on either (only race does in the bundled
    data, but this stays generic rather than hardcoding "half-elf")."""
    for src in (race, subrace):
        if not src or not src.get("ability_bonus_options"):
            continue
        envelope = src["ability_bonus_options"]
        cid = f"species:{race_id}:ability-bonus"
        source = {"kind": "species", "id": race_id, "label": race["name"] if race else ""}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by 1."
        return build_choice_template(envelope, cid, source, "Ability Score Increase", description=description)
    return None
```

In `resolve()`, find the ability-score-choice-unsupported problem block:

```python
    if race and race.get("ability_bonus_options"):
        problems.append({
            "id": "species-ability-choice-unsupported",
            "message": f"{race['name']}'s ability-score choice isn't supported yet — no bonus from it was applied.",
        })
    if subrace and subrace.get("ability_bonus_options"):
        problems.append({
            "id": "species-ability-choice-unsupported",
            "message": f"{subrace['name']}'s ability-score choice isn't supported yet — no bonus from it was applied.",
        })
```

Replace it with a call to the new helper, applying the player's already-submitted species choices (read directly from `species.get("choices")`, the same early-access pattern Phase 3a used for `class_choices` before ASI):

```python
    species_ability_choice_tpl = _species_ability_bonus_choice_template(race, subrace, race_id)
    if species_ability_choice_tpl:
        species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
        valid_ability_ids = {o["id"] for o in species_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = species_choices_raw.get(species_ability_choice_tpl["id"]) or []
        selected_abilities = [s for s in raw_selected if isinstance(s, str) and s in valid_ability_ids][: species_ability_choice_tpl["count"]]
        for ab_id in selected_abilities:
            ab_key = ab_id.upper()
            species_bonuses[ab_key] = species_bonuses.get(ab_key, 0) + 1  # bundled data's `bonus` is always 1; if a future data source varies this, look it up from the option instead of hardcoding 1 here
```

This must run AFTER `species_bonuses = _species_ability_bonuses(race, subrace)` (the fixed bonuses) and BEFORE the `final_scores` loop that reads `species_bonuses`.

Later, where `choice_templates` are assembled (the `if race and race_id: choice_templates += _species_choice_templates(...)` block), add the new template to the list too — so it shows up as a normal Choice in the response (for UI rendering and pending/resolved status), using the SAME `species_ability_choice_tpl` object already built above rather than rebuilding it:

```python
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)
        if species_ability_choice_tpl:
            choice_templates.append(species_ability_choice_tpl)
```

Since this template is now included in `choice_templates`, it will flow through the existing main selection-resolution loop (`for tpl in choice_templates: ...`) exactly like every other choice — producing a `resolved`/`pending` status choice in the response, with its `selected` field independently re-derived by that generic loop (using the SAME `all_selections` dict, which already includes `species.get("choices")` — confirm this is really already the case by reading the `all_selections.update(species.get("choices") or {})` line). This means the choice appears TWICE in terms of computation (once in the early pass to compute `species_bonuses`, once in the generic loop for display) — that's expected and fine, not a bug, since both reads are idempotent and must agree (they read the same underlying selection data); do not try to "optimize" this into a single pass, since the early pass exists specifically to solve the ordering problem the same way Phase 3a's ASI progression does.

- [ ] **Step 8: Run to verify the resolve()-layer tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k half_elf`
Expected: PASS, all 3 cases.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 9: Empirically verify a complete Half-Elf export**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
catalog = load()
draft = {
    'name': 'Half-Elf Test',
    'classes': [{'classId': 'bard', 'level': 1, 'choices': {}}],
    'species': {'id': 'half-elf', 'choices': {'species:half-elf:ability-bonus': ['str', 'dex']}},
    'abilities': {'base': {'STR': 14, 'DEX': 12, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 15}},
}
result = resolve(draft, catalog)
print('problems:', result['problems'])
print(to_yaml(result))
"
```

Confirm `problems` is empty (or at least contains nothing about the ability-score choice) and the printed YAML shows STR 15, DEX 13, CHA 17 (15 base + 2 fixed). If a Half-Elf character with a fully-resolved ability-bonus choice STILL can't export, stop and investigate before committing — that would mean this task didn't actually fix the dead-end it set out to fix.

- [ ] **Step 10: Commit**

```bash
git add server/catalog/choices.py server/engine/resolve.py server/tests/test_choices.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: Half-Elf's ability-score choice — from unblockable problem to a real Choice

Half-Elf (the only race/subrace with ability_bonus_options in the
bundled data) previously produced a permanent "species-ability-choice-
unsupported" PROBLEM with no UI able to resolve it — every Half-Elf
character was unexportable, full stop. build_choice_options gains a
branch for the "ability_bonus" option type; resolve() builds a real
Choice for the envelope and applies the validated selection to
species_bonuses before modifiers is computed, mirroring Phase 3a's ASI
progression pattern for the same reason (everything downstream depends
on final ability scores).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Deduplicate repeated choice selections

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: a choice selection listing the same option id multiple times (e.g. `["fire-bolt", "fire-bolt"]` for a 1-count choice) now resolves to a single occurrence, not a duplicated one, and doesn't spuriously trigger the over-selection problem.

- [ ] **Step 1: Empirically confirm the bug**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'classes': [{'classId': 'wizard', 'level': 1, 'choices': {
        'class:wizard:spells-cantrips': ['fire-bolt', 'fire-bolt', 'fire-bolt'],
    }}],
    'abilities': {'base': {'INT': 16}},
}
result = resolve(draft, catalog)
cantrip_choice = next(c for c in result['choices'] if c['id'] == 'class:wizard:spells-cantrips')
print('selected:', cantrip_choice['selected'])
print('status:', cantrip_choice['status'])
print('problems:', result['problems'])
"
```

Confirm the output currently shows `['fire-bolt', 'fire-bolt', 'fire-bolt']` in `selected` (or truncated to `tpl['count']` copies if count is smaller — either way, a real duplicate persisting) rather than a single `'fire-bolt'`.

- [ ] **Step 2: Write failing tests**

Add to `server/tests/test_resolve.py`:

```python
def test_duplicate_selection_within_count_resolves_to_one_and_stays_resolved(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 1, "choices": {
            "class:wizard:spells-cantrips": ["fire-bolt", "fire-bolt", "fire-bolt"],
        }}],
        abilities={"method": "manual", "base": {"INT": 16, "STR": 10, "DEX": 10, "CON": 10, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    cantrip_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-cantrips")
    # cantrips_known at level 1 for a 16 INT Wizard is 3 — submit only
    # duplicates of one spell, confirm dedup happens BEFORE the
    # over-selection check (3 copies of 1 spell should NOT satisfy a
    # count-3 choice by padding with duplicates, nor should it spuriously
    # report over-selection — it should show 1 unique selection, pending).
    assert cantrip_choice["selected"] == ["fire-bolt"]
    assert cantrip_choice["status"] == "pending"
    assert not any(p["id"].startswith("over-selected") for p in resolution["problems"])


def test_duplicate_selection_does_not_trigger_a_spurious_over_selection_problem(catalog):
    # Fighter's prof-choice-0 has count=2 and "skill-athletics" is one of
    # its 8 valid options (confirmed empirically while writing this plan)
    # — 2 duplicate copies of 1 valid skill should dedupe to 1 unique
    # selection (pending, not over-selected), not silently count as if 2
    # different skills had been chosen.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 1, "choices": {
            "class:fighter:1:prof-choice-0": ["skill-athletics", "skill-athletics"],
        }}],
    )
    resolution = resolve(draft, catalog)
    prof_choice = next(c for c in resolution["choices"] if c["id"] == "class:fighter:1:prof-choice-0")
    assert prof_choice["selected"] == ["skill-athletics"]
    assert prof_choice["status"] == "pending"
    assert not any(p["id"] == "over-selected-class:fighter:1:prof-choice-0" for p in resolution["problems"])
```

- [ ] **Step 3: Run to verify these fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k duplicate_selection`
Expected: FAIL.

- [ ] **Step 4: Implement**

Find the main choice-resolution loop:

```python
    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        selected = [s for s in raw_selected if isinstance(s, str) and s in valid_ids]
        if len(selected) > tpl["count"]:
```

Replace the `selected` line to deduplicate while preserving first-occurrence order, BEFORE the over-selection check:

```python
    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        filtered = [s for s in raw_selected if isinstance(s, str) and s in valid_ids]
        selected = list(dict.fromkeys(filtered))  # dedupe, preserve first-occurrence order
        if len(selected) > tpl["count"]:
```

`dict.fromkeys(filtered)` is the standard, idiomatic Python way to deduplicate a list while preserving order (dict keys are insertion-ordered since Python 3.7) — no need for an explicit seen-set loop.

- [ ] **Step 5: Run to verify these pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k duplicate_selection`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect everything green. Pay particular attention to any EXISTING test that might have relied on the old (buggy) duplication behavior — if one breaks, read it carefully: if it was asserting the bug's own behavior, that test itself needs updating (not this fix); if it reveals a real edge case this fix handles differently than intended, stop and investigate.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: deduplicate repeated choice selections before applying them

A selection list containing the same valid option id more than once
(e.g. picking "Fire Bolt" three times for one cantrip choice) previously
resolved with the duplicate intact, appearing multiple times wherever
that choice's `selected` list feeds into the sheet — this is a generic
engine bug, not specific to any one choice type, first surfaced by
Phase 2c's final review but deferred as a cross-cutting fix. Dedup now
happens before the over-selection check via dict.fromkeys(), so 3
copies of one valid option for a count-1 choice correctly resolves to a
single selection rather than spuriously reporting over-selection.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Signal when an entire equipment choice envelope is dropped

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `resolution["warnings"]` (populated for the first time ever — the list has existed in the `Resolution` shape since Phase 0 but nothing has ever written to it) gains an entry when an entire starting-equipment envelope can't be represented in the flat Choice model (e.g. a nested `choice`-within-`choice` shape), as opposed to `_equipment_choice_templates`'s EXISTING per-choice note for when only SOME options within a surviving choice were dropped.

- [ ] **Step 1: Empirically find a class with a genuinely dropped equipment envelope**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
catalog = load()
for cls_id, cls in catalog.classes.items():
    envelopes = cls.get('starting_equipment_options', [])
    from catalog.choices import build_choice_template
    survived = 0
    for i, env in enumerate(envelopes):
        cid = f'class:{cls_id}:1:equipment-choice-{i}'
        tpl = build_choice_template(env, cid, {'kind':'equipment','id':cls_id,'label':cls['name'],'level':1}, 'Starting Equipment')
        if tpl:
            survived += 1
    if survived < len(envelopes):
        print(cls_id, 'total:', len(envelopes), 'survived:', survived)
"
```

This reproduces the exact same envelope-resolution logic `_equipment_choice_templates` already uses (calling `build_choice_template` directly per envelope) to find which classes have a genuinely-dropped envelope (not just a partially-resolved one, which already gets a description note).

**Already run while writing this plan — real output, so Step 2 below uses it directly (no need to re-run unless you want to double-check):**

```
barbarian total: 2 survived: 2
bard total: 3 survived: 3
cleric total: 5 survived: 4
druid total: 3 survived: 2
fighter total: 4 survived: 3
monk total: 2 survived: 2
paladin total: 4 survived: 2
ranger total: 3 survived: 3
rogue total: 3 survived: 3
sorcerer total: 3 survived: 3
warlock total: 4 survived: 3
wizard total: 3 survived: 3
```

Paladin has the largest gap (4 total, 2 survived → 2 dropped) — use it for the "dropped" case. Wizard is fully clean (3 total, 3 survived → 0 dropped) — use it for the "no warning" case. Note Fighter itself has 1 dropped (4 total, 3 survived, matching the Phase 2a-era finding referenced in the module's existing tests) — it is NOT a clean example, so don't use `_fighter_acolyte_human_draft`'s default class for the negative case; override `classes` to Wizard explicitly.

- [ ] **Step 2: Write a failing test**

```python
def test_a_fully_dropped_equipment_envelope_produces_a_warning(catalog):
    # Paladin has 4 starting-equipment envelopes in the bundled SRD data,
    # of which only 2 survive build_choice_template (confirmed empirically
    # while writing this plan) — the other 2 are genuinely dropped.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "paladin", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any("equipment" in w["id"] for w in resolution["warnings"])


def test_a_class_with_no_dropped_envelopes_has_no_such_warning(catalog):
    # Wizard has 3 starting-equipment envelopes, all 3 survive
    # build_choice_template (confirmed empirically while writing this
    # plan) — zero dropped, so no equipment warning should appear.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "wizard", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert not any("equipment" in w["id"] for w in resolution["warnings"])
```

- [ ] **Step 3: Run to verify the new test fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k dropped_equipment_envelope`
Expected: FAIL.

- [ ] **Step 4: Implement**

Find `_equipment_choice_templates`:

```python
def _equipment_choice_templates(entity: dict, source_kind: str, source_id: str, source_label: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if not tpl:
            continue
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (tpl["description"] + " (Note: one or more of the original options for this choice aren't available yet and have been left out.)").strip()
        templates.append(tpl)
    return templates
```

Change its return type to also report drop count, and update BOTH call sites:

```python
def _equipment_choice_templates(entity: dict, source_kind: str, source_id: str, source_label: str) -> tuple[list[dict], int]:
    templates = []
    dropped_envelopes = 0
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if not tpl:
            dropped_envelopes += 1
            continue
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (tpl["description"] + " (Note: one or more of the original options for this choice aren't available yet and have been left out.)").strip()
        templates.append(tpl)
    return templates, dropped_envelopes
```

Find the two call sites:

```python
    if cls and cls_id:
        choice_templates += _equipment_choice_templates(cls, "class", cls_id, cls["name"])
    if bg and bg_id:
        choice_templates += _equipment_choice_templates(bg, "background", bg_id, bg["name"])
```

Replace with:

```python
    if cls and cls_id:
        cls_equipment_templates, cls_dropped = _equipment_choice_templates(cls, "class", cls_id, cls["name"])
        choice_templates += cls_equipment_templates
        if cls_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-class-{cls_id}",
                "message": f"{cls['name']}'s starting equipment has {cls_dropped} choice(s) that can't be shown yet and were left out.",
            })
    if bg and bg_id:
        bg_equipment_templates, bg_dropped = _equipment_choice_templates(bg, "background", bg_id, bg["name"])
        choice_templates += bg_equipment_templates
        if bg_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-background-{bg_id}",
                "message": f"{bg['name']}'s starting equipment has {bg_dropped} choice(s) that can't be shown yet and were left out.",
            })
```

`warnings` is already a `list[dict]` declared near the top of `resolve()` (alongside `problems`) — confirm it's in scope at this point in the function (it should be, since it's declared before `choice_templates` is built).

- [ ] **Step 5: Run to verify the tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k dropped_equipment_envelope`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect everything green.

- [ ] **Step 6: Sweep all 12 classes + all backgrounds**

From `server/`, re-run resolve() for every class and confirm the `warnings` list's presence/absence matches Step 1's empirical sweep exactly (same classes flagged, same drop counts) — this is your cross-check that the wiring is correct, not just that it compiles.

- [ ] **Step 7: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: warn when an entire equipment choice envelope can't be represented

_equipment_choice_templates already notes in a choice's own description
when SOME options within it were dropped (Phase 2a) — but had no signal
at all when an ENTIRE envelope resolves to nothing (a nested choice-
within-choice shape, deliberately out of scope since Phase 2a). Both
call sites now also report a warning via the previously-unused
resolution["warnings"] list, giving the eventual UI something to surface
instead of a silently shorter equipment section.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- Task 3 is the only genuinely new mechanic in this plan (the other four are pure bug fixes to existing logic) — it deliberately mirrors Phase 3a's ASI-progression pattern (compute a choice's effect on ability scores before `modifiers`, in a small early pass, then ALSO include the same template in the normal `choice_templates` list for UI display) rather than inventing a different approach. If an implementer is tempted to simplify this into a single pass, re-read Task 3's Step 7 explanation of why the double-computation is intentional, not redundant.
- Task 5's Step 2 test bodies use Paladin (2 of 4 equipment envelopes dropped) and Wizard (0 of 3 dropped) — both confirmed by actually running Step 1's empirical sweep while writing this plan, not guessed.
- None of these five fixes should change any EXISTING test's expected value. If running the full suite after any task shows an existing test's assertion now failing (not a new test, an old one), stop and read that test carefully before changing it — it's more likely the fix has a real bug than that the old test was encoding the bug's own behavior, but confirm which case you're in rather than assuming.
