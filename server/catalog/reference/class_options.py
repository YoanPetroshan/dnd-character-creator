"""X2 recharge upgrades, invocation effects, class option choices, languages, expertise.

Split from catalog/reference_data.py (S17); the text below is moved unchanged.
"""
from __future__ import annotations
from .core_tables import LANGUAGES
from .subclass_tail_2014_w8b import _w8_res
from .subclass_tail_2014_w8d import SUBCLASS_TAIL_2014_BOOKS
from .resource_tail_2024 import RESOURCE_TAIL_2024, SUBCLASS_TAIL_2024
from .resource_tail_2014 import RESOURCE_TAIL_2014, SUBCLASS_TAIL_2014

ZEALOT_WARRIOR_DICE_2024 = ((3, 4), (6, 5), (12, 6), (17, 7))

# Land Druid Land's Aid: 2d6, "The damage and healing increase by 1d6 when you reach Druid levels 10 (3d6) and 14 (4d6)."
# (class level, d6 count), pinned against land-xphb-3-lands-aid.
LANDS_AID_DICE_2024 = ((3, 2), (10, 3), (14, 4))

# Wizard Signature Spells (XPHB, level 20), built from the picked spells, not from a table row: "Choose two level
# 3 spells in your spellbook as your signature spells. You always have these spells prepared, and you can cast
# each of them once at level 3 without expending a spell slot. When you do so, you can't cast them in this way
# again until you finish a Short or Long Rest."
SIGNATURE_SPELLS_2024 = {"feature": "xphb-wizard-20-signature-spells", "choice": "class:wizard:20:signature-spells",
                         "recharge": "short-or-long"}

# Arcane Recovery (SRD `arcane-recovery`, XPHB Arcane Recovery): "combined level ... no more
# than half your Wizard level (round up), and none of the slots can be level 6 or higher".
ARCANE_RECOVERY_MAX_SLOT_LEVEL = 5

# ---- X2: per-turn / per-combat / per-rage limits of class and subclass features -------------------------------------
# Rows that were note-only (`uses` None, `recharge` None) although the catalog text limits the feature's main effect to
# "once per turn" / "only once per rage": X2 sets `uses` 1 and the recharge and appends the pinned sentence to the row's
# quotes when no quote has it yet. (table, subclass or None, feature id, name, recharge, sentence); the sentences are
# pinned against catalog.features by tests/test_x2_turn_combat_rage_recharges.py.
_DIVINE_STRIKE_SENTENCE = "Once on each of your turns when you hit a creature with a weapon attack"
X2_RECHARGE_UPGRADES: tuple[tuple, ...] = (
    ("RESOURCE_TAIL_2014", None, "foe-slayer", "Foe Slayer", "turn",
     "Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll"),
    ("RESOURCE_TAIL_2024", None, "xphb-monk-5-stunning-strike", "Stunning Strike", "turn",
     "Once per turn when you hit a creature with a Monk weapon or an Unarmed Strike"),
    ("SUBCLASS_TAIL_2014", "life", "divine-strike", "Divine Strike (Life Domain)", "turn", _DIVINE_STRIKE_SENTENCE),
) + tuple(
    ("SUBCLASS_TAIL_2014_BOOKS", sub, f"{sub}-8-divine-strike", f"Divine Strike ({dom} Domain)", "turn", _DIVINE_STRIKE_SENTENCE)
    for sub, dom in (("forge-xge", "Forge"), ("nature-phb", "Nature"), ("order-tce", "Order"), ("solidarity-psa", "Solidarity"),
                     ("strength-psa", "Strength"), ("tempest-phb", "Tempest"), ("trickery-phb", "Trickery"),
                     ("twilight-tce", "Twilight"), ("war-phb", "War"), ("zeal-psa", "Zeal"))
) + (
    ("SUBCLASS_TAIL_2014_BOOKS", "death-dmg", "death-dmg-8-divine-strike", "Divine Strike (Death Domain)", "turn",
     "Once on each of the cleric's turns when he or she hits a creature with a weapon attack"),
    ("SUBCLASS_TAIL_2014_BOOKS", "order-tce", "order-tce-17-orders-wrath", "Order's Wrath", "turn",
     "You can curse a creature in this way only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "cavalier-xge", "cavalier-xge-15-ferocious-charger", "Ferocious Charger", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "kensei-xge", "kensei-xge-6-one-with-the-blade", "Deft Strike", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "mercy-tce", "mercy-tce-3-hand-of-harm", "Hand of Harm", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "fey-wanderer-tce", "fey-wanderer-tce-3-dreadful-strikes", "Dreadful Strikes", "turn",
     "which can take this extra damage only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "swarmkeeper-tce", "swarmkeeper-tce-3-gathered-swarm", "Gathered Swarm", "turn",
     "Once on each of your turns, you can cause the swarm to assist you"),
    ("SUBCLASS_TAIL_2014_BOOKS", "divine-soul-xge", "divine-soul-xge-6-empowered-healing", "Empowered Healing", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "genie-tce", "genie-tce-1-genies-vessel", "Genie's Wrath", "turn",
     "Once during each of your turns when you hit with an attack roll"),
    ("SUBCLASS_TAIL_2014_BOOKS", "necromancy-phb", "necromancy-phb-2-grim-harvest", "Grim Harvest", "turn",
     "Once per turn when you kill one or more creatures with a spell of 1st level or higher"),
    ("SUBCLASS_TAIL_2014_BOOKS", "zealot-xge", "zealot-xge-6-fanatical-focus", "Fanatical Focus", "rage",
     "You can use this ability only once per rage"),
)


