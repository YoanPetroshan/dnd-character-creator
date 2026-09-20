import { createContext, useContext, type ReactNode } from "react";
import { useCatalog, type CatalogClass, type CatalogBackground, type CatalogSpecies } from "./useCatalog";

interface CatalogContextValue {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  loading: boolean;
  error: string | null;
  retry: () => void;
}

const CatalogContext = createContext<CatalogContextValue | null>(null);

export function CatalogProvider({ children }: { children: ReactNode }) {
  const state = useCatalog();
  return <CatalogContext.Provider value={state}>{children}</CatalogContext.Provider>;
}

export function useCatalogContext(): CatalogContextValue {
  const ctx = useContext(CatalogContext);
  if (!ctx) throw new Error("useCatalogContext must be used within a CatalogProvider");
  return ctx;
}
