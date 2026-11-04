import { createContext, useContext, type ReactNode } from "react";
import { useDraft } from "./DraftContext";
import type { Msg } from "./logic/messages";
import {
  useCatalog, type CatalogClass, type CatalogBackground, type CatalogSpecies, type CatalogSource,
} from "./useCatalog";

interface CatalogContextValue {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  sources: CatalogSource[];
  allBackgrounds: CatalogBackground[];
  backgroundsFallback?: boolean;
  allSpecies: CatalogSpecies[];
  loading: boolean;
  error: Msg | null;
  retry: () => void;
}

const CatalogContext = createContext<CatalogContextValue | null>(null);

export function CatalogProvider({ children }: { children: ReactNode }) {
  const { draft } = useDraft();
  const state = useCatalog(draft.ruleset, draft.sources);
  return <CatalogContext.Provider value={state}>{children}</CatalogContext.Provider>;
}

export function useCatalogContext(): CatalogContextValue {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error("useCatalogContext must be used within a CatalogProvider");
  return ctx;
}
