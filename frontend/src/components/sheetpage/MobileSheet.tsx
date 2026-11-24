import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useDraft } from "../../DraftContext";
import { useT } from "../../LanguageContext";
import { useLibrary } from "../../LibraryContext";
import { formatModifier } from "../../logic/abilities";
import { currentHp } from "../../logic/play";
import type { SheetSection, SheetSectionData } from "../../logic/sheetSections";
import type { Resolution } from "../../types";
import { HeroPortrait } from "../HeroPortrait";
import { DefensesSection } from "../sheet/EquipmentSection";
import { LanguagesSection, ProficienciesSection, SavingThrowsSection, SkillsSection } from "../sheet/ProficiencySections";
import { Signed } from "../sheet/Signed";
import { PassivesSection, SensesSection } from "../sheet/StatSections";
import { ActionsPanel, BackgroundPanel, FeaturesPanel, InventoryPanel, NotesPanel, SpellsPanel } from "./panels";
import { ConditionsEditor, HitPointsBox } from "./PlayBoxes";

function data<K extends SheetSection["key"]>(sections: SheetSection[], key: K): SheetSectionData[K] | undefined {
  return sections.find((s) => s.key === key)?.data as SheetSectionData[K] | undefined;
}

/** The phone sections, in the online app's menu order (docs/SHEET-DDB-SPEC-PHONE.md 3.1). */
export const PHONE_SECTIONS = [
  "abilities",
  "skills",
  "actions",
  "inventory",
  "spells",
  "speedDefenses",
  "features",
  "proficiencies",
  "background",
  "notes",
] as const;
export type PhoneSection = (typeof PHONE_SECTIONS)[number];

/** The section names exactly as on the online app (English game terms in both languages, like the sheet tabs). */
const SECTION_NAMES: Record<PhoneSection, string> = {
  abilities: "Abilities, Saves, Senses",
  skills: "Skills",
  actions: "Actions",
  inventory: "Inventory",
  spells: "Spells",
  speedDefenses: "Speed & Defenses",
  features: "Features & Traits",
  proficiencies: "Proficiencies & Training",
  background: "Background",
  notes: "Notes",
};

/** Small line icons of our own for the section bar and the menu (24 x 24, stroke only). */
const ICONS: Record<PhoneSection, string> = {
  abilities: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 8l4 7H8z",
  skills: "M6 4l1.2 3.3L10.5 8.5 7.2 9.7 6 13 4.8 9.7 1.5 8.5 4.8 7.3zM16 10l1 2.7 2.7 1-2.7 1-1 2.8-1-2.8-2.7-1 2.7-1zM17 2l.7 1.8 1.8.7-1.8.7L17 7l-.7-1.8-1.8-.7 1.8-.7z",
  actions: "M21 3L10 14M7 11l6 6M10 14l-5 5M4 20l1-1",
  inventory: "M4 9h16v10H4zM4 9l2-4h12l2 4M10 13h4",
  spells: "M12 3c2 3 5 5 5 9a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3 0-5 1-8z",
  speedDefenses: "M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6zM12 3v18",
  features: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6",
  proficiencies: "M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14zM15 15l6 6M10 6v5M10 13.5v.5",
  background: "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7",
  notes: "M4 5h12v9H8l-4 3zM20 9v9l-3-2h-7",
};

function SectionIcon({ section }: { section: PhoneSection }) {
  return (
    <svg className="m-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d={ICONS[section]} />
    </svg>
  );
}

/** The phone sheet, one to one with the online app (docs/SHEET-DDB-SPEC-PHONE.md): the stat area scrolls away, the section bar
 *  sticks under the top, and the sections sit side by side in a pager that you swipe left and right (or pick from the menu that
 *  the bar opens). Only the part under the bar changes. */
