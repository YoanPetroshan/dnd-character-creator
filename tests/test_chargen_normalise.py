"""Tests for chargen/normalise.py — vendor JSON -> the shared chargen.model schema.

Two vendors, two test styles:

- 5e-bits (2014 ruleset): real files committed under chargen/data/srd/*.json
  (synced in Task 2). These tests read the actual files.
- 5etools (2024/official ruleset): no files exist on disk yet — Task 10 fetches
  them. These tests use inline fixture dicts (verified against the real
  5etools API shapes by the task author) so the 2024-path normalizer functions
  are proven correct now and just need real files wired through them later.
"""

import json
import pathlib

import pytest

from chargen import model as M
from chargen import normalise as N

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "chargen" / "data" / "srd"


def _load(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _find(raws, index):
    return next(r for r in raws if r["index"] == index)


# ---------------------------------------------------------------------------
# Real-file fixtures (2014 / 5e-bits)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def races_raw():
    return _load("5e-SRD-Races.json")


@pytest.fixture(scope="module")
def subraces_raw():
    return _load("5e-SRD-Subraces.json")


@pytest.fixture(scope="module")
def traits_raw():
    return _load("5e-SRD-Traits.json")


@pytest.fixture(scope="module")
def classes_raw():
    return _load("5e-SRD-Classes.json")


@pytest.fixture(scope="module")
def levels_raw():
    return _load("5e-SRD-Levels.json")


@pytest.fixture(scope="module")
def spells_raw():
    return _load("5e-SRD-Spells.json")


@pytest.fixture(scope="module")
def equipment_raw():
    return _load("5e-SRD-Equipment.json")


@pytest.fixture(scope="module")
def backgrounds_raw():
    return _load("5e-SRD-Backgrounds.json")


@pytest.fixture(scope="module")
def traits_by_index(traits_raw):
    return {t["index"]: t for t in traits_raw}


# ---------------------------------------------------------------------------
# 2014 / 5e-bits: Spell (Fireball, magic-missile)
# ---------------------------------------------------------------------------


def test_fireball_2014_real_file(spells_raw):
    raw = _find(spells_raw, "fireball")
    spell = N.spell_from_5ebits(raw)

    assert spell.id == "fireball"
    assert spell.name == "Fireball"
    assert spell.level == 3
    assert spell.school == "Evocation"
    assert spell.classes == ["Sorcerer", "Wizard"]
    assert spell.subclasses == ["Lore", "Fiend"]
    assert spell.concentration is False
    assert spell.ritual is False
    assert spell.casting_time == "1 action"
    assert spell.range == "150 feet"
    assert spell.duration == "Instantaneous"
    assert spell.components == {"v": True, "s": True, "m": "A tiny ball of bat guano and sulfur."}
    assert spell.save == "DEX"
    assert spell.damage is not None
    assert "explosion of flame" in spell.description
    assert "1d6 for each slot level" in spell.higher_level


def test_magic_missile_2014_real_file_no_material_no_save(spells_raw):
    """magic-missile has no M component and no dc block — confirms the
    'missing field yields a real absence, never a guess' rule for Spell."""
    raw = _find(spells_raw, "magic-missile")
    spell = N.spell_from_5ebits(raw)

    assert spell.components == {"v": True, "s": True, "m": False}
    assert spell.save is None


# ---------------------------------------------------------------------------
# 2014 / 5e-bits: Weapon (Longsword) — supporting type, not in the brief's
# five dataclasses but required by the plan's own test checklist item.
# ---------------------------------------------------------------------------


def test_longsword_2014_real_file(equipment_raw):
    raw = _find(equipment_raw, "longsword")
    weapon = N.weapon_from_5ebits(raw)

    assert weapon.id == "longsword"
    assert weapon.name == "Longsword"
    assert weapon.category == "Martial"
    assert weapon.damage_dice == "1d8"
    assert weapon.damage_type == "Slashing"
    assert weapon.versatile_damage_dice == "1d10"
    assert "Versatile" in weapon.properties
    assert weapon.cost == "15 gp"
    assert weapon.weight == 3


def test_handaxe_2014_real_file_has_no_versatile_damage(equipment_raw):
    raw = _find(equipment_raw, "handaxe")
    weapon = N.weapon_from_5ebits(raw)
    assert weapon.versatile_damage_dice is None


# ---------------------------------------------------------------------------
# 2014 / 5e-bits: Race + Subrace (Dwarf / Hill Dwarf)
# ---------------------------------------------------------------------------


def test_dwarf_race_2014_real_file(races_raw, traits_by_index):
    raw = _find(races_raw, "dwarf")
    race = N.race_from_5ebits(raw, traits_by_index)

    assert race.id == "dwarf"
    assert race.name == "Dwarf"
    assert race.ruleset == "2014"
    assert race.size == "Medium"
    assert race.speed == 25
    assert race.ability_bonuses == {"CON": 2}
    assert race.languages == ["Common", "Dwarvish"]
    # traits are resolved against the separate Traits.json file, not left as refs
    trait_names = {t.name for t in race.traits}
    assert "Darkvision" in trait_names
    darkvision = next(t for t in race.traits if t.name == "Darkvision")
    assert "see in dim light" in darkvision.text


def test_dwarf_race_missing_ability_bonus_options_yields_none(races_raw, traits_by_index):
    """Dwarf has no 'ability_bonus_options' key at all (only half-elf does in
    the SRD) — the normalizer must yield None, never a fabricated choice."""
    raw = _find(races_raw, "dwarf")
    race = N.race_from_5ebits(raw, traits_by_index)
    assert race.ability_choice is None


def test_half_elf_race_2014_real_file_has_ability_choice(races_raw, traits_by_index):
    raw = _find(races_raw, "half-elf")
    race = N.race_from_5ebits(raw, traits_by_index)
    assert race.ability_choice == {"count": 2, "amount": 1}


def test_hill_dwarf_subrace_2014_real_file(subraces_raw, traits_by_index):
    raw = _find(subraces_raw, "hill-dwarf")
    subrace = N.subrace_from_5ebits(raw, traits_by_index)

    assert subrace.ability_bonuses == {"WIS": 1}
    assert subrace.parent_race_id == "dwarf"
    # 2014 subrace names are ALREADY the full display name — do not compose
    assert subrace.name == "Hill Dwarf"


def test_dwarf_race_embeds_its_normalised_subrace(races_raw, subraces_raw, traits_by_index):
    """Task 3 scope: race.subraces holds the already-normalised Subrace
    objects for children whose parent matches. No ability-bonus COMPOSITION
    happens here — that's a later build() stage, per the brief."""
    race_raw = _find(races_raw, "dwarf")
    all_subraces = [N.subrace_from_5ebits(r, traits_by_index) for r in subraces_raw]
    race = N.race_from_5ebits(race_raw, traits_by_index, subraces=all_subraces)

    assert len(race.subraces) == 1
    assert race.subraces[0].name == "Hill Dwarf"
    assert race.subraces[0].ability_bonuses == {"WIS": 1}
    # composition would be {"CON": 2, "WIS": 1} — confirm we did NOT do that
    assert race.ability_bonuses == {"CON": 2}


# ---------------------------------------------------------------------------
# 2014 / 5e-bits: Background (Acolyte — the only SRD background)
# ---------------------------------------------------------------------------


def test_acolyte_background_2014_real_file(backgrounds_raw):
    raw = _find(backgrounds_raw, "acolyte")
    bg = N.background_from_5ebits(raw)

    assert bg.id == "acolyte"
    assert bg.ruleset == "2014"
    assert set(bg.skill_proficiencies) == {"Insight", "Religion"}
    assert bg.languages == 2  # language_options.choose, no explicit list
    assert bg.feature is not None
    assert bg.feature.name == "Shelter of the Faithful"
    assert "command the respect" in bg.feature.text
    assert len(bg.starting_equipment) == 2
    names = {item.name for item in bg.starting_equipment}
    assert names == {"Clothes, common", "Pouch"}


def test_acolyte_background_2014_has_no_2024_only_fields(backgrounds_raw):
    """Global Finding 1: 0 of 20 2014 backgrounds carry an 'ability' field —
    the real Acolyte record confirms this. origin_feat/ability_choice must
    reflect that absence, not a guess."""
    raw = _find(backgrounds_raw, "acolyte")
    assert "ability" not in raw
    bg = N.background_from_5ebits(raw)
    assert bg.origin_feat is None
    assert bg.ability_choice == []


# ---------------------------------------------------------------------------
# 2014 / 5e-bits: ClassLevelRow (Wizard level 5) + CharClass (Fighter)
# ---------------------------------------------------------------------------


def test_wizard_level_5_row_2014_real_file(levels_raw):
    raw = next(
        r for r in levels_raw if r["class"]["index"] == "wizard" and r["level"] == 5
    )
    row = N.class_level_row_from_5ebits(raw)

    assert row.level == 5
    assert row.proficiency_bonus == 3
    assert row.cantrips_known == 4
    assert row.spell_slots[1] == 4
    assert row.spell_slots[2] == 3
    assert row.spell_slots[3] == 2
    # convention pinned: zero-value slot levels are dropped, not kept at 0
    assert 4 not in row.spell_slots
    assert 9 not in row.spell_slots


def test_fighter_level_1_row_2014_real_file_has_features_and_extras(levels_raw):
    raw = next(
        r for r in levels_raw if r["class"]["index"] == "fighter" and r["level"] == 1
    )
    row = N.class_level_row_from_5ebits(raw)

    assert row.level == 1
    assert row.proficiency_bonus == 2
    assert set(row.features) == {"Fighting Style", "Second Wind"}
    assert row.cantrips_known is None
    assert row.spell_slots == {}
    assert row.extras.get("action_surges") == 0


def test_fighter_class_2014_real_file(classes_raw, levels_raw):
    """Fighter's Levels.json rows include 5 SUBCLASS (Champion) rows sharing
    the same class index and levels — a real vendor quirk, not a fixture
    artifact. class_level_rows_from_5ebits() must filter those out and
    return exactly the 20 main class levels."""
    raw = _find(classes_raw, "fighter")
    level_rows = N.class_level_rows_from_5ebits(levels_raw, "fighter")
    cls = N.class_from_5ebits(raw, level_rows)

    assert cls.id == "fighter"
    assert cls.hit_die == 10
    assert "All armor" in cls.armor
    assert "Shields" in cls.armor
    assert "Simple Weapons" in cls.weapons
    assert "Martial Weapons" in cls.weapons
    assert set(cls.saving_throws) == {"STR", "CON"}
    assert cls.skill_choice["count"] == 2
    assert "Acrobatics" in cls.skill_choice["options"]
    assert "Perception" in cls.skill_choice["options"]
    assert len(cls.levels) == 20


def test_rogue_class_2014_real_file_has_tool_proficiency(classes_raw, levels_raw):
    """Fighter's own proficiency list has no tools — exercise a class that
    does (Rogue: Thieves' Tools) so the 'tools' bucket of the armor/weapons/
    tools split is proven against real data, not just reachable code."""
    raw = _find(classes_raw, "rogue")
    level_rows = N.class_level_rows_from_5ebits(levels_raw, "rogue")
    cls = N.class_from_5ebits(raw, level_rows)
    assert "Thieves' Tools" in cls.tools


# ---------------------------------------------------------------------------
# Ruleset split (Global Finding 1), real-file half + fixture half
# ---------------------------------------------------------------------------


def test_2014_race_has_bonuses_2014_background_has_none(races_raw, backgrounds_raw, traits_by_index):
    race = N.race_from_5ebits(_find(races_raw, "dwarf"), traits_by_index)
    bg = N.background_from_5ebits(_find(backgrounds_raw, "acolyte"))

    assert race.ruleset == "2014"
    assert race.ability_bonuses != {}
    assert bg.ruleset == "2014"
    assert bg.ability_choice == []
    assert bg.origin_feat is None


# ---------------------------------------------------------------------------
# 2024 / 5etools: inline fixtures — no network, no files on disk yet.
# Verified shapes per the task brief; Task 10 wires real files through these
# same normalizer functions.
# ---------------------------------------------------------------------------

XPHB_RACE_FIXTURE = {
    "name": "Elf",
    "source": "XPHB",
    "edition": "one",
    "size": ["M"],
    "speed": 30,
    # 2024 races carry NO "ability" field at all.
    "skillProficiencies": [{"perception": True}],
    "darkvision": 60,
    "entries": [
        "Although elves reach physical maturity...",
        {
            "type": "entries",
            "name": "Fey Ancestry",
            "entries": [
                "You have advantage on saving throws you make to avoid or end the charmed condition."
            ],
        },
        {
            "type": "entries",
            "name": "Keen Senses",
            "entries": ["You have proficiency in the {@skill Perception} skill."],
        },
        {
            "type": "entries",
            "name": "Trance",
            "entries": [
                "You don't sleep and can't be forced to sleep by any means. "
                "You can finish a long rest in 4 hours if you spend it in a "
                "trancelike meditation, during which you retain consciousness."
            ],
        },
    ],
}

XPHB_BACKGROUND_FIXTURE = {
    "name": "Acolyte",
    "source": "XPHB",
    "edition": "one",
    "skillProficiencies": [{"insight": True, "religion": True}],
    "ability": [
        {"choose": {"weighted": {"from": ["int", "wis", "cha"], "weights": [2, 1]}}},
        {"choose": {"weighted": {"from": ["int", "wis", "cha"], "weights": [1, 1, 1]}}},
    ],
    "feats": [{"magic initiate; cleric|xphb": True}],
}

XPHB_BACKGROUND_WITH_TOOLS_FIXTURE = {
    "name": "Guide",
    "source": "XPHB",
    "edition": "one",
    "skillProficiencies": [{"stealth": True, "survival": True}],
    "toolProficiencies": [{"cartographersTools": True}],
    "ability": [
        {"choose": {"weighted": {"from": ["dex", "wis"], "weights": [2, 1]}}},
    ],
}


def test_xphb_race_fixture_has_no_ability_bonuses():
    race = N.race_from_5etools(XPHB_RACE_FIXTURE)
    assert race.ruleset == "2024"
    assert race.ability_bonuses == {}
    assert race.name == "Elf"
    assert race.size == "M"
    assert race.speed == 30


def test_xphb_race_fixture_traits_extracted_and_stripped():
    race = N.race_from_5etools(XPHB_RACE_FIXTURE)
    trait_names = {t.name for t in race.traits}
    assert trait_names == {"Fey Ancestry", "Keen Senses", "Trance"}
    keen_senses = next(t for t in race.traits if t.name == "Keen Senses")
    # {@skill Perception} must be stripped to plain "Perception"
    assert "{@" not in keen_senses.text
    assert "proficiency in the Perception skill" in keen_senses.text


def test_xphb_background_fixture_ability_choice_and_origin_feat():
    bg = N.background_from_5etools(XPHB_BACKGROUND_FIXTURE)

    assert bg.ruleset == "2024"
    assert len(bg.ability_choice) == 2
    assert bg.ability_choice[0] == M.AbilityChoice(options=["INT", "WIS", "CHA"], weights=[2, 1])
    assert bg.ability_choice[1] == M.AbilityChoice(
        options=["INT", "WIS", "CHA"], weights=[1, 1, 1]
    )
    assert bg.origin_feat is not None
    assert "Magic Initiate" in bg.origin_feat
    assert set(bg.skill_proficiencies) == {"Insight", "Religion"}


def test_xphb_background_fixture_tool_proficiencies():
    bg = N.background_from_5etools(XPHB_BACKGROUND_WITH_TOOLS_FIXTURE)
    assert len(bg.tool_proficiencies) == 1
    assert "Cartographer" in bg.tool_proficiencies[0]


def test_2024_race_has_no_bonuses_2024_background_has_both():
    race = N.race_from_5etools(XPHB_RACE_FIXTURE)
    bg = N.background_from_5etools(XPHB_BACKGROUND_FIXTURE)

    assert race.ruleset == "2024"
    assert race.ability_bonuses == {}
    assert bg.ruleset == "2024"
    assert bg.ability_choice != []
    assert bg.origin_feat is not None


# ---------------------------------------------------------------------------
# 2024 / 5etools: subrace naming quirk
# ---------------------------------------------------------------------------

XPHB_SUBRACE_FIXTURES = [
    {"name": "Hill", "raceName": "Dwarf", "raceSource": "PHB", "ability": [{"wis": 1}]},
    {"name": "High", "raceName": "Elf", "raceSource": "PHB", "ability": [{"int": 1}]},
    # ~5% of 5etools subrace records have no "name" at all (base variant)
    {"raceName": "Human", "raceSource": "PHB", "ability": [{"str": 1}]},
]


def test_5etools_subrace_name_composes_from_variant_plus_race_name():
    subraces = N.subraces_from_5etools(XPHB_SUBRACE_FIXTURES)
    assert len(subraces) == 2
    names = {s.name for s in subraces}
    assert names == {"Hill Dwarf", "High Elf"}


def test_5etools_unnamed_subrace_is_skipped_not_blank():
    subraces = N.subraces_from_5etools(XPHB_SUBRACE_FIXTURES)
    assert all(s.name for s in subraces)
    assert not any(s.name.strip() == "" for s in subraces)


def test_2014_subrace_name_used_as_is_no_double_composition(subraces_raw, traits_by_index):
    """The 2014 vendor's subrace 'name' is ALREADY 'Hill Dwarf' — composing
    'Hill Dwarf' + 'Dwarf' would wrongly yield 'Hill Dwarf Dwarf'."""
    raw = _find(subraces_raw, "hill-dwarf")
    subrace = N.subrace_from_5ebits(raw, traits_by_index)
    assert subrace.name == "Hill Dwarf"
    assert "Dwarf Dwarf" not in subrace.name


# ---------------------------------------------------------------------------
# Task 10: real-data bugs — ruleset tagging, id collisions, _copy skipping,
# subrace source/traits. Small hand-written fixtures, not the real files
# (which live outside the repo, fetched by chargen/sync.py --official).
# ---------------------------------------------------------------------------


def test_edition_one_tags_2024_ruleset():
    raw = {"name": "Aasimar", "source": "XPHB", "edition": "one"}
    race = N.race_from_5etools(raw)
    assert race.ruleset == "2024"


def test_missing_edition_key_tags_2014_ruleset():
    # Real omnibus data: no "edition" key at all means pre-2024 content —
    # hardcoding "2024" would silently mislabel ~90% of the real file.
    raw = {"name": "Dwarf", "source": "PHB", "ability": [{"con": 2}]}
    race = N.race_from_5etools(raw)
    assert race.ruleset == "2014"


def test_background_edition_one_tags_2024_ruleset():
    raw = {"name": "Sage", "source": "XPHB", "edition": "one"}
    bg = N.background_from_5etools(raw)
    assert bg.ruleset == "2024"


def test_background_missing_edition_tags_2014_ruleset():
    raw = {"name": "Sage", "source": "PHB"}
    bg = N.background_from_5etools(raw)
    assert bg.ruleset == "2014"


def test_subrace_edition_one_tags_2024_ruleset():
    raw = {"name": "Draconblood", "source": "EGW", "edition": "one",
           "raceName": "Dragonborn", "raceSource": "PHB"}
    subrace = N.subrace_from_5etools(raw)
    assert subrace.ruleset == "2024"


def test_subrace_missing_edition_tags_2014_ruleset():
    raw = {"name": "Draconblood", "source": "EGW",
           "raceName": "Dragonborn", "raceSource": "PHB"}
    subrace = N.subrace_from_5etools(raw)
    assert subrace.ruleset == "2014"


def test_same_race_name_different_source_gets_two_distinct_ids():
    """Real data: 37 duplicate race names across sourcebooks (e.g. "Dwarf"
    from PHB and "Dwarf" from XPHB are two mechanically distinct records).
    Bare _slug(name) collisions would silently overwrite one in a
    {id: record} dict — source-qualified ids keep the merge additive."""
    raws = [
        {"name": "Dwarf", "source": "PHB", "ability": [{"con": 2}]},
        {"name": "Dwarf", "source": "XPHB", "edition": "one"},
    ]
    races = N.races_from_5etools(raws)
    ids = {r.id for r in races}
    assert len(races) == 2
    assert len(ids) == 2
    assert "dwarf-phb" in ids
    assert "dwarf-xphb" in ids


def test_same_background_name_different_source_gets_two_distinct_ids():
    raws = [
        {"name": "Acolyte", "source": "PHB"},
        {"name": "Acolyte", "source": "XPHB", "edition": "one"},
    ]
    backgrounds = N.backgrounds_from_5etools(raws)
    ids = {b.id for b in backgrounds}
    assert len(backgrounds) == 2
    assert len(ids) == 2
    assert "acolyte-phb" in ids
    assert "acolyte-xphb" in ids


def test_race_with_copy_key_is_skipped_by_single_normalizer():
    raw = {
        "name": "Amonkhet",
        "source": "PSA",
        "_copy": {"name": "Variant", "source": "PHB", "raceName": "Human"},
    }
    assert N.race_from_5etools(raw) is None


def test_race_with_copy_key_dropped_by_list_wrapper_without_erroring():
    raws = [
        {"name": "Dwarf", "source": "PHB", "ability": [{"con": 2}]},
        {
            "name": "Amonkhet",
            "source": "PSA",
            "_copy": {"name": "Variant", "source": "PHB", "raceName": "Human"},
        },
    ]
    races = N.races_from_5etools(raws)
    assert len(races) == 1
    assert races[0].name == "Dwarf"


def test_background_with_copy_key_is_skipped():
    raw = {"name": "Anthropologist", "source": "TCE",
           "_copy": {"name": "Anthropologist", "source": "GGR"}}
    assert N.background_from_5etools(raw) is None


def test_subrace_with_copy_key_is_skipped():
    raw = {"name": "Some Variant", "source": "XXX", "raceName": "Human",
           "_copy": {"name": "Base", "source": "PHB", "raceName": "Human"}}
    assert N.subrace_from_5etools(raw) is None


def test_subrace_source_is_own_book_not_parent_race_source():
    """Real record: Draconblood dragonborn subrace is from EGW, but its
    parent race (Dragonborn) is from PHB — subrace.source must be EGW, not
    the parent's book."""
    raw = {
        "name": "Draconblood",
        "source": "EGW",
        "raceName": "Dragonborn",
        "raceSource": "PHB",
        "ability": [{"int": 2, "cha": 1}],
        "entries": [],
    }
    subrace = N.subrace_from_5etools(raw)
    assert subrace.source == "EGW"
    assert subrace.source != "PHB"


def test_subrace_traits_populated_from_entries_not_hardcoded_empty():
    raw = {
        "name": "Draconblood",
        "source": "EGW",
        "raceName": "Dragonborn",
        "raceSource": "PHB",
        "ability": [{"int": 2, "cha": 1}],
        "entries": [
            {
                "type": "entries",
                "name": "Draconic Resistance",
                "entries": ["You have resistance to {@damage acid} damage."],
            }
        ],
    }
    subrace = N.subrace_from_5etools(raw)
    expected = N._entries_to_traits_5etools(raw["entries"])
    assert subrace.traits == expected
    assert len(subrace.traits) == 1
    assert subrace.traits[0].name == "Draconic Resistance"
    assert "{@" not in subrace.traits[0].text


def test_subrace_parent_race_id_matches_qualified_race_id():
    """parent_race_id must be qualified with the PARENT race's own source
    (raceSource), matching exactly the id race_from_5etools() produces for
    that same race — not the subrace's own (usually different) source."""
    race_raw = {"name": "Dragonborn", "source": "PHB", "ability": [{"str": 2, "cha": 1}]}
    subrace_raw = {
        "name": "Draconblood",
        "source": "EGW",
        "raceName": "Dragonborn",
        "raceSource": "PHB",
        "ability": [{"int": 2, "cha": 1}],
    }
    race = N.race_from_5etools(race_raw)
    subrace = N.subrace_from_5etools(subrace_raw)
    assert subrace.parent_race_id == race.id
    assert subrace.parent_race_id == "dragonborn-phb"


# ---------------------------------------------------------------------------
# Markup stripper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("{@skill Perception}", "Perception"),
        ("{@dice 1d4}", "1d4"),
        ("{@condition charmed}", "charmed"),
        ("Plain prose with no tags at all.", "Plain prose with no tags at all."),
        (
            "You have proficiency in the {@skill Perception} skill.",
            "You have proficiency in the Perception skill.",
        ),
        ("{@dice 1d4|1d4|extra}", "1d4"),
    ],
)
def test_strip_5etools_tags(raw, expected):
    assert N._strip_5etools_tags(raw) == expected


