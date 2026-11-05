// Guards of the copy catalog (SK6-BI): bg and en have the same keys, the same arity and the same
// placeholders; en has no Cyrillic; the Latin words in bg come only from an explicit allowlist; and the
// UI code takes all its text from the catalog (AST scan of the sources).
import { readFileSync, readdirSync, statSync } from "node:fs";
import { parseAst } from "rolldown/parseAst";
import { describe, expect, it } from "vitest";
import { bg, en } from "./copy";
import { glossary } from "./copy/glossary.gen";

type Leaf = string | ((...a: any[]) => string);
const isFn = (v: unknown): v is (...a: any[]) => string => typeof v === "function";

/** Every leaf (string or function) of a catalog with its dotted path. */
function leaves(obj: unknown, path: string[] = []): [string, Leaf][] {
  if (typeof obj === "string" || isFn(obj)) return [[path.join("."), obj]];
  return Object.entries(obj as object).flatMap(([k, v]) => leaves(v, [...path, k]));
}
const BG = new Map(leaves(bg));
const EN = new Map(leaves(en));

// ---- sample calls -----------------------------------------------------------------------------
// A catalog function is called with distinct sentinels so we can see which parameters it prints.
// Kinds are tried in turn (numbers, strings, string arrays) until the call works.
const KINDS = ["num", "str", "arr"] as const;
type Kind = (typeof KINDS)[number];
const sentinel = (kind: Kind, i: number): unknown =>
  kind === "num" ? 1000 + i * 111 : kind === "str" ? `§${i}§` : [`§${i}§`];
const marker = (i: number, kind: Kind) => (kind === "num" ? String(1000 + i * 111) : `§${i}§`);

/** Proxy parameter object for `msg.*` templates: every property read yields a sentinel. */
function msgParams(used: Set<string>) {
  return new Proxy({}, { get: (_t, k) => (used.add(String(k)), `§${used.size}§`) });
}

interface Call { kinds: Kind[]; out: string; used: Set<number> | Set<string> }
function sampleCalls(fn: (...a: any[]) => string, isMsg: boolean): Call[] {
  const calls: Call[] = [];
  if (isMsg) {
    const used = new Set<string>();
    try { calls.push({ kinds: [], out: fn(msgParams(used)), used }); } catch { /* not callable */ }
    return calls;
  }
  const n = fn.length;
  const combos: Kind[][] = [[]];
  for (let i = 0; i < n; i++) combos.splice(0, combos.length, ...combos.flatMap((c) => KINDS.map((k) => [...c, k])));
  for (const kinds of combos) {
    try {
      const out = fn(...kinds.map((k, i) => sentinel(k, i)));
      if (typeof out !== "string") continue;
      calls.push({ kinds, out, used: new Set(kinds.map((k, i) => (out.includes(marker(i, k)) ? i : -1)).filter((i) => i >= 0)) as Set<number> });
    } catch { /* wrong kinds */ }
  }
  return calls;
}
const isMsgPath = (p: string) => p.startsWith("msg.");

describe("copy catalog parity (bg vs en)", () => {
  it("has exactly the same keys", () => {
    expect([...EN.keys()].sort()).toEqual([...BG.keys()].sort());
  });

  it("has the same kind of leaf (text or template) and the same arity", () => {
    for (const [path, b] of BG) {
      const e = EN.get(path)!;
      expect(typeof e, path).toBe(typeof b);
      if (isFn(b) && isFn(e)) expect(e.length, `${path}: arity`).toBe(b.length);
    }
  });

  it("every template prints the same parameters in both languages", () => {
    for (const [path, b] of BG) {
      const e = EN.get(path)!;
      if (!isFn(b) || !isFn(e)) continue;
      const cb = sampleCalls(b, isMsgPath(path));
      const ce = sampleCalls(e, isMsgPath(path));
      expect(cb.length, `${path}: bg template cannot be sampled`).toBeGreaterThan(0);
      for (const c of cb) {
        const twin = ce.find((x) => x.kinds.join() === c.kinds.join());
        expect(twin, `${path}: en template fails for ${c.kinds.join()}`).toBeDefined();
        expect([...twin!.used].sort(), `${path} (${c.kinds.join() || "msg"})`).toEqual([...c.used].sort());
      }
    }
  });

  it("every message code used by the code has a catalog entry in both languages", () => {
    expect(Object.keys(en.msg).sort()).toEqual(Object.keys(bg.msg).sort());
  });
});

