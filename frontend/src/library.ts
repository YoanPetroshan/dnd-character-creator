// Character library (SK4): several characters in localStorage. Pure functions over an
// injected storage adapter (no React, no globals) so the whole thing is testable with an
// in-memory adapter, a fake clock and fake ids.
//
// Storage layout
//   dnd-builder-library-v1            {version:1, activeId, items:{[id]:{id,name,createdAt,updatedAt,seenChoiceIds}}}
//   dnd-builder-draft-v2:<id>         one Draft per character (shape and DRAFT_VERSION unchanged)
//   dnd-builder-draft-v2              LEGACY single draft: migrated at boot into the first item and
//                                     then only READ; removed once a second character exists
//   <key>.unreadable-backup           copies of texts that could not be loaded (never overwritten silently)
//
// Write rules: every write is try/catch. The draft is written BEFORE the index, so a failed
// draft write never leaves the index pointing at a half-written character, and a failed write
// of one character never touches the others.
import type { Draft } from "./types";
import { emptyDraft, mergeDraft, totalLevel } from "./logic/draft";
import { MsgError, msg, toMsg, type Msg } from "./logic/messages";

export const LIBRARY_KEY = "dnd-builder-library-v1";
export const LIBRARY_BACKUP_KEY = "dnd-builder-library-v1.unreadable-backup";
export const LEGACY_DRAFT_KEY = "dnd-builder-draft-v2";
export const LEGACY_BACKUP_KEY = "dnd-builder-draft-v2.unreadable-backup";
export const DRAFT_KEY_PREFIX = "dnd-builder-draft-v2:";
const BACKUP_SUFFIX = ".unreadable-backup";
export const MAX_IMPORT = 200;

export const draftKey = (id: string) => `${DRAFT_KEY_PREFIX}${id}`;
export const backupKey = (id: string) => `${DRAFT_KEY_PREFIX}${id}${BACKUP_SUFFIX}`;

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  keys(): string[];
}

export interface LibraryEnv {
  storage: StorageLike;
  /** epoch milliseconds */
  now(): number;
  newId(): string;
}

export interface LibraryItem {
  id: string;
  name: string;
  createdAt: number;
  updatedAt: number;
  seenChoiceIds: string[];
}

export interface Library {
  version: 1;
  activeId: string;
  items: Record<string, LibraryItem>;
  /** id of the item the legacy single key was migrated into (decides when the legacy key may go) */
  legacyId?: string;
}

export interface BootResult {
  library: Library;
  draft: Draft;
  notices: Msg[];
  /** raw text of an unreadable ACTIVE draft/legacy key whose backup write failed */
  unsavedRaw: string | null;
  storageFailed: boolean;
}

export interface ItemSummary {
  id: string;
  name: string;
  classes: Array<{ classId: string; level: number }>;
  totalLevel: number;
  createdAt: number;
  updatedAt: number;
  /** ok = draft readable; empty = no stored draft; corrupt = stored text unreadable */
  status: "ok" | "empty" | "corrupt";
}

export interface ImportEntry {
  index: number;
  name: string;
  status: "accepted" | "rejected";
  id?: string;
  message: Msg;
}

export interface LiveDraft {
  id: string;
  draft: Draft;
}

// ---- storage helpers (never throw) -------------------------------------------------------

