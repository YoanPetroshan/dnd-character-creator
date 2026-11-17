import { createContext, useContext, useReducer, useEffect, useMemo, useRef, useState, type Dispatch, type ReactNode } from "react";
import type { Draft } from "./types";
import { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, reducer, totalLevel, type Action } from "./logic/draft";
import { useLibrary } from "./LibraryContext";
import { createDebouncedSaver } from "./logic/debouncedSave";
import type { Msg } from "./logic/messages";

// Re-exported so existing imports from "./DraftContext" keep working.
export { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, totalLevel };

interface DraftContextValue {
  /** The ACTIVE character's draft. Every page works with this one only. */
  draft: Draft;
  dispatch: Dispatch<Action>;
  /** One-off messages about the boot-time load (unreadable stored data). */
  notices: Msg[];
  dismissNotice: () => void;
  /** Raw text of an unreadable stored draft whose backup write failed; offered for download. */
  unsavedRaw: string | null;
  /** The last write to localStorage failed (quota, private mode). */
  storageFailed: boolean;
}

const DraftContext = createContext<DraftContextValue | null>(null);

/** Milliseconds of quiet after the last change before the draft is written to storage (FE-07). */
const SAVE_DELAY_MS = 400;

/** Holds the active character's draft in a reducer and saves it into the character library
 *  after each change. Switching characters remounts it (key = active id), so the reducer
 *  restarts from the newly active character's stored draft. */
export function DraftProvider({ children }: { children: ReactNode }) {
  const lib = useLibrary();
  return (
    <ActiveDraft key={lib.activeId} activeId={lib.activeId} initial={lib.activeDraft}>
      {children}
    </ActiveDraft>
  );
}

function ActiveDraft({ activeId, initial, children }: { activeId: string; initial: Draft; children: ReactNode }) {
  const lib = useLibrary();
  const [draft, dispatch] = useReducer(reducer, initial);
  const [draftFailed, setDraftFailed] = useState(false);
  const { persistActive, noteLive } = lib;
  // the text last handed to storage (starts as the loaded draft): an unchanged draft is not rewritten,
  // so merely opening a character does not bump its "updated" time
  const lastSaved = useRef<string>(JSON.stringify(initial));

  // FE-07: storage is written after the typing pauses (SAVE_DELAY_MS), and at once when the page is hidden or left, so a
  // run of keystrokes is one write, not one per key
  const saver = useMemo(
    () =>
      createDebouncedSaver<Draft>((d) => {
        const text = JSON.stringify(d);
        if (text === lastSaved.current) return;
        // on failure the draft still works in memory for this session, it just won't survive a reload
        const ok = persistActive(activeId, d);
        if (ok) lastSaved.current = text;
        setDraftFailed(!ok);
      }, SAVE_DELAY_MS),
    [activeId, persistActive],
  );

  useEffect(() => {
    noteLive(activeId, draft);
    saver.schedule(draft);
  }, [draft, activeId, noteLive, saver]);

  useEffect(() => {
    const flush = () => saver.flush();
    const onVisibility = () => {
      if (document.visibilityState === "hidden") saver.flush();
    };
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", onVisibility);
      saver.flush(); // switching character (or unmounting) saves what is pending
    };
  }, [saver]);

  const storageFailed = draftFailed || lib.storageFailed;
  const { notices, dismissNotice, unsavedRaw } = lib;
  const value = useMemo<DraftContextValue>(
    () => ({ draft, dispatch, notices, dismissNotice, unsavedRaw, storageFailed }),
    [draft, notices, dismissNotice, unsavedRaw, storageFailed],
  );

  return <DraftContext.Provider value={value}>{children}</DraftContext.Provider>;
}

/** The draft's ruleset, or "mixed" outside a DraftProvider (components that only need it to pick rule texts). */
export function useDraftRuleset(): string {
  return useContext(DraftContext)?.draft.ruleset ?? "mixed";
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error("useDraft must be used within a DraftProvider");
  return ctx;
}