// ---- rendered outputs ---------------------------------------------------------------------------

/** All strings the catalog can print: texts, and the outputs of every template for every sample call. */
function outputs(map: Map<string, Leaf>): [string, string][] {
  const out: [string, string][] = [];
  for (const [path, v] of map) {
    if (typeof v === "string") out.push([path, v]);
    else for (const c of sampleCalls(v, isMsgPath(path))) out.push([path, c.out]);
  }
  return out;
}

const CYRILLIC = /[Ѐ-ӿ]/;

describe("scripts", () => {
  it("en.ts has no Cyrillic (source text and every rendered output)", () => {
    expect(CYRILLIC.test(readFileSync(new URL("./copy/en.ts", import.meta.url)).toString("utf8"))).toBe(false);
    for (const [path, text] of outputs(EN)) expect(CYRILLIC.test(text), `${path}: ${text}`).toBe(false);
  });

  // Latin words that may appear in the Bulgarian UI.
  // Permanent: abbreviations and proper nouns the Bulgarian text keeps (dice, ability codes, file formats, units).
  const PERMANENT = new Set(["AC", "DC", "CR", "SRD", "PDF", "YAML", "JSON", "json", "MB", "Markdown", "EN", "STR", "DEX", "CON", "INT", "WIS", "CHA", "d", "lb"]);
  // Legacy: English words the Bulgarian UI already showed before the copy catalog existed (page titles, labels,
  // sentences). They stay so that the BG rendering is byte-identical; translating them is a deliberate later change.
  const LEGACY = new Set([
    "Abilities", "Add", "Array", "Attacks", "Background", "Buy", "Carrying", "Character", "Dueling", "Equipment",
    "Export", "Home", "Manual", "Name", "Origin", "Point", "Points", "Preferences", "Problems", "Re", "Remaining",
    "Resolution", "Roll", "Saved", "Sources", "Species", "Standard", "Stealth", "Subspecies", "Unresolved", "action",
    "all", "and", "api", "armor", "as", "background", "backgrounds", "be", "capacity", "choice", "choices", "current",
    "disadvantage", "drag", "drop", "feat", "from", "hand", "here", "level", "lift", "lowest", "mastery", "name",
    "none", "off", "on", "over", "page", "pending", "per", "push", "range", "reload", "replaces", "resolve",
    "rolling", "ruleset", "scores", "should", "six", "species", "still", "the", "this", "type", "versatile", "with",
    "you",
  ]);

  it("the legacy list has no stale entries (every word is still printed by the Bulgarian UI)", () => {
    const used = new Set<string>();
    for (const [, text] of outputs(BG)) for (const w of text.match(/[A-Za-z]+/g) ?? []) used.add(w);
    expect([...LEGACY].filter((w) => !used.has(w))).toEqual([]);
  });

  it("bg.ts uses Latin words only from the allowlist (permanent abbreviations + legacy English)", () => {
    const unknown = new Set<string>();
    for (const [path, text] of outputs(BG)) {
      if (path === "common.dateLocale") continue; // a locale tag, not text
      for (const w of text.match(/[A-Za-z]+/g) ?? []) if (!PERMANENT.has(w) && !LEGACY.has(w)) unknown.add(`${w} (${path})`);
    }
    expect([...unknown].sort()).toEqual([]);
  });
});

// ---- the glossary ------------------------------------------------------------------------------

