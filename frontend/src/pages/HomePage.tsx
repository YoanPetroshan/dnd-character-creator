import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";

export function HomePage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
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
    </div>
  );
}
