// The worker's message loop with a fake engine: boot messages, lazy / eager PDF stack, one job at a time, cancel.
import { describe, expect, it } from "vitest";
import type { Engine } from "./engineCore";
import { createEngineHost } from "./engineHost";
import type { FromWorker } from "./engineProtocol";

const tick = () => new Promise((r) => setTimeout(r, 5));

function fake(opts: { bootFails?: boolean; pdfFails?: boolean } = {}) {
  const log: string[] = [];
  const engine: Engine = {
    boot: async () => {
      log.push("boot");
      if (opts.bootFails) throw new Error("no wasm");
    },
    preparePdf: async () => {
      log.push("preparePdf");
      if (opts.pdfFails) throw new Error("wheel missing");
    },
    call: (method, path) => {
      log.push(`call ${method} ${path}`);
      return { status: 200, contentType: "application/json", headers: {}, body: new Uint8Array([123, 125]) };
    },
  };
  const out: FromWorker[] = [];
  return { engine, log, out, post: (m: FromWorker) => void out.push(m) };
}
const req = (id: number, path = "/api/x") => ({ t: "request" as const, id, method: "GET", path, query: "", body: null });

describe("engine host", () => {
  it("boots, says ready, and does not touch the PDF stack (lazy is the default)", async () => {
    const f = fake();
    createEngineHost(f.engine, f.post);
    await tick();
    expect(f.out).toEqual([{ t: "ready" }]);
    expect(f.log).toEqual(["boot"]);
  });

  it("a failed boot is reported once and requests are never answered", async () => {
    const f = fake({ bootFails: true });
    const h = createEngineHost(f.engine, f.post);
    h.onMessage(req(1));
    await tick();
    expect(f.out).toEqual([{ t: "boot-error", message: "no wasm" }]);
  });

  it("answers requests in order with transferable bytes", async () => {
    const f = fake();
    const h = createEngineHost(f.engine, f.post);
    h.onMessage(req(1, "/a"));
    h.onMessage(req(2, "/b"));
    await tick();
    expect(f.log).toEqual(["boot", "call GET /a", "call GET /b"]);
    const replies = f.out.filter((m) => m.t === "response");
    expect(replies.map((m) => (m as { id: number }).id)).toEqual([1, 2]);
  });

  it("a prepare message loads the stack once and answers prepared; the request after it sees it loaded", async () => {
    const f = fake();
    const h = createEngineHost(f.engine, f.post);
    h.onMessage({ t: "prepare", what: "pdf" });
    h.onMessage(req(1, "/api/export/pdf"));
    await tick();
    expect(f.log).toEqual(["boot", "preparePdf", "call GET /api/export/pdf"]);
    expect(f.out.map((m) => m.t)).toEqual(["ready", "prepared", "response"]);
  });

  it("a failed load is reported as prepare-error and the loop goes on", async () => {
    const f = fake({ pdfFails: true });
    const h = createEngineHost(f.engine, f.post);
    h.onMessage({ t: "prepare", what: "pdf" });
    h.onMessage(req(1));
    await tick();
    expect(f.out.map((m) => m.t)).toEqual(["ready", "prepare-error", "response"]);
  });

  it("eager mode starts the load right after boot and announces it", async () => {
    const f = fake();
    createEngineHost(f.engine, f.post, { pdf: "eager" });
    await tick();
    expect(f.out.map((m) => m.t)).toEqual(["ready", "preparing", "prepared"]);
    expect(f.log).toEqual(["boot", "preparePdf"]);
  });

  it("a cancel removes a request that has not started", async () => {
    const f = fake();
    const h = createEngineHost(f.engine, f.post);
    h.onMessage(req(1, "/a"));
    h.onMessage(req(2, "/b"));
    h.onMessage({ t: "cancel", id: 2 });
    await tick();
    expect(f.log).toEqual(["boot", "call GET /a"]);
  });
});
