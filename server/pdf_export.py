"""Turns a Resolution (see engine/resolve.py) into a printable PDF
character sheet via fpdf2 — a fresh, self-drawn document, NOT a fill of
v1's official WotC template (repo-root pdf_fill.py / assets/
character-sheet-template.pdf, removed in D-5) — see this plan's Scope note for why.
Mirrors markdown_export.py's exact section structure and field
selection; only the rendering target differs. The two should be kept in
sync by hand if resolve()'s output shape changes — they are two
renderings of one contract, not independently-designed documents.
"""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from catalog.reference_data import ABILITIES, LANGUAGE_NAMES, SKILL_NAMES, proficiency_label
from export_fields import (DETAIL_SECTIONS, SPELL_PICK_KEYS, class_label as _class_label, extra_blocks, fmt_mod as _fmt_mod,
                           fmt_spell_slots as _fmt_spell_slots, pack_contents_suffix, species_label as _species_label,
                           worn_wielded_line)
from export_labels import DEFAULT_LANG, check_lang, label, word

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
_LANGUAGE_NAMES = LANGUAGE_NAMES
_PROFICIENCY_SECTIONS = (("armor", "profArmor"), ("weapons", "profWeapons"), ("tools", "profTools"))
_EQUIPMENT_SECTIONS = [("granted", "equipGranted"), ("chosen", "equipChosen"), ("added", "equipAdded")]


