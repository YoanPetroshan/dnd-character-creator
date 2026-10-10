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

def subclass_unlock_level(class_id: str, ruleset: str = "mixed") -> int | None:
    """The class level at which the subclass can be picked. Under ruleset
    "2024" every class unlocks it at level 3 (all 12 XPHB class records place
    their Subclass feature at 3); "2014", "mixed" and unknown rulesets keep the
    per-class SUBCLASS_UNLOCK_LEVEL (mixed stays on the SRD chassis)."""
    base = SUBCLASS_UNLOCK_LEVEL.get(class_id)
    if base is not None and ruleset == "2024":
        return 3
    return base


# Spellcasting ability of subclasses whose CLASS has none (the class has no
# `spellcasting` block, so spells.spellcasting_ability() is None): the 1/3
# casters and the monk subclasses that grant always-prepared cantrips.
SUBCLASS_SPELLCASTING_ABILITY: dict[str, str] = {
    "arcane-trickster-phb": "INT", "arcane-trickster-xphb": "INT",
    "eldritch-knight-phb": "INT", "eldritch-knight-xphb": "INT",
    "shadow-phb": "WIS", "shadow-xphb": "WIS", "elements-xphb": "WIS",
}

# 2014 third-caster spell-school limits: spells known must come from `schools`
# except the spells learned at the levels in `free_at` (one of the first three
# at level 3, then those learned at 8, 14 and 20), so the number of any-school
# spells allowed at class level L is len([l for l in free_at if l <= L]).
# The 2024 reprints have no school restriction.
SUBCLASS_SPELL_SCHOOL_LIMITS: dict[str, dict] = {
    "eldritch-knight-phb": {"schools": ["abjuration", "evocation"], "free_at": [3, 8, 14, 20]},
    "arcane-trickster-phb": {"schools": ["enchantment", "illusion"], "free_at": [3, 8, 14, 20]},
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
    return PROFICIENCY_LABEL_OVERRIDES.get(prof_id) or prof_id.replace("-", " ").capitalize()


PROFICIENCY_LABEL_OVERRIDES = {
    "martial-weapons-finesse-or-light": "Martial weapons with Finesse or Light",
    "martial-weapons-light": "Martial weapons with Light",
}


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
#   attack_bonus / damage_bonus  Archery (+2 ranged attack) and Dueling (+2
#                       one-handed melee damage); read by engine/features.attack_styles.
#   two_weapon_fighting / great_weapon_fighting  flags, same reader
#                       (great_weapon_fighting_2024 = the XPHB wording; damage_bonus.thrown = Thrown
#                       Weapon Fighting, shown as a note on thrown weapons).
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
    "fighter-fighting-style-two-weapon-fighting": {"two_weapon_fighting": True},
    "ranger-fighting-style-two-weapon-fighting": {"two_weapon_fighting": True},
    "opt-dueling-phb": {"damage_bonus": {"one_handed_melee": 2}},
    "opt-two-weapon-fighting-phb": {"two_weapon_fighting": True},
    "fighter-fighting-style-great-weapon-fighting": {"great_weapon_fighting": True},
    "fighting-style-great-weapon-fighting": {"great_weapon_fighting": True},
    # C3: the 2024 (XPHB) Fighting Style feats, keyed by feat index. Defense, Archery,
    # Dueling, Two-Weapon Fighting reuse the 2014 shapes; Great Weapon Fighting is its
    # own flag (the 2024 text is "treat a 1 or 2 on a damage die as a 3", not a reroll);
    # Thrown Weapon Fighting is damage_bonus.thrown. Blind Fighting's blindsight comes
    # from the feat record's own `senses`. Interception, Protection (reactions),
    # Unarmed Fighting (no generic unarmed strike for non-Monks), Blessed / Druidic /
    # Arcane Warrior (cantrip picks cascade as ordinary feat spell choices) have no
    # numeric effect here.
    "archery-xphb": {"attack_bonus": {"ranged": 2}},
    "defense-xphb": {"ac_bonus_armored": 1},
    "dueling-xphb": {"damage_bonus": {"one_handed_melee": 2}},
    "great-weapon-fighting-xphb": {"great_weapon_fighting_2024": True},
    "two-weapon-fighting-xphb": {"two_weapon_fighting": True},
    "thrown-weapon-fighting-xphb": {"damage_bonus": {"thrown": 2}},
    "jack-of-all-trades": {"half_proficiency": "floor"},
    "remarkable-athlete": {"half_proficiency": "ceil"},
    "primal-champion": {"ability_bonus": {"STR": 4, "CON": 4}, "ability_cap": 24},
    # R5: always-on numbers folded into derived. Slippery Mind is NOT here: it
    # differs by ruleset (WIS in 2014, WIS + CHA in 2024), see engine/features.py.
    "aura-of-protection": {"save_bonus_ability": "CHA", "save_bonus_min": 1},
    "diamond-soul": {"save_proficiency": "all"},
    "fast-movement": {"speed_bonus_unless_heavy_armor": 10},
}

