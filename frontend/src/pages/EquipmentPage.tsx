import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useItems } from "../useItems";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";
import { ItemDetailBody, useItemDetails } from "../components/ItemDetailBody";

/** Values of the category filter; the labels are `t.equipmentPage.categories[value || "all"]`. */
const CATEGORIES = ["", "weapon", "armor", "adventuring-gear", "tools", "mounts-and-vehicles"];

/** The starting-equipment cards come from the class and from the background: each gets its own heading. */
const SOURCES = [
  { prefix: "class:", title: "fromClass" },
  { prefix: "background:", title: "fromBackground" },
] as const;

interface SlotFieldProps {
  label: string;
  placeholder: string;
  options: { itemId: string; name: string }[];
  value: string;
  onChange: (value: string) => void;
}

/** A worn or held slot. A dropdown only where there is a choice: with nothing to pick the placeholder is plain text,
 *  with exactly one thing it is a toggle row (take it or leave it). */
function SlotField({ label, placeholder, options, value, onChange }: SlotFieldProps) {
  if (options.length === 0) return <p className="equipment-field equipment-field--plain">{`${label}: ${placeholder}`}</p>;
  if (options.length === 1) {
    const only = options[0];
    return (
      <label className="equipment-toggle">
        <input type="checkbox" checked={value === only.itemId} onChange={(e) => onChange(e.target.checked ? only.itemId : "")} />
        {`${label}: ${only.name}`}
      </label>
    );
  }
  return (
    <label className="equipment-field">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.itemId} value={o.itemId}>
            {o.name}
          </option>
        ))}
      </select>
    </label>
  );
}

/** RP8: the items of a 2024 equipment pack, one plain line ("Backpack, Oil ×2"). */
function contentsText(contents: { name: string; qty: number }[]): string {
  return contents.map((c) => (c.qty !== 1 ? `${c.name} ×${c.qty}` : c.name)).join(", ");
}

/** The eye button of an item row and its panel. `rowKey` is the row (the same item can be in several lists at once). */
function useItemEyes(ruleset: string, label: (name: string) => string) {
  const { detailOf, loadDetail } = useItemDetails(ruleset);
  const [open, setOpen] = useState<Set<string>>(new Set());
  function toggle(rowKey: string, itemId: string) {
    const next = new Set(open);
    if (next.has(rowKey)) next.delete(rowKey);
    else {
      next.add(rowKey);
      loadDetail(itemId);
    }
    setOpen(next);
  }
  const button = (rowKey: string, itemId: string, name: string) => (
    <button
      type="button"
      className="spell-eye item-eye"
      aria-label={label(name)}
      aria-expanded={open.has(rowKey)}
      onClick={() => toggle(rowKey, itemId)}
    />
  );
  const panel = (rowKey: string, itemId: string) =>
    open.has(rowKey) && (
      <div className="spell-eye__panel item-eye__panel">
        <ItemDetailBody state={detailOf(itemId)} />
      </div>
    );
  return { button, panel };
}

