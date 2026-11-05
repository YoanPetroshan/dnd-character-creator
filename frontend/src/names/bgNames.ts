// Name lists for the random-name dice button (slice N1). These are CONTENT (data), not UI text, so the
// Cyrillic here is allowed by an explicit exception in copyGuards.test.ts.
//
// Scope: authentic / historical Bulgarian names only. Excluded as foreign borrowings: Turkish/Arabic roots
// (Хаджиев, Стамболов, Чолаков, Юруков, Камбуров, Дюлгеров, ...) and modern Western names.
//
// Origins:
//   bulgar    - Proto-Bulgar khans and nobles
//   slavic    - old Slavic names
//   dynastic  - medieval dynastic names, some of Cuman/Turkic root (Асен, Шишман) or disputed etymology (?)
//   christian - Greek/Hebrew/Latin roots (Иван, Георги, ...). Tagged and INCLUDED by default (owner decision,
//               2026-11-05, reversing E1); remove "christian" from DEFAULT_ORIGINS below to opt out.
//               Owner rule: no name or title of God / Christ from the Bible in any list (Христо, Христов, Христина,
//               ... must never appear); bgNames.test.ts pins this.
//   folklore  - haiduk / folk-song names (Дельо, Страхил, ...)
//   revival   - National Revival figures (Априлов, Геров, Друмев, ...)
//   literary  - characters and authors of Bulgarian literature (Под игото, Албена, Пижо, ...)
//
// N2 (2026-11-05, owner decision): everything from the research candidate tables was added except the rejected
// first names Вяра, Рая, Нона, Дойна, Иво. Trailing comments on the N2 rows: "?" = doubtful, the owner accepted it
// but it is listed for audit; then the source key (W-BGN, W-REV, W-HAJ, W-APR, W-PI, W-DEL, W-YOV, W-PEL, W-TOB, S-PI
// = a page that was fetched; "memory 0.x" / "memory" = from the researcher's memory, NOT verified online;
// "derived" = a patronymic derived from a listed first name). Surnames that are invariant in the female form
// (Боримечка, Кралич, Попович, Берон) use s(m, m, origin).
//
// Comments: "ADD" = added by the executor beyond the planner's list (for the user to review);
//           "?" = disputed or uncertain etymology/authenticity (for the user to review).

export type Origin = "bulgar" | "slavic" | "dynastic" | "christian" | "folklore" | "revival" | "literary";
export type Gender = "m" | "f";

export interface FirstName { bg: string; origin: Origin }
export interface Surname { m: string; f: string; origin: Origin }

/** The one switch: origins the dice may use. Includes christian (Иван, Георги, Иванов, Петров, ...); drop "christian" to opt out. */
export const DEFAULT_ORIGINS: readonly Origin[] = ["bulgar", "slavic", "dynastic", "christian", "folklore", "revival", "literary"];

const n = (bg: string, origin: Origin): FirstName => ({ bg, origin });
const s = (m: string, f: string, origin: Origin): Surname => ({ m, f, origin });
/** Surname with the regular female form: -ски -> -ска, otherwise + "а". */
const sr = (m: string, origin: Origin): Surname => s(m, m.endsWith("ски") ? m.slice(0, -1) + "а" : m + "а", origin);

