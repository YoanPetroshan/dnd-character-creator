# Bulgarian translation style guide for rules texts (work order)

Who reads this: the translators who turn the long English rules texts into Bulgarian: spell descriptions first, then species traits and lore, item properties and class option texts. Follow this file exactly. Where it gives one rendering, use that one, even if you know a good synonym. One term, one word, everywhere.

**CLARITY FIRST (owner, 2026-11-17, overrides everything about wording).** A player who reads the Bulgarian text once must understand exactly what happens: who acts, when, what roll, what result. If a faithful sentence is hard to follow, PARAPHRASE it: split long sentences, drop flavour metaphors that only obscure ("turn its momentary uncertainty into encouragement"), name the creature instead of "the triggering creature", say "next roll" plainly. The RULES must stay exact (every number, die, condition, range, target, duration, "or"/"and", limit); the English sentence shape and flavour words need not. Prefer short sentences in game order: trigger → effect → limit. Paragraph count still stays the same (the validator checks it). See the Silvery Barbs gold example in 5.0.

The quality bar: clean, natural, literate Bulgarian that a native reader would accept in a published book. Do not translate word for word and do not clip sentences. Re-order a sentence when Bulgarian needs it. The grammar must be correct: full and short article, agreement, pronoun gender, verb aspect. The rules meaning must not change: every number, die, condition, range, target and "or"/"and" must survive.

---

## 1. Binding rules (owner decisions)

1. **Address the reader with "ти"**, never "вие": „Имаш…“, „Избери…“, „Направи атака…“, „твоя“, „си“. Imperatives are second person singular: Избери, Хвърли, Направи, Докосни.
2. **Spell, magic, cantrip.** spell = **заклинание** (заклинанието, заклинания, заклинанията); magic = **магия**; cantrip = **трик (Cantrip)** / трикове (Cantrips). Cast = **изричам** (изричаш, изречеш, изречено). Never "магия" for a spell.
3. **Names of game content stay English**, are not translated and take no brackets: spell names (Magic Missile, Greater Restoration), item names, feature and trait names used as a reference (Wild Shape, Sneak Attack), class, subclass, species, feat, background and creature names (Goblin, Wolf), **ability names** (Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma) and **skill names** (Athletics, Insight, Perception, Stealth …). Examples: „спасително хвърляне (Saving Throw) за Dexterity“, „проверка на Wisdom (Perception)“.
4. **Rules terms are Bulgarian followed by the English term in brackets**, at the **first occurrence inside one record only**; later occurrences are Bulgarian only. One record = one spell (or one trait, one item) with all its paragraphs: `desc` and `higherLevel` together count as one text. `castingCondition` and `material` are shown apart from the description, so each of them brackets its own first occurrences. Verbs, adjectives used as plain words and connecting words get no brackets („изричаш“, „телепортираш се“, „засегнатите същества“).
5. **English with no brackets**, as it is (no Bulgarian word at all): **Spell Slot / Spell Slots**, **Advantage**, **Disadvantage**, **AC**, **DC**, **DM**. (A price in GP is written „зл.“, see 4.6.) Examples: „с по-висок Spell Slot“, „Spell Slot от ниво 3“, „Имаш Advantage при спасителните хвърляния (Saving Throws) за Wisdom“, „има Disadvantage на следващото си хвърляне за атака“. Never write предимство, неизгода or недостатък for these.
6. **Distances, weights, units**: keep the number and add metric in brackets. 1 ft = 0,3 m, 5 ft = 1,5 м, Bulgarian decimal comma: „20 фута (6 м)“, „5 фута (1,5 м)“, „60 фута (18 м)“, „1 миля (1,6 км)“. Pounds: „фунта (X кг)“ at 1 lb = 0,45 kg. See the lookup table in 4.5; never compute by hand when the table has the value.
7. **Dice and numbers are kept exactly**: 8d6, 1d10, 2d8 + 4, +5, DC 15, ниво 3. Do not change, merge or "fix" a number. If a number looks wrong, keep it and write it in your hand-over notes.
8. **Reuse the app's existing terms exactly** (the term table below already contains them; the source is docs/TERMS-PROPOSAL.md, server/i18n/glossary.json and frontend/src/copy/bg.ts).
9. **Bracket spelling** is the English rules term in PHB Title Case, singular or plural to match the Bulgarian: „хвърляне за атака (Attack Roll)“, „хвърлянията за атака (Attack Rolls)“, „Клас броня (Armor Class, AC)“.
10. **Species words in running prose are Bulgarian common nouns.** When elves, dwarves, humans, orcs … are named as a kind of creature, write the Bulgarian noun in lower case, no bracket: "creatures that don't sleep, such as elves" → „същества, които не спят, като елфите“. Only a reference to the species as a game option (a heading, „раса (Species) Elf“, a prerequisite) stays English under rule 3.

---

## 2. Term table

How to use it: the **Bulgarian** column is the form for the first occurrence (with the bracket). Later in the same record write only the Bulgarian words. Bulgarian common nouns are lower case in running text (the bracket keeps its Title Case); capitalise only at a sentence start or where the column shows a capital (condition names, 2.5). "(app)" marks a wording the app already uses; it must not change.

### 2.1 Core and characters

