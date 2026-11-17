import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./api/transport";
import type { Lang } from "./copy";
import { withLang } from "./logic/langQuery";
import { MsgError, msg, toMsg, type Msg } from "./logic/messages";

export interface CatalogItem {
  id: string;
  name: string;
  category: string;
  source?: string;
  ruleset?: string;
}

/** GET /api/items/<id>: what the item eye shows. Names (item, property, mastery) stay English; the texts follow `lang`. */
export interface ItemDetail extends CatalogItem {
  cost: { quantity: number; unit: string } | null;
  weight: number | null;
  damage: { dice: string; type: string | null } | null;
  twoHandedDamage: { dice: string; type: string | null } | null;
  range: { normal: number; long?: number | null } | null;
  throwRange: { normal: number; long?: number | null } | null;
  properties: { id: string; name: string; desc: string[] }[];
  mastery: { name: string; desc: string[] } | null;
  armor: { base: number; dexBonus: boolean; maxBonus: number | null; strMinimum: number; stealthDisadvantage: boolean } | null;
  contents: { id: string | null; name: string | null; qty: number }[];
  desc: string[];
  special: string[];
  textLang?: "bg" | "en";
}

export async function fetchItemDetail(id: string, lang: Lang, ruleset: string, signal?: AbortSignal): Promise<ItemDetail> {
  const base = `/api/items/${encodeURIComponent(id)}${ruleset && ruleset !== "mixed" ? `?ruleset=${encodeURIComponent(ruleset)}` : ""}`;
  const resp = await apiFetch(withLang(base, lang), { signal });
  if (!resp.ok) throw new MsgError(msg("item.failed", { status: resp.status }));
  return (await resp.json()) as ItemDetail;
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
      apiFetch(`/api/items?${params.toString()}`)
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
