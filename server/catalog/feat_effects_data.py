"""Feat effect scan table, vocabulary and coverage ratchet (FE0, data only, no behaviour change).

Pure data (it imports only its sibling data module ``feat_effects_tail``, the FE10 tail). Later FE slices
(docs/superpowers/plans/2026-10-11-feat-effects.md) fill ``FEAT_EFFECTS`` one slice at a time and
shrink ``FEAT_PENDING`` until FE10 empties it. ``tests/test_feat_effects_coverage.py`` enforces
the ratchet against ``catalog.feats``.

Why a hand table: 5etools carries no structured key for initiative, hit points, speed, AC,
passive scores, resources or attack riders. Every such effect is prose.

Edition policy: entries are keyed by feat index (``alert-phb`` and ``alert-xphb`` are different
entries), so a feat follows its own edition's text under every ruleset.

Copyright note: when an entry is added, the governing sentence is quoted from the catalog text
in a comment and pinned by a "quote matches catalog text" test; never paste book text here.

Effect vocabulary (every key optional; the full semantics are in plan section 4.1)::

    initiative                  int | "pb"
    hp_per_level, hp_flat       int
    walk_bonus                  int
    climb_equals_walk           bool
    ac_formula                  {base, abilities, allows_shield}
    medium_armor_dex_cap        {cap, min_dex_score}
    medium_armor_stealth_ok     bool
    ac_bonus_if                 {bonus, wielded}
    passive_bonus               {skill-index: int}
    senses_additive             {sense: range}
    prof_or_expertise           bool   (marks the feat's skill card)
    lacks_expertise             bool   (marks the feat's Expertise card under every ruleset)
    resist_choice               {count, options}                (FE7: card ``:resistance-choice``; picks join
                                        damageModifiers.resistances)
    resist_by_variant           {variant slug: damage type}     (FE7: read from the ``:spell-variant`` pick)
    damage_type_choice          {options, distinct_across_repeats}  (FE7: card ``:damage-type``; a repeat must differ)
    variant_choice              {suffix, label, description, options: [{id, label, note}]}
                                        (FE7: card ``:<suffix>``; the picked option's note joins the feat notes)
    weapon_proficiency_choice   {count, categories}  (FE8: card ``:weapon-choice``; the picks join the proficient weapons)
    mastery_choice              {count, categories}  (FE8: card ``:weapon-mastery``; proficient weapons only; the pick
                                        joins sheet.weaponMasteries)
    option_picks                {kind, count}  (FE9: kind fighting-style | maneuver | metamagic | invocation; card
                                        ``:fighting-style`` / ``:maneuvers`` / ``:metamagic`` / ``:invocation`` (+
                                        ``:invocation-ability``); the pool is built in resolve from the SRD / Battle Master lists)
    unarmed                     {die, die_free_hands, type, ability, notes}
    offhand                     {non_light_one_handed_melee | light_crossbow_mod | dw2024: True}
    finesse_items               [item index]
    attack_notes                [{when: {predicate}, text}]
    resources                   [{name, uses, recharge, note, die, dc}]  (FE3 implements these keys; uses = int | "pb";
                                        recharge = long | short | short-or-long; FE9 adds ``die`` and ``dc``, an
                                        expression over pb / <abl>_mod; dice/pool come with the slices that need them)
    notes                       [template]  ({expr} over pb, level, <abl>_mod, <abl>_score, inc_mod;
                                        {sum:a,b} prints "a + b = total"; {choice} is the instance's pick (FE7);
                                        see engine/feat_effects.render)
    data_only                   bool   (everything is carried by catalog fields or by
                                        reference_data.CLASS_FEATURE_EFFECTS)

Scan kinds (plan section 3; a feat may belong to several of the first four):

    numeric   derived numbers (initiative, HP, speed, AC, passive, senses)           19 feats
    choice    choice-shaped gaps (cards, data fixes, option picks)                   22 feats
    attack    attack rows (unarmed, off-hand, row notes)                             32 feats
    resource  resources with uses                                                    82 feats
    notes     notes only (nothing numeric to compute)                               154 feats
    fighting-style  the 2024 Fighting Style feats already done through
              CLASS_FEATURE_EFFECTS (Blind Fighting through its blindsight)           7 feats

The 3 remaining FS-category feats are Interception and Protection (scanned as notes) and
Unarmed Fighting (scanned as attack); the three spell-card FS feats (Arcane Warrior, Blessed
Warrior, Druidic Warrior) get their cantrips from the catalog and are scanned as notes.
"""
from __future__ import annotations

FEAT_EFFECT_KEYS: frozenset[str] = frozenset({
    "initiative", "hp_per_level", "hp_flat", "walk_bonus", "climb_equals_walk", "ac_formula",
    "medium_armor_dex_cap", "medium_armor_stealth_ok", "ac_bonus_if", "passive_bonus",
    "senses_additive", "prof_or_expertise", "lacks_expertise", "resist_choice",
    "resist_by_variant", "damage_type_choice", "variant_choice", "weapon_proficiency_choice", "mastery_choice",
    "option_picks", "unarmed", "offhand", "finesse_items", "attack_notes", "resources", "notes",
    "data_only", "modifies",
})

SCAN_KINDS: frozenset[str] = frozenset(
    {"numeric", "choice", "attack", "resource", "notes", "fighting-style"})

# True since FE10, the slice that emptied FEAT_PENDING; the ratchet test then requires it to stay empty.
FE10_DONE = True

_NUMERIC = (
    "alert-phb",
    "alert-xphb",
    "athlete-xphb",
    "boon-of-fortitude-xphb",
    "boon-of-speed-xphb",
    "dragon-hide-xge",
    "dual-wielder-phb",
    "keenness-of-the-stone-giant-bgg",
    "mark-of-passage-efa",
    "medium-armor-master-phb",
    "medium-armor-master-xphb",
    "mobile-phb",
    "observant-phb",
    "revenant-blade-erlw",
    "speedy-xphb",
    "squat-nimbleness-xge",
    "tough-phb",
    "tough-xphb",
    "transmuted-anatomy-au",
)

_CHOICE = (
    "boon-of-energy-resistance-xphb",
    "boon-of-skill-xphb",
    "dragonscarred-frhof",
    "echoing-soul-rhw",
    "eldritch-adept-tce",
    "elemental-adept-phb",
    "elemental-adept-xphb",
    "fighting-initiate-tce",
    "harper-agent-frhof",
    "keen-mind-xphb",
    "martial-adept-phb",
    "metamagic-adept-tce",
    "observant-xphb",
    "portal-jumper-au",
    "prodigy-xge",
    "scion-of-the-outer-planes-sato",
    "skill-expert-tce",
    "skill-expert-xphb",
    "spell-resistant-au",
    "strike-of-the-giants-bgg",
    "weapon-master-phb",
    "weapon-master-xphb",
)

_ATTACK = (
    "bomber-abh",
    "boon-of-irresistible-offense-xphb",
    "charger-phb",
    "charger-xphb",
    "crossbow-expert-phb",
    "crossbow-expert-xphb",
    "crusher-tce",
    "crusher-xphb",
    "dragon-hide-xge",
    "dual-wielder-phb",
    "dual-wielder-xphb",
    "elven-accuracy-xge",
    "great-weapon-master-phb",
    "great-weapon-master-xphb",
    "gunner-tce",
    "orcish-fury-xge",
    "piercer-tce",
    "piercer-xphb",
    "poisoner-tce",
    "poisoner-xphb",
    "polearm-master-phb",
    "polearm-master-xphb",
    "revenant-blade-erlw",
    "savage-attacker-phb",
    "savage-attacker-xphb",
    "sharpshooter-phb",
    "sharpshooter-xphb",
    "slasher-tce",
    "slasher-xphb",
    "tavern-brawler-phb",
    "tavern-brawler-xphb",
    "unarmed-fighting-xphb",
)

