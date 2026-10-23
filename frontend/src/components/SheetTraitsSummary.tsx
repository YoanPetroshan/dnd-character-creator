import type { Sheet } from "../types";

// Same wording as the exports (server/export_fields.py `extra_blocks` and markdown_export.py).
const SENSE_NAMES: Record<string, string> = {
  darkvision: "тъмно зрение", blindsight: "сляпо зрение",
  tremorsense: "усещане за вибрации", truesight: "истинско зрение", devilsSight: "дяволско зрение",
};
const DAMAGE_SECTIONS = [
  ["resistances", "Устойчивост"],
  ["immunities", "Имунитет"],
  ["vulnerabilities", "Уязвимост"],
] as const;

const title = (slug: string) => {
  const s = slug.replace(/-/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
};

/** Read-only senses, damage modifiers, condition immunities and innate spells of the sheet. */
export function SheetTraitsSummary({ sheet }: { sheet: Sheet }) {
  const senses = Object.entries(sheet.senses ?? {});
  const damage = sheet.damageModifiers;
  const damageLines = DAMAGE_SECTIONS.filter(([key]) => (damage?.[key]?.length ?? 0) > 0);
  const conditions = sheet.conditionImmunities ?? [];
  const innate = sheet.innateSpells ?? [];
  return (
    <>
      {senses.length > 0 && (
        <div>
          <h2>Сетива</h2>
          <ul>
            {senses.map(([k, v]) => (
              <li key={k}>
                {SENSE_NAMES[k] ?? k} {v} фута
              </li>
            ))}
          </ul>
        </div>
      )}
      {(damageLines.length > 0 || conditions.length > 0) && (
        <div>
          <h2>Съпротиви и имунитети</h2>
          <ul>
            {damageLines.map(([key, label]) => (
              <li key={key}>
                {label} към щета: {damage![key].map(title).join(", ")}
              </li>
            ))}
            {conditions.length > 0 && <li>Имунитет към състояния: {conditions.map(title).join(", ")}</li>}
          </ul>
        </div>
      )}
      {innate.length > 0 && (
        <div>
          <h2>Вродени заклинания</h2>
          <ul>
            {innate.map((e, i) => (
              <li key={`${e.spellId ?? e.name}:${i}`}>
                {e.name} ({e.uses}
                {e.level ? `, от ниво ${e.level}` : ""}){e.note ? ` - ${e.note}` : ""}
                {e.source ? ` [${e.source}]` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
