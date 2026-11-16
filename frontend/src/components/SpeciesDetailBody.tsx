import { useEffect, useRef, useState } from "react";
import { useT } from "../LanguageContext";
import type { Copy } from "../copy";
import { renderMsg, toMsg, type Msg } from "../logic/messages";
import { fetchSpeciesDetail, type SpeciesDetail } from "../useSpeciesDetail";

export type SpeciesDetailState =
  | { status: "loading" }
  | { status: "error"; message: Msg }
  | { status: "ready"; species: SpeciesDetail };

/** Lazily fetched species details keyed by species id: `loadDetail(id)` fetches once (a failed fetch may be retried). */
export function useSpeciesDetails() {
  const [details, setDetails] = useState<Record<string, SpeciesDetailState>>({});
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
    fetchSpeciesDetail(id)
      .then((species) => {
        if (alive.current) setDetails((d) => ({ ...d, [id]: { status: "ready", species } }));
      })
      .catch((err: unknown) => {
        if (!alive.current) return;
        requested.current.delete(id); // closing and reopening the row retries
        setDetails((d) => ({ ...d, [id]: { status: "error", message: toMsg(err) } }));
      });
  }

  return { details, loadDetail };
}

interface Fact {
  key: string;
  label: string;
  value: string;
}

const signed = (n: number) => (n >= 0 ? `+${n}` : `${n}`);

/** The quick facts of a species, only those the record has: size, speed, darkvision, ability scores, resistance, languages. */
export function speciesFacts(t: Copy, s: SpeciesDetail): Fact[] {
  const p = t.speciesPage.preview;
  const facts: Fact[] = [];
  const sizes = s.size_options?.length > 1 ? s.size_options : [s.size];
  facts.push({ key: "size", label: p.size, value: sizes.join(" / ") });

  const modes = Object.entries(s.movement ?? {}).map(
    ([mode, v]) => `${t.sheet.speeds.modes[mode] ?? mode} ${t.common.feet(v === true ? s.speed : v)}`,
  );
  facts.push({ key: "speed", label: p.speed, value: [t.common.feet(s.speed), ...modes].join(", ") });

  if (s.darkvision) facts.push({ key: "darkvision", label: p.darkvision, value: t.common.feet(s.darkvision) });

  const fixedAbilities = (s.ability_bonuses ?? []).map((b) => `${b.ability_score.name} ${signed(b.bonus)}`);
  const pickAbilities = s.ability_bonus_options
    ? [p.chooseFrom(s.ability_bonus_options.choose, (s.ability_bonus_options.from.options ?? []).map((o) => `${o.ability_score?.name ?? ""} ${signed(o.bonus ?? 0)}`).join(", "))]
    : [];
  if (fixedAbilities.length + pickAbilities.length > 0) {
    facts.push({ key: "abilities", label: p.abilities, value: [...fixedAbilities, ...pickAbilities].join("; ") });
  }

  const pickResist = s.resist_options
    ? [p.chooseFrom(s.resist_options.choose, (s.resist_options.from.options ?? []).map((o) => o.string ?? "").join(", "))]
    : [];
  if ((s.resist ?? []).length + pickResist.length > 0) {
    facts.push({ key: "resist", label: p.resistance, value: [...s.resist, ...pickResist].join("; ") });
  }

  const languages = (s.languages ?? []).map((l) => l.name);
  if (s.language_options) languages.push(p.moreLanguages(s.language_options.choose));
  if (languages.length > 0) facts.push({ key: "languages", label: p.languages, value: languages.join(", ") });
  return facts;
}

export function SpeciesDetailBody({ state }: { state: SpeciesDetailState | undefined }) {
  const t = useT();
  if (!state || state.status === "loading") return <p className="species-eye__status">{t.common.loading}</p>;
  if (state.status === "error") return <p className="species-eye__status">{t.common.errorLine(renderMsg(t, state.message))}</p>;
  const { species } = state;
  return (
    <div className="species-eye__body">
      <p className="species-eye__facts">
        {speciesFacts(t, species).map((f) => (
          <span key={f.key} className="species-eye__fact">
            <span className="species-eye__fact-label">{f.label}</span> {f.value}
          </span>
        ))}
      </p>
      {species.fluff.map((paragraph, i) => (
        <p key={i} className="species-eye__lore">
          {paragraph}
        </p>
      ))}
      {species.traitDetails.length > 0 && (
        <dl className="species-eye__traits">
          {species.traitDetails.map((trait, i) => (
            <div key={i} className="species-eye__trait">
              <dt className="species-eye__trait-name">{trait.name}</dt>
              {trait.desc.map((line, j) => (
                <dd key={j} className="species-eye__trait-text">
                  {line}
                </dd>
              ))}
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
