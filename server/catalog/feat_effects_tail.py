"""FE10: the resource and note tail of the feat effect table (docs/superpowers/plans/2026-10-11-feat-effects.md).

Pure data, imported at the end of ``feat_effects_data`` (which merges ``TAIL_EFFECTS`` into ``FEAT_EFFECTS`` and
``TAIL_QUOTES`` into ``FEAT_EFFECT_QUOTES``; ``COMPLETION`` / ``COMPLETION_QUOTES`` add the notes and resources that
earlier slices left out of entries they had already classified).

Every feat that was still pending after FE9 is classified here, each under its own edition's text, under every ruleset:

- a feat with uses gets ``resources`` (``uses``: int, ``"pb"`` the Proficiency Bonus, or ``"inc_mod"`` the modifier of
  the ability the feat increased; ``recharge`` long | short | short-or-long);
- every other benefit is a note that paraphrases the catalog text with the character's numbers (``{pb}``,
  ``{8+pb+inc_mod}``, ``{level}``, ``{<abl>_mod}``, ...: see ``engine.feat_effects.render``);
- ``data_only`` marks a feat whose whole text is carried by catalog fields (spells, languages, proficiencies);
- spell-grant tables (the eight Arcane Adept feats of Unearthed Arcana keyed by spell slot level, Potent Dragonmark's
  extra slot, Rune Shaper's runes, Boon of Magic School Mastery, Magic Connoisseur) are notes only (decision F-D8: FE11
  is not built).

Effects that the catalog already carries as structured fields (resistances, immunities, senses, Expertise, spells,
languages, proficiencies) reach the sheet without an entry here; ``tests/test_feat_tail.py`` pins that each of those
feats really has such a field. ``TAIL_QUOTES`` pins the governing sentence(s) of each entry against the catalog text.
"""
from __future__ import annotations

TAIL_EFFECTS: dict[str, dict] = {}
TAIL_QUOTES: dict[str, str | tuple[str, ...]] = {}


def _res(name: str, uses, recharge: str, note: str | None = None, **extra) -> dict:
    entry = {"name": name, "uses": uses, "recharge": recharge}
    if note:
        entry["note"] = note
    entry.update(extra)
    return entry


