# Plan: class-feature numbers, the 2024 class chassis, and small gaps

> **Note (2026-10-11):** the statements below that C6b, C6c, C7 and C9 are "skipped" were superseded by `docs/superpowers/plans/2026-10-10-2024-chassis-remaining-stages.md`; all of those slices (plus C8, R9, F0, F3a, F3b) are done. See ARCHITECTURE-CURRENT-STATE.md, "2024 chassis (C) overview".

(Opus planner, 2026-10-09. Suggested file name: `docs/superpowers/plans/2026-10-09-class-resources-2024-chassis-small-gaps.md`.)

I only read code and data for this plan and changed nothing. The numbers below that are marked "verified" came from scripts I ran on the real SRD files (`chargen/data/srd/5e-SRD-Levels.json`, `5e-SRD-Features.json`) and the real 5etools files (`~/.claude/dnd/.data/official/class/*.json`, `items-base.json`, `feats.json`, `optionalfeatures.json`). Anything marked **VERIFY** must be checked by a script before its test is written. If a script and this plan disagree, the script wins, and the executor writes the deviation into the slice's ARCHITECTURE section.

## Decisions (user answers, 2026-10-09)

D3 = separate `duelingDamage` field (default b). D7 = both rulesets, prepared = spellbook. D8 = C1–C4 + C5 + C6a (C6b, C6c, C7, C9 skipped unless asked later; C10 never). D1, D2, D4, D5, D6, D9, D10, D11 = the recommended defaults in the table below.

## Conventions for every slice

- **Order:** test first, then the minimal implementation.
- **Test gate after every slice (all three must be green):**
  - `cd /Users/yoanpetrov/dnd-character-creator/server && ../.venv/bin/python -m pytest -q` (server suite, currently about 1240 tests)
  - `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/python -m pytest -q` (root suite, about 405 passing and 8 skipped; includes `tests/test_chargen_isolation.py`)
  - `cd frontend && npm run build`, whenever the slice touches the frontend.
- **Speed limit:** `resolve()` for a level-20 Fighter (and from R1 on, a level-20 Monk and a Warlock 17/Paladin 3) must stay under 50 ms. The last measured value was about 2.7 ms. Record the before/after numbers in the ARCHITECTURE section.
- **Commits:** one commit per slice, in the style `feat(resources): ... (R1)`. Use the attribution trailer from the executing session's instructions; earlier plans used `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Never stage `Resurses/`. Use `git add <explicit paths>` only, never `git add -A` or `git add .`.
- **ARCHITECTURE doc:** each slice appends a short dated section to `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`, in the same style as the "PART 1/2/3" sections. Step F at the end consolidates them.
- **Real data:** tests that need it use the existing skip markers (`has_official()`, `has_official_classes()`), following `server/tests/test_class_2024_spells.py`.
- **Ruleset rule (U9):** 2024 numbers apply only under `ruleset == "2024"`. `"mixed"` and `"2014"` use the 2014/SRD numbers (see decision D2). The ruleset is in the local `ruleset` in `resolve()` (around line 3398). The class loop reads the raw `draft["ruleset"]`, as in O2.
- **Rule matrices:** for every RAW rule (not just a number), the test file's docstring quotes the governing rule and lists the cases it distinguishes. This is the Phase 3b-ii lesson in ARCHITECTURE "Process notes". It matters most for the multiclass stacking rules in R2 and R3.
- **No visual work.** Frontend changes are plain `<ul>`/`<p>` lists with no new CSS. Check them at 375px: `document.documentElement.scrollWidth === 375` and nothing is hidden behind horizontal scroll.
- **Executors run one at a time** (shared git repo).

---

## Decision points for the user

Each has a recommended default. Executors use the default unless the user overrides it. Ask all of these in one message before starting. D3, D7 and D8 actually block the slices that depend on them.

| # | Question | Recommended default |
|---|---|---|
| D1 | Where do class resources live? | A new `derived.classResources` list (per class, plus subclass entries) shown on ClassPage under each class block and on ExportPage. They do not go into `sheet.features`. |
| D2 | Should `"mixed"` use 2014 or 2024 numbers for resources (rages, channel divinity, wild shape...)? | 2014/SRD numbers. This matches U9 (mixed = SRD chassis). |
| D3 | **Dueling one-hand check.** The engine has no "hands" model. Every granted, chosen and `equipped` added item counts as equipped, so a starting Fighter with a longsword, shield and two handaxes always has "another weapon". | (a) Strict: no Dueling when any other weapon is equipped. Wrong for most starting kits. (b) **Default:** keep the base damage without Dueling and add a separate `duelingDamage` field (like `versatileDamage`) plus a note "only when wielding no other weapon". (c) Add an optional `wielded` flag per item (draft `equipment.wielded: {main, off}` plus an EquipmentPage selector) and apply Dueling only when main hand is one-handed melee and off hand is empty or a shield. Most correct, but it adds a draft field and UI. |
| D4 | Cross-edition same-name feats (U5/U7; 46 name pairs under `mixed`, e.g. Alert PHB/XPHB): should taking one count as "already taken" for the other? | Yes, under every ruleset (it only matters under `mixed`), unless the feat being picked is `repeatable`. |
| D5 | Situational always-on numbers: fold them into `derived`, or keep them only as resource/notes? | Fold into `derived`: Aura of Protection into every save, Diamond Soul / Slippery Mind into save proficiency, Barbarian Fast Movement into walk speed (no heavy armor). Rage damage and resistances stay inside the Rage resource. Sneak Attack and Rage only add notes to attack rows. |
| D6 | Armor of Shadows (Mage Armor at will) as an AC candidate formula 13+DEX, the same pattern as Draconic Resilience? Devil's Sight as darkvision 120? | Yes to both. Devil's Sight goes in as `senses.devilsSight: 120` rather than overriding darkvision, because it also works in magical darkness. |
| D7 | **Wizard spellbook:** both rulesets or 2024 only? Restrict the prepared list to spellbook spells? Restricting means existing drafts' prepared picks outside the book get pruned. | Both rulesets (the rule is the same: 6 at level 1, +2 per level). Prepared options = spellbook contents. Stale picks go to `pruned` (non-blocking). |
| D8 | **2024 chassis scope:** which optional stages (C5–C9) to build. | Build C1–C4 now. C5 and C6a next if the user wants a "real 2024 sheet". C6b, C6c, C7 and C9 are optional. C10 (full parallel `*-xphb` classes) is not recommended. |
| D9 | Weapon Mastery options: weapon kinds from SRD plus the imported non-SRD weapons (Musket, Pistol, Double-Bladed Scimitar, Hoopak, Yklwa) whenever 5etools gives them a mastery? | Yes, as long as the item exists in `catalog.items` and has a mastery. |
| D10 | Feature-text option choices: only build-time choices (Totem Spirit, Aspect of the Beast, Totemic Attunement, Storm Aura), or also choices that can be changed on a rest (Third Eye, Aspect of the Wilds)? | Build-time only. |
| D11 | Mystic Arcanum location. | `sheet.spells[<warlock entry>].mysticArcanum: [{level, id, name}]`, picked through four ordinary choices. |

---

## Part 1: Numeric effects of class features (R slices)

### Data facts (verified by script)

