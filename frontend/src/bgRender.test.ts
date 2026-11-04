// BG render guard (SK6-BI): the Bulgarian UI must stay byte-identical while the copy moves into the
// catalog. Every main route is rendered with renderToStaticMarkup for several states (the fixture
// characters, an empty/loading app, a failed resolve, a "busy" synthetic state with choices, problems,
// warnings, notices ...) and compared with the snapshot captured BEFORE the conversion
// (src/__snapshots__/bg-render.json.gz, full HTML including aria-label / placeholder / title).
// The snapshot is only rewritten on purpose: UPDATE_BG_RENDER=1 npx vitest run src/bgRender.test.ts
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { gunzipSync, gzipSync } from "node:zlib";
import { describe, expect, it, vi } from "vitest";
import bard10 from "./__fixtures__/bard10-2014.json";
import fighter4 from "./__fixtures__/fighter4-2024.json";
import rogue6 from "./__fixtures__/rogue6-2024.json";
import warlock7 from "./__fixtures__/warlock7-2024.json";
import wizard20 from "./__fixtures__/wizard20-2024.json";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DraftProvider } from "./DraftContext";
import { LibraryProvider } from "./LibraryContext";
import { emptyDraft } from "./logic/draft";
import type { LibraryEnv } from "./library";
import type { Draft } from "./types";

process.env.TZ = "UTC";

interface Cap {
  catalog: unknown;
  resolution: unknown;
  error: string | null;
  loading: boolean;
  items: unknown[];
}
const cap = vi.hoisted(() => ({ cur: null as unknown as Cap }));

vi.mock("./useCatalog", () => ({
  useCatalog: () => ({ ...(cap.cur.catalog as object), retry: () => undefined }),
}));
vi.mock("./useResolution", () => ({
  useResolution: () => ({ resolution: cap.cur.resolution, loading: cap.cur.loading, error: cap.cur.error, retry: () => undefined }),
}));
vi.mock("./useItems", () => ({
  useItems: () => ({ items: cap.cur.items, loading: false, error: cap.cur.error ? "Elements failed" : null, retry: () => undefined }),
}));
vi.mock("./useSpells", async (orig) => ({
  ...(await orig<object>()),
  useSpells: () => ({ spells: [], loading: false, error: null, retry: () => undefined }),
}));

const ROUTES = ["/home", "/class", "/background", "/species", "/abilities", "/equipment", "/sheet", "/export"];

interface Fixture {
  id: string;
  ruleset: string;
  base: Record<string, number>;
  resolution: any;
}
const FIXTURES = [warlock7, bard10, fighter4, wizard20, rogue6] as unknown as Fixture[];

function draftOf(f: Fixture, name: string): Draft {
  const s = f.resolution.sheet;
  return {
    ...emptyDraft,
    name,
    ruleset: f.ruleset as Draft["ruleset"],
    classes: s.classes.map((c: any) => ({ classId: c.id, level: c.level, choices: {}, ...(c.subclass ? { subclassId: c.subclass.id } : {}) })),
    species: { id: s.species.id, choices: {} },
    background: { id: s.background.id, choices: {} },
    abilities: { method: "standard", base: f.base as Draft["abilities"]["base"] },
  } as Draft;
}

