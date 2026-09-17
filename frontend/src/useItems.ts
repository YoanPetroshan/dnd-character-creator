import { useCallback, useEffect, useRef, useState } from "react";

export interface CatalogItem {
  id: string;
  name: string;
  category: string;
}

interface ItemsState {
  items: CatalogItem[];
  loading: boolean;
  error: string | null;
}

const DEBOUNCE_MS = 150;

export function useItems(category: string, query: string): ItemsState & { retry: () => void } {
  const [state, setState] = useState<ItemsState>({ items: [], loading: true, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (query) params.set("q", query);
      fetch(`/api/items?${params.toString()}`)
        .then((resp) => {
          if (!resp.ok) throw new Error(`items fetch failed: ${resp.status}`);
          return resp.json() as Promise<{ items: CatalogItem[] }>;
        })
        .then((data) => {
          if (id !== requestId.current) return;
          setState({ items: data.items, loading: false, error: null });
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
  }, [category, query, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
