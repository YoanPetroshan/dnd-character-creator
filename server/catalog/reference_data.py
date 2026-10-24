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
    {"index": "dragonchess-set", "name": "Dragonchess Set", "category": "Gaming Sets"},   # RPX4: PHB, not in the SRD
    {"index": "playing-card-set", "name": "Playing Card Set", "category": "Gaming Sets"},
    {"index": "three-dragon-ante-set", "name": "Three-Dragon Ante Set", "category": "Gaming Sets"},  # RPX4
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

# RPX4 (Extra 4): the two PHB gaming sets the SRD equipment list lacks (the SRD has Dice Set and Playing Card Set).
# Source: Player's Handbook (2014) ch. 5, "Tools" table, Gaming set rows: Dragonchess set 1 gp, 1/2 lb.; Three-Dragon
# Ante set 1 gp, no weight. The PHB 2024 table has the same four sets. The local 5etools data has no gaming-set item
# record, so the catalog gets these through `loader._merge_official_items` (ids = the TOOLS indexes above). Tuples:
# (index, name, cost gp, weight lb).
PHB_GAMING_SETS: list[tuple[str, str, int, float]] = [
    ("dragonchess-set", "Dragonchess Set", 1, 0.5),
    ("three-dragon-ante-set", "Three-Dragon Ante Set", 1, 0),
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

# RP2 (B2): fixed numeric effects of XPHB class and subclass features, ruleset "2024" only. Keyed by the
# imported XPHB feature record id; `engine/features.xphb_effects_2024` applies an entry when the character's level in
# the record's class has reached the record's own `level` (and, for a subclass feature, the record's subclass is the
# selected one). An entry whose record is not in the catalog (SRD-only) gives nothing. `quotes` are verbatim
# sentences of the record's text (pinned by tests/test_xphb_feature_effects_2024.py); the other keys are the
# CLASS_FEATURE_EFFECTS keys plus:
#   supersedes          SRD feature id whose CLASS_FEATURE_EFFECTS entry this one replaces (not stacks with) once
#                       the XPHB record is found (Primal Champion: the SRD effect caps at 24).
#   senses_additive     {sense: ft}: "If you already have Darkvision, its range increases by 60 feet" - added to
#                       the final range of that sense, else the sense itself.
#   sense_range         {sense: ft}: at least this range (Blindsight 30).
#   climb_equals_walk / swim_equals_walk   "a Climb / Swim Speed equal to your Speed".
#   speed_bonus_flat    ft added to the walking speed with no condition.
#   speed_bonus_unless_heavy_armor   same key as Fast Movement.
#   resist              [damage types]
#   skills / proficiencies   skill ids / tool ids granted.
# Conditional wording (while raging, in the aura, while an Emanation or form is active) is not an effect: see
# CLASS_FEATURE_NOTES_ONLY_2024.
CLASS_FEATURE_EFFECTS_2024: dict[str, dict] = {
    "xphb-monk-20-body-and-mind": {
        "quotes": ("Your Dexterity and Wisdom scores increase by 4, to a maximum of 25.",),
        "ability_bonus": {"DEX": 4, "WIS": 4}, "ability_cap": 25},
    "xphb-barbarian-20-primal-champion": {
        "quotes": ("Your Strength and Constitution scores increase by 4, to a maximum of 25.",),
        "ability_bonus": {"STR": 4, "CON": 4}, "ability_cap": 25, "supersedes": "primal-champion"},
    # "3, and ... 1 whenever you gain another Sorcerer level" = the Sorcerer level (the feature is level 3). The
    # text says "armor", not "armor or a Shield" (compare the Monk's), so a shield is allowed.
    "draconic-xphb-3-draconic-resilience": {
        "quotes": ("Your Hit Point maximum increases by 3, and it increases by 1 whenever you gain another Sorcerer level.",
                   "While you aren't wearing armor, your base Armor Class equals 10 plus your Dexterity and Charisma modifiers."),
        "hp_per_class_level": 1, "ac_formula": {"base": 10, "abilities": ["DEX", "CHA"], "allows_shield": True}},
    # The record is a child of Dazzling Footwork, whose parent sentence is the condition: "While you aren't wearing
    # armor or wielding a Shield, you gain the following benefits." A shield therefore removes the formula.
    "dance-xphb-3-unarmored-defense": {
        "quotes": ("Your base Armor Class equals 10 plus your Dexterity and Charisma modifiers.",),
        "parent_quotes": {"dance-xphb-3-dazzling-footwork":
                          "While you aren't wearing armor or wielding a Shield, you gain the following benefits."},
        "ac_formula": {"base": 10, "abilities": ["DEX", "CHA"], "allows_shield": False}},
    "shadow-xphb-3-darkvision": {
        "quotes": ("You gain Darkvision with a range of 60 feet. If you already have Darkvision, its range increases by 60 feet.",),
        "senses_additive": {"darkvision": 60}},
    "gloom-stalker-xphb-3-umbral-sight": {
        "quotes": ("You gain Darkvision with a range of 60 feet. If you already have Darkvision when you gain this feature, "
                   "its range increases by 60 feet.",),
        "senses_additive": {"darkvision": 60}},
    "thief-xphb-3-second-story-work": {
        "quotes": ("You gain a Climb Speed equal to your Speed.",), "climb_equals_walk": True},
    "sea-xphb-6-aquatic-affinity": {
        "quotes": ("In addition, you gain a Swim Speed equal to your Speed.",), "swim_equals_walk": True},
    "war-xphb-17-avatar-of-battle": {
        "quotes": ("You gain Resistance to Bludgeoning, Piercing, and Slashing damage.",),
        "resist": ["bludgeoning", "piercing", "slashing"]},
    "psi-warrior-xphb-10-guarded-mind": {
        "quotes": ("You have Resistance to Psychic damage.",), "resist": ["psychic"]},
    "aberrant-xphb-6-psychic-defenses": {
        "quotes": ("You have Resistance to Psychic damage,",), "resist": ["psychic"]},
    "great-old-one-xphb-10-thought-shield": {
        "quotes": ("You also have Resistance to Psychic damage,",), "resist": ["psychic"]},
    "celestial-xphb-6-radiant-soul": {
        "quotes": ("You have Resistance to Radiant damage.",), "resist": ["radiant"]},
    # The ally clause of the same record ("the ally's Speed increases by 10 feet until the end of their next turn")
    # stays text only.
    "glory-xphb-7-aura-of-alacrity": {
        "quotes": ("Your Speed increases by 10 feet.",), "speed_bonus_flat": 10},
    "mercy-xphb-3-implements-of-mercy": {
        "quotes": ("You gain proficiency in the Insight and Medicine skills and proficiency with the Herbalism Kit.",),
        "skills": ["skill-insight", "skill-medicine"], "proficiencies": ["herbalism-kit"]},
    # Not on the plan's list, same kind (unconditional, fixed numbers, XPHB class feature).
    # RPF: unconditional condition immunities ("You are immune to ..."). The conditional ones stay text: Aura of
    # Courage / Aura of Devotion (in your Aura), Mindless Rage (while Rage is active). Nature's Ward's damage
    # Resistance depends on the land choice and stays in NOTES_ONLY wording below; only the Poisoned sentence is here.
    "archfey-xphb-10-beguiling-defenses": {
        "quotes": ("You are immune to the Charmed condition.",), "condition_immune": ["charmed"]},
    "land-xphb-10-natures-ward": {
        "quotes": ("You are immune to the Poisoned condition,",), "condition_immune": ["poisoned"]},
    # RPF: "When you roll Initiative, you can add your Wisdom modifier to the roll." (no use limit)
    "gloom-stalker-xphb-3-dread-ambusher": {
        "quotes": ("Initiative Bonus. When you roll Initiative, you can add your Wisdom modifier to the roll.",),
        "initiative_ability": "WIS"},
    "xphb-ranger-6-roving": {
        "quotes": ("Your Speed increases by 10 feet while you aren't wearing Heavy armor. You also have a Climb Speed "
                   "and a Swim Speed equal to your Speed.",),
        "speed_bonus_unless_heavy_armor": 10, "climb_equals_walk": True, "swim_equals_walk": True},
    "xphb-ranger-18-feral-senses": {
        "quotes": ("grants you Blindsight with a range of 30 feet.",), "sense_range": {"blindsight": 30}},
}

# XPHB features with fixed-looking numbers that are NOT effects because the text makes them conditional or a
# per-rest / per-activation choice (record id -> the verbatim conditional wording, pinned by tests). They stay in
# the feature text on the sheet.
CLASS_FEATURE_NOTES_ONLY_2024: dict[str, str] = {
    "elements-xphb-11-stride-of-the-elements": "While your Elemental Attunement is active",
    "elements-xphb-17-elemental-epitome": "While your Elemental Attunement is active",
    "wild-heart-xphb-14-power-of-the-wilds": "While your Rage is active, you have a Fly Speed equal to your Speed",
    "sea-xphb-10-stormborn": "Your Wrath of the Sea confers two more benefits while active",
    "stars-xphb-14-full-of-stars": "While in your Starry Form",
    "stars-xphb-3-starry-form": "Whenever you assume your starry form, choose which of the following constellations",
    "zealot-xphb-14-rage-of-the-gods": "While in this form, you gain the benefits below.",
    "ancients-xphb-7-aura-of-warding": "while in your Aura of Protection",
    "fiend-xphb-10-fiendish-resilience": "whenever you finish a Short or Long Rest",
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
# FE5: weapon-group proficiency ids a feat grants (Gunner: "firearms"); attacks.weapon_is_proficient maps it to the DMG firearms.
FEAT_WEAPON_PROFICIENCY_IDS = {"firearms"}
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

# C9b: XPHB class starting-equipment names that are not a plain catalog item name (the catalog is
# the SRD item list). Keys are the lower-cased 5etools item name; values are (catalog item id,
# count per unit; F3a-6: the catalog `arrow` item is already a 20-pack, quantity 20, weight 1, so "Arrows (20)" is ONE
# unit of it). Source: the `entries` line of each XPHB class record, e.g. Druid "Druidic Focus
# (Quarterstaff)", Fighter "Arrows (20)|XPHB|20 Arrows", Wizard "Robe". "holy symbol" and the musical
# instrument are nested picks, the Monk's tool is the sentinel below.
CLASS_2024_EQUIPMENT_ITEM_MAP = {
    "arrows (20)": ("arrow", 1),
    "robe": ("robes", 1),
    "druidic focus": ("quarterstaff", 1),
}
# RP8 (D): 2024 equipment packs. Source: Player's Handbook (2024) ch. 6, the "Equipment Packs" table (weight in
# lb.) and the per-pack item lists. Stored as numbers and catalog item ids only. The pack stays ONE inventory item
# (the catalog pack records are the SRD 2014 ones: weight None, other contents); under ruleset 2024 resolve() adds
# `contents` to its entries and carried weight uses the table weight. Differences from the SRD items are documented
# in ARCHITECTURE (e.g. the SRD rope weighs 10 lb, the 2024 pack total counts 5 lb of it; Priest's costs 33 GP
# here and 19 GP in the SRD record, cost is not shown).
# RPF: PHB 2024 ch. 6 weights that differ from the SRD catalog records, for items the 2024 packages, backgrounds and
# packs use or sell (all other gear, weapon, armor and tool weights were compared and are equal). lb.
ITEM_WEIGHTS_2024 = {"rope-hempen-50-feet": 5, "warhammer": 5}

PACKS_2024 = {
    "burglars-pack": {"weight": 42, "contents": [
        ("backpack", 1), ("ball-bearings-bag-of-1000", 1), ("bell", 1), ("candle", 10), ("crowbar", 1),
        ("lantern-hooded", 1), ("oil-flask", 7), ("rations-1-day", 5), ("rope-hempen-50-feet", 1),
        ("tinderbox", 1), ("waterskin", 1)]},
    "diplomats-pack": {"weight": 39, "contents": [
        ("chest", 1), ("clothes-fine", 1), ("ink-1-ounce-bottle", 1), ("ink-pen", 5), ("lamp", 1),
        ("case-map-or-scroll", 2), ("oil-flask", 4), ("paper-one-sheet", 5), ("parchment-one-sheet", 5),
        ("perfume-vial", 1), ("tinderbox", 1)]},
    "dungeoneers-pack": {"weight": 55, "contents": [
        ("backpack", 1), ("caltrops", 1), ("crowbar", 1), ("oil-flask", 2), ("rations-1-day", 10),
        ("rope-hempen-50-feet", 1), ("tinderbox", 1), ("torch", 10), ("waterskin", 1)]},
    "entertainers-pack": {"weight": 58.5, "contents": [
        ("backpack", 1), ("bedroll", 1), ("bell", 1), ("lantern-bullseye", 1), ("clothes-costume", 3),
        ("mirror-steel", 1), ("oil-flask", 8), ("rations-1-day", 9), ("tinderbox", 1), ("waterskin", 1)]},
    "explorers-pack": {"weight": 55, "contents": [
        ("backpack", 1), ("bedroll", 1), ("oil-flask", 2), ("rations-1-day", 10), ("rope-hempen-50-feet", 1),
        ("tinderbox", 1), ("torch", 10), ("waterskin", 1)]},
    "priests-pack": {"weight": 29, "contents": [
        ("backpack", 1), ("blanket", 1), ("holy-water-flask", 1), ("lamp", 1), ("rations-1-day", 7),
        ("robes", 1), ("tinderbox", 1)]},
    "scholars-pack": {"weight": 22, "contents": [
        ("backpack", 1), ("book", 1), ("ink-1-ounce-bottle", 1), ("ink-pen", 1), ("lamp", 1),
        ("oil-flask", 10), ("parchment-one-sheet", 10), ("tinderbox", 1)]},
}

# RP9 (C, E12): 2024 background starting equipment. Keys are the lower-cased 5etools item names that are not a plain
# catalog item name; values are (catalog item id, count per unit, label). Source: the `Equipment:` line of each
# ruleset-2024 background record ("Robe", "20 Arrows", "20 Bolts", "Iron Spikes"). `arrow` and `crossbow-bolt` are
# already 20-packs (F3a-6) and `spike-iron` weighs 5 lb (the 10-pack), so "20 Arrows" is ONE unit of each.
BACKGROUND_2024_EQUIPMENT_ITEM_MAP = {
    "robe": ("robes", 1, "Robes"),
    "arrows (20)": ("arrow", 1, "Arrows (20)"),
    "bolts (20)": ("crossbow-bolt", 1, "Bolts (20)"),
    "iron spikes": ("spike-iron", 1, "Iron Spikes"),
}
# Names with NO catalog item at all (a catalog gap, not a placeholder): a narrative item. The plain 5etools "map"
# would match the catalog "Case, map or scroll" by word subset, which is a different item.
BACKGROUND_2024_NARRATIVE_ITEMS = {"map": "Map"}
# The option member that stands for "the tool of this background's own tool proficiency pick" ("Gaming Set (same
# as above)"); resolve() replaces it by that item, or shows its label as a narrative item while it is unpicked.
BACKGROUND_TOOL_SENTINEL = "background-tool"

# Monk A: "Artisan's Tools or Musical Instrument chosen for the tool proficiency above". The option
# member id is this sentinel; resolve() replaces it by the item of the Monk's tool proficiency pick.
MONK_TOOL_SENTINEL = "monk-tool"


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
    # W1 (F1): the official (5etools) dwarves carry the same sentence under synthetic trait ids; each entry is pinned
    # by TRAIT_EFFECT_QUOTES against the catalog text (tests/test_w1_dwarven_toughness_heavy_armor.py also scans the
    # whole trait catalog for the sentence, so a new book cannot add an unmapped one).
    "dwarf-xphb-trait-2": {"hp_per_level": 1},
    "dwarf-phb-hill-phb-trait-0": {"hp_per_level": 1},
    "dwarf-(kaladesh)-psk-trait-6": {"hp_per_level": 1},
    "human-(innistrad)-psi-stensia-psi-trait-1": {"hp_per_level": 2},  # Stensia "Tough": 2, and 2 per level
    "hellish-resistance": {"resist": ["fire"]},
    "infernal-legacy": {"innate_spells": [
        {"name": "Thaumaturgy", "spell_id": "thaumaturgy", "level": 1, "uses": "at-will", "ability": "CHA", "variant": None},
        {"name": "Hellish Rebuke", "spell_id": "hellish-rebuke", "level": 3, "uses": "1/day", "ability": "CHA", "variant": None},
        {"name": "Darkness", "spell_id": "darkness", "level": 5, "uses": "1/day", "ability": "CHA", "variant": None},
    ]},
    "high-elf-cantrip": {"spell_ability": "INT"},
}

# W1 quote pins for the hp_per_level entries above (catalog text, tags stripped).
TRAIT_EFFECT_QUOTES: dict[str, str] = {
    "dwarven-toughness": "maximum increases by 1, and it increases by 1 every time you gain a level.",
    "dwarf-xphb-trait-2": "maximum increases by 1, and it increases by 1 again whenever you gain a level.",
    "dwarf-phb-hill-phb-trait-0": "maximum increases by 1, and it increases by 1 every time you gain a level.",
    "dwarf-(kaladesh)-psk-trait-6": "maximum increases by 1, and it increases by 1 every time you gain a level.",
    "human-(innistrad)-psi-stensia-psi-trait-1": "maximum increases by 2, and it increases by 2 every time you gain a level.",
}

# W5a (F2): species traits (ruleset "2024" species records only) with a use count, a rest rule or numbers, keyed by
# catalog trait id. `engine/species_resources.py` builds `derived.speciesResources` from it. Fields: `race` (species
# id), `name`, `uses` (int, "pb" or None = note only), `recharge`, `level` (character level the trait is gained at,
# default 1), `dc` (ability whose modifier joins 8 + PB), `dice_by_level` ((level, dice), ...), `die`, `heal` (template),
# `save`, `shape`, `damage_type` ("ancestry" = the picked Draconic Ancestry), `note` (template over pb, two_pb, level,
# dice, dc, damage_type, speed, con_mod) and `quotes`: verbatim substrings of the catalog trait text (tags stripped;
# tests/test_w5a_species_resources.py pins every one). Breath Weapon-like traits are resources, not attack rows (D-2).
SPECIES_RESOURCES: dict[str, dict] = {
    "dragonborn-xphb-trait-1": {
        "race": "dragonborn-xphb", "name": "Breath Weapon", "uses": "pb", "recharge": "long", "dc": "CON", "save": "DEX",
        "shape": "15-foot Cone or 30-foot Line (5 feet wide)", "damage_type": "ancestry",
        "dice_by_level": ((1, "1d10"), (5, "2d10"), (11, "3d10"), (17, "4d10")),
        "note": "Replaces one of your attacks in the Attack action: {shape}, Dexterity save, {dice} {damage_type} "
                "damage on a failed save and half as much on a success",
        "quotes": ("you can replace one of your attacks with an exhalation of magical energy in either a 15-foot Cone "
                   "or a 30-foot Line that is 5 feet wide",
                   "Dexterity saving throw (8 plus your Constitution modifier and Proficiency Bonus)",
                   "takes 1d10 damage of the type determined by your Draconic Ancestry trait",
                   "levels 5 (2d10), 11 (3d10), and 17 (4d10)",
                   "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you "
                   "finish a Long Rest")},
    "dragonborn-xphb-trait-4": {
        "race": "dragonborn-xphb", "name": "Draconic Flight", "uses": 1, "recharge": "long", "level": 5,
        "note": "Bonus Action, 10 minutes: spectral wings give a Fly Speed equal to your Speed{speed_part}",
        "quotes": ("When you reach character level 5", "you have a Fly Speed equal to your Speed",
                   "wings on your back that last for 10 minutes",
                   "you can't use it again until you finish a Long Rest")},
    "dwarf-xphb-trait-3": {
        "race": "dwarf-xphb", "name": "Stonecunning", "uses": "pb", "recharge": "long",
        "note": "Bonus Action, 10 minutes: Tremorsense with a range of 60 feet while on or touching a stone surface",
        "quotes": ("you gain Tremorsense with a range of 60 feet for 10 minutes",
                   "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you "
                   "finish a Long Rest")},
    "goliath-xphb-trait-0": {
        "race": "goliath-xphb", "name": "Giant Ancestry", "uses": "pb", "recharge": "long", "giant_ancestry": True,
        "note": "{ancestry}",
        "quotes": ("you can use the chosen benefit a number of times equal to your Proficiency Bonus, and you regain "
                   "all expended uses when you finish a Long Rest",)},
    "goliath-xphb-trait-1": {
        "race": "goliath-xphb", "name": "Large Form", "uses": 1, "recharge": "long", "level": 5,
        "note": "Bonus Action, 10 minutes: your size becomes Large, Advantage on Strength checks, Speed +10 feet",
        "quotes": ("Starting at character level 5", "change your size to Large as a Bonus Action",
                   "lasts for 10 minutes", "Advantage on Strength checks, and your Speed increases by 10 feet",
                   "you can't use it again until you finish a Long Rest")},
    "orc-xphb-trait-0": {
        "race": "orc-xphb", "name": "Adrenaline Rush", "uses": "pb", "recharge": "short-or-long",
        "note": "Take the Dash action as a Bonus Action and gain {pb} Temporary Hit Points",
        "quotes": ("You can take the Dash action as a Bonus Action",
                   "you gain a number of Temporary Hit Points equal to your Proficiency Bonus",
                   "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you "
                   "finish a Short or Long Rest")},
    "orc-xphb-trait-2": {
        "race": "orc-xphb", "name": "Relentless Endurance", "uses": 1, "recharge": "long",
        "note": "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        "quotes": ("you can drop to 1 Hit Point instead",
                   "you can't do so again until you finish a Long Rest")},
    "aasimar-xphb-trait-2": {
        "race": "aasimar-xphb", "name": "Healing Hands", "uses": 1, "recharge": "long", "heal": "{pb}d4",
        "note": "Magic action, touch: the creature regains Hit Points equal to the total of {pb}d4",
        "quotes": ("roll a number of d4s equal to your Proficiency Bonus",
                   "regains a number of Hit Points equal to the total rolled",
                   "you can't use it again until you finish a Long Rest")},
    "aasimar-xphb-trait-4": {
        "race": "aasimar-xphb", "name": "Celestial Revelation", "uses": 1, "recharge": "long", "level": 3,
        "note": "Bonus Action, 1 minute: once on each of your turns, extra damage equal to {pb} (Necrotic for "
                "Necrotic Shroud, Radiant for Heavenly Wings and Inner Radiance)",
        "quotes": ("When you reach character level 3", "The transformation lasts for 1 minute",
                   "The extra damage equals your Proficiency Bonus",
                   "Necrotic for Necrotic Shroud or Radiant for Heavenly Wings and Inner Radiance",
                   "you can't do so again until you finish a Long Rest")},
    "halfling-xphb-trait-2": {
        "race": "halfling-xphb", "name": "Luck", "uses": None, "recharge": None,
        "note": "When you roll a 1 on the d20 of a D20 Test, reroll the die and use the new roll",
        "quotes": ("When you roll a 1 on the d20 of a D20 Test, you can reroll the die, and you must use the new roll",)},
    "human-xphb-trait-0": {
        "race": "human-xphb", "name": "Resourceful", "uses": None, "recharge": "long",
        "note": "You gain Heroic Inspiration whenever you finish a Long Rest",
        "quotes": ("You gain Heroic Inspiration whenever you finish a Long Rest",)},
    "lupin-rhw-trait-2": {
        "race": "lupin-rhw", "name": "Howl", "uses": "pb", "recharge": "long", "dc": "CON", "save": "WIS",
        "note": "Bonus Action: creatures of your choice within 15 feet make a Wisdom save or have Disadvantage on "
                "attack rolls and saving throws until the start of your next turn",
        "quotes": ("Each creature of your choice within 15 feet of you must succeed on a Wisdom saving throw "
                   "(DC 8 plus your Constitution modifier and Proficiency Bonus)",
                   "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you "
                   "finish a Long Rest")},
    "reborn-rhw-trait-2": {
        "race": "reborn-rhw", "name": "Knowledge from a Past Life", "uses": "pb", "recharge": "long", "die": "1d6",
        "note": "When you fail an ability check, add 1d6 to the d20",
        "quotes": ("you can roll 1d6 and add the number rolled to the d20",
                   "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you "
                   "finish a Long Rest")},
    "shifter-efa-trait-2": {
        "race": "shifter-efa", "name": "Shifting", "uses": "pb", "recharge": "long",
        "note": "Bonus Action, 1 minute: gain {two_pb} Temporary Hit Points (2 times your Proficiency Bonus) and one "
                "shifting option",
        "quotes": ("This transformation lasts for 1 minute",
                   "Temporary Hit Points equal to 2 times your Proficiency Bonus",
                   "You can shift a number of times equal to your Proficiency Bonus, and you regain all expended "
                   "uses when you finish a Long Rest")},
    "khoravar-efa-trait-3": {
        "race": "khoravar-efa", "name": "Lethargy Resilience", "uses": 1, "recharge": None,
        "note": "When you fail a save to avoid or end Unconscious you can succeed instead; after using it, you can't "
                "do so again until you finish 1d4 Long Rests",
        "quotes": ("you can succeed instead",
                   "you can't do so again until you finish 1d4 Long Rests")},
}

# W5b (F2): the same table shape for the non-2024 (ruleset "2014") species records: the SRD species and the book
# species (PHB, MPMM, VGM, ...). Commit 1 holds the SRD ones. Extra fields: `srd_ancestry` (the damage type, save and
# area come from the picked Draconic Ancestry subtrait's `trait_specific.breath_weapon`; the dice progression and the DC
# are the pinned text). `damage_type: "ancestry"` reads the variant's `resist` or, for the PHB Dragonborn, the species
# resistance pick. Quotes are verbatim substrings of the catalog trait text (tests/test_w5b_species_resources.py).
SPECIES_RESOURCES_2014: dict[str, dict] = {
    "breath-weapon": {
        "race": "dragonborn", "name": "Breath Weapon", "uses": 1, "recharge": "short-or-long", "dc": "CON",
        "srd_ancestry": True, "damage_type": "ancestry",
        "dice_by_level": ((1, "2d6"), (6, "3d6"), (11, "4d6"), (16, "5d6")),
        "note": "Action: exhale in {shape}, {save} saving throw, {dice} {damage_type} damage on a failed save and half "
                "as much on a success",
        "quotes": ("You can use your action to exhale destructive energy",
                   "The DC for this saving throw equals 8 + your Constitution modifier + your proficiency bonus",
                   "A creature takes 2d6 damage on a failed save, and half as much damage on a successful one",
                   "The damage increases to 3d6 at 6th level, 4d6 at 11th level, and 5d6 at 16th level",
                   "you cannot use it again until you complete a short or long rest")},
    "relentless-endurance": {
        "race": "half-orc", "name": "Relentless Endurance", "uses": 1, "recharge": "long",
        "note": "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        "quotes": ("you can drop to 1 hit point instead",
                   "you cannot use this feature again until you finish a long rest")},
    "lucky": {
        "race": "halfling", "name": "Lucky", "uses": None, "recharge": None,
        "note": "When you roll a 1 on the d20 of an attack roll, ability check or saving throw, reroll the die and use the new roll",
        "quotes": ("When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the "
                   "die and must use the new roll",)},
}

# W5b commit 2: the book species (PHB, MPMM, VGM, FTD, AAG, ...). Only a use count / rest rule that the trait text states
# is modelled (PB uses, fixed uses, short / long rests, dice); `_e` is shorthand for the same spec shape. The scan of
# every other non-SRD, non-2024 species trait is listed in ARCHITECTURE-CURRENT-STATE.md (W5b) and pinned in
# tests/test_w5b_species_resources.py (SKIPPED_BOOK_TRAITS).
_PB_LONG = "a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"


_LUCKY_NOTE = "When you roll a 1 on the d20 of an attack roll, ability check or saving throw, reroll the die and use the new roll"


def _e(race, name, uses, recharge, note, quotes, **kw):
    return {"race": race, "name": name, "uses": uses, "recharge": recharge, "note": note, "quotes": tuple(quotes), **kw}


