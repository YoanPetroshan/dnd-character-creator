/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" in the offline build (`npm run build:offline`, `dev:offline`): use the in-browser engine when the pack is there. */
  readonly VITE_OFFLINE_ENGINE?: string;
}