# The 13 PHB/XPHB damage types, alphabetical (Rage resistance lists).
DAMAGE_TYPES = ["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
                "poison", "psychic", "radiant", "slashing", "thunder"]
# Totem Warrior, Totem Spirit, Bear (PHB p.50): while raging, resistance to all damage except psychic.
TOTEM_BEAR_OPTION_ID = "totem-warrior-phb-3-totem-spirit--bear"


# Specific-weapon proficiency ids (class/race grants such as "rapiers") and the
# mapping from an Equipment.json weapon index to its proficiency id. The rule is
# index + "s"; the exceptions are listed. The set is every specific-weapon id the
# SRD classes, races and traits grant (verified by scanning their `proficiencies`).
SPECIFIC_WEAPON_PROFICIENCY_IDS = {
    "shortswords", "clubs", "crossbows-light", "daggers", "darts", "hand-crossbows",
    "javelins", "longswords", "maces", "quarterstaffs", "rapiers", "scimitars",
    "sickles", "slings", "spears",
    "battleaxes", "handaxes", "light-hammers", "warhammers", "shortbows", "longbows",
}
WEAPON_PROFICIENCY_ID_OVERRIDES = {
    "crossbow-light": "crossbows-light",
    "crossbow-hand": "hand-crossbows",
    "crossbow-heavy": "crossbows-heavy",
}


def weapon_proficiency_id(item_index: str) -> str:
    return WEAPON_PROFICIENCY_ID_OVERRIDES.get(item_index, item_index + "s")


# F1 (C2) / C9a: pseudo proficiency ids that `attacks.weapon_is_proficient` resolves by weapon
# category + properties. XPHB Rogue (class record): Simple + "Martial weapons that have the
# Finesse or Light property"; XPHB Monk: Simple + "Martial weapons that have the Light property".
# They come from the 2024 class chassis overlay (`catalog.classes_2024`, C9a); 2014 and mixed
# keep the SRD lists.
MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID = "martial-weapons-finesse-or-light"
MARTIAL_LIGHT_PROFICIENCY_ID = "martial-weapons-light"


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


# Fixed proficiency grants of a subclass (the SRD feature text is prose only).
# Only subclasses whose grant is a fixed list belong here; Lore Bard's three
# free skills are a choice and are not modelled.
SUBCLASS_PROFICIENCIES: dict[str, list[str]] = {
    "life": ["heavy-armor"],  # Life Domain: Bonus Proficiency
    # Slice 11b.5, read off the imported feature text (fixed lists only; skill
    # and tool CHOICES, Mastermind's/Mercy's skills and Bladesinging's weapon
    # pick are not modelled). Applied whenever the subclass is selected, even
    # below the level that grants it (a 2024 subclass picked at class level 1).
    "valor-phb": ["medium-armor", "shields", "martial-weapons"],
    "valor-xphb": ["medium-armor", "shields", "martial-weapons"],
    "swords-xge": ["medium-armor", "scimitars"],
    "death-dmg": ["martial-weapons"],
    "nature-phb": ["heavy-armor"],
    "tempest-phb": ["martial-weapons", "heavy-armor"],
    "war-phb": ["martial-weapons", "heavy-armor"],
    "solidarity-psa": ["heavy-armor"],
    "strength-psa": ["heavy-armor"],
    "zeal-psa": ["martial-weapons", "heavy-armor"],
    "order-tce": ["heavy-armor"],
    "twilight-tce": ["martial-weapons", "heavy-armor"],
    "forge-xge": ["heavy-armor", "smiths-tools"],
    "rune-knight-tce": ["smiths-tools"],
    "assassin-phb": ["disguise-kit", "poisoners-kit"],
    "assassin-xphb": ["disguise-kit", "poisoners-kit"],
    "hexblade-xge": ["medium-armor", "shields", "martial-weapons"],
    "bladesinging-tce": ["light-armor"],
}

