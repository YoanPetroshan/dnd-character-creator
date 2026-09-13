# Character Creator App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone Flask app (new repo `~/dnd-character-creator`) that creates
D&D 5e characters via the ported `chargen` engine and exports them as YAML,
Markdown, and a filled official PDF character sheet.

**Architecture:** `chargen/` (ported verbatim, zero changes) is the rules/content
engine. `storage.py` persists the sheet as YAML at the same path convention the
source repo's play app already uses (`~/.claude/dnd/characters/<Name>/current.yaml`,
override via `DND_CAMPAIGN_ROOT`) — no code shared, just the same directory
so a future integration needs no data migration. `sheet_derive.py` computes
AC/skills/saves/spellcasting numbers a printed sheet needs but `chargen.build()`
deliberately omits, by calling functions already in `chargen.rules`.
`markdown_render.py` and `pdf_fill.py` are the two export formats, both reading
only the sheet dict + derived-stats dict. `app.py` is a thin Flask layer wiring
an HTTP API onto all of the above. `templates/builder.html` is the ported,
trimmed 7-step wizard UI.

**Tech Stack:** Python 3.11+, Flask, flask-cors, PyYAML, pypdf. No JS framework —
`builder.html` is one self-contained file (inline CSS/JS), same as the source repo.

## Global Constraints

- **Nothing in this repo imports from the source repo's play engine**
  (`char_state_schema`, `char_state_sync`, `char_state_derive`, `character`,
  `lookup`, `library`, `paths`, etc.). `chargen/` is ported verbatim and
  already follows this rule; every new module (`sheet_derive.py`,
  `markdown_render.py`, `pdf_fill.py`, `storage.py`, `app.py`) follows it too.
  `sheet_derive.py` MAY import from `chargen` (it lives in this repo) — the
  constraint is about the *other* repo's engine, not about `chargen` itself.
- **The sheet dict shape is exactly what `chargen.build()` returns** — see
  Task 1's reference copy of `chargen/build.py` for the authoritative shape.
  Do not add fields to it; derived stats live in a separate `derived` dict
  (Task 3), never merged into the sheet dict itself.
- **Character storage path**: `<root>/characters/<safe-name>/current.yaml`
  (plus `character.md` and `character.pdf` alongside it), where `<root>` is
  `$DND_CAMPAIGN_ROOT` if set, else `~/.claude/dnd` — the exact convention
  `skills/dnd/scripts/paths.py::characters_dir()` uses in the source repo, so
  characters this app creates are already visible to that app's existing
  `library.py` with no migration, without this repo importing anything from
  it. This is a deliberate, more forward-compatible choice than "a `library/`
  folder inside this repo" — if that reads as a change from an earlier
  conversation, it is: keep this path convention.
- **PDF template**: `assets/character-sheet-template.pdf` (already committed —
  the official Wizards of the Coast fillable 2014-ruleset sheet, 334 AcroForm
  fields, verified via `pypdf.PdfReader.get_fields()`). Field names are
  case- and whitespace-exact, including two real quirks in this specific
  file: the Dex modifier field is `"DEXmod "` (trailing space) and the
  Charisma modifier field is `"CHamod"` (lowercase "h", not `"CHAmod"`).
  Copy field names from Task 5 verbatim — do not "fix" the typo, it must
  match the PDF's actual AcroForm field name to have any effect.
- **PDF fill scope, deliberately limited** (Task 5): identity, ability
  scores/mods, saves, skills, combat stats, currency, equipment/features/
  proficiencies/personality/backstory as text blobs, and up to 3 equipped
  weapons by name. Per-spell-level slot boxes (`SlotsTotal 19-27`) and the
  individual spell-list rows (`Spells 10100`..`Spells 1080` — cryptically
  numbered, no reliable field-to-spell-level mapping without visually
  inspecting widget positions) are **not** filled in this plan. Markdown
  export (Task 4) is the complete spell/weapon-math reference; the PDF is
  the "hand someone a physical sheet" format, not required to be 100% complete
  on spells. Do not attempt the slot/spell-row fields — that's future work.
- **Every new Python file's first line of testing is import isolation**:
  a test asserting the module raises no error importing with only stdlib +
  `chargen` + (for `pdf_fill.py`/`storage.py`) `pypdf`/`PyYAML` available —
  mirrors `chargen`'s own `test_chargen_isolation.py`.

---

### Task 1: Port `chargen` verbatim + establish the repo skeleton

**Files:**
- Create: `chargen/` — copy of `dnd-app-bg-local/chargen/` in full (all `.py`
  files plus `chargen/data/srd/*.json`), zero content changes
- Create: `tests/test_chargen_sync.py`, `tests/test_chargen_catalog.py`,
  `tests/test_chargen_rules.py`, `tests/test_chargen_cli.py`,
  `tests/test_chargen_build.py`, `tests/test_chargen_normalise.py`,
  `tests/test_chargen_isolation.py` — copies of the identically-named files
  in `dnd-app-bg-local/tests/`, zero content changes
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pytest.ini`

**Interfaces:**
- Produces: `chargen.build.build(draft, catalog=None) -> (sheet, problems, warnings)`,
  `chargen.catalog.Catalog.load(ruleset="2024") -> Catalog`, `chargen.rules.*`
  (all as documented in `dnd-app-bg-local/chargen/`) — every later task
  imports from this `chargen` package.

- [ ] **Step 1: Copy the chargen package**

```bash
cp -R /Users/yoanpetrov/dnd-app-bg-local/chargen /Users/yoanpetrov/dnd-character-creator/chargen
```

- [ ] **Step 2: Copy chargen's existing tests**

```bash
mkdir -p /Users/yoanpetrov/dnd-character-creator/tests
for f in test_chargen_sync.py test_chargen_catalog.py test_chargen_rules.py \
         test_chargen_cli.py test_chargen_build.py test_chargen_normalise.py \
         test_chargen_isolation.py; do
  cp "/Users/yoanpetrov/dnd-app-bg-local/tests/$f" \
     "/Users/yoanpetrov/dnd-character-creator/tests/$f"
done
touch /Users/yoanpetrov/dnd-character-creator/tests/__init__.py
```

- [ ] **Step 3: Write `requirements.txt`**

```
flask
flask-cors
PyYAML
pypdf
pytest
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
*.tmp
.DS_Store
```

- [ ] **Step 5: Write `pytest.ini`** (so `chargen`, `storage`, etc. import as
  top-level modules when pytest runs from repo root — same layout the
  source repo uses)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

- [ ] **Step 6: Set up a venv and install dependencies**

```bash
cd /Users/yoanpetrov/dnd-character-creator
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
```

- [ ] **Step 7: Run the ported tests to confirm chargen works standalone**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/ -v`
Expected: all `test_chargen_*` tests PASS with no changes needed. If any
fail, the failure is almost certainly a path assumption
(`chargen/sources.py::srd_dir()` resolves `Path(__file__).resolve().parent.parent`
— i.e. two directories up from `chargen/sources.py`, which must land on this
repo's root, exactly as it lands on `dnd-app-bg-local`'s root there). Do not
alter chargen's logic to fix a failure — if one occurs, the copy is
incomplete (check `chargen/data/srd/*.json` copied correctly) rather than
chargen needing a code change.

- [ ] **Step 8: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add chargen tests requirements.txt .gitignore pytest.ini
git commit -m "feat: port chargen engine and its tests verbatim

Copied unchanged from dnd-app-bg-local/chargen — it already has zero
dependencies outside chargen + stdlib, which this whole app leans on.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: `storage.py` — character persistence

