import { useEffect, useState } from "react";
import { useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
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
  hit_die?: number; // raw SRD class object field, spread into this response as-is
}

function ClassBlock({ classId, isPrimary }: { classId: string; isPrimary: boolean }) {
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const [tab, setTab] = useState<ClassTab>("features");
  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);

  const classEntry = draft.classes.find((c) => c.classId === classId);
  const classLevel = classEntry?.level ?? 1;

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/catalog/class/${classId}`)
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
  }, [classId]);

  const classChoices = resolution
    ? resolution.choices.filter(
        (c) => (c.source.kind === "class" || c.source.kind === "feat") && c.id.startsWith(`class:${classId}:`)
      )
    : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";

  const tabFeaturesId = `tab-features-${classId}`;
  const panelFeaturesId = `panel-features-${classId}`;
  const tabSpellsId = `tab-spells-${classId}`;
  const panelSpellsId = `panel-spells-${classId}`;

  function handleChange(choiceId: string, selected: string[]) {
    dispatch({ type: "SET_CHOICE_SELECTION", source: "class", choiceId, selected });
  }

  return (
    <div className="class-block">
      <h2>
        {classId}{" "}
        {!isPrimary && (
          <button type="button" onClick={() => dispatch({ type: "REMOVE_CLASS", classId })}>
            ✕ Премахни
          </button>
        )}
      </h2>

      <label>
        Ниво
        <input
          type="number"
          min={1}
          max={20}
          value={classLevel}
          onChange={(e) => {
            const parsed = parseInt(e.target.value, 10);
            if (!Number.isNaN(parsed)) dispatch({ type: "SET_CLASS_LEVEL", classId, level: parsed });
          }}
        />
      </label>

      {classDetail && classDetail.subclassUnlockLevel !== null && classLevel >= classDetail.subclassUnlockLevel && (
        <label>
          Подклас
          <select
            value={classEntry?.subclassId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBCLASS", classId, subclassId: e.target.value || undefined })}
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

      {classDetail && (
        <p className="higher-levels-teaser">
          Способности на по-високи нива:{" "}
          {Object.entries(classDetail.levelFeatureCounts)
            .filter(([lvl]) => Number(lvl) > classLevel)
            .reduce((sum, [, count]) => sum + count, 0)}
        </p>
      )}

      {draft.preferences.hitPointType === "manual" && classLevel >= 2 && (
        <div className="hp-rolls">
          <h3>Хвърляния за точки живот</h3>
          {Array.from({ length: classLevel - 1 }, (_, i) => i + 2).map((lvl) => (
            <label key={lvl}>
              Ниво {lvl}
              <input
                type="number"
                min={1}
                placeholder={
                  classDetail?.hit_die !== undefined ? String(Math.floor(classDetail.hit_die / 2) + 1) : undefined
                }
                value={classEntry?.hpRolls?.[String(lvl)] ?? ""}
                onChange={(e) => {
                  const parsed = parseInt(e.target.value, 10);
                  if (!Number.isNaN(parsed)) dispatch({ type: "SET_HP_ROLL", classId, level: lvl, value: parsed });
                }}
              />
            </label>
          ))}
        </div>
      )}

      <div className="tab-bar" role="tablist">
        <button
          type="button"
          id={tabFeaturesId}
          role="tab"
          aria-selected={effectiveTab === "features"}
          aria-controls={panelFeaturesId}
          onClick={() => setTab("features")}
        >
          Способности
        </button>
        {hasSpells && (
          <button
            type="button"
            id={tabSpellsId}
            role="tab"
            aria-selected={effectiveTab === "spells"}
            aria-controls={panelSpellsId}
            onClick={() => setTab("spells")}
          >
            Заклинания
          </button>
        )}
      </div>

      {effectiveTab === "features" && (
        <div id={panelFeaturesId} role="tabpanel" aria-labelledby={tabFeaturesId}>
          {!loading && featureChoices.length === 0 && <p>Няма избори за този клас.</p>}
          {featureChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}
        </div>
      )}

      {effectiveTab === "spells" && (
        <div id={panelSpellsId} role="tabpanel" aria-labelledby={tabSpellsId}>
          {spellChoices.map((choice) => (
            <ChoiceCard key={choice.id} choice={choice} onChange={handleChange} />
          ))}

          <SpellLibrary key={classId} classId={classId} />
        </div>
      )}
    </div>
  );
}

export function ClassPage() {
  const { draft, dispatch } = useDraft();
  const { resolution, loading, error, retry } = useResolutionContext();
  const catalog = useCatalogContext();

  if (error)
    return (
      <div className="page">
        <p>Грешка: {error}</p>
        <button type="button" onClick={retry}>
          Опитай пак
        </button>
      </div>
    );

  const takenClassIds = new Set(draft.classes.map((c) => c.classId));
  const primaryClassId = draft.classes[0]?.classId;

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

      {draft.classes.length <= 1 && (
        <ul className="picker-list">
          {catalog.classes.map((c) => (
            <li key={c.id}>
              <label>
                <input
                  type="radio"
                  name="class"
                  checked={c.id === primaryClassId}
                  onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
                />
                {c.name} (d{c.hitDie})
              </label>
            </li>
          ))}
        </ul>
      )}

      {primaryClassId && (
        <div className="hp-summary">
          <strong>Точки живот:</strong> {resolution ? String(resolution.derived.hitPointMax ?? "—") : "—"}
        </div>
      )}

      {draft.classes.map((c, i) => (
        <ClassBlock key={c.classId} classId={c.classId} isPrimary={i === 0} />
      ))}

      {primaryClassId && (
        <div className="add-class">
          <h3>+ Добави клас</h3>
          <ul className="picker-list">
            {catalog.classes
              .filter((c) => !takenClassIds.has(c.id))
              .map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => dispatch({ type: "ADD_CLASS", classId: c.id })}>
                    {c.name} (d{c.hitDie})
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
