import { Fragment, useId, useState } from "react";
import { useT } from "../LanguageContext";
import type { Copy } from "../copy";
import { optionSource } from "../logic/sources";
import type { Choice, ChoiceOption } from "../types";
import { useDraftRuleset } from "../DraftContext";
import { optionFeatId, optionItemIds } from "../logic/optionItems";
import { isLetteredEquipment } from "../logic/choiceRouting";
import { DetailEye, DetailPanel, ParagraphsBody } from "./DetailEye";
import { FeatDetailBody, useFeatDetails } from "./FeatDetailBody";
import { ItemDetailBody, useItemDetails } from "./ItemDetailBody";
import { SpellDetailBody, useSpellDetails } from "./SpellDetailBody";

interface ChoicePickerProps {
  choice: Choice;
  /** Toggle one option. The parent computes the new selection from the
   *  draft's stored array (not from `choice.selected`), so two quick taps
   *  inside the debounce window both register. */
  onToggle: (choiceId: string, optionId: string, count: number) => void;
}

/** A filter box appears once a choice has more options than this. */
export const FILTER_THRESHOLD = 20;

/** Y1: a card with more options than this gets the long-list layout
 *  (collapsed groups, "Избрано" block, source select). Shorter cards render
 *  exactly as before. */
export const LONG_LIST_THRESHOLD = 30;

/** The state of one option row, for styling: disabled, hidden-by-filters or available. */
/** The book code of an option: the server's `source` (Y2), else the code parsed from the label. */
const srcOf = (o: ChoiceOption): string | null => o.source ?? optionSource(o.label);

function optionState(o: ChoiceOption): "disabled" | "hidden-by-filters" | "available" {
  return o.disabled ? "disabled" : o.hiddenByFilters ? "hidden-by-filters" : "available";
}

export function groupLabel(t: Copy, group: string): string {
  const m = /^spell-level-(\d+)$/.exec(group);
  if (m) return m[1] === "0" ? t.choice.cantripsGroup : t.choice.spellLevelGroup(m[1]);
  return t.choice.groups[group] ?? group;
}

const isSpellOption = (o: ChoiceOption): boolean => /^spell-level-\d+$/.test(o.group ?? "");

/** The eye button of a spell row or an item row (a sibling of the label, so it never toggles the checkbox) and the panel
 *  under it. A spell option is a spell id; an option of an equipment (or weapon mastery) choice is one or several item
 *  ids joined with "+", and its panel stacks one item body per id. */
function useOptionPreview(choice: Choice) {
  const t = useT();
  const spells = useSpellDetails();
  const items = useItemDetails(useDraftRuleset());
  const feats = useFeatDetails();
  const [open, setOpen] = useState<Set<string>>(new Set());
  const isOpen = (o: ChoiceOption) => open.has(o.id);
  const itemIds = (o: ChoiceOption) => optionItemIds(choice, o);
  const featId = (o: ChoiceOption) => (isSpellOption(o) || itemIds(o).length > 0 ? null : optionFeatId(o));
  // the rules text the option carries itself (Fighting Style, invocations, ...): shown without a fetch
  const ownText = (o: ChoiceOption) => (isSpellOption(o) || itemIds(o).length > 0 || featId(o) ? "" : (o.description ?? "").trim());
  const hasEye = (o: ChoiceOption) => isSpellOption(o) || itemIds(o).length > 0 || featId(o) !== null || ownText(o) !== "";
  function toggle(o: ChoiceOption) {
    const next = new Set(open);
    if (next.has(o.id)) next.delete(o.id);
    else {
      next.add(o.id);
      if (isSpellOption(o)) spells.loadDetail(o.id);
      else if (featId(o)) feats.loadDetail(featId(o)!);
      else itemIds(o).forEach(items.loadDetail);
    }
    setOpen(next);
  }
  const button = (o: ChoiceOption) =>
    hasEye(o) && (
      <DetailEye
        label={isSpellOption(o) ? t.choice.showSpell : itemIds(o).length > 0 ? t.choice.showItem : t.choice.showDetails(o.label)}
        open={isOpen(o)}
        onToggle={() => toggle(o)}
      />
    );
  const panel = (o: ChoiceOption) =>
    hasEye(o) &&
    isOpen(o) && (
      <DetailPanel>
        {isSpellOption(o) ? (
          <SpellDetailBody state={spells.details[o.id]} />
        ) : itemIds(o).length > 0 ? (
          itemIds(o).map((id) => <ItemDetailBody key={id} state={items.detailOf(id)} />)
        ) : featId(o) ? (
          <FeatDetailBody state={feats.detailOf(featId(o)!)} />
        ) : (
          <ParagraphsBody paragraphs={ownText(o).split(/\n{2,}/)} />
        )}
      </DetailPanel>
    );
  const itemClass = (o: ChoiceOption, extra?: string) =>
    [extra, hasEye(o) ? "choice-picker__item--spell" : null, hasEye(o) && isOpen(o) ? "choice-picker__item--spell-open" : null]
      .filter(Boolean)
      .join(" ") || undefined;
  return { button, panel, itemClass, hasEye };
}