**Files:**
- Create: `storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure filesystem + PyYAML)
- Produces: `storage.root_dir() -> Path`, `storage.safe_dir_name(name: str) -> str`,
  `storage.char_dir(name: str) -> Path`, `storage.save_yaml(name: str, sheet: dict) -> Path`,
  `storage.save_markdown(name: str, text: str) -> Path`,
  `storage.save_pdf(name: str, data: bytes) -> Path`,
  `storage.list_characters() -> list[dict]` (each: `{"name", "race", "classes", "level"}`,
  read back from each character's `current.yaml`) — Tasks 4, 5, 6 all call
  `storage.save_*` and `storage.list_characters()`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_storage.py
import os
import yaml
import pytest

import storage


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    yield tmp_path


def test_root_dir_respects_env(isolated_root):
    assert storage.root_dir() == isolated_root


def test_root_dir_default(monkeypatch):
    monkeypatch.delenv("DND_CAMPAIGN_ROOT", raising=False)
    assert storage.root_dir() == (__import__("pathlib").Path("~/.claude/dnd").expanduser())


def test_safe_dir_name_strips_unsafe_chars():
    assert storage.safe_dir_name("Sy/lwen:*Night?brook") == "Sylwen Nightbrook"


def test_safe_dir_name_rejects_empty():
    with pytest.raises(ValueError):
        storage.safe_dir_name("///")


def test_save_yaml_round_trips(isolated_root):
    sheet = {"name": "Torvin Bracewell", "race": "Human",
             "classes": [{"cls": "Fighter", "subclass": "", "level": 1}]}
    path = storage.save_yaml("Torvin Bracewell", sheet)
    assert path.exists()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert loaded == sheet
    assert path.parent == storage.char_dir("Torvin Bracewell")
    assert path.name == "current.yaml"


def test_save_markdown_and_pdf(isolated_root):
    md_path = storage.save_markdown("Torvin Bracewell", "# Torvin Bracewell\n")
    pdf_path = storage.save_pdf("Torvin Bracewell", b"%PDF-fake-bytes")
    assert md_path.read_text(encoding="utf-8") == "# Torvin Bracewell\n"
    assert pdf_path.read_bytes() == b"%PDF-fake-bytes"
    assert md_path.name == "character.md"
    assert pdf_path.name == "character.pdf"


def test_list_characters(isolated_root):
    storage.save_yaml("Sylwen Nightbrook", {
        "name": "Sylwen Nightbrook", "race": "Wood Elf",
        "classes": [{"cls": "Cleric", "subclass": "Life", "level": 1}]})
    storage.save_yaml("Torvin Bracewell", {
        "name": "Torvin Bracewell", "race": "Human",
        "classes": [{"cls": "Fighter", "subclass": "", "level": 1}]})
    out = storage.list_characters()
    names = sorted(c["name"] for c in out)
    assert names == ["Sylwen Nightbrook", "Torvin Bracewell"]
    sylwen = next(c for c in out if c["name"] == "Sylwen Nightbrook")
    assert sylwen["race"] == "Wood Elf"
    assert sylwen["classes"] == [{"cls": "Cleric", "subclass": "Life", "level": 1}]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'storage'`

- [ ] **Step 3: Write `storage.py`**

```python
"""Character persistence — YAML sheet + Markdown + PDF, one directory per
character, at the same path convention dnd-app-bg-local's play app already
uses (skills/dnd/scripts/paths.py::characters_dir()) — so a character this
app saves is already visible to that app's library.py with zero migration,
without this module importing anything from that repo.

Imports nothing outside the standard library + PyYAML.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import yaml

_UNSAFE = re.compile(r"[/\\:*?\"<>|\x00-\x1f]")


def root_dir() -> Path:
    raw = os.environ.get("DND_CAMPAIGN_ROOT", "")
    if raw.strip():
        return Path(raw.strip()).expanduser().resolve()
    return Path("~/.claude/dnd").expanduser()


def characters_dir() -> Path:
    d = root_dir() / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_dir_name(name: str) -> str:
    """A character name reduced to something safe to use as a folder.

    Preserves spaces, case, and non-ASCII letters — the folder is meant to
    be readable in a file browser — and only strips what a filesystem
    cannot take. A name that reduces to nothing is rejected.
    """
    cleaned = _UNSAFE.sub("", unicodedata.normalize("NFC", str(name))).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise ValueError(f"character name {name!r} has no usable characters")
    return cleaned[:80]


def char_dir(name: str) -> Path:
    d = characters_dir() / safe_dir_name(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def save_yaml(name: str, sheet: dict) -> Path:
    path = char_dir(name) / "current.yaml"
    text = yaml.safe_dump(sheet, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
    _atomic_write_text(path, text)
    return path


def save_markdown(name: str, text: str) -> Path:
    path = char_dir(name) / "character.md"
    _atomic_write_text(path, text)
    return path


def save_pdf(name: str, data: bytes) -> Path:
    path = char_dir(name) / "character.pdf"
    _atomic_write_bytes(path, data)
    return path


def list_characters() -> list[dict]:
    out = []
    root = characters_dir()
    if not root.exists():
        return out
    for entry in sorted(root.iterdir()):
        current = entry / "current.yaml"
        if not current.is_file():
            continue
        try:
            sheet = yaml.safe_load(current.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        classes = sheet.get("classes") or []
        level = sum(int(c.get("level", 0) or 0) for c in classes if isinstance(c, dict))
        out.append({
            "name": sheet.get("name", entry.name),
            "race": sheet.get("race", ""),
            "classes": classes,
            "level": level,
        })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_storage.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add storage.py tests/test_storage.py
git commit -m "feat: add character storage (YAML/Markdown/PDF)

Same characters_dir() convention as dnd-app-bg-local's paths.py, no import
from that repo — a character saved here is already visible to that repo's
library.py without any migration, once the two are wired together later.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: `sheet_derive.py` — AC, skills, saves, spellcasting numbers

**Files:**
- Create: `sheet_derive.py`
- Test: `tests/test_sheet_derive.py`

**Interfaces:**
- Consumes: `chargen.rules.ability_modifier`, `chargen.rules.proficiency_bonus`,
  `chargen.rules.armor_class`, `chargen.rules.spell_save_dc`,
  `chargen.rules.spell_attack_bonus`, `chargen.rules.skill_bonus` (Task 1);
  a `chargen.build()` sheet dict + the `catalog` and `draft` that produced it
  (the caller — Task 6's `/api/chargen/build` — has both in scope right
  after calling `chargen.build.build(draft, catalog)`)
- Produces: `sheet_derive.derive(sheet: dict, catalog, draft: dict) -> dict`
  returning exactly:
  ```python
  {
    "ac": int,
    "initiative": int,               # == DEX modifier
    "proficiency_bonus": int,
    "passive_perception": int,       # 10 + Perception skill bonus
    "ability_mods": {"STR": int, ...},  # all 6 abilities
    "skills": {"Acrobatics": int, ...},  # all 18 skills -> bonus
    "saves": {"STR": int, ...},          # all 6 abilities -> save bonus
    "spellcasting": {                    # None if the class doesn't cast
        "ability": "WIS", "save_dc": int, "attack_bonus": int
    } | None,
  }
  ```
  Task 4 and Task 5 both call this and consume exactly this shape.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sheet_derive.py
import sheet_derive
from chargen.catalog import Catalog

CATALOG = Catalog.load()


def _fighter_sheet_and_draft():
    """A level-1 Human Fighter (Soldier background), no armor equipped —
    matches build.py's own sheet shape so this test doubles as a shape check."""
    sheet = {
        "name": "Torvin Bracewell",
        "race": "Human",
        "background": "Soldier",
        "classes": [{"cls": "Fighter", "subclass": "", "level": 1}],
        "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                           "INT": 10, "WIS": 12, "CHA": 8},
        "proficiencies": {
            "saving_throws": ["STR", "CON"],
            "skills": ["Athletics", "Intimidation"],
            "armor": ["Light Armor", "Medium Armor", "Heavy Armor", "Shields"],
            "weapons": ["Simple Weapons", "Martial Weapons"],
            "tools": [],
            "languages": ["Common"],
        },
        "equipment": [],
    }
    draft = {"equipped_armor_id": None, "shield": False}
    return sheet, draft


def test_ac_no_armor_is_10_plus_dex_mod():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # DEX 14 -> mod +2 -> AC 12 unarmored
    assert out["ac"] == 12


def test_ac_with_equipped_armor():
    sheet, draft = _fighter_sheet_and_draft()
    chain_shirt = next(a for a in CATALOG.armor() if a["name"] == "Chain Shirt")
    draft = {"equipped_armor_id": chain_shirt["id"], "shield": True}
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Chain Shirt: base_ac 13, medium armor -> dex capped at +2 -> 13+2=15, +2 shield -> 17
    assert out["ac"] == 15 + 2


def test_proficiency_bonus_level_1():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["proficiency_bonus"] == 2


def test_skill_bonus_proficient_vs_not():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Athletics (STR, proficient): mod +3, prof +2 -> +5
    assert out["skills"]["Athletics"] == 5
    # Acrobatics (DEX, not proficient): mod +2, no prof -> +2
    assert out["skills"]["Acrobatics"] == 2


def test_save_bonus_proficient_vs_not():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # STR save (proficient): mod +3, prof +2 -> +5
    assert out["saves"]["STR"] == 5
    # DEX save (not proficient): mod +2, no prof -> +2
    assert out["saves"]["DEX"] == 2


def test_passive_perception():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Perception (WIS 12 -> mod +1, not proficient) -> 10 + 1 = 11
    assert out["passive_perception"] == 11


def test_non_caster_has_no_spellcasting_block():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["spellcasting"] is None


def test_caster_has_spellcasting_block():
    sheet = {
        "name": "Sylwen Nightbrook",
        "race": "Wood Elf",
        "background": "Acolyte",
        "classes": [{"cls": "Cleric", "subclass": "Life", "level": 1}],
        "ability_scores": {"STR": 10, "DEX": 12, "CON": 14,
                           "INT": 10, "WIS": 16, "CHA": 12},
        "proficiencies": {
            "saving_throws": ["WIS", "CHA"], "skills": ["Insight", "Religion"],
            "armor": [], "weapons": [], "tools": [], "languages": [],
        },
        "equipment": [],
    }
    draft = {"equipped_armor_id": None, "shield": False}
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["spellcasting"] is not None
    assert out["spellcasting"]["ability"] == "WIS"
    # WIS 16 -> mod +3, prof +2 -> DC 8+2+3=13, atk +2+3=5
    assert out["spellcasting"]["save_dc"] == 13
    assert out["spellcasting"]["attack_bonus"] == 5
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_sheet_derive.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sheet_derive'`

