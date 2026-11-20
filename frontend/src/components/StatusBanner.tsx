import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useEngineStatus } from "../api/useEngineStatus";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { DRAFT_VERSION } from "../logic/draft";
import { serverIsOlder } from "../logic/serverHealth";
import { useServerHealth } from "../useServerHealth";
import { pwa, reportStorageFailed, usePwa } from "../pwa/pwaStore";
import { useLibrary } from "../LibraryContext";
import { safeFilename, shareOrDownload } from "../logic/files";

/** App-wide status lines shown on every page: a failed /api/resolve (the last
 *  good resolution stays on screen), a draft that could not be stored or
 *  restored, and selections the server dropped. */
export function StatusBanner() {
  const t = useT();
  const { notices, storageFailed, dismissNotice, unsavedRaw } = useDraft();
  const { resolution, error, retry } = useResolutionContext();
  const health = useServerHealth();
  const engine = useEngineStatus();
  const offline = usePwa();
  const [readyDismissed, setReadyDismissed] = useState(false);
  const library = useLibrary();
  const [backup, setBackup] = useState<{ skipped: string[] } | null>(null);
  // an update must not take over a draft that exists only in memory (see pwa/register.ts, dataAtRisk)
  useEffect(() => reportStorageFailed(storageFailed), [storageFailed]);
  async function downloadBackup() {
    const { json, skipped } = library.exportAll();
    await shareOrDownload(new Blob([json], { type: "application/json" }), safeFilename("dnd-heroes", "json"), "application/json");
    setBackup({ skipped });
  }
  const prunedCount = resolution?.pruned.length ?? 0;
  return (
    <>
      {engine.engine === "starting" && (
        <p className="status-banner" role="status" data-state="engine-starting">
          {t.status.engineStarting}
        </p>
      )}
      {engine.engine === "unavailable" && (
        <p className="status-banner" role="alert" data-state="engine-unavailable">
          {t.status.engineUnavailable} <NavLink to="/help">{t.pwa.helpLink}</NavLink>
        </p>
      )}
      {offline.phase === "installing" && (
        <p className="status-banner" role="status" data-state="pwa-installing">
          {t.pwa.installing}
        </p>
      )}
      {offline.phase === "error" && (
        <p className="status-banner" role="status" data-state="pwa-error">
          {t.pwa.installFailed}
        </p>
      )}
      {offline.phase === "update-available" && (
        <p className="status-banner" role="status" data-state="update-available">
          {t.pwa.updateAvailable}{" "}
          <button type="button" onClick={() => pwa().applyUpdate()}>
            {t.pwa.updateNow}
          </button>
        </p>
      )}
      {offline.phase === "update-needs-backup" && (
        <div className="status-banner" role="alert" data-state="update-needs-backup">
          <p>{t.pwa.needsBackup}</p>
          <p>
            <button type="button" onClick={() => void downloadBackup()}>
              {t.pwa.downloadAll}
            </button>{" "}
            <button type="button" onClick={() => pwa().applyUpdate()} disabled={!backup}>
              {t.pwa.updateNow}
            </button>
          </p>
          {backup && (
            <p>
              {t.pwa.backupDone}
              {backup.skipped.length > 0 && ` ${t.pwa.backupSkipped}${backup.skipped.join(", ")}`}
            </p>
          )}
        </div>
      )}
      {offline.phase === "offline-ready" && offline.justReady && !readyDismissed && (
        <p className="status-banner" role="status" data-state="offline-ready">
          {t.pwa.offlineReady}{" "}
          <button type="button" onClick={() => setReadyDismissed(true)}>
            {t.status.dismiss}
          </button>
        </p>
      )}
      {error && (
        <p className="status-banner" role="alert" data-state="error">
          {t.status.calcError(renderMsg(t, error))}
          {resolution && ` ${t.status.lastGood}`}{" "}
          <button type="button" onClick={retry}>
            {t.common.retry}
          </button>
        </p>
      )}
      {notices.length > 0 && (
        <p className="status-banner" role="status" data-state="notice">
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
        <p className="status-banner" role="status" data-state="storage-failed">
          {t.status.storageFailed}
        </p>
      )}
      {serverIsOlder(health, DRAFT_VERSION) && (
        <p className="status-banner" role="status" data-state="server-older">
          {t.status.serverOlder}
        </p>
      )}
      {prunedCount > 0 && (
        <p className="status-banner" role="status" data-state="pruned">
          {t.status.pruned(prunedCount)} <NavLink to="/home">{t.status.seeInHome}</NavLink>
        </p>
      )}
    </>
  );
}
