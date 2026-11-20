// Pure draft logic moved out of DraftContext (SK1): no React, importable from tests.
import type { Ability, ChoiceSourceKind, Draft, Ruleset } from "../types";
import { MsgError, msg } from "./messages";
import { migrateDraft } from "./migrations";
import { DEFAULT_SOURCES } from "./sources";

/** Bump when the draft shape changes incompatibly. Stored/imported drafts
 *  with a NEWER version than this build are rejected rather than guessed at.
 *  v2: `ruleset` added. Older drafts need no migration step: mergeDraft
 *  fills the missing key with the default ("mixed", the behaviour they had)
 *  and stamps the current version. */
export const DRAFT_VERSION = 2;

export const emptyDraft: Draft = {
  draftVersion: DRAFT_VERSION,
  name: "",
  // A NEW draft starts with the core books on (owner, 2026-11-20): the Player's Handbook and the Dungeon Master's Guide of
  // both rulesets, plus the SRD; every other book is off until the player turns it on. An EMPTY list still means
  // "everything available" (server/engine/resolve.py's permissive default), and it is what older saved drafts and
  // "Select all" hold. "Clear all" stores ["srd"], since an empty list means "everything". A record the filters hide
  // stays pickable when the draft already holds it (the catalog keeps it, flagged hidden).
  sources: [...DEFAULT_SOURCES],
  ruleset: "mixed",
  preferences: {
    hitPointType: "fixed",
    usePrerequisites: { feats: true, multiclass: true },
  },
  classes: [],
  background: { choices: {} },
  species: { choices: {} },
  abilities: {
    method: "standard",
    base: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
  },
  equipment: { choices: {}, added: [], skipped: false },
  details: {},
};

export type Action =
  | { type: "SET_NAME"; name: string }
  | { type: "SET_RULESET"; ruleset: Ruleset }
  | { type: "SET_SOURCES"; sources: string[] }
  | { type: "SET_DRAFT"; draft: Draft }
  | { type: "RESET" }
  | { type: "SET_CLASS"; classId: string }
  | { type: "ADD_CLASS"; classId: string }
  | { type: "REMOVE_CLASS"; classId: string }
  | { type: "SET_BACKGROUND"; backgroundId: string }
  | { type: "SET_SPECIES"; speciesId: string }
  | { type: "SET_SUBSPECIES"; subspeciesId: string | undefined }
  | { type: "SET_CLASS_LEVEL"; classId: string; level: number }
  | { type: "SET_SUBCLASS"; classId: string; subclassId: string | undefined }
  | { type: "SET_HP_ROLL"; classId: string; level: number; value: number }
  | { type: "SET_ABILITY_METHOD"; method: Draft["abilities"]["method"] }
  | { type: "SET_HIT_POINT_TYPE"; hitPointType: Draft["preferences"]["hitPointType"] }
  | { type: "SET_USE_PREREQUISITE"; field: keyof Draft["preferences"]["usePrerequisites"]; value: boolean }
  | { type: "SET_ABILITY_SCORE"; ability: Ability; value: number }
  | { type: "SET_ABILITY_SCORES"; base: Record<Ability, number> }
  | { type: "SET_DETAIL"; field: keyof Draft["details"]; value: string }
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] }
  | { type: "TOGGLE_CHOICE_OPTION"; source: ChoiceSourceKind; choiceId: string; optionId: string; count: number }
  | { type: "CLEAR_STALE_SELECTIONS"; keepIds: string[]; clearSubclassFor?: string[] }
  | { type: "ADD_ITEM"; itemId: string }
  | { type: "REMOVE_ITEM"; itemId: string }
  | { type: "TOGGLE_EQUIPPED"; itemId: string }
  | { type: "SET_WORN"; worn: Draft["equipment"]["worn"] }
  | { type: "SET_WIELDED"; wielded: Draft["equipment"]["wielded"] };

export const MAX_TOTAL_LEVEL = 20;

export function totalLevel(d: Draft): number {
  return d.classes.reduce((sum, c) => sum + (typeof c.level === "number" ? c.level : 0), 0);
}

/** The selection currently stored in the draft for a choice (not the last
 *  server resolution, which lags by the debounce + network round trip). */
