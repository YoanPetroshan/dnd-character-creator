"""Loads and indexes the bundled SRD JSON data. This is the ONLY data
source in Phase 1 — no local sourcebook packs, no 5etools adapter (that's
Phase 4 scope, see the architecture spec §9-10). Every entity list is
indexed by its `index` field for O(1) lookup; the raw SRD field shapes are
used as-is here — catalog/choices.py and engine/resolve.py read those same
shapes directly rather than remapping them into a separate schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"


def _load(filename: str) -> list[dict]:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _load_srd(filename: str) -> list[dict]:
    """SRD 5.1 records are 2014 content; tag them so ruleset filtering sees them."""
    records = _load(filename)
    for r in records:
        r.setdefault("ruleset", "2014")
    return records


def _index_by(items: list[dict], key: str = "index") -> dict[str, dict]:
    return {item[key]: item for item in items}


@dataclass
class Catalog:
    classes: dict[str, dict] = field(default_factory=dict)
    levels: list[dict] = field(default_factory=list)
    features: dict[str, dict] = field(default_factory=dict)
    subclasses: dict[str, dict] = field(default_factory=dict)
    races: dict[str, dict] = field(default_factory=dict)
    subraces: dict[str, dict] = field(default_factory=dict)
    traits: dict[str, dict] = field(default_factory=dict)
    backgrounds: dict[str, dict] = field(default_factory=dict)
    items: dict[str, dict] = field(default_factory=dict)
    spells: dict[str, dict] = field(default_factory=dict)
    feats: dict[str, dict] = field(default_factory=dict)

    def class_level_row(self, class_id: str, level: int) -> dict | None:
        for row in self.levels:
            if (row.get("class", {}).get("index") == class_id
                    and row.get("level") == level
                    and "subclass" not in row):
                return row
        return None

    def subclass_level_row(self, subclass_id: str, level: int) -> dict | None:
        for row in self.levels:
            if row.get("subclass", {}).get("index") == subclass_id and row.get("level") == level:
                return row
        return None

    def subraces_of(self, race_id: str) -> list[dict]:
        return [s for s in self.subraces.values() if s.get("race", {}).get("index") == race_id]


def load() -> Catalog:
    from .official_source import (
        load_official_races, load_official_backgrounds, load_official_feats, official_dir,
    )

    official_races, official_subraces, official_traits = load_official_races(official_dir())
    official_backgrounds = load_official_backgrounds(official_dir())
    official_feats = load_official_feats(official_dir())
    races = {**_index_by(_load_srd("5e-SRD-Races.json")), **_index_by(official_races)}
    subraces = {**_index_by(_load_srd("5e-SRD-Subraces.json")), **_index_by(official_subraces)}
    traits = {**_index_by(_load("5e-SRD-Traits.json")), **official_traits}  # official_traits is already a dict — see load_official_races' own return type
    backgrounds = {**_index_by(_load_srd("5e-SRD-Backgrounds.json")), **_index_by(official_backgrounds)}
    feats = _index_by(official_feats)  # NO SRD merge — 2014 SRD has no feats at all (Phase 4c-i Task 1)

    return Catalog(
        classes=_index_by(_load("5e-SRD-Classes.json")),
        levels=_load("5e-SRD-Levels.json"),
        features=_index_by(_load("5e-SRD-Features.json")),
        subclasses=_index_by(_load("5e-SRD-Subclasses.json")),
        races=races,
        subraces=subraces,
        traits=traits,
        backgrounds=backgrounds,
        items=_index_by(_load("5e-SRD-Equipment.json")),
        spells=_index_by(_load("5e-SRD-Spells.json")),
        feats=feats,
    )