_RESOURCE = (
    "aberrant-dragonmark-efa",
    "adept-of-the-red-robes-dsotdq",
    "agent-of-order-sato",
    "arcane-artist-au",
    "arcane-infiltrator-au",
    "arcane-omens-au",
    "arcane-overload-au",
    "arcane-safeguard-au",
    "arcane-undertaker-au",
    "baleful-scion-sato",
    "bloodlust-abh",
    "boon-of-erupting-spellpower-au",
    "boon-of-exquisite-radiance-frhof",
    "boon-of-fate-xphb",
    "boon-of-fluid-forms-frhof",
    "boon-of-misty-escape-abh",
    "boon-of-recovery-xphb",
    "boon-of-terror-frhof",
    "boon-of-the-soul-drinker-frhof",
    "cult-of-the-dragon-initiate-frhof",
    "delicious-pain-abh",
    "divination-adept-au",
    "ember-of-the-fire-giant-bgg",
    "fade-away-xge",
    "fairy-trickster-frhof",
    "familiar-friend-au",
    "fury-of-the-frost-giant-bgg",
    "gathered-whispers-rhw",
    "genie-magic-frhof",
    "gift-of-the-chromatic-dragon-ftd",
    "gift-of-the-gem-dragon-ftd",
    "gift-of-the-metallic-dragon-ftd",
    "greater-aberrant-mark-efa",
    "greater-mark-of-handling-efa",
    "greater-mark-of-healing-efa",
    "greater-mark-of-hospitality-efa",
    "greater-mark-of-scribing-efa",
    "greater-mark-of-warding-efa",
    "guile-of-the-cloud-giant-bgg",
    "keenness-of-the-stone-giant-bgg",
    "knight-of-the-crown-dsotdq",
    "knight-of-the-rose-dsotdq",
    "knight-of-the-sword-dsotdq",
    "light-bringer-abh",
    "living-shadow-rhw",
    "lordly-resolve-frhof",
    "love-bites-abh",
    "lucky-phb",
    "lucky-xphb",
    "mage-slayer-xphb",
    "mark-of-sentinel-efa",
    "martial-adept-phb",
    "metamagic-adept-tce",
    "mist-walker-rhw",
    "mythal-touched-frhof",
    "orcish-fury-xge",
    "planar-wanderer-sato",
    "portal-jumper-au",
    "potent-dragonmark-efa",
    "purple-dragon-commandant-frhof",
    "purple-dragon-rook-frhof",
    "putrefy-abh",
    "rebuke-abh",
    "righteous-heritor-sato",
    "ritual-caster-xphb",
    "rune-shaper-bgg",
    "second-chance-xge",
    "sharp-eye-rhw",
    "soul-of-the-storm-giant-bgg",
    "spell-resistant-au",
    "spell-subterfuge-au",
    "spellfire-spark-frhof",
    "squire-of-solamnia-dsotdq",
    "strike-of-the-giants-bgg",
    "strixhaven-mascot-scc",
    "survivor-rhw",
    "symbiotic-being-rhw",
    "tireless-reveler-abh",
    "transmuted-anatomy-au",
    "vampire-hunter-abh",
    "vampires-plaything-abh",
    "vampiric-exultation-psx",
)

_NOTES = (
    "aberrant-anatomy-rhw",
    "aberrant-dragonmark-erlw",
    "ability-score-improvement-xphb",
    "abjuration-adept-au",
    "actor-phb",
    "actor-xphb",
    "adept-of-the-black-robes-dsotdq",
    "adept-of-the-white-robes-dsotdq",
    "arcane-eloquence-au",
    "arcane-warrior-au",
    "artificer-initiate-tce",
    "athlete-phb",
    "blessed-warrior-xphb",
    "boon-of-blazing-dawn-abh",
    "boon-of-bloodshed-frhof",
    "boon-of-bountiful-health-frhof",
    "boon-of-combat-prowess-xphb",
    "boon-of-communication-frhof",
    "boon-of-desperate-resilience-frhof",
    "boon-of-dimensional-travel-xphb",
    "boon-of-fortunes-favor-frhof",
    "boon-of-looming-shadows-abh",
    "boon-of-magic-school-mastery-au",
    "boon-of-poison-mastery-frhof",
    "boon-of-revelry-frhof",
    "boon-of-siberys-efa",
    "boon-of-spell-recall-xphb",
    "boon-of-the-bright-sun-frhof",
    "boon-of-the-furious-storm-frhof",
    "boon-of-the-iron-mind-au",
    "boon-of-the-night-spirit-xphb",
    "boon-of-truesight-xphb",
    "bountiful-luck-xge",
    "cartomancer-bmt",
    "chef-tce",
    "chef-xphb",
    "child-of-the-sun-lfl",
    "cloying-mists-abh",
    "cohort-of-chaos-sato",
    "cold-caster-frhof",
    "conjuration-adept-au",
    "crafter-xphb",
    "defensive-duelist-phb",
    "defensive-duelist-xphb",
    "divinely-favored-dsotdq",
    "dragon-fear-xge",
    "drow-high-magic-xge",
    "druidic-warrior-xphb",
    "dungeon-delver-phb",
    "durable-phb",
    "durable-xphb",
    "dwarven-fortitude-xge",
    "elemental-familiar-au",
    "emerald-enclave-fledgling-frhof",
    "enchantment-adept-au",
    "enclave-magic-frhof",
    "evocation-adept-au",
    "fey-teleportation-xge",
    "fey-touched-tce",
    "fey-touched-xphb",
    "flames-of-phlegethos-xge",
    "grappler-phb",
    "grappler-xphb",
    "greater-mark-of-detection-efa",
    "greater-mark-of-finding-efa",
    "greater-mark-of-making-efa",
    "greater-mark-of-passage-efa",
    "greater-mark-of-sentinel-efa",
    "greater-mark-of-shadow-efa",
    "greater-mark-of-storm-efa",
    "harper-teamwork-frhof",
    "healer-phb",
    "healer-xphb",
    "heavily-armored-phb",
    "heavily-armored-xphb",
    "heavy-armor-master-phb",
    "heavy-armor-master-xphb",
    "illusion-adept-au",
    "infernal-constitution-xge",
    "initiate-of-high-sorcery-dsotdq",
    "inspiring-leader-phb",
    "inspiring-leader-xphb",
    "interception-xphb",
    "keen-mind-phb",
    "lightly-armored-phb",
    "lightly-armored-xphb",
    "linguist-phb",
    "lords-alliance-agent-frhof",
    "mage-slayer-phb",
    "magic-connoisseur-au",
    "magic-initiate-phb",
    "magic-initiate-xphb",
    "mark-of-detection-efa",
    "mark-of-finding-efa",
    "mark-of-handling-efa",
    "mark-of-healing-efa",
    "mark-of-hospitality-efa",
    "mark-of-making-efa",
    "mark-of-scribing-efa",
    "mark-of-shadow-efa",
    "mark-of-storm-efa",
    "mark-of-warding-efa",
    "martial-weapon-training-xphb",
    "moderately-armored-phb",
    "moderately-armored-xphb",
    "mounted-combatant-phb",
    "mounted-combatant-xphb",
    "musician-xphb",
    "necromancy-adept-au",
    "orders-resilience-frhof",
    "otherworldly-familiar-au",
    "outlands-envoy-sato",
    "protection-xphb",
    "quicksmithing-psk",
    "resilient-phb",
    "resilient-xphb",
    "ritual-caster-phb",
    "second-skin-rhw",
    "sentinel-phb",
    "sentinel-xphb",
    "servo-crafting-psk",
    "shadow-touched-tce",
    "shadow-touched-xphb",
    "shadowmoor-hexer-lfl",
    "shield-master-phb",
    "shield-master-xphb",
    "skilled-phb",
    "skilled-xphb",
    "skulker-phb",
    "skulker-xphb",
    "soothing-familiar-au",
    "spell-sniper-phb",
    "spell-sniper-xphb",
    "spellfire-adept-frhof",
    "street-justice-frhof",
    "strixhaven-initiate-scc",
    "svirfneblin-magic-mtf",
    "telekinetic-tce",
    "telekinetic-xphb",
    "telepathic-tce",
    "telepathic-xphb",
    "touch-of-death-rhw",
    "transmutation-adept-au",
    "treacherous-allure-abh",
    "tyro-of-the-gauntlet-frhof",
    "vampire-touched-abh",
    "vigor-of-the-hill-giant-bgg",
    "war-caster-phb",
    "war-caster-xphb",
    "warlike-familiar-au",
    "watchers-rhw",
    "wood-elf-magic-xge",
    "zhentarim-ruffian-frhof",
    "zhentarim-tactics-frhof",
)

_DONE_FIGHTING_STYLE = (
    "archery-xphb",
    "blind-fighting-xphb",
    "defense-xphb",
    "dueling-xphb",
    "great-weapon-fighting-xphb",
    "thrown-weapon-fighting-xphb",
    "two-weapon-fighting-xphb",
)

_BY_KIND = (
    ("numeric", _NUMERIC), ("choice", _CHOICE), ("attack", _ATTACK), ("resource", _RESOURCE),
    ("notes", _NOTES), ("fighting-style", _DONE_FIGHTING_STYLE),
)


def _build_kinds() -> dict[str, frozenset[str]]:
    out: dict[str, set[str]] = {}
    for kind, indexes in _BY_KIND:
        for index in indexes:
            out.setdefault(index, set()).add(kind)
    return {index: frozenset(kinds) for index, kinds in out.items()}


# feat index -> scan kinds, one entry per catalog feat (exhaustiveness enforced by the tests).
FEAT_KINDS: dict[str, frozenset[str]] = _build_kinds()

# Classified feats. FE0 only lists the 7 Fighting Style feats whose effects already live in
# reference_data.CLASS_FEATURE_EFFECTS (and Blind Fighting's blindsight): nothing new to add.
FEAT_EFFECTS: dict[str, dict] = {index: {"data_only": True} for index in _DONE_FIGHTING_STYLE}

# FE1: initiative, hit point maximum, walking speed, climb speed. The governing sentence of each
# entry is in FEAT_EFFECT_QUOTES (tags stripped), pinned against the catalog text by a test.
FEAT_EFFECTS.update({
    "alert-phb": {"initiative": 5},
    "alert-xphb": {"initiative": "pb"},
    "tough-phb": {"hp_per_level": 2},
    "tough-xphb": {"hp_per_level": 2},
    "boon-of-fortitude-xphb": {"hp_flat": 40},
    "mobile-phb": {"walk_bonus": 10},
    "speedy-xphb": {"walk_bonus": 10},
    "boon-of-speed-xphb": {"walk_bonus": 30},
    "squat-nimbleness-xge": {"walk_bonus": 5},
    "mark-of-passage-efa": {"walk_bonus": 5},
    "transmuted-anatomy-au": {"walk_bonus": 5},
    "athlete-xphb": {"climb_equals_walk": True},
})

