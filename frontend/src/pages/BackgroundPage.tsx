import { useResolutionContext } from "../ResolutionContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function BackgroundPage() {
  const { resolution, loading, error } = useResolutionContext();
  if (error) return <div className="page">Грешка: {error}</div>;
  if (!resolution) return <div className="page">Зареждане…</div>;
  const choices = resolution.choices.filter((c) => c.source.kind === "background");
  return (
    <div className="page">
      <h1>Background {loading && "…"}</h1>
      {choices.length === 0 && <p>Няма избори за background все още.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={() => {}} />
      ))}
    </div>
  );
}
