import type { Resolution } from "../types";

function sortedSlots(slots: Record<string, number> | undefined): [number, number][] {
  return Object.entries(slots ?? {})
    .map(([level, count]): [number, number] => [Number(level), count])
    .filter(([, count]) => count > 0)
    .sort((a, b) => a[0] - b[0]);
}

/** Plain-text spell slot lines from derived.spellSlots / derived.warlockSpellSlots.
 *  `classId` limits the pact line to a Warlock tab; omit it (export page) to show both. */
export function SpellSlotsSummary({ resolution, classId }: { resolution: Resolution; classId?: string }) {
  const { spellSlots, warlockSpellSlots, slotGrantingClasses = [] } = resolution.derived;
  const shared = sortedSlots(spellSlots);
  const pact = sortedSlots(warlockSpellSlots);
  // The shared pool is "common" exactly when more than one class grants slots (server-computed).
  const sharers = slotGrantingClasses.length;
  const showPact = pact.length > 0 && (classId === undefined || classId === "warlock");
  const showShared = shared.length > 0 && (classId === undefined || classId === "warlock" || (classId !== undefined && slotGrantingClasses.includes(classId)));
  return (
    <>
      {showShared && (
        <p>
          Клетки за заклинания: {shared.map(([level, count]) => `ниво ${level} ×${count}`).join(", ")}
          {sharers > 1 && " (общи за всички класове)"}
        </p>
      )}
      {showPact && <p>Магия на договора: {pact.map(([level, count]) => `${count} × ниво ${level}`).join(", ")}</p>}
    </>
  );
}
