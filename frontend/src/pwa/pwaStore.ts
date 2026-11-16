// The app's PWA instance and its React hook (see register.ts). `startPwa()` is called from main.tsx once the in-browser
// engine is in use; the dev server and the Flask build never register a service worker.
import { useSyncExternalStore } from "react";
import storageSchema from "../storageSchema.json";
import { createPwa, type Pwa, type PwaSnapshot } from "./register";

let instance: Pwa | null = null;
let storageFailed = false;
const GUARD_KEY = "dnd-builder-autoupdate-at";
const GUARD_MS = 30_000;
/** The draft context tells whether the last save failed (such a draft lives only in memory: no silent update). */
export function reportStorageFailed(failed: boolean): void {
  storageFailed = failed;
}

export function pwa(): Pwa {
  if (!instance) {
    const nav = typeof navigator === "undefined" ? undefined : navigator;
    const base = import.meta.env.BASE_URL;
    instance = createPwa({
      container: nav && "serviceWorker" in nav && typeof window !== "undefined" && window.isSecureContext ? nav.serviceWorker : undefined,
      swUrl: `${base}sw.js`,
      scope: base,
      storage: nav?.storage,
      reload: () => window.location.reload(),
      schema: storageSchema.schema,
      dataAtRisk: () => storageFailed,
      autoApply: {
        windowMs: 60_000,
        now: () => Date.now(),
        // never twice within 30 s: a reload loop cannot form even if the new worker does not take over cleanly
        allowed: () => {
          try {
            const at = Number(window.sessionStorage.getItem(GUARD_KEY));
            return !at || Date.now() - at > GUARD_MS;
          } catch {
            return true;
          }
        },
        mark: () => {
          try {
            window.sessionStorage.setItem(GUARD_KEY, String(Date.now()));
          } catch {
            // no sessionStorage: the 60 s window alone limits it
          }
        },
      },
    });
  }
  return instance;
}

/** Register the service worker (production builds only) and look for a new version whenever the app is shown again. */
export function startPwa(): void {
  if (!import.meta.env.PROD) return;
  const p = pwa();
  void p.start();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") void p.checkForUpdate();
  });
}

export function usePwa(): PwaSnapshot {
  const p = pwa();
  return useSyncExternalStore(p.subscribe, p.get, p.get);
}
