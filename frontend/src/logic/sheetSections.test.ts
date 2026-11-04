import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SheetView } from "../components/sheet/SheetView";
import { t } from "../copy";
import bard10 from "../__fixtures__/bard10-2014.json";
import fighter4 from "../__fixtures__/fighter4-2024.json";
import rogue6 from "../__fixtures__/rogue6-2024.json";
import warlock7 from "../__fixtures__/warlock7-2024.json";
import wizard20 from "../__fixtures__/wizard20-2024.json";
import coverage from "./sheetCoverage.json";
import { expertiseLabel, languageName, proficiencyLabel, skillName } from "./labels";
import { SHEET_SECTION_KEYS, abilityRows, sheetSections, type SheetSection, type SheetSectionData, type SheetSectionKey } from "./sheetSections";
import { spellcastingAbility } from "./spellAbility";
import { routeTitle } from "./routeTitle";
import type { Ability, Resolution } from "../types";

interface Fixture {
  id: string;
  ruleset: string;
  base: Record<Ability, number>;
  resolution: unknown;
}
const FIXTURES = [warlock7, bard10, fighter4, wizard20, rogue6] as unknown as Fixture[];
const res = (f: Fixture) => f.resolution as Resolution;
const byId = (id: string) => FIXTURES.find((f) => f.id === id)!;
const keysOf = (f: Fixture) => sheetSections(res(f), f.base).map((s) => s.key);
const section = <K extends SheetSectionKey>(f: Fixture, key: K): SheetSectionData[K] =>
  sheetSections(res(f), f.base).find((s) => s.key === key)?.data as SheetSectionData[K];

