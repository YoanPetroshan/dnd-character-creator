// The sheet page (/sheet; /export redirects to it): export buttons, summary strip and tabs. Rendered with renderToStaticMarkup
// (there is no DOM in these tests): the markup carries the ARIA attributes, the buttons and every section; the keyboard
// behaviour is the pure function `tabAfterKey` (tested in logic/sheetTabs.test.ts) and was also tried in the real browser.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import bard10 from "../__fixtures__/bard10-2014.json";
import fighter4 from "../__fixtures__/fighter4-2024.json";
import rogue6 from "../__fixtures__/rogue6-2024.json";
import warlock7 from "../__fixtures__/warlock7-2024.json";
import wizard20 from "../__fixtures__/wizard20-2024.json";
import App from "../App";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { DraftProvider } from "../DraftContext";
import { LanguageProvider } from "../LanguageContext";
import { LibraryProvider } from "../LibraryContext";
import { bg, en, type Lang } from "../copy";
import { emptyDraft } from "../logic/draft";
import { exportRedirectTarget } from "../logic/exportRedirect";
import { SHEET_SECTION_KEYS, sheetSections } from "../logic/sheetSections";
import { TAB_IDS } from "../logic/sheetTabs";
import type { Draft, Resolution } from "../types";

process.env.TZ = "UTC";
const cap = vi.hoisted(() => ({ resolution: null as unknown, error: null as unknown }));
vi.mock("../useCatalog", () => ({
  useCatalog: () => ({ classes: [], backgrounds: [], species: [], sources: [], allBackgrounds: [], allSpecies: [], loading: false, error: null, retry: () => undefined }),
}));
vi.mock("../useResolution", () => ({ useResolution: () => ({ resolution: cap.resolution, loading: false, error: cap.error, retry: () => undefined }) }));
vi.mock("../useItems", () => ({ useItems: () => ({ items: [], loading: false, error: null, retry: () => undefined }) }));
vi.mock("../useSpells", async (orig) => ({
  ...(await orig<object>()),
  useSpells: () => ({
    spells: [{ id: "fireball", name: "Fireball", level: 3, school: "Evocation", castingTime: "1 action", range: "150 feet", components: ["V", "S", "M"], duration: "Instantaneous", concentration: false, ritual: false, source: "SRD", ruleset: "2014" }],
    loading: false, error: null, retry: () => undefined,
  }),
}));

const FIXTURES = [warlock7, bard10, fighter4, wizard20, rogue6] as unknown as { id: string; ruleset: string; base: Draft["abilities"]["base"]; resolution: Resolution }[];

function page(resolution: Resolution | null, route: string, lang: Lang = "bg", base?: Draft["abilities"]["base"], error: unknown = null): string {
  cap.resolution = resolution;
  cap.error = error;
  const store = new Map<string, string>();
  const draft = { ...emptyDraft, name: "Тест", ...(base ? { abilities: { method: "manual", base } } : {}) };
  store.set("dnd-builder-draft-v2", JSON.stringify(draft));
  const env = { storage: { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k), keys: () => [...store.keys()] }, now: () => 1_700_000_000_000, newId: () => "id1" };
  return renderToStaticMarkup(
    createElement(MemoryRouter, { initialEntries: [route] }, createElement(LanguageProvider, { initial: lang, children: createElement(ErrorBoundary, null, createElement(LibraryProvider, { env, children: createElement(DraftProvider, null, createElement(App)) })) })),
  );
}

const withProblems = (r: Resolution): Resolution => ({ ...r, problems: [{ id: "unknown-class", message: "Unknown class x" }], choices: [{ id: "class:fighter:4:asi", source: { kind: "class", id: "fighter", label: "Fighter" }, label: "Ability Score Improvement", description: "", count: 2, status: "pending", options: [], selected: [] } as never] });

