# Phase 4b — Sourcebook Backgrounds (Full Fidelity Except Feats) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every background from every official sourcebook (135 non-`_copy` real records, already fetched via `chargen/sync.py --official` to `~/.claude/dnd/.data/official/backgrounds.json`) becomes selectable with full mechanical fidelity: skill/tool proficiencies (fixed and choice, including an "any N" wildcard), fixed and choice language grants, the 2024-style ability-score-improvement choice, and the "choose equipment package A or B" starting-equipment shape. Feat-granting is imported and stored but stays mechanically INERT (no prerequisite checking, no granted-effect application) until Phase 4c gives it a real home — this is a deliberate, disclosed scope boundary, not an oversight. The SRD baseline (Acolyte, already working) is completely unaffected — this is purely additive, safe no-op on a machine that hasn't fetched official data.

**Architecture:** Directly extends the exact pattern Phase 4a already built and merged for races — `server/catalog/official_source.py` is extended (not replaced) with `load_official_backgrounds()`, converting raw 5etools background JSON into the SAME dict shape `server/catalog/loader.py` already produces for the bundled SRD background (`starting_proficiencies`, `languages`, `language_options`, `starting_equipment`, `starting_equipment_options`, `starting_gold`, `feature`). `catalog/loader.py` merges this into `Catalog.backgrounds` at load time. Backgrounds are structurally SIMPLER than races here: SRD backgrounds carry proficiencies/languages/equipment as DIRECT top-level fields, not indirected through a separate "traits" catalog the way races are — so this phase needs no synthetic-trait-minting step at all, unlike races' Task 1.

**Tech Stack:** Same as Phase 4a — Python/Flask backend, no new dependencies, reads the already-fetched local JSON, no network calls in `resolve()`'s own request path.

## Global Constraints

