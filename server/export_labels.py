"""Labels of the Markdown and PDF character sheets in Bulgarian and English (XL of the bilingual plan).

``LABELS = {"bg": {...}, "en": {...}}``: both languages carry exactly the same keys (a test checks keys and
placeholders). A leaf is a template string, or a dict of such strings for a family of words (``recharge``,
``modes``, ``senses``, ``damage``). Templates use the same syntax as the engine catalog (``str.format`` fields and the
plural filter ``{n|one|many}``, see ``i18n.messages.format_template``); ``label(lang, key, **params)`` fills one in.

* English: the wording of the sources (2024 Player's Handbook first, SRD second); a rules term is the ``en`` of the
  term in ``i18n/glossary.json`` (a test pins the link for every term that has one), the rest is plain English.
* Bulgarian: byte for byte what the exports printed before they were bilingual (the baseline test pins it), so a rules
  term equals the glossary ``bg`` where the export used it. Two BG labels are English on purpose: "Spell Slots"
  (also the glossary bg and the web UI since 2026-11-05) and "Pact Magic Slots".
* Game terms the data supplies (class / species / feat / spell / item / skill / language names) are not labels: they
  stay English in both languages.

Nothing here knows about rules; the exporters (markdown_export, pdf_export, export_fields) only pick words.
"""
from __future__ import annotations

from i18n.messages import format_template

LANGS = ("bg", "en")
DEFAULT_LANG = "bg"  # the language the exports had before they were bilingual; `lang` omitted means this