describe("rules terms come from the glossary", () => {
  const get = (c: object, path: string) => path.split(".").reduce((o: any, k) => o[k], c) as string;
  const MAP: [string, keyof typeof glossary][] = [
    ["sheet.abilities.title", "abilityScores"],
    ["sheet.armorClass.title", "armorClass"],
    ["sheet.hitPoints.title", "hitPoints"],
    ["sheet.hitPoints.hitDice", "hitPointDice"],
    ["sheet.proficiencyBonus.title", "proficiencyBonus"],
    ["sheet.savingThrows.title", "savingThrows"],
    ["sheet.skills.title", "skills"],
    ["sheet.initiative.title", "initiative"],
    ["sheet.speeds.title", "speed"],
    ["sheet.passives.perception", "passivePerception"],
    ["sheet.passives.insight", "passiveInsight"],
    ["sheet.passives.investigation", "passiveInvestigation"],
    ["sheet.spells.saveDC", "spellSaveDc"],
    ["sheet.spells.attackBonus", "spellAttackBonus"],
    ["sheet.spells.slotsTitle", "spellSlots"],
    ["sheet.spells.cantrips", "cantrips"],
    ["sheet.spells.spellbook", "spellbook"],
    ["sheet.identity.species", "species"],
    ["sheet.identity.background", "background"],
    ["sheet.identity.size", "size"],
    ["sheet.features.title", "classFeatures"],
    ["sheet.feats.title", "feats"],
    ["sheet.languages.title", "languages"],
    ["sheet.equipment.title", "equipment"],
    ["sheet.attacks.masteriesTitle", "weaponMastery"],
    ["sheet.senses.title", "senses"],
    ["sheet.senses.kinds.darkvision", "darkvision"],
    ["sheet.senses.kinds.blindsight", "blindsight"],
    ["sheet.senses.kinds.tremorsense", "tremorsense"],
    ["sheet.senses.kinds.truesight", "truesight"],
    ["sheet.carryingCapacity.title", "carryingCapacity"],
    ["sheet.resources.text.recharge.long", "longRest"],
    ["sheet.resources.text.recharge.short", "shortRest"],
    ["choice.cantripsGroup", "cantrips"],
    ["spellLibrary.filters.cantrips", "cantrips"],
  ];
  for (const [path, term] of MAP) {
    it(`${path} is the glossary term ${term}`, () => {
      expect(get(bg, path)).toBe(glossary[term].bg);
      expect(get(en, path)).toBe(glossary[term].en);
    });
  }
  it("the spell slots heading is the same text everywhere in bg ('Клетки за заклинания')", () => {
    expect(bg.sheet.spells.slotsTitle).toBe("Клетки за заклинания");
    expect(glossary.spellSlots.bg).toBe("Клетки за заклинания");
  });
});

// ---- AST scan of the sources ------------------------------------------------------------------------

const SRC = new URL("./", import.meta.url);
function sourceFiles(dir: URL): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const url = new URL(name, dir.href.endsWith("/") ? dir : new URL(dir.href + "/"));
    if (statSync(url).isDirectory()) {
      if (["copy", "__fixtures__", "__snapshots__"].includes(name)) continue;
      out.push(...sourceFiles(new URL(url.href + "/")));
    } else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) && !name.endsWith(".d.ts")) out.push(url.href);
  }
  return out;
}

const HAS_LETTER = /\p{L}/u;
// attributes that are read by people (screen readers, tooltips, placeholders)
const TEXT_ATTRS = new Set(["aria-label", "aria-description", "aria-placeholder", "aria-roledescription", "placeholder", "title", "alt", "label"]);
const DIALOGS = new Set(["alert", "confirm", "prompt"]);

// Short explicit exceptions: [file suffix, text]. Technical tokens that are not user-facing copy.
const EXCEPTIONS: [string, string][] = [];

// Files whose Cyrillic literals are CONTENT, not UI text: the name lists of the random-name button and the
// Cyrillic -> Latin transliteration table. Nothing here is shown as a label; each file is listed with its reason.
const CONTENT_FILES: [string, string][] = [
  ["names/bgNames.ts", "name lists (data)"],
  ["logic/translit.ts", "transliteration table (script mapping)"],
];

interface Hit { file: string; what: string; text: string }

/** Calls `cb` with every piece of text an expression can print: string literals, template text,
 *  the branches of ?: && || ??, and `+` operands. Comparisons, call arguments, keys and nested JSX
 *  are not value positions (nested JSX is scanned on its own). */
function valueStrings(node: any, cb: (text: string) => void): void {
  if (!node) return;
  switch (node.type) {
    case "Literal":
      if (typeof node.value === "string") cb(node.value);
      return;
    case "TemplateLiteral":
      for (const q of node.quasis) cb(q.value.cooked ?? q.value.raw);
      for (const e of node.expressions) valueStrings(e, cb);
      return;
    case "LogicalExpression":
      if (node.operator !== "&&") valueStrings(node.left, cb);
      valueStrings(node.right, cb);
      return;
    case "ConditionalExpression":
      valueStrings(node.consequent, cb);
      valueStrings(node.alternate, cb);
      return;
    case "BinaryExpression":
      if (node.operator === "+") {
        valueStrings(node.left, cb);
        valueStrings(node.right, cb);
      }
      return;
    case "ParenthesizedExpression":
    case "TSAsExpression":
    case "TSNonNullExpression":
      valueStrings(node.expression, cb);
      return;
    default:
      return;
  }
}

