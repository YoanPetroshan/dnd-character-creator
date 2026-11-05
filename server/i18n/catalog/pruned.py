"""Pruned-selection reason messages (I3): the `reason` of each `pruned` entry `{choiceId, reason}`.

`MESSAGES[key] = {"en": template, "bg": template}`. The English templates reproduce the engine's former f-strings byte
for byte (the frozen snapshot depends on it); the Bulgarian ones keep the same placeholders. `{names:, }` joins a list
parameter with ", " (a list of option / spell / feat names); `{n|one|many}` is the plural filter (English keeps its
`selection(s)` wording, Bulgarian picks the form). Quoted `'{label}'` / `'{id}'` are card labels and choice ids from the
engine and stay as they are; game terms and names (Expertise, invocation, Bard, Iron Mind, ability codes) stay English,
rules words follow `i18n/glossary.json` (Bulgarian: owned proficiency = "владее", Weapon Mastery = "Майсторство с оръжия").
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # --- languages -----------------------------------------------------------------------------------------------
    "pruned-language-replacement-lost": {
        "en": "'{label}': {names:, } no longer applies because you do not already know {lang}; the language selection was ignored.",
        "bg": "'{label}': {names:, } вече не се прилага, защото още не знаете {lang}; изборът на език беше пренебрегнат.",
    },
    "pruned-language-known": {
        "en": "'{label}': {names:, } is already known; the language selection was ignored.",
        "bg": "'{label}': вече се знае {names:, }; изборът на език беше пренебрегнат.",
    },
    # --- proficiencies and Expertise -------------------------------------------------------------------------------
    "pruned-proficient-source": {
        "en": "'{label}': {names:, } is already proficient ({source}); the selection was ignored.",
        "bg": "'{label}': вече се владее {names:, } ({source}); изборът беше пренебрегнат.",
    },
    "pruned-proficient-skill": {
        "en": "'{label}': {names:, } is already a proficient skill; the selection was ignored.",
        "bg": "'{label}': вече се владее като умение (Skill) {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-proficient": {
        "en": "'{label}': {names:, } is already proficient; the selection was ignored.",
        "bg": "'{label}': вече се владее {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-iron-mind": {
        "en": ("'{label}': the Wisdom saving throw is not proficient yet, so Iron Mind grants it outright and the stored "
               "selection was ignored."),
        "bg": ("'{label}': спасителното хвърляне (Saving Throw) на Мъдрост (WIS) още не се владее, затова Iron Mind го дава директно и запазеният избор беше пренебрегнат."),
    },
    "pruned-expertise-already": {
        "en": "'{label}': {names:, } already has Expertise; the selection was ignored.",
        "bg": "'{label}': вече има експертиза (Expertise) {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-expertise-not-proficient": {
        "en": "'{label}': {names:, } is no longer a proficient skill; the Expertise selection was ignored.",
        "bg": "'{label}': вече не се владее като умение (Skill) {names:, }; изборът на експертиза (Expertise) беше пренебрегнат.",
    },
    "pruned-expertise-already-chosen": {
        "en": "'{label}': {names:, } already has Expertise; the Expertise selection was ignored.",
        "bg": "'{label}': вече има експертиза (Expertise) {names:, }; изборът на експертиза беше пренебрегнат.",
    },
    # --- spells already held -----------------------------------------------------------------------------------------
    "pruned-bard-known": {
        "en": "'{label}': {names:, } is already known on the Bard's spell cards and was ignored.",
        "bg": "'{label}': вече се знае в картите със заклинания на Bard {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-known-ignored": {
        "en": "'{label}': {names:, } is already known and was ignored.",
        "bg": "'{label}': вече се знае {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-minor-illusion-required": {
        "en": "'{label}' applies only when you already know Minor Illusion; the selection was ignored.",
        "bg": "'{label}' се прилага само когато вече знаете Minor Illusion; изборът беше пренебрегнат.",
    },
    # --- invocations -------------------------------------------------------------------------------------------------
    "pruned-invocation-prereq": {
        "en": "'{label}': {names:, } no longer meets its prerequisites and was ignored.",
        "bg": "'{label}': изискванията вече не са изпълнени за {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-invocation-dependent": {
        "en": "'{label}' no longer applies: its invocation is no longer selected, so the pick was ignored.",
        "bg": "'{label}' вече не се прилага: съответният invocation вече не е избран, затова изборът беше пренебрегнат.",
    },
    "pruned-eldritch-adept-prereq": {
        "en": "'{label}': {names:, } needs a Warlock who meets its prerequisite and was ignored.",
        "bg": "'{label}': {names:, } изисква Warlock, който отговаря на изискването му; изборът беше пренебрегнат.",
    },
    # --- counts, stale picks -----------------------------------------------------------------------------------------
    "pruned-count-overflow": {
        "en": "'{id}' now allows {count} selection(s); {n} stored selection(s) no longer fit and were ignored: {names:, }.",
        "bg": ("'{id}' вече позволява {count} {count|избор|избора}; пренебрегнати са {n} "
               "{n|запазен избор, който не се побира|запазени избора, които не се побират}: {names:, }."),
    },
    "pruned-wizard-not-in-spellbook": {
        "en": "'{id}': {n} stored prepared spell(s) are not in your spellbook and were ignored: {names:, }.",
        "bg": ("'{id}': {n} {n|запазено подготвено заклинание не е|запазени подготвени заклинания не са} в книгата със "
               "заклинания (spellbook) и {n|е пренебрегнато|са пренебрегнати}: {names:, }."),
    },
    "pruned-wizard-not-in-spellbook-and-over": {
        "en": ("'{id}': {n} stored prepared spell(s) are not in your spellbook and were ignored: {names:, }. "
               "Also {m} over the allowed {count} selection(s): {rest:, }."),
        "bg": ("'{id}': {n} {n|запазено подготвено заклинание не е|запазени подготвени заклинания не са} в книгата със "
               "заклинания (spellbook) и {n|е пренебрегнато|са пренебрегнати}: {names:, }. "
               "Освен това {m} над позволените {count} {count|избор|избора}: {rest:, }."),
    },
    "pruned-stale": {
        "en": "'{id}' no longer applies to the current character and was ignored.",
        "bg": "'{id}' вече не се прилага към текущия герой и беше пренебрегнат.",
    },
    "pruned-no-longer-available": {
        "en": "'{label}': {names:, } is no longer available and was ignored.",
        "bg": "'{label}': вече не е налично {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-no-longer-offered": {
        "en": "'{label}': {names:, } is no longer offered and was ignored.",
        "bg": "'{label}': вече не се предлага {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-more": {
        "en": "...and {extra} more stale selections were ignored.",
        "bg": "...и още {extra} {extra|остарял избор е пренебрегнат|остарели избора са пренебрегнати}.",
    },
    # --- duplicates across cards ---------------------------------------------------------------------------------------
    "pruned-distinct-duplicate": {
        "en": "'{label}': {names:, } was already chosen for {name} ({n}); the selection was ignored.",
        "bg": "'{label}': вече е избрано за {name} ({n}) {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-already-taken": {
        "en": "'{label}': {names:, } was already taken ({where}); the selection was ignored.",
        "bg": "'{label}': вече е взето ({where}) {names:, }; изборът беше пренебрегнат.",
    },
    # --- weapon mastery ------------------------------------------------------------------------------------------------
    "pruned-mastered-through-class": {
        "en": "'{label}': {names:, } is already mastered through a class and was ignored.",
        "bg": "'{label}': вече е избрано за Майсторство с оръжия (Weapon Mastery) чрез клас {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-weapon-not-proficient": {
        "en": "'{label}': {names:, } is no longer a proficient weapon and was ignored.",
        "bg": "'{label}': вече не е оръжие, което владеете: {names:, }; изборът беше пренебрегнат.",
    },
    "pruned-mastery-unavailable-class": {
        "en": "'{label}': {names:, } is not an available weapon for this class and was ignored.",
        "bg": "'{label}': {names:, } не е налично оръжие за този клас; изборът беше пренебрегнат.",
    },
    "pruned-mastery-unavailable-feat": {
        "en": "'{label}': {names:, } is not an available weapon for this feat and was ignored.",
        "bg": "'{label}': {names:, } не е налично оръжие за този талант (Feat); изборът беше пренебрегнат.",
    },
    # --- ability score caps ----------------------------------------------------------------------------------------------
    "pruned-ability-at-max": {
        "en": "{name}: {ab} is already at maximum ({cap}) and the increase was ignored.",
        "bg": "{name}: {ab} вече е на максимума ({cap}); увеличението беше пренебрегнато.",
    },
    "pruned-ability-at-max-delta": {
        "en": "{name}: {ab} is already at maximum ({cap}) and the +{delta} increase was ignored.",
        "bg": "{name}: {ab} вече е на максимума ({cap}); увеличението с +{delta} беше пренебрегнато.",
    },
    "pruned-ability-capped": {
        "en": "{name}: {ab} is capped at {cap}; only +{applied} of +{bonus} applied.",
        "bg": "{name}: {ab} е ограничено до {cap}; приложени са само +{applied} от +{bonus}.",
    },
    "pruned-asi-feat-ineligible": {
        "en": "'{name}' can't be taken at this Ability Score Improvement and was ignored.",
        "bg": "'{name}' не може да се вземе при това Увеличение на характеристиките (Ability Score Improvement) и беше пренебрегнат.",
    },
    "pruned-asi-option-closed": {
        "en": "'{label}': {option} is not available ({why}) and was ignored.",
        "bg": "'{label}': {option} не е наличен: {why}; изборът беше пренебрегнат.",
    },
    "pruned-ability-closed-item": {
        "en": "{ab} is {why}",
        "bg": "{ab} е {why}",
    },
    "pruned-ability-closed": {
        "en": "'{label}': {items:, } and was ignored.",
        "bg": "'{label}': {items:, }; изборът беше пренебрегнат.",
    },
    # --- subclass, equipment ---------------------------------------------------------------------------------------------
    "pruned-subclass-unlocks": {
        "en": "'{subclass}' unlocks at {cls} level {level} and was ignored.",
        "bg": "'{subclass}' се отключва на ниво {level} на {cls} и беше пренебрегнат.",
    },
    "pruned-slot-removed": {
        "en": "{name} is no longer in the inventory and was removed from the {kind} {slot} slot.",
        "bg": "{name} вече не е в инвентара и беше премахнат от мястото ({kind}: {slot}).",
    },
}