/** The shared "Kind: " prefix of every option label ("Skill: Arcana", "Skill: History" ...), or "" when the labels differ.
 *  The card heading already names the kind, so the rows drop it (DESIGN-L: say a thing once). */
export function sharedLabelPrefix(options: ChoiceOption[]): string {
  if (options.length < 2) return "";
  const m = /^([^:]{2,24}): /.exec(options[0].label);
  return m && options.every((o) => o.label.startsWith(m[0])) ? m[0] : "";
}

function ShortPicker({ choice, onToggle }: ChoicePickerProps) {
  const t = useT();
  const [filter, setFilter] = useState("");
  const [showUnavailable, setShowUnavailable] = useState(false);
  const preview = useOptionPreview(choice);

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

  // starting equipment: the options are lettered rows A, B, C (the order of the rules text, "(A) ... (B) ...")
  // (the follow-up pick of an option, "...equipment-choice-2:0", is a plain list: it only appears once its option is picked)
  const lettered = isLetteredEquipment(choice);
  const letterOf = (o: ChoiceOption) => (lettered ? String.fromCharCode(65 + choice.options.indexOf(o)) : undefined);
  const prefix = sharedLabelPrefix(choice.options);

  function renderOption(option: ChoiceOption, prev: ChoiceOption | undefined) {
    const heading = option.group && option.group !== prev?.group ? option.group : null;
    // a spell row keeps its own box (the eye button and the panel hang on it): its group heading is a row of its own
    const spellHeading = heading && preview.hasEye(option) ? heading : null;
    return (
      <Fragment key={option.id}>
        {spellHeading && (
          <li className="choice-picker__group-row" role="presentation">
            <span className="choice-picker__group" role="presentation">
              {groupLabel(t, spellHeading)}
            </span>
          </li>
        )}
      <li className={preview.itemClass(option, heading && !spellHeading ? "choice-picker__item--group-start" : undefined)} data-state={optionState(option)}>
        {heading && !spellHeading && (
          <span className="choice-picker__group" role="presentation">
            {groupLabel(t, heading)}
          </span>
        )}
        <label className={option.disabled ? "choice-picker__option--disabled" : ""} data-letter={letterOf(option)}>
          <input
            type="checkbox"
            checked={selected.has(option.id)}
            disabled={option.disabled}
            aria-disabled={option.disabled || undefined}
            aria-describedby={option.disabled && option.disabledReason ? `${choice.id}::${option.id}::why` : undefined}
            onChange={() => onToggle(choice.id, option.id, choice.count)}
          />
          {prefix ? option.label.slice(prefix.length) : option.label}
          {option.hiddenByFilters && (
            <span className="choice-picker__reason"> — {t.common.hiddenByFilters}</span>
          )}
          {option.disabled && option.disabledReason && (
            <span className="choice-picker__reason" id={`${choice.id}::${option.id}::why`}> — {option.disabledReason}</span>
          )}
        </label>
        {preview.button(option)}
        {preview.panel(option)}
      </li>
      </Fragment>
    );
  }

  return (
    <div className="choice-picker-wrap">
      {filterable && (
        <input
          type="search"
          className="picker-filter"
          aria-label={t.choice.searchLabel(choice.label)}
          placeholder={t.common.search}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      )}
      {filterable && needle && available.length + hidden.length === 0 && <p>{t.common.noMatches}</p>}
      <ul className={lettered ? "choice-picker choice-picker--lettered" : "choice-picker"}>{shown.map((o, i) => renderOption(o, shown[i - 1]))}</ul>
      {hidden.length > 0 && (
        <button
          type="button"
          className="choice-picker__toggle-unavailable"
          aria-expanded={showUnavailable}
          onClick={() => setShowUnavailable((v) => !v)}
        >
          {showUnavailable ? t.choice.hideUnavailable : t.choice.showUnavailable(hidden.length)}
        </button>
      )}
    </div>
  );
}

