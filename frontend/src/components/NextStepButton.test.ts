import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { LanguageProvider } from "../LanguageContext";
import { STEPS } from "../logic/steps";
import { NextStepButton } from "./NextStepButton";

function render(path: string, lang: "bg" | "en"): string {
  return renderToStaticMarkup(
    createElement(
      MemoryRouter,
      { initialEntries: [path] },
      createElement(LanguageProvider, { initial: lang, children: createElement(NextStepButton) }),
    ),
  );
}

describe("NextStepButton", () => {
  it("Bulgarian markup: class, data-next, href and an aria-label naming the target step", () => {
    expect(render("/home", "bg")).toBe('<a class="next-button" data-next="class" aria-label="Напред: Клас" href="/class" data-discover="true">Напред</a>');
    expect(render("/class", "bg")).toContain('data-next="background"');
    expect(render("/class", "bg")).toContain('aria-label="Напред: Произход (Background)"');
  });
  it("English markup", () => {
    expect(render("/home", "en")).toBe('<a class="next-button" data-next="class" aria-label="Next: Class" href="/class" data-discover="true">Next</a>');
    expect(render("/species", "en")).toBe('<a class="next-button" data-next="abilities" aria-label="Next: Abilities" href="/abilities" data-discover="true">Next</a>');
  });
  it("a deep-link hash on the current page does not matter", () => {
    expect(renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: ["/class#class:warlock:1:x"] }, createElement(NextStepButton)))).toContain('data-next="background"');
  });
  it("under a base path the router strips it: the target is found and the href carries it", () => {
    const at = (path: string) => renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [path], basename: "/dnd-character-creator" }, createElement(NextStepButton)));
    expect(at("/dnd-character-creator/species")).toContain('data-next="abilities" aria-label="Напред: Abilities" href="/dnd-character-creator/abilities"');
    expect(at("/dnd-character-creator/sheet")).toBe("");
  });
  it("every step but the last has exactly one button, pointing at the next step", () => {
    STEPS.slice(0, -1).forEach((s, i) => {
      const html = render(s.path, "en");
      expect(html.match(/class="next-button"/g)).toHaveLength(1);
      expect(html).toContain(`href="${STEPS[i + 1].path}"`);
    });
  });
  it("renders nothing on the last step (Sheet), on Help and on an unknown route", () => {
    expect(render("/sheet", "bg")).toBe("");
    expect(render("/help", "en")).toBe("");
    expect(render("/nope", "en")).toBe("");
  });
});
