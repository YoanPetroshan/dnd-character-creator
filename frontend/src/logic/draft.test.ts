import { describe, expect, it } from "vitest";
import { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, reducer, sanitizeDraft, totalLevel } from "./draft";
import type { Draft } from "../types";

const withClasses = (classes: unknown[]) => ({ draftVersion: DRAFT_VERSION, classes });

describe("mergeDraft", () => {
  it("throws on a draft written by a newer version", () => {
    expect(() => mergeDraft({ draftVersion: DRAFT_VERSION + 1, classes: [] })).toThrow(/по-нова версия/);
  });
  it("throws on non-objects", () => {
    for (const v of [null, undefined, 5, "x", true, []]) expect(() => mergeDraft(v), String(v)).toThrow(/не е чернова/);
  });
  it("throws on an object without any draft key (e.g. an exported sheet)", () => {
    expect(() => mergeDraft({ sheet: {}, derived: {} })).toThrow(/не прилича на чернова/);
  });
  it("accepts an older version and stamps the current one, filling defaults", () => {
    const d = mergeDraft({ draftVersion: 1, classes: [{ classId: "fighter", level: 3, choices: {} }] });
    expect(d.draftVersion).toBe(DRAFT_VERSION);
    expect(d.ruleset).toBe("mixed");
    expect(d.preferences.usePrerequisites).toEqual({ feats: true, multiclass: true });
    expect(d.abilities.base.STR).toBe(10);
  });
  it("accepts a draft with no version at all", () => {
    expect(mergeDraft({ classes: [] }).draftVersion).toBe(DRAFT_VERSION);
  });
  it("drops null / non-object / id-less class entries", () => {
    const d = mergeDraft(withClasses([null, 5, "x", [], { level: 3 }, { classId: "" }, { classId: 7 }, { classId: "bard", level: 2, choices: {} }]));
    expect(d.classes.map((c) => c.classId)).toEqual(["bard"]);
  });
  it("drops a duplicated class, keeping the first", () => {
    const d = mergeDraft(withClasses([{ classId: "bard", level: 2 }, { classId: "bard", level: 9 }]));
    expect(d.classes).toHaveLength(1);
    expect(d.classes[0].level).toBe(2);
  });
  it("clamps levels to 1..20 and repairs bad ones", () => {
    const lv = (level: unknown) => mergeDraft(withClasses([{ classId: "fighter", level }])).classes[0].level;
    expect(lv(0)).toBe(1);
    expect(lv(-4)).toBe(1);
    expect(lv(21)).toBe(20);
    expect(lv(999)).toBe(20);
    expect(lv(3.9)).toBe(3);
    expect(lv(20)).toBe(20);
    expect(lv("5")).toBe(1);
    expect(lv(NaN)).toBe(1);
    expect(lv(Infinity)).toBe(1);
    expect(lv(undefined)).toBe(1);
  });
  it("repairs missing / invalid choices to {}", () => {
    expect(mergeDraft(withClasses([{ classId: "fighter", level: 1 }])).classes[0].choices).toEqual({});
    expect(mergeDraft(withClasses([{ classId: "fighter", level: 1, choices: [] }])).classes[0].choices).toEqual({});
  });
  it("drops malformed equipment.added entries", () => {
    const d = mergeDraft({
      draftVersion: 2,
      equipment: { choices: {}, skipped: false, added: [null, { itemId: "a", qty: "2" }, { qty: 1 }, { itemId: "b", qty: NaN }, { itemId: "ok", qty: 2, equipped: true }] },
    });
    expect(d.equipment.added).toEqual([{ itemId: "ok", qty: 2, equipped: true }]);
  });
  it("keeps stored values of the right type and ignores wrong types", () => {
    const d = mergeDraft({ draftVersion: 2, name: "Ана", ruleset: 5, sources: ["srd"] });
    expect(d.name).toBe("Ана");
    expect(d.ruleset).toBe("mixed");
    expect(d.sources).toEqual(["srd"]);
  });
  it("does not mutate emptyDraft", () => {
    const before = JSON.stringify(emptyDraft);
    mergeDraft({ draftVersion: 2, name: "x", classes: [{ classId: "bard", level: 2 }] });
    expect(JSON.stringify(emptyDraft)).toBe(before);
  });
  it("a round trip of a merged draft is stable", () => {
    const d = mergeDraft({ draftVersion: 2, name: "x", classes: [{ classId: "bard", level: 2, choices: { a: ["b"] } }] });
    expect(mergeDraft(JSON.parse(JSON.stringify(d)))).toEqual(d);
  });
});