function get(env: LibraryEnv, key: string): string | null {
  try {
    return env.storage.getItem(key);
  } catch {
    return null;
  }
}
function put(env: LibraryEnv, key: string, value: string): boolean {
  try {
    env.storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}
function del(env: LibraryEnv, key: string): void {
  try {
    env.storage.removeItem(key);
  } catch {
    // nothing sensible to do
  }
}
function keysOf(env: LibraryEnv): string[] {
  try {
    return env.storage.keys();
  } catch {
    return [];
  }
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
const whyOf = (e: unknown): Msg =>
  e instanceof SyntaxError
    ? msg("lib.unreadable")
    : e instanceof MsgError
      ? e.msg
      : e instanceof Error
        ? msg("raw", { text: e.message })
        : msg("lib.cannotRead");

function writeIndex(env: LibraryEnv, lib: Library): boolean {
  return put(env, LIBRARY_KEY, JSON.stringify(lib));
}

function freshId(env: LibraryEnv, lib: Library): string {
  let id = env.newId();
  for (let i = 0; i < 50 && (lib.items[id] || get(env, draftKey(id)) !== null); i++) id = env.newId();
  return id;
}

function newItem(env: LibraryEnv, id: string, name: string, seen: string[] = []): LibraryItem {
  const t = env.now();
  return { id, name, createdAt: t, updatedAt: t, seenChoiceIds: [...seen] };
}

type DraftRead =
  | { kind: "ok"; draft: Draft }
  | { kind: "missing" }
  | { kind: "corrupt"; raw: string; why: Msg };

function readDraft(env: LibraryEnv, id: string): DraftRead {
  const raw = get(env, draftKey(id));
  if (raw === null) return { kind: "missing" };
  try {
    return { kind: "ok", draft: mergeDraft(JSON.parse(raw)) };
  } catch (e) {
    return { kind: "corrupt", raw, why: whyOf(e) };
  }
}

/** The legacy single key goes away only after a second character exists and only when its
 *  content is safe elsewhere: a migrated draft exists under its item id, or an unreadable
 *  text has an identical backup. */
function dropLegacy(env: LibraryEnv, lib: Library): void {
  if (Object.keys(lib.items).length < 2) return;
  const raw = get(env, LEGACY_DRAFT_KEY);
  if (raw === null) return;
  const lid = lib.legacyId;
  const safe = lid ? !lib.items[lid] || get(env, draftKey(lid)) !== null : get(env, LEGACY_BACKUP_KEY) === raw;
  if (safe) del(env, LEGACY_DRAFT_KEY);
}

/** Back up a corrupt item draft and remove it from the draft key (the item becomes an empty
 *  character). If the backup cannot be written the stored text is left untouched. */
function isolateCorrupt(env: LibraryEnv, item: LibraryItem, raw: string, why: Msg): { isolated: boolean; notice: Msg } {
  const bk = backupKey(item.id);
  if (put(env, bk, raw)) {
    del(env, draftKey(item.id));
    return {
      isolated: true,
      notice: msg("lib.isolated", { name: item.name, why, key: bk }),
    };
  }
  return {
    isolated: false,
    notice: msg("lib.isolatedNoBackup", { name: item.name, why }),
  };
}

function normalizeLibrary(parsed: unknown, env: LibraryEnv): Library | null {
  if (!isObj(parsed) || parsed.version !== 1 || !isObj(parsed.items)) return null;
  const items: Record<string, LibraryItem> = {};
  for (const [id, v] of Object.entries(parsed.items)) {
    if (!isObj(v)) continue;
    const t = env.now();
    items[id] = {
      id,
      name: typeof v.name === "string" ? v.name : "",
      createdAt: typeof v.createdAt === "number" && Number.isFinite(v.createdAt) ? v.createdAt : t,
      updatedAt: typeof v.updatedAt === "number" && Number.isFinite(v.updatedAt) ? v.updatedAt : t,
      seenChoiceIds: Array.isArray(v.seenChoiceIds) ? v.seenChoiceIds.filter((x): x is string => typeof x === "string") : [],
    };
  }
  const ids = Object.keys(items);
  if (ids.length === 0) return null;
  const activeId = typeof parsed.activeId === "string" && items[parsed.activeId] ? parsed.activeId : mostRecent(items);
  const lib: Library = { version: 1, activeId, items };
  if (typeof parsed.legacyId === "string") lib.legacyId = parsed.legacyId;
  return lib;
}

function mostRecent(items: Record<string, LibraryItem>, except?: string): string {
  return Object.values(items)
    .filter((i) => i.id !== except)
    .sort((a, b) => b.updatedAt - a.updatedAt || b.createdAt - a.createdAt)[0]?.id as string;
}

/** Library rebuilt from the per-character draft keys when the index is unreadable. */
function rebuildFromDraftKeys(env: LibraryEnv): Library | null {
  const items: Record<string, LibraryItem> = {};
  for (const k of keysOf(env)) {
    if (!k.startsWith(DRAFT_KEY_PREFIX) || k.endsWith(BACKUP_SUFFIX)) continue;
    const id = k.slice(DRAFT_KEY_PREFIX.length);
    if (!id) continue;
    let name = "";
    try {
      name = mergeDraft(JSON.parse(get(env, k) as string)).name;
    } catch {
      // unreadable: adopted anyway, isolated by the per-item check
    }
    items[id] = newItem(env, id, name);
  }
  const ids = Object.keys(items);
  if (ids.length === 0) return null;
  return { version: 1, activeId: ids[0], items };
}

// ---- boot ---------------------------------------------------------------------------------

export function bootLibrary(env: LibraryEnv): BootResult {
  const notices: Msg[] = [];
  let unsavedRaw: string | null = null;
  let storageFailed = false;
  let lib: Library | null = null;
  let loadedText: string | null = null;
  let firstItemDraft: Draft | null = null;

  const libRaw = get(env, LIBRARY_KEY);
  if (libRaw !== null) {
    try {
      lib = normalizeLibrary(JSON.parse(libRaw), env);
      loadedText = libRaw;
    } catch {
      lib = null;
    }
    if (!lib) {
      // unreadable or newer-version index: keep the text, rebuild from the draft keys
      const saved = put(env, LIBRARY_BACKUP_KEY, libRaw);
      lib = rebuildFromDraftKeys(env);
      notices.push(
        msg("lib.libraryDamaged", {
          saved: saved ? msg("lib.backupSaved", { key: LIBRARY_BACKUP_KEY }) : msg("lib.backupFailed"),
          recovered: lib ? msg("lib.recovered") : msg("lib.startedEmptyLibrary"),
        }),
      );
      if (!saved) unsavedRaw = libRaw;
      loadedText = null;
    }
  }

  if (!lib) {
    // first run (or nothing recoverable): migrate the legacy single key, else start empty
    const id = env.newId();
    const legacyRaw = get(env, LEGACY_DRAFT_KEY);
    let item: LibraryItem;
    let draft: Draft = emptyDraft;
    let migrated = false;
    if (legacyRaw !== null) {
      try {
        draft = mergeDraft(JSON.parse(legacyRaw));
        migrated = true;
      } catch (e) {
        draft = emptyDraft;
        const saved = put(env, LEGACY_BACKUP_KEY, legacyRaw);
        const why = whyOf(e);
        if (saved) notices.push(msg("lib.legacyBackedUp", { why, key: LEGACY_BACKUP_KEY }));
        else {
          unsavedRaw = legacyRaw;
          notices.push(msg("lib.legacyNotBackedUp", { why }));
        }
      }
    }
    item = newItem(env, id, draft.name);
    lib = { version: 1, activeId: id, items: { [id]: item } };
    if (migrated) lib.legacyId = id;
    firstItemDraft = draft;
    // draft first, then index; a failed index removes the draft again so the next boot
    // migrates from the untouched legacy key instead of finding an orphan
    const draftOk = put(env, draftKey(id), JSON.stringify(draft));
    const indexOk = draftOk && writeIndex(env, lib);
    if (draftOk && !indexOk) del(env, draftKey(id));
    if (!indexOk) storageFailed = true;
    return { library: lib, draft: firstItemDraft, notices, unsavedRaw, storageFailed };
  }

  // existing library: check every item, isolate the corrupt ones, load the active draft
  let active: Draft | null = null;
  for (const item of Object.values(lib.items)) {
    const r = readDraft(env, item.id);
    if (r.kind === "ok") {
      if (item.id === lib.activeId) active = r.draft;
    } else if (r.kind === "corrupt") {
      const iso = isolateCorrupt(env, item, r.raw, r.why);
      notices.push(iso.notice);
      if (item.id === lib.activeId) {
        if (!iso.isolated) unsavedRaw = r.raw;
        active = { ...clone(emptyDraft), name: item.name };
      }
    } else if (item.id === lib.activeId) {
      active = { ...clone(emptyDraft), name: item.name };
    }
  }
  const text = JSON.stringify(lib);
  if (text !== loadedText && !writeIndex(env, lib)) storageFailed = true;
  return { library: lib, draft: active as Draft, notices, unsavedRaw, storageFailed };
}

// ---- operations ---------------------------------------------------------------------------

export function saveDraft(env: LibraryEnv, lib: Library, id: string, draft: Draft): { library: Library; ok: boolean } {
  const item = lib.items[id];
  if (!item) return { library: lib, ok: true };
  if (!put(env, draftKey(id), JSON.stringify(draft))) return { library: lib, ok: false };
  const next: Library = { ...lib, items: { ...lib.items, [id]: { ...item, name: draft.name, updatedAt: env.now() } } };
  return { library: next, ok: writeIndex(env, next) };
}

/** Add a character (the draft defaults to an empty one) and make it active. Does not touch the others. */
export function createCharacter(env: LibraryEnv, lib: Library, draft: Draft = emptyDraft): { library: Library; id: string; draft: Draft; ok: boolean } {
  const id = freshId(env, lib);
  const draftOk = put(env, draftKey(id), JSON.stringify(draft));
  const next: Library = { ...lib, activeId: id, items: { ...lib.items, [id]: newItem(env, id, draft.name) } };
  const indexOk = writeIndex(env, next);
  dropLegacy(env, next);
  return { library: next, id, draft, ok: draftOk && indexOk };
}

export function openCharacter(
  env: LibraryEnv,
  lib: Library,
  id: string,
): { library: Library; draft: Draft | null; notices: Msg[]; unsavedRaw: string | null; ok: boolean } {
  const item = lib.items[id];
  if (!item) return { library: lib, draft: null, notices: [], unsavedRaw: null, ok: true };
  const notices: Msg[] = [];
  let unsavedRaw: string | null = null;
  let draft: Draft;
  const r = readDraft(env, id);
  if (r.kind === "ok") draft = r.draft;
  else {
    draft = { ...clone(emptyDraft), name: item.name };
    if (r.kind === "corrupt") {
      const iso = isolateCorrupt(env, item, r.raw, r.why);
      notices.push(iso.notice);
      if (!iso.isolated) unsavedRaw = r.raw;
    }
  }
  const next: Library = { ...lib, activeId: id };
  return { library: next, draft, notices, unsavedRaw, ok: writeIndex(env, next) };
}

/** Rename = set draft.name (kept in sync with the index). For the active character with unsaved
 *  in-memory edits the caller dispatches SET_NAME instead. */
export function renameCharacter(env: LibraryEnv, lib: Library, id: string, name: string): { library: Library; ok: boolean } {
  const item = lib.items[id];
  if (!item) return { library: lib, ok: true };
  const r = readDraft(env, id);
  const base = r.kind === "ok" ? r.draft : { ...clone(emptyDraft) };
  if (r.kind === "corrupt") return { library: lib, ok: false };
  return saveDraft(env, lib, id, { ...base, name });
}

/** The words the library writes into a character's name (language-dependent, so the caller supplies them). */
export interface LibraryNames {
  unnamed: string;
  copyName: (name: string) => string;
}

export function duplicateCharacter(
  env: LibraryEnv,
  lib: Library,
  id: string,
  live: LiveDraft | undefined,
  names: LibraryNames,
): { library: Library; id: string | null; ok: boolean } {
  const item = lib.items[id];
  if (!item) return { library: lib, id: null, ok: true };
  let source: Draft;
  if (live && live.id === id) source = live.draft;
  else {
    const r = readDraft(env, id);
    if (r.kind === "corrupt") return { library: lib, id: null, ok: false };
    source = r.kind === "ok" ? r.draft : { ...clone(emptyDraft), name: item.name };
  }
  const copy = clone(source);
  copy.name = names.copyName(copy.name || names.unnamed);
  const newId = freshId(env, lib);
  const draftOk = put(env, draftKey(newId), JSON.stringify(copy));
  const next: Library = { ...lib, items: { ...lib.items, [newId]: newItem(env, newId, copy.name, item.seenChoiceIds) } };
  const indexOk = writeIndex(env, next);
  dropLegacy(env, next);
  return { library: next, id: newId, ok: draftOk && indexOk };
}

/** Delete one character. Deleting the active one activates the most recently updated other one
 *  (its draft is returned); deleting the last one creates an empty character. `draft` is null when
 *  the active character did not change. */
export function deleteCharacter(env: LibraryEnv, lib: Library, id: string): { library: Library; draft: Draft | null; notices: Msg[]; unsavedRaw: string | null; ok: boolean } {
  if (!lib.items[id]) return { library: lib, draft: null, notices: [], unsavedRaw: null, ok: true };
  const items = { ...lib.items };
  delete items[id];
  let next: Library = { ...lib, items };
  let draft: Draft | null = null;
  let ok = true;
  let notices: Msg[] = [];
  let unsavedRaw: string | null = null;
  if (Object.keys(items).length === 0) {
    const created = createCharacter(env, next);
    next = created.library;
    draft = clone(emptyDraft);
    ok = created.ok;
  } else if (lib.activeId === id) {
    const opened = openCharacter(env, next, mostRecent(items));
    next = opened.library;
    draft = opened.draft;
    notices = opened.notices;
    unsavedRaw = opened.unsavedRaw;
    ok = opened.ok;
  } else {
    ok = writeIndex(env, next);
  }
  del(env, draftKey(id));
  del(env, backupKey(id));
  return { library: next, draft, notices, unsavedRaw, ok };
}

/** Drafts to put in the bundle (plain drafts, oldest character first). `live` overrides the stored
 *  text of the active character, which can lag behind when a storage write failed. */
export function exportLibrary(
  env: LibraryEnv,
  lib: Library,
  live?: LiveDraft,
): { bundle: { kind: "dnd-builder-library"; version: 1; drafts: Draft[] }; skipped: string[] } {
  const drafts: Draft[] = [];
  const skipped: string[] = [];
  const items = Object.values(lib.items).sort((a, b) => a.createdAt - b.createdAt);
  for (const item of items) {
    if (live && live.id === item.id) {
      drafts.push(clone(live.draft));
      continue;
    }
    const r = readDraft(env, item.id);
    if (r.kind === "ok") drafts.push(r.draft);
    else if (r.kind === "missing") drafts.push({ ...clone(emptyDraft), name: item.name });
    else skipped.push(item.name);
  }
  return { bundle: { kind: "dnd-builder-library", version: 1, drafts }, skipped };
}

/** Import one draft or a library bundle. Every draft goes through mergeDraft; accepted ones become
 *  NEW characters with fresh ids (existing characters are never overwritten, the active one does not
 *  change). The report has one entry per candidate, with messages (Msg, rendered by the UI). */
export function importDrafts(env: LibraryEnv, lib: Library, parsed: unknown): { library: Library; report: ImportEntry[]; ok: boolean } {
  const report: ImportEntry[] = [];
  let candidates: unknown[];
  if (isObj(parsed) && parsed.kind === "dnd-builder-library") {
    if (typeof parsed.version === "number" && parsed.version > 1) {
      return rejectAll(lib, msg("lib.bundleNewer"));
    }
    if (!Array.isArray(parsed.drafts)) return rejectAll(lib, msg("lib.bundleNoList"));
    candidates = parsed.drafts;
    if (candidates.length === 0) return rejectAll(lib, msg("lib.bundleEmpty"));
  } else {
    candidates = [parsed];
  }
  let next = lib;
  let ok = true;
  let accepted = 0;
  candidates.forEach((c, index) => {
    const nameOf = isObj(c) && typeof c.name === "string" ? c.name : "";
    if (index >= MAX_IMPORT) {
      report.push({ index, name: nameOf, status: "rejected", message: msg("lib.tooMany", { max: MAX_IMPORT }) });
      return;
    }
    let draft: Draft;
    try {
      draft = mergeDraft(c);
    } catch (e) {
      report.push({ index, name: nameOf, status: "rejected", message: toMsg(e) });
      return;
    }
    const id = freshId(env, next);
    if (!put(env, draftKey(id), JSON.stringify(draft))) {
      ok = false;
      report.push({ index, name: draft.name, status: "rejected", message: msg("lib.cannotStore") });
      return;
    }
    next = { ...next, items: { ...next.items, [id]: newItem(env, id, draft.name) } };
    accepted++;
    report.push({ index, name: draft.name, status: "accepted", id, message: msg("lib.added") });
  });
  if (accepted > 0) {
    if (!writeIndex(env, next)) ok = false;
    dropLegacy(env, next);
  }
  return { library: next, report, ok };

  function rejectAll(l: Library, message: Msg) {
    return { library: l, report: [{ index: 0, name: "", status: "rejected" as const, message }], ok: true };
  }
}

/** Per-character rows for the list, newest first. */
export function summarize(env: LibraryEnv, lib: Library, live?: LiveDraft): ItemSummary[] {
  const rows: ItemSummary[] = Object.values(lib.items).map((item) => {
    let draft: Draft | null = null;
    let status: ItemSummary["status"] = "ok";
    if (live && live.id === item.id) draft = live.draft;
    else {
      const r = readDraft(env, item.id);
      if (r.kind === "ok") draft = r.draft;
      else status = r.kind === "missing" ? "empty" : "corrupt";
    }
    return {
      id: item.id,
      name: item.name,
      classes: draft ? draft.classes.map((c) => ({ classId: c.classId, level: c.level })) : [],
      totalLevel: draft ? totalLevel(draft) : 0,
      createdAt: item.createdAt,
      updatedAt: item.updatedAt,
      status,
    };
  });
  return rows.sort((a, b) => b.updatedAt - a.updatedAt || b.createdAt - a.createdAt);
}

// ---- helpers for code that sits outside the providers (ErrorBoundary) --------------------

/** Raw stored text of the active character (or of the legacy key when no library exists yet). */
export function activeDraftRaw(storage: StorageLike): string | null {
  try {
    const lib = JSON.parse(storage.getItem(LIBRARY_KEY) ?? "null");
    if (isObj(lib) && typeof lib.activeId === "string") return storage.getItem(draftKey(lib.activeId));
  } catch {
    // fall through to the legacy key
  }
  try {
    return storage.getItem(LEGACY_DRAFT_KEY);
  } catch {
    return null;
  }
}

/** Remove only the active character's stored draft (the item stays and boots as an empty character). */
export function resetActiveDraft(storage: StorageLike): void {
  try {
    const lib = JSON.parse(storage.getItem(LIBRARY_KEY) ?? "null");
    if (isObj(lib) && typeof lib.activeId === "string") {
      storage.removeItem(draftKey(lib.activeId));
      return;
    }
  } catch {
    // fall through
  }
  try {
    storage.removeItem(LEGACY_DRAFT_KEY);
  } catch {
    // ignore
  }
}

// ---- default environment (browser) -------------------------------------------------------

export function browserStorage(): StorageLike {
  return {
    getItem: (k) => localStorage.getItem(k),
    setItem: (k, v) => localStorage.setItem(k, v),
    removeItem: (k) => localStorage.removeItem(k),
    keys: () => Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i)).filter((k): k is string => k !== null),
  };
}

export function browserEnv(): LibraryEnv {
  return {
    storage: browserStorage(),
    now: () => Date.now(),
    newId: () =>
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`,
  };
}
