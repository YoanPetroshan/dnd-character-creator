import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { DetailEye, DetailPanel } from "./components/DetailEye";
import { FeatureDetailBody, type FeatureDetailState } from "./components/FeatureDetailBody";
import { SubclassPreview, type SubclassDetailState } from "./components/SubclassPreview";
import { LanguageProvider } from "./LanguageContext";
import type { Lang } from "./copy";

const render = (lang: Lang, el: ReturnType<typeof createElement>) =>
  renderToStaticMarkup(createElement(LanguageProvider, { initial: lang, children: el }));

describe("DetailEye", () => {
  it("is a button with the label and aria-expanded; the panel wraps its content", () => {
    const h = render("en", createElement(DetailEye, { label: "Show X", open: true, onToggle: () => undefined }));
    expect(h).toContain('class="spell-eye"');
    expect(h).toContain('aria-label="Show X"');
    expect(h).toContain('aria-expanded="true"');
    expect(render("en", createElement(DetailPanel, null, "Body"))).toContain('class="spell-eye__panel">Body');
  });
});

describe("SubclassPreview", () => {
  const ready = {
    status: "ready",
    value: {
      id: "champion",
      name: "Champion",
      desc: ["Intro text."],
      features: [
        { id: "a", name: "Improved Critical", level: 3, desc: ["Crit on 19."] },
        { id: "b", name: "Remarkable Athlete", level: 3, desc: ["Half proficiency."] },
        { id: "c", name: "Additional Fighting Style", level: 7, desc: ["Pick a style."] },
      ],
    },
  } satisfies SubclassDetailState;
  it("shows the intro, then features grouped by level (bg headings)", () => {
    const h = render("bg", createElement(SubclassPreview, { state: ready }));
    for (const s of ["Intro text.", "Ниво 3", "Ниво 7", "Improved Critical", "Crit on 19.", "Additional Fighting Style"]) expect(h).toContain(s);
    expect(h.match(/Ниво 3/g)?.length).toBe(1);
    expect(h.indexOf("Intro text.")).toBeLessThan(h.indexOf("Ниво 3"));
  });
  it("loading and error", () => {
    expect(render("en", createElement(SubclassPreview, { state: { status: "loading" } }))).toContain("Loading");
    expect(render("en", createElement(SubclassPreview, { state: undefined }))).toContain("Loading");
    const err = render("en", createElement(SubclassPreview, { state: { status: "error", message: { code: "net.offline" } as never } }));
    expect(err).toContain("No connection");
  });
});

describe("FeatureDetailBody", () => {
  const state = {
    status: "ready",
    value: { id: "x", name: "Second Wind", level: 1, className: "Fighter", subclassName: null, desc: ["One.", "Two."] },
  } satisfies FeatureDetailState;
  it("name, class and level line, paragraphs", () => {
    const h = render("bg", createElement(FeatureDetailBody, { state }));
    for (const s of ["Second Wind", "Fighter", "Ниво 1", "One.", "Two."]) expect(h).toContain(s);
  });
  it("loading", () => {
    expect(render("en", createElement(FeatureDetailBody, { state: { status: "loading" } }))).toContain("Loading");
  });
});
