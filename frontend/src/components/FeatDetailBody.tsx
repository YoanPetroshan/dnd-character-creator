import { useEffect, useRef, useState } from "react";
import { useLang, useT } from "../LanguageContext";
import type { Lang } from "../copy";
import { cacheFor, cachePut, emptyCache, type LangCache } from "../logic/langCache";
import { renderMsg, toMsg, type Msg } from "../logic/messages";
import { fetchFeatDetail, type FeatDetail } from "../useFeats";

export type FeatDetailState = { status: "loading" } | { status: "error"; message: Msg } | { status: "ready"; feat: FeatDetail };

/** Lazily fetched feat texts keyed by feat id and the app language (same shape as useItemDetails). */
export function useFeatDetails() {
  const { lang } = useLang();
  const [cache, setCache] = useState<LangCache<FeatDetailState>>(() => emptyCache(lang));
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
    const put = (state: FeatDetailState) => setCache((c) => cachePut(c, lang, id, state, current.current));
    put({ status: "loading" });
    fetchFeatDetail(id, lang)
      .then((feat) => {
        if (alive.current) put({ status: "ready", feat });
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
    detailOf: (id: string): FeatDetailState | undefined => all[id],
    loadDetail: (id: string) => {
      opened.current.add(id);
      loadDetail(id);
    },
  };
}

export function FeatDetailBody({ state }: { state: FeatDetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const { feat } = state;
  return (
    <div className="species-eye__body">
      {feat.prerequisite && (
        <p className="species-eye__facts">
          <span className="species-eye__fact">
            <span className="species-eye__fact-label">{t.choice.prerequisite}</span> {feat.prerequisite}
          </span>
        </p>
      )}
      {feat.desc.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
    </div>
  );
}
