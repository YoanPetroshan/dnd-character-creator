import { describe, expect, it } from "vitest";
import { STEPS, nextUnfinishedStep, stepBadgeCount, stepForChoice, stepStatus } from "./steps";
import { emptyDraft } from "./draft";
import { choice, resolution } from "./testFixtures";
import type { Draft } from "../types";

describe("STEPS", () => {
  it("keeps the eight routes in order (the sheet sits between Equipment and Export)", () => {
    expect(STEPS.map((s) => s.path)).toEqual(["/home", "/class", "/background", "/species", "/abilities", "/equipment", "/sheet", "/export"]);
  });
});

// Badge behaviour; SK3 added `missing` for an empty Class/Species/Background step.
describe("stepStatus (current behaviour)", () => {
  it("no resolution: nothing outstanding, nothing done", () => {
    const s = stepStatus(null);
    for (const step of STEPS) expect(s[step.path]).toEqual({ pending: 0, problems: 0, missing: 0, done: false });
  });

  it("a clean resolution is done everywhere", () => {
    const s = stepStatus(resolution());
    for (const step of STEPS) expect(s[step.path].done).toBe(true);
  });

  it("without a draft, an empty step is read from the resolution's sheet (SK3)", () => {
    const s = stepStatus(resolution({ classes: 0, species: false, background: false }));
    expect(["/class", "/species", "/background"].map((p) => s[p].missing)).toEqual([1, 1, 1]);
    for (const p of ["/home", "/abilities", "/equipment", "/export"]) expect(stepBadgeCount(s[p])).toBe(0);
  });

  it("counts pending cards on their own step and skips optional / non-pending ones", () => {
    const s = stepStatus(
      resolution({
        choices: [
          choice({ id: "class:fighter:4:asi" }),
          choice({ id: "class:fighter:1:prof-choice-0" }),
          choice({ id: "class:fighter:2:opt", optional: true }),
          choice({ id: "class:fighter:3:done", status: "resolved" as never }),
          choice({ id: "class:fighter:20:gone", status: "unavailable" }),
          choice({ id: "background:acolyte:languages", source: { kind: "background" } as never }),
          choice({ id: "species:human:languages", source: { kind: "species" } as never }),
          choice({ id: "class:fighter:1:equipment-choice-0", source: { kind: "equipment" } as never }),
          choice({ id: "class:fighter:1:equipment-choice-1", source: { kind: "equipment" } as never }),
        ],
      })
    );
    expect(s["/class"].pending).toBe(2);
    expect(s["/background"].pending).toBe(1);
    expect(s["/species"].pending).toBe(1);
    expect(s["/equipment"].pending).toBe(2);
    expect(s["/abilities"].pending).toBe(0);
    expect(s["/home"].pending).toBe(0);
    expect(s["/export"].pending).toBe(0);
    expect(s["/class"].done).toBe(false);
  });

  it("a feat card counts on exactly one step, by its cid", () => {
    const feat = (id: string) => choice({ id, source: { kind: "feat" } as never });
    const s = stepStatus(
      resolution({ choices: [feat("class:fighter:4:asi:feat:0:ability"), feat("feat:alert-xphb:x"), feat("species:human:feat:0:x")] })
    );
    expect([s["/class"].pending, s["/background"].pending, s["/species"].pending]).toEqual([1, 1, 1]);
  });

  it("problems count on the step that owns them and add to the badge", () => {
    const s = stepStatus(
      resolution({
        problems: [
          { id: "feat-prerequisite-unmet-x", message: "" },
          { id: "unknown-background", message: "" },
          { id: "point-buy-over-budget", message: "" },
          { id: "over-selected-x", message: "" },
          { id: "something-unmapped", message: "" },
        ],
        choices: [choice({ id: "class:fighter:4:asi" })],
      })
    );
    expect(s["/class"]).toMatchObject({ problems: 1, pending: 1, done: false });
    expect(stepBadgeCount(s["/class"])).toBe(2);
    expect(s["/background"].problems).toBe(1);
    expect(s["/abilities"].problems).toBe(1);
    expect(s["/equipment"].problems).toBe(1);
    expect(s["/species"].problems).toBe(0);
    expect(s["/export"].problems).toBe(0); // unmapped problems stay Export-only and are not badged
  });
});

const pickedDraft = {
  ...emptyDraft,
  classes: [{ classId: "fighter", level: 1 }],
  species: { id: "human", choices: {} },
  background: { id: "acolyte", choices: {} },
} as unknown as Draft;