# How a subclass's `spells` list (5e-SRD-Subclasses.json) behaves. Default is
# "always": the spells are always prepared / known and do not count against the
# class's prepared or known limits (Life domain, Devotion oath, Land circle).
# "expanded": the spells are only added to the class's pick list (Fiend
# Expanded Spell List).
SUBCLASS_SPELL_MODE: dict[str, str] = {
    "fiend": "expanded",
}

# Build-time option choices that live in feature TEXT (an `options` block of
# `refSubclassFeature` children in the 5etools class files), keyed by imported
# feature id -> number of picks. The converter turns the block into
# `feature_specific.text_options`. Per-rest choices (The Third Eye, Master
# Transmuter) and grant-all blocks (Psionic Power, Soul Blades) are
# deliberately absent. Storm Soul / Raging Storm follow the Storm Aura pick.
FEATURE_TEXT_CHOICES: dict[str, int] = {
    "totem-warrior-phb-3-totem-spirit": 1,
    "totem-warrior-phb-6-aspect-of-the-beast": 1,
    "totem-warrior-phb-14-totemic-attunement": 1,
    "storm-herald-xge-3-storm-aura": 1,
}

# Subclass features the SRD level tables never reference but that carry data
# the engine needs: (class level, feature index). Circle of the Land's terrain
# pick (`circle-of-the-land`, 7 terrain subfeatures) is not listed in any level
# row, so without this the terrain choice, and the circle spells that depend on
# it, would be unreachable.
SUBCLASS_EXTRA_FEATURES: dict[str, list[tuple[int, str]]] = {
    "land": [(2, "circle-of-the-land")],
}


# Slice 10: books printed under the 2024 rules. Races and backgrounds are
# tagged from 5etools' own `edition: "one"` marker (RHW species/backgrounds
# are 2024, RHW feats are not); feats carry no edition field, so they are
# tagged by source.
RULESET_2024_SOURCES = {"XPHB", "XDMG", "XMM", "FRHoF", "EFA", "ABH", "LFL"}


def ruleset_for_edition(raw: dict) -> str:
    return "2024" if raw.get("edition") == "one" else "2014"


# G1: feats that may be taken more than once although the imported 5etools record
# carries no `repeatable` flag. PHB 2014 Elemental Adept: "You can select this
# feat multiple times. Each time you do so, you must choose a different damage
# type." (the XPHB version has the flag in the data). The engine does not model
# the damage-type choice, so a second take is simply allowed and the "different
# type" rule is player-enforced. PHB Magic Initiate and Skilled are NOT here:
# their PHB text has no repeat sentence.
REPEATABLE_FEAT_OVERRIDES = {"elemental-adept-phb"}


def ruleset_for_feat(raw: dict) -> str:
    return "2024" if raw.get("source") in RULESET_2024_SOURCES else "2014"


def ruleset_allows(record: dict, kind: str, ruleset: str) -> bool:
    """Visibility of a species/subspecies/background/feat record under a
    draft ruleset (kind is "species", "background", "feat", "spell" or "subclass"). "2014" hides 2024 records of every kind; "2024" hides
    only 2014 backgrounds (2014 species and feats stay usable, since the
    2024 books reuse them); "mixed" (and anything unknown) hides nothing.
    Purely a picker filter - resolve() never rejects on ruleset alone."""
    tag = record.get("ruleset") or "2014"
    if ruleset == "2014":
        return tag != "2024"
    if ruleset == "2024":
        return not (kind == "background" and tag == "2014")
    return True


