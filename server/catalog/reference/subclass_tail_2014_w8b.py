"""2014 book subclass tails, part 2 (W8b).

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .subclass_tail_2014_books import ARCANE_BANISHMENT_2014, BOOK_TABLE_PINS_2014, CIRCLE_FORMS_CR_2014, CIRCLE_FORMS_LIMIT_2014, FIGHTING_SPIRIT_THP_2014, GIANTS_MIGHT_DICE_2014, HALO_OF_SPORES_DICE_2014, RUNES_KNOWN_2014, STARRY_FORM_DICE_2014, SUBCLASS_NOTES_2014_BOOKS, SUBCLASS_TAIL_2014_BOOKS
from .resource_tail_2014 import DIVINE_STRIKE_DICE_2014

BOOK_TABLE_PINS_2014.update({
    "DIVINE_STRIKE_DICE_2014": (("death-dmg-8-divine-strike", "the cleric can cause the attack to deal an extra 1d8 necrotic damage to the target"),
                                ("death-dmg-8-divine-strike", "When the cleric reaches 14th level, the extra damage increases to 2d8")),
    "ARCANE_BANISHMENT_2014": (("arcana-scag-2-channel-divinity:-arcane-abjuration",
                                "Cleric level | Banishes Creatures of CR... 5th | 1/2 or lower 8th | 1 or lower 11th | 2 or lower 14th | 3 or lower 17th | 4 or lower"),),
    "HALO_OF_SPORES_DICE_2014": (("spores-tce-2-halo-of-spores", "deal 1d4 necrotic damage to that creature"),
                                 ("spores-tce-2-halo-of-spores", "increases to 1d6 at 6th level, 1d8 at 10th level, and 1d10 at 14th level")),
    "CIRCLE_FORMS_CR_2014": (("moon-phb-2-circle-forms",
                              "Max. CR | Limitations 2nd | 1 | No flying or swimming speed 4th | 1 | No flying speed 6th | 2 | No flying speed 8th | 2 | — 9th | 3 | — 12th | 4 | — 15th | 5 | — 18th | 6 | —"),),
    "CIRCLE_FORMS_LIMIT_2014": (("moon-phb-2-circle-forms",
                                 "2nd | 1 | No flying or swimming speed 4th | 1 | No flying speed 6th | 2 | No flying speed 8th | 2 | —"),),
    "STARRY_FORM_DICE_2014": (("stars-tce-2-archer", "1d8 + your Wisdom modifier"),
                              ("stars-tce-10-twinkling-constellations", "The 1d8 of the Archer and the Chalice becomes 2d8")),
    "RUNES_KNOWN_2014": (("rune-knight-tce-3-rune-carver", "Fighter Level | Number of Runes 3rd | 2 7th | 3 10th | 4 15th | 5"),),
    "GIANTS_MIGHT_DICE_2014": (("rune-knight-tce-3-giants-might", "can deal an extra 1d6 damage to a target on a hit"),
                               ("rune-knight-tce-10-great-stature", "the extra damage you deal with your Giant's Might feature increases to 1d8"),
                               ("rune-knight-tce-18-runic-juggernaut", "the extra damage you deal with the Giant's Might feature increases to 1d10")),
    "FIGHTING_SPIRIT_THP_2014": (("samurai-xge-3-fighting-spirit", "you also gain 5 temporary hit points"),
                                 ("samurai-xge-3-fighting-spirit", "increasing to 10 at 10th level and 15 at 15th level")),
})


def _w8_res(sub, cls, feature, name, uses, recharge, note, quotes, **kw):
    return {"subclass": sub, "class": cls, "feature": feature, "name": name, "uses": uses, "recharge": recharge,
            "note": note, "quotes": tuple((feature if q[0] is None else q[0], q[1]) for q in quotes), **kw}


def _w8_note(sub, cls, target, feature, name, note, quotes, **kw):
    return {"subclass": sub, "class": cls, "target": target, "feature": feature, "name": name, "note": note,
            "quotes": tuple((feature if q[0] is None else q[0], q[1]) for q in quotes), **kw}


def _w8_cd(sub, feature, name, note, quotes, **kw):
    """A Cleric domain Channel Divinity option: a sentence on `cleric:channel-divinity`."""
    return _w8_note(sub, "cleric", "cleric:channel-divinity", feature, name, note, quotes, **kw)


def _w8_divine_strike(sub, feature, domain, damage, quote):
    """The Cleric domain Divine Strike (level 8, 2d8 from 14): extra weapon damage once on each of your turns. The id
    names the domain so it never feeds the 2024 `cleric:divine-strike` attack-row notes."""
    return _w8_res(sub, "cleric", feature, f"Divine Strike ({domain} Domain)", None, None,
                   "Once on each of your turns when you hit a creature with a weapon attack, the attack deals an extra "
                   "{strike_dice} " + damage, ((None, quote), (None, "the extra damage increases to 2d8")),
                   dice="@strike_dice", level_vars={"strike_dice": DIVINE_STRIKE_DICE_2014})


_WARD = ("a number of times equal to your Wisdom modifier", "long rest")
_FLARE_NOTE = ("Reaction: when a creature within 30 feet that you can see attacks you, impose disadvantage on the attack "
               "roll (an attacker that can't be blinded is immune)")
_DUPLICITY_NOTE = ("Invoke Duplicity (action): create an illusory duplicate of yourself in an unoccupied space within 30 "
                   "feet for 1 minute (concentration); a bonus action moves it up to 30 feet, within 120 feet of you; you "
                   "can cast spells from its space and have advantage on attack rolls against a creature that can see it "
                   "when you and the duplicate are both within 5 feet of it")
_DUPLICITY_QUOTES = ((None, "As an action, you create a perfect illusion of yourself that lasts for 1 minute, or until you lose your concentration"),
                     (None, "you can move the illusion up to 30 feet to a space you can see"),
                     (None, "it must remain within 120 feet of you"),
                     (None, "you have advantage on attack rolls against that creature"))
_CLOAK_NOTE = "Cloak of Shadows (action): become invisible until the end of your next turn; you become visible if you attack or cast a spell"
_CLOAK_QUOTE = "As an action, you become invisible until the end of your next turn. You become visible if you attack or cast a spell."
_IMPROVED_DUPLICITY = "Improved Duplicity: up to four duplicates; a bonus action moves any number of them up to 30 feet each, within 120 feet of you"
_ID_QUOTES = "you can create up to four duplicates of yourself, instead of one, when you use Invoke Duplicity"
_PLUS10_BLESSING = ("{name} (reaction, 30 feet): spend a Channel Divinity use to give a creature making {rolls} a +10 bonus "
                    "to the roll, chosen after you see it and before the DM says whether it succeeds or fails")

_W8B_TAIL: tuple[dict, ...] = (
    # ---- Cleric: Ambition Domain (PSA)
    _w8_res("ambition-psa", "cleric", "ambition-psa-1-warding-flare", "Warding Flare", "@wis_min1", "long", _FLARE_NOTE,
            ((None, "you can use your reaction to impose disadvantage on the attack roll"), (None, _WARD[0] + " (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    # ---- Cleric: Death Domain (DMG)
    _w8_divine_strike("death-dmg", "death-dmg-8-divine-strike", "Death", "necrotic damage",
                      "the cleric can cause the attack to deal an extra 1d8 necrotic damage to the target"),
    # ---- Cleric: Forge Domain (XGE)
    _w8_res("forge-xge", "cleric", "forge-xge-1-blessing-of-the-forge", "Blessing of the Forge", 1, "long",
            "At the end of a long rest, touch one nonmagical suit of armor or simple or martial weapon: until the end of "
            "your next long rest (or your death) it is magical, +1 AC (armor) or +1 to attack and damage rolls (weapon)",
            ((None, "the object becomes a magic item, granting a +1 bonus to AC if it's armor or a +1 bonus to attack and damage rolls if it's a weapon"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    _w8_divine_strike("forge-xge", "forge-xge-8-divine-strike", "Forge", "fire damage",
                      "you can cause the attack to deal an extra 1d8 fire damage to the target"),
    # ---- Cleric: Grave Domain (XGE)
    _w8_res("grave-xge", "cleric", "grave-xge-1-eyes-of-the-grave", "Eyes of the Grave", "@wis_min1", "long",
            "Action: until the end of your next turn you know the location of any undead within 60 feet of you that isn't "
            "behind cover or protected from divination magic",
            ((None, "you know the location of any undead within 60 feet of you that isn't behind Cover"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_res("grave-xge", "cleric", "grave-xge-6-sentinel-at-deaths-door", "Sentinel at Death's Door", "@wis_min1", "long",
            "Reaction: when you or a creature you can see within 30 feet suffers a critical hit, turn it into a normal "
            "hit (effects triggered by a critical hit are canceled)",
            ((None, "when you or a creature you can see within 30 feet of you suffers a critical hit"),
             (None, "you can turn that hit into a normal hit"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"))),
    _w8_res("grave-xge", "cleric", "grave-xge-17-keeper-of-souls", "Keeper of Souls", None, None,
            "When an enemy you can see dies within 60 feet, you or one creature of your choice within 60 feet regains hit "
            "points equal to the enemy's number of Hit Dice (not while you are incapacitated); once until the start of "
            "your next turn",
            ((None, "regains hit points equal to the enemy's number of Hit Dice"),
             (None, "Once you use it, you can't do so again until the start of your next turn"))),
    # ---- Cleric: Knowledge Domain (PHB and PSA)
    *[_w8_res(sub, "cleric", f"{sub}-17-visions-of-the-past", "Visions of the Past", 1, "short-or-long",
              "Meditate for at least 1 minute (concentration) for up to your Wisdom score in minutes: Object Reading "
              "(the object's previous owners, within a number of days equal to your Wisdom score, 1 more minute per "
              "owner) or Area Reading (recent events in a room, street or similar space up to a 50-foot cube, going "
              "back a number of days equal to your Wisdom score)",
              ((None, "You can meditate in this way for a number of minutes equal to your Wisdom score"),
               (None, "up to a 50-foot cube"),
               (None, "Once you use this feature, you can't use it again until you finish a short or long rest")))
      for sub in ("knowledge-phb", "knowledge-psa")],
    # ---- Cleric: Light Domain (PHB)
    _w8_res("light-phb", "cleric", "light-phb-1-warding-flare", "Warding Flare", "@wis_min1", "long", _FLARE_NOTE,
            ((None, "you can use your reaction to impose disadvantage on the attack roll"), (None, _WARD[0] + " (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"),
             ("light-phb-6-improved-flare", "you can also use your Warding Flare feature when a creature that you can see within 30 feet of you attacks a creature other than you")),
            extras=(("light-phb-6-improved-flare", "Improved Flare: you can also use it when a creature you can see within 30 "
                     "feet attacks a creature other than you"),)),
    _w8_res("light-phb", "cleric", "light-phb-17-corona-of-light", "Corona of Light", None, None,
            "Action: an aura of sunlight for 1 minute or until you dismiss it with another action; bright light in a "
            "60-foot radius and dim light 30 feet beyond; your enemies in the bright light have disadvantage on saving "
            "throws against spells that deal fire or radiant damage",
            ((None, "an aura of sunlight that lasts for 1 minute or until you dismiss it using another action"),
             (None, "You emit bright light in a 60-foot radius and dim light 30 feet beyond that"),
             (None, "disadvantage on saving throws against any spell that deals fire or radiant damage"))),
    # ---- Cleric: Nature Domain (PHB)
    _w8_res("nature-phb", "cleric", "nature-phb-6-dampen-elements", "Dampen Elements", None, None,
            "Reaction: when you or a creature within 30 feet takes acid, cold, fire, lightning or thunder damage, grant it "
            "resistance to that instance of the damage",
            ((None, "when you or a creature within 30 feet of you takes acid, cold, fire, lightning, or thunder damage"),
             (None, "you can use your reaction to grant resistance to the creature against that instance of the damage"))),
    _w8_divine_strike("nature-phb", "nature-phb-8-divine-strike", "Nature", "cold, fire or lightning damage (your choice)",
                      "an extra 1d8 cold, fire, or lightning damage (your choice) to the target"),
    # ---- Cleric: Order Domain (TCE)
    _w8_res("order-tce", "cleric", "order-tce-6-embodiment-of-the-law", "Embodiment of the Law", "@wis_min1", "long",
            "If you cast an enchantment spell of 1st level or higher whose casting time is 1 action, change the casting "
            "time to 1 bonus action for that casting",
            ((None, "you can change the spell's casting time to 1 bonus action for this casting"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "you regain all expended uses of it when you finish a long rest"))),
    _w8_divine_strike("order-tce", "order-tce-8-divine-strike", "Order", "psychic damage",
                      "an extra 1d8 psychic damage to the target"),
    _w8_res("order-tce", "cleric", "order-tce-17-orders-wrath", "Order's Wrath", None, None,
            "If you deal your Divine Strike damage to a creature on your turn, you can curse it until the start of your "
            "next turn: the next time an ally hits it, it takes an extra 2d8 psychic damage and the curse ends; once per turn",
            ((None, "you can curse that creature until the start of your next turn"),
             (None, "the target also takes 2d8 psychic damage"),
             (None, "You can curse a creature in this way only once per turn"))),
    # ---- Cleric: Peace Domain (TCE)
    _w8_res("peace-tce", "cleric", "peace-tce-1-emboldening-bond", "Emboldening Bond", "@pb", "long",
            "Action: bond up to {pb} willing creatures within 30 feet (proficiency bonus; you can be one) for 10 minutes or "
            "until you use this feature again; while a bonded creature is within 30 feet of another, it can add a d4 to "
            "an attack roll, ability check or saving throw (once per turn)",
            ((None, "a number of willing creatures within 30 feet of you (this can include yourself) equal to your proficiency bonus"),
             (None, "for 10 minutes or until you use this feature again"),
             (None, "roll a d4 and add the number rolled"),
             (None, "no more than once per turn"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Cleric: Solidarity Domain (PSA)
    _w8_res("solidarity-psa", "cleric", "solidarity-psa-1-solidaritys-action", "Solidarity's Action", "@wis_min1", "long",
            "When you take the Help action to aid an ally's attack, you can make one weapon attack as a bonus action",
            ((None, "you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (minimum of once)"),
             (None, "You regain expended uses when you finish a long rest"))),
    _w8_divine_strike("solidarity-psa", "solidarity-psa-8-divine-strike", "Solidarity", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Strength Domain (PSA)
    _w8_divine_strike("strength-psa", "strength-psa-8-divine-strike", "Strength", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Tempest Domain (PHB)
    _w8_res("tempest-phb", "cleric", "tempest-phb-1-wrath-of-the-storm", "Wrath of the Storm", "@wis_min1", "long",
            "Reaction: when a creature within 5 feet that you can see hits you with an attack, it makes a Dexterity "
            "saving throw, taking 2d8 lightning or thunder damage (your choice) on a failure, half as much on a success",
            ((None, "When a creature within 5 feet of you that you can see hits you with an attack"),
             (None, "The creature takes 2d8 lightning or thunder damage (your choice) on a failed saving throw, and half as much damage on a successful one"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"))),
    _w8_divine_strike("tempest-phb", "tempest-phb-8-divine-strike", "Tempest", "thunder damage",
                      "an extra 1d8 thunder damage to the target"),
    # ---- Cleric: Trickery Domain (PHB)
    _w8_divine_strike("trickery-phb", "trickery-phb-8-divine-strike", "Trickery", "poison damage",
                      "an extra 1d8 poison damage to the target"),
    # ---- Cleric: Twilight Domain (TCE)
    _w8_res("twilight-tce", "cleric", "twilight-tce-1-eyes-of-night", "Eyes of Night", 1, "long",
            "Darkvision out to 300 feet (dim light as bright, darkness as dim); action: share it with up to {wis_min1} "
            "willing creature(s) within 10 feet (Wisdom modifier, minimum 1) for 1 hour; share it again before a long rest "
            "by expending a spell slot of any level",
            ((None, "You have darkvision out to a range of 300 feet"),
             (None, "up to a number of creatures equal to your Wisdom modifier (minimum of one creature)"),
             (None, "The shared darkvision lasts for 1 hour"),
             (None, "unless you expend a spell slot of any level to share it again"))),
    _w8_res("twilight-tce", "cleric", "twilight-tce-6-steps-of-night", "Steps of Night", "@pb", "long",
            "Bonus action when you are in dim light or darkness: a flying speed equal to your walking speed for 1 minute",
            ((None, "As a bonus action when you are in dim light or darkness, you can magically give yourself a flying speed equal to your walking speed for 1 minute"),
             (None, "You can use this bonus action a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("twilight-tce", "twilight-tce-8-divine-strike", "Twilight", "radiant damage",
                      "the attack to deal an extra 1d8 radiant damage"),
    # ---- Cleric: War Domain (PHB)
    _w8_res("war-phb", "cleric", "war-phb-1-war-priest", "War Priest", "@wis_min1", "long",
            "When you use the Attack action, you can make one weapon attack as a bonus action",
            ((None, "When you use the Attack action, you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("war-phb", "war-phb-8-divine-strike", "War", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    # ---- Cleric: Zeal Domain (PSA)
    _w8_res("zeal-psa", "cleric", "zeal-psa-1-priest-of-zeal", "Priest of Zeal", "@wis_min1", "long",
            "When you use the Attack action, you can make one weapon attack as a bonus action",
            ((None, "When you use the Attack action, you can make one weapon attack as a bonus action"),
             (None, "You can use this feature a number of times equal to your Wisdom modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"))),
    _w8_divine_strike("zeal-psa", "zeal-psa-8-divine-strike", "Zeal", "damage of the weapon's type",
                      "an extra 1d8 damage of the same type dealt by the weapon to the target"),
    _w8_res("zeal-psa", "cleric", "zeal-psa-17-blaze-of-glory", "Blaze of Glory", 1, "long",
            "When an attacker you can see reduces you to 0 hit points, use your reaction to move up to your speed toward it "
            "and make one melee weapon attack with advantage; a hit deals an extra 5d10 fire damage and an extra 5d10 damage "
            "of the weapon's type; then you fall unconscious and make death saving throws",
            ((None, "you can use your reaction to move up to your speed toward the attacker and make one melee weapon attack against it"),
             (None, "You make this attack with advantage"),
             (None, "an extra 5d10 fire damage and an extra 5d10 damage of the weapon's type"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of Dreams (XGE)
    _w8_res("dreams-xge", "druid", "dreams-xge-2-balm-of-the-summer-court", "Balm of the Summer Court", "@level", "long",
            "Bonus action: choose a creature you can see within 120 feet and spend up to {half_level} of your d6s (half your "
            "Druid level or less); it regains the total rolled in hit points and 1 temporary hit point per die spent",
            ((None, "a pool of fey energy represented by a number of d6s equal to your druid level"),
             (None, "spend a number of those dice equal to half your druid level or less"),
             (None, "The target also gains 1 temporary hit point per die spent"),
             (None, "You regain all expended dice when you finish a long rest")), die="d6"),
    _w8_res("dreams-xge", "druid", "dreams-xge-10-hidden-paths", "Hidden Paths", "@wis_min1", "long",
            "Bonus action: teleport up to 60 feet to an unoccupied space you can see; or action: teleport one willing "
            "creature you touch up to 30 feet",
            ((None, "you can teleport up to 60 feet to an unoccupied space you can see"),
             (None, "teleport one willing creature you touch up to 30 feet"),
             (None, "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("dreams-xge", "druid", "dreams-xge-14-walker-in-dreams", "Walker in Dreams", 1, "long",
            "When you finish a short rest, cast dream (you as the messenger), scrying or teleportation circle without a "
            "spell slot or components (the portal leads to where you last finished a long rest on your plane)",
            ((None, "When you finish a short rest, you can cast one of the following spells, without expending a spell slot or requiring material components: dream (with you as the messenger), scrying, or teleportation circle"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of the Shepherd (XGE)
    _w8_res("shepherd-xge", "druid", "shepherd-xge-2-spirit-totem", "Spirit Totem", 1, "short-or-long",
            "Bonus action: summon a spirit to a point within 60 feet (30-foot aura; a bonus action moves it up to 60 feet) "
            "for 1 minute. Bear: creatures of your choice in the aura gain {five_plus_level} temporary hit points (5 + "
            "Druid level) and you and your allies have advantage on Strength checks and saving throws there. Hawk: "
            "reaction to give advantage to an attack roll against a target in the aura. Unicorn: when you cast a healing "
            "spell with a slot, each creature of your choice in the aura also regains {level} hit points (Druid level)",
            ((None, "you can magically summon an incorporeal spirit to a point you can see within 60 feet of you"),
             (None, "The spirit creates an aura in a 30-foot radius around that point"),
             (None, "The spirit persists for 1 minute"),
             (None, "gains temporary hit points equal to 5 + your druid level"),
             (None, "each creature of your choice in the aura also regains hit points equal to your druid level"),
             (None, "Once you use this feature, you can't use it again until you finish a short or long rest"),
             ("shepherd-xge-10-guardian-spirit", "that creature regains a number of hit points equal to half your druid level")),
            extras=(("shepherd-xge-10-guardian-spirit", "Guardian Spirit: a beast or fey you summoned or created with a spell "
                     "that ends its turn in the aura regains {half_level} hit points (half your Druid level)"),)),
    _w8_res("shepherd-xge", "druid", "shepherd-xge-14-faithful-summons", "Faithful Summons", 1, "long",
            "If you are reduced to 0 hit points or incapacitated against your will, gain the benefits of conjure animals as "
            "a 9th-level spell: four beasts of challenge rating 2 or lower appear within 20 feet and last 1 hour with no "
            "concentration",
            ((None, "It summons four beasts of your choice that are challenge rating 2 or lower"),
             (None, "The conjured beasts appear within 20 feet of you"),
             (None, "The spell lasts for 1 hour, requiring no concentration"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Druid: Circle of Spores (TCE)
    _w8_res("spores-tce", "druid", "spores-tce-2-halo-of-spores", "Halo of Spores", None, None,
            "Reaction: when a creature you can see moves into a space within 10 feet of you or starts its turn there, it "
            "takes {halo} necrotic damage unless it succeeds on a Constitution saving throw (DC {dc_wis}, your spell save DC)",
            ((None, "deal 1d4 necrotic damage to that creature unless it succeeds on a Constitution saving throw against your spell save DC"),
             (None, "a creature you can see moves into a space within 10 feet of you"),
             (None, "increases to 1d6 at 6th level, 1d8 at 10th level, and 1d10 at 14th level")),
            dice="@halo", level_vars={"halo": HALO_OF_SPORES_DICE_2014}),
    _w8_res("spores-tce", "druid", "spores-tce-6-fungal-infestation", "Fungal Infestation", "@wis_min1", "long",
            "Reaction: a Small or Medium beast or humanoid that dies within 10 feet of you stands up with 1 hit point as a "
            "zombie that obeys your mental commands (Attack action only) for 1 hour",
            ((None, "If a beast or a humanoid that is Small or Medium dies within 10 feet of you, you can use your reaction to animate it, causing it to stand up immediately with 1 hit point"),
             (None, "It remains animate for 1 hour"),
             (None, "a number of times equal to your Wisdom modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    # ---- Druid: Circle of the Stars (TCE)
    _w8_res("stars-tce", "druid", "stars-tce-2-star-map", "Star Map", "@pb", "long",
            "While holding your star map you know the guidance cantrip and have guiding bolt prepared (a druid spell that "
            "doesn't count against your prepared spells); cast guiding bolt without a spell slot; a replacement map takes "
            "a 1-hour ceremony during a short or long rest",
            ((None, "You can cast guiding bolt without expending a spell slot"),
             (None, "a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"),
             (None, "you can perform a 1-hour ceremony to magically create a replacement"))),
    _w8_res("stars-tce", "druid", "stars-tce-6-cosmic-omen", "Cosmic Omen", "@pb", "long",
            "After each long rest, consult your star map and roll a die: even is Weal, odd is Woe until your next long "
            "rest. Reaction: when a creature you can see within 30 feet is about to make an attack roll, saving throw or "
            "ability check, roll a d6 and add it (Weal) or subtract it (Woe)",
            ((None, "roll a d6 and add the number rolled to the total"),
             (None, "roll a d6 and subtract the number rolled from the total"),
             (None, "Whenever a creature you can see within 30 feet of you is about to make an attack roll, a saving throw, or an ability check"),
             (None, "You can use this reaction a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Druid: Circle of Wildfire (TCE)
    _w8_res("wildfire-tce", "druid", "wildfire-tce-10-cauterizing-flames", "Cauterizing Flames", "@pb", "long",
            "When a Small or larger creature dies within 30 feet of you or your wildfire spirit, a spectral flame lasts 1 "
            "minute in its space; reaction when a creature you can see enters it: heal that creature or deal it fire "
            "damage of 2d10{wis:+d} (2d10 + Wisdom modifier)",
            ((None, "dies within 30 feet of you or your wildfire spirit"),
             (None, "flickers there for 1 minute"),
             (None, "The healing or damage equals 2d10 + your Wisdom modifier"),
             (None, "You can use this reaction a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    _w8_res("wildfire-tce", "druid", "wildfire-tce-14-blazing-revival", "Blazing Revival", 1, "long",
            "If your wildfire spirit is within 120 feet when you are reduced to 0 hit points, drop it to 0 hit points: you "
            "regain half your hit points and rise to your feet",
            ((None, "If the spirit is within 120 feet of you when you are reduced to 0 hit points"),
             (None, "You then regain half your hit points"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
    # ---- Fighter: Cavalier (XGE)
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-3-unwavering-mark", "Unwavering Mark", "@str_min1", "long",
            "When you hit a creature with a melee weapon attack, mark it until the end of your next turn: while within 5 "
            "feet of you it has disadvantage on attack rolls that don't target you; if it damages anyone else, on your next "
            "turn you can make a special melee weapon attack against it as a bonus action with advantage, dealing extra "
            "damage equal to half your Fighter level ({half_level}); the uses count these special attacks",
            ((None, "you can mark the creature until the end of your next turn"),
             (None, "the attack's weapon deals extra damage to the target equal to half your fighter level"),
             (None, "a number of times equal to your Strength modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-7-warding-maneuver", "Warding Maneuver", "@con_min1", "long",
            "Reaction: when you or a creature you can see within 5 feet is hit by an attack and you wield a melee weapon or "
            "a shield, roll 1d8 and add it to the target's AC against that attack; if the attack still hits, the target has "
            "resistance to its damage",
            ((None, "you can roll 1d8 as a reaction if you're wielding a melee weapon or a shield"),
             (None, "the target has resistance against the attack's damage"),
             (None, "a number of times equal to your Constitution modifier (minimum of once), and you regain all expended uses of it when you finish a long rest"))),
    _w8_res("cavalier-xge", "fighter", "cavalier-xge-15-ferocious-charger", "Ferocious Charger", None, None,
            "If you move at least 10 feet in a straight line right before hitting a creature with an attack, it makes a "
            "Strength saving throw (DC {dc_str}) or is knocked prone; once on each of your turns",
            ((None, "that target must succeed on a Strength saving throw (DC 8 + your proficiency bonus + your Strength modifier) or be knocked prone"),
             (None, "You can use this feature only once on each of your turns"))),
    # ---- Fighter: Echo Knight (EGW)
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-3-manifest-echo", "Manifest Echo", None, None,
            "Bonus action: manifest an echo in an unoccupied space you can see within 15 feet (AC {echo_ac}, 1 hit point, "
            "immune to all conditions, uses your saving throw bonuses); you can move it up to 30 feet without an action "
            "(destroyed if it ends your turn more than 30 feet from you); bonus action: swap places with it at a cost of "
            "15 feet of your movement; your attacks can originate from its space; opportunity attacks can too",
            ((None, "an echo of yourself in an unoccupied space you can see within 15 feet of you"),
             (None, "Your echo has AC 14 + your proficiency bonus, 1 hit point, and immunity to all conditions"),
             (None, "move up to 30 feet in any direction"),
             (None, "at a cost of 15 feet of your movement"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-3-unleash-incarnation", "Unleash Incarnation", "@con_min1", "long",
            "Whenever you take the Attack action, make one additional melee attack from the echo's position",
            ((None, "you can make one additional melee attack from the echo's position"),
             (None, "You can use this feature a number of times equal to your Constitution modifier (a minimum of once)"),
             (None, "You regain all expended uses when you finish a long rest"),
             ("echo-knight-egw-18-legion-of-one", "create two echoes with your Manifest Echo feature"),
             ("echo-knight-egw-18-legion-of-one", "you regain one use of that feature")),
            extras=(("echo-knight-egw-18-legion-of-one", "Legion of One: two echoes can coexist; when you roll initiative with "
                     "no uses left you regain one use"),)),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-7-echo-avatar", "Echo Avatar", None, None,
            "Action: see through your echo's eyes and hear through its ears for up to 10 minutes (you are deafened and "
            "blinded); the echo can be up to 1,000 feet from you without being destroyed",
            ((None, "You can sustain this effect for up to 10 minutes"),
             (None, "it can be up to 1,000 feet away from you without being destroyed"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-10-shadow-martyr", "Shadow Martyr", 1, "short-or-long",
            "Reaction, before an attack roll against another creature you can see: teleport your echo to an unoccupied "
            "space within 5 feet of the target; the attack is made against your echo",
            ((None, "teleport the echo to an unoccupied space within 5 feet of the targeted creature"),
             (None, "Once you use this feature, you can't use it again until you finish a short or long rest"))),
    _w8_res("echo-knight-egw", "fighter", "echo-knight-egw-15-reclaim-potential", "Reclaim Potential", "@con_min1", "long",
            "When an echo of yours is destroyed by taking damage, gain 2d6{con:+d} temporary hit points (2d6 + Constitution "
            "modifier) if you have none",
            ((None, "a number of temporary hit points equal to 2d6 + your Constitution modifier, provided you don't already have temporary hit points"),
             (None, "You can use this feature a number of times equal to your Constitution modifier (a minimum of once)"))),
    # ---- Fighter: Rune Knight (TCE)
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-3-rune-carver", "Rune Carver", None, None,
            "After a long rest, touch up to {runes} objects (the runes you know) and inscribe a different rune on each; a "
            "rune stays until your next long rest; Rune Magic save DC {dc_con}",
            ((None, "Whenever you finish a long rest, you can touch a number of objects equal to the number of runes you know"),
             (None, "your Rune Magic save DC equals 8 + your proficiency bonus + your Constitution modifier"),
             (None, "Fighter Level | Number of Runes 3rd | 2 7th | 3 10th | 4 15th | 5"),
             ("rune-knight-tce-15-master-of-runes", "You can invoke each rune you know from your Rune Carver feature twice, rather than once, and you regain all expended uses when you finish a short or long rest")),
            level_vars={"runes": RUNES_KNOWN_2014},
            extras=(("rune-knight-tce-15-master-of-runes", "Master of Runes: you can invoke each rune you know twice, rather "
                     "than once, and regain all expended uses on a short or long rest"),)),
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-3-giants-might", "Giant's Might", "@pb", "long",
            "Bonus action, 1 minute: if smaller than Large you become Large; advantage on Strength checks and Strength "
            "saving throws; once on each of your turns one weapon or unarmed attack that hits deals an extra {gm_dice} damage",
            ((None, "which last for 1 minute"),
             (None, "If you are smaller than Large, you become Large"),
             (None, "You have advantage on Strength checks and Strength saving throws"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses of it when you finish a long rest"),
             ("rune-knight-tce-18-runic-juggernaut", "your size can increase to Huge, and while you are that size, your reach increases by 5 feet")),
            dice="@gm_dice", level_vars={"gm_dice": GIANTS_MIGHT_DICE_2014},
            extras=(("rune-knight-tce-18-runic-juggernaut", "Runic Juggernaut: your size can increase to Huge, and while you "
                     "are Huge your reach increases by 5 feet"),)),
    _w8_res("rune-knight-tce", "fighter", "rune-knight-tce-7-runic-shield", "Runic Shield", "@pb", "long",
            "Reaction: when another creature you can see within 60 feet is hit by an attack roll, force the attacker to "
            "reroll the d20 and use the new roll",
            ((None, "When another creature you can see within 60 feet of you is hit by an attack roll, you can use your reaction to force the attacker to reroll the d20 and use the new roll"),
             (None, "You can use this feature a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest"))),
    # ---- Fighter: Samurai (XGE)
    _w8_res("samurai-xge", "fighter", "samurai-xge-3-fighting-spirit", "Fighting Spirit", 3, "long",
            "Bonus action: advantage on weapon attack rolls until the end of the current turn and {fs_thp} temporary hit points",
            ((None, "As a bonus action on your turn, you can give yourself advantage on weapon attack rolls until the end of the current turn"),
             (None, "you also gain 5 temporary hit points"),
             (None, "increasing to 10 at 10th level and 15 at 15th level"),
             (None, "You can use this feature three times, and you regain all expended uses of it when you finish a long rest"),
             ("samurai-xge-10-tireless-spirit", "when you roll initiative and have no uses of Fighting Spirit remaining, you regain one use")),
            level_vars={"fs_thp": FIGHTING_SPIRIT_THP_2014},
            extras=(("samurai-xge-10-tireless-spirit", "Tireless Spirit: when you roll initiative and have no uses left, you "
                     "regain one use"),)),
    _w8_res("samurai-xge", "fighter", "samurai-xge-18-strength-before-death", "Strength before Death", 1, "long",
            "If damage reduces you to 0 hit points without killing you outright, use your reaction to delay falling "
            "unconscious and take an extra turn immediately (death saving throws still apply)",
            ((None, "you can use your reaction to delay falling unconscious, and you can immediately take an extra turn"),
             (None, "Once you use this feature, you can't use it again until you finish a long rest"))),
)

_W8B_NOTES: tuple[dict, ...] = (
    # ---- Cleric Channel Divinity options (sentences on `cleric:channel-divinity`)
    _w8_cd("ambition-psa", "ambition-psa-2-channel-divinity:-invoke-duplicity", "Invoke Duplicity", _DUPLICITY_NOTE,
           _DUPLICITY_QUOTES + (("ambition-psa-17-improved-duplicity", _ID_QUOTES),),
           extras=(("ambition-psa-17-improved-duplicity", _IMPROVED_DUPLICITY),)),
    _w8_cd("ambition-psa", "ambition-psa-6-channel-divinity:-cloak-of-shadows", "Cloak of Shadows", _CLOAK_NOTE, ((None, _CLOAK_QUOTE),)),
    _w8_cd("arcana-scag", "arcana-scag-2-channel-divinity:-arcane-abjuration", "Arcane Abjuration",
           "Arcane Abjuration (action, 30 feet): one celestial, elemental, fey or fiend that can see or hear you makes a "
           "Wisdom saving throw or is turned for 1 minute or until it takes damage{banish}",
           ((None, "one celestial, elemental, fey, or fiend of your choice that is within 30 feet of you must make a Wisdom saving throw"),
            (None, "it is turned for 1 minute or until it takes any damage"),
            (None, "the creature is banished for 1 minute (as in the banishment spell, no concentration required) if it isn't on its plane of origin")),
           level_vars={"banish": ARCANE_BANISHMENT_2014}),
    _w8_cd("death-dmg", "death-dmg-2-channel-divinity:-touch-of-death", "Touch of Death",
           "Touch of Death: when you hit a creature with a melee attack, spend a Channel Divinity use to deal extra "
           "necrotic damage equal to {five_plus_twice_level} (5 + twice your Cleric level)",
           ((None, "deal extra necrotic damage to the target"), (None, "The damage equals 5 + twice his or her cleric level"))),
    _w8_cd("forge-xge", "forge-xge-2-channel-divinity:-artisans-blessing", "Artisan's Blessing",
           "Artisan's Blessing (1-hour ritual): craft a nonmagical item that includes metal and is worth no more than 100 "
           "gp (a simple or martial weapon, a suit of armor, ten pieces of ammunition, a set of tools or another metal "
           "object), paid for with metal of equal value that you lay out",
           ((None, "You conduct an hour-long ritual"), (None, "worth no more than 100 gp"))),
    _w8_cd("grave-xge", "grave-xge-2-channel-divinity:-path-to-the-grave", "Path to the Grave",
           "Path to the Grave (action, 30 feet): curse a creature you can see until the end of your next turn; the next "
           "attack by you or an ally that hits it makes it vulnerable to all of that attack's damage, then the curse ends",
           ((None, "you choose one creature you can see within 30 feet of you, cursing it until the end of your next turn"),
            (None, "the creature has vulnerability to all of that attack's damage"))),
    *[_w8_cd(sub, f"{sub}-2-channel-divinity:-knowledge-of-the-ages", "Knowledge of the Ages",
             "Knowledge of the Ages (action): choose one skill or tool; for 10 minutes you have proficiency with it",
             ((None, "For 10 minutes, you have proficiency with the chosen skill or tool"),))
      for sub in ("knowledge-phb", "knowledge-psa")],
    *[_w8_cd(sub, f"{sub}-6-channel-divinity:-read-thoughts", "Read Thoughts",
             "Read Thoughts (action, 60 feet): a creature you can see makes a Wisdom saving throw (on a success you can't "
             "use this on it again until a long rest); on a failure you read its surface thoughts within 60 feet for 1 "
             "minute and can use your action to cast suggestion on it without a spell slot (it automatically fails the save)",
             ((None, "choose one creature that you can see within 60 feet of you"),
              (None, "This effect lasts for 1 minute"),
              (None, "cast the suggestion spell on the creature without expending a spell slot"),
              (None, "you can't use this feature on it again until you finish a long rest")))
      for sub in ("knowledge-phb", "knowledge-psa")],
    _w8_cd("light-phb", "light-phb-2-channel-divinity:-radiance-of-the-dawn", "Radiance of the Dawn",
           "Radiance of the Dawn (action): dispel magical darkness within 30 feet; each hostile creature within 30 feet "
           "makes a Constitution saving throw, taking radiant damage of 2d10 + {level} (2d10 + Cleric level) on a failure, "
           "half on a success; a creature with cover from you is unaffected",
           ((None, "any magical darkness within 30 feet of you is dispelled"),
            (None, "radiant damage equal to 2d10 + your cleric level on a failed saving throw, and half as much damage on a successful one"),
            (None, "A creature that has Cover from you is not affected"))),
    _w8_cd("nature-phb", "nature-phb-2-channel-divinity:-charm-animals-and-plants", "Charm Animals and Plants",
           "Charm Animals and Plants (action): each beast or plant creature that can see you within 30 feet makes a Wisdom "
           "saving throw or is charmed by you for 1 minute or until it takes damage",
           ((None, "Each beast or plant creature that can see you within 30 feet of you must make a Wisdom saving throw"),
            (None, "it is charmed by you for 1 minute or until it takes damage"))),
    _w8_cd("order-tce", "order-tce-2-channel-divinity:-orders-demand", "Order's Demand",
           "Order's Demand (action, 30 feet): each creature of your choice that can see or hear you makes a Wisdom saving "
           "throw or is charmed by you until the end of your next turn or until it takes damage; charmed creatures that fail "
           "can be made to drop what they hold",
           ((None, "each creature of your choice that can see or hear you within 30 feet of you must succeed on a Wisdom saving throw or be charmed by you until the end of your next turn or until the charmed creature takes any damage"),
            (None, "You can also cause any of the charmed creatures to drop what they are holding when they fail the saving throw"))),
    _w8_cd("peace-tce", "peace-tce-2-channel-divinity:-balm-of-peace", "Balm of Peace",
           "Balm of Peace (action): move up to your speed without provoking opportunity attacks; each creature you move "
           "within 5 feet of can regain 2d6 {wis:+d} hit points (minimum 1 hit point in total), once per use",
           ((None, "restore a number of hit points to that creature equal to 2d6 + your Wisdom modifier (minimum of 1 hit point)"),
            (None, "move up to your speed, without provoking opportunity attacks"),
            (None, "A creature can receive this healing only once whenever you take this action"))),
    _w8_cd("solidarity-psa", "solidarity-psa-2-channel-divinity:-preserve-life", "Preserve Life",
           "Preserve Life (action, 30 feet): restore up to {five_level} hit points (5 x Cleric level) divided among "
           "creatures you choose, none above half its hit point maximum; not on an undead or a construct",
           ((None, "restore a number of hit points equal to five times your cleric level"),
            (None, "This feature can restore a creature to no more than half of its hit point maximum"),
            (None, "You can't use this feature on an undead or a construct"))),
    _w8_cd("solidarity-psa", "solidarity-psa-6-oketras-blessing", "Oketra's Blessing",
           _PLUS10_BLESSING.replace("{name}", "Oketra's Blessing").replace("{rolls}", "an attack roll"),
           ((None, "when a creature within 30 feet of you makes an attack roll, you can use your reaction to grant that creature a +10 bonus to the roll, using your Channel Divinity"),)),
    _w8_cd("strength-psa", "strength-psa-2-channel-divinity:-feat-of-strength", "Feat of Strength",
           "Feat of Strength: spend a Channel Divinity use to gain a +10 bonus to an attack roll, ability check or saving "
           "throw using Strength, chosen after you see the roll and before the DM says whether it succeeds or fails",
           ((None, "you can use your Channel Divinity to gain a +10 bonus to the roll"),)),
    _w8_cd("strength-psa", "strength-psa-6-rhonass-blessing", "Rhonas's Blessing",
           _PLUS10_BLESSING.replace("{name}", "Rhonas's Blessing").replace("{rolls}", "an attack roll, ability check or saving throw using Strength"),
           ((None, "when a creature within 30 feet of you makes an attack roll, ability check, or saving throw using Strength, you can use your reaction to grant that creature a +10 bonus to the roll"),)),
    _w8_cd("tempest-phb", "tempest-phb-2-channel-divinity:-destructive-wrath", "Destructive Wrath",
           "Destructive Wrath: when you roll lightning or thunder damage, spend a Channel Divinity use to deal maximum "
           "damage instead of rolling",
           ((None, "you can use your Channel Divinity to deal maximum damage, instead of rolling"),)),
    _w8_cd("trickery-phb", "trickery-phb-2-channel-divinity:-invoke-duplicity", "Invoke Duplicity", _DUPLICITY_NOTE,
           _DUPLICITY_QUOTES + (("trickery-phb-17-improved-duplicity", _ID_QUOTES),),
           extras=(("trickery-phb-17-improved-duplicity", _IMPROVED_DUPLICITY),)),
    _w8_cd("trickery-phb", "trickery-phb-6-channel-divinity:-cloak-of-shadows", "Cloak of Shadows", _CLOAK_NOTE, ((None, _CLOAK_QUOTE),)),
    _w8_cd("twilight-tce", "twilight-tce-2-channel-divinity:-twilight-sanctuary", "Twilight Sanctuary",
           "Twilight Sanctuary (action, 1 minute): a 30-foot-radius sphere of dim twilight centered on you; whenever a "
           "creature (you included) ends its turn in it, grant it 1d6 + {level} temporary hit points (1d6 + Cleric level) or end a "
           "charmed or frightened effect on it",
           ((None, "has a 30-foot radius"),
            (None, "it lasts for 1 minute"),
            (None, "temporary hit points equal to 1d6 plus your cleric level"))),
    _w8_cd("war-phb", "war-phb-2-channel-divinity:-guided-strike", "Guided Strike",
           "Guided Strike: when you make an attack roll, spend a Channel Divinity use to gain a +10 bonus to it, chosen "
           "after you see the roll and before the DM says whether it hits or misses",
           ((None, "you can use your Channel Divinity to gain a +10 bonus to the roll"),)),
    _w8_cd("war-phb", "war-phb-6-channel-divinity:-war-gods-blessing", "War God's Blessing",
           _PLUS10_BLESSING.replace("{name}", "War God's Blessing").replace("{rolls}", "an attack roll"),
           ((None, "when a creature within 30 feet of you makes an attack roll, you can use your reaction to grant that creature a +10 bonus to the roll, using your Channel Divinity"),)),
    _w8_cd("zeal-psa", "zeal-psa-2-channel-divinity:-consuming-fervor", "Consuming Fervor",
           "Consuming Fervor: when you roll fire or thunder damage, spend a Channel Divinity use to deal maximum damage "
           "instead of rolling",
           ((None, "When you roll fire or thunder damage, you can use your Channel Divinity to deal maximum damage instead of rolling"),)),
    # ---- Druid: sentences on Wild Shape
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-2-combat-wild-shape", "Combat Wild Shape",
             "Combat Wild Shape: use Wild Shape as a bonus action; while transformed, a bonus action and a spell slot "
             "regain 1d8 hit points per level of the slot",
             ((None, "use Wild Shape on your turn as a bonus action"),
              (None, "expend one spell slot to regain 1d8 hit points per level of the spell slot expended"))),
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-2-circle-forms", "Circle Forms",
             "Circle Forms: Wild Shape into a beast of challenge rating {moon_cr} or lower ({moon_limit}), ignoring the "
             "Max. CR column of the Beast Shapes table",
             ((None, "you can use your Wild Shape to transform into a beast with a challenge rating as high as 1 (you ignore the Max. CR column of the Beast Shapes table"),
              (None, "challenge rating as high as your druid level divided by 3, rounded down")),
             level_vars={"moon_cr": CIRCLE_FORMS_CR_2014, "moon_limit": CIRCLE_FORMS_LIMIT_2014}),
    _w8_note("moon-phb", "druid", "druid:wild-shape", "moon-phb-10-elemental-wild-shape", "Elemental Wild Shape",
             "Elemental Wild Shape: expend two uses of Wild Shape at the same time to become an air, earth, fire or water "
             "elemental",
             ((None, "you can expend two uses of Wild Shape at the same time to transform into an air elemental, an earth elemental, a fire elemental, or a water elemental"),)),
    _w8_note("spores-tce", "druid", "druid:wild-shape", "spores-tce-2-symbiotic-entity", "Symbiotic Entity",
             "Symbiotic Entity (action): expend a use of Wild Shape to awaken your spores instead of transforming and gain "
             "{four_level} temporary hit points (4 per Druid level); for 10 minutes, until they are gone or you Wild Shape: "
             "your Halo of Spores damage die is rolled twice and your melee weapon hits deal an extra 1d6 necrotic damage",
             ((None, "you can expend a use of your Wild Shape feature to awaken those spores, rather than transforming into a beast form, and you gain 4 temporary hit points for each level you have in this class"),
              (None, "These benefits last for 10 minutes"),
              (None, "Your melee weapon attacks deal an extra 1d6 necrotic damage to any target they hit"),
              (None, "roll the damage die a second time and add it to the total"),
              ("spores-tce-10-spreading-spores", "you can hurl spores up to 30 feet away, where they swirl in a 10-foot cube for 1 minute"),
              ("spores-tce-10-spreading-spores", "takes your Halo of Spores damage, unless the creature succeeds on a Constitution saving throw against your spell save DC")),
             extras=(("spores-tce-10-spreading-spores", "Spreading Spores (bonus action while Symbiotic Entity is active): hurl "
                      "spores up to 30 feet into a 10-foot cube for 1 minute; a creature that moves into it or starts its "
                      "turn there takes your Halo of Spores damage unless it passes a Constitution saving throw (DC {dc_wis})"),)),
    _w8_note("stars-tce", "druid", "druid:wild-shape", "stars-tce-2-starry-form", "Starry Form",
             "Starry Form (bonus action): expend a use of Wild Shape to take a starry form for 10 minutes (bright light in a "
             "10-foot radius, dim light 10 feet more) with one constellation: Archer (a bonus-action ranged spell attack "
             "within 60 feet, {star_dice}{wis:+d} radiant damage), Chalice (when you cast a healing spell with a slot, you or "
             "a creature within 30 feet regains {star_dice}{wis:+d} hit points) or Dragon (treat a d20 roll of 9 or lower as "
             "10 on Intelligence and Wisdom checks and concentration saves)",
             ((None, "you can expend a use of your Wild Shape feature to take on a starry form"),
              (None, "The form lasts for 10 minutes"),
              (None, "This form sheds bright light in a 10-foot radius and dim light for an additional 10 feet"),
              ("stars-tce-2-archer", "1d8 + your Wisdom modifier"),
              ("stars-tce-2-archer", "a luminous arrow that targets one creature within 60 feet of you"),
              ("stars-tce-2-chalice", "you or another creature within 30 feet of you can regain hit points equal to 1d8 + your Wisdom modifier"),
              ("stars-tce-2-dragon", "you can treat a roll of 9 or lower on the d20 as a 10"),
              ("stars-tce-10-twinkling-constellations", "you have a flying speed of 20 feet and can hover")),
             level_vars={"star_dice": STARRY_FORM_DICE_2014},
             extras=(("stars-tce-10-twinkling-constellations", "Twinkling Constellations: while the Dragon is active you have a "
                      "flying speed of 20 feet and can hover; you can change the constellation at the start of each of your turns"),)),
    _w8_note("wildfire-tce", "druid", "druid:wild-shape", "wildfire-tce-2-summon-wildfire-spirit", "Summon Wildfire Spirit",
             "Summon Wildfire Spirit (action): expend a use of Wild Shape to summon your wildfire spirit within 30 feet; each "
             "other creature within 10 feet of it makes a Dexterity saving throw (DC {dc_wis}) or takes 2d6 fire damage; the "
             "spirit (proficiency bonus {pb}) lasts 1 hour, until it drops to 0 hit points, until you summon it again or "
             "until you die",
             ((None, "you can expend one use of your Wild Shape feature to summon your wildfire spirit"),
              (None, "within 30 feet of you"),
              (None, "within 10 feet of the spirit (other than you)"),
              (None, "against your spell save DC or take 2d6 fire damage"),
              (None, "The spirit manifests for 1 hour"),
              ("wildfire-tce-6-enhanced-bond", "roll a d8, and you gain a bonus equal to the number rolled to one damage or healing roll of the spell")),
             extras=(("wildfire-tce-6-enhanced-bond", "Enhanced Bond: while the spirit is summoned, roll a d8 and add it to one "
                      "damage or healing roll of a fire-damage or healing spell you cast"),)),
    # ---- Fighter: sentences on Second Wind, Action Surge, Indomitable
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:second-wind", "purple-dragon-knight-scag-3-rallying-cry", "Rallying Cry",
             "Rallying Cry: when you use Second Wind, up to three allies within 60 feet that can see or hear you regain "
             "{level} hit points each (your Fighter level)",
             ((None, "you can choose up to three creatures within 60 feet of you that are allied with you. Each one regains hit points equal to your fighter level"),)),
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:action-surge", "purple-dragon-knight-scag-10-inspiring-surge", "Inspiring Surge",
             "Inspiring Surge: when you use Action Surge, one ally within 60 feet that can see or hear you makes one melee "
             "or ranged weapon attack with its reaction",
             ((None, "you can choose one creature within 60 feet of you that is allied with you. That creature can make one melee or ranged weapon attack with its reaction"),
              ("purple-dragon-knight-scag-18-inspiring-surge", "you can choose two allies within 60 feet of you, rather than one")),
             extras=(("purple-dragon-knight-scag-18-inspiring-surge", "from 18th level you can choose two allies within 60 feet "
                      "instead of one"),)),
    _w8_note("purple-dragon-knight-scag", "fighter", "fighter:indomitable", "purple-dragon-knight-scag-15-bulwark", "Bulwark",
             "Bulwark: when you use Indomitable to reroll an Intelligence, Wisdom or Charisma saving throw, one ally within "
             "60 feet that failed the same save and can see or hear you also rerolls it and must use the new roll",
             ((None, "you can choose one ally within 60 feet of you that also failed its saving throw against the same effect"),)),
)

SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + _W8B_TAIL
SUBCLASS_NOTES_2014_BOOKS = SUBCLASS_NOTES_2014_BOOKS + _W8B_NOTES

# ---- W8c: Monk, Paladin, Ranger, Rogue (book subclasses) ----------------------------------------------------------------
# Tables that live only in the text (pinned in BOOK_TABLE_PINS_2014, like the W8a / W8b ones).
BREATH_ROLLS_2014 = ((3, 2), (11, 3))
ELEMENTAL_KI_CAP_2014 = ((3, "extra ki points can't raise a spell's level before Monk level 5"),
                         (5, "you can spend up to 3 ki points in total on one discipline spell to raise its level"),
                         (9, "you can spend up to 4 ki points in total on one discipline spell to raise its level"),
                         (13, "you can spend up to 5 ki points in total on one discipline spell to raise its level"),
                         (17, "you can spend up to 6 ki points in total on one discipline spell to raise its level"))
PALADIN_AURA_FEET_2014 = ((7, 10), (18, 30))
DRAKES_BREATH_DICE_2014 = ((11, "8d6"), (15, "10d6"))
DREADFUL_STRIKES_DICE_2014 = ((3, "1d4"), (11, "1d6"))
PLANAR_WARRIOR_DICE_2014 = ((3, "1d8"), (11, "2d8"))
GATHERED_SWARM_DICE_2014 = ((3, "1d6"), (11, "1d8"))
