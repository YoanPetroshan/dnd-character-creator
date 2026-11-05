"""F0: golden guard that `mixed` and `2014` resolve() output never changes during the 2024 stages.

The 2024 chassis series (C6b ... C9b) may only change behaviour under ``ruleset == "2024"``.
This file pins ~230 fully filled drafts, each resolved under ``mixed`` and ``2014`` (never 2024):

- the 12 SRD classes at levels 1, 3, 11 and 20 (first SRD subclass from level 3), every pending
  choice auto-filled with the kitchen-sink "first option" filler, under ``sources`` ``[]`` and
  ``["srd"]``;
- five multiclass drafts (Wizard 1 / Fighter 1, Rogue 3 / Bard 2, Warlock 5 / Sorcerer 3,
  Cleric 1 / Druid 1, Barbarian 3 / Monk 2);
- every non-2024 kitchen-sink entry (own ruleset), under both ``sources`` values.

The golden file stores the FILLED DRAFT next to its resolve() result, so a later change to the
filler or to the set of pending cards cannot move the input. The test compares the freshly
resolved result with the stored one after a JSON round trip (exact equality).

Deliberate change: a later slice may add an explicitly listed additive key to ``STRIP`` (a
mapping of dotted paths, see ``strip``). Any other difference fails. To regenerate the golden
on purpose (only after the user agreed that mixed/2014 output may change), run from ``server/``:

    ../.venv/bin/python tests/test_c_series_golden.py --regenerate

FE12 appended the feat-holding kitchen-sink cases with ``--append`` (existing cases asserted unchanged and rewritten
byte for byte; only the new names are added). Use ``--append`` for any later addition.

REBASELINE MODE (RP6 / P0). A slice that deliberately changes mixed / 2014 output (the E11 slices and the
RPX extras) must not use ``--regenerate``. It adds an entry to ``REBASELINES`` (append-only; the entries so far are
RP7, RPF, RP15, RP16, RPX1, RPX2 and RPX3, see the constant below):

    REBASELINES["RP7"] = {"cases": ["mixed/*/monk*", "2014/*/monk*"],      # fnmatch over case names
                          "paths": [r"^result[.]choices[[]class:monk:1:prof-choice-1[]]"],  # regexes over paths
                          "why": "SRD Monk tool or instrument choice"}

The ``paths`` allowlist is written from the slice's rule matrix, never copied from the dry-run output. Then, from
``server/``:

    ../.venv/bin/python tests/test_c_series_golden.py --rebaseline RP7 --dry-run   # prints the diff, writes nothing
    ../.venv/bin/python tests/test_c_series_golden.py --rebaseline RP7             # writes the gz, prints the summary

Cases NOT matching ``cases`` must re-resolve to their stored result (written back unchanged). For matching cases
``ks.fill`` fills only the cards that are now ``pending`` (existing picks stay), the draft is re-resolved, and
``{draft, result}`` old vs new is diffed on normalized paths: lists of dicts that all carry a unique ``id`` become dicts
keyed by id (path ``result.choices[<id>].options[<id>]``), so an inserted card does not shift every index. Every changed
path must match a ``paths`` regex or the run fails; a matching case with no diff prints a warning (pattern too wide).
Cases are never deleted (new ones come only through ``--append``). Paste the printed summary into the slice's
ARCHITECTURE section and name the rebaseline in the commit message. ``STRIP`` is applied to both sides of the compare.

The file was first written from the engine at commit 81fce17 (before any C-series work). The
whole module skips when the local 5etools data (classes, official, spells) is absent.
"""
from __future__ import annotations

import copy
import fnmatch
import gzip
import json
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from catalog import official_source as official  # noqa: E402
from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
import kitchen_sink as ks  # noqa: E402

GOLDEN = pathlib.Path(__file__).parent / "golden" / "c_series_mixed_2014_baseline.json.gz"

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger",
           "rogue", "sorcerer", "warlock", "wizard"]
LEVELS = (1, 3, 11, 20)
RULESETS = ("mixed", "2014")
SOURCES = ([], ["srd"])
MULTICLASS = {
    "wizard1-fighter1": [("wizard", 1), ("fighter", 1)],
    "rogue3-bard2": [("rogue", 3), ("bard", 2)],
    "warlock5-sorcerer3": [("warlock", 5), ("sorcerer", 3)],
    "cleric1-druid1": [("cleric", 1), ("druid", 1)],
    "barbarian3-monk2": [("barbarian", 3), ("monk", 2)],
}

# Additive keys a later slice may legitimately add under mixed/2014: dotted paths, "[]" = every
# list element. Empty on purpose; adding to it needs the user's agreement and a note here.
# "derived.featResources": FE3 additive key (feat resources, e.g. Lucky), always [] for the feat-less golden
# drafts; user-approved feat-effects series (decision F-D1). Both sides are stripped, nothing else changes.
# "derived.speciesResources": W5a additive key (species trait resources), always [] for the golden drafts (SRD Human).
STRIP: tuple[str, ...] = ("derived.featResources", "derived.speciesResources")

