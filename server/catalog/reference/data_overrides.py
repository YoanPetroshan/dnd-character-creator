"""Ruleset helpers, feat and background overrides, DATA_OVERRIDES and the source names.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

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
    "AU": "Unearthed Arcana (AU)",  # playtest material; the feats of this source are not a published book (audit DATA-07)
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
