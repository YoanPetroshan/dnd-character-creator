import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDraft } from "../DraftContext";
import { useLibrary } from "../LibraryContext";
import { MAX_IMPORT_FILE_MB, type ImportEntry } from "../library";
import { useT } from "../LanguageContext";
import { msg, renderMsg, toMsg } from "../logic/messages";
import { useCatalogContext } from "../CatalogContext";
import { safeFilename, shareOrDownload } from "../logic/files";
import { formatDateTime } from "../logic/formatDate";
import { ClassGlyph } from "../components/ClassGlyph";

function closeMenu(e: { currentTarget: HTMLElement }) {
  (e.currentTarget.closest("details") as HTMLDetailsElement | null)?.removeAttribute("open");
}

/** The hero library (DESIGN-L, decision 3A): only "which hero am I making" and "make a new one". The brand in the header
 *  leads here. Rename, duplicate and delete are in each row's menu; import and export in one closed section. */
export function HeroesPage() {
  const t = useT();
  const navigate = useNavigate();
  const { draft, dispatch } = useDraft();
  const catalog = useCatalogContext();
  const fileInput = useRef<HTMLInputElement>(null);
  // after a bundle download: null (nothing yet) or the names of the characters left out
  const [exportNote, setExportNote] = useState<{ skipped: string[] } | null>(null);

  const library = useLibrary();
  const [importReport, setImportReport] = useState<ImportEntry[] | null>(null);

  async function downloadDraft() {
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    await shareOrDownload(blob, safeFilename(draft.name, "draft.json", t.exportPage.fileFallback), "application/json");
  }

  async function exportAll() {
    const { json, skipped } = library.exportAll();
    await shareOrDownload(new Blob([json], { type: "application/json" }), safeFilename("dnd-heroes", "json"), "application/json");
    setExportNote({ skipped });
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_IMPORT_FILE_MB * 1_000_000) {
      setImportReport([{ index: 0, name: "", status: "rejected", message: msg("file.tooBig", { max: MAX_IMPORT_FILE_MB }) }]);
      if (fileInput.current) fileInput.current.value = "";
      return;
    }
    try {
      setImportReport(library.importParsed(JSON.parse(await file.text())));
    } catch (e) {
      const message = e instanceof SyntaxError ? msg("file.notJson") : toMsg(e);
      setImportReport([{ index: 0, name: "", status: "rejected", message }]);
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function renameItem(id: string, current: string) {
    const name = window.prompt(t.home.renamePrompt, current);
    if (name === null) return;
    if (id === library.activeId) dispatch({ type: "SET_NAME", name });
    else library.renameCharacter(id, name);
  }

  function deleteItem(id: string, name: string) {
    if (window.confirm(t.home.deleteConfirm(name || t.home.unnamed))) library.deleteCharacter(id);
  }

  const className = (classId: string) => catalog.classes.find((c) => c.id === classId)?.name ?? classId;

  return (
    <div className="page" data-page="heroes">
      <h1>{t.home.charactersTitle}</h1>
      <ul className="hero-list">
        {library.items.map((item) => {
          const active = item.id === library.activeId;
          const name = active ? draft.name : item.name;
          return (
            <li key={item.id} className="hero" data-active={active ? "true" : undefined}>
              {library.portraits[item.id] ? (
                <img className="hero__portrait" src={library.portraits[item.id]} alt="" />
              ) : (
                <ClassGlyph classId={item.status === "ok" ? item.classes[0]?.classId : undefined} solid={active} />
              )}
              <div className="hero__text">
                <strong className="hero__name">{name || t.home.unnamed}</strong>
                {active && <span className="hero__tag">{t.home.active}</span>}
                <span className="hero__meta">
                  {item.status === "corrupt" && t.home.corrupt}
                  {item.status === "empty" && t.home.noStoredDraft}
                  {item.status === "ok" &&
                    t.home.itemSummary(item.classes.length ? item.classes.map((c) => `${className(c.classId)} ${c.level}`).join(", ") : t.home.noClass, item.totalLevel)}
                </span>
                {/* a missing or zero time (an old import) is not shown as 1 January 1970 */}
                {item.updatedAt > 946684800000 && (
                  <time className="hero__meta" dateTime={new Date(item.updatedAt).toISOString()}>
                    {t.home.updated(formatDateTime(item.updatedAt, t.common.dateLocale))}
                  </time>
                )}
              </div>
              <div className="hero__actions">
                {!active && (
                  <button type="button" className="hero__open" onClick={() => {
                    library.openCharacter(item.id);
                    navigate("/home");
                  }}>
                    {t.home.open}
                  </button>
                )}
                <details className="hero__menu">
                  <summary className="hero__menu-toggle" aria-label={t.home.moreActions}>
                    <span className="hero__menu-dot" aria-hidden="true" />
                    <span className="hero__menu-dot" aria-hidden="true" />
                    <span className="hero__menu-dot" aria-hidden="true" />
                  </summary>
                  <div className="hero__menu-list">
                    {!active && (
                      <button
                        type="button"
                        onClick={(e) => {
                          closeMenu(e);
                          library.openCharacter(item.id);
                        }}
                      >
                        {t.home.open}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        closeMenu(e);
                        renameItem(item.id, name);
                      }}
                    >
                      {t.home.rename}
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        closeMenu(e);
                        library.duplicateCharacter(item.id);
                      }}
                    >
                      {t.home.duplicate}
                    </button>
                    <button
                      type="button"
                      className="hero__menu-danger"
                      onClick={(e) => {
                        closeMenu(e);
                        deleteItem(item.id, name);
                      }}
                    >
                      {t.home.delete}
                    </button>
                  </div>
                </details>
              </div>
            </li>
          );
        })}
      </ul>
      <div className="library-actions">
        <button type="button" className="library-actions__new" onClick={() => {
          library.newCharacter();
          navigate("/home");
        }}>
          {t.home.newHero}
        </button>
        {/* import and export are rare: one closed section instead of three more buttons (DESIGN-L) */}
        <details className="details-section">
          <summary>{t.home.filesTitle}</summary>
          <div className="library-actions__files">
            <button type="button" onClick={exportAll}>
              {t.home.downloadAll}
            </button>
            <button type="button" onClick={() => fileInput.current?.click()}>
              {t.home.upload}
            </button>
            <button type="button" onClick={downloadDraft}>
              {t.home.downloadOne}
            </button>
          </div>
        </details>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          hidden
          onChange={(e) => importFile(e.target.files?.[0])}
        />
        {exportNote && (
          <p role="status">
            {exportNote.skipped.length
              ? t.home.exportedSkipped(exportNote.skipped.map((n) => n || t.home.unnamed).join(", "))
              : t.home.exportedAll}
          </p>
        )}
        {importReport && (
          <div role="status">
            <p>
              {t.home.importSummary(
                importReport.filter((e) => e.status === "accepted").length,
                importReport.filter((e) => e.status === "rejected").length,
              )}
            </p>
            <ul>
              {importReport.map((e) => (
                <li key={e.index} data-status={e.status}>
                  {e.name || t.home.importIndex(e.index + 1)}: {e.status === "accepted" ? t.home.importAccepted : t.home.importRejected} — {renderMsg(t, e.message)}
                </li>
              ))}
            </ul>
            <button type="button" onClick={() => setImportReport(null)}>
              {t.home.hide}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
