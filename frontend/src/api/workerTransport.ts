// The worker transport: apiFetch's answer when the engine runs in the browser (a module Web Worker with Pyodide, see
// engine.worker.ts). It turns a fetch call into {method, path, query, body}, waits for the engine to boot, and builds a
// real Response from the reply, so the call sites cannot tell it from the network.
//
// Error shapes are fetch's: an aborted signal rejects with an AbortError DOMException (the reply, if it still comes, is
// dropped); the 30 s timeout rejects with a TimeoutError DOMException and starts only when the request is handed to the
// booted engine (never while Pyodide is still starting); an engine that cannot be reached rejects with a TypeError, like
// a failed network request. A worker that cannot boot at all hands the call to the plain-fetch fallback.
//
// The PDF stack is not part of the boot: the first POST /api/export/pdf asks the worker to load it (state `pdf:
// "loading"`, which the Export page shows as "preparing PDF") and is sent when that is done; the timeout of that request
// starts after the preparation, like after the boot.
import type { EngineSnapshot, FromWorker, ToWorker } from "./engineProtocol";
import { createStatusStore, type StatusStore } from "./engineStatus";

export const DEFAULT_TIMEOUT_MS = 30_000;

/** The part of a Worker the transport uses (a fake in the tests). */
export interface WorkerLike {
  postMessage(message: ToWorker, transfer?: Transferable[]): void;
  terminate(): void;
  onmessage: ((event: { data: FromWorker }) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onmessageerror?: ((event: unknown) => void) | null;
}

export type ApiInit = RequestInit & {
  /** Reject with a TimeoutError after this many ms. In the worker transport it counts from the moment the booted engine
   *  receives the request; the transport default (30 s) applies when absent. */
  timeoutMs?: number;
};
export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface Transport {
  fetch(input: RequestInfo | URL, init?: ApiInit): Promise<Response>;
  readonly store: StatusStore;
}

export const abortError = (signal?: AbortSignal | null): unknown =>
  signal?.reason ?? new DOMException("The operation was aborted.", "AbortError");
export const timeoutError = (): DOMException => new DOMException("The request timed out.", "TimeoutError");
export const isTimeoutError = (err: unknown): boolean => (err as { name?: unknown } | null)?.name === "TimeoutError";

/** fetch with `timeoutMs` (the plain-fetch half of ApiInit). */
export function fetchWithTimeout(fetchImpl: FetchLike, input: RequestInfo | URL, init: ApiInit = {}): Promise<Response> {
  const { timeoutMs, ...rest } = init;
  if (!timeoutMs) return fetchImpl(input, rest);
  const controller = new AbortController();
  const outer = rest.signal;
  const onOuter = () => controller.abort(abortError(outer));
  if (outer?.aborted) onOuter();
  else outer?.addEventListener("abort", onOuter, { once: true });
  const timer = setTimeout(() => controller.abort(timeoutError()), timeoutMs);
  return fetchImpl(input, { ...rest, signal: controller.signal }).finally(() => {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onOuter);
  });
}

interface Described {
  method: string;
  path: string;
  query: string;
  body: Uint8Array | null;
  signal: AbortSignal | null;
}

const JSON_TYPE = /json/i;

/** fetch's arguments as the service wants them. As with the Flask adapter, a body is only passed when the request says
 *  it is JSON (the service ignores any other, as Flask's get_json(silent=True) did). */
export function describeRequest(input: RequestInfo | URL, init: RequestInit = {}): Described {
  const isReq = typeof Request !== "undefined" && input instanceof Request;
  const raw = typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;
  const url = new URL(raw, "http://engine.local");
  const method = (init.method ?? (isReq ? (input as Request).method : "GET")).toUpperCase();
  const headers = new Headers(init.headers ?? (isReq ? (input as Request).headers : undefined));
  let body: Uint8Array | null = null;
  const b = init.body;
  if (b !== undefined && b !== null) {
    if (typeof b === "string") body = new TextEncoder().encode(b);
    else if (b instanceof ArrayBuffer) body = new Uint8Array(b.slice(0));
    else if (ArrayBuffer.isView(b)) body = new Uint8Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
    else throw new TypeError("The engine transport accepts string and binary request bodies only.");
  }
  if (body && !JSON_TYPE.test(headers.get("Content-Type") ?? "")) body = null;
  return { method, path: decodeURIComponent(url.pathname), query: url.search, body, signal: init.signal ?? null };
}

/** The Response of an engine reply. */
export function buildResponse(status: number, contentType: string, headers: Record<string, string>, body: ArrayBuffer): Response {
  const h = new Headers(headers);
  h.set("Content-Type", contentType);
  // 204 / 304 may not carry a body in a Response; the service never answers them, this keeps a future one valid.
  return new Response(status === 204 || status === 304 ? null : body, { status, headers: h });
}

export interface WorkerTransportOptions {
  spawn(): WorkerLike;
  /** Plain fetch: used when the worker cannot boot, and for anything the engine cannot take. */
  fallback: FetchLike;
  timeoutMs?: number;
}

/** The one request that needs the PDF stack. */
export const needsPdfStack = (method: string, path: string): boolean => method === "POST" && path === "/api/export/pdf";

interface Pending {
  resolve(r: Response): void;
  reject(e: unknown): void;
}

