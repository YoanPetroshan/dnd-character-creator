# Builder v2 Phase 2f — Markdown Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Markdown half of the architecture spec's §10 Phase 2 scope item "Markdown + PDF export." This plan covers Markdown only — see "Scope note: PDF export" below for why.

**Scope note: PDF export.** v1 (`pdf_fill.py`, repo root) already fills the official WotC fillable sheet PDF at `assets/character-sheet-template.pdf` via pypdf's AcroForm API, with every field name already reverse-engineered and documented. That asset and field-mapping knowledge is real and reusable — but this project's architecture spec (§9) states plainly that the *only* v1 artifact carried into v2 is the bundled SRD JSON (`chargen/data/srd/*.json`); every other v1 module is explicitly out of bounds, and no prior phase in this project has reused any other v1 file or asset. Reusing the PDF template (a licensed Wizards of the Coast asset, not open SRD content) is a real scope decision that widens that stated boundary, not an implementation detail — it needs a human call, not an autonomous one. This plan implements Markdown export only, which needs no v1 reuse of any kind (a fresh renderer against v2's own `resolve()` output), and leaves PDF export as an open question for later.

**Architecture:** A new pure-function module `server/markdown_export.py` (`to_markdown(resolution: dict) -> str`), mirroring the existing `export.py`'s `to_yaml()` in spirit (same input contract, same "pure rendering, no I/O" discipline) but producing a human-readable Markdown document instead of a machine-readable YAML one. A new `POST /api/export/markdown` route in `server/app.py`, sharing the exact pending-choice export gate `api_export_yaml` already has (extracted into a small shared helper rather than copy-pasted). `ExportPage.tsx` gains a second download button, refactoring the existing single-format download logic to handle both.

**Tech Stack:** Same as every prior phase — Python/Flask backend, React/TypeScript frontend, no new dependencies (Markdown is plain text, no library needed to produce it).

## Global Constraints

- **No v1 code or v1-specific assets are reused, imported, or referenced anywhere in this plan.** This is NOT a port of `markdown_render.py` — that module is scoped to `chargen.build()`'s different sheet shape (it has fields v2 doesn't compute yet: HP current/temp tracking, currency, a `features_traits` list with descriptions, per-spell-level slot counts, a per-spell `prepared` boolean) and skipped fields v2 does have. `server/markdown_export.py` is written fresh, scoped to exactly what `resolve()` actually produces today — no speculative fields, no attempt to match v1's template section-for-section.
- **Every value rendered comes from `resolution["sheet"]`/`resolution["derived"]` as `resolve()` already produces them** — no new engine computation, no new `sheet`/`derived` keys. The one small backend addition this plan needs is a skill-id-to-display-name lookup table (`SKILL_NAMES` in `server/catalog/reference_data.py`, mirroring the file's existing `LANGUAGES` table — open 5e SRD skill names are safe to hardcode the same way), since `derived.skills` is keyed by opaque ids like `"skill-sleight-of-hand"` and no display-name table exists anywhere in the backend yet (the frontend never needed one — choice option labels come embedded in the SRD JSON's own `proficiency_choices` entries, which doesn't help a Markdown renderer working from `derived.skills` directly).
- **The pending-choice export gate is shared, not duplicated.** `api_export_yaml`'s existing gate logic (problems + pending non-equipment choices) is extracted into a small module-level helper in `server/app.py` and both `/api/export/yaml` and the new `/api/export/markdown` call it — a character that can't export as YAML can't export as Markdown either, and there is exactly one place that decides "is this character export-ready."
- **No visual/design work on the frontend** — the new "Изтегли Markdown" button matches the existing "Изтегли YAML" button's styling exactly (no new CSS beyond what's already there for the export page).

---

### Task 1: `to_markdown()`, skill names, shared export gate, `/api/export/markdown`

