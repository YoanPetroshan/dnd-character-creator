// Messages between the page (workerTransport.ts) and the engine worker (engine.worker.ts). Plain structured-clone data.

/** Page -> worker. `body` is the request body as bytes (null: no JSON body). */
export type ToWorker =
  | { t: "request"; id: number; method: string; path: string; query: string; body: Uint8Array | null }
  | { t: "cancel"; id: number }
  | { t: "prepare"; what: "pdf" };

/** Worker -> page. */
export type FromWorker =
  | { t: "ready" }
  | { t: "boot-error"; message: string }
  | { t: "response"; id: number; status: number; contentType: string; headers: Record<string, string>; body: ArrayBuffer }
  | { t: "failure"; id: number; message: string }
  | { t: "preparing"; what: "pdf" } // unsolicited: the worker started loading it itself (eager mode)
  | { t: "prepared"; what: "pdf" }
  | { t: "prepare-error"; what: "pdf"; message: string };

/** What the UI may show (useEngineStatus). `engine`: "off" = plain fetch (dev / Flask / no WebAssembly / no pack),
 *  "starting" = the worker is booting Pyodide, "ready" = answering, "fallback" = the worker failed, plain fetch now,
 *  "unavailable" = a serverless build (static host, VITE_SERVERLESS=1) that cannot run the engine (no WebAssembly / Worker,
 *  e.g. iOS Lockdown Mode, the pack is not reachable, or the worker failed): there is no server to fall back to. */
export type EngineState = "off" | "starting" | "ready" | "fallback" | "unavailable";
/** `pdf`: the PDF stack (fpdf2, Pillow, fonttools, fonts) is loaded on the first PDF export (or at boot in eager mode,
 *  see PDF_MODE in engine.worker.ts); `loading` is what the Export page shows as "preparing PDF". */
export type PdfState = "idle" | "loading" | "ready";
export interface EngineSnapshot {
  readonly engine: EngineState;
  readonly pdf: PdfState;
}
