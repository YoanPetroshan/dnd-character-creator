/**
 * O2: the worker transport on the REAL engine. The same engineCore + engineHost the browser worker runs, on Pyodide in
 * Node, behind an in-process stand-in for the Worker (messages are structured-cloned like a real worker's). Checks that
 * apiFetch's answers are what the Flask server answered: health, a resolve of a real draft, a catalog read, a Markdown
 * and a PDF export with Content-Disposition, JSON errors with their status, abort and timeout.
 * Skipped when the pack is absent (`.venv/bin/python scripts/build_offline.py`).
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import { createEngine } from "../api/engineCore.ts";
import { createEngineHost } from "../api/engineHost.ts";
import { createWorkerTransport } from "../api/workerTransport.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const pack = path.resolve(here, "../../public/pyodide");
const packPresent = existsSync(path.join(pack, "app.zip")) && existsSync(path.join(pack, "pyodide.asm.wasm"));

// = server/tests/service_requests.exportable_draft(): a Fighter 1 that passes the export gate (SRD, 2014 rules)
const draft = {"name": "Torvin Bracewell", "sources": ["srd"], "classes": [{"classId": "fighter", "level": 1, "choices": {"class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"], "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"]}}], "background": {"id": "acolyte", "choices": {"background:acolyte:languages": ["dwarvish", "elvish"]}}, "species": {"id": "human", "choices": {"species:human:languages": ["giant"]}}, "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}}, "equipment": {"added": [], "skipped": false, "choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"], "class:fighter:1:equipment-choice-2": ["handaxe"], "class:fighter:1:equipment-choice-3": ["explorers-pack"]}}, "details": {}};
const json = { "Content-Type": "application/json" };
const post = (url, body) => ({ method: "POST", headers: json, body: JSON.stringify(body) });

describe.skipIf(!packPresent)("worker transport on the real Pyodide engine", () => {
  let t;
  let bootMs;
  beforeAll(async () => {
    const t0 = performance.now();
    const io = {
      async loadPyodide() {
        const { loadPyodide } = await import(/* @vite-ignore */ pathToFileURL(path.join(pack, "pyodide.mjs")).href);
        return loadPyodide({ indexURL: pack + "/", packageCacheDir: pack + "/" });
      },
      readBytes: async (name) => new Uint8Array(readFileSync(path.join(pack, name))),
      assetRef: (name) => path.join(pack, name),
    };
    const worker = {
      onmessage: null,
      onerror: null,
      terminate() {},
      postMessage(m) {
        // a real worker receives a structured clone, in a later task
        const copy = structuredClone(m);
        setTimeout(() => host.onMessage(copy), 0);
      },
    };
    const host = createEngineHost(createEngine(io), (m) => setTimeout(() => worker.onmessage?.({ data: structuredClone(m) }), 0));
    t = createWorkerTransport({ spawn: () => worker, fallback: async () => { throw new TypeError("no network"); }, timeoutMs: 120_000 });
    await host.booted;
    await new Promise((r) => setTimeout(r, 20)); // the "ready" message is delivered in a later task
    bootMs = performance.now() - t0;
  }, 600_000);

  it("is ready after boot", () => {
    expect(t.store.get().engine).toBe("ready");
    console.log("engine boot (Node)", Math.round(bootMs), "ms");
  });

  it("answers /api/health like the server", async () => {
    const r = await t.fetch("/api/health");
    expect(r.status).toBe(200);
    expect(r.headers.get("Content-Type")).toBe("application/json");
    const body = await r.json();
    expect(body.ok).toBe(true);
    expect(body.draftVersion).toBe(2);
  });

  it("resolves a draft and returns the sheet", async () => {
    const r = await t.fetch("/api/resolve?lang=en", post("", draft));
    expect(r.status).toBe(200);
    const res = await r.json();
    expect(res.sheet.classes[0].name).toBe("Fighter");
    expect(res.problems).toEqual([]);
  });

  it("reads the catalog, a class page and a spell, with query strings", async () => {
    const cat = await (await t.fetch("/api/catalog?ruleset=2014&sources=srd")).json();
    expect(cat.classes.length).toBeGreaterThan(5);
    const cls = await t.fetch("/api/catalog/class/wizard");
    expect(cls.status).toBe(200);
    const spells = await (await t.fetch("/api/spells?class=wizard&level=0")).json();
    expect(spells.spells.length).toBeGreaterThan(3);
    expect((await t.fetch("/api/spells/fireball")).status).toBe(200);
    expect((await t.fetch("/api/spells/no-such-spell")).status).toBe(404);
  });

  it("keeps the server's error shapes: 400 for a bad level, 404 for an unknown path", async () => {
    const bad = await t.fetch("/api/spells?class=wizard&level=x");
    expect(bad.status).toBe(400);
    expect(typeof (await bad.json()).error).toBe("string");
    expect((await t.fetch("/api/nope")).status).toBe(404);
    expect((await t.fetch("/api/resolve", { method: "POST", headers: json, body: "[1]" })).status).toBe(400);
  });

  it("exports Markdown, YAML and PDF with Content-Disposition and real bytes; the PDF stack loads on the first PDF only", async () => {
    expect(t.store.get().pdf).toBe("idle");
    const md = await t.fetch("/api/export/markdown?lang=en", post("", draft));
    expect(md.status).toBe(200);
    expect(md.headers.get("Content-Type")).toBe("text/markdown; charset=utf-8");
    expect(md.headers.get("Content-Disposition")).toBe("attachment; filename*=UTF-8''Torvin%20Bracewell.md");
    expect(await md.text()).toContain("Fighter");
    expect((await (await t.fetch("/api/export/yaml", post("", draft))).text()).length).toBeGreaterThan(100);
    expect(t.store.get().pdf).toBe("idle"); // Markdown and YAML did not need the PDF stack
    const states = [];
    t.store.subscribe(() => states.push(t.store.get().pdf));
    const pdf = await t.fetch("/api/export/pdf?lang=bg", post("", draft));
    expect(pdf.status).toBe(200);
    expect(pdf.headers.get("Content-Type")).toBe("application/pdf");
    const bytes = new Uint8Array(await (await pdf.blob()).arrayBuffer());
    expect(new TextDecoder().decode(bytes.slice(0, 5))).toBe("%PDF-");
    expect(bytes.length).toBeGreaterThan(5000);
    expect(states).toEqual(["loading", "ready"]);
    // the second one reuses the loaded stack
    expect((await t.fetch("/api/export/pdf", post("", draft))).status).toBe(200);
    expect(states).toEqual(["loading", "ready"]);
  }, 120_000);

  it("an unfinished draft is refused with the problems list (400)", async () => {
    const r = await t.fetch("/api/export/markdown", post("", { ...draft, classes: [] }));
    expect(r.status).toBe(400);
    expect((await r.json()).problems.length).toBeGreaterThan(0);
  });

  it("aborts: the call rejects with an AbortError and the engine stays usable", async () => {
    const c = new AbortController();
    const p = t.fetch("/api/resolve", { ...post("", draft), signal: c.signal }).catch((e) => e);
    c.abort();
    expect((await p).name).toBe("AbortError");
    expect((await t.fetch("/api/health")).status).toBe(200);
  });
});
