// Service worker registration and what the UI shows about it. Pure logic over injected browser objects, so the tests
// drive it with fakes. The worker itself is frontend/pwa/sw.template.js (rendered into dist/sw.js by the build).
//
// phase:  unsupported       no service worker support here (or an insecure page): the app still works online
//         idle              not started (dev server, or the engine is not in use)
//         installing        the first visit is downloading the app and the offline pack (about 20 MB) into the cache
//         offline-ready     everything is cached: the app starts without a network
//         update-available  a new version is downloaded and waiting. When its storage schema equals this page's, nothing is
//                           at risk and the app was just opened (or shown again), it is applied by itself (autoApply);
//                           otherwise it takes over when the user asks (applyUpdate)
//         update-needs-backup  the waiting version cannot be applied silently (its storage schema differs, or the last save
//                           failed so a draft lives only in memory): the UI asks for a download of all characters first
//         error             registration failed
// persisted: the answer of navigator.storage.persist() ("granted" keeps the browser from evicting the cache and the drafts).

export type PwaPhase = "unsupported" | "idle" | "installing" | "offline-ready" | "update-available" | "update-needs-backup" | "error";
export type PersistState = "unknown" | "granted" | "denied" | "unsupported";

export interface PwaSnapshot {
  readonly phase: PwaPhase;
  readonly persisted: PersistState;
  /** The phase became `offline-ready` during this visit (the first install finished), not at page load. */
  readonly justReady: boolean;
}

export interface WorkerLike {
  readonly state: string;
  addEventListener(type: "statechange", listener: () => void): void;
  postMessage(message: unknown): void;
}
export interface RegistrationLike {
  readonly installing: WorkerLike | null;
  readonly waiting: WorkerLike | null;
  readonly active: WorkerLike | null;
  addEventListener(type: "updatefound", listener: () => void): void;
  update(): Promise<unknown>;
}
export interface ContainerLike {
  readonly controller: unknown;
  register(url: string, options: { scope: string; updateViaCache?: "none" | "imports" | "all" }): Promise<RegistrationLike>;
  addEventListener(type: "controllerchange", listener: () => void): void;
  addEventListener(type: "message", listener: (event: { data?: unknown; source?: unknown }) => void): void;
}
export interface StorageManagerLike {
  persist?(): Promise<boolean>;
  persisted?(): Promise<boolean>;
}

export interface PwaDeps {
  container: ContainerLike | undefined;
  /** URL of the service worker and its scope, both under the app's base path. */
  swUrl: string;
  scope: string;
  storage?: StorageManagerLike;
  reload(): void;
  /** Storage schema of this page (src/storageSchema.json). Without it nothing is ever applied automatically. */
  schema?: number;
  /** True while a draft is not safely stored (the last write failed): an update then asks for a backup. */
  dataAtRisk?(): boolean;
  /** Apply a compatible update by itself, but only in the first `windowMs` after the app was opened / shown again. */
  autoApply?: { windowMs: number; now(): number; allowed(): boolean; mark(): void };
}

export interface Pwa {
  get(): PwaSnapshot;
  subscribe(listener: () => void): () => void;
  /** Register the worker (once). Resolves when the registration is tracked. */
  start(): Promise<void>;
  /** Ask the browser whether the worker file changed. */
  checkForUpdate(): Promise<void>;
  /** Let the waiting version take over; the page reloads when it has. */
  applyUpdate(): void;
}

/** Ask for persistent storage. Never throws. */
export async function requestPersistence(storage: StorageManagerLike | undefined): Promise<PersistState> {
  try {
    if (!storage || typeof storage.persist !== "function") return "unsupported";
    if (typeof storage.persisted === "function" && (await storage.persisted())) return "granted";
    return (await storage.persist()) ? "granted" : "denied";
  } catch {
    return "unknown";
  }
}

