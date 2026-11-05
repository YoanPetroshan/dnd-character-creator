import type { EngineSnapshot } from "./engineProtocol";

/** A tiny observable holding the engine's EngineSnapshot (an immutable object replaced on every change, so it works
 *  as a useSyncExternalStore snapshot). */
export interface StatusStore {
  get(): EngineSnapshot;
  set(patch: Partial<EngineSnapshot>): void;
  subscribe(listener: () => void): () => void;
}

export function createStatusStore(initial: EngineSnapshot): StatusStore {
  let snapshot = initial;
  const listeners = new Set<() => void>();
  return {
    get: () => snapshot,
    set(patch) {
      const next = { ...snapshot, ...patch };
      if (next.engine === snapshot.engine && next.pdf === snapshot.pdf) return;
      snapshot = next;
      for (const l of [...listeners]) l();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
  };
}
