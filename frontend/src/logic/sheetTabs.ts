import type { SheetFeature, Resolution, SheetFeat } from "../types";
import type { SpellcasterData } from "./sheetSections";

/** The tabs of the sheet page, in order; the id is what `?tab=` carries (a deep link survives a reload). */
export const TAB_IDS = ["actions", "spells", "inventory", "features", "background", "notes"] as const;
export type TabId = (typeof TAB_IDS)[number];
export const DEFAULT_TAB: TabId = "actions";

/** `?tab=` value -> tab id; anything unknown is the default tab. */
export function parseTab(value: string | null | undefined): TabId {
  return (TAB_IDS as readonly string[]).includes(value ?? "") ? (value as TabId) : DEFAULT_TAB;
}

/** The tab a key press moves to (WAI-ARIA tabs: arrows wrap, Home / End jump); null = not a tab key. */
export function tabAfterKey(current: number, count: number, key: string, vertical = false): number | null {
  const prev = vertical ? "ArrowUp" : "ArrowLeft";
  const next = vertical ? "ArrowDown" : "ArrowRight";
  if (key === next) return (current + 1) % count;
  if (key === prev) return (current - 1 + count) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return null;
}

/** The standard actions of the 2024 rules: game terms, shown as they are in both languages (like spell and item names). */
export const STANDARD_ACTIONS = ["Attack", "Dash", "Disengage", "Dodge", "Help", "Hide", "Influence", "Magic", "Ready", "Search", "Study", "Utilize"] as const;

export type SpellMark = "known" | "spellbook" | "alwaysPrepared" | "mysticArcanum" | "spellMastery" | "signatureSpells" | "pactOfTheTome";
export interface SpellRowData {
  id: string;
  name: string;
  level: number;
  /** Where the spell comes from on this caster's list; one row per spell however many lists name it. */
  marks: SpellMark[];
}
export interface SpellLevelGroup {
  level: number;
  spells: SpellRowData[];
}

/** One caster's spells merged into one row per spell and grouped by level, cantrips (level 0) first. */
export function mergeSpellRows(caster: SpellcasterData): SpellLevelGroup[] {
  const rows = new Map<string, SpellRowData>();
  const add = (id: string, name: string, level: number, mark: SpellMark | null) => {
    const row = rows.get(id) ?? { id, name, level, marks: [] };
    if (mark && !row.marks.includes(mark)) row.marks.push(mark);
    rows.set(id, row);
  };
  for (const s of caster.cantrips) add(s.id, s.name, s.level, null);
  const lists: [SpellMark, { id: string; name: string; level: number }[]][] = [
    ["known", caster.known],
    ["spellbook", caster.spellbook],
    ["alwaysPrepared", caster.alwaysPrepared],
    ["mysticArcanum", caster.mysticArcanum],
    ["spellMastery", caster.spellMastery],
    ["signatureSpells", caster.signatureSpells],
    ["pactOfTheTome", caster.pactOfTheTome],
  ];
  for (const [mark, list] of lists) for (const s of list) add(s.id, s.name, s.level, mark);
  const byLevel = new Map<number, SpellRowData[]>();
  for (const row of rows.values()) byLevel.set(row.level, [...(byLevel.get(row.level) ?? []), row]);
  return [...byLevel.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([level, spells]) => ({ level, spells: spells.sort((a, b) => a.name.localeCompare(b.name, "en")) }));
}

export const FEATURE_FILTERS = ["all", "class", "species", "feats"] as const;
export type FeatureFilter = (typeof FEATURE_FILTERS)[number];

export interface FeatureGroup {
  key: string;
  kind: "class" | "species" | "background" | "feat";
  label: string;
  features: SheetFeature[];
  feats: SheetFeat[];
}

/** The features and feats of the character grouped by source (class, species, background, feats), narrowed by a filter. */
export function featureGroups(resolution: Resolution, filter: FeatureFilter): FeatureGroup[] {
  const groups: FeatureGroup[] = [];
  for (const f of resolution.sheet.features ?? []) {
    if (f.source.kind === "feat") continue; // feats are listed from sheet.feats
    const kind = f.source.kind as FeatureGroup["kind"];
    const key = `${kind}:${f.source.id}:${f.source.label}`;
    const last = groups[groups.length - 1];
    if (last && last.key === key) last.features.push(f);
    else groups.push({ key, kind, label: f.source.label, features: [f], feats: [] });
  }
  const feats = resolution.sheet.feats ?? [];
  if (feats.length > 0) groups.push({ key: "feats", kind: "feat", label: "", features: [], feats });
  return groups.filter((g) => filter === "all" || (filter === "class" && g.kind === "class") || (filter === "species" && g.kind === "species") || (filter === "feats" && g.kind === "feat"));
}
