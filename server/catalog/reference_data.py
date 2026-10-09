"""Small, hand-maintained reference tables for open 5e SRD content that
Backgrounds.json references via a resource_list URL (e.g.
"/api/2014/languages") but that isn't bundled as its own file under
chargen/data/srd/ — languages are pure open-content SRD material, not
sourcebook-specific, so hardcoding the standard list here is safe. Also
carries the skill→ability mapping, which the bundled data never states
explicitly as its own table (it only shows up implicitly, skill by skill,
inside each class's proficiency_choices).
"""
from __future__ import annotations

LANGUAGES: list[dict[str, str]] = [
    {"index": "common", "name": "Common"},
    {"index": "dwarvish", "name": "Dwarvish"},
    {"index": "elvish", "name": "Elvish"},
    {"index": "giant", "name": "Giant"},
    {"index": "gnomish", "name": "Gnomish"},
    {"index": "goblin", "name": "Goblin"},
    {"index": "halfling", "name": "Halfling"},
    {"index": "orc", "name": "Orc"},
    {"index": "abyssal", "name": "Abyssal"},
    {"index": "celestial", "name": "Celestial"},
    {"index": "draconic", "name": "Draconic"},
    {"index": "deep-speech", "name": "Deep Speech"},
    {"index": "infernal", "name": "Infernal"},
    {"index": "primordial", "name": "Primordial"},
    {"index": "sylvan", "name": "Sylvan"},
    {"index": "undercommon", "name": "Undercommon"},
]

# SRD skill `index` -> the UPPERCASE ability score it's keyed off of.
# Verified directly against every skill index referenced anywhere in
# chargen/data/srd/5e-SRD-Classes.json's proficiency_choices (18 total).
SKILL_ABILITY: dict[str, str] = {
    "skill-acrobatics": "DEX",
    "skill-animal-handling": "WIS",
    "skill-arcana": "INT",
    "skill-athletics": "STR",
    "skill-deception": "CHA",
    "skill-history": "INT",
    "skill-insight": "WIS",
    "skill-intimidation": "CHA",
    "skill-investigation": "INT",
    "skill-medicine": "WIS",
    "skill-nature": "INT",
    "skill-perception": "WIS",
    "skill-performance": "CHA",
    "skill-persuasion": "CHA",
    "skill-religion": "INT",
    "skill-sleight-of-hand": "DEX",
    "skill-stealth": "DEX",
    "skill-survival": "WIS",
}

ABILITIES: list[str] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

# SRD skill `index` -> its standard 5e display name. Open SRD content,
# same "safe to hardcode" reasoning as LANGUAGES above — no bundled SRD
# file carries these as their own list; they only exist embedded inside
# each class's proficiency_choices option labels, which doesn't help code
# that starts from a skill `index` (e.g. derived.skills' keys) rather than
# from a class's own choice envelope.
SKILL_NAMES: dict[str, str] = {
    "skill-acrobatics": "Acrobatics",
    "skill-animal-handling": "Animal Handling",
    "skill-arcana": "Arcana",
    "skill-athletics": "Athletics",
    "skill-deception": "Deception",
    "skill-history": "History",
    "skill-insight": "Insight",
    "skill-intimidation": "Intimidation",
    "skill-investigation": "Investigation",
    "skill-medicine": "Medicine",
    "skill-nature": "Nature",
    "skill-perception": "Perception",
    "skill-performance": "Performance",
    "skill-persuasion": "Persuasion",
    "skill-religion": "Religion",
    "skill-sleight-of-hand": "Sleight of Hand",
    "skill-stealth": "Stealth",
    "skill-survival": "Survival",
}