const CATALOG = {
  classes: [
    { id: "fighter", name: "Fighter", hitDie: 10 },
    { id: "rogue", name: "Rogue", hitDie: 8 },
    { id: "warlock", name: "Warlock", hitDie: 8 },
    { id: "wizard", name: "Wizard", hitDie: 6 },
    { id: "bard", name: "Bard", hitDie: 8 },
  ],
  backgrounds: [
    { id: "acolyte", name: "Acolyte", source: "SRD" },
    { id: "soldier-xphb", name: "Soldier", source: "XPHB" },
  ],
  species: [
    { id: "human", name: "Human", subspecies: [] },
    { id: "human-xphb", name: "Human (XPHB)", subspecies: [{ id: "sub-a", name: "Sub A" }] },
  ],
  sources: [
    { id: "srd", name: "System Reference Document", count: 20 },
    { id: "phb", name: "Player's Handbook", count: 30 },
    { id: "xphb", name: "Player's Handbook (2024)", count: 40 },
  ],
  allBackgrounds: [
    { id: "acolyte", name: "Acolyte", source: "SRD" },
    { id: "soldier-xphb", name: "Soldier", source: "XPHB" },
    { id: "sage", name: "Sage", source: "PHB" },
  ],
  allSpecies: [
    { id: "human", name: "Human", subspecies: [] },
    { id: "human-xphb", name: "Human (XPHB)", subspecies: [{ id: "sub-a", name: "Sub A" }] },
    { id: "elf", name: "Elf", subspecies: [{ id: "high", name: "High Elf" }] },
  ],
  loading: false,
  error: null,
};

const ITEMS = [
  { id: "longsword", name: "Longsword", category: "weapon" },
  { id: "backpack", name: "Backpack", category: "adventuring-gear" },
];

function option(i: number, over: Record<string, unknown> = {}) {
  return { id: `opt-${i}`, label: `Option ${i}`, ...over };
}

