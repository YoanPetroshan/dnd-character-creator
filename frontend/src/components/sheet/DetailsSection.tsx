import { useT } from "../../LanguageContext";
import type { DetailSectionKey, SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

/** `only` narrows the blocks shown (the sheet page splits the details between its Background and Notes tabs). */
export function DetailsSection({ data, only }: { data: SheetSectionData["details"]; only?: DetailSectionKey[] }) {
  const t = useT();
  const c = t.sheet.details;
  return (
    <SectionFrame sectionKey="details" title={c.title}>
      {data.filter((s) => !only || only.includes(s.section)).map((s) => (
        <div key={s.section}>
          <h3>{c.sections[s.section]}</h3>
          <dl>
            {s.fields.map((f) => (
              <div key={f.key}>
                <dt>{c.fields[f.key]}</dt>
                <dd>{f.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </SectionFrame>
  );
}
