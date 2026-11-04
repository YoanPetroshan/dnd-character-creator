import type { Lang } from "../copy";

/** Appends `?lang=<lang>` to an API path (the server ignores it until the i18n slices). */
export function withLang(path: string, lang: Lang): string {
  return `${path}${path.includes("?") ? "&" : "?"}lang=${encodeURIComponent(lang)}`;
}
