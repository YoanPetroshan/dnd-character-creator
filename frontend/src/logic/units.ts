// Weights for display (owner decision 2026-11-10): English shows pounds only ("96 lb"); Bulgarian adds the
// kilograms in brackets ("96 lb (43,5 kg)"). Display only: the sheet fields stay numeric pounds.
// Mirrors server/export_labels.py (`kilograms`, `weight`, `weight_pair`); a test pins the two to each other.
import type { Lang } from "../copy";

const KG_PER_LB = 0.45359237;

/** Kilograms of `lb` pounds: ONE decimal (half up), decimal comma, a trailing ",0" dropped. No unit. */
export function kilograms(lb: number): string {
  // The product is shifted by 1e-9 so a value that is a hair under a half only through float error rounds up.
  const tenths = Math.floor(Math.abs(lb) * KG_PER_LB * 10 + 0.5 + 1e-9);
  const whole = Math.floor(tenths / 10);
  const frac = tenths % 10;
  const sign = lb < 0 && tenths > 0 ? "-" : "";
  return `${sign}${whole}${frac ? `,${frac}` : ""}`;
}

/** "96 lb" in English, "96 lb (43,5 kg)" in Bulgarian. */
export function formatWeight(lb: number, lang: Lang): string {
  if (lang !== "bg" || !Number.isFinite(lb)) return `${lb} lb`;
  return `${lb} lb (${kilograms(lb)} kg)`;
}

/** "96/225 lb" in English, "96/225 lb (43,5/102,1 kg)" in Bulgarian. */
export function formatWeightPair(a: number, b: number, lang: Lang): string {
  if (lang !== "bg" || !Number.isFinite(a) || !Number.isFinite(b)) return `${a}/${b} lb`;
  return `${a}/${b} lb (${kilograms(a)}/${kilograms(b)} kg)`;
}
