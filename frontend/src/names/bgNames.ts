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
//   christian - Greek/Hebrew/Latin roots (Иван, Георги, ...). Tagged, but EXCLUDED by default (decision E1);
//               flip DEFAULT_ORIGINS below to include them.
//
// Comments: "ADD" = added by the executor beyond the planner's list (for the user to review);
//           "?" = disputed or uncertain etymology/authenticity (for the user to review).

export type Origin = "bulgar" | "slavic" | "dynastic" | "christian";
export type Gender = "m" | "f";

export interface FirstName { bg: string; origin: Origin }
export interface Surname { m: string; f: string; origin: Origin }

/** The one switch: origins the dice may use. Add "christian" to include Иван, Георги, Иванов, Петров, ... */
export const DEFAULT_ORIGINS: readonly Origin[] = ["bulgar", "slavic", "dynastic"];

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
  // christian (excluded by default)
  n("Симеон", "christian"), n("Самуил", "christian"), n("Калоян", "christian"), n("Иван", "christian"),
  n("Христо", "christian"), n("Васил", "christian"), n("Георги", "christian"),
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
  // christian (excluded by default)
  n("Кераца", "christian"), n("Гергана", "christian"), n("Тонка", "christian"),
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
  // christian (excluded by default)
  sr("Иванов", "christian"), sr("Петров", "christian"), sr("Георгиев", "christian"), sr("Димитров", "christian"),
  sr("Христов", "christian"), sr("Йорданов", "christian"), sr("Даскалов", "christian"),
  sr("Калоянов", "christian"), sr("Кънчев", "christian"),
];