/** A stable bucket for options the server gave no `group`. */
const NO_GROUP = "";

function LongPicker({ choice, onToggle }: ChoicePickerProps) {
  const t = useT();
  const uid = useId();
  const [filter, setFilter] = useState("");
  const [source, setSource] = useState("");
  const [showUnavailable, setShowUnavailable] = useState(false);
  /** User choices only; a group with no entry follows its default. */
  const [openState, setOpenState] = useState<Record<string, boolean>>({});
  const preview = useOptionPreview(choice);

  const selected = new Set(choice.selected);
  const needle = filter.trim().toLowerCase();
  const searching = needle !== "" || source !== "";
  const labelOf = new Map(choice.options.map((o) => [o.id, o.label]));

  // Source select: only when the labels carry book codes for 2+ books.
  const sourceCounts = new Map<string, number>();
  let unlabelled = 0;
  for (const o of choice.options) {
    const src = srcOf(o);
    if (src) sourceCounts.set(src, (sourceCounts.get(src) ?? 0) + 1);
    else unlabelled += 1;
  }
  const showSourceSelect = sourceCounts.size >= 2;

  const unavailable = (o: ChoiceOption) => (!!o.disabled || !!o.hiddenByFilters) && !selected.has(o.id);
  // The "Избрано" block lists what is picked, so search does not need to
  // keep selected rows in the groups (unlike the short layout).
  const matches = (o: ChoiceOption) => {
    if (needle && !o.label.toLowerCase().includes(needle)) return false;
    if (source) {
      const src = srcOf(o);
      if (source === "-" ? src !== null : src !== source) return false;
    }
    return true;
  };

  // Groups keep the order of first appearance in the server's list.
  const order: string[] = [];
  const buckets = new Map<string, { available: ChoiceOption[]; hidden: ChoiceOption[]; selected: number; shown: ChoiceOption[] }>();
  for (const o of choice.options) {
    const key = o.group ?? NO_GROUP;
    let b = buckets.get(key);
    if (!b) {
      b = { available: [], hidden: [], selected: 0, shown: [] };
      buckets.set(key, b);
      order.push(key);
    }
    if (selected.has(o.id)) b.selected += 1;
    if (!matches(o)) continue;
    if (unavailable(o)) b.hidden.push(o);
    else b.available.push(o);
    if (!unavailable(o) || showUnavailable) b.shown.push(o);
  }
  const grouped = order.length > 1;
  const totalAvailable = order.reduce((n, k) => n + buckets.get(k)!.available.length, 0);
  const totalHidden = order.reduce((n, k) => n + buckets.get(k)!.hidden.length, 0);
  const firstKey = order.find((k) => {
    const b = buckets.get(k)!;
    return b.available.length + b.hidden.length > 0;
  });

  function isOpen(key: string): boolean {
    if (key in openState) return openState[key];
    const b = buckets.get(key)!;
    if (searching) return b.available.length + b.hidden.length > 0;
    return b.selected > 0 || key === firstKey;
  }
  function toggleGroup(key: string) {
    setOpenState((s) => ({ ...s, [key]: !isOpen(key) }));
  }
  function resetOpen() {
    setOpenState({});
  }

  function renderRow(option: ChoiceOption) {
    return (
      <li key={option.id} className={preview.itemClass(option)} data-state={optionState(option)}>
        <label className={option.disabled ? "choice-picker__option--disabled" : ""}>
          <input
            type="checkbox"
            checked={selected.has(option.id)}
            disabled={option.disabled}
            aria-disabled={option.disabled || undefined}
            aria-describedby={option.disabled && option.disabledReason ? `${choice.id}::${option.id}::why` : undefined}
            onChange={() => onToggle(choice.id, option.id, choice.count)}
          />
          {option.label}
          {option.hiddenByFilters && (
            <span className="choice-picker__reason"> — {t.common.hiddenByFilters}</span>
          )}
          {option.disabled && option.disabledReason && (
            <span className="choice-picker__reason" id={`${choice.id}::${option.id}::why`}> — {option.disabledReason}</span>
          )}
        </label>
        {preview.button(option)}
        {preview.panel(option)}
      </li>
    );
  }

  return (
    <div className="choice-picker-wrap choice-picker-wrap--long">
      <div className="choice-picker__selected" role="group" aria-label={t.choice.selectedTitle}>
        <p className="choice-picker__selected-title">
          {t.choice.selectedCount(choice.selected.length, choice.count)}
        </p>
        {choice.selected.length > 0 && (
          <ul className="choice-picker__selected-list">
            {choice.selected.map((id) => {
              const label = labelOf.get(id) ?? id;
              return (
                <li key={id}>
                  <span>{label}</span>
                  <button
                    type="button"
                    aria-label={t.choice.removeLabel(label)}
                    onClick={() => onToggle(choice.id, id, choice.count)}
                  >
                    {t.common.remove}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <input
        type="search"
        className="picker-filter"
        aria-label={t.choice.searchLabel(choice.label)}
        placeholder={t.common.search}
        value={filter}
        onChange={(e) => {
          setFilter(e.target.value);
          resetOpen();
        }}
      />
      {showSourceSelect && (
        <select
          className="picker-source"
          aria-label={t.choice.sourceLabel(choice.label)}
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            resetOpen();
          }}
        >
          <option value="">{t.choice.allSources}</option>
          {[...sourceCounts.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([code, n]) => (
            <option key={code} value={code}>
              {code} ({n})
            </option>
          ))}
          {unlabelled > 0 && <option value="-">{t.choice.unlabelled(unlabelled)}</option>}
        </select>
      )}
      {searching && (
        <p role="status" aria-live="polite" className="choice-picker__result-count">
          {totalAvailable + totalHidden === 0 ? t.common.noMatches : t.choice.found(totalAvailable, totalHidden)}
        </p>
      )}
      {grouped ? (
        order.map((key) => {
          const b = buckets.get(key)!;
          if (b.available.length + b.hidden.length === 0) return null;
          const open = isOpen(key);
          const listId = `${uid}-${key || "other"}`;
          return (
            <div key={key} className="choice-picker__section">
              <button
                type="button"
                className="choice-picker__group-toggle"
                aria-expanded={open}
                aria-controls={listId}
                onClick={() => toggleGroup(key)}
              >
                {key === NO_GROUP ? t.choice.other : groupLabel(t, key)} — {t.choice.groupSummary(b.available.length, b.hidden.length, b.selected)}
              </button>
              {open && (
                <ul className="choice-picker" id={listId}>
                  {b.shown.map(renderRow)}
                </ul>
              )}
            </div>
          );
        })
      ) : (
        <ul className="choice-picker">{buckets.get(order[0] ?? NO_GROUP)?.shown.map(renderRow)}</ul>
      )}
      {totalHidden > 0 && (
        <button
          type="button"
          className="choice-picker__toggle-unavailable"
          aria-expanded={showUnavailable}
          onClick={() => setShowUnavailable((v) => !v)}
        >
          {showUnavailable ? t.choice.hideUnavailable : t.choice.showUnavailable(totalHidden)}
        </button>
      )}
    </div>
  );
}

export function ChoicePicker(props: ChoicePickerProps) {
  return props.choice.options.length > LONG_LIST_THRESHOLD ? <LongPicker {...props} /> : <ShortPicker {...props} />;
}