**Files:**
- Modify: `server/catalog/reference_data.py`
- Create: `server/markdown_export.py`
- Modify: `server/app.py`
- Test: `server/tests/test_markdown_export.py` (new), `server/tests/test_app.py`

**Interfaces:**
- Consumes: `resolve()`'s output shape (unchanged) — see the Global Constraints for the exact `sheet`/`derived` keys this reads.
- Produces: `to_markdown(resolution: dict) -> str`, `POST /api/export/markdown` (same request/response contract as `/api/export/yaml`: `POST` a draft JSON body, `200` with `text/markdown` body on success, `400` with `{"problems": [...]}` on a blocked export).

- [ ] **Step 1: Add `SKILL_NAMES` to `server/catalog/reference_data.py`**

Add near the existing `SKILL_ABILITY` table (same file, matching its documentation style):

```python
# SRD skill `index` -> its standard 5e display name. Open SRD content,
# same "safe to hardcode" reasoning as LANGUAGES above — no bundled SRD
# file carries these as their own list; they only exist embedded inside
# each class's proficiency_choices option labels, which doesn't help code
# that starts from a skill `index` (e.g. derived.skills' keys) rather than
# from a class's own choice envelope.
SKILL_NAMES: dict[str, str] = {
    "skill-acrobatics": "Acrobatics",
    "skill-animal-handling": "Animal Handling",
    "skill-arcana": "Arcana",
    "skill-athletics": "Athletics",
    "skill-deception": "Deception",
    "skill-history": "History",
    "skill-insight": "Insight",
    "skill-intimidation": "Intimidation",
    "skill-investigation": "Investigation",
    "skill-medicine": "Medicine",
    "skill-nature": "Nature",
    "skill-perception": "Perception",
    "skill-performance": "Performance",
    "skill-persuasion": "Persuasion",
    "skill-religion": "Religion",
    "skill-sleight-of-hand": "Sleight of Hand",
    "skill-stealth": "Stealth",
    "skill-survival": "Survival",
}
```

- [ ] **Step 2: Write failing tests for `to_markdown()`**

Create `server/tests/test_markdown_export.py`, matching `server/tests/test_export.py`'s existing style (a `_sample_resolution()` builder — copy and adapt it, since `to_markdown` takes the exact same `resolution` shape `to_yaml` does):

