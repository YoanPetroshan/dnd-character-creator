# Quick sheet: Bulgarian rules texts

Distilled from docs/TRANSLATION-STYLE-BG.md (the full guide wins on any conflict). Enough to translate or edit without reading the full guide.

## 1. Binding rules

1. **CLARITY FIRST.** A player reading once must know who acts, when, what roll, what result. If a faithful sentence is hard to follow, PARAPHRASE: split long sentences, drop obscuring flavour metaphors, name the creature („съществото, което току-що е успяло“, never „задействащото същество“). Rules stay exact: every number, die, condition, range, target, duration, „или“/„и“, limit. Order: trigger → effect → limit.
2. **ти**, never „вие/Ви/Ваш“. Imperatives singular: Избери, Хвърли, Направи, Докосни. Reflexive „си/своя“ when the owner is the subject.
3. **Names stay English, no bracket, invariable**: spells, items, creatures (Goblin, Dire Wolf), classes, subclasses, species as game option, feats, backgrounds, features/traits, abilities (Strength…Charisma), skills (Athletics, Perception…), maneuver and invocation names, weapon property and mastery names (Finesse, Topple…), languages (Common, Elvish), planes (Material Plane, Feywild). 2014 lower case → restore casing (Magic Missile, Dexterity).
4. **Species in running prose** = Bulgarian lower-case noun, no bracket: елфи, джуджета, хора, орки, драконородни, тифлинги, халфлинги, гномове. Kenku, Genasi, Tabaxi, Aasimar etc. stay English.
5. **Bracket rule**: Bulgarian term + English Title Case term in brackets at the FIRST occurrence per record only; later Bulgarian only. Record = one spell/trait/item/species entry; `desc` + `higherLevel` = one text; `material` and `castingCondition` each bracket on their own. Singular/plural count as the same term; a term inside a longer bracketed term counts as used. Bracket number follows the noun: „хвърлянията за атака (Attack Rolls)“.
6. **Never nested brackets** („(30 фута, 9 м)“, not „(30 фута (9 м))“); **never a bracket on a verb**, plain adjective, name, or the bare words of rule 7.
7. **Bare English, no bracket, no Bulgarian**: Spell Slot(s) (masc.; „със Spell Slot“), Advantage, Disadvantage, AC, DC, DM.
8. **spell = заклинание** (never „магия“); magic = магия; cantrip = Cantrip (stays English: „един Cantrip“, „два Cantrips“; never „трик“); cast = изричам (изричаш, изречеш).
9. **Metric in brackets**, feet kept: lookup — 5=1,5 м; 10=3; 15=4,5; 20=6; 25=7,5; 30=9; 35=10,5; 40=12; 45=13,5; 50=15; 60=18; 70=21; 90=27; 100=30; 120=36; 150=45; 200=60; 300=90; 500=150; 1000=300 м; 1 фут (0,3 м); else ×0,3. Miles ×1,6 (1 миля (1,6 км)); inches ×2,5 (1 инч (2,5 см)); lb: 1 фунт (0,45 кг), 5 (2,3), 10 (4,5), 20 (9), 50 (23), 100 (45) кг. Hyphen units → phrase: „сфера с радиус 20 фута (6 м)“, „конус с дължина 60 фута (18 м)“, „куб с ръб 20 фута (6 м)“. Money: GP = „зл.“, SP ср., CP мед., EP ел., PP пл.
10. **Numbers and dice exact** (8d6, 2d8 + 4, +5, DC 15, ниво 3). Never fix; note suspicious ones. Digits stay digits, words stay words. Decimal comma; drop English thousands comma (1000); 5+ digits take a thin space („10 000“). Ordinals → „ниво 4“, „над 3“.
11. **Reader has no gender**: no participle/adjective agreeing with „ти“ („ранен“, „обгърнат“, „влязъл“). Rebuild: „Мъгла те обгръща…“.
12. Present tense for rules (never „ще“). Perfective in one-off if/when clauses („Ако изречеш“, „когато достигнеш“).
13. Pronoun gender follows the Bulgarian noun: цел → тя/нея/ѝ; същество → то/него/му; предмет → той/него/му. „ѝ“ with accent. Full article -ът/-ят only on subjects.
14. Typography: „…“ quotes, — dash with spaces, hyphen only in words/ranges (2-6).
15. **Validator quirks**: every paragraph must contain Cyrillic; same count of dice mentions as English; paragraph count per field equal (never merge/split); nulls stay null.
16. **Tables**: keep every ' | ' and cell count; dice/ranges unchanged („1d10 | Поведение през хода“); level cells read „Ниво N | …“; caption paragraph = short Bulgarian caption. Markdown tables: keep outer pipes, copy separator row as is; keep *** emphasis positions.
17. `castingCondition` = full sentence: „Изричаш го като реакция (Reaction), когато …“ Capital, full stop. `material` = noun phrase, capital, full stop.
18. „Name. text“ labels: game-content name stays English; plain labels translated („Червен. …“). Do not add "Using a Higher-Level Spell Slot"/"Cantrip Upgrade" headings.

