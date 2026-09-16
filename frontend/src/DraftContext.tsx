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
  equipment: { added: [], skipped: false },
  details: {},
};

type Action =
  | { type: "SET_NAME"; name: string }
  | { type: "SET_DRAFT"; draft: Draft }
  | { type: "RESET" }
  | { type: "SET_CLASS"; classId: string }
  | { type: "SET_BACKGROUND"; backgroundId: string }
  | { type: "SET_SPECIES"; speciesId: string }
  | { type: "SET_SUBSPECIES"; subspeciesId: string | undefined }
  | { type: "SET_ABILITY_METHOD"; method: Draft["abilities"]["method"] }
  | { type: "SET_ABILITY_SCORE"; ability: Ability; value: number }
  | { type: "SET_CHOICE_SELECTION"; source: ChoiceSourceKind; choiceId: string; selected: string[] };

function reducer(state: Draft, action: Action): Draft {
  switch (action.type) {
    case "SET_NAME":
      return { ...state, name: action.name };
    case "SET_DRAFT":
      return action.draft;
    case "RESET":
      return emptyDraft;
    case "SET_CLASS":
      // A fresh single-entry array with empty choices — Phase 1 supports
      // exactly one class at level 1, and any choices tied to a previous
      // class selection are meaningless for the new one.
      return { ...state, classes: [{ classId: action.classId, level: 1, choices: {} }] };
    case "SET_BACKGROUND":
      return { ...state, background: { id: action.backgroundId, choices: {} } };
    case "SET_SPECIES":
      // Switching species clears any subspecies pick too — a subspecies id
      // from the old species is never valid for the new one.
      return { ...state, species: { id: action.speciesId, choices: {} } };
    case "SET_SUBSPECIES":
      return {
        ...state,
        species: { ...state.species, subspeciesId: action.subspeciesId, choices: {} },
      };
    case "SET_ABILITY_METHOD":
      return { ...state, abilities: { ...state.abilities, method: action.method } };
    case "SET_ABILITY_SCORE":
      return {
        ...state,
        abilities: {
          ...state.abilities,
          base: { ...state.abilities.base, [action.ability]: action.value },
        },
      };
    case "SET_CHOICE_SELECTION": {
      if (action.source === "class") {
        if (state.classes.length === 0) return state; // no class picked yet — ignore
        const [cls] = state.classes;
        return {
          ...state,
          classes: [{ ...cls, choices: { ...cls.choices, [action.choiceId]: action.selected } }],
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
      return state; // subclass/feature/equipment choices aren't dispatched from anywhere in Phase 1b
    }
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
