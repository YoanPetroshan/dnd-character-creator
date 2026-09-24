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
- **`chargen` is a sibling of `server/`, not a subpackage of it — `import chargen` fails from every real way this server runs.** Confirmed empirically while setting up this plan's worktree: `cd server && .venv/bin/python -c "from chargen.sources import official_dir"` raises `ModuleNotFoundError`, both under `python app.py` (production) and `python -m pytest` (tests, despite `server/tests/conftest.py`'s existing `sys.path` insert — that insert only adds `server/` itself, not its parent). **`server/catalog/official_source.py` is the ONE place that fixes this** — it inserts the repo root onto `sys.path` at import time, then imports AND RE-EXPORTS `official_dir`/`has_official` from `chargen.sources` (see Task 1 Step 4). Every other file in this plan — `catalog/loader.py`, every test file, everything — imports `official_dir`/`has_official`/`load_official_races` FROM `catalog.official_source`, never directly from `chargen.sources`. This is a single point of truth, not a convention to remember per-file: **never write `from chargen.sources import ...` anywhere in this plan except inside `official_source.py` itself** — doing so elsewhere reintroduces the `ModuleNotFoundError`, since nothing guarantees `official_source.py`'s sys.path fix ran first.

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
# official_dir/has_official are imported FROM official_source (a
# re-export), not from chargen.sources directly — official_source.py is
# the one place that fixes sys.path so `chargen` (a sibling of server/,
# not a subpackage) is importable at all; importing chargen.sources
# directly here would fail with ModuleNotFoundError before that fix runs.
from catalog.official_source import official_dir, has_official, load_official_races

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
Expected: FAIL with `ModuleNotFoundError: No module named 'catalog.official_source'` — `catalog/official_source.py` doesn't exist yet. (This is the only expected failure mode. If you instead see a `chargen`-related ModuleNotFoundError, something imported `chargen.sources` directly instead of via `catalog.official_source` — check the test file matches Step 2 exactly.)

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

chargen lives at the repo root, a SIBLING of server/ — not a subpackage
of it. Every real way this server runs (`cd server && python app.py` in
production, `cd server && pytest` for tests) has `server/` as the
working directory, which does not put the repo root on sys.path. The
insert below is what makes `from chargen.sources import ...` resolve —
this module is the ONLY place in the whole codebase that imports
chargen.sources directly; official_dir/has_official are re-exported
from here (see the import line right below) so every caller (loader.py,
every test) imports them FROM catalog.official_source instead, and
never needs to know chargen lives one level up at all.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

_repo_root = Path(__file__).resolve().parents[2]  # server/catalog/official_source.py -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402  (must follow the sys.path fix above)


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

Confirm the subrace shape (likely has a `raceName`/`raceSource` back-reference to its parent race, plus its own `ability`/`entries` following the same conventions as races) and the bundled SRD subrace shape (`chargen/data/srd/5e-SRD-Subraces.json`, at the REPO ROOT, not under `server/` — read one record) for the target shape — `catalog/loader.py`'s SRD subrace conversion should already show the exact fields needed (likely `index, name, race:{index,name,url}, ability_bonuses, racial_traits, ...` — verify, don't assume). Implement `_subrace_from_5etools(raw, traits_by_index) -> dict | None` mirroring `_race_from_5etools`'s structure, and wire it into `load_official_races` to populate the `subraces` return value. Update the module's own tests (Step 2) with a real subrace case once this exists.

- [ ] **Step 6: Wire into `catalog/loader.py`**

Read `server/catalog/loader.py` in full — it's short (confirmed at plan-writing time: `_DATA_DIR = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"`, i.e. the repo root's `chargen/data/srd/`, and a single parameterless `load() -> Catalog` function returning `Catalog(classes=..., races=_index_by(_load("5e-SRD-Races.json")), subraces=_index_by(_load("5e-SRD-Subraces.json")), traits=_index_by(_load("5e-SRD-Traits.json")), ...)` in one `return` statement — re-confirm this hasn't changed since, then replace `load()` with:

