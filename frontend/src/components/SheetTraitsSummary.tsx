import { useT } from "../LanguageContext";
import { slugTitle } from "../logic/labels";
import type { Sheet } from "../types";

// Same wording as the exports (server/export_fields.py `extra_blocks` and markdown_export.py); the words live in the catalog.
const DAMAGE_SECTIONS = ["resistances", "immunities", "vulnerabilities"] as const;

/** Read-only senses, damage modifiers, condition immunities and innate spells of the sheet. */
export function SheetTraitsSummary({ sheet }: { sheet: Sheet }) {
  const t = useT();
  const senses = Object.entries(sheet.senses ?? {});
  const damage = sheet.damageModifiers;
  const damageLines = DAMAGE_SECTIONS.filter((key) => (damage?.[key]?.length ?? 0) > 0);
  const conditions = sheet.conditionImmunities ?? [];
  const innate = sheet.innateSpells ?? [];
  return (
    <>
      {senses.length > 0 && (
        <div>
          <h2>{t.sheet.senses.title}</h2>
          <ul>
            {senses.map(([k, v]) => (
              <li key={k}>{t.traits.senseLine(t.sheet.senses.kinds[k] ?? k, v)}</li>
            ))}
          </ul>
        </div>
      )}
      {(damageLines.length > 0 || conditions.length > 0) && (
        <div>
          <h2>{t.sheet.defenses.title}</h2>
          <ul>
            {damageLines.map((key) => (
              <li key={key}>
                {t.sheet.defenses[key]}: {damage![key].map(slugTitle).join(", ")}
              </li>
            ))}
            {conditions.length > 0 && (
              <li>
                {t.sheet.defenses.conditionImmunities}: {conditions.map(slugTitle).join(", ")}
              </li>
            )}
          </ul>
        </div>
      )}
      {innate.length > 0 && (
        <div>
          <h2>{t.sheet.innateSpells.title}</h2>
          <ul>
            {innate.map((e, i) => (
              <li key={`${e.spellId ?? e.name}:${i}`}>
                {t.sheet.innateSpells.line(e.name, e.uses, e.level)}
                {e.note ? ` - ${e.note}` : ""}
                {e.source ? ` [${e.source}]` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
