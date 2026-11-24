import { useState } from "react";
import { useDraft } from "../../DraftContext";
import { useT } from "../../LanguageContext";
import { CONDITIONS, currentHp } from "../../logic/play";
import type { SheetSection, SheetSectionData } from "../../logic/sheetSections";
import { DefensesSection } from "../sheet/EquipmentSection";

function data<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** Hit points, live like the online sheet: HEAL / amount / DAMAGE on the left, then CURRENT / MAX / TEMP. Damage takes the
 *  temporary hit points first. The values live in the hero's play state (never sent to the engine). */
export function HitPointsBox({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const b = t.sheet.boxes;
  const { draft, dispatch } = useDraft();
  const hp = data(sections, "hitPoints");
  const [amount, setAmount] = useState("");
  const [editingTemp, setEditingTemp] = useState(false);
  if (!hp) return null;
  const max = hp.max;
  const current = currentHp(max, draft.play?.damage);
  const temp = draft.play?.tempHp ?? 0;
  const n = Number.parseInt(amount, 10);
  function apply(kind: "heal" | "damage") {
    if (!Number.isFinite(n) || n <= 0) return;
    dispatch({ type: "APPLY_HP", kind, amount: n, maxHp: max });
    setAmount("");
  }
  return (
    <div className="sheet-box stat-box stat-box--hp" data-summary="hitPoints" data-section="hitPoints">
      <div className="hp-adjust">
        <button type="button" className="hp-adjust__heal" onClick={() => apply("heal")} disabled={!(n > 0)}>
          {b.heal}
        </button>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          className="hp-adjust__amount"
          aria-label={b.amountLabel}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") apply("damage");
          }}
        />
        <button type="button" className="hp-adjust__damage" onClick={() => apply("damage")} disabled={!(n > 0)}>
          {b.damage}
        </button>
      </div>
      <dl className="hp-values">
        <div className="hp-cell">
          <dt className="hp-cell__label">{b.hpCurrent}</dt>
          <dd className="hp-cell__value" data-summary="currentHp">
            {current}
          </dd>
        </div>
        <span className="hp-values__slash" aria-hidden="true">
          /
        </span>
        <div className="hp-cell">
          <dt className="hp-cell__label">{b.hpMax}</dt>
          <dd className="hp-cell__value">{max}</dd>
        </div>
        <div className="hp-cell hp-cell--temp">
          <dt className="hp-cell__label">{b.hpTemp}</dt>
          <dd className="hp-cell__value">
            {editingTemp ? (
              <input
                type="number"
                inputMode="numeric"
                min={0}
                autoFocus
                className="hp-temp-input"
                aria-label={b.hpTemp}
                defaultValue={temp || ""}
                onBlur={(e) => {
                  dispatch({ type: "SET_TEMP_HP", value: Number(e.target.value) });
                  setEditingTemp(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                }}
              />
            ) : (
              <button type="button" className="hp-temp" aria-label={b.editTemp} onClick={() => setEditingTemp(true)}>
                {temp > 0 ? temp : "--"}
              </button>
            )}
          </dd>
        </div>
      </dl>
      <p className="stat-box__bottom hp-title">{b.hpTitle}</p>
    </div>
  );
}

/** Heroic Inspiration: a framed box that is on or off, its name under it (outside the frame). */
export function InspirationBox() {
  const t = useT();
  const { draft, dispatch } = useDraft();
  const on = !!draft.play?.inspiration;
  return (
    <div className="inspiration">
      <button
        type="button"
        className="inspiration__box"
        aria-pressed={on}
        aria-label={t.sheet.boxes.inspiration}
        onClick={() => dispatch({ type: "TOGGLE_INSPIRATION" })}
      />
      <span className="inspiration__label" aria-hidden="true">
        {t.sheet.boxes.inspiration}
      </span>
    </div>
  );
}

/** DEFENSES | CONDITIONS: the character's resistances and immunities on the left, the active conditions on the right with a
 *  menu to add one (always shown, like the online sheet, so the row over the tabs has no hole). */
export function DefensesConditionsBox({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const b = t.sheet.boxes;
  const defenses = data(sections, "defenses");
  return (
    <div className="defenses-conditions">
      <div className="defenses-conditions__half">
        <h3>{b.defenses}</h3>
        {defenses ? <DefensesSection data={defenses} /> : <p className="defenses-conditions__none">{b.noDefenses}</p>}
      </div>
      <div className="defenses-conditions__half">
        <h3>{b.conditions}</h3>
        <ConditionsEditor />
      </div>
    </div>
  );
}

/** The active conditions as chips (tap to remove) and the menu to add one. */
export function ConditionsEditor({ open = false }: { open?: boolean }) {
  const t = useT();
  const b = t.sheet.boxes;
  const { draft, dispatch } = useDraft();
  const active = draft.play?.conditions ?? [];
  return (
    <>
        {active.length > 0 && (
          <ul className="condition-chips">
            {active.map((c) => (
              <li key={c}>
                <button type="button" aria-label={b.removeCondition(c)} onClick={() => dispatch({ type: "TOGGLE_CONDITION", condition: c })}>
                  {c} <span aria-hidden="true">×</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <details className="condition-menu" open={open || undefined}>
          <summary>{b.addCondition}</summary>
          <ul>
            {CONDITIONS.map((c) => (
              <li key={c}>
                <label>
                  <input type="checkbox" checked={active.includes(c)} onChange={() => dispatch({ type: "TOGGLE_CONDITION", condition: c })} />
                  {c}
                </label>
              </li>
            ))}
          </ul>
        </details>
    </>
  );
}
