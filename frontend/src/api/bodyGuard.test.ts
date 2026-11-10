// VF7.6: the offline body guards: the numbers equal server/service.py's, the byte scan agrees with the server's scan, and
// engineCore hands the verdict to the service instead of copying a hostile body into WebAssembly.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { MAX_BODY_BYTES, MAX_JSON_DEPTH, bodyProblem, jsonDepthExceeds } from "./bodyGuard";
import { createEngine, type EngineIO } from "./engineCore";

const enc = (s: string) => new TextEncoder().encode(s);
const rep = (ch: string, n: number) => ch.repeat(n);

describe("limits", () => {
  it("equal the server's (server/service.py)", () => {
    const src = readFileSync(new URL("../../../server/service.py", import.meta.url)).toString("utf8");
    expect(Number(/^MAX_JSON_DEPTH = (\d+)/m.exec(src)?.[1])).toBe(MAX_JSON_DEPTH);
    expect(Number((/^MAX_BODY_BYTES = ([\d_]+)/m.exec(src)?.[1] ?? "").replace(/_/g, ""))).toBe(MAX_BODY_BYTES);
  });
});

describe("jsonDepthExceeds", () => {
  it("counts brackets, not strings", () => {
    expect(jsonDepthExceeds(enc(rep("[", 64) + rep("]", 64)))).toBe(false);
    expect(jsonDepthExceeds(enc(rep("[", 65) + rep("]", 65)))).toBe(true);
    expect(jsonDepthExceeds(enc(`{"a": "${rep("[", 500)}", "b": "\\"${rep("{", 500)}"}`))).toBe(false);
    expect(jsonDepthExceeds(enc(`{"name":${rep("[", 70)}${rep("]", 70)}}`))).toBe(true);
    expect(jsonDepthExceeds(enc('{"é":"Ана \u{1F409} [[["}'))).toBe(false);
  });
  it("flags an unbalanced run like the server's raw scan and stops at once", () => {
    expect(jsonDepthExceeds(enc(rep("[", 450000)))).toBe(true);
    expect(jsonDepthExceeds(enc(rep("[", 64)))).toBe(false);
  });
  it("is fast for a 1 MB body", () => {
    const body = enc(JSON.stringify({ details: { notes: Array.from({ length: 15000 }, () => "y".repeat(50)) } }));
    const t = performance.now();
    expect(jsonDepthExceeds(body)).toBe(false);
    expect(performance.now() - t).toBeLessThan(200);
  });
});

describe("bodyProblem", () => {
  it("is null without a body and for ordinary drafts, size first", () => {
    expect(bodyProblem(null)).toBeNull();
    expect(bodyProblem(enc('{"name":"x"}'))).toBeNull();
    expect(bodyProblem(new Uint8Array(MAX_BODY_BYTES))).toBeNull(); // the limit itself is allowed (Flask: > 1,000,000 is refused)
    expect(bodyProblem(new Uint8Array(MAX_BODY_BYTES + 1))).toBe("too-large");
    expect(bodyProblem(enc(rep("[", 450000)))).toBe("too-deep");
    expect(bodyProblem(new Uint8Array(MAX_BODY_BYTES + 1).fill(0x5b))).toBe("too-large");
  });
});

describe("engineCore.call", () => {
  function fakeIo() {
    const calls: unknown[][] = [];
    const bridge = (...args: unknown[]) => {
      calls.push(args);
      return { toJs: () => [200, "application/json", {}, new Uint8Array([123, 125])], destroy() {} };
    };
    const py = {
      loadPackage: async () => undefined,
      unpackArchive: () => undefined,
      runPython: () => undefined,
      globals: { get: () => bridge },
    };
    const io: EngineIO = { loadPyodide: async () => py, readBytes: async () => new Uint8Array(), assetRef: (n) => n };
    return { io, calls };
  }

  it("passes a normal body through and no problem", async () => {
    const f = fakeIo();
    const engine = createEngine(f.io);
    await engine.boot();
    const body = enc('{"name":"x"}');
    engine.call("POST", "/api/resolve", "", body);
    expect(f.calls[0]).toEqual(["POST", "/api/resolve", "", body, undefined]);
    engine.call("GET", "/api/health", "", null);
    expect(f.calls[1]).toEqual(["GET", "/api/health", "", undefined, undefined]);
  });

  it("does not copy a too-large or too-deep body into the engine, it names the problem", async () => {
    const f = fakeIo();
    const engine = createEngine(f.io);
    await engine.boot();
    engine.call("POST", "/api/resolve", "", new Uint8Array(MAX_BODY_BYTES + 1));
    engine.call("POST", "/api/export/yaml", "?lang=bg", enc(rep("[", 450000)));
    expect(f.calls[0]).toEqual(["POST", "/api/resolve", "", undefined, "too-large"]);
    expect(f.calls[1]).toEqual(["POST", "/api/export/yaml", "?lang=bg", undefined, "too-deep"]);
  });
});
