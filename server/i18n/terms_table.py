"""docs/TERMS-PROPOSAL.md: the game / rules terms whose Bulgarian wording was inconsistent, and what the owner decided (T1).

History: the table started (2026-11-05) as a PROPOSAL; the owner accepted the recommendation of every row and decided that
a Bulgarian rules term is followed by its English term in brackets ("Талант (Feat)") everywhere it is used as a term (web
UI, server messages, export labels, glossary). This file now records the decision: each row has a `decision` (DONE + the
final wording), and the checks below keep the app in line with it.

The table is GENERATED. Written by hand here is only `TERMS`: for each term the English wording (2024 Player's Handbook
first), the Bulgarian wordings to count (a label and a case-insensitive regex; an "(old)" label may count 0 now), the options
and the recommendation of the proposal, the notes, the DECISION, and two kinds of check:

* `checks`: (Bulgarian noun regex, English bracket regex) pairs. Every Bulgarian text that contains the noun must also hold a
  bracket with the English term, except the entries of `COVERAGE_EXCEPTIONS` (each with its reason). Verbs ("владее",
  "изричам") and the parts of a message after the first occurrence are not nouns/first occurrences and are not checked.
* `forbid`: a regex for the OLD wording; it must occur nowhere (outside brackets) in the Bulgarian texts.

The counts and the "where used" column are computed from the sources, so they cannot drift:

* UI   = `frontend/src/copy/bg.ts` (strings and templates, glossary references resolved),
* msg  = the Bulgarian side of the server catalogs (problems, warnings, pruned, disabled, labels),
* exp  = `server/export_labels.py` `LABELS["bg"]` (Markdown / PDF),
* gloss = `server/i18n/glossary.json` `bg`.

A count is the number of texts (leaves) that contain the wording, not the number of occurrences.

    cd server && ../.venv/bin/python -m i18n.terms_table            # rewrite docs/TERMS-PROPOSAL.md
    cd server && ../.venv/bin/python -m i18n.terms_table --check     # exit 1 when the file is stale (the suite runs this)
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
    decision: str = ""                       # T1: what was done (final wording)
    checks: tuple[tuple[str, str], ...] = () # (Bulgarian noun regex, English bracket regex)
    forbid: str | None = None                # regex of the old wording that must be gone


TERMS: tuple[Term, ...] = (
    Term("Feat / Feats", "feats",
         (("Талант / Таланти", r"талант"), ("Черти (for feats, old)", r"(общи|за произход|\(2014\)).*черти|черти (за произход|\(2014\))"),
          ("(Feat) / (Feats) in brackets", r"\(feats?\)|\(origin feats?\)|\(general feats\)")),
         ("Талант", "Черта", "Feat (keep English)"),
         "Талант everywhere; no English in brackets.",
         "The glossary and many server messages already said Талант; only the three choice-card group headings said Черти, which "
         "collides with 'Черти и способности' (class features) and 'Черти на характера' (personality traits). One word for feat "
         "removes the ambiguity. (The 'no English in brackets' part was superseded by the owner's bracket rule.)",
         "DONE: Талант (Feat) / Таланти (Feats). Card groups: Общи таланти (General Feats), Таланти от произхода (Origin Feats), "
         "Таланти от 2014 (Feats). 'Черти' no longer means a feat; the home-page label 'Прояви на дарби' is now 'Изисквания за "
         "таланти (Feat Prerequisites)'.",
         ((r"\bталант\w*", r"feat"),), r"черти за произход|общи черти|черти \(2014"),
    Term("Class Features / feature", "classFeatures",
         (("Черти и способности (old)", r"черти и способности"), ("чертата (a feature, old)", r"чертата"), ("Способност", r"способност")),
         ("Способности на класа", "Черти и способности (as now)", "Class Features (keep English)"),
         "Способности на класа for the section; 'способност' for one feature.",
         "'Черти' should stop meaning feats (see Feat). 'Черта' also means 'trait' (Черти на характера), so it is a poor word for "
         "'feature'. 'чертата Spellcasting или Pact Magic' (a disabled reason) becomes 'способността ...'.",
         "DONE: Способности на класа (Class Features) for the section; Способности (Features) on the class tabs; "
         "'способността (Feature) Spellcasting' in the prerequisite messages.",
         ((r"способности на класа|\bспособности\b(?! на по)|способността (?!да)", r"class features|feature"),
          (r"способности на по-високи нива", r"features")), r"черти и способности|\bчертата\b"),
    Term("Origin Feat", "originFeat",
         (("Талант от произхода", r"талант от произхода"), ("Черти за произход (old)", r"черти за произход"),
          ("(Origin Feat) in brackets", r"\(origin feats?\)")),
         ("Талант от произхода (as in the glossary)", "Начален талант", "Origin Feat (keep English)"),
         "Талант от произхода.",
         "Follows the Feat decision. The 2024 PHB gives every Background one Origin feat, so the link to 'Произход' is the useful "
         "part of the name.",
         "DONE: Талант от произхода (Origin Feat).",
         ((r"талант\w* от произхода", r"origin feat"),), None),
    Term("Resistance", "resistance",
         (("Устойчивост", r"устойчивост"), ("съпротива / Съпротиви (old)", r"съпротив")),
         ("Устойчивост (to damage)", "Съпротива", "Resistance (keep English)"),
         "Устойчивост; heading 'Устойчивост и имунитети'.",
         "Glossary, the damage-resistance card and the sheet field said Устойчивост; the resource lines and the heading "
         "'Съпротиви и имунитети' said съпротива (UI and BG export). 'Съпротива' reads as 'resistance' in the sense of opposing "
         "force; Устойчивост is the usual game translation. Singular 'щета' (UI) vs plural 'щети' (card): see Damage.",
         "DONE: Устойчивост (Resistance) everywhere; heading 'Устойчивост (Resistance) и имунитети (Immunities)'; resource "
         "lines 'устойчивост (Resistance): ...'; 'съпротива' is gone.",
         ((r"устойчивост", r"resistance"),), r"съпротив"),
    Term("Immunity / Vulnerability", "immunity",
         (("Имунитет", r"имунитет"), ("Уязвимост", r"уязвимост")),
         ("Имунитет / Уязвимост (as now)", "Неуязвимост / Уязвимост", "Immunity / Vulnerability (keep English)"),
         "Keep as now.",
         "Consistent in every surface. Listed because it sits next to Resistance in the same heading.",
         "DONE (wording kept, brackets added): Имунитет (Immunity) / Имунитети (Immunities), Уязвимост (Vulnerability).",
         ((r"имунитет", r"immunit"), (r"уязвимост", r"vulnerab")), None),
    Term("Damage (resistance, immunity labels)", None,
         (("към щета (singular, old)", r"към щета"), ("на щети (plural, old)", r"устойчивост на щети"),
          ("щети / вид щети", r"щети")),
         ("'към щета' everywhere", "'на щети' everywhere", "'към вид щета' (damage type)"),
         "Устойчивост към щети, Имунитет към щети, Уязвимост към щети.",
         "The sheet and the export said 'към щета' (singular); the choice card said 'Устойчивост на щети'. The plural reads more "
         "naturally when it means the whole damage category.",
         "DONE: Устойчивост (Resistance) към щети, Имунитет (Immunity) към щети, Уязвимост (Vulnerability) към щети; also "
         "'всички видове щети освен психични' and 'типове щети' in the resource lines (damage as a category is plural).",
         (), r"към щета|на щети|видове щета|типове щета"),
    Term("Proficiency / proficient", None,
         (("владеене", r"владеене"), ("владее / се владее", r"владее|владеят|владеете|се владее"),
          ("Умение (also 'skill')", r"умени[ея]")),
         ("Владеене", "Опитност", "Proficiency (keep English)"),
         "Keep Владеене / владее.",
         "Consistent for the noun and verb. The risk is 'Умение', which is both the glossary word for Skills and part of "
         "'Бонус за умение' (Proficiency Bonus); see the next row.",
         "DONE (wording kept): Владеене (Proficiency) / Владеене на ... (Skill Proficiencies ...) as noun, heading, label and "
         "column title; the verb 'владее / се владее / владеете' has no brackets.",
         ((r"владеене", r"proficienc"),), None),
    Term("Proficiency Bonus", "proficiencyBonus",
         (("Бонус за умение (old)", r"бонус за умение"), ("Бонус за владеене", r"бонус за владеене")),
         ("Бонус за владеене", "Бонус за майсторство", "Proficiency Bonus (keep English)"),
         "Бонус за владеене.",
         "'Бонус за умение' reads as 'skill bonus' because Умения = Skills. 'Бонус за владеене' matches the noun used "
         "everywhere else (владеене). Glossary entry and one UI heading.",
         "DONE: Бонус за владеене (Proficiency Bonus).",
         ((r"бонус за владеене", r"proficiency bonus"),), r"бонус за умение"),
    Term("Skills", "skills",
         (("Умения", r"умения"), ("Умение (one)", r"умение(?!\w)")),
         ("Умения", "Сръчности", "Skills (keep English)"),
         "Keep Умения.",
         "Consistent. The skill NAMES (Athletics ...) stay English as data.",
         "DONE (wording kept, brackets added): Умения (Skills), Умение (Skill).",
         ((r"умени[ея]", r"skill"),), None),
    Term("Expertise", None,
         (("Expertise (English, old)", r"(?<!\()expertise(?!\))"), ("експертиза", r"експертиза")),
         ("Експертиза", "Майсторско владеене", "Expertise (keep English)"),
         "Експертиза.",
         "The UI and the export said 'експертиза' while the server messages kept the class-feature name 'Expertise'. The "
         "feature itself is a data name; messages that only talk about the concept can use the Bulgarian word.",
         "DONE: експертиза (Expertise) in the messages (the card label tail 'Expertise' is now the catalog entry "
         "label-expertise); sheet / export: експертиза (Expertise), tag '(експертиза, Expertise)'.",
         ((r"експертиза", r"expertise"),), None),
    Term("Cast (a spell)", None,
         (("изричам / изречете", r"изрич|изреч"),),
         ("изричам заклинание", "прилагам заклинание", "cast (keep English)"),
         "изричам.",
         "Only four messages (descriptions of invocation, arcanum, wizard picks, armour penalty) use a verb; all use 'изричам'. "
         "Listed so the choice is made once for any future text.",
         "DONE (kept): изричам; the one message that said 'произнасяте' (prerequisite 'способността да произнасяте ...') now "
         "says 'изричате'. A verb has no brackets.",
         (), r"произнас"),
    Term("Cantrip / Cantrips", "cantrips",
         (("Трик / Трикове", r"трик"),),
         ("Трик", "Малко заклинание", "Cantrip (keep English)"),
         "Keep Трик / Трикове (or Cantrip if you want to match the spell data).",
         "'Трик' is the app's own rendering of 'cantrip' (no standard Bulgarian word exists); spell names stay English data, so a "
         "Bulgarian 'Трик' label sits next to English spell names.",
         "DONE (wording kept, brackets added): Трик (Cantrip) / Трикове (Cantrips).",
         ((r"\bтрик\w*", r"cantrip"),), None),
    Term("Spell Slots", "spellSlots",
         (("Spell Slot(s)", r"spell slots?"), ("слот / слотове (resource lines, old)", r"слот"),
          ("Клетки за заклинания (old)", r"клетк")),
         ("Spell Slots (as now)", "Слотове за заклинания", "Клетки за заклинания (the old wording)"),
         "Keep Spell Slots (owner decision 2026-11-05). Decide whether the resource lines keep the short Bulgarian 'слот'.",
         "The heading, the glossary and the export agreed. The resource lines (UI and export) still used the Bulgarian "
         "'слот', which was outside the 2026-11-05 decision. 'Pact Magic Slots' stays English as exported.",
         "DONE: Spell Slots stays English only, no brackets. Read as: the resource lines use the English term too ('Spell Slot "
         "ниво N за M т.', 'Spell Slots до ниво N', 'срещу Spell Slot'); the Bulgarian 'слот' is gone.",
         (), r"слот|клетк"),
    Term("Saving Throw", "savingThrows",
         (("Спасително хвърляне / Спасителни хвърляния", r"спасителн"), ("Спасяване (in Spell Save DC, old)", r"спасяване за заклинание")),
         ("Спасително хвърляне", "Защитно хвърляне", "Saving Throw (keep English)"),
         "Keep Спасително хвърляне.",
         "Consistent. The only other form is 'Спасяване' inside the Spell Save DC label.",
         "DONE (wording kept, brackets added): Спасително хвърляне (Saving Throw) / Спасителни хвърляния (Saving Throws).",
         ((r"спасителн\w+ хвърлян\w+", r"saving throw"),), None),
    Term("Spell Save DC", "spellSaveDc",
         (("Спасяване за заклинание (DC, old)", r"спасяване за заклинание"), ("DC на спасяването от заклинание", r"dc на спасяването")),
         ("Трудност на спасяването от заклинание (DC)", "DC на заклинанието", "Spell Save DC (keep English)"),
         "DC на спасяването от заклинание.",
         "The old phrase mixed Bulgarian with the English abbreviation DC. Armor Class has the same shape 'Клас броня (AC)'; "
         "if the abbreviation stays in brackets the two read alike.",
         "DONE: DC на спасяването от заклинание (Spell Save DC).",
         ((r"dc на спасяването", r"spell save dc"),), r"спасяване за заклинание"),
    Term("Spell Attack Modifier", "spellAttackBonus",
         (("Бонус за атака (old)", r"бонус за атака(?! със заклинание)"), ("Бонус за атака със заклинание", r"бонус за атака със заклинание"),
          ("Модификатор (ability)", r"модификатор")),
         ("Модификатор на атаката със заклинание", "Бонус за атака със заклинание", "Spell Attack Modifier (keep English)"),
         "Бонус за атака със заклинание.",
         "The English glossary follows the 2024 PHB ('Modifier'); the Bulgarian was 'Бонус за атака' without 'spell'. 'Модификатор' "
         "is already used for the ability modifier column.",
         "DONE: Бонус за атака със заклинание (Spell Attack Modifier).",
         ((r"бонус за атака със заклинание", r"spell attack modifier"),), r"бонус за атака(?! със заклинание)"),
    Term("Hit Points", "hitPoints",
         (("Точки живот", r"точки живот"),),
         ("Точки живот", "Кондиция / Жизненост", "Hit Points (keep English)"),
         "Keep Точки живот.",
         "Consistent in all surfaces.",
         "DONE (wording kept, brackets added): Точки живот (Hit Points).",
         ((r"точки живот", r"hit point"),), None),
    Term("Hit Point Dice", "hitPointDice",
         (("Зарове за живот (old)", r"зарове за живот"), ("Зарове за точки живот", r"зарове за точки живот")),
         ("Зарове за живот", "Зарове за точки живот", "Hit Point Dice (keep English)"),
         "Зарове за точки живот.",
         "Only 'Hit Points' is 'Точки живот'; the dice are 'за живот'. Matching the long form makes the two terms read as a pair.",
         "DONE: Зарове за точки живот (Hit Point Dice).",
         ((r"зарове за точки живот", r"hit point dice"),), r"зарове за живот"),
    Term("Armor Class", "armorClass",
         (("Клас броня", r"клас броня"),),
         ("Клас броня (AC)", "Защита", "Armor Class (keep English)"),
         "Keep Клас броня (AC).",
         "Consistent; 'AC' is in the permanent abbreviation allowlist.",
         "DONE: Клас броня (Armor Class, AC). Chosen over 'Клас броня (Armor Class)' because the abbreviation AC is used on its "
         "own in messages and by players; both stand in the same brackets. The abbreviation alone ('добавя към AC') is not the term.",
         ((r"клас броня", r"armor class"),), None),
    Term("Background", "background",
         (("Произход", r"произход"), ("Background (English, old)", r"(?<![('])\bbackgrounds?\b(?![)'])")),
         ("Произход", "Предистория", "Background (keep English)"),
         "Произход, or keep Background as the step name only if the owner wants it recognisable next to the PHB.",
         "The glossary and the sheet said Произход; the step bar, page title, labels and 4 ruleset-help sentences printed 'Background' "
         "(the SK6-BI LEGACY words). 'Произход' is also used for 'Origin Feat' ('от произхода'), which is a good link. "
         "'Предистория' would be the literal 'backstory'.",
         "DONE: Произход (Background) replaces the English step label, page title, select label, placeholder and the "
         "ruleset-help words (the 'избери background' text is 'избери произход (Background)').",
         ((r"произход\w*", r"background|origin feat"),), r"(?<!')\bbackgrounds?\b(?!')"),
    Term("Species", "species",
         (("Раса", r"раса|расат"), ("Species (English, old)", r"(?<![('])\bspecies\b(?![)'])"), ("вид (as species, old)", r"вида \(species\)|на вида")),
         ("Раса", "Вид", "Species (keep English)"),
         "Раса, or Вид if you want to follow the 2024 rename.",
         "The 2024 PHB renamed Race to Species. The glossary and the sheet said Раса; the step bar and species page kept the "
         "English word (LEGACY); the ruleset-help sentences said 'вида (species)'. 'Вид' also means 'kind/type' (вид оръжие, вид щети), "
         "so it is the riskiest of the three.",
         "DONE: Раса (Species) replaces the English labels and 'вида (species)' (Раса chosen, not Вид: 'вид' also means "
         "kind/type).",
         ((r"\bраса\b|\bрасата\b", r"species"),), r"(?<!')\bspecies\b(?!')|вида \(|на вида"),
    Term("Short Rest / Long Rest", "shortRest",
         (("кратка почивка", r"кратка почивка"), ("дълга почивка", r"дълга почивка")),
         ("кратка / дълга почивка (as now)", "кратък / дълъг отдих", "Short Rest / Long Rest (keep English)"),
         "Keep as now.",
         "Consistent. 'Rest' is lower case in running text and capitalised in headings only where the glossary asks for it.",
         "DONE (wording kept, brackets added): кратка почивка (Short Rest), дълга почивка (Long Rest); 'short or long' is "
         "'кратка почивка (Short Rest) или дълга почивка (Long Rest)'. In a resource line the bracketed word is joined with a "
         "comma instead of a second pair of parentheses.",
         ((r"(кратка|дълга) почивка", r"rest"),), None),
    Term("Weapon Mastery", "weaponMastery",
         (("Майсторство с оръжия", r"майсторство с оръжия"), ("Майсторство със заклинания", r"майсторство със заклинания")),
         ("Майсторство с оръжия", "Weapon Mastery (keep English)", "Оръжейно майсторство"),
         "Keep Майсторство с оръжия.",
         "Consistent. The same word is used for 'Spell Mastery' (Wizard level 18); fine, but keep it away from 'Expertise' and "
         "'Proficiency'.",
         "DONE (wording kept, brackets added): Майсторство с оръжия (Weapon Mastery), Майсторство със заклинания (Spell "
         "Mastery). The short 'майсторство' (a weapon's mastery property, the attack-table column) has no brackets.",
         ((r"майсторство с оръжия|майсторство със заклинания", r"mastery"),), None),
    Term("Advantage / Disadvantage", None,
         (("недостатък", r"недостатък"), ("disadvantage (English, old)", r"(?<!\()\bdisadvantage\b(?!\))")),
         ("предимство / недостатък", "Advantage / Disadvantage (keep English)", "предимство / пречка"),
         "предимство / недостатък.",
         "The Bulgarian word for Advantage ('предимство') is not used anywhere yet. 'недостатък' is used in a message, the export and "
         "the UI, and one LEGACY UI text still said 'disadvantage' in English.",
         "DONE: недостатък (Disadvantage); the English UI text 'armor: disadvantage on Stealth' is now 'броня: недостатък "
         "(Disadvantage) при Скритост'. 'предимство (Advantage)' is the form for any future text (no text uses it yet).",
         ((r"недостатък|предимство", r"disadvantage|advantage"),), r"\bdisadvantage\b"),
    Term("Bonus Action", None,
         (("бонус действие", r"бонус действие"),),
         ("бонус действие", "допълнително действие", "Bonus Action (keep English)"),
         "бонус действие.",
         "Consistent where it appears.",
         "DONE (wording kept, brackets added): бонус действие (Bonus Action).",
         ((r"бонус действие", r"bonus action"),), None),
    Term("Fighting Style / Metamagic / Maneuvers / Eldritch Invocation (class option names)", None,
         (("Fighting Style", r"fighting style"), ("Eldritch / Metamagic / Maneuver", r"eldritch|metamagic|maneuver"),
          ("Mystic Arcanum", r"mystic arcanum")),
         ("Keep English (data names)", "Боен стил / Метамагия / Маневри / Мистични инвокации", "English name with a Bulgarian gloss"),
         "Keep English.",
         "These are names the class data prints in English in both languages. Translating them only inside messages would make "
         "the message and the card disagree.",
         "DONE (kept English, no brackets): Fighting Style, Metamagic, Maneuvers, Eldritch Invocation, Mystic Arcanum in the "
         "messages. Left as they were, outside this row: the Bulgarian words 'метамагия:' (resource line), 'Мистичен арканум' "
         "(sheet / export heading) and 'Книга на сенките'.",
         (), None),
    Term("Ability / Ability Score", "abilityScores",
         (("Характеристики", r"характеристик"), ("Модификатор / Бонус (columns)", r"модификатор|бонус(?!\w)")),
         ("Характеристики", "Показатели", "Ability Scores (keep English)"),
         "Keep Характеристики.",
         "Consistent. The ability NAMES in messages stay as 'Intelligence, Wisdom, Charisma' or the codes STR / DEX; a decision on "
         "their Bulgarian form would be a separate row.",
         "DONE (wording kept, brackets added): Характеристики (Ability Scores), Характеристика (Ability Score) in sentences, "
         "Характеристика (Ability) as a table column; 'проверки на характеристики (Ability Checks)'. 'Физически "
         "характеристики' (physical characteristics) is not this term and has no brackets.",
         ((r"характеристик", r"ability"),), None),
    Term("Carrying Capacity", "carryingCapacity",
         (("Носимост", r"носимост"), ("Претоварен", r"претоварен")),
         ("Носимост", "Товароносимост", "Carrying Capacity (keep English)"),
         "Keep Носимост.",
         "Consistent; 'Товароносимост' is the dictionary word if the owner prefers it.",
         "DONE (wording kept, brackets added): Носимост (Carrying Capacity).",
         ((r"носимост", r"carrying capacity"),), None),
    Term("Special Senses (Darkvision, Blindsight ...)", "senses",
         (("Сетива", r"сетива"), ("тъмно / сляпо / истинско зрение", r"(тъмно|сляпо|истинско|дяволско) зрение"),
          ("усещане за вибрации", r"вибрации")),
         ("as now", "Darkvision / Blindsight (keep English)", "Тъмно зрение (capitalised)"),
         "Keep as now.",
         "Consistent; the sense names are lower case in running text and the glossary has them that way.",
         "DONE (wording kept, brackets added): Сетива (Senses), тъмно зрение (Darkvision), сляпо зрение (Blindsight), усещане "
         "за вибрации (Tremorsense), истинско зрение (Truesight), дяволско зрение (Devil's Sight).",
         ((r"сетива|(тъмно|сляпо|истинско|дяволско) зрение|усещане за вибрации", r"senses|darkvision|blindsight|truesight|devil|tremorsense"),), None),
)

# (row English term, "<surface>:<key>") -> reason. A text that has the Bulgarian noun but no bracket for it, on purpose.
COVERAGE_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("Ability / Ability Score", "UI:sheet.details.sections.physical"): "'Физически характеристики' = physical characteristics (height, weight ...), not the Ability Scores",
    ("Ability / Ability Score", "exp:detailSections.physical"): "same: physical characteristics of the character details",
}


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


_BRACKET = re.compile(r"\(([^()]*)\)")


def _brackets(text: str) -> str:
    """The text of all bracket groups of `text`, joined (what the English term must be found in)."""
    return " | ".join(_BRACKET.findall(text))


def coverage_gaps(corpus=None) -> list[tuple[str, str, str]]:
    """(row, "<surface>:<key>", noun) for every Bulgarian text that holds a term noun without its English bracket and is not
    an entry of COVERAGE_EXCEPTIONS."""
    corpus = _corpus() if corpus is None else corpus
    gaps = []
    for t in TERMS:
        for noun, bracket in t.checks:
            nrx, brx = re.compile(noun, re.IGNORECASE), re.compile(bracket, re.IGNORECASE)
            for surface, key, text in corpus:
                m = nrx.search(text)
                if m and not brx.search(_brackets(text)) and (t.en, f"{surface}:{key}") not in COVERAGE_EXCEPTIONS:
                    gaps.append((t.en, f"{surface}:{key}", m.group(0)))
    return gaps


def forbidden_hits(corpus=None) -> list[tuple[str, str, str]]:
    """(row, "<surface>:<key>", match) for every text that still holds the OLD wording of a row (outside brackets)."""
    corpus = _corpus() if corpus is None else corpus
    hits = []
    for t in TERMS:
        if not t.forbid:
            continue
        rx = re.compile(t.forbid, re.IGNORECASE)
        for surface, key, text in corpus:
            m = rx.search(_BRACKET.sub("", text))
            if m:
                hits.append((t.en, f"{surface}:{key}", m.group(0)))
    return hits


def render() -> str:
    corpus = _corpus()
    lines = [
        "# Terms: the owner's decisions (T1)",
        "",
        "<!-- GENERATED by `cd server && ../.venv/bin/python -m i18n.terms_table`. Do not edit; change `TERMS` in "
        "server/i18n/terms_table.py and regenerate. `--check` exits 1 when this file is stale. -->",
        "",
        "History: this file began (2026-11-05) as a proposal for the project owner. **The owner accepted the recommendation of "
        "every row** and decided that **a Bulgarian rules term is followed by the English term in brackets, everywhere it is "
        "used as a term** (web UI, server messages, export labels, glossary): `Талант (Feat)`, `кратка почивка (Short Rest)`. "
        "Verbs and connecting words have no brackets (`вече се владее`, `изричам`); inside one message the brackets are added at "
        "the first occurrence of a term. Where the proposal says to keep the English word (`Spell Slots`, `Fighting Style` ...) "
        "the term stays English with no brackets. English text is unchanged. The **Decision** column says what was done "
        "(DONE) and the final wording; the other columns are the proposal as it was written, with the counts recomputed from the "
        "app as it is now (an `(old)` wording should count 0).",
        "",
        "How to read it: **English term** is the 2024 Player's Handbook wording (the glossary id in brackets when the term is "
        "one). **BG wordings now** are the Bulgarian words found in the app with how many texts use them: `UI` = web "
        "app texts, `msg` = server messages (problems, warnings, pruned and disabled reasons, card labels), `exp` = Markdown "
        "and PDF export labels, `gloss` = the glossary. A count is the number of texts that contain the wording. **Where "
        "used** adds a few example keys. Names of game content (classes, species, feats, spells, items, skills) stay English "
        "in both languages and are not in this table. Tests (`server/tests/test_terms_table.py`, `test_t1_brackets.py`) check "
        "that every Bulgarian text with a term noun holds its bracket and that no old wording is left.",
        "",
        "| # | English term | Where used (examples) | BG wordings now (texts) | BG options | Recommendation (accepted) | Notes | Decision |",
        "|---|---|---|---|---|---|---|---|",
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
            f"{_cell('<br>'.join(f'{i}. {o}' for i, o in enumerate(t.options, 1)))} | {_cell(t.recommend)} | {_cell(t.notes)} | "
            f"{_cell(t.decision)} |"
        )
    lines += ["", f"{len(TERMS)} terms. All DONE. Source of the wordings: `docs/I18N-REVIEW.md`, `KNOWN_INCONSISTENCIES` in "
                  "`server/tests/test_i18n_completeness.py`, `server/i18n/glossary.json`, `frontend/src/copy/bg.ts`, the server "
                  "catalogs and `server/export_labels.py`. English brackets: `server/i18n/bracket_terms.py`.", ""]
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
