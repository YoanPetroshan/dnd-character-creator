// The service worker (pwa/sw.template.js) run in a vm sandbox with a fake Cache Storage, fetch and event targets.
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { describe, expect, it } from "vitest";
import { renderServiceWorker } from "../../pwa/precache.mjs";

const TEMPLATE = readFileSync(new URL("../../pwa/sw.template.js", import.meta.url), "utf8");
const ORIGIN = "https://example.test";
const SCOPE = `${ORIGIN}/dnd-character-creator/`;

const entries = (revs) => [
  { url: "index.html", revision: revs.index ?? "r1" },
  { url: "assets/app-1.js", revision: revs.app ?? "r2" },
  { url: "pyodide/pyodide.asm.wasm", revision: revs.wasm ?? "r3" },
];
const manifest = (version, revs = {}) => ({ version, totalBytes: 0, entries: entries(revs) });

/** One browser: a shared Cache Storage and network, and any number of worker versions installed into it. */
function browser() {
  const store = new Map(); // cache name -> Map(key -> text)
  const network = new Map(); // absolute url -> text (missing: 404)
  const log = [];
  const caches = {
    async open(name) {
      if (!store.has(name)) store.set(name, new Map());
      const m = store.get(name);
      return {
        async match(key) {
          return m.has(key) ? new Response(m.get(key)) : undefined;
        },
        async put(key, resp) {
          m.set(key, await resp.text());
        },
      };
    },
    async keys() {
      return [...store.keys()];
    },
    async delete(name) {
      return store.delete(name);
    },
  };
  const fetchFn = async (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    log.push({ url, cache: init?.cache });
    return network.has(url) ? new Response(network.get(url)) : new Response("nope", { status: 404 });
  };
  function load(man) {
    const handlers = {};
    const state = { skipped: false, claimed: false };
    const sandbox = {
      URL, Response, Promise, Map, Array, Math, Error,
      caches,
      fetch: fetchFn,
      self: {
        registration: { scope: SCOPE },
        location: { origin: ORIGIN },
        addEventListener: (t, h) => (handlers[t] = h),
        skipWaiting: () => (state.skipped = true),
        clients: { claim: async () => (state.claimed = true) },
      },
    };
    vm.runInNewContext(renderServiceWorker(TEMPLATE, man), sandbox);
    const wait = async (type, ev = {}) => {
      let p;
      handlers[type]({ ...ev, waitUntil: (x) => (p = x) });
      await p;
    };
    const request = (path, { mode = "no-cors", method = "GET", headers = {}, origin = ORIGIN } = {}) => ({
      url: origin + path,
      method,
      mode,
      headers: { has: (h) => h.toLowerCase() in headers },
    });
    const fetchEvent = async (req) => {
      let answered;
      handlers.fetch({ request: req, respondWith: (p) => (answered = p) });
      return answered === undefined ? undefined : await (await answered).text();
    };
    return { handlers, state, install: () => wait("install"), activate: () => wait("activate"), message: (data, source) => handlers.message({ data, source }), request, fetchEvent };
  }
  return { store, network, log, load };
}

function serveAll(b, man, bodies = {}) {
  for (const e of man.entries) b.network.set(SCOPE + e.url, bodies[e.url] ?? `body of ${e.url}`);
}

