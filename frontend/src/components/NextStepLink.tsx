import { Link } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { useResolutionContext } from "../ResolutionContext";
import { nextUnfinishedStep } from "../logic/steps";

/** "Next unfinished step" link shown under the StepNav on every page: the
 *  first step with a missing part, a pending card or a problem, else Export. */
export function NextStepLink() {
  const t = useT();
  const { draft } = useDraft();
  const { resolution } = useResolutionContext();
  const next = nextUnfinishedStep(resolution, draft);
  if (!next) return null;
  return (
    <p className="next-step">
      <Link to={next}>{t.nav.nextStep}</Link>
    </p>
  );
}