# index -> the sentence (plain text, 5etools tags stripped) that governs the entry.
FEAT_EFFECT_QUOTES: dict[str, str] = {
    "alert-phb": "You gain a +5 bonus to initiative.",
    "alert-xphb": "you can add your Proficiency Bonus to the roll",
    "tough-phb": "Whenever you gain a level thereafter, your hit point maximum increases by an additional 2 hit points.",
    "tough-xphb": "Whenever you gain a character level thereafter, your Hit Point maximum increases by an additional 2 Hit Points.",
    "boon-of-fortitude-xphb": "Your Hit Point maximum increases by 40.",
    "mobile-phb": "Your speed increases by 10 feet.",
    "speedy-xphb": "Your Speed increases by 10 feet.",
    "boon-of-speed-xphb": "Your Speed increases by 30 feet.",
    "squat-nimbleness-xge": "Increase your walking speed by 5 feet.",
    "mark-of-passage-efa": "Your Speed increases by 5 feet.",
    "transmuted-anatomy-au": "Your Speed increases by 5 feet.",
    "athlete-xphb": "You gain a Climb Speed equal to your Speed.",
}

# FE3: notes (effects that are not folded into a number, with the character's numbers filled in) and
# feat resources. Note templates: {expr} = integer arithmetic over pb, level, <abl>_mod, <abl>_score
# (lowercase ability) and inc_mod (the modifier of the ability this feat increased); {sum:a,b} prints
# "a + b = total". A template that needs inc_mod renders "(choose the ability)" until it is chosen.
# data_only: the effect is carried by the catalog fields (proficiencies, saving throw / language /
# spell choices) and already reaches the sheet; the entry only classifies the feat.
FEAT_EFFECTS.update({index: {"data_only": True} for index in (
    "heavily-armored-phb", "heavily-armored-xphb", "lightly-armored-phb", "lightly-armored-xphb",
    "moderately-armored-phb", "moderately-armored-xphb", "martial-weapon-training-xphb",
    "resilient-phb", "resilient-xphb", "skilled-phb", "skilled-xphb", "magic-initiate-phb",
    "magic-initiate-xphb", "fey-touched-xphb", "shadow-touched-xphb")})

FEAT_EFFECTS.update({
    "actor-phb": {"notes": [
        "Advantage on Charisma (Deception) and Charisma (Performance) checks to pass yourself off as a different person.",
        "Mimicry: copy a voice or creature sound you heard for at least 1 minute; a listener's Wisdom (Insight) check, "
        "contested by your Charisma (Deception) check, reveals the fake."]},
    "actor-xphb": {"notes": [
        "Impersonation: Advantage on Charisma (Deception or Performance) checks to convince others you are the person you are disguised as.",
        "Mimicry: a creature that hears it needs a Wisdom (Insight) check against DC {8+cha_mod+pb} to see it is faked."]},
    "athlete-phb": {"notes": [
        "Standing up from prone costs only 5 feet of movement; climbing costs no extra movement; "
        "a running jump needs only 5 feet of movement first."]},
    "chef-xphb": {"notes": [
        "Replenishing Meal (Short Rest): food for {4+pb} creatures; each that spends Hit Dice regains an extra 1d8 Hit Points.",
        "Bolstering Treats: {pb} treats per batch (1 hour of work or a Long Rest); eating one (Bonus Action) gives "
        "{pb} Temporary Hit Points for 8 hours."]},
    "crafter-xphb": {"notes": [
        "Discount: 20 percent off nonmagical items you buy.",
        "Fast Crafting: after a Long Rest craft one piece of gear from the Fast Crafting table (you need the tools "
        "and proficiency); it falls apart at your next Long Rest."]},
    "defensive-duelist-phb": {"notes": [
        "Reaction (finesse weapon you are proficient with): +{pb} AC against one melee attack that hit you."]},
    "defensive-duelist-xphb": {"notes": [
        "Parry (Reaction, holding a Finesse weapon): +{pb} AC against melee attacks until the start of your next turn."]},
    "durable-phb": {"notes": [
        "A Hit Die you roll to regain hit points restores at least {max(2,2*con_mod)} hit points."]},
    "durable-xphb": {"notes": [
        "Advantage on Death Saving Throws.",
        "Speedy Recovery (Bonus Action): expend a Hit Point Die and regain Hit Points equal to the roll."]},
    "dungeon-delver-phb": {"notes": [
        "Advantage on Wisdom (Perception) and Intelligence (Investigation) checks to find secret doors, and on saves against traps.",
        "Resistance to trap damage; a fast travel pace does not lower your passive Wisdom (Perception)."]},
    "grappler-phb": {"notes": [
        "Advantage on attack rolls against a creature you are grappling.",
        "Action: pin a creature you grapple with another grapple check; you both are Restrained until the grapple ends."]},
    "grappler-xphb": {"notes": [
        "Punch and Grab: an Unarmed Strike hit in the Attack action can deal damage and grapple (once per turn).",
        "Advantage on attack rolls against a creature Grappled by you; moving it costs no extra movement if it is your size or smaller."]},
    "healer-phb": {"notes": [
        "Healer's kit: stabilizing a dying creature also gives it 1 hit point.",
        "Action, one kit use: restore 1d6 + 4 hit points plus the creature's maximum number of Hit Dice (once per creature until a rest)."]},
    "healer-xphb": {"notes": [
        "Battle Medic (Utilize, one Healer's Kit use): the creature spends a Hit Point Die and regains the roll + {pb} Hit Points.",
        "Reroll a 1 on a die that restores Hit Points with a spell or Battle Medic."]},
    "heavy-armor-master-phb": {"notes": [
        "While wearing heavy armor: bludgeoning, piercing and slashing damage from nonmagical attacks is reduced by 3."]},
    "heavy-armor-master-xphb": {"notes": [
        "While wearing Heavy armor: Bludgeoning, Piercing and Slashing damage from an attack that hits you is reduced by {pb}."]},
    "inspiring-leader-phb": {"notes": [
        "Inspire (10 minutes): up to six friendly creatures each gain {sum:level,cha_mod} Temporary Hit Points "
        "(once per short or long rest each)."]},
    "inspiring-leader-xphb": {"notes": [
        "Bolstering Performance (after a Short or Long Rest): up to six allies within 30 feet each gain "
        "{sum:level,inc_mod} Temporary Hit Points."]},
    "keen-mind-phb": {"notes": [
        "You always know north and the hours left before sunrise or sunset, and recall anything seen or heard in the past month."]},
    "linguist-phb": {"notes": [
        "Ciphers: others need an Intelligence check against DC {int_score+pb} to decipher your code."]},
    "mage-slayer-phb": {"notes": [
        "Reaction: a melee weapon attack against a creature within 5 feet that casts a spell.",
        "A creature you damage that is concentrating has disadvantage on its concentration save.",
        "Advantage on saves against spells cast by creatures within 5 feet of you."]},
    "mage-slayer-xphb": {
        "notes": [
            "Concentration Breaker: a creature you damage while it is concentrating has Disadvantage on its concentration save.",
            "Guarded Mind: turn a failed Intelligence, Wisdom or Charisma save into a success (see the resource)."],
        "resources": [{"name": "Guarded Mind", "uses": 1, "recharge": "short-or-long"}]},
    "mounted-combatant-phb": {"notes": [
        "While mounted and not incapacitated: advantage on melee attacks against unmounted creatures smaller than your mount; "
        "you can take an attack aimed at your mount; your mount takes no damage on a successful Dexterity save for half, and half on a failure."]},
    "mounted-combatant-xphb": {"notes": [
        "Mounted Strike: Advantage on attacks against unmounted creatures within 5 feet of your mount that are at least one size smaller than it.",
        "Leap Aside: your mount takes no damage on a successful Dexterity save for half, and half on a failure.",
        "Veer: while mounted, an attack that hits your mount can hit you instead."]},
    "musician-xphb": {"notes": [
        "Encouraging Song (after a Short or Long Rest): Heroic Inspiration for up to {pb} allies who hear it."]},
    "ritual-caster-phb": {"notes": [
        "Ritual book with two 1st-level ritual spells from one class list; copying a found ritual spell takes 2 hours and 50 gp per spell level."]},
    "ritual-caster-xphb": {
        "notes": [
            "Ritual Spells: {pb} level 1 Ritual spells always prepared; one more each time your Proficiency Bonus increases.",
            "Quick Ritual: cast a prepared Ritual spell at its normal casting time without a spell slot (see the resource)."],
        "resources": [{"name": "Quick Ritual", "uses": 1, "recharge": "long"}]},
    "sentinel-phb": {"notes": [
        "A creature you hit with an opportunity attack has speed 0 for the rest of the turn; Disengage does not stop your opportunity attacks.",
        "Reaction: a melee weapon attack against a creature within 5 feet that attacks a target other than you (unless that target has this feat)."]},
    "sentinel-xphb": {"notes": [
        "Guardian: an Opportunity Attack against a creature within 5 feet that takes the Disengage action or hits a target other than you.",
        "Halt: a creature you hit with an Opportunity Attack has Speed 0 for the rest of the turn."]},
    "shield-master-phb": {"notes": [
        "While wielding a shield: a bonus action shove after the Attack action; add the shield's AC bonus to Dexterity saves against "
        "effects that target only you; a reaction to take no damage on a successful Dexterity save for half."]},
    "shield-master-xphb": {"notes": [
        "Shield Bash: Strength save DC {8+str_mod+pb} (push 5 feet or knock Prone) after a melee hit in the Attack action, once per turn.",
        "Interpose Shield: Reaction, no damage on a successful Dexterity save for half damage while holding a Shield."]},
    "skulker-phb": {"notes": [
        "You can hide when lightly obscured; a missed ranged attack from hiding does not reveal you; dim light does not "
        "impose disadvantage on your sight-based Wisdom (Perception) checks."]},
    "skulker-xphb": {"notes": [
        "Blindsight 10 feet (counted in Senses).",
        "Fog of War: Advantage on Dexterity (Stealth) checks to Hide during combat; a missed attack from hiding does not reveal your location."]},
    "spell-sniper-phb": {"notes": [
        "The range of spells that need an attack roll is doubled; your ranged spell attacks ignore half and three-quarters cover; "
        "you also learn one attack-roll cantrip."]},
    "spell-sniper-xphb": {"notes": [
        "Bypass Cover: your spell attack rolls ignore half and three-quarters cover.",
        "Casting in Melee: enemies within 5 feet do not give Disadvantage on your spell attack rolls.",
        "Increased Range: an attack-roll spell with a range of 10 feet or more gains 60 feet of range."]},
    "telekinetic-xphb": {"notes": [
        "Telekinetic Shove (Bonus Action): a creature you see within 30 feet makes a Strength save, DC {8+inc_mod+pb}, "
        "or is moved 5 feet toward or away from you."]},
    "telepathic-xphb": {"notes": [
        "Telepathic Utterance: speak telepathically to a creature you can see within 60 feet, in a language you know."]},
    "war-caster-phb": {"notes": [
        "Advantage on Constitution saves to keep concentration when you take damage; somatic components with weapons or a shield in hand; "
        "reaction: cast a one-action spell at a creature whose movement provokes an opportunity attack."]},
    "war-caster-xphb": {"notes": [
        "Advantage on Constitution saves to maintain Concentration; Somatic components with weapons or a Shield in hand; "
        "Reactive Spell: cast a one-action spell at a creature that provokes an Opportunity Attack."]},
    "lucky-phb": {
        "notes": ["Spend a luck point to roll an extra d20 on an attack roll, ability check or saving throw, or when an attack "
                  "roll is made against you, and choose which d20 counts."],
        "resources": [{"name": "Luck Points", "uses": 3, "recharge": "long"}]},
    "lucky-xphb": {
        "notes": ["Spend 1 Luck Point to gain Advantage on a d20 Test, or to impose Disadvantage on an attack roll against you."],
        "resources": [{"name": "Luck Points", "uses": "pb", "recharge": "long"}]},
    "second-chance-xge": {
        "notes": ["Reaction: when a creature you can see hits you with an attack roll, it must reroll."],
        "resources": [{"name": "Second Chance", "uses": 1, "recharge": "short-or-long",
                       "note": "also regained when you roll initiative"}]},
    "fade-away-xge": {
        "notes": ["Reaction right after you take damage: become invisible until the end of your next turn or until you "
                  "attack, deal damage or force a saving throw."],
        "resources": [{"name": "Fade Away", "uses": 1, "recharge": "short-or-long"}]},
    "orcish-fury-xge": {
        "notes": ["Once per rest, on a hit with a simple or martial weapon, roll one of its damage dice again as extra damage "
                  "of the weapon's type.",
                  "Reaction right after Relentless Endurance: make one weapon attack."],
        "resources": [{"name": "Orcish Fury", "uses": 1, "recharge": "short-or-long"}]},
})