```python
def load() -> Catalog:
    from .official_source import load_official_races, official_dir

    official_races, official_subraces, official_traits = load_official_races(official_dir())
    races = {**_index_by(_load("5e-SRD-Races.json")), **_index_by(official_races)}
    subraces = {**_index_by(_load("5e-SRD-Subraces.json")), **_index_by(official_subraces)}
    traits = {**_index_by(_load("5e-SRD-Traits.json")), **official_traits}  # official_traits is already a dict — see load_official_races' own return type

    return Catalog(
        classes=_index_by(_load("5e-SRD-Classes.json")),
        levels=_load("5e-SRD-Levels.json"),
        features=_index_by(_load("5e-SRD-Features.json")),
        subclasses=_index_by(_load("5e-SRD-Subclasses.json")),
        races=races,
        subraces=subraces,
        traits=traits,
        backgrounds=_index_by(_load("5e-SRD-Backgrounds.json")),
        items=_index_by(_load("5e-SRD-Equipment.json")),
        spells=_index_by(_load("5e-SRD-Spells.json")),
    )
```

The `from .official_source import ...` is deliberately a LOCAL import inside `load()`, not a top-level one — `official_source.py` does its own `sys.path` mutation at import time (a real but narrow side effect, confirmed necessary in Global Constraints), and keeping that side effect out of `loader.py`'s own top-level import list keeps it obviously scoped to only the one function that needs it. `official_dir` here is `catalog.official_source`'s re-export, not `chargen.sources` imported directly (Global Constraints: never import `chargen.sources` directly outside `official_source.py`). If the real current `load()` has evolved from the shape above by the time this task runs, adapt the same merge pattern to whatever it actually looks like — the load-bearing part is the three-way dict merge (SRD ∪ official, official wins ties only in the impossible case of an id collision, which Global Constraints' source-qualified-id rule guarantees never happens), not the exact surrounding syntax.

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


```

A second test — confirming the choice actually flows through `resolve()` end to end — belongs in `server/tests/test_resolve.py` instead, not this file: that file already has its own module-scoped `catalog` fixture (`@pytest.fixture(scope="module") def catalog(): return load()`, at the top of `test_resolve.py`), which after Task 1's `loader.py` wiring automatically includes official data when present on the machine — no separate fixture needed. Add there:

```python
@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_ability_bonus_choice_flows_through_resolve(catalog):
    # A real resolve() test — build a draft selecting 2 of the 5 offered
    # abilities for Aetherborn's choice envelope, confirm it applies. Ground
    # the exact draft/assertions against real data from this task's own
    # Step 1 output before writing this — don't guess the race name/values.
    ...
```

(`has_official` needs importing there too — `from catalog.official_source import has_official`, same rule as everywhere else in this plan.)

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

### Task 3b: Close a pre-existing gap — `resolve()` never consumed tool/weapon/armor proficiencies from race/subrace traits

**Why this task exists:** Task 3's own review (both the implementer and an independent reviewer, verified two ways — direct code reading and an empirical `resolve()` repro) found that `server/engine/resolve.py` has NEVER forwarded tool/weapon/armor proficiency ids out of race/subrace traits into `sheet.proficiencies` — only `skill-` prefixed ids are read from traits. This is a PRE-EXISTING gap, not introduced by this plan: it silently affects the BUNDLED SRD data too (confirmed: SRD Dwarf's "Dwarven Combat Training" trait grants battleaxe/handaxe/light-hammer/warhammer proficiency, and it has never once reached `sheet.proficiencies.weapons`). It went unnoticed until now because nothing before this plan wrote a test asserting a race's weapon/tool/armor grant actually lands on the sheet. Given this plan's explicit goal is full mechanical fidelity (not partial — the user's own words: "искам всичко да е вътре... това беше задачата от началото"), Task 3's correctly-shaped-but-uncommitted data must not ship inert. This task closes the gap for EVERY race (SRD and sourcebook alike), and fixes a related weapon-id convention bug Task 3's review found along the way.

**Files:**
- Modify: `server/engine/resolve.py`, `server/catalog/official_source.py`
- Test: `server/tests/test_resolve.py`, `server/tests/test_official_source.py`

**Interfaces:**
- Consumes: the EXISTING `_categorize_proficiency(prof_id: str) -> None` nested function inside `resolve()` (already handles the armor/weapon/tool bucketing correctly, including its own `_SPECIFIC_WEAPON_PROFICIENCY_IDS` set — reused unmodified).
- Produces: `sheet.proficiencies.armor/weapons/tools` now ALSO include grants from race/subrace traits, for every race (SRD and sourcebook).

- [ ] **Step 1: Ground the exact current code before touching it**

Read `server/engine/resolve.py` around the `proficient_skills`/`proficient_armor`/`proficient_weapons`/`proficient_tools` block (confirmed at plan-writing time to span roughly lines 944-1025 — re-locate if line numbers have shifted). Confirm the exact current shape:

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

    proficient_armor: set[str] = set()
    proficient_weapons: set[str] = set()
    proficient_tools: set[str] = set()

    _SPECIFIC_WEAPON_PROFICIENCY_IDS = {
        "shortswords", "clubs", "crossbows-light", "daggers", "darts", "hand-crossbows",
        "javelins", "longswords", "maces", "quarterstaffs", "rapiers", "scimitars",
        "sickles", "slings", "spears",
    }

    def _categorize_proficiency(prof_id: str) -> None:
        if prof_id.startswith("skill-") or prof_id.startswith("saving-throw-"):
            return
        if "armor" in prof_id or prof_id == "shields":
            proficient_armor.add(prof_id)
        elif "weapon" in prof_id or prof_id in _SPECIFIC_WEAPON_PROFICIENCY_IDS:
            proficient_weapons.add(prof_id)
        else:
            proficient_tools.add(prof_id)
```

Note `_SPECIFIC_WEAPON_PROFICIENCY_IDS` already contains `"crossbows-light"` — this is the authoritative id resolve.py recognizes for that weapon, and it is the OPPOSITE ordering from what Task 3's naive pluralization would produce ("light-crossbows" — wrong, silently uncategorized as a "tool" instead of a weapon, since neither "weapon" nor a member of `_SPECIFIC_WEAPON_PROFICIENCY_IDS` matches it).

- [ ] **Step 2: Write failing tests against a REAL bundled SRD race first**

This is the highest-value test in this task — proving a real, currently-broken SRD behavior gets fixed, independent of any sourcebook data (so it runs unconditionally, no `has_official()` skip needed):

```python
def test_dwarf_dwarven_combat_training_weapon_proficiencies_reach_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    weapons = set(resolution["sheet"]["proficiencies"]["weapons"])
    # Dwarven Combat Training (PHB): battleaxe, handaxe, light hammer, warhammer.
    # Verify the exact ids against chargen/data/srd/5e-SRD-Traits.json's
    # "dwarven-combat-training" record before trusting this literal — do
    # not assume from memory.
    assert {"battleaxes", "handaxes", "light-hammers", "warhammers"} <= weapons
```

(Ground the exact expected id set against the real bundled trait record — `python -c "import json; d=json.load(open('chargen/data/srd/5e-SRD-Traits.json')); print([t for t in d if t['index']=='dwarven-combat-training'])"` from the repo root — before trusting the literal above; SRD's own trait data may already use whatever id convention `_categorize_proficiency` expects, or may not, which is exactly what this test needs to prove either way.)

Add a second test for a race with NO weapon/tool/armor trait grants (e.g. Human) confirming no regression:

```python
def test_human_has_no_extra_weapon_tool_armor_from_traits(catalog):
    draft = _fighter_acolyte_human_draft()
    resolution = resolve(draft, catalog)
    # Human has no traits granting weapon/tool/armor proficiencies — Fighter's
    # own class grants (martial-weapons, simple-weapons, etc.) are untouched,
    # this just confirms nothing EXTRA leaks in from trait-scanning.
    ...  # ground the exact expected set against Fighter's real class proficiencies before writing this assertion
```

- [ ] **Step 3: Run to verify Step 2's tests fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k dwarven_combat_training`
Expected: FAIL — `weapons` set is currently missing the Dwarven Combat Training grants entirely (this is the bug).

- [ ] **Step 4: Fix `resolve.py`**

Add a second pass over the SAME `trait_refs` the skill-scanning block already computes, calling the existing `_categorize_proficiency` for every non-skill entry. Since `_categorize_proficiency` is defined AFTER the skill-scanning block (it needs `proficient_armor`/`proficient_weapons`/`proficient_tools` to already exist), add this right after `_categorize_proficiency`'s own definition, before the class-level prof-choice loop that already calls it:

```python
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            for p in trait.get("proficiencies", []):
                if not p["index"].startswith("skill-"):
                    _categorize_proficiency(p["index"])
```

This recomputes `trait_refs` a second time (a small, disclosed duplication of the identical computation in the skill-scanning block above it) rather than restructuring the function to compute it once and reuse it across two now-separated blocks — matches this file's own already-established tolerance for small, disclosed duplication elsewhere (e.g. `_class_label()`, per the architecture doc's own "known gaps" section) over a broader refactor this task doesn't need. If you find a cleaner way that doesn't risk the working skill-scanning code above it, that's fine too — just keep the diff minimal and don't restructure code outside this concern.

- [ ] **Step 5: Run to verify Step 2's tests pass, then full suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "dwarven_combat_training or human_has_no_extra"`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (332 baseline + your new tests), no regressions. Pay special attention to any existing test that asserts an exact (not `in`-based) proficiencies list for any race with a proficiency-granting trait — none were found during this plan's own grounding pass (`grep -rn "\"weapons\"\]" tests/*.py` found only `in`-based assertions), but re-verify.

- [ ] **Step 6: Fix the weapon-id convention bug Task 3's review found**

Task 3's review found a concrete mismatch: `official_source.py`'s weapon-id conversion (pluralize-and-strip-source) produces `"light-crossbows"` for 5etools' `"light crossbow|phb"`, but the id `_categorize_proficiency` actually recognizes (per `_SPECIFIC_WEAPON_PROFICIENCY_IDS`, Step 1) is `"crossbows-light"` — meaning this specific weapon would now (after Step 4's fix) get silently miscategorized into `tools` instead of `weapons` for any sourcebook race granting it, once official data is fetched.

