"""Class and subclass resource tails and notes under the 2014 rules (SRD classes and subclasses).

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations

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
