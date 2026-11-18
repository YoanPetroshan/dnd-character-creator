"""Subclass picks and option cards, rune knight runes, wizard spell picks.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .core_tables import msg

# literal keys (a test pins that every msg() key is a literal)
DTYPE_MSG = {
    "acid": lambda: msg("opt-dtype-acid"),
    "bludgeoning": lambda: msg("opt-dtype-bludgeoning"),
    "cold": lambda: msg("opt-dtype-cold"),
    "fire": lambda: msg("opt-dtype-fire"),
    "force": lambda: msg("opt-dtype-force"),
    "lightning": lambda: msg("opt-dtype-lightning"),
    "necrotic": lambda: msg("opt-dtype-necrotic"),
    "piercing": lambda: msg("opt-dtype-piercing"),
    "poison": lambda: msg("opt-dtype-poison"),
    "psychic": lambda: msg("opt-dtype-psychic"),
    "radiant": lambda: msg("opt-dtype-radiant"),
    "slashing": lambda: msg("opt-dtype-slashing"),
    "thunder": lambda: msg("opt-dtype-thunder"),
}

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
            t: {"name": t.title(), "resist": [t], "summary": msg("opt-affinity", dtype=DTYPE_MSG[t]()),
                "note": f"Add your Charisma modifier ({{cha:+d}}) to one damage roll of a {t} damage spell"}
            for t in ("acid", "cold", "fire", "lightning", "poison")},
    },
    "beast-master-xphb-3-primal-companion": {
        "class": "ranger", "subclass": "beast-master-xphb", "label": "Primal Companion",
        "quotes": ("Choose its stat block: Beast of the Land, Beast of the Sea, or Beast of the Sky.",),
        "options": {
            "beast-of-the-land": {"name": "Beast of the Land", "summary": msg("opt-companion-land")},
            "beast-of-the-sea": {"name": "Beast of the Sea", "summary": msg("opt-companion-sea")},
            "beast-of-the-sky": {"name": "Beast of the Sky", "summary": msg("opt-companion-sky")},
        }},
    "fey-wanderer-xphb-3-fey-wanderer-spells": {
        "class": "ranger", "subclass": "fey-wanderer-xphb", "label": "Feywild Gifts",
        "optional": True,  # RPF: a cosmetic table pick; an unpicked card does not block export
        "quotes": ("You also possess a fey blessing. Choose it from the Feywild Gifts table or determine it randomly.",),
        "options": {
            "gift-1": {"name": "Illusory butterflies flutter around you while you take a Short or Long Rest.", "summary": "Illusory butterflies flutter around you while you take a Short or Long Rest.",
                       "quote": "1 | Illusory butterflies flutter around you while you take a Short or Long Rest."},
            "gift-2": {"name": "Flowers bloom from your hair each dawn.", "summary": "Flowers bloom from your hair each dawn.",
                       "quote": "2 | Flowers bloom from your hair each dawn."},
            "gift-3": {"name": "You faintly smell of cinnamon, lavender, nutmeg, or another comforting herb or spice.", "summary": "You faintly smell of cinnamon, lavender, nutmeg, or another comforting herb or spice.",
                       "quote": "3 | You faintly smell of cinnamon, lavender, nutmeg, or another comforting herb or spice."},
            "gift-4": {"name": "Your shadow dances while no one is looking directly at it.", "summary": "Your shadow dances while no one is looking directly at it.",
                       "quote": "4 | Your shadow dances while no one is looking directly at it."},
            "gift-5": {"name": "Horns or antlers sprout from your head.", "summary": "Horns or antlers sprout from your head.",
                       "quote": "5 | Horns or antlers sprout from your head."},
            "gift-6": {"name": "Your skin and hair change color each dawn.", "summary": "Your skin and hair change color each dawn.",
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


# VF7.5: natural weapons of the imported species. Keyed by the species trait id; `quote` is the sentence of the trait (the catalog
# keeps the 5etools `{@damage ...}` tags) that gives the die, the damage type and, for Constitution, the ability. The row is an
# unarmed strike ("which you can use to make unarmed strikes"), so the character is proficient; the damage adds the ability modifier
# ("+ your Strength modifier"). Read with `species_traits.rows`. The base Unarmed Strike (1 + Strength, bludgeoning) is a book rule
# (PHB p.195 / PHB 2024), not in the vendored data; each record pins its "normal" part with "instead of the bludgeoning damage".
