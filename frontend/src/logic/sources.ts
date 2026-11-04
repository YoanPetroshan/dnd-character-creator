/** Book code the server appends to a feat label when it has to tell
 *  same-named options apart, e.g. "Athlete (XPHB)" -> "XPHB".
 *  Moved verbatim from ChoicePicker (SK1). */
const SOURCE_SUFFIX = /\s\(([A-Z][A-Z0-9]{1,7})\)$/;
export function optionSource(label: string): string | null {
  const m = SOURCE_SUFFIX.exec(label);
  return m ? m[1] : null;
}

/** Is a source enabled for a draft's `sources` list? [] means "everything". */
export function sourceOn(draftSources: string[], id: string): boolean {
  return draftSources.length === 0 || draftSources.some((x) => x.toLowerCase() === id.toLowerCase());
}

/** The new `sources` list after switching one source on or off.
 *  [] means "everything", so all-on collapses to [] and none-on becomes SRD only. */
export function toggleSource(draftSources: string[], allSourceIds: string[], id: string, on: boolean): string[] {
  const current = draftSources.length === 0 ? allSourceIds : draftSources;
  const next = on
    ? [...current.filter((x) => x.toLowerCase() !== id.toLowerCase()), id]
    : current.filter((x) => x.toLowerCase() !== id.toLowerCase());
  const all = allSourceIds.every((x) => next.some((n) => n.toLowerCase() === x.toLowerCase()));
  return all ? [] : next.length === 0 ? ["srd"] : next;
}