function busyResolution(): any {
  const base = structuredClone(fighter4.resolution) as any;
  const longOptions = Array.from({ length: 36 }, (_, i) =>
    option(i, {
      label: `Feat ${i}${i % 3 === 0 ? " (XPHB)" : i % 3 === 1 ? " (PHB)" : ""}`,
      group: i < 12 ? "asi" : i < 24 ? "general" : i < 30 ? "origin" : "spell-level-1",
      ...(i === 5 ? { disabled: true, disabledReason: "Reason five" } : {}),
      ...(i === 7 ? { hiddenByFilters: true } : {}),
    }),
  );
  base.choices = [
    {
      id: "class:fighter:1:fighting-style", source: { kind: "class", id: "fighter", label: "Fighter", level: 1 }, label: "Fighting Style",
      description: "Pick a style.", count: 1, status: "resolved",
      options: [option(1), option(2, { disabled: true, disabledReason: "Needs more" }), option(3, { hiddenByFilters: true }), option(4)], selected: [],
      granted: [{ id: "g1", label: "Granted A" }],
    },
    {
      id: "class:fighter:4:asi", source: { kind: "class", id: "fighter", label: "Fighter", level: 4 }, label: "Ability Score Improvement",
      description: "Long list.", count: 2, status: "pending", options: longOptions, selected: ["opt-1", "opt-13"],
    },
    {
      id: "class:fighter:1:spells-known", source: { kind: "class", id: "fighter", label: "Fighter" }, label: "Spells",
      description: "Spells.", count: 1, status: "pending", options: [option(1)], selected: [],
    },
    {
      id: "background:soldier-xphb:skills", source: { kind: "background", id: "soldier-xphb", label: "Soldier" }, label: "Background skills",
      description: "Pick skills.", count: 2, status: "pending",
      options: Array.from({ length: 24 }, (_, i) => option(i, { label: `Skill ${i}`, ...(i === 3 ? { disabled: true, disabledReason: "Taken" } : {}), ...(i === 4 ? { hiddenByFilters: true } : {}), ...(i < 2 ? { group: "origin" } : i < 4 ? { group: "any-school" } : {}) })), selected: ["opt-2"],
    },
    {
      id: "species:human-xphb:language", source: { kind: "species", id: "human-xphb", label: "Human" }, label: "Language",
      description: "Pick a language.", count: 1, status: "unavailable", unavailableReason: "Nothing here.", options: [], selected: [],
    },
    {
      id: "class:fighter:1:equipment-choice-1", source: { kind: "equipment", id: "fighter", label: "Fighter" }, label: "Starting equipment",
      description: "Pick a package.", count: 1, status: "pending", options: [option(1, { label: "Package A" }), option(2, { label: "Package B" })], selected: [],
    },
    {
      id: "feat:0:ability", source: { kind: "feat", id: "alert", label: "Alert" }, label: "Alert ability",
      description: "Optional.", count: 1, status: "pending", optional: true, options: [option(1)], selected: [],
    },
  ];
  base.problems = [
    { id: "unknown-class", message: "Unknown class x" },
    { id: "unknown-background", message: "Unknown background y" },
    { id: "unknown-species", message: "Unknown species z" },
    { id: "point-buy-over-budget", message: "Over budget" },
    { id: "over-selected-weapons", message: "Too many" },
    { id: "something-else", message: "Export-only problem" },
  ];
  base.warnings = [
    { id: "ruleset-mismatch", message: "Ruleset warning" },
    { id: "hp-roll-invalid-fighter-2", message: "Roll invalid" },
    { id: "plain-warning", message: "Plain warning" },
  ];
  base.pruned = [
    { choiceId: "class:fighter:1:fighting-style", reason: "Pruned reason A" },
    { choiceId: "class:fighter:subclass", reason: "Pruned subclass" },
  ];
  base.derived = {
    ...base.derived,
    hitPointMax: 37,
    attacksPerAction: 2,
    attacks: [
      { itemId: "longsword", name: "Longsword", attackBonus: 5, damage: "1d8+3", damageType: "slashing", versatileDamage: "1d10+3", duelingDamage: "1d8+5", offhandDamage: "1d8", range: "5 ft.", notes: ["Heavy", "Light"], mastery: "Sap" },
      { itemId: "dagger", name: "Dagger", attackBonus: -1, notes: [] },
    ],
    classResources: [
      { id: "rage", classId: "fighter", name: "Rage", uses: 3, recharge: "long", bonus: 2, details: { damageBonus: 2, resistances: ["bludgeoning", "piercing"], note: "A note" } },
      { id: "ki", classId: "monk", name: "Ki", pool: 5, dc: 13, recharge: "short-or-long", details: { shortRestRegains: 2, spellSlotRegainsUse: true, bonusActionRegainsOne: true, onShortRest: true, maxSlotLevel: 3, slotCosts: { 1: 2, 3: 5 }, damageTypes: "fire, cold", knownForms: 4, fly: true, swim: true, metamagic: [{ name: "Quickened", cost: 2 }], perRageOptions: [{ name: "Bear", effect: "resist" }], maxCr: "1/2", heal: "1d6" } },
      { id: "second-wind", classId: "fighter", name: "Second Wind", unlimited: true, die: "d10", dice: "2d6", recharge: "other" },
    ],
    featResources: [{ id: "lucky", name: "Lucky", uses: 3, recharge: "turn" }],
    speciesResources: [{ id: "breath", name: "Breath", uses: 1, recharge: "combat", details: { resistances: ["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing", "poison", "radiant", "slashing", "thunder"] } }],
    carryingCapacity: { carried: 120, capacity: 240, pushDragLift: 480, overCapacity: true },
    stealthDisadvantage: true,
    spellSlots: { 1: 4, 2: 3 },
    warlockSpellSlots: { 3: 2 },
    slotGrantingClasses: ["fighter", "warlock"],
  };
  base.sheet = {
    ...base.sheet,
    weaponMasteries: [{ itemId: "longsword", name: "Longsword", mastery: "Sap" }],
    feats: [{ id: "alert", name: "Alert", origin: "background", level: null, choice: ["A", "B"], notes: ["n1", "n2"] }],
    senses: { darkvision: 60, devilsSight: 30 },
    damageModifiers: { resistances: ["fire-damage"], immunities: ["poison"], vulnerabilities: ["cold"] },
    conditionImmunities: ["charmed", "frightened"],
    innateSpells: [{ spellId: "mage-armor", name: "Mage Armor", level: 1, uses: "at will", ability: "CHA", variant: null, source: "Invocation", note: "Free" }],
  };
  return base;
}

