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

from i18n.messages import msg

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
    # VF1.1: TCE Oath of Glory 7 "Your walking speed increases by 10 feet." (unconditional; the ally clause stays text).
    # Quote-pinned against the vendored subclassFeature in tests/test_campaign_regressions.py. The XPHB twin is
    # CLASS_FEATURE_EFFECTS_2024 (ruleset 2024 only, RP2); this one is keyed by the TCE record and applies in every ruleset.
    "glory-tce-7-aura-of-alacrity": {"speed_bonus_flat": 10},
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
        ("Your draconic ancestry determines the size, shape, and damage type of the exhalation",
         "the type of which is determined by your draconic ancestry",
         "The DC for this saving throw equals 8 + your Constitution modifier + your proficiency bonus",
         "A creature takes 2d6 damage on a failed save, and half as much damage on a successful one",
         "The damage increases to 3d6 at 6th level, 4d6 at 11th level, and 5d6 at 16th level",
         "you can't use it again until you complete a short or long rest"),
        dc="CON", damage_type="ancestry", dice_by_level=((1, "2d6"), (6, "3d6"), (11, "4d6"), (16, "5d6")),
        phb_ancestry=True,
        note_picked="Action: exhale destructive energy in {shape}, {save} saving throw, {dice} {damage_type} damage on a "
                    "failed save and half as much on a success"),
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

# B1: the PHB Dragonborn's Draconic Ancestry table (the 10 rows of the PHB race entry, `races.json` "Draconic Ancestry"
# table: Dragon | Damage Type | Breath Weapon). `row` is the verbatim data row (tests/test_b1_draconic_ancestry.py compares
# it with the vendored record); the other fields are read from that row: `damage` the damage type, `shape` / `length` /
# `width` the area ("5 by 30 ft. line" = a line 30 feet long and 5 feet wide; "15 ft. cone" = a 15-foot cone, no width),
# `save` the ability of the saving throw ("Dex. save" / "Con. save"). The damage type alone does not name the dragon
# (fire = Brass, Gold, Red), hence the card `species:dragonborn-phb:draconic-ancestry`.
DRACONIC_ANCESTRY_PHB: dict[str, dict] = {
    "black": {"name": "Black", "damage": "acid", "shape": "line", "length": 30, "width": 5, "save": "DEX",
              "row": ("Black", "Acid", "5 by 30 ft. line (Dex. save)")},
    "blue": {"name": "Blue", "damage": "lightning", "shape": "line", "length": 30, "width": 5, "save": "DEX",
             "row": ("Blue", "Lightning", "5 by 30 ft. line (Dex. save)")},
    "brass": {"name": "Brass", "damage": "fire", "shape": "line", "length": 30, "width": 5, "save": "DEX",
              "row": ("Brass", "Fire", "5 by 30 ft. line (Dex. save)")},
    "bronze": {"name": "Bronze", "damage": "lightning", "shape": "line", "length": 30, "width": 5, "save": "DEX",
               "row": ("Bronze", "Lightning", "5 by 30 ft. line (Dex. save)")},
    "copper": {"name": "Copper", "damage": "acid", "shape": "line", "length": 30, "width": 5, "save": "DEX",
               "row": ("Copper", "Acid", "5 by 30 ft. line (Dex. save)")},
    "gold": {"name": "Gold", "damage": "fire", "shape": "cone", "length": 15, "width": None, "save": "DEX",
             "row": ("Gold", "Fire", "15 ft. cone (Dex. save)")},
    "green": {"name": "Green", "damage": "poison", "shape": "cone", "length": 15, "width": None, "save": "CON",
              "row": ("Green", "Poison", "15 ft. cone (Con. save)")},
    "red": {"name": "Red", "damage": "fire", "shape": "cone", "length": 15, "width": None, "save": "DEX",
            "row": ("Red", "Fire", "15 ft. cone (Dex. save)")},
    "silver": {"name": "Silver", "damage": "cold", "shape": "cone", "length": 15, "width": None, "save": "CON",
               "row": ("Silver", "Cold", "15 ft. cone (Con. save)")},
    "white": {"name": "White", "damage": "cold", "shape": "cone", "length": 15, "width": None, "save": "CON",
              "row": ("White", "Cold", "15 ft. cone (Con. save)")},
}
# The species records that hold the PHB table: the PHB Dragonborn and, through it, its EGW subraces (Draconblood, Ravenite).
DRACONIC_ANCESTRY_RACES: tuple[str, ...] = ("dragonborn-phb",)

# X2: the resource recharge vocabulary. `long` / `short` / `short-or-long` are rests; `turn` ("Once per turn"), `combat`
# ("only once per combat"), `rage` ("only once per rage") and `other` (any other stated condition, written out in
# `details.note`) are the non-rest limits. Consumers: export_fields._RECHARGE_WORDS, ClassResourcesList.tsx RECHARGE,
# types.ts ResourceCore.recharge (tests/test_x2_turn_combat_rage_recharges.py keeps the four in step).
RESOURCE_RECHARGES: tuple[str, ...] = ("long", "short", "short-or-long", "turn", "combat", "rage", "other")

# X2: the five book species traits W5b skipped because the vocabulary could not express their limit.
SPECIES_RESOURCES_2014.update({
    "hobgoblin-dmg-trait-0": _e("hobgoblin-dmg", "Martial Advantage", 1, "turn",
        "Once per turn, extra 2d6 damage to a creature you hit with a weapon attack if it is within 5 feet of an ally of "
        "yours that isn't incapacitated",
        ("Once per turn, you can deal an extra 2d6 damage to a creature you hit with a weapon attack",
         "if that creature is within 5 ft. of an ally of yours that isn't incapacitated")),
    "bugbear-erlw-trait-7": _e("bugbear-erlw", "Surprise Attack", 1, "combat",
        "If you surprise a creature and hit it with an attack on your first turn in combat, the attack deals an extra 2d6 damage",
        ("If you surprise a creature and hit it with an attack on your first turn in combat",
         "the attack deals an extra 2d6 damage to it", "You can use this trait only once per combat.")),
    "bugbear-vgm-trait-6": _e("bugbear-vgm", "Surprise Attack", 1, "combat",
        "If you surprise a creature and hit it with an attack on your first turn in combat, the attack deals an extra 2d6 damage",
        ("If you surprise a creature and hit it with an attack on your first turn in combat",
         "the attack deals an extra 2d6 damage to it", "You can use this trait only once per combat.")),
    "tabaxi-mpmm-trait-5": _e("tabaxi-mpmm", "Feline Agility", 1, "other",
        "When you move on your turn in combat, double your speed until the end of the turn; after you use it you can't use "
        "it again until you move 0 feet on one of your turns",
        ("When you move on your turn in combat, you can double your speed until the end of the turn",
         "you can't use it again until you move 0 feet on one of your turns.")),
    "tabaxi-vgm-trait-3": _e("tabaxi-vgm", "Feline Agility", 1, "other",
        "When you move on your turn in combat, double your speed until the end of the turn; after you use it you can't use "
        "it again until you move 0 feet on one of your turns",
        ("When you move on your turn in combat, you can double your speed until the end of the turn",
         "you can't use it again until you move 0 feet on one of your turns.")),
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


# X1: a species flying speed the trait text bans in armor. trait id -> the record that holds it (`race`, plus `subrace`
# for a subspecies trait), the display `name` used in the warning, the armor `categories` that ban it and the sentence
# (`quote`, pinned against catalog.traits by tests/test_x1_fly_armor.py). Only these nine records say so: the Aarakocra
# (DMG) record has fly 50 but no Flight trait text, so it is NOT banned. Winged Tiefling (SCAG) says heavy armor only.
_FLY_MEDIUM_HEAVY = ("Medium", "Heavy")
FLY_ARMOR_BAN: dict[str, dict] = {
    "aarakocra-eepc-trait-3": {"race": "aarakocra-eepc", "name": "Aarakocra", "categories": _FLY_MEDIUM_HEAVY,
                               "quote": "To use this speed, you can't be wearing medium or heavy armor."},
    "aarakocra-mpmm-trait-0": {"race": "aarakocra-mpmm", "name": "Aarakocra", "categories": _FLY_MEDIUM_HEAVY,
                               "quote": "You can't use this flying speed if you're wearing medium or heavy armor."},
    "aven-psa-trait-3": {"race": "aven-psa", "name": "Aven", "categories": _FLY_MEDIUM_HEAVY,
                         "quote": "You can't use your flying speed while you wear medium or heavy armor."},
    "aven-psd-trait-3": {"race": "aven-psd", "name": "Aven", "categories": _FLY_MEDIUM_HEAVY,
                         "quote": "You can't use your flying speed while you wear medium or heavy armor."},
    "fairy-mpmm-trait-2": {"race": "fairy-mpmm", "name": "Fairy", "categories": _FLY_MEDIUM_HEAVY,
                           "quote": "You can't use this flying speed if you're wearing medium or heavy armor."},
    "fairy-wbtw-trait-1": {"race": "fairy-wbtw", "name": "Fairy", "categories": _FLY_MEDIUM_HEAVY,
                           "quote": "You can't use this flying speed if you're wearing medium or heavy armor."},
    "owlin-scc-trait-2": {"race": "owlin-scc", "name": "Owlin", "categories": _FLY_MEDIUM_HEAVY,
                          "quote": "You can't use this flying speed if you're wearing medium or heavy armor."},
    "siren-psx-trait-3": {"race": "siren-psx", "name": "Siren", "categories": _FLY_MEDIUM_HEAVY,
                          "quote": "You can't use your flying speed while you wear medium or heavy armor."},
    "tiefling-phb-variant;-winged-scag-trait-1": {
        "race": "tiefling-phb", "subrace": "tiefling-phb-variant;-winged-scag", "name": "Winged Tiefling",
        "categories": ("Heavy",),
        "quote": "You have a flying speed of 30 feet while you aren't wearing heavy armor."},
}


# VF2.1: Armor Class a species trait states in its own text (trait id -> record). `kind`: "unarmored" = `base` + the abilities'
# modifiers while no body armor is worn; "natural" = the same, and ALSO usable when the armor worn would leave a lower AC (Lizardfolk,
# Locathah, Loxodon: "You can use your natural armor to determine your AC if the armor you wear would leave you with a lower AC");
# "fixed" = a base AC that armor does not change (Tortle: "You can't wear ..." / "You gain no benefit from wearing armor"); "flat" =
# a +`base` bonus on top of whatever AC applies, armor included (Lizardfolk DMG, Troglodyte, Warforged). A shield adds in every
# kind ("A shield's benefits apply as normal"). Several formulas never sum: the best applies (PHB 2024 / GGR "AC Calculations
# Don't Stack"). Not here (conditional / not an AC of the character): Shifter and Beasthide (while shifted), Tortle Shell Defense
# (withdrawn), Simic Hybrid Carapace (an enhancement pick), the AC 5 of the Gnome clockwork devices. `quote` is the sentence of the
# record (tags stripped), pinned in tests/test_campaign_regressions.py.
SPECIES_AC: dict[str, dict] = {
    "autognome-aag-trait-1": {"race": "autognome-aag", "kind": "unarmored", "base": 13, "abilities": ("DEX",),
                              "quote": "While you aren't wearing armor, your base Armor Class is 13 + your Dexterity modifier."},
    "thri-kreen-aag-trait-2": {"race": "thri-kreen-aag", "kind": "unarmored", "base": 13, "abilities": ("DEX",),
                               "quote": "While you aren't wearing armor, your carapace gives you a base Armor Class of 13 + your Dexterity modifier."},
    "goblin-psz-trait-5": {"race": "goblin-psz", "kind": "unarmored", "base": 11, "abilities": ("DEX",),
                           "quote": "when you are wearing no armor, your AC is equal to 11 + your Dexterity modifier."},
    "lizardfolk-mpmm-trait-4": {"race": "lizardfolk-mpmm", "kind": "natural", "base": 13, "abilities": ("DEX",),
                                "quote": "When you aren't wearing armor, your base AC is 13 + Dexterity modifier. You can use your natural armor to "
                                         "determine your AC if the armor you wear would leave you with a lower AC."},
    "lizardfolk-vgm-trait-7": {"race": "lizardfolk-vgm", "kind": "natural", "base": 13, "abilities": ("DEX",),
                               "quote": "When you aren't wearing armor, your AC is 13 + your Dexterity modifier. You can use your natural armor to "
                                        "determine your AC if the armor you wear would leave you with a lower AC."},
    "locathah-lr-trait-2": {"race": "locathah-lr", "kind": "natural", "base": 12, "abilities": ("DEX",),
                            "quote": "When you aren't wearing armor, your AC is 12 + your Dexterity modifier. You can use your natural armor to "
                                     "determine your AC if the armor you wear would leave you with a lower AC."},
    "loxodon-ggr-trait-5": {"race": "loxodon-ggr", "kind": "natural", "base": 12, "abilities": ("CON",),
                            "quote": "When you aren't wearing armor, your AC is 12 + your Constitution modifier. You can use your natural armor to "
                                     "determine your AC if the armor you wear would leave you with a lower AC."},
    "tortle-mpmm-trait-3": {"race": "tortle-mpmm", "kind": "fixed", "base": 17, "abilities": (),
                            "quote": "Your shell provides you a base AC of 17 (your Dexterity modifier doesn't affect this number). "
                                     "You can't wear light, medium, or heavy armor, but if you are using a shield, you can apply the shield's bonus as normal."},
    "tortle-ttp-trait-6": {"race": "tortle-ttp", "kind": "fixed", "base": 17, "abilities": (),
                           "quote": "it gives you a base AC of 17 (your Dexterity modifier doesn't affect this number). You gain no benefit from "
                                    "wearing armor, but if you are using a shield, you can apply the shield's bonus as normal."},
    "lizardfolk-dmg-trait-1": {"race": "lizardfolk-dmg", "kind": "flat", "base": 3, "abilities": (),
                               "quote": "granting you a +3 bonus to Armor Class."},
    "troglodyte-dmg-trait-3": {"race": "troglodyte-dmg", "kind": "flat", "base": 1, "abilities": (),
                               "quote": "Your thick hide grants you a +1 bonus to Armor Class."},
    "warforged-erlw-trait-5": {"race": "warforged-erlw", "kind": "flat", "base": 1, "abilities": (),
                               "quote": "You gain a +1 bonus to Armor Class."},
    "warforged-efa-trait-1": {"race": "warforged-efa", "kind": "flat", "base": 1, "abilities": (),
                              "quote": "You gain a +1 bonus to your Armor Class."},
}


# VF2.2: a species trait that lets the character add the Proficiency Bonus to initiative rolls (Harengon Hare-Trigger, MPMM and
# WBtW). Like Alert (XPHB) the full bonus replaces the Jack of All Trades / Remarkable Athlete half bonus; two sources of the same
# "add your proficiency bonus" do not double. `quote` is the sentence of the record, pinned in tests/test_campaign_regressions.py.
SPECIES_INITIATIVE_PB: dict[str, dict] = {
    "harengon-mpmm-trait-1": {"race": "harengon-mpmm", "quote": "You can add your proficiency bonus to your initiative rolls."},
    "harengon-wbtw-trait-1": {"race": "harengon-wbtw", "quote": "You can add your proficiency bonus to your initiative rolls."},
}


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

# VF4.1: a background whose TEXT fixes the variant (spell list / college) of the feat it grants while the `feats` key carries
# none ("You gain the Strixhaven Initiate feat and must choose Lorehold within it."; Astral Drifter: "... Magic Initiate
# feat from the Player's Handbook and must choose cleric for the feat."). Key = "name|source" lowercased; `hints` =
# {feat ref: variant hint} in the shape `_feat_variant_hints_from_5etools` makes (a Magic Initiate variant is
# "<List> Spells"; a Strixhaven Initiate hint is the college, which prefixes its three variants "Lorehold 1" ... "Lorehold 3");
# `quote` is the record's own sentence (pinned by a test against the vendored data).
BACKGROUND_FEAT_VARIANT_FROM_TEXT: dict[str, dict] = {
    f"{college.lower()} student|scc": {
        "hints": {"strixhaven-initiate-scc": college},
        "quote": f"You gain the {{@feat Strixhaven Initiate|SCC}} feat and must choose {college} within it.",
    }
    for college in ("Lorehold", "Prismari", "Quandrix", "Silverquill", "Witherbloom")
}
# VF6: Astral Drifter (AAG) fixes the Magic Initiate (PHB) list to Cleric the same way (owner-approved).
BACKGROUND_FEAT_VARIANT_FROM_TEXT["astral drifter|aag"] = {
    "hints": {"magic-initiate-phb": "Cleric Spells"},
    "quote": "You gain the {@feat Magic Initiate||Magic Initiate feat} from the {@book Player's Handbook|PHB} and must choose cleric for the feat.",
}

# FE6 (B4): 5etools says `languageProficiencies: [{"thieves' cant": true}]` for Harper Agent (FRHoF) and the
# converter used to drop the unknown key. index -> language ids ("You know Thieves' Cant."). Display names come
# from LANGUAGE_NAMES (the 2024 rare table, C6b-2).
FEAT_FIXED_LANGUAGE_OVERRIDES = {"harper-agent-frhof": ["thieves-cant"]}

# W11: DATA_OVERRIDES, the single registry of every place the converters or tables correct a defect of the raw 5etools
# data. It is DOCUMENTATION plus a tripwire, not a lookup: nothing reads it at runtime (behavior is unchanged), the
# code keeps using the tables and functions named in `where`. tests/test_data_overrides.py asserts per entry that the
# raw record STILL has the defect (a fixed upstream record fails loudly, so the override can be removed) and that the
# `where` symbol ("module:name") still exists.
#   what = the correction; where = the code that applies it; raw_record_pin = {file, record, defect} in the synced
#   official data (path under official_dir() unless noted); reason = why the data is wrong and what wins.
DATA_OVERRIDES: dict[str, dict] = {
    "cleric-2024-gold": {
        "what": "Cleric XPHB starting equipment A: gold is 70 GP from the text-line amount, not the data value",
        "where": "catalog.official.class_chassis:_class_equipment_options_2024",
        "raw_record_pin": {"file": "class/class-cleric.json", "record": "class Cleric|XPHB startingEquipment",
                           "defect": "defaultData A value is 7000 (cp) while the entries line says \"7 GP\""},
        "reason": "the record's own text line wins over `value`; the class gold is read from the text per option",
    },
    "mulhorandi-tomb-raider-gold": {
        "what": "Mulhorandi Tomb Raider (FRHoF) equipment A keeps its 26 GP, taken from the text line",
        "where": "catalog.official.background_equipment:_text_gold",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Mulhorandi Tomb Raider|FRHoF startingEquipment",
                           "defect": "the gold is fused into the waterskin displayName \"Waterskin 26 GP\" and no value entry exists"},
        "reason": "the data lost the gold amount into a display name; the text line states it",
    },
    "scribe-item-counts": {
        "what": "Scribe (XPHB) Oil x3 and Parchment x12 come from the text tokens",
        "where": "catalog.official.background_equipment:_text_count",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Scribe|XPHB startingEquipment A",
                           "defect": "oil and parchment are bare items without quantity or displayName count"},
        "reason": "the data lost \"(3 flasks)\" and \"(12 sheets)\"; the text line states them and wins",
    },
    "carouser-generic-gaming-set": {
        "what": "Carouser (ABH) tool proficiency {\"gaming set\": true} becomes a one-pick card of Gaming Sets",
        "where": "catalog.official.proficiencies:_GENERIC_TOOL_KEYS",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Carouser|ABH toolProficiencies",
                           "defect": "a generic category name stored as a fixed grant: {\"gaming set\": true}"},
        "reason": "the text says \"Choose one kind of Gaming Set\"; a fixed grant of a category is not a tool",
    },
    "elemental-adept-phb-repeatable": {
        "what": "PHB 2014 Elemental Adept may be taken more than once",
        "where": "catalog.reference_data:REPEATABLE_FEAT_OVERRIDES",
        "raw_record_pin": {"file": "feats.json", "record": "feat Elemental Adept|PHB",
                           "defect": "no `repeatable` flag (the XPHB record has it)"},
        "reason": "the feat text allows several takes with a different damage type each",
    },
    "echoing-soul-skill-count": {
        "what": "Echoing Soul (RHW) grants two skill proficiencies",
        "where": "catalog.reference_data:FEAT_SKILL_PICK_COUNT_OVERRIDES",
        "raw_record_pin": {"file": "feats.json", "record": "feat Echoing Soul|RHW skillProficiencies",
                           "defect": "[{\"any\": 1}] while the text says \"proficiency in two skills of your choice\""},
        "reason": "the feat text wins over the structured count",
    },
    "harper-agent-thieves-cant": {
        "what": "Harper Agent (FRHoF) fixed language Thieves' Cant",
        "where": "catalog.reference_data:FEAT_FIXED_LANGUAGE_OVERRIDES",
        "raw_record_pin": {"file": "feats.json", "record": "feat Harper Agent|FRHoF languageProficiencies",
                           "defect": "[{\"thieves' cant\": true}], a key the language converter does not know"},
        "reason": "the feat text says \"You know Thieves' Cant.\"",
    },
    "genie-touched-feat": {
        "what": "Genie Touched (FRHoF) grants Magic Initiate (Wizard)",
        "where": "catalog.reference_data:BACKGROUND_FEATS_FROM_TEXT",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Genie Touched|FRHoF",
                           "defect": "no `feats` field although its entries line says \"Magic Initiate|XPHB (Wizard)\""},
        "reason": "the record's own text names the feat; the table restores the raw-shaped `feats` list",
    },
    "scc-student-feat-college": {
        "what": "The five SCC Student backgrounds (Lorehold, Prismari, Quandrix, Silverquill, Witherbloom) fix the Strixhaven Initiate college",
        "where": "catalog.reference_data:BACKGROUND_FEAT_VARIANT_FROM_TEXT",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Lorehold Student|SCC (and the four other colleges) feats",
                           "defect": "[{\"strixhaven initiate|scc\": true}] carries no variant while the entry says \"must choose Lorehold within it\""},
        "reason": "the record's own sentence names the college; the table restores the variant hint the Magic Initiate backgrounds carry",
    },
    "astral-drifter-feat-list": {
        "what": "Astral Drifter (AAG) fixes the Magic Initiate (PHB) spell list to Cleric",
        "where": "catalog.reference_data:BACKGROUND_FEAT_VARIANT_FROM_TEXT",
        "raw_record_pin": {"file": "backgrounds.json", "record": "background Astral Drifter|AAG feats",
                           "defect": "[{\"magic initiate|phb\": true}] carries no variant while the entry says \"must choose cleric for the feat\""},
        "reason": "the record's own sentence names the list; the table restores the variant hint the Magic Initiate backgrounds carry",
    },
    "srd-paladin-simple-melee-weapon": {
        "what": "SRD Paladin starting equipment (b) \"any simple melee weapon\" offers the simple MELEE weapons only",
        "where": "catalog.loader:_follow_melee_description",
        "raw_record_pin": {"file": "chargen/data/srd/5e-SRD-Classes.json (not under official_dir)",
                           "record": "class paladin starting_equipment_options[1]",
                           "defect": "desc \"(a) five javelins or (b) any simple melee weapon\" but the nested pick is `any simple weapon` / simple-weapons"},
        "reason": "the line's own description and PHB p.82 (class file: weaponSimpleMelee) say melee; the description wins",
    },
    "srd-levels-invocations-metamagic-known": {
        "what": "SRD Levels counts: Warlock Eldritch Invocations known (L4 2, L6 3) and Sorcerer Metamagic known (L16 3) follow the PHB table",
        "where": "catalog.loader:_apply_srd_levels_count_fixes",
        "raw_record_pin": {"file": "chargen/data/srd/5e-SRD-Levels.json (not under official_dir)",
                           "record": "warlock-4 / warlock-6 class_specific.invocations_known, sorcerer-16 class_specific.metamagic_known",
                           "defect": "3 at L4 and 4 at L6 (PHB 2 and 3), 4 at L16 (PHB 3): one level early"},
        "reason": "the PHB table (class-warlock.json / class-sorcerer.json optionalfeatureProgression) is the rule; the SRD Levels file has the error",
    },
    "pact-of-the-chain-ritual": {
        "what": "Pact of the Chain (XPHB) Find Familiar is an at-will innate spell",
        "where": "engine.class_choices_2024:_INNATE_USES_2024",
        "raw_record_pin": {"file": "optionalfeatures.json", "record": "optionalfeature Pact of the Chain|XPHB additionalSpells",
                           "defect": "innate frequency key \"ritual\" while the text casts it as a Magic action without a slot"},
        "reason": "the text says no spell slot is expended, so the engine maps \"ritual\" to at-will",
    },
}

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

# G2: 2014 Metamagic costs in Sorcery Points (`details.metamagicCosts` of sorcerer:sorcery-points, picked options only).
# Option id (the SRD Metamagic feature records, `metamagic-<slug>`, and the TCE records `opt-<slug>-tce`) ->
# {"cost": the number, or the exact text when the cost is not a number (Twinned Spell: "spell level"), "quote": the
# verbatim sentence of the record that states it (pinned by tests/test_metamagic_costs_2014.py)}. The vendored
# optionalfeatures.json `consumes` agrees where it has an amount (Heightened 3, Quickened 2, Seeking 2).
METAMAGIC_COSTS_2014: dict[str, dict] = {
    "metamagic-careful-spell": {"cost": 1, "quote": "To do so, you spend 1 sorcery point and choose a number of those creatures"},
    "metamagic-distant-spell": {"cost": 1, "quote": "you can spend 1 sorcery point to double the range of the spell"},
    "metamagic-empowered-spell": {"cost": 1, "quote": "you can spend 1 sorcery point to reroll a number of the damage dice"},
    "metamagic-extended-spell": {"cost": 1, "quote": "you can spend 1 sorcery point to double its duration"},
    "metamagic-heightened-spell": {"cost": 3, "quote": "you can spend 3 sorcery points to give one target of the spell disadvantage"},
    "metamagic-quickened-spell": {"cost": 2, "quote": "you can spend 2 sorcery points to change the casting time to 1 bonus action"},
    "metamagic-subtle-spell": {"cost": 1, "quote": "you can spend 1 sorcery point to cast it without any somatic or verbal components"},
    # F1: the cost text carries the cantrip rule of the same sentence ("(1 sorcery point if the spell is a cantrip)").
    "metamagic-twinned-spell": {"cost": "spell level, 1 for a cantrip",
                                "quote": "you can spend a number of sorcery points equal to the spell's level to target a second creature "
                                         "in range with the same spell (1 sorcery point if the spell is a cantrip)"},
    "opt-seeking-spell-tce": {"cost": 2, "quote": "you can spend 2 sorcery points to reroll the"},
    "opt-transmuted-spell-tce": {"cost": 1, "quote": "you can spend 1 sorcery point to change that damage type"},
}

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
     "level_vars": {"size": PERFORMANCE_OF_CREATION_SIZE_2014,
                    "gp_cap": ((1, "worth up to {twenty_level} gp (20 x Bard level)"), (14, "of any gp value (no gp limit)"))},
     "note": "Action: create one nonmagical item {gp_cap}, {size} or smaller, in an "
             "unoccupied space within 10 feet; it disappears after {pb} hours (proficiency bonus); use it again before a "
             "long rest by expending a spell slot of 2nd level or higher; only one such item at a time",
     "extras": (("creation-tce-14-creative-crescendo", "Creative Crescendo: create up to {cha_min2} items at once (Charisma "
                 "modifier, minimum 2), only one of the maximum size and the rest Small or Tiny"),),
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
             "saving throw it gains temporary hit points equal to the roll {cha:+d} (minimum 1 temporary hit point in total)",
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

# ---- W8b: Cleric, Druid, Fighter (book subclasses) ---------------------------------------------------------------------
# Tables that live only in the text (pinned in BOOK_TABLE_PINS_2014, like the W8a ones).
ARCANE_BANISHMENT_2014 = ((2, ""),
                          (5, "; from level 5 a creature that fails is also banished for 1 minute (no concentration) if it "
                              "is not on its plane of origin and its challenge rating is 1/2 or lower"),
                          (8, "; from level 5 a creature that fails is also banished for 1 minute (no concentration) if it "
                              "is not on its plane of origin and its challenge rating is 1 or lower"),
                          (11, "; from level 5 a creature that fails is also banished for 1 minute (no concentration) if it "
                               "is not on its plane of origin and its challenge rating is 2 or lower"),
                          (14, "; from level 5 a creature that fails is also banished for 1 minute (no concentration) if it "
                               "is not on its plane of origin and its challenge rating is 3 or lower"),
                          (17, "; from level 5 a creature that fails is also banished for 1 minute (no concentration) if it "
                               "is not on its plane of origin and its challenge rating is 4 or lower"))