In `official_source.py`'s weapon-id conversion function (built in Task 3), add a lookup against the known `_SPECIFIC_WEAPON_PROFICIENCY_IDS` set for exact/near matches before falling back to the generic pluralize-and-strip logic — e.g., a small dict mapping known 5etools weapon slugs to their `_categorize_proficiency`-recognized id where they diverge (starting with the one confirmed case: `"light-crossbow"` → `"crossbows-light"`), with a code comment explaining why (cite Task 3's review finding). Do NOT try to exhaustively solve every possible weapon-id naming mismatch in the wider data — this task fixes the ONE concrete case the review found and verified; further mismatches, if any turn up later, are the same kind of "narrow, disclosed gap" this project already accepts elsewhere (a mismatched id just means that one specific weapon's proficiency silently lands in the wrong bucket — visible/inspectable, not a crash, not data loss).

Write a test confirming this specific conversion:

```python
def test_light_crossbow_weapon_id_matches_resolve_pys_recognized_convention():
    # Ground: 5etools' "light crossbow|phb" must convert to the SAME id
    # _categorize_proficiency's _SPECIFIC_WEAPON_PROFICIENCY_IDS set
    # recognizes ("crossbows-light"), not the naive pluralized form
    # ("light-crossbows") — confirmed mismatched during Task 3's review.
    ...  # call whichever official_source.py function does this conversion directly, assert it returns "crossbows-light" for this input
```

- [ ] **Step 7: Run full suite, empirical end-to-end check, commit**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'dwarf', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
print('Dwarf weapon proficiencies:', sorted(r['sheet']['proficiencies']['weapons']))
print('problems:', r['problems'])
"
```

Confirm the Dwarf's Dwarven Combat Training weapons now genuinely appear alongside Fighter's own martial/simple-weapons grants, with zero problems.

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/catalog/official_source.py server/tests/test_resolve.py server/tests/test_official_source.py
git commit -m "$(cat <<'EOF'
fix: resolve() now consumes tool/weapon/armor proficiencies from traits

Race/subrace traits could always carry tool/weapon/armor proficiency
grants (SRD's own Dwarven Combat Training is a real, bundled example),
but resolve()'s trait-scanning only ever forwarded skill- prefixed
entries into the sheet — armor/weapon/tool grants from traits have
never reached sheet.proficiencies, for any race, SRD included. Found
during Phase 4a's own review process, not introduced by it. Fixed by
extending the existing trait-scanning pass to also call the existing
_categorize_proficiency for non-skill entries. Also fixes a weapon-id
convention mismatch in official_source.py's conversion (5etools'
"light crossbow" now converts to "crossbows-light", matching
_categorize_proficiency's own recognized id, not a naive pluralized
form that would have silently miscategorized it as a tool).

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

### Task 4b: Close a pre-existing gap — race-sourced proficiency CHOICES never reach the sheet

**Why this task exists:** Task 4's own review (implementer + independent reviewer, verified by direct code reading AND a live `resolve()` repro against real bundled SRD data) found TWO pre-existing gaps in `server/engine/resolve.py`, analogous to Task 3's gap but for CHOICE-based (not fixed) race proficiency grants:
1. `_species_choice_templates` (confirmed at plan-writing time to span lines 267-305) reads a trait's `trait_specific.subtrait_options` and race/subrace `language_options`, but NEVER reads a trait's `proficiency_choices` field — so no Choice template is ever built for it, for ANY race. Confirmed empirically: bundled SRD Half-Elf's real "Skill Versatility" trait (`choose 2 of {every skill}`) and Dwarf's real "Tool Proficiency" trait (`choose 1 of {smith's, brewer's, mason's tools}`) both have this exact field in `chargen/data/srd/5e-SRD-Traits.json`, confirmed present, and neither currently produces a Choice the player can even see.
2. Even if the template existed, the merge logic that turns a Choice's `selected` values into `proficient_skills`/`sheet.proficiencies` is hardcoded to only look at `c["source"]["kind"] == "class"` (confirmed at two call sites: the `proficient_skills` loop and the `_categorize_proficiency` prof-choice loop) — species-sourced choices (`kind == "species"`, the source `_species_choice_templates` already uses) are unconditionally excluded from both.

This predates the whole plan and affects bundled SRD data (Half-Elf, Dwarf) today, not just sourcebook races. Given this plan's explicit full-fidelity goal, this needs closing before race proficiency CHOICES (Task 4's own contribution) can be called complete end-to-end — mirroring the Task 3 → Task 3b precedent exactly.

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: the EXISTING `build_choice_template`/`build_choice_options` machinery (already handles the real `proficiency_choices` envelope shape — confirmed identical `options_array` shape to every other choice type, verified against both real SRD examples below) and the EXISTING `_categorize_proficiency` helper (Task 3b).
- Produces: `sheet.proficiencies`/`proficient_skills` now include selections from race-sourced proficiency CHOICES, for every race (SRD and sourcebook).

- [ ] **Step 1: Ground the exact current code and real data**

Confirmed at plan-writing time — `server/engine/resolve.py`'s `_species_choice_templates` (lines 267-305):

```python
def _species_choice_templates(catalog: Catalog, race: dict, race_id: str, subrace: dict | None) -> list[dict]:
    templates = []
    trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
    for ref in trait_refs:
        trait = catalog.traits.get(ref["index"])
        if not trait:
            continue
        envelope = (trait.get("trait_specific") or {}).get("subtrait_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:trait:{trait['index']}"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        tpl = build_choice_template(envelope, cid, source, trait["name"], description=_join_desc(trait.get("desc")))
        if tpl:
            templates.append(tpl)

    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        if not src:
            continue
        envelope = src.get("language_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:languages"
        if src is subrace:
            cid = f"species:{race_id}:subspecies:{src_id}:languages"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} additional language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Bonus Language", description=description)
        if tpl:
            templates.append(tpl)

    return templates
```

Real bundled SRD data (`chargen/data/srd/5e-SRD-Traits.json`) confirmed at plan-writing time — Dwarf's "Tool Proficiency" trait:

```json
{"index": "tool-proficiency", "name": "Tool Proficiency", "proficiency_choices": {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "options_array", "options": [{"option_type": "reference", "item": {"index": "smiths-tools", "name": "Smith's Tools", ...}}, ...]}}}
```

Half-Elf's "Skill Versatility" trait: identical shape, `choose: 2`, options listing every `skill-*` id. Both are the SAME `options_array` envelope `build_choice_template` already handles — this task needs no new envelope logic, only reading the field and building the template, exactly mirroring the existing `subtrait_options` block immediately above it in the same function.

The two merge sites (confirmed at plan-writing time, re-locate if line numbers have shifted from Task 4's own additions):

```python
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
```

and, further down (inside the `_categorize_proficiency`-calling block):

```python
    for c in choices:
        if c["source"]["kind"] == "class" and "prof-choice-" in c["id"]:
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
```

- [ ] **Step 2: Write failing tests against REAL bundled SRD races first**

No `has_official()` skip needed — this bug affects SRD data unconditionally:

```python
def test_half_elf_skill_versatility_choice_is_offered_and_flows_through_resolve(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "half-elf", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    versatility_cid = next((cid for cid in cids if "skill-versatility" in cid), None)
    assert versatility_cid is not None, f"expected a Skill Versatility choice, got choice ids: {cids}"

    # Re-resolve with a real selection for it and confirm it lands on the sheet.
    draft["species"]["choices"][versatility_cid] = ["skill-arcana", "skill-history"]
    resolution2 = resolve(draft, catalog)
    assert {"skill-arcana", "skill-history"} <= set(resolution2["sheet"]["proficiencies"]["skills"])
    # (Confirm resolution2["sheet"]["proficiencies"]["skills"]'s exact real
    # field name/shape against a passing existing test in test_resolve.py
    # before trusting this literal.)


def test_dwarf_tool_proficiency_choice_flows_into_sheet_tools(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    tool_cid = next((cid for cid in cids if "tool-proficiency" in cid), None)
    assert tool_cid is not None, f"expected a Tool Proficiency choice, got choice ids: {cids}"

    draft["species"]["choices"][tool_cid] = ["smiths-tools"]
    resolution2 = resolve(draft, catalog)
    assert "smiths-tools" in resolution2["sheet"]["proficiencies"]["tools"]
```

(Ground the exact `_fighter_acolyte_human_draft` species-override call shape and the exact sheet field paths against `test_resolve.py`'s own existing, passing tests before trusting these literals.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "skill_versatility or tool_proficiency_choice"`
Expected: FAIL — no Skill Versatility / Tool Proficiency choice id appears in `resolution["choices"]` at all today (gap 1), and even a manually-injected selection for a guessed cid wouldn't reach the sheet (gap 2).

- [ ] **Step 4: Fix gap 1 — build the Choice template**

Add a third block to `_species_choice_templates`, mirroring the existing `subtrait_options` block's structure exactly, reading `proficiency_choices` instead:

```python
        envelope = trait.get("proficiency_choices")
        if envelope:
            cid = f"species:{race_id}:trait:{trait['index']}:proficiency-choice"
            source = {"kind": "species", "id": race_id, "label": race["name"]}
            choose = envelope.get("choose", 1)
            description = f"Choose {choose} proficienc{'ies' if choose != 1 else 'y'} of your choice."
            tpl = build_choice_template(envelope, cid, source, trait["name"], description=description)
            if tpl:
                templates.append(tpl)
```

**The `:proficiency-choice` suffix on the cid is load-bearing, not decorative** — it must be DISTINCT from the existing `subtrait_options` block's cid for the same trait (`f"species:{race_id}:trait:{trait['index']}"`, no suffix) to avoid two different Choice templates colliding on the same id if a trait ever had both fields (not observed in real bundled data, but nothing guarantees it can't happen for a sourcebook trait later). It must ALSO be independently greppable as a distinct substring (`"proficiency-choice"`) so Step 5's merge-site fix can distinguish a genuine proficiency choice from a `subtrait_options` selection (e.g. Draconic Ancestry's damage-type/ancestry choice, which is NOT a proficiency and must never be fed into `_categorize_proficiency`) or a bonus-language selection — mirroring exactly how the existing class-side merge already distinguishes proficiency choices from other class choices via the `"prof-choice-"` substring in `c["id"]`.

Place this new block either right after or right before the existing `subtrait_options` block inside the same `for ref in trait_refs:` loop — both read from the same `trait` variable already in scope, so no new loop is needed.

- [ ] **Step 5: Fix gap 2 — the two merge sites**

`proficient_skills` loop — extend the kind check (the existing `.startswith("skill-")` filter already correctly excludes non-skill selections from ANY source, so no id-substring narrowing is needed here, only the kind extension):

```python
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] in ("class", "species"):
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
```

Prof-choice loop — here the id-substring narrowing IS needed (a species-sourced `subtrait_options` or bonus-language selection must never reach `_categorize_proficiency`, which has no "is this even a real proficiency id" guard and would silently miscategorize a damage-type string like `"fire"` or a language id into `tools`). Add a parallel condition, matching this file's own established style of explicit, separate blocks rather than a merged conditional:

```python
    for c in choices:
        if c["source"]["kind"] == "class" and "prof-choice-" in c["id"]:
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "species" and "proficiency-choice" in c["id"]:
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
```

(If you find a cleaner way to express this without duplicating the inner loop body, that's fine — just keep the id-substring narrowing for the species branch, it's the load-bearing part, not the exact syntax.)

- [ ] **Step 6: Run to verify Step 2's tests pass, then full suite**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "skill_versatility or tool_proficiency_choice"`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (348 baseline + your new tests). Specifically re-check any existing test that exercises Half-Elf, Dwarf, or Draconic Ancestry (Dragonborn) — a subtrait_options-based race — to confirm the new proficiency-choice block and the merge-site kind extension don't change THEIR behavior (Dragonborn's Draconic Ancestry choice must keep working exactly as before, since it's a `subtrait_options` choice, not a `proficiency_choices` one, and must never be miscategorized by the new species branch in Step 5 — the `"proficiency-choice" in c["id"]` check is precisely what prevents this, verify it actually does).

- [ ] **Step 7: Empirical end-to-end check, commit**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
draft = {
    'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'half-elf', 'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
}
r = resolve(draft, catalog)
versatility = [c for c in r['choices'] if 'skill-versatility' in c['id']]
print('Skill Versatility choice offered:', bool(versatility))
print('problems:', r['problems'])
"
```

Confirm the Skill Versatility choice is genuinely offered to the player, zero problems.

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: resolve() now offers and consumes race-sourced proficiency choices

_species_choice_templates read a trait's trait_specific.subtrait_options
and language_options, but never its proficiency_choices field — so
bundled SRD Half-Elf's real "Skill Versatility" trait (choose 2 skills)
and Dwarf's "Tool Proficiency" trait (choose 1 tool) never produced a
Choice the player could even see. Even manually injecting a selection
wouldn't have helped: the Choice.selected merge into proficient_skills
and _categorize_proficiency was hardcoded to class-sourced choices
only. Found during Task 4's own review process, not introduced by it —
mirrors Task 3b's fix for FIXED (non-choice) race proficiency grants.
Both merge sites now also accept species-sourced choices, with an id
substring check (":proficiency-choice") preventing a non-proficiency
species choice (e.g. Dragonborn's Draconic Ancestry damage-type pick)
from being miscategorized.

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

Both tests below go in `server/tests/test_resolve.py`, using that file's own existing module-scoped `catalog` fixture (`return load()` — automatically official-data-aware after Task 1's `loader.py` wiring, no separate fixture needed) and its existing `_fighter_acolyte_human_draft` helper:

```python
@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_race_damage_modifiers_carry_through_to_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "aasimar-vgm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["necrotic", "radiant"]
    assert resolution["sheet"]["damageModifiers"]["immunities"] == []
    assert resolution["sheet"]["conditionImmunities"] == []


def test_a_race_with_no_damage_modifiers_gets_empty_lists(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)  # Human, no resistances
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}
    assert resolution["sheet"]["conditionImmunities"] == []
```

(`from catalog.official_source import has_official` needs adding to `test_resolve.py`'s imports — same single-point-of-truth rule as everywhere else in this plan. The first test's exact Aasimar-VGM resistances literal must be re-confirmed against Step 1's real output before trusting it here.)

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
