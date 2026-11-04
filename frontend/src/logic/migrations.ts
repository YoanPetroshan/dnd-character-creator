// Draft migration chain (SK9). A stored or imported draft carries `draftVersion` (a draft without
// one is version 1). Each entry upgrades a draft by ONE version; migrateDraft applies them in order
// up to the version of this build. mergeDraft runs it first, then fills defaults and sanitizes.
// When DRAFT_VERSION is bumped, add the step from the old version here (and a test).
import { MsgError, msg } from "./messages";

export type DraftRecord = Record<string, unknown>;
export type Migration = (draft: DraftRecord) => DraftRecord;
export type MigrationTable = Record<number, Migration>;

export const MIGRATIONS: MigrationTable = {
  // v1 -> v2: `ruleset` was added; a v1 draft behaved like "mixed"
  1: (d) => ({ ...d, ruleset: typeof d.ruleset === "string" ? d.ruleset : "mixed" }),
};

/** The version a stored draft claims (none, or anything that is not a positive integer, means 1). */
export function draftVersionOf(draft: DraftRecord): number {
  const v = draft.draftVersion;
  return typeof v === "number" && Number.isInteger(v) && v >= 1 ? v : 1;
}

/** Upgrades `draft` to `target`. A newer draft is rejected ("draft.newer"); a missing step in the
 *  table is a programming error and throws (the chain must be complete). The input is not mutated. */
export function migrateDraft(draft: DraftRecord, target: number, table: MigrationTable = MIGRATIONS): DraftRecord {
  let version = draftVersionOf(draft);
  if (version > target) throw new MsgError(msg("draft.newer"));
  let out = draft;
  while (version < target) {
    const step = table[version];
    if (!step) throw new Error(`no draft migration from version ${version}`);
    out = { ...step(out), draftVersion: version + 1 };
    version += 1;
  }
  return out;
}
