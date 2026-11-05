"""Glossary of rules terms: loader, validator, citation checker and generator.

`glossary.json` maps termId -> {"en", "bg", "cite": {"src", "locator"}}.
  en    the wording of the source (2024 Player's Handbook first, SRD second).
  bg    the Bulgarian rendering the app uses today (UI copy, exports); stored in
        the case the app prints it, en in the case of the source.
  cite  where the English term is found. Only the term and a locator are stored,
        never book text (copyright).

Locators by source (checked by `check_cite`, case-insensitive for phb2024):
  phb2024  "Armor Class": a markdown heading line, a bold / bold-italic run-in
           ("***Hit Point Dice.***", "**Spell save DC**") or a Rules Glossary entry name;
           "text:50 GP": the literal text occurs somewhere in the file.
  srd      "5e-SRD-Traits.json::Darkvision": the JSON string occurs (exactly) as a value in
           that file of chargen/data/srd.
  5etools  "races.json::darkvision": same, relative to server/data/official.
The 2024 PHB markdown lives outside the repo, so it is checked only if present.

Generated from the JSON (`python -m i18n.glossary` from server/, or `--check` to detect drift):
  docs/GLOSSARY.md, frontend/src/copy/glossary.gen.ts
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
GLOSSARY_JSON = HERE / "glossary.json"
GLOSSARY_MD = REPO / "docs" / "GLOSSARY.md"
GLOSSARY_TS = REPO / "frontend" / "src" / "copy" / "glossary.gen.ts"
SRD_DIR = REPO / "chargen" / "data" / "srd"
OFFICIAL_DIR = REPO / "server" / "data" / "official"
PHB_PATH = pathlib.Path("/Users/yoanpetrov/Downloads/Player's Handbook (2024).md")

SOURCES = ("phb2024", "srd", "5etools")
SOURCE_LABELS = {"phb2024": "2024 PHB", "srd": "SRD", "5etools": "5etools data"}
_TERM_ID = re.compile(r"^[a-z][A-Za-z0-9]*$")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def load(path: pathlib.Path = GLOSSARY_JSON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# Terms whose Bulgarian wording is the English term on purpose (owner decision 2026-11-05): bg must equal en.
BG_IS_ENGLISH = frozenset({"spellSlots"})


def validate(data: object) -> list[str]:
    """Structural errors of a glossary mapping (empty list = valid)."""
    if not isinstance(data, dict) or not data:
        return ["glossary must be a non-empty object"]
    errors: list[str] = []
    seen_en: dict[str, str] = {}
    for tid, term in data.items():
        if not _TERM_ID.match(tid):
            errors.append(f"{tid}: id must be camelCase ASCII")
        if not isinstance(term, dict) or set(term) != {"en", "bg", "cite"}:
            errors.append(f"{tid}: must have exactly en, bg, cite")
            continue
        for k in ("en", "bg"):
            v = term[k]
            if not isinstance(v, str) or not v.strip() or v != v.strip():
                errors.append(f"{tid}: {k} must be a non-empty trimmed string")
        if isinstance(term["en"], str) and _CYRILLIC.search(term["en"]):
            errors.append(f"{tid}: en contains Cyrillic")
        if (isinstance(term["bg"], str) and term["bg"] and not _CYRILLIC.search(term["bg"])
                and not (tid in BG_IS_ENGLISH and term["bg"] == term["en"])):
            errors.append(f"{tid}: bg has no Cyrillic")
        cite = term["cite"]
        if not isinstance(cite, dict) or set(cite) != {"src", "locator"}:
            errors.append(f"{tid}: cite must have exactly src, locator")
        else:
            if cite["src"] not in SOURCES:
                errors.append(f"{tid}: cite.src must be one of {SOURCES}")
            if not isinstance(cite["locator"], str) or not cite["locator"].strip():
                errors.append(f"{tid}: cite.locator must be a non-empty string")
            elif cite["src"] in ("srd", "5etools") and "::" not in cite["locator"]:
                errors.append(f"{tid}: {cite['src']} locator must be 'file.json::string'")
        if isinstance(term["en"], str):
            if term["en"] in seen_en:
                errors.append(f"{tid}: en duplicates {seen_en[term['en']]}")
            seen_en[term["en"]] = tid
    return errors


# --- citation checks ----------------------------------------------------------------------

def _json_has_string(path: pathlib.Path, needle: str) -> bool:
    found = False

    def walk(node) -> None:
        nonlocal found
        if found:
            return
        if isinstance(node, str):
            found = node == needle
        elif isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for x in node.values():
                walk(x)

    walk(json.loads(path.read_text(encoding="utf-8")))
    return found


def phb_locator_found(text: str, locator: str) -> bool:
    if locator.startswith("text:"):
        return locator[5:] in text
    loc = re.escape(locator)
    patterns = (
        rf"^#{{1,6}}\s+{loc}\s*$",                     # heading line
        rf"\*{{2,3}}{loc}\.?\*{{2,3}}",                # bold / bold-italic run-in
        rf'data-rd-data-embed-name="true">{loc}<',     # Rules Glossary entry
    )
    return any(re.search(p, text, re.IGNORECASE | re.MULTILINE) for p in patterns)


def check_cite(tid: str, cite: dict, phb_path: pathlib.Path | None = PHB_PATH) -> str | None:
    """None if the citation holds or cannot be checked here (PHB file absent), else an error text."""
    src, loc = cite["src"], cite["locator"]
    if src == "phb2024":
        if phb_path is None or not phb_path.is_file():
            return None
        if not phb_locator_found(phb_path.read_text(encoding="utf-8"), loc):
            return f"{tid}: PHB locator {loc!r} not found"
        return None
    base = SRD_DIR if src == "srd" else OFFICIAL_DIR
    fname, _, needle = loc.partition("::")
    path = base / fname
    if not path.is_file():
        return f"{tid}: {src} file {fname} does not exist"
    if not _json_has_string(path, needle):
        return f"{tid}: {needle!r} not found in {fname}"
    return None


# --- generated outputs --------------------------------------------------------------------

def render_markdown(data: dict) -> str:
    out = [
        "# Glossary (BG / EN)",
        "",
        "<!-- GENERATED from server/i18n/glossary.json by `python -m i18n.glossary` (run in server/). Do not edit. -->",
        "",
        "Rules terms in two languages. English follows the wording of the sources (2024 Player's Handbook "
        "first, SRD second); Bulgarian is the rendering the app uses. The last column is a citation "
        "(source and locator only, no book text).",
        "",
        "| Term id | English | Български | Source | Locator |",
        "|---|---|---|---|---|",
    ]
    for tid, t in data.items():
        cell = lambda s: s.replace("|", "\\|")
        out.append(f"| `{tid}` | {cell(t['en'])} | {cell(t['bg'])} | {SOURCE_LABELS[t['cite']['src']]} | "
                   f"{cell(t['cite']['locator'])} |")
    return "\n".join(out) + "\n"


def render_ts(data: dict) -> str:
    out = [
        "// GENERATED from server/i18n/glossary.json by `python -m i18n.glossary` (run in server/). Do not edit.",
        "// Rules terms: `en` follows the sources (2024 PHB, then SRD); `bg` is the Bulgarian the app uses.",
        "",
        "export const glossary = {",
    ]
    for tid, t in data.items():
        out.append(f"  {tid}: {{ en: {json.dumps(t['en'], ensure_ascii=False)}, "
                   f"bg: {json.dumps(t['bg'], ensure_ascii=False)} }},")
    out += ["} as const;", "", "export type GlossaryId = keyof typeof glossary;", ""]
    return "\n".join(out)


def _rel(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def outputs(data: dict) -> dict[pathlib.Path, str]:
    return {GLOSSARY_MD: render_markdown(data), GLOSSARY_TS: render_ts(data)}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    check = "--check" in args
    data = load()
    errors = validate(data)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    stale = []
    for path, text in outputs(data).items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == text:
            continue
        if check:
            stale.append(_rel(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {_rel(path)}")
    if stale:
        print("out of date (run `python -m i18n.glossary` in server/): " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