class _SheetPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_font("DejaVu", "", str(_FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(_FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_page()

    def h1(self, text: str) -> None:
        self.set_font("DejaVu", "B", 18)
        self.multi_cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")  # multi_cell wraps a long name; cell would run off the page

    def h2(self, text: str) -> None:
        self.ln(2)
        self.set_font("DejaVu", "B", 13)
        self.multi_cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(180, 180, 180)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def h3(self, text: str) -> None:
        self.set_font("DejaVu", "B", 11)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def body(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def bullet(self, text: str) -> None:
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, f"• {text}", new_x="LMARGIN", new_y="NEXT")


def to_pdf(resolution: dict, lang: str = DEFAULT_LANG) -> bytes:
    """The character sheet as a PDF in `lang` ("bg", the default, or "en"). DejaVu Sans draws both scripts."""
    check_lang(lang)
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    pdf = _SheetPDF()

    classes = sheet["classes"]
    bg = sheet["background"]

    class_label = _class_label(classes)

    pdf.h1(sheet["name"] or label(lang, "unnamed"))
    pdf.body(
        f"{label(lang, 'level', level=sheet['level'])} {class_label}  |  "
        f"{label(lang, 'background')}: {bg['name'] if bg else '—'}  |  "
        f"{label(lang, 'species')}: {_species_label(sheet['species'])}"
    )

    pdf.h2(label(lang, "secCombat"))
    hit_dice = derived["hitDice"] if derived["hitDice"] is not None else "—"
    speed = label(lang, "feet", n=derived["speed"]) if derived["speed"] is not None else "—"
    pdf.body(
        f"{label(lang, 'armorClass')}: {derived['armorClass']}\n"
        f"{label(lang, 'hitPoints')}: {derived['hitPointMax']} ({hit_dice})\n"
        f"{label(lang, 'speed')}: {speed}\n"
        f"{label(lang, 'initiative')}: {_fmt_mod(derived['initiative'])}\n"
        f"{label(lang, 'passivePerception')}: {derived['passivePerception']}\n"
        f"{label(lang, 'passiveInsight')}: {derived['passiveInsight']}\n"
        f"{label(lang, 'passiveInvestigation')}: {derived['passiveInvestigation']}\n"
        f"{label(lang, 'proficiencyBonus')}: {_fmt_mod(derived['proficiencyBonus'])}"
    )

    pdf.h2(label(lang, "secAbilities"))
    scores = sheet["abilities"]
    mods = derived["abilityModifiers"]
    pdf.body("   ".join(f"{ab} {scores[ab]} ({_fmt_mod(mods[ab])})" for ab in ABILITIES))

    pdf.h2(label(lang, "secSaves"))
    saves = derived["savingThrows"]
    proficient_saves = sheet["proficiencies"]["savingThrows"]
    pdf.body("   ".join(
        f"{'●' if ab in proficient_saves else '○'} {ab} {_fmt_mod(saves[ab])}" for ab in ABILITIES
    ))

    pdf.h2(label(lang, "secSkills"))
    skills = derived["skills"]
    proficient_skills = sheet["proficiencies"]["skills"]
    expertise = sheet.get("expertiseSkills") or []
    for skill_id in sorted(skills, key=lambda sid: SKILL_NAMES.get(sid, sid)):
        marker = "●" if skill_id in proficient_skills else "○"
        tag = f" {label(lang, 'expertiseTag')}" if skill_id in expertise else ""
        pdf.bullet(f"{marker} {SKILL_NAMES.get(skill_id, skill_id)}: {_fmt_mod(skills[skill_id])}{tag}")

    pdf.h2(label(lang, "secLanguages"))
    languages = sheet["proficiencies"]["languages"]
    pdf.body(", ".join(_LANGUAGE_NAMES.get(lang_id, lang_id) for lang_id in languages) if languages else "—")

    pdf.h2(label(lang, "secProficiencies"))
    any_prof = False
    for key, label_key in _PROFICIENCY_SECTIONS:
        entries = sheet["proficiencies"].get(key) or []
        if entries:
            any_prof = True
            pdf.body(f"{label(lang, label_key)}: " + ", ".join(proficiency_label(e) for e in entries))
    if not any_prof:
        pdf.body("—")

    equipment = sheet["equipment"]
    pdf.h2(label(lang, "secEquipment"))
    any_equipment = False
    for key, label_key in _EQUIPMENT_SECTIONS:
        entries = equipment[key]
        if not entries:
            continue
        any_equipment = True
        pdf.h3(label(lang, label_key))
        for e in entries:
            qty_tag = f" x{e['qty']}" if e.get("qty", 1) != 1 else ""
            equipped_tag = f" {label(lang, 'equipped')}" if e.get("equipped") else ""
            pdf.bullet(f"{e['name']}{qty_tag}{equipped_tag}{pack_contents_suffix(e, lang)}")
    line = worn_wielded_line(sheet, lang)
    if line:
        any_equipment = True
        pdf.body(line)
    if not any_equipment:
        pdf.body("—")

    # sheet["spells"]: one entry per spellcasting class (see markdown_export.to_markdown for the layout notes).
    spells = sheet["spells"]
    if spells:
        pdf.h2(label(lang, "secSpells"))
        class_names = {c["id"]: c["name"] for c in classes}
        multi_caster = len(spells) > 1
        for class_spells in spells:
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            save_dc = class_spells["spellSaveDC"]
            if save_dc is not None:
                pdf.body(
                    f"{label(lang, 'spellSaveDc')}{suffix}: {save_dc}   "
                    f"{label(lang, 'spellAttackBonus')}{suffix}: {_fmt_mod(class_spells['spellAttackBonus'])}"
                )
        spell_slots = derived["spellSlots"]
        if spell_slots:
            pdf.body(f"{label(lang, 'spellSlots')}: {_fmt_spell_slots(spell_slots, lang)}")
        warlock_slots = derived["warlockSpellSlots"]
        if warlock_slots:
            pdf.body(f"{label(lang, 'pactSlots')}: {_fmt_spell_slots(warlock_slots, lang)}")
        for class_spells in spells:
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            if class_spells["cantrips"]:
                pdf.h3(f"{label(lang, 'cantrips')}{suffix}")
                for s in class_spells["cantrips"]:
                    pdf.bullet(s["name"])
            if class_spells.get("spellbook"):
                book = ", ".join(f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})" for s in class_spells["spellbook"])
                pdf.body(f"{label(lang, 'spellbook')}{suffix}: {book}")
            if class_spells["known"]:
                pdf.h3(f"{label(lang, 'preparedSpells')}{suffix}")
                for s in class_spells["known"]:
                    pdf.bullet(f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})")
            if class_spells.get("mysticArcanum"):
                arcanum = ", ".join(f"{m['name']} ({label(lang, 'spellLevel', lvl=m['level'])})" for m in class_spells["mysticArcanum"])
                pdf.body(f"{label(lang, 'mysticArcanum')}{suffix}: {arcanum}")
            for key in SPELL_PICK_KEYS:  # C6d: Wizard 18 / 20 picks
                if class_spells.get(key):
                    picked = ", ".join(f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})" for s in class_spells[key])
                    pdf.body(f"{label(lang, key)}{suffix}: {picked}")

    innate = sheet.get("innateSpells") or []
    if innate:
        pdf.h2(label(lang, "secInnate"))
        for e in innate:
            level = label(lang, "innateFromLevel", level=e["level"]) if e.get("level") else ""
            note = f" - {e['note']}" if e.get("note") else ""  # RP5
            pdf.bullet(f"{e['name']} ({e.get('uses', '')}{level}){note}")

    for kind, text in extra_blocks(resolution, lang):
        {"h2": pdf.h2, "h3": pdf.h3, "bullet": pdf.bullet, "body": pdf.body}[kind](text)

    details = sheet["details"]
    if details:
        for section_key, field_keys in DETAIL_SECTIONS:
            present = [(word(lang, "detailFields", key), details[key]) for key in field_keys if key in details]
            if not present:
                continue
            pdf.h2(word(lang, "detailSections", section_key))
            for field_label, value in present:
                pdf.h3(f"{field_label}:")
                pdf.body(value)
                pdf.ln(1)

    return bytes(pdf.output())
