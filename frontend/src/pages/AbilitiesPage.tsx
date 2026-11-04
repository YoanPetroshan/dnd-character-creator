import { CommitNumberInput } from "../components/CommitNumberInput";
import { StepProblems } from "../components/StepProblems";
import { t } from "../copy";
import { useDraft } from "../DraftContext";
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

  const pointBuySpent = pointBuySpentOf(base);

  return (
    <div className="page">
      <h1>Abilities {loading && "…"}</h1>
      <StepProblems step="abilities" />
      <div className="ability-method-selector">
        <label>
          <input type="radio" name="ability-method" checked={method === "standard"} onChange={() => setMethod("standard")} />
          Standard Array
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "pointbuy"} onChange={() => setMethod("pointbuy")} />
          Point Buy
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "roll"} onChange={() => setMethod("roll")} />
          Roll (4d6, drop lowest)
        </label>
        <label>
          <input type="radio" name="ability-method" checked={method === "manual"} onChange={() => setMethod("manual")} />
          Manual
        </label>
      </div>

      {method === "roll" && (
        <p>
          <button
            type="button"
            onClick={() =>
              dispatch({
                type: "SET_ABILITY_SCORES",
                base: Object.fromEntries(ABILITIES.map((a) => [a, rollAbilityScore()])) as Record<Ability, number>,
              })
            }
          >
            Roll all six scores
          </button>{" "}
          Re-rolling replaces the current scores.
        </p>
      )}
      {method === "pointbuy" && <p>Points Remaining: {POINT_BUY_BUDGET - pointBuySpent}</p>}

      <table className="ability-table">
        <thead>
          <tr>
            <th>{t.abilitiesPage.columns.ability}</th>
            <th>{t.abilitiesPage.columns.base}</th>
            <th>{t.abilitiesPage.columns.bonus}</th>
            <th>{t.abilitiesPage.columns.total}</th>
            <th>{t.abilitiesPage.columns.modifier}</th>
          </tr>
        </thead>
        <tbody>
          {ABILITIES.map((ability) => {
            const score = base[ability];
            const canInc = canIncrement(base, ability);
            const row = rowOf(ability);
            return (
              <tr key={ability}>
                <td>{ability}</td>
                <td>
                  {method === "standard" && (
                    <select aria-label={`${ability}: стойност`} value={score} onChange={(e) => setStandard(ability, Number(e.target.value))}>
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
                      <button type="button" aria-label={`${ability}: намали`} disabled={score <= 8} onClick={() => setAbility(ability, score - 1)}>
                        −
                      </button>
                      <span className="point-buy-stepper__value">{score}</span>
                      <button type="button" aria-label={`${ability}: увеличи`} disabled={!canInc} onClick={() => setAbility(ability, score + 1)}>
                        +
                      </button>
                    </span>
                  )}
                  {method === "roll" && <span>{score}</span>}
                  {method === "manual" && (
                    <CommitNumberInput
                      ariaLabel={`${ability}: стойност`}
                      min={1}
                      max={30}
                      value={score}
                      onCommit={(value) => setAbility(ability, value)}
                    />
                  )}
                </td>
                <td>{row?.bonus == null ? t.common.none : formatModifier(row.bonus)}</td>
                <td>{row?.total ?? t.common.none}</td>
                <td>{formatModifier(row?.modifier)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
