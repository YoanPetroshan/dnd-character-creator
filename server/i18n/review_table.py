"""docs/I18N-REVIEW.md: the wordings the earlier slices (and the C1 audit) flagged as uncertain, in one plain table.

The table is GENERATED. The English and Bulgarian text of each row is read from where it lives (message catalogs,
export labels, glossary, frontend copy), so it cannot drift from the code; what is written by hand here is only WHICH
entries are flagged and WHY (`FLAGS`, with the slice that raised the doubt). Names (N1) are not in a catalog: their
text is hand-written below and a test checks each is still present in `frontend/src/names/bgNames.ts`.

    cd server && ../.venv/bin/python -m i18n.review_table            # rewrite docs/I18N-REVIEW.md
    cd server && ../.venv/bin/python -m i18n.review_table --check     # exit 1 when the file is stale (the suite runs this)

To flag a wording: add a line to `FLAGS`, run the command, commit the regenerated file. To resolve one after the owner
answered: fix the wording in its catalog, delete the line, regenerate.
"""
from __future__ import annotations

import pathlib
import re
import sys

from i18n import glossary
from i18n.catalog import MESSAGES
from i18n.ts_copy import COPY_DIR, flatten, parse_catalog

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = REPO / "docs" / "I18N-REVIEW.md"
NAMES_TS = REPO / "frontend" / "src" / "names" / "bgNames.ts"

