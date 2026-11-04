import { t } from "../../copy";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData } from "../../logic/sheetSections";
import type { Attack } from "../../types";
import { SectionFrame } from "./SectionFrame";

function damageText(a: Attack): string {
  const c = t.sheet.attacks;
  if (!a.damage) return t.common.none;
  const parts = [c.damage(a.damage, a.damageType)];
  if (a.versatileDamage) parts.push(c.versatile(a.versatileDamage));
  if (a.duelingDamage) parts.push(c.dueling(a.duelingDamage));
  if (a.offhandDamage) parts.push(c.offhand(a.offhandDamage));
  return parts.join(", ");
}

export function AttacksSection({ data }: { data: SheetSectionData["attacks"] }) {
  const c = t.sheet.attacks;
  return (
    <SectionFrame sectionKey="attacks" title={c.title}>
      <dl>
        <dt>{c.perAction}</dt>
        <dd>{data.perAction}</dd>
      </dl>
      {data.attacks.length > 0 && (
        <table>
          <thead>
            <tr>
              <th scope="col">{c.columns.weapon}</th>
              <th scope="col">{c.columns.ability}</th>
              <th scope="col">{c.columns.bonus}</th>
              <th scope="col">{c.columns.damage}</th>
              <th scope="col">{c.columns.range}</th>
              <th scope="col">{c.columns.mastery}</th>
              <th scope="col">{c.columns.notes}</th>
            </tr>
          </thead>
          <tbody>
            {data.attacks.map((a) => (
              <tr key={a.itemId} data-proficient={a.proficient} data-wielded={a.wielded ?? undefined}>
                <th scope="row">
                  {a.name}
                  {a.wielded ? ` (${c.wielded})` : ""}
                </th>
                <td>{a.ability}</td>
                <td>{formatModifier(a.attackBonus)}</td>
                <td>{damageText(a)}</td>
                <td>{a.range ?? t.common.none}</td>
                <td>{a.mastery ?? t.common.none}</td>
                <td>{a.notes.length > 0 ? a.notes.join("; ") : t.common.none}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data.masteries.length > 0 && (
        <>
          <h3>{c.masteriesTitle}</h3>
          <ul>
            {data.masteries.map((m) => (
              <li key={m.itemId}>
                {m.name}: {m.mastery}
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionFrame>
  );
}
