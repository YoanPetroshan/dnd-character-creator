import type { Choice } from "../types";

/** Which Class-step tab a class card belongs to: the "Заклинания" tab holds
 *  the spell-pick cards, every other class card is on "Способности".
 *  Moved verbatim from ClassPage (SK1). Cards are keyed by their choice id
 *  ("class:<classId>:..."), so this is a pure string test. */
export function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known") || choiceId.endsWith(":spellbook") || choiceId.includes(":mystic-arcanum-") || choiceId.includes(":spell-mastery-") || choiceId.endsWith(":signature-spells") || choiceId.endsWith(":feature:additional-magical-secrets") || choiceId.includes(":opt-pact-of-the-tome-xphb:") || /:feature:[a-z0-9-]+-(?:savant|improved-illusions|magical-discoveries)$/.test(choiceId);
}

/** Cid scoping shared by StepNav's badge counts and the step pages: a feat
 *  card's source.kind is "feat" for the class, background and species steps
 *  alike, so the step is told apart by the id prefix. */
export const isClassCid = (id: string): boolean => id.startsWith("class:");
export const isSpeciesCid = (id: string): boolean => id.startsWith("species:");
/** Background step: everything that is neither a class nor a species card. */
export const isBackgroundCid = (id: string): boolean => !id.startsWith("class:") && !id.startsWith("species:");

/** The class and feat cards that belong to one class block on the Class page. */
export function classChoicesFor(choices: Choice[], classId: string): Choice[] {
  return choices.filter((c) => (c.source.kind === "class" || c.source.kind === "feat") && c.id.startsWith(`class:${classId}:`));
}

/** Split one class's cards into the "Способности" list and the "Заклинания"
 *  list. C4: the Wizard's spellbook card comes first (prepared spells are
 *  drawn from it). */
export function splitClassChoices(classChoices: Choice[]): { featureChoices: Choice[]; spellChoices: Choice[] } {
  return {
    featureChoices: classChoices.filter((c) => !isSpellChoiceId(c.id)),
    spellChoices: classChoices
      .filter((c) => isSpellChoiceId(c.id))
      .sort((a, b) => Number(b.id.endsWith(":spellbook")) - Number(a.id.endsWith(":spellbook"))),
  };
}

/** Species step cards: species-sourced ones plus feat cards cascaded from a species pick. */
export function speciesChoicesOf(choices: Choice[]): Choice[] {
  return choices.filter((c) => c.source.kind === "species" || (c.source.kind === "feat" && c.id.startsWith("species:")));
}

/** Background step cards: background-sourced and feat cards that are neither class nor species. */
export function backgroundChoicesOf(choices: Choice[]): Choice[] {
  return choices.filter((c) => (c.source.kind === "background" || c.source.kind === "feat") && !c.id.startsWith("class:") && !c.id.startsWith("species:"));
}
