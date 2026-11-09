// Display names of game content that the exports print from ids (server/catalog/reference_data.py
// SKILL_NAMES, LANGUAGE_NAMES, proficiency_label). Game content is not translated, so these live
// here and not in copy/.

export const SKILL_NAMES: Record<string, string> = {
  "skill-acrobatics": "Acrobatics",
  "skill-animal-handling": "Animal Handling",
  "skill-arcana": "Arcana",
  "skill-athletics": "Athletics",
  "skill-deception": "Deception",
  "skill-history": "History",
  "skill-insight": "Insight",
  "skill-intimidation": "Intimidation",
  "skill-investigation": "Investigation",
  "skill-medicine": "Medicine",
  "skill-nature": "Nature",
  "skill-perception": "Perception",
  "skill-performance": "Performance",
  "skill-persuasion": "Persuasion",
  "skill-religion": "Religion",
  "skill-sleight-of-hand": "Sleight of Hand",
  "skill-stealth": "Stealth",
  "skill-survival": "Survival",
};

export const LANGUAGE_NAMES: Record<string, string> = {
  common: "Common",
  dwarvish: "Dwarvish",
  elvish: "Elvish",
  giant: "Giant",
  gnomish: "Gnomish",
  goblin: "Goblin",
  halfling: "Halfling",
  orc: "Orc",
  abyssal: "Abyssal",
  celestial: "Celestial",
  draconic: "Draconic",
  "deep-speech": "Deep Speech",
  infernal: "Infernal",
  primordial: "Primordial",
  sylvan: "Sylvan",
  undercommon: "Undercommon",
  "common-sign-language": "Common Sign Language",
  druidic: "Druidic",
  "thieves-cant": "Thieves' Cant",
  // VF2.4: languages the 2014 species records grant (Primordial dialects and the named `other` languages); display only
  aarakocra: "Aarakocra",
  aquan: "Aquan",
  auran: "Auran",
  aven: "Aven",
  bullywug: "Bullywug",
  gith: "Gith",
  grung: "Grung",
  ignan: "Ignan",
  keldon: "Keldon",
  khenra: "Khenra",
  kraul: "Kraul",
  "kor-silent-speech": "Kor silent speech",
  leonin: "Leonin",
  loxodon: "Loxodon",
  merfolk: "Merfolk",
  minotaur: "Minotaur",
  naga: "Naga",
  quori: "Quori",
  siren: "Siren",
  terran: "Terran",
  troglodyte: "Troglodyte",
  vampire: "Vampire",
  vedalken: "Vedalken",
};

const PROFICIENCY_OVERRIDES: Record<string, string> = {
  "martial-weapons-finesse-or-light": "Martial weapons with Finesse or Light",
  "martial-weapons-light": "Martial weapons with Light",
};

/** "light-armor" -> "Light armor" (first letter upper case, dashes to spaces). */
export function slugTitle(slug: string): string {
  const s = slug.replace(/-/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const skillName = (id: string): string => SKILL_NAMES[id] ?? id;
export const languageName = (id: string): string => LANGUAGE_NAMES[id] ?? id;
export const proficiencyLabel = (id: string): string => PROFICIENCY_OVERRIDES[id] ?? slugTitle(id);
/** An expertise entry is a skill id or a tool id (the Rogue's thieves-tools). */
export const expertiseLabel = (id: string): string => SKILL_NAMES[id] ?? proficiencyLabel(id);
