import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";

export function BackgroundPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const selectedBackgroundId = draft.background.id;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "background", choiceId, selected });
  }

  const choices = resolution ? resolution.choices.filter((c) => c.source.kind === "background") : [];

  return (
    <div className="page">
      <h1>Background {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <select
        value={selectedBackgroundId ?? ""}
        onChange={(e) => {
          if (e.target.value) dispatch({ type: "SET_BACKGROUND", backgroundId: e.target.value });
        }}
      >
        <option value="">— избери background —</option>
        {catalog.backgrounds.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
      </select>
      {selectedBackgroundId && !loading && choices.length === 0 && <p>Няма избори за този background.</p>}
      {choices.map((choice) => (
        <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
      ))}

      <details className="details-section">
        <summary>Данни за героя</summary>
        <label>
          Мирогледие
          <select value={draft.details.alignment ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "alignment", value: e.target.value })}>
            <option value="">—</option>
            <option value="Lawful Good">Законен добър</option>
            <option value="Neutral Good">Неутрален добър</option>
            <option value="Chaotic Good">Хаотичен добър</option>
            <option value="Lawful Neutral">Законен неутрален</option>
            <option value="True Neutral">Истински неутрален</option>
            <option value="Chaotic Neutral">Хаотичен неутрален</option>
            <option value="Lawful Evil">Законен зъл</option>
            <option value="Neutral Evil">Неутрален зъл</option>
            <option value="Chaotic Evil">Хаотичен зъл</option>
          </select>
        </label>
        <label>
          Вяра/Божество
          <input type="text" value={draft.details.faith ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "faith", value: e.target.value })} />
        </label>
        <label>
          Начин на живот
          <input type="text" value={draft.details.lifestyle ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "lifestyle", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Физически характеристики</summary>
        <label>
          Възраст
          <input type="text" value={draft.details.age ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "age", value: e.target.value })} />
        </label>
        <label>
          Височина
          <input type="text" value={draft.details.height ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "height", value: e.target.value })} />
        </label>
        <label>
          Тегло
          <input type="text" value={draft.details.weight ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "weight", value: e.target.value })} />
        </label>
        <label>
          Очи
          <input type="text" value={draft.details.eyes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "eyes", value: e.target.value })} />
        </label>
        <label>
          Кожа
          <input type="text" value={draft.details.skin ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "skin", value: e.target.value })} />
        </label>
        <label>
          Коса
          <input type="text" value={draft.details.hair ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "hair", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Личност</summary>
        <label>
          Черти на характера
          <textarea value={draft.details.personalityTraits ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "personalityTraits", value: e.target.value })} />
        </label>
        <label>
          Идеали
          <textarea value={draft.details.ideals ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "ideals", value: e.target.value })} />
        </label>
        <label>
          Връзки
          <textarea value={draft.details.bonds ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "bonds", value: e.target.value })} />
        </label>
        <label>
          Слабости
          <textarea value={draft.details.flaws ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "flaws", value: e.target.value })} />
        </label>
      </details>

      <details className="details-section">
        <summary>Бележки</summary>
        <label>
          Предистория
          <textarea value={draft.details.backstory ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "backstory", value: e.target.value })} />
        </label>
        <label>
          Организации
          <textarea value={draft.details.organizations ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "organizations", value: e.target.value })} />
        </label>
        <label>
          Съюзници
          <textarea value={draft.details.allies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "allies", value: e.target.value })} />
        </label>
        <label>
          Врагове
          <textarea value={draft.details.enemies ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "enemies", value: e.target.value })} />
        </label>
        <label>
          Допълнителни бележки
          <textarea value={draft.details.notes ?? ""} onChange={(e) => dispatch({ type: "SET_DETAIL", field: "notes", value: e.target.value })} />
        </label>
      </details>
    </div>
  );
}