_BG: dict = {
    # --- title, header line
    "unnamed": "Безименен герой",
    "filenameFallback": "герой",
    "level": "Ниво {level}",
    "background": "Произход",
    "species": "Раса",
    # --- combat statistics
    "secCombat": "Бойни показатели",
    "armorClass": "Клас броня (AC)",
    "hitPoints": "Точки живот",
    "speed": "Скорост",
    "initiative": "Инициатива",
    "passivePerception": "Пасивно възприятие",
    "passiveInsight": "Пасивна проницателност",
    "passiveInvestigation": "Пасивно разследване",
    "proficiencyBonus": "Бонус за умение",
    "feet": "{n} фута",
    # --- sections of the fixed layout
    "secAbilities": "Характеристики",
    "secSaves": "Спасителни хвърляния",
    "secSkills": "Умения",
    "secLanguages": "Езици",
    "secProficiencies": "Владеене",
    "profArmor": "Брони",
    "profWeapons": "Оръжия",
    "profTools": "Инструменти",
    "expertiseTag": "(експертиза)",
    "secEquipment": "Екипировка",
    "equipGranted": "Получена екипировка",
    "equipChosen": "Избрана екипировка",
    "equipAdded": "Инвентар",
    "equipped": "(екипиран)",
    "packContents": "съдържа: {items}",
    "worn": "Носено: {parts}",
    "wornArmor": "броня: {name}",
    "wornShield": ", щит",
    "wornNoArmor": "без броня",
    "wielded": "в ръце: основна {main}, свободна {off}",
    "handEmpty": "празна",
    # --- spells
    "secSpells": "Заклинания",
    "spellSaveDc": "Спасяване за заклинание (DC)",
    "spellAttackBonus": "Бонус за атака",
    "spellSlots": "Spell Slots",
    "pactSlots": "Pact Magic Slots",
    "slotLevel": "ниво {lvl}: {n}",
    "spellLevel": "ниво {lvl}",
    "cantrips": "Трикове",
    "spellbook": "Книга със заклинания",
    "preparedSpells": "Известни/Подготвени заклинания",
    "mysticArcanum": "Мистичен арканум",
    "spellMastery": "Майсторство със заклинания",
    "signatureSpells": "Запазени заклинания",
    "pactOfTheTome": "Книга на сенките",
    "secInnate": "Вродени заклинания",
    "innateFromLevel": ", от ниво {level}",
    "alwaysPrepared": "Винаги подготвени заклинания",
    # --- the extra blocks
    "secMovement": "Движение",
    "secSize": "Размер",
    "secSenses": "Сетива",
    "secExpertise": "Експертиза",
    "secResistances": "Съпротиви и имунитети",
    "dmgResistances": "Устойчивост към щета",
    "dmgImmunities": "Имунитет към щета",
    "dmgVulnerabilities": "Уязвимост към щета",
    "conditionImmunities": "Имунитет към състояния",
    "secAttacks": "Атаки",
    "attacksPerAction": "Атаки на действие: {n}",
    "attackVersatile": "versatile {dice}",
    "attackDueling": "с Дуел {dice}",
    "attackOffhand": "off hand {dice}",
    "attackRange": "range {range}",
    "attackMastery": "майсторство {mastery}",
    "secMasteries": "Майсторство с оръжия",
    "secClassResources": "Ресурси на класа",
    "secFeatResources": "Ресурси от таланти",
    "secSpeciesResources": "Ресурси от расата",
    "secCarrying": "Носимост",
    "overCapacity": " (претоварен)",
    "pushDragLift": ", тласкане/влачене/вдигане {n} lb",
    "secArmor": "Броня",
    "stealthDisadvantage": "Недостатък при Скритост (носена броня).",
    "secStartingGold": "Начално злато и други предмети",
    "startingGold": "Начално злато: {n} зл.",
    "secFeatures": "Черти и способности",
    "featureLevel": "ниво {level}",
    "secFeats": "Таланти",
    # --- class resources
    "unlimited": "без ограничение",
    "pool": "пул ",
    "bonus": "бонус ",
    "dc": "ТС ",
    "damageBonus": "щета +{n}",
    "healing": "лекуване {v}",
    "maxCr": "макс. CR {v}",
    "resAll": "съпротива: всички видове щета освен психична",
    "resSome": "съпротива: {types}",
    "shortRestRegains": "{n} {n|използване се възстановява|използвания се възстановяват} при кратка почивка",
    "spellSlotRegainsUse": "използване се възстановява срещу слот за заклинание",
    "bonusActionRegainsOne": "бонус действие: връща 1 зар",
    "onShortRest": "при кратка почивка",
    "maxSlotLevel": "слотове до ниво {n}",
    "slotCost": "слот ниво {lvl} за {n} т.",
    "knownForms": "известни форми: {n}",
    "metamagic": "метамагия: {items}",
    "perRageOptions": "при всяка ярост една от опциите: {items}",
    "recharge": {"long": "дълга почивка", "short": "кратка почивка", "short-or-long": "кратка или дълга почивка",
                 "turn": "на ход", "combat": "на битка", "rage": "на ярост", "other": "виж бележката"},
    "modes": {"walk": "ходене", "fly": "летене", "swim": "плуване", "climb": "катерене", "burrow": "ровене"},
    "senses": {"darkvision": "тъмно зрение", "blindsight": "сляпо зрение", "tremorsense": "усещане за вибрации",
               "truesight": "истинско зрение", "devilsSight": "дяволско зрение"},
    "damage": {"acid": "киселинни", "bludgeoning": "дробящи", "cold": "студени", "fire": "огнени", "force": "силови",
               "lightning": "мълниеносни", "necrotic": "некротични", "piercing": "пробождащи", "poison": "отровни",
               "psychic": "психични", "radiant": "лъчисти", "slashing": "режещи", "thunder": "гръмотевични"},
    # --- character details (sections and their fields)
    "detailSections": {
        "identity": "Данни за героя", "physical": "Физически характеристики", "personality": "Личност", "notes": "Бележки"},
    "detailFields": {
        "alignment": "Мирогледие", "faith": "Вяра/Божество", "lifestyle": "Начин на живот",
        "age": "Възраст", "height": "Височина", "weight": "Тегло", "eyes": "Очи", "skin": "Кожа", "hair": "Коса",
        "personalityTraits": "Черти на характера", "ideals": "Идеали", "bonds": "Връзки", "flaws": "Слабости",
        "backstory": "Предистория", "organizations": "Организации", "allies": "Съюзници", "enemies": "Врагове",
        "notes": "Допълнителни бележки"},
}

