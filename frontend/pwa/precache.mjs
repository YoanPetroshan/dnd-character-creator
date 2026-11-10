// Build side of the PWA: the precache manifest (every file of dist, with a content hash), the service worker rendered
// from sw.template.js, and the vite plugin that writes both after the build. Pure functions are exported for the tests.
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, posix, relative, sep } from "node:path";

/** Files of dist that are NOT precached: the worker itself, the GitHub Pages 404 copy of index.html, source maps, OS litter. */
export const DEFAULT_EXCLUDE = (path) => path === "sw.js" || path === "404.html" || path.endsWith(".map") || posix.basename(path) === ".DS_Store";

export const sha256Hex = (bytes) => createHash("sha256").update(bytes).digest("hex");

/** Every file under `dir` as { path (posix, relative), size, sha256 }, sorted by path. */
export function collectFiles(dir) {
  const out = [];
  const walk = (d) => {
    for (const name of readdirSync(d).sort()) {
      const full = join(d, name);
      if (statSync(full).isDirectory()) walk(full);
      else {
        const bytes = readFileSync(full);
        out.push({ path: relative(dir, full).split(sep).join("/"), size: bytes.length, sha256: sha256Hex(bytes) });
      }
    }
  };
  walk(dir);
  return out.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
}

/**
 * The precache manifest of a file list: { version, totalBytes, entries: [{ url, revision, size }] }.
 * `url` is relative to the service worker scope; `revision` is the first 16 hex digits of the file's sha256; `version`
 * names the cache and changes whenever any precached file (path or content) changes.
 */
export function buildPrecacheManifest(files, exclude = DEFAULT_EXCLUDE) {
  const entries = files
    .filter((f) => !exclude(f.path))
    .map((f) => ({ url: f.path, revision: f.sha256.slice(0, 16), size: f.size }))
    .sort((a, b) => (a.url < b.url ? -1 : a.url > b.url ? 1 : 0));
  const version = sha256Hex(entries.map((e) => `${e.url}:${e.revision}`).join("\n")).slice(0, 12);
  return { version, totalBytes: entries.reduce((n, e) => n + e.size, 0), entries };
}

/** Paths of `files` (minus the excluded ones) that the manifest does not list, and entries whose file is gone or changed. */
export function manifestProblems(manifest, files, exclude = DEFAULT_EXCLUDE) {
  const byPath = new Map(files.map((f) => [f.path, f]));
  const listed = new Map(manifest.entries.map((e) => [e.url, e]));
  const missing = files.filter((f) => !exclude(f.path) && !listed.has(f.path)).map((f) => f.path);
  const stale = manifest.entries.filter((e) => !byPath.has(e.url) || byPath.get(e.url).sha256.slice(0, 16) !== e.revision).map((e) => e.url);
  return { missing, stale };
}

const TOKEN = "__PRECACHE_MANIFEST__";

/** sw.template.js with the manifest filled in (the token appears exactly once). */
export function renderServiceWorker(template, manifest) {
  if (template.split(TOKEN).length !== 2) throw new Error(`sw.template.js must contain ${TOKEN} exactly once`);
  const { version, entries } = manifest;
  return template.replace(TOKEN, () => JSON.stringify({ version, entries: entries.map(({ url, revision }) => ({ url, revision })) }));
}

/** Parse the manifest back out of a rendered service worker (used by the dist check). */
export function readManifestFromServiceWorker(source) {
  const m = /const MANIFEST = (\{.*\});/.exec(source);
  if (!m) throw new Error("no MANIFEST in the service worker");
  return JSON.parse(m[1]);
}

/**
 * Vite plugin: after the build writes dist/sw.js (the precache manifest of everything in dist) and dist/404.html (a
 * copy of index.html: GitHub Pages answers an unknown path with it, so a deep link still loads the single-page app).
 * Active only for builds that use the in-browser engine (`enabled()`), and only when the offline pack was built.
 */
export function pwaPlugin({ enabled, templatePath, log = console.log }) {
  let outDir = "dist";
  let root = process.cwd();
  return {
    name: "dnd-builder-pwa",
    apply: "build",
    configResolved(config) {
      outDir = config.build.outDir;
      root = config.root;
    },
    closeBundle: {
      order: "post",
      handler() {
        if (!enabled()) return;
        const dist = join(root, outDir);
        if (!existsSync(join(dist, "pyodide", "pack.json"))) {
          log("[pwa] frontend/public/pyodide/pack.json is missing (run scripts/build_offline.py): no service worker written");
          return;
        }
        copyFileSync(join(dist, "index.html"), join(dist, "404.html"));
        const manifest = buildPrecacheManifest(collectFiles(dist));
        writeFileSync(join(dist, "sw.js"), renderServiceWorker(readFileSync(templatePath, "utf8"), manifest));
        log(`[pwa] sw.js: ${manifest.entries.length} files, ${(manifest.totalBytes / (1 << 20)).toFixed(2)} MB precached, version ${manifest.version}`);
      },
    },
  };
}
