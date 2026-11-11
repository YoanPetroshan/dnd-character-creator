import { useState } from "react";
import { useDraft } from "../../DraftContext";
import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSection, SheetSectionData } from "../../logic/sheetSections";
import { FEATURE_FILTERS, STANDARD_ACTIONS, featureGroups, mergeSpellRows, type FeatureFilter, type SpellMark } from "../../logic/sheetTabs";
import { useSpells, type CatalogSpell } from "../../useSpells";
import type { Resolution } from "../../types";
import { SpellSlotsSummary } from "../SpellSlotsSummary";
import { AbilitiesSection } from "../sheet/AbilitiesSection";
import { AttacksSection } from "../sheet/AttacksSection";
import { DetailsSection } from "../sheet/DetailsSection";
import { CarryingCapacitySection, DefensesSection, EquipmentSection } from "../sheet/EquipmentSection";
import { IdentitySection } from "../sheet/IdentitySection";
import { LanguagesSection, ProficienciesSection, SavingThrowsSection, SkillsSection } from "../sheet/ProficiencySections";
import { ResourcesSection } from "../sheet/ResourcesSection";
import { SectionFrame } from "../sheet/SectionFrame";
import { InnateSpellsSection } from "../sheet/SpellsSection";
import {
  ArmorClassSection,
  HitPointsSection,
  InitiativeSection,
  PassivesSection,
  ProficiencyBonusSection,
  SensesSection,
  SpeedsSection,
} from "../sheet/StatSections";

function find<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** Actions: attacks, the standard actions, resources; then the numbers, skills, saves, senses and proficiencies the page keeps here
 *  (nothing the old sheet page showed is dropped). Every block grows with its content: no inner scroll windows. */
export function ActionsPanel({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const attacks = find(sections, "attacks");
  const resources = find(sections, "resources");
  const abilities = find(sections, "abilities");
  const hp = find(sections, "hitPoints");
  const ac = find(sections, "armorClass");
  const initiative = find(sections, "initiative");
  const speeds = find(sections, "speeds");
  const prof = find(sections, "proficiencyBonus");
  const passives = find(sections, "passives");
  const saves = find(sections, "savingThrows");
  const skills = find(sections, "skills");
  const senses = find(sections, "senses");
  const defenses = find(sections, "defenses");
  const proficiencies = find(sections, "proficiencies");
  const languages = find(sections, "languages");
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
      {abilities && <AbilitiesSection data={abilities} />}
      {prof !== undefined && <ProficiencyBonusSection data={prof} />}
      {ac && <ArmorClassSection data={ac} />}
      {hp && <HitPointsSection data={hp} />}
      {initiative !== undefined && <InitiativeSection data={initiative} />}
      {speeds && <SpeedsSection data={speeds} />}
      {passives && <PassivesSection data={passives} />}
      {saves && <SavingThrowsSection data={saves} />}
      {skills && <SkillsSection data={skills} />}
      {senses && <SensesSection data={senses} />}
      {defenses && <DefensesSection data={defenses} />}
      {proficiencies && <ProficienciesSection data={proficiencies} />}
      {languages && <LanguagesSection data={languages} />}
    </>
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
                const notes = [
                  ...(info?.concentration ? [c.concentration] : []),
                  ...(info?.ritual ? [c.ritual] : []),
                  ...s.marks.map((m: SpellMark) => c.marks[m]),
                ];
                return (
                  <tr key={s.id} data-spell={s.id}>
                    <th scope="row">{s.name}</th>
                    <td>{info?.castingTime ?? t.common.none}</td>
                    <td>{info?.range ?? t.common.none}</td>
                    <td>{info && info.components.length > 0 ? info.components.join(", ") : t.common.none}</td>
                    <td>{info?.duration ?? t.common.none}</td>
                    <td>{notes.length > 0 ? notes.join(", ") : t.common.none}</td>
                  </tr>
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
      <div className="feature-filters" role="group" aria-label={c.filtersLabel}>
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
                {g.label} ({c.source[g.kind as "class" | "species" | "background"]})
              </h3>
              <ul>
                {g.features.map((f, i) => (
                  <li key={`${f.name}:${i}`}>
                    {f.name}
                    {f.level ? ` (${t.sheet.features.level(f.level)})` : ""}
                    {f.choice && f.choice.length > 0 ? `: ${f.choice.join(", ")}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </SectionFrame>
      )}
      {featBlock && (
        <SectionFrame sectionKey="feats" title={t.sheet.feats.title}>
          <ul>
            {featBlock.feats.map((f, i) => (
              // a repeatable feat appears once per pick with the same id
              <li key={`${f.id}:${f.origin}:${f.level ?? ""}:${i}`}>
                {f.name}
                {f.level ? ` (${t.sheet.feats.level(f.level)})` : ""}
                {f.choice && f.choice.length > 0 ? `: ${f.choice.join(", ")}` : ""}
                {f.notes && f.notes.length > 0 ? ` — ${f.notes.join("; ")}` : ""}
              </li>
            ))}
          </ul>
        </SectionFrame>
      )}
    </>
  );
}

/** Background: who the character is (name, classes, species, size, background) and the characteristics / personality blocks. */
export function BackgroundPanel({ sections }: { sections: SheetSection[] }) {
  const identity = find(sections, "identity");
  const details = find(sections, "details");
  return (
    <>
      {identity && <IdentitySection data={identity} />}
      {details && <DetailsSection data={details} only={["character", "physical", "personality"]} />}
    </>
  );
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