**2014 (SRD level rows).** `class_specific` per class:
- barbarian: `rage_count` (2,2,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,**9999** at 20), `rage_damage_bonus` (+2 at 1–8, +3 at 9–15, +4 at 16–20), `brutal_critical_dice`
- bard: `bardic_inspiration_die`, `song_of_rest_die`, `magical_secrets_max_*`
- cleric: `channel_divinity_charges`, `destroy_undead_cr`
- druid: `wild_shape_max_cr`, `wild_shape_swim`, `wild_shape_fly`
- fighter: `action_surges`, `extra_attacks`, `indomitable_uses`
- monk: `ki_points`, `martial_arts {dice_count, dice_value}` (d4 at 1–4, d6 at 5–10, d8 at 11–16, d10 at 17–20), `unarmored_movement`
- paladin: `aura_range`
- ranger: `favored_enemies`, `favored_terrain`
- rogue: `sneak_attack {dice_count, dice_value}`
- sorcerer: `sorcery_points`, `metamagic_known`, `creating_spell_slots`
- warlock: `invocations_known`, `mystic_arcanum_level_6..9`
- wizard: `arcane_recovery_levels`

Relevant SRD feature ids: `rage`, `fast-movement`, `brutal-critical-*`, `bardic-inspiration-d6/d8/d10/d12`, `font-of-inspiration`, `channel-divinity-1-rest/2-rest/3-rest`, `destroy-undead-*`, `wild-shape-*`, `second-wind`, `action-surge-1-use/2-uses`, `indomitable-1/2/3`, `extra-attack-1/2/3`, `barbarian-extra-attack`, `monk-extra-attack`, `paladin-extra-attack`, `ki`, `martial-arts`, `diamond-soul`, `divine-sense`, `lay-on-hands`, `channel-divinity` (paladin), `aura-of-protection`, `aura-improvements`, `sneak-attack`, `slippery-mind`, `font-of-magic`, `mystic-arcanum-6th-level`…`9th`, `arcane-recovery`, `eldritch-invocation-*` (32).

**2024 (XPHB `classTableGroups`, non-spell columns, 20 rows each):**
- Barbarian: Rages "2,2,3,3,3,4,4,4,4,4,4,5,5,5,5,5,6,6,6,6" (no unlimited at 20); Rage Damage `{type:"bonus", value}` (VERIFY per level); Weapon Mastery 2,2,2,3×6,4×11 (3 at 4, 4 at 10).
- Bard: Bardic Die `{type:"dice", toRoll:[{number, faces}]}`.
- Cleric: Channel Divinity 0,2,2,2,2,3×12,4,4,4 (2 at 2, 3 at 6, 4 at 18).
- Druid: Wild Shape 0,2,2,2,2,3×11,4×4 (2 at 2, 3 at 6, 4 at 17).
- Fighter: Second Wind 2,2,2,3×6,4×11; Weapon Mastery 3,3,3,4×6,5×6,6×5.
- Monk: Martial Arts dice; Focus Points 0,2,3,…,20 (= level from 2); Unarmored Movement `{type:"bonusSpeed"}`.
- Paladin: Channel Divinity 0,0,2×8,3×10.
- Ranger: Favored Enemy 2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,6,6,6,6.
- Rogue: Sneak Attack dice.
- Sorcerer: Sorcery Points 0,2,3,…,20.
- Warlock: Invocations 1,3,3,3,5,5,6,6,7,7,7,8,8,8,9,9,9,10,10,10.

**XPHB subclass tables (verified):** Psi Warrior and Soulknife energy dice, levels 3–20: d6×4 at 3–4, d8×6 at 5–8, d8×8 at 9–10, d10×8 at 11–12, d10×10 at 13–16, d12×12 at 17–20.

**Prose-only values to hardcode** (with a comment, as `reference_data` already does). Executors double-check each against the imported feature text.
- Lay on Hands = 5 × paladin level (both editions).
- Divine Sense (2014) = 1 + CHA modifier uses per long rest.
- Bardic Inspiration uses = max(1, CHA modifier) (both); recharge becomes short rest from bard 5 (Font of Inspiration).
- Second Wind (2014): 1 use, 1d10 + fighter level.
- Arcane Recovery = ceil(level/2) slot levels.
- Ki/Focus save DC = 8 + PB + WIS.
- 2014 Psi Warrior/Soulknife (TCE): dice count = 2 × PB; die d6 at 3, d8 at 5, d10 at 11, d12 at 17.
- Battle Master (both): 4 superiority dice d8, 5 at 7, 6 at 15, d10 at 10, d12 at 18; maneuver DC 8 + PB + max(STR, DEX). VERIFY the XPHB text.
- Arcane Archer: 2 Arcane Shot uses per short rest.

### Resource shape (fixed in R1, extended by later slices)

`derived.classResources: list[ClassResource]`. Ordering: class order, then subclass entries, then insertion order inside a class.

```
{ "id": "barbarian:rage", "classId": "barbarian",
  "source": {"kind": "class"|"subclass", "id": "...", "label": "..."},
  "name": "Rage",
  "uses": int|None, "unlimited": bool?,
  "recharge": "long"|"short"|"short-or-long"|None,
  "die": "d8"?, "dice": "3d6"?, "pool": int?, "bonus": int?, "dc": int?,
  "details": {...}? }
```

Example `details`: Rage's `{"damageBonus": 2, "resistances": ["bludgeoning","piercing","slashing"]}`.

---

### R1: Resource framework, plus Barbarian and Rogue (M)

**Goal.** The pipeline from catalog tables to an engine module to `derived.classResources` to exports, types and a plain frontend list, proven on two classes.

**Files and functions:**
1. `server/catalog/official/subclasses.py`: new `load_class_2024_tables(class_dir) -> {class_id: {column_slug: [20 normalized values]}}`.
   - Reads XPHB class records in the same way as `load_class_2024_progressions`.
   - Skips columns whose label contains `|spells|`, plus "Spell Slots" and "Slot Level".
   - Label normalization: strip `{@filter X|...}` / `{@tip X|...}` down to X, then slug it (`rages`, `rage-damage`, `weapon-mastery`, `bardic-die`, `channel-divinity`, `wild-shape`, `second-wind`, `martial-arts`, `focus-points`, `unarmored-movement`, `favored-enemy`, `sneak-attack`, `sorcery-points`, `invocations`).
   - Value normalization: digit strings become int; `{type:"bonus"|"bonusSpeed", value}` becomes the int value; `{type:"dice", toRoll:[{number,faces}]}` becomes `"NdF"` (e.g. `"1d6"`, `"3d6"`); 0 stays 0.
   - Also `load_subclass_2024_tables` for subclasses with `subclassTableGroups[*].rows` (Psi Warrior / Soulknife XPHB). `{@dice D6}` becomes `"d6"`.
2. `server/catalog/loader.py`: add `Catalog.class_2024_tables` and `Catalog.subclass_2024_tables` (default `{}`), filled where `class_2024_progressions` is filled.
3. New pure module `server/engine/class_resources.py`, modeled on `engine/features.py`:
   - `resources_for(catalog, resolved_classes, modifiers, prof_bonus, ruleset, choices) -> list[dict]`
   - per-class builders `_barbarian(rc, ...)`, `_rogue(rc, ...)`, dispatched by a `_BUILDERS` dict
   - 2014 values from `rc["level_row"]["class_specific"]`, 2024 values from `catalog.class_2024_tables[cls][level-1]`
