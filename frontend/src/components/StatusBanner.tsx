import { NavLink } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";

/** App-wide status lines shown on every page: a failed /api/resolve (the last
 *  good resolution stays on screen), a draft that could not be stored or
 *  restored, and selections the server dropped. */
export function StatusBanner() {
  const t = useT();
  const { notices, storageFailed, dismissNotice, unsavedRaw } = useDraft();
  const { resolution, error, retry } = useResolutionContext();
  const prunedCount = resolution?.pruned.length ?? 0;
  return (
    <>
      {error && (
        <p className="status-banner" role="alert">
          {t.status.calcError(renderMsg(t, error))}
          {resolution && ` ${t.status.lastGood}`}{" "}
          <button type="button" onClick={retry}>
            {t.common.retry}
          </button>
        </p>
      )}
      {notices.length > 0 && (
        <p className="status-banner" role="status">
          {notices.map((m) => renderMsg(t, m)).join(" ")}{" "}
          {unsavedRaw && (
            <>
              <a href={`data:application/json;charset=utf-8,${encodeURIComponent(unsavedRaw)}`} download="dnd-draft-unreadable.json">
                {t.status.downloadOld}
              </a>{" "}
              <button type="button" onClick={() => void navigator.clipboard?.writeText(unsavedRaw).catch(() => undefined)}>
                {t.status.copyText}
              </button>{" "}
            </>
          )}
          <button type="button" onClick={dismissNotice}>
            {t.status.dismiss}
          </button>
        </p>
      )}
      {storageFailed && (
        <p className="status-banner" role="status">
          {t.status.storageFailed}
        </p>
      )}
      {prunedCount > 0 && (
        <p className="status-banner" role="status">
          {t.status.pruned(prunedCount)} <NavLink to="/home">{t.status.seeInHome}</NavLink>
        </p>
      )}
    </>
  );
}
