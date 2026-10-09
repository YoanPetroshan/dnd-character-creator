import { createContext, useContext, useReducer, useEffect, type Dispatch, type ReactNode } from "react";
import type { Ability, ChoiceSourceKind, Draft, Ruleset } from "./types";

const STORAGE_KEY = "dnd-builder-draft-v2";

/** Bump when the draft shape changes incompatibly. Stored/imported drafts
 *  with a NEWER version than this build are rejected rather than guessed at.
 *  v2: `ruleset` added. Older drafts need no migration step: mergeDraft
 *  fills the missing key with the default ("mixed", the behaviour they had)
 *  and stamps the current version. */
export const DRAFT_VERSION = 2;

export const emptyDraft: Draft = {
  draftVersion: DRAFT_VERSION,
  name: "",
  // Empty = "everything available" (server/engine/resolve.py's permissive
  // default). This was `["srd"]` since Phase 0, before any sourcebook data
  // existed — but SpeciesPage already lets a player pick any official race
  // from the unfiltered /api/catalog list, and this draft is the base
  // template for every new/persisted draft, so a non-empty default here
  // silently breaks every sourcebook race pick with a spurious
  // "unknown species" resolve() problem. The Sources picker on the Home
  // page narrows this down (and "None except SRD" stores ["srd"], since
  // an empty list means "everything").
  sources: [],
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

type Action =
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
  | { type: "TOGGLE_EQUIPPED"; itemId: string };

export const MAX_TOTAL_LEVEL = 20;

export function totalLevel(d: Draft): number {
  return d.classes.reduce((sum, c) => sum + (typeof c.level === "number" ? c.level : 0), 0);
}

/** The selection currently stored in the draft for a choice (not the last
 *  server resolution, which lags by the debounce + network round trip). */
function storedSelection(state: Draft, source: ChoiceSourceKind, choiceId: string): string[] {
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

function reducer(state: Draft, action: Action): Draft {
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
    default:
      return state;
  }
}

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
function sanitizeDraft(d: Draft): Draft {
  const classes = (Array.isArray(d.classes) ? d.classes : [])
    .filter((c): c is Draft["classes"][number] => isPlainObject(c) && typeof c.classId === "string" && c.classId !== "")
    .map((c) => ({
      ...c,
      level: typeof c.level === "number" && Number.isFinite(c.level) ? Math.min(20, Math.max(1, Math.trunc(c.level))) : 1,
      choices: isPlainObject(c.choices) ? c.choices : {},
    }));
  const seen = new Set<string>();
  const uniqueClasses = classes.filter((c) => (seen.has(c.classId) ? false : (seen.add(c.classId), true)));
  const added = (Array.isArray(d.equipment?.added) ? d.equipment.added : []).filter(
    (e) => isPlainObject(e) && typeof e.itemId === "string" && typeof e.qty === "number" && Number.isFinite(e.qty)
  );
  return { ...d, classes: uniqueClasses, equipment: { ...d.equipment, added } };
}

/** Deep-merge a stored/imported draft over the defaults so keys added by a
 *  newer build never come back undefined. Throws on non-objects or on a
 *  draft written by a newer app version. */
export function mergeDraft(stored: unknown): Draft {
  if (!isPlainObject(stored)) throw new Error("This file isn't a character draft.");
  const v = stored.draftVersion;
  if (typeof v === "number" && v > DRAFT_VERSION) {
    throw new Error("This draft was saved by a newer version of the app.");
  }
  const merged = mergeInto(emptyDraft, stored) as Draft;
  return sanitizeDraft({ ...merged, draftVersion: DRAFT_VERSION });
}

function loadInitial(): Draft {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return mergeDraft(JSON.parse(raw));
  } catch {
    // corrupt or inaccessible storage — fall through to a fresh draft
  }
  return emptyDraft;
}

interface DraftContextValue {
  draft: Draft;
  dispatch: Dispatch<Action>;
}

const DraftContext = createContext<DraftContextValue | null>(null);

export function DraftProvider({ children }: { children: ReactNode }) {
  const [draft, dispatch] = useReducer(reducer, undefined, loadInitial);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // storage unavailable (private mode, quota) — the draft still works
      // in-memory for this session, it just won't survive a reload
    }
  }, [draft]);

  return <DraftContext.Provider value={{ draft, dispatch }}>{children}</DraftContext.Provider>;
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error("useDraft must be used within a DraftProvider");
  return ctx;
}
