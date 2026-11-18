import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import type { FeatureDetail } from "../useFeatureDetail";
import type { DetailState } from "../useLangDetails";

export type FeatureDetailState = DetailState<FeatureDetail>;

/** One feature: its name, a level / class line (when it has them) and the text paragraphs. */
export function FeatureDetailBody({ state }: { state: FeatureDetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const f = state.value;
  const where = [f.subclassName ?? f.className, f.level != null ? t.classPage.levelN(f.level) : null].filter(Boolean).join(" · ");
  return (
    <div className="species-eye__body">
      <p className="species-eye__facts">
        <span className="species-eye__trait-name">{f.name}</span>
        {where && <span className="species-eye__fact"> — {where}</span>}
      </p>
      {f.desc.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
    </div>
  );
}
