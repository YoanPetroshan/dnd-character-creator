import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { speciesChoicesOf } from "../logic/choiceRouting";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";

export function SpeciesPage() {
  const t = useT();
  const sp = t.speciesPage;
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
    ? speciesChoicesOf(resolution.choices)
    : [];

  return (
    <div className="page">
      <h1>{sp.title} {loading && "…"}</h1>
      <StepProblems step="species" />
      {catalog.error && (
        <p>
          {t.common.loadError(renderMsg(t, catalog.error))}{" "}
          <button type="button" onClick={catalog.retry}>
            {t.common.retry}
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
        aria-label={sp.searchLabel}
        placeholder={sp.searchPlaceholder}
        value={speciesFilter}
        onChange={(e) => setSpeciesFilter(e.target.value)}
      />
      {needle && shownSpecies.length === 0 && <p>{t.common.noMatches}</p>}
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
              {speciesHidden && s.id === selectedSpeciesId ? ` (${t.common.hiddenByFilters})` : ""}
            </label>
          </li>
        ))}
      </ul>
      {selectedSpecies && subspeciesList.length > 0 && (
        <>
          <h2>{sp.subspecies}</h2>
          <select
            aria-label={sp.subspecies}
            value={draft.species.subspeciesId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBSPECIES", subspeciesId: e.target.value || undefined })}
          >
            <option value="">{sp.subspeciesNone}</option>
            {subspeciesList.map((sub) => (
              <option key={sub.id} value={sub.id}>
                {sub.name}
              </option>
            ))}
          </select>
        </>
      )}
      {selectedSpeciesId && !loading && choices.length === 0 && <p>{sp.noChoices}</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(choices)} />
      ))}
    </div>
  );
}
