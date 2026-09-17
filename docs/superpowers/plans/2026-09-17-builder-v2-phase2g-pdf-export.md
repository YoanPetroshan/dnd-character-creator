# Builder v2 Phase 2g — PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the PDF half of the architecture spec's §10 Phase 2 scope item "Markdown + PDF export," closing out Phase 2's scope entirely. Per the human's explicit direction, this is a **fresh PDF rendering with a new library** — not a fill of v1's official WotC template (`assets/character-sheet-template.pdf` + `pdf_fill.py`), which stays untouched and unreferenced. This was one of three options presented after Phase 2f's final review (reuse the v1 template asset / fresh PDF via a new dependency / print-styled HTML relying on browser print-to-PDF); the human chose fresh PDF rendering.

**Architecture:** A new pure-ish module `server/pdf_export.py` (`to_pdf(resolution: dict) -> bytes`) mirrors `markdown_export.py`'s exact section structure and content selection (same fields, same order: header, combat stats, abilities, saves, skills, languages, equipment, spells, details) but renders via `fpdf2` instead of building a Markdown string — the two renderers stay in lockstep by sharing the same field-selection logic conceptually, even though PDF's page-layout API means the code can't be a literal shared function the way, say, `_LANGUAGE_NAMES` is a shared lookup. Cyrillic text (this app's own example characters are Bulgarian) needs a Unicode TrueType font — PDF's built-in core fonts (Helvetica/Times/Courier) have no Cyrillic glyphs — so this plan bundles the DejaVu Sans family (regular + bold) as a font asset, empirically confirmed below to have full Cyrillic coverage and a license that permits redistribution.

This phase also extracts the by-now-three-times-duplicated export route body (`draft = ...; resolution = resolve(...); check problems; return Response(...)`) into a single parameterized route with a `{format: (renderer, mimetype)}` lookup table — flagged as the right move by Phase 2f's own final review at exactly this trigger point (a third format). The frontend's export handler is refactored the same way, and — because a PDF response is binary — its download path switches from `resp.text()` (which would corrupt binary content) to `resp.blob()` (which already carries the correct `Content-Type` from the server, so the client no longer needs to separately track a MIME type at all).

**Tech Stack:** New backend dependency: `fpdf2` (pure Python, LGPL-3.0-only — a normal, unmodified-library dependency use, not a redistribution-of-modified-source situation, so this is a non-issue for a self-hosted personal tool; no system-level dependencies like Cairo/Pango, confirmed by installing and testing it directly). New bundled asset: DejaVu Sans + DejaVu Sans Bold TTF files (Bitstream Vera License — explicitly permits reproduction and redistribution of the unmodified fonts, confirmed by reading the license text directly). New test-time dependency: `pypdf` (already a dependency of this repo's v1 code at the root `requirements.txt`; added to `server/requirements.txt` too, used only to extract real text back out of generated PDFs for content assertions in tests — the same "assert real content, not just no-crash" discipline established for `markdown_export.py`'s tests).

## Global Constraints

