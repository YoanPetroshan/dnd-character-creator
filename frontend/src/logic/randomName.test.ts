import { describe, expect, it } from "vitest";
import { randomName } from "./randomName";
import { FEMALE_FIRST, MALE_FIRST, SURNAMES } from "../names/bgNames";

function mulberry32(a: number) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const CYR = /[А-Яа-я]/;
const maleF = new Set(MALE_FIRST.map((x) => x.bg));
const femaleF = new Set(FEMALE_FIRST.map((x) => x.bg));
const christian = new Set([...MALE_FIRST, ...FEMALE_FIRST].filter((x) => x.origin === "christian").map((x) => x.bg));
const christianS = new Set(SURNAMES.filter((x) => x.origin === "christian").flatMap((x) => [x.m, x.f]));

describe("randomName", () => {
  it("EN output is Latin title case with no Cyrillic", () => {
    const r = mulberry32(1);
    for (let i = 0; i < 500; i++) {
      const n = randomName("en", r);
      expect(n).toMatch(/^[A-Z][a-z]+( [A-Z][a-z]+)*$/);
      expect(CYR.test(n)).toBe(false);
    }
  });
  it("BG output is all Cyrillic, 'First Surname'", () => {
    const r = mulberry32(2);
    for (let i = 0; i < 200; i++) expect(randomName("bg", r)).toMatch(/^[А-Яа-я]+ [А-Яа-я]+$/);
  });
  it("is deterministic for a seed and varies across seeds", () => {
    const a = Array.from({ length: 20 }, (_, i) => randomName("bg", mulberry32(7 + i * 0)));
    expect(new Set(a).size).toBe(1);
    const seq = (seed: number) => { const r = mulberry32(seed); return Array.from({ length: 10 }, () => randomName("en", r)); };
    expect(seq(42)).toEqual(seq(42));
    expect(seq(42)).not.toEqual(seq(43));
  });
  it("picks both genders about half the time when unspecified", () => {
    const r = mulberry32(3);
    let m = 0;
    for (let i = 0; i < 1000; i++) if (maleF.has(randomName("bg", r).split(" ")[0])) m++;
    expect(m).toBeGreaterThan(400);
    expect(m).toBeLessThan(600);
  });
  it("a female first name always gets the female surname, a male the male one", () => {
    const r = mulberry32(4);
    const mS = new Set(SURNAMES.map((x) => x.m));
    const fS = new Set(SURNAMES.map((x) => x.f));
    for (let i = 0; i < 1000; i++) {
      const [first, sur] = randomName("bg", r).split(" ");
      if (femaleF.has(first)) expect(fS.has(sur), `${first} ${sur}`).toBe(true);
      else { expect(maleF.has(first)).toBe(true); expect(mS.has(sur), `${first} ${sur}`).toBe(true); }
    }
    for (let i = 0; i < 100; i++) {
      expect(femaleF.has(randomName("bg", r, "f").split(" ")[0])).toBe(true);
      expect(maleF.has(randomName("bg", r, "m").split(" ")[0])).toBe(true);
    }
  });
  it("never uses christian-tagged names by default, and does when asked", () => {
    const r = mulberry32(5);
    for (let i = 0; i < 3000; i++) {
      const [first, sur] = randomName("bg", r).split(" ");
      expect(christian.has(first), first).toBe(false);
      expect(christianS.has(sur), sur).toBe(false);
    }
    const all = ["bulgar", "slavic", "dynastic", "christian"] as const;
    const seen = new Set<string>();
    for (let i = 0; i < 3000; i++) seen.add(randomName("bg", r, undefined, all).split(" ")[1]);
    expect([...seen].some((s) => christianS.has(s))).toBe(true);
  });
  it("copes with rng returning values at the edges", () => {
    expect(randomName("bg", () => 0, "m")).toBeTruthy();
    expect(randomName("bg", () => 0.9999999, "f")).toBeTruthy();
  });
});
