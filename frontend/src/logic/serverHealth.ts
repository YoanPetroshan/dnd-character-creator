// /api/health as the client uses it (SK9). Read once per page load; see docs/API.md.
export interface ServerHealth {
  ok: boolean;
  apiVersion?: number;
  draftVersion?: number;
  dataSource?: string;
  bundleSha256?: string | null;
}

/** Parses a /api/health body; null when it is not an object with `ok: true`. The old server
 *  answered `{ok:true}` alone: every other field is optional. */
export function parseHealth(body: unknown): ServerHealth | null {
  if (typeof body !== "object" || body === null || Array.isArray(body)) return null;
  const b = body as Record<string, unknown>;
  if (b.ok !== true) return null;
  return {
    ok: true,
    apiVersion: typeof b.apiVersion === "number" ? b.apiVersion : undefined,
    draftVersion: typeof b.draftVersion === "number" ? b.draftVersion : undefined,
    dataSource: typeof b.dataSource === "string" ? b.dataSource : undefined,
    bundleSha256: typeof b.bundleSha256 === "string" ? b.bundleSha256 : null,
  };
}

/** True when the server understands an OLDER draft version than this build writes: it may
 *  mishandle new draft fields. A server that does not report a version (the old health body) is
 *  treated as older as well, since it predates the contract. */
export function serverIsOlder(health: ServerHealth | null, clientDraftVersion: number): boolean {
  if (!health) return false;
  return health.draftVersion === undefined || health.draftVersion < clientDraftVersion;
}