- **No reuse of v1's PDF machinery.** `pdf_export.py` must not import from, reference, or structurally copy `pdf_fill.py` (repo root) or open `assets/character-sheet-template.pdf`. This is a from-scratch document, not a form fill.
- **Every rendered value comes from `resolution["sheet"]`/`resolution["derived"]` exactly as `resolve()` produces them today** — no new engine computation. Re-verify the exact key shapes against the current `server/engine/resolve.py` at implementation time (its own docstring notes the shape has grown in nearly every phase of this project).
- **Content parity with `markdown_export.py`, not a copy-paste of its code.** Same sections, same order, same field selection (including the same 18-detail-field grouping, the same skill/language display-name lookups, the same "omit empty subsections" behavior for equipment/spells/details). If `markdown_export.py`'s content logic changes in some future phase, this module's content logic should be revisited too — they are two renderings of one contract, not independent designs.
- **The bundled font files are a licensed asset, checked into the repo, with their license text alongside them** — `server/assets/fonts/DejaVuSans.ttf`, `server/assets/fonts/DejaVuSans-Bold.ttf`, `server/assets/fonts/LICENSE` (the exact Bitstream Vera / DejaVu license text, verified permissive and redistribution-safe before this plan was written — see this plan's Task 1 for the empirical verification already performed).
- **The export-route consolidation must preserve the two existing endpoints' exact behavior** (`POST /api/export/yaml`, `POST /api/export/markdown` — same URLs, same request/response contract, same problem-shape on a blocked export) — this plan touches pre-existing, already-shipped, already-tested code, not purely additive code. Verify byte-for-byte behavioral equivalence before/after, the same discipline Phase 2f's Task 1 applied to the `_pending_export_problems` extraction.
- **No visual/design work beyond what a printable document minimally needs to be readable and navigable** (font-size hierarchy for headers vs. body, thin grey rules between sections, standard margins) — no colors beyond black text and light-grey rules, no branding, no illustration. This waits for the separate paper/parchment design pass, same as every prior phase.

---

### Task 1: Font asset, `to_pdf()`, consolidated export route

**Files:**
- Create: `server/assets/fonts/DejaVuSans.ttf`, `server/assets/fonts/DejaVuSans-Bold.ttf`, `server/assets/fonts/LICENSE`
- Modify: `server/requirements.txt`
- Create: `server/pdf_export.py`
- Modify: `server/app.py`
- Test: `server/tests/test_pdf_export.py` (new), `server/tests/test_app.py`

**Interfaces:**
- Consumes: `resolve()`'s output shape (see Global Constraints).
- Produces: `to_pdf(resolution: dict) -> bytes`. `POST /api/export/<fmt>` where `fmt` is one of `yaml`/`markdown`/`pdf` (replaces the previous two separate `/api/export/yaml`/`/api/export/markdown` route functions with one parameterized route — the URLs themselves are unchanged, only the Python implementation consolidates), returning `200` with the right `Content-Type` on success, `400` with `{"problems": [...]}` on a blocked export, `404` with `{"error": ...}` for an unrecognized format segment.

- [ ] **Step 0: Obtain and place the font assets**

This step's exact commands were already run once while writing this plan, to confirm the approach works before committing to it in writing — re-run them (or verify the files already exist at these paths from that earlier run) rather than skipping straight to Step 1 assuming they're already in place, since a fresh implementer's checkout won't have them yet:

```bash
brew install font-dejavu   # installs to ~/Library/Fonts/ on macOS; if this is not macOS or Homebrew isn't available, obtain DejaVu Sans Regular + Bold TTFs and their LICENSE file by any other means — they are widely mirrored (e.g. the dejavu-fonts project's own releases) as long as the LICENSE file travels with them
mkdir -p /Users/yoanpetrov/dnd-character-creator/server/assets/fonts
cp ~/Library/Fonts/DejaVuSans.ttf ~/Library/Fonts/DejaVuSans-Bold.ttf /Users/yoanpetrov/dnd-character-creator/server/assets/fonts/
cp /opt/homebrew/Caskroom/font-dejavu/*/dejavu-fonts-ttf-*/LICENSE /Users/yoanpetrov/dnd-character-creator/server/assets/fonts/LICENSE
```

Verify the license text you copied is the Bitstream Vera Fonts Copyright (starts "Copyright (c) 2003 by Bitstream, Inc." and explicitly grants "Permission ... to reproduce and distribute the Font Software ... including without limitation the rights to use, copy, merge, publish, distribute, and/or sell copies") — this was read in full when this plan was written and confirmed permissive; if what you copied looks different, stop and investigate before proceeding, don't assume it's equivalent.

Verify Cyrillic coverage empirically rather than trusting this plan's claim — this exact check was run when writing this plan and passed:

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pip install fonttools -q
.venv/bin/python -c "
from fontTools.ttLib import TTFont
f = TTFont('assets/fonts/DejaVuSans.ttf')
cmap = f.getBestCmap()
for cp in [0x0410, 0x0430, 0x044F, 0x042E, 0x0436]:
    assert cp in cmap, f'missing cyrillic codepoint {hex(cp)}'
print('all cyrillic codepoints present')
"
```

- [ ] **Step 1: Add `fpdf2` and `pypdf` to `server/requirements.txt`**

Open the file (currently `flask`, `flask-cors`, `pytest`, `pyyaml`, unpinned) and add two lines, matching the existing unpinned style:

```
fpdf2
pypdf
```

Install into the venv: `cd server && .venv/bin/pip install -r requirements.txt`

- [ ] **Step 2: Empirically confirm fpdf2's real API before writing tests or implementation**

This plan's code below was written against fpdf2 2.8.8's real API, verified directly (not from memory/training-data recall, which is frequently stale for fast-moving libraries) — re-confirm the key calls still behave as expected, since a future `pip install` could pull a newer major version with a changed API:

```bash
cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/python -c "
from fpdf import FPDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.add_font('DejaVu', '', 'assets/fonts/DejaVuSans.ttf')
pdf.add_font('DejaVu', 'B', 'assets/fonts/DejaVuSans-Bold.ttf')
pdf.set_font('DejaVu', 'B', 16)
pdf.cell(0, 10, 'Тестов Герой', new_x='LMARGIN', new_y='NEXT')
pdf.set_font('DejaVu', '', 11)
pdf.multi_cell(0, 6, 'Първи ред.\n\nВтори абзац.')
out = pdf.output()
print(type(out), len(out))
with open('/tmp/_phase2g_probe.pdf', 'wb') as f:
    f.write(out)
"
.venv/bin/python -c "
from pypdf import PdfReader
text = PdfReader('/tmp/_phase2g_probe.pdf').pages[0].extract_text()
assert 'Тестов Герой' in text
assert 'Първи ред.' in text and 'Втори абзац.' in text
print('round-trip OK:', repr(text))
"
rm -f /tmp/_phase2g_probe.pdf
```

If `pdf.output()`'s return type, `add_font`'s signature, or `multi_cell`'s newline handling has changed from what this plan assumes (a 3-positional-arg `add_font(family, style, path)`, `output()` returning `bytes`/`bytearray` directly with no `dest=`/manual `.encode()` step needed, `multi_cell` correctly wrapping embedded `\n\n` into separate paragraphs), adapt the implementation below to match reality — don't force reality to match this plan's assumed API.

- [ ] **Step 3: Write failing tests for `to_pdf()`**

Create `server/tests/test_pdf_export.py`. Copy the same `_sample_resolution()` builder `test_markdown_export.py` uses (read that file first, copy its fixture verbatim so the two renderers are tested against an identical input shape — this is deliberate duplication, not an oversight, since the two test files should be able to evolve independently if one renderer's tests need a case the other doesn't). Since PDF isn't plain text, tests extract text back out via `pypdf` rather than substring-matching raw bytes:

```python
import io

from pypdf import PdfReader

from pdf_export import to_pdf


def _sample_resolution():
    # Copy verbatim from test_markdown_export.py's _sample_resolution() —
    # see that file for the exact fixture. Do not diverge the two fixtures
    # unless a test in this file specifically needs different data.
    ...


def _extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_produces_valid_pdf_bytes():
    pdf_bytes = to_pdf(_sample_resolution())
    assert pdf_bytes[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_includes_name_and_header_line():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Тестов Герой" in text
    assert "Fighter" in text
    assert "Acolyte" in text


def test_includes_combat_stats_and_ability_scores():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "12" in text  # armorClass/hitPointMax
    assert "1d10" in text
    assert "STR" in text and "17" in text


def test_skill_and_language_names_are_human_readable():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Sleight of Hand" in text
    assert "skill-sleight-of-hand" not in text


def test_omits_spells_section_for_a_non_caster():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Заклинания" not in text


def test_includes_spells_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["class"] = {"id": "wizard", "name": "Wizard"}
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }
    resolution["derived"]["spellSaveDC"] = 13
    resolution["derived"]["spellAttackBonus"] = 5
    text = _extract_text(to_pdf(resolution))
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "13" in text


def test_includes_multiline_detail_values_intact():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"backstory": "Първи ред.\n\nВтори абзац с още текст."}
    text = _extract_text(to_pdf(resolution))
    assert "Първи ред." in text
    assert "Втори абзац с още текст." in text


