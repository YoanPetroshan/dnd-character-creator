"""Index the user's 5etools JSON and Markdown rulebooks.

The books are ~2.6 MB of Markdown and several MB of JSON. Nothing here is
ever inlined into a prompt — the index stores only names and locations, and
`lookup.py` pulls a single entry on demand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from engine.config import content_root_path, json_dir, rules_index_path

# kind -> ordered list of (filename, top-level key). Order is priority: on a
# same-kind name collision, find() (lookup.py) returns whichever entry was
# indexed first — so list the authoritative 2024/MM-2025 file before any
# supplementary Xanathar's/Volo's file. Verified against the real corpus:
# 10 spells (Charm Monster, Dragon's Breath, Toll the Dead, ...) exist in
# both spells-xphb.json and spells-xge.json with different-era text.
JSON_SOURCES: dict[str, list[tuple[str, str]]] = {
    "monster": [("bestiary-xmm.json", "monster"), ("bestiary-xge.json", "monster")],
    "item": [("items.json", "item")],
    "item_base": [("items-base.json", "baseitem")],
    "trap": [("trapshazards.json", "trap")],
    "hazard": [("trapshazards.json", "hazard")],
    "reward": [("rewards.json", "reward")],
    "encounter_table": [("encounters.json", "encounter")],
    "spell": [("spells-xphb.json", "spell"), ("spells-xge.json", "spell")],
}

# loot.json is table-shaped rather than a flat list; lookup.py reads it directly.
LOOT_FILE = "loot.json"

BOOK_FILES = {
    "book-xphb.json": "PHB 2024",
    "book-xdmg.json": "DMG 2024",
    "book-xmm.json": "Monster Manual 2025",
    "book-xge.json": "Xanathar's Guide",
    "book-vgm.json": "Volo's Guide",
}

_HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*$")


def index_json_sources(
    directory: Path | None = None, skipped: list[str] | None = None
) -> list[dict]:
    directory = Path(directory) if directory is not None else json_dir()
    entries: list[dict] = []

    for kind, sources in JSON_SOURCES.items():
        for filename, key in sources:
            path = directory / filename
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            records = data.get(key)
            if not isinstance(records, list):
                continue
            for pos, record in enumerate(records):
                if not isinstance(record, dict):
                    continue
                name = record.get("name")
                if not name:
                    continue
                if "_copy" in record:
                    # Unresolved 5etools inheritance stub — its stats live on
                    # a base record we may not even have. Indexing it would
                    # let lookup return a name with no ac/hp/actions behind it.
                    if skipped is not None:
                        skipped.append(name)
                    continue
                entries.append({
                    "name": name,
                    "kind": kind,
                    "file": filename,
                    "key": key,
                    "pos": pos,
                    "source": record.get("source", ""),
                })

    # Book chapters, so `rule` queries can fall back to structured book text.
    for filename, label in BOOK_FILES.items():
        path = directory / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        chapters = data.get("data")
        if not isinstance(chapters, list):
            continue
        for pos, chapter in enumerate(chapters):
            name = chapter.get("name") if isinstance(chapter, dict) else None
            if not name:
                continue
            entries.append({
                "name": name,
                "kind": "chapter",
                "file": filename,
                "key": "data",
                "pos": pos,
                "source": label,
            })

    return entries


def index_markdown_books(root: Path | None = None) -> list[dict]:
    root = Path(root) if root is not None else content_root_path()
    entries: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            m = _HEADING.match(line)
            if not m:
                continue
            entries.append({
                "name": m.group(2).strip(),
                "kind": "rule",
                "file": str(path),
                "line": lineno,
                "source": path.stem,
            })
    return entries


def build_index(
    directory: Path | None = None,
    root: Path | None = None,
    out_path: Path | None = None,
) -> dict:
    skipped: list[str] = []
    entries = index_json_sources(directory, skipped=skipped) + index_markdown_books(root)
    payload = {
        "entries": entries,
        "count": len(entries),
        "skipped_copy_stubs": skipped,
    }
    out = Path(out_path) if out_path is not None else rules_index_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def load_index(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else rules_index_path()
    if not p.exists():
        return {"entries": [], "count": 0}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"entries": [], "count": 0}


if __name__ == "__main__":
    payload = build_index()
    kinds: dict[str, int] = {}
    for entry in payload["entries"]:
        kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
    print(f"indexed {payload['count']} entries")
    for kind, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {kind:16} {n}")
    skipped = payload["skipped_copy_stubs"]
    if skipped:
        print(f"\nskipped {len(skipped)} unresolved _copy stubs (no ac/hp of their own):")
        for name in skipped[:10]:
            print(f"  - {name}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")
