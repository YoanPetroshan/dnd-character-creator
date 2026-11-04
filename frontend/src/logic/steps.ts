import type { ChoiceSourceKind, Draft, Resolution } from "../types";
import { problemsForStep, type ProblemStep } from "../problems";
import { isBackgroundCid, isClassCid, isSpeciesCid } from "./choiceRouting";

export interface Step {
  path: string;
  label: string;
  // Most steps only ever show choices of their own kind. The Background
  // step also renders feat-sourced choices (a background-granted feat's
  // proficiency/ability-bonus/language picks — see BackgroundPage.tsx),
  // so its badge count must include "feat" too or it'll undercount. The
  // Class step has the same situation: a feat picked at an ASI slot can
  // cascade its own proficiency/ability-bonus/language sub-choices (see
  // ClassPage.tsx), so it also needs "feat" in its kind list.
  kind: ChoiceSourceKind[] | null;
  // A background-granted feat's cascaded choices (cid "feat:{index}:...")
  // and an ASI-selected feat's cascaded choices (cid
  // "class:{clsId}:{lvl}:asi:feat:{index}:...") share source.kind "feat",
  // so the plain `kind` list above can't tell them apart on its own — it
  // would double-count a single choice on BOTH the Class and Background
  // badges. `cidFilter`, when given, additionally requires a choice's id
  // to match before it counts toward this step, mirroring the same cid
  // scoping ClassPage.tsx / BackgroundPage.tsx apply to their own choice
  // lists. Omit it for steps that don't include "feat" in `kind`.
  cidFilter?: (id: string) => boolean;
  // Blocking resolve() problems that belong to this step also count.
  problemStep?: ProblemStep;
}

export const STEPS: Step[] = [
  { path: "/home", label: "Home", kind: null },
  { path: "/class", problemStep: "class", label: "Клас", kind: ["class", "feat"], cidFilter: isClassCid },
  { path: "/background", problemStep: "background", label: "Background", kind: ["background", "feat"], cidFilter: isBackgroundCid },
  { path: "/species", problemStep: "species", label: "Species", kind: ["species", "feat"], cidFilter: isSpeciesCid },
  { path: "/abilities", problemStep: "abilities", label: "Abilities", kind: null },
  { path: "/equipment", problemStep: "equipment", label: "Equipment", kind: ["equipment"] },
  { path: "/export", label: "Export", kind: null },
];

export interface StepStatus {
  /** Pending (non-optional) choice cards that belong to the step. */
  pending: number;
  /** Blocking resolve() problems that belong to the step. */
  problems: number;
  /** Required parts that are not chosen at all: 1 for an empty Class, Species
   *  or Background step, else 0. */
  missing: number;
  /** Nothing outstanding (and a resolution exists). */
  done: boolean;
}

/** Is the part a step is about still unchosen? Read from the draft when one
 *  is given (it is the user's truth), else from the resolution's sheet (the
 *  same test the export gate uses). */
function isMissing(path: string, resolution: Resolution, draft?: Draft): boolean {
  switch (path) {
    case "/class":
      return draft ? draft.classes.length === 0 : resolution.sheet.classes.length === 0;
    case "/species":
      return draft ? !draft.species.id : !resolution.sheet.species;
    case "/background":
      return draft ? !draft.background.id : !resolution.sheet.background;
    default:
      return false;
  }
}

/** Per-step status, keyed by step path. The StepNav badge is
 *  `problems + pending + missing`. Without a resolution nothing is counted
 *  (no badge flashes while the first resolve is loading). */
export function stepStatus(resolution: Resolution | null, draft?: Draft): Record<string, StepStatus> {
  const out: Record<string, StepStatus> = {};
  for (const step of STEPS) {
    let problems = 0;
    let pending = 0;
    let missing = 0;
    if (resolution) {
      missing = isMissing(step.path, resolution, draft) ? 1 : 0;
      problems = step.problemStep ? problemsForStep(resolution.problems, step.problemStep).length : 0;
      if (step.kind) {
        const kinds = step.kind;
        pending = resolution.choices.filter(
          (c) => kinds.includes(c.source.kind) && (!step.cidFilter || step.cidFilter(c.id)) && c.status === "pending" && !c.optional
        ).length;
      }
    }
    out[step.path] = { pending, problems, missing, done: resolution !== null && pending + problems + missing === 0 };
  }
  return out;
}

/** The number shown in the StepNav badge (0 = no badge). */
export function stepBadgeCount(status: StepStatus): number {
  return status.problems + status.pending + status.missing;
}

/** The first step, in STEPS order, that still has something outstanding
 *  (a missing part, a pending card or a blocking problem); Export when
 *  nothing is. null while there is no resolution yet. */
export function nextUnfinishedStep(resolution: Resolution | null, draft?: Draft): string | null {
  if (!resolution) return null;
  const status = stepStatus(resolution, draft);
  const next = STEPS.find((step) => stepBadgeCount(status[step.path]) > 0);
  return next ? next.path : "/export";
}

/** The step page that owns a choice card, from its cid. Equipment cards
 *  come first: a class's equipment cid ("class:<id>:1:equipment-choice-N")
 *  starts with "class:" but is shown on the Equipment page. */
export function stepForChoice(cid: string): string {
  if (/(^|:)equipment-choice-\d+$/.test(cid)) return "/equipment";
  if (isClassCid(cid)) return "/class";
  if (isSpeciesCid(cid)) return "/species";
  return "/background";
}