| English | Bulgarian (first occurrence) | Notes / forms |
|---|---|---|
| Hit Points | точки живот (Hit Points) | (app). „1 точка живот“, „10 точки живот“. Never „кръв“, „живот“ alone. |
| Hit Point maximum | максимум на точките живот (Hit Point Maximum) | „максимумът на точките ти живот“ (subject), „максимума на точките ти живот“ (object). |
| Temporary Hit Points | временни точки живот (Temporary Hit Points) | |
| Hit Point Dice | Зарове за точки живот (Hit Point Dice) | (app). Lower case in prose: зарове за точки живот. |
| regain (Hit Points) | възстановява | Verb, no bracket. „възстановява 2d8 точки живот“. |
| heal / healing | лекува / лечението | Verb and noun, no bracket. |
| Armor Class | Клас броня (Armor Class, AC) | (app). Short: „AC“ alone, no bracket: „бонус +5 към AC“. |
| Proficiency | владеене (Proficiency) | (app). Verb „владееш“, no bracket. |
| Proficiency Bonus | Бонус за владеене (Proficiency Bonus) | (app). In prose: бонуса за владеене. |
| Expertise | експертиза (Expertise) | (app). |
| Ability / Ability Score | характеристика (Ability) / характеристика (Ability Score) | (app, TERMS row 27). The value is „стойността на Strength“. The ability names themselves stay English. |
| ability modifier | модификатор на характеристика | „модификатора на Strength“. No bracket. |
| Skill / Skills | умение (Skill) / умения (Skills) | (app). Skill names stay English. |
| Ability Check | проверка на характеристика (Ability Check) | (app, „проверки на характеристики (Ability Checks)“). „проверка на Strength (Athletics)“. |
| Saving Throw | спасително хвърляне (Saving Throw) | (app). Pl. спасителни хвърляния (Saving Throws). „save“ alone = спасителното хвърляне, or „при успех/неуспех“ (see 3). |
| DC | DC | No bracket, no translation: „DC 15“, „спасително хвърляне за Constitution с DC 15“. |
| Spell Save DC | DC на спасяването от заклинание (Spell Save DC) | (app). „срещу DC на спасяването от твоите заклинания“. |
| Spell Attack Modifier | Бонус за атака със заклинание (Spell Attack Modifier) | (app). |
| Spellcasting Ability | магическа характеристика (Spellcasting Ability) | (app). „модификатора на магическата ти характеристика“. |
| Initiative | инициатива | (app glossary: no bracket). |
| Speed | скорост | (app glossary: no bracket). „Скоростта ти“. |
| Advantage | Advantage | English, no bracket (owner). „имаш Advantage при…“, „с Advantage“. |
| Disadvantage | Disadvantage | English, no bracket (owner). „има Disadvantage на…“. |
| Heroic Inspiration | героично вдъхновение (Heroic Inspiration) | (app export). |
| Exhaustion level | ниво на Изтощение | „получава 1 ниво на Изтощение (Exhaustion)“, „2 нива на Изтощение“; see 2.5. |
| Short Rest / Long Rest | кратка почивка (Short Rest) / дълга почивка (Long Rest) | (app). „след кратка или дълга почивка“ brackets each at first occurrence. |
| Resistance / Immunity / Vulnerability | устойчивост (Resistance) / имунитет (Immunity) / уязвимост (Vulnerability) | (app). Always „към щети от …“. Condition immunity: „имунитет към състоянието …“. |
| Feat | талант (Feat) | (app). Feat names stay English. |
| Species / Background / Class | раса (Species) / произход (Background) / клас | (app). |
| Feature | способност (Feature) | (app). „способността (Feature) Spellcasting“. |
| level (character) | ниво | „когато достигнеш ниво 5“, „герой от ниво 3“. |
| Proficient with | владееш | Verb. |
| Death Saving Throw | спасяване от смърт (Death Saving Throw) | (app sheet: „Спасявания от смърт (Death Saves)“). Pl. спасявания от смърт. |
| Stable / Dying | стабилизиран / умиращ | Plain words. |
| Senses | сетива (Senses) | (app). |
| Darkvision | тъмно зрение (Darkvision) | (app). |
| Blindsight | сляпо зрение (Blindsight) | (app). |
| Tremorsense | усещане за вибрации (Tremorsense) | (app). |
| Truesight | истинско зрение (Truesight) | (app). |
| Telepathy | телепатия (Telepathy) | |
| Passive Perception | пасивно възприятие | (app glossary: no bracket). |
| Carrying Capacity | носимост (Carrying Capacity) | (app). |
| Encumbered | натоварване (Encumbered) | (app export). |
| Weapon Mastery | майсторство с оръжия (Weapon Mastery) | (app). Mastery property names (Cleave, Graze, Nick, Push, Sap, Slow, Topple, Vex) stay English. |
| Spell Mastery | майсторство със заклинания (Spell Mastery) | (app). |
| Breath Weapon | дъх (Breath Weapon) | (app). |
| Draconic Ancestry | драконово потекло (Draconic Ancestry) | (app). |
| Languages / Common | езици / Common | Language names stay English (Common, Draconic, Elvish). |

| Alignment | мирогледие (Alignment) | (app) „Мирогледие“; not „мироглед“ |
| Challenge Rating | ниво на опасност (Challenge Rating) | |
| Strength check (any ability) | проверка на Strength | a named ability check is „проверка на <Ability>“, no bracket; „проверка на характеристика (Ability Check)“ only when no ability is named |
| statistics (game statistics, stat block) | игрови показатели | |
| Melee weapon / Ranged weapon (the item) | оръжие за близък бой (Melee Weapon) / оръжие за далечен бой (Ranged Weapon) | |
| for the duration | докато трае заклинанието | "until the spell ends" stays „до края на заклинанието“ (2.11) |
| 1 damage | 1 точка щети | never „1 щети“ |
| for the first time on a turn | за пръв път в даден ход | not „през хода си“ |

### 2.2 Actions and the turn

| English | Bulgarian (first occurrence) | Notes / forms |
|---|---|---|
| Action | действие (Action) | (app). „take an action“ = предприемаш действие. |
| Bonus Action | бонус действие (Bonus Action) | (app). „като бонус действие“. |
| Reaction | реакция (Reaction) | (app). Feminine: „която“. „Можеш да използваш реакцията си, за да…“. |
| Magic action | действието Магия (Magic) | „предприемаш действието Магия“. Pattern for all named actions: „действието X (Y)“. |
| Attack action | действието Атака (Attack) | |
| Dash | действието Спринт (Dash) | „Спринт“, not „Бяг“: clearly the burst, not running in general. |
| Disengage | действието Оттегляне (Disengage) | |
| Dodge | действието Избягване (Dodge) | |
| Help | действието Помощ (Help) | |
| Hide | действието Скриване (Hide) | |
| Influence | действието Влияние (Influence) | |
| Ready | действието Подготовка (Ready) | „подготвено действие“ for the readied action. |
| Search | действието Търсене (Search) | |
| Study | действието Изучаване (Study) | |
| Utilize | действието Използване (Utilize) | |
| Opportunity Attack | атака по възможност (Opportunity Attack) | |
| turn | ход | „в своя ход“, „в края на хода си“. |
| round | рунд | „1 рунд“, „всеки рунд“. |
| on your turn | в своя ход | „в своя ход“ (subject = you) / „в твоя ход“ (other subject). |
| on each of your turns | във всеки свой ход | |
| on your later turns | в следващите си ходове | |
| start / end of your next turn | началото / края на следващия ти ход | Use „си“ if the subject is "ти" (see 4.2). |
| movement | движение | „използва цялото си движение“. |
| move (verb) | придвижваш се / преместваш | „преместваш“ is transitive: преместваш сферата. |
| trigger / triggering attack | задейства / атаката, която е задействала… | Plain words. |
| Surprise | изненада | „изненадан“ plain word. |

### 2.3 Attacks and damage rolls

| English | Bulgarian (first occurrence) | Notes / forms |
|---|---|---|
| attack | атака | Plain word. |
| Attack Roll | хвърляне за атака (Attack Roll) | Pl. хвърляния за атака (Attack Rolls). Never „атакуващо хвърляне“. |
| Melee Attack | атака в близък бой (Melee Attack) | |
| Ranged Attack | атака от разстояние (Ranged Attack) | |
| Spell Attack | атака със заклинание (Spell Attack) | |
| Melee Spell Attack | атака със заклинание в близък бой (Melee Spell Attack) | |
| Ranged Spell Attack | атака със заклинание от разстояние (Ranged Spell Attack) | |
| Weapon Attack | атака с оръжие (Weapon Attack) | „Melee weapon attack“ = атака с оръжие в близък бой. |
| Unarmed Strike | удар без оръжие (Unarmed Strike) | |
| hit (noun / verb) | попадение / улучва | „При попадение…“, „ако атаката улучи“. |
| miss | пропуск / пропуска | „При пропуск…“. |
| Critical Hit | критично попадение (Critical Hit) | |
| Damage Roll | хвърляне за щети (Damage Roll) | |
| damage | щети | Always plural: „получава 8d6 щети“, „половината от тези щети“. |
| deal / take damage | нанася / получава щети | „take no damage“ = не получава щети. |
| half as much damage | половината от тези щети | |
| roll (dice) | хвърляш | „хвърли 1d8“, „хвърли отново“. |
| reroll | хвърляш отново | |
| bonus / penalty | бонус / наказание | „бонус +5 към AC“, „-2 към хвърлянията“. |
| modifier | модификатор | |
| reach | обсег (Reach) | (app). The bracket only where Reach is the weapon property or a stat („Обсег (Reach): 10 фута“). In prose, bare: „в обсега си“. |
| Cover | прикритие (Cover) | |
| Half Cover | половинчато прикритие (Half Cover) | |
| Three-Quarters Cover | прикритие от три четвърти (Three-Quarters Cover) | |
| Total Cover | пълно прикритие (Total Cover) | |
| Improvised Weapon | импровизирано оръжие (Improvised Weapon) | |
| Simple / Martial weapon | обикновено (Simple) / бойно (Martial) оръжие | |
| Finesse / Light / Heavy / Versatile / Thrown / Two-Handed / Loading / Ammunition / Reach / Range | фино (Finesse) / леко (Light) / тежко (Heavy) / гъвкаво (Versatile) / хвърляемо (Thrown) / двуръчно (Two-Handed) / зареждане (Loading) / боеприпаси (Ammunition) / обсег (Reach) / обхват (Range) | Weapon properties, for item texts. Heavy, Thrown, Two-Handed, Loading, Ammunition, Reach are (app). |

