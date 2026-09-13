"""The shared character-data schema.

Every vendor (5e-bits/2014, 5etools/2024) disagrees on shape — 5e-bits uses
`{"index","name","url"}` reference objects, 5etools uses inline
`{@tag visible|extra}` markup strings. `chargen/normalise.py` converts both
into these frozen dataclasses so everything downstream (the builder, the
API) only ever sees one schema, regardless of which vendor or ruleset a
record came from.

Fields a vendor's record simply doesn't carry are populated with `None` (or
an empty collection, per the field's declared type) — never a guessed or
fabricated value.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Trait:
    """A named trait/feature with descriptive text — a racial trait, a
    background feature, a class feature entry, etc."""

    name: str
    text: str


@dataclass(frozen=True)
class ItemRef:
    """A reference to a piece of equipment plus how many of it."""

    id: str | None
    name: str
    quantity: int


@dataclass(frozen=True)
class AbilityChoice:
    """One legal ability-bonus pattern: pick `len(weights)` distinct
    abilities from `options` and assign the weights in order.

    2024-only (Global Finding 2). E.g. Acolyte (XPHB) has two of these:
    options=["INT","WIS","CHA"], weights=[2,1] and weights=[1,1,1].
    """

    options: list[str]  # ["INT","WIS","CHA"]
    weights: list[int]  # [2,1] or [1,1,1]


@dataclass(frozen=True)
class Subrace:
    id: str
    name: str  # already-composed display name, e.g. "Hill Dwarf"
    source: str
    ruleset: str  # "2014" | "2024"
    parent_race_id: str
    ability_bonuses: dict[str, int]
    traits: list[Trait]


@dataclass(frozen=True)
class Race:
    id: str
    name: str
    source: str
    ruleset: str  # "2014" | "2024"
    size: str
    speed: int
    ability_bonuses: dict[str, int]  # {"DEX": 2}
    ability_choice: dict | None  # {"count": 2, "amount": 1}
    traits: list[Trait]
    subraces: list[Subrace]
    languages: list[str]


@dataclass(frozen=True)
class Background:
    id: str
    name: str
    source: str
    ruleset: str  # "2014" | "2024"
    skill_proficiencies: list[str]
    tool_proficiencies: list[str]
    languages: int | list[str]
    starting_equipment: list[ItemRef]
    feature: Trait | None
    origin_feat: str | None  # 2024 only
    ability_choice: list[AbilityChoice]  # 2024 only; see finding 2


@dataclass(frozen=True)
class ClassLevelRow:
    level: int
    proficiency_bonus: int
    features: list[str]
    spell_slots: dict[int, int]  # {1: 4, 2: 3} — zero-slot levels are dropped
    cantrips_known: int | None
    extras: dict  # Rages, Ki, Sneak Attack...


@dataclass(frozen=True)
class CharClass:
    """A class's fixed shape (proficiencies, saving throws, skill choice)
    plus its full level table. Not in the plan brief's five dataclasses, but
    required to hold the class-shape fields the plan's own normalisation
    notes describe (armor/weapon/tool split, saving throws, skill choice) —
    ClassLevelRow alone only covers per-level data from the separate Levels
    file, not the class's fixed shape from the Classes file."""

    id: str
    name: str
    source: str
    ruleset: str  # "2014" | "2024"
    hit_die: int
    armor: list[str]
    weapons: list[str]
    tools: list[str]
    saving_throws: list[str]  # ["STR", "CON"]
    skill_choice: dict | None  # {"count": 2, "options": [...]}
    levels: list[ClassLevelRow]


@dataclass(frozen=True)
class Weapon:
    """Not in the plan brief's five dataclasses, but required by the plan's
    own test checklist ('Longsword is 1d8 slashing, martial, versatile
    1d10'), which needs somewhere to land."""

    id: str
    name: str
    source: str
    category: str  # "Martial" | "Simple"
    damage_dice: str | None
    damage_type: str | None
    versatile_damage_dice: str | None
    properties: list[str]
    weight: float | None
    cost: str | None


@dataclass(frozen=True)
class Spell:
    id: str
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    duration: str
    components: dict  # {"v": True, "s": True, "m": "bat guano"}
    concentration: bool
    ritual: bool
    classes: list[str]  # ["Sorcerer", "Wizard"]
    subclasses: list[str]
    description: str
    higher_level: str
    damage: dict | None
    save: str | None
