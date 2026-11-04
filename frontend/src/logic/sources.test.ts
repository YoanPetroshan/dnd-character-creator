import { describe, expect, it } from "vitest";
import { optionSource, sourceOn, toggleSource } from "./sources";

const ALL = ["srd", "PHB", "XGE", "TCE"];

describe("toggleSource", () => {
  it("turning the last missing source on collapses to [] (everything)", () => {
    expect(toggleSource(["srd", "PHB", "XGE"], ALL, "TCE", true)).toEqual([]);
  });
  it("turning one source off from 'everything' lists all the others", () => {
    expect(toggleSource([], ALL, "XGE", false)).toEqual(["srd", "PHB", "TCE"]);
  });
  it("turning the last source off leaves SRD only", () => {
    expect(toggleSource(["PHB"], ALL, "PHB", false)).toEqual(["srd"]);
  });
  it("is case-insensitive and never duplicates", () => {
    expect(toggleSource(["srd", "phb"], ALL, "PHB", true)).toEqual(["srd", "PHB"]);
    expect(toggleSource(["srd", "PHB"], ALL, "phb", false)).toEqual(["srd"]);
  });
  it("adds a source to a narrow list", () => {
    expect(toggleSource(["srd"], ALL, "XGE", true)).toEqual(["srd", "XGE"]);
  });
  it("with no known sources, switching on from [] stays []", () => {
    expect(toggleSource([], [], "X", true)).toEqual([]);
  });
});

describe("sourceOn", () => {
  it("[] means everything is on", () => expect(sourceOn([], "XGE")).toBe(true));
  it("matches case-insensitively", () => {
    expect(sourceOn(["srd", "phb"], "PHB")).toBe(true);
    expect(sourceOn(["srd"], "PHB")).toBe(false);
  });
});

describe("optionSource", () => {
  it("reads the trailing book code", () => {
    expect(optionSource("Athlete (XPHB)")).toBe("XPHB");
    expect(optionSource("Fey Touched (TCE)")).toBe("TCE");
    expect(optionSource("Tough (PHB)")).toBe("PHB");
    expect(optionSource("Foo (A1)")).toBe("A1");
  });
  it("is null without a suffix", () => {
    expect(optionSource("Athlete")).toBeNull();
    expect(optionSource("")).toBeNull();
  });
  it("ignores lowercase, too short/long codes and a code that is not last", () => {
    expect(optionSource("Athlete (xphb)")).toBeNull();
    expect(optionSource("Athlete (X)")).toBeNull();
    expect(optionSource("Athlete (ABCDEFGHI)")).toBeNull();
    expect(optionSource("Athlete (XPHB) extra")).toBeNull();
    expect(optionSource("Athlete(XPHB)")).toBeNull();
    expect(optionSource("Ranger (Fey Wanderer)")).toBeNull();
  });
  it("takes the last group of a label with several parentheses", () => {
    expect(optionSource("Spell (Ritual) (PHB)")).toBe("PHB");
  });
});