export function storedSelection(state: Draft, source: ChoiceSourceKind, choiceId: string): string[] {
  let bucket: Record<string, string[]> | undefined;
  if (source === "class") {
    const targetClassId = choiceId.split(":")[1];
    bucket = state.classes.find((c) => c.classId === targetClassId)?.choices;
  } else if (source === "background") bucket = state.background.choices;
  else if (source === "species") bucket = state.species.choices;
  else if (source === "equipment") bucket = state.equipment.choices;
  const v = bucket?.[choiceId];
  return Array.isArray(v) ? v : [];
}

export function reducer(state: Draft, action: Action): Draft {
  switch (action.type) {
    case "CLEAR_STALE_SELECTIONS": {
      // Drop stored selections whose choice no longer exists in the resolution
      // (what the server reports as `pruned`).
      const keep = new Set(action.keepIds);
      const prune = (m: Record<string, string[]>) =>
        Object.fromEntries(Object.entries(m ?? {}).filter(([id]) => keep.has(id)));
      return {
        ...state,
        classes: state.classes.map((c) => ({
          ...c,
          choices: prune(c.choices),
          ...(action.clearSubclassFor?.includes(c.classId) ? { subclassId: undefined } : {}),
        })),
        background: { ...state.background, choices: prune(state.background.choices) },
        species: { ...state.species, choices: prune(state.species.choices) },
        equipment: { ...state.equipment, choices: prune(state.equipment.choices) },
      };
    }
    case "TOGGLE_CHOICE_OPTION": {
      const current = storedSelection(state, action.source, action.choiceId);
      let next: string[];
      if (current.includes(action.optionId)) next = current.filter((id) => id !== action.optionId);
      else if (current.length >= action.count) next = [...current.slice(current.length - action.count + 1), action.optionId];
      else next = [...current, action.optionId];
      return reducer(state, { type: "SET_CHOICE_SELECTION", source: action.source, choiceId: action.choiceId, selected: next });
    }
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_RULESET":
      return { ...state, ruleset: action.ruleset };
    case "SET_SOURCES":
      return { ...state, sources: action.sources };
    case "SET_DRAFT":
      return action.draft;
    case "RESET":
      return emptyDraft;
    case "SET_CLASS":
      // Sets/replaces the PRIMARY class (classes[0]) — clears the whole
      // array, since a new primary class invalidates every existing
      // class's choices (equipment/background choices are anchored to
      // the primary class too). Adding a SECOND-OR-LATER class is
      // ADD_CLASS below, which does NOT clear anything.
      return {
        ...state,
        classes: [{ classId: action.classId, level: 1, choices: {} }],
        equipment: { ...state.equipment, choices: {} },
      };
    case "ADD_CLASS": {
      if (state.classes.some((c) => c.classId === action.classId)) return state; // already present — no-op
      if (totalLevel(state) >= MAX_TOTAL_LEVEL) return state; // a new class starts at level 1
      return {
        ...state,
        classes: [...state.classes, { classId: action.classId, level: 1, choices: {} }],
      };
    }
    case "REMOVE_CLASS": {
      // If the removed class is the PRIMARY (classes[0]), equipment choice
      // ids anchored to it go stale — same reasoning as SET_CLASS above.
      // Removing a non-primary class leaves classes[0] untouched, so
      // equipment choices are still anchored correctly and need no change.
      const isPrimary = state.classes[0]?.classId === action.classId;
      return {
        ...state,
        classes: state.classes.filter((c) => c.classId !== action.classId),
        ...(isPrimary ? { equipment: { ...state.equipment, choices: {} } } : {}),
      };
    }
    case "SET_BACKGROUND":
      // Equipment choice ids are also background-scoped, so they go stale
      // on background change too — see SET_CLASS above.
      return {
        ...state,
        background: { id: action.backgroundId, choices: {} },
        equipment: { ...state.equipment, choices: {} },
      };
    case "SET_SPECIES":
      // Switching species clears any subspecies pick too — a subspecies id
      // from the old species is never valid for the new one.
      return { ...state, species: { id: action.speciesId, choices: {} } };
    case "SET_SUBSPECIES":
      return {
        ...state,
        species: { ...state.species, subspeciesId: action.subspeciesId, choices: {} },
      };
    case "SET_CLASS_LEVEL": {
      // Per-class 1..20 AND the whole character capped at 20 levels.
      const others = totalLevel(state) - (state.classes.find((c) => c.classId === action.classId)?.level ?? 0);
      const level = Math.max(1, Math.min(20, MAX_TOTAL_LEVEL - others, action.level));
      return {
        ...state,
        classes: state.classes.map((c) => (c.classId === action.classId ? { ...c, level } : c)),
      };
    }
    case "SET_SUBCLASS":
      return {
        ...state,
        classes: state.classes.map((c) => (c.classId === action.classId ? { ...c, subclassId: action.subclassId } : c)),
      };
    case "SET_HP_ROLL":
      return {
        ...state,
        classes: state.classes.map((c) =>
          c.classId === action.classId
            ? { ...c, hpRolls: { ...(c.hpRolls ?? {}), [String(action.level)]: action.value } }
            : c
        ),
      };
    case "SET_ABILITY_METHOD":
      return { ...state, abilities: { ...state.abilities, method: action.method } };
    case "SET_HIT_POINT_TYPE":
      return { ...state, preferences: { ...state.preferences, hitPointType: action.hitPointType } };
    case "SET_USE_PREREQUISITE":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          usePrerequisites: { ...state.preferences.usePrerequisites, [action.field]: action.value },
        },
      };
    case "SET_ABILITY_SCORES":
      return { ...state, abilities: { ...state.abilities, base: { ...action.base } } };
    case "SET_ABILITY_SCORE":
      return {
        ...state,
        abilities: {
          ...state.abilities,
          base: { ...state.abilities.base, [action.ability]: action.value },
        },
      };
    case "SET_DETAIL":
      return { ...state, details: { ...state.details, [action.field]: action.value } };
    case "SET_CHOICE_SELECTION": {
      if (action.source === "class") {
        const targetClassId = action.choiceId.split(":")[1];
        return {
          ...state,
          classes: state.classes.map((c) =>
            c.classId === targetClassId ? { ...c, choices: { ...c.choices, [action.choiceId]: action.selected } } : c
          ),
        };
      }
      if (action.source === "background") {
        return {
          ...state,
          background: {
            ...state.background,
            choices: { ...state.background.choices, [action.choiceId]: action.selected },
          },
        };
      }
      if (action.source === "species") {
        return {
          ...state,
          species: {
            ...state.species,
            choices: { ...state.species.choices, [action.choiceId]: action.selected },
          },
        };
      }
      if (action.source === "equipment") {
        return {
          ...state,
          equipment: {
            ...state.equipment,
            choices: { ...state.equipment.choices, [action.choiceId]: action.selected },
          },
        };
      }
      return state; // subclass/feature choices aren't dispatched from anywhere yet
    }
    case "ADD_ITEM": {
      const existing = state.equipment.added.find((e) => e.itemId === action.itemId);
      const added = existing
        ? state.equipment.added.map((e) => (e.itemId === action.itemId ? { ...e, qty: e.qty + 1 } : e))
        : [...state.equipment.added, { itemId: action.itemId, qty: 1, equipped: false }];
      return { ...state, equipment: { ...state.equipment, added } };
    }
    case "REMOVE_ITEM":
      return {
        ...state,
        equipment: { ...state.equipment, added: state.equipment.added.filter((e) => e.itemId !== action.itemId) },
      };
    case "TOGGLE_EQUIPPED":
      return {
        ...state,
        equipment: {
          ...state.equipment,
          added: state.equipment.added.map((e) => (e.itemId === action.itemId ? { ...e, equipped: !e.equipped } : e)),
        },
      };
    case "SET_WORN": {
      const { worn: _drop, ...rest } = state.equipment;
      return { ...state, equipment: action.worn ? { ...rest, worn: action.worn } : rest };
    }
    case "SET_WIELDED": {
      const { wielded: _drop, ...rest } = state.equipment;
      return { ...state, equipment: action.wielded ? { ...rest, wielded: action.wielded } : rest };
    }
    default:
      return state;
  }
}

