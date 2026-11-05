"""Turns a Resolution (see engine/resolve.py) into a human-readable
Markdown character sheet. Not a port of the v1 markdown_render.py at the
repo root (removed in D-5) — that module is scoped to chargen.build()'s different sheet
shape (it has fields v2 doesn't compute yet, like HP tracking and
currency, and skips fields v2 does have). This module reads only
resolution["sheet"]/["derived"] exactly as engine/resolve.py's resolve()
already produces them — no new engine computation happens here.
"""
from __future__ import annotations

from catalog.reference_data import ABILITIES, LANGUAGE_NAMES, SKILL_NAMES, proficiency_label
from export_fields import DETAIL_SECTIONS, SPELL_PICK_KEYS, extra_blocks, pack_contents_suffix, worn_wielded_line
from export_labels import DEFAULT_LANG, check_lang, label, word

_LANGUAGE_NAMES = LANGUAGE_NAMES
_PROFICIENCY_SECTIONS = (("armor", "profArmor"), ("weapons", "profWeapons"), ("tools", "profTools"))
_EQUIPMENT_SECTIONS = [("granted", "equipGranted"), ("chosen", "equipChosen"), ("added", "equipAdded")]


def _fmt_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _species_label(species: dict | None) -> str:
    if not species:
        return "—"
    label = species["name"]
    if species.get("subspecies"):
        label += f" ({species['subspecies']['name']})"
    if species.get("variant"):
        label += f" - {species['variant']['name']}"
    return label


def _class_label(classes: list) -> str:
    if not classes:
        return "—"
    parts = []
    for c in classes:
        # Single-class drafts keep the plain name (the level is already
        # shown once, in the level prefix); a multiclass draft's level
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


def _fmt_spell_slots(slots: dict, lang: str) -> str:
    """slots is derived["spellSlots"]/["warlockSpellSlots"] — a dict of
    only the nonzero slot levels, keyed by level as a string (see
    engine/spells.py's _nonzero_spell_slots). Sorted numerically (dict
    insertion order already happens to be ascending since resolve()
    builds it that way, but this doesn't rely on that)."""
    ordered = sorted(slots, key=int)
    return ", ".join(label(lang, "slotLevel", lvl=lvl, n=slots[lvl]) for lvl in ordered)


def _skill_lines(derived: dict, proficient: list[str], expertise: list[str] = (), lang: str = DEFAULT_LANG) -> list[str]:
    skills = derived["skills"]
    ordered = sorted(skills, key=lambda sid: SKILL_NAMES.get(sid, sid))
    lines = []
    for skill_id in ordered:
        name = SKILL_NAMES.get(skill_id, skill_id)
        marker = "●" if skill_id in proficient else "○"
        tag = f" {label(lang, 'expertiseTag')}" if skill_id in expertise else ""
        lines.append(f"- {marker} {name}: {_fmt_mod(skills[skill_id])}{tag}")
    return lines


