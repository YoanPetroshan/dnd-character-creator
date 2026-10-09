import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import type { Ability, Draft } from "../types";

const ABILITIES: Ability[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
const STANDARD_ARRAY = [15, 14, 13, 12, 10, 8];
const POINT_BUY_COST: Record<number, number> = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
const POINT_BUY_BUDGET = 27;

/** 4d6, drop the lowest die. Uses crypto randomness where available. */
function rollAbilityScore(): number {
  const buf = new Uint32Array(4);
  if (typeof crypto !== "undefined" && crypto.getRandomValues) crypto.getRandomValues(buf);
  else for (let i = 0; i < 4; i++) buf[i] = Math.floor(Math.random() * 0xffffffff);
  const dice = Array.from(buf, (n) => (n % 6) + 1).sort((a, b) => a - b);
  return dice[1] + dice[2] + dice[3];
}

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

  // Standard array: every select lists all six values; picking one that
  // another ability holds swaps the two, so the selects never lock.
  function setStandard(ability: Ability, value: number) {
    const holder = ABILITIES.find((a) => a !== ability && base[a] === value);
    const next = { ...base, [ability]: value };
    if (holder) next[holder] = base[ability];
    dispatch({ type: "SET_ABILITY_SCORES", base: next });
  }

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
                    <select value={score} onChange={(e) => setStandard(ability, Number(e.target.value))}>
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
                      <button type="button" disabled={score <= 8} onClick={() => setAbility(ability, score - 1)}>
                        −
                      </button>
                      <span className="point-buy-stepper__value">{score}</span>
                      <button type="button" disabled={!canIncrement} onClick={() => setAbility(ability, score + 1)}>
                        +
                      </button>
                    </span>
                  )}
                  {method === "roll" && <span>{score}</span>}
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
