import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import type { SubclassDetail } from "../useSubclassDetail";
import type { DetailState } from "../useLangDetails";

export type SubclassDetailState = DetailState<SubclassDetail>;

/** What a subclass gives: the book intro, then every feature under its level with name and text. */
export function SubclassPreview({ state }: { state: SubclassDetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const sub = state.value;
  const levels = [...new Set(sub.features.map((f) => f.level))];
  return (
    <div className="species-eye__body">
      {sub.desc.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
      {levels.map((level) => (
        <section key={level} className="species-eye__traits">
          <h4 className="species-eye__trait-name">{t.classPage.levelN(level)}</h4>
          {sub.features
            .filter((f) => f.level === level)
            .map((f) => (
              <div key={f.id} className="species-eye__trait">
                <p className="species-eye__trait-name">{f.name}</p>
                {f.desc.map((paragraph, i) => (
                  <p key={i} className="species-eye__trait-text">
                    {paragraph}
                  </p>
                ))}
              </div>
            ))}
        </section>
      ))}
    </div>
  );
}
