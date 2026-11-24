/** The conditions of the rules, by their English game term (kept English in both languages, like damage types). */
export const CONDITIONS = [
  "Blinded",
  "Charmed",
  "Deafened",
  "Exhaustion",
  "Frightened",
  "Grappled",
  "Incapacitated",
  "Invisible",
  "Paralyzed",
  "Petrified",
  "Poisoned",
  "Prone",
  "Restrained",
  "Stunned",
  "Unconscious",
] as const;

/** Current hit points from the maximum and the play state (never below 0). */
export function currentHp(maxHp: number, damage: number | undefined): number {
  return Math.max(0, maxHp - (damage ?? 0));
}