def _x2_upgrade(table_name: str, sub: str | None, feature: str, name: str, recharge: str, sentence: str) -> None:
    rows = list(globals()[table_name])
    hits = [i for i, row in enumerate(rows) if row["feature"] == feature and row["name"] == name
            and (sub is None or row.get("subclass") == sub)]
    assert len(hits) == 1, (table_name, feature, name)
    row = rows[hits[0]]
    assert row["uses"] is None and row["recharge"] is None, (feature, name)
    quotes = tuple(row["quotes"])
    if not any(sentence in quote for _fid, quote in quotes):
        quotes += ((feature, sentence),)
    rows[hits[0]] = {**row, "uses": 1, "recharge": recharge, "quotes": quotes}
    globals()[table_name] = tuple(rows)


# New rows (features the W6-W8 / RP11 scans skipped as "once per turn, no number"), appended to the tables.
SUBCLASS_TAIL_2014_BOOKS = SUBCLASS_TAIL_2014_BOOKS + (
    _w8_res("samurai-xge", "fighter", "samurai-xge-15-rapid-strike", "Rapid Strike", 1, "turn",
            "If you take the Attack action on your turn and have advantage on an attack roll against one of the targets, "
            "forgo the advantage for that roll to make an additional weapon attack against that target as part of the same "
            "action; once per turn",
            ((None, "you can forgo the advantage for that roll to make an additional weapon attack against that target, as part of the same action"),
             (None, "You can do so no more than once per turn"))),
    _w8_res("kensei-xge", "monk", "kensei-xge-17-unerring-accuracy", "Unerring Accuracy", 1, "turn",
            "If you miss with an attack roll using a monk weapon on your turn, you can reroll it; once on each of your turns",
            ((None, "If you miss with an attack roll using a monk weapon on your turn, you can reroll it"),
             (None, "You can use this feature only once on each of your turns"))),
    _w8_res("gloom-stalker-xge", "ranger", "gloom-stalker-xge-11-stalkers-flurry", "Stalker's Flurry", 1, "turn",
            "Once on each of your turns when you miss with a weapon attack, make another weapon attack as part of the same action",
            ((None, "Once on each of your turns when you miss with a weapon attack, you can make another weapon attack as part of the same action"),)),
    _w8_res("wild-phb", "sorcerer", "wild-phb-18-spell-bombardment", "Spell Bombardment", 1, "turn",
            "When you roll damage for a spell and roll the highest number possible on any of the dice, choose one of those "
            "dice, roll it again and add that roll to the damage; once per turn",
            ((None, "When you roll damage for a spell and roll the highest number possible on any of the dice, choose one of those dice, roll it again and add that roll to the damage"),
             (None, "You can use the feature only once per turn"))),
)

SUBCLASS_TAIL_2024 = SUBCLASS_TAIL_2024 + (
    {"subclass": "fey-wanderer-xphb", "class": "ranger", "feature": "fey-wanderer-xphb-3-dreadful-strikes",
     "name": "Dreadful Strikes", "uses": 1, "recharge": "turn",
     "note": "When you hit a creature with a weapon you can deal an extra 1d4 Psychic damage (1d6 from Ranger level 11); a "
             "creature can take it only once per turn",
     "quotes": (("fey-wanderer-xphb-3-dreadful-strikes", "you can deal an extra 1d4 Psychic damage to the target"),
                ("fey-wanderer-xphb-3-dreadful-strikes", "which can take this extra damage only once per turn"),
                ("fey-wanderer-xphb-3-dreadful-strikes", "The extra damage increases to 1d6 when you reach Ranger level 11"))},
    {"subclass": "celestial-xphb", "class": "warlock", "feature": "celestial-xphb-6-radiant-soul",
     "name": "Radiant Soul", "uses": 1, "recharge": "turn",
     "note": "Once per turn, when a spell you cast deals Radiant or Fire damage, add your Charisma modifier ({cha:+d}) to "
             "that spell's damage against one of its targets",
     "quotes": (("celestial-xphb-6-radiant-soul", "Once per turn, when a spell you cast deals Radiant or Fire damage"),
                ("celestial-xphb-6-radiant-soul", "you can add your Charisma modifier to that spell's damage against one of the spell's targets"))},
    {"subclass": "hunter-xphb", "class": "ranger", "feature": "hunter-xphb-11-superior-hunters-prey",
     "name": "Superior Hunter's Prey", "uses": 1, "recharge": "turn",
     "note": "Once per turn when you deal damage to a creature marked by your Hunter's Mark, also deal that spell's extra "
             "damage to a different creature you can see within 30 feet of the first",
     "quotes": (("hunter-xphb-11-superior-hunters-prey", "Once per turn when you deal damage to a creature marked by your Hunter's Mark"),
                ("hunter-xphb-11-superior-hunters-prey", "you can also deal that spell's extra damage to a different creature that you can see within 30 feet of the first creature"))},
    {"subclass": "world-tree-xphb", "class": "barbarian", "feature": "world-tree-xphb-14-travel-along-the-tree",
     "name": "Travel Along the Tree", "uses": 1, "recharge": "rage",
     "note": "When you activate your Rage and as a Bonus Action while it is active, teleport up to 60 feet to an unoccupied "
             "space you can see; once per Rage the range is 150 feet and you can bring up to six willing creatures within "
             "10 feet of you",
     "quotes": (("world-tree-xphb-14-travel-along-the-tree", "you can teleport up to 60 feet to an unoccupied space you can see"),
                ("world-tree-xphb-14-travel-along-the-tree", "once per Rage, you can increase the range of that teleport to 150 feet"),
                ("world-tree-xphb-14-travel-along-the-tree", "you can also bring up to six willing creatures who are within 10 feet of you"))},
)

