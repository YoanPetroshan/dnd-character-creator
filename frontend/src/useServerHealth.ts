import { useEffect, useState } from "react";
import { apiFetch } from "./api/transport";
import { parseHealth, type ServerHealth } from "./logic/serverHealth";

/** Reads /api/health once when the app starts. A failure is silent: the resolve call already
 *  reports an unreachable server, so this only adds the version information. */
export function useServerHealth(): ServerHealth | null {
  const [health, setHealth] = useState<ServerHealth | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    apiFetch("/api/health", { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((body: unknown) => setHealth(parseHealth(body)))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  return health;
}