function scan(file: string, code: string): Hit[] {
  const hits: Hit[] = [];
  const isContent = CONTENT_FILES.some(([f]) => file.endsWith(f));
  const excepted = (text: string) => EXCEPTIONS.some(([f, t]) => file.endsWith(f) && t === text);
  const flag = (what: string) => (text: string) => {
    if (HAS_LETTER.test(text) && !excepted(text)) hits.push({ file, what, text: text.trim().slice(0, 60) });
  };
  const ast = parseAst(code, { lang: file.endsWith(".tsx") ? "tsx" : "ts" });
  walk(ast, (n: any) => {
    if (n.type === "JSXText") flag("JSX text")(n.value);
    if ((n.type === "JSXElement" || n.type === "JSXFragment") && Array.isArray(n.children)) {
      for (const c of n.children) if (c.type === "JSXExpressionContainer") valueStrings(c.expression, flag("JSX child expression"));
    }
    if (n.type === "JSXAttribute" && n.name?.type === "JSXIdentifier" && TEXT_ATTRS.has(n.name.name) && n.value) {
      const what = `${n.name.name} attribute`;
      if (n.value.type === "Literal") flag(what)(String(n.value.value));
      else if (n.value.type === "JSXExpressionContainer") valueStrings(n.value.expression, flag(what));
    }
    if (n.type === "CallExpression") {
      const c = n.callee;
      const name = c.type === "Identifier" ? c.name : c.type === "MemberExpression" && c.object?.name === "window" ? c.property?.name : null;
      if (name && DIALOGS.has(name)) for (const a of n.arguments) valueStrings(a, flag(`${name}() argument`));
    }
    if (n.type === "AssignmentExpression" && n.left?.type === "MemberExpression" && n.left.property?.name === "title" && n.left.object?.name === "document")
      valueStrings(n.right, flag("document.title"));
    // no Cyrillic literal anywhere outside the catalog
    if (isContent) return;
    if (n.type === "Literal" && typeof n.value === "string" && CYRILLIC.test(n.value)) hits.push({ file, what: "Cyrillic literal", text: n.value.slice(0, 60) });
    if (n.type === "TemplateElement" && CYRILLIC.test(n.value.raw)) hits.push({ file, what: "Cyrillic template text", text: n.value.raw.slice(0, 60) });
  });
  return hits;
}

/** Depth-first walk over every node with a `type`. */
function walk(node: any, visit: (n: any) => void): void {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node)) {
    for (const c of node) walk(c, visit);
    return;
  }
  if (typeof node.type === "string") visit(node);
  for (const v of Object.values(node)) walk(v, visit);
}

describe("source scan: all UI text comes from the catalog", () => {
  const files = sourceFiles(SRC);
  it("finds the sources", () => expect(files.length).toBeGreaterThan(40));

  it("the scan itself catches what it should (negative tests)", () => {
    const bad = `export const A = () => <div title="Hello" aria-label={\`Add \${x}\`}>Text {ok && "more"}<input placeholder="Search" /></div>;
      export const f = () => window.confirm("Sure?");`;
    const hits = scan("x.tsx", bad).map((h) => h.what);
    expect(hits).toEqual(expect.arrayContaining(["title attribute", "aria-label attribute", "JSX text", "JSX child expression", "placeholder attribute", "confirm() argument"]));
    expect(scan("x.tsx", "export const A = () => <p>{t.a}{' '}—</p>;")).toEqual([]);
    expect(scan("x.ts", "export const m = 'Грешка';").map((h) => h.what)).toEqual(["Cyrillic literal"]);
  });

  it("the content-file exception list is exactly the two data files and they exist", () => {
    expect(CONTENT_FILES.map(([f]) => f)).toEqual(["names/bgNames.ts", "logic/translit.ts"]);
    for (const [f] of CONTENT_FILES) expect(files.some((h) => h.endsWith("/" + f)), f).toBe(true);
    // the exception covers only Cyrillic literals in those two files
    expect(scan("names/bgNames.ts", "export const m = 'Иван';")).toEqual([]);
    expect(scan("names/other.ts", "export const m = 'Иван';").map((h) => h.what)).toEqual(["Cyrillic literal"]);
  });

  it("has no letters in JSX text, aria-label, placeholder or title outside t.*, and no Cyrillic literal", () => {
    const hits: Hit[] = [];
    for (const href of files) hits.push(...scan(href.replace(SRC.href, ""), readFileSync(new URL(href)).toString("utf8")));
    expect(hits.map((h) => `${h.file}: ${h.what}: ${h.text}`)).toEqual([]);
  });
});