# Every "Tools"-category item in the bundled SRD equipment list
# (chargen/data/srd/5e-SRD-Equipment.json), hardcoded here for the same
# reason as LANGUAGES/SKILL_NAMES above: choices.py's build_choice_options
# is a pure function of its `from_field` envelope, with no Catalog access,
# so an "any tool"/"any artisan's tool"/"any musical instrument" wildcard
# option set (sourcebook races' skillProficiencies/toolProficiencies
# "any"/"anyArtisansTool"/"anyMusicalInstrument" shapes, Phase 4a) needs its
# own source of "every possible tool", independent of catalog.items. `index`
# matches catalog.items' own equipment ids exactly (verified directly
# against 5e-SRD-Equipment.json); `category` matches that same file's own
# `tool_category` field verbatim ("Artisan's Tools", "Gaming Sets",
# "Musical Instrument", "Other Tools") so a category filter can compare
# against it without any translation table of its own.
TOOLS: list[dict[str, str]] = [
    {"index": "alchemists-supplies", "name": "Alchemist's Supplies", "category": "Artisan's Tools"},
    {"index": "brewers-supplies", "name": "Brewer's Supplies", "category": "Artisan's Tools"},
    {"index": "calligraphers-supplies", "name": "Calligrapher's Supplies", "category": "Artisan's Tools"},
    {"index": "carpenters-tools", "name": "Carpenter's Tools", "category": "Artisan's Tools"},
    {"index": "cartographers-tools", "name": "Cartographer's Tools", "category": "Artisan's Tools"},
    {"index": "cobblers-tools", "name": "Cobbler's Tools", "category": "Artisan's Tools"},
    {"index": "cooks-utensils", "name": "Cook's utensils", "category": "Artisan's Tools"},
    {"index": "glassblowers-tools", "name": "Glassblower's Tools", "category": "Artisan's Tools"},
    {"index": "jewelers-tools", "name": "Jeweler's Tools", "category": "Artisan's Tools"},
    {"index": "leatherworkers-tools", "name": "Leatherworker's Tools", "category": "Artisan's Tools"},
    {"index": "masons-tools", "name": "Mason's Tools", "category": "Artisan's Tools"},
    {"index": "painters-supplies", "name": "Painter's Supplies", "category": "Artisan's Tools"},
    {"index": "potters-tools", "name": "Potter's Tools", "category": "Artisan's Tools"},
    {"index": "smiths-tools", "name": "Smith's Tools", "category": "Artisan's Tools"},
    {"index": "tinkers-tools", "name": "Tinker's Tools", "category": "Artisan's Tools"},
    {"index": "weavers-tools", "name": "Weaver's Tools", "category": "Artisan's Tools"},
    {"index": "woodcarvers-tools", "name": "Woodcarver's Tools", "category": "Artisan's Tools"},
    {"index": "dice-set", "name": "Dice Set", "category": "Gaming Sets"},
    {"index": "playing-card-set", "name": "Playing Card Set", "category": "Gaming Sets"},
    {"index": "bagpipes", "name": "Bagpipes", "category": "Musical Instrument"},
    {"index": "drum", "name": "Drum", "category": "Musical Instrument"},
    {"index": "dulcimer", "name": "Dulcimer", "category": "Musical Instrument"},
    {"index": "flute", "name": "Flute", "category": "Musical Instrument"},
    {"index": "lute", "name": "Lute", "category": "Musical Instrument"},
    {"index": "lyre", "name": "Lyre", "category": "Musical Instrument"},
    {"index": "horn", "name": "Horn", "category": "Musical Instrument"},
    {"index": "pan-flute", "name": "Pan flute", "category": "Musical Instrument"},
    {"index": "shawm", "name": "Shawm", "category": "Musical Instrument"},
    {"index": "viol", "name": "Viol", "category": "Musical Instrument"},
    {"index": "navigators-tools", "name": "Navigator's Tools", "category": "Other Tools"},
    {"index": "thieves-tools", "name": "Thieves' Tools", "category": "Other Tools"},
]

# The level each class first grants its subclass-defining feature (e.g.
# Divine Domain, Primal Path) — read directly from each class's own
# features list in 5e-SRD-Levels.json. There is no structured "choose
# your subclass" envelope anywhere in the bundled data; the unlock level
# is identified only by which specifically-named feature first appears,
# so this table is hardcoded from that empirical reading — the same
# "open RAW fact the bundled JSON doesn't expose structurally" precedent
# as SKILL_ABILITY/LANGUAGES/SKILL_NAMES above. Verified against the
# actual per-class features lists at levels 1-3 while writing this plan.
SUBCLASS_UNLOCK_LEVEL: dict[str, int] = {
    "cleric": 1, "sorcerer": 1, "warlock": 1,
    "wizard": 2, "druid": 2,
    "barbarian": 3, "bard": 3, "fighter": 3, "monk": 3,
    "paladin": 3, "ranger": 3, "rogue": 3,
}

# Full-caster classes (contribute their own level to multiclass caster
# level per 5e RAW). Real 5e distinction not present as a flag anywhere
# in the bundled SRD data, so hardcoded from the standard SRD class list.
FULL_CASTER_CLASSES = {"bard", "cleric", "druid", "sorcerer", "wizard"}