4. `server/engine/resolve.py`: add `"classResources": class_resources_mod.resources_for(...)` to the `derived` dict (around line 4308). No other change.
5. `server/export_fields.py`: add `("classResources", [])` to `DERIVED_FIELDS`; add an `extra_blocks` section "Ресурси на класа" with one bullet per resource (`name: uses/die/dice/pool/bonus/dc (recharge)`). Bulgarian recharge words: "кратка почивка", "дълга почивка".
6. `frontend/src/types.ts`: `ClassResource` interface and optional `classResources?: ClassResource[]` on `Derived`.
7. `frontend/src/pages/ClassPage.tsx`: in each class block, a plain `<ul>` of `resolution.derived.classResources?.filter(r => r.classId === classId)`.
8. `frontend/src/pages/ExportPage.tsx`: a plain list after Attacks.

**Tests** (new `server/tests/test_class_resources.py`; loader parts use a `tmp_path` class dir like `test_loader_reads_the_xphb_progressions_from_a_class_dir`):
- Loader: synthetic class file with Rages/Rage Damage/Sneak Attack columns gives ints and `"2d6"`; a spell column is skipped. Real catalog (`needs_classes`): `class_2024_tables["barbarian"]["rages"][19] == 6`, `["fighter"]["weapon-mastery"][15] == 6`, `["cleric"]["channel-divinity"][17] == 4`.
- Barbarian under 2014/mixed:
  - L1: `{uses: 2, recharge: "long", details.damageBonus: 2, details.resistances: [b, p, s]}`
  - L9: 4 uses / +3
  - L16: 5 / +4
  - L20: `unlimited: True`, `uses: None`
- Barbarian under 2024: L20 uses 6 (not unlimited); L17 6.
- Rogue: L1 `dice: "1d6"`, L5 `"3d6"`, L20 `"10d6"` under all three rulesets (VERIFY 2024 equals 2014).
- Multiclass Barbarian 3 / Rogue 3: two entries with the right classIds.
- A non-resource class (Wizard 1 before R4) has no entries.
- Exports: YAML carries `classResources`; Markdown and PDF text contain "Ресурси на класа" and "Rage" for a Barbarian 5. `test_every_sheet_and_derived_key_is_exported_or_excluded` stays green.

**Acceptance.** All tests green; the frontend builds; Barbarian 5 shows "Rage: 3 uses, +2 damage..." on ClassPage at 375px without overflow.

**Risks.**
- Old stored resolutions lack the field, so it must stay optional in `types.ts`.
- `resolve()` must not crash when `class_2024_tables` is empty (no official data). Under 2024, fall back to 2014 numbers and add the warning `class-2024-tables-missing` once. Test this with a patched empty catalog.

---

### R2: Fighter and Monk, Extra Attack and the unarmed strike (M). Depends on R1.

**Goal.** Second Wind, Action Surge, Indomitable, Ki/Focus points with the save DC, the Martial Arts die, attacks per action, and a Monk unarmed-strike attack row.

**Files.**
- `engine/class_resources.py`: `_fighter`, `_monk`, plus a shared `attacks_per_action(resolved_classes)`.
- `engine/attacks.py`: `unarmed_strike(modifiers, prof_bonus, martial_arts_die | None)`.
- `resolve.py`: append the unarmed row to `attacks` when the character has Monk level ≥ 1; add `derived["attacksPerAction"]`.
- `export_fields.py`: add `attacksPerAction` to `DERIVED_FIELDS`, and to the "Атаки" block as "Атаки на действие: N".

**Rules to quote in the test docstring.**
- PHB 164 Extra Attack: "If you gain the Extra Attack class feature from more than one class, the features don't add together." So `attacksPerAction` = 1 + max over classes of `extra_attacks` (Fighter 1/2/3 at 5/11/20; Barbarian/Monk/Paladin/Ranger `*-extra-attack` = 1 at 5). VERIFY the Ranger and Bard-Valor/Sword sources by feature id; subclass Extra Attacks (Valor bard 6, Swords bard 6, Bladesinger 6) are optional and listed in the docstring.
- Monk unarmed strike: ability = the better of STR/DEX (Martial Arts). Damage = martial arts die + modifier; without Monk it is 1 + STR, but only add the row for Monks.

**Tests.**
- Fighter 2014/mixed:
  - L1: Second Wind `{uses: 1, recharge: "short-or-long", details.heal: "1d10+1"}`
  - L2: Action Surge 1
  - L17: Action Surge 2, Indomitable 3
- Fighter 2024: L4 Second Wind uses 3, L10 uses 4.
- Monk 5, WIS 16, DEX 16:
  - 2014: Ki 5, DC 14 (8+3+3), Martial Arts d6, unarmed attack +6 for `1d6+3`
  - 2024: Focus 5, Martial Arts d8 (VERIFY the 2024 die table), same DC
- Monk 1: no ki resource (level 2+), Martial Arts d4 (2014) / d6 (2024).
- Fighter 11 → attacksPerAction 3; Fighter 5 / Barbarian 5 → 2 (no stacking); Fighter 20 → 4.
- Speed: R1 timing still under 50 ms.

**Risk.** The unarmed row must not be deduped against an item with index "unarmed-strike". Use id `unarmed-strike` and VERIFY no catalog item has it.

---

### R3: Cleric, Paladin, Druid (M). Depends on R1.

**Goal.** Channel Divinity (Cleric and Paladin, with the multiclass rule), Destroy Undead CR, Lay on Hands pool, Divine Sense (2014), Wild Shape uses and CR limits.

**Rule to quote (PHB 164, Channel Divinity).** "If you already have the Channel Divinity feature and gain a level in a class that also grants the feature, you gain the effect options granted by that class, but getting the feature again doesn't give you an additional use of it." So there is one combined resource `channel-divinity` with uses = max over classes, and `classId` = the class giving the max. VERIFY whether the 2024 PHB multiclass text is the same, and quote whichever applies.

**Tests.**
- Cleric 2014: L2 1 use (short rest), L6 2, L18 3; L5 Destroy Undead CR "1/2". Cleric 2024: L2 2, L6 3, L18 4.
- Paladin 2014: L1 Lay on Hands pool 5, L10 pool 50; Divine Sense uses 1+CHA (CHA 16 → 4); L3 Channel Divinity 1. Paladin 2024: no Divine Sense; L3 Channel Divinity 2, L11 3.
- Cleric 6 / Paladin 3 (2014): exactly one Channel Divinity entry with uses 2.
- Druid 2014: L2 uses 2, max CR "1/4" with no fly/swim; L4 CR "1/2", no fly; L8 CR 1; L20 `unlimited` (Archdruid; VERIFY the SRD feature id `archdruid`). Druid 2024: L2 2, L6 3, L17 4; max CR from the XPHB text (1/4 at 2, 1/2 at 4, 1 at 8 — VERIFY).

---

### R4: Bard, Sorcerer, Wizard, Ranger (2024 favored enemy) (S–M). Depends on R1.

**Tests.**
- Bard, CHA 16: L1 die d6, uses 3, recharge long; L5 d8, recharge short; L10 d10; L15 d12. Same under 2024 (VERIFY Bardic Die column). CHA 8 gives uses 1.
- Sorcerer: L1 no entry; L2 points 2; L20 20 (both rulesets). `details.slotCosts` from `creating_spell_slots` ({1:2, 2:3, 3:5, 4:6, 5:7}).
- Wizard: L1 Arcane Recovery 1, L5 3, L20 10 (recharge "long", once per day after a short rest).
- Ranger 2024: Favored Enemy as `{name: "Favored Enemy (Hunter's Mark)", uses: 2...6, recharge: "long"}`. Ranger 2014 gets no resource (favored enemy is a choice, already modelled).