def test_omits_details_sections_when_none():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Мирогледие" not in text


def test_handles_a_long_character_spanning_multiple_pages():
    # A character with every optional section populated should not crash
    # even if it overflows one page — fpdf2's auto page break should
    # handle it transparently.
    resolution = _sample_resolution()
    resolution["sheet"]["class"] = {"id": "wizard", "name": "Wizard"}
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": f"cantrip-{i}", "name": f"Cantrip Spell {i}", "level": 0} for i in range(10)],
        "known": [{"id": f"spell-{i}", "name": f"Known Spell {i}", "level": 1} for i in range(15)],
    }
    resolution["sheet"]["equipment"] = {
        "granted": [{"itemId": f"item-{i}", "name": f"Granted Item {i}", "qty": 1} for i in range(10)],
        "chosen": [{"itemId": f"item2-{i}", "name": f"Chosen Item {i}", "qty": 1} for i in range(10)],
        "added": [{"itemId": f"item3-{i}", "name": f"Added Item {i}", "qty": 1, "equipped": False} for i in range(10)],
    }
    resolution["sheet"]["details"] = {
        "alignment": "Chaotic Good", "faith": "—", "lifestyle": "—",
        "age": "30", "height": "180cm", "weight": "70kg", "eyes": "—", "skin": "—", "hair": "—",
        "personalityTraits": "Дълъг текст. " * 30,
        "ideals": "Още дълъг текст. " * 30,
        "bonds": "—", "flaws": "—",
        "backstory": "Много дълга предистория. " * 50,
        "organizations": "—", "allies": "—", "enemies": "—", "notes": "—",
    }
    pdf_bytes = to_pdf(resolution)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 2  # confirms auto page break actually engaged
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_pdf_export.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'pdf_export'`).

- [ ] **Step 5: Implement `server/pdf_export.py`**

This was drafted and partially hand-verified (the font/API portions) while writing this plan; re-verify the full assembled module against the live checkout before trusting it wholesale — in particular re-check every `sheet`/`derived` key against the CURRENT `server/engine/resolve.py`, per this plan's Global Constraints:

```python
"""Turns a Resolution (see engine/resolve.py) into a printable PDF
character sheet via fpdf2 — a fresh, self-drawn document, NOT a fill of
v1's official WotC template (repo-root pdf_fill.py / assets/
character-sheet-template.pdf) — see this plan's Scope note for why.
Mirrors markdown_export.py's exact section structure and field
selection; only the rendering target differs. The two should be kept in
sync by hand if resolve()'s output shape changes — they are two
renderings of one contract, not independently-designed documents.
"""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from catalog.reference_data import ABILITIES, LANGUAGES, SKILL_NAMES

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_LANGUAGE_NAMES = {lang["index"]: lang["name"] for lang in LANGUAGES}

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


