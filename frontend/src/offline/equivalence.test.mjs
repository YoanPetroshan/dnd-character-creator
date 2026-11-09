/**
 * O1: the browser engine (Pyodide, the same app.zip the PWA will ship) is proven equal to the native one.
 * Loads Pyodide from public/pyodide in Node, mounts app.zip and runs, against the stored baselines (O3: the PDF stack,
 * fonts.zip + the four wheels, is NOT part of the boot: `service` must import without it, and it is loaded on demand,
 * before the first part that renders a PDF, like the worker does on the first PDF export):
 *   - every golden case (STRIP applied, canonical JSON equal),
 *   - the 54 export baseline drafts (Markdown / YAML byte-equal by sha256, PDF after /CreationDate + /ID normalising),
 *   - the fixed request list of server/tests/service_requests.py through service.handle (status, content type,
 *     Content-Disposition, body sha256 + length equal to service_baseline.json).
 * Skipped when the pack is absent (build it: `.venv/bin/python scripts/build_offline.py`). The export / request
 * inputs are built by scripts/offline_fixtures.py with the repo's .venv Python; those two parts are skipped without it.
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { gunzipSync } from "node:zlib";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../..");
const pack = path.join(repo, "frontend/public/pyodide");
const python = path.join(repo, ".venv/bin/python");
const packPresent = existsSync(path.join(pack, "app.zip")) && existsSync(path.join(pack, "pyodide.asm.wasm"));
const hasPython = existsSync(python);
const testData = path.join(repo, "server/tests");

/** @typedef {{checked: number, mismatches: string[], seconds: number, [k: string]: unknown}} Report */
let py;
let fixtures;
const timings = {};
let pdfStack = null;

/** The PDF stack, loaded once on demand (what the worker's `prepare` does). */
async function loadPdfStack() {
  pdfStack ??= (async () => {
    const t = performance.now();
    py.unpackArchive(bytes(path.join(pack, "fonts.zip")), "zip", { extractDir: "/app" });
    await py.loadPackage(
      [
        "pillow",
        "fonttools",
        path.join(pack, "defusedxml-0.7.1-py2.py3-none-any.whl"),
        path.join(pack, "fpdf2-2.8.8-py3-none-any.whl"),
      ],
      { messageCallback: () => {} },
    );
    timings.pdf_stack_ms = performance.now() - t;
  })();
  return pdfStack;
}

const bytes = (p) => new Uint8Array(readFileSync(p));
/** @returns {Report} */
const run = (code) => JSON.parse(py.runPython(code));

describe.skipIf(!packPresent)("offline engine equals the native engine", () => {
  beforeAll(async () => {
    const t0 = performance.now();
    // vitest.config (server.deps.external) keeps public/pyodide out of vite's transform: a plain Node import.
    const { loadPyodide } = await import(/* @vite-ignore */ pathToFileURL(path.join(pack, "pyodide.mjs")).href);
    py = await loadPyodide({ indexURL: pack + "/", packageCacheDir: pack + "/" });
    timings.boot_ms = performance.now() - t0;
    const quiet = { messageCallback: () => {} };
    await py.loadPackage(["pyyaml"], quiet);
    py.unpackArchive(bytes(path.join(pack, "app.zip")), "zip", { extractDir: "/app" });
    timings.ready_ms = performance.now() - t0;
    py.FS.writeFile("/harness.py", readFileSync(path.join(here, "harness.py"), "utf8"));
    py.runPython("import sys; sys.path.insert(0, '/'); import harness; harness.setup()");
    py.FS.writeFile("/golden.json.gz", bytes(path.join(testData, "golden/c_series_mixed_2014_baseline.json.gz")));
    py.FS.writeFile("/export_baseline.json", bytes(path.join(testData, "export_baseline.json")));
    py.FS.writeFile("/service_baseline.json", bytes(path.join(testData, "service_baseline.json")));
    if (hasPython) {
      const out = path.join(mkdtempSync(path.join(tmpdir(), "offline-fx-")), "fixtures.json");
      const env = { ...process.env };
      delete env.DND_OFFICIAL_DATA; // the baselines are those of the bundled data
      const r = spawnSync(python, ["-I", path.join(repo, "scripts/offline_fixtures.py"), out], { env, encoding: "utf8" });
      if (r.status !== 0) throw new Error(`offline_fixtures.py failed: ${r.stderr}`);
      fixtures = out;
      py.FS.writeFile("/fixtures.json", bytes(out));
    }
  }, 600_000);

  afterAll(() => {
    console.log("offline timings", JSON.stringify(timings));
  });

  it("boots and imports the engine, catalog and service", () => {
    const r = JSON.parse(
      py.runPython(`
import json, time
t = time.perf_counter()
import service
from catalog.loader import load
json.dumps({"health": service.handle("GET", "/api/health")[0], "seconds": time.perf_counter() - t})`),
    );
    expect(r.health).toBe(200);
  });

  it("imports service and serves every non-PDF route before the PDF stack is loaded", () => {
    const r = JSON.parse(
      py.runPython(`
import json, sys, service
status = [service.handle("GET", "/api/catalog")[0], service.handle("GET", "/api/spells/fireball")[0]]
loaded = sorted(m for m in sys.modules if m.split(".")[0] in ("fpdf", "PIL", "fontTools", "defusedxml"))
json.dumps({"status": status, "loaded": loaded})`),
    );
    expect(r.status).toEqual([200, 200]);
    expect(r.loaded).toEqual([]);
  });

  it("matches every golden case", () => {
    const r = run("harness.golden()");
    timings.golden_s = r.seconds;
    expect(r.checked).toBe(Object.keys(JSON.parse(gunzipSync(readFileSync(path.join(testData, "golden/c_series_mixed_2014_baseline.json.gz"))).toString())).length);
    expect(r.checked).toBeGreaterThanOrEqual(251);
    expect(r.mismatches).toEqual([]);
  }, 600_000);

  it.skipIf(!hasPython)("matches the 90 export baseline hashes (Markdown, YAML, PDF)", async () => {
    await loadPdfStack();
    const r = run("harness.exports()");
    timings.exports_s = r.seconds;
    expect(r.checked).toBe(90);
    expect(r.ids).toBe(true);
    expect(r.mismatches).toEqual([]);
  }, 600_000);

  it.skipIf(!hasPython)("answers the fixed request list through service.handle like the Flask baseline", async () => {
    await loadPdfStack();
    const r = run("harness.requests()");
    timings.requests_s = r.seconds;
    expect(r.baselineSize).toBe(138);
    expect(r.checked).toBe(137); // all but GET /api, which Flask answers with the SPA catch-all
    expect(r.mismatches).toEqual([]);
    expect(fixtures).toBeDefined();
  }, 600_000);
});
