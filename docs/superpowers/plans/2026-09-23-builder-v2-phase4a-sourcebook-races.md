# Phase 4a — Sourcebook Races (Full Fidelity) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every race and subrace from every official sourcebook (~160 races, ~98 subraces, already fetched via `chargen/sync.py --official` to `~/.claude/dnd/.data/official/races.json`) becomes selectable with full mechanical fidelity: ability bonuses (fixed and choice, including the weighted shape), speed, size, languages, skill/tool/weapon/armor proficiencies (fixed and choice, including an "any N" wildcard), damage resistances/immunities/vulnerabilities, condition immunities, and innate spellcasting. The SRD baseline (already working) is completely unaffected — this is purely additive, and on a machine that hasn't fetched the official data, behaves exactly as it does today.

**Architecture:** A new module, `server/catalog/official_source.py`, converts raw 5etools-src race/subrace records into the SAME dict shape `server/catalog/loader.py` already produces for SRD races (`index`, `name`, `speed`, `ability_bonuses`, `size`, `languages`, `traits` — plus new fields for resistances/immunities/innate spells this phase adds). `catalog/loader.py` calls this new module once at load time, extending `Catalog.races`/`subraces`/`traits` with the converted records — `catalog/choices.py`/`engine/resolve.py` need ZERO changes to consume races/subraces/traits themselves, since the shape matches exactly. Genuinely new mechanical surface (resistances, innate spells, the "any N" proficiency wildcard) gets its own small, additive extension to `resolve()`/`choices.py`, following the same patterns Phase 3b already established for `ability_bonus_options`.

**Tech Stack:** Same as every prior phase — Python/Flask backend, no new dependencies. Reads a local JSON file already on disk (`chargen.sources.official_dir()`); no network calls in `resolve()`'s own request path.

## Global Constraints

- **Safe no-op when official data is absent.** Every new code path in `catalog/loader.py`/`resolve()` must produce IDENTICAL output to today's when `chargen.sources.has_official()` is `False` — this is the single most important regression guard in this plan, checked at the end of every task, not just the last one.
- **Reuse `chargen.sources.official_dir()`/`has_official()` directly** (pure path/existence helpers, confirmed to have no `chargen.catalog`-specific coupling) — do NOT reuse anything from `chargen.catalog`/`chargen.model`/`chargen.normalise` (different, incompatible object model).
- **Source-qualified ids, matching 5etools' own convention.** A record from a non-SRD source gets an id suffixed by its source tag (e.g. `aasimar-vgm`, matching how the raw data already disambiguates reprints — Aasimar appears in VGM, then again reprinted in MPMM and XPHB, each a DIFFERENT record needing a DIFFERENT id) — never collide with an SRD id or with each other.
- **Every fix verified against the REAL fetched data** (`~/.claude/dnd/.data/official/races.json`, already on this machine) — this project's unbroken discipline, more important than ever now that the data is messier/more varied than SRD's.
- **`_copy`/`_mod`-based records are skipped** (return nothing from the normalizer for that record) — these are 5etools' own "this record is defined as another record plus a diff" shorthand, and fully resolving them is out of scope for this pass (matches v1's own disclosed cut in `chargen/normalise.py`, inherited here for the same reason: real, but bounded, engineering cost with a small number of affected records).

---

### Task 1: `official_source.py` scaffolding — basic race fields, wired into `catalog/loader.py`

