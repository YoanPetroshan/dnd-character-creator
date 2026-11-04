import { bg } from "./bg";

/** The shape every locale file must have (a future copy/en.ts is `const en: Copy = {...}`). */
export type Copy = typeof bg;

/** The active copy. One locale today; the BG/EN switch will pick the object here. */
export const t: Copy = bg;
