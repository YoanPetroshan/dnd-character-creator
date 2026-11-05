// The message loop of the engine worker, independent of `self`: engine.worker.ts connects it to the worker scope, a Node
// test connects it to an in-process fake worker. Requests run one at a time; between two of them the loop yields so a
// "cancel" for a queued request is seen before it starts.
import type { Engine } from "./engineCore";
import type { FromWorker, ToWorker } from "./engineProtocol";

type Job = Extract<ToWorker, { t: "request" | "prepare" }>;
const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

export interface HostOptions {
  /** "eager": start loading the PDF stack as soon as the engine is ready (the files are precached by then, O4). */
  pdf?: "lazy" | "eager";
}

export function createEngineHost(engine: Engine, post: (message: FromWorker, transfer?: Transferable[]) => void, options: HostOptions = {}) {
  let queue: Job[] = [];
  let running = false;

  const booted: Promise<boolean> = engine.boot().then(
    () => {
      post({ t: "ready" });
      if (options.pdf === "eager") {
        queue.push({ t: "prepare", what: "pdf" });
        post({ t: "preparing", what: "pdf" });
        void pump();
      }
      return true;
    },
    (e: unknown) => {
      post({ t: "boot-error", message: errorText(e) });
      return false;
    },
  );

  async function pump(): Promise<void> {
    if (running) return;
    running = true;
    try {
      if (!(await booted)) return;
      while (queue.length) {
        const job = queue.shift()!;
        if (job.t === "prepare") {
          try {
            await engine.preparePdf();
            post({ t: "prepared", what: job.what });
          } catch (e) {
            post({ t: "prepare-error", what: job.what, message: errorText(e) });
          }
          continue;
        }
        try {
          const r = engine.call(job.method, job.path, job.query, job.body);
          const body = r.body.buffer as ArrayBuffer;
          post({ t: "response", id: job.id, status: r.status, contentType: r.contentType, headers: r.headers, body }, [body]);
        } catch (e) {
          post({ t: "failure", id: job.id, message: errorText(e) });
        }
        await new Promise((resolve) => setTimeout(resolve, 0)); // let queued "cancel" messages in
      }
    } finally {
      running = false;
    }
  }

  return {
    booted,
    onMessage(m: ToWorker): void {
      if (m.t === "request" || m.t === "prepare") {
        queue.push(m);
        void pump();
      } else if (m.t === "cancel") {
        queue = queue.filter((j) => j.t !== "request" || j.id !== m.id);
      }
    },
  };
}
