import { createContext, useContext, useReducer, useEffect, type Dispatch, type ReactNode } from "react";
import type { Ability, ChoiceSourceKind, Draft } from "./types";

const STORAGE_KEY = "dnd-builder-draft-v2";

export const emptyDraft: Draft = {
  name: "",
  sources: ["srd"],
  preferences: {
    advancementType: "milestone",
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
  | { type: "SET_ADVANCEMENT_TYPE"; advancementType: Draft["preferences"]["advancementType"] }
  | { type: "SET_USE_PREREQUISITE"; field: keyof Draft["preferences"]["usePrerequisites"]; value: boolean }
  | { type: "SET_ABILITY_SCORE"; ability: Ability; value: number }
  | { type: "SET_DETAIL"; field: keyof Draft["details"]; value: string }
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] }
  | { type: "ADD_ITEM"; itemId: string }
  | { type: "REMOVE_ITEM"; itemId: string }
  | { type: "TOGGLE_EQUIPPED"; itemId: string };

function reducer(state: Draft, action: Action): Draft {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.name };
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
      const level = Math.min(20, Math.max(1, action.level));
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
    case "SET_ADVANCEMENT_TYPE":
      return { ...state, preferences: { ...state.preferences, advancementType: action.advancementType } };
    case "SET_USE_PREREQUISITE":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          usePrerequisites: { ...state.preferences.usePrerequisites, [action.field]: action.value },
        },
      };
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

function loadInitial(): Draft {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...emptyDraft, ...(JSON.parse(raw) as Partial<Draft>) };
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
