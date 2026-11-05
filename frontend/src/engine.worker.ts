// The engine worker (module worker): Pyodide + the Python engine of the offline pack, answering the page's requests
// (api/engineProtocol.ts). Everything comes from same-origin files under /pyodide/ (scripts/build_offline.py): the
// Pyodide runtime, python_stdlib.zip, pyyaml / pillow / fonttools wheels, the bundled fpdf2 / defusedxml wheels,
// app.zip (server/*.py, engine, catalog, data) and fonts.zip. The engine is api/engineCore.ts, the message loop
// api/engineHost.ts; this file only connects them to the worker scope. Booting starts as soon as the worker loads.
import { createEngine, type EngineIO } from "./api/engineCore";
import { createEngineHost } from "./api/engineHost";
import type { FromWorker, ToWorker } from "./api/engineProtocol";

interface Scope {
  postMessage(message: FromWorker, transfer?: Transferable[]): void;
  onmessage: ((event: { data: ToWorker }) => void) | null;
  location: { origin: string };
}
const scope = self as unknown as Scope;

const root = new URL(import.meta.env.BASE_URL + "pyodide/", scope.location.origin).href;

const io: EngineIO = {
  async loadPyodide() {
    const mod = await import(/* @vite-ignore */ root + "pyodide.mjs");
    return mod.loadPyodide({ indexURL: root });
  },
  async readBytes(name) {
    const resp = await fetch(root + name);
    if (!resp.ok) throw new Error(`${name}: HTTP ${resp.status}`);
    return new Uint8Array(await resp.arrayBuffer());
  },
  assetRef: (name) => root + name,
};

const host = createEngineHost(createEngine(io), (message, transfer) => scope.postMessage(message, transfer));
scope.onmessage = (event) => host.onMessage(event.data);
