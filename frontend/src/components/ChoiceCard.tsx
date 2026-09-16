import { useState } from "react";
import type { Choice } from "../types";
import { ChoicePicker } from "./ChoicePicker";

interface ChoiceCardProps {
  choice: Choice;
  onChange: (choiceId: string, selected: string[]) => void;
}

export function ChoiceCard({ choice, onChange }: ChoiceCardProps) {
  const [expanded, setExpanded] = useState(choice.status === "pending");

  return (
    <div className="choice-card" data-status={choice.status}>
      <button
        type="button"
        className="choice-card__header"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {choice.status === "pending" && (
          <span className="choice-card__pending-dot" aria-label="pending choice">
            !
          </span>
        )}
        <span className="choice-card__label">{choice.label}</span>
        {choice.source.level != null && (
          <span className="choice-card__level">{choice.source.level} level</span>
        )}
        <span className="choice-card__count">
          {choice.count} {choice.count === 1 ? "Choice" : "Choices"}
        </span>
      </button>
      {expanded && (
        <div className="choice-card__body">
          <p>{choice.description}</p>
          <ChoicePicker choice={choice} onChange={onChange} />
        </div>
      )}
    </div>
  );
}
