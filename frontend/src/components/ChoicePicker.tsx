import type { Choice } from "../types";

interface ChoicePickerProps {
  choice: Choice;
  onChange: (choiceId: string, selected: string[]) => void;
}

export function ChoicePicker({ choice, onChange }: ChoicePickerProps) {
  function toggle(optionId: string) {
    const isSelected = choice.selected.includes(optionId);
    let next: string[];
    if (isSelected) {
      next = choice.selected.filter((id) => id !== optionId);
    } else if (choice.selected.length >= choice.count) {
      // At capacity for a single-choice (count=1) card: picking a
      // different option replaces the previous one, matching how a
      // radio-style choice behaves. For count>1 this drops the oldest
      // pick — acceptable for Phase 0's read-only-round-trip demo; Phase 1
      // can swap this for an explicit "deselect one first" UX if desired.
      next = [...choice.selected.slice(1), optionId];
    } else {
      next = [...choice.selected, optionId];
    }
    onChange(choice.id, next);
  }

  return (
    <ul className="choice-picker">
      {choice.options.map((option) => (
        <li key={option.id}>
          <label className={option.disabled ? "choice-picker__option--disabled" : ""}>
            <input
              type="checkbox"
              checked={choice.selected.includes(option.id)}
              disabled={option.disabled}
              onChange={() => toggle(option.id)}
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