describe("export buttons", () => {
  it("are exactly two, the fillable sheet first and Markdown second; no YAML and no simple PDF button", () => {
    for (const lang of ["bg", "en"] as const) {
      const html = page(fighter4.resolution as unknown as Resolution, "/sheet", lang);
      const kinds = [...html.matchAll(/data-export="([a-z]+)"/g)].map((m) => m[1]);
      expect(kinds).toEqual(["sheet", "markdown"]);
      const t = lang === "bg" ? bg : en;
      expect(html).toContain(t.exportPage.downloadSheet);
      expect(html.indexOf(t.exportPage.downloadSheet)).toBeLessThan(html.indexOf(t.exportPage.downloadMarkdown));
      expect(html).not.toMatch(/YAML|yaml/);
      expect(html).not.toContain("simple PDF");
      expect(html).not.toContain("простия PDF");
    }
    expect(bg.exportPage.downloadSheet).toBe("Лист за игра (форма)");
    expect(en.exportPage.downloadSheet).toBe("Character sheet (form)");
    expect(bg.exportPage.downloadMarkdown).toBe("Markdown");
  });

  it("are enabled for a ready draft and disabled WITH the reason shown for an unfinished one (never hidden)", () => {
    const ready = page(fighter4.resolution as unknown as Resolution, "/sheet", "en");
    expect(ready).not.toMatch(/data-export="[a-z]+"[^>]*disabled/);
    expect(ready).toContain(en.exportPage.ready);
    expect(ready).not.toContain('id="export-reasons"');
    for (const lang of ["bg", "en"] as const) {
      const t = lang === "bg" ? bg : en;
      const html = page(withProblems(fighter4.resolution as unknown as Resolution), "/sheet", lang);
      expect(html.match(/data-export="[a-z]+"[^>]*disabled=""/g)).toHaveLength(2);
      expect(html).toContain('data-state="disabled"');
      expect(html).toContain('aria-describedby="export-reasons"');
      expect(html).toContain('id="export-reasons"');
      expect(html).toContain("Unknown class x");
      expect(html).toContain(t.exportPage.notReady);
      expect(html).toContain("Ability Score Improvement");
    }
  });

  it("a failed resolve also keeps the buttons disabled", () => {
    const html = page(fighter4.resolution as unknown as Resolution, "/sheet", "en", undefined, { code: "net.offline" });
    expect(html.match(/data-export="[a-z]+"[^>]*disabled=""/g)).toHaveLength(2);
  });
});

describe("tabs (WAI-ARIA)", () => {
  const html = (route: string, lang: Lang = "en") => page(fighter4.resolution as unknown as Resolution, route, lang);

  it("has a tablist with six tabs in order, one selected, roving tabindex and aria-controls pointing at real tabpanels", () => {
    const h = html("/sheet");
    expect(h).toContain('role="tablist"');
    const tabs = [...h.matchAll(/<button[^>]*role="tab"[^>]*>/g)].map((m) => m[0]);
    expect(tabs).toHaveLength(6);
    expect(tabs.map((t) => /data-tab="([a-z]+)"/.exec(t)![1])).toEqual([...TAB_IDS]);
    expect(tabs.filter((t) => t.includes('aria-selected="true"'))).toHaveLength(1);
    expect(tabs.filter((t) => t.includes('tabindex="0"'))).toHaveLength(1);
    expect(tabs.filter((t) => t.includes('tabindex="-1"'))).toHaveLength(5);
    for (const t of tabs) {
      const controls = /aria-controls="([^"]+)"/.exec(t)![1];
      expect(h).toMatch(new RegExp(`role="tabpanel"[^>]*id="${controls}"|id="${controls}"[^>]*role="tabpanel"`));
    }
    expect(h.match(/role="tabpanel"/g)).toHaveLength(6);
    expect(h.match(/role="tabpanel"[^>]*hidden=""/g)).toHaveLength(5);
  });

  it("defaults to Actions; ?tab= selects a tab (a deep link); an unknown value is Actions", () => {
    const selected = (h: string) => /data-tab="([a-z]+)"[^>]*aria-selected="true"|aria-selected="true"[^>]*data-tab="([a-z]+)"/.exec(h)!.slice(1).find(Boolean);
    expect(selected(html("/sheet"))).toBe("actions");
    for (const id of TAB_IDS) expect(selected(html(`/sheet?tab=${id}`))).toBe(id);
    expect(selected(html("/sheet?tab=nope"))).toBe("actions");
    expect(html("/sheet?tab=notes&lang=en")).toContain('data-tab="notes"');
  });

  it("names the tabs: Bulgarian term + English in brackets (T1), English plain", () => {
    expect(Object.values(bg.sheet.tabs).slice(1)).toEqual(["Действия (Actions)", "Заклинания (Spells)", "Екипировка (Inventory)", "Черти и особености (Features & Traits)", "Предистория (Background)", "Бележки (Notes)"]);
    expect(Object.values(en.sheet.tabs).slice(1)).toEqual(["Actions", "Spells", "Inventory", "Features & Traits", "Background", "Notes"]);
    expect(html("/sheet", "bg")).toContain("Действия (Actions)");
  });
});

