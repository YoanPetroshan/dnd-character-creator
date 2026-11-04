import { readFileSync, readdirSync, statSync } from "node:fs";
import { describe, expect, it } from "vitest";

const SRC = new URL("./", import.meta.url);

function files(dir: URL, ext: string): URL[] {
  const out: URL[] = [];
  for (const name of readdirSync(dir)) {
    const u = new URL(name + (statSync(new URL(name, dir)).isDirectory() ? "/" : ""), dir);
    if (name === "node_modules" || name === "__snapshots__") continue;
    if (u.pathname.endsWith("/")) out.push(...files(u, ext));
    else if (name.endsWith(ext) && !name.endsWith(".test.ts")) out.push(u);
  }
  return out;
}
const text = (u: URL) => readFileSync(u).toString("utf8");

describe("theming hooks (SK7)", () => {
  const tsx = files(SRC, ".tsx");
  const cssFiles = files(SRC, ".css");
  const css = cssFiles.map(text).join("\n").replace(/\/\*[\s\S]*?\*\//g, "");

  it("no inline style objects in the sources", () => {
    expect(tsx.filter((f) => /style=\{\{/.test(text(f))).map((f) => f.pathname)).toEqual([]);
  });

  it("every class used in TSX exists in some stylesheet", () => {
    const have = new Set([...css.matchAll(/\.([A-Za-z_][\w-]*)/g)].map((m) => m[1]));
    const missing = new Set<string>();
    for (const f of tsx) {
      for (const m of text(f).matchAll(/className=(?:"([^"]*)"|\{([^}]*)\})/g)) {
        const literals = m[1] !== undefined ? [m[1]] : [...m[2].matchAll(/"([^"]*)"/g)].map((x) => x[1]);
        for (const lit of literals) for (const c of lit.split(/\s+/).filter(Boolean)) if (!have.has(c)) missing.add(`${c} (${f.pathname.split("/src/")[1]})`);
      }
    }
    expect([...missing]).toEqual([]);
  });

  it("index.css only imports the split stylesheets, tokens first, and each file is imported", () => {
    const idx = text(new URL("./index.css", import.meta.url));
    const imports = [...idx.matchAll(/@import "\.\/styles\/([\w-]+)\.css";/g)].map((m) => m[1]);
    expect(imports[0]).toBe("tokens");
    expect(idx.replace(/@import "[^"]+";\s*/g, "").trim()).toBe("");
    const onDisk = readdirSync(new URL("./styles/", import.meta.url)).filter((n) => n.endsWith(".css")).map((n) => n.replace(".css", ""));
    expect([...imports].sort()).toEqual(onDisk.sort());
  });

  it("tokens are defined once on :root and the other stylesheets use them without redefining", () => {
    const tokens = text(new URL("./styles/tokens.css", import.meta.url));
    const defined = new Set([...tokens.matchAll(/(--[\w-]+):/g)].map((m) => m[1]));
    for (const f of cssFiles.filter((u) => !u.pathname.endsWith("/tokens.css"))) {
      const t = text(f);
      expect([...t.matchAll(/^\s*(--[\w-]+):/gm)], f.pathname).toEqual([]);
      for (const m of t.matchAll(/var\((--[\w-]+)\)/g)) expect(defined.has(m[1]), `${m[1]} in ${f.pathname}`).toBe(true);
    }
  });

  it("the 44px touch-target rule of the language switch is in the stylesheets", () => {
    expect(css).toMatch(/\.lang-switch button \{[^}]*min-width: 44px;[^}]*min-height: 44px;/);
  });
});
