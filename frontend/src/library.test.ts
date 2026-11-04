import { describe, expect, it } from "vitest";
import {
  LEGACY_BACKUP_KEY,
  LEGACY_DRAFT_KEY,
  LIBRARY_BACKUP_KEY,
  LIBRARY_KEY,
  activeDraftRaw,
  backupKey,
  bootLibrary,
  createCharacter,
  deleteCharacter,
  draftKey,
  duplicateCharacter,
  exportLibrary,
  importDrafts,
  openCharacter,
  renameCharacter,
  resetActiveDraft,
  saveDraft,
  summarize,
  type LibraryEnv,
  type StorageLike,
} from "./library";
import { DRAFT_VERSION, emptyDraft } from "./logic/draft";
import type { Draft } from "./types";

class MemoryStorage implements StorageLike {
  data = new Map<string, string>();
  /** keys whose setItem throws (quota) */
  failKeys = new Set<string>();
  failAll = false;
  getItem(k: string) {
    return this.data.has(k) ? (this.data.get(k) as string) : null;
  }
  setItem(k: string, v: string) {
    if (this.failAll || this.failKeys.has(k)) throw new DOMException("full", "QuotaExceededError");
    this.data.set(k, v);
  }
  removeItem(k: string) {
    this.data.delete(k);
  }
  keys() {
    return [...this.data.keys()];
  }
}

function makeEnv(storage = new MemoryStorage(), ids: string[] = []) {
  let t = 1000;
  let n = 0;
  const env: LibraryEnv = {
    storage,
    now: () => (t += 10),
    newId: () => (ids.length ? (ids.shift() as string) : `id${++n}`),
  };
  return { env, storage };
}

function draftOf(name: string, classes: Array<[string, number]> = []): Draft {
  return {
    ...structuredClone(emptyDraft),
    name,
    classes: classes.map(([classId, level]) => ({ classId, level, choices: { [`class:${classId}:x`]: ["a"] } })),
  };
}

const legacyRaw = (d: Draft) => JSON.stringify(d);
const stored = (s: MemoryStorage, id: string) => JSON.parse(s.getItem(draftKey(id)) as string) as Draft;
const idx = (s: MemoryStorage) => JSON.parse(s.getItem(LIBRARY_KEY) as string);

