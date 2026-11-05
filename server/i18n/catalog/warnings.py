"""Warning messages (I2): non-blocking notes from `resolve`, the equipment, worn and class-resource modules.

Same conventions as `problems.py`: the English templates reproduce the former f-strings byte for byte; the Bulgarian
ones keep the placeholders, keep game terms and names in English and take rules words from `i18n/glossary.json`.
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # --- ruleset and source filters ---------------------------------------------------------------------------
    "ruleset-invalid": {
        "en": "Unknown ruleset '{ruleset}'; using mixed.",
        "bg": "Непознат набор от правила '{ruleset}'; използва се mixed.",
    },
    "ruleset-2014-background-asi-ignored": {
        "en": "{name} is a 2024 background; under the 2014 rules its ability score increase is ignored.",
        "bg": "{name} е произход (Background) от 2024; според правилата от 2014 увеличението на характеристиките (Ability Scores) му се пренебрегва.",
    },
    "ruleset-2024-species-asi-ignored": {
        "en": "Under the 2024 rules ability scores come from the background; the species' ability score increase is ignored.",
        "bg": ("Според правилата от 2024 характеристиките (Ability Scores) идват от произхода (Background); увеличението на характеристиките от расата (Species) се пренебрегва."),
    },
    "ruleset-2024-background-no-asi": {
        "en": "{name} is a 2014 background and grants no ability score increase under the 2024 rules.",
        "bg": "{name} е произход (Background) от 2014 и не дава увеличение на характеристиките (Ability Scores) според правилата от 2024.",
    },
    "ruleset-2024-background-no-origin-feat": {
        "en": "{name} grants no Origin feat, which the 2024 rules expect from a background.",
        "bg": "{name} не дава талант от произхода (Origin Feat), какъвто правилата от 2024 очакват от един произход (Background).",
    },
    "asi-double-dip-prevented": {
        "en": "The background's ability score increase replaces the species' (both would double-count under the 2024 rules).",
        "bg": ("Увеличението на характеристиките (Ability Scores) от произхода (Background) замества това от расата (Species); според правилата от 2024 иначе щяха да се броят два пъти."),
    },
    "source-hidden": {
        "en": "'{name}' comes from a book that is switched off in Sources; it is still applied.",
        "bg": "'{name}' идва от книга, изключена в Източници; все пак се прилага.",
    },
    "feat-hidden-by-filters": {
        "en": "{feat} is outside the current ruleset/sources but stays selected.",
        "bg": "{feat} е извън текущия набор от правила/източници, но остава избран.",
    },
    # --- ability scores, hit points, equipment envelopes ------------------------------------------------------
    "ability-above-20": {
        "en": "{ab} base score {value} is above 20, the usual cap for a character's own score.",
        "bg": "Базовата стойност {value} на {ab} е над 20 — обичайната горна граница за собствената характеристика (Ability Score) на героя.",
    },
    "hp-roll-invalid": {
        "en": "The HP roll for {cls} level {level} must be between 1 and {die}; the average was used instead.",
        "bg": ("Хвърлянето за точки живот (Hit Points) за {cls} ниво {level} трябва да е между 1 и {die}; вместо него е използвана средната стойност."),
    },
    "equipment-envelope-dropped": {
        "en": "{name}'s starting equipment has {n} choice(s) that can't be shown yet and were left out.",
        "bg": "Част от началната екипировка на {name} ({n} {n|избор|избора}) още не може да се покаже и беше пропусната.",
    },
    # --- class resources --------------------------------------------------------------------------------------
    "class-2024-tables-missing": {
        "en": "The 2024 class tables are not available; class resources use the 2014 numbers.",
        "bg": "Таблиците за класовете от 2024 не са налични; ресурсите на класовете използват числата от 2014.",
    },
    "subclass-2024-tables-missing": {
        "en": "The 2024 subclass tables are not available; subclass resources use the 2014 formulas.",
        "bg": "Таблиците за подкласовете от 2024 не са налични; ресурсите на подкласовете използват формулите от 2014.",
    },
    # --- armor ------------------------------------------------------------------------------------------------
    "armor-not-proficient": {
        "en": ("Not proficient with {name}: disadvantage on STR/DEX ability checks, saves and attack rolls, "
               "and no spellcasting while it is worn."),
        "bg": ("Нямаш владеене (Proficiency) на {name}: недостатък (Disadvantage) при проверки на характеристики (Ability Checks) STR/DEX, спасителни хвърляния (Saving Throws) и хвърляния за атака, и не можеш да изричаш заклинания, докато се носи."),
    },
    "armor-strength": {
        "en": "{name} needs Strength {minimum}; below that, speed is reduced by 10 ft.",
        "bg": "{name} изисква Сила (STR) {minimum}; под тази стойност скоростта се намалява с 10 фута.",
    },
    "armor-multiple-body": {
        "en": "More than one suit of body armor is equipped; only one can be worn.",
        "bg": "Екипирана е повече от една броня за тяло; може да се носи само една.",
    },
    "fly-armor": {
        "en": "{name} flying speed unusable in {armor} armor.",
        "bg": "Скоростта на летене на {name} не може да се използва в {armor} броня.",
    },
    "armor-category-medium-heavy": {"en": "medium/heavy", "bg": "средна/тежка"},
    "armor-category-light": {"en": "light", "bg": "лека"},
    "armor-category-medium": {"en": "medium", "bg": "средна"},
    "armor-category-heavy": {"en": "heavy", "bg": "тежка"},
    # --- worn and wielded items -------------------------------------------------------------------------------
    "slot-kind-worn": {"en": "worn", "bg": "носен"},
    "slot-kind-wielded": {"en": "wielded", "bg": "държан"},
    "slot-armor": {"en": "armor", "bg": "броня"},
    "slot-main": {"en": "main", "bg": "основна ръка"},
    "slot-off": {"en": "off", "bg": "втора ръка"},
    "slot-unknown-item": {
        "en": "The {kind} {slot} item '{item}' is not in the catalog and was ignored.",
        "bg": "Предметът '{item}' ({kind}: {slot}) не е в каталога и беше пренебрегнат.",
    },
    "slot-not-in-inventory": {
        "en": "{name} is set as {kind} ({slot}) but is not in the inventory; it was ignored.",
        "bg": "{name} е зададен ({kind}: {slot}), но не е в инвентара; беше пренебрегнат.",
    },
    "wielded-not-holdable": {
        "en": "{name} is body armor; it cannot be held in a hand.",
        "bg": "{name} е броня за тяло; не може да се държи в ръка.",
    },
    "wielded-main-shield": {
        "en": "{name} is a shield; put it in the off hand.",
        "bg": "{name} е щит; сложете го във втората ръка.",
    },
    "wielded-same-item-twice": {
        "en": "{name} is in both hands but the inventory has only one.",
        "bg": "{name} е в двете ръце, но инвентарът съдържа само един.",
    },
    "wielded-two-handed-conflict": {
        "en": "{name} needs both hands, but the other hand also holds an item.",
        "bg": "{name} изисква две ръце, но другата ръка също държи предмет.",
    },
    "worn-armor-not-body-armor": {
        "en": "{name} is not body armor; the armor slot was ignored.",
        "bg": "{name} не е броня за тяло; мястото за броня беше пренебрегнато.",
    },
    "worn-shield-missing": {
        "en": "A shield is marked as worn but the inventory has none.",
        "bg": "Щит е отбелязан като носен, но инвентарът няма такъв.",
    },
    "wielded-shield-not-worn": {
        "en": "{name} is in the off hand but the shield is marked as not worn; it adds no AC.",
        "bg": "{name} е във втората ръка, но щитът е отбелязан като неносен; не добавя към AC.",
    },
    "wielded-two-handed-shield": {
        "en": "A two-handed weapon is held while a shield is marked as worn.",
        "bg": "Държи се двуръчно оръжие, докато щит е отбелязан като носен.",
    },
}
