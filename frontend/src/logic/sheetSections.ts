import type {
  Ability,
  Attack,
  CarryingCapacity,
  CharacterDetails,
  ClassResource,
  FeatResource,
  Resolution,
  SheetEquipmentEntry,
  SheetFeat,
  SheetFeature,
  SheetInnateSpell,
  SheetSpellSummary,
  SpeciesResource,
  WeaponMastery,
} from "../types";
import { ABILITIES } from "./abilities";
import { expertiseLabel, languageName, proficiencyLabel, skillName, slugTitle } from "./labels";
import { spellcastingAbility } from "./spellAbility";

// The in-app character sheet (/sheet) is a list of sections computed from a Resolution by the pure
// function below. Components in components/sheet/ only render a section's data; they fetch and
// derive nothing. `logic/sheetCoverage.json` maps every section key to the resolution paths it
// shows (the server test test_sheet_coverage.py reads the same file).

export const SHEET_SECTION_KEYS = [
  "identity",
  "abilities",
  "proficiencyBonus",
  "armorClass",
  "hitPoints",
  "initiative",
  "speeds",
  "senses",
  "passives",
  "savingThrows",
  "skills",
  "proficiencies",
  "languages",
  "attacks",
  "resources",
  "features",
  "feats",
  "spells",
  "innateSpells",
  "equipment",
  "carryingCapacity",
  "defenses",
  "details",
] as const;

export type SheetSectionKey = (typeof SHEET_SECTION_KEYS)[number];

export interface AbilityRow {
  ability: Ability;
  /** The score before species / background / feat bonuses; null when the draft's base is not known. */
  base: number | null;
  /** total - base; null together with base. */
  bonus: number | null;
  total: number;
  modifier: number;
}

export interface SkillRow {
  id: string;
  name: string;
  bonus: number;
  proficient: boolean;
  expertise: boolean;
}

export interface SpellcasterData {
  classId: string;
  className: string;
  ability: Ability | null;
  saveDC: number | null;
  attackBonus: number | null;
  cantrips: SheetSpellSummary[];
  known: SheetSpellSummary[];
  spellbook: SheetSpellSummary[];
  alwaysPrepared: SheetSpellSummary[];
  spellMastery: SheetSpellSummary[];
  signatureSpells: SheetSpellSummary[];
  pactOfTheTome: SheetSpellSummary[];
  mysticArcanum: { level: number; id: string; name: string }[];
}

export interface SlotRow {
  level: number;
  count: number;
}

export interface EquipmentGroup {
  kind: "granted" | "chosen" | "added";
  entries: (SheetEquipmentEntry & { equipped?: boolean })[];
}

export interface SheetSectionData {
  identity: {
    name: string;
    level: number;
    classes: { id: string; name: string; level: number; subclass: string | null }[];
    species: { name: string; subspecies: string | null; variant: string | null; size: string | null } | null;
    background: string | null;
  };
  abilities: AbilityRow[];
  proficiencyBonus: number;
  armorClass: { value: number; stealthDisadvantage: boolean };
  hitPoints: { max: number; hitDice: string | null };
  initiative: number;
  speeds: { mode: string; feet: number }[];
  senses: { kind: string; feet: number }[];
  passives: { perception: number; insight: number; investigation: number };
  savingThrows: { ability: Ability; bonus: number; proficient: boolean }[];
  skills: { rows: SkillRow[]; otherExpertise: string[] };
  proficiencies: { armor: string[]; weapons: string[]; tools: string[] };
  languages: string[];
  attacks: { perAction: number; attacks: Attack[]; masteries: WeaponMastery[] };
  resources: { class: ClassResource[]; feat: FeatResource[]; species: SpeciesResource[] };
  features: { label: string; items: SheetFeature[] }[];
  feats: SheetFeat[];
  spells: { casters: SpellcasterData[]; slots: SlotRow[]; pactSlots: SlotRow[]; slotsShared: boolean };
  innateSpells: SheetInnateSpell[];
  equipment: {
    groups: EquipmentGroup[];
    /** Names; armor null = none worn. Present only when the draft sets worn / wielded. */
    worn: { armor: string | null; shield: boolean } | null;
    wielded: { main: string | null; off: string | null } | null;
    startingGold: number;
    narrativeItems: string[];
  };
  carryingCapacity: CarryingCapacity;
  defenses: { resistances: string[]; immunities: string[]; vulnerabilities: string[]; conditionImmunities: string[] };
  details: { section: DetailSectionKey; fields: { key: keyof CharacterDetails; value: string }[] }[];
}

export type SheetSection = { [K in SheetSectionKey]: { key: K; data: SheetSectionData[K] } }[SheetSectionKey];

