import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard } from "../components/ChoiceCard";

export function SpeciesPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalogContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedSpeciesId = draft.species.id;
  const selectedSpecies = catalog.species.find((s) => s.id === selectedSpeciesId);

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "species", choiceId, selected });
  }

  const choices = resolution ? resolution.choices.filter((c) => c.source.kind === "species") : [];

  return (
    <div className="page">
      <h1>Species {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="picker-list">
        {catalog.species.map((s) => (
          <li key={s.id}>
            <label>
              <input
                type="radio"
                name="species"
                checked={selectedSpeciesId === s.id}
                onChange={() => dispatch({ type: "SET_SPECIES", speciesId: s.id })}
              />
              {s.name}
            </label>
          </li>
        ))}
      </ul>
      {selectedSpecies && selectedSpecies.subspecies.length > 0 && (
        <>
          <h2>Subspecies</h2>
          <select
            value={draft.species.subspeciesId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBSPECIES", subspeciesId: e.target.value || undefined })}
          >
            <option value="">— none —</option>
            {selectedSpecies.subspecies.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.name}
              </option>
            ))}
          </select>
        </>
      )}
      {selectedSpeciesId && !loading && choices.length === 0 && <p>Няма избори за този species.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}
    </div>
  );
}