for _args in X2_RECHARGE_UPGRADES:
    _x2_upgrade(*_args)
del _args

# Bard Font of Inspiration (SRD `font-of-inspiration`, XPHB): short rest recharge from level 5.
FONT_OF_INSPIRATION_LEVEL = 5


# ---- Subclass resources (R6) -------------------------------------------------
# All first features of these subclasses are at fighter/rogue level 3.
SUBCLASS_RESOURCE_MIN_LEVEL = 3

# Psi Warrior / Soulknife, TCE (2014) `*-tce-3-psionic-power`: "a number of these dice equal
# to twice your proficiency bonus"; the die is d6 and "increases: at 5th level (d8), 11th
# level (d10), and 17th level (d12)". (class level, die), ascending. The XPHB version is a
# class-level table (catalog.subclass_2024_tables), not this formula.
PSIONIC_DICE_PB_MULTIPLIER_2014 = 2
PSIONIC_DIE_BY_LEVEL_2014 = [(3, "d6"), (5, "d8"), (11, "d10"), (17, "d12")]

# Battle Master superiority dice (PHB `combat-superiority`, `improved-combat-superiority`;
# XPHB identical): four d8, "another superiority die at 7th level and one more at 15th";
# d10 at 10, d12 at 18 (XPHB "Improved"/"Ultimate Combat Superiority"). Ascending by level.
SUPERIORITY_DICE_COUNT = [(3, 4), (7, 5), (15, 6)]
SUPERIORITY_DIE_BY_LEVEL = [(3, "d8"), (10, "d10"), (18, "d12")]
# Maneuver save DC = 8 + proficiency bonus + STR or DEX modifier (PHB abilityDc str/dex,
# XPHB "your choice"): the better one is used.
MANEUVER_DC_BASE = 8

# Arcane Archer (XGE `arcane-shot`): "You have two uses of this ability, and you regain all
# expended uses of it when you finish a short or long rest."
ARCANE_SHOT_USES = 2


# ---- Eldritch Invocation effects (R8, SRD set) ------------------------------
# Keyed by SRD feature id. Every entry was checked against the SRD feature text
# and the SRD spell ids (tests/test_invocation_effects.py re-checks them).
# Keys: innate_spell {spell, uses "at-will" | "1/long rest", level} (CHA, source
# "Eldritch Invocation"); skills; ac_formula (same shape as CLASS_FEATURE_EFFECTS,
# decision D6); senses (devilsSight, not darkvision); resource_bonus (Agonizing
# Blast, CHA mod); note (text-only effects). "Once using a warlock spell slot ...
# until you finish a long rest" -> "1/long rest" at the spell's own level.
_INV = "eldritch-invocation-"


def _at_will(spell: str, level: int) -> dict:
    return {"innate_spell": {"spell": spell, "uses": "at-will", "level": level}}


def _once(spell: str, level: int) -> dict:
    return {"innate_spell": {"spell": spell, "uses": "1/long rest", "level": level}}


