"""Species trait effects and resources, draconic ancestry, the fly-in-armor ban, species AC, subclass proficiencies.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

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
    "kithkin-lfl-trait-2": {  # S13: Kithkin (LFL) is a `_copy` reprint; its Luck is the Halfling's, word for word
        "race": "kithkin-lfl", "name": "Luck", "uses": None, "recharge": None,
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
    # S13 (`_copy` reprints resolved): the same traits under their own ids
    "goblin-erlw-trait-3": _e("goblin-erlw", "Fury of the Small", 1, "short-or-long",
        "When you damage a creature larger than you, extra damage equal to your level ({level})",
        ("The extra damage equals your level", "you can't use it again until you finish a short or long rest")),
    "goblin-ggr-trait-3": _e("goblin-ggr", "Fury of the Small", 1, "short-or-long",
        "When you damage a creature larger than you, extra damage equal to your level ({level})",
        ("The extra damage equals your level", "you can't use it again until you finish a short or long rest")),
    "boggart-lfl-trait-3": _e("boggart-lfl", "Fury of the Small", "pb", "long",
        "When you damage a creature larger than you, extra damage equal to your Proficiency Bonus ({pb}); no more than once per turn",
        ("The extra damage equals your proficiency bonus", "regaining all expended uses when you finish a long rest",
         "no more than once per turn")),
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
    "hobgoblin-erlw-trait-4": _e("hobgoblin-erlw", "Saving Face", 1, "short-or-long",  # S13: the `_copy` reprint
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
    "faerie-lfl-trait-2": {"race": "faerie-lfl", "name": "Flight", "categories": _FLY_MEDIUM_HEAVY,  # S13: the `_copy` reprint of Fairy (MPMM)
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
