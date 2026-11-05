"""docs/TERMS-PROPOSAL.md: game / rules terms whose Bulgarian wording is inconsistent, or where English vs Bulgarian is a real choice.

A PROPOSAL for the project owner. Nothing in the app is changed by it: no wording in a catalog, glossary, export label or
test depends on this file (a test only checks that the file is well formed and the document is up to date).

The table is GENERATED. Written by hand here is only `TERMS`: for each term the English wording (2024 Player's Handbook
first), the Bulgarian wordings to count (a label and a case-insensitive regex), 2-3 Bulgarian options, the
recommendation and notes. The counts and the "where used" column are computed from the sources, so they cannot drift:

* UI   = `frontend/src/copy/bg.ts` (strings and templates, glossary references resolved),
* msg  = the Bulgarian side of the server catalogs (problems, warnings, pruned, disabled, labels),
* exp  = `server/export_labels.py` `LABELS["bg"]` (Markdown / PDF),
* gloss = `server/i18n/glossary.json` `bg`.

A count is the number of texts (leaves) that contain the wording, not the number of occurrences.

    cd server && ../.venv/bin/python -m i18n.terms_table            # rewrite docs/TERMS-PROPOSAL.md
    cd server && ../.venv/bin/python -m i18n.terms_table --check     # exit 1 when the file is stale (the suite runs this)

To change a proposal: edit `TERMS`, regenerate, commit the file. Once the owner decides, change the wording in its
catalog (and glossary), then delete the row here.
"""
from __future__ import annotations

import pathlib
import re
import sys
from typing import NamedTuple

from i18n import glossary
from i18n.catalog import MESSAGES
from i18n.review_table import _copy_text, _flatten_labels
from i18n.ts_copy import COPY_DIR, flatten, parse_catalog

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = REPO / "docs" / "TERMS-PROPOSAL.md"

SURFACES = ("UI", "msg", "exp", "gloss")


class Term(NamedTuple):
    en: str                                  # 2024 PHB wording (or the app's English label)
    gloss: str | None                        # glossary id when the term is one (its `en` must equal `en`)
    wordings: tuple[tuple[str, str], ...]    # (label shown, regex counted)
    options: tuple[str, ...]                 # 2-3 Bulgarian options (may include "keep English")
    recommend: str
    notes: str