HALO_OF_SPORES_DICE_2014 = ((2, "1d4"), (6, "1d6"), (10, "1d8"), (14, "1d10"))
CIRCLE_FORMS_CR_2014 = ((2, "1"), (6, "2"), (9, "3"), (12, "4"), (15, "5"), (18, "6"))
CIRCLE_FORMS_LIMIT_2014 = ((2, "no flying or swimming speed"), (4, "no flying speed"), (8, "no other limitation"))
STARRY_FORM_DICE_2014 = ((2, "1d8"), (10, "2d8"))
RUNES_KNOWN_2014 = ((3, 2), (7, 3), (10, 4), (15, 5))
GIANTS_MIGHT_DICE_2014 = ((3, "1d6"), (10, "1d8"), (18, "1d10"))
FIGHTING_SPIRIT_THP_2014 = ((3, 5), (10, 10), (15, 15))

BOOK_TABLE_PINS_2014.update({
    "DIVINE_STRIKE_DICE_2014": (("death-dmg-8-divine-strike", "the cleric can cause the attack to deal an extra 1d8 necrotic damage to the target"),
                                ("death-dmg-8-divine-strike", "When the cleric reaches 14th level, the extra damage increases to 2d8")),
    "ARCANE_BANISHMENT_2014": (("arcana-scag-2-channel-divinity:-arcane-abjuration",
                                "Cleric level | Banishes Creatures of CR... 5th | 1/2 or lower 8th | 1 or lower 11th | 2 or lower 14th | 3 or lower 17th | 4 or lower"),),
    "HALO_OF_SPORES_DICE_2014": (("spores-tce-2-halo-of-spores", "deal 1d4 necrotic damage to that creature"),
                                 ("spores-tce-2-halo-of-spores", "increases to 1d6 at 6th level, 1d8 at 10th level, and 1d10 at 14th level")),
    "CIRCLE_FORMS_CR_2014": (("moon-phb-2-circle-forms",
                              "Max. CR | Limitations 2nd | 1 | No flying or swimming speed 4th | 1 | No flying speed 6th | 2 | No flying speed 8th | 2 | — 9th | 3 | — 12th | 4 | — 15th | 5 | — 18th | 6 | —"),),
    "CIRCLE_FORMS_LIMIT_2014": (("moon-phb-2-circle-forms",
                                 "2nd | 1 | No flying or swimming speed 4th | 1 | No flying speed 6th | 2 | No flying speed 8th | 2 | —"),),
    "STARRY_FORM_DICE_2014": (("stars-tce-2-archer", "1d8 + your Wisdom modifier"),
                              ("stars-tce-10-twinkling-constellations", "The 1d8 of the Archer and the Chalice becomes 2d8")),
    "RUNES_KNOWN_2014": (("rune-knight-tce-3-rune-carver", "Fighter Level | Number of Runes 3rd | 2 7th | 3 10th | 4 15th | 5"),),
    "GIANTS_MIGHT_DICE_2014": (("rune-knight-tce-3-giants-might", "can deal an extra 1d6 damage to a target on a hit"),
                               ("rune-knight-tce-10-great-stature", "the extra damage you deal with your Giant's Might feature increases to 1d8"),
                               ("rune-knight-tce-18-runic-juggernaut", "the extra damage you deal with the Giant's Might feature increases to 1d10")),
    "FIGHTING_SPIRIT_THP_2014": (("samurai-xge-3-fighting-spirit", "you also gain 5 temporary hit points"),
                                 ("samurai-xge-3-fighting-spirit", "increasing to 10 at 10th level and 15 at 15th level")),
})


def _w8_res(sub, cls, feature, name, uses, recharge, note, quotes, **kw):
    return {"subclass": sub, "class": cls, "feature": feature, "name": name, "uses": uses, "recharge": recharge,
            "note": note, "quotes": tuple((feature if q[0] is None else q[0], q[1]) for q in quotes), **kw}


def _w8_note(sub, cls, target, feature, name, note, quotes, **kw):
    return {"subclass": sub, "class": cls, "target": target, "feature": feature, "name": name, "note": note,
            "quotes": tuple((feature if q[0] is None else q[0], q[1]) for q in quotes), **kw}


def _w8_cd(sub, feature, name, note, quotes, **kw):
    """A Cleric domain Channel Divinity option: a sentence on `cleric:channel-divinity`."""
    return _w8_note(sub, "cleric", "cleric:channel-divinity", feature, name, note, quotes, **kw)


def _w8_divine_strike(sub, feature, domain, damage, quote):
    """The Cleric domain Divine Strike (level 8, 2d8 from 14): extra weapon damage once on each of your turns. The id
    names the domain so it never feeds the 2024 `cleric:divine-strike` attack-row notes."""
    return _w8_res(sub, "cleric", feature, f"Divine Strike ({domain} Domain)", None, None,
                   "Once on each of your turns when you hit a creature with a weapon attack, the attack deals an extra "
                   "{strike_dice} " + damage, ((None, quote), (None, "the extra damage increases to 2d8")),
                   dice="@strike_dice", level_vars={"strike_dice": DIVINE_STRIKE_DICE_2014})


_WARD = ("a number of times equal to your Wisdom modifier", "long rest")
_FLARE_NOTE = ("Reaction: when a creature within 30 feet that you can see attacks you, impose disadvantage on the attack "
               "roll (an attacker that can't be blinded is immune)")
_DUPLICITY_NOTE = ("Invoke Duplicity (action): create an illusory duplicate of yourself in an unoccupied space within 30 "
                   "feet for 1 minute (concentration); a bonus action moves it up to 30 feet, within 120 feet of you; you "
                   "can cast spells from its space and have advantage on attack rolls against a creature that can see it "
                   "when you and the duplicate are both within 5 feet of it")
_DUPLICITY_QUOTES = ((None, "As an action, you create a perfect illusion of yourself that lasts for 1 minute, or until you lose your concentration"),
                     (None, "you can move the illusion up to 30 feet to a space you can see"),
                     (None, "it must remain within 120 feet of you"),
                     (None, "you have advantage on attack rolls against that creature"))
_CLOAK_NOTE = "Cloak of Shadows (action): become invisible until the end of your next turn; you become visible if you attack or cast a spell"
_CLOAK_QUOTE = "As an action, you become invisible until the end of your next turn. You become visible if you attack or cast a spell."
_IMPROVED_DUPLICITY = "Improved Duplicity: up to four duplicates; a bonus action moves any number of them up to 30 feet each, within 120 feet of you"
_ID_QUOTES = "you can create up to four duplicates of yourself, instead of one, when you use Invoke Duplicity"
_PLUS10_BLESSING = ("{name} (reaction, 30 feet): spend a Channel Divinity use to give a creature making {rolls} a +10 bonus "
                    "to the roll, chosen after you see it and before the DM says whether it succeeds or fails")

