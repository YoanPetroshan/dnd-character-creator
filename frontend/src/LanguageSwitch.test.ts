import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { LanguageSwitch } from "./components/LanguageSwitch";
import { LanguageProvider } from "./LanguageContext";
import { withLang } from "./logic/langQuery";
import type { Lang } from "./copy";

const html = (lang: Lang) =>
  renderToStaticMarkup(createElement(LanguageProvider, { initial: lang, children: createElement(LanguageSwitch) }));

describe("LanguageSwitch", () => {
  it("renders two buttons; bg is pressed in the Bulgarian UI", () => {
    const h = html("bg");
    expect(h).toContain('aria-label="Език"');
    expect(h).toContain('<button type="button" lang="bg" aria-pressed="true" data-state="active">БГ</button>');
    expect(h).toContain('<button type="button" lang="en" aria-pressed="false" data-state="inactive">EN</button>');
  });
  it("en is pressed in the English UI and the labels come from the English catalog", () => {
    const h = html("en");
    expect(h).toContain('aria-label="Language"');
    expect(h).toContain('lang="bg" aria-pressed="false" data-state="inactive">BG</button>');
    expect(h).toContain('lang="en" aria-pressed="true" data-state="active">EN</button>');
  });
});

describe("withLang", () => {
  it("appends ?lang= or &lang=", () => {
    expect(withLang("/api/resolve", "bg")).toBe("/api/resolve?lang=bg");
    expect(withLang("/api/export/pdf", "en")).toBe("/api/export/pdf?lang=en");
    expect(withLang("/api/x?a=1", "en")).toBe("/api/x?a=1&lang=en");
  });
});

describe("requests carry the language", () => {
  it("useResolution and the export bar build their URLs with withLang(…, lang) and re-resolve on lang", () => {
    const res = readFileSync(new URL("./useResolution.ts", import.meta.url)).toString("utf8");
    expect(res).toContain('withLang("/api/resolve", lang)');
    expect(res).toContain("[draft, retryNonce, lang]");
    const exp = readFileSync(new URL("./components/sheetpage/ExportBar.tsx", import.meta.url)).toString("utf8");
    expect(exp).toContain("withLang(config.endpoint, lang)");
  });
});
