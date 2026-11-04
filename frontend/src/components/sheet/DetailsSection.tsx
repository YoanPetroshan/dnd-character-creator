import { t } from "../../copy";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function DetailsSection({ data }: { data: SheetSectionData["details"] }) {
  const c = t.sheet.details;
  return (
    <SectionFrame sectionKey="details" title={c.title}>
      {data.map((s) => (
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
