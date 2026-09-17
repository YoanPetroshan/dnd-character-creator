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
  material: string | null;
  desc: string;
}

interface SpellsState {
  spells: CatalogSpell[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 150;

export function useSpells(classId: string, level: string, query: string): SpellsState & { retry: () => void } {
  const [state, setState] = useState<SpellsState>({ spells: [], loading: false, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

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
  }, [classId, level, query, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
