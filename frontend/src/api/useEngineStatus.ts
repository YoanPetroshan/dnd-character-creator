import { useSyncExternalStore } from "react";
import type { EngineSnapshot } from "./engineProtocol";
import { engineSnapshot, subscribeEngine } from "./transport";

/** What the in-browser engine is doing (see api/transport.ts): `engine` off | starting | ready | fallback, `pdf` idle | loading | ready. */
export function useEngineStatus(): EngineSnapshot {
  return useSyncExternalStore(subscribeEngine, engineSnapshot, engineSnapshot);
}