export const MALE_FIRST: readonly FirstName[] = [
  n("Аспарух", "bulgar"), n("Кубрат", "bulgar"), n("Тервел", "bulgar"), n("Крум", "bulgar"),
  n("Омуртаг", "bulgar"), n("Маламир", "bulgar"),
  n("Пресиан", "bulgar"), // ?
  n("Борис", "bulgar"), n("Кардам", "bulgar"), n("Севар", "bulgar"), n("Телериг", "bulgar"), n("Батбаян", "bulgar"),
  n("Владимир", "slavic"), n("Светослав", "slavic"),
  n("Ивайло", "dynastic"), // ?
  n("Смилец", "dynastic"), n("Радослав", "slavic"), n("Богдан", "slavic"), n("Велко", "slavic"),
  n("Райко", "slavic"), n("Стоян", "slavic"), n("Добри", "slavic"), n("Любен", "slavic"), n("Здравко", "slavic"),
  n("Цветан", "slavic"), n("Драгомир", "slavic"), n("Боян", "slavic"), n("Радко", "slavic"),
  n("Борил", "dynastic"), // ?
  n("Асен", "dynastic"), // T: Cuman/Turkic root
  n("Шишман", "dynastic"), // T: Cuman/Turkic root
  // ADD (executor): old Slavic compounds and Proto-Bulgar khan names
  n("Веселин", "slavic"), n("Мирослав", "slavic"), n("Добромир", "slavic"), n("Станимир", "slavic"),
  n("Ратимир", "slavic"), n("Първан", "slavic"), n("Вълчан", "slavic"), n("Ясен", "slavic"),
  n("Гостун", "bulgar"), // ADD, ? (khan of the Dulo list, etymology disputed)
  n("Умор", "bulgar"), // ADD, ? (khan of the Dulo list, etymology disputed)
  // christian (included by default; no names or titles of God / Christ)
  n("Симеон", "christian"), n("Самуил", "christian"), n("Калоян", "christian"), n("Иван", "christian"),
  n("Васил", "christian"), n("Георги", "christian"),
  // N2: folklore, revival, literary and more Slavic male names (owner: all candidates)
  n("Богомил", "slavic"), // ?, W-BGN
  n("Божидар", "slavic"), // ?, W-BGN
  n("Бойко", "slavic"), // W-BGN
  n("Бранимир", "slavic"), // W-BGN
  n("Венцислав", "slavic"), // W-BGN
  n("Владислав", "slavic"), // W-BGN
  n("Гроздан", "slavic"), // ?, W-BGN
  n("Делян", "slavic"), // W-BGN
  n("Драган", "slavic"), // W-BGN
  n("Желязко", "slavic"), // W-BGN
  n("Живко", "slavic"), // W-BGN
  n("Златан", "slavic"), // W-BGN
  n("Златко", "slavic"), // W-BGN
  n("Калин", "slavic"), // W-BGN
  n("Красимир", "slavic"), // W-BGN
  n("Любомир", "slavic"), // W-BGN
  n("Милен", "slavic"), // W-BGN
  n("Младен", "slavic"), // W-BGN
  n("Момчил", "slavic"), // W-BGN
  n("Найден", "slavic"), // W-BGN, W-REV
  n("Недялко", "slavic"), // W-BGN
  n("Неделчо", "slavic"), // W-BGN
  n("Огнян", "slavic"), // W-BGN
  n("Пенчо", "slavic"), // W-BGN
  n("Пламен", "slavic"), // W-BGN
  n("Радомир", "slavic"), // W-BGN
  n("Румен", "slavic"), // W-BGN
  n("Спас", "slavic"), // ?, W-BGN
  n("Станислав", "slavic"), // W-BGN
  n("Станко", "slavic"), // W-BGN
  n("Стилян", "slavic"), // W-BGN
  n("Тихомир", "slavic"), // W-BGN
  n("Валко", "slavic"), // W-BGN
  n("Явор", "slavic"), // W-BGN
  n("Борислав", "slavic"), // W-BGN
  n("Страхил", "folklore"), // memory 0.9
  n("Дельо", "folklore"), // W-HAJ, W-DEL
  n("Чавдар", "folklore"), // ?, W-HAJ
  n("Ильо", "folklore"), // ?, W-HAJ, W-REV
  n("Петко", "folklore"), // W-HAJ, W-REV
  n("Райно", "revival"), // W-REV
  n("Дойчин", "folklore"), // memory 0.9
  n("Дойно", "folklore"), // W-REV
  n("Бачо", "revival"), // ?, W-REV
  n("Кольо", "revival"), // W-REV
  n("Колчо", "literary"), // W-PI, S-PI
  n("Мунчо", "literary"), // W-PI
  n("Ганчо", "literary"), // ?, memory 0.6
  n("Стефчо", "literary"), // ?, memory 0.7
  n("Цанко", "literary"), // S-PI
  n("Бойчо", "literary"), // W-PI, S-PI
  n("Генко", "literary"), // W-PI
  n("Пижо", "literary"), // W-PEL
  n("Марко", "folklore"), // memory 0.95
  n("Рангел", "slavic"), // ?, W-BGN
  n("Стефан", "christian"), // W-APR, W-REV
  n("Николай", "christian"), // W-BGN
  n("Никола", "christian"), // W-APR
  n("Петър", "christian"), // W-REV
  n("Димитър", "christian"), // W-REV
  n("Кирил", "christian"), // W-BGN
  n("Атанас", "christian"), // W-BGN
  n("Анастас", "christian"), // ?, W-BGN
  n("Андрей", "christian"), // W-BGN
  n("Константин", "christian"), // W-REV
  n("Александър", "christian"), // W-BGN
  n("Йордан", "christian"), // W-BGN
  n("Тодор", "christian"), // W-REV
  n("Ангел", "christian"), // ?, W-HAJ
  n("Захари", "christian"), // W-REV
  n("Нечо", "slavic"), // ?, memory 0.6
];

