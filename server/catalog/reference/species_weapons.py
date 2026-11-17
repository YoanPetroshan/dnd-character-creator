"""Species natural weapons and the unarmed-strike damage type.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

SPECIES_NATURAL_WEAPONS: dict[str, dict] = {
    "aarakocra-dmg-trait-1": {"name": "Talons", "die": "1d4", "type": "slashing", "ability": "STR",
        "quote": 'which deal {@damage 1d4} slashing damage on a hit'},
    "aarakocra-eepc-trait-4": {"name": "Talons", "die": "1d4", "type": "slashing", "ability": "STR",
        "quote": 'you deal slashing damage equal to {@damage 1d4} + your Strength modifier'},
    "aarakocra-mpmm-trait-1": {"name": "Talons", "die": "1d6", "type": "slashing", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier slashing damage'},
    "centaur-ggr-trait-5": {"name": "Hooves", "die": "1d4", "type": "bludgeoning", "ability": "STR",
        "quote": 'you deal bludgeoning damage equal to {@damage 1d4} + your Strength modifier'},
    "centaur-mot-trait-5": {"name": "Hooves", "die": "1d4", "type": "bludgeoning", "ability": "STR",  # S13: `_copy` of Centaur (GGR)
        "quote": 'you deal bludgeoning damage equal to {@damage 1d4} + your Strength modifier'},
    "centaur-mpmm-trait-3": {"name": "Hooves", "die": "1d6", "type": "bludgeoning", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier bludgeoning damage'},
    "dhampir-rhw-trait-3": {"name": "Vampiric Bite", "die": "1d4", "type": "piercing", "ability": "CON",
        "quote": 'You deal Piercing damage equal to {@damage 1d4} plus your Constitution modifier',
        "note": 'bite-replaces'},
    "dhampir-vrgr-trait-5": {"name": "Vampiric Bite", "die": "1d4", "type": "piercing", "ability": "CON",
        "quote": 'You add your Constitution modifier, instead of your Strength modifier, to the attack and damage rolls when you attack with this bite. It deals {@damage 1d4} piercing damage on a hit.',
        "note": 'half-hp-advantage'},
    "gnoll-dmg-trait-0": {"name": "Bite", "die": "1d4", "type": "piercing", "ability": "STR",
        "quote": 'you deal piercing damage equal to {@damage 1d4} + your Strength modifier'},
    "leonin-mot-trait-4": {"name": "Claws", "die": "1d4", "type": "slashing", "ability": "STR",
        "quote": 'you can deal slashing damage equal to {@damage 1d4} + your Strength modifier'},
    "lizardfolk-mpmm-trait-1": {"name": "Bite", "die": "1d6", "type": "slashing", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier slashing damage'},
    "lizardfolk-vgm-trait-3": {"name": "Bite", "die": "1d6", "type": "piercing", "ability": "STR",
        "quote": 'you deal piercing damage equal to {@damage 1d6} + your Strength modifier'},
    "minotaur-ggr-trait-4": {"name": "Horns", "die": "1d6", "type": "piercing", "ability": "STR",
        "quote": 'you deal piercing damage equal to {@damage 1d6} + your Strength modifier'},
    "minotaur-mot-trait-4": {"name": "Horns", "die": "1d6", "type": "piercing", "ability": "STR",  # S13: `_copy` of Minotaur (GGR)
        "quote": 'you deal piercing damage equal to {@damage 1d6} + your Strength modifier'},
    "minotaur-mpmm-trait-0": {"name": "Horns", "die": "1d6", "type": "piercing", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier piercing damage'},
    "minotaur-(amonkhet)-psa-trait-3": {"name": "Horns", "die": "1d6", "type": "bludgeoning", "ability": "STR",
        "quote": 'you deal bludgeoning damage equal to {@damage 1d6} + your Strength modifier'},
    "naga-psa-trait-4": {"name": "Bite", "die": "1d4", "type": "piercing", "ability": "STR",
        "quote": 'you deal piercing damage equal to {@damage 1d4} + your Strength modifier',
        "note": 'naga-bite'},
    "satyr-mot-trait-4": {"name": "Ram", "die": "1d4", "type": "bludgeoning", "ability": "STR",
        "quote": 'you deal bludgeoning damage equal to {@damage 1d4} + your Strength modifier'},
    "satyr-mpmm-trait-1": {"name": "Ram", "die": "1d6", "type": "bludgeoning", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier bludgeoning damage'},
    "tabaxi-mpmm-trait-2": {"name": "Cat's Claws", "die": "1d6", "type": "slashing", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier slashing damage'},
    "tabaxi-vgm-trait-4": {"name": "Cat's Claws", "die": "1d4", "type": "slashing", "ability": "STR",
        "quote": 'you deal slashing damage equal to {@damage 1d4} + your Strength modifier'},
    "tortle-mpmm-trait-1": {"name": "Claws", "die": "1d6", "type": "slashing", "ability": "STR",
        "quote": 'the strike deals {@damage 1d6} + your Strength modifier slashing damage'},
    "tortle-ttp-trait-4": {"name": "Claws", "die": "1d4", "type": "slashing", "ability": "STR",
        "quote": 'you deal slashing damage equal to {@damage 1d4} + your Strength modifier'},
}

# VF7.5: the Longtooth shifting feature (MPMM and EFA Shifter lineages): while shifted, a bonus-action unarmed strike with the fangs.
# Keyed by (species id, variant id); `quote` is pinned against the raw races.json entry (the variant text is not a catalog trait).
SPECIES_VARIANT_NATURAL_WEAPONS: dict[tuple[str, str], dict] = {
    ("shifter-mpmm", "longtooth"): {
        "name": "Longtooth", "die": "1d6", "type": "piercing", "ability": "STR",
        "quote": "you can deal piercing damage equal to {@damage 1d6} + your Strength modifier", "note": "shifted-bonus-action"},
    ("shifter-efa", "longtooth"): {
        "name": "Longtooth", "die": "1d6", "type": "piercing", "ability": "STR",
        "quote": "you can deal Piercing damage equal to {@dice 1d6} plus your Strength modifier", "note": "shifted-bonus-action"},
}

# VF7.5: a species trait that changes the damage type of every Unarmed Strike (Lupin, RHW: "Your Unarmed Strikes deal Slashing
# damage instead of Bludgeoning damage").
SPECIES_UNARMED_TYPE: dict[str, dict] = {
    "lupin-rhw-trait-1": {"type": "slashing", "quote": "deal Slashing damage instead of Bludgeoning damage"},
}