TERMS: tuple[Term, ...] = (
    Term("Feat / Feats", "feats",
         (("Талант / Таланти", r"талант"), ("Черти (for feats)", r"(общи|за произход|\(2014\)).*черти|черти (за произход|\(2014\))"),
          ("талант (feat): the English word in brackets", r"\(feats?\)|origin feat")),
         ("Талант", "Черта", "Feat (keep English)"),
         "Талант everywhere; no English in brackets.",
         "The glossary and many server messages already say Талант; only the three choice-card group headings say Черти, which "
         "collides with 'Черти и способности' (class features) and 'Черти на характера' (personality traits). One word for feat "
         "removes the ambiguity. The three Черти headings are pinned in C1 KNOWN_INCONSISTENCIES; several messages print both "
         "words, 'талант (feat)'."),
    Term("Class Features / feature", "classFeatures",
         (("Черти и способности", r"черти и способности"), ("чертата (a feature)", r"чертата"), ("Способност", r"способност")),
         ("Способности на класа", "Черти и способности (as now)", "Class Features (keep English)"),
         "Способности на класа for the section; 'способност' for one feature.",
         "'Черти' should stop meaning feats (see Feat). 'Черта' also means 'trait' (Черти на характера), so it is a poor word for "
         "'feature'. 'чертата Spellcasting или Pact Magic' (a disabled reason) would become 'способността ...'."),
    Term("Origin Feat", "originFeat",
         (("Талант от произхода", r"талант от произхода"), ("Черти за произход", r"черти за произход"),
          ("(Origin feat)", r"origin feat")),
         ("Талант от произхода (as in the glossary)", "Начален талант", "Origin Feat (keep English)"),
         "Талант от произхода.",
         "Follows the Feat decision. The 2024 PHB gives every Background one Origin feat, so the link to 'Произход' is the useful "
         "part of the name."),
    Term("Resistance", "resistance",
         (("Устойчивост", r"устойчивост"), ("съпротива / Съпротиви", r"съпротив")),
         ("Устойчивост (to damage)", "Съпротива", "Resistance (keep English)"),
         "Устойчивост; heading 'Устойчивост и имунитети'.",
         "Glossary, the damage-resistance card and the sheet field say Устойчивост; the resource lines and the heading "
         "'Съпротиви и имунитети' say съпротива (UI and BG export). 'Съпротива' reads as 'resistance' in the sense of opposing "
         "force; Устойчивост is the usual game translation. Singular 'щета' (UI) vs plural 'щети' (card): see Damage."),
    Term("Immunity / Vulnerability", "immunity",
         (("Имунитет", r"имунитет"), ("Уязвимост", r"уязвимост")),
         ("Имунитет / Уязвимост (as now)", "Неуязвимост / Уязвимост", "Immunity / Vulnerability (keep English)"),
         "Keep as now.",
         "Consistent in every surface. Listed because it sits next to Resistance in the same heading."),
    Term("Damage (resistance, immunity labels)", None,
         (("към щета (singular)", r"към щета"), ("на щети (plural)", r"на щети"), ("щети / вид щети", r"щети")),
         ("'към щета' everywhere", "'на щети' everywhere", "'към вид щета' (damage type)"),
         "Устойчивост към щети, Имунитет към щети, Уязвимост към щети.",
         "The sheet and the export say 'към щета' (singular); the choice card says 'Устойчивост на щети'. The plural reads more "
         "naturally when it means the whole damage category."),
    Term("Proficiency / proficient", None,
         (("владеене", r"владеене"), ("владее / се владее", r"владее|владеят|владеете|се владее"),
          ("Умение (also 'skill')", r"умени[ея]")),
         ("Владеене", "Опитност", "Proficiency (keep English)"),
         "Keep Владеене / владее.",
         "Consistent for the noun and verb. The risk is 'Умение', which is both the glossary word for Skills and part of "
         "'Бонус за умение' (Proficiency Bonus); see the next row."),
    Term("Proficiency Bonus", "proficiencyBonus",
         (("Бонус за умение", r"бонус за умение"),),
         ("Бонус за владеене", "Бонус за майсторство", "Proficiency Bonus (keep English)"),
         "Бонус за владеене.",
         "'Бонус за умение' reads as 'skill bonus' because Умения = Skills. 'Бонус за владеене' matches the noun used "
         "everywhere else (владеене). Glossary entry and one UI heading."),
    Term("Skills", "skills",
         (("Умения", r"умения"), ("Умение (one)", r"умение(?!\w)")),
         ("Умения", "Сръчности", "Skills (keep English)"),
         "Keep Умения.",
         "Consistent. The skill NAMES (Athletics ...) stay English as data."),
    Term("Expertise", None,
         (("Expertise (English)", r"expertise"), ("експертиза", r"експертиза")),
         ("Експертиза", "Майсторско владеене", "Expertise (keep English)"),
         "Експертиза.",
         "The UI and the export say 'експертиза' while the server messages keep the class-feature name 'Expertise'. The "
         "feature itself is a data name; messages that only talk about the concept can use the Bulgarian word."),
    Term("Cast (a spell)", None,
         (("изричам / изречете", r"изрич|изреч"),),
         ("изричам заклинание", "прилагам заклинание", "cast (keep English)"),
         "изричам.",
         "Only four messages (descriptions of invocation, arcanum, wizard picks, armour penalty) use a verb; all use 'изричам'. "
         "Listed so the choice is made once for any future text."),
    Term("Cantrip / Cantrips", "cantrips",
         (("Трик / Трикове", r"трик"),),
         ("Трик", "Малко заклинание", "Cantrip (keep English)"),
         "Keep Трик / Трикове (or Cantrip if you want to match the spell data).",
         "'Трик' is the app's own rendering of 'cantrip' (no standard Bulgarian word exists); spell names stay English data, so a "
         "Bulgarian 'Трик' label sits next to English spell names."),
    Term("Spell Slots", "spellSlots",
         (("Spell Slot(s)", r"spell slots?"), ("слот / слотове (resource lines)", r"слот"),
          ("Клетки за заклинания (old)", r"клетк")),
         ("Spell Slots (as now)", "Слотове за заклинания", "Клетки за заклинания (the old wording)"),
         "Keep Spell Slots (owner decision 2026-11-05). Decide whether the resource lines keep the short Bulgarian 'слот'.",
         "The heading, the glossary and the export now agree. The resource lines (UI and export) still use the Bulgarian "
         "'слот', which was outside the 2026-11-05 decision. 'Pact Magic Slots' stays English as exported."),
    Term("Saving Throw", "savingThrows",
         (("Спасително хвърляне / Спасителни хвърляния", r"спасителн"), ("Спасяване (in Spell Save DC)", r"спасяване")),
         ("Спасително хвърляне", "Защитно хвърляне", "Saving Throw (keep English)"),
         "Keep Спасително хвърляне.",
         "Consistent. The only other form is 'Спасяване' inside the Spell Save DC label."),
    Term("Spell Save DC", "spellSaveDc",
         (("Спасяване за заклинание (DC)", r"спасяване за заклинание"),),
         ("Трудност на спасяването от заклинание (DC)", "DC на заклинанието", "Spell Save DC (keep English)"),
         "DC на спасяването от заклинание.",
         "The current phrase mixes Bulgarian with the English abbreviation DC. Armor Class has the same shape 'Клас броня (AC)'; "
         "if the abbreviation stays in brackets the two read alike."),
    Term("Spell Attack Modifier", "spellAttackBonus",
         (("Бонус за атака", r"бонус за атака"), ("Модификатор (ability)", r"модификатор")),
         ("Модификатор на атаката със заклинание", "Бонус за атака със заклинание", "Spell Attack Modifier (keep English)"),
         "Бонус за атака със заклинание.",
         "The English glossary follows the 2024 PHB ('Modifier'); the Bulgarian was 'Бонус за атака' without 'spell'. 'Модификатор' "
         "is already used for the ability modifier column."),
    Term("Hit Points", "hitPoints",
         (("Точки живот", r"точки живот"),),
         ("Точки живот", "Кондиция / Жизненост", "Hit Points (keep English)"),
         "Keep Точки живот.",
         "Consistent in all surfaces."),
    Term("Hit Point Dice", "hitPointDice",
         (("Зарове за живот", r"зарове за живот"),),
         ("Зарове за живот", "Зарове за точки живот", "Hit Point Dice (keep English)"),
         "Зарове за точки живот.",
         "Only 'Hit Points' is 'Точки живот'; the dice are 'за живот'. Matching the long form makes the two terms read as a pair."),
    Term("Armor Class", "armorClass",
         (("Клас броня (AC)", r"клас броня"),),
         ("Клас броня (AC)", "Защита", "Armor Class (keep English)"),
         "Keep Клас броня (AC).",
         "Consistent; 'AC' is in the permanent abbreviation allowlist."),
    Term("Background", "background",
         (("Произход", r"произход"), ("Background (English)", r"background")),
         ("Произход", "Предистория", "Background (keep English)"),
         "Произход, or keep Background as the step name only if the owner wants it recognisable next to the PHB.",
         "The glossary and the sheet say Произход; the step bar, page title, labels and 4 ruleset-help sentences print 'Background' "
         "(the SK6-BI LEGACY words). 'Произход' is also used for 'Origin Feat' ('от произхода'), which is a good link. "
         "'Предистория' would be the literal 'backstory'."),
    Term("Species", "species",
         (("Раса", r"раса|расат"), ("Species (English)", r"species"), ("вид (as species)", r"вида \(species\)|на вида")),
         ("Раса", "Вид", "Species (keep English)"),
         "Раса, or Вид if you want to follow the 2024 rename.",
         "The 2024 PHB renamed Race to Species. The glossary and the sheet say Раса; the step bar and species page keep the "
         "English word (LEGACY); the ruleset-help sentences say 'вида (species)'. 'Вид' also means 'kind/type' (вид оръжие, вид щети), "
         "so it is the riskiest of the three."),
    Term("Short Rest / Long Rest", "shortRest",
         (("кратка почивка", r"кратка почивка"), ("дълга почивка", r"дълга почивка")),
         ("кратка / дълга почивка (as now)", "кратък / дълъг отдих", "Short Rest / Long Rest (keep English)"),
         "Keep as now.",
         "Consistent. 'Rest' is lower case in running text and capitalised in headings only where the glossary asks for it."),
    Term("Weapon Mastery", "weaponMastery",
         (("Майсторство с оръжия", r"майсторство с оръжия"), ("Майсторство със заклинания", r"майсторство със заклинания")),
         ("Майсторство с оръжия", "Weapon Mastery (keep English)", "Оръжейно майсторство"),
         "Keep Майсторство с оръжия.",
         "Consistent. The same word is used for 'Spell Mastery' (Wizard level 18); fine, but keep it away from 'Expertise' and "
         "'Proficiency'."),
    Term("Advantage / Disadvantage", None,
         (("недостатък", r"недостатък"), ("disadvantage (English)", r"disadvantage")),
         ("предимство / недостатък", "Advantage / Disadvantage (keep English)", "предимство / пречка"),
         "предимство / недостатък.",
         "The Bulgarian word for Advantage ('предимство') is not used anywhere yet. 'недостатък' is used in a message, the export and "
         "the UI, and one LEGACY UI text still says 'disadvantage' in English."),
    Term("Bonus Action", None,
         (("бонус действие", r"бонус действие"),),
         ("бонус действие", "допълнително действие", "Bonus Action (keep English)"),
         "бонус действие.",
         "Consistent where it appears."),
    Term("Fighting Style / Metamagic / Maneuvers / Eldritch Invocation (class option names)", None,
         (("Fighting Style", r"fighting style"), ("Eldritch / Metamagic / Maneuver", r"eldritch|metamagic|maneuver"),
          ("Mystic Arcanum", r"mystic arcanum")),
         ("Keep English (data names)", "Боен стил / Метамагия / Маневри / Мистични инвокации", "English name with a Bulgarian gloss"),
         "Keep English.",
         "These are names the class data prints in English in both languages. Translating them only inside messages would make "
         "the message and the card disagree."),
    Term("Ability / Ability Score", "abilityScores",
         (("Характеристики", r"характеристик"), ("Модификатор / Бонус (columns)", r"модификатор|бонус(?!\w)")),
         ("Характеристики", "Показатели", "Ability Scores (keep English)"),
         "Keep Характеристики.",
         "Consistent. The ability NAMES in messages stay as 'Intelligence, Wisdom, Charisma' or the codes STR / DEX; a decision on "
         "their Bulgarian form would be a separate row."),
    Term("Carrying Capacity", "carryingCapacity",
         (("Носимост", r"носимост"), ("Претоварен", r"претоварен")),
         ("Носимост", "Товароносимост", "Carrying Capacity (keep English)"),
         "Keep Носимост.",
         "Consistent; 'Товароносимост' is the dictionary word if the owner prefers it."),
    Term("Special Senses (Darkvision, Blindsight ...)", "senses",
         (("Сетива", r"сетива"), ("тъмно / сляпо / истинско зрение", r"(тъмно|сляпо|истинско|дяволско) зрение"),
          ("усещане за вибрации", r"вибрации")),
         ("as now", "Darkvision / Blindsight (keep English)", "Тъмно зрение (capitalised)"),
         "Keep as now.",
         "Consistent; the sense names are lower case in running text and the glossary has them that way."),
)