# RP6 / P0: append-only record of deliberate mixed / 2014 changes, see the module docstring. slice id ->
# {"cases": [fnmatch over case names], "paths": [regexes over normalized paths], "why": one line}. Append-only; one entry per deliberate change.
REBASELINES: dict[str, dict] = {
    # RP7 / E11c: the SRD Monk "one type of artisan's tools or one musical instrument" is now a card (the nested
    # choice is flattened), so the primary-Monk cases gain the card, the filler's first-option pick, and that tool in
    # the proficiencies. The multiclass Barbarian 3 / Monk 2 (Monk is secondary) must not move.
    "RP7": {
        "cases": ["*/src-*/monk[0-9]*", "ks/src-*/monk14"],
        "paths": [
            r"^result\.choices\[class:monk:1:prof-choice-1\]$",            # the new card, reported once at its root
            r"^draft\.classes\[0\]\.choices\.class:monk:1:prof-choice-1$",   # the filler's pick, in the draft (Monk first)
            r"^result\.sheet\.proficiencies\.tools$",                      # the picked tool
        ],
        "why": "SRD Monk tool or instrument choice (E11c)",
    },
    # RPF: PHB "you can't gain the same proficiency twice": the later of two ordinary skill pick cards loses a
    # duplicate. Only the golden's multiclass Rogue 3 / Bard 2 holds one (the Bard multiclass skill card, entered
    # second, was filled with Acrobatics like the Rogue's card). The filler re-picks the first enabled skill
    # (Animal Handling), so: the Bard multiclass card (options disabled "already proficient", the new pick, the draft
    # pick), the skill list, the new skill's modifier and its option in the Rogue's expertise card (a skill that
    # is now proficient becomes eligible for Expertise) move, nothing else.
    "RPF": {
        "cases": ["*/src-*/multi-rogue3-bard2"],
        "paths": [
            r"^draft\.classes\[1\]\.choices\.class:bard:multiclass-prof-choice-0\[0\]$",   # the filler's new pick
            r"^result\.choices\[class:bard:multiclass-prof-choice-0\]",                       # options disabled, selected
            r"^result\.choices\[class:rogue:1:expertise-choice:rogue-expertise-1\]\.options\[skill-animal-handling\]\.(disabled|disabledReason)$",
            r"^result\.sheet\.proficiencies\.skills$",                                         # the replacement skill
            r"^result\.derived\.skills\.skill-animal-handling$",                                # its modifier
        ],
        "why": "duplicate skill pick between ordinary class cards (RPF)",
    },
    # RP15 / E11b: the SRD Wizard Spell Mastery (18) and Signature Spell (20) are cards under mixed and 2014 (same cids
    # as 2024). Only the Wizard 20 cases hold them. Rule matrix: the three new cards; the filler's picks in the
    # draft; sheet.spells[wizard].spellMastery / signatureSpells / alwaysPrepared (signature picks are always
    # prepared; Spell Mastery is not); the resource wizard:signature-spells; the Spell Mastery / Signature Spell
    # sheet.features rows' picked names; the prepared card's disabled flags (always-prepared signature picks).
    "RP15": {
        "cases": ["*/src-*/wizard20"],
        "paths": [
            r"^result\.choices\[class:wizard:18:spell-mastery-[12]\]$",           # the new cards, reported once at the root
            r"^result\.choices\[class:wizard:20:signature-spells\]$",
            r"^draft\.classes\[0\]\.choices\.class:wizard:(18:spell-mastery-[12]|20:signature-spells)$",  # filler picks
            r"^result\.sheet\.spells\[\d+\]\.(spellMastery|signatureSpells|alwaysPrepared)$",
            r"^result\.derived\.classResources\[wizard:signature-spells\]$",
            r"^result\.sheet\.features\[\d+\]\.choice$",                          # the two rows' picked spell names
            r"^result\.choices\[class:wizard:spells-known\]\.options\[[^\]]+\]\.(disabled|disabledReason)$",
        ],
        "why": "SRD Wizard Spell Mastery / Signature Spell cards (E11b)",
    },
    # RP16 / E11a: SRD Bard Magical Secrets (10 / 14 / 18). The Bard known-spells card also offers every other class's
    # spells up to the highest slot level plus their cantrips, labelled "(Magical Secrets)", and its description names
    # the cap. Only the Bard 11 and 20 cases hold the feature (Bard 1 / 3 are below 10; the multiclass Bard is 2).
    # Rule matrix: the added options (reported once at their roots), a changed option's label / group / disabled flag,
    # the description. The stored picks (the old list's first spells), the count, the selection and every other card
    # stay as they are.
    "RP16": {
        "cases": ["*/src-*/bard11", "*/src-*/bard20"],
        "paths": [
            r"^result\.choices\[class:bard:spells-known\]\.options\[[^\]]+\]$",       # an added option, at its root
            r"^result\.choices\[class:bard:spells-known\]\.options\[[^\]]+\]\.(label|group|disabled|disabledReason)$",
            r"^result\.choices\[class:bard:spells-known\]\.description$",
        ],
        "why": "SRD Bard Magical Secrets (E11a)",
    },
    # RPX1 / Extra 1: the SRD College of Lore (the golden's first SRD Bard subclass, Bard 3 / 11 / 20): Bard 3 Bonus
    # Proficiencies (3 skills, a card at the RP12 position) and Bard 6 Additional Magical Secrets (2 spells of any
    # class, not counted in Spells Known). Cases: the Bard 3 / 11 / 20 cases; the multiclass Bard 2 has no subclass and
    # the Bard 10 kitchen sink holds no Lore. Rule matrix: the two new cards (reported once at their roots) and the
    # filler's picks in the draft; the picked skills in sheet.proficiencies.skills, their derived.skills modifiers;
    # the Bard 3 / 10 Expertise cards' options (a Lore skill is proficient, so eligible for Expertise); the Cantrips / Spells Known cards' options (a spell picked as an Additional Magical Secret is
    # disabled there); sheet.spells[bard].known (the two picks); the two Lore rows' picked names in sheet.features.
    # Stored picks of existing cards, counts and every other card stay as they are.
    "RPX1": {
        "cases": ["*/src-*/bard3", "*/src-*/bard11", "*/src-*/bard20"],
        "paths": [
            r"^result\.choices\[class:bard:3:feature:bonus-proficiencies\]$",
            r"^result\.choices\[class:bard:6:feature:additional-magical-secrets\]$",
            r"^draft\.classes\[0\]\.choices\.class:bard:(3:feature:bonus-proficiencies|6:feature:additional-magical-secrets)$",
            r"^result\.sheet\.proficiencies\.skills$",
            r"^result\.derived\.skills\.skill-[a-z-]+$",
            r"^result\.choices\[class:bard:(3|10):expertise-choice:bard-expertise-[12]\]\.options\[skill-[a-z-]+\]\.(disabled|disabledReason)$",
            r"^result\.choices\[class:bard:spells-(cantrips|known)\]\.options\[[^\]]+\]\.(disabled|disabledReason)$",
            r"^result\.sheet\.spells\[\d+\]\.known\[[^\]]+\]$",              # the two picks, one path each
            r"^result\.sheet\.features\[\d+\]\.choice$",
        ],
        "why": "SRD Lore Bard Bonus Proficiencies and Additional Magical Secrets (Extra 1)",
    },
    # RPX2 / Extra 2: SRD packs weigh the sum of their SRD contents (they weighed 0). Every golden case holds a pack
    # (fixed grant or the filler's first package), so `cases` is "*". Rule matrix: only the carried total and, where it
    # crosses the capacity, the over-capacity flag move; nothing else reads weight.
    "RPX2": {
        "cases": ["*"],
        "paths": [
            r"^result\.derived\.carryingCapacity\.carried$",
            r"^result\.derived\.carryingCapacity\.overCapacity$",
        ],
        "why": "SRD pack weight = contents sum (Extra 2)",
    },
    # RPX3 / Extra 3: the counts of the SRD starting-equipment text are real quantities under mixed / 2014 (two
    # handaxes, five javelins, two shortswords; "20 arrows" stays ONE catalog arrow pack; the Ranger's fixed 20 arrows
    # become that one pack). Cases: the primary Barbarian, Fighter, Paladin and Ranger (the classes with a counted
    # option or the fixed arrows) in every golden family, including the kitchen sinks with those primaries. The
    # multiclass Wizard 1 / Fighter 1 (Fighter secondary: no starting equipment) must not move. Rule matrix: the
    # option's quantities and its "Nx " label on the four cards, the sheet entries' qty (Ranger granted arrow, the
    # chosen counted items when the filler's pick is the counted option), the carried total / capacity flag.
    "RPX3": {
        "cases": ["*/src-*/barbarian*", "*/src-*/fighter*", "*/src-*/paladin*", "*/src-*/ranger*",
                  "*/src-*/feats-mixed-fighter14", "*/src-*/psi-warrior11", "*/src-*/totem-bear6",
                  "*/src-*/multi-barbarian3-monk2"],
        "paths": [
            r"^result\.choices\[class:(barbarian:1:equipment-choice-1|fighter:1:equipment-choice-2|paladin:1:equipment-choice-1|ranger:1:equipment-choice-1)\]\.options\[(handaxe|javelin|shortsword)\]\.(label|quantities)",
            r"^result\.sheet\.equipment\.(granted|chosen)\[\d+\]\.qty$",
            r"^result\.derived\.carryingCapacity\.(carried|overCapacity)$",
        ],
        "why": "SRD bundle quantities from the equipment text (Extra 3)",
    },
    # W6 / F4: the 2014 SRD class-feature use-limit tail (`RESOURCE_TAIL_2014` / `RESOURCE_NOTES_2014`). Rule matrix:
    # a class case moves when its level has reached a modelled SRD feature record: Barbarian 11 / 20 (Brutal Critical 9,
    # Relentless Rage 11), Bard 3 / 11 / 20 (Song of Rest 2, Superior Inspiration 20), Cleric 3 / 11 / 20 (Channel
    # Divinity 2, Divine Intervention 10), Druid 3 / 11 / 20 (Wild Shape 2), Monk 3 / 11 / 20 (Ki 2, Deflect Missiles 3 ...),
    # every Paladin level (Lay on Hands 1, Divine Smite 2, Channel Divinity 3, Cleansing Touch 14), Ranger / Rogue /
    # Sorcerer 20 (Foe Slayer, Stroke of Luck, Sorcerous Restoration), Warlock 11 / 20 (Mystic Arcanum 11, Eldritch
    # Master 20); the multiclass Rogue 3 / Bard 2 (Song of Rest) and Barbarian 3 / Monk 2 (Ki note); the kitchen sinks
    # of those classes at or above those levels. Level 1 / 3 of the other classes, Fighter, Wizard and the remaining
    # multiclass cases must not move. Rule matrix for paths: new resources (reported once at their roots), notes added
    # to the existing resources, and the whole list when it was empty before (Ranger 20, Warlock without picks).
    "W6": {
        "cases": ["*/src-*/barbarian11", "*/src-*/barbarian20", "*/src-*/bard3", "*/src-*/bard11", "*/src-*/bard20",
                  "*/src-*/cleric3", "*/src-*/cleric11", "*/src-*/cleric20", "*/src-*/druid3", "*/src-*/druid11",
                  "*/src-*/druid20", "*/src-*/monk3", "*/src-*/monk11", "*/src-*/monk20", "*/src-*/paladin*",
                  "*/src-*/ranger20", "*/src-*/rogue20", "*/src-*/sorcerer20", "*/src-*/warlock11",
                  "*/src-*/warlock20", "*/src-*/multi-rogue3-bard2", "*/src-*/multi-barbarian3-monk2",
                  "ks/src-*/barbarian20-2014", "ks/src-*/bard10-2014", "ks/src-*/bard6-lore-*", "ks/src-*/cleric6",
                  "ks/src-*/monk14", "ks/src-*/paladin6", "ks/src-*/warlock17"],
        "paths": [
            r"^result\.derived\.classResources\[(barbarian:(brutal-critical|relentless-rage)|bard:song-of-rest|cleric:divine-intervention|monk:(deflect-missiles|slow-fall|stunning-strike|empty-body)|paladin:(divine-smite|cleansing-touch)|ranger:foe-slayer|rogue:stroke-of-luck|warlock:(mystic-arcanum|eldritch-master))\]$",
            r"^result\.derived\.classResources\[(bard:bardic-inspiration|cleric:channel-divinity|druid:wild-shape|monk:ki|paladin:(lay-on-hands|channel-divinity)|sorcerer:sorcery-points)\]\.details(\.note)?$",
            r"^result\.derived\.classResources$",
        ],
        "why": "2014 SRD class-feature use-limit tail (W6)",
    },
    # W7 / F4: the 2014 SRD subclass use-limit tail (`SUBCLASS_TAIL_2014` / `SUBCLASS_NOTES_2014`). The golden's primary
    # cases hold the first SRD subclass of the class from level 3 (Berserker, Lore, Life, Land, Champion, Open Hand,
    # Devotion, Hunter, Thief, Draconic, Fiend, Evocation). Rule matrix: a case moves when its level has reached a
    # modelled SRD subclass feature record: Barbarian 3 / 11 / 20 (Frenzy 3, Intimidating Presence 10), Bard 3 / 11 / 20
    # (Cutting Words 3), Cleric 3 / 11 / 20 (Disciple of Life 1, Preserve Life 2, Divine Strike 8), Druid 3 / 11 / 20 (Natural
    # Recovery 2, Nature's Sanctuary 14), Fighter 20 (Survivor 18), Monk 11 / 20 (Wholeness of Body 6, Tranquility 11,
    # Quivering Palm 17), Paladin 3 / 11 / 20 (Sacred Weapon, Turn the Unholy 3, Holy Nimbus 20), Sorcerer 11 / 20
    # (Elemental Affinity 6, Draconic Presence 18), Warlock 3 / 11 / 20 (Dark One's Blessing 1, Dark One's Own Luck 6, Hurl
    # Through Hell 14), Wizard 11 / 20 (Empowered Evocation 10, Overchannel 14); the multiclass Barbarian 3 / Monk 2
    # (Berserker) and Warlock 5 / Sorcerer 3 (Fiend); the Lore Bard kitchen sinks. Level 1 cases, Monk 3, Sorcerer 3, Wizard
    # 3, Fighter 3 / 11, Ranger and Rogue (Hunter and Thief have no entry) and the other multiclass cases must not move.
    # Rule matrix for paths: the new subclass resources (reported once at their roots), the notes added to the five
    # attached targets, and the whole `classResources` list when it was empty before (a Warlock 3 with no Eldritch
    # Invocation resource gets Dark One's Blessing as its first entry).
    "W7": {
        "cases": ["*/src-*/barbarian3", "*/src-*/barbarian11", "*/src-*/barbarian20", "*/src-*/multi-barbarian3-monk2",
                  "*/src-*/bard3", "*/src-*/bard11", "*/src-*/bard20", "*/src-*/cleric3", "*/src-*/cleric11",
                  "*/src-*/cleric20", "*/src-*/druid3", "*/src-*/druid11", "*/src-*/druid20", "*/src-*/fighter20",
                  "*/src-*/monk11", "*/src-*/monk20", "*/src-*/paladin3", "*/src-*/paladin11", "*/src-*/paladin20",
                  "*/src-*/sorcerer11", "*/src-*/sorcerer20", "*/src-*/warlock3", "*/src-*/warlock11",
                  "*/src-*/warlock20", "*/src-*/multi-warlock5-sorcerer3", "*/src-*/wizard11", "*/src-*/wizard20",
                  "ks/src-*/bard6-lore-*"],
        "paths": [
            r"^result\.derived\.classResources\[(barbarian:(frenzy|intimidating-presence)|cleric:(disciple-of-life|divine-strike-life-domain)|druid:(natural-recovery|nature-s-sanctuary)|fighter:survivor|monk:(wholeness-of-body|tranquility)|paladin:holy-nimbus|sorcerer:elemental-affinity|warlock:(dark-one-s-blessing|dark-one-s-own-luck|hurl-through-hell)|wizard:(empowered-evocation|overchannel))\]$",
            r"^result\.derived\.classResources\[(bard:bardic-inspiration|cleric:channel-divinity|paladin:channel-divinity|monk:ki|sorcerer:sorcery-points)\]\.details(\.note)?$",
            r"^result\.derived\.classResources$",
        ],
        "why": "2014 SRD subclass use-limit tail (W7)",
    },
    # X2: per-turn / per-combat / per-rage limits as a recharge ("turn" / "combat" / "rage" / "other"). Rule matrix: the
    # existing SRD resources whose catalog text says "Once per turn" / "Once on each of your turns" get `uses` 1 and
    # `recharge` "turn": the Rogue's Sneak Attack (every Rogue level 1 / 3 / 11 / 20, the multiclass Rogue 3 / Bard 2, the
    # 2014 feats Rogue 16 kitchen sink), the Life Domain Divine Strike (Cleric 11 / 20) and the Ranger's Foe Slayer (Ranger
    # 20). Only the `uses` and `recharge` fields of those three resource ids move; nothing else (no new resource, no note).
    # The book-subclass rows and the species rows X2 touches are in no golden case (verified by the dry-run).
    "X2": {
        "cases": ["*/src-*/rogue1", "*/src-*/rogue3", "*/src-*/rogue11", "*/src-*/rogue20", "*/src-*/multi-rogue3-bard2",
                  "*/src-*/cleric11", "*/src-*/cleric20", "*/src-*/ranger20", "ks/src-*/feats-2014-rogue16"],
        "paths": [
            r"^result\.derived\.classResources\[(rogue:sneak-attack|cleric:divine-strike-life-domain|ranger:foe-slayer)\]\.(uses|recharge)$",
        ],
        "why": "per-turn recharge of Sneak Attack, Life Domain Divine Strike and Foe Slayer (X2)",
    },
    # SK10 / Y2: option dicts carry `source` (the book code, "SRD" when the record has none). Rule: only a new key on
    # an existing option of an existing card; no label, id, order, card or draft changes. Every case holds options.
    "Y2": {
        "cases": ["*"],
        "paths": [
            r"^result[.]choices[[][^]]+[]][.]options[[][^]]+[]][.]source$",
        ],
        "why": "option source field (SK10 / Y2)",
    },
    # G1: 2014 Hunter / Totem Warrior pick effects as note-only subclass resources (`SUBCLASS_PICK_RESOURCES_2014`). Rule
    # matrix: the golden's primary Ranger (level >= 3: the first SRD subclass, Hunter) holds the filler's first-option picks,
    # Colossus Slayer (Hunter's Prey, Ranger 3), Escape the Horde (Defensive Tactics, Ranger 7), Volley (Multiattack,
    # Ranger 11) and Evasion (Superior Hunter's Defense, Ranger 15), so Ranger 3 gains one resource, Ranger 11 three and
    # Ranger 20 four; the Totem Warrior is no primary (the first SRD Barbarian subclass is Berserker), only the
    # `totem-bear6` kitchen sink picks Bear for Totem Spirit and Aspect of the Beast and gains those two. Nothing else
    # moves: the picks are already in the stored drafts, so no draft, card or other result path may change. Paths: the new
    # resources at their roots, and the whole `classResources` list for the Ranger cases whose list was empty before.
    "G1": {
        "cases": ["*/src-*/ranger3", "*/src-*/ranger11", "*/src-*/ranger20", "ks/src-*/totem-bear6"],
        "paths": [
            r"^result\.derived\.classResources\[(ranger:(hunter-s-prey-colossus-slayer|defensive-tactics-escape-the-horde|multiattack-volley|superior-hunter-s-defense-evasion)|barbarian:(totem-spirit-bear|aspect-of-the-beast-bear))\]$",
            r"^result\.derived\.classResources$",
        ],
        "why": "2014 Hunter and Totem Warrior pick effects as note-only subclass resources (G1)",
    },
    # G2: 2014 Metamagic costs (`details.metamagicCosts` + the 2024-shaped `details.metamagic` on sorcerer:sorcery-points) and
    # the two TCE options the SRD list lacks (Seeking Spell, Transmuted Spell), offered by the three SRD Metamagic cards.
    # Rule matrix: the golden's primary Sorcerer 3 / 11 / 20 (cards at level 3, 10, 17; the filler's first-option picks are
    # already stored) and the multiclass Warlock 5 / Sorcerer 3 gain the two details keys (the picked options, so a
    # level-3 Sorcerer gets two) and the two new options on each Metamagic card the class has. Sorcerer 1 has no card or
    # points, the 2024 Sorcerer is untouched, no pick, count or draft may change. Paths: the added options at their roots
    # and the two added details keys.
    "G2": {
        "cases": ["*/src-*/sorcerer3", "*/src-*/sorcerer11", "*/src-*/sorcerer20", "*/src-*/multi-warlock5-sorcerer3"],
        "paths": [
            r"^result\.choices\[class:sorcerer:(3|10|17):feature:metamagic-[123]\]\.options\[opt-(seeking|transmuted)-spell-tce\]$",
            r"^result\.derived\.classResources\[sorcerer:sorcery-points\]\.details\.(metamagicCosts|metamagic)$",
        ],
        "why": "2014 Metamagic costs on Sorcery Points and the TCE Seeking / Transmuted Spell options (G2)",
    },
}

