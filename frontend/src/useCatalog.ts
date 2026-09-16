import { useCallback, useEffect, useState } from "react";

export interface CatalogClass {
  id: string;
  name: string;
  hitDie: number;
}

export interface CatalogBackground {
  id: string;
  name: string;
}

export interface CatalogSpeciesSubspecies {
  id: string;
  name: string;
}

export interface CatalogSpecies {
  id: string;
  name: string;
  subspecies: CatalogSpeciesSubspecies[];
}

interface CatalogState {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  loading: boolean;
  error: string | null;
}

const EMPTY_STATE: CatalogState = { classes: [], backgrounds: [], species: [], loading: true, error: null };

export function useCatalog(): CatalogState & { retry: () => void } {
  const [state, setState] = useState<CatalogState>(EMPTY_STATE);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetch("/api/catalog")
      .then((resp) => {
        if (!resp.ok) throw new Error(`catalog fetch failed: ${resp.status}`);
        return resp.json() as Promise<Omit<CatalogState, "loading" | "error">>;
      })
      .then((data) => {
        if (cancelled) return;
        setState({ ...data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setState((s) => ({ ...s, loading: false, error: message }));
      });
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
