import { CommitNumberInput } from "../components/CommitNumberInput";
import { ScoreSlider } from "../components/ScoreSlider";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { useResolutionContext } from "../ResolutionContext";
import {
  ABILITIES,
  POINT_BUY_BUDGET,
  STANDARD_ARRAY,
  canIncrement,
  formatModifier,
  pointBuySpent as pointBuySpentOf,
  rollAbilityScore,
  setStandardScore,
} from "../logic/abilities";
import { abilityRows } from "../logic/sheetSections";
import type { Ability, Draft } from "../types";

export function AbilitiesPage() {
  const t = useT();
  const ap = t.abilitiesPage;
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();


  const { method, base } = draft.abilities;
  // base / bonus / total / modifier per ability (the scores before and after species, background and feat bonuses)
  const rows = resolution ? abilityRows(resolution.sheet.abilities, resolution.derived.abilityModifiers, base) : null;
  const rowOf = (ability: Ability) => rows?.find((r) => r.ability === ability);

  function setAbility(ability: Ability, value: number) {
    dispatch({ type: "SET_ABILITY_SCORE", ability, value });
  }

  function setMethod(next: Draft["abilities"]["method"]) {
    dispatch({ type: "SET_ABILITY_METHOD", method: next });
  }

  // Standard array: every select lists all six values; picking one that
  // another ability holds swaps the two, so the selects never lock.
  function setStandard(ability: Ability, value: number) {
    dispatch({ type: "SET_ABILITY_SCORES", base: setStandardScore(base, ability, value) });
  }

  const pointsLeft = POINT_BUY_BUDGET - pointBuySpentOf(base);

  return (
    <div className="page">
      <h1>{ap.title} {loading && "…"}</h1>
      <StepProblems step="abilities" />
      <div className="ability-method-selector">
        <label>
          <input type="radio" name="ability-method" checked={method === "standard"} onChange={() => setMethod("standard")} />
          {ap.methods.standard}
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "pointbuy"} onChange={() => setMethod("pointbuy")} />
          {ap.methods.pointbuy}
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "roll"} onChange={() => setMethod("roll")} />
          {ap.methods.roll}
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "manual"} onChange={() => setMethod("manual")} />
          {ap.methods.manual}
        </label>
      </div>

      {method === "roll" && (
        <div className="ability-roll">
          <button
            type="button"
            className="ability-roll__button"
            onClick={() =>
              dispatch({
                type: "SET_ABILITY_SCORES",
                base: Object.fromEntries(ABILITIES.map((a) => [a, rollAbilityScore()])) as Record<Ability, number>,
              })
            }
          >
            {ap.rollAll}
          </button>
          <p className="ability-note">
            <span className="ability-note__mark" aria-hidden="true">
              !
            </span>
            {ap.rerollNote}
          </p>
        </div>
      )}
      {method === "pointbuy" && (
        <p className="point-buy-remaining" role="status" data-state={pointsLeft <= 0 ? "alert" : "ok"}>
          {pointsLeft <= 0 && (
            <span className="ability-note__mark" aria-hidden="true">
              !
            </span>
          )}
          {ap.pointsRemaining(pointsLeft)}
        </p>
      )}

      <table className="ability-table">
        <thead>
          <tr>
            <th>{ap.columns.ability}</th>
            <th>{ap.columns.base}</th>
            <th>{ap.columns.bonus}</th>
            <th>{ap.columns.total}</th>
            <th>{ap.columns.modifier}</th>
          </tr>
        </thead>
        <tbody>
          {ABILITIES.map((ability) => {
            const score = base[ability];
            const canInc = canIncrement(base, ability);
            const row = rowOf(ability);
            // while the resolution is one step behind the base (a slider drag), the total and the modifier are worked out here
            const stale = row != null && row.base !== score;
            const total = stale ? score + (row.bonus ?? 0) : row?.total;
            const modifier = stale && total != null ? Math.floor((total - 10) / 2) : row?.modifier;
            return (
              <tr key={ability}>
                <th scope="row" className="ability-name">{ability}</th>
                <td>
                  {method === "standard" && (
                    <select aria-label={ap.valueLabel(ability)} value={score} onChange={(e) => setStandard(ability, Number(e.target.value))}>
                      {!STANDARD_ARRAY.includes(score) && <option value={score}>{score}</option>}
                      {STANDARD_ARRAY.map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  )}
                  {method === "pointbuy" && (
                    <span className="point-buy-stepper">
                      <button type="button" aria-label={ap.decreaseLabel(ability)} disabled={score <= 8} onClick={() => setAbility(ability, score - 1)}>
                        −
                      </button>
                      <span className="point-buy-stepper__value">{score}</span>
                      <button type="button" aria-label={ap.increaseLabel(ability)} disabled={!canInc} onClick={() => setAbility(ability, score + 1)}>
                        +
                      </button>
                    </span>
                  )}
                  {method === "roll" && <span>{score}</span>}
                  {method === "manual" && (
                    <span className="ability-manual">
                      <CommitNumberInput
                        ariaLabel={ap.valueLabel(ability)}
                        min={1}
                        max={30}
                        value={score}
                        onCommit={(value) => setAbility(ability, value)}
                      />
                      <ScoreSlider ariaLabel={ap.sliderLabel(ability)} min={1} max={20} value={score} onChange={(value) => setAbility(ability, value)} />
                    </span>
                  )}
                </td>
                <td>
                  <span className="ability-chip" data-empty={!row?.bonus ? "true" : undefined}>
                    {row?.bonus ? formatModifier(row.bonus) : t.common.none}
                  </span>
                </td>
                <td className="ability-total">{total ?? t.common.none}</td>
                <td>
                  <span className="ability-mod">{formatModifier(modifier)}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
