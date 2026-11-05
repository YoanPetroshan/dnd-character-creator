import { describe, expect, it } from "vitest";
import { DEFAULT_ORIGINS, FEMALE_FIRST, MALE_FIRST, SURNAMES } from "./bgNames";

const CYR = /^[А-Яа-я]+$/;
const inc = <T extends { origin: string }>(l: readonly T[]) => l.filter((x) => (DEFAULT_ORIGINS as readonly string[]).includes(x.origin));

describe("name lists", () => {
  it("meet the minimum counts after the default origin filter", () => {
    expect(inc(MALE_FIRST).length).toBeGreaterThanOrEqual(30);
    expect(inc(FEMALE_FIRST).length).toBeGreaterThanOrEqual(30);
    expect(inc(SURNAMES).length).toBeGreaterThanOrEqual(50);
  });
  it("the default filter excludes christian and nothing else is lost", () => {
    expect(DEFAULT_ORIGINS).not.toContain("christian");
    for (const l of [MALE_FIRST, FEMALE_FIRST, SURNAMES] as readonly (readonly { origin: string }[])[]) {
      expect(l.some((x) => x.origin === "christian")).toBe(true);
      expect(inc(l).every((x) => x.origin !== "christian")).toBe(true);
      expect(inc(l).length).toBe(l.filter((x) => x.origin !== "christian").length);
    }
  });
  it("have no duplicates", () => {
    const dup = (a: string[]) => a.filter((x, i) => a.indexOf(x) !== i);
    expect(dup(MALE_FIRST.map((x) => x.bg))).toEqual([]);
    expect(dup(FEMALE_FIRST.map((x) => x.bg))).toEqual([]);
    expect(dup(SURNAMES.map((x) => x.m))).toEqual([]);
    expect(dup(SURNAMES.map((x) => x.f))).toEqual([]);
  });
  it("are all Cyrillic, one capitalised word each", () => {
    for (const w of [...MALE_FIRST.map((x) => x.bg), ...FEMALE_FIRST.map((x) => x.bg), ...SURNAMES.flatMap((x) => [x.m, x.f])]) {
      expect(w, w).toMatch(CYR);
      expect(w[0], w).toBe(w[0].toUpperCase());
      expect(w.slice(1), w).toBe(w.slice(1).toLowerCase());
    }
  });
  it("surname forms pair: f === m + 'а', -ски -> -ска", () => {
    for (const s of SURNAMES) {
      expect(s.f, s.m).toBe(s.m.endsWith("ски") ? s.m.slice(0, -1) + "а" : s.m + "а");
      expect(s.m).not.toBe(s.f);
    }
    expect(SURNAMES.some((s) => s.m.endsWith("ски"))).toBe(true);
  });
});
