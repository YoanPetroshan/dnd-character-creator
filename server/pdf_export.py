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
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, f"• {text}", new_x="LMARGIN", new_y="NEXT")


def to_pdf(resolution: dict) -> bytes:
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    pdf = _SheetPDF()

    cls = sheet["class"]
    bg = sheet["background"]

    class_label = cls["name"] if cls else "—"
    if cls and cls.get("subclass"):
        class_label += f" ({cls['subclass']['name']})"

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