describe("sheetSections", () => {
  it("lists section keys in page order, each at most once", () => {
    for (const f of FIXTURES) {
      const keys = keysOf(f);
      expect(new Set(keys).size).toBe(keys.length);
      expect(keys).toEqual(SHEET_SECTION_KEYS.filter((k) => keys.includes(k)));
    }
  });

  it("always has the core sections", () => {
    for (const f of FIXTURES) {
      expect(keysOf(f)).toEqual(
        expect.arrayContaining(["identity", "abilities", "proficiencyBonus", "armorClass", "hitPoints", "initiative", "speeds", "passives", "savingThrows", "skills"]),
      );
    }
  });

  it("covers every section key somewhere in the fixtures except details (synthetic test below)", () => {
    const seen = new Set(FIXTURES.flatMap(keysOf));
    expect(SHEET_SECTION_KEYS.filter((k) => !seen.has(k))).toEqual(["defenses", "details"].filter((k) => !seen.has(k as SheetSectionKey)));
  });

  it("the coverage file lists exactly the section keys", () => {
    expect(Object.keys(coverage.sections).sort()).toEqual([...SHEET_SECTION_KEYS].sort());
  });

  it("warlock 7 (2024): pact slots, innate spell, devil's sight, Mystic-Arcanum-free caster", () => {
    const f = byId("warlock7-2024");
    expect(keysOf(f)).toEqual(expect.arrayContaining(["spells", "innateSpells", "senses", "features", "feats", "resources", "equipment", "carryingCapacity"]));
    const spells = section(f, "spells")!;
    expect(spells.pactSlots).toEqual([{ level: 4, count: 2 }]);
    expect(spells.slots).toEqual([]);
    expect(spells.casters).toHaveLength(1);
    expect(spells.casters[0]).toMatchObject({ classId: "warlock", ability: "CHA", saveDC: 14, attackBonus: 6 });
    expect(spells.casters[0].cantrips.length).toBeGreaterThan(0);
    expect(section(f, "senses")).toEqual([{ kind: "devilsSight", feet: 120 }]);
    expect(section(f, "innateSpells")![0].name).toBe("Mage Armor");
  });

  it("bard 10 (2014): known spells, shared slots listed, no pact slots", () => {
    const f = byId("bard10-2014");
    const spells = section(f, "spells")!;
    expect(spells.slots.length).toBeGreaterThan(0);
    expect(spells.pactSlots).toEqual([]);
    expect(spells.slotsShared).toBe(false);
    expect(spells.casters[0].ability).toBe("CHA");
    expect(spells.casters[0].known.length).toBeGreaterThan(10);
    expect(section(f, "identity")!.species).not.toBeNull();
  });

  it("fighter 4 (2024): attacks table, heavy armor, equipment with a pack's contents", () => {
    const f = byId("fighter4-2024");
    const attacks = section(f, "attacks")!;
    expect(attacks.attacks.map((a) => a.name)).toEqual(expect.arrayContaining(["Greatsword"]));
    expect(attacks.perAction).toBe(1);
    const eq = section(f, "equipment")!;
    expect(eq.groups.map((g) => g.kind)).toEqual(["chosen"]);
    expect(eq.groups[0].entries.find((e) => e.contents?.length)?.name).toBe("Dungeoneer's Pack");
    expect(section(f, "armorClass")!.value).toBeGreaterThanOrEqual(16);
  });

  it("wizard 20 (2024): spellbook, Spell Mastery and Signature Spells", () => {
    const caster = section(byId("wizard20-2024"), "spells")!.casters[0];
    expect(caster.ability).toBe("INT");
    expect(caster.spellbook.length).toBeGreaterThan(20);
    expect(caster.spellMastery).toHaveLength(2);
    expect(caster.signatureSpells).toHaveLength(2);
  });

  it("rogue 6 (2024): expertise marks on skills", () => {
    const skills = section(byId("rogue6-2024"), "skills")!;
    expect(skills.rows.filter((r) => r.expertise).length).toBeGreaterThanOrEqual(2);
    for (const r of skills.rows) if (r.expertise) expect(r.proficient).toBe(true);
    expect(skills.rows.map((r) => r.name)).toEqual([...skills.rows.map((r) => r.name)].sort((a, b) => a.localeCompare(b, "en")));
  });

  it("saving throws mark exactly the proficient abilities", () => {
    for (const f of FIXTURES) {
      const saves = section(f, "savingThrows")!;
      expect(saves.filter((s) => s.proficient).map((s) => s.ability).sort()).toEqual([...res(f).sheet.proficiencies.savingThrows].sort());
    }
  });

  it("abilities: base + bonus = total, modifier from the server", () => {
    for (const f of FIXTURES) {
      const rows = section(f, "abilities")!;
      expect(rows.map((r) => r.ability)).toEqual(["STR", "DEX", "CON", "INT", "WIS", "CHA"]);
      for (const r of rows) {
        expect(r.base).toBe(f.base[r.ability]);
        expect(r.base! + r.bonus!).toBe(r.total);
        expect(r.modifier).toBe(res(f).derived.abilityModifiers[r.ability]);
      }
    }
    // fighter 4 base STR 16 -> total 20 (an ASI-less +4 from the background/feat): the bonus column shows the difference
    expect(section(byId("fighter4-2024"), "abilities")!.find((r) => r.ability === "STR")).toMatchObject({ base: 16, total: 20, bonus: 4 });
  });

  it("abilities without a known base show no base / bonus", () => {
    const f = byId("fighter4-2024");
    const rows = sheetSections(res(f)).find((s) => s.key === "abilities")!.data as ReturnType<typeof abilityRows>;
    expect(rows.every((r) => r.base === null && r.bonus === null)).toBe(true);
  });

  it("details: only filled fields, grouped like the exports", () => {
    const f = byId("bard10-2014");
    const withDetails = {
      ...res(f),
      sheet: { ...res(f).sheet, details: { alignment: "Chaotic Good", ideals: "Freedom", backstory: "Long ago", notes: "" } },
    } as Resolution;
    const details = sheetSections(withDetails).find((s) => s.key === "details")!.data as { section: string; fields: { key: string; value: string }[] }[];
    expect(details.map((d) => d.section)).toEqual(["character", "personality", "notes"]);
    expect(details[0].fields).toEqual([{ key: "alignment", value: "Chaotic Good" }]);
    expect(details[2].fields).toEqual([{ key: "backstory", value: "Long ago" }]);
    expect(keysOf({ ...f, resolution: { ...res(f), sheet: { ...res(f).sheet, details: {} } } })).not.toContain("details");
  });

  it("defenses, a hand-held shield and worn / wielded lines", () => {
    const f = byId("fighter4-2024");
    const r = res(f);
    const custom = {
      ...r,
      sheet: {
        ...r.sheet,
        damageModifiers: { resistances: ["fire"], immunities: [], vulnerabilities: ["cold"] },
        conditionImmunities: ["charmed"],
        equipment: {
          ...r.sheet.equipment,
          worn: { armor: "chain-mail", shield: false, manual: true },
          wielded: { main: "greatsword", off: null, manual: true },
        },
      },
    } as Resolution;
    const sections = sheetSections(custom);
    expect(sections.find((s) => s.key === "defenses")!.data).toEqual({
      resistances: ["Fire"], immunities: [], vulnerabilities: ["Cold"], conditionImmunities: ["Charmed"],
    });
    const eq = sections.find((s) => s.key === "equipment")!.data as { worn: unknown; wielded: unknown };
    expect(eq.worn).toEqual({ armor: "Chain Mail", shield: false });
    expect(eq.wielded).toEqual({ main: "Greatsword", off: null });
  });

  it("an empty resolution still gives a sheet (identity, abilities, saves, skills, passives) without throwing", () => {
    const r = res(byId("fighter4-2024"));
    const bare = {
      ...r,
      sheet: { ...r.sheet, classes: [], species: null, background: null, spells: [], features: [], feats: [], innateSpells: [], senses: {}, weaponMasteries: [] },
      derived: { ...r.derived, attacks: [], classResources: [], featResources: [], speciesResources: [], spellSlots: {}, warlockSpellSlots: {} },
    } as unknown as Resolution;
    const keys = sheetSections(bare).map((s) => s.key);
    expect(keys).not.toEqual(expect.arrayContaining(["spells", "features", "feats", "resources", "innateSpells", "senses"]));
    expect(keys).toEqual(expect.arrayContaining(["identity", "abilities", "savingThrows", "skills", "passives"]));
  });
});

