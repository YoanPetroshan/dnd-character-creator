import { useRef, type ReactNode } from "react";
import { tabAfterKey } from "../../logic/sheetTabs";

export interface TabDef<Id extends string> {
  id: Id;
  label: string;
}

/** WAI-ARIA tabs (automatic activation): role tablist / tab / tabpanel, aria-selected / aria-controls, a roving tabindex,
 *  Left / Right (wrapping), Home and End. Only the selected panel has content; the others stay as empty hidden elements so that
 *  every aria-controls points at something. The tab list scrolls sideways on a narrow screen (CSS). */
export function Tabs<Id extends string>({
  idPrefix,
  label,
  tabs,
  selected,
  onSelect,
  renderPanel,
}: {
  idPrefix: string;
  label: string;
  tabs: TabDef<Id>[];
  selected: Id;
  onSelect: (id: Id) => void;
  renderPanel: (id: Id) => ReactNode;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const current = Math.max(0, tabs.findIndex((t) => t.id === selected));

  function onKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const next = tabAfterKey(current, tabs.length, e.key);
    if (next === null) return;
    e.preventDefault();
    const id = tabs[next].id;
    onSelect(id);
    refs.current[id]?.focus();
  }

  return (
    <div className="tabs" data-tabs={idPrefix}>
      <div className="tabs__list" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`${idPrefix}-tab-${tab.id}`}
            className="tabs__tab"
            data-tab={tab.id}
            aria-selected={tab.id === selected}
            aria-controls={`${idPrefix}-panel-${tab.id}`}
            tabIndex={tab.id === selected ? 0 : -1}
            ref={(el) => {
              refs.current[tab.id] = el;
            }}
            onClick={() => onSelect(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${idPrefix}-panel-${tab.id}`}
          className="tabs__panel"
          data-panel={tab.id}
          aria-labelledby={`${idPrefix}-tab-${tab.id}`}
          hidden={tab.id !== selected}
          tabIndex={0}
        >
          {tab.id === selected ? renderPanel(tab.id) : null}
        </div>
      ))}
    </div>
  );
}
