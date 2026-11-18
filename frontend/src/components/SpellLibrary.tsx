import { useState } from "react";
import { useDraft } from "../DraftContext";
import { useT } from "../LanguageContext";
import { localizeSpellRow } from "../logic/spellRow";
import { renderMsg } from "../logic/messages";
import { useSpells, type CatalogSpell } from "../useSpells";
import { SpellDetailBody, useSpellDetails } from "./SpellDetailBody";

type LevelFilter = "" | "0" | "1";

const LEVEL_FILTERS: { value: LevelFilter; key: "all" | "cantrips" | "level1" }[] = [
  { value: "", key: "all" },
  { value: "0", key: "cantrips" },
  { value: "1", key: "level1" },
];

interface SpellLibraryProps {
  classId: string;
}

export function SpellLibrary({ classId }: SpellLibraryProps) {
  const t = useT();
  const sl = t.spellLibrary;
  const { draft } = useDraft();
  const [levelFilter, setLevelFilter] = useState<LevelFilter>("");
  const [query, setQuery] = useState("");
  const cantrips = useSpells(classId, "0", query, draft.ruleset, draft.sources);
  const knownSpells = useSpells(classId, "1", query, draft.ruleset, draft.sources);
  // The list rows are slim; a spell's text is fetched when its card is first opened.
  const { details, loadDetail } = useSpellDetails();

  const loading = cantrips.loading || knownSpells.loading;
  const error = cantrips.error ?? knownSpells.error;
  const merged: CatalogSpell[] = [...cantrips.spells, ...knownSpells.spells].sort((a, b) =>
    a.name.localeCompare(b.name),
  );
  const visible = levelFilter === "" ? merged : merged.filter((s) => String(s.level) === levelFilter);

  function retry() {
    cantrips.retry();
    knownSpells.retry();
  }

  return (
    <>
      <h2>{sl.title} {loading && "…"}</h2>
      <input type="text" inputMode="search" enterKeyHint="search" aria-label={sl.searchLabel} placeholder={t.common.search} value={query} onChange={(e) => setQuery(e.target.value)} />
      <select aria-label={sl.levelLabel} value={levelFilter} onChange={(e) => setLevelFilter(e.target.value as LevelFilter)}>
        {LEVEL_FILTERS.map((l) => (
          <option key={l.value} value={l.value}>
            {sl.filters[l.key]}
          </option>
        ))}
      </select>
      {error && (
        <p>
          {t.common.errorLine(renderMsg(t, error))}{" "}
          <button type="button" onClick={retry}>
            {t.common.retry}
          </button>
        </p>
      )}
      <ul className="spell-library-list">
        {visible.map((spell) => {
          const row = localizeSpellRow(t.spellRow, spell);
          return (
          <li key={spell.id} className="spell-library-card">
            <details
              onToggle={(e) => {
                if ((e.currentTarget as HTMLDetailsElement).open) loadDetail(spell.id);
              }}
            >
              <summary>
                <span className="spell-library-card__header">
                  <span className="spell-library-card__name">{spell.name}</span>
                  <span className="spell-library-card__level">{spell.level === 0 ? sl.cantrip : sl.levelBadge(spell.level)}</span>
                </span>
                <span className="spell-library-card__meta">
                  {row.school && <span>{row.school}</span>}
                  {row.castingTime && <span>{row.castingTime}</span>}
                  {row.range && <span>{row.range}</span>}
                  {spell.components.length > 0 && <span>{spell.components.join(", ")}</span>}
                  {row.duration && <span>{row.duration}</span>}
                  {spell.concentration && <span>{sl.concentration}</span>}
                  {spell.ritual && <span>{sl.ritual}</span>}
                </span>
              </summary>
              <SpellDetailBody state={details[spell.id]} />
            </details>
          </li>
          );
        })}
      </ul>
    </>
  );
}