- [ ] **Step 3: Write `sheet_derive.py`**

```python
"""Derived combat/skill numbers a printed character sheet needs that
chargen.build()'s sheet dict deliberately omits (AC and friends — the
source repo's play engine derives them live from equipped gear during
play; this app has no live engine, so it derives them once, at export
time, from the same sheet + the catalog/draft that built it).

Imports nothing outside chargen + the standard library.
"""
from __future__ import annotations

from chargen import rules
from chargen.catalog import Catalog

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# Fixed 5e SRD skill -> governing ability. Not derived from any catalog
# file because chargen has no such table; this is the standard, unchanging
# 5e SRD list (18 skills), safe to hardcode.
SKILL_ABILITY = {
    "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
    "Athletics": "STR", "Deception": "CHA", "History": "INT",
    "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
    "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
    "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
    "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS",
}

CASTING_ABILITY = {
    "Bard": "CHA", "Cleric": "WIS", "Druid": "WIS", "Paladin": "CHA",
    "Ranger": "WIS", "Sorcerer": "CHA", "Warlock": "CHA", "Wizard": "INT",
}


def _total_level(sheet: dict) -> int:
    classes = sheet.get("classes") or []
    return sum(int(c.get("level", 0) or 0) for c in classes if isinstance(c, dict))


def derive(sheet: dict, catalog: Catalog, draft: dict) -> dict:
    scores = sheet.get("ability_scores") or {}
    mods = {a: rules.ability_modifier(int(scores.get(a, 10))) for a in ABILITIES}

    level = _total_level(sheet) or 1
    prof = rules.proficiency_bonus(level)

    armor = None
    armor_id = draft.get("equipped_armor_id")
    if armor_id:
        armor = next((a for a in catalog.armor() if a["id"] == armor_id), None)
    shield = bool(draft.get("shield"))
    ac = rules.armor_class(mods["DEX"], armor, shield)

    proficiencies = sheet.get("proficiencies") or {}
    prof_skills = set(proficiencies.get("skills") or [])
    prof_saves = set(proficiencies.get("saving_throws") or [])

    skills = {
        name: rules.skill_bonus(mods[ability], name in prof_skills, False, prof)
        for name, ability in SKILL_ABILITY.items()
    }
    saves = {
        a: mods[a] + (prof if a in prof_saves else 0)
        for a in ABILITIES
    }
    passive_perception = 10 + skills["Perception"]

    spellcasting = None
    classes = sheet.get("classes") or []
    if classes:
        cls_name = classes[0].get("cls", "")
        ability = CASTING_ABILITY.get(cls_name)
        if ability:
            spellcasting = {
                "ability": ability,
                "save_dc": rules.spell_save_dc(prof, mods[ability]),
                "attack_bonus": rules.spell_attack_bonus(prof, mods[ability]),
            }

    return {
        "ac": ac,
        "initiative": mods["DEX"],
        "proficiency_bonus": prof,
        "passive_perception": passive_perception,
        "ability_mods": mods,
        "skills": skills,
        "saves": saves,
        "spellcasting": spellcasting,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_sheet_derive.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add sheet_derive.py tests/test_sheet_derive.py
git commit -m "feat: derive AC/skills/saves/spellcasting for a built sheet

Calls chargen.rules (already has armor_class/proficiency_bonus/spell_save_dc/
spell_attack_bonus/skill_bonus) rather than reimplementing 5e formulas or
porting the play engine's char_state_derive.py and its dependency chain.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: `markdown_render.py` — fresh Markdown export

**Files:**
- Create: `markdown_render.py`
- Test: `tests/test_markdown_render.py`

**Interfaces:**
- Consumes: a `chargen.build()` sheet dict + a `sheet_derive.derive()` output
  dict (Task 3's exact shape)
- Produces: `markdown_render.render(sheet: dict, derived: dict) -> str`
  — Task 6 calls this and saves the result via `storage.save_markdown()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_markdown_render.py
import markdown_render