SPECIES_RESOURCES_2014.update({
    # --- Aasimar
    "aasimar-mpmm-trait-3": _e("aasimar-mpmm", "Healing Hands", 1, "long",
        "Action, touch: the creature regains Hit Points equal to the total of {pb}d4",
        ("roll a number of d4s equal to your proficiency bonus", "regains a number of hit points equal to the total rolled",
         "you can't use it again until you finish a long rest"), heal="{pb}d4"),
    "aasimar-mpmm-trait-5": _e("aasimar-mpmm", "Celestial Revelation", 1, "long",
        "Bonus Action, 1 minute: unleash the revelation you chose at 3rd level",
        ("When you reach 3rd level, choose one of the revelation options below", "Your transformation lasts for 1 minute",
         "you can't use it again until you finish a long rest"), level=3),
    "aasimar-vgm-trait-4": _e("aasimar-vgm", "Healing Hands", 1, "long",
        "Action, touch: the creature regains Hit Points equal to your level ({level})",
        ("cause it to regain a number of hit points equal to your level",
         "you can't use it again until you finish a long rest"), heal="{level}"),
    "aasimar-vgm-fallen-vgm-trait-0": _e("aasimar-vgm", "Necrotic Shroud", 1, "long",
        "Action, 1 minute: creatures within 10 feet that see you make a Charisma save or are frightened of you until the "
        "end of your next turn; once on each of your turns, extra necrotic damage equal to your level ({level})",
        ("Starting at 3rd level", "within 10 feet of you that can see you must succeed on a Charisma saving throw (8 + your proficiency bonus + your Charisma modifier)",
         "Your transformation lasts for 1 minute", "The extra necrotic damage equals your level",
         "you can't use it again until you finish a long rest"), level=3, dc="CHA", save="CHA"),
    "aasimar-vgm-protector-vgm-trait-0": _e("aasimar-vgm", "Radiant Soul", 1, "long",
        "Action, 1 minute: flying speed of 30 feet; once on each of your turns, extra radiant damage equal to your level ({level})",
        ("Starting at 3rd level", "Your transformation lasts for 1 minute", "you have a flying speed of 30 feet",
         "The extra radiant damage equals your level", "you can't use it again until you finish a long rest"), level=3),
    "aasimar-vgm-scourge-vgm-trait-0": _e("aasimar-vgm", "Radiant Consumption", 1, "long",
        "Action, 1 minute: bright light 10 feet and dim light 10 feet further; at the end of each of your turns you and "
        "each creature within 10 feet take radiant damage equal to half your level rounded up ({half_level_up}); once "
        "on each of your turns, extra radiant damage equal to your level ({level})",
        ("Starting at 3rd level", "Your transformation lasts for 1 minute", "radiant damage equal to half your level (rounded up)",
         "The extra radiant damage equals your level", "you can't use it again until you finish a long rest"), level=3),
    # --- Astral elf, autognome, deep gnome
    "astral-elf-aag-trait-5": _e("astral-elf-aag", "Starlight Step", "pb", "long",
        "Bonus Action: teleport up to 30 feet to an unoccupied space you can see",
        ("teleport up to 30 feet to an unoccupied space you can see", _PB_LONG)),
    "autognome-aag-trait-2": _e("autognome-aag", "Built for Success", "pb", "long",
        "Add 1d4 to one attack roll, ability check or saving throw after seeing the d20 roll",
        ("You can add a d4 to one attack roll, ability check, or saving throw you make", _PB_LONG), die="1d4"),
    "deep-gnome-mpmm-trait-4": _e("deep-gnome-mpmm", "Svirfneblin Camouflage", "pb", "long",
        "Advantage on a Dexterity (Stealth) check",
        ("make the check with advantage", _PB_LONG)),
    # --- Dhampir
    "dhampir-rhw-trait-3": _e("dhampir-rhw", "Vampiric Bite", "pb", "long",
        "Unarmed Strike bite: Piercing damage 1d4 plus your Constitution modifier ({con_mod:+d}); when it hits a creature "
        "that isn't a Construct or an Undead you can empower yourself",
        ("You deal Piercing damage equal to 1d4 plus your Constitution modifier",
         "a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest"),
        die="1d4"),
    "dhampir-vrgr-trait-5": _e("dhampir-vrgr", "Vampiric Bite", "pb", "long",
        "Bite (natural weapon): add your Constitution modifier ({con_mod:+d}) to attack and damage, 1d4 piercing; when it "
        "hits a creature that isn't a Construct or an Undead you can empower yourself",
        ("You add your Constitution modifier, instead of your Strength modifier", "It deals 1d4 piercing damage on a hit",
         _PB_LONG), die="1d4"),
    # --- Dragonborn (PHB, Ravenite/Draconblood, FTD)
    "dragonborn-phb-trait-3": _e("dragonborn-phb", "Breath Weapon", 1, "short-or-long",
        "Action: exhale destructive energy ({damage_type}); size, shape and the saving throw follow your Draconic "
        "Ancestry; {dice} damage on a failed save and half as much on a success",
        ("The DC for this saving throw equals 8 + your Constitution modifier + your proficiency bonus",
         "A creature takes 2d6 damage on a failed save, and half as much damage on a successful one",
         "The damage increases to 3d6 at 6th level, 4d6 at 11th level, and 5d6 at 16th level",
         "you can't use it again until you complete a short or long rest"),
        dc="CON", damage_type="ancestry", dice_by_level=((1, "2d6"), (6, "3d6"), (11, "4d6"), (16, "5d6"))),
    "dragonborn-phb-draconblood-egw-trait-1": _e("dragonborn-phb", "Forceful Presence", 1, "short-or-long",
        "Advantage on a Charisma (Intimidation or Persuasion) check",
        ("you can do so with advantage", "you can't do so again until you finish a short or long rest")),
    "dragonborn-phb-ravenite-egw-trait-1": _e("dragonborn-phb", "Vengeful Assault", 1, "short-or-long",
        "Reaction when you take damage from a creature in range of a weapon you wield: make an attack against that creature",
        ("you can use your reaction to make an attack with the weapon against that creature",
         "you can't do so again until you finish a short or long rest")),
    "dragonborn-(chromatic)-ftd-trait-1": _e("dragonborn-(chromatic)-ftd", "Breath Weapon", "pb", "long",
        "Replaces one of your attacks in the Attack action: 30-foot line that is 5 feet wide, Dexterity save, {dice} "
        "{damage_type} damage on a failed save and half as much on a success",
        ("replace one of your attacks with an exhalation of magical energy in a 30-foot line that is 5 feet wide",
         "must make a Dexterity saving throw (DC = 8 + your Constitution modifier + your proficiency bonus)",
         "On a failed save, the creature takes 1d10 damage of the type associated with your Chromatic Ancestry",
         "This damage increases by 1d10 when you reach 5th level (2d10), 11th level (3d10), and 17th level (4d10)",
         "You can use your Breath Weapon " + _PB_LONG),
        dc="CON", save="DEX", damage_type="ancestry", dice_by_level=((1, "1d10"), (5, "2d10"), (11, "3d10"), (17, "4d10"))),
    "dragonborn-(chromatic)-ftd-trait-3": _e("dragonborn-(chromatic)-ftd", "Chromatic Warding", 1, "long",
        "Action, 1 minute: immune to the damage type of your Chromatic Ancestry ({damage_type})",
        ("Starting at 5th level", "For 1 minute, you become immune to the damage type associated with your Chromatic Ancestry",
         "you can't do so again until you finish a long rest"), level=5, damage_type="ancestry"),
    "dragonborn-(gem)-ftd-trait-1": _e("dragonborn-(gem)-ftd", "Breath Weapon", "pb", "long",
        "Replaces one of your attacks in the Attack action: 15-foot cone, Dexterity save, {dice} {damage_type} damage on "
        "a failed save and half as much on a success",
        ("replace one of your attacks with an exhalation of magical energy in a 15-foot cone",
         "must make a Dexterity saving throw (DC = 8 + your Constitution modifier + your proficiency bonus)",
         "On a failed save, the creature takes 1d10 damage of the type associated with your Gem Ancestry",
         "This damage increases by 1d10 when you reach 5th level (2d10), 11th level (3d10), and 17th level (4d10)",
         "You can use your Breath Weapon " + _PB_LONG),
        dc="CON", save="DEX", damage_type="ancestry", dice_by_level=((1, "1d10"), (5, "2d10"), (11, "3d10"), (17, "4d10"))),
    "dragonborn-(gem)-ftd-trait-4": _e("dragonborn-(gem)-ftd", "Gem Flight", 1, "long",
        "Bonus Action, 1 minute: spectral wings give a flying speed equal to your walking speed{speed_part} and you can hover",
        ("Starting at 5th level", "These wings last for 1 minute", "you gain a flying speed equal to your walking speed and can hover",
         "you can't do so again until you finish a long rest"), level=5),
    "dragonborn-(metallic)-ftd-trait-1": _e("dragonborn-(metallic)-ftd", "Breath Weapon", "pb", "long",
        "Replaces one of your attacks in the Attack action: 15-foot cone, Dexterity save, {dice} {damage_type} damage on "
        "a failed save and half as much on a success",
        ("replace one of your attacks with an exhalation of magical energy in a 15-foot cone",
         "must make a Dexterity saving throw (DC = 8 + your Constitution modifier + your proficiency bonus)",
         "On a failed save, the creature takes 1d10 damage of the type associated with your Metallic Ancestry",
         "This damage increases by 1d10 when you reach 5th level (2d10), 11th level (3d10), and 17th level (4d10)",
         "You can use your Breath Weapon " + _PB_LONG),
        dc="CON", save="DEX", damage_type="ancestry", dice_by_level=((1, "1d10"), (5, "2d10"), (11, "3d10"), (17, "4d10"))),
    "dragonborn-(metallic)-ftd-trait-3": _e("dragonborn-(metallic)-ftd", "Metallic Breath Weapon", 1, "long",
        "Replaces one of your attacks in the Attack action: 15-foot cone, a second breath weapon whose effect you choose "
        "each time you use it",
        ("At 5th level, you gain a second breath weapon", "in a 15-foot cone",
         "The save DC for this breath is 8 + your Constitution modifier + your proficiency bonus",
         "you can't do so again until you finish a long rest"), level=5, dc="CON"),
    # --- Eladrin, elf (Eladrin / Shadar-kai), shadar-kai
    "eladrin-mpmm-trait-4": _e("eladrin-mpmm", "Fey Step", "pb", "long",
        "Bonus Action: teleport up to 30 feet to an unoccupied space you can see",
        ("teleport up to 30 feet to an unoccupied space you can see", _PB_LONG)),
    "elf-phb-eladrin-mtf-trait-1": _e("elf-phb", "Fey Step", 1, "short-or-long",
        "Bonus Action: teleport up to 30 feet to an unoccupied space you can see",
        ("teleport up to 30 feet to an unoccupied space you can see",
         "you can't do so again until you finish a short or long rest")),
    "elf-phb-shadar-kai-mtf-trait-1": _e("elf-phb", "Blessing of the Raven Queen", 1, "long",
        "Bonus Action: teleport up to 30 feet to an unoccupied space you can see; from 3rd level you also have "
        "resistance to all damage until the start of your next turn",
        ("teleport up to 30 feet to an unoccupied space you can see", "you can't do so again until you finish a long rest",
         "you also gain resistance to all damage when you teleport using this trait")),
    "shadar-kai-mpmm-trait-1": _e("shadar-kai-mpmm", "Blessing of the Raven Queen", "pb", "long",
        "Bonus Action: teleport up to 30 feet to an unoccupied space you can see; from 3rd level you also have "
        "resistance to all damage until the start of your next turn",
        ("teleport up to 30 feet to an unoccupied space you can see", _PB_LONG,
         "you also gain resistance to all damage when you teleport using this trait")),
    # --- Firbolg, giff, goblin, goliath, hadozee, harengon
    "firbolg-mpmm-trait-1": _e("firbolg-mpmm", "Hidden Step", "pb", "long",
        "Bonus Action: turn invisible until the start of your next turn or until you attack, make a damage roll, or force a saving throw",
        ("you can magically turn invisible until the start of your next turn", _PB_LONG)),
    "firbolg-vgm-trait-3": _e("firbolg-vgm", "Hidden Step", 1, "short-or-long",
        "Bonus Action: turn invisible until the start of your next turn or until you attack, make a damage roll, or force a saving throw",
        ("you can magically turn invisible until the start of your next turn",
         "you can't use it again until you finish a short or long rest")),
    "giff-aag-trait-0": _e("giff-aag", "Astral Spark", "pb", "long",
        "On a hit, the target takes extra Force damage equal to your Proficiency Bonus ({pb}); no more than once per turn",
        ("take extra force damage equal to your proficiency bonus", "no more than once per turn",
         "You regain all expended uses when you finish a long rest")),
    "goblin-mpmm-trait-3": _e("goblin-mpmm", "Fury of the Small", "pb", "long",
        "When you damage a creature larger than you, extra damage equal to your Proficiency Bonus ({pb}); no more than once per turn",
        ("The extra damage equals your proficiency bonus", "regaining all expended uses when you finish a long rest",
         "no more than once per turn")),
    "goblin-vgm-trait-3": _e("goblin-vgm", "Fury of the Small", 1, "short-or-long",
        "When you damage a creature larger than you, extra damage equal to your level ({level})",
        ("The extra damage equals your level", "you can't use it again until you finish a short or long rest")),
    "goliath-mpmm-trait-2": _e("goliath-mpmm", "Stone's Endurance", "pb", "long",
        "Reaction when you take damage: roll 1d12 + your Constitution modifier ({con_mod:+d}) and reduce the damage by that total",
        ("roll a d12. Add your Constitution modifier to the number rolled and reduce the damage by that total", _PB_LONG), die="1d12"),
    "goliath-vgm-trait-3": _e("goliath-vgm", "Stone's Endurance", 1, "short-or-long",
        "Reaction when you take damage: roll 1d12 + your Constitution modifier ({con_mod:+d}) and reduce the damage by that total",
        ("roll a d12. Add your Constitution modifier to the number rolled, and reduce the damage by that total",
         "you can't use it again until you finish a short or long rest"), die="1d12"),
    "hadozee-aag-trait-3": _e("hadozee-aag", "Hadozee Dodge", "pb", "long",
        "Reaction when you take damage: roll 1d6 + your Proficiency Bonus ({pb}) and reduce the damage by that total (minimum 0)",
        ("you can use your reaction to roll a d6. Add your proficiency bonus to the number rolled",
         "You can use this trait a number of times equal to your proficiency bonus. You regain all expended uses when you finish a long rest"),
        die="1d6"),
    "harengon-mpmm-trait-4": _e("harengon-mpmm", "Rabbit Hop", "pb", "long",
        "Bonus Action: jump {hop} feet (five times your Proficiency Bonus) without provoking opportunity attacks",
        ("jump a number of feet equal to five times your proficiency bonus, without provoking opportunity attacks", _PB_LONG)),
    "harengon-wbtw-trait-4": _e("harengon-wbtw", "Rabbit Hop", "pb", "long",
        "Bonus Action: jump {hop} feet (five times your Proficiency Bonus) without provoking opportunity attacks",
        ("jump a number of feet equal to five times your proficiency bonus, without provoking opportunity attacks", _PB_LONG)),
    # --- Hexblood, hobgoblin
    "hexblood-vrgr-trait-4": _e("hexblood-vrgr", "Eerie Token", 1, "long",
        "Bonus Action: remove a lock of hair, a nail or a tooth to create a token imbued with magic until you finish a long rest",
        ("you can harmlessly remove a lock of your hair, one of your nails, or one of your teeth",
         "Once you create a token using this feature, you can't do so again until you finish a long rest")),
    "hobgoblin-mpmm-trait-3": _e("hobgoblin-mpmm", "Fey Gift", "pb", "long",
        "Take the Help action as a Bonus Action",
        ("take the Help action as a bonus action", "You regain all expended uses when you finish a long rest")),
    "hobgoblin-mpmm-trait-4": _e("hobgoblin-mpmm", "Fortune from the Many", "pb", "long",
        "When you miss with an attack or fail an ability check or saving throw, add a bonus equal to the allies you can see within 30 feet (maximum +3)",
        ("a bonus to the roll equal to the number of allies you can see within 30 feet of you (maximum bonus of +3)", _PB_LONG)),
    "hobgoblin-vgm-trait-4": _e("hobgoblin-vgm", "Saving Face", 1, "short-or-long",
        "When you miss with an attack or fail an ability check or saving throw, add a bonus equal to the allies you can see within 30 feet (maximum +5)",
        ("(maximum bonus of +5)", "you can't use it again until you finish a short or long rest")),
    # --- Halfling (PHB), Kor: WF, word-for-word the SRD Lucky (note only; the PHB text omits "the d20")
    "halfling-phb-trait-2": _e("halfling-phb", "Lucky", None, None, _LUCKY_NOTE,
        ("When you roll a 1 on an attack roll, ability check, or saving throw, you can reroll the die and must use "
         "the new roll",)),
    "kor-psz-trait-7": _e("kor-psz", "Lucky", None, None, _LUCKY_NOTE,
        ("When you roll a 1 on the d20 for an attack roll, ability check, or saving throw, you can reroll the die and "
         "must use the new roll",)),
    # --- Human (Mark of Sentinel), kender, kenku, kobold, leonin, lizardfolk
    "human-phb-mark-of-sentinel-erlw-trait-2": _e("human-phb", "Vigilant Guardian", 1, "long",
        "Reaction when a creature within 5 feet is hit by an attack: swap places with it and take the hit instead",
        ("you can use your reaction to swap places with that creature", "you can't do so again until you finish a long rest")),
    "kender-dsotdq-trait-0": _e("kender-dsotdq", "Fearless", 1, "long",
        "When you fail a saving throw to avoid or end the frightened condition on yourself, you can succeed instead",
        ("you can choose to succeed instead", "you can't do so again until you finish a long rest")),
    "kender-dsotdq-trait-2": _e("kender-dsotdq", "Taunt", "pb", "long",
        "Bonus Action: a creature within 60 feet makes a Wisdom save or has disadvantage on attacks against targets other "
        "than you until the start of your next turn; DC 8 + your Proficiency Bonus ({pb}) + the Intelligence, Wisdom or Charisma modifier you chose",
        ("must succeed on a Wisdom saving throw", "The DC equals 8 + your proficiency bonus + your Intelligence, Wisdom, or Charisma modifier (choose when you select this race)",
         "You can use this bonus action " + _PB_LONG)),
    "kenku-mpmm-trait-2": _e("kenku-mpmm", "Kenku Recall", "pb", "long",
        "Advantage on an ability check using a skill you are proficient in (declared before rolling)",
        ("you can give yourself advantage on the check before rolling the d20",
         "You can give yourself advantage in this way " + _PB_LONG)),
    "kobold-mpmm-trait-1": _e("kobold-mpmm", "Draconic Cry", "pb", "long",
        "Bonus Action: enemies within 10 feet that can hear you; until the start of your next turn you and your allies have advantage on attack rolls against them",
        ("you let out a cry at your enemies within 10 feet of you", _PB_LONG)),
    "kobold-vgm-trait-3": _e("kobold-vgm", "Grovel, Cower, and Beg", 1, "short-or-long",
        "Action: until the end of your next turn your allies have advantage on attack rolls against enemies within 10 feet of you that you can see",
        ("your allies gain advantage on attack rolls against enemies within 10 feet of you that you can see",
         "you can't use it again until you finish a short or long rest")),
    "leonin-mot-trait-6": _e("leonin-mot", "Daunting Roar", 1, "short-or-long",
        "Bonus Action: creatures of your choice within 10 feet make a Wisdom save or are frightened of you until the end of your next turn",
        ("Creatures of your choice within 10 feet of you that can hear you must succeed on a Wisdom saving throw",
         "The DC of the save equals 8 + your proficiency bonus + your Constitution modifier",
         "you can't use it again until you finish a short or long rest"), dc="CON", save="WIS"),
    "lizardfolk-mpmm-trait-3": _e("lizardfolk-mpmm", "Hungry Jaws", "pb", "long",
        "Bonus Action: a special Bite attack; on a hit it deals normal damage and you gain {pb} Temporary Hit Points (your Proficiency Bonus)",
        ("you can make a special attack with your Bite", "you gain temporary hit points equal to your proficiency bonus", _PB_LONG)),
    "lizardfolk-vgm-trait-8": _e("lizardfolk-vgm", "Hungry Jaws", 1, "short-or-long",
        "Bonus Action: a special bite attack; on a hit it deals normal damage and you gain {con_temp} Temporary Hit Points (your Constitution modifier, minimum 1)",
        ("you can make a special attack with your bite", "temporary hit points equal to your Constitution modifier (minimum of 1)",
         "you can't use this trait again until you finish a short or long rest")),
    # --- Relentless Endurance (orc, half-orc, minotaur), Adrenaline Rush
    "half-orc-phb-trait-4": _e("half-orc-phb", "Relentless Endurance", 1, "long",
        "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        ("you can drop to 1 hit point instead", "You can't use this feature again until you finish a long rest")),
    "orc-mpmm-trait-3": _e("orc-mpmm", "Relentless Endurance", 1, "long",
        "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        ("you can drop to 1 hit point instead", "you can't do so again until you finish a long rest")),
    "orc-(ixalan)-psx-trait-4": _e("orc-(ixalan)-psx", "Relentless Endurance", 1, "long",
        "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        ("you can drop to 1 hit point instead", "You can't use this feature again until you finish a long rest")),
    "minotaur-(amonkhet)-psa-trait-5": _e("minotaur-(amonkhet)-psa", "Relentless Endurance", 1, "long",
        "When reduced to 0 Hit Points but not killed outright, drop to 1 Hit Point instead",
        ("you can drop to 1 hit point instead", "You can't use this feature again until you finish a long rest")),
    "orc-mpmm-trait-0": _e("orc-mpmm", "Adrenaline Rush", "pb", "long",
        "Take the Dash action as a Bonus Action and gain {pb} Temporary Hit Points",
        ("You can take the Dash action as a bonus action", "you gain a number of temporary hit points equal to your proficiency bonus", _PB_LONG)),
    # --- Reborn, shifter, vedalken
    "reborn-vrgr-trait-3": _e("reborn-vrgr", "Knowledge from a Past Life", "pb", "long",
        "When you make an ability check that uses a skill, add 1d6 after seeing the d20",
        ("roll a d6 immediately after seeing the number on the d20 and add the number on the d6 to the check", "You can use this feature " + _PB_LONG),
        die="1d6"),
    "shifter-mpmm-trait-2": _e("shifter-mpmm", "Shifting", "pb", "long",
        "Bonus Action, 1 minute: gain {two_pb} Temporary Hit Points (2 times your Proficiency Bonus) and the benefit of your shifter option",
        ("This transformation lasts for 1 minute", "you gain temporary hit points equal to 2 × your proficiency bonus",
         "You can shift " + _PB_LONG)),
    "shifter-erlw-trait-5": _e("shifter-erlw", "Shifting", 1, "short-or-long",
        "Bonus Action, 1 minute: gain {shift_temp} Temporary Hit Points (your level plus your Constitution modifier, minimum 1) and your subrace's benefits",
        ("This transformation lasts for 1 minute", "temporary hit points equal to your level + your Constitution modifier (minimum of 1 temporary hit point)",
         "you can't do so again until you finish a short or long rest")),
    "vedalken-ggr-trait-5": _e("vedalken-ggr", "Partially Amphibious", 1, "long",
        "You can breathe underwater for up to 1 hour",
        ("you can breathe underwater for up to 1 hour", "you can't use this trait again until you finish a long rest")),
})

# W5a: Giant Ancestry (Goliath, XPHB) boons by species variant id. The catalog trait text drops the list, so the
# `quote` is pinned against the raw 5etools race entry instead (tests/test_w5a_species_resources.py).
GIANT_ANCESTRY_2024: dict[str, dict] = {
    "cloud-giant-ancestry": {"name": "Cloud's Jaunt", "note": "Bonus Action: teleport up to 30 feet to an unoccupied space you can see",
                             "quote": "you magically teleport up to 30 feet to an unoccupied space you can see"},
    "fire-giant-ancestry": {"name": "Fire's Burn", "note": "when you hit a target with an attack roll and deal damage, also deal 1d10 Fire damage to it",
                            "quote": "you can also deal 1d10 Fire damage to that target"},
    "frost-giant-ancestry": {"name": "Frost's Chill", "note": "when you hit a target with an attack roll and deal damage, also deal 1d6 Cold damage and reduce its Speed by 10 feet until the start of your next turn",
                             "quote": "you can also deal 1d6 Cold damage to that target and reduce its Speed by 10 feet until the start of your next turn"},
    "hill-giant-ancestry": {"name": "Hill's Tumble", "note": "when you hit a Large or smaller creature with an attack roll and deal damage, give it the Prone condition",
                            "quote": "you can give that target the Prone condition"},
    "stone-giant-ancestry": {"name": "Stone's Endurance", "note": "Reaction when you take damage: roll 1d12 + your Constitution modifier ({con_mod:+d}) and reduce the damage by that total",
                             "quote": "roll 1d12. Add your Constitution modifier to the number rolled and reduce the damage by that total"},
    "storm-giant-ancestry": {"name": "Storm's Thunder", "note": "Reaction when you take damage from a creature within 60 feet: deal 1d8 Thunder damage to it",
                             "quote": "you can take a Reaction to deal 1d8 Thunder damage to that creature"},
}

# W1 (F3): "Your speed is not reduced by wearing heavy armor." Traits (official races) and the SRD dwarf, whose SRD
# record has no such trait (the sentence is in the SRD Dwarf Speed text), pinned by race id. Dwarf (XPHB) has none.
HEAVY_ARMOR_SPEED_EXEMPT_TRAITS: dict[str, str] = {
    "dwarf-phb-trait-2": "Your speed is not reduced by wearing heavy armor.",
    "dwarf-(kaladesh)-psk-trait-3": "Your speed is not reduced by wearing heavy armor.",
}
HEAVY_ARMOR_SPEED_EXEMPT_RACES: dict[str, str] = {"dwarf": "Your speed is not reduced by wearing heavy armor."}


# Fixed proficiency grants of a subclass (the SRD feature text is prose only).
# Only subclasses whose grant is a fixed list belong here; Lore Bard's three
# free skills are a choice (RP12: SUBCLASS_PICKS_2024, ruleset 2024).
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

# FE6 (B3): 5etools says `skillProficiencies: [{"any": 1}]` for Echoing Soul (Ravenloft), but the feat text says
# "You have proficiency in two skills of your choice." The text wins: index -> number of skill picks.
FEAT_SKILL_PICK_COUNT_OVERRIDES = {"echoing-soul-rhw": 2}

# W4 (F5): a 2024 background record whose `feats` field is missing from the 5etools file although its own entry names
# the feat. Key = "name|source" lowercased; `grant` is the raw-shaped `feats` list the converter then reads like any
# other (so the variant hint "Wizard Spells" follows); `quote` is the record's own text (pinned by a test).
BACKGROUND_FEATS_FROM_TEXT: dict[str, dict] = {
    "genie touched|frhof": {
        "grant": [{"magic initiate; wizard|xphb": True}],
        "quote": "{@feat Magic Initiate|XPHB} (Wizard)",
    },
}

# FE6 (B4): 5etools says `languageProficiencies: [{"thieves' cant": true}]` for Harper Agent (FRHoF) and the
# converter used to drop the unknown key. index -> language ids ("You know Thieves' Cant."). Display names come
# from LANGUAGE_NAMES (the 2024 rare table, C6b-2).
FEAT_FIXED_LANGUAGE_OVERRIDES = {"harper-agent-frhof": ["thieves-cant"]}

# RP3 (A1): a feat whose fixed language becomes "one language of your choice" when the character already knows it.
# index -> {language, label, quote} (`quote` is pinned against the catalog feat text). The replacement pool is the
# PHB 2024 Standard + Rare tables (decision E2): the feat text names "the language tables in the Player's Handbook
# or Chapter 2 of this book" and the catalog has no FRHoF-specific language table.
FEAT_LANGUAGE_REPLACEMENT = {
    "cult-of-the-dragon-initiate-frhof": {
        "language": "draconic",
        "label": "Dragon's Tongue",
        "quote": ("If you already know Draconic when you select this feat, you instead learn one language "
                  "of your choice from the language tables in the Player's Handbook or Chapter 2 of this book."),
    },
}


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

# --- Class resources (R9, decision E14): the 2024 resource tail, prose-only ---
# No XPHB class table column carries these numbers (columns: barbarian rages / rage-damage / weapon-mastery,
# bard bardic-die, cleric + paladin channel-divinity, druid wild-shape, fighter second-wind / weapon-mastery,
# monk martial-arts / focus-points / unarmored-movement, ranger favored-enemy, rogue sneak-attack, sorcerer
# sorcery-points, warlock invocations). `class_resources._tail_2024` builds one resource per entry, under ruleset
# "2024" only, when the XPHB feature record `feature` is in the catalog and the class level has reached that
# record's level. `uses` is an int, "wis_min1" (max(1, Wisdom modifier)) or None (note only, no uses and no
# recharge). `note` may use {half_level} (floor(class level / 2)) and {wis_min1}; `extras` are
# (feature id, text) pairs appended to the note once that XPHB feature record's level is reached.
# Texts are the XPHB feature texts as imported (quoted per entry).
RESOURCE_TAIL_2024: tuple[dict, ...] = (
    # Innate Sorcery: "You can use this feature twice, and you regain all expended uses of it when you finish a
    # Long Rest." / "The spell save DC of your Sorcerer spells increases by 1. You have Advantage on the attack
    # rolls of Sorcerer spells you cast."
    {"class": "sorcerer", "feature": "xphb-sorcerer-1-innate-sorcery", "name": "Innate Sorcery", "uses": 2,
     "recharge": "long",
     "note": "Bonus Action, 1 minute: the spell save DC of your Sorcerer spells increases by 1 and you have "
             "Advantage on the attack rolls of Sorcerer spells you cast",
     "extras": (
         # Sorcery Incarnate (7): "If you have no uses of Innate Sorcery left, you can use it if you spend 2 Sorcery
         # Points when you take the Bonus Action to activate it. ... you can use up to two of your Metamagic options
         # on each spell you cast."
         ("xphb-sorcerer-7-sorcery-incarnate", "with no uses left you can activate it by spending 2 Sorcery Points; "
          "while it is active you can use up to two Metamagic options on each spell you cast"),
         # Arcane Apotheosis (20): "While your Innate Sorcery feature is active, you can use one Metamagic option on
         # each of your turns without spending Sorcery Points on it."
         ("xphb-sorcerer-20-arcane-apotheosis", "while it is active you can use one Metamagic option on each of "
          "your turns without spending Sorcery Points on it"))},
    # Sorcerous Restoration: "When you finish a Short Rest, you can regain expended Sorcery Points, but no more than
    # a number equal to half your Sorcerer level (round down). Once you use this feature, you can't do so again
    # until you finish a Long Rest."
    {"class": "sorcerer", "feature": "xphb-sorcerer-5-sorcerous-restoration", "name": "Sorcerous Restoration",
     "uses": 1, "recharge": "long",
     "note": "When you finish a Short Rest, regain expended Sorcery Points, up to half your Sorcerer level "
             "rounded down ({half_level})"},
    # Uncanny Metabolism: "When you roll Initiative, you can regain all expended Focus Points. When you do so, roll
    # your Martial Arts die, and regain a number of Hit Points equal to your Monk level plus the number rolled.
    # Once you use this feature, you can't use it again until you finish a Long Rest." (details.heal is built from
    # the Martial Arts die resource)
    {"class": "monk", "feature": "xphb-monk-2-uncanny-metabolism", "name": "Uncanny Metabolism", "uses": 1,
     "recharge": "long", "heal_martial_arts": True,
     "note": "When you roll Initiative, regain all expended Focus Points and regain Hit Points equal to your Monk "
             "level plus a roll of your Martial Arts die"},
    # Divine Intervention: "As a Magic action, choose any Cleric spell of level 5 or lower that doesn't require a
    # Reaction to cast. As part of the same action, you cast that spell without expending a spell slot or needing
    # Material components. You can't use this feature again until you finish a Long Rest."
    {"class": "cleric", "feature": "xphb-cleric-10-divine-intervention", "name": "Divine Intervention", "uses": 1,
     "recharge": "long",
     "note": "Magic action: cast any Cleric spell of level 5 or lower that doesn't require a Reaction, without "
             "a spell slot or Material components",
     "extras": (
         # Greater Divine Intervention (20): "you can choose Wish when you select a spell. If you do so, you can't
         # use Divine Intervention again until you finish 2d4 Long Rests."
         ("xphb-cleric-20-greater-divine-intervention", "you can choose Wish; if you do, you can't use Divine "
          "Intervention again until you finish 2d4 Long Rests"),)},
    # Paladin's Smite: "You always have the Divine Smite spell prepared. In addition, you can cast it without
    # expending a spell slot, but you must finish a Long Rest before you can cast it in this way again."
    {"class": "paladin", "feature": "xphb-paladin-2-paladins-smite", "name": "Paladin's Smite", "uses": 1,
     "recharge": "long", "note": "Cast Divine Smite without expending a spell slot"},
    # Faithful Steed: "You always have the Find Steed spell prepared. You can also cast the spell once without
    # expending a spell slot, and you regain the ability to do so when you finish a Long Rest."
    {"class": "paladin", "feature": "xphb-paladin-5-faithful-steed", "name": "Faithful Steed", "uses": 1,
     "recharge": "long", "note": "Cast Find Steed once without expending a spell slot"},
    # Tireless: "As a Magic action, you can give yourself a number of Temporary Hit Points equal to 1d8 plus your
    # Wisdom modifier (minimum of 1). You can use this action a number of times equal to your Wisdom modifier
    # (minimum of once), and you regain all expended uses when you finish a Long Rest. ... Whenever you finish a
    # Short Rest, your Exhaustion level, if any, decreases by 1."
    {"class": "ranger", "feature": "xphb-ranger-10-tireless", "name": "Tireless", "uses": "wis_min1",
     "recharge": "long",
     "note": "Magic action: gain Temporary Hit Points equal to 1d8 + {wis_min1} (Wisdom modifier, minimum 1); "
             "whenever you finish a Short Rest your Exhaustion level decreases by 1"},
    # Nature's Veil: "As a Bonus Action, you can give yourself the Invisible condition until the end of your next
    # turn. You can use this feature a number of times equal to your Wisdom modifier (minimum of once), and you
    # regain all expended uses when you finish a Long Rest."
    {"class": "ranger", "feature": "xphb-ranger-14-natures-veil", "name": "Nature's Veil", "uses": "wis_min1",
     "recharge": "long",
     "note": "Bonus Action: gain the Invisible condition until the end of your next turn"},
    # Wild Companion (decision E9, a note only): "As a Magic action, you can expend a spell slot or a use of Wild
    # Shape to cast the Find Familiar spell without Material components. When you cast the spell in this way, the
    # familiar is Fey and disappears when you finish a Long Rest."
    {"class": "druid", "feature": "xphb-druid-2-wild-companion", "name": "Wild Companion", "uses": None,
     "recharge": None,
     "note": "Magic action: expend a spell slot or a use of Wild Shape to cast Find Familiar without Material "
             "components; the familiar is Fey and disappears when you finish a Long Rest"},
    # Wild Resurgence: "Once on each of your turns, if you have no uses of Wild Shape left, you can give yourself
    # one use by expending a spell slot (no action required). In addition, you can expend one use of Wild Shape
    # (no action required) to give yourself a level 1 spell slot, but you can't do so again until you finish a
    # Long Rest." (the one use counted is the second, once per Long Rest, benefit)
    {"class": "druid", "feature": "xphb-druid-5-wild-resurgence", "name": "Wild Resurgence", "uses": 1,
     "recharge": "long",
     "note": "Once on each of your turns, with no Wild Shape uses left, expend a spell slot to regain one use "
             "(no action); expend one Wild Shape use to gain a level 1 spell slot (no action)"},
    # Archdruid, Nature Magician: "You can convert uses of Wild Shape into a spell slot (no action required).
    # Choose a number of your unexpended uses of Wild Shape and convert them into a single spell slot, with each
    # use contributing 2 spell levels. For example, if you convert two uses of Wild Shape, you produce a level 4
    # spell slot. Once you use this benefit, you can't do so again until you finish a Long Rest."
    {"class": "druid", "feature": "xphb-druid-20-archdruid", "name": "Nature Magician", "uses": 1,
     "recharge": "long",
     "note": "Convert unexpended Wild Shape uses into one spell slot, each use giving 2 spell levels "
             "(two uses = a level 4 slot), no action"},
    # Stroke of Luck: "If you fail a D20 Test, you can turn the roll into a 20. Once you use this feature, you
    # can't use it again until you finish a Short or Long Rest."
    {"class": "rogue", "feature": "xphb-rogue-20-stroke-of-luck", "name": "Stroke of Luck", "uses": 1,
     "recharge": "short-or-long", "note": "If you fail a D20 Test, you can turn the roll into a 20"},
    # Persistent Rage: "When you roll Initiative, you can regain all expended uses of Rage. After you regain uses
    # of Rage in this way, you can't do so again until you finish a Long Rest."
    {"class": "barbarian", "feature": "xphb-barbarian-15-persistent-rage", "name": "Persistent Rage", "uses": 1,
     "recharge": "long", "note": "When you roll Initiative, regain all expended uses of Rage"},
    # ---- RP10 (B1): note-only entries (uses None, no recharge) whose text gives numbers or a use rule. `quotes`
    # are (feature id, verbatim substring of the record's name + desc) pairs pinned by test. Note templates use
    # the variables of `class_resources._note_vars` (level, twice_level, five_level, wis, dex, cha, wis_min1,
    # cha_min1, dex_level, dc_wis / dc_cha / dc_dex = 8 + Proficiency Bonus + modifier, ma_die, spark_dice) and the
    # entry's own `vars`: name -> (default, ((feature id, value), ...)), the value of the last feature record
    # whose level the class has reached. Each note is one sentence with the computed number.
    {"class": "barbarian", "feature": "xphb-barbarian-9-brutal-strike", "name": "Brutal Strike", "uses": None,
     "recharge": None,
     "note": "If you use Reckless Attack you can forgo Advantage on one Strength attack roll; if it hits, the "
             "target takes an extra {brutal_die} damage and you cause {brutal_effects}: Forceful Blow (pushed 15 "
             "feet, then you move up to half your Speed), Hamstring Blow (Speed reduced by 15 feet until the start "
             "of your next turn)",
     "vars": {"brutal_die": ("1d10", (("xphb-barbarian-17-improved-brutal-strike", "2d10"),)),
              "brutal_effects": ("one effect", (("xphb-barbarian-17-improved-brutal-strike", "two different effects"),))},
     "extras": (("xphb-barbarian-13-improved-brutal-strike",
                 "also Staggering Blow (Disadvantage on its next saving throw, no Opportunity Attacks) and "
                 "Sundering Blow (+5 to the next attack roll by another creature against it)"),),
     "quotes": (("xphb-barbarian-9-brutal-strike", "the target takes an extra 1d10 damage"),
                ("xphb-barbarian-9-brutal-strike", "The target is pushed 15 feet straight away from you."),
                ("xphb-barbarian-9-brutal-strike", "The target's Speed is reduced by 15 feet"),
                ("xphb-barbarian-13-improved-brutal-strike", "Staggering Blow"),
                ("xphb-barbarian-13-improved-brutal-strike", "gains a +5 bonus to the roll"),
                ("xphb-barbarian-17-improved-brutal-strike", "The extra damage of your Brutal Strike increases to 2d10."),
                ("xphb-barbarian-17-improved-brutal-strike", "you can use two different Brutal Strike effects"))},
    {"class": "barbarian", "feature": "xphb-barbarian-11-relentless-rage", "name": "Relentless Rage", "uses": None,
     "recharge": None,
     "note": "If you drop to 0 Hit Points while raging and don't die outright: DC 10 Constitution saving throw (+5 "
             "for each use after the first, resetting to 10 after a Short or Long Rest); on a success your Hit "
             "Points become {twice_level}",
     "quotes": (("xphb-barbarian-11-relentless-rage", "you can make a DC 10 Constitution saving throw"),
                ("xphb-barbarian-11-relentless-rage", "a number equal to twice your Barbarian level"),
                ("xphb-barbarian-11-relentless-rage", "Each time you use this feature after the first, the DC increases by 5."),
                ("xphb-barbarian-11-relentless-rage", "When you finish a Short or Long Rest, the DC resets to 10."))},
    {"class": "cleric", "feature": "xphb-cleric-5-sear-undead", "name": "Sear Undead", "uses": None, "recharge": None,
     "note": "Whenever you use Turn Undead you can roll {wis_min1}d8 (Wisdom modifier, minimum 1); each Undead that "
             "fails its saving throw takes that much Radiant damage, which doesn't end the turn effect",
     "quotes": (("xphb-cleric-5-sear-undead", "a number of d8s equal to your Wisdom modifier (minimum of 1d8)"),
                ("xphb-cleric-5-sear-undead", "takes Radiant damage equal to the roll's total"))},
    {"class": "monk", "feature": "xphb-monk-3-deflect-attacks", "name": "Deflect Attacks", "uses": None,
     "recharge": None,
     "note": "Reaction when an attack hits you: reduce its damage by 1d10{dex_level:+d} (1d10 + Dexterity modifier "
             "+ Monk level); at 0 damage, 1 Focus Point to redirect 2{ma_die}{dex:+d} damage (Dexterity save, DC "
             "{dc_wis})",
     "extras": (("xphb-monk-13-deflect-energy", "works against attacks of any damage type (Deflect Energy)"),),
     "quotes": (("xphb-monk-3-deflect-attacks", "The reduction equals 1d10 plus your Dexterity modifier and Monk level."),
                ("xphb-monk-3-deflect-attacks", "you can expend 1 Focus Point to redirect"),
                ("xphb-monk-3-deflect-attacks", "damage equal to two rolls of your Martial Arts die plus your Dexterity modifier"),
                ("xphb-monk-13-deflect-energy", "any damage type"))},
    {"class": "monk", "feature": "xphb-monk-4-slow-fall", "name": "Slow Fall", "uses": None, "recharge": None,
     "note": "Reaction when you fall: reduce the fall damage by {five_level} (5 x Monk level)",
     "quotes": (("xphb-monk-4-slow-fall", "an amount equal to five times your Monk level"),)},
    {"class": "monk", "feature": "xphb-monk-5-stunning-strike", "name": "Stunning Strike", "uses": None,
     "recharge": None,
     "note": "Once per turn on a hit with a Monk weapon or Unarmed Strike, expend 1 Focus Point: Constitution save "
             "(DC {dc_wis}) or Stunned until the start of your next turn; on a success its Speed is halved",
     "quotes": (("xphb-monk-5-stunning-strike", "Once per turn when you hit a creature with a Monk weapon or an Unarmed Strike"),
                ("xphb-monk-5-stunning-strike", "you can expend 1 Focus Point to attempt a stunning strike"),
                ("xphb-monk-5-stunning-strike", "the target's Speed is halved until the start of your next turn"))},
    {"class": "monk", "feature": "xphb-monk-10-heightened-focus", "name": "Heightened Focus", "uses": None,
     "recharge": None,
     "note": "Flurry of Blows makes three Unarmed Strikes; Patient Defense gives Temporary Hit Points equal to two "
             "rolls of your Martial Arts die (2{ma_die}); Step of the Wind can carry a willing Large or smaller "
             "creature within 5 feet",
     "quotes": (("xphb-monk-10-heightened-focus", "make three Unarmed Strikes with it instead of two"),
                ("xphb-monk-10-heightened-focus", "a number of Temporary Hit Points equal to two rolls of your Martial Arts die"),
                ("xphb-monk-10-heightened-focus", "a willing creature within 5 feet of yourself that is Large or smaller"))},
    {"class": "monk", "feature": "xphb-monk-18-superior-defense", "name": "Superior Defense", "uses": None,
     "recharge": None,
     "note": "At the start of your turn, expend 3 Focus Points: Resistance to all damage except Force damage for 1 "
             "minute or until you have the Incapacitated condition",
     "quotes": (("xphb-monk-18-superior-defense", "you can expend 3 Focus Points to bolster yourself against harm for 1 minute"),
                ("xphb-monk-18-superior-defense", "Resistance to all damage except Force damage"))},
    {"class": "paladin", "feature": "xphb-paladin-9-abjure-foes", "name": "Abjure Foes", "uses": None,
     "recharge": None,
     "note": "Magic action, expend one Channel Divinity use: up to {cha_min1} creatures (Charisma modifier, minimum "
             "1) you can see within 60 feet make a Wisdom saving throw (DC {dc_cha}) or have the Frightened "
             "condition for 1 minute or until they take any damage",
     "quotes": (("xphb-paladin-9-abjure-foes", "expend one use of this class's Channel Divinity"),
                ("xphb-paladin-9-abjure-foes", "a number of creatures equal to your Charisma modifier (minimum of one creature)"),
                ("xphb-paladin-9-abjure-foes", "have the Frightened condition for 1 minute or until it takes any damage"))},
    {"class": "rogue", "feature": "xphb-rogue-5-cunning-strike", "name": "Cunning Strike", "uses": None,
     "recharge": None,
     "note": "When you deal Sneak Attack damage you can add {cunning_effects}, forgoing the dice shown for each: "
             "Poison 1d6 (Constitution save, needs a Poisoner's Kit), Trip 1d6 (Dexterity save, Large or "
             "smaller), Withdraw 1d6; save DC {dc_dex}",
     "vars": {"cunning_effects": ("one effect", (("xphb-rogue-11-improved-cunning-strike", "up to two effects"),))},
     "extras": (("xphb-rogue-14-devious-strikes",
                 "Devious Strikes add Daze 2d6, Obscure 3d6 and Knock Out 6d6 (Constitution or Dexterity save)"),),
     "quotes": (("xphb-rogue-5-cunning-strike", "the DC equals 8 plus your Dexterity modifier and Proficiency Bonus"),
                ("xphb-rogue-5-poison-(cost:-1d6)", "Poison (Cost: 1d6)"),
                ("xphb-rogue-5-trip-(cost:-1d6)", "Trip (Cost: 1d6)"),
                ("xphb-rogue-5-withdraw-(cost:-1d6)", "Withdraw (Cost: 1d6)"),
                ("xphb-rogue-5-poison-(cost:-1d6)", "you must have a Poisoner's Kit on your person"),
                ("xphb-rogue-11-improved-cunning-strike", "up to two Cunning Strike effects"),
                ("xphb-rogue-14-daze-(cost:-2d6)", "Daze (Cost: 2d6)"),
                ("xphb-rogue-14-obscure-(cost:-3d6)", "Obscure (Cost: 3d6)"),
                ("xphb-rogue-14-knock-out-(cost:-6d6)", "Knock Out (Cost: 6d6)"))},
)

# RP10 (B1): a sentence added to the `details.note` of an EXISTING 2024 class resource (`target` = its id), when
# the XPHB record `feature` is in the catalog and the class level has reached its level; `extras` and `vars` as
# above. Entries for the same target join with "; " after any note the resource already has.
RESOURCE_NOTES_2024: tuple[dict, ...] = (
    {"class": "bard", "target": "bard:bardic-inspiration", "feature": "xphb-bard-18-superior-inspiration",
     "note": "Superior Inspiration: when you roll Initiative, you regain expended uses until you have two if you "
             "have fewer than that",
     "quotes": (("xphb-bard-18-superior-inspiration",
                 "you regain expended uses of Bardic Inspiration until you have two if you have fewer than that"),)},
    {"class": "cleric", "target": "cleric:channel-divinity", "feature": "xphb-cleric-2-divine-spark",
     "note": "Divine Spark (Magic action, 30 feet): {spark_dice}d8{wis:+d} to restore Hit Points or force a "
             "Constitution save for that much Necrotic or Radiant damage (half on a success); Turn Undead (Magic "
             "action): Wisdom save, Undead within 30 feet are Frightened and Incapacitated for 1 minute; save DC "
             "{dc_wis}",
     "quotes": (("xphb-cleric-2-divine-spark", "Roll 1d8 and add your Wisdom modifier."),
                ("xphb-cleric-2-divine-spark", "On a successful save, the creature takes half as much damage"),
                ("xphb-cleric-2-turn-undead", "Each Undead of your choice within 30 feet of you must make a Wisdom saving throw"),
                ("xphb-cleric-2-turn-undead", "it has the Frightened and Incapacitated conditions for 1 minute"),
                ("xphb-cleric-2-channel-divinity", "the DC equals the spell save DC from this class's Spellcasting feature"))},
    {"class": "druid", "target": "druid:wild-shape", "feature": "xphb-druid-20-archdruid",
     "note": "Evergreen Wild Shape: whenever you roll Initiative and have no uses left, you regain one expended use",
     "quotes": (("xphb-druid-20-archdruid",
                 "Whenever you roll Initiative and have no uses of Wild Shape left, you regain one expended use of it."),)},
    {"class": "fighter", "target": "fighter:indomitable", "feature": "xphb-fighter-9-indomitable",
     "note": "If you fail a saving throw, reroll it with a bonus of +{level} (your Fighter level); you must use the "
             "new roll",
     "quotes": (("xphb-fighter-9-indomitable", "you can reroll it with a bonus equal to your Fighter level"),
                ("xphb-fighter-9-indomitable", "You must use the new roll"))},
    {"class": "fighter", "target": "fighter:second-wind", "feature": "xphb-fighter-2-tactical-mind",
     "note": "Tactical Mind: when you fail an ability check, expend a use to add 1d10 to it instead of regaining Hit "
             "Points; if the check still fails, the use isn't expended",
     "quotes": (("xphb-fighter-2-tactical-mind", "you can expend a use of your Second Wind"),
                ("xphb-fighter-2-tactical-mind", "you roll 1d10 and add the number rolled to the ability check"),
                ("xphb-fighter-2-tactical-mind", "If the check still fails, this use of Second Wind isn't expended."))},
    {"class": "monk", "target": "monk:focus-points", "feature": "xphb-monk-15-perfect-focus",
     "note": "Perfect Focus: when you roll Initiative and don't use Uncanny Metabolism, you regain expended Focus "
             "Points until you have 4 if you have 3 or fewer",
     "quotes": (("xphb-monk-15-perfect-focus",
                 "When you roll Initiative and don't use Uncanny Metabolism, you regain expended Focus Points until you have 4 if you have 3 or fewer."),)},
    {"class": "paladin", "target": "paladin:lay-on-hands", "feature": "xphb-paladin-1-lay-on-hands",
     "note": "Expend 5 Hit Points from the pool to remove the Poisoned condition from the creature (those points "
             "don't also restore Hit Points)",
     "extras": (("xphb-paladin-14-restoring-touch",
                 "Restoring Touch: 5 Hit Points of the pool per condition removed (Blinded, Charmed, Deafened, "
                 "Frightened, Paralyzed or Stunned)"),),
     "quotes": (("xphb-paladin-1-lay-on-hands", "expend 5 Hit Points from the pool of healing power to remove the Poisoned condition"),
                ("xphb-paladin-14-restoring-touch", "You must expend 5 Hit Points from the healing pool of Lay On Hands for each of these conditions you remove"),
                ("xphb-paladin-14-restoring-touch", "Blinded, Charmed, Deafened, Frightened, Paralyzed, or Stunned"))},
    {"class": "ranger", "target": "ranger:favored-enemy-hunter-s-mark", "feature": "xphb-ranger-20-foe-slayer",
     "note": "Foe Slayer: the damage die of your Hunter's Mark is a d10 rather than a d6",
     "quotes": (("xphb-ranger-20-foe-slayer", "The damage die of your Hunter's Mark is a d10 rather than a d6."),)},
)

# Cleric Divine Spark: "You roll an additional d8 when you reach Cleric levels 7 (2d8), 13 (3d8), and 18 (4d8)."
# (class level, dice), pinned against xphb-cleric-2-divine-spark; 1d8 below level 7.
DIVINE_SPARK_DICE_2024 = ((7, 2), (13, 3), (18, 4))

# ---- RP11 (B3): 2024 subclass resource tail. XPHB subclass features whose text gives a use count, a recharge or a
# number that spends an existing resource. `SUBCLASS_TAIL_2024`: one resource per entry (source kind "subclass");
# `SUBCLASS_NOTES_2024`: a sentence on an EXISTING resource of the class or of the R6 subclass builders (`target` = its
# id). Both appear only under ruleset 2024, when the character's subclass is `subclass`, the XPHB `feature` record is in
# the catalog and the class level has reached that record's level. `uses`: an int or a variable of
# `class_resources._note_vars` (wis_min1, cha_min1, int_min1, zealot_dice, level_plus1); `uses_stages` /
# `recharge_stages` / `vars`: the value of the last listed feature record whose level the class has reached. Note
# templates take the `_note_vars` variables; `extras` (feature id, template) are appended with "; " once that record's
# level is reached. `quotes` are (feature id, verbatim substring of the record's name + desc) pairs pinned by test.
# Paraphrased in the notes, never copied sentences.
SUBCLASS_TAIL_2024: tuple[dict, ...] = (
    # ---- Barbarian
    {"subclass": "berserker-xphb", "class": "barbarian", "feature": "berserker-xphb-14-intimidating-presence",
     "name": "Intimidating Presence", "uses": 1, "recharge": "long",
     "note": "Bonus Action: creatures of your choice in a 30-foot Emanation make a Wisdom saving throw (DC {dc_str}) "
             "or have the Frightened condition for 1 minute; you can restore the use by expending a use of Rage (no "
             "action required)",
     "quotes": (("berserker-xphb-14-intimidating-presence", "DC 8 plus your Strength modifier and Proficiency Bonus"),
                ("berserker-xphb-14-intimidating-presence", "30-foot Emanation"),
                ("berserker-xphb-14-intimidating-presence", "you can't use it again until you finish a Long Rest unless you expend a use of your Rage"))},
    {"subclass": "zealot-xphb", "class": "barbarian", "feature": "zealot-xphb-3-warrior-of-the-gods",
     "name": "Warrior of the Gods", "uses": "zealot_dice", "die": "d12", "recharge": "long",
     "note": "Bonus Action: expend dice from the pool, roll them and regain Hit Points equal to the total",
     "quotes": (("zealot-xphb-3-warrior-of-the-gods", "You have a pool of four d12s that you can spend to heal yourself."),
                ("zealot-xphb-3-warrior-of-the-gods", "regain a number of Hit Points equal to the roll's total"),
                ("zealot-xphb-3-warrior-of-the-gods", "Your pool regains all expended dice when you finish a Long Rest."))},
    {"subclass": "zealot-xphb", "class": "barbarian", "feature": "zealot-xphb-10-zealous-presence",
     "name": "Zealous Presence", "uses": 1, "recharge": "long",
     "note": "Bonus Action: up to ten other creatures within 60 feet gain Advantage on attack rolls and saving throws "
             "until the start of your next turn; you can restore the use by expending a use of Rage (no action required)",
     "quotes": (("zealot-xphb-10-zealous-presence", "Up to ten other creatures of your choice within 60 feet of you gain Advantage on attack rolls and saving throws"),
                ("zealot-xphb-10-zealous-presence", "you can't use it again until you finish a Long Rest unless you expend a use of your Rage"))},
    {"subclass": "zealot-xphb", "class": "barbarian", "feature": "zealot-xphb-14-rage-of-the-gods",
     "name": "Rage of the Gods", "uses": 1, "recharge": "long",
     "note": "When you activate Rage, a divine form for 1 minute: Fly Speed equal to your Speed (hover), Resistance to "
             "Necrotic, Psychic and Radiant damage, and Revivification (Reaction, expend a use of Rage): a creature "
             "within 30 feet about to drop to 0 Hit Points has {level} Hit Points instead (your Barbarian level)",
     "quotes": (("zealot-xphb-14-rage-of-the-gods", "Once you use this feature, you can't do so again until you finish a Long Rest."),
                ("zealot-xphb-14-rage-of-the-gods", "You have Resistance to Necrotic, Psychic, and Radiant damage."),
                ("zealot-xphb-14-rage-of-the-gods", "change the target's Hit Points to a number equal to your Barbarian level"))},
    # ---- Bard
    {"subclass": "glamour-xphb", "class": "bard", "feature": "glamour-xphb-3-beguiling-magic",
     "name": "Beguiling Magic", "uses": 1, "recharge": "long",
     "note": "After you cast an Enchantment or Illusion spell with a spell slot, a creature you can see within 60 feet "
             "makes a Wisdom saving throw against your spell save DC or has the Charmed or Frightened condition (your "
             "choice) for 1 minute; you can restore the use by expending a use of Bardic Inspiration (no action required)",
     "quotes": (("glamour-xphb-3-beguiling-magic", "Once you use this benefit, you can't use it again until you finish a Long Rest."),
                ("glamour-xphb-3-beguiling-magic", "You can also restore your use of it by expending one use of your Bardic Inspiration"),
                ("glamour-xphb-3-beguiling-magic", "Wisdom saving throw against your spell save DC"))},
    {"subclass": "glamour-xphb", "class": "bard", "feature": "glamour-xphb-6-mantle-of-majesty",
     "name": "Mantle of Majesty", "uses": 1, "recharge": "long",
     "note": "Cast Command without a spell slot (Bonus Action) and take an unearthly appearance for 1 minute or until "
             "your Concentration ends, casting Command as a Bonus Action without a slot meanwhile; you can restore the "
             "use by expending a level 3+ spell slot (no action required)",
     "quotes": (("glamour-xphb-6-mantle-of-majesty", "Once you use this feature, you can't use it again until you finish a Long Rest."),
                ("glamour-xphb-6-mantle-of-majesty", "You can also restore your use of it by expending a level 3+ spell slot"))},
    {"subclass": "glamour-xphb", "class": "bard", "feature": "glamour-xphb-14-unbreakable-majesty",
     "name": "Unbreakable Majesty", "uses": 1, "recharge": "short-or-long",
     "note": "Bonus Action, 1 minute: the first time a creature hits you with an attack roll on a turn it makes a "
             "Charisma saving throw against your spell save DC or the attack misses",
     "quotes": (("glamour-xphb-14-unbreakable-majesty", "you can't do so again until you finish a Short or Long Rest"),
                ("glamour-xphb-14-unbreakable-majesty", "must succeed on a Charisma saving throw against your spell save DC"))},
    # ---- Cleric
    {"subclass": "light-xphb", "class": "cleric", "feature": "light-xphb-3-warding-flare",
     "name": "Warding Flare", "uses": "wis_min1", "recharge": "long",
     "recharge_stages": (("light-xphb-6-improved-warding-flare", "short-or-long"),),
     "note": "Reaction: a creature you can see within 30 feet makes an attack roll with Disadvantage",
     "extras": (("light-xphb-6-improved-warding-flare",
                 "Improved Warding Flare: the target of the triggering attack also gains 2d6{wis:+d} Temporary Hit Points"),),
     "quotes": (("light-xphb-3-warding-flare", "impose Disadvantage on the attack roll"),
                ("light-xphb-3-warding-flare", "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)."),
                ("light-xphb-3-warding-flare", "You regain all expended uses when you finish a Long Rest."),
                ("light-xphb-6-improved-warding-flare", "You regain all expended uses of your Warding Flare when you finish a Short or Long Rest."),
                ("light-xphb-6-improved-warding-flare", "2d6 plus your Wisdom modifier"))},
    {"subclass": "light-xphb", "class": "cleric", "feature": "light-xphb-17-corona-of-light",
     "name": "Corona of Light", "uses": "wis_min1", "recharge": "long",
     "note": "Magic action, 1 minute: Bright Light in a 60-foot radius and Dim Light 30 feet beyond; your enemies in "
             "the Bright Light have Disadvantage on saving throws against Radiance of the Dawn and your Fire or "
             "Radiant spells",
     "quotes": (("light-xphb-17-corona-of-light", "Bright Light in a 60-foot radius"),
                ("light-xphb-17-corona-of-light", "have Disadvantage on saving throws against your Radiance of the Dawn"),
                ("light-xphb-17-corona-of-light", "You can use this feature a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest."))},
    {"subclass": "war-xphb", "class": "cleric", "feature": "war-xphb-3-war-priest",
     "name": "War Priest", "uses": "wis_min1", "recharge": "short-or-long",
     "note": "Bonus Action: make one attack with a weapon or an Unarmed Strike",
     "quotes": (("war-xphb-3-war-priest", "you can make one attack with a weapon or an Unarmed Strike"),
                ("war-xphb-3-war-priest", "a number of times equal to your Wisdom modifier (minimum of once)"),
                ("war-xphb-3-war-priest", "You regain all expended uses when you finish a Short or Long Rest."))},
    # ---- Druid
    {"subclass": "moon-xphb", "class": "druid", "feature": "moon-xphb-10-moonlight-step",
     "name": "Moonlight Step", "uses": "wis_min1", "recharge": "long",
     "note": "Bonus Action: teleport up to 30 feet to an unoccupied space you can see and have Advantage on your next "
             "attack roll this turn; you can regain a use by expending a level 2+ spell slot (no action required)",
     "quotes": (("moon-xphb-10-moonlight-step", "you teleport up to 30 feet to an unoccupied space you can see"),
                ("moon-xphb-10-moonlight-step", "a number of times equal to your Wisdom modifier (minimum of once)"),
                ("moon-xphb-10-moonlight-step", "expending a level 2+ spell slot for each use you want to restore"))},
    {"subclass": "stars-xphb", "class": "druid", "feature": "stars-xphb-3-star-map",
     "name": "Star Map", "uses": "wis_min1", "recharge": "long",
     "note": "While holding the map you can cast Guiding Bolt without a spell slot",
     "quotes": (("stars-xphb-3-star-map", "you can cast Guiding Bolt without expending a spell slot"),
                ("stars-xphb-3-star-map", "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "stars-xphb", "class": "druid", "feature": "stars-xphb-6-cosmic-omen",
     "name": "Cosmic Omen", "uses": "wis_min1", "recharge": "long",
     "note": "After a Long Rest roll a die: even is Weal, odd is Woe; Reaction when a creature you can see within 30 "
             "feet is about to make a D20 Test: add (Weal) or subtract (Woe) 1d6",
     "quotes": (("stars-xphb-6-cosmic-omen", "Weal (even)"),
                ("stars-xphb-6-cosmic-omen", "Woe (odd)"),
                ("stars-xphb-6-cosmic-omen", "you can take a Reaction to roll 1d6 and add the number rolled to the total"),
                ("stars-xphb-6-cosmic-omen", "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "land-xphb", "class": "druid", "feature": "land-xphb-6-natural-recovery",
     "name": "Natural Recovery (Circle Spell)", "uses": 1, "recharge": "long",
     "note": "Cast one of your prepared level 1+ Circle Spells without a spell slot",
     "quotes": (("land-xphb-6-natural-recovery", "You can cast one of the level 1+ spells that you have prepared from your Circle Spells feature without expending a spell slot, and you must finish a Long Rest before you do so again."),)},
    {"subclass": "land-xphb", "class": "druid", "feature": "land-xphb-6-natural-recovery",
     "name": "Natural Recovery (Spell Slots)", "uses": 1, "recharge": "long",
     "note": "After a Short Rest recover expended spell slots with a combined level of at most {half_level_up} (half "
             "your Druid level, rounded up), none of level 6+",
     "quotes": (("land-xphb-6-natural-recovery", "combined level that is equal to or less than half your Druid level (round up)"),
                ("land-xphb-6-natural-recovery", "none of them can be level 6+"),
                ("land-xphb-6-natural-recovery", "Once you recover spell slots with this feature, you can't do so again until you finish a Long Rest."))},
    # ---- Fighter
    {"subclass": "battle-master-xphb", "class": "fighter", "feature": "battle-master-xphb-7-know-your-enemy",
     "name": "Know Your Enemy", "uses": 1, "recharge": "long",
     "note": "Bonus Action: learn the Immunities, Resistances and Vulnerabilities of a creature you can see within 30 "
             "feet; you can restore the use by expending one Superiority Die (no action required)",
     "quotes": (("battle-master-xphb-7-know-your-enemy", "you know whether that creature has any Immunities, Resistances, or Vulnerabilities"),
                ("battle-master-xphb-7-know-your-enemy", "you can't do so again until you finish a Long Rest"),
                ("battle-master-xphb-7-know-your-enemy", "restore a use of the feature by expending one Superiority Die"))},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "feature": "psi-warrior-xphb-3-telekinetic-movement",
     "name": "Telekinetic Movement", "uses": 1, "recharge": "short-or-long",
     "note": "Magic action: move a loose object of Large size or smaller or a willing creature other than you, within "
             "30 feet of you, up to 30 feet; you can restore the use by expending a Psionic Energy Die (no action required)",
     "quotes": (("psi-warrior-xphb-3-telekinetic-movement", "choose one target you can see within 30 feet of yourself"),
                ("psi-warrior-xphb-3-telekinetic-movement", "You transport the target up to 30 feet"),
                ("psi-warrior-xphb-3-telekinetic-movement", "you can't do so again until you finish a Short or Long Rest unless you expend a Psionic Energy Die"))},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "feature": "psi-warrior-xphb-7-psi-powered-leap",
     "name": "Psi-Powered Leap", "uses": 1, "recharge": "short-or-long",
     "note": "Bonus Action: Fly Speed equal to twice your Speed until the end of the turn; you can restore the use by "
             "expending a Psionic Energy Die (no action required)",
     "quotes": (("psi-warrior-xphb-7-psi-powered-leap", "you gain a Fly Speed equal to twice your Speed"),
                ("psi-warrior-xphb-7-psi-powered-leap", "you can't do so again until you finish a Short or Long Rest unless you expend a Psionic Energy Die"))},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "feature": "psi-warrior-xphb-15-bulwark-of-force",
     "name": "Bulwark of Force", "uses": "int_min1", "recharge": "long",
     "note": "Bonus Action: up to {int_creatures} within 30 feet of you (you can be one) have Half Cover for 1 minute; "
             "you can restore the use by expending a Psionic Energy Die (no action required)",
     "quotes": (("psi-warrior-xphb-15-bulwark-of-force", "up to a number of creatures equal to your Intelligence modifier (minimum of one creature)"),
                ("psi-warrior-xphb-15-bulwark-of-force", "Half Cover for 1 minute"),
                ("psi-warrior-xphb-15-bulwark-of-force", "you can't do so again until you finish a Long Rest unless you expend a Psionic Energy Die"))},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "feature": "psi-warrior-xphb-18-telekinetic-master",
     "name": "Telekinetic Master", "uses": 1, "recharge": "long",
     "note": "Cast Telekinesis (always prepared) without a spell slot or components, using Intelligence; make one weapon "
             "attack as a Bonus Action each turn you concentrate on it; you can restore the use by expending a "
             "Psionic Energy Die (no action required)",
     "quotes": (("psi-warrior-xphb-18-telekinetic-master", "your spellcasting ability for it is Intelligence"),
                ("psi-warrior-xphb-18-telekinetic-master", "you can make one attack with a weapon as a Bonus Action"),
                ("psi-warrior-xphb-18-telekinetic-master", "you can't do so in this way again until you finish a Long Rest unless you expend a Psionic Energy Die"))},
    # ---- Monk
    {"subclass": "open-hand-xphb", "class": "monk", "feature": "open-hand-xphb-6-wholeness-of-body",
     "name": "Wholeness of Body", "uses": "wis_min1", "recharge": "long",
     "note": "Bonus Action: roll your Martial Arts die and regain that many Hit Points 1{ma_die}{wis:+d} (minimum "
             "1 Hit Point regained)",
     "quotes": (("open-hand-xphb-6-wholeness-of-body", "You regain a number of Hit Points equal to the number rolled plus your Wisdom modifier (minimum of 1 Hit Point regained)"),
                ("open-hand-xphb-6-wholeness-of-body", "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "mercy-xphb", "class": "monk", "feature": "mercy-xphb-11-flurry-of-healing-and-harm",
     "name": "Flurry of Healing and Harm", "uses": "wis_min1", "recharge": "long",
     "note": "With Flurry of Blows, replace each Unarmed Strike with Hand of Healing at no Focus Point cost for the "
             "healing, and use Hand of Harm on a Flurry strike at no Focus Point cost (still once per turn); "
             "{wis_min1} uses in total",
     "quotes": (("mercy-xphb-11-flurry-of-healing-and-harm", "you can replace each of the Unarmed Strikes with a use of Hand of Healing without expending Focus Points for the healing"),
                ("mercy-xphb-11-flurry-of-healing-and-harm", "a total number of times equal to your Wisdom modifier (minimum of once)"),
                ("mercy-xphb-11-flurry-of-healing-and-harm", "You regain all expended uses when you finish a Long Rest."))},
    {"subclass": "mercy-xphb", "class": "monk", "feature": "mercy-xphb-17-hand-of-ultimate-mercy",
     "name": "Hand of Ultimate Mercy", "uses": 1, "recharge": "long",
     "note": "Magic action, expend 5 Focus Points: a creature that died within the past 24 hours returns to life with "
             "4d10{wis:+d} Hit Points and loses Blinded, Deafened, Paralyzed, Poisoned and Stunned",
     "quotes": (("mercy-xphb-17-hand-of-ultimate-mercy", "expend 5 Focus Points"),
                ("mercy-xphb-17-hand-of-ultimate-mercy", "4d10 plus your Wisdom modifier"),
                ("mercy-xphb-17-hand-of-ultimate-mercy", "you can't use it again until you finish a Long Rest"))},
    # ---- Paladin
    {"subclass": "glory-xphb", "class": "paladin", "feature": "glory-xphb-15-glorious-defense",
     "name": "Glorious Defense", "uses": "cha_min1", "recharge": "long",
     "note": "Reaction when you or a creature you can see within 10 feet is hit: +{cha_min1} AC against that attack "
             "(Charisma modifier, minimum +1); if it misses, make one weapon attack against the attacker",
     "quotes": (("glory-xphb-15-glorious-defense", "The bonus equals your Charisma modifier (minimum of +1)."),
                ("glory-xphb-15-glorious-defense", "a number of times equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "glory-xphb", "class": "paladin", "feature": "glory-xphb-20-living-legend",
     "name": "Living Legend", "uses": 1, "recharge": "long",
     "note": "Bonus Action, 10 minutes: Advantage on Charisma checks, Reaction to reroll a failed saving throw, and "
             "once per turn turn a missed weapon attack into a hit; you can restore the use by expending a level 5 "
             "spell slot (no action required)",
     "quotes": (("glory-xphb-20-living-legend", "Once you use this feature, you can't use it again until you finish a Long Rest."),
                ("glory-xphb-20-living-legend", "You can also restore your use of it by expending a level 5 spell slot"),
                ("glory-xphb-20-living-legend", "you can cause that attack to hit instead"))},
    {"subclass": "devotion-xphb", "class": "paladin", "feature": "devotion-xphb-20-holy-nimbus",
     "name": "Holy Nimbus", "uses": 1, "recharge": "long",
     "note": "Bonus Action, 10 minutes: Advantage on saving throws forced by Fiends and Undead, and an enemy that "
             "starts its turn in your aura takes {cha_pb} Radiant damage (Charisma modifier + Proficiency Bonus); you "
             "can restore the use by expending a level 5 spell slot (no action required)",
     "quotes": (("devotion-xphb-20-holy-nimbus", "Radiant damage equal to your Charisma modifier plus your Proficiency Bonus"),
                ("devotion-xphb-20-holy-nimbus", "Once you use this feature, you can't use it again until you finish a Long Rest."),
                ("devotion-xphb-20-holy-nimbus", "You can also restore your use of it by expending a level 5 spell slot"))},
    {"subclass": "ancients-xphb", "class": "paladin", "feature": "ancients-xphb-15-undying-sentinel",
     "name": "Undying Sentinel", "uses": 1, "recharge": "long",
     "note": "When you are reduced to 0 Hit Points and not killed outright, you drop to 1 Hit Point instead and "
             "regain {three_level} Hit Points (3 x Paladin level)",
     "quotes": (("ancients-xphb-15-undying-sentinel", "you regain a number of Hit Points equal to three times your Paladin level"),
                ("ancients-xphb-15-undying-sentinel", "Once you use this feature, you can't do so again until you finish a Long Rest."))},
    {"subclass": "ancients-xphb", "class": "paladin", "feature": "ancients-xphb-20-elder-champion",
     "name": "Elder Champion", "uses": 1, "recharge": "long",
     "note": "Bonus Action, 1 minute: enemies in your aura have Disadvantage on saving throws against your spells and "
             "Channel Divinity options, you regain 10 Hit Points at the start of each of your turns, and spells with "
             "an action casting time can be cast as a Bonus Action; you can restore the use by expending a level 5 "
             "spell slot (no action required)",
     "quotes": (("ancients-xphb-20-elder-champion", "you regain 10 Hit Points"),
                ("ancients-xphb-20-elder-champion", "Once you use this feature, you can't use it again until you finish a Long Rest."),
                ("ancients-xphb-20-elder-champion", "You can also restore your use of it by expending a level 5 spell slot"))},
    {"subclass": "vengeance-xphb", "class": "paladin", "feature": "vengeance-xphb-20-avenging-angel",
     "name": "Avenging Angel", "uses": 1, "recharge": "long",
     "note": "Bonus Action, 10 minutes: Fly Speed of 60 feet (hover), and an enemy that starts its turn in your aura "
             "makes a Wisdom saving throw or is Frightened for 1 minute or until it takes damage; you can restore the "
             "use by expending a level 5 spell slot (no action required)",
     "quotes": (("vengeance-xphb-20-avenging-angel", "have a Fly Speed of 60 feet, and can hover"),
                ("vengeance-xphb-20-avenging-angel", "Once you use this feature, you can't use it again until you finish a Long Rest."),
                ("vengeance-xphb-20-avenging-angel", "You can also restore your use of it by expending a level 5 spell slot"))},
    # ---- Ranger
    {"subclass": "fey-wanderer-xphb", "class": "ranger", "feature": "fey-wanderer-xphb-11-fey-reinforcements",
     "name": "Fey Reinforcements", "uses": 1, "recharge": "long",
     "note": "Cast Summon Fey once without a spell slot and without a Material component; you can make it not "
             "require Concentration, with a duration of 1 minute",
     "quotes": (("fey-wanderer-xphb-11-fey-reinforcements", "You can also cast it once without a spell slot, and you regain the ability to cast it in this way when you finish a Long Rest."),
                ("fey-wanderer-xphb-11-fey-reinforcements", "the spell's duration becomes 1 minute for that casting"))},
    {"subclass": "fey-wanderer-xphb", "class": "ranger", "feature": "fey-wanderer-xphb-15-misty-wanderer",
     "name": "Misty Wanderer", "uses": "wis_min1", "recharge": "long",
     "note": "Cast Misty Step without a spell slot, bringing along one willing creature you can see within 5 feet",
     "quotes": (("fey-wanderer-xphb-15-misty-wanderer", "You can cast Misty Step without expending a spell slot."),
                ("fey-wanderer-xphb-15-misty-wanderer", "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "gloom-stalker-xphb", "class": "ranger", "feature": "gloom-stalker-xphb-3-dread-ambusher",
     "name": "Dread Ambusher", "uses": "wis_min1", "recharge": "long",
     "vars": {"dreadful": ("2d6", (("gloom-stalker-xphb-11-stalkers-flurry", "2d8"),))},
     "note": "Dreadful Strike: once per turn when you hit with a weapon, {dreadful} extra Psychic damage; you also gain "
             "+10 feet of Speed on your first turn of each combat and add your Wisdom modifier ({wis:+d}) to Initiative",
     "quotes": (("gloom-stalker-xphb-3-dread-ambusher", "you can deal an extra 2d6 Psychic damage"),
                ("gloom-stalker-xphb-3-dread-ambusher", "you can use it a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"),
                ("gloom-stalker-xphb-3-dread-ambusher", "your Speed increases by 10 feet until the end of that turn"),
                ("gloom-stalker-xphb-3-dread-ambusher", "you can add your Wisdom modifier to the roll"),
                ("gloom-stalker-xphb-11-stalkers-flurry", "The Psychic damage of your Dreadful Strike becomes 2d8."))},
    # ---- Rogue
    {"subclass": "arcane-trickster-xphb", "class": "rogue", "feature": "arcane-trickster-xphb-17-spell-thief",
     "name": "Spell Thief", "uses": 1, "recharge": "long",
     "note": "Reaction after a creature casts a spell that targets you or includes you in its area: Intelligence saving "
             "throw against your spell save DC; on a failure the spell does nothing to you and you steal it (level 1+, "
             "of a level you can cast) for 8 hours",
     "quotes": (("arcane-trickster-xphb-17-spell-thief", "The DC equals your spell save DC."),
                ("arcane-trickster-xphb-17-spell-thief", "For the next 8 hours, you have the spell prepared."),
                ("arcane-trickster-xphb-17-spell-thief", "Once you steal a spell with this feature, you can't use this feature again until you finish a Long Rest."))},
    {"subclass": "soulknife-xphb", "class": "rogue", "feature": "soulknife-xphb-13-psychic-veil",
     "name": "Psychic Veil", "uses": 1, "recharge": "long",
     "note": "Magic action: the Invisible condition for 1 hour, ending early after you deal damage or force a saving "
             "throw; you can restore the use by expending a Psionic Energy Die (no action required)",
     "quotes": (("soulknife-xphb-13-psychic-veil", "you gain the Invisible condition for 1 hour"),
                ("soulknife-xphb-13-psychic-veil", "you can't do so again until you finish a Long Rest unless you expend a Psionic Energy Die"))},
    {"subclass": "soulknife-xphb", "class": "rogue", "feature": "soulknife-xphb-17-rend-mind",
     "name": "Rend Mind", "uses": 1, "recharge": "long",
     "note": "When Psychic Blades deal Sneak Attack damage, the target makes a Wisdom saving throw (DC {dc_dex}) or has "
             "the Stunned condition for 1 minute (repeating the save each turn); you can restore the use by expending "
             "three Psionic Energy Dice (no action required)",
     "quotes": (("soulknife-xphb-17-rend-mind", "Wisdom saving throw (DC 8 plus your Dexterity modifier and Proficiency Bonus)"),
                ("soulknife-xphb-17-rend-mind", "has the Stunned condition for 1 minute"),
                ("soulknife-xphb-17-rend-mind", "you can't do so again until you finish a Long Rest unless you expend three Psionic Energy Dice"))},
    # ---- Sorcerer
    {"subclass": "clockwork-xphb", "class": "sorcerer", "feature": "clockwork-xphb-3-restore-balance",
     "name": "Restore Balance", "uses": "cha_min1", "recharge": "long",
     "note": "Reaction: a creature you can see within 60 feet about to roll a d20 with Advantage or Disadvantage rolls "
             "it without either",
     "quotes": (("clockwork-xphb-3-restore-balance", "prevent the roll from being affected by Advantage and Disadvantage"),
                ("clockwork-xphb-3-restore-balance", "a number of times equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a Long Rest"))},
    {"subclass": "clockwork-xphb", "class": "sorcerer", "feature": "clockwork-xphb-14-trance-of-order",
     "name": "Trance of Order", "uses": 1, "recharge": "long",
     "note": "Bonus Action, 1 minute: attack rolls against you can't benefit from Advantage and you treat a d20 roll of "
             "9 or lower as a 10 on your D20 Tests; you can restore the use by spending 5 Sorcery Points (no action required)",
     "quotes": (("clockwork-xphb-14-trance-of-order", "treat a roll of 9 or lower on the d20 as a 10"),
                ("clockwork-xphb-14-trance-of-order", "you can't use it again until you finish a Long Rest unless you spend 5 Sorcery Points"))},
    {"subclass": "clockwork-xphb", "class": "sorcerer", "feature": "clockwork-xphb-18-clockwork-cavalcade",
     "name": "Clockwork Cavalcade", "uses": 1, "recharge": "long",
     "note": "Magic action, 30-foot Cube: restore up to 100 Hit Points divided among creatures of your choice, repair "
             "damaged objects and end spells of level 6 and lower; you can restore the use by spending 7 Sorcery Points",
     "quotes": (("clockwork-xphb-18-clockwork-cavalcade", "The spirits restore up to 100 Hit Points"),
                ("clockwork-xphb-18-clockwork-cavalcade", "Every spell of level 6 and lower ends"),
                ("clockwork-xphb-18-clockwork-cavalcade", "you can't use it again until you finish a Long Rest unless you spend 7 Sorcery Points"))},
    {"subclass": "aberrant-xphb", "class": "sorcerer", "feature": "aberrant-xphb-18-warping-implosion",
     "name": "Warping Implosion", "uses": 1, "recharge": "long",
     "note": "Magic action: teleport up to 120 feet; each creature within 30 feet of the space you left makes a "
             "Strength saving throw against your spell save DC or takes 3d10 Force damage and is pulled toward it "
             "(half damage on a success); you can restore the use by spending 5 Sorcery Points",
     "quotes": (("aberrant-xphb-18-warping-implosion", "you teleport to an unoccupied space you can see within 120 feet of yourself"),
                ("aberrant-xphb-18-warping-implosion", "a creature takes 3d10 Force damage"),
                ("aberrant-xphb-18-warping-implosion", "you can't do so again until you finish a Long Rest unless you spend 5 Sorcery Points"))},
    {"subclass": "draconic-xphb", "class": "sorcerer", "feature": "draconic-xphb-14-dragon-wings",
     "name": "Dragon Wings", "uses": 1, "recharge": "long",
     "note": "Bonus Action: wings for 1 hour give you a Fly Speed of 60 feet; you can restore the use by spending 3 "
             "Sorcery Points (no action required)",
     "quotes": (("draconic-xphb-14-dragon-wings", "you have a Fly Speed of 60 feet"),
                ("draconic-xphb-14-dragon-wings", "you can't use it again until you finish a Long Rest unless you spend 3 Sorcery Points"))},
    {"subclass": "draconic-xphb", "class": "sorcerer", "feature": "draconic-xphb-18-dragon-companion",
     "name": "Dragon Companion", "uses": 1, "recharge": "long",
     "note": "Cast Summon Dragon once without a spell slot and without a Material component; you can make it not "
             "require Concentration, with a duration of 1 minute",
     "quotes": (("draconic-xphb-18-dragon-companion", "You can also cast it once without a spell slot, and you regain the ability to cast it in this way when you finish a Long Rest."),
                ("draconic-xphb-18-dragon-companion", "the spell's duration becomes 1 minute for that casting"))},
    {"subclass": "wild-magic-xphb", "class": "sorcerer", "feature": "wild-magic-xphb-3-tides-of-chaos",
     "name": "Tides of Chaos", "uses": 1, "recharge": "long",
     "note": "Advantage on one D20 Test before you roll; you regain the use after a Long Rest or when you cast a "
             "Sorcerer spell with a spell slot (then you roll on the Wild Magic Surge table)",
     "quotes": (("wild-magic-xphb-3-tides-of-chaos", "give yourself Advantage on one D20 Test before you roll the d20"),
                ("wild-magic-xphb-3-tides-of-chaos", "you must cast a Sorcerer spell with a spell slot or finish a Long Rest before you can use this feature again"))},
    {"subclass": "wild-magic-xphb", "class": "sorcerer", "feature": "wild-magic-xphb-18-tamed-surge",
     "name": "Tamed Surge", "uses": 1, "recharge": "long",
     "note": "After you cast a Sorcerer spell with a spell slot, choose an effect from the Wild Magic Surge table (not "
             "the final row) instead of rolling",
     "quotes": (("wild-magic-xphb-18-tamed-surge", "you can create an effect of your choice from the Wild Magic Surge table instead of rolling on that table"),
                ("wild-magic-xphb-18-tamed-surge", "Once you use this feature, you can't do so again until you finish a Long Rest."))},
    # ---- Warlock
    {"subclass": "archfey-xphb", "class": "warlock", "feature": "archfey-xphb-3-steps-of-the-fey",
     "name": "Steps of the Fey", "uses": "cha_min1", "recharge": "long",
     "note": "Cast Misty Step without a spell slot, adding Refreshing Step (1d10 Temporary Hit Points to you or a "
             "creature within 10 feet) or Taunting Step (Wisdom saving throw against your spell save DC)",
     "quotes": (("archfey-xphb-3-steps-of-the-fey", "You can cast Misty Step without expending a spell slot a number of times equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a Long Rest."),
                ("archfey-xphb-3-steps-of-the-fey", "gains 1d10 Temporary Hit Points"),
                ("archfey-xphb-3-steps-of-the-fey", "Wisdom saving throw against your spell save DC"))},
    {"subclass": "archfey-xphb", "class": "warlock", "feature": "archfey-xphb-10-beguiling-defenses",
     "name": "Beguiling Defenses", "uses": 1, "recharge": "long",
     "note": "Reaction after a creature hits you: halve the damage you take, and the attacker makes a Wisdom saving "
             "throw against your spell save DC or takes Psychic damage equal to the damage you take; you can restore "
             "the use by expending a Pact Magic slot (no action required)",
     "quotes": (("archfey-xphb-10-beguiling-defenses", "reduce the damage you take by half (round down)"),
                ("archfey-xphb-10-beguiling-defenses", "you can't use it again until you finish a Long Rest unless you expend a Pact Magic spell slot"))},
    {"subclass": "celestial-xphb", "class": "warlock", "feature": "celestial-xphb-3-healing-light",
     "name": "Healing Light", "uses": "level_plus1", "die": "d6", "recharge": "long",
     "note": "Bonus Action: heal yourself or a creature you can see within 60 feet by expending dice from the pool, "
             "at most {cha_dice} at once (Charisma modifier, minimum 1); restore Hit Points equal to the total",
     "quotes": (("celestial-xphb-3-healing-light", "The number of dice in the pool equals 1 plus your Warlock level."),
                ("celestial-xphb-3-healing-light", "The maximum number of dice you can expend at once equals your Charisma modifier (minimum of one die)."),
                ("celestial-xphb-3-healing-light", "Your pool regains all expended dice when you finish a Long Rest."))},
    {"subclass": "celestial-xphb", "class": "warlock", "feature": "celestial-xphb-14-searing-vengeance",
     "name": "Searing Vengeance", "uses": 1, "recharge": "long",
     "note": "When you or an ally within 60 feet is about to make a Death Saving Throw, that creature regains half its "
             "Hit Point maximum and can end Prone; creatures of your choice within 30 feet take 2d8{cha:+d} Radiant "
             "damage and are Blinded until the end of the turn",
     "quotes": (("celestial-xphb-14-searing-vengeance", "regains Hit Points equal to half its Hit Point maximum"),
                ("celestial-xphb-14-searing-vengeance", "Radiant damage equal to 2d8 plus your Charisma modifier"),
                ("celestial-xphb-14-searing-vengeance", "Once you use this feature, you can't use it again until you finish a Long Rest."))},
    {"subclass": "fiend-xphb", "class": "warlock", "feature": "fiend-xphb-6-dark-ones-own-luck",
     "name": "Dark One's Own Luck", "uses": "cha_min1", "recharge": "long",
     "note": "Add 1d10 to an ability check or saving throw after seeing the roll (once per roll)",
     "quotes": (("fiend-xphb-6-dark-ones-own-luck", "you can use this feature to add 1d10 to your roll"),
                ("fiend-xphb-6-dark-ones-own-luck", "a number of times equal to your Charisma modifier (minimum of once), but you can use it no more than once per roll"),
                ("fiend-xphb-6-dark-ones-own-luck", "You regain all expended uses when you finish a Long Rest."))},
    {"subclass": "fiend-xphb", "class": "warlock", "feature": "fiend-xphb-14-hurl-through-hell",
     "name": "Hurl Through Hell", "uses": 1, "recharge": "long",
     "note": "Once per turn on an attack hit: the target makes a Charisma saving throw against your spell save DC or is "
             "hurled through the Lower Planes, taking 8d10 Psychic damage (not a Fiend) and Incapacitated until the end "
             "of your next turn; you can restore the use by expending a Pact Magic slot (no action required)",
     "quotes": (("fiend-xphb-14-hurl-through-hell", "The target takes 8d10 Psychic damage if it isn't a Fiend"),
                ("fiend-xphb-14-hurl-through-hell", "Charisma saving throw against your spell save DC"),
                ("fiend-xphb-14-hurl-through-hell", "you can't use it again until you finish a Long Rest unless you expend a Pact Magic spell slot"))},
    {"subclass": "great-old-one-xphb", "class": "warlock", "feature": "great-old-one-xphb-6-clairvoyant-combatant",
     "name": "Clairvoyant Combatant", "uses": 1, "recharge": "short-or-long",
     "note": "When you form an Awakened Mind bond, the creature makes a Wisdom saving throw against your spell save DC "
             "or has Disadvantage on attack rolls against you while you have Advantage against it for the bond; you "
             "can restore the use by expending a Pact Magic slot (no action required)",
     "quotes": (("great-old-one-xphb-6-clairvoyant-combatant", "Wisdom saving throw against your spell save DC"),
                ("great-old-one-xphb-6-clairvoyant-combatant", "you can't use it again until you finish a Short or Long Rest unless you expend a Pact Magic spell slot"))},
    # ---- Wizard
    {"subclass": "abjurer-xphb", "class": "wizard", "feature": "abjurer-xphb-3-arcane-ward",
     "name": "Arcane Ward", "uses": 1, "recharge": "long",
     "note": "When you cast an Abjuration spell with a spell slot you can create a ward with a Hit Point maximum of "
             "{ward_hp} Hit Points (twice your Wizard level + Intelligence modifier) that lasts until a Long Rest and "
             "takes your damage instead; it regains twice the level of the slot you spend",
     "quotes": (("abjurer-xphb-3-arcane-ward", "The ward has a Hit Point maximum equal to twice your Wizard level plus your Intelligence modifier."),
                ("abjurer-xphb-3-arcane-ward", "the ward regains a number of Hit Points equal to twice the level of the spell slot"),
                ("abjurer-xphb-3-arcane-ward", "Once you create the ward, you can't create it again until you finish a Long Rest."))},
    {"subclass": "diviner-xphb", "class": "wizard", "feature": "diviner-xphb-3-portent",
     "name": "Portent", "uses": 2, "die": "d20", "recharge": "long",
     "uses_stages": (("diviner-xphb-14-greater-portent", 3),),
     "note": "After a Long Rest roll the d20s and record them; once per turn replace a D20 Test made by you or a "
             "creature you can see with one (declare before the roll); unused rolls are lost at your next Long Rest",
     "quotes": (("diviner-xphb-3-portent", "roll two d20s and record the numbers rolled"),
                ("diviner-xphb-3-portent", "Each foretelling roll can be used only once."),
                ("diviner-xphb-14-greater-portent", "Roll three d20s for your Portent feature rather than two."))},
    {"subclass": "diviner-xphb", "class": "wizard", "feature": "diviner-xphb-10-the-third-eye",
     "name": "The Third Eye", "uses": 1, "recharge": "short-or-long",
     "note": "Bonus Action, until a Short or Long Rest: choose Darkvision 120 feet, reading any language, or See "
             "Invisibility without a spell slot",
     "quotes": (("diviner-xphb-10-the-third-eye", "You can't use this feature again until you finish a Short or Long Rest."),
                ("diviner-xphb-10-the-third-eye", "Darkvision. You gain Darkvision with a range of 120 feet."))},
    {"subclass": "illusionist-xphb", "class": "wizard", "feature": "illusionist-xphb-6-phantasmal-creatures",
     "name": "Phantasmal Creatures", "uses": 2, "recharge": "long",
     "note": "Summon Beast and Summon Fey are always prepared; cast each once per Long Rest without a spell slot as an "
             "Illusion (the creature has half its Hit Points)",
     "quotes": (("illusionist-xphb-6-phantasmal-creatures", "You always have the Summon Beast and Summon Fey spells prepared."),
                ("illusionist-xphb-6-phantasmal-creatures", "casting it without a slot halves the creature's Hit Points"),
                ("illusionist-xphb-6-phantasmal-creatures", "you must finish a Long Rest before you can cast the spell in that way again"))},
    {"subclass": "illusionist-xphb", "class": "wizard", "feature": "illusionist-xphb-10-illusory-self",
     "name": "Illusory Self", "uses": 1, "recharge": "short-or-long",
     "note": "Reaction when a creature hits you with an attack roll: the attack automatically misses; you can restore "
             "the use by expending a level 2+ spell slot (no action required)",
     "quotes": (("illusionist-xphb-10-illusory-self", "The attack automatically misses you"),
                ("illusionist-xphb-10-illusory-self", "you can't use it again until you finish a Short or Long Rest"),
                ("illusionist-xphb-10-illusory-self", "expending a level 2+ spell slot"))},
)

SUBCLASS_NOTES_2024: tuple[dict, ...] = (
    {"subclass": "glamour-xphb", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "glamour-xphb-3-mantle-of-inspiration", "name": "Mantle of Inspiration",
     "note": "Mantle of Inspiration (Bonus Action, expend a use): up to {cha_creatures} within 60 feet gain Temporary "
             "Hit Points equal to twice the Bardic Inspiration die roll and can move up to their Speed as a Reaction",
     "quotes": (("glamour-xphb-3-mantle-of-inspiration", "up to a number equal to your Charisma modifier (minimum of one creature)"),
                ("glamour-xphb-3-mantle-of-inspiration", "Temporary Hit Points equal to two times the number rolled on the Bardic Inspiration die"))},
    {"subclass": "life-xphb", "class": "cleric", "target": "cleric:channel-divinity",
     "feature": "life-xphb-3-preserve-life", "name": "Preserve Life",
     "note": "Preserve Life (Magic action): restore up to {five_level} Hit Points (5 x Cleric level) divided among "
             "Bloodied creatures within 30 feet, none above half its Hit Point maximum",
     "quotes": (("life-xphb-3-preserve-life", "equal to five times your Cleric level"),
                ("life-xphb-3-preserve-life", "no more than half its Hit Point maximum"))},
    {"subclass": "light-xphb", "class": "cleric", "target": "cleric:channel-divinity",
     "feature": "light-xphb-3-radiance-of-the-dawn", "name": "Radiance of the Dawn",
     "note": "Radiance of the Dawn (Magic action, 30-foot Emanation): dispels magical Darkness; creatures of your "
             "choice make a Constitution saving throw or take 2d10 + {level} Radiant damage (half on a success)",
     "quotes": (("light-xphb-3-radiance-of-the-dawn", "Radiant damage equal to 2d10 plus your Cleric level on a failed save"),
                ("light-xphb-3-radiance-of-the-dawn", "30-foot Emanation"))},
    {"subclass": "war-xphb", "class": "cleric", "target": "cleric:channel-divinity",
     "feature": "war-xphb-3-guided-strike", "name": "Guided Strike",
     "note": "Guided Strike: when you or a creature within 30 feet misses an attack roll, expend a use to give that "
             "roll a +10 bonus (a Reaction for another creature's roll)",
     "quotes": (("war-xphb-3-guided-strike", "give that roll a +10 bonus"),
                ("war-xphb-3-guided-strike", "you must take a Reaction to do so"))},
    {"subclass": "moon-xphb", "class": "druid", "target": "druid:wild-shape",
     "feature": "moon-xphb-3-circle-forms", "name": "Circle Forms",
     "note": "Circle Forms: the form's maximum CR is {third_level} (Druid level / 3, rounded down), its AC is 13 + WIS "
             "({moon_ac}) if higher than the Beast's, and you gain {three_level} Temporary Hit Points (3 x Druid level)",
     "quotes": (("moon-xphb-3-circle-forms", "equals your Druid level divided by 3 (round down)"),
                ("moon-xphb-3-circle-forms", "your AC equals 13 plus your Wisdom modifier if that total is higher than the Beast's AC"),
                ("moon-xphb-3-circle-forms", "a number of Temporary Hit Points equal to three times your Druid level"))},
    {"subclass": "land-xphb", "class": "druid", "target": "druid:wild-shape",
     "feature": "land-xphb-3-lands-aid", "name": "Land's Aid",
     "note": "Land's Aid (Magic action, expend a use): creatures of your choice in a 10-foot-radius Sphere within 60 "
             "feet make a Constitution saving throw against your spell save DC or take {lands_aid}d6 Necrotic damage "
             "(half on a success), and one creature in it regains {lands_aid}d6 Hit Points",
     "quotes": (("land-xphb-3-lands-aid", "taking 2d6 Necrotic damage on a failed save or half as much damage on a successful one"),
                ("land-xphb-3-lands-aid", "regains 2d6 Hit Points"),
                ("land-xphb-3-lands-aid", "The damage and healing increase by 1d6 when you reach Druid levels 10 (3d6) and 14 (4d6)."))},
    {"subclass": "sea-xphb", "class": "druid", "target": "druid:wild-shape",
     "feature": "sea-xphb-3-wrath-of-the-sea", "name": "Wrath of the Sea",
     "note": "Wrath of the Sea (Bonus Action, expend a use, 10 minutes): a 5-foot Emanation; a creature you choose in "
             "it makes a Constitution saving throw against your spell save DC or takes {wis_min1}d6 Cold damage "
             "(Wisdom modifier, minimum 1 die) and, if Large or smaller, is pushed up to 15 feet",
     "quotes": (("sea-xphb-3-wrath-of-the-sea", "5-foot Emanation"),
                ("sea-xphb-3-wrath-of-the-sea", "roll a number of d6s equal to your Wisdom modifier (minimum of one die)"),
                ("sea-xphb-3-wrath-of-the-sea", "be pushed up to 15 feet away from you"))},
    {"subclass": "battle-master-xphb", "class": "fighter", "target": "fighter:superiority-dice",
     "feature": "battle-master-xphb-15-relentless", "name": "Relentless",
     "note": "Relentless: once per turn, when you use a maneuver, you can roll 1d8 and use that number instead of "
             "expending a Superiority Die",
     "quotes": (("battle-master-xphb-15-relentless", "Once per turn, when you use a maneuver, you can roll 1d8 and use the number rolled instead of expending a Superiority Die."),)},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "target": "fighter:psionic-energy-dice",
     "feature": "psi-warrior-xphb-3-protective-field", "name": "Protective Field",
     "note": "Protective Field (Reaction, expend a die): reduce the damage to you or a creature within 30 feet by the "
             "roll {int:+d} (Intelligence modifier), minimum reduction 1",
     "quotes": (("psi-warrior-xphb-3-protective-field", "reduce the damage taken by the number rolled plus your Intelligence modifier (minimum reduction of 1)"),)},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "target": "fighter:psionic-energy-dice",
     "feature": "psi-warrior-xphb-3-psionic-strike", "name": "Psionic Strike",
     "note": "Psionic Strike (once per turn after a weapon hit within 30 feet, expend a die): Force damage equal to "
             "the roll {int:+d} (Intelligence modifier)",
     "quotes": (("psi-warrior-xphb-3-psionic-strike", "dealing Force damage to the target equal to the number rolled plus your Intelligence modifier"),)},
    {"subclass": "psi-warrior-xphb", "class": "fighter", "target": "fighter:psionic-energy-dice",
     "feature": "psi-warrior-xphb-7-telekinetic-thrust", "name": "Telekinetic Thrust",
     "note": "Telekinetic Thrust (on Psionic Strike damage): Strength saving throw (DC {dc_int}) or Prone or moved up "
             "to 10 feet horizontally",
     "quotes": (("psi-warrior-xphb-7-telekinetic-thrust", "Strength saving throw (DC 8 plus your Intelligence modifier and Proficiency Bonus)"),
                ("psi-warrior-xphb-7-telekinetic-thrust", "transport it up to 10 feet horizontally"))},
    {"subclass": "soulknife-xphb", "class": "rogue", "target": "rogue:psionic-energy-dice",
     "feature": "soulknife-xphb-3-psychic-whispers", "name": "Psychic Whispers",
     "note": "Psychic Whispers (Magic action): up to {pb} creatures (Proficiency Bonus) can speak telepathically with "
             "you for hours equal to a Psionic Energy Die roll; the first use after a Long Rest doesn't expend the die",
     "quotes": (("soulknife-xphb-3-psychic-whispers", "up to a number of creatures equal to your Proficiency Bonus"),
                ("soulknife-xphb-3-psychic-whispers", "For a number of hours equal to the number rolled"),
                ("soulknife-xphb-3-psionic-power", "The first time you use this power after each Long Rest, you don't expend the Psionic Energy Die."))},
    {"subclass": "soulknife-xphb", "class": "rogue", "target": "rogue:psionic-energy-dice",
     "feature": "soulknife-xphb-9-psychic-teleportation", "name": "Psychic Teleportation",
     "note": "Psychic Teleportation (Bonus Action, expend a die): throw the Psychic Blade up to 10 times the roll in "
             "feet and teleport to that space",
     "quotes": (("soulknife-xphb-9-psychic-teleportation", "up to a number of feet away equal to 10 times the number rolled"),)},
    {"subclass": "mercy-xphb", "class": "monk", "target": "monk:focus-points",
     "feature": "mercy-xphb-3-hand-of-harm", "name": "Hand of Harm",
     "note": "Hand of Harm (1 Focus Point, once per turn on an Unarmed Strike hit): extra Necrotic damage 1{ma_die}{wis:+d}",
     "quotes": (("mercy-xphb-3-hand-of-harm", "you can expend 1 Focus Point to deal extra Necrotic damage equal to one roll of your Martial Arts die plus your Wisdom modifier"),)},
    {"subclass": "mercy-xphb", "class": "monk", "target": "monk:focus-points",
     "feature": "mercy-xphb-3-hand-of-healing", "name": "Hand of Healing",
     "note": "Hand of Healing (Magic action, 1 Focus Point): restore 1{ma_die}{wis:+d} Hit Points; no Focus Point "
             "cost when it replaces a Flurry of Blows strike",
     "quotes": (("mercy-xphb-3-hand-of-healing", "restore a number of Hit Points equal to a roll of your Martial Arts die plus your Wisdom modifier"),
                ("mercy-xphb-3-hand-of-healing", "replace one of the Unarmed Strikes with a use of this feature without expending a Focus Point for the healing"))},
    {"subclass": "open-hand-xphb", "class": "monk", "target": "monk:focus-points",
     "feature": "open-hand-xphb-17-quivering-palm", "name": "Quivering Palm",
     "note": "Quivering Palm (4 Focus Points on an Unarmed Strike hit): vibrations last {level} days (Monk level); "
             "ending them forces a Constitution saving throw, 10d12 Force damage on a failure, half on a success",
     "quotes": (("open-hand-xphb-17-quivering-palm", "you can expend 4 Focus Points to start these imperceptible vibrations"),
                ("open-hand-xphb-17-quivering-palm", "which last for a number of days equal to your Monk level"),
                ("open-hand-xphb-17-quivering-palm", "taking 10d12 Force damage on a failed save or half as much damage on a successful one"))},
    {"subclass": "elements-xphb", "class": "monk", "target": "monk:focus-points",
     "feature": "elements-xphb-6-elemental-burst", "name": "Elemental Burst",
     "note": "Elemental Burst (Magic action, 2 Focus Points): 20-foot-radius Sphere within 120 feet, Dexterity saving "
             "throw, 3{ma_die} damage of a chosen elemental type (half on a success)",
     "quotes": (("elements-xphb-6-elemental-burst", "you can expend 2 Focus Points"),
                ("elements-xphb-6-elemental-burst", "damage of the chosen type equal to three rolls of your Martial Arts die"))},
    {"subclass": "shadow-xphb", "class": "monk", "target": "monk:focus-points",
     "feature": "shadow-xphb-17-cloak-of-shadows", "name": "Cloak of Shadows",
     "note": "Cloak of Shadows (Magic action in Dim Light or Darkness, 3 Focus Points): Invisible for 1 minute, move "
             "through occupied spaces, and Flurry of Blows costs no Focus Points",
     "quotes": (("shadow-xphb-17-cloak-of-shadows", "you can expend 3 Focus Points to shroud yourself with shadows for 1 minute"),
                ("shadow-xphb-17-cloak-of-shadows", "You can use your Flurry of Blows without expending any Focus Points."))},
    {"subclass": "devotion-xphb", "class": "paladin", "target": "paladin:channel-divinity",
     "feature": "devotion-xphb-3-sacred-weapon", "name": "Sacred Weapon",
     "note": "Sacred Weapon (Attack action, expend a use, 10 minutes): add +{cha_min1} (Charisma modifier, minimum +1) "
             "to attack rolls with the imbued Melee weapon, which can deal Radiant damage",
     "quotes": (("devotion-xphb-3-sacred-weapon", "you add your Charisma modifier to attack rolls you make with that weapon (minimum bonus of +1)"),
                ("devotion-xphb-3-sacred-weapon", "For 10 minutes or until you use this feature again"))},
    {"subclass": "glory-xphb", "class": "paladin", "target": "paladin:channel-divinity",
     "feature": "glory-xphb-3-inspiring-smite", "name": "Inspiring Smite",
     "note": "Inspiring Smite (after Divine Smite, expend a use): distribute 2d8 + {level} Temporary Hit Points (Paladin "
             "level) among creatures within 30 feet",
     "quotes": (("glory-xphb-3-inspiring-smite", "The total number of Temporary Hit Points equals 2d8 plus your Paladin level"),)},
    {"subclass": "clockwork-xphb", "class": "sorcerer", "target": "sorcerer:sorcery-points",
     "feature": "clockwork-xphb-6-bastion-of-law", "name": "Bastion of Law",
     "note": "Bastion of Law (Magic action): spend 1 to 5 Sorcery Points to ward yourself or a creature within 30 feet "
             "with that many d8s, which reduce the damage it takes (lasts until a Long Rest)",
     "quotes": (("clockwork-xphb-6-bastion-of-law", "you can expend 1 to 5 Sorcery Points"),
                ("clockwork-xphb-6-bastion-of-law", "a number of d8s equal to the number of Sorcery Points spent"))},
    {"subclass": "wild-magic-xphb", "class": "sorcerer", "target": "sorcerer:sorcery-points",
     "feature": "wild-magic-xphb-6-bend-luck", "name": "Bend Luck",
     "note": "Bend Luck (Reaction, 1 Sorcery Point): after another creature rolls the d20 of a D20 Test, apply 1d4 as a "
             "bonus or penalty (your choice)",
     "quotes": (("wild-magic-xphb-6-bend-luck", "spend 1 Sorcery Point to roll 1d4 and apply the number rolled as a bonus or penalty"),)},
    {"subclass": "aberrant-xphb", "class": "sorcerer", "target": "sorcerer:sorcery-points",
     "feature": "aberrant-xphb-6-psionic-sorcery", "name": "Psionic Sorcery",
     "note": "Psionic Sorcery: cast a level 1+ Psionic Spell by spending Sorcery Points equal to the spell's level "
             "instead of a spell slot (no Verbal or Somatic components)",
     "quotes": (("aberrant-xphb-6-psionic-sorcery", "by spending a number of Sorcery Points equal to the spell's level"),
                ("aberrant-xphb-6-psionic-sorcery", "it requires no Verbal or Somatic components"))},
)

# ---- W6 (finding F4): the 2014 (SRD) class-feature use-limit tail. The counterpart of RESOURCE_TAIL_2024 /
# RESOURCE_NOTES_2024 for rulesets "mixed" and "2014": SRD class features (2014 API ids) whose text gives a use count,
# a rest rule or a number the sheet can compute. `class_resources._tail_2014` builds one resource per entry when the SRD
# feature record `feature` is in the catalog and the class level has reached that record's level; nothing under ruleset
# "2024". Spec keys: `class`, `feature`, `name`, optional `uses` / `recharge` / `die` / `dice` / `pool` (a literal, an
# "@name" variable of `class_resources._note_vars` / `vars` / `level_vars`, or a staged tuple (default, ((feature id,
# value), ...)): the value of the last listed record whose level the class has reached), `note` (template over the same
# variables), `vars` (name -> (default, stages)), `level_vars` (name -> ((class level, value), ...) for tables that live
# only in the text; each is pinned by test), `extras` ((feature id, template) appended with "; "
# once that record's level is reached) and `quotes` ((feature id, verbatim substring of name + desc) pinned by test).
# Notes are paraphrases carrying the character's computed numbers. `uses: None` and `recharge: None` = note only (the
# text has no use count or rest rule).
RESOURCE_TAIL_2014: tuple[dict, ...] = (
    # Brutal Critical: "you can roll one additional weapon damage die when determining the extra damage for a critical
    # hit with a melee attack. This increases to two additional dice at 13th level and three additional dice at 17th
    # level."
    {"class": "barbarian", "feature": "brutal-critical-1-die", "name": "Brutal Critical", "uses": None, "recharge": None,
     "vars": {"crit_extra": ("one additional weapon damage die", (
         ("brutal-critical-2-dice", "two additional weapon damage dice"),
         ("brutal-critical-3-dice", "three additional weapon damage dice")))},
     "note": "On a critical hit with a melee attack, roll {crit_extra} for the extra damage",
     "quotes": (("brutal-critical-1-die", "you can roll one additional weapon damage die when determining the extra damage for a critical hit with a melee attack"),
                ("brutal-critical-1-die", "This increases to two additional dice at 13th level and three additional dice at 17th level."))},
    # Relentless Rage: "If you drop to 0 hit points while you're raging and don't die outright, you can make a DC 10
    # Constitution saving throw. If you succeed, you drop to 1 hit point instead. Each time you use this feature after
    # the first, the DC increases by 5. When you finish a short or long rest, the DC resets to 10."
    {"class": "barbarian", "feature": "relentless-rage", "name": "Relentless Rage", "uses": None, "recharge": None,
     "note": "If you drop to 0 hit points while raging and don't die outright, make a DC 10 Constitution saving throw; "
             "on a success you drop to 1 hit point instead. Each use after the first raises the DC by 5 (+5); a short "
             "or long rest resets to 10",
     "quotes": (("relentless-rage", "you can make a DC 10 Constitution saving throw. If you succeed, you drop to 1 hit point instead."),
                ("relentless-rage", "Each time you use this feature after the first, the DC increases by 5. When you finish a short or long rest, the DC resets to 10."))},
    # Song of Rest: "each of those creatures regains an extra 1d6 hit points. The extra hit points increase when you
    # reach certain levels in this class: to 1d8 at 9th level, to 1d10 at 13th level, and to 1d12 at 17th level."
    {"class": "bard", "feature": "song-of-rest-d6", "name": "Song of Rest", "uses": None, "recharge": None,
     "die": "@rest_die",
     "vars": {"rest_die": ("d6", (("song-of-rest-d8", "d8"), ("song-of-rest-d10", "d10"), ("song-of-rest-d12", "d12")))},
     "note": "During a short rest, you and friendly creatures who hear your performance and spend Hit Dice regain an "
             "extra 1{rest_die} hit points",
     "quotes": (("song-of-rest-d6", "regain hit points at the end of the short rest by spending one or more Hit Dice, each of those creatures regains an extra 1d6 hit points"),
                ("song-of-rest-d6", "to 1d8 at 9th level, to 1d10 at 13th level, and to 1d12 at 17th level"))},
    # Divine Intervention: "roll percentile dice. If you roll a number equal to or lower than your cleric level, your
    # deity intervenes. ... If your deity intervenes, you can't use this feature again for 7 days. Otherwise, you can use
    # it again after you finish a long rest. At 20th level, your call for intervention succeeds automatically, no roll
    # required."
    {"class": "cleric", "feature": "divine-intervention", "name": "Divine Intervention", "uses": 1, "recharge": "long",
     "note": "Action: roll percentile dice; your deity intervenes on a roll of {level} or lower (your Cleric level), "
             "after which you can't use this again for 7 days; otherwise you can use it again after a long rest",
     "extras": (("divine-intervention-improvement", "your call for intervention succeeds automatically, no roll required"),),
     "quotes": (("divine-intervention", "roll percentile dice. If you roll a number equal to or lower than your cleric level, your deity intervenes"),
                ("divine-intervention", "If your deity intervenes, you can't use this feature again for 7 days. Otherwise, you can use it again after you finish a long rest."),
                ("divine-intervention-improvement", "your call for intervention succeeds automatically, no roll required"))},
    # Deflect Missiles: "the damage you take from the attack is reduced by 1d10 + your Dexterity modifier + your monk
    # level. ... you can spend 1 ki point to make a ranged attack with the weapon or piece of ammunition you just caught,
    # ... a normal range of 20 feet and a long range of 60 feet."
    {"class": "monk", "feature": "deflect-missiles", "name": "Deflect Missiles", "uses": None, "recharge": None,
     "note": "Reaction when a ranged weapon attack hits you: reduce the damage by 1d10{dex_level:+d} (1d10 + DEX "
             "modifier + Monk level); if you reduce it to 0 you can catch the missile and spend 1 ki point to attack "
             "with it as part of the same reaction (range 20/60 feet)",
     "quotes": (("deflect-missiles", "the damage you take from the attack is reduced by 1d10 + your Dexterity modifier + your monk level"),
                ("deflect-missiles", "you can spend 1 ki point to make a ranged attack with the weapon or piece of ammunition you just caught"),
                ("deflect-missiles", "a normal range of 20 feet and a long range of 60 feet"))},
    # Slow Fall: "reduce any falling damage you take by an amount equal to five times your monk level."
    {"class": "monk", "feature": "slow-fall", "name": "Slow Fall", "uses": None, "recharge": None,
     "note": "Reaction when you fall: reduce the falling damage by {five_level} (5 x Monk level)",
     "quotes": (("slow-fall", "reduce any falling damage you take by an amount equal to five times your monk level"),)},
    # Stunning Strike: "you can spend 1 ki point to attempt a stunning strike. The target must succeed on a Constitution
    # saving throw or be stunned until the end of your next turn." Ki: "Ki save DC = 8 + your proficiency bonus + your
    # Wisdom modifier".
    {"class": "monk", "feature": "stunning-strike", "name": "Stunning Strike", "uses": None, "recharge": None,
     "note": "When you hit with a melee weapon attack, spend 1 ki point: the target makes a Constitution saving throw "
             "(DC {dc_wis}) or is stunned until the end of your next turn",
     "quotes": (("stunning-strike", "you can spend 1 ki point to attempt a stunning strike. The target must succeed on a Constitution saving throw or be stunned until the end of your next turn"),
                ("ki", "Ki save DC = 8 + your proficiency bonus + your Wisdom modifier"))},
    # Empty Body: "spend 4 ki points to become invisible for 1 minute. During that time, you also have resistance to all
    # damage but force damage. Additionally, you can spend 8 ki points to cast the astral projection spell, without
    # needing material components."
    {"class": "monk", "feature": "empty-body", "name": "Empty Body", "uses": None, "recharge": None,
     "note": "Action, 4 ki points: invisible for 1 minute with resistance to all damage but force; or 8 ki points to "
             "cast astral projection without material components (you can't take other creatures)",
     "quotes": (("empty-body", "spend 4 ki points to become invisible for 1 minute"),
                ("empty-body", "resistance to all damage but force damage"),
                ("empty-body", "you can spend 8 ki points to cast the astral projection spell, without needing material components"),
                ("empty-body", "you can't take any other creatures with you"))},
    # Divine Smite: "you can expend one spell slot to deal radiant damage to the target, in addition to the weapon's
    # damage. The extra damage is 2d8 for a 1st-level spell slot, plus 1d8 for each spell level higher than 1st, to a
    # maximum of 5d8. The damage increases by 1d8 if the target is an undead or a fiend."
    {"class": "paladin", "feature": "divine-smite", "name": "Divine Smite", "uses": None, "recharge": None,
     "note": "When you hit with a melee weapon attack, expend a spell slot for extra radiant damage: 2d8 for a 1st-level "
             "slot, +1d8 per slot level above 1st, maximum 5d8; +1d8 against an undead or a fiend",
     "extras": (
         # Improved Divine Smite (11): "Whenever you hit a creature with a melee weapon, the creature takes an extra 1d8
         # radiant damage. If you also use your Divine Smite with an attack, you add this damage to the extra damage of
         # your Divine Smite."
         ("improved-divine-smite", "Improved Divine Smite: every melee weapon hit deals an extra 1d8 radiant damage, "
          "added to Divine Smite's damage"),),
     "quotes": (("divine-smite", "you can expend one spell slot to deal radiant damage to the target, in addition to the weapon's damage"),
                ("divine-smite", "The extra damage is 2d8 for a 1st-level spell slot, plus 1d8 for each spell level higher than 1st, to a maximum of 5d8."),
                ("divine-smite", "The damage increases by 1d8 if the target is an undead or a fiend."),
                ("improved-divine-smite", "Whenever you hit a creature with a melee weapon, the creature takes an extra 1d8 radiant damage."))},
    # Cleansing Touch: "you can use your action to end one spell on yourself or on one willing creature that you touch.
    # You can use this feature a number of times equal to your Charisma modifier (a minimum of once). You regain
    # expended uses when you finish a long rest."
    {"class": "paladin", "feature": "cleansing-touch", "name": "Cleansing Touch", "uses": "@cha_min1", "recharge": "long",
     "note": "Action: end one spell on yourself or on one willing creature that you touch",
     "quotes": (("cleansing-touch", "you can use your action to end one spell on yourself or on one willing creature that you touch"),
                ("cleansing-touch", "a number of times equal to your Charisma modifier (a minimum of once). You regain expended uses when you finish a long rest."))},
    # Foe Slayer: "Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll of an
    # attack you make against one of your favored enemies."
    {"class": "ranger", "feature": "foe-slayer", "name": "Foe Slayer", "uses": None, "recharge": None,
     "note": "Once on each of your turns, add your Wisdom modifier ({wis:+d}) to the attack roll or the damage roll of "
             "an attack against one of your favored enemies (before or after the roll)",
     "quotes": (("foe-slayer", "Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll of an attack you make against one of your favored enemies."),)},
    # Stroke of Luck: "If your attack misses a target within range, you can turn the miss into a hit. Alternatively, if
    # you fail an ability check, you can treat the d20 roll as a 20. Once you use this feature, you can't use it again
    # until you finish a short or long rest."
    {"class": "rogue", "feature": "stroke-of-luck", "name": "Stroke of Luck", "uses": 1, "recharge": "short-or-long",
     "note": "If your attack misses a target within range, turn the miss into a hit; or if you fail an ability check, "
             "treat the d20 roll as a 20",
     "quotes": (("stroke-of-luck", "If your attack misses a target within range, you can turn the miss into a hit."),
                ("stroke-of-luck", "if you fail an ability check, you can treat the d20 roll as a 20."),
                ("stroke-of-luck", "you can't use it again until you finish a short or long rest."))},
    # Mystic Arcanum: "You can cast your arcanum spell once without expending a spell slot. You must finish a long rest
    # before you can do so again. At higher levels, you gain more warlock spells ...: one 7th- level spell at 13th level,
    # one 8th-level spell at 15th level, and one 9th-level spell at 17th level. You regain all uses of your Mystic
    # Arcanum when you finish a long rest."
    {"class": "warlock", "feature": "mystic-arcanum-6th-level", "name": "Mystic Arcanum", "recharge": "long",
     "uses": (1, (("mystic-arcanum-7th-level", 2), ("mystic-arcanum-8th-level", 3), ("mystic-arcanum-9th-level", 4))),
     "vars": {"arcanum_levels": ("6th", (("mystic-arcanum-7th-level", "6th and 7th"),
                                         ("mystic-arcanum-8th-level", "6th, 7th and 8th"),
                                         ("mystic-arcanum-9th-level", "6th, 7th, 8th and 9th")))},
     "note": "Cast each arcanum spell ({arcanum_levels} level) once without expending a spell slot; regain all uses "
             "when you finish a long rest",
     "quotes": (("mystic-arcanum-6th-level", "You can cast your arcanum spell once without expending a spell slot. You must finish a long rest before you can do so again."),
                ("mystic-arcanum-6th-level", "one 8th-level spell at 15th level, and one 9th-level spell at 17th level. You regain all uses of your Mystic Arcanum when you finish a long rest."))},
    # Eldritch Master: "You can spend 1 minute entreating your patron for aid to regain all your expended spell slots from
    # your Pact Magic feature. Once you regain spell slots with this feature, you must finish a long rest before you can
    # do so again."
    {"class": "warlock", "feature": "eldritch-master", "name": "Eldritch Master", "uses": 1, "recharge": "long",
     "note": "Spend 1 minute entreating your patron to regain all your expended Pact Magic spell slots (maximum "
             "{pact_slots})",
     "quotes": (("eldritch-master", "You can spend 1 minute entreating your patron for aid to regain all your expended spell slots from your Pact Magic feature."),
                ("eldritch-master", "you must finish a long rest before you can do so again"))},
)

# W6: a sentence added to the `details.note` of an EXISTING class resource (`target` = its id), under the same
# conditions as RESOURCE_TAIL_2014; the notes of one target join with "; " in table order.
RESOURCE_NOTES_2014: tuple[dict, ...] = (
    # Superior Inspiration: "when you roll initiative and have no uses of Bardic Inspiration left, you regain one use."
    {"class": "bard", "target": "bard:bardic-inspiration", "feature": "superior-inspiration",
     "note": "Superior Inspiration: when you roll initiative with no uses left, you regain one use",
     "quotes": (("superior-inspiration", "when you roll initiative and have no uses of Bardic Inspiration left, you regain one use"),)},
    # Channel Divinity (Cleric): "Each undead that can see or hear you within 30 feet of you must make a Wisdom saving
    # throw. If the creature fails its saving throw, it is turned for 1 minute or until it takes any damage." / "When you
    # use such an effect from this class, the DC equals your cleric spell save DC."
    {"class": "cleric", "target": "cleric:channel-divinity", "feature": "channel-divinity-turn-undead",
     "note": "Turn Undead (action): each undead within 30 feet that can see or hear you makes a Wisdom saving throw or "
             "is turned for 1 minute or until it takes damage; save DC {dc_wis} (your cleric spell save DC)",
     "quotes": (("channel-divinity-turn-undead", "Each undead that can see or hear you within 30 feet of you must make a Wisdom saving throw."),
                ("channel-divinity-turn-undead", "it is turned for 1 minute or until it takes any damage"),
                ("channel-divinity-1-rest", "the DC equals your cleric spell save DC"))},
    # Wild Shape: "You can stay in a beast shape for a number of hours equal to half your druid level (rounded down). You
    # then revert to your normal form unless you expend another use of this feature."
    {"class": "druid", "target": "druid:wild-shape", "feature": "wild-shape-cr-1-4-or-below-no-flying-or-swim-speed",
     "note": "A beast shape lasts {half_level} hours (half your Druid level, rounded down) unless you expend another use",
     "quotes": (("wild-shape-cr-1-4-or-below-no-flying-or-swim-speed", "You can stay in a beast shape for a number of hours equal to half your druid level (rounded down)."),
                ("wild-shape-cr-1-4-or-below-no-flying-or-swim-speed", "unless you expend another use of this feature"))},
    # Ki: "You start knowing three such features: Flurry of Blows, Patient Defense, and Step of the Wind." / "you can
    # spend 1 ki point to make two unarmed strikes as a bonus action" / "You can spend 1 ki point to take the Dodge
    # action as a bonus action" / "You can spend 1 ki point to take the Disengage or Dash action as a bonus action".
    {"class": "monk", "target": "monk:ki", "feature": "flurry-of-blows",
     "note": "Flurry of Blows, Patient Defense and Step of the Wind each cost 1 ki point",
     "quotes": (("flurry-of-blows", "you can spend 1 ki point to make two unarmed strikes as a bonus action"),
                ("patient-defense", "You can spend 1 ki point to take the Dodge action as a bonus action"),
                ("step-of-the-wind", "You can spend 1 ki point to take the Disengage or Dash action as a bonus action"))},
    # Diamond Soul: "whenever you make a saving throw and fail, you can spend 1 ki point to reroll it and take the second
    # result."
    {"class": "monk", "target": "monk:ki", "feature": "diamond-soul",
     "note": "Diamond Soul: when you fail a saving throw, spend 1 ki point to reroll it and take the second result",
     "quotes": (("diamond-soul", "whenever you make a saving throw and fail, you can spend 1 ki point to reroll it and take the second result"),)},
    # Perfect Self: "when you roll for initiative and have no ki points remaining, you regain 4 ki points."
    {"class": "monk", "target": "monk:ki", "feature": "perfect-self",
     "note": "Perfect Self: when you roll initiative with no ki points left, you regain 4 ki points",
     "quotes": (("perfect-self", "when you roll for initiative and have no ki points remaining, you regain 4 ki points"),)},
    # Lay on Hands: "you can expend 5 hit points from your pool of healing to cure the target of one disease or neutralize
    # one poison affecting it. ... This feature has no effect on undead and constructs."
    {"class": "paladin", "target": "paladin:lay-on-hands", "feature": "lay-on-hands",
     "note": "Expend 5 hit points from the pool to cure one disease or neutralize one poison (separately for each); no "
             "effect on undead and constructs",
     "quotes": (("lay-on-hands", "you can expend 5 hit points from your pool of healing to cure the target of one disease or neutralize one poison affecting it"),
                ("lay-on-hands", "This feature has no effect on undead and constructs."))},
    # Channel Divinity (Paladin): "When you use such an effect from this class, the DC equals your paladin spell save DC."
    {"class": "paladin", "target": "paladin:channel-divinity", "feature": "channel-divinity",
     "note": "Channel Divinity effects that need a saving throw use save DC {dc_cha} (your paladin spell save DC)",
     "quotes": (("channel-divinity", "the DC equals your paladin spell save DC"),)},
    # Sorcerous Restoration: "you regain 4 expended sorcery points whenever you finish a short rest."
    {"class": "sorcerer", "target": "sorcerer:sorcery-points", "feature": "sorcerous-restoration",
     "note": "Sorcerous Restoration: you regain 4 expended sorcery points whenever you finish a short rest",
     "quotes": (("sorcerous-restoration", "you regain 4 expended sorcery points whenever you finish a short rest"),)},
)

# ---- W7 (finding F4): the 2014 SRD subclass use-limit tail. The counterpart of SUBCLASS_TAIL_2024 / SUBCLASS_NOTES_2024
# for rulesets "mixed" and "2014" and the 12 SRD subclasses only (berserker, lore, life, land, champion, open-hand,
# devotion, hunter, thief, draconic, fiend, evocation; the book subclasses are slice W8). Same spec keys as
# RESOURCE_TAIL_2014 plus `subclass`; `class_resources._subclass_tail_2014` builds one resource per SUBCLASS_TAIL_2014
# entry (source kind "subclass") and adds each SUBCLASS_NOTES_2014 sentence to the resource `target` of the class.
# Both need the character's selected subclass, the SRD feature record in the catalog and the class level at its level.

# Life Domain Divine Strike: "you can cause the attack to deal an extra 1d8 radiant damage to the target. When you reach
# 14th level, the extra damage increases to 2d8." (class level, dice), pinned against `divine-strike` (level 8).
DIVINE_STRIKE_DICE_2014 = ((8, "1d8"), (14, "2d8"))

SUBCLASS_TAIL_2014: tuple[dict, ...] = (
    # ---- Berserker (Barbarian)
    # Frenzy: "for the duration of your rage you can make a single melee weapon attack as a bonus action on each of your
    # turns after this one. When your rage ends, you suffer one level of exhaustion"
    {"subclass": "berserker", "class": "barbarian", "feature": "frenzy", "name": "Frenzy", "uses": None, "recharge": None,
     "note": "While raging you can make a single melee weapon attack as a bonus action on each of your turns after "
             "this one; when your rage ends you suffer one level of exhaustion",
     "quotes": (("frenzy", "for the duration of your rage you can make a single melee weapon attack as a bonus action on each of your turns after this one"),
                ("frenzy", "When your rage ends, you suffer one level of exhaustion"))},
    # Intimidating Presence: "choose one creature that you can see within 30 feet of you. If the creature can see or hear
    # you, it must succeed on a Wisdom saving throw (DC equal to 8 + your proficiency bonus + your Charisma modifier) or
    # be frightened of you until the end of your next turn. ... If the creature succeeds on its saving throw, you can't
    # use this feature on that creature again for 24 hours."
    {"subclass": "berserker", "class": "barbarian", "feature": "intimidating-presence", "name": "Intimidating Presence",
     "uses": None, "recharge": None,
     "note": "Action: one creature you can see within 30 feet that can see or hear you makes a Wisdom saving throw "
             "(DC {dc_cha}) or is frightened of you until the end of your next turn (extend it with your action on "
             "later turns); a creature that succeeds can't be targeted again for 24 hours",
     "quotes": (("intimidating-presence", "DC equal to 8 + your proficiency bonus + your Charisma modifier"),
                ("intimidating-presence", "choose one creature that you can see within 30 feet of you"),
                ("intimidating-presence", "you can't use this feature on that creature again for 24 hours"))},
    # ---- Life (Cleric)
    # Disciple of Life: "Whenever you use a spell of 1st level or higher to restore hit points to a creature, the
    # creature regains additional hit points equal to 2 + the spell's level." / Blessed Healer (6): "When you cast a spell
    # of 1st level or higher that restores hit points to a creature other than you, you regain hit points equal to 2 +
    # the spell's level."
    {"subclass": "life", "class": "cleric", "feature": "disciple-of-life", "name": "Disciple of Life", "uses": None,
     "recharge": None,
     "note": "A healing spell of 1st level or higher restores an extra 2 + the spell's level hit points",
     "extras": (("blessed-healer", "Blessed Healer: when you heal another creature with a spell of 1st level or higher, "
                 "you regain 2 + the spell's level hit points"),),
     "quotes": (("disciple-of-life", "the creature regains additional hit points equal to 2 + the spell's level"),
                ("blessed-healer", "you regain hit points equal to 2 + the spell's level"))},
    # Divine Strike: "Once on each of your turns when you hit a creature with a weapon attack, you can cause the attack to
    # deal an extra 1d8 radiant damage to the target. When you reach 14th level, the extra damage increases to 2d8." (the
    # id differs from the 2024 `cleric:divine-strike`, which drives the attack-row notes.)
    {"subclass": "life", "class": "cleric", "feature": "divine-strike", "name": "Divine Strike (Life Domain)",
     "uses": None, "recharge": None, "dice": "@strike_dice", "level_vars": {"strike_dice": DIVINE_STRIKE_DICE_2014},
     "note": "Once on each of your turns when you hit a creature with a weapon attack, the attack deals an extra "
             "{strike_dice} radiant damage",
     "quotes": (("divine-strike", "Once on each of your turns when you hit a creature with a weapon attack, you can cause the attack to deal an extra 1d8 radiant damage to the target."),
                ("divine-strike", "When you reach 14th level, the extra damage increases to 2d8."))},
    # ---- Land (Druid)
    # Natural Recovery: "During a short rest, you choose expended spell slots to recover. The spell slots can have a
    # combined level that is equal to or less than half your druid level (rounded up), and none of the slots can be 6th
    # level or higher. You can't use this feature again until you finish a long rest."
    {"subclass": "land", "class": "druid", "feature": "natural-recovery", "name": "Natural Recovery", "uses": None,
     "recharge": "long", "pool": "@half_level_up",
     "note": "During a short rest, recover expended spell slots with a combined level of up to {half_level_up} (half "
             "your Druid level, rounded up), none of them 6th level or higher; once until you finish a long rest",
     "quotes": (("natural-recovery", "During a short rest, you choose expended spell slots to recover."),
                ("natural-recovery", "equal to or less than half your druid level (rounded up), and none of the slots can be 6th level or higher"),
                ("natural-recovery", "You can't use this feature again until you finish a long rest."))},
    # Nature's Sanctuary: "When a beast or plant creature attacks you, that creature must make a Wisdom saving throw
    # against your druid spell save DC. On a failed save, the creature must choose a different target, or the attack
    # automatically misses. On a successful save, the creature is immune to this effect for 24 hours."
    {"subclass": "land", "class": "druid", "feature": "natures-sanctuary", "name": "Nature's Sanctuary", "uses": None,
     "recharge": None,
     "note": "A beast or plant creature that attacks you makes a Wisdom saving throw (DC {dc_wis}, your druid spell save "
             "DC); on a failure it must choose a different target or the attack misses; on a success it is immune for "
             "24 hours",
     "quotes": (("natures-sanctuary", "that creature must make a Wisdom saving throw against your druid spell save DC"),
                ("natures-sanctuary", "the creature is immune to this effect for 24 hours"))},
    # ---- Champion (Fighter)
    # Survivor: "At the start of each of your turns, you regain hit points equal to 5 + your Constitution modifier if you
    # have no more than half of your hit points left. You don't gain this benefit if you have 0 hit points."
    {"subclass": "champion", "class": "fighter", "feature": "survivor", "name": "Survivor", "uses": None, "recharge": None,
     "note": "At the start of each of your turns, if you have no more than half your hit points left (and more than 0), "
             "regain {survivor} hit points (5 + CON modifier)",
     "quotes": (("survivor", "you regain hit points equal to 5 + your Constitution modifier if you have no more than half of your hit points left"),
                ("survivor", "You don't gain this benefit if you have 0 hit points."))},
    # ---- Open Hand (Monk)
    # Wholeness of Body: "As an action, you can regain hit points equal to three times your monk level. You must finish a
    # long rest before you can use this feature again."
    {"subclass": "open-hand", "class": "monk", "feature": "wholeness-of-body", "name": "Wholeness of Body", "uses": 1,
     "recharge": "long",
     "note": "Action: regain {three_level} hit points (3 x Monk level)",
     "quotes": (("wholeness-of-body", "you can regain hit points equal to three times your monk level"),
                ("wholeness-of-body", "You must finish a long rest before you can use this feature again."))},
    # Tranquility: "At the end of a long rest, you gain the effect of a sanctuary spell that lasts until the start of your
    # next long rest (the spell can end early as normal). The saving throw DC for the spell equals 8 + your Wisdom
    # modifier + your proficiency bonus."
    {"subclass": "open-hand", "class": "monk", "feature": "tranquility", "name": "Tranquility", "uses": None,
     "recharge": None,
     "note": "At the end of a long rest you gain the effect of a sanctuary spell until the start of your next long rest "
             "(it can end early as normal); save DC {dc_wis}",
     "quotes": (("tranquility", "At the end of a long rest, you gain the effect of a sanctuary spell"),
                ("tranquility", "The saving throw DC for the spell equals 8 + your Wisdom modifier + your proficiency bonus."))},
    # ---- Devotion (Paladin)
    # Holy Nimbus: the catalog text has no rest rule, so none is modelled. "For 1 minute, bright light shines from you in a
    # 30-foot radius, and dim light shines 30 feet beyond that. Whenever an enemy creature starts its turn in the bright
    # light, the creature takes 10 radiant damage. In addition, for the duration, you have advantage on saving throws
    # against spells cast by fiends or undead."
    {"subclass": "devotion", "class": "paladin", "feature": "holy-nimbus", "name": "Holy Nimbus", "uses": None,
     "recharge": None,
     "note": "Action, 1 minute: bright light in a 30-foot radius (dim light 30 feet beyond); an enemy that starts its "
             "turn in the bright light takes 10 radiant damage; you have advantage on saving throws against spells cast "
             "by fiends or undead",
     "quotes": (("holy-nimbus", "bright light shines from you in a 30-foot radius"),
                ("holy-nimbus", "the creature takes 10 radiant damage"),
                ("holy-nimbus", "you have advantage on saving throws against spells cast by fiends or undead"))},
    # ---- Draconic (Sorcerer)
    # Elemental Affinity: "when you cast a spell that deals damage of the type associated with your draconic ancestry,
    # you can add your Charisma modifier to one damage roll of that spell. At the same time, you can spend 1 sorcery point
    # to gain resistance to that damage type for 1 hour."
    {"subclass": "draconic", "class": "sorcerer", "feature": "elemental-affinity", "name": "Elemental Affinity",
     "uses": None, "recharge": None,
     "note": "When you cast a spell that deals damage of your draconic ancestry's type, add your Charisma modifier "
             "({cha:+d}) to one damage roll of that spell; you can spend 1 sorcery point to gain resistance to that "
             "damage type for 1 hour",
     "quotes": (("elemental-affinity", "you can add your Charisma modifier to one damage roll of that spell. At the same time, you can spend 1 sorcery point to gain resistance to that damage type for 1 hour"),)},
    # ---- Fiend (Warlock)
    # Dark One's Blessing: "when you reduce a hostile creature to 0 hit points, you gain temporary hit points equal to
    # your Charisma modifier + your warlock level (minimum of 1)."
    {"subclass": "fiend", "class": "warlock", "feature": "dark-ones-blessing", "name": "Dark One's Blessing",
     "uses": None, "recharge": None,
     "note": "When you reduce a hostile creature to 0 hit points, you gain {blessing} temporary hit points (CHA modifier "
             "+ Warlock level, minimum 1)",
     "quotes": (("dark-ones-blessing", "when you reduce a hostile creature to 0 hit points, you gain temporary hit points equal to your Charisma modifier + your warlock level (minimum of 1)"),)},
    # Dark One's Own Luck: "When you make an ability check or a saving throw, you can use this feature to add a d10 to
    # your roll. You can do so after seeing the initial roll but before any of the roll's effects occur. Once you use
    # this feature, you can't use it again until you finish a short or long rest."
    {"subclass": "fiend", "class": "warlock", "feature": "dark-ones-own-luck", "name": "Dark One's Own Luck", "uses": 1,
     "recharge": "short-or-long", "die": "d10",
     "note": "Add a d10 to an ability check or saving throw you make, after seeing the roll but before any of its "
             "effects occur",
     "quotes": (("dark-ones-own-luck", "When you make an ability check or a saving throw, you can use this feature to add a d10 to your roll."),
                ("dark-ones-own-luck", "you can't use it again until you finish a short or long rest."))},
    # Hurl Through Hell: "when you hit a creature with an attack, you can use this feature to instantly transport the
    # target through the lower planes. ... At the end of your next turn, the target returns to the space it previously
    # occupied ... If the target is not a fiend, it takes 10d10 psychic damage ... you can't use it again until you finish
    # a long rest."
    {"subclass": "fiend", "class": "warlock", "feature": "hurl-through-hell", "name": "Hurl Through Hell", "uses": 1,
     "recharge": "long",
     "note": "When you hit a creature with an attack, banish it through the lower planes: it returns at the end of your "
             "next turn and, unless it is a fiend, takes 10d10 psychic damage",
     "quotes": (("hurl-through-hell", "when you hit a creature with an attack, you can use this feature to instantly transport the target through the lower planes"),
                ("hurl-through-hell", "At the end of your next turn, the target returns to the space it previously occupied"),
                ("hurl-through-hell", "If the target is not a fiend, it takes 10d10 psychic damage"),
                ("hurl-through-hell", "you can't use it again until you finish a long rest."))},
    # ---- Evocation (Wizard)
    # Empowered Evocation: "you can add your Intelligence modifier to one damage roll of any wizard evocation spell you
    # cast."
    {"subclass": "evocation", "class": "wizard", "feature": "empowered-evocation", "name": "Empowered Evocation",
     "uses": None, "recharge": None,
     "note": "Add your Intelligence modifier ({int:+d}) to one damage roll of any wizard evocation spell you cast",
     "quotes": (("empowered-evocation", "you can add your Intelligence modifier to one damage roll of any wizard evocation spell you cast"),)},
    # Overchannel: "When you cast a wizard spell of 1st through 5th level that deals damage, you can deal maximum damage
    # with that spell. The first time you do so, you suffer no adverse effect. If you use this feature again before you
    # finish a long rest, you take 2d12 necrotic damage for each level of the spell, immediately after you cast it. Each
    # time you use this feature again before finishing a long rest, the necrotic damage per spell level increases by
    # 1d12. This damage ignores resistance and immunity."
    {"subclass": "evocation", "class": "wizard", "feature": "overchannel", "name": "Overchannel", "uses": 1,
     "recharge": "long",
     "note": "When you cast a wizard spell of 1st through 5th level that deals damage, deal maximum damage with it; the "
             "first use before a long rest has no adverse effect, each further use deals 2d12 necrotic damage to you per "
             "spell level (+1d12 per level for every use after that), ignoring resistance and immunity",
     "quotes": (("overchannel", "you can deal maximum damage with that spell"),
                ("overchannel", "The first time you do so, you suffer no adverse effect."),
                ("overchannel", "you take 2d12 necrotic damage for each level of the spell"),
                ("overchannel", "the necrotic damage per spell level increases by 1d12"),
                ("overchannel", "This damage ignores resistance and immunity."))},
)

# W7: a sentence added to the `details.note` of an EXISTING resource of the class (`target` = its id), when the feature
# spends that resource; same conditions as SUBCLASS_TAIL_2014, joined with "; " after the notes it already has.
SUBCLASS_NOTES_2014: tuple[dict, ...] = (
    # Cutting Words: "you can use your reaction to expend one of your uses of Bardic Inspiration, rolling a Bardic
    # Inspiration die and subtracting the number rolled from the creature's roll."
    {"subclass": "lore", "class": "bard", "target": "bard:bardic-inspiration", "feature": "cutting-words",
     "name": "Cutting Words",
     "note": "Cutting Words (Reaction, 60 feet): expend a use to roll a Bardic Inspiration die and subtract it from a "
             "creature's attack roll, ability check or damage roll",
     "quotes": (("cutting-words", "you can use your reaction to expend one of your uses of Bardic Inspiration, rolling a Bardic Inspiration die and subtracting the number rolled from the creature's roll"),
                ("cutting-words", "within 60 feet of you"))},
    # Peerless Skill: "when you make an ability check, you can expend one use of Bardic Inspiration. Roll a Bardic
    # Inspiration die and add the number rolled to your ability check."
    {"subclass": "lore", "class": "bard", "target": "bard:bardic-inspiration", "feature": "peerless-skill",
     "name": "Peerless Skill",
     "note": "Peerless Skill: expend a use to add a Bardic Inspiration die to your own ability check, after the roll but "
             "before the GM says whether you succeed",
     "quotes": (("peerless-skill", "you can expend one use of Bardic Inspiration. Roll a Bardic Inspiration die and add the number rolled to your ability check"),)},
    # Preserve Life: "restore a number of hit points equal to five times your cleric level. Choose any creatures within
    # 30 feet of you, and divide those hit points among them. This feature can restore a creature to no more than half of
    # its hit point maximum. You can't use this feature on an undead or a construct."
    {"subclass": "life", "class": "cleric", "target": "cleric:channel-divinity", "feature": "channel-divinity-preserve-life",
     "name": "Preserve Life",
     "note": "Preserve Life (action, 30 feet): restore up to {five_level} hit points (5 x Cleric level) divided among "
             "creatures, none above half its hit point maximum; not on an undead or a construct",
     "quotes": (("channel-divinity-preserve-life", "restore a number of hit points equal to five times your cleric level"),
                ("channel-divinity-preserve-life", "This feature can restore a creature to no more than half of its hit point maximum."),
                ("channel-divinity-preserve-life", "You can't use this feature on an undead or a construct."))},
    # Sacred Weapon: "For 1 minute, you add your Charisma modifier to attack rolls made with that weapon (with a minimum
    # bonus of +1). The weapon also emits bright light in a 20-foot radius ... If the weapon is not already magical, it
    # becomes magical for the duration."
    {"subclass": "devotion", "class": "paladin", "target": "paladin:channel-divinity",
     "feature": "channel-divinity-sacred-weapon", "name": "Sacred Weapon",
     "note": "Sacred Weapon (action, 1 minute): add {cha_min1:+d} (CHA modifier, minimum +1) to attack rolls with one "
             "weapon you hold; it emits bright light in a 20-foot radius and becomes magical",
     "quotes": (("channel-divinity-sacred-weapon", "you add your Charisma modifier to attack rolls made with that weapon (with a minimum bonus of +1)"),
                ("channel-divinity-sacred-weapon", "For 1 minute"),
                ("channel-divinity-sacred-weapon", "emits bright light in a 20-foot radius"))},
    # Turn the Unholy: "Each fiend or undead that can see or hear you within 30 feet of you must make a Wisdom saving
    # throw. If the creature fails its saving throw, it is turned for 1 minute or until it takes damage."
    {"subclass": "devotion", "class": "paladin", "target": "paladin:channel-divinity",
     "feature": "channel-divinity-turn-the-unholy", "name": "Turn the Unholy",
     "note": "Turn the Unholy (action, 30 feet): each fiend or undead that can see or hear you makes a Wisdom saving "
             "throw or is turned for 1 minute or until it takes damage",
     "quotes": (("channel-divinity-turn-the-unholy", "Each fiend or undead that can see or hear you within 30 feet of you must make a Wisdom saving throw."),
                ("channel-divinity-turn-the-unholy", "it is turned for 1 minute or until it takes damage"))},
    # Quivering Palm: "When you hit a creature with an unarmed strike, you can spend 3 ki points to start these
    # imperceptible vibrations, which last for a number of days equal to your monk level. ... When you use this action,
    # the creature must make a Constitution saving throw. If it fails, it is reduced to 0 hit points. If it succeeds, it
    # takes 10d10 necrotic damage." The DC is the Ki save DC (Ki: "Ki save DC = 8 + your proficiency bonus + your Wisdom
    # modifier").
    {"subclass": "open-hand", "class": "monk", "target": "monk:ki", "feature": "quivering-palm", "name": "Quivering Palm",
     "note": "Quivering Palm (3 ki points when you hit with an unarmed strike): the vibrations last {level} days (Monk "
             "level); ending them takes your action and forces a Constitution saving throw (DC {dc_wis}): 0 hit points "
             "on a failure, 10d10 necrotic damage on a success; one creature at a time",
     "quotes": (("quivering-palm", "you can spend 3 ki points to start these imperceptible vibrations, which last for a number of days equal to your monk level"),
                ("quivering-palm", "the creature must make a Constitution saving throw"),
                ("quivering-palm", "If it succeeds, it takes 10d10 necrotic damage."),
                ("quivering-palm", "You can have only one creature under the effect of this feature at a time."),
                ("ki", "Ki save DC = 8 + your proficiency bonus + your Wisdom modifier"))},
    # Draconic Presence: "As an action, you can spend 5 sorcery points to draw on this power and exude an aura of awe or
    # fear (your choice) to a distance of 60 feet. For 1 minute or until you lose your concentration ..., each hostile
    # creature that starts its turn in this aura must succeed on a Wisdom saving throw or be charmed (if you chose awe) or
    # frightened (if you chose fear) until the aura ends. A creature that succeeds on this saving throw is immune to your
    # aura for 24 hours."
    {"subclass": "draconic", "class": "sorcerer", "target": "sorcerer:sorcery-points", "feature": "draconic-presence",
     "name": "Draconic Presence",
     "note": "Draconic Presence (action, 5 sorcery points): an aura of awe or fear to 60 feet for 1 minute "
             "(concentration); a hostile creature that starts its turn in it makes a Wisdom saving throw or is charmed "
             "or frightened; a creature that succeeds is immune for 24 hours",
     "quotes": (("draconic-presence", "you can spend 5 sorcery points to draw on this power and exude an aura of awe or fear (your choice) to a distance of 60 feet"),
                ("draconic-presence", "must succeed on a Wisdom saving throw or be charmed (if you chose awe) or frightened (if you chose fear)"),
                ("draconic-presence", "A creature that succeeds on this saving throw is immune to your aura for 24 hours."))},
)

# ---- W8 (finding F4, book half): the 2014 non-SRD subclass use-limit tail ------------------------------------------
# Same spec keys as SUBCLASS_TAIL_2014 / SUBCLASS_NOTES_2014 (W7), keyed by the imported book subclass id
# (`<slug>-<source>`) and its feature record id; `class_resources._subclass_tail_2014` reads both tuples. Only the numbers
# present in the record text are used (each entry quotes them); features whose picks, tables or text give no use rule or
# number stay plain feature lines (see the ARCHITECTURE W8 scan). Mixed / 2014 only.

# Level tables that live only in the text; every one is pinned in BOOK_TABLE_PINS_2014.
SPIRIT_SHIELD_DICE_2014 = ((6, "2d6"), (10, "3d6"), (14, "4d6"))
ELEMENTAL_CLEAVER_DICE_2014 = ((6, "1d6"), (14, "2d6"))
STORM_AURA_DESERT_2014 = ((3, 2), (5, 3), (10, 4), (15, 5), (20, 6))
STORM_AURA_SEA_2014 = ((3, "1d6"), (10, "2d6"), (15, "3d6"), (20, "4d6"))
STORM_AURA_TUNDRA_2014 = ((3, 2), (5, 3), (10, 4), (15, 5), (20, 6))
PERFORMANCE_OF_CREATION_SIZE_2014 = ((3, "Medium"), (6, "Large"), (14, "Huge"))
MANTLE_OF_INSPIRATION_THP_2014 = ((3, 5), (5, 8), (10, 11), (15, 14))
PSYCHIC_BLADES_DICE_2014 = ((3, "2d6"), (5, "3d6"), (10, "5d6"), (15, "8d6"))

BOOK_TABLE_PINS_2014: dict[str, tuple] = {
    "SPIRIT_SHIELD_DICE_2014": (("ancestral-guardian-xge-6-spirit-shield", "reduce that damage by 2d6"),
                                ("ancestral-guardian-xge-6-spirit-shield", "by 3d6 at 10th level and by 4d6 at 14th level")),
    "ELEMENTAL_CLEAVER_DICE_2014": (("giant-bgg-6-elemental-cleaver", "it deals an extra 1d6 damage of the chosen type when it hits"),
                                    ("giant-bgg-14-demiurgic-colossus", "the extra damage dealt by your Elemental Cleaver feature increases to 2d6")),
    "STORM_AURA_DESERT_2014": (("storm-herald-xge-3-storm-aura", "all other creatures in your aura take 2 fire damage each"),
                               ("storm-herald-xge-3-storm-aura", "increasing to 3 at 5th level, 4 at 10th level, 5 at 15th level, and 6 at 20th level")),
    "STORM_AURA_SEA_2014": (("storm-herald-xge-3-storm-aura", "The target takes 1d6 lightning damage on a failed save"),
                            ("storm-herald-xge-3-storm-aura", "increasing to 2d6 at 10th level, 3d6 at 15th level, and 4d6 at 20th level")),
    "STORM_AURA_TUNDRA_2014": (("storm-herald-xge-3-storm-aura", "gains 2 temporary hit points"),
                               ("storm-herald-xge-3-storm-aura", "The temporary hit points increase when you reach certain levels in this class, increasing to 3 at 5th level, 4 at 10th level, 5 at 15th level, and 6 at 20th level")),
    "PERFORMANCE_OF_CREATION_SIZE_2014": (("creation-tce-3-performance-of-creation", "the item must be Medium or smaller"),
                                          ("creation-tce-3-performance-of-creation", "increases by one size category when you reach 6th level (Large) and 14th level (Huge)")),
    "MANTLE_OF_INSPIRATION_THP_2014": (("glamour-xge-3-mantle-of-inspiration", "Each of them gains 5 temporary hit points"),
                                       ("glamour-xge-3-mantle-of-inspiration", "increasing to 8 at 5th level, 11 at 10th level, and 14 at 15th level")),
    "PSYCHIC_BLADES_DICE_2014": (("whispers-xge-3-psychic-blades", "deal an extra 2d6 psychic damage to that target"),
                                 ("whispers-xge-3-psychic-blades", "increasing to 3d6 at 5th level, 5d6 at 10th level, and 8d6 at 15th level")),
}

SUBCLASS_TAIL_2014_BOOKS: tuple[dict, ...] = (
    # ---- Barbarian: Path of the Ancestral Guardian (XGE)
    # Spirit Shield: "If you are raging and another creature you can see within 30 feet of you takes damage, you can use
    # your reaction to reduce that damage by 2d6. ... by 3d6 at 10th level and by 4d6 at 14th level." Vengeful Ancestors (14):
    # "the attacker takes an amount of force damage equal to the damage that your Spirit Shield prevents."
    {"subclass": "ancestral-guardian-xge", "class": "barbarian", "feature": "ancestral-guardian-xge-6-spirit-shield",
     "name": "Spirit Shield", "uses": None, "recharge": None, "dice": "@shield_dice",
     "level_vars": {"shield_dice": SPIRIT_SHIELD_DICE_2014},
     "note": "While raging, when another creature you can see within 30 feet takes damage, use your reaction to reduce "
             "that damage by {shield_dice}",
     "extras": (("ancestral-guardian-xge-14-vengeful-ancestors", "Vengeful Ancestors: the attacker takes force damage "
                 "equal to the damage your Spirit Shield prevents"),),
     "quotes": (("ancestral-guardian-xge-6-spirit-shield", "If you are raging and another creature you can see within 30 feet of you takes damage, you can use your reaction to reduce that damage by 2d6"),
                ("ancestral-guardian-xge-14-vengeful-ancestors", "the attacker takes an amount of force damage equal to the damage that your Spirit Shield prevents"))},
    # Consult the Spirits: "you cast the augury or clairvoyance spell, without using a spell slot or material components.
    # ... Wisdom is your spellcasting ability for these spells. After you cast either spell in this way, you can't use this
    # feature again until you finish a short or long rest."
    {"subclass": "ancestral-guardian-xge", "class": "barbarian", "feature": "ancestral-guardian-xge-10-consult-the-spirits",
     "name": "Consult the Spirits", "uses": 1, "recharge": "short-or-long",
     "note": "Cast augury or clairvoyance without a spell slot or material components (Wisdom is the spellcasting "
             "ability; clairvoyance summons an ancestral spirit instead of a sensor)",
     "quotes": (("ancestral-guardian-xge-10-consult-the-spirits", "you cast the augury or clairvoyance spell, without using a spell slot or material components"),
                ("ancestral-guardian-xge-10-consult-the-spirits", "Wisdom is your spellcasting ability for these spells"),
                ("ancestral-guardian-xge-10-consult-the-spirits", "you can't use this feature again until you finish a short or long rest"))},
    # ---- Barbarian: Path of the Battlerager (SCAG)
    # Battlerager Armor: "While you are wearing spiked armor and are raging, you can use a bonus action to make one melee
    # weapon attack with your armor spikes ... the spikes deal 1d4 piercing damage. ... when you use the Attack action to
    # grapple a creature, the target takes 3 piercing damage if your grapple check succeeds."
    {"subclass": "battlerager-scag", "class": "barbarian", "feature": "battlerager-scag-3-battlerager-armor",
     "name": "Battlerager Armor", "uses": None, "recharge": None,
     "note": "In spiked armor while raging: a bonus action melee attack with the armor spikes at a target within 5 feet "
             "(Strength modifier) deals 1d4 piercing damage; grappling with the Attack action deals 3 piercing damage "
             "when the grapple check succeeds",
     "quotes": (("battlerager-scag-3-battlerager-armor", "the spikes deal 1d4 piercing damage"),
                ("battlerager-scag-3-battlerager-armor", "the target takes 3 piercing damage if your grapple check succeeds"))},
    # Reckless Abandon: "when you use Reckless Attack while raging, you also gain temporary hit points equal to your
    # Constitution modifier (minimum of 1). They vanish if any of them are left when your rage ends."
    {"subclass": "battlerager-scag", "class": "barbarian", "feature": "battlerager-scag-6-reckless-abandon",
     "name": "Reckless Abandon", "uses": None, "recharge": None,
     "note": "Reckless Attack while raging also gives you {con_min1} temporary hit points (Constitution modifier, minimum "
             "1); they vanish when your rage ends",
     "quotes": (("battlerager-scag-6-reckless-abandon", "you also gain temporary hit points equal to your Constitution modifier (minimum of 1)"),
                ("battlerager-scag-6-reckless-abandon", "They vanish if any of them are left when your rage ends"))},
    # Spiked Retribution: "when a creature within 5 feet of you hits you with a melee attack, the attacker takes 3 piercing
    # damage if you are raging, aren't incapacitated, and are wearing spiked armor."
    {"subclass": "battlerager-scag", "class": "barbarian", "feature": "battlerager-scag-14-spiked-retribution",
     "name": "Spiked Retribution", "uses": None, "recharge": None,
     "note": "While raging in spiked armor and not incapacitated, a creature within 5 feet that hits you with a melee "
             "attack takes 3 piercing damage",
     "quotes": (("battlerager-scag-14-spiked-retribution", "the attacker takes 3 piercing damage if you are raging, aren't incapacitated, and are wearing spiked armor"),)},
    # ---- Barbarian: Path of the Beast (TCE)
    # Form of the Beast: Bite 1d8 piercing, "you regain a number of hit points equal to your proficiency bonus, provided
    # you have less than half your hit points"; Claws 1d6 slashing, one additional claw attack; Tail 1d8 piercing, reach,
    # "you can use your reaction to swipe your tail and roll a d8, applying a bonus to your AC equal to the number rolled".
    {"subclass": "beast-tce", "class": "barbarian", "feature": "beast-tce-3-form-of-the-beast", "name": "Form of the Beast",
     "uses": None, "recharge": None,
     "note": "When you rage, manifest one natural weapon (Strength modifier on attack and damage, simple melee weapon). "
             "Bite: 1d8 piercing; once on each of your turns when you damage a creature with it you regain {pb} hit "
             "points (proficiency bonus) if you have less than half your hit points. Claws: 1d6 slashing; once on each "
             "of your turns with the Attack action you can make one additional claw attack. Tail: 1d8 piercing, reach; "
             "when a creature you can see within 10 feet hits you, use your reaction to add a d8 to your AC against "
             "that attack",
     "quotes": (("beast-tce-3-form-of-the-beast", "It deals 1d8 piercing damage on a hit."),
                ("beast-tce-3-form-of-the-beast", "you regain a number of hit points equal to your proficiency bonus, provided you have less than half your hit points"),
                ("beast-tce-3-form-of-the-beast", "It deals 1d6 slashing damage on a hit."),
                ("beast-tce-3-form-of-the-beast", "you can make one additional claw attack as part of the same action"),
                ("beast-tce-3-form-of-the-beast", "which deals 1d8 piercing damage on a hit and has the reach property"),
                ("beast-tce-3-form-of-the-beast", "roll a d8, applying a bonus to your AC equal to the number rolled"))},
    # Infectious Fury: "The target must succeed on a Wisdom saving throw (DC equal to 8 + your Constitution modifier + your
    # proficiency bonus) or suffer one of the following effects ... The target takes 2d12 psychic damage. You can use this
    # feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest."
    {"subclass": "beast-tce", "class": "barbarian", "feature": "beast-tce-10-infectious-fury", "name": "Infectious Fury",
     "uses": "@pb", "recharge": "long",
     "note": "When you hit with your natural weapons while raging, the target makes a Wisdom saving throw (DC {dc_con}) "
             "or your choice of: it uses its reaction to make a melee attack against another creature you choose, or it "
             "takes 2d12 psychic damage",
     "quotes": (("beast-tce-10-infectious-fury", "(DC equal to 8 + your Constitution modifier + your proficiency bonus)"),
                ("beast-tce-10-infectious-fury", "The target takes 2d12 psychic damage."),
                ("beast-tce-10-infectious-fury", "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))},
    # Call the Hunt: "a number of other willing creatures you can see within 30 feet of you equal to your Constitution
    # modifier (minimum of one creature). You gain 5 temporary hit points for each creature that accepts ... roll a d6 and gain
    # a bonus to the damage ... a number of times equal to your proficiency bonus ... long rest."
    {"subclass": "beast-tce", "class": "barbarian", "feature": "beast-tce-14-call-the-hunt", "name": "Call the Hunt",
     "uses": "@pb", "recharge": "long",
     "note": "When you enter your rage, choose up to {con_min1} other willing creature(s) you can see within 30 feet "
             "(Constitution modifier, minimum 1); you gain 5 temporary hit points for each one that accepts, and until "
             "the rage ends each can add a d6 to the damage of one hit on each of its turns",
     "quotes": (("beast-tce-14-call-the-hunt", "a number of other willing creatures you can see within 30 feet of you equal to your Constitution modifier (minimum of one creature)"),
                ("beast-tce-14-call-the-hunt", "You gain 5 temporary hit points for each creature that accepts this feature"),
                ("beast-tce-14-call-the-hunt", "roll a d6 and gain a bonus to the damage equal to the number rolled"),
                ("beast-tce-14-call-the-hunt", "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))},
    # ---- Barbarian: Path of the Giant (BGG)
    # Elemental Cleaver: "infuse it with one of the following damage types: acid, cold, fire, thunder, or lightning ... it deals
    # an extra 1d6 damage of the chosen type when it hits, and it gains the thrown property, with a normal range of 20 feet and a
    # long range of 60 feet." Demiurgic Colossus (14): "increases to 2d6".
    {"subclass": "giant-bgg", "class": "barbarian", "feature": "giant-bgg-6-elemental-cleaver", "name": "Elemental Cleaver",
     "uses": None, "recharge": None, "dice": "@cleaver_dice", "level_vars": {"cleaver_dice": ELEMENTAL_CLEAVER_DICE_2014},
     "note": "When you enter your rage, infuse a weapon you hold with acid, cold, fire, thunder, or lightning damage: it "
             "deals an extra {cleaver_dice} of that type, gains the thrown property (range 20/60 feet) and returns to "
             "your hand after it hits or misses; a bonus action changes the type",
     "quotes": (("giant-bgg-6-elemental-cleaver", "acid, cold, fire, thunder, or lightning"),
                ("giant-bgg-6-elemental-cleaver", "a normal range of 20 feet and a long range of 60 feet"),
                ("giant-bgg-6-elemental-cleaver", "you can use a bonus action to change the infused weapon's current damage type"),
                ("giant-bgg-14-demiurgic-colossus", "the extra damage dealt by your Elemental Cleaver feature increases to 2d6"))},
    # Mighty Impel: "As a bonus action while raging, you can choose one Medium or smaller creature within your reach and move
    # it to an unoccupied space you can see within 30 feet of yourself. An unwilling creature must succeed on a Strength
    # saving throw (DC equals 8 + your proficiency bonus + your Strength modifier)"
    {"subclass": "giant-bgg", "class": "barbarian", "feature": "giant-bgg-10-mighty-impel", "name": "Mighty Impel",
     "uses": None, "recharge": None,
     "note": "Bonus action while raging: move one Medium or smaller creature within your reach to an unoccupied space "
             "you can see within 30 feet; an unwilling creature makes a Strength saving throw (DC {dc_str}) to avoid "
             "it; a creature left unsupported falls and lands prone",
     "quotes": (("giant-bgg-10-mighty-impel", "choose one Medium or smaller creature within your reach and move it to an unoccupied space you can see within 30 feet of yourself"),
                ("giant-bgg-10-mighty-impel", "(DC equals 8 + your proficiency bonus + your Strength modifier)"))},
    # ---- Barbarian: Path of the Storm Herald (XGE)
    # Storm Aura: "The aura extends 10 feet from you ... the DC equals 8 + your proficiency bonus + your Constitution
    # modifier." Desert 2 fire damage (3 / 4 / 5 / 6 at 5 / 10 / 15 / 20), Sea 1d6 lightning, Dexterity save (2d6 / 3d6 /
    # 4d6 at 10 / 15 / 20), Tundra 2 temporary hit points (3 / 4 / 5 / 6). Raging Storm (14), Desert: "fire damage equal to
    # half your barbarian level." The chosen environment is not tracked, so all three are listed.
    {"subclass": "storm-herald-xge", "class": "barbarian", "feature": "storm-herald-xge-3-storm-aura", "name": "Storm Aura",
     "uses": None, "recharge": None,
     "level_vars": {"desert": STORM_AURA_DESERT_2014, "sea": STORM_AURA_SEA_2014, "tundra": STORM_AURA_TUNDRA_2014},
     "note": "While you rage, an aura extends 10 feet from you (not through cover); activate its effect when you rage and "
             "again on each of your turns as a bonus action; saving throw DC {dc_con}. Desert: all other creatures in the "
             "aura take {desert} fire damage. Sea: one other creature you can see in the aura makes a Dexterity saving "
             "throw, taking {sea} lightning damage on a failure, half on a success. Tundra: each creature of your choice "
             "in the aura gains {tundra} temporary hit points",
     "extras": (("storm-herald-xge-14-raging-storm", "Raging Storm, desert: when a creature in your aura hits you, use "
                 "your reaction to force a Dexterity saving throw, a failure takes fire damage equal to half your "
                 "barbarian level ({half_level}); sea: when you hit a creature in your aura, use your reaction to force "
                 "a Strength saving throw or it is knocked prone; tundra: when the aura effect activates, one creature "
                 "you choose in it makes a Strength saving throw or its speed is 0 until the start of your next turn"),),
     "quotes": (("storm-herald-xge-3-storm-aura", "The aura extends 10 feet from you in every direction"),
                ("storm-herald-xge-3-storm-aura", "the DC equals 8 + your proficiency bonus + your Constitution modifier"),
                ("storm-herald-xge-3-storm-aura", "all other creatures in your aura take 2 fire damage each"),
                ("storm-herald-xge-3-storm-aura", "The target must make a Dexterity saving throw. The target takes 1d6 lightning damage on a failed save, or half as much damage on a successful one."),
                ("storm-herald-xge-3-storm-aura", "each creature of your choice in your aura gains 2 temporary hit points"),
                ("storm-herald-xge-14-raging-storm", "the creature takes fire damage equal to half your barbarian level"))},
    # ---- Barbarian: Path of Wild Magic (TCE)
    # Magic Awareness: "you know the location of any spell or magic item within 60 feet of you that isn't behind Cover ...
    # a number of times equal to your proficiency bonus ... long rest."
    {"subclass": "wild-magic-tce", "class": "barbarian", "feature": "wild-magic-tce-3-magic-awareness",
     "name": "Magic Awareness", "uses": "@pb", "recharge": "long",
     "note": "Action: until the end of your next turn you know the location of any spell or magic item within 60 feet "
             "that isn't behind cover, and the school of magic of a spell you sense",
     "quotes": (("wild-magic-tce-3-magic-awareness", "you know the location of any spell or magic item within 60 feet of you that isn't behind Cover"),
                ("wild-magic-tce-3-magic-awareness", "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))},
    # Wild Surge: "When you enter your rage, roll on the Wild Magic table ... If the effect requires a saving throw, the DC
    # equals 8 + your proficiency bonus + your Constitution modifier."
    {"subclass": "wild-magic-tce", "class": "barbarian", "feature": "wild-magic-tce-3-wild-surge", "name": "Wild Surge",
     "uses": None, "recharge": None,
     "note": "When you enter your rage, roll a d8 on the Wild Magic table for a magical effect; saving throw DC {dc_con}",
     "quotes": (("wild-magic-tce-3-wild-surge", "When you enter your rage, roll on the Wild Magic table to determine the magical effect produced"),
                ("wild-magic-tce-3-wild-surge", "the DC equals 8 + your proficiency bonus + your Constitution modifier"),
                ("wild-magic-tce-3-wild-surge", "Wild Magic d8"))},
    # Bolstering Magic: "As an action, you can touch one creature ... For 10 minutes, the creature can roll a d3 whenever
    # making an attack roll or an ability check ... Roll a d3. The creature regains one expended spell slot, the level of which
    # equals the number rolled or lower ... a number of times equal to your proficiency bonus ... long rest."
    {"subclass": "wild-magic-tce", "class": "barbarian", "feature": "wild-magic-tce-6-bolstering-magic",
     "name": "Bolstering Magic", "uses": "@pb", "recharge": "long",
     "note": "Action, touch one creature (yourself included): for 10 minutes it adds a d3 to attack rolls and ability "
             "checks, or roll a d3 and it regains an expended spell slot of that level or lower (once per creature "
             "until a long rest)",
     "quotes": (("wild-magic-tce-6-bolstering-magic", "For 10 minutes, the creature can roll a d3 whenever making an attack roll or an ability check and add the number rolled to the d20 roll"),
                ("wild-magic-tce-6-bolstering-magic", "The creature regains one expended spell slot, the level of which equals the number rolled or lower"),
                ("wild-magic-tce-6-bolstering-magic", "You can take this action a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))},
    # ---- Barbarian: Path of the Zealot (XGE)
    # Divine Fury: "While you're raging, the first creature you hit on each of your turns with a weapon attack takes extra
    # damage equal to 1d6 + half your barbarian level. The extra damage is necrotic or radiant"
    {"subclass": "zealot-xge", "class": "barbarian", "feature": "zealot-xge-3-divine-fury", "name": "Divine Fury",
     "uses": None, "recharge": None,
     "note": "While raging, the first creature you hit on each of your turns with a weapon attack takes extra damage of "
             "1d6 + {half_level} (half your Barbarian level), necrotic or radiant (chosen when you gain the feature)",
     "quotes": (("zealot-xge-3-divine-fury", "the first creature you hit on each of your turns with a weapon attack takes extra damage equal to 1d6 + half your barbarian level"),
                ("zealot-xge-3-divine-fury", "The extra damage is necrotic or radiant"))},
    # Fanatical Focus: "If you fail a saving throw while you're raging, you can reroll it, and you must use the new roll. You
    # can use this ability only once per rage." (a rage is not a rest, so no recharge is modelled)
    {"subclass": "zealot-xge", "class": "barbarian", "feature": "zealot-xge-6-fanatical-focus", "name": "Fanatical Focus",
     "uses": None, "recharge": None,
     "note": "If you fail a saving throw while raging you can reroll it and must use the new roll; once per rage",
     "quotes": (("zealot-xge-6-fanatical-focus", "If you fail a saving throw while you're raging, you can reroll it, and you must use the new roll"),
                ("zealot-xge-6-fanatical-focus", "You can use this ability only once per rage"))},
    # Zealous Presence: "Up to ten other creatures of your choice within 60 feet of you that can hear you gain advantage on
    # attack rolls and saving throws until the start of your next turn. Once you use this feature, you can't use it again until
    # you finish a long rest."
    {"subclass": "zealot-xge", "class": "barbarian", "feature": "zealot-xge-10-zealous-presence",
     "name": "Zealous Presence", "uses": 1, "recharge": "long",
     "note": "Bonus action: up to ten other creatures of your choice within 60 feet that can hear you have advantage on "
             "attack rolls and saving throws until the start of your next turn",
     "quotes": (("zealot-xge-10-zealous-presence", "Up to ten other creatures of your choice within 60 feet of you that can hear you gain advantage on attack rolls and saving throws until the start of your next turn"),
                ("zealot-xge-10-zealous-presence", "Once you use this feature, you can't use it again until you finish a long rest"))},
    # ---- Bard: College of Creation (TCE)
    # Performance of Creation: "The gp value of the item can't be more than 20 times your bard level, and the item must be
    # Medium or smaller. ... disappears after a number of hours equal to your proficiency bonus. ... can't do so again until you
    # finish a long rest, unless you expend a spell slot of 2nd level or higher ... Large at 6th level and Huge at 14th." Creative
    # Crescendo (14): "The number of items equals your Charisma modifier (minimum of two items)."
    {"subclass": "creation-tce", "class": "bard", "feature": "creation-tce-3-performance-of-creation",
     "name": "Performance of Creation", "uses": 1, "recharge": "long",
     "level_vars": {"size": PERFORMANCE_OF_CREATION_SIZE_2014},
     "note": "Action: create one nonmagical item worth up to {twenty_level} gp (20 x Bard level), {size} or smaller, in an "
             "unoccupied space within 10 feet; it disappears after {pb} hours (proficiency bonus); use it again before a "
             "long rest by expending a spell slot of 2nd level or higher; only one such item at a time",
     "extras": (("creation-tce-14-creative-crescendo", "Creative Crescendo: create up to {cha_min2} items at once (Charisma "
                 "modifier, minimum 2), only one of the maximum size and the rest Small or Tiny, with no gp limit"),),
     "quotes": (("creation-tce-3-performance-of-creation", "The gp value of the item can't be more than 20 times your bard level"),
                ("creation-tce-3-performance-of-creation", "The created item disappears after a number of hours equal to your proficiency bonus"),
                ("creation-tce-3-performance-of-creation", "unless you expend a spell slot of 2nd level or higher to use this feature again"),
                ("creation-tce-14-creative-crescendo", "The number of items equals your Charisma modifier (minimum of two items)"))},
    # Animating Performance: "animate one Large or smaller nonmagical item within 30 feet of you ... Dancing Item stat block,
    # which uses your proficiency bonus (PB) ... lives for 1 hour ... can't do so again until you finish a long rest, unless you
    # expend a spell slot of 3rd level or higher"
    {"subclass": "creation-tce", "class": "bard", "feature": "creation-tce-6-animating-performance",
     "name": "Animating Performance", "uses": 1, "recharge": "long",
     "note": "Action: animate one Large or smaller nonmagical item within 30 feet (Dancing Item stat block, PB {pb}); it "
             "lives for 1 hour; use it again before a long rest by expending a spell slot of 3rd level or higher; only "
             "one animated item at a time",
     "quotes": (("creation-tce-6-animating-performance", "animate one Large or smaller nonmagical item within 30 feet of you"),
                ("creation-tce-6-animating-performance", "It lives for 1 hour"),
                ("creation-tce-6-animating-performance", "unless you expend a spell slot of 3rd level or higher to use this feature again"))},
    # ---- Bard: College of Eloquence (TCE)
    # Universal Speech: "choose one or more creatures within 60 feet of you, up to a number equal to your Charisma modifier
    # (minimum of one creature) ... for 1 hour. Once you use this feature, you can't use it again until you finish a long rest,
    # unless you expend a spell slot to use it again."
    {"subclass": "eloquence-tce", "class": "bard", "feature": "eloquence-tce-6-universal-speech",
     "name": "Universal Speech", "uses": 1, "recharge": "long",
     "note": "Action: up to {cha_min1} creature(s) within 60 feet (Charisma modifier, minimum 1) magically understand you "
             "for 1 hour; use it again before a long rest by expending a spell slot",
     "quotes": (("eloquence-tce-6-universal-speech", "choose one or more creatures within 60 feet of you, up to a number equal to your Charisma modifier (minimum of one creature)"),
                ("eloquence-tce-6-universal-speech", "for 1 hour"),
                ("eloquence-tce-6-universal-speech", "unless you expend a spell slot to use it again"))},
    # Infectious Inspiration: "you can use your reaction to encourage a different creature ... within 60 feet of you, giving it a
    # Bardic Inspiration die without expending any of your Bardic Inspiration uses. You can use this reaction a number of times
    # equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a long rest."
    {"subclass": "eloquence-tce", "class": "bard", "feature": "eloquence-tce-14-infectious-inspiration",
     "name": "Infectious Inspiration", "uses": "@cha_min1", "recharge": "long",
     "note": "Reaction: when a creature within 60 feet adds your Bardic Inspiration die to a roll and succeeds, give a "
             "different creature (not you) that can hear you within 60 feet a Bardic Inspiration die without expending "
             "any of your uses",
     "quotes": (("eloquence-tce-14-infectious-inspiration", "giving it a Bardic Inspiration die without expending any of your Bardic Inspiration uses"),
                ("eloquence-tce-14-infectious-inspiration", "You can use this reaction a number of times equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a long rest"))},
    # ---- Bard: College of Glamour (XGE)
    # Enthralling Performance: "If you perform for at least 1 minute ... choose a number of humanoids within 60 feet of you ...
    # up to a number equal to your Charisma modifier (minimum of one). Each target must succeed on a Wisdom saving throw against
    # your spell save DC or be charmed ... ends on a target after 1 hour ... until you finish a short or long rest."
    {"subclass": "glamour-xge", "class": "bard", "feature": "glamour-xge-3-enthralling-performance",
     "name": "Enthralling Performance", "uses": 1, "recharge": "short-or-long",
     "note": "Perform for at least 1 minute: up to {cha_min1} humanoid(s) within 60 feet (Charisma modifier, minimum 1) "
             "make a Wisdom saving throw (DC {dc_cha}) or are charmed by you for 1 hour (ends early if they take damage, "
             "you attack them or they see you attack their allies)",
     "quotes": (("glamour-xge-3-enthralling-performance", "If you perform for at least 1 minute"),
                ("glamour-xge-3-enthralling-performance", "up to a number equal to your Charisma modifier (minimum of one)"),
                ("glamour-xge-3-enthralling-performance", "Each target must succeed on a Wisdom saving throw against your spell save DC or be charmed by you"),
                ("glamour-xge-3-enthralling-performance", "This effect ends on a target after 1 hour"),
                ("glamour-xge-3-enthralling-performance", "you can't use it again until you finish a short or long rest"))},
    # Mantle of Majesty: "you cast command, without expending a spell slot, and you take on an appearance of unearthly beauty
    # for 1 minute ... Once you use this feature, you can't use it again until you finish a long rest."
    {"subclass": "glamour-xge", "class": "bard", "feature": "glamour-xge-6-mantle-of-majesty", "name": "Mantle of Majesty",
     "uses": 1, "recharge": "long",
     "note": "Bonus action: cast command without a spell slot and take on an appearance of unearthly beauty for 1 minute "
             "(concentration); cast command as a bonus action on each of your turns without a slot; a creature charmed "
             "by you automatically fails its save against it",
     "quotes": (("glamour-xge-6-mantle-of-majesty", "you cast command, without expending a spell slot, and you take on an appearance of unearthly beauty for 1 minute"),
                ("glamour-xge-6-mantle-of-majesty", "Any creature charmed by you automatically fails its saving throw against the command you cast with this feature"),
                ("glamour-xge-6-mantle-of-majesty", "Once you use this feature, you can't use it again until you finish a long rest"))},
    # Unbreakable Majesty: "as a bonus action, you can assume a magically majestic presence for 1 minute or until you are
    # incapacitated ... the attacker must make a Charisma saving throw against your spell save DC ... short or long rest."
    {"subclass": "glamour-xge", "class": "bard", "feature": "glamour-xge-14-unbreakable-majesty",
     "name": "Unbreakable Majesty", "uses": 1, "recharge": "short-or-long",
     "note": "Bonus action, 1 minute or until incapacitated: a creature attacking you for the first time on a turn makes "
             "a Charisma saving throw (DC {dc_cha}); on a failure it can't attack you that turn and must pick a new "
             "target; on a success it has disadvantage on its saving throws against your spells on your next turn",
     "quotes": (("glamour-xge-14-unbreakable-majesty", "as a bonus action, you can assume a magically majestic presence for 1 minute or until you are incapacitated"),
                ("glamour-xge-14-unbreakable-majesty", "the attacker must make a Charisma saving throw against your spell save DC"),
                ("glamour-xge-14-unbreakable-majesty", "you can't do so again until you finish a short or long rest"))},
    # ---- Bard: College of Spirits (VRGR)
    # Spirit Session: "You can conduct the ritual with a number of willing creatures equal to your proficiency bonus (including
    # yourself). ... a level equal to the number of creatures that conducted the ritual or less ... divination or necromancy.
    # ... Once you perform the ritual, you can't do so again until you start a long rest"
    {"subclass": "spirits-vrgr", "class": "bard", "feature": "spirits-vrgr-6-spirit-session", "name": "Spirit Session",
     "uses": 1, "recharge": "long",
     "note": "Hour-long ritual (during a short or long rest) with up to {pb} willing creatures including you (proficiency "
             "bonus): you temporarily learn one divination or necromancy spell from any class, of a level up to the "
             "number of participants and a level you can cast, until you start a long rest",
     "quotes": (("spirits-vrgr-6-spirit-session", "a number of willing creatures equal to your proficiency bonus (including yourself)"),
                ("spirits-vrgr-6-spirit-session", "of a level equal to the number of creatures that conducted the ritual or less"),
                ("spirits-vrgr-6-spirit-session", "it must be in the school of divination or necromancy"),
                ("spirits-vrgr-6-spirit-session", "Once you perform the ritual, you can't do so again until you start a long rest"))},
    # ---- Bard: College of Whispers (XGE)
    # Words of Terror: "If you speak to a humanoid alone for at least 1 minute ... Wisdom saving throw against your spell
    # save DC or be frightened of you or another creature of your choice ... for 1 hour ... short or long rest."
    {"subclass": "whispers-xge", "class": "bard", "feature": "whispers-xge-3-words-of-terror", "name": "Words of Terror",
     "uses": 1, "recharge": "short-or-long",
     "note": "Speak to a humanoid alone for at least 1 minute: it makes a Wisdom saving throw (DC {dc_cha}) or is "
             "frightened of you or another creature of your choice for 1 hour (until it is attacked or damaged or sees "
             "its allies attacked or damaged)",
     "quotes": (("whispers-xge-3-words-of-terror", "If you speak to a humanoid alone for at least 1 minute"),
                ("whispers-xge-3-words-of-terror", "the target must succeed on a Wisdom saving throw against your spell save DC"),
                ("whispers-xge-3-words-of-terror", "The target is frightened in this way for 1 hour"),
                ("whispers-xge-3-words-of-terror", "you can't use it again until you finish a short or long rest"))},
    # Mantle of Whispers: "When a humanoid dies within 30 feet of you, you can magically capture its shadow using your
    # reaction. ... This disguise lasts for 1 hour ... You gain a +5 bonus to your check. ... short or long rest."
    {"subclass": "whispers-xge", "class": "bard", "feature": "whispers-xge-6-mantle-of-whispers",
     "name": "Mantle of Whispers", "uses": 1, "recharge": "short-or-long",
     "note": "Reaction: capture the shadow of a humanoid that dies within 30 feet (kept until used or a long rest); as an "
             "action, wear its likeness for 1 hour or until you end it as a bonus action; a creature that sees through "
             "the disguise must beat your Charisma (Deception) check, which has a +5 bonus",
     "quotes": (("whispers-xge-6-mantle-of-whispers", "When a humanoid dies within 30 feet of you, you can magically capture its shadow using your reaction"),
                ("whispers-xge-6-mantle-of-whispers", "This disguise lasts for 1 hour"),
                ("whispers-xge-6-mantle-of-whispers", "You gain a +5 bonus to your check"),
                ("whispers-xge-6-mantle-of-whispers", "you can't capture another one with it until you finish a short or long rest"))},
    # Shadow Lore: "magically whisper a phrase that only one creature of your choice within 30 feet of you can hear. The target
    # must make a Wisdom saving throw against your spell save DC. ... charmed by you for the next 8 hours ... long rest."
    {"subclass": "whispers-xge", "class": "bard", "feature": "whispers-xge-14-shadow-lore", "name": "Shadow Lore",
     "uses": 1, "recharge": "long",
     "note": "Action: whisper to one creature within 30 feet that shares a language with you and can hear you; it makes a "
             "Wisdom saving throw (DC {dc_cha}) or is charmed by you for 8 hours (or until you or your allies attack, "
             "damage or force a saving throw on it) and obeys your commands short of risking its life",
     "quotes": (("whispers-xge-14-shadow-lore", "one creature of your choice within 30 feet of you can hear"),
                ("whispers-xge-14-shadow-lore", "The target must make a Wisdom saving throw against your spell save DC"),
                ("whispers-xge-14-shadow-lore", "the target is charmed by you for the next 8 hours"),
                ("whispers-xge-14-shadow-lore", "Once you use this feature, you can't use it again until you finish a long rest"))},
)

SUBCLASS_NOTES_2014_BOOKS: tuple[dict, ...] = (
    # ---- Bard notes on Bardic Inspiration
    # Mote of Potential: the mote's Constitution saving throw is "against your spell save DC", thunder damage equal to the
    # number rolled; "temporary hit points equal to the number rolled on the Bardic Inspiration die plus your Charisma modifier
    # (minimum of 1 temporary hit point)".
    {"subclass": "creation-tce", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "creation-tce-3-mote-of-potential", "name": "Mote of Potential",
     "note": "Mote of Potential: when you give a Bardic Inspiration die, a mote orbits the creature; on an ability check "
             "it rolls the die twice and picks one, on an attack roll the target and creatures of your choice within 5 "
             "feet of it make a Constitution saving throw (DC {dc_cha}) or take thunder damage equal to the roll, on a "
             "saving throw it gains temporary hit points equal to the roll + {cha_min1} (Charisma modifier, minimum 1)",
     "quotes": (("creation-tce-3-mote-of-potential", "must succeed on a Constitution saving throw against your spell save DC or take thunder damage equal to the number rolled on the Bardic Inspiration die"),
                ("creation-tce-3-mote-of-potential", "temporary hit points equal to the number rolled on the Bardic Inspiration die plus your Charisma modifier (minimum of 1 temporary hit point)"),
                ("creation-tce-3-mote-of-potential", "the creature can roll the Bardic Inspiration die again and choose which roll to use"))},
    # Unsettling Words: "As a bonus action, you can expend one use of your Bardic Inspiration and choose one creature you can
    # see within 60 feet of you. Roll the Bardic Inspiration die. The creature must subtract the number rolled from the next
    # saving throw it makes before the start of your next turn."
    {"subclass": "eloquence-tce", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "eloquence-tce-3-unsettling-words", "name": "Unsettling Words",
     "note": "Unsettling Words (bonus action, 60 feet): expend a use to roll the die; one creature you can see subtracts "
             "it from the next saving throw it makes before the start of your next turn",
     "quotes": (("eloquence-tce-3-unsettling-words", "you can expend one use of your Bardic Inspiration and choose one creature you can see within 60 feet of you"),
                ("eloquence-tce-3-unsettling-words", "The creature must subtract the number rolled from the next saving throw it makes before the start of your next turn"))},
    # Mantle of Inspiration: "you can expend one use of your Bardic Inspiration to grant yourself a wondrous appearance ...
    # up to a number equal to your Charisma modifier (minimum of one). Each of them gains 5 temporary hit points ... increasing
    # to 8 at 5th level, 11 at 10th level, and 14 at 15th level." (reaction: move up to its speed without provoking)
    {"subclass": "glamour-xge", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "glamour-xge-3-mantle-of-inspiration", "name": "Mantle of Inspiration",
     "level_vars": {"thp": MANTLE_OF_INSPIRATION_THP_2014},
     "note": "Mantle of Inspiration (bonus action): expend a use to give up to {cha_min1} creature(s) you can see within "
             "60 feet that can see you (Charisma modifier, minimum 1) {thp} temporary hit points each; each can use its "
             "reaction to move up to its speed without provoking opportunity attacks",
     "quotes": (("glamour-xge-3-mantle-of-inspiration", "you can expend one use of your Bardic Inspiration to grant yourself a wondrous appearance"),
                ("glamour-xge-3-mantle-of-inspiration", "up to a number equal to your Charisma modifier (minimum of one)"),
                ("glamour-xge-3-mantle-of-inspiration", "it can immediately use its reaction to move up to its speed, without provoking opportunity attacks"))},
    # Tales from Beyond: "you can use a bonus action to expend one use of your Bardic Inspiration and roll on the Spirit Tales
    # table using your Bardic Inspiration die ... within 30 feet ... If the tale requires a saving throw, the DC equals your spell
    # save DC."
    {"subclass": "spirits-vrgr", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "spirits-vrgr-3-tales-from-beyond", "name": "Tales from Beyond",
     "note": "Tales from Beyond (bonus action, holding your Spiritual Focus): expend a use and roll the Bardic "
             "Inspiration die on the Spirit Tales table (12 tales); keep the tale until you bestow it with an action on "
             "a creature you can see within 30 feet or finish a short or long rest; only one tale at a time; saving "
             "throw DC {dc_cha}",
     "quotes": (("spirits-vrgr-3-tales-from-beyond", "you can use a bonus action to expend one use of your Bardic Inspiration and roll on the Spirit Tales table using your Bardic Inspiration die"),
                ("spirits-vrgr-3-tales-from-beyond", "choose one creature you can see within 30 feet of you"),
                ("spirits-vrgr-3-tales-from-beyond", "If the tale requires a saving throw, the DC equals your spell save DC"))},
    # Blade Flourish: "your walking speed increases by 10 feet until the end of the turn ... You can expend one use of your
    # Bardic Inspiration to cause the weapon to deal extra damage ... equals the number you roll on the Bardic Inspiration die."
    # Master's Flourish (14): "you can roll a d6 and use it instead of expending a Bardic Inspiration die."
    {"subclass": "swords-xge", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "swords-xge-3-blade-flourish", "name": "Blade Flourish",
     "note": "Blade Flourish: when you take the Attack action your walking speed increases by 10 feet until the end of the "
             "turn; when a weapon attack hits, expend a use (once per turn) for extra damage equal to the die: "
             "Defensive (also add the die to your AC until your next turn), Slashing (also hits another creature within "
             "5 feet) or Mobile (push the target 5 feet plus the die, then move up to your speed with your reaction)",
     "extras": (("swords-xge-14-masters-flourish", "Master's Flourish: roll a d6 and use it instead of expending a "
                 "Bardic Inspiration die"),),
     "quotes": (("swords-xge-3-blade-flourish", "your walking speed increases by 10 feet until the end of the turn"),
                ("swords-xge-3-blade-flourish", "You can use only one Blade Flourish option per turn"),
                ("swords-xge-3-blade-flourish", "The damage equals the number you roll on the Bardic Inspiration die"),
                ("swords-xge-14-masters-flourish", "you can roll a d6 and use it instead of expending a Bardic Inspiration die"))},
    # Psychic Blades: "When you hit a creature with a weapon attack, you can expend one use of your Bardic Inspiration to deal
    # an extra 2d6 psychic damage to that target. You can do so only once per round on your turn. ... 3d6 at 5th level, 5d6 at
    # 10th level, and 8d6 at 15th level."
    {"subclass": "whispers-xge", "class": "bard", "target": "bard:bardic-inspiration",
     "feature": "whispers-xge-3-psychic-blades", "name": "Psychic Blades",
     "level_vars": {"psychic": PSYCHIC_BLADES_DICE_2014},
     "note": "Psychic Blades: when you hit a creature with a weapon attack, expend a use to deal an extra {psychic} "
             "psychic damage; only once per round on your turn",
     "quotes": (("whispers-xge-3-psychic-blades", "you can expend one use of your Bardic Inspiration to deal an extra 2d6 psychic damage to that target"),
                ("whispers-xge-3-psychic-blades", "You can do so only once per round on your turn"))},
)

# Zealot Warrior of the Gods: "a pool of four d12s ... The pool's maximum number of dice increases by one when you
# reach Barbarian levels 6 (5 dice), 12 (6 dice), and 17 (7 dice)." (class level, dice), pinned against
# zealot-xphb-3-warrior-of-the-gods.
ZEALOT_WARRIOR_DICE_2024 = ((3, 4), (6, 5), (12, 6), (17, 7))

# Land Druid Land's Aid: 2d6, "The damage and healing increase by 1d6 when you reach Druid levels 10 (3d6) and 14 (4d6)."
# (class level, d6 count), pinned against land-xphb-3-lands-aid.
LANDS_AID_DICE_2024 = ((3, 2), (10, 3), (14, 4))

# Wizard Signature Spells (XPHB, level 20), built from the picked spells, not from a table row: "Choose two level
# 3 spells in your spellbook as your signature spells. You always have these spells prepared, and you can cast
# each of them once at level 3 without expending a spell slot. When you do so, you can't cast them in this way
# again until you finish a Short or Long Rest."
SIGNATURE_SPELLS_2024 = {"feature": "xphb-wizard-20-signature-spells", "choice": "class:wizard:20:signature-spells",
                         "recharge": "short-or-long"}

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


# ---- XPHB (2024) Eldritch Invocation effects (C7b) ---------------------------------------------
# Keyed by the XPHB feature id `opt-<slug>-xphb`. Holds ONLY what the imported record does not carry:
# innate spells (with frequency) and senses come from the record itself (class_choices_2024.invocation_effect).
# Texts read from catalog.features on 2026-10-10 (tests/test_invocation_effects_2024.py re-checks them).
# Keys as INVOCATION_EFFECTS, plus swim_equals_walk. Notes may use {cha_names} (max(1, CHA modifier)) and
# {spear_range} (30 x Warlock level); they are formatted by class_resources._warlock (resource notes) only.
# E6: Pact of the Chain's data says "ritual", the text "cast it as a Magic action without expending a spell
# slot", so it is an at-will innate entry (the engine maps "ritual" to at-will) with the note below.
# Not here (C7c): Pact of the Tome, Lessons of the First Ones.
_XPHB_INV = "opt-{}-xphb"
INVOCATION_EFFECTS_2024: dict[str, dict] = {
    _XPHB_INV.format("armor-of-shadows"): {"ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True}},
    _XPHB_INV.format("devils-sight"): {"senses": {"devilsSight": 120}},
    _XPHB_INV.format("gift-of-the-depths"): {
        "swim_equals_walk": True, "note": "You can breathe underwater and have a Swim Speed equal to your Speed."},
    _XPHB_INV.format("eldritch-mind"): {"note": "Advantage on Constitution saving throws to maintain Concentration."},
    _XPHB_INV.format("fiendish-vigor"): {
        "note": "On yourself; you don't roll the die for the Temporary Hit Points, you get the highest number on the die."},
    _XPHB_INV.format("one-with-shadows"): {
        "note": "On yourself, while you are in an area of Dim Light or Darkness."},
    _XPHB_INV.format("pact-of-the-chain"): {
        "note": "Magic action, no spell slot. Special forms: Imp, Pseudodragon, Quasit, Skeleton, Slaad Tadpole, "
                "Sphinx of Wonder, Sprite, Venomous Snake. When you take the Attack action you can forgo one of your "
                "attacks so the familiar attacks with its Reaction."},
    _XPHB_INV.format("pact-of-the-blade"): {
        "note": "Bonus Action: conjure a pact weapon (Simple or Martial Melee) or bond with a magic weapon you touch. "
                "You are proficient with it and can use it as a Spellcasting Focus. Attack and damage rolls can use "
                "Charisma, and it can deal Necrotic, Psychic or Radiant damage or its normal type."},
    _XPHB_INV.format("thirsting-blade"): {
        "note": "Extra Attack with your pact weapon only: attack twice instead of once with the Attack action. "
                "It doesn't give additional attacks if you also have Extra Attack (PHB 2024 Multiclassing)."},
    _XPHB_INV.format("devouring-blade"): {"note": "The Extra Attack of Thirsting Blade confers two extra attacks rather than one."},
    _XPHB_INV.format("eldritch-smite"): {
        "note": "Once per turn on a pact weapon hit: expend a Pact Magic slot for an extra 1d8 Force damage plus 1d8 per "
                "slot level; the target is Prone if Huge or smaller."},
    _XPHB_INV.format("lifedrinker"): {
        "note": "Once per turn on a pact weapon hit: extra 1d6 Necrotic, Psychic or Radiant damage, and you can expend a "
                "Hit Point Die to regain the roll plus your Constitution modifier (minimum 1) Hit Points."},
    _XPHB_INV.format("gaze-of-two-minds"): {
        "note": "Bonus Action: touch a willing creature and perceive through its senses until the end of your next turn "
                "(maintain with a Bonus Action each turn); you can cast spells from its space within 60 feet."},
    _XPHB_INV.format("gift-of-the-protectors"): {
        "note": "Book of Shadows page holds {cha_names} {cha_names_word} (Charisma modifier, minimum one). A named creature "
                "reduced to 0 Hit Points but not killed drops to 1 instead; once triggered, no one benefits until a Long Rest."},
    _XPHB_INV.format("investment-of-the-chain-master"): {
        "note": "Your Find Familiar familiar gains a 40 ft Fly or Swim Speed, Bonus Action Attack command, Necrotic or "
                "Radiant damage option, your spell save DC, and Reaction Resistance for it."},
    _XPHB_INV.format("agonizing-blast"): {"resource_bonus": {"name": "Agonizing Blast", "ability": "CHA", "spell": None}},
    _XPHB_INV.format("eldritch-spear"): {
        "note": "One known damaging Warlock cantrip with range 10+ feet: its range increases by 30 x Warlock level = {spear_range} feet."},
    _XPHB_INV.format("repelling-blast"): {
        "note": "One known Warlock cantrip that requires an attack roll: when you hit a Large or smaller creature you can push it up to 10 feet straight away."},
}


# C7c: short notes added to the attack row of the Pact of the Blade weapon, by selected XPHB invocation id (the Blade's own
# note is attacks.PACT_WEAPON_NOTE; texts as in
# INVOCATION_EFFECTS_2024 and the XPHB records, read 2026-10-11). The numbers on the row are unchanged (information).
PACT_WEAPON_ROW_NOTES_2024: dict[str, str] = {
    _XPHB_INV.format("thirsting-blade"): "Thirsting Blade: attack twice with the Attack action (not on top of Extra Attack)",
    _XPHB_INV.format("devouring-blade"): "Devouring Blade: Thirsting Blade confers two extra attacks rather than one",
    _XPHB_INV.format("eldritch-smite"): "Eldritch Smite: once per turn, expend a Pact Magic slot for +1d8 Force (+1d8 per slot level), Prone if Huge or smaller",
    _XPHB_INV.format("lifedrinker"): "Lifedrinker: once per turn +1d6 Necrotic, Psychic or Radiant; spend a Hit Point Die to heal",
}


# ---- 2024 class option choices (C6a orders, C6c-2 Blessed Strikes / Elemental Fury) -------------
# XPHB class features that offer a pick between sibling feature records (ruleset "2024" only).
# Texts read from the imported catalog.features on 2026-10-10:
#   Protector   "you gain proficiency with Martial weapons and training with Heavy armor."
#   Thaumaturge "You know one extra cantrip from the Cleric spell list. In addition ... a bonus
#                to your Intelligence (Arcana or Religion) checks. The bonus equals your Wisdom
#                modifier (minimum of +1)."
#   Warden      "... proficiency with Martial weapons and training with Medium armor."
#   Magician    "You know one extra cantrip from the Druid spell list. ... Intelligence (Arcana or
#                Nature) checks. The bonus equals your Wisdom modifier (minimum bonus of +1)."
#   Blessed Strikes (Cleric 7)  "You gain one of the following options of your choice (if you get either
#                option from a Cleric subclass in an older book, use only the option you choose for this
#                feature)."  Divine Strike: "extra 1d8 Necrotic or Radiant damage (your choice)" once per
#                turn on a weapon hit; Potent Spellcasting: "Add your Wisdom modifier to the damage you
#                deal with any Cleric cantrip." Improved Blessed Strikes (14): Divine Strike "increases to
#                2d8"; Potent Spellcasting: temporary hit points "equal to twice your Wisdom modifier".
#   Elemental Fury (Druid 7)    "You gain one of the following options of your choice."  Primal Strike:
#                "extra 1d8 Cold, Fire, Lightning, or Thunder damage (choose when you hit)" once per turn on
#                a weapon (or Wild Shape Beast form) hit; Potent Spellcasting: "... any Druid cantrip."
#                Improved Elemental Fury (15): Potent: a cantrip with range 10 feet or greater gains 300
#                feet; Primal Strike "increases to 2d8".
# Keyed by (class, slug). Keys: feature (XPHB feature record that must exist), label, level (the class level
# the card appears at), cid (the stored-pick key; the C6a cids keep their historic shape), options
# {catalog feature index: effect}. Effect keys: proficiencies (ids of the shared proficiency sets),
# extra_cantrips (count bump on the class cantrip card), skill_bonus {skills, ability, minimum}: bonus =
# max(minimum, ability modifier) added to those skills' totals (C6a); divine_strike / primal_strike
# {dice_by_level {class level: dice}, types} and potent_spellcasting {class, improved_level} are read by class_resources (C6c-2, decision E3: resources + attack-row notes).
CLASS_OPTION_CHOICES_2024: dict[tuple[str, str], dict] = {
    ("cleric", "divine-order"): {
        "feature": "xphb-cleric-1-divine-order", "label": "Divine Order", "level": 1,
        "cid": "class:cleric:1:divine-order",
        "options": {
            "xphb-cleric-1-protector": {"proficiencies": ["martial-weapons", "heavy-armor"]},
            "xphb-cleric-1-thaumaturge": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-religion"], "ability": "WIS", "minimum": 1},
            },
        },
    },
    ("druid", "primal-order"): {
        "feature": "xphb-druid-1-primal-order", "label": "Primal Order", "level": 1,
        "cid": "class:druid:1:primal-order",
        "options": {
            "xphb-druid-1-magician": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-nature"], "ability": "WIS", "minimum": 1},
            },
            "xphb-druid-1-warden": {"proficiencies": ["martial-weapons", "medium-armor"]},
        },
    },
    ("cleric", "blessed-strikes"): {
        "feature": "xphb-cleric-7-blessed-strikes", "label": "Blessed Strikes", "level": 7,
        "cid": "class:cleric:7:feature:xphb-cleric-7-blessed-strikes",
        "options": {
            "xphb-cleric-7-divine-strike": {
                "divine_strike": {"dice_by_level": {7: "1d8", 14: "2d8"}, "types": "Necrotic or Radiant"}},
            "xphb-cleric-7-potent-spellcasting": {
                "potent_spellcasting": {"class": "Cleric", "improved_level": 14}},
        },
    },
    ("druid", "elemental-fury"): {
        "feature": "xphb-druid-7-elemental-fury", "label": "Elemental Fury", "level": 7,
        "cid": "class:druid:7:feature:xphb-druid-7-elemental-fury",
        "options": {
            "xphb-druid-7-potent-spellcasting": {
                "potent_spellcasting": {"class": "Druid", "improved_level": 15}},
            "xphb-druid-7-primal-strike": {
                "primal_strike": {"dice_by_level": {7: "1d8", 15: "2d8"}, "types": "Cold, Fire, Lightning, or Thunder"}},
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
    "sorcerer": ("metamagic-1", "metamagic-2", "metamagic-3"),
    "warlock": ("eldritch-invocations", "pact-boon"),  # C7a: the XPHB card holds the Pacts as invocations
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


# RP12 (F1, E13): subclass proficiency picks, ruleset "2024" only. Each entry names the XPHB subclass feature record
# (its own `level` is the first level of the card; the class and subclass come from the record too) and what is
# picked. `kind`: "skills" (`pool`: "any" = the 18 skills, "class-level-1:<class>" = the skills of that class's 2024
# level 1 list, or an explicit skill-id tuple), "tool" (`pool`: "artisans-tools"), "save" (`fixed` = the saving throw
# the feature grants outright, `alternatives` = the saves offered instead when `fixed` is already proficient at the
# card's position). `cid`: "feature" -> `class:<cls>:<lvl>:feature:<fid>`, "tool-choice" ->
# `class:<cls>:<lvl>:tool-choice:<fid>` (a feature with two picks needs two cids; both attach to the feature's
# sheet row). `quote` is a verbatim sentence of the record (pinned by tests); `note` (+ `quote`) becomes a note-only
# class resource of the subclass.
SUBCLASS_PICKS_2024: tuple[dict, ...] = (
    {"subclass": "lore-xphb", "class": "bard", "feature": "lore-xphb-3-bonus-proficiencies",
     "kind": "skills", "pool": "any", "count": 3, "cid": "feature", "label": "Bonus Proficiencies",
     "quote": "You gain proficiency with three skills of your choice."},
    {"subclass": "battle-master-xphb", "class": "fighter", "feature": "battle-master-xphb-3-student-of-war",
     "kind": "tool", "pool": "artisans-tools", "count": 1, "cid": "tool-choice",
     "label": "Student of War: Artisan's Tools",
     "quote": "You gain proficiency with one type of Artisan's Tools of your choice"},
    {"subclass": "battle-master-xphb", "class": "fighter", "feature": "battle-master-xphb-3-student-of-war",
     "kind": "skills", "pool": "class-level-1:fighter", "count": 1, "cid": "feature",
     "label": "Student of War: Skill",
     "quote": "one skill of your choice from the skills available to Fighters at level 1"},
    {"subclass": "fey-wanderer-xphb", "class": "ranger", "feature": "fey-wanderer-xphb-3-otherworldly-glamour",
     "kind": "skills", "pool": ("skill-deception", "skill-performance", "skill-persuasion"), "count": 1,
     "cid": "feature", "label": "Otherworldly Glamour",
     "quote": "You also gain proficiency in one of these skills of your choice: Deception, Performance, or Persuasion.",
     "note": "Whenever you make a Charisma check, add +{wis_min1} (your Wisdom modifier, minimum +1)",
     "note_quote": "Whenever you make a Charisma check, you gain a bonus to the check equal to your Wisdom modifier (minimum of +1)."},
    {"subclass": "gloom-stalker-xphb", "class": "ranger", "feature": "gloom-stalker-xphb-7-iron-mind",
     "kind": "save", "fixed": "WIS", "alternatives": ("INT", "CHA"), "count": 1, "cid": "feature",
     "label": "Iron Mind",
     "quote": "If you already have this proficiency, you instead gain proficiency in Intelligence or Charisma saving throws (your choice)."},
)



# RPX1 (Extra 1): the SRD College of Lore under mixed / 2014 (every ruleset but 2024). Same shape as
# SUBCLASS_PICKS_2024 (the RP12 positioned proficiency gate and card builder are shared); `feature` is the SRD
# feature record (`bonus-proficiencies`, Bard 3) and `quote` a verbatim part of its text (pinned by tests).
SUBCLASS_PICKS_2014: tuple[dict, ...] = (
    {"subclass": "lore", "class": "bard", "feature": "bonus-proficiencies",
     "kind": "skills", "pool": "any", "count": 3, "cid": "feature", "label": "Bonus Proficiencies",
     "quote": "you gain proficiency with three skills of your choice."},
)

# RPX1: SRD Lore Bard 6 Additional Magical Secrets ("you learn two spells of your choice from any class ... but don't
# count against the number of bard spells you know"). One card `class:bard:<feature level>:feature:<feature id>`,
# spells of any class list (cantrips included) of a level the Bard table can cast; the picks do not use Spells Known.
ADDITIONAL_SECRETS_2014: dict = {
    "subclass": "lore", "class": "bard", "feature": "additional-magical-secrets", "count": 2,
    "label": "Additional Magical Secrets",
    "quote": "you learn two spells of your choice from any class.",
}


# RP13 (F2, E13): editable build-time option cards of XPHB subclass features (ruleset 2024 only), keyed by the
# imported XPHB feature record id. Card cid `class:<cls>:<lvl>:feature:<feature id>` (level from the record), option
# ids `<feature id>--<option key>`, count 1, required. The option list is read from the record text: `quotes` are
# verbatim sentences of the record (pinned by tests), and an option marked `line` has its own "Name. text" line in
# the record (its description). Per option: `name` (label), `quote` (verbatim, pinned), and the effect keys the
# engine reads: `senses_additive`, `climb_equals_walk`, `swim_equals_walk`, `resist` (the class-effect keys of
# CLASS_FEATURE_EFFECTS_2024), `note` (a note-only subclass resource; `{cha:+d}` style fields come from the
# class-resource note variables) and `attack_note` (added to every weapon attack row). Deliberately NOT here:
# Elemental Epitome, Fiendish Resilience, Starry Form and The Third Eye (the pick lasts a turn, a rest or one use,
# so the feature text stays the note; see CLASS_FEATURE_NOTES_ONLY_2024), and the Beast Master stat blocks (not in the data: the card is a label only).
SUBCLASS_OPTIONS_2024: dict[str, dict] = {
    "hunter-xphb-3-hunters-prey": {
        "class": "ranger", "subclass": "hunter-xphb", "label": "Hunter's Prey",
        "quotes": ("You gain one of the following feature options of your choice. Whenever you finish a Short or Long "
                   "Rest, you can replace the chosen option with the other one.",),
        "options": {
            "colossus-slayer": {
                "name": "Colossus Slayer", "line": True,
                "quote": "Colossus Slayer. Your tenacity can wear down even the most resilient foes. When you hit a "
                         "creature with a weapon, the weapon deals an extra 1d8 damage to the target if it's missing "
                         "any of its Hit Points. You can deal this extra damage only once per turn.",
                "note": "Once per turn, a weapon hit deals an extra 1d8 damage if the target is missing any of its Hit Points",
                "attack_note": "Colossus Slayer: +1d8 once per turn if the target is missing any Hit Points"},
            "horde-breaker": {
                "name": "Horde Breaker", "line": True,
                "quote": "Horde Breaker. Once on each of your turns when you make an attack with a weapon, you can make "
                         "another attack with the same weapon against a different creature that is within 5 feet of "
                         "the original target, that is within the weapon's range, and that you haven't attacked this turn.",
                "note": "Once on each of your turns, make another attack with the same weapon against a different "
                        "creature within 5 feet of the original target"},
        }},
    "hunter-xphb-7-defensive-tactics": {
        "class": "ranger", "subclass": "hunter-xphb", "label": "Defensive Tactics",
        "quotes": ("You gain one of the following feature options of your choice. Whenever you finish a Short or Long "
                   "Rest, you can replace the chosen option with the other one.",),
        "options": {
            "escape-the-horde": {
                "name": "Escape the Horde", "line": True,
                "quote": "Escape the Horde. Opportunity Attacks have Disadvantage against you.",
                "note": "Opportunity Attacks have Disadvantage against you"},
            "multiattack-defense": {
                "name": "Multiattack Defense", "line": True,
                "quote": "Multiattack Defense. When a creature hits you with an attack roll, that creature has "
                         "Disadvantage on all other attack rolls against you this turn.",
                "note": "When a creature hits you with an attack roll, it has Disadvantage on all other attack rolls "
                        "against you this turn"},
        }},
    "wild-heart-xphb-6-aspect-of-the-wilds": {
        "class": "barbarian", "subclass": "wild-heart-xphb", "label": "Aspect of the Wilds",
        "quotes": ("You gain one of the following options of your choice. Whenever you finish a Long Rest, you can "
                   "change your choice.",),
        "options": {
            "owl": {"name": "Owl", "line": True,
                    "quote": "Owl. You have Darkvision with a range of 60 feet. If you already have Darkvision, its "
                             "range increases by 60 feet.",
                    "senses_additive": {"darkvision": 60}},
            "panther": {"name": "Panther", "line": True,
                        "quote": "Panther. You have a Climb Speed equal to your Speed.", "climb_equals_walk": True},
            "salmon": {"name": "Salmon", "line": True,
                       "quote": "Salmon. You have a Swim Speed equal to your Speed.", "swim_equals_walk": True},
        }},
    "draconic-xphb-6-elemental-affinity": {
        "class": "sorcerer", "subclass": "draconic-xphb", "label": "Elemental Affinity",
        "quotes": ("Choose one of those types: Acid, Cold, Fire, Lightning, or Poison.",
                   "You have Resistance to that damage type, and when you cast a spell that deals damage of that "
                   "type, you can add your Charisma modifier to one damage roll of that spell."),
        "options": {
            t: {"name": t.title(), "resist": [t],
                "note": f"Add your Charisma modifier ({{cha:+d}}) to one damage roll of a {t} damage spell"}
            for t in ("acid", "cold", "fire", "lightning", "poison")},
    },
    "beast-master-xphb-3-primal-companion": {
        "class": "ranger", "subclass": "beast-master-xphb", "label": "Primal Companion",
        "quotes": ("Choose its stat block: Beast of the Land, Beast of the Sea, or Beast of the Sky.",),
        "options": {
            "beast-of-the-land": {"name": "Beast of the Land"},
            "beast-of-the-sea": {"name": "Beast of the Sea"},
            "beast-of-the-sky": {"name": "Beast of the Sky"},
        }},
    "fey-wanderer-xphb-3-fey-wanderer-spells": {
        "class": "ranger", "subclass": "fey-wanderer-xphb", "label": "Feywild Gifts",
        "optional": True,  # RPF: a cosmetic table pick; an unpicked card does not block export
        "quotes": ("You also possess a fey blessing. Choose it from the Feywild Gifts table or determine it randomly.",),
        "options": {
            "gift-1": {"name": "Illusory butterflies flutter around you while you take a Short or Long Rest.",
                       "quote": "1 | Illusory butterflies flutter around you while you take a Short or Long Rest."},
            "gift-2": {"name": "Flowers bloom from your hair each dawn.",
                       "quote": "2 | Flowers bloom from your hair each dawn."},
            "gift-3": {"name": "You faintly smell of cinnamon, lavender, nutmeg, or another comforting herb or spice.",
                       "quote": "3 | You faintly smell of cinnamon, lavender, nutmeg, or another comforting herb or spice."},
            "gift-4": {"name": "Your shadow dances while no one is looking directly at it.",
                       "quote": "4 | Your shadow dances while no one is looking directly at it."},
            "gift-5": {"name": "Horns or antlers sprout from your head.",
                       "quote": "5 | Horns or antlers sprout from your head."},
            "gift-6": {"name": "Your skin and hair change color each dawn.",
                       "quote": "6 | Your skin and hair change color each dawn."},
        }},
    # RP17: Circle of the Land. The picked land decides the Circle Spells (catalog `spells_by_variant`, by `variant`) and
    # Nature's Ward's damage Resistance (`ward`: the XPHB feature record and, per option, its table row `ward_quote` and
    # `ward_resist`). "Whenever you finish a Long Rest, choose one type of land" - an editable card.
    "land-xphb-3-circle-of-the-land-spells": {
        "class": "druid", "subclass": "land-xphb", "label": "Circle Spells (land type)",
        "quotes": ("Whenever you finish a Long Rest, choose one type of land: arid, polar, temperate, or tropical.",
                   "you have the spells listed for your Druid level and lower prepared."),
        "ward": {"feature": "land-xphb-10-natures-ward",
                 "quotes": ("you have Resistance to a damage type associated with your current land choice in the "
                            "Circle Spells feature, as shown in the Nature's Ward table.",)},
        "options": {
            "arid": {"name": "Arid", "quote": "Arid Land", "variant": "arid",
                     "ward_quote": "Arid | Fire", "ward_resist": "fire"},
            "polar": {"name": "Polar", "quote": "Polar Land", "variant": "polar",
                      "ward_quote": "Polar | Cold", "ward_resist": "cold"},
            "temperate": {"name": "Temperate", "quote": "Temperate Land", "variant": "temperate",
                          "ward_quote": "Temperate | Lightning", "ward_resist": "lightning"},
            "tropical": {"name": "Tropical", "quote": "Tropical Land", "variant": "tropical",
                         "ward_quote": "Tropical | Poison", "ward_resist": "poison"},
        }},
}

# RP17 (F3, E13): XPHB subclass spell picks other than a named-variant table, ruleset 2024 only. Keyed by the XPHB
# subclass feature record id; the filters (school, class lists, level lists) and the counts come from the catalog
# subclass record's `spell_choices` (one entry per spell, with the class level it is gained at), the texts are pinned
# verbatim by tests.
#   savant       Wizard 3, "add them to your spellbook for free": count = entries reached (2 at level 3, +1 at every
#                level that opens a new spell slot level); options = Wizard spells of `school`, levels 1 .. the highest
#                Wizard slot level (the 2024 spellbook holds level 1+ spells, C4); not counted against the spellbook card.
#   cantrip      Illusionist 3 Improved Illusions: Minor Illusion is known (the subclass `spells` entry); when it is
#                already known one other Wizard cantrip, not counted against the cantrips known.
#   discoveries  Lore Bard 6: two spells of the Cleric / Druid / Wizard lists, cantrips or levels with Bard slots, always
#                prepared (reason "Magical Discoveries").
SUBCLASS_SPELL_PICKS_2024: dict[str, dict] = {
    "abjurer-xphb-3-abjuration-savant": {
        "kind": "savant", "class": "wizard", "subclass": "abjurer-xphb", "school": "abjuration",
        "quotes": ("Choose two Wizard spells from the Abjuration school, each of which must be no higher than level 2, "
                   "and add them to your spellbook for free.",
                   "whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell "
                   "from the Abjuration school to your spellbook for free. The chosen spell must be of a level for "
                   "which you have spell slots.")},
    "diviner-xphb-3-divination-savant": {
        "kind": "savant", "class": "wizard", "subclass": "diviner-xphb", "school": "divination",
        "quotes": ("Choose two Wizard spells from the Divination school, each of which must be no higher than level 2, "
                   "and add them to your spellbook for free.",
                   "whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell "
                   "from the Divination school to your spellbook for free. The chosen spell must be of a level for "
                   "which you have spell slots.")},
    "evoker-xphb-3-evocation-savant": {
        "kind": "savant", "class": "wizard", "subclass": "evoker-xphb", "school": "evocation",
        "quotes": ("Choose two Wizard spells from the Evocation school, each of which must be no higher than level 2, "
                   "and add them to your spellbook for free.",
                   "whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell "
                   "from the Evocation school to your spellbook for free. The chosen spell must be of a level for "
                   "which you have spell slots.")},
    "illusionist-xphb-3-illusion-savant": {
        "kind": "savant", "class": "wizard", "subclass": "illusionist-xphb", "school": "illusion",
        "quotes": ("Choose two Wizard spells from the Illusion school, each of which must be no higher than level 2, "
                   "and add them to your spellbook for free.",
                   "whenever you gain access to a new level of spell slots in this class, you can add one Wizard spell "
                   "from the Illusion school to your spellbook for free. The chosen spell must be of a level for "
                   "which you have spell slots.")},
    "illusionist-xphb-3-improved-illusions": {
        "kind": "cantrip", "class": "wizard", "subclass": "illusionist-xphb", "known": "minor-illusion",
        "quotes": ("You also know the Minor Illusion cantrip. If you already know it, you learn a different Wizard "
                   "cantrip of your choice. The cantrip doesn't count against your number of cantrips known.",)},
    "lore-xphb-6-magical-discoveries": {
        "kind": "discoveries", "class": "bard", "subclass": "lore-xphb", "lists": ("cleric", "druid", "wizard"),
        "grant": "Magical Discoveries",
        "quotes": ("You learn two spells of your choice. These spells can come from the Cleric, Druid, or Wizard spell "
                   "list or any combination thereof",
                   "A spell you choose must be a cantrip or a spell for which you have spell slots, as shown in the "
                   "Bard Features table.",
                   "You always have the chosen spells prepared,")},
}

# RP18 (F4): innate spells of the XPHB subclasses, ruleset "2024" only. Keyed by the XPHB feature record that grants the
# spell (its own `level` is the first class level). The catalog subclass record's `innate_spells` (converter) says which
# spell exists at which level; this table says what the text means and carries the verbatim quotes (pinned by
# tests/test_subclass_innate_2024.py).
#   mode        "innate": a sheet.innateSpells entry (source = the subclass name); "prepared": the spells are always
#               prepared (Great Old One Eldritch Hex: "You always have the Hex spell prepared." - not a free cast)
#   spells      spell slugs without the -xphb suffix
#   uses        the use rule as shown on the sheet; {cha_min1} = max(1, Charisma modifier)
#   ability     the casting ability; ability_from "text" (the feature states it), "data" (the 5etools block's `ability`)
#               or "class" (the feature says nothing: the class's spellcasting ability, checked by test)
# The RP11 resource rows (Steps of the Fey, Mantle of Majesty, Telekinetic Master, The Third Eye) stay the trackers.
SUBCLASS_INNATE_2024: dict[str, dict] = {
    "wild-heart-xphb-3-animal-speaker": {
        "class": "barbarian", "subclass": "wild-heart-xphb", "mode": "innate", "spells": ("beast-sense", "speak-with-animals"),
        "uses": "ritual only", "ability": "WIS", "ability_from": "text", "note": None,
        "quotes": ("You can cast the Beast Sense and Speak with Animals spells but only as Rituals. Wisdom is your "
                   "spellcasting ability for them.",)},
    "wild-heart-xphb-10-nature-speaker": {
        "class": "barbarian", "subclass": "wild-heart-xphb", "mode": "innate", "spells": ("commune-with-nature",),
        "uses": "ritual only", "ability": "WIS", "ability_from": "text", "note": None,
        "quotes": ("You can cast the Commune with Nature spell but only as a Ritual. Wisdom is your spellcasting ability "
                   "for it.",)},
    "glamour-xphb-6-mantle-of-majesty": {
        "class": "bard", "subclass": "glamour-xphb", "mode": "innate", "spells": ("command",),
        "uses": "1/long rest", "ability": "CHA", "ability_from": "class",
        "note": "Cast as a Bonus Action without a spell slot, then again as a Bonus Action for 1 minute; regain the use by "
                "expending a level 3+ spell slot.",
        "quotes": ("As a Bonus Action, you cast Command without expending a spell slot,",
                   "Once you use this feature, you can't use it again until you finish a Long Rest. You can also restore "
                   "your use of it by expending a level 3+ spell slot (no action required).")},
    "psi-warrior-xphb-18-telekinetic-master": {
        "class": "fighter", "subclass": "psi-warrior-xphb", "mode": "innate", "spells": ("telekinesis",),
        "uses": "1/long rest", "ability": "INT", "ability_from": "text",
        "note": "No spell slot or components; regain the use by expending a Psionic Energy Die.",
        "quotes": ("You always have the Telekinesis spell prepared. With this feature, you can cast it without a spell slot "
                   "or components, and your spellcasting ability for it is Intelligence.",
                   "Once you cast the spell with this feature, you can't do so in this way again until you finish a Long "
                   "Rest unless you expend a Psionic Energy Die (no action required) to restore your use of it.")},
    "shadow-xphb-3-darkness": {
        "class": "monk", "subclass": "shadow-xphb", "mode": "innate", "spells": ("darkness",),
        "uses": "1 Focus Point", "ability": "WIS", "ability_from": "data",
        "note": "No spell components; you can see within the area.",
        "quotes": ("You can expend 1 Focus Point to cast the Darkness spell without spell components. You can see within "
                   "the spell's area when you cast it with this feature.",)},
    "archfey-xphb-3-steps-of-the-fey": {
        "class": "warlock", "subclass": "archfey-xphb", "mode": "innate", "spells": ("misty-step",),
        "uses": "{cha_min1}/long rest", "ability": "CHA", "ability_from": "class",
        "note": "No spell slot; when you cast it you can add a Steps of the Fey effect.",
        "quotes": ("You can cast Misty Step without expending a spell slot a number of times equal to your Charisma "
                   "modifier (minimum of once), and you regain all expended uses when you finish a Long Rest.",)},
    "diviner-xphb-10-the-third-eye": {
        "class": "wizard", "subclass": "diviner-xphb", "mode": "innate", "spells": ("see-invisibility",),
        "uses": "1/short or long rest", "ability": "INT", "ability_from": "class",
        "note": "The Third Eye: choose this benefit as a Bonus Action; it lasts until you start a Short or Long Rest.",
        "quotes": ("See Invisibility. You can cast See Invisibility without expending a spell slot.",
                   "You can't use this feature again until you finish a Short or Long Rest.")},
    "great-old-one-xphb-10-eldritch-hex": {
        "class": "warlock", "subclass": "great-old-one-xphb", "mode": "prepared", "spells": ("hex",),
        "quotes": ("You always have the Hex spell prepared.",)},
}

# C6d: XPHB Wizard spell picks that are "always prepared" (ruleset 2024 only), keyed by the choice-id
# tail. Texts (XPHB, read from catalog.features):
#   Spell Mastery (18)   "Choose a level 1 and a level 2 spell in your spellbook that have a casting time of an
#                        action. You always have those spells prepared, and you can cast them at their lowest
#                        level without expending a spell slot."
#   Signature Spells (20) "Choose two level 3 spells in your spellbook as your signature spells. You always have
#                        these spells prepared, and you can cast each of them once at level 3 without expending a
#                        spell slot."
# Keys: feature (the XPHB feature record that must exist), class_level, spell_level, count, casting_time (None =
# no condition), label (card label), grant (the always-prepared reason, also the sheet.features row name),
# sheet_key (key on the Wizard sheet.spells entry).
WIZARD_SPELL_PICKS_2024: dict[str, dict] = {
    "spell-mastery-1": {"feature": "xphb-wizard-18-spell-mastery", "class_level": 18, "spell_level": 1, "count": 1,
                        "casting_time": "1 action", "label": "Spell Mastery (level 1)", "grant": "Spell Mastery",
                        "sheet_key": "spellMastery"},
    "spell-mastery-2": {"feature": "xphb-wizard-18-spell-mastery", "class_level": 18, "spell_level": 2, "count": 1,
                        "casting_time": "1 action", "label": "Spell Mastery (level 2)", "grant": "Spell Mastery",
                        "sheet_key": "spellMastery"},
    "signature-spells": {"feature": "xphb-wizard-20-signature-spells", "class_level": 20, "spell_level": 3, "count": 2,
                         "casting_time": None, "label": "Signature Spells", "grant": "Signature Spells",
                         "sheet_key": "signatureSpells"},
}


# RP15 (E11b): the SRD (2014) Wizard Spell Mastery / Signature Spell, under mixed and 2014. The cids are the SAME
# as the 2024 cards (a stored pick survives a ruleset switch). Texts (SRD, read from catalog.features):
#   Spell Mastery (18)   "Choose a 1st-level wizard spell and a 2nd-level wizard spell that are in your spellbook.
#                        You can cast those spells at their lowest level without expending a spell slot when you
#                        have them prepared." - no casting-time condition, and NOT always prepared.
#   Signature Spell (20) "Choose two 3rd-level wizard spells in your spellbook as your signature spells. You always
#                        have these spells prepared, they don't count against the number of spells you have
#                        prepared, and you can cast each of them once at 3rd level without expending a spell slot.
#                        When you do so, you can't do so again until you finish a short or long rest."
# Same keys as the 2024 table plus `always_prepared` (2024 entries default True) and `feature_name` (the SRD feature
# name, the sheet.features row).
WIZARD_SPELL_PICKS_2014: dict[str, dict] = {
    "spell-mastery-1": {"feature": "spell-mastery", "class_level": 18, "spell_level": 1, "count": 1,
                        "casting_time": None, "label": "Spell Mastery (level 1)", "grant": "Spell Mastery",
                        "sheet_key": "spellMastery", "always_prepared": False, "feature_name": "Spell Mastery"},
    "spell-mastery-2": {"feature": "spell-mastery", "class_level": 18, "spell_level": 2, "count": 1,
                        "casting_time": None, "label": "Spell Mastery (level 2)", "grant": "Spell Mastery",
                        "sheet_key": "spellMastery", "always_prepared": False, "feature_name": "Spell Mastery"},
    "signature-spells": {"feature": "signature-spell", "class_level": 20, "spell_level": 3, "count": 2,
                         "casting_time": None, "label": "Signature Spells", "grant": "Signature Spells",
                         "sheet_key": "signatureSpells", "always_prepared": True, "feature_name": "Signature Spell"},
}

# Wizard 20 Signature Spell resource (SRD): one cast of each picked spell per short or long rest, at 3rd level.
SIGNATURE_SPELLS_2014 = {"feature": "signature-spell", "choice": "class:wizard:20:signature-spells",
                         "recharge": "short-or-long"}


def wizard_spell_picks(ruleset: str) -> dict[str, dict]:
    """The Spell Mastery / Signature Spells spec for a ruleset: the XPHB table under 2024, the SRD one otherwise."""
    return WIZARD_SPELL_PICKS_2024 if ruleset == "2024" else WIZARD_SPELL_PICKS_2014
