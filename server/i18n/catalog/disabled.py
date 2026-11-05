"""Option `disabledReason` messages (I4): why a choice-card option is closed.

`MESSAGES[key] = {"en": template, "bg": template}`. The English templates reproduce the engine's former strings byte for
byte (the frozen snapshot depends on it, and the engine itself reads `startswith("already taken")` on a reason). The
Bulgarian ones keep the same placeholders; the reason reads as a short label under the option, so it stays a phrase.
`{parts:; }` / `{items: or }` join a list parameter with the text after the colon; `{n|one|many}` is the plural filter.
Game terms and names (Expertise, Warlock, Magical Secrets, feat and spell names, ability codes) stay English, rules
words follow `i18n/glossary.json` (Bulgarian: owned proficiency = "владее", cantrip = "трик", Weapon Mastery =
"Майсторство с оръжия"). The `prereq-*` keys are pieces of a feat-prerequisite reason (nested messages).
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # --- already held / taken ----------------------------------------------------------------------------------------
    "disabled-already-known": {"en": "already known", "bg": "вече се знае"},
    "disabled-already-proficient": {"en": "already proficient", "bg": "вече се владее"},
    "disabled-already-prepared": {"en": "already prepared", "bg": "вече подготвено"},
    "disabled-in-spellbook": {"en": "already in your spellbook", "bg": "вече е във вашата книга със заклинания"},
    "disabled-always-prepared": {"en": "always prepared ({source})", "bg": "винаги подготвено ({source})"},
    "disabled-chosen-as": {"en": "chosen as {label}", "bg": "избрано като {label}"},
    "disabled-already-chosen-for": {"en": "already chosen for {name}", "bg": "вече избрано за {name}"},
    "disabled-already-chosen-for-n": {"en": "already chosen for {name} ({n})", "bg": "вече избрано за {name} ({n})"},
    "disabled-already-chosen-lessons": {
        "en": "already chosen for Lessons of the First Ones",
        "bg": "вече избрано за Lessons of the First Ones",
    },
    "disabled-already-taken": {"en": "already taken", "bg": "вече взето"},
    "disabled-already-taken-from": {"en": "already taken ({where})", "bg": "вече взето ({where})"},
    "disabled-granted-by": {"en": "already granted by {name}", "bg": "вече дадено от {name}"},
    "disabled-has-expertise": {"en": "already has Expertise", "bg": "вече има експертиза (Expertise)"},
    "disabled-not-proficient": {"en": "not proficient", "bg": "не се владее"},
    "disabled-already-mastered": {"en": "already mastered", "bg": "вече усвоено като Майсторство с оръжия (Weapon Mastery)"},
    # --- limits ----------------------------------------------------------------------------------------------------------
    "disabled-feat-ability-max": {"en": "already at maximum ({cap})", "bg": "вече на максимума ({cap})"},
    "disabled-ability-cap-20": {
        "en": "would exceed the ability score cap of 20",
        "bg": "би надвишило горната граница от 20 за характеристика (Ability Score)",
    },
    "disabled-magical-secrets-used": {
        "en": "Magical Secrets: {cap} of {cap} used",
        "bg": "Magical Secrets: използвани {cap} от {cap}",
    },
    "disabled-school-limit": {
        "en": "only {free} spell(s) may come from outside {schools: or } at this level",
        "bg": "само {free} {free|заклинание може да е|заклинания могат да са} извън {schools: или } на това ниво",
    },
    "disabled-melee-only": {"en": "melee weapons only", "bg": "само оръжия за близък бой"},
    "disabled-requires-level": {"en": "requires level {level}", "bg": "изисква ниво {level}"},
    "disabled-not-available": {"en": "not available", "bg": "не е налично"},
    # --- invocation prerequisites ------------------------------------------------------------------------------------------
    "disabled-requires-warlock-level": {"en": "requires warlock level {level}", "bg": "изисква ниво {level} на warlock"},
    "disabled-requires": {"en": "requires {name}", "bg": "изисква {name}"},
    "disabled-requires-cantrip": {"en": "requires the {spell} cantrip", "bg": "изисква трика (Cantrip) {spell}"},
    "disabled-requires-attack-cantrip": {
        "en": "requires a Warlock cantrip that requires an attack roll",
        "bg": "изисква трик (Cantrip) на Warlock, който изисква хвърляне за атака",
    },
    "disabled-requires-damage-cantrip": {
        "en": "requires a Warlock cantrip that deals damage",
        "bg": "изисква трик (Cantrip) на Warlock, който нанася щети",
    },
    "disabled-take-first": {"en": "take {name} first", "bg": "първо вземете {name}"},
    "disabled-take-first-n": {"en": "take {name} ({n}) first", "bg": "първо вземете {name} ({n})"},
    "disabled-needs-another-cantrip": {"en": "needs another eligible cantrip", "bg": "изисква още един подходящ трик (Cantrip)"},
    "disabled-needs-cantrip": {"en": "needs an eligible cantrip", "bg": "изисква подходящ трик (Cantrip)"},
    # --- Eldritch Spear / Agonizing / Repelling Blast target cantrips -------------------------------------------------------
    "disabled-target-no-attack-roll": {"en": "does not require an attack roll", "bg": "не изисква хвърляне за атака"},
    "disabled-target-no-damage": {"en": "does not deal damage", "bg": "не нанася щети"},
    "disabled-target-short-range": {"en": "range is under 10 feet", "bg": "обхватът е под 10 фута"},
    # --- feat prerequisites ----------------------------------------------------------------------------------------------------
    "disabled-prereq-unmet": {"en": "prerequisite not met", "bg": "изискването не е изпълнено"},
    "disabled-prereq-unmet-requires": {
        "en": "prerequisite not met: requires {parts:; }",
        "bg": "изискването не е изпълнено: изисква се {parts:; }",
    },
    "prereq-any-of": {"en": "{items: or }", "bg": "{items: или }"},
    "prereq-level": {"en": "character level {level}", "bg": "ниво на героя {level}"},
    "prereq-spellcasting-or-pact": {
        "en": "the Spellcasting or Pact Magic feature",
        "bg": "способността (Feature) Spellcasting или Pact Magic",
    },
    "prereq-fighting-style": {"en": "the Fighting Style feature", "bg": "способността (Feature) Fighting Style"},
    "prereq-spellcasting": {"en": "the Spellcasting feature", "bg": "способността (Feature) Spellcasting"},
    "prereq-cast-spell": {
        "en": "the ability to cast at least one spell",
        "bg": "способността да изричате поне едно заклинание",
    },
    "prereq-race": {"en": "a {name} character", "bg": "герой {name}"},
    "prereq-dragonmark": {"en": "a Dragonmark feat", "bg": "талант (Feat) Dragonmark"},
    "prereq-feat-category": {"en": "a feat of a required category", "bg": "талант (Feat) от нужната категория"},
    "prereq-martial": {"en": "martial weapon proficiency", "bg": "владеене (Proficiency) на бойни оръжия (martial)"},
    "prereq-shield": {"en": "shield proficiency", "bg": "владеене (Proficiency) на щит"},
    "prereq-armor-proficiency": {"en": "{category} armor proficiency", "bg": "владеене (Proficiency) на {category} броня"},
    "prereq-feat": {"en": "the {name} feat", "bg": "талантът (Feat) {name}"},
}
