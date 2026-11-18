// The data values of a spell list row (school, casting time, range, duration) are English in the catalog; in Bulgarian
// mode the row shows them in Bulgarian. Pure: the words come from a copy table (`t.spellRow`); a value no pattern
// matches is returned unchanged, so a new catalog value shows in English rather than breaking the row.
export interface SpellRowCopy {
  /** false (English): every value is returned as it is. */
  localize: boolean;
  schools: Record<string, string>;
  /** Fixed values, lower-case English key -> text ("self", "touch", "instantaneous", "special", ...). */
  words: Record<string, string>;
  /** Casting time without a number: "1 action", "1 bonus action", "1 reaction" (key: the English noun phrase). */
  actions: Record<string, string>;
  /** The noun of a time unit, singular and plural, key: the English unit ("minute" / "minutes", "hour", "round", "day"). */
  units: Record<string, string>;
  mile: { one: string; many: string };
  feet: (n: number) => string;
  /** "60 feet" -> feet(60) + metres in brackets. */
  withMetres: (feet: string, metres: string) => string;
  shapes: Record<string, string>;
  /** "Self (30-foot cone)" -> `Себе си, конус 30 фута (9 м)`. */
  selfShape: (self: string, shape: string, size: string) => string;
  upTo: string;
  or: string;
  kilometres: (km: string) => string;
  metres: (m: string) => string;
}

export interface SpellRowValues {
  school: string | null;
  castingTime: string | null;
  range: string | null;
  duration: string | null;
}

const decimal = (n: number): string => {
  const rounded = Math.round(n * 10) / 10;
  return String(rounded).replace(".", ",");
};

const cap = (s: string): string => (s ? s[0].toUpperCase() + s.slice(1) : s);

function unit(c: SpellRowCopy, n: number, key: string): string | null {
  const word = c.units[n === 1 ? key : `${key}s`];
  return word ? `${n} ${word}` : null;
}

function localizeTime(c: SpellRowCopy, value: string): string | null {
  const exact = c.actions[value.toLowerCase()];
  if (exact) return exact;
  const m = /^(\d+) (minute|hour|round|day)s?$/i.exec(value);
  return m ? unit(c, Number(m[1]), m[2].toLowerCase()) : null;
}

function distance(c: SpellRowCopy, n: number, u: "foot" | "mile"): string {
  if (u === "mile") {
    return `${n} ${n === 1 ? c.mile.one : c.mile.many} (${c.kilometres(decimal(n * 1.6))})`;
  }
  return c.withMetres(c.feet(n), c.metres(decimal(n * 0.3)));
}

function localizeRange(c: SpellRowCopy, value: string): string | null {
  const word = c.words[value.toLowerCase()];
  if (word) return word;
  let m = /^(\d+) (feet|foot|miles?)$/i.exec(value);
  if (m) return distance(c, Number(m[1]), m[2].toLowerCase().startsWith("mile") ? "mile" : "foot");
  m = /^Self \((\d+)-foot (\w+)\)$/i.exec(value);
  if (m && c.shapes[m[2].toLowerCase()]) {
    return c.selfShape(c.words.self, c.shapes[m[2].toLowerCase()], distance(c, Number(m[1]), "foot"));
  }
  return null;
}

function localizeDuration(c: SpellRowCopy, value: string): string | null {
  const parts = value.split(/ or /i);
  if (parts.length > 1) {
    const each = parts.map((p) => localizeDuration(c, p));
    return each.every((x) => x !== null) ? each.map((x, i) => (i === 0 ? x : (x as string).toLowerCase())).join(` ${c.or} `) : null;
  }
  const word = c.words[value.toLowerCase()];
  if (word) return word;
  const m = /^up to (\d+) (minute|hour|round|day)s?$/i.exec(value);
  if (m) {
    const u = unit(c, Number(m[1]), m[2].toLowerCase());
    return u ? `${c.upTo} ${u}` : null;
  }
  return localizeTime(c, value);
}

/** The row's data values for display; `null` stays `null`, an unknown value stays as it came. */
export function localizeSpellRow(c: SpellRowCopy, row: SpellRowValues): SpellRowValues {
  if (!c.localize) return row;
  const pick = (value: string | null, fn: (c: SpellRowCopy, v: string) => string | null) => {
    if (value === null) return null;
    const out = fn(c, value.trim());
    return out === null ? value : cap(out);
  };
  return {
    school: row.school === null ? null : (c.schools[row.school] ?? row.school),
    castingTime: pick(row.castingTime, localizeTime),
    range: pick(row.range, localizeRange),
    duration: pick(row.duration, localizeDuration),
  };
}