SHEET = {
    "name": "Torvin Bracewell",
    "player": "",
    "race": "Human",
    "background": "Soldier",
    "alignment": "Lawful Good",
    "classes": [{"cls": "Fighter", "subclass": "", "level": 1}],
    "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                       "INT": 10, "WIS": 12, "CHA": 8},
    "combat": {"hp_current": 12, "hp_max": 12, "hp_temp": 0, "speed": 30,
              "death_saves": {"successes": 0, "failures": 0},
              "hit_dice": [{"cls": "Fighter", "die": 10, "used": 0}]},
    "proficiencies": {"saving_throws": ["STR", "CON"],
                      "skills": ["Athletics", "Intimidation"],
                      "armor": ["Light Armor"], "weapons": ["Simple Weapons"],
                      "tools": [], "languages": ["Common"]},
    "personality": {"traits": "Brave", "ideals": "Honor",
                    "bonds": "My squad", "flaws": "Reckless"},
    "features_traits": [{"name": "Second Wind", "description": "Once per rest...",
                         "source": "Class"}],
    "backstory": "A soldier from the border wars.",
    "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 15, "pp": 0},
    "equipment": [{"name": "Chain Shirt", "equipped": True, "quantity": 1},
                  {"name": "Longsword", "equipped": False, "quantity": 1}],
    "spellcasting": [], "spells": [], "spell_slots": {},
}
DERIVED = {
    "ac": 15, "initiative": 2, "proficiency_bonus": 2, "passive_perception": 11,
    "ability_mods": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
    "skills": {"Athletics": 5, "Intimidation": 1},
    "saves": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
    "spellcasting": None,
}


def test_render_includes_name_heading():
    out = markdown_render.render(SHEET, DERIVED)
    assert out.startswith("# Torvin Bracewell\n")


def test_render_includes_hp_line():
    out = markdown_render.render(SHEET, DERIVED)
    assert "**HP:** 12 / 12" in out


def test_render_includes_ac_and_combat_stats():
    out = markdown_render.render(SHEET, DERIVED)
    assert "**AC:** 15" in out
    assert "**Initiative:** +2" in out
    assert "**Speed:** 30" in out
    assert "**Passive Perception:** 11" in out


def test_render_includes_ability_scores_and_mods():
    out = markdown_render.render(SHEET, DERIVED)
    assert "STR 16 (+3)" in out


def test_render_includes_skills_with_bonus():
    out = markdown_render.render(SHEET, DERIVED)
    assert "Athletics" in out and "+5" in out


def test_render_includes_equipment_and_features_and_backstory():
    out = markdown_render.render(SHEET, DERIVED)
    assert "Chain Shirt" in out
    assert "Second Wind" in out
    assert "A soldier from the border wars." in out


def test_render_omits_spellcasting_section_for_non_caster():
    out = markdown_render.render(SHEET, DERIVED)
    assert "## Spellcasting" not in out


def test_render_includes_spellcasting_section_for_caster():
    caster_sheet = dict(SHEET)
    caster_sheet["classes"] = [{"cls": "Cleric", "subclass": "Life", "level": 1}]
    caster_sheet["spells"] = [{"name": "Cure Wounds", "cls": "Cleric", "prepared": True}]
    caster_derived = dict(DERIVED)
    caster_derived["spellcasting"] = {"ability": "WIS", "save_dc": 13, "attack_bonus": 5}
    out = markdown_render.render(caster_sheet, caster_derived)
    assert "## Spellcasting" in out
    assert "Cure Wounds" in out
    assert "Save DC 13" in out
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_markdown_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'markdown_render'`

- [ ] **Step 3: Write `markdown_render.py`**

```python
"""Fresh Markdown character-sheet renderer — takes a chargen.build() sheet
dict plus a sheet_derive.derive() dict, returns a Markdown string. Not a
port of dnd-app-bg-local's library.py::_render_markdown() (that function is
a fragile bridge into the play engine's char_state_sync module); this is a
self-contained renderer scoped to exactly what chargen + sheet_derive
produce.

Imports nothing outside the standard library.
"""
from __future__ import annotations


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _classes_line(sheet: dict) -> str:
    parts = []
    for c in sheet.get("classes") or []:
        piece = c.get("cls", "")
        if c.get("subclass"):
            piece += f" ({c['subclass']})"
        piece += f" {c.get('level', '')}"
        parts.append(piece.strip())
    return " / ".join(parts)


def render(sheet: dict, derived: dict) -> str:
    combat = sheet.get("combat") or {}
    scores = sheet.get("ability_scores") or {}
    mods = derived.get("ability_mods") or {}
    lines: list[str] = []

    lines.append(f"# {sheet.get('name', '')}")
    lines.append("")
    player = sheet.get("player") or "—"
    lines.append(f"**Player:** {player}  |  **Race:** {sheet.get('race', '')}  |  "
                 f"**Class:** {_classes_line(sheet)}  |  "
                 f"**Background:** {sheet.get('background', '')}  |  "
                 f"**Alignment:** {sheet.get('alignment', '')}")
    lines.append("")

    lines.append("## Combat")
    lines.append(f"- **HP:** {combat.get('hp_current', 1)} / {combat.get('hp_max', 1)}"
                 f" (temp {combat.get('hp_temp', 0)})")
    lines.append(f"- **AC:** {derived.get('ac', 10)}  |  "
                 f"**Initiative:** {_fmt_mod(derived.get('initiative', 0))}  |  "
                 f"**Speed:** {combat.get('speed', 30)}  |  "
                 f"**Passive Perception:** {derived.get('passive_perception', 10)}  |  "
                 f"**Proficiency Bonus:** {_fmt_mod(derived.get('proficiency_bonus', 2))}")
    lines.append("")

    lines.append("## Ability Scores")
    ability_line = "  ".join(
        f"**{a}** {scores.get(a, 10)} ({_fmt_mod(mods.get(a, 0))})"
        for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    )
    lines.append(ability_line)
    lines.append("")

    lines.append("## Saving Throws")
    saves = derived.get("saves") or {}
    lines.append("  ".join(f"**{a}** {_fmt_mod(v)}" for a, v in saves.items()))
    lines.append("")

    lines.append("## Skills")
    skills = derived.get("skills") or {}
    for name in sorted(skills):
        lines.append(f"- {name}: {_fmt_mod(skills[name])}")
    lines.append("")

    proficiencies = sheet.get("proficiencies") or {}
    lines.append("## Proficiencies & Languages")
    lines.append(f"- **Armor:** {', '.join(proficiencies.get('armor') or []) or '—'}")
    lines.append(f"- **Weapons:** {', '.join(proficiencies.get('weapons') or []) or '—'}")
    lines.append(f"- **Tools:** {', '.join(proficiencies.get('tools') or []) or '—'}")
    lines.append(f"- **Languages:** {', '.join(proficiencies.get('languages') or []) or '—'}")
    lines.append("")

    lines.append("## Equipment")
    for item in sheet.get("equipment") or []:
        tag = " (equipped)" if item.get("equipped") else ""
        qty = item.get("quantity", 1)
        qty_tag = f" x{qty}" if qty and qty != 1 else ""
        lines.append(f"- {item.get('name', '')}{qty_tag}{tag}")
    lines.append("")

    currency = sheet.get("currency") or {}
    lines.append("## Currency")
    lines.append(", ".join(f"{currency.get(k, 0)} {k.upper()}"
                           for k in ("cp", "sp", "ep", "gp", "pp")))
    lines.append("")

    spellcasting = derived.get("spellcasting")
    if spellcasting:
        lines.append("## Spellcasting")
        lines.append(f"- **Ability:** {spellcasting['ability']}  |  "
                     f"**Save DC** {spellcasting['save_dc']}  |  "
                     f"**Attack Bonus** {_fmt_mod(spellcasting['attack_bonus'])}")
        for spell in sheet.get("spells") or []:
            prepared_tag = " (prepared)" if spell.get("prepared") else ""
            lines.append(f"- {spell.get('name', '')}{prepared_tag}")
        lines.append("")

    lines.append("## Features & Traits")
    for feature in sheet.get("features_traits") or []:
        text = f" — {feature['description']}" if feature.get("description") else ""
        lines.append(f"- **{feature.get('name', '')}** ({feature.get('source', '')}){text}")
    lines.append("")

    personality = sheet.get("personality") or {}
    lines.append("## Personality")
    lines.append(f"- **Traits:** {personality.get('traits', '') or '—'}")
    lines.append(f"- **Ideals:** {personality.get('ideals', '') or '—'}")
    lines.append(f"- **Bonds:** {personality.get('bonds', '') or '—'}")
    lines.append(f"- **Flaws:** {personality.get('flaws', '') or '—'}")
    lines.append("")

    lines.append("## Backstory")
    lines.append(sheet.get("backstory") or "—")
    lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_markdown_render.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add markdown_render.py tests/test_markdown_render.py