describe("bootLibrary: first run and legacy migration", () => {
  it("fresh storage -> one empty active character, persisted", () => {
    const { env, storage } = makeEnv();
    const b = bootLibrary(env);
    expect(Object.keys(b.library.items)).toHaveLength(1);
    expect(b.library.activeId).toBe("id1");
    expect(b.draft.classes).toEqual([]);
    expect(idx(storage).version).toBe(1);
    expect(stored(storage, "id1").draftVersion).toBe(DRAFT_VERSION);
  });

  it("migrates the legacy single key into the first item, draft preserved, active set, legacy key untouched", () => {
    const { env, storage } = makeEnv();
    const legacy = draftOf("Зара", [["warlock", 7]]);
    storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(legacy));
    const b = bootLibrary(env);
    const ids = Object.keys(b.library.items);
    expect(ids).toHaveLength(1);
    expect(b.library.activeId).toBe(ids[0]);
    expect(b.library.items[ids[0]].name).toBe("Зара");
    expect(b.draft.classes[0]).toMatchObject({ classId: "warlock", level: 7 });
    expect(stored(storage, ids[0]).classes[0].classId).toBe("warlock");
    expect(storage.getItem(LEGACY_DRAFT_KEY)).toBe(legacyRaw(legacy));
    expect(b.notices).toEqual([]);
  });

  it("migrating twice is idempotent (second boot reads the library, not the legacy key)", () => {
    const { env, storage } = makeEnv();
    storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const first = bootLibrary(env);
    const second = bootLibrary(env);
    expect(Object.keys(second.library.items)).toEqual(Object.keys(first.library.items));
    expect(second.library.activeId).toBe(first.library.activeId);
    expect(second.draft).toEqual(first.draft);
  });

  it("an unreadable legacy key is backed up (legacy behaviour), a notice is returned, an empty character starts", () => {
    const { env, storage } = makeEnv();
    storage.setItem(LEGACY_DRAFT_KEY, "{not json");
    const b = bootLibrary(env);
    expect(storage.getItem(LEGACY_BACKUP_KEY)).toBe("{not json");
    expect(b.notices[0]).toContain("повредена");
    expect(b.notices[0]).toContain(LEGACY_BACKUP_KEY);
    expect(b.unsavedRaw).toBeNull();
    expect(Object.keys(b.library.items)).toHaveLength(1);
    expect(b.draft.classes).toEqual([]);
  });

  it("an unreadable legacy key whose backup fails is offered as unsavedRaw", () => {
    const { env, storage } = makeEnv();
    storage.setItem(LEGACY_DRAFT_KEY, "{not json");
    storage.failKeys.add(LEGACY_BACKUP_KEY);
    const b = bootLibrary(env);
    expect(b.unsavedRaw).toBe("{not json");
    expect(b.notices[0]).toContain("НЕ можа да се запази");
  });

  it("a newer-version legacy draft is treated as unreadable and backed up", () => {
    const { env, storage } = makeEnv();
    storage.setItem(LEGACY_DRAFT_KEY, JSON.stringify({ draftVersion: DRAFT_VERSION + 1, classes: [] }));
    const b = bootLibrary(env);
    expect(storage.getItem(LEGACY_BACKUP_KEY)).not.toBeNull();
    expect(b.notices[0]).toContain("по-нова версия");
  });

  it("migration is lossless when the library cannot be written: legacy stays, nothing half-written", () => {
    const { env, storage } = makeEnv();
    storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["bard", 3]])));
    storage.failKeys.add(LIBRARY_KEY);
    const b = bootLibrary(env);
    expect(b.storageFailed).toBe(true);
    expect(b.draft.classes[0].classId).toBe("bard");
    expect(storage.getItem(LEGACY_DRAFT_KEY)).not.toBeNull();
    expect(storage.keys().filter((k) => k.startsWith("dnd-builder-draft-v2:"))).toEqual([]);
    // next boot, storage healthy again: migrates cleanly
    storage.failKeys.clear();
    const again = bootLibrary(env);
    expect(again.draft.classes[0].classId).toBe("bard");
    expect(Object.keys(again.library.items)).toHaveLength(1);
  });
});

