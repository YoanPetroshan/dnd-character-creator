export type Ability = "STR" | "DEX" | "CON" | "INT" | "WIS" | "CHA";

export interface ChoiceOption {
  id: string;
  label: string;
  description?: string;
  disabled?: boolean;
  disabledReason?: string;
  /** Optional grouping key; consecutive options sharing it render under one heading. */
  group?: string;
  /** Option is hidden by the current ruleset/source filters (treated like an unavailable option). */
  hiddenByFilters?: boolean;
  /** 2024 class starting-equipment package: {item id: count} for members with a count other than 1. */
  quantities?: Record<string, number>;
}

export type ChoiceSourceKind =
  | "class"
  | "subclass"
  | "background"
  | "species"
  | "feat"
  | "feature"
  | "equipment";

export interface ChoiceSource {
  kind: ChoiceSourceKind;
  id: string;
  label: string;
  level?: number;
}

/** "unavailable" (F3a): a new 2024 card with no enabled option; it never blocks export. */
export type ChoiceStatus = "pending" | "resolved" | "invalid" | "unavailable";

export interface Choice {
  id: string;
  source: ChoiceSource;
  label: string;
  description: string;
  count: number;
  options: ChoiceOption[];
  selected: string[];
  status: ChoiceStatus;
  /** Options granted automatically (e.g. Elemental Attunement); not pickable. */
  granted?: { id: string; label: string }[];
  /** Set with status "unavailable": why nothing can be chosen. */
  unavailableReason?: string;
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
  /** Wizard only (C4): the spellbook; the prepared spells in `known` are drawn from it. */
  spellbook?: SheetSpellSummary[];
  /** Subclass spells (domain/oath/circle): always prepared, outside the limits. */
  alwaysPrepared: SheetSpellSummary[];
  /** Wizard 18+ (2024): the Spell Mastery picks (always prepared; cast at the lowest level at will). */
  spellMastery?: SheetSpellSummary[];
  /** Wizard 20 (2024): the two Signature Spells (always prepared; one free cast per rest). */
  signatureSpells?: SheetSpellSummary[];
  /** Warlock (2024) with Pact of the Tome: the Book of Shadows cantrips, then the two rituals (prepared, function as Warlock spells). */
  pactOfTheTome?: SheetSpellSummary[];
  /** Warlock only: the Mystic Arcanum picks (level 6-9 spells, one per gained level). */
  mysticArcanum?: { level: number; id: string; name: string }[];
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
  variant?: { id: string; name: string } | null;
  size?: string | null;
}

export interface SheetProficiencies {
  skills: string[];
  savingThrows: string[];
  languages: string[];
  armor?: string[];
  weapons?: string[];
  tools?: string[];
}

export interface SheetDamageModifiers {
  resistances: string[];
  immunities: string[];
  vulnerabilities: string[];
}

export interface SheetInnateSpell {
  spellId: string | null;
  name: string;
  level: number;
  uses: string;
  ability: Ability | null;
  variant: string | null;
  /** Origin label, e.g. "Eldritch Invocation". */
  source?: string;
  note?: string;
}

export type SheetFeatureSourceKind = "class" | "subclass" | "species" | "background" | "feat";

export interface SheetFeature {
  source: { kind: SheetFeatureSourceKind; id: string; label: string };
  name: string;
  /** Class level that grants it; null for species, background and feats. */
  level: number | null;
  /** Labels of what the player picked for this feature (fighting style, metamagic, ...). */
  choice?: string[];
}

export interface SheetFeat {
  id: string;
  name: string;
  origin: "background" | "species" | "asi" | "fighting-style" | "invocation";
  level: number | null;
  choice?: string[];
}

export interface SlotItem {
  itemId: string;
  name: string;
  kind?: "weapon" | "shield";
  twoHanded?: boolean;
}

