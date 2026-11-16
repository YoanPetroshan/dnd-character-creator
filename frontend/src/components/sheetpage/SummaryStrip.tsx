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
  const classLine = identity?.classes.map((cl) => t.sheet.identity.classLine(cl.name, cl.level, cl.subclass)).join(" / ");
  const speciesLine = identity?.species ? t.sheet.identity.speciesLine(identity.species.name, identity.species.subspecies, identity.species.variant) : null;
  const size = identity?.species?.size ?? null;
  const multiclass = (identity?.classes.length ?? 0) > 1;
  const extraSpeeds = (speeds ?? []).slice(1);
  const stats: [string, string | null, string, string | number | null | undefined][] = [
    ["hitPoints", "hitPoints", c.hitPoints, hp?.max],
    ["armorClass", "armorClass", c.armorClass, ac?.value],
    ["initiative", "initiative", c.initiative, initiative === undefined ? null : formatModifier(initiative)],
    ["speed", "speeds", c.speed, speeds && speeds[0] ? t.common.feet(speeds[0].feet) : null],
    ["proficiencyBonus", "proficiencyBonus", c.proficiencyBonus, prof === undefined ? null : formatModifier(prof)],
    ["hitDice", null, c.hitDice, hp?.hitDice],
  ];
  return (
    <section className="summary-strip" data-section="summary" aria-label={c.label}>
      <p className="summary-strip__who" data-section="identity">
        <strong data-summary="name">{identity?.name || t.sheet.unnamed}</strong>
        <span data-summary="class">{classLine}</span>
        {speciesLine && <span data-summary="species">{speciesLine}</span>}
        {size && <span data-summary="size">{size}</span>}
        {identity?.background && <span data-summary="background">{identity.background}</span>}
        {identity && multiclass && (
          <span data-summary="level">
            {t.sheet.identity.level} {identity.level}
          </span>
        )}
      </p>
      <ul className="summary-strip__abilities" data-section="abilities">
        {(abilities ?? []).map((r) => (
          <li key={r.ability} data-summary-ability={r.ability}>
            <span className="ability__label">{r.ability}</span>
            <span className="ability__mod">{formatModifier(r.modifier)}</span>
            <span className="ability__score">{r.total}</span>
          </li>
        ))}
      </ul>
      <dl className="summary-strip__stats">
        {stats
          .filter(([, , , value]) => value !== null && value !== undefined)
          .map(([key, section, label, value]) => (
            <div key={key} data-summary={key} data-section={section ?? undefined}>
              <dt>{label}</dt>
              <dd>{value}</dd>
              {key === "speed" &&
                extraSpeeds.map((sp) => (
                  <span key={sp.mode} className="summary-strip__sub">
                    {t.sheet.speeds.modes[sp.mode] ?? sp.mode} {t.common.feet(sp.feet)}
                  </span>
                ))}
            </div>
          ))}
      </dl>
      {ac?.stealthDisadvantage && (
        <p className="summary-strip__note" data-summary="stealthDisadvantage">
          {t.sheet.armorClass.stealthDisadvantage}
        </p>
      )}
    </section>
  );
}
