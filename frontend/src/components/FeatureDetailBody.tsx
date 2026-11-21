import { useState } from "react";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import type { FeatureDetail } from "../useFeatureDetail";
import type { DetailState } from "../useLangDetails";

export type FeatureDetailState = DetailState<FeatureDetail>;

/** One feature: its name, a level / class line (when it has them) and the text paragraphs. */
export function FeatureDetailBody({ state, compact = false }: { state: FeatureDetailState | undefined; compact?: boolean }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const f = state.value;
  const where = [f.subclassName ?? f.className, f.level != null ? t.classPage.levelN(f.level) : null].filter(Boolean).join(" · ");
  return (
    <div className="species-eye__body">
      {!compact && (
        <p className="species-eye__facts">
          <span className="species-eye__trait-name">{f.name}</span>
          {where && <span className="species-eye__fact"> — {where}</span>}
        </p>
      )}
      {compact ? <ClampedParagraphs paragraphs={f.desc} /> : f.desc.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
    </div>
  );
}

/** A text longer than this many characters is cut (at a sentence end where there is one) with a "Show more" button. */
export const CLAMP_CHARS = 520;

/** The first part of `paragraphs` that fits `max` characters, cut at the end of a sentence (else at a word), or null when the whole
 *  text is short enough (a little over the limit is not worth a button). */
export function clampParagraphs(paragraphs: string[], max: number = CLAMP_CHARS): string[] | null {
  const total = paragraphs.reduce((n, p) => n + p.length, 0);
  if (total <= max * 1.25) return null;
  const out: string[] = [];
  let used = 0;
  for (const p of paragraphs) {
    if (used + p.length <= max) {
      out.push(p);
      used += p.length;
      continue;
    }
    if (out.length === 0) {
      const room = p.slice(0, max);
      const sentence = Math.max(room.lastIndexOf(". "), room.lastIndexOf("! "), room.lastIndexOf("? "));
      const cut = sentence > max * 0.4 ? sentence + 1 : room.lastIndexOf(" ");
      out.push(`${p.slice(0, cut > 0 ? cut : max).trimEnd()}${sentence > max * 0.4 ? "" : "…"}`);
    }
    break;
  }
  return out;
}

function ClampedParagraphs({ paragraphs }: { paragraphs: string[] }) {
  const t = useT();
  const [expanded, setExpanded] = useState(false);
  const short = clampParagraphs(paragraphs);
  const shown = !short || expanded ? paragraphs : short;
  return (
    <>
      {shown.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
      {short && (
        <button type="button" className="feature-card__more" aria-expanded={expanded} onClick={() => setExpanded((v) => !v)}>
          {expanded ? t.common.showLess : t.common.showMore}
        </button>
      )}
    </>
  );
}