**Files:**
- Create: `server/catalog/official_source.py`
- Modify: `server/catalog/loader.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_catalog_loader.py` (or wherever `Catalog.load`'s own existing tests live — check first)

**Interfaces:**
- Consumes: `chargen.sources.official_dir()`, `chargen.sources.has_official()` (both existing, reused as-is).
- Produces: `load_official_races(official_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]` returning `(races, subraces, traits_by_index)` — all three in the EXACT dict shape `catalog/loader.py` already uses for SRD races/subraces/traits.

- [ ] **Step 1: Confirm the exact target shape empirically**

From `server/`, before writing any conversion code, dump one full real SRD race record and one full real SRD trait record to confirm the target shape precisely (do this even though it's already documented above — this project's discipline is to verify at the moment of writing code, not just trust an earlier summary):

```bash
.venv/bin/python -c "
import json
with open('../chargen/data/srd/5e-SRD-Races.json') as f:
    print(json.dumps(json.load(f)[0], indent=2))
with open('../chargen/data/srd/5e-SRD-Traits.json') as f:
    traits = json.load(f)
    print(json.dumps(next(t for t in traits if t['index']=='keen-senses'), indent=2))
"
```

Confirm: race has `index, name, speed, ability_bonuses ([{ability_score:{index,name,url}, bonus}]), alignment, age, size, size_description, languages ([{index,name,url}]), language_desc, traits ([{index,name,url}])`. Trait has `index, races, subraces, name, desc ([str]), proficiencies ([{index,name,url}])`.

- [ ] **Step 2: Write failing tests against the REAL fetched official data**

Read `server/tests/test_resolve.py`'s conventions for the `catalog` fixture, then write `server/tests/test_official_source.py`:

```python
import pytest
from chargen.sources import official_dir, has_official
from catalog.official_source import load_official_races

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


def test_loads_a_real_non_srd_race_with_a_source_qualified_id():
    races, subraces, traits_by_index = load_official_races(official_dir())
    aasimar_records = [r for r in races if r["name"] == "Aasimar"]
    assert len(aasimar_records) >= 1  # VGM, MPMM, XPHB reprints — several distinct records
    vgm_aasimar = next(r for r in aasimar_records if r["index"].endswith("-vgm"))
    assert vgm_aasimar["index"] == "aasimar-vgm"
    assert vgm_aasimar["speed"] == 30
    assert vgm_aasimar["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 2}]


def test_srd_style_fields_present_and_correctly_shaped():
    races, subraces, traits_by_index = load_official_races(official_dir())
    for r in races[:20]:  # spot-check a slice, not all 160 — this is a shape check, not exhaustive
        assert "index" in r and "name" in r and "speed" in r
        assert isinstance(r.get("ability_bonuses", []), list)
        assert isinstance(r.get("languages", []), list)
        assert isinstance(r.get("traits", []), list)


def test_no_id_collides_with_a_bundled_srd_race_id():
    from catalog.loader import load
    catalog = load()
    srd_ids = set(catalog.races.keys())
    official_races, _, _ = load_official_races(official_dir())
    official_ids = {r["index"] for r in official_races}
    assert srd_ids.isdisjoint(official_ids)


def test_copy_based_records_are_skipped_not_crashed_on():
    # Confirm the loader doesn't raise on the whole real dataset, which is
    # known (from empirical grounding) to contain _copy/_mod records.
    races, subraces, traits_by_index = load_official_races(official_dir())
    assert len(races) > 100  # sanity: most of the ~160 real records survived
```

(Empirically confirm Aasimar-VGM's exact `ability_bonuses` value and any other asserted literal against the real data before trusting this snippet — re-run the Step 1 style dump filtered to Aasimar/VGM if the assertion above doesn't match on the first test run, and correct the test, not the implementation, if the real data disagrees with this plan's memory of it.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v`
Expected: FAIL (`ModuleNotFoundError` or similar — `catalog/official_source.py` doesn't exist yet).

- [ ] **Step 4: Implement**

Create `server/catalog/official_source.py`:

```python
"""Converts the wider, multi-sourcebook 5etools-src race/subrace/background
data (fetched by `python3 -m chargen.sync --official` into
chargen.sources.official_dir(), never committed to this repo — see that
module and chargen/sync.py for the fetch/licensing details this module
inherits without re-litigating) into the SAME dict shape
catalog/loader.py already produces for the bundled 2014 SRD data. This is
a from-scratch v2-native normalizer — it does NOT reuse chargen.catalog's
own normalizer (chargen.normalise.race_from_5etools etc.), because that
targets chargen's own frozen dataclasses, a different, incompatible
object model from the raw dicts catalog/choices.py and engine/resolve.py
read throughout. Only chargen.sources' pure path/existence helpers are
shared.

Every record's id is source-qualified (e.g. "aasimar-vgm") using the raw
5etools "source" field lowercased, so a reprint across multiple books
(Aasimar in VGM, then MPMM, then XPHB) produces multiple distinct
records, and nothing here can ever collide with a bundled SRD id (SRD ids
have no source suffix at all).

_copy/_mod-based records (5etools' own "defined as another record plus a
diff" shorthand) are skipped — real, but a bounded, disclosed cut, same
scope decision v1's own chargen/normalise.py already made for the same
reason (see that module's docstring).
"""
from __future__ import annotations

from pathlib import Path
import json


def _ability_bonuses_from_5etools(ability_list: list[dict]) -> list[dict]:
    """Converts 5etools' `ability` field (a list of dicts, each either a
    flat {"cha": 2, ...} fixed-bonus map or containing a "choose" sub-key)
    into SRD-shaped ability_bonuses — ONLY the fixed-bonus portion; the
    choose-N portion is handled separately by
    _ability_bonus_options_from_5etools, since SRD keeps these as two
    distinct fields (ability_bonuses vs ability_bonus_options) and so does
    this module, for the same reason: build_choice_template only ever
    looks at ability_bonus_options, and _species_ability_bonuses only
    ever looks at ability_bonuses — keeping them separate here means both
    existing functions need no changes."""
    bonuses = []
    for entry in ability_list or []:
        for key, val in entry.items():
            if key == "choose":
                continue
            bonuses.append({"ability_score": {"index": key, "name": key.upper(), "url": ""}, "bonus": val})
    return bonuses


def _race_from_5etools(raw: dict, traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    slug = raw["name"].lower().replace(" ", "-").replace("'", "")
    index = f"{slug}-{source}"

    size_map = {"S": "Small", "M": "Medium", "L": "Large"}
    sizes = raw.get("size") or ["M"]
    size = size_map.get(sizes[0], "Medium")

    # Trait entries: mint one synthetic trait per top-level `entries` item,
    # added to traits_by_index (mutated in place, mirroring how the SRD
    # loader builds one shared traits_by_index dict up front) so the
    # existing trait-rendering/proficiency-scanning code in resolve.py
    # (which already reads catalog.traits by id, already handles a trait
    # with no `proficiencies` field correctly per Phase 3b-i) picks these
    # up with zero changes. Subsequent tasks in this plan ADD proficiencies/
    # resist/spells fields onto these same synthetic trait dicts — this
    # task only creates them with description text.
    trait_refs = []
    for i, entry in enumerate(raw.get("entries", [])):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue  # skip bare strings / unnamed entries — not real traits
        trait_id = f"{index}-trait-{i}"
        desc_lines = [e for e in entry.get("entries", []) if isinstance(e, str)]
        traits_by_index[trait_id] = {
            "index": trait_id, "races": [{"index": index, "name": raw["name"], "url": ""}],
            "subraces": [], "name": entry["name"], "desc": desc_lines, "proficiencies": [], "url": "",
        }
        trait_refs.append({"index": trait_id, "name": entry["name"], "url": ""})

    return {
        "index": index, "name": raw["name"],
        "speed": raw.get("speed") if isinstance(raw.get("speed"), int) else 30,
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "alignment": "", "age": "", "size": size, "size_description": "",
        "languages": [], "language_desc": "",
        "traits": trait_refs,
        "source": raw.get("source", ""),  # NEW field, SRD races don't have it (implicitly "SRD") — Task 6 uses this for filtering/labeling
    }


def load_official_races(official_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]:
    races_path = official_dir / "races.json"
    if not races_path.exists():
        return [], [], {}
    with open(races_path, encoding="utf-8") as f:
        data = json.load(f)

    traits_by_index: dict[str, dict] = {}
    races = []
    for raw in data.get("race", []):
        converted = _race_from_5etools(raw, traits_by_index)
        if converted is not None:
            races.append(converted)

    # Subraces: deferred detail — Step 5 of this task extends this function
    # for subrace["subrace"] records once the race-only path is proven.
    subraces: list[dict] = []

    return races, subraces, traits_by_index
```

- [ ] **Step 5: Extend for subraces**

Read a real subrace record from the data first:

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
print(json.dumps(data['subrace'][0], indent=2)[:1000])
"
```

Confirm the subrace shape (likely has a `raceName`/`raceSource` back-reference to its parent race, plus its own `ability`/`entries` following the same conventions as races) and the bundled SRD subrace shape (`server/chargen/data/srd/5e-SRD-Subraces.json`, read one record) for the target shape — `catalog.loader.py`'s SRD subrace conversion should already show the exact fields needed (likely `index, name, race:{index,name,url}, ability_bonuses, racial_traits, ...` — verify, don't assume). Implement `_subrace_from_5etools(raw, traits_by_index) -> dict | None` mirroring `_race_from_5etools`'s structure, and wire it into `load_official_races` to populate the `subraces` return value. Update the module's own tests (Step 2) with a real subrace case once this exists.

- [ ] **Step 6: Wire into `catalog/loader.py`**

Read `server/catalog/loader.py` in full. Find the `Catalog` dataclass's `races`/`subraces`/`traits` population (likely in a `load()` function that builds the dataclass from `_load()`/`_index_by()` calls on the bundled SRD files). Add, after the SRD data is loaded:

```python
from .official_source import load_official_races
from chargen.sources import official_dir

# ... inside load():
official_races, official_subraces, official_traits = load_official_races(official_dir())
races_by_index = {**_index_by(_load("5e-SRD-Races.json")), **_index_by(official_races)}
# (adapt to the real existing variable names/construction pattern in this
# file rather than assuming this exact snippet — read the current code
# first, this is illustrative of the MERGE, not a literal patch)
traits_by_index = {**_index_by(_load("5e-SRD-Traits.json")), **official_traits}
```

The exact insertion point depends on `loader.py`'s real current structure — read it fully before editing, and confirm the merge preserves every existing SRD-only behavior unchanged (Global Constraints' no-op guarantee).

- [ ] **Step 7: Run to verify all pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v`
Expected: PASS (or SKIPPED if `has_official()` is False on the CI/test machine — the `pytestmark` skip guard handles this).

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect every existing test to still pass UNCHANGED (this is the single most important check in this task — the SRD-only behavior must be byte-identical).

- [ ] **Step 8: Empirical end-to-end check — resolve a character with a real non-SRD race**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
print('total races after merge:', len(catalog.races))
print('aasimar variants:', [r for r in catalog.races if 'aasimar' in r])
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'aasimar-vgm', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
print('CHA (base 8 + Aasimar +2):', r['sheet']['abilities']['CHA'])
print('problems:', r['problems'])
"
```

Confirm CHA shows 10 (8 base + Aasimar's +2), zero problems, and the species resolves cleanly through the EXISTING, unmodified `_species_ability_bonuses`/species choice pipeline.

- [ ] **Step 9: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/official_source.py server/catalog/loader.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: load sourcebook races/subraces into the same dict shape as SRD

New server/catalog/official_source.py converts the wider 5etools-src
race/subrace data (already fetched via chargen/sync.py --official,
never committed) into the exact dict shape catalog/loader.py already
produces for bundled SRD races — so catalog/choices.py and
engine/resolve.py need zero changes to consume them. Ability bonuses,
speed, size, and trait descriptions land this task; skill/tool/weapon/
armor proficiencies, resistances, and innate spellcasting are separate
follow-up tasks in this same plan. Safe no-op when official data
hasn't been fetched on a given machine.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Ability bonus CHOICES — fixed-weight and weighted shapes

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: `catalog/choices.py`'s EXISTING `option_type: "ability_bonus"` handling (built in Phase 3b for Half-Elf) — reused, not modified, for the simple choose-N-of-M case.
- Produces: races with a `choose` sub-entry in their `ability` field now carry a populated `ability_bonus_options` field (SRD shape), feeding the EXISTING `_species_ability_bonus_choice_template`/Choice machinery with zero changes to `resolve.py`.

- [ ] **Step 1: Empirically confirm both real shapes**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
for r in data['race']:
    ab = r.get('ability')
    if ab:
        for entry in ab:
            if 'choose' in entry:
                print(r['name'], r.get('source'), '->', entry)
"
```

Confirm the simple shape (`{"choose": {"from": [...], "count": N}}`, possibly alongside a fixed bonus in the SAME entry, e.g. Aetherborn's `{"cha": 2, "choose": {"from": [...], "count": 2}}` — a FIXED +2 CHA plus a SEPARATE choice of +1 to two others) — read this carefully, since it means a single race can have BOTH `ability_bonuses` (the fixed part) AND `ability_bonus_options` (the choice part) simultaneously, which `_species_ability_bonuses`/`_species_ability_bonus_choice_template` already both handle correctly (they're independent code paths, not mutually exclusive) — confirm this by reading both functions once more.

- [ ] **Step 2: Write failing tests**

```python
def test_ability_choice_race_gets_both_fixed_and_choice_envelopes():
    races, _, _ = load_official_races(official_dir())
    # Use whichever real race Step 1 found with a mixed fixed+choice shape
    aetherborn = next(r for r in races if r["name"] == "Aetherborn")
    assert aetherborn["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 2}]
    assert aetherborn["ability_bonus_options"]["choose"] == 2
    assert {o["ability_score"]["index"] for o in aetherborn["ability_bonus_options"]["from"]["options"]} == {"str", "dex", "con", "int", "wis"}


def test_ability_choice_flows_through_the_existing_choice_machinery(catalog_with_official):
    # A real resolve() test — build a draft selecting 2 of the 5 offered
    # abilities for Aetherborn's choice envelope, confirm it applies.
    ...
```

(Ground the second test's exact draft/assertions against real data once Step 1's output is in hand — don't guess the exact race name/values without having run Step 1 first.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k ability_choice`

- [ ] **Step 4: Implement `_ability_bonus_options_from_5etools`**

Add to `official_source.py`, matching SRD's `ability_bonus_options` envelope shape exactly (`{"choose": N, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": [{"option_type": "ability_bonus", "ability_score": {...}, "bonus": 1}, ...]}}`, per Phase 3b's own established shape):

```python
def _ability_bonus_options_from_5etools(ability_list: list[dict]) -> dict | None:
    for entry in ability_list or []:
        choose = entry.get("choose")
        if not choose:
            continue
        from_list = choose.get("from", [])
        count = choose.get("count", 1)
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": 1}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    return None
```

Wire it into `_race_from_5etools`'s return dict:

```python
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", [])),
```

**Note the WEIGHTED shape from backgrounds (`{"weighted": {"from": [...], "weights": [...]}}`) is explicitly NOT handled by this function** — confirmed empirically that this shape appears on BACKGROUNDS (Phase 4b), not races (this task's scope) — races only use the simple `{"from": [...], "count": N}` shape. If Step 1's real data check finds a race using the weighted shape too, stop and flag it rather than silently mishandling it — but ground truth from this plan's own research says races don't need it.

- [ ] **Step 5: Run to verify tests pass, then full suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_official_source.py -v -k ability_choice`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green, no regressions.

- [ ] **Step 6: Commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: sourcebook races' ability-bonus CHOICES flow through the existing machinery

A race can carry both a fixed ability_bonuses entry and a separate
ability_bonus_options choice simultaneously (e.g. Aetherborn: fixed
+2 CHA, plus choose 2 of 5 for +1 each) — both SRD-shaped fields are
independently populated, feeding Phase 3b's already-built ability-
bonus Choice mechanism (built for Half-Elf) with zero changes to
resolve.py or catalog/choices.py.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Skill/tool/weapon/armor proficiencies — fixed grants

**Files:**
- Modify: `server/catalog/official_source.py`
- Test: `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: the synthetic per-trait dicts (Task 1) gain a populated `proficiencies` field wherever the source race grants a FIXED (non-choice) skill/tool/weapon/armor proficiency — feeding the EXISTING trait-proficiency-scanning code in `resolve.py` (built in Phase 3b-i, reads `trait.get("proficiencies", [])` filtered by `skill-`/other prefixes) with zero changes there.

- [ ] **Step 1: Empirically confirm the exact boolean-map shape for all four categories**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
for key in ('skillProficiencies', 'toolProficiencies', 'weaponProficiencies', 'armorProficiencies'):
    for r in data['race']:
        if r.get(key):
            print(key, '->', r['name'], r.get('source'), '->', r[key])
            break
"
```

- [ ] **Step 2: Write failing tests**

```python
def test_fixed_skill_proficiency_lands_on_a_synthetic_trait():
    races, _, traits_by_index = load_official_races(official_dir())
    aetherborn = next(r for r in races if r["name"] == "Aetherborn")
    # Find the synthetic trait carrying the skill grant.
    skill_traits = [
        traits_by_index[t["index"]] for t in aetherborn["traits"]
        if any(p["index"] == "skill-intimidation" for p in traits_by_index[t["index"]].get("proficiencies", []))
    ]
    assert len(skill_traits) == 1
```

(Confirm Aetherborn is genuinely the right example — re-derive from Step 1's real output rather than assuming, per this plan's own established discipline.)

- [ ] **Step 3: Run to verify it fails**

- [ ] **Step 4: Implement**

The skill/tool/weapon/armor proficiency fields need conversion into SRD's `proficiencies: [{index, name, url}]` shape (matching `keen-senses`'s own shape exactly). Key conversion challenge: 5etools' skill ids are bare names (`"intimidation"`), matching SRD's convention needs a `skill-` prefix (`"skill-intimidation"`) — confirm this transformation against `reference_data.SKILL_NAMES`/`SKILL_ABILITY`'s existing id conventions (both already exist, built in earlier phases) before writing the conversion, to guarantee the ids this produces are ones `resolve.py`'s existing `skill-` prefix filter and `SKILL_ABILITY` lookup actually recognize.

Weapon/tool/armor ids need their OWN prefix-stripping (5etools' weapon ids carry a `|source` suffix, e.g. `"battleaxe|phb"` — confirmed empirically in this plan's own research — strip everything from `|` onward) and should be checked against `catalog.items`' real ids where possible (a mismatch here would silently produce an unrecognized-but-harmless proficiency id that never matches any equipment — acceptable for now, matching this project's "known, disclosed, narrow gap" pattern, but WORTH a code comment noting it, not silently assumed perfect).

Add a helper, called once per synthetic trait built for a race that has ANY of the four proficiency fields (attach to the FIRST synthetic trait, or mint a dedicated "Automatic Proficiencies" synthetic trait if a race has proficiency grants but no matching `entries` item describing them in prose — read the real data to determine which case is more common before deciding):

```python
def _proficiencies_from_5etools(race_raw: dict) -> list[dict]:
    profs = []
    for skill_id, granted in (race_raw.get("skillProficiencies") or [{}])[0].items():
        if granted is True:
            profs.append({"index": f"skill-{skill_id}", "name": f"Skill: {skill_id.title()}", "url": ""})
    # ... mirror for tool/weapon/armor, stripping "|source" suffixes and
    # using whatever prefix convention (if any) resolve.py's existing
    # sheet.proficiencies.tools/weapons/armor categorization expects —
    # re-read _categorize_proficiency in resolve.py (built Phase 3b-i)
    # before finalizing this, since it already has a real, tested
    # id-pattern-matching heuristic this data must align with.
    return profs
```

(This is intentionally left less fully pre-written than earlier tasks' snippets — the exact `_categorize_proficiency` alignment requires reading that Phase 3b-i function fresh, which may have evolved since this plan was written; ground it against the real current code, don't transcribe a guess.)

- [ ] **Step 5: Run to verify tests pass, full suite green**

- [ ] **Step 6: Sweep all races with any of the four proficiency fields, spot-check 3-4 by hand against the raw source data**

- [ ] **Step 7: Commit**

```bash
git add server/catalog/official_source.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
feat: sourcebook races' fixed skill/tool/weapon/armor grants

Synthetic per-trait proficiencies fields feed the existing Phase 3b-i
trait-proficiency-scanning code with zero resolve.py changes — skill
grants flow into proficient_skills exactly like Elf's Keen Senses
already does; tool/weapon/armor grants flow into
sheet.proficiencies.tools/weapons/armor exactly like multiclass
proficiency grants already do.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Skill/tool proficiency CHOICES, including the "any N" wildcard

**Files:**
- Modify: `server/catalog/official_source.py`, `server/catalog/choices.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_choices.py`

**Interfaces:**
- Consumes: nothing new for the named-list case (reuses `build_choice_template`/`build_choice_options` unchanged).
- Produces: a new `option_set_type` (or a new sentinel within `options_array` — plan-writing/implementation judgment call, ground against the real shape first) handling `{"any": N}` — build_choice_options gains a branch reading from the FULL set of skills/tools rather than a fixed `options` list in the envelope itself.

- [ ] **Step 1: Empirically confirm which races have a genuine CHOICE (not just a fixed grant) for skills/tools, and the "any N" shape's exact structure**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
for r in data['race']:
    sp = r.get('skillProficiencies') or []
    for entry in sp:
        if 'choose' in entry or 'any' in entry:
            print('skill choice:', r['name'], r.get('source'), entry)
    tp = r.get('toolProficiencies') or []
    for entry in tp:
        if 'any' in entry or 'choose' in entry:
            print('tool choice:', r['name'], r.get('source'), entry)
"
```

- [ ] **Step 2: Design the envelope for the "any N" case**

Read `catalog/choices.py`'s `build_choice_options` in full (already read once while writing this plan — re-read for the real current state before editing, since Task 3 of THIS plan may have already touched nearby code). The "any N" wildcard needs a source of "every possible option" that ISN'T present in the envelope itself — for skills, `reference_data.SKILL_NAMES` (already exists, used elsewhere) is the exact right source; for tools, check whether `reference_data` or `catalog.items` already has a clean "all tool ids" list, or whether one needs building.

Represent this as a NEW `option_set_type` value in the envelope this module builds (e.g. `"any_skill"`/`"any_tool"`), and add a corresponding branch in `build_choice_options`:

```python
    if set_type == "any_skill":
        return [{"id": f"skill-{s_id}", "label": name} for s_id, name in reference_data.SKILL_NAMES.items()]
```

(Ground the exact `reference_data.SKILL_NAMES` shape — dict vs list of tuples — against the real current file before writing this line.)

- [ ] **Step 3: Write failing tests, implement, verify — standard TDD loop**

Follow this plan's established Step pattern (write test against real data → confirm fail → implement → confirm pass → full suite green) for both the envelope-building side (`official_source.py`) and the `choices.py` extension.

- [ ] **Step 4: Empirical end-to-end check and commit**

```bash
git add server/catalog/official_source.py server/catalog/choices.py server/tests/test_official_source.py server/tests/test_choices.py
git commit -m "$(cat <<'EOF'
feat: "choose N of any skill/tool" proficiency choices for sourcebook races

A new option_set_type ("any_skill"/"any_tool") in build_choice_options
sources its option list from reference_data instead of the envelope's
own options array — the first choice envelope shape this project has
needed that isn't a fixed, enumerated list.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Damage resistances, immunities, vulnerabilities, condition immunities

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `sheet["damageModifiers"]: {"resistances": string[], "immunities": string[], "vulnerabilities": string[]}`, `sheet["conditionImmunities"]: string[]` — new, always-present (empty-list-when-none, per this project's established convention) sheet fields.

- [ ] **Step 1: Empirically confirm the exact shape for all four fields**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
for key in ('resist', 'immune', 'vulnerable', 'conditionImmune'):
    for r in data['race']:
        if r.get(key):
            print(key, '->', r['name'], '->', r[key])
            break
"
```

Confirm each is a plain list of strings (not nested dicts with conditions — 5etools sometimes uses conditional resistance shapes like "resistance to X unless Y", check for this and handle simple string-only entries first, flagging any conditional/complex entry found for a documented, disclosed skip — matching this project's "narrow, disclosed cut" pattern rather than silently mis-modeling a conditional resistance as unconditional).

- [ ] **Step 2: Write failing tests**

```python
def test_race_damage_modifiers_carry_through_to_the_sheet(catalog_with_official):
    draft = _fighter_acolyte_human_draft(species={"id": "aasimar-vgm", "choices": {}})
    resolution = resolve(draft, catalog_with_official)
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["necrotic", "radiant"]
    assert resolution["sheet"]["damageModifiers"]["immunities"] == []
    assert resolution["sheet"]["conditionImmunities"] == []


def test_a_race_with_no_damage_modifiers_gets_empty_lists(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)  # Human, no resistances
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}
    assert resolution["sheet"]["conditionImmunities"] == []
```

- [ ] **Step 3-4: Standard TDD loop** — implement `_damage_modifiers_from_5etools`/`_condition_immunities_from_5etools` in `official_source.py` (adding these as NEW fields directly on the race dict, e.g. `race["resist"]`/`race["immune"]`/`race["vulnerable"]`/`race["condition_immune"]`, matching 5etools' own field names rather than inventing new ones, so the conversion is a near-identity copy), then wire a small new block into `resolve()`'s `sheet = {...}` construction reading `race.get("resist", [])` etc. (guard for `race` being `None`, matching every other species-conditional field already in `resolve()`).

- [ ] **Step 5: Run full suite, empirical end-to-end check, commit**

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: damage resistances/immunities/vulnerabilities on the sheet

New sheet.damageModifiers/conditionImmunities fields, always present
(empty lists, not null, when a race grants none) — pure data
pass-through from the race record, since this app computes a
character snapshot rather than simulating combat, there's nothing
else in the engine for this data to interact with yet.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Innate spellcasting

**Files:**
- Modify: `server/catalog/official_source.py`, `server/engine/resolve.py`
- Test: `server/tests/test_official_source.py`, `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog.spells` (already exists, indexed by spell id — confirm innate spell names from 5etools data match real spell ids in the bundled/wider spell catalog; if the wider spell catalog isn't fetched yet — confirmed out of scope per the design spec — an innate spell referencing a NON-SRD spell (e.g. a spell only published in a book this project hasn't imported spell DATA for) has nowhere to resolve its name/level/school from; this task must handle that gracefully, see Step 4).
- Produces: a new list, `sheet["innateSpells"]`, one entry per race-granted innate spell, each `{spellId, level (character level it becomes available), ability, name}` (or however Step 2's real grounding shapes it).

- [ ] **Step 1: Empirically confirm the exact `additionalSpells` shape across several real records**

```bash
.venv/bin/python -c "
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
count = 0
for r in data['race']:
    sp = r.get('additionalSpells')
    if sp:
        print(r['name'], r.get('source'), '->', json.dumps(sp))
        count += 1
        if count >= 5:
            break
"
```

Confirm the shape variance across multiple real examples (fixed-ability vs. choose-ability, single spell vs. multiple, level-gated vs. always-available) before finalizing the target sheet shape — this field is the most heterogeneous of everything covered in this plan, so ground it thoroughly rather than designing against one example.

- [ ] **Step 2: Check whether referenced spell names resolve against the bundled spell catalog**

```bash
.venv/bin/python -c "
from catalog.loader import load
catalog = load()
import json
with open('/Users/yoanpetrov/.claude/dnd/.data/official/races.json') as f:
    data = json.load(f)
missing = 0
total = 0
for r in data['race']:
    sp = r.get('additionalSpells') or []
    for entry in sp:
        for level_spells in (entry.get('innate') or {}).values():
            for spell_name in level_spells:
                total += 1
                spell_id = spell_name.lower().replace(' ', '-').replace(\"'\", '')
                if spell_id not in catalog.spells:
                    missing += 1
print(f'{missing}/{total} innate spell references not found in the bundled spell catalog')
"
```

**This number determines this task's real scope.** If most innate spells resolve fine against the bundled 2014 SRD spell list (plausible, since 2014-era races' innate spells are usually 2014-era spells too), implement fully as designed. If a large fraction don't resolve (plausible for 2024/XPHB-sourced races referencing 2024-only spells this project hasn't imported spell DATA for — explicitly out of scope per the design spec), degrade gracefully: still record the innate spell's NAME as a text field (not a resolved `catalog.spells` lookup) so it's visible on the sheet, but skip any field that requires the full spell record (level/school) when the id doesn't resolve — document this exact behavior in a code comment once the real number is known, don't guess.

- [ ] **Step 3-5: Standard TDD loop, informed by Step 1/2's real findings** — implement, test against real data, full suite, empirical end-to-end check, commit.

```bash
git add server/catalog/official_source.py server/engine/resolve.py server/tests/test_official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: innate spellcasting from sourcebook races

sheet.innateSpells carries every race-granted innate spell — exact
degradation behavior for spells referencing content outside the
bundled 2014 SRD spell catalog is documented based on empirical
measurement of how common that actually is in the real data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Source filtering (`draft.sources`) and catalog endpoint labeling

**Files:**
- Modify: `server/engine/resolve.py`, `server/app.py`
- Test: `server/tests/test_resolve.py`, `server/tests/test_app.py`

**Interfaces:**
- Consumes: `Draft.sources: string[]` (already exists in the type, never read until now).
- Produces: `resolve()` rejects a `species.id` whose source isn't in `draft.sources` (when non-empty) as `unknown-species` (reusing the existing problem id — a filtered-out record and a genuinely-nonexistent record are indistinguishable from the player's point of view: "not a valid choice right now"). `GET /api/catalog` (or the class/species detail endpoints — check which one lists races) includes each race/background's `source` field for frontend grouping.

- [ ] **Step 1: Read `resolve()`'s current species-lookup code precisely**

Find `race = catalog.races.get(race_id) if race_id else None` (or equivalent) and the `unknown-species` problem it already raises when `race_id` is truthy but not found. This task adds a check right after: if `race` was found but `draft.get("sources")` is non-empty and `race.get("source")` isn't in that list (and isn't "SRD"/empty, meaning bundled data), raise the SAME `unknown-species` problem and set `race = None`, matching exactly how an unrecognized id is already handled.

- [ ] **Step 2-4: Standard TDD loop** — a test with `draft.sources = ["phb"]` correctly rejecting a `-vgm`-sourced race; a test with empty/absent `sources` correctly allowing everything (today's default, unaffected); full suite green.

- [ ] **Step 5: Expose `source` on the catalog endpoint**

Read `server/app.py`'s species/race listing endpoint (`GET /api/catalog` or `GET /api/catalog/species/<id>` — check which one lists every race for the picker) and add `source` to each entry's serialized shape, alongside `id`/`name`.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/app.py server/tests/test_resolve.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: draft.sources filters selectable races, catalog exposes source labels

Draft.sources has existed since Phase 0, never read until now — when
non-empty, a race whose source isn't in the list is treated exactly
like an unrecognized id (the same unknown-species problem, no new
problem type). Empty/absent sources means everything is available,
the same permissive default as today.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- This is the largest plan in the project's history by task count and by the genuine novelty of what several tasks build (the "any N" wildcard choice shape, innate spellcasting, damage modifiers are all first-time mechanisms, not extensions of a near-identical existing pattern the way most of Phase 3b's tasks were).
- Several tasks (3, 4, 6) deliberately leave their EXACT conversion code less fully pre-written than this project's usual plan style, with explicit instructions to re-ground against the real current code/data at implementation time rather than trust a possibly-stale snippet — this is intentional given how much this plan's OWN research already had to correct itself (the first design-spec draft undercounted the data's real structure), and matches the final lesson recorded in Phase 3b-ii's own portability-doc update: specify the invariant and the real data shape, let the implementer write the conversion code against fresh empirical grounding, rather than shipping copy-paste-ready code that's more likely to have drifted from a data shape this varied.
- Task 6 (innate spellcasting) has a genuine, unresolved-until-Step-2 scope question (how many innate spells reference content outside the bundled spell catalog) — flagged explicitly rather than guessed at plan-writing time.
- Phase 4b (backgrounds) and 4c (feats) are separate future plans, not part of this one.