_NEEDS_DATA = [m for m, ok in (("classes", official.has_official_classes), ("official", official.has_official),
                               ("spells", official.has_official_spells)) if not ok()]


def strip(res: dict) -> dict:
    res = copy.deepcopy(res)
    for path in STRIP:
        _strip(res, path.split("."))
    return res


def _strip(node, parts):
    head, rest = parts[0], parts[1:]
    if head == "[]":
        for x in node:
            _strip(x, rest) if rest else None
        return
    if not isinstance(node, dict) or head not in node:
        return
    if rest:
        _strip(node[head], rest)
    else:
        del node[head]


def _subclass(catalog, cls):
    for sid, s in catalog.subclasses.items():
        if s["class"]["index"] == cls and s.get("source") == "SRD":
            return sid
    return None


def _draft(catalog, classes, ruleset, sources):
    out = []
    for cid, lvl in classes:
        c = {"classId": cid, "level": lvl, "choices": {}}
        sub = _subclass(catalog, cid) if lvl >= 3 else None
        if sub:
            c["subclassId"] = sub
        out.append(c)
    return {"name": "golden", "ruleset": ruleset, "sources": list(sources),
            "abilities": {"method": "manual", "base": dict(ks._BASE)},
            "species": {"id": "human", "choices": {}}, "background": {"id": "acolyte", "choices": {}},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "classes": out}


