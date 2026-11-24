import { Fragment, useState } from "react";
import { localizeSpellRow } from "../../logic/spellRow";
import { useDraft } from "../../DraftContext";
import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { DetailSectionKey, SheetSection, SheetSectionData } from "../../logic/sheetSections";
import { FEATURE_FILTERS, STANDARD_ACTIONS, featureGroups, mergeSpellRows, type FeatureFilter, type SpellMark } from "../../logic/sheetTabs";
import { useSpells, type CatalogSpell } from "../../useSpells";
import type { Resolution } from "../../types";
import { SpellSlotsSummary } from "../SpellSlotsSummary";
import { AttacksSection } from "../sheet/AttacksSection";
import { DetailsSection } from "../sheet/DetailsSection";
import { CarryingCapacitySection, EquipmentSection } from "../sheet/EquipmentSection";
import { LanguagesSection, ProficienciesSection, SavingThrowsSection, SkillsSection } from "../sheet/ProficiencySections";
import { ResourcesSection } from "../sheet/ResourcesSection";
import { SectionFrame } from "../sheet/SectionFrame";
import { SheetEye, SheetEyePanel, SheetEyeRow, featureEyeTarget } from "../sheet/SheetEyes";
import { InnateSpellsSection } from "../sheet/SpellsSection";
import { PassivesSection, SensesSection } from "../sheet/StatSections";

function find<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** Actions: attacks, the standard actions, resources. The numbers, saves, skills and proficiencies are in the summary strip and the
 *  reference block (shown with every tab). Every block grows with its content: no inner scroll windows. */
