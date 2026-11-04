// Builders for the unit tests (no test runner imports, so tsc -b can check it).
import type { Choice, Draft, Problem, Resolution } from "../types";

export function choice(over: Partial<Choice> & { id: string }): Choice {
  return {
    source: { kind: "class" },
    label: over.id,
    description: "",
    count: 1,
    options: [],
    selected: [],
    status: "pending",
    ...over,
  } as Choice;
}

/** A resolution that is export-ready unless the overrides say otherwise. */
export function resolution(over: { choices?: Choice[]; problems?: Problem[]; classes?: number; species?: boolean; background?: boolean } = {}): Resolution {
  return {
    sheet: {
      classes: Array.from({ length: over.classes ?? 1 }, () => ({})),
      species: over.species === false ? null : { id: "human" },
      background: over.background === false ? null : { id: "acolyte" },
    },
    choices: over.choices ?? [],
    derived: {},
    problems: over.problems ?? [],
    warnings: [],
    pruned: [],
  } as unknown as Resolution;
}

export function draftWith(over: Partial<Draft>): Draft {
  return over as Draft;
}
