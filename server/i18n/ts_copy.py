"""A small reader for the frontend copy catalogs (`frontend/src/copy/bg.ts`, `en.ts`, `glossary.gen.ts`).

Like the types drift guard it reads the TypeScript SOURCE (no Node, no TypeScript compiler): a tiny tokenizer walks the
exported object literal and returns its tree. A branch is a dict; a leaf is a `Leaf(kind, text)` with kind "str"
(a string / template literal without `${}`), "fn" (an arrow function or method: a template with parameters) or
"expr" (anything else, e.g. `g.armorClass.en` or a template that interpolates).
"""
from __future__ import annotations

import pathlib
import re
from typing import NamedTuple

COPY_DIR = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "copy"


class Leaf(NamedTuple):
    kind: str   # "str" | "fn" | "expr"
    text: str   # str: the decoded value; fn / expr: the source text


def _skip_ws(s: str, i: int) -> int:
    while i < len(s):
        if s[i].isspace():
            i += 1
        elif s.startswith("//", i):
            i = s.index("\n", i) if "\n" in s[i:] else len(s)
        elif s.startswith("/*", i):
            i = s.index("*/", i) + 2
        else:
            break
    return i


def _read_string(s: str, i: int) -> int:
    """Index just after the string / template literal starting at s[i]."""
    quote = s[i]
    i += 1
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
        elif c == quote:
            return i + 1
        elif quote == "`" and s.startswith("${", i):
            i = _skip_expr(s, i + 2, closers="}") + 1
        else:
            i += 1
    raise ValueError("unterminated string")


def _skip_expr(s: str, i: int, closers: str = ",}") -> int:
    """Index of the first top-level character in `closers` (or an unbalanced closing bracket) at or after i."""
    depth = 0
    while i < len(s):
        c = s[i]
        if c in "\"'`":
            i = _read_string(s, i)
            continue
        if s.startswith("//", i) or s.startswith("/*", i):
            i = _skip_ws(s, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return i
            depth -= 1
        elif depth == 0 and c in closers:
            return i
        i += 1
    return i


_ARROW = re.compile(r"^(async\s+)?(\([^)]*\)|\w+)\s*(:\s*[^=]+)?=>", re.S)


def _decode(literal: str) -> str:
    body = literal[1:-1]
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), body)


def _leaf(text: str) -> Leaf:
    text = text.strip()
    if _ARROW.match(text):
        return Leaf("fn", text)
    if text[:1] in "\"'`" and _read_string(text, 0) == len(text) and "${" not in text:
        return Leaf("str", _decode(text))
    return Leaf("expr", text)


def _parse_object(s: str, i: int) -> tuple[dict, int]:
    assert s[i] == "{"
    out: dict = {}
    i += 1
    while True:
        i = _skip_ws(s, i)
        if s[i] == "}":
            return out, i + 1
        if s.startswith("...", i):
            end = _skip_expr(s, i)
            out[f"...{s[i + 3:end].strip()}"] = Leaf("expr", s[i:end])
            i = end
        else:
            if s[i] in "\"'":
                end = _read_string(s, i)
                key = _decode(s[i:end])
                i = end
            elif s[i] == "[":
                end = _skip_expr(s, i + 1, closers="]") + 1
                key = s[i:end]
                i = end
            else:
                m = re.compile(r"[A-Za-z_$][\w$]*").match(s, i)
                if not m:
                    raise ValueError(f"unexpected {s[i:i + 40]!r}")
                key, i = m.group(0), m.end()
            i = _skip_ws(s, i)
            if s[i] == ":":
                i = _skip_ws(s, i + 1)
                if s[i] == "{":
                    out[key], i = _parse_object(s, i)
                    m = re.compile(r"\s*as\s+Record<string,\s*string>").match(s, i)
                    if m:
                        i = m.end()
                else:
                    end = _skip_expr(s, i)
                    out[key] = _leaf(s[i:end])
                    i = end
            elif s[i] == "(":  # method shorthand: key(args) { ... }
                end = _skip_expr(s, i)
                end = _skip_expr(s, _skip_ws(s, end))  # the body
                out[key] = Leaf("fn", s[i:end])
                i = end
            else:  # shorthand property
                out[key] = Leaf("expr", key)
        i = _skip_ws(s, i)
        if s[i] == ",":
            i += 1


def parse_catalog(path: pathlib.Path, const: str) -> dict:
    """The tree of `export const <const>[: Type] = { ... }` in a TypeScript file."""
    s = path.read_text(encoding="utf-8")
    m = re.search(rf"export const {const}\b[^=]*=\s*", s)
    assert m, f"{const} not found in {path}"
    tree, _end = _parse_object(s, m.end())
    return tree


def flatten(tree: dict, prefix: str = "") -> dict[str, Leaf]:
    """{"a.b.c": Leaf} for every leaf of a tree."""
    out: dict[str, Leaf] = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = value
    return out


def load_glossary_ts(path: pathlib.Path = COPY_DIR / "glossary.gen.ts") -> dict[str, dict[str, str]]:
    """{termId: {"en": ..., "bg": ...}} from the generated `glossary` const."""
    out: dict[str, dict[str, str]] = {}
    for tid, value in parse_catalog(path, "glossary").items():
        out[tid] = {k: v.text for k, v in value.items()}
    return out
