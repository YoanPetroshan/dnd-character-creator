import { t } from "../../copy";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function FeaturesSection({ data }: { data: SheetSectionData["features"] }) {
  const c = t.sheet.features;
  return (
    <SectionFrame sectionKey="features" title={c.title}>
      {data.map((group, g) => (
        <div key={`${group.label}:${g}`}>
          <h3>{group.label}</h3>
          <ul>
            {group.items.map((f, i) => (
              <li key={`${f.name}:${i}`}>
                {f.name}
                {f.level ? ` (${c.level(f.level)})` : ""}
                {f.choice && f.choice.length > 0 ? `: ${f.choice.join(", ")}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </SectionFrame>
  );
}

export function FeatsSection({ data }: { data: SheetSectionData["feats"] }) {
  const c = t.sheet.feats;
  return (
    <SectionFrame sectionKey="feats" title={c.title}>
      <ul>
        {data.map((f, i) => (
          // a repeatable feat (Elemental Adept, Magic Initiate, Skilled) appears once per pick with the same id
          <li key={`${f.id}:${f.origin}:${f.level ?? ""}:${i}`}>
            {f.name}
            {f.level ? ` (${c.level(f.level)})` : ""}
            {f.choice && f.choice.length > 0 ? `: ${f.choice.join(", ")}` : ""}
            {f.notes && f.notes.length > 0 ? ` — ${f.notes.join("; ")}` : ""}
          </li>
        ))}
      </ul>
    </SectionFrame>
  );
}
