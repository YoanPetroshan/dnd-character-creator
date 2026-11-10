// The app's PWA instance and its React hook (see register.ts). `startPwa()` is called from main.tsx once the in-browser
// engine is in use; the dev server and the Flask build never register a service worker.
import { useSyncExternalStore } from "react";
import { createPwa, type Pwa, type PwaSnapshot } from "./register";

let instance: Pwa | null = null;

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