# ----------------------------------------------------------------------------------------------- resources
TAIL_EFFECTS.update({
    "aberrant-dragonmark-efa": {
        "notes": ["Aberrant Magic: a Sorcerer cantrip and a level 1 Sorcerer spell (always prepared); Constitution is the "
                  "spellcasting ability. Spells of the mark are listed with the innate spells.",
                  "Aberrant Surge: when you cast that level 1 spell you can expend and roll a Hit Point Die; an even roll "
                  "gives you that many Temporary Hit Points, an odd roll deals that much Force damage to one other "
                  "creature within 30 feet (to you if none is in range)."],
        "resources": [
            _res("Aberrant Fortitude", 1, "long", "Reaction when you fail a Constitution save: add 1d4 to the save."),
            _res("Aberrant Magic (level 1 spell)", 1, "short-or-long", "Cast the chosen level 1 spell without a spell slot.")]},
    "adept-of-the-red-robes-dsotdq": {
        "notes": ["Insightful Magic: one 2nd-level Illusion or Transmutation spell, cast once without a slot per Long Rest "
                  "(spellcasting ability chosen for Initiate of High Sorcery)."],
        "resources": [_res("Magical Balance", "pb", "long",
                           "After rolling a 9 or lower on the d20 of an attack roll or ability check, treat it as a 10.")]},
    "agent-of-order-sato": {
        "notes": ["Stasis Strike: once per turn when you damage a creature you see within 60 feet, +1d8 force damage; "
                  "Wisdom save, DC {8+pb} plus the modifier of the spellcasting ability chosen for Scion of the Outer "
                  "Planes; a failure leaves it Restrained until the start of your next turn."],
        "resources": [_res("Stasis Strike", "pb", "long", "Once per turn; DC 8 + Proficiency Bonus + the Scion spellcasting modifier.")]},
    "arcane-artist-au": {
        "notes": ["Cantrip: Minor Illusion (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Inspiring Magic: when you cast an Illusion spell, one ally within 30 feet who sees you gains Heroic Inspiration."],
        "resources": [_res("Inspiring Magic", 1, "long")]},
    "arcane-infiltrator-au": {
        "notes": ["Cantrip: Friends (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Cunning Diversion: take the Dodge action as a Bonus Action."],
        "resources": [_res("Cunning Diversion", "pb", "long")]},
    "arcane-omens-au": {
        "notes": ["Cantrip: Guidance (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Helpful Premonition: Reaction when you or a creature you see within 30 feet fails a saving throw: add 1d4 to the save."],
        "resources": [_res("Helpful Premonition", "pb", "long")]},
    "arcane-overload-au": {
        "notes": ["Cantrip: Fire Bolt (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Power Surge: when you cast an Evocation spell and deal damage with it, add +{pb} to one damage roll of the spell."],
        "resources": [_res("Power Surge", 1, "long", "Adds your Proficiency Bonus to one damage roll of an Evocation spell.")]},
    "arcane-safeguard-au": {
        "notes": ["Cantrip: Resistance (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Sheltering Aid: when you take the Help action to assist an ally's ability check, that ally gains {pb} Temporary Hit Points."],
        "resources": [_res("Resistance as a Bonus Action", "pb", "long")]},
    "arcane-undertaker-au": {
        "notes": ["Cantrip: one Necromancy cantrip from the Cleric or Wizard list (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Knowledge from the Dead: add 1d4 to an Intelligence (History) or Wisdom (Medicine) check.",
                  "Understanding of Death: when you take the Help action to stabilize a creature at 0 Hit Points, you gain Heroic Inspiration."],
        "resources": [_res("Understanding of Death", 1, "long")]},
    "baleful-scion-sato": {
        "notes": ["Grasp of Avarice: once per turn when you damage a creature you see within 60 feet, it also takes "
                  "1d6 + {pb} necrotic damage and you regain Hit Points equal to that necrotic damage."],
        "resources": [_res("Grasp of Avarice", "pb", "long", "Once per turn; 1d6 + Proficiency Bonus necrotic damage, healing the same amount.")]},
    "bloodlust-abh": {
        "notes": ["Powerful Recovery: when you roll a Hit Point Die to regain Hit Points, treat a 1 or 2 as a 3.",
                  "Sanguine Feast: once per turn when you hit a Bloodied creature that is not a Construct or Undead, expend "
                  "a Hit Point Die and regain the roll + {con_mod} Hit Points."],
        "resources": [_res("Sanguine Feast", "pb", "long", "Once per turn; regain the Hit Die roll + Constitution modifier.")]},
    "boon-of-erupting-spellpower-au": {
        "notes": ["Spell Overload: when you cast a damage spell with a spell slot, treat any 1 or 2 on a damage die as a 3; "
                  "creatures that took damage from the spell also have the Prone condition."],
        "resources": [_res("Spell Overload", 1, "short-or-long", "Also regained when you roll Initiative.")]},
    "boon-of-exquisite-radiance-frhof": {
        "notes": ["Eternal Rest: creatures you reduce to 0 Hit Points cannot become Undead.",
                  "Powerful Radiance: on a damage roll that deals Radiant damage you can use the highest number possible on each die."],
        "resources": [_res("Powerful Radiance", 1, "long")]},
    "boon-of-fate-xphb": {
        "notes": ["Improve Fate: when you or another creature within 60 feet succeeds on or fails a D20 Test, roll 2d4 "
                  "and apply the total as a bonus or a penalty to that d20 roll."],
        "resources": [_res("Improve Fate", 1, "short-or-long", "Also regained when you roll Initiative.")]},
    "boon-of-fluid-forms-frhof": {
        "notes": ["Shapechanger (Magic action, 1 hour): become a Beast, Humanoid or Monstrosity of Challenge Rating 10 or "
                  "lower and gain Temporary Hit Points equal to the form's Hit Points; the form ends early at 0 Temporary Hit Points.",
                  "Hardy Transformation: the Temporary Hit Points you gain when you shape-shift increase by 20."],
        "resources": [_res("Shapechanger", 1, "long")]},
    "boon-of-misty-escape-abh": {
        "notes": ["Gaseous Form: if you drop to 0 Hit Points but are not killed outright, drop to 1 instead and cast Gaseous "
                  "Form on yourself with no action and no slot: Fly Speed 20 feet and 10 Hit Points regained at the start of "
                  "each of your turns; the spellcasting ability is the ability this feat increased."],
        "resources": [_res("Gaseous Form", 1, "long")]},
    "boon-of-recovery-xphb": {
        "notes": ["Last Stand: when you would drop to 0 Hit Points you instead drop to 1 and regain half your Hit Point maximum.",
                  "Recover Vitality: a Bonus Action to spend dice from the pool of ten d10s and regain Hit Points equal to the total rolled."],
        "resources": [_res("Last Stand", 1, "long"),
                      _res("Recover Vitality", 10, "long", "A pool of ten d10s; expend any number as a Bonus Action.", die="d10")]},
    "boon-of-terror-frhof": {
        "notes": ["Fearless: Immunity to the Frightened condition (counted in the condition immunities).",
                  "Flee, Fools!: Reaction when a Frightened creature starts its turn within 60 feet of you and you see it (not "
                  "behind Cover): Wisdom save, DC {8+cha_mod+pb}, or it spends its turn moving away from you.",
                  "Intimidating: proficiency in Intimidation (if you lack it) and Expertise in it (counted in the skills)."],
        "resources": [_res("Flee, Fools!", 1, "short-or-long", "Wisdom save DC 8 + Charisma modifier + Proficiency Bonus.",
                           dc="8 + cha_mod + pb")]},
    "boon-of-the-soul-drinker-frhof": {
        "notes": ["Grave Resistance: Resistance to Cold and Necrotic damage (counted in the damage modifiers).",
                  "Siphon Life: Reaction when an enemy within 120 feet is reduced to 0 Hit Points: regain 50 Hit Points."],
        "resources": [_res("Siphon Life", 1, "short-or-long", "Regain 50 Hit Points.")]},
    "cult-of-the-dragon-initiate-frhof": {
        "notes": ["Dragon's Tongue: you know Draconic; if you already know it, choose any other language instead (the "
                  "app lists Draconic only, so add the replacement language by hand).",
                  "Dragon's Terror (Magic action): a creature you see within 30 feet makes a Wisdom save, DC {8+wis_mod+pb}, "
                  "or is Frightened until the end of your next turn; the target is then immune for 24 hours.",
                  "Inspired by Fear: when you frighten a creature you are the source of fear for, gain Heroic Inspiration if you lack it."],
        "resources": [_res("Inspired by Fear", 1, "short-or-long")]},
    "delicious-pain-abh": {
        "notes": ["Toughened Flesh: Reaction right after you take Bludgeoning, Piercing or Slashing damage: Resistance to "
                  "those three types until the start of your next turn."],
        "resources": [_res("Toughened Flesh", 1, "short-or-long")]},
    "divination-adept-au": {
        "notes": ["Additional Spells (always prepared when you have spell slots of that level): 1 Detect Evil and Good; "
                  "2 Mind Spike; 3 Clairvoyance; 4 Divination; 5 Scrying; the spells of that level and lower.",
                  "Prescient Intervention: Reaction when a creature you see within 60 feet makes a D20 Test: give it "
                  "Advantage or Disadvantage."],
        "resources": [_res("Prescient Intervention", 1, "long", "Also regained when you cast a Divination spell with a spell slot.")]},
    "ember-of-the-fire-giant-bgg": {
        "notes": ["Born of Flame: Resistance to fire damage (counted in the damage modifiers).",
                  "Searing Ignition: replace one attack of the Attack action with a 15-foot-radius burst around you; Dexterity "
                  "save, DC {8+pb+inc_mod}; on a failure 1d8 + {pb} fire damage and Blinded until the start of your next "
                  "turn, half damage on a success."],
        "resources": [_res("Searing Ignition", "pb", "long", "No more than once per turn; 1d8 + Proficiency Bonus fire damage.")]},
    "fairy-trickster-frhof": {
        "notes": ["Faerie Trod Trotter: after you take the Disengage action, Difficult Terrain costs no extra movement for the rest of the turn.",
                  "Flustering Strike: when you hit with an attack roll, the target makes a Wisdom save, DC {8+inc_mod+pb}, "
                  "or has Disadvantage on saving throws until the end of your next turn."],
        "resources": [_res("Flustering Strike", "pb", "long")]},
    "familiar-friend-au": {
        "notes": ["Faithful Companion: Find Familiar is always prepared; cast it once without a slot or Material components "
                  "per Long Rest (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Fortified Familiar: when you cast Find Familiar, your familiar's Hit Points maximum and current Hit "
                  "Points increase by {2*level}.",
                  "Helpful Friend: Advantage on an ability check with a skill you are proficient in while your familiar is within 5 feet."],
        "resources": [_res("Helpful Friend", "pb", "long")]},
    "fury-of-the-frost-giant-bgg": {
        "notes": ["Born of Ice: Resistance to cold damage (counted in the damage modifiers).",
                  "Frigid Retaliation: Reaction after a creature you see within 30 feet hits you and deals damage: it makes a "
                  "Constitution save, DC {8+pb+inc_mod}; on a failure it takes 1d8 + {pb} cold damage and its speed is 0 "
                  "until the end of its next turn."],
        "resources": [_res("Frigid Retaliation", "pb", "long", "1d8 + Proficiency Bonus cold damage.")]},
    "gathered-whispers-rhw": {
        "notes": ["Spirit Whispers: Message (no Material components) and Augury (always prepared, cast once without a slot "
                  "or components per Long Rest); Intelligence, Wisdom or Charisma, chosen with the feat.",
                  "Unearthly Scream: Reaction when an attack roll hits you: add +{pb} to your AC against that attack.",
                  "Voices from Beyond: after you roll a 1 on a D20 Test, make a Wisdom save, DC {13+pb}; on a failure you "
                  "are Deafened until the end of your next turn and have Disadvantage on ability checks and attack rolls."],
        "resources": [_res("Unearthly Scream", "pb", "long", "Reaction: add your Proficiency Bonus to your AC against one attack.")]},
    "genie-magic-frhof": {
        "notes": ["Wish Magic (Magic action): cast a level 1 Sorcerer spell with a casting time of an action; the spellcasting "
                  "ability is the ability this feat increased. At level 11 it is cast as with a level 2 slot, at level 17 "
                  "as with a level 3 slot (your level is {level})."],
        "resources": [_res("Wish Magic", 1, "long")]},
    "gift-of-the-chromatic-dragon-ftd": {
        "notes": ["Chromatic Infusion (Bonus Action): touch a simple or martial weapon; for 1 minute it deals an extra "
                  "1d4 damage of acid, cold, fire, lightning or poison (your choice) on a hit.",
                  "Reactive Resistance: Reaction when you take acid, cold, fire, lightning or poison damage: Resistance to that instance."],
        "resources": [_res("Chromatic Infusion", 1, "long"), _res("Reactive Resistance", "pb", "long")]},
    "gift-of-the-gem-dragon-ftd": {
        "notes": ["Telekinetic Reprisal: Reaction when a creature within 10 feet damages you: Strength save, DC {8+pb+inc_mod}; "
                  "on a failure it takes 2d8 force damage and is pushed up to 10 feet, half damage and no push on a success."],
        "resources": [_res("Telekinetic Reprisal", "pb", "long", "2d8 force damage.")]},
    "gift-of-the-metallic-dragon-ftd": {
        "notes": ["Draconic Healing: Cure Wounds, cast once without a slot per long rest (Intelligence, Wisdom or Charisma, "
                  "chosen with the feat).",
                  "Protective Wings: Reaction when you or a creature within 5 feet that you see is hit: +{pb} to the target's AC against that attack."],
        "resources": [_res("Draconic Healing (Cure Wounds)", 1, "long"),
                      _res("Protective Wings", "pb", "long", "Adds your Proficiency Bonus to the target's AC against one attack.")]},
    "greater-aberrant-mark-efa": {
        "notes": ["Improved Fortitude: Aberrant Fortitude rolls 1d6 instead of 1d4 and is regained on a Short or Long Rest.",
                  "Mark of Inspiration: when you cast a cantrip, roll one or two unexpended Hit Point Dice; you gain that "
                  "many Temporary Hit Points + {con_mod} and one creature within 30 feet takes that much Force damage; the dice are expended."],
        "resources": [_res("Mark of Inspiration", "pb", "long")]},
    "greater-mark-of-handling-efa": {
        "notes": ["Improved Intuition: Wild Intuition rolls 1d6 instead of 1d4.",
                  "Improved Handling: when you are mounted and hit a target within 5 feet of your mount, your mount can use its Reaction to move or make one attack.",
                  "Subdue Animal (Magic action): a Beast or Monstrosity within 30 feet makes a Wisdom save, DC {8+wis_mod+pb}, or is Frightened until the start of your next turn."],
        "resources": [_res("Subdue Animal", "pb", "long", "Wisdom save DC 8 + Wisdom modifier + Proficiency Bonus.", dc="8 + wis_mod + pb")]},
    "greater-mark-of-healing-efa": {
        "notes": ["Improved Intuition: Medical Intuition rolls 1d6 instead of 1d4.",
                  "Improved Healing: cast Cure Wounds through Healing Touch without a slot; when you cast Cure Wounds, treat a 1 or 2 on a healing die as a 3."],
        "resources": [_res("Improved Healing (Cure Wounds)", "pb", "long")]},
    "greater-mark-of-hospitality-efa": {
        "notes": ["Improved Intuition: Ever Hospitable rolls 1d6 instead of 1d4.",
                  "Improved Hospitality: modify Purify Food and Drink so creatures of your choice within 30 feet lose 1 level of "
                  "Exhaustion and gain Temporary Hit Points equal to {pb} plus your chosen Intelligence, Wisdom or Charisma modifier."],
        "resources": [_res("Improved Hospitality", 1, "long")]},
    "greater-mark-of-scribing-efa": {
        "notes": ["Improved Intuition: Gifted Scribe rolls 1d6 instead of 1d4.",
                  "Inspired Scribing: modify Comprehend Languages to cover up to three willing creatures within 30 feet, who "
                  "can also speak telepathically to each other within 1 mile."],
        "resources": [_res("Inspired Scribing", 1, "long")]},
    "greater-mark-of-warding-efa": {
        "notes": ["Improved Intuition: Warder's Intuition rolls 1d6 instead of 1d4.",
                  "Improved Warding: Reaction when a creature attacks you or a creature you see within 30 feet: impose Disadvantage on that roll."],
        "resources": [_res("Improved Warding", "pb", "long")]},
    "guile-of-the-cloud-giant-bgg": {
        "notes": ["Cloudy Escape: Reaction when a creature you see hits you with an attack roll: Resistance to that attack's "
                  "damage, then teleport to an unoccupied space you see within 30 feet."],
        "resources": [_res("Cloudy Escape", "pb", "long")]},
    "knight-of-the-crown-dsotdq": {
        "notes": ["Commanding Rally (Bonus Action): one ally within 30 feet who sees or hears you makes one weapon attack as a "
                  "Reaction; on a hit they add 1d8 to the damage. You keep every Knight of Solamnia feat if you change order."],
        "resources": [_res("Commanding Rally", "pb", "long")]},
    "knight-of-the-rose-dsotdq": {
        "notes": ["Bolstering Rally (Bonus Action): a creature you see within 30 feet (yourself included) who sees or hears you "
                  "gains 1d8 + {pb} + {inc_mod} Temporary Hit Points. You keep every Knight of Solamnia feat if you change order."],
        "resources": [_res("Bolstering Rally", "pb", "long", "1d8 + Proficiency Bonus + the increased ability's modifier Temporary Hit Points.")]},
    "knight-of-the-sword-dsotdq": {
        "notes": ["Demoralizing Strike: once per turn when you hit with a weapon attack, the target makes a Wisdom save, DC "
                  "{8+pb+inc_mod}; on a failure it is Frightened of you until the end of your next turn, on a success it has "
                  "Disadvantage on its next attack roll. You keep every Knight of Solamnia feat if you change order."],
        "resources": [_res("Demoralizing Strike", "pb", "long")]},
    "light-bringer-abh": {
        "notes": ["Sacred Magic: the Light cantrip (or another Cleric cantrip if you know it); the spellcasting ability is the "
                  "ability this feat increased.",
                  "Solar Luminance: the light of your Light spell can be sunlight.",
                  "Sun's Healing (Bonus Action, in sunlight): expend a Hit Point Die and regain Hit Points equal to the roll."],
        "resources": [_res("Solar Luminance", 1, "long"), _res("Sun's Healing", 1, "short-or-long")]},
    "living-shadow-rhw": {
        "notes": ["Grasping Shadow: Mage Hand without spell components (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Lengthened Strike: +10 feet of reach on a melee attack roll made as part of the Attack or Magic action on your turn.",
                  "Ominous Will: after you roll a 1 on a D20 Test, make a Wisdom save, DC {13+pb}; on a failure you are "
                  "Incapacitated until the start of your next turn and act as the Shadow's Will table decides."],
        "resources": [_res("Lengthened Strike", "pb", "long")]},
    "lordly-resolve-frhof": {
        "notes": ["Standard Bearer (Bonus Action): up to three creatures within 60 feet that see you can end Prone with a "
                  "Reaction and, for 1 minute, cannot be possessed or Charmed or Frightened (Advantage on new saves if they already are)."],
        "resources": [_res("Standard Bearer", 1, "long")]},
    "love-bites-abh": {
        "notes": ["Endearing Pain: Bonus Action right after you damage a creature with a Melee weapon or an Unarmed Strike: it "
                  "is Charmed until the start of your next turn or until you or your allies damage it."],
        "resources": [_res("Endearing Pain", 1, "short-or-long")]},
    "mark-of-sentinel-efa": {
        "notes": ["Sentinel's Intuition: add 1d4 to a Wisdom (Insight or Perception) check.",
                  "Guardian's Shield: Shield is always prepared and cast once without a slot per Long Rest (spells are in the innate spells).",
                  "Vigilant Guardian: Reaction when a creature you see within 5 feet is hit by an attack roll: swap places with it and be hit instead.",
                  "Spells of the Mark (added to a Spellcasting or Pact Magic spell list): 1 Compelled Duel, Shield of Faith; "
                  "2 Warding Bond, Zone of Truth; 3 Counterspell, Protection from Energy; 4 Death Ward, Guardian of Faith; 5 Bigby's Hand."],
        "resources": [_res("Vigilant Guardian", "pb", "long")]},
    "mist-walker-rhw": {
        "notes": ["Domain Traveler: when you enter the Mists for a specific domain you know by name, you count as having a "
                  "Mist talisman keyed to it.",
                  "Mist Walk: Reaction when you take damage or fail a save against Grappled or Restrained: teleport up to 15 feet.",
                  "Poisoned Roots: after a Long Rest, each Short Rest you finish within 10 miles needs a Constitution save, DC "
                  "{13+pb}; on a failure it gives no benefits."],
        "resources": [_res("Mist Walk", "pb", "long")]},
    "mythal-touched-frhof": {
        "notes": ["Mythal Ward: Reaction when a spell attack hits you or you fail a save against a spell: roll on the "
                  "Mythal-Touched Magic table; any effect save is DC {8+inc_mod+pb}."],
        "resources": [_res("Mythal Ward", "pb", "long", "Roll on the Mythal-Touched Magic table.")]},
    "planar-wanderer-sato": {
        "notes": ["Planar Adaptation: after a Long Rest choose Resistance to acid, cold or fire damage until the next Long Rest "
                  "(pick it at the table: the choice lasts one rest).",
                  "Portal Cracker: concentrate on a portal within 5 feet and make a DC 20 Intelligence (Arcana) check; on a "
                  "failure you take 3d8 psychic damage, on a success you force it open or closed for 1 hour.",
                  "Portal Sense: you know the direction to the last portal you used on the same plane; once per Long Rest an action "
                  "detects portals within 30 feet that are not behind Cover."],
        "resources": [_res("Portal Sense (detect portals)", 1, "long")]},
    "potent-dragonmark-efa": {
        "notes": ["Dragonmark Preparation: the spells of your Spells of the Mark list are always prepared.",
                  "Dragonmark Spellcasting: one extra spell slot of level {min(5, (level+1)//2)} (half your level rounded up, "
                  "at most 5) for spells your Dragonmark feat and this feat give; regained on a Short or Long Rest."]},
    "purple-dragon-commandant-frhof": {
        "notes": ["Encourage Ally (Bonus Action): an ally you see within 30 feet gains 2d6 + {inc_mod} Temporary Hit Points.",
                  "Last Stand: Advantage on attack rolls while you are Bloodied."],
        "resources": [_res("Encourage Ally", "pb", "long", "2d6 + the increased ability's modifier Temporary Hit Points.")]},
    "purple-dragon-rook-frhof": {
        "notes": ["Entreat: proficiency in Insight, Performance or Persuasion (your choice).",
                  "Rallying Cry: when you roll Initiative and are not Incapacitated, up to {pb} creatures you see within 30 feet gain Heroic Inspiration."],
        "resources": [_res("Rallying Cry", 1, "long", "Up to your Proficiency Bonus in creatures gain Heroic Inspiration.")]},
    "putrefy-abh": {
        "notes": ["Necrosis: when you make a damage roll that deals Necrotic damage, one creature taking it is Poisoned until the start of your next turn."],
        "resources": [_res("Necrosis", 1, "short-or-long")]},
    "rebuke-abh": {
        "notes": ["Radiant Strike: when you make a damage roll that deals Radiant damage, one Huge or smaller creature taking it is knocked Prone."],
        "resources": [_res("Radiant Strike", 1, "short-or-long")]},
    "righteous-heritor-sato": {
        "notes": ["Soothe Pain: Reaction when you or a creature within 30 feet takes damage: reduce it by 1d10 + {pb}."],
        "resources": [_res("Soothe Pain", "pb", "long", "Reduce the damage by 1d10 + Proficiency Bonus.")]},
    "rune-shaper-bgg": {
        "notes": ["Comprehend Languages: learned; cast once without a slot per long rest.",
                  "Rune Magic: you know {pb//2} rune(s) (half your Proficiency Bonus, rounded down) from the Rune Spells table "
                  "(Cloud fog cloud, Death inflict wounds, Dragon chromatic orb, Enemy disguise self, Fire burning hands, Friend "
                  "speak with animals, Frost armor of Agathys, Hill goodberry, Journey longstrider, King command, Mountain "
                  "entangle, Stone sanctuary, Storm thunderwave). After a long rest inscribe each rune on an object; each "
                  "rune's spell is cast once without a slot per long rest, and you can swap one rune each time you gain a level."]},
    "sharp-eye-rhw": {
        "notes": ["When you take the Search or Study action, give yourself Advantage on any ability check made as part of it; "
                  "a use is not expended if the check fails."],
        "resources": [_res("Sharp Eye", "pb", "long", "A use is not expended if the check fails.")]},
    "soul-of-the-storm-giant-bgg": {
        "notes": ["Maelstrom Aura (Bonus Action): a 10-foot aura until the start of your next turn; while it lasts you have "
                  "Resistance to lightning and thunder damage, attack rolls against you have Disadvantage, and a creature that "
                  "starts its turn inside makes a Strength save, DC {8+pb+inc_mod}, or has its speed halved."],
        "resources": [_res("Maelstrom Aura", "pb", "long")]},
    "spell-subterfuge-au": {
        "notes": ["Shrouding Spells: after you cast an action-time spell with a slot, take Dash and Hide together as a Bonus "
                  "Action; the uses equal the modifier of the increased ability ({inc_mod}).",
                  "Sneaky Casting: a Verbal spell or a spell attack does not end the Invisible condition from Hide while you end the turn behind Cover."],
        "resources": [_res("Shrouding Spells", "inc_mod", "long", "Uses equal the modifier of the ability this feat increased.")]},
    "spellfire-spark-frhof": {
        "notes": ["Magic Absorption: once per turn when you take damage from a spell or magical effect, reduce it by 1d4 "
                  "(not while Incapacitated).",
                  "Spellfire Flame: Sacred Flame (Intelligence, Wisdom or Charisma, chosen with the feat), which you can also "
                  "cast as a Bonus Action."],
        "resources": [_res("Spellfire Flame (Bonus Action)", "pb", "long")]},
    "squire-of-solamnia-dsotdq": {
        "notes": ["Mount Up: mounting or dismounting costs only 5 feet of movement.",
                  "Precise Strike: once per turn give a weapon attack roll Advantage; if it hits, add 1d8 to the damage "
                  "(a use is spent only on a hit). You keep every Knight of Solamnia feat if you change order."],
        "resources": [_res("Precise Strike", "pb", "long", "A use is expended only if the attack hits.")]},
    "strixhaven-mascot-scc": {
        "notes": ["Find Familiar as a ritual; the familiar can take the mascot form of your college.",
                  "When you take the Attack action you can forgo one attack to let the mascot familiar attack with its reaction.",
                  "Teleport (action): swap places with your familiar if it is within 60 feet."],
        "resources": [_res("Mascot teleport", 1, "long", "Can be used again by expending a spell slot of level 2 or higher.")]},
    "survivor-rhw": {
        "notes": ["Hypervigilance: when you roll Initiative you can reroll a d20 result of 9 or lower and must use the new roll.",
                  "Steel Yourself: Reaction when you fail a save against Charmed or Frightened: add +{pb} to the roll."],
        "resources": [_res("Steel Yourself", 1, "long", "Adds your Proficiency Bonus to the save.")]},
    "symbiotic-being-rhw": {
        "notes": ["Entwined Existence: the symbiote cannot be targeted; it dies and revives with you.",
                  "Second Mind: proficiency in one of Arcana, Deception, History, Intimidation, Insight, Investigation, Nature, "
                  "Religion, Perception or Persuasion, and one extra language.",
                  "Sustained Symbiosis: Reaction when you fail a saving throw: expend a Hit Die and add the roll to the save.",
                  "Symbiotic Agenda: after you roll a 1 on a D20 Test, make a Charisma save, DC {13+pb}; on a failure you are "
                  "Charmed for 1d12 hours."],
        "resources": [_res("Sustained Symbiosis", "pb", "long", "Add an expended Hit Die roll to a failed save.")]},
    "tireless-reveler-abh": {
        "notes": ["When an ally you see within 60 feet expends Heroic Inspiration, you gain Heroic Inspiration if you lack it."],
        "resources": [_res("Tireless Reveler", "pb", "short-or-long")]},
    "vampire-hunter-abh": {
        "notes": ["Adroit Escape: Advantage on checks to escape nonmagical restraints or the Grappled condition.",
                  "Vitality Ward: Reaction when you take Necrotic damage: roll {pb}d6 and reduce the damage by the total."],
        "resources": [_res("Vitality Ward", 1, "short-or-long", "Reduces Necrotic damage by Proficiency Bonus d6.")]},
    "vampires-plaything-abh": {
        "notes": ["Decanting: after a Long Rest, with an empty vial or flask, create one Potion of Healing or Antitoxin that evaporates at your next Long Rest.",
                  "Timely Retreat: Bonus Action to Dash or Disengage.",
                  "Vampiric Connection: on the same plane your former vampire master can speak telepathically to you and perceive through your senses."],
        "resources": [_res("Timely Retreat", "pb", "long")]},
    "vampiric-exultation-psx": {
        "notes": ["Action: turn the lower half of your body into vapor and gain a Fly Speed of 30 feet for up to 10 minutes."],
        "resources": [_res("Vapor form", 1, "short-or-long")]},
})

