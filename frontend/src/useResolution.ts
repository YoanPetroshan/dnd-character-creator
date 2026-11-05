import { useEffect, useRef, useState, useCallback } from "react";
import { apiFetch, isTimeoutError } from "./api/transport";
import { useLang } from "./LanguageContext";
import { withLang } from "./logic/langQuery";
import type { Draft, Resolution } from "./types";
import { httpErrorMessage } from "./httpErrors";
import { MsgError, msg, toMsg, type Msg } from "./logic/messages";

const DEBOUNCE_MS = 150;
const REQUEST_TIMEOUT_MS = 30_000;

interface ResolutionState {
  resolution: Resolution | null;
  loading: boolean;
  error: Msg | null;
}

export function useResolution(draft: Draft): ResolutionState & { retry: () => void } {
  const [state, setState] = useState<ResolutionState>({
    resolution: null,
    loading: false,
    error: null,
  });
  const [retryNonce, setRetryNonce] = useState(0);
  const { lang } = useLang();
  const requestId = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const id = ++requestId.current;
      setState((s) => ({ ...s, loading: true, error: null }));
      apiFetch(withLang("/api/resolve", lang), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
        signal: controller.signal,
        // counted from the moment the request is sent (with the in-browser engine: after it has booted)
        timeoutMs: REQUEST_TIMEOUT_MS,
      })
        .then(async (resp) => {
          if (!resp.ok) {
            let detail = "";
            try {
              detail = ((await resp.json()) as { error?: string }).error ?? "";
            } catch {
              // non-JSON error body
            }
            throw new MsgError(httpErrorMessage(resp.status, detail));
          }
          return (await resp.json()) as Resolution;
        })
        .then((resolution) => {
          if (id !== requestId.current) return; // a newer request already won
          setState({ resolution, loading: false, error: null });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current) return;
          // A superseded request is aborted by the cleanup below; only a
          // timeout reaches here with the current id still set.
          let message: Msg;
          if (isTimeoutError(err)) message = msg("net.timeout");
          else if (err instanceof TypeError) message = msg("net.offline");
          else message = toMsg(err);
          // keep the last good resolution: only the error line changes
          setState((s) => ({ ...s, loading: false, error: message }));
        });
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
      // an aborted in-flight request must not leave a stuck "loading"
      requestId.current++;
    };
  }, [draft, retryNonce, lang]);

  const retry = useCallback(() => setRetryNonce((n) => n + 1), []);

  return { ...state, retry };
}