# FE3 quotes: the governing sentence(s) of each FE3 entry that carries notes or resources, pinned against the
# catalog text by tests/test_feat_resources.py. A tuple pins several sentences of one entry.
FEAT_EFFECT_QUOTES.update({
    "actor-phb": "You can mimic the speech of another person or the sounds made by other creatures.",
    "actor-xphb": "8 plus your Charisma modifier and Proficiency Bonus",
    "athlete-phb": "Climbing doesn't cost you extra movement.",
    "chef-xphb": ("a number of creatures equal to 4 plus your Proficiency",
                  "gain a number of Temporary Hit Points equal to your Proficiency"),
    "crafter-xphb": "you receive a 20 percent discount on it",
    "defensive-duelist-phb": "you can use your reaction to add your proficiency bonus to your AC for that attack",
    "defensive-duelist-xphb": "you can take a Reaction to add your Proficiency Bonus to your Armor Class",
    "durable-phb": "the minimum number of hit points you regain from the roll equals twice your Constitution modifier (minimum of 2)",
    "durable-xphb": "you can expend one of your Hit Point Dice, roll the die, and regain a number of Hit Points equal to the roll",
    "dungeon-delver-phb": "You have resistance to the damage dealt by traps.",
    "grappler-phb": "You have advantage on attack rolls against a creature you are grappling.",
    "grappler-xphb": "You have Advantage on attack rolls against a creature Grappled by you.",
    "healer-phb": "restore 1d6 + 4 hit points to it",
    "healer-xphb": "The creature regains a number of Hit Points equal to the roll plus your Proficiency Bonus.",
    "heavy-armor-master-phb": "damage that you take from nonmagical attacks is reduced by 3",
    "heavy-armor-master-xphb": "is reduced by an amount equal to your Proficiency",
    "inspiring-leader-phb": "Each creature can gain temporary hit points equal to your level + your Charisma modifier.",
    "inspiring-leader-xphb": "Temporary Hit Points equal to your character level plus the modifier of the ability you increased with this feat",
    "keen-mind-phb": "You always know which way is north.",
    "linguist-phb": "they succeed on an Intelligence check (DC equal to your Intelligence score + your proficiency bonus)",
    "mage-slayer-phb": "You have advantage on saving throws against spells cast by creatures within 5 feet of you.",
    "mage-slayer-xphb": ("If you fail an Intelligence, a Wisdom, or a Charisma saving throw, you can cause yourself to succeed instead.",
                         "you can't use it again until you finish a Short or Long Rest"),
    "mounted-combatant-phb": "You can force an attack targeted at your mount to target you instead.",
    "mounted-combatant-xphb": "you can force an attack that hits your mount to hit you instead",
    "musician-xphb": "The number of allies you can affect in this way equals your Proficiency Bonus.",
    "ritual-caster-phb": "The process of copying the spell into your ritual book takes 2 hours per level of the spell, and costs 50 gp per level.",
    "ritual-caster-xphb": ("Choose a number of level 1 spells equal to your Proficiency Bonus",
                           "you can't use this benefit again until you finish a Long Rest"),
    "sentinel-phb": "When you hit a creature with an opportunity attack, the creature's speed becomes 0 for the rest of the turn.",
    "sentinel-xphb": "When you hit a creature with an Opportunity Attack, the creature's Speed becomes 0 for the rest of the current turn.",
    "shield-master-phb": "you can add your shield's AC bonus to any Dexterity saving throw you make against a spell or other harmful effect that targets only you",
    "shield-master-xphb": "8 plus your Strength modifier and Proficiency Bonus",
    "skulker-phb": "Dim light doesn't impose disadvantage on your Wisdom (Perception) checks relying on sight.",
    "skulker-xphb": "You have Blindsight with a range of 10 feet.",
    "spell-sniper-phb": "When you cast a spell that requires you to make an attack roll, the spell's range is doubled.",
    "spell-sniper-xphb": "you can increase the spell's range by 60 feet",
    "telekinetic-xphb": "8 plus the ability modifier of the score increased by this feat and your Proficiency Bonus",
    "telepathic-xphb": "You can speak telepathically to any creature you can see within 60 feet of yourself.",
    "war-caster-phb": "You have advantage on Constitution saving throws that you make to maintain your concentration on a spell when you take damage.",
    "war-caster-xphb": "You have Advantage on Constitution saving throws that you make to maintain Concentration.",
    "lucky-phb": ("You have 3 luck points.", "You regain your expended luck points when you finish a long rest."),
    "lucky-xphb": ("You have a number of Luck Points equal to your Proficiency",
                   "You regain your expended Luck Points when you finish a Long Rest."),
    "second-chance-xge": "you can't use it again until you roll initiative at the start of combat or until you finish a short or long rest",
    "fade-away-xge": "you can't do so again until you finish a short or long rest",
    "orcish-fury-xge": "you can't use it again until you finish a short or long rest",
})

# FE4: Armor Class, passive scores, Stealth and senses. Governing sentences in FEAT_EFFECT_QUOTES (pinned by
# tests/test_feat_defense.py). Conditional AC (F-D3) applies only when ``equipment.wielded`` proves the
# condition; the static note says so, so a build without the wielded hands still sees the rule.
FEAT_EFFECTS.update({
    "dragon-hide-xge": {
        "ac_formula": {"base": 13, "abilities": ["DEX"], "allows_shield": True},
        "notes": ["Claws (no action to extend or retract): unarmed strikes deal 1d4 + Strength modifier slashing damage."]},
    "medium-armor-master-phb": {
        "medium_armor_dex_cap": {"cap": 3, "min_dex_score": 16}, "medium_armor_stealth_ok": True},
    "medium-armor-master-xphb": {
        "medium_armor_dex_cap": {"cap": 3, "min_dex_score": 16}},
    "dual-wielder-phb": {
        "ac_bonus_if": {"bonus": 1, "wielded": "two-melee"},
        "notes": ["+1 AC while wielding a separate melee weapon in each hand (included in Armor Class when the "
                  "wielded hands are set on the Equipment page)."]},
    "revenant-blade-erlw": {
        "ac_bonus_if": {"bonus": 1, "wielded": {"item": "double-bladed-scimitar", "two_hands": True}},
        "notes": ["+1 AC while holding a double-bladed scimitar with two hands (included in Armor Class when the "
                  "wielded hands are set on the Equipment page).",
                  "A double-bladed scimitar has the Finesse property when you wield it (applied to its attack row)."]},
    "observant-phb": {
        "passive_bonus": {"skill-perception": 5, "skill-investigation": 5},
        "notes": ["If you can see a creature's mouth while it speaks a language you understand, you can read its lips."]},
    "keenness-of-the-stone-giant-bgg": {"senses_additive": {"darkvision": 60}},
})

FEAT_EFFECT_QUOTES.update({
    "dragon-hide-xge": "While you aren't wearing armor, you can calculate your AC as 13 + your Dexterity modifier. "
                       "You can use a shield and still gain this benefit.",
    "medium-armor-master-phb": ("Wearing medium armor doesn't impose disadvantage on your Dexterity (Stealth) checks.",
                                "you can add 3, rather than 2, to your AC if you have a Dexterity of 16 or higher"),
    "medium-armor-master-xphb": "you can add 3, rather than 2 to your AC if you have a Dexterity score of 16 or higher",
    "dual-wielder-phb": "You gain a +1 bonus to AC while you are wielding a separate melee weapon in each hand.",
    "revenant-blade-erlw": ("While you are holding a double-bladed scimitar with two hands, you gain a +1 bonus to Armor Class.",
                            "A double-bladed scimitar has the finesse property when you wield it."),
    "observant-phb": "You have a +5 bonus to your passive Wisdom (Perception) and passive Intelligence (Investigation) scores.",
    "keenness-of-the-stone-giant-bgg": "You gain darkvision with a range of 60 feet. If you already have darkvision from "
                                       "another source, its range increases by 60 feet.",
})

# FE5: attack rows. Optional or conditional riders never fold into ``damage`` (F-D2): they are row notes, with the
# character's number filled in. ``attack_notes`` entries are ``{when, text}``; ``when`` is a predicate (or a list of
# predicates, any of which may match) over the attack row:
#   melee / ranged (bool)   the weapon's range kind (the unarmed strike is melee)
#   weapon (bool)           the row is a catalog weapon (not the unarmed strike)
#   properties              {"all": [...], "any": [...]} weapon properties; ``lacks`` [...] properties it must not have
#   damage_types / items / ability_in    the row's damage type / item id / attack ability must be in the list
#   proficient (bool)       the row's proficiency; ``damaging`` (bool) the row has a damage die
# Text placeholders: {pb}, {inc_mod}, {inc_score}, {mod} (the row's ability modifier), {die} (one die of the row's
# damage dice), {dtype}, {dmg:1d4} (a die plus the row's modifier) and the {expr} arithmetic of the FE3 notes.
# ``unarmed`` is an Unarmed Strike the feat improves (F-D6: the row exists only when such a feat is held);
# ``offhand`` and ``finesse_items`` change the row's numbers. Governing sentences: FEAT_EFFECT_QUOTES.
_CROSSBOWS = ["crossbow-hand", "crossbow-light", "crossbow-heavy"]
_FIREARMS = ["musket", "pistol"]

