// Random character name (slice N1): a first name and a surname of the same gender. Bulgarian UI gets the Cyrillic
// name, the English UI its official transliteration. `rng` returns a number in [0, 1) (Math.random, or a seeded
// generator in tests).
import { DEFAULT_ORIGINS, FEMALE_FIRST, MALE_FIRST, SURNAMES, type Gender, type Origin } from "../names/bgNames";
import { transliterate } from "./translit";

export type Rng = () => number;

function pick<T>(list: readonly T[], rng: Rng): T {
  return list[Math.min(list.length - 1, Math.floor(rng() * list.length))];
}

export function randomName(
  lang: "bg" | "en",
  rng: Rng,
  gender?: Gender,
  origins: readonly Origin[] = DEFAULT_ORIGINS,
): string {
  const g: Gender = gender ?? (rng() < 0.5 ? "m" : "f");
  const firsts = (g === "m" ? MALE_FIRST : FEMALE_FIRST).filter((x) => origins.includes(x.origin));
  const surnames = SURNAMES.filter((x) => origins.includes(x.origin));
  const first = pick(firsts, rng).bg;
  const sur = pick(surnames, rng);
  const full = `${first} ${g === "m" ? sur.m : sur.f}`;
  return lang === "bg" ? full : transliterate(full);
}