const DRAFT_KEYS = ["draftVersion", "classes", "species", "background", "abilities", "equipment"];

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function mergeInto(defaults: unknown, stored: unknown): unknown {
  if (isPlainObject(defaults)) {
    if (!isPlainObject(stored)) return defaults;
    const out: Record<string, unknown> = { ...defaults };
    for (const [k, v] of Object.entries(stored)) {
      out[k] = k in defaults ? mergeInto(defaults[k], v) : v;
    }
    return out;
  }
  if (Array.isArray(defaults)) return Array.isArray(stored) ? stored : defaults;
  // primitive default: keep stored only when it has the same type
  return typeof stored === typeof defaults ? stored : defaults;
}

/** Drop malformed list entries (null, non-objects, missing ids) that a
 *  hand-edited or corrupt stored/uploaded draft can carry; they would
 *  otherwise crash the pages that iterate them. */
export function sanitizeDraft(d: Draft): Draft {
  const classes = (Array.isArray(d.classes) ? d.classes : [])
    .filter((c): c is Draft["classes"][number] => isPlainObject(c) && typeof c.classId === "string" && c.classId !== "")
    .map((c) => {
      const out: Draft["classes"][number] = {
        ...c,
        level: typeof c.level === "number" && Number.isFinite(c.level) ? Math.min(20, Math.max(1, Math.trunc(c.level))) : 1,
        choices: choiceMap(c.choices),
      };
      if (typeof c.subclassId !== "string") delete out.subclassId;
      if (c.hpRolls !== undefined) {
        out.hpRolls = isPlainObject(c.hpRolls)
          ? Object.fromEntries(Object.entries(c.hpRolls).filter(([, v]) => typeof v === "number" && Number.isFinite(v)))
          : {};
      }
      return out;
    });
  const seen = new Set<string>();
  const uniqueClasses = classes.filter((c) => (seen.has(c.classId) ? false : (seen.add(c.classId), true)));
  const added = (Array.isArray(d.equipment?.added) ? d.equipment.added : []).filter(
    (e) => isPlainObject(e) && typeof e.itemId === "string" && typeof e.qty === "number" && Number.isFinite(e.qty)
  );
  const species = { ...d.species, choices: choiceMap(d.species?.choices) };
  if (typeof species.id !== "string") delete species.id;
  if (typeof species.subspeciesId !== "string") delete species.subspeciesId;
  const background = { ...d.background, choices: choiceMap(d.background?.choices) };
  if (typeof background.id !== "string") delete background.id;
  // FE-06: only the keys of a draft, and only well-typed values in them
  const out: Record<string, unknown> = {};
  for (const key of DRAFT_TOP_KEYS) if (key in d) out[key] = (d as unknown as Record<string, unknown>)[key];
  return {
    ...(out as unknown as Draft),
    name: typeof d.name === "string" ? d.name : "",
    sources: Array.isArray(d.sources) ? d.sources.filter((s): s is string => typeof s === "string") : [],
    classes: uniqueClasses,
    species,
    background,
    equipment: { ...d.equipment, added },
    details: detailStrings(d.details),
  };
}

