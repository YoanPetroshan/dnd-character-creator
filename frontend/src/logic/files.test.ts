import { describe, expect, it } from "vitest";
import { safeFilename } from "./files";

describe("safeFilename", () => {
  it("uses the name and the extension", () => expect(safeFilename("Гандалф", "pdf")).toBe("Гандалф.pdf"));
  it("falls back to 'character' for an empty or missing name", () => {
    expect(safeFilename("", "yaml")).toBe("character.yaml");
    expect(safeFilename(undefined, "md")).toBe("character.md");
  });
  it("takes the language's fallback word", () => {
    expect(safeFilename("", "pdf", "герой")).toBe("герой.pdf");
    expect(safeFilename(undefined, "md", "character")).toBe("character.md");
    expect(safeFilename("Hero", "md", "герой")).toBe("Hero.md");
  });
  it("replaces every character that is unsafe in a file name", () => {
    expect(safeFilename('a\\b/c:d*e?f"g<h>i|j', "pdf")).toBe("a_b_c_d_e_f_g_h_i_j.pdf");
  });
  it("keeps a compound extension (drafts)", () => expect(safeFilename("Hero", "draft.json")).toBe("Hero.draft.json"));
  it("keeps dots, spaces and non-ASCII", () => expect(safeFilename("Dr. Ünal Bey", "md")).toBe("Dr. Ünal Bey.md"));
});