_ATTACK_EFFECTS = {
    "savage-attacker-phb": {"attack_notes": [
        {"when": {"melee": True, "weapon": True},
         "text": "Savage Attacker: once per turn, reroll the weapon's damage dice and use either total."}]},
    "savage-attacker-xphb": {"attack_notes": [
        {"when": {"weapon": True},
         "text": "Savage Attacker: once per turn when you hit, roll the weapon's damage dice twice and use either roll."}]},
    "great-weapon-master-phb": {"attack_notes": [
        {"when": {"melee": True, "weapon": True, "properties": {"all": ["heavy"]}, "proficient": True},
         "text": "Great Weapon Master: before you attack you may take -5 to the attack roll; if it hits, +10 damage."},
        {"when": {"melee": True, "weapon": True},
         "text": "Great Weapon Master: on your turn, a critical hit or reducing a creature to 0 hit points with a melee "
                 "weapon lets you make one melee weapon attack as a bonus action."}]},
    "great-weapon-master-xphb": {"attack_notes": [
        {"when": {"weapon": True, "properties": {"all": ["heavy"]}},
         "text": "Great Weapon Master: +{pb} damage when you hit with this Heavy weapon as part of the Attack action "
                 "on your turn."},
        {"when": {"melee": True, "weapon": True},
         "text": "Great Weapon Master (Hew): after a Critical Hit or reducing a creature to 0 Hit Points with a Melee "
                 "weapon, make one attack with the same weapon as a Bonus Action."}]},
    "sharpshooter-phb": {"attack_notes": [
        {"when": {"ranged": True, "weapon": True, "proficient": True},
         "text": "Sharpshooter: before you attack you may take -5 to the attack roll; if it hits, +10 damage."},
        {"when": {"ranged": True, "weapon": True},
         "text": "Sharpshooter: no disadvantage at long range; ignores half and three-quarters cover."}]},
    "sharpshooter-xphb": {"attack_notes": [
        {"when": {"ranged": True, "weapon": True},
         "text": "Sharpshooter: ignores Half and Three-Quarters Cover; no Disadvantage within 5 feet of an enemy or at "
                 "long range."}]},
    "crossbow-expert-phb": {
        "offhand": {"hand_crossbow_mod": True},   # FE12: Sage Advice - the bonus attack adds the ability modifier
        "attack_notes": [
            {"when": {"items": _CROSSBOWS, "proficient": True},
             "text": "Crossbow Expert: ignore the loading quality; no disadvantage within 5 feet of a hostile creature."},
            {"when": {"items": ["crossbow-hand"]},
             "text": "Crossbow Expert: after attacking with a one-handed weapon in the Attack action, a bonus action "
                     "attack with a hand crossbow you are holding; this bonus action attack adds your ability "
                     "modifier to the damage (official Sage Advice; the offhand damage column)."}]},
    "crossbow-expert-xphb": {
        "offhand": {"light_crossbow_mod": True},
        "attack_notes": [
            {"when": {"items": _CROSSBOWS},
             "text": "Crossbow Expert: ignore the Loading property; no Disadvantage within 5 feet of an enemy."},
            {"when": {"items": _CROSSBOWS, "properties": {"all": ["light"]}},
             "text": "Crossbow Expert (Dual Wielding): the extra attack of the Light property adds your ability "
                     "modifier to the damage."}]},
    "dual-wielder-phb": {
        "offhand": {"non_light_one_handed_melee": True},
        "attack_notes": [
            {"when": {"melee": True, "weapon": True, "lacks": ["two-handed", "light"]},
             "text": "Dual Wielder: two-weapon fighting is allowed with this weapon although it is not Light."}]},
    "dual-wielder-xphb": {
        "offhand": {"dw2024": True},
        "attack_notes": [
            {"when": {"melee": True, "weapon": True, "lacks": ["two-handed"]},
             "text": "Dual Wielder: after attacking with a Light weapon in the Attack action, one extra Bonus Action "
                     "attack with this weapon (no ability modifier to its damage unless negative)."}]},
    "tavern-brawler-phb": {"unarmed": {
        "name": "Tavern Brawler", "die": "1d4", "type": "bludgeoning", "ability": "STR",
        "notes": ["Tavern Brawler: proficient with improvised weapons; when you hit with an unarmed strike or an "
                  "improvised weapon, a bonus action to attempt a grapple."]}},
    "tavern-brawler-xphb": {"unarmed": {
        "name": "Tavern Brawler", "die": "1d4", "type": "bludgeoning", "ability": "STR",
        "notes": ["Tavern Brawler: reroll a 1 on a damage die and use the new roll; when you hit as part of the Attack "
                  "action you can also push the target 5 feet (once per turn)."]}},
    "unarmed-fighting-xphb": {"unarmed": {
        "name": "Unarmed Fighting", "die": "1d6", "die_free_hands": "1d8", "type": "bludgeoning", "ability": "STR",
        "notes": ["Unarmed Fighting: at the start of each of your turns, 1d4 Bludgeoning damage to one creature "
                  "Grappled by you."]}},
    "dragon-hide-xge": {"unarmed": {
        "name": "Dragon Hide claws", "die": "1d4", "type": "slashing", "ability": "STR",
        "notes": ["Dragon Hide: retractable claws (no action to extend or retract) deal slashing damage."]}},
    "revenant-blade-erlw": {
        "finesse_items": ["double-bladed-scimitar"],
        "attack_notes": [
            {"when": {"items": ["double-bladed-scimitar"]},
             "text": "Revenant Blade: Finesse while you wield it (the better of Strength and Dexterity)."}]},
    "piercer-tce": {"attack_notes": [
        {"when": {"damage_types": ["piercing"]},
         "text": "Piercer: once per turn when you hit, reroll one damage die and use the new roll; on a critical hit "
                 "roll one additional damage die."}]},
    "piercer-xphb": {"attack_notes": [
        {"when": {"damage_types": ["piercing"]},
         "text": "Piercer: once per turn when you hit, reroll one damage die and use the new roll; on a Critical Hit "
                 "roll one additional damage die."}]},
    "slasher-tce": {"attack_notes": [
        {"when": {"damage_types": ["slashing"]},
         "text": "Slasher: once per turn when you hit, reduce the target's speed by 10 feet until the start of your "
                 "next turn; on a critical hit it has disadvantage on all attack rolls until then."}]},
    "slasher-xphb": {"attack_notes": [
        {"when": {"damage_types": ["slashing"]},
         "text": "Slasher: once per turn when you hit, reduce the target's Speed by 10 feet until the start of your "
                 "next turn; on a Critical Hit it has Disadvantage on attack rolls until then."}]},
    "crusher-tce": {"attack_notes": [
        {"when": {"damage_types": ["bludgeoning"]},
         "text": "Crusher: once per turn when you hit, move the target 5 feet to an unoccupied space (no more than one "
                 "size larger than you); on a critical hit, attack rolls against it have advantage until the start "
                 "of your next turn."}]},
    "crusher-xphb": {"attack_notes": [
        {"when": {"damage_types": ["bludgeoning"]},
         "text": "Crusher: once per turn when you hit, move the target 5 feet to an unoccupied space (no more than one "
                 "size larger than you); on a Critical Hit, attack rolls against it have Advantage until the start "
                 "of your next turn."}]},
    "polearm-master-phb": {"attack_notes": [
        {"when": {"items": ["glaive", "halberd", "quarterstaff", "spear"]},
         "text": "Polearm Master: after the Attack action with only this weapon, a bonus action attack with its "
                 "opposite end: {dmg:1d4} bludgeoning (same ability modifier)."},
        {"when": {"items": ["glaive", "halberd", "pike", "quarterstaff", "spear"]},
         "text": "Polearm Master: creatures that enter your reach with this weapon provoke an opportunity attack."}]},
    "polearm-master-xphb": {"attack_notes": [
        {"when": [{"items": ["quarterstaff", "spear"]},
                  {"melee": True, "weapon": True, "properties": {"all": ["heavy", "reach"]}}],
         "text": "Polearm Master (Pole Strike): after the Attack action, a Bonus Action attack with the opposite end: "
                 "{dmg:1d4} Bludgeoning."},
        {"when": [{"items": ["quarterstaff", "spear"]},
                  {"melee": True, "weapon": True, "properties": {"all": ["heavy", "reach"]}}],
         "text": "Polearm Master (Reactive Strike): Reaction melee attack against a creature that enters your reach."}]},
    "charger-phb": {"attack_notes": [
        {"when": {"melee": True, "weapon": True},
         "text": "Charger: after the Dash action, a bonus action melee attack; if you moved at least 10 feet in a "
                 "straight line first, +5 damage on a hit (not included in the damage shown)."}]},
    "charger-xphb": {"attack_notes": [
        {"when": {"melee": True},
         "text": "Charger (Charge Attack): after moving at least 10 feet in a straight line toward the target, +1d8 "
                 "damage or push it up to 10 feet (once per turn; not included in the damage shown)."}]},
    "gunner-tce": {"attack_notes": [
        {"when": {"items": _FIREARMS},
         "text": "Gunner: ignore the loading property; no disadvantage within 5 feet of a hostile creature."}]},
    "elven-accuracy-xge": {"attack_notes": [
        {"when": {"ability_in": ["DEX", "INT", "WIS", "CHA"]},
         "text": "Elven Accuracy: with advantage on this attack, you can reroll one of the dice once."}]},
    "orcish-fury-xge": {"attack_notes": [
        {"when": {"weapon": True, "damaging": True},
         "text": "Orcish Fury: on a hit, roll one of the weapon's damage dice again for +{die} {dtype} extra damage "
                 "(once per short or long rest)."}]},
    "poisoner-tce": {"attack_notes": [
        {"when": {"weapon": True},
         "text": "Poisoner: apply a poison dose as a bonus action; a creature damaged by it must succeed on a DC 14 "
                 "Constitution save or take 2d8 poison damage and become poisoned until the end of your next turn."}]},
    "poisoner-xphb": {"attack_notes": [
        {"when": {"weapon": True},
         "text": "Poisoner: apply a poison dose as a Bonus Action; a creature damaged by it must succeed on a DC "
                 "{8+inc_mod+pb} Constitution save or take 2d8 Poison damage and be Poisoned until the end of your "
                 "next turn."}]},
    "bomber-abh": {"attack_notes": [
        {"when": {"weapon": True, "properties": {"any": ["thrown"]}},
         "text": "Bomber: no Disadvantage at long range with Thrown weapons; a thrown vial or flask can target "
                 "something you see within 40 feet."}]},
    "boon-of-irresistible-offense-xphb": {"attack_notes": [
        {"when": {"damage_types": ["bludgeoning", "piercing", "slashing"]},
         "text": "Boon of Irresistible Offense: your {dtype} damage always ignores Resistance."},
        {"when": {},
         "text": "Boon of Irresistible Offense: on a 20 on the d20, extra damage equal to {inc_score} (the score you "
                 "increased), of the attack's type."}]},
}
FEAT_EFFECTS.update({
    index: ({**FEAT_EFFECTS.get(index, {}), **effect}) for index, effect in _ATTACK_EFFECTS.items()})

FEAT_EFFECT_QUOTES.update({
    "savage-attacker-phb": "Once per turn when you roll damage for a melee weapon attack, you can reroll the weapon's damage dice and use either total.",
    "savage-attacker-xphb": "Once per turn when you hit a target with a weapon, you can roll the weapon's damage dice twice and use either roll against the target.",
    "great-weapon-master-phb": ("Before you make a melee attack with a heavy weapon that you are proficient with, you can choose to take a -5 penalty to the attack roll. If the attack hits, you add +10 to the attack's damage.",
                                "you can make one melee weapon attack as a bonus action"),
    "great-weapon-master-xphb": ("The extra damage equals your Proficiency Bonus.",
                                 "you can make one attack with the same weapon as a Bonus Action"),
    "sharpshooter-phb": ("Before you make an attack with a ranged weapon that you are proficient with, you can choose to take a -5 penalty to the attack roll. If the attack hits, you add +10 to the attack's damage.",
                         "Attacking at long range doesn't impose disadvantage on your ranged weapon attack rolls."),
    "sharpshooter-xphb": ("Your ranged attacks with weapons ignore Half Cover and Three-Quarters Cover.",
                          "Being within 5 feet of an enemy doesn't impose Disadvantage on your attack rolls with Ranged weapons."),
    "crossbow-expert-phb": ("You ignore the loading quality of crossbows with which you are proficient.",
                            "you can use a bonus action to attack with a hand crossbow you are holding"),
    "crossbow-expert-xphb": ("You ignore the Loading property of the Hand Crossbow, Heavy Crossbow, and Light Crossbow",
                             "you can add your ability modifier to the damage of the extra attack if that attack is with a crossbow that has the Light property"),
    "dual-wielder-phb": ("You gain a +1 bonus to AC while you are wielding a separate melee weapon in each hand.",
                         "You can use two-weapon fighting even when the one-handed melee weapons you are wielding aren't light."),
    "dual-wielder-xphb": ("you can make one extra attack as a Bonus Action later on the same turn with a different weapon, which must be a Melee weapon that lacks the Two-Handed property",
                          "You don't add your ability modifier to the extra attack's damage unless that modifier is negative."),
    "dragon-hide-xge": ("While you aren't wearing armor, you can calculate your AC as 13 + your Dexterity modifier. "
                        "You can use a shield and still gain this benefit.",
                        "you deal slashing damage equal to 1d4 + your Strength modifier, instead of the normal bludgeoning damage for an unarmed strike"),
    "orcish-fury-xge": ("you can't use it again until you finish a short or long rest",
                        "you can roll one of the weapon's damage dice an additional time and add it as extra damage of the weapon's damage type"),
    "tavern-brawler-phb": "Your unarmed strike uses a d4 for damage.",
    "tavern-brawler-xphb": ("you can deal Bludgeoning damage equal to 1d4 plus your Strength modifier instead of the normal damage of an Unarmed Strike",
                            "you can reroll the die if it rolls a 1"),
    "unarmed-fighting-xphb": ("you can deal Bludgeoning damage equal to 1d6 plus your Strength modifier instead of the normal damage of an Unarmed Strike",
                              "If you aren't holding any weapons or a Shield when you make the attack roll, the d6 becomes a d8."),
    "piercer-tce": "Once per turn, when you hit a creature with an attack that deals piercing damage, you can reroll one of the attack's damage dice, and you must use the new roll.",
    "piercer-xphb": "Once per turn, when you hit a creature with an attack that deals Piercing damage, you can reroll one of the attack's damage dice, and you must use the new roll.",
    "slasher-tce": "Once per turn when you hit a creature with an attack that deals slashing damage, you can reduce the speed of the target by 10 feet until the start of your next turn.",
    "slasher-xphb": "Once per turn when you hit a creature with an attack that deals Slashing damage, you can reduce the Speed of that creature by 10 feet until the start of your next turn.",
    "crusher-tce": "Once per turn, when you hit a creature with an attack that deals bludgeoning damage, you can move it 5 feet to an unoccupied space, provided the target is no more than one size larger than you.",
    "crusher-xphb": "Once per turn, when you hit a creature with an attack that deals Bludgeoning damage, you can move it 5 feet to an unoccupied space if the target is no more than one size larger than you.",
    "polearm-master-phb": ("The weapon's damage die for this attack is a d4, and the attack deals bludgeoning damage.",
                           "While you are wielding a glaive, halberd, pike, quarterstaff, or spear, other creatures provoke an opportunity attack from you when they enter the reach you have with that weapon."),
    "polearm-master-xphb": ("The weapon deals Bludgeoning damage, and the weapon's damage die for this attack is a d4.",
                            "you can take a Reaction to make one melee attack against a creature that enters the reach you have with that weapon"),
    "charger-phb": "you either gain a +5 bonus to the attack's damage roll",
    "charger-xphb": "gain a 1d8 bonus to the attack's damage roll, or push the target up to 10 feet away if it is no more than one size larger than you",
    "gunner-tce": ("You ignore the loading property of firearms.",
                   "Being within 5 feet of a hostile creature doesn't impose disadvantage on your ranged attack rolls."),
    "elven-accuracy-xge": "Whenever you have advantage on an attack roll using Dexterity, Intelligence, Wisdom, or Charisma, you can reroll one of the dice once.",
    "poisoner-tce": ("When you make a damage roll that deals poison damage, it ignores resistance to poison damage.",
                     "that creature must succeed on a 14 Constitution saving throw or take 2d8 poison damage"),
    "poisoner-xphb": ("Constitution saving throw (8 plus the modifier of the ability increased by this feat and your Proficiency Bonus) or take 2d8 Poison damage",),
    "bomber-abh": ("you can target an object or creature you can see within 40 feet of yourself",
                   "Attacking at long range doesn't impose Disadvantage on your attack rolls with Thrown weapons."),
    "boon-of-irresistible-offense-xphb": ("The Bludgeoning, Piercing, and Slashing damage you deal always ignores Resistance.",
                                          "you can deal extra damage to the target equal to the ability score increased by this feat"),
})