INVOCATION_EFFECTS: dict[str, dict] = {
    _INV + "armor-of-shadows": {
        **_at_will("mage-armor", 1),
        "ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True},
    },
    _INV + "ascendant-step": _at_will("levitate", 2),
    _INV + "beast-speech": _at_will("speak-with-animals", 1),
    _INV + "eldritch-sight": _at_will("detect-magic", 1),
    _INV + "fiendish-vigor": _at_will("false-life", 1),
    _INV + "mask-of-many-faces": _at_will("disguise-self", 1),
    _INV + "misty-visions": _at_will("silent-image", 1),
    _INV + "otherworldly-leap": _at_will("jump", 1),
    _INV + "master-of-myriad-forms": _at_will("alter-self", 2),
    _INV + "whispers-of-the-grave": _at_will("speak-with-dead", 3),
    _INV + "visions-of-distant-realms": _at_will("arcane-eye", 4),
    # At will, but "finish a long rest before you can use this invocation on the same creature again".
    _INV + "chains-of-carceri": {
        **_at_will("hold-monster", 5),
        "note": "Only against a celestial, fiend or elemental; once per creature per long rest.",
    },
    _INV + "thief-of-five-fates": _once("bane", 1),
    _INV + "mire-the-mind": _once("slow", 3),
    _INV + "sign-of-ill-omen": _once("bestow-curse", 3),
    _INV + "bewitching-whispers": _once("compulsion", 4),
    _INV + "dreadful-word": _once("confusion", 4),
    _INV + "sculptor-of-flesh": _once("polymorph", 4),
    _INV + "minions-of-chaos": _once("conjure-elemental", 5),
    _INV + "beguiling-influence": {"skills": ["skill-deception", "skill-persuasion"]},
    _INV + "devils-sight": {"senses": {"devilsSight": 120}},
    _INV + "agonizing-blast": {"resource_bonus": {"name": "Agonizing Blast", "ability": "CHA", "spell": "eldritch-blast"}},
    _INV + "thirsting-blade": {"note": "Attack with your pact weapon twice, instead of once, when you take the Attack action."},
    _INV + "repelling-blast": {"note": "When eldritch blast hits a creature, you can push it up to 10 feet away from you in a straight line."},
    _INV + "book-of-ancient-secrets": {"note": "Two 1st-level ritual spells in your Book of Shadows (the ritual book itself is not modelled)."},
}