# Display names for the source picker (names verified against 5etools
# books.json; sources it does not list are filled from memory or fall back
# to the bare source code).
SOURCE_NAMES: dict[str, str] = {
    "AAG": "Astral Adventurer's Guide",
    "ABH": "Astarion's Book of Hungers",
    "AI": "Acquisitions Incorporated",
    "BGDIA": "Baldur's Gate: Descent into Avernus",
    "BGG": "Bigby Presents: Glory of the Giants",
    "BMT": "The Book of Many Things",
    "DMG": "Dungeon Master's Guide (2014)",
    "DSotDQ": "Dragonlance: Shadow of the Dragon Queen",
    "EEPC": "Elemental Evil Player's Companion",
    "EFA": "Eberron: Forge of the Artificer",
    "EGW": "Explorer's Guide to Wildemount",
    "ERLW": "Eberron: Rising from the Last War",
    "FRHoF": "Forgotten Realms: Heroes of Faerun",
    "FTD": "Fizban's Treasury of Dragons",
    "GGR": "Guildmasters' Guide to Ravnica",
    "GoS": "Ghosts of Saltmarsh",
    "LFL": "Lorwyn: First Light",
    "LR": "Locathah Rising",
    "MOT": "Mythic Odysseys of Theros",
    "MPMM": "Mordenkainen Presents: Monsters of the Multiverse",
    "MTF": "Mordenkainen's Tome of Foes",
    "OGA": "One Grung Above",
    "PHB": "Player's Handbook (2014)",
    "PSA": "Plane Shift: Amonkhet",
    "PSD": "Plane Shift: Dominaria",
    "PSI": "Plane Shift: Innistrad",
    "PSK": "Plane Shift: Kaladesh",
    "PSX": "Plane Shift: Ixalan",
    "PSZ": "Plane Shift: Zendikar",
    "SCAG": "Sword Coast Adventurer's Guide",
    "SCC": "Strixhaven: A Curriculum of Chaos",
    "SatO": "Sigil and the Outlands",
    "TCE": "Tasha's Cauldron of Everything",
    "TTP": "The Tortle Package",
    "ToA": "Tomb of Annihilation",
    "VGM": "Volo's Guide to Monsters",
    "VRGR": "Van Richten's Guide to Ravenloft",
    "WBtW": "The Wild Beyond the Witchlight",
    "XGE": "Xanathar's Guide to Everything",
    "XPHB": "Player's Handbook (2024)",
}


# --- Class resources (R3): prose-only numbers, verified against the texts below ---

# Paladin 2014 Channel Divinity (PHB p.85 / SRD feature `channel-divinity`, level 3): the
# SRD level rows have no column and the feature text is empty (the oath adds the effects);
# the PHB gives one use per short or long rest at every level.
PALADIN_2014_CHANNEL_DIVINITY = {"minLevel": 3, "uses": 1}

# Wild Shape 2014 (SRD feature `wild-shape-cr-1-4-or-below-no-flying-or-swim-speed`): "You can
# use this feature twice. You regain expended uses when you finish a short or long rest."
WILD_SHAPE_2014_USES = 2

# Wild Shape 2024, "Beast Shapes" table in the XPHB Wild Shape feature text (not a class table
# column): (druid level, known forms, max CR, fly speed allowed), ascending by level.
WILD_SHAPE_2024_BEAST_SHAPES: list[tuple[int, int, str, bool]] = [
    (2, 4, "1/4", False),
    (4, 6, "1/2", False),
    (8, 8, "1", True),
]

# Challenge ratings the SRD level rows store as numbers, as the text form used in the sheet.
CR_TEXT: dict[float, str] = {0: "0", 0.125: "1/8", 0.25: "1/4", 0.5: "1/2"}


# --- Class resources (R4): prose-only numbers ---

# Sorcerer 2024 "Creating Spell Slots" table (XPHB Font of Magic feature text, not a class
# table column): (slot level, sorcery point cost, minimum sorcerer level). The 2014 SRD costs
# come from the level rows (`creating_spell_slots`: 2/3/5/6/7) and have no minimum level.
SORCERER_2024_CREATING_SLOTS: list[tuple[int, int, int]] = [
    (1, 2, 2),
    (2, 3, 3),
    (3, 5, 5),
    (4, 6, 7),
    (5, 7, 9),
]

# Arcane Recovery (SRD `arcane-recovery`, XPHB Arcane Recovery): "combined level ... no more
# than half your Wizard level (round up), and none of the slots can be level 6 or higher".
ARCANE_RECOVERY_MAX_SLOT_LEVEL = 5

# Bard Font of Inspiration (SRD `font-of-inspiration`, XPHB): short rest recharge from level 5.
FONT_OF_INSPIRATION_LEVEL = 5


