import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useItems } from "../useItems";
import { ChoiceCard } from "../components/ChoiceCard";

const CATEGORIES = [
  { value: "", label: "Всички" },
  { value: "weapon", label: "Оръжия" },
  { value: "armor", label: "Брони" },
  { value: "adventuring-gear", label: "Снаряжение" },
  { value: "tools", label: "Инструменти" },
  { value: "mounts-and-vehicles", label: "Превозни средства" },
];

export function EquipmentPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const items = useItems(category, query, draft.ruleset, draft.sources);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );
  if (!resolution) return <div className="page">Зареждане…</div>;

  const equipmentChoices = resolution.choices.filter((c) => c.source.kind === "equipment");

  function handleChoiceChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "equipment", choiceId, optionId, count });
  }

  const sheetEquipment = resolution.sheet.equipment;

  return (
    <div className="page">
      <h1>Equipment {loading && "…"}</h1>

      {equipmentChoices.length === 0 && <p>Няма избори за стартова екипировка.</p>}
      {equipmentChoices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onToggle={handleChoiceChange} />
      ))}

      {sheetEquipment.granted.length > 0 && (
        <div className="equipment-section">
          <h2>Получена екипировка</h2>
          <ul>
            {sheetEquipment.granted.map((g, i) => (
              <li key={`${g.itemId}-${i}`}>
                {g.name} ×{g.qty}
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
              <li key={`${c.itemId}-${i}`}>{c.name}</li>
            ))}
          </ul>
        </div>
      )}

      <h2>Предмети</h2>
      <input type="text" placeholder="Търсене…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select value={category} onChange={(e) => setCategory(e.target.value)}>
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
            <button type="button" onClick={() => dispatch({ type: "ADD_ITEM", itemId: item.id })}>
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
              </span>
              <label>
                <input
                  type="checkbox"
                  checked={entry.equipped}
                  onChange={() => dispatch({ type: "TOGGLE_EQUIPPED", itemId: entry.itemId })}
                />
                Екипиран
              </label>
              <button type="button" onClick={() => dispatch({ type: "REMOVE_ITEM", itemId: entry.itemId })}>
                Премахни
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