export function MobileSheet({ sections, resolution }: { sections: SheetSection[]; resolution: Resolution }) {
  const t = useT();
  const m = t.sheet.phone;
  const [index, setIndex] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sheet, setSheet] = useState<null | "hp" | "conditions">(null);
  const pager = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLDivElement>(null);
  const current = PHONE_SECTIONS[index];

  // the pager is as tall as the section on screen (each section keeps its own length)
  useLayoutEffect(() => {
    const el = pager.current?.children[index] as HTMLElement | undefined;
    if (!el) return;
    // the height is set on the element itself (no inline style objects in the sources)
    const update = () => pager.current?.style.setProperty("height", `${el.scrollHeight}px`);
    update();
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(update) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  }, [index]);

  function onScroll() {
    const el = pager.current;
    if (!el || !el.clientWidth) return;
    const i = Math.round(el.scrollLeft / el.clientWidth);
    if (i !== index && i >= 0 && i < PHONE_SECTIONS.length) setIndex(i);
  }

  function go(i: number) {
    const el = pager.current;
    setMenuOpen(false);
    setIndex(i);
    el?.scrollTo?.({ left: i * el.clientWidth, behavior: "smooth" });
    // a new section starts at its top: if the page was scrolled past the bar, bring the bar back to its sticky place
    const top = bar.current ? bar.current.getBoundingClientRect().top + window.scrollY - 64 : 0;
    if (window.scrollY > top) window.scrollTo({ top, behavior: "smooth" });
  }

  useEffect(() => {
    if (!menuOpen && !sheet) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setSheet(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen, sheet]);

  return (
    <div className="m-sheet">
      <MobileStats sections={sections} onHp={() => setSheet("hp")} onConditions={() => setSheet("conditions")} />

      <div className="m-bar" ref={bar}>
        <button type="button" className="m-bar__button" aria-haspopup="dialog" aria-expanded={menuOpen} onClick={() => setMenuOpen(true)}>
          <SectionIcon section={current} />
          <span className="m-bar__title">{SECTION_NAMES[current]}</span>
          <span className="m-bar__dots" aria-hidden="true">
            {Array.from({ length: 9 }, (_, i) => (
              <span key={i} />
            ))}
          </span>
          <span className="m-bar__list" aria-hidden="true">
            <svg className="m-icon" viewBox="0 0 24 24" focusable="false">
              <path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" />
            </svg>
          </span>
        </button>
      </div>

      <div className="m-pager" ref={pager} onScroll={onScroll} aria-live="polite">
        {PHONE_SECTIONS.map((key, i) => (
          <section
            key={key}
            className="m-page"
            data-phone-section={key}
            aria-label={SECTION_NAMES[key]}
            aria-hidden={i !== index || undefined}
            inert={i !== index || undefined}
          >
            {Math.abs(i - index) <= 1 && <PhonePage section={key} sections={sections} resolution={resolution} />}
          </section>
        ))}
      </div>

      {menuOpen && (
        <div className="m-modal" role="dialog" aria-modal="true" aria-label={m.menuLabel}>
          <div className="m-modal__sheet">
            <div className="m-modal__top">
              <button type="button" className="m-modal__close" aria-label={m.close} onClick={() => setMenuOpen(false)}>
                <span aria-hidden="true">×</span>
              </button>
            </div>
            <ul className="m-menu">
              {PHONE_SECTIONS.map((key, i) => (
                <li key={key}>
                  <button type="button" aria-current={i === index ? "true" : undefined} onClick={() => go(i)}>
                    <SectionIcon section={key} />
                    {SECTION_NAMES[key]}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {sheet && (
        <div className="m-modal" role="dialog" aria-modal="true" aria-label={sheet === "hp" ? t.sheet.boxes.hpTitle : t.sheet.boxes.conditions}>
          <div className="m-modal__sheet">
            <div className="m-modal__top">
              <button type="button" className="m-modal__close" aria-label={m.close} onClick={() => setSheet(null)}>
                <span aria-hidden="true">×</span>
              </button>
              <h2 className="m-modal__title">{sheet === "hp" ? t.sheet.boxes.hpTitle : t.sheet.boxes.conditions}</h2>
            </div>
            <div className="m-modal__body">
              {sheet === "hp" ? <HitPointsBox sections={sections} /> : <ConditionsEditor open />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** The stat area: armor class (shield), initiative (hexagon), the portrait with the Heroic Inspiration badge, the hit points
 *  box (opens the hit point sheet) and the CONDITIONS button. It scrolls away with the page. */
function MobileStats({ sections, onHp, onConditions }: { sections: SheetSection[]; onHp: () => void; onConditions: () => void }) {
  const t = useT();
  const b = t.sheet.boxes;
  const { draft, dispatch } = useDraft();
  const { activeId } = useLibrary();
  const identity = data(sections, "identity");
  const ac = data(sections, "armorClass");
  const initiative = data(sections, "initiative");
  const hp = data(sections, "hitPoints");
  const max = hp?.max ?? 0;
  const cur = currentHp(max, draft.play?.damage);
  const temp = draft.play?.tempHp ?? 0;
  const conditions = draft.play?.conditions ?? [];
  const classLine = identity?.classes.map((c) => `${c.name} ${c.level}`).join(" / ");
  return (
    <>
      <header className="m-name">
        <strong>
          {identity?.name || (
            <Link to="/home" className="sheet-name-prompt">
              {t.sheet.nameIt}
            </Link>
          )}
        </strong>
        <span>{[identity?.species?.name, classLine].filter(Boolean).join(" ")}</span>
      </header>
      <div className="m-stats">
        {ac && (
          <div className="m-ac" data-summary="armorClass">
            <span className="m-label">{b.acTop}</span>
            <span className="m-ac__shield">{ac.value}</span>
            <span className="m-label">{b.acBottom}</span>
          </div>
        )}
        {initiative !== undefined && (
          <div className="m-init" data-summary="initiative">
            <span className="m-init__hex">
              <Signed value={formatModifier(initiative)} />
            </span>
            <span className="m-label">{b.initiative}</span>
          </div>
        )}
        <div className="m-portrait">
          <HeroPortrait id={activeId} classId={identity?.classes[0]?.id} />
          <button
            type="button"
            className="m-portrait__badge"
            aria-pressed={!!draft.play?.inspiration}
            aria-label={b.inspiration}
            onClick={() => dispatch({ type: "TOGGLE_INSPIRATION" })}
          >
            <span aria-hidden="true">★</span>
          </button>
          <span className="m-label m-portrait__label">{b.inspiration}</span>
        </div>
        {hp && (
          <button type="button" className="m-hp" data-summary="hitPoints" onClick={onHp}>
            <span className="m-label">{b.hpTitle}</span>
            <span className="m-hp__value">
              {cur}/{max}
              {temp > 0 && <span className="m-hp__temp"> ({temp})</span>}
            </span>
            {/* the bar: blue for the current points, green after it for the temporary ones (SVG, no inline styles) */}
            <svg className="m-hp__bar" viewBox="0 0 100 3" preserveAspectRatio="none" aria-hidden="true" focusable="false">
              <rect className="m-hp__fill" x={0} y={0} height={3} width={max ? (cur / (max + temp)) * 100 : 0} />
              {temp > 0 && (
                <rect className="m-hp__fill m-hp__fill--temp" x={max ? (cur / (max + temp)) * 100 : 0} y={0} height={3} width={(temp / (max + temp)) * 100} />
              )}
            </svg>
          </button>
        )}
        <button type="button" className="m-conditions" onClick={onConditions}>
          {b.conditions}
          {conditions.length > 0 && ` (${conditions.length})`}
        </button>
      </div>
    </>
  );
}

function PhonePage({ section, sections, resolution }: { section: PhoneSection; sections: SheetSection[]; resolution: Resolution }) {
  const t = useT();
  const b = t.sheet.boxes;
  const abilities = data(sections, "abilities");
  let body: ReactNode = null;
  switch (section) {
    case "abilities": {
      const saves = data(sections, "savingThrows");
      const passives = data(sections, "passives");
      const senses = data(sections, "senses");
      body = (
        <>
          <ul className="m-abilities">
            {(abilities ?? []).map((r) => (
              <li key={r.ability} className="sheet-box ability-box">
                <span className="ability__label">{b.abilityNames[r.ability] ?? r.ability}</span>
                <span className="ability__mod">
                  <Signed value={formatModifier(r.modifier)} />
                </span>
                <span className="ability__score">{r.total}</span>
              </li>
            ))}
          </ul>
          {saves && <SavingThrowsSection data={saves} />}
          {passives && <PassivesSection data={passives} />}
          {senses && <SensesSection data={senses} />}
        </>
      );
      break;
    }
    case "skills": {
      const skills = data(sections, "skills");
      body = skills ? <SkillsSection data={skills} /> : null;
      break;
    }
    case "actions":
      body = <ActionsPanel sections={sections} />;
      break;
    case "inventory":
      body = <InventoryPanel sections={sections} />;
      break;
    case "spells":
      body = <SpellsPanel sections={sections} resolution={resolution} />;
      break;
    case "speedDefenses": {
      const speeds = data(sections, "speeds") ?? [];
      const defenses = data(sections, "defenses");
      body = (
        <>
          <h3 className="m-heading">{t.sheet.phone.speedHeading}</h3>
          <ul className="m-speeds">
            {speeds.map((sp) => (
              <li key={sp.mode}>
                {t.sheet.speeds.modes[sp.mode] ?? sp.mode}: <strong>{sp.feet}</strong> <span className="stat-box__unit">{b.feetUnit}</span>
              </li>
            ))}
          </ul>
          <h3 className="m-heading">{b.defenses}</h3>
          {defenses ? <DefensesSection data={defenses} /> : <p className="m-muted">{b.noDefenses}</p>}
        </>
      );
      break;
    }
    case "features":
      body = <FeaturesPanel resolution={resolution} />;
      break;
    case "proficiencies": {
      const prof = data(sections, "proficiencyBonus");
      const proficiencies = data(sections, "proficiencies");
      const languages = data(sections, "languages");
      body = (
        <>
          {prof !== undefined && (
            <p className="m-prof">
              <span className="m-prof__value">
                <Signed value={formatModifier(prof)} />
              </span>
              <span className="m-label">
                {b.profTop} {b.profBottom}
              </span>
            </p>
          )}
          {proficiencies ? <ProficienciesSection data={proficiencies} languages={languages} /> : languages && <LanguagesSection data={languages} />}
        </>
      );
      break;
    }
    case "background":
      body = <BackgroundPanel sections={sections} />;
      break;
    case "notes":
      body = <NotesPanel sections={sections} />;
      break;
  }
  // "sheet-reference" gives the saves, passives and skills the same pills and boxes as on the wide sheet
  return <div className="m-page__inner sheet-reference">{body}</div>;
}
