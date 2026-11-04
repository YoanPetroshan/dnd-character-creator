import { bg } from "./bg";
import { en } from "./en";

/** The shape every locale file must have: en.ts is `const en: Copy = {...}`, so a missing key is a tsc error. */
export type Copy = typeof bg;

export type Lang = "bg" | "en";
export const LANGS: readonly Lang[] = ["bg", "en"];
export const DEFAULT_LANG: Lang = "bg";

export const COPY: Record<Lang, Copy> = { bg, en };

/** The catalog of a language. Components get it from `useT()`; pure modules take it as a `t` argument. */
export const copyFor = (lang: Lang): Copy => COPY[lang];

export { bg, en };
