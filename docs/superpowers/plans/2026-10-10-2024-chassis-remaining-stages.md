# Plan: the remaining 2024 class chassis (C6b, C6c, C6d, C7, C9, optional C8/R9) and final consolidation (F3)

(Opus planner, 2026-10-10. Suggested file name: `docs/superpowers/plans/2026-10-10-2024-chassis-remaining-stages.md`. I only read code and data and changed nothing in the repo. Scratch scripts ran with `.venv/bin/python` against the real catalog. Numbers marked "verified" come from those runs. **VERIFY** means the executor re-checks by script before writing the test. If a script and this plan disagree, the script wins and the deviation goes into the slice's ARCHITECTURE section.)

## 0. Conventions (everything from the 2026-10-09 plan still applies, plus the points below)

- **TDD.** Write the tests first (a rule matrix in the docstring that quotes the governing XPHB text), then the smallest implementation that passes.
- **Gate after every slice:**
  - `cd server && ../.venv/bin/python -m pytest -q`: baseline **2128 passed**.
  - `cd <root> && .venv/bin/python -m pytest -q`: **405 passed, 8 skipped**.
  - `cd frontend && npm run build` whenever `frontend/` is touched.
  - Record the new totals in the slice's ARCHITECTURE section.
- **Ruleset rule.** Behaviour changes only under `ruleset == "2024"`. `mixed` and `2014` must not change by a single byte.
  - Slice F0 adds a golden file that enforces this for every later slice.
  - Exception: purely additive keys on catalog records (e.g. new spell fields), which never reach `resolve()` output under mixed/2014.
- **Degrade.** With an SRD-only catalog (no `class_2024_*` data, no XPHB optional features), every new card is absent, the SRD behaviour stays, and nothing crashes. Each slice has one test using the existing patched/empty-catalog pattern.
- **Speed.** `resolve()` must stay under 50 ms. Time Fighter 20, Monk 20, Warlock 17 / Paladin 3 and Wizard 20 (mixed and 2024), plus each new 2024 reference character named in the slice.
- **Commits.** One commit per slice, e.g. `feat(2024): ... (C6b-1)`. Use the trailer from the executing session. Stage with `git add <explicit paths>` only; never stage `Resurses/`.
- **ARCHITECTURE doc.** Each slice appends a dated section to `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`.
- **Frontend.** Plain markup, no CSS. Check at 375px that `document.documentElement.scrollWidth === 375`.
- **Hand-written types.** Every new sheet/derived key goes into `frontend/src/types.ts` (optional) in the same commit. Every top-level key also goes into `export_fields.py` or the export-key test fails.
- **One cid convention for every XPHB-backed card.** The cid is `class:<cls>:<lvl>:<kind>:<xphb feature id>`, where `<kind>` is one of `feature | expertise-choice | languages | invocations`.
  - Slice C6b-1 extends `sheet_features._CLASS_CHOICE_ID` (add `languages`) and adds a generic "attach by XPHB feature id" rule.
  - After that, every later card attaches to its C5 XPHB row with no further `sheet_features` work.
- **Stored picks across rulesets.** An SRD cid and its 2024 replacement are different strings. Switching ruleset moves the stored picks into `pruned` through the generic stale-cid pass, the same precedent as C3. They are never lost silently.

## Decisions (user answers, 2026-10-10)

User approved building C6b, C6c, C7, C9 ("Да") and asked for maximum RAW fidelity. E1-E10 and E14 = the recommended defaults below (they follow the book/XPHB text). C8 (E10) and R9 (E14) are INCLUDED. E11, E12, E13 = out of scope (listed as follow-ups in F3). Executors do not re-ask these.

## 1. Decision points for the user

These cannot be settled from the book text or the data. Ask them all in one message before starting. Each has a recommended default, which the executor uses unless the user overrides it.

| # | Question | Recommended default |
|---|---|---|
| E1 | Expertise duplicates. Deft Explorer and Ranger 9 say "with which you lack Expertise". Bard 2/9, Rogue 1/6 and Scholar do not. Should a skill that already has Expertise be blocked on every 2024 expertise card? | Follow the text exactly. Only Deft Explorer and Ranger 9 disable "already has Expertise". On the other cards a duplicate is allowed (it is simply wasted). |
| E2 | Language pool for Deft Explorer and Thieves' Cant ("from the language tables in chapter 2"). | Standard table plus Rare table (19 entries, incl. Druidic, Thieves' Cant, Common Sign Language). Languages the character already knows are shown disabled ("already known"). |
| E3 | Potent Spellcasting, Divine Strike and Primal Strike. The engine has no cantrip damage rows. | A `derived.classResources` entry with `dice` / `bonus` / `details.note`. Divine Strike and Primal Strike also add a note to weapon attack rows (the same pattern as the R5 Rage / Sneak Attack notes). |
| E4 | Repeatable invocations (Agonizing Blast, Eldritch Spear, Repelling Blast, Lessons of the First Ones). | Extra option ids `<id>~2`, `<id>~3`, labelled "Agonizing Blast (2)". Instance k is enabled only when instance k-1 is selected. Each instance has its own target pick, and targets must differ between instances. |
| E5 | Pact of the Blade. | A dependent build-time "pact weapon" pick (melee weapons in the inventory). That weapon's attack row is proficient and uses CHA when CHA is better than its normal ability. Otherwise note only. |
| E6 | Pact of the Chain. The data says "ritual"; the text says "can cast it ... without expending a spell slot". | The text wins: Find Familiar is an innate entry, at will, with the note "Magic action". |
| E7 | Lessons of the First Ones (an Origin feat per instance). This is the heaviest piece. | Build it in C7c. |
| E8 | Starting-equipment quantities (4 Handaxes, 8 Javelins). Today every chosen bundle item gets `qty 1` in every ruleset. | Fix quantities only on the new 2024 class-package path. The SRD/mixed bundles stay `qty 1` (a separate follow-up if wanted). |
| E9 | Druid L2 Find Familiar. The data marks it "prepared"; the Wild Companion text only lets you cast it with a slot or a Wild Shape use. | The text wins: not always prepared. Wild Companion becomes a note in R9. |
| E10 | Slice C8, 2024 origin languages (Common + 2 Standard). Today a 2024 character has **zero languages**; verified with Human XPHB / Criminal XPHB / Rogue 6. | Build C8. Common is fixed, plus one 2-pick card. Language grants of 2014 records used under 2024 still apply on top (no removal). |
| E11 | 2014 counterparts found on the way (SRD Magical Secrets, 2014 Spell Mastery / Signature Spells, the SRD Monk tool choice that today resolves to no card under every ruleset). Mixed/2014 must not change. | Out of scope. List them as a separate 2014-fidelity follow-up. |
| E12 | XPHB background packages hold narrative placeholders (verified across 16 XPHB backgrounds: `category-gaming-set` ×4, `unlisted-robe` ×2, `unlisted-arrows-(20)` ×2, `unlisted-holy-symbol`, `category-artisans-tools`, `category-musical-instrument`, `unlisted-bolts-(20)`). Fixing them changes mixed output, because XPHB backgrounds are visible under mixed. | Leave them. Optional C9c applies the C9b item map to backgrounds only under 2024. |
| E13 | 2024 subclass build-time choices found by the scan (Lore Bonus Proficiencies and Magical Discoveries, Battle Master Student of War, Fey Wanderer Otherworldly Glamour, Hunter's Prey / Defensive Tactics, Wild Heart Aspect of the Wilds, Draconic Elemental Affinity, Elements Elemental Epitome, Abjurer/Diviner/Evoker/Illusionist Savant free spellbook spells, Illusionist Improved Illusions cantrip, Beast Master companion type, Fey Wanderer gifts). | Out of this plan. Offer a later "C6f subclass choices" plan. |
| E14 | Optional slice R9, the 2024 resource tail (Innate Sorcery, Sorcerous Restoration, Uncanny Metabolism, Divine Intervention, Paladin's Smite free cast, Faithful Steed, Tireless, Wild Resurgence, Stroke of Luck, Wild Companion note). | Build it after C7, if the user wants it. |

## 2. Verified data facts

**XPHB class records.** Those with `optionalfeatureProgression`:
- Sorcerer Metamagic `{"2": 2, "10": 4, "17": 6}` (featureType MM).
- Warlock Eldritch Invocations `[1,3,3,3,5,5,6,6,7,7,7,8,8,8,9,9,9,10,10,10]` (featureType EI). This is identical to `class_2024_tables["warlock"]["invocations"]`.
- `load_class_2024_records` does not keep this key yet.

**optionalfeatures.json.**
- EI: PHB 32, TCE 8, XGE 14, **XPHB 28**. MM: PHB 8, TCE 2, **XPHB 10**.
- None of the 38 XPHB EI/MM records is in `catalog.features` today. Ids `opt-<slug>-xphb` are collision-free; verified with the converter's own id rule. `catalog.features` holds 76 `opt-*` records today.
- Repeatable is a named sub-entry `{"name": "Repeatable"}`. Four invocations carry it: Agonizing Blast, Eldritch Spear, Repelling Blast, Lessons of the First Ones.

**XPHB EI prerequisites.**

| Warlock level | Invocations |
|---|---|
| none | Armor of Shadows, Eldritch Mind, Pact of the Blade / Chain / Tome (5) |
| 2 | Agonizing Blast (+ damaging Warlock cantrip), Devil's Sight, Eldritch Spear (+ damaging cantrip), Fiendish Vigor, Lessons of the First Ones, Mask of Many Faces, Misty Visions, Otherworldly Leap, Repelling Blast (+ attack-roll cantrip) (9) |
| 5 | Ascendant Step, Eldritch Smite (Blade), Gaze of Two Minds, Gift of the Depths, Investment of the Chain Master (Chain), Master of Myriad Forms, One with Shadows, Thirsting Blade (Blade) (8) |
| 7 | Whispers of the Grave |
| 9 | Gift of the Protectors (Tome), Lifedrinker (Blade), Visions of Distant Realms |
| 12 | Devouring Blade (Thirsting Blade) |
| 15 | Witch Sight |

- Prerequisite shapes: `level.level`, `optionalfeature: ["pact of the blade|xphb"]`, `spell: [{"choose": "level=0|class=Warlock", "entry": "...Deals Damage" / "...via an Attack Roll"}]`.
- Data-carried effects:
  - `additionalSpells.innate._`: at-will lists for mage armor, levitate, false life, disguise self, alter self, silent image, invisibility, jump, arcane eye, speak with dead.
  - `daily.1e`: water breathing.
  - Find familiar under `ritual`.
  - Pact of the Tome: `known` "level=0" ×3 and `prepared` "level=1|ritual" ×2.
  - Witch Sight `senses: [{"truesight": 30}]`.
  - Lessons `featProgression` (category O).
- Every XPHB spell id these need exists (`mage-armor-xphb` ... `find-familiar-xphb`, `contact-other-plane-xphb`, `hunters-mark-xphb`, `divine-smite-xphb`, `find-steed-xphb`, `speak-with-animals-xphb`, `power-word-heal-xphb`, `power-word-kill-xphb`).

**Spell damage / attack data.**
- Converted official spells keep no damage or attack data today. Keys: casting_time, classes, components, concentration, desc, duration, higher_level, index, level, name, range, ritual, ruleset, school, source.
- The raw 5etools spells have `damageInflict` and `spellAttack` (Eldritch Blast `['force']`/`['R']`; Toll the Dead `['necrotic']`/none; Minor Illusion neither).
- SRD spells have `damage` and `attack_type`.
- XPHB Warlock cantrips (2024 visible): blade-ward, chill-touch, eldritch-blast, friends, mage-hand, mind-sliver, minor-illusion, poison-spray, prestidigitation, thunderclap, toll-the-dead, true-strike.

**XPHB Metamagic costs** (from the text): Heightened 2, Quickened 2; Careful, Distant, Empowered, Extended, Seeking, Subtle, Transmuted, Twinned 1 each. Matches the `consumes.amount` field (default 1).

**XPHB class features with a build-time choice.** The full scan of `class_2024_level_features` plus the 23 child records is in section 3.

**XPHB child records used as options.**
- `xphb-cleric-7-divine-strike`, `xphb-cleric-7-potent-spellcasting`.
- `xphb-druid-7-potent-spellcasting`, `xphb-druid-7-primal-strike`.
- Improved versions are class features at Cleric 14 (Divine Strike 2d8; Potent: temp HP = 2×WIS) and Druid 15 (Primal Strike 2d8; Potent: cantrip range +300 ft).

**Skill choices: XPHB `startingProficiencies` vs SRD.**
- Fighter adds **Persuasion** (9 options).
- Rogue drops **Performance** (10 options, count 4).
- Wizard adds **Nature** (7 options).
- All other lists and counts are equal (Bard any 3, Ranger 3 of 8).
- Multiclass skill picks: Bard any 1, Ranger 1 of 8, Rogue 1 of 10 (SRD 11).

**Weapon / armor: XPHB vs SRD.**
- Bard: simple only (SRD adds longswords, rapiers, shortswords, hand crossbows).
- Druid: light armor, shields, simple (SRD: medium armor, 11 named weapons).
- Monk: simple + Martial with Light (SRD: simple + shortswords). Tools: one Artisan's Tool OR Musical Instrument (the raw data is a two-alternative list).
- Rogue: simple + Martial Finesse/Light (F1-4 already does this through an override).
- Sorcerer and Wizard: simple (SRD: 5 named).
- Fighter and Paladin: light, medium, heavy, shield (equals SRD `all-armor`).

**Multiclass proficiencies: XPHB vs SRD.**
- Barbarian, Fighter, Paladin, Ranger lose `simple-weapons`.
- Druid loses `medium-armor`.
- Monk gains nothing (SRD: simple + shortswords).
- Warlock: light armor only (SRD: + simple).
- Cleric, Rogue, Bard: equal apart from skill lists.

**Saving throws and hit dice.** Equal to SRD for all 12 classes (verified). XPHB `primaryAbility` matches the SRD multiclass prerequisites (VERIFY by test).

**Starting equipment** (`startingEquipment.defaultData`, A/B, Fighter A/B/C, gold `value` in cp).
- Run through the background converter `_starting_equipment_options_from_5etools`:
  - Monk crashes, because its member is `{"equipmentTypes": [...]}` (plural).
  - Non-catalog members: Bard `category-musical-instrument`, Cleric `unlisted-holy-symbol`, Druid `unlisted-druidic-focus`, Fighter/Ranger/Rogue `unlisted-arrows-(20)`, Wizard robe and `special: Spellbook`.
- Catalog items exist for the mapping:
  - `arrow` (SRD bundles use count 20), `robes`, `spellbook`, `quarterstaff`, `sprig-of-mistletoe`, `crystal`, `orb`.
  - Holy symbols `amulet` / `emblem` / `reliquary` (`gear_category holy-symbols`; 2024 Holy Symbol table = Amulet / Emblem / Reliquary, PHB ch. 6).
  - Druidic Focus "Wooden staff (also a Quarterstaff)" (PHB ch. 6). The Druid package text says "Druidic Focus (Quarterstaff)".
- `reference_data.TOOLS`: Artisan's Tools 17, Musical Instrument 10.

**XPHB class `additionalSpells`** (always prepared from that class level):
- Bard 20 Power Word Heal / Kill. Bard `expanded` 10: `level=1;2;3;4;5|class=Cleric;Druid;Wizard`, plus s6–s9 keys (Magical Secrets).
- Druid 1 Speak with Animals, Druid 2 Find Familiar (see E9).
- Paladin 2 Divine Smite, Paladin 5 Find Steed.
- Ranger 1 Hunter's Mark.
- Warlock 9 Contact Other Plane.

**Languages.**
- `reference_data.LANGUAGES` has 16 entries. Common Sign Language, Druidic and Thieves' Cant are missing.
- The PHB 2024 ch. 2 tables (user's markdown, lines ~2135–2160):
  - Standard: Common, Common Sign Language, Draconic, Dwarvish, Elvish, Giant, Gnomish, Goblin, Halfling, Orc.
  - Rare: Abyssal, Celestial, Deep Speech, Druidic, Infernal, Primordial, Sylvan, Thieves' Cant, Undercommon.
- Exports label languages through `LANGUAGES` (`markdown_export._LANGUAGE_NAMES`, `pdf_export._LANGUAGE_NAMES`). The SPA does not render languages.
- `chosen_languages` in `resolve()` only reads `background` / `species` / `feat` choices whose id ends `:languages`.

**SRD choice cards still offered under 2024 today** (`_feature_choice_templates` reads SRD refs):
- bard-expertise-1/2 (levels 3/10), rogue-expertise-1/2 (1/6; options include thieves' tools).
- metamagic-1/2/3 (3/10/17).
- eldritch-invocations (2), pact-boon (3).
- favored-enemy-1/2/3 (1/6/14), natural-explorer-1/2/3 (1/6/10).

**Existing golden.** `tests/golden/g2_resolve_baseline.json.gz` contains a **2024 case** (`srd-monk5-2024`) that C9a will legitimately change.

## 3. Scan: every choice-bearing 2024 class feature

| Class | Feature (level) | Status | Slice |
|---|---|---|---|
| Barbarian | Weapon Mastery (1) | done (C2) | – |
| Barbarian | Primal Knowledge (3): +1 skill from the Barbarian L1 list | **new** | C6b-2 |
| Barbarian | Brutal Strike (9/13/17) | per-attack, not build-time | not modelled (note) |
| Bard | Spellcasting (1) | done | – |
| Bard | Expertise (2, 9): 2 skills each | **remap** | C6b-1 |
| Bard | Magical Secrets (10): list expansion | **new** | C6d |
| Bard | Words of Creation (20): always prepared | **new** | C6d |
| Cleric | Divine Order (1) | done (C6a) | – |
| Cleric | Blessed Strikes (7) + Improved (14) | **new** | C6c-2 |
| Cleric | Divine Intervention (10) | per-use | R9 resource |
| Druid | Primal Order (1) | done | – |
| Druid | Druidic (1): language + always-prepared Speak with Animals | **new** (fixed grants) | C6b-2 / C6d |
| Druid | Wild Shape (2): known Beast forms | no beast data | disclose |
| Druid | Elemental Fury (7) + Improved (15) | **new** | C6c-2 |
| Fighter | Fighting Style (1), Weapon Mastery (1) | done | – |
| Fighter | Tactical Master (9) | per-attack | note |
| Monk | none build-time; Uncanny Metabolism is a resource | – | R9 |
| Paladin | Weapon Mastery (1), Fighting Style (2) | done | – |
| Paladin | Paladin's Smite (2), Faithful Steed (5): always prepared + free cast | **new** | C6d / R9 |
| Ranger | Favored Enemy (1): Hunter's Mark resource done; always prepared | **new** | C6d |
| Ranger | Weapon Mastery (1), Fighting Style (2) | done | – |
| Ranger | Deft Explorer (2): 1 Expertise + 2 languages | **new** | C6b-1 / C6b-2 |
| Ranger | Expertise (9): 2 | **new** | C6b-1 |
| Ranger | 2014 Favored Enemy / Natural Explorer cards under 2024 | **remove** | C6b-1 |
| Rogue | Expertise (1, 6): skills only in 2024 | **remap** | C6b-1 |
| Rogue | Thieves' Cant (1): Thieves' Cant + 1 language | **new** | C6b-2 |
| Rogue | Weapon Mastery (1) | done | – |
| Rogue | Cunning Strike / Devious Strikes | per-attack | note |
| Sorcerer | Metamagic (2/10/17): 2/4/6, XPHB list | **new** | C6c-1 |
| Sorcerer | Innate Sorcery (1), Sorcerous Restoration (5) | resources | R9 |
| Warlock | Eldritch Invocations (1): XPHB list, Pact as invocation | **new** | C7a–c |
| Warlock | Magical Cunning (2), Contact Patron (9): resources; Contact Patron also always prepared | **new** | C7b / C6d |
| Warlock | Mystic Arcanum (11–17) | done (R7) | – |
| Wizard | Scholar (2): 1 Expertise from 6 skills | **new** | C6b-1 |
| Wizard | Spell Mastery (18), Signature Spells (20) | **new** | C6d |
| All | Starting proficiencies, skill choices, multiclass proficiencies, equipment | **new** | C9a / C9b |

## 4. Slices

### F0 Golden baseline for mixed and 2014 (S, tests only). Run first.

**Goal.** A machine guard for "mixed/2014 must not change" across the whole series.

**Files.**
- New `server/tests/test_c_series_golden.py`.
- New `server/tests/golden/c_series_mixed_2014_baseline.json.gz`, written by a one-off script from the current engine. The script lives in the scratchpad and is not committed; the test documents how it was produced.
- `server/tests/test_worn_wielded.py`: names ending `-2024` are excluded from the strict comparison, with a docstring explaining that 2024 output evolves through the C-series. Keep the file entry.

**Cases.** Each in both `mixed` and `2014`:
- The 12 SRD classes at levels 1, 3, 11 and 20 with every pending choice auto-filled. Reuse the `kitchen_sink.fill` "first option" filler.
- Multiclasses: Wizard 1 / Fighter 1, Rogue 3 / Bard 2, Warlock 5 / Sorcerer 3, Cleric 1 / Druid 1, Barbarian 3 / Monk 2.
- Every non-2024 kitchen-sink entry.
- Under `sources: []` and `["srd"]`.

**Test.** Exact equality after JSON round trip.
- A later slice may add an explicitly listed additive key to a strip list (like `strip_g2`). Any other difference fails.
- The test skips when the official data is missing (`has_official_classes()`).

**Acceptance.** Suite green. Golden file under 2 MB gzipped (trim levels if larger).

### C9a 2024 class chassis: starting and multiclass proficiencies, skill and tool choices (M). Depends on F0.

**Why first.** It changes `rc["cls"]`, which feeds the feat prerequisite pre-walk, the Weapon Mastery gate, the expertise gate (thieves' tools), Primal Knowledge (Barbarian skill list) and the Scholar options (Wizard Nature). Every later slice then tests against correct 2024 proficiencies. It also folds in the F1-4 Rogue hack.

**Files and functions.**

1. New `server/catalog/official/class_chassis.py`: `convert_class_chassis_2024(records, srd_classes) -> {cls: dict}`. It returns a **full merged class dict** `{**srd_cls, ...overlay}` and never mutates the SRD dict. Overlay keys:
   - `proficiencies`: `[{"index": id}]`.
     - Armor: `light-armor`, `medium-armor`, `heavy-armor`, `shields`.
     - Weapons: `simple-weapons`, `martial-weapons`, `martial-weapons-finesse-or-light` (Rogue), new `martial-weapons-light` (Monk).
     - Fixed tools: `thieves-tools`, `herbalism-kit`.
     - Saving throws `saving-throw-xxx` from the XPHB `proficiency` key (keeps the SRD list shape).
     - Map 5etools strings by `{@filter ...}` text; anything unmapped raises in the converter (test).
   - `proficiency_choices`:
     - Skills: `_skill_choice_envelope_from_5etools`.
     - Tools: Bard `anyMusicalInstrument: 3` through `_background_tool_choice_envelopes_from_5etools`.
     - Monk: the two-alternative list becomes ONE `options_array` envelope of the 27 Artisan's Tools + Musical Instruments from `reference_data.TOOLS`.
   - `multi_classing`: `{**srd_mc (prerequisites kept), "proficiencies": [...], "proficiency_choices": [...]}` from `multiclassing.proficienciesGained`.
   - `starting_equipment: []` and `starting_equipment_options: []`. C9b fills the options; until then, under 2024, the class card shows the SRD options — **VERIFY** decision: leave the SRD options in C9a and replace them in C9b. Simplest: C9a copies the SRD equipment keys unchanged.
2. `server/catalog/loader.py`:
   - `Catalog.classes_2024: dict[str, dict]` (default `{}`).
   - New `_merge_class_chassis_2024(catalog)` called after `_merge_official_items`.
   - `official_source.py` re-exports the converter.
3. `server/engine/resolve.py`, in the per-entry class loop (~line 3796, where `entry_cls` is read):
   - When `draft.get("ruleset") == "2024"` and `catalog.classes_2024.get(entry_cls_id)`, use that dict as `entry_cls`.
   - Read the raw ruleset, as O2 does: only the exact string "2024" matters.
   - Everything downstream (pre-walk `held.proficiency_ids`, `_class_choice_templates`, `_multiclass_proficiency_choice_templates`, the proficiency block, `_equipment_choice_templates`) reads it unchanged.
4. Delete `reference_data.RULESET_CLASS_WEAPON_PROFICIENCIES` and its branch in the proficiency block (~line 4939). Keep `MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID`.
5. `server/engine/attacks.weapon_is_proficient`: add `martial-weapons-light` (Martial and `light` property). Add the constant `MARTIAL_LIGHT_PROFICIENCY_ID` in `reference_data`.
6. `reference_data.proficiency_label`: an override map, so exports print "Martial weapons with Finesse or Light" and "Martial weapons with Light".
7. `app.py` `/api/catalog/class/<id>`: when `ruleset == "2024"`, spread `classes_2024[id]` if present, and compute `levelFeatureCounts` from `class_2024_level_features`. This removes the C5 display drift on ClassPage.

**Tests** (new `server/tests/test_class_chassis_2024.py`, real data `needs_classes`).

Converter:
- 12 records.
- Fighter skill envelope 9 options incl. `skill-persuasion`; Rogue 10, no `skill-performance`, count 4; Wizard 7 incl. `skill-nature`.
- Monk tool envelope: 27 options, count 1.
- Bard instruments count 3.
- Every proficiency string mapped (unknown raises).
- Saves equal SRD for all 12.

Resolve, 2024:
- Fighter 1: prof-choice-0 has 9 options.
- Rogue 1: Rapier, Scimitar and Whip proficient (attack rows `proficient`); Longsword not; `sheet.proficiencies.weapons` contains `martial-weapons-finesse-or-light` and not `longswords`.
- Monk 1: Shortsword and Scimitar proficient, Longsword not; tool card present with 27 options.
- Bard 1: Longsword not proficient.
- Druid 1: no `medium-armor`; scale mail gives the armor warning.
- Wizard 1 / Fighter 1 (secondary Fighter): weapons include `martial-weapons`, armor light/medium/shields, no `simple-weapons` from the Fighter (the Wizard grants it anyway; also assert on Barbarian 1 / Fighter 1).
- Cleric 1 / Monk 1: the Monk grants nothing.
- Wizard 1 / Rogue 1: Rogue multiclass skill card has 10 options.

Unchanged and guards:
- `mixed` / `2014`: covered by the F0 golden.
- The weapon-mastery Rogue tests in `test_weapon_mastery.py` stay green with the override deleted.
- Multiclass prerequisite parity: for each class, the XPHB `primaryAbility` equals the SRD multiclass prerequisite (abilities, and any-of vs all-of; Fighter STR or DEX).
- SRD-only catalog: no overlay, no crash.

**Acceptance.** All gates green. The G2 golden 2024 case is excluded per F0.

**Risks.**
- Existing 2024 tests that relied on SRD proficiencies. Grep `"2024"` in `test_weapon_mastery.py`, `test_class_order.py`, `test_fighting_style_feats.py`, `test_resolve.py` and `kitchen_sink.py`, and update them in the same commit, listing each.
- The A1/C3 pool sizes are unchanged: the Fighting Style flag does not depend on proficiencies; armor-proficiency feat prerequisites may change for Druid medium armor. VERIFY the pool counts in `test_asi_feat_eligibility.py` under 2024.

### C6b-1 2024 expertise cards and removal of the SRD Ranger cards (M). Depends on C9a.

**Rules to quote.**
- Bard 2/9 and Rogue 1/6: "You gain Expertise in two of your skill proficiencies of your choice."
- Ranger 9: "Choose two of your skill proficiencies with which you lack Expertise."
- Deft Explorer: "Choose one of your skill proficiencies with which you lack Expertise."
- Scholar: "Choose one of the following skills in which you have proficiency: Arcana, History, Investigation, Medicine, Nature, or Religion."

**Files.**

1. `reference_data.EXPERTISE_2024`, keyed by XPHB feature id: `{class, level, count, skills: None|[ids], lacks_expertise: bool}`.
   - `xphb-bard-2-expertise` 2, `xphb-bard-9-expertise` 2.
   - `xphb-rogue-1-expertise` 2, `xphb-rogue-6-expertise` 2.
   - `xphb-ranger-2-deft-explorer` 1, `lacks_expertise`.
   - `xphb-ranger-9-expertise` 2, `lacks_expertise`.
   - `xphb-wizard-2-scholar` 1, skills `[arcana, history, investigation, medicine, nature, religion]`.
   - Source comment quoting the text.
2. `resolve._expertise_2024_templates(catalog, rc, ruleset)`:
   - Ruleset 2024 only, and only when the feature id exists in `catalog.features`.
   - One card per entry with `level <= rc["level"]`. cid `class:<cls>:<lvl>:expertise-choice:<fid>`, `source.level` = lvl, label = XPHB feature name, description = feature text.
   - Options: the 18 `skill-*` ids from `SKILL_NAMES`, or the listed skills. Never tools.
   - Called in the per-class template loop next to `_feature_choice_templates`.
   - The existing `_gate_expertise_choices` (proficiency) and the `sheet.expertiseSkills` / `derived.skills` merge work unchanged because of the `expertise-choice` marker.
3. `lacks_expertise` gate, inside `_gate_expertise_choices`, keyed by a template flag `lacksExpertise` (strip it from output like `count_by_level`):
   - Walk the expertise cards in order: feat expertise first, then class order, then level.
   - For a flagged card, disable options that already have Expertise from an earlier card or feat ("already has Expertise"). Drop such stored picks with a `pruned` entry.
   - Unflagged cards are unchanged (E1 default).
4. Skip list under 2024, only when the replacing XPHB card exists. Pass these to `_feature_choice_templates(skip_features=...)`, merged with the C3 set:
   - `bard-expertise-1/2`, `rogue-expertise-1/2`.
   - `favored-enemy-1-type`, `favored-enemy-2-types`, `favored-enemy-3-enemies`.
   - `natural-explorer-1-terrain-type`, `natural-explorer-2-terrain-types`, `natural-explorer-3-terrain-types`.
   - Ranger cards: always skipped under 2024 whenever `class_2024_records["ranger"]` exists (2024 Favored Enemy is the R4 resource).
5. `engine/sheet_features.py`, generic attach-by-id:
   - `_xphb_class_rows` also returns the feature id.
   - A choice whose `_CLASS_CHOICE_ID` group 2 is an id present in this class's XPHB rows attaches to that row. Add `languages` to the kind alternation now, for C6b-2.
   - Remove the now-dead SRD map entries only if no 2024 card uses them. Mixed never uses the overlay, so the entries can stay; leave them, since they are harmless.
   - Update `SRD_CHOICE_FEATURES_WITHOUT_XPHB`: Natural Explorer rows are no longer reachable under 2024 (closes open question 9).

**Tests** (new `server/tests/test_expertise_2024.py`).
- Bard 1: no expertise card. Bard 2: one card, count 2, 18 skill options, no thieves' tools. Bard 9: two cards. No `class:bard:3:...bard-expertise-1` card under 2024. Bard 3 under mixed: unchanged SRD card (F0 covers this too).
- Rogue 1 (2024): `class:rogue:1:expertise-choice:xphb-rogue-1-expertise`; thieves' tools not an option. Rogue 6: two cards.
- A non-proficient skill is disabled "not proficient" (existing gate).
- Ranger 2 (2024): Deft Explorer card count 1. With Stealth already expert from a feat or an earlier card, Stealth is disabled "already has Expertise". A stored Stealth pick is pruned.
- Ranger 9: second card count 2. Two cards picking the same skill: the later one is pruned.
- Ranger 1/6/14 (2024): no `enemy-type` / `terrain-type` cards. A stored 2014 favored-enemy pick lands in `pruned`.
- Wizard 2 (2024): Scholar with 6 options; Nature enabled only if proficient (Wizard skill pick or background).
- Bard 2 / Rogue 1 multiclass: four cards total; both attach to their own XPHB rows in `sheet.features`.
- `sheet.features` (2024) Bard 9: rows "Expertise" level 2 and level 9 each carry their picks.
- `derived.skills`: Rogue 1 DEX 16, Stealth proficient + expertise = 3 + 4.
- SRD-only catalog: SRD cards remain.

**Risks.** `test_class_2024_feature_list.py` asserts Bard/Rogue/Ranger expertise and favored-enemy attachment through SRD cids under 2024. Rewrite those cases to the XPHB cids, list them in the commit, and remove the corresponding `SRD_TO_XPHB_FEATURE` expectations only where they are now unreachable.

### C6b-2 2024 class languages and Primal Knowledge (S–M). Depends on C6b-1.

**Rules.**
- Thieves' Cant: "You know Thieves' Cant and one other language of your choice, which you choose from the language tables in chapter 2."
- Druidic: "You know Druidic".
- Deft Explorer: "You know two languages of your choice from the language tables in chapter 2."
- Primal Knowledge: "You gain proficiency in another skill of your choice from the skill list available to Barbarians at level 1."

**Files.**
1. `reference_data`:
   - `LANGUAGES_2024_STANDARD` / `LANGUAGES_2024_RARE` (ids `common`, `common-sign-language`, ..., `thieves-cant`, `druidic`), with a source comment citing PHB 2024 ch. 2.
   - `LANGUAGE_NAMES` = the union of all tables, used by the exports.
   - **Do not** add the new ids to `LANGUAGES`: that list drives every mixed/2014 language choice.
   - `markdown_export.py` / `pdf_export.py` read `LANGUAGE_NAMES`.
2. `reference_data.CLASS_LANGUAGES_2024`:
   - `rogue`: fixed `thieves-cant`, choice 1, feature `xphb-rogue-1-thieves-cant`, level 1.
   - `druid`: fixed `druidic`, `xphb-druid-1-druidic`, level 1.
   - `ranger`: choice 2, `xphb-ranger-2-deft-explorer`, level 2.
3. `resolve._class_language_templates(catalog, rc, ruleset, known)`:
   - cid `class:<cls>:<lvl>:languages:<fid>`, options = standard + rare (E2).
   - Options already known (fixed race/background/feat/class languages, other language selections) are disabled "already known". Use a late gate like the expertise gate, so selections on other cards count: `_gate_language_choices`.
   - Fixed class languages are added to `fixed_languages` (~line 5080) under 2024.
   - `chosen_languages` additionally accepts `kind == "class" and ":languages:" in id`.
4. Primal Knowledge:
   - `resolve._primal_knowledge_template`: Barbarian ≥ 3 under 2024, cid `class:barbarian:3:feature:xphb-barbarian-3-primal-knowledge`, count 1.
   - Options = the Barbarian XPHB L1 skill list, from `classes_2024["barbarian"]["proficiency_choices"][0]`.
   - Late gate: options the character is already proficient in from any other source are disabled "already proficient". Compute from `proficient_skills` minus this card's own selection.
   - Skills flow into `proficient_skills` through the existing class-kind merge.

**Tests** (new `server/tests/test_class_languages_2024.py`).
- 2024 Rogue 1: `languages` include `thieves-cant`, plus a 19-option card (`common` disabled once C8 grants it; in this slice `common` is enabled unless known).
- Druid 1: `druidic`.
- Ranger 2: card count 2. A pick of Elvish for an Elf is disabled. Picks land in `sheet.proficiencies.languages`.
- Markdown/PDF print "Thieves' Cant" / "Druidic".
- Mixed Rogue: no `thieves-cant` (F0).
- Barbarian 3 (2024): Primal Knowledge with 6 options; Athletics already chosen at level 1 is disabled; the pick appears in `derived.skills` as proficient. Barbarian 2: no card.
- `sheet.features` Deft Explorer row lists the expertise and the languages.

### C6c-1 XPHB optional-feature import (EI + MM) and 2024 Metamagic (M). Depends on C6b-1 (attach rule).

**Files.**

1. `official/subclasses.py`:
   - `load_class_2024_records` adds `"optional_feature_progression": raw.get("optionalfeatureProgression") or []`.
   - New `convert_class_optional_features_2024(raw_options, resolve_spell)` for records with `source == "XPHB"` and featureType EI or MM. Output `opt-<slug>-xphb` = `{index, name, desc, source "XPHB", ruleset "2024", feature_types, repeatable, prerequisite_2024, spells, senses, feat_progression, cost}`:
     - `repeatable`: a named "Repeatable" sub-entry exists.
     - `prerequisite_2024`: `{level, optional_features: [opt ids], cantrip: "damage"|"attack"|None}`, parsed from `prerequisite` (the `entry` text "via an Attack Roll" → "attack", otherwise "damage").
     - `spells`: from `additionalSpells`, as `innate [{spell id, uses "at-will"|"1/long rest"|"ritual"}]` plus `known_choose` / `prepared_choose` as parsed filters (reuse `_parse_spell_filter`).
     - `cost`: MM `consumes.amount`, default 1.
   - Do NOT widen `OPTION_FEATURE_TYPES`: the subclass path must not change.
2. `loader._merge_official_subclasses`: merge them. Raise on an id clash (none verified). `test_loader` feature count +38.
3. `official/spells.py::_spell_from_5etools`: add `damage_inflict` (list) and `spell_attack` (list). New `engine/spells.py::spell_deals_damage(spell)` = `bool(damage_inflict or damage)` and `spell_attack_roll(spell)` = `bool(spell_attack or attack_type)`. Used by C7.
4. `resolve._metamagic_2024_template(catalog, rc, ruleset)`:
   - Sorcerer under 2024, record progression `{2:2, 10:4, 17:6}`. Count = value at the highest reached level; none below 2.
   - cid `class:sorcerer:2:feature:xphb-sorcerer-2-metamagic`, `count_by_level: True` (level-down → `pruned`, not a problem).
   - Options: the 10 XPHB MM records, label "Careful Spell (1 SP)".
   - Skip SRD `metamagic-1/2/3` under 2024 when this card exists.
5. `class_resources._sorcerer`: under 2024, `details.metamagic = [{name, cost}]` for the selected options. Printed by `resource_detail_parts` / `ClassResourcesList` ("метамагия: Quickened Spell (2)").

**Tests** (new `server/tests/test_metamagic_2024.py`).
- Converter: 38 records; repeatable exactly {Agonizing Blast, Eldritch Spear, Repelling Blast, Lessons of the First Ones}; Thirsting Blade prerequisite `{level 5, optional_features [opt-pact-of-the-blade-xphb]}`; Agonizing Blast `cantrip "damage"`, Repelling Blast `"attack"`; Witch Sight `senses {truesight 30}`; Gift of the Depths innate water-breathing-xphb "1/long rest"; MM costs as in section 2.
- Spells: `eldritch-blast-xphb` deals damage and has an attack roll; `toll-the-dead-xphb` deals damage, no attack; `minor-illusion-xphb` neither; SRD `eldritch-blast` both.
- Sorcerer 1 (2024): no card. 2: count 2, 10 options. 10: 4. 17: 6. 10 → 9 with 4 stored: pruned "now allows 2". No SRD metamagic cards under 2024; mixed unchanged.
- `sheet.features` Metamagic row (level 2) lists the picks.
- Sorcery Points resource lists the costs.

### C6c-2 Blessed Strikes and Elemental Fury (S–M). Depends on C6c-1 (or C6b-1 only).

**Rules.**
- Blessed Strikes: "You gain one of the following options of your choice (if you get either option from a Cleric subclass in an older book, use only the option you choose for this feature)."
- Elemental Fury: "You gain one of the following options of your choice."
- Option texts are in section 2.

**Files.**

1. Generalise C6a:
   - `reference_data.CLASS_ORDER_CHOICES` becomes `CLASS_OPTION_CHOICES_2024` keyed `(class, slug)` with `level` (divine-order 1, primal-order 1, blessed-strikes 7, elemental-fury 7).
   - The C6a cids stay `class:cleric:1:divine-order` (no migration).
   - New cards use `class:cleric:7:feature:xphb-cleric-7-blessed-strikes` / `class:druid:7:feature:xphb-druid-7-elemental-fury`.
   - Rename `_class_order_*` to `_class_option_*`, taking `(cls, slug)`. Keep thin wrappers or update the call sites. The C6a tests must stay green unchanged.
2. Effect records:
   - `divine_strike`: `{dice_by_level {7: "1d8", 14: "2d8"}, types "Necrotic or Radiant"}`.
   - `primal_strike`: `{dice_by_level {7: "1d8", 15: "2d8"}, types "Cold, Fire, Lightning, or Thunder"}`.
   - `potent_spellcasting`: `{ability "WIS", cleric_14_temp_hp: "2×WIS", druid_15_range: 300}`.
3. `class_resources._cleric` / `_druid`, under 2024 and with the pick:
   - `cleric:divine-strike` with `dice`, `details.note` "once per turn, weapon hit".
   - `cleric:potent-spellcasting` with `bonus` = WIS mod, `details.note` (at 14 add "temp HP 2×WIS = N").
   - Druid equivalents (at 15, Potent adds "cantrip range +300 ft").
   - `class_resources.annotate_attacks`: weapon rows get the note "Divine Strike: +1d8 necrotic or radiant (once per turn)" / "Primal Strike: ...".
4. Older-subclass rule: under 2024 with a pick, a 2014 cleric subclass feature named "Divine Strike" or "Potent Spellcasting" is not listed with an effect (none is modelled today). Its `sheet.features` row gets no extra choice. Document it; no code unless a row would duplicate.

**Tests.**
- Cleric 6: no card. Cleric 7 (2024): card with 2 options, pending (blocks export).
- Divine Strike: resource dice 1d8; Cleric 14: 2d8; the longsword row carries the note.
- Potent Spellcasting, WIS 16: bonus 3; at 14 the note mentions 6.
- Druid 7 Primal Strike: resource and note; Druid 15: 2d8.
- 7 → 6 with a stored pick: pruned.
- Mixed: no card (F0).
- Cleric 7 / Druid 7 multiclass: both cards.
- `sheet.features` "Blessed Strikes" row has the choice.

### C6d 2024 class spell grants: always prepared, Magical Secrets, Spell Mastery, Signature Spells (M). Depends on C9a (and C4).

**Files.**

1. `load_class_2024_records` adds `additional_spells` (raw). The loader converts it to `catalog.class_2024_spell_grants[cls] = {"always": {level: [spell ids]}, "expanded": {level_key: filter}}`, resolving names through `catalog.resolve_spell_id` (`|xphb` → `-xphb` ids; verified that all exist).
   - Decision E9: drop Druid L2 Find Familiar, with a comment quoting the Wild Companion text.
   - Druid 1 Speak with Animals stays: the Druidic text says "you always have the Speak with Animals spell prepared".
2. `resolve`, in the spell loop where `always_prepared` is built (~line 4411):
   - Under 2024, merge class grants at `level <= rc_level` with label `"<Class>"`.
   - Paladin 1 has no Divine Smite until 2.
   - Ranger 1 Hunter's Mark; Warlock 9 Contact Other Plane; Bard 20 both Power Words.
   - They appear in `sheet.spells[i].alwaysPrepared` and are disabled in the picker, as subclass spells are.
3. Magical Secrets (Bard ≥ 10, 2024): `expanded_spell_ids` += Cleric, Druid and Wizard spells of levels 1..max slot level, via `_spell_filter_options`, which already parses this filter. Options are labelled "(Magical Secrets)" or grouped. VERIFY that the prepared card's `group` tagging still works.
4. Wizard (2024 only, decision E11):
   - `class:wizard:18:spell-mastery-1` / `-2` (count 1 each): options = the effective spellbook spells of level 1 / 2 with `casting_time == "1 action"`; casting times verified as "1 action" strings.
   - `class:wizard:20:signature-spells` (count 2): level-3 spells in the book.
   - Picks join the Wizard's `always_prepared` (disabled in the prepared card).
   - Sheet keys `spellMastery: [{id, name, level}]` and `signatureSpells: [...]` on the Wizard `sheet.spells` entry.
   - Markdown/PDF lines "Майсторство със заклинания: ..." and "Запазени заклинания: ...", mirrored in both exporters.
   - Frontend: `isSpellChoiceId` matches `:spell-mastery-` and `:signature-spells`; `types.ts` `SheetClassSpells.spellMastery?` / `signatureSpells?`.
   - Stale picks after a spellbook change: options not offered → generic pass → `pruned`.

**Tests.**
- Ranger 1 (2024): `alwaysPrepared` has `hunters-mark-xphb` and the prepared card shows it disabled.
- Paladin 1 vs 2: Divine Smite only at 2. Paladin 5: Find Steed.
- Druid 1: Speak with Animals; Druid 2: no Find Familiar.
- Warlock 9: Contact Other Plane. Bard 20: Power Word Heal and Kill.
- Bard 10 (2024): the prepared card offers `fireball-xphb` (Wizard) and `cure-wounds-xphb`; Bard 9 does not.
- Wizard 18 with a book containing Shield (reaction) and Magic Missile: Shield is not offered for mastery-1, Magic Missile is.
- Wizard 20 signature: 2 level-3 book spells; picks are in `alwaysPrepared` and disabled in the prepared card.
- Mixed unchanged (F0).

### C7a 2024 Eldritch Invocation card, counts, prerequisites, Pact as invocation (M). Depends on C6c-1.

**Rule.** "You gain one invocation of your choice ... If an invocation has a prerequisite, you must meet it to learn that invocation." The count comes from the XPHB table.

**Files.**

1. `resolve._invocations_2024_template(catalog, rc, ruleset)`:
   - Warlock under 2024 when XPHB EI records exist.
   - cid `class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations`, count `class_2024_tables["warlock"]["invocations"][level-1]`.
   - Options: the 28 XPHB EI records sorted by name, plus repeat instances `<id>~2..~count` for repeatables (E4).
   - Level-prerequisite options above the level are disabled at template time ("requires warlock level N").
   - The `:invocations:` marker keeps R8's count-variable pruning, `selected_invocation_ids` and the `_class_resources._warlock` reader working.
2. Under 2024, skip SRD `eldritch-invocations` and `pact-boon` when the card exists.
3. `_gate_invocation_choices`: a 2024 branch (`_invocation_unmet_2024(opt, level, selected_ids, warlock_cantrips)`):
   - Level.
   - `optional_features` met when the base id is selected in the same card (strip `~k`).
   - Cantrip prerequisite: at least one selected Warlock cantrip (`class:warlock:spells-cantrips`) satisfies `spell_deals_damage` or `spell_attack_roll`. In C7c, Pact of the Tome cantrips also count (they "function as Warlock spells").
   - Repeat instance k requires instance k-1.
   - Run the gate to a fixed point (at most 3 passes): removing Pact of the Blade must also prune Thirsting Blade and then Devouring Blade.
   - Disabled reasons: "requires Pact of the Blade", "requires a Warlock cantrip that deals damage", "take Agonizing Blast first".
4. `features.selected_invocation_ids` returns base ids (strip `~k`) for effect lookup, and keeps the instance id for per-instance dependents.

**Tests** (new `server/tests/test_invocations_2024.py`).
- Warlock 1 (2024): count 1; 5 enabled options (level 1). No SRD invocation or Pact Boon card. Mixed Warlock 3: SRD cards unchanged (F0).
- Warlock 2: count 3; Agonizing Blast disabled without a damaging cantrip, enabled with `eldritch-blast-xphb`; with only `minor-illusion-xphb` still disabled.
- Repelling Blast with Toll the Dead only: disabled ("attack roll").
- Warlock 5 + Pact of the Blade + Thirsting Blade: valid. Remove Pact: Thirsting is pruned with the reason.
- Warlock 12 + Devouring: removing Thirsting prunes Devouring (fixed point).
- `~2` without the base: disabled. Base + `~2`: both resolved.
- 5 → 4: count 3, over-count pruned.
- Witch Sight disabled below 15.
- `sheet.features` row "Eldritch Invocations" (level 1) lists the picks ("Agonizing Blast (2)").

### C7b Invocation effects (M). Depends on C7a, R8.

**Files.**

1. `reference_data.INVOCATION_EFFECTS_2024`, keyed by XPHB id, holding only what the data does not carry:
   - Armor of Shadows `ac_formula 13+DEX`.
   - Devil's Sight `senses devilsSight 120`.
   - Gift of the Depths `swim_equals_walk` + note "breathe underwater".
   - Notes: Eldritch Mind (advantage on Concentration saves), Thirsting Blade (Extra Attack with the pact weapon; with Extra Attack from a class it adds nothing, per PHB 2024 Multiclassing), Devouring Blade, Eldritch Smite, Lifedrinker, Gaze of Two Minds, Gift of the Protectors (names = max(1, CHA)), Investment of the Chain Master, Pact of the Blade, Pact of the Chain extra notes, One with Shadows "on yourself, in dim light or darkness", Fiendish Vigor "max temp HP".
   - `resource_bonus` for Agonizing Blast (C7c fills the target spell). Eldritch Spear note "range +30×level = N ft".
   - A test asserts every XPHB EI id is in the table or has data-only effects (exhaustiveness).
2. `features.invocation_effects`: merges the data effects (innate spells → `innate_spell` entries with the spell level from the catalog; `senses` from the record) with the table. E6: Pact of the Chain is at-will with the note "Magic action".
3. Speeds: `swim_equals_walk` sets `speeds["swim"] = max(existing, walk)` after Fast Movement / Unarmored Movement.
4. `class_resources._warlock`, under 2024:
   - `warlock:magical-cunning`: uses 1, long rest, `details.note` "regain up to half your Pact Magic slots (rounded up) = N".
   - `warlock:contact-patron` from level 9: uses 1, long rest.
   - Verify both texts (quoted in section 2).
5. Exports: no new top-level keys. `types.ts` unchanged unless new details keys appear (add them).

**Tests.**
- Warlock 1 Armor of Shadows, DEX 14, `worn.armor=null`: AC 15; innate `mage-armor-xphb` at will.
- Devil's Sight: senses 120. Witch Sight 15: truesight 30.
- Gift of the Depths: swim = walk (30), innate water-breathing "1/long rest".
- Pact of the Chain: innate find-familiar-xphb at will with note.
- Eldritch Mind: resource note.
- Warlock 2 Magical Cunning: note "2" at Warlock 5 (2 pact slots → 1? VERIFY the rounding: half of max slots rounded up; Warlock 5 has 2 slots → 1).
- Warlock 9: Contact Patron.
- Mixed SRD Warlock: unchanged (F0).

### C7c Invocation dependents: targets, Pact of the Tome, Pact of the Blade, Lessons of the First Ones (L). Depends on C7b. Decisions E4, E5, E7.

**Files.**

1. `resolve._invocation_dependent_templates(catalog, rc, ruleset, class_choices)`: built from the RAW stored invocation selection (as feat cascades are), so they exist only for picked instances. The cids deliberately contain `:invocation:` (singular) and never `:invocations:`, so R8 plumbing ignores them.
   - Agonizing Blast / Eldritch Spear / Repelling Blast instance → `class:warlock:invocation:<inst>:cantrip`, count 1.
     - Options = selected Warlock cantrips (+ Tome cantrips) that meet the prerequisite (Spear additionally needs `range` ≥ 10 ft; parse "N feet"; VERIFY the range strings).
     - Cantrips chosen by another instance of the same invocation are disabled "already chosen for Agonizing Blast".
     - Effects: Agonizing resource `details.spell` = the pick; Spear note with the pick and range; Repelling note with the pick.
   - Pact of the Tome → `...:opt-pact-of-the-tome-xphb:cantrips` (count 3, `_spell_filter_options({"level": [0]})`) and `...:rituals` (count 2, `{"level": [1], "ritual": True}`).
     - Spells already prepared or known by the Warlock are disabled ("already prepared").
     - Sheet: the Warlock spells entry `pactOfTheTome: [{id, name, level}]`. Markdown/PDF line "Книга на сенките: ...". `types.ts`.
     - `isSpellChoiceId` matches `:opt-pact-of-the-tome-xphb:` so these go to the Spells tab.
   - Pact of the Blade (E5) → `...:opt-pact-of-the-blade-xphb:weapon`, count 1, options = melee weapons in the inventory (granted + chosen + added; needs equipment resolution, so build early and gate late, like Weapon Mastery). Effect on that attack row: proficient, ability = CHA if CHA mod > its normal ability mod, note "Pact weapon".
   - Lessons of the First Ones instance → `...:<inst>:feat`, options `feat:<index>` of category O from `_feat_options` / `_feat_offered` (sources, ruleset), with prerequisite states as ASI feats.
     - Other Lessons instances' feats are disabled "already chosen for Lessons of the First Ones". The S2 `taken` map applies (an Origin feat already from the background is "already taken" unless repeatable).
     - Resolution: new `_LessonsResolver` hook in the F1 ordered walk (the `_FightingStyleResolver` pattern), position (warlock class index, level 2, instance order), origin `class:warlock:invocation:<inst>:feat:<index>`, tagged `_asi_origin`, `_asi_level 2` and `_inv_cid`. Cascaded feat choices (Magic Initiate spells, Skilled picks) via `_feat_choice_templates` / `_feat_spell_choice_templates` with that origin.
     - `feats_summary` origin `"invocation"`; `types.ts` `SheetFeat.origin` union.
2. Frontend: `ClassPage` shows the dependents on the Features tab (prefix `class:warlock:`); Tome spell cards on the Spells tab.

**Tests.**
- Two Agonizing Blast instances with eldritch-blast and toll-the-dead: two resources; the second instance cannot pick eldritch-blast.
- Spear note: range at Warlock 5 = 150 ft.
- Tome: 3 cantrips from any class (e.g. `fire-bolt-xphb`), 2 level-1 rituals; `pactOfTheTome` in the sheet and exports; Tome cantrip `fire-bolt-xphb` satisfies the Agonizing prerequisite.
- Blade: pick longsword, CHA 16 / STR 10, attack uses CHA and is proficient; Thirsting note on that row.
- Lessons: pick Alert XPHB → in `sheet.feats` (origin invocation) and initiative changes. A second instance picking Alert is disabled. A background that already grants Alert → "already taken". Magic Initiate via Lessons cascades its spell cards. Removing the invocation prunes the feat pick.
- Timing: Warlock 20 (2024) with 10 invocations including two Lessons and the Tome, under 50 ms.

**Risks.** The F1 walk ordering and duplicate blame (a Lessons feat vs a later ASI pick) and `taken` snapshots. Write an explicit order test: Warlock 4 with ASI Alert vs Lessons Alert at level 2 → the ASI pick is the duplicate.

### C9b 2024 starting equipment packages (M). Depends on C9a. Decision E8.

**Files.**

1. `official/class_chassis.py`, `_class_equipment_options_2024(raw_starting_equipment)`:
   - Convert `defaultData` A/B(/C) through `_starting_equipment_options_from_5etools`, with a class-specific pre-map (`reference_data.CLASS_2024_EQUIPMENT_ITEM_MAP`):
     - `"arrows (20)"` → `arrow` count 20; `"robe"` → `robes`; `{"special": "Spellbook"}` → `spellbook`.
     - `"druidic focus"` → `quarterstaff` (Druid package text "Druidic Focus (Quarterstaff)").
     - `"holy symbol"` → a nested `option_type: "choice"` over the `holy-symbols` category, in the same shape as the SRD nested picks (print the SRD Paladin envelope to copy the shape).
     - `{"equipmentType": "instrumentMusical"}` → a nested `musical-instruments` choice.
     - Monk `{"equipmentTypes": [...]}` → the sentinel member `monk-tool` (see below).
   - Fix the crash on plural `equipmentTypes` inside the class path only. The background path is untouched (E12).
   - The overlay `starting_equipment_options` replaces the SRD one; `starting_equipment: []`.
2. Quantities (E8): `build_choice_options` and `build_equipment_choice` accept `keep_counts=True` (passed only for the 2024 class envelopes). Options carry `quantities: {itemId: n}`. `_chosen_equipment` / `_gather_equipped_items` use them; `_chosen_equipment` sets `qty`.
3. Monk sentinel: when the selected Monk option contains `monk-tool`, `_chosen_equipment` adds the item of the Monk's tool proficiency pick (`class:monk:1:prof-choice-1`). The text says "chosen for the tool proficiency above". With no pick, a narrative "Artisan's Tools or Musical Instrument (choose the tool proficiency)".
4. Gold: `gp-N` bundle members are already summed into `sheet.startingGold` with the background's.

**Tests** (new `server/tests/test_class_equipment_2024.py`).
- The converter output for all 12 classes has no `unlisted-` / `category-` member (exhaustive), and no crash.
- Fighter (2024): 3 options; option C gold 155.
- Barbarian A: greataxe ×1, handaxe qty 4, explorer's pack, 15 gp → `startingGold` 15 + background gold.
- Cleric A: a nested holy-symbol pick (3 options) appears once A is selected; Chain Shirt + Shield → AC 13 + DEX(max 2) + 2.
- Bard A: nested instrument pick (10).
- Monk A with tool proficiency `smiths-tools` → item granted.
- Wizard A grants `spellbook`.
- Ranger A: `arrow` qty 20.
- B options give only gold.
- Secondary class: no equipment card (unchanged rule).
- Mixed/2014 SRD packages: unchanged (F0).
- ExportPage/EquipmentPage at 375px: the cards render (generic).

### C8 2024 origin languages (S). Optional, recommended (E10). Depends on C6b-2.

**Rule.** PHB 2024 ch. 2 "Choose Languages": "Your character knows at least three languages: Common plus two languages you roll or choose from the Standard Languages table."

**Files.**
- `resolve`: under 2024, `fixed_languages += ["common"]`.
- Card `origin:languages` (source kind `background`, so BackgroundPage renders it and the export gate counts it), count 2, options = Standard minus Common (9). Already-known ones are disabled through the C6b-2 `_gate_language_choices`.
- `chosen_languages` accepts it: the id ends `:languages` with kind background.
- Frontend `problems.ts` maps nothing new. VERIFY that the BackgroundPage filter (`kind background|feat`, not `class:`) shows it.

**Tests.**
- Human XPHB / Criminal XPHB Rogue 1 (2024): `common` fixed, a card with 9 options, pending (blocks export), picks in languages.
- Rogue Thieves' Cant card has `common` disabled "already known".
- Mixed: unchanged (F0).

### R9 2024 resource tail (S–M). Optional (E14). Depends on C7b.

Builders: Innate Sorcery (2, long), Sorcerous Restoration (1, long, "half sorcerer level"), Uncanny Metabolism (1, long), Divine Intervention (1, long), Paladin's Smite free cast (1, long), Faithful Steed (1, long), Tireless (uses = max(1, WIS mod), long), Wild Resurgence (1, long), Stroke of Luck (1, short-or-long), Wild Companion note.
- Each must be checked against the imported text and its numbers quoted in the test docstring.
- 2024 only, read through `ctx.table` / `ruleset` like R1.
- Tests: one per class.

### F3 Consolidation (M). Last.

1. ARCHITECTURE:
   - Consolidate the per-slice sections into the "2024 chassis (C) overview" table (C6b-1/2, C6c-1/2, C6d, C7a/b/c, C8, C9a/b, F0 marked done).
   - Update "What's implemented vs. not"; the open design questions (close 9; add E-series answers); and the R overview (R9).
   - Remove the F1-4 override text, now folded into C9a.
   - Update the Known gaps list with: Wild Shape forms, per-attack options (Brutal / Cunning Strike, Tactical Master), the E11 2014 counterparts, the E13 subclass choices and the E12 background placeholders.
2. Types drift guard: new `server/tests/test_types_drift.py`.
   - Resolve every kitchen-sink draft (add 2024 entries: Warlock 20 with Tome / Blade / Lessons, Sorcerer 17, Rogue 6, Ranger 9, Bard 10, Wizard 20 with mastery / signature, Cleric 14 Divine Strike, Druid 15 Primal Strike, Monk 1, Fighter 1 package C).
   - Assert every key of `sheet`, `derived`, `sheet.spells[*]`, `sheet.feats[*]`, `derived.classResources[*].details` and `derived.attacks[*]` appears as `key:` or `key?:` in `frontend/src/types.ts` (regex per interface block).
   - Fix any drift found.
3. Kitchen-sink export sweep (S6 test): the new 2024 entries pass the YAML/Markdown/PDF field checks (invocation names, `pactOfTheTome`, `spellMastery`, Metamagic costs, Divine Strike note, languages "Thieves' Cant").
4. Cross-slice review checklist (whole-branch review, ARCHITECTURE "Process notes"):
   - C9a × C2: mastery gate with the new Monk / Rogue / Bard lists.
   - C9a × A1 / A4: armor-proficiency feat prerequisites for the 2024 Druid.
   - C9a × C6b-1: Scholar Nature with the Wizard's new skill list.
   - C6b-1 × S2 / feats: Skill Expert expertise vs `lacks_expertise`.
   - C6b-2 × C8: "already known" across class, origin, species and feat language cards.
   - C6c-1 × R4: Sorcery Points details.
   - C6d × C4: Spell Mastery / Signature from the effective book; always-prepared spells vs the prepared count.
   - C6d × R7: a Bard 10 with Magical Secrets and Mystic-Arcanum-like groups.
   - C7a × C7c fixed point: prerequisite chains with the Tome cantrips.
   - C7c × F1 walk: Lessons vs ASI vs Fighting Style ordering and duplicate blame.
   - C7c × G2: Pact of the Blade with `wielded`.
   - C9b × G2: worn/wielded slots from 2024 packages.
   - F0 golden still byte-identical.
5. Re-time: Fighter 20, Monk 20, Warlock 17 / Paladin 3 and Wizard 20 (mixed and 2024), plus Warlock 20 (2024, full invocations), Sorcerer 20 (2024) and Bard 20 (2024). Each under 50 ms; record the numbers.
6. Final gates and frontend build; browser check at 375px of ClassPage for Warlock 20 / Bard 10 / Rogue 1 (2024) and EquipmentPage for Cleric 1 (2024).

## 5. Global order (test gate after each)

0. Decision gate: ask E1–E14 in one message and record the answers at the top of the plan file.
1. **F0** golden mixed/2014 baseline (+2128 → about 2128 + N golden cases).
2. **C9a** chassis proficiencies, skills, multiclass (folds F1-4).
3. **C6b-1** 2024 expertise cards; remove the SRD Ranger cards; generic sheet attach.
4. **C6b-2** class languages and Primal Knowledge.
5. **C6c-1** XPHB EI/MM import, spell damage/attack fields, Metamagic.
6. **C6c-2** Blessed Strikes / Elemental Fury.
7. **C6d** always-prepared, Magical Secrets, Spell Mastery / Signature.
8. **C7a** invocation card and prerequisites.
9. **C7b** invocation effects plus Magical Cunning / Contact Patron.
10. **C7c** invocation dependents (targets, Tome, Blade, Lessons).
11. **C9b** 2024 starting equipment.
12. **C8** origin languages (if E10 = yes).
13. **R9** resource tail (if E14 = yes).
14. **F3** consolidation, drift guard, review, re-timing.

Each step runs the server suite, the root suite (405 passed / 8 skipped) and `npm run build` when the frontend changed. The F0 golden must stay green at every step. Executors run one at a time (shared repo).

## 6. Cross-cutting risks

- **`resolve.py` is 5203 lines.** New logic goes into helpers. Candidates: `engine/class_choices_2024.py` for the C6b/C6c/C7 template builders and gates, imported by `resolve`; `catalog/official/class_chassis.py` for C9. `resolve()` only wires.
- **Existing 2024 expectations will change on purpose.** `test_class_2024_feature_list.py` (SRD cids under 2024), `test_weapon_mastery.py`, `test_class_order.py`, the `kitchen_sink.py` 2024 entries, the G2 golden 2024 case and `test_loader` counts (+38 features). Each slice lists the tests it changed and why in the commit message.
- **Count-variable pruning.** New level-scaled cards (Metamagic, invocations, Tome counts) must be count-variable (`count_by_level` or the `:invocations:` marker) so a level-down gives `pruned`, not a blocking `over-selected` problem.
- **Repeat-instance ids (`~k`)** must be stripped wherever an effect, feature or label is looked up (`features.invocation_effects`, `class_resources._warlock`, `sheet_features` labels).
- **Missing official data.** Every slice falls back to SRD cards, with no empty card and no crash.
- **Hand-written `types.ts`.** F3 adds a structural guard. Until then, each slice updates it in the same commit.

### Critical Files for Implementation
- /Users/yoanpetrov/dnd-character-creator/server/engine/resolve.py (class loop ~3780–3830, template loop ~4243–4310, spell loop ~4392–4425, `_feature_choice_templates` ~1584, `_gate_expertise_choices` ~1827, `_gate_invocation_choices` ~1868, `_class_order_*` ~3464–3530, proficiency block ~4860–4960, languages ~5080, equipment ~3585–3675)
- /Users/yoanpetrov/dnd-character-creator/server/catalog/official/subclasses.py (`load_class_2024_records`, new `convert_class_optional_features_2024`), /Users/yoanpetrov/dnd-character-creator/server/catalog/official/equipment.py, /Users/yoanpetrov/dnd-character-creator/server/catalog/official/spells.py, new /Users/yoanpetrov/dnd-character-creator/server/catalog/official/class_chassis.py, /Users/yoanpetrov/dnd-character-creator/server/catalog/loader.py
- /Users/yoanpetrov/dnd-character-creator/server/catalog/reference_data.py (`EXPERTISE_2024`, `CLASS_LANGUAGES_2024`, language tables, `CLASS_OPTION_CHOICES_2024`, `INVOCATION_EFFECTS_2024`, `CLASS_2024_EQUIPMENT_ITEM_MAP`; remove `RULESET_CLASS_WEAPON_PROFICIENCIES`)
- /Users/yoanpetrov/dnd-character-creator/server/engine/sheet_features.py, /Users/yoanpetrov/dnd-character-creator/server/engine/class_resources.py, /Users/yoanpetrov/dnd-character-creator/server/engine/features.py, /Users/yoanpetrov/dnd-character-creator/server/engine/attacks.py
- /Users/yoanpetrov/dnd-character-creator/frontend/src/types.ts, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ClassPage.tsx, /Users/yoanpetrov/dnd-character-creator/server/export_fields.py (+ markdown_export.py / pdf_export.py language names and spell lines), /Users/yoanpetrov/dnd-character-creator/server/app.py (class detail under 2024)

Reference inputs: /Users/yoanpetrov/dnd-character-creator/docs/superpowers/plans/2026-10-09-class-resources-2024-chassis-small-gaps.md, /Users/yoanpetrov/dnd-character-creator/docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md, /Users/yoanpetrov/Downloads/Player's Handbook (2024).md (ch. 2 languages ~line 2129, multiclassing ~2548, ch. 6 foci ~7007/7120/7155), ~/.claude/dnd/.data/official/class/*.json, ~/.claude/dnd/.data/official/optionalfeatures.json, /Users/yoanpetrov/dnd-character-creator/server/tests/test_worn_wielded.py (golden pattern), /Users/yoanpetrov/dnd-character-creator/server/tests/kitchen_sink.py.