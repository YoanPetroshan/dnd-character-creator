import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ChoiceCard } from "./components/ChoiceCard";
import { NewChoicesLink } from "./components/NewChoicesLink";
import { LanguageProvider } from "./LanguageContext";
import { NewChoicesContext } from "./NewChoicesContext";
import { choice } from "./logic/testFixtures";
import type { Lang } from "./copy";

const value = (ids: string[]) => ({ ids, has: (id: string) => ids.includes(id) });
const wrap = (lang: Lang, ids: string[], child: ReturnType<typeof createElement>) =>
  renderToStaticMarkup(
    createElement(
      MemoryRouter,
      null,
      createElement(LanguageProvider, { initial: lang, children: createElement(NewChoicesContext.Provider, { value: value(ids), children: child }) }),
    ),
  );
const card = (status: "pending" | "resolved") =>
  createElement(ChoiceCard, { choice: choice({ id: "class:fighter:5:asi", label: "ASI", status }), onToggle: () => undefined });

describe("new-choice markup (SK8)", () => {
  it("a new pending card carries data-new and the marker (bg: ново, en: new)", () => {
    const bgHtml = wrap("bg", ["class:fighter:5:asi"], card("pending"));
    expect(bgHtml).toContain('data-new="true"');
    expect(bgHtml).toContain('<span class="choice-card__new">ново</span>');
    expect(wrap("en", ["class:fighter:5:asi"], card("pending"))).toContain('<span class="choice-card__new">new</span>');
  });
  it("an acknowledged or resolved card has neither", () => {
    expect(wrap("bg", [], card("pending"))).not.toContain("data-new");
    expect(wrap("bg", ["class:fighter:5:asi"], card("resolved"))).not.toContain("data-new");
    expect(wrap("bg", [], card("pending"))).not.toContain("choice-card__new");
  });
  it("the header link counts the new cards and points at the first one", () => {
    const h = wrap("bg", ["class:fighter:5:asi", "class:fighter:6:x"], createElement(NewChoicesLink));
    expect(h).toContain("Нови избори: 2");
    expect(h).toContain('href="/class#class:fighter:5:asi"');
    expect(wrap("en", ["species:x"], createElement(NewChoicesLink))).toContain("New choices: 1");
    expect(wrap("bg", [], createElement(NewChoicesLink))).toBe("");
  });
});