```python
from markdown_export import to_markdown


def _sample_resolution(**overrides):
    resolution = {
        "sheet": {
            "name": "Тестов Герой",
            "level": 1,
            "class": {"id": "fighter", "name": "Fighter"},
            "background": {"id": "acolyte", "name": "Acolyte"},
            "species": {"id": "human", "name": "Human", "subspecies": None},
            "abilities": {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9},
            "proficiencies": {"skills": ["skill-athletics"], "savingThrows": ["STR", "CON"], "languages": ["common"]},
            "equipment": {"granted": [], "chosen": [], "added": []},
            "spells": None,
            "details": None,
        },
        "derived": {
            "abilityModifiers": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
            "proficiencyBonus": 2,
            "hitPointMax": 12,
            "hitDice": "1d10",
            "armorClass": 12,
            "speed": 30,
            "savingThrows": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
            "skills": {
                "skill-acrobatics": 2, "skill-animal-handling": 1, "skill-arcana": 0, "skill-athletics": 5,
                "skill-deception": -1, "skill-history": 0, "skill-insight": 1, "skill-intimidation": -1,
                "skill-investigation": 0, "skill-medicine": 1, "skill-nature": 0, "skill-perception": 1,
                "skill-performance": -1, "skill-persuasion": -1, "skill-religion": 0,
                "skill-sleight-of-hand": 2, "skill-stealth": 2, "skill-survival": 1,
            },
            "passivePerception": 11,
            "spellSaveDC": None,
            "spellAttackBonus": None,
        },
        "choices": [], "problems": [], "warnings": [], "pruned": [],
    }
    for key, value in overrides.items():
        if key in resolution["sheet"]:
            resolution["sheet"][key] = value
        elif key in resolution["derived"]:
            resolution["derived"][key] = value
    return resolution


def test_includes_name_and_header_line():
    text = to_markdown(_sample_resolution())
    assert text.startswith("# Тестов Герой")
    assert "Ниво 1 Fighter" in text
    assert "Acolyte" in text
    assert "Human" in text


def test_includes_combat_stats():
    text = to_markdown(_sample_resolution())
    assert "12" in text  # armorClass and hitPointMax are both 12 in the fixture — presence check
    assert "1d10" in text
    assert "30" in text  # speed
    assert "+2" in text  # DEX modifier used as initiative


def test_includes_ability_scores():
    text = to_markdown(_sample_resolution())
    assert "STR" in text and "17" in text and "+3" in text


def test_proficient_save_is_marked_differently_from_non_proficient():
    text = to_markdown(_sample_resolution())
    # STR and CON are proficient saves in the fixture; DEX is not.
    # Whatever exact marker the implementation uses, a proficient and a
    # non-proficient save line must render visibly differently.
    lines = [l for l in text.splitlines() if "**STR**" in l or "**DEX**" in l]
    str_line = next(l for l in lines if "**STR**" in l)
    dex_line = next(l for l in lines if "**DEX**" in l)
    assert str_line != dex_line.replace("DEX", "STR")  # not just the ability letter differs


def test_skill_names_are_human_readable_not_raw_ids():
    text = to_markdown(_sample_resolution())
    assert "Sleight of Hand" in text
    assert "skill-sleight-of-hand" not in text
    assert "Athletics" in text


def test_includes_languages_or_a_placeholder():
    text = to_markdown(_sample_resolution())
    assert "common" in text.lower() or "Common" in text


def test_omits_spells_section_for_a_non_caster():
    text = to_markdown(_sample_resolution())
    assert "Заклинания" not in text


def test_includes_spells_section_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["class"] = {"id": "wizard", "name": "Wizard"}
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }
    resolution["derived"]["spellSaveDC"] = 13
    resolution["derived"]["spellAttackBonus"] = 5
    text = to_markdown(resolution)
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "13" in text


def test_omits_equipment_subsections_that_are_empty():
    text = to_markdown(_sample_resolution())  # all three equipment lists are empty in the fixture
    assert "Получена екипировка" not in text
    assert "Избрана екипировка" not in text
    assert "Инвентар" not in text


def test_includes_populated_equipment_subsections():
    resolution = _sample_resolution()
    resolution["sheet"]["equipment"] = {
        "granted": [{"itemId": "chain-mail", "name": "Chain Mail", "qty": 1}],
        "chosen": [{"itemId": "handaxe", "name": "Handaxe", "qty": 1}],
        "added": [{"itemId": "torch", "name": "Torch", "qty": 2, "equipped": False}],
    }
    text = to_markdown(resolution)
    assert "Chain Mail" in text
    assert "Handaxe" in text
    assert "Torch" in text
    assert "x2" in text


def test_omits_details_sections_when_none():
    text = to_markdown(_sample_resolution())
    assert "Мирогледие" not in text
    assert "Предистория" not in text


def test_includes_only_submitted_details_fields():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"alignment": "Chaotic Good", "backstory": "Роден в планините."}
    text = to_markdown(resolution)
    assert "Chaotic Good" in text
    assert "Роден в планините." in text
    assert "Вяра" not in text  # faith wasn't submitted, its label shouldn't appear
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_markdown_export.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'markdown_export'`).

- [ ] **Step 4: Implement `server/markdown_export.py`**

