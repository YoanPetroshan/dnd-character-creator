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
    # Slice 11a: bare-slug references to a spell that lives under another id
    # (the 17 SRD renames: "tensers-floating-disk" -> "floating-disk"; 2024-only
    # spells: "divine-smite" -> "divine-smite-xphb"), and the 2014 <-> 2024 pairs
    # of the same spell (symmetric id -> id), used for ruleset visibility.
    spell_aliases: dict[str, str] = field(default_factory=dict)
    spell_twins: dict[str, str] = field(default_factory=dict)
    # Slice 11b: 2014 <-> 2024 pairs of the same subclass (symmetric id -> id).
    subclass_twins: dict[str, str] = field(default_factory=dict)
    # O3: XPHB spell progressions per caster class id ({"caster", "cantrips"[20],
    # "prepared"[20]}), used only under ruleset "2024".
    class_2024_progressions: dict[str, dict] = field(default_factory=dict)
    # Level-row indexes (class_id, level) / (subclass_id, level) -> row, built
    # lazily and rebuilt when the number of rows changes.
    _row_index: tuple | None = field(default=None, repr=False, compare=False)

    def resolve_spell_id(self, spell_id: str | None) -> str | None:
        """The catalog id for a spell reference: the id itself, else its alias, else None."""
        if spell_id in self.spells:
            return spell_id
        alias = self.spell_aliases.get(spell_id)
        return alias if alias in self.spells else None

    def _rows(self) -> tuple[dict, dict]:
        cached = self._row_index
        if cached is None or cached[0] != len(self.levels):
            class_rows: dict[tuple, dict] = {}
            sub_rows: dict[tuple, dict] = {}
            for row in self.levels:
                level = row.get("level")
                sub = row.get("subclass")
                if sub is not None:
                    sub_rows.setdefault((sub.get("index"), level), row)
                else:
                    class_rows.setdefault((row.get("class", {}).get("index"), level), row)
            cached = self._row_index = (len(self.levels), class_rows, sub_rows)
        return cached[1], cached[2]

    def class_level_row(self, class_id: str, level: int) -> dict | None:
        return self._rows()[0].get((class_id, level))

    def subclass_level_row(self, subclass_id: str, level: int) -> dict | None:
        return self._rows()[1].get((subclass_id, level))

    def subraces_of(self, race_id: str) -> list[dict]:
        return [s for s in self.subraces.values() if s.get("race", {}).get("index") == race_id]


def _load_spells() -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    """SRD spells (tagged source "SRD", ruleset "2014") plus every official
    sourcebook spell found on disk. An official spell that is the same spell
    as an SRD one only contributes its class list (classes missing from the
    SRD record are appended); everything else is added under its own id."""
    from .official_source import (
        build_spell_aliases, link_spell_versions, load_official_spells, spells_dir,
    )

    spells = _index_by(_load_srd("5e-SRD-Spells.json"))
    for spell in spells.values():
        spell.setdefault("source", "SRD")
    for record in load_official_spells(spells_dir(), srd_indices=frozenset(spells)):
        existing = spells.get(record["index"])
        if existing is None:
            spells[record["index"]] = record
            continue
        have = {c["index"] for c in existing.get("classes", [])}
        for c in record["classes"]:
            if c["index"] not in have:
                existing.setdefault("classes", []).append(c)
                have.add(c["index"])
    return spells, build_spell_aliases(spells), link_spell_versions(spells)


def _merge_official_subclasses(catalog: Catalog) -> None:
    """Tags the SRD subclasses and merges every sourcebook subclass found on
    disk (subclass records, their features, their level rows, the 2014/2024
    twin map). SRD records win a key clash."""
    from .official_source import (
        class_dir, convert_subclasses, load_class_2024_progressions, load_raw_class_data, load_raw_optional_features, optionalfeatures_file,
        subclass_twins_from,
    )

    srd_ids = set(catalog.subclasses)
    for sub in catalog.subclasses.values():
        sub.setdefault("source", "SRD")
        sub.setdefault("ruleset", "2014")
    catalog.class_2024_progressions = load_class_2024_progressions(class_dir())
    raw_subs, raw_feats = load_raw_class_data(class_dir())
    if not raw_subs:
        return
    subs, feats, rows = convert_subclasses(raw_subs, raw_feats, srd_ids, catalog.resolve_spell_id,
                                           load_raw_optional_features(optionalfeatures_file()))
    clash = (set(subs) & set(catalog.subclasses)) | (set(feats) & set(catalog.features))
    if clash:
        raise ValueError(f"imported subclass ids clash with the SRD: {sorted(clash)[:5]}")
    catalog.subclasses.update(subs)
    catalog.features.update(feats)
    catalog.levels.extend(rows)
    catalog.subclass_twins = subclass_twins_from(raw_subs, set(catalog.subclasses))


def _merge_official_items(catalog: Catalog) -> None:
    """Tags the SRD items and merges the mundane non-SRD weapons and armor of
    `items-base.json`. SRD records win a key clash."""
    from .official_source import convert_items, items_base_file, load_raw_base_items

    for item in catalog.items.values():
        item.setdefault("source", "SRD")
        item.setdefault("ruleset", "2014")
    for index, item in convert_items(load_raw_base_items(items_base_file()), set(catalog.items)).items():
        catalog.items.setdefault(index, item)


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

    spells, spell_aliases, spell_twins = _load_spells()

    catalog = Catalog(
        classes=_index_by(_load("5e-SRD-Classes.json")),
        levels=_load("5e-SRD-Levels.json"),
        features=_index_by(_load("5e-SRD-Features.json")),
        subclasses=_index_by(_load("5e-SRD-Subclasses.json")),
        races=races,
        subraces=subraces,
        traits=traits,
        backgrounds=backgrounds,
        items=_index_by(_load("5e-SRD-Equipment.json")),
        spells=spells,
        feats=feats,
        spell_aliases=spell_aliases,
        spell_twins=spell_twins,
    )
    _merge_official_subclasses(catalog)
    _merge_official_items(catalog)
    return catalog
