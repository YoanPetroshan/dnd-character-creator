import type { EngineSnapshot } from "./engineProtocol";

/** Resolves once the in-browser engine has stopped booting (ready, fallen back or unavailable), or after `timeoutMs`.
 *  The service worker starts its precache of the whole app (~20 MB) only then: while the engine is still booting, the
 *  page's own downloads (the Pyodide runtime, the Python files) have the bandwidth to themselves, and the worker's
 *  `no-cache` fetches later find those files already downloaded (a 304, no second copy). */
export function whenEngineSettled(
  snapshot: () => EngineSnapshot,
  subscribe: (listener: () => void) => () => void,
  timeoutMs: number,
): Promise<void> {
  const settled = () => snapshot().engine !== "starting";
  return new Promise((resolve) => {
    if (settled()) return resolve();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = subscribe(() => {
      if (settled()) done();
    });
    function done() {
      unsubscribe();
      if (timer) clearTimeout(timer);
      resolve();
    }
    timer = setTimeout(done, timeoutMs);
  });
}
