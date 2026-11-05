"""Problem messages (I2): the draft's own mistakes, found by `normalize_draft` and `resolve`, and the export gate.

`MESSAGES[key] = {"en": template, "bg": template}`. The English templates reproduce the engine's former f-strings
byte for byte (the frozen snapshot depends on it); the Bulgarian ones keep the same placeholders. Game terms and names
(class, species, feat, item names, ability codes, `mixed`/`2024` values) stay English; rules words follow
`i18n/glossary.json`. Quoted `'{x}'` parameters are ids or labels from the draft and stay as they are.
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # --- normalize_draft: the draft arrived with the wrong JSON type ------------------------------------------
    "malformed-object": {
        "en": "'{label}' must be an object; it was ignored.",
        "bg": "'{label}' трябва да бъде обект; беше пренебрегнато.",
    },
    "malformed-text": {
        "en": "'{label}' must be text; it was ignored.",
        "bg": "'{label}' трябва да бъде текст; беше пренебрегнато.",
    },
    "malformed-selection-not-list": {
        "en": "The selection for '{key}' must be a list; it was ignored.",
        "bg": "Изборът за '{key}' трябва да бъде списък; беше пренебрегнат.",
    },
    "malformed-selection-entries": {
        "en": "Non-text entries in the selection for '{key}' were ignored.",
        "bg": "Записите, които не са текст, в избора за '{key}' бяха пренебрегнати.",
    },
    "malformed-draft": {
        "en": "The draft must be a JSON object; it was ignored.",
        "bg": "Черновата трябва да бъде JSON обект; беше пренебрегната.",
    },
    "malformed-name": {
        "en": "'name' must be text; it was ignored.",
        "bg": "'name' трябва да бъде текст; беше пренебрегнато.",
    },
    "malformed-sources": {
        "en": "'sources' must be a list; it was ignored.",
        "bg": "'sources' трябва да бъде списък; беше пренебрегнато.",
    },
    "malformed-use-prerequisites": {
        "en": "'preferences.usePrerequisites' must be an object; it was ignored.",
        "bg": "'preferences.usePrerequisites' трябва да бъде обект; беше пренебрегнато.",
    },
    "malformed-abilities-base": {
        "en": "'abilities.base' must be an object; it was ignored.",
        "bg": "'abilities.base' трябва да бъде обект; беше пренебрегнато.",
    },
    "ability-invalid-whole": {
        "en": "{ab} score {value!r} isn't a valid whole number; using 10 instead.",
        "bg": "Стойността {value!r} на {ab} не е валидно цяло число; вместо нея се използва 10.",
    },
    "ability-out-of-range-clamped": {
        "en": "{ab} score {n} is out of the 1-30 range; using {clamped} instead.",
        "bg": "Стойността {n} на {ab} е извън диапазона 1-30; вместо нея се използва {clamped}.",
    },
    "ability-out-of-range-clamped-final": {
        "en": ("{ab} score {n} is out of the 1-30 range; using {clamped} instead. With the species, background and feat "
               "bonuses the final {ab} score is {final}, still outside 1-30."),
        "bg": ("Стойността {n} на {ab} е извън диапазона 1-30; вместо нея се използва {clamped}. С бонусите от расата (Species), произхода (Background) и талантите (Feats) крайната стойност на {ab} е {final} и все още е извън 1-30."),
    },
    "level-invalid-whole": {
        "en": "Level {value!r} for '{cls}' isn't a valid whole number; using 1 instead.",
        "bg": "Нивото {value!r} за '{cls}' не е валидно цяло число; вместо него се използва 1.",
    },
    "equipment-qty-invalid": {
        "en": "Quantity {value!r} for '{item}' isn't a positive whole number; using 1 instead.",
        "bg": "Количеството {value!r} за '{item}' не е положително цяло число; вместо него се използва 1.",
    },
    "malformed-equipment": {
        "en": "'equipment' must be an object; it was ignored.",
        "bg": "'equipment' трябва да бъде обект; беше пренебрегнато.",
    },
    "malformed-equipment-slot-object": {
        "en": "'equipment.{key}' must be an object; it was ignored.",
        "bg": "'equipment.{key}' трябва да бъде обект; беше пренебрегнато.",
    },
    "malformed-equipment-slot-type": {
        "en": "'equipment.{key}.{field}' has the wrong type; it was ignored.",
        "bg": "'equipment.{key}.{field}' е от грешен тип; беше пренебрегнато.",
    },
    # --- resolve: ability score method ------------------------------------------------------------------------
    "point-buy-out-of-range": {
        "en": "Point buy scores must be between 8 and 15.",
        "bg": "Стойностите при разпределяне с точки (point buy) трябва да са между 8 и 15.",
    },
    "point-buy-over-budget": {
        "en": "Point buy allows 27 points but these scores cost {spent}.",
        "bg": "Разпределянето с точки (point buy) позволява 27 точки, а тези стойности струват {spent}.",
    },
    "standard-array-mismatch": {
        "en": "The standard array is 15, 14, 13, 12, 10, 8, each used once.",
        "bg": "Стандартният набор е 15, 14, 13, 12, 10, 8, като всяка стойност се използва по веднъж.",
    },
    "roll-out-of-range": {
        "en": "Rolled scores (4d6, drop the lowest) must be between 3 and 18.",
        "bg": "Хвърлените стойности (4d6, без най-ниския зар) трябва да са между 3 и 18.",
    },
    "ability-out-of-range": {
        "en": "{ab} score {score} is out of the 1-30 range.",
        "bg": "Стойността {score} на {ab} е извън диапазона 1-30.",
    },
    # --- resolve: classes, species, background ----------------------------------------------------------------
    "malformed-classes": {
        "en": "'classes' must be a list.",
        "bg": "'classes' трябва да бъде списък.",
    },
    "malformed-class-entry": {
        "en": "one or more entries in 'classes' were not objects and were ignored.",
        "bg": "един или повече записи в 'classes' не бяха обекти и бяха пренебрегнати.",
    },
    "duplicate-class": {
        "en": "'{cls}' appears more than once in classes — only the first entry is used.",
        "bg": "'{cls}' се среща повече от веднъж в classes — използва се само първият запис.",
    },
    "level-out-of-range": {
        "en": "Level {level} for '{cls}' is out of the 1-20 range; using 1 instead.",
        "bg": "Нивото {level} за '{cls}' е извън диапазона 1-20; вместо него се използва 1.",
    },
    "unknown-class": {
        "en": "Unknown class '{id}'.",
        "bg": "Непознат клас '{id}'.",
    },
    "unknown-subclass": {
        "en": "Unknown subclass '{id}'.",
        "bg": "Непознат подклас '{id}'.",
    },
    "subclass-mismatch": {
        "en": "'{subclass}' isn't a subclass of '{cls}'.",
        "bg": "'{subclass}' не е подклас на '{cls}'.",
    },
    "total-level-exceeded": {
        "en": "Total character level {total} exceeds the 20-level cap.",
        "bg": "Общото ниво на героя ({total}) надвишава ограничението от 20 нива.",
    },
    "malformed-background": {
        "en": "'background' must be an object.",
        "bg": "'background' трябва да бъде обект.",
    },
    "unknown-background": {
        "en": "Unknown background '{id}'.",
        "bg": "Непознат произход (Background) '{id}'.",
    },
    "malformed-species": {
        "en": "'species' must be an object.",
        "bg": "'species' трябва да бъде обект.",
    },
    "unknown-species": {
        "en": "Unknown species '{id}'.",
        "bg": "Непозната раса (Species) '{id}'.",
    },
    "unknown-subspecies": {
        "en": "Unknown subspecies '{id}'.",
        "bg": "Непозната подраса '{id}'.",
    },
    "subspecies-mismatch": {
        "en": "'{name}' isn't a subspecies of the selected species.",
        "bg": "'{name}' не е подраса на избраната раса (Species).",
    },
    # --- resolve: feats and prerequisites ---------------------------------------------------------------------
    "feat-duplicate-at-source": {
        "en": "{feat} was already taken, so the pick at {source} isn't applied.",
        "bg": "{feat} вече е взет, затова изборът при {source} не се прилага.",
    },
    "feat-duplicate-at-level": {
        "en": "{feat} was already taken, so the pick at {cls} level {level} isn't applied.",
        "bg": "{feat} вече е взет, затова изборът при {cls} ниво {level} не се прилага.",
    },
    "feat-prerequisite-unmet-pick": {
        "en": "{feat}'s prerequisite isn't met, so the {source} pick isn't applied.",
        "bg": "Изискването на {feat} не е изпълнено, затова изборът при {source} не се прилага.",
    },
    "feat-prerequisite-unmet": {
        "en": "{feat}'s prerequisite isn't met.",
        "bg": "Изискването на {feat} не е изпълнено.",
    },
    "feat-prerequisite-unmet-at-level": {
        "en": "{feat}'s prerequisite isn't met at {cls} level {level}, so it isn't applied.",
        "bg": "Изискването на {feat} не е изпълнено при {cls} ниво {level}, затова не се прилага.",
    },
    "multiclass-prerequisite-unmet": {
        "en": "{cls}'s multiclassing prerequisite isn't met.",
        "bg": "Изискването за мултиклас на {cls} не е изпълнено.",
    },
    "subclass-spell-school-limit": {
        "en": "{n} known spells are outside {school_a} or {school_b} but only {free} are allowed at this level.",
        "bg": ("{n} {n|познато заклинание е|познати заклинания са} извън школите {school_a} или {school_b}, "
               "а на това ниво са позволени само {free}."),
    },
    # --- resolve: equipment choices, hit points ---------------------------------------------------------------
    "malformed-equipment-choices": {
        "en": "'equipment.choices' must be an object.",
        "bg": "'equipment.choices' трябва да бъде обект.",
    },
    "malformed-equipment-added": {
        "en": "'equipment.added' must be a list.",
        "bg": "'equipment.added' трябва да бъде списък.",
    },
    "over-selected": {
        "en": "'{label}' allows {count} selection(s) but {submitted} were submitted.",
        "bg": "'{label}' позволява {count} {count|избор|избора}, но са подадени {submitted}.",
    },
    # --- the export gate (app._pending_export_problems) -------------------------------------------------------
    "export-missing-class": {
        "en": "Choose a class first.",
        "bg": "Първо изберете клас.",
    },
    "export-missing-species": {
        "en": "Choose a species first.",
        "bg": "Първо изберете раса (Species).",
    },
    "export-missing-background": {
        "en": "Choose a background first.",
        "bg": "Първо изберете произход (Background).",
    },
    "unresolved-choice": {
        "en": "'{label}' isn't fully chosen yet.",
        "bg": "'{label}' още не е избрано докрай.",
    },
}
