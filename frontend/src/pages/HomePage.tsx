import { useRef, useState } from "react";
import { useDraft } from "../DraftContext";
import { useLibrary } from "../LibraryContext";
import type { ImportEntry } from "../library";
import { useT } from "../LanguageContext";
import { msg, renderMsg, toMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { safeFilename, shareOrDownload } from "../logic/files";
import { sourceOn, toggleSource } from "../logic/sources";
import type { Ruleset } from "../types";
import { formatDateTime } from "../logic/formatDate";

export function HomePage() {
  const t = useT();
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();
  const fileInput = useRef<HTMLInputElement>(null);
  // after a bundle download: null (nothing yet) or the names of the characters left out
  const [exportNote, setExportNote] = useState<{ skipped: string[] } | null>(null);

  const library = useLibrary();
  const [importReport, setImportReport] = useState<ImportEntry[] | null>(null);

  async function downloadDraft() {
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    await shareOrDownload(blob, safeFilename(draft.name, "draft.json"), "application/json");
  }

  async function exportAll() {
    const { json, skipped } = library.exportAll();
    await shareOrDownload(new Blob([json], { type: "application/json" }), safeFilename("dnd-heroes", "json"), "application/json");
    setExportNote({ skipped });
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
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

  const allSourceIds = catalog.sources.map((src) => src.id);
  const sourceOnFor = (id: string) => sourceOn(draft.sources, id);
  function toggle(id: string, on: boolean) {
    dispatch({ type: "SET_SOURCES", sources: toggleSource(draft.sources, allSourceIds, id, on) });
  }
  return (
    <div className="page">
      <h1>{t.home.title}</h1>
      <label>
        {t.home.nameLabel}
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>{t.home.nameHint}</p>

      <h2>{t.home.charactersTitle}</h2>
      <ul>
        {library.items.map((item) => {
          const active = item.id === library.activeId;
          const name = active ? draft.name : item.name;
          return (
            <li key={item.id} data-active={active ? "true" : undefined}>
              <strong>{name || t.home.unnamed}</strong>
              {active && ` ${t.home.active}`}
              {item.status === "corrupt" && ` — ${t.home.corrupt}`}
              {item.status === "empty" && ` — ${t.home.noStoredDraft}`}
              {item.status === "ok" &&
                ` — ${t.home.itemSummary(item.classes.length ? item.classes.map((c) => `${className(c.classId)} ${c.level}`).join(", ") : t.home.noClass, item.totalLevel)}`}
              {" — "}
              <time dateTime={new Date(item.updatedAt).toISOString()}>
                {t.home.updated(formatDateTime(item.updatedAt, t.common.dateLocale))}
              </time>{" "}
              {!active && (
                <button type="button" onClick={() => library.openCharacter(item.id)}>
                  {t.home.open}
                </button>
              )}{" "}
              <button type="button" onClick={() => renameItem(item.id, name)}>
                {t.home.rename}
              </button>{" "}
              <button type="button" onClick={() => library.duplicateCharacter(item.id)}>
                {t.home.duplicate}
              </button>{" "}
              <button type="button" onClick={() => deleteItem(item.id, name)}>
                {t.home.delete}
              </button>
            </li>
          );
        })}
      </ul>
      <div>
        <button type="button" onClick={() => library.newCharacter()}>
          {t.home.newHero}
        </button>{" "}
        <button type="button" onClick={exportAll}>
          {t.home.downloadAll}
        </button>{" "}
        <button type="button" onClick={() => fileInput.current?.click()}>
          {t.home.upload}
        </button>{" "}
        <button type="button" onClick={downloadDraft}>
          {t.home.downloadOne}
        </button>
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

      <h2>{t.home.rulesTitle}</h2>
      <label>
        {t.home.rulesetLabel}
        <select value={draft.ruleset} onChange={(e) => dispatch({ type: "SET_RULESET", ruleset: e.target.value as Ruleset })}>
          <option value="2014">2014</option>
          <option value="2024">2024</option>
          <option value="mixed">{t.home.rulesetMixed}</option>
        </select>
      </label>
      <p>{t.home.rulesetHelp[draft.ruleset] ?? t.home.rulesetHelp.mixed}</p>
      <details className="details-section">
        <summary>
          {t.home.sourcesSummary(draft.sources.length === 0 ? null : draft.sources.filter((x) => x.toLowerCase() !== "srd").length)}
        </summary>
        <div>
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: [] })}>
            {t.home.sourcesAll}
          </button>{" "}
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: ["srd"] })}>
            {t.home.sourcesSrdOnly}
          </button>
        </div>
        {catalog.sources.map((src) => (
          <label key={src.id}>
            <input type="checkbox" checked={sourceOnFor(src.id)} onChange={(e) => toggle(src.id, e.target.checked)} />
            {src.name} ({src.count})
          </label>
        ))}
      </details>

      <h2>{t.home.preferencesTitle}</h2>
      <fieldset>
        <legend>{t.home.hpPerLevel}</legend>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "fixed"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "fixed" })}
          />
          {t.home.hpFixed}
        </label>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "manual"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "manual" })}
          />
          {t.home.hpManual}
        </label>
      </fieldset>

      <fieldset>
        <legend>{t.home.prerequisites}</legend>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.feats}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "feats", value: e.target.checked })}
          />
          {t.home.prereqFeats}
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.multiclass}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "multiclass", value: e.target.checked })}
          />
          {t.home.prereqMulticlass}
        </label>
      </fieldset>

      <h2>{t.home.resolutionTitle}</h2>
      {loading && <p>{t.common.loading}</p>}
      {resolution && (
        <ul>
          {resolution.warnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
      {resolution && resolution.pruned.length > 0 && (
        <>
          <h3>{t.home.prunedTitle}</h3>
          <ul>
            {resolution.pruned.map((p, i) => (
              <li key={`${i}-${p.choiceId}`} data-state="pruned">{p.reason}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() =>
              dispatch({
                type: "CLEAR_STALE_SELECTIONS",
                keepIds: resolution.choices.map((c) => c.id),
                // "class:<id>:subclass" = a subclass kept below its unlock level
                clearSubclassFor: resolution.pruned
                  .map((p) => /^class:(.+):subclass$/.exec(p.choiceId)?.[1])
                  .filter((id): id is string => !!id),
              })
            }
          >
            {t.home.clearPruned}
          </button>
        </>
      )}
    </div>
  );
}
