"""R1: the vocabulary review sheet for the project owner (a Bulgarian speaker): `docs/I18N-SHEET.xlsx` and `docs/I18N-SHEET.csv`.

One row per text that is translated, or deliberately left untranslated, in the whole app. The owner opens the xlsx, fills
the `Решение` dropdown (`Остава` / `Променя се` / `?`) and, for a change, the `Нова версия` column, and returns the file.
Layers (`Слой`):

* Интерфейс        the web UI copy (`frontend/src/copy/bg.ts` + `en.ts`); a template is shown with example arguments filled in
* Съобщение        the server catalogs (problems, warnings, pruned, disabled, labels), rendered in Bulgarian with sample params
* Експорт          the Markdown / PDF labels (`server/export_labels.py`), shown as the line would appear in the export
* Речник           the rules terms (`server/i18n/glossary.json`), each with a sentence from the app
* Имена            one summary row for each random-name list (`frontend/src/names/bgNames.ts`)
* Не се превежда   what stays English on purpose, and why

The CSV is the DETERMINISTIC companion (sorted, no timestamps, UTF-8 with BOM) and is stdlib only: the test suite runs
`--check` on it. The xlsx needs `openpyxl`, which is NOT a project dependency: run the xlsx step from a throwaway
virtualenv outside the repo (see the README, "Review sheet"). Rendering the UI templates needs `node` (the templates are
TypeScript functions); the sheet is built from the SOURCE files, nothing is read from a running app.

    cd server && ../.venv/bin/python -m i18n.review_sheet --csv-only      # rewrite docs/I18N-SHEET.csv (stdlib only)
    cd server && <venv with openpyxl>/bin/python -m i18n.review_sheet     # rewrite docs/I18N-SHEET.csv and docs/I18N-SHEET.xlsx
    cd server && ../.venv/bin/python -m i18n.review_sheet --check         # exit 1 when the CSV is stale (the suite runs this)

What is written by hand here: the sample parameters of the server messages (`MESSAGE_SAMPLES`), the example lines of the
export labels (`EXPORT_LINES`), where each UI text appears (`UI_WHERE`), the "does not translate" rows (`UNTRANSLATED`) and
the notes. Every text itself is read from where it lives, so the sheet cannot drift from the code.
"""
from __future__ import annotations

import csv
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys

from i18n import glossary as glossary_mod
from i18n import review_table
from i18n.bracket_terms import BRACKET_TERMS
from i18n.catalog import MESSAGES, disabled, labels, problems, pruned, warnings
from i18n.messages import msg, render
from i18n.ts_copy import COPY_DIR, Leaf, flatten, parse_catalog

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DOCS = REPO / "docs"
OUT_CSV = DOCS / "I18N-SHEET.csv"
OUT_XLSX = DOCS / "I18N-SHEET.xlsx"
NAMES_TS = REPO / "frontend" / "src" / "names" / "bgNames.ts"

HEADERS = ["№", "Слой", "Ключ", "Английски", "Български", "Пример в изречение", "Състояние", "Решение", "Нова версия", "Бележка"]
LAYERS = ["Интерфейс", "Съобщение", "Експорт", "Речник", "Имена", "Не се превежда"]
STATES = ["преведено", "преведено + английско в скоби", "остава английско (решено)", "изключение"]
DECISIONS = ["Остава", "Променя се", "?"]

# ---------------------------------------------------------------------------------------------------------------------
# helpers

_CYR = re.compile("[Ѐ-ӿ]")
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")
_BRACKET = re.compile(r"\([^()]*\)")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’]+")
# Latin tokens that are abbreviations / units / codes, not English words that were left untranslated.
_ABBREVIATIONS = {"AC", "DC", "HP", "CR", "SP", "GP", "lb", "ft", "STR", "DEX", "CON", "INT", "WIS", "CHA", "JSON", "PDF", "MB",
                  "SRD", "BG", "EN", "YAML", "HTTP", "API", "ID", "bg", "en", "GB", "NPC"}


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _english_words(bg: str) -> list[str]:
    """Latin words of a Bulgarian text outside brackets and placeholders (abbreviations excepted)."""
    text = _BRACKET.sub(" ", _PLACEHOLDER.sub(" ", bg))
    return [w for w in _LATIN_WORD.findall(text) if w not in _ABBREVIATIONS and not re.fullmatch(r"d\d+", w)]


def _has_brackets_term(bg: str) -> bool:
    for inner in re.findall(r"\(([^()]*)\)", bg):
        if any(p.strip() in BRACKET_TERMS for p in inner.split(",")):
            return True
    return False


def classify(en: str, bg: str) -> tuple[str, str]:
    """(state, extra note) of one Bulgarian text."""
    english = _english_words(bg)
    cyr = bool(_CYR.search(bg))
    if cyr:
        if english:
            return "изключение", "Българският текст съдържа английски думи извън скоби: " + ", ".join(dict.fromkeys(english)) + "."
        if _has_brackets_term(bg):
            return "преведено + английско в скоби", ""
        return "преведено", ""
    if english:
        return "остава английско (решено)", ""
    return "преведено", ""  # only symbols, numbers, placeholders


def _quote(text: str) -> str:
    return "„" + text + "“"


# ---------------------------------------------------------------------------------------------------------------------
# notes: uncertain items of docs/I18N-REVIEW.md and the awkward lengths of T1

_FLAG_SOURCES = {"I0": "речника", "I2": "проблеми и предупреждения", "I3": "отпаднали избори", "I4": "причини за недостъпна опция",
                 "I5": "карти за избор", "XL": "експортите", "SK6-BI": "интерфейса", "N1": "имената", "N2": "имената", "C1": "проверката за еднаквост"}


def _flag_notes() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for kind, ref, source, why in review_table.FLAGS:
        out[(kind, ref)] = f"Съмнение от docs/I18N-REVIEW.md ({source}): {why}"
    return out


# Bulgarian texts that became long when the English term was put in brackets (T1, "Awkward lengths" in ARCHITECTURE).
AWKWARD = (
    "Произход (Background)", "Раса (Species)", "Характеристика (Ability)", "Владеене (Proficiency)", "Умение (Skill)",
    "експертиза (Expertise)", "Устойчивост (Resistance) и имунитети (Immunities)",
    "Увеличение на характеристики (Ability Score Improvement)", "Бонус за атака със заклинание (Spell Attack Modifier)",
    "DC на спасяването от заклинание (Spell Save DC)", "Магическа характеристика (Spellcasting Ability)",
    "Зарове за точки живот (Hit Point Dice)", "Способности на класа (Class Features)", "Бонус за владеене (Proficiency Bonus)",
    "усещане за вибрации (Tremorsense)", "кратка почивка (Short Rest) или дълга почивка (Long Rest)",
)


def _awkward_note(bg: str) -> str:
    if bg in AWKWARD:
        return (f"Дълго заради скобите (T1): {len(bg)} знака. На телефон и в тясна колона на таблица може да е неудобно; "
                "реши дали да остане с термина в скоби или да има по-кратка форма.")
    return ""


# ---------------------------------------------------------------------------------------------------------------------
# layer: Интерфейс (frontend/src/copy)

# Where each group of UI texts appears. Key: the dotted path of the group (the key without its last segment); the longest
# prefix wins. A group not listed falls back to its parent.
UI_WHERE: dict[str, str] = {
    "": "Горна лента на приложението",
    "lang": "Горна лента, превключвател на езика БГ / EN",
    "nav": "Лентата със стъпки под горната лента",
    "nav.steps": "Лентата със стъпки, име на стъпка",
    "titles": "Заглавие на раздела в браузъра",
    "titles.pages": "Заглавие на раздела в браузъра за страница",
    "common": "Общи думи по много страници",
    "status": "Лента със състояние над страницата (грешки, предупреждения, запис)",
    "errorBoundary": "Екран при неочаквана грешка в приложението",
    "home": "Страница „Home“",
    "home.rulesetHelp": "Страница „Home“, помощен текст под избора на правила",
    "classPage": "Страница „Клас“",
    "backgroundPage": "Страница „Произход (Background)“",
    "backgroundPage.alignments": "Страница „Произход (Background)“, подсказка за мирогледа на произхода",
    "speciesPage": "Страница „Раса (Species)“",
    "abilitiesPage": "Страница „Abilities“",
    "abilitiesPage.methods": "Страница „Abilities“, избор на начин за определяне на характеристиките",
    "abilitiesPage.columns": "Страница „Abilities“, таблица с характеристиките",
    "equipmentPage": "Страница „Equipment“",
    "equipmentPage.categories": "Страница „Equipment“, филтър за категория предмет",
    "choice": "Карта за избор (клас, произход, раса, таланти) на страниците",
    "choice.groups": "Карта за избор, заглавие на група опции",
    "spellLibrary": "Списък със заклинания в картата за избор",
    "spellLibrary.filters": "Списък със заклинания, филтър по ниво",
    "traits": "Раса, ред със сетиво",
    "slots": "Клетки за заклинания на страница „Клас“",
    "sheet": "Страница „Лист на героя“",
    "sheet.markers": "Лист, до умение или спасително хвърляне",
    "sheet.identity": "Лист, секция „Герой“",
    "sheet.abilities": "Лист, секция „Характеристики“",
    "sheet.abilities.columns": "Лист, таблица „Характеристики“",
    "sheet.proficiencyBonus": "Лист, секция „Бонус за владеене“",
    "sheet.armorClass": "Лист, секция „Клас броня“",
    "sheet.hitPoints": "Лист, секция „Точки живот“",
    "sheet.initiative": "Лист, секция „Инициатива“",
    "sheet.speeds": "Лист, секция „Скорост“",
    "sheet.speeds.modes": "Лист, секция „Скорост“, вид движение",
    "sheet.senses": "Лист, секция „Сетива“",
    "sheet.senses.kinds": "Лист, секция „Сетива“, вид сетиво",
    "sheet.passives": "Лист, секция „Пасивни стойности“",
    "sheet.savingThrows": "Лист, секция „Спасителни хвърляния“",
    "sheet.savingThrows.columns": "Лист, таблица „Спасителни хвърляния“",
    "sheet.skills": "Лист, секция „Умения“",
    "sheet.skills.columns": "Лист, таблица „Умения“",
    "sheet.proficiencies": "Лист, секция „Владеене“",
    "sheet.languages": "Лист, секция „Езици“",
    "sheet.attacks": "Лист, секция „Атаки“",
    "sheet.attacks.columns": "Лист, таблица „Атаки“",
    "sheet.resources": "Лист, секция „Ресурси“",
    "sheet.resources.text": "Лист, ред на ресурс (части от реда)",
    "sheet.resources.text.recharge": "Лист, ред на ресурс, кога се възстановява",
    "sheet.resources.text.damageTypes": "Лист, ред на ресурс, вид щета",
    "sheet.features": "Лист, секция „Способности на класа“",
    "sheet.feats": "Лист, секция „Таланти“",
    "sheet.spells": "Лист, секция „Заклинания“",
    "sheet.innateSpells": "Лист, секция „Вродени заклинания“",
    "sheet.equipment": "Лист, секция „Екипировка“",
    "sheet.equipment.groups": "Лист, секция „Екипировка“, група предмети",
    "sheet.carryingCapacity": "Лист, секция „Носимост“",
    "sheet.defenses": "Лист, секция „Устойчивост и имунитети“",
    "sheet.details": "Лист, секция „Данни за героя“",
    "sheet.details.sections": "Лист, „Данни за героя“, заглавие на раздел",
    "sheet.details.fields": "Лист, „Данни за героя“, етикет на поле",
    "exportPage": "Страница „Export“",
    "exportPage.missing": "Страница „Export“, какво още липсва преди експорта",
    "library": "Списък с герои",
    "msg": "Съобщение за грешка или състояние (червена или жълта лента)",
    "msg.http": "Съобщение за грешка при заявка към сървъра",
    "msg.net": "Съобщение за липса на връзка",
    "msg.catalog": "Съобщение при зареждане на каталога",
    "msg.items": "Съобщение при зареждане на предметите",
    "msg.spells": "Съобщение при зареждане на заклинанията",
    "msg.spell": "Съобщение при зареждане на заклинание",
    "msg.export": "Съобщение при експорт",
    "msg.file": "Съобщение при качване на файл",
    "msg.draft": "Съобщение при качване на чернова",
    "msg.lib": "Съобщение за запазените герои в браузъра",
}