class _SheetPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_page()

    def h1(self, text: str) -> None:
        self.set_font("DejaVu", "B", 18)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")

    def h2(self, text: str) -> None:
        self.ln(2)
        self.set_font("DejaVu", "B", 13)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def h3(self, text: str) -> None:
        self.set_font("DejaVu", "B", 11)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def body(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, text)

    def bullet(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, f"• {text}")


def to_pdf(resolution: dict) -> bytes:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    pdf = _SheetPDF()

    cls = sheet["class"]
    bg = sheet["background"]

    pdf.h1(sheet["name"] or "Безименен герой")
    pdf.body(
        f"Ниво {sheet['level']} {cls['name'] if cls else '—'}  |  "
        f"Произход: {bg['name'] if bg else '—'}  |  "
        f"Раса: {_species_label(sheet['species'])}"
    )

    pdf.h2("Бойни показатели")
    hit_dice = derived["hitDice"] if derived["hitDice"] is not None else "—"
    speed = f"{derived['speed']} фута" if derived["speed"] is not None else "—"
    pdf.body(
        f"Клас броня (AC): {derived['armorClass']}\n"
        f"Точки живот: {derived['hitPointMax']} ({hit_dice})\n"
        f"Скорост: {speed}\n"
        f"Инициатива: {_fmt_mod(derived['abilityModifiers']['DEX'])}\n"
        f"Пасивно възприятие: {derived['passivePerception']}\n"
        f"Бонус за умение: {_fmt_mod(derived['proficiencyBonus'])}"
    )

    pdf.h2("Характеристики")
    scores = sheet["abilities"]
    mods = derived["abilityModifiers"]
    pdf.body("   ".join(f"{ab} {scores[ab]} ({_fmt_mod(mods[ab])})" for ab in ABILITIES))

    pdf.h2("Спасителни хвърляния")
    saves = derived["savingThrows"]
    proficient_saves = sheet["proficiencies"]["savingThrows"]
    pdf.body("   ".join(
        f"{'●' if ab in proficient_saves else '○'} {ab} {_fmt_mod(saves[ab])}" for ab in ABILITIES
    ))

    pdf.h2("Умения")
    skills = derived["skills"]
    proficient_skills = sheet["proficiencies"]["skills"]
    for skill_id in sorted(skills, key=lambda sid: SKILL_NAMES.get(sid, sid)):
        marker = "●" if skill_id in proficient_skills else "○"
        pdf.bullet(f"{marker} {SKILL_NAMES.get(skill_id, skill_id)}: {_fmt_mod(skills[skill_id])}")

    pdf.h2("Езици")
    languages = sheet["proficiencies"]["languages"]
    pdf.body(", ".join(_LANGUAGE_NAMES.get(lang_id, lang_id) for lang_id in languages) if languages else "—")

    equipment = sheet["equipment"]
    pdf.h2("Екипировка")
    any_equipment = False
    for key, label in _EQUIPMENT_SECTIONS:
        entries = equipment[key]
        if not entries:
            continue
        any_equipment = True
        pdf.h3(label)
        for e in entries:
            qty_tag = f" x{e['qty']}" if e.get("qty", 1) != 1 else ""
            equipped_tag = " (екипиран)" if e.get("equipped") else ""
            pdf.bullet(f"{e['name']}{qty_tag}{equipped_tag}")
    if not any_equipment:
        pdf.body("—")

    spells = sheet["spells"]
    if spells is not None:
        pdf.h2("Заклинания")
        if derived["spellSaveDC"] is not None:
            pdf.body(
                f"Спасяване за заклинание (DC): {derived['spellSaveDC']}   "
                f"Бонус за атака: {_fmt_mod(derived['spellAttackBonus'])}"
            )
        if spells["cantrips"]:
            pdf.h3("Трикове")
            for s in spells["cantrips"]:
                pdf.bullet(s["name"])
        if spells["known"]:
            pdf.h3("Известни/Подготвени заклинания")
            for s in spells["known"]:
                pdf.bullet(f"{s['name']} (ниво {s['level']})")

    details = sheet["details"]
    if details:
        for section_label, fields in _DETAIL_SECTIONS:
            present = [(label, details[key]) for key, label in fields if key in details]
            if not present:
                continue
            pdf.h2(section_label)
            for label, value in present:
                pdf.h3(f"{label}:")
                pdf.body(value)
                pdf.ln(1)

    return bytes(pdf.output())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_pdf_export.py -v`
Expected: PASS, all cases including the multi-page one.

- [ ] **Step 7: Consolidate the export routes in `server/app.py`**

This is the one place this task touches pre-existing, already-shipped, already-tested code. Read the CURRENT `_pending_export_problems`, `api_export_yaml`, and `api_export_markdown` functions first (they may have shifted slightly since this plan was written) before changing anything.

Add the import at the top of the file (alongside the existing `from export import to_yaml` / `from markdown_export import to_markdown`):

```python
from pdf_export import to_pdf
```

Replace the two separate route functions (`api_export_yaml` and `api_export_markdown`) with:

```python
_EXPORT_RENDERERS = {
    "yaml": (to_yaml, "application/x-yaml"),
    "markdown": (to_markdown, "text/markdown"),
    "pdf": (to_pdf, "application/pdf"),
}


