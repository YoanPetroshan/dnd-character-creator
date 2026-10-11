"""Feat effect scan table, vocabulary and coverage ratchet (FE0, data only, no behaviour change).

Pure data: this module imports nothing and nothing in the engine reads it yet. Later FE slices
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
    resist_choice               {count, options}
    resist_by_variant           {variant: damage type}
    damage_type_choice          {options, distinct_across_repeats}
    weapon_proficiency_choice   {count, categories}
    mastery_choice              {count}
    option_picks                {kind, count, pool}
    unarmed                     {die, die_free_hands, type, ability, notes}
    offhand                     {non_light_one_handed_melee | light_crossbow_mod | dw2024: True}
    finesse_items               [item index]
    attack_notes                [{when: {predicate}, text}]
    resources                   [{name, uses, recharge, die, dice, pool, dc, note}]
    notes                       [text]
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
    "resist_by_variant", "damage_type_choice", "weapon_proficiency_choice", "mastery_choice",
    "option_picks", "unarmed", "offhand", "finesse_items", "attack_notes", "resources", "notes",
    "data_only",
})

SCAN_KINDS: frozenset[str] = frozenset(
    {"numeric", "choice", "attack", "resource", "notes", "fighting-style"})

# Set to True by FE10, the slice that empties FEAT_PENDING; the ratchet test then requires it.
FE10_DONE = False

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

# Feats not classified yet. Each slice removes the ones it covers (by adding them to FEAT_EFFECTS);
# FE10 empties it.
FEAT_PENDING: frozenset[str] = frozenset(FEAT_KINDS) - frozenset(FEAT_EFFECTS)
