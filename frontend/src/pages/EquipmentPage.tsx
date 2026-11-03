import { useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useItems } from "../useItems";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";

const CATEGORIES = [
  { value: "", label: "Всички" },
  { value: "weapon", label: "Оръжия" },
  { value: "armor", label: "Брони" },
  { value: "adventuring-gear", label: "Снаряжение" },
  { value: "tools", label: "Инструменти" },
  { value: "mounts-and-vehicles", label: "Превозни средства" },
];

/** RP8: the items of a 2024 equipment pack, one plain line ("Backpack, Oil ×2"). */
function contentsText(contents: { name: string; qty: number }[]): string {
  return contents.map((c) => (c.qty !== 1 ? `${c.name} ×${c.qty}` : c.name)).join(", ");
}

export function EquipmentPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error } = useResolutionContext();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const items = useItems(category, query, draft.ruleset, draft.sources);

  if (!resolution) return <div className="page">{error ? null : "Зареждане…"}</div>;

  const equipmentChoices = resolution.choices.filter((c) => c.source.kind === "equipment");

  function handleChoiceChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "equipment", choiceId, optionId, count });
  }

  const sheetEquipment = resolution.sheet.equipment;

  return (
    <div className="page">
      <h1>Equipment {loading && "…"}</h1>
      <StepProblems step="equipment" />

      {equipmentChoices.length === 0 && <p>Няма избори за стартова екипировка.</p>}
      {equipmentChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChoiceChange} defaultExpanded={choice.id === firstPendingId(equipmentChoices)} />
      ))}

      {sheetEquipment.granted.length > 0 && (
        <div className="equipment-section">
          <h2>Получена екипировка</h2>
          <ul>
            {sheetEquipment.granted.map((g, i) => (
              <li key={`${g.itemId}-${i}`}>
                {g.name} ×{g.qty}
                {g.contents && g.contents.length > 0 && ` (съдържа: ${contentsText(g.contents)})`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sheetEquipment.chosen.length > 0 && (
        <div className="equipment-section">
          <h2>Избрана екипировка</h2>
          <ul>
            {sheetEquipment.chosen.map((c, i) => (
              <li key={`${c.itemId}-${i}`}>
                {c.name}
                {c.qty !== 1 ? ` ×${c.qty}` : ""}
                {c.contents && c.contents.length > 0 && ` (съдържа: ${contentsText(c.contents)})`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sheetEquipment.slots && (
        <div className="equipment-section">
          <h2>Носено и държано</h2>
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
            Задай ръчно какво нося
          </label>
          {draft.equipment.worn && (
            <>
              <label>
                Броня
                <select
                  value={draft.equipment.worn.armor ?? ""}
                  onChange={(e) =>
                    dispatch({ type: "SET_WORN", worn: { ...draft.equipment.worn, armor: e.target.value || null } })
                  }
                >
                  <option value="">Без броня</option>
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
                Щит
              </label>
            </>
          )}
          <label>
            <input
              type="checkbox"
              checked={!!draft.equipment.wielded}
              onChange={(e) => dispatch({ type: "SET_WIELDED", wielded: e.target.checked ? { main: null, off: null } : undefined })}
            />
            Задай ръчно какво държа в ръцете
          </label>
          {draft.equipment.wielded && (
            <>
              {(["main", "off"] as const).map((hand) => (
                <label key={hand}>
                  {hand === "main" ? "Основна ръка" : "Свободна ръка"}
                  <select
                    value={draft.equipment.wielded?.[hand] ?? ""}
                    onChange={(e) =>
                      dispatch({ type: "SET_WIELDED", wielded: { ...draft.equipment.wielded, [hand]: e.target.value || null } })
                    }
                  >
                    <option value="">Празна</option>
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

      <h2>Предмети</h2>
      <input type="search" aria-label="Търсене на предмети" placeholder="Търсене…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select aria-label="Категория" value={category} onChange={(e) => setCategory(e.target.value)}>
        {CATEGORIES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
      {items.error && (
        <p>
          Грешка: {items.error}{" "}
          <button type="button" onClick={items.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="item-browser-list">
        {items.items.map((item) => (
          <li key={item.id}>
            <span>{item.name}</span>
            <button type="button" aria-label={`Добави ${item.name}`} onClick={() => dispatch({ type: "ADD_ITEM", itemId: item.id })}>
              Add
            </button>
          </li>
        ))}
      </ul>

      <h2>Инвентар</h2>
      {sheetEquipment.added.length === 0 && <p>Няма добавени предмети.</p>}
      {sheetEquipment.added.length > 0 && (
        <ul className="inventory-list">
          {sheetEquipment.added.map((entry) => (
            <li key={entry.itemId}>
              <span>
                {entry.name} ×{entry.qty}
                {entry.contents && entry.contents.length > 0 && ` (съдържа: ${contentsText(entry.contents)})`}
              </span>
              <label>
                <input
                  type="checkbox"
                  checked={entry.equipped}
                  onChange={() => dispatch({ type: "TOGGLE_EQUIPPED", itemId: entry.itemId })}
                />
                Екипиран
              </label>
              <button type="button" aria-label={`Премахни ${entry.name}`} onClick={() => dispatch({ type: "REMOVE_ITEM", itemId: entry.itemId })}>
                Премахни
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
