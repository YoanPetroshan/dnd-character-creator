import { Link } from "react-router-dom";
import { useT } from "../../LanguageContext";
import { exportReadiness } from "../../logic/exportReadiness";
import { stepForChoice } from "../../logic/steps";
import { stepForProblem } from "../../problems";
import type { Resolution } from "../../types";

const PART_PATH = { class: "/class", species: "/species", background: "/background" } as const;

/** The alert at the top of an unfinished sheet: a red mark, the bold count of what is left, the reason the downloads are
 *  off, and every missing part, pending choice and problem as a link to the step that fixes it. It is the element the
 *  download buttons point to (`aria-describedby="export-reasons"`). Nothing is rendered for a sheet that can be exported. */
export function IncompleteAlert({ resolution, error }: { resolution: Resolution; error: unknown }) {
  const t = useT();
  const { missingParts, pendingChoices, problems, canExport } = exportReadiness(resolution, error);
  if (canExport) return null;
  const count = missingParts.length + pendingChoices.length + problems.length;
  return (
    <section id="export-reasons" className="sheet-alert" data-state="incomplete" aria-label={t.sheet.incompleteLabel}>
      {count > 0 && (
        <p className="sheet-alert__title" role="status">
          <span className="alert-dot" aria-hidden="true">
            !
          </span>
          <span>
            {t.sheet.incompleteLead} <strong className="sheet-alert__count">{count}</strong>
          </span>
        </p>
      )}
      <p className="sheet-alert__reason">{t.exportPage.notReady}</p>
      {count > 0 && (
        <ul className="sheet-alert__list">
          {missingParts.map((m) => (
            <li key={m}>
              <Link to={PART_PATH[m]}>{t.exportPage.missing[m]}</Link>
            </li>
          ))}
          {problems.map((p) => {
            const step = stepForProblem(p);
            return <li key={p.id}>{step ? <Link to={`/${step}`}>{p.message}</Link> : p.message}</li>;
          })}
          {pendingChoices.map((c) => (
            <li key={c.id}>
              <Link to={{ pathname: stepForChoice(c.id), hash: c.id }}>{c.label}</Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
