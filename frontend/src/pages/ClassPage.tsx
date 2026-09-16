import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function ClassPage() {
  const { resolution, loading, error, retry } = useResolutionContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  const classChoices = resolution.choices.filter((c) => c.source.kind === "class");

  function handleChange(choiceId: string, selected: string[]) {
    // Phase 0: this is intentionally not wired back into the Draft yet.
    // The stub backend ignores the request body and always returns the
    // same hardcoded choices, so there is nothing for a real selection to
    // affect until Phase 1's engine exists to validate against. Logging
    // here is the deliberate, documented extent of this task's scope —
    // do not add draft-mutation wiring in this task.
    console.log("choice changed", choiceId, selected);
  }

  return (
    <div className="page">
      <h1>Клас {loading && "…"}</h1>
      {classChoices.length === 0 && <p>Няма избори за клас все още.</p>}
      {classChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
