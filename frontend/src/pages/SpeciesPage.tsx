import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function SpeciesPage() {
  const { resolution, loading, error } = useResolutionContext();
  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;
  const choices = resolution.choices.filter((c) => c.source.kind === "species");
  return (
    <div className="page">
      <h1>Species {loading && "…"}</h1>
      {choices.length === 0 && <p>Няма избори за species все още.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={() => {}} />
      ))}
    </div>
  );
}