describe("sanitizeDraft", () => {
  it("tolerates a missing equipment object", () => {
    const d = sanitizeDraft({ ...emptyDraft, equipment: undefined as never });
    expect(d.equipment.added).toEqual([]);
  });
});

describe("reducer", () => {
  const two: Draft = { ...emptyDraft, classes: [{ classId: "fighter", level: 10, choices: {} }, { classId: "wizard", level: 8, choices: {} }] };

  it("totalLevel sums levels", () => expect(totalLevel(two)).toBe(18));
  it("SET_CLASS_LEVEL caps the whole character at 20", () => {
    expect(totalLevel(reducer(two, { type: "SET_CLASS_LEVEL", classId: "wizard", level: 20 }))).toBe(MAX_TOTAL_LEVEL);
    expect(reducer(two, { type: "SET_CLASS_LEVEL", classId: "fighter", level: 0 }).classes[0].level).toBe(1);
  });
  it("ADD_CLASS is a no-op for a duplicate and at the level cap", () => {
    expect(reducer(two, { type: "ADD_CLASS", classId: "fighter" })).toBe(two);
    const full = reducer(two, { type: "SET_CLASS_LEVEL", classId: "wizard", level: 10 });
    expect(reducer(full, { type: "ADD_CLASS", classId: "rogue" })).toBe(full);
    expect(reducer(two, { type: "ADD_CLASS", classId: "rogue" }).classes.map((c) => c.classId)).toEqual(["fighter", "wizard", "rogue"]);
  });
  it("SET_CLASS replaces everything and clears equipment choices", () => {
    const d = reducer({ ...two, equipment: { choices: { x: ["y"] }, added: [], skipped: false } }, { type: "SET_CLASS", classId: "bard" });
    expect(d.classes).toEqual([{ classId: "bard", level: 1, choices: {} }]);
    expect(d.equipment.choices).toEqual({});
  });
  it("TOGGLE_CHOICE_OPTION adds, removes, and replaces the oldest at the count", () => {
    const toggle = (d: Draft, optionId: string, count: number) =>
      reducer(d, { type: "TOGGLE_CHOICE_OPTION", source: "class", choiceId: "class:fighter:4:asi", optionId, count });
    let d = toggle(two, "a", 2);
    d = toggle(d, "b", 2);
    expect(d.classes[0].choices["class:fighter:4:asi"]).toEqual(["a", "b"]);
    d = toggle(d, "c", 2);
    expect(d.classes[0].choices["class:fighter:4:asi"]).toEqual(["b", "c"]);
    d = toggle(d, "b", 2);
    expect(d.classes[0].choices["class:fighter:4:asi"]).toEqual(["c"]);
  });
  it("CLEAR_STALE_SELECTIONS keeps only the listed ids", () => {
    const d = reducer(
      { ...two, classes: [{ classId: "fighter", level: 4, subclassId: "champion", choices: { keep: ["1"], drop: ["2"] } }] },
      { type: "CLEAR_STALE_SELECTIONS", keepIds: ["keep"], clearSubclassFor: ["fighter"] }
    );
    expect(d.classes[0].choices).toEqual({ keep: ["1"] });
    expect(d.classes[0].subclassId).toBeUndefined();
  });
  it("RESET returns the empty draft", () => expect(reducer(two, { type: "RESET" })).toBe(emptyDraft));
});
