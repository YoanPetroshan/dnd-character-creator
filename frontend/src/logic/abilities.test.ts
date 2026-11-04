import { describe, expect, it } from "vitest";
import { canIncrement, formatModifier, pointBuySpent, scoreFromDice, setStandardScore } from "./abilities";
import type { Ability } from "../types";

const base = (o: Partial<Record<Ability, number>> = {}) => ({ STR: 8, DEX: 8, CON: 8, INT: 8, WIS: 8, CHA: 8, ...o });

describe("pointBuySpent", () => {
  it("all 8s cost nothing", () => expect(pointBuySpent(base())).toBe(0));
  it("the default 10s cost 12", () => expect(pointBuySpent(base({ STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 }))).toBe(12));
  it("a full 27-point build: 15 15 15 8 8 8", () => expect(pointBuySpent(base({ STR: 15, DEX: 15, CON: 15 }))).toBe(27));
  it("the standard array 15 14 13 12 10 8 costs 27", () =>
    expect(pointBuySpent({ STR: 15, DEX: 14, CON: 13, INT: 12, WIS: 10, CHA: 8 })).toBe(9 + 7 + 5 + 4 + 2 + 0));
  it("scores outside 8..15 count as 0", () => expect(pointBuySpent(base({ STR: 18, DEX: 3 }))).toBe(0));
});

describe("canIncrement", () => {
  it("allows a cheap step inside the budget", () => expect(canIncrement(base(), "STR")).toBe(true));
  it("stops at 15", () => expect(canIncrement(base({ STR: 15 }), "STR")).toBe(false));
  it("stops when the next step would exceed 27 points", () => {
    const b = base({ STR: 15, DEX: 15, CON: 15 }); // 27 spent
    expect(canIncrement(b, "INT")).toBe(false);
  });
  it("allows the last point exactly", () => {
    const b = base({ STR: 15, DEX: 15, CON: 14, INT: 8 }); // 9+9+7=25; 8->9 costs 1
    expect(canIncrement(b, "INT")).toBe(true);
    expect(canIncrement(base({ STR: 15, DEX: 15, CON: 14, INT: 9, WIS: 9 }), "CHA")).toBe(false); // 27 spent
  });
});

describe("setStandardScore", () => {
  const std = { STR: 15, DEX: 14, CON: 13, INT: 12, WIS: 10, CHA: 8 };
  it("swaps with the ability that holds the picked value", () =>
    expect(setStandardScore(std, "STR", 8)).toEqual({ ...std, STR: 8, CHA: 15 }));
  it("does not mutate its input", () => {
    const copy = { ...std };
    setStandardScore(std, "STR", 8);
    expect(std).toEqual(copy);
  });
  it("a value nobody holds just sets", () => expect(setStandardScore(std, "CHA", 9)).toEqual({ ...std, CHA: 9 }));
  it("picking the value it already has changes nothing", () => expect(setStandardScore(std, "DEX", 14)).toEqual(std));
});

describe("scoreFromDice", () => {
  it("drops the lowest die", () => {
    expect(scoreFromDice([1, 6, 5, 4])).toBe(15);
    expect(scoreFromDice([6, 6, 6, 6])).toBe(18);
    expect(scoreFromDice([1, 1, 1, 1])).toBe(3);
    expect(scoreFromDice([2, 3, 3, 1])).toBe(8);
  });
  it("does not mutate the dice", () => {
    const d = [3, 1, 2, 6];
    scoreFromDice(d);
    expect(d).toEqual([3, 1, 2, 6]);
  });
});

describe("formatModifier", () => {
  it("signs", () => {
    expect(formatModifier(3)).toBe("+3");
    expect(formatModifier(0)).toBe("+0");
    expect(formatModifier(-1)).toBe("-1");
    expect(formatModifier(undefined)).toBe("—");
  });
});
