import type { Ability } from "../types";

// The resolution gives a caster's save DC and attack bonus but not the spellcasting ability. The
// ability is a fixed fact of the class (Fighter and Rogue only through their casting subclass), so it
// is looked up here and then CROSS-CHECKED against the server's own numbers: it is shown only when
// 8 + proficiency + modifier equals the server's DC (and, when present, proficiency + modifier its
// attack bonus). A mismatch (homebrew, unknown class) shows no ability rather than a wrong one.
const CLASS_ABILITY: Record<string, Ability> = {
  artificer: "INT",
  wizard: "INT",
  fighter: "INT", // Eldritch Knight
  rogue: "INT", // Arcane Trickster
  cleric: "WIS",
  druid: "WIS",
  ranger: "WIS",
  bard: "CHA",
  paladin: "CHA",
  sorcerer: "CHA",
  warlock: "CHA",
};

export function spellcastingAbility(
  classId: string,
  saveDC: number | null,
  attackBonus: number | null,
  modifiers: Partial<Record<Ability, number>> | undefined,
  proficiencyBonus: number | undefined,
): Ability | null {
  const ability = CLASS_ABILITY[classId];
  const mod = ability ? modifiers?.[ability] : undefined;
  if (!ability || mod === undefined || proficiencyBonus === undefined) return null;
  if (saveDC !== null && saveDC !== 8 + proficiencyBonus + mod) return null;
  if (attackBonus !== null && attackBonus !== proficiencyBonus + mod) return null;
  return saveDC === null && attackBonus === null ? null : ability;
}