### 2.4 Damage types (pattern: „щети от X (Type)“)

One pattern only: **„N щети от X (Type)“**, never „огнени щети“. Reason: the adjective form does not exist for half of the types (thunder, force, slashing) and the „от“ form reads naturally in lists: „щети от киселина, студ или огън“. Later in the record: „щети от огън“. The bracket holds only the type word.

| English | Bulgarian (first occurrence) | Notes |
|---|---|---|
| Acid damage | щети от киселина (Acid) | |
| Bludgeoning damage | щети от удар (Bludgeoning) | |
| Cold damage | щети от студ (Cold) | |
| Fire damage | щети от огън (Fire) | |
| Force damage | щети от силова енергия (Force) | „сила“ alone is ambiguous („силата на заклинанието“). |
| Lightning damage | щети от мълния (Lightning) | |
| Necrotic damage | щети от некротична енергия (Necrotic) | |
| Piercing damage | щети от пробождане (Piercing) | |
| Poison damage | щети от отрова (Poison) | |
| Psychic damage | щети от психична енергия (Psychic) | |
| Radiant damage | щети от сияйна енергия (Radiant) | |
| Slashing damage | щети от рязане (Slashing) | |
| Thunder damage | щети от гръм (Thunder) | |
| damage type | вид щети | „вида щети по твой избор“. |
| "damage of the type you chose" | щети от избрания от теб вид | |

### 2.5 Conditions (pattern: „състоянието Име (Condition)“)

A condition is a name: write it capitalised, in this fixed masculine form, after the word „състоянието“, so it never has to agree with цел (ж. р.) or същество (ср. р.). „has the X condition“ = **има състоянието X**; „gains / is subjected to“ = **получава състоянието X**; „the condition ends“ = **състоянието приключва**. When English uses the bare adjective ("the target is Prone", 2014 "is paralyzed"), still write „има състоянието Повален (Prone)“.

| English | Bulgarian (first occurrence) | Notes |
|---|---|---|
| Blinded | състоянието Ослепен (Blinded) | |
| Charmed | състоянието Омаян (Charmed) | |
| Deafened | състоянието Оглушен (Deafened) | |
| Exhaustion | състоянието Изтощение (Exhaustion) | Levels: „1 ниво на Изтощение“. |
| Frightened | състоянието Уплашен (Frightened) | |
| Grappled | състоянието Сграбчен (Grappled) | „escape the grapple“ = освобождава се от хватката. |
| Incapacitated | състоянието Обезвреден (Incapacitated) | „Обезвреден“: cannot act, not „неспособен“ (sounds like "incompetent"). |
| Invisible | състоянието Невидим (Invisible) | |
| Paralyzed | състоянието Парализиран (Paralyzed) | |
| Petrified | състоянието Вкаменен (Petrified) | |
| Poisoned | състоянието Отровен (Poisoned) | |
| Prone | състоянието Повален (Prone) | „stand up“ = изправя се. |
| Restrained | състоянието Обездвижен (Restrained) | |
| Stunned | състоянието Зашеметен (Stunned) | |
| Unconscious | състоянието В безсъзнание (Unconscious) | |
| condition | състояние | „имунитет към състоянието Омаян“. |

### 2.6 Areas of effect, space and distance

| English | Bulgarian (first occurrence) | Notes |
|---|---|---|
| Area of Effect | зона на действие (Area of Effect) | „в зоната“ later. |
| Cone | конус (Cone) | „конус с дължина 60 фута (18 м)“. |
| Cube | куб (Cube) | „куб с ръб 20 фута (6 м)“. |
| Cylinder | цилиндър (Cylinder) | „цилиндър с радиус 10 фута (3 м) и височина 40 фута (12 м)“. |
| Emanation | излъчване (Emanation) | „излъчване от 10 фута (3 м) около теб“. |
| Line | линия (Line) | „линия с дължина 100 фута (30 м) и ширина 5 фута (1,5 м)“. |
| Sphere | сфера (Sphere) | „сфера с радиус 20 фута (6 м) и център тази точка“. |
| point of origin | изходна точка | |
| centered on | и център (after a radius) / с център | |
| radius / wide / long / high | радиус / ширина / дължина / височина | Use the noun + „с“: „с радиус“. |
| space | пространство | „незаето пространство“. |
| unoccupied space | незаето пространство | |
| within N feet of | на разстояние до N фута от | „на разстояние до 30 фута (9 м) от теб“. |
| within range | в обхвата | |
| Range (spell) | обхват (Range) | (app column). The bracket only where Range is the stat name or weapon property. In prose („within range“), bare: „в обхвата“. |
| Self / Touch / Sight / Unlimited | себе си / докосване / в полезрението / неограничен | Range values. |
| line of sight / clear path | пряка видимост / свободен път | |
| Difficult Terrain | труден терен (Difficult Terrain) | „всеки фут струва 1 допълнителен фут движение“. |
| teleport | телепортираш се / телепортира | Verb, no bracket. |
| Fly Speed | скорост на летене (Fly Speed) | „Скорост на летене 60 фута (18 м)“. |
| Swim Speed | скорост на плуване (Swim Speed) | |
| Climb Speed | скорост на катерене (Climb Speed) | |
| Burrow Speed | скорост на ровене (Burrow Speed) | |
| hover | може да се рее | |
| Jump / High Jump / Long Jump | скок / скок на височина / скок на дължина | |
| fall / Falling | падане | „щети от падане“: 1d6 щети от удар за всеки 10 фута. |
| Suffocation | задушаване (Suffocation) | |
| Size | размер | (app glossary: no bracket). |
| Tiny / Small / Medium / Large / Huge / Gargantuan | миниатюрен (Tiny) / малък (Small) / среден (Medium) / голям (Large) / огромен (Huge) / гигантски (Gargantuan) | Adjectives agree with the noun: „голямо (Large) или по-малко същество“, „огромен предмет“. |

### 2.7 Light, vision and hazards

| English | Bulgarian (first occurrence) | Notes |
|---|---|---|
| Bright Light | ярка светлина (Bright Light) | |
| Dim Light | слаба светлина (Dim Light) | |
| Darkness | мрак (Darkness) | Not the spell name Darkness, which stays English. |
| Lightly Obscured | леко закрит (Lightly Obscured) | „Зоната е леко закрита (Lightly Obscured).“ |
| Heavily Obscured | плътно закрит (Heavily Obscured) | |
| Magical Darkness | магически мрак | |
| shed light | излъчва светлина | |
| Burning | горене (Burning) | The verb „start burning“ is „се запалват / пламват“, no bracket. |
| Dehydration / Malnutrition | обезводняване / недохранване | |
| Hazard | опасност | |

### 2.8 Spellcasting