# ---- XPHB (2024) Eldritch Invocation effects (C7b) ---------------------------------------------
# Keyed by the XPHB feature id `opt-<slug>-xphb`. Holds ONLY what the imported record does not carry:
# innate spells (with frequency) and senses come from the record itself (class_choices_2024.invocation_effect).
# Texts read from catalog.features on 2026-10-10 (tests/test_invocation_effects_2024.py re-checks them).
# Keys as INVOCATION_EFFECTS, plus swim_equals_walk. Notes may use {cha_names} (max(1, CHA modifier)) and
# {spear_range} (30 x Warlock level); they are formatted by class_resources._warlock (resource notes) only.
# E6: Pact of the Chain's data says "ritual", the text "cast it as a Magic action without expending a spell
# slot", so it is an at-will innate entry (the engine maps "ritual" to at-will) with the note below.
# Not here (C7c): Pact of the Tome, Lessons of the First Ones.
_XPHB_INV = "opt-{}-xphb"
INVOCATION_EFFECTS_2024: dict[str, dict] = {
    _XPHB_INV.format("armor-of-shadows"): {"ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True}},
    _XPHB_INV.format("devils-sight"): {"senses": {"devilsSight": 120}},
    _XPHB_INV.format("gift-of-the-depths"): {
        "swim_equals_walk": True, "note": "You can breathe underwater and have a Swim Speed equal to your Speed."},
    _XPHB_INV.format("eldritch-mind"): {"note": "Advantage on Constitution saving throws to maintain Concentration."},
    _XPHB_INV.format("fiendish-vigor"): {
        "note": "On yourself; you don't roll the die for the Temporary Hit Points, you get the highest number on the die."},
    _XPHB_INV.format("one-with-shadows"): {
        "note": "On yourself, while you are in an area of Dim Light or Darkness."},
    _XPHB_INV.format("pact-of-the-chain"): {
        "note": "Magic action, no spell slot. Special forms: Imp, Pseudodragon, Quasit, Skeleton, Slaad Tadpole, "
                "Sphinx of Wonder, Sprite, Venomous Snake. When you take the Attack action you can forgo one of your "
                "attacks so the familiar attacks with its Reaction."},
    _XPHB_INV.format("pact-of-the-blade"): {
        "note": "Bonus Action: conjure a pact weapon (Simple or Martial Melee) or bond with a magic weapon you touch. "
                "You are proficient with it and can use it as a Spellcasting Focus. Attack and damage rolls can use "
                "Charisma, and it can deal Necrotic, Psychic or Radiant damage or its normal type."},
    _XPHB_INV.format("thirsting-blade"): {
        "note": "Extra Attack with your pact weapon only: attack twice instead of once with the Attack action. "
                "It doesn't give additional attacks if you also have Extra Attack (PHB 2024 Multiclassing)."},
    _XPHB_INV.format("devouring-blade"): {"note": "The Extra Attack of Thirsting Blade confers two extra attacks rather than one."},
    _XPHB_INV.format("eldritch-smite"): {
        "note": "Once per turn on a pact weapon hit: expend a Pact Magic slot for an extra 1d8 Force damage plus 1d8 per "
                "slot level; the target is Prone if Huge or smaller."},
    _XPHB_INV.format("lifedrinker"): {
        "note": "Once per turn on a pact weapon hit: extra 1d6 Necrotic, Psychic or Radiant damage, and you can expend a "
                "Hit Point Die to regain the roll plus your Constitution modifier (minimum 1) Hit Points."},
    _XPHB_INV.format("gaze-of-two-minds"): {
        "note": "Bonus Action: touch a willing creature and perceive through its senses until the end of your next turn "
                "(maintain with a Bonus Action each turn); you can cast spells from its space within 60 feet."},
    _XPHB_INV.format("gift-of-the-protectors"): {
        "note": "Book of Shadows page holds {cha_names} {cha_names_word} (Charisma modifier, minimum one). A named creature "
                "reduced to 0 Hit Points but not killed drops to 1 instead; once triggered, no one benefits until a Long Rest."},
    _XPHB_INV.format("investment-of-the-chain-master"): {
        "note": "Your Find Familiar familiar gains a 40 ft Fly or Swim Speed, Bonus Action Attack command, Necrotic or "
                "Radiant damage option, your spell save DC, and Reaction Resistance for it."},
    _XPHB_INV.format("agonizing-blast"): {"resource_bonus": {"name": "Agonizing Blast", "ability": "CHA", "spell": None}},
    _XPHB_INV.format("eldritch-spear"): {
        "note": "One known damaging Warlock cantrip with range 10+ feet: its range increases by 30 x Warlock level = {spear_range} feet."},
    _XPHB_INV.format("repelling-blast"): {
        "note": "One known Warlock cantrip that requires an attack roll: when you hit a Large or smaller creature you can push it up to 10 feet straight away."},
}


# C7c: short notes added to the attack row of the Pact of the Blade weapon, by selected XPHB invocation id (the Blade's own
# note is attacks.PACT_WEAPON_NOTE; texts as in
# INVOCATION_EFFECTS_2024 and the XPHB records, read 2026-10-11). The numbers on the row are unchanged (information).
PACT_WEAPON_ROW_NOTES_2024: dict[str, str] = {
    _XPHB_INV.format("thirsting-blade"): "Thirsting Blade: attack twice with the Attack action",
    _XPHB_INV.format("devouring-blade"): "Devouring Blade: Thirsting Blade confers two extra attacks rather than one",
    _XPHB_INV.format("eldritch-smite"): "Eldritch Smite: once per turn, expend a Pact Magic slot for +1d8 Force (+1d8 per slot level), Prone if Huge or smaller",
    _XPHB_INV.format("lifedrinker"): "Lifedrinker: once per turn +1d6 Necrotic, Psychic or Radiant; spend a Hit Point Die to heal",
}


# ---- 2024 class option choices (C6a orders, C6c-2 Blessed Strikes / Elemental Fury) -------------
# XPHB class features that offer a pick between sibling feature records (ruleset "2024" only).
# Texts read from the imported catalog.features on 2026-10-10:
#   Protector   "you gain proficiency with Martial weapons and training with Heavy armor."
#   Thaumaturge "You know one extra cantrip from the Cleric spell list. In addition ... a bonus
#                to your Intelligence (Arcana or Religion) checks. The bonus equals your Wisdom
#                modifier (minimum of +1)."
#   Warden      "... proficiency with Martial weapons and training with Medium armor."
#   Magician    "You know one extra cantrip from the Druid spell list. ... Intelligence (Arcana or
#                Nature) checks. The bonus equals your Wisdom modifier (minimum bonus of +1)."
#   Blessed Strikes (Cleric 7)  "You gain one of the following options of your choice (if you get either
#                option from a Cleric subclass in an older book, use only the option you choose for this
#                feature)."  Divine Strike: "extra 1d8 Necrotic or Radiant damage (your choice)" once per
#                turn on a weapon hit; Potent Spellcasting: "Add your Wisdom modifier to the damage you
#                deal with any Cleric cantrip." Improved Blessed Strikes (14): Divine Strike "increases to
#                2d8"; Potent Spellcasting: temporary hit points "equal to twice your Wisdom modifier".
#   Elemental Fury (Druid 7)    "You gain one of the following options of your choice."  Primal Strike:
#                "extra 1d8 Cold, Fire, Lightning, or Thunder damage (choose when you hit)" once per turn on
#                a weapon (or Wild Shape Beast form) hit; Potent Spellcasting: "... any Druid cantrip."
#                Improved Elemental Fury (15): Potent: a cantrip with range 10 feet or greater gains 300
#                feet; Primal Strike "increases to 2d8".
# Keyed by (class, slug). Keys: feature (XPHB feature record that must exist), label, level (the class level
# the card appears at), cid (the stored-pick key; the C6a cids keep their historic shape), options
# {catalog feature index: effect}. Effect keys: proficiencies (ids of the shared proficiency sets),
# extra_cantrips (count bump on the class cantrip card), skill_bonus {skills, ability, minimum}: bonus =
# max(minimum, ability modifier) added to those skills' totals (C6a); divine_strike / primal_strike
# {dice_by_level {class level: dice}, types} and potent_spellcasting {class, improved_level} are read by class_resources (C6c-2, decision E3: resources + attack-row notes).
CLASS_OPTION_CHOICES_2024: dict[tuple[str, str], dict] = {
    ("cleric", "divine-order"): {
        "feature": "xphb-cleric-1-divine-order", "label": "Divine Order", "level": 1,
        "cid": "class:cleric:1:divine-order",
        "options": {
            "xphb-cleric-1-protector": {"proficiencies": ["martial-weapons", "heavy-armor"]},
            "xphb-cleric-1-thaumaturge": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-religion"], "ability": "WIS", "minimum": 1},
            },
        },
    },
    ("druid", "primal-order"): {
        "feature": "xphb-druid-1-primal-order", "label": "Primal Order", "level": 1,
        "cid": "class:druid:1:primal-order",
        "options": {
            "xphb-druid-1-magician": {
                "extra_cantrips": 1,
                "skill_bonus": {"skills": ["skill-arcana", "skill-nature"], "ability": "WIS", "minimum": 1},
            },
            "xphb-druid-1-warden": {"proficiencies": ["martial-weapons", "medium-armor"]},
        },
    },
    ("cleric", "blessed-strikes"): {
        "feature": "xphb-cleric-7-blessed-strikes", "label": "Blessed Strikes", "level": 7,
        "cid": "class:cleric:7:feature:xphb-cleric-7-blessed-strikes",
        "options": {
            "xphb-cleric-7-divine-strike": {
                "divine_strike": {"dice_by_level": {7: "1d8", 14: "2d8"}, "types": "Necrotic or Radiant"}},
            "xphb-cleric-7-potent-spellcasting": {
                "potent_spellcasting": {"class": "Cleric", "improved_level": 14}},
        },
    },
    ("druid", "elemental-fury"): {
        "feature": "xphb-druid-7-elemental-fury", "label": "Elemental Fury", "level": 7,
        "cid": "class:druid:7:feature:xphb-druid-7-elemental-fury",
        "options": {
            "xphb-druid-7-potent-spellcasting": {
                "potent_spellcasting": {"class": "Druid", "improved_level": 15}},
            "xphb-druid-7-primal-strike": {
                "primal_strike": {"dice_by_level": {7: "1d8", 15: "2d8"}, "types": "Cold, Fire, Lightning, or Thunder"}},
        },
    },
}