describe("spellcastingAbility", () => {
  const mods = { STR: 0, DEX: 2, CON: 1, INT: 4, WIS: 1, CHA: 3 };
  it("returns the class ability when the server's numbers agree", () => {
    expect(spellcastingAbility("wizard", 8 + 3 + 4, 3 + 4, mods, 3)).toBe("INT");
    expect(spellcastingAbility("warlock", 14, 6, mods, 3)).toBe("CHA");
    expect(spellcastingAbility("fighter", 15, 7, mods, 3)).toBe("INT"); // Eldritch Knight
  });
  it("returns null on a mismatch, an unknown class or missing numbers", () => {
    expect(spellcastingAbility("wizard", 13, 5, mods, 3)).toBeNull();
    expect(spellcastingAbility("homebrew", 15, 7, mods, 3)).toBeNull();
    expect(spellcastingAbility("wizard", null, null, mods, 3)).toBeNull();
    expect(spellcastingAbility("wizard", 15, 7, undefined, 3)).toBeNull();
  });
});

describe("routeTitle", () => {
  it("every step path has its own title ending with the app name", () => {
    const paths = ["/home", "/class", "/background", "/species", "/abilities", "/equipment", "/sheet", "/export"];
    const titles = paths.map(routeTitle);
    expect(new Set(titles).size).toBe(paths.length);
    for (const title of titles) expect(title.endsWith(t.appName)).toBe(true);
    expect(routeTitle("/sheet").startsWith(t.titles.pages["/sheet"])).toBe(true);
  });
  it("an unknown path gets the fallback title", () => {
    expect(routeTitle("/nope")).toBe(`${t.titles.fallback}${t.titles.separator}${t.appName}`);
  });
});

