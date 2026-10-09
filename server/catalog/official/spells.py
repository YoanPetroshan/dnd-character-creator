"""5etools spell files -> SRD-shaped spell records (Slice 11a).

`spells/index.json` maps a source code to a file; each file is {"spell": [...]}.
Records carry no class list: class membership lives in `spells/sources.json`
as {SOURCE: {SpellName: {"class": [{name, source}], "classVariant": [...]}}}.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_raw_spells(spell_dir) -> list[dict]:
    """Every raw spell of every book in `spell_dir/index.json`, in index
    order. [] when the directory or index is missing; a file that is missing
    or not valid JSON is skipped."""
    if not spell_dir:
        return []
    spell_dir = Path(spell_dir)
    index = _read_json(spell_dir / "index.json")
    if not isinstance(index, dict):
        return []
    out: list[dict] = []
    for filename in index.values():
        if not isinstance(filename, str):
            continue
        data = _read_json(spell_dir / filename)
        if isinstance(data, dict):
            out.extend(s for s in data.get("spell", []) if isinstance(s, dict))
    return out


def load_spell_class_lookup(spell_dir) -> dict:
    """`spells/sources.json` as-is ({SOURCE: {SpellName: {...}}}); {} when missing."""
    if not spell_dir:
        return {}
    data = _read_json(Path(spell_dir) / "sources.json")
    return data if isinstance(data, dict) else {}