export const FEMALE_FIRST: readonly FirstName[] = [
  n("Десислава", "slavic"), n("Радослава", "slavic"), n("Светослава", "slavic"), n("Богдана", "slavic"),
  n("Божана", "slavic"), n("Бояна", "slavic"), n("Райна", "slavic"), n("Цветана", "slavic"),
  n("Стояна", "slavic"), n("Велика", "slavic"), n("Здравка", "slavic"), n("Добрина", "slavic"),
  n("Любка", "slavic"), n("Радка", "slavic"), n("Милена", "slavic"), n("Мила", "slavic"), n("Злата", "slavic"),
  n("Златина", "slavic"), n("Драгана", "slavic"), n("Снежана", "slavic"), n("Калина", "slavic"),
  n("Румяна", "slavic"), n("Невена", "slavic"), n("Вела", "slavic"), n("Неда", "slavic"), n("Станка", "slavic"),
  n("Живка", "slavic"), n("Велислава", "slavic"), n("Росица", "slavic"), n("Елица", "slavic"),
  n("Деница", "slavic"), n("Божидара", "slavic"),
  // ADD (executor): feminine forms of the male Slavic compounds and old Slavic nature names
  n("Веселина", "slavic"), n("Мирослава", "slavic"), n("Добромира", "slavic"), n("Станимира", "slavic"),
  n("Ясена", "slavic"), n("Лъчезара", "slavic"), n("Пламена", "slavic"), n("Радостина", "slavic"),
  // christian (included by default; no names or titles of God / Christ)
  n("Кераца", "christian"), n("Гергана", "christian"), n("Тонка", "christian"),
  // N2: more female names (owner: all candidates)
  n("Бисера", "slavic"), // W-BGN
  n("Бонислава", "slavic"), // W-BGN
  n("Борислава", "slavic"), // W-BGN
  n("Бойка", "slavic"), // W-BGN
  n("Галя", "slavic"), // W-BGN
  n("Гинка", "slavic"), // W-BGN
  n("Гина", "folklore"), // ?, memory 0.7
  n("Грозда", "slavic"), // W-BGN
  n("Гроздана", "slavic"), // W-BGN
  n("Ивелина", "slavic"), // W-BGN
  n("Илиана", "slavic"), // W-BGN
  n("Кремена", "slavic"), // W-BGN
  n("Красимира", "slavic"), // W-BGN
  n("Надежда", "slavic"), // W-BGN
  n("Недялка", "slavic"), // W-BGN, W-REV
  n("Ралица", "slavic"), // W-BGN
  n("Радина", "slavic"), // W-BGN
  n("Роза", "slavic"), // W-BGN
  n("Стилияна", "slavic"), // W-BGN
  n("Станислава", "slavic"), // W-BGN
  n("Стоянка", "slavic"), // W-BGN
  n("Тодора", "christian"), // W-BGN
  n("Тодорка", "christian"), // W-BGN
  n("Трендафила", "folklore"), // W-BGN
  n("Цвета", "slavic"), // W-BGN
  n("Цветанка", "slavic"), // W-BGN
  n("Василка", "christian"), // W-BGN
  n("Яна", "slavic"), // W-BGN
  n("Зора", "slavic"), // W-BGN
  n("Златка", "slavic"), // W-BGN
  n("Албена", "literary"), // W-YOV
  n("Боряна", "literary"), // W-YOV
  n("Лалка", "literary"), // W-PI
  n("Рада", "folklore"), // W-PI, W-BGN
  n("Пенда", "literary"), // W-PEL
  n("Ирина", "literary"), // W-TOB
  n("Дафина", "folklore"), // memory 0.9
  n("Лиляна", "slavic"), // memory 0.8
  n("Миглена", "slavic"), // memory 0.8
  n("Ленка", "folklore"), // ?, memory 0.7
  n("Румена", "folklore"), // W-HAJ
  n("Калинка", "folklore"), // memory 0.9
  n("Зорница", "slavic"), // memory 0.8
  n("Недка", "folklore"), // ?, memory 0.7
  n("Милка", "folklore"), // memory 0.8
  n("Янка", "folklore"), // memory 0.8
  n("Невяна", "folklore"), // ?, memory 0.7
  n("Марийка", "literary"), // W-PI
  n("Славка", "slavic"), // memory 0.8
  n("Славея", "slavic"), // memory 0.8
  n("Ружа", "slavic"), // memory 0.8
  n("Деяна", "slavic"), // memory 0.8
  n("Нейка", "folklore"), // ?, memory 0.7
  n("Петя", "christian"), // W-BGN
  n("Иванка", "christian"), // W-BGN
  n("Йорданка", "christian"), // W-BGN
  n("Вълкана", "slavic"), // memory 0.8
  n("Райка", "folklore"), // memory 0.8
  n("Дена", "folklore"), // ?, memory 0.6
  n("Лозана", "folklore"), // ?, memory 0.6
];