| English | Bulgarian (first occurrence) | Notes |
|---|---|---|
| spell | заклинание | Never „магия“. |
| cast a spell | изричаш заклинание | (app). „Когато изричаш това заклинание“. |
| Spell Slot(s) | Spell Slot / Spell Slots | English, no bracket, masculine: „с по-висок Spell Slot“, „Spell Slot от ниво 3“, „изразходваш Spell Slot“. „Spell“ starts with [s], so the preposition is „със Spell Slot“. |
| spell slot level | ниво на Spell Slot | „за всяко ниво на Spell Slot над 3“. |
| spell level | ниво на заклинанието | „заклинание от ниво 3“ (not „3-то ниво“). |
| Cantrip | трик (Cantrip) | (app). |
| Cantrip Upgrade (heading) | Подобряване на трика | Heading only; see 4.1. |
| Using a Higher-Level Spell Slot (heading) | Използване на Spell Slot от по-високо ниво | Heading only; see 4.1. |
| Casting Time | време за изричане (Casting Time) | (app column „Време“). |
| Components | компоненти (Components) | (app column). |
| Verbal (V) | вербален компонент (Verbal) | Letters V, S, M stay Latin. |
| Somatic (S) | соматичен компонент (Somatic) | |
| Material (M) | материален компонент (Material) | |
| consumed (material) | заклинанието изразходва | „компонент, който заклинанието изразходва“. |
| Spellcasting Focus | фокус за заклинания (Spellcasting Focus) | Arcane Focus, Holy Symbol, Druidic Focus are item names: English. |
| Concentration | концентрация (Concentration) | (app). „докато поддържаш концентрация“, „концентрацията ти се прекъсва“. |
| Ritual | ритуал (Ritual) | (app). „да изречеш като ритуал“. |
| Duration | продължителност (Duration) | (app column). |
| Instantaneous | мигновено | Duration value. |
| up to 1 minute | до 1 минута | |
| Until Dispelled | до разсейване | „dispel“ = разсейва. |
| prepared spell | подготвено заклинание | (app). |
| Spellbook | книга със заклинания | (app). |
| known spells | известни заклинания | (app). |
| School of Magic | школа на магията | (app „Школа на магията“). |
| Abjuration | Абюрация (Abjuration) | Schools: Bulgarian name + bracket, capitalised. Абюрация, Евокация, Трансмутация are transliterations: the literal words (отблъскване, въплъщение) mean something else. |
| Conjuration | Призоваване (Conjuration) | |
| Divination | Прорицание (Divination) | |
| Enchantment | Омагьосване (Enchantment) | |
| Evocation | Евокация (Evocation) | |
| Illusion | Илюзия (Illusion) | |
| Necromancy | Некромантия (Necromancy) | |
| Transmutation | Трансмутация (Transmutation) | |
| target | цел | Feminine: целта, „нея“, „неѝ“, „своя ход“. |
| creature | същество | Neuter: съществото, „него“, „му“. |
| object | предмет | Masculine: предметът / предмета, „него“, „му“. |
| willing creature | същество, което е съгласно | Pl. същества, които са съгласни. Never start a sentence with „Съгласно“ (it reads as 'according to'). |
| ally / enemy / hostile | съюзник / враг / враждебен | |
| a creature of your choice | същество по твой избор | |
| summon / conjure | призоваваш | |
| spectral / illusory | призрачен / илюзорен | |
| magical / nonmagical | магически / немагически | |
| Magic Item | магически предмет (Magic Item) | |
| Attunement | обвързване (Attunement) | „изисква обвързване“, „обвързан с“. |
| charges | заряди | „1 заряд“, „3 заряда“. |
| Antimagic | антимагия | |
| Shapechange / transform | превръщаш се / приема формата | |
| Familiar | фамилиар (Familiar) | |
| Spell list | списък със заклинания | |
| Innate spellcasting | вродени заклинания | (app). |

### 2.9 Creature types (Bulgarian + bracket; lower case in prose)

| English | Bulgarian (first occurrence) | Notes / plural |
|---|---|---|
| Aberration | аберация (Aberration) | аберации |
| Beast | звяр (Beast) | зверове |
| Celestial | небесно същество (Celestial) | небесни същества |
| Construct | конструкт (Construct) | конструкти |
| Dragon | дракон (Dragon) | дракони |
| Elemental | елементал (Elemental) | елементали |
| Fey | фея (Fey) | феи |
| Fiend | изчадие (Fiend) | изчадия |
| Giant | великан (Giant) | великани |
| Humanoid | хуманоид (Humanoid) | хуманоиди |
| Monstrosity | чудовище (Monstrosity) | чудовища |
| Ooze | слуз (Ooze) | feminine: слузта; pl. слузи |
| Plant | растение (Plant) | растения |
| Undead | немъртъв (Undead) | немъртви |
| creature type | вид същество | „същество от вида немъртъв (Undead)“ when a noun phrase is needed |

Creature *names* (Goblin, Wolf, Giant Spider) stay English with no bracket.

### 2.10 Planes (names stay English)

Plane names stay English, like other proper names, with no bracket: Material Plane, Ethereal Plane, Astral Plane, Shadowfell, Feywild, Elemental Plane of Fire, the Nine Hells, the Abyss, Outer Planes, Inner Planes. The common noun is Bulgarian:

| English | Bulgarian | Notes |
|---|---|---|
| plane / plane of existence | план / план на битието (Plane of Existence) | „друг план на битието“. |
| on the Ethereal Plane | в Ethereal Plane | No Bulgarian article on the English name. |
| Border Ethereal | Border Ethereal | |
| extraplanar | от друг план | |
| demiplane | полуплан | |
| portal | портал | |

### 2.11 Time

| English | Bulgarian | Notes |
|---|---|---|
| round / turn | рунд / ход | |
| minute / hour / day | минута / час / ден | „1 минута“, „10 минути“, „8 часа“, „24 часа“. |
| for the duration | докато трае заклинанието | (effect, not a heading). |
| until the spell ends | до края на заклинанието | One fixed form. |
| until the start of your next turn | до началото на следващия ти ход | „следващия си ход“ when the subject is "ти". |
| until the end of its next turn | до края на следващия си ход | subject = it. |
| at the start of each of its turns | в началото на всеки свой ход | |
| immediately | веднага | |
| once per turn | веднъж на ход | |
| once per Long Rest | веднъж между две дълги почивки | Or „веднъж, докато не завършиш дълга почивка“ when the source says "until you finish". |
| for 1 hour | за 1 час | |
| early | предсрочно | „заклинанието приключва предсрочно“. |

### 2.12 Common words and fixed phrases

| English | Bulgarian | Notes |
|---|---|---|
| choose | избираш / избери | |
| a point you choose | избрана от теб точка | |
| your choice | по твой избор | „(по твой избор)“. |
| DM's choice | по избор на DM | „DM“ stays. |
| you can see | който/която/което виждаш | Agree with the noun: „същество, което виждаш“. |
| worn or carried | никой не го носи или държи | „ако никой не го носи или държи“. |
| equal to | равен на | „брой точки живот, равен на…“. |
| plus | плюс | „2d8 плюс модификатора…“. |
| rounded down / up | закръглено надолу / нагоре | |
| at will | неограничено | |
| additional | допълнителен / още един | „още едно същество“. |
| automatically | автоматично | |
| otherwise | иначе | |
| instead | вместо това | |
| succeed / fail (a save) | успява / не успява | „при успех / при неуспех“. |
| repeats the save | повтаря спасителното хвърляне | |
| ends the spell on itself | заклинанието приключва за нея/него | |
| harmlessly | безвредно | |
| subject to | подложен на | |
| affected (creature) | засегнатото (същество) | |
| invisible (adj. for things) | невидим | Only the condition takes the bracket. |
| the spell ends | заклинанието приключва | |
| has no effect | няма ефект | |
| immune to | има имунитет към | |
| can't | не може да | |
| a number of | брой | |
| gp / GP | зл. | „на стойност поне 50 зл.“ (app „зл.“). |
| sp / cp / ep / pp | ср. / мед. / ел. / пл. | „5 ср.“ |
| worth at least 50 GP | на стойност поне 50 зл. | „5+ GP“ = „поне 5 зл.“. |

