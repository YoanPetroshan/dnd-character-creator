import { describe, expect, it } from "vitest";
import { backgroundChoicesOf, classChoicesFor, isBackgroundCid, isClassCid, isSpeciesCid, isSpellChoiceId, speciesChoicesOf, splitClassChoices } from "./choiceRouting";
import { choice } from "./testFixtures";

// Every card the server puts on the Class page's "Заклинания" tab.
const SPELL_CIDS = [
  "class:wizard:spells-cantrips",
  "class:bard:spells-known",
  "class:sorcerer:spells-known",
  "class:wizard:spellbook",
  "class:warlock:11:mystic-arcanum-6",
  "class:warlock:13:mystic-arcanum-7",
  "class:wizard:18:spell-mastery-1",
  "class:wizard:18:spell-mastery-2",
  "class:wizard:20:signature-spells",
  "class:bard:10:feature:additional-magical-secrets",
  "class:warlock:1:invocation:opt-pact-of-the-tome-xphb:cantrips",
  "class:warlock:invocation:opt-pact-of-the-tome-xphb:rituals",
  "class:wizard:3:feature:abjurer-xphb-3-abjuration-savant",
  "class:wizard:3:feature:diviner-xphb-3-divination-savant",
  "class:wizard:3:feature:evoker-xphb-3-evocation-savant",
  "class:wizard:3:feature:illusionist-xphb-3-improved-illusions",
  "class:bard:6:feature:lore-xphb-6-magical-discoveries",
];

// Cards that stay on "Способности".
const FEATURE_CIDS = [
  "class:fighter:4:asi",
  "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations",
  "class:warlock:invocation:opt-agonizing-blast-xphb:cantrip",
  "class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon",
  "class:warlock:invocation:opt-lessons-of-the-first-ones-xphb:feat",
  "class:warlock:1:prof-choice-0",
  "class:bard:3:expertise-choice:bard-expertise-1",
  "class:druid:3:feature:land-xphb-3-circle-of-the-land-spells",
  "class:wizard:3:feature:abjurer-xphb-3-abjurer",
  "class:wizard:3:feature:illusionist-xphb-3-illusionist",
  "class:bard:3:feature:lore-xphb-3-bonus-proficiencies",
  "class:wizard:subclass",
  "class:fighter:1:equipment-choice-0",
  "class:fighter:4:asi:feat:0:ability-bonus",
];

describe("isSpellChoiceId", () => {
  it.each(SPELL_CIDS)("spell card %s", (cid) => expect(isSpellChoiceId(cid)).toBe(true));
  it.each(FEATURE_CIDS)("feature card %s", (cid) => expect(isSpellChoiceId(cid)).toBe(false));
  it("the savant pattern is anchored at the end", () => {
    expect(isSpellChoiceId("class:wizard:3:feature:evoker-xphb-3-evocation-savant-extra")).toBe(false);
    expect(isSpellChoiceId("class:wizard:3:feature:evocation-savant")).toBe(true);
  });
  it("spells-known only as a suffix", () => {
    expect(isSpellChoiceId("class:bard:spells-known:more")).toBe(false);
  });
});

describe("cid scoping", () => {
  it("class / species / background prefixes", () => {
    expect(isClassCid("class:fighter:4:asi")).toBe(true);
    expect(isClassCid("feat:alert-xphb:x")).toBe(false);
    expect(isSpeciesCid("species:human:languages")).toBe(true);
    expect(isBackgroundCid("background:acolyte:languages")).toBe(true);
    expect(isBackgroundCid("feat:alert-xphb:x")).toBe(true);
    expect(isBackgroundCid("class:x")).toBe(false);
    expect(isBackgroundCid("species:x")).toBe(false);
  });
});

describe("choice lists", () => {
  const cards = [
    choice({ id: "class:wizard:spells-cantrips" }),
    choice({ id: "class:wizard:spellbook" }),
    choice({ id: "class:wizard:3:asi" }),
    choice({ id: "class:wizard:4:asi:feat:0:x", source: { kind: "feat" } as never }),
    choice({ id: "class:fighter:4:asi" }),
    choice({ id: "background:acolyte:languages", source: { kind: "background" } as never }),
    choice({ id: "feat:alert-xphb:x", source: { kind: "feat" } as never }),
    choice({ id: "species:human:languages", source: { kind: "species" } as never }),
    choice({ id: "species:human:feat:0:x", source: { kind: "feat" } as never }),
    choice({ id: "class:fighter:1:equipment-choice-0", source: { kind: "equipment" } as never }),
  ];
  it("classChoicesFor keeps one class's class and feat cards", () => {
    expect(classChoicesFor(cards, "wizard").map((c) => c.id)).toEqual([
      "class:wizard:spells-cantrips",
      "class:wizard:spellbook",
      "class:wizard:3:asi",
      "class:wizard:4:asi:feat:0:x",
    ]);
  });
  it("does not match a class whose id is a prefix of another", () => {
    expect(classChoicesFor([choice({ id: "class:fighter-x:1:asi" })], "fighter")).toEqual([]);
  });
  it("splitClassChoices puts the spellbook first among the spell cards", () => {
    const { featureChoices, spellChoices } = splitClassChoices(classChoicesFor(cards, "wizard"));
    expect(spellChoices.map((c) => c.id)).toEqual(["class:wizard:spellbook", "class:wizard:spells-cantrips"]);
    expect(featureChoices.map((c) => c.id)).toEqual(["class:wizard:3:asi", "class:wizard:4:asi:feat:0:x"]);
  });
  it("background and species lists", () => {
    expect(backgroundChoicesOf(cards).map((c) => c.id)).toEqual(["background:acolyte:languages", "feat:alert-xphb:x"]);
    expect(speciesChoicesOf(cards).map((c) => c.id)).toEqual(["species:human:languages", "species:human:feat:0:x"]);
  });
});
