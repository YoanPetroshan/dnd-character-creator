/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" in the offline build (`npm run build:offline`, `dev:offline`): use the in-browser engine when the pack is there. */
  readonly VITE_OFFLINE_ENGINE?: string;
  /** "eager": the worker loads the PDF stack right after boot instead of on the first PDF export (O4 precaches it). */
  readonly VITE_OFFLINE_PDF?: string;
  /** "1" for a static-host build (GitHub Pages): no server to fall back to, so an engine that cannot run is reported as unavailable. */
  readonly VITE_SERVERLESS?: string;
  /** Public base path of the build (read by vite.config.ts; the app reads import.meta.env.BASE_URL). */
  readonly VITE_BASE?: string;
}
