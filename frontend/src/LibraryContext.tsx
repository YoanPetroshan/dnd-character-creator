import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import type { Draft } from "./types";
import {
  bootLibrary,
  browserEnv,
  createCharacter,
  deleteCharacter,
  duplicateCharacter,
  exportLibrary,
  importDrafts,
  openCharacter,
  renameCharacter,
  saveDraft,
  summarize,
  type ImportEntry,
  type ItemSummary,
  type Library,
  type LibraryNames,
  type LibraryEnv,
} from "./library";
import { totalLevel } from "./logic/draft";
import type { Msg } from "./logic/messages";
import { useT } from "./LanguageContext";

export interface LibraryContextValue {
  /** Rows for the character list, newest first. */
  items: ItemSummary[];
  activeId: string;
  /** The active character's draft as loaded at boot / on switch (DraftProvider's initial state). */
  activeDraft: Draft;
  /** Boot-time / switch-time messages (unreadable stored data), dismissable. */
  notices: Msg[];
  dismissNotice: () => void;
  unsavedRaw: string | null;
  /** The last library-level write failed (quota, private mode). */
  storageFailed: boolean;
  /** Called by DraftProvider after each edit of the active character; returns whether the write succeeded. */
  persistActive: (id: string, draft: Draft) => boolean;
  newCharacter: () => void;
  openCharacter: (id: string) => void;
  /** Rename a character that is NOT the active one (the active one is renamed with SET_NAME). */
  renameCharacter: (id: string, name: string) => void;
  duplicateCharacter: (id: string) => void;
  deleteCharacter: (id: string) => void;
  /** Bundle of all characters (plus names of unreadable ones that were left out). */
  exportAll: () => { json: string; skipped: string[] };
  importParsed: (parsed: unknown) => ImportEntry[];
}

const LibraryContext = createContext<LibraryContextValue | null>(null);

export function LibraryProvider({ children, env }: { children: ReactNode; env?: LibraryEnv }) {
  const envRef = useRef<LibraryEnv>(env ?? browserEnv());
  const [boot] = useState(() => bootLibrary(envRef.current));
  const libRef = useRef<Library>(boot.library);
  // the live draft of the active character: summaries and exports use it instead of the (possibly lagging) stored text
  const liveRef = useRef<{ id: string; draft: Draft }>({ id: boot.library.activeId, draft: boot.draft });
  const [lib, setLib] = useState<Library>(boot.library);
  const [activeDraft, setActiveDraft] = useState<Draft>(boot.draft);
  const [summaries, setSummaries] = useState<ItemSummary[]>(() => summarize(envRef.current, boot.library));
  const [notices, setNotices] = useState<Msg[]>(boot.notices);
  // the words written into a copied character's name follow the language at the time of the click
  const t = useT();
  const namesRef = useRef<LibraryNames>({ unnamed: t.library.unnamed, copyName: t.library.copyName });
  namesRef.current = { unnamed: t.library.unnamed, copyName: t.library.copyName };
  const [unsavedRaw, setUnsavedRaw] = useState<string | null>(boot.unsavedRaw);
  const [storageFailed, setStorageFailed] = useState(boot.storageFailed);

  const commit = useCallback((next: Library, activeDraftNext?: Draft | null) => {
    libRef.current = next;
    if (activeDraftNext) liveRef.current = { id: next.activeId, draft: activeDraftNext };
    setLib(next);
    if (activeDraftNext) setActiveDraft(activeDraftNext);
    setSummaries(summarize(envRef.current, next, liveRef.current));
  }, []);

  const persistActive = useCallback((id: string, draft: Draft) => {
    liveRef.current = { id, draft };
    const r = saveDraft(envRef.current, libRef.current, id, draft);
    libRef.current = r.library;
    setLib(r.library);
    // refresh just this row from the live draft; the other rows do not change
    setSummaries((rows) =>
      rows
        .map((row) =>
          row.id === id
            ? {
                ...row,
                name: draft.name,
                classes: draft.classes.map((c) => ({ classId: c.classId, level: c.level })),
                totalLevel: totalLevel(draft),
                updatedAt: r.library.items[id]?.updatedAt ?? row.updatedAt,
                status: "ok" as const,
              }
            : row,
        )
        .sort((a, b) => b.updatedAt - a.updatedAt || b.createdAt - a.createdAt),
    );
    setStorageFailed(!r.ok);
    return r.ok;
  }, []);

  const addNotices = (more: Msg[], raw: string | null) => {
    if (more.length) setNotices((n) => [...n, ...more]);
    if (raw) setUnsavedRaw(raw);
  };

  const value = useMemo<LibraryContextValue>(
    () => ({
      items: summaries,
      activeId: lib.activeId,
      activeDraft,
      notices,
      dismissNotice: () => {
        setNotices([]);
        setUnsavedRaw(null);
      },
      unsavedRaw,
      storageFailed,
      persistActive,
      newCharacter: () => {
        const r = createCharacter(envRef.current, libRef.current);
        commit(r.library, structuredClone(r.draft));
        setStorageFailed(!r.ok);
      },
      openCharacter: (id) => {
        if (id === libRef.current.activeId) return;
        const r = openCharacter(envRef.current, libRef.current, id);
        if (!r.draft) return;
        commit(r.library, r.draft);
        addNotices(r.notices, r.unsavedRaw);
        setStorageFailed(!r.ok);
      },
      renameCharacter: (id, name) => {
        const r = renameCharacter(envRef.current, libRef.current, id, name);
        commit(r.library);
        setStorageFailed(!r.ok);
      },
      duplicateCharacter: (id) => {
        const r = duplicateCharacter(envRef.current, libRef.current, id, liveRef.current, namesRef.current);
        commit(r.library);
        setStorageFailed(!r.ok);
      },
      deleteCharacter: (id) => {
        const r = deleteCharacter(envRef.current, libRef.current, id);
        commit(r.library, r.draft);
        addNotices(r.notices, r.unsavedRaw);
        setStorageFailed(!r.ok);
      },
      exportAll: () => {
        const out = exportLibrary(envRef.current, libRef.current, liveRef.current);
        return { json: JSON.stringify(out.bundle, null, 2), skipped: out.skipped };
      },
      importParsed: (parsed) => {
        const r = importDrafts(envRef.current, libRef.current, parsed);
        commit(r.library);
        setStorageFailed(!r.ok);
        return r.report;
      },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [summaries, lib.activeId, activeDraft, notices, unsavedRaw, storageFailed, persistActive, commit],
  );

  return <LibraryContext.Provider value={value}>{children}</LibraryContext.Provider>;
}

export function useLibrary(): LibraryContextValue {
  const ctx = useContext(LibraryContext);
  if (!ctx) throw new Error("useLibrary must be used within a LibraryProvider");
  return ctx;
}
