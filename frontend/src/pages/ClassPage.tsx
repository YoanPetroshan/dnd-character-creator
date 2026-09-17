import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";
import { SpellLibrary } from "../components/SpellLibrary";

type ClassTab = "features" | "spells";

function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known");
}

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();
  const [tab, setTab] = useState<ClassTab>("features");

  const selectedClassId = draft.classes[0]?.classId;
  const classChoices = resolution ? resolution.choices.filter((c) => c.source.kind === "class") : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";

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
          <button
            type="button"
            id="tab-features"
            role="tab"
            aria-selected={effectiveTab === "features"}
            aria-controls="panel-features"
            onClick={() => setTab("features")}
          >
            Способности
          </button>
          {hasSpells && (
            <button
              type="button"
              id="tab-spells"
              role="tab"
              aria-selected={effectiveTab === "spells"}
              aria-controls="panel-spells"
              onClick={() => setTab("spells")}
            >
              Заклинания
            </button>
          )}
        </div>
      )}

      {selectedClassId && effectiveTab === "features" && (
        <div id="panel-features" role="tabpanel" aria-labelledby="tab-features">
          {!loading && featureChoices.length === 0 && <p>Няма избори за този клас.</p>}
          {featureChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
        </div>
      )}

      {selectedClassId && effectiveTab === "spells" && (
        <div id="panel-spells" role="tabpanel" aria-labelledby="tab-spells">
          {spellChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}

          <SpellLibrary key={selectedClassId} classId={selectedClassId} />
        </div>
      )}
    </div>
  );
}