---

### S4 (prerequisite of R5): feature-text option choices — see Part 3 below. Run it before R5.

### R5: Saves, speed and rage effects folded into derived (M). Depends on R1–R3 and S4; decision D5.

**Goal.** Always-on numbers change `derived` itself.

**Files.**
- `catalog/reference_data.CLASS_FEATURE_EFFECTS` new keys:
  - `aura-of-protection`: `{"save_bonus_ability": "CHA", "min": 1}`
  - `diamond-soul`: `{"save_proficiency": "all"}`
  - `slippery-mind`: `{"save_proficiency": ["WIS"]}`; under 2024, WIS and CHA (VERIFY XPHB Slippery Mind; it is a ruleset override, so put it in `class_resources`/`features` under a ruleset parameter, not in the static table)
  - `fast-movement`: `{"speed_bonus_unless_heavy_armor": 10}`
- `engine/features.py`: `save_bonus(effects, modifiers)`, `save_proficiencies(effects)`, `speed_bonus_unless_heavy(effects, equipped_items)`.
- `resolve.py`:
  - extend `proficient_save_abilities` before `saves = ...` (around line 4282)
  - add the save bonus after `derived_mod.saving_throws`
  - Fast Movement: +10 when no equipped armor has category "Heavy". It stacks with Unarmored Movement only for a Barbarian/Monk multiclass. Both apply per RAW, but Unarmored Movement needs no armor; VERIFY and quote.
- Rage resource `details.resistances`: 2014 Totem Spirit Bear (S4 choice `...bear`) gives every damage type except psychic. Optional: 2024 Path of the Wild Heart is a per-rage choice and is not modelled; disclose.
- Attack notes (D5): when the Barbarian has Rage, STR melee rows get the note "Rage: +N damage"; finesse and ranged rows of a Rogue get "Sneak Attack Xd6".

**Tests.**
- Paladin 6, CHA 16, ruleset 2014: every save is +3 higher than at Paladin 5 with the same scores.
- Paladin 6 with CHA 8: +1 (minimum 1). VERIFY the RAW minimum; the PHB says "minimum of +1".
- Monk 14: all six saves proficient.
- Rogue 15 (2014): WIS proficient; under 2024, WIS and CHA (VERIFY).
- Barbarian 5 in hide armor: speed 40; in a hypothetical heavy armor via `added`: 30.
- Bear totem Barbarian 3 (2014): rage resistances contain "fire" but not "psychic".

**Risk.** Changing saves changes existing expectations in `test_resolve.py` for Paladin 6+ / Monk 14+ drafts. Search with `grep -n "paladin\|monk" server/tests/test_resolve.py` and update those values in the same commit.

---

### R6: Subclass resources (M). Depends on R1. Optional tail items are marked.

**Goal.** Psi Warrior / Soulknife psionic dice (2014 formula, 2024 table), Battle Master superiority dice and maneuver DC, Arcane Archer shots.

**Files.** `class_resources.py`: `_SUBCLASS_BUILDERS` keyed by subclass id (`psi-warrior-tce`, `psi-warrior-xphb`, `soulknife-tce`, `soulknife-xphb`, `battle-master-phb`, `battle-master-xphb`, `arcane-archer-xge`). VERIFY the ids against `catalog.subclasses`; the importer uses `slug(short_name)-source`. The 2014 Psi dice formula goes in a `reference_data` table with a comment.

**Tests.**
- Psi Warrior TCE 3 (PB 2): 4 × d6. L5 (PB 3): 6 × d8. L11 (PB 4): 8 × d10. L17 (PB 6): 12 × d12.
- Psi Warrior XPHB 9: 8 × d8; XPHB 13: 10 × d10 (table).
- Battle Master 3, STR 16: 4 × d8, DC 13; L7: 5 dice; L10: d10; L15: 6; L18: d12.
- Arcane Archer 3: uses 2, recharge short.
- Optional (separate commit, only if time allows): Rune Knight rune uses, Bladesinging uses = PB, Twilight Sanctuary, etc. List what is skipped in the ARCHITECTURE section.

---

### R7: Mystic Arcanum (M). Depends on R1 only for exports; otherwise independent.

**Goal.** Warlock 11/13/15/17 each pick one spell of level 6/7/8/9 from the Warlock list. Same levels in 2024 (VERIFY XPHB Mystic Arcanum levels).

**Files.**
- `resolve.py`: new `_mystic_arcanum_templates(catalog, rc, sources, ruleset, class_choices)`, called in the per-class spell loop next to `_spell_choice_templates`.
  - cid `class:warlock:{11|13|15|17}:mystic-arcanum-{6..9}`, count 1
  - options from `_spell_options(catalog, "warlock", N, sources, ruleset, kept)`, keeping a stored pick offered
  - group tag `spell-level-N`
  - only when `class_specific.mystic_arcanum_level_N` ≥ 1 at the current level (2014). Under 2024 use the fixed level table.
- `sheet.spells` warlock entry gains `mysticArcanum: [{level, id, name}]`.
- Exports: Markdown/PDF spell section line "Мистичен арканум: ...". The key sits inside `sheet.spells`, so no `export_fields` key is needed, but add it to the spells rendering in both `markdown_export.py` and `pdf_export.py` (they mirror each other).
- `frontend/src/pages/ClassPage.tsx`: `isSpellChoice` also matches `:mystic-arcanum-`; `types.ts` updated.
- Level-down pruning comes for free (generic stale-cid pruning). Test it.

**Tests.**
- Warlock 10: no arcanum templates.
- Warlock 11: one template, all options level 6 Warlock spells (count by script).
- Warlock 17: four templates.
- Selecting `true-seeing` (VERIFY the id) at 11 appears in `sheet.spells[...]["mysticArcanum"]`.
- Warlock 17 → 12 with picks at 13/15/17: those three cids are in `pruned`.
- A Warlock 11 multiclassed with a Wizard 5: the arcanum options are still only Warlock spells.

---

### R8: Eldritch Invocation effects (SRD set) (M). Depends on R1 and R5 (effects plumbing); decision D6.

**Goal.** A selected invocation produces real sheet effects.

**Files.**
- `catalog/reference_data.INVOCATION_EFFECTS`, keyed by SRD id (`eldritch-invocation-*`). Effect kinds:
  - `innate_spell {spell, uses: "at-will"|"1/long-rest-slot", level?}`: Armor of Shadows (mage-armor), Ascendant Step (levitate), Beast Speech (speak-with-animals), Eldritch Sight (detect-magic), Fiendish Vigor (false-life), Mask of Many Faces (disguise-self), Misty Visions (silent-image), Otherworldly Leap (jump), Master of Myriad Forms (alter-self), Thief of Five Fates (bane), Mire the Mind (slow), Sign of Ill Omen (bestow-curse), Bewitching Whispers (compulsion), Dreadful Word (confusion), Minions of Chaos (conjure-elemental), Sculptor of Flesh (polymorph), Chains of Carceri (hold-monster), Whispers of the Grave (speak-with-dead), Visions of Distant Realms (arcane-eye). VERIFY each against the SRD feature text and the SRD spell ids.
  - `skills`: Beguiling Influence gives deception and persuasion.
  - `ac_formula 13+DEX` (no armor): Armor of Shadows (D6).
  - `senses {devilsSight: 120}`: Devil's Sight.
  - `resource_bonus`: Agonizing Blast gives `{name: "Agonizing Blast", bonus: CHA mod, details: {spell: "eldritch-blast"}}`.
  - `note`: Thirsting Blade ("Extra Attack with pact weapon") and Repelling Blast. Book of Ancient Secrets: note only (ritual book not modelled).