# Half-caster classes use ability_modifier + floor(class_level / 2) for
# their prepared-spell count, not the full-caster ability_modifier +
# class_level formula — real 5e RAW, not present as a distinguishing
# flag anywhere in the bundled SRD data. Ranger's own level rows happen
# to carry an explicit `spells_known` field (the known-caster branch
# below), so this only actually changes Paladin's behavior today — but
# the set describes a real RAW fact about both classes, independent of
# which code branch currently reads it.
HALF_CASTER_CLASSES = {"paladin", "ranger"}


def proficiency_label(prof_id: str) -> str:
    """Human-readable form of a slug proficiency id ("light-armor" ->
    "Light armor"), used by the markdown/PDF exports."""
    return prof_id.replace("-", " ").capitalize()


# Hand-maintained mechanical effects of SRD class features, keyed by the
# feature `index` in 5e-SRD-Features.json (the SRD data does not encode
# them structurally). Effect keys:
#   ac_formula          {"base", "abilities", "allows_shield"}: alternative
#                       unarmored AC; the best candidate wins, never summed,
#                       and it only applies with no body armor.
#   ac_bonus_armored    flat AC bonus only while wearing body armor.
#   speed_bonus_by_class_level  {class level: ft}, only with no armor and
#                       no shield; the highest reached level applies.
#   hp_per_class_level  extra max HP per level of the granting class.
#   half_proficiency    "floor" (Jack of All Trades, every non-proficient
#                       check) or "ceil" (Remarkable Athlete, STR/DEX/CON).
#   ability_bonus / ability_cap  Primal Champion (+4 STR/CON, cap 24).
#   attack_bonus        stored for the attacks slice; no consumer yet.
CLASS_FEATURE_EFFECTS: dict[str, dict] = {
    "barbarian-unarmored-defense": {"ac_formula": {"base": 10, "abilities": ["DEX", "CON"], "allows_shield": True}},
    "monk-unarmored-defense": {"ac_formula": {"base": 10, "abilities": ["DEX", "WIS"], "allows_shield": False}},
    "draconic-resilience": {
        "ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True},
        "hp_per_class_level": 1,
    },
    "unarmored-movement-1": {"speed_bonus_by_class_level": {2: 10, 6: 15, 10: 20, 14: 25, 18: 30}},
    "fighter-fighting-style-defense": {"ac_bonus_armored": 1},
    "fighting-style-defense": {"ac_bonus_armored": 1},
    "ranger-fighting-style-defense": {"ac_bonus_armored": 1},
    "fighter-fighting-style-archery": {"attack_bonus": {"ranged": 2}},
    "ranger-fighting-style-archery": {"attack_bonus": {"ranged": 2}},
    "fighter-fighting-style-dueling": {"damage_bonus": {"one_handed_melee": 2}},
    "fighting-style-dueling": {"damage_bonus": {"one_handed_melee": 2}},
    "ranger-fighting-style-dueling": {"damage_bonus": {"one_handed_melee": 2}},
    "jack-of-all-trades": {"half_proficiency": "floor"},
    "remarkable-athlete": {"half_proficiency": "ceil"},
    "primal-champion": {"ability_bonus": {"STR": 4, "CON": 4}, "ability_cap": 24},
}


# SRD racial trait index -> mechanical effect. The bundled SRD JSON describes
# these traits in prose only (official 5etools races carry real fields
# instead, and use synthetic trait ids, so they never match here). Keys:
#   senses          {sense: range in feet}
#   resist          [damage types]
#   hp_per_level    flat HP added per character level (Dwarven Toughness)
#   innate_spells   catalog-innate-shaped entries; `level` is the character
#                   level the spell is gained at
#   spell_ability   spellcasting ability for the trait's own chosen spell
#                   (High Elf Cantrip's `trait_specific.spell_options` pick)
SRD_TRAIT_EFFECTS: dict[str, dict] = {
    "darkvision": {"senses": {"darkvision": 60}},
    "dwarven-resilience": {"resist": ["poison"]},
    "dwarven-toughness": {"hp_per_level": 1},
    "hellish-resistance": {"resist": ["fire"]},
    "infernal-legacy": {"innate_spells": [
        {"name": "Thaumaturgy", "spell_id": "thaumaturgy", "level": 1, "uses": "at-will", "ability": "CHA", "variant": None},
        {"name": "Hellish Rebuke", "spell_id": "hellish-rebuke", "level": 3, "uses": "1/day", "ability": "CHA", "variant": None},
        {"name": "Darkness", "spell_id": "darkness", "level": 5, "uses": "1/day", "ability": "CHA", "variant": None},
    ]},
    "high-elf-cantrip": {"spell_ability": "INT"},
}
