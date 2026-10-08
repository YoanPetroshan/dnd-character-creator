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

from catalog.reference_data import ABILITIES, LANGUAGES, SKILL_NAMES, proficiency_label

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_LANGUAGE_NAMES = {lang["index"]: lang["name"] for lang in LANGUAGES}
_PROFICIENCY_SECTIONS = (("armor", "Брони"), ("weapons", "Оръжия"), ("tools", "Инструменти"))

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


def _class_label(classes: list) -> str:
    if not classes:
        return "—"
    parts = []
    for c in classes:
        # Single-class drafts keep the plain name (the level is already
        # shown once, in the "Ниво N" prefix); a multiclass draft's level
        # line covers only the total, so each class here carries its own.
        part = c["name"] if len(classes) == 1 else f"{c['name']} {c['level']}"
        if c.get("subclass"):
            part += f" ({c['subclass']['name']})"
        parts.append(part)
    return " / ".join(parts)


def _fmt_spell_slots(slots: dict) -> str:
    """Mirrors markdown_export._fmt_spell_slots exactly (duplicated per
    this file's established convention) — slots is
    derived["spellSlots"]/["warlockSpellSlots"], a dict of only the
    nonzero slot levels keyed by level as a string."""
    ordered = sorted(slots, key=int)
    return ", ".join(f"ниво {lvl}: {slots[lvl]}" for lvl in ordered)


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
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, f"• {text}", new_x="LMARGIN", new_y="NEXT")


def to_pdf(resolution: dict) -> bytes:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    pdf = _SheetPDF()

    classes = sheet["classes"]
    bg = sheet["background"]

    class_label = _class_label(classes)

    pdf.h1(sheet["name"] or "Безименен герой")
    pdf.body(
        f"Ниво {sheet['level']} {class_label}  |  "
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

    pdf.h2("Владеене")
    any_prof = False
    for key, label in _PROFICIENCY_SECTIONS:
        entries = sheet["proficiencies"].get(key) or []
        if entries:
            any_prof = True
            pdf.body(f"{label}: " + ", ".join(proficiency_label(e) for e in entries))
    if not any_prof:
        pdf.body("—")

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

    # sheet["spells"] is a list with one entry per class that has
    # spellcasting this level (multiclass-aware as of the Phase 3b-i
    # final-review fix — a single-class caster still gets a one-entry
    # list). Each entry now carries its OWN spellSaveDC/spellAttackBonus
    # (Phase 3b-ii — a multiclass character's casters each use their own
    # spellcasting ability), so these are shown once per caster, labeled,
    # rather than once at the top as before. derived["spellSlots"] is the
    # single shared pool across every non-Warlock caster;
    # derived["warlockSpellSlots"] is Warlock's own separate Pact Magic
    # pool — both are character-wide, not per-caster, so they're shown
    # once each, after the per-caster DC/attack lines.
    spells = sheet["spells"]
    if spells:
        pdf.h2("Заклинания")
        class_names = {c["id"]: c["name"] for c in classes}
        multi_caster = len(spells) > 1
        for class_spells in spells:
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            save_dc = class_spells["spellSaveDC"]
            if save_dc is not None:
                pdf.body(
                    f"Спасяване за заклинание (DC){suffix}: {save_dc}   "
                    f"Бонус за атака{suffix}: {_fmt_mod(class_spells['spellAttackBonus'])}"
                )
        spell_slots = derived["spellSlots"]
        if spell_slots:
            pdf.body(f"Spell Slots: {_fmt_spell_slots(spell_slots)}")
        warlock_slots = derived["warlockSpellSlots"]
        if warlock_slots:
            pdf.body(f"Pact Magic Slots: {_fmt_spell_slots(warlock_slots)}")
        for class_spells in spells:
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            if class_spells["cantrips"]:
                pdf.h3(f"Трикове{suffix}")
                for s in class_spells["cantrips"]:
                    pdf.bullet(s["name"])
            if class_spells["known"]:
                pdf.h3(f"Известни/Подготвени заклинания{suffix}")
                for s in class_spells["known"]:
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