_EN: dict = {
    "unnamed": "Unnamed Character",
    "filenameFallback": "character",
    "level": "Level {level}",
    "background": "Background",
    "species": "Species",
    "secCombat": "Combat Statistics",
    "armorClass": "Armor Class",
    "hitPoints": "Hit Points",
    "speed": "Speed",
    "initiative": "Initiative",
    "passivePerception": "Passive Perception",
    "passiveInsight": "Passive Insight",
    "passiveInvestigation": "Passive Investigation",
    "proficiencyBonus": "Proficiency Bonus",
    "feet": "{n} feet",
    "secAbilities": "Ability Scores",
    "secSaves": "Saving Throws",
    "secSkills": "Skills",
    "secLanguages": "Languages",
    "secProficiencies": "Proficiencies",
    "profArmor": "Armor",
    "profWeapons": "Weapons",
    "profTools": "Tools",
    "expertiseTag": "(expertise)",
    "secEquipment": "Equipment",
    "equipGranted": "Granted Equipment",
    "equipChosen": "Chosen Equipment",
    "equipAdded": "Inventory",
    "equipped": "(equipped)",
    "packContents": "contains: {items}",
    "worn": "Worn and wielded: {parts}",
    "wornArmor": "armor: {name}",
    "wornShield": ", shield",
    "wornNoArmor": "no armor",
    "wielded": "in hands: main {main}, off {off}",
    "handEmpty": "empty",
    "secSpells": "Spells",
    "spellSaveDc": "Spell Save DC",
    "spellAttackBonus": "Spell Attack Modifier",
    "spellSlots": "Spell Slots",
    "pactSlots": "Pact Magic Slots",
    "slotLevel": "level {lvl}: {n}",
    "spellLevel": "level {lvl}",
    "cantrips": "Cantrips",
    "spellbook": "Spellbook",
    "preparedSpells": "Known/Prepared Spells",
    "mysticArcanum": "Mystic Arcanum",
    "spellMastery": "Spell Mastery",
    "signatureSpells": "Signature Spells",
    "pactOfTheTome": "Book of Shadows",
    "secInnate": "Innate Spells",
    "innateFromLevel": ", from level {level}",
    "alwaysPrepared": "Always Prepared Spells",
    "secMovement": "Movement",
    "secSize": "Size",
    "secSenses": "Special Senses",
    "secExpertise": "Expertise",
    "secResistances": "Resistances and Immunities",
    "dmgResistances": "Damage Resistance",
    "dmgImmunities": "Damage Immunity",
    "dmgVulnerabilities": "Damage Vulnerability",
    "conditionImmunities": "Condition Immunity",
    "secAttacks": "Attacks",
    "attacksPerAction": "Attacks per Action: {n}",
    "attackVersatile": "versatile {dice}",
    "attackDueling": "with Dueling {dice}",
    "attackOffhand": "off hand {dice}",
    "attackRange": "range {range}",
    "attackMastery": "mastery {mastery}",
    "secMasteries": "Weapon Mastery",
    "secClassResources": "Class Resources",
    "secFeatResources": "Feat Resources",
    "secSpeciesResources": "Species Resources",
    "secCarrying": "Carrying Capacity",
    "overCapacity": " (over capacity)",
    "pushDragLift": ", push/drag/lift {n} lb",
    "secArmor": "Armor",
    "stealthDisadvantage": "Disadvantage on Stealth (worn armor).",
    "secStartingGold": "Starting Gold and Other Items",
    "startingGold": "Starting Gold: {n} GP",
    "secFeatures": "Class Features",
    "featureLevel": "level {level}",
    "secFeats": "Feats",
    "unlimited": "unlimited",
    "pool": "pool ",
    "bonus": "bonus ",
    "dc": "DC ",
    "damageBonus": "damage +{n}",
    "healing": "healing {v}",
    "maxCr": "max CR {v}",
    "resAll": "resistance: all damage types except psychic",
    "resSome": "resistance: {types}",
    "shortRestRegains": "{n} {n|use regained|uses regained} on a short rest",
    "spellSlotRegainsUse": "a use is regained by expending a spell slot",
    "bonusActionRegainsOne": "bonus action: regain 1 die",
    "onShortRest": "on a short rest",
    "maxSlotLevel": "slots up to level {n}",
    "slotCost": "level {lvl} slot for {n} pts",
    "knownForms": "known forms: {n}",
    "metamagic": "metamagic: {items}",
    "perRageOptions": "each Rage, one of the options: {items}",
    "recharge": {"long": "long rest", "short": "short rest", "short-or-long": "short or long rest",
                 "turn": "per turn", "combat": "per combat", "rage": "per Rage", "other": "see note"},
    "modes": {"walk": "walk", "fly": "fly", "swim": "swim", "climb": "climb", "burrow": "burrow"},
    "senses": {"darkvision": "Darkvision", "blindsight": "Blindsight", "tremorsense": "Tremorsense",
               "truesight": "Truesight", "devilsSight": "Devil's Sight"},
    "damage": {t: t for t in ("acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
                              "poison", "psychic", "radiant", "slashing", "thunder")},
    "detailSections": {
        "identity": "Character Details", "physical": "Physical Characteristics", "personality": "Personality",
        "notes": "Notes"},
    "detailFields": {
        "alignment": "Alignment", "faith": "Faith/Deity", "lifestyle": "Lifestyle",
        "age": "Age", "height": "Height", "weight": "Weight", "eyes": "Eyes", "skin": "Skin", "hair": "Hair",
        "personalityTraits": "Personality Traits", "ideals": "Ideals", "bonds": "Bonds", "flaws": "Flaws",
        "backstory": "Backstory", "organizations": "Organizations", "allies": "Allies", "enemies": "Enemies",
        "notes": "Additional Notes"},
}

