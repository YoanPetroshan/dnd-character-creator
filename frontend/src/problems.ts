import type { Problem } from "./types";

export type ProblemStep = "class" | "background" | "species" | "abilities" | "equipment";

/** Which wizard step a blocking resolve() problem belongs to, so it can be
 *  shown (and counted in the StepNav badge) where the user can fix it instead
 *  of only on the Export page. Unmapped problems stay Export-only. Mirrors the
 *  problem ids in server/engine/resolve.py and normalize.py. */
export function stepForProblem(p: Problem): ProblemStep | null {
  const id = p.id;
  if (id.startsWith("feat-duplicate-")) {
    // feat-duplicate-{feat}-{choice id}: the choice id says where the pick lives
    if (id.includes("-species:")) return "species";
    if (id.includes("-class:")) return "class";
    return "background";
  }
  if (id.startsWith("feat-prerequisite-unmet-")) return "class";
  if (
    id.startsWith("multiclass-prerequisite-unmet-") ||
    id === "total-level-exceeded" ||
    id === "duplicate-class" ||
    id === "unknown-class" ||
    id === "unknown-subclass" ||
    id === "subclass-mismatch" ||
    id === "level-unsupported" ||
    id === "malformed-classes" ||
    id === "malformed-class-entry"
  )
    return "class";
  if (id === "unknown-background" || id === "malformed-background") return "background";
  if (id === "unknown-species" || id === "unknown-subspecies" || id === "subspecies-mismatch" || id === "malformed-species")
    return "species";
  if (
    id.startsWith("point-buy-") ||
    id.startsWith("ability-") ||
    id === "standard-array-mismatch" ||
    id === "roll-out-of-range"
  )
    return "abilities";
  if (id.startsWith("over-selected-") || id === "malformed-equipment-added" || id === "malformed-equipment-choices")
    return "equipment";
  return null;
}

export function problemsForStep(problems: Problem[], step: ProblemStep): Problem[] {
  return problems.filter((p) => stepForProblem(p) === step);
}
