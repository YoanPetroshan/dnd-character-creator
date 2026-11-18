import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChoicePicker } from "./components/ChoicePicker";
import { FeatDetailBody, type FeatDetailState } from "./components/FeatDetailBody";
import { LanguageProvider } from "./LanguageContext";
import { choice } from "./logic/testFixtures";
import { optionFeatId } from "./logic/optionItems";
import type { Lang } from "./copy";

const render = (lang: Lang, el: ReturnType<typeof createElement>) =>
  renderToStaticMarkup(createElement(LanguageProvider, { initial: lang, children: el }));
const picker = (lang: Lang, c: ReturnType<typeof choice>) =>
  render(lang, createElement(ChoicePicker, { choice: c, onToggle: () => undefined }));

describe("optionFeatId", () => {
  it("maps feat:<idx> to the catalog feat index, nothing else", () => {
    expect(optionFeatId({ id: "feat:tough-xphb", label: "x" })).toBe("tough-xphb");
    expect(optionFeatId({ id: "feat:x:ability-bonus", label: "x" })).toBeNull();
    expect(optionFeatId({ id: "athletics", label: "x" })).toBeNull();
  });
});

describe("description eye in the picker", () => {
  const options = [
    { id: "defense", label: "Defense", description: "While you wear armor, you gain +1 AC." },
    { id: "plain", label: "Plain" },
    { id: "feat:alert", label: "Alert" },
  ];
  it("only options with text or a feat id get an eye, with the option name in the label (bg)", () => {
    const h = picker("bg", choice({ id: "class:fighter:1:fighting-style", options } as never));
    expect(h.match(/class="spell-eye"/g)?.length).toBe(2);
    expect(h).toContain('aria-label="Покажи какво дава: Defense"');
    expect(h).toContain('aria-label="Покажи какво дава: Alert"');
    expect(h).not.toContain("Покажи какво дава: Plain");
    expect(h).not.toContain("While you wear armor"); // closed: nothing inline until opened
  });
  it("the long picker renders the same eyes", () => {
    const many = Array.from({ length: 40 }, (_, i) => ({ id: `o${i}`, label: `O${i}`, description: "Text." }));
    const h = picker("en", choice({ id: "c", options: many } as never));
    expect(h).toContain('aria-label="Show what it gives: O0"');
  });
});

describe("FeatDetailBody", () => {
  it("shows the prerequisite and every paragraph; loading state", () => {
    const state = { status: "ready", feat: { id: "x", name: "X", prerequisite: "Level 4", desc: ["One.", "Two."] } } satisfies FeatDetailState;
    const h = render("en", createElement(FeatDetailBody, { state }));
    for (const s of ["Prerequisite", "Level 4", "One.", "Two."]) expect(h).toContain(s);
    expect(render("bg", createElement(FeatDetailBody, { state }))).toContain("Изискване");
    expect(render("en", createElement(FeatDetailBody, { state: { status: "loading" } }))).toContain("Loading");
  });
});