def _label(sources):
    return "src-" + ("all" if not sources else "srd")


def case_drafts(catalog) -> dict[str, dict]:
    """name -> filled draft (unfilled here; `fill` runs in regenerate)."""
    cases = {}
    for rs in RULESETS:
        for src in SOURCES:
            for cid in CLASSES:
                for lvl in LEVELS:
                    cases[f"{rs}/{_label(src)}/{cid}{lvl}"] = (_draft(catalog, [(cid, lvl)], rs, src), {})
            for name, cl in MULTICLASS.items():
                cases[f"{rs}/{_label(src)}/multi-{name}"] = (_draft(catalog, cl, rs, src), {})
    for sid, spec in ks.KITCHEN_SINK.items():
        if spec["ruleset"] == "2024":
            continue
        # FE12: feat-holding drafts are added once, under `sources` [] (a "srd" filter would hide the feat picks)
        for src in (([],) if spec.get("feats") or spec.get("once") else SOURCES):
            d = ks.base_draft(spec)
            d["sources"] = list(src)
            cases[f"ks/{_label(src)}/{sid}"] = (d, spec["overrides"])
    return cases


def regenerate() -> None:
    catalog = load()
    out = {}
    for name, (draft, overrides) in case_drafts(catalog).items():
        spec = ks.KITCHEN_SINK.get(name.rsplit("/", 1)[-1]) if name.startswith("ks/") else None
        if spec and ks.skip_reason(spec):
            continue
        filled = ks.fill(draft, catalog, overrides, resolve)
        out[name] = {"draft": filled, "result": json.loads(json.dumps(resolve(filled, catalog)))}
    GOLDEN.parent.mkdir(exist_ok=True)
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(out, f, sort_keys=True, separators=(",", ":"))
    print(f"wrote {len(out)} cases, {GOLDEN.stat().st_size} bytes")


def append_new_cases() -> None:
    """FE12: add only the cases the golden does not hold yet (the feat-holding kitchen-sink drafts).

    Every existing entry is asserted unchanged first: its stored filled draft and (stripped) result must equal a fresh
    resolve, and it is written back byte for byte. Nothing else in the file may move."""
    catalog = load()
    old = json.load(gzip.open(GOLDEN, "rt"))
    before = {name: json.dumps(entry, sort_keys=True, separators=(",", ":")) for name, entry in old.items()}
    for name, entry in old.items():
        now = strip(json.loads(json.dumps(resolve(copy.deepcopy(entry["draft"]), catalog))))
        assert now == strip(entry["result"]), f"existing golden case changed: {name}"
    added = []
    for name, (draft, overrides) in case_drafts(catalog).items():
        if name in old:
            continue
        spec = ks.KITCHEN_SINK.get(name.rsplit("/", 1)[-1]) if name.startswith("ks/") else None
        if spec and ks.skip_reason(spec):
            continue
        filled = ks.fill(draft, catalog, overrides, resolve)
        old[name] = {"draft": filled, "result": json.loads(json.dumps(resolve(filled, catalog)))}
        added.append(name)
    for name, text in before.items():
        assert json.dumps(old[name], sort_keys=True, separators=(",", ":")) == text, name
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(old, f, sort_keys=True, separators=(",", ":"))
    print(f"kept {len(before)} existing cases unchanged, added {len(added)}: {added}")


class RebaselineError(AssertionError):
    """A rebaseline broke its allowlist (or an unmatched case moved)."""


def _keyed(node):
    """Normalize: lists of dicts that each carry a unique string `id` become dicts keyed by it."""
    if isinstance(node, dict):
        return {k: _keyed(v) for k, v in node.items()}
    if isinstance(node, list):
        if node and all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in node):
            ids = [x["id"] for x in node]
            if len(set(ids)) == len(ids):
                return {_KeyedId(x["id"]): _keyed(x) for x in node}
        return [_keyed(x) for x in node]
    return node


class _KeyedId(str):
    """A dict key that came from an `id` (rendered `[id]` in paths, not `.id`)."""


def _join(path: str, key) -> str:
    return f"{path}[{key}]" if isinstance(key, _KeyedId) else f"{path}.{key}" if path else str(key)


