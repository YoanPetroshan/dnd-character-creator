// The worker transport against a fake worker: Response mapping, request mapping, boot wait, the 30 s timeout that starts
// only after boot, abort, and the failure shapes. (The real Pyodide behind the same transport: offline/transport.engine.test.mjs.)
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FromWorker, ToWorker } from "./engineProtocol";
import {
  buildResponse,
  createWorkerTransport,
  describeRequest,
  fetchWithTimeout,
  isTimeoutError,
  type WorkerLike,
} from "./workerTransport";

class FakeWorker implements WorkerLike {
  onmessage: ((event: { data: FromWorker }) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  sent: ToWorker[] = [];
  terminated = false;
  postMessage(m: ToWorker) {
    this.sent.push(m);
  }
  terminate() {
    this.terminated = true;
  }
  emit(m: FromWorker) {
    this.onmessage?.({ data: m });
  }
  requests() {
    return this.sent.filter((m): m is Extract<ToWorker, { t: "request" }> => m.t === "request");
  }
}

const buf = (s: string) => new TextEncoder().encode(s).buffer as ArrayBuffer;
const reply = (id: number, status = 200, body = "{}\n", extra: Record<string, string> = {}): FromWorker => ({
  t: "response", id, status, contentType: "application/json", headers: extra, body: buf(body),
});

let worker: FakeWorker;
const fallback = vi.fn(async () => new Response("from the network", { status: 200 }));
const make = (timeoutMs?: number) => {
  worker = new FakeWorker();
  fallback.mockClear();
  return createWorkerTransport({ spawn: () => worker, fallback, timeoutMs });
};
const flush = async () => {
  for (let i = 0; i < 5; i++) await Promise.resolve();
};

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("buildResponse", () => {
  it("makes a real Response: status, Content-Type, Content-Disposition, body bytes", async () => {
    const pdf = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0, 255, 128]);
    const r = buildResponse(200, "application/pdf", { "Content-Disposition": "attachment; filename*=UTF-8''%D0%B3.pdf" }, pdf.buffer.slice(0));
    expect(r).toBeInstanceOf(Response);
    expect(r.ok).toBe(true);
    expect(r.status).toBe(200);
    expect(r.headers.get("Content-Type")).toBe("application/pdf");
    expect(r.headers.get("Content-Disposition")).toBe("attachment; filename*=UTF-8''%D0%B3.pdf");
    expect(new Uint8Array(await r.arrayBuffer())).toEqual(pdf);
  });
  it("keeps error statuses and JSON bodies readable by the call sites", async () => {
    const r = buildResponse(400, "application/json", {}, buf('{"error":"bad"}\n'));
    expect(r.ok).toBe(false);
    expect(r.status).toBe(400);
    expect(await r.json()).toEqual({ error: "bad" });
  });
  it("gives a blob for exports", async () => {
    const r = buildResponse(200, "text/markdown; charset=utf-8", {}, buf("# Hi"));
    expect(await (await r.blob()).text()).toBe("# Hi");
  });
  it("a 204 carries no body", () => {
    expect(buildResponse(204, "application/json", {}, buf("")).status).toBe(204);
  });
});

describe("describeRequest", () => {
  it("splits path and query, decodes the path, defaults to GET", () => {
    const d = describeRequest("/api/spells/fire%20ball?class=wizard&q=%D0%B0");
    expect(d).toMatchObject({ method: "GET", path: "/api/spells/fire ball", query: "?class=wizard&q=%D0%B0", body: null });
  });
  it("sends a JSON body as bytes and drops one that is not declared as JSON (like the Flask adapter)", () => {
    const json = describeRequest("/api/resolve?lang=bg", { method: "post", headers: { "Content-Type": "application/json" }, body: '{"a":"я"}' });
    expect(json.method).toBe("POST");
    expect(new TextDecoder().decode(json.body!)).toBe('{"a":"я"}');
    expect(describeRequest("/api/resolve", { method: "POST", body: "{}" }).body).toBeNull();
    expect(describeRequest("/api/resolve", { method: "POST", headers: { "Content-Type": "text/plain" }, body: "{}" }).body).toBeNull();
  });
  it("refuses a body type it cannot carry", () => {
    expect(() => describeRequest("/x", { method: "POST", body: new FormData() })).toThrow(TypeError);
  });
});

