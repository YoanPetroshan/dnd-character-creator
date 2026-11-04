import { createContext, useContext, type ReactNode } from "react";
import { useDraft } from "./DraftContext";
import { useResolution } from "./useResolution";
import type { Resolution } from "./types";
import type { Msg } from "./logic/messages";

interface ResolutionContextValue {
  resolution: Resolution | null;
  loading: boolean;
  error: Msg | null;
  retry: () => void;
}

const ResolutionContext = createContext<ResolutionContextValue | null>(null);

export function ResolutionProvider({ children }: { children: ReactNode }) {
  const { draft } = useDraft();
  const state = useResolution(draft);
  return <ResolutionContext.Provider value={state}>{children}</ResolutionContext.Provider>;
}

export function useResolutionContext(): ResolutionContextValue {
  const ctx = useContext(ResolutionContext);
  if (!ctx) throw new Error("useResolutionContext must be used within a ResolutionProvider");
  return ctx;
}