// ---- leaf coverage: every resolution leaf that sheetCoverage.json assigns to a section reaches both the
// section data and the rendered page text (the server test test_sheet_coverage.py checks that EVERY leaf the
// export audit looks at is either assigned or listed in SHEET_OMITTED).
function patternRegex(pat: string): RegExp {
  const esc = pat.replace(/[.+^${}()|\\?]/g, "\\$&").replace(/\[/g, "\\[").replace(/\]/g, "\\]");
  return new RegExp(esc.replace(/\*\*/g, "\u0000").replace(/\*/g, "[^.]+").replace(/\u0000/g, ".+") + "$");
}
function* leaves(obj: unknown, path: string[]): Generator<[string, unknown]> {
  if (Array.isArray(obj)) for (const v of obj) yield* leaves(v, [...path, "[]"]);
  else if (obj && typeof obj === "object")
    for (const [k, v] of Object.entries(obj)) yield* leaves(v, [...path, /^\d+$/.test(k) ? "#" : k]);
  else yield [path.join("."), obj];
}
const norm = (s: string) => s.replace(/\s+/g, " ").trim().toLowerCase();
function pageText(sections: SheetSection[]): string {
  const html = renderToStaticMarkup(createElement(SheetView, { sections }));
  return norm(
    html
      .replace(/<[^>]*>/g, " ")
      .replace(/&#x27;/g, "'")
      .replace(/&quot;/g, '"')
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&amp;/g, "&"),
  );
}
const numberToken = (n: number) =>
  new RegExp(`(?<![\\w.])${n < 0 ? "-" : "[+x×−-]?"}${Math.abs(n)}(?![\\w])`);

// values the page prints through a label table
const FORMATTED: [string, (v: string) => string[]][] = [
  ["sheet.proficiencies.skills.[]", (v) => [skillName(v)]],
  ["sheet.expertiseSkills.[]", (v) => [expertiseLabel(v)]],
  ["sheet.proficiencies.languages.[]", (v) => [languageName(v)]],
  ["sheet.proficiencies.armor.[]", (v) => [proficiencyLabel(v)]],
  ["sheet.proficiencies.weapons.[]", (v) => [proficiencyLabel(v)]],
  ["sheet.proficiencies.tools.[]", (v) => [proficiencyLabel(v)]],
  ["derived.classResources.[].recharge", (v) => [t.sheet.resources.text.recharge[v]]],
  ["derived.featResources.[].recharge", (v) => [t.sheet.resources.text.recharge[v]]],
  ["derived.speciesResources.[].recharge", (v) => [t.sheet.resources.text.recharge[v]]],
  ["derived.classResources.[].details.resistances.[]", (v) => [t.sheet.resources.text.damageTypes[v], t.sheet.resources.text.resistancesAllButPsychic]],
  ["sheet.damageModifiers.*.[]", (v) => [v.replace(/-/g, " ")]],
  ["sheet.conditionImmunities.[]", (v) => [v.replace(/-/g, " ")]],
];

describe("sheetCoverage.json leaves reach the rendered sheet", () => {
  const patterns = Object.entries(coverage.sections).flatMap(([key, pats]) => (pats as string[]).map((p) => [key, patternRegex(p), p] as const));
  for (const f of FIXTURES) {
    it(`${f.id}: every covered leaf is in its section's data and in the page text`, () => {
      const sections = sheetSections(res(f), f.base);
      const text = pageText(sections);
      const dataOf = new Map(sections.map((s) => [s.key, norm(JSON.stringify(s.data))]));
      const failures: string[] = [];
      let checked = 0;
      for (const root of ["sheet", "derived"] as const) {
        for (const [path, value] of leaves((res(f) as unknown as Record<string, unknown>)[root], [root])) {
          const hit = patterns.find(([, re]) => re.test(path));
          if (!hit || value === null || value === false || value === "" || value === undefined) continue;
          const [key, , pat] = hit;
          checked++;
          if (!dataOf.has(key as SheetSectionKey)) {
            failures.push(`${path}: section ${key} is missing`);
            continue;
          }
          if (typeof value === "string") {
            const alts = (FORMATTED.find(([p]) => patternRegex(p).test(path))?.[1](value) ?? [value]).map(norm);
            if (!alts.some((a) => text.includes(a))) failures.push(`${path} = ${value} (${pat}) is not on the page`);
          } else if (typeof value === "number") {
            if (!numberToken(value).test(text)) failures.push(`${path} = ${value} (${pat}) is not on the page`);
          } else if (value === true) {
            // flags: stealthDisadvantage / overCapacity / equipped / unlimited / details.fly ... print a phrase; the page must have the section
          }
        }
      }
      expect(failures).toEqual([]);
      expect(checked).toBeGreaterThan(150);
    });
  }
});
