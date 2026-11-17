"""Class feature effects (2014 and 2024), weapon proficiency ids and the 2024 equipment item maps.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

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
