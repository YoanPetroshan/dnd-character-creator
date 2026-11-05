import { describe, expect, it } from "vitest";
import { exportReadiness } from "./exportReadiness";
import { choice, resolution } from "./testFixtures";

// Parity with server/service.py `_pending_export_problems` (and /api/export's
// refusal on resolve problems).
describe("exportReadiness", () => {
  it("a complete character can export", () => {
    const r = exportReadiness(resolution(), null);
    expect(r.canExport).toBe(true);
    expect(r.missingParts).toEqual([]);
    expect(r.pendingChoices).toEqual([]);
  });

  it("a pending class, background, species or feat card blocks", () => {
    for (const kind of ["class", "background", "species", "feat"] as const) {
      const r = exportReadiness(resolution({ choices: [choice({ id: `${kind}:x`, source: { kind } as never })] }), null);
      expect(r.canExport, kind).toBe(false);
      expect(r.pendingChoices.map((c) => c.id)).toEqual([`${kind}:x`]);
    }
  });

  it("a pending equipment card never blocks, but is reported", () => {
    const r = exportReadiness(resolution({ choices: [choice({ id: "class:fighter:1:equipment-choice-0", source: { kind: "equipment" } as never })] }), null);
    expect(r.canExport).toBe(true);
    expect(r.pendingChoices).toEqual([]);
    expect(r.pendingEquipment).toHaveLength(1);
  });

  it("an optional card never blocks", () => {
    const r = exportReadiness(resolution({ choices: [choice({ id: "class:x", optional: true })] }), null);
    expect(r.canExport).toBe(true);
    expect(r.pendingChoices).toEqual([]);
  });

  it("an unavailable card never blocks (only status pending counts)", () => {
    const r = exportReadiness(resolution({ choices: [choice({ id: "class:wizard:20:signature-spells", status: "unavailable" })] }), null);
    expect(r.canExport).toBe(true);
  });

  it("a resolved card does not block", () => {
    expect(exportReadiness(resolution({ choices: [choice({ id: "class:x", status: "resolved" as never })] }), null).canExport).toBe(true);
  });

  it("a missing class, species or background blocks, each with its own line", () => {
    expect(exportReadiness(resolution({ classes: 0 }), null)).toMatchObject({ canExport: false, missingParts: ["class"] });
    expect(exportReadiness(resolution({ species: false }), null)).toMatchObject({ canExport: false, missingParts: ["species"] });
    expect(exportReadiness(resolution({ background: false }), null)).toMatchObject({ canExport: false, missingParts: ["background"] });
    expect(exportReadiness(resolution({ classes: 0, species: false, background: false }), null).missingParts).toHaveLength(3);
  });

  it("a resolve problem blocks (the server refuses export on resolution.problems too)", () => {
    const problems = [{ id: "feat-prerequisite-unmet-x", message: "m" }];
    const r = exportReadiness(resolution({ problems }), null);
    expect(r.canExport).toBe(false);
    expect(r.problems).toBe(problems);
  });

  it("a failed re-resolve (error) blocks even a clean resolution", () => {
    expect(exportReadiness(resolution(), new Error("network")).canExport).toBe(false);
  });
});