interface State {
  name: string;
  draft: Draft;
  resolution: unknown;
  error: string | null;
  loading: boolean;
  catalog: unknown;
  library?: (storage: Map<string, string>) => void;
  stored?: boolean;
}

function states(): State[] {
  const out: State[] = FIXTURES.map((f, i) => ({
    name: f.id,
    draft: draftOf(f, ["Бранимир", "Rosen", "Мила Тестова", "Wizard Twenty", ""][i]),
    resolution: f.resolution,
    error: null,
    loading: false,
    catalog: CATALOG,
  }));
  out.push({ name: "empty-loading", draft: { ...emptyDraft }, resolution: null, error: null, loading: true, catalog: { ...CATALOG, loading: true } });
  out.push({ name: "empty-failed", draft: { ...emptyDraft }, resolution: null, error: "Няма връзка със сървъра.", loading: false, catalog: { ...CATALOG, error: "Каталогът не се зареди (грешка 500)." } });
  const f = FIXTURES[2];
  for (const [method, hp] of [["pointbuy", "manual"], ["roll", "fixed"], ["manual", "fixed"]] as const) {
    const d = draftOf(f, "Тест " + method);
    d.abilities = { method, base: { STR: 15, DEX: 14, CON: 13, INT: 12, WIS: 10, CHA: 8 } };
    d.preferences = { ...d.preferences, hitPointType: hp };
    d.classes = [{ classId: "fighter", level: 4, choices: {}, hpRolls: { "2": 6 } } as any, { classId: "rogue", level: 2, choices: {} } as any];
    d.sources = method === "pointbuy" ? ["srd", "phb"] : [];
    d.background = { id: "sage", choices: {} };
    d.species = { id: "human-xphb", subspeciesId: "sub-a", choices: {} } as any;
    d.equipment = { ...d.equipment, worn: { armor: null, shield: false }, wielded: { main: null, off: null } } as any;
    d.details = { alignment: "Lawful Good", faith: "Тир", age: "30", personalityTraits: "Смел" };
    const res = busyResolution();
    res.sheet.equipment = {
      granted: [{ itemId: "pack", name: "Explorer's Pack", qty: 1, contents: [{ itemId: "oil", name: "Oil", qty: 2 }, { itemId: "rope", name: "Rope", qty: 1 }] }],
      chosen: [{ itemId: "axe", name: "Axe", qty: 2 }, { itemId: "mace", name: "Mace", qty: 1, contents: [{ itemId: "x", name: "X", qty: 1 }] }],
      added: [{ itemId: "lamp", name: "Lamp", qty: 3, equipped: true, contents: [{ itemId: "oil", name: "Oil", qty: 1 }] }, { itemId: "bag", name: "Bag", qty: 1, equipped: false }],
      slots: { current: { armor: null, shield: false }, armor: [{ itemId: "chain", name: "Chain Mail" }], hands: [{ itemId: "sword", name: "Sword", kind: "weapon" }, { itemId: "shield", name: "Shield", kind: "shield" }] },
      worn: { armor: null, shield: true },
    };
    out.push({ name: `busy-${method}`, draft: d, resolution: res, error: method === "roll" ? "Сървърът не отговори навреме." : null, loading: method === "manual", catalog: { ...CATALOG, error: method === "manual" ? "cat err" : null, backgroundsFallback: method === "pointbuy" }, stored: true });
  }
  return out;
}

function memoryStorage(initial: Map<string, string>) {
  return {
    getItem: (k: string) => (initial.has(k) ? initial.get(k)! : null),
    setItem: (k: string, v: string) => void initial.set(k, v),
    removeItem: (k: string) => void initial.delete(k),
    keys: () => [...initial.keys()],
  };
}

