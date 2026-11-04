import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function ProficiencyBonusSection({ data }: { data: SheetSectionData["proficiencyBonus"] }) {
  const t = useT();
  return (
    <SectionFrame sectionKey="proficiencyBonus" title={t.sheet.proficiencyBonus.title}>
      <p>{formatModifier(data)}</p>
    </SectionFrame>
  );
}

export function ArmorClassSection({ data }: { data: SheetSectionData["armorClass"] }) {
  const t = useT();
  return (
    <SectionFrame sectionKey="armorClass" title={t.sheet.armorClass.title}>
      <p>{data.value}</p>
      {data.stealthDisadvantage && <p>{t.sheet.armorClass.stealthDisadvantage}</p>}
    </SectionFrame>
  );
}

export function HitPointsSection({ data }: { data: SheetSectionData["hitPoints"] }) {
  const t = useT();
  const c = t.sheet.hitPoints;
  return (
    <SectionFrame sectionKey="hitPoints" title={c.title}>
      <dl>
        <dt>{c.max}</dt>
        <dd>{data.max}</dd>
        <dt>{c.hitDice}</dt>
        <dd>{data.hitDice ?? t.common.none}</dd>
      </dl>
    </SectionFrame>
  );
}

export function InitiativeSection({ data }: { data: SheetSectionData["initiative"] }) {
  const t = useT();
  return (
    <SectionFrame sectionKey="initiative" title={t.sheet.initiative.title}>
      <p>{formatModifier(data)}</p>
    </SectionFrame>
  );
}

export function SpeedsSection({ data }: { data: SheetSectionData["speeds"] }) {
  const t = useT();
  const c = t.sheet.speeds;
  return (
    <SectionFrame sectionKey="speeds" title={c.title}>
      <ul>
        {data.map((s) => (
          <li key={s.mode}>
            {c.modes[s.mode] ?? s.mode}: {t.common.feet(s.feet)}
          </li>
        ))}
      </ul>
    </SectionFrame>
  );
}

export function SensesSection({ data }: { data: SheetSectionData["senses"] }) {
  const t = useT();
  const c = t.sheet.senses;
  return (
    <SectionFrame sectionKey="senses" title={c.title}>
      <ul>
        {data.map((s) => (
          <li key={s.kind}>
            {c.kinds[s.kind] ?? s.kind}: {t.common.feet(s.feet)}
          </li>
        ))}
      </ul>
    </SectionFrame>
  );
}

export function PassivesSection({ data }: { data: SheetSectionData["passives"] }) {
  const t = useT();
  const c = t.sheet.passives;
  return (
    <SectionFrame sectionKey="passives" title={c.title}>
      <dl>
        <dt>{c.perception}</dt>
        <dd>{data.perception}</dd>
        <dt>{c.insight}</dt>
        <dd>{data.insight}</dd>
        <dt>{c.investigation}</dt>
        <dd>{data.investigation}</dd>
      </dl>
    </SectionFrame>
  );
}
