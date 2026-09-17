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
