import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useT } from "../LanguageContext";
import type { Choice } from "../types";
import { ChoicePicker } from "./ChoicePicker";
import { cidFromHash } from "../logic/hashTarget";
import { useNewChoices } from "../NewChoicesContext";

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
  const t = useT();
  // A "#<cid>" URL hash (the Export page's unresolved list links here) opens
  // this card and scrolls to it. cids contain colons, so the element is found
  // with getElementById, never a CSS selector.
  const { hash } = useLocation();
  const isTarget = cidFromHash(hash) === choice.id;
  const isNew = useNewChoices().has(choice.id) && choice.status === "pending";
  const [expanded, setExpanded] = useState(defaultExpanded || isTarget);

  useEffect(() => {
    if (!isTarget) return;
    setExpanded(true);
    document.getElementById(choice.id)?.scrollIntoView?.({ block: "start" });
  }, [isTarget, choice.id]);

  return (
    <div className="choice-card" id={choice.id} data-status={choice.status} data-state={expanded ? "expanded" : "collapsed"} data-new={isNew ? "true" : undefined}>
      <button
        type="button"
        className="choice-card__header"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {choice.status === "pending" && !choice.optional && (
          <span className="choice-card__pending-dot" aria-label={t.choice.pendingDot}>
            !
          </span>
        )}
        <span className="choice-card__label">{choice.label}</span>
        {isNew && <span className="choice-card__new">{t.choice.newMarker}</span>}
        {choice.source.level != null && (
          <span className="choice-card__level">{t.choice.levelBadge(choice.source.level)}</span>
        )}
        <span className="choice-card__count">
          {t.choice.counter(choice.selected.length, choice.count)}
        </span>
      </button>
      {expanded && (
        <div className="choice-card__body">
          <p>{choice.description}</p>
          {choice.status === "unavailable" && <p>{choice.unavailableReason}</p>}
          {choice.granted && choice.granted.length > 0 && (
            <p>{t.choice.granted(choice.granted.map((g) => g.label).join(", "))}</p>
          )}
          <ChoicePicker choice={choice} onToggle={onToggle} />
        </div>
      )}
    </div>
  );
}
