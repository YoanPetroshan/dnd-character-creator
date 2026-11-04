import { describe, expect, it } from "vitest";
import { MIGRATIONS, draftVersionOf, migrateDraft, type MigrationTable } from "./migrations";
import { DRAFT_VERSION, mergeDraft } from "./draft";
import { parseHealth, serverIsOlder } from "./serverHealth";

describe("migration table", () => {
  it("has a step for every version below the current one (the chain is complete)", () => {
    for (let v = 1; v < DRAFT_VERSION; v++) expect(typeof MIGRATIONS[v]).toBe("function");
  });

  it("a draft without draftVersion is version 1; garbage versions count as 1", () => {
    expect(draftVersionOf({})).toBe(1);
    expect(draftVersionOf({ draftVersion: "2" })).toBe(1);
    expect(draftVersionOf({ draftVersion: 0 })).toBe(1);
    expect(draftVersionOf({ draftVersion: 2 })).toBe(2);
  });

  it("v1 -> v2 adds ruleset mixed, keeps an existing ruleset, stamps the version, does not mutate", () => {
    const v1 = { classes: [], name: "A" };
    const out = migrateDraft(v1, 2);
    expect(out).toMatchObject({ ruleset: "mixed", draftVersion: 2, name: "A" });
    expect(v1).toEqual({ classes: [], name: "A" });
    expect(migrateDraft({ draftVersion: 1, ruleset: "2024" }, 2).ruleset).toBe("2024");
  });

  it("a current draft is returned as is", () => {
    const d = { draftVersion: DRAFT_VERSION, name: "x" };
    expect(migrateDraft(d, DRAFT_VERSION)).toBe(d);
  });

  it("runs several steps in order (synthetic table v1 -> v4)", () => {
    const log: number[] = [];
    const table: MigrationTable = {
      1: (d) => (log.push(1), { ...d, a: 1 }),
      2: (d) => (log.push(2), { ...d, b: (d.a as number) + 1 }),
      3: (d) => (log.push(3), { ...d, c: (d.b as number) + 1 }),
    };
    expect(migrateDraft({}, 4, table)).toEqual({ a: 1, b: 2, c: 3, draftVersion: 4 });
    expect(log).toEqual([1, 2, 3]);
    expect(migrateDraft({ draftVersion: 3, b: 5 }, 4, table)).toEqual({ draftVersion: 4, b: 5, c: 6 });
    expect(log).toEqual([1, 2, 3, 3]);
  });

  it("a newer draft is rejected, a hole in the table throws", () => {
    expect(() => migrateDraft({ draftVersion: 9 }, 2)).toThrow();
    expect(() => migrateDraft({}, 3, { 1: (d) => d })).toThrow(/no draft migration from version 2/);
  });

  it("mergeDraft runs the chain: a v1 draft loads as ruleset mixed at the current version", () => {
    const d = mergeDraft({ draftVersion: 1, name: "Old", classes: [{ classId: "fighter", level: 3, choices: {} }] });
    expect(d.ruleset).toBe("mixed");
    expect(d.draftVersion).toBe(DRAFT_VERSION);
    expect(d.classes[0].level).toBe(3);
    expect(mergeDraft({ name: "No version", classes: [] }).draftVersion).toBe(DRAFT_VERSION);
    expect(() => mergeDraft({ draftVersion: DRAFT_VERSION + 1, classes: [] })).toThrow();
  });
});

describe("server health (SK9)", () => {
  it("parses the full body and the old {ok:true} body", () => {
    expect(parseHealth({ ok: true, apiVersion: 1, draftVersion: 2, dataSource: "bundled", bundleSha256: "ab" })).toEqual({
      ok: true, apiVersion: 1, draftVersion: 2, dataSource: "bundled", bundleSha256: "ab",
    });
    expect(parseHealth({ ok: true })).toEqual({ ok: true, apiVersion: undefined, draftVersion: undefined, dataSource: undefined, bundleSha256: null });
    expect(parseHealth({ ok: false })).toBeNull();
    expect(parseHealth([])).toBeNull();
    expect(parseHealth(null)).toBeNull();
  });
  it("the banner shows only when the server's draftVersion is older (or unreported)", () => {
    expect(serverIsOlder(parseHealth({ ok: true, draftVersion: 1 }), 2)).toBe(true);
    expect(serverIsOlder(parseHealth({ ok: true }), 2)).toBe(true);
    expect(serverIsOlder(parseHealth({ ok: true, draftVersion: 2 }), 2)).toBe(false);
    expect(serverIsOlder(parseHealth({ ok: true, draftVersion: 3 }), 2)).toBe(false);
    expect(serverIsOlder(null, 2)).toBe(false);
  });
});
