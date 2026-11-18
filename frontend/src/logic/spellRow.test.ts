import { describe, expect, it } from "vitest";
import { bg } from "../copy/bg";
import { en } from "../copy/en";
import { localizeSpellRow, type SpellRowValues } from "./spellRow";

const row = (castingTime: string, range: string, duration: string, school = "Abjuration"): SpellRowValues => ({ school, castingTime, range, duration });
const B = (r: SpellRowValues) => localizeSpellRow(bg.spellRow, r);

// The distinct values of GET /api/spells (557 spells), 2026-11-18.
const SCHOOLS = ["Abjuration", "Conjuration", "Divination", "Enchantment", "Evocation", "Illusion", "Necromancy", "Transmutation"];
const TIMES = ["1 action", "1 bonus action", "1 hour", "1 minute", "1 reaction", "10 minutes", "12 hours", "24 hours", "8 hours"];
const RANGES = ["1 mile", "10 feet", "100 feet", "1000 feet", "120 feet", "150 feet", "20 feet", "30 feet", "300 feet", "5 feet", "500 feet", "500 miles", "60 feet", "90 feet", "Self", "Self (10-foot emanation)", "Self (10-foot radius)", "Self (100-foot line)", "Self (120-foot line)", "Self (15-foot cone)", "Self (15-foot radius)", "Self (20-foot emanation)", "Self (30-foot cone)", "Self (30-foot line)", "Self (30-foot radius)", "Self (5-foot radius)", "Self (60-foot cone)", "Self (60-foot emanation)", "Sight", "Special", "Touch", "Unlimited"];
const DURATIONS = ["1 hour", "1 minute", "1 round", "10 days", "10 minutes", "24 hours", "30 days", "6 hours", "7 days", "8 hours", "Instantaneous", "Instantaneous or 1 hour", "Special", "Until dispelled", "Until dispelled or triggered", "Up to 1 hour", "Up to 1 minute", "Up to 1 round", "Up to 10 minutes", "Up to 2 hours", "Up to 24 hours", "Up to 6 rounds", "Up to 8 hours"];

describe("localizeSpellRow", () => {
  it("renders the common values in Bulgarian", () => {
    expect(B(row("1 reaction", "Self", "1 round"))).toEqual({ school: "Абюрация", castingTime: "1 реакция", range: "Себе си", duration: "1 рунд" });
    expect(B(row("1 action", "60 feet", "Instantaneous", "Conjuration"))).toEqual({ school: "Призоваване", castingTime: "1 действие", range: "60 фута (18 м)", duration: "Мигновено" });
    expect(B(row("1 bonus action", "Touch", "Up to 1 minute")).duration).toBe("До 1 минута");
    expect(B(row("10 minutes", "5 feet", "8 hours"))).toMatchObject({ castingTime: "10 минути", range: "5 фута (1,5 м)", duration: "8 часа" });
    expect(B(row("1 hour", "1 mile", "1 minute"))).toMatchObject({ castingTime: "1 час", range: "1 миля (1,6 км)", duration: "1 минута" });
    expect(B(row("1 action", "Self (30-foot cone)", "Until dispelled")).range).toBe("Себе си, конус 30 фута (9 м)");
    expect(B(row("1 action", "Sight", "Instantaneous or 1 hour")).duration).toBe("Мигновено или 1 час");
    expect(B(row("1 action", "Unlimited", "Until dispelled or triggered")).duration).toBe("До разсейване или задействане");
  });

  it("leaves an unknown value in English and keeps nulls", () => {
    expect(B(row("1 action, which you take when X", "Strange", "Whenever", "Chronurgy"))).toEqual({ school: "Chronurgy", castingTime: "1 action, which you take when X", range: "Strange", duration: "Whenever" });
    expect(B({ school: null, castingTime: null, range: null, duration: null })).toEqual({ school: null, castingTime: null, range: null, duration: null });
  });

  it("returns English rows unchanged", () => {
    const r = row("1 action", "Self (30-foot cone)", "Up to 1 minute");
    expect(localizeSpellRow(en.spellRow, r)).toBe(r);
  });

  it("sweeps the real catalog values: Bulgarian or unchanged, never a crash", () => {
    const stay: string[] = [];
    const check = (kind: string, values: string[], pick: (r: SpellRowValues) => string, mk: (v: string) => SpellRowValues) => {
      for (const v of values) {
        const out = pick(B(mk(v)));
        if (out === v) stay.push(`${kind}: ${v}`);
        else expect(out).toMatch(/[Ѐ-ӿ]/);
      }
    };
    check("school", SCHOOLS, (r) => r.school as string, (v) => row("1 action", "Self", "1 round", v));
    check("time", TIMES, (r) => r.castingTime as string, (v) => row(v, "Self", "1 round"));
    check("range", RANGES, (r) => r.range as string, (v) => row("1 action", v, "1 round"));
    check("duration", DURATIONS, (r) => r.duration as string, (v) => row("1 action", "Self", v));
    expect(stay).toEqual([]);
  });
});
