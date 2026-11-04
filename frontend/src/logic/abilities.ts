import type { Ability } from "../types";

export const ABILITIES: Ability[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
export const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
export const POINT_BUY_COST: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
export const POINT_BUY_BUDGET = 27;

/** Points spent by a set of base scores under point buy (out-of-range scores cost 0, as before). */
export function pointBuySpent(base: Record<Ability, number>): number {
  return ABILITIES.reduce((sum, a) => sum + (POINT_BUY_COST[base[a]] ?? 0), 0);
}

/** May `ability` go up by one point without leaving the budget? */
export function canIncrement(base: Record<Ability, number>, ability: Ability): boolean {
  const score = base[ability];
  const currentCost = POINT_BUY_COST[score] ?? 0;
  const nextCost = POINT_BUY_COST[score + 1];
  return score < 15 && nextCost !== undefined && pointBuySpent(base) - currentCost + nextCost <= POINT_BUY_BUDGET;
}

/** Standard array: picking a value another ability holds swaps the two, so
 *  the selects never lock. Returns the new base scores. */
export function setStandardScore(base: Record<Ability, number>, ability: Ability, value: number): Record<Ability, number> {
  const holder = ABILITIES.find((a) => a !== ability && base[a] === value);
  const next = { ...base, [ability]: value };
  if (holder) next[holder] = base[ability];
  return next;
}

/** 4d6 drop the lowest: the sum of the three highest of the four dice (each 1..6). */
export function scoreFromDice(dice: number[]): number {
  const sorted = [...dice].sort((a, b) => a - b);
  return sorted[1] + sorted[2] + sorted[3];
}

/** 4d6, drop the lowest die. Uses crypto randomness where available. */
export function rollAbilityScore(): number {
  const buf = new Uint32Array(4);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) crypto.getRandomValues(buf);
  else for (let i = 0; i < 4; i++) buf[i] = Math.floor(Math.random() * 0xffffffff);
  return scoreFromDice(Array.from(buf, (n) => (n % 6) + 1));
}

/** "+2" / "-1" / "—" for an unknown modifier. */
export function formatModifier(modifier: number | undefined): string {
  return modifier === undefined ? "—" : modifier >= 0 ? `+${modifier}` : String(modifier);
}
