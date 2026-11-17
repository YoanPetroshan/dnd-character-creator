/** Where the error page's reset sends the browser: Home under the build's public base path (`import.meta.env.BASE_URL`,
 *  "/" in the default build, "/dnd-character-creator/" on GitHub Pages). A bare "/home" would leave the app there. */
export function resetTarget(base: string | undefined): string {
  const root = (base ?? "/").replace(/\/+$/, "");
  return `${root}/home`;
}
