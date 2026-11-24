import { Link } from "react-router-dom";
import { useT } from "../../LanguageContext";
import { useLibrary } from "../../LibraryContext";
import { formatModifier } from "../../logic/abilities";
import type { SheetSection, SheetSectionData } from "../../logic/sheetSections";
import { HeroPortrait } from "../HeroPortrait";
import { Signed } from "../sheet/Signed";
import { DefensesSection } from "../sheet/EquipmentSection";

function data<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** The sheet header: the hero's picture (or the class mark), the name, then species and class, then the level. */
export function SheetHero({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const { activeId } = useLibrary();
  const identity = data(sections, "identity");
  const classLine = identity?.classes.map((cl) => t.sheet.identity.classLine(cl.name, cl.level, cl.subclass)).join(" / ");
  const speciesLine = identity?.species ? t.sheet.identity.speciesLine(identity.species.name, identity.species.subspecies, identity.species.variant) : null;
  const size = identity?.species?.size ?? null;
  return (
    <header className="sheet-hero">
      <HeroPortrait id={activeId} classId={identity?.classes[0]?.id} />
      <p className="summary-strip__who" data-section="identity">
        <strong data-summary="name">
          {identity?.name || (
            <Link to="/home" className="sheet-name-prompt">
              {t.sheet.nameIt}
            </Link>
          )}
        </strong>
        <span className="summary-strip__line">
          {speciesLine && <span data-summary="species">{speciesLine}</span>}
          <span data-summary="class">{classLine}</span>
          {size && <span data-summary="size">{size}</span>}
          {identity?.background && <span data-summary="background">{identity.background}</span>}
        </span>
        {identity && (
          <span className="summary-strip__level" data-summary="level">
            {t.sheet.identity.level} {identity.level}
          </span>
        )}
      </p>
    </header>
  );
}

/** The top row of boxes: six abilities (modifier large, score in a bubble), proficiency bonus, speed and hit points.
 *  Read-only: the app does not track play state (no current / temporary HP, rests, inspiration or dice). */
export function SummaryStrip({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const c = t.sheet.summary;
  const b = t.sheet.boxes;
  const abilities = data(sections, "abilities");
  const hp = data(sections, "hitPoints");
  const speeds = data(sections, "speeds");
  const prof = data(sections, "proficiencyBonus");
  const first = speeds?.[0];
  const extraSpeeds = (speeds ?? []).slice(1);
  return (
    <section className="summary-strip" data-section="summary" aria-label={c.label}>
      <ul className="summary-strip__abilities" data-section="abilities">
        {(abilities ?? []).map((r) => (
          <li key={r.ability} className="sheet-box ability-box" data-summary-ability={r.ability}>
            <span className="ability__label">{b.abilityNames[r.ability] ?? r.ability}</span>
            <span className="ability__mod">
              <Signed value={formatModifier(r.modifier)} />
            </span>
            <span className="ability__score">{r.total}</span>
          </li>
        ))}
      </ul>
      <dl className="summary-strip__stats">
        {prof !== undefined && (
          <div className="sheet-box stat-box" data-summary="proficiencyBonus" data-section="proficiencyBonus">
            <dt>
              <span className="stat-box__top">{b.profTop}</span> <span className="stat-box__bottom">{b.profBottom}</span>
            </dt>
            <dd>
              <Signed value={formatModifier(prof)} />
            </dd>
          </div>
        )}
        {first && (
          <div className="sheet-box stat-box" data-summary="speed" data-section="speeds">
            <dt>
              <span className="stat-box__top stat-box__top--grey">{t.sheet.speeds.modes[first.mode] ?? b.speedTop}</span>{" "}
              <span className="stat-box__bottom">{b.speedBottom}</span>
            </dt>
            <dd>
              {first.feet}
              <span className="stat-box__unit">{b.feetUnit}</span>
            </dd>
            {extraSpeeds.map((sp) => (
              <span key={sp.mode} className="summary-strip__sub">
                {t.sheet.speeds.modes[sp.mode] ?? sp.mode} {t.common.feet(sp.feet)}
              </span>
            ))}
          </div>
        )}
        {hp && (
          <div className="sheet-box stat-box stat-box--hp" data-summary="hitPoints" data-section="hitPoints">
            <dt className="stat-box__bottom">{b.hpTitle}</dt>
            <dd className="hp-cell">
              <span className="hp-cell__label">{b.hpMax}</span>
              <span className="hp-cell__value">{hp.max}</span>
            </dd>
            {hp.hitDice && (
              <dd className="hp-cell" data-summary="hitDice">
                <span className="hp-cell__label">{b.hpDice}</span>
                <span className="hp-cell__value hp-cell__value--dice">{hp.hitDice}</span>
              </dd>
            )}
          </div>
        )}
      </dl>
    </section>
  );
}

/** Initiative and Armor Class boxes, then the defenses box when the character has any: the row over the tab panel. */
export function CombatRow({ sections }: { sections: SheetSection[] }) {
  const t = useT();
  const ac = data(sections, "armorClass");
  const initiative = data(sections, "initiative");
  const defenses = data(sections, "defenses");
  return (
    <div className="sheet-combat">
      <dl className="sheet-combat__stats">
        {initiative !== undefined && (
          <div className="sheet-box stat-box" data-summary="initiative" data-section="initiative">
            <dt>{t.sheet.boxes.initiative}</dt>
            <dd>
              <Signed value={formatModifier(initiative)} />
            </dd>
          </div>
        )}
        {ac && (
          <div className="sheet-box stat-box stat-box--ac" data-summary="armorClass" data-section="armorClass">
            <dt>
              <span className="stat-box__top stat-box__top--grey">{t.sheet.boxes.acTop}</span>{" "}
              <span className="stat-box__bottom stat-box__bottom--grey">{t.sheet.boxes.acBottom}</span>
            </dt>
            <dd>{ac.value}</dd>
          </div>
        )}
      </dl>
      {defenses && <DefensesSection data={defenses} />}
      {ac?.stealthDisadvantage && (
        <p className="summary-strip__note" data-summary="stealthDisadvantage">
          {t.sheet.armorClass.stealthDisadvantage}
        </p>
      )}
    </div>
  );
}