- `resolve.py`:
  - read the selected ids from the `class:warlock:*:invocations:*` choice after `_gate_invocation_choices`
  - innate entries go through the existing `_innate_entry_to_sheet` shape (ability CHA, source label "Eldritch Invocation")
  - skills join `proficient_skills` before `skill_scores` (be careful with ordering: the invocation choice is resolved inside `choices`, which is available before the skill pass; VERIFY)
  - AC formula joins `features_mod.ac_formulas(effects)`
- Exports already cover innateSpells, senses and skills; `export_fields` needs the "devilsSight" label in `_SENSE_NAMES`.

**Tests.**
- Warlock 2 picking Armor of Shadows + Devil's Sight, DEX 14, no armor: AC 15 (13+2); `senses.devilsSight == 120`; innateSpells contains mage-armor at-will.
- Beguiling Influence: deception and persuasion proficient.
- Agonizing Blast: CHA 16 gives a resource bonus of 3.
- Warlock 9 picking Sign of Ill Omen: an innate bestow-curse "1/long rest".
- Level-down to 4 with Sign of Ill Omen stored: pruned by the existing invocation gate, and the effect is gone.

---

## Part 2: The fuller 2024 class chassis

### Size assessment

The app keeps the 12 SRD (2014) classes as the chassis for every ruleset. Under 2024 these already change:
- subclass unlock at level 3 (O2)
- XPHB cantrip/prepared counts and Paladin/Ranger round-up slots (O3)
- Epic Boon at 19 (A1)
- 2024 subclasses with features (11b)

Everything else in the class block is still 2014:
- feature names and text
- Fighting Style options (SRD subfeatures instead of FS feats)
- Rogue/Bard expertise levels (Bard 2014 3/10 vs 2024 2/9)
- Metamagic counts (2014 2/3/4 at 3/10/17 vs 2024 2/4/6 at 2/10/17)
- invocations (32 SRD vs the XPHB EI list, from 1 at level 1; Pact Boons become invocations)
- level-1 choices that don't exist (Divine Order, Primal Order, Weapon Mastery)
- level-2 choices (Deft Explorer, Scholar)
- level-7 choices (Blessed Strikes, Elemental Fury)
- starting equipment packages and multiclass proficiencies
- the Wizard spellbook, which is absent in both editions

The data exists for all of it:
- 12 XPHB class records with `classTableGroups`, `featProgression` (Fighting Style FS at 1/2/2, Epic Boon at 19), `startingProficiencies`, `startingEquipment`, `multiclassing`, `classFeatures` refs
- 283 XPHB `classFeature` records
- 13 FS-category feats (verified: FS 11 = 10 XPHB + Arcane Warrior AU; Blessed Warrior XPHB `FS:P`; Druidic Warrior XPHB `FS:R`)
- weapon masteries on 40 XPHB base items (verified; 8 masteries: Cleave, Graze, Nick, Push, Sap, Slow, Topple, Vex). 37 SRD weapons need name-mapping (e.g. "Crossbow, light" ↔ "Light Crossbow").

A full parallel `<class>-xphb` record set (C10) would touch every class code path: `_cumulative_feature_refs`, `class_level_row`, proficiency grants, starting equipment, multiclass prerequisites, `spells_mod`, every ClassPage fetch, and the class-id keys in stored drafts. It doubles the test matrix. That makes it XL, 8–12 slices, and it is not recommended.

The staged overlay below keeps the SRD chassis and swaps in 2024 behavior under `ruleset == "2024"` only, one mechanic at a time.

### Stages

| Stage | Size | Value | Status |
|---|---|---|---|
| C1 XPHB class data import (records, features, masteries on items) | S | foundation | **required** |
| C2 Weapon Mastery choice + attack-row mastery | M | high (every 2024 martial) | **required** |
| C3 2024 Fighting Style = FS feat choice (+ FS feats at ASI, U3) | M | high | **required** |
| C4 Wizard spellbook (both rulesets, D7) | M | high | **required** |
| C5 2024 feature list overlay in `sheet.features` and exports | M | medium (correct names/text) | optional, recommended |
| C6a Divine Order / Primal Order (level 1 choices with effects) | M | medium | optional |
| C6b Expertise level remap + Deft Explorer + Scholar | M | medium | optional |
| C6c Metamagic 2024 counts/options, Blessed Strikes / Elemental Fury | S–M | low | optional |
| C7 2024 Eldritch Invocations (XPHB EI list, counts from table, Pact Boon as invocations, effects table for XPHB ids) | L | medium | optional |
| C9 2024 starting equipment / starting & multiclass proficiencies | M | low–medium | optional |
| C10 full parallel `*-xphb` class records | XL | — | **not recommended** |

### C1: XPHB class data import (S). No behavior change.

**Files.**
- `catalog/official/subclasses.py`, new `load_class_2024_records(class_dir)`. Returns `{cls: {"feat_progression": [{category:[..], progression:{lvl:n}}], "features": [{"name","level","ref"}], "starting_proficiencies": raw, "multiclassing": raw, "starting_equipment": raw}}`.
- Converter `convert_class_features_2024(raw_class_features)` gives `catalog.features` entries `xphb-<class>-<lvl>-<slug(name)>` with `{index, name, level, class, desc (via _flatten_entries), source "XPHB", ruleset "2024"}`.
  - Skip the "Subclass Feature", "<Class> Subclass", "Ability Score Improvement" and "Epic Boon" placeholder rows; VERIFY their names by script.
  - Add `catalog.class_2024_level_features[cls][lvl] = [ids]`.
- `catalog/official/items.py` (or the loader merge): add `item["mastery"] = "<Name>"` for weapons whose normalized name matches an XPHB base item with `mastery`. Normalization: lowercase; reorder "crossbow, light" to "light crossbow"; VERIFY all 37 SRD weapons plus the 5 imported ones map (Net has none). Add `catalog.weapon_masteries = {name: desc}` from `itemMastery`.
- `loader.py`: attach all of the above.

**Tests** (`test_class_2024_chassis.py`):
- `len(class_2024_records) == 12`
- fighter `feat_progression` contains FS at 1 and EB at 19
- the count of imported XPHB class features (VERIFY by script; it is the 283 raw records minus placeholders)
- `catalog.items["longsword"]["mastery"] == "Sap"`, `["crossbow-light"]["mastery"] == "Slow"` (VERIFY)
- every SRD weapon except net has a mastery
- `weapon_masteries` has 8 keys
- the SRD-only catalog (no official data) still loads

**Risk.** Feature id collisions with the SRD `features` dict. Assert there are none in the test.

### C2: Weapon Mastery (M). Depends on C1; decision D9.

**Rule (XPHB, verify and quote).** Barbarian, Fighter, Paladin, Ranger and Rogue each have a "Weapon Mastery" feature: choose N kinds of weapons you are proficient with (Barbarian: simple or martial melee; Rogue: simple, or martial with Finesse or Light). You can change one choice after a long rest (not modelled). N comes from the table: Barbarian/Fighter columns; Paladin, Ranger and Rogue have 2 fixed (VERIFY in the XPHB feature text).

