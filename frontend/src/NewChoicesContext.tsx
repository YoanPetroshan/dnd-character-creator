import { createContext, useContext, useEffect, useMemo, useRef, type ReactNode } from "react";
import { useLibrary } from "./LibraryContext";
import { useResolutionContext } from "./ResolutionContext";
import { newChoiceIds, syncSeen, type SeenTracker } from "./logic/newChoices";

interface NewChoices {
  /** Ids of the pending cards that are new (level-up choices not acknowledged yet), in resolution order. */
  ids: string[];
  has: (id: string) => boolean;
}

const EMPTY: NewChoices = { ids: [], has: () => false };
export const NewChoicesContext = createContext<NewChoices>(EMPTY);

/** Computes the "new" cards of the active character from the resolution and keeps the
 *  character's acknowledged ids in the library. Sits inside ResolutionProvider (which is
 *  remounted per character, so the session tracker never leaks between characters). */
export function NewChoicesProvider({ children }: { children: ReactNode }) {
  const { resolution } = useResolutionContext();
  const { seenChoiceIds, seenBaselined, setSeen } = useLibrary();
  const tracker = useRef<SeenTracker | null>(null);

  // Render-time view: what the stored state will be after this resolution is synced (no flash of
  // cards that are about to be absorbed).
  const view = useMemo(() => {
    if (!resolution) return null;
    return syncSeen({ seen: seenChoiceIds, baselined: seenBaselined }, tracker.current, resolution);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolution, seenChoiceIds, seenBaselined]);

  useEffect(() => {
    if (!resolution || !view) return;
    tracker.current = view.tracker;
    if (view.changed) setSeen(view.state.seen, view.state.baselined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolution]);

  const value = useMemo<NewChoices>(() => {
    if (!resolution || !view) return EMPTY;
    const ids = newChoiceIds(resolution.choices, view.state.seen);
    const set = new Set(ids);
    return { ids, has: (id) => set.has(id) };
  }, [resolution, view]);

  return <NewChoicesContext.Provider value={value}>{children}</NewChoicesContext.Provider>;
}

export function useNewChoices(): NewChoices {
  return useContext(NewChoicesContext);
}
