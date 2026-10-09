import { useState } from "react";
import type { Choice, ChoiceOption } from "../types";

interface ChoicePickerProps {
  choice: Choice;
  /** Toggle one option. The parent computes the new selection from the
   *  draft's stored array (not from `choice.selected`), so two quick taps
   *  inside the debounce window both register. */
  onToggle: (choiceId: string, optionId: string, count: number) => void;
}

/** A filter box appears once a choice has more options than this. */
export const FILTER_THRESHOLD = 20;

const GROUP_LABELS: Record<string, string> = {
  asi: "Увеличение на характеристики",
  general: "Общи черти",
  origin: "Черти за произход",
  "epic-boon": "Епични дарове",
  "feat-2014": "Черти (2014)",
  "any-school": "Всяка школа",
  school: "Школа на магията",
};

export function groupLabel(group: string): string {
  const m = /^spell-level-(\d+)$/.exec(group);
  if (m) return m[1] === "0" ? "Трикове" : `Заклинания ниво ${m[1]}`;
  return GROUP_LABELS[group] ?? group;
}

export function ChoicePicker({ choice, onToggle }: ChoicePickerProps) {
  const [filter, setFilter] = useState("");
  const [showUnavailable, setShowUnavailable] = useState(false);

  const selected = new Set(choice.selected);
  const needle = filter.trim().toLowerCase();
  const filterable = choice.options.length > FILTER_THRESHOLD;
  const matches = (o: ChoiceOption) =>
    !filterable || !needle || selected.has(o.id) || o.label.toLowerCase().includes(needle);
  const unavailable = (o: ChoiceOption) => (!!o.disabled || !!o.hiddenByFilters) && !selected.has(o.id);

  const available = choice.options.filter((o) => !unavailable(o) && matches(o));
  const hidden = choice.options.filter((o) => unavailable(o) && matches(o));
  const shown = showUnavailable ? [...available, ...hidden].sort(
    (a, b) => choice.options.indexOf(a) - choice.options.indexOf(b),
  ) : available;

  function renderOption(option: ChoiceOption, prev: ChoiceOption | undefined) {
    const heading = option.group && option.group !== prev?.group ? option.group : null;
    return (
      <li key={option.id} className={heading ? "choice-picker__item--group-start" : undefined}>
        {heading && (
          <span className="choice-picker__group" role="presentation">
            {groupLabel(heading)}
          </span>
        )}
        <label className={option.disabled ? "choice-picker__option--disabled" : ""}>
          <input
            type="checkbox"
            checked={selected.has(option.id)}
            disabled={option.disabled}
            onChange={() => onToggle(choice.id, option.id, choice.count)}
          />
          {option.label}
          {option.hiddenByFilters && (
            <span className="choice-picker__reason"> — скрит от текущите филтри</span>
          )}
          {option.disabled && option.disabledReason && (
            <span className="choice-picker__reason"> — {option.disabledReason}</span>
          )}
        </label>
      </li>
    );
  }

  return (
    <div className="choice-picker-wrap">
      {filterable && (
        <input
          type="search"
          className="picker-filter"
          aria-label={`Търсене: ${choice.label}`}
          placeholder="Търсене…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      )}
      {filterable && needle && available.length + hidden.length === 0 && <p>Няма съвпадения.</p>}
      <ul className="choice-picker">{shown.map((o, i) => renderOption(o, shown[i - 1]))}</ul>
      {hidden.length > 0 && (
        <button
          type="button"
          className="choice-picker__toggle-unavailable"
          aria-expanded={showUnavailable}
          onClick={() => setShowUnavailable((v) => !v)}
        >
          {showUnavailable ? "Скриване на недостъпните" : `Показване на недостъпните (${hidden.length})`}
        </button>
      )}
    </div>
  );
}