## 2. Core terms (first-occurrence form)

Core / character
- Hit Points = точки живот (Hit Points); „1 точка живот“
- Temporary Hit Points = временни точки живот (Temporary Hit Points)
- Hit Point Maximum = максимум на точките живот (Hit Point Maximum)
- Hit Point Dice / Hit Dice = зарове за точки живот (Hit Point Dice)
- regain HP = възстановява (no bracket); heal = лекува
- Armor Class = Клас броня (Armor Class, AC); later „AC“
- Speed = скорост (no bracket); Initiative = инициатива (no bracket)
- Size = размер (no bracket)
- Proficiency = владеене (Proficiency); verb „владееш X“
- Proficiency Bonus = Бонус за владеене (Proficiency Bonus); prose „бонуса ти за владеене“
- Expertise = експертиза (Expertise)
- Ability / Ability Score = характеристика (Ability / Ability Score)
- ability modifier = модификатор на характеристика („модификатора на Strength“)
- Skill(s) = умение (Skill) / умения (Skills)
- Ability Check = проверка на характеристика (Ability Check); named: „проверка на Strength (Athletics)“, no bracket
- Saving Throw = спасително хвърляне (Saving Throw); pl. спасителни хвърляния (Saving Throws)
- Death Saving Throw = спасяване от смърт (Death Saving Throw)
- Spell Save DC = DC на спасяването от заклинание (Spell Save DC)
- Spell Attack Modifier = Бонус за атака със заклинание (Spell Attack Modifier)
- Spellcasting Ability = магическа характеристика (Spellcasting Ability)
- Heroic Inspiration = героично вдъхновение (Heroic Inspiration)
- D20 Test = D20 тест (D20 Test)
- Luck Points = точки на късмета (Luck Points)
- Ki Points = точки ки (Ki Points)
- Sorcery Points = точки на чародейство (Sorcery Points)
- Focus Points = NOT in full guide (ask / flag)
- Superiority Dice = зарове на превъзходството (Superiority Dice); sg. зар на превъзходството (Superiority Die)
- Bloodied = „половината или по-малко от максимума на точките си живот (Bloodied)“ (see 4)
- Short Rest / Long Rest = кратка почивка (Short Rest) / дълга почивка (Long Rest)
- Resistance / Immunity / Vulnerability = устойчивост (Resistance) / имунитет (Immunity) / уязвимост (Vulnerability) + „към щети от …“
- Exhaustion levels = „1 ниво на Изтощение (Exhaustion)“
- Feat = талант (Feat); Feature = способност (Feature); trait = черта
- Species / Background = раса (Species) / произход (Background); class = клас
- Invocation = инвокация (Invocation); maneuver = маневра
- Pact Weapon = оръжие на пакта (Pact Weapon)
- Weapon Mastery = майсторство с оръжия (Weapon Mastery)
- Alignment = мирогледие (Alignment); Challenge Rating = ниво на опасност (Challenge Rating)
- Carrying Capacity = носимост (Carrying Capacity)
- Senses = сетива (Senses); Passive Perception = пасивно възприятие (no bracket)
- Darkvision = тъмно зрение (Darkvision); Blindsight = сляпо зрение (Blindsight)
- Tremorsense = усещане за вибрации (Tremorsense); Truesight = истинско зрение (Truesight); Telepathy = телепатия (Telepathy)
- Breath Weapon = дъх (Breath Weapon)
- level = ниво („герой от ниво 3“, „заклинание от ниво 3“)

