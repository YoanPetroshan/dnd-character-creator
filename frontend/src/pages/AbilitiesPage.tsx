import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import type { Ability, Draft } from "../types";

const ABILITIES: Ability[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const POINT_BUY_COST: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
const POINT_BUY_BUDGET = 27;

export function AbilitiesPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const { method, base } = draft.abilities;
  const derived = resolution?.derived as { abilityModifiers?: Record<string, number> } | undefined;
  const modifiers = derived?.abilityModifiers;

  function setAbility(ability: Ability, value: number) {
    dispatch({ type: "SET_ABILITY_SCORE", ability, value });
  }

  function setMethod(next: Draft["abilities"]["method"]) {
    dispatch({ type: "SET_ABILITY_METHOD", method: next });
  }

  const usedInStandardArray = ABILITIES.map((a) => base[a]);
  const pointBuySpent = ABILITIES.reduce((sum, a) => sum + (POINT_BUY_COST[base[a]] ?? 0), 0);

  return (
    <div className="page">
      <h1>Abilities {loading && "…"}</h1>
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
          <input type="radio" name="ability-method" checked={method === "manual"} onChange={() => setMethod("manual")} />
          Manual
        </label>
      </div>

      {method === "pointbuy" && <p>Points Remaining: {POINT_BUY_BUDGET - pointBuySpent}</p>}

      <table className="ability-table">
        <thead>
          <tr>
            <th>Ability</th>
            <th>Score</th>
            <th>Modifier</th>
          </tr>
        </thead>
        <tbody>
          {ABILITIES.map((ability) => {
            const score = base[ability];
            const currentCost = POINT_BUY_COST[score] ?? 0;
            const nextCost = POINT_BUY_COST[score + 1];
            const canIncrement = score < 15 && nextCost !== undefined && pointBuySpent - currentCost + nextCost <= POINT_BUY_BUDGET;
            const modifier = modifiers?.[ability];
            return (
              <tr key={ability}>
                <td>{ability}</td>
                <td>
                  {method === "standard" && (
                    <select value={score} onChange={(e) => setAbility(ability, Number(e.target.value))}>
                      <option value={score}>{score}</option>
                      {STANDARD_ARRAY.filter((v) => !usedInStandardArray.includes(v)).map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  )}
                  {method === "pointbuy" && (
                    <span className="point-buy-stepper">
                      <button type="button" disabled={score <= 8} onClick={() => setAbility(ability, score - 1)}>
                        −
                      </button>
                      <span className="point-buy-stepper__value">{score}</span>
                      <button type="button" disabled={!canIncrement} onClick={() => setAbility(ability, score + 1)}>
                        +
                      </button>
                    </span>
                  )}
                  {method === "manual" && (
                    <input
                      type="number"
                      value={score}
                      onChange={(e) => setAbility(ability, Number(e.target.value))}
                    />
                  )}
                </td>
                <td>{modifier === undefined ? "—" : modifier >= 0 ? `+${modifier}` : modifier}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