function render(state: State, route: string): string {
  const store = new Map<string, string>();
  if (state.stored) {
    // a library with several characters: active ok, one empty (no stored draft), one corrupt, one with a class and a draft
    store.set("dnd-builder-library-v1", JSON.stringify({
      version: 1,
      activeId: "c1",
      items: {
        c1: { id: "c1", name: state.draft.name, createdAt: 1_700_000_000_000, updatedAt: 1_700_000_100_000, seenChoiceIds: [] },
        c2: { id: "c2", name: "Втори герой", createdAt: 1_700_000_000_000, updatedAt: 1_700_000_050_000, seenChoiceIds: [] },
        c3: { id: "c3", name: "", createdAt: 1_700_000_000_000, updatedAt: 1_700_000_040_000, seenChoiceIds: [] },
        c4: { id: "c4", name: "Повреден", createdAt: 1_700_000_000_000, updatedAt: 1_700_000_030_000, seenChoiceIds: [] },
      },
    }));
    store.set("dnd-builder-draft-v2:c1", JSON.stringify(state.draft));
    store.set("dnd-builder-draft-v2:c2", JSON.stringify({ ...emptyDraft, name: "Втори герой", classes: [{ classId: "wizard", level: 3, choices: {} }, { classId: "gone", level: 1, choices: {} }] }));
    store.set("dnd-builder-draft-v2:c4", "{not json");
  } else {
    store.set("dnd-builder-draft-v2", JSON.stringify(state.draft));
  }
  let n = 0;
  const env: LibraryEnv = { storage: memoryStorage(store), now: () => 1_700_000_200_000, newId: () => `id${++n}` };
  cap.cur = { catalog: state.catalog, resolution: state.resolution, error: state.error, loading: state.loading, items: ITEMS };
  const html = renderToStaticMarkup(
    createElement(
      MemoryRouter,
      { initialEntries: [route] },
      createElement(
        ErrorBoundary,
        null,
        createElement(LibraryProvider, { env, children: createElement(DraftProvider, null, createElement(App)) }),
      ),
    ),
  );
  // React ids (useId) depend on the tree above; they carry no copy
  return html.replace(/(["#=])(?:_[rR]_[0-9a-zA-Z]+_|«r[0-9a-z]+»|:r[0-9a-z]+:)/g, "$1<uid>");
}

function capture(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const st of states()) for (const route of ROUTES) out[`${st.name} ${route}`] = render(st, route);
  return out;
}

const SNAPSHOT = new URL("./__snapshots__/bg-render.json.gz", import.meta.url);

describe("BG render is identical to the snapshot captured before the copy conversion", () => {
  it("renders every route for every state", () => {
    const now = capture();
    if (process.env.UPDATE_BG_RENDER === "1") {
      mkdirSync(new URL("./__snapshots__/", import.meta.url), { recursive: true });
      writeFileSync(SNAPSHOT, gzipSync(Buffer.from(JSON.stringify(now)), { level: 9 }));
    }
    expect(existsSync(SNAPSHOT)).toBe(true);
    const then = JSON.parse(gunzipSync(readFileSync(SNAPSHOT)).toString("utf8")) as Record<string, string>;
    expect(Object.keys(now)).toEqual(Object.keys(then));
    for (const key of Object.keys(then)) {
      if (now[key] !== then[key]) {
        let i = 0;
        while (now[key][i] === then[key][i]) i++;
        throw new Error(`${key}: first difference at ${i}\nwas: ${then[key].slice(Math.max(0, i - 80), i + 120)}\nnow: ${now[key].slice(Math.max(0, i - 80), i + 120)}`);
      }
    }
  });

  it("the captured pages contain real content (the harness is not rendering empty shells)", () => {
    const now = capture();
    expect(now["busy-pointbuy /class"]).toContain("Fighting Style");
    expect(now["busy-pointbuy /home"]).toContain("Втори герой");
    expect(now["busy-manual /equipment"]).toContain("Explorer&#x27;s Pack");
    expect(now["wizard20-2024 /sheet"].length).toBeGreaterThan(10000);
  });
});