TAIL_QUOTES.update({
    "aberrant-dragonmark-efa": ("Once you've used this benefit, you can't use it again until you finish a Long Rest.",
                                "you regain the ability to cast it in that way when you finish a Short or Long Rest"),
    "adept-of-the-red-robes-dsotdq": "You can balance fate in this way a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest.",
    "agent-of-order-sato": "You can use this benefit a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest.",
    "arcane-artist-au": "Once you use this benefit, you can't use it again until you finish a Long Rest.",
    "arcane-infiltrator-au": "You can take the Dodge action as a Bonus Action.",
    "arcane-omens-au": "roll 1d4 and add the number rolled to the save's total",
    "arcane-overload-au": "you can add your Proficiency Bonus to one damage roll of that spell",
    "arcane-safeguard-au": "that ally gains a number of Temporary Hit Points equal to your Proficiency",
    "arcane-undertaker-au": "When you take the Help action to stabilize a creature with 0 Hit Points, you gain Heroic Inspiration.",
    "baleful-scion-sato": "The necrotic damage equals 1d6 + your proficiency bonus",
    "bloodlust-abh": "regain a number of Hit Points equal to the number rolled plus your Constitution modifier",
    "boon-of-erupting-spellpower-au": "Once you use this benefit, you can't do so again until you roll Initiative or finish a Long Rest or Short Rest.",
    "boon-of-exquisite-radiance-frhof": "Once you use this benefit, you can't do so again until you finish a Long Rest.",
    "boon-of-fate-xphb": "you can roll 2d4 and apply the total rolled as a bonus or penalty to the d20 roll",
    "boon-of-fluid-forms-frhof": "increase that number of Temporary Hit Points by 20",
    "boon-of-misty-escape-abh": "you can instead drop to 1 Hit Point and cast Gaseous Form without expending a spell slot",
    "boon-of-recovery-xphb": ("You have a pool of ten d10s.", "you can drop to 1 Hit Point instead and regain a number of Hit Points equal to half your Hit Point maximum"),
    "boon-of-terror-frhof": "DC 8 plus your Charisma modifier and your Proficiency Bonus",
    "boon-of-the-soul-drinker-frhof": "you can take a Reaction to regain 50 Hit Points",
    "cult-of-the-dragon-initiate-frhof": ("DC 8 plus your Wisdom modifier and Proficiency", "you instead learn one language of your choice"),
    "delicious-pain-abh": "you can take a Reaction to gain Resistance to Bludgeoning, Piercing, and Slashing damage until the start of your next turn",
    "divination-adept-au": "You can also regain use of this feature when you cast a spell from the Divination school using a spell slot.",
    "ember-of-the-fire-giant-bgg": "fire damage equal to 1d8 + your proficiency bonus",
    "fairy-trickster-frhof": "DC 8 plus the ability modifier of the score increased by this feat and your Proficiency",
    "familiar-friend-au": ("increased by an amount equal to twice your character level",
                           "You can use this benefit a number of times equal to your Proficiency"),
    "fury-of-the-frost-giant-bgg": "the creature takes cold damage equal to 1d8 + your proficiency bonus",
    "gathered-whispers-rhw": ("add your Proficiency Bonus to your AC against that attack", "DC 13 plus your Proficiency"),
    "genie-magic-frhof": ("When you reach level 11, the spell you cast with this feat is cast as though using a level 2 spell slot.",
                          "When you reach level 17, the spell is cast as though using a level 3 spell slot."),
    "gift-of-the-chromatic-dragon-ftd": ("the weapon deals an extra 1d4 damage of the chosen type when it hits",
                                         "You can use this reaction a number of times equal to your proficiency bonus"),
    "gift-of-the-gem-dragon-ftd": "the creature takes 2d8 force damage",
    "gift-of-the-metallic-dragon-ftd": "You grant a bonus to the target's AC equal to your proficiency bonus against that attack roll",
    "greater-aberrant-mark-efa": ("you can roll 1d6 instead of 1d4", "You can use this benefit a number of times equal to your Proficiency"),
    "greater-mark-of-handling-efa": "DC 8 plus your Wisdom modifier and Proficiency",
    "greater-mark-of-healing-efa": "a number of times equal to your Proficiency",
    "greater-mark-of-hospitality-efa": "Once you modify the spell with this benefit, you can't do so again until you finish a Long Rest.",
    "greater-mark-of-scribing-efa": "up to three willing creatures you can see within 30 feet of yourself",
    "greater-mark-of-warding-efa": "you can take a Reaction to impose Disadvantage on that roll",
    "guile-of-the-cloud-giant-bgg": "You can use this reaction a number of times equal to your proficiency bonus",
    "knight-of-the-crown-dsotdq": "You can use this bonus action a number of times equal to your proficiency bonus",
    "knight-of-the-rose-dsotdq": "temporary hit points equal to 1d8 + your proficiency bonus + the ability modifier of the ability score increased by this feat",
    "knight-of-the-sword-dsotdq": "DC equals 8 + your proficiency bonus + the ability modifier of the score increased by this feat",
    "light-bringer-abh": ("Once you use this benefit, you can't use it again until you finish a Long Rest.",
                          "Once you use this benefit, you can't use it again until you finish a Short or Long Rest."),
    "living-shadow-rhw": ("you can increase your reach for that attack by 10 feet", "DC 13 plus your Proficiency"),
    "lordly-resolve-frhof": "Once you use this benefit, you can't do so again until you finish a Long Rest.",
    "love-bites-abh": "Once you use this benefit, you can't use it again until you finish a Short or Long Rest.",
    "mark-of-sentinel-efa": ("When you make a Wisdom (Insight or Perception) check, you can roll 1d4 and add the number rolled to the ability check.",
                             "You can use this feature a number of times equal to your Proficiency"),
    "mist-walker-rhw": ("teleport up to 15 feet to an unoccupied space you can see", "DC 13 plus your Proficiency"),
    "mythal-touched-frhof": "the DC equals 8 plus the modifier of the ability increased by this feat and your Proficiency",
    "planar-wanderer-sato": ("you gain resistance to either acid, cold, or fire damage (your choice) until you finish your next long rest",
                             "make a 20 Intelligence (Arcana) check"),
    "potent-dragonmark-efa": "The spell slot's level is half your level (round up), to a maximum of level 5.",
    "purple-dragon-commandant-frhof": "The ally gains Temporary Hit Points equal to 2d6 plus the modifier of the ability score increased by this feat.",
    "purple-dragon-rook-frhof": "a number of creatures equal to your Proficiency Bonus that you can see within 30 feet of yourself",
    "putrefy-abh": "Once you use this benefit, you can't use it again until you finish a Short or Long Rest.",
    "rebuke-abh": "you can cause one Huge or smaller creature taking the damage to have the Prone condition",
    "righteous-heritor-sato": "reduce that damage by 1d10 + your proficiency bonus",
    "rune-shaper-bgg": "You know a number of runes equal to half your proficiency bonus (rounded down)",
    "sharp-eye-rhw": "If the check fails, the use of this feature isn't expended.",
    "soul-of-the-storm-giant-bgg": "You can use this bonus action a number of times equal to your proficiency bonus",
    "spell-subterfuge-au": "You can use this benefit a number of times equal to the ability modifier of the score increased by this feat",
    "spellfire-spark-frhof": ("you reduce the total damage taken by 1d4", "a number of times equal to your Proficiency"),
    "squire-of-solamnia-dsotdq": "a use is expended only if the attack hits",
    "strixhaven-mascot-scc": "unless you expend a spell slot of 2nd level or higher to do it again",
    "survivor-rhw": "The bonus is equal to your Proficiency Bonus.",
    "symbiotic-being-rhw": ("expend one of your Hit Dice", "DC 13 plus your Proficiency"),
    "tireless-reveler-abh": "You can use this benefit a number of times equal to your Proficiency",
    "vampire-hunter-abh": "Roll a number of d6s equal to your Proficiency",
    "vampires-plaything-abh": "You can take a Bonus Action to take the Dash action or the Disengage action.",
    "vampiric-exultation-psx": "Once you use this ability, you can't use it again until you finish a short or long rest.",
})

