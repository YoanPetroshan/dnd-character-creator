import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { speciesChoicesOf } from "../logic/choiceRouting";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { FeatureEyeList, grantedFeatures } from "../components/FeatureEyeList";
import { SheetEyesProvider } from "../components/sheet/SheetEyes";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";
import { SpeciesDetailBody, useSpeciesDetails } from "../components/SpeciesDetailBody";
import { BookPicker } from "../components/BookPicker";

export function SpeciesPage() {
  const t = useT();
  const sp = t.speciesPage;
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();
  const { details, loadDetail } = useSpeciesDetails();
  const [openSpecies, setOpenSpecies] = useState<Set<string>>(new Set());

  function toggleSpecies(id: string) {
    const next = new Set(openSpecies);
    if (next.has(id)) next.delete(id);
    else {
      next.add(id);
      loadDetail(id);
    }
    setOpenSpecies(next);
  }

  const selectedSpeciesId = draft.species.id;
  // A selected species/subspecies the current ruleset/sources hide stays
  // listed (from the unfiltered catalog) so the player sees what is picked.
  const selectedSpecies =
    catalog.species.find((s) => s.id === selectedSpeciesId) ?? catalog.allSpecies.find((s) => s.id === selectedSpeciesId);
  const speciesHidden = !!selectedSpecies && !catalog.species.some((s) => s.id === selectedSpecies.id);
  const speciesList = speciesHidden && selectedSpecies ? [selectedSpecies, ...catalog.species] : catalog.species;
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
    <SheetEyesProvider>
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
      <BookPicker
        name="species"
        items={speciesList}
        sources={catalog.sources}
        selected={selectedSpecies}
        selectedHidden={speciesHidden}
        onPick={(id) => dispatch({ type: "SET_SPECIES", speciesId: id })}
        labels={{
          search: sp.searchLabel,
          searchPlaceholder: sp.searchPlaceholder,
          noMatches: t.common.noMatches,
          noSourceGroup: sp.noSourceGroup,
          groupSummary: sp.groupSummary,
          change: sp.change,
          changeLabel: sp.changeLabel,
          cancel: sp.cancel,
          hidden: t.common.hiddenByFilters,
        }}
        pickedExtra={(s) => ({
          button: (
            <button
              type="button"
              className="species-eye"
              aria-label={sp.showSpecies(s.name)}
              aria-expanded={openSpecies.has(s.id)}
              onClick={() => toggleSpecies(s.id)}
            />
          ),
          panel: openSpecies.has(s.id) && (
            <div className="species-eye__panel">
              <SpeciesDetailBody state={details[s.id]} />
            </div>
          ),
        })}
      />
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
      {selectedSpeciesId && grantedFeatures(resolution?.sheet, "species").length > 0 && (
        <div className="granted-features">
          <h2>{sp.traits}</h2>
          <FeatureEyeList idPrefix="species" features={grantedFeatures(resolution?.sheet, "species")} />
        </div>
      )}
      {selectedSpeciesId && !loading && choices.length === 0 && <p>{sp.noChoices}</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(choices)} />
      ))}
    </div>
    </SheetEyesProvider>
  );
}