@app.route("/api/export/<fmt>", methods=["POST"])
def api_export(fmt: str):
    entry = _EXPORT_RENDERERS.get(fmt)
    if entry is None:
        return jsonify({"error": f"unknown export format '{fmt}'"}), 404
    renderer, mimetype = entry
    draft = request.get_json(silent=True) or {}
    resolution = resolve(draft, _catalog)
    all_problems = resolution["problems"] + _pending_export_problems(resolution)
    if all_problems:
        return jsonify({"problems": all_problems}), 400
    return Response(renderer(resolution), mimetype=mimetype)
```

`_pending_export_problems` itself is unchanged — keep it exactly as-is, including its existing comments (they document real history: the equipment carve-out, the deliberate non-carve-out for spell choices). The two existing URLs (`POST /api/export/yaml`, `POST /api/export/markdown`) still work identically — `fmt` is a URL path segment, so `/api/export/yaml` still routes here with `fmt == "yaml"`. `/api/export/pdf` is the new one. An unrecognized format (e.g. `/api/export/xml`) now correctly 404s instead of Flask's routing itself 404ing on an unmatched literal route — verify this is a reasonable, not-worse behavior change (it is: previously an unrecognized format wasn't even a valid URL at all, so this is strictly an improvement, not a regression, but confirm this reasoning holds by testing it, not just asserting it).

- [ ] **Step 8: Update `server/tests/test_app.py`**

Read the existing `test_export_yaml_endpoint_returns_valid_yaml`, `test_export_yaml_rejects_a_draft_with_problems`, `test_export_yaml_rejects_when_a_choice_is_still_pending`, `test_export_markdown_endpoint_returns_markdown`, `test_export_markdown_rejects_when_a_choice_is_still_pending`, and `test_export_yaml_does_not_block_on_pending_equipment_choices` tests first — confirm every one of them STILL PASSES UNCHANGED after Step 7's refactor (they should, since the URLs and behavior are byte-for-byte preserved — this is your verification that the consolidation didn't silently change anything). Then add new cases for the PDF format specifically:

```python
def test_export_pdf_endpoint_returns_a_pdf(client):
    resp = client.post("/api/export/pdf", json=_fully_resolved_draft())  # use whatever fixture-building helper the existing export tests already use
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/pdf")
    assert resp.data[:4] == b"%PDF"


