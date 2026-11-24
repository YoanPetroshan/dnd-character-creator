import { Fragment, useState, type ReactNode } from "react";
import type { CatalogSource } from "../useCatalog";

/** The core books come first, in this order; every other source follows as its own group. */
const CORE_SOURCES = ["PHB", "XPHB", "DMG", "XDMG"];
/** Groups open from the start (the Player's Handbooks); every other book is a closed group with its count (DESIGN-L, 4A). */
const OPEN_SOURCES = new Set(["PHB", "XPHB"]);

export interface BookItem {
  id: string;
  name: string;
  source?: string;
}

interface Group<T> {
  key: string;
  label: string;
  items: T[];
}

/** Groups by source: core books first (PHB 2014, XPHB 2024, DMG, XDMG), then the rest by display name; names alphabetical inside. */
export function groupBySource<T extends BookItem>(list: T[], sources: CatalogSource[], noSourceLabel: string): Group<T>[] {
  const nameOf = new Map(sources.map((x) => [x.id, x.name]));
  const byKey = new Map<string, Group<T>>();
  for (const s of list) {
    const key = s.source ?? "";
    let g = byKey.get(key);
    if (!g) {
      g = { key, label: key ? (nameOf.get(key) ?? key) : noSourceLabel, items: [] };
      byKey.set(key, g);
    }
    g.items.push(s);
  }
  for (const g of byKey.values()) g.items.sort((a, b) => a.name.localeCompare(b.name, "en") || a.id.localeCompare(b.id));
  const core = CORE_SOURCES.flatMap((k) => byKey.get(k) ?? []);
  const rest = [...byKey.values()]
    .filter((g) => !CORE_SOURCES.includes(g.key))
    .sort((a, b) => a.label.localeCompare(b.label) || a.key.localeCompare(b.key));
  return [...core, ...rest];
}

export interface BookPickerLabels {
  search: string;
  searchPlaceholder: string;
  noMatches: string;
  noSourceGroup: string;
  groupSummary: (book: string, n: number) => string;
  change: string;
  changeLabel: (name: string) => string;
  cancel: string;
  /** appended to a picked item the current rules or books hide */
  hidden: string;
}

interface BookPickerProps<T extends BookItem> {
  /** radio group name */
  name: string;
  items: T[];
  sources: CatalogSource[];
  selected: T | undefined;
  /** the picked item is hidden by the current rules or books (it is still shown, marked) */
  selectedHidden: boolean;
  onPick: (id: string) => void;
  labels: BookPickerLabels;
  /** extra controls inside the picked pill (the species eye) and what they open under it */
  pickedExtra?: (item: T) => { button: ReactNode; panel: ReactNode };
}

/** One way to pick one thing from many books (Species, Background; DESIGN-L): a search, titled book groups (the
 *  Player's Handbooks open, the rest closed with a count), text-wide pills. Once picked, the list folds into the
 *  picked pill and a "Change" button. */
export function BookPicker<T extends BookItem>({ name, items, sources, selected, selectedHidden, onPick, labels, pickedExtra }: BookPickerProps<T>) {
  const [changing, setChanging] = useState(false);
  const [filter, setFilter] = useState("");

  if (selected && !changing) {
    const extra = pickedExtra?.(selected);
    return (
      <div className="book-picked">
        <ul className="book-chips">
          <li className="book-chip">
            <label className="book-chip__label">
              <input type="radio" name={name} checked readOnly />
              {selected.name}
              {selectedHidden ? ` (${labels.hidden})` : ""}
            </label>
            {extra?.button}
          </li>
          {extra?.panel && <li className="book-panel">{extra.panel}</li>}
        </ul>
        <button type="button" className="book-picked__change" aria-label={labels.changeLabel(selected.name)} onClick={() => setChanging(true)}>
          {labels.change}
        </button>
      </div>
    );
  }

  const needle = filter.trim().toLowerCase();
  const shown = needle ? items.filter((s) => s.id === selected?.id || s.name.toLowerCase().includes(needle)) : items;
  const groups = groupBySource(shown, sources, labels.noSourceGroup);
  const anyCoreOpen = groups.some((x) => OPEN_SOURCES.has(x.key));
  return (
    <>
      <input
        type="search"
        className="picker-filter"
        aria-label={labels.search}
        placeholder={labels.searchPlaceholder}
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      {needle && shown.length === 0 && <p>{labels.noMatches}</p>}
      <ul className="book-groups">
        {groups.map((g, index) => {
          const chips = (
            <ul className="book-chips" aria-label={g.label}>
              {g.items.map((s) => (
                <Fragment key={s.id}>
                  <li className="book-chip">
                    <label className="book-chip__label">
                      <input
                        type="radio"
                        name={name}
                        checked={selected?.id === s.id}
                        onChange={() => {
                          onPick(s.id);
                          setChanging(false);
                        }}
                      />
                      {s.name}
                      {selectedHidden && s.id === selected?.id ? ` (${labels.hidden})` : ""}
                    </label>
                  </li>
                </Fragment>
              ))}
            </ul>
          );
          // a book's group is open when it is a Player's Handbook (without either handbook, e.g. SRD only, the first
          // group), while searching, or when it holds the pick
          const open =
            OPEN_SOURCES.has(g.key) || (index === 0 && !anyCoreOpen) || !!needle || g.items.some((s) => s.id === selected?.id);
          return (
            <li key={g.key} className="book-group">
              {open ? (
                <>
                  <h3 className="book-group__title">{g.label}</h3>
                  {chips}
                </>
              ) : (
                <details className="book-group__more">
                  <summary>{labels.groupSummary(g.label, g.items.length)}</summary>
                  {chips}
                </details>
              )}
            </li>
          );
        })}
      </ul>
      {selected && (
        <button type="button" className="book-picked__change" onClick={() => setChanging(false)}>
          {labels.cancel}
        </button>
      )}
    </>
  );
}
