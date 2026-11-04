import { useT } from "../../LanguageContext";
import type { SheetSectionData } from "../../logic/sheetSections";
import { ClassResourcesList } from "../ClassResourcesList";
import { SectionFrame } from "./SectionFrame";

export function ResourcesSection({ data }: { data: SheetSectionData["resources"] }) {
  const t = useT();
  const c = t.sheet.resources;
  return (
    <SectionFrame sectionKey="resources" title={c.title}>
      {data.class.length > 0 && (
        <>
          <h3>{c.class}</h3>
          <ClassResourcesList resources={data.class} />
        </>
      )}
      {data.feat.length > 0 && (
        <>
          <h3>{c.feat}</h3>
          <ClassResourcesList resources={data.feat} />
        </>
      )}
      {data.species.length > 0 && (
        <>
          <h3>{c.species}</h3>
          <ClassResourcesList resources={data.species} />
        </>
      )}
    </SectionFrame>
  );
}