describe("operations", () => {
  function twoCharacters() {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const boot = bootLibrary(h.env);
    return { ...h, boot, firstId: boot.library.activeId };
  }

  it("new character does not delete the others, activates itself, and finally drops the legacy key", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    expect(storage.getItem(LEGACY_DRAFT_KEY)).not.toBeNull();
    const r = createCharacter(env, boot.library);
    expect(r.ok).toBe(true);
    expect(Object.keys(r.library.items)).toHaveLength(2);
    expect(r.library.activeId).toBe(r.id);
    expect(stored(storage, firstId).classes[0].classId).toBe("warlock");
    expect(storage.getItem(LEGACY_DRAFT_KEY)).toBeNull();
    expect(idx(storage).activeId).toBe(r.id);
  });

  it("the legacy key survives while a single character exists", () => {
    const { env, storage, boot } = twoCharacters();
    saveDraft(env, boot.library, boot.library.activeId, draftOf("Зара", [["warlock", 8]]));
    expect(storage.getItem(LEGACY_DRAFT_KEY)).not.toBeNull();
  });

  it("open switches the active character and loads its draft", () => {
    const { env, boot, firstId } = twoCharacters();
    const made = createCharacter(env, boot.library);
    const back = openCharacter(env, made.library, firstId);
    expect(back.library.activeId).toBe(firstId);
    expect(back.draft?.classes[0].classId).toBe("warlock");
    expect(back.notices).toEqual([]);
  });

  it("saveDraft keeps the item name in sync with draft.name and bumps updatedAt", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const before = boot.library.items[firstId].updatedAt;
    const r = saveDraft(env, boot.library, firstId, draftOf("Мира", [["warlock", 7]]));
    expect(r.ok).toBe(true);
    expect(r.library.items[firstId].name).toBe("Мира");
    expect(r.library.items[firstId].updatedAt).toBeGreaterThan(before);
    expect(idx(storage).items[firstId].name).toBe("Мира");
    expect(stored(storage, firstId).name).toBe("Мира");
  });

  it("rename of a non-active character rewrites its draft name and the index", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const made = createCharacter(env, boot.library);
    const r = renameCharacter(env, made.library, firstId, "Нова Зара");
    expect(r.library.items[firstId].name).toBe("Нова Зара");
    expect(stored(storage, firstId).name).toBe("Нова Зара");
    expect(stored(storage, firstId).classes[0].classId).toBe("warlock");
    expect(r.library.activeId).toBe(made.id);
  });

  it("duplicate deep-copies: new id, 'копие' suffix, independent from the original", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const r = duplicateCharacter(env, boot.library, firstId);
    expect(r.id).not.toBe(firstId);
    expect(r.library.items[r.id as string].name).toBe("Зара (копие)");
    const copy = stored(storage, r.id as string);
    expect(copy.name).toBe("Зара (копие)");
    expect(copy.classes[0]).toMatchObject({ classId: "warlock", level: 7 });
    // mutate the saved original: the copy must not follow
    saveDraft(env, r.library, firstId, draftOf("Зара", [["warlock", 3]]));
    expect(stored(storage, r.id as string).classes[0].level).toBe(7);
    expect(r.library.activeId).toBe(firstId);
    expect(storage.getItem(LEGACY_DRAFT_KEY)).toBeNull();
  });

  it("duplicate uses the live in-memory draft of the active character when storage lags", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    storage.failKeys.add(draftKey(firstId));
    const live = draftOf("Зара", [["warlock", 12]]);
    const r = duplicateCharacter(env, boot.library, firstId, { id: firstId, draft: live });
    expect(stored(storage, r.id as string).classes[0].level).toBe(12);
  });

  it("an unnamed character duplicates as 'Без име (копие)'", () => {
    const { env } = makeEnv();
    const b = bootLibrary(env);
    const r = duplicateCharacter(env, b.library, b.library.activeId);
    expect(r.library.items[r.id as string].name).toBe("Без име (копие)");
  });

  it("delete of a non-active character leaves the active one", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const made = createCharacter(env, boot.library);
    const r = deleteCharacter(env, made.library, firstId);
    expect(r.library.activeId).toBe(made.id);
    expect(r.library.items[firstId]).toBeUndefined();
    expect(storage.getItem(draftKey(firstId))).toBeNull();
    expect(r.draft).toBeNull();
  });

  it("delete of the active character activates another (most recently updated) and returns its draft", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const made = createCharacter(env, boot.library);
    const r = deleteCharacter(env, made.library, made.id as string);
    expect(r.library.activeId).toBe(firstId);
    expect(r.draft?.classes[0].classId).toBe("warlock");
    expect(storage.getItem(draftKey(made.id as string))).toBeNull();
    expect(idx(storage).activeId).toBe(firstId);
  });

  it("delete of the last character creates an empty one and makes it active", () => {
    const { env, storage, boot, firstId } = twoCharacters();
    const r = deleteCharacter(env, boot.library, firstId);
    const ids = Object.keys(r.library.items);
    expect(ids).toHaveLength(1);
    expect(ids[0]).not.toBe(firstId);
    expect(r.library.activeId).toBe(ids[0]);
    expect(r.draft?.classes).toEqual([]);
    expect(storage.getItem(draftKey(firstId))).toBeNull();
    expect(stored(storage, ids[0]).classes).toEqual([]);
  });

  it("deleting everything never leaves an unknown activeId", () => {
    const { env, boot } = twoCharacters();
    let lib = boot.library;
    for (let i = 0; i < 3; i++) lib = deleteCharacter(env, lib, lib.activeId).library;
    expect(lib.items[lib.activeId]).toBeDefined();
  });
});