export const SURNAMES: readonly Surname[] = [
  // revival-era and literary figures (planner list)
  sr("Ботев", "slavic"), sr("Каравелов", "slavic"), sr("Раковски", "slavic"), sr("Бенковски", "slavic"),
  sr("Славейков", "slavic"), sr("Вазов", "slavic"), sr("Чинтулов", "slavic"), sr("Каблешков", "slavic"),
  sr("Волов", "slavic"), sr("Миладинов", "slavic"), sr("Дринов", "slavic"), sr("Обретенов", "slavic"),
  sr("Яворов", "slavic"), sr("Войников", "slavic"), sr("Хитов", "slavic"), sr("Блъсков", "slavic"),
  // patronymics from Slavic first names (planner list)
  sr("Стоянов", "slavic"), sr("Радев", "slavic"), sr("Цветков", "slavic"), sr("Богданов", "slavic"),
  sr("Велков", "slavic"), sr("Драганов", "slavic"), sr("Златев", "slavic"), sr("Добрев", "slavic"),
  sr("Любенов", "slavic"), sr("Райков", "slavic"), sr("Божилов", "slavic"), sr("Милев", "slavic"),
  sr("Станев", "slavic"), sr("Русев", "slavic"), sr("Здравков", "slavic"), sr("Славов", "slavic"),
  sr("Владимиров", "slavic"), sr("Борисов", "bulgar"), sr("Крумов", "bulgar"), sr("Аспарухов", "bulgar"),
  sr("Белев", "slavic"), sr("Бойчев", "slavic"), sr("Вълчев", "slavic"), sr("Вълков", "slavic"),
  sr("Чернев", "slavic"), sr("Жеков", "slavic"), sr("Желязков", "slavic"),
  sr("Шишманов", "dynastic"), // T
  sr("Ценов", "slavic"), sr("Хубенов", "slavic"), sr("Райчев", "slavic"), sr("Мирчев", "slavic"),
  sr("Асенов", "dynastic"), // T
  sr("Стойков", "slavic"), sr("Неделчев", "slavic"), sr("Гроздев", "slavic"), sr("Горанов", "slavic"),
  sr("Ясенов", "slavic"),
  // ADD (executor): more patronymics from old Slavic / Proto-Bulgar first names, and Левски
  s("Левски", "Левска", "slavic"), // ADD, ? (a nickname that became a famous surname)
  sr("Първанов", "slavic"), sr("Веселинов", "slavic"), sr("Мирославов", "slavic"), sr("Стоилов", "slavic"),
  sr("Тихомиров", "slavic"), sr("Ивайлов", "dynastic"), sr("Кубратов", "bulgar"), sr("Тервелов", "bulgar"),
  sr("Омуртагов", "bulgar"), sr("Радков", "slavic"), sr("Станков", "slavic"), sr("Ненов", "slavic"),
  sr("Събев", "slavic"), sr("Мирков", "slavic"), sr("Вутов", "slavic"), sr("Цонев", "slavic"),
  sr("Дражев", "slavic"), sr("Благоев", "slavic"), sr("Миланов", "slavic"), sr("Борилов", "dynastic"),
  sr("Севаров", "bulgar"), sr("Драгомиров", "slavic"), sr("Светославов", "slavic"), sr("Радославов", "slavic"),
  // christian (included by default; no names or titles of God / Christ)
  sr("Иванов", "christian"), sr("Петров", "christian"), sr("Георгиев", "christian"), sr("Димитров", "christian"),
  sr("Йорданов", "christian"), sr("Даскалов", "christian"),
  sr("Калоянов", "christian"), sr("Кънчев", "christian"),
  // N2: more surnames (owner: all candidates)
  sr("Огнянов", "literary"), // W-PI
  sr("Стефчов", "literary"), // W-PI
  sr("Заманов", "literary"), // ?, W-PI
  sr("Кандов", "literary"), // W-PI
  s("Боримечка", "Боримечка", "literary"), // ?, W-PI
  s("Кралич", "Кралич", "literary"), // ?, W-PI
  s("Попович", "Попович", "revival"), // ?, W-REV
  sr("Заимов", "revival"), // W-APR
  sr("Драгостинов", "revival"), // W-APR
  sr("Петлешков", "revival"), // W-APR
  sr("Геров", "revival"), // W-REV
  sr("Богоров", "revival"), // ?, W-REV
  sr("Априлов", "revival"), // W-REV
  s("Берон", "Берон", "revival"), // ?, W-REV, W-BGN
  sr("Друмев", "revival"), // W-REV
  sr("Фотинов", "revival"), // W-REV
  sr("Величков", "revival"), // W-REV
  sr("Китанчев", "revival"), // W-REV
  sr("Ковачев", "slavic"), // W-BGN
  sr("Младенов", "slavic"), // W-BGN
  sr("Николов", "christian"), // W-BGN
  sr("Тодоров", "christian"), // W-BGN
  sr("Илиев", "christian"), // ?, W-BGN
  sr("Петков", "christian"), // W-BGN
  sr("Михайлов", "christian"), // W-BGN
  sr("Рангелов", "slavic"), // W-BGN
  sr("Дилов", "slavic"), // W-BGN
  sr("Какалов", "slavic"), // ?, W-BGN
  sr("Цветанов", "slavic"), // W-BGN
  sr("Йовков", "literary"), // W-YOV
  sr("Дебелянов", "literary"), // memory 0.95
  sr("Димов", "literary"), // memory
  sr("Константинов", "literary"), // memory
  sr("Лилиев", "literary"), // memory 0.8
  sr("Траянов", "literary"), // memory 0.8
  sr("Гешов", "literary"), // ?, memory 0.7
  sr("Бобчев", "literary"), // ?, memory 0.6
  sr("Смирненски", "literary"), // ?, memory
  sr("Колев", "slavic"), // derived
  sr("Недев", "slavic"), // derived
  sr("Пенчев", "slavic"), // derived
  sr("Донев", "slavic"), // derived
  sr("Дончев", "slavic"), // derived
  sr("Маринов", "christian"), // derived
  sr("Живков", "slavic"), // ?, derived
  sr("Златков", "slavic"), // derived
  sr("Калинов", "slavic"), // derived
  sr("Красимиров", "slavic"), // derived
  sr("Любомиров", "slavic"), // derived
  sr("Момчилов", "slavic"), // derived
  sr("Найденов", "slavic"), // derived
  sr("Пламенов", "slavic"), // derived
  sr("Радомиров", "slavic"), // derived
  sr("Руменов", "slavic"), // derived
  sr("Спасов", "slavic"), // ?, derived
  sr("Станчев", "slavic"), // derived
  sr("Янев", "slavic"), // derived
  sr("Янков", "slavic"), // derived
  sr("Дойчинов", "folklore"), // derived
  sr("Страхилов", "folklore"), // derived
  sr("Чавдаров", "folklore"), // ?, derived
  sr("Делев", "folklore"), // derived
  sr("Райнов", "slavic"), // derived
  sr("Ганчев", "literary"), // derived
  sr("Цанков", "literary"), // derived
  sr("Генков", "literary"), // derived
  sr("Попов", "slavic"), // W-BGN
  sr("Кирилов", "christian"), // derived
];