```python
"""Turns a Resolution (see engine/resolve.py) into a human-readable
Markdown character sheet. Not a port of the v1 markdown_render.py at the
repo root — that module is scoped to chargen.build()'s different sheet
shape (it has fields v2 doesn't compute yet, like HP tracking and
currency, and skips fields v2 does have). This module reads only
resolution["sheet"]/["derived"] exactly as engine/resolve.py's resolve()
already produces them — no new engine computation happens here.
"""
from __future__ import annotations

from catalog.reference_data import SKILL_NAMES

_ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

_DETAIL_SECTIONS = [
    ("Данни за героя", [("alignment", "Мирогледие"), ("faith", "Вяра/Божество"), ("lifestyle", "Начин на живот")]),
    ("Физически характеристики", [
        ("age", "Възраст"), ("height", "Височина"), ("weight", "Тегло"),
        ("eyes", "Очи"), ("skin", "Кожа"), ("hair", "Коса"),
    ]),
    ("Личност", [
        ("personalityTraits", "Черти на характера"), ("ideals", "Идеали"),
        ("bonds", "Връзки"), ("flaws", "Слабости"),
    ]),
    ("Бележки", [
        ("backstory", "Предистория"), ("organizations", "Организации"),
        ("allies", "Съюзници"), ("enemies", "Врагове"), ("notes", "Допълнителни бележки"),
    ]),
]

_EQUIPMENT_SECTIONS = [("granted", "Получена екипировка"), ("chosen", "Избрана екипировка"), ("added", "Инвентар")]


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _species_label(species: dict | None) -> str:
    if not species:
        return "—"
    label = species["name"]
    if species.get("subspecies"):
        label += f" ({species['subspecies']['name']})"
    return label


def _ability_line(sheet: dict, derived: dict) -> str:
    scores = sheet["abilities"]
    mods = derived["abilityModifiers"]
    return "  ".join(f"**{ab}** {scores[ab]} ({_fmt_mod(mods[ab])})" for ab in _ABILITIES)


def _saves_line(derived: dict, proficient: list[str]) -> str:
    saves = derived["savingThrows"]
    parts = []
    for ab in _ABILITIES:
        marker = "●" if ab in proficient else "○"
        parts.append(f"{marker} **{ab}** {_fmt_mod(saves[ab])}")
    return "  ".join(parts)


def _skill_lines(derived: dict, proficient: list[str]) -> list[str]:
    skills = derived["skills"]
    ordered = sorted(skills, key=lambda sid: SKILL_NAMES.get(sid, sid))
    lines = []
    for skill_id in ordered:
        name = SKILL_NAMES.get(skill_id, skill_id)
        marker = "●" if skill_id in proficient else "○"
        lines.append(f"- {marker} {name}: {_fmt_mod(skills[skill_id])}")
    return lines


def to_markdown(resolution: dict) -> str:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    lines: list[str] = []

    cls = sheet["class"]
    bg = sheet["background"]

    lines.append(f"# {sheet['name'] or 'Безименен герой'}")
    lines.append("")
    lines.append(
        f"**Ниво {sheet['level']} {cls['name'] if cls else '—'}** | "
        f"**Произход:** {bg['name'] if bg else '—'} | "
        f"**Раса:** {_species_label(sheet['species'])}"
    )
    lines.append("")

    lines.append("## Бойни показатели")
    lines.append(f"- **Клас броня (AC):** {derived['armorClass']}")
    lines.append(f"- **Точки живот:** {derived['hitPointMax']} ({derived['hitDice']})")
    lines.append(f"- **Скорост:** {derived['speed']} фута" if derived["speed"] is not None else "- **Скорост:** —")
    lines.append(f"- **Инициатива:** {_fmt_mod(derived['abilityModifiers']['DEX'])}")
    lines.append(f"- **Пасивно възприятие:** {derived['passivePerception']}")
    lines.append(f"- **Бонус за умение:** {_fmt_mod(derived['proficiencyBonus'])}")
    lines.append("")

    lines.append("## Характеристики")
    lines.append(_ability_line(sheet, derived))
    lines.append("")

    lines.append("## Спасителни хвърляния")
    lines.append(_saves_line(derived, sheet["proficiencies"]["savingThrows"]))
    lines.append("")

    lines.append("## Умения")
    lines.extend(_skill_lines(derived, sheet["proficiencies"]["skills"]))
    lines.append("")

    languages = sheet["proficiencies"]["languages"]
    lines.append("## Езици")
    lines.append(", ".join(languages) if languages else "—")
    lines.append("")

    equipment = sheet["equipment"]
    lines.append("## Екипировка")
    any_equipment = False
    for key, label in _EQUIPMENT_SECTIONS:
        entries = equipment[key]
        if not entries:
            continue
        any_equipment = True
        lines.append(f"### {label}")
        for e in entries:
            qty_tag = f" x{e['qty']}" if e.get("qty", 1) != 1 else ""
            equipped_tag = " (екипиран)" if e.get("equipped") else ""
            lines.append(f"- {e['name']}{qty_tag}{equipped_tag}")
        lines.append("")
    if not any_equipment:
        lines.append("—")
        lines.append("")

    spells = sheet["spells"]
    if spells is not None:
        lines.append("## Заклинания")
        if derived["spellSaveDC"] is not None:
            lines.append(
                f"- **Спасяване за заклинание (DC):** {derived['spellSaveDC']}  |  "
                f"**Бонус за атака:** {_fmt_mod(derived['spellAttackBonus'])}"
            )
        if spells["cantrips"]:
            lines.append("### Трикове")
            for s in spells["cantrips"]:
                lines.append(f"- {s['name']}")
        if spells["known"]:
            lines.append("### Известни/Подготвени заклинания")
            for s in spells["known"]:
                lines.append(f"- {s['name']} (ниво {s['level']})")
        lines.append("")

    details = sheet["details"]
    if details:
        for section_label, fields in _DETAIL_SECTIONS:
            present = [(label, details[key]) for key, label in fields if key in details]
            if not present:
                continue
            lines.append(f"## {section_label}")
            for label, value in present:
                lines.append(f"- **{label}:** {value}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_markdown_export.py -v`
