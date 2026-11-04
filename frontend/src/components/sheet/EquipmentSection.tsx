import { useT } from "../../LanguageContext";
import type { SheetSectionData } from "../../logic/sheetSections";
import { SectionFrame } from "./SectionFrame";

export function EquipmentSection({ data }: { data: SheetSectionData["equipment"] }) {
  const t = useT();
  const c = t.sheet.equipment;
  return (
    <SectionFrame sectionKey="equipment" title={c.title}>
      {data.groups.map((group) => (
        <div key={group.kind}>
          <h3>{c.groups[group.kind]}</h3>
          <ul>
            {group.entries.map((e, i) => (
              <li key={`${e.itemId}:${i}`}>
                {e.name}
                {e.qty !== 1 ? ` ${c.quantity(e.qty)}` : ""}
                {e.equipped ? ` (${c.equipped})` : ""}
                {e.contents && e.contents.length > 0 && (
                  <>
                    {" "}
                    ({c.contents}:{" "}
                    {e.contents.map((p) => p.name + (p.qty !== 1 ? ` ${c.quantity(p.qty)}` : "")).join(", ")})
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {(data.worn || data.wielded) && (
        <dl>
          {data.worn && (
            <>
              <dt>
                {c.worn}: {c.armor}
              </dt>
              <dd>
                {data.worn.armor ?? c.noArmor}
                {data.worn.shield ? `, ${c.shield}` : ""}
              </dd>
            </>
          )}
          {data.wielded && (
            <>
              <dt>{c.handsTitle}</dt>
              <dd>
                {c.mainHand}: {data.wielded.main ?? c.emptyHand}; {c.offHand}: {data.wielded.off ?? c.emptyHand}
              </dd>
            </>
          )}
        </dl>
      )}
      {data.startingGold > 0 && (
        <p>
          {c.startingGold}: {t.common.gold(data.startingGold)}
        </p>
      )}
      {data.narrativeItems.length > 0 && (
        <>
          <h3>{c.narrativeItems}</h3>
          <ul>
            {data.narrativeItems.map((item, i) => (
              <li key={`${item}:${i}`}>{item}</li>
            ))}
          </ul>
        </>
      )}
    </SectionFrame>
  );
}

export function CarryingCapacitySection({ data }: { data: SheetSectionData["carryingCapacity"] }) {
  const t = useT();
  const c = t.sheet.carryingCapacity;
  return (
    <SectionFrame sectionKey="carryingCapacity" title={c.title}>
      <dl>
        <dt>{c.carried}</dt>
        <dd>{t.common.pounds(data.carried)}</dd>
        <dt>{c.capacity}</dt>
        <dd>{t.common.pounds(data.capacity)}</dd>
        <dt>{c.pushDragLift}</dt>
        <dd>{t.common.pounds(data.pushDragLift)}</dd>
      </dl>
      {data.overCapacity && <p>{c.overCapacity}</p>}
    </SectionFrame>
  );
}

export function DefensesSection({ data }: { data: SheetSectionData["defenses"] }) {
  const t = useT();
  const c = t.sheet.defenses;
  const rows = [
    [c.resistances, data.resistances],
    [c.immunities, data.immunities],
    [c.vulnerabilities, data.vulnerabilities],
    [c.conditionImmunities, data.conditionImmunities],
  ] as const;
  return (
    <SectionFrame sectionKey="defenses" title={c.title}>
      <dl>
        {rows
          .filter(([, list]) => list.length > 0)
          .map(([label, list]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{list.join(", ")}</dd>
            </div>
          ))}
      </dl>
    </SectionFrame>
  );
}