# ---- Subclass resources (R6) -------------------------------------------------
# All first features of these subclasses are at fighter/rogue level 3.
SUBCLASS_RESOURCE_MIN_LEVEL = 3

# Psi Warrior / Soulknife, TCE (2014) `*-tce-3-psionic-power`: "a number of these dice equal
# to twice your proficiency bonus"; the die is d6 and "increases: at 5th level (d8), 11th
# level (d10), and 17th level (d12)". (class level, die), ascending. The XPHB version is a
# class-level table (catalog.subclass_2024_tables), not this formula.
PSIONIC_DICE_PB_MULTIPLIER_2014 = 2
PSIONIC_DIE_BY_LEVEL_2014 = [(3, "d6"), (5, "d8"), (11, "d10"), (17, "d12")]

# Battle Master superiority dice (PHB `combat-superiority`, `improved-combat-superiority`;
# XPHB identical): four d8, "another superiority die at 7th level and one more at 15th";
# d10 at 10, d12 at 18 (XPHB "Improved"/"Ultimate Combat Superiority"). Ascending by level.
SUPERIORITY_DICE_COUNT = [(3, 4), (7, 5), (15, 6)]
SUPERIORITY_DIE_BY_LEVEL = [(3, "d8"), (10, "d10"), (18, "d12")]
# Maneuver save DC = 8 + proficiency bonus + STR or DEX modifier (PHB abilityDc str/dex,
# XPHB "your choice"): the better one is used.
MANEUVER_DC_BASE = 8

# Arcane Archer (XGE `arcane-shot`): "You have two uses of this ability, and you regain all
# expended uses of it when you finish a short or long rest."
ARCANE_SHOT_USES = 2


# ---- Eldritch Invocation effects (R8, SRD set) ------------------------------
# Keyed by SRD feature id. Every entry was checked against the SRD feature text
# and the SRD spell ids (tests/test_invocation_effects.py re-checks them).
# Keys: innate_spell {spell, uses "at-will" | "1/long rest", level} (CHA, source
# "Eldritch Invocation"); skills; ac_formula (same shape as CLASS_FEATURE_EFFECTS,
# decision D6); senses (devilsSight, not darkvision); resource_bonus (Agonizing
# Blast, CHA mod); note (text-only effects). "Once using a warlock spell slot ...
# until you finish a long rest" -> "1/long rest" at the spell's own level.
_INV = "eldritch-invocation-"


def _at_will(spell: str, level: int) -> dict:
    return {"innate_spell": {"spell": spell, "uses": "at-will", "level": level}}


def _once(spell: str, level: int) -> dict:
    return {"innate_spell": {"spell": spell, "uses": "1/long rest", "level": level}}


INVOCATION_EFFECTS: dict[str, dict] = {
    _INV + "armor-of-shadows": {
        **_at_will("mage-armor", 1),
        "ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True},
    },
    _INV + "ascendant-step": _at_will("levitate", 2),
    _INV + "beast-speech": _at_will("speak-with-animals", 1),
    _INV + "eldritch-sight": _at_will("detect-magic", 1),
    _INV + "fiendish-vigor": _at_will("false-life", 1),
    _INV + "mask-of-many-faces": _at_will("disguise-self", 1),
    _INV + "misty-visions": _at_will("silent-image", 1),
    _INV + "otherworldly-leap": _at_will("jump", 1),
    _INV + "master-of-myriad-forms": _at_will("alter-self", 2),
    _INV + "whispers-of-the-grave": _at_will("speak-with-dead", 3),
    _INV + "visions-of-distant-realms": _at_will("arcane-eye", 4),
    # At will, but "finish a long rest before you can use this invocation on the same creature again".
    _INV + "chains-of-carceri": {
        **_at_will("hold-monster", 5),
        "note": "Only against a celestial, fiend or elemental; once per creature per long rest.",
    },
    _INV + "thief-of-five-fates": _once("bane", 1),
    _INV + "mire-the-mind": _once("slow", 3),
    _INV + "sign-of-ill-omen": _once("bestow-curse", 3),
    _INV + "bewitching-whispers": _once("compulsion", 4),
    _INV + "dreadful-word": _once("confusion", 4),
    _INV + "sculptor-of-flesh": _once("polymorph", 4),
    _INV + "minions-of-chaos": _once("conjure-elemental", 5),
    _INV + "beguiling-influence": {"skills": ["skill-deception", "skill-persuasion"]},
    _INV + "devils-sight": {"senses": {"devilsSight": 120}},
    _INV + "agonizing-blast": {"resource_bonus": {"name": "Agonizing Blast", "ability": "CHA", "spell": "eldritch-blast"}},
    _INV + "thirsting-blade": {"note": "Attack with your pact weapon twice, instead of once, when you take the Attack action."},
    _INV + "repelling-blast": {"note": "When eldritch blast hits a creature, you can push it up to 10 feet away from you in a straight line."},
    _INV + "book-of-ancient-secrets": {"note": "Two 1st-level ritual spells in your Book of Shadows (the ritual book itself is not modelled)."},
}