export interface SheetEquipment {
  /** G2: what the worn/wielded selectors can offer, from the resolved inventory. */
  slots?: { armor: SlotItem[]; shield: SlotItem[]; hands: SlotItem[]; current: { armor: string | null; shield: boolean } };
  /** G2: present only when the draft sets worn / wielded. */
  worn?: { armor: string | null; shield: boolean; manual: boolean };
  wielded?: { main: string | null; off: string | null; manual: boolean };
  granted: SheetEquipmentEntry[];
  chosen: SheetEquipmentEntry[];
  added: SheetAddedEquipmentEntry[];
  narrativeItems?: string[];
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
  /** Sense ranges in feet, e.g. {darkvision: 60}. */
  senses?: Record<string, number>;
  /** Skill ids (and the Rogue's "thieves-tools") with doubled proficiency. */
  expertiseSkills?: string[];
  damageModifiers?: SheetDamageModifiers;
  conditionImmunities?: string[];
  innateSpells?: SheetInnateSpell[];
  startingGold?: number;
  /** Feat catalog ids granted by the background or taken at an ASI level. */
  grantedFeats?: string[];
  featOptions?: unknown[];
  /** Class/subclass/species/background/feat features with the player's picks. */
  features?: SheetFeature[];
  feats?: SheetFeat[];
  /** C2: chosen Weapon Masteries (2024). */
  weaponMasteries?: WeaponMastery[];
}

export interface Attack {
  itemId: string;
  name: string;
  ability: "STR" | "DEX";
  proficient: boolean;
  attackBonus: number;
  /** null for a weapon without damage (net). */
  damage: string | null;
  damageType: string | null;
  versatileDamage: string | null;
  /** One-handed melee with Dueling only: damage including the +2 (S5). */
  duelingDamage: string | null;
  /** G2: only when the draft sets equipment.wielded. */
  wielded?: boolean;
  offhandDamage: string | null;
  range: string | null;
  notes: string[];
  /** C2: the mastery name (e.g. "Sap") when this weapon is one of the chosen Weapon Masteries. */
  mastery?: string | null;
}

export interface WeaponMastery {
  itemId: string;
  name: string;
  mastery: string;
}

export interface CarryingCapacity {
  capacity: number;
  pushDragLift: number;
  carried: number;
  overCapacity: boolean;
}

/** A class feature with a number to track (R1): rages, sneak attack dice, ... */
export interface ClassResource {
  id: string;
  classId: string;
  source: { kind: "class" | "subclass"; id: string | null; label: string };
  name: string;
  uses: number | null;
  unlimited?: boolean;
  recharge: "long" | "short" | "short-or-long" | null;
  die?: string;
  dice?: string;
  pool?: number;
  bonus?: number;
  dc?: number;
  details?: Record<string, unknown> & { damageBonus?: number; heal?: string; maxCr?: string; note?: string };
}

export interface Derived {
  abilityModifiers: Record<Ability, number>;
  proficiencyBonus: number;
  hitPointMax: number;
  hitDice: string | null;
  armorClass: number;
  speed: number | null;
  /** Every movement mode, e.g. {walk: 30, swim: 30}; `speed` is the walk entry. */
  speeds: Record<string, number>;
  savingThrows: Record<Ability, number>;
  skills: Record<string, number>;
  initiative: number;
  passivePerception: number;
  passiveInsight: number;
  passiveInvestigation: number;
  spellSlots: Record<string, number>;
  warlockSpellSlots: Record<string, number>;
  slotGrantingClasses?: string[];
  /** Equipped weapons, one entry per distinct weapon. Optional: older stored resolutions lack it. */
  attacks?: Attack[];
  /** Class resources in class order (R1). Optional: older stored resolutions lack it. */
  classResources?: ClassResource[];
  /** Attacks per Attack action (R2): 1 + the largest Extra Attack, never stacked. Optional: older stored resolutions lack it. */
  attacksPerAction?: number;
  carryingCapacity?: CarryingCapacity;
  /** True when any equipped armor imposes disadvantage on Stealth. */
  stealthDisadvantage?: boolean;
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
  hitPointType: "fixed" | "manual";
  usePrerequisites: { feats: boolean; multiclass: boolean };
}

export type Ruleset = "2014" | "2024" | "mixed";

export interface Draft {
  draftVersion?: number;
  name: string;
  sources: string[];
  /** Which ability-score rules apply (species vs background); "mixed" = house rules. */
  ruleset: Ruleset;
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
    /** G2, optional: absent = best armor/shield auto-detected. armor null = none worn. */
    worn?: { armor?: string | null; shield?: boolean | null };
    /** G2, optional: absent = hands not tracked. */
    wielded?: { main?: string | null; off?: string | null };
    skipped: boolean;
  };
  details: CharacterDetails;
}
