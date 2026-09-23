export type Ability = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA";

export interface ChoiceOption {
  id: string;
  label: string;
  description?: string;
  disabled?: boolean;
  disabledReason?: string;
}

export type ChoiceSourceKind =
  | "class"
  | "subclass"
  | "background"
  | "species"
  | "feature"
  | "equipment";

export interface ChoiceSource {
  kind: ChoiceSourceKind;
  id: string;
  label: string;
  level?: number;
}

export type ChoiceStatus = "pending" | "resolved" | "invalid";

export interface Choice {
  id: string;
  source: ChoiceSource;
  label: string;
  description: string;
  count: number;
  options: ChoiceOption[];
  selected: string[];
  status: ChoiceStatus;
}

export interface Problem {
  id: string;
  message: string;
}

export interface WarningItem {
  id: string;
  message: string;
}

export interface Pruned {
  choiceId: string;
  reason: string;
}

export interface CharacterDetails {
  // Character Details
  alignment?: string;
  faith?: string;
  lifestyle?: string;
  // Physical Characteristics
  age?: string;
  height?: string;
  weight?: string;
  eyes?: string;
  skin?: string;
  hair?: string;
  // Personality
  personalityTraits?: string;
  ideals?: string;
  bonds?: string;
  flaws?: string;
  // Notes
  backstory?: string;
  organizations?: string;
  allies?: string;
  enemies?: string;
  notes?: string;
}

export interface SheetEquipmentEntry {
  itemId: string;
  name: string;
  qty: number;
}

export interface SheetAddedEquipmentEntry extends SheetEquipmentEntry {
  equipped: boolean;
}

export interface SheetSpellSummary {
  id: string;
  name: string;
  level: number;
}

export interface SheetClassSpells {
  classId: string;
  cantrips: SheetSpellSummary[];
  known: SheetSpellSummary[];
  spellSaveDC: number | null;
  spellAttackBonus: number | null;
}

export interface SheetClassSubclass {
  id: string;
  name: string;
}

export interface SheetClass {
  id: string;
  name: string;
  level: number;
  subclass: SheetClassSubclass | null;
}

export interface SheetBackground {
  id: string;
  name: string;
}

export interface SheetSubspecies {
  id: string;
  name: string;
}

export interface SheetSpecies {
  id: string;
  name: string;
  subspecies: SheetSubspecies | null;
}

export interface SheetProficiencies {
  skills: string[];
  savingThrows: string[];
  languages: string[];
}

export interface SheetEquipment {
  granted: SheetEquipmentEntry[];
  chosen: SheetEquipmentEntry[];
  added: SheetAddedEquipmentEntry[];
}

export interface Sheet {
  name: string;
  level: number;
  classes: SheetClass[];
  background: SheetBackground | null;
  species: SheetSpecies | null;
  abilities: Record<Ability, number>;
  proficiencies: SheetProficiencies;
  equipment: SheetEquipment;
  spells: SheetClassSpells[];
  details: CharacterDetails | null;
}

export interface Derived {
  abilityModifiers: Record<Ability, number>;
  proficiencyBonus: number;
  hitPointMax: number;
  hitDice: string | null;
  armorClass: number;
  speed: number | null;
  savingThrows: Record<Ability, number>;
  skills: Record<string, number>;
  passivePerception: number;
  spellSlots: Record<string, number>;
  warlockSpellSlots: Record<string, number>;
}

export interface Resolution {
  sheet: Sheet;
  choices: Choice[];
  derived: Derived;
  problems: Problem[];
  warnings: WarningItem[];
  pruned: Pruned[];
}

export interface ClassSelection {
  classId: string;
  level: number;
  subclassId?: string;
  hpRolls?: Record<string, number>;
  choices: Record<string, string[]>;
}

export interface Preferences {
  advancementType: "milestone" | "xp";
  hitPointType: "fixed" | "manual";
  usePrerequisites: { feats: boolean; multiclass: boolean };
}

export interface Draft {
  name: string;
  sources: string[];
  preferences: Preferences;
  classes: ClassSelection[];
  background: { id?: string; choices: Record<string, string[]> };
  species: { id?: string; subspeciesId?: string; choices: Record<string, string[]> };
  abilities: {
    method: "standard" | "roll" | "pointbuy" | "manual";
    base: Record<Ability, number>;
  };
  equipment: {
    startingChoice?: string;
    choices: Record<string, string[]>;
    added: { itemId: string; qty: number; equipped: boolean }[];
    skipped: boolean;
  };
  details: CharacterDetails;
}
