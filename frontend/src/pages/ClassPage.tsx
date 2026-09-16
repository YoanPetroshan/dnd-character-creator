import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function ClassPage() {
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

  const selectedClassId = draft.classes[0]?.classId;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

  const classChoices = resolution ? resolution.choices.filter((c) => c.source.kind === "class") : [];

  return (
    <div className="page">
      <h1>Клас {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане на класовете: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="picker-list">
        {catalog.classes.map((c) => (
          <li key={c.id}>
            <label>
              <input
                type="radio"
                name="class"
                checked={selectedClassId === c.id}
                onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
              />
              {c.name} (d{c.hitDie})
            </label>
          </li>
        ))}
      </ul>
      {selectedClassId && !loading && classChoices.length === 0 && <p>Няма избори за този клас.</p>}
      {classChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