def to_markdown(resolution: dict, lang: str = DEFAULT_LANG) -> str:
    """The character sheet as Markdown in `lang` ("bg", the default, or "en"): the labels come from export_labels,
    every name from the data stays as it is."""
    check_lang(lang)
    sheet = resolution["sheet"]
    derived = resolution["derived"]
    lines: list[str] = []

    classes = sheet["classes"]
    bg = sheet["background"]

    class_label = _class_label(classes)

    lines.append(f"# {sheet['name'] or label(lang, 'unnamed')}")
    lines.append("")
    lines.append(
        f"**{label(lang, 'level', level=sheet['level'])} {class_label}** | "
        f"**{label(lang, 'background')}:** {bg['name'] if bg else '—'} | "
        f"**{label(lang, 'species')}:** {_species_label(sheet['species'])}"
    )
    lines.append("")

    lines.append(f"## {label(lang, 'secCombat')}")
    lines.append(f"- **{label(lang, 'armorClass')}:** {derived['armorClass']}")
    lines.append(
        f"- **{label(lang, 'hitPoints')}:** {derived['hitPointMax']} ({derived['hitDice']})"
        if derived["hitDice"] is not None
        else f"- **{label(lang, 'hitPoints')}:** {derived['hitPointMax']} (—)"
    )
    lines.append(f"- **{label(lang, 'speed')}:** {label(lang, 'feet', n=derived['speed'])}" if derived["speed"] is not None else f"- **{label(lang, 'speed')}:** —")
    lines.append(f"- **{label(lang, 'initiative')}:** {_fmt_mod(derived['initiative'])}")
    lines.append(f"- **{label(lang, 'passivePerception')}:** {derived['passivePerception']}")
    lines.append(f"- **{label(lang, 'passiveInsight')}:** {derived['passiveInsight']}")
    lines.append(f"- **{label(lang, 'passiveInvestigation')}:** {derived['passiveInvestigation']}")
    lines.append(f"- **{label(lang, 'proficiencyBonus')}:** {_fmt_mod(derived['proficiencyBonus'])}")
    lines.append("")

    lines.append(f"## {label(lang, 'secAbilities')}")
    lines.append(_ability_line(sheet, derived))
    lines.append("")

    lines.append(f"## {label(lang, 'secSaves')}")
    lines.append(_saves_line(derived, sheet["proficiencies"]["savingThrows"]))
    lines.append("")

    lines.append(f"## {label(lang, 'secSkills')}")
    lines.extend(_skill_lines(derived, sheet["proficiencies"]["skills"], sheet.get("expertiseSkills") or [], lang))
    lines.append("")

    languages = sheet["proficiencies"]["languages"]
    lines.append(f"## {label(lang, 'secLanguages')}")
    lines.append(
        ", ".join(_LANGUAGE_NAMES.get(lang_id, lang_id) for lang_id in languages) if languages else "—"
    )
    lines.append("")

    lines.append(f"## {label(lang, 'secProficiencies')}")
    any_prof = False
    for key, label_key in _PROFICIENCY_SECTIONS:
        entries = sheet["proficiencies"].get(key) or []
        if entries:
            any_prof = True
            lines.append(f"- **{label(lang, label_key)}:** " + ", ".join(proficiency_label(e) for e in entries))
    if not any_prof:
        lines.append("—")
    lines.append("")

    equipment = sheet["equipment"]
    lines.append(f"## {label(lang, 'secEquipment')}")
    any_equipment = False
    for key, label_key in _EQUIPMENT_SECTIONS:
        entries = equipment[key]
        if not entries:
            continue
        any_equipment = True
        lines.append(f"### {label(lang, label_key)}")
        for e in entries:
            qty_tag = f" x{e['qty']}" if e.get("qty", 1) != 1 else ""
            equipped_tag = f" {label(lang, 'equipped')}" if e.get("equipped") else ""
            lines.append(f"- {e['name']}{qty_tag}{equipped_tag}{pack_contents_suffix(e, lang)}")
        lines.append("")
    line = worn_wielded_line(sheet, lang)
    if line:
        any_equipment = True
        lines.append(line)
        lines.append("")
    if not any_equipment:
        lines.append("—")
        lines.append("")

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
        lines.append(f"## {label(lang, 'secSpells')}")
        class_names = {c["id"]: c["name"] for c in classes}
        multi_caster = len(spells) > 1
        for class_spells in spells:
            # Only label each subsection by class when there's more than
            # one caster to disambiguate — a single-class sheet keeps the
            # plain, unlabeled headings it always had.
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            save_dc = class_spells["spellSaveDC"]
            if save_dc is not None:
                lines.append(
                    f"- **{label(lang, 'spellSaveDc')}{suffix}:** {save_dc}  |  "
                    f"**{label(lang, 'spellAttackBonus')}{suffix}:** {_fmt_mod(class_spells['spellAttackBonus'])}"
                )
        spell_slots = derived["spellSlots"]
        if spell_slots:
            lines.append(f"- **{label(lang, 'spellSlots')}:** {_fmt_spell_slots(spell_slots, lang)}")
        warlock_slots = derived["warlockSpellSlots"]
        if warlock_slots:
            lines.append(f"- **{label(lang, 'pactSlots')}:** {_fmt_spell_slots(warlock_slots, lang)}")
        for class_spells in spells:
            suffix = f" ({class_names.get(class_spells['classId'], class_spells['classId'])})" if multi_caster else ""
            if class_spells["cantrips"]:
                lines.append(f"### {label(lang, 'cantrips')}{suffix}")
                for s in class_spells["cantrips"]:
                    lines.append(f"- {s['name']}")
                lines.append("")
            if class_spells.get("spellbook"):
                book = ", ".join(f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})" for s in class_spells["spellbook"])
                lines.append(f"- **{label(lang, 'spellbook')}{suffix}:** {book}")
                lines.append("")
            if class_spells["known"]:
                lines.append(f"### {label(lang, 'preparedSpells')}{suffix}")
                for s in class_spells["known"]:
                    lines.append(f"- {s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})")
                lines.append("")
            if class_spells.get("mysticArcanum"):
                arcanum = ", ".join(f"{m['name']} ({label(lang, 'spellLevel', lvl=m['level'])})" for m in class_spells["mysticArcanum"])
                lines.append(f"- **{label(lang, 'mysticArcanum')}{suffix}:** {arcanum}")
                lines.append("")
            for key in SPELL_PICK_KEYS:  # C6d: Wizard 18 / 20 picks
                if class_spells.get(key):
                    picked = ", ".join(f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})" for s in class_spells[key])
                    lines.append(f"- **{label(lang, key)}{suffix}:** {picked}")
                    lines.append("")
        lines.append("")

    innate = sheet.get("innateSpells") or []
    if innate:
        lines.append(f"## {label(lang, 'secInnate')}")
        for e in innate:
            level = label(lang, "innateFromLevel", level=e["level"]) if e.get("level") else ""
            note = f" - {e['note']}" if e.get("note") else ""  # RP5
            lines.append(f"- {e['name']} ({e.get('uses', '')}{level}){note}")
        lines.append("")

    for kind, text in extra_blocks(resolution, lang):
        if kind == "h2" and lines and lines[-1] != "":
            lines.append("")
        lines.append({"h2": f"## {text}", "h3": f"### {text}", "bullet": f"- {text}", "body": text}[kind])
    lines.append("")

    details = sheet["details"]
    if details:
        for section_key, field_keys in DETAIL_SECTIONS:
            present = [(word(lang, "detailFields", key), details[key]) for key in field_keys if key in details]
            if not present:
                continue
            lines.append(f"## {word(lang, 'detailSections', section_key)}")
            lines.append("")
            for field_label, value in present:
                lines.append(f"**{field_label}:**")
                lines.append("")
                lines.append(value)
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"