/** The keys of a draft (the others of a stored or uploaded object are dropped). */
const DRAFT_TOP_KEYS = ["draftVersion", "name", "sources", "ruleset", "preferences", "classes", "background", "species", "abilities", "equipment", "details"];

/** `Record<string, string[]>` from whatever is stored: lists keep their strings, anything else is dropped. */
function choiceMap(value: unknown): Record<string, string[]> {
  if (!isPlainObject(value)) return {};
  const out: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(value)) {
    if (Array.isArray(v)) out[k] = v.filter((x): x is string => typeof x === "string");
  }
  return out;
}

/** Detail fields are text: strings stay, numbers become their text, everything else is dropped. */
function detailStrings(value: unknown): Draft["details"] {
  if (!isPlainObject(value)) return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(value)) {
    if (typeof v === "string") out[k] = v;
    else if (typeof v === "number" && Number.isFinite(v)) out[k] = String(v);
  }
  return out as Draft["details"];
}

/** Deep-merge a stored/imported draft over the defaults so keys added by a
 *  newer build never come back undefined. Throws on non-objects or on a
 *  draft written by a newer app version. */
export function mergeDraft(stored: unknown): Draft {
  if (!isPlainObject(stored)) throw new MsgError(msg("draft.notADraft"));
  const v = stored.draftVersion;
  if (typeof v === "number" && v > DRAFT_VERSION) {
    throw new MsgError(msg("draft.newer"));
  }
  // an arbitrary JSON object (e.g. an exported sheet) is not a draft: demand at least one draft key
  if (!DRAFT_KEYS.some((k) => k in stored)) throw new MsgError(msg("draft.notRecognised"));
  const merged = mergeInto(emptyDraft, migrateDraft(stored, DRAFT_VERSION)) as Draft;
  return sanitizeDraft({ ...merged, draftVersion: DRAFT_VERSION });
}
