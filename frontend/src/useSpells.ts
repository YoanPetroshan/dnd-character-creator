import { useCallback, useEffect, useRef, useState } from "react";

export interface CatalogSpell {
  id: string;
  name: string;
  level: number;
  school: string | null;
  castingTime: string | null;
  range: string | null;
  components: string[];
  duration: string | null;
  concentration: boolean;
  ritual: boolean;
  /** Book code ("SRD", "PHB", "XGE", ...) and the ruleset the book was printed under. */
  source: string;
  ruleset: string;
}

/** GET /api/spells/<id>: what the slim list rows leave out. */
export interface SpellDetail extends CatalogSpell {
  material: string | null;
  desc: string[];
  higherLevel: string[];
  castingCondition: string | null;
  classes: { id: string; name: string }[];
  sourceName: string;
}

export async function fetchSpellDetail(id: string, signal?: AbortSignal): Promise<SpellDetail> {
  const resp = await fetch(`/api/spells/${encodeURIComponent(id)}`, { signal });
  if (!resp.ok) throw new Error(`spell fetch failed: ${resp.status}`);
  return (await resp.json()) as SpellDetail;
}

interface SpellsState {
  spells: CatalogSpell[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 150;

/** `ruleset` / `sources` are the draft's: they decide which spells the server lists. */
export function useSpells(
  classId: string, level: string, query: string, ruleset: string = "mixed", sources: string[] = [],
): SpellsState & { retry: () => void } {
  const [state, setState] = useState<SpellsState>({ spells: [], loading: false, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);
  const sourcesKey = sources.join(",");

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!classId) {
      requestId.current++;
      setState({ spells: [], loading: false, error: null });
      return;
    }
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      const params = new URLSearchParams();
      params.set("class", classId);
      if (level) params.set("level", level);
      if (query) params.set("q", query);
      if (ruleset !== "mixed") params.set("ruleset", ruleset);
      if (sourcesKey) params.set("sources", sourcesKey);
      fetch(`/api/spells?${params.toString()}`)
        .then((resp) => {
          if (!resp.ok) throw new Error(`spells fetch failed: ${resp.status}`);
          return resp.json() as Promise<{ spells: CatalogSpell[] }>;
        })
        .then((data) => {
          if (id !== requestId.current) return;
          setState({ spells: data.spells, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current) return;
          const message = err instanceof Error ? err.message : String(err);
          setState((s) => ({ ...s, loading: false, error: message }));
        });
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [classId, level, query, ruleset, sourcesKey, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