describe("storage failure and corruption", () => {
  it("a failing write of one character does not corrupt the index or the other characters", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const b = bootLibrary(h.env);
    const made = createCharacter(h.env, b.library);
    const indexBefore = h.storage.getItem(LIBRARY_KEY);
    h.storage.failKeys.add(draftKey(made.id as string));
    const r = saveDraft(h.env, made.library, made.id as string, draftOf("Нов", [["bard", 2]]));
    expect(r.ok).toBe(false);
    // index is parseable, lists both, and was not changed by the failed save
    expect(h.storage.getItem(LIBRARY_KEY)).toBe(indexBefore);
    expect(Object.keys(idx(h.storage).items)).toHaveLength(2);
    expect(stored(h.storage, b.library.activeId).classes[0].classId).toBe("warlock");
    // after the quota recovers, boot is consistent
    h.storage.failKeys.clear();
    const again = bootLibrary(h.env);
    expect(Object.keys(again.library.items)).toHaveLength(2);
  });

  it("creating a character when the draft key fails keeps the in-memory item, reports failure, boot stays sane", () => {
    const h = makeEnv(undefined, ["a", "b"]);
    const b = bootLibrary(h.env);
    h.storage.failKeys.add(draftKey("b"));
    const r = createCharacter(h.env, b.library);
    expect(r.ok).toBe(false);
    expect(r.library.items["b"]).toBeDefined();
    h.storage.failKeys.clear();
    const again = bootLibrary(h.env);
    expect(again.library.items["a"]).toBeDefined();
    expect(Object.keys(again.library.items).length).toBeGreaterThanOrEqual(1);
  });

  it("a corrupt item is backed up, isolated and noticed at boot; the others load", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const b = bootLibrary(h.env);
    const second = createCharacter(h.env, b.library);
    const third = createCharacter(h.env, second.library);
    h.storage.setItem(draftKey(second.id as string), "{broken");
    const again = bootLibrary(h.env);
    expect(Object.keys(again.library.items)).toHaveLength(3);
    expect(h.storage.getItem(backupKey(second.id as string))).toBe("{broken");
    expect(again.notices.join(" ")).toContain("повредена");
    expect(again.library.activeId).toBe(third.id);
    const list = summarize(h.env, again.library);
    expect(list).toHaveLength(3);
    expect(list.find((s) => s.id === b.library.activeId)?.totalLevel).toBe(7);
    expect(list.find((s) => s.id === second.id)?.totalLevel).toBe(0);
  });

  it("a corrupt ACTIVE item loads empty, keeps its name, backs up, and notices", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const b = bootLibrary(h.env);
    h.storage.setItem(draftKey(b.library.activeId), "[]x");
    const again = bootLibrary(h.env);
    expect(again.draft.classes).toEqual([]);
    expect(again.draft.name).toBe("Зара");
    expect(h.storage.getItem(backupKey(b.library.activeId))).toBe("[]x");
    expect(again.notices).toHaveLength(1);
  });

  it("a corrupt item whose backup fails is left untouched (no data loss) and noticed", () => {
    const h = makeEnv();
    const b = bootLibrary(h.env);
    const second = createCharacter(h.env, b.library);
    h.storage.setItem(draftKey(b.library.activeId), "{broken");
    h.storage.failKeys.add(backupKey(b.library.activeId));
    const again = bootLibrary(h.env);
    expect(h.storage.getItem(draftKey(b.library.activeId))).toBe("{broken");
    expect(again.notices.join(" ")).toContain("НЕ можа");
    expect(again.library.activeId).toBe(second.id);
    expect(summarize(h.env, again.library).find((s) => s.id === b.library.activeId)?.status).toBe("corrupt");
  });

  it("an unreadable library index is backed up and rebuilt from the draft keys", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const b = bootLibrary(h.env);
    createCharacter(h.env, b.library);
    h.storage.setItem(LIBRARY_KEY, "garbage");
    const again = bootLibrary(h.env);
    expect(h.storage.getItem(LIBRARY_BACKUP_KEY)).toBe("garbage");
    expect(Object.keys(again.library.items)).toHaveLength(2);
    expect(again.notices.join(" ")).toContain("библиотеката");
    expect(again.library.items[again.library.activeId]).toBeDefined();
  });

  it("a library written by a newer version is not overwritten: backed up, then rebuilt", () => {
    const h = makeEnv();
    h.storage.setItem(LIBRARY_KEY, JSON.stringify({ version: 2, activeId: "x", items: {} }));
    const b = bootLibrary(h.env);
    expect(h.storage.getItem(LIBRARY_BACKUP_KEY)).toContain('"version":2');
    expect(Object.keys(b.library.items)).toHaveLength(1);
  });

  it("an index whose activeId is unknown falls back to an existing item", () => {
    const h = makeEnv();
    const b = bootLibrary(h.env);
    const broken = { ...idx(h.storage), activeId: "ghost" };
    h.storage.setItem(LIBRARY_KEY, JSON.stringify(broken));
    const again = bootLibrary(h.env);
    expect(again.library.activeId).toBe(b.library.activeId);
  });

  it("an index item without a draft key loads as an empty character with its name", () => {
    const h = makeEnv();
    const b = bootLibrary(h.env);
    saveDraft(h.env, b.library, b.library.activeId, draftOf("Тихо"));
    h.storage.removeItem(draftKey(b.library.activeId));
    const again = bootLibrary(h.env);
    expect(again.draft.name).toBe("Тихо");
    expect(again.notices).toEqual([]);
  });

  it("legacy key is never removed while it is an unreadable text without a backup", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, "{bad");
    h.storage.failKeys.add(LEGACY_BACKUP_KEY);
    const b = bootLibrary(h.env);
    createCharacter(h.env, b.library);
    expect(h.storage.getItem(LEGACY_DRAFT_KEY)).toBe("{bad");
  });

  it("activeDraftRaw / resetActiveDraft work for the library and for a bare legacy key", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, "legacy");
    expect(activeDraftRaw(h.storage)).toBe("legacy");
    const h2 = makeEnv();
    const boot = bootLibrary(h2.env);
    expect(activeDraftRaw(h2.storage)).toContain('"draftVersion"');
    resetActiveDraft(h2.storage);
    expect(h2.storage.getItem(draftKey(boot.library.activeId))).toBeNull();
    resetActiveDraft(h.storage);
    expect(h.storage.getItem(LEGACY_DRAFT_KEY)).toBeNull();
  });
});

