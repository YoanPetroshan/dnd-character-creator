import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { sourceLabel, sourceOn, toggleSource } from "../logic/sources";
import type { Ruleset } from "../types";
import { LanguageSwitch } from "../components/LanguageSwitch";

/** Things set once (DESIGN-L, decision 3A): language, rules and books, hit points and prerequisites, and the clean-up of
 *  picks that no longer apply. They were on Home, between the hero list and the name. */
export function SettingsPage() {
  const t = useT();
  const { draft, dispatch } = useDraft();
  const { resolution } = useResolutionContext();
  const catalog = useCatalogContext();

  const allSourceIds = catalog.sources.map((src) => src.id);
  const sourceOnFor = (id: string) => sourceOn(draft.sources, id);
  function toggle(id: string, on: boolean) {
    dispatch({ type: "SET_SOURCES", sources: toggleSource(draft.sources, allSourceIds, id, on) });
  }
  return (
    <div className="page" data-page="settings">
      <h1>{t.nav.settings}</h1>
      <h2>{t.lang.label}</h2>
      <LanguageSwitch />

      <h2>{t.home.rulesTitle}</h2>
      <label>
        {t.home.rulesetLabel}
        <select value={draft.ruleset} onChange={(e) => dispatch({ type: "SET_RULESET", ruleset: e.target.value as Ruleset })}>
          <option value="2014">2014</option>
          <option value="2024">2024</option>
          <option value="mixed">{t.home.rulesetMixed}</option>
        </select>
      </label>
      <p>{t.home.rulesetHelp[draft.ruleset] ?? t.home.rulesetHelp.mixed}</p>
      <details className="details-section">
        <summary>
          {t.home.sourcesSummary(draft.sources.length === 0 ? null : draft.sources.filter((x) => x.toLowerCase() !== "srd" && allSourceIds.some((id) => id.toLowerCase() === x.toLowerCase())).length)}
        </summary>
        <div>
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: [] })}>
            {t.home.sourcesAll}
          </button>{" "}
          <button type="button" onClick={() => dispatch({ type: "SET_SOURCES", sources: ["srd"] })}>
            {t.home.sourcesSrdOnly}
          </button>
        </div>
        {catalog.sources.map((src) => (
          <label key={src.id}>
            <input type="checkbox" checked={sourceOnFor(src.id)} onChange={(e) => toggle(src.id, e.target.checked)} />
            {sourceLabel(src)} <span className="source-count">({src.count})</span>
          </label>
        ))}
      </details>

      <h2>{t.home.preferencesTitle}</h2>
      <fieldset>
        <legend>{t.home.hpPerLevel}</legend>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "fixed"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "fixed" })}
          />
          {t.home.hpFixed}
        </label>
        <label>
          <input
            type="radio"
            name="hitPointType"
            checked={draft.preferences.hitPointType === "manual"}
            onChange={() => dispatch({ type: "SET_HIT_POINT_TYPE", hitPointType: "manual" })}
          />
          {t.home.hpManual}
        </label>
      </fieldset>

      <fieldset>
        <legend>{t.home.prerequisites}</legend>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.feats}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "feats", value: e.target.checked })}
          />
          {t.home.prereqFeats}
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.preferences.usePrerequisites.multiclass}
            onChange={(e) => dispatch({ type: "SET_USE_PREREQUISITE", field: "multiclass", value: e.target.checked })}
          />
          {t.home.prereqMulticlass}
        </label>
      </fieldset>

      {resolution && resolution.pruned.length > 0 && (
        <>
          <h2>{t.home.prunedTitle}</h2>
          <ul>
            {resolution.pruned.map((p, i) => (
              <li key={`${i}-${p.choiceId}`} data-state="pruned">{p.reason}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() =>
              dispatch({
                type: "CLEAR_STALE_SELECTIONS",
                keepIds: resolution.choices.map((c) => c.id),
                // "class:<id>:subclass" = a subclass kept below its unlock level
                clearSubclassFor: resolution.pruned
                  .map((p) => /^class:(.+):subclass$/.exec(p.choiceId)?.[1])
                  .filter((id): id is string => !!id),
              })
            }
          >
            {t.home.clearPruned}
          </button>
        </>
      )}
    </div>
  );
}