# FE6: skill and Expertise rules. The flags are read by engine.resolve when it builds the feat's cards:
# ``prof_or_expertise`` marks the skill card (a pick the character is already proficient in, at the feat's
# position in the build, becomes Expertise); ``lacks_expertise`` marks the Expertise card (a skill that already
# has Expertise is refused under EVERY ruleset: the feats' own rule). Echoing Soul and Harper Agent are carried
# by catalog fields (the skill count override and the Thieves' Cant language), so they are ``data_only``.
FEAT_EFFECTS.update({
    "keen-mind-xphb": {"prof_or_expertise": True},
    "observant-xphb": {"prof_or_expertise": True},
    "skill-expert-tce": {"lacks_expertise": True},
    "prodigy-xge": {"lacks_expertise": True},
    "skill-expert-xphb": {"lacks_expertise": True},
    "boon-of-skill-xphb": {"lacks_expertise": True},
    "echoing-soul-rhw": {"data_only": True},
    "harper-agent-frhof": {"data_only": True},
})
FEAT_EFFECT_QUOTES.update({
    "keen-mind-xphb": "If you lack proficiency in the chosen skill, you gain proficiency in it, and if you already have proficiency in it, you gain Expertise in it.",
    "observant-xphb": "If you lack proficiency with the chosen skill, you gain proficiency in it, and if you already have proficiency in it, you gain Expertise in it.",
    "skill-expert-tce": "The skill you choose must be one that isn't already benefiting from a feature, such as Expertise, that doubles your proficiency bonus.",
    "prodigy-xge": "The skill you choose must be one that isn't already benefiting from a feature, such as Expertise, that doubles your proficiency bonus.",
    "skill-expert-xphb": "Choose one skill in which you have proficiency but lack Expertise.",
    "boon-of-skill-xphb": "Choose one skill in which you lack Expertise.",
    "echoing-soul-rhw": "You have proficiency in two skills of your choice.",
    "harper-agent-frhof": "You know Thieves' Cant.",
})

# FE7: resistance, damage-type and variant picks. The cards are built by ``resolve._feat_extra_templates`` for every
# feat instance (background, species, Fighting Style, Lessons, ASI) under the cid ``<prefix>:<suffix>``. The picks of a
# ``resist_choice`` join ``damageModifiers.resistances``; Scion's ``resist_by_variant`` reads the ``:spell-variant`` pick
# the spell machinery already offers (no extra card). Choices that the text lets you change on a rest (Boon of Energy
# Resistance) stay editable build-time cards (F-D7). ``{choice}`` in a note is the instance's pick.
_ENERGY = ["acid", "cold", "fire", "lightning", "necrotic", "poison", "psychic", "radiant", "thunder"]

FEAT_EFFECTS.update({
    "dragonscarred-frhof": {
        "resist_choice": {"count": 1, "options": ["acid", "cold", "fire", "lightning", "poison"]},
        "notes": ["Resistance to the chosen damage type: {choice}.",
                  "When you deal damage as part of the Attack or Magic action on your turn, you can use the Dragon's "
                  "Terror benefit of Cult of the Dragon Initiate as a Bonus Action that turn."]},
    "boon-of-energy-resistance-xphb": {
        "resist_choice": {"count": 2, "options": _ENERGY},
        "notes": ["Resistance to two damage types: {choice}. You can change both choices when you finish a Long Rest.",
                  "Energy Redirection (Reaction, when you take damage of a chosen type): a creature you can see within "
                  "60 feet makes a Dexterity save, DC {8 + con_mod + pb}, or takes 2d12 + {con_mod} damage of that type."]},
    "portal-jumper-au": {
        "resist_choice": {"count": 1, "options": ["necrotic", "psychic", "radiant"]},
        "notes": ["Resistance to the chosen damage type: {choice}."],
        "resources": [{"name": "Portal Step", "uses": "pb", "recharge": "long",
                       "note": "Spend 15 feet of movement to teleport to an unoccupied space you can see within 15 feet; "
                               "once per turn."}]},
    "spell-resistant-au": {
        "resist_choice": {"count": 1, "options": ["necrotic", "psychic", "radiant", "thunder"]},
        "notes": ["Resistance to the chosen damage type: {choice}."],
        "resources": [{"name": "Magic Resistant", "uses": "pb", "recharge": "long",
                       "note": "When you would fail a saving throw against a spell or magical effect, roll 1d6 and add "
                               "it to the total."}]},
    "scion-of-the-outer-planes-sato": {
        "resist_by_variant": {"chaotic-outer-plane": "poison", "evil-outer-plane": "necrotic",
                              "good-outer-plane": "radiant", "lawful-outer-plane": "force", "the-outlands": "psychic"},
        "notes": ["Planar Infusion damage resistance: {choice}."]},
    "elemental-adept-phb": {
        "damage_type_choice": {"options": ["acid", "cold", "fire", "lightning", "thunder"],
                               "distinct_across_repeats": True},
        "notes": ["Chosen damage type: {choice}. Spells you cast ignore resistance to it, and you can treat any 1 on a "
                  "damage die of such a spell as a 2."]},
    "elemental-adept-xphb": {
        "damage_type_choice": {"options": ["acid", "cold", "fire", "lightning", "thunder"],
                               "distinct_across_repeats": True},
        "notes": ["Energy Mastery damage type: {choice}. Spells you cast ignore Resistance to it, and you can treat any 1 "
                  "on a damage die of such a spell as a 2."]},
    "strike-of-the-giants-bgg": {
        "variant_choice": {
            "suffix": "giant-type", "label": "Giant Strike", "description": "Choose the giant strike this feat grants.",
            "options": [
                {"id": "cloud", "label": "Cloud Strike", "note": "Extra 1d4 thunder damage; a creature must succeed on a Wisdom save or you become invisible to it until the start of your next turn or until immediately after you make an attack roll or cast a spell."},
                {"id": "fire", "label": "Fire Strike", "note": "Extra 1d10 fire damage."},
                {"id": "frost", "label": "Frost Strike", "note": "Extra 1d6 cold damage; a creature must succeed on a Constitution save or its speed is reduced to 0 until the start of your next turn."},
                {"id": "hill", "label": "Hill Strike", "note": "Extra 1d6 damage of the weapon's type; a creature must succeed on a Strength save or have the prone condition."},
                {"id": "stone", "label": "Stone Strike", "note": "Extra 1d6 force damage; a creature must succeed on a Strength save or be pushed 10 feet from you in a straight line."},
                {"id": "storm", "label": "Storm Strike", "note": "Extra 1d6 lightning damage; a creature must succeed on a Constitution save or have disadvantage on attack rolls until the start of your next turn."},
            ]},
        "notes": ["{choice}: once per turn, when you hit with a melee weapon attack or a thrown ranged weapon attack, "
                  "you can imbue the attack. Save DC {8 + pb + max(str_mod, con_mod)} (Strength or Constitution)."],
        "resources": [{"name": "Strike of the Giants", "uses": "pb", "recharge": "long",
                       "note": "{choice}, once per turn on a melee or thrown weapon hit."}]},
})
FEAT_EFFECT_QUOTES.update({
    "dragonscarred-frhof": "choose Acid, Cold, Fire, Lightning, or Poison. You have Resistance to the chosen damage type.",
    "boon-of-energy-resistance-xphb": (
        "You gain Resistance to two of the following damage types of your choice: Acid, Cold, Fire, Lightning, Necrotic, "
        "Poison, Psychic, Radiant, or Thunder. Whenever you finish a Long Rest, you can change your choices.",
        "(8 plus your Constitution modifier and Proficiency Bonus) or take damage equal to 2d12 plus your Constitution modifier"),
    "portal-jumper-au": (
        "You have Resistance to one of the following damage types: Necrotic, Psychic, or Radiant (choose when you select this feat).",
        "You can use this benefit a number of times equal to your Proficiency Bonus but only once per turn, and you regain "
        "all expended uses when you finish a Long Rest."),
    "spell-resistant-au": (
        "You have Resistance to one of the following damage types (choose when you gain this feat): Necrotic, Psychic, Radiant, or Thunder.",
        "you can roll 1d6 and add the number rolled to the save's total",
        "You can use this benefit a number of times equal to your Proficiency Bonus, and you regain all expended uses when you finish a Long Rest."),
    "scion-of-the-outer-planes-sato": (
        "Your choice gives you resistance to a damage type and the ability to cast a cantrip, as specified in the table.",
        "Chaotic Outer Plane Poison", "Evil Outer Plane Necrotic", "Good Outer Plane Radiant", "Lawful Outer Plane Force",
        "The Outlands Psychic"),
    "elemental-adept-phb": (
        "choose one of the following damage types: acid, cold, fire, lightning, or thunder.",
        "Spells you cast ignore resistance to damage of the chosen type.",
        "Each time you do so, you must choose a different damage type."),
    "elemental-adept-xphb": (
        "Choose one of the following damage types: Acid, Cold, Fire, Lightning, or Thunder.",
        "Spells you cast ignore Resistance to damage of the chosen type.",
        "you must choose a different damage type each time for Energy Mastery."),
    "strike-of-the-giants-bgg": (
        "choose one of the benefits listed below.",
        "The target takes an extra 1d4 thunder damage.", "The target takes an extra 1d10 fire damage.",
        "The target takes an extra 1d6 cold damage.", "The target takes an extra 1d6 damage of the weapon's type.",
        "The target takes an extra 1d6 force damage.", "The target takes an extra 1d6 lightning damage.",
        "The saving throw DC for these effects equals 8 + your proficiency bonus + your Strength or Constitution modifier.",
        "You can use this feat a number of times equal to your proficiency bonus, and you regain all expended uses when you finish a long rest."),
})

