// The precache manifest builder and the service worker renderer (frontend/pwa/precache.mjs): pure functions plus a
// temporary directory standing in for dist.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { buildPrecacheManifest, collectFiles, manifestProblems, readManifestFromServiceWorker, renderServiceWorker } from "../../pwa/precache.mjs";

const dir = mkdtempSync(join(tmpdir(), "dnd-precache-"));
afterAll(() => rmSync(dir, { recursive: true, force: true }));
const put = (rel, text) => {
  const full = join(dir, rel);
  mkdirSync(join(full, ".."), { recursive: true });
  writeFileSync(full, text);
};
put("index.html", "<html>");
put("404.html", "<html>");
put("sw.js", "old worker");
put("assets/index-abc.js", "console.log(1)");
put("assets/index-abc.js.map", "{}");
put("pyodide/pyodide.asm.wasm", "wasm bytes");
put("pyodide/pack.json", "{}");
put("icons/icon-192.png", "png");
put(".DS_Store", "x");

describe("collectFiles", () => {
  it("lists every file with posix relative paths, sizes and sha256, sorted", () => {
    const files = collectFiles(dir);
    expect(files.map((f) => f.path)).toEqual([".DS_Store", "404.html", "assets/index-abc.js", "assets/index-abc.js.map", "icons/icon-192.png", "index.html", "pyodide/pack.json", "pyodide/pyodide.asm.wasm", "sw.js"]);
    const js = files.find((f) => f.path === "assets/index-abc.js");
    expect(js.size).toBe(14);
    expect(js.sha256).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe("buildPrecacheManifest", () => {
  const files = collectFiles(dir);
  const manifest = buildPrecacheManifest(files);

  it("lists every file of dist except the worker, the 404 copy, source maps and OS litter", () => {
    expect(manifest.entries.map((e) => e.url)).toEqual(["assets/index-abc.js", "icons/icon-192.png", "index.html", "pyodide/pack.json", "pyodide/pyodide.asm.wasm"]);
    expect(manifest.totalBytes).toBe(manifest.entries.reduce((n, e) => n + e.size, 0));
  });

  it("uses scope-relative urls (no leading slash, no origin): the app works under any sub-path", () => {
    for (const e of manifest.entries) expect(e.url).not.toMatch(/^(\/|[a-z]+:)/i);
  });

  it("revisions are 16 hex digits of the content hash", () => {
    for (const e of manifest.entries) {
      expect(e.revision).toMatch(/^[0-9a-f]{16}$/);
      expect(files.find((f) => f.path === e.url).sha256.startsWith(e.revision)).toBe(true);
    }
  });

  it("the version is stable for the same files and changes when any file's content or name changes", () => {
    expect(buildPrecacheManifest(collectFiles(dir)).version).toBe(manifest.version);
    expect(manifest.version).toMatch(/^[0-9a-f]{12}$/);
    const changed = files.map((f) => (f.path === "pyodide/pyodide.asm.wasm" ? { ...f, sha256: "0".repeat(64) } : f));
    expect(buildPrecacheManifest(changed).version).not.toBe(manifest.version);
    const renamed = files.map((f) => (f.path === "index.html" ? { ...f, path: "index2.html" } : f));
    expect(buildPrecacheManifest(renamed).version).not.toBe(manifest.version);
    // an excluded file changing does not
    const sw = files.map((f) => (f.path === "sw.js" ? { ...f, sha256: "1".repeat(64) } : f));
    expect(buildPrecacheManifest(sw).version).toBe(manifest.version);
  });
});

describe("manifestProblems", () => {
  const files = collectFiles(dir);
  const manifest = buildPrecacheManifest(files);
  it("finds nothing for a manifest built from the same files", () => {
    expect(manifestProblems(manifest, files)).toEqual({ missing: [], stale: [] });
  });
  it("reports a file the manifest does not list, a listed file that is gone and one whose content changed", () => {
    const missing = { ...manifest, entries: manifest.entries.filter((e) => e.url !== "pyodide/pyodide.asm.wasm") };
    expect(manifestProblems(missing, files).missing).toEqual(["pyodide/pyodide.asm.wasm"]);
    const gone = manifestProblems(manifest, files.filter((f) => f.path !== "icons/icon-192.png"));
    expect(gone.stale).toEqual(["icons/icon-192.png"]);
    const changed = manifestProblems(manifest, files.map((f) => (f.path === "index.html" ? { ...f, sha256: "2".repeat(64) } : f)));
    expect(changed.stale).toEqual(["index.html"]);
  });
});

describe("renderServiceWorker", () => {
  const manifest = buildPrecacheManifest(collectFiles(dir));
  const template = "const MANIFEST = __PRECACHE_MANIFEST__;\nself.x = 1;\n";
  it("fills the token and the manifest can be read back", () => {
    const out = renderServiceWorker(template, manifest);
    expect(out).not.toContain("__PRECACHE_MANIFEST__");
    const back = readManifestFromServiceWorker(out);
    expect(back.version).toBe(manifest.version);
    expect(back.entries).toEqual(manifest.entries.map(({ url, revision }) => ({ url, revision })));
  });
  it("refuses a template with no token or with two", () => {
    expect(() => renderServiceWorker("nothing", manifest)).toThrow();
    expect(() => renderServiceWorker("__PRECACHE_MANIFEST__ __PRECACHE_MANIFEST__", manifest)).toThrow();
  });
  it("does not interpret $ patterns in file names", () => {
    const m = { version: "v", entries: [{ url: "a$&b.js", revision: "r" }] };
    expect(readManifestFromServiceWorker(renderServiceWorker(template, m)).entries[0].url).toBe("a$&b.js");
  });
});