LABELS: dict[str, dict] = {"bg": _BG, "en": _EN}

# label key -> glossary term whose `en` (and, for BG, `bg`) the label is; tests pin the equality.
GLOSSARY_LINKS: dict[str, str] = {
    "armorClass": "armorClass", "hitPoints": "hitPoints", "speed": "speed", "initiative": "initiative",
    "passivePerception": "passivePerception", "passiveInsight": "passiveInsight",
    "passiveInvestigation": "passiveInvestigation", "proficiencyBonus": "proficiencyBonus",
    "secAbilities": "abilityScores", "secSaves": "savingThrows", "secSkills": "skills", "secLanguages": "languages",
    "secEquipment": "equipment", "background": "background", "species": "species",
    "spellSaveDc": "spellSaveDc", "spellAttackBonus": "spellAttackBonus", "cantrips": "cantrips",
    "spellbook": "spellbook", "secSize": "size", "secSenses": "senses", "secMasteries": "weaponMastery",
    "secCarrying": "carryingCapacity", "secFeats": "feats", "secFeatures": "classFeatures",
}
GLOSSARY_NESTED: dict[tuple[str, str], str] = {
    ("senses", "darkvision"): "darkvision", ("senses", "blindsight"): "blindsight",
    ("senses", "tremorsense"): "tremorsense", ("senses", "truesight"): "truesight",
    ("recharge", "long"): "longRest", ("recharge", "short"): "shortRest",
}


def check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise ValueError(f"unsupported language {lang!r}; use one of {LANGS}")
    return lang


def label(lang: str, key: str, **params) -> str:
    """The template `key` of `lang` filled in with `params`."""
    return format_template(LABELS[check_lang(lang)][key], params)


def word(lang: str, group: str, key: str, default: str | None = None) -> str:
    """One entry of a family (``recharge``, ``modes``, ``senses``, ``damage``); `default` (else `key`) when unknown."""
    return LABELS[check_lang(lang)][group].get(key, key if default is None else default)