export function EquipmentPage() {
  const t = useT();
  const ep = t.equipmentPage;
  const eq = t.sheet.equipment;
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  // null = no category picked yet (the list stays closed); "" = "All"
  const [category, setCategory] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const items = useItems(category ?? "", query, draft.ruleset, draft.sources);
  const eyes = useItemEyes(draft.ruleset, ep.showItem);
  // DESIGN-L: the item list shows only after a search or a category pick (all ~250 rows at once were 500+ targets)
  const browsing = category !== null || query.trim() !== "";

  if (!resolution) return <div className="page">{error ? null : t.common.loading}</div>;

  const equipmentChoices = resolution.choices.filter((c) => c.source.kind === "equipment");

  function handleChoiceChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "equipment", choiceId, optionId, count });
  }

  const sheetEquipment = resolution.sheet.equipment;

  return (
    <div className="page">
      <h1>{ep.title} {loading && "…"}</h1>
      <StepProblems step="equipment" />

      {equipmentChoices.length === 0 && <p>{ep.noStartingChoices}</p>}
      {SOURCES.map(({ prefix, title }) => {
        const cards = equipmentChoices.filter((c) => c.id.startsWith(prefix));
        if (cards.length === 0) return null;
        return (
          <section key={prefix} className="equipment-source">
            <h2>{ep[title]}</h2>
            {prefix === "class:" && <p className="equipment-hint">{ep.startingHint}</p>}
            {cards.map((choice) => (
              <ChoiceCard key={choice.id} choice={choice} onToggle={handleChoiceChange} defaultExpanded={choice.id === firstPendingId(equipmentChoices)} />
            ))}
          </section>
        );
      })}
      {equipmentChoices
        .filter((c) => !SOURCES.some(({ prefix }) => c.id.startsWith(prefix)))
        .map((choice) => (
          <ChoiceCard key={choice.id} choice={choice} onToggle={handleChoiceChange} defaultExpanded={choice.id === firstPendingId(equipmentChoices)} />
        ))}

      {(sheetEquipment.granted.length > 0 || sheetEquipment.chosen.length > 0) && (
        <section className="equipment-final">
          <h2>{ep.finalTitle}</h2>
          <p className="equipment-hint">{ep.finalHint}</p>
          {sheetEquipment.granted.length > 0 && (
            <div className="equipment-section">
              <h3>{eq.groups.granted}</h3>
              <ul>
                {sheetEquipment.granted.map((g, i) => (
                  <li key={`${g.itemId}-${i}`}>
                    {g.name} ×{g.qty}
                    {g.contents && g.contents.length > 0 && ` ${ep.contains(contentsText(g.contents))}`}
                    {eyes.button(`granted-${i}`, g.itemId, g.name)}
                    {eyes.panel(`granted-${i}`, g.itemId)}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {sheetEquipment.chosen.length > 0 && (
            <div className="equipment-section">
              <h3>{eq.groups.chosen}</h3>
              <ul>
                {sheetEquipment.chosen.map((c, i) => (
                  <li key={`${c.itemId}-${i}`}>
                    {c.name}
                    {c.qty !== 1 ? ` ×${c.qty}` : ""}
                    {c.contents && c.contents.length > 0 && ` ${ep.contains(contentsText(c.contents))}`}
                    {eyes.button(`chosen-${i}`, c.itemId, c.name)}
                    {eyes.panel(`chosen-${i}`, c.itemId)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <h2>{eq.groups.added}</h2>
      {sheetEquipment.added.length === 0 && <p>{ep.noAdded}</p>}
      {sheetEquipment.added.length > 0 && (
        <ul className="inventory-list">
          {sheetEquipment.added.map((entry) => (
            <li key={entry.itemId}>
              <span>
                {entry.name} ×{entry.qty}
                {entry.contents && entry.contents.length > 0 && ` ${ep.contains(contentsText(entry.contents))}`}
              </span>
              {eyes.button(`added-${entry.itemId}`, entry.itemId, entry.name)}
              <label className="equipment-toggle">
                <input
                  type="checkbox"
                  checked={entry.equipped}
                  onChange={() => dispatch({ type: "TOGGLE_EQUIPPED", itemId: entry.itemId })}
                />
                {ep.equipped}
              </label>
              <button type="button" aria-label={ep.removeLabel(entry.name)} onClick={() => dispatch({ type: "REMOVE_ITEM", itemId: entry.itemId })}>
                {t.common.remove}
              </button>
              {eyes.panel(`added-${entry.itemId}`, entry.itemId)}
            </li>
          ))}
        </ul>
      )}
      <h2>{ep.itemsTitle}</h2>
      <div className="item-search">
        <input type="text" inputMode="search" enterKeyHint="search" aria-label={ep.searchLabel} placeholder={t.common.search} value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>
      <div className="item-categories" role="group" aria-label={ep.categoryLabel}>
        {CATEGORIES.map((value) => (
          <label key={value}>
            <input type="radio" name="item-category" checked={category === value} onChange={() => setCategory(value)} />
            {ep.categories[value || "all"]}
          </label>
        ))}
      </div>
      {items.error && (
        <p>
          {t.common.errorLine(renderMsg(t, items.error))}{" "}
          <button type="button" onClick={items.retry}>
            {t.common.retry}
          </button>
        </p>
      )}
      {!browsing && <p className="equipment-hint">{ep.browseHint}</p>}
      <ul className="item-browser-list">
        {(browsing ? items.items : []).map((item) => (
          <li key={item.id}>
            {eyes.button(`browse-${item.id}`, item.id, item.name)}
            <span>{item.name}</span>
            <button type="button" className="item-add" aria-label={ep.addLabel(item.name)} onClick={() => dispatch({ type: "ADD_ITEM", itemId: item.id })}>
              {ep.add}
            </button>
            {eyes.panel(`browse-${item.id}`, item.id)}
          </li>
        ))}
      </ul>

      {sheetEquipment.slots && (
        <details className="details-section" open={!!draft.equipment.worn || !!draft.equipment.wielded}>
          <summary>{ep.wornAndHeld}</summary>
          <label className="equipment-toggle">
            <input
              type="checkbox"
              checked={!!draft.equipment.worn}
              onChange={(e) =>
                dispatch({
                  type: "SET_WORN",
                  worn: e.target.checked
                    ? { armor: sheetEquipment.slots?.current.armor ?? null, shield: sheetEquipment.slots?.current.shield ?? false }
                    : undefined,
                })
              }
            />
            {ep.setWornManually}
          </label>
          {draft.equipment.worn && (
            <>
              <SlotField
                label={ep.armor}
                placeholder={ep.noArmor}
                options={sheetEquipment.slots.armor}
                value={draft.equipment.worn.armor ?? ""}
                onChange={(value) => dispatch({ type: "SET_WORN", worn: { ...draft.equipment.worn, armor: value || null } })}
              />
              <label className="equipment-toggle">
                <input
                  type="checkbox"
                  checked={draft.equipment.worn.shield == null ? !!sheetEquipment.worn?.shield : draft.equipment.worn.shield}
                  onChange={(e) => dispatch({ type: "SET_WORN", worn: { ...draft.equipment.worn, shield: e.target.checked } })}
                />
                {ep.shield}
              </label>
            </>
          )}
          <label className="equipment-toggle">
            <input
              type="checkbox"
              checked={!!draft.equipment.wielded}
              onChange={(e) => dispatch({ type: "SET_WIELDED", wielded: e.target.checked ? { main: null, off: null } : undefined })}
            />
            {ep.setWieldedManually}
          </label>
          {draft.equipment.wielded && (
            <>
              {(["main", "off"] as const).map((hand) => (
                <SlotField
                  key={hand}
                  label={hand === "main" ? ep.mainHand : ep.offHand}
                  placeholder={ep.emptyHand}
                  options={sheetEquipment.slots!.hands.filter((o) => hand === "off" || o.kind !== "shield")}
                  value={draft.equipment.wielded?.[hand] ?? ""}
                  onChange={(value) => dispatch({ type: "SET_WIELDED", wielded: { ...draft.equipment.wielded, [hand]: value || null } })}
                />
              ))}
            </>
          )}
        </details>
      )}
    </div>
  );
}
