/** Where the old /export goes: the sheet page, with the query string kept (`?tab=`, ...). */
export function exportRedirectTarget(search: string): { pathname: string; search: string } {
  return { pathname: "/sheet", search };
}