---

## 3. Phrase patterns

Use these renderings whenever the English matches; change only the variable parts. Brackets are shown as at the first occurrence; drop them if the term already appeared in the record.

| # | English | Bulgarian |
|---|---|---|
| 1 | Each creature in a 20-foot-radius Sphere centered on that point makes a Dexterity saving throw, taking 8d6 Fire damage on a failed save or half as much damage on a successful one. | Всяко същество в сфера (Sphere) с радиус 20 фута (6 м) и център тази точка прави спасително хвърляне (Saving Throw) за Dexterity и получава 8d6 щети от огън (Fire) при неуспех или половината от тези щети при успех. |
| 2 | (2014) Each creature in a 20-foot-radius sphere … must make a dexterity saving throw. A target takes 8d6 fire damage on a failed save, or half as much damage on a successful one. | Всяко същество в сфера (Sphere) … трябва да направи спасително хвърляне (Saving Throw) за Dexterity. Целта получава 8d6 щети от огън (Fire) при неуспех или половината от тези щети при успех. |
| 3 | On a failed save, the target takes 3d8 Necrotic damage and has the Poisoned condition until the end of your next turn. | При неуспех целта получава 3d8 щети от некротична енергия (Necrotic) и има състоянието Отровен (Poisoned) до края на следващия ти ход. |
| 4 | On a successful save, the target takes half as much damage only. | При успех целта получава само половината от тези щети. |
| 5 | Failed Save: 12d6 Acid damage. Successful Save: Half as much damage. | Неуспешно спасително хвърляне: 12d6 щети от киселина (Acid). Успешно спасително хвърляне: половината от тези щети. |
| 6 | The target must succeed on a Wisdom saving throw or have the Frightened condition for the duration. | Целта трябва да направи успешно спасително хвърляне (Saving Throw) за Wisdom, иначе има състоянието Уплашен (Frightened), докато трае заклинанието. |
| 7 | At the end of each of its turns, the target repeats the save, ending the spell on itself on a success. | В края на всеки свой ход целта повтаря спасителното хвърляне и при успех заклинанието приключва за нея. |
| 8 | (2014) At the end of each of its turns, the target can make another Wisdom saving throw. On a success, the spell ends on the target. | В края на всеки свой ход целта може да направи ново спасително хвърляне за Wisdom. При успех заклинанието приключва за нея. |
| 9 | Make a ranged spell attack against the target. On a hit, the target takes 1d10 Fire damage. | Направи атака със заклинание от разстояние (Ranged Spell Attack) срещу целта. При попадение целта получава 1d10 щети от огън (Fire). |
| 10 | (2014) If the attack hits, the creature takes 3d8 damage of the type you chose. | Ако атаката улучи, съществото получава 3d8 щети от избрания от теб вид. |
| 11 | The damage increases by 1d6 for each spell slot level above 3. | Щетите се увеличават с 1d6 за всяко ниво на Spell Slot над 3. |
| 12 | (2014) When you cast this spell using a spell slot of 4th level or higher, the damage increases by 1d6 for each slot level above 3rd. | Когато изричаш това заклинание със Spell Slot от ниво 4 или по-високо, щетите се увеличават с 1d6 за всяко ниво на Spell Slot над 3. |
| 13 | If you cast this spell using a spell slot of level 2 or higher, … | Ако изречеш това заклинание със Spell Slot от ниво 2 или по-високо, … |
| 14 | You can target one additional creature for each spell slot level above 1. | Можеш да насочиш заклинанието към още едно същество за всяко ниво на Spell Slot над 1. |
| 15 | The damage increases by 1d10 when you reach levels 5 (2d10), 11 (3d10), and 17 (4d10). | Щетите се увеличават с 1d10, когато достигнеш ниво 5 (2d10), ниво 11 (3d10) и ниво 17 (4d10). |
| 16 | (2014) This spell's damage increases by 1d10 when you reach 5th level (2d10), 11th level (3d10), and 17th level (4d10). | Щетите от това заклинание се увеличават с 1d10, когато достигнеш ниво 5 (2d10), ниво 11 (3d10) и ниво 17 (4d10). |
| 17 | The healing increases by 2d8 for each spell slot level above 1. | Лечението се увеличава с 2d8 за всяко ниво на Spell Slot над 1. |
| 18 | A creature you touch regains a number of Hit Points equal to 2d8 plus your spellcasting ability modifier. | Същество, което докоснеш, възстановява брой точки живот (Hit Points), равен на 2d8 плюс модификатора на магическата ти характеристика (Spellcasting Ability). |
| 19 | You gain 10 Temporary Hit Points for the duration. | Получаваш 10 временни точки живот (Temporary Hit Points), докато трае заклинанието. |
| 20 | Choose a creature you can see within range. | Избери същество, което виждаш в обхвата. |
| 21 | a creature or an object within range | същество или предмет в обхвата |
| 22 | until the spell ends | до края на заклинанието |
| 23 | for the duration | докато трае заклинанието |
| 24 | As a Bonus Action on your later turns, you can move the Sphere up to 30 feet. | В следващите си ходове можеш като бонус действие (Bonus Action) да преместиш сферата на разстояние до 30 фута (9 м). |
| 25 | You can take a Magic action to … | Можеш да предприемеш действието Магия (Magic), за да … |
| 26 | which you take when you are hit by an attack roll (castingCondition) | Изричаш го като реакция (Reaction), когато те улучи хвърляне за атака (Attack Roll). (Full sentence, capital, full stop: the app shows it on its own line; this replaces the fragment form in 4.1 and 5.2.) |
| 27 | The target has Advantage on attack rolls against … | Целта има Advantage при хвърлянията за атака (Attack Rolls) срещу … |
| 28 | … and has Disadvantage on the next attack roll it makes before the end of its next turn. | … и има Disadvantage на следващото си хвърляне за атака (Attack Roll) преди края на следващия си ход. |
| 29 | You have Resistance to Fire damage. | Имаш устойчивост (Resistance) към щети от огън (Fire). |
| 30 | The creature's Speed is halved / becomes 0. | Скоростта на съществото се намалява наполовина / става 0. |
| 31 | The target can't take Reactions until the start of its next turn. | Целта не може да предприема реакции (Reactions) до началото на следващия си ход. |
| 32 | You teleport up to 30 feet to an unoccupied space you can see. | Телепортираш се на разстояние до 30 фута (9 м) в незаето пространство, което виждаш. |
| 33 | … sheds Bright Light in a 20-foot radius and Dim Light for an additional 20 feet. | … излъчва ярка светлина (Bright Light) в радиус 20 фута (6 м) и слаба светлина (Dim Light) в още 20 фута (6 м) извън него. |
| 34 | The area is Difficult Terrain for the duration. | Докато трае заклинанието, зоната е труден терен (Difficult Terrain). |
| 35 | … makes a DC 15 Constitution saving throw. | … прави спасително хвърляне за Constitution с DC 15. |
| 36 | … adds 1d4 to any ability check using the chosen skill. | … добавя 1d4 към всяка проверка на характеристика (Ability Check) с избраното умение. |
| 37 | Flammable objects in the area that aren't being worn or carried start burning. | Запалимите предмети в зоната, които никой не носи или държи, пламват. |
| 38 | This spell has no effect on Undead or Constructs. | Това заклинание няма ефект върху немъртви (Undead) и конструкти (Constructs). |
| 39 | The spell ends early if … | Заклинанието приключва предсрочно, ако … |
| 40 | A willing creature you touch gains … | Докосваш същество, което е съгласно, и то получава … |
| 41 | (clarity) The target must succeed on a Wisdom saving throw or have the X condition … | Целта прави спасително хвърляне (Saving Throw) за Wisdom. При неуспех тя има състоянието X … (Two short sentences: save, then result. Prefer this to „трябва да направи успешно …, иначе“ whenever the result is more than a few words.) |
| 42 | (clarity) whenever A, whenever B, or whenever C, the creature makes a save | Say who first, then list the triggers: „Такова същество прави спасително хвърляне … всеки път, когато A, когато B или когато C.“ Split any sentence that carries more than one trigger and one result. |
| 43 | (clarity) the triggering creature / the triggering attack | Name it by what it did: „съществото, което току-що е успяло“, „атаката, заради която изричаш заклинанието“. Never „задействащото същество“. |
| 44 | (clarity) If the target is missing any of its Hit Points, it instead takes 1d12 … | Ако целта има по-малко точки живот от максимума си, тя получава вместо това 1d12 … (Say the plain game state, not a literal "is missing".) |

