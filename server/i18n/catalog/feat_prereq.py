"""Feat prerequisite texts (feat eye, `GET /api/feats/<id>`): `MESSAGES[key] = {"en": template, "bg": template}`.

Same shape and template syntax as the other catalog modules, but NOT merged into `i18n.catalog.MESSAGES`: these are not
tagged engine messages (`Msg`); `text(key, lang, **params)` renders one directly, so the review sheet and the T1 term
tables, which walk the merged catalog, stay as they are.

The English templates reproduce `sheet_data._prereq_alt_text` byte for byte. Names (abilities, classes, species, feats,
features, campaigns) are parameters and stay English; free text the data carries (`other`, a species `displayEntry`) is
plain data and stays English unless a key below knows it. Style: docs/TRANSLATION-STYLE-BG.md (T1 brackets at first use).
"""
from __future__ import annotations

from i18n.messages import check_lang, format_template

MESSAGES: dict[str, dict[str, str]] = {
    "feat-prereq-level": {"en": "Level {n}", "bg": "Ниво {n} или по-високо"},
    "feat-prereq-class-level": {"en": "{cls} level {n}", "bg": "{cls} ниво {n} или по-високо"},
    "feat-prereq-ability-one": {"en": "{ability} {n}", "bg": "{ability} {n} или повече"},
    "feat-prereq-ability": {"en": "{items: or }", "bg": "{items: или }"},
    "feat-prereq-feat": {"en": "{names: or } feat", "bg": "Талант (Feat): {names: или }"},
    "feat-prereq-feature": {"en": "{names: or } feature", "bg": "Способност (Feature): {names: или }"},
    "feat-prereq-spellcasting-feature": {"en": "Spellcasting or Pact Magic feature",
                                         "bg": "Способност (Feature): Spellcasting или Pact Magic"},
    "feat-prereq-spellcasting": {"en": "The ability to cast at least one spell",
                                 "bg": "Способност да изричаш поне едно заклинание"},
    "feat-prereq-prof-shield": {"en": "Proficiency with shield", "bg": "Владеене (Proficiency) на щитове"},
    "feat-prereq-prof-armor-light": {"en": "Proficiency with light armor", "bg": "Владеене (Proficiency) на лека броня"},
    "feat-prereq-prof-armor-medium": {"en": "Proficiency with medium armor", "bg": "Владеене (Proficiency) на средна броня"},
    "feat-prereq-prof-armor-heavy": {"en": "Proficiency with heavy armor", "bg": "Владеене (Proficiency) на тежка броня"},
    "feat-prereq-prof-weapons-martial": {"en": "Proficiency with martial weapons",
                                         "bg": "Владеене (Proficiency) на бойни оръжия"},
    "feat-prereq-prof-weapons-simple": {"en": "Proficiency with simple weapons",
                                        "bg": "Владеене (Proficiency) на обикновени оръжия"},
    "feat-prereq-prof-armor": {"en": "Proficiency with {value} armor", "bg": "Владеене (Proficiency) на броня: {value}"},
    "feat-prereq-prof-weapons": {"en": "Proficiency with {value} weapons", "bg": "Владеене (Proficiency) на оръжия: {value}"},
    "feat-prereq-dragonmark-feat": {"en": "A Dragonmark feat", "bg": "Талант (Feat) Dragonmark"},
    "feat-prereq-feat-category": {"en": "A feat of a required category", "bg": "Талант (Feat) от изискваната категория"},
    "feat-prereq-campaign": {"en": "Campaign: {names:, }", "bg": "Кампания: {names:, }"},
    "feat-prereq-no-other-dragonmark": {"en": "No other dragonmark", "bg": "Без друг драконов знак (Dragonmark)"},
    "feat-prereq-special": {"en": "Special", "bg": "Специално"},
    "feat-prereq-alt-join": {"en": "; or ", "bg": "; или "},
    "feat-prereq-part-join": {"en": ", ", "bg": ", "},
}


def text(key: str, lang: str, /, **params) -> str:
    """The template `key` in `lang` ("en" or "bg") filled with `params`; a list parameter is joined by its field's separator."""
    check_lang(lang)
    return format_template(MESSAGES[key][lang], params)