describe("missing parts (SK3)", () => {
  it("an empty draft counts 1 on Class, Species and Background and badges them", () => {
    const s = stepStatus(resolution({ classes: 0, species: false, background: false }), emptyDraft);
    for (const p of ["/class", "/species", "/background"]) {
      expect(s[p]).toMatchObject({ missing: 1, pending: 0, problems: 0, done: false });
      expect(stepBadgeCount(s[p])).toBe(1);
    }
    for (const p of ["/home", "/abilities", "/equipment", "/export"]) expect(stepBadgeCount(s[p])).toBe(0);
  });

  it("picking a part clears only its own missing count", () => {
    const s = stepStatus(resolution({ species: false, background: false }), { ...emptyDraft, classes: pickedDraft.classes });
    expect([s["/class"].missing, s["/species"].missing, s["/background"].missing]).toEqual([0, 1, 1]);
  });

  it("missing adds to pending and problems in the badge", () => {
    const s = stepStatus(resolution({ species: false, choices: [choice({ id: "species:human:x", source: { kind: "species" } as never })] }), {
      ...pickedDraft,
      species: { choices: {} },
    });
    expect(s["/species"]).toMatchObject({ missing: 1, pending: 1 });
    expect(stepBadgeCount(s["/species"])).toBe(2);
  });

  it("no resolution: no missing count even for an empty draft (nothing flashes while loading)", () => {
    const s = stepStatus(null, emptyDraft);
    for (const step of STEPS) expect(s[step.path]).toEqual({ pending: 0, problems: 0, missing: 0, done: false });
  });

  it("a complete draft has no missing parts", () => {
    const s = stepStatus(resolution(), pickedDraft);
    for (const step of STEPS) expect(s[step.path].missing).toBe(0);
  });
});

describe("nextUnfinishedStep", () => {
  const empty = resolution({ classes: 0, species: false, background: false });

  it("empty draft -> the Class page", () => {
    expect(nextUnfinishedStep(empty, emptyDraft)).toBe("/class");
  });

  it("class picked -> the first of the remaining steps in STEPS order (Background)", () => {
    const d = { ...emptyDraft, classes: pickedDraft.classes } as Draft;
    expect(nextUnfinishedStep(resolution({ species: false, background: false }), d)).toBe("/background");
  });

  it("class and background picked -> Species", () => {
    const d = { ...emptyDraft, classes: pickedDraft.classes, background: pickedDraft.background } as Draft;
    expect(nextUnfinishedStep(resolution({ species: false }), d)).toBe("/species");
  });

  it("a pending card or a problem counts, in step order", () => {
    expect(nextUnfinishedStep(resolution({ choices: [choice({ id: "class:fighter:4:asi" })] }), pickedDraft)).toBe("/class");
    expect(nextUnfinishedStep(resolution({ problems: [{ id: "point-buy-over-budget", message: "" }] }), pickedDraft)).toBe("/abilities");
    const eq = choice({ id: "class:fighter:1:equipment-choice-0", source: { kind: "equipment" } as never });
    expect(nextUnfinishedStep(resolution({ choices: [eq] }), pickedDraft)).toBe("/equipment");
  });

  it("everything done -> Export", () => {
    expect(nextUnfinishedStep(resolution(), pickedDraft)).toBe("/export");
  });

  it("no resolution yet -> null (no link while loading)", () => {
    expect(nextUnfinishedStep(null, emptyDraft)).toBeNull();
  });
});

describe("stepForChoice", () => {
  it("class cards (and a feat cascaded from an ASI slot) belong to /class", () => {
    expect(stepForChoice("class:fighter:4:asi")).toBe("/class");
    expect(stepForChoice("class:wizard:1:spells-cantrips")).toBe("/class");
    expect(stepForChoice("class:fighter:4:asi:feat:0:ability")).toBe("/class");
  });
  it("species cards and species-granted feat cascades belong to /species", () => {
    expect(stepForChoice("species:human:languages")).toBe("/species");
    expect(stepForChoice("species:human:feat:0:x")).toBe("/species");
  });
  it("background cards and background-granted feat cascades belong to /background", () => {
    expect(stepForChoice("background:acolyte:languages")).toBe("/background");
    expect(stepForChoice("feat:alert-xphb:x")).toBe("/background");
  });
  it("equipment cards belong to /equipment, even with a class: prefix", () => {
    expect(stepForChoice("class:fighter:1:equipment-choice-0")).toBe("/equipment");
    expect(stepForChoice("background:acolyte:equipment-choice-1")).toBe("/equipment");
  });
});
