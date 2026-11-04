import type { SheetSection } from "../../logic/sheetSections";
import { AbilitiesSection } from "./AbilitiesSection";
import { AttacksSection } from "./AttacksSection";
import { DetailsSection } from "./DetailsSection";
import { CarryingCapacitySection, DefensesSection, EquipmentSection } from "./EquipmentSection";
import { FeatsSection, FeaturesSection } from "./FeaturesSection";
import { IdentitySection } from "./IdentitySection";
import { LanguagesSection, ProficienciesSection, SavingThrowsSection, SkillsSection } from "./ProficiencySections";
import { ResourcesSection } from "./ResourcesSection";
import { InnateSpellsSection, SpellsSection } from "./SpellsSection";
import {
  ArmorClassSection,
  HitPointsSection,
  InitiativeSection,
  PassivesSection,
  ProficiencyBonusSection,
  SensesSection,
  SpeedsSection,
} from "./StatSections";

function renderSection(s: SheetSection) {
  switch (s.key) {
    case "identity": return <IdentitySection key={s.key} data={s.data} />;
    case "abilities": return <AbilitiesSection key={s.key} data={s.data} />;
    case "proficiencyBonus": return <ProficiencyBonusSection key={s.key} data={s.data} />;
    case "armorClass": return <ArmorClassSection key={s.key} data={s.data} />;
    case "hitPoints": return <HitPointsSection key={s.key} data={s.data} />;
    case "initiative": return <InitiativeSection key={s.key} data={s.data} />;
    case "speeds": return <SpeedsSection key={s.key} data={s.data} />;
    case "senses": return <SensesSection key={s.key} data={s.data} />;
    case "passives": return <PassivesSection key={s.key} data={s.data} />;
    case "savingThrows": return <SavingThrowsSection key={s.key} data={s.data} />;
    case "skills": return <SkillsSection key={s.key} data={s.data} />;
    case "proficiencies": return <ProficienciesSection key={s.key} data={s.data} />;
    case "languages": return <LanguagesSection key={s.key} data={s.data} />;
    case "attacks": return <AttacksSection key={s.key} data={s.data} />;
    case "resources": return <ResourcesSection key={s.key} data={s.data} />;
    case "features": return <FeaturesSection key={s.key} data={s.data} />;
    case "feats": return <FeatsSection key={s.key} data={s.data} />;
    case "spells": return <SpellsSection key={s.key} data={s.data} />;
    case "innateSpells": return <InnateSpellsSection key={s.key} data={s.data} />;
    case "equipment": return <EquipmentSection key={s.key} data={s.data} />;
    case "carryingCapacity": return <CarryingCapacitySection key={s.key} data={s.data} />;
    case "defenses": return <DefensesSection key={s.key} data={s.data} />;
    case "details": return <DetailsSection key={s.key} data={s.data} />;
  }
}

/** All sections of the sheet in order. Presentational: it only maps section data to components. */
export function SheetView({ sections }: { sections: SheetSection[] }) {
  return <>{sections.map(renderSection)}</>;
}
