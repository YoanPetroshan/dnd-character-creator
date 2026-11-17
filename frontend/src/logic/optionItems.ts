import type { Choice, ChoiceOption } from "../types";

/** Pieces of a starting-equipment option id that are not catalog items: a gold pick ("gp-10"), an open choice
 *  ("any-martial-weapons") and the monk tool placeholder. */
const NOT_AN_ITEM = /^(gp-\d+|any-.*|monk-tool)$/;

/** Does this choice offer items (starting equipment, weapon mastery picks)? Only then do its rows get an item eye. */
export function isItemChoice(choice: Choice): boolean {
  return choice.source.kind === "equipment" || choice.id.endsWith(":weapon-mastery");
}

/** The item ids an option of an item choice stands for: its id split on "+" (a package is "a+b+gp-10"), without gold
 *  picks and open choices. Empty when the option has no catalog item (no eye). */
export function optionItemIds(choice: Choice, option: ChoiceOption): string[] {
  if (!isItemChoice(choice)) return [];
  return option.id.split("+").filter((part) => part !== "" && !NOT_AN_ITEM.test(part));
}