def diff_paths(old, new, path: str = "") -> list[str]:
    """Dotted paths where `old` and `new` differ (an added / removed subtree is reported once, at its root)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for k in sorted(set(old) | set(new), key=str):
            sub = _join(path, k)
            if k not in old or k not in new:
                out.append(sub)
            else:
                out += diff_paths(old[k], new[k], sub)
        return out
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        out = []
        for i, (a, b) in enumerate(zip(old, new)):
            out += diff_paths(a, b, f"{path}[{i}]")
        return out
    return [] if old == new else [path]


def _norm(entry: dict) -> dict:
    return _keyed({"draft": entry["draft"], "result": strip(entry["result"])})


def _write_golden(data: dict) -> None:
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(data, f, sort_keys=True, separators=(",", ":"))


def rebaseline(slice_id: str, *, dry_run: bool = False, catalog=None, rebaselines: dict | None = None,
               resolver=None, filler=None, overrides_for=None, out=print) -> dict:
    """RP6 / P0: re-resolve the golden under a slice's allowlist (see the module docstring).

    Returns {"changed": {case: [paths]}, "violations": {case: [paths]}, "warnings": [case], "counts": {regex: n}}.
    Outside `dry_run` a violation raises `RebaselineError` before anything is written."""
    table = REBASELINES if rebaselines is None else rebaselines
    if slice_id not in table:
        raise KeyError(f"unknown rebaseline slice {slice_id!r}: add it to REBASELINES first")
    spec = table[slice_id]
    patterns, allowed = spec["cases"], [re.compile(p) for p in spec["paths"]]
    resolver = resolver or resolve
    filler = filler or ks.fill
    if catalog is None:
        catalog = load()
    if overrides_for is None:
        drafts = case_drafts(catalog)
        overrides_for = lambda name: drafts[name][1] if name in drafts else {}  # noqa: E731
    old = _load_golden()
    new, changed, violations, warnings = {}, {}, {}, []
    counts = {p.pattern: 0 for p in allowed}
    for name, entry in old.items():
        matched = any(fnmatch.fnmatchcase(name, pat) for pat in patterns)
        if not matched:
            now = strip(json.loads(json.dumps(resolver(copy.deepcopy(entry["draft"]), catalog))))
            if now != strip(entry["result"]):
                bad = diff_paths(_norm(entry), _keyed({"draft": entry["draft"], "result": now}))
                violations[name] = bad or ["<unmatched case changed>"]
            new[name] = entry  # unmatched cases are written back untouched
            continue
        draft = filler(copy.deepcopy(entry["draft"]), catalog, overrides_for(name), resolver)
        fresh = {"draft": draft, "result": json.loads(json.dumps(resolver(copy.deepcopy(draft), catalog)))}
        paths = diff_paths(_norm(entry), _norm(fresh))
        new[name] = fresh if paths else entry
        if not paths:
            warnings.append(name)
            continue
        changed[name] = paths
        for pth in paths:
            hit = [p for p in allowed if p.search(pth)]
            if not hit:
                violations.setdefault(name, []).append(pth)
            for p in hit[:1]:
                counts[p.pattern] += 1
    assert set(new) == set(old), "a rebaseline never deletes or adds cases (use --append)"
    out(f"rebaseline {slice_id} ({spec.get('why', '')}){' [dry run]' if dry_run else ''}")
    out(f"  matching cases changed: {len(changed)} of {len(old)}")
    for p, n in counts.items():
        out(f"  {n:5d} changed path(s) match {p}")
    for name in warnings:
        out(f"  WARNING: {name} matches `cases` but did not change (pattern too wide?)")
    for name, paths in changed.items():
        if dry_run:
            out(f"  {name}")
            for pth in paths:
                out(f"      {'DISALLOWED ' if pth in violations.get(name, []) else ''}{pth}")
    for name, paths in violations.items():
        out(f"  VIOLATION {name}: {len(paths)} path(s) outside the allowlist, e.g. {paths[:3]}")
    report = {"changed": changed, "violations": violations, "warnings": warnings, "counts": counts}
    if dry_run:
        return report
    if violations:
        raise RebaselineError(f"rebaseline {slice_id}: paths outside the allowlist or unmatched case changed: "
                              f"{ {n: p[:3] for n, p in violations.items()} }")
    if changed:
        _write_golden(new)
        out(f"wrote {len(new)} cases, {GOLDEN.stat().st_size} bytes")
    else:
        out("nothing changed, golden file not rewritten")
    return report


def _load_golden() -> dict:
    return json.load(gzip.open(GOLDEN, "rt")) if GOLDEN.exists() else {}


_GOLDEN = _load_golden() if not _NEEDS_DATA else {}
pytestmark = pytest.mark.skipif(bool(_NEEDS_DATA), reason=f"5etools data missing: {', '.join(_NEEDS_DATA)}")


@pytest.fixture(scope="module")
def catalog():
    return load()


def test_golden_file_present_and_covers_every_case():
    assert _GOLDEN, "golden file missing: regenerate (see module docstring)"
    names = set(case_drafts(load()))
    kitchen = {n for n in names if n.startswith("ks/") and ks.skip_reason(ks.KITCHEN_SINK[n.rsplit("/", 1)[-1]])}
    assert set(_GOLDEN) == names - kitchen
    assert all(json.loads(json.dumps(v["draft"]))["ruleset"] in RULESETS for v in _GOLDEN.values())


# --- RP6 / P0: rebaseline mode, tested on a synthetic two-case golden (the real file is never touched) ---

def _synthetic(tmp_path, monkeypatch):
    """Two cases in tmp_path; `GOLDEN` is overridden at module level. Fake resolver: result = hp + choice cards."""
    path = tmp_path / "synthetic.json.gz"
    monkeypatch.setitem(globals(), "GOLDEN", path)
    fighter, wizard = ({"hp": 10, "cards": ["a", "b"]}, {"hp": 6, "cards": ["a"]})
    entries = {}
    for name, d in (("mixed/x/fighter", fighter), ("mixed/x/wizard", wizard)):
        entries[name] = {"draft": d, "result": _fake(d, {})}
    _write_golden(entries)
    return path


def _fake(draft, flags):
    cards = [{"id": c, "status": "done", "options": [{"id": "o1"}, {"id": "o2"}]} for c in draft["cards"]]
    if flags.get("insert"):
        cards.insert(0, {"id": "new", "status": "pending", "options": []})
    bump = flags.get("hp", 0) if not flags.get("fighter_only") or "b" in draft["cards"] else 0
    return {"hp": draft["hp"] + bump, "choices": cards, "derived": {"featResources": [1]}}


def _run(slice_id, flags, table, **kw):
    log = []
    rep = rebaseline(slice_id, catalog=object(), rebaselines=table, overrides_for=lambda n: {},
                     resolver=lambda d, c: _fake(d, flags), filler=lambda d, *a: d, out=log.append, **kw)
    return rep, "\n".join(log)


def _table(cases, paths):
    return {"T": {"cases": cases, "paths": paths, "why": "synthetic"}}


def test_rebaseline_expected_path_passes_and_writes(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    before = json.load(gzip.open(path, "rt"))
    rep, log = _run("T", {"hp": 1, "fighter_only": True}, _table(["*/fighter"], [r"^result[.]hp$"]))
    after = json.load(gzip.open(path, "rt"))
    assert rep["changed"] == {"mixed/x/fighter": ["result.hp"]} and not rep["violations"]
    assert after["mixed/x/fighter"]["result"]["hp"] == 11 and after["mixed/x/wizard"] == before["mixed/x/wizard"]
    assert "1 changed path(s) match ^result[.]hp$" in log


def test_rebaseline_unexpected_path_fails_and_leaves_file(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    with pytest.raises(RebaselineError):
        _run("T", {"hp": 1, "insert": True, "fighter_only": True}, _table(["*/fighter"], [r"^result[.]hp$"]))
    assert path.read_bytes() == raw


def test_rebaseline_unmatched_case_changing_fails(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    with pytest.raises(RebaselineError, match="wizard"):
        _run("T", {"hp": 1}, _table(["*/fighter"], [r"^result[.]hp$"]))  # wizard also moves but is not listed
    assert path.read_bytes() == raw


def test_rebaseline_dry_run_writes_nothing_and_prints_diff(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    rep, log = _run("T", {"hp": 1, "fighter_only": True}, _table(["*/fighter"], [r"^nothing$"]), dry_run=True)  # no raise on violations
    assert path.read_bytes() == raw
    assert "DISALLOWED result.hp" in log and "[dry run]" in log and "mixed/x/fighter" in rep["violations"]


def test_rebaseline_warns_when_a_matching_case_does_not_change(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    rep, log = _run("T", {}, _table(["mixed/*"], [r"^result"]))
    assert sorted(rep["warnings"]) == ["mixed/x/fighter", "mixed/x/wizard"] and "WARNING" in log
    assert "not rewritten" in log


def test_rebaseline_inserted_card_lands_at_a_keyed_path(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    rep, _ = _run("T", {"insert": True}, _table(["mixed/*"], [r"^result[.]choices\[new\]$"]), dry_run=True)
    # one path per case, not a shifted index for every following card
    assert rep["changed"] == {"mixed/x/fighter": ["result.choices[new]"], "mixed/x/wizard": ["result.choices[new]"]}
    assert not rep["violations"]


def test_rebaseline_unknown_slice_raises(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    with pytest.raises(KeyError):
        _run("nope", {}, _table(["*"], []))


def test_rebaselines_constant_is_append_only_and_strip_unchanged():
    """Append-only record: a later slice adds a key, never edits or removes one (extend this tuple then)."""
    assert tuple(REBASELINES) == ("RP7", "RPF", "RP15", "RP16", "RPX1", "RPX2", "RPX3", "W6", "W7", "X2", "Y2", "G1", "G2") and STRIP == ("derived.featResources", "derived.speciesResources")
    rp7 = REBASELINES["RP7"]
    assert rp7["cases"] == ["*/src-*/monk[0-9]*", "ks/src-*/monk14"] and len(rp7["paths"]) == 3


@pytest.mark.filterwarnings("ignore:Possible nested set:FutureWarning")
def test_every_rebaseline_allowlist_regex_compiles():
    """The Y2 regexes use `[[]` (a literal bracket), which Python flags as a possible nested set: the entry is frozen
    (append-only), so the warning is filtered here, where the allowlists are compiled."""
    for slice_id, spec in REBASELINES.items():
        assert spec["cases"] and spec["paths"] and spec["why"], slice_id
        for rx in spec["paths"]:
            re.compile(rx)


def test_rp7_cases_are_the_primary_monk_cases_only():
    """The multiclass Barbarian 3 / Monk 2 (Monk secondary) is not matched, so it must stay byte-identical."""
    names = sorted(_GOLDEN)
    hit = [n for n in names if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP7"]["cases"])]
    assert len(hit) == 18 and not [n for n in hit if "multi-" in n]
    for n in hit:  # every matched case carries the new card with the filler's pick (the rebaselined content)
        assert any(c["id"] == "class:monk:1:prof-choice-1" and c["status"] == "resolved" for c in _GOLDEN[n]["result"]["choices"])
    for n in names:
        if "multi-barbarian3-monk2" in n:
            assert not any(c["id"] == "class:monk:1:prof-choice-1" for c in _GOLDEN[n]["result"]["choices"])


def test_rpf_cases_are_the_multiclass_rogue_bard_only_and_hold_no_duplicate_skill_pick():
    hit = [n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RPF"]["cases"])]
    assert len(hit) == 4 and all("multi-rogue3-bard2" in n for n in hit)
    for n in hit:
        res = _GOLDEN[n]["result"]
        picks = [s for c in res["choices"] if c["id"].endswith(("prof-choice-0", "prof-choice-1")) and c["source"]["kind"] == "class"
                 for s in c["selected"] if s.startswith("skill-")]
        assert len(picks) == len(set(picks)), n


def test_rp15_cases_are_the_wizard_20_cases_and_hold_the_srd_pick_cards():
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP15"]["cases"]))
    assert len(hit) == 4 and all(n.endswith("/wizard20") for n in hit)
    for n in hit:  # the golden books hold level 1 / 2 spells only: Mastery is filled, Signature has nothing to offer
        by_id = {c["id"]: c for c in _GOLDEN[n]["result"]["choices"]}
        assert by_id["class:wizard:18:spell-mastery-1"]["status"] == "resolved", n
        assert by_id["class:wizard:20:signature-spells"]["status"] == "unavailable", n
    for n in ("ks/src-all/wizard20-2014", "ks/src-srd/wizard20-2014"):  # appended kitchen sink with real picks
        res = _GOLDEN[n]["result"]
        entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "wizard")
        assert [s["id"] for s in entry["signatureSpells"]] == ["fireball", "counterspell"]
        assert [s["id"] for s in entry["spellMastery"]] == ["shield", "web"]
        assert [s["id"] for s in entry["alwaysPrepared"]] == ["fireball", "counterspell"]
        assert any(r["id"] == "wizard:signature-spells" and r["uses"] == 2 for r in res["derived"]["classResources"])


def test_rp16_cases_are_the_bard_11_and_20_cases_and_hold_the_magical_secrets_options():
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP16"]["cases"]))
    assert len(hit) == 8 and all(n.endswith(("/bard11", "/bard20")) for n in hit)
    for n in hit:  # the stored picks are the old list's first spells: none from another class, all kept
        card = next(c for c in _GOLDEN[n]["result"]["choices"] if c["id"] == "class:bard:spells-known")
        labelled = [o for o in card["options"] if o["label"].endswith("(Magical Secrets)")]
        assert labelled and any(o["id"] == "fire-bolt" for o in labelled) and "Magical Secrets" in card["description"], n
        assert not set(card["selected"]) & {o["id"] for o in labelled}, n
        assert len(card["selected"]) == card["count"], n
    for n in ("ks/src-all/bard10-2014", "ks/src-srd/bard10-2014"):  # appended kitchen sink with real picks
        res = _GOLDEN[n]["result"]
        known = next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]
        assert {"fireball", "sacred-flame"} <= {s["id"] for s in known}, n
        assert not [p for p in res["pruned"] if p["choiceId"] == "class:bard:spells-known"], n


def test_rpx1_cases_are_the_lore_bard_3_11_20_cases_and_hold_the_lore_picks():
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RPX1"]["cases"]))
    assert len(hit) == 12 and all(n.endswith(("/bard3", "/bard11", "/bard20")) for n in hit)
    for n in hit:
        res = _GOLDEN[n]["result"]
        bonus = next(c for c in res["choices"] if c["id"] == "class:bard:3:feature:bonus-proficiencies")
        assert bonus["count"] == 3 and len(bonus["selected"]) == 3 and bonus["status"] == "resolved", n
        assert set(bonus["selected"]) <= set(res["sheet"]["proficiencies"]["skills"]), n
        secrets = next((c for c in res["choices"] if c["id"] == "class:bard:6:feature:additional-magical-secrets"), None)
        if n.endswith("/bard3"):
            assert secrets is None, n
            continue
        known = next(c for c in res["choices"] if c["id"] == "class:bard:spells-known")
        assert secrets["count"] == 2 and len(secrets["selected"]) == 2 and not set(secrets["selected"]) & set(known["selected"]), n
        sheet_known = {s["id"] for s in next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]}
        assert set(secrets["selected"]) <= sheet_known and len(sheet_known) == known["count"] + 2, n
        assert not [p for p in res["pruned"] if p["choiceId"] in (secrets["id"], bonus["id"])], n
    for n in ("ks/src-all/bard6-lore-2014", "ks/src-srd/bard6-lore-2014"):  # appended kitchen sink with real picks
        res = _GOLDEN[n]["result"]
        skills = set(res["sheet"]["proficiencies"]["skills"])
        assert {"skill-arcana", "skill-history", "skill-nature"} <= skills, n
        known = next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]
        assert {"fireball", "sacred-flame"} <= {s["id"] for s in known}, n
        assert not res["pruned"] or not [p for p in res["pruned"] if "bonus" in p["choiceId"] or "secrets" in p["choiceId"]], n


_SRD_PACK_LB = {"burglars-pack": 47.5, "diplomats-pack": 36, "dungeoneers-pack": 61.5, "entertainers-pack": 38,
                "explorers-pack": 59, "priests-pack": 18, "scholars-pack": 10}


def test_rpx2_every_case_counts_its_srd_pack_weight():
    """RPX2: every golden case holds an SRD pack and its carried total includes the pack's contents sum."""
    assert len(REBASELINES["RPX2"]["cases"]) == 1 and REBASELINES["RPX2"]["cases"] == ["*"]
    for n, entry in _GOLDEN.items():
        eq = entry["result"]["sheet"]["equipment"]
        packs = sum(_SRD_PACK_LB.get(e["itemId"], 0) * e.get("qty", 1) for k in ("granted", "chosen", "added") for e in eq[k])
        assert packs > 0, n
        assert entry["result"]["derived"]["carryingCapacity"]["carried"] >= packs, n