_BUTTONS = {"retry", "remove", "print", "exportLink", "downloadOld", "copyText", "dismiss", "download", "reset", "randomName", "open",
            "rename", "duplicate", "delete", "newHero", "downloadAll", "upload", "downloadOne", "hide", "clearPruned", "addClass",
            "rollAll", "hideUnavailable", "showUnavailable", "seeInHome", "nextStep", "sheetLink", "add", "setWornManually",
            "setWieldedManually", "choose"}


def _ui_where(path: str) -> str:
    group = path.rsplit(".", 1)[0] if "." in path else ""
    parts = group.split(".") if group else []
    while True:
        key = ".".join(parts)
        if key in UI_WHERE:
            return UI_WHERE[key]
        if not parts:
            return "Приложението"
        parts.pop()


def _ui_element(path: str) -> str:
    leaf = path.rsplit(".", 1)[-1]
    group = path.rsplit(".", 1)[0] if "." in path else ""
    if group.endswith("columns"):
        return "Заглавие на колона"
    if leaf == "title" or leaf.endswith("Title"):
        return "Заглавие на секция"
    if leaf in _BUTTONS or leaf.startswith(("download", "upload")):
        return "Бутон или връзка"
    if leaf.endswith("Label"):
        return "Етикет на поле (чете се и от екранен четец)"
    if leaf.endswith("Placeholder"):
        return "Подсказка в празно поле"
    if group.endswith(("modes", "kinds", "damageTypes", "recharge", "methods", "categories", "alignments", "filters", "groups")):
        return "Стойност от списък"
    if group.startswith(("msg", "status")) or leaf in ("loadError", "errorLine", "calcError"):
        return "Текст на съобщение"
    if leaf.endswith(("Note", "Hint", "Help")) or leaf in ("hint", "nameHint"):
        return "Поясняващ текст"
    return "Текст"


# A typical value printed next to a label, so the example reads as a real line of the page. Key: UI path.
UI_VALUES: dict[str, str] = {
    "sheet.identity.name": "Тордек", "sheet.identity.level": "5", "sheet.identity.classes": "Fighter 5 (Champion)",
    "sheet.identity.species": "Dwarf (Hill Dwarf)", "sheet.identity.size": "Medium", "sheet.identity.background": "Soldier",
    "sheet.hitPoints.max": "44", "sheet.proficiencyBonus.title": "+3", "sheet.armorClass.title": "18",
    "sheet.hitPoints.title": "44 (5d10)", "sheet.initiative.title": "+1", "sheet.speeds.title": "30 фута",
    "sheet.passives.perception": "13", "sheet.passives.insight": "11", "sheet.passives.investigation": "9",
    "sheet.attacks.perAction": "2", "sheet.carryingCapacity.carried": "96", "sheet.carryingCapacity.capacity": "225",
    "sheet.spells.ability": "Intelligence", "sheet.spells.saveDC": "14", "sheet.spells.attackBonus": "+6",
    "sheet.details.fields.alignment": "Законен добър", "sheet.details.fields.age": "42", "sheet.details.fields.height": "1,32 м",
    "sheet.details.fields.weight": "75 кг", "sheet.details.fields.eyes": "кафяви", "sheet.details.fields.hair": "черна",
    "sheet.details.fields.skin": "мургава", "sheet.details.fields.faith": "Мoradin", "sheet.details.fields.lifestyle": "Skilled",
    "home.nameLabel": "Тордек", "classPage.level": "5", "classPage.subclass": "Champion", "classPage.hitPoints": "d10",
    "abilitiesPage.title": "", "speciesPage.subspecies": "Hill Dwarf", "equipmentPage.categoryLabel": "Оръжия",
    "sheet.skills.otherExpertise": "Stealth",
}

# Example arguments of the UI templates (by parameter name); `UI_ARGS` overrides one template by its path.
_ARG_BY_NAME = {
    "n": 3, "count": 2, "level": 3, "selected": 2, "available": 12, "hidden": 3, "detail": "HTTP 503", "name": "Longsword",
    "subclass": "Champion", "dice": "1d8", "type": "slashing", "ability": "Strength", "added": 2, "rejected": 1, "when": "преди 5 мин.",
    "names": "Тордек, Лира", "classes": "Fighter 5, Wizard 2", "total": 7, "max": 20, "die": 10, "list": "Rage, Frenzy",
    "label": "Скрити способности", "format": "PDF", "range": "80/320", "mastery": "Sap", "carried": 96, "capacity": 225,
    "pushDragLift": 450, "dice2": "1d10", "uses": "1/дълга почивка", "h": "2d6", "cr": "1/2", "types": "fire, cold",
    "points": 3, "subspecies": "Hill Dwarf", "variant": "Dragonborn", "classLine": "Fighter 5", "p": None, "range2": "5",
    "feet": 60, "selectedN": 2, "classLevel": 5,
}
_P_KEYS = {"text": "Не всички части са избрани", "status": 503, "base": "Сървърът върна грешка 500.", "detail": "HTTP 500",
           "name": "Тордек", "why": "Данните са повредени.", "key": "dnd-builder-draft-v2:abc", "saved": "Старият текст е запазен в браузъра. ",
           "recovered": " Героите са възстановени.", "max": 200}