# ---- 2024 level-1 class "order" choices (C6a) -------------------------------
# XPHB Cleric "Divine Order" and Druid "Primal Order" (ruleset "2024" only). The
# effects below were checked against the imported catalog.features text on 2026-10-10
# (xphb-cleric-1-protector / -thaumaturge, xphb-druid-1-warden / -magician):
#   Protector   "you gain proficiency with Martial weapons and training with Heavy armor."
#   Thaumaturge "You know one extra cantrip from the Cleric spell list. In addition ... a bonus
#                to your Intelligence (Arcana or Religion) checks. The bonus equals your Wisdom
#                modifier (minimum of +1)."
#   Warden      "... proficiency with Martial weapons and training with Medium armor."
#   Magician    "You know one extra cantrip from the Druid spell list. ... Intelligence (Arcana or
#                Nature) checks. The bonus equals your Wisdom modifier (minimum bonus of +1)."
# Option id = the catalog feature index (the text is read from there). Keys per option:
# proficiencies (ids of the shared proficiency sets), extra_cantrips (count bump on the class
# cantrip card), skill_bonus {skills, ability, minimum}: bonus = max(minimum, ability modifier)
# added to those skills' totals.
CLASS_ORDER_CHOICES: dict[str, dict] = {
    "cleric": {
        "slug": "divine-order", "feature": "xphb-cleric-1-divine-order", "label": "Divine Order",
        "options": {
            "xphb-cleric-1-protector": {"proficiencies": ["martial-weapons", "heavy-armor"]},
            "xphb-cleric-1-thaumaturge": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-religion"], "ability": "WIS", "minimum": 1},
            },
        },
    },
    "druid": {
        "slug": "primal-order", "feature": "xphb-druid-1-primal-order", "label": "Primal Order",
        "options": {
            "xphb-druid-1-magician": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-nature"], "ability": "WIS", "minimum": 1},
            },
            "xphb-druid-1-warden": {"proficiencies": ["martial-weapons", "medium-armor"]},
        },
    },
}


