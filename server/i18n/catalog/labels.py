"""Engine-written card labels, descriptions and `unavailableReason` texts (I5).

`MESSAGES[key] = {"en": template, "bg": template}`. The English templates reproduce the engine's former strings byte for
byte (the frozen snapshot depends on it, and the engine itself compares a card label with `.key`). The Bulgarian ones keep
the same placeholders. Key families:

- `label-*`   a card label (or a piece of one); `label-prefixed` is the "{head}: {tail}" shape of a feat's or pact's card.
- `desc-*`    a card description written by the engine; `noun-*` are the nested pieces of a "Choose N <noun>." sentence
              (so the Bulgarian word order can differ), `desc-cond-*` the casting-time condition of a Wizard pick.
- `unavailable-*`  the `unavailableReason` of a card that can never be completed.

Not here, on purpose: feature / class / species / feat / spell names and the labels the data carries (a class feature name
such as "Divine Order", the text a 5etools record or a starting-equipment envelope supplies) are parameters or plain data
and stay English; engine rule paraphrases stay English too (decision E4). `{n|one|many}` is the plural filter, `{names: or }`
joins a list. Rules words follow `i18n/glossary.json` (Bulgarian: owned proficiency = "владеене", cantrip = "трик",
Weapon Mastery = "Майсторство с оръжия", Prepared Spells = "Подготвени заклинания", Spellbook = "Книга със заклинания").
T1 (owner decision 2026-11-05): a Bulgarian rules term is followed by its English term in brackets at its first occurrence in
a text ("талант (Feat)", "трик (Cantrip)"); verbs have none; `Spell Slot` and the class option names stay English without
brackets. The English terms allowed in brackets: `i18n/bracket_terms.py`.
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    # --- fixed labels ----------------------------------------------------------------------------------------------
    "label-skill-proficiencies": {"en": "Skill Proficiencies", "bg": "Владеене на умения (Skill Proficiencies)"},
    "label-tool-proficiencies": {"en": "Tool Proficiencies", "bg": "Владеене на инструменти (Tool Proficiencies)"},
    "label-choice": {"en": "Choice", "bg": "Избор"},
    "label-skill-proficiency": {"en": "Skill Proficiency", "bg": "Владеене на умение (Skill Proficiency)"},
    "label-tool-proficiency": {"en": "Tool Proficiency", "bg": "Владеене на инструмент (Tool Proficiency)"},
    "label-skill-or-tool-proficiency": {"en": "Skill or Tool Proficiency", "bg": "Владеене на умение или инструмент (Skill or Tool Proficiency)"},
    "label-tool-proficiency-category": {"en": "Tool Proficiency ({category})", "bg": "Владеене на инструмент (Tool Proficiency, {category})"},
    "label-bonus-language": {"en": "Bonus Language", "bg": "Допълнителен език"},
    "label-languages": {"en": "Languages", "bg": "Езици"},
    "label-damage-resistance": {"en": "Damage Resistance", "bg": "Устойчивост (Resistance) към щети"},
    "label-damage-type": {"en": "Damage Type", "bg": "Вид щети"},
    "label-ability-score-increase": {"en": "Ability Score Increase", "bg": "Увеличаване на характеристика (Ability Score Increase)"},
    "label-asi": {"en": "Ability Score Improvement", "bg": "Увеличение на характеристики (Ability Score Improvement)"},
    "label-lineage": {"en": "Lineage / Ancestry", "bg": "Родова линия / Потекло"},
    "label-size": {"en": "Size", "bg": "Размер"},
    "label-dragon-colour": {"en": "Dragon Colour (Draconic Ancestry)", "bg": "Цвят на дракона"},
    "label-species-cantrip": {"en": "Cantrip", "bg": "Трик (Cantrip)"},
    "label-origin-feat": {"en": "Origin Feat", "bg": "Талант от произхода (Origin Feat)"},
    "label-feat": {"en": "Feat", "bg": "Талант (Feat)"},
    "label-weapon-mastery": {"en": "Weapon Mastery", "bg": "Майсторство с оръжия (Weapon Mastery)"},
    "label-weapon-proficiencies": {"en": "Weapon Proficiencies", "bg": "Владеене на оръжия (Weapon Proficiencies)"},
    "label-cantrips-known": {"en": "Cantrips Known", "bg": "Известни трикове (Cantrips Known)"},
    "label-spells-known": {"en": "Spells Known", "bg": "Известни заклинания"},
    "label-prepared-spells": {"en": "Prepared Spells", "bg": "Подготвени заклинания"},
    "label-spellbook": {"en": "Spellbook", "bg": "Книга със заклинания"},
    "label-starting-equipment": {"en": "Starting Equipment", "bg": "Начална екипировка"},
    "label-saving-throw": {"en": "Saving Throw", "bg": "Спасително хвърляне (Saving Throw)"},
    "label-spellcasting-ability": {"en": "Spellcasting Ability", "bg": "Характеристика за заклинания (Spellcasting Ability)"},
    "label-spell-list": {"en": "Spell List", "bg": "Списък със заклинания"},
    "label-cantrip": {"en": "Cantrip", "bg": "Трик (Cantrip)"},
    "label-spell": {"en": "Spell", "bg": "Заклинание"},
    "label-cantrips": {"en": "Cantrips", "bg": "Трикове (Cantrips)"},
    "label-rituals": {"en": "Rituals", "bg": "Ритуали"},
    "label-skill": {"en": "Skill", "bg": "Умение (Skill)"},
    "label-expertise": {"en": "Expertise", "bg": "Експертиза (Expertise)"},
    "label-artisans-tools": {"en": "Artisan's Tools", "bg": "Инструменти на занаятчия"},
    "label-pact-weapon": {"en": "Pact Weapon", "bg": "Оръжие на пакта"},
    "label-circle-spells-land": {"en": "Circle Spells (land type)", "bg": "Circle Spells (вид терен)"},
    # --- attack-row notes (VF7.7a): the closed vocabulary the engine writes on `derived.attacks[].notes` ---------------------------
    "label-attack-note-two-handed": {"en": "two-handed", "bg": "двуръчно (Two-Handed)"},
    "label-attack-note-heavy": {"en": "heavy", "bg": "тежко (Heavy)"},
    "label-attack-note-ammunition": {"en": "ammunition", "bg": "боеприпаси (Ammunition)"},
    "label-attack-note-loading": {"en": "loading", "bg": "зареждане (Loading)"},
    "label-attack-note-reach": {"en": "reach", "bg": "обсег (Reach)"},
    "label-attack-note-thrown": {"en": "thrown", "bg": "хвърляемо (Thrown)"},
    "label-attack-note-gwf": {"en": "Great Weapon Fighting: reroll 1s and 2s",
                              "bg": "Great Weapon Fighting: хвърлете наново 1 и 2"},
    "label-attack-note-gwf-2024": {"en": "Great Weapon Fighting: treat 1s and 2s as 3",
                                   "bg": "Great Weapon Fighting: третирайте 1 и 2 като 3"},
    "label-attack-note-twf": {"en": "Thrown Weapon Fighting: +{n} damage when thrown",
                              "bg": "Thrown Weapon Fighting: +{n} щета при хвърляне"},
    "label-attack-note-dueling-only": {"en": "Dueling: only with no other weapon",
                                       "bg": "Dueling: само когато не държите друго оръжие"},
    "label-attack-note-dueling": {"en": "Dueling: +2 damage", "bg": "Dueling: +2 щета"},
    "label-attack-note-pact-weapon": {
        "en": "Pact weapon: proficient; Charisma for attack and damage; Necrotic, Psychic or Radiant damage allowed",
        "bg": "Pact weapon: владеете с него; Харизма за атака и щета; позволена е некротична, психична или лъчиста щета",
    },
    "label-attack-note-rage": {"en": "Rage: +{n} damage", "bg": "Rage: +{n} щета"},
    "label-attack-note-bite-replaces": {"en": "Replaces the damage of an Unarmed Strike when you bite",
                                        "bg": "Заменя щетата на Unarmed Strike, когато ухапете"},
    "label-attack-note-half-hp-advantage": {
        "en": "Advantage while you are missing half or more of your hit points",
        "bg": "предимство (Advantage), докато ви липсва половината или повече от точките живот (Hit Points)",
    },
    "label-attack-note-naga-bite": {
        "en": "On a hit the target makes a Constitution save or takes poison damage (see the trait)",
        "bg": "При попадение целта прави спасително хвърляне (Saving Throw) на Constitution или търпи отровна щета (виж чертата)",
    },
    "label-attack-note-shifted-bonus-action": {"en": "While shifted: bonus action",
                                               "bg": "Докато сте в Shifting: бонус действие (Bonus Action)"},
    # --- a stale stored pick named in a `pruned` reason (VF7.7c): EN prints the id (the frozen text), BG the label. The `!s:.0` precision
    # cuts a string to nothing, so each template names both parameters (the catalog needs equal placeholders) and prints one. --------
    "label-stale-pick": {"en": "{id!s}{label!s:.0}", "bg": "{label!s}{id!s:.0}"},
    "label-pick-join": {"en": "{parts: + }", "bg": "{parts: + }"},
    # --- class chassis descriptions (VF7.7b): the count word is a nested message (EN a word, BG a digit), the noun follows the count ---
    "label-number-1": {"en": "one", "bg": "1"},
    "label-number-2": {"en": "two", "bg": "2"},
    "label-number-3": {"en": "three", "bg": "3"},
    "label-number-4": {"en": "four", "bg": "4"},
    "label-number-5": {"en": "five", "bg": "5"},
    "desc-class-skills-from": {
        "en": "Choose {word} {n|skill|skills} from {names:, }.",
        "bg": "Изберете {word} {n|умение (Skill)|умения (Skills)} от {names:, }.",
    },
    "desc-class-skills-any": {
        "en": "Choose any {word} {n|skill|skills}.",
        "bg": "Изберете {word} {n|умение (Skill)|умения (Skills)} по ваш избор.",
    },
    "desc-class-tools-musical": {
        "en": "Choose {word} {n|musical instrument|musical instruments}.",
        "bg": "Изберете {word} {n|музикален инструмент|музикални инструмента}.",
    },
    "desc-class-tools-artisan": {
        "en": "Choose {word} {n|artisan's tool|artisan's tools}.",
        "bg": "Изберете {word} {n|инструмент на занаятчия|инструмента на занаятчия}.",
    },
    "desc-class-tool-either": {
        "en": "Choose one tool: an Artisan's Tool or a Musical Instrument.",
        "bg": "Изберете един инструмент: инструмент на занаятчия или музикален инструмент.",
    },
    # --- composed labels: a feature or feat name stays a parameter ----------------------------------------------------
    "label-prefixed": {"en": "{head}: {tail}", "bg": "{head}: {tail}"},
    "label-feature-level": {"en": "{name} (level {level})", "bg": "{name} (ниво {level})"},
    # --- descriptions: languages and proficiencies ---------------------------------------------------------------------
    "desc-origin-languages": {
        "en": "Your character knows Common plus two languages you choose from the Standard Languages table "
              "(Player's Handbook 2024, chapter 2).",
        "bg": "Героят ви знае Common плюс два езика, които избирате от таблицата със стандартни езици "
              "(Player's Handbook 2024, глава 2).",
    },
    "desc-replacement-language": {
        "en": "You already know {language}, so you learn one language of your choice instead.",
        "bg": "Вече знаете {language}, затова научавате вместо него един език по ваш избор.",
    },
    "label-favored-enemy-language": {"en": "Favored Enemy language", "bg": "Език за Favored Enemy"},
    "desc-favored-enemy-language": {
        "en": "You learn one language of your choice that is spoken by your favored enemies, if they speak one at all.",
        "bg": "Научавате един език по ваш избор, на който говорят враговете ви от Favored Enemy, ако изобщо говорят на някакъв.",
    },
    "desc-feat-languages": {
        "en": "Choose {n} {n|language|languages} of your choice.",
        "bg": "Изберете {n} {n|език|езика} по ваш избор.",
    },
    "desc-bonus-languages": {
        "en": "Choose {n} additional {n|language|languages} of your choice.",
        "bg": "Изберете {n} {n|допълнителен език|допълнителни езика} по ваш избор.",
    },
    "desc-feat-proficiencies": {
        "en": "Choose {n} {n|proficiency|proficiencies} of your choice.",
        "bg": "Изберете {n} {n|владеене (Proficiency)|владеения (Proficiencies)} по ваш избор.",
    },
    "desc-feat-expertise": {
        "en": "Choose {n} {n|skill|skills} you are proficient in to gain Expertise.",
        "bg": "Изберете {n} {n|умение (Skill)|умения (Skills)}, които владеете, за да получите експертиза (Expertise).",
    },
    "desc-feat-saves": {
        "en": "Choose {n} {n|ability|abilities} to gain saving throw proficiency in.",
        "bg": "Изберете {n} {n|характеристика (Ability Score)|характеристики (Ability Scores)}, в чиито спасителни хвърляния (Saving Throws) да получите владеене (Proficiency).",
    },
    "desc-weapon-proficiency-choice": {
        "en": "Choose {n} {n|weapon|weapons} you gain proficiency with.",
        "bg": "Изберете {n} {n|оръжие|оръжия}, с които получавате владеене (Proficiency).",
    },
    # --- descriptions: ability scores, damage, size, lineage, feats ------------------------------------------------------
    "desc-asi-option-one": {
        "en": "Choose one ability score improvement option.",
        "bg": "Изберете един вариант за увеличение на характеристики (Ability Score Improvement).",
    },
    "desc-asi-improvement-options": {
        "en": "Choose {n} ability score improvement {n|option|options}.",
        "bg": "Изберете {n} {n|вариант|варианта} за увеличение на характеристики (Ability Score Improvement).",
    },
    "desc-asi-increase": {
        "en": "Choose {n} ability {n|score|scores} to increase by {bonus}.",
        "bg": "Изберете {n} {n|характеристика (Ability Score), която да се увеличи|характеристики (Ability Scores), които да се увеличат} с {bonus}.",
    },
    "desc-asi": {
        "en": "Increase one ability score by 2, or two ability scores by 1 each — or take a feat instead.",
        "bg": "Увеличете една характеристика (Ability Score) с 2 или две характеристики с по 1 — или вземете талант (Feat) вместо това.",
    },
    "desc-resist-types": {
        "en": "Choose {n} damage {n|type|types} you resist.",
        "bg": "Изберете {n} {n|вид щети, на който имате|вида щети, на които имате} устойчивост (Resistance).",
    },
    "desc-resist-type": {
        "en": "Choose the damage type you resist.",
        "bg": "Изберете вида щети, на който имате устойчивост (Resistance).",
    },
    "desc-damage-type": {
        "en": "Choose the damage type this feat applies to.",
        "bg": "Изберете вида щети, за който важи този талант (Feat).",
    },
    "desc-giant-strike": {
        "en": "Choose the giant strike this feat grants.",
        "bg": "Изберете гигантския удар, който дава този талант (Feat).",
    },
    "desc-lineage": {
        "en": "Choose which lineage, ancestry or legacy this species has.",
        "bg": "Изберете каква родова линия, потекло или наследство има тази раса (Species).",
    },
    "desc-size": {"en": "Choose your size.", "bg": "Изберете размера си."},
    "desc-species-feat": {"en": "Choose {noun}.", "bg": "Изберете {noun}."},
    "desc-species-feats": {"en": "Choose {count} feats.", "bg": "Изберете {count} таланта (Feats)."},
    "desc-feat-or-dark-gift": {"en": "Choose {name} or a Dark Gift feat.", "bg": "Изберете {name} или талант (Feat) Dark Gift."},
    "noun-origin-feat": {"en": "an Origin feat", "bg": "талант от произхода (Origin Feat)"},
    "noun-dark-gift-feat": {"en": "a Dark Gift feat", "bg": "талант (Feat) Dark Gift"},
    "noun-feat": {"en": "a feat", "bg": "талант (Feat)"},
    "desc-fighting-style-feat": {"en": "Choose a Fighting Style feat.", "bg": "Изберете талант (Feat) Fighting Style."},
    "desc-origin-feat": {"en": "Choose an Origin feat.", "bg": "Изберете талант от произхода (Origin Feat)."},
    "desc-spell-ability": {
        "en": "Choose this feat's spellcasting ability.",
        "bg": "Изберете характеристиката (Ability Score) за заклинания на този талант (Feat).",
    },
    "desc-species-spell-ability": {
        "en": "Choose the spellcasting ability for this species' spells.",
        "bg": "Изберете характеристиката (Ability) за заклинанията на тази раса (Species).",
    },
    "desc-dragon-colour": {
        "en": "Choose the dragon of your Draconic Ancestry; it sets the damage type, area and saving throw of your Breath Weapon.",
        "bg": "Изберете дракона от таблицата за драконово потекло (Draconic Ancestry); той определя вида щети, зоната и спасителния хвърлей (Saving Throw) на дъха ви (Breath Weapon).",
    },
    "desc-species-cantrip": {
        "en": "Choose which cantrip this species knows.",
        "bg": "Изберете кой трик (Cantrip) познава тази раса (Species).",
    },
    "desc-spell-list": {
        "en": "Choose which spell list this feat draws from.",
        "bg": "Изберете от кой списък със заклинания черпи този талант (Feat).",
    },
    "desc-pick-fighting-style": {
        "en": "Learn {n} Fighting Style {n|option|options} from the fighter class. It must differ from any style you already have.",
        "bg": "Научете {n} {n|опция|опции} Fighting Style от класа fighter. Тя трябва да се различава от всеки стил, който вече имате.",
    },
    "desc-pick-maneuver": {
        "en": "Learn {n} {n|maneuver|maneuvers} from those available to the Battle Master.",
        "bg": "Научете {n} {n|маневра|маневри} от достъпните за Battle Master.",
    },
    "desc-pick-metamagic": {
        "en": "Learn {n} Metamagic {n|option|options} from the sorcerer class.",
        "bg": "Научете {n} {n|опция|опции} Metamagic от класа sorcerer.",
    },
    "desc-pick-invocation": {
        "en": "Learn {n} {n|Eldritch Invocation|Eldritch Invocations} from the warlock class. "
              "One with a prerequisite is for a Warlock who meets it.",
        "bg": "Научете {n} {n|Eldritch Invocation|Eldritch Invocations} от класа warlock. "
              "Инвокация с изискване е за Warlock, който го изпълнява.",
    },
    "desc-invocation-ability": {
        "en": "The ability you use to cast the invocation's spell (Intelligence, Wisdom or Charisma).",
        "bg": "Характеристиката (Ability Score), с която изричате заклинанието на инвокацията (Intelligence, Wisdom или Charisma).",
    },
    "desc-weapon-mastery-feat": {
        "en": "Choose {n} {n|kind|kinds} of weapon you are proficient with to use its mastery property. "
              "You can change the choice after a long rest.",
        "bg": "Изберете {n} {n|вид оръжие|вида оръжие}, с които владеете, за да използвате свойството му от Майсторство с оръжия (Weapon Mastery). Можете да смените избора след дълга почивка (Long Rest).",
    },
    "desc-weapon-mastery-class": {
        "en": "Choose {count} kinds of weapons you are proficient with to use their mastery properties. "
              "You can change one choice after a long rest.",
        "bg": "Изберете {count} вида оръжия, с които владеете, за да използвате техните свойства от Майсторство с оръжия (Weapon Mastery). Можете да смените един избор след дълга почивка (Long Rest).",
    },
    "desc-granted-automatically": {
        "en": "{names} {n|is|are} granted automatically.",
        "bg": "{names} {n|се получава|се получават} автоматично.",
    },
    "desc-granted-automatically-after": {
        "en": "{text}\n\n{names} {n|is|are} granted automatically.",
        "bg": "{text}\n\n{names} {n|се получава|се получават} автоматично.",
    },
    # --- descriptions: spells --------------------------------------------------------------------------------------------
    "desc-choose-noun": {"en": "Choose {count} {noun}.", "bg": "Изберете {count} {noun}."},
    "noun-cantrip": {"en": "{n|cantrip|cantrips}", "bg": "{n|трик (Cantrip)|трика (Cantrips)}"},
    "noun-spell": {"en": "{n|spell|spells}", "bg": "{n|заклинание|заклинания}"},
    "noun-spell-levels": {
        "en": "level {levels: or } {n|spell|spells}",
        "bg": "{n|заклинание|заклинания} от ниво {levels: или }",
    },
    "noun-spell-upto": {
        "en": "level-{max}-or-lower {n|spell|spells}",
        "bg": "{n|заклинание|заклинания} от ниво {max} или по-ниско",
    },
    "noun-school": {"en": "{schools: or } {noun}", "bg": "{noun} от школа {schools: или }"},
    "noun-from-list": {"en": "{noun} from the {classes: or } list", "bg": "{noun} от списъка на {classes: или }"},
    "noun-ritual": {"en": "{noun} with the Ritual tag", "bg": "{noun} с етикет Ритуал"},
    "desc-listed-spells": {
        "en": "Choose {n} {n|spell|spells} from the listed options.",
        "bg": "Изберете {n} {n|заклинание|заклинания} от изброените възможности.",
    },
    "desc-cantrips-from-list": {
        "en": "Choose {n} {n|cantrip|cantrips} from the {list} spell list.",
        "bg": "Изберете {n} {n|трик (Cantrip)|трика (Cantrips)} от списъка със заклинания на {list}.",
    },
    "desc-spells-know": {
        "en": "Choose {n} {noun} to know from the {list} spell list.",
        "bg": "Изберете {n} {noun}, които да знаете, от списъка със заклинания на {list}.",
    },
    "desc-spells-prepare": {
        "en": "Choose {n} {noun} to prepare from the {list} spell list.",
        "bg": "Изберете {n} {noun}, които да подготвите, от списъка със заклинания на {list}.",
    },
    "desc-spells-know-book": {
        "en": "Choose {n} {noun} to know from your spellbook.",
        "bg": "Изберете {n} {noun}, които да знаете, от вашата книга със заклинания.",
    },
    "desc-spells-prepare-book": {
        "en": "Choose {n} {noun} to prepare from your spellbook.",
        "bg": "Изберете {n} {noun}, които да подготвите, от вашата книга със заклинания.",
    },
    "desc-spellbook-first": {
        "en": "Choose spells for your spellbook first.",
        "bg": "Първо изберете заклинания за книгата си със заклинания.",
    },
    "desc-spells-secrets": {
        "en": "{text} Magical Secrets: up to {cap} of them may be spells of any class's list, or another "
              "class's cantrips; they count in this number.",
        "bg": "{text} Magical Secrets: до {cap} от тях може да са заклинания от списъка на кой да е клас или трикове (Cantrips) на друг клас; те се броят в това число.",
    },
    "desc-spellbook": {
        "en": "Choose {count} {noun} for your spellbook (six at level 1, two more for each Wizard level). "
              "Prepared spells are drawn from the book.",
        "bg": "Изберете {count} {noun} за книгата си със заклинания (шест на ниво 1, по две повече за всяко ниво на Wizard). "
              "Подготвените заклинания се черпят от книгата.",
    },
    "desc-mystic-arcanum": {
        "en": "Choose one level-{level} spell from the Warlock spell list as your Mystic Arcanum. "
              "You can cast it once per long rest without a spell slot.",
        "bg": "Изберете едно заклинание от ниво {level} от списъка със заклинания на Warlock за вашия Mystic Arcanum. Можете да го изречете веднъж на дълга почивка (Long Rest) без Spell Slot.",
    },
    "desc-additional-secrets": {
        "en": "{text} These picks do not count against the number of spells you know.",
        "bg": "{text} Тези избори не се броят към броя на заклинанията, които знаете.",
    },
    "desc-savant-free": {
        "en": "{text} Free spellbook spells so far: {count}. They do not count against the spellbook card.",
        "bg": "{text} Безплатни заклинания в книгата досега: {count}. Те не се броят към картата на книгата със заклинания.",
    },
    "desc-wizard-pick-prepared": {
        "en": "Choose {count} level {level} {count|spell|spells} in your spellbook{condition}. You always have them prepared.",
        "bg": "Изберете {count} {count|заклинание|заклинания} от ниво {level} във вашата книга със заклинания{condition}. "
              "Те винаги са подготвени.",
    },
    "desc-wizard-pick-cast": {
        "en": "Choose {count} level {level} {count|spell|spells} in your spellbook{condition}. You can cast them at their "
              "lowest level without a spell slot while they are prepared.",
        "bg": "Изберете {count} {count|заклинание|заклинания} от ниво {level} във вашата книга със заклинания{condition}. "
              "Можете да ги изричате на най-ниското им ниво без Spell Slot, докато са подготвени.",
    },
    "desc-wizard-pick-none": {
        "en": "No spell in your spellbook is eligible (level {level}{condition}).",
        "bg": "Няма подходящо заклинание във вашата книга със заклинания (ниво {level}{condition}).",
    },
    "desc-cond-action": {
        "en": " that have a casting time of an action",
        "bg": " с време за изпълнение действие",
    },
    "desc-cond-time": {
        "en": " that have a casting time of {time}",
        "bg": " с време за изпълнение {time}",
    },
    # --- descriptions: Warlock pact cards, equipment, choices --------------------------------------------------------------
    "desc-tome-cantrips": {
        "en": "Choose {count} cantrips from any class's spell list that you don't already have prepared. "
              "While the Book of Shadows is on your person you have them prepared and they function as Warlock spells.",
        "bg": "Изберете {count} трика (Cantrips) от списъка със заклинания на кой да е клас, които още нямате подготвени. Докато Book of Shadows е у вас, те са подготвени и действат като заклинания на Warlock.",
    },
    "desc-tome-rituals": {
        "en": "Choose {count} level 1 spells with the Ritual tag from any class's spell list that you don't already have prepared. "
              "While the Book of Shadows is on your person you have them prepared and they function as Warlock spells.",
        "bg": "Изберете {count} заклинания от ниво 1 с етикет Ритуал от списъка със заклинания на кой да е клас, които още нямате "
              "подготвени. Докато Book of Shadows е у вас, те са подготвени и действат като заклинания на Warlock.",
    },
    "desc-pact-blade": {
        "en": "Choose the Simple or Martial Melee weapon you conjure and bond with. You are proficient with it "
              "and can use your Charisma modifier for its attack and damage rolls.",
        "bg": "Изберете простото или бойното оръжие за близък бой, което призовавате и с което се свързвате. Владеете го "
              "и можете да използвате модификатора си на Charisma за хвърлянията му за атака и щети.",
    },
    "desc-choose-colon": {"en": "Choose {n}: {what}.", "bg": "Изберете {n}: {what}."},
    "desc-equipment-note": {
        "en": "{text} (Note: one or more of the original options for this choice aren't available yet and have been left out.)",
        "bg": "{text} (Забележка: една или повече от първоначалните възможности за този избор още не са налични и са пропуснати.)",
    },
    "desc-equipment-note-only": {
        "en": "(Note: one or more of the original options for this choice aren't available yet and have been left out.)",
        "bg": "(Забележка: една или повече от първоначалните възможности за този избор още не са налични и са пропуснати.)",
    },
    # --- unavailableReason ----------------------------------------------------------------------------------------------
    "unavailable-no-feat-offered": {
        "en": "No feat is offered by the selected sources, so nothing can be chosen here.",
        "bg": "Избраните източници не предлагат талант (Feat), затова тук нищо не може да се избере.",
    },
    "unavailable-no-option": {
        "en": "Nothing can be chosen here with the current character: no option is offered yet.",
        "bg": "С текущия герой тук нищо не може да се избере: още не се предлага нито една възможност.",
    },
    "unavailable-all-closed": {
        "en": "Nothing can be chosen here with the current character: every option is unavailable.",
        "bg": "С текущия герой тук нищо не може да се избере: всички възможности са недостъпни.",
    },
}
