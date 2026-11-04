import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function AbilitiesSection({ data }: { data: SheetSectionData["abilities"] }) {
  const t = useT();
  const c = t.sheet.abilities.columns;
  return (
    <SectionFrame sectionKey="abilities" title={t.sheet.abilities.title}>
      <table>
        <thead>
          <tr>
            <th scope="col">{c.ability}</th>
            <th scope="col">{c.base}</th>
            <th scope="col">{c.bonus}</th>
            <th scope="col">{c.total}</th>
            <th scope="col">{c.modifier}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.ability}>
              <th scope="row">{r.ability}</th>
              <td>{r.base ?? t.common.none}</td>
              <td>{r.bonus === null ? t.common.none : formatModifier(r.bonus)}</td>
              <td>{r.total}</td>
              <td>{formatModifier(r.modifier)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionFrame>
  );
}
