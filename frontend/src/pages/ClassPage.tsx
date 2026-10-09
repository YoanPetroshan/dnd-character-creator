import { useEffect, useState } from "react";
import { StepProblems } from "../components/StepProblems";
import { MAX_TOTAL_LEVEL, totalLevel, useDraft } from "../DraftContext";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard } from "../components/ChoiceCard";
import { CommitNumberInput } from "../components/CommitNumberInput";
import { SpellLibrary } from "../components/SpellLibrary";

type ClassTab = "features" | "spells";

function isSpellChoiceId(choiceId: string): boolean {
  return choiceId.endsWith(":spells-cantrips") || choiceId.endsWith(":spells-known");
}

interface ClassDetail {
  // "index", not "id". Filtered server-side by ruleset/sources; `hidden` marks
  // the draft's current pick when the filters would hide it.
  subclasses: { index: string; name: string; source?: string; ruleset?: string; hidden?: boolean }[];
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
  const selectedSubclassId = classEntry?.subclassId ?? "";
  const sourcesKey = draft.sources.join(",");

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams();
    if (draft.ruleset !== "mixed") params.set("ruleset", draft.ruleset);
    if (sourcesKey) params.set("sources", sourcesKey);
    if (selectedSubclassId) params.set("include", selectedSubclassId);
    const query = params.toString();
    fetch(`/api/catalog/class/${classId}${query ? `?${query}` : ""}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: ClassDetail) => {
        if (!cancelled) setClassDetail(data && data.levelFeatureCounts ? data : null);
      })
      .catch(() => {
        if (!cancelled) setClassDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [classId, draft.ruleset, sourcesKey, selectedSubclassId]);

  const classChoices = resolution
    ? resolution.choices.filter(
        (c) => (c.source.kind === "class" || c.source.kind === "feat") && c.id.startsWith(`class:${classId}:`)
      )
    : [];
  const featureChoices = classChoices.filter((c) => !isSpellChoiceId(c.id));
  const spellChoices = classChoices.filter((c) => isSpellChoiceId(c.id));
  const prunedReasons = new Map((resolution?.pruned ?? []).map((p) => [p.choiceId, p.reason]));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";

  const tabFeaturesId = `tab-features-${classId}`;
  const panelFeaturesId = `panel-features-${classId}`;
  const tabSpellsId = `tab-spells-${classId}`;
  const panelSpellsId = `panel-spells-${classId}`;

  function handleChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "class", choiceId, optionId, count });
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
        <CommitNumberInput
          min={1}
          max={Math.min(20, MAX_TOTAL_LEVEL - (totalLevel(draft) - classLevel))}
          value={classLevel}
          onCommit={(level) => dispatch({ type: "SET_CLASS_LEVEL", classId, level })}
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
                {s.source && s.source !== "SRD" ? ` (${s.source})` : ""}
                {s.hidden ? " — скрит от текущите филтри" : ""}
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

      {/* The primary class's level 1 is always the maximum die; a class taken
          later rolls (or averages) its own level 1 as well. */}
      {draft.preferences.hitPointType === "manual" && classLevel >= (isPrimary ? 2 : 1) && (
        <div className="hp-rolls">
          <h3>Хвърляния за точки живот</h3>
          {(resolution?.warnings ?? [])
            .filter((w) => w.id.startsWith(`hp-roll-invalid-${classId}-`))
            .map((w) => (
              <p key={w.id} role="status">
                {w.message}
              </p>
            ))}
          {Array.from({ length: classLevel - (isPrimary ? 1 : 0) }, (_, i) => i + (isPrimary ? 2 : 1)).map((lvl) => (
            <label key={lvl}>
              Ниво {lvl}
              <CommitNumberInput
                min={1}
                max={classDetail?.hit_die}
                placeholder={
                  classDetail?.hit_die !== undefined ? String(Math.floor(classDetail.hit_die / 2) + 1) : undefined
                }
                value={classEntry?.hpRolls?.[String(lvl)]}
                onCommit={(value) => dispatch({ type: "SET_HP_ROLL", classId, level: lvl, value })}
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
            <div key={choice.id}>
              <ChoiceCard choice={choice} onToggle={handleChange} />
              {prunedReasons.has(choice.id) && (
                <p className="choice-pruned" role="note">
                  {prunedReasons.get(choice.id)}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {effectiveTab === "spells" && (
        <div id={panelSpellsId} role="tabpanel" aria-labelledby={tabSpellsId}>
          {spellChoices.map((choice) => (
            <div key={choice.id}>
              <ChoiceCard choice={choice} onToggle={handleChange} />
              {prunedReasons.has(choice.id) && (
                <p className="choice-pruned" role="note">
                  {prunedReasons.get(choice.id)}
                </p>
              )}
            </div>
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
      <StepProblems step="class" />
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
          {totalLevel(draft) >= MAX_TOTAL_LEVEL && (
            <p role="note">Общото ниво е {MAX_TOTAL_LEVEL} — намали ниво на клас, за да добавиш друг.</p>
          )}
          <ul className="picker-list">
            {catalog.classes
              .filter((c) => !takenClassIds.has(c.id))
              .map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={totalLevel(draft) >= MAX_TOTAL_LEVEL}
                    onClick={() => dispatch({ type: "ADD_CLASS", classId: c.id })}
                  >
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
