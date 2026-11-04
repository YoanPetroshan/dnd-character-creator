import { describe, expect, it } from "vitest";
import { STEPS, stepBadgeCount, stepStatus } from "./steps";
import { choice, resolution } from "./testFixtures";

describe("STEPS", () => {
  it("keeps the seven routes in order", () => {
    expect(STEPS.map((s) => s.path)).toEqual(["/home", "/class", "/background", "/species", "/abilities", "/equipment", "/export"]);
  });
});

// The CURRENT badge behaviour (SK3 changes it for empty steps).
describe("stepStatus (current behaviour)", () => {
  it("no resolution: nothing outstanding, nothing done", () => {
    const s = stepStatus(null);
    for (const step of STEPS) expect(s[step.path]).toEqual({ pending: 0, problems: 0, missing: 0, done: false });
  });

  it("a clean resolution is done everywhere", () => {
    const s = stepStatus(resolution());
    for (const step of STEPS) expect(s[step.path].done).toBe(true);
  });

  it("an EMPTY step gets no badge today (no species/background/class is not counted)", () => {
    const s = stepStatus(resolution({ classes: 0, species: false, background: false }));
    for (const step of STEPS) expect(stepBadgeCount(s[step.path])).toBe(0);
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
