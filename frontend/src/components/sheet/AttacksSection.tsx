import { Fragment } from "react";
import type { Copy } from "../../copy";
import { useT } from "../../LanguageContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData } from "../../logic/sheetSections";
import type { Attack } from "../../types";
import { SectionFrame } from "./SectionFrame";
import { SheetEye, SheetEyePanel, SheetEyeRow } from "./SheetEyes";

function damageText(t: Copy, a: Attack): string {
  const c = t.sheet.attacks;
  if (!a.damage) return t.common.none;
  const parts = [c.damage(a.damage, a.damageType)];
  if (a.versatileDamage) parts.push(c.versatile(a.versatileDamage));
  if (a.duelingDamage) parts.push(c.dueling(a.duelingDamage));
  if (a.offhandDamage) parts.push(c.offhand(a.offhandDamage));
  return parts.join(", ");
}

export function AttacksSection({ data }: { data: SheetSectionData["attacks"] }) {
  const t = useT();
  const c = t.sheet.attacks;
  return (
    <SectionFrame sectionKey="attacks" title={c.title}>
      <dl className="attacks__per-action">
        <dt>{c.perAction}</dt>
        <dd>{data.perAction}</dd>
      </dl>
      {data.attacks.length > 0 && (
        <table className="attacks">
          <thead>
            <tr>
              <th scope="col">{c.columns.weapon}</th>
              <th scope="col">{c.columns.range}</th>
              <th scope="col">{c.columns.bonus}</th>
              <th scope="col">{c.columns.damage}</th>
              <th scope="col">{c.columns.notes}</th>
            </tr>
          </thead>
          <tbody>
            {data.attacks.map((a) => (
              <Fragment key={a.itemId}>
              <tr data-proficient={a.proficient} data-wielded={a.wielded ?? undefined}>
                <th scope="row">
                  <span className="attack__name">{a.name}</span>
                  <SheetEye rowKey={`attack:${a.itemId}`} kind="item" id={a.itemId} name={a.name} />
                  <span className="attack__sub">
                    {[a.ability, ...(a.wielded ? [c.wielded] : []), ...(a.mastery ? [`${c.columns.mastery}: ${a.mastery}`] : [])].join(" · ")}
                  </span>
                </th>
                <td className="attack__range">{a.range ?? t.common.none}</td>
                <td>
                  <span className="sheet-chip">{formatModifier(a.attackBonus)}</span>
                </td>
                <td>
                  <span className="sheet-chip sheet-chip--wide">{damageText(t, a)}</span>
                </td>
                <td className="attack__notes">{a.notes.length > 0 ? a.notes.join("; ") : t.common.none}</td>
              </tr>
              <SheetEyeRow rowKey={`attack:${a.itemId}`} kind="item" id={a.itemId} colSpan={5} />
              </Fragment>
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
                {m.name}
                <SheetEye rowKey={`mastery:${m.itemId}`} kind="item" id={m.itemId} name={m.name} />: {m.mastery}
                <SheetEyePanel rowKey={`mastery:${m.itemId}`} kind="item" id={m.itemId} />
              </li>
            ))}
          </ul>
        </>
      )}
    </SectionFrame>
  );
}
