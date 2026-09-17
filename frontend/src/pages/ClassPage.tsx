import { useEffect, useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalog } from "../useCatalog";
import { ChoiceCard } from "../components/ChoiceCard";
import { SpellLibrary } from "../components/SpellLibrary";

type ClassTab = "features" | "spells";

function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known");
}

interface ClassDetail {
  subclasses: { index: string; name: string }[]; // "index", not "id" — raw SRD class object, unmapped
  levelFeatureCounts: Record<string, number>;
  subclassUnlockLevel: number | null;
}

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalog();
  const [tab, setTab] = useState<ClassTab>("features");
  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);

  const selectedClassId = draft.classes[0]?.classId;
  const classLevel = draft.classes[0]?.level ?? 1;

  useEffect(() => {
    if (!selectedClassId) {
      setClassDetail(null);
      return;
    }
    let cancelled = false;
    fetch(`/api/catalog/class/${selectedClassId}`)
      .then((r) => r.json())
      .then((data: ClassDetail) => {
        if (!cancelled) setClassDetail(data);
      })
      .catch(() => {
        if (!cancelled) setClassDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedClassId]);

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
        <label>
          Ниво
          <input
            type="number"
            min={1}
            max={20}
            value={classLevel}
            onChange={(e) => {
              const parsed = parseInt(e.target.value, 10);
              if (!Number.isNaN(parsed)) dispatch({ type: "SET_CLASS_LEVEL", level: parsed });
            }}
          />
        </label>
      )}

      {selectedClassId &&
        classDetail &&
        classDetail.subclassUnlockLevel !== null &&
        classLevel >= classDetail.subclassUnlockLevel && (
          <label>
            Подклас
            <select
              value={draft.classes[0]?.subclassId ?? ""}
              onChange={(e) => {
                if (e.target.value) dispatch({ type: "SET_SUBCLASS", subclassId: e.target.value });
              }}
            >
              <option value="">— избери подклас —</option>
              {classDetail.subclasses.map((s) => (
                <option key={s.index} value={s.index}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
        )}

      {selectedClassId && classDetail && (
        <p className="higher-levels-teaser">
          Налични на по-високи нива:{" "}
          {Object.entries(classDetail.levelFeatureCounts)
            .filter(([lvl]) => Number(lvl) > classLevel)
            .reduce((sum, [, count]) => sum + count, 0)}
        </p>
      )}

      {selectedClassId && (
        <div className="hp-summary">
          <strong>Точки живот:</strong>{" "}
          {resolution ? String(resolution.derived.hitPointMax ?? "—") : "—"}
        </div>
      )}

      {selectedClassId && draft.preferences.hitPointType === "manual" && classLevel >= 2 && (
        <div className="hp-rolls">
          <h3>Хвърляния за точки живот</h3>
          {Array.from({ length: classLevel - 1 }, (_, i) => i + 2).map((lvl) => (
            <label key={lvl}>
              Ниво {lvl}
              <input
                type="number"
                min={1}
                value={draft.classes[0]?.hpRolls?.[String(lvl)] ?? ""}
                onChange={(e) => {
                  const parsed = parseInt(e.target.value, 10);
                  if (!Number.isNaN(parsed)) dispatch({ type: "SET_HP_ROLL", level: lvl, value: parsed });
                }}
              />
            </label>
          ))}
        </div>
      )}

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
