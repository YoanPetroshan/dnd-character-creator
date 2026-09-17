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

export interface Resolution {
  sheet: Record<string, unknown>;
  choices: Choice[];
  derived: Record<string, unknown>;
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
  details: {
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
  };
}
