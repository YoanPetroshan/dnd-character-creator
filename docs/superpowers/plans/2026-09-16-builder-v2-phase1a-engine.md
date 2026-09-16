# Builder v2 Phase 1a — Catalog & Resolve Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Phase 0's hardcoded `/api/resolve` stub with a real engine:
a catalog loader/normalizer for the bundled SRD JSON, a `resolve(draft,
catalog) -> Resolution` implementing the architecture spec's single-pass
rules pipeline for a **single-class, level-1** character, and a YAML export
endpoint. This is the backend half of Phase 1 ("vertical slice") from the
architecture spec's phasing (§10) — no frontend changes are in scope here;
that is a separate follow-up plan (Phase 1b) once this is done and reviewed.

**Architecture:** Two new Python packages under `server/`: `server/catalog/`
(loads and indexes `chargen/data/srd/*.json`, and normalizes the SRD's
"choose N of..." envelopes into `Choice` templates) and `server/engine/`
(pure derived-stat math plus the `resolve()` orchestration function).
`server/export.py` turns a `Resolution` into a YAML string.  `server/app.py`
is updated to wire these in, replacing the Phase-0 stub, and gains
`GET /api/catalog[...]` and `POST /api/export/yaml` endpoints.

**Tech Stack:** Python 3, Flask (already in place from Phase 0), `pyyaml`
(new dependency for YAML export), pytest.

## Global Constraints