describe("the old export route", () => {
  it("redirects to /sheet and keeps the query string", () => {
    expect(exportRedirectTarget("?tab=spells&x=1")).toEqual({ pathname: "/sheet", search: "?tab=spells&x=1" });
    expect(exportRedirectTarget("")).toEqual({ pathname: "/sheet", search: "" });
    const app = readFileSync(new URL("../App.tsx", import.meta.url)).toString("utf8");
    expect(app).toMatch(/path="\/export" element=\{<ExportRedirect \/>\}/);
    expect(app).not.toContain("ExportPage");
  });
});

describe("no data is lost: every section of the old sheet / export pages is rendered in some tab", () => {
  it("each fixture: every section key of sheetSections() appears as data-section in at least one tab", () => {
    for (const f of FIXTURES) {
      const keys = sheetSections(f.resolution, f.base).map((s) => s.key);
      const seen = new Set<string>();
      for (const tab of TAB_IDS) {
        for (const m of page(f.resolution, `/sheet?tab=${tab}`, "en", f.base).matchAll(/data-section="([A-Za-z]+)"/g)) seen.add(m[1]);
      }
      expect(keys.filter((k) => !seen.has(k)), f.id).toEqual([]);
    }
    expect(SHEET_SECTION_KEYS.length).toBeGreaterThan(20);
  });

  it("the summary strip is always there: name, class, species, six abilities, HP, AC, initiative, speed, proficiency bonus, passive perception", () => {
    const f = fighter4;
    const h = page(f.resolution as unknown as Resolution, "/sheet?tab=notes", "en", f.base as Draft["abilities"]["base"]);
    expect(h).toContain('data-section="summary"');
    for (const a of ["STR", "DEX", "CON", "INT", "WIS", "CHA"]) expect(h).toContain(`data-summary-ability="${a}"`);
    for (const k of ["name", "class", "species", "hitPoints", "armorClass", "initiative", "speed", "proficiencyBonus", "passivePerception"]) expect(h).toContain(`data-summary="${k}"`);
    expect(h).not.toMatch(/current HP|temp(orary)? HP|inspiration|short rest/i);
  });

  it("spells: one row per spell, grouped by level, with the catalog columns", () => {
    const f = wizard20;
    const h = page(f.resolution as unknown as Resolution, "/sheet?tab=spells", "en", f.base as Draft["abilities"]["base"]);
    expect(h).toContain("data-spell-level=");
    const ids = [...h.matchAll(/data-spell="([^"]+)"/g)].map((m) => m[1]);
    expect(new Set(ids).size).toBe(ids.length);
    expect(h).toContain("Fireball");
  });

  it("features: the ALL / CLASS / SPECIES / FEATS buttons with aria-pressed, ALL pressed by default", () => {
    const h = page(fighter4.resolution as unknown as Resolution, "/sheet?tab=features", "en");
    const buttons = [...h.matchAll(/<button[^>]*data-filter="([a-z]+)"[^>]*>/g)];
    expect(buttons.map((m) => m[1])).toEqual(["all", "class", "species", "feats"]);
    expect(buttons.filter((m) => m[0].includes('aria-pressed="true"')).map((m) => m[1])).toEqual(["all"]);
  });
});

describe("sections grow with their content", () => {
  it("the stylesheets of the sheet page have no max-height / overflow window on content blocks (only the tab list scrolls sideways)", () => {
    const css = readFileSync(new URL("../styles/layout.css", import.meta.url)).toString("utf8");
    const part = css.slice(css.indexOf("/* The sheet page"));
    const rules = [...part.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ sel: m[1].trim(), body: m[2] }));
    for (const r of rules) {
      expect(r.body).not.toMatch(/max-height|overflow-y|overflow:\s*(auto|scroll)/);
      if (/overflow-x/.test(r.body)) expect(r.sel).toBe(".tabs__list");
    }
  });
});