Notes on the patterns:
- **Make a save** = „прави спасително хвърляне“ (XPHB states a fact: present tense, not „трябва да“). 2014 "must make" = „трябва да направи“. "must succeed on … or" = „трябва да направи успешно … , иначе“ (not the calque „да успее на“).
- **"on a failed save / on a successful one"** = „при неуспех / при успех“ when the save is the topic of the sentence; otherwise „при неуспешно / успешно спасително хвърляне“.
- **"you can see"** follows the noun and agrees: същество, което виждаш; цел, която виждаш; предмет, който виждаш.

---

## 4. Formatting and grammar rules

### 4.1 Structure of the input
- You get a record (one spell) with up to four fields: `desc` (list of paragraphs), `higherLevel` (list of paragraphs), `material` (one string or null), `castingCondition` (one string or null). Return the same fields. **Keep the paragraph count and order exactly**: one Bulgarian paragraph per English paragraph, never merged, split or dropped. A null stays null.
- **"Name. text" paragraphs**: a short label, a full stop, then the text. If the label is a rules heading or a plain description (a colour, an option, "Failed Save", "Using a Higher-Level Spell Slot"), translate it: „Червен. …“. If the label is a game-content name (spell, feature, creature, item), keep it English: „Magic Missile. …“. Keep the full stop after the label.
- **Headings not in the text**: the catalog text does not contain "Using a Higher-Level Spell Slot" or "Cantrip Upgrade" (the app shows them). Do not add them. If one appears as a label, use „Използване на Spell Slot от по-високо ниво.“ / „Подобряване на трика.“.
- **Tables (XPHB records)**: a table is a caption paragraph followed by rows whose cells are joined with " | ". Keep every " | " and the exact number of cells in every row. Translate captions, column headings and cell text; keep dice and number ranges as they are ("1d10", "2-6", "7-8"). Example: "1d10 | Behavior for the Turn" → „1d10 | Поведение през хода“.
- **Markdown tables (2014 / SRD records)**: rows look like "| d10 | Behavior |". Keep the leading and trailing pipes and the cell count; copy the separator row "|---|---|" exactly as it is.
- **Markdown emphasis (2014 / SRD records)**: "***1. Red.*** The target …" → „***1. Червен.*** Целта …“. Keep the asterisks and their positions.
- **`material`** is a noun phrase with a capital and a full stop: "A ball of bat guano and sulfur." → „Топче от прилепно гуано и сяра.“ Prices: "A diamond worth 300+ GP, which the spell consumes." → „Диамант на стойност поне 300 зл., който заклинанието изразходва.“
- **`castingCondition`** is an English fragment that completes the casting time "1 Reaction, …". The app shows it on its own line, so translate it as a FULL SENTENCE that names the trigger: "which you take when …" → „Изричаш го като реакция (Reaction), когато ….“ Capital letter, final full stop (see pattern 26 and gold examples 5.0 and 5.2).

### 4.2 Grammar
- **Full and short article (пълен/кратък член)**: a masculine singular noun takes -ът/-ят when it is the subject (test: you can replace it with „той“), -а/-я otherwise. „Предметът пламва.“ / „Удари предмета.“ / „Ходът ти приключва.“ / „в края на хода си“. Check every masculine noun with an article.
- **Reflexive possessive „си“/„своя“**: when the owner is the subject of the clause, use „си“/„своя“, not „ти“/„неговия“. „Имаш бонус +5 към AC до началото на следващия си ход.“ (subject „ти“), but „Целта има Disadvantage до началото на следващия ти ход.“ (the turn is yours, the subject is the target).
- **Pronoun gender follows the Bulgarian noun**, not the English "it": цел → тя / нея / ѝ; същество → то / него / му; предмет → той / него / му; сфера → тя. The short dative of „тя“ is written „ѝ“ (with the grave accent).
- **Agreement**: adjectives, participles and „който/която/което/които“ agree with their noun: „засегнатите същества“, „цел, която виждаш“, „голямо (Large) или по-малко същество“.
- **Counting form**: masculine non-person nouns after a number take the counting form: „2 предмета“, „30 фута“, „3 заряда“, „5 предмета“. One: „1 фут“.
- **Verb aspect**: rules that repeat or describe a state use the imperfective (present): „Всеки път, когато целта прави хвърляне за атака…“, „получава“, „прави“. A single completed act in a conditional or temporal clause uses the perfective: „Ако изречеш това заклинание…“, „когато достигнеш ниво 5“, „Същество, което докоснеш“. „Когато изричаш това заклинание, избери…“ when the choice happens during the casting.
- **Tense**: rules are in the present, never the future: „получава“, not „ще получи“.
- **Gender-neutral "ти"**: never a gendered participle or adjective for the reader („Обвит в мъгла, ти…“, „ако си ранен“). Rebuild the sentence: „Мъгла те обгръща и…“, „ако имаш по-малко от половината си точки живот“.
- **Word order**: Bulgarian prefers the time or condition first: „До края на заклинанието можеш…“, „При попадение целта получава…“. "X you can see within range": the relative clause follows the noun and „в обхвата“ closes it: „същество, което виждаш в обхвата“, „хуманоид (Humanoid), когото виждаш в обхвата“ (not „същество в обхвата, което виждаш“).
- **Say which spell, slot or roll**: when the English "that spell", "the slot", "the spell" points to a spell other than the one described (the interrupted, duplicated or triggering spell), name it: „прекъснатото заклинание“, „дублираното заклинание“, „този Spell Slot“. „Това заклинание“ always means the spell of the record.
- **"any" picking one is „някое“**, not „всяко“: "forcing a reroll of any die roll" → „като накараш някое хвърляне на зар да бъде повторено“. „Всяко“ only for "each/every".
- **Two antecedents of different gender** (същество или предмет): do not hang a gendered „който/което“ on them; use „ако носи…“, „го“, or rebuild the clause.
- **No calques**: "succeed on a save" → „направи успешно спасително хвърляне“; "take damage" → „получава щети“; "make an attack" → „направи атака“ / „атакува“; "half as much damage" → „половината от тези щети“; "consult the table" → „виж таблицата“.

