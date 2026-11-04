import { useCallback, useEffect, useRef, useState } from "react";
import { MsgError, msg, toMsg, type Msg } from "./logic/messages";

export interface CatalogItem {
  id: string;
  name: string;
  category: string;
  source?: string;
  ruleset?: string;
}

interface ItemsState {
  items: CatalogItem[];
  loading: boolean;
  error: Msg | null;
}

const DEBOUNCE_MS = 150;

/** `ruleset` / `sources` are the draft's: they decide which sourcebook items the server lists. */
export function useItems(
  category: string, query: string, ruleset: string = "mixed", sources: string[] = [],
): ItemsState & { retry: () => void } {
  const [state, setState] = useState<ItemsState>({ items: [], loading: true, error: null });
  const [nonce, setNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);
  const sourcesKey = sources.join(",");

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (query) params.set("q", query);
      if (ruleset !== "mixed") params.set("ruleset", ruleset);
      if (sourcesKey) params.set("sources", sourcesKey);
      fetch(`/api/items?${params.toString()}`)
        .then((resp) => {
          if (!resp.ok) throw new MsgError(msg("items.failed", { status: resp.status }));
          return resp.json() as Promise<{ items: CatalogItem[] }>;
        })
        .then((data) => {
          if (id !== requestId.current) return;
          setState({ items: data.items, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current) return;
          setState((s) => ({ ...s, loading: false, error: toMsg(err) }));
        });
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [category, query, ruleset, sourcesKey, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, retry };
}
