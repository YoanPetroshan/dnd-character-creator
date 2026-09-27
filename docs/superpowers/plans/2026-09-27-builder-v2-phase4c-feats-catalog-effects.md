# Phase 4c-i — Feats: Catalog + Granted Effects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every official feat (305 real records, already fetched via `chargen/sync.py --official` to `~/.claude/dnd/.data/official/feats.json`) is importable into a new `Catalog.feats` dict with full granted-effect fidelity — ability bonuses, proficiencies, languages, resistances/immunities/condition-immunities/senses, expertise, saving-throw proficiencies. Background-granted feats (already flowing as inert `sheet.grantedFeats` since Phase 4b) now actually APPLY their effects to the resolved sheet — this is the direct continuation of Phase 4b's own deferral. Structured prerequisites (character level, minimum ability score) are checked and surfaced as a `problems` entry when unmet, gated behind a preference toggle mirroring the existing multiclass-prerequisite pattern exactly. On a machine without official data fetched, `Catalog.feats` is simply empty and everything degrades to today's behavior (inert `grantedFeats`, no new problems) — trivially safe, since there is no bundled SRD feats file and thus no pre-Phase-4c feat behavior to preserve.

**Architecture:** `server/catalog/official_source.py` gains `load_official_feats()`, mirroring `load_official_races()`/`load_official_backgrounds()` exactly (source-qualified ids, `_copy` skip). `catalog/loader.py` gains a new `Catalog.feats: dict[str, dict]` field, populated ONLY from official data (no SRD merge — 2014 SRD has no feats at all). `engine/resolve.py` gains a new `_feat_granted_effects()` pass, structurally mirroring `_species_ability_bonuses`/`_background_ability_bonuses`, feeding the SAME early ability-score pass and the SAME `_categorize_proficiency`/`proficient_skills` merge points every other source already feeds.

**Tech Stack:** Same as every prior phase — Python/Flask backend, no new dependencies.

## Global Constraints

