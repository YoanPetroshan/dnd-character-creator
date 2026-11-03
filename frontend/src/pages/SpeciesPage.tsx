import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";

export function SpeciesPage() {
  const { draft, dispatch } = useDraft();
  const [speciesFilter, setSpeciesFilter] = useState("");
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();


  const selectedSpeciesId = draft.species.id;
  // A selected species/subspecies the current ruleset/sources hide stays
  // listed (from the unfiltered catalog) so the player sees what is picked.
  const selectedSpecies =
    catalog.species.find((s) => s.id === selectedSpeciesId) ?? catalog.allSpecies.find((s) => s.id === selectedSpeciesId);
  const speciesHidden = !!selectedSpecies && !catalog.species.some((s) => s.id === selectedSpecies.id);
  const speciesList = speciesHidden && selectedSpecies ? [selectedSpecies, ...catalog.species] : catalog.species;
  const needle = speciesFilter.trim().toLowerCase();
  const shownSpecies = needle
    ? speciesList.filter((s) => s.id === selectedSpeciesId || s.name.toLowerCase().includes(needle))
    : speciesList;
  const fullSpecies = catalog.allSpecies.find((s) => s.id === selectedSpeciesId);
  const subspeciesList = selectedSpecies
    ? [
        ...selectedSpecies.subspecies,
        ...(fullSpecies?.subspecies ?? []).filter(
          (sub) => sub.id === draft.species.subspeciesId && !selectedSpecies.subspecies.some((x) => x.id === sub.id),
        ),
      ]
    : [];
  const rulesetWarnings = resolution
    ? resolution.warnings.filter((w) => w.id.startsWith("ruleset-") || w.id.startsWith("source-hidden") || w.id.startsWith("asi-double-dip"))
    : [];

  function handleChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "species", choiceId, optionId, count });
  }

  // A species-granted feat (Human/XPHB's Origin feat, Variant Human) is a
  // "species:" choice, and its cascaded choices (proficiencies, spells, ...)
  // have source.kind "feat" but a "species:" cid, so they show here too.
  const choices = resolution
    ? resolution.choices.filter((c) => c.source.kind === "species" || (c.source.kind === "feat" && c.id.startsWith("species:")))
    : [];

  return (
    <div className="page">
      <h1>Species {loading && "…"}</h1>
      <StepProblems step="species" />
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      {rulesetWarnings.length > 0 && (
        <ul role="status">
          {rulesetWarnings.map((w) => (
            <li key={w.id}>{w.message}</li>
          ))}
        </ul>
      )}
      <input
        type="search"
        className="picker-filter"
        aria-label="Търсене на species"
        placeholder="Търсене на species…"
        value={speciesFilter}
        onChange={(e) => setSpeciesFilter(e.target.value)}
      />
      {needle && shownSpecies.length === 0 && <p>Няма съвпадения.</p>}
      <ul className="picker-list">
        {shownSpecies.map((s) => (
          <li key={s.id}>
            <label>
              <input
                type="radio"
                name="species"
                checked={selectedSpeciesId === s.id}
                onChange={() => dispatch({ type: "SET_SPECIES", speciesId: s.id })}
              />
              {s.name}
              {speciesHidden && s.id === selectedSpeciesId ? " (скрит от текущите филтри)" : ""}
            </label>
          </li>
        ))}
      </ul>
      {selectedSpecies && subspeciesList.length > 0 && (
        <>
          <h2>Subspecies</h2>
          <select
            aria-label="Subspecies"
            value={draft.species.subspeciesId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBSPECIES", subspeciesId: e.target.value || undefined })}
          >
            <option value="">— none —</option>
            {subspeciesList.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.name}
              </option>
            ))}
          </select>
        </>
      )}
      {selectedSpeciesId && !loading && choices.length === 0 && <p>Няма избори за този species.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(choices)} />
      ))}
    </div>
  );
}