describe("worker transport", () => {
  it("waits for the engine to boot, posts the request, and builds the Response from the reply", async () => {
    const t = make();
    expect(t.store.get().engine).toBe("starting");
    const p = t.fetch("/api/spells?class=wizard");
    await flush();
    expect(worker.requests()).toHaveLength(0); // still booting
    worker.emit({ t: "ready" });
    expect(t.store.get().engine).toBe("ready");
    await flush();
    const [req] = worker.requests();
    expect(req).toMatchObject({ method: "GET", path: "/api/spells", query: "?class=wizard", body: null });
    worker.emit(reply(req.id, 200, '{"spells":[]}\n'));
    const r = await p;
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ spells: [] });
  });

  it("answers concurrent requests by id, in any order", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const a = t.fetch("/api/a");
    const b = t.fetch("/api/b");
    await flush();
    const [ra, rb] = worker.requests();
    worker.emit(reply(rb.id, 200, '"b"'));
    worker.emit(reply(ra.id, 404, '"a"'));
    expect([(await a).status, (await b).status]).toEqual([404, 200]);
  });

  it("the timeout starts after boot, not before", async () => {
    const t = make(30_000);
    const p = t.fetch("/api/resolve", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const settled = vi.fn();
    p.then(settled, settled);
    await vi.advanceTimersByTimeAsync(120_000); // a long boot: far beyond 30 s
    expect(settled).not.toHaveBeenCalled();
    worker.emit({ t: "ready" });
    await flush();
    const [req] = worker.requests();
    await vi.advanceTimersByTimeAsync(29_000);
    expect(settled).not.toHaveBeenCalled();
    worker.emit(reply(req.id));
    expect((await p).status).toBe(200);
  });

  it("rejects with a TimeoutError 30 s after the engine got the request, and drops the late reply", async () => {
    const t = make(30_000);
    worker.emit({ t: "ready" });
    const p = t.fetch("/api/resolve");
    const caught = p.catch((e) => e);
    await flush();
    const [req] = worker.requests();
    await vi.advanceTimersByTimeAsync(30_001);
    const err = await caught;
    expect(isTimeoutError(err)).toBe(true);
    expect(worker.sent.at(-1)).toEqual({ t: "cancel", id: req.id });
    worker.emit(reply(req.id)); // late: ignored, no throw
  });

  it("a per-call timeoutMs overrides the default", async () => {
    const t = make(30_000);
    worker.emit({ t: "ready" });
    const caught = t.fetch("/api/x", { timeoutMs: 1000 }).catch((e) => e);
    await flush();
    await vi.advanceTimersByTimeAsync(1001);
    expect(isTimeoutError(await caught)).toBe(true);
  });

  it("an abort while the engine is booting rejects at once with an AbortError and sends nothing", async () => {
    const t = make();
    const c = new AbortController();
    const caught = t.fetch("/api/x", { signal: c.signal }).catch((e) => e);
    await flush();
    c.abort();
    const err = await caught;
    expect(err.name).toBe("AbortError");
    worker.emit({ t: "ready" });
    await flush();
    expect(worker.requests()).toHaveLength(0);
  });

  it("an already-aborted signal never reaches the engine", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const c = new AbortController();
    c.abort();
    await expect(t.fetch("/api/x", { signal: c.signal })).rejects.toMatchObject({ name: "AbortError" });
    expect(worker.requests()).toHaveLength(0);
  });

  it("an abort after the request was sent rejects with an AbortError, cancels it, and drops the reply", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const c = new AbortController();
    const caught = t.fetch("/api/x", { signal: c.signal }).catch((e) => e);
    await flush();
    const [req] = worker.requests();
    c.abort();
    expect((await caught).name).toBe("AbortError");
    expect(worker.sent.at(-1)).toEqual({ t: "cancel", id: req.id });
    worker.emit(reply(req.id)); // dropped
    // the timer was cleared: nothing fires later
    await vi.advanceTimersByTimeAsync(60_000);
  });

  it("a boot error hands the call to plain fetch and everything after it", async () => {
    const t = make();
    const p = t.fetch("/api/health");
    worker.emit({ t: "boot-error", message: "no wasm" });
    expect(await (await p).text()).toBe("from the network");
    expect(t.store.get().engine).toBe("fallback");
    expect(worker.terminated).toBe(true);
    expect(await (await t.fetch("/api/health")).text()).toBe("from the network");
    expect(fallback).toHaveBeenCalledTimes(2);
  });

  it("a worker that cannot be created falls back too", async () => {
    fallback.mockClear();
    const t = createWorkerTransport({ spawn: () => { throw new Error("no module workers"); }, fallback });
    expect((await t.fetch("/api/health")).status).toBe(200);
    expect(t.store.get().engine).toBe("fallback");
  });

  it("a crash after boot fails the waiting calls like a lost connection (TypeError)", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const caught = t.fetch("/api/x").catch((e) => e);
    await flush();
    worker.onerror?.({});
    const err = await caught;
    expect(err).toBeInstanceOf(TypeError);
    expect(t.store.get().engine).toBe("fallback");
  });

  it("an engine failure on one request is a TypeError for that request only", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const a = t.fetch("/api/a").catch((e) => e);
    const b = t.fetch("/api/b");
    await flush();
    const [ra, rb] = worker.requests();
    worker.emit({ t: "failure", id: ra.id, message: "boom" });
    worker.emit(reply(rb.id));
    expect(await a).toBeInstanceOf(TypeError);
    expect((await b).status).toBe(200);
  });

  it("notifies subscribers of the engine state", () => {
    const t = make();
    const seen: string[] = [];
    t.store.subscribe(() => seen.push(t.store.get().engine));
    worker.emit({ t: "ready" });
    expect(seen).toEqual(["ready"]);
  });
});

