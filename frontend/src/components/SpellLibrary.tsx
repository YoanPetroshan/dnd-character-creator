import { useState } from "react";
import { useSpells, type CatalogSpell } from "../useSpells";

type LevelFilter = "" | "0" | "1";

const LEVEL_FILTERS: { value: LevelFilter; label: string }[] = [
  { value: "", label: "Всички избираеми" },
  { value: "0", label: "Трикове" },
  { value: "1", label: "1-во ниво" },
];

interface SpellLibraryProps {
  classId: string;
}

export function SpellLibrary({ classId }: SpellLibraryProps) {
  const [levelFilter, setLevelFilter] = useState<LevelFilter>("");
  const [query, setQuery] = useState("");
  const cantrips = useSpells(classId, "0", query);
  const knownSpells = useSpells(classId, "1", query);

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
      <h2>Списък със заклинания {loading && "…"}</h2>
      <input type="text" placeholder="Търсене…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value as LevelFilter)}>
        {LEVEL_FILTERS.map((l) => (
          <option key={l.value} value={l.value}>
            {l.label}
          </option>
        ))}
      </select>
      {error && (
        <p>
          Грешка: {error}{" "}
          <button type="button" onClick={retry}>
            Опитай пак
          </button>
        </p>
      )}
      <ul className="spell-library-list">
        {visible.map((spell) => (
          <li key={spell.id} className="spell-library-card">
            <div className="spell-library-card__header">
              <span className="spell-library-card__name">{spell.name}</span>
              <span className="spell-library-card__level">{spell.level === 0 ? "Трик" : `${spell.level} ниво`}</span>
            </div>
            <div className="spell-library-card__meta">
              {spell.school && <span>{spell.school}</span>}
              {spell.castingTime && <span>{spell.castingTime}</span>}
              {spell.range && <span>{spell.range}</span>}
              {spell.components.length > 0 && <span>{spell.components.join(", ")}</span>}
              {spell.duration && <span>{spell.duration}</span>}
              {spell.concentration && <span>Концентрация</span>}
              {spell.ritual && <span>Ритуал</span>}
            </div>
            {spell.material && <p className="spell-library-card__material">{spell.material}</p>}
            <p className="spell-library-card__desc">{spell.desc}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
