import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function SavingThrowsSection({ data }: { data: SheetSectionData["savingThrows"] }) {
  const t = useT();
  const c = t.sheet.savingThrows;
  return (
    <SectionFrame sectionKey="savingThrows" title={c.title}>
      <table>
        <thead>
          <tr>
            <th scope="col">{c.columns.ability}</th>
            <th scope="col">{c.columns.bonus}</th>
            <th scope="col">{c.columns.mark}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s) => (
            <tr key={s.ability} data-proficient={s.proficient}>
              <th scope="row">{s.ability}</th>
              <td>{formatModifier(s.bonus)}</td>
              <td>{s.proficient ? t.sheet.markers.proficient : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionFrame>
  );
}

export function SkillsSection({ data }: { data: SheetSectionData["skills"] }) {
  const t = useT();
  const c = t.sheet.skills;
  return (
    <SectionFrame sectionKey="skills" title={c.title}>
      <table>
        <thead>
          <tr>
            <th scope="col">{c.columns.skill}</th>
            <th scope="col">{c.columns.bonus}</th>
            <th scope="col">{c.columns.mark}</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((s) => (
            <tr key={s.id} data-proficient={s.proficient} data-expertise={s.expertise}>
              <th scope="row">{s.name}</th>
              <td>{formatModifier(s.bonus)}</td>
              <td>{s.expertise ? t.sheet.markers.expertise : s.proficient ? t.sheet.markers.proficient : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.otherExpertise.length > 0 && (
        <p>
          {c.otherExpertise}: {data.otherExpertise.join(", ")}
        </p>
      )}
    </SectionFrame>
  );
}

export function ProficienciesSection({ data }: { data: SheetSectionData["proficiencies"] }) {
  const t = useT();
  const c = t.sheet.proficiencies;
  const rows = [
    [c.armor, data.armor],
    [c.weapons, data.weapons],
    [c.tools, data.tools],
  ] as const;
  return (
    <SectionFrame sectionKey="proficiencies" title={c.title}>
      <dl>
        {rows
          .filter(([, list]) => list.length > 0)
          .map(([label, list]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{list.join(", ")}</dd>
            </div>
          ))}
      </dl>
    </SectionFrame>
  );
}

export function LanguagesSection({ data }: { data: SheetSectionData["languages"] }) {
  const t = useT();
  return (
    <SectionFrame sectionKey="languages" title={t.sheet.languages.title}>
      <p>{data.join(", ")}</p>
    </SectionFrame>
  );
}