# kind -> where `ref` is looked up:
#   msg       key of the server message catalogs (problems, warnings, pruned, disabled, labels)
#   export    dotted path in export_labels.LABELS[lang]
#   glossary  term id of i18n/glossary.json
#   copy      dotted path in frontend/src/copy/bg.ts and en.ts
#   name      a Bulgarian name of frontend/src/names/bgNames.ts (EN = its official transliteration, written here)
#
# (kind, ref, raised by, why it is uncertain)
FLAGS: list[tuple[str, str, str, str]] = [
    # ---- glossary: rules terms --------------------------------------------------------------------------------------
    ("glossary", "originFeat", "I0", "New wording: no Bulgarian label for the 2024 'Origin Feat' existed before the glossary."),
    ("glossary", "feats", "C1", "Glossary says 'Таланти'; the choice-card groups in the Bulgarian UI say 'Черти' (see the copy rows below). One word should win."),
    ("glossary", "classFeatures", "C1", "'Черти и способности' uses 'черти' for class features while 'feat' is 'талант': check the two do not read as the same thing."),
    ("glossary", "proficiencyBonus", "C1", "'Бонус за умение' uses the word that is also the Bulgarian for 'Skills' ('Умения'); is that the wording you want?"),
    ("glossary", "spellAttackBonus", "I0", "English follows the 2024 PHB ('Spell Attack Modifier'); the Bulgarian is the app's older 'Бонус за атака' (no 'spell', 'бонус' not 'модификатор')."),
    ("glossary", "spellSaveDc", "C1", "'Спасяване за заклинание (DC)' mixes a Bulgarian phrase with the English abbreviation DC."),
    ("glossary", "spellSlots", "C1", "Glossary and the web UI say 'Клетки за заклинания'; the Bulgarian PDF/Markdown export prints 'Spell Slots' (its output is pinned byte for byte, so it was not changed)."),
    ("glossary", "cantrips", "I4", "Glossary plural is 'Трикове'; the server messages count with 'трик / трика'. 'Трик' for 'cantrip' is the app's own rendering."),
    ("glossary", "resistance", "C1", "Glossary 'Устойчивост'; resource lines and one heading in the UI and exports say 'съпротива' / 'Съпротиви' (see the rows below)."),
    # ---- exports (XL) -----------------------------------------------------------------------------------------------
    ("export", "spellSlots", "XL", "Bulgarian export prints the English 'Spell Slots' (kept so the Bulgarian output stays byte-identical)."),
    ("export", "pactSlots", "XL", "Bulgarian export prints the English 'Pact Magic Slots' (same reason)."),
    ("export", "attackVersatile", "XL", "Bulgarian export keeps the English attack tag 'versatile'."),
    ("export", "attackOffhand", "XL", "Bulgarian export keeps the English attack tag 'off hand'."),
    ("export", "attackRange", "XL", "Bulgarian export keeps the English attack tag 'range'."),
    ("export", "secResistances", "C1", "Heading 'Съпротиви и имунитети' vs the glossary's 'Устойчивост' (the line labels below it say 'Устойчивост към щета')."),
    ("export", "resAll", "C1", "'съпротива' vs the glossary's 'Устойчивост'."),
    ("export", "resSome", "C1", "'съпротива' vs the glossary's 'Устойчивост'."),
    # ---- server messages --------------------------------------------------------------------------------------------
    ("msg", "label-damage-resistance", "C1", "'Устойчивост на щети' here, 'Устойчивост към щета' in the sheet and export lines: 'на' vs 'към', plural vs singular."),
    ("msg", "label-prefixed", "I5", "'{head}: {tail}': the tail is a rules term with no translation yet (Expertise, Fighting Style, Maneuvers, Metamagic, Eldritch Invocation), so Bulgarian shows it in English."),
    ("msg", "disabled-already-known", "I4", "'вече се знае' (already known) as the short reason under an option."),
    ("msg", "disabled-already-proficient", "I4", "'вече се владее' (already proficient): 'владеене' as 'proficiency' is the app's existing choice."),
    ("msg", "disabled-already-taken-from", "I4", "'вече взето ({where})': 'взето' (taken) for a feat/option already picked."),
    ("msg", "disabled-already-mastered", "I4", "'вече усвоено (Майсторство с оръжия)': 'усвоено' is new wording for 'already mastered'."),
    ("msg", "disabled-requires-warlock-level", "I4", "'изисква ниво N на warlock': class name left in English."),
    ("msg", "disabled-requires-cantrip", "I4", "'изисква трика {spell}': 'трик' for 'cantrip', in the accusative."),
    ("msg", "prereq-feat-category", "I4", "'талант (feat) от нужната категория': the English word is added in brackets to help the reader."),
    ("msg", "prereq-martial", "I4", "'владеене на бойни оръжия (martial)': 'бойни оръжия' for 'martial weapons'."),
    ("msg", "pruned-proficient", "I3", "'вече се владее {names}': the name list follows the sentence head, so one wording fits one or many names."),
    ("msg", "pruned-known-ignored", "I3", "'вече се знае {names}': same pattern as above."),
    ("msg", "over-selected", "I2", "'{count|избор|избора}': plural forms chosen by the engine; English keeps 'selection(s)'."),
    ("msg", "pruned-wizard-not-in-spellbook", "I3", "Long sentence with two plural-agreement parts ('запазено ... не е' / 'запазени ... не са'); worth a native read."),
    ("msg", "disabled-school-limit", "I4", "Plural agreement of 'заклинание може да е / заклинания могат да са' and 'или' between two schools."),
    ("msg", "noun-cantrip", "I5", "'{n|трик|трика}' is the building block of every 'Choose N cantrips' sentence."),
    ("msg", "desc-species-feats", "I5", "'Изберете {count} таланта': the count form of 'талант' (not 'черти')."),
    # ---- frontend copy ----------------------------------------------------------------------------------------------
    ("copy", "choice.groups.general", "C1", "Feat group 'Общи черти': glossary says feats are 'Таланти'."),
    ("copy", "choice.groups.origin", "C1", "Feat group 'Черти за произход': glossary says 'Талант от произхода'."),
    ("copy", "choice.groups.feat-2014", "C1", "Feat group 'Черти (2014)': glossary says 'Таланти'."),
    ("copy", "sheet.defenses.title", "C1", "'Съпротиви и имунитети' vs the glossary's 'Устойчивост' (same heading as the export)."),
    ("copy", "sheet.resources.text.resistancesAllButPsychic", "C1", "'съпротива' vs the glossary's 'Устойчивост'."),
    ("copy", "nav.steps.home", "SK6-BI", "Page names that the Bulgarian UI has always shown in English (the LEGACY list): translating them is a deliberate later change."),
    ("copy", "nav.steps.background", "SK6-BI", "English in the Bulgarian UI on purpose (LEGACY); glossary 'Произход'."),
    ("copy", "nav.steps.species", "SK6-BI", "English in the Bulgarian UI on purpose (LEGACY); glossary 'Раса'."),
    ("copy", "nav.steps.abilities", "SK6-BI", "English in the Bulgarian UI on purpose (LEGACY); glossary 'Характеристики'."),
    ("copy", "nav.steps.equipment", "SK6-BI", "English in the Bulgarian UI on purpose (LEGACY); glossary 'Екипировка'."),
    ("copy", "nav.steps.export", "SK6-BI", "English in the Bulgarian UI on purpose (LEGACY)."),
    ("copy", "backgroundPage.choose", "SK6-BI", "'— избери background —': mixes the English word into a Bulgarian sentence (LEGACY)."),
    ("copy", "exportPage.missing.species", "SK6-BI", "'Избери species.': the English word inside a Bulgarian sentence (LEGACY)."),
    ("copy", "speciesPage.noChoices", "SK6-BI", "'Няма избори за този species.': the English word inside a Bulgarian sentence (LEGACY)."),
    # ---- random names (N1) --------------------------------------------------------------------------------------------
    ("name", "Пресиан", "N1", "Planner marked it '?'."),
    ("name", "Ивайло", "N1", "Planner marked it '?'."),
    ("name", "Борил", "N1", "Planner marked it '?'."),
    ("name", "Асен", "N1", "Cuman/Turkic dynastic root kept (Асенов as the surname)."),
    ("name", "Шишман", "N1", "Cuman/Turkic dynastic root kept (Шишманов as the surname)."),
    ("name", "Гостун", "N1", "Added with doubt: khan name, etymology disputed."),
    ("name", "Умор", "N1", "Added with doubt: khan name, etymology disputed."),
    ("name", "Левски", "N1", "Added with doubt: a nickname that became a surname; Левска as the female form."),
    ("name", "Райна", "N1", "Popular and Slavic by form, but often tied to a Christian-era figure."),
    ("name", "Калина", "N1", "Popular, Slavic by form (with Румяна)."),
    ("name", "Румяна", "N1", "Popular, Slavic by form (with Калина)."),
    ("name", "Калоян", "N1", "Tagged christian (included by default since 2026-11-05); could arguably count as medieval Bulgarian (Калоянов too)."),
    ("name", "Кънчев", "N1", "Tagged christian (included by default since 2026-11-05); could arguably count as medieval Bulgarian."),
    ("name", "Кераца", "N1", "Tagged christian (included by default): a folk form of a Greek root."),
    ("name", "Гергана", "N1", "Tagged christian (included by default): a folk form of a Greek root."),
    ("name", "Тонка", "N1", "Tagged christian (included by default): a folk form of a Greek root."),
]

