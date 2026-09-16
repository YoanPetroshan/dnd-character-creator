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