git commit -m "feat: add fresh Markdown character sheet renderer

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `pdf_fill.py` — fill the official WotC sheet

**Files:**
- Create: `pdf_fill.py`
- Test: `tests/test_pdf_fill.py`

**Interfaces:**
- Consumes: a `chargen.build()` sheet dict + a `sheet_derive.derive()` output
  dict; `assets/character-sheet-template.pdf` (committed in Task... actually
  already committed to the repo root's `assets/` before this plan — verify
  it's present at that path; if missing, it must be re-added before this
  task can proceed, since there is no other copy to fall back to)
- Produces: `pdf_fill.fill(sheet: dict, derived: dict) -> bytes` — Task 6
  calls this and saves the result via `storage.save_pdf()`.

- [ ] **Step 1: Verify the template exists**

Run: `ls -la /Users/yoanpetrov/dnd-character-creator/assets/character-sheet-template.pdf`
Expected: the file exists (~380KB). If missing, stop and re-fetch it from
`https://media.wizards.com/2022/dnd/downloads/DnD_5E_CharacterSheet_FormFillable.pdf`
before continuing — do not proceed without it, there is nothing to fill.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_pdf_fill.py
from pathlib import Path

from pypdf import PdfReader

import pdf_fill

SHEET = {
    "name": "Torvin Bracewell",
    "player": "Yoan",
    "race": "Human",
    "background": "Soldier",
    "alignment": "Lawful Good",
    "classes": [{"cls": "Fighter", "subclass": "", "level": 1}],
    "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                       "INT": 10, "WIS": 12, "CHA": 8},
    "combat": {"hp_current": 12, "hp_max": 12, "hp_temp": 0, "speed": 30,
              "death_saves": {"successes": 0, "failures": 0},
              "hit_dice": [{"cls": "Fighter", "die": 10, "used": 0}]},
    "proficiencies": {"saving_throws": ["STR", "CON"],
                      "skills": ["Athletics", "Intimidation"],
                      "armor": ["Light Armor"], "weapons": ["Simple Weapons"],
                      "tools": [], "languages": ["Common"]},
    "personality": {"traits": "Brave", "ideals": "Honor",
                    "bonds": "My squad", "flaws": "Reckless"},
    "features_traits": [{"name": "Second Wind", "description": "", "source": "Class"}],
    "backstory": "A soldier from the border wars.",
    "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 15, "pp": 0},
    "equipment": [{"name": "Chain Shirt", "equipped": True, "quantity": 1},
                  {"name": "Longsword", "equipped": False, "quantity": 1}],
    "spellcasting": [], "spells": [], "spell_slots": {},
}
DERIVED = {
    "ac": 15, "initiative": 2, "proficiency_bonus": 2, "passive_perception": 11,
    "ability_mods": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
    "skills": {"Acrobatics": 2, "Animal Handling": 1, "Arcana": 0, "Athletics": 5,
              "Deception": -1, "History": 0, "Insight": 1, "Intimidation": 1,
              "Investigation": 0, "Medicine": 1, "Nature": 0, "Perception": 1,
              "Performance": -1, "Persuasion": -1, "Religion": 0,
              "Sleight of Hand": 2, "Stealth": 2, "Survival": 1},
    "saves": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
    "spellcasting": None,
}


def _fill_and_read_fields():
    data = pdf_fill.fill(SHEET, DERIVED)
    import io
    reader = PdfReader(io.BytesIO(data))
    fields = reader.get_fields() or {}
    return {k: (v.get("/V") if isinstance(v, dict) else None) for k, v in fields.items()}


def test_fill_returns_pdf_bytes():
    data = pdf_fill.fill(SHEET, DERIVED)
    assert data[:4] == b"%PDF"


def test_fill_identity_fields():
    values = _fill_and_read_fields()
    assert values["CharacterName"] == "Torvin Bracewell"
    assert values["PlayerName"] == "Yoan"
    assert values["Race "] == "Human"
    assert values["Background"] == "Soldier"
    assert values["Alignment"] == "Lawful Good"
    assert values["ClassLevel"] == "Fighter 1"


def test_fill_ability_scores_and_mods():
    values = _fill_and_read_fields()
    assert values["STR"] == "16"
    assert values["STRmod"] == "+3"
    assert values["DEXmod "] == "+2"
    # the real quirk in this PDF's own field naming — not a typo in this code
    assert values["CHamod"] == "-1"


def test_fill_saves_and_skills():
    values = _fill_and_read_fields()
    assert values["ST Strength"] == "+5"
    assert values["Athletics"] == "+5"
    assert values["Animal"] == "+1"


def test_fill_combat_stats():
    values = _fill_and_read_fields()
    assert values["AC"] == "15"
    assert values["Initiative"] == "+2"
    assert values["Speed"] == "30"
    assert values["HPMax"] == "12"
    assert values["HPCurrent"] == "12"
    assert values["Passive"] == "11"
    assert values["ProfBonus"] == "+2"


def test_fill_equipment_and_backstory_text_blobs():
    values = _fill_and_read_fields()
    assert "Chain Shirt" in values["Equipment"]
    assert "Longsword" in values["Equipment"]
    assert values["Backstory"] == "A soldier from the border wars."


def test_fill_leaves_spell_fields_untouched_for_non_caster():
    values = _fill_and_read_fields()
    assert values.get("Spellcasting Class 2") in (None, "")


def test_fill_populates_spellcasting_for_caster():
    caster_sheet = dict(SHEET)
    caster_sheet["classes"] = [{"cls": "Cleric", "subclass": "Life", "level": 1}]
    caster_derived = dict(DERIVED)
    caster_derived["spellcasting"] = {"ability": "WIS", "save_dc": 13, "attack_bonus": 5}
    data = pdf_fill.fill(caster_sheet, caster_derived)
    import io
    reader = PdfReader(io.BytesIO(data))
    fields = reader.get_fields() or {}
    values = {k: (v.get("/V") if isinstance(v, dict) else None) for k, v in fields.items()}
    assert values["Spellcasting Class 2"] == "Cleric"
    assert values["SpellcastingAbility 2"] == "WIS"
    assert values["SpellSaveDC  2"] == "13"
    assert values["SpellAtkBonus 2"] == "+5"
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_pdf_fill.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdf_fill'`

- [ ] **Step 4: Write `pdf_fill.py`**

