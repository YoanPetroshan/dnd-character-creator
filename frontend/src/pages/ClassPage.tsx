import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { useSpells } from "../useSpells";
import { ChoiceCard } from "../components/ChoiceCard";

type ClassTab = "features" | "spells";

function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known");
}

const SPELL_LEVELS = [
  { value: "", label: "Всички нива" },
  { value: "0", label: "Трикове" },
  { value: "1", label: "1-во ниво" },
];

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();
  const [tab, setTab] = useState<ClassTab>("features");
  const [spellLevel, setSpellLevel] = useState("");
  const [spellQuery, setSpellQuery] = useState("");

  const selectedClassId = draft.classes[0]?.classId;
  const classChoices = resolution ? resolution.choices.filter((c) => c.source.kind === "class") : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";
  const spells = useSpells(hasSpells ? (selectedClassId ?? "") : "", spellLevel, spellQuery);

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

  return (
    <div className="page">
      <h1>Клас {loading && "…"}</h1>
      {catalog.error && (
        <p>
          Грешка при зареждане на класовете: {catalog.error}{" "}
          <button type="button" onClick={catalog.retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="picker-list">
        {catalog.classes.map((c) => (
          <li key={c.id}>
            <label>
              <input
                type="radio"
                name="class"
                checked={selectedClassId === c.id}
                onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
              />
              {c.name} (d{c.hitDie})
            </label>
          </li>
        ))}
      </ul>

      {selectedClassId && (
        <div className="tab-bar" role="tablist">
          <button type="button" role="tab" aria-selected={effectiveTab === "features"} onClick={() => setTab("features")}>
            Способности
          </button>
          {hasSpells && (
            <button type="button" role="tab" aria-selected={effectiveTab === "spells"} onClick={() => setTab("spells")}>
              Заклинания
            </button>
          )}
        </div>
      )}

      {selectedClassId && effectiveTab === "features" && (
        <>
          {!loading && featureChoices.length === 0 && <p>Няма избори за този клас.</p>}
          {featureChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
        </>
      )}

      {selectedClassId && effectiveTab === "spells" && (
        <>
          {spellChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}

          <h2>Списък със заклинания</h2>
          <input
            type="text"
            placeholder="Търсене…"
            value={spellQuery}
            onChange={(e) => setSpellQuery(e.target.value)}
          />
          <select value={spellLevel} onChange={(e) => setSpellLevel(e.target.value)}>
            {SPELL_LEVELS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
          {spells.error && (
            <p>
              Грешка: {spells.error}{" "}
              <button type="button" onClick={spells.retry}>
                Опитай пак
              </button>
            </p>
          )}
          <ul className="spell-library-list">
            {spells.spells.map((spell) => (
              <li key={spell.id} className="spell-library-card">
                <div className="spell-library-card__header">
                  <span className="spell-library-card__name">{spell.name}</span>
                  <span className="spell-library-card__level">{spell.level === 0 ? "Трик" : `${spell.level} ниво`}</span>
                </div>
                <div className="spell-library-card__meta">
                  {spell.school && <span>{spell.school}</span>}
                  {spell.castingTime && <span>{spell.castingTime}</span>}
                  {spell.range && <span>{spell.range}</span>}
                  {spell.components.length > 0 && <span>{spell.components.join(", ")}</span>}
                  {spell.duration && <span>{spell.duration}</span>}
                  {spell.concentration && <span>Концентрация</span>}
                  {spell.ritual && <span>Ритуал</span>}
                </div>
                <p className="spell-library-card__desc">{spell.desc}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