# ---------------------------------------------------------------------------
# 5etools race speed, and the background fields that used to be hardcoded
# empty (final fix wave)
# ---------------------------------------------------------------------------


def test_5etools_dict_speed_is_coerced_to_the_walking_speed():
    """29 of the real official races carry speed as a dict of movement modes
    rather than an int. Race.speed is typed int and every consumer prints it
    as a number ("[object Object] ft" in the UI otherwise)."""
    race = N.race_from_5etools(
        {"name": "Aarakocra", "source": "MPMM", "speed": {"walk": 30, "fly": 50}})
    assert race.speed == 30


def test_5etools_other_movement_modes_become_a_trait_rather_than_vanishing():
    race = N.race_from_5etools(
        {"name": "Aarakocra", "source": "MPMM", "speed": {"walk": 20, "fly": 50}})
    speed_trait = next(t for t in race.traits if t.name == "Speed")
    assert "Fly speed 50 ft." in speed_trait.text


def test_5etools_true_valued_speed_mode_says_equal_to_walking():
    """5etools' shorthand: `"climb": true` means "equal to your walking
    speed", not a missing number."""
    race = N.race_from_5etools(
        {"name": "Hadozee", "source": "AAG", "speed": {"walk": 30, "climb": True}})
    speed_trait = next(t for t in race.traits if t.name == "Speed")
    assert "equal to your walking speed" in speed_trait.text