```python
"""Fills assets/character-sheet-template.pdf (the official Wizards of the
Coast fillable 2014-ruleset sheet) from a chargen.build() sheet dict + a
sheet_derive.derive() dict, via pypdf's AcroForm field API.

Field names below are copied verbatim from this exact PDF's own AcroForm
(inspected with pypdf.PdfReader.get_fields() against
assets/character-sheet-template.pdf) — including two real quirks in the
PDF itself: the Dex-modifier field is "DEXmod " (trailing space) and the
Charisma-modifier field is "CHamod" (lowercase "h"). These are not typos
in this module; changing them to the "obviously correct" spelling would
silently stop the fill from having any effect on those two fields.

Deliberately does not populate: per-spell-level slot boxes
("SlotsTotal 19".."SlotsTotal 27") or the individual spell-list rows
("Spells 10100".."Spells 1080") — their field-to-spell-level mapping isn't
documented anywhere and isn't safely inferrable without visually matching
widget positions on the rendered page; getting it wrong would silently put
a caster's 3rd-level spell in the 1st-level box. The Markdown export
(markdown_render.py) is the complete reference for spells; this PDF covers
everything else a printed sheet needs.

Imports nothing outside chargen + pypdf + the standard library.
"""
from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter

_TEMPLATE = Path(__file__).resolve().parent / "assets" / "character-sheet-template.pdf"

_SKILL_FIELD = {
    "Acrobatics": "Acrobatics", "Animal Handling": "Animal", "Arcana": "Arcana",
    "Athletics": "Athletics", "Deception": "Deception ", "History": "History ",
    "Insight": "Insight", "Intimidation": "Intimidation",
    "Investigation": "Investigation ", "Medicine": "Medicine", "Nature": "Nature",
    "Perception": "Perception ", "Performance": "Performance",
    "Persuasion": "Persuasion", "Religion": "Religion",
    "Sleight of Hand": "SleightofHand", "Stealth": "Stealth ", "Survival": "Survival",
}

_SAVE_FIELD = {
    "STR": "ST Strength", "DEX": "ST Dexterity", "CON": "ST Constitution",
    "INT": "ST Intelligence", "WIS": "ST Wisdom", "CHA": "ST Charisma",
}

# Real quirks in this specific PDF's field names — see module docstring.
_MOD_FIELD = {
    "STR": "STRmod", "DEX": "DEXmod ", "CON": "CONmod",
    "INT": "INTmod", "WIS": "WISmod", "CHA": "CHamod",
}


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _classlevel_text(sheet: dict) -> str:
    classes = sheet.get("classes") or []
    if not classes:
        return ""
    c = classes[0]
    text = c.get("cls", "")
    if c.get("subclass"):
        text += f" ({c['subclass']})"
    return f"{text} {c.get('level', '')}".strip()


def _equipment_text(sheet: dict) -> str:
    lines = []
    for item in sheet.get("equipment") or []:
        qty = item.get("quantity", 1)
        qty_tag = f" x{qty}" if qty and qty != 1 else ""
        tag = " (equipped)" if item.get("equipped") else ""
        lines.append(f"{item.get('name', '')}{qty_tag}{tag}")
    return "\n".join(lines)


def _features_text(sheet: dict) -> str:
    lines = []
    for feature in sheet.get("features_traits") or []:
        text = feature.get("name", "")
        if feature.get("description"):
            text += f": {feature['description']}"
        lines.append(text)
    return "\n".join(lines)


def _proficiencies_text(sheet: dict) -> str:
    p = sheet.get("proficiencies") or {}
    parts = []
    if p.get("armor"):
        parts.append("Armor: " + ", ".join(p["armor"]))
    if p.get("weapons"):
        parts.append("Weapons: " + ", ".join(p["weapons"]))
    if p.get("tools"):
        parts.append("Tools: " + ", ".join(p["tools"]))
    if p.get("languages"):
        parts.append("Languages: " + ", ".join(p["languages"]))
    return "\n".join(parts)


def fill(sheet: dict, derived: dict) -> bytes:
    reader = PdfReader(str(_TEMPLATE))
    writer = PdfWriter()
    writer.append(reader)

    scores = sheet.get("ability_scores") or {}
    mods = derived.get("ability_mods") or {}
    combat = sheet.get("combat") or {}
    currency = sheet.get("currency") or {}
    personality = sheet.get("personality") or {}
    skills = derived.get("skills") or {}
    saves = derived.get("saves") or {}

    values: dict[str, str] = {
        "CharacterName": sheet.get("name", ""),
        "PlayerName": sheet.get("player", ""),
        "Race ": sheet.get("race", ""),
        "Background": sheet.get("background", ""),
        "Alignment": sheet.get("alignment", ""),
        "ClassLevel": _classlevel_text(sheet),
        "AC": str(derived.get("ac", "")),
        "Initiative": _fmt_mod(derived.get("initiative", 0)),
        "Speed": str(combat.get("speed", "")),
        "HPMax": str(combat.get("hp_max", "")),
        "HPCurrent": str(combat.get("hp_current", "")),
        "HPTemp": str(combat.get("hp_temp", 0)),
        "HD": "".join(f"{h.get('die', '')}" for h in combat.get("hit_dice") or [])[:1]
              and f"1d{(combat.get('hit_dice') or [{}])[0].get('die', '')}",
        "HDTotal": str(sum(c.get("level", 0) for c in sheet.get("classes") or [])),
        "ProfBonus": _fmt_mod(derived.get("proficiency_bonus", 2)),
        "Passive": str(derived.get("passive_perception", 10)),
        "Inspiration": "1" if (sheet.get("conditions") or {}).get("inspiration") else "",
        "CP": str(currency.get("cp", 0)), "SP": str(currency.get("sp", 0)),
        "EP": str(currency.get("ep", 0)), "GP": str(currency.get("gp", 0)),
        "PP": str(currency.get("pp", 0)),
        "Equipment": _equipment_text(sheet),
        "Features and Traits": _features_text(sheet),
        "ProficienciesLang": _proficiencies_text(sheet),
        "PersonalityTraits ": personality.get("traits", ""),
        "Ideals": personality.get("ideals", ""),
        "Bonds": personality.get("bonds", ""),
        "Flaws": personality.get("flaws", ""),
        "Backstory": sheet.get("backstory", ""),
    }

    for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
        values[ability] = str(scores.get(ability, 10))
        values[_MOD_FIELD[ability]] = _fmt_mod(mods.get(ability, 0))
        values[_SAVE_FIELD[ability]] = _fmt_mod(saves.get(ability, 0))

    for skill_name, field_name in _SKILL_FIELD.items():
        if skill_name in skills:
            values[field_name] = _fmt_mod(skills[skill_name])

    weapon_names = [i["name"] for i in (sheet.get("equipment") or [])][:3]
    wpn_fields = ["Wpn Name", "Wpn Name 2", "Wpn Name 3"]
    for name, field in zip(weapon_names, wpn_fields):
        values[field] = name

    spellcasting = derived.get("spellcasting")
    classes = sheet.get("classes") or []
    if spellcasting and classes:
        values["Spellcasting Class 2"] = classes[0].get("cls", "")
        values["SpellcastingAbility 2"] = spellcasting["ability"]
        values["SpellSaveDC  2"] = str(spellcasting["save_dc"])
        values["SpellAtkBonus 2"] = _fmt_mod(spellcasting["attack_bonus"])

    for page in writer.pages:
        writer.update_page_form_field_values(page, values)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
```

  Note on the `"HD"` line above: it computes a `"1dN"` string only when
  `hit_dice` is non-empty, else falls back to the `and` short-circuit
  producing an empty string — this is intentionally terse to keep the dict
  literal one expression per key; if a reviewer finds it unclear, replacing
  it with a small helper function above `fill()` is a fine simplification,
  just keep the same behavior (empty string when `hit_dice` is empty,
  `"1d<die>"` from the first entry otherwise).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_pdf_fill.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add pdf_fill.py tests/test_pdf_fill.py
git commit -m "feat: fill the official WotC PDF sheet from a built character

Field names verified against assets/character-sheet-template.pdf's own
AcroForm (pypdf get_fields()), including two real quirks in that PDF
(DEXmod trailing space, CHamod lowercase h). Spell-slot boxes and the
individual spell-list rows are deliberately left unfilled — no reliable
field-to-spell-level mapping without visual inspection; Markdown is the
complete spell reference instead.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `app.py` — the Flask app

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `chargen.catalog.Catalog`, `chargen.build.build`,
  `sheet_derive.derive`, `markdown_render.render`, `pdf_fill.fill`,
  `storage.save_yaml`/`save_markdown`/`save_pdf`/`list_characters` (all
  earlier tasks)