Expected: PASS, all cases.

- [ ] **Step 6: Extract the shared export-gate helper and add `/api/export/markdown` in `server/app.py`**

Find `api_export_yaml`'s current body — it builds `pending_problems` inline. Extract that into a module-level helper placed just above `api_export_yaml`:

```python
def _pending_export_problems(resolution: dict) -> list[dict]:
    return [
        {"id": f"unresolved-choice-{c['id']}", "message": f"'{c['label']}' isn't fully chosen yet."}
        for c in resolution["choices"]
        if c["status"] == "pending" and c["source"]["kind"] != "equipment"
        # Equipment choices are excluded from this gate — see the git
        # history around Phase 2a/2b for why (a frontend now resolves
        # them; the exclusion predates both export routes using this
        # shared helper and applies identically to each).
    ]
```

Update `api_export_yaml` to call it:

```python
@app.route("/api/export/yaml", methods=["POST"])
def api_export_yaml():
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    return Response(to_yaml(resolution), mimetype="application/x-yaml")
```

Add the new route right after it, and add the import at the top of the file (alongside `from export import to_yaml`):

```python
from markdown_export import to_markdown
```

```python
@app.route("/api/export/markdown", methods=["POST"])
def api_export_markdown():
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    return Response(to_markdown(resolution), mimetype="text/markdown")
```

- [ ] **Step 7: Write and run `server/tests/test_app.py` cases**

Open the file first and find the existing `/api/export/yaml` tests — match their exact style (fixture/client setup). Add equivalent cases for `/api/export/markdown`:
- A fully-resolved character POSTed to `/api/export/markdown` returns `200` with `Content-Type` starting `text/markdown` and a body containing the character's name.
- A character with a pending (unresolved) non-equipment choice returns `400` with the same `{"problems": [...]}` shape `/api/export/yaml` already returns for the identical draft — confirming both routes share the same gate, not two independently-drifting copies of it.