**Files.**
- `resolve.py` new `_weapon_mastery_template(catalog, rc, ruleset, proficient_weapons)`, only for `ruleset == "2024"` and the five classes, for every class in the character (VERIFY that the 2024 multiclass rule grants the feature).
  - cid `class:<cls>:weapon-mastery`, `count_by_level: True` so a level-down prunes
  - options = weapon item ids with a mastery, label "Longsword (Sap)"
  - weapons the character isn't proficient with, or outside the class filter, are disabled with a reason. That needs the proficiency set, which is computed later in `resolve()`. Either build the template late and splice it into `choices` (as the equipment dependents are spliced), or compute the class weapon proficiencies early. Pick one and document it.
- `sheet.weaponMasteries: [{itemId, name, mastery}]`; `derived.attacks[i].mastery` = the mastery name when that weapon is mastered.
- Add to `export_fields` (SHEET_TAIL_FIELDS plus an extra block "Майсторство с оръжия"), `types.ts`, and the "Атаки" bullet suffix.
- The ClassPage features tab shows it automatically (cid prefix `class:<cls>:`).

**Tests.**
- Fighter 1, 2024: card count 3, Longsword enabled. Fighter 4: count 4. Fighter 10: 5. Fighter 16: 6.
- Barbarian 1: Longbow disabled ("melee weapons only"). Rogue 1: Greatsword disabled, Rapier enabled.
- Wizard 1 / Fighter 1 under 2014 or mixed: no card.
- Fighter 4 → 1 with 4 stored: pruned "now allows 3".
- Selected Longsword plus an equipped longsword: the attack row has `mastery == "Sap"`.
- Fighter 1 / Rogue 1 (2024): two cards.

### C3: 2024 Fighting Style feats (M). Depends on C1. Resolves U3.

**Files.**
- `resolve._feature_choice_templates`: under ruleset 2024, when the feature index is in `{"fighter-fighting-style", "paladin-fighting-style", "ranger-fighting-style"}`, build a feat choice instead of the SRD subfeature options.
  - Paladin offers FS + FS:P; Ranger FS + FS:R; Fighter FS.
  - cid `class:<cls>:<lvl>:fighting-style`, options `feat:<index>` via `_feat_options`, prerequisite and duplicate states as for ASI feats.
  - A stored SRD subfeature pick under 2024 lands in `pruned`, and vice versa (generic, because the cid differs).
  - Champion's `additional-fighting-style` (2014 SRD) is also replaced under 2024 only if the XPHB Champion has an "Additional Fighting Style" feature (VERIFY: XPHB Champion level 7).
- The resolved pick becomes a feat with origin `class:<cls>:<lvl>:fighting-style:feat:<index>`, tagged like `_asi_origin` so `_feat_cid_prefix`, `_feat_instance_key` and `sheet.feats` (origin `"fighting-style"`; extend `feats_summary`) work.
- `reference_data.CLASS_FEATURE_EFFECTS`: add `archery-xphb`, `defense-xphb`, `dueling-xphb`, `great-weapon-fighting-xphb`, `two-weapon-fighting-xphb`, and `thrown-weapon-fighting-xphb` (`damage_bonus.thrown: 2`, a new key in `attack_styles`). `_class_feature_list` must also yield these feat ids, e.g. by appending resolved fighting-style feat indices.
- ASI pools: `_is_asi_eligible_feat` admits `FS`, `FS:P`, `FS:R` under 2024/mixed when the class has a Fighting Style feature. Expected prerequisite data: `{"other": "Fighting Style Feature"}` or similar (VERIFY). Add a `fighting_style` flag to `_HeldFeatState`. Update the A1 rule table in the ARCHITECTURE doc.
- **Note for the user:** this changes the verified A1 pool sizes under 2024/mixed for Fighter/Paladin/Ranger. Recompute by script and update `test_asi_feat_eligibility.py`.

**Tests.**
- Fighter 1 (2024): card `class:fighter:1:fighting-style` has 11 feat options (10 XPHB FS + Arcane Warrior AU under no sources; VERIFY whether AU is offered under 2024: U1 says AU is a 2014 pool, so expect 10 under 2024).
- Pick Defense in chain mail: AC 17.
- Paladin 2 (2024): Blessed Warrior offered; Ranger 2 (2024): Druidic Warrior offered.
- Fighter 1 (2014): the old SRD subfeature card is unchanged.
- Fighter 4 (2024) ASI card includes `feat:archery-xphb` with the right state; Wizard 4 (2024) does not.

### C4: Wizard spellbook (M). Decision D7.

**Rule (PHB 114 / XPHB, quote).** At level 1 a spellbook holds six level-1 Wizard spells. Each Wizard level adds two spells of a level you have slots for. Prepared spells come from the spellbook.

**Files.**
- `resolve._spell_choice_templates`, for `cls_id == "wizard"` (both rulesets):
  - New template `class:wizard:spellbook`: count = 6 + 2 × (level − 1), options = Wizard spells up to the highest slot level (same visibility and kept rules), `count_by_level` count-variable so a level-down prunes. Mark it count-variable in `_is_count_variable_choice`.
  - The `spells-known` (prepared) template's options become the stored spellbook selection (read `class_choices["class:wizard:spellbook"]`, as `_kept` does). With an empty spellbook, the prepared card has zero options and a description "Choose spells for your spellbook first."
- Stale prepared picks outside the book go to `pruned` (the existing count-variable path truncates invalid options; VERIFY that it handles "option not present").
- Multiclass: only the Wizard class gets a spellbook.
- Frontend: `isSpellChoice` also matches `:spellbook`. Check the order: spellbook card first.
- Exports: `sheet.spells[wizard].spellbook: [ids]` plus a Markdown/PDF line "Книга със заклинания".

**Tests.**
- Wizard 1: spellbook count 6, all options level 1; prepared options == the stored book.
- Wizard 5: count 14, options up to level 3.
- Prepared pick not in the book: pruned.
- Wizard 5 → 3 with 14 in the book: pruned "now allows 10".
- 2024 Wizard 1: prepared count from the XPHB table (4), options = book.

### C5–C9 (optional; build only after D8)

- **C5 feature list overlay.** Under 2024, `sheet_features.build_features` and ClassPage's class-feature listing use `class_2024_level_features` names/levels instead of the SRD refs. SRD choice-bearing features keep their choices attached through a small SRD→XPHB name map (Fighting Style, Expertise, Metamagic, Eldritch Invocations, Pact Boon → none). Tests: Fighter 2 (2024) features include "Tactical Mind"; Fighter 2 (2014) does not. Exports follow automatically.
- **C6a Divine/Primal Order.** cids `class:cleric:1:divine-order`, `class:druid:1:primal-order`, options from the XPHB feature text, hardcoded in `reference_data` with a comment.
  - Protector: martial weapons + heavy armor proficiency.
  - Thaumaturge: +1 cantrip (count bump on the cantrip template) + WIS modifier (min 1) bonus to Arcana/Religion (a derived skills bonus).
  - Magician: +1 cantrip + WIS bonus to Arcana/Nature.
  - Warden: martial weapons + medium armor.
