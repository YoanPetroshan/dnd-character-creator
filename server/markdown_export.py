"""Turns a Resolution (see engine/resolve.py) into a human-readable
Markdown character sheet. Not a port of the v1 markdown_render.py at the
repo root — that module is scoped to chargen.build()'s different sheet
shape (it has fields v2 doesn't compute yet, like HP tracking and
currency, and skips fields v2 does have). This module reads only
resolution["sheet"]/["derived"] exactly as engine/resolve.py's resolve()
already produces them — no new engine computation happens here.
"""
from __future__ import annotations

from catalog.reference_data import ABILITIES, LANGUAGES, SKILL_NAMES

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


def _ability_line(sheet: dict, derived: dict) -> str:
    scores = sheet["abilities"]
    mods = derived["abilityModifiers"]
    return "  ".join(f"**{ab}** {scores[ab]} ({_fmt_mod(mods[ab])})" for ab in ABILITIES)


def _saves_line(derived: dict, proficient: list[str]) -> str:
    saves = derived["savingThrows"]
    parts = []
    for ab in ABILITIES:
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

    classes = sheet["classes"]
    bg = sheet["background"]

    class_label = _class_label(classes)

    lines.append(f"# {sheet['name'] or 'Безименен герой'}")
    lines.append("")
    lines.append(
        f"**Ниво {sheet['level']} {class_label}** | "
        f"**Произход:** {bg['name'] if bg else '—'} | "
        f"**Раса:** {_species_label(sheet['species'])}"
    )
    lines.append("")

    lines.append("## Бойни показатели")
    lines.append(f"- **Клас броня (AC):** {derived['armorClass']}")
    lines.append(
        f"- **Точки живот:** {derived['hitPointMax']} ({derived['hitDice']})"
        if derived["hitDice"] is not None
        else f"- **Точки живот:** {derived['hitPointMax']} (—)"
    )
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
    lines.append(
        ", ".join(_LANGUAGE_NAMES.get(lang_id, lang_id) for lang_id in languages) if languages else "—"
    )
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

    # sheet["spells"] is a list with one entry per class that has
    # spellcasting this level (multiclass-aware as of the Phase 3b-i
    # final-review fix — a single-class caster still gets a one-entry
    # list). derived["spellSaveDC"]/["spellAttackBonus"] stay PRIMARY-class-
    # only (see resolve.py), so they're shown once, up top, not per class.
    spells = sheet["spells"]
    if spells:
        lines.append("## Заклинания")
        if derived["spellSaveDC"] is not None:
            lines.append(
                f"- **Спасяване за заклинание (DC):** {derived['spellSaveDC']}  |  "
                f"**Бонус за атака:** {_fmt_mod(derived['spellAttackBonus'])}"
            )
        class_names = {c["id"]: c["name"] for c in classes}
        multi_caster = len(spells) > 1
        for class_spells in spells:
            # Only label each subsection by class when there's more than
            # one caster to disambiguate — a single-class sheet keeps the
            # plain, unlabeled headings it always had.
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            if class_spells["cantrips"]:
                lines.append(f"### Трикове{suffix}")
                for s in class_spells["cantrips"]:
                    lines.append(f"- {s['name']}")
                lines.append("")
            if class_spells["known"]:
                lines.append(f"### Известни/Подготвени заклинания{suffix}")
                for s in class_spells["known"]:
                    lines.append(f"- {s['name']} (ниво {s['level']})")
                lines.append("")
        lines.append("")

    details = sheet["details"]
    if details:
        for section_label, fields in _DETAIL_SECTIONS:
            present = [(label, details[key]) for key, label in fields if key in details]
            if not present:
                continue
            lines.append(f"## {section_label}")
            lines.append("")
            for label, value in present:
                lines.append(f"**{label}:**")
                lines.append("")
                lines.append(value)
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"
