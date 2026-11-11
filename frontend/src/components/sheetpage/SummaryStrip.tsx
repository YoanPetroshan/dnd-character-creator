import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSection, SheetSectionData } from "../../logic/sheetSections";

function data<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** A compact always-visible strip: who the character is and the numbers needed most. Read-only: the app does not track play
 *  state (no current / temporary HP, rests, inspiration or dice). */
export function SummaryStrip({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const c = t.sheet.summary;
  const identity = data(sections, "identity");
  const abilities = data(sections, "abilities");
  const hp = data(sections, "hitPoints");
  const ac = data(sections, "armorClass");
  const initiative = data(sections, "initiative");
  const speeds = data(sections, "speeds");
  const prof = data(sections, "proficiencyBonus");
  const passives = data(sections, "passives");
  const classLine = identity?.classes.map((cl) => t.sheet.identity.classLine(cl.name, cl.level, cl.subclass)).join(" / ");
  const speciesLine = identity?.species ? t.sheet.identity.speciesLine(identity.species.name, identity.species.subspecies, identity.species.variant) : null;
  const stats: [string, string, string | number | null | undefined][] = [
    ["hitPoints", c.hitPoints, hp?.max],
    ["armorClass", c.armorClass, ac?.value],
    ["initiative", c.initiative, initiative === undefined ? null : formatModifier(initiative)],
    ["speed", c.speed, speeds && speeds[0] ? t.common.feet(speeds[0].feet) : null],
    ["proficiencyBonus", c.proficiencyBonus, prof === undefined ? null : formatModifier(prof)],
    ["passivePerception", c.passivePerception, passives?.perception],
    ["hitDice", c.hitDice, hp?.hitDice],
  ];
  return (
    <section className="summary-strip" data-section="summary" aria-label={c.label}>
      <p className="summary-strip__who">
        <strong data-summary="name">{identity?.name || t.sheet.unnamed}</strong>{" "}
        <span data-summary="class">{classLine}</span> <span data-summary="species">{speciesLine}</span>
      </p>
      <ul className="summary-strip__abilities">
        {(abilities ?? []).map((r) => (
          <li key={r.ability} data-summary-ability={r.ability}>
            {c.ability(r.ability, r.total, formatModifier(r.modifier))}
          </li>
        ))}
      </ul>
      <dl className="summary-strip__stats">
        {stats
          .filter(([, , value]) => value !== null && value !== undefined)
          .map(([key, label, value]) => (
            <div key={key} data-summary={key}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
      </dl>
    </section>
  );
}
