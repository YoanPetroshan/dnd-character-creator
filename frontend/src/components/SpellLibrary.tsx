import { useEffect, useRef, useState } from "react";
import { useDraft } from "../DraftContext";
import { fetchSpellDetail, useSpells, type CatalogSpell, type SpellDetail } from "../useSpells";

type LevelFilter = "" | "0" | "1";

const LEVEL_FILTERS: { value: LevelFilter; label: string }[] = [
  { value: "", label: "Всички избираеми" },
  { value: "0", label: "Трикове" },
  { value: "1", label: "1-во ниво" },
];

interface SpellLibraryProps {
  classId: string;
}

type DetailState = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; spell: SpellDetail };

export function SpellLibrary({ classId }: SpellLibraryProps) {
  const { draft } = useDraft();
  const [levelFilter, setLevelFilter] = useState<LevelFilter>("");
  const [query, setQuery] = useState("");
  const cantrips = useSpells(classId, "0", query, draft.ruleset, draft.sources);
  const knownSpells = useSpells(classId, "1", query, draft.ruleset, draft.sources);
  // The list rows are slim; a spell's text is fetched when its card is first opened.
  const [details, setDetails] = useState<Record<string, DetailState>>({});
  const requested = useRef(new Set<string>());
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode runs mount, cleanup, mount
    return () => {
      alive.current = false;
    };
  }, []);

  function loadDetail(id: string) {
    if (requested.current.has(id)) return;
    requested.current.add(id);
    setDetails((d) => ({ ...d, [id]: { status: "loading" } }));
    fetchSpellDetail(id)
      .then((spell) => {
        if (alive.current) setDetails((d) => ({ ...d, [id]: { status: "ready", spell } }));
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        requested.current.delete(id); // closing and reopening the card retries
        setDetails((d) => ({ ...d, [id]: { status: "error", message: err instanceof Error ? err.message : String(err) } }));
      });
  }

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
      <input type="text" inputMode="search" enterKeyHint="search" aria-label="Търсене на заклинания" placeholder="Търсене…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <select aria-label="Ниво на заклинанията" value={levelFilter} onChange={(e) => setLevelFilter(e.target.value as LevelFilter)}>
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
            <details
              onToggle={(e) => {
                if ((e.currentTarget as HTMLDetailsElement).open) loadDetail(spell.id);
              }}
            >
              <summary>
                <span className="spell-library-card__header">
                  <span className="spell-library-card__name">{spell.name}</span>
                  <span className="spell-library-card__level">{spell.level === 0 ? "Трик" : `${spell.level} ниво`}</span>
                </span>
                <span className="spell-library-card__meta">
                  {spell.school && <span>{spell.school}</span>}
                  {spell.castingTime && <span>{spell.castingTime}</span>}
                  {spell.range && <span>{spell.range}</span>}
                  {spell.components.length > 0 && <span>{spell.components.join(", ")}</span>}
                  {spell.duration && <span>{spell.duration}</span>}
                  {spell.concentration && <span>Концентрация</span>}
                  {spell.ritual && <span>Ритуал</span>}
                </span>
              </summary>
              <SpellDetailBody state={details[spell.id]} />
            </details>
          </li>
        ))}
      </ul>
    </>
  );
}

function SpellDetailBody({ state }: { state: DetailState | undefined }) {
  if (!state || state.status === "loading") return <p className="spell-library-card__desc">Зареждане…</p>;
  if (state.status === "error") return <p className="spell-library-card__desc">Грешка: {state.message}</p>;
  const { spell } = state;
  return (
    <div className="spell-library-card__body">
      {spell.material && <p className="spell-library-card__material">{spell.material}</p>}
      {spell.castingCondition && <p className="spell-library-card__material">{spell.castingCondition}</p>}
      {spell.desc.map((paragraph, i) => (
        <p key={i} className="spell-library-card__desc">
          {paragraph}
        </p>
      ))}
      {spell.higherLevel.map((paragraph, i) => (
        <p key={`h${i}`} className="spell-library-card__desc">
          {paragraph}
        </p>
      ))}
      <p className="spell-library-card__material">
        {spell.sourceName}
        {spell.classes.length > 0 && ` · ${spell.classes.map((c) => c.name).join(", ")}`}
      </p>
    </div>
  );
}