- "such as" introducing examples → „например“, not „като“ (which reads as "like/as").

- "pushed/moved up to N feet away from you" → „избутан до N фута (X м) далеч от теб“; "pushed N feet away from you" (exact) → „избутан на N фута (X м) назад, далеч от теб“. Never „на разстояние до N фута от теб“: that means it ends up WITHIN N feet of you.

- "within N feet (of X)" → „на разстояние до N фута (X м) от …“. A bare „на N фута от теб“ reads as EXACTLY N feet away and is wrong for "within".

- "must do X or Y" when the creature picks one → „трябва или да …, или да …“; never „…, иначе …“ (that turns a choice into a condition).

- An animal (звяр, животно) takes „който“; „когото“ is only for people.

- Creature and item names stay English even in lower case inside example lists ("a scimitar", "a dire wolf" → „Scimitar“, „Dire Wolf“).
- "is/while X is incapacitated" (a state) → „има състоянието …“; „получи състоянието“ only for the moment it is gained.
- "avoid doing X" → „избягва да …“, never „избягва“ + noun.

- A bare condition adjective in 2014 texts ("becomes invisible", "is charmed") is still the condition: „има състоянието Невидим (Invisible)“.

- Several alternative triggers ("whenever A, B, or C") → „всеки път, когато A, когато B или когато C“; never „и когато … и когато“ (reads as all at once).

### 4.3 Typography
- Quotes: „…“ (inner quotes ‚…‘). Never "…" or «…».
- Dash: — with spaces around it („ … — …“). A hyphen only inside a word or a range: „2-6“, „по-високо“.
- Decimal comma: „1,5 м“, „0,45 кг“. Drop the English thousands comma: "1,000 feet" → „1000 фута (300 м)“; five digits and more take a thin space: „10 000“.
- Numbers stay digits as in English: „3 същества“ if the English has "3", „три същества“ if the English has "three".
- Ordinals of the 2014 texts become plain numbers: "4th level" → „ниво 4“, "above 3rd" → „над 3“.
- **No English left** except names (rule 3), bracketed terms, the bare English terms of rule 5 (Spell Slot, Advantage, Disadvantage, AC, DC, DM) and dice.
- **Restore English casing in 2014 texts**: they write names and abilities in lower case ("magic missile", "dexterity saving throw"). Write them as names: Magic Missile, Dexterity. Bracketed terms are always Title Case.

### 4.4 The bracket rule in practice
- First occurrence in the record: „спасително хвърляне (Saving Throw)“. Second: „спасителното хвърляне“.
- A term inside a longer term counts as used: after „атака със заклинание от разстояние (Ranged Spell Attack)“, a later „атака“ needs no bracket.
- Singular / plural of the same term count as the same term.
- Never bracket a verb („телепортираш се“), a plain adjective („магически“), the bare words of rule 5, a name, or a word repeated from the same paragraph.

### 4.5 Unit lookup (use these values)

| Feet | Metric | Feet | Metric | Feet | Metric |
|---|---|---|---|---|---|
| 1 фут | 0,3 м | 35 фута | 10,5 м | 100 фута | 30 м |
| 5 фута | 1,5 м | 40 фута | 12 м | 120 фута | 36 м |
| 10 фута | 3 м | 45 фута | 13,5 м | 150 фута | 45 м |
| 15 фута | 4,5 м | 50 фута | 15 м | 200 фута | 60 м |
| 20 фута | 6 м | 60 фута | 18 м | 300 фута | 90 м |
| 25 фута | 7,5 м | 70 фута | 21 м | 500 фута | 150 м |
| 30 фута | 9 м | 90 фута | 27 м | 1000 фута | 300 м |

Other values: multiply by 0,3. Miles: 1 миля (1,6 км), 5 мили (8 км), 10 мили (16 км), 100 мили (160 км), 500 мили (800 км); otherwise ×1,6. Inches (no owner rule; decided here): 1 инч (2,5 см), 4 инча (10 см), 6 инча (15 см), 12 инча (30 см); otherwise ×2,5. Square feet: квадратни фута (×0,09 м²). Pounds: 1 фунт (0,45 кг), 5 фунта (2,3 кг), 10 фунта (4,5 кг), 20 фунта (9 кг), 50 фунта (23 кг), 100 фунта (45 кг), 500 фунта (225 кг), 1000 фунта (450 кг); up to 10 lb one decimal, above that whole kilograms. Ounces: унция (28 г). Gallons: галон (3,8 л).

Units with a hyphen in English become phrases: "20-foot-radius Sphere" → „сфера с радиус 20 фута (6 м)“, "60-foot Cone" → „конус с дължина 60 фута (18 м)“, "4-inch-diameter sphere" → „сфера с диаметър 4 инча (10 см)“. Metric only in brackets, never instead of the feet.

### 4.6 Currency
GP / gp = „зл.“ (app), SP = „ср.“, CP = „мед.“, EP = „ел.“, PP = „пл.“, no brackets.

---

## 5. Gold examples

### 5.0 Silvery Barbs (paraphrase for clarity)

**castingCondition** EN: which you take when a creature you can see within 60 feet of yourself succeeds on an attack roll, an ability check, or a saving throw

BG: Изричаш го като реакция (Reaction), когато същество, което виждаш на до 60 фута (18 м) от теб, успее с хвърляне за атака (Attack Roll), проверка на характеристика (Ability Check) или спасително хвърляне (Saving Throw).

(The field is shown on its own, so make it a full sentence that says it is the trigger.)

**desc[0]** EN: You magically distract the triggering creature and turn its momentary uncertainty into encouragement for another creature. The triggering creature must reroll the d20 and use the lower roll.

BG: Разсейваш с магия съществото, което току-що е успяло. То трябва да хвърли d20 отново и да използва по-ниския от двата резултата.

**desc[1]** EN: You can then choose a different creature you can see within range (you can choose yourself). The chosen creature has advantage on the next attack roll, ability check, or saving throw it makes within 1 minute. A creature can be empowered by only one use of this spell at a time.

BG: След това можеш да избереш друго същество, което виждаш в обхвата (може и себе си). През следващата 1 минута то има Advantage при първото си хвърляне за атака (Attack Roll), проверка на характеристика (Ability Check) или спасително хвърляне (Saving Throw). Едно същество може да има само един такъв бонус от това заклинание наведнъж.


Each example shows the record field by field: English, then the Bulgarian to deliver. These follow every rule above; copy their solutions.

### 5.1 Fireball

**desc[0]** EN: A bright streak flashes from you to a point you choose within range and then blossoms with a low roar into a fiery explosion. Each creature in a 20-foot-radius Sphere centered on that point makes a Dexterity saving throw, taking 8d6 Fire damage on a failed save or half as much damage on a successful one.

BG: Ярка светлинна ивица се стрелва от теб към точка в обхвата по твой избор и с глух тътен разцъфва в огнен взрив. Всяко същество в сфера (Sphere) с радиус 20 фута (6 м) и център тази точка прави спасително хвърляне (Saving Throw) за Dexterity и получава 8d6 щети от огън (Fire) при неуспех или половината от тези щети при успех.

**desc[1]** EN: Flammable objects in the area that aren't being worn or carried start burning.

BG: Запалимите предмети в зоната, които никой не носи или държи, пламват.

**higherLevel[0]** EN: The damage increases by 1d6 for each spell slot level above 3.

BG: Щетите се увеличават с 1d6 за всяко ниво на Spell Slot над 3.

Source note: the converter bug that made this read "8d6" is fixed (the book value 1d6 is now in the input).

