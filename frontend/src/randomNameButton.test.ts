// The dice button next to the character name (N1): source-level checks (the project has no DOM test library;
// the click itself is covered in the browser).
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { bg, en } from "./copy";

const read = (p: string) => readFileSync(new URL(p, import.meta.url)).toString("utf8");

describe("random-name dice button", () => {
  const home = read("./pages/HomePage.tsx");
  it("is a type=button that dispatches SET_NAME with randomName(lang, Math.random)", () => {
    expect(home).toMatch(/<button\s+type="button"\s+className="name-dice"\s+aria-label=\{t\.home\.randomName\}/);
    expect(home).toContain('dispatch({ type: "SET_NAME", name: randomName(lang, Math.random) })');
  });
  it("has a bilingual accessible name and a 44px rule", () => {
    expect(bg.home.randomName).toMatch(/[А-Яа-я]/);
    expect(en.home.randomName).toBe("Random name");
    expect(read("./styles/touch.css")).toMatch(/\.name-dice,[^{]*\{[^}]*min-height: 44px;[^}]*min-width: 44px;/);
  });
});
