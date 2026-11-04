import { createContext, useContext, useReducer, useEffect, useRef, useState, type Dispatch, type ReactNode } from "react";
import type { Draft } from "./types";
import { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, reducer, totalLevel, type Action } from "./logic/draft";
import { useLibrary } from "./LibraryContext";
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
  const { persistActive } = lib;
  // the text last handed to storage (starts as the loaded draft): an unchanged draft is not rewritten,
  // so merely opening a character does not bump its "updated" time
  const lastSaved = useRef<string>(JSON.stringify(initial));

  useEffect(() => {
    const text = JSON.stringify(draft);
    if (text === lastSaved.current) return;
    // on failure the draft still works in memory for this session, it just won't survive a reload
    const ok = persistActive(activeId, draft);
    if (ok) lastSaved.current = text;
    setDraftFailed(!ok);
  }, [draft, activeId, persistActive]);

  return (
    <DraftContext.Provider
      value={{
        draft,
        dispatch,
        notices: lib.notices,
        dismissNotice: lib.dismissNotice,
        unsavedRaw: lib.unsavedRaw,
        storageFailed: draftFailed || lib.storageFailed,
      }}
    >
      {children}
    </DraftContext.Provider>
  );
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error("useDraft must be used within a DraftProvider");
  return ctx;
}
