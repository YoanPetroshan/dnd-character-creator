import { Link } from "react-router-dom";
import { SheetView } from "../components/sheet/SheetView";
import { t } from "../copy";
import { useDraft } from "../DraftContext";
import { exportReadiness } from "../logic/exportReadiness";
import { sheetSections } from "../logic/sheetSections";
import { useResolutionContext } from "../ResolutionContext";

/** The in-app character sheet: every section of the resolution, read-only. Works on an unfinished draft too. */
export function SheetPage() {
  const { draft } = useDraft();
  const { resolution, loading, error } = useResolutionContext();

  if (!resolution) {
    return (
      <div className="page">
        <h1>{t.sheet.title}</h1>
        {!error && <p>{t.sheet.loading}</p>}
      </div>
    );
  }

  const { missingParts, pendingChoices, problems } = exportReadiness(resolution, error);
  const outstanding = missingParts.length + pendingChoices.length + problems.length;
  const sections = sheetSections(resolution, draft.abilities.base);

  return (
    <div className="page" data-page="sheet">
      <h1>
        {t.sheet.title} {loading && "…"}
      </h1>
      <p className="no-print">
        <button type="button" onClick={() => window.print()}>
          {t.sheet.print}
        </button>{" "}
        <Link to="/export">{t.sheet.exportLink}</Link>
      </p>
      {outstanding > 0 && (
        <p className="no-print" role="status">
          {t.sheet.incomplete(outstanding)}
        </p>
      )}
      <SheetView sections={sections} />
    </div>
  );
}