- **C6b.** Under 2024, the Bard expertise SRD features at 3/10 move to 2/9 (remap the expertise template level), Rogue stays at 1/6, Ranger Deft Explorer at 2 (1 expertise + 2 languages), Wizard Scholar at 2 (1 expertise from 6 skills).
- **C6c.** Metamagic 2024 counts (2/4/6 at 2/10/17) and the XPHB MM option list; Blessed Strikes / Potent Spellcasting (Cleric 7), Elemental Fury (Druid 7) choices.
- **C7 2024 Invocations.** The XPHB EI optional features (featureType EI, source XPHB), counts from `class_2024_tables["warlock"]["invocations"]`, prerequisites parsed from `prerequisite` (level / spell / pact). Pact of the Blade/Chain/Tome are invocations, so the SRD `pact-boon` template is suppressed under 2024. The R8 effects table is extended with XPHB ids.
- **C9.** Under 2024, the primary class's level-1 skill choice / equipment uses the XPHB `startingProficiencies` / `startingEquipment` (A/B/C packages incl. gold, reusing `build_equipment_choice`); a secondary class uses XPHB `multiclassing.proficienciesGained`.
- **C10.** Not recommended (see the size assessment).

---

## Part 3: Small gaps (S slices)

### S1: Spell slots in the frontend (S, frontend only)

**Files.** `frontend/src/pages/ClassPage.tsx`, `frontend/src/pages/ExportPage.tsx`.
- ClassPage spells tab: above the cards, a plain `<p>` "Клетки за заклинания: ниво 1 ×4, ниво 2 ×3" from `resolution.derived.spellSlots`. If this class is a Warlock and `warlockSpellSlots` is non-empty, also "Магия на договора: N × ниво M".
- The shared pool shows on every caster's tab, with the note "(общи за всички класове)" when more than one class grants slots. Count those from `sheet.spells` entries; VERIFY the shape.
- ExportPage: the same two lines.
- Third casters (Eldritch Knight / Arcane Trickster) already feed `derived.spellSlots`.

**Acceptance.** `npm run build` passes. Browser check at 375px:
- Wizard 5 shows ×4/×3/×2
- Warlock 5 shows "2 × ниво 3"
- Eldritch Knight 3 shows "ниво 1 ×2"
- Wizard 3 / Warlock 2 shows both lines
- no overflow

No server tests change.

### S2: Cross-edition same-name feat duplicates (S–M). Decision D4.

**Files.** `resolve.py`:
- New `_feat_name_key(feat)`: lowercased name, trailing " (...)" stripped.
- Add name keys to the "already taken" sets in:
  - `_asi_choice_templates` (around 2712)
  - the ASI-walk duplicate detection (around 3480)
  - `_species_feat_choice_template` / `_resolve_species_selected_feats` (around 2041–2100)
  - `_resolve_granted_feats` / the background path, if it de-dups
- Exempt the pick when the feat being picked is `repeatable`.
- Disabled reason "already taken (Alert, XPHB)". Problem id stays `feat-duplicate-<index>-<cid>`.

**Tests** (`test_feat_cross_edition_duplicates.py`, needs_official):
- Background with an XPHB Alert grant (Guard/XPHB or Criminal/XPHB; VERIFY by script) + Fighter 4 under mixed: `feat:alert-phb` is disabled "already taken".
- A stored `feat:alert-phb` gives a feat-duplicate problem and no second Alert in `sheet.feats`.
- `magic-initiate-xphb` (repeatable) next to `magic-initiate-phb`: VERIFY the expected outcome. Rule: picking a repeatable feat is allowed; picking the non-repeatable PHB one after the XPHB one is blocked. Document whichever the user picks in D4.
- Under 2014 and 2024 nothing changes (each pool contains only one edition; assert the A1 counts are unchanged).
- Remove "U5/U7 not implemented" from ARCHITECTURE.

### S3: Four Elements required attunement (S)

**Data (verified).** Raw Way of the Four Elements PHB has `optionalfeatureProgression[0].required = {"3": ["Elemental Attunement|PHB"]}`, progression {3:2, 6:3, 11:4, 17:5}. The option Elemental Attunement PHB has featureType ED.

**Files.**
- `catalog/official/subclasses.py` `convert_subclasses`: carry `required` into `optional_progression.required = {lvl: [opt ids]}`, mapping "Name|SRC" to `opt-<slug>-<src>` (the same id rule as `convert_optional_features`).
- `resolve._optional_progression_template`:
  - required ids at reached levels are removed from `options`
  - `count` decreases by their number
  - the template gets `granted: [{id, label}]` (the description appends "Elemental Attunement is granted automatically.")
  - a stored selection containing a required id is silently filtered before resolution (no `pruned` entry, since it is not a loss)
- `_class_feature_list` and `sheet_features.build_features` include the granted option (choice labels list it first).

**Tests.**
- Four Elements 3: count 1, `opt-elemental-attunement-phb` not among the options; the feature's sheet `choice` contains "Elemental Attunement" plus the pick.
- Level 6: count 2.
- Old draft with [attunement, fangs] at 3: the selection resolves to [fangs], no over-selected problem, no pruned entry.
- Battle Master and others are unchanged (no `required`).

### S4: Feature-text option choices (Totem Spirit and others) (M). Decision D10. Run before R5.

