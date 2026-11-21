import { describe, expect, it, vi } from "vitest";
import type { EngineSnapshot } from "./engineProtocol";
import { whenEngineSettled } from "./whenEngineSettled";

function store(engine: EngineSnapshot["engine"]) {
  let snap = { engine, pdf: "idle" } as EngineSnapshot;
  const listeners = new Set<() => void>();
  return {
    snapshot: () => snap,
    subscribe: (l: () => void) => (listeners.add(l), () => listeners.delete(l)),
    set(next: EngineSnapshot["engine"]) {
      snap = { ...snap, engine: next };
      listeners.forEach((l) => l());
    },
    count: () => listeners.size,
  };
}

describe("whenEngineSettled", () => {
  it("resolves at once when the engine is not booting", async () => {
    const s = store("ready");
    await expect(whenEngineSettled(s.snapshot, s.subscribe, 1000)).resolves.toBeUndefined();
  });

  it("waits while the engine is starting and resolves when it is ready", async () => {
    const s = store("starting");
    let done = false;
    const p = whenEngineSettled(s.snapshot, s.subscribe, 60_000).then(() => (done = true));
    await Promise.resolve();
    expect(done).toBe(false);
    s.set("ready");
    await p;
    expect(done).toBe(true);
    expect(s.count()).toBe(0); // unsubscribed
  });

  it("a failed engine settles too (the offline copy is still worth trying)", async () => {
    const s = store("starting");
    const p = whenEngineSettled(s.snapshot, s.subscribe, 60_000);
    s.set("fallback");
    await expect(p).resolves.toBeUndefined();
  });

  it("gives up after the timeout", async () => {
    vi.useFakeTimers();
    const s = store("starting");
    const p = whenEngineSettled(s.snapshot, s.subscribe, 5000);
    vi.advanceTimersByTime(5000);
    await expect(p).resolves.toBeUndefined();
    expect(s.count()).toBe(0);
    vi.useRealTimers();
  });
});
