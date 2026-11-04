import type { Copy } from "../copy";

/** document.title for a path: "<page> — <app name>"; an unknown path gets the fallback page name. */
export function routeTitle(t: Copy, pathname: string): string {
  const page = t.titles.pages[pathname] ?? t.titles.fallback;
  return `${page}${t.titles.separator}${t.appName}`;
}