export const DETAIL_SECTIONS = {
  character: ["alignment", "faith", "lifestyle"],
  physical: ["age", "height", "weight", "eyes", "skin", "hair"],
  personality: ["personalityTraits", "ideals", "bonds", "flaws"],
  notes: ["backstory", "organizations", "allies", "enemies", "notes"],
} as const satisfies Record<string, readonly (keyof CharacterDetails)[]>;
export type DetailSectionKey = keyof typeof DETAIL_SECTIONS;

function slotRows(slots: Record<string, number> | undefined): SlotRow[] {
  return Object.entries(slots ?? {})
    .map(([level, count]) => ({ level: Number(level), count }))
    .filter((r) => r.count > 0)
    .sort((a, b) => a.level - b.level);
}

/** The six ability rows. `base` is the draft's base scores (optional: a resolution alone does not carry them). */
export function abilityRows(
  totals: Record<Ability, number>,
  modifiers: Record<Ability, number>,
  base?: Record<Ability, number>,
): AbilityRow[] {
  return ABILITIES.map((ability) => ({
    ability,
    base: base ? base[ability] : null,
    bonus: base ? totals[ability] - base[ability] : null,
    total: totals[ability],
    modifier: modifiers[ability],
  }));
}

/** The sections of the sheet with data to show, in page order. A section with nothing to show is left out. */
export function sheetSections(resolution: Resolution, base?: Record<Ability, number>): SheetSection[] {
  const { sheet, derived } = resolution;
  const out: SheetSection[] = [];
  const push = <K extends SheetSectionKey>(key: K, data: SheetSectionData[K]) => out.push({ key, data } as SheetSection);

  const classNames = new Map(sheet.classes.map((c) => [c.id, c.name]));

  push("identity", {
    name: sheet.name,
    level: sheet.level,
    classes: sheet.classes.map((c) => ({ id: c.id, name: c.name, level: c.level, subclass: c.subclass?.name ?? null })),
    species: sheet.species
      ? {
          name: sheet.species.name,
          subspecies: sheet.species.subspecies?.name ?? null,
          variant: sheet.species.variant?.name ?? null,
          size: sheet.species.size ?? null,
        }
      : null,
    background: sheet.background?.name ?? null,
  });

  push("abilities", abilityRows(sheet.abilities, derived.abilityModifiers, base));
  if (derived.proficiencyBonus !== undefined) push("proficiencyBonus", derived.proficiencyBonus);
  if (derived.armorClass !== undefined)
    push("armorClass", { value: derived.armorClass, stealthDisadvantage: derived.stealthDisadvantage === true });
  if (derived.hitPointMax !== undefined) push("hitPoints", { max: derived.hitPointMax, hitDice: derived.hitDice ?? null });
  if (derived.initiative !== undefined) push("initiative", derived.initiative);

  const speeds = Object.entries(derived.speeds ?? {}).map(([mode, feet]) => ({ mode, feet }));
  if (speeds.length === 0 && derived.speed != null) speeds.push({ mode: "walk", feet: derived.speed });
  if (speeds.length > 0) push("speeds", speeds);

  const senses = Object.entries(sheet.senses ?? {}).map(([kind, feet]) => ({ kind, feet }));
  if (senses.length > 0) push("senses", senses);

  push("passives", {
    perception: derived.passivePerception,
    insight: derived.passiveInsight,
    investigation: derived.passiveInvestigation,
  });

  const saveProf = new Set<string>(sheet.proficiencies.savingThrows);
  push(
    "savingThrows",
    ABILITIES.map((ability) => ({ ability, bonus: derived.savingThrows[ability], proficient: saveProf.has(ability) })),
  );

  const skillProf = new Set(sheet.proficiencies.skills);
  const expertise = new Set(sheet.expertiseSkills ?? []);
  const rows = Object.entries(derived.skills)
    .map(([id, bonus]) => ({ id, name: skillName(id), bonus, proficient: skillProf.has(id), expertise: expertise.has(id) }))
    .sort((a, b) => a.name.localeCompare(b.name, "en"));
  const otherExpertise = [...expertise].filter((id) => !(id in derived.skills)).map(expertiseLabel);
  push("skills", { rows, otherExpertise });

  const prof = sheet.proficiencies;
  const armor = (prof.armor ?? []).map(proficiencyLabel);
  const weapons = (prof.weapons ?? []).map(proficiencyLabel);
  const tools = (prof.tools ?? []).map(proficiencyLabel);
  if (armor.length + weapons.length + tools.length > 0) push("proficiencies", { armor, weapons, tools });
  if (prof.languages.length > 0) push("languages", prof.languages.map(languageName));

  const attacks = derived.attacks ?? [];
  const perAction = derived.attacksPerAction ?? 1;
  const masteries = sheet.weaponMasteries ?? [];
  if (attacks.length > 0 || perAction > 1 || masteries.length > 0) push("attacks", { perAction, attacks, masteries });

  const resources = {
    class: derived.classResources ?? [],
    feat: derived.featResources ?? [],
    species: derived.speciesResources ?? [],
  };
  if (resources.class.length + resources.feat.length + resources.species.length > 0) push("resources", resources);

  // Feats have their own section; features are grouped by their source label, in the order given.
  const groups: { label: string; items: SheetFeature[] }[] = [];
  for (const f of sheet.features ?? []) {
    if (f.source.kind === "feat") continue;
    const last = groups[groups.length - 1];
    if (last && last.label === f.source.label) last.items.push(f);
    else groups.push({ label: f.source.label, items: [f] });
  }
  if (groups.length > 0) push("features", groups);
  if ((sheet.feats ?? []).length > 0) push("feats", sheet.feats!);

  const slots = slotRows(derived.spellSlots);
  const pactSlots = slotRows(derived.warlockSpellSlots);
  if (sheet.spells.length > 0 || slots.length > 0 || pactSlots.length > 0) {
    push("spells", {
      casters: sheet.spells.map((s) => ({
        classId: s.classId,
        className: classNames.get(s.classId) ?? s.classId,
        ability: spellcastingAbility(s.classId, s.spellSaveDC, s.spellAttackBonus, derived.abilityModifiers, derived.proficiencyBonus),
        saveDC: s.spellSaveDC,
        attackBonus: s.spellAttackBonus,
        cantrips: s.cantrips,
        known: s.known,
        spellbook: s.spellbook ?? [],
        alwaysPrepared: s.alwaysPrepared,
        spellMastery: s.spellMastery ?? [],
        signatureSpells: s.signatureSpells ?? [],
        pactOfTheTome: s.pactOfTheTome ?? [],
        mysticArcanum: s.mysticArcanum ?? [],
      })),
      slots,
      pactSlots,
      // the shared pool is common exactly when more than one class grants slots (server-computed)
      slotsShared: (derived.slotGrantingClasses ?? []).length > 1,
    });
  }
  if ((sheet.innateSpells ?? []).length > 0) push("innateSpells", sheet.innateSpells!);

  const eq = sheet.equipment;
  const equipmentGroups: EquipmentGroup[] = (
    [
      { kind: "granted", entries: eq.granted },
      { kind: "chosen", entries: eq.chosen },
      { kind: "added", entries: eq.added },
    ] as EquipmentGroup[]
  ).filter((g) => g.entries.length > 0);
  const names = new Map<string, string>();
  for (const list of [eq.slots?.armor, eq.slots?.shield, eq.slots?.hands]) for (const o of list ?? []) names.set(o.itemId, o.name);
  const nameOf = (id: string | null | undefined) => (id ? (names.get(id) ?? id) : null);
  const worn = eq.worn ? { armor: nameOf(eq.worn.armor), shield: eq.worn.shield } : null;
  const wielded = eq.wielded ? { main: nameOf(eq.wielded.main), off: nameOf(eq.wielded.off) } : null;
  const startingGold = sheet.startingGold ?? 0;
  const narrativeItems = eq.narrativeItems ?? [];
  if (equipmentGroups.length > 0 || worn || wielded || startingGold > 0 || narrativeItems.length > 0)
    push("equipment", { groups: equipmentGroups, worn, wielded, startingGold, narrativeItems });

  if (derived.carryingCapacity) push("carryingCapacity", derived.carryingCapacity);

  const dm = sheet.damageModifiers;
  const defenses = {
    resistances: (dm?.resistances ?? []).map(slugTitle),
    immunities: (dm?.immunities ?? []).map(slugTitle),
    vulnerabilities: (dm?.vulnerabilities ?? []).map(slugTitle),
    conditionImmunities: (sheet.conditionImmunities ?? []).map(slugTitle),
  };
  if (Object.values(defenses).some((l) => l.length > 0)) push("defenses", defenses);

  const details = sheet.details;
  if (details) {
    const detailSections = (Object.keys(DETAIL_SECTIONS) as DetailSectionKey[])
      .map((section) => ({
        section,
        fields: (DETAIL_SECTIONS[section] as readonly (keyof CharacterDetails)[])
          .filter((k) => typeof details[k] === "string" && details[k] !== "")
          .map((key) => ({ key, value: details[key] as string })),
      }))
      .filter((s) => s.fields.length > 0);
    if (detailSections.length > 0) push("details", detailSections);
  }

  return out;
}