# ---- 2024 Expertise cards (C6b-1) -------------------------------------------
# Keyed by the XPHB feature id (imported into catalog.features by C1). Texts read from the
# imported catalog on 2026-10-10:
#   Bard 2 / 9, Rogue 1 / 6   "You gain Expertise in two of your skill proficiencies of your choice."
#   Ranger 9                  "Choose two of your skill proficiencies with which you lack Expertise."
#   Ranger 2 Deft Explorer    "Choose one of your skill proficiencies with which you lack Expertise."
#   Wizard 2 Scholar          "Choose one of the following skills in which you have proficiency:
#                              Arcana, History, Investigation, Medicine, Nature, or Religion."
# Keys: class, level, count, skills (None = every skill, else the allowed skill ids),
# lacks_expertise (True = options that already have Expertise are disabled; only the two
# "with which you lack Expertise" texts, decision E1: the other cards allow a wasted duplicate).
# No card offers tools (2024 Expertise is skills only).
EXPERTISE_2024: dict[str, dict] = {
    "xphb-bard-2-expertise": {"class": "bard", "level": 2, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-bard-9-expertise": {"class": "bard", "level": 9, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-rogue-1-expertise": {"class": "rogue", "level": 1, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-rogue-6-expertise": {"class": "rogue", "level": 6, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-ranger-2-deft-explorer": {"class": "ranger", "level": 2, "count": 1, "skills": None, "lacks_expertise": True},
    "xphb-ranger-9-expertise": {"class": "ranger", "level": 9, "count": 2, "skills": None, "lacks_expertise": True},
    "xphb-wizard-2-scholar": {
        "class": "wizard", "level": 2, "count": 1, "lacks_expertise": False,
        "skills": ["skill-arcana", "skill-history", "skill-investigation", "skill-medicine", "skill-nature", "skill-religion"],
    },
}

# SRD (2014) class cards that the 2024 cards replace; skipped under ruleset "2024" only when the
# replacing XPHB feature exists in the catalog. The Ranger's Favored Enemy / Natural Explorer
# cards have no 2024 counterpart card at all (2024 Favored Enemy is a resource, Deft Explorer
# replaces Natural Explorer), so they go whenever the XPHB Ranger is imported.
SRD_CARDS_REPLACED_2024: dict[str, tuple[str, ...]] = {
    "bard": ("bard-expertise-1", "bard-expertise-2"),
    "rogue": ("rogue-expertise-1", "rogue-expertise-2"),
    "ranger": ("favored-enemy-1-type", "favored-enemy-2-types", "favored-enemy-3-enemies",
               "natural-explorer-1-terrain-type", "natural-explorer-2-terrain-types",
               "natural-explorer-3-terrain-types"),
}


# ---- 2024 class languages and Primal Knowledge (C6b-2) ----------------------------------------
# PHB 2024 chapter 2 language tables (Standard and Rare). Deliberately NOT merged into LANGUAGES:
# that list drives every mixed / 2014 language choice and must not change.
LANGUAGES_2024_STANDARD: list[dict[str, str]] = [
    {"index": "common", "name": "Common"},
    {"index": "common-sign-language", "name": "Common Sign Language"},
    {"index": "draconic", "name": "Draconic"},
    {"index": "dwarvish", "name": "Dwarvish"},
    {"index": "elvish", "name": "Elvish"},
    {"index": "giant", "name": "Giant"},
    {"index": "gnomish", "name": "Gnomish"},
    {"index": "goblin", "name": "Goblin"},
    {"index": "halfling", "name": "Halfling"},
    {"index": "orc", "name": "Orc"},
]
LANGUAGES_2024_RARE: list[dict[str, str]] = [
    {"index": "abyssal", "name": "Abyssal"},
    {"index": "celestial", "name": "Celestial"},
    {"index": "deep-speech", "name": "Deep Speech"},
    {"index": "druidic", "name": "Druidic"},
    {"index": "infernal", "name": "Infernal"},
    {"index": "primordial", "name": "Primordial"},
    {"index": "sylvan", "name": "Sylvan"},
    {"index": "thieves-cant", "name": "Thieves' Cant"},
    {"index": "undercommon", "name": "Undercommon"},
]
# id -> display name of every language any ruleset can produce (exports read this).
LANGUAGE_NAMES: dict[str, str] = {
    lang["index"]: lang["name"] for lang in LANGUAGES + LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE
}

# XPHB class features that grant languages (texts read from catalog.features on 2026-10-10):
#   Rogue 1 Thieves' Cant   "You know Thieves' Cant and one other language of your choice, which you choose
#                            from the language tables in chapter 2."
#   Druid 1 Druidic         "You know Druidic, the secret language of Druids."
#   Ranger 2 Deft Explorer  "Languages. You know two languages of your choice from the language tables in chapter 2."
# Keys: class, level, fixed (language ids always known), choose (picks from the 19-entry pool, decision E2).
CLASS_LANGUAGES_2024: dict[str, dict] = {
    "xphb-rogue-1-thieves-cant": {"class": "rogue", "level": 1, "fixed": ["thieves-cant"], "choose": 1},
    "xphb-druid-1-druidic": {"class": "druid", "level": 1, "fixed": ["druidic"], "choose": 0},
    "xphb-ranger-2-deft-explorer": {"class": "ranger", "level": 2, "fixed": [], "choose": 2},
}

# XPHB Barbarian 3 Primal Knowledge: "You gain proficiency in another skill of your choice from the
# skill list available to Barbarians at level 1." (options = classes_2024["barbarian"] level 1 skill list)
PRIMAL_KNOWLEDGE_2024: dict[str, object] = {
    "feature": "xphb-barbarian-3-primal-knowledge", "class": "barbarian", "level": 3,
}