def test_rpx3_cases_hold_the_text_counts_and_no_ammunition_stack():
    """RPX3: 77 cases (primary Barbarian / Fighter / Paladin / Ranger families); the counted options carry their
    quantities, a picked counted option is in the inventory with that qty, the Ranger's fixed arrows are ONE pack,
    and no case anywhere holds an ammunition stack of 20 (a 400-arrow inventory)."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RPX3"]["cases"]))
    assert len(hit) == 77 and not [n for n in hit if "wizard1-fighter1" in n]
    expect = {"class:barbarian:1:equipment-choice-1": ("handaxe", 2), "class:fighter:1:equipment-choice-2": ("handaxe", 2),
              "class:paladin:1:equipment-choice-1": ("javelin", 5), "class:ranger:1:equipment-choice-1": ("shortsword", 2)}
    for n in hit:
        res = _GOLDEN[n]["result"]
        for c in res["choices"]:
            if c["id"] in expect:
                item, qty = expect[c["id"]]
                opt = next(o for o in c["options"] if o["id"] == item or o["id"].endswith("+" + item) or item in o["id"].split("+"))
                assert opt["quantities"] == {item: qty}, (n, c["id"])
                if c["selected"] == [opt["id"]]:
                    chosen = {e["itemId"]: e["qty"] for e in res["sheet"]["equipment"]["chosen"]}
                    assert chosen[item] == qty, n
        if "/ranger" in n:
            assert {e["itemId"]: e["qty"] for e in res["sheet"]["equipment"]["granted"]}["arrow"] == 1, n
    for n, entry in _GOLDEN.items():
        for k in ("granted", "chosen", "added"):
            for e in entry["result"]["sheet"]["equipment"][k]:
                if e["itemId"] in ("arrow", "crossbow-bolt", "sling-bullet", "blowgun-needle"):
                    assert e["qty"] == 1, (n, e)


def test_w6_cases_hold_the_2014_class_feature_tail():
    """W6: every matched case carries the SRD tail entries of its class at its level; Fighter, Wizard, the low-level
    cases and the other multiclass cases do not hold any W6 resource."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["W6"]["cases"]))
    assert len(hit) == 116
    w6_ids = {"barbarian:brutal-critical", "barbarian:relentless-rage", "bard:song-of-rest", "cleric:divine-intervention",
              "monk:deflect-missiles", "monk:slow-fall", "monk:stunning-strike", "monk:empty-body", "paladin:divine-smite",
              "paladin:cleansing-touch", "ranger:foe-slayer", "rogue:stroke-of-luck", "warlock:mystic-arcanum",
              "warlock:eldritch-master"}
    for n, entry in _GOLDEN.items():
        ids = {r["id"] for r in entry["result"]["derived"]["classResources"]}
        if n not in hit and "/whispers-bard14" not in n and "/watchers-paladin20" not in n and "/celestial-warlock14" not in n and "/totem-elk14" not in n and "/cleric6-paladin3-2014" not in n:  # W8a / W8c / W8d / G1 / G3 appended sinks (G3: a Cleric 6 holds Disciple of Life, a Paladin 3 Divine Smite): a Bard 14 holds Song of Rest, a Paladin 20 Divine Smite and Cleansing Touch, a Warlock 14 Mystic Arcanum, a Barbarian 14 Brutal Critical and Relentless Rage
            assert not ids & w6_ids, n
    for n in hit:
        ids = {r["id"] for r in _GOLDEN[n]["result"]["derived"]["classResources"]}
        if "rogue20" in n:
            assert "rogue:stroke-of-luck" in ids, n
        if "warlock20" in n and "src-srd" in n:
            assert {"warlock:eldritch-master", "warlock:mystic-arcanum"} <= ids, n