# ----------------------------------------------------------------------------------------------- notes only
def _adept(school: str, table: str, benefit: str) -> dict:
    return {"notes": [f"Additional Spells (always prepared once you have spell slots of that level, with the lower levels): {table}.",
                      benefit]}


def _mark_notes(intuition: str, magic: str, table: str) -> list[str]:
    return [intuition, magic,
            f"Spells of the Mark (added to a Spellcasting or Pact Magic spell list): {table}."]


TAIL_EFFECTS.update({
    "aberrant-anatomy-rhw": {
        "notes": ["Breathless: you can hold your breath for 1 hour.",
                  "Extrasensory Perception: proficiency and Expertise in Perception, and Blindsight 15 feet (counted in the skills and senses).",
                  "Warping Flesh: after you roll a 1 on a D20 Test, make a Constitution save, DC {13+pb}; on a failure you are Stunned until the end of your next turn."]},
    "aberrant-dragonmark-erlw": {
        "notes": ["A cantrip and a level 1 spell from the Sorcerer list (Constitution is the spellcasting ability); you cast the "
                  "level 1 spell through the mark and need a short or long rest before casting it that way again.",
                  "When you cast it you can expend a Hit Die: an even roll gives that many Temporary Hit Points, an odd roll "
                  "deals that much Force damage to a random creature within 30 feet (you if none is in range).",
                  "You also develop a random flaw from the Aberrant Dragonmark Flaws table (DM option: Greater Aberrant Powers)."],
        "resources": [_res("Aberrant mark spell", 1, "short-or-long", "Cast the level 1 spell through the mark.")]},
    "ability-score-improvement-xphb": {
        "notes": ["Increase one ability score by 2, or two ability scores by 1 each, to a maximum of 20; the feat is repeatable. "
                  "The app gives this through the ability score improvement choice of a class level, not as a feat pick."]},
    "abjuration-adept-au": _adept("Abjuration", "1 Shield; 2 Lesser Restoration; 3 Protection from Energy; 4 Banishment; 5 Mass Cure Wounds",
                                  "Protective Ward: when you cast an Abjuration spell with a spell slot, you or a creature you see within 30 "
                                  "feet gains Temporary Hit Points equal to twice the level of the slot."),
    "adept-of-the-black-robes-dsotdq": {
        "notes": ["Ambitious Magic: one 2nd-level Enchantment or Necromancy spell, cast once without a slot per long rest "
                  "(spellcasting ability chosen for Initiate of High Sorcery).",
                  "Life Channel: when a creature you see within 60 feet fails a save against a damage spell you cast, expend "
                  "Hit Dice equal to the spell's level and add the total rolled to the damage."]},
    "adept-of-the-white-robes-dsotdq": {
        "notes": ["Protective Magic: one 2nd-level Abjuration or Divination spell, cast once without a slot per long rest "
                  "(spellcasting ability chosen for Initiate of High Sorcery).",
                  "Protective Ward: Reaction when you or a creature within 30 feet takes damage: expend a spell slot and reduce "
                  "the damage by a d6 for each level of the slot plus your spellcasting ability modifier."]},
    "arcane-eloquence-au": {
        "notes": ["Cantrip: Vicious Mockery (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Smooth Talker: add 1d4 to a Charisma (Deception, Intimidation or Persuasion) check."]},
    "arcane-warrior-au": {
        "notes": ["Two Wizard cantrips (Mage Hand and Ray of Frost are recommended); Intelligence, Wisdom or Charisma is the "
                  "spellcasting ability. When you gain a level you can replace one with another Wizard cantrip."]},
    "artificer-initiate-tce": {
        "notes": ["An artificer cantrip and a 1st-level artificer spell (Intelligence); the 1st-level spell is cast once "
                  "without a slot per long rest.",
                  "Proficiency with one artisan's tool; you can use that tool type as a spellcasting focus for Intelligence spells."]},
    "blessed-warrior-xphb": {
        "notes": ["Two Cleric cantrips (Guidance and Sacred Flame are recommended) that count as Paladin spells, with Charisma "
                  "as the spellcasting ability. When you gain a Paladin level you can replace one with another Cleric cantrip."]},
    "boon-of-blazing-dawn-abh": {
        "notes": ["Beloved of the Sun: Immunity to Radiant damage (counted in the damage modifiers).",
                  "Blazing Strike: a weapon hit can deal Radiant or the weapon's normal damage type.",
                  "Burst of Sunlight: once per turn when you hit with an attack that deals Radiant damage, emit sunlight (Bright 30 feet, Dim 30 more) until the start of your next turn."]},
    "boon-of-bloodshed-frhof": {
        "notes": ["Killer's Fortune: when an enemy you see drops to 0 Hit Points, Advantage on your next attack roll before the end of your next turn.",
                  "Power from Pain: once per turn, on an attack roll while Bloodied, +{pb} extra damage of the attack's type."]},
    "boon-of-bountiful-health-frhof": {
        "notes": ["Augmented Health: whenever you gain Temporary Hit Points you gain 5 more.",
                  "Superior Recuperation: when you spend Hit Point Dice to regain Hit Points you can use the highest number possible on each die."]},
    "boon-of-combat-prowess-xphb": {
        "notes": ["Peerless Aim: when you miss with an attack roll you can hit instead; usable again at the start of your next turn."]},
    "boon-of-communication-frhof": {
        "notes": ["Cunning Speaker: no Disadvantage on ability checks to influence Hostile creatures.",
                  "Gifted Interpreter: you understand the literal meaning of any language you hear or see signed, or any written language you see.",
                  "Mental Communication: telepathy with a range of 120 feet."]},
    "boon-of-desperate-resilience-frhof": {
        "notes": ["Defense of Body and Mind: while you are Bloodied you have Resistance to every damage type except Force."]},
    "boon-of-dimensional-travel-xphb": {
        "notes": ["Blink Steps: right after you take the Attack or Magic action, teleport up to 30 feet to an unoccupied space you see."]},
    "boon-of-fortunes-favor-frhof": {
        "notes": ["Saving Throw Reroll: when you fail a saving throw you can reroll it and must use the new roll; usable again at the start of your next turn."]},
    "boon-of-looming-shadows-abh": {
        "notes": ["Shadowy Stretch: when you take the Attack action, your Melee weapon reach grows by 10 feet until the end of your turn.",
                  "Dancing Silhouette: take the Dodge action as a Bonus Action."]},
    "boon-of-magic-school-mastery-au": {
        "notes": ["Choose a school of magic (repeatable, a different school each time). Rote Casting: a level 1 spell of that "
                  "school from your class list is always prepared and cast without a slot or components. Signature Arcanum: "
                  "a spell of level 7 or lower from the school, always prepared and cast once without a slot per Long Rest."]},
    "boon-of-poison-mastery-frhof": {
        "notes": ["Antitoxic: Immunity to Poison damage and the Poisoned condition (counted in the immunities).",
                  "Perfect Poisoner: once per turn, when you roll dice for Poison damage from your attack, spell or feature, use the highest number on each die."]},
    "boon-of-revelry-frhof": {
        "notes": ["Inspire Dance: Otto's Irresistible Dance is always prepared, cast once without a slot per Long Rest with no "
                  "components, and damage does not break its Concentration.",
                  "Sing Out: a creature Charmed by that spell cannot cast spells with Verbal components."]},
    "boon-of-siberys-efa": {
        "notes": ["Aberrant Magic: one Sorcerer spell of level 8 or lower, or a Siberys Dragonmark spell (Animal Shapes "
                  "Handling, Control Weather Storm, Demiplane Making, Heroes' Feast Hospitality, Maze Warding, Mind Blank "
                  "Sentinel, Plane Shift Passage, Project Image Shadow, Regenerate Healing, Symbol Scribing, Teleport "
                  "Finding, True Seeing Detection); always prepared, cast once without a slot or components per Short or "
                  "Long Rest (Intelligence, Wisdom or Charisma, chosen with the feat)."]},
    "boon-of-spell-recall-xphb": {
        "notes": ["Free Casting: when you cast a spell with a level 1-4 slot, roll 1d4; if it equals the slot's level, the slot is not expended."]},
    "boon-of-the-bright-sun-frhof": {
        "notes": ["Daylight Presence (Bonus Action): a 30-foot Emanation of sunlight that dispels overlapping spell Darkness, until you dismiss it, die or are Incapacitated.",
                  "Fortifying Light: while it is active, at the start of each of your turns you and allies you see in it gain 10 Temporary Hit Points."]},
    "boon-of-the-furious-storm-frhof": {
        "notes": ["Eye of the Storm: Resistance to Lightning and Thunder damage (counted in the damage modifiers); Immunity to both while you are Bloodied.",
                  "Storm's Strength: creatures have Disadvantage on saves against your Lightning and Thunder spells."]},
    "boon-of-the-iron-mind-au": {
        "notes": ["Unshakable Focus: you lose Concentration only if you cast or activate another Concentration effect, are Petrified or Unconscious, or die."]},
    "boon-of-the-night-spirit-xphb": {
        "notes": ["Merge with Shadows: in Dim Light or Darkness, a Bonus Action to become Invisible until you take an action, Bonus Action or Reaction.",
                  "Shadowy Form: in Dim Light or Darkness you have Resistance to all damage except Psychic and Radiant."]},
    "boon-of-truesight-xphb": {
        "notes": ["Truesight with a range of 60 feet (counted in the senses)."]},
    "bountiful-luck-xge": {
        "notes": ["Reaction when an ally you see within 30 feet rolls a 1 on an attack roll, ability check or saving throw: they "
                  "reroll and use the new roll. You cannot use your Lucky racial trait before the end of your next turn."]},
    "cartomancer-bmt": {
        "notes": ["A card deck is a spellcasting focus; you know Prestidigitation (its components can pass as card handling).",
                  "Hidden Ace: after a Long Rest imbue a card with one action-time spell from your class list of a level you "
                  "have slots for; for 8 hours a Bonus Action casts it from the card, which then loses its magic."]},
    "chef-tce": {
        "notes": ["Proficiency with cook's utensils.",
                  "Short rest cooking: food for {4+pb} creatures; each that spends Hit Dice regains an extra 1d8 Hit Points.",
                  "Treats: {pb} treats per hour of work or Long Rest, lasting 8 hours; a Bonus Action to eat one gives {pb} Temporary Hit Points."]},
    "child-of-the-sun-lfl": {
        "notes": ["Eyes of Eirdu: you and allies within 10 feet have Advantage on saves to avoid or end the Blinded condition.",
                  "Faerie Fire: cast once without a slot per Long Rest (Intelligence, Wisdom or Charisma, chosen with the feat); "
                  "taking damage cannot break your Concentration on it when cast that way."]},
    "cloying-mists-abh": {
        "notes": ["Arise, Fog: Fog Cloud is always prepared and cast once without a slot per Long Rest (the increased ability is the spellcasting ability).",
                  "Grasping Mist: Fog Cloud extinguishes nonmagical flames in its sphere and reduces the Speed of other creatures in it by 5 feet."]},
    "cohort-of-chaos-sato": {
        "notes": ["Chaotic Flare: when you roll a 1 or 20 on an attack roll or saving throw, roll a d4 on the Chaotic Flares "
                  "table (1 Battle Fury, 2 Disruption Field 1d8 force, 3 Unbound teleport with your walking speed, 4 Wailing "
                  "Winds); a flare lasts until the end of your next turn and a new one cannot start before it ends."]},
    "cold-caster-frhof": {
        "notes": ["Cantrip: Ray of Frost (or another Wizard cantrip if you know it); the increased ability is the spellcasting ability.",
                  "Frostbite: once per turn when you hit and deal Cold damage, the creature subtracts 1d4 from the next saving throw it makes before the end of your next turn."]},
    "conjuration-adept-au": _adept("Conjuration", "1 Entangle; 2 Misty Step; 3 Conjure Animals; 4 Dimension Door; 5 Conjure Elemental",
                                   "Persistent Conjuration: while concentrating on a Conjuration spell, +{inc_mod} to Constitution saves to maintain Concentration."),
    "divinely-favored-dsotdq": {
        "notes": ["A Cleric cantrip, Augury, and a 1st-level spell by alignment (Evil Warlock, Good Cleric, Neutral Druid); the "
                  "1st-level spell and Augury are cast once without a slot per long rest.",
                  "A holy symbol is a spellcasting focus for the spells that use the ability you chose."]},
    "dragon-fear-xge": {
        "notes": ["Instead of exhaling, expend a Breath Weapon use to roar: creatures of your choice within 30 feet make a "
                  "Wisdom save, DC {8+pb+cha_mod}, or are Frightened for 1 minute (they repeat the save when damaged)."]},
    "drow-high-magic-xge": {"data_only": True},
    "druidic-warrior-xphb": {
        "notes": ["Two Druid cantrips (Guidance and Starry Wisp are recommended) that count as Ranger spells, with Wisdom as "
                  "the spellcasting ability. When you gain a Ranger level you can replace one with another Druid cantrip."]},
    "dwarven-fortitude-xge": {
        "notes": ["When you take the Dodge action you can spend a Hit Die, roll it, add {con_mod} and regain that many Hit Points (minimum 1)."]},
    "elemental-familiar-au": {
        "notes": ["Elemental Energy: when you cast Find Familiar, choose Acid, Cold, Fire, Lightning or Thunder; the familiar "
                  "has Resistance to that type.",
                  "Energy Pulse (Bonus Action, the familiar uses its Reaction): creatures in a 5-foot Emanation around the "
                  "familiar make a Dexterity save, DC {8+pb} plus your Find Familiar spellcasting modifier, or take 2d4 damage "
                  "of that type (and fall Prone if Medium or smaller)."]},
    "emerald-enclave-fledgling-frhof": {
        "notes": ["Speak with Animals is always prepared (Intelligence, Wisdom or Charisma, chosen with the feat); cast as a "
                  "Ritual its duration is 8 hours.",
                  "Tag Team: when you take the Help action you can swap places with a willing ally within 5 feet without provoking Opportunity Attacks."]},
    "enchantment-adept-au": _adept("Enchantment", "1 Dissonant Whispers; 2 Enthrall; 3 Hold Person; 4 Dominate Beast; 5 Modify Memory",
                                   "Subtle Enchantments: when you cast an Enchantment spell with a slot, omit its Verbal, Somatic and Material components "
                                   "(except consumed or costly Material components)."),
    "enclave-magic-frhof": {
        "notes": ["Friend to Animals: Advantage on ability checks when you take the Influence action with Beasts.",
                  "Two Hearts, One Mind: Beast Sense is always prepared and cast once without a slot per Long Rest, without Concentration."]},
    "evocation-adept-au": _adept("Evocation", "1 Chromatic Orb; 2 Shatter; 3 Fireball; 4 Vitriolic Sphere; 5 Wall of Force",
                                 "Fueled Evocation: once per turn when you cast an Evocation spell and deal damage, roll up to two unexpended "
                                 "Hit Point Dice and add the total to one damage roll (the dice are expended)."),
    "fey-teleportation-xge": {"data_only": True},
    "fey-touched-tce": {"data_only": True},
    "flames-of-phlegethos-xge": {
        "notes": ["When you roll fire damage for a spell you can reroll any 1 and must use the new roll.",
                  "When you cast a fire damage spell you can wreathe yourself in flames until the end of your next turn: bright "
                  "light 30 feet and dim light 30 more, and a creature within 5 feet that hits you with a melee attack takes 1d4 fire damage."]},
    "greater-mark-of-detection-efa": {
        "notes": ["Improved Intuition: Deductive Intuition rolls 1d6 instead of 1d4.",
                  "Shared Detection: when you cast See Invisibility through Magical Detection, one creature you see within 30 feet shares the spell."]},
    "greater-mark-of-finding-efa": {
        "notes": ["Improved Intuition: Hunter's Intuition rolls 1d6 instead of 1d4.",
                  "Improved Finding: Hunter's Mark through Finder's Magic has double range and can stop the target benefiting from the Invisible condition."]},
    "greater-mark-of-making-efa": {
        "notes": ["Improved Intuition: Artisan's Intuition rolls 1d6 instead of 1d4.",
                  "Improved Making: Magic Weapon through Spellsmith is cast as its level 3 version."]},
    "greater-mark-of-passage-efa": {
        "notes": ["Improved Intuition: Intuitive Motion rolls 1d6 instead of 1d4.",
                  "Improved Passage: when you cast Misty Step through Magical Passage, up to two willing creatures within 30 feet "
                  "can use their Reaction to teleport up to 30 feet as well."]},
    "greater-mark-of-sentinel-efa": {
        "notes": ["Improved Intuition: Sentinel's Intuition rolls 1d6 instead of 1d4.",
                  "Improved Sentinel: Vigilant Guardian also lets you make one weapon or Unarmed Strike attack as part of the same Reaction."]},
    "greater-mark-of-shadow-efa": {
        "notes": ["Improved Intuition: Cunning Intuition rolls 1d6 instead of 1d4.",
                  "Improved Shadow: Invisibility through Shape Shadows is cast as its level 3 version."]},
    "greater-mark-of-storm-efa": {
        "notes": ["Improved Intuition: Windwright's Intuition rolls 1d6 instead of 1d4.",
                  "Improved Storm: Gust of Wind through Storm Magic also gives you a Fly Speed of 60 feet for the spell's duration."]},
    "harper-teamwork-frhof": {
        "notes": ["Withering Wordplay: when you take the Help action to assist an ally's attack, that enemy also has Disadvantage on the first saving throw it makes before the start of your next turn.",
                  "Inspiring Willpower: when you succeed on a save to end Frightened or Paralyzed, one ally within 30 feet with the same condition is freed too."]},
    "illusion-adept-au": _adept("Illusion", "1 Silent Image; 2 Phantasmal Force; 3 Major Image; 4 Hallucinatory Terrain; 5 Seeming",
                                "Masterful Illusions: an Illusion spell cast with a slot needs no Verbal, Somatic or Material components (except "
                                "consumed or costly ones), and creatures have Disadvantage on Intelligence (Investigation) checks to see through it."),
    "infernal-constitution-xge": {
        "notes": ["Resistance to cold and poison damage (counted in the damage modifiers); Advantage on saves against being Poisoned."]},
    "initiate-of-high-sorcery-dsotdq": {"data_only": True},
    "interception-xphb": {
        "notes": ["Reaction when a creature you see hits another creature within 5 feet of you: reduce the damage by 1d10 + {pb} "
                  "(you must hold a Shield or a Simple or Martial weapon)."]},
    "lords-alliance-agent-frhof": {
        "notes": ["Inspiring Strike: once per turn on a Critical Hit, an ally within 30 feet who lacks Heroic Inspiration gains it.",
                  "Reassert Honor: when an enemy damages an ally within 5 feet of you, Advantage on your next attack roll against it before the end of your next turn."]},
    "magic-connoisseur-au": {
        "notes": ["Additional Spells: a level 1 and a level 2 spell from the list of your Magic Initiate cantrips; always prepared, "
                  "each cast once without a slot per Long Rest, with the same spellcasting ability.",
                  "Spell Change: when you gain a level you can swap one of them for another spell of the same level from that list."]},
    "mark-of-detection-efa": {
        "notes": _mark_notes("Deductive Intuition: add 1d4 to an Intelligence (Investigation) or Wisdom (Insight) check.",
                             "Magical Detection: Detect Magic and Detect Poison and Disease (and See Invisibility from character level 3) are always prepared, each cast once without a slot per Long Rest.",
                             "1 Detect Evil and Good, Identify; 2 Detect Thoughts, Find Traps; 3 Clairvoyance, Nondetection; 4 Arcane Eye, Divination; 5 Legend Lore")},
    "mark-of-finding-efa": {
        "notes": _mark_notes("Hunter's Intuition: add 1d4 to a Wisdom (Perception or Survival) check.",
                             "Finder's Magic: Hunter's Mark (and Locate Object from character level 3) is always prepared, cast once without a slot per Long Rest.",
                             "1 Faerie Fire, Longstrider; 2 Locate Animals or Plants, Mind Spike; 3 Clairvoyance, Speak with Plants; 4 Divination, Locate Creature; 5 Commune with Nature")},
    "mark-of-handling-efa": {
        "notes": _mark_notes("Wild Intuition: add 1d4 to an Intelligence (Nature) or Wisdom (Animal Handling) check.",
                             "Primal Connection: Animal Friendship and Speak with Animals are always prepared, each cast once without a slot per Long Rest; from character level 3 they can target a Monstrosity of Intelligence 3 or lower.",
                             "1 Command, Find Familiar; 2 Beast Sense, Calm Emotions; 3 Beacon of Hope, Conjure Animals; 4 Aura of Life, Dominate Beast; 5 Awaken")},
    "mark-of-healing-efa": {
        "notes": _mark_notes("Medical Intuition: add 1d4 to a Wisdom (Medicine) check or an ability check with a Herbalism Kit.",
                             "Healing Touch: Cure Wounds (and Lesser Restoration from character level 3) is always prepared, cast once without a slot per Long Rest.",
                             "1 False Life, Healing Word; 2 Arcane Vigor, Prayer of Healing; 3 Aura of Vitality, Mass Healing Word; 4 Aura of Life, Aura of Purity; 5 Greater Restoration")},
    "mark-of-hospitality-efa": {
        "notes": _mark_notes("Ever Hospitable: add 1d4 to a Charisma (Persuasion) check or an ability check with Brewer's Supplies or Cook's Utensils.",
                             "Innkeeper's Magic: Purify Food and Drink and Unseen Servant (and Calm Emotions from character level 3) are always prepared, each cast once without a slot per Long Rest.",
                             "1 Goodberry, Sleep; 2 Aid, Enhance Ability; 3 Create Food and Water, Leomund's Tiny Hut; 4 Aura of Purity, Mordenkainen's Private Sanctum; 5 Hallow")},
    "mark-of-making-efa": {
        "notes": _mark_notes("Artisan's Intuition: add 1d4 to an Intelligence (Arcana) check or an ability check with Artisan's Tools.",
                             "Spellsmith: Mending, and Magic Weapon always prepared and cast once without a slot per Long Rest.",
                             "1 Identify, Tenser's Floating Disk; 2 Continual Flame, Spiritual Weapon; 3 Conjure Barrage, Elemental Weapon; 4 Fabricate, Stone Shape; 5 Creation")},
    "mark-of-scribing-efa": {
        "notes": _mark_notes("Gifted Scribe: add 1d4 to an Intelligence (History) check or an ability check with Calligrapher's Supplies.",
                             "Scribe's Insight: Message, and Comprehend Languages (and Magic Mouth from character level 3) always prepared, each cast once without a slot per Long Rest.",
                             "1 Command, Illusory Script; 2 Animal Messenger, Silence; 3 Sending, Tongues; 4 Arcane Eye, Confusion; 5 Dream")},
    "mark-of-shadow-efa": {
        "notes": _mark_notes("Cunning Intuition: add 1d4 to a Dexterity (Stealth) or Charisma (Performance) check.",
                             "Shape Shadows: Minor Illusion, and Invisibility always prepared and cast once without a slot per Long Rest.",
                             "1 Disguise Self, Silent Image; 2 Darkness, Pass without Trace; 3 Clairvoyance, Major Image; 4 Greater Invisibility, Hallucinatory Terrain; 5 Mislead")},
    "mark-of-storm-efa": {
        "notes": _mark_notes("Windwright's Intuition: add 1d4 to a Dexterity (Acrobatics) check or an ability check with Navigator's Tools.",
                             "Storm's Boon: Resistance to Lightning damage (counted in the damage modifiers). Storm Magic: Thunderclap, and Gust of Wind from character level 3 (cast once without a slot per Long Rest).",
                             "1 Feather Fall, Fog Cloud; 2 Levitate, Shatter; 3 Sleet Storm, Wind Wall; 4 Conjure Minor Elementals, Control Water; 5 Conjure Elemental")},
    "mark-of-warding-efa": {
        "notes": _mark_notes("Warder's Intuition: add 1d4 to an Intelligence (Investigation) check or an ability check with Thieves' Tools.",
                             "Wards and Seals: Alarm and Mage Armor (and Arcane Lock from character level 3) always prepared, each cast once without a slot per Long Rest.",
                             "1 Armor of Agathys, Sanctuary; 2 Knock, Nystul's Magic Aura; 3 Glyph of Warding, Magic Circle; 4 Leomund's Secret Chest, Mordenkainen's Faithful Hound; 5 Antilife Shell")},
    "necromancy-adept-au": _adept("Necromancy", "1 Inflict Wounds; 2 Ray of Enfeeblement; 3 Vampiric Touch; 4 Blight; 5 Raise Dead",
                                  "Life Manipulation: when you cast a Necromancy spell with a slot, roll up to two unexpended Hit Point Dice "
                                  "and regain the total plus the slot's level in Hit Points (the dice are expended)."),
    "orders-resilience-frhof": {
        "notes": ["Resurge: when Prone you can right yourself with only 5 feet of movement.",
                  "Stronger Together: within 5 feet of an ally who is not Incapacitated, you both have Advantage on Strength saving throws."]},
    "otherworldly-familiar-au": {
        "notes": ["Otherworldly Power: when you cast Find Familiar, imbue it until you cast it again: Resistance to Necrotic, "
                  "Poison, Psychic, Radiant or Thunder damage (your choice), and it can move through creatures and objects as Difficult Terrain."]},
    "outlands-envoy-sato": {"data_only": True},
    "protection-xphb": {
        "notes": ["Reaction when a creature you see attacks a target other than you within 5 feet of you: interpose your "
                  "Shield to impose Disadvantage on that attack roll and all other attack rolls against the target until the "
                  "start of your next turn while you stay within 5 feet."]},
    "quicksmithing-psk": {
        "notes": ["Two 1st-level ritual spells from any class list mastered as effects (Intelligence); more can be added up to half your level rounded up ({(level+1)//2}), 2 hours and 50 gp per spell level.",
                  "Proficiency with quicksmith's tools; 1 hour and 10 gp builds a Tiny clockwork device (AC 5, 1 hp, up to three active, 24 hours)."]},
    "second-skin-rhw": {
        "notes": ["Alternate Form: Alter Self is always prepared and cast once without a slot per Long Rest, without Concentration.",
                  "Involuntary Change: roll on the Change Catalyst table when you take the feat; after the catalyst, a Charisma save, DC {13+pb}, "
                  "or you cast Alter Self at the start of your next turn (Stunned until then if the use is spent)."]},
    "servo-crafting-psk": {
        "notes": ["Cast Find Familiar as a ritual to create a servo; communicate and perceive through it on the same plane.",
                  "When you take the Attack action you can forgo one attack to let your servo make one attack."]},
    "shadow-touched-tce": {"data_only": True},
    "shadowmoor-hexer-lfl": {
        "notes": ["Hex is always prepared and cast once without a slot per Long Rest (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Curse Magic: a creature you cursed with Hex that hits you takes {pb} Psychic damage, once per turn."]},
    "soothing-familiar-au": {
        "notes": ["Healing Beacon: a 5-foot Emanation around your familiar (within 120 feet of you) lets allies in it treat a 1 or 2 on a healing die as a 3."]},
    "spellfire-adept-frhof": {
        "notes": ["Fueled Spellfire: once per turn when a spell deals Radiant damage, expend up to two Hit Point Dice and add the total to one damage roll.",
                  "Searing Spellfire: your Radiant damage rolls ignore Resistance to Radiant damage."]},
    "street-justice-frhof": {
        "notes": ["Headlock: your allies have Advantage on attack rolls against a creature Grappled by you.",
                  "Sturdy Knot: when you bind a creature with Chain, Manacles or Rope, add {pb} to the DC to escape or burst it.",
                  "Tough Talk: a Hostile attitude does not impose Disadvantage on your Charisma (Intimidation) checks to influence it."]},
    "strixhaven-initiate-scc": {"data_only": True},
    "svirfneblin-magic-mtf": {"data_only": True},
    "telekinetic-tce": {
        "notes": ["Mage Hand without verbal or somatic components, invisible hand (range +30 feet if you already know it); the increased ability is its spellcasting ability.",
                  "Bonus Action: telekinetically shove a creature you see within 30 feet; Strength save, DC {8+pb+inc_mod}, or it moves 5 feet toward or away from you."]},
    "telepathic-tce": {
        "notes": ["Speak telepathically to a creature you see within 60 feet, in a language you know (it cannot answer telepathically).",
                  "Detect Thoughts, cast once without a slot or components per long rest (the increased ability is the spellcasting ability)."]},
    "touch-of-death-rhw": {
        "notes": ["Death Touch: Chill Touch without components; its Necrotic damage ignores Resistance (Intelligence, Wisdom or Charisma, chosen with the feat).",
                  "Pull of the Grave: Disadvantage on Death Saving Throws."]},
    "transmutation-adept-au": _adept("Transmutation", "1 Jump; 2 Spider Climb; 3 Slow; 4 Polymorph; 5 Animate Objects",
                                     "Magical Augmentation: on your turn when you cast a Transmutation spell with a slot, your Speed rises by 5 feet "
                                     "per level of the slot until the end of the turn."),
    "treacherous-allure-abh": {
        "notes": ["Enchanting Presence: Charm Person is always prepared and cast once without a slot per Long Rest.",
                  "Inevitable Betrayal: Advantage on attack rolls against Charmed creatures."]},
    "tyro-of-the-gauntlet-frhof": {
        "notes": ["Stand as One: Reaction to prevent an ally within 5 feet (not Incapacitated) from being pushed or pulled.",
                  "Vigilant: when you take the Ready action, the next attack roll against you before the start of your next turn has Disadvantage."]},
    "vampire-touched-abh": {
        "notes": ["Vampire Magic: a level 1 Enchantment or Illusion spell and Spider Climb (on yourself) are always prepared and each cast once without a slot per Long Rest."]},
    "vigor-of-the-hill-giant-bgg": {
        "notes": ["Bulwark: Reaction when an effect would move you at least 5 feet or knock you Prone: you are not moved and not Prone.",
                  "Iron Stomach: when you eat food during a short rest and spend Hit Dice, you regain {con_mod+pb} extra Hit Points."]},
    "warlike-familiar-au": {
        "notes": ["Battle Familiar is always prepared and cast once without a slot per Long Rest.",
                  "Intercept Attack: your familiar's Reaction adds +{pb} to the Armor Class of a creature within 5 feet of it against one attack."]},
    "watchers-rhw": {
        "notes": ["Borrowed Eyes: Beast Sense and Speak with Animals are always prepared, each cast once without a slot per Long Rest.",
                  "Heightened Suspicion: when you take the Search action, add 1d4 to the ability checks of that action.",
                  "Incessant Watchers: Disadvantage on saves against Scrying; after you roll a 1 on a D20 Test, a Wisdom save, DC {13+pb}, or Disadvantage on D20 Tests for 1 minute."]},
    "wood-elf-magic-xge": {"data_only": True},
    "zhentarim-ruffian-frhof": {
        "notes": ["Exploit Opening: roll an Opportunity Attack's damage dice twice and use either roll.",
                  "Family First: if you have Heroic Inspiration when you roll Initiative, expend it to give yourself and your allies Advantage on that roll."]},
    "zhentarim-tactics-frhof": {
        "notes": ["Retaliate: right after a creature within 5 feet hits you with a melee attack, make an Opportunity Attack against it.",
                  "Versatile Merc: after a Long Rest choose a skill you are proficient in; you have Expertise in it until your next Long Rest (a choice that lasts one rest: note it at the table)."]},
})

