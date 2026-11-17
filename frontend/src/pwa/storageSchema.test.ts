import { describe, expect, it } from "vitest";
import { DRAFT_VERSION } from "../logic/draft";
import { DRAFT_KEY_PREFIX, LEGACY_DRAFT_KEY, LIBRARY_KEY, PORTRAIT_KEY_PREFIX } from "../library";
import storageSchema from "../storageSchema.json";

/** What each storage schema number means. The service worker carries the number (dist/sw.js); a page whose number differs from
 *  the waiting version's asks for a backup instead of updating by itself. Whoever changes a storage format must raise
 *  `src/storageSchema.json` by one AND add the new row here; this test is the reminder (it fails on either half alone). */
const FORMATS_BY_SCHEMA: Record<number, Record<string, string | number>> = {
  1: {
    draftVersion: 2,
    libraryKey: "dnd-builder-library-v1",
    draftKeyPrefix: "dnd-builder-draft-v2:",
    legacyDraftKey: "dnd-builder-draft-v2",
    portraitKeyPrefix: "dnd-builder-portrait-v1:",
  },
};

describe("storage schema", () => {
  it("the storage formats in the code are the ones the current schema number stands for", () => {
    const now = {
      draftVersion: DRAFT_VERSION,
      libraryKey: LIBRARY_KEY,
      draftKeyPrefix: DRAFT_KEY_PREFIX,
      legacyDraftKey: LEGACY_DRAFT_KEY,
      portraitKeyPrefix: PORTRAIT_KEY_PREFIX,
    };
    expect(
      FORMATS_BY_SCHEMA[storageSchema.schema],
      "a storage format changed: raise src/storageSchema.json by one and add its row to FORMATS_BY_SCHEMA (docs/DEPLOY-PAGES.md)",
    ).toEqual(now);
  });

  it("the number in the JSON file is the newest row of the table", () => {
    expect(storageSchema.schema).toBe(Math.max(...Object.keys(FORMATS_BY_SCHEMA).map(Number)));
  });
});