# Feats not classified yet. Each slice removes the ones it covers (by adding them to FEAT_EFFECTS);
# FE10 empties it.
# FE8: Weapon Master. PHB gives four weapon proficiencies (card ``:weapon-choice``, ids via
# ``reference_data.weapon_proficiency_id``, added to the proficient weapons before the C2 mastery gate); XPHB gives one
# Weapon Mastery pick among weapons the character is proficient with (card ``:weapon-mastery``, changeable on a Long
# Rest: an editable build-time card, F-D7). Categories name the weapon_category values the card offers.
FEAT_EFFECTS.update({
    "weapon-master-phb": {
        "weapon_proficiency_choice": {"count": 4, "categories": ["simple", "martial"]},
        "notes": ["Proficiency with four chosen weapons (see the choice)."]},
    "weapon-master-xphb": {
        "mastery_choice": {"count": 1, "categories": ["simple", "martial"]},
        "notes": ["Mastery Property: you can change the kind of weapon after a Long Rest."]},
})
FEAT_EFFECT_QUOTES.update({
    "weapon-master-phb": "You gain proficiency with four weapons of your choice. Each one must be a simple or a martial weapon.",
    "weapon-master-xphb": (
        "use the mastery property of one kind of Simple or Martial weapon of your choice, provided you have proficiency with it.",
        "Whenever you finish a Long Rest, you can change the kind of weapon to another eligible kind."),
})

# FE9: option-pick feats. ``option_picks`` {kind, count} asks for one card of the feat's own options, cid
# ``<prefix>:<suffix>``: fighting-style -> ``:fighting-style`` (the six SRD fighter styles; the pick joins the class
# feature list, so CLASS_FEATURE_EFFECTS applies Archery / Defense / Dueling / ...), maneuver -> ``:maneuvers`` (the
# Battle Master list, PHB + TCE), metamagic -> ``:metamagic`` (the SRD Metamagic options), invocation -> ``:invocation``
# (the SRD invocations, prerequisites only for a Warlock who meets them; the effects reach
# ``features.invocation_effects``). Resource keys ``die`` and ``dc`` (an expression over pb / <abl>_mod) are new.
FEAT_EFFECTS.update({
    "fighting-initiate-tce": {
        "option_picks": {"kind": "fighting-style", "count": 1},
        "notes": ["Fighting Style: {choice}. When you reach a level that grants Ability Score Improvement you can replace "
                  "it with another fighter style you don't have."]},
    "eldritch-adept-tce": {
        "option_picks": {"kind": "invocation", "count": 1},
        "notes": ["Eldritch Invocation: {choice}. Only an invocation without a prerequisite, or one a Warlock who meets "
                  "it takes. Your spellcasting ability for it is chosen with the feat. When you gain a level you can "
                  "replace it with another warlock invocation."]},
    "martial-adept-phb": {
        "option_picks": {"kind": "maneuver", "count": 2},
        "resources": [{
            "name": "Superiority Die (Martial Adept)", "uses": 1, "recharge": "short-or-long", "die": "d6",
            "dc": "8 + pb + max(str_mod, dex_mod)",
            "note": "Maneuvers: {choice}. This die is added to any superiority dice you have from another source "
                    "(it stays a d6)."}]},
    "metamagic-adept-tce": {
        "option_picks": {"kind": "metamagic", "count": 2},
        "resources": [{
            "name": "Sorcery Points (Metamagic Adept)", "uses": 2, "recharge": "long",
            "note": "Metamagic: {choice}. Added to any sorcery points you have from another source but usable only on "
                    "Metamagic; you can use one Metamagic option per spell unless the option says otherwise."}]},
})
FEAT_EFFECT_QUOTES.update({
    "fighting-initiate-tce": (
        "If you already have a style, the one you choose must be different.",
        "Whenever you reach a level that grants the Ability Score Improvement feature, you can replace this feat's "
        "fighting style with another one from the fighter class that you don't have."),
    "eldritch-adept-tce": (
        "Your spellcasting ability for the invocation is Intelligence, Wisdom, or Charisma (choose when you select this feat).",
        "If the invocation has a prerequisite of any kind, you can choose that invocation only if you're a warlock who "
        "meets the prerequisite.",
        "Whenever you gain a level, you can replace the invocation with another one from the warlock class."),
    "martial-adept-phb": (
        "of your choice from among those available to the Battle Master archetype in the fighter class.",
        "the saving throw DC equals 8 + your proficiency bonus + your Strength or Dexterity modifier (your choice).",
        "You gain one superiority die, which is a d6 (this die is added to any superiority dice you have from another source).",
        "You regain your expended superiority dice when you finish a short or long rest."),
    "metamagic-adept-tce": (
        "of your choice from the sorcerer class.",
        "Whenever you reach a level that grants the Ability Score Improvement feature, you can replace one of these "
        "Metamagic options with another one from the sorcerer class.",
        "You gain 2 sorcery points to spend on Metamagic (these points are added to any sorcery points you have from "
        "another source but can be used only on Metamagic). You regain all spent sorcery points when you finish a long rest."),
})

# FE10: the resource and note tail (every feat still pending after FE9) and the notes / resources that earlier slices
# left out of entries they had classified for their number. See feat_effects_tail for the rules.
from catalog.feat_effects_tail import COMPLETION, COMPLETION_QUOTES, TAIL_EFFECTS, TAIL_QUOTES  # noqa: E402

assert not set(TAIL_EFFECTS) & set(FEAT_EFFECTS), "the FE10 tail must only classify feats that were still pending"
FEAT_EFFECTS.update(TAIL_EFFECTS)
FEAT_EFFECT_QUOTES.update(TAIL_QUOTES)
for _index, _extra in COMPLETION.items():
    _entry = dict(FEAT_EFFECTS[_index])
    for _key in ("notes", "resources"):
        if _key in _extra:
            _entry[_key] = list(_entry.get(_key, [])) + list(_extra[_key])
    FEAT_EFFECTS[_index] = _entry
# Quotes pinning the text that FE10 added to an entry of an earlier slice (their first quote stays in FEAT_EFFECT_QUOTES).
FEAT_EFFECT_EXTRA_QUOTES: dict[str, tuple[str, ...]] = {
    index: (quote if isinstance(quote, tuple) else (quote,)) for index, quote in COMPLETION_QUOTES.items()}

# Empty since FE10: every catalog feat is classified.
FEAT_PENDING: frozenset[str] = frozenset(FEAT_KINDS) - frozenset(FEAT_EFFECTS)
