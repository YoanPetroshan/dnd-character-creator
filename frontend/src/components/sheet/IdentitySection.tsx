import { useT } from "../../LanguageContext";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function IdentitySection({ data }: { data: SheetSectionData["identity"] }) {
  const t = useT();
  const c = t.sheet.identity;
  return (
    <SectionFrame sectionKey="identity" title={c.title}>
      <dl>
        <dt>{c.name}</dt>
        <dd>{data.name || t.sheet.unnamed}</dd>
        <dt>{c.level}</dt>
        <dd>{data.level}</dd>
        <dt>{c.classes}</dt>
        <dd>
          {data.classes.length === 0 ? (
            t.common.none
          ) : (
            <ul>
              {data.classes.map((cl) => (
                <li key={cl.id}>{c.classLine(cl.name, cl.level, cl.subclass)}</li>
              ))}
            </ul>
          )}
        </dd>
        <dt>{c.species}</dt>
        <dd>{data.species ? c.speciesLine(data.species.name, data.species.subspecies, data.species.variant) : t.common.none}</dd>
        {data.species?.size && (
          <>
            <dt>{c.size}</dt>
            <dd>{data.species.size}</dd>
          </>
        )}
        <dt>{c.background}</dt>
        <dd>{data.background ?? t.common.none}</dd>
      </dl>
    </SectionFrame>
  );
}