Actions / turn
- Action = действие (Action); Bonus Action = бонус действие (Bonus Action)
- Reaction = реакция (Reaction) (fem.: „която“)
- named actions: „действието X (Y)“: Атака (Attack), Магия (Magic), Спринт (Dash), Оттегляне (Disengage), Избягване (Dodge), Помощ (Help), Скриване (Hide), Влияние (Influence), Подготовка (Ready), Търсене (Search), Изучаване (Study), Използване (Utilize)
- Opportunity Attack = атака по възможност (Opportunity Attack)
- turn / round = ход / рунд; movement = движение

Attacks / damage
- Attack Roll = хвърляне за атака (Attack Roll); pl. хвърляния за атака (Attack Rolls)
- Melee / Ranged Attack = атака в близък бой (Melee Attack) / атака от разстояние (Ranged Attack)
- Spell Attack = атака със заклинание (Spell Attack); + „в близък бой“ / „от разстояние“
- Weapon Attack = атака с оръжие (Weapon Attack); Unarmed Strike = удар без оръжие (Unarmed Strike)
- hit / miss = попадение, улучва / пропуск, пропуска
- Critical Hit = критично попадение (Critical Hit); Damage Roll = хвърляне за щети (Damage Roll)
- damage = щети (always plural); 1 damage = „1 точка щети“
- Simple / Martial = обикновено (Simple) / бойно (Martial) оръжие
- Melee / Ranged Weapon = оръжие за близък бой (Melee Weapon) / за далечен бой (Ranged Weapon)
- Improvised Weapon = импровизирано оръжие (Improvised Weapon)
- reach = обсег (prose bare: „в обсега си“); Range = обхват (prose: „в обхвата“); Long Range = голям обсег (Long Range)
- Cover = прикритие (Cover); Half / Three-Quarters / Total = половинчато / от три четвърти / пълно прикритие

Damage types: pattern „N щети от X (Type)“, never adjective
- Acid киселина · Bludgeoning удар · Cold студ · Fire огън · Force силова енергия · Lightning мълния · Necrotic некротична енергия · Piercing пробождане · Poison отрова · Psychic психична енергия · Radiant сияйна енергия · Slashing рязане · Thunder гръм
- „щети от избрания от теб вид“; damage type = вид щети

Conditions: „има състоянието X (Condition)“ / „получава състоянието X“ (moment gained) / „състоянието приключва“; fixed masc. capitalised form
- Blinded Ослепен · Charmed Омаян · Deafened Оглушен · Exhaustion Изтощение · Frightened Уплашен · Grappled Сграбчен · Incapacitated Обезвреден · Invisible Невидим · Paralyzed Парализиран · Petrified Вкаменен · Poisoned Отровен · Prone Повален · Restrained Обездвижен · Stunned Зашеметен · Unconscious В безсъзнание

Areas, space, sizes
- Area of Effect = зона на действие (Area of Effect)
- Cone конус · Cube куб (ръб) · Cylinder цилиндър · Emanation излъчване · Line линия · Sphere сфера — all + (English)
- unoccupied space = незаето пространство; point of origin = изходна точка
- Difficult Terrain = труден терен (Difficult Terrain)
- Fly / Swim / Climb / Burrow Speed = скорост на летене / плуване / катерене / ровене (… Speed)
- Tiny миниатюрен · Small малък · Medium среден · Large голям · Huge огромен · Gargantuan гигантски (+ bracket, agree with noun)

Light / vision
- Bright Light = ярка светлина (Bright Light); Dim Light = слаба светлина (Dim Light)
- Darkness = мрак (Darkness) (spell name stays English)
- Lightly / Heavily Obscured = леко / плътно закрит (… Obscured)

Spellcasting
- Cantrip = Cantrip (English, never „трик“); Concentration = концентрация (Concentration); Ritual = ритуал (Ritual)
- Casting Time = време за изричане (Casting Time); Duration = продължителност (Duration); Components = компоненти (Components)
- Verbal / Somatic / Material = вербален / соматичен / материален компонент (…)
- Spellcasting Focus = фокус за заклинания (Spellcasting Focus)
- prepared spell = подготвено заклинание; spellbook = книга със заклинания; spell list = списък със заклинания
- Magic Item = магически предмет (Magic Item); Attunement = обвързване (Attunement); charges = заряди
- Familiar = фамилиар (Familiar); plane of existence = план на битието
- target = цел (fem.); creature = същество (neut.); object = предмет (masc.)
- willing creature = същество, което е съгласно; friendly creature = съюзническо същество
- Schools: Абюрация (Abjuration), Призоваване (Conjuration), Прорицание (Divination), Омагьосване (Enchantment), Евокация (Evocation), Илюзия (Illusion), Некромантия (Necromancy), Трансмутация (Transmutation)