def _corpus() -> list[tuple[str, str, str]]:
    """(surface, key, Bulgarian text) for every Bulgarian text the app owns."""
    import export_labels

    gloss = glossary.load()
    out: list[tuple[str, str, str]] = []
    for key, leaf in flatten(parse_catalog(COPY_DIR / "bg.ts", "bg")).items():
        out.append(("UI", key, _copy_text(leaf, gloss, "bg")))
    for key, entry in MESSAGES.items():
        out.append(("msg", key, entry["bg"]))
    for key, text in _flatten_labels(export_labels.LABELS["bg"]):
        out.append(("exp", key, text))
    for key, term in gloss.items():
        out.append(("gloss", key, term["bg"]))
    return out


def count(corpus, regex: str) -> dict[str, list[str]]:
    """Surface -> keys of the texts that contain the wording."""
    rx = re.compile(regex, re.IGNORECASE)
    hits: dict[str, list[str]] = {s: [] for s in SURFACES}
    for surface, key, text in corpus:
        if rx.search(text):
            hits[surface].append(key)
    return hits


def _counts_text(hits: dict[str, list[str]]) -> str:
    parts = [f"{s} {len(hits[s])}" for s in SURFACES if hits[s]]
    return ", ".join(parts) if parts else "0"


def _cell(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().replace("|", "\\|")


def render() -> str:
    corpus = _corpus()
    lines = [
        "# Terms proposal: English or Bulgarian, and which Bulgarian",
        "",
        "<!-- GENERATED by `cd server && ../.venv/bin/python -m i18n.terms_table`. Do not edit; change `TERMS` in "
        "server/i18n/terms_table.py and regenerate. `--check` exits 1 when this file is stale. -->",
        "",
        "A proposal for the project owner. **Nothing in the app was changed because of this file**: every wording below is "
        "what the app prints today. For each term please say which option you want (or keep the recommendation); the "
        "developer then changes the one catalog and removes the row.",
        "",
        "How to read it: **English term** is the 2024 Player's Handbook wording (the glossary id in brackets when the term is "
        "one). **Current BG wordings** are the Bulgarian words found in the app with how many texts use them: `UI` = web "
        "app texts, `msg` = server messages (problems, warnings, pruned and disabled reasons, card labels), `exp` = Markdown "
        "and PDF export labels, `gloss` = the glossary. A count is the number of texts that contain the wording. **Where "
        "used** adds a few example keys. Names of game content (classes, species, feats, spells, items, skills) stay English "
        "in both languages and are not in this table.",
        "",
        "| # | English term | Where used (examples) | Current BG wordings (texts) | BG options | Recommendation | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for number, t in enumerate(TERMS, 1):
        wording_cells = []
        examples: list[str] = []
        for label, regex in t.wordings:
            hits = count(corpus, regex)
            wording_cells.append(f"{label}: {_counts_text(hits)}")
            for s in SURFACES:
                for key in hits[s][:1]:
                    ex = f"{s}:{key}"
                    if ex not in examples:
                        examples.append(ex)
        english = t.en + (f" (`{t.gloss}`)" if t.gloss else "")
        where = "; ".join(f"`{e}`" for e in examples[:4])
        lines.append(
            f"| {number} | {_cell(english)} | {_cell(where)} | {_cell('<br>'.join(wording_cells))} | "
            f"{_cell('<br>'.join(f'{i}. {o}' for i, o in enumerate(t.options, 1)))} | {_cell(t.recommend)} | {_cell(t.notes)} |"
        )
    lines += ["", f"{len(TERMS)} terms. Source of the wordings: `docs/I18N-REVIEW.md`, `KNOWN_INCONSISTENCIES` in "
                  "`server/tests/test_i18n_completeness.py`, `server/i18n/glossary.json`, `frontend/src/copy/bg.ts`, the server "
                  "catalogs and `server/export_labels.py`.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None, out: pathlib.Path = OUT) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = render()
    if "--check" in args:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print(f"{out} is stale; run: cd server && ../.venv/bin/python -m i18n.terms_table", file=sys.stderr)
            return 1
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(TERMS)} terms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
