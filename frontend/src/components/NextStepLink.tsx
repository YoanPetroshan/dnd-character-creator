import { Link, useLocation } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { useResolutionContext } from "../ResolutionContext";
import { STEPS, nextUnfinishedStep } from "../logic/steps";

/** Link to the first unfinished step, shown under the StepNav on every page. It names the step and says whether it
 *  lies behind the page the player is on ("Back to ...") or ahead ("On to ..."); the Sheet when nothing is outstanding.
 *  Nothing is shown on the page it would point to. */
export function NextStepLink() {
  const t = useT();
  const { draft } = useDraft();
  const { resolution } = useResolutionContext();
  const { pathname } = useLocation();
  const next = nextUnfinishedStep(resolution, draft);
  if (!next || next === pathname) return null;
  const nextIndex = STEPS.findIndex((s) => s.path === next);
  const hereIndex = STEPS.findIndex((s) => s.path === pathname);
  const step = STEPS[nextIndex];
  const label = !step
    ? t.nav.nextStepAhead(t.nav.sheet)
    : next === "/sheet"
      ? t.nav.nextStepSheet
      : hereIndex >= 0 && nextIndex < hereIndex
        ? t.nav.nextStepBack(t.nav.steps[step.key])
        : t.nav.nextStepAhead(t.nav.steps[step.key]);
  return (
    <nav className="next-step" aria-label={t.nav.nextStepRegion}>
      <Link to={next}>{label}</Link>
    </nav>
  );
}
