import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../../api/transport";
import { useEngineStatus } from "../../api/useEngineStatus";
import { useDraft } from "../../DraftContext";
import { httpErrorMessage } from "../../httpErrors";
import { useLang, useT } from "../../LanguageContext";
import { exportReadiness } from "../../logic/exportReadiness";
import { safeFilename, shareOrDownload } from "../../logic/files";
import { withLang } from "../../logic/langQuery";
import { MsgError, msg, renderMsg, toMsg, type Msg } from "../../logic/messages";
import { stepForChoice } from "../../logic/steps";
import type { Resolution } from "../../types";

// Only two downloads are offered in the UI: the fillable character sheet first, then Markdown. The server still answers
// /api/export/yaml and /api/export/pdf (docs/API.md), they just have no button.
const EXPORTS = {
  sheet: { endpoint: "/api/export/sheet", extension: "pdf" },
  markdown: { endpoint: "/api/export/markdown", extension: "md" },
} as const;
type ExportKind = keyof typeof EXPORTS;
const ORDER: ExportKind[] = ["sheet", "markdown"];
const BUTTON_CLASS: Record<ExportKind, string> = { sheet: "export-bar__button export-bar__button--primary", markdown: "export-bar__button" };

/** The export actions at the top of the sheet page: two buttons, the reasons when the draft is not ready (the buttons stay, disabled),
 *  the download itself (same request, file name, share / download and offline handling as the old Export page). */
export function ExportBar({ resolution, error }: { resolution: Resolution; error: unknown }) {
  const t = useT();
  const xp = t.exportPage;
  const { lang } = useLang();
  const { draft } = useDraft();
  const engine = useEngineStatus();
  const [exportError, setExportError] = useState<Msg | null>(null);
  const [busy, setBusy] = useState<ExportKind | null>(null);
  const { missingParts, pendingChoices, pendingEquipment, canExport } = exportReadiness(resolution, error);
  const problems = resolution.problems;
  const reasons = missingParts.length + pendingChoices.length + problems.length > 0 || !canExport;

  async function download(kind: ExportKind) {
    const config = EXPORTS[kind];
    setBusy(kind);
    setExportError(null);
    try {
      const resp = await apiFetch(withLang(config.endpoint, lang), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      if (!resp.ok) {
        let body: { problems?: { message: string }[]; error?: string } = {};
        try {
          body = await resp.json();
        } catch {
          // non-JSON error body
        }
        const problemText = body.problems?.map((p) => p.message).join("; ");
        if (problemText) throw new MsgError(msg("export.refused", { text: problemText }));
        throw new MsgError(msg("export.failed", { detail: httpErrorMessage(resp.status, body.error ?? "") }));
      }
      const blob = await resp.blob();
      await shareOrDownload(blob, safeFilename(draft.name, config.extension, xp.fileFallback));
    } catch (err) {
      setExportError(err instanceof TypeError ? msg("export.offline") : toMsg(err));
    } finally {
      setBusy(null);
    }
  }

  const label: Record<ExportKind, string> = { sheet: xp.downloadSheet, markdown: xp.downloadMarkdown };
  return (
    <section className="export-bar" data-section="export" aria-labelledby="export-heading">
      <h2 id="export-heading">{xp.heading}</h2>
      <div className="export-bar__buttons">
        {ORDER.map((kind) => (
          <button
            key={kind}
            type="button"
            className={BUTTON_CLASS[kind]}
            data-export={kind}
            disabled={!canExport || busy !== null}
            aria-describedby={canExport ? undefined : "export-reasons"}
            data-state={busy === kind ? "busy" : !canExport || busy !== null ? "disabled" : "ready"}
            onClick={() => download(kind)}
          >
            {busy === kind ? xp.downloading : label[kind]}
          </button>
        ))}
      </div>
      {engine.pdf === "loading" && (
        <p role="status" data-state="preparing-pdf">
          {xp.preparingPdf}
        </p>
      )}
      {exportError && (
        <p role="alert" className="status--error" data-state="error">
          {renderMsg(t, exportError)}
        </p>
      )}
      {reasons && (
        <div id="export-reasons" className="export-bar__reasons" data-state="not-ready">
          <p role="status">{xp.notReady}</p>
          {problems.length > 0 && (
            <div>
              <h3>{xp.problems}</h3>
              <ul>
                {problems.map((p) => (
                  <li key={p.id}>{p.message}</li>
                ))}
              </ul>
            </div>
          )}
          {missingParts.length > 0 && (
            <ul role="alert">
              {missingParts.map((m) => (
                <li key={m}>{xp.missing[m]}</li>
              ))}
            </ul>
          )}
          {pendingChoices.length > 0 && (
            <div>
              <h3>{xp.unresolved}</h3>
              <ul>
                {pendingChoices.map((c) => (
                  <li key={c.id}>
                    <Link to={{ pathname: stepForChoice(c.id), hash: c.id }}>{c.label}</Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      {pendingEquipment.length > 0 && <p>{xp.pendingEquipment(pendingEquipment.length)}</p>}
      {canExport && <p>{xp.ready}</p>}
    </section>
  );
}
