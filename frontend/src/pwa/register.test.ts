import { describe, expect, it, vi } from "vitest";
import { createPwa, requestPersistence, type ContainerLike, type PwaDeps, type RegistrationLike, type StorageManagerLike, type WorkerLike } from "./register";

/** A fake worker whose state the test moves by hand. */
function fakeWorker(state = "installing") {
  const listeners: (() => void)[] = [];
  const posted: unknown[] = [];
  const w = {
    state,
    addEventListener: (_t: "statechange", l: () => void) => void listeners.push(l),
    postMessage: (m: unknown) => void posted.push(m),
    move(next: string) {
      w.state = next;
      listeners.forEach((l) => l());
    },
    posted,
  };
  return w;
}
type FakeWorker = ReturnType<typeof fakeWorker>;

function fakeRegistration(init: Partial<Record<"installing" | "waiting" | "active", FakeWorker | null>> = {}) {
  const updatefound: (() => void)[] = [];
  const reg = {
    installing: init.installing ?? null,
    waiting: init.waiting ?? null,
    active: init.active ?? null,
    addEventListener: (_t: "updatefound", l: () => void) => void updatefound.push(l),
    update: vi.fn(async () => undefined),
    fire: () => updatefound.forEach((l) => l()),
  } as RegistrationLike & { installing: WorkerLike | null; waiting: WorkerLike | null; active: WorkerLike | null; fire(): void; update: ReturnType<typeof vi.fn> };
  return reg;
}

function fakeContainer(reg: RegistrationLike | Error, controller: unknown = null) {
  const changes: (() => void)[] = [];
  const messages: ((e: { data?: unknown; source?: unknown }) => void)[] = [];
  const c = {
    controller,
    register: vi.fn(async () => {
      if (reg instanceof Error) throw reg;
      return reg;
    }),
    addEventListener: (t: string, l: (e: never) => void) => void (t === "message" ? messages : changes).push(l as never),
    claim: () => changes.forEach((l) => l()),
    say: (data: unknown, source?: unknown) => messages.forEach((l) => l({ data, source })),
  };
  return c as unknown as ContainerLike & { register: ReturnType<typeof vi.fn>; claim(): void; say(data: unknown, source?: unknown): void };
}

const deps = (container: ContainerLike | undefined, extra: { storage?: StorageManagerLike; reload?: () => void } & Partial<PwaDeps> = {}): PwaDeps => ({
  ...extra,
  container,
  swUrl: "/dnd-character-creator/sw.js",
  scope: "/dnd-character-creator/",
  reload: extra.reload ?? (() => undefined),
  storage: extra.storage,
});