TAIL_QUOTES.update({
    "aberrant-anatomy-rhw": ("You can hold your breath for 1 hour.", "DC 13 plus your Proficiency"),
    "aberrant-dragonmark-erlw": ("Once you cast it, you must finish a short or long rest before you can cast it again through the mark.",
                                 "If you roll an even number, you gain a number of temporary hit points equal to the number rolled."),
    "ability-score-improvement-xphb": "This feat can't increase an ability score above 20.",
    "abjuration-adept-au": "gains Temporary Hit Points equal to twice the level of spell slot expended",
    "adept-of-the-black-robes-dsotdq": "The damage that the creature takes increases by an amount equal to that total.",
    "adept-of-the-white-robes-dsotdq": "Roll a number of d6s equal to the level of the spell slot expended",
    "arcane-eloquence-au": "you can roll 1d4 and add the number rolled to the ability check",
    "arcane-warrior-au": "Whenever you gain a level, you can replace one of these cantrips with another Wizard cantrip.",
    "artificer-initiate-tce": "you can use that type of tool as a spellcasting focus for any spell you cast that uses Intelligence as its spellcasting ability",
    "blessed-warrior-xphb": "The chosen cantrips count as Paladin spells for you, and Charisma is your spellcasting ability for them.",
    "boon-of-blazing-dawn-abh": "You have Immunity to Radiant damage.",
    "boon-of-bloodshed-frhof": "you can deal extra damage to the target equal to your Proficiency",
    "boon-of-bountiful-health-frhof": "increase the number of Temporary Hit Points you gain by 5",
    "boon-of-combat-prowess-xphb": "When you miss with an attack roll, you can hit instead.",
    "boon-of-communication-frhof": "You gain telepathy with a range of 120 feet.",
    "boon-of-desperate-resilience-frhof": "While you are Bloodied, you have Resistance to every damage type except Force.",
    "boon-of-dimensional-travel-xphb": "you can teleport up to 30 feet to an unoccupied space you can see",
    "boon-of-fortunes-favor-frhof": "When you fail a saving throw, you can reroll it and must use the new roll.",
    "boon-of-looming-shadows-abh": "your reach for your Melee weapon attacks increases by 10 feet until the end of your turn",
    "boon-of-magic-school-mastery-au": "you must choose a different school of magic each time",
    "boon-of-poison-mastery-frhof": "You have Immunity to Poison damage and the Poisoned condition.",
    "boon-of-revelry-frhof": "taking damage doesn't break your Concentration on it",
    "boon-of-siberys-efa": ("Choose a level 8 or lower spell from the", "a spell from the Siberys Dragonmark Spells table"),
    "boon-of-spell-recall-xphb": "roll 1d4. If the number you roll is the same as the slot's level, the slot isn't expended",
    "boon-of-the-bright-sun-frhof": "you and allies you can see in your Daylight Presence gain 10 Temporary Hit Points",
    "boon-of-the-furious-storm-frhof": "While you are Bloodied, you have Immunity to Lightning and Thunder damage.",
    "boon-of-the-iron-mind-au": "you lose Concentration only if you cast a spell or activate another effect that requires Concentration",
    "boon-of-the-night-spirit-xphb": "you have Resistance to all damage except Psychic and Radiant",
    "boon-of-truesight-xphb": "You have Truesight with a range of 60 feet.",
    "bountiful-luck-xge": "you can use your reaction to let the ally reroll the die",
    "cartomancer-bmt": "The card then immediately loses its magic.",
    "chef-tce": ("You can prepare enough of this food for a number of creatures equal to 4 + your proficiency bonus.",
                 "you can cook a number of treats equal to your proficiency bonus"),
    "child-of-the-sun-lfl": "taking damage can't break your Concentration on the spell",
    "cloying-mists-abh": "creatures other than you and your allies have their Speed reduced by 5 feet",
    "cohort-of-chaos-sato": "When you roll a 1 or a 20 on an attack roll or a saving throw, the magic of chaos flows through you.",
    "cold-caster-frhof": "The creature subtracts 1d4 from the next saving throw it makes before the end of your next turn.",
    "conjuration-adept-au": "This bonus is equal to the ability modifier of the score increased by this feat.",
    "divinely-favored-dsotdq": "you can use a holy symbol as a spellcasting focus for any spell you cast that uses the spellcasting ability you choose",
    "dragon-fear-xge": "(8 + your proficiency bonus + your Charisma modifier)",
    "drow-high-magic-xge": "Charisma is your spellcasting ability for all three spells.",
    "druidic-warrior-xphb": "Whenever you gain a Ranger level, you can replace one of these cantrips with another Druid cantrip.",
    "dwarven-fortitude-xge": "add your Constitution modifier, and regain a number of hit points equal to the total (minimum of 1)",
    "elemental-familiar-au": "Your familiar has Resistance to the chosen damage type.",
    "emerald-enclave-fledgling-frhof": "This movement doesn't provoke Opportunity Attacks.",
    "enchantment-adept-au": "you can cast it without any Verbal, Somatic, or Material components",
    "enclave-magic-frhof": "it doesn't require Concentration",
    "evocation-adept-au": "you can roll up to two of your unexpended Hit Point Dice and add the total rolled to one of the spell's damage rolls",
    "fey-teleportation-xge": "You learn to speak, read, and write Sylvan.",
    "fey-touched-tce": "The spells' spellcasting ability is the ability increased by this feat.",
    "flames-of-phlegethos-xge": "any creature within 5 feet of you that hits you with a melee attack takes 1d4 fire damage",
    "greater-mark-of-detection-efa": "That creature also gains the benefits of the spell for its duration.",
    "greater-mark-of-finding-efa": "the range of the spell is doubled",
    "greater-mark-of-making-efa": "you cast the spell as its level 3 version",
    "greater-mark-of-passage-efa": "Each target can then take a Reaction to also teleport up to 30 feet to an unoccupied space it can see.",
    "greater-mark-of-sentinel-efa": "you can also make one attack with a weapon or an Unarmed Strike as part of that same Reaction",
    "greater-mark-of-shadow-efa": "you cast the spell as its level 3 version",
    "greater-mark-of-storm-efa": "you also gain a Fly Speed of 60 feet for the duration of the spell",
    "harper-teamwork-frhof": "That condition immediately ends for that ally.",
    "illusion-adept-au": "creatures have Disadvantage on Intelligence (Investigation) checks made to discern the true nature of illusions created by your spells",
    "infernal-constitution-xge": "You have advantage on saving throws against being poisoned.",
    "initiate-of-high-sorcery-dsotdq": "Your spellcasting ability for this feat's spells is Intelligence, Wisdom, or Charisma (choose when you select this feat).",
    "interception-xphb": "reduce the damage dealt to the target by 1d10 plus your Proficiency",
    "lords-alliance-agent-frhof": "you have Advantage on your next attack roll against that enemy before the end of your next turn",
    "magic-connoisseur-au": "Whenever you gain a new level, you can replace one of the spells you chose for this feat with a different spell of the same level",
    "mark-of-detection-efa": "When you reach character level 3, you also always have the See Invisibility spell prepared and can cast it the same way.",
    "mark-of-finding-efa": "When you reach character level 3, you also always have the Locate Object spell prepared and can cast it the same way.",
    "mark-of-handling-efa": "you can target a Monstrosity when you cast Animal Friendship or Speak with Animals if the creature's Intelligence score is 3 or lower",
    "mark-of-healing-efa": "When you reach character level 3, you also always have the Lesser Restoration spell prepared and can cast it the same way.",
    "mark-of-hospitality-efa": "When you reach character level 3, you also always have the Calm Emotions spell prepared and can cast it the same way.",
    "mark-of-making-efa": "You know the Mending cantrip.",
    "mark-of-scribing-efa": "When you reach character level 3, you also always have the Magic Mouth spell prepared and can cast it the same way.",
    "mark-of-shadow-efa": "You know the Minor Illusion cantrip.",
    "mark-of-storm-efa": "You have Resistance to Lightning damage.",
    "mark-of-warding-efa": "When you reach character level 3, you also always have the Arcane Lock spell prepared and can cast it the same way.",
    "necromancy-adept-au": "You regain Hit Points equal to the total rolled plus the level of spell slot expended.",
    "orders-resilience-frhof": "you and that ally have Advantage on Strength saving throws",
    "otherworldly-familiar-au": "Your familiar can move through other creatures and objects as if they were Difficult Terrain.",
    "outlands-envoy-sato": "When you cast tongues using this feat, you require no material components.",
    "protection-xphb": "You impose Disadvantage on the triggering attack roll and all other attack rolls against the target until the start of your next turn if you remain within 5 feet of the target.",
    "quicksmithing-psk": "The spell's level can be no higher than half your level (rounded up), and it must have the ritual tag.",
    "second-skin-rhw": "DC 13 plus your Proficiency",
    "servo-crafting-psk": "you can forgo one of your own attacks to allow your servo familiar to make one attack of its own",
    "shadow-touched-tce": "The spells' spellcasting ability is the ability increased by this feat.",
    "shadowmoor-hexer-lfl": "the creature takes Psychic damage equal to your Proficiency",
    "soothing-familiar-au": "that ally can treat a roll of 1 or 2 on the die as a 3",
    "spellfire-adept-frhof": "it ignores Resistance to Radiant damage",
    "street-justice-frhof": "add your Proficiency Bonus to the DC to escape or burst the Chain, Manacles, or Rope",
    "strixhaven-initiate-scc": "You can cast the chosen 1st-level spell without a spell slot, and you must finish a long rest before you can cast it in this way again.",
    "svirfneblin-magic-mtf": "Intelligence is your spellcasting ability for these spells, and you cast them at their lowest possible levels.",
    "telekinetic-tce": "the target must succeed on a Strength saving throw (8 + your proficiency bonus + the ability modifier of the score increased by this feat)",
    "telepathic-tce": "You can speak telepathically to any creature you can see within 60 feet of you.",
    "touch-of-death-rhw": "You have Disadvantage on Death Saving Throws.",
    "transmutation-adept-au": "your Speed increases by a number of feet equal to five times the level of spell slot expended",
    "treacherous-allure-abh": "You have Advantage on attack rolls against creatures with the Charmed condition.",
    "tyro-of-the-gauntlet-frhof": "the next attack roll made against you has Disadvantage before the start of your next turn",
    "vampire-touched-abh": "You always have that spell and the Spider Climb spell prepared.",
    "vigor-of-the-hill-giant-bgg": "you regain additional hit points equal to your Constitution modifier + your proficiency bonus",
    "warlike-familiar-au": "The bonus is equal to your Proficiency Bonus.",
    "watchers-rhw": "You have Disadvantage on saving throws made against the Scrying spell.",
    "wood-elf-magic-xge": "Wisdom is your spellcasting ability for all three spells.",
    "zhentarim-ruffian-frhof": "you can roll the damage dice twice and use either roll against the target",
    "zhentarim-tactics-frhof": "You have Expertise in that skill until you finish your next Long Rest.",
})

