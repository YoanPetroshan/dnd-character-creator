import { describe, expect, it } from "vitest";
import { transliterate } from "./translit";

const CASES: [string, string][] = [
  ["Аспарух", "Asparuh"],
  ["Щерю", "Shteryu"],
  ["Щастие", "Shtastie"],
  ["Жадна", "Zhadna"],
  ["Цветан", "Tsvetan"],
  ["Чавдар", "Chavdar"],
  ["Шишман", "Shishman"],
  ["Юлиян", "Yuliyan"],
  ["Явор", "Yavor"],
  ["Ъгъл", "Agal"],
  ["Мария", "Maria"],
  ["Юлия", "Yulia"],
  ["Илия", "Ilia"],
  ["Георги", "Georgi"],
  ["Андрей", "Andrey"],
  ["Васильо", "Vasilyo"],
  ["Любен", "Lyuben"],
  ["Ивайло", "Ivaylo"],
  ["Раковски", "Rakovski"],
  ["Бенковска", "Benkovska"],
  ["ЖИВКА", "ZHIVKA"],
  ["МАРИЯ", "MARIA"],
  ["Анна-Мария", "Anna-Maria"],
  ["Цвета Щерева", "Tsveta Shtereva"],
  ["Ян 3 Smith", "Yan 3 Smith"],
  ["Я", "Ya"],
  ["Ия", "Ia"],
  ["Дельо", "Delyo"],
  ["Ильо", "Ilyo"],
  ["Йордан", "Yordan"],
  ["Ивайлов", "Ivaylov"],
  ["Пижо", "Pizho"],
  ["Юнак", "Yunak"],
  ["Кольо", "Kolyo"],
  ["Боримечка", "Borimechka"],
  ["Смирненска", "Smirnenska"],
  ["Желязко", "Zhelyazko"],
  ["Дойчин", "Doychin"],
  ["Йовков", "Yovkov"],
  ["Иван, Петър!", "Ivan, Petar!"],
  ["", ""],
];

describe("transliterate (official streamlined system)", () => {
  for (const [bg, en] of CASES) it(`${bg || "(empty)"} -> ${en || "(empty)"}`, () => expect(transliterate(bg)).toBe(en));
  it("'ия' only at the end of a word", () => {
    expect(transliterate("Диана")).toBe("Diana");
    expect(transliterate("Лилия")).toBe("Lilia");
    expect(transliterate("Ияна")).toBe("Iyana");
  });
});