Run: `cd server && .venv/bin/python -m pytest tests/test_app.py -v -k export`
Expected: PASS.

Then run the full backend suite: `cd server && .venv/bin/python -m pytest -v` — expect all 140 existing plus your new cases, all green.

- [ ] **Step 8: Empirically verify against a real multi-section character**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from markdown_export import to_markdown
catalog = load()
draft = {
    'name': 'Ешелон Дъбосърце',
    'classes': [{'classId': 'cleric', 'level': 1, 'choices': {
        'class:cleric:1:spells-cantrips': [],
        'class:cleric:1:spells-known': [],
    }}],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'dwarf', 'choices': {}},
    'abilities': {'base': {'STR': 14, 'DEX': 10, 'CON': 15, 'INT': 10, 'WIS': 16, 'CHA': 12}},
    'details': {'alignment': 'Lawful Good', 'backstory': 'Порасна в храма на Морадин.'},
}
result = resolve(draft, catalog)
print(to_markdown(result))
"
```

(The two spell choice ids are left empty on purpose — this just needs a plausible level-1 Cleric with some real cantrip/spell choice ids visible in the output; if the printed markdown's Cantrips/Prepared Spells subsections are simply absent because nothing was selected, that's correct per this module's own "omit empty subsections" rule — the point of this check is to eyeball a full multi-section document rendering cleanly with real names, not to exercise every possible selection.) Confirm the output reads as a coherent character sheet: header line, combat stats, six abilities, six saves with a legible proficient/non-proficient distinction, all 18 skills with human-readable names (not `skill-` ids), a Spellcasting section (Cleric has real spellcasting at level 1), and the submitted alignment/backstory under the right detail sections. If anything looks garbled, wrong, or a section is unexpectedly empty/present, stop and investigate before committing.

- [ ] **Step 9: Commit**

```bash
git add server/catalog/reference_data.py server/markdown_export.py server/app.py server/tests/test_markdown_export.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: add Markdown character sheet export (GET /api/export/markdown)