_W8B_TAIL: tuple[dict, ...] = (
    # ---- Cleric: Ambition Domain (PSA)
    _w8_res("ambition-psa", "cleric", "ambition-psa-1-warding-flare", "Warding Flare", "@wis_min1", "long", _FLARE_NOTE,
            ((None, "you can use your reaction to impose disadvantage on the attack roll"), (None, _WARD[0] + " (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    # ---- Cleric: Death Domain (DMG)
    _w8_divine_strike("death-dmg", "death-dmg-8-divine-strike", "Death", "necrotic damage",
                      "the cleric can cause the attack to deal an extra 1d8 necrotic damage to the target"),
    # ---- Cleric: Forge Domain (XGE)
    _w8_res("forge-xge", "cleric", "forge-xge-1-blessing-of-the-forge", "Blessing of the Forge", 1, "long",
            "At the end of a long rest, touch one nonmagical suit of armor or simple or martial weapon: until the end of "
            "your next long rest (or your death) it is magical, +1 AC (armor) or +1 to attack and damage rolls (weapon)",
            ((None, "the object becomes a magic item, granting a +1 bonus to AC if it's armor or a +1 bonus to attack and damage rolls if it's a weapon"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    _w8_divine_strike("forge-xge", "forge-xge-8-divine-strike", "Forge", "fire damage",
                      "you can cause the attack to deal an extra 1d8 fire damage to the target"),
    # ---- Cleric: Grave Domain (XGE)
    _w8_res("grave-xge", "cleric", "grave-xge-1-eyes-of-the-grave", "Eyes of the Grave", "@wis_min1", "long",
            "Action: until the end of your next turn you know the location of any undead within 60 feet of you that isn't "
            "behind cover or protected from divination magic",
            ((None, "you know the location of any undead within 60 feet of you that isn't behind Cover"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_res("grave-xge", "cleric", "grave-xge-6-sentinel-at-deaths-door", "Sentinel at Death's Door", "@wis_min1", "long",
            "Reaction: when you or a creature you can see within 30 feet suffers a critical hit, turn it into a normal "
            "hit (effects triggered by a critical hit are canceled)",
            ((None, "when you or a creature you can see within 30 feet of you suffers a critical hit"),
             (None, "you can turn that hit into a normal hit"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"))),
    _w8_res("grave-xge", "cleric", "grave-xge-17-keeper-of-souls", "Keeper of Souls", None, None,
            "When an enemy you can see dies within 60 feet, you or one creature of your choice within 60 feet regains hit "
            "points equal to the enemy's number of Hit Dice (not while you are incapacitated); once until the start of "
            "your next turn",
            ((None, "regains hit points equal to the enemy's number of Hit Dice"),
             (None, "Once you use it, you can't do so again until the start of your next turn"))),
    # ---- Cleric: Knowledge Domain (PHB and PSA)
    *[_w8_res(sub, "cleric", f"{sub}-17-visions-of-the-past", "Visions of the Past", 1, "short-or-long",
              "Meditate for at least 1 minute (concentration) for up to your Wisdom score in minutes: Object Reading "
              "(the object's previous owners, within a number of days equal to your Wisdom score, 1 more minute per "
              "owner) or Area Reading (recent events in a room, street or similar space up to a 50-foot cube, going "
              "back a number of days equal to your Wisdom score)",
              ((None, "You can meditate in this way for a number of minutes equal to your Wisdom score"),
               (None, "up to a 50-foot cube"),
               (None, "Once you use this feature, you can't use it again until you finish a short or long rest")))
      for sub in ("knowledge-phb", "knowledge-psa")],
    # ---- Cleric: Light Domain (PHB)
    _w8_res("light-phb", "cleric", "light-phb-1-warding-flare", "Warding Flare", "@wis_min1", "long", _FLARE_NOTE,
            ((None, "you can use your reaction to impose disadvantage on the attack roll"), (None, _WARD[0] + " (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"),
             ("light-phb-6-improved-flare", "you can also use your Warding Flare feature when a creature that you can see within 30 feet of you attacks a creature other than you")),
            extras=(("light-phb-6-improved-flare", "Improved Flare: you can also use it when a creature you can see within 30 "
                     "feet attacks a creature other than you"),)),
    _w8_res("light-phb", "cleric", "light-phb-17-corona-of-light", "Corona of Light", None, None,
            "Action: an aura of sunlight for 1 minute or until you dismiss it with another action; bright light in a "
            "60-foot radius and dim light 30 feet beyond; your enemies in the bright light have disadvantage on saving "
            "throws against spells that deal fire or radiant damage",
            ((None, "an aura of sunlight that lasts for 1 minute or until you dismiss it using another action"),
             (None, "You emit bright light in a 60-foot radius and dim light 30 feet beyond that"),
             (None, "disadvantage on saving throws against any spell that deals fire or radiant damage"))),
    # ---- Cleric: Nature Domain (PHB)
    _w8_res("nature-phb", "cleric", "nature-phb-6-dampen-elements", "Dampen Elements", None, None,
            "Reaction: when you or a creature within 30 feet takes acid, cold, fire, lightning or thunder damage, grant it "
            "resistance to that instance of the damage",
            ((None, "when you or a creature within 30 feet of you takes acid, cold, fire, lightning, or thunder damage"),
             (None, "you can use your reaction to grant resistance to the creature against that instance of the damage"))),
    _w8_divine_strike("nature-phb", "nature-phb-8-divine-strike", "Nature", "cold, fire or lightning damage (your choice)",
                      "an extra 1d8 cold, fire, or lightning damage (your choice) to the target"),
    # ---- Cleric: Order Domain (TCE)
    _w8_res("order-tce", "cleric", "order-tce-6-embodiment-of-the-law", "Embodiment of the Law", "@wis_min1", "long",
            "If you cast an enchantment spell of 1st level or higher whose casting time is 1 action, change the casting "
            "time to 1 bonus action for that casting",
            ((None, "you can change the spell's casting time to 1 bonus action for this casting"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "you regain all expended uses of it when you finish a long rest"))),
    _w8_divine_strike("order-tce", "order-tce-8-divine-strike", "Order", "psychic damage",
                      "an extra 1d8 psychic damage to the target"),
    _w8_res("order-tce", "cleric", "order-tce-17-orders-wrath", "Order's Wrath", None, None,
            "If you deal your Divine Strike damage to a creature on your turn, you can curse it until the start of your "
            "next turn: the next time an ally hits it, it takes an extra 2d8 psychic damage and the curse ends; once per turn",
            ((None, "you can curse that creature until the start of your next turn"),
             (None, "the target also takes 2d8 psychic damage"),
             (None, "You can curse a creature in this way only once per turn"))),
    # ---- Cleric: Peace Domain (TCE)
    _w8_res("peace-tce", "cleric", "peace-tce-1-emboldening-bond", "Emboldening Bond", "@pb", "long",
            "Action: bond up to {pb} willing creatures within 30 feet (proficiency bonus; you can be one) for 10 minutes or "
            "until you use this feature again; while a bonded creature is within 30 feet of another, it can add a d4 to "
            "an attack roll, ability check or saving throw (once per turn)",
            ((None, "a number of willing creatures within 30 feet of you (this can include yourself) equal to your proficiency bonus"),
             (None, "for 10 minutes or until you use this feature again"),
             (None, "roll a d4 and add the number rolled"),
             (None, "no more than once per turn"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Cleric: Solidarity Domain (PSA)
    _w8_res("solidarity-psa", "cleric", "solidarity-psa-1-solidaritys-action", "Solidarity's Action", "@wis_min1", "long",
            "When you take the Help action to aid an ally's attack, you can make one weapon attack as a bonus action",
            ((None, "you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "You regain expended uses when you finish a long rest"))),
    _w8_divine_strike("solidarity-psa", "solidarity-psa-8-divine-strike", "Solidarity", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Strength Domain (PSA)
    _w8_divine_strike("strength-psa", "strength-psa-8-divine-strike", "Strength", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Tempest Domain (PHB)
    _w8_res("tempest-phb", "cleric", "tempest-phb-1-wrath-of-the-storm", "Wrath of the Storm", "@wis_min1", "long",
            "Reaction: when a creature within 5 feet that you can see hits you with an attack, it makes a Dexterity "
            "saving throw, taking 2d8 lightning or thunder damage (your choice) on a failure, half as much on a success",
            ((None, "When a creature within 5 feet of you that you can see hits you with an attack"),
             (None, "The creature takes 2d8 lightning or thunder damage (your choice) on a failed saving throw, and half as much damage on a successful one"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"))),
    _w8_divine_strike("tempest-phb", "tempest-phb-8-divine-strike", "Tempest", "thunder damage",
                      "an extra 1d8 thunder damage to the target"),
    # ---- Cleric: Trickery Domain (PHB)
    _w8_divine_strike("trickery-phb", "trickery-phb-8-divine-strike", "Trickery", "poison damage",
                      "an extra 1d8 poison damage to the target"),
    # ---- Cleric: Twilight Domain (TCE)
    _w8_res("twilight-tce", "cleric", "twilight-tce-1-eyes-of-night", "Eyes of Night", 1, "long",
            "Darkvision out to 300 feet (dim light as bright, darkness as dim); action: share it with up to {wis_min1} "
            "willing creature(s) within 10 feet (Wisdom modifier, minimum 1) for 1 hour; share it again before a long rest "
            "by expending a spell slot of any level",
            ((None, "You have darkvision out to a range of 300 feet"),
             (None, "up to a number of creatures equal to your Wisdom modifier (minimum of one creature)"),
             (None, "The shared darkvision lasts for 1 hour"),
             (None, "unless you expend a spell slot of any level to share it again"))),
    _w8_res("twilight-tce", "cleric", "twilight-tce-6-steps-of-night", "Steps of Night", "@pb", "long",
            "Bonus action when you are in dim light or darkness: a flying speed equal to your walking speed for 1 minute",
            ((None, "As a bonus action when you are in dim light or darkness, you can magically give yourself a flying speed equal to your walking speed for 1 minute"),
             (None, "You can use this bonus action a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("twilight-tce", "twilight-tce-8-divine-strike", "Twilight", "radiant damage",
                      "the attack to deal an extra 1d8 radiant damage"),
    # ---- Cleric: War Domain (PHB)
    _w8_res("war-phb", "cleric", "war-phb-1-war-priest", "War Priest", "@wis_min1", "long",
            "When you use the Attack action, you can make one weapon attack as a bonus action",
            ((None, "When you use the Attack action, you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("war-phb", "war-phb-8-divine-strike", "War", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Zeal Domain (PSA)
    _w8_res("zeal-psa", "cleric", "zeal-psa-1-priest-of-zeal", "Priest of Zeal", "@wis_min1", "long",
            "When you use the Attack action, you can make one weapon attack as a bonus action",
            ((None, "When you use the Attack action, you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("zeal-psa", "zeal-psa-8-divine-strike", "Zeal", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    _w8_res("zeal-psa", "cleric", "zeal-psa-17-blaze-of-glory", "Blaze of Glory", 1, "long",
            "When an attacker you can see reduces you to 0 hit points, use your reaction to move up to your speed toward it "
            "and make one melee weapon attack with advantage; a hit deals an extra 5d10 fire damage and an extra 5d10 damage "
            "of the weapon's type; then you fall unconscious and make death saving throws",
            ((None, "you can use your reaction to move up to your speed toward the attacker and make one melee weapon attack against it"),
             (None, "You make this attack with advantage"),
             (None, "an extra 5d10 fire damage and an extra 5d10 damage of the weapon's type"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of Dreams (XGE)
    _w8_res("dreams-xge", "druid", "dreams-xge-2-balm-of-the-summer-court", "Balm of the Summer Court", "@level", "long",
            "Bonus action: choose a creature you can see within 120 feet and spend up to {half_level} of your d6s (half your "
            "Druid level or less); it regains the total rolled in hit points and 1 temporary hit point per die spent",
            ((None, "a pool of fey energy represented by a number of d6s equal to your druid level"),
             (None, "spend a number of those dice equal to half your druid level or less"),
             (None, "The target also gains 1 temporary hit point per die spent"),
             (None, "You regain all expended dice when you finish a long rest")), die="d6"),
    _w8_res("dreams-xge", "druid", "dreams-xge-10-hidden-paths", "Hidden Paths", "@wis_min1", "long",
            "Bonus action: teleport up to 60 feet to an unoccupied space you can see; or action: teleport one willing "
            "creature you touch up to 30 feet",
            ((None, "you can teleport up to 60 feet to an unoccupied space you can see"),
             (None, "teleport one willing creature you touch up to 30 feet"),
             (None, "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("dreams-xge", "druid", "dreams-xge-14-walker-in-dreams", "Walker in Dreams", 1, "long",
            "When you finish a short rest, cast dream (you as the messenger), scrying or teleportation circle without a "
            "spell slot or components (the portal leads to where you last finished a long rest on your plane)",
            ((None, "When you finish a short rest, you can cast one of the following spells, without expending a spell slot or requiring material components: dream (with you as the messenger), scrying, or teleportation circle"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of the Shepherd (XGE)
    _w8_res("shepherd-xge", "druid", "shepherd-xge-2-spirit-totem", "Spirit Totem", 1, "short-or-long",
            "Bonus action: summon a spirit to a point within 60 feet (30-foot aura; a bonus action moves it up to 60 feet) "
            "for 1 minute. Bear: creatures of your choice in the aura gain {five_plus_level} temporary hit points (5 + "
            "Druid level) and you and your allies have advantage on Strength checks and saving throws there. Hawk: "
            "reaction to give advantage to an attack roll against a target in the aura. Unicorn: when you cast a healing "
            "spell with a slot, each creature of your choice in the aura also regains {level} hit points (Druid level)",
            ((None, "you can magically summon an incorporeal spirit to a point you can see within 60 feet of you"),
             (None, "The spirit creates an aura in a 30-foot radius around that point"),
             (None, "The spirit persists for 1 minute"),
             (None, "gains temporary hit points equal to 5 + your druid level"),
             (None, "each creature of your choice in the aura also regains hit points equal to your druid level"),
             (None, "Once you use this feature, you can't use it again until you finish a short or long rest"),
             ("shepherd-xge-10-guardian-spirit", "that creature regains a number of hit points equal to half your druid level")),
            extras=(("shepherd-xge-10-guardian-spirit", "Guardian Spirit: a beast or fey you summoned or created with a spell "
                     "that ends its turn in the aura regains {half_level} hit points (half your Druid level)"),)),
    _w8_res("shepherd-xge", "druid", "shepherd-xge-14-faithful-summons", "Faithful Summons", 1, "long",
            "If you are reduced to 0 hit points or incapacitated against your will, gain the benefits of conjure animals as "
            "a 9th-level spell: four beasts of challenge rating 2 or lower appear within 20 feet and last 1 hour with no "
            "concentration",
            ((None, "It summons four beasts of your choice that are challenge rating 2 or lower"),
             (None, "The conjured beasts appear within 20 feet of you"),
             (None, "The spell lasts for 1 hour, requiring no concentration"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of Spores (TCE)
    _w8_res("spores-tce", "druid", "spores-tce-2-halo-of-spores", "Halo of Spores", None, None,
            "Reaction: when a creature you can see moves into a space within 10 feet of you or starts its turn there, it "
            "takes {halo} necrotic damage unless it succeeds on a Constitution saving throw (DC {dc_wis}, your spell save DC)",
            ((None, "deal 1d4 necrotic damage to that creature unless it succeeds on a Constitution saving throw against your spell save DC"),
             (None, "a creature you can see moves into a space within 10 feet of you"),
             (None, "increases to 1d6 at 6th level, 1d8 at 10th level, and 1d10 at 14th level")),
            dice="@halo", level_vars={"halo": HALO_OF_SPORES_DICE_2014}),
    _w8_res("spores-tce", "druid", "spores-tce-6-fungal-infestation", "Fungal Infestation", "@wis_min1", "long",
            "Reaction: a Small or Medium beast or humanoid that dies within 10 feet of you stands up with 1 hit point as a "
            "zombie that obeys your mental commands (Attack action only) for 1 hour",
            ((None, "If a beast or a humanoid that is Small or Medium dies within 10 feet of you, you can use your reaction to animate it, causing it to stand up immediately with 1 hit point"),
             (None, "It remains animate for 1 hour"),
             (None, "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    # ---- Druid: Circle of the Stars (TCE)
    _w8_res("stars-tce", "druid", "stars-tce-2-star-map", "Star Map", "@pb", "long",
            "While holding your star map you know the guidance cantrip and have guiding bolt prepared (a druid spell that "
            "doesn't count against your prepared spells); cast guiding bolt without a spell slot; a replacement map takes "
            "a 1-hour ceremony during a short or long rest",
            ((None, "You can cast guiding bolt without expending a spell slot"),
             (None, "a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"),
             (None, "you can perform a 1-hour ceremony to magically create a replacement"))),
    _w8_res("stars-tce", "druid", "stars-tce-6-cosmic-omen", "Cosmic Omen", "@pb", "long",
            "After each long rest, consult your star map and roll a die: even is Weal, odd is Woe until your next long "
            "rest. Reaction: when a creature you can see within 30 feet is about to make an attack roll, saving throw or "
            "ability check, roll a d6 and add it (Weal) or subtract it (Woe)",
            ((None, "roll a d6 and add the number rolled to the total"),
             (None, "roll a d6 and subtract the number rolled from the total"),
             (None, "Whenever a creature you can see within 30 feet of you is about to make an attack roll, a saving throw, or an ability check"),
             (None, "You can use this reaction a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Druid: Circle of Wildfire (TCE)
    _w8_res("wildfire-tce", "druid", "wildfire-tce-10-cauterizing-flames", "Cauterizing Flames", "@pb", "long",
            "When a Small or larger creature dies within 30 feet of you or your wildfire spirit, a spectral flame lasts 1 "
            "minute in its space; reaction when a creature you can see enters it: heal that creature or deal it fire "
            "damage of 2d10{wis:+d} (2d10 + Wisdom modifier)",
            ((None, "dies within 30 feet of you or your wildfire spirit"),
             (None, "flickers there for 1 minute"),
             (None, "The healing or damage equals 2d10 + your Wisdom modifier"),
             (None, "You can use this reaction a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("wildfire-tce", "druid", "wildfire-tce-14-blazing-revival", "Blazing Revival", 1, "long",
            "If your wildfire spirit is within 120 feet when you are reduced to 0 hit points, drop it to 0 hit points: you "
            "regain half your hit points and rise to your feet",
            ((None, "If the spirit is within 120 feet of you when you are reduced to 0 hit points"),
             (None, "You then regain half your hit points"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Fighter: Cavalier (XGE)
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-3-unwavering-mark", "Unwavering Mark", "@str_min1", "long",
            "When you hit a creature with a melee weapon attack, mark it until the end of your next turn: while within 5 "
            "feet of you it has disadvantage on attack rolls that don't target you; if it damages anyone else, on your next "
            "turn you can make a special melee weapon attack against it as a bonus action with advantage, dealing extra "
            "damage equal to half your Fighter level ({half_level}); the uses count these special attacks",
            ((None, "you can mark the creature until the end of your next turn"),
             (None, "the attack's weapon deals extra damage to the target equal to half your fighter level"),
             (None, "a number of times equal to your Strength modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-7-warding-maneuver", "Warding Maneuver", "@con_min1", "long",
            "Reaction: when you or a creature you can see within 5 feet is hit by an attack and you wield a melee weapon or "
            "a shield, roll 1d8 and add it to the target's AC against that attack; if the attack still hits, the target has "
            "resistance to its damage",
            ((None, "you can roll 1d8 as a reaction if you're wielding a melee weapon or a shield"),
             (None, "the target has resistance against the attack's damage"),
             (None, "a number of times equal to your Constitution modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-15-ferocious-charger", "Ferocious Charger", None, None,
            "If you move at least 10 feet in a straight line right before hitting a creature with an attack, it makes a "
            "Strength saving throw (DC {dc_str}) or is knocked prone; once on each of your turns",
            ((None, "that target must succeed on a Strength saving throw (DC 8 + your proficiency bonus + your Strength modifier) or be knocked prone"),
             (None, "You can use this feature only once on each of your turns"))),
    # ---- Fighter: Echo Knight (EGW)
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-3-manifest-echo", "Manifest Echo", None, None,
            "Bonus action: manifest an echo in an unoccupied space you can see within 15 feet (AC {echo_ac}, 1 hit point, "
            "immune to all conditions, uses your saving throw bonuses); you can move it up to 30 feet without an action "
            "(destroyed if it ends your turn more than 30 feet from you); bonus action: swap places with it at a cost of "
            "15 feet of your movement; your attacks can originate from its space; opportunity attacks can too",
            ((None, "an echo of yourself in an unoccupied space you can see within 15 feet of you"),
             (None, "Your echo has AC 14 + your proficiency bonus, 1 hit point, and immunity to all conditions"),
             (None, "move up to 30 feet in any direction"),
             (None, "at a cost of 15 feet of your movement"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-3-unleash-incarnation", "Unleash Incarnation", "@con_min1", "long",
            "Whenever you take the Attack action, make one additional melee attack from the echo's position",
            ((None, "you can make one additional melee attack from the echo's position"),
             (None, "You can use this feature a number of times equal to your Constitution modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"),
             ("echo-knight-egw-18-legion-of-one", "create two echoes with your Manifest Echo feature"),
             ("echo-knight-egw-18-legion-of-one", "you regain one use of that feature")),
            extras=(("echo-knight-egw-18-legion-of-one", "Legion of One: two echoes can coexist; when you roll initiative with "
                     "no uses left you regain one use"),)),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-7-echo-avatar", "Echo Avatar", None, None,
            "Action: see through your echo's eyes and hear through its ears for up to 10 minutes (you are deafened and "
            "blinded); the echo can be up to 1,000 feet from you without being destroyed",
            ((None, "You can sustain this effect for up to 10 minutes"),
             (None, "it can be up to 1,000 feet away from you without being destroyed"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-10-shadow-martyr", "Shadow Martyr", 1, "short-or-long",
            "Reaction, before an attack roll against another creature you can see: teleport your echo to an unoccupied "
            "space within 5 feet of the target; the attack is made against your echo",
            ((None, "teleport the echo to an unoccupied space within 5 feet of the targeted creature"),
             (None, "Once you use this feature, you can't use it again until you finish a short or long rest"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-15-reclaim-potential", "Reclaim Potential", "@con_min1", "long",
            "When an echo of yours is destroyed by taking damage, gain 2d6{con:+d} temporary hit points (2d6 + Constitution "
            "modifier) if you have none",
            ((None, "a number of temporary hit points equal to 2d6 + your Constitution modifier, provided you don't already have temporary hit points"),
             (None, "You can use this feature a number of times equal to your Constitution modifier (a minimum of once)"))),
    # ---- Fighter: Rune Knight (TCE)
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-3-rune-carver", "Rune Carver", None, None,
            "After a long rest, touch up to {runes} objects (the runes you know) and inscribe a different rune on each; a "
            "rune stays until your next long rest; Rune Magic save DC {dc_con}",
            ((None, "Whenever you finish a long rest, you can touch a number of objects equal to the number of runes you know"),
             (None, "your Rune Magic save DC equals 8 + your proficiency bonus + your Constitution modifier"),
             (None, "Fighter Level | Number of Runes 3rd | 2 7th | 3 10th | 4 15th | 5"),
             ("rune-knight-tce-15-master-of-runes", "You can invoke each rune you know from your Rune Carver feature twice, rather than once, and you regain all expended uses when you finish a short or long rest")),
            level_vars={"runes": RUNES_KNOWN_2014},
            extras=(("rune-knight-tce-15-master-of-runes", "Master of Runes: you can invoke each rune you know twice, rather "
                     "than once, and regain all expended uses on a short or long rest"),)),
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-3-giants-might", "Giant's Might", "@pb", "long",
            "Bonus action, 1 minute: if smaller than Large you become Large; advantage on Strength checks and Strength "
            "saving throws; once on each of your turns one weapon or unarmed attack that hits deals an extra {gm_dice} damage",
            ((None, "which last for 1 minute"),
             (None, "If you are smaller than Large, you become Large"),
             (None, "You have advantage on Strength checks and Strength saving throws"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses of it when you finish a long rest"),
             ("rune-knight-tce-18-runic-juggernaut", "your size can increase to Huge, and while you are that size, your reach increases by 5 feet")),
            dice="@gm_dice", level_vars={"gm_dice": GIANTS_MIGHT_DICE_2014},
            extras=(("rune-knight-tce-18-runic-juggernaut", "Runic Juggernaut: your size can increase to Huge, and while you "
                     "are Huge your reach increases by 5 feet"),)),
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-7-runic-shield", "Runic Shield", "@pb", "long",
            "Reaction: when another creature you can see within 60 feet is hit by an attack roll, force the attacker to "
            "reroll the d20 and use the new roll",
            ((None, "When another creature you can see within 60 feet of you is hit by an attack roll, you can use your reaction to force the attacker to reroll the d20 and use the new roll"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Fighter: Samurai (XGE)
    _w8_res("samurai-xge", "fighter", "samurai-xge-3-fighting-spirit", "Fighting Spirit", 3, "long",
            "Bonus action: advantage on weapon attack rolls until the end of the current turn and {fs_thp} temporary hit points",
            ((None, "As a bonus action on your turn, you can give yourself advantage on weapon attack rolls until the end of the current turn"),
             (None, "you also gain 5 temporary hit points"),
             (None, "increasing to 10 at 10th level and 15 at 15th level"),
             (None, "You can use this feature three times, and you regain all expended uses of it when you finish a long rest"),
             ("samurai-xge-10-tireless-spirit", "when you roll initiative and have no uses of Fighting Spirit remaining, you regain one use")),
            level_vars={"fs_thp": FIGHTING_SPIRIT_THP_2014},
            extras=(("samurai-xge-10-tireless-spirit", "Tireless Spirit: when you roll initiative and have no uses left, you "
                     "regain one use"),)),
    _w8_res("samurai-xge", "fighter", "samurai-xge-18-strength-before-death", "Strength before Death", 1, "long",
            "If damage reduces you to 0 hit points without killing you outright, use your reaction to delay falling "
            "unconscious and take an extra turn immediately (death saving throws still apply)",
            ((None, "you can use your reaction to delay falling unconscious, and you can immediately take an extra turn"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
)

_W8B_NOTES: tuple[dict, ...] = (
    # ---- Cleric Channel Divinity options (sentences on `cleric:channel-divinity`)
    _w8_cd("ambition-psa", "ambition-psa-2-channel-divinity:-invoke-duplicity", "Invoke Duplicity", _DUPLICITY_NOTE,
           _DUPLICITY_QUOTES + (("ambition-psa-17-improved-duplicity", _ID_QUOTES),),
           extras=(("ambition-psa-17-improved-duplicity", _IMPROVED_DUPLICITY),)),
    _w8_cd("ambition-psa", "ambition-psa-6-channel-divinity:-cloak-of-shadows", "Cloak of Shadows", _CLOAK_NOTE, ((None, _CLOAK_QUOTE),)),
    _w8_cd("arcana-scag", "arcana-scag-2-channel-divinity:-arcane-abjuration", "Arcane Abjuration",
           "Arcane Abjuration (action, 30 feet): one celestial, elemental, fey or fiend that can see or hear you makes a "
           "Wisdom saving throw or is turned for 1 minute or until it takes damage{banish}",
           ((None, "one celestial, elemental, fey, or fiend of your choice that is within 30 feet of you must make a Wisdom saving throw"),
            (None, "it is turned for 1 minute or until it takes any damage"),
            (None, "the creature is banished for 1 minute (as in the banishment spell, no concentration required) if it isn't on its plane of origin")),
           level_vars={"banish": ARCANE_BANISHMENT_2014}),
    _w8_cd("death-dmg", "death-dmg-2-channel-divinity:-touch-of-death", "Touch of Death",
           "Touch of Death: when you hit a creature with a melee attack, spend a Channel Divinity use to deal extra "
           "necrotic damage equal to {five_plus_twice_level} (5 + twice your Cleric level)",
           ((None, "deal extra necrotic damage to the target"), (None, "The damage equals 5 + twice his or her cleric level"))),
    _w8_cd("forge-xge", "forge-xge-2-channel-divinity:-artisans-blessing", "Artisan's Blessing",
           "Artisan's Blessing (1-hour ritual): craft a nonmagical item that includes metal and is worth no more than 100 "
           "gp (a simple or martial weapon, a suit of armor, ten pieces of ammunition, a set of tools or another metal "
           "object), paid for with metal of equal value that you lay out",
           ((None, "You conduct an hour-long ritual"), (None, "worth no more than 100 gp"))),
    _w8_cd("grave-xge", "grave-xge-2-channel-divinity:-path-to-the-grave", "Path to the Grave",
           "Path to the Grave (action, 30 feet): curse a creature you can see until the end of your next turn; the next "
           "attack by you or an ally that hits it makes it vulnerable to all of that attack's damage, then the curse ends",
           ((None, "you choose one creature you can see within 30 feet of you, cursing it until the end of your next turn"),
            (None, "the creature has vulnerability to all of that attack's damage"))),
    *[_w8_cd(sub, f"{sub}-2-channel-divinity:-knowledge-of-the-ages", "Knowledge of the Ages",
             "Knowledge of the Ages (action): choose one skill or tool; for 10 minutes you have proficiency with it",
             ((None, "For 10 minutes, you have proficiency with the chosen skill or tool"),))
      for sub in ("knowledge-phb", "knowledge-psa")],
    *[_w8_cd(sub, f"{sub}-6-channel-divinity:-read-thoughts", "Read Thoughts",
             "Read Thoughts (action, 60 feet): a creature you can see makes a Wisdom saving throw (on a success you can't "
             "use this on it again until a long rest); on a failure you read its surface thoughts within 60 feet for 1 "
             "minute and can use your action to cast suggestion on it without a spell slot (it automatically fails the save)",
             ((None, "choose one creature that you can see within 60 feet of you"),
              (None, "This effect lasts for 1 minute"),
              (None, "cast the suggestion spell on the creature without expending a spell slot"),
              (None, "you can't use this feature on it again until you finish a long rest")))
      for sub in ("knowledge-phb", "knowledge-psa")],
    _w8_cd("light-phb", "light-phb-2-channel-divinity:-radiance-of-the-dawn", "Radiance of the Dawn",
           "Radiance of the Dawn (action): dispel magical darkness within 30 feet; each hostile creature within 30 feet "
           "makes a Constitution saving throw, taking radiant damage of 2d10 + {level} (2d10 + Cleric level) on a failure, "
           "half on a success; a creature with cover from you is unaffected",
           ((None, "any magical darkness within 30 feet of you is dispelled"),
            (None, "radiant damage equal to 2d10 + your cleric level on a failed saving throw, and half as much damage on a successful one"),
            (None, "A creature that has Cover from you is not affected"))),
    _w8_cd("nature-phb", "nature-phb-2-channel-divinity:-charm-animals-and-plants", "Charm Animals and Plants",
           "Charm Animals and Plants (action): each beast or plant creature that can see you within 30 feet makes a Wisdom "
           "saving throw or is charmed by you for 1 minute or until it takes damage",
           ((None, "Each beast or plant creature that can see you within 30 feet of you must make a Wisdom saving throw"),
            (None, "it is charmed by you for 1 minute or until it takes damage"))),
    _w8_cd("order-tce", "order-tce-2-channel-divinity:-orders-demand", "Order's Demand",
           "Order's Demand (action, 30 feet): each creature of your choice that can see or hear you makes a Wisdom saving "
           "throw or is charmed by you until the end of your next turn or until it takes damage; charmed creatures that fail "
           "can be made to drop what they hold",
           ((None, "each creature of your choice that can see or hear you within 30 feet of you must succeed on a Wisdom saving throw or be charmed by you until the end of your next turn or until the charmed creature takes any damage"),
            (None, "You can also cause any of the charmed creatures to drop what they are holding when they fail the saving throw"))),
    _w8_cd("peace-tce", "peace-tce-2-channel-divinity:-balm-of-peace", "Balm of Peace",
           "Balm of Peace (action): move up to your speed without provoking opportunity attacks; each creature you move "
           "within 5 feet of can regain 2d6 {wis:+d} hit points (minimum 1 hit point in total), once per use",
           ((None, "restore a number of hit points to that creature equal to 2d6 + your Wisdom modifier (minimum of 1 hit point)"),
            (None, "move up to your speed, without provoking opportunity attacks"),
            (None, "A creature can receive this healing only once whenever you take this action"))),
    _w8_cd("solidarity-psa", "solidarity-psa-2-channel-divinity:-preserve-life", "Preserve Life",
           "Preserve Life (action, 30 feet): restore up to {five_level} hit points (5 x Cleric level) divided among "
           "creatures you choose, none above half its hit point maximum; not on an undead or a construct",
           ((None, "restore a number of hit points equal to five times your cleric level"),
            (None, "This feature can restore a creature to no more than half of its hit point maximum"),
            (None, "You can't use this feature on an undead or a construct"))),
    _w8_cd("solidarity-psa", "solidarity-psa-6-oketras-blessing", "Oketra's Blessing",
           _PLUS10_BLESSING.replace("{name}", "Oketra's Blessing").replace("{rolls}", "an attack roll"),
           ((None, "when a creature within 30 feet of you makes an attack roll, you can use your reaction to grant that creature a +10 bonus to the roll, using your Channel Divinity"),)),
    _w8_cd("strength-psa", "strength-psa-2-channel-divinity:-feat-of-strength", "Feat of Strength",
           "Feat of Strength: spend a Channel Divinity use to gain a +10 bonus to an attack roll, ability check or saving "
           "throw using Strength, chosen after you see the roll and before the DM says whether it succeeds or fails",
           ((None, "you can use your Channel Divinity to gain a +10 bonus to the roll"),)),
    _w8_cd("strength-psa", "strength-psa-6-rhonass-blessing", "Rhonas's Blessing",
           _PLUS10_BLESSING.replace("{name}", "Rhonas's Blessing").replace("{rolls}", "an attack roll, ability check or saving throw using Strength"),
           ((None, "when a creature within 30 feet of you makes an attack roll, ability check, or saving throw using Strength, you can use your reaction to grant that creature a +10 bonus to the roll"),)),
    _w8_cd("tempest-phb", "tempest-phb-2-channel-divinity:-destructive-wrath", "Destructive Wrath",
           "Destructive Wrath: when you roll lightning or thunder damage, spend a Channel Divinity use to deal maximum "
           "damage instead of rolling",
           ((None, "you can use your Channel Divinity to deal maximum damage, instead of rolling"),)),
    _w8_cd("trickery-phb", "trickery-phb-2-channel-divinity:-invoke-duplicity", "Invoke Duplicity", _DUPLICITY_NOTE,
           _DUPLICITY_QUOTES + (("trickery-phb-17-improved-duplicity", _ID_QUOTES),),
           extras=(("trickery-phb-17-improved-duplicity", _IMPROVED_DUPLICITY),)),
    _w8_cd("trickery-phb", "trickery-phb-6-channel-divinity:-cloak-of-shadows", "Cloak of Shadows", _CLOAK_NOTE, ((None, _CLOAK_QUOTE),)),
    _w8_cd("twilight-tce", "twilight-tce-2-channel-divinity:-twilight-sanctuary", "Twilight Sanctuary",
           "Twilight Sanctuary (action, 1 minute): a 30-foot-radius sphere of dim twilight centered on you; whenever a "
           "creature (you included) ends its turn in it, grant it 1d6 + {level} temporary hit points (1d6 + Cleric level) or end a "
           "charmed or frightened effect on it",
           ((None, "has a 30-foot radius"),
            (None, "it lasts for 1 minute"),
            (None, "temporary hit points equal to 1d6 plus your cleric level"))),
    _w8_cd("war-phb", "war-phb-2-channel-divinity:-guided-strike", "Guided Strike",
           "Guided Strike: when you make an attack roll, spend a Channel Divinity use to gain a +10 bonus to it, chosen "
           "after you see the roll and before the DM says whether it hits or misses",
           ((None, "you can use your Channel Divinity to gain a +10 bonus to the roll"),)),
    _w8_cd("war-phb", "war-phb-6-channel-divinity:-war-gods-blessing", "War God's Blessing",
           _PLUS10_BLESSING.replace("{name}", "War God's Blessing").replace("{rolls}", "an attack roll"),
           ((None, "when a creature within 30 feet of you makes an attack roll, you can use your reaction to grant that creature a +10 bonus to the roll, using your Channel Divinity"),)),
    _w8_cd("zeal-psa", "zeal-psa-2-channel-divinity:-consuming-fervor", "Consuming Fervor",
           "Consuming Fervor: when you roll fire or thunder damage, spend a Channel Divinity use to deal maximum damage "
           "instead of rolling",
           ((None, "When you roll fire or thunder damage, you can use your Channel Divinity to deal maximum damage instead of rolling"),)),
    # ---- Druid: sentences on Wild Shape
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-2-combat-wild-shape", "Combat Wild Shape",
             "Combat Wild Shape: use Wild Shape as a bonus action; while transformed, a bonus action and a spell slot "
             "regain 1d8 hit points per level of the slot",
             ((None, "use Wild Shape on your turn as a bonus action"),
              (None, "expend one spell slot to regain 1d8 hit points per level of the spell slot expended"))),
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-2-circle-forms", "Circle Forms",
             "Circle Forms: Wild Shape into a beast of challenge rating {moon_cr} or lower ({moon_limit}), ignoring the "
             "Max. CR column of the Beast Shapes table",
             ((None, "you can use your Wild Shape to transform into a beast with a challenge rating as high as 1 (you ignore the Max. CR column of the Beast Shapes table"),
              (None, "challenge rating as high as your druid level divided by 3, rounded down")),
             level_vars={"moon_cr": CIRCLE_FORMS_CR_2014, "moon_limit": CIRCLE_FORMS_LIMIT_2014}),
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-10-elemental-wild-shape", "Elemental Wild Shape",
             "Elemental Wild Shape: expend two uses of Wild Shape at the same time to become an air, earth, fire or water "
             "elemental",
             ((None, "you can expend two uses of Wild Shape at the same time to transform into an air elemental, an earth elemental, a fire elemental, or a water elemental"),)),
    _w8_note("spores-tce", "druid", "druid:wild-shape", "spores-tce-2-symbiotic-entity", "Symbiotic Entity",
             "Symbiotic Entity (action): expend a use of Wild Shape to awaken your spores instead of transforming and gain "
             "{four_level} temporary hit points (4 per Druid level); for 10 minutes, until they are gone or you Wild Shape: "
             "your Halo of Spores damage die is rolled twice and your melee weapon hits deal an extra 1d6 necrotic damage",
             ((None, "you can expend a use of your Wild Shape feature to awaken those spores, rather than transforming into a beast form, and you gain 4 temporary hit points for each level you have in this class"),
              (None, "These benefits last for 10 minutes"),
              (None, "Your melee weapon attacks deal an extra 1d6 necrotic damage to any target they hit"),
              (None, "roll the damage die a second time and add it to the total"),
              ("spores-tce-10-spreading-spores", "you can hurl spores up to 30 feet away, where they swirl in a 10-foot cube for 1 minute"),
              ("spores-tce-10-spreading-spores", "takes your Halo of Spores damage, unless the creature succeeds on a Constitution saving throw against your spell save DC")),
             extras=(("spores-tce-10-spreading-spores", "Spreading Spores (bonus action while Symbiotic Entity is active): hurl "
                      "spores up to 30 feet into a 10-foot cube for 1 minute; a creature that moves into it or starts its "
                      "turn there takes your Halo of Spores damage unless it passes a Constitution saving throw (DC {dc_wis})"),)),
    _w8_note("stars-tce", "druid", "druid:wild-shape", "stars-tce-2-starry-form", "Starry Form",
             "Starry Form (bonus action): expend a use of Wild Shape to take a starry form for 10 minutes (bright light in a "
             "10-foot radius, dim light 10 feet more) with one constellation: Archer (a bonus-action ranged spell attack "
             "within 60 feet, {star_dice}{wis:+d} radiant damage), Chalice (when you cast a healing spell with a slot, you or "
             "a creature within 30 feet regains {star_dice}{wis:+d} hit points) or Dragon (treat a d20 roll of 9 or lower as "
             "10 on Intelligence and Wisdom checks and concentration saves)",
             ((None, "you can expend a use of your Wild Shape feature to take on a starry form"),
              (None, "The form lasts for 10 minutes"),
              (None, "This form sheds bright light in a 10-foot radius and dim light for an additional 10 feet"),
              ("stars-tce-2-archer", "1d8 + your Wisdom modifier"),
              ("stars-tce-2-archer", "a luminous arrow that targets one creature within 60 feet of you"),
              ("stars-tce-2-chalice", "you or another creature within 30 feet of you can regain hit points equal to 1d8 + your Wisdom modifier"),
              ("stars-tce-2-dragon", "you can treat a roll of 9 or lower on the d20 as a 10"),
              ("stars-tce-10-twinkling-constellations", "you have a flying speed of 20 feet and can hover")),
             level_vars={"star_dice": STARRY_FORM_DICE_2014},
             extras=(("stars-tce-10-twinkling-constellations", "Twinkling Constellations: while the Dragon is active you have a "
                      "flying speed of 20 feet and can hover; you can change the constellation at the start of each of your turns"),)),
    _w8_note("wildfire-tce", "druid", "druid:wild-shape", "wildfire-tce-2-summon-wildfire-spirit", "Summon Wildfire Spirit",
             "Summon Wildfire Spirit (action): expend a use of Wild Shape to summon your wildfire spirit within 30 feet; each "
             "other creature within 10 feet of it makes a Dexterity saving throw (DC {dc_wis}) or takes 2d6 fire damage; the "
             "spirit (proficiency bonus {pb}) lasts 1 hour, until it drops to 0 hit points, until you summon it again or "
             "until you die",
             ((None, "you can expend one use of your Wild Shape feature to summon your wildfire spirit"),
              (None, "within 30 feet of you"),
              (None, "within 10 feet of the spirit (other than you)"),
              (None, "against your spell save DC or take 2d6 fire damage"),
              (None, "The spirit manifests for 1 hour"),
              ("wildfire-tce-6-enhanced-bond", "roll a d8, and you gain a bonus equal to the number rolled to one damage or healing roll of the spell")),
             extras=(("wildfire-tce-6-enhanced-bond", "Enhanced Bond: while the spirit is summoned, roll a d8 and add it to one "
                      "damage or healing roll of a fire-damage or healing spell you cast"),)),
    # ---- Fighter: sentences on Second Wind, Action Surge, Indomitable
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:second-wind", "purple-dragon-knight-scag-3-rallying-cry", "Rallying Cry",
             "Rallying Cry: when you use Second Wind, up to three allies within 60 feet that can see or hear you regain "
             "{level} hit points each (your Fighter level)",
             ((None, "you can choose up to three creatures within 60 feet of you that are allied with you. Each one regains hit points equal to your fighter level"),)),
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:action-surge", "purple-dragon-knight-scag-10-inspiring-surge", "Inspiring Surge",
             "Inspiring Surge: when you use Action Surge, one ally within 60 feet that can see or hear you makes one melee "
             "or ranged weapon attack with its reaction",
             ((None, "you can choose one creature within 60 feet of you that is allied with you. That creature can make one melee or ranged weapon attack with its reaction"),
              ("purple-dragon-knight-scag-18-inspiring-surge", "you can choose two allies within 60 feet of you, rather than one")),
             extras=(("purple-dragon-knight-scag-18-inspiring-surge", "from 18th level you can choose two allies within 60 feet "
                      "instead of one"),)),
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:indomitable", "purple-dragon-knight-scag-15-bulwark", "Bulwark",
             "Bulwark: when you use Indomitable to reroll an Intelligence, Wisdom or Charisma saving throw, one ally within "
             "60 feet that failed the same save and can see or hear you also rerolls it and must use the new roll",
             ((None, "you can choose one ally within 60 feet of you that also failed its saving throw against the same effect"),)),
)

SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + _W8B_TAIL
SUBCLASS_NOTES_2014_BOOKS = SUBCLASS_NOTES_2014_BOOKS + _W8B_NOTES

# ---- W8c: Monk, Paladin, Ranger, Rogue (book subclasses) ----------------------------------------------------------------
# Tables that live only in the text (pinned in BOOK_TABLE_PINS_2014, like the W8a / W8b ones).
BREATH_ROLLS_2014 = ((3, 2), (11, 3))
ELEMENTAL_KI_CAP_2014 = ((3, "extra ki points can't raise a spell's level before Monk level 5"),
                         (5, "you can spend up to 3 ki points in total on one discipline spell to raise its level"),
                         (9, "you can spend up to 4 ki points in total on one discipline spell to raise its level"),
                         (13, "you can spend up to 5 ki points in total on one discipline spell to raise its level"),
                         (17, "you can spend up to 6 ki points in total on one discipline spell to raise its level"))
PALADIN_AURA_FEET_2014 = ((7, 10), (18, 30))
DRAKES_BREATH_DICE_2014 = ((11, "8d6"), (15, "10d6"))
DREADFUL_STRIKES_DICE_2014 = ((3, "1d4"), (11, "1d6"))
PLANAR_WARRIOR_DICE_2014 = ((3, "1d8"), (11, "2d8"))
GATHERED_SWARM_DICE_2014 = ((3, "1d6"), (11, "1d8"))

BOOK_TABLE_PINS_2014.update({
    "BREATH_ROLLS_2014": (("ascendant-dragon-ftd-3-breath-of-the-dragon", "equal to two rolls of your Martial Arts die on a failed save"),
                          ("ascendant-dragon-ftd-3-breath-of-the-dragon", "At 11th level, the damage of this feature increases to three rolls of your Martial Arts die")),
    "ELEMENTAL_KI_CAP_2014": (("four-elements-phb-3-disciple-of-the-elements",
                               "At 5th level, you may spend up to 3 ki points; this increases to 4 ki points at 9th level, 5 at 13th level, and 6 at 17th level"),
                              ("four-elements-phb-3-disciple-of-the-elements", "Once you reach 5th level in this class, you can spend additional ki points to increase the level of an elemental discipline spell that you cast")),
    "PALADIN_AURA_FEET_2014": (("conquest-xge-7-aura-of-conquest", "The aura extends 10 feet from you in every direction"),
                               ("conquest-xge-7-aura-of-conquest", "At 18th level, the range of this aura increases to 30 feet."),
                               ("oathbreaker-dmg-7-aura-of-hate", "within 10 feet of the paladin"),
                               ("oathbreaker-dmg-7-aura-of-hate", "At 18th level, the range of this aura increases to 30 feet."),
                               ("watchers-tce-7-aura-of-the-sentinel", "within 10 feet of you roll initiative"),
                               ("watchers-tce-7-aura-of-the-sentinel", "At 18th level, the range of this aura increases to 30 feet.")),
    "DRAKES_BREATH_DICE_2014": (("drakewarden-ftd-11-drakes-breath", "taking 8d6 damage on a failed save, or half as much damage on a successful one"),
                                ("drakewarden-ftd-11-drakes-breath", "This damage increases to 10d6 when you reach 15th level in this class")),
    "DREADFUL_STRIKES_DICE_2014": (("fey-wanderer-tce-3-dreadful-strikes", "you can deal an extra 1d4 psychic damage to the target"),
                                   ("fey-wanderer-tce-3-dreadful-strikes", "The extra damage increases to 1d6 when you reach 11th level in this class")),
    "PLANAR_WARRIOR_DICE_2014": (("horizon-walker-xge-3-planar-warrior", "the creature takes an extra 1d8 force damage from the attack"),
                                 ("horizon-walker-xge-3-planar-warrior", "the extra damage increases to 2d8")),
    "GATHERED_SWARM_DICE_2014": (("swarmkeeper-tce-3-gathered-swarm", "The attack's target takes 1d6 piercing damage from the swarm"),
                                 ("swarmkeeper-tce-11-mighty-swarm", "The damage of Gathered Swarm increases to 1d8")),
})

_KI_DC = ("ki", "Ki save DC = 8 + your proficiency bonus + your Wisdom modifier")
_PAL = "paladin:channel-divinity"


def _w8_pcd(sub, feature, name, note, quotes, **kw):
    """A Paladin Channel Divinity option: a sentence on `paladin:channel-divinity`."""
    return _w8_note(sub, "paladin", _PAL, feature, name, note, quotes, **kw)


_W8C_TAIL: tuple[dict, ...] = (
    # ---- Monk: Way of the Ascendant Dragon (FTD)
    _w8_res("ascendant-dragon-ftd", "monk", "ascendant-dragon-ftd-3-breath-of-the-dragon", "Breath of the Dragon", "@pb", "long",
            "Replace one attack of the Attack action with a 20-foot cone or a 30-foot line 5 feet wide: each creature in it "
            "makes a Dexterity saving throw (ki save DC {dc_wis}) and takes {rolls}{ma_die} damage of a chosen type (acid, "
            "cold, fire, lightning or poison), half as much on a success; with no uses left you can spend 2 ki points to "
            "use it again",
            ((None, "in either a 20-foot cone or a 30-foot line that is 5 feet wide (your choice)"),
             (None, "Each creature in that area must make a Dexterity saving throw against your ki save DC"),
             (None, "equal to two rolls of your Martial Arts die on a failed save, or half as much damage on a successful one"),
             (None, "At 11th level, the damage of this feature increases to three rolls of your Martial Arts die"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"),
             (None, "While you have no uses available, you can spend 2 ki points to use this feature again"),
             ("ascendant-dragon-ftd-17-ascendant-aspect", "you can spend 1 ki point to augment its shape and power"),
             ("ascendant-dragon-ftd-17-ascendant-aspect", "either a 60-foot cone or a 90-foot line that is 5 feet wide (your choice)"),
             ("ascendant-dragon-ftd-17-ascendant-aspect", "takes damage equal to four rolls of your Martial Arts die on a failed save"),
             _KI_DC),
            level_vars={"rolls": BREATH_ROLLS_2014},
            extras=(("ascendant-dragon-ftd-17-ascendant-aspect", "Augment Breath: spend 1 ki point to make it a 60-foot cone or "
                     "a 90-foot line 5 feet wide that deals 4{ma_die}"),)),
    _w8_res("ascendant-dragon-ftd", "monk", "ascendant-dragon-ftd-3-draconic-disciple", "Draconic Presence", 1, "long",
            "If you fail a Charisma (Intimidation) or Charisma (Persuasion) check, use your reaction to reroll it; once this "
            "turns a failure into a success you can't use it again until you finish a long rest",
            ((None, "If you fail a Charisma (Intimidation) or Charisma (Persuasion) check, you can use your reaction to reroll the check"),
             (None, "Once this feature turns a failure into a success, you can't use it again until you finish a long rest"))),
    _w8_res("ascendant-dragon-ftd", "monk", "ascendant-dragon-ftd-6-wings-unfurled", "Wings Unfurled", "@pb", "long",
            "When you use Step of the Wind, unfurl spectral draconic wings that vanish at the end of your turn: a flying speed "
            "equal to your walking speed",
            ((None, "When you use your Step of the Wind, you can unfurl spectral draconic wings from your back that vanish at the end of your turn"),
             (None, "you have a flying speed equal to your walking speed"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("ascendant-dragon-ftd", "monk", "ascendant-dragon-ftd-11-aspect-of-the-wyrm", "Aspect of the Wyrm", 1, "long",
            "Bonus action: an aura of draconic power radiates 10 feet from you for 1 minute with one effect of your choice: "
            "Frightful Presence (a creature in the aura that you choose makes a Wisdom saving throw, ki save DC {dc_wis}, or is "
            "frightened of you for 1 minute) or Resistance (you and your allies in the aura resist a chosen damage type: acid, "
            "cold, fire, lightning or poison); after you create it you can't again until you finish a long rest unless you "
            "expend 3 ki points",
            ((None, "radiates 10 feet from you for 1 minute"),
             (None, "The target must succeed on a Wisdom saving throw against your ki save DC or become frightened of you for 1 minute"),
             (None, "You and your allies within the aura have resistance to that damage"),
             (None, "Once you create this aura, you can't create it again until you finish a long rest, unless you expend 3 ki points to create it again"),
             ("ascendant-dragon-ftd-17-ascendant-aspect", "Each of those creatures must succeed on a Dexterity saving throw against your ki save DC or take 3d10 acid, cold, fire, lightning, or poison damage"),
             _KI_DC),
            extras=(("ascendant-dragon-ftd-17-ascendant-aspect", "Explosive Fury: when you activate it, creatures you choose in "
                     "the aura make a Dexterity saving throw (ki save DC {dc_wis}) or take 3d10 acid, cold, fire, lightning "
                     "or poison damage"),)),
    # ---- Monk: Way of the Astral Self (TCE)
    _w8_res("astral-self-tce", "monk", "astral-self-tce-3-arms-of-the-astral-self", "Arms of the Astral Self", None, None,
            "Bonus action, 1 ki point: summon spectral arms for 10 minutes; each creature of your choice you can see within 10 "
            "feet makes a Dexterity saving throw (ki save DC {dc_wis}) or takes force damage equal to two rolls of your "
            "Martial Arts die (2{ma_die}). While they last: Wisdom modifier instead of Strength for Strength checks and "
            "saving throws; unarmed strikes with the arms have 5 feet more reach, use your Wisdom modifier for attack and "
            "damage rolls and deal force damage",
            ((None, "you can spend 1 ki point to summon the arms of your astral self"),
             (None, "must succeed on a Dexterity saving throw or take force damage equal to two rolls of your Martial Arts die"),
             (None, "For 10 minutes, these spectral arms hover near your shoulders"),
             (None, "your reach for it is 5 feet greater than normal"),
             _KI_DC)),
    _w8_res("astral-self-tce", "monk", "astral-self-tce-6-visage-of-the-astral-self", "Visage of the Astral Self", None, None,
            "Bonus action (or as part of Arms of the Astral Self), 1 ki point: summon the visage for 10 minutes: darkvision "
            "120 feet (magical darkness too), advantage on Wisdom (Insight) and Charisma (Intimidation) checks, and direct "
            "your words to one creature within 60 feet or amplify them to 600 feet",
            ((None, "you can spend 1 ki point to summon this visage for 10 minutes"),
             (None, "to a distance of 120 feet"),
             (None, "You have advantage on Wisdom (Insight) and Charisma (Intimidation) checks"),
             (None, "all creatures within 600 feet can hear you"))),
    _w8_res("astral-self-tce", "monk", "astral-self-tce-11-body-of-the-astral-self", "Body of the Astral Self", None, None,
            "With both arms and visage summoned, the body appears (no action). Deflect Energy: reaction when you take acid, "
            "cold, fire, force, lightning or thunder damage, reduce it by 1d10 {wis:+d} (minimum "
            "reduction 1 in total). Empowered Arms: once on each of your turns when you hit with the arms, extra damage equal to "
            "your Martial Arts die (1{ma_die})",
            ((None, "the damage you take is reduced by 1d10 + your Wisdom modifier (minimum reduction of 1)"),
             (None, "you can deal extra damage to the target equal to your Martial Arts die"))),
    _w8_res("astral-self-tce", "monk", "astral-self-tce-17-awakened-astral-self", "Awakened Astral Self", None, None,
            "Bonus action, 5 ki points: summon the arms, visage and body for 10 minutes: +2 bonus to Armor Class, and Extra "
            "Attack can make three attacks instead of two if all are made with the astral arms",
            ((None, "you can spend 5 ki points to summon the arms, visage, and body of your astral self and awaken it for 10 minutes"),
             (None, "You gain a +2 bonus to Armor Class"),
             (None, "you can instead attack three times if all the attacks are made with your astral arms"))),
    # ---- Monk: Way of the Drunken Master (XGE)
    _w8_res("drunken-master-xge", "monk", "drunken-master-xge-6-tipsy-sway", "Tipsy Sway", None, None,
            "Redirect Attack: when a creature misses you with a melee attack roll, spend 1 ki point as a reaction to make "
            "that attack hit another creature of your choice (not the attacker) you can see within 5 feet of you. Leap to "
            "Your Feet: stand up from prone by spending 5 feet of movement",
            ((None, "you can spend 1 ki point as a reaction to cause that attack to hit one creature of your choice, other than the attacker, that you can see within 5 feet of you"),
             (None, "you can stand up by spending 5 feet of movement, rather than half your speed"))),
    _w8_res("drunken-master-xge", "monk", "drunken-master-xge-11-drunkards-luck", "Drunkard's Luck", None, None,
            "When you make an ability check, an attack roll or a saving throw with disadvantage, spend 2 ki points to cancel "
            "the disadvantage for that roll",
            ((None, "you can spend 2 ki points to cancel the disadvantage for that roll"),)),
    # ---- Monk: Way of the Four Elements (PHB); the discipline picks are not tracked
    _w8_res("four-elements-phb", "monk", "four-elements-phb-3-disciple-of-the-elements", "Disciple of the Elements", None, None,
            "An elemental discipline spends ki points each time you use it (the costs of the picked disciplines are on the Ki entry); {cap}",
            ((None, "A discipline requires you to spend ki points each time you use it"),
             (None, "The spell's level increases by 1 for each additional ki point you spend")),
            level_vars={"cap": ELEMENTAL_KI_CAP_2014}),
    # ---- Monk: Way of the Kensei (XGE)
    _w8_res("kensei-xge", "monk", "kensei-xge-3-path-of-the-kensei", "Kensei's Shot", None, None,
            "Bonus action on your turn: until the end of the turn any target you hit with a ranged attack using a kensei "
            "weapon takes an extra 1d4 damage of the weapon's type",
            ((None, "You can use a bonus action on your turn to make your ranged attacks with a kensei weapon more deadly"),
             (None, "takes an extra 1d4 damage of the weapon's type"))),
    _w8_res("kensei-xge", "monk", "kensei-xge-6-one-with-the-blade", "Deft Strike", None, None,
            "When you hit a target with a kensei weapon, spend 1 ki point to deal extra damage equal to your Martial Arts "
            "die (1{ma_die}); only once on each of your turns",
            ((None, "you can spend 1 ki point to cause the weapon to deal extra damage to the target equal to your Martial Arts die"),
             (None, "You can use this feature only once on each of your turns"))),
    _w8_res("kensei-xge", "monk", "kensei-xge-11-sharpen-the-blade", "Sharpen the Blade", None, None,
            "Bonus action, up to 3 ki points: one kensei weapon you touch gets a bonus to attack and damage rolls equal to the "
            "ki points spent (up to +3) for 1 minute or until you use this again; no effect on a magic weapon that already "
            "has a bonus",
            ((None, "you can expend up to 3 ki points to grant one kensei weapon you touch a bonus to attack and damage rolls"),
             (None, "The bonus equals the number of ki points you spent"),
             (None, "This bonus lasts for 1 minute or until you use this feature again"))),
    # ---- Monk: Way of the Long Death (SCAG)
    _w8_res("long-death-scag", "monk", "long-death-scag-3-touch-of-death", "Touch of Death", None, None,
            "When you reduce a creature within 5 feet of you to 0 hit points, you gain {wis_level_min1} temporary hit points "
            "(Wisdom modifier + Monk level, minimum 1)",
            ((None, "you gain temporary hit points equal to your Wisdom modifier + your monk level (minimum of 1 temporary hit point)"),)),
    _w8_res("long-death-scag", "monk", "long-death-scag-11-mastery-of-death", "Mastery of Death", None, None,
            "When you are reduced to 0 hit points, expend 1 ki point (no action required) to have 1 hit point instead",
            ((None, "you can expend 1 ki point (no action required) to have 1 hit point instead"),)),
    _w8_res("long-death-scag", "monk", "long-death-scag-17-touch-of-the-long-death", "Touch of the Long Death", None, None,
            "Action: touch one creature within 5 feet and expend 1 to 10 ki points; it makes a Constitution saving throw (ki "
            "save DC {dc_wis}) and takes 2d10 necrotic damage per ki point spent (up to 20d10), half as much on a success",
            ((None, "you touch one creature within 5 feet of you, and you expend 1 to 10 ki points"),
             (None, "it takes 2d10 necrotic damage per ki point spent on a failed save, or half as much damage on a successful one"),
             _KI_DC)),
    # ---- Monk: Way of Mercy (TCE)
    _w8_res("mercy-tce", "monk", "mercy-tce-3-hand-of-harm", "Hand of Harm", None, None,
            "When you hit a creature with an unarmed strike, spend 1 ki point to deal extra necrotic damage equal to one roll "
            "of your Martial Arts die + your Wisdom modifier (1{ma_die}{wis:+d}); only once per turn",
            ((None, "you can spend 1 ki point to deal extra necrotic damage equal to one roll of your Martial Arts die + your Wisdom modifier"),
             (None, "You can use this feature only once per turn"))),
    _w8_res("mercy-tce", "monk", "mercy-tce-3-hand-of-healing", "Hand of Healing", None, None,
            "Action, 1 ki point: touch a creature and restore hit points equal to a roll of your Martial Arts die + your "
            "Wisdom modifier (1{ma_die}{wis:+d}); when you use Flurry of Blows you can replace one of the unarmed strikes "
            "with a use of this feature without spending a ki point for the healing",
            ((None, "you can spend 1 ki point to touch a creature and restore a number of hit points equal to a roll of your Martial Arts die + your Wisdom modifier"),
             (None, "you can replace one of the unarmed strikes with a use of this feature without spending a ki point for the healing"))),
    _w8_res("mercy-tce", "monk", "mercy-tce-17-hand-of-ultimate-mercy", "Hand of Ultimate Mercy", 1, "long",
            "Action, 5 ki points: touch the corpse of a creature that died within the past 24 hours; it returns to life with "
            "4d10{wis:+d} hit points (4d10 + your Wisdom modifier), with blinded, deafened, paralyzed, poisoned and stunned "
            "removed",
            ((None, "touch the corpse of a creature that died within the past 24 hours and expend 5 ki points"),
             (None, "regaining a number of hit points equal to 4d10 + your Wisdom modifier"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Monk: Way of Shadow (PHB)
    _w8_res("shadow-phb", "monk", "shadow-phb-3-shadow-arts", "Shadow Arts", None, None,
            "Action, 2 ki points: cast darkness, darkvision, pass without trace or silence without material components",
            ((None, "you can spend 2 ki points to cast darkness, darkvision, pass without trace, or silence, without providing material components"),)),
    # ---- Monk: Way of the Sun Soul (XGE)
    _w8_res("sun-soul-xge", "monk", "sun-soul-xge-3-radiant-sun-bolt", "Radiant Sun Bolt", None, None,
            "Attack option with the Attack action: a ranged spell attack with a range of 30 feet, proficient, adding your "
            "Dexterity modifier ({dex:+d}) to attack and damage; radiant damage with your Martial Arts die ({ma_die}); spend "
            "1 ki point to make it twice as a bonus action",
            ((None, "The special attack is a ranged spell attack with a range of 30 feet"),
             (None, "you add your Dexterity modifier to its attack and damage rolls"),
             (None, "you can spend 1 ki point to make the special attack twice as a bonus action"))),
    _w8_res("sun-soul-xge", "monk", "sun-soul-xge-6-searing-arc-strike", "Searing Arc Strike", None, None,
            "Immediately after the Attack action, spend 2 ki points to cast burning hands as a bonus action; each additional "
            "ki point raises the spell's level by 1, to at most {half_level} ki points in total (half your Monk level)",
            ((None, "you can spend 2 ki points to cast the burning hands spell as a bonus action"),
             (None, "Each additional ki point you spend increases the spell's level by 1"),
             (None, "equals half your monk level"))),
    _w8_res("sun-soul-xge", "monk", "sun-soul-xge-11-searing-sunburst", "Searing Sunburst", None, None,
            "Action: hurl an orb at a point within 150 feet; each creature in the 20-foot-radius sphere makes a Constitution "
            "saving throw (ki save DC {dc_wis}) or takes 2d6 radiant damage; each ki point you spend (up to 3) adds 2d6, "
            "so 8d6 at most",
            ((None, "hurl it at a point you choose within 150 feet"),
             (None, "Each creature in that 20-foot-radius sphere must succeed on a Constitution saving throw or take 2d6 radiant damage"),
             (None, "Each point you spend, to a maximum of 3, increases the damage by 2d6"),
             _KI_DC)),
    _w8_res("sun-soul-xge", "monk", "sun-soul-xge-17-sun-shield", "Sun Shield", None, None,
            "You shed bright light in a 30-foot radius and dim light for 30 feet more (a bonus action extinguishes or restores "
            "it); when a creature hits you with a melee attack while it shines, use your reaction to deal {five_plus_wis} "
            "radiant damage (5 + your Wisdom modifier)",
            ((None, "You shed bright light in a 30-foot radius and dim light for an additional 30 feet"),
             (None, "The radiant damage equals 5 + your Wisdom modifier"))),
    # ---- Paladin: Oath of the Ancients (PHB)
    _w8_res("ancients-phb", "paladin", "ancients-phb-15-undying-sentinel", "Undying Sentinel", 1, "long",
            "When you are reduced to 0 hit points and not killed outright, drop to 1 hit point instead",
            ((None, "you can choose to drop to 1 hit point instead"),
             (None, "Once you use this ability, you can't use it again until you finish a long rest"))),
    _w8_res("ancients-phb", "paladin", "ancients-phb-20-elder-champion", "Elder Champion", 1, "long",
            "Action: for 1 minute you regain 10 hit points at the start of each of your turns, cast paladin spells with a "
            "casting time of 1 action as a bonus action, and enemies within 10 feet have disadvantage on saving throws "
            "against your paladin spells and Channel Divinity options",
            ((None, "For 1 minute, you gain the following benefits"),
             (None, "At the start of each of your turns, you regain 10 hit points"),
             (None, "Enemy creatures within 10 feet of you have disadvantage on saving throws against your paladin spells and Channel Divinity options"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Paladin: Oath of Conquest (XGE)
    _w8_res("conquest-xge", "paladin", "conquest-xge-7-aura-of-conquest", "Aura of Conquest", None, None,
            "While you are not incapacitated, a menacing aura extends {aura} feet from you (not through Cover): a creature "
            "frightened of you has its speed reduced to 0 in it and takes {half_level} psychic damage (half your Paladin "
            "level) if it starts its turn there",
            ((None, "If a creature is frightened of you, its speed is reduced to 0 while in the aura"),
             (None, "takes psychic damage equal to half your paladin level if it starts its turn there")),
            level_vars={"aura": PALADIN_AURA_FEET_2014}),
    _w8_res("conquest-xge", "paladin", "conquest-xge-15-scornful-rebuke", "Scornful Rebuke", None, None,
            "Whenever a creature hits you with an attack and you are not incapacitated, it takes {cha_min1} psychic damage "
            "(Charisma modifier, minimum 1)",
            ((None, "that creature takes psychic damage equal to your Charisma modifier (minimum of 1) if you're not incapacitated"),)),
    _w8_res("conquest-xge", "paladin", "conquest-xge-20-invincible-conqueror", "Invincible Conqueror", 1, "long",
            "Action: for 1 minute you have resistance to all damage, can make one additional attack with the Attack action "
            "and score a critical hit on a 19 or 20 with melee weapon attacks",
            ((None, "gaining the following benefits for 1 minute"),
             (None, "You have resistance to all damage"),
             (None, "Your melee weapon attacks score a critical hit on a roll of 19 or 20 on the d20"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Paladin: Oath of the Crown (SCAG)
    _w8_res("crown-scag", "paladin", "crown-scag-20-exalted-champion", "Exalted Champion", 1, "long",
            "Action: for 1 hour you resist bludgeoning, piercing and slashing damage from nonmagical weapons, your allies "
            "within 30 feet have advantage on death saving throws and on Wisdom saving throws (as do you); it ends early if "
            "you are incapacitated or die",
            ((None, "You can use your action to gain the following benefits for 1 hour"),
             (None, "Your allies have advantage on death saving throws while within 30 feet of you"),
             (None, "You have advantage on Wisdom saving throws, as do your allies within 30 feet of you"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Paladin: Oath of Glory (TCE)
    _w8_res("glory-tce", "paladin", "glory-tce-15-glorious-defense", "Glorious Defense", "@cha_min1", "long",
            "Reaction: when you or a creature you can see within 10 feet is hit by an attack roll, give the target a bonus to "
            "AC against that attack equal to your Charisma modifier (minimum +1), currently +{cha_min1}; if the attack "
            "misses you can make one weapon attack against the attacker as part of the reaction",
            ((None, "When you or another creature you can see within 10 feet of you is hit by an attack roll"),
             (None, "The bonus equals your Charisma modifier (minimum of +1)"),
             (None, "You can use this feature a number of times equal to your Charisma modifier (minimum of once), and you regain all expended uses when you finish a long rest"))),
    _w8_res("glory-tce", "paladin", "glory-tce-20-living-legend", "Living Legend", 1, "long",
            "Bonus action: for 1 minute you have advantage on all Charisma checks, once on each of your turns you can turn a "
            "weapon attack miss into a hit, and you can use your reaction to reroll a failed saving throw; you can use it "
            "again before a long rest by expending a 5th-level spell slot",
            ((None, "As a bonus action, you gain the following benefits for 1 minute"),
             (None, "gaining advantage on all Charisma checks"),
             (None, "you can use your reaction to reroll it"),
             (None, "unless you expend a 5th-level spell slot to use it again"))),
    # ---- Paladin: Oathbreaker (DMG)
    _w8_res("oathbreaker-dmg", "paladin", "oathbreaker-dmg-7-aura-of-hate", "Aura of Hate", None, None,
            "You and any fiends and undead within {aura} feet of you gain a bonus to melee weapon damage rolls equal to your "
            "Charisma modifier (minimum +1), currently +{cha_min1}; a creature benefits from only one paladin at a time",
            ((None, "gains a bonus to melee weapon damage rolls equal to the paladin's Charisma modifier (minimum of +1)"),
             (None, "A creature can benefit from this feature from only one paladin at a time")),
            level_vars={"aura": PALADIN_AURA_FEET_2014}),
    _w8_res("oathbreaker-dmg", "paladin", "oathbreaker-dmg-20-dread-lord", "Dread Lord", 1, "long",
            "Action: for 1 minute an aura of gloom fills a 30-foot radius (bright light becomes dim); an enemy frightened by "
            "you that starts its turn in it takes 4d10 psychic damage, and as a bonus action you can make a melee spell "
            "attack against a target in the aura for 3d10{cha:+d} necrotic damage (3d10 + your Charisma modifier)",
            ((None, "surround himself or herself with an aura of gloom that lasts for 1 minute"),
             (None, "reduces any bright light in a 30-foot radius around the paladin to dim light"),
             (None, "it takes 4d10 psychic damage"),
             (None, "necrotic damage equal to 3d10 + the paladin's Charisma modifier"),
             (None, "the paladin can't do so again until he or she finishes a long rest"))),
    # ---- Paladin: Oath of Redemption (XGE)
    _w8_res("redemption-xge", "paladin", "redemption-xge-15-protective-spirit", "Protective Spirit", None, None,
            "If you end your turn in combat with fewer than half of your hit points and you aren't incapacitated, you regain "
            "1d6 + {half_level} hit points (half your Paladin level)",
            ((None, "You regain hit points equal to 1d6 + half your paladin level"),)),
    # ---- Paladin: Oath of Vengeance (PHB)
    _w8_res("vengeance-phb", "paladin", "vengeance-phb-20-avenging-angel", "Avenging Angel", 1, "long",
            "Action: for 1 hour you have wings and a flying speed of 60 feet and emanate a 30-foot aura of menace: the first "
            "time an enemy enters it or starts its turn there during a battle, it makes a Wisdom saving throw or "
            "is frightened of you for 1 minute or until it takes damage, and attack rolls against it have advantage",
            ((None, "For 1 hour, you gain the following benefits"),
             (None, "grant you a flying speed of 60 feet"),
             (None, "You emanate an aura of menace in a 30-foot radius"),
             (None, "must succeed on a Wisdom saving throw or become frightened of you for 1 minute or until it takes any damage"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Paladin: Oath of the Watchers (TCE)
    _w8_res("watchers-tce", "paladin", "watchers-tce-7-aura-of-the-sentinel", "Aura of the Sentinel", None, None,
            "While you aren't incapacitated, you and any creatures of your choice within {aura} feet of you gain a bonus to "
            "initiative equal to your proficiency bonus (+{pb})",
            ((None, "you all gain a bonus to initiative equal to your proficiency bonus"),),
            level_vars={"aura": PALADIN_AURA_FEET_2014}),
    _w8_res("watchers-tce", "paladin", "watchers-tce-15-vigilant-rebuke", "Vigilant Rebuke", None, None,
            "Whenever you or a creature you can see within 30 feet succeeds on an Intelligence, Wisdom or Charisma saving "
            "throw, use your reaction to deal 2d8{cha:+d} force damage (2d8 + your Charisma modifier) to the creature that "
            "forced the save",
            ((None, "you can use your reaction to deal 2d8 + your Charisma modifier force damage to the creature that forced the saving throw"),)),
    _w8_res("watchers-tce", "paladin", "watchers-tce-20-mortal-bulwark", "Mortal Bulwark", 1, "long",
            "Bonus action: for 1 minute you have truesight to 120 feet and advantage on attack rolls against aberrations, "
            "celestials, elementals, fey and fiends; when you hit one with damage you can force a Charisma saving throw "
            "(DC {dc_cha}) or it is banished to its native plane (24 hours of immunity on a success); you can use it again "
            "before a long rest by expending a 5th-level spell slot",
            ((None, "you gain the following benefits for 1 minute"),
             (None, "You gain truesight with a range of 120 feet"),
             (None, "force it to make a Charisma saving throw against your spell save DC"),
             (None, "the creature can't be banished by this feature for 24 hours"),
             (None, "unless you expend a 5th-level spell slot to use it again"))),
    # ---- Ranger: Beast Master (PHB)
    _w8_res("beast-master-phb", "ranger", "beast-master-phb-3-rangers-companion", "Ranger's Companion", None, None,
            "Choose a Medium or smaller beast of challenge rating 1/4 or lower; add your proficiency bonus (+{pb}) to its AC, "
            "attack and damage rolls and to the saving throws and skills it is proficient in; its hit point maximum is its "
            "normal maximum or {four_level} (four times your Ranger level), whichever is higher",
            ((None, "Choose a beast that is no larger than Medium and that has a challenge rating of 1/4 or lower"),
             (None, "Add your proficiency bonus to the beast's AC, attack rolls, and damage rolls"),
             (None, "Its hit point maximum equals its normal maximum or four times your ranger level, whichever is higher"))),
    # ---- Ranger: Drakewarden (FTD)
    _w8_res("drakewarden-ftd", "ranger", "drakewarden-ftd-3-drake-companion", "Drake Companion", 1, "long",
            "Action: summon your drake in an unoccupied space within 30 feet and choose a damage type for its Draconic "
            "Essence; it remains until it is reduced to 0 hit points, you summon it again or you die; summoning it again "
            "before a long rest costs a spell slot of 1st level or higher",
            ((None, "It appears in an unoccupied space of your choice within 30 feet of you"),
             (None, "choose a damage type listed in its Draconic Essence trait"),
             (None, "you can't do so again until you finish a long rest, unless you expend a spell slot of 1st level or higher to summon it"),
             ("drakewarden-ftd-7-bond-of-fang-and-scale", "The drake's Bite attack deals an extra 1d6 damage of the type chosen for the drake's Draconic Essence"),
             ("drakewarden-ftd-15-perfected-bond", "(for a total of 2d6 extra damage)")),
            extras=(("drakewarden-ftd-7-bond-of-fang-and-scale", "Magic Fang: the drake's Bite deals an extra 1d6 damage of "
                     "its chosen type and you resist that type"),
                    ("drakewarden-ftd-15-perfected-bond", "Empowered Bite: the extra bite damage is 2d6 in total"))),
    _w8_res("drakewarden-ftd", "ranger", "drakewarden-ftd-11-drakes-breath", "Drake's Breath", 1, "long",
            "Action: you or your drake exhale a 30-foot cone of acid, cold, fire, lightning or poison damage; each creature in "
            "it makes a Dexterity saving throw (DC {dc_wis}) and takes {breath} damage, half as much on a success; you can "
            "use it again before a long rest by expending a spell slot of 3rd level or higher",
            ((None, "you can exhale a 30-foot cone of damaging breath or cause your drake to exhale it"),
             (None, "Each creature in the cone must make a Dexterity saving throw against your spell save DC"),
             (None, "you can't do so again until you finish a long rest, unless you expend a spell slot of 3rd level or higher to use it again")),
            dice="@breath", level_vars={"breath": DRAKES_BREATH_DICE_2014}),
    _w8_res("drakewarden-ftd", "ranger", "drakewarden-ftd-15-perfected-bond", "Reflexive Resistance", "@pb", "long",
            "Reaction: when you or the drake takes damage while you are within 30 feet of each other, give yourself or the "
            "drake resistance to that instance of damage",
            ((None, "When either you or the drake takes damage while you're within 30 feet of each other, you can use your reaction to give yourself or the drake resistance to that instance of damage"),
             (None, "You can use this reaction a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Ranger: Fey Wanderer (TCE)
    _w8_res("fey-wanderer-tce", "ranger", "fey-wanderer-tce-3-dreadful-strikes", "Dreadful Strikes", None, None,
            "When you hit a creature with a weapon you can deal an extra {strikes} psychic damage; a creature can take it only "
            "once per turn",
            ((None, "which can take this extra damage only once per turn"),),
            dice="@strikes", level_vars={"strikes": DREADFUL_STRIKES_DICE_2014}),
    _w8_res("fey-wanderer-tce", "ranger", "fey-wanderer-tce-3-otherworldly-glamour", "Otherworldly Glamour", None, None,
            "Whenever you make a Charisma check you gain a bonus equal to your Wisdom modifier (minimum +1), currently "
            "+{wis_min1}",
            ((None, "you gain a bonus to the check equal to your Wisdom modifier (minimum of +1)"),)),
    _w8_res("fey-wanderer-tce", "ranger", "fey-wanderer-tce-7-beguiling-twist", "Beguiling Twist", None, None,
            "Reaction: when you or a creature you can see within 120 feet succeeds on a saving throw against being charmed or "
            "frightened, force a different creature you can see within 120 feet to make a Wisdom saving throw (DC {dc_wis}) "
            "or be charmed or frightened by you (your choice) for 1 minute; it repeats the save at the end of each of its "
            "turns",
            ((None, "you or a creature you can see within 120 feet of you succeeds on a saving throw against being charmed or frightened"),
             (None, "to make a Wisdom saving throw against your spell save DC"),
             (None, "charmed or frightened by you (your choice) for 1 minute"))),
    _w8_res("fey-wanderer-tce", "ranger", "fey-wanderer-tce-11-fey-reinforcements", "Fey Reinforcements", 1, "long",
            "Cast summon fey once without a spell slot (no material component); you can modify it so it doesn't require "
            "concentration, in which case its duration is 1 minute",
            ((None, "You can also cast it once without a spell slot, and you regain the ability to do so when you finish a long rest"),
             (None, "the spell's duration becomes 1 minute for that casting"))),
    _w8_res("fey-wanderer-tce", "ranger", "fey-wanderer-tce-15-misty-wanderer", "Misty Wanderer", "@wis_min1", "long",
            "Cast misty step without expending a spell slot; whenever you cast it you can bring along one willing creature "
            "you can see within 5 feet of you",
            ((None, "You can do so a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses when you finish a long rest"),
             (None, "you can bring along one willing creature you can see within 5 feet of you"))),
    # ---- Ranger: Gloom Stalker (XGE)
    _w8_res("gloom-stalker-xge", "ranger", "gloom-stalker-xge-3-dread-ambusher", "Dread Ambusher", None, None,
            "You can give yourself a bonus to initiative rolls equal to your Wisdom modifier ({wis:+d}); at the start of your "
            "first turn of each combat your walking speed increases by 10 feet until the end of that turn, and if you take "
            "the Attack action you can make one additional weapon attack, which deals an extra 1d8 damage of the weapon's "
            "type if it hits",
            ((None, "You can give yourself a bonus to your initiative rolls equal to your Wisdom modifier"),
             (None, "your walking speed increases by 10 feet, which lasts until the end of that turn"),
             (None, "the target takes an extra 1d8 damage of the weapon's damage type"))),
    # ---- Ranger: Horizon Walker (XGE)
    _w8_res("horizon-walker-xge", "ranger", "horizon-walker-xge-3-detect-portal", "Detect Portal", 1, "short-or-long",
            "Action: detect the distance and direction to the closest planar portal within 1 mile of you",
            ((None, "you detect the distance and direction to the closest planar portal within 1 mile of you"),
             (None, "you can't use it again until you finish a short or long rest"))),
    _w8_res("horizon-walker-xge", "ranger", "horizon-walker-xge-3-planar-warrior", "Planar Warrior", None, None,
            "Bonus action: choose a creature you can see within 30 feet; the next time you hit it this turn with a weapon "
            "attack, all damage of the attack becomes force damage and the creature takes an extra {pw} force damage",
            ((None, "choose one creature you can see within 30 feet of you"),
             (None, "all damage dealt by the attack becomes force damage")),
            dice="@pw", level_vars={"pw": PLANAR_WARRIOR_DICE_2014}),
    _w8_res("horizon-walker-xge", "ranger", "horizon-walker-xge-7-ethereal-step", "Ethereal Step", 1, "short-or-long",
            "Bonus action: cast etherealness without expending a spell slot; the spell ends at the end of the current turn",
            ((None, "you can cast the etherealness spell with this feature, without expending a spell slot"),
             (None, "you can't use it again until you finish a short or long rest"))),
    # ---- Ranger: Monster Slayer (XGE)
    _w8_res("monster-slayer-xge", "ranger", "monster-slayer-xge-3-hunters-sense", "Hunter's Sense", "@wis_min1", "long",
            "Action: choose a creature you can see within 60 feet and learn whether it has damage immunities, resistances or "
            "vulnerabilities and what they are",
            ((None, "choose one creature you can see within 60 feet of you"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "You regain all expended uses of it when you finish a long rest"))),
    _w8_res("monster-slayer-xge", "ranger", "monster-slayer-xge-3-slayers-prey", "Slayer's Prey", None, None,
            "Bonus action: designate a creature you can see within 60 feet; the first time each turn you hit it with a weapon "
            "attack it takes an extra 1d6 damage; it lasts until you finish a short or long rest or designate another "
            "creature",
            ((None, "you designate one creature you can see within 60 feet of you as the target of this feature"),
             (None, "it takes an extra 1d6 damage from the weapon"),
             (None, "This benefit lasts until you finish a short or long rest"),
             ("monster-slayer-xge-7-supernatural-defense", "add 1d6 to your roll")),
            extras=(("monster-slayer-xge-7-supernatural-defense", "Supernatural Defense: add 1d6 to saving throws that the "
                     "target forces and to ability checks to escape its grapple"),)),
    _w8_res("monster-slayer-xge", "ranger", "monster-slayer-xge-11-magic-users-nemesis", "Magic-User's Nemesis", 1, "short-or-long",
            "Reaction: when you see a creature cast a spell or teleport within 60 feet of you, it makes a Wisdom saving throw "
            "(DC {dc_wis}) or its spell or teleport fails and is wasted",
            ((None, "casting a spell or teleporting within 60 feet of you"),
             (None, "The creature must succeed on a Wisdom saving throw against your spell save DC"),
             (None, "you can't use it again until you finish a short or long rest"))),
    # ---- Ranger: Swarmkeeper (TCE)
    _w8_res("swarmkeeper-tce", "ranger", "swarmkeeper-tce-3-gathered-swarm", "Gathered Swarm", None, None,
            "Once on each of your turns, immediately after you hit a creature with an attack, the swarm can do one of: deal "
            "{swarm} piercing damage to the target; move the target up to 15 feet horizontally (Strength saving throw, DC "
            "{dc_wis}); or move you 5 feet horizontally",
            ((None, "Once on each of your turns, you can cause the swarm to assist you in one of the following ways"),
             (None, "must succeed on a Strength saving throw against your spell save DC or be moved by the swarm up to 15 feet horizontally"),
             (None, "You are moved by the swarm 5 feet horizontally"),
             ("swarmkeeper-tce-11-mighty-swarm", "you can also cause the swarm to knock the creature prone")),
            dice="@swarm", level_vars={"swarm": GATHERED_SWARM_DICE_2014},
            extras=(("swarmkeeper-tce-11-mighty-swarm", "Mighty Swarm: a creature that fails the save is also knocked prone, and "
                     "when the swarm moves you it gives you Cover until the start of your next turn"),)),
    _w8_res("swarmkeeper-tce", "ranger", "swarmkeeper-tce-7-writhing-tide", "Writhing Tide", "@pb", "long",
            "Bonus action: gain a flying speed of 10 feet and hover for 1 minute or until you are incapacitated",
            ((None, "you gain a flying speed of 10 feet and can hover"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("swarmkeeper-tce", "ranger", "swarmkeeper-tce-15-swarming-dispersal", "Swarming Dispersal", "@pb", "long",
            "Reaction when you take damage: gain resistance to that damage, then teleport to an unoccupied space you can see "
            "within 30 feet",
            ((None, "you can use your reaction to give yourself resistance to that damage"),
             (None, "teleport to an unoccupied space that you can see within 30 feet of you"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Rogue: Arcane Trickster (PHB)
    _w8_res("arcane-trickster-phb", "rogue", "arcane-trickster-phb-17-spell-thief", "Spell Thief", 1, "long",
            "Reaction right after a creature casts a spell that targets you or includes you in its area: it makes a saving "
            "throw with its spellcasting ability modifier (DC {dc_int}); on a failure you negate the spell against you and "
            "steal it (1st level or higher and of a level you can cast) for 8 hours, during which the creature can't cast it",
            ((None, "The DC equals your spell save DC"),
             (None, "For the next 8 hours, you know the spell and can cast it using your spell slots"),
             (None, "The creature can't cast that spell until the 8 hours have passed"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Rogue: Assassin (PHB)
    _w8_res("assassin-phb", "rogue", "assassin-phb-17-death-strike", "Death Strike", None, None,
            "When you attack and hit a surprised creature, it makes a Constitution saving throw (DC {dc_dex}); on a failure the "
            "damage of your attack is doubled",
            ((None, "it must make a Constitution saving throw (DC 8 + your Dexterity modifier + your proficiency bonus)"),
             (None, "On a failed save, double the damage of your attack against the creature"))),
    # ---- Rogue: Inquisitive (XGE)
    _w8_res("inquisitive-xge", "rogue", "inquisitive-xge-3-insightful-fighting", "Insightful Fighting", None, None,
            "Bonus action: a Wisdom (Insight) check against a creature you can see that isn't incapacitated, contested by its "
            "Charisma (Deception) check; on a success you can use Sneak Attack against it without advantage (but not with "
            "disadvantage) for 1 minute or until you succeed against a different target",
            ((None, "you can make a Wisdom (Insight) check against a creature you can see that isn't incapacitated, contested by the target's Charisma (Deception) check"),
             (None, "This benefit lasts for 1 minute or until you successfully use this feature against a different target"),
             ("inquisitive-xge-17-eye-for-weakness", "your Sneak Attack damage against that creature increases by 3d6")),
            extras=(("inquisitive-xge-17-eye-for-weakness", "Eye for Weakness: your Sneak Attack damage against that creature "
                     "increases by 3d6"),)),
    _w8_res("inquisitive-xge", "rogue", "inquisitive-xge-13-unerring-eye", "Unerring Eye", "@wis_min1", "long",
            "Action: sense illusions, shapechangers not in their original form and other magic designed to deceive the senses "
            "within 30 feet of you, provided you aren't blinded or deafened",
            ((None, "within 30 feet of you, provided you aren't blinded or deafened"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "you regain all expended uses of it when you finish a long rest"))),
    # ---- Rogue: Phantom (TCE)
    _w8_res("phantom-tce", "rogue", "phantom-tce-3-wails-from-the-grave", "Wails from the Grave", "@pb", "long",
            "Immediately after you deal Sneak Attack damage on your turn, target a second creature you can see within 30 feet "
            "of the first: it takes {wails} necrotic damage (half your Sneak Attack dice, rounded up)",
            ((None, "you can target a second creature that you can see within 30 feet of the first creature"),
             (None, "Roll half the number of Sneak Attack dice for your level (round up)"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"),
             ("phantom-tce-17-deaths-friend", "you can deal the necrotic damage to both the first and the second creature")),
            dice="@wails",
            extras=(("phantom-tce-17-deaths-friend", "Death's Friend: you can deal the necrotic damage to both the first and "
                     "the second creature"),)),
    _w8_res("phantom-tce", "rogue", "phantom-tce-9-tokens-of-the-departed", "Tokens of the Departed", None, None,
            "As a reaction when a creature you can see dies within 30 feet of you, create a Tiny soul trinket in your free "
            "hand; you can hold at most {pb} soul trinkets (your proficiency bonus). Each gives advantage on death saving "
            "throws and Constitution saving throws; destroy one when you deal Sneak Attack damage to use Wails from the "
            "Grave without spending a use, or as an action to ask its spirit one question",
            ((None, "You can have a maximum number of soul trinkets equal to your proficiency bonus"),
             (None, "you have advantage on death saving throws and Constitution saving throws"),
             (None, "then immediately use Wails from the Grave, without expending a use of that feature"))),
    _w8_res("phantom-tce", "rogue", "phantom-tce-13-ghost-walk", "Ghost Walk", 1, "long",
            "Bonus action: a spectral form for 10 minutes (or until you end it as a bonus action) with a flying speed of 10 "
            "feet, hovering, attack rolls against you have disadvantage, and you move through creatures and objects as "
            "difficult terrain, taking 1d10 force damage if you end your turn inside one; to use it again before a long rest, "
            "destroy a soul trinket as part of the bonus action",
            ((None, "you have a flying speed of 10 feet, you can hover, and attack rolls have disadvantage against you"),
             (None, "you take 1d10 force damage if you end your turn inside a creature or an object"),
             (None, "You stay in this form for 10 minutes"),
             (None, "To use this feature again, you must finish a long rest or destroy one of your soul trinkets"))),
    # ---- Rogue: Soulknife (TCE)
    _w8_res("soulknife-tce", "rogue", "soulknife-tce-3-psychic-blades", "Psychic Blades", None, None,
            "Whenever you take the Attack action you can manifest a psychic blade (a simple melee finesse and thrown weapon, "
            "range 60 feet) and attack with it: 1d6 psychic damage plus the ability modifier used for the attack; afterward "
            "a second blade can attack as a bonus action with a 1d4 damage die",
            ((None, "It has a normal range of 60 feet and no long range"),
             (None, "it deals psychic damage equal to 1d6 plus the ability modifier you used for the attack roll"),
             (None, "The damage die of this bonus attack is 1d4, instead of 1d6"))),
    _w8_res("soulknife-tce", "rogue", "soulknife-tce-13-psychic-veil", "Psychic Veil", 1, "long",
            "Action: become invisible with what you wear and carry for 1 hour or until you dismiss it; it ends early after you "
            "deal damage or force a saving throw; you can use it again before a long rest by expending a Psionic Energy die",
            ((None, "for 1 hour or until you dismiss this effect"),
             (None, "unless you expend a Psionic Energy die to use this feature again"))),
    _w8_res("soulknife-tce", "rogue", "soulknife-tce-17-rend-mind", "Rend Mind", 1, "long",
            "When you deal Sneak Attack damage with your Psychic Blades, force the target to make a Wisdom saving throw (DC "
            "{dc_dex}) or be stunned for 1 minute (it repeats the save at the end of each of its turns); you can use it again "
            "before a long rest by expending three Psionic Energy dice",
            ((None, "DC equal to 8 + your proficiency bonus + your Dexterity modifier"),
             (None, "the target is stunned for 1 minute"),
             (None, "unless you expend three Psionic Energy dice to use it again"))),
    # ---- Rogue: Swashbuckler (XGE)
    _w8_res("swashbuckler-xge", "rogue", "swashbuckler-xge-3-rakish-audacity", "Rakish Audacity", None, None,
            "You can give yourself a bonus to initiative rolls equal to your Charisma modifier ({cha:+d}); you can Sneak "
            "Attack without advantage if you are within 5 feet of the target, no other creature is within 5 feet of you and "
            "you don't have disadvantage",
            ((None, "You can give yourself a bonus to your initiative rolls equal to your Charisma modifier"),
             (None, "you don't need advantage on your attack roll to use Sneak Attack against a creature if you are within 5 feet of it, no other creatures are within 5 feet of you, and you don't have disadvantage on the attack roll"))),
    _w8_res("swashbuckler-xge", "rogue", "swashbuckler-xge-17-master-duelist", "Master Duelist", 1, "short-or-long",
            "If you miss with an attack roll you can roll it again with advantage",
            ((None, "you can roll it again with advantage"),
             (None, "you can't use this feature again until you finish a short or long rest"))),
)

# Channel Divinity options of the Paladin oaths (sentences on `paladin:channel-divinity`; the save DC is the one that
# note already names).
_W8C_NOTES: tuple[dict, ...] = (
    _w8_pcd("ancients-phb", "ancients-phb-3-natures-wrath", "Nature's Wrath",
            "Nature's Wrath (action, 10 feet): spectral vines restrain a creature you can see unless it succeeds on a Strength "
            "or Dexterity saving throw (its choice); it repeats the save at the end of each of its turns",
            ((None, "within 10 feet of you that you can see"), (None, "must succeed on a Strength or Dexterity saving throw (its choice) or be restrained"))),
    _w8_pcd("ancients-phb", "ancients-phb-3-turn-the-faithless", "Turn the Faithless",
            "Turn the Faithless (action, 30 feet): each fey or fiend that can hear you makes a Wisdom saving throw or is turned "
            "for 1 minute or until it takes damage",
            ((None, "each fey or fiend within 30 feet of you that can hear you must make a Wisdom saving throw"),
             (None, "the creature is turned for 1 minute or until it takes damage"))),
    _w8_pcd("conquest-xge", "conquest-xge-3-conquering-presence", "Conquering Presence",
            "Conquering Presence (action, 30 feet): each creature of your choice you can see makes a Wisdom saving throw or is "
            "frightened of you for 1 minute, repeating the save at the end of each of its turns",
            ((None, "each creature of your choice that you can see within 30 feet of you to make a Wisdom saving throw"),
             (None, "a creature becomes frightened of you for 1 minute"))),
    _w8_pcd("conquest-xge", "conquest-xge-3-guided-strike", "Guided Strike",
            "Guided Strike: when you make an attack roll, gain a +10 bonus to the roll, chosen after you see it and before the "
            "DM says whether it hits or misses",
            ((None, "you can use your Channel Divinity to gain a +10 bonus to the roll"),)),
    _w8_pcd("crown-scag", "crown-scag-3-champion-challenge", "Champion Challenge",
            "Champion Challenge (bonus action, 30 feet): each creature of your choice you can see makes a Wisdom saving throw "
            "or can't willingly move more than 30 feet away from you",
            ((None, "As a bonus action, you issue a challenge"),
             (None, "a creature can't willingly move more than 30 feet away from you"))),
    _w8_pcd("crown-scag", "crown-scag-3-turn-the-tide", "Turn the Tide",
            "Turn the Tide (bonus action, 30 feet): each creature of your choice that can hear you and has no more than half "
            "of its hit points regains 1d6 {cha:+d} hit points (minimum 1 in total; the book wording is ambiguous, read as a minimum on the total)",
            ((None, "regains hit points equal to 1d6 + your Charisma modifier (minimum of 1) if it has no more than half of its hit points"),)),
    _w8_pcd("glory-tce", "glory-tce-3-inspiring-smite", "Inspiring Smite",
            "Inspiring Smite (bonus action, right after dealing Divine Smite damage): distribute temporary hit points "
            "totalling 2d8 + {level} (your Paladin level) among creatures of your choice within 30 feet, including you",
            ((None, "The total number of temporary hit points equals 2d8 + your level in this class"),)),
    _w8_pcd("glory-tce", "glory-tce-3-peerless-athlete", "Peerless Athlete",
            "Peerless Athlete (bonus action): for 10 minutes, advantage on Strength (Athletics) and Dexterity (Acrobatics) "
            "checks, twice the carrying capacity and 10 feet more on long and high jumps",
            ((None, "For the next 10 minutes"), (None, "the distance of your long and high jumps increases by 10 feet"))),
    _w8_pcd("oathbreaker-dmg", "oathbreaker-dmg-3-control-undead", "Control Undead",
            "Control Undead (action, 30 feet): an undead creature you can see makes a Wisdom saving throw or obeys your "
            "commands for 24 hours (or until you use this again); an undead with a challenge rating of {level} or higher "
            "(your Paladin level) is immune",
            ((None, "within 30 feet of him or her"), (None, "obey the paladin's commands for the next 24 hours"),
             (None, "An undead whose challenge rating is equal to or greater than the paladin's level is immune to this effect"))),
    _w8_pcd("oathbreaker-dmg", "oathbreaker-dmg-3-dreadful-aspect", "Dreadful Aspect",
            "Dreadful Aspect (action, 30 feet): each creature of your choice that can see you makes a Wisdom saving throw or is "
            "frightened of you for 1 minute; one that ends its turn more than 30 feet away can save again",
            ((None, "Each creature of the paladin's choice within 30 feet of the paladin must make a Wisdom saving throw"),
             (None, "the target is frightened of the paladin for 1 minute"))),
    _w8_pcd("redemption-xge", "redemption-xge-3-emissary-of-peace", "Emissary of Peace",
            "Emissary of Peace (bonus action): +5 bonus to Charisma (Persuasion) checks for 10 minutes",
            ((None, "you grant yourself a +5 bonus to Charisma (Persuasion) checks for the next 10 minutes"),)),
    _w8_pcd("redemption-xge", "redemption-xge-3-rebuke-the-violent", "Rebuke the Violent",
            "Rebuke the Violent (reaction, 30 feet): right after an attacker deals damage to a creature other than you, it makes "
            "a Wisdom saving throw or takes radiant damage equal to the damage it dealt (half on a success)",
            ((None, "an attacker within 30 feet of you deals damage with an attack against a creature other than you"),
             (None, "the attacker takes radiant damage equal to the damage it just dealt"))),
    _w8_pcd("vengeance-phb", "vengeance-phb-3-abjure-enemy", "Abjure Enemy",
            "Abjure Enemy (action, 60 feet): one creature you can see makes a Wisdom saving throw (fiends and undead have "
            "disadvantage) or is frightened for 1 minute or until it takes damage, with speed 0; on a success its speed is "
            "halved for 1 minute or until it takes damage",
            ((None, "Choose one creature within 60 feet of you that you can see"),
             (None, "Fiends and undead have disadvantage on this saving throw"),
             (None, "the creature's speed is halved for 1 minute or until the creature takes any damage"))),
    _w8_pcd("vengeance-phb", "vengeance-phb-3-vow-of-enmity", "Vow of Enmity",
            "Vow of Enmity (bonus action, 10 feet): advantage on attack rolls against one creature you can see for 1 minute or "
            "until it drops to 0 hit points or falls unconscious",
            ((None, "against a creature you can see within 10 feet of you"),
             (None, "You gain advantage on attack rolls against the creature for 1 minute"))),
    _w8_pcd("watchers-tce", "watchers-tce-3-abjure-the-extraplanar", "Abjure the Extraplanar",
            "Abjure the Extraplanar (action, 30 feet): each aberration, celestial, elemental, fey or fiend that can hear you "
            "makes a Wisdom saving throw or is turned for 1 minute or until it takes damage",
            ((None, "each aberration, celestial, elemental, fey, or fiend within 30 feet of you that can hear you must make a Wisdom saving throw"),
             (None, "the creature is turned for 1 minute or until it takes damage"))),
    _w8_pcd("watchers-tce", "watchers-tce-3-watchers-will", "Watcher's Will",
            "Watcher's Will (action, 30 feet): choose up to {cha_min1} creatures you can see (Charisma modifier, minimum 1); "
            "for 1 minute you and they have advantage on Intelligence, Wisdom and Charisma saving throws",
            ((None, "up to a number equal to your Charisma modifier (minimum of one creature)"),
             (None, "you and the chosen creatures have advantage on Intelligence, Wisdom, and Charisma saving throws"))),
    # Soulknife powers (sentences on the R6 `rogue:psionic-energy-dice` resource)
    _w8_note("soulknife-tce", "rogue", "rogue:psionic-energy-dice", "soulknife-tce-3-psionic-power", "Psi-Bolstered Knack",
             "Psi-Bolstered Knack: when you fail an ability check with a skill or tool you are proficient in, add one "
             "Psionic Energy die to the check; the die is expended only if the roll succeeds",
             ((None, "if you fail an ability check using a skill or tool with which you have proficiency, you can roll one Psionic Energy die and add the number rolled to the check"),
              (None, "You expend the die only if the roll succeeds"))),
    _w8_note("soulknife-tce", "rogue", "rogue:psionic-energy-dice", "soulknife-tce-3-psionic-power", "Psychic Whispers",
             "Psychic Whispers (action): choose up to {pb} creatures you can see (your proficiency bonus) and roll one die; "
             "for that many hours they can speak telepathically with you, and you with them, within 1 mile; the first use "
             "after each long rest doesn't expend the die",
             ((None, "up to a number of creatures equal to your proficiency bonus"),
              (None, "For a number of hours equal to the number rolled"),
              (None, "you and the other creature must be within 1 mile of each other"),
              (None, "The first time you use this power after each long rest, you don't expend the Psionic Energy die"))),
    _w8_note("soulknife-tce", "rogue", "rogue:psionic-energy-dice", "soulknife-tce-9-soul-blades", "Homing Strikes",
             "Homing Strikes: if a Psychic Blades attack misses, add one Psionic Energy die to the attack roll; the die is "
             "expended only if the attack then hits",
             ((None, "If you make an attack roll with your Psychic Blades and miss the target, you can roll one Psionic Energy die and add the number rolled to the attack roll"),
              (None, "If this causes the attack to hit, you expend the Psionic Energy die"))),
    _w8_note("soulknife-tce", "rogue", "rogue:psionic-energy-dice", "soulknife-tce-9-soul-blades", "Psychic Teleportation",
             "Psychic Teleportation (bonus action): manifest a Psychic Blade, expend and roll one die, throw the blade at an "
             "unoccupied space you can see up to 10 times the number rolled in feet away, and teleport there",
             ((None, "expend one Psionic Energy die and roll it"),
              (None, "up to a number of feet away equal to 10 times the number rolled"))),
)

SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + _W8C_TAIL
SUBCLASS_NOTES_2014_BOOKS = SUBCLASS_NOTES_2014_BOOKS + _W8C_NOTES

# ---- W8d: Sorcerer, Warlock, Wizard (book subclasses) --------------------------------------------------------------------
# Tables that live only in the text (pinned in BOOK_TABLE_PINS_2014, like the W8a..W8c ones).
TENTACLE_DICE_2014 = ((1, "1d8"), (10, "2d8"))
PORTENT_DICE_2014 = ((2, 2), (14, 3))

BOOK_TABLE_PINS_2014.update({
    "TENTACLE_DICE_2014": (("fathomless-tce-1-tentacle-of-the-deeps", "the target takes 1d8 cold damage"),
                           ("fathomless-tce-1-tentacle-of-the-deeps", "the damage increases to 2d8"),
                           ("fathomless-tce-6-guardian-coil", "reduce the damage to that creature by 1d8"),
                           ("fathomless-tce-6-guardian-coil", "the damage reduced by the tentacle increases to 2d8")),
    "PORTENT_DICE_2014": (("divination-phb-2-portent", "roll two d20s and record the numbers rolled"),
                          ("divination-phb-14-greater-portent", "You roll three d20s for your Portent feature, rather than two")),
})

_SORC_SP = "sorcerer:sorcery-points"

_W8D_TAIL: tuple[dict, ...] = (
    # ---- Sorcerer: Aberrant Mind (TCE)
    _w8_res("aberrant-mind-tce", "sorcerer", "aberrant-mind-tce-1-telepathic-speech", "Telepathic Speech", None, None,
            "Bonus action: choose a creature you can see within 30 feet; you can speak telepathically with each other while "
            "within {cha_min1} mile(s) of each other (Charisma modifier, minimum 1), for {level} minutes (your Sorcerer "
            "level) or until you are incapacitated or die or you connect to a different creature",
            ((None, "choose one creature you can see within 30 feet of you"),
             (None, "within a number of miles of each other equal to your Charisma modifier (minimum of 1 mile)"),
             (None, "The telepathic connection lasts for a number of minutes equal to your sorcerer level"))),
    _w8_res("aberrant-mind-tce", "sorcerer", "aberrant-mind-tce-14-revelation-in-flesh", "Revelation in Flesh", None, None,
            "Bonus action, 1 or more sorcery points: transform your body for 10 minutes; each sorcery point spent gives one "
            "benefit of your choice: see invisible creatures within 60 feet; a flying speed equal to your walking speed and "
            "hovering; a swimming speed of twice your walking speed and breathing underwater; moving through spaces as narrow "
            "as 1 inch and spending 5 feet of movement to escape nonmagical restraints or a grapple",
            ((None, "you can spend 1 or more sorcery points to magically transform your body for 10 minutes"),
             (None, "For each sorcery point you spend, you can gain one of the following benefits of your choice"),
             (None, "You can see any invisible creature within 60 feet of you"),
             (None, "You gain a swimming speed equal to twice your walking speed"),
             (None, "as narrow as 1 inch without squeezing"))),
    _w8_res("aberrant-mind-tce", "sorcerer", "aberrant-mind-tce-18-warping-implosion", "Warping Implosion", 1, "long",
            "Action: teleport to an unoccupied space you can see within 120 feet; each creature within 30 feet of the space you "
            "left makes a Strength saving throw (DC {dc_cha}) or takes 3d10 force damage and is pulled toward it (half "
            "damage and not pulled on a success); you can use it again before a long rest by spending 5 sorcery points",
            ((None, "teleport to an unoccupied space you can see within 120 feet of you"),
             (None, "must make a Strength saving throw against your spell save DC"),
             (None, "a creature takes 3d10 force damage"),
             (None, "unless you spend 5 sorcery points to use it again"))),
    # ---- Sorcerer: Clockwork Soul (TCE)
    _w8_res("clockwork-soul-tce", "sorcerer", "clockwork-soul-tce-1-restore-balance", "Restore Balance", "@pb", "long",
            "Reaction: when a creature you can see within 60 feet is about to roll a d20 with advantage or disadvantage, "
            "prevent the roll from being affected by advantage and disadvantage",
            ((None, "within 60 feet of you is about to roll a d20 with advantage or disadvantage"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("clockwork-soul-tce", "sorcerer", "clockwork-soul-tce-6-bastion-of-law", "Bastion of Law", None, None,
            "Action, 1 to 5 sorcery points: a magical ward on yourself or another creature you can see within 30 feet, lasting "
            "until you finish a long rest or use this again; it is a number of d8s equal to the sorcery points spent, and the "
            "warded creature can expend and roll some of them to reduce damage taken by the total",
            ((None, "you can expend 1 to 5 sorcery points to create a magical ward"),
             (None, "within 30 feet of you"),
             (None, "The ward is represented by a number of d8s equal to the number of sorcery points spent to create it"),
             (None, "reduce the damage taken by the total rolled on those dice"))),
    _w8_res("clockwork-soul-tce", "sorcerer", "clockwork-soul-tce-14-trance-of-order", "Trance of Order", 1, "long",
            "Bonus action: for 1 minute attack rolls against you can't benefit from advantage, and you can treat a d20 roll "
            "of 9 or lower as a 10 on attack rolls, ability checks and saving throws; you can use it again before a long "
            "rest by spending 5 sorcery points",
            ((None, "you can enter this state for 1 minute"),
             (None, "you can treat a roll of 9 or lower on the d20 as a 10"),
             (None, "unless you spend 5 sorcery points to use it again"))),
    _w8_res("clockwork-soul-tce", "sorcerer", "clockwork-soul-tce-18-clockwork-cavalcade", "Clockwork Cavalcade", 1, "long",
            "Action: spirits fill a 30-foot cube originating from you: they restore up to 100 hit points divided among "
            "creatures of your choice in the cube, repair damaged objects and end every spell of 6th level or lower on "
            "creatures and objects of your choice; you can use it again before a long rest by spending 7 sorcery points",
            ((None, "you summon the spirits in a 30-foot cube originating from you"),
             (None, "The spirits restore up to 100 hit points"),
             (None, "Every spell of 6th level or lower ends on creatures and objects of your choice in the cube"),
             (None, "unless you spend 7 sorcery points to use it again"))),
    # ---- Sorcerer: Divine Soul (XGE)
    _w8_res("divine-soul-xge", "sorcerer", "divine-soul-xge-1-favored-by-the-gods", "Favored by the Gods", 1, "short-or-long",
            "If you fail a saving throw or miss with an attack roll, roll 2d4 and add it to the total, possibly changing the "
            "outcome",
            ((None, "you can roll 2d4 and add it to the total, possibly changing the outcome"),
             (None, "you can't use it again until you finish a short or long rest")),
            dice="2d4"),
    _w8_res("divine-soul-xge", "sorcerer", "divine-soul-xge-6-empowered-healing", "Empowered Healing", None, None,
            "Whenever you or an ally within 5 feet of you rolls dice for the hit points a spell restores, spend 1 sorcery point "
            "to reroll any number of those dice once (not while incapacitated); only once per turn",
            ((None, "you can spend 1 sorcery point to reroll any number of those dice once"),
             (None, "You can use this feature only once per turn"))),
    _w8_res("divine-soul-xge", "sorcerer", "divine-soul-xge-18-unearthly-recovery", "Unearthly Recovery", 1, "long",
            "Bonus action when you have fewer than half of your hit points remaining: regain half your hit point maximum",
            ((None, "when you have fewer than half of your hit points remaining"),
             (None, "regain a number of hit points equal to half your hit point maximum"),
             (None, "you can't use it again until you finish a long rest"))),
    # ---- Sorcerer: Lunar Sorcery (DSotDQ)
    _w8_res("lunar-dsotdq", "sorcerer", "lunar-dsotdq-1-lunar-embodiment", "Lunar Embodiment", 1, "long",
            "After each long rest choose a phase (Full Moon, New Moon or Crescent Moon); while in it you can cast one 1st-level "
            "spell of that phase once without a spell slot, then not again until you finish a long rest (the phase pick is "
            "not tracked)",
            ((None, "Whenever you finish a long rest, you can choose what lunar phase manifests its power through your magic"),
             (None, "you can cast one 1st-level spell of the associated phase in the Lunar Spells table once without expending a spell slot"),
             (None, "Once you cast a spell in this way, you can't do so again until you finish a long rest"))),
    _w8_res("lunar-dsotdq", "sorcerer", "lunar-dsotdq-6-lunar-boons", "Lunar Boons", "@pb", "long",
            "Using Metamagic on a spell of a school tied to your current phase (Full Moon abjuration and divination, New Moon "
            "enchantment and necromancy, Crescent Moon illusion and transmutation) reduces the sorcery points spent by 1 "
            "(minimum 0)",
            ((None, "Full Moon. Abjuration and divination spells"),
             (None, "you can reduce the sorcery points spent by 1 (minimum 0)"),
             (None, "You can reduce the sorcery points spent for your Metamagic a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("lunar-dsotdq", "sorcerer", "lunar-dsotdq-6-waxing-and-waning", "Waxing and Waning", None, None,
            "Bonus action, 1 sorcery point: change your current Lunar Embodiment phase; you can cast one 1st-level spell from "
            "each phase once without a spell slot while your current phase matches it, each once until a long rest",
            ((None, "you can spend 1 sorcery point to change your current Lunar Embodiment phase to a different one"),
             (None, "Once you cast a lunar phase spell in this way, you can't do so again until you finish a long rest"))),
    _w8_res("lunar-dsotdq", "sorcerer", "lunar-dsotdq-18-lunar-phenomenon", "Lunar Phenomenon", None, None,
            "Bonus action (or as part of changing phase): Full Moon, creatures of your choice within 30 feet make a "
            "Constitution saving throw (DC {dc_cha}) or are blinded until the end of their next turn, and one creature in the "
            "area regains 3d8 hit points; New Moon, creatures of your choice within 30 feet make a Dexterity saving throw (DC "
            "{dc_cha}) or take 3d10 necrotic damage and have their speed reduced to 0 until the end of their next turn, and "
            "you are invisible until the end of your next turn; Crescent Moon, teleport up to 60 feet and bring one willing "
            "creature within 5 feet, both resisting all damage until the start of your next turn; each benefit once until a "
            "long rest unless you spend 5 sorcery points",
            ((None, "Each creature of your choice within 30 feet of you must succeed on a Constitution saving throw against your spell save DC or be blinded until the end of its next turn"),
             (None, "one creature of your choice in that area regains 3d8 hit points"),
             (None, "take 3d10 necrotic damage and have its speed reduced to 0 until the end of its next turn"),
             (None, "You can magically teleport to an unoccupied space you can see within 60 feet of yourself"),
             (None, "you can't use that benefit again until you finish a long rest, unless you spend 5 sorcery points to use it again"))),
    # ---- Sorcerer: Pyromancer (PSK)
    _w8_res("pyromancer-psk", "sorcerer", "pyromancer-psk-1-heart-of-fire", "Heart of Fire", None, None,
            "Whenever you start casting a spell of 1st level or higher that deals fire damage, creatures of your choice you can "
            "see within 10 feet of you take {half_level_min1} fire damage (half your Sorcerer level, minimum 1)",
            ((None, "creatures of your choice that you can see within 10 feet of you to take fire damage equal to half your sorcerer level (minimum of 1)"),)),
    _w8_res("pyromancer-psk", "sorcerer", "pyromancer-psk-14-pyromancers-fury", "Pyromancer's Fury", None, None,
            "Reaction when you are hit by a melee attack: deal {level} fire damage (your Sorcerer level) to the attacker, "
            "ignoring resistance to fire damage",
            ((None, "when you are hit by a melee attack, you can use your reaction to deal fire damage to the attacker"),
             (None, "The damage equals your sorcerer level, and ignores resistance to fire damage"))),
    # ---- Sorcerer: Shadow Magic (XGE)
    _w8_res("shadow-xge", "sorcerer", "shadow-xge-1-eyes-of-the-dark", "Eyes of the Dark", None, None,
            "Darkvision with a range of 120 feet; from Sorcerer level 3 you know darkness (not counted against your spells "
            "known) and can cast it by spending 2 sorcery points, seeing through the darkness it creates",
            ((None, "you have darkvision with a range of 120 feet"),
             (None, "you can cast it by spending 2 sorcery points or by expending a spell slot"),
             (None, "you can see through the darkness created by the spell"))),
    _w8_res("shadow-xge", "sorcerer", "shadow-xge-1-strength-of-the-grave", "Strength of the Grave", 1, "long",
            "When damage reduces you to 0 hit points, make a Charisma saving throw (DC 5 + the damage taken); on a success you "
            "drop to 1 hit point instead (not against radiant damage or a critical hit); after a success you can't use it "
            "again until you finish a long rest",
            ((None, "you can make a Charisma saving throw (DC 5 + the damage taken)"),
             (None, "You can't use this feature if you are reduced to 0 hit points by radiant damage or by a critical hit"),
             (None, "After the saving throw succeeds, you can't use this feature again until you finish a long rest"))),
    _w8_res("shadow-xge", "sorcerer", "shadow-xge-6-hound-of-ill-omen", "Hound of Ill Omen", None, None,
            "Bonus action, 3 sorcery points: summon a hound of ill omen (dire wolf statistics, Medium monstrosity) that "
            "targets one creature you can see within 120 feet; it appears within 30 feet of the target with {half_level} "
            "temporary hit points (half your Sorcerer level), and while it is within 5 feet of the target the target has "
            "disadvantage on saving throws against your spells; it lasts 5 minutes",
            ((None, "you can spend 3 sorcery points to magically summon a hound of ill omen to target one creature you can see within 120 feet of you"),
             (None, "It appears with a number of temporary hit points equal to half your sorcerer level"),
             (None, "within 30 feet of the target"),
             (None, "or after 5 minutes"))),
    _w8_res("shadow-xge", "sorcerer", "shadow-xge-18-umbral-form", "Umbral Form", None, None,
            "Bonus action, 6 sorcery points: a shadowy form for 1 minute with resistance to all damage except force and "
            "radiant, moving through creatures and objects as difficult terrain and taking 5 force damage if you end your "
            "turn inside an object",
            ((None, "you can spend 6 sorcery points as a bonus action to magically transform yourself into a shadowy form"),
             (None, "You take 5 force damage if you end your turn inside an object"),
             (None, "You remain in this form for 1 minute"))),
    # ---- Sorcerer: Storm Sorcery (XGE)
    _w8_res("storm-xge", "sorcerer", "storm-xge-6-heart-of-the-storm", "Heart of the Storm", None, None,
            "Whenever you start casting a spell of 1st level or higher that deals lightning or thunder damage, creatures of "
            "your choice you can see within 10 feet of you take {half_level} lightning or thunder damage (half your "
            "Sorcerer level; choose each time)",
            ((None, "take lightning or thunder damage (choose each time this ability activates) equal to half your sorcerer level"),
             (None, "within 10 feet of you"))),
    _w8_res("storm-xge", "sorcerer", "storm-xge-14-storms-fury", "Storm's Fury", None, None,
            "Reaction when you are hit by a melee attack: deal {level} lightning damage (your Sorcerer level) to the attacker, "
            "who also makes a Strength saving throw (DC {dc_cha}) or is pushed up to 20 feet away from you",
            ((None, "The damage equals your sorcerer level"),
             (None, "The attacker must also make a Strength saving throw against your sorcerer spell save DC"),
             (None, "pushed in a straight line up to 20 feet away from you"))),
    _w8_res("storm-xge", "sorcerer", "storm-xge-18-wind-soul", "Wind Soul", 1, "short-or-long",
            "You have a magical flying speed of 60 feet; as an action reduce it to 30 feet for 1 hour and choose up to "
            "{three_plus_cha} creatures within 30 feet (3 + your Charisma modifier) who gain a magical flying speed of 30 "
            "feet for 1 hour",
            ((None, "You also gain a magical flying speed of 60 feet"),
             (None, "equal to 3 + your Charisma modifier"),
             (None, "Once you reduce your flying speed in this way, you can't do so again until you finish a short or long rest"))),
    # ---- Sorcerer: Wild Magic (PHB)
    _w8_res("wild-phb", "sorcerer", "wild-phb-1-tides-of-chaos", "Tides of Chaos", 1, "long",
            "Gain advantage on one attack roll, ability check or saving throw; until you regain the use the DM can have you "
            "roll on the Wild Magic Surge table after you cast a sorcerer spell of 1st level or higher, which regains it",
            ((None, "gain advantage on one attack roll, ability check, or saving throw"),
             (None, "you must finish a long rest before you can use this feature again"),
             (None, "You then regain the use of this feature"))),
    _w8_res("wild-phb", "sorcerer", "wild-phb-1-wild-magic-surge", "Wild Magic Surge", None, None,
            "Immediately after you cast a sorcerer spell of 1st level or higher the DM can have you roll a d20; on a 1 roll on "
            "the Wild Magic Surge table; a surge can happen once per turn (a spell it casts ignores Metamagic and needs no "
            "concentration)",
            ((None, "the DM can have you roll a d20. If you roll a 1, roll on the Wild Magic Surge table"),
             (None, "A Wild Magic Surge can happen once per turn"))),
    _w8_res("wild-phb", "sorcerer", "wild-phb-6-bend-luck", "Bend Luck", None, None,
            "Reaction, 2 sorcery points: when another creature you can see makes an attack roll, an ability check or a saving "
            "throw, roll 1d4 and apply it as a bonus or penalty (your choice) to its roll, after the roll but before its "
            "effects",
            ((None, "you can use your reaction and spend 2 sorcery points to roll 1d4"),
             (None, "as a bonus or penalty (your choice) to the creature's roll"))),
    # ---- Warlock: The Archfey (PHB)
    _w8_res("archfey-phb", "warlock", "archfey-phb-1-fey-presence", "Fey Presence", 1, "short-or-long",
            "Action: each creature in a 10-foot cube originating from you makes a Wisdom saving throw (DC {dc_cha}) or is "
            "charmed or frightened by you (your choice) until the end of your next turn",
            ((None, "each creature in a 10-foot cube originating from you to make a Wisdom saving throw against your warlock spell save DC"),
             (None, "charmed or frightened by you (your choice) until the end of your next turn"),
             (None, "you can't use it again until you finish a short or long rest"))),
    _w8_res("archfey-phb", "warlock", "archfey-phb-6-misty-escape", "Misty Escape", 1, "short-or-long",
            "Reaction when you take damage: turn invisible and teleport up to 60 feet to an unoccupied space you can see; you "
            "stay invisible until the start of your next turn or until you attack or cast a spell",
            ((None, "turn invisible and teleport up to 60 feet to an unoccupied space you can see"),
             (None, "you can't use it again until you finish a short or long rest"))),
    _w8_res("archfey-phb", "warlock", "archfey-phb-10-beguiling-defenses", "Beguiling Defenses", None, None,
            "You are immune to being charmed; when another creature tries to charm you, use your reaction to turn the charm "
            "back: it makes a Wisdom saving throw (DC {dc_cha}) or is charmed by you for 1 minute or until it takes damage",
            ((None, "You are immune to being charmed"),
             (None, "The creature must succeed on a Wisdom saving throw against your warlock spell save DC or be charmed by you for 1 minute or until the creature takes any damage"))),
    _w8_res("archfey-phb", "warlock", "archfey-phb-14-dark-delirium", "Dark Delirium", 1, "short-or-long",
            "Action: choose a creature you can see within 60 feet; it makes a Wisdom saving throw (DC {dc_cha}) or is charmed "
            "or frightened by you (your choice) for 1 minute or until your concentration is broken, thinking it is lost in a "
            "misty realm; it ends early if the creature takes damage",
            ((None, "choose a creature that you can see within 60 feet of you"),
             (None, "for 1 minute or until your concentration is broken"),
             (None, "You must finish a short or long rest before you can use this feature again"))),
    # ---- Warlock: The Celestial (XGE)
    _w8_res("celestial-xge", "warlock", "celestial-xge-1-healing-light", "Healing Light", "@level_plus1", "long",
            "A pool of d6s ({level_plus1} = 1 + your Warlock level); bonus action: heal one creature you can see within 60 "
            "feet by spending dice from the pool (at most {cha_dice} at once: your Charisma modifier, minimum one die), "
            "restoring the total rolled",
            ((None, "The number of dice in the pool equals 1 + your warlock level"),
             (None, "heal one creature you can see within 60 feet of you"),
             (None, "The maximum number of dice you can spend at once equals your Charisma modifier (minimum of one die)"),
             (None, "Your pool regains all expended dice when you finish a long rest")),
            die="d6"),
    _w8_res("celestial-xge", "warlock", "celestial-xge-6-radiant-soul", "Radiant Soul", None, None,
            "When you cast a spell that deals radiant or fire damage, add your Charisma modifier ({cha:+d}) to one radiant or "
            "fire damage roll of the spell against one of its targets",
            ((None, "you can add your Charisma modifier to one radiant or fire damage roll of that spell against one of its targets"),)),
    _w8_res("celestial-xge", "warlock", "celestial-xge-10-celestial-resilience", "Celestial Resilience", None, None,
            "Whenever you finish a short or long rest you gain {level_plus_cha} temporary hit points (your Warlock level + "
            "your Charisma modifier), and up to five creatures you can see at the end of the rest each gain "
            "{half_level_plus_cha} (half your Warlock level + your Charisma modifier)",
            ((None, "These temporary hit points equal your warlock level + your Charisma modifier"),
             (None, "choose up to five creatures you can see at the end of the rest"),
             (None, "temporary hit points equal to half your warlock level + your Charisma modifier"))),
    _w8_res("celestial-xge", "warlock", "celestial-xge-14-searing-vengeance", "Searing Vengeance", 1, "long",
            "When you have to make a death saving throw at the start of your turn, spring back to your feet instead: regain "
            "half your hit point maximum, and each creature of your choice within 30 feet takes 2d8{cha:+d} radiant damage "
            "(2d8 + your Charisma modifier) and is blinded until the end of the current turn",
            ((None, "You regain hit points equal to half your hit point maximum"),
             (None, "within 30 feet of you takes radiant damage equal to 2d8 + your Charisma modifier"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Warlock: The Fathomless (TCE)
    _w8_res("fathomless-tce", "warlock", "fathomless-tce-1-tentacle-of-the-deeps", "Tentacle of the Deeps", "@pb", "long",
            "Bonus action: create a 10-foot-long spectral tentacle at a point you can see within 60 feet for 1 minute (or "
            "until you create another); when you create it, and when you move it up to 30 feet as a bonus action, make a melee "
            "spell attack against a creature within 10 feet of it: {tentacle} cold damage on a hit and the target's speed is "
            "reduced by 10 feet until the start of your next turn",
            ((None, "you create a 10-foot-long tentacle at a point you can see within 60 feet of you"),
             (None, "The tentacle lasts for 1 minute"),
             (None, "the target takes 1d8 cold damage, and its speed is reduced by 10 feet until the start of your next turn"),
             (None, "When you reach 10th level in this class, the damage increases to 2d8"),
             (None, "you can move the tentacle up to 30 feet and repeat the attack"),
             (None, "You can summon the tentacle a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest")),
            dice="@tentacle", level_vars={"tentacle": TENTACLE_DICE_2014}),
    _w8_res("fathomless-tce", "warlock", "fathomless-tce-6-guardian-coil", "Guardian Coil", None, None,
            "Reaction: when you or a creature you can see takes damage while within 10 feet of the tentacle, reduce the damage "
            "to one of them by {tentacle}",
            ((None, "When you or a creature you can see takes damage while within 10 feet of the tentacle"),
             (None, "reduce the damage to that creature by 1d8")),
            level_vars={"tentacle": TENTACLE_DICE_2014}),
    _w8_res("fathomless-tce", "warlock", "fathomless-tce-10-grasping-tentacles", "Grasping Tentacles", 1, "long",
            "Cast Evard's black tentacles once without a spell slot; whenever you cast it you gain {level} temporary hit "
            "points (your Warlock level) and damage can't break your concentration on it",
            ((None, "You can also cast it once without a spell slot, and you regain the ability to do so when you finish a long rest"),
             (None, "granting you a number of temporary hit points equal to your warlock level"))),
    _w8_res("fathomless-tce", "warlock", "fathomless-tce-14-fathomless-plunge", "Fathomless Plunge", 1, "short-or-long",
            "Action: teleport yourself and up to five other willing creatures you can see within 30 feet to a body of water "
            "you've seen (pond size or larger) up to 1 mile away, each appearing within 30 feet of the others",
            ((None, "you can teleport yourself and up to five other willing creatures that you can see within 30 feet of you"),
             (None, "reappear up to 1 mile away in a body of water you've seen"),
             (None, "you can't use it again until you finish a short or long rest"))),
    # ---- Warlock: The Genie (TCE)
    _w8_res("genie-tce", "warlock", "genie-tce-1-genies-vessel", "Bottled Respite", 1, "long",
            "While touching your vessel (AC equal to your spell save DC {dc_cha}, hit points equal to your Warlock level plus "
            "your proficiency bonus = {level_plus_pb}, immune to poison and psychic damage): as an action vanish into it, an "
            "extradimensional 20-foot-radius cylinder 20 feet high, for up to {two_pb} hours (twice your proficiency "
            "bonus); you can't enter it again until you finish a long rest",
            ((None, "The vessel's AC equals your spell save DC"),
             (None, "Its hit points equal your warlock level plus your proficiency bonus"),
             (None, "a 20-foot-radius cylinder, 20 feet high"),
             (None, "up to a number of hours equal to twice your proficiency bonus"),
             (None, "you can't enter again until you finish a long rest"),
             ("genie-tce-10-sanctuary-vessel", "you can now choose up to five willing creatures that you can see within 30 feet of you"),
             ("genie-tce-10-sanctuary-vessel", "anyone (including you) who remains within the vessel for at least 10 minutes gains the benefit of finishing a short rest")),
            extras=(("genie-tce-10-sanctuary-vessel", "Sanctuary Vessel: up to five willing creatures within 30 feet can come in "
                     "with you; 10 minutes inside counts as a short rest, and anyone can add +{pb} (your proficiency bonus) to "
                     "the hit points regained from Hit Dice spent there"),)),
    _w8_res("genie-tce", "warlock", "genie-tce-1-genies-vessel", "Genie's Wrath", None, None,
            "Once during each of your turns when you hit with an attack roll, deal extra damage equal to your proficiency "
            "bonus (+{pb}), of a type set by your patron (bludgeoning dao, thunder djinni, fire efreeti, cold marid)",
            ((None, "Once during each of your turns when you hit with an attack roll, you can deal extra damage to the target equal to your proficiency bonus"),)),
    _w8_res("genie-tce", "warlock", "genie-tce-6-elemental-gift", "Elemental Gift", "@pb", "long",
            "Bonus action: a magical flying speed of 30 feet for 10 minutes, and you can hover",
            ((None, "as a bonus action, you can give yourself a flying speed of 30 feet that lasts for 10 minutes"),
             (None, "You can use this bonus action a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("genie-tce", "warlock", "genie-tce-14-limited-wish", "Limited Wish", 1, "other",
            "Action: speak a wish to your vessel for the effect of one spell of 6th level or lower with a casting time of 1 "
            "action, from any class's list and ignoring its requirements and costly components; after using it you can't "
            "use it again until you finish 1d4 long rests",
            ((None, "requesting the effect of one spell that is 6th level or lower and has a casting time of 1 action"),
             (None, "you can't use it again until you finish 1d4 long rests")),
            details={"recharges": "1d4 long rests"}),  # G4: the d4 is rolled by the player, so the recharge is "other"
    # ---- Warlock: The Great Old One (PHB)
    _w8_res("great-old-one-phb", "warlock", "great-old-one-phb-6-entropic-ward", "Entropic Ward", 1, "short-or-long",
            "Reaction when a creature makes an attack roll against you: impose disadvantage on it; if the attack misses, your "
            "next attack roll against the creature before the end of your next turn has advantage",
            ((None, "you can use your reaction to impose disadvantage on that roll"),
             (None, "you can't use it again until you finish a short or long rest"))),
    # ---- Warlock: The Hexblade (XGE)
    _w8_res("hexblade-xge", "warlock", "hexblade-xge-1-hexblades-curse", "Hexblade's Curse", 1, "short-or-long",
            "Bonus action: curse a creature you can see within 30 feet for 1 minute: a damage bonus equal to your proficiency "
            "bonus (+{pb}) against it, attack rolls against it are critical hits on a 19 or 20, and if it dies you regain "
            "{blessing} hit points (your Warlock level + your Charisma modifier, minimum 1)",
            ((None, "choose one creature you can see within 30 feet of you"),
             (None, "The bonus equals your proficiency bonus"),
             (None, "is a critical hit on a roll of 19 or 20 on the d20"),
             (None, "you regain hit points equal to your warlock level + your Charisma modifier (minimum of 1 hit point)"),
             (None, "You can't use this feature again until you finish a short or long rest"))),
    _w8_res("hexblade-xge", "warlock", "hexblade-xge-6-accursed-specter", "Accursed Specter", 1, "long",
            "When you slay a humanoid, its spirit rises as a specter with {half_level} temporary hit points (half your Warlock "
            "level) and an attack bonus equal to your Charisma modifier (minimum +0, currently +{cha_min0}); it serves until "
            "the end of your next long rest",
            ((None, "it gains temporary hit points equal to half your warlock level"),
             (None, "a special bonus to its attack rolls equal to your Charisma modifier (minimum of +0)"),
             (None, "Once you bind a specter with this feature, you can't use the feature again until you finish a long rest"))),
    # ---- Warlock: The Undead (VRGR)
    _w8_res("undead-vrgr", "warlock", "undead-vrgr-1-form-of-dread", "Form of Dread", "@pb", "long",
            "Bonus action: transform for 1 minute with 1d10 + {level} temporary hit points (your Warlock level), immunity to "
            "the frightened condition, and once during each of your turns when you hit with an attack roll you can force the "
            "target to make a Wisdom saving throw or be frightened of you until the end of your next turn",
            ((None, "you transform for 1 minute"),
             (None, "You gain temporary hit points equal to 1d10 + your warlock level"),
             (None, "the target is frightened of you until the end of your next turn"),
             (None, "You can transform a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("undead-vrgr", "warlock", "undead-vrgr-10-necrotic-husk", "Necrotic Husk", 1, "other",
            "Reaction when you would be reduced to 0 hit points: drop to 1 hit point instead; each creature of your choice "
            "within 30 feet takes 2d10 + {level} necrotic damage (your Warlock level) and you gain 1 level of exhaustion; "
            "you can't do it again until you finish 1d4 long rests",
            ((None, "you can use your reaction to drop to 1 hit point instead"),
             (None, "takes necrotic damage equal to 2d10 + your warlock level"),
             (None, "You then gain 1 level of exhaustion"),
             (None, "you can't do so again until you finish 1d4 long rests")),
            details={"recharges": "1d4 long rests"}),  # G4
    _w8_res("undead-vrgr", "warlock", "undead-vrgr-14-spirit-projection", "Spirit Projection", 1, "long",
            "Action: project your spirit from your body for up to 1 hour or until your concentration is broken; your body is "
            "unconscious; you and your spirit resist bludgeoning, piercing and slashing damage, have a flying speed equal to "
            "your walking speed, and take 1d10 force damage if you end your turn inside a creature or an object",
            ((None, "Your spirit can remain outside your body for up to 1 hour or until your concentration is broken"),
             (None, "you take 1d10 force damage if you end your turn inside a creature or an object"),
             (None, "Once you use this feature, you can't do so again until you finish a long rest"))),
    # ---- Warlock: The Undying (SCAG)
    _w8_res("undying-scag", "warlock", "undying-scag-1-among-the-dead", "Among the Dead", None, None,
            "Advantage on saving throws against disease; an undead that targets you directly with an attack or harmful spell "
            "makes a Wisdom saving throw (DC {dc_cha}) or must choose a new target; on a success it is immune for 24 hours",
            ((None, "You also have advantage on saving throws against any disease"),
             (None, "that creature must make a Wisdom saving throw against your spell save DC"),
             (None, "the creature is immune to this effect for 24 hours"))),
    _w8_res("undying-scag", "warlock", "undying-scag-6-defy-death", "Defy Death", 1, "long",
            "When you succeed on a death saving throw or stabilize a creature with spare the dying, regain 1d8 "
            "{con:+d} hit points (minimum 1 hit point in total)",
            ((None, "You can regain hit points equal to 1d8 + your Constitution modifier (minimum of 1 hit point)"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    _w8_res("undying-scag", "warlock", "undying-scag-14-indestructible-life", "Indestructible Life", 1, "short-or-long",
            "Bonus action on your turn: regain 1d8 + {level} hit points (your Warlock level); a severed body part you put back "
            "in place reattaches",
            ((None, "you can use a bonus action to regain hit points equal to 1d8 + your warlock level"),
             (None, "Once you use this feature, you can't use it again until you finish a short or long rest"))),
    # ---- Wizard: School of Abjuration (PHB)
    _w8_res("abjuration-phb", "wizard", "abjuration-phb-2-arcane-ward", "Arcane Ward", 1, "long",
            "When you cast an abjuration spell of 1st level or higher, create a ward on yourself until you finish a long rest: "
            "its hit point maximum is {ward_hp} (twice your Wizard level + your Intelligence modifier), it takes your damage "
            "first, and it regains twice the spell's level in hit points whenever you cast an abjuration spell of 1st level "
            "or higher; you can't create it again until a long rest",
            ((None, "The ward has a hit point maximum equal to twice your wizard level + your Intelligence modifier"),
             (None, "the ward regains a number of hit points equal to twice the level of the spell"),
             (None, "Once you create the ward, you can't create it again until you finish a long rest"))),
    _w8_res("abjuration-phb", "wizard", "abjuration-phb-10-improved-abjuration", "Improved Abjuration", None, None,
            "When you cast an abjuration spell that needs an ability check as part of casting (counterspell, dispel magic), add "
            "your proficiency bonus (+{pb}) to that check",
            ((None, "you add your proficiency bonus to that ability check"),)),
    # ---- Wizard: Bladesinging (TCE)
    _w8_res("bladesinging-tce", "wizard", "bladesinging-tce-2-bladesong", "Bladesong", "@pb", "long",
            "Bonus action, 1 minute (not in medium or heavy armor or with a shield; it ends if you use two hands to attack): "
            "AC +{int_min1} (Intelligence modifier, minimum +1), walking speed +10 feet, advantage on Dexterity (Acrobatics) "
            "checks, and +{int_min1} to Constitution saving throws to keep concentration",
            ((None, "You gain a bonus to your AC equal to your Intelligence modifier (minimum of +1)"),
             (None, "Your walking speed increases by 10 feet"),
             (None, "The bonus equals your Intelligence modifier (minimum of +1)"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("bladesinging-tce", "wizard", "bladesinging-tce-10-song-of-defense", "Song of Defense", None, None,
            "While your Bladesong is active, when you take damage use your reaction and expend a spell slot to reduce the "
            "damage by five times the slot's level",
            ((None, "you can use your reaction to expend one spell slot and reduce that damage to you by an amount equal to five times the spell's slot level"),)),
    _w8_res("bladesinging-tce", "wizard", "bladesinging-tce-14-song-of-victory", "Song of Victory", None, None,
            "While your Bladesong is active, add your Intelligence modifier (minimum +1, currently +{int_min1}) to the damage "
            "of your melee weapon attacks",
            ((None, "you add your Intelligence modifier (minimum of +1) to the damage of your melee weapon attacks"),)),
    # ---- Wizard: Chronurgy Magic (EGW)
    _w8_res("chronurgy-egw", "wizard", "chronurgy-egw-2-chronal-shift", "Chronal Shift", 2, "long",
            "Reaction: after you or a creature you can see within 30 feet makes an attack roll, an ability check or a saving "
            "throw, force it to reroll and use the second result",
            ((None, "within 30 feet of you makes an attack roll, an ability check, or a saving throw"),
             (None, "You can use this ability twice, and you regain any expended uses when you finish a long rest"))),
    _w8_res("chronurgy-egw", "wizard", "chronurgy-egw-2-temporal-awareness", "Temporal Awareness", None, None,
            "You add your Intelligence modifier ({int:+d}) to your initiative rolls",
            ((None, "You can add your Intelligence modifier to your initiative rolls"),)),
    _w8_res("chronurgy-egw", "wizard", "chronurgy-egw-6-momentary-stasis", "Momentary Stasis", "@int_min1", "long",
            "Action: a Large or smaller creature you can see within 60 feet makes a Constitution saving throw (DC {dc_int}) or "
            "is encased until the end of your next turn or until it takes damage, incapacitated with speed 0",
            ((None, "a Large or smaller creature you can see within 60 feet of you to make a Constitution saving throw against your spell save DC"),
             (None, "You can use this feature a number of times equal to your Intelligence modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_res("chronurgy-egw", "wizard", "chronurgy-egw-10-arcane-abeyance", "Arcane Abeyance", 1, "short-or-long",
            "When you cast a spell with a slot of 4th level or lower, condense it into a gray bead (Tiny, AC 15, 1 hit point, "
            "immune to poison and psychic damage) held for 1 hour; a creature holding it can use its action to release the "
            "spell, which uses your spell attack bonus and save DC",
            ((None, "When you cast a spell using a spell slot of 4th level or lower"),
             (None, "held within a gray bead for 1 hour"),
             (None, "This bead is a Tiny object with AC 15 and 1 hit point"),
             (None, "Once you create a bead with this feature, you can't do so again until you finish a short or long rest"))),
    # ---- Wizard: School of Conjuration (PHB)
    _w8_res("conjuration-phb", "wizard", "conjuration-phb-6-benign-transposition", "Benign Transposition", 1, "long",
            "Action: teleport up to 30 feet to an unoccupied space you can see, or swap places with a willing Small or Medium "
            "creature in range; you can't use it again until you finish a long rest or cast a conjuration spell of 1st level "
            "or higher",
            ((None, "you can use your action to teleport up to 30 feet to an unoccupied space that you can see"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest or you cast a conjuration spell of 1st level or higher"))),
    # ---- Wizard: School of Divination (PHB)
    _w8_res("divination-phb", "wizard", "divination-phb-2-portent", "Portent", "@portent", "long",
            "When you finish a long rest, roll {portent} d20s and record them (three from level 14); you can replace any attack "
            "roll, saving throw or ability check made by you or a creature you can see with one of them, once per turn, "
            "choosing before the roll; each can be used once and unused ones are lost at your next long rest",
            ((None, "roll two d20s and record the numbers rolled"),
             (None, "only once per turn"),
             (None, "Each foretelling roll can be used only once"),
             ("divination-phb-14-greater-portent", "You roll three d20s for your Portent feature, rather than two")),
            level_vars={"portent": PORTENT_DICE_2014}),
    _w8_res("divination-phb", "wizard", "divination-phb-10-the-third-eye", "The Third Eye", 1, "short-or-long",
            "Action: choose one benefit until you are incapacitated or take a rest: darkvision out to 60 feet, seeing into the "
            "Ethereal Plane within 60 feet, reading any language, or seeing invisible creatures and objects within 10 feet in "
            "line of sight; you can't use it again until you finish a rest",
            ((None, "You gain darkvision out to a range of 60 feet"),
             (None, "You can see into the Ethereal Plane within 60 feet of you"),
             (None, "within 10 feet of you that are within line of sight"),
             (None, "You can't use the feature again until you finish a rest"))),
    # ---- Wizard: School of Enchantment (PHB)
    _w8_res("enchantment-phb", "wizard", "enchantment-phb-2-hypnotic-gaze", "Hypnotic Gaze", None, None,
            "Action: choose a creature you can see within 5 feet that can see or hear you; it makes a Wisdom saving throw (DC "
            "{dc_int}) or is charmed until the end of your next turn, incapacitated with speed 0; you can maintain it with "
            "your action; once it ends or the creature saves, you can't use it on that creature again until a long rest",
            ((None, "choose one creature that you can see within 5 feet of you"),
             (None, "it must succeed on a Wisdom saving throw against your wizard spell save DC"),
             (None, "you can't use this feature on that creature again until you finish a long rest"))),
    _w8_res("enchantment-phb", "wizard", "enchantment-phb-6-instinctive-charm", "Instinctive Charm", None, None,
            "Reaction when a creature you can see within 30 feet attacks you: it makes a Wisdom saving throw (DC {dc_int}) or "
            "must target the creature closest to it (not you or itself); after a success you can't use this on it again until "
            "a long rest; creatures that can't be charmed are immune",
            ((None, "when a creature you can see within 30 feet of you makes an attack roll against you"),
             (None, "The attacker must make a Wisdom saving throw against your wizard spell save DC"),
             (None, "you can't use this feature on the attacker again until you finish a long rest"))),
    _w8_res("enchantment-phb", "wizard", "enchantment-phb-14-alter-memories", "Alter Memories", None, None,
            "Once before an enchantment spell that charmed creatures expires, use your action to make a charmed creature "
            "forget time spent charmed: it makes an Intelligence saving throw (DC {dc_int}) or loses {one_plus_cha_min1} "
            "hour(s) of memories (1 + your Charisma modifier, minimum 1 in total), at most the spell's duration",
            ((None, "The creature must succeed on an Intelligence saving throw against your wizard spell save DC"),
             (None, "lose a number of hours of its memories equal to 1 + your Charisma modifier (minimum of 1)"))),
    # ---- Wizard: Graviturgy Magic (EGW)
    _w8_res("graviturgy-egw", "wizard", "graviturgy-egw-10-violent-attraction", "Violent Attraction", "@int_min1", "long",
            "Reaction: when another creature you can see within 60 feet hits with a weapon attack, the target takes an extra "
            "1d10 damage of the weapon's type; or when a creature within 60 feet takes fall damage, increase it by 2d10",
            ((None, "causing the attack's target to take an extra 1d10 damage of the weapon's type"),
             (None, "increase the fall's damage by 2d10"),
             (None, "You can use this feature a number of times equal to your Intelligence modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_res("graviturgy-egw", "wizard", "graviturgy-egw-14-event-horizon", "Event Horizon", 1, "long",
            "Action: for up to 1 minute (concentration), whenever a hostile creature starts its turn within 30 feet of you it "
            "makes a Strength saving throw (DC {dc_int}) or takes 2d10 force damage and has speed 0 until the start of its next "
            "turn; on a success half damage and each foot it moves costs 2 extra feet; you can use it again before a long rest "
            "by expending a spell slot of 3rd level or higher",
            ((None, "for up to 1 minute or until your concentration ends"),
             (None, "within 30 feet of you, it must make a Strength saving throw against your spell save DC"),
             (None, "it takes 2d10 force damage, and its speed is reduced to 0 until the start of its next turn"),
             (None, "or until you expend a spell slot of 3rd level or higher on it"))),
    # ---- Wizard: School of Illusion (PHB)
    _w8_res("illusion-phb", "wizard", "illusion-phb-10-illusory-self", "Illusory Self", 1, "short-or-long",
            "Reaction when a creature makes an attack roll against you: the attack automatically misses you and the illusory "
            "duplicate dissipates",
            ((None, "The attack automatically misses you, then the illusion dissipates"),
             (None, "you can't use it again until you finish a short or long rest"))),
    # ---- Wizard: School of Necromancy (PHB)
    _w8_res("necromancy-phb", "wizard", "necromancy-phb-2-grim-harvest", "Grim Harvest", None, None,
            "Once per turn when you kill one or more creatures with a spell of 1st level or higher you regain hit points equal "
            "to twice the spell's level, or three times its level for a necromancy spell (not for constructs or undead)",
            ((None, "Once per turn when you kill one or more creatures with a spell of 1st level or higher"),
             (None, "you regain hit points equal to twice the spell's level, or three times its level if the spell belongs to the School of Necromancy"))),
    _w8_res("necromancy-phb", "wizard", "necromancy-phb-6-undead-thralls", "Undead Thralls", None, None,
            "An undead you create with a necromancy spell has its hit point maximum increased by {level} (your Wizard level) and "
            "adds your proficiency bonus (+{pb}) to its weapon damage rolls; animate dead can target one additional corpse",
            ((None, "The creature's hit point maximum is increased by an amount equal to your wizard level"),
             (None, "The creature adds your proficiency bonus to its weapon damage rolls"))),
    _w8_res("necromancy-phb", "wizard", "necromancy-phb-14-command-undead", "Command Undead", None, None,
            "Action: an undead you can see within 60 feet makes a Charisma saving throw (DC {dc_int}; advantage if its "
            "Intelligence is 8 or higher) or is friendly to you and obeys your commands until you use this again; on a success "
            "you can't use it on that creature again; one with Intelligence 12 or higher repeats the save every hour",
            ((None, "choose one undead that you can see within 60 feet of you"),
             (None, "must make a Charisma saving throw against your wizard spell save DC"),
             (None, "If the target has an Intelligence of 8 or higher, it has advantage on the saving throw"))),
    # ---- Wizard: Order of Scribes (TCE)
    _w8_res("scribes-tce", "wizard", "scribes-tce-2-awakened-spellbook", "Awakened Spellbook", 1, "long",
            "While you hold the book: when you cast a wizard spell with a slot you can swap its damage type for one from "
            "another spell in your spellbook of the same level as the slot, and you can cast a wizard spell as a ritual in its "
            "normal casting time; once you use this benefit you can't again until you finish a long rest",
            ((None, "The latter spell must be of the same level as the spell slot you expend"),
             (None, "Once you use this benefit, you can't do so again until you finish a long rest"))),
    _w8_res("scribes-tce", "wizard", "scribes-tce-6-manifest-mind", "Manifest Mind", 1, "long",
            "Bonus action: manifest the mind of your Awakened Spellbook as a Tiny spectral object within 60 feet (dim light 10 "
            "feet, darkvision 60 feet); you can cast wizard spells on your turn from its space up to {pb} times per day (your "
            "proficiency bonus); a bonus action moves it up to 30 feet; it stops if it is more than 300 feet away; you can't "
            "conjure it again until a long rest unless you expend a spell slot of any level",
            ((None, "hovering in an unoccupied space of your choice within 60 feet of you"),
             (None, "You can do so a number of times per day equal to your proficiency bonus"),
             (None, "hover up to 30 feet to an unoccupied space"),
             (None, "more than 300 feet away from you"),
             (None, "unless you expend a spell slot of any level to conjure it again"))),
    _w8_res("scribes-tce", "wizard", "scribes-tce-10-master-scrivener", "Master Scrivener", None, None,
            "Whenever you finish a long rest, create one magic scroll from a 1st or 2nd level spell with a casting time of 1 "
            "action in your Awakened Spellbook, which must be within 5 feet; the spell counts as one level higher, and the "
            "scroll's spell vanishes when you cast it or when you finish your next long rest",
            ((None, "Whenever you finish a long rest, you can create one magic scroll"),
             (None, "The chosen spell must be of 1st or 2nd level and must have a casting time of 1 action"),
             (None, "counting as one level higher than normal"))),
    _w8_res("scribes-tce", "wizard", "scribes-tce-14-one-with-the-word", "One with the Word", 1, "long",
            "If you take damage while your spellbook's mind is manifested, use your reaction to dismiss it and prevent all of "
            "that damage; then roll 3d6: the spellbook loses spells totalling at least that spell level for 1d6 long rests "
            "(or you drop to 0 hit points if it holds too few)",
            ((None, "you can prevent all of that damage to you by using your reaction to dismiss the spectral mind"),
             (None, "Then roll 3d6"),
             (None, "Until you finish 1d6 long rests"),
             (None, "Once you use this reaction, you can't do so again until you finish a long rest"))),
    # ---- Wizard: School of Transmutation (PHB)
    _w8_res("transmutation-phb", "wizard", "transmutation-phb-10-shapechanger", "Shapechanger", 1, "short-or-long",
            "Cast polymorph without a spell slot, targeting only yourself and becoming a beast of challenge rating 1 or lower; "
            "you can still cast it normally with a slot",
            ((None, "You can cast polymorph without expending a spell slot"),
             (None, "transform into a beast whose challenge rating is 1 or lower"),
             (None, "Once you cast polymorph in this way, you can't do so again until you finish a short or long rest"))),
    _w8_res("transmutation-phb", "wizard", "transmutation-phb-14-master-transmuter", "Master Transmuter", 1, "long",
            "Action: consume your transmuter's stone (destroyed, and not remade until you finish a long rest) for one effect: "
            "Major Transformation (an object no larger than a 5-foot cube, 10 minutes of handling), Panacea (remove curses, "
            "diseases and poisons from a creature you touch and restore all its hit points), Restore Life (raise dead without "
            "a slot) or Restore Youth (reduce a willing creature's apparent age by 3d10 years, to a minimum of 13)",
            ((None, "can't be remade until you finish a long rest"),
             (None, "no larger than a 5-foot cube"),
             (None, "You must spend 10 minutes handling the object to transform it"),
             (None, "reduced by 3d10 years, to a minimum of 13 years"))),
    # ---- Wizard: War Magic (XGE)
    _w8_res("war-xge", "wizard", "war-xge-2-arcane-deflection", "Arcane Deflection", None, None,
            "Reaction when you are hit by an attack or fail a saving throw: +2 bonus to your AC against that attack or +4 to "
            "that saving throw; until the end of your next turn you can't cast spells other than cantrips",
            ((None, "you can use your reaction to gain a +2 bonus to your AC against that attack or a +4 bonus to that saving throw"),
             (None, "you can't cast spells other than cantrips until the end of your next turn"),
             ("war-xge-14-deflecting-shroud", "Up to three creatures of your choice that you can see within 60 feet of you each take force damage equal to half your wizard level")),
            extras=(("war-xge-14-deflecting-shroud", "Deflecting Shroud: up to three creatures of your choice within 60 feet "
                     "each take {half_level} force damage (half your Wizard level)"),)),
    _w8_res("war-xge", "wizard", "war-xge-2-tactical-wit", "Tactical Wit", None, None,
            "You can give yourself a bonus to initiative rolls equal to your Intelligence modifier ({int:+d})",
            ((None, "You can give yourself a bonus to your initiative rolls equal to your Intelligence modifier"),)),
    _w8_res("war-xge", "wizard", "war-xge-6-power-surge", "Power Surge", "@int_min1", "other",
            "You store at most {int_min1} power surges (your Intelligence modifier, minimum one); a long rest resets the power "
            "surges to one, a short rest that ends with none gives one, ending a spell with dispel magic or counterspell "
            "gives one; once per turn when you damage a creature or object with a wizard spell, spend one for extra force "
            "damage equal to {half_level} (half your Wizard level)",
            ((None, "You can store a maximum number of power surges equal to your Intelligence modifier (minimum of one)"),
             (None, "Whenever you finish a long rest, your number of power surges resets to one"),
             (None, "If you end a short rest with no power surges, you gain one power surge"),
             (None, "The extra damage equals half your wizard level")),
            # G4: `uses` is the maximum pool; the pool is refilled by the conditions below, never by "all uses on a rest"
            details={"recharges": "a long rest resets the power surges to one, a short rest that ends with none gives one, "
                                  "ending a spell with dispel magic or counterspell gives one"}),  # also in the note (export audit)
)

_W8D_NOTES: tuple[dict, ...] = (
    _w8_note("aberrant-mind-tce", "sorcerer", _SORC_SP, "aberrant-mind-tce-6-psionic-sorcery", "Psionic Sorcery",
             "Psionic Sorcery: a spell of 1st level or higher from your Psionic Spells can be cast by spending sorcery points "
             "equal to the spell's level instead of a spell slot; then it needs no verbal or somatic components and no "
             "material components unless they are consumed",
             ((None, "by spending a number of sorcery points equal to the spell's level"),
              (None, "it requires no verbal or somatic components"))),
)

SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + _W8D_TAIL
SUBCLASS_NOTES_2014_BOOKS = SUBCLASS_NOTES_2014_BOOKS + _W8D_NOTES

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

# ---- X2: per-turn / per-combat / per-rage limits of class and subclass features -------------------------------------
# Rows that were note-only (`uses` None, `recharge` None) although the catalog text limits the feature's main effect to
# "once per turn" / "only once per rage": X2 sets `uses` 1 and the recharge and appends the pinned sentence to the row's
# quotes when no quote has it yet. (table, subclass or None, feature id, name, recharge, sentence); the sentences are
# pinned against catalog.features by tests/test_x2_turn_combat_rage_recharges.py.
_DIVINE_STRIKE_SENTENCE = "Once on each of your turns when you hit a creature with a weapon attack"
X2_RECHARGE_UPGRADES: tuple[tuple, ...] = (
    ("RESOURCE_TAIL_2014", None, "foe-slayer", "Foe Slayer", "turn",
     "Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll"),
    ("RESOURCE_TAIL_2024", None, "xphb-monk-5-stunning-strike", "Stunning Strike", "turn",
     "Once per turn when you hit a creature with a Monk weapon or an Unarmed Strike"),
    ("SUBCLASS_TAIL_2014", "life", "divine-strike", "Divine Strike (Life Domain)", "turn", _DIVINE_STRIKE_SENTENCE),
) + tuple(
    ("SUBCLASS_TAIL_2014_BOOKS", sub, f"{sub}-8-divine-strike", f"Divine Strike ({dom} Domain)", "turn", _DIVINE_STRIKE_SENTENCE)
    for sub, dom in (("forge-xge", "Forge"), ("nature-phb", "Nature"), ("order-tce", "Order"), ("solidarity-psa", "Solidarity"),
                     ("strength-psa", "Strength"), ("tempest-phb", "Tempest"), ("trickery-phb", "Trickery"),
                     ("twilight-tce", "Twilight"), ("war-phb", "War"), ("zeal-psa", "Zeal"))
) + (
    ("SUBCLASS_TAIL_2014_BOOKS", "death-dmg", "death-dmg-8-divine-strike", "Divine Strike (Death Domain)", "turn",
     "Once on each of the cleric's turns when he or she hits a creature with a weapon attack"),
    ("SUBCLASS_TAIL_2014_BOOKS", "order-tce", "order-tce-17-orders-wrath", "Order's Wrath", "turn",
     "You can curse a creature in this way only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "cavalier-xge", "cavalier-xge-15-ferocious-charger", "Ferocious Charger", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "kensei-xge", "kensei-xge-6-one-with-the-blade", "Deft Strike", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "mercy-tce", "mercy-tce-3-hand-of-harm", "Hand of Harm", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "fey-wanderer-tce", "fey-wanderer-tce-3-dreadful-strikes", "Dreadful Strikes", "turn",
     "which can take this extra damage only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "swarmkeeper-tce", "swarmkeeper-tce-3-gathered-swarm", "Gathered Swarm", "turn",
     "Once on each of your turns, you can cause the swarm to assist you"),
    ("SUBCLASS_TAIL_2014_BOOKS", "divine-soul-xge", "divine-soul-xge-6-empowered-healing", "Empowered Healing", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "genie-tce", "genie-tce-1-genies-vessel", "Genie's Wrath", "turn",
     "Once during each of your turns when you hit with an attack roll"),
    ("SUBCLASS_TAIL_2014_BOOKS", "necromancy-phb", "necromancy-phb-2-grim-harvest", "Grim Harvest", "turn",
     "Once per turn when you kill one or more creatures with a spell of 1st level or higher"),
    ("SUBCLASS_TAIL_2014_BOOKS", "zealot-xge", "zealot-xge-6-fanatical-focus", "Fanatical Focus", "rage",
     "You can use this ability only once per rage"),
)


def _x2_upgrade(table_name: str, sub: str | None, feature: str, name: str, recharge: str, sentence: str) -> None:
    rows = list(globals()[table_name])
    hits = [i for i, row in enumerate(rows) if row["feature"] == feature and row["name"] == name
            and (sub is None or row.get("subclass") == sub)]
    assert len(hits) == 1, (table_name, feature, name)
    row = rows[hits[0]]
    assert row["uses"] is None and row["recharge"] is None, (feature, name)
    quotes = tuple(row["quotes"])
    if not any(sentence in quote for _fid, quote in quotes):
        quotes += ((feature, sentence),)
    rows[hits[0]] = {**row, "uses": 1, "recharge": recharge, "quotes": quotes}
    globals()[table_name] = tuple(rows)


# New rows (features the W6-W8 / RP11 scans skipped as "once per turn, no number"), appended to the tables.
SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + (
    _w8_res("samurai-xge", "fighter", "samurai-xge-15-rapid-strike", "Rapid Strike", 1, "turn",
            "If you take the Attack action on your turn and have advantage on an attack roll against one of the targets, "
            "forgo the advantage for that roll to make an additional weapon attack against that target as part of the same "
            "action; once per turn",
            ((None, "you can forgo the advantage for that roll to make an additional weapon attack against that target, as part of the same action"),
             (None, "You can do so no more than once per turn"))),
    _w8_res("kensei-xge", "monk", "kensei-xge-17-unerring-accuracy", "Unerring Accuracy", 1, "turn",
            "If you miss with an attack roll using a monk weapon on your turn, you can reroll it; once on each of your turns",
            ((None, "If you miss with an attack roll using a monk weapon on your turn, you can reroll it"),
             (None, "You can use this feature only once on each of your turns"))),
    _w8_res("gloom-stalker-xge", "ranger", "gloom-stalker-xge-11-stalkers-flurry", "Stalker's Flurry", 1, "turn",
            "Once on each of your turns when you miss with a weapon attack, make another weapon attack as part of the same action",
            ((None, "Once on each of your turns when you miss with a weapon attack, you can make another weapon attack as part of the same action"),)),
    _w8_res("wild-phb", "sorcerer", "wild-phb-18-spell-bombardment", "Spell Bombardment", 1, "turn",
            "When you roll damage for a spell and roll the highest number possible on any of the dice, choose one of those "
            "dice, roll it again and add that roll to the damage; once per turn",
            ((None, "When you roll damage for a spell and roll the highest number possible on any of the dice, choose one of those dice, roll it again and add that roll to the damage"),
             (None, "You can use the feature only once per turn"))),
)

SUBCLASS_TAIL_2024 = SUBCLASS_TAIL_2024 + (
    {"subclass": "fey-wanderer-xphb", "class": "ranger", "feature": "fey-wanderer-xphb-3-dreadful-strikes",
     "name": "Dreadful Strikes", "uses": 1, "recharge": "turn",
     "note": "When you hit a creature with a weapon you can deal an extra 1d4 Psychic damage (1d6 from Ranger level 11); a "
             "creature can take it only once per turn",
     "quotes": (("fey-wanderer-xphb-3-dreadful-strikes", "you can deal an extra 1d4 Psychic damage to the target"),
                ("fey-wanderer-xphb-3-dreadful-strikes", "which can take this extra damage only once per turn"),
                ("fey-wanderer-xphb-3-dreadful-strikes", "The extra damage increases to 1d6 when you reach Ranger level 11"))},
    {"subclass": "celestial-xphb", "class": "warlock", "feature": "celestial-xphb-6-radiant-soul",
     "name": "Radiant Soul", "uses": 1, "recharge": "turn",
     "note": "Once per turn, when a spell you cast deals Radiant or Fire damage, add your Charisma modifier ({cha:+d}) to "
             "that spell's damage against one of its targets",
     "quotes": (("celestial-xphb-6-radiant-soul", "Once per turn, when a spell you cast deals Radiant or Fire damage"),
                ("celestial-xphb-6-radiant-soul", "you can add your Charisma modifier to that spell's damage against one of the spell's targets"))},
    {"subclass": "hunter-xphb", "class": "ranger", "feature": "hunter-xphb-11-superior-hunters-prey",
     "name": "Superior Hunter's Prey", "uses": 1, "recharge": "turn",
     "note": "Once per turn when you deal damage to a creature marked by your Hunter's Mark, also deal that spell's extra "
             "damage to a different creature you can see within 30 feet of the first",
     "quotes": (("hunter-xphb-11-superior-hunters-prey", "Once per turn when you deal damage to a creature marked by your Hunter's Mark"),
                ("hunter-xphb-11-superior-hunters-prey", "you can also deal that spell's extra damage to a different creature that you can see within 30 feet of the first creature"))},
    {"subclass": "world-tree-xphb", "class": "barbarian", "feature": "world-tree-xphb-14-travel-along-the-tree",
     "name": "Travel Along the Tree", "uses": 1, "recharge": "rage",
     "note": "When you activate your Rage and as a Bonus Action while it is active, teleport up to 60 feet to an unoccupied "
             "space you can see; once per Rage the range is 150 feet and you can bring up to six willing creatures within "
             "10 feet of you",
     "quotes": (("world-tree-xphb-14-travel-along-the-tree", "you can teleport up to 60 feet to an unoccupied space you can see"),
                ("world-tree-xphb-14-travel-along-the-tree", "once per Rage, you can increase the range of that teleport to 150 feet"),
                ("world-tree-xphb-14-travel-along-the-tree", "you can also bring up to six willing creatures who are within 10 feet of you"))},
)

for _args in X2_RECHARGE_UPGRADES:
    _x2_upgrade(*_args)
del _args

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
    _XPHB_INV.format("thirsting-blade"): "Thirsting Blade: attack twice with the Attack action",
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

# G2: the three SRD (2014) Metamagic cards of the Sorcerer (levels 3, 10 and 17).
SRD_METAMAGIC_FEATURES = ("metamagic-1", "metamagic-2", "metamagic-3")

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
# VF2.4: languages the 2014 species records grant that the pick pool (LANGUAGES) does not hold. Display names only: they are
# never offered in a pick card. (a) The Primordial dialects the records key by name ({"auran": true} Kenku DMG / VGM,
# {"aquan": true} Locathah, Merfolk DMG, Sea Elf, Tortle TTP, {"terran": true} Deep Gnome DMG, ...); "ignan" completes the
# set (no record uses it yet). (b) The record's `other: true` ("another language, named in the text": Aven, Gith, Quori ...)
# -- `names` are written in the quoted sentence of the record's own Languages trait, which a test pins. Keyed by the catalog
# race / subrace id. `other` also stands for Vedalken in the Simic Hybrid choice ("your choice of Elvish or Vedalken").
SPECIES_DIALECT_LANGUAGES: dict[str, str] = {"auran": "Auran", "aquan": "Aquan", "ignan": "Ignan", "terran": "Terran"}
SPECIES_OTHER_LANGUAGES: dict[str, dict] = {
    "aarakocra-eepc": {"names": ["Aarakocra"], "quote": "You can speak, read, and write Common, Aarakocra, and Auran."},
    "aven-psa": {"names": ["Aven"], "quote": "You can speak, read, and write Common and Aven."},
    "aven-psd": {"names": ["Aven"], "quote": "You can speak, read, and write Common and Aven."},
    "bullywug-dmg": {"names": ["Bullywug"], "quote": "You can speak, read, and write Bullywug."},
    "gith-mtf": {"names": ["Gith"], "quote": "You can speak, read, and write Common and Gith."},
    "grung-oga": {"names": ["Grung"], "quote": "You can speak, read, and write Grung."},
    "kalashtar-erlw": {"names": ["Quori"], "quote": "You can speak, read, and write Common, Quori, and one other language of your choice."},
    "khenra-psa": {"names": ["Khenra"], "quote": "You can speak, read, and write Common and Khenra."},
    "kor-psz": {"names": ["Kor silent speech"], "quote": "You can speak, read, and write Common, and communicate in the silent speech of the Kor."},
    "leonin-mot": {"names": ["Leonin"], "quote": "You can speak, read, and write Common and Leonin."},
    "loxodon-ggr": {"names": ["Loxodon"], "quote": "You can speak, read, and write Common and Loxodon."},
    "merfolk-psz": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common, Merfolk, and one extra language of your choice."},
    "minotaur-ggr": {"names": ["Minotaur"], "quote": "You can speak, read, and write Common and Minotaur."},
    "minotaur-(amonkhet)-psa": {"names": ["Minotaur"], "quote": "You can speak, read, and write Common and Minotaur."},
    "naga-psa": {"names": ["Naga"], "quote": "You can speak, read, and write Common and Naga."},
    "simic-hybrid-ggr": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common and your choice of Elvish or Vedalken."},
    "siren-psx": {"names": ["Siren"],
                  "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign) and Siren."},
    "troglodyte-dmg": {"names": ["Troglodyte"], "quote": "You can speak, read, and write Troglodyte."},
    "vampire-psz": {"names": ["Vampire"], "quote": "You can speak, read, and write Common and Vampire."},
    "vedalken-ggr": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common, Vedalken, and one other language of your choice."},
    "vedalken-psk": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common and Vedalken."},
    "human-phb-keldon-psd": {"names": ["Keldon"], "quote": "You can speak, read, and write Common and Keldon."},
    "merfolk-psz-ixalan;-blue-psx": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign), Merfolk, and one additional language of your choice."},
    "merfolk-psz-ixalan;-green-psx": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign), Merfolk, and one additional language of your choice."},
}

# VF4.4: counted features of the SRD Levels file (`class_specific`) that disagree with the PHB class table. Level 1..20.
# Warlock "Eldritch Invocations" optionalfeatureProgression [0,2,2,2,3,3,4,4,5,5,5,6,6,6,7,7,7,8,8,8] (PHB p.107) and Sorcerer
# "Metamagic" {"3": 2, "10": 3, "17": 4} (PHB p.101), both read from the vendored class files by a test. The SRD Levels file has
# invocations_known 3 at L4 and 4 at L6, metamagic_known 4 at L16 (an audit of cantrips known, spells known, invocations and
# metamagic against every PHB class table found exactly these three). Nothing else in the file disagrees.
SRD_LEVELS_COUNT_FIXES: dict[tuple[str, str], list[int]] = {
    ("warlock", "invocations_known"): [0, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    ("sorcerer", "metamagic_known"): [0, 0, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4],
}

# VF4.2: the four GGR backgrounds whose `languageProficiencies` choose.from list holds the placeholder "other" (Boros
# Legionnaire, Golgari Agent, Izzet Engineer, Selesnya Initiate). The record's own "Languages:" line names the language
# ("Choose one of Elvish, Loxodon, or Sylvan"); `names` replace the placeholder in the pick card, in place. Keyed by the
# catalog background id; `quote` is that line (pinned by a test). Display names only, the pick pool LANGUAGES is unchanged.
BACKGROUND_OTHER_LANGUAGES: dict[str, dict] = {
    "boros-legionnaire-ggr": {"names": ["Minotaur"], "quote": "Choose one of Celestial, Draconic, Goblin, or Minotaur"},
    "golgari-agent-ggr": {"names": ["Kraul"], "quote": "Choose one of Elvish, Giant, or Kraul"},
    "izzet-engineer-ggr": {"names": ["Vedalken"], "quote": "Choose one of Draconic, Goblin, or Vedalken"},
    "selesnya-initiate-ggr": {"names": ["Loxodon"], "quote": "Choose one of Elvish, Loxodon, or Sylvan"},
}

# id -> display name of every language any ruleset can produce (exports read this).
LANGUAGE_NAMES: dict[str, str] = {
    lang["index"]: lang["name"] for lang in LANGUAGES + LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE
}
LANGUAGE_NAMES.update(SPECIES_DIALECT_LANGUAGES)
LANGUAGE_NAMES.update({n.lower().replace(" ", "-"): n for row in SPECIES_OTHER_LANGUAGES.values() for n in row["names"]})
LANGUAGE_NAMES.update({n.lower().replace(" ", "-"): n for row in BACKGROUND_OTHER_LANGUAGES.values() for n in row["names"]})  # VF4.2

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
     "label": msg("label-prefixed", head="Student of War", tail=msg("label-artisans-tools")),
     "quote": "You gain proficiency with one type of Artisan's Tools of your choice"},
    {"subclass": "battle-master-xphb", "class": "fighter", "feature": "battle-master-xphb-3-student-of-war",
     "kind": "skills", "pool": "class-level-1:fighter", "count": 1, "cid": "feature",
     "label": msg("label-prefixed", head="Student of War", tail=msg("label-skill")),
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


# G1: 2014 Hunter (SRD) and Totem Warrior (PHB) pick effects as note-only subclass resources, the 2014 twin of
# SUBCLASS_OPTIONS_2024 (RP13). The pick cards already exist (the SRD `subfeature_options` of Hunter's Prey, Defensive
# Tactics, Multiattack and Superior Hunter's Defense; the `text_options` of the three Totem Warrior features); what a
# picked option does was not shown. Keyed by the card's feature id (the parent record, whose level is the card's first
# level); `options` maps the option id (what `choices[].selected` holds) to its entry. `quote` is a verbatim part of the
# record text (pinned by tests): the option's own child record for the Hunter (`record`), the parent's "Name. text"
# line for the Totem Warrior. `note` is the entry's text, `uses` + `recharge` (the X2 vocabulary) only where the quoted
# text states a limit: "only once per turn" / "Once on each of your turns" -> 1 + "turn"; "you can use your reaction"
# -> 1 + "other" with "Reaction:" first in the note; `dc` names the note variable that holds a DC the text gives
# ("DC 8 + your Strength bonus + your proficiency bonus", Elk Totemic Attunement only). Ruleset "mixed" / "2014" only.
def _g1(subclass, cls, label, options):
    return {"class": cls, "subclass": subclass, "label": label, "options": options}


def _g1_child(option_id, name, quote, note, **kw):
    """A Hunter option: the quote lives in the option's own child record (the option id)."""
    return option_id, {"name": name, "record": option_id, "quote": quote, "note": note, **kw}


def _g1_totem(feature, animal, quote, note, **kw):
    """A Totem Warrior option: a "<Animal>. text" line of the feature record."""
    return f"{feature}--{animal.lower()}", {"name": animal, "quote": quote, "note": note, **kw}


_TOTEM_SPIRIT = "totem-warrior-phb-3-totem-spirit"
_TOTEM_ASPECT = "totem-warrior-phb-6-aspect-of-the-beast"
_TOTEM_ATTUNE = "totem-warrior-phb-14-totemic-attunement"

SUBCLASS_PICK_RESOURCES_2014: dict[str, dict] = {
    "hunters-prey": _g1("hunter", "ranger", "Hunter's Prey", dict([
        _g1_child("hunters-prey-colossus-slayer", "Colossus Slayer",
                  "the creature takes an extra 1d8 damage if it's below its hit point maximum. You can deal this extra "
                  "damage only once per turn.",
                  "Once per turn, a weapon attack against a creature below its hit point maximum deals an extra 1d8 damage",
                  uses=1, recharge="turn"),
        _g1_child("hunters-prey-giant-killer", "Giant Killer",
                  "When a Large or larger creature within 5 feet of you hits or misses you with an attack, you can use "
                  "your reaction to attack that creature immediately after its attack, provided that you can see the creature.",
                  "Reaction: when a Large or larger creature within 5 feet of you hits or misses you with an attack, attack "
                  "that creature immediately after its attack, provided that you can see it",
                  uses=1, recharge="other"),
        _g1_child("hunters-prey-horde-breaker", "Horde Breaker",
                  "Once on each of your turns when you make a weapon attack, you can make another attack with the same "
                  "weapon against a different creature that is within 5 feet of the original target and within range of "
                  "your weapon.",
                  "Once on each of your turns when you make a weapon attack, make another attack with the same weapon "
                  "against a different creature within 5 feet of the original target and within range of your weapon",
                  uses=1, recharge="turn"),
    ])),
    "defensive-tactics": _g1("hunter", "ranger", "Defensive Tactics", dict([
        _g1_child("defensive-tactics-escape-the-horde", "Escape the Horde",
                  "Opportunity attacks against you are made with disadvantage.",
                  "Opportunity attacks against you are made with disadvantage"),
        _g1_child("defensive-tactics-multiattack-defense", "Multiattack Defense",
                  "When a creature hits you with an attack, you gain a +4 bonus to AC against all subsequent attacks made "
                  "by that creature for the rest of the turn.",
                  "When a creature hits you with an attack, you gain a +4 bonus to AC against all subsequent attacks made "
                  "by that creature for the rest of the turn"),
        _g1_child("defensive-tactics-steel-will", "Steel Will",
                  "You have advantage on saving throws against being frightened.",
                  "Advantage on saving throws against being frightened"),
    ])),
    "multiattack": _g1("hunter", "ranger", "Multiattack", dict([
        _g1_child("multiattack-volley", "Volley",
                  "You can use your action to make a ranged attack against any number of creatures within 10 feet of a "
                  "point you can see within your weapon's range.",
                  "Action: make a ranged attack against any number of creatures within 10 feet of a point you can see "
                  "within your weapon's range, with ammunition for each target and a separate attack roll for each target"),
        _g1_child("multiattack-whirlwind-attack", "Whirlwind Attack",
                  "You can use your action to make a melee attack against any number of creatures within 5 feet of you, "
                  "with a separate attack roll for each target.",
                  "Action: make a melee attack against any number of creatures within 5 feet of you, with a separate "
                  "attack roll for each target"),
    ])),
    "superior-hunters-defense": _g1("hunter", "ranger", "Superior Hunter's Defense", dict([
        _g1_child("superior-hunters-defense-evasion", "Evasion",
                  "you instead take no damage if you succeed on the saving throw, and only half damage if you fail.",
                  "Dexterity saving throws against effects that deal half damage on a success: no damage on a success, "
                  "half damage on a failure"),
        _g1_child("superior-hunters-defense-stand-against-the-tide", "Stand Against the Tide",
                  "When a hostile creature misses you with a melee attack, you can use your reaction to force that "
                  "creature to repeat the same attack against another creature (other than itself) of your choice.",
                  "Reaction: when a hostile creature misses you with a melee attack, force it to repeat the same attack "
                  "against another creature (other than itself) of your choice",
                  uses=1, recharge="other"),
        _g1_child("superior-hunters-defense-uncanny-dodge", "Uncanny Dodge",
                  "When an attacker that you can see hits you with an attack, you can use your reaction to halve the "
                  "attack's damage against you.",
                  "Reaction: when an attacker that you can see hits you with an attack, halve the attack's damage "
                  "against you",
                  uses=1, recharge="other"),
    ])),
    _TOTEM_SPIRIT: _g1("totem-warrior-phb", "barbarian", "Totem Spirit", dict([
        _g1_totem(_TOTEM_SPIRIT, "Bear", "Bear. While raging, you have resistance to all damage except psychic damage.",
                  "While raging, resistance to all damage except psychic damage"),
        _g1_totem(_TOTEM_SPIRIT, "Eagle",
                  "Eagle. While you're raging and aren't wearing heavy armor, other creatures have disadvantage on "
                  "opportunity attack rolls against you, and you can use the Dash action as a bonus action on your turn.",
                  "While raging and not wearing heavy armor, other creatures have disadvantage on opportunity attack rolls "
                  "against you, and you can use the Dash action as a bonus action on your turn"),
        _g1_totem(_TOTEM_SPIRIT, "Elk",
                  "Elk. While you're raging and aren't wearing heavy armor, your walking speed increases by 15 feet.",
                  "While raging and not wearing heavy armor, your walking speed increases by 15 feet"),
        _g1_totem(_TOTEM_SPIRIT, "Tiger",
                  "Tiger. While raging, you can add 10 feet to your long jump distance and 3 feet to your high jump distance.",
                  "While raging, add 10 feet to your long jump distance and 3 feet to your high jump distance"),
        _g1_totem(_TOTEM_SPIRIT, "Wolf",
                  "Wolf. While you're raging, your friends have advantage on melee attack rolls against any creature "
                  "within 5 feet of you that is hostile to you.",
                  "While raging, your friends have advantage on melee attack rolls against any creature within 5 feet of "
                  "you that is hostile to you"),
    ])),
    _TOTEM_ASPECT: _g1("totem-warrior-phb", "barbarian", "Aspect of the Beast", dict([
        _g1_totem(_TOTEM_ASPECT, "Bear",
                  "Bear. You gain the might of a bear. Your carrying capacity (including maximum load and maximum lift) "
                  "is doubled, and you have advantage on Strength checks made to push, pull, lift, or break objects.",
                  "Carrying capacity (including maximum load and maximum lift) is doubled, and advantage on Strength "
                  "checks made to push, pull, lift, or break objects"),
        _g1_totem(_TOTEM_ASPECT, "Eagle",
                  "Eagle. You gain the eyesight of an eagle. You can see up to 1 mile away with no difficulty, able to "
                  "discern even fine details as though looking at something no more than 100 feet away from you. "
                  "Additionally, dim light doesn't impose disadvantage on your Wisdom (Perception) checks.",
                  "See up to 1 mile away with no difficulty, discerning fine details as though looking at something no "
                  "more than 100 feet away; dim light doesn't impose disadvantage on Wisdom (Perception) checks"),
        _g1_totem(_TOTEM_ASPECT, "Elk",
                  "Elk. Whether mounted or on foot, your travel pace is doubled, as is the travel pace of up to ten "
                  "companions while they're within 60 feet of you and you're not incapacitated.",
                  "Whether mounted or on foot, your travel pace is doubled, as is the travel pace of up to ten companions "
                  "while they're within 60 feet of you and you're not incapacitated"),
        _g1_totem(_TOTEM_ASPECT, "Tiger",
                  "Tiger. You gain proficiency in two skills from the following list: Athletics, Acrobatics, Stealth, "
                  "and Survival.",
                  "Proficiency in two skills from the following list: Athletics, Acrobatics, Stealth, and Survival "
                  "(not tracked in the proficiencies)"),
        _g1_totem(_TOTEM_ASPECT, "Wolf",
                  "Wolf. You gain the hunting sensibilities of a wolf. You can track other creatures while traveling at "
                  "a fast pace, and you can move stealthily while traveling at a normal pace.",
                  "You can track other creatures while traveling at a fast pace, and you can move stealthily while "
                  "traveling at a normal pace"),
    ])),
    _TOTEM_ATTUNE: _g1("totem-warrior-phb", "barbarian", "Totemic Attunement", dict([
        _g1_totem(_TOTEM_ATTUNE, "Bear",
                  "Bear. While you're raging, any creature within 5 feet of you that's hostile to you has disadvantage on "
                  "attack rolls against targets other than you or another character with this feature.",
                  "While raging, any creature within 5 feet of you that's hostile to you has disadvantage on attack rolls "
                  "against targets other than you or another character with this feature (immune if it can't see or hear "
                  "you or can't be frightened)"),
        _g1_totem(_TOTEM_ATTUNE, "Eagle",
                  "Eagle. While raging, you have a flying speed equal to your current walking speed. This benefit works "
                  "only in short bursts; you fall if you end your turn in the air and nothing else is holding you aloft.",
                  "While raging, a flying speed equal to your current walking speed, only in short bursts: you fall if you "
                  "end your turn in the air and nothing else is holding you aloft"),
        _g1_totem(_TOTEM_ATTUNE, "Elk",
                  "Elk. While raging, you can use a bonus action during your move to pass through the space of a Large or "
                  "smaller creature. That creature must succeed on a Strength saving throw (DC 8 + your Strength bonus + "
                  "your proficiency bonus) or be knocked prone and take bludgeoning damage equal to 1d12 + your Strength "
                  "modifier.",
                  "While raging, use a bonus action during your move to pass through the space of a Large or smaller "
                  "creature, which must succeed on a Strength saving throw (DC {dc_str}) or be knocked prone and take "
                  "bludgeoning damage equal to 1d12{str:+d}",
                  dc="dc_str"),
        _g1_totem(_TOTEM_ATTUNE, "Tiger",
                  "Tiger. While you're raging, if you move at least 20 feet in a straight line toward a Large or smaller "
                  "target right before making a melee weapon attack against it, you can use a bonus action to make an "
                  "additional melee weapon attack against it.",
                  "While raging, if you move at least 20 feet in a straight line toward a Large or smaller target right "
                  "before making a melee weapon attack against it, use a bonus action to make an additional melee weapon "
                  "attack against it"),
        _g1_totem(_TOTEM_ATTUNE, "Wolf",
                  "Wolf. While you're raging, you can use a bonus action on your turn to knock a Large or smaller "
                  "creature prone when you hit it with melee weapon attack.",
                  "While raging, use a bonus action on your turn to knock a Large or smaller creature prone when you hit "
                  "it with a melee weapon attack"),
    ])),
}


# G4: Way of the Four Elements (PHB) discipline ki costs on the Ki resource, and Rune Knight (TCE) runes as resources.
# Both read the pick cards that already exist (`choices[].selected`), mixed / 2014 only and only for the selected
# subclass. Every entry has verbatim `quotes` taken from the option's own catalog record (pinned by tests).
# Disciplines: `cost` is the base ki cost the text states ("You can spend 2 ki points to cast thunderwave."); `more` is the
# optional extra the same text allows (Fangs of the Fire Snake: one more ki point when the attack hits; Unbroken Air and
# Water Whip: one more ki point per extra 1d10). Elemental Attunement (granted, "elemental forces" with no ki) has no cost
# in its text and is not listed. The card is `class:monk:3:feature:<feature>`; the costs go to `target` (details.disciplineKiCosts
# {option id: base cost} and a sentence on its note).
def _ed(name, cost, *quotes, more=None):
    return {"name": name, "cost": cost, "quotes": quotes, **({"more": more} if more else {})}


ELEMENTAL_DISCIPLINES_2014: dict = {
    "class": "monk", "subclass": "four-elements-phb", "feature": "four-elements-phb-3-way-of-the-four-elements",
    "target": "monk:ki",
    "options": {
        "opt-breath-of-winter-phb": _ed("Breath of Winter", 6, "You can spend 6 ki points to cast cone of cold."),
        "opt-clench-of-the-north-wind-phb": _ed("Clench of the North Wind", 3, "You can spend 3 ki points to cast hold person."),
        "opt-eternal-mountain-defense-phb": _ed("Eternal Mountain Defense", 5, "You can spend 5 ki points to cast stoneskin, targeting yourself."),
        "opt-fangs-of-the-fire-snake-phb": _ed(
            "Fangs of the Fire Snake", 1, "you can spend 1 ki point to cause tendrils of flame to stretch out from your fists and feet",
            "if you spend 1 ki point when the attack hits, it also deals an extra 1d10 fire damage",
            more="1 more ki point when the attack hits: extra 1d10 fire damage"),
        "opt-fist-of-four-thunders-phb": _ed("Fist of Four Thunders", 2, "You can spend 2 ki points to cast thunderwave."),
        "opt-flames-of-the-phoenix-phb": _ed("Flames of the Phoenix", 4, "You can spend 4 ki points to cast fireball."),
        "opt-gong-of-the-summit-phb": _ed("Gong of the Summit", 3, "You can spend 3 ki points to cast shatter."),
        "opt-mist-stance-phb": _ed("Mist Stance", 4, "You can spend 4 ki points to cast gaseous form, targeting yourself."),
        "opt-ride-the-wind-phb": _ed("Ride the Wind", 4, "You can spend 4 ki points to cast fly, targeting yourself."),
        "opt-river-of-hungry-flame-phb": _ed("River of Hungry Flame", 5, "You can spend 5 ki points to cast wall of fire."),
        "opt-rush-of-the-gale-spirits-phb": _ed("Rush of the Gale Spirits", 2, "You can spend 2 ki points to cast gust of wind."),
        "opt-shape-the-flowing-river-phb": _ed(
            "Shape the Flowing River", 1, "As an action, you can spend 1 ki point to choose an area of ice or water"),
        "opt-sweeping-cinder-strike-phb": _ed("Sweeping Cinder Strike", 2, "You can spend 2 ki points to cast burning hands."),
        "opt-unbroken-air-phb": _ed(
            "Unbroken Air", 2, "As an action, you can spend 2 ki points and choose a creature within 30 feet of you.",
            "plus an extra 1d10 bludgeoning damage for each additional ki point you spend",
            more="1 more ki point per extra 1d10 bludgeoning damage"),
        "opt-water-whip-phb": _ed(
            "Water Whip", 2, "You can spend 2 ki points as an action to create a whip of water",
            "plus an extra 1d10 bludgeoning damage for each additional ki point you spend",
            more="1 more ki point per extra 1d10 bludgeoning damage"),
        "opt-wave-of-rolling-earth-phb": _ed("Wave of Rolling Earth", 6, "You can spend 6 ki points to cast wall of stone."),
    },
}

# Rune Knight Rune Carver: the picked rune is one resource, "Rune Carver: <Rune>", `uses` 1 and `recharge` "short-or-long"
# ("Once you invoke this rune, you can't do so again until you finish a short or long rest." in every rune record), 2 uses
# from Master of Runes ("You can invoke each rune you know from your Rune Carver feature twice, rather than once, and you
# regain all expended uses when you finish a short or long rest"; the level is that record's). `dc` (the Rune Magic save DC,
# 8 + proficiency bonus + Constitution modifier, note variable `dc_con`) only for the runes whose text names a saving throw
# (Fire: Strength, Stone: Wisdom). The card is `class:fighter:3:feature:<feature>`; the level requirement of the Hill and
# Storm runes is the card's.
_RUNE_LIMIT = "Once you invoke this rune, you can't do so again until you finish a short or long rest."


def _rune(name, note, *quotes, dc=None):
    return {"name": name, "quotes": (*quotes, _RUNE_LIMIT), "note": note, **({"dc": dc} if dc else {})}


RUNE_KNIGHT_RUNES_2014: dict = {
    "class": "fighter", "subclass": "rune-knight-tce", "feature": "rune-knight-tce-3-rune-knight", "label": "Rune Carver",
    "master": "rune-knight-tce-15-master-of-runes",
    "master_quotes": (("rune-knight-tce-15-master-of-runes", "You can invoke each rune you know from your Rune Carver feature twice, rather than once, and you regain all expended uses when you finish a short or long rest."),
                      ("rune-knight-tce-3-rune-carver", "your Rune Magic save DC equals 8 + your proficiency bonus + your Constitution modifier")),
    "options": {
        "opt-cloud-rune-tce": _rune(
            "Cloud Rune",
            "While wearing or carrying the inscribed object: advantage on Dexterity (Sleight of Hand) and Charisma (Deception) "
            "checks. Invoke (reaction): when you or a creature you can see within 30 feet of you is hit by an attack roll, "
            "choose a different creature within 30 feet of you, other than the attacker; it becomes the target of the attack, "
            "using the same roll, regardless of the attack's range",
            "you have advantage on Dexterity (Sleight of Hand) checks and Charisma (Deception) checks.",
            "you can use your reaction to invoke the rune and choose a different creature within 30 feet of you, other than the attacker."),
        "opt-fire-rune-tce": _rune(
            "Fire Rune",
            "While wearing or carrying the inscribed object: your proficiency bonus is doubled for any ability check that uses "
            "your proficiency with a tool. Invoke (when you hit a creature with a weapon attack): the target takes an extra "
            "2d6 fire damage and must succeed on a Strength saving throw (DC {dc_con}) or be restrained for 1 minute; while "
            "restrained it takes 2d6 fire damage at the start of each of its turns and repeats the save at the end of each "
            "of its turns",
            "your proficiency bonus is doubled for any ability check you make that uses your proficiency with a tool.",
            "the target takes an extra 2d6 fire damage, and it must succeed on a Strength saving throw or be restrained for 1 minute.",
            dc="dc_con"),
        "opt-frost-rune-tce": _rune(
            "Frost Rune",
            "While wearing or carrying the inscribed object: advantage on Wisdom (Animal Handling) and Charisma (Intimidation) "
            "checks. Invoke (bonus action): for 10 minutes, a +2 bonus to all ability checks and saving throws that use "
            "Strength or Constitution",
            "you have advantage on Wisdom (Animal Handling) checks and Charisma (Intimidation) checks.",
            "you gain a +2 bonus to all ability checks and saving throws that use Strength or Constitution."),
        "opt-hill-rune-tce": _rune(
            "Hill Rune",
            "While wearing or carrying the inscribed object: advantage on saving throws against being poisoned and resistance "
            "to poison damage. Invoke (bonus action): resistance to bludgeoning, piercing and slashing damage for 1 minute",
            "you have advantage on saving throws against being poisoned, and you have resistance against poison damage.",
            "gaining resistance to bludgeoning, piercing, and slashing damage for 1 minute."),
        "opt-stone-rune-tce": _rune(
            "Stone Rune",
            "While wearing or carrying the inscribed object: advantage on Wisdom (Insight) checks and darkvision out to 120 "
            "feet. Invoke (reaction, when a creature you can see ends its turn within 30 feet of you): it must make a Wisdom "
            "saving throw (DC {dc_con}); unless it succeeds, it is charmed by you for 1 minute, with a speed of 0 and "
            "incapacitated, and repeats the save at the end of each of its turns",
            "you have advantage on Wisdom (Insight) checks, and you have darkvision out to a range of 120 feet.",
            "force the creature to make a Wisdom saving throw.",
            dc="dc_con"),
        "opt-storm-rune-tce": _rune(
            "Storm Rune",
            "While wearing or carrying the inscribed object: advantage on Intelligence (Arcana) checks, and you can't be "
            "surprised while you aren't incapacitated. Invoke (bonus action): a prophetic state for 1 minute or until you're "
            "incapacitated; meanwhile, when you or another creature you can see within 60 feet of you makes an attack roll, a "
            "saving throw or an ability check, use your reaction to give the roll advantage or disadvantage",
            "you have advantage on Intelligence (Arcana) checks, and you can't be surprised as long as you aren't incapacitated.",
            "you can use your reaction to cause the roll to have advantage or disadvantage."),
    },
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
        "class": "druid", "subclass": "land-xphb", "label": msg("label-circle-spells-land"),
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
    # G5: the Forgotten Realms: Heroes of Faerun (FRHoF) subclasses (ruleset 2024 like the XPHB ones, source FRHoF).
    # Banneret is visible under "2024" only (it has a 2014 twin), Moon is also offered under "mixed" but this table is
    # read for ruleset "2024" only. NOT done (picks, not a literal spell: the 5etools blocks hold `choose` items): Moon's
    # Primal Lore cantrip (any Druid cantrip, replaceable on each Bard level) and Scion of the Three's Dread Allegiance
    # cantrip (one of three, changeable after every Long Rest, tied to the resistance pick: a one-rest choice, Q17).
    "banneret-frhof-3-knightly-envoy": {
        "class": "fighter", "subclass": "banneret-frhof", "mode": "innate", "spells": ("comprehend-languages",),
        "uses": "ritual only", "ability": "CHA", "ability_from": "text", "note": None,
        "quotes": ("Comprehension. You can cast the Comprehend Languages spell but only as a Ritual. Charisma is your "
                   "spellcasting ability for it.",)},
    "moon-frhof-6-blessing-of-moonlight": {
        "class": "bard", "subclass": "moon-frhof", "mode": "prepared", "spells": ("moonbeam",),
        "quotes": ("You always have the Moonbeam spell prepared.",)},
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
                        "casting_time": "1 action", "label": msg("label-feature-level", name="Spell Mastery", level=1), "grant": "Spell Mastery",
                        "sheet_key": "spellMastery"},
    "spell-mastery-2": {"feature": "xphb-wizard-18-spell-mastery", "class_level": 18, "spell_level": 2, "count": 1,
                        "casting_time": "1 action", "label": msg("label-feature-level", name="Spell Mastery", level=2), "grant": "Spell Mastery",
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
                        "casting_time": None, "label": msg("label-feature-level", name="Spell Mastery", level=1), "grant": "Spell Mastery",
                        "sheet_key": "spellMastery", "always_prepared": False, "feature_name": "Spell Mastery"},
    "spell-mastery-2": {"feature": "spell-mastery", "class_level": 18, "spell_level": 2, "count": 1,
                        "casting_time": None, "label": msg("label-feature-level", name="Spell Mastery", level=2), "grant": "Spell Mastery",
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


# VF7.2: 2014 subclass features that add ONE cantrip of the class's own list on top of the class table. Keyed by subclass id:
# {class, feature (catalog feature index, its level is the class level the grant starts at), extra}.
# Quote-pinned in tests/test_campaign_regressions.py: SRD "Bonus Cantrip" (Circle of the Land, Druid 2): "you learn one additional
# druid cantrip of your choice"; PHB: "This cantrip doesn't count against the number of druid cantrips you know." Modelled as a
# count bump on the class cantrip card (the pick is a druid cantrip), like the 2024 Thaumaturge / Magician (CLASS_OPTION_CHOICES_2024).
# Other "bonus cantrip" features were checked and are NOT in this table (fixed cantrips already reach `alwaysPrepared`: Light Domain,
# Illusion School, Celestial; the rest are other-list or conditional picks, see ARCHITECTURE VF7.2).
SUBCLASS_EXTRA_CANTRIPS_2014: dict[str, dict] = {
    "land": {"class": "druid", "feature": "bonus-cantrip", "extra": 1},
}


# VF7.3: the three SRD 2014 Ranger "Favored Enemy" features (class levels 1, 6, 14); each gain also teaches one language
# (PHB text quoted in tests/test_campaign_regressions.py).
FAVORED_ENEMY_FEATURES_2014: tuple[str, ...] = ("favored-enemy-1-type", "favored-enemy-2-types", "favored-enemy-3-enemies")