**Data (verified scan).** 27 subclass features contain `"type":"options"` blocks. Most are already handled (optional-feature refs: maneuvers, arcane shots, runes, disciplines, metamagic) or grant every option (Psionic Power, Soul Blades, Telekinetic Adept, Genie's Vessel, Tipsy Sway) or are per-rest choices (The Third Eye, Master Transmuter). Hunter PHB is `srd: true`, so the SRD record with `subfeature_options` is used and the import drops it.

**Allowlist (build-time choices).** `reference_data.FEATURE_TEXT_CHOICES`, keyed by imported feature id. VERIFY the ids by script:
- `totem-warrior-phb-3-totem-spirit`
- `totem-warrior-phb-6-aspect-of-the-beast`
- `totem-warrior-phb-14-totemic-attunement`
- `storm-herald-xge-3-storm-aura`, count 1

Storm Soul and Raging Storm follow the Storm Aura environment, so they get no separate choice. Record that as derived text only.

**Files.**
- Converter `prepare()`: when the feature id is in the allowlist (or for every top-level `options` block, with the allowlist applied in resolve; choose the converter side for simplicity), emit `feature_specific.text_options = {"count": entry.get("count", 1), "options": [{"id": f"{fid}--{slug(child name)}", "name", "desc"}]}` while still inlining the text into `desc`.
- `resolve._feature_choice_templates`: new branch `elif specific.get("text_options")`, cid `class:<cls>:<lvl>:feature:<featureId>` (matches `sheet_features._CLASS_CHOICE_ID` and `_class_feature_list`).
- Option ids such as `totem-warrior-phb-3-totem-spirit--bear` are what R5 keys the Bear resistance off.

**Tests.**
- Totem Warrior 3: card with 3 options (Bear, Eagle, Wolf; VERIFY: PHB has 3 at level 3, SCAG adds Elk/Tiger in a separate entry); pick Bear and `sheet.features` "Totem Spirit" has choice ["Bear"].
- Totem Warrior 6 and 14 cards exist.
- Storm Herald 3: Desert/Sea/Tundra.
- Third Eye (Divination 10): no card.
- Level-down 6 → 3: Aspect pick pruned (generic).

### S5: Dueling one-hand check (S). Decision D3.

**Default (b).**
- `engine/attacks.weapon_attack`: when Dueling applies (one-handed melee, not two-handed), `damage` stays without the Dueling bonus and a new `duelingDamage` field = dice + mod + 2. The note stays "Dueling: only with no other weapon".
- Add `duelingDamage` to the `Attack` type, to the Markdown/PDF "Атаки" bullet ("с Дуел ..."), and to the ExportPage list.
- Update the module docstring's "Out of scope".

**Tests** (`test_engine_attacks.py`): Fighter with Dueling and a longsword → `damage "1d8+3"`, `duelingDamage "1d8+5"`; versatile damage unaffected; greatsword → no `duelingDamage`; ranged → none.

**If D3 = (a):** count the distinct equipped weapons (excluding the one being rated and shields); no bonus when > 0. **If D3 = (c):** add `equipment.wielded` to `Draft`, `normalize.py`, a reducer action, and an EquipmentPage select (functional), and apply Dueling only when main is one-handed melee and off is empty or a shield; budget M.

**Update 2026-10-10:** option (c) was added on top of (b) as G2 (`equipment.worn` / `wielded`, see ARCHITECTURE "G2"); without `wielded` the (b) behavior above still holds.

**Risk.** Existing tests assert `damage` includes Dueling (Slice 9). Update them in the same commit and say so in the commit message.

### S6: PDF / Markdown / YAML field-level export check (S). After all R/C slices that add fields.

**Goal.** Every new field reaches all three exports with readable text; no visual changes.

**Files.**
- `server/tests/test_export_fields.py`: a parametrized "kitchen-sink" set of real drafts:
  - Barbarian 20 (2014 & 2024)
  - Monk 14
  - Paladin 6 / Cleric 6
  - Warlock 17 with arcanum and invocations
  - Fighter 10 (2024) with weapon masteries and an FS feat
  - Wizard 5 with a spellbook
  - Psi Warrior 11
  - Totem Warrior 6 Bear
- For each: (1) YAML has every `sheet`/`derived` key (the existing invariant); (2) for every non-empty `classResources` entry, its `name` appears in both the Markdown and PDF text (`pypdf` `_extract_text`, as in `test_pdf_export.py`); (3) the same for `weaponMasteries` names, `mysticArcanum` spell names, the `spellbook` heading, `attacksPerAction`, `duelingDamage`, `senses.devilsSight` label; (4) `to_pdf` raises nothing and no glyph is missing. Assert the extracted text contains no "?" substitutions for the Bulgarian headings, and that characters like "×" render or are avoided (fpdf2 with DejaVu supports them; VERIFY).
- `test_markdown_and_pdf_share_the_same_blocks` must stay green.

**Acceptance.** All kitchen-sink drafts export through `/api/export/<fmt>` with status 200 (one `test_app.py` case, mirroring `test_all_export_formats_carry_features_through_the_api`).

---

## Global execution order (test gate after each)

0. **Decision gate:** ask D1–D11 in one message; record the answers at the top of the plan file.
1. **S1** spell slots in the frontend
2. **S2** cross-edition duplicate feats
3. **S3** Four Elements attunement
4. **S4** feature-text options (Totem Spirit...)
5. **S5** Dueling (per D3)
6. **R1** resource framework + Barbarian/Rogue
7. **R2** Fighter/Monk + Extra Attack + unarmed strike
8. **R3** Cleric/Paladin/Druid (Channel Divinity multiclass rule)
9. **R4** Bard/Sorcerer/Wizard/Ranger 2024
10. **R5** saves/speed/rage effects (needs S4 for Bear)
11. **R6** subclass resources (Psi Warrior/Soulknife/Battle Master/Arcane Archer)
12. **R7** Mystic Arcanum
13. **R8** invocation effects
14. **C1** XPHB class data import
15. **C2** Weapon Mastery
16. **C3** 2024 Fighting Style feats (+ FS at ASI; recompute A1 counts)
17. **C4** Wizard spellbook
18. **Optional per D8:** C5 → C6a → C6b → C6c → C7 → C9
19. **S6** export field-level sweep (kitchen sink)
20. **F, final:**
    - Consolidate the per-slice sections into `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md`:
      - add a "Class resources (R)" section
      - add "2024 chassis (C)" with the stage table and which were skipped
      - update "What's implemented vs. not"
      - update the Slice 9 "Out of scope" (Dueling, Weapon Mastery, Monk unarmed)
      - update the 11b "disclosed skips" (Psi dice, feature-text options, EK/AT now done)
      - update U3/U5/U7 in PART 1
      - update the test counts
      - remove the "Wizard spellbook: NOT implemented" line
    - Diff `types.ts` against a real `/api/resolve` JSON of a kitchen-sink draft (`Derived`/`Sheet` keys) to catch drift.
    - Run a whole-branch review (ARCHITECTURE "Process notes": per-slice reviews miss cross-slice interactions). Cross-slice interactions to check:
      - S4 × R5 (Bear)
      - C3 × S2 (FS feat duplicates)
      - C3 × A1 pools
      - R8 × R5 AC formulas (Armor of Shadows vs Unarmored Defense: best one wins, never stacked)
      - C4 × the count-variable pruning cap
    - Re-time `resolve()` for the four reference characters.

## Cross-cutting risks

- **`resolve.py` is 4440 lines.** Keep new logic in `engine/class_resources.py` (pure) and small helpers. `resolve()` only wires.
- **Hand-maintained `types.ts`:** every slice that adds a field adds an optional TS field in the same commit.
- **Default ruleset is "mixed"**, so 2024-only behavior (C2, C3, 2024 resource numbers) never appears unless a test sets `ruleset: "2024"`. Each slice needs at least one test per ruleset where the behavior differs.
- **Missing official data:** every slice must degrade to SRD behavior, with no crash, when `class_2024_tables`/`class_2024_records` are empty. Test one case with an SRD-only catalog (pattern: existing tests that build a catalog copy).

### Critical files for implementation
- /Users/yoanpetrov/dnd-character-creator/server/engine/resolve.py (`_effective_caster` ~2850, `_spell_choice_templates` ~2893, `_feature_choice_templates` ~1495, `_optional_progression_template` ~1467, `_class_feature_list` ~3114, `derived` assembly ~4283–4332, `sheet` ~4384)
- /Users/yoanpetrov/dnd-character-creator/server/engine/class_resources.py (new) and /Users/yoanpetrov/dnd-character-creator/server/engine/features.py, /Users/yoanpetrov/dnd-character-creator/server/engine/attacks.py
- /Users/yoanpetrov/dnd-character-creator/server/catalog/official/subclasses.py (`load_class_2024_progressions`, `convert_subclasses.prepare`, new `load_class_2024_tables` / `load_class_2024_records`) and /Users/yoanpetrov/dnd-character-creator/server/catalog/loader.py
- /Users/yoanpetrov/dnd-character-creator/server/catalog/reference_data.py (`CLASS_FEATURE_EFFECTS`, new `INVOCATION_EFFECTS`, `FEATURE_TEXT_CHOICES`, Psi/Battle Master tables)
- /Users/yoanpetrov/dnd-character-creator/server/export_fields.py (plus `markdown_export.py` / `pdf_export.py` spell sections), /Users/yoanpetrov/dnd-character-creator/frontend/src/types.ts, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ClassPage.tsx, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ExportPage.tsx