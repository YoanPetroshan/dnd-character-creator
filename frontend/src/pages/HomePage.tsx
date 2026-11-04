import { useRef, useState } from "react";
import { useDraft } from "../DraftContext";
import { useLibrary } from "../LibraryContext";
import type { ImportEntry } from "../library";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { safeFilename, shareOrDownload } from "../logic/files";
import { sourceOn, toggleSource } from "../logic/sources";
import type { Ruleset } from "../types";

const RULESET_HELP: Record<Ruleset, string> = {
  "2014": "2014: увеличенията на характеристики идват от вида (species); увеличенията на произхода (background) се игнорират. Съдържанието от 2024 е скрито.",
  "2024": "2024: увеличенията идват от произхода (background); тези на вида се игнорират. Скрити са само стари (2014) произходи.",
  mixed: "Смесени: всичко е достъпно. Ако произходът дава собствено увеличение, това на вида не се прилага (без двойно броене).",
};

export function HomePage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();
  const fileInput = useRef<HTMLInputElement>(null);
  const [draftMessage, setDraftMessage] = useState<string | null>(null);

  const library = useLibrary();
  const [importReport, setImportReport] = useState<ImportEntry[] | null>(null);

  async function downloadDraft() {
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    await shareOrDownload(blob, safeFilename(draft.name, "draft.json"), "application/json");
  }

  async function exportAll() {
    const { json, skipped } = library.exportAll();
    await shareOrDownload(new Blob([json], { type: "application/json" }), safeFilename("dnd-heroes", "json"), "application/json");
    setDraftMessage(
      skipped.length ? `Пакетът е изтеглен без повредени герои: ${skipped.join(", ")}.` : "Пакетът с всички герои е изтеглен.",
    );
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
    try {
      setImportReport(library.importParsed(JSON.parse(await file.text())));
    } catch (e) {
      const message = e instanceof SyntaxError ? "Файлът не е валиден JSON." : e instanceof Error ? e.message : String(e);
      setImportReport([{ index: 0, name: "", status: "rejected", message }]);
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function renameItem(id: string, current: string) {
    const name = window.prompt("Ново име на героя:", current);
    if (name === null) return;
    if (id === library.activeId) dispatch({ type: "SET_NAME", name });
    else library.renameCharacter(id, name);
  }

  function deleteItem(id: string, name: string) {
    if (window.confirm(`Изтриване на героя „${name || "Без име"}“? Това не може да се отмени.`)) library.deleteCharacter(id);
  }

  const className = (classId: string) => catalog.classes.find((c) => c.id === classId)?.name ?? classId;

  const allSourceIds = catalog.sources.map((src) => src.id);
  const sourceOnFor = (id: string) => sourceOn(draft.sources, id);
  function toggle(id: string, on: boolean) {
    dispatch({ type: "SET_SOURCES", sources: toggleSource(draft.sources, allSourceIds, id, on) });
  }
  return (
    <div className="page">
      <h1>Home</h1>
      <label>
        Character Name
        <input
          type="text"
          value={draft.name}
          onChange={(e) => dispatch({ type: "SET_NAME", name: e.target.value })}
        />
      </label>
      <p>Saved as you type — reload the page and this name should still be here.</p>

      <h2>Герои</h2>
      <ul>
        {library.items.map((item) => {
          const active = item.id === library.activeId;
          const name = active ? draft.name : item.name;
          return (
            <li key={item.id} data-active={active ? "true" : undefined}>
              <strong>{name || "Без име"}</strong>
              {active && " (активен)"}
              {item.status === "corrupt" && " — повредена чернова"}
              {item.status === "empty" && " — няма запазена чернова"}
              {item.status === "ok" &&
                ` — ${item.classes.length ? item.classes.map((c) => `${className(c.classId)} ${c.level}`).join(", ") : "без клас"}, общо ниво ${item.totalLevel}`}
              {" — "}
              <time dateTime={new Date(item.updatedAt).toISOString()}>променен {new Date(item.updatedAt).toLocaleString("bg-BG")}</time>{" "}
              {!active && (
                <button type="button" onClick={() => library.openCharacter(item.id)}>
                  Отвори
                </button>
              )}{" "}
              <button type="button" onClick={() => renameItem(item.id, name)}>
                Преименувай
              </button>{" "}
              <button type="button" onClick={() => library.duplicateCharacter(item.id)}>
                Копирай
              </button>{" "}
              <button type="button" onClick={() => deleteItem(item.id, name)}>
                Изтрий
              </button>
            </li>
          );
        })}
      </ul>
      <div>
        <button type="button" onClick={() => library.newCharacter()}>
          Нов герой
        </button>{" "}
        <button type="button" onClick={exportAll}>
          Изтегли всички (.json)
        </button>{" "}
        <button type="button" onClick={() => fileInput.current?.click()}>
          Качи герой или пакет (.json)
        </button>{" "}
        <button type="button" onClick={downloadDraft}>
          Изтегли този герой (.json)
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          hidden
          onChange={(e) => importFile(e.target.files?.[0])}
        />
        {draftMessage && <p role="status">{draftMessage}</p>}
        {importReport && (
          <div role="status">
            <p>
              Качване: {importReport.filter((e) => e.status === "accepted").length} добавени, {importReport.filter((e) => e.status === "rejected").length} отхвърлени. Съществуващите герои не са променени.
            </p>
            <ul>
              {importReport.map((e) => (
                <li key={e.index} data-status={e.status}>
                  {e.name || `№ ${e.index + 1}`}: {e.status === "accepted" ? "добавен" : "отхвърлен"} — {e.message}
                </li>
              ))}
            </ul>
            <button type="button" onClick={() => setImportReport(null)}>
              Скрий
            </button>
          </div>
        )}
      </div>

      <h2>Правила и източници</h2>
      <label>
        Правила (ruleset)
        <select value={draft.ruleset} onChange={(e) => dispatch({ type: "SET_RULESET", ruleset: e.target.value as Ruleset })}>
          <option value="2014">2014</option>
          <option value="2024">2024</option>
          <option value="mixed">Смесени</option>
        </select>
      </label>
      <p>{RULESET_HELP[draft.ruleset] ?? RULESET_HELP.mixed}</p>
      <details className="details-section">
        <summary>
          Източници (Sources){" "}
          {draft.sources.length === 0 ? "— всички" : `— ${draft.sources.filter((x) => x.toLowerCase() !== "srd").length} избрани`}
        </summary>
        <div>
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: [] })}>
            Всички
          </button>{" "}
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: ["srd"] })}>
            Само SRD
          </button>
        </div>
        {catalog.sources.map((src) => (
          <label key={src.id}>
            <input type="checkbox" checked={sourceOnFor(src.id)} onChange={(e) => toggle(src.id, e.target.checked)} />
            {src.name} ({src.count})
          </label>
        ))}
      </details>

      <h2>Preferences</h2>
      <fieldset>
        <legend>Точки живот на ниво</legend>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "fixed"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "fixed" })}
          />
          Фиксирани (средна стойност)
        </label>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "manual"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "manual" })}
          />
          Хвърляне на зарове (ръчно въвеждане)
        </label>
      </fieldset>

      <fieldset>
        <legend>Изисквания</legend>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.feats}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "feats", value: e.target.checked })}
          />
          Прояви на дарби
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.multiclass}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "multiclass", value: e.target.checked })}
          />
          Смяна на класове
        </label>
      </fieldset>

      <h2>Resolution (from /api/resolve)</h2>
      {loading && <p>Зареждане…</p>}
      {resolution && (
        <ul>
          {resolution.warnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
      {resolution && resolution.pruned.length > 0 && (
        <>
          <h3>Отпаднали избори</h3>
          <ul>
            {resolution.pruned.map((p, i) => (
              <li key={`${i}-${p.choiceId}`}>{p.reason}</li>
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
            Изчисти отпаднали избори
          </button>
        </>
      )}
    </div>
  );
}
