import { t } from "../../copy";
import { formatModifier } from "../../logic/abilities";
import type { SheetSectionData, SlotRow } from "../../logic/sheetSections";
import type { SheetInnateSpell, SheetSpellSummary } from "../../types";
import { SectionFrame } from "./SectionFrame";

function SpellList({ title, spells }: { title: string; spells: SheetSpellSummary[] }) {
  if (spells.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul>
        {spells.map((s) => (
          <li key={s.id}>{t.sheet.spells.spellLine(s.name, s.level)}</li>
        ))}
      </ul>
    </>
  );
}

function Slots({ title, rows, note }: { title: string; rows: SlotRow[]; note?: string }) {
  if (rows.length === 0) return null;
  return (
    <>
      <h3>{title}</h3>
      <ul>
        {rows.map((r) => (
          <li key={r.level}>{t.sheet.spells.slotLine(r.level, r.count)}</li>
        ))}
      </ul>
      {note && <p>({note})</p>}
    </>
  );
}

export function SpellsSection({ data }: { data: SheetSectionData["spells"] }) {
  const c = t.sheet.spells;
  return (
    <SectionFrame sectionKey="spells" title={c.title}>
      <Slots title={c.slotsTitle} rows={data.slots} note={data.slotsShared ? c.slotsShared : undefined} />
      <Slots title={c.pactTitle} rows={data.pactSlots} />
      {data.casters.map((caster) => (
        <article key={caster.classId} data-class={caster.classId}>
          <h3>{caster.className}</h3>
          <dl>
            {caster.ability && (
              <>
                <dt>{c.ability}</dt>
                <dd>{caster.ability}</dd>
              </>
            )}
            {caster.saveDC !== null && (
              <>
                <dt>{c.saveDC}</dt>
                <dd>{caster.saveDC}</dd>
              </>
            )}
            {caster.attackBonus !== null && (
              <>
                <dt>{c.attackBonus}</dt>
                <dd>{formatModifier(caster.attackBonus)}</dd>
              </>
            )}
          </dl>
          <SpellList title={c.cantrips} spells={caster.cantrips} />
          <SpellList title={c.spellbook} spells={caster.spellbook} />
          <SpellList title={c.known} spells={caster.known} />
          <SpellList title={c.alwaysPrepared} spells={caster.alwaysPrepared} />
          {caster.mysticArcanum.length > 0 && (
            <>
              <h4>{c.mysticArcanum}</h4>
              <ul>
                {caster.mysticArcanum.map((m) => (
                  <li key={m.id}>{c.spellLine(m.name, m.level)}</li>
                ))}
              </ul>
            </>
          )}
          <SpellList title={c.spellMastery} spells={caster.spellMastery} />
          <SpellList title={c.signatureSpells} spells={caster.signatureSpells} />
          <SpellList title={c.pactOfTheTome} spells={caster.pactOfTheTome} />
        </article>
      ))}
    </SectionFrame>
  );
}

export function InnateSpellsSection({ data }: { data: SheetSectionData["innateSpells"] }) {
  const c = t.sheet.innateSpells;
  const line = (e: SheetInnateSpell) =>
    [
      c.line(e.name, e.uses, e.level),
      e.ability ? `${c.ability} ${e.ability}` : null,
      e.variant ? `${c.variant}: ${e.variant}` : null,
      e.note ?? null,
      e.source ? `[${e.source}]` : null,
    ]
      .filter(Boolean)
      .join(", ");
  return (
    <SectionFrame sectionKey="innateSpells" title={c.title}>
      <ul>
        {data.map((e, i) => (
          <li key={`${e.spellId ?? e.name}:${i}`}>{line(e)}</li>
        ))}
      </ul>
    </SectionFrame>
  );
}
