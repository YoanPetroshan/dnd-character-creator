import { useEffect, useRef, useState } from "react";
import { useLang, useT } from "../LanguageContext";
import { cacheFor, cachePut, emptyCache, type LangCache } from "../logic/langCache";
import { renderMsg, toMsg, type Msg } from "../logic/messages";
import type { Lang } from "../copy";
import { fetchSpellDetail, type SpellDetail } from "../useSpells";

export type DetailState = { status: "loading" } | { status: "error"; message: Msg } | { status: "ready"; spell: SpellDetail };

/** Lazily fetched spell texts keyed by spell id and the app language: `loadDetail(id)` fetches once per language (a
 *  failed fetch may be retried), and switching the language hides the other language's texts. */
export function useSpellDetails() {
  const { lang } = useLang();
  const [cache, setCache] = useState<LangCache<DetailState>>(() => emptyCache(lang));
  const requested = useRef<{ lang: Lang; ids: Set<string> }>({ lang, ids: new Set() });
  const current = useRef(lang);
  current.current = lang;
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode runs mount, cleanup, mount
    return () => {
      alive.current = false;
    };
  }, []);

  function loadDetail(id: string) {
    if (requested.current.lang !== lang) requested.current = { lang, ids: new Set() };
    const ids = requested.current.ids;
    if (ids.has(id)) return;
    ids.add(id);
    const put = (state: DetailState) => setCache((c) => cachePut(c, lang, id, state, current.current));
    put({ status: "loading" });
    fetchSpellDetail(id, lang)
      .then((spell) => {
        if (alive.current) put({ status: "ready", spell });
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        ids.delete(id); // closing and reopening the card retries
        put({ status: "error", message: toMsg(err) });
      });
  }

  // A card that was opened before a language switch is still open: fetch its text again in the new language.
  const loadRef = useRef(loadDetail);
  loadRef.current = loadDetail;
  const opened = useRef(new Set<string>());
  useEffect(() => {
    const ids = [...opened.current];
    ids.forEach((id) => loadRef.current(id));
  }, [lang]);

  return {
    details: cacheFor(cache, lang),
    loadDetail: (id: string) => {
      opened.current.add(id);
      loadDetail(id);
    },
  };
}

export function SpellDetailBody({ state }: { state: DetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="spell-library-card__desc">{t.common.loading}</p>;
  if (state.status === "error") return <p className="spell-library-card__desc">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const { spell } = state;
  return (
    <div className="spell-library-card__body">
      {spell.material && <p className="spell-library-card__material">{spell.material}</p>}
      {spell.castingCondition && <p className="spell-library-card__material">{spell.castingCondition}</p>}
      {spell.desc.map((paragraph, i) => (
        <p key={i} className="spell-library-card__desc">
          {paragraph}
        </p>
      ))}
      {spell.higherLevel.map((paragraph, i) => (
        <p key={`h${i}`} className="spell-library-card__desc">
          {paragraph}
        </p>
      ))}
      <p className="spell-library-card__material">
        {spell.sourceName}
        {spell.classes.length > 0 && ` · ${spell.classes.map((c) => c.name).join(", ")}`}
      </p>
    </div>
  );
}