Creature types (lower case in prose)
- аберация (Aberration), звяр (Beast), небесно същество (Celestial), конструкт (Construct), дракон (Dragon), елементал (Elemental), фея (Fey), изчадие (Fiend), великан (Giant), хуманоид (Humanoid), чудовище (Monstrosity), слуз (Ooze), растение (Plant), немъртъв (Undead)

## 3. Sentence patterns

1. Short or Long Rest → „кратка почивка (Short Rest) или дълга почивка (Long Rest)“
2. once per Long Rest → „… веднъж … Не можеш да го направиш отново, докато не завършиш дълга почивка (Long Rest).“ / „веднъж между две дълги почивки“
3. DC formula → „DC 8 плюс модификатора ти на X и бонуса ти за владеене (Proficiency Bonus)“
4. cast at will → „Можеш да изричаш X неограничено, без да изразходваш Spell Slot.“
5. Ki cast → „Можеш да изразходваш N точки ки (Ki Points), за да изречеш X.“ (изразходваш, never похарчиш)
6. Superiority Die → „изразходваш един зар на превъзходството (Superiority Die)“
7. within N feet → „на разстояние до N фута (X м) от теб“ (bare „на N фута“ = exactly)
8. pushed up to N ft away → „избутан до N фута (X м) далеч от теб“; exact → „избутан на N фута (X м) назад, далеч от теб“
9. unless you have X → „освен ако имаш X“ (never „освен ако нямаш“)
10. whenever A, B or C → „всеки път, когато A, когато B или когато C“; say who first
11. must do X or Y (creature chooses) → „трябва или да …, или да …“
12. choose cantrips → „Избери N Cantrips от списъка със заклинания на X.“
13. choose spells → „Избери N заклинания [от ниво L или по-ниско], които да знаеш/подготвиш, от списъка със заклинания на X.“
14. choose skills → „Избери три умения (Skills) по твой избор“; weapon → „обикновено оръжие (Simple Weapon) по твой избор“; feat → „талант (Feat) от категорията X“
15. Repeatable → „Повтаряема. Можеш да получиш тази инвокация (Invocation) повече от веднъж…“
16. until the end of your next turn → „до края на следващия ти ход“ („си“ if subject is ти); its next turn → „до края на следващия си ход“
17. until the start of your next turn → „до началото на следващия ти/си ход“
18. for the duration → „докато трае заклинанието“; until the spell ends → „до края на заклинанието“
19. ends early → „Заклинанието приключва предсрочно, ако …“
20. a creature you can see within range → „същество, което виждаш в обхвата“ (humanoid: „когото“; animal: „който“)
21. point you choose → „избрана от теб точка“ / „по твой избор“
22. save + damage → „… прави спасително хвърляне (Saving Throw) за Dexterity и получава 8d6 щети от огън (Fire) при неуспех или половината от тези щети при успех.“
23. must succeed or condition → „Целта прави спасително хвърляне (Saving Throw) за Wisdom. При неуспех тя има състоянието X …“ (short form „трябва да направи успешно …, иначе …“ only for a short result)
24. repeat save → „В края на всеки свой ход целта повтаря спасителното хвърляне. При успех заклинанието приключва за нея.“
25. DC save → „прави спасително хвърляне за Constitution с DC 15“
26. spell attack → „Направи атака със заклинание от разстояние (Ranged Spell Attack) срещу целта. При попадение целта получава 1d10 щети от огън (Fire).“
27. upcast → „Щетите се увеличават с 1d6 за всяко ниво на Spell Slot над 3.“ (healing: „Лечението се увеличава с …“)
28. 2014 upcast → „Когато изричаш това заклинание със Spell Slot от ниво 4 или по-високо, …“
29. extra target → „Можеш да насочиш заклинанието към още едно същество за всяко ниво на Spell Slot над 1.“
30. cantrip scaling → „Щетите се увеличават с 1d10, когато достигнеш ниво 5 (2d10), ниво 11 (3d10) и ниво 17 (4d10).“
31. healing → „възстановява брой точки живот (Hit Points), равен на 2d8 плюс модификатора на магическата ти характеристика (Spellcasting Ability)“
32. Advantage → „има Advantage при хвърлянията за атака (Attack Rolls) срещу …“; Disadvantage → „има Disadvantage на следващото си хвърляне за атака (Attack Roll)“
33. you can't / can't take Reactions → „не може да предприема реакции (Reactions)“ / „Не можеш да …“
34. can't be targeted by X → „X не може да бъде насочено към …“
35. Magic action → „Можеш да предприемеш действието Магия (Magic), за да …“
36. Bonus Action later turns → „В следващите си ходове можеш като бонус действие (Bonus Action) да …“
37. teleport → „Телепортираш се на разстояние до 30 фута (9 м) в незаето пространство, което виждаш.“
38. light → „излъчва ярка светлина (Bright Light) в радиус 20 фута (6 м) и слаба светлина (Dim Light) в още 20 фута (6 м) извън него“
39. worn or carried → „които никой не носи или държи“
40. Resistance → „Имаш устойчивост (Resistance) към щети от огън (Fire).“
41. Grapple → „държиш в състоянието Сграбчен (Grappled)“; until incapacitated → „докато не получиш състоянието Обезвреден (Incapacitated)“
42. missing HP → „Ако целта има по-малко точки живот от максимума си, …“
43. ≤ N → „равно на N или по-ниско“; such as → „например“
44. first time on a turn → „за пръв път в даден ход“; once per turn → „веднъж на ход“
45. any spell slot → „с всеки свой Spell Slot“; „със свои Spell Slots от подходящо ниво“
46. castingCondition → „Изричаш го като реакция (Reaction), когато те улучи хвърляне за атака (Attack Roll).“