**material** EN: A ball of bat guano and sulfur.

BG: Топче от прилепно гуано и сяра.

### 5.2 Shield

**desc[0]** EN: An imperceptible barrier of magical force protects you. Until the start of your next turn, you have a +5 bonus to AC, including against the triggering attack, and you take no damage from Magic Missile.

BG: Незабележима преграда от магическа сила те защитава. До началото на следващия си ход имаш бонус +5 към AC. Бонусът важи и срещу атаката, заради която изричаш заклинанието. Освен това дотогава не получаваш щети от Magic Missile.

**castingCondition** EN: which you take when you are hit by an attack roll or targeted by the Magic Missile spell

BG: Изричаш го като реакция (Reaction), когато те улучи хвърляне за атака (Attack Roll) или когато станеш цел на заклинанието Magic Missile.

(Why: „си“ because "ти" is the subject; „AC“ bare; Magic Missile is a name; castingCondition is a full sentence; long sentence split for clarity; no gendered „улучен“.)

### 5.3 Fire Bolt

**desc[0]** EN: You hurl a mote of fire at a creature or an object within range. Make a ranged spell attack against the target. On a hit, the target takes 1d10 Fire damage. A flammable object hit by this spell starts burning if it isn't being worn or carried.

BG: Мяташ огнена искра по същество или предмет в обхвата. Направи атака със заклинание от разстояние (Ranged Spell Attack) срещу целта. При попадение целта получава 1d10 щети от огън (Fire). Запалим предмет, улучен от заклинанието, пламва, ако никой не го носи или държи.

**higherLevel[0]** EN: The damage increases by 1d10 when you reach levels 5 (2d10), 11 (3d10), and 17 (4d10).

BG: Щетите се увеличават с 1d10, когато достигнеш ниво 5 (2d10), ниво 11 (3d10) и ниво 17 (4d10).

### 5.4 Hold Person

**desc[0]** EN: Choose a Humanoid that you can see within range. The target must succeed on a Wisdom saving throw or have the Paralyzed condition for the duration. At the end of each of its turns, the target repeats the save, ending the spell on itself on a success.

BG: Избери хуманоид (Humanoid), когото виждаш в обхвата. Целта прави спасително хвърляне (Saving Throw) за Wisdom. При неуспех тя има състоянието Парализиран (Paralyzed), докато трае заклинанието. В края на всеки свой ход целта повтаря спасителното хвърляне. При успех заклинанието приключва за нея.

**higherLevel[0]** EN: You can target one additional Humanoid for each spell slot level above 2.

BG: Можеш да насочиш заклинанието към още един хуманоид за всяко ниво на Spell Slot над 2.

**material** EN: A straight piece of iron.

BG: Право парче желязо.

(Why: „когото“ because a humanoid is a person; „нея“ because „целта“ is feminine; the second „хуманоид“ has no bracket, same record.)

### 5.5 Misty Step

**desc[0]** EN: Briefly surrounded by silvery mist, you teleport up to 30 feet to an unoccupied space you can see.

BG: За миг те обгръща сребриста мъгла и се телепортираш на разстояние до 30 фута (9 м) в незаето пространство, което виждаш.

(Why: the English participle "surrounded" would force a gender on "ти" („обгърнат/обгърната“); the sentence is rebuilt.)

### 5.6 Vicious Mockery (Disadvantage)

**desc[0]** EN: You unleash a string of insults laced with subtle enchantments at one creature you can see or hear within range. The target must succeed on a Wisdom saving throw or take 1d6 Psychic damage and have Disadvantage on the next attack roll it makes before the end of its next turn.

BG: Изсипваш порой от обиди, пропити с фини омагьосвания, върху едно същество, което виждаш или чуваш в обхвата. Целта трябва да направи успешно спасително хвърляне (Saving Throw) за Wisdom, иначе получава 1d6 щети от психична енергия (Psychic) и има Disadvantage на следващото си хвърляне за атака (Attack Roll) преди края на следващия си ход.

**higherLevel[0]** EN: The damage increases by 1d6 when you reach levels 5 (2d6), 11 (3d6), and 17 (4d6).

BG: Щетите се увеличават с 1d6, когато достигнеш ниво 5 (2d6), ниво 11 (3d6) и ниво 17 (4d6).

### 5.7 Faerie Fire (Advantage)

**desc[0]** EN: Objects in a 20-foot Cube within range are outlined in blue, green, or violet light (your choice). Each creature in the Cube is also outlined if it fails a Dexterity saving throw. For the duration, objects and affected creatures shed Dim Light in a 10-foot radius and can't benefit from the Invisible condition.

BG: Предметите в куб (Cube) с ръб 20 фута (6 м) в обхвата се очертават със синя, зелена или виолетова светлина (по твой избор). Всяко същество в куба също се очертава, ако спасителното му хвърляне (Saving Throw) за Dexterity е неуспешно. Докато трае заклинанието, предметите и засегнатите същества излъчват слаба светлина (Dim Light) в радиус 10 фута (3 м) и не могат да се възползват от състоянието Невидим (Invisible).

**desc[1]** EN: Attack rolls against an affected creature or object have Advantage if the attacker can see it.

BG: Хвърлянията за атака (Attack Rolls) срещу засегнато същество или предмет имат Advantage, ако нападателят го вижда.

(Why: "if it fails a save" is rebuilt around the save, avoiding the calque „не успее на“; the plural bracket follows the plural noun; „го“ covers both същество and предмет.)

### 5.8 Table row (Confusion, XPHB)

EN: 1d10 | Behavior for the Turn
BG: 1d10 | Поведение през хода

EN: 7-8 | The target doesn't move, and it takes the Attack action to make one melee attack against a random creature within reach. If none are within reach, the target takes no action.
BG: 7-8 | Целта не се придвижва и предприема действието Атака (Attack), за да направи една атака в близък бой (Melee Attack) срещу случайно същество в обсега си. Ако в обсега ѝ няма същество, целта не предприема действие.

---

## 6. Self-check before hand-over

Go through every record:

1. Same number of paragraphs, in the same order, in every field; null fields still null; every table row has the same number of " | " separators (Markdown separator rows copied as they are).
2. Every number and die is identical to the English (count them: 8d6, 20, 3, +5, DC 15 …); every distance has its metric bracket from the table in 4.5; decimal comma.
3. Names (spells, items, features, creatures, classes, species, feats, planes, ability and skill names) are English, correctly cased, without brackets.
4. Each rules term has its English bracket at its first occurrence in the record and nowhere else; `material` and `castingCondition` checked on their own.
5. Spell Slot, Advantage, Disadvantage, AC, DC, DM are bare English; the words предимство, неизгода, недостатък do not appear.
6. Every term matches the table in section 2 (one word per term): заклинание (never „магия“ for a spell), трик, изричам, щети от X, състоянието X.
7. "Ти" everywhere: no вие, ви, Ваш; imperatives in the singular; no gendered participle or adjective for the reader.
8. Full / short article checked on every masculine noun; „си“ when the owner is the subject; pronouns agree with цел / същество / предмет; „ѝ“ written with the accent.
9. Present tense for rules, perfective verbs in "if/when you do X once" clauses; no calques such as „да успее на“ (see 4.2).
10. Quotes „…“, dash —, no English words left except those allowed by rules 3 and 5.
11. Read the Bulgarian aloud once without the English: it must sound like a book, not like a translation. If a sentence is hard to follow, re-order it.
12. Anything that looks wrong in the English source (a number, a missing word, a "8d6" in an upcast line) goes into your notes, not into a silent fix.
