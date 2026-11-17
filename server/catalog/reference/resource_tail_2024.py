"""Class and subclass resource tails and notes under the 2024 rules.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

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