def test_5etools_speed_trait_is_not_added_twice():
    """4 of the 29 real dict-speed races already carry their own entry named
    "Speed" saying exactly this."""
    race = N.race_from_5etools({
        "name": "Tabaxi", "source": "MPMM", "speed": {"walk": 30, "climb": True},
        "entries": [{"name": "Speed",
                     "entries": ["Your walking speed is 30 feet, and you have "
                                 "a climbing speed equal to your walking speed."]}],
    })
    assert [t.name for t in race.traits].count("Speed") == 1
    assert race.speed == 30


def test_5etools_int_speed_is_untouched_and_adds_no_trait():
    race = N.race_from_5etools({"name": "Dwarf", "source": "PHB", "speed": 25})
    assert race.speed == 25
    assert not any(t.name == "Speed" for t in race.traits)


_PHB_ACOLYTE_EQUIPMENT_FIXTURE = {
    "name": "Acolyte",
    "source": "PHB",
    "languageProficiencies": [{"anyStandard": 2}],
    "startingEquipment": [
        {"_": [
            {"item": "holy symbol|phb", "displayName": "holy symbol (a gift)"},
            {"special": "sticks of incense", "quantity": 5},
            "common clothes|phb",
            {"item": "pouch|phb", "containsValue": 1500},
        ]},
        # An either/or kit — a player choice the Draft cannot record, so it
        # is deliberately not resolved.
        {"a": [{"item": "book|phb", "displayName": "prayer book"}],
         "b": [{"special": "prayer wheel"}]},
    ],
    "entries": [
        {"type": "list", "items": [
            {"type": "item", "name": "Equipment:", "entry": "A {@item holy symbol|phb}"}]},
        {"name": "Feature: Shelter of the Faithful", "type": "entries",
         "entries": ["You command the respect of those who share your "
                     "{@skill Religion|PHB} faith."],
         "data": {"isFeature": True}},
        {"name": "Suggested Characteristics", "type": "entries",
         "entries": ["Acolytes are shaped by their experience in temples."]},
    ],
}


