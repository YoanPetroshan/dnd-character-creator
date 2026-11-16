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

describe("safeFilename follows the server's download name rules (FE-10, API-05)", () => {
  it("drops control and bidi-override characters", () => {
    expect(safeFilename("a\u0000b\u001bc\u202ed\u2066e\u2069f\u007fg", "pdf")).toBe("abcdefg.pdf");
  });
  it("removes trailing dots and spaces, and uses the fallback when nothing is left", () => {
    expect(safeFilename("Torvin. . ", "md")).toBe("Torvin.md");
    expect(safeFilename("...", "md")).toBe("character.md");
    expect(safeFilename("   ", "md", "герой")).toBe("герой.md");
  });
  it("prefixes a reserved Windows device name with an underscore", () => {
    expect(safeFilename("CON", "md")).toBe("_CON.md");
    expect(safeFilename("com1", "md")).toBe("_com1.md");
    expect(safeFilename("LPT9", "md")).toBe("_LPT9.md");
    expect(safeFilename("Console", "md")).toBe("Console.md");
  });
  it("cuts the name to 200 characters", () => {
    expect(safeFilename("N".repeat(5000), "md")).toBe("N".repeat(200) + ".md");
  });
});