# ------------------------------------------------------------------------------------------- completion
# Benefits of feats that earlier slices classified for their number (Alert, Tough, speed, ...) but whose other text
# was never written down. They are appended to the existing entries by ``feat_effects_data``.
COMPLETION: dict[str, dict] = {
    "alert-phb": {"notes": ["You cannot be surprised while you are conscious, and hidden attackers gain no Advantage against you."]},
    "alert-xphb": {"notes": ["Initiative Swap: right after you roll Initiative you can swap it with a willing ally's (neither of you Incapacitated)."]},
    "athlete-xphb": {"notes": ["Hop Up: when Prone you stand with only 5 feet of movement.",
                               "Jumping: a running Long Jump or High Jump after only 5 feet of movement."]},
    "boon-of-fortitude-xphb": {"notes": ["Whenever you regain Hit Points you can regain {con_mod} extra Hit Points, once until the start of your next turn."]},
    "boon-of-speed-xphb": {"notes": ["Escape Artist: a Bonus Action to take the Disengage action, which also ends the Grappled condition on you."]},
    "keen-mind-xphb": {"notes": ["Quick Study: take the Study action as a Bonus Action."]},
    "keenness-of-the-stone-giant-bgg": {
        "notes": ["Stone Throw (Bonus Action): a ranged spell attack within 60 feet using the increased ability; on a hit 1d10 "
                  "force damage and a Strength save, DC {8+pb+inc_mod}, or the target falls Prone."],
        "resources": [_res("Stone Throw", "pb", "long", "Bonus Action ranged spell attack, 1d10 force damage.")]},
    "mark-of-passage-efa": {
        "notes": ["Intuitive Motion: add 1d4 to a Strength (Athletics) or Dexterity (Acrobatics) check.",
                  "Magical Passage: Misty Step is always prepared and cast once without a slot per Long Rest.",
                  "Spells of the Mark (added to a Spellcasting or Pact Magic spell list): 1 Expeditious Retreat, Jump; 2 Find Steed, "
                  "Pass without Trace; 3 Blink, Phantom Steed; 4 Dimension Door, Freedom of Movement; 5 Teleportation Circle."]},
    "mobile-phb": {"notes": ["Dash ignores Difficult Terrain for that turn; a creature you make a melee attack against cannot make Opportunity Attacks against you for the rest of the turn."]},
    "observant-xphb": {"notes": ["Quick Search: take the Search action as a Bonus Action."]},
    "speedy-xphb": {"notes": ["Dash ignores Difficult Terrain for the rest of the turn; Opportunity Attacks against you have Disadvantage."]},
    "squat-nimbleness-xge": {"notes": ["Proficiency in Acrobatics or Athletics (your choice); Advantage on Athletics or Acrobatics checks to escape a grapple."]},
    "transmuted-anatomy-au": {
        "notes": ["Resilient Anatomy: Advantage on saves against effects that force you to shape-shift; Reaction when you fail a "
                  "Constitution save: add 1d4 to the save."],
        "resources": [_res("Resilient Anatomy", "pb", "long", "Reaction: add 1d4 to a failed Constitution save.")]},
}

