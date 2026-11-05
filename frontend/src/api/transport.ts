// apiFetch: the one function every API call of the app goes through. Same signature as fetch.
//
// Two implementations, chosen once at startup:
//   - plain fetch (the default): the Flask server of `npm run dev` / the LAN server answers.
//   - the worker transport: the engine runs in this browser (Pyodide in a Web Worker, workerTransport.ts), no server.
// The worker transport is used only when ALL hold: the build asked for it (VITE_OFFLINE_ENGINE=1, `npm run
// build:offline` / `dev:offline`), the browser has WebAssembly and module-capable Workers, and the offline pack is
// really served (`/pyodide/pack.json`, written by scripts/build_offline.py). Otherwise, and whenever the worker cannot
// boot, calls go to plain fetch. `engineSnapshot` / `subscribeEngine` tell the UI what is going on (useEngineStatus).
import type { EngineSnapshot } from "./engineProtocol";
import { createStatusStore } from "./engineStatus";
import { createWorkerTransport, fetchWithTimeout, type ApiInit, type Transport, type WorkerLike } from "./workerTransport";

export type { ApiInit } from "./workerTransport";
export { isTimeoutError } from "./workerTransport";

export type EngineChoice = "worker" | "fetch";

export interface EngineEnvironment {
  /** The build flag, as written (`VITE_OFFLINE_ENGINE`). */
  flag: string | undefined;
  hasWebAssembly: boolean;
  hasWorker: boolean;
  /** `/pyodide/pack.json` is served (not the SPA's index.html). */
  packPresent: boolean;
}

export const flagOn = (flag: string | undefined): boolean => /^(1|true|on|worker)$/i.test((flag ?? "").trim());

/** The selection rule. Plain fetch unless the build asked for the engine AND this browser can run it AND the pack is there. */
export function chooseEngine(env: EngineEnvironment): EngineChoice {
  return flagOn(env.flag) && env.hasWebAssembly && env.hasWorker && env.packPresent ? "worker" : "fetch";
}

/** Does the server answer `<base>pyodide/pack.json` with the pack's JSON? (A dev server or the SPA catch-all answers a
 *  missing file with index.html and status 200, so the body is checked.) */
export async function detectPack(fetchImpl: typeof fetch, baseUrl: string): Promise<boolean> {
  try {
    const resp = await fetchImpl(`${baseUrl}pyodide/pack.json`, { cache: "no-cache" });
    if (!resp.ok) return false;
    const pack = (await resp.json()) as Record<string, unknown>;
    return typeof pack === "object" && pack !== null && "app.zip" in pack && "pyodide.asm.wasm" in pack;
  } catch {
    return false;
  }
}

export interface ApiTransport {
  apiFetch(input: RequestInfo | URL, init?: ApiInit): Promise<Response>;
  snapshot(): EngineSnapshot;
  subscribe(listener: () => void): () => void;
  /** Resolves when the choice is made (and, for the worker, when it is spawned). */
  readonly chosen: Promise<EngineChoice>;
}

export interface ApiTransportOptions {
  flag: string | undefined;
  baseUrl: string;
  plainFetch: typeof fetch;
  environment?: { hasWebAssembly: boolean; hasWorker: boolean };
  /** Detect the pack (default: detectPack over plainFetch). */
  detect?: () => Promise<boolean>;
  /** Build the worker transport (default: the real worker, see spawnEngineWorker). */
  makeWorkerTransport?: () => Transport;
}

export function createApiTransport(opts: ApiTransportOptions): ApiTransport {
  const env = opts.environment ?? {
    hasWebAssembly: typeof WebAssembly === "object",
    hasWorker: typeof Worker === "function",
  };
  const store = createStatusStore({ engine: "off", pdf: "idle" });
  let worker: Transport | null = null;

  const chosen: Promise<EngineChoice> = (async () => {
    // The cheap checks first: with the flag off (dev) or no WebAssembly nothing is fetched or started.
    if (!flagOn(opts.flag) || !env.hasWebAssembly || !env.hasWorker) return "fetch";
    store.set({ engine: "starting" }); // pack probe + boot: the UI shows "engine starting"
    const packPresent = await (opts.detect ?? (() => detectPack(opts.plainFetch, opts.baseUrl)))();
    const choice = chooseEngine({ flag: opts.flag, ...env, packPresent });
    if (choice === "fetch") {
      store.set({ engine: "off" });
      return "fetch";
    }
    const t = opts.makeWorkerTransport!();
    worker = t;
    store.set(t.store.get());
    t.store.subscribe(() => store.set(t.store.get()));
    return "worker";
  })();

  return {
    chosen,
    snapshot: store.get,
    subscribe: store.subscribe,
    async apiFetch(input, init) {
      const choice = await chosen;
      if (choice === "worker" && worker) return worker.fetch(input, init);
      return fetchWithTimeout(opts.plainFetch, input, init);
    },
  };
}

// --- the app's instance ---------------------------------------------------------------------------------------------

let instance: ApiTransport | null = null;

/** The app's transport, created on first use. (`startEngine()` in main.tsx creates it at page load so the engine boots
 *  while the first screen is drawn.) */
export function transport(): ApiTransport {
  if (!instance) {
    const base = import.meta.env.BASE_URL;
    instance = createApiTransport({
      flag: import.meta.env.VITE_OFFLINE_ENGINE as string | undefined,
      baseUrl: base,
      plainFetch: (input, init) => fetch(input, init),
      makeWorkerTransport: () =>
        createWorkerTransport({
          spawn: () => new Worker(new URL("../engine.worker.ts", import.meta.url), { type: "module" }) as unknown as WorkerLike,
          fallback: (input, init) => fetch(input, init),
        }),
    });
  }
  return instance;
}

export const startEngine = (): void => void transport();

/** fetch, answered by the Flask server or by the in-browser engine (see the header). */
export function apiFetch(input: RequestInfo | URL, init?: ApiInit): Promise<Response> {
  return transport().apiFetch(input, init);
}

export const engineSnapshot = (): EngineSnapshot => transport().snapshot();
export const subscribeEngine = (listener: () => void): (() => void) => transport().subscribe(listener);