describe("the PDF stack", () => {
  const pdfPost = (t: ReturnType<typeof make>, extra: RequestInit = {}) =>
    t.fetch("/api/export/pdf?lang=bg", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}", ...extra });
  const prepares = () => worker.sent.filter((m) => m.t === "prepare");

  it("only a PDF export asks for it: the other routes and exports never do", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const a = t.fetch("/api/export/markdown", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const b = t.fetch("/api/export/pdf"); // a GET is not the export
    await flush();
    for (const r of worker.requests()) worker.emit(reply(r.id));
    await Promise.all([a, b]);
    expect(prepares()).toHaveLength(0);
    expect(t.store.get().pdf).toBe("idle");
  });

  it("the fillable sheet export needs the PDF stack too (it also needs pypdf)", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const p = t.fetch("/api/export/sheet?lang=en", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    await flush();
    expect(prepares()).toEqual([{ t: "prepare", what: "pdf" }]);
    expect(worker.requests()).toHaveLength(0);
    worker.emit({ t: "prepared", what: "pdf" });
    await flush();
    const [req] = worker.requests();
    expect(req.path).toBe("/api/export/sheet");
    worker.emit(reply(req.id));
    expect((await p).status).toBe(200);
  });

  it("the first PDF export loads the stack first (state loading), then sends the request, and later ones do not load again", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const states: string[] = [];
    t.store.subscribe(() => states.push(t.store.get().pdf));
    const p = pdfPost(t);
    await flush();
    expect(prepares()).toEqual([{ t: "prepare", what: "pdf" }]);
    expect(worker.requests()).toHaveLength(0); // not before the stack is there
    expect(t.store.get().pdf).toBe("loading");
    worker.emit({ t: "prepared", what: "pdf" });
    await flush();
    const [req] = worker.requests();
    expect(req.path).toBe("/api/export/pdf");
    worker.emit(reply(req.id));
    expect((await p).status).toBe(200);
    expect(states).toEqual(["loading", "ready"]);
    const again = pdfPost(t);
    await flush();
    expect(prepares()).toHaveLength(1);
    worker.emit(reply(worker.requests()[1].id));
    await again;
  });

  it("two PDF exports at once share one load", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const a = pdfPost(t);
    const b = pdfPost(t);
    await flush();
    expect(prepares()).toHaveLength(1);
    worker.emit({ t: "prepared", what: "pdf" });
    await flush();
    for (const r of worker.requests()) worker.emit(reply(r.id));
    await Promise.all([a, b]);
  });

  it("the timeout does not count the preparation", async () => {
    const t = make(30_000);
    worker.emit({ t: "ready" });
    const p = pdfPost(t);
    const settled = vi.fn();
    p.then(settled, settled);
    await vi.advanceTimersByTimeAsync(90_000); // a slow first load
    expect(settled).not.toHaveBeenCalled();
    worker.emit({ t: "prepared", what: "pdf" });
    await flush();
    await vi.advanceTimersByTimeAsync(29_000);
    expect(settled).not.toHaveBeenCalled();
    worker.emit(reply(worker.requests()[0].id));
    expect((await p).status).toBe(200);
  });

  it("an abort during the preparation rejects with an AbortError; the load goes on and the next export reuses it", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const c = new AbortController();
    const caught = pdfPost(t, { signal: c.signal }).catch((e) => e);
    await flush();
    c.abort();
    expect((await caught).name).toBe("AbortError");
    worker.emit({ t: "prepared", what: "pdf" });
    const next = pdfPost(t);
    await flush();
    expect(prepares()).toHaveLength(1);
    expect(worker.requests()).toHaveLength(1);
    worker.emit(reply(worker.requests()[0].id));
    await next;
  });

  it("a failed load is a TypeError, the state goes back to idle, and the next export tries again", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    const caught = pdfPost(t).catch((e) => e);
    await flush();
    worker.emit({ t: "prepare-error", what: "pdf", message: "wheel missing" });
    expect(await caught).toBeInstanceOf(TypeError);
    expect(t.store.get().pdf).toBe("idle");
    void pdfPost(t).catch(() => undefined);
    await flush();
    expect(prepares()).toHaveLength(2);
  });

  it("eager mode: the worker announces and finishes the load by itself, and no export asks for it", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    worker.emit({ t: "preparing", what: "pdf" });
    expect(t.store.get().pdf).toBe("loading");
    worker.emit({ t: "prepared", what: "pdf" });
    expect(t.store.get().pdf).toBe("ready");
    const p = pdfPost(t);
    await flush();
    expect(prepares()).toHaveLength(0);
    worker.emit(reply(worker.requests()[0].id));
    await p;
  });

  it("an export that arrives while the eager load runs waits for it instead of asking again", async () => {
    const t = make();
    worker.emit({ t: "ready" });
    worker.emit({ t: "preparing", what: "pdf" });
    const p = pdfPost(t);
    await flush();
    expect(worker.requests()).toHaveLength(0);
    worker.emit({ t: "prepared", what: "pdf" });
    await flush();
    expect(prepares()).toHaveLength(0);
    worker.emit(reply(worker.requests()[0].id));
    await p;
  });
});

describe("plain fetch with a timeout", () => {
  it("passes through without timeoutMs, and strips the extension", async () => {
    const f = vi.fn(async (_i: unknown, init?: RequestInit) => new Response(String(Object.keys(init ?? {}))));
    expect(await (await fetchWithTimeout(f, "/x", { method: "POST", timeoutMs: 0 })).text()).toBe("method");
  });
  it("aborts with a TimeoutError after timeoutMs, and honours the caller's signal", async () => {
    const hang = (_i: unknown, init?: RequestInit) =>
      new Promise<Response>((_res, rej) => init?.signal?.addEventListener("abort", () => rej(init.signal!.reason)));
    const p = fetchWithTimeout(hang, "/x", { timeoutMs: 500 }).catch((e) => e);
    await vi.advanceTimersByTimeAsync(501);
    expect(isTimeoutError(await p)).toBe(true);
    const c = new AbortController();
    const q = fetchWithTimeout(hang, "/x", { timeoutMs: 500, signal: c.signal }).catch((e) => e);
    c.abort();
    expect((await q).name).toBe("AbortError");
  });
});
