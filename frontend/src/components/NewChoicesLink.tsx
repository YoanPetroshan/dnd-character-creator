import { Link } from "react-router-dom";
import { useT } from "../LanguageContext";
import { useNewChoices } from "../NewChoicesContext";
import { stepForChoice } from "../logic/steps";

/** "New choices: N" under the step nav: links to the first new card (its step page and card anchor).
 *  Nothing is rendered when no level-up choice is waiting. */
export function NewChoicesLink() {
  const t = useT();
  const { ids } = useNewChoices();
  if (ids.length === 0) return null;
  return (
    <p className="new-choices" data-new="true">
      <Link to={{ pathname: stepForChoice(ids[0]), hash: ids[0] }}>{t.nav.newChoices(ids.length)}</Link>
    </p>
  );
}