def test_export_pdf_rejects_when_a_choice_is_still_pending(client):
    resp = client.post("/api/export/pdf", json=_draft_with_a_pending_choice())  # mirror test_export_markdown_rejects_when_a_choice_is_still_pending's exact fixture
    assert resp.status_code == 400
    body = resp.get_json()
    assert "problems" in body


def test_export_unknown_format_returns_404():
    resp = client.post("/api/export/xml", json={})
    assert resp.status_code == 404
```

(Adapt the fixture-building calls to match whatever helper functions the existing tests in this file actually use — read them first, don't invent new fixture-building code when the file already has an established convention.)

- [ ] **Step 9: Run the full backend suite**

Run: `cd server && .venv/bin/python -m pytest -v`
Expected: all 156 existing tests plus your new ones (roughly 9 from `test_pdf_export.py`, 3 from `test_app.py`), all green — confirming both the new PDF format AND that the route consolidation didn't break YAML/Markdown.

- [ ] **Step 10: Empirically verify against a real, rich character**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from pdf_export import to_pdf
catalog = load()
draft = {
    'name': 'Ешелон Дъбосърце',
    'classes': [{'classId': 'cleric', 'level': 1, 'choices': {}}],
    'background': {'id': 'acolyte', 'choices': {}},
    'species': {'id': 'dwarf', 'choices': {}},
    'abilities': {'base': {'STR': 14, 'DEX': 10, 'CON': 15, 'INT': 10, 'WIS': 16, 'CHA': 12}},
    'details': {'alignment': 'Lawful Good', 'backstory': 'Порасна в храма на Морадин.\n\nВтори абзац от предисторията.'},
}
result = resolve(draft, catalog)
pdf_bytes = to_pdf(result)
with open('/tmp/_phase2g_cleric.pdf', 'wb') as f:
    f.write(pdf_bytes)
print(len(pdf_bytes), 'bytes written')
"
```

Open `/tmp/_phase2g_cleric.pdf` with whatever tool you have available (a PDF viewer, or extract text with pypdf and read it) and confirm it reads as a coherent, well-laid-out single- or multi-page character sheet: readable header, combat stats, six abilities, six saves, 18 skills with real names, languages, granted equipment (Dwarves + Cleric + Acolyte should produce some), a Spellcasting section (Cleric casts at level 1), and the two-paragraph backstory rendered intact and readable, not garbled or truncated. Delete `/tmp/_phase2g_cleric.pdf` when done.

- [ ] **Step 11: Commit**

```bash
git add server/assets/fonts/DejaVuSans.ttf server/assets/fonts/DejaVuSans-Bold.ttf server/assets/fonts/LICENSE server/requirements.txt server/pdf_export.py server/app.py server/tests/test_pdf_export.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: add PDF character sheet export (POST /api/export/pdf)

New server/pdf_export.py renders resolve()'s output as a printable PDF
via fpdf2 — a fresh, self-drawn document, NOT a fill of v1's official
WotC template (that asset/module stays untouched; this was an explicit
choice among three options presented after Phase 2f's final review).
Mirrors markdown_export.py's exact section structure and field
selection. Bundles the DejaVu Sans font family (Bitstream Vera License,
confirmed redistribution-safe) since PDF core fonts have no Cyrillic
glyphs and this app's own characters are routinely Bulgarian.

Consolidates the by-now-three-times-duplicated export route body into a
single parameterized POST /api/export/<fmt> with a {format: (renderer,
mimetype)} lookup table, per Phase 2f's own final review flagging this
as the right move once a third format existed. The two existing URLs
(/api/export/yaml, /api/export/markdown) are unchanged; behavioral
equivalence verified against the existing test suite before/after.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Frontend PDF download + `EXPORT_FORMATS` refactor

**Files:**
- Modify: `frontend/src/pages/ExportPage.tsx`

**Interfaces:**
- Consumes: `POST /api/export/pdf` (Task 1).

- [ ] **Step 1: Rewrite `frontend/src/pages/ExportPage.tsx`**

Read the current file first — it has a `handleExport(format: "yaml" | "markdown")` with an inline ternary picking endpoint/extension/MIME type, and downloads via `resp.text()` → `new Blob([text], {type: mimeType})`. This step does two things at once: adds the PDF format, AND fixes a real bug this addition would otherwise trigger — `resp.text()` decodes the response body as text, which corrupts binary content (a PDF is binary); switching to `resp.blob()` fixes this for PDF and works identically for the existing text formats (a `Blob` built from `resp.blob()` downloads the same as one built from `resp.text()` did), so this isn't a special case for PDF, it's a strictly more correct approach for all three formats. As a side effect, the client no longer needs to separately track a MIME type at all — `resp.blob()` already carries the server's real `Content-Type`.

```tsx
import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