- Produces: the Flask app object `app`, importable as `from app import app`
  for the test client; the HTTP routes below.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app.py
import io
import json

import pytest

from app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _human_fighter_draft():
    # ids/casing verified directly against chargen/data/srd/*.json: only
    # "acolyte" exists in the bundled SRD backgrounds (no "soldier"); race
    # id "human" and class id "fighter" are confirmed lowercase index
    # values; skill_picks values are Title Case ("Athletics", not
    # "athletics") because chargen.normalise.class_from_5ebits strips the
    # "Skill: " prefix off the raw SRD name and keeps its casing as-is.
    return {
        "name": "Torvin Bracewell", "player": "Yoan",
        "race_id": "human", "background_id": "acolyte",
        "class_id": "fighter", "level": 1,
        "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                           "INT": 10, "WIS": 12, "CHA": 8},
        "skill_picks": ["Athletics", "Intimidation"],
        "alignment": "Lawful Good",
    }


def test_index_serves_builder_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"chargen" in resp.data.lower() or b"builder" in resp.data.lower()


def test_catalog_endpoint(client):
    resp = client.get("/api/chargen/catalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "races" in body and "classes" in body and "backgrounds" in body


def test_preview_does_not_save(client, tmp_path):
    resp = client.post("/api/chargen/preview", json=_human_fighter_draft())
    assert resp.status_code == 200
    assert not (tmp_path / "characters").exists()


def test_build_with_illegal_draft_returns_400(client):
    resp = client.post("/api/chargen/build", json={"name": "Nobody"})
    assert resp.status_code == 400
    assert "problems" in resp.get_json()


def test_build_saves_all_three_formats(client, tmp_path):
    resp = client.post("/api/chargen/build", json=_human_fighter_draft())
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["ok"] is True
    yaml_path = tmp_path / "characters" / "Torvin Bracewell" / "current.yaml"
    md_path = tmp_path / "characters" / "Torvin Bracewell" / "character.md"
    pdf_path = tmp_path / "characters" / "Torvin Bracewell" / "character.pdf"
    assert yaml_path.exists() and yaml_path.stat().st_size > 0
    assert md_path.exists() and md_path.stat().st_size > 0
    assert pdf_path.exists() and pdf_path.read_bytes()[:4] == b"%PDF"


def test_characters_list_endpoint(client):
    client.post("/api/chargen/build", json=_human_fighter_draft())
    resp = client.get("/api/characters")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.get_json()]
    assert "Torvin Bracewell" in names


def test_download_endpoints(client):
    client.post("/api/chargen/build", json=_human_fighter_draft())
    for fmt, prefix in (("yaml", b"name:"), ("md", b"#"), ("pdf", b"%PDF")):
        resp = client.get(f"/api/characters/Torvin Bracewell/{fmt}")
        assert resp.status_code == 200, (fmt, resp.get_json() if resp.is_json else resp.data)
        assert resp.data.startswith(prefix) or prefix in resp.data[:200]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write `app.py`**

```python
"""Thin Flask shell around chargen + sheet_derive + the two export
renderers + storage. All character-mechanics logic lives in chargen;
this module only wires HTTP onto it.
"""
from __future__ import annotations

import dataclasses

from flask import Flask, jsonify, request, render_template, Response

from chargen.build import build
from chargen.catalog import Catalog
import sheet_derive
import markdown_render
import pdf_fill
import storage

app = Flask(__name__)

_CATALOG = Catalog.load()


@app.route("/")
def index():
    return render_template("builder.html")


@app.route("/api/chargen/catalog")
def api_catalog():
    # Catalog.races()/classes()/backgrounds() all return frozen dataclasses
    # (Race/CharClass/Background) — dataclasses.asdict() recurses through
    # their nested Trait/Subrace/ClassLevelRow fields too, which a plain
    # .__dict__ would not (frozen dataclasses still expose .__dict__, but
    # it only shallow-copies top-level fields, leaving nested dataclass
    # instances un-serializable by jsonify).
    return jsonify({
        "races": [dataclasses.asdict(r) for r in _CATALOG.races()],
        "classes": [dataclasses.asdict(c) for c in _CATALOG.classes()],
        "backgrounds": [dataclasses.asdict(b) for b in _CATALOG.backgrounds()],
    })


@app.route("/api/chargen/spells")
def api_spells():
    return jsonify({"spells": [dataclasses.asdict(s) for s in _CATALOG.spells()]})


@app.route("/api/chargen/equipment")
def api_equipment():
    # armor() already returns plain dicts (see chargen/catalog.py's
    # _armor_from_5ebits) — no asdict() needed there, unlike weapons/gear.
    return jsonify({
        "armor": _CATALOG.armor(),
        "weapons": [dataclasses.asdict(w) for w in _CATALOG.weapons()],
        "gear": [dataclasses.asdict(g) for g in _CATALOG.gear()],
    })


@app.route("/api/chargen/preview", methods=["POST"])
def api_preview():
    draft = request.get_json(silent=True) or {}
    sheet, problems, warnings = build(draft, _CATALOG)
    if problems:
        return jsonify({"problems": problems, "warnings": warnings}), 400
    return jsonify({"sheet": sheet, "warnings": warnings})


@app.route("/api/chargen/build", methods=["POST"])
def api_build():
    draft = request.get_json(silent=True) or {}
    sheet, problems, warnings = build(draft, _CATALOG)
    if problems:
        return jsonify({"problems": problems, "warnings": warnings}), 400

    derived = sheet_derive.derive(sheet, _CATALOG, draft)
    yaml_path = storage.save_yaml(sheet["name"], sheet)
    md_text = markdown_render.render(sheet, derived)
    md_path = storage.save_markdown(sheet["name"], md_text)
    pdf_bytes = pdf_fill.fill(sheet, derived)
    pdf_path = storage.save_pdf(sheet["name"], pdf_bytes)

    return jsonify({
        "ok": True, "warnings": warnings,
        "yaml_path": str(yaml_path), "md_path": str(md_path), "pdf_path": str(pdf_path),
    }), 201


@app.route("/api/characters")
def api_characters():
    return jsonify(storage.list_characters())


_FMT_CONTENT_TYPE = {
    "yaml": "application/x-yaml", "md": "text/markdown", "pdf": "application/pdf",
}
_FMT_FILENAME = {"yaml": "current.yaml", "md": "character.md", "pdf": "character.pdf"}


@app.route("/api/characters/<name>/<fmt>")
def api_character_download(name: str, fmt: str):
    if fmt not in _FMT_FILENAME:
        return jsonify({"error": f"unknown format {fmt!r}"}), 400
    path = storage.char_dir(name) / _FMT_FILENAME[fmt]
    if not path.exists():
        return jsonify({"error": "not found"}), 404
    mode = "rb" if fmt == "pdf" else "r"
    encoding = None if fmt == "pdf" else "utf-8"
    with open(path, mode, encoding=encoding) as f:
        data = f.read()
    return Response(data, mimetype=_FMT_CONTENT_TYPE[fmt])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5300, debug=True)
```

- [ ] **Step 4: Create `templates/` directory placeholder for the test to find**

Task 7 writes the real `templates/builder.html`; for this task's own test
(`test_index_serves_builder_page`) to pass without waiting on Task 7, create
a minimal stand-in now:

```bash
mkdir -p /Users/yoanpetrov/dnd-character-creator/templates
cat > /Users/yoanpetrov/dnd-character-creator/templates/builder.html <<'EOF'
<!doctype html>
<title>Character Builder</title>
<p>chargen builder placeholder — replaced in a later task.</p>
EOF
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/test_app.py -v`
Expected: all PASS — the draft shape in `_human_fighter_draft()` (ids,
casing, key names) was verified directly against `chargen/validate.py` and
`chargen/data/srd/*.json` while writing this plan (human/fighter/acolyte
all confirmed to exist with those exact lowercase ids; `skill_picks` values
are Title Case because `chargen.normalise.class_from_5ebits` keeps the raw
SRD name's casing after stripping the "Skill: " prefix). If a test still
fails, something in the ported `chargen/` differs from what was inspected
in `dnd-app-bg-local` — diff the two copies before assuming the test data
is wrong.

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add app.py templates/builder.html tests/test_app.py
git commit -m "feat: add the Flask app wiring chargen + exports together

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Port and trim `builder.html`

**Files:**
- Modify: `templates/builder.html` (replace Task 6's placeholder)
- Reference only (read, don't modify): `/Users/yoanpetrov/dnd-app-bg-local/skills/dnd/display/templates/builder.html`

**Interfaces:**
- Consumes: the same `/api/chargen/*` endpoints Task 6 built (the ported
  JS in `builder.html` already only calls these — no interface change needed
  on the JS side, only the three cross-app links noted below)
- Produces: the real builder UI Task 6's `index()` route serves.

- [ ] **Step 1: Copy the source file**

```bash
cp /Users/yoanpetrov/dnd-app-bg-local/skills/dnd/display/templates/builder.html \
   /Users/yoanpetrov/dnd-character-creator/templates/builder.html
```

- [ ] **Step 2: Remove the three cross-app links**

Open `templates/builder.html` and find these three lines (confirmed present
at these approximate locations in the source file — search for the text if
line numbers have shifted):

1. Around line 238: `<p class="version">Версия <b>{{ version }}</b> · <a href="/menu">← към началото</a></p>`
   → remove the `<a href="/menu">← към началото</a>` part (and the `·`
   separator before it), keep the version line itself only if `{{ version }}`
   is still meaningful here — if not (this app has no version concept yet),
   remove the whole `<p class="version">` line.
2. Around line 401: `<a href="/menu">← Начало</a> · <a href="/">Към екрана на играта →</a>`
   → remove this whole line — there is no `/menu` or play screen in this app.
3. Around line 1154: `<a href="/menu" class="act" style="margin-left:10px">Виж го в „Герои" →</a>`
   → replace with static text (no link, since there's no library-browsing
   page yet in this app): `<span class="act" style="margin-left:10px">Записан</span>`
   (or leave this step's exact replacement to the implementer's judgment —
   the important part is removing the dead `/menu` link, not the exact
   wording of what replaces it).

- [ ] **Step 3: Verify no other cross-app references remain**

Run: `grep -n 'href="/menu"\|href="/"' /Users/yoanpetrov/dnd-character-creator/templates/builder.html`
Expected: no output (empty). If anything remains, remove/adapt it the same way.

- [ ] **Step 4: Verify the favicon reference**

`builder.html` references `/icons/favicon.ico` — this app doesn't have an
`/icons/<path>` route (Task 6's `app.py` doesn't define one) or the icon
file itself. Either:
(a) copy `dnd-app-bg-local/skills/dnd/display/icons/favicon.ico` to a new
`static/favicon.ico` in this repo, add `app.route("/icons/<path:filename>")`
to `app.py` serving from that `static/` dir (mirror the source repo's own
route for this), or
(b) simplify the `<link rel="icon" href="/icons/favicon.ico">` line to
point at Flask's default `/favicon.ico` static handling.
Pick (a) — it's a direct, minimal port matching what already works in the
source repo — and implement it now.

```bash
mkdir -p /Users/yoanpetrov/dnd-character-creator/static
cp /Users/yoanpetrov/dnd-app-bg-local/skills/dnd/display/icons/favicon.ico \
   /Users/yoanpetrov/dnd-character-creator/static/favicon.ico
```

Add to `app.py` (near the top-level routes):

```python
from flask import send_from_directory
import os

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.route("/icons/<path:filename>")
def icons(filename):
    return send_from_directory(_STATIC_DIR, filename)
```

- [ ] **Step 5: Run the full test suite**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/ -v`
Expected: all PASS (this task doesn't add new automated tests — `builder.html`
is markup/JS the existing `test_app.py::test_index_serves_builder_page`
already exercises at the route level; a full click-through check happens
in Task 8's manual verification step).

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add templates/builder.html static/favicon.ico app.py
git commit -m "feat: port and trim the character builder UI

Removed the three links back to the play app's /menu and / (they don't
exist in this repo); everything else — the 7-step stepper and its JS
calling /api/chargen/* — is unchanged, since it already only talks to
endpoints this app now provides itself.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: End-to-end manual verification + README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 1-7 (this task adds no new importable code).

- [ ] **Step 1: Start the app**

```bash
cd /Users/yoanpetrov/dnd-character-creator
.venv/bin/python3 app.py
```

- [ ] **Step 2: Open it in a browser and build one character through the real UI**

Navigate to `http://127.0.0.1:5300/`, walk through all 7 steps of the
builder for any race/class/background combination, and submit.

- [ ] **Step 3: Verify the three export files on disk**

```bash
ls -la ~/.claude/dnd/characters/*/
```

Expected: a directory named after the character with `current.yaml`,
`character.md`, and `character.pdf`, all non-empty.

- [ ] **Step 4: Open the PDF and visually confirm it looks like a real character sheet**

Open `character.pdf` in a PDF viewer (or `open ~/.claude/dnd/characters/<Name>/character.pdf`
on macOS). Confirm: name/race/class/background/alignment show correctly,
all six ability scores and modifiers are filled (including the Dex and
Charisma modifier boxes — the two fields with the naming quirks noted in
Task 5), AC/HP/Speed/Initiative/Passive Perception are filled, the skills
and saving throws grid shows real bonuses (not blank), and equipment/
features/backstory text appears in their boxes.

- [ ] **Step 5: Stop the app**

Ctrl+C in the terminal running `app.py`.

- [ ] **Step 6: Write `README.md`**

```markdown
# D&D Character Creator

A standalone character-creation app for D&D 5e (SRD content), split out of
the `dnd-app-bg` play app's builder. Produces three exports per character:

- `current.yaml` — the canonical sheet (same shape/location convention the
  play app's character library already uses, at
  `~/.claude/dnd/characters/<Name>/current.yaml` — override the root with
  `DND_CAMPAIGN_ROOT`)
- `character.md` — a human-readable Markdown sheet
- `character.pdf` — the official Wizards of the Coast fillable sheet, filled in

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt

## Run

    .venv/bin/python3 app.py

Then open http://127.0.0.1:5300/

## Test

    .venv/bin/pytest tests/ -v

## Architecture

See `docs/superpowers/specs/2026-09-13-character-creator-app-design.md` for
the full design rationale. In short: `chargen/` (ported verbatim from
`dnd-app-bg-local`) is the rules/content engine and has zero dependencies
outside the standard library; everything else in this repo (`storage.py`,
`sheet_derive.py`, `markdown_render.py`, `pdf_fill.py`, `app.py`) is new,
and none of it imports from `dnd-app-bg-local`'s play engine.

Not yet done: linking this app's output back into the play app as a
campaign-recruitable character. The storage path is chosen so that step
needs no data migration when it happens.
```

- [ ] **Step 7: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add README.md
git commit -m "docs: add README

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
