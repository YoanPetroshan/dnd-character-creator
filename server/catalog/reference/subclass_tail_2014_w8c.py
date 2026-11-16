"""2014 book subclass tails, part 3 (W8c).

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .subclass_tail_2014_books import BOOK_TABLE_PINS_2014
from .subclass_tail_2014_w8b import BREATH_ROLLS_2014, DRAKES_BREATH_DICE_2014, DREADFUL_STRIKES_DICE_2014, ELEMENTAL_KI_CAP_2014, GATHERED_SWARM_DICE_2014, PALADIN_AURA_FEET_2014, PLANAR_WARRIOR_DICE_2014, SUBCLASS_NOTES_2014_BOOKS, SUBCLASS_TAIL_2014_BOOKS, _w8_note, _w8_res

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
