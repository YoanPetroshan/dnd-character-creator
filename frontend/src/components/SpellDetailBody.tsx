import { useEffect, useRef, useState } from "react";
import { useT } from "../LanguageContext";
import { renderMsg, toMsg, type Msg } from "../logic/messages";
import { fetchSpellDetail, type SpellDetail } from "../useSpells";

export type DetailState = { status: "loading" } | { status: "error"; message: Msg } | { status: "ready"; spell: SpellDetail };

/** Lazily fetched spell texts keyed by spell id: `loadDetail(id)` fetches once (a failed fetch may be retried). */
export function useSpellDetails() {
  const [details, setDetails] = useState<Record<string, DetailState>>({});
  const requested = useRef(new Set<string>());
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode runs mount, cleanup, mount
    return () => {
      alive.current = false;
    };
  }, []);

  function loadDetail(id: string) {
    if (requested.current.has(id)) return;
    requested.current.add(id);
    setDetails((d) => ({ ...d, [id]: { status: "loading" } }));
    fetchSpellDetail(id)
      .then((spell) => {
        if (alive.current) setDetails((d) => ({ ...d, [id]: { status: "ready", spell } }));
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        requested.current.delete(id); // closing and reopening the card retries
        setDetails((d) => ({ ...d, [id]: { status: "error", message: toMsg(err) } }));
      });
  }

  return { details, loadDetail };
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