def test_w7_cases_hold_the_2014_subclass_tail():
    """W7: 112 matched cases carry the SRD subclass entries of their class at their level; Hunter, Thief, level 1 and the
    other cases hold no W7 subclass resource (their subclass entries stay the R6 builders')."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["W7"]["cases"]))
    assert len(hit) == 112
    w7_ids = {"barbarian:frenzy", "barbarian:intimidating-presence", "cleric:disciple-of-life",
              "cleric:divine-strike-life-domain", "druid:natural-recovery", "druid:nature-s-sanctuary", "fighter:survivor",
              "monk:wholeness-of-body", "monk:tranquility", "paladin:holy-nimbus", "sorcerer:elemental-affinity",
              "warlock:dark-one-s-blessing", "warlock:dark-one-s-own-luck", "warlock:hurl-through-hell",
              "wizard:empowered-evocation", "wizard:overchannel"}
    for n, entry in _GOLDEN.items():
        ids = {r["id"] for r in entry["result"]["derived"]["classResources"]}
        if n not in hit and "/cleric6-paladin3-2014" not in n:  # (the W8a sink holds no SRD subclass entry either; the G3 sink holds the Life and Devotion ones)
            assert not ids & w7_ids, n
        elif "warlock20" in n and "/multi" not in n:
            assert {"warlock:dark-one-s-blessing", "warlock:dark-one-s-own-luck", "warlock:hurl-through-hell"} <= ids, n


def test_w8a_no_rebaseline_and_the_whispers_sink_guards_the_book_tail():
    """W8a: no golden case moved (the golden's primary cases hold the SRD subclass; psi-warrior11 and totem-bear6 hold
    unmodelled book subclasses), so there is no REBASELINES entry; the Whispers Bard 14 kitchen sink was appended
    instead and holds the book subclass entries."""
    assert "W8a" not in REBASELINES
    for n in ("ks/src-all/whispers-bard14-2014", "ks/src-srd/whispers-bard14-2014"):
        ids = [r["id"] for r in _GOLDEN[n]["result"]["derived"]["classResources"]]
        assert {"bard:words-of-terror", "bard:mantle-of-whispers", "bard:shadow-lore"} <= set(ids), n
        bi = next(r for r in _GOLDEN[n]["result"]["derived"]["classResources"] if r["id"] == "bard:bardic-inspiration")
        assert "Psychic Blades" in bi["details"]["note"], n


def test_w8b_no_rebaseline_and_the_stars_sink_guards_the_book_tail():
    """W8b: no golden case moved (Life, Land and Champion are the primary SRD subclasses; the book-subclass sinks hold
    unmodelled features), so there is no REBASELINES entry; the Circle of the Stars Druid 10 sink was appended instead."""
    assert "W8b" not in REBASELINES
    for n in ("ks/src-all/stars-druid10-mixed", "ks/src-srd/stars-druid10-mixed"):
        res = {r["id"]: r for r in _GOLDEN[n]["result"]["derived"]["classResources"]}
        assert {"druid:star-map", "druid:cosmic-omen"} <= set(res), n
        assert "Starry Form" in res["druid:wild-shape"]["details"]["note"], n
        assert res["druid:star-map"]["uses"] == 4 and res["druid:star-map"]["recharge"] == "long", n


def test_w8c_no_rebaseline_and_the_watchers_sink_guards_the_book_tail():
    """W8c: no golden case moved (Open Hand, Devotion, Hunter and Thief are the primary SRD subclasses; the book-subclass
    sinks hold unmodelled features), so there is no REBASELINES entry; the Oath of the Watchers Paladin 20 sink was
    appended instead."""
    assert "W8c" not in REBASELINES
    for n in ("ks/src-all/watchers-paladin20-2014", "ks/src-srd/watchers-paladin20-2014"):
        res = {r["id"]: r for r in _GOLDEN[n]["result"]["derived"]["classResources"]}
        assert {"paladin:aura-of-the-sentinel", "paladin:vigilant-rebuke", "paladin:mortal-bulwark"} <= set(res), n
        assert "Watcher's Will" in res["paladin:channel-divinity"]["details"]["note"], n
        assert "within 30 feet of you gain a bonus to initiative" in res["paladin:aura-of-the-sentinel"]["details"]["note"], n


def test_w8d_no_rebaseline_and_the_celestial_sink_guards_the_book_tail():
    """W8d: no golden case moved (Draconic, Fiend and Evocation are the primary SRD subclasses; the book-subclass sinks
    hold no modelled feature), so there is no REBASELINES entry; the Celestial Warlock 14 sink was appended instead."""
    assert "W8d" not in REBASELINES
    for n in ("ks/src-all/celestial-warlock14-mixed", "ks/src-srd/celestial-warlock14-mixed"):
        res = {r["id"]: r for r in _GOLDEN[n]["result"]["derived"]["classResources"]}
        assert {"warlock:healing-light", "warlock:radiant-soul", "warlock:celestial-resilience", "warlock:searing-vengeance"} <= set(res), n
        assert res["warlock:healing-light"]["uses"] == 15 and res["warlock:healing-light"]["die"] == "d6", n
        assert res["warlock:searing-vengeance"]["recharge"] == "long", n


def test_keyed_normalization_and_diff_paths():
    a = _keyed({"choices": [{"id": "x", "v": 1}, {"id": "y", "v": 2}], "plain": [1, 2]})
    b = _keyed({"choices": [{"id": "n", "v": 0}, {"id": "x", "v": 1}, {"id": "y", "v": 3}], "plain": [1, 2]})
    assert diff_paths(a, b) == ["choices[n]", "choices[y].v"]
    dup = _keyed({"c": [{"id": "x"}, {"id": "x"}]})  # non-unique ids stay a list
    assert isinstance(dup["c"], list)


@pytest.mark.parametrize("name", sorted(_GOLDEN))
def test_mixed_and_2014_resolve_is_unchanged(catalog, name):
    entry = _GOLDEN[name]
    now = strip(json.loads(json.dumps(resolve(copy.deepcopy(entry["draft"]), catalog))))
    assert now == strip(entry["result"])


def test_x2_cases_hold_the_turn_recharge():
    """X2: the 33 rebaselined cases carry Sneak Attack / Life Domain Divine Strike / Foe Slayer as 1 use per turn; every
    other case holds no resource with a non-rest recharge (the species, book-subclass and 2024 rows are in no golden case)."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["X2"]["cases"]))
    assert len(hit) == 33
    x2_ids = {"rogue:sneak-attack", "cleric:divine-strike-life-domain", "ranger:foe-slayer"}
    for n, entry in _GOLDEN.items():
        resources = entry["result"]["derived"]["classResources"]
        turn = {r["id"] for r in resources if r["recharge"] in ("turn", "combat", "rage", "other")
                and not r["name"].startswith(G1_PICK_LABELS)}  # G1's pick resources have their own pin test
        assert (turn <= x2_ids) and (n in hit or not turn), n
        if n in hit:
            assert turn and all(r["uses"] == 1 and r["recharge"] == "turn" for r in resources if r["id"] in turn), n


