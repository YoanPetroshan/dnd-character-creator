/** Save a value after it has been quiet for `delayMs`, and at once on `flush` (what `pagehide` / `visibilitychange` call,
 *  so the last keystrokes are never lost). Only the latest scheduled value is saved. */
export interface DebouncedSaver<T> {
  schedule(value: T): void;
  /** Save the pending value now (nothing pending: nothing happens). */
  flush(): void;
  /** Forget the pending value. */
  cancel(): void;
}

export function createDebouncedSaver<T>(save: (value: T) => void, delayMs: number): DebouncedSaver<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let pending: { value: T } | null = null;
  const run = () => {
    clearTimeout(timer);
    timer = undefined;
    const p = pending;
    pending = null;
    if (p) save(p.value);
  };
  return {
    schedule(value) {
      pending = { value };
      clearTimeout(timer);
      timer = setTimeout(run, delayMs);
    },
    flush: run,
    cancel() {
      clearTimeout(timer);
      timer = undefined;
      pending = null;
    },
  };
}
