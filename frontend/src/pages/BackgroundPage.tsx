import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { backgroundChoicesOf } from "../logic/choiceRouting";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";

export function BackgroundPage() {
  const t = useT();
  const bp = t.backgroundPage;
  const d = t.sheet.details;
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();


  const selectedBackgroundId = draft.background.id;
  // A selected background the current ruleset/sources hide stays listed.
  const hiddenBackground =
    selectedBackgroundId && !catalog.backgrounds.some((b) => b.id === selectedBackgroundId)
      ? catalog.allBackgrounds.find((b) => b.id === selectedBackgroundId)
      : undefined;
  const backgroundList = hiddenBackground ? [hiddenBackground, ...catalog.backgrounds] : catalog.backgrounds;
  const rulesetWarnings = resolution
    ? resolution.warnings.filter((w) => w.id.startsWith("ruleset-") || w.id.startsWith("source-hidden") || w.id.startsWith("asi-double-dip"))
    : [];

  function handleChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "background", choiceId, optionId, count });
  }

  // The "feat" branch here is for a background-granted feat's own cascaded
  // proficiency/ability-bonus/language choices (cid "feat:{index}:...").
  // Excluding a "class:"-prefixed cid keeps this from ALSO picking up an
  // ASI-selected feat's cascaded choices (cid
  // "class:{clsId}:{lvl}:asi:feat:{index}:...", same source.kind "feat")
  // — those belong on ClassPage only, which already scopes by that same
  // "class:" cid prefix.
  const choices = resolution
    ? backgroundChoicesOf(resolution.choices)
    : [];

  return (
    <div className="page">
      <h1>{bp.title} {loading && "…"}</h1>
      <StepProblems step="background" />
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
      {catalog.backgroundsFallback && (
        <p role="note">
          {bp.fallbackNote}
        </p>
      )}
      <select
        aria-label={bp.selectLabel}
        value={selectedBackgroundId ?? ""}
        onChange={(e) => {
          if (e.target.value) dispatch({ type: "SET_BACKGROUND", backgroundId: e.target.value });
        }}
      >
        <option value="">{bp.choose}</option>
        {backgroundList.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
            {hiddenBackground && b.id === hiddenBackground.id ? ` (${t.common.hiddenByFilters})` : ""}
          </option>
        ))}
      </select>
      {selectedBackgroundId && !loading && choices.length === 0 && <p>{bp.noChoices}</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(choices)} />
      ))}

      <details className="details-section">
        <summary>{d.title}</summary>
        <label>
          {d.fields.alignment}
          <select value={draft.details.alignment ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "alignment", value: e.target.value })}>
            <option value="">{t.common.none}</option>
            <option value="Lawful Good">{bp.alignments["Lawful Good"]}</option>
            <option value="Neutral Good">{bp.alignments["Neutral Good"]}</option>
            <option value="Chaotic Good">{bp.alignments["Chaotic Good"]}</option>
            <option value="Lawful Neutral">{bp.alignments["Lawful Neutral"]}</option>
            <option value="True Neutral">{bp.alignments["True Neutral"]}</option>
            <option value="Chaotic Neutral">{bp.alignments["Chaotic Neutral"]}</option>
            <option value="Lawful Evil">{bp.alignments["Lawful Evil"]}</option>
            <option value="Neutral Evil">{bp.alignments["Neutral Evil"]}</option>
            <option value="Chaotic Evil">{bp.alignments["Chaotic Evil"]}</option>
          </select>
        </label>
        <label>
          {d.fields.faith}
          <input type="text" value={draft.details.faith ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "faith", value: e.target.value })} />
        </label>
        <label>
          {d.fields.lifestyle}
          <input type="text" value={draft.details.lifestyle ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "lifestyle", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.physical}</summary>
        <label>
          {d.fields.age}
          <input type="text" value={draft.details.age ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "age", value: e.target.value })} />
        </label>
        <label>
          {d.fields.height}
          <input type="text" value={draft.details.height ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "height", value: e.target.value })} />
        </label>
        <label>
          {d.fields.weight}
          <input type="text" value={draft.details.weight ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "weight", value: e.target.value })} />
        </label>
        <label>
          {d.fields.eyes}
          <input type="text" value={draft.details.eyes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "eyes", value: e.target.value })} />
        </label>
        <label>
          {d.fields.skin}
          <input type="text" value={draft.details.skin ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "skin", value: e.target.value })} />
        </label>
        <label>
          {d.fields.hair}
          <input type="text" value={draft.details.hair ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "hair", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.personality}</summary>
        <label>
          {d.fields.personalityTraits}
          <textarea value={draft.details.personalityTraits ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "personalityTraits", value: e.target.value })} />
        </label>
        <label>
          {d.fields.ideals}
          <textarea value={draft.details.ideals ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "ideals", value: e.target.value })} />
        </label>
        <label>
          {d.fields.bonds}
          <textarea value={draft.details.bonds ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "bonds", value: e.target.value })} />
        </label>
        <label>
          {d.fields.flaws}
          <textarea value={draft.details.flaws ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "flaws", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>{d.sections.notes}</summary>
        <label>
          {d.fields.backstory}
          <textarea value={draft.details.backstory ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "backstory", value: e.target.value })} />
        </label>
        <label>
          {d.fields.organizations}
          <textarea value={draft.details.organizations ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "organizations", value: e.target.value })} />
        </label>
        <label>
          {d.fields.allies}
          <textarea value={draft.details.allies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "allies", value: e.target.value })} />
        </label>
        <label>
          {d.fields.enemies}
          <textarea value={draft.details.enemies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "enemies", value: e.target.value })} />
        </label>
        <label>
          {d.fields.notes}
          <textarea value={draft.details.notes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "notes", value: e.target.value })} />
        </label>
      </details>
    </div>
  );
}
