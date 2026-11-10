// Service worker of the offline build (hand-written; the build fills in the manifest token below, see precache.mjs).
//
// What it does, and nothing more:
//   install   download every file of the manifest (the app shell, the whole offline pack incl. the PDF stack and fonts) into
//             one cache named after the manifest version. Files an older cache already holds under the same revision are
//             copied locally (a new version re-downloads only what changed, not the 9.6 MB wasm). One failed file fails
//             the install (the browser retries later); the files already stored are kept so a retry resumes.
//   waiting   a new version never takes over by itself: the page shows "update available" and sends SKIP_WAITING.
//   activate  delete every older `dnd-builder-precache-*` cache, claim the open pages.
//   fetch     same-origin GET inside the scope: answered from the cache when the file is in the manifest; a page
//             navigation inside the scope gets index.html (single-page app). Everything else (the /api calls of a
//             server build, other origins, non-GET, Range) is left to the network.
// All URLs are relative to the scope (self.registration.scope), so the app works under any sub-path.
"use strict";

const MANIFEST = __PRECACHE_MANIFEST__;
const PREFIX = "dnd-builder-precache-";
const CACHE = PREFIX + MANIFEST.version;
const CONCURRENCY = 4;

const absolute = (rel) => new URL(rel, self.registration.scope).href;
const keyOf = (entry) => absolute(entry.url) + "?__v=" + entry.revision;

let keysByPath = null;
function lookup() {
  if (!keysByPath) {
    keysByPath = new Map();
    for (const e of MANIFEST.entries) keysByPath.set(new URL(e.url, self.registration.scope).pathname, keyOf(e));
  }
  return keysByPath;
}

async function fillCache() {
  const cache = await caches.open(CACHE);
  const older = (await caches.keys()).filter((k) => k.startsWith(PREFIX) && k !== CACHE);
  async function fetchOne(entry) {
    const key = keyOf(entry);
    if (await cache.match(key)) return; // stored by an earlier, interrupted install of this version
    for (const name of older) {
      const hit = await (await caches.open(name)).match(key);
      if (hit) {
        await cache.put(key, hit);
        return;
      }
    }
    // "no-cache": revalidate, so a copy the page itself just downloaded is reused (304) and a stale one is not
    const resp = await fetch(absolute(entry.url), { cache: "no-cache" });
    if (!resp.ok) throw new Error(entry.url + ": HTTP " + resp.status);
    await cache.put(key, resp);
  }
  const queue = MANIFEST.entries.slice();
  const lanes = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
    for (let e = queue.shift(); e; e = queue.shift()) await fetchOne(e);
  });
  await Promise.all(lanes);
}

self.addEventListener("install", (event) => {
  event.waitUntil(fillCache());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const k of await caches.keys()) if (k.startsWith(PREFIX) && k !== CACHE) await caches.delete(k);
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type === "SKIP_WAITING") self.skipWaiting();
  else if (data.type === "GET_VERSION" && event.source) event.source.postMessage({ type: "VERSION", version: MANIFEST.version, files: MANIFEST.entries.length });
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  const scopePath = new URL(self.registration.scope).pathname;
  if (!url.pathname.startsWith(scopePath)) return;
  const table = lookup();
  let key = table.get(url.pathname);
  if (!key && req.mode === "navigate") key = table.get(scopePath + "index.html");
  if (!key) return;
  event.respondWith(
    caches
      .open(CACHE)
      .then((c) => c.match(key))
      .then((hit) => hit || fetch(req)),
  );
});
