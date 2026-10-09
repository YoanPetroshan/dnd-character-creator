import type { Choice } from "../types";

interface ChoicePickerProps {
  choice: Choice;
  /** Toggle one option. The parent computes the new selection from the
   *  draft's stored array (not from `choice.selected`), so two quick taps
   *  inside the debounce window both register. */
  onToggle: (choiceId: string, optionId: string, count: number) => void;
}

export function ChoicePicker({ choice, onToggle }: ChoicePickerProps) {
  return (
    <ul className="choice-picker">
      {choice.options.map((option) => (
        <li key={option.id}>
          <label className={option.disabled ? "choice-picker__option--disabled" : ""}>
            <input
              type="checkbox"
              checked={choice.selected.includes(option.id)}
              disabled={option.disabled}
              onChange={() => onToggle(choice.id, option.id, choice.count)}
            />
            {option.label}
            {option.disabled && option.disabledReason && (
              <span className="choice-picker__reason"> — {option.disabledReason}</span>
            )}
          </label>
        </li>
      ))}
    </ul>
  );
}
