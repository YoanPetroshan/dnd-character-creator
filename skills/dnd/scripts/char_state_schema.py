#!/usr/bin/env python3
"""char_state_schema.py — the Character dataclass and its YAML I/O.

This is the ONLY module that knows the on-disk YAML shape. Every other
char_state module imports `Character` and the load/save functions from
here rather than touching YAML directly, so the schema has exactly one
place it can drift from what's actually on disk.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import paths  # noqa: E402


@dataclass
class ClassLevel:
    cls: str
    subclass: str
    level: int


@dataclass
class AbilityScores:
    STR: int
    DEX: int
    CON: int
    INT: int
    WIS: int
    CHA: int


@dataclass
class DeathSaves:
    successes: int = 0
    failures: int = 0


@dataclass
class HitDieUsage:
    cls: str
    die: int
    used: int = 0


@dataclass
class CombatStats:
    hp_current: int
    hp_max: int
    hp_temp: int = 0
    speed: int = 30
    death_saves: DeathSaves = field(default_factory=DeathSaves)
    hit_dice: list[HitDieUsage] = field(default_factory=list)


@dataclass
class Proficiencies:
    saving_throws: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    armor: list[str] = field(default_factory=list)
    weapons: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass
class Conditions:
    inspiration: bool = False
    exhaustion: int = 0
    active: list[str] = field(default_factory=list)
    attunement: list[str] = field(default_factory=list)
    weapon_mastery: list[str] = field(default_factory=list)


@dataclass
class Personality:
    traits: str = ""
    ideals: str = ""
    bonds: str = ""
    flaws: str = ""


@dataclass
class FeatureTrait:
    name: str
    description: str
    source: str


@dataclass
class Currency:
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


@dataclass
class EquipmentItem:
    name: str
    equipped: bool = False
    quantity: int = 1


@dataclass
class MiscItem:
    name: str
    quantity: int = 1
    note: str = ""


@dataclass
class SpellcastingClass:
    cls: str
    ability: str


@dataclass
class SpellEntry:
    name: str
    cls: str
    prepared: bool = False


@dataclass
class SlotPool:
    max: int = 0
    used: int = 0


@dataclass
class Character:
    name: str
    race: str
    background: str
    alignment: str
    player: str
    classes: list[ClassLevel]
    ability_scores: AbilityScores
    combat: CombatStats
    proficiencies: Proficiencies
    conditions: Conditions
    personality: Personality
    features_traits: list[FeatureTrait]
    backstory: str
    currency: Currency
    equipment: list[EquipmentItem]
    misc_items: list[MiscItem]
    spellcasting: list[SpellcastingClass]
    spells: list[SpellEntry]
    spell_slots: dict[int, SlotPool]
    pact_magic_slots: Optional[SlotPool]


def character_yaml_path(campaign: str, slug: str) -> Path:
    return paths.find_campaign(campaign) / "characters" / f"{slug}.yaml"


def character_markdown_path(campaign: str, slug: str) -> Path:
    return paths.find_campaign(campaign) / "characters" / f"{slug}.md"


def atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` via a sibling tmp file + rename.

    `Path.replace()` is atomic on POSIX, so a crash mid-write can never leave
    a truncated file behind — a reader sees either the old contents or the
    new ones, never half of either. Shared by every file this system
    generates (the canonical YAML and the rendered markdown view alike); the
    markdown write used to be a bare write_text() and could be truncated.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def save_character(campaign: str, slug: str, character: Character) -> None:
    path = character_yaml_path(campaign, slug)
    data = asdict(character)
    atomic_write_text(path, yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=False,
    ))


def _slot_pool(d) -> SlotPool:
    return SlotPool(**d) if d else SlotPool()


def load_character(campaign: str, slug: str) -> Character:
    path = character_yaml_path(campaign, slug)
    if not path.exists():
        raise FileNotFoundError(f"no character sheet at {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    return Character(
        name=data["name"],
        race=data["race"],
        background=data["background"],
        alignment=data["alignment"],
        player=data.get("player", ""),
        classes=[ClassLevel(**c) for c in data.get("classes", [])],
        ability_scores=AbilityScores(**data["ability_scores"]),
        combat=CombatStats(
            hp_current=data["combat"]["hp_current"],
            hp_max=data["combat"]["hp_max"],
            hp_temp=data["combat"].get("hp_temp", 0),
            speed=data["combat"].get("speed", 30),
            death_saves=DeathSaves(**data["combat"].get("death_saves", {})),
            hit_dice=[HitDieUsage(**h) for h in data["combat"].get("hit_dice", [])],
        ),
        proficiencies=Proficiencies(**data.get("proficiencies", {})),
        conditions=Conditions(**data.get("conditions", {})),
        personality=Personality(**data.get("personality", {})),
        features_traits=[FeatureTrait(**f) for f in data.get("features_traits", [])],
        backstory=data.get("backstory", ""),
        currency=Currency(**data.get("currency", {})),
        equipment=[EquipmentItem(**e) for e in data.get("equipment", [])],
        misc_items=[MiscItem(**m) for m in data.get("misc_items", [])],
        spellcasting=[SpellcastingClass(**s) for s in data.get("spellcasting", [])],
        spells=[SpellEntry(**s) for s in data.get("spells", [])],
        spell_slots={int(k): _slot_pool(v) for k, v in (data.get("spell_slots") or {}).items()},
        pact_magic_slots=_slot_pool(data["pact_magic_slots"]) if data.get("pact_magic_slots") else None,
    )
