import { useEffect, useRef, useState, useCallback } from "react";
import type { Draft, Resolution } from "./types";

const DEBOUNCE_MS = 150;

interface ResolutionState {
  resolution: Resolution | null;
  loading: boolean;
  error: string | null;
}

export function useResolution(draft: Draft): ResolutionState & { retry: () => void } {
  const [state, setState] = useState<ResolutionState>({
    resolution: null,
    loading: false,
    error: null,
  });
  const [retryNonce, setRetryNonce] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      fetch("/api/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      })
        .then((resp) => {
          if (!resp.ok) throw new Error(`resolve failed: ${resp.status}`);
          return resp.json() as Promise<Resolution>;
        })
        .then((resolution) => {
          if (id !== requestId.current) return; // a newer request already won
          setState({ resolution, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current) return;
          const message = err instanceof Error ? err.message : String(err);
          setState((s) => ({ ...s, loading: false, error: message }));
        });
    }, DEBOUNCE_MS);

    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [draft, retryNonce]);

  const retry = useCallback(() => setRetryNonce((n) => n + 1), []);

  return { ...state, retry };
}