New server/markdown_export.py renders resolve()'s output as a
human-readable Markdown document — written fresh against v2's own sheet
shape, not a port of the v1 markdown_render.py at the repo root (which
targets a different, richer sheet shape v2 doesn't fully compute yet).
Adds a SKILL_NAMES lookup table to reference_data.py, mirroring the
existing LANGUAGES table, since derived.skills is keyed by opaque ids
with no display-name table anywhere in the backend until now.

The pending-choice export gate (problems + unresolved non-equipment
choices) is now a single shared helper used by both /api/export/yaml and
the new /api/export/markdown, so the two formats can never drift on what
counts as export-ready.

PDF export is deliberately out of scope for this phase — see the plan's
Global Constraints for why (it would require reusing a v1 asset outside
this project's stated "only chargen/data/srd/*.json is reused" boundary,
a scope decision left for later).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Frontend Markdown download + end-to-end verification

**Files:**
- Modify: `frontend/src/pages/ExportPage.tsx`

**Interfaces:**
- Consumes: `POST /api/export/markdown` (Task 1).

- [ ] **Step 1: Refactor `handleExport` to a shared download helper, add the Markdown button**

Read the current `frontend/src/pages/ExportPage.tsx` first — it has one `handleExport` function hardcoded to `/api/export/yaml`. Generalize it to take the endpoint, filename extension, and MIME type as parameters, then call it from two button handlers:

```tsx
import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<"yaml" | "markdown" | null>(null);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  const pendingChoices = resolution.choices.filter((c) => c.status === "pending");
  const canExport = resolution.problems.length === 0 && pendingChoices.length === 0;

  async function handleExport(format: "yaml" | "markdown") {
    const config =
      format === "yaml"
        ? { endpoint: "/api/export/yaml", extension: "yaml", mimeType: "application/x-yaml" }
        : { endpoint: "/api/export/markdown", extension: "md", mimeType: "text/markdown" };
    setExportingFormat(format);
    setExportError(null);
    try {
      const resp = await fetch(config.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!resp.ok) {
        const body = (await resp.json()) as { problems?: { message: string }[] };
        throw new Error(body.problems?.map((p) => p.message).join("; ") ?? `export failed: ${resp.status}`);
      }
      const text = await resp.text();
      const blob = new Blob([text], { type: config.mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${draft.name || "character"}.${config.extension}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <div className="page">
      <h1>Export {loading && "…"}</h1>
      {resolution.problems.length > 0 && (
        <div>
          <h2>Problems</h2>
          <ul>
            {resolution.problems.map((p) => (
              <li key={p.id}>{p.message}</li>
            ))}
          </ul>
        </div>
      )}
      {pendingChoices.length > 0 && (
        <div>
          <h2>Unresolved choices</h2>
          <ul>
            {pendingChoices.map((c) => (
              <li key={c.id}>{c.label}</li>
            ))}
          </ul>
        </div>
      )}
      {canExport && <p>Всичко е готово за експорт.</p>}
      {exportError && <p style={{ color: "red" }}>{exportError}</p>}
      <button type="button" disabled={!canExport || exportingFormat !== null} onClick={() => handleExport("yaml")}>
        {exportingFormat === "yaml" ? "Изтегляне…" : "Изтегли YAML"}
      </button>
      <button type="button" disabled={!canExport || exportingFormat !== null} onClick={() => handleExport("markdown")}>
        {exportingFormat === "markdown" ? "Изтегляне…" : "Изтегли Markdown"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: no errors.

- [ ] **Step 3: Manual end-to-end verification**

```bash
cd server && .venv/bin/python app.py &
sleep 1
cd ../frontend && npm run dev &
sleep 2
```

Build a complete level-1 Cleric or Wizard character through the real UI (name, class with cantrips/spells resolved, background with languages resolved, species, abilities, equipment). Confirm both "Изтегли YAML" and "Изтегли Markdown" buttons are enabled once every choice is resolved (and both disabled while any choice is still pending — verify this by checking a page before resolving everything). Click "Изтегли Markdown" — confirm a `.md` file downloads, open it, and confirm it reads as a coherent character sheet with the correct name, class, ability scores, skills with real names (not `skill-` ids), spellcasting section (if applicable), and any details you filled in. Click "Изтегли YAML" too — confirm it still works exactly as before this phase (this task didn't change its behavior, only its code path, so this is a regression check).

```bash
kill %1 %2
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ExportPage.tsx
git commit -m "$(cat <<'EOF'
feat: add Markdown download button to the Export step

Generalizes the existing YAML-only download handler to take a format
parameter (endpoint/extension/MIME type), used by both the existing
"Изтегли YAML" button (behavior unchanged) and a new "Изтегли Markdown"
button backed by Phase 2f's GET /api/export/markdown.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- The PDF-export deferral (see this plan's opening "Scope note") is not an oversight — do not add PDF export to this plan's scope, and do not reach for v1's `pdf_fill.py`/`assets/character-sheet-template.pdf` even as "just a reference" without checking with the human first. If a reviewer or implementer is tempted to "just knock out PDF too while we're here," that temptation is exactly the boundary this note exists to catch.
- `to_markdown()`'s field-selection logic (which `sheet`/`derived` keys it reads, which sections it omits when empty) should be re-checked against `resolve()`'s actual current shape at implementation time, not assumed frozen from this plan's text — `resolve()` has gained fields in nearly every phase of this project so far (equipment in 2a, spells in 2c, details in 2e), and a future phase could add more before this one is merged. If `resolve()`'s shape has changed since this plan was written, treat the plan's code as a template to adapt, not a literal transcript.
