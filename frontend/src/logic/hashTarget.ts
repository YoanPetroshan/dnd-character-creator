/** The choice id a URL hash points at ("#class:warlock:1:x" -> "class:warlock:1:x"),
 *  or null for no/empty hash. cids contain colons, so the value is only ever
 *  used with document.getElementById / string compare, never a CSS selector. */
export function cidFromHash(hash: string): string | null {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!raw) return null;
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}
