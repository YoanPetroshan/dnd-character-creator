import { useState } from "react";
import type { Choice } from "../types";
import { ChoicePicker } from "./ChoicePicker";

interface ChoiceCardProps {
  choice: Choice;
  onToggle: (choiceId: string, optionId: string, count: number) => void;
  /** Start expanded (pages pass true for the first pending card only). */
  defaultExpanded?: boolean;
}

/** Id of the first pending choice in a page's list, if any. */
export function firstPendingId(choices: Choice[]): string | undefined {
  return (choices.find((c) => c.status === "pending" && !c.optional) ?? choices.find((c) => c.status === "pending"))?.id;
}

export function ChoiceCard({ choice, onToggle, defaultExpanded = false }: ChoiceCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="choice-card" data-status={choice.status}>
      <button
        type="button"
        className="choice-card__header"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {choice.status === "pending" && !choice.optional && (
          <span className="choice-card__pending-dot" aria-label="pending choice">
            !
          </span>
        )}
        <span className="choice-card__label">{choice.label}</span>
        {choice.source.level != null && (
          <span className="choice-card__level">{choice.source.level} level</span>
        )}
        <span className="choice-card__count">
          избрани {choice.selected.length}/{choice.count}
        </span>
      </button>
      {expanded && (
        <div className="choice-card__body">
          <p>{choice.description}</p>
          {choice.status === "unavailable" && <p>{choice.unavailableReason}</p>}
          {choice.granted && choice.granted.length > 0 && (
            <p>Получавате автоматично: {choice.granted.map((g) => g.label).join(", ")}</p>
          )}
          <ChoicePicker choice={choice} onToggle={onToggle} />
        </div>
      )}
    </div>
  );
}