## 4. Forbidden / wrong

- „вие“, „Ви“, „Ваш“, plural imperatives
- „предимство“, „неизгода“, „недостатък“ for Advantage/Disadvantage (lore edge = „преднина“; flaws = „слабости“)
- „магия“ for a spell; „атакуващо хвърляне“
- „огнени щети“ (adjective damage); „1 щети“ → „1 точка щети“
- „болтове“ → „стрели за арбалет“; „банда“ → „дружина“
- Bulgarian suffixes on English names („Bard-ове“) — names are invariable („по пътя на Bard“)
- nested brackets; bracket on a verb („не владееш (Proficiency)“); bracket repeated after first occurrence
- „владееш с X“ / „в X“ → „владееш X“
- gendered participles for the reader („ранен“, „обгърнат“, „влязъл“, „улучен“); „Ти си <размер>“ → „Размерът ти е …“
- „ранен“ for Bloodied
- „освен ако нямаш“ for "unless you have" (flips the rule); any comparison flipped — re-check direction of every „по-“/„или по-ниско“
- „на N фута от теб“ for "within"; „на разстояние до N фута от теб“ for "pushed away"
- „…, иначе …“ when the creature chooses between options
- „и когато … и когато“ for alternative triggers
- „задействащото същество“; „Съгласно“ at sentence start
- „да успее на“ calque; „ще получи“ future tense
- „всяко“ for "any" that picks one → „някое“
- „неспособен“ for Incapacitated; „Бяг“ for Dash; „мироглед“; „кръв“/„живот“ alone for HP
- „като“ for "such as"; „ходи“ for takes its turn → „ходът му е веднага след твоя“
- „похарчиш“ for spending points
- „3-то ниво“ → „ниво 3“; English thousands comma; "…" or «…» quotes
- metric instead of feet; computing by hand when the lookup has the value
- merging/splitting paragraphs; „fixing“ numbers

## 5. Gold example (Fireball)

EN: Each creature in a 20-foot-radius Sphere centered on that point makes a Dexterity saving throw, taking 8d6 Fire damage on a failed save or half as much damage on a successful one.
BG: Всяко същество в сфера (Sphere) с радиус 20 фута (6 м) и център тази точка прави спасително хвърляне (Saving Throw) за Dexterity и получава 8d6 щети от огън (Fire) при неуспех или половината от тези щети при успех.
EN: Flammable objects in the area that aren't being worn or carried start burning.
BG: Запалимите предмети в зоната, които никой не носи или държи, пламват.
EN (higherLevel): The damage increases by 1d6 for each spell slot level above 3.
BG: Щетите се увеличават с 1d6 за всяко ниво на Spell Slot над 3.

Rare term not here? grep -n "<english term>" docs/TRANSLATION-STYLE-BG.md
