// The built dist (npm run build:offline) against its own precache manifest: dist/sw.js must list EVERY file of dist (and so
// every file of the offline pack) with the right content hash, and the pack's own pack.json must be covered too.
// Skipped when dist was not built with the pack (a plain `npm run build` has no sw.js); the CI job sets
// REQUIRE_PRECACHE=1, which turns the skip into a failure.
import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { DEFAULT_EXCLUDE, collectFiles, manifestProblems, readManifestFromServiceWorker } from "../../pwa/precache.mjs";

const dist = new URL("../../dist/", import.meta.url).pathname;
const have = existsSync(dist + "sw.js");
const required = process.env.REQUIRE_PRECACHE === "1";

describe.skipIf(!have && !required)("dist precache manifest", () => {
  it("dist/sw.js exists (build with `npm run build:offline` after scripts/build_offline.py)", () => {
    expect(have).toBe(true);
  });
  if (!have) return;

  const files = collectFiles(dist);
  const manifest = readManifestFromServiceWorker(readFileSync(dist + "sw.js", "utf8"));

  it("lists every file of dist (nothing missing, nothing stale)", () => {
    expect(manifestProblems(manifest, files)).toEqual({ missing: [], stale: [] });
  });

  it("lists every file of the offline pack named in pack.json, plus pack.json", () => {
    const pack = JSON.parse(readFileSync(dist + "pyodide/pack.json", "utf8"));
    const listed = new Set(manifest.entries.map((e) => e.url));
    const names = Object.keys(pack);
    expect(names.length).toBeGreaterThan(10);
    for (const name of names) {
      expect(listed.has(`pyodide/${name}`), name).toBe(true);
      const entry = manifest.entries.find((e) => e.url === `pyodide/${name}`);
      expect(pack[name].sha256.startsWith(entry.revision), `${name}: revision is the pack's sha256`).toBe(true);
    }
    expect(listed.has("pyodide/pack.json")).toBe(true);
  });

  it("includes the app shell, the manifest, the icons and the engine worker, and not the worker itself", () => {
    const urls = manifest.entries.map((e) => e.url);
    for (const must of ["index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"]) expect(urls, must).toContain(must);
    expect(urls.some((u) => /^assets\/engine\.worker-.*\.js$/.test(u))).toBe(true);
    expect(urls.some((u) => /^assets\/index-.*\.js$/.test(u))).toBe(true);
    expect(urls).not.toContain("sw.js");
    expect(DEFAULT_EXCLUDE("sw.js")).toBe(true);
  });

  it("index.html and 404.html are identical (GitHub Pages answers a deep link with the 404 page)", () => {
    expect(existsSync(dist + "404.html")).toBe(true);
    expect(readFileSync(dist + "404.html", "utf8")).toBe(readFileSync(dist + "index.html", "utf8"));
  });
});