# Official streamlined transliteration of the flagged names (what the English dice button prints).
TRANSLITERATION: dict[str, str] = {
    "Пресиан": "Presian", "Ивайло": "Ivaylo", "Борил": "Boril", "Асен": "Asen", "Шишман": "Shishman", "Гостун": "Gostun",
    "Умор": "Umor", "Левски": "Levski", "Райна": "Rayna", "Калина": "Kalina", "Румяна": "Rumyana", "Калоян": "Kaloyan",
    "Кънчев": "Kanchev", "Кераца": "Keratsa", "Гергана": "Gergana", "Тонка": "Tonka",
}

KINDS = ("glossary", "export", "msg", "copy", "name")
KIND_TITLES = {
    "glossary": "Rules terms (glossary)",
    "export": "Exports (Markdown / PDF labels)",
    "msg": "Messages from the server (problems, warnings, pruned reasons, disabled reasons, card texts)",
    "copy": "Web UI texts",
    "name": "Random names (the dice button)",
}
_CYRILLIC = re.compile("[Ѐ-ӿ]")


def _flatten_labels(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _flatten_labels(v, path + (k,))
    else:
        yield ".".join(path), node


def _copy_text(leaf, gloss: dict, lang: str) -> str:
    if leaf.kind == "fn":
        return "(template) " + re.sub(r"\s+", " ", leaf.text)
    text = re.sub(r"\$\{g\.(\w+)\.(en|bg)\}", lambda m: gloss[m.group(1)][m.group(2)], leaf.text)
    whole = re.fullmatch(r"g\.(\w+)\.(en|bg)", text)
    return gloss[whole.group(1)][whole.group(2)] if whole else text


def lookup(kind: str, ref: str) -> tuple[str, str]:
    """(English, Bulgarian) text of a flagged entry; KeyError when it no longer exists (the test catches that)."""
    if kind == "msg":
        return MESSAGES[ref]["en"], MESSAGES[ref]["bg"]
    if kind == "glossary":
        term = glossary.load()[ref]
        return term["en"], term["bg"]
    if kind == "export":
        import export_labels
        labels = {lang: dict(_flatten_labels(export_labels.LABELS[lang])) for lang in ("en", "bg")}
        return labels["en"][ref], labels["bg"][ref]
    if kind == "copy":
        gloss = glossary.load()
        bg = flatten(parse_catalog(COPY_DIR / "bg.ts", "bg"))
        en = flatten(parse_catalog(COPY_DIR / "en.ts", "en"))
        return _copy_text(en[ref], gloss, "en"), _copy_text(bg[ref], gloss, "bg")
    if kind == "name":
        if ref not in NAMES_TS.read_text(encoding="utf-8"):
            raise KeyError(ref)
        return TRANSLITERATION[ref], ref
    raise KeyError(kind)


def _cell(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().replace("|", "\\|")
    return text if len(text) <= 220 else text[:217] + "..."


def render() -> str:
    lines = [
        "# Bulgarian and English wordings to review",
        "",
        "<!-- GENERATED by `cd server && ../.venv/bin/python -m i18n.review_table`. Do not edit; change the flag list in "
        "server/i18n/review_table.py and regenerate. `--check` exits 1 when this file is stale. -->",
        "",
        "This is the list of wordings that earlier work on the Bulgarian/English switch was NOT sure about. Nothing here "
        "is broken: the app uses the wording shown. For each row please say keep, or write the wording you want in the "
        "last column; the developer then changes the one place named in the key and removes the row.",
        "",
        "How to read it: **Key** says where the text lives (kind and name), **EN** and **BG** are the texts the app prints "
        "now, **Why** is the doubt and the slice that raised it. `{name}`, `{n}` and similar are filled in by the app; "
        "`{n|a|b}` picks form `a` for 1 and form `b` otherwise. Names of game content (classes, spells, feats, items) "
        "stay English in both languages on purpose and are not listed.",
        "",
    ]
    number = 0
    for kind in KINDS:
        rows = [f for f in FLAGS if f[0] == kind]
        if not rows:
            continue
        lines += [f"## {KIND_TITLES[kind]}", "", "| # | Key | EN | BG | Why uncertain (slice) | Your call |", "|---|---|---|---|---|---|"]
        for _kind, ref, source, why in rows:
            number += 1
            en, bg = lookup(kind, ref)
            lines.append(f"| {number} | `{kind}:{ref}` | {_cell(en)} | {_cell(bg)} | {_cell(why)} ({source}) | |")
        lines.append("")
    lines += [
        f"{number} rows. Slices: I0 glossary, I2-I5 server messages, XL exports, SK6-BI web UI texts, N1 names, "
        "C1 the consistency audit (`server/tests/test_i18n_completeness.py`, `KNOWN_INCONSISTENCIES`).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None, out: pathlib.Path = OUT) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render()
    if "--check" in args:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print(f"{out} is stale; run: cd server && ../.venv/bin/python -m i18n.review_table", file=sys.stderr)
            return 1
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(FLAGS)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
