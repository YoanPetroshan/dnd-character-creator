import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useItems } from "../useItems";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";

/** Values of the category filter; the labels are `t.equipmentPage.categories[value || "all"]`. */
const CATEGORIES = ["", "weapon", "armor", "adventuring-gear", "tools", "mounts-and-vehicles"];

/** RP8: the items of a 2024 equipment pack, one plain line ("Backpack, Oil ×2"). */
function contentsText(contents: { name: string; qty: number }[]): string {
  return contents.map((c) => (c.qty !== 1 ? `${c.name} ×${c.qty}` : c.name)).join(", ");
}

export function EquipmentPage() {
  const t = useT();
  const ep = t.equipmentPage;
  const eq = t.sheet.equipment;
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const items = useItems(category, query, draft.ruleset, draft.sources);

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
      {equipmentChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChoiceChange} defaultExpanded={choice.id === firstPendingId(equipmentChoices)} />
      ))}

      {sheetEquipment.granted.length > 0 && (
        <div className="equipment-section">
          <h2>{eq.groups.granted}</h2>
          <ul>
            {sheetEquipment.granted.map((g, i) => (
              <li key={`${g.itemId}-${i}`}>
                {g.name} ×{g.qty}
                {g.contents && g.contents.length > 0 && ` ${ep.contains(contentsText(g.contents))}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sheetEquipment.chosen.length > 0 && (
        <div className="equipment-section">
          <h2>{eq.groups.chosen}</h2>
          <ul>
            {sheetEquipment.chosen.map((c, i) => (
              <li key={`${c.itemId}-${i}`}>
                {c.name}
                {c.qty !== 1 ? ` ×${c.qty}` : ""}
                {c.contents && c.contents.length > 0 && ` ${ep.contains(contentsText(c.contents))}`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sheetEquipment.slots && (
        <div className="equipment-section">
          <h2>{ep.wornAndHeld}</h2>
          <label>
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
              <label>
                {ep.armor}
                <select
                  value={draft.equipment.worn.armor ?? ""}
                  onChange={(e) =>
                    dispatch({ type: "SET_WORN", worn: { ...draft.equipment.worn, armor: e.target.value || null } })
                  }
                >
                  <option value="">{ep.noArmor}</option>
                  {sheetEquipment.slots.armor.map((o) => (
                    <option key={o.itemId} value={o.itemId}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={draft.equipment.worn.shield == null ? !!sheetEquipment.worn?.shield : draft.equipment.worn.shield}
                  onChange={(e) => dispatch({ type: "SET_WORN", worn: { ...draft.equipment.worn, shield: e.target.checked } })}
                />
                {ep.shield}
              </label>
            </>
          )}
          <label>
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
                <label key={hand}>
                  {hand === "main" ? ep.mainHand : ep.offHand}
                  <select
                    value={draft.equipment.wielded?.[hand] ?? ""}
                    onChange={(e) =>
                      dispatch({ type: "SET_WIELDED", wielded: { ...draft.equipment.wielded, [hand]: e.target.value || null } })
                    }
                  >
                    <option value="">{ep.emptyHand}</option>
                    {sheetEquipment.slots!.hands
                      .filter((o) => hand === "off" || o.kind !== "shield")
                      .map((o) => (
                        <option key={o.itemId} value={o.itemId}>
                          {o.name}
                        </option>
                      ))}
                  </select>
                </label>
              ))}
            </>
          )}
        </div>
      )}

      <h2>{ep.itemsTitle}</h2>
      <input type="text" inputMode="search" enterKeyHint="search" aria-label={ep.searchLabel} placeholder={t.common.search} value={query} onChange={(e) => setQuery(e.target.value)} />
      <select aria-label={ep.categoryLabel} value={category} onChange={(e) => setCategory(e.target.value)}>
        {CATEGORIES.map((value) => (
          <option key={value} value={value}>
            {ep.categories[value || "all"]}
          </option>
        ))}
      </select>
      {items.error && (
        <p>
          {t.common.errorLine(renderMsg(t, items.error))}{" "}
          <button type="button" onClick={items.retry}>
            {t.common.retry}
          </button>
        </p>
      )}
      <ul className="item-browser-list">
        {items.items.map((item) => (
          <li key={item.id}>
            <span>{item.name}</span>
            <button type="button" aria-label={ep.addLabel(item.name)} onClick={() => dispatch({ type: "ADD_ITEM", itemId: item.id })}>
              {ep.add}
            </button>
          </li>
        ))}
      </ul>

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
              <label>
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
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