export function createWorkerTransport(options: WorkerTransportOptions): Transport {
  const timeoutDefault = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const store = createStatusStore({ engine: "starting", pdf: "idle" });
  const pending = new Map<number, Pending>();
  let nextId = 1;
  let worker: WorkerLike | null = null;

  // the PDF stack: loaded on demand (or eagerly by the worker), once
  let pdfReady: Promise<void> | null = null;
  let pdfSettle: { resolve(): void; reject(e: unknown): void } | null = null;
  const startPdf = (): Promise<void> => {
    if (!pdfReady) {
      store.set({ pdf: "loading" });
      pdfReady = new Promise<void>((resolve, reject) => (pdfSettle = { resolve, reject }));
      pdfReady.catch(() => undefined); // the callers handle it; never an unhandled rejection
    }
    return pdfReady;
  };
  /** Ask the worker for the PDF stack (idempotent; shared by concurrent exports). */
  const preparePdf = (): Promise<void> => {
    if (store.get().pdf === "ready") return Promise.resolve();
    const fresh = !pdfReady;
    const p = startPdf();
    if (fresh) worker?.postMessage({ t: "prepare", what: "pdf" });
    return p;
  };

  let bootDone!: (ok: boolean) => void;
  const booted = new Promise<boolean>((r) => (bootDone = r));
  let bootSettled = false;

  const settleBoot = (ok: boolean) => {
    if (bootSettled) return;
    bootSettled = true;
    store.set({ engine: ok ? "ready" : "fallback" });
    bootDone(ok);
  };

  /** The worker is gone or broken: fail what is waiting on it like a lost connection and use plain fetch from now on. */
  const lose = (reason: string) => {
    settleBoot(false);
    store.set({ engine: "fallback" });
    for (const [, p] of pending) p.reject(new TypeError(reason));
    pending.clear();
    pdfSettle?.reject(new TypeError(reason));
    pdfSettle = null;
    pdfReady = null;
    store.set({ pdf: "idle" });
    try {
      worker?.terminate();
    } catch {
      // already gone
    }
    worker = null;
  };

  try {
    worker = options.spawn();
    worker.onmessage = (e) => {
      const m = e.data;
      if (m.t === "ready") settleBoot(true);
      else if (m.t === "boot-error") lose(`engine failed to start: ${m.message}`);
      else if (m.t === "response") {
        const p = pending.get(m.id);
        if (p) {
          pending.delete(m.id);
          p.resolve(buildResponse(m.status, m.contentType, m.headers, m.body));
        } // else: aborted or timed out earlier, the reply is dropped
      } else if (m.t === "preparing") {
        void startPdf(); // the worker loads it by itself (eager mode)
      } else if (m.t === "prepared") {
        void startPdf();
        store.set({ pdf: "ready" });
        pdfSettle?.resolve();
        pdfSettle = null;
      } else if (m.t === "prepare-error") {
        // a later export tries again
        const s = pdfSettle;
        pdfSettle = null;
        pdfReady = null;
        store.set({ pdf: "idle" });
        s?.reject(new TypeError(`PDF stack failed to load: ${m.message}`));
      } else if (m.t === "failure") {
        const p = pending.get(m.id);
        if (p) {
          pending.delete(m.id);
          p.reject(new TypeError(m.message));
        }
      }
    };
    worker.onerror = () => lose("engine worker crashed");
  } catch {
    // no Worker / no module workers: plain fetch
    worker = null;
    settleBoot(false);
  }

  /** Wait for `p`; reject early when the caller aborts meanwhile (the work itself goes on). */
  function orAbort<T>(p: Promise<T>, signal: AbortSignal | null): Promise<T> {
    if (!signal) return p;
    if (signal.aborted) return Promise.reject(abortError(signal));
    return new Promise<T>((resolve, reject) => {
      const onAbort = () => reject(abortError(signal));
      signal.addEventListener("abort", onAbort, { once: true });
      p.then(
        (v) => {
          signal.removeEventListener("abort", onAbort);
          resolve(v);
        },
        (e) => {
          signal.removeEventListener("abort", onAbort);
          reject(e);
        },
      );
    });
  }

  async function fetchViaEngine(input: RequestInfo | URL, init: ApiInit = {}): Promise<Response> {
    const { timeoutMs, ...rest } = init;
    const req = describeRequest(input, rest);
    if (!(await orAbort(booted, req.signal)) || !worker) return fetchWithTimeout(options.fallback, input, init);
    if (needsPdfStack(req.method, req.path)) await orAbort(preparePdf(), req.signal);
    const signal = req.signal;
    if (signal?.aborted) throw abortError(signal);
    const w = worker as WorkerLike | null;
    if (!w) throw new TypeError("engine worker is gone"); // it crashed while the PDF stack was loading
    const id = nextId++;
    return new Promise<Response>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | undefined;
      const finish = () => {
        clearTimeout(timer);
        signal?.removeEventListener("abort", onAbort);
        pending.delete(id);
      };
      const drop = (err: unknown) => {
        if (!pending.has(id)) return;
        finish();
        w.postMessage({ t: "cancel", id });
        reject(err);
      };
      const onAbort = () => drop(abortError(signal));
      pending.set(id, {
        resolve: (r) => (finish(), resolve(r)),
        reject: (e) => (finish(), reject(e)),
      });
      signal?.addEventListener("abort", onAbort, { once: true });
      // the clock starts here: the engine is booted and has the request
      timer = setTimeout(() => drop(timeoutError()), timeoutMs ?? timeoutDefault);
      const msg: ToWorker = { t: "request", id, method: req.method, path: req.path, query: req.query, body: req.body };
      w.postMessage(msg, req.body ? [req.body.buffer as ArrayBuffer] : []);
    });
  }

  return { fetch: fetchViaEngine, store };
}

export type { EngineSnapshot };
