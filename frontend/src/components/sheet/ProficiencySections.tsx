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
            <th scope="col" aria-label={c.columns.mark}>
              {c.head.prof}
            </th>
            <th scope="col" aria-label={t.sheet.savingThrows.columns.ability}>
              {c.head.mod}
            </th>
            <th scope="col">{c.head.skill}</th>
            <th scope="col">{c.head.bonus}</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((s) => (
            <tr key={s.id} data-proficient={s.proficient} data-expertise={s.expertise}>
              <td className="skill__mark">
                <span className="visually-hidden">{s.expertise ? t.sheet.markers.expertise : s.proficient ? t.sheet.markers.proficient : ""}</span>
              </td>
              <td className="skill__ability">{s.ability ?? ""}</td>
              <th scope="row">{s.name}</th>
              <td className="skill__bonus">
                <span className="sheet-chip">{formatModifier(s.bonus)}</span>
              </td>
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

/** Proficiencies & training: armor, weapons and tools, with the languages as the last block inside the same box. */
export function ProficienciesSection({ data, languages }: { data: SheetSectionData["proficiencies"]; languages?: SheetSectionData["languages"] }) {
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
      {languages && <LanguagesSection data={languages} nested />}
    </SectionFrame>
  );
}

export function LanguagesSection({ data, nested = false }: { data: SheetSectionData["languages"]; nested?: boolean }) {
  const t = useT();
  return (
    <SectionFrame sectionKey="languages" title={t.sheet.languages.title} level={nested ? 3 : 2}>
      <p>{data.join(", ")}</p>
    </SectionFrame>
  );
}