describe("createPwa", () => {
  it("is unsupported without a service worker container and never registers", async () => {
    const pwa = createPwa(deps(undefined));
    expect(pwa.get().phase).toBe("unsupported");
    await pwa.start();
    expect(pwa.get().phase).toBe("unsupported");
  });

  it("registers at the given URL and scope, bypassing the HTTP cache for the worker file", async () => {
    const container = fakeContainer(fakeRegistration({ active: fakeWorker("activated") }), {});
    await createPwa(deps(container)).start();
    expect(container.register).toHaveBeenCalledWith("/dnd-character-creator/sw.js", { scope: "/dnd-character-creator/", updateViaCache: "none" });
  });

  it("first visit: installing, then offline-ready with justReady when the worker activates", async () => {
    const installing = fakeWorker("installing");
    const reg = fakeRegistration({ installing });
    const pwa = createPwa(deps(fakeContainer(reg, null), { storage: { persisted: async () => false, persist: async () => true } }));
    await pwa.start();
    expect(pwa.get()).toMatchObject({ phase: "installing", justReady: false });
    installing.move("installed"); // no active worker yet and no controller: no update prompt
    expect(pwa.get().phase).toBe("installing");
    reg.active = installing;
    installing.move("activated");
    expect(pwa.get()).toMatchObject({ phase: "offline-ready", justReady: true });
    await new Promise((r) => setTimeout(r, 0));
    expect(pwa.get().persisted).toBe("granted");
  });

  it("a later visit with an active worker is offline-ready without the 'just ready' flag", async () => {
    const pwa = createPwa(deps(fakeContainer(fakeRegistration({ active: fakeWorker("activated") }), {})));
    await pwa.start();
    expect(pwa.get()).toMatchObject({ phase: "offline-ready", justReady: false });
  });

  it("an update installing behind an active worker keeps offline-ready, then asks the user", async () => {
    const reg = fakeRegistration({ active: fakeWorker("activated") });
    const pwa = createPwa(deps(fakeContainer(reg, {})));
    await pwa.start();
    const next = fakeWorker("installing");
    reg.installing = next;
    reg.fire();
    expect(pwa.get().phase).toBe("offline-ready");
    reg.installing = null;
    reg.waiting = next;
    next.move("installed");
    expect(pwa.get().phase).toBe("update-available");
  });

  it("applyUpdate asks the waiting worker to take over and reloads only after the controller changed", async () => {
    const waiting = fakeWorker("installed");
    const reg = fakeRegistration({ active: fakeWorker("activated"), waiting });
    const reload = vi.fn();
    const container = fakeContainer(reg, {});
    const pwa = createPwa(deps(container, { reload }));
    await pwa.start();
    expect(pwa.get().phase).toBe("update-available");
    container.claim(); // not asked for: no reload
    expect(reload).not.toHaveBeenCalled();
    pwa.applyUpdate();
    expect(waiting.posted).toEqual([{ type: "SKIP_WAITING" }]);
    expect(reload).not.toHaveBeenCalled();
    container.claim();
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("applyUpdate with nothing waiting does nothing", async () => {
    const container = fakeContainer(fakeRegistration({ active: fakeWorker("activated") }), {});
    const reload = vi.fn();
    const pwa = createPwa(deps(container, { reload }));
    await pwa.start();
    pwa.applyUpdate();
    container.claim();
    expect(reload).not.toHaveBeenCalled();
  });

  it("a failed registration is the error phase, not a crash", async () => {
    const pwa = createPwa(deps(fakeContainer(new Error("SecurityError"))));
    await pwa.start();
    expect(pwa.get().phase).toBe("error");
  });

  it("start registers once; checkForUpdate asks the registration and swallows a network failure", async () => {
    const reg = fakeRegistration({ active: fakeWorker("activated") });
    const container = fakeContainer(reg, {});
    const pwa = createPwa(deps(container));
    await Promise.all([pwa.start(), pwa.start()]);
    expect(container.register).toHaveBeenCalledTimes(1);
    await pwa.checkForUpdate();
    expect(reg.update).toHaveBeenCalledTimes(1);
    reg.update.mockRejectedValueOnce(new TypeError("offline"));
    await expect(pwa.checkForUpdate()).resolves.toBeUndefined();
  });

  it("notifies subscribers once per change and stops after unsubscribe", async () => {
    const installing = fakeWorker("installing");
    const reg = fakeRegistration({ installing });
    const pwa = createPwa(deps(fakeContainer(reg, null)));
    const seen: string[] = [];
    const off = pwa.subscribe(() => seen.push(pwa.get().phase));
    await pwa.start();
    off();
    reg.active = installing;
    installing.move("activated");
    expect(seen).toEqual(["installing"]);
  });
});

describe("automatic update", () => {
  const SAME = { type: "VERSION", schema: 3 };
  function setup(opts: { atRisk?: boolean; allowed?: boolean; clock?: { t: number } } = {}) {
    const waiting = fakeWorker("installed");
    const reg = fakeRegistration({ active: fakeWorker("activated"), waiting });
    const container = fakeContainer(reg, {});
    const reload = vi.fn();
    const clock = opts.clock ?? { t: 0 };
    const mark = vi.fn();
    const pwa = createPwa(
      deps(container, {
        reload,
        schema: 3,
        dataAtRisk: () => !!opts.atRisk,
        autoApply: { windowMs: 1000, now: () => clock.t, allowed: () => opts.allowed ?? true, mark },
      }),
    );
    return { waiting, reg, container, reload, clock, mark, pwa };
  }

  it("asks the waiting worker for its schema; the same schema is applied by itself right after the app opened", async () => {
    const { waiting, container, pwa, mark, reload } = setup();
    await pwa.start();
    expect(waiting.posted).toEqual([{ type: "GET_VERSION" }]);
    expect(pwa.get().phase).toBe("update-available");
    container.say(SAME, waiting);
    expect(mark).toHaveBeenCalledTimes(1);
    expect(waiting.posted).toEqual([{ type: "GET_VERSION" }, { type: "SKIP_WAITING" }]);
    container.claim();
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("a different schema, or one that is not stated, asks for a backup and never applies by itself", async () => {
    for (const data of [{ type: "VERSION", schema: 4 }, { type: "VERSION" }]) {
      const { waiting, container, pwa, reload } = setup();
      await pwa.start();
      container.say(data, waiting);
      expect(pwa.get().phase).toBe("update-needs-backup");
      expect(waiting.posted).toEqual([{ type: "GET_VERSION" }]);
      pwa.applyUpdate(); // the person pressed the button after the download
      container.claim();
      expect(reload).toHaveBeenCalledTimes(1);
    }
  });

  it("a draft that failed to save blocks the silent update even with the same schema", async () => {
    const { waiting, container, pwa } = setup({ atRisk: true });
    await pwa.start();
    container.say(SAME, waiting);
    expect(pwa.get().phase).toBe("update-needs-backup");
    expect(waiting.posted).not.toContainEqual({ type: "SKIP_WAITING" });
  });

  it("outside the window after opening the update waits (manual button) and is applied when the app is shown again", async () => {
    const clock = { t: 0 };
    const { waiting, container, pwa, reg } = setup({ clock });
    await pwa.start();
    clock.t = 5000; // the person has been using the app for a while
    container.say(SAME, waiting);
    expect(pwa.get().phase).toBe("update-available");
    expect(waiting.posted).not.toContainEqual({ type: "SKIP_WAITING" });
    await pwa.checkForUpdate(); // shown again: armed again
    expect(reg.update).toHaveBeenCalledTimes(1);
    expect(waiting.posted).toContainEqual({ type: "SKIP_WAITING" });
  });

  it("the reload guard (allowed() false) stops a second automatic update", async () => {
    const { waiting, container, pwa } = setup({ allowed: false });
    await pwa.start();
    container.say(SAME, waiting);
    expect(waiting.posted).not.toContainEqual({ type: "SKIP_WAITING" });
    expect(pwa.get().phase).toBe("update-available");
  });

  it("ignores answers from another worker and messages of other kinds", async () => {
    const { waiting, container, pwa } = setup();
    await pwa.start();
    container.say(SAME, fakeWorker("activated"));
    container.say({ type: "SOMETHING", schema: 3 }, waiting);
    container.say(null, waiting);
    expect(waiting.posted).toEqual([{ type: "GET_VERSION" }]);
  });

  it("without a schema or autoApply nothing is asked and nothing is applied by itself", async () => {
    const waiting = fakeWorker("installed");
    const container = fakeContainer(fakeRegistration({ active: fakeWorker("activated"), waiting }), {});
    const pwa = createPwa(deps(container));
    await pwa.start();
    expect(waiting.posted).toEqual([]);
    expect(pwa.get().phase).toBe("update-available");
  });
});

describe("requestPersistence", () => {
  it("is unsupported without the API", async () => {
    expect(await requestPersistence(undefined)).toBe("unsupported");
    expect(await requestPersistence({})).toBe("unsupported");
  });
  it("is granted when already persisted, without asking again", async () => {
    const persist = vi.fn(async () => true);
    expect(await requestPersistence({ persisted: async () => true, persist })).toBe("granted");
    expect(persist).not.toHaveBeenCalled();
  });
  it("asks once and reports granted or denied", async () => {
    expect(await requestPersistence({ persisted: async () => false, persist: async () => true })).toBe("granted");
    expect(await requestPersistence({ persist: async () => false })).toBe("denied");
  });
  it("never throws", async () => {
    expect(
      await requestPersistence({
        persist: async () => {
          throw new Error("blocked");
        },
      }),
    ).toBe("unknown");
  });
});
