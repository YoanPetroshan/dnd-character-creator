"""Descriptive text of the species from the 5etools `fluff-races.json` (what they are, how they look, where they
come from), for the species preview (`GET /api/catalog/species/<id>`). Records are matched to a species by
(name, source). Images, tables, lists, quotes and insets are dropped; 5etools tags are stripped to their display
text. The processed file is cached once per data directory."""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path

from .paths import official_dir
from .spells import _strip_tags

MAX_PARAGRAPHS = 4
MAX_CHARS = 460
_DROPPED = frozenset({"image", "table", "list", "inset", "insetReadaloud", "quote", "gallery", "item", "itemSub"})


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", _strip_tags(value)).strip()


def _first_paragraph(entries) -> str | None:
    """The first plain paragraph of a block's entries (descending into nested entries), or None."""
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, str):
            text = _text(entry)
            if text:
                return text
        elif isinstance(entry, dict) and entry.get("type") not in _DROPPED:
            found = _first_paragraph(entry.get("entries"))
            if found:
                return found
    return None


def _flatten(entries, out: list[tuple[str | None, str]]) -> None:
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, str):
            text = _text(entry)
            if text:
                out.append((None, text))
        elif isinstance(entry, dict) and entry.get("type") not in _DROPPED:
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                text = _first_paragraph(entry.get("entries"))
                if text:
                    out.append((_text(name), text))
            else:
                _flatten(entry.get("entries"), out)


def _apply_mod(entries: list, mod) -> list:
    """The `_copy._mod.entries` prepend/append modes (the only ones the fluff file uses)."""
    mods = mod.get("entries") if isinstance(mod, dict) else None
    for step in mods if isinstance(mods, list) else [mods]:
        if not isinstance(step, dict):
            continue
        items = step.get("items")
        items = items if isinstance(items, list) else [items]
        if step.get("mode") == "prependArr":
            entries = items + entries
        elif step.get("mode") == "appendArr":
            entries = entries + items
    return entries


@functools.lru_cache(maxsize=4)
def _load(directory: str) -> dict[tuple[str, str], list[tuple[str | None, str]]]:
    try:
        raw = json.loads((Path(directory) / "fluff-races.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    records = {(r.get("name"), r.get("source")): r for r in raw.get("raceFluff") or [] if isinstance(r, dict)}

    def entries_of(key, seen=()):
        record = records.get(key) or {}
        copy = record.get("_copy")
        if isinstance(copy, dict) and key not in seen:
            base = entries_of((copy.get("name"), copy.get("source")), seen + (key,))
            return _apply_mod(list(base), copy.get("_mod"))
        return list(record.get("entries") or [])

    out = {}
    for key in records:
        flat: list[tuple[str | None, str]] = []
        _flatten(entries_of(key), flat)
        if flat:
            out[key] = flat
    return out


def _short(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    cut = text[:MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[:end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"


def _norm(name: str) -> str:
    n = re.sub(r"\([^)]*\)", "", name.lower()).strip()
    n = re.sub(r"ves\b", "f", n)
    return re.sub(r"s\b", "", n)


def species_fluff(name: str, source: str, subspecies_names=()) -> list[str]:
    """At most MAX_PARAGRAPHS short paragraphs about the species itself; blocks about one of its subspecies are
    skipped (named blocks read "Name. text")."""
    blocks = _load(str(official_dir())).get((name, source or "PHB")) or []  # an SRD record has no source: PHB text
    own = {_norm(n) for n in subspecies_names}
    paragraphs = []
    for title, text in blocks:
        if title and _norm(title) in own:
            continue
        paragraphs.append(_short(f"{title}. {text}" if title else text))
        if len(paragraphs) == MAX_PARAGRAPHS:
            break
    return paragraphs


def trait_details(race: dict, traits: dict[str, dict]) -> list[dict]:
    out = []
    for ref in race.get("traits") or []:
        trait = traits.get(ref.get("index"))
        if not trait:
            continue
        desc = [t for t in (_text(line) for line in trait.get("desc") or [] if isinstance(line, str)) if t]
        if desc:  # a synthetic proficiency trait has no text of its own
            out.append({"name": trait.get("name") or ref.get("name") or "", "desc": desc})
    return out
