import type { Lang } from "../copy";

/** A per-language cache of lazily fetched details: it holds the entries of ONE language, and reading it for another
 *  language yields an empty map (the other language's entries are never shown). */
export interface LangCache<T> {
  lang: Lang;
  map: Record<string, T>;
}

export function emptyCache<T>(lang: Lang): LangCache<T> {
  return { lang, map: {} };
}

export function cacheFor<T>(cache: LangCache<T>, lang: Lang): Record<string, T> {
  return cache.lang === lang ? cache.map : {};
}

/** `cache` with `id` set for `lang`. A write for the current language that the cache does not hold yet starts a new
 *  cache; a write for a language that is no longer current (a response that arrived after a switch) is dropped. */
export function cachePut<T>(cache: LangCache<T>, lang: Lang, id: string, value: T, current: Lang): LangCache<T> {
  if (lang !== current) return cache;
  const base = cache.lang === lang ? cache.map : {};
  return { lang, map: { ...base, [id]: value } };
}
