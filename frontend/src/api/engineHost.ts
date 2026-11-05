// The message loop of the engine worker, independent of `self`: engine.worker.ts connects it to the worker scope, a Node
// test connects it to an in-process fake worker. Requests run one at a time; between two of them the loop yields so a
// "cancel" for a queued request is seen before it starts.
import type { Engine } from "./engineCore";
import type { FromWorker, ToWorker } from "./engineProtocol";

type Request = Extract<ToWorker, { t: "request" }>;
const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

export function createEngineHost(engine: Engine, post: (message: FromWorker, transfer?: Transferable[]) => void) {
  let queue: Request[] = [];
  let running = false;

  const booted: Promise<boolean> = engine.boot().then(
    () => {
      post({ t: "ready" });
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
      if (m.t === "request") {
        queue.push(m);
        void pump();
      } else if (m.t === "cancel") {
        queue = queue.filter((j) => j.id !== m.id);
      }
    },
  };
}