- **Single class, level 1 only.** If `draft.classes` has more than one
  entry, that's a `problems[]` entry (`"multiclass-unsupported"`) and only
  the first entry is used. If the entry's `level` isn't 1, that's a
  `problems[]` entry (`"level-unsupported"`) and level 1's data is used
  anyway (never crash — always return the best coherent Resolution the
  engine can, with `problems[]` telling the caller what's not honored).
  Multiclassing and leveling above 1 are explicitly Phase 3 scope.
- **No subclass selection.** `draft.classes[0].subclassId` is read (it's
  part of the Phase 0 `ClassSelection` type) but Phase 1 makes no UI to set
  it, so treat it as "no subclass chosen." Any level-1 SRD feature gated to
  a specific subclass (`feature.subclass` is set) is filtered out of choice
  generation rather than guessed at.
- **No equipment resolution.** `starting_equipment_options` (on both
  classes and backgrounds) and any choice envelope whose
  `from.option_set_type` is `"equipment_category"` are never turned into
  `Choice`s in this plan — equipment is Phase 2 scope. `build_choice_options`
  (Task 3) returns `None` for these, and every caller must skip a `None`
  result rather than emit a broken/empty choice.
- **Only bundled SRD data — no local sourcebook packs.** The catalog loader
  reads only `chargen/data/srd/*.json`. The 5etools adapter and any local
  pack directory (`~/.claude/dnd/.data/official` or similar) are Phase 4
  scope — do not add code that reads from them in this plan.
- **Ability score keys are UPPERCASE strings** (`"STR"`, `"DEX"`, `"CON"`,
  `"INT"`, `"WIS"`, `"CHA"`) everywhere in this plan's Python code — engine
  internals, `derived.abilityModifiers`/`savingThrows`, and
  `sheet.abilities`. This matches the frontend's already-shipped
  `Draft.abilities.base: Record<Ability, number>` type
  (`frontend/src/types.ts`, `Ability = "STR"|"DEX"|"CON"|"INT"|"WIS"|"CHA"`)
  exactly — the SRD JSON itself uses lowercase ability-score `index` values
  (`"str"`, `"dex"`, ...), so every place this plan reads an ability index
  out of SRD data must `.upper()` it before using it as a dict key. Getting
  this backwards silently breaks ability-score lookups (a `.get(key,
  default)` miss returns the default instead of erroring), so tests must
  assert on the actual computed values, never just "no exception was
  raised."
- **The `Resolution` JSON shape is unchanged from Phase 0.** Every field
  name and nesting in `frontend/src/types.ts`'s `Resolution`/`Choice`/
  `ChoiceSource`/`ChoiceOption`/`Problem`/`WarningItem`/`Pruned` types stays
  exactly as Phase 0 defined it — this plan changes what `/api/resolve`
  *computes*, never the shape of what it returns. In particular: `choices[]`
  entries always carry `id`, `source: {kind, id, label, level?}`, `label`,
  `description`, `count`, `options: [{id, label, description?, disabled?,
  disabledReason?}]`, `selected`, `status: "pending"|"resolved"`. (Phase 1
  never produces `status: "invalid"` — that's a later phase.)
- **`resolve()` must never throw on an incomplete draft.** The Phase
  0 frontend's default `emptyDraft` (`classes: []`, no `background.id`, no
  `species.id`) is a completely legitimate input — every existing Phase 0
  page must keep working (showing "no choices yet") against it, not error.
  Only genuinely malformed data (an unknown class/background/species id, a
  score outside 1-30, more than one class) becomes a `problems[]` entry;
  "nothing selected yet" is not a problem.
- **`server/tests/test_resolve_stub.py` is deleted in this plan** (Task 7) —
  its assertions describe Phase 0's hardcoded stub data, which no longer
  exists once `/api/resolve` calls the real engine. Its replacement,
  `server/tests/test_app.py`, is written in the same task so backend test
  coverage of the Flask endpoints is never gapped.

---

### Task 1: Reference data — languages and skill-to-ability table

**Files:**
- Create: `server/catalog/__init__.py`
- Create: `server/catalog/reference_data.py`
- Create: `server/tests/test_reference_data.py`

**Interfaces:**
- Produces: `reference_data.LANGUAGES: list[dict]` (`{"index": str, "name":
  str}`, 16 entries), `reference_data.SKILL_ABILITY: dict[str, str]` (18
  entries, skill `index` → UPPERCASE ability), `reference_data.ABILITIES:
  list[str]` (`["STR","DEX","CON","INT","WIS","CHA"]`) — every later task in
  this plan imports these.

- [ ] **Step 1: Write `server/catalog/__init__.py`** (empty — just makes
  `catalog` a package)

```python
```

- [ ] **Step 2: Write `server/catalog/reference_data.py`**

```python
"""Small, hand-maintained reference tables for open 5e SRD content that
Backgrounds.json references via a resource_list URL (e.g.
"/api/2014/languages") but that isn't bundled as its own file under
chargen/data/srd/ — languages are pure open-content SRD material, not
sourcebook-specific, so hardcoding the standard list here is safe. Also
carries the skill→ability mapping, which the bundled data never states
explicitly as its own table (it only shows up implicitly, skill by skill,
inside each class's proficiency_choices).
"""
from __future__ import annotations

LANGUAGES: list[dict[str, str]] = [
    {"index": "common", "name": "Common"},
    {"index": "dwarvish", "name": "Dwarvish"},
    {"index": "elvish", "name": "Elvish"},
    {"index": "giant", "name": "Giant"},
    {"index": "gnomish", "name": "Gnomish"},
    {"index": "goblin", "name": "Goblin"},
    {"index": "halfling", "name": "Halfling"},
    {"index": "orc", "name": "Orc"},
    {"index": "abyssal", "name": "Abyssal"},
    {"index": "celestial", "name": "Celestial"},
    {"index": "draconic", "name": "Draconic"},
    {"index": "deep-speech", "name": "Deep Speech"},
    {"index": "infernal", "name": "Infernal"},
    {"index": "primordial", "name": "Primordial"},
    {"index": "sylvan", "name": "Sylvan"},
    {"index": "undercommon", "name": "Undercommon"},
]

# SRD skill `index` -> the UPPERCASE ability score it's keyed off of.
# Verified directly against every skill index referenced anywhere in
# chargen/data/srd/5e-SRD-Classes.json's proficiency_choices (18 total).
SKILL_ABILITY: dict[str, str] = {
    "skill-acrobatics": "DEX",
    "skill-animal-handling": "WIS",
    "skill-arcana": "INT",
    "skill-athletics": "STR",
    "skill-deception": "CHA",
    "skill-history": "INT",
    "skill-insight": "WIS",
    "skill-intimidation": "CHA",
    "skill-investigation": "INT",
    "skill-medicine": "WIS",
    "skill-nature": "INT",
    "skill-perception": "WIS",
    "skill-performance": "CHA",
    "skill-persuasion": "CHA",
    "skill-religion": "INT",
    "skill-sleight-of-hand": "DEX",
    "skill-stealth": "DEX",
    "skill-survival": "WIS",
}

ABILITIES: list[str] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
```

- [ ] **Step 3: Write `server/tests/test_reference_data.py`**

```python
from catalog import reference_data


def test_languages_has_sixteen_entries_with_unique_ids():
    ids = [lang["index"] for lang in reference_data.LANGUAGES]
    assert len(ids) == 16
    assert len(set(ids)) == 16
    assert "common" in ids
    assert "draconic" in ids


def test_skill_ability_has_eighteen_entries_all_valid_abilities():
    assert len(reference_data.SKILL_ABILITY) == 18
    for ability in reference_data.SKILL_ABILITY.values():
        assert ability in reference_data.ABILITIES


def test_skill_ability_known_mappings():
    assert reference_data.SKILL_ABILITY["skill-athletics"] == "STR"
    assert reference_data.SKILL_ABILITY["skill-stealth"] == "DEX"
    assert reference_data.SKILL_ABILITY["skill-arcana"] == "INT"
    assert reference_data.SKILL_ABILITY["skill-perception"] == "WIS"
    assert reference_data.SKILL_ABILITY["skill-persuasion"] == "CHA"


def test_abilities_are_the_six_srd_abilities_uppercase():
    assert reference_data.ABILITIES == ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_reference_data.py -v`
Expected: all 4 PASS (no implementation to fail against — this is reference
data, not TDD in the red/green sense, but still run the tests to confirm
they import and pass).

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/__init__.py server/catalog/reference_data.py server/tests/test_reference_data.py
git commit -m "$(cat <<'EOF'
feat: add v2 engine reference data (languages, skill-ability table)

Small hand-maintained tables for open SRD content the bundled JSON
files reference but don't ship as their own file (Backgrounds.json's
language_options points at "/api/2014/languages", which isn't bundled).
Ability keys are UPPERCASE to match frontend/src/types.ts's Ability
type exactly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Catalog loader

**Files:**
- Create: `server/catalog/loader.py`
- Create: `server/tests/test_loader.py`

**Interfaces:**
- Consumes: nothing from Task 1
- Produces: `catalog.loader.Catalog` dataclass with fields `classes: dict[str,
  dict]`, `levels: list[dict]`, `features: dict[str, dict]`, `subclasses:
  dict[str, dict]`, `races: dict[str, dict]`, `subraces: dict[str, dict]`,
  `traits: dict[str, dict]`, `backgrounds: dict[str, dict]`, plus methods
  `level_row(class_id: str, level: int) -> dict | None` and
  `subraces_of(race_id: str) -> list[dict]`; `catalog.loader.load() ->
  Catalog` — every later task in this plan imports `Catalog`/`load` from
  here.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_loader.py
from catalog.loader import load


def test_load_returns_expected_counts():
    catalog = load()
    assert len(catalog.classes) == 12
    assert len(catalog.races) == 9
    assert len(catalog.subraces) == 4
    assert len(catalog.backgrounds) == 1
    assert len(catalog.traits) == 38
    assert len(catalog.features) == 407
    assert len(catalog.levels) == 290
    assert len(catalog.subclasses) == 12


def test_classes_indexed_by_srd_index():
    catalog = load()
    assert "fighter" in catalog.classes
    assert catalog.classes["fighter"]["name"] == "Fighter"
    assert catalog.classes["fighter"]["hit_die"] == 10


def test_level_row_returns_the_matching_class_and_level():
    catalog = load()
    row = catalog.level_row("fighter", 1)
    assert row is not None
    assert row["level"] == 1
    assert row["prof_bonus"] == 2
    feature_names = {f["name"] for f in row["features"]}
    assert "Fighting Style" in feature_names
    assert "Second Wind" in feature_names


def test_level_row_returns_none_for_unknown_class_or_level():
    catalog = load()
    assert catalog.level_row("not-a-class", 1) is None
    assert catalog.level_row("fighter", 99) is None


def test_subraces_of_returns_only_that_races_subraces():
    catalog = load()
    dwarf_subraces = catalog.subraces_of("dwarf")
    assert [s["index"] for s in dwarf_subraces] == ["hill-dwarf"]
    assert catalog.subraces_of("human") == []


def test_backgrounds_contains_only_acolyte():
    catalog = load()
    assert list(catalog.backgrounds.keys()) == ["acolyte"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'catalog.loader'`

- [ ] **Step 3: Write `server/catalog/loader.py`**

```python
"""Loads and indexes the bundled SRD JSON data. This is the ONLY data
source in Phase 1 — no local sourcebook packs, no 5etools adapter (that's
Phase 4 scope, see the architecture spec §9-10). Every entity list is
indexed by its `index` field for O(1) lookup; the raw SRD field shapes are
used as-is here — catalog/choices.py and engine/resolve.py read those same
shapes directly rather than remapping them into a separate schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"


def _load(filename: str) -> list[dict]:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _index_by(items: list[dict], key: str = "index") -> dict[str, dict]:
    return {item[key]: item for item in items}


@dataclass
class Catalog:
    classes: dict[str, dict] = field(default_factory=dict)
    levels: list[dict] = field(default_factory=list)
    features: dict[str, dict] = field(default_factory=dict)
    subclasses: dict[str, dict] = field(default_factory=dict)
    races: dict[str, dict] = field(default_factory=dict)
    subraces: dict[str, dict] = field(default_factory=dict)
    traits: dict[str, dict] = field(default_factory=dict)
    backgrounds: dict[str, dict] = field(default_factory=dict)

    def level_row(self, class_id: str, level: int) -> dict | None:
        for row in self.levels:
            if row.get("class", {}).get("index") == class_id and row.get("level") == level:
                return row
        return None

    def subraces_of(self, race_id: str) -> list[dict]:
        return [s for s in self.subraces.values() if s.get("race", {}).get("index") == race_id]


def load() -> Catalog:
    return Catalog(
        classes=_index_by(_load("5e-SRD-Classes.json")),
        levels=_load("5e-SRD-Levels.json"),
        features=_index_by(_load("5e-SRD-Features.json")),
        subclasses=_index_by(_load("5e-SRD-Subclasses.json")),
        races=_index_by(_load("5e-SRD-Races.json")),
        subraces=_index_by(_load("5e-SRD-Subraces.json")),
        traits=_index_by(_load("5e-SRD-Traits.json")),
        backgrounds=_index_by(_load("5e-SRD-Backgrounds.json")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_loader.py -v`
Expected: all 6 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/loader.py server/tests/test_loader.py
git commit -m "$(cat <<'EOF'
feat: add v2 catalog loader for bundled SRD JSON

Indexes every chargen/data/srd/*.json file by its `index` field.
Counts verified against direct inspection of the bundled files (12
classes, 9 races, 4 subraces, 1 background, 38 traits, 407 features,
290 level rows, 12 subclasses) — Phase 1 reads only this bundled data,
no local sourcebook packs (that's Phase 4 scope).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Choice template builder

**Files:**
- Create: `server/catalog/choices.py`
- Create: `server/tests/test_choices.py`

**Interfaces:**
- Consumes: `reference_data.LANGUAGES` (Task 1)
- Produces: `choices.build_choice_options(from_field: dict) -> list[dict] |
  None` and `choices.build_choice_template(envelope: dict, choice_id: str,
  source: dict, label: str, description: str | None = None) -> dict | None`
  — Task 5 (`engine/resolve.py`) is the only later consumer.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_choices.py
import json
from pathlib import Path

from catalog.choices import build_choice_options, build_choice_template

_DATA_DIR = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"


def _load(name):
    with open(_DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def test_options_array_resolves_to_explicit_options():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["proficiency_choices"][0]
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert ids == {
        "skill-acrobatics", "skill-animal-handling", "skill-athletics",
        "skill-history", "skill-insight", "skill-intimidation",
        "skill-perception", "skill-survival",
    }
    labels = {o["label"] for o in options}
    assert "Skill: Athletics" in labels


def test_resource_list_languages_resolves_from_reference_data():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["language_options"]
    assert envelope["from"]["option_set_type"] == "resource_list"
    options = build_choice_options(envelope["from"])
    assert options is not None
    assert len(options) == 16
    ids = {o["id"] for o in options}
    assert "celestial" in ids
    assert "draconic" in ids


def test_equipment_category_is_unresolved_in_phase_1():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["starting_equipment_options"][0]
    assert envelope["from"]["option_set_type"] == "equipment_category"
    assert build_choice_options(envelope["from"]) is None


def test_build_choice_template_fighting_style_shape():
    features = _load("5e-SRD-Features.json")
    fighting_style = next(f for f in features if f["index"] == "fighter-fighting-style")
    # The subfeature_options envelope itself carries no 'desc' key (verified
    # directly against the JSON — only proficiency_choices envelopes do);
    # the description text lives on the parent feature. build_choice_template
    # never guesses at this — the caller (engine/resolve.py, Task 5) always
    # passes it explicitly, which is exactly what this test exercises.
    envelope = fighting_style["feature_specific"]["subfeature_options"]
    assert "desc" not in envelope
    source = {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1}
    tpl = build_choice_template(
        envelope, "class:fighter:1:feature:fighter-fighting-style", source, "Fighting Style",
        description=" ".join(fighting_style["desc"]),
    )
    assert tpl is not None
    assert tpl["id"] == "class:fighter:1:feature:fighter-fighting-style"
    assert tpl["source"] == source
    assert tpl["label"] == "Fighting Style"
    assert tpl["count"] == 1
    assert "specialty" in tpl["description"]
    option_ids = {o["id"] for o in tpl["options"]}
    assert "fighter-fighting-style-archery" in option_ids
    assert "fighter-fighting-style-defense" in option_ids


def test_build_choice_template_returns_none_when_unresolvable():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["starting_equipment_options"][0]
    source = {"kind": "background", "id": "acolyte", "label": "Acolyte"}
    assert build_choice_template(envelope, "background:acolyte:equipment", source, "Equipment") is None


def test_build_choice_template_joins_list_desc_into_a_string():
    features = _load("5e-SRD-Features.json")
    fighting_style = next(f for f in features if f["index"] == "fighter-fighting-style")
    assert isinstance(fighting_style["desc"], list)
    envelope = fighting_style["feature_specific"]["subfeature_options"]
    source = {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1}
    tpl = build_choice_template(envelope, "x", source, "Fighting Style", description=" ".join(fighting_style["desc"]))
    assert isinstance(tpl["description"], str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_choices.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'catalog.choices'`

- [ ] **Step 3: Write `server/catalog/choices.py`**

```python
"""Builds Choice-shaped templates (id, source, label, description, count,
options) from the SRD's "choose N of..." envelopes, per the architecture
spec's central abstraction (docs/superpowers/specs/2026-09-16-builder-v2-architecture.md
§1-2). Handles the two option_set_type shapes Phase 1 needs:
`options_array` (an explicit option list — the common case) and
`resource_list` for languages specifically (Backgrounds.json's
language_options references "/api/2014/languages", which isn't bundled as
its own SRD file — resolved from reference_data.LANGUAGES instead, since
that's pure open-content SRD data, not sourcebook material).
`equipment_category`-based option sets (used by starting_equipment_options)
are NOT resolved here — equipment choices are out of scope until Phase 2,
so any envelope needing that path returns None, and every caller must skip
a None result entirely rather than emit a partial or broken choice.
"""
from __future__ import annotations

from . import reference_data


def _option_label(option: dict) -> str | None:
    option_type = option.get("option_type")
    if option_type == "reference":
        return option["item"]["name"]
    if option_type == "counted_reference":
        return option["of"]["name"]
    if option_type == "string":
        return option["string"]
    return None  # score_prerequisite, multiple, etc. — not used by any Phase 1 choice


def build_choice_options(from_field: dict) -> list[dict] | None:
    """Returns [{id, label}] for this option set, or None if it can't be
    resolved from bundled Phase 1 data (equipment_category, or a
    resource_list type other than languages)."""
    set_type = from_field.get("option_set_type")

    if set_type == "options_array":
        options = []
        for opt in from_field.get("options", []):
            label = _option_label(opt)
            if label is None:
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
        return options

    if set_type == "resource_list":
        url = from_field.get("resource_list_url", "")
        if url.rstrip("/").endswith("languages"):
            return [{"id": lang["index"], "label": lang["name"]} for lang in reference_data.LANGUAGES]
        return None  # an unrecognized resource type — nothing else is bundled in Phase 1

    return None  # equipment_category and anything else — Phase 2+


def build_choice_template(
    envelope: dict,
    choice_id: str,
    source: dict,
    label: str,
    description: str | None = None,
) -> dict | None:
    """envelope is a raw "choose N of..." dict (has 'choose' and 'from').
    Returns a Choice template WITHOUT 'selected'/'status' — the engine adds
    those once it has the Draft's actual selections — or None if the option
    set can't be resolved from bundled Phase 1 data."""
    options = build_choice_options(envelope.get("from", {}))
    if options is None:
        return None
    desc = description if description is not None else envelope.get("desc")
    if isinstance(desc, list):
        desc = " ".join(desc)
    return {
        "id": choice_id,
        "source": source,
        "label": label,
        "description": desc or "",
        "count": envelope.get("choose", 1),
        "options": options,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_choices.py -v`
Expected: all 6 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/choices.py server/tests/test_choices.py
git commit -m "$(cat <<'EOF'
feat: add v2 Choice-template builder for SRD 'choose N of...' envelopes

Handles the two option_set_type shapes Phase 1 needs: options_array
(explicit list) and resource_list-for-languages (Backgrounds.json
points at "/api/2014/languages", not bundled as its own file — falls
back to reference_data.LANGUAGES). equipment_category is deliberately
unresolved (returns None) since equipment choices are Phase 2 scope —
verified this is exactly what Acolyte's starting_equipment_options[0]
hits.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Derived-stat math

**Files:**
- Create: `server/engine/__init__.py`
- Create: `server/engine/derived.py`
- Create: `server/tests/test_derived.py`

**Interfaces:**
- Consumes: `reference_data.ABILITIES`, `reference_data.SKILL_ABILITY` (Task 1)
- Produces: `derived.ability_modifier(score: int) -> int`,
  `derived.ability_modifiers(scores: dict[str, int]) -> dict[str, int]`,
  `derived.hit_point_max(hit_die: int | None, con_modifier: int) -> int`,
  `derived.armor_class(dex_modifier: int) -> int`,
  `derived.saving_throws(modifiers: dict, proficient_abilities: list[str],
  prof_bonus: int) -> dict[str, int]`,
  `derived.skill_scores(modifiers: dict, proficient_skills: list[str],
  prof_bonus: int) -> dict[str, int]`,
  `derived.passive_perception(skills: dict[str, int]) -> int`,
  `derived.ABILITIES` (re-exported) — Task 5 (`engine/resolve.py`) is the
  only later consumer.

- [ ] **Step 1: Write `server/engine/__init__.py`** (empty — just makes
  `engine` a package)

```python
```

- [ ] **Step 2: Write the failing tests**

```python
# server/tests/test_derived.py
from engine import derived


def test_ability_modifier_standard_table():
    assert derived.ability_modifier(10) == 0
    assert derived.ability_modifier(11) == 0
    assert derived.ability_modifier(16) == 3
    assert derived.ability_modifier(8) == -1
    assert derived.ability_modifier(20) == 5
    assert derived.ability_modifier(1) == -5


def test_ability_modifiers_maps_every_ability_defaulting_to_ten():
    mods = derived.ability_modifiers({"STR": 16, "DEX": 14})
    assert mods == {"STR": 3, "DEX": 2, "CON": 0, "INT": 0, "WIS": 0, "CHA": 0}


def test_hit_point_max_is_hit_die_plus_con_modifier_at_level_one():
    assert derived.hit_point_max(10, 2) == 12
    assert derived.hit_point_max(6, -1) == 5
    assert derived.hit_point_max(None, 2) == 0


def test_armor_class_unarmored_is_ten_plus_dex():
    assert derived.armor_class(2) == 12
    assert derived.armor_class(-1) == 9


def test_saving_throws_adds_prof_bonus_only_for_proficient_abilities():
    modifiers = {"STR": 3, "DEX": 2, "CON": 1, "INT": 0, "WIS": -1, "CHA": 0}
    saves = derived.saving_throws(modifiers, ["STR", "CON"], 2)
    assert saves == {"STR": 5, "DEX": 2, "CON": 3, "INT": 0, "WIS": -1, "CHA": 0}


def test_skill_scores_adds_prof_bonus_only_for_proficient_skills():
    modifiers = {"STR": 3, "DEX": 2, "CON": 1, "INT": 0, "WIS": -1, "CHA": 0}
    skills = derived.skill_scores(modifiers, ["skill-athletics", "skill-perception"], 2)
    assert skills["skill-athletics"] == 5  # STR 3 + prof 2
    assert skills["skill-perception"] == 1  # WIS -1 + prof 2
    assert skills["skill-stealth"] == 2  # DEX 2, not proficient
    assert len(skills) == 18


def test_passive_perception_is_ten_plus_perception_skill():
    skills = {"skill-perception": 3}
    assert derived.passive_perception(skills) == 13


def test_passive_perception_defaults_to_ten_when_perception_missing():
    assert derived.passive_perception({}) == 10
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_derived.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.derived'`

- [ ] **Step 4: Write `server/engine/derived.py`**

```python
"""Pure derived-stat math for a resolved level-1 single-class character.
No I/O, no catalog access — every function here is independently testable
against hand-computed 5e SRD values. All ability-keyed dicts use the same
UPPERCASE ability keys as frontend/src/types.ts's Ability type
("STR"/"DEX"/"CON"/"INT"/"WIS"/"CHA").
"""
from __future__ import annotations

from catalog import reference_data

ABILITIES = reference_data.ABILITIES


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def ability_modifiers(scores: dict[str, int]) -> dict[str, int]:
    return {ab: ability_modifier(scores.get(ab, 10)) for ab in ABILITIES}


def hit_point_max(hit_die: int | None, con_modifier: int) -> int:
    # Level 1 always takes the hit die's maximum, never rolled — matches
    # every published 5e level-1 HP rule.
    if hit_die is None:
        return 0
    return hit_die + con_modifier


def armor_class(dex_modifier: int) -> int:
    # No armor/shield yet — equipment is Phase 2. Unarmored AC = 10 + DEX mod.
    return 10 + dex_modifier


def saving_throws(
    modifiers: dict[str, int], proficient_abilities: list[str], prof_bonus: int,
) -> dict[str, int]:
    return {
        ab: modifiers[ab] + (prof_bonus if ab in proficient_abilities else 0)
        for ab in ABILITIES
    }


def skill_scores(
    modifiers: dict[str, int], proficient_skills: list[str], prof_bonus: int,
) -> dict[str, int]:
    return {
        skill_id: modifiers[ability] + (prof_bonus if skill_id in proficient_skills else 0)
        for skill_id, ability in reference_data.SKILL_ABILITY.items()
    }


def passive_perception(skills: dict[str, int]) -> int:
    return 10 + skills.get("skill-perception", 0)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_derived.py -v`
Expected: all 8 PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/__init__.py server/engine/derived.py server/tests/test_derived.py
git commit -m "$(cat <<'EOF'
feat: add v2 engine derived-stat math (mods, HP, AC, saves, skills)

Pure functions, no catalog/I-O dependency beyond the reference_data
skill-ability table — independently testable against hand-computed 5e
SRD values. All ability keys are UPPERCASE, matching
frontend/src/types.ts's Ability type exactly.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: The `resolve()` engine

**Files:**
- Create: `server/engine/resolve.py`
- Create: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog.loader.Catalog`/`load` (Task 2), `catalog.choices.
  build_choice_template` (Task 3), `engine.derived` (Task 4)
- Produces: `resolve.resolve(draft: dict, catalog: Catalog) -> dict` (a
  `Resolution`-shaped dict, per the Global Constraints) — Task 7
  (`server/app.py`) is the only later consumer.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_resolve.py
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _fighter_acolyte_human_draft(**overrides):
    draft = {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    draft.update(overrides)
    return draft


def _empty_draft():
    return {
        "name": "", "sources": ["srd"], "classes": [],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "standard", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }


def test_empty_draft_resolves_without_error_or_problems(catalog):
    resolution = resolve(_empty_draft(), catalog)
    assert resolution["problems"] == []
    assert resolution["choices"] == []
    assert resolution["sheet"]["name"] == ""
    assert resolution["sheet"]["level"] == 0
    assert resolution["sheet"]["class"] is None


def test_fighter_acolyte_human_produces_expected_sheet_and_derived(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["problems"] == []
    sheet = resolution["sheet"]
    assert sheet["name"] == "Torvin Bracewell"
    assert sheet["level"] == 1
    assert sheet["class"] == {"id": "fighter", "name": "Fighter"}
    assert sheet["background"] == {"id": "acolyte", "name": "Acolyte"}
    assert sheet["species"]["id"] == "human"
    assert sheet["species"]["subspecies"] is None
    # Human's +1 to every ability (chargen/data/srd/5e-SRD-Races.json)
    assert sheet["abilities"] == {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9}

    derived = resolution["derived"]
    assert derived["abilityModifiers"] == {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1}
    assert derived["proficiencyBonus"] == 2
    assert derived["hitPointMax"] == 12  # Fighter hit_die 10 + CON mod 2
    assert derived["hitDice"] == "1d10"
    assert derived["armorClass"] == 12  # 10 + DEX mod 2, unarmored
    assert derived["speed"] == 30
    # Fighter is proficient in STR and CON saves
    assert derived["savingThrows"]["STR"] == 5
    assert derived["savingThrows"]["CON"] == 4
    assert derived["savingThrows"]["DEX"] == 2  # not proficient
    assert derived["passivePerception"] == 10 + derived["skills"]["skill-perception"]


def test_fighter_class_skill_choice_disables_options_already_granted_by_background(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    skill_choice = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Skill Proficiencies"
    )
    insight = next(o for o in skill_choice["options"] if o["id"] == "skill-insight")
    assert insight.get("disabled") is True
    assert "Acolyte" in insight["disabledReason"]
    athletics = next(o for o in skill_choice["options"] if o["id"] == "skill-athletics")
    assert not athletics.get("disabled")


def test_fighting_style_choice_is_present_and_pending_by_default(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    fighting_style = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Fighting Style"
    )
    assert fighting_style["count"] == 1
    assert fighting_style["selected"] == []
    assert fighting_style["status"] == "pending"
    # The subfeature_options envelope itself carries no description — this
    # must be sourced from the parent feature's own 'desc', or it silently
    # renders blank in the UI.
    assert "specialty" in fighting_style["description"]
    option_ids = {o["id"] for o in fighting_style["options"]}
    assert "fighter-fighting-style-archery" in option_ids


def test_selecting_a_choice_marks_it_resolved(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"]},
        }],
    )
    resolution = resolve(draft, catalog)
    fighting_style = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Fighting Style"
    )
    assert fighting_style["selected"] == ["fighter-fighting-style-archery"]
    assert fighting_style["status"] == "resolved"


def test_background_language_choice_offers_sixteen_languages(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    languages = next(c for c in resolution["choices"] if c["source"]["kind"] == "background")
    assert languages["label"] == "Languages"
    assert languages["count"] == 2
    assert len(languages["options"]) == 16
    assert languages["description"] == "Choose 2 languages of your choice."


def test_species_trait_choice_for_dragonborn_ancestry(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dragonborn", "choices": {}})
    resolution = resolve(draft, catalog)
    ancestry = next(c for c in resolution["choices"] if c["source"]["kind"] == "species")
    assert ancestry["label"] == "Draconic Ancestry"
    assert ancestry["count"] == 1
    # subtrait_options itself carries no description — must come from the
    # parent trait's own 'desc'.
    assert "draconic ancestry" in ancestry["description"].lower()
    option_ids = {o["id"] for o in ancestry["options"]}
    assert "draconic-ancestry-black" in option_ids


def test_subrace_ability_bonus_stacks_with_race(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "subspeciesId": "hill-dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    # Dwarf +2 CON, Hill Dwarf subrace +1 WIS (chargen/data/srd/5e-SRD-Races.json,
    # 5e-SRD-Subraces.json)
    assert resolution["sheet"]["abilities"]["CON"] == 16  # base 14 + 2
    assert resolution["sheet"]["abilities"]["WIS"] == 13  # base 12 + 1
    assert resolution["sheet"]["species"]["subspecies"] == {"id": "hill-dwarf", "name": "Hill Dwarf"}


def test_multiclass_draft_produces_a_problem_and_uses_only_the_first_class(catalog):
    draft = _fighter_acolyte_human_draft(classes=[
        {"classId": "fighter", "level": 1, "choices": {}},
        {"classId": "wizard", "level": 1, "choices": {}},
    ])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])
    assert resolution["sheet"]["class"]["id"] == "fighter"


def test_level_other_than_one_produces_a_problem_but_still_resolves(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "level-unsupported" for p in resolution["problems"])
    assert resolution["sheet"]["level"] == 1
    assert resolution["derived"]["proficiencyBonus"] == 2


def test_unknown_class_id_produces_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "not-a-class", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "unknown-class" for p in resolution["problems"])
    assert resolution["sheet"]["class"] is None


def test_ability_score_out_of_range_produces_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(abilities={
        "method": "manual",
        "base": {"STR": 99, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
    })
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "ability-out-of-range-STR" for p in resolution["problems"])


def test_mismatched_subspecies_is_a_problem_and_subspecies_is_ignored(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "human", "subspeciesId": "hill-dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "subspecies-mismatch" for p in resolution["problems"])
    assert resolution["sheet"]["species"]["subspecies"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_resolve.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.resolve'`

- [ ] **Step 3: Write `server/engine/resolve.py`**

```python
"""resolve(draft, catalog) -> Resolution — the single entry point for all
character-rules computation, per the architecture spec's engine contract
(docs/superpowers/specs/2026-09-16-builder-v2-architecture.md §3). One
fixed-order pass: sources → species ability bonuses → final ability scores
→ derived stats → choice generation/validation (§4a) — never iterates to a
fixpoint.

Phase 1 scope: single class, level 1 only. Multiclass, leveling above 1,
subclass selection, and equipment are all out of scope (see the plan's
Global Constraints) — draft.classes[0].subclassId is read but never
trusted to gate a feature choice unless it actually matches, so any
level-1 feature gated to a specific subclass is filtered out rather than
guessed at.
"""
from __future__ import annotations

from catalog.choices import build_choice_template
from catalog.loader import Catalog
from . import derived as derived_mod


def _species_ability_bonuses(race: dict | None, subrace: dict | None) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for src in (race, subrace):
        if not src:
            continue
        for entry in src.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses


def _class_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(cls.get("proficiency_choices", [])):
        cid = f"class:{cls_id}:1:prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}
        label = "Skill Proficiencies" if envelope.get("type") == "proficiencies" else (envelope.get("type") or "Choice").title()
        tpl = build_choice_template(envelope, cid, source, label)
        if tpl:
            templates.append(tpl)
    return templates


def _join_desc(desc) -> str | None:
    """Feature/trait 'desc' fields are lists of paragraph strings; choice
    envelopes never carry their own 'desc' except proficiency_choices (see
    Task 3's build_choice_template, which already handles a list there).
    This joins a parent object's desc for explicit passing as the
    'description' override, since the choice envelope itself has none."""
    if isinstance(desc, list):
        return " ".join(desc)
    return desc


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


def _background_choice_templates(bg: dict, bg_id: str) -> list[dict]:
    templates = []
    envelope = bg.get("language_options")
    if envelope:
        cid = f"background:{bg_id}:languages"
        source = {"kind": "background", "id": bg_id, "label": bg["name"]}
        # language_options carries no 'desc' of its own, and the background
        # object has no separate summary text for it either — write a
        # plain, generic description rather than leaving it blank.
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Languages", description=description)
        if tpl:
            templates.append(tpl)
    return templates


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
        # subtrait_options carries no 'desc' of its own — the description
        # text lives on the parent trait (verified directly against
        # 5e-SRD-Traits.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, trait["name"], description=_join_desc(trait.get("desc")))
        if tpl:
            templates.append(tpl)
    return templates


def _apply_background_overlap(class_templates: list[dict], bg: dict | None) -> None:
    if not bg:
        return
    granted = {p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-")}
    if not granted:
        return
    for tpl in class_templates:
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = f"already granted by {bg['name']}"


def resolve(draft: dict, catalog: Catalog) -> dict:
    problems: list[dict] = []
    warnings: list[dict] = []

    classes = draft.get("classes") or []
    if len(classes) > 1:
        problems.append({"id": "multiclass-unsupported", "message": "Multiclassing isn't supported yet — pick a single class."})
        classes = classes[:1]

    cls_entry = classes[0] if classes else None
    cls_id = cls_entry.get("classId") if cls_entry else None
    subclass_id = cls_entry.get("subclassId") if cls_entry else None
    if cls_entry and cls_entry.get("level", 1) != 1:
        problems.append({"id": "level-unsupported", "message": "Only level 1 is supported in this version."})

    cls = catalog.classes.get(cls_id) if cls_id else None
    if cls_id and not cls:
        problems.append({"id": "unknown-class", "message": f"Unknown class '{cls_id}'."})

    bg_id = (draft.get("background") or {}).get("id")
    bg = catalog.backgrounds.get(bg_id) if bg_id else None
    if bg_id and not bg:
        problems.append({"id": "unknown-background", "message": f"Unknown background '{bg_id}'."})

    species = draft.get("species") or {}
    race_id = species.get("id")
    race = catalog.races.get(race_id) if race_id else None
    if race_id and not race:
        problems.append({"id": "unknown-species", "message": f"Unknown species '{race_id}'."})

    subrace_id = species.get("subspeciesId")
    subrace = catalog.subraces.get(subrace_id) if subrace_id else None
    if subrace_id and not subrace:
        problems.append({"id": "unknown-subspecies", "message": f"Unknown subspecies '{subrace_id}'."})
    elif subrace and subrace.get("race", {}).get("index") != race_id:
        problems.append({
            "id": "subspecies-mismatch",
            "message": f"'{subrace['name']}' isn't a subspecies of the selected species.",
        })
        subrace = None

    # Final ability scores: base + species bonuses (2014-rules placement —
    # backgrounds don't grant ability bonuses in this ruleset; see spec §4).
    base_scores = (draft.get("abilities") or {}).get("base") or {}
    species_bonuses = _species_ability_bonuses(race, subrace)
    final_scores = {
        ab: int(base_scores.get(ab, 10)) + species_bonuses.get(ab, 0)
        for ab in derived_mod.ABILITIES
    }
    for ab, score in final_scores.items():
        if not (1 <= score <= 30):
            problems.append({"id": f"ability-out-of-range-{ab}", "message": f"{ab} score {score} is out of the 1-30 range."})

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus = 2  # fixed at level 1 for every class, per the SRD level tables

    # Choice templates from every source.
    choice_templates: list[dict] = []
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.level_row(cls_id, 1)
        if level_row:
            choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], level_row.get("features", []), subclass_id)
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)

    # Apply the draft's own selections onto each template to get a real Choice.
    all_selections: dict[str, list[str]] = {}
    if cls_entry:
        all_selections.update(cls_entry.get("choices") or {})
    all_selections.update((draft.get("background") or {}).get("choices") or {})
    all_selections.update((draft.get("species") or {}).get("choices") or {})

    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"]}
        selected = [s for s in all_selections.get(tpl["id"], []) if s in valid_ids]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    # Derived stats.
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class" and c["label"] == "Skill Proficiencies":
            proficient_skills.update(c["selected"])
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))

    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]

    hit_die = cls.get("hit_die") if cls else None
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max(hit_die, modifiers["CON"]),
        "hitDice": f"1d{hit_die}" if hit_die else None,
        "armorClass": derived_mod.armor_class(modifiers["DEX"]),
        "speed": race.get("speed") if race else None,
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills),
    }

    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])]
    chosen_languages = [s for c in choices if c["label"] == "Languages" for s in c["selected"]]

    sheet = {
        "name": draft.get("name") or "",
        "level": 1 if cls else 0,
        "class": {"id": cls_id, "name": cls["name"]} if cls else None,
        "background": {"id": bg_id, "name": bg["name"]} if bg else None,
        "species": {
            "id": race_id, "name": race["name"],
            "subspecies": {"id": subrace_id, "name": subrace["name"]} if subrace else None,
        } if race else None,
        "abilities": final_scores,
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + chosen_languages)),
        },
    }

    return {
        "sheet": sheet,
        "choices": choices,
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": [],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_resolve.py -v`
Expected: all 14 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: add v2 resolve() engine for single-class level-1 characters

Single fixed-order pass (sources -> species ability bonuses -> final
scores -> derived stats -> choice generation), per the architecture
spec's engine contract. Handles class skill/feature choices,
background languages, and species trait sub-choices (e.g. Draconic
Ancestry); disables class-skill options already granted by the
background, with a disabledReason naming it. Never throws on an
incomplete draft — an empty draft resolves to an empty-but-valid
Resolution, matching what Phase 0's frontend already sends by default.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: YAML export

**Files:**
- Create: `server/export.py`
- Modify: `server/requirements.txt` (add `pyyaml`)
- Create: `server/tests/test_export.py`

**Interfaces:**
- Consumes: nothing from earlier tasks directly (operates on a `Resolution`
  dict, whatever produced it)
- Produces: `export.to_yaml(resolution: dict) -> str` — Task 7
  (`server/app.py`) is the only later consumer.

- [ ] **Step 1: Add `pyyaml` to `server/requirements.txt`**

```
flask
flask-cors
pytest
pyyaml
```

- [ ] **Step 2: Install it**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server
.venv/bin/pip install -q pyyaml
```

- [ ] **Step 3: Write the failing tests**

```python
# server/tests/test_export.py
import yaml

from export import to_yaml


def _sample_resolution():
    return {
        "sheet": {
            "name": "Тестов Герой",
            "level": 1,
            "class": {"id": "fighter", "name": "Fighter"},
            "background": {"id": "acolyte", "name": "Acolyte"},
            "species": {"id": "human", "name": "Human", "subspecies": None},
            "abilities": {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9},
            "proficiencies": {"skills": ["skill-athletics"], "savingThrows": ["STR", "CON"], "languages": ["common"]},
        },
        "derived": {
            "abilityModifiers": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
            "proficiencyBonus": 2,
            "hitPointMax": 12,
            "hitDice": "1d10",
            "armorClass": 12,
            "speed": 30,
            "savingThrows": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
            "skills": {"skill-athletics": 5},
            "passivePerception": 11,
        },
        "choices": [], "problems": [], "warnings": [], "pruned": [],
    }


def test_to_yaml_produces_parseable_yaml_with_expected_fields():
    text = to_yaml(_sample_resolution())
    doc = yaml.safe_load(text)
    assert doc["name"] == "Тестов Герой"
    assert doc["level"] == 1
    assert doc["class"] == {"id": "fighter", "name": "Fighter"}
    assert doc["abilities"]["STR"] == 17
    assert doc["hitPointMax"] == 12
    assert doc["armorClass"] == 12
    assert doc["proficiencies"]["skills"] == ["skill-athletics"]


def test_to_yaml_does_not_escape_unicode_names():
    text = to_yaml(_sample_resolution())
    assert "Тестов Герой" in text
    assert "\\u" not in text
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_export.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'export'`

- [ ] **Step 5: Write `server/export.py`**

```python
"""Turns a Resolution (see engine/resolve.py) into a portable YAML
character sheet — a flat document with the fields a player would actually
want to keep, not the internal choices/problems bookkeeping.
"""
from __future__ import annotations

import yaml


def to_yaml(resolution: dict) -> str:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    doc = {
        "name": sheet["name"],
        "level": sheet["level"],
        "class": sheet["class"],
        "background": sheet["background"],
        "species": sheet["species"],
        "abilities": sheet["abilities"],
        "abilityModifiers": derived["abilityModifiers"],
        "proficiencyBonus": derived["proficiencyBonus"],
        "hitPointMax": derived["hitPointMax"],
        "hitDice": derived["hitDice"],
        "armorClass": derived["armorClass"],
        "speed": derived["speed"],
        "savingThrows": derived["savingThrows"],
        "skills": derived["skills"],
        "passivePerception": derived["passivePerception"],
        "proficiencies": sheet["proficiencies"],
    }
    # allow_unicode=True: character names in this app are routinely
    # Cyrillic (the app's own examples are Bulgarian) — without this,
    # PyYAML escapes them as \uXXXX, which is technically valid YAML but
    # unreadable to a human opening the file.
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_export.py -v`
Expected: both PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/export.py server/requirements.txt server/tests/test_export.py
git commit -m "$(cat <<'EOF'
feat: add v2 YAML export for a resolved character

Flat, player-facing document (not the internal choices/problems
bookkeeping) — allow_unicode=True so Cyrillic names round-trip
readably instead of escaping to \\uXXXX, matching this app's own
example characters.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Wire the engine into `server/app.py`

**Files:**
- Modify: `server/app.py`
- Create: `server/tests/test_app.py`
- Delete: `server/tests/test_resolve_stub.py`

**Interfaces:**
- Consumes: `catalog.loader.load`/`Catalog` (Task 2), `engine.resolve.
  resolve` (Task 5), `export.to_yaml` (Task 6)
- Produces: the real `POST /api/resolve`, plus new `GET /api/catalog`,
  `GET /api/catalog/class/<id>`, `GET /api/catalog/background/<id>`,
  `GET /api/catalog/species/<id>`, `POST /api/export/yaml` — Phase 1b (a
  separate, later plan) is the consumer of the new catalog endpoints from
  the frontend side; nothing in this plan depends on them being consumed.

- [ ] **Step 1: Delete the Phase 0 stub test file**

```bash
cd /Users/yoanpetrov/dnd-character-creator
rm server/tests/test_resolve_stub.py
```

Its assertions describe Phase 0's hardcoded stub Resolution (fixed
Fighter/Acolyte/Dragonborn choices returned regardless of the request
body), which no longer exists once `/api/resolve` calls the real engine —
Step 3 below writes its replacement in the same task, so coverage is never
gapped.

- [ ] **Step 2: Write the failing tests**

```python
# server/tests/test_app.py
import yaml

from app import app


import pytest


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _fighter_acolyte_human_draft():
    return {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_resolve_empty_draft_is_valid_not_an_error(client):
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["choices"] == []


def test_resolve_real_draft_returns_computed_values(client):
    resp = client.post("/api/resolve", json=_fighter_acolyte_human_draft())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["sheet"]["class"]["id"] == "fighter"
    assert body["derived"]["hitPointMax"] == 12
    assert body["derived"]["armorClass"] == 12
    skill_choice = next(c for c in body["choices"] if c["label"] == "Skill Proficiencies")
    insight = next(o for o in skill_choice["options"] if o["id"] == "skill-insight")
    assert insight["disabled"] is True


def test_catalog_endpoint_lists_all_classes_backgrounds_species(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["classes"]) == 12
    assert len(body["backgrounds"]) == 1
    assert len(body["species"]) == 9
    fighter = next(c for c in body["classes"] if c["id"] == "fighter")
    assert fighter["hitDie"] == 10
    dwarf = next(s for s in body["species"] if s["id"] == "dwarf")
    assert dwarf["subspecies"] == [{"id": "hill-dwarf", "name": "Hill Dwarf"}]


def test_catalog_class_detail_endpoint(client):
    resp = client.get("/api/catalog/class/fighter")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Fighter"


def test_catalog_class_detail_endpoint_404s_for_unknown_id(client):
    resp = client.get("/api/catalog/class/not-a-class")
    assert resp.status_code == 404


def test_catalog_background_detail_endpoint(client):
    resp = client.get("/api/catalog/background/acolyte")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Acolyte"


def test_catalog_species_detail_endpoint_includes_subspecies(client):
    resp = client.get("/api/catalog/species/dwarf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Dwarf"
    assert [s["index"] for s in body["subspecies"]] == ["hill-dwarf"]


def test_export_yaml_endpoint_returns_valid_yaml(client):
    resp = client.post("/api/export/yaml", json=_fighter_acolyte_human_draft())
    assert resp.status_code == 200
    assert resp.mimetype == "application/x-yaml"
    doc = yaml.safe_load(resp.data.decode("utf-8"))
    assert doc["name"] == "Torvin Bracewell"
    assert doc["hitPointMax"] == 12


def test_export_yaml_rejects_a_draft_with_problems(client):
    resp = client.post("/api/export/yaml", json={
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}, {"classId": "wizard", "level": 1, "choices": {}}],
    })
    assert resp.status_code == 400
    assert any(p["id"] == "multiclass-unsupported" for p in resp.get_json()["problems"])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_app.py -v`
Expected: FAIL (old `_stub_resolution` still in place, new catalog/export
routes don't exist yet)

- [ ] **Step 4: Rewrite `server/app.py`**

```python
"""Thin Flask shell around the v2 catalog + resolve engine + YAML export.
No rules logic lives here — this module only wires HTTP onto
catalog.loader / engine.resolve / export.
"""
from __future__ import annotations

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from catalog.loader import load as load_catalog
from engine.resolve import resolve
from export import to_yaml

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

_catalog = load_catalog()


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    draft = request.get_json(silent=True) or {}
    return jsonify(resolve(draft, _catalog))


@app.route("/api/catalog")
def api_catalog():
    return jsonify({
        "classes": [{"id": c["index"], "name": c["name"], "hitDie": c["hit_die"]} for c in _catalog.classes.values()],
        "backgrounds": [{"id": b["index"], "name": b["name"]} for b in _catalog.backgrounds.values()],
        "species": [
            {
                "id": r["index"], "name": r["name"],
                "subspecies": [{"id": s["index"], "name": s["name"]} for s in _catalog.subraces_of(r["index"])],
            }
            for r in _catalog.races.values()
        ],
    })


@app.route("/api/catalog/class/<class_id>")
def api_catalog_class(class_id: str):
    cls = _catalog.classes.get(class_id)
    if not cls:
        return jsonify({"error": "not found"}), 404
    return jsonify(cls)


@app.route("/api/catalog/background/<background_id>")
def api_catalog_background(background_id: str):
    bg = _catalog.backgrounds.get(background_id)
    if not bg:
        return jsonify({"error": "not found"}), 404
    return jsonify(bg)


@app.route("/api/catalog/species/<species_id>")
def api_catalog_species(species_id: str):
    race = _catalog.races.get(species_id)
    if not race:
        return jsonify({"error": "not found"}), 404
    return jsonify({**race, "subspecies": _catalog.subraces_of(species_id)})


@app.route("/api/export/yaml", methods=["POST"])
def api_export_yaml():
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    if resolution["problems"]:
        return jsonify({"problems": resolution["problems"]}), 400
    return Response(to_yaml(resolution), mimetype="application/x-yaml")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_app.py -v`
Expected: all 10 PASS

- [ ] **Step 6: Run the FULL server test suite to confirm nothing regressed**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all tests across every file in this plan PASS (test_reference_data,
test_loader, test_choices, test_derived, test_resolve, test_export, test_app
— roughly 45 tests total), and `test_resolve_stub.py` no longer exists in
the collected list.

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/app.py server/tests/test_app.py
git rm server/tests/test_resolve_stub.py
git commit -m "$(cat <<'EOF'
feat: wire the real v2 engine into app.py, add catalog + export endpoints

/api/resolve now calls the real resolve() engine instead of returning
Phase 0's hardcoded stub. New GET /api/catalog[/class|background|species/<id>]
endpoints (for Phase 1b's real pickers, not yet consumed by any
frontend code) and POST /api/export/yaml. test_resolve_stub.py is
replaced by test_app.py, which tests the real endpoints end to end.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: End-to-end verification

**Files:** none created or modified — this task is pure verification.

**Interfaces:** none — this task consumes the finished Task 1-7 system as a
whole and verifies it behaves correctly from the outside, the way a real
client (the Phase 0 frontend, or curl) would.

- [ ] **Step 1: Run the full backend test suite one more time**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 2: Start the server and exercise it with curl for a full
  character build + export round trip**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server
.venv/bin/python3 app.py &
sleep 1

curl -s -X POST http://127.0.0.1:8000/api/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Torvin Bracewell",
    "sources": ["srd"],
    "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
    "background": {"id": "acolyte", "choices": {}},
    "species": {"id": "human", "choices": {}},
    "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    "equipment": {"added": [], "skipped": false},
    "details": {}
  }' | python3 -m json.tool | head -60

echo "--- export ---"
curl -s -X POST http://127.0.0.1:8000/api/export/yaml \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Torvin Bracewell",
    "sources": ["srd"],
    "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
    "background": {"id": "acolyte", "choices": {}},
    "species": {"id": "human", "choices": {}},
    "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    "equipment": {"added": [], "skipped": false},
    "details": {}
  }'

echo "--- empty draft (matches Phase 0's default frontend state) ---"
curl -s -X POST http://127.0.0.1:8000/api/resolve -H "Content-Type: application/json" -d '{}' | python3 -m json.tool

kill %1
```

Expected: the first call returns a full Resolution with `problems: []`, a
populated `sheet`, and `derived.hitPointMax == 12`; the export call returns
a readable YAML document (not `%PDF`/JSON — actual YAML) with the same
character's data; the empty-draft call returns a valid Resolution with
`choices: []` and `problems: []`, not an error — confirming the Phase 0
frontend (unchanged, still loaded with its default empty draft) will not
break against this new backend.

- [ ] **Step 3: Confirm no stray server process is left running**

```bash
ps aux | grep -E "app\.py" | grep -v grep
```

Expected: empty output.
