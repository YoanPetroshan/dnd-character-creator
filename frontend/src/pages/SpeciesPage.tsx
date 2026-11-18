import { Fragment, useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { speciesChoicesOf } from "../logic/choiceRouting";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import type { CatalogSource, CatalogSpecies } from "../useCatalog";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";
import { SpeciesDetailBody, useSpeciesDetails } from "../components/SpeciesDetailBody";

/** The core books come first, in this order; every other source follows as its own group. */
const CORE_SOURCES = ["PHB", "XPHB", "DMG", "XDMG"];

interface SpeciesGroup {
  key: string;
  label: string;
  items: CatalogSpecies[];
}

/** Groups species by source: core books first, then the rest by display name; names keep their order inside. */
function groupBySource(list: CatalogSpecies[], sources: CatalogSource[], noSourceLabel: string): SpeciesGroup[] {
  const nameOf = new Map(sources.map((x) => [x.id, x.name]));
  const byKey = new Map<string, SpeciesGroup>();
  for (const s of list) {
    const key = s.source ?? "";
    let g = byKey.get(key);
    if (!g) {
      g = { key, label: key ? (nameOf.get(key) ?? key) : noSourceLabel, items: [] };
      byKey.set(key, g);
    }
    g.items.push(s);
  }
  const core = CORE_SOURCES.flatMap((k) => byKey.get(k) ?? []);
  const rest = [...byKey.values()]
    .filter((g) => !CORE_SOURCES.includes(g.key))
    .sort((a, b) => a.label.localeCompare(b.label) || a.key.localeCompare(b.key));
  return [...core, ...rest];
}

export function SpeciesPage() {
  const t = useT();
  const sp = t.speciesPage;
  const { draft, dispatch } = useDraft();
  const [speciesFilter, setSpeciesFilter] = useState("");
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
  const needle = speciesFilter.trim().toLowerCase();
  const shownSpecies = needle
    ? speciesList.filter((s) => s.id === selectedSpeciesId || s.name.toLowerCase().includes(needle))
    : speciesList;
  const speciesGroups = groupBySource(shownSpecies, catalog.sources, sp.noSourceGroup);
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
      <ul className="picker-list picker-list--rows">
        {speciesGroups.map((g) => (
          <Fragment key={g.key}>
            <li className="picker-list__group" role="presentation">
              {g.label}
            </li>
            {g.items.map((s) => (
              <li key={s.id} className={openSpecies.has(s.id) ? "picker-list__item--open" : undefined}>
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
                <button
                  type="button"
                  className="species-eye"
                  aria-label={sp.showSpecies(s.name)}
                  aria-expanded={openSpecies.has(s.id)}
                  onClick={() => toggleSpecies(s.id)}
                />
                {s.source && !s.name.endsWith(`(${s.source})`) && <span className="picker-list__source">{s.source}</span>}
                {openSpecies.has(s.id) && (
                  <div className="species-eye__panel">
                    <SpeciesDetailBody state={details[s.id]} />
                  </div>
                )}
              </li>
            ))}
          </Fragment>
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