const EXPORT_FORMATS = {
  yaml: { endpoint: "/api/export/yaml", extension: "yaml", label: "YAML" },
  markdown: { endpoint: "/api/export/markdown", extension: "md", label: "Markdown" },
  pdf: { endpoint: "/api/export/pdf", extension: "pdf", label: "PDF" },
} as const;

type ExportFormat = keyof typeof EXPORT_FORMATS;

export function ExportPage() {
  const { draft } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

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

  async function handleExport(format: ExportFormat) {
    const config = EXPORT_FORMATS[format];
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
      const blob = await resp.blob();
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
      {(Object.keys(EXPORT_FORMATS) as ExportFormat[]).map((format) => (
        <button
          key={format}
          type="button"
          disabled={!canExport || exportingFormat !== null}
          onClick={() => handleExport(format)}
        >
          {exportingFormat === format ? "Изтегляне…" : `Изтегли ${EXPORT_FORMATS[format].label}`}
        </button>
      ))}
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

Build a complete level-1 Cleric or Wizard character through the real UI. Confirm all three buttons ("Изтегли YAML", "Изтегли Markdown", "Изтегли PDF") are disabled while any choice is pending, and all three enable together once fully resolved. Click "Изтегли PDF" — confirm a `.pdf` file downloads and actually opens as a valid PDF (not a corrupted/empty file — this is exactly the failure mode the `resp.text()` → `resp.blob()` fix in Step 1 prevents; if you skipped straight to adding PDF without that fix, this is where it would show up as a broken download). Confirm the PDF content matches the character built (name, class, abilities, equipment, spells if applicable, details if filled in). Click "Изтегли YAML" and "Изтегли Markdown" too — confirm both still work exactly as before this phase (regression check for the `resp.blob()` switch affecting the pre-existing text formats).

```bash
kill %1 %2
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ExportPage.tsx
git commit -m "$(cat <<'EOF'
feat: add PDF download button to the Export step

Generalizes the export button config into an EXPORT_FORMATS map (yaml/
markdown/pdf), per Phase 2f's own final review flagging this as the
right move at a third format. Switches the download path from
resp.text() to resp.blob() — the former would corrupt PDF's binary
content; the latter works correctly for all three formats and picks up
the server's real Content-Type automatically, so the client no longer
tracks MIME types itself at all.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes (for whoever executes this plan)

- The `resp.text()` → `resp.blob()` switch in Task 2 is not optional polish — it is the fix for a real bug the PDF addition would otherwise introduce (binary content corrupted by text decoding). Do not skip it or treat it as a nice-to-have; verify it live in Step 3, not just by reading the diff.
- Task 1's font-asset step (Step 0) is the one step in this plan that isn't pure code — it fetches and places binary files and verifies a license. If the exact `brew install font-dejavu` path isn't available in the execution environment, the goal (DejaVu Sans + Sans-Bold TTFs, with their license text, confirmed to cover Cyrillic) matters more than the exact command — adapt the acquisition method, but don't skip the license-text verification or the Cyrillic-coverage check.
- This plan was written with the PDF-export decision already made by the human (fresh library, no v1 reuse) after Phase 2f's final review presented three options. Do not re-litigate that choice mid-implementation — if something makes fresh PDF rendering impractical partway through, stop and report back rather than silently falling back to a different one of the three original options.
