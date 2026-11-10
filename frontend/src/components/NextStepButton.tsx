import { Link, useLocation } from "react-router-dom";
import { useT } from "../LanguageContext";
import { nextStepAfter } from "../logic/steps";

/** "Next" button at the very bottom of every step page: goes to the step after the current one in the
 *  fixed STEPS order (unlike NextStepLink, which jumps to the first unfinished step). Nothing on the last
 *  step (Export) and on non-step routes (Help). `data-next` holds the target step key. */
export function NextStepButton() {
  const t = useT();
  const { pathname } = useLocation();
  const next = nextStepAfter(pathname);
  if (!next) return null;
  return (
    <Link
      className="next-button"
      data-next={next.key}
      to={next.path}
      aria-label={`${t.nav.nextButton}: ${t.nav.steps[next.key]}`}
      // a new page opens at its top (RouteA11y moves focus with preventScroll, so it does not scroll)
      onClick={() => window.scrollTo?.(0, 0)}
    >
      {t.nav.nextButton}
    </Link>
  );
}