- **Safe no-op when official data is absent.** `Catalog.feats` is empty; `sheet.grantedFeats` stays inert (Phase 4b's existing behavior); no new `problems` entries. Checked at the end of every task.
- **`official_dir`/`has_official`/`load_official_races`/`load_official_backgrounds`/`load_official_feats` imported ONLY from `catalog.official_source`, never `chargen.sources` directly, anywhere outside that one file.** Unchanged constraint from Phase 4a/4b — never write `from chargen.sources import ...` anywhere in this plan.
- **Source-qualified ids**, matching races'/backgrounds' established `slug-source` convention — verify feat-name collisions across sources empirically before assuming none exist (do not skip this check just because it wasn't flagged in the design spec's own research).
- **Every claim verified against the REAL fetched data** (`~/.claude/dnd/.data/official/feats.json`) — this project's unbroken discipline. The design spec's own research already found real complexity the FIRST empirical pass on races/backgrounds missed; ground every task's exact shapes fresh.
- **Explicitly out of scope for this plan** (per the design spec, `docs/superpowers/specs/2026-09-27-builder-v2-phase4c-feats-design.md`): `additionalSpells` in any shape, the "take a feat instead of an ASI" class-level choice, `repeatable`/`repeatableHidden` multiplicity, `exclusiveFeatCategory` enforcement, `skillToolLanguageProficiencies`. Do not build any of these — disclose them in code comments where relevant, matching this project's established narrow-cut pattern.
- **Prerequisite enforcement is gated behind a preference toggle**, mirroring the EXACT existing shape: `draft.get("preferences", {}).get("usePrerequisites", {})` is a DICT keyed by mechanism (confirmed real: `.get("multiclass")` already exists) — add a NEW `"feats"` key to that SAME dict, do not invent a separate top-level preference.
- **A feat's non-structured prerequisites (campaign, other-feat, feature-name, free text) are never enforced, but the feat's full text still round-trips through the catalog for future display** — never silently drop the `entries` field.

---

### Task 1: `load_official_feats()` scaffolding, wired into `catalog/loader.py`

**Files:**
- Modify: `server/catalog/official_source.py`, `server/catalog/loader.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_loader.py`

**Interfaces:**
- Consumes: `official_dir()`/`has_official()` (already re-exported from this same module).
- Produces: `load_official_feats(official_dir: Path) -> list[dict]` returning feats with `index` (source-qualified), `name`, `source`, `category`, `entries` (raw, for future display), plus placeholder fields for every later task in this plan (mirroring Task 1's own scaffolding pattern from both Phase 4a and 4b — create the shape now, populate it task by task).

- [ ] **Step 1: Confirm the exact real data shape and check for name collisions**

```bash
cd server
.venv/bin/python -c "
import json, collections
with open('/Users/yoanpetrov/.claude/dnd/.data/official/feats.json') as f:
    data = json.load(f)
feats = [f for f in data.get('feat', []) if '_copy' not in f]
print(len(feats), 'non-copy records')
names = collections.Counter(f['name'] for f in feats)
dupes = {n: c for n, c in names.items() if c > 1}
print('duplicate names:', dupes)
print(json.dumps(feats[0], indent=2)[:1500])
"
```

Confirm the duplicate-name count (design spec's own research did not check this explicitly for feats — ground it now) and the exact top-level field shape before writing conversion code.

- [ ] **Step 2: Write failing tests against the REAL fetched data**

```python
import pytest
from catalog.official_source import official_dir, has_official, load_official_feats

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


def test_loads_a_real_feat_with_a_source_qualified_id():
    feats = load_official_feats(official_dir())
    alert = next(f for f in feats if f["name"] == "Alert")
    assert alert["index"].endswith("-phb") or alert["index"].endswith("-xphb")  # ground the real source


def test_total_feat_count_matches_real_data():
    feats = load_official_feats(official_dir())
    assert len(feats) > 250  # sanity: most of the 305 real non-copy records survived


def test_category_is_preserved():
    feats = load_official_feats(official_dir())
    origin_feats = [f for f in feats if f.get("category") == "O"]
    assert len(origin_feats) > 0  # 35 real Origin-category feats confirmed at plan-writing time
```

(Ground every literal against Step 1's real output before trusting it.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k feat`
Expected: FAIL — `load_official_feats` doesn't exist yet.

- [ ] **Step 4: Implement**

Add to `server/catalog/official_source.py` (the file already has the `sys.path` fix and `official_dir`/`has_official` re-export at its top from Phase 4a — do not duplicate, add new functions below the existing race/background code):

```python
def _feat_from_5etools(raw: dict) -> dict | None:
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    slug = raw["name"].lower().replace(" ", "-").replace("'", "")
    index = f"{slug}-{source}"

    return {
        "index": index,
        "name": raw["name"],
        "source": raw.get("source", ""),
        "category": raw.get("category", ""),
        "entries": raw.get("entries", []),
        "prerequisite": raw.get("prerequisite", []),  # Task 6 (prerequisite checking)
        "ability_bonuses": [],  # Task 2
        "ability_bonus_options": None,  # Task 2
        "proficiencies": [],  # Task 3 — skill/tool/weapon/armor, fixed grants
        "proficiency_choices": None,  # Task 3
        "languages": [],  # Task 4
        "language_options": None,  # Task 4
        "resist": [],  # Task 5
        "immune": [],  # Task 5
        "condition_immune": [],  # Task 5
        "senses": {},  # Task 5
        "expertise_skills": [],  # Task 6
        "saving_throw_proficiencies": [],  # Task 6
    }


def load_official_feats(official_dir: Path) -> list[dict]:
    feats_path = official_dir / "feats.json"
    if not feats_path.exists():
        return []
    with open(feats_path, encoding="utf-8") as f:
        data = json.load(f)
    feats = []
    for raw in data.get("feat", []):
        converted = _feat_from_5etools(raw)
        if converted is not None:
            feats.append(converted)
    return feats
```

The placeholder fields are populated by later tasks in this plan, matching the exact scaffolding pattern Phase 4a Task 1 and Phase 4b Task 1 both used.

- [ ] **Step 5: Wire into `catalog/loader.py`**

Read `server/catalog/loader.py`'s current `Catalog` dataclass and `load()` function in full first (confirm the exact current shape — Phase 4a/4b already modified this file twice). Add a `feats: dict[str, dict] = field(default_factory=dict)` field to `Catalog`, and inside `load()`:

```python
def load() -> Catalog:
    from .official_source import load_official_races, load_official_backgrounds, load_official_feats, official_dir
    # ... existing race/background merge logic ...
    official_feats = load_official_feats(official_dir())
    feats = _index_by(official_feats)  # NO SRD merge — 2014 SRD has no feats at all
    return Catalog(
        # ... existing fields ...
        feats=feats,
    )
```

Adapt to the real current structure — the load-bearing part is that `feats` has NO SRD-file merge (unlike races/backgrounds/traits), since there is no bundled SRD feats file to merge against.

- [ ] **Step 6: Run to verify all pass, full suite green**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k feat`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (455 baseline + your new tests), no regressions.

- [ ] **Step 7: Empirical end-to-end check**

```bash
.venv/bin/python -c "
from catalog.loader import load
catalog = load()
print('total feats after merge:', len(catalog.feats))
print('sample:', next(iter(catalog.feats.values()))['name'])
"
```

- [ ] **Step 8: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/official_source.py server/catalog/loader.py server/tests/test_official_source.py server/tests/test_loader.py
git commit -m "$(cat <<'EOF'
feat: load official feats into a new Catalog.feats dict

New load_official_feats() in official_source.py mirrors
load_official_races()/load_official_backgrounds() exactly
(source-qualified ids, _copy skip). No SRD merge — 2014 SRD has no
feats at all, so Catalog.feats is official-data-only, empty and
trivially safe when official data isn't fetched. Granted-effect
conversion (ability bonuses, proficiencies, languages, resistances/
senses, expertise, saving throws) and prerequisite checking are
separate follow-up tasks in this same plan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Ability bonus grants (fixed and choice)

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: the SAME `{"choose": {"from": [...], "amount"/"count": N}}` shape already handled for races (Phase 4a Task 2) and backgrounds (Phase 4b Task 4) — reuse that conversion logic directly, don't reimplement. Note feats' shape uses BOTH `"amount"` and `"count"` as the count key across different records (confirmed in the design spec's own research on "Ability Score Improvement" itself) — ground which key each real record actually uses before assuming one.
- Produces: `feat["ability_bonuses"]` (fixed, SRD `ability_bonuses` shape) and `feat["ability_bonus_options"]` (a real Choice envelope, SRD `ability_bonus_options` shape) populated.

- [ ] **Step 1: Ground the real shapes, confirm reusability of existing conversion functions**

```bash
.venv/bin/python -c "
import json, collections
with open('/Users/yoanpetrov/.claude/dnd/.data/official/feats.json') as f:
    data = json.load(f)
feats = [f for f in data.get('feat', []) if '_copy' not in f]
shapes = collections.Counter()
for f in feats:
    ab = f.get('ability')
    if not ab: continue
    for entry in ab:
        shapes[tuple(sorted(entry.keys()))] += 1
print(shapes)
"
```

Read the EXISTING race-side and background-side ability-bonus conversion functions in `official_source.py` fresh (both already exist, built in Phase 4a/4b) — determine whether feats' shape is close enough to call one of them directly, or needs its own small variant (feats can have a SINGLE fixed bonus like `{"con": 1}` with no `choose` at all — confirm this is handled by whichever existing function you reuse, or needs a small addition).

- [ ] **Step 2: Write failing tests against real feats**

```python
def test_actor_grants_a_fixed_charisma_bonus():
    feats = load_official_feats(official_dir())
    actor = next(f for f in feats if f["name"] == "Actor")
    assert actor["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 1}]


def test_athlete_offers_a_choice_of_str_or_dex():
    feats = load_official_feats(official_dir())
    athlete = next(f for f in feats if f["name"] == "Athlete")
    envelope = athlete["ability_bonus_options"]
    assert envelope["choose"] == 1
    ids = {o["ability_score"]["index"] for o in envelope["from"]["options"]}
    assert ids == {"str", "dex"}
```

(Ground both literals against Step 1's real output before trusting them.)

- [ ] **Step 3: Run to verify they fail, implement, verify pass, full suite green**

- [ ] **Step 4: Commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: feat ability-bonus grants (fixed and choice)

Reuses the existing races/backgrounds ability-bonus conversion
machinery directly — feats use the same envelope shapes, just
sometimes with a single fixed bonus and no choice at all.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Skill/tool/weapon/armor proficiency grants (fixed and choice)

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: the SAME `_proficiencies_from_5etools`/proficiency-choice-envelope machinery already built for races (Phase 4a Task 3/4) and backgrounds (Phase 4b Task 1/2) — reuse directly.
- Produces: `feat["proficiencies"]` (fixed grants, SRD shape) and `feat["proficiency_choices"]` populated.

**Real data confirmed at plan-writing time:** only 12/305 feats have `skillProficiencies`, 10 have `toolProficiencies`, 6 have `armorProficiencies`, 4 have `weaponProficiencies` — a small surface. Ground the exact shapes (fixed vs. choice vs. wildcard) via the same style of dump command used in every prior task before assuming they match races'/backgrounds' exact shapes.

- [ ] **Step 1: Ground the real shapes**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/feats.json') as f:
    data = json.load(f)
feats = [f for f in data.get('feat', []) if '_copy' not in f]
for key in ('skillProficiencies', 'toolProficiencies', 'weaponProficiencies', 'armorProficiencies'):
    for f in feats:
        if f.get(key):
            print(key, '->', f['name'], '->', f[key])
"
```

- [ ] **Step 2-4: Standard TDD loop** — write failing tests against real feats for each category found, implement by reusing the existing race/background-side conversion functions (read their current signatures fresh, adapt if genuinely needed), verify, full suite green.

- [ ] **Step 5: Commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: feat skill/tool/weapon/armor proficiency grants

Reuses the existing races/backgrounds proficiency conversion
machinery directly (fixed grants and choices) — a small real surface
(12/10/6/4 feats respectively for skill/tool/armor/weapon).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Language grants (fixed and choice)

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: the SAME language-grant conversion machinery built for backgrounds (Phase 4b Task 3) — reuse directly. Only 7/305 feats have `languageProficiencies` — a small surface.

- [ ] **Step 1: Ground the real shapes** (same dump-command style as every prior task).
- [ ] **Step 2-4: Standard TDD loop.**
- [ ] **Step 5: Commit.**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: feat language grants (fixed and choice)

Reuses the existing background language-grant conversion machinery
directly — a small real surface (7/305 feats).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Resistances, immunities, condition immunities, senses

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `resist`/`immune`/`conditionImmune`'s SAME conversion machinery built for races (Phase 4a Task 5) — reuse `_damage_modifiers_from_5etools`/`_condition_immunities_from_5etools` directly if their signatures allow a raw dict input generically (confirm this before assuming, mirroring how Phase 4b Task 1's report found `_proficiencies_from_5etools` was ALREADY dict-shape-agnostic despite its race-specific parameter name).
- Produces: `feat["resist"]`/`feat["immune"]`/`feat["condition_immune"]` (SRD shape, reused fields) populated. A NEW `feat["senses"]: dict` field (e.g. `{"blindsight": 15}`) — no existing precedent to reuse, build fresh, small.
- Produces (resolve.py): `sheet.damageModifiers`/`sheet.conditionImmunities` (Phase 4a's existing fields) now ALSO merge in feat-granted entries (a feat's resistance ADDS to whatever race/subrace already granted, deduplicated, not replacing it). A NEW `sheet.senses: dict` field, merging race-granted senses (if any exist — check, Phase 4a's race work may not have modeled senses at all, in which case this is purely feat-sourced) with feat-granted ones (higher range wins per D&D RAW for the same sense type — e.g. two sources of darkvision take the better range, not both applied additively; confirm this is the correct RAW rule before implementing, don't assume).

- [ ] **Step 1: Ground the real shapes** (resist/immune/conditionImmune/senses dump, same style as every prior task — only 11/2/2/4 feats respectively, a small surface).

- [ ] **Step 2: Read the EXISTING `_species_damage_modifiers`/`_species_condition_immunities` in `resolve.py` fresh** (Phase 4a Task 5, confirm current exact shape) to determine the cleanest way to ALSO merge feat-sourced entries into the same `sheet.damageModifiers`/`conditionImmunities` fields — this is genuinely the first time this plan touches an EXISTING Phase 4a merge point rather than building something purely additive, so ground it carefully.

- [ ] **Step 3-5: Standard TDD loop**, including a same-sense-type "which range wins" test if senses turns out to need that rule (ground the real RAW rule, don't assume additive-vs-max without checking).

- [ ] **Step 6: Commit.**

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: feat-granted resistances, immunities, condition immunities, senses

Reuses Phase 4a's existing damage-modifier/condition-immunity
conversion machinery, merging feat-sourced entries into the SAME
sheet.damageModifiers/conditionImmunities fields races already
populate (additive, deduplicated). New sheet.senses field is
feat-sourced for now (no prior precedent), same-type sources resolved
per the real RAW "higher range wins" rule, not simple addition.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Expertise, saving-throw proficiencies, structured prerequisite checking, and wiring background-granted feats onto the sheet

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing existing directly reusable for expertise/saving-throw-proficiencies (genuinely new mechanics) — the existing `_multiclass_prerequisite_problems` (Phase 3b-i) as the direct structural precedent for the new `_feat_prerequisite_problems`.
- Produces: `feat["expertise_skills"]`/`feat["saving_throw_proficiencies"]` populated in `official_source.py`. In `resolve.py`: a new `_feat_granted_effects(catalog, feat_ids) -> dict` function collecting EVERY effect type across a list of feat ids (ability bonuses, proficiencies, languages, resistances, senses, expertise, saving throws — all six prior tasks' outputs, in one place), wired into the SAME early ability-score pass and the SAME `_categorize_proficiency`/`proficient_skills` merge points every other source already feeds, driven by `sheet.grantedFeats` (already populated by Phase 4b, previously inert). A new `sheet.expertiseSkills: string[]` field (always `[]` when none). `proficient_save_abilities` (currently class-only) gains feat-sourced entries. A new `_feat_prerequisite_problems(catalog, feat_ids, total_level, final_scores, use_prerequisites)` function, gated on `draft.get("preferences", {}).get("usePrerequisites", {}).get("feats")` (a NEW key in the SAME existing dict `.get("multiclass")` already uses — confirm this exact current shape before adding to it).

- [ ] **Step 1: Ground the real expertise/savingThrowProficiencies shapes** (7 and 2 real feats respectively — a small surface, dump command matching every prior task's style).

- [ ] **Step 2: Read `_multiclass_prerequisite_problems` in full, fresh, in the current `resolve.py`** — this is the exact structural precedent for `_feat_prerequisite_problems`: same "only check if the preference is on," same "append a problem, never block/hide the underlying grant," same per-item problem id convention (mirror `f"multiclass-prerequisite-unmet-{cls_id}"` as something like `f"feat-prerequisite-unmet-{feat_id}"`).

- [ ] **Step 3: Read the current `draft.get("preferences", {}).get("usePrerequisites", {})` call site(s) in `resolve.py` fresh** — confirm it's genuinely a dict keyed by mechanism name (`"multiclass"` confirmed at plan-writing time) before adding a new `"feats"` key to the same shape.

- [ ] **Step 4: Write failing tests against real data** — cover: a background-granted feat's ability bonus/proficiency/resistance/sense/expertise/saving-throw ALL landing on the sheet when `sheet.grantedFeats` includes it (an integration test exercising every effect type on one real feat if a single real feat happens to grant several simultaneously — check Step 1's dump for a good candidate — otherwise several smaller tests); a feat with an unmet LEVEL prerequisite producing a `problems` entry when the toggle is on, and none when it's off; a feat with an unmet ABILITY-SCORE prerequisite, same toggle behavior; a feat with a NON-structured prerequisite (campaign/other/feature) producing NO problem regardless of the toggle (disclosed non-enforcement, not silently almost-enforced); an SRD-only draft (no official data, or no feats granted) completely unaffected.

- [ ] **Step 5: Implement** — `_feat_granted_effects` wiring, `_feat_prerequisite_problems`, the `usePrerequisites.feats` toggle, `sheet.expertiseSkills`, `proficient_save_abilities` extension.

- [ ] **Step 6: Run to verify tests pass, then full suite green.** Confirm the existing multiclass-prerequisite test suite still passes UNCHANGED (this task touches the SAME preferences dict shape, verify it doesn't disturb the existing `"multiclass"` key's behavior).

- [ ] **Step 7: Empirical end-to-end check**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
# Ground a real background that grants a feat with a real, checkable
# effect (an ability bonus or a proficiency) before trusting this —
# find one via catalog.backgrounds' own 'feats' field.
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'background': {'id': '<a real background id granting a real feat>', 'choices': {}},
    'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
print('granted feats:', r['sheet']['grantedFeats'])
print('problems:', r['problems'])
print('proficiencies:', r['sheet']['proficiencies'])
"
```

- [ ] **Step 8: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: apply background-granted feats' full mechanical effects

sheet.grantedFeats (inert since Phase 4b) now actually applies its
feats' effects — ability bonuses, proficiencies, languages,
resistances/senses, expertise, saving throws — via a new
_feat_granted_effects pass feeding the same merge points every other
source already feeds. Structured (level/ability-score) prerequisites
now produce a problems entry when unmet, gated behind a new
preferences.usePrerequisites.feats toggle mirroring the existing
multiclass-prerequisite pattern exactly. Non-structured prerequisites
(campaign, other-feat, feature-name, free text) are explicitly never
enforced — disclosed, not silently approximated.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** every "in scope" item from the design spec has a task — catalog import (Task 1), ability bonuses (2), proficiencies (3), languages (4), resistances/senses (5), expertise/saving-throws/prerequisite-checking/wiring (6). Every "explicitly out of scope" item (additionalSpells, ASI-or-feat choice, repeatable multiplicity, exclusiveFeatCategory, skillToolLanguageProficiencies) has NO task — confirmed no task's scope silently reaches into any of them.
- **Placeholder scan:** Tasks 2-6 deliberately leave exact conversion code less fully pre-written than Task 1's scaffolding, with explicit instructions to re-ground against real data and re-read the exact current existing-machinery signatures before reusing them — matching Phase 4a/4b's own established practice for their less purely-mechanical tasks, given how often "should reuse X directly" claims needed a small adjustment once checked against real code.
- **Type consistency:** every new sheet field name (`grantedFeats` — Phase 4b, unchanged; `expertiseSkills` — new; `senses` — new; `damageModifiers`/`conditionImmunities` — Phase 4a, extended not replaced) is introduced once and referenced consistently across tasks.
- **Cross-task interaction risk, learned from both prior phases' final reviews:** Task 6 explicitly asks the implementer to confirm the existing `"multiclass"` preferences-toggle behavior is undisturbed by adding a sibling `"feats"` key — the SAME class of "did this task's addition change an existing, unrelated behavior" risk both Phase 4a's and Phase 4b's final reviews had to catch. A genuine final whole-branch review remains the real backstop for anything this plan's own per-task grounding doesn't anticipate.
- **Scope check:** 6 tasks, each independently testable, deliberately narrower than "all of Phase 4c" (see design spec). Given BOTH prior phases grew via review-found chained gaps (Phase 4a: 7→9 tasks, Phase 4b: 6→9 tasks), this plan's own task count is a floor, not a ceiling.
