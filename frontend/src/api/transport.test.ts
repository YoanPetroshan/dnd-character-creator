// Selection logic of apiFetch: which implementation answers, decided from the build flag, the browser and the pack.
import { describe, expect, it, vi } from "vitest";
import { chooseEngine, createApiTransport, detectPack, flagOn } from "./transport";
import type { Transport } from "./workerTransport";
import { createStatusStore } from "./engineStatus";

describe("chooseEngine", () => {
  const on = { flag: "1", hasWebAssembly: true, hasWorker: true, packPresent: true };
  it("uses the worker only when the flag, WebAssembly, Workers and the pack are all there", () => {
    expect(chooseEngine(on)).toBe("worker");
    expect(chooseEngine({ ...on, flag: undefined })).toBe("fetch");
    expect(chooseEngine({ ...on, flag: "0" })).toBe("fetch");
    expect(chooseEngine({ ...on, flag: "" })).toBe("fetch");
    expect(chooseEngine({ ...on, hasWebAssembly: false })).toBe("fetch"); // e.g. iOS Lockdown Mode
    expect(chooseEngine({ ...on, hasWorker: false })).toBe("fetch");
    expect(chooseEngine({ ...on, packPresent: false })).toBe("fetch");
  });
  it("reads the flag leniently", () => {
    for (const f of ["1", "true", "TRUE", "on", "worker", " 1 "]) expect(flagOn(f)).toBe(true);
    for (const f of ["0", "false", "off", "fetch", "", undefined]) expect(flagOn(f)).toBe(false);
  });
});

describe("detectPack", () => {
  const json = (body: unknown, init?: ResponseInit) => async () => new Response(typeof body === "string" ? body : JSON.stringify(body), init);
  it("is true for the pack's pack.json", async () => {
    expect(await detectPack(json({ "app.zip": {}, "pyodide.asm.wasm": {} }) as typeof fetch, "/")).toBe(true);
  });
  it("is false for the SPA's index.html answered with 200, a 404, or a network failure", async () => {
    expect(await detectPack(json("<!doctype html><div id=root>") as typeof fetch, "/")).toBe(false);
    expect(await detectPack(json({}, { status: 404 }) as typeof fetch, "/")).toBe(false);
    expect(await detectPack((async () => { throw new TypeError("offline"); }) as typeof fetch, "/")).toBe(false);
  });
  it("looks under the base URL", async () => {
    const f = vi.fn(json({ "app.zip": 1, "pyodide.asm.wasm": 1 }));
    await detectPack(f as unknown as typeof fetch, "/builder/");
    expect((f.mock.calls as unknown[][])[0][0]).toBe("/builder/pyodide/pack.json");
  });
});

describe("createApiTransport", () => {
  const plain = () => vi.fn(async () => new Response("server"));
  const fakeWorker = (): Transport & { calls: number } => {
    const store = createStatusStore({ engine: "starting", pdf: "idle" });
    const t = { calls: 0, store, fetch: async () => (t.calls++, new Response("engine")) };
    return t;
  };
  const text = async (p: Promise<Response>) => (await p).text();

  it("flag off (npm run dev): plain fetch, nothing detected, nothing started, state off", async () => {
    const f = plain();
    const detect = vi.fn(async () => true);
    const make = vi.fn(fakeWorker);
    const t = createApiTransport({ flag: undefined, baseUrl: "/", plainFetch: f as unknown as typeof fetch, detect, makeWorkerTransport: make });
    expect(await text(t.apiFetch("/api/health"))).toBe("server");
    expect(detect).not.toHaveBeenCalled();
    expect(make).not.toHaveBeenCalled();
    expect(t.snapshot().engine).toBe("off");
    expect(f).toHaveBeenCalledWith("/api/health", {});
  });

  it("flag on but no WebAssembly: plain fetch, pack not even looked for", async () => {
    const detect = vi.fn(async () => true);
    const t = createApiTransport({ flag: "1", baseUrl: "/", plainFetch: plain() as unknown as typeof fetch, environment: { hasWebAssembly: false, hasWorker: true }, detect, makeWorkerTransport: fakeWorker });
    expect(await text(t.apiFetch("/api/health"))).toBe("server");
    expect(detect).not.toHaveBeenCalled();
    expect(t.snapshot().engine).toBe("off");
  });

  it("flag on, pack absent: plain fetch and the state goes starting -> off", async () => {
    let release!: (v: boolean) => void;
    const detect = () => new Promise<boolean>((r) => (release = r));
    const t = createApiTransport({ flag: "1", baseUrl: "/", plainFetch: plain() as unknown as typeof fetch, environment: { hasWebAssembly: true, hasWorker: true }, detect, makeWorkerTransport: fakeWorker });
    await Promise.resolve();
    expect(t.snapshot().engine).toBe("starting");
    release(false);
    expect(await text(t.apiFetch("/api/health"))).toBe("server");
    expect(t.snapshot().engine).toBe("off");
  });

  it("flag on and everything present: the worker transport answers and its state is mirrored", async () => {
    const w = fakeWorker();
    const t = createApiTransport({ flag: "1", baseUrl: "/", plainFetch: plain() as unknown as typeof fetch, environment: { hasWebAssembly: true, hasWorker: true }, detect: async () => true, makeWorkerTransport: () => w });
    const seen: string[] = [];
    t.subscribe(() => seen.push(t.snapshot().engine));
    expect(await text(t.apiFetch("/api/health"))).toBe("engine");
    expect(w.calls).toBe(1);
    w.store.set({ engine: "ready" });
    expect(t.snapshot().engine).toBe("ready");
    expect(seen.at(-1)).toBe("ready");
    w.store.set({ engine: "fallback" });
    expect(t.snapshot().engine).toBe("fallback");
  });

  it("plain fetch honours timeoutMs with a TimeoutError", async () => {
    vi.useFakeTimers();
    try {
      const hang = vi.fn((_i: unknown, init?: RequestInit) => new Promise<Response>((_r, rej) => init?.signal?.addEventListener("abort", () => rej(init.signal!.reason))));
      const t = createApiTransport({ flag: undefined, baseUrl: "/", plainFetch: hang as unknown as typeof fetch });
      const p = t.apiFetch("/api/resolve", { timeoutMs: 30_000 }).catch((e) => e);
      await vi.advanceTimersByTimeAsync(30_001);
      expect((await p).name).toBe("TimeoutError");
    } finally {
      vi.useRealTimers();
    }
  });
});