COMPLETION_QUOTES: dict[str, str | tuple[str, ...]] = {
    "alert-phb": "You can't be surprised while you are conscious.",
    "alert-xphb": "you can swap your Initiative with the Initiative of one willing ally in the same combat",
    "athlete-xphb": "You can make a running Long or High Jump after moving only 5 feet.",
    "boon-of-fortitude-xphb": "whenever you regain Hit Points, you can regain additional Hit Points equal to your Constitution modifier",
    "boon-of-speed-xphb": "you can take the Disengage action, which also ends the Grappled condition on you",
    "keen-mind-xphb": "You can take the Study action as a Bonus Action.",
    "keenness-of-the-stone-giant-bgg": ("You can use this bonus action a number of times equal to your proficiency bonus",
                                        "the rock deals 1d10 force damage"),
    "mark-of-passage-efa": "When you make a Strength (Athletics) or Dexterity (Acrobatics) check, you can roll 1d4 and add the number rolled to the ability check.",
    "mobile-phb": "you don't provoke opportunity attacks from that creature for the rest of the turn, whether you hit or not",
    "observant-xphb": "You can take the Search action as a Bonus Action.",
    "speedy-xphb": "Opportunity Attacks have Disadvantage against you.",
    "squat-nimbleness-xge": "You gain proficiency in the Acrobatics or Athletics skill (your choice).",
    "transmuted-anatomy-au": ("You have Advantage on saving throws against effects that would compel you to shape-shift against your will.",
                              "You can use this benefit a number of times equal to your Proficiency"),
}
