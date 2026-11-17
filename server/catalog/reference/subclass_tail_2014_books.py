"""2014 book subclass tails, part 1 (W8, Barbarian and Bard).

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .resource_tail_2014 import ELEMENTAL_CLEAVER_DICE_2014, MANTLE_OF_INSPIRATION_THP_2014, PERFORMANCE_OF_CREATION_SIZE_2014, PSYCHIC_BLADES_DICE_2014, SPIRIT_SHIELD_DICE_2014, STORM_AURA_DESERT_2014, STORM_AURA_SEA_2014, STORM_AURA_TUNDRA_2014

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
