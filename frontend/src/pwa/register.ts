// Service worker registration and what the UI shows about it. Pure logic over injected browser objects, so the tests
// drive it with fakes. The worker itself is frontend/pwa/sw.template.js (rendered into dist/sw.js by the build).
//
// phase:  unsupported       no service worker support here (or an insecure page): the app still works online
//         idle              not started (dev server, or the engine is not in use)
//         installing        the first visit is downloading the app and the offline pack (about 20 MB) into the cache
//         offline-ready     everything is cached: the app starts without a network
//         update-available  a new version is downloaded and waiting; it takes over when the user asks (applyUpdate)
//         error             registration failed
// persisted: the answer of navigator.storage.persist() ("granted" keeps the browser from evicting the cache and the drafts).

export type PwaPhase = "unsupported" | "idle" | "installing" | "offline-ready" | "update-available" | "error";
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

  const watched = new WeakSet<object>();
  function watch(worker: WorkerLike | null) {
    if (!worker || watched.has(worker)) return;
    watched.add(worker);
    worker.addEventListener("statechange", evaluate);
  }

  function evaluate() {
    const reg = registration;
    if (!reg || !deps.container) return;
    watch(reg.installing);
    watch(reg.waiting);
    if (reg.waiting && deps.container.controller) {
      set({ phase: "update-available" });
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

  return {
    get: () => snapshot,
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    start() {
      const container = deps.container;
      if (!container) return Promise.resolve();
      started ??= (async () => {
        container.addEventListener("controllerchange", () => {
          if (applying) deps.reload(); // the new version took over: load its files; not on the very first claim
        });
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
    },
    async checkForUpdate() {
      try {
        await registration?.update();
      } catch {
        // offline or the host is unreachable: try again at the next visit
      }
    },
    applyUpdate() {
      const waiting = registration?.waiting;
      if (!waiting) return;
      applying = true;
      waiting.postMessage({ type: "SKIP_WAITING" });
    },
  };
}