def test_5etools_background_starting_equipment_resolves_the_granted_block():
    bg = N.background_from_5etools(_PHB_ACOLYTE_EQUIPMENT_FIXTURE)
    names = [i.name for i in bg.starting_equipment]
    assert names == [
        "Holy symbol (a gift)",
        "Sticks of incense",
        "Common Clothes",
        "Pouch (containing 15 gp)",
    ]
    assert [i.quantity for i in bg.starting_equipment] == [1, 5, 1, 1]
    # ids are 5etools slugs, not catalog ids — None rather than a plausible
    # id nothing can look up.
    assert all(i.id is None for i in bg.starting_equipment)


def test_5etools_background_either_or_equipment_is_not_resolved():
    """Both branches of an "a"/"b" kit would be wrong, and picking one for
    the player is the engine inventing a decision — same disclosed cut as
    the SRD classes' starting_equipment_options."""
    bg = N.background_from_5etools(_PHB_ACOLYTE_EQUIPMENT_FIXTURE)
    names = [i.name for i in bg.starting_equipment]
    assert not any("rayer" in n for n in names)


def test_5etools_background_coin_values_are_copper():
    bg = N.background_from_5etools({
        "name": "Rich One", "source": "XPHB",
        "startingEquipment": [{"_": [{"value": 800}, {"value": 50}, {"value": 7}]}],
    })
    assert [i.name for i in bg.starting_equipment] == ["8 gp", "5 sp", "7 cp"]


