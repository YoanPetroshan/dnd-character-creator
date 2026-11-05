import type { Choice, Problem, Resolution } from "../types";

export type MissingPart = "class" | "species" | "background";

export interface ExportReadiness {
  /** Missing parts; ExportPage prints `t.exportPage.missing[part]`. */
  missingParts: MissingPart[];
  /** Pending cards that block export (equipment and optional cards never do). */
  pendingChoices: Choice[];
  /** Pending equipment cards: shown as a note, never blocking. */
  pendingEquipment: Choice[];
  problems: Problem[];
  canExport: boolean;
}

/** Must mirror server/service.py `_pending_export_problems` (plus the resolve
 *  problems that /api/export/<fmt> also refuses on): equipment choices never
 *  block export, `optional` cards never block, a character needs a class,
 *  species and background, and only status "pending" cards count (an
 *  "unavailable" card never blocks). `error` is the resolver's last failure:
 *  a failed re-resolve means the data on screen may be stale, so export is
 *  not offered. */
export function exportReadiness(resolution: Resolution, error: unknown): ExportReadiness {
  const allPending = resolution.choices.filter((c) => c.status === "pending");
  const pendingChoices = allPending.filter((c) => c.source.kind !== "equipment" && !c.optional);
  const pendingEquipment = allPending.filter((c) => c.source.kind === "equipment");
  const missingParts = [
    resolution.sheet.classes.length === 0 && "class",
    !resolution.sheet.species && "species",
    !resolution.sheet.background && "background",
  ].filter((m): m is MissingPart => typeof m === "string");
  const canExport = !error && resolution.problems.length === 0 && pendingChoices.length === 0 && missingParts.length === 0;
  return { missingParts, pendingChoices, pendingEquipment, problems: resolution.problems, canExport };
}
