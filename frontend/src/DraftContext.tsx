import { createContext, useCallback, useContext, useReducer, useEffect, useState, type Dispatch, type ReactNode } from "react";
import type { Draft } from "./types";
import { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, reducer, totalLevel, type Action } from "./logic/draft";

// Re-exported so existing imports from "./DraftContext" keep working.
export { DRAFT_VERSION, MAX_TOTAL_LEVEL, emptyDraft, mergeDraft, totalLevel };

const STORAGE_KEY = "dnd-builder-draft-v2";
/** A stored draft that could not be loaded is copied here before the empty
 *  default overwrites it, so a newer-version or corrupt draft is not lost. */
const BACKUP_KEY = "dnd-builder-draft-v2.unreadable-backup";

function loadInitial(): { draft: Draft; notice: string | null; unsavedRaw: string | null } {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { draft: mergeDraft(JSON.parse(raw)), notice: null, unsavedRaw: null };
  } catch (e) {
    // corrupt or inaccessible storage — start fresh, but keep what was there
    if (raw) {
      let backedUp = true;
      try {
        localStorage.setItem(BACKUP_KEY, raw);
      } catch {
        backedUp = false; // storage near quota: the old text is about to be overwritten
      }
      const why = e instanceof SyntaxError ? "Запазената чернова е повредена." : e instanceof Error ? e.message : "";
      if (!backedUp) {
        return {
          draft: emptyDraft,
          notice: `${why} Започнато е с празна чернова, а старата НЕ можа да се запази в браузъра (хранилището е пълно). Свали я сега, иначе ще се загуби.`,
          unsavedRaw: raw,
        };
      }
      return { draft: emptyDraft, notice: `${why} Започнато е с празна чернова; старата е запазена в браузъра (${BACKUP_KEY}).`, unsavedRaw: null };
    }
  }
  return { draft: emptyDraft, notice: null, unsavedRaw: null };
}

interface DraftContextValue {
  draft: Draft;
  dispatch: Dispatch<Action>;
  /** One-off message about the boot-time load (unreadable stored draft). */
  notice: string | null;
  dismissNotice: () => void;
  /** Raw text of an unreadable stored draft whose backup write failed; offered for download. */
  unsavedRaw: string | null;
  /** The last write to localStorage failed (quota, private mode). */
  storageFailed: boolean;
}

const DraftContext = createContext<DraftContextValue | null>(null);

export function DraftProvider({ children }: { children: ReactNode }) {
  const [boot] = useState(loadInitial);
  const [draft, dispatch] = useReducer(reducer, boot.draft);
  const [notice, setNotice] = useState<string | null>(boot.notice);
  const [storageFailed, setStorageFailed] = useState(false);
  const dismissNotice = useCallback(() => setNotice(null), []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
      setStorageFailed(false);
    } catch {
      // storage unavailable (private mode, quota) — the draft still works
      // in-memory for this session, it just won't survive a reload
      setStorageFailed(true);
    }
  }, [draft]);

  return (
    <DraftContext.Provider value={{ draft, dispatch, notice, dismissNotice, unsavedRaw: boot.unsavedRaw, storageFailed }}>{children}</DraftContext.Provider>
  );
}

export function useDraft(): DraftContextValue {
  const ctx = useContext(DraftContext);
  if (!ctx) throw new Error("useDraft must be used within a DraftProvider");
  return ctx;
}
