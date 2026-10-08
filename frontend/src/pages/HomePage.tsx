import { useRef, useState } from "react";
import { mergeDraft, useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function HomePage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
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
    const filename = `${(draft.name || "character").replace(/[\\/:*?"<>|]/g, "_")}.draft.json`;
    if (typeof File !== "undefined" && navigator.canShare && window.matchMedia("(pointer: coarse)").matches) {
      const file = new File([blob], filename, { type: "application/json" });
      if (navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ files: [file] });
          return;
        } catch (e) {
          if (e instanceof DOMException && e.name === "AbortError") return;
        }
      }
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
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
      setDraftMessage(e instanceof SyntaxError ? "Файлът не е валиден JSON." : e instanceof Error ? e.message : String(e));
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
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
        <legend>Тип напредък</legend>
        <label>
          <input
            type="radio"
            name="advancementType"
            checked={draft.preferences.advancementType === "milestone"}
            onChange={() => dispatch({ type: "SET_ADVANCEMENT_TYPE", advancementType: "milestone" })}
          />
          Ключови моменти
        </label>
        <label>
          <input
            type="radio"
            name="advancementType"
            checked={draft.preferences.advancementType === "xp"}
            onChange={() => dispatch({ type: "SET_ADVANCEMENT_TYPE", advancementType: "xp" })}
          />
          Опит (XP)
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
      {error && (
        <p style={{ color: "red" }}>
          Грешка: {error}{" "}
          <button type="button" onClick={retry}>
            Опитай пак
          </button>{" "}
          <button type="button" onClick={resetDraft}>
            Нулирай чернова
          </button>
        </p>
      )}
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
            {resolution.pruned.map((p) => (
              <li key={p.choiceId}>{p.reason}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