G1_PICK_LABELS = ("Hunter's Prey: ", "Defensive Tactics: ", "Multiattack: ", "Superior Hunter's Defense: ",
                  "Totem Spirit: ", "Aspect of the Beast: ", "Totemic Attunement: ")


def test_g1_cases_hold_the_2014_pick_resources_and_nothing_else_moved():
    """G1: the 14 rebaselined cases are the primary Ranger 3 / 11 / 20 (Hunter, first-option picks: Colossus Slayer at 3,
    + Escape the Horde and Volley at 11, + Evasion at 20) and the `totem-bear6` sink (Totem Spirit and Aspect of the
    Beast, Bear); the two cases appended with them hold the Elk Totemic Attunement DC and the other Hunter options. Every
    other case holds no G1 pick resource."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["G1"]["cases"]))
    assert len(hit) == 14
    expected = {"ranger3": ["Hunter's Prey: Colossus Slayer"],
                "ranger11": ["Hunter's Prey: Colossus Slayer", "Defensive Tactics: Escape the Horde", "Multiattack: Volley"],
                "ranger20": ["Hunter's Prey: Colossus Slayer", "Defensive Tactics: Escape the Horde", "Multiattack: Volley",
                             "Superior Hunter's Defense: Evasion"],
                "totem-bear6": ["Totem Spirit: Bear", "Aspect of the Beast: Bear"]}
    appended = {"totem-elk14": ["Totem Spirit: Elk", "Aspect of the Beast: Tiger", "Totemic Attunement: Elk"],
                "hunter15-2014": ["Hunter's Prey: Horde Breaker", "Defensive Tactics: Multiattack Defense",
                                  "Multiattack: Whirlwind Attack", "Superior Hunter's Defense: Uncanny Dodge"]}
    for n, entry in _GOLDEN.items():
        names = [r["name"] for r in entry["result"]["derived"]["classResources"] if r["name"].startswith(G1_PICK_LABELS)]
        key = n.rsplit("/", 1)[-1]
        assert names == (expected.get(key) or appended.get(key) or []), n
        assert (n in hit) == (key in expected), n
    elk = {r["id"]: r for r in _GOLDEN["ks/src-all/totem-elk14"]["result"]["derived"]["classResources"]}
    assert elk["barbarian:totemic-attunement-elk"]["dc"] == 8 + 5 + 3 + 1 and "DC 17" in elk["barbarian:totemic-attunement-elk"]["details"]["note"]


def test_g2_cases_hold_the_metamagic_costs_and_nothing_else_moved():
    """G2: the 16 rebaselined cases are the primary Sorcerer 3 / 11 / 20 and the multiclass Warlock 5 / Sorcerer 3 (x
    mixed / 2014 x src-all / src-srd); each holds the costs of the stored first-option picks of the level-3 card
    (Careful and Distant Spell, 1 point each; the stored Sorcerer 11 / 20 drafts have no pick on the later cards) and
    the two TCE options on every Metamagic card. The case appended with them holds Twinned ("spell level"), Seeking, Heightened and Transmuted."""
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["G2"]["cases"]))
    assert len(hit) == 16
    first = ["metamagic-careful-spell", "metamagic-distant-spell"]
    expected = {"sorcerer3": first, "multi-warlock5-sorcerer3": first, "sorcerer11": first, "sorcerer20": first}
    for n, entry in _GOLDEN.items():
        key = n.rsplit("/", 1)[-1]
        sp = [r for r in entry["result"]["derived"]["classResources"] if r["id"] == "sorcerer:sorcery-points"]
        costs = sp[0]["details"].get("metamagicCosts") if sp else None
        if n.startswith("ks/") and key == "sorcerer17-metamagic-2014":
            assert costs == {"metamagic-twinned-spell": "spell level", "opt-seeking-spell-tce": 2,
                             "metamagic-heightened-spell": 3, "opt-transmuted-spell-tce": 1}, n
            assert [m["name"] for m in sp[0]["details"]["metamagic"]] == ["Twinned Spell", "Seeking Spell", "Heightened Spell",
                                                                          "Transmuted Spell"]
            continue
        if n.startswith("2024/") or n.startswith("ks/"):
            assert not costs, n
            continue
        assert (n in hit) == (key in expected), n
        assert costs == ({o: 1 for o in expected[key]} if key in expected else None), n
        if key in expected:
            for card in entry["result"]["choices"]:
                if card["id"].startswith("class:sorcerer:") and ":feature:metamagic-" in card["id"]:
                    ids = [o["id"] for o in card["options"]]
                    assert len(ids) == 10 and "opt-seeking-spell-tce" in ids and "opt-transmuted-spell-tce" in ids, n


def test_g3_no_rebaseline_and_the_merged_channel_divinity_sink_holds_both_notes():
    """G3: no stored case moved (no golden case holds two Channel Divinity classes and the Divine Intervention lockouts
    were already in the notes), so there is no REBASELINES entry; the Cleric 6 / Paladin 3 sink was appended instead.
    Every other case holds at most one Channel Divinity entry without a class label."""
    assert "G3" not in REBASELINES
    for n, entry in _GOLDEN.items():
        cds = [r for r in entry["result"]["derived"]["classResources"] if r["name"] == "Channel Divinity"]
        merged = "classes" in (cds[0]["details"] if cds else {}) if len(cds) == 1 else False
        notes = [(r.get("details") or {}).get("note") or "" for r in cds]
        if n.rsplit("/", 1)[-1] == "cleric6-paladin3-2014":
            assert len(cds) == 1 and cds[0]["details"]["classes"] == ["cleric", "paladin"], n
            note = cds[0]["details"]["note"]
            assert note.startswith("Cleric: Turn Undead") and " | Paladin: " in note and "Sacred Weapon" in note, n
        else:
            assert not merged and not any(x.startswith(("Cleric:", "Paladin:")) for x in notes), n


def test_y2_golden_options_carry_a_source_and_nothing_else_moved():
    """Y2: the rebaseline touched only `options[*].source` (the allowlist); 218 of the first 254 cases hold a book option (the
    G2 and G3 cases appended later hold one too: 221 of 257), the other 36 (level 1 / 3 cases without feat, spell or feature options) are byte-identical. Every stored source is a
    non-empty code, and no option outside the book kinds (skills, languages, equipment items) has one."""
    assert REBASELINES["Y2"]["cases"] == ["*"] and len(REBASELINES["Y2"]["paths"]) == 1
    with_source = 0
    for name, entry in _GOLDEN.items():
        has = False
        for card in entry["result"]["choices"]:
            for o in card["options"]:
                if "source" in o:
                    has = True
                    assert isinstance(o["source"], str) and o["source"], (name, card["id"], o["id"])
                    assert not o["id"].startswith("skill-") and card["source"]["kind"] != "equipment", (name, card["id"], o["id"])
        with_source += has
    assert with_source == 221  # 218 + the G2 sorcerer17-metamagic-2014 case + the two G3 cleric6-paladin3-2014 cases


if __name__ == "__main__":
    if "--rebaseline" in sys.argv:
        i = sys.argv.index("--rebaseline")
        if i + 1 >= len(sys.argv):
            sys.exit("--rebaseline needs a slice id (a key of REBASELINES)")
        try:
            rebaseline(sys.argv[i + 1], dry_run="--dry-run" in sys.argv)
        except (KeyError, RebaselineError) as e:
            sys.exit(str(e))
    elif "--append" in sys.argv:
        append_new_cases()
    elif "--regenerate" in sys.argv:
        regenerate()
    else:
        sys.exit("pass --append (add new cases only), --rebaseline <SLICE> [--dry-run] or --regenerate (rewrite everything) to change the golden file")