export function createPwa(deps: PwaDeps): Pwa {
  let snapshot: PwaSnapshot = { phase: deps.container ? "idle" : "unsupported", persisted: "unknown", justReady: false };
  const listeners = new Set<() => void>();
  const set = (patch: Partial<PwaSnapshot>) => {
    const next = { ...snapshot, ...patch };
    if (next.phase === snapshot.phase && next.persisted === snapshot.persisted && next.justReady === snapshot.justReady) return;
    snapshot = next;
    for (const l of [...listeners]) l();
  };

  let registration: RegistrationLike | null = null;
  let started: Promise<void> | null = null;
  let applying = false;
  let persistAsked = false;
  const auto = deps.autoApply;
  let armedUntil = auto ? auto.now() + auto.windowMs : 0;
  const arm = () => {
    if (auto) armedUntil = auto.now() + auto.windowMs;
  };
  // a download that BEGAN inside the window keeps the right to apply itself when it ends (the 20 MB pack can take longer than
  // the window on a slow network); one that began later is the person already working: it waits for the next open
  let downloadStartedArmed = false;
  // what the waiting worker said about its storage schema: "ok" (same as this page) or "backup"
  const verdicts = new WeakMap<object, "ok" | "backup">();
  const asked = new WeakSet<object>();

  const watched = new WeakSet<object>();
  function watch(worker: WorkerLike | null) {
    if (!worker || watched.has(worker)) return;
    watched.add(worker);
    worker.addEventListener("statechange", () => {
      // FE-03: a first install that is thrown away (nothing active or waiting to fall back on) is a failure, not a wait
      if (worker.state === "redundant" && registration && !registration.active && !registration.waiting) set({ phase: "error" });
      else evaluate();
    });
  }

  function evaluate() {
    const reg = registration;
    if (!reg || !deps.container) return;
    watch(reg.installing);
    watch(reg.waiting);
    if (auto && reg.installing && deps.container.controller && auto.now() <= armedUntil) downloadStartedArmed = true;
    if (reg.waiting && deps.container.controller) {
      const v = verdicts.get(reg.waiting);
      set({ phase: v === "backup" || (v === "ok" && deps.dataAtRisk?.()) ? "update-needs-backup" : "update-available" });
      if (deps.schema !== undefined && !asked.has(reg.waiting)) {
        asked.add(reg.waiting);
        reg.waiting.postMessage({ type: "GET_VERSION" });
      }
      if (auto && downloadStartedArmed) {
        downloadStartedArmed = false;
        armedUntil = Math.max(armedUntil, auto.now() + auto.windowMs); // the clock starts when the version is ready
      }
      tryAutoApply();
    } else if (reg.active && reg.active.state === "activated") {
      const wasInstalling = snapshot.phase === "installing";
      set({ phase: "offline-ready", justReady: snapshot.justReady || wasInstalling });
      if (!persistAsked) {
        persistAsked = true;
        void requestPersistence(deps.storage).then((persisted) => set({ persisted }));
      }
    } else if (reg.installing || reg.waiting) {
      // a first install; an update installing behind an active worker keeps the current phase
      if (snapshot.phase !== "offline-ready" && snapshot.phase !== "update-available") set({ phase: "installing" });
    }
  }

  let hadController = false;
  let listening = false;
  let reloaded = false;
  function start(): Promise<void> {
    const container = deps.container;
    if (!container) return Promise.resolve();
    started ??= (async () => {
      if (!listening) {
        listening = true;
        hadController = !!container.controller;
        container.addEventListener("message", (event) => onVersion(event?.data, event?.source));
        container.addEventListener("controllerchange", () => {
          // the new version took over: load its files. Our own applyUpdate, or (FE-09) another tab's, when this tab was
          // already controlled; not on the very first claim of a tab that started without a controller
          if ((applying || hadController) && !reloaded) {
            reloaded = true;
            deps.reload();
          }
        });
      }
      try {
        registration = await container.register(deps.swUrl, { scope: deps.scope, updateViaCache: "none" });
      } catch {
        set({ phase: "error" });
        return;
      }
      registration.addEventListener("updatefound", evaluate);
      evaluate();
    })();
    return started;
  }

  function onVersion(data: unknown, source: unknown) {
    const waiting = registration?.waiting;
    if (!waiting || deps.schema === undefined || !data || typeof data !== "object") return;
    if ((data as { type?: unknown }).type !== "VERSION") return;
    if (source !== undefined && source !== waiting) return; // the active worker answering for itself
    const schema = (data as { schema?: unknown }).schema;
    // a version that does not say its schema is treated as incompatible
    verdicts.set(waiting, schema === deps.schema ? "ok" : "backup");
    evaluate();
  }

  /** Apply the waiting version now when it is safe: same schema, nothing unsaved, inside the arming window. */
  function tryAutoApply() {
    const waiting = registration?.waiting;
    if (!auto || !waiting || verdicts.get(waiting) !== "ok") return;
    if (deps.dataAtRisk?.()) return; // evaluate() has put the phase on "update-needs-backup"
    if (auto.now() > armedUntil || !auto.allowed() || applying) return;
    auto.mark();
    api.applyUpdate();
  }

  const api: Pwa = {
    get: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    start,
    async checkForUpdate() {
      arm(); // the app is shown again: a compatible update found now may be applied by itself
      if (snapshot.phase === "error") {
        // FE-03: a failed registration or install is tried again when the app is shown again
        started = null;
        registration = null;
        await start();
        return;
      }
      try {
        await registration?.update();
      } catch {
        // offline or the host is unreachable: try again at the next visit
      }
      evaluate(); // an update already waiting from an earlier visit
    },
    applyUpdate() {
      const waiting = registration?.waiting;
      if (!waiting) return;
      applying = true;
      waiting.postMessage({ type: "SKIP_WAITING" });
    },
  };
  return api;
}
