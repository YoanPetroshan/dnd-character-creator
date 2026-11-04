import { describe, expect, it } from "vitest";
import { newChoiceIds, syncSeen, type SeenState, type SeenTracker } from "./newChoices";
import { choice, resolution } from "./testFixtures";
import type { Choice, Resolution } from "../types";

/** A resolution at a given total level with the given cards. */
function at(level: number, choices: Choice[]): Resolution {
  const r = resolution({ choices });
  (r.sheet as { level: number }).level = level;
  return r;
}
const pending = (id: string) => choice({ id, status: "pending" });
const resolved = (id: string) => choice({ id, status: "resolved", selected: ["x"] });

/** Plays resolutions one after another the way NewChoicesProvider does. */
function play(start: SeenState, steps: Resolution[], tracker: SeenTracker | null = null) {
  let state = start;
  let t = tracker;
  for (const r of steps) {
    const out = syncSeen(state, t, r);
    state = out.state;
    t = out.tracker;
  }
  return { state, tracker: t as SeenTracker };
}
const fresh: SeenState = { seen: [], baselined: false };

describe("syncSeen / newChoiceIds (SK8)", () => {
  it("a first sync acknowledges everything: old characters do not light up", () => {
    const r = at(5, [pending("class:fighter:1:a"), resolved("class:fighter:1:b")]);
    const { state } = play(fresh, [r]);
    expect(state.baselined).toBe(true);
    expect(newChoiceIds(r.choices, state.seen)).toEqual([]);
  });

  it("raising a level makes the new pending card new", () => {
    const l4 = at(4, [resolved("class:fighter:1:a")]);
    const l5 = at(5, [resolved("class:fighter:1:a"), pending("class:fighter:5:asi")]);
    const { state } = play(fresh, [l4, l5]);
    expect(state.seen).not.toContain("class:fighter:5:asi");
    expect(newChoiceIds(l5.choices, state.seen)).toEqual(["class:fighter:5:asi"]);
  });

  it("the card stays new on later syncs and after a reload (stored state, empty tracker)", () => {
    const l5 = at(5, [resolved("a"), pending("class:fighter:5:asi")]);
    const first = play({ seen: ["a"], baselined: true }, [at(4, [resolved("a")]), l5]);
    const again = play(first.state, [l5, l5]);
    expect(newChoiceIds(l5.choices, again.state.seen)).toEqual(["class:fighter:5:asi"]);
    // a new session: no tracker, stored seen only
    const reloaded = play(first.state, [l5]);
    expect(newChoiceIds(l5.choices, reloaded.state.seen)).toEqual(["class:fighter:5:asi"]);
  });

  it("resolving clears the marker for good", () => {
    const l5 = at(5, [pending("c1")]);
    const s1 = play({ seen: [], baselined: true }, [at(4, []), l5]);
    expect(newChoiceIds(l5.choices, s1.state.seen)).toEqual(["c1"]);
    const done = at(5, [resolved("c1")]);
    const s2 = play(s1.state, [done], s1.tracker);
    expect(s2.state.seen).toContain("c1");
    expect(newChoiceIds(done.choices, s2.state.seen)).toEqual([]);
    // un-picking later does not make it new again
    const back = at(5, [pending("c1")]);
    expect(newChoiceIds(back.choices, play(s2.state, [back], s2.tracker).state.seen)).toEqual([]);
  });

  it("a card that appears without a level raise (class, subclass, species picked) is not new", () => {
    const s = play({ seen: [], baselined: true }, [at(0, []), at(1, [pending("class:wizard:1:skills")]), at(1, [pending("class:wizard:1:skills"), pending("species:x")])]);
    expect(newChoiceIds([pending("class:wizard:1:skills"), pending("species:x")], s.state.seen)).toEqual([]);
  });

  it("adding a second class at level 1 is a level raise", () => {
    const a = at(5, [resolved("a")]);
    const b = at(6, [resolved("a"), pending("class:rogue:1:skills")]);
    const { state } = play({ seen: ["a"], baselined: true }, [a, b]);
    expect(newChoiceIds(b.choices, state.seen)).toEqual(["class:rogue:1:skills"]);
  });

  it("unavailable cards are acknowledged and never new", () => {
    const r = at(3, [choice({ id: "u", status: "unavailable" })]);
    expect(newChoiceIds(r.choices, play(fresh, [r]).state.seen)).toEqual([]);
  });

  it("an unchanged resolution reports no change", () => {
    const r = at(2, [resolved("a")]);
    const first = syncSeen(fresh, null, r);
    const second = syncSeen(first.state, first.tracker, r);
    expect(second.changed).toBe(false);
    expect(second.state.seen).toBe(first.state.seen);
  });
});