describe("service worker", () => {
  it("install downloads every manifest file into one versioned cache (revalidating, not trusting the HTTP cache blindly)", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m);
    const sw = b.load(m);
    await sw.install();
    expect([...b.store.keys()]).toEqual(["dnd-builder-precache-v1"]);
    expect(b.store.get("dnd-builder-precache-v1").size).toBe(3);
    expect(b.log.every((l) => l.cache === "no-cache")).toBe(true);
    expect(b.log.map((l) => l.url).sort()).toEqual(m.entries.map((e) => SCOPE + e.url).sort());
  });

  it("a file that fails to download fails the install (the browser retries), and a retry resumes without refetching stored files", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m);
    b.network.delete(SCOPE + "pyodide/pyodide.asm.wasm");
    const sw = b.load(m);
    await expect(sw.install()).rejects.toThrow(/HTTP 404/);
    b.network.set(SCOPE + "pyodide/pyodide.asm.wasm", "wasm");
    b.log.length = 0;
    await sw.install();
    expect(b.store.get("dnd-builder-precache-v1").size).toBe(3);
    expect(b.log.length).toBeLessThan(3); // the files stored by the first attempt are not downloaded again
  });

  it("an update copies unchanged files from the old cache and downloads only what changed", async () => {
    const b = browser();
    const m1 = manifest("v1");
    serveAll(b, m1);
    await b.load(m1).install();
    const m2 = manifest("v2", { app: "r2b" }); // only the app bundle changed
    b.network.set(SCOPE + "assets/app-1.js", "new app");
    b.log.length = 0;
    await b.load(m2).install();
    expect(b.log.map((l) => l.url)).toEqual([SCOPE + "assets/app-1.js"]);
    expect(b.store.get("dnd-builder-precache-v2").size).toBe(3);
  });

  it("activate deletes older precache caches (and only those) and claims the pages", async () => {
    const b = browser();
    const m1 = manifest("v1");
    serveAll(b, m1);
    await b.load(m1).install();
    b.store.set("some-other-cache", new Map());
    const m2 = manifest("v2");
    const sw = b.load(m2);
    await sw.install();
    await sw.activate();
    expect([...b.store.keys()].sort()).toEqual(["dnd-builder-precache-v2", "some-other-cache"]);
    expect(sw.state.claimed).toBe(true);
  });

  it("serves precached files from the cache, with no network", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m, { "pyodide/pyodide.asm.wasm": "WASM" });
    const sw = b.load(m);
    await sw.install();
    b.network.clear();
    b.log.length = 0;
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/pyodide/pyodide.asm.wasm"))).toBe("WASM");
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/app-1.js?x=1"))).toBe("body of assets/app-1.js");
    expect(b.log).toEqual([]);
  });

  it("answers any navigation inside the scope with index.html (single-page app), also offline", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m, { "index.html": "SHELL" });
    const sw = b.load(m);
    await sw.install();
    b.network.clear();
    for (const path of ["/dnd-character-creator/", "/dnd-character-creator/sheet", "/dnd-character-creator/class/deep"]) {
      expect(await sw.fetchEvent(sw.request(path, { mode: "navigate" }))).toBe("SHELL");
    }
  });

  it("leaves everything else to the network: /api, other origins, other paths, POST, Range, unknown files", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m);
    const sw = b.load(m);
    await sw.install();
    expect(await sw.fetchEvent(sw.request("/api/health"))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/api/health"))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/other.js"))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/other-app/", { mode: "navigate" }))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/app-1.js", { origin: "https://cdn.test" }))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/app-1.js", { method: "POST" }))).toBeUndefined();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/app-1.js", { headers: { range: "bytes=0-9" } }))).toBeUndefined();
  });

  it("a new version waits: it does not skip waiting by itself, only on the page's SKIP_WAITING message", async () => {
    const b = browser();
    const m = manifest("v1");
    serveAll(b, m);
    const sw = b.load(m);
    await sw.install();
    expect(sw.state.skipped).toBe(false);
    sw.message({ type: "SKIP_WAITING" });
    expect(sw.state.skipped).toBe(true);
  });

  it("GET_VERSION answers the sender with the cache version", async () => {
    const b = browser();
    const m = manifest("v9");
    const sw = b.load(m);
    const sent = [];
    sw.message({ type: "GET_VERSION" }, { postMessage: (x) => sent.push(x) });
    expect(sent).toEqual([{ type: "VERSION", version: "v9", files: 3 }]);
  });

  it("works under a different sub-path (the scope decides every URL)", async () => {
    const b = browser();
    const m = manifest("v1");
    for (const e of m.entries) b.network.set(`${ORIGIN}/dnd-character-creator/${e.url}`, "x");
    const sw = b.load(m);
    await sw.install();
    expect(await sw.fetchEvent(sw.request("/dnd-character-creator/assets/app-1.js"))).toBe("x");
    expect(await sw.fetchEvent(sw.request("/assets/app-1.js"))).toBeUndefined(); // the domain root is outside the scope
  });
});
