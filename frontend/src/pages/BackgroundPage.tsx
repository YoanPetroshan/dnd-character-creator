import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { backgroundChoicesOf } from "../logic/choiceRouting";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";
import { FeatureEyeList, grantedFeatures } from "../components/FeatureEyeList";
import { SheetEyesProvider } from "../components/sheet/SheetEyes";

export function BackgroundPage() {
  const t = useT();
  const bp = t.backgroundPage;
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
    <SheetEyesProvider>
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
      {selectedBackgroundId && grantedFeatures(resolution?.sheet, "background").length > 0 && (
        <div className="granted-features">
          <h2>{bp.gives}</h2>
          <FeatureEyeList idPrefix="background" features={grantedFeatures(resolution?.sheet, "background")} />
        </div>
      )}
      {selectedBackgroundId && !loading && choices.length === 0 && <p>{bp.noChoices}</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(choices)} />
      ))}

    </div>
    </SheetEyesProvider>
  );
}
