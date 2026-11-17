import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createDebouncedSaver } from "./debouncedSave";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("createDebouncedSaver (FE-07)", () => {
  it("a run of keystrokes is one save, of the last value, after the quiet time", () => {
    const save = vi.fn();
    const s = createDebouncedSaver<string>(save, 400);
    for (const v of ["a", "ab", "abc"]) {
      s.schedule(v);
      vi.advanceTimersByTime(100);
    }
    expect(save).not.toHaveBeenCalled();
    vi.advanceTimersByTime(400);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith("abc");
  });

  it("flush saves the pending value at once, and only once", () => {
    const save = vi.fn();
    const s = createDebouncedSaver<string>(save, 400);
    s.schedule("x");
    s.flush();
    expect(save).toHaveBeenCalledWith("x");
    s.flush();
    vi.advanceTimersByTime(1000);
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("flush with nothing pending does nothing", () => {
    const save = vi.fn();
    createDebouncedSaver<string>(save, 400).flush();
    expect(save).not.toHaveBeenCalled();
  });

  it("a quick pagehide / visibilitychange after the last key loses nothing", () => {
    const save = vi.fn();
    const s = createDebouncedSaver<string>(save, 400);
    s.schedule("one");
    vi.advanceTimersByTime(50);
    s.schedule("two");
    s.flush(); // what pagehide does
    expect(save).toHaveBeenLastCalledWith("two");
    vi.advanceTimersByTime(1000);
    expect(save).toHaveBeenCalledTimes(1);
  });

  it("cancel drops the pending value", () => {
    const save = vi.fn();
    const s = createDebouncedSaver<string>(save, 400);
    s.schedule("x");
    s.cancel();
    vi.advanceTimersByTime(1000);
    expect(save).not.toHaveBeenCalled();
  });

  it("a save after a flush starts a new quiet time", () => {
    const save = vi.fn();
    const s = createDebouncedSaver<string>(save, 400);
    s.schedule("a");
    s.flush();
    s.schedule("b");
    vi.advanceTimersByTime(399);
    expect(save).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(2);
    expect(save).toHaveBeenLastCalledWith("b");
  });
});
