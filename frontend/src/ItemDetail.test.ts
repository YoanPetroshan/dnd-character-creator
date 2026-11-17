import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChoicePicker } from "./components/ChoicePicker";
import { ItemDetailBody } from "./components/ItemDetailBody";
import { LanguageProvider } from "./LanguageContext";
import { choice } from "./logic/testFixtures";
import { optionItemIds } from "./logic/optionItems";
import type { Lang } from "./copy";
import type { ItemDetail } from "./useItems";

const base: ItemDetail = {
  id: "x", name: "X", category: "weapon", source: "SRD", ruleset: "2014", cost: null, weight: null, damage: null, twoHandedDamage: null,
  range: null, throwRange: null, properties: [], mastery: null, armor: null, contents: [], desc: [], special: [],
};
const longsword: ItemDetail = {
  ...base, id: "longsword", name: "Longsword", cost: { quantity: 15, unit: "gp" }, weight: 3,
  damage: { dice: "1d8", type: "slashing" }, twoHandedDamage: { dice: "1d10", type: "slashing" }, range: { normal: 5 },
  properties: [{ id: "versatile", name: "Versatile", desc: ["Two hands for the bigger die."] }],
  mastery: { name: "Sap", desc: ["Disadvantage on the next attack."] },
};
const html = (lang: Lang, item: ItemDetail) =>
  renderToStaticMarkup(createElement(LanguageProvider, { initial: lang, children: createElement(ItemDetailBody, { state: { status: "ready", item } }) }));

describe("ItemDetailBody", () => {
  it("a weapon shows cost, weight, damage, versatile dice, range, property and mastery texts (en)", () => {
    const h = html("en", longsword);
    for (const s of ["Weapons", "15 GP", "Weight", "3 lb", "1d8 Slashing", "Two-handed", "1d10", "5 feet", "Versatile", "Two hands for the bigger die.", "Mastery: Sap", "Disadvantage on the next attack."]) {
      expect(h, s).toContain(s);
    }
  });
  it("Bulgarian labels, item names stay English", () => {
    const h = html("bg", longsword);
    for (const s of ["Versatile", "15 зл.", "Тегло", "режещи", "Двуръчно", "Свойства", "Майсторство с оръжия (Weapon Mastery): Sap"]) expect(h, s).toContain(s);
  });
  it("armor shows AC, Dexterity cap, Strength minimum and Stealth Disadvantage", () => {
    const armor: ItemDetail = { ...base, category: "armor", name: "Half Plate", armor: { base: 15, dexBonus: true, maxBonus: 2, strMinimum: 13, stealthDisadvantage: true } };
    const h = html("en", armor);
    expect(h).toContain("15 + Dexterity (max +2)");
    expect(h).toContain("Strength required");
    expect(h).toContain("13");
    expect(h).toContain("Disadvantage");
    expect(html("en", { ...armor, armor: { base: 2, dexBonus: false, maxBonus: null, strMinimum: 0, stealthDisadvantage: false } })).toContain("+2");
  });
  it("a pack lists its contents with quantities", () => {
    const h = html("en", { ...base, category: "adventuring-gear", contents: [{ id: "torch", name: "Torch", qty: 10 }, { id: "bedroll", name: "Bedroll", qty: 1 }] });
    expect(h).toContain("Torch ×10, Bedroll");
  });
  it("desc and special paragraphs are rendered; loading and error states", () => {
    const h = html("en", { ...base, desc: ["First."], special: ["Net rules."] });
    expect(h).toContain("First.");
    expect(h).toContain("Net rules.");
    const loading = renderToStaticMarkup(createElement(LanguageProvider, { initial: "en", children: createElement(ItemDetailBody, { state: { status: "loading" } }) }));
    expect(loading).toContain("Loading");
  });
});

describe("optionItemIds", () => {
  const eq = (id: string) => choice({ id, source: { kind: "equipment", id: "fighter", label: "F" } });
  const opt = (id: string) => ({ id, label: id });
  it("splits a package on + and drops gold and open picks", () => {
    expect(optionItemIds(eq("a"), opt("chain-mail+longsword+gp-4"))).toEqual(["chain-mail", "longsword"]);
    expect(optionItemIds(eq("a"), opt("gp-155"))).toEqual([]);
    expect(optionItemIds(eq("a"), opt("any-martial-weapons+shield"))).toEqual(["shield"]);
    expect(optionItemIds(eq("a"), opt("monk-tool"))).toEqual([]);
  });
  it("weapon mastery choices count, other choices do not", () => {
    expect(optionItemIds(choice({ id: "class:fighter:weapon-mastery" }), opt("longsword"))).toEqual(["longsword"]);
    expect(optionItemIds(choice({ id: "class:fighter:1:skills" }), opt("athletics"))).toEqual([]);
  });
});

describe("item eye in the picker", () => {
  const picker = (c: ReturnType<typeof choice>) =>
    renderToStaticMarkup(createElement(LanguageProvider, { initial: "bg", children: createElement(ChoicePicker, { choice: c, onToggle: () => undefined }) }));
  it("an equipment option with items gets an eye, a gold-only option does not", () => {
    const h = picker(choice({ id: "e", source: { kind: "equipment" }, options: [{ id: "longsword+gp-5", label: "A" }, { id: "gp-155", label: "B" }] } as never));
    expect(h.match(/class="spell-eye"/g)?.length).toBe(1);
    expect(h).toContain('aria-label="Покажи описанието на предмета"');
    expect(h).toContain('aria-expanded="false"');
  });
});
