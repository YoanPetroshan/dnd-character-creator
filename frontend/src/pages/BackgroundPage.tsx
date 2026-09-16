import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function BackgroundPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedBackgroundId = draft.background.id;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "background", choiceId, selected });
  }

  const choices = resolution ? resolution.choices.filter((c) => c.source.kind === "background") : [];

  return (
    <div className="page">
      <h1>Background {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <select
        value={selectedBackgroundId ?? ""}
        onChange={(e) => {
          if (e.target.value) dispatch({ type: "SET_BACKGROUND", backgroundId: e.target.value });
        }}
      >
        <option value="">— избери background —</option>
        {catalog.backgrounds.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
      </select>
      {selectedBackgroundId && !loading && choices.length === 0 && <p>Няма избори за този background.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
