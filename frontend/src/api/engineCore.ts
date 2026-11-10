// The engine inside Pyodide, independent of where it runs: the worker (engine.worker.ts) and a Node test use the same
// code with different `EngineIO`. It boots Pyodide, mounts app.zip, installs the bundled wheels and answers
// service.handle(method, path, query, body) (server/service.py, the same module the Flask server calls).

import { bodyProblem } from "./bodyGuard";

// Pyodide's API surface used here (the package has no bundled typings in this project).
/* eslint-disable @typescript-eslint/no-explicit-any */
export type PyodideApi = any;

export interface EngineIO {
  /** Start the Pyodide runtime (core files from /pyodide/ in the browser, from the pack directory in Node). */
  loadPyodide(): Promise<PyodideApi>;
  /** The bytes of a pack file (app.zip, fonts.zip). */
  readBytes(name: string): Promise<Uint8Array>;
  /** What `loadPackage` takes for a pack file: a URL in the browser, a path in Node. */
  assetRef(name: string): string;
}

export interface EngineReply {
  status: number;
  contentType: string;
  headers: Record<string, string>;
  body: Uint8Array;
}

// The wheels of the PDF stack: pillow and fonttools come from the Pyodide distribution (pyodide-lock.json), the two
// pure-Python ones are the pinned wheels of scripts/offline_manifest.json.
export const PDF_WHEELS = ["pillow", "fonttools", "defusedxml-0.7.1-py2.py3-none-any.whl", "fpdf2-2.8.8-py3-none-any.whl"] as const;

const BRIDGE = `
import sys
for _p in ("/app/server", "/app"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import service

def engine_call(method, path, query, body, problem):
    # VF7.6: problem ("too-large" / "too-deep") is the verdict of the JavaScript body guard (bodyGuard.ts); the body itself
    # is then not copied in. The service answers it like Flask: only the two draft routes, after their lang check.
    data = service.body_problem(problem) if problem else (None if body is None else body.to_bytes())
    return service.handle(method, path, query, data)
`;

const quiet = { messageCallback: () => undefined, errorCallback: () => undefined };

export interface Engine {
  boot(): Promise<void>;
  /** Load the PDF stack (wheels + fonts.zip) once; later calls return the same promise. */
  preparePdf(): Promise<void>;
  call(method: string, path: string, query: string, body: Uint8Array | null): EngineReply;
}

export function createEngine(io: EngineIO): Engine {
  let py: PyodideApi;
  let call: any;
  let pdf: Promise<void> | null = null;

  async function loadPdfStack(): Promise<void> {
    py.unpackArchive(await io.readBytes("fonts.zip"), "zip", { extractDir: "/app" });
    await py.loadPackage(PDF_WHEELS.map((w) => (w.endsWith(".whl") ? io.assetRef(w) : w)), quiet);
  }

  return {
    async boot() {
      py = await io.loadPyodide();
      await py.loadPackage(["pyyaml"], quiet);
      py.unpackArchive(await io.readBytes("app.zip"), "zip", { extractDir: "/app" });
      // `import service` needs only the engine, the catalog and pyyaml: pdf_export is imported when the first PDF is
      // rendered, after preparePdf().
      py.runPython(BRIDGE);
      call = py.globals.get("engine_call");
    },
    preparePdf() {
      // a failed load may be retried: the promise is dropped on failure
      pdf ??= loadPdfStack().catch((e) => {
        pdf = null;
        throw e;
      });
      return pdf;
    },
    call(method, path, query, body) {
      const problem = bodyProblem(body);
      const raw = call(method, path, query, problem ? undefined : (body ?? undefined), problem ?? undefined);
      try {
        const [status, contentType, headers, data] = raw.toJs({ dict_converter: Object.fromEntries });
        // `data` may view the WebAssembly heap: copy it out before anything else runs.
        return { status, contentType, headers, body: new Uint8Array(data) };
      } finally {
        raw.destroy();
      }
    },
  };
}