export function ActionsPanel({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const attacks = find(sections, "attacks");
  const resources = find(sections, "resources");
  return (
    <>
      {attacks && <AttacksSection data={attacks} />}
      <SectionFrame sectionKey="standardActions" title={t.sheet.actionsTab.standardActions}>
        <ul className="standard-actions">
          {STANDARD_ACTIONS.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </SectionFrame>
      {resources && <ResourcesSection data={resources} />}
    </>
  );
}

/** The reference boxes shown with every tab: saving throws, passive senses and senses, proficiencies & training (with the
 *  languages) on the left; skills in their own column. Defenses sit with Initiative / AC over the tabs (CombatRow). */
export function ReferenceBlock({ sections }: { sections: SheetSection[] }) {
  const passives = find(sections, "passives");
  const saves = find(sections, "savingThrows");
  const skills = find(sections, "skills");
  const senses = find(sections, "senses");
  const proficiencies = find(sections, "proficiencies");
  const languages = find(sections, "languages");
  return (
    <div className="sheet-reference">
      <div className="sheet-reference__saves">{saves && <SavingThrowsSection data={saves} />}</div>
      <div className="sheet-reference__skills">{skills && <SkillsSection data={skills} />}</div>
      <div className="sheet-reference__rest">
        {/* one SENSES box like the online sheet: the three passives, then the senses line, the title at the bottom */}
        {(passives || senses) && (
          <div className="sheet-senses-box">
            {passives && <PassivesSection data={passives} />}
            {senses && <SensesSection data={senses} />}
          </div>
        )}
        {proficiencies ? (
          <ProficienciesSection data={proficiencies} languages={languages} />
        ) : (
          languages && <LanguagesSection data={languages} />
        )}
      </div>
    </div>
  );
}

function SpellRows({ caster, catalog }: { caster: ReturnType<typeof mergeSpellRows>; catalog: Map<string, CatalogSpell> }) {
  const t = useT();
  const c = t.sheet.spellsTab;
  return (
    <>
      {caster.map((group) => (
        <div key={group.level} data-spell-level={group.level}>
          <h4>{c.level(group.level)}</h4>
          <table>
            <thead>
              <tr>
                <th scope="col">{c.columns.spell}</th>
                <th scope="col">{c.columns.time}</th>
                <th scope="col">{c.columns.range}</th>
                <th scope="col">{c.columns.components}</th>
                <th scope="col">{c.columns.duration}</th>
                <th scope="col">{c.columns.notes}</th>
              </tr>
            </thead>
            <tbody>
              {group.spells.map((s) => {
                const info = catalog.get(s.id);
                const row = info ? localizeSpellRow(t.spellRow, info) : null;
                const notes = [
                  ...(info?.concentration ? [c.concentration] : []),
                  ...(info?.ritual ? [c.ritual] : []),
                  ...s.marks.map((m: SpellMark) => c.marks[m]),
                ];
                return (
                  <Fragment key={s.id}>
                    <tr data-spell={s.id}>
                      <th scope="row">
                        {s.name}
                        <SheetEye rowKey={`spell:${s.id}`} kind="spell" id={s.id} name={s.name} />
                      </th>
                      <td>{row?.castingTime ?? t.common.none}</td>
                      <td>{row?.range ?? t.common.none}</td>
                      <td>{info && info.components.length > 0 ? info.components.join(", ") : t.common.none}</td>
                      <td>{row?.duration ?? t.common.none}</td>
                      <td>{notes.length > 0 ? notes.join(", ") : t.common.none}</td>
                    </tr>
                    <SheetEyeRow rowKey={`spell:${s.id}`} kind="spell" id={s.id} colSpan={6} />
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}

function CasterBlock({ caster }: { caster: SheetSectionData["spells"]["casters"][number] }) {
  const t = useT();
  const c = t.sheet.spells;
  const { draft } = useDraft();
  const { spells } = useSpells(caster.classId, "", "", draft.ruleset, draft.sources);
  const catalog = new Map(spells.map((s) => [s.id, s]));
  return (
    <article data-class={caster.classId}>
      <h3>{caster.className}</h3>
      <dl>
        {caster.ability && (
          <>
            <dt>{c.ability}</dt>
            <dd>{caster.ability}</dd>
          </>
        )}
        {caster.saveDC !== null && (
          <>
            <dt>{c.saveDC}</dt>
            <dd>{caster.saveDC}</dd>
          </>
        )}
        {caster.attackBonus !== null && (
          <>
            <dt>{c.attackBonus}</dt>
            <dd>{formatModifier(caster.attackBonus)}</dd>
          </>
        )}
      </dl>
      <SpellRows caster={mergeSpellRows(caster)} catalog={catalog} />
    </article>
  );
}

/** Spells: slots, then per spellcasting source its numbers and ONE row per spell (merged lists), grouped by level with cantrips first. */
export function SpellsPanel({ sections, resolution }: { sections: SheetSection[]; resolution: Resolution }) {
  const t = useT();
  const spells = find(sections, "spells");
  const innate = find(sections, "innateSpells");
  return (
    <>
      {spells ? (
        <SectionFrame sectionKey="spells" title={t.sheet.spells.title}>
          <SpellSlotsSummary resolution={resolution} />
          {spells.casters.map((caster) => (
            <CasterBlock key={caster.classId} caster={caster} />
          ))}
        </SectionFrame>
      ) : (
        !innate && <p>{t.sheet.spellsTab.empty}</p>
      )}
      {innate && <InnateSpellsSection data={innate} />}
    </>
  );
}

/** Inventory: items with quantity and weight carried (kilograms follow the pounds in Bulgarian), worn / wielded, gold. */
export function InventoryPanel({ sections }: { sections: SheetSection[] }) {
  const equipment = find(sections, "equipment");
  const carrying = find(sections, "carryingCapacity");
  return (
    <>
      {equipment && <EquipmentSection data={equipment} />}
      {carrying && <CarryingCapacitySection data={carrying} />}
    </>
  );
}

/** Features & Traits with the ALL / CLASS / SPECIES / FEATS filter (buttons with aria-pressed), grouped by source. */
export function FeaturesPanel({ resolution }: { resolution: Resolution }) {
  const t = useT();
  const c = t.sheet.featuresTab;
  const [filter, setFilter] = useState<FeatureFilter>("all");
  const groups = featureGroups(resolution, filter);
  const featureBlocks = groups.filter((g) => g.kind !== "feat");
  const featBlock = groups.find((g) => g.kind === "feat");
  return (
    <>
      <div className="feature-filters sheet-pills" role="group" aria-label={c.filtersLabel}>
        {FEATURE_FILTERS.map((f) => (
          <button key={f} type="button" data-filter={f} aria-pressed={filter === f} onClick={() => setFilter(f)}>
            {c.filters[f]}
          </button>
        ))}
      </div>
      {groups.length === 0 && <p>{c.empty}</p>}
      {featureBlocks.length > 0 && (
        <SectionFrame sectionKey="features" title={t.sheet.tabs.features}>
          {featureBlocks.map((g) => (
            <div key={g.key} data-source={g.kind}>
              <h3>
                {g.label} <span className="feature__source">{c.source[g.kind as "class" | "species" | "background"]}</span>
              </h3>
              <ul className="feature-list">
                {g.features.map((f, i) => {
                  const target = featureEyeTarget(f.ref);
                  const rowKey = `feature:${g.key}:${i}`;
                  return (
                  <li key={`${f.name}:${i}`} className="feature">
                    <strong className="feature__name">{f.name}</strong>
                    {target && <SheetEye rowKey={rowKey} kind={target.kind} id={target.id} name={f.name} />}
                    {f.level ? <span className="feature__meta">{t.sheet.features.level(f.level)}</span> : null}
                    {f.choice && f.choice.length > 0 && <span className="feature__nested">{f.choice.join(", ")}</span>}
                    {target && <SheetEyePanel rowKey={rowKey} kind={target.kind} id={target.id} />}
                  </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </SectionFrame>
      )}
      {featBlock && (
        <SectionFrame sectionKey="feats" title={t.sheet.feats.title}>
          <ul className="feature-list">
            {featBlock.feats.map((f, i) => (
              // a repeatable feat appears once per pick with the same id
              <li key={`${f.id}:${f.origin}:${f.level ?? ""}:${i}`} className="feature">
                <strong className="feature__name">{f.name}</strong>
                <SheetEye rowKey={`feat:${i}`} kind="feat" id={f.id} name={f.name} />
                {f.level ? <span className="feature__meta">{t.sheet.feats.level(f.level)}</span> : null}
                {((f.choice && f.choice.length > 0) || (f.notes && f.notes.length > 0)) && (
                  <span className="feature__nested">
                    {[...(f.choice && f.choice.length > 0 ? [f.choice.join(", ")] : []), ...(f.notes ?? [])].join("; ")}
                  </span>
                )}
                <SheetEyePanel rowKey={`feat:${i}`} kind="feat" id={f.id} />
              </li>
            ))}
          </ul>
        </SectionFrame>
      )}
    </>
  );
}

/** Background: the characteristics / personality blocks (name, classes, species, size and background are in the summary strip). */
export function BackgroundPanel({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const details = find(sections, "details");
  const only: DetailSectionKey[] = ["character", "physical", "personality"];
  const hasData = details?.some((d) => only.includes(d.section)) ?? false;
  return <>{details && hasData ? <DetailsSection data={details} only={only} /> : <p>{t.sheet.backgroundTab.empty}</p>}</>;
}

/** Notes: organizations, allies, enemies, backstory and the other notes. */
export function NotesPanel({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const details = find(sections, "details");
  const hasNotes = details?.some((d) => d.section === "notes") ?? false;
  return (
    <>
      {details && hasNotes && <DetailsSection data={details} only={["notes"]} />}
      {!hasNotes && <p>{t.sheet.notesTab.empty}</p>}
    </>
  );
}
