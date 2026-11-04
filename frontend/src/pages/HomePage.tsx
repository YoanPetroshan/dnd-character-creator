import { useRef, useState } from "react";
import { mergeDraft, useDraft } from "../DraftContext";
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

  const resetDraft = () => {
    if (window.confirm("Нулиране на черновата? Текущият герой ще бъде изтрит.")) {
      dispatch({ type: "RESET" });
      setDraftMessage(null);
    }
  };

  async function downloadDraft() {
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" });
    await shareOrDownload(blob, safeFilename(draft.name, "draft.json"), "application/json");
  }

  async function uploadDraft(file: File | undefined) {
    if (!file) return;
    try {
      const imported = mergeDraft(JSON.parse(await file.text()));
      if (draft.classes.length > 0 || draft.name) {
        if (!window.confirm("Качването ще замени текущата чернова. Продължаване?")) return;
      }
      dispatch({ type: "SET_DRAFT", draft: imported });
      setDraftMessage("Черновата е качена.");
    } catch (e) {
      setDraftMessage(
        (e instanceof SyntaxError ? "Файлът не е валиден JSON." : e instanceof Error ? e.message : String(e)) +
          " Текущата чернова не е променена.",
      );
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }

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

      <div>
        <button type="button" onClick={resetDraft}>
          Нов герой
        </button>{" "}
        <button type="button" onClick={downloadDraft}>
          Изтегли чернова (.json)
        </button>{" "}
        <button type="button" onClick={() => fileInput.current?.click()}>
          Качи чернова (.json)
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".json,application/json"
          hidden
          onChange={(e) => uploadDraft(e.target.files?.[0])}
        />
        {draftMessage && <p role="status">{draftMessage}</p>}
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
