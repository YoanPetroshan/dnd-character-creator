"""2014 book subclass tails, part 4 (W8d).

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .subclass_tail_2014_books import BOOK_TABLE_PINS_2014
from .subclass_tail_2014_w8c import PORTENT_DICE_2014, SUBCLASS_NOTES_2014_BOOKS, SUBCLASS_TAIL_2014_BOOKS, TENTACLE_DICE_2014
from .subclass_tail_2014_w8b import _w8_note, _w8_res

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
