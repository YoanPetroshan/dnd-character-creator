// The web app manifest, the icons, index.html's PWA tags, the Help/install copy and the PWA components' hooks.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { bg, en } from "../copy";

const root = (p: string) => new URL(`../../${p}`, import.meta.url);
const text = (p: string) => readFileSync(root(p)).toString("utf8");
const manifest = JSON.parse(text("public/manifest.webmanifest")) as Record<string, any>;
const tokens = text("src/styles/tokens.css");
const token = (name: string) => new RegExp(`${name}:\\s*(#[0-9a-fA-F]{3,6})`).exec(tokens)![1].toLowerCase();

/** width and height of a PNG from its IHDR chunk */
function pngSize(p: string): [number, number] {
  const b = readFileSync(root(p));
  expect([...b.slice(0, 8)]).toEqual([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const u32 = (o: number) => ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0;
  return [u32(16), u32(20)];
}

describe("web app manifest", () => {
  it("names the app in Bulgarian, is standalone and starts at the app's own folder (relative, any sub-path)", () => {
    expect(manifest.name).toBe("Конструктор на герои");
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.short_name.length).toBeLessThanOrEqual(12);
    expect(manifest.lang).toBe("bg");
    expect(manifest.display).toBe("standalone");
    for (const key of ["start_url", "scope", "id"]) {
      expect(manifest[key], key).toBe("./");
    }
  });

  it("takes its colours from the design tokens", () => {
    expect(manifest.theme_color.toLowerCase()).toBe(token("--color-accent"));
    expect(manifest.background_color.toLowerCase()).toBe(token("--color-page"));
    expect(text("index.html")).toContain(`<meta name="theme-color" content="${manifest.theme_color}"`);
  });

  it("has the 192 and 512 icons, any and maskable, relative paths that exist with the declared size", () => {
    const wanted = ["192x192:any", "512x512:any", "192x192:maskable", "512x512:maskable"];
    expect(manifest.icons.map((i: any) => `${i.sizes}:${i.purpose}`).sort()).toEqual([...wanted].sort());
    for (const icon of manifest.icons) {
      expect(icon.src).not.toMatch(/^(\/|[a-z]+:)/i);
      expect(icon.type).toBe("image/png");
      const [w, h] = icon.sizes.split("x").map(Number);
      expect(pngSize(`public/${icon.src}`)).toEqual([w, h]);
    }
  });

  it("has the 180x180 apple-touch-icon", () => {
    expect(pngSize("public/icons/apple-touch-icon.png")).toEqual([180, 180]);
  });
});

describe("index.html", () => {
  const html = text("index.html");
  it("links the manifest and the icons and carries the iOS standalone tags", () => {
    expect(html).toContain('<link rel="manifest" href="/manifest.webmanifest" />'); // vite prefixes the build's base path
    expect(html).toContain('<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />');
    expect(html).toContain('<meta name="apple-mobile-web-app-capable" content="yes" />');
    expect(html).toContain('<meta name="apple-mobile-web-app-title"');
    expect(html).toContain("viewport-fit=cover");
  });
});

describe("Help / install and PWA copy", () => {
  const phases = ["idle", "unsupported", "installing", "offline-ready", "update-available", "error"];
  it("has a status text for every phase, in both languages", () => {
    for (const c of [bg, en]) for (const p of phases) expect(c.help.status[p], p).toBeTruthy();
  });
  it("explains the iPhone Safari steps and the 7-day eviction with a backup reminder, in both languages", () => {
    expect(en.help.iosSteps.join(" ")).toMatch(/Safari/);
    expect(en.help.iosSteps.join(" ")).toMatch(/Share/);
    expect(en.help.iosSteps.join(" ")).toMatch(/Add to Home Screen/);
    expect(bg.help.iosSteps.join(" ")).toMatch(/Safari/);
    expect(bg.help.iosSteps.join(" ")).toMatch(/началния екран/);
    expect(en.help.keepText).toMatch(/7 days/);
    expect(bg.help.keepText).toMatch(/7 дни/);
    expect(en.help.keepLink).toMatch(/Home/);
    expect(bg.help.keepLink).toMatch(/Home/);
  });
  it("the engine-unavailable text names WebAssembly / Lockdown Mode in both languages", () => {
    expect(bg.status.engineUnavailable).toMatch(/Lockdown Mode/);
    expect(en.status.engineUnavailable).toMatch(/Lockdown Mode/);
  });
  it("the Bulgarian texts are Bulgarian (Cyrillic) and the English ones are not", () => {
    const strings = (o: unknown): string[] => (typeof o === "string" ? [o] : o && typeof o === "object" ? Object.values(o).flatMap(strings) : []);
    for (const s of [...strings(bg.help), ...strings(bg.pwa)]) expect(s).toMatch(/[Ѐ-ӿ]/);
    for (const s of [...strings(en.help), ...strings(en.pwa)]) expect(s).not.toMatch(/[Ѐ-ӿ]/);
  });
});

describe("PWA components carry state in data attributes only", () => {
  const banner = text("src/components/StatusBanner.tsx");
  const help = text("src/pages/HelpPage.tsx");
  it("the banner lines have data-state hooks and no inline style", () => {
    for (const state of ["engine-unavailable", "pwa-installing", "update-available", "offline-ready"]) expect(banner).toContain(`data-state="${state}"`);
    expect(banner + help).not.toMatch(/style=\{/);
  });
  it("the update prompt activates the new version only from a button press", () => {
    expect(banner).toMatch(/<button type="button" onClick=\{\(\) => pwa\(\)\.applyUpdate\(\)\}>/);
    expect(banner.match(/applyUpdate/g)).toHaveLength(1);
  });
  it("the Help page is routed and linked from the header", () => {
    const app = text("src/App.tsx");
    expect(app).toContain('<Route path="/help" element={<HelpPage />} />');
    expect(app).toContain('<NavLink className="help-link" to="/help">');
  });
  it("the router and the service worker follow the build's base path", () => {
    expect(text("src/main.tsx")).toContain("<BrowserRouter basename={import.meta.env.BASE_URL}>");
    expect(text("src/pwa/pwaStore.ts")).toContain("swUrl: `${base}sw.js`");
  });
});
