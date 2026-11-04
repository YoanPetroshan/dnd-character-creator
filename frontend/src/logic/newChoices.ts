// "New since last visit" marker for level-up choices (SK8). Pure.
//
// `seen` = the choice ids the app has acknowledged for one character. A PENDING card whose
// id is not in `seen` is "new" (data-new="true", the text marker, the header link).
//
// syncSeen(resolution) decides which ids become acknowledged:
//   - every non-pending card (resolved / unavailable): resolving clears the marker for good;
//   - an item that was never synced (`baselined` false: an old character, or a brand-new one)
//     acknowledges everything it has, once;
//   - afterwards a pending card that APPEARS (not in the previous resolution of this session) is
//     acknowledged at once, unless the total level went up in the same step: then it is a
//     level-up choice and stays unseen, also across reloads (nothing is absorbed on the first
//     sync of a session, only the previous session's state counts).
import type { Choice, Resolution } from "../types";

export interface SeenState {
  seen: string[];
  baselined: boolean;
}

/** What the previous resolution of this session looked like (null before the first one). */
export interface SeenTracker {
  ids: string[];
  level: number;
}

export interface SeenSync {
  state: SeenState;
  tracker: SeenTracker;
  changed: boolean;
}

export function syncSeen(state: SeenState, tracker: SeenTracker | null, resolution: Resolution): SeenSync {
  const choices = resolution.choices;
  const level = resolution.sheet?.level ?? 0;
  const seen = new Set(state.seen);
  const before = seen.size;
  const prevIds = tracker ? new Set(tracker.ids) : null;
  // a level-up needs a real previous level: going from "nothing" to a first class is not one
  const raised = tracker !== null && tracker.level >= 1 && level > tracker.level;

  for (const c of choices) {
    if (c.status !== "pending") seen.add(c.id);
    else if (!state.baselined) seen.add(c.id);
    else if (prevIds && !prevIds.has(c.id) && !raised) seen.add(c.id);
  }
  const baselined = true;
  const changed = seen.size !== before || !state.baselined;
  return {
    state: { seen: changed ? [...seen] : state.seen, baselined },
    tracker: { ids: choices.map((c) => c.id), level },
    changed,
  };
}

/** Pending cards that are new: pending and not acknowledged. */
export function newChoiceIds(choices: Choice[], seen: string[]): string[] {
  const s = new Set(seen);
  return choices.filter((c) => c.status === "pending" && !s.has(c.id)).map((c) => c.id);
}
