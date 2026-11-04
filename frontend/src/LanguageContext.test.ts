import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LANG_KEY, LanguageProvider, readLang, useLang, useT } from "./LanguageContext";

const store = (v: string | null) => ({ getItem: (k: string) => (k === LANG_KEY ? v : null) });

describe("readLang", () => {
  it("uses the key dnd-builder-lang-v1 and defaults to bg", () => {
    expect(LANG_KEY).toBe("dnd-builder-lang-v1");
    expect(readLang(store(null))).toBe("bg");
    expect(readLang(store("bg"))).toBe("bg");
    expect(readLang(store("en"))).toBe("en");
  });
  it("ignores anything else and a storage that throws", () => {
    expect(readLang(store("de"))).toBe("bg");
    expect(readLang(store(""))).toBe("bg");
    expect(readLang({ getItem: () => { throw new Error("blocked"); } })).toBe("bg");
  });
});

function Probe() {
  const t = useT();
  const { lang } = useLang();
  return createElement("p", null, `${lang}:${t.nav.steps.class}`);
}

describe("LanguageProvider", () => {
  it("serves the catalog of the active language; without a provider the default (bg) applies", () => {
    expect(renderToStaticMarkup(createElement(Probe))).toBe("<p>bg:Клас</p>");
    expect(renderToStaticMarkup(createElement(LanguageProvider, { initial: "en", children: createElement(Probe) }))).toBe("<p>en:Class</p>");
    expect(renderToStaticMarkup(createElement(LanguageProvider, { initial: "bg", children: createElement(Probe) }))).toBe("<p>bg:Клас</p>");
  });
});