describe("export and import", () => {
  it("export-all -> import into a fresh library is a round trip (drafts equal, ids new)", () => {
    const a = makeEnv();
    a.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const boot = bootLibrary(a.env);
    const second = createCharacter(a.env, boot.library);
    saveDraft(a.env, second.library, second.id as string, draftOf("Борис", [["fighter", 4], ["wizard", 2]]));
    const lib = { ...second.library, items: { ...second.library.items } };
    const bundle = exportLibrary(a.env, lib);
    expect(bundle.bundle.kind).toBe("dnd-builder-library");
    expect(bundle.bundle.version).toBe(1);
    expect(bundle.bundle.drafts).toHaveLength(2);
    expect(bundle.skipped).toEqual([]);

    const b = makeEnv();
    const fresh = bootLibrary(b.env);
    const r = importDrafts(b.env, fresh.library, JSON.parse(JSON.stringify(bundle.bundle)));
    expect(r.report.filter((e) => e.status === "accepted")).toHaveLength(2);
    const names = Object.values(r.library.items).map((i) => i.name).sort();
    expect(names).toEqual(["", "Борис", "Зара"].sort());
    const boris = Object.values(r.library.items).find((i) => i.name === "Борис");
    expect(stored(b.storage, boris?.id as string).classes.map((c) => c.classId)).toEqual(["fighter", "wizard"]);
    // import never activates or overwrites the existing character
    expect(r.library.activeId).toBe(fresh.library.activeId);
    expect(Object.keys(r.library.items)).toHaveLength(3);
  });

  it("export uses the live in-memory draft and lists unreadable items as skipped", () => {
    const h = makeEnv();
    const b = bootLibrary(h.env);
    const second = createCharacter(h.env, b.library);
    h.storage.setItem(draftKey(b.library.activeId), "{x");
    const out = exportLibrary(h.env, second.library, { id: second.id as string, draft: draftOf("Живо", [["bard", 1]]) });
    expect(out.bundle.drafts.map((d) => d.name)).toEqual(["Живо"]);
    expect(out.skipped).toHaveLength(1);
  });

  it("bundle import with mixed valid/invalid entries gives a per-item report and adds only the valid", () => {
    const { env, storage } = makeEnv();
    const boot = bootLibrary(env);
    const newer = { ...draftOf("Новичка"), draftVersion: DRAFT_VERSION + 1 };
    const bundle = {
      kind: "dnd-builder-library",
      version: 1,
      drafts: [draftOf("Добър", [["rogue", 3]]), null, 5, { sheet: {} }, newer, draftOf("Втори", [["cleric", 1]])],
    };
    const r = importDrafts(env, boot.library, bundle);
    expect(r.report.map((e) => e.status)).toEqual(["accepted", "rejected", "rejected", "rejected", "rejected", "accepted"]);
    expect(r.report[1].message).toMatch(/чернова/);
    expect(r.report[3].message).toContain("не прилича на чернова");
    expect(r.report[4].message).toContain("по-нова версия");
    expect(r.report[0].name).toBe("Добър");
    expect(Object.keys(r.library.items)).toHaveLength(3);
    expect(idx(storage).items).toBeDefined();
    expect(Object.keys(idx(storage).items)).toHaveLength(3);
  });

  it("ids are regenerated on collision and existing characters are never overwritten", () => {
    // first generated id collides with the existing item "a"
    const h = makeEnv(undefined, ["a", "a", "fresh"]);
    const boot = bootLibrary(h.env);
    expect(boot.library.activeId).toBe("a");
    saveDraft(h.env, boot.library, "a", draftOf("Оригинал", [["monk", 5]]));
    const r = importDrafts(h.env, boot.library, draftOf("Вносен", [["rogue", 1]]));
    expect(r.report[0]).toMatchObject({ status: "accepted", id: "fresh" });
    expect(stored(h.storage, "a").name).toBe("Оригинал");
    expect(stored(h.storage, "fresh").name).toBe("Вносен");
  });

  it("a single draft (not a bundle) is imported as a new character", () => {
    const { env } = makeEnv();
    const boot = bootLibrary(env);
    const r = importDrafts(env, boot.library, draftOf("Сам", [["druid", 2]]));
    expect(r.report).toHaveLength(1);
    expect(r.report[0].status).toBe("accepted");
    expect(Object.keys(r.library.items)).toHaveLength(2);
  });

  it("rejects a non-draft value, a newer bundle, and a bundle without a list", () => {
    const { env } = makeEnv();
    const boot = bootLibrary(env);
    for (const bad of [null, 7, "x", [], { foo: 1 }, { kind: "dnd-builder-library", version: 2, drafts: [] }, { kind: "dnd-builder-library", version: 1 }]) {
      const r = importDrafts(env, boot.library, bad);
      expect(r.report.every((e) => e.status === "rejected"), JSON.stringify(bad)).toBe(true);
      expect(r.report.length).toBeGreaterThan(0);
      expect(Object.keys(r.library.items)).toHaveLength(1);
    }
  });

  it("an import that hits the quota rejects the unsaved entries and leaves the index intact", () => {
    const h = makeEnv(undefined, ["a", "b", "c"]);
    const boot = bootLibrary(h.env);
    h.storage.failKeys.add(draftKey("c"));
    const r = importDrafts(h.env, boot.library, { kind: "dnd-builder-library", version: 1, drafts: [draftOf("Х1"), draftOf("Х2")] });
    expect(r.report.map((e) => e.status)).toEqual(["accepted", "rejected"]);
    expect(r.report[1].message).toContain("пълно");
    expect(r.ok).toBe(false);
    expect(Object.keys(idx(h.storage).items).sort()).toEqual(["a", "b"]);
  });

  it("the imported legacy-era first character is not lost when the import adds the second one", () => {
    const h = makeEnv();
    h.storage.setItem(LEGACY_DRAFT_KEY, legacyRaw(draftOf("Зара", [["warlock", 7]])));
    const boot = bootLibrary(h.env);
    importDrafts(h.env, boot.library, draftOf("Вносен"));
    expect(h.storage.getItem(LEGACY_DRAFT_KEY)).toBeNull();
    expect(stored(h.storage, boot.library.activeId).classes[0].classId).toBe("warlock");
  });
});

describe("summarize", () => {
  it("returns name, class list, total level and updatedAt per item, newest first", () => {
    const h = makeEnv();
    const boot = bootLibrary(h.env);
    saveDraft(h.env, boot.library, boot.library.activeId, draftOf("Първи", [["fighter", 4], ["wizard", 2]]));
    const lib1 = bootLibrary(h.env).library;
    const made = createCharacter(h.env, lib1);
    saveDraft(h.env, made.library, made.id as string, draftOf("Втори", [["bard", 1]]));
    const lib = bootLibrary(h.env).library;
    const list = summarize(h.env, lib);
    expect(list.map((s) => s.name)).toEqual(["Втори", "Първи"]);
    expect(list[1]).toMatchObject({ totalLevel: 6, status: "ok", classes: [{ classId: "fighter", level: 4 }, { classId: "wizard", level: 2 }] });
    expect(list[0].updatedAt).toBeGreaterThan(list[1].updatedAt);
  });
});