- **Safe no-op when official data is absent.** Every new code path in `catalog/loader.py`/`resolve()` must produce IDENTICAL output to today's when `chargen.sources.has_official()` is `False` — checked at the end of every task.
- **`official_dir`/`has_official`/`load_official_races`/`load_official_backgrounds` are imported ONLY from `catalog.official_source`, never `chargen.sources` directly, anywhere outside `official_source.py` itself.** This constraint and its enforcement mechanism (the `sys.path` fix + re-export) already exist and are unchanged by this plan — `load_official_backgrounds` is simply a new function added to the same file, reusing the same already-patched `sys.path`. Never write `from chargen.sources import ...` anywhere in this plan.
- **Source-qualified ids, matching 5etools' own convention and races' established pattern.** Confirmed empirically: 13 background NAMES collide across different sourcebooks in the real data (Acolyte, Archaeologist, Charlatan, Criminal, Entertainer, Haunted One, Hermit, House Agent, Investigator, Noble, Sage, Sailor, Soldier — each appears in 2 different sources). An id like `acolyte-xphb` (source-qualified, exactly like races' `aasimar-vgm`) is required — never collide with the bundled SRD `acolyte` id (SRD ids carry no source suffix) or with each other.
- **Every fix verified against the REAL fetched data** (`~/.claude/dnd/.data/official/backgrounds.json`, already on this machine) — every shape claim in this plan was checked against real records while writing it; re-verify at implementation time, don't trust this plan's memory of the data over the data itself.
- **`_copy`/`_mod`-based records are skipped** (161 total records, 135 non-`_copy` — same disclosed, bounded cut as races).
- **Feats are storage-only, not a mechanic.** A background's `feats` field converts into an inert list (feat ids/names) attached to the resolved background/sheet — no prerequisite checking, no effect application, nothing reads it downstream except (eventually) display. Do not build any feat mechanics in this plan; that's explicitly Phase 4c's job, deferred until this phase's own shape reveals how feat-references should look in practice.
- **The `additionalSpells` field on backgrounds uses a DIFFERENT shape than races' innate spellcasting, and is explicitly OUT OF SCOPE for this plan.** Confirmed empirically: 15/135 backgrounds have `additionalSpells`, and every one uses the `"expanded"` key (e.g. `{"expanded": {"s0": [...], "s1": [...], ...}}`) — meaning "these spells count as being on your class's spell list," a spell-LIST-EXPANSION mechanic. This is NOT the same as races' `"innate"` key (spells you can cast without preparation, Phase 4a Task 6). Nothing in this engine models "expand my known-spell options" today — do not build it in this plan; disclose it as an explicitly-skipped field, matching this project's established narrow-cut pattern (e.g. Phase 4a's choice-shaped Dragonborn resistances).

---

### Task 1: `load_official_backgrounds()` scaffolding — basic fields + fixed skill/tool proficiencies, wired into `catalog/loader.py`

**Files:**
- Modify: `server/catalog/official_source.py`, `server/catalog/loader.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: `official_dir()`/`has_official()` (already re-exported from this same module, Phase 4a).
- Produces: `load_official_backgrounds(official_dir: Path) -> list[dict]` returning backgrounds in the EXACT dict shape `catalog/loader.py` already uses for the bundled SRD background.

- [ ] **Step 1: Confirm the exact target shape and real data shape empirically**

```bash
cd server
.venv/bin/python -c "
import json
with open('../chargen/data/srd/5e-SRD-Backgrounds.json') as f:
    print(json.dumps(json.load(f)[0], indent=2)[:1500])
"
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/backgrounds.json') as f:
    data = json.load(f)
bgs = [b for b in data['background'] if '_copy' not in b]
print(len(bgs), 'non-copy records')
print(json.dumps(bgs[0], indent=2)[:2000])
"
```

Confirm: bundled SRD background has `index, name, starting_proficiencies ([{index,name,url}]), language_options ({choose,type,from}), starting_equipment ([{equipment:{index,name,url}, quantity}]), starting_gold ({quantity, unit}), starting_equipment_options ([{choose,type,from}]), feature ({name, desc:[str]})`. Real 5etools background has `name, source, skillProficiencies ([{skill:true,...}]), toolProficiencies ([{tool:true,...} or {any:N}]), languageProficiencies ([{lang:true,...} or {anyStandard:N} or {choose:{from:[...]}}]), ability ([{choose:{weighted:{from:[3 abilities], weights:[2,1] or [1,1,1]}}}, ...] — always exactly 2 entries, confirmed across all 60 real records with this field), feats ([{feat-slug:true}]), startingEquipment ([{a:[...], b:[...]}]), entries (flavor text), additionalSpells (OUT OF SCOPE, see Global Constraints).

- [ ] **Step 2: Write failing tests against the REAL fetched official data**

```python
def test_loads_a_real_non_srd_background_with_a_source_qualified_id():
    backgrounds = load_official_backgrounds(official_dir())
    acolyte_records = [b for b in backgrounds if b["name"] == "Acolyte"]
    assert len(acolyte_records) >= 1
    xphb_acolyte = next(b for b in acolyte_records if b["index"].endswith("-xphb"))
    assert xphb_acolyte["index"] == "acolyte-xphb"


def test_no_id_collides_with_the_bundled_srd_background_id():
    from catalog.loader import load
    catalog = load()
    srd_ids = set(catalog.backgrounds.keys())
    official_backgrounds = load_official_backgrounds(official_dir())
    official_ids = {b["index"] for b in official_backgrounds}
    assert srd_ids.isdisjoint(official_ids)


def test_copy_based_records_are_skipped_not_crashed_on():
    backgrounds = load_official_backgrounds(official_dir())
    assert len(backgrounds) > 100  # sanity: most of the 135 real non-copy records survived


def test_fixed_skill_proficiency_lands_directly_on_the_background_dict():
    backgrounds = load_official_backgrounds(official_dir())
    # Use whichever real background Step 1's dump showed with skillProficiencies
    # (Aberrant Heir/EFA grants History + Intimidation per this plan's own
    # research — re-verify against Step 1's real output before trusting this).
    aberrant_heir = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    prof_ids = {p["index"] for p in aberrant_heir["starting_proficiencies"]}
    assert {"skill-history", "skill-intimidation"} <= prof_ids
```

(Ground every literal against Step 1's real output before trusting it — re-run a targeted dump filtered to the specific background if an assertion doesn't match on the first test run, and correct the test, not the implementation, if the real data disagrees with this plan's memory of it.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k background`
Expected: FAIL — `load_official_backgrounds` doesn't exist yet.

- [ ] **Step 4: Implement**

Add to `server/catalog/official_source.py` (the file already exists from Phase 4a, with the `sys.path` fix and `official_dir`/`has_official` re-export already in place at its top — do not duplicate that, just add new functions below the existing race-side code):

```python
def _race_style_skill_tool_proficiencies(raw: dict) -> list[dict]:
    """Converts skillProficiencies/toolProficiencies (the SAME boolean-map
    shape races use — [{"history": true, "intimidation": true}]) into
    SRD's starting_proficiencies shape. Reuses the exact id-prefix
    conventions _proficiencies_from_5etools already established for races
    (Phase 4a Task 3) — skill- prefix + reference_data.SKILL_NAMES,
    tool ids via the same _slug()/_tool_display_name() helpers already in
    this file. Do NOT reimplement the conversion logic; call the existing
    race-side helper(s) directly if their signature allows it (read
    _proficiencies_from_5etools's current signature first — it may need a
    small refactor to accept a raw dict directly rather than a race
    record specifically, if it currently assumes race-only fields; if so,
    that refactor is in scope for this task, keep it minimal)."""
    ...


def _background_from_5etools(raw: dict) -> dict | None:
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    slug = raw["name"].lower().replace(" ", "-").replace("'", "")
    index = f"{slug}-{source}"

    return {
        "index": index,
        "name": raw["name"],
        "starting_proficiencies": _race_style_skill_tool_proficiencies(raw),
        "language_options": None,  # Task 3
        "languages": [],  # Task 3
        "starting_equipment": [],  # Task 5
        "starting_gold": None,  # Task 5
        "starting_equipment_options": [],  # Task 5
        "feature": {"name": "", "desc": []},  # not modeled mechanically — flavor text only, SRD's own `feature` field is likewise never read for anything mechanical by resolve.py today (confirm this by grepping `bg.get("feature"` / `bg\[.feature.\]` in resolve.py before assuming — if it turns out to be read somewhere, populate this properly from raw["entries"] instead of leaving it empty)
        "ability_bonus_options": None,  # Task 4
        "source": raw.get("source", ""),
        "feats": [],  # Task 6
    }


def load_official_backgrounds(official_dir: Path) -> list[dict]:
    bg_path = official_dir / "backgrounds.json"
    if not bg_path.exists():
        return []
    with open(bg_path, encoding="utf-8") as f:
        data = json.load(f)
    backgrounds = []
    for raw in data.get("background", []):
        converted = _background_from_5etools(raw)
        if converted is not None:
            backgrounds.append(converted)
    return backgrounds
```

The placeholder fields (`language_options: None`, `starting_equipment: []`, etc.) are populated by later tasks in this same plan — this task's job is scaffolding + the fixed skill/tool proficiency path, matching Phase 4a Task 1+3's combined scope (backgrounds need no separate synthetic-trait step, so these collapse into one task here).

Before finalizing, actually read `_proficiencies_from_5etools` (or whatever it's now named) in the current `official_source.py` to confirm whether it can be called directly for a background's raw dict or needs a small parameter change — ground this against the real current code, not this plan's memory of Phase 4a's own shape.

- [ ] **Step 5: Wire into `catalog/loader.py`**

Read `server/catalog/loader.py`'s current `load()` function (already modified once by Phase 4a for races — confirm its exact current shape before editing). Add the background merge alongside the existing race merge, following the identical pattern:

```python
from .official_source import load_official_races, load_official_backgrounds, official_dir

# inside load():
official_races, official_subraces, official_traits = load_official_races(official_dir())
official_backgrounds = load_official_backgrounds(official_dir())
races = {**_index_by(_load("5e-SRD-Races.json")), **_index_by(official_races)}
subraces = {**_index_by(_load("5e-SRD-Subraces.json")), **_index_by(official_subraces)}
traits = {**_index_by(_load("5e-SRD-Traits.json")), **official_traits}
backgrounds = {**_index_by(_load("5e-SRD-Backgrounds.json")), **_index_by(official_backgrounds)}
```

Adapt to whatever the real current `load()` looks like — the load-bearing part is the dict merge (SRD ∪ official), not the exact surrounding syntax.

- [ ] **Step 6: Run to verify all pass, full suite green**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k background`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (375 baseline from Phase 4a + your new tests), no regressions.

- [ ] **Step 7: Empirical end-to-end check**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
print('total backgrounds after merge:', len(catalog.backgrounds))
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'background': {'id': 'acolyte-xphb', 'choices': {}},
    'species': {'id': 'human', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
print('proficient skills:', r['sheet']['proficiencies']['skills'] if 'skills' in r['sheet']['proficiencies'] else r['derived'].get('skills'))
print('problems:', r['problems'])
"
```

(Ground the exact real 2024 Acolyte's skill grants and the sheet's real skill-proficiency field path against Step 1/existing tests before trusting this snippet's assertions — this is illustrative of the check, not a literal expected-output spec.)

- [ ] **Step 8: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/official_source.py server/catalog/loader.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: load sourcebook backgrounds, fixed skill/tool proficiencies

New load_official_backgrounds() in official_source.py (already the
Phase 4a single point of truth for the chargen.sources import)
converts raw 5etools background JSON into the exact dict shape
catalog/loader.py already produces for the bundled SRD Acolyte
background — backgrounds carry proficiencies/languages/equipment as
direct top-level fields (unlike races' trait-indirected shape), so no
synthetic-trait step is needed here. Fixed skill/tool proficiencies
reuse Phase 4a's own conversion helpers directly. Language choices,
the ability-bonus choice, equipment package choice, and feat storage
are separate follow-up tasks in this same plan. Safe no-op when
official data hasn't been fetched.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 1b: Close a pre-existing gap — `resolve()` never consumed tool/weapon/armor proficiencies from backgrounds

**Why this task exists:** Task 1's own review (implementer + independent reviewer, verified two ways — direct code reading and a live `resolve()` repro against real sourcebook data) found that `server/engine/resolve.py:1088` is the ONLY place a background's `starting_proficiencies` is read, and it only forwards `skill-` prefixed entries into `sheet.proficiencies.skills` — tool/weapon/armor grants from a background (e.g. `acolyte-xphb`'s real Calligrapher's Supplies grant) never reach `sheet.proficiencies.tools`. This is a genuinely SEPARATE code path from Phase 4a's Task 3b fix (which only touches race/subrace trait scanning, never reads `bg` at all) — so that fix does not cover this. Confirmed empirically: `catalog.backgrounds["acolyte-xphb"]["starting_proficiencies"]` contains the tool grant, but the resolved sheet's `tools` list comes back empty. Mirrors the Task 3→3b precedent from Phase 4a exactly — a per-task review found a bug in existing engine code, not introduced by this plan, that needs its own dedicated fix task before this phase can claim full proficiency fidelity.

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: the EXISTING `_categorize_proficiency(prof_id: str) -> None` nested function inside `resolve()` (Phase 4a Task 3b already extended it once for race/subrace traits — reused unmodified here).
- Produces: `sheet.proficiencies.armor/weapons/tools` now ALSO include grants from a background's `starting_proficiencies`, for every background (SRD and sourcebook).

- [ ] **Step 1: Ground the exact current code**

Confirmed at plan-writing time — `server/engine/resolve.py` around lines 1083-1160 has, in order: the skill-scanning block (`proficient_skills.update(...)` for classes/species/background/race traits, `bg.get("starting_proficiencies", [])` filtered to `skill-` only at the line this bug lives on), then `proficient_armor`/`proficient_weapons`/`proficient_tools` set init, then `_categorize_proficiency`'s definition, then the race/subrace trait second-pass Task 3b already added (`if race: trait_refs = ...`), then the class-level prof-choice loop. Re-locate this exact sequence before editing — other tasks in THIS plan (2-6) may run before or after this one depending on execution order, but none should have touched this exact block.

- [ ] **Step 2: Write a failing test against REAL sourcebook data first**

No `has_official()` skip needed if a bundled-SRD example existed, but confirmed at plan-writing time that SRD's own Acolyte has NO tool/weapon/armor proficiency grant (only `skill-insight`/`skill-religion`) — so this bug is only reachable via sourcebook data, and this test DOES need the skip guard:

```python
@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_background_tool_proficiency_reaches_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(background={"id": "acolyte-xphb", "choices": {}})
    resolution = resolve(draft, catalog)
    tools = set(resolution["sheet"]["proficiencies"]["tools"])
    # Ground the exact real tool id against catalog.backgrounds["acolyte-xphb"]
    # ["starting_proficiencies"] before trusting this literal — this plan's
    # own research found "calligraphers-supplies", re-verify it still matches.
    assert "calligraphers-supplies" in tools
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k background_tool_proficiency`
Expected: FAIL — `tools` is empty despite the grant existing in the background dict.

- [ ] **Step 4: Fix `resolve.py`**

Add a small pass reading `bg.get("starting_proficiencies", [])` for non-skill entries, calling the existing `_categorize_proficiency`, placed right alongside the race/subrace trait second-pass Task 3b already added (same style, same reasoning — a small, disclosed second read of data already scanned once for skills):

```python
    if bg:
        for p in bg.get("starting_proficiencies", []):
            if not p["index"].startswith("skill-"):
                _categorize_proficiency(p["index"])
```

- [ ] **Step 5: Run to verify it passes, then full suite green**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k background_tool_proficiency`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (381 baseline from Task 1 + your new test). Re-check any existing test asserting an exact (not `in`-based) tools/armor/weapons list for any background — Phase 4a's own grounding found none for races; re-verify the same holds for backgrounds before assuming it.

- [ ] **Step 6: Empirical end-to-end check, commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: resolve() now consumes tool/weapon/armor proficiencies from backgrounds

Backgrounds could always carry tool/weapon/armor proficiency grants
(sourcebook data has plenty of real examples, e.g. acolyte-xphb's
Calligrapher's Supplies), but resolve()'s background-scanning code
only ever forwarded skill- prefixed entries into the sheet — a
genuinely separate code path from Phase 4a's Task 3b fix, which only
touches race/subrace trait scanning. Found during Phase 4b's own Task
1 review, not introduced by it. Fixed by adding a small pass over
bg.get("starting_proficiencies", []) calling the existing
_categorize_proficiency for non-skill entries, mirroring Task 3b's
own fix pattern exactly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Proficiency CHOICES for skills/tools, including the "any N" wildcard

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog/choices.py`'s EXISTING `any_skill`/`any_tool` `option_set_type` branches (built in Phase 4a Task 4 for races) — reused UNMODIFIED, no changes to `choices.py` needed for this task.
- Produces: a NEW `_background_choice_templates` block (extending the existing function, which today only reads `language_options`) that also reads a background's skill/tool proficiency-choice envelope and builds a Choice template from it.

**Real data confirmed at plan-writing time:** `skillProficiencies`/`toolProficiencies` entries can ALSO carry a `{"choose": {"from": [...]}}` shape (an enumerated proficiency CHOICE, not just a fixed grant) or an `{"any": N}` wildcard — the SAME two shapes Phase 4a Task 3/4 already found and handled for races. Confirm the exact real examples via:

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/backgrounds.json') as f:
    data = json.load(f)
for b in [x for x in data['background'] if '_copy' not in x]:
    for key in ('skillProficiencies', 'toolProficiencies'):
        for entry in b.get(key) or []:
            if 'choose' in entry or 'any' in entry:
                print(key, '->', b['name'], b.get('source'), '->', entry)
"
```

- [ ] **Step 1: Ground the real shapes from the command above, confirm they match the race-side shapes Phase 4a already solved**

- [ ] **Step 2: Write failing tests**

```python
def test_enumerated_skill_choice_on_a_background_becomes_an_options_array_choice(catalog):
    draft = _fighter_acolyte_human_draft(background={"id": "<real-background-id-with-an-enumerated-skill-choice>", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    assert any("skill" in cid or "proficiency" in cid for cid in cids)  # tighten once the real cid convention is chosen in Step 3


def test_any_n_wildcard_tool_choice_on_a_background_offers_every_tool(catalog):
    # Ground the real background/count against Step 1's output before writing this.
    ...
```

(These are illustrative — ground the exact background id, cid convention, and expected option count against Step 1's real findings before finalizing.)

- [ ] **Step 3: Implement**

Add a skill/tool proficiency-choice envelope builder to `official_source.py` mirroring races' equivalent logic (Phase 4a Task 3/4's `_race_style_skill_tool_proficiencies`-adjacent choice-building code — locate and reuse, don't reimplement), storing it as a NEW field on the background dict, e.g. `starting_proficiency_choices: list[dict]` (a list since a background could in principle need both a skill AND a tool choice simultaneously — confirm via Step 1 whether this actually happens in real data, and size the field accordingly: a single dict if it never does, a list if it can).

Extend `_background_choice_templates` in `resolve.py` (currently only reads `language_options`) to also build a Choice template from this new field, using the SAME `build_choice_template` call pattern already used for the existing `language_options` block right above it — reuse `catalog/choices.py`'s `any_skill`/`any_tool` `option_set_type` branches unmodified for the wildcard case; enumerated choices need no new envelope shape at all (same `options_array` mechanism everything else uses).

- [ ] **Step 4: Run to verify tests pass, then full suite green**

- [ ] **Step 5: Commit**

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: sourcebook backgrounds' skill/tool proficiency choices

Extends the existing _background_choice_templates (previously only
built a Choice for language_options) with a new block reading
proficiency choices, reusing Phase 4a's any_skill/any_tool wildcard
branches in catalog/choices.py unmodified.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Fixed and choice language grants

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`, `server/catalog/choices.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog/choices.py`'s EXISTING `resource_list` handling (already resolves language ids from `reference_data.LANGUAGES` for the SRD `language_options` shape) — reused for the `anyStandard: N` wildcard case, since it's the SAME "every language" set. Consumes the EXISTING `options_array` mechanism for the named-list case.
- Produces: `bg["languages"]` (fixed grants, SRD-shaped `[{index,name,url}]`) and `bg["language_options"]` (a real Choice envelope) populated for sourcebook backgrounds.

**Real data confirmed at plan-writing time:** `languageProficiencies` entries take THREE shapes across 56 real backgrounds — `{"anyStandard": N}` (46 records, "choose N of any language" — this is a WILDCARD, but since it's semantically identical to SRD's own `language_options` `resource_list` mechanism, it should feed the EXISTING `resource_list`/`/languages` pathway directly, not the `any_skill`-style new-branch pattern), `{"choose": {"from": [...]}}` (6 records, an enumerated list of specific languages, sometimes including a literal `"other"` entry meaning "or any other language of your choice" — treat `"other"` as just another named option in the list, labeled distinctly, e.g. "Other"), and a FIXED grant shape `{"giant": true}` (a couple of records, e.g. Rune Carver/BGG). A background can combine a fixed grant with a separate `anyStandard`/`choose` entry (mirroring races' Aetherborn-style fixed+choice combination from Phase 4a Task 2) — ground this against real data before assuming either "exactly one entry" or "always combinable."

- [ ] **Step 1: Confirm the exact three shapes and any fixed+choice combinations via a real data dump**

```bash
.venv/bin/python -c "
import json, collections
with open('/Users/yoanpetrov/.claude/dnd/.data/official/backgrounds.json') as f:
    data = json.load(f)
bgs = [b for b in data['background'] if '_copy' not in b]
for b in bgs:
    lp = b.get('languageProficiencies')
    if lp:
        print(b['name'], b.get('source'), '->', lp)
"
```

- [ ] **Step 2: Write failing tests, TDD loop**

Cover: a fixed-grant-only background (`bg["languages"]` populated, no Choice offered), an `anyStandard`-only background (a real Choice offered, sourcing every language via the existing `resource_list` mechanism — confirm this by checking the Choice's option COUNT matches `len(reference_data.LANGUAGES)`), an enumerated-list background (a real Choice with exactly the named options, `"other"` handled sanely), and — if Step 1 finds one — a background combining both a fixed grant and a choice simultaneously.

- [ ] **Step 3: Implement**

In `official_source.py`, convert `languageProficiencies` into `bg["languages"]` (fixed entries, SRD `{index,name,url}` shape, looked up via `reference_data.LANGUAGES` by matching the 5etools language slug — confirm the slug format matches `reference_data.LANGUAGES`' own ids, e.g. "giant" → the real `reference_data.LANGUAGES` entry for Giant, adjust for any casing/naming mismatch found) and `bg["language_options"]` (an SRD-shaped envelope: for `anyStandard`, build `{"choose": N, "type": "languages", "from": {"option_set_type": "resource_list", "resource_list_url": "/api/2014/languages"}}` — literally the SAME shape SRD's own Acolyte already uses, so `catalog/choices.py` needs ZERO changes for this case; for `choose`/named-list, build a normal `options_array` envelope).

`resolve()` already reads `bg.get("languages", [])` (confirmed at plan-writing time, `resolve.py` around line 1238: `fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + ...`) and already builds a Choice from `bg.get("language_options")` via the existing `_background_choice_templates` block — so THIS task needs no `resolve.py` changes at all if the SRD-shaped envelope is produced correctly; re-verify this claim against the real current code before assuming it, and only touch `resolve.py` if grounding reveals it's actually needed.

- [ ] **Step 4: Run to verify tests pass, full suite green**

- [ ] **Step 5: Commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: sourcebook backgrounds' fixed and choice language grants

Fixed grants populate bg.languages (SRD shape, already consumed by
resolve()); the "any standard language" wildcard reuses SRD's own
existing language_options/resource_list mechanism verbatim (zero new
code in catalog/choices.py); an enumerated named-list choice uses the
same options_array envelope every other choice in this codebase uses.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: The 2024 background ability-score-improvement choice

**Files:**
- Modify: `server/catalog/official_source.py`, `server/catalog/choices.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing existing directly reusable — this is a genuinely NEW envelope shape and a NEW resolve.py pipeline step, mirroring (structurally, not literally) `_species_ability_bonuses`/`_species_ability_bonus_choice_template` (Phase 1-era functions, unchanged) but for backgrounds instead of species.
- Produces: `_background_ability_bonuses(bg)` (parallel to the existing `_species_ability_bonuses`) returning `{}` for every background (backgrounds never grant a FIXED, non-choice ability bonus — confirmed empirically: every one of the 60 real records with an `ability` field uses the `choose` shape exclusively, never a flat `{"str": 2}`-style fixed entry) and `_background_ability_bonus_choice_template(bg, bg_id)` building a real Choice for the 2-option weighted mechanic.

**The real rule, confirmed empirically and precisely — read this before designing anything:** every one of the 60 real backgrounds with an `ability` field has EXACTLY 2 entries in a fixed pattern: entry 1 is `{"choose": {"weighted": {"from": [3 abilities], "weights": [2, 1]}}}` (pick ONE of the 3 to get +2, then a DIFFERENT ONE of the remaining 2 to get +1) and entry 2 is `{"choose": {"weighted": {"from": [the SAME 3 abilities], "weights": [1, 1, 1]}}}` (get +1 to ALL THREE). This is the real, standardized 2024 PHB background ASI rule ("+2/+1 split, or +1/+1/+1", always from a fixed pool of exactly 3 named abilities) — it is NOT a per-background varying shape, it's ONE universal mechanic with a per-background 3-ability pool. Confirmed via exhaustive scan: `list lengths: {2}`, `weight patterns seen: {(1,1,1), (2,1)}`, `from-pool sizes: {3}` — zero exceptions across all 60 records.

This means the player is choosing between exactly 2 "bundles," each bundle being a SET of simultaneous ability bonuses (2 abilities for the split option, 3 for the flat option) — not a single ability+bonus pick the way `ability_bonus_options`' existing `option_type: "ability_bonus"` (one ability, one bonus) already models. This needs a bundle-of-multiple-ability-bonuses option shape, analogous to how `catalog/choices.py`'s EXISTING `"multiple"` option type already bundles multiple `counted_reference` equipment items into one selectable option (see that file's own `_bundle_label_and_id`) — but for `ability_bonus` sub-items instead of `counted_reference` ones.

- [ ] **Step 1: Design the envelope and option shape**

Represent each background's ability choice as a `{"choose": 1, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": [OPTION_A, OPTION_B]}}` envelope (reusing the existing `options_array` top-level mechanism — `choose: 1` because the player picks ONE of the two bundles as a whole). Each option is `{"option_type": "multiple", "items": [{"option_type": "ability_bonus", "ability_score": {...}, "bonus": 2}, {"option_type": "ability_bonus", "ability_score": {...}, "bonus": 1}]}` for the split option, and three `ability_bonus` items each with `bonus: 1` for the flat option — but WITHOUT actually committing to which of the 3 abilities gets which bonus yet, since for the split option the player ALSO needs to choose WHICH ability gets +2 vs which gets +1 among the 3, and for the flat option all 3 are fixed (no further choice needed within that bundle).

**This means the real player-facing choice has up to 3 layers for the split bundle** (pick split-vs-flat, THEN pick which of the 3 gets +2, implicitly the other two of the remaining pair get... no — re-derive this precisely from the real rule, don't guess): re-read the actual 2024 PHB rule text if available, or reason from the weights: `weights: [2, 1]` with `from: [A, B, C]` (3 abilities) means the player picks 2 of the 3 abilities and assigns +2 to one and +1 to the other (leaving the third untouched) — that's `3 choose 2, times 2 orderings = 6` total combinations for the split bundle, plus exactly 1 combination for the flat bundle (all three get +1, no further choice). **Ground this combinatorial count against `server/engine/asi.py`'s existing pure-ASI-combination-math module (built in an earlier phase for the standard ASI choice) before designing new code — check whether it already has a generic "N abilities from a pool, with per-slot weights" combination generator you can reuse, since this is structurally very similar to how ASI/Half-Elf's own ability_bonus_options combination generation already works (per Phase 1's own architecture).**

Enumerate the FULL real option list as flat, individually-selectable "bundle" options (one per concrete combination — e.g. "STR +2, CON +1" / "STR +2, CHA +1" / "CON +2, STR +1" / "CON +2, CHA +1" / "CHA +2, STR +1" / "CHA +2, CON +1" / "STR +1, CON +1, CHA +1"), matching how `catalog/choices.py`'s existing "multiple" bundling already flattens equipment bundles into single selectable options — this avoids inventing a NEW multi-layer choice UI concept (which `<ChoiceCard>`/`<ChoicePicker>` don't support today) and instead produces one ordinary Choice with up to 7 options, fully representable by the EXISTING generic Choice model with zero frontend changes.

- [ ] **Step 2: Write failing tests against real data**

```python
def test_background_ability_choice_offers_all_split_and_flat_combinations():
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["name"] == "Aberrant Heir")  # STR/CON/CHA pool, confirmed in this plan's own research
    envelope = bg["ability_bonus_options"]
    assert envelope["choose"] == 1
    options = envelope["from"]["options"]
    assert len(options) == 7  # 6 split combinations + 1 flat combination
```

(Ground the exact expected option count/labels against your Step 1 design and real data before finalizing this test — 7 is this plan's own derivation, re-verify it, don't take it on faith.)

- [ ] **Step 3: Implement `_ability_bonus_options_from_5etools_weighted_pair`** in `official_source.py`, producing the flattened option list per Step 1's design. Wire it into `_background_from_5etools`'s `ability_bonus_options` field.

- [ ] **Step 4: Implement `_background_ability_bonuses`/`_background_ability_bonus_choice_template`** in `resolve.py`, mirroring `_species_ability_bonuses`/`_species_ability_bonus_choice_template`'s existing structure closely (read both functions fresh first — Phase 4a's plan already reproduced their exact current code once; re-read `resolve.py` directly rather than trusting that older copy, since other tasks may have touched nearby lines since). `_background_ability_bonuses` always returns `{}` (backgrounds never grant a fixed bonus — see Global claim above), so it exists mainly for symmetry/future-proofing and to make the "ability bonuses come from species AND background, both flow through the same early ability-score pass" invariant explicit in the code, matching this plan's earlier research note: "backgrounds don't grant ability bonuses in this ruleset" (a 2014-only comment already in `resolve.py`) becomes false once these are wired in — find and update that comment.

Wire the new choice template into wherever `_species_ability_bonus_choice_template`'s result already gets included in `choice_templates` (find that call site, add the background-side equivalent alongside it) and wire the resolved selection's ability bonuses into the SAME early ability-score pass `_species_ability_bonuses` already feeds (find that exact code path before designing the wiring — this is the single most delicate part of this task, since ability scores are computed once, early, and every bonus source must land in the same place).

- [ ] **Step 5: Run to verify tests pass, then full suite green.** Specifically confirm: selecting a split-bundle option applies +2/+1 correctly to final ability scores; selecting the flat-bundle option applies +1/+1/+1 correctly; an SRD-only Acolyte draft (no `ability_bonus_options` field) is completely unaffected (safe no-op, `_background_ability_bonuses`/the new choice template contribute nothing when the field is absent).

- [ ] **Step 6: Empirical end-to-end check, commit**

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: 2024-style background ability-score-improvement choice

Every real background with an ability field uses the SAME universal
mechanic (choose: +2/+1 split between two of a 3-ability pool, or
+1/+1/+1 flat across all three) — not a per-background varying shape.
Flattened into ordinary selectable bundle options (up to 7 per
background), representable by the existing generic Choice model with
zero frontend changes. bg.ability_bonus_options feeds a new
_background_ability_bonus_choice_template mirroring the existing
species-side function; resolved selections flow into the same early
ability-score pass every other bonus source already uses.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Starting equipment package choice (A or B)

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: the EXISTING `_equipment_choice_templates`/`starting_equipment_options` pathway (`resolve.py`, unchanged) and `catalog/choices.py`'s EXISTING `"multiple"` option-bundling mechanism (unchanged) — this task needs ZERO `resolve.py` changes if the envelope is shaped correctly, since `starting_equipment_options` already flows through the exact same generic Choice machinery every other choice type uses. Confirm this claim by re-reading `_equipment_choice_templates` (Phase 4a's plan already reproduced it once; re-read fresh) before assuming it holds unmodified.

**Real data confirmed at plan-writing time:** `startingEquipment` is a list with exactly one entry, `{"a": [...], "b": [...]}` — bundle A is usually a mix of specific item-name strings (with a `|source` suffix to strip, matching races' weapon-id convention from Phase 4a Task 3) and an optional trailing `{"value": N}` entry (a gold amount in COPPER — confirm the unit against real data, e.g. Aberrant Heir's `{"value": 1600}` for bundle A's trailing gold vs `{"value": 5000}` for bundle B's gold-only option; 5etools' own convention for `"value"` in this context is typically copper pieces — verify, don't assume, since getting the unit wrong makes every converted gold amount 100x wrong), bundle B is often gold-only (a single `{"value": N}` entry) but not always — ground the real variety via:

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/backgrounds.json') as f:
    data = json.load(f)
count = 0
for b in [x for x in data['background'] if '_copy' not in x]:
    se = b.get('startingEquipment')
    if se:
        print(b['name'], b.get('source'), '->', json.dumps(se))
        count += 1
        if count >= 8:
            break
"
```

- [ ] **Step 1: Ground the real variety (item-only bundles, gold-only bundles, mixed bundles, the gold unit) from the command above**

- [ ] **Step 2: Write failing tests**

```python
def test_equipment_package_choice_becomes_a_two_option_multiple_bundle_choice(catalog):
    draft = _fighter_acolyte_human_draft(background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    equip_cid = next((cid for cid in cids if "equipment-choice" in cid), None)
    assert equip_cid is not None, f"expected an equipment package choice, got: {cids}"
    equip_choice = next(c for c in resolution["choices"] if c["id"] == equip_cid)
    assert len(equip_choice["options"]) == 2  # package A, package B
```

(Ground the exact background id/expected option count against Step 1's real output before trusting this.)

- [ ] **Step 3: Implement**

In `official_source.py`, convert `startingEquipment[0]`'s `a`/`b` lists into `bg["starting_equipment_options"]` — an SRD-shaped `[{choose: 1, type: "equipment", from: {option_set_type: "options_array", options: [OPTION_A, OPTION_B]}}]` where each OPTION is `option_type: "multiple"` bundling the resolved items (strip `|source`, look up against `catalog.items` by the same slug convention Phase 4a's weapon-id work established — flag, don't silently drop, any item slug that doesn't resolve against `catalog.items`, matching this plan's established narrow-disclosed-gap pattern) plus a synthetic "N gp" entry for any `{"value": N}` member (a `counted_reference`-shaped or `string`-shaped synthetic option item — ground which shape `catalog/choices.py`'s existing `_bundle_label_and_id` actually requires for every member before choosing; it currently requires EVERY item in a "multiple" bundle to be a plain `counted_reference` or the whole bundle returns `None` — a gold-value member needs to either match that shape via a synthetic item entry, or `_bundle_label_and_id` needs a narrow, disclosed extension to accept one gold-value member per bundle; ground this against the current real code before deciding which path, and prefer the synthetic-item approach if it avoids touching `choices.py` at all).

- [ ] **Step 4: Run to verify tests pass, full suite green**

- [ ] **Step 5: Empirical end-to-end check, commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: sourcebook backgrounds' equipment package choice (A or B)

Converts 5etools' {"a": [...], "b": [...]} shape into SRD's own
starting_equipment_options envelope, each bundle represented via the
existing "multiple" option-bundling mechanism catalog/choices.py
already has — needs zero resolve.py changes since starting_equipment_
options already flows through the generic Choice pipeline unmodified.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Feat storage (inert) and source filtering for backgrounds

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `bg["feats"]: string[]` (inert feat ids, no mechanical effect) and — mirroring Phase 4a Task 7 exactly — `draft.sources` now also filters selectable backgrounds the same way it already filters races.

- [ ] **Step 1: Confirm the real `feats` shape** (already sampled in this plan's own research: `[{"aberrant dragonmark|efa": true}]` — a boolean-map of feat-slug-with-source-suffix → true, same convention as skill/toolProficiencies) and convert into a plain list of feat ids (strip `|source`, keep the slug — do NOT attempt to resolve against any feat catalog, since none exists in this app yet; this is pure inert data).

- [ ] **Step 2: Write failing tests, TDD loop** — a background with `feats` populated produces `bg["feats"] == [...]` (or wherever this plan's grounding decides it should live on the resolved sheet — a new `sheet.grantedFeats` field, mirroring Phase 4a Task 5's `sheet.damageModifiers` precedent of "pure data pass-through, new sheet field, always present as `[]` not null" is the most consistent choice; confirm against how the existing `feature` field, if read at all, surfaces on the sheet before finalizing where this goes).

- [ ] **Step 3: Extend `resolve()`'s background-lookup code** (find the equivalent of races' `elif race and draft.get("sources"):` block for backgrounds — likely needs adding, since Phase 4a's Task 7 only touched the race-lookup path) to reject a background whose source isn't in `draft.sources` (when non-empty), reusing whatever the existing `unknown-background`-equivalent problem id already is (find it — likely `unknown-background`, mirroring `unknown-species`).

- [ ] **Step 4: Run to verify tests pass, full suite green.** Re-check the exact analogous risk Phase 4a's final review caught: does a source-filtered-out background interact badly with anything ELSE that reads `bg` independently downstream (the way races' Task 5/6 functions did with `race`/`subrace`)? Grep for every place `resolve.py` reads `bg.get(...)` independently of the main `bg` lookup and confirm each one is `None`-safe when `bg` itself is `None` — this is exactly the class of bug the Phase 4a final review found, worth checking proactively here rather than waiting for a final review to catch it again.

- [ ] **Step 5: Also expose `source` on `GET /api/catalog` for backgrounds** (mirroring Phase 4a Task 7's race-side exposure — check whether that task already added a generic per-record `source` field that backgrounds automatically inherit, or whether backgrounds need their own explicit addition; read `server/app.py`'s current catalog endpoint to confirm before assuming either way).

- [ ] **Step 6: Empirical end-to-end check, commit**

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: inert feat storage and draft.sources filtering for backgrounds

Mirrors Phase 4a Task 5 (pure data pass-through, new sheet field) and
Task 7 (source filtering, reusing the existing unknown-X problem
pattern) for backgrounds. Feats are stored but mechanically inert —
no prerequisite checking, no effect application — until Phase 4c.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** every mechanical dimension the committed Phase 4 design spec named for backgrounds is covered — skill/tool proficiencies (fixed + choice + wildcard, Tasks 1-2), language proficiencies (fixed + choice + wildcard, Task 3), the background ability-bonus pipeline step (Task 4), the equipment package choice (Task 5), and feat storage (Task 6). `additionalSpells`'s "expanded" mechanic is explicitly, deliberately out of scope (Global Constraints) — not a coverage gap, a disclosed cut matching this project's established pattern.
- **Placeholder scan:** Task 4 (the ability-bonus choice) and Task 5 (the equipment package) are deliberately left with real, load-bearing DESIGN QUESTIONS flagged as decisions to make at implementation time against fresh real-code grounding (the exact combinatorial option count for Task 4, the exact bundling mechanism for a gold-value member in Task 5) — this mirrors Phase 4a's own established practice for its hardest tasks (Task 3's `_categorize_proficiency` alignment, Task 6's innate-spell scope) rather than shipping a possibly-wrong copy-paste snippet. This is a deliberate choice given how much of Phase 4a's OWN first-draft assumptions were corrected by real-data grounding at implementation time — not an oversight.
- **Type consistency:** `bg["ability_bonus_options"]`, `bg["starting_proficiency_choices"]`, `bg["feats"]` are all introduced once (Task 1's scaffolding, as `None`/`[]` placeholders) and populated by name-matching later tasks — verified no task references a field name a different task didn't establish.
- **Cross-task interaction risk, learned from Phase 4a's own final review:** Task 6's Step 4 explicitly asks the implementer to proactively check for the "filtered-to-None but something else still reads the stale reference" class of bug that Phase 4a's final review had to catch after the fact (Tasks 5/6 × Task 7 interaction) — since this plan follows the SAME task ordering shape (data-adding tasks first, source-filtering last), the SAME risk shape could recur. Flagging this explicitly in Task 6 rather than only relying on this plan's own final whole-branch review to catch it, though that review remains the real backstop.
- **Scope check:** this plan is appropriately sized for one SDD cycle — 6 tasks, each independently testable, matching Phase 4a's original (pre-chained-gap) 7-task scope. Given Phase 4a grew to 9 tasks via review-found chained gaps, this plan's own task count is a floor, not a ceiling — expect it may grow the same way, and that's a sign the process is working, not a planning failure.
