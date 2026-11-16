import { describe, expect, it } from "vitest";

import { resetTarget } from "./resetTarget";

describe("resetTarget (FE-02: the error page's reset goes to Home under the app's base path)", () => {
  it("is /home at the root", () => {
    expect(resetTarget("/")).toBe("/home");
  });
  it("keeps the GitHub Pages sub-path", () => {
    expect(resetTarget("/dnd-character-creator/")).toBe("/dnd-character-creator/home");
  });
  it("copes with a base without a trailing slash and with an empty one", () => {
    expect(resetTarget("/sub")).toBe("/sub/home");
    expect(resetTarget("")).toBe("/home");
    expect(resetTarget(undefined)).toBe("/home");
  });
});
