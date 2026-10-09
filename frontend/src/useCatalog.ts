import { useCallback, useEffect, useState } from "react";

export interface CatalogClass {
  id: string;
  name: string;
  hitDie: number;
}

export interface CatalogBackground {
  id: string;
  name: string;
  source?: string;
  ruleset?: string;
}

export interface CatalogSpeciesSubspecies {
  id: string;
  name: string;
  source?: string;
  ruleset?: string;
}

export interface CatalogSpecies {
  id: string;
  name: string;
  source?: string;
  ruleset?: string;
  subspecies: CatalogSpeciesSubspecies[];
}

export interface CatalogSource {
  id: string;
  name: string;
  count: number;
}

interface CatalogData {
  classes: CatalogClass[];
  backgrounds: CatalogBackground[];
  species: CatalogSpecies[];
  sources: CatalogSource[];
}

interface CatalogState extends CatalogData {
  /** The UNFILTERED lists, so a selected record the current ruleset/sources
   *  hides can still be shown (by name) instead of silently vanishing. */
  allBackgrounds: CatalogBackground[];
  allSpecies: CatalogSpecies[];
  loading: boolean;
  error: string | null;
}

const EMPTY_STATE: CatalogState = {
  classes: [], backgrounds: [], species: [], sources: [], allBackgrounds: [], allSpecies: [], loading: true, error: null,
};

async function fetchCatalog(query: string): Promise<CatalogData> {
  const resp = await fetch(`/api/catalog${query}`);
  if (!resp.ok) throw new Error(`catalog fetch failed: ${resp.status}`);
  return (await resp.json()) as CatalogData;
}

/** `ruleset`/`sources` come from the draft and filter the species and
 *  background lists on the server; the catalog is refetched when they change. */
export function useCatalog(ruleset: string = "mixed", sources: string[] = []): CatalogState & { retry: () => void } {
  const [state, setState] = useState<CatalogState>(EMPTY_STATE);
  const [nonce, setNonce] = useState(0);
  const sourcesKey = sources.join(",");

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    const params = new URLSearchParams();
    if (ruleset !== "mixed") params.set("ruleset", ruleset);
    if (sourcesKey) params.set("sources", sourcesKey);
    const query = params.toString() ? `?${params}` : "";
    const filtered = fetchCatalog(query);
    const all = query ? fetchCatalog("") : filtered;
    Promise.all([filtered, all])
      .then(([data, full]) => {
        if (cancelled) return;
        setState({
          ...data,
          sources: full.sources, // the picker always lists every book
          allBackgrounds: full.backgrounds,
          allSpecies: full.species,
          loading: false,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setState((s) => ({ ...s, loading: false, error: message }));
      });
    return () => {
      cancelled = true;
    };
  }, [nonce, ruleset, sourcesKey]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
