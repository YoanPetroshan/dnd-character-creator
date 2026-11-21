import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { apiFetch } from "../api/transport";
import { StepProblems } from "../components/StepProblems";
import { MAX_TOTAL_LEVEL, totalLevel, useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { renderMsg } from "../logic/messages";
import { useResolutionContext } from "../ResolutionContext";
import { useCatalogContext } from "../CatalogContext";
import { ChoiceCard, firstPendingId } from "../components/ChoiceCard";
import { ClassGlyph } from "../components/ClassGlyph";
import { CommitNumberInput } from "../components/CommitNumberInput";
import { SpellLibrary } from "../components/SpellLibrary";
import { ClassResourcesList } from "../components/ClassResourcesList";
import { SpellSlotsSummary } from "../components/SpellSlotsSummary";
import { classChoicesFor, splitClassChoices } from "../logic/choiceRouting";
import { cidFromHash } from "../logic/hashTarget";
import { DetailEye, DetailPanel } from "../components/DetailEye";
import { SubclassPreview } from "../components/SubclassPreview";
import { LevelFeatureList } from "../components/FeatureEyeList";
import type { SheetFeature } from "../types";
import { SheetEyesProvider } from "../components/sheet/SheetEyes";
import { useSubclassDetails } from "../useSubclassDetail";

type ClassTab = "features" | "spells";

interface ClassDetail {
  // "index", not "id". Filtered server-side by ruleset/sources; `hidden` marks
  // the draft's current pick when the filters would hide it.
  subclasses: { index: string; name: string; source?: string; ruleset?: string; hidden?: boolean }[];
  levelFeatureCounts: Record<string, number>;
  subclassUnlockLevel: number | null;
  hit_die?: number; // raw SRD class object field, spread into this response as-is
}

function ClassBlock({ classId, isPrimary }: { classId: string; isPrimary: boolean }) {
  const t = useT();
  const cp = t.classPage;
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();
  const sheetClass = resolution?.sheet.classes.find((c) => c.id === classId);
  const [tab, setTab] = useState<ClassTab>("features");
  const [classDetail, setClassDetail] = useState<ClassDetail | null>(null);
  const [subOpen, setSubOpen] = useState(false);
  const [higherOpen, setHigherOpen] = useState(false);
  // every class feature by level (names and the id of their text), for the "next levels" list
  const [levelList, setLevelList] = useState<{ level: number; name: string; ref: string }[]>([]);
  const subclasses = useSubclassDetails();

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
    apiFetch(`/api/catalog/class/${classId}${query ? `?${query}` : ""}`)
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

  useEffect(() => {
    let cancelled = false;
    apiFetch(`/api/catalog/class/${classId}/levels${draft.ruleset !== "mixed" ? `?ruleset=${draft.ruleset}` : ""}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data: { levelFeatures?: { level: number; name: string; ref: string }[] }) => {
        if (!cancelled) setLevelList(Array.isArray(data?.levelFeatures) ? data.levelFeatures : []);
      })
      .catch(() => {
        if (!cancelled) setLevelList([]);
      });
    return () => {
      cancelled = true;
    };
  }, [classId, draft.ruleset]);

  const { loadDetail: loadSubclass } = subclasses;
  useEffect(() => {
    if (subOpen && selectedSubclassId) loadSubclass(selectedSubclassId);
  }, [subOpen, selectedSubclassId]);

  // What the levels give: the class features (and the chosen subclass's) up to the current level, with an eye each, plus the
  // Ability Score Improvement of a level and the subclass pick, which are not in the feature list.
  const levelFeatures = (resolution?.sheet.features ?? []).filter(
    (f) => (f.source.kind === "class" && f.source.id === classId) || (f.source.kind === "subclass" && !!selectedSubclassId && f.source.id === selectedSubclassId),
  );
  const levelExtras: { level: number; key: string; name: string; choice?: string[] }[] = [];
  for (const c of resolution?.choices ?? []) {
    const m = new RegExp(`^class:${classId}:(\\d+):asi$`).exec(c.id);
    if (!m || Number(m[1]) > classLevel) continue;
    const labels = c.selected.map((id) => c.options.find((o) => o.id === id)?.label ?? id);
    levelExtras.push({ level: Number(m[1]), key: c.id, name: cp.asiRow, choice: labels });
  }
  if (classDetail && classDetail.subclassUnlockLevel !== null && classLevel >= classDetail.subclassUnlockLevel) {
    const subName = classDetail.subclasses.find((s) => s.index === selectedSubclassId)?.name ?? selectedSubclassId;
    // the chosen subclass's own features are in the list; this row marks the level where the subclass is picked
    levelExtras.push({ level: classDetail.subclassUnlockLevel, key: `subclass:${classId}`, name: cp.subclass, choice: subName ? [subName] : undefined });
  }

  // the class features of the levels still ahead, from the class catalog (a subclass's own are not known before the pick)
  const upcoming: SheetFeature[] = levelList
    .filter((f) => f.level > classLevel)
    .map((f) => ({ source: { kind: "class", id: classId, label: classId }, name: f.name, level: f.level, ref: { kind: "feature", id: f.ref } }));

  const classChoices = resolution ? classChoicesFor(resolution.choices, classId) : [];
  const { featureChoices, spellChoices } = splitClassChoices(classChoices);
  const prunedReasons = new Map((resolution?.pruned ?? []).map((p) => [p.choiceId, p.reason]));
  const hasSpells = spellChoices.length > 0;
  const effectiveTab: ClassTab = hasSpells ? tab : "features";
  // a tab that is not open shows the red mark when one of its required choices is still open
  const hasPending = (list: typeof featureChoices) => list.some((c) => c.status === "pending" && !c.optional);
  const featuresPending = effectiveTab !== "features" && hasPending(featureChoices);
  const spellsPending = effectiveTab !== "spells" && hasPending(spellChoices);

  // A "#<cid>" hash may point into the tab that is not showing: switch to it
  // (the card itself expands and scrolls, see ChoiceCard).
  const hashCid = cidFromHash(useLocation().hash);
  const hashInSpells = hashCid !== null && spellChoices.some((c) => c.id === hashCid);
  const hashInFeatures = hashCid !== null && featureChoices.some((c) => c.id === hashCid);
  useEffect(() => {
    if (hashInSpells) setTab("spells");
    else if (hashInFeatures) setTab("features");
  }, [hashCid, hashInSpells, hashInFeatures]);

  const tabFeaturesId = `tab-features-${classId}`;
  const panelFeaturesId = `panel-features-${classId}`;
  const tabSpellsId = `tab-spells-${classId}`;
  const panelSpellsId = `panel-spells-${classId}`;

  function handleChange(choiceId: string, optionId: string, count: number) {
    dispatch({ type: "TOGGLE_CHOICE_OPTION", source: "class", choiceId, optionId, count });
  }

  return (
    <div className="class-block">
      <div className="class-block__head">
        <ClassGlyph classId={classId} solid />
        <h2>
          {sheetClass?.name ?? catalog.classes.find((c) => c.id === classId)?.name ?? classId}{" "}
          {!isPrimary && (
            <button type="button" onClick={() => dispatch({ type: "REMOVE_CLASS", classId })}>
              {cp.remove}
            </button>
          )}
        </h2>
      </div>

      <label className="class-level">
        {cp.level}
        <CommitNumberInput
          min={1}
          max={Math.min(20, MAX_TOTAL_LEVEL - (totalLevel(draft) - classLevel))}
          value={classLevel}
          onCommit={(level) => dispatch({ type: "SET_CLASS_LEVEL", classId, level })}
        />
      </label>
      {/* decorative: the number field above stays the control and the source of truth */}
      <span className="level-pips" aria-hidden="true">
        {Array.from({ length: 20 }, (_, i) => (
          <span key={i} className="level-pips__pip" data-on={i < classLevel ? "true" : undefined} />
        ))}
      </span>

      {classDetail && classDetail.subclassUnlockLevel !== null && classLevel >= classDetail.subclassUnlockLevel && (
        <div className="class-subclass">
        <label className="class-subclass__label">
          {cp.subclass}
          <select
            value={classEntry?.subclassId ?? ""}
            onChange={(e) => dispatch({ type: "SET_SUBCLASS", classId, subclassId: e.target.value || undefined })}
          >
            <option value="">{cp.chooseSubclass}</option>
            {classDetail.subclasses.map((s) => (
              <option key={s.index} value={s.index}>
                {s.name}
                {s.source && s.source !== "SRD" ? ` (${s.source})` : ""}
                {s.hidden ? ` — ${t.common.hiddenByFilters}` : ""}
              </option>
            ))}
          </select>
        </label>
        {selectedSubclassId && (
          <DetailEye
            label={cp.showSubclass(classDetail.subclasses.find((s) => s.index === selectedSubclassId)?.name ?? selectedSubclassId)}
            open={subOpen}
            onToggle={() => setSubOpen((v) => !v)}
          />
        )}
        {selectedSubclassId && subOpen && (
          <DetailPanel>
            <SubclassPreview state={subclasses.detailOf(selectedSubclassId)} />
          </DetailPanel>
        )}
        </div>
      )}

      {levelFeatures.length + levelExtras.length > 0 && (
        <div className="class-level-features">
          <h3>{cp.levelFeatures}</h3>
          <LevelFeatureList idPrefix={`class:${classId}`} features={levelFeatures} extra={levelExtras} />
        </div>
      )}

      {upcoming.length > 0 ? (
        <div className="class-next-levels">
          <button type="button" className="class-next-levels__toggle" aria-expanded={higherOpen} onClick={() => setHigherOpen((v) => !v)}>
            {cp.higherLevelsToggle(upcoming.length)}
          </button>
          {higherOpen && <LevelFeatureList idPrefix={`next:${classId}`} features={upcoming} extra={[]} />}
        </div>
      ) : (
        classDetail && (
          <p className="higher-levels-teaser">
            {cp.higherLevels}{" "}
            {Object.entries(classDetail.levelFeatureCounts)
              .filter(([lvl]) => Number(lvl) > classLevel)
              .reduce((sum, [, count]) => sum + count, 0)}
          </p>
        )
      )}

      {(resolution?.derived.classResources ?? []).some((r) => r.classId === classId) && (
        <div className="class-resources">
          <h3>{cp.classResources}</h3>
          <ClassResourcesList resources={(resolution?.derived.classResources ?? []).filter((r) => r.classId === classId)} />
        </div>
      )}

      {/* The primary class's level 1 is always the maximum die; a class taken
          later rolls (or averages) its own level 1 as well. */}
      {draft.preferences.hitPointType === "manual" && classLevel >= (isPrimary ? 2 : 1) && (
        <div className="hp-rolls">
          <h3>{cp.hpRolls}</h3>
          {(resolution?.warnings ?? [])
            .filter((w) => w.id.startsWith(`hp-roll-invalid-${classId}-`))
            .map((w) => (
              <p key={w.id} role="status">
                {w.message}
              </p>
            ))}
          {Array.from({ length: classLevel - (isPrimary ? 1 : 0) }, (_, i) => i + (isPrimary ? 2 : 1)).map((lvl) => (
            <label key={lvl}>
              {cp.levelN(lvl)}
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
          {cp.tabFeatures}
          {featuresPending && (
            <span className="tab-bar__pending" aria-label={t.choice.pendingDot}>
              !
            </span>
          )}
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
            {cp.tabSpells}
            {spellsPending && (
              <span className="tab-bar__pending" aria-label={t.choice.pendingDot}>
                !
              </span>
            )}
          </button>
        )}
      </div>

      {effectiveTab === "features" && (
        <div id={panelFeaturesId} role="tabpanel" aria-labelledby={tabFeaturesId}>
          {!loading && featureChoices.length === 0 && <p>{cp.noChoices}</p>}
          {featureChoices.map((choice) => (
            <div key={choice.id}>
              <ChoiceCard choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(featureChoices)} />
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
          {resolution && <SpellSlotsSummary resolution={resolution} classId={classId} />}
          {spellChoices.map((choice) => (
            <div key={choice.id}>
              <ChoiceCard choice={choice} onToggle={handleChange} defaultExpanded={choice.id === firstPendingId(spellChoices)} />
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
  const t = useT();
  const cp = t.classPage;
  const { draft, dispatch } = useDraft();
  const { resolution, loading } = useResolutionContext();
  const catalog = useCatalogContext();


  const takenClassIds = new Set(draft.classes.map((c) => c.classId));
  const primaryClassId = draft.classes[0]?.classId;

  return (
    <SheetEyesProvider>
    <div className="page">
      <h1>{cp.title} {loading && "…"}</h1>
      <StepProblems step="class" />
      {catalog.error && (
        <p>
          {cp.loadError(renderMsg(t, catalog.error))}{" "}
          <button type="button" onClick={catalog.retry}>
            {t.common.retry}
          </button>
        </p>
      )}

      {draft.classes.length <= 1 && (
        <ul className="picker-list picker-list--classes">
          {catalog.classes.map((c) => (
            <li key={c.id}>
              <label>
                <input
                  type="radio"
                  name="class"
                  checked={c.id === primaryClassId}
                  onChange={() => dispatch({ type: "SET_CLASS", classId: c.id })}
                />
                <ClassGlyph classId={c.id} />
                {cp.hitDieLabel(c.name, c.hitDie)}
              </label>
            </li>
          ))}
        </ul>
      )}

      {primaryClassId && (
        <div className="hp-summary">
          <strong>{cp.hitPoints}</strong> {resolution ? String(resolution.derived.hitPointMax ?? "—") : "—"}
        </div>
      )}

      {draft.classes.map((c, i) => (
        <ClassBlock key={c.classId} classId={c.classId} isPrimary={i === 0} />
      ))}

      {primaryClassId && (
        <div className="add-class">
          <h3>{cp.addClass}</h3>
          {totalLevel(draft) >= MAX_TOTAL_LEVEL && (
            <p role="note">{cp.levelCap(MAX_TOTAL_LEVEL)}</p>
          )}
          <ul className="picker-list picker-list--classes">
            {catalog.classes
              .filter((c) => !takenClassIds.has(c.id))
              .map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    disabled={totalLevel(draft) >= MAX_TOTAL_LEVEL}
                    onClick={() => dispatch({ type: "ADD_CLASS", classId: c.id })}
                  >
                    <ClassGlyph classId={c.id} />
                    {cp.hitDieLabel(c.name, c.hitDie)}
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
    </SheetEyesProvider>
  );
}
