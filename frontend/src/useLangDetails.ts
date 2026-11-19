import { useEffect, useRef, useState } from "react";
import { useLang } from "./LanguageContext";
import type { Lang } from "./copy";
import { cacheFor, cachePut, emptyCache, type LangCache } from "./logic/langCache";
import { toMsg, type Msg } from "./logic/messages";

export type DetailState<T> = { status: "loading" } | { status: "error"; message: Msg } | { status: "ready"; value: T };

/** Lazily fetched details keyed by id and the app language (same shape as useFeatDetails): a language switch refetches
 *  the ones that were opened, and a response for another language is dropped. */
export function useLangDetails<T>(fetcher: (id: string, lang: Lang) => Promise<T>) {
  const { lang } = useLang();
  const [cache, setCache] = useState<LangCache<DetailState<T>>>(() => emptyCache(lang));
  const requested = useRef<{ lang: Lang; ids: Set<string> }>({ lang, ids: new Set() });
  const current = useRef(lang);
  current.current = lang;
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  function loadDetail(id: string) {
    if (requested.current.lang !== lang) requested.current = { lang, ids: new Set() };
    const ids = requested.current.ids;
    if (ids.has(id)) return;
    ids.add(id);
    const put = (state: DetailState<T>) => setCache((c) => cachePut(c, lang, id, state, current.current));
    put({ status: "loading" });
    fetcher(id, lang)
      .then((value) => {
        if (alive.current) put({ status: "ready", value });
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        ids.delete(id);
        put({ status: "error", message: toMsg(err) });
      });
  }

  const loadRef = useRef(loadDetail);
  loadRef.current = loadDetail;
  const opened = useRef(new Set<string>());
  useEffect(() => {
    [...opened.current].forEach((id) => loadRef.current(id));
  }, [lang]);

  const all = cacheFor(cache, lang);
  return {
    detailOf: (id: string): DetailState<T> | undefined => all[id],
    loadDetail: (id: string) => {
      opened.current.add(id);
      loadDetail(id);
    },
  };
}
