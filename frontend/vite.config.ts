import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { pwaPlugin } from "./pwa/precache.mjs";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", ["VITE_"]);
  // Public base path of the built app. "/" (default) is right for the Flask server and for a host at the domain root.
  // A static host under a sub-path (GitHub Pages: /dnd-character-creator/) builds with VITE_BASE=/dnd-character-creator/ :
  // every asset URL, the worker, /pyodide/*, the manifest, the service worker scope and the router basename follow it.
  const base = normaliseBase(env.VITE_BASE);
  return {
    base,
    plugins: [
      react(),
      // offline build only: dist/sw.js (precache manifest of everything in dist) and dist/404.html
      pwaPlugin({
        enabled: () => /^(1|true|on|worker)$/i.test((env.VITE_OFFLINE_ENGINE ?? "").trim()),
        templatePath: decodeURIComponent(new URL("./pwa/sw.template.js", import.meta.url).pathname),
      }),
    ],
    // Pure-logic tests (src/logic/*.test.ts) run in plain node: no DOM, no React.
    test: {
      environment: "node",
      include: ["src/**/*.test.ts", "src/offline/*.test.mjs", "src/pwa/*.test.mjs"],
      // The offline pack (Pyodide, built by scripts/build_offline.py) is imported by src/offline/equivalence.test.ts
      // as plain Node modules, not transformed by vite.
      server: { deps: { external: [/\/public\/pyodide\//] } },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});

/** "" / undefined -> "/"; otherwise a path that starts and ends with "/" ("/dnd-character-creator/"). */
function normaliseBase(raw: string | undefined): string {
  const v = (raw ?? "").trim();
  if (v === "" || v === "/") return "/";
  if (!/^\/?[\w.~-]+(\/[\w.~-]+)*\/?$/.test(v)) throw new Error(`VITE_BASE must be a path like /name/ , got ${JSON.stringify(v)}`);
  return `/${v.replace(/^\/+|\/+$/g, "")}/`;
}