UI_ARGS: dict[str, list] = {
    "common.feet": [1], "common.pounds": [96], "common.gold": [150], "common.level": [5], "common.levelOf": [3],
    "sheet.incomplete": [3], "sheet.identity.classLine": ["Fighter", 5, "Champion"],
    "sheet.identity.speciesLine": ["Dwarf", "Hill Dwarf", None], "sheet.attacks.damage": ["1d8", "slashing"],
    "sheet.resources.text.pool": [10], "sheet.resources.text.bonus": [2], "sheet.resources.text.dc": [14],
    "sheet.resources.text.damageBonus": [2], "sheet.resources.text.heal": ["1d8+3"], "sheet.resources.text.maxCr": ["1/2"],
    "sheet.resources.text.resistances": [["fire", "cold"]], "sheet.resources.text.shortRestRegains": [2],
    "sheet.resources.text.maxSlotLevel": [5], "sheet.resources.text.slotCost": ["2", 3],
    "sheet.resources.text.damageTypesLine": ["огнени, студени"], "sheet.resources.text.knownForms": [4],
    "sheet.resources.text.metamagic": ["Quickened Spell, Twinned Spell"],
    "sheet.resources.text.perRageOptions": ["Bear, Eagle, Wolf"],
    "sheet.features.level": [3], "sheet.feats.level": [4], "sheet.spells.slotLine": [1, 4], "sheet.spells.spellLine": ["Fireball", 3],
    "sheet.innateSpells.line": ["Misty Step", "1/дълга почивка", 3], "sheet.equipment.quantity": [20],
    "nav.unresolved": [3], "nav.newChoices": [2], "status.pruned": [2], "classPage.hitDieLabel": ["Fighter", 10],
    "classPage.levelN": [3], "classPage.levelCap": [20], "home.itemSummary": ["Fighter 5, Wizard 2", 7],
    "home.sourcesSummary": [4], "choice.levelBadge": [3], "choice.counter": [1, 2], "choice.granted": ["Light Armor, Medium Armor"],
    "choice.spellLevelGroup": ["3"], "choice.showUnavailable": [5], "choice.selectedCount": [1, 2], "choice.unlabelled": [4],
    "choice.found": [12, 3], "choice.groupSummary": [12, 3, 1], "spellLibrary.levelBadge": [3], "traits.senseLine": ["тъмно зрение (Darkvision)", 60],
    "slots.line": [1, 4], "slots.pactLine": [2, 3], "library.copyName": ["Тордек"], "exportPage.attacksPerAction": [2],
    "exportPage.attackDamage": ["1d8", "slashing"], "exportPage.carrying": [96, 225, 450], "exportPage.pendingEquipment": [2],
    "exportPage.download": ["PDF"], "home.importSummary": [2, 1], "home.importIndex": [3], "home.exportedSkipped": ["Тордек, Лира"],
    "home.deleteConfirm": ["Тордек"], "home.updated": ["преди 5 мин."], "equipmentPage.contains": ["Backpack, Bedroll, Rations"],
    "equipmentPage.addLabel": ["Longsword"], "equipmentPage.removeLabel": ["Longsword"], "choice.removeLabel": ["Athletics"],
    "choice.searchLabel": ["Умения (Skills)"], "choice.sourceLabel": ["PHB"], "abilitiesPage.pointsRemaining": [7],
    "abilitiesPage.valueLabel": ["Strength"], "abilitiesPage.decreaseLabel": ["Strength"], "abilitiesPage.increaseLabel": ["Strength"],
    "errorBoundary.body": ["Cannot read properties of undefined"], "status.calcError": ["HTTP 503"], "classPage.loadError": ["HTTP 503"],
    "common.loadError": ["HTTP 503"], "common.errorLine": ["HTTP 503"],
    "msg.raw": [{"text": "Черновата не може да се запази."}],
}
_NODE_RENDER = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const g = input.g;
const out = input.items.map((it) => {
  try { const f = new Function('g', 'return (' + it.src + ')')(g); return String(f(...it.args)); }
  catch (e) { return 'ERROR ' + e.message; }
});
process.stdout.write(JSON.stringify(out));
"""


def _strip_ts_params(src: str) -> str:
    """`(a: number, b: string | null) =>` -> `(a, b) =>`; a method shorthand `(a: T) { ... }` is left as an arrow too."""
    m = re.match(r"\s*(async\s+)?\(([^)]*)\)\s*(:\s*[^=]+)?=>", src, re.S)
    if m:
        params = ", ".join(p.split(":")[0].strip() for p in _split_params(m.group(2)) if p.strip())
        return f"({params}) =>" + src[m.end():]
    m = re.match(r"\s*\(([^)]*)\)\s*\{", src, re.S)
    if m:
        params = ", ".join(p.split(":")[0].strip() for p in _split_params(m.group(1)) if p.strip())
        return f"function({params}) {{" + src[m.end():]
    return src


def _split_params(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def _fn_params(src: str) -> list[str]:
    m = re.match(r"\s*(async\s+)?\(([^)]*)\)", src, re.S)
    return [p.split(":")[0].strip() for p in _split_params(m.group(2)) if p.strip()] if m else []


def _default_args(path: str, src: str) -> list:
    if path in UI_ARGS:
        return UI_ARGS[path]
    args = []
    for name in _fn_params(src):
        if name == "p":
            keys = re.findall(r"p\.(\w+)", src)
            args.append({k: _P_KEYS.get(k, "…") for k in dict.fromkeys(keys)})
        else:
            args.append(_ARG_BY_NAME.get(name, 3))
    return args


def _g_object(gloss: dict) -> dict:
    return {tid: {"en": t["en"], "bg": t["bg"]} for tid, t in gloss.items()}


def render_templates(items: list[dict], gloss: dict) -> list[str]:
    """Run the TypeScript arrow functions of the copy catalog in node with example arguments. [{src, args}] -> [text]."""
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("node is needed to fill in the UI templates of the review sheet (the templates are TypeScript functions)")
    payload = {"g": _g_object(gloss), "items": [{"src": _strip_ts_params(i["src"]), "args": i["args"]} for i in items]}
    done = subprocess.run([node, "-e", _NODE_RENDER], input=json.dumps(payload), capture_output=True, text=True, check=True)
    result = json.loads(done.stdout)
    bad = [(i["path"], r) for i, r in zip(items, result) if r.startswith("ERROR")]
    if bad:
        raise RuntimeError(f"UI template did not render with the sample arguments: {bad}")
    return result


def _copy_value(leaf: Leaf, gloss: dict) -> str:
    text = re.sub(r"\$\{g\.(\w+)\.(en|bg)\}", lambda m: gloss[m.group(1)][m.group(2)], leaf.text)
    whole = re.fullmatch(r"g\.(\w+)\.(en|bg)", text)
    return gloss[whole.group(1)][whole.group(2)] if whole else text


_PAGE_ORDER = ["appName", "lang", "nav", "titles", "common", "status", "errorBoundary", "home", "classPage", "backgroundPage",
               "speciesPage", "abilitiesPage", "equipmentPage", "choice", "spellLibrary", "traits", "slots", "sheet", "exportPage",
               "library", "msg"]

# Why a UI text stays English (by the text itself).
_UI_ENGLISH_REASONS: dict[str, str] = {
    "Home": "Името на страницата е на английски от самото начало (LEGACY списъкът от SK6-BI); превеждането е решение, което още не е взето.",
    "Abilities": "Името на страницата е на английски от самото начало (LEGACY); в речника на българския е „Характеристики (Ability Scores)“.",
    "Equipment": "Името на страницата е на английски от самото начало (LEGACY); в речника на българския е „Екипировка“, а на листа и в експорта вече е на български.",
    "Export": "Името на страницата е на английски от самото начало (LEGACY); заглавието на раздела в браузъра е „Експорт“.",
    "Character Name": "Етикетът на полето за име е на английски от самото начало (LEGACY).",
    "Spell Slots": "Решение на собственика (2026-11-05): Spell Slots остава английски навсякъде, без скоби; не е „Клетки за заклинания“.",
    "Pact Magic Slots": "Решение на собственика (T1): остава английски като Spell Slots.",
}
_UI_ENGLISH_DEFAULT = ("Английски от самото начало в българския интерфейс (LEGACY списъкът от SK6-BI): думата е запазена както е била, "
                       "превеждането е осъзнато бъдещо решение.")


def _ui_rows(gloss: dict, flags: dict) -> tuple[list[dict], list[dict]]:
    """(rows of the layer Интерфейс, English-only UI rows that go to the layer Не се превежда)."""
    bg = flatten(parse_catalog(COPY_DIR / "bg.ts", "bg"))
    en = flatten(parse_catalog(COPY_DIR / "en.ts", "en"))
    assert set(bg) == set(en), "bg.ts and en.ts differ in shape"
    # render every template once, bg and en
    todo = []
    for path in bg:
        for lang, tree in (("bg", bg), ("en", en)):
            leaf = tree[path]
            if leaf.kind == "fn":
                src = leaf.text
                if lang == "en":
                    src = re.sub(r"\bg\.(\w+)\.(en|bg)\b", lambda m: json.dumps(gloss[m.group(1)][m.group(2)], ensure_ascii=False), src)
                todo.append({"path": path, "lang": lang, "src": src, "args": _default_args(path, bg[path].text)})
    rendered = dict(zip(((t["path"], t["lang"]) for t in todo), render_templates(todo, gloss)))

    def text(path: str, lang: str) -> str:
        leaf = (bg if lang == "bg" else en)[path]
        return rendered[(path, lang)] if leaf.kind == "fn" else _copy_value(leaf, gloss)

    def order(path: str) -> tuple[int, int]:
        top = path.split(".")[0]
        return (_PAGE_ORDER.index(top) if top in _PAGE_ORDER else len(_PAGE_ORDER), list(bg).index(path))

    groups: dict[tuple[str, str], dict] = {}
    for path in sorted(bg, key=order):
        e, b = text(path, "en"), text(path, "bg")
        item = groups.setdefault((e, b), {"paths": [], "en": e, "bg": b, "template": False})
        item["paths"].append(path)
        item["template"] = item["template"] or bg[path].kind == "fn"

    rows, english = [], []
    for (e, b), item in groups.items():
        paths = item["paths"]
        first = paths[0]
        state, extra = classify(e, b)
        if item["template"]:
            arg_words = set()
            for p in paths:
                arg_words |= set(_LATIN_WORD.findall(json.dumps(_default_args(p, bg[p].text) if bg[p].kind == "fn" else [], ensure_ascii=False)))
            own = [w for w in _english_words(b) if w not in arg_words]
            if not own:
                state, extra = ("преведено + английско в скоби" if _has_brackets_term(b) and _CYR.search(b) else "преведено"), ""
            elif _CYR.search(b):
                state, extra = "изключение", "Българският текст съдържа английски думи извън скоби: " + ", ".join(dict.fromkeys(own)) + "."
        notes = []
        for p in paths:
            if ("copy", p) in flags:
                notes.append(flags[("copy", p)])
        awkward = _awkward_note(b)
        if awkward:
            notes.append(awkward)
        if extra and state == "изключение":
            notes.append(extra)
        examples = []
        for p in paths[:3]:
            value = UI_VALUES.get(p)
            shown = _quote(text(p, "bg"))
            line = f"{_ui_where(p)} · {_ui_element(p).lower()}: {shown}"
            if value:
                line += f" → напр. {_quote(text(p, 'bg') + ': ' + value if not text(p, 'bg').endswith(':') else text(p, 'bg') + ' ' + value)}"
            examples.append(line)
        if len(paths) > 3:
            examples.append(f"(и още на {len(paths) - 3} места)")
        if item["template"]:
            examples = [x + "  [шаблон, попълнен с примерни стойности]" for x in examples[:1]] + examples[1:]
        row = {"layer": "Интерфейс", "key": "\n".join(f"copy:{p}" for p in paths), "en": e, "bg": b,
               "example": "\n".join(examples), "state": state, "note": " ".join(notes)}
        if not _CYR.search(b) and not re.search("[A-Za-z]", b):
            row.update(layer="Не се превежда", state="изключение",
                       note="Не е текст за превод: символ или код. " + ("Кодът на езика за датите." if b == "bg-BG" else ""))
            english.append(row)
        elif state == "остава английско (решено)":
            row.update(layer="Не се превежда", note=" ".join(filter(None, [_UI_ENGLISH_REASONS.get(b, _UI_ENGLISH_DEFAULT), *notes])))
            english.append(row)
        else:
            rows.append(row)
    return rows, english


# ---------------------------------------------------------------------------------------------------------------------
# layer: Съобщение (server/i18n/catalog)

_KIND_NAME = [(problems, "Проблем или предупреждение в черновата (лента над листа)"),
              (warnings, "Предупреждение за героя"),
              (pruned, "Отпаднал избор (показва се, когато запазен избор вече не важи)"),
              (disabled, "Причина под недостъпна опция"),
              (labels, "Етикет, описание или причина на карта за избор")]
_DEFAULT_PARAMS: dict = {
    "ab": "STR", "value": "abc", "n": 2, "count": 2, "cls": "Wizard", "id": "class:fighter:1:skills", "name": "Longsword",
    "names": ["Athletics", "Stealth"], "level": 5, "feat": "Alert", "source": "Fighter, ниво 4", "where": "Fighter, ниво 4",
    "label": None, "key": "abilities", "subclass": "Champion", "item": "longsword", "spent": 31, "total": 23, "cap": 20,
    "delta": 2, "applied": 1, "bonus": 2, "ruleset": "2012", "minimum": 15, "free": 1, "schools": ["Evocation", "Abjuration"],
    "school_a": "Evocation", "school_b": "Abjuration", "die": 8, "field": "qty", "kind": "worn", "slot": "armor", "category": "Heavy",
    "armor": "Heavy", "submitted": 4, "clamped": 30, "final": 32, "extra": 3, "m": 1, "rest": ["Shield", "Mage Armor"],
    "why": "вече е на максимума", "option": "Feat: Alert", "items": ["Strength", "Dexterity"], "parts": ["ниво 5", "Spellcasting"],
    "spell": "Eldritch Blast", "lang": "Elvish", "language": "Elvish", "list": "Wizard", "classes": ["Cleric", "Wizard"],
    "levels": [1, 2], "max": 3, "head": "Alert", "tail": None, "text": "Изберете заклинания.", "what": "Athletics, Stealth",
    "condition": " с време за изричане един час", "time": "1 минута", "score": 35, "subscript": None, "noun": None,
}


def _sample_msg(key: str, **params):
    return msg(key, **params)


def _message_params(key: str) -> dict:
    """Sample parameters of one catalog entry (realistic values; nested messages are real `Msg`s)."""
    base = dict(_DEFAULT_PARAMS)
    base["label"] = msg("label-skill-proficiencies")
    base["tail"] = msg("label-expertise")
    base["noun"] = msg("noun-cantrip", n=2)
    over = MESSAGE_SAMPLES.get(key, {})
    base.update(over)
    return base


MESSAGE_SAMPLES: dict[str, dict] = {
    "malformed-object": {"label": "equipment"}, "malformed-text": {"label": "name"},
    "malformed-selection-not-list": {"key": "class:fighter:1:skills"},
    "malformed-selection-entries": {"key": "class:fighter:1:skills"},
    "ability-invalid-whole": {"value": "dd"}, "ability-out-of-range-clamped": {"n": 42, "clamped": 30},
    "ability-out-of-range-clamped-final": {"n": 30, "clamped": 30, "final": 32},
    "ability-out-of-range": {"score": 42},
    "level-invalid-whole": {"value": "три"},
    "equipment-qty-invalid": {"value": -1, "item": "arrow"},
    "malformed-equipment-slot-object": {"key": "worn"}, "malformed-equipment-slot-type": {"key": "worn", "field": "armor"},
    "point-buy-over-budget": {"spent": 31}, "level-out-of-range": {"level": 25},
    "unknown-class": {"id": "wizzard"}, "unknown-subclass": {"id": "champon"}, "unknown-background": {"id": "soldiar"},
    "unknown-species": {"id": "dwarff"}, "unknown-subspecies": {"id": "hill-dwarff"},
    "subclass-mismatch": {"subclass": "Champion", "cls": "Wizard"}, "total-level-exceeded": {"total": 23},
    "subspecies-mismatch": {"name": "High Elf"},
    "multiclass-prerequisite-unmet": {"cls": "Paladin"},
    "feat-duplicate-at-source": {"feat": "Alert", "source": "Fighter, ниво 4"},
    "feat-duplicate-at-level": {"feat": "Alert", "cls": "Fighter", "level": 8},
    "feat-prerequisite-unmet-pick": {"feat": "Grappler", "source": "Fighter, ниво 4"},
    "feat-prerequisite-unmet": {"feat": "Grappler"}, "feat-prerequisite-unmet-at-level": {"feat": "Grappler", "cls": "Fighter", "level": 4},
    "subclass-spell-school-limit": {"n": 3, "free": 1},
    "over-selected": {"count": 2, "submitted": 4}, "unresolved-choice": {},
    "ruleset-invalid": {"ruleset": "2012"}, "ruleset-2014-background-asi-ignored": {"name": "Soldier"},
    "ruleset-2024-background-no-asi": {"name": "Acolyte (2014)"}, "ruleset-2024-background-no-origin-feat": {"name": "Sage (2014)"},
    "source-hidden": {"name": "Tasha's Cauldron of Everything"}, "feat-hidden-by-filters": {"feat": "Fey Touched"},
    "dark-gift-needs-ravenloft": {"feat": "Mist Walker"},
    "ability-final-above-20": {"ab": "CON", "value": 21, "base": 19},
    "equipment-unknown-item": {"item": "plate"},
    "ability-above-20": {"ab": "STR", "value": 22}, "hp-roll-invalid": {"cls": "Fighter", "level": 3, "die": 10},
    "equipment-envelope-dropped": {"name": "Fighter", "n": 1},
    "armor-not-proficient": {"name": "Plate Armor"}, "armor-strength": {"name": "Plate Armor", "minimum": 15},
    "fly-armor": {"name": "Aarakocra", "armor": msg("armor-category-medium-heavy")},
    "slot-unknown-item": {"kind": msg("slot-kind-worn"), "slot": msg("slot-armor"), "item": "plate-of-vigor"},
    "slot-not-in-inventory": {"name": "Shield", "kind": msg("slot-kind-wielded"), "slot": msg("slot-off")},
    "wielded-not-holdable": {"name": "Plate Armor"}, "wielded-main-shield": {"name": "Shield"},
    "wielded-same-item-twice": {"name": "Longsword"}, "wielded-two-handed-conflict": {"name": "Greatsword"},
    "worn-armor-not-body-armor": {"name": "Shield"}, "wielded-shield-not-worn": {"name": "Shield"},
    "pruned-language-replacement-lost": {"names": ["Dwarvish"], "lang": "Elvish"},
    "pruned-language-known": {"names": ["Elvish"], "label": msg("label-languages")},
    "pruned-proficient-source": {"names": ["Athletics"], "source": "Soldier"},
    "pruned-proficient-skill": {"names": ["Athletics"]}, "pruned-proficient": {"names": ["Longsword"], "label": msg("label-weapon-proficiencies")},
    "pruned-iron-mind": {"label": msg("label-saving-throw")}, "pruned-expertise-already": {"names": ["Stealth"], "label": msg("label-expertise")},
    "pruned-expertise-not-proficient": {"names": ["Stealth"], "label": msg("label-expertise")},
    "pruned-expertise-already-chosen": {"names": ["Stealth"], "label": msg("label-expertise")},
    "pruned-bard-known": {"names": ["Vicious Mockery"], "label": msg("label-cantrips")},
    "pruned-known-ignored": {"names": ["Fire Bolt"], "label": msg("label-cantrips")},
    "pruned-minor-illusion-required": {"label": msg("label-prefixed", head="Illusion Savant", tail=msg("label-spell"))},
    "pruned-invocation-prereq": {"names": ["Eldritch Smite"]},
    "pruned-invocation-dependent": {"label": msg("label-prefixed", head="Eldritch Spear", tail=msg("label-cantrip"))},
    "pruned-eldritch-adept-prereq": {"names": ["Armor of Shadows"]},
    "pruned-count-overflow": {"count": 2, "n": 2, "names": ["Athletics", "Stealth"], "id": "class:fighter:1:skills"},
    "pruned-wizard-not-in-spellbook": {"n": 2, "names": ["Fireball", "Shield"], "id": "class:wizard:1:prepared"},
    "pruned-wizard-not-in-spellbook-and-over": {"n": 2, "m": 1, "count": 6, "names": ["Fireball", "Shield"], "rest": ["Mage Armor"], "id": "class:wizard:1:prepared"},
    "pruned-stale": {"id": "class:wizard:9:subclass"}, "pruned-no-longer-available": {"names": ["Shield"], "label": msg("label-spells-known")},
    "pruned-no-longer-offered": {"names": ["Alert"], "label": msg("label-feat")}, "pruned-more": {"extra": 3},
    "pruned-distinct-duplicate": {"names": ["Athletics"], "name": "Soldier", "n": 2},
    "pruned-already-taken": {"names": ["Alert"], "where": "Fighter, ниво 4", "label": msg("label-feat")},
    "pruned-mastered-through-class": {"names": ["Longsword"], "label": msg("label-weapon-mastery")},
    "pruned-weapon-not-proficient": {"names": ["Longsword"], "label": msg("label-weapon-mastery")},
    "pruned-mastery-unavailable-class": {"names": ["Longsword"], "label": msg("label-weapon-mastery")},
    "pruned-mastery-unavailable-feat": {"names": ["Longsword"], "label": msg("label-weapon-mastery")},
    "pruned-ability-at-max": {"name": "Soldier", "ab": "STR", "cap": 20},
    "pruned-ability-at-max-delta": {"name": "Soldier", "ab": "STR", "cap": 20, "delta": 2},
    "pruned-ability-capped": {"name": "Soldier", "ab": "STR", "cap": 20, "applied": 1, "bonus": 2},
    "pruned-asi-feat-ineligible": {"name": "Grappler"},
    "pruned-asi-option-closed": {"label": msg("label-asi"), "option": "Grappler", "why": msg("disabled-prereq-unmet")},
    "pruned-ability-closed-item": {"ab": "STR", "why": msg("disabled-ability-cap-20")},
    "pruned-ability-closed": {"label": msg("label-asi"), "items": [msg("pruned-ability-closed-item", ab="STR", why=msg("disabled-ability-cap-20"))]},
    "pruned-subclass-unlocks": {"subclass": "Champion", "cls": "Fighter", "level": 3},
    "pruned-slot-removed": {"name": "Shield", "kind": msg("slot-kind-worn"), "slot": msg("slot-armor")},
    "disabled-always-prepared": {"source": "Cleric, домейн Life"}, "disabled-chosen-as": {"label": msg("label-cantrip")},
    "disabled-already-chosen-for": {"name": "Eldritch Spear"}, "disabled-already-chosen-for-n": {"name": "Agonizing Blast", "n": 2},
    "disabled-already-taken-from": {"where": "Fighter, ниво 4"}, "disabled-granted-by": {"name": "Soldier"},
    "disabled-feat-ability-max": {"cap": 20}, "disabled-magical-secrets-used": {"cap": 2},
    "disabled-school-limit": {"free": 1, "schools": ["Evocation", "Abjuration"]}, "disabled-requires-level": {"level": 5},
    "disabled-requires-warlock-level": {"level": 5}, "disabled-requires": {"name": "Pact of the Blade"},
    "disabled-requires-cantrip": {"spell": "Eldritch Blast"}, "disabled-take-first": {"name": "Agonizing Blast"},
    "disabled-take-first-n": {"name": "Agonizing Blast", "n": 1},
    "disabled-prereq-unmet-requires": {"parts": [msg("prereq-level", level=5), msg("prereq-fighting-style")]},
    "prereq-any-of": {"items": [msg("prereq-martial"), msg("prereq-shield")]}, "prereq-level": {"level": 5},
    "prereq-race": {"name": "Elf"}, "prereq-armor-proficiency": {"category": msg("armor-category-heavy")},
    "prereq-feat": {"name": "Alert"},
    "label-tool-proficiency-category": {"category": "Artisan's Tools"}, "label-feature-level": {"name": "Second Wind", "level": 1},
    "label-prefixed": {"head": "Skilled", "tail": msg("label-skill-proficiencies")},
    "desc-replacement-language": {"language": "Elvish"}, "desc-feat-languages": {"n": 2}, "desc-bonus-languages": {"n": 1},
    "desc-feat-proficiencies": {"n": 3}, "desc-feat-expertise": {"n": 2}, "desc-feat-saves": {"n": 1},
    "desc-weapon-proficiency-choice": {"n": 4}, "desc-asi-improvement-options": {"n": 2},
    "desc-asi-increase": {"n": 2, "bonus": "+1"}, "desc-resist-types": {"n": 2},
    "desc-species-feat": {"noun": msg("noun-origin-feat")}, "desc-species-feats": {"count": 2}, "desc-feat-or-dark-gift": {"name": "Survivor"},
    "desc-pick-fighting-style": {"n": 1}, "desc-pick-maneuver": {"n": 3}, "desc-pick-metamagic": {"n": 2},
    "desc-pick-invocation": {"n": 2}, "desc-weapon-mastery-feat": {"n": 2}, "desc-weapon-mastery-class": {"count": 3},
    "desc-granted-automatically": {"names": "Fire Bolt", "n": 1},
    "desc-granted-automatically-after": {"text": "Изберете една от опциите.", "names": "Fire Bolt, Light", "n": 2},
    "desc-choose-noun": {"count": 2, "noun": msg("noun-cantrip", n=2)},
    "noun-cantrip": {"n": 2}, "noun-spell": {"n": 2},
    "noun-spell-levels": {"n": 2, "levels": [1, 2]}, "noun-spell-upto": {"n": 2, "max": 3},
    "noun-school": {"schools": ["Evocation", "Abjuration"], "noun": msg("noun-spell", n=2)},
    "noun-from-list": {"noun": msg("noun-spell", n=2), "classes": ["Cleric", "Wizard"]},
    "noun-ritual": {"noun": msg("noun-spell", n=1)},
    "desc-listed-spells": {"n": 2}, "desc-cantrips-from-list": {"n": 3, "list": "Wizard"},
    "desc-spells-know": {"n": 2, "noun": msg("noun-spell", n=2), "list": "Bard"},
    "desc-spells-prepare": {"n": 4, "noun": msg("noun-spell", n=4), "list": "Cleric"},
    "desc-spells-know-book": {"n": 2, "noun": msg("noun-spell", n=2)},
    "desc-spells-prepare-book": {"n": 4, "noun": msg("noun-spell", n=4)},
    "desc-spells-secrets": {"text": msg("desc-spells-know", n=2, noun=msg("noun-spell", n=2), list="Bard"), "cap": 2},
    "desc-spellbook": {"count": 6, "noun": msg("noun-spell", n=6)}, "desc-mystic-arcanum": {"level": 6},
    "desc-additional-secrets": {"text": msg("desc-spells-know", n=2, noun=msg("noun-spell", n=2), list="Bard")},
    "desc-savant-free": {"text": msg("desc-spellbook", count=6, noun=msg("noun-spell", n=6)), "count": 2},
    "desc-wizard-pick-prepared": {"count": 2, "level": 3, "condition": msg("desc-cond-action")},
    "desc-wizard-pick-cast": {"count": 2, "level": 3, "condition": msg("desc-cond-time", time="1 минута")},
    "desc-wizard-pick-none": {"level": 3, "condition": msg("desc-cond-action")},
    "desc-cond-time": {"time": "1 минута"}, "desc-tome-cantrips": {"count": 3}, "desc-tome-rituals": {"count": 2},
    "desc-choose-colon": {"n": 2, "what": "Athletics, Stealth, Perception"},
    "desc-equipment-note": {"text": "(a) longsword или (b) handaxe"},
}


def _message_rows(flags: dict) -> list[dict]:
    kind_of = {}
    for module, kind in _KIND_NAME:
        for key in module.MESSAGES:
            kind_of[key] = kind
    rows = []
    for key, entry in MESSAGES.items():
        params = _message_params(key)
        used = {f for f in _used_fields(entry["en"])}
        params = {k: v for k, v in params.items() if k in used}
        try:
            en_text = render(msg(key, **params), "en")
            bg_text = render(msg(key, **params), "bg")
        except KeyError as exc:  # a sample parameter is missing
            raise RuntimeError(f"no sample for {{{exc.args[0]}}} of the message {key!r}: add it to MESSAGE_SAMPLES") from exc
        state, extra = classify(entry["en"], entry["bg"])
        notes = []
        if ("msg", key) in flags:
            notes.append(flags[("msg", key)])
        awkward = _awkward_note(entry["bg"])
        if awkward:
            notes.append(awkward)
        if state == "изключение":
            notes.append(extra)
        if state == "остава английско (решено)":
            notes.append("Българският шаблон е еднакъв с английския (на английски е решено).")
        rows.append({"layer": "Съобщение", "key": f"msg:{key}", "en": entry["en"], "bg": entry["bg"],
                     "example": f"{kind_of[key]}: {bg_text}", "state": state, "note": " ".join(n for n in notes if n),
                     "_en_example": en_text})
    return rows


def _used_fields(template: str) -> set[str]:
    from i18n.messages import template_fields
    return template_fields(template)


# ---------------------------------------------------------------------------------------------------------------------
# layer: Експорт (server/export_labels.py)

def _leaves(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, path + (k,))
    else:
        yield ".".join(path), node


# label path -> (params, the export line; "@" stands for the label as printed). Lines are the Markdown export in Bulgarian.
EXPORT_LINES: dict[str, tuple[dict, str]] = {
    "unnamed": ({}, "# @   (заглавието, когато героят няма име)"),
    "filenameFallback": ({}, "име на изтегления файл, когато героят няма име: @.md"),
    "level": ({"level": 5}, "**@ Fighter (Champion)** | **Произход (Background):** Soldier | **Раса (Species):** Dwarf (Hill Dwarf)"),
    "background": ({}, "**Ниво 5 Fighter** | **@:** Soldier | **Раса (Species):** Dwarf"),
    "species": ({}, "**Ниво 5 Fighter** | **Произход (Background):** Soldier | **@:** Dwarf (Hill Dwarf)"),
    "secCombat": ({}, "## @"),
    "armorClass": ({}, "- **@:** 18"), "hitPoints": ({}, "- **@:** 44 (5d10)"), "speed": ({}, "- **@:** 30 фута"),
    "initiative": ({}, "- **@:** +1"), "passivePerception": ({}, "- **@:** 13"), "passiveInsight": ({}, "- **@:** 11"),
    "passiveInvestigation": ({}, "- **@:** 9"), "proficiencyBonus": ({}, "- **@:** +3"),
    "feet": ({"n": 30}, "- **Скорост:** @"),
    "secAbilities": ({}, "## @"), "secSaves": ({}, "## @"), "secSkills": ({}, "## @"), "secLanguages": ({}, "## @"),
    "secProficiencies": ({}, "## @"),
    "profArmor": ({}, "- **@:** Light Armor, Medium Armor, Shield"), "profWeapons": ({}, "- **@:** Simple Weapons, Martial Weapons"),
    "profTools": ({}, "- **@:** Smith's Tools"),
    "expertiseTag": ({}, "- Stealth: +9 @"),
    "secEquipment": ({}, "## @"), "equipGranted": ({}, "### @"), "equipChosen": ({}, "### @"), "equipAdded": ({}, "### @"),
    "equipped": ({}, "- Longsword @"),
    "packContents": ({"items": "Backpack, Bedroll, Rations x5"}, "- Explorer's Pack (@)"),
    "worn": ({"parts": "броня: Chain Mail, щит; в ръце: основна Longsword, свободна Shield"}, "@"),
    "wornArmor": ({"name": "Chain Mail"}, "Носено и в ръце: @, щит"), "wornShield": ({}, "Носено и в ръце: броня: Chain Mail@"),
    "wornNoArmor": ({}, "Носено и в ръце: @"),
    "wielded": ({"main": "Longsword", "off": "Shield"}, "Носено и в ръце: броня: Chain Mail; @"),
    "handEmpty": ({}, "Носено и в ръце: в ръце: основна Longsword, свободна @"),
    "secSpells": ({}, "## @"),
    "spellSaveDc": ({}, "- **@ (Wizard):** 14  |  **Бонус за атака със заклинание (Spell Attack Modifier) (Wizard):** +6"),
    "spellAttackBonus": ({}, "- **DC на спасяването от заклинание (Spell Save DC) (Wizard):** 14  |  **@ (Wizard):** +6"),
    "spellSlots": ({}, "- **@:** ниво 1: 4, ниво 2: 3"), "pactSlots": ({}, "- **@:** ниво 2: 2"),
    "slotLevel": ({"lvl": 1, "n": 4}, "- **Spell Slots:** @, ниво 2: 3"), "spellLevel": ({"lvl": 3}, "- Fireball (@)"),
    "cantrips": ({}, "### @ (Wizard)"), "spellbook": ({}, "- **@ (Wizard):** Shield (ниво 1), Mage Armor (ниво 1)"),
    "preparedSpells": ({}, "### @ (Cleric)"), "mysticArcanum": ({}, "- **@ (Warlock):** Mass Suggestion (ниво 6)"),
    "spellMastery": ({}, "- **@ (Wizard):** Shield (ниво 1), Misty Step (ниво 2)"),
    "signatureSpells": ({}, "- **@ (Wizard):** Counterspell (ниво 3)"),
    "pactOfTheTome": ({}, "- **@ (Warlock):** Guidance, Mage Hand, Thaumaturgy"),
    "secInnate": ({}, "## @"), "innateFromLevel": ({"level": 3}, "- Misty Step (1/дълга почивка (Long Rest)@)"),
    "alwaysPrepared": ({}, "### @ (Cleric)"),
    "secMovement": ({}, "## @"), "secSize": ({}, "## @"), "secSenses": ({}, "## @"), "secExpertise": ({}, "## @"),
    "secResistances": ({}, "## @"),
    "dmgResistances": ({}, "- @: Fire, Cold"), "dmgImmunities": ({}, "- @: Poison"), "dmgVulnerabilities": ({}, "- @: Radiant"),
    "conditionImmunities": ({}, "- @: Frightened"),
    "secAttacks": ({}, "## @"), "attacksPerAction": ({"n": 2}, "- @"),
    "attackVersatile": ({"dice": "1d10"}, "- Longsword: +6, 1d8 slashing (@)"),
    "attackDueling": ({"dice": "1d8+2"}, "- Longsword: +6, 1d8 slashing, @"),
    "attackOffhand": ({"dice": "1d6"}, "- Shortsword: +6, 1d6 piercing, @"),
    "attackRange": ({"range": "80/320"}, "- Longbow: +4, 1d8 piercing, @"),
    "attackMastery": ({"mastery": "Sap"}, "- Longsword: +6, 1d8 slashing, @"),
    "secMasteries": ({}, "## @"), "secClassResources": ({}, "## @"), "secFeatResources": ({}, "## @"),
    "secSpeciesResources": ({}, "## @"), "secCarrying": ({}, "## @"),
    "overCapacity": ({}, "- Носено: 260 / 225 lb@"), "pushDragLift": ({"n": 450}, "- Носено: 96 / 225 lb@"),
    "secArmor": ({}, "## @"), "stealthDisadvantage": ({}, "- Chain Mail: @"),
    "secStartingGold": ({}, "## @"), "startingGold": ({"n": 150}, "- @"),
    "secFeatures": ({}, "## @"), "featureLevel": ({"level": 3}, "- Improved Critical (@)"), "secFeats": ({}, "## @"),
    "unlimited": ({}, "- Reckless Attack: @"), "pool": ({}, "- Lay on Hands: @10 (дълга почивка (Long Rest))"),
    "bonus": ({}, "- Bardic Inspiration: 3, @+3"), "dc": ({}, "- Stunning Strike: @14"),
    "damageBonus": ({"n": 2}, "- Rage: 3, дълга почивка (Long Rest), @"), "healing": ({"v": "1d8+3"}, "- Second Wind: 1, кратка почивка (Short Rest), @"),
    "maxCr": ({"v": "1/2"}, "- Wild Shape: 2, кратка почивка (Short Rest), @"),
    "resAll": ({}, "- Spirit Walker: 1, дълга почивка (Long Rest), @"), "resSome": ({"types": "огнени, студени"}, "- Rage: 3, дълга почивка (Long Rest), @"),
    "shortRestRegains": ({"n": 1}, "- Channel Divinity: 2, дълга почивка (Long Rest), @"),
    "spellSlotRegainsUse": ({}, "- Font of Magic: 3, @"), "bonusActionRegainsOne": ({}, "- Superiority Dice: 4, @"),
    "onShortRest": ({}, "- Arcane Recovery: 1, @"), "maxSlotLevel": ({"n": 5}, "- Arcane Recovery: 1, @"),
    "slotCost": ({"lvl": 2, "n": 3}, "- Font of Magic: 5, @"), "knownForms": ({"n": 4}, "- Wild Shape: 2, @"),
    "metamagic": ({"items": "Quickened Spell (2), Twinned Spell (1)"}, "- Metamagic: 3, @"),
    "perRageOptions": ({"items": "Bear: ...; Eagle: ..."}, "- Rage: 3, @"),
    "damageTypesLine": ({"types": "Cold, Fire, Lightning, or Thunder"}, "- Primal Strike: 1d8, @"),
}
_EXPORT_FAMILY_LINES = {
    "recharge": "- Rage: 3, @, щета +2   (с „(“ в думата се слага запетая, без скоби — в скоби: „(@)“)",
    "modes": "## Движение → @ 30 фута",
    "senses": "## Сетива (Senses) → @ 60 фута",
    "damage": "- Rage: 3, дълга почивка (Long Rest), устойчивост (Resistance): @",
    "detailSections": "## @",
    "detailFields": "**@:**\n\nтекст, който играчът е написал",
}


def _export_rows(flags: dict) -> list[dict]:
    from export_labels import LABELS, label as export_label
    from i18n.messages import format_template
    bg, en = dict(_leaves(LABELS["bg"])), dict(_leaves(LABELS["en"]))
    rows = []
    for path, text in bg.items():
        params = EXPORT_LINES.get(path, ({}, None))[0]
        if path in EXPORT_LINES:
            line = EXPORT_LINES[path][1]
        else:
            family = path.split(".")[0]
            if family not in _EXPORT_FAMILY_LINES:
                raise RuntimeError(f"no export example line for the label {path!r}: add it to EXPORT_LINES")
            line = _EXPORT_FAMILY_LINES[family]
        shown = format_template(text, params) if path in EXPORT_LINES else text
        if path == "pool":
            shown = text.strip()
        example = "Ред в Markdown / PDF файла: " + line.replace("@", shown)
        state, extra = classify(en[path], text)
        notes = []
        if ("export", path) in flags:
            notes.append(flags[("export", path)])
        awkward = _awkward_note(text)
        if awkward:
            notes.append(awkward)
        if state == "изключение":
            notes.append(extra)
        rows.append({"layer": "Експорт", "key": f"export:{path}", "en": en[path], "bg": text, "example": example,
                     "state": state, "note": " ".join(notes)})
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# layer: Речник (server/i18n/glossary.json)

def _glossary_rows(flags: dict, corpus: list[tuple[str, str]], ui_examples: dict[str, str]) -> list[dict]:
    """`corpus`: [(where, bg text)] of real app sentences in which a term can be found."""
    gloss = glossary_mod.load()
    rows = []
    for tid, term in gloss.items():
        bg = term["bg"]
        core = re.sub(r"\s*\([^()]*\)$", "", bg)
        candidates = [(w, t) for w, t in corpus if bg in t and t != bg and len(t) >= len(bg) + 12]
        if not candidates:
            candidates = [(w, t) for w, t in corpus if core in t and t != core and len(t) >= len(core) + 12]
        if candidates:
            where, sentence = min(candidates, key=lambda c: (len(c[1]) > 160, len(c[1]) if len(c[1]) > 40 else 999, c[1]))
            example = f"{where}: {sentence}"
        else:
            example = ui_examples.get(bg) or f"Заглавие или етикет в приложението: {_quote(bg)}"
        state, extra = classify(term["en"], bg)
        notes = []
        awkward = _awkward_note(bg)
        if awkward:
            notes.append(awkward)
        if state == "изключение":
            notes.append(extra)
        if tid in ("spellSlots",):
            notes.append("Решение на собственика (2026-11-05): Spell Slots остава английски без скоби.")
        rows.append({"layer": "Речник", "key": f"glossary:{tid}", "en": term["en"], "bg": bg, "example": example,
                     "state": state, "note": " ".join(n for n in notes if n)})
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# layer: Имена

def _names_rows(flags: dict) -> list[dict]:
    text = NAMES_TS.read_text(encoding="utf-8")

    def block(name: str) -> str:
        m = re.search(rf"export const {name}\b.*?\n\];", text, re.S)
        assert m, name
        return m.group(0)

    male, female, surn = (re.sub(r"//[^\n]*", "", block(n)) for n in ("MALE_FIRST", "FEMALE_FIRST", "SURNAMES"))
    n_male, n_female = len(re.findall(r'\bn\("', male)), len(re.findall(r'\bn\("', female))
    n_surn = len(re.findall(r'\bsr?\("', surn))
    flagged = [(ref, why) for (kind, ref), why in flags.items() if kind == "name"]

    def doubtful(block_text: str) -> str:
        names = sorted(ref for ref, _w in flagged if f'"{ref}"' in block_text)
        return (f" Под съмнение (прегледани и приети от собственика, виж docs/I18N-REVIEW.md): {', '.join(names)}." if names else "")

    examples = {"male": "Пример при мъж: „Борислав Вутов“ (бутонът със зара до „Character Name“ на страница „Home“)",
                "female": "Драгана Вутова (бутонът със зара до „Character Name“ на страница „Home“; на английски: Dragana Vutova)",
                "surname": "Фамилията се слага по пола на малкото име: Вутов / Вутова, -ски / -ска (бутонът със зара на „Home“)"}
    base = ("Списъкът е в frontend/src/names/bgNames.ts (всяко име има произход: bulgar, slavic, dynastic, christian, folklore, "
            "revival, literary; всички произходи са включени по подразбиране). Собственикът го е прегледал при N1 и N2; "
            "английският вариант е официалната транслитерация (frontend/src/logic/translit.ts).")
    return [
        {"layer": "Имена", "key": "names:MALE_FIRST", "en": f"{n_male} male first names", "bg": f"{n_male} мъжки собствени имена",
         "example": examples["male"], "state": "преведено",
         "note": base + doubtful(male)},
        {"layer": "Имена", "key": "names:FEMALE_FIRST", "en": f"{n_female} female first names", "bg": f"{n_female} женски собствени имена",
         "example": examples["female"], "state": "преведено", "note": base + doubtful(female)},
        {"layer": "Имена", "key": "names:SURNAMES", "en": f"{n_surn} surnames (male and female form)", "bg": f"{n_surn} фамилии (мъжка и женска форма)",
         "example": examples["surname"], "state": "преведено", "note": base + doubtful(surn)},
    ]


# ---------------------------------------------------------------------------------------------------------------------
# layer: Не се превежда

_E4 = ("Решение E4: правилата, които двигателят описва със свои думи (бележки в reference_data, бележки за ефекти на таланти, "
       "бележки за ресурси на класове), са текст на правилата и остават на английски и в българския.")
# (key, English, Bulgarian as shown, example, state, why)
UNTRANSLATED: list[tuple[str, str, str, str, str, str]] = [
    ("data:class-names", "Fighter, Wizard, Cleric ... (class names)", "Fighter, Wizard, Cleric ...",
     "Лист, секция „Герой“: Класове: Fighter 5 (Champion); съобщение: „изисква ниво 5 на warlock“",
     "остава английско (решено)", "Имената на класовете идват от данните (SRD и 5etools) и остават английски и в двата езика, за да съвпадат с книгите. В българско изречение името стои английско: „изисква ниво 5 на warlock“."),
    ("data:subclass-names", "Champion, Evocation, Life Domain ...", "Champion, Evocation, Life Domain ...",
     "Страница „Клас“, падащ списък „Подклас“: Champion", "остава английско (решено)", "Имената на подкласовете идват от данните и не се превеждат."),
    ("data:species-names", "Dwarf (Hill Dwarf), Elf, Tiefling ...", "Dwarf (Hill Dwarf), Elf, Tiefling ...",
     "Лист, секция „Герой“: Раса (Species): Dwarf (Hill Dwarf)", "остава английско (решено)", "Имената на расите и подрасите идват от данните и не се превеждат."),
    ("data:background-names", "Soldier, Sage, Acolyte ...", "Soldier, Sage, Acolyte ...",
     "Страница „Произход (Background)“: списък с произходи; лист: Произход (Background): Soldier", "остава английско (решено)", "Имената на произходите идват от данните и не се превеждат."),
    ("data:feat-names", "Alert, Grappler, Skilled ...", "Alert, Grappler, Skilled ...",
     "Лист, секция „Таланти (Feats)“: Alert; съобщение: „Alert вече е взет“", "остава английско (решено)", "Имената на талантите идват от данните и не се превеждат; думата „талант (Feat)“ около тях е преведена."),
    ("data:spell-names", "Fireball, Shield, Fire Bolt ...", "Fireball, Shield, Fire Bolt ...",
     "Лист, секция „Заклинания“: Fireball (ниво 3); експорт: „Fireball (ниво 3)“", "остава английско (решено)", "Имената на заклинанията идват от данните и не се превеждат."),
    ("data:item-names", "Longsword, Chain Mail, Explorer's Pack ...", "Longsword, Chain Mail, Explorer's Pack ...",
     "Лист, секция „Екипировка“: Chain Mail (екипиран); експорт: „Explorer's Pack (съдържа: Backpack, Bedroll)“", "остава английско (решено)", "Имената на предметите идват от данните и не се превеждат."),
    ("data:feature-names", "Second Wind, Rage, Divine Order, Thieves' Cant ...", "Second Wind, Rage, Divine Order, Thieves' Cant ...",
     "Лист, секция „Способности на класа (Class Features)“: Second Wind (ниво 1); ресурс: „Rage: 3, дълга почивка (Long Rest), щета +2“",
     "остава английско (решено)", "Имената на способностите на класа и на чертите на расата са данни и остават английски (на техните описания също)."),
    ("data:skill-names", "Athletics, Stealth, Perception ...", "Athletics, Stealth, Perception ...",
     "Лист, таблица „Умения (Skills)“: Stealth +5; съобщение: „'Владеене на умения (Skill Proficiencies)': вече се владее Athletics“",
     "остава английско (решено)", "Имената на уменията са данни (SRD). Думата „умение (Skill)“ около тях е преведена, самите имена не."),
    ("data:language-names", "Elvish, Dwarvish, Common ...", "Elvish, Dwarvish, Common ...",
     "Лист, секция „Езици“: Common, Dwarvish; съобщение: „вече знаете Elvish“", "остава английско (решено)", "Имената на езиците са данни и не се превеждат."),
    ("data:ability-names", "Strength, Dexterity, Intelligence, STR, DEX ...", "Strength, Dexterity, Intelligence, STR, DEX ...",
     "Съобщение: „Характеристиката (Ability Score), с която изричате заклинанието на инвокацията (Intelligence, Wisdom или Charisma)“; страница „Abilities“: STR, DEX",
     "остава английско (решено)", "Имената и кодовете на характеристиките остават английски. Само общата дума „Характеристики (Ability Scores)“ е преведена. Български вариант на самите имена би бил отделно решение."),
    ("data:damage-type-ids", "acid, bludgeoning, fire, slashing ...", "acid, bludgeoning, fire, slashing ...",
     "Лист, секция „Атаки“, колона „Щета“: 1d8 slashing (типът щета идва от данните като английски идентификатор); ресурс: „устойчивост (Resistance): огнени, студени“ (там думите са преведени)",
     "остава английско (решено)", "Типовете щети в данните за оръжия и ефекти са английски идентификатори (slashing, fire ...). Преведени са само в редовете на ресурсите, в списъка с устойчивост и в имунитетите (виж „киселинни, дробящи, студени, огнени ...“ в слоя Интерфейс и Експорт)."),
    ("data:size-names", "Small, Medium, Large", "Small, Medium, Large",
     "Лист, секция „Герой“: Размер: Medium", "остава английско (решено)", "Размерът на расата идва от данните."),
    ("data:source-names", "PHB, XPHB, TCE, SRD", "PHB, XPHB, TCE, SRD",
     "Страница „Home“, списък „Източници (Sources)“: XPHB; съобщение: „вече се владее Athletics (Soldier)“", "остава английско (решено)", "Имената и съкращенията на книгите са данни."),
    ("data:class-option-names", "Fighting Style", "Fighting Style",
     "Заглавие на карта: „Fighter: Fighting Style“; описание: „Научете 1 Fighting Style опция от класа fighter. Тя трябва да се различава от стил, който вече имате.“",
     "остава английско (решено)", "Решение на собственика (T1): имената на опциите на класа остават английски, без скоби. Преведено е само изречението около тях."),
    ("data:class-option-names-metamagic", "Metamagic", "Metamagic",
     "Заглавие на карта: „Sorcerer: Metamagic“; ресурс: „метамагия: Quickened Spell (2), Twinned Spell (1)“", "остава английско (решено)",
     "Решение на собственика (T1): остава английско име на опцията на класа. В реда на ресурса думата „метамагия:“ вече е на български (преведена преди T1)."),
    ("data:class-option-names-maneuvers", "Maneuvers", "Maneuvers",
     "Заглавие на карта: „Fighter: Maneuvers“; описание: „Научете 3 maneuvers от наличните за Battle Master.“", "остава английско (решено)",
     "Решение на собственика (T1): остава английско име на опцията на класа."),
    ("data:class-option-names-invocation", "Eldritch Invocation", "Eldritch Invocation",
     "Заглавие на карта: „Warlock: Eldritch Invocation“; описание: „Научете 2 Eldritch Invocations от класа warlock.“", "остава английско (решено)",
     "Решение на собственика (T1): остава английско име на опцията на класа."),
    ("data:class-option-names-arcanum", "Mystic Arcanum", "Mystic Arcanum",
     "Описание на карта: „Изберете едно заклинание от ниво 6 от списъка на Warlock като свой Mystic Arcanum.“; на листа и в експорта заглавието е на български: „Мистичен арканум“",
     "остава английско (решено)", "Решение на собственика (T1): в съобщенията остава английско име на опцията. Заглавието „Мистичен арканум“ на листа и в експорта е преведено още преди T1 (виж ред „Мистичен арканум“ в слоя Експорт)."),
    ("term:spell-slots", "Spell Slots", "Spell Slots",
     "Лист, секция „Заклинания“: заглавие „Spell Slots“: ниво 1: 4, ниво 2: 3; ресурс: „Spell Slots до ниво 5“; „1 използване се възстановява срещу Spell Slot“",
     "остава английско (решено)", "Решение на собственика (2026-11-05): остава английско навсякъде (лист, експорт, редове на ресурсите, речник), без скоби и без „слот“ или „Клетки за заклинания“."),
    ("term:pact-magic-slots", "Pact Magic Slots", "Pact Magic Slots",
     "Експорт, секция „Заклинания“: „- Pact Magic Slots: ниво 2: 2“; на листа заглавието е „Магия на договора“", "остава английско (решено)",
     "Българският експорт печата английската дума, както за Spell Slots (XL). Уебстраницата казва „Магия на договора“. Съмнение в docs/I18N-REVIEW.md (ред 1)."),
    ("export:attack-tags", "versatile / off hand / range", "versatile / off hand / range",
     "Експорт, секция „Атаки“: „Longsword: +6, 1d8 slashing (versatile 1d10), range 80/320“; в уебстраницата същите тагове са на български („двуръчно“, „в свободната ръка“)",
     "остава английско (решено)", "Българският експорт запазва английските тагове на атаките (XL); уебстраницата има български (двуръчно, с Дуел, в свободната ръка). Съмнение в docs/I18N-REVIEW.md (редове 2-4)."),
    ("rules:paraphrases-notes", "Rule paraphrase notes (reference data)", "Rule paraphrase notes (reference data)",
     "Лист, редове на ресурсите и бележки: „Rage: 3, дълга почивка (Long Rest), щета +2“ — бележката след запетаята е текст на правилата, написан от двигателя на английски",
     "остава английско (решено)", _E4),
    ("rules:feat-effect-notes", "Feat effect notes", "Feat effect notes",
     "Лист, секция „Таланти (Feats)“ и бележки към атаки/защита: например „+5 към инициативата“-тип бележки от ефектите на талантите са на английски", "остава английско (решено)", _E4),
    ("rules:class-resource-notes", "Class resource notes", "Class resource notes",
     "Лист, секция „Ресурси“: бележката на ресурс, например за Channel Divinity", "остава английско (решено)", _E4),
    ("rules:5etools-descriptions", "5etools feature/feat/spell descriptions", "5etools feature/feat/spell descriptions",
     "Лист и страници за избор: описанията на способности, таланти и заклинания в карта за избор", "остава английско (решено)",
     "Описанията идват от данните (5etools и SRD) като английски текст и не се превеждат; това е най-големият дял английски текст в приложението."),
    ("rules:equipment-envelopes", "(a) ... or (b) ... starting equipment text", "(a) ... or (b) ... starting equipment text",
     "Страница „Equipment“, началната екипировка на класа: „(a) a longsword or (b) a handaxe“; описание на карта: „Choose two skills from ...“",
     "остава английско (решено)", "Текстът на началната екипировка и „Choose two skills from ...“ са данни от 5etools и не се превеждат."),
    ("engine:instance-label", "Agonizing Blast (2)", "Agonizing Blast (2)",
     "Страница „Клас“, втора карта за една и съща опция на инвокация: „Agonizing Blast (2)“", "остава английско (решено)",
     "Етикетът с номер на екземпляр е езиково неутрален (име + число), няма какво да се превежда."),
    ("api:transport-error", "{\"error\": ...} (API transport texts)", "{\"error\": ...} (API transport texts)",
     "Отговор на сървъра при невалидна заявка: {\"error\": \"'lang' must be 'bg' or 'en'\"}; браузърът показва вместо него българско съобщение („Черновата не е във вярна форма и сървърът я отхвърли.“)",
     "остава английско (решено)", "Текстовете в „error“ на API са за програмисти и са английски. Приложението показва своето българско съобщение (слой Интерфейс, msg.http.*)."),
    ("user:own-text", "The character's own text (name, details)", "The character's own text (name, details)",
     "Лист: Име: Тордек; Данни за героя: „Предистория“ — както са въведени", "остава английско (решено)", "Текстът, който играчът пише (име, външност, предистория), се показва както е написан."),
    ("export:yaml", "YAML export has no labels", "YAML export has no labels",
     "Страница „Export“, бутон „Изтегли YAML“: файлът има само ключове, без преведени етикети", "остава английско (решено)", "YAML файлът носи данни, не етикети, затова е еднакъв в двата езика."),
    ("export:quirk-null", "null in an attack line", "null in an attack line",
     "Експорт, секция „Атаки“: атака с щета, но без вид щета, печата „1d8 null“", "изключение", "Запазена особеност: редът печата буквално null. Не е превод; описано е тук, за да реши собственикът дали да се поправи."),
    ("export:quirk-feet", "senses: always 'фута'", "senses: always 'фута'",
     "Експорт и лист: „тъмно зрение (Darkvision) 60 фута“ — думата е една и за 1, и за 60", "изключение", "Запазена особеност: „фута“ се печата и за 1 фут. Не е превод."),
    ("abbr:AC", "AC", "AC",
     "Лист, секция „Клас броня (Armor Class, AC)“: 18; съобщение: „{name} е в лявата ръка, но щитът не е отбелязан като носен; не добавя към AC.“", "изключение",
     "Съкращението AC е в скобите на термина „Клас броня (Armor Class, AC)“ и се ползва самостоятелно в изреченията (T1: избрано е с AC, защото играчите казват „AC“)."),
    ("abbr:DC", "DC", "DC",
     "Лист, секция „Заклинания“: „DC на спасяването от заклинание (Spell Save DC): 14“; ресурс: „ТС 14“", "изключение",
     "DC остава английско съкращение в името на термина, а в реда на ресурса е „ТС“ (трудност на спасяването) — две различни форми на една и съща дума; реши коя да остане."),
    ("abbr:HP", "HP", "HP",
     "Съобщение: „Хвърлянето за HP на Fighter ниво 3 трябва да е между 1 и 10; използвана е средната стойност.“ (шаблон hp-roll-invalid)", "изключение",
     "Съкращението HP остава в някои съобщения, докато заглавията казват „Точки живот (Hit Points)“; реши дали и там да е „точки живот“."),
    ("abbr:CR", "CR", "CR",
     "Ред на ресурс: „макс. CR 1/2“ (Wild Shape)", "изключение", "CR (challenge rating) е ограничителният показател на звяр за Wild Shape; остава съкращение."),
    ("abbr:SP", "SP", "SP",
     "Опция на талант в карта за избор: „Quickened Spell (2 SP)“ (точки за чародейство)", "изключение", "SP (sorcery points) е в етикети от данните и не се превежда."),
    ("abbr:lb", "lb", "lb",
     "Лист, „Носимост (Carrying Capacity)“: 96 / 225 lb; експорт: „, тласкане/влачене/вдигане 450 lb“", "изключение", "Мерната единица lb (паунд) остава, както е в книгите; футовете са преведени („фута“)."),
    ("abbr:dice", "d4, d6, d8, d10, d12, d20", "d4, d6, d8, d10, d12, d20",
     "Страница „Клас“: „Fighter (d10)“; лист: Точки живот (Hit Points): 44 (5d10)", "изключение", "Означенията на зарове са международни и не се превеждат."),
    ("ui:marks", "Latin tags: Ritual, Concentration", "Ритуал, Концентрация",
     "Списък със заклинания: „Fireball · 3 ниво · Концентрация“", "преведено", "За справка: в списъка със заклинания етикетите са български, имената на заклинанията са английски."),
]


def _untranslated_rows(english_ui: list[dict]) -> list[dict]:
    rows = []
    for key, en, bg, example, state, why in UNTRANSLATED:
        rows.append({"layer": "Не се превежда", "key": key, "en": en, "bg": bg, "example": example, "state": state, "note": why})
    return rows + english_ui


# ---------------------------------------------------------------------------------------------------------------------
# corpus of real Bulgarian sentences for the glossary examples

def _corpus(ui_rows: list[dict], msg_rows: list[dict], export_rows: list[dict]) -> list[tuple[str, str]]:
    out = []
    for r in msg_rows:
        bg = r["example"].split(": ", 1)[1] if ": " in r["example"] else r["example"]
        out.append(("Съобщение на сървъра", bg))
    for r in ui_rows:
        if len(r["bg"]) > 25:
            out.append(("Текст в интерфейса", r["bg"]))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# assembling

def build_rows() -> list[dict]:
    gloss = glossary_mod.load()
    flags = _flag_notes()
    ui, ui_english = _ui_rows(gloss, flags)
    msg_rows = _message_rows(flags)
    exp_rows = _export_rows(flags)
    ui_examples = {r["bg"]: r["example"].split("\n")[0] for r in ui + exp_rows}
    gl_rows = _glossary_rows(flags, _corpus(ui, msg_rows, exp_rows), ui_examples)
    names = _names_rows(flags)
    untranslated = _untranslated_rows(ui_english)
    rows = ui + msg_rows + exp_rows + gl_rows + names + untranslated
    for r in rows:
        r.pop("_en_example", None)
    rows.sort(key=lambda r: LAYERS.index(r["layer"]))  # stable: page order inside a layer
    for i, r in enumerate(rows, 1):
        r["n"] = i
        r.setdefault("note", "")
    return rows


def row_values(r: dict) -> list:
    return [r["n"], r["layer"], r["key"], r["en"], r["bg"], r["example"], r["state"], "", "", r["note"]]


def render_csv(rows: list[dict]) -> str:
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADERS)
    for r in rows:
        w.writerow(row_values(r))
    return "﻿" + buf.getvalue()


def counts(rows: list[dict]) -> list[tuple[str, int]]:
    return [(layer, sum(1 for r in rows if r["layer"] == layer)) for layer in LAYERS]


# ---------------------------------------------------------------------------------------------------------------------
# xlsx (needs openpyxl, not a project dependency)

HOWTO = [
    ("Как да ползваш този файл", True),
    ("Това е списък на всички думи и изрази в приложението, които са преведени на български или нарочно са оставени на английски. Целта е ти да прегледаш речника и да кажеш кое да остане и кое да се промени.", False),
    ("", False),
    ("Колоните", True),
    ("№ — пореден номер на реда (за справка, не го променяй).", False),
    ("Слой — къде е текстът: Интерфейс (уебстраниците), Съобщение (текстове, които пише сървърът: проблеми, предупреждения, причини, етикети на карти), Експорт (етикетите в Markdown и PDF файла), Речник (правилата и термините), Имена (списъците за случайните имена), Не се превежда (английското, което е оставено нарочно, с причина).", False),
    ("Ключ — къде живее текстът в кода. Не е нужно да го четеш; разработчикът го ползва, за да намери мястото. Когато един и същ текст е на няколко места, ключовете са един под друг.", False),
    ("Английски — оригиналният английски текст (правилата са по Player's Handbook 2024, после SRD).", False),
    ("Български — текстът, който приложението показва сега. Думите като {name} или {n} се попълват от приложението; {n|а|б} избира форма „а“ за 1 и „б“ за повече.", False),
    ("Пример в изречение — как изглежда текстът на мястото си: на коя страница е, или цялото изречение със попълнени примерни стойности. Той е за ориентация, не го променяй.", False),
    ("Състояние — преведено; преведено + английско в скоби (по решението T1 българският термин е следван от английския в скоби); остава английско (решено); изключение (смесен текст или особеност, за която да решиш).", False),
    ("Решение — падащ списък: Остава (текстът е добър), Променя се (искаш друг текст), ? (не си сигурен/сигурна). Празно значи, че още не си го гледал/а; ще го приема за „Остава“.", False),
    ("Нова версия — ако си избрал „Променя се“, напиши тук точния нов български текст (запази думите в {скоби} и формите {n|а|б}, както са).", False),
    ("Бележка — защо реда е спорен: предварително попълнена от предишната работа (docs/I18N-REVIEW.md) и за дългите текстове заради скобите. Можеш да пишеш и свои бележки.", False),
    ("", False),
    ("Как да отбележиш решение", True),
    ("1. Филтрирай по „Слой“ или по „Бележка“ (има филтри на всяка колона), за да видиш най-спорните първо.", False),
    ("2. В колоната „Решение“ избери от списъка. Не е нужно да попълваш всичко: ред без решение се счита за „Остава“.", False),
    ("3. При „Променя се“ напиши новия текст в „Нова версия“.", False),
    ("", False),
    ("Какво става после", True),
    ("Върни файла (xlsx) и ще приложа решенията: за всеки ред с „Променя се“ ще сменя текста на мястото от колоната „Ключ“ (на български, а при нужда и в речника), ще пусна проверките и ще върна обновения файл. Изборът „?“ ще ти го върна като въпрос.", False),
]


def write_xlsx(rows: list[dict], path: pathlib.Path) -> None:
    # imported by name: openpyxl is not a project dependency (the isolation test scans literal imports)
    import importlib
    Workbook = importlib.import_module("openpyxl").Workbook
    styles = importlib.import_module("openpyxl.styles")
    Alignment, Font, PatternFill = styles.Alignment, styles.Font, styles.PatternFill
    get_column_letter = importlib.import_module("openpyxl.utils").get_column_letter
    DataValidation = importlib.import_module("openpyxl.worksheet.datavalidation").DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Преглед"
    ws.append(HEADERS)
    for r in rows:
        ws.append(row_values(r))
    widths = [6, 16, 34, 38, 38, 60, 24, 14, 38, 50]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    head_fill = PatternFill("solid", fgColor="DDE6F0")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = head_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{len(rows) + 1}"
    dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True, showErrorMessage=True,
                        errorTitle="Решение", error="Избери Остава, Променя се или ?")
    ws.add_data_validation(dv)
    dv.add(f"H2:H{len(rows) + 1}")
    edit_fill = PatternFill("solid", fgColor="FFF8DC")
    for r in range(2, len(rows) + 2):
        ws.cell(r, 8).fill = edit_fill
        ws.cell(r, 9).fill = edit_fill

    how = wb.create_sheet("Как да ползваш")
    how.column_dimensions["A"].width = 120
    for text, bold in HOWTO:
        how.append([text])
        c = how.cell(how.max_row, 1)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if bold:
            c.font = Font(bold=True, size=13)

    summary = wb.create_sheet("Брой по слой")
    summary.append(["Слой", "Редове"])
    for layer, n in counts(rows):
        summary.append([layer, n])
    summary.append(["Общо", len(rows)])
    for cell in summary[1]:
        cell.font = Font(bold=True)
    summary.cell(summary.max_row, 1).font = Font(bold=True)
    summary.cell(summary.max_row, 2).font = Font(bold=True)
    summary.column_dimensions["A"].width = 22
    wb.save(path)


# ---------------------------------------------------------------------------------------------------------------------
# CLI

def main(argv: list[str] | None = None, out_csv: pathlib.Path = OUT_CSV, out_xlsx: pathlib.Path = OUT_XLSX) -> int:
    args = sys.argv[1:] if argv is None else argv
    rows = build_rows()
    text = render_csv(rows)
    if "--check" in args:
        if not out_csv.exists() or out_csv.read_bytes() != text.encode("utf-8"):
            print(f"{out_csv} is stale; run: cd server && ../.venv/bin/python -m i18n.review_sheet --csv-only", file=sys.stderr)
            return 1
        return 0
    out_csv.write_bytes(text.encode("utf-8"))
    print(f"wrote {out_csv} ({len(rows)} rows: " + ", ".join(f"{layer} {n}" for layer, n in counts(rows)) + ")")
    if "--csv-only" in args:
        return 0
    import importlib.util
    if importlib.util.find_spec("openpyxl") is None:
        print("openpyxl is not installed here: the xlsx was not written (use a throwaway venv outside the repo, see the README)",
              file=sys.stderr)
        return 0
    write_xlsx(rows, out_xlsx)
    print(f"wrote {out_xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