def test_5etools_background_equipment_type_names_the_category():
    bg = N.background_from_5etools({
        "name": "Entertainer", "source": "PHB",
        "startingEquipment": [{"_": [{"equipmentType": "instrumentMusical"}]}],
    })
    assert bg.starting_equipment[0].name == "Musical instrument (any one)"


def test_5etools_background_feature_is_the_feature_entry_only():
    bg = N.background_from_5etools(_PHB_ACOLYTE_EQUIPMENT_FIXTURE)
    assert bg.feature is not None
    # The "Feature: " prefix is stripped, and neither the proficiency summary
    # list nor "Suggested Characteristics" is mistaken for the feature.
    assert bg.feature.name == "Shelter of the Faithful"
    assert "{@" not in bg.feature.text
    assert "respect" in bg.feature.text


def test_5etools_2024_background_has_no_feature_and_that_is_correct():
    """2024 replaced the background feature with an origin feat; None here
    is the true answer, not a parse gap."""
    bg = N.background_from_5etools(XPHB_BACKGROUND_FIXTURE)
    assert bg.feature is None
    assert bg.origin_feat is not None


def test_5etools_race_languages_are_the_named_ones():
    """Race.languages is list[str] — 74 of the 144 real official races name
    real languages, which used to be dropped for a hardcoded []."""
    race = N.race_from_5etools({
        "name": "Dwarf", "source": "PHB",
        "languageProficiencies": [{"common": True, "dwarvish": True}]})
    assert race.languages == ["Common", "Dwarvish"]


def test_5etools_race_free_language_choice_is_not_invented_into_a_name():
    """"other"/"anyStandard" mean "one of your choice" — a count, which
    list[str] has no room for. Better empty than a language called "Other"."""
    race = N.race_from_5etools({
        "name": "Human", "source": "PHB",
        "languageProficiencies": [{"common": True, "other": True}]})
    assert race.languages == ["Common"]


def test_5etools_background_languages_count_and_names():
    count_only = N.background_from_5etools(
        {"name": "A", "source": "PHB", "languageProficiencies": [{"anyStandard": 2}]})
    assert count_only.languages == 2

    named = N.background_from_5etools(
        {"name": "B", "source": "PHB", "languageProficiencies": [{"dwarvish": True}]})
    assert named.languages == ["Dwarvish"]

    chooser = N.background_from_5etools(
        {"name": "C", "source": "GGR",
         "languageProficiencies": [{"choose": {"from": ["elvish", "giant"]}}]})
    assert chooser.languages == 1

    none_at_all = N.background_from_5etools({"name": "D", "source": "PHB"})
    assert none_at_all.languages == []