# ---- 2024 Expertise cards (C6b-1) -------------------------------------------
# Keyed by the XPHB feature id (imported into catalog.features by C1). Texts read from the
# imported catalog on 2026-10-10:
#   Bard 2 / 9, Rogue 1 / 6   "You gain Expertise in two of your skill proficiencies of your choice."
#   Ranger 9                  "Choose two of your skill proficiencies with which you lack Expertise."
#   Ranger 2 Deft Explorer    "Choose one of your skill proficiencies with which you lack Expertise."
#   Wizard 2 Scholar          "Choose one of the following skills in which you have proficiency:
#                              Arcana, History, Investigation, Medicine, Nature, or Religion."
# Keys: class, level, count, skills (None = every skill, else the allowed skill ids),
# lacks_expertise (True = options that already have Expertise are disabled; only the two
# "with which you lack Expertise" texts, decision E1: the other cards allow a wasted duplicate).
# No card offers tools (2024 Expertise is skills only).
EXPERTISE_2024: dict[str, dict] = {
    "xphb-bard-2-expertise": {"class": "bard", "level": 2, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-bard-9-expertise": {"class": "bard", "level": 9, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-rogue-1-expertise": {"class": "rogue", "level": 1, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-rogue-6-expertise": {"class": "rogue", "level": 6, "count": 2, "skills": None, "lacks_expertise": False},
    "xphb-ranger-2-deft-explorer": {"class": "ranger", "level": 2, "count": 1, "skills": None, "lacks_expertise": True},
    "xphb-ranger-9-expertise": {"class": "ranger", "level": 9, "count": 2, "skills": None, "lacks_expertise": True},
    "xphb-wizard-2-scholar": {
        "class": "wizard", "level": 2, "count": 1, "lacks_expertise": False,
        "skills": ["skill-arcana", "skill-history", "skill-investigation", "skill-medicine", "skill-nature", "skill-religion"],
    },
}

# G2: the three SRD (2014) Metamagic cards of the Sorcerer (levels 3, 10 and 17).
SRD_METAMAGIC_FEATURES = ("metamagic-1", "metamagic-2", "metamagic-3")

# SRD (2014) class cards that the 2024 cards replace; skipped under ruleset "2024" only when the
# replacing XPHB feature exists in the catalog. The Ranger's Favored Enemy / Natural Explorer
# cards have no 2024 counterpart card at all (2024 Favored Enemy is a resource, Deft Explorer
# replaces Natural Explorer), so they go whenever the XPHB Ranger is imported.
SRD_CARDS_REPLACED_2024: dict[str, tuple[str, ...]] = {
    "bard": ("bard-expertise-1", "bard-expertise-2"),
    "rogue": ("rogue-expertise-1", "rogue-expertise-2"),
    "sorcerer": ("metamagic-1", "metamagic-2", "metamagic-3"),
    "warlock": ("eldritch-invocations", "pact-boon"),  # C7a: the XPHB card holds the Pacts as invocations
    "ranger": ("favored-enemy-1-type", "favored-enemy-2-types", "favored-enemy-3-enemies",
               "natural-explorer-1-terrain-type", "natural-explorer-2-terrain-types",
               "natural-explorer-3-terrain-types"),
}


# ---- 2024 class languages and Primal Knowledge (C6b-2) ----------------------------------------
# PHB 2024 chapter 2 language tables (Standard and Rare). Deliberately NOT merged into LANGUAGES:
# that list drives every mixed / 2014 language choice and must not change.
LANGUAGES_2024_STANDARD: list[dict[str, str]] = [
    {"index": "common", "name": "Common"},
    {"index": "common-sign-language", "name": "Common Sign Language"},
    {"index": "draconic", "name": "Draconic"},
    {"index": "dwarvish", "name": "Dwarvish"},
    {"index": "elvish", "name": "Elvish"},
    {"index": "giant", "name": "Giant"},
    {"index": "gnomish", "name": "Gnomish"},
    {"index": "goblin", "name": "Goblin"},
    {"index": "halfling", "name": "Halfling"},
    {"index": "orc", "name": "Orc"},
]
LANGUAGES_2024_RARE: list[dict[str, str]] = [
    {"index": "abyssal", "name": "Abyssal"},
    {"index": "celestial", "name": "Celestial"},
    {"index": "deep-speech", "name": "Deep Speech"},
    {"index": "druidic", "name": "Druidic"},
    {"index": "infernal", "name": "Infernal"},
    {"index": "primordial", "name": "Primordial"},
    {"index": "sylvan", "name": "Sylvan"},
    {"index": "thieves-cant", "name": "Thieves' Cant"},
    {"index": "undercommon", "name": "Undercommon"},
]
# VF2.4: languages the 2014 species records grant that the pick pool (LANGUAGES) does not hold. Display names only: they are
# never offered in a pick card. (a) The Primordial dialects the records key by name ({"auran": true} Kenku DMG / VGM,
# {"aquan": true} Locathah, Merfolk DMG, Sea Elf, Tortle TTP, {"terran": true} Deep Gnome DMG, ...); "ignan" completes the
# set (no record uses it yet). (b) The record's `other: true` ("another language, named in the text": Aven, Gith, Quori ...)
# -- `names` are written in the quoted sentence of the record's own Languages trait, which a test pins. Keyed by the catalog
# race / subrace id. `other` also stands for Vedalken in the Simic Hybrid choice ("your choice of Elvish or Vedalken").
SPECIES_DIALECT_LANGUAGES: dict[str, str] = {"auran": "Auran", "aquan": "Aquan", "ignan": "Ignan", "terran": "Terran"}
SPECIES_OTHER_LANGUAGES: dict[str, dict] = {
    "aarakocra-eepc": {"names": ["Aarakocra"], "quote": "You can speak, read, and write Common, Aarakocra, and Auran."},
    "aven-psa": {"names": ["Aven"], "quote": "You can speak, read, and write Common and Aven."},
    "aven-psd": {"names": ["Aven"], "quote": "You can speak, read, and write Common and Aven."},
    "bullywug-dmg": {"names": ["Bullywug"], "quote": "You can speak, read, and write Bullywug."},
    "gith-mtf": {"names": ["Gith"], "quote": "You can speak, read, and write Common and Gith."},
    "grung-oga": {"names": ["Grung"], "quote": "You can speak, read, and write Grung."},
    "kalashtar-erlw": {"names": ["Quori"], "quote": "You can speak, read, and write Common, Quori, and one other language of your choice."},
    "khenra-psa": {"names": ["Khenra"], "quote": "You can speak, read, and write Common and Khenra."},
    "kor-psz": {"names": ["Kor silent speech"], "quote": "You can speak, read, and write Common, and communicate in the silent speech of the Kor."},
    "leonin-mot": {"names": ["Leonin"], "quote": "You can speak, read, and write Common and Leonin."},
    "loxodon-ggr": {"names": ["Loxodon"], "quote": "You can speak, read, and write Common and Loxodon."},
    "merfolk-psz": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common, Merfolk, and one extra language of your choice."},
    "minotaur-ggr": {"names": ["Minotaur"], "quote": "You can speak, read, and write Common and Minotaur."},
    "minotaur-(amonkhet)-psa": {"names": ["Minotaur"], "quote": "You can speak, read, and write Common and Minotaur."},
    "naga-psa": {"names": ["Naga"], "quote": "You can speak, read, and write Common and Naga."},
    "simic-hybrid-ggr": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common and your choice of Elvish or Vedalken."},
    "siren-psx": {"names": ["Siren"],
                  "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign) and Siren."},
    "troglodyte-dmg": {"names": ["Troglodyte"], "quote": "You can speak, read, and write Troglodyte."},
    "vampire-psz": {"names": ["Vampire"], "quote": "You can speak, read, and write Common and Vampire."},
    "vedalken-ggr": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common, Vedalken, and one other language of your choice."},
    "vedalken-psk": {"names": ["Vedalken"], "quote": "You can speak, read, and write Common and Vedalken."},
    "human-phb-keldon-psd": {"names": ["Keldon"], "quote": "You can speak, read, and write Common and Keldon."},
    "merfolk-psz-ixalan;-blue-psx": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign), Merfolk, and one additional language of your choice."},
    "merfolk-psz-ixalan;-green-psx": {"names": ["Merfolk"], "quote": "You can speak, read, and write Common Trade Pidgin (if it exists in your campaign), Merfolk, and one additional language of your choice."},
}

# VF4.4: counted features of the SRD Levels file (`class_specific`) that disagree with the PHB class table. Level 1..20.
# Warlock "Eldritch Invocations" optionalfeatureProgression [0,2,2,2,3,3,4,4,5,5,5,6,6,6,7,7,7,8,8,8] (PHB p.107) and Sorcerer
# "Metamagic" {"3": 2, "10": 3, "17": 4} (PHB p.101), both read from the vendored class files by a test. The SRD Levels file has
# invocations_known 3 at L4 and 4 at L6, metamagic_known 4 at L16 (an audit of cantrips known, spells known, invocations and
# metamagic against every PHB class table found exactly these three). Nothing else in the file disagrees.
SRD_LEVELS_COUNT_FIXES: dict[tuple[str, str], list[int]] = {
    ("warlock", "invocations_known"): [0, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    ("sorcerer", "metamagic_known"): [0, 0, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4],
}

# VF4.2: the four GGR backgrounds whose `languageProficiencies` choose.from list holds the placeholder "other" (Boros
# Legionnaire, Golgari Agent, Izzet Engineer, Selesnya Initiate). The record's own "Languages:" line names the language
# ("Choose one of Elvish, Loxodon, or Sylvan"); `names` replace the placeholder in the pick card, in place. Keyed by the
# catalog background id; `quote` is that line (pinned by a test). Display names only, the pick pool LANGUAGES is unchanged.
BACKGROUND_OTHER_LANGUAGES: dict[str, dict] = {
    "boros-legionnaire-ggr": {"names": ["Minotaur"], "quote": "Choose one of Celestial, Draconic, Goblin, or Minotaur"},
    "golgari-agent-ggr": {"names": ["Kraul"], "quote": "Choose one of Elvish, Giant, or Kraul"},
    "izzet-engineer-ggr": {"names": ["Vedalken"], "quote": "Choose one of Draconic, Goblin, or Vedalken"},
    "selesnya-initiate-ggr": {"names": ["Loxodon"], "quote": "Choose one of Elvish, Loxodon, or Sylvan"},
}

# id -> display name of every language any ruleset can produce (exports read this).
LANGUAGE_NAMES: dict[str, str] = {
    lang["index"]: lang["name"] for lang in LANGUAGES + LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE
}
LANGUAGE_NAMES.update(SPECIES_DIALECT_LANGUAGES)
LANGUAGE_NAMES.update({n.lower().replace(" ", "-"): n for row in SPECIES_OTHER_LANGUAGES.values() for n in row["names"]})
LANGUAGE_NAMES.update({n.lower().replace(" ", "-"): n for row in BACKGROUND_OTHER_LANGUAGES.values() for n in row["names"]})  # VF4.2

# XPHB class features that grant languages (texts read from catalog.features on 2026-10-10):
#   Rogue 1 Thieves' Cant   "You know Thieves' Cant and one other language of your choice, which you choose
#                            from the language tables in chapter 2."
#   Druid 1 Druidic         "You know Druidic, the secret language of Druids."
#   Ranger 2 Deft Explorer  "Languages. You know two languages of your choice from the language tables in chapter 2."
# Keys: class, level, fixed (language ids always known), choose (picks from the 19-entry pool, decision E2).
CLASS_LANGUAGES_2024: dict[str, dict] = {
    "xphb-rogue-1-thieves-cant": {"class": "rogue", "level": 1, "fixed": ["thieves-cant"], "choose": 1},
    "xphb-druid-1-druidic": {"class": "druid", "level": 1, "fixed": ["druidic"], "choose": 0},
    "xphb-ranger-2-deft-explorer": {"class": "ranger", "level": 2, "fixed": [], "choose": 2},
}

# XPHB Barbarian 3 Primal Knowledge: "You gain proficiency in another skill of your choice from the
# skill list available to Barbarians at level 1." (options = classes_2024["barbarian"] level 1 skill list)
PRIMAL_KNOWLEDGE_2024: dict[str, object] = {
    "feature": "xphb-barbarian-3-primal-knowledge", "class": "barbarian", "level": 3,
}


# RP12 (F1, E13): subclass proficiency picks, ruleset "2024" only. Each entry names the XPHB subclass feature record
# (its own `level` is the first level of the card; the class and subclass come from the record too) and what is
# picked. `kind`: "skills" (`pool`: "any" = the 18 skills, "class-level-1:<class>" = the skills of that class's 2024
# level 1 list, or an explicit skill-id tuple), "tool" (`pool`: "artisans-tools"), "save" (`fixed` = the saving throw
# the feature grants outright, `alternatives` = the saves offered instead when `fixed` is already proficient at the
# card's position). `cid`: "feature" -> `class:<cls>:<lvl>:feature:<fid>`, "tool-choice" ->
# `class:<cls>:<lvl>:tool-choice:<fid>` (a feature with two picks needs two cids; both attach to the feature's
# sheet row). `quote` is a verbatim sentence of the record (pinned by tests); `note` (+ `quote`) becomes a note-only
# class resource of the subclass.
