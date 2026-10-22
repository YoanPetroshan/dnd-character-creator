# Plan: the remaining program (RP), covering open questions 13-16 and 21, notes-only features, E11, E12, E13, the 2024 packs and final consolidation

Opus planner, 2026-10-22. Suggested file: `docs/superpowers/plans/2026-10-22-remaining-program.md`.

I only read code and data and changed nothing. My checks ran as stdin scripts (`.venv/bin/python -`), not as scratch files. Numbers marked **verified** come from those runs against the real catalog. **VERIFY** means the executor re-checks by script before writing the test. If a script and this plan disagree, the script wins and the deviation goes into the slice's ARCHITECTURE section.

---

## Decisions (user, 2026-10-22)

User: "execute them all, choose what is most suitable, build a clear plan and execute". Approved: D1 = yes (keep the FE edition policy for A1/A2/A5); D2 = gate 2024 only; D3 = yes, RP21 renumbering is IN; D4 = YES for Extras 1-4 (SRD Lore Bard Bonus Proficiencies + Additional Magical Secrets, SRD pack weights, SRD bundle quantities, extra gaming-set items) as slices RPX1-RPX4 placed right after RP16 and using the P0 `--rebaseline` policy; Extra 5 (TCE fighting styles for Fighting Initiate under mixed) = NO (DM-permission rule). Decided here too: Martial Adept d6 stays a separate resource; Monk keeps better of STR/DEX for unarmed with Unarmed Fighting/Tavern Brawler; Weapon Master PHB keeps musket/pistol; one-rest choices stay notes. Executors do not re-ask.

## 0. Conventions

Everything in the Conventions blocks of `2026-10-10-2024-chassis-remaining-stages.md` and `2026-10-11-feat-effects.md` still applies.

### Working rules
- **TDD.** Write the tests first. The test docstring holds a rule matrix that quotes the governing sentence, read from `catalog.features[...]["desc"]` or `catalog.feats[...]["entries"]`. Every data table entry gets a "quote matches catalog text" pin test (the R9 / FE10 pattern).
- **Test gate after every slice.**
  - Server: `cd server && ../.venv/bin/python -m pytest -q`. Baseline 3984 passed.
  - Root: `.venv/bin/python -m pytest -q`. Baseline 405 passed, 8 skipped.
  - Frontend: `cd frontend && npm run build` whenever `frontend/` is touched.
  - On this machine a full run can take more than 400 s, so use `run_in_background`.
  - Record the new totals in the slice's ARCHITECTURE section.
- **Executors.** One at a time (Sonnet), each slice reviewed independently. Run a read-only Opus whole-branch review after RP7, RP14, RP18 and RP22.
- **Commits.** One commit per slice, e.g. `feat(2024): ... (RP9 / E12)`. Stage explicit paths only. Never stage `Resurses/`.
- **Speed.** `resolve()` must stay under 50 ms. Time Fighter 20, Wizard 20 and Bard 20 (mixed and 2024), plus the slice's own reference characters.
- **Degrade.** Every new card or effect is absent with an SRD-only or empty catalog. Each slice has one patched-catalog test.
- **Frontend.** Plain markup, no CSS. Check at 375 px that `scrollWidth === 375`. Every new sheet / derived / option key goes into `types.ts` and `export_fields.py` in the same commit, and `test_types_drift.py` stays green with an empty `UNTYPED_ALLOWLIST`.
- **Count-variable and unavailable.** Every new pick card whose valid set follows level, book or other picks gets added to `_is_count_variable_choice`, so a stale pick becomes a non-blocking `pruned` entry. It also gets added to the `mark_unavailable` card set.
  - `is_new_2024_class_card` matches only `feature:xphb-*`. Subclass feature cids (`feature:<sub>-xphb-...`) must be added.
  - For the E11 cards under mixed / 2014, `mark_unavailable` must also run outside 2024, but only for those card ids.
- **Card id convention.**
  - Subclass cards: `class:<cls>:<lvl>:feature:<feature id>`, option ids `<featureId>--<slug(name)>` (S4 convention). They attach to the sheet row through `sheet_features._CLASS_CHOICE_ID` with no extra work.
  - Feat cards use the feat cid prefix.
  - Spell-pick cards also need `ClassPage.isSpellChoiceId`.

### Ruleset policy (where mixed / 2014 may change)

| Kind of slice | Gate | Golden |
|---|---|---|
| 2024 class / subclass / background / pack work (B, C, D, F, X1, A3, A4) | `ruleset == "2024"` only | green, never regenerated |
| Feat-effect completions (A1, A2, A5) | Standing FE edition policy: the feat's own text under every ruleset in which the character holds it (user-approved for the FE series) | green without regeneration (VERIFY by script: the 3 golden feat cases hold none of the affected feats) |
| E11 (2014 fidelity) | mixed and 2014 | changes, through the `--rebaseline` policy in section 1 |

Why the subclass gate costs nothing (verified): only 3 of the 48 XPHB subclasses are visible under mixed, because they have no 2014 twin: World Tree, Dance, Sea. None of them has an E13 choice. The other 45 show under mixed only as a stored, hidden pick.

---

## 1. Golden policy for mixed / 2014-changing slices (P0, built before the first E11 slice)

New mode in `server/tests/test_c_series_golden.py`: `--rebaseline <SLICE>` (plus `--dry-run`).

**Spec.** A module constant `REBASELINES: dict[str, dict]`, append-only. Each entry:
- `cases`: fnmatch patterns over case names;
- `paths`: regexes over normalized JSON paths, e.g. `^result\.choices\[class:monk:1:prof-choice-1\]`;
- `why`: one line.

**Algorithm.**
1. Load the old golden.
2. For every case NOT matching `cases`: assert that the stored draft re-resolves to the stored result (as the test does). It is written back byte for byte.
3. For matching cases: `ks.fill(deepcopy(stored draft))` fills only cards that are now `pending`; existing picks are untouched. Then re-resolve.
4. Normalize both sides. Lists of dicts that each carry a unique `id` (choices, options, classResources, attacks, features) become dicts keyed by id, so an inserted card does not shift every index.
5. Diff `{draft, result}` old against new into dotted paths.
6. Every changed path must match a `paths` regex, or the run fails.
7. A matching case with no diff prints a warning: the pattern is too wide.
8. Print a summary: changed cases, and count per path regex.

**`--dry-run`** prints the diff without writing. The executor uses it first.
- The `paths` allowlist is written from the slice's rule matrix, not copied from the dry-run output.
- The reviewer compares the two.

**Write and log.**
- The run writes the gz and prints the summary. The summary goes verbatim into the slice's ARCHITECTURE section.
- The commit holds code, tests and gz together, and its message names the rebaseline (`golden: rebaseline E11c (18 cases, paths: ...)`).
- Rebaselines never delete cases.
- New cases come only through `--append`, whose existing assertion stays.
- New non-2024 kitchen-sink drafts automatically become new case names, so `test_golden_file_present_and_covers_every_case` fails until `--append` runs.

**P0 tests.** A synthetic two-case golden in `tmp_path`, written through a module-level path override:
- an unexpected path fails;
- an expected path passes;
- an unmatched case changing fails;
- a dry run writes nothing;
- the normalization puts an inserted card at a keyed path.

Size S, tests only. `STRIP` stays `("derived.featResources",)`.

---

## 2. Verified facts (anchors for the slices)

### Bugs found while planning (2024 only, cheap, put in the order)
1. **2024 background increases are not capped at 20.** Human (XPHB) / Soldier (XPHB), base STR 20 with `str-2+dex-1` gives STR 22. PHB 2024 ch. 2 / ch. 4 (lines 2215, 3147 of the user's markdown): "None of these increases can raise a score above 20." → X1.
2. **Monk 20 Body and Mind is not applied under 2024.** A 2024 Monk 20 keeps DEX 14 / WIS 14; it needs +4 each, max 25. `CLASS_FEATURE_EFFECTS` has no `xphb-monk-20-body-and-mind`.
3. **Primal Champion under 2024 uses the SRD effect** (`ability_cap: 24`). The XPHB text says "to a maximum of 25".
4. **Draconic Resilience (XPHB) is unmapped.** A 2024 Draconic (XPHB) Sorcerer 6 has HP 38 and AC 12; the SRD subclass gives 44 / 15. The XPHB formula is 10 + DEX + CHA, not the SRD 13 + DEX.
5. **Many XPHB subclass fixed effects are unmapped:**
   - Dance Unarmored Defense (10 + DEX + CHA);
   - Shadow and Gloom Stalker Darkvision 60 / +60;
   - Thief climb speed;
   - Sea Aquatic Affinity swim speed;
   - War Avatar of Battle B/P/S resistance;
   - psychic resistance from Psi Warrior 10, Aberrant 6 and Great Old One 10;
   - Celestial 6 radiant resistance;
   - Glory 7 speed +10;
   - Mercy Insight / Medicine / Herbalism Kit.
6. **XPHB subclass resource tail: 45 features** with "a number of times equal to your X modifier (minimum of once)" or "can't use it again until you finish a ... Rest" text are not resources; only R6 Psionic Dice and Superiority Dice exist.

### Data shapes
- **SRD Monk tool choice.** `classes.monk.proficiency_choices[1]` is the only nested `option_type: "choice"` in any catalog proficiency envelope (all other nested choices are equipment). That is why no card appears under mixed / 2014. Under 2024 the same cid `class:monk:1:prof-choice-1` has 27 options (C9a).
- **Arcane Adept.** Raw `feats.json` has `additionalSpells[0].prepared` with keys `s1`..`s5` for the 8 Arcane Adept feats (AU). `_feat_spells_from_5etools` skips `sN` keys, so the tables ARE data and are dropped today.
- **Spells of the Mark.** The 12 Mark feats (EFA) have `expanded` `s1`..`s5`, also skipped (today a note).
- **Cult of the Dragon Initiate (FRHoF, ruleset 2024).** `languages: [draconic]`, `language_options: None`.
- **Greater dragonmarks.** All 12 Greater Marks plus Greater Aberrant Mark already carry `modifies`.
  - Not modelled: Greater Mark of Healing changes the base Healing Touch Cure Wounds (an innate entry with `uses "1/day"`) to Proficiency Bonus uses per Long Rest. Today the base innate "1/day" AND the Greater resource "Improved Healing (Cure Wounds)" (pb) both show, which double counts.
  - Not modelled: Greater Mark of Making / Shadow say "cast the spell as its level 3 version" (Magic Weapon / Invisibility innate entries).
- **Other feats that read another feat's choice** (scan of all 305 feats): Adept of the Black / Red / White Robes (DSotDQ), Outlands Envoy (SATO), Warlike Familiar (AU) and Magic Connoisseur (AU) use "the spellcasting ability chosen for" Initiate of High Sorcery / Scion of the Outer Planes / Familiar Friend / Magic Initiate. Today each has its own ability card.
  - Dragonscarred refers to Cult of the Dragon Initiate's Dragon's Terror (note only, no number).
- **XPHB invocation prerequisites.** Agonizing Blast, Eldritch Spear and Repelling Blast have `prerequisite_2024 = {level 2, cantrip damage|attack}`; Lessons of the First Ones is level 2. The Pacts have no prerequisite.
  - Eldritch Adept (TCE) offers the 32 SRD invocations under every ruleset.
  - SRD Agonizing Blast already names `eldritch-blast`, so open question 15 only exists if the 2024 pool is used.
  - PHB 2024 line 68: "the versions of things in this book replace versions from older books". This settles that under ruleset 2024 the TCE / PHB option-pick feats draw from the 2024 class lists.
- **XPHB background equipment placeholders.** 26 backgrounds with ruleset 2024 (9 XPHB, 17 ABH / FRHoF / EFA / RHW) carry 13 distinct placeholder ids:
  - `unlisted-holy-symbol`, `unlisted-robe`, `unlisted-arrows-(20)`, `unlisted-bolts-(20)`;
  - `category-gaming-set`, `category-gaming-set-(same-as-above)`, `unlisted-gaming-set`;
  - `category-artisans-tools`, `category-artisans-tools-(same-as-above)`;
  - `category-musical-instrument`, `unlisted-musical-instrument`;
  - `unlisted-iron-spikes`, `unlisted-arcane-focus`.
  - Raw XPHB lines: Artisan, Entertainer, Guard, Noble and Soldier say "(same as above)" (= the background's tool proficiency pick). Wayfarer says "Gaming Set (any)".
  - Bundle quantities are lost today: Acolyte's 10 Parchment, 2 Pouches and 2 Costumes are each qty 1.
  - The gaming-set proficiency card offers only `dice-set` and `playing-card-set` (the catalog has 2 gaming-set items).
- **Packs.** The 7 catalog packs are SRD 2014 records with `weight: None`, so `carryingCapacity.carried` counts 0 for any pack today, in every ruleset.
  - PHB 2024 ch. 6 (user markdown lines 6915-6968 and 7064-7310) gives the contents and table weights: Burglar's 42, Diplomat's 39, Dungeoneer's 55, Entertainer's 58.5, Explorer's 55, Priest's 29, Scholar's 22 lb.
  - Every member maps to an existing catalog item: `oil-flask`, `rations-1-day`, `torch`, `rope-hempen-50-feet`, `lantern-hooded`, `lantern-bullseye`, `ball-bearings-bag-of-1000`, `bell`, `candle`, `case-map-or-scroll`, `paper-one-sheet`, `parchment-one-sheet`, `ink-1-ounce-bottle`, `ink-pen`, `chest`, `clothes-fine`, `clothes-costume`, `mirror-steel`, `perfume-vial`, `blanket`, `holy-water-flask`, `robes`, `lamp`, `book`, `caltrops`, `crowbar`, `tinderbox`, `waterskin`, `bedroll`, `backpack`.
- **XPHB subclass spell data** (raw class files; 11b.4 skipped every `{choose}` and multi-block entry):
  - Abjurer / Diviner / Evoker / Illusionist `known` choose filters per class level: 3 → two picks, then one each at 5, 7, ..., 17; the school filter is in the data.
  - Lore `prepared` 6 → two choose `level=0..3|class=Cleric;Druid;Wizard`.
  - Land: 4 named blocks (Arid / Polar / Temperate / Tropical, levels 3 / 5 / 7 / 9).
  - Illusionist `minor illusion#c` known at 3.
  - Innate blocks: Wild Heart rituals, Glamour Command, Psi Warrior Telekinesis, Shadow Darkness by Focus Point, Archfey Misty Step, Great Old One Hex, Diviner See Invisibility.
  - Nature's Ward table: Arid Fire, Polar Cold, Temperate Lightning, Tropical Poison, plus Poisoned immunity.
  - The 2024 spellbook holds level 1+ spells, so Savant picks are levels 1+ (C4 precedent).
- **E13 text classes.**
  - Changeable on a rest, so a build-time card that stays editable (F-D7): Hunter's Prey, Defensive Tactics, Aspect of the Wilds, Land type, Beast Master companion.
  - The pick lasts one rest or one turn, so a note: Elemental Epitome resistance, Fiendish Resilience, Starry Form, The Third Eye.
  - Beast Master stat blocks are not in the data (refs dropped), so that card is a label only.
- **2014 SRD.**
  - Magical Secrets is `magical-secrets-1/2/3` (Bard 10 / 14 / 18): "included in the number in the Spells Known column", "of a level you can cast ... or a cantrip".
  - `spell-mastery` (Wizard 18) is "when you have them prepared", so not always prepared.
  - `signature-spell` (Wizard 20, singular id) is always prepared, does not count against prepared, and is cast once each per short or long rest.
  - SRD Lore `bonus-proficiencies` and `additional-magical-secrets` are also unmodelled; they are outside the E11 list (see Extras).

---

## 3. Slices in global order (smallest valuable first; test gate after each)

### RP1 (X1) 2024 background ability increases capped at 20 (S). No dependencies.
- **Goal.** Under ruleset 2024, background `ability-bonus` increases (and the "older background" +2/+1 / +1/+1/+1 path) cannot raise a score above 20.
  - Use the FX7 pattern: the clamped part is a non-blocking `pruned` entry ("<Background>: STR is already at maximum (20) and the increase was ignored"), `choiceId` = the background ability card.
  - Mixed and 2014 are unchanged (the 2014 rules have no such sentence).
- **Files.** `engine/resolve.py` (where background ability bonuses are applied; next to the FX7 clamp code), `tests/test_background_cap_2024.py`.
- **VERIFY.**
  - Where the 2024 background ASI is applied relative to species bonuses and ASI progression. The cap applies to the background step only; later ASIs and feats keep their own caps.
  - That older species' ability increases are already ignored under 2024 (verified: SRD Human under 2024 shows base scores).
- **TDD.**
  - 20 + 2 → 20 with a pruned entry;
  - 19 + 2 → 20 with a pruned entry (1 lost);
  - 18 + 2 → 20, nothing lost;
  - +1/+1/+1 with one 20;
  - an older-book background under 2024;
  - mixed: 20 + 2 stays 22 (guard);
  - the problems list is unchanged.
- **Acceptance.** Golden green; FX7 tests green.
- **Risk.** Ordering with Epic Boon caps (FE2): the clamp happens before ASI / feat increases.

### RP2 (B2) 2024 fixed numeric effects of XPHB class and subclass features (S–M). No dependencies.
- **Goal.** A 2024-only effect table keyed by XPHB feature id, applied when the class level (and the selected subclass) reaches the record's own `level`. Covers:
  - Body and Mind (+4 DEX / WIS, cap 25);
  - Primal Champion 2024 (cap 25 instead of the SRD 24; replace, do not stack, under 2024);
  - Draconic Resilience XPHB (HP + Sorcerer level; unarmored AC 10 + DEX + CHA, shield allowed? VERIFY the text);
  - Dance Unarmored Defense (VERIFY its armor / shield clause);
  - Shadow and Gloom Stalker Darkvision (60, or +60 when the character already has Darkvision);
  - Thief Second-Story Work (climb = speed);
  - Sea 6 swim = speed;
  - War 17 resistances;
  - psychic resistance: Psi Warrior 10, Aberrant 6, Great Old One 10;
  - Celestial 6 radiant resistance;
  - Glory 7 speed +10;
  - Mercy 3 Insight + Medicine + Herbalism Kit.
  - Conditional ones (while raging, in the aura, Elemental Attunement active) become notes, not effects.
- **Files.** `catalog/reference_data.py` (`CLASS_FEATURE_EFFECTS_2024` plus quotes), `engine/features.py` (collect under 2024), `engine/resolve.py` (ability step, HP, AC formulas, senses, speeds, resistances, proficiencies), `tests/test_xphb_feature_effects_2024.py`.
- **VERIFY.**
  - How `_class_feature_list` builds effect ids under 2024: the SRD rows still drive `primal-champion` and must not double-apply with the new entry.
  - The "+60 if you already have Darkvision" rule uses the senses already collected at that point.
  - Where the SRD `draconic-resilience` hook lives, so the XPHB one reuses the AC-formula / HP-per-level plumbing.
- **TDD.**
  - Monk 20 2024: DEX / WIS +4 (cap 25, a pruned note when lost);
  - Barbarian 20 2024: cap 25 (base 22 STR → 25 vs SRD 24);
  - Draconic XPHB Sorcerer 6: HP 44 and AC 10 + DEX + CHA (with and without armor; G2 worn armor);
  - Darkvision none → 60 and dwarf → 120;
  - Thief climb, Sea swim, Glory +10;
  - resistances appear in `sheet.damageModifiers`;
  - Mercy skills appear in proficiencies;
  - mixed with the same draft is unchanged;
  - SRD-only catalog: no change.
- **Acceptance.** Golden green; quotes pinned.
- **Risk.** Multiple AC formulas: the PHB 2024 "only one way to calculate AC at a time" rule; the existing `ac_formulas` max-pick handles it, test with Draconic + Barbarian multiclass.

### RP3 (A1, open question 13) Cult of the Dragon Initiate replacement language (S). No dependencies.
- **Goal.** When Draconic is already known at the feat's position, a language card `<feat cid prefix>:languages` (count 1) appears.
  - Options: the E2 pool (Standard + Rare, 19), with known languages disabled "already known".
  - The cid suffix `:languages` makes `chosen_languages` and `gate_languages` pick it up untouched.
  - The fixed Draconic still shows. The FE10 note "add it by hand" is removed from `feat_effects_tail`.
- **Rule** (catalog text): "If you already know Draconic when you select this feat, you instead learn one language of your choice from the language tables..."
- **Position (F3a-5).** Draconic counts as known before the feat from:
  - fixed species / background languages;
  - class-fixed languages at or before the feat's (class index, level);
  - earlier feat or origin-card picks, when the feat is not the origin-background feat itself (the C8 origin card already disables Draconic in that case).
- **Files.** `engine/resolve.py` (feat choice templates, next to `_feat_extra_templates`), `engine/class_choices_2024.py` `gate_languages` (feat replacement card priority = the feat's position), `catalog/feat_effects_tail.py` (note), `tests/test_cult_of_the_dragon_language.py`.
- **VERIFY.** No FRHoF-specific language table in the catalog (use the E2 pool and document it).
- **TDD.**
  - Dragonborn (SRD, fixed Draconic) + Dragon Cultist under 2024: the card appears, Draconic disabled.
  - Human XPHB + Dragon Cultist: no card.
  - Feat via Lessons of the First Ones after an origin Draconic pick: card.
  - Removing the earlier source drops the card and prunes the pick.
  - Mixed with the feat: the same behaviour (FE policy).
- **Acceptance.** Golden green (no golden case holds the feat; VERIFY).

### RP4 (A4, open question 16) 2024 Fighting Style feat card sees a Fighting Initiate style (S). No dependencies.
- **Goal.** In the F1 ordered walk, a Fighting Initiate pick (feat `:fighting-style` card) at its position adds `seen["name:<style>"] = "<Style>, Fighting Initiate"`, so a LATER 2024 Fighting Style feat card disables the same-named FS feat and a stored duplicate gives the usual `feat-duplicate-*` problem.
  - Under 2024 only: under mixed this would turn the FE9 `pruned` path for SRD style cards into a G1-3 problem and move output.
- **Files.** `engine/resolve.py` (`_resolve_asi_selected_feats` / the `walk_hook` site where ASI feat picks enter `seen`; `_taken_reason`), `tests/test_fighting_initiate_fs_card_2024.py`.
- **TDD.**
  - Rogue 4 (FI Dueling) then Fighter 1: FS card Dueling disabled "already taken (Dueling, Fighting Initiate)".
  - Fighter 1 Dueling then FI at 4: unchanged FE9 behaviour.
  - Origin-position FI (VERIFY whether any origin path can grant FI; if not, document it).
  - Mixed guard: FE9 tests unchanged.
- **Risk.** Double reporting (walk problem + `_gate_duplicate_picks` prune). Assert exactly one entry.

### RP5 (A5, open question 21) Cross-feat modifications with numbers (S–M). No dependencies.
- **Goal.**
  1. Extend `modifies` with `innate: {spell_id: {"uses": <str with {pb}>, "note": <str>}}`, applied where feat innate spells are built, only while the target feat is held:
     - Greater Mark of Healing: Cure Wounds uses "{pb}/long rest" + note "Improved Healing: treat a 1 or 2 on a healing die as a 3". Keep its resource as the tracker. No "1/day" Cure Wounds remains.
     - Greater Mark of Making / Shadow: note "cast as its level 3 version" on Magic Weapon / Invisibility.
  2. New entry field `ability_from: <feat index>` for Adept of the Black / Red / White Robes, Outlands Envoy, Warlike Familiar and Magic Connoisseur. When the base feat is held, the dependent feat's `:spell-ability` card is not built and its spells use the base feat's chosen ability. A stored pick on the removed card → `pruned`.
- **Files.** `catalog/feat_effects_data.py` / `feat_effects_tail.py` (+ `FEAT_EFFECT_KEYS`), `engine/feat_effects.py` (`apply_modifies`), `engine/resolve.py` (feat innate assembly; `_feat_spell_ability` at the `:spell-ability` lookup around line 686), `tests/test_feat_modifies.py` (extend).
- **VERIFY.**
  - The exact cid and stored shape of each base feat's ability pick (Magic Initiate PHB / XPHB variants, Familiar Friend "Faithful Companion", Scion of the Outer Planes).
  - That every dependent feat's prerequisite requires the base feat (else keep the card when the base feat is absent).
- **TDD.**
  - Greater Mark of Healing at PB 2 / 4;
  - the base without Greater is unchanged;
  - Making / Shadow note;
  - Adept of the Red Robes with Initiate WIS: no own card, ability WIS;
  - removing Initiate brings the card back;
  - Markdown / PDF lines.
- **Acceptance.** Golden green; the FE coverage ratchet stays green.

### RP6 (P0) Golden rebaseline mode (S, tests only). See section 1.

### RP7 (E11c) SRD Monk tool or instrument choice (S). Depends on RP6. Changes mixed / 2014.
- **Goal.** `catalog/choices.build_choice_template` (proficiency envelopes only) flattens a nested `option_type: "choice"` into one option list:
  - 17 Artisan's Tools + 10 Musical Instruments = 27;
  - `group` labels "Artisan's Tools" / "Musical Instrument";
  - cid `class:monk:1:prof-choice-1`, the same as the 2024 card, so a pick survives a ruleset switch.
  - The pick reaches `sheet.proficiencies.tools`.
- **Files.** `catalog/choices.py`, `tests/test_choices.py`, `tests/test_srd_monk_tool_choice.py`.
- **VERIFY.**
  - That the change cannot touch equipment nested choices (separate `build_equipment_choice` path).
  - That no other proficiency envelope in classes / backgrounds / races / feats has a nested choice (verified once: none).
- **TDD.**
  - Monk 1 under mixed / 2014: card present with 27 options; the pick → tools;
  - a secondary Monk (multiclass) has no card;
  - the 2024 card is unchanged;
  - card order (`prof-choice-0` then `-1`).
- **Golden.** `REBASELINES["E11c"]`:
  - cases `*/src-*/monk*`, `ks/*/monk14`;
  - paths: `result.choices[class:monk:1:prof-choice-1]`, `draft.classes.*.choices.class:monk:1:prof-choice-1`, `result.sheet.proficiencies.tools`, plus whatever `sheet.features` attach the dry run shows, if it matches the rule (VERIFY).
  - The multiclass Barbarian 3 / Monk 2 must be unchanged.

### RP8 (D) 2024 pack contents and carried weight (S–M). No dependencies.
- **Goal.** `reference_data.PACKS_2024 = {pack id: {"weight": <PHB table lb>, "contents": [(item id, qty), ...]}}` for the 7 packs (contents and weights from PHB 2024 ch. 6; the source comment names the table, the data is ids and numbers).
  - Under ruleset 2024: every inventory entry (granted / chosen / added) of a pack id gets `contents: [{itemId, name, qty}]`, and `equipment_weight` uses the table weight for packs.
  - Exports print "Explorer's Pack (съдържа: Backpack, Bedroll, Oil x2, ...)".
  - `EquipmentPage` prints the same contents line (plain text).
  - The pack stays one item; it is not expanded into the inventory.
  - Mixed / 2014: untouched (SRD packs weigh 0 and contents are not shown; see Extras).
- **Files.** `catalog/reference_data.py`, `engine/derived.py` (`equipment_weight(..., weights=None)`), `engine/resolve.py` (inventory entries, carrying under 2024), `export_fields.py`, `markdown_export.py`, `pdf_export.py`, `frontend/src/types.ts` (`contents?`), `frontend/src/pages/EquipmentPage.tsx`, tests `tests/test_packs_2024.py`, `test_export_fields.py` `_EXPECT` (2024 drafts carrying packs: `fighter4-2024`).
- **VERIFY.**
  - Every member id exists.
  - The table weight vs the sum of SRD member weights (Explorer's: SRD rope 10 lb vs PHB 5 lb). The table weight wins; the test documents the difference.
  - The current carried totals of the 2024 kitchen sinks.
- **TDD.**
  - Fighter 2024 package A with Dungeoneer's Pack: carried +55;
  - an added Explorer's Pack under 2024 / mixed (mixed unchanged);
  - contents keys in YAML / MD / PDF;
  - the drift test;
  - 375 px EquipmentPage.
- **Risk.** Pack cost differs (Priest's 33 GP vs SRD 19); not shown anywhere, so it is documented, not changed.

### RP9 (C, E12) 2024 background starting equipment: real items and quantities (M). Depends on RP8 (nothing hard; same area).
- **Decision (mine, as asked): ruleset 2024 only.**
  - The user's byte-identical rule for mixed.
  - The C9b / E8 precedent (quantities only on the 2024 package path).
  - The mixed placeholders are text, not wrong.
  - The golden is unaffected either way (all golden cases use SRD Acolyte; VERIFY). Flipping to "all rulesets" later is a one-line gate plus a P0 rebaseline.
- **Goal.** For the 26 ruleset-2024 backgrounds, the converter adds an ADDITIVE catalog key `starting_equipment_options_2024` (the old key untouched):
  - `keep_counts: True` (Parchment 10, Pouch 2, Costume 2, Dagger 2...);
  - "Robe" → `robes`;
  - "Arrows (20)" → one `arrow`, "Bolts (20)" → one `crossbow-bolt` (both already 20-packs, F3a-6);
  - "Holy Symbol" → nested `holy-symbols` pick (C9b);
  - "Arcane Focus" → nested arcane-focus pick (VERIFY the catalog category: crystal / orb / rod / staff / wand);
  - "Iron Spikes" → `spike-iron` (VERIFY unit size);
  - "(same as above)" tool / instrument / gaming set → a sentinel `background-tool` that `resolve` replaces with the item of the background's own tool proficiency pick (generalize `_monk_tool_pick`; narrative label while unpicked; when the picked tool has no catalog item, keep the label narrative);
  - "(any)" / unlisted gaming set / instrument → a nested pick of that category.
  - A leftover placeholder raises ValueError (strict, like C9b).
  - `resolve` under 2024 reads the `_2024` key, with the same cid and option ids so picks survive a ruleset switch (VERIFY option ids; else the F3a-1 prune applies).
- **Files.** `catalog/official/equipment.py` / `backgrounds.py` (2024 envelope), `catalog/reference_data.py` (extend `CLASS_2024_EQUIPMENT_ITEM_MAP` or a `BACKGROUND_2024_EQUIPMENT_ITEM_MAP`, sentinel), `engine/resolve.py` (`_chosen_equipment`, `_selected_gold_and_narrative_items`), tests `tests/test_background_equipment_2024.py` (rule matrix = the `entries` "Choose A or B" line of every one of the 26), `test_export_fields.py` (`_EXPECT` for the F3b Soldier XPHB drafts).
- **VERIFY.** Raw lines for the 17 non-XPHB backgrounds (FRHoF / EFA / RHW / ABH); gold amounts vs text (C9b found a defect).
- **TDD.**
  - Acolyte A: Parchment x10, a holy-symbol nested card, Robes; carried weight.
  - Soldier A: gaming set = the proficiency pick, Arrows as a 20-pack.
  - Guard: Bolts.
  - Wayfarer: the gaming-set nested card.
  - Artisan / Entertainer: the same-as-above tool / instrument.
  - Mixed: Acolyte XPHB unchanged (narrative "Holy Symbol", "Robe").
  - Ruleset switch keeps the A/B pick.
  - Every 2024 background package converts (no ValueError).
- **Risk.** The F3b 2024 kitchen sinks change (Soldier A); update `_EXPECT` deliberately.

### RP10 (B1) 2024 class-feature numbers as notes (M). No dependencies.
- **Goal.** Under 2024, where the XPHB text gives a number or a use rule, attach it to the existing resource's `details.note`, or add a note-only tail entry (`uses: None`), R9 style. Candidates:
  - Barbarian:
    - Relentless Rage (11): note-only resource "DC 10 Constitution save, +5 per later use, resets on a Short or Long Rest; Hit Points become {2 x Barbarian level}".
    - Brutal Strike (9): "extra 1d10 (2d10 from 17), effects ...; two effects from 17".
  - Bard: Superior Inspiration (18) on Bardic Inspiration: "on Initiative regain uses until you have 2".
  - Cleric:
    - Channel Divinity: Divine Spark dice by level (VERIFY the scaling in `xphb-cleric-2-channel-divinity`), Turn Undead DC = spell save DC;
    - Sear Undead (5): "{max(1, WIS)}d8 Radiant".
  - Druid: Archdruid's Evergreen Wild Shape on Wild Shape.
  - Fighter:
    - Indomitable: "+{Fighter level} to the reroll";
    - Tactical Mind on Second Wind: "1d10 to a failed ability check".
  - Monk:
    - Focus Points: "save DC {8 + WIS + PB}" (quote: "The save DC equals 8 plus your Wisdom modifier and Proficiency Bonus.");
    - notes: Stunning Strike (1 FP, Constitution save), Deflect Attacks "1d10 + {DEX + Monk level}", Slow Fall "{5 x Monk level}", Heightened Focus (Patient Defense Temporary HP = two Martial Arts dice), Perfect Focus (15) "regain to 4 on Initiative", Superior Defense (18) "3 FP: Resistance to all damage except Force, 1 minute".
  - Paladin:
    - Abjure Foes (9): "targets = {max(1, CHA)}";
    - Restoring Touch (14): "5 Hit Points of the pool per condition";
    - VERIFY whether the Lay on Hands pool number is shown.
  - Ranger: Foe Slayer (20) "Hunter's Mark die d10".
  - Rogue: Cunning Strike (5) "save DC {8 + DEX + PB}; costs ...", Improved Cunning Strike (11) two effects, Devious Strikes (14).
- **Files.** `catalog/reference_data.py` (`RESOURCE_TAIL_2024` + `RESOURCE_NOTES_2024`), `engine/class_resources.py` (`_tail_2024`, note merge), `tests/test_class_feature_numbers_2024.py`.
- **TDD.**
  - A numbers matrix at two levels per class;
  - quote pins;
  - no entry before the record's level;
  - mixed unchanged;
  - SRD-only catalog: nothing.
- **Acceptance.** No new output keys, so exports / types are untouched (`details.note` prints already).
- **Risk.** Note bloat. Keep each note to one sentence with the computed number.

### RP11 (B3) 2024 subclass resource tail (M). Depends on RP10 (same table).
- **Goal.** Extend the tail with `subclass` gating for the 45 scanned XPHB subclass features. Uses are an int, `wis_min1`, `cha_min1` or `int_min1`; recharge as the text says. Examples:
  - Warding Flare, Corona of Light, War Priest (short-or-long);
  - Moonlight Step, Star Map, Cosmic Omen;
  - Wholeness of Body, Glorious Defense, Misty Wanderer, Dread Ambusher;
  - Restore Balance, Steps of the Fey, Dark One's Own Luck;
  - the "once per Long / Short Rest" capstones (Hurl Through Hell, Avenging Angel, Elder Champion, Dragon Wings, ...).
  - Entries already in R6 (Psionic Dice, Superiority Dice) are skipped.
  - Features whose use is "expend Channel Divinity / Wild Shape / Focus" become a note on that resource, not a new one.
- **Files.** `catalog/reference_data.py`, `engine/class_resources.py` (`_tail_2024` subclass check: `rc["subclass_id"]` == entry subclass, level from the record), `tests/test_subclass_resources_2024.py`.
- **VERIFY.** The final list by script (the scan pattern is in this plan's facts); each quote pinned; Mercy Flurry "a total number of times equal to your Wisdom modifier".
- **TDD.**
  - Parametrized resolve over every entry at its level (ruleset 2024, the subclass selected);
  - uses at WIS 8 / 16 (min 1);
  - a twin subclass under mixed shows nothing new;
  - order after the class resources.
- **Risk.** Count of resources on mobile. The SPA list is plain; check at 375 px in G.

### RP12 (F1, E13) Subclass proficiency picks (M). No hard dependency (after RP2 for Mercy).
- **Goal.** Under 2024:
  - Lore 3 Bonus Proficiencies: 3 of the 18 skills.
  - Battle Master 3 Student of War: 1 Artisan's Tool + 1 skill from the 2024 Fighter level 1 skill list (`classes_2024`).
  - Fey Wanderer 3 Otherworldly Glamour: 1 of Deception / Performance / Persuasion, plus a note "Charisma checks + {max(1, WIS)}".
  - Gloom Stalker 7 Iron Mind: WIS save proficiency (fixed); if WIS is already a proficient save at that position, a card INT / CHA (count 1) appears instead.
  - Generalize the C6b-2 / F3a-4 Primal Knowledge position gating into "positioned proficiency picks", so these cards see earlier proficiencies and later cards see them. Already-proficient options are disabled; a stored duplicate is pruned.
- **Files.** `catalog/reference_data.py` (`SUBCLASS_PICKS_2024`), `engine/class_choices_2024.py` (templates + generalized gate; keep `is_primal_knowledge_card` as a member of the new set), `engine/resolve.py` (wire; saves for Iron Mind), tests `tests/test_subclass_picks_2024.py`, and the existing Primal Knowledge / F3a-4 tests stay green unedited.
- **TDD.**
  - Each card's options and count;
  - the skills reach `derived.skills` and the tools reach proficiencies;
  - the position order (Rogue 1 Stealth then Lore 3 → Stealth disabled; Lore before a later class skill card);
  - Iron Mind for a Ranger only (WIS fixed) vs Cleric 1 / Ranger 7 (INT / CHA card);
  - attach to the subclass rows in `sheet.features`;
  - `mark_unavailable` on an empty card;
  - mixed with a hidden stored XPHB subclass: no card.

### RP13 (F2, E13) Subclass option cards and their effects (M). Depends on RP2 (senses / speeds plumbing).
- **Goal.** Under 2024, editable build-time cards (F-D7):
  - **Hunter's Prey** (Colossus Slayer → attack-row note "+1d8 once per turn if the target is missing Hit Points"; Horde Breaker → note).
  - **Defensive Tactics** (notes).
  - **Aspect of the Wilds** (Owl: Darkvision 60 / +60; Panther: climb = speed; Salmon: swim = speed).
  - **Draconic Elemental Affinity** (Acid / Cold / Fire / Lightning / Poison → resistance + note "add {CHA} to one damage roll of a spell of that type").
  - **Beast Master Primal Companion** (Land / Sea / Sky, label only; stat blocks are not in the data).
  - **Fey Wanderer Feywild Gifts** (6 flavour options parsed from the feature's table; VERIFY the raw table shape).
  - Notes only (text: per turn or per rest): Elemental Epitome resistance, Fiendish Resilience, Starry Form.
  - Option ids `<featureId>--<slug>`; effects keyed by option id (R5 / S4 style).
- **Files.**
  - `catalog/official/subclasses.py`: either extend `FEATURE_TEXT_CHOICES` (if the XPHB raw entries are `options` blocks; VERIFY) or a data table `SUBCLASS_OPTION_CHOICES_2024` with option names parsed from "Name. text" lines, the G1-7 Wild Heart approach.
  - `catalog/reference_data.py` (effects), `engine/resolve.py` / `features.py` / `attacks` notes (`class_resources.annotate_attacks` pattern).
  - Tests `tests/test_subclass_options_2024.py`.
- **TDD.**
  - Each card;
  - Owl with and without species Darkvision;
  - Panther climb, Salmon swim;
  - the Affinity resistance in `damageModifiers`;
  - the Colossus Slayer row note on weapon rows only;
  - switching an option moves the effect;
  - exports;
  - mixed / stored hidden: nothing.

### RP14 (X3, Known gaps) SPA shows senses, damage modifiers and innate spells (S, frontend). Depends on RP2 and RP13 (they add such data).
- **Goal.** Today these appear only in the YAML / Markdown / PDF exports (no `.tsx` reads `damageModifiers`, `senses`, `innateSpells`; verified). Add plain read-only blocks to the ExportPage preview: "Сетива", "Съпротивления и имунитети", "Вродени заклинания", mirroring the Markdown labels.
- **Files.** `frontend/src/pages/ExportPage.tsx` (or a small component), types already present.
- **Acceptance.** `npm run build`; 375 px check with Draconic XPHB (resistance), Gloom Stalker (Darkvision), a Warlock with Mask of Many Faces.

### RP15 (E11b) 2014 Spell Mastery / Signature Spells (M). Depends on RP6. Changes mixed / 2014.
- **Goal.** Under mixed and 2014, a Wizard (SRD) gets the cards `class:wizard:18:spell-mastery-1` / `-2` and `class:wizard:20:signature-spells`. These are the SAME cids as 2024, so picks survive a switch.
  - The spec `WIZARD_SPELL_PICKS_2014` uses the SRD features `spell-mastery` / `signature-spell` and has no casting-time condition.
  - Spell Mastery picks are NOT always prepared ("when you have them prepared"): note only.
  - Signature picks are always prepared (reason "Signature Spells") and get the R9-style resource (short-or-long, one use each).
  - `sheet.spells[wizard].spellMastery` / `signatureSpells` and the existing export lines appear under mixed / 2014.
  - `mark_unavailable` must cover these three cids outside 2024, or an empty-book card blocks export under mixed.
- **Files.** `engine/class_choices_2024.py` (`wizard_spell_pick_templates`: a ruleset-keyed spec; rename optional), `catalog/reference_data.py`, `engine/class_resources.py` (`_signature_spells` for 2014), `engine/sheet_features.py` (`_spell_pick_labels` by SRD names "Spell Mastery" / "Signature Spell"; VERIFY the names), tests `tests/test_wizard_picks_2014.py`.
- **VERIFY.** Whether the golden Wizard 20 stored spellbooks hold level-1 / 2 / 3 spells (decides pending vs unavailable in the rebaseline).
- **TDD.**
  - 2014 Wizard 18: Spell Mastery cards, a reaction spell allowed (no casting-time rule);
  - not always prepared;
  - 20: Signature → `alwaysPrepared` + resource;
  - level-down prune;
  - an empty book → unavailable, never blocking;
  - 2024 tests unchanged.
- **Golden.** `REBASELINES["E11b"]`:
  - cases `*/wizard20` (4);
  - paths: `result.choices[class:wizard:18:spell-mastery-*|class:wizard:20:signature-spells]`, `draft...` same cids, `result.sheet.spells[*].spellMastery|signatureSpells|alwaysPrepared`, `result.derived.classResources[wizard:signature-spells]`, `result.sheet.features[...]` pick labels, plus the prepared card's disabled flags (`result.choices[class:wizard:spells-known].options[*].disabled|disabledReason`).
  - Then `--append` a new kitchen sink `wizard18-2014`.

### RP16 (E11a) SRD Magical Secrets (M). Depends on RP6. Changes mixed / 2014.
- **Goal.** Under mixed and 2014, at Bard >= 10 the SRD known card (`class:bard:spells-known`):
  - also offers spells of every class list (ruleset / sources aware via `_spell_filter_options`) up to the highest slot level, plus other-class cantrips (the text: "or a cantrip"; "included in the number in the Spells Known column", so no count change);
  - labels them "<Spell> (Magical Secrets)" and tags groups;
  - a cap gate (pattern of `_apply_school_limit`): picks not on the Bard list ≤ 2 x (Magical Secrets features reached: 10 / 14 / 18). Over-cap options are disabled "Magical Secrets: N of N used"; a stored over-cap pick → `pruned`.
  - Approximation, as in C6d: no level-up history, so per-feature level limits are not enforced. Documented.
- **Files.** `engine/resolve.py` (`_spell_choice_templates` known-card branch; the cap gate), `engine/class_choices_2024.py` (label helper reuse), `tests/test_magical_secrets_2014.py`.
- **TDD.**
  - Bard 9: none;
  - Bard 10: cap 2, Fireball offered, a third non-Bard pick disabled;
  - Bard 14: cap 4; Bard 18: cap 6;
  - a cantrip from another class counts against the known number;
  - `sources ["srd"]` filter;
  - multiclass Bard 10 / Wizard: the Wizard's own list is unaffected;
  - 2024 unchanged;
  - timing (Bard 20 mixed under 50 ms; the option list is ~300).
- **Golden.** `REBASELINES["E11a"]`:
  - cases `*/bard11`, `*/bard20` (8);
  - paths `result.choices[class:bard:spells-known].options.*` (added options, labels, groups, disabled) and `.description` only; stored picks unchanged (VERIFY with the dry run).
  - `--append` a new kitchen sink `bard10-2014` with one Magical Secrets pick.

### RP17 (F3, E13) Subclass spell picks: Savants, Improved Illusions, Magical Discoveries, Land (M–L, frontend routing). Depends on RP12.
- **Converter.** Keep the XPHB subclass `{choose}` filters and Land's named blocks as additive catalog keys (`spell_choices`, `spells_by_variant`).
- **Savants** (Abjurer / Diviner / Evoker / Illusionist 3):
  - card `class:wizard:3:feature:<savant fid>`, count = filter entries reached (2 at 3, +1 at 5 / 7 / 9 / 11 / 13 / 15 / 17);
  - options: Wizard-list spells of the school, levels 1 to the highest Wizard slot level (2024 book = level 1+);
  - picks join the effective `wizard_book` for free (not counted against the spellbook card), so the prepared card, Spell Mastery and Signature see them;
  - a spell already in the book is disabled "already in your spellbook".
- **Improved Illusions.** When Minor Illusion is already known at Illusionist 3 (VERIFY sources: Wizard cantrip card, species / feat innate), a card "one other Wizard cantrip" (not counted against cantrips known); otherwise Minor Illusion is known (11b.4 already lists it).
- **Magical Discoveries** (Lore 6): 2 picks from the Cleric / Druid / Wizard lists, cantrips or levels with Bard slots; always prepared (reason "Magical Discoveries").
- **Land.** Card (Arid / Polar / Temperate / Tropical; editable).
  - The chosen block's spells are always prepared by Druid level (3 / 5 / 7 / 9).
  - Nature's Ward (10): resistance by land + Poisoned immunity.
  - Without a pick: no circle spells (pending card).
- **Files.**
  - `catalog/official/subclasses.py`, `engine/resolve.py` (`_spell_choice_templates` wizard branch before the prepared card; `_subclass_spell_ids` variant selection), `engine/class_choices_2024.py`;
  - `_is_count_variable_choice` + `mark_unavailable` + `frontend/src/pages/ClassPage.isSpellChoiceId` (Savant / Discoveries / Illusions cards → Spells tab);
  - tests `tests/test_subclass_spell_picks_2024.py`.
- **TDD.**
  - Evoker 3 / 5 / 17 counts;
  - the school filter;
  - `sources` filter;
  - Savant picks preparable;
  - removing the subclass prunes;
  - Illusionist with and without Minor Illusion picked;
  - Lore 6 Discoveries always prepared and disabled on the known card;
  - Land Arid at 5 (Fireball prepared), at 10 (fire resistance), switching land;
  - drift test;
  - `npm run build`;
  - 375 px Spells tab.
- **Risk.** Spellbook-dependent cascades (Spell Mastery picks of a Savant spell). Test the removal cascade.

### RP18 (F4) XPHB subclass innate spells (S–M). Depends on RP17 (same converter).
- **Goal.** Under 2024, the innate blocks become `sheet.innateSpells` with source = subclass name:
  - Wild Heart: Beast Sense / Speak with Animals rituals, Commune with Nature at 10;
  - Glamour 6: Command;
  - Psi Warrior 18: Telekinesis 1/day;
  - Shadow 3: Darkness via a Focus Point (note "1 Focus Point");
  - Archfey: Misty Step {max(1, CHA)}/long rest (VERIFY vs the RP11 Steps of the Fey resource; one surface only);
  - Great Old One 10: Hex;
  - Diviner 10: See Invisibility (The Third Eye; VERIFY the data meaning).
- **Files.** `catalog/official/subclasses.py` (`_spells_2024`-like parse), `engine/resolve.py` (innate assembly), `tests/test_subclass_innate_2024.py`.
- **TDD.** Each entry at its level; mixed nothing; exports.

### RP19 (A2, open question 14, + Spells of the Mark) Slot-keyed feat spell tables (M). No dependencies.
- **Arcane Adept.**
  - `feats.py` converts `prepared` `sN` into an additive record key `slot_spells: {N: [spell ids]}` (8 AU feats).
  - The engine resolves it against the character's highest spell slot level: max of the shared pool and the Pact Magic slot level ("When you have spell slots of a level specified ... you thereafter always have the spells listed for that level and lower prepared").
  - Each spell becomes a `sheet.innateSpells` entry (`uses` "always prepared", featId, source = feat; no class attribution, so no multiclass question).
  - FE10's table note is shortened.
- **Spells of the Mark** (12 EFA Mark feats).
  - `expanded` `sN` becomes an additive key `expanded_spells`.
  - For each caster class, the spells up to that class's highest castable level are added through the existing `expanded_spell_ids` mechanism (label "(Spells of the Mark)").
  - For a Wizard they are added to the spellbook card's options (VERIFY that the text adds them to the class spell list and that the C4 book draws from the class list).
- **Files.** `catalog/official/feats.py`, `engine/resolve.py`, `catalog/feat_effects_tail.py`, tests `tests/test_feat_slot_spells.py`.
- **TDD.**
  - Abjuration Adept for a Paladin 5 (slot 2): Shield + Lesser Restoration;
  - Wizard 9: up to Mass Cure Wounds;
  - Warlock 5 (pact level 3);
  - a non-caster (prerequisite VERIFY): nothing;
  - Mark of Healing Cleric 5: Spells of the Mark options;
  - mixed: same (FE policy);
  - golden green.

### RP20 (A3, open question 15) 2024 pools for the option-pick feats (L). Depends on RP4 and RP19 (no hard dependency); the last feature slice.
- **Rule** (PHB 2024 line 68): under ruleset 2024 the TCE / PHB option-pick feats draw from the 2024 class lists:
  - Eldritch Adept → the 28 XPHB invocations with `gate_invocations` (Warlock level = 0 for a non-Warlock, so Agonizing Blast / Spear / Repelling / Lessons need Warlock 2; the Pacts are open to anyone with the feat's own prerequisite);
  - Metamagic Adept → XPHB Metamagic (10 incl. Seeking / Transmuted);
  - Martial Adept → XPHB Battle Master maneuvers (20).
  - Fighting Initiate keeps the SRD styles (their effects are already the same-named FS effects; no 2024 "style option" list exists).
  - Mixed: unchanged.
- **Dependents for a feat-held XPHB invocation**, reusing the C7c builders with the feat card as the holder:
  - target cantrip cards (Agonizing / Spear / Repelling);
  - Pact of the Tome cantrips / rituals;
  - Pact of the Blade weapon;
  - Pact of the Chain innate.
  - Lessons of the First Ones through the feat: hook the feat instance into the F1 `walk_hook` like `_LessonsResolver`. This is the heavy part; split it into A3b if the slice grows.
- **Files.** `engine/resolve.py` (`_feat_extra_templates`, `_gate_feat_invocation_prereqs` 2024 branch), `engine/class_choices_2024.py` (C7c builders parameterized by holder cid), `engine/class_resources.py`, `engine/features.py`, tests `tests/test_option_feats_2024.py`.
- **TDD.**
  - 2024 Wizard with Eldritch Adept: XPHB options, Agonizing disabled "requires warlock level 2";
  - Warlock 5 with Eldritch Adept Agonizing Blast: a target card over the known Warlock cantrips;
  - a non-Warlock Pact of the Tome: cards appear;
  - the duplicate family vs the Warlock card (FE9 name compare);
  - Metamagic Adept Seeking Spell;
  - Martial Adept XPHB maneuver;
  - stored SRD ids under 2024 → pruned;
  - mixed unchanged;
  - golden green (`feats-mixed-wizard8` is mixed).
- **Risk.** C7c helpers assume `class:warlock:invocation:` cids (`DEPENDENT_PREFIX`); a feat-holder prefix needs `_is_count_variable_choice` and `prune_invocation_dependents` support. Run the timing check (Warlock 20 + Eldritch Adept).

### RP21 (X2, open question 5) Invocation repeat-instance renumbering (S). Only if decision D3 is approved.
- **Goal.** When the base instance is removed while `~2` stays, the instances are renumbered and their dependent picks (target / feat) move with the instance. Applies to the Warlock card and the A3 feat card.
- **Files.** `engine/class_choices_2024.py` (`raw_invocation_instances`), tests.

### RP22 (G) Final consolidation (M). Last.
- **ARCHITECTURE doc.**
  - One dated section per slice, plus an "RP overview" table.
  - Open questions 5, 7-11 and 13-16 marked closed or superseded with pointers; question 21 (rest) and 22 (2024 part, X1) updated.
  - Known gaps rewritten: SPA surfaces done; FE12 gap list updated.
  - The F0 section gets the rebaseline log and policy.
  - Also update `docs/superpowers/plans/...` cross-references and the project-status memory file.
- **Types drift guard.**
  - New kitchen sinks: `lore-bard6-2024`, `abjurer-wizard9-2024`, `hunter-ranger7-2024`, `wild-heart-barb6-2024`, `draconic-sorc6-2024`, `land-druid10-2024`, `battle-master3-2024`, `fey-wanderer3-2024`, `gloom-stalker-cleric1-ranger7-2024`, `monk20-2024`, `acolyte-xphb-package-a-2024`, `explorers-pack-2024`, `eldritch-adept-warlock5-2024`, `wizard18-2014`, `bard10-2014`, `monk1-2014`.
  - `test_types_drift` over them; `UNTYPED_ALLOWLIST` empty.
  - Non-2024 ones go into the golden via `--append`.
- **Kitchen-sink export sweep.** `test_export_fields._EXPECT` and `_expected_strings` for every new draft (pack contents line, background items with `x<qty>`, subclass picks on rows, new resources / notes, innate spells, Spell Mastery / Signature 2014, Magical Secrets labels).
- **Review checklist.**
  - Every new card is in `_is_count_variable_choice` / `mark_unavailable` when needed.
  - Every spell card is in `isSpellChoiceId`.
  - Every new data entry has a quote pin.
  - Ruleset gates are 2024-only except the declared E11 / FE ones.
  - Golden: STRIP unchanged; rebaselines logged.
  - No `Resurses/` staged.
- **Re-timing** (`resolve()` mean of 50, mixed / 2024): Fighter 20, Monk 20, Wizard 20 (Savant + book), Bard 20 (Magical Secrets mixed; Lore Discoveries 2024), Warlock 20 with 10 invocations + Eldritch Adept, Druid 20 Land, Sorcerer 20 Draconic, the heaviest feat draft. All under 50 ms.
- **375 px browser check** (Vite + Flask, drafts via `localStorage["dnd-builder-draft-v2"]`): ClassPage features / Spells tabs (Savant, Hunter's Prey, Aspect, Iron Mind INT / CHA, Land), BackgroundPage + EquipmentPage (nested holy symbol, same-as-above tool, pack contents line), ExportPage (X3 blocks, resources). `scrollWidth === 375`, no console errors, the export buttons work.

---

## 4. Order, gates and dependencies

| Order | Slice | Size | Depends on | mixed / 2014 | Frontend |
|---|---|---|---|---|---|
| 1 | RP1 X1 background cap | S | none | no | no |
| 2 | RP2 B2 XPHB fixed effects | S–M | none | no | no |
| 3 | RP3 A1 Cult of the Dragon | S | none | feat holders (FE policy) | no |
| 4 | RP4 A4 FS card vs Fighting Initiate | S | none | no | no |
| 5 | RP5 A5 cross-feat | S–M | none | feat holders | no |
| 6 | RP6 P0 rebaseline mode | S | none | tests only | no |
| 7 | RP7 E11c Monk tool | S | RP6 | yes, rebaseline | no |
| (Opus review) | | | | | |
| 8 | RP8 D packs | S–M | none | no | yes |
| 9 | RP9 C E12 | M | RP8 | no | maybe (types) |
| 10 | RP10 B1 class numbers | M | none | no | no |
| 11 | RP11 B3 subclass tail | M | RP10 | no | no |
| 12 | RP12 F1 proficiency picks | M | RP2 | no | no |
| 13 | RP13 F2 option cards | M | RP2 | no | no |
| 14 | RP14 X3 SPA surfaces | S | RP2, RP13 | no | yes |
| (Opus review) | | | | | |
| 15 | RP15 E11b Spell Mastery 2014 | M | RP6 | yes, rebaseline | no |
| 16 | RP16 E11a Magical Secrets | M | RP6 | yes, rebaseline | no |
| 17 | RP17 F3 subclass spell picks | M–L | RP12 | no | yes |
| 18 | RP18 F4 subclass innate | S–M | RP17 | no | no |
| (Opus review) | | | | | |
| 19 | RP19 A2 slot tables + Mark spells | M | none | feat holders | no |
| 20 | RP20 A3 2024 option-feat pools | L | RP4 | no | maybe |
| 21 | RP21 X2 renumbering | S | D3 | no | no |
| 22 | RP22 G consolidation | M | all | append-only golden | yes |
| (Opus review) | | | | | |

---

## 5. Decision points (only what the books and data cannot settle; each has a default the executor uses)

| # | Question | Default |
|---|---|---|
| D1 | A1 / A2 / A5 change output under mixed / 2014 only for drafts that hold those feats (the FE edition policy the user approved for feat effects). Keep that policy for these completions? | Yes. The golden stays green. Strict alternative: gate them on 2024 (one condition each). |
| D2 | The 2024 subclass work (B2 / B3 / F1-F4) is gated on `ruleset == "2024"`. Precedent is mixed: R6 builders and `SUBCLASS_PROFICIENCIES` already apply XPHB subclass content in every ruleset; G1-7 and the C-series gate on 2024. World Tree, Dance and Sea (the only XPHB subclasses visible under mixed) would then keep their gaps under mixed. | Gate on 2024 (strict byte-identical rule; affects only those 3 subclasses and stored hidden picks). |
| D3 | Open question 5: when the base invocation instance is removed, should the stored picks follow the instance (renumber) or keep their keys? | Renumber: picks follow the instance (RP21). Skip RP21 if the user prefers to leave it. |
| D4 | 2014 / mixed fidelity items outside the E11 list (Extras 1-4 below) change mixed / 2014 output. Do them? | No, unless approved. Each would use the P0 rebaseline policy. |

Settled here without asking:
- **E12 is 2024 only (my decision, as requested).** Reasons in RP9; flipping it later is a gate change plus a rebaseline.
- **The pack (D) is 2024 only.**
- **A3 follows PHB 2024 line 68.** "The versions of things in this book replace versions from older books."
- **Savant picks are levels 1+.** The 2024 spellbook holds level 1+ spells (C4 precedent).
- **2014 Magical Secrets cantrips count in Spells Known.** The feature's own sentence says so.
- **Beast Master companion is a label only.** The stat blocks are not in the data.

---

## 6. Extras: cheap and rules-relevant items found (beyond the requested list)

**Already in the program:**
- X1: the 2024 background cap (a real bug).
- B2: Body and Mind and Primal Champion cap 25 (real bugs).
- X3: SPA surfaces (functional, Known gaps).
- X2: open question 5 renumbering (needs D3).

**Not in the program (D4: change mixed / 2014, need approval):**
1. SRD Lore Bard 3 **Bonus Proficiencies** (3 skills) and 6 **Additional Magical Secrets** (2 any-class spells, not counted). This changes the golden Bard 3 / 11 / 20 cases (the golden's first SRD subclass is Lore).
2. **SRD packs weigh 0** (`weight: None`), so `carried` ignores them under mixed / 2014. Fixing it with the SRD contents' sum changes every golden case holding a pack.
3. **SRD bundle quantities are qty 1** under mixed / 2014 (E8 deliberately limited counts to 2024 packages).
4. **Gaming-set picks offer only Dice Set and Playing Card Set** (the catalog has 2 gaming-set items; Dragonchess and Three-Dragon Ante are missing). This affects every gaming-set card. A 2024-only variant is possible inside RP9 if the user wants it.

**Also a decision, not in the program:**
5. TCE fighting styles (Blind Fighting, Interception, Thrown Weapon, Unarmed, Superior Technique) for Fighting Initiate under mixed. The TCE optional class features are a DM-permission rule, so this is a user decision. Default: no.

**Not cheap, or user-owned, so left as they are:**
- Open question 12 (`unavailable` naming): visual and UX pass.
- Open questions 1-4 and 17-20: decided or user-owned.
- Thirsting Blade attack count: pact weapon only, so a note is right.
- Wild Shape forms: no data.
- Open question 22 under mixed: by design.

---

## 7. Needs a real-device check (not doable here; the user postponed it)

On an iPhone (Safari) and an Android phone (Chrome), at 360 and 375 widths:
- Native `<select>` / ChoicePicker with long lists: Magical Secrets ~300 options, the Savant school lists, the ASI feat picker with 131+ options, the XPHB invocation list for Eldritch Adept.
- Checkbox and touch targets in "Носено и държано" and the nested equipment cards.
- `localStorage` draft persistence across tab kill and reload.
- PDF download and open (Content-Disposition, iOS share sheet), and the Cyrillic DejaVu font rendering in the device PDF viewer.
- Markdown / YAML download on iOS.
- Sticky StepNav overflow.
- Long resource lists (RP10 / RP11) readable without horizontal scroll.
- Spells-tab routing of the new cards.
- Performance of `/api/resolve` on mobile networks for Bard 20 / Warlock 20 drafts.

---

## 8. Cross-cutting risks

- **Golden rebaseline scope creep.** Write the `paths` allowlist from the rule matrix; the reviewer compares it with the dry-run output. Never use `--regenerate`.
- **The 2024 kitchen sinks move** in RP8 / RP9 / RP10 / RP11 (Soldier XPHB package A, Fighter 4 pack, notes). Update `_EXPECT` deliberately in the same slice and say so in ARCHITECTURE.
- **Position-gating generalization (RP12)** can shift the F3a-4 / Primal Knowledge outcomes. Existing tests must pass unedited.
- **Spellbook cascades (RP17, RP15).** Savant spells feed Spell Mastery / Signature; removal must prune without blocking.
- **Holder generalization in RP20** touches C7c code paths; the C7c test modules must stay green unedited.
- **Copyright.** Tests pin short catalog sentences (the established pattern). Pack contents are stored as item ids and numbers, not copied sentences.
- **`types.ts` drift.** `contents?` on equipment entries, new `ChoiceOption.group` uses, innate `note`; the drift test catches them.

### Critical Files for Implementation
- /Users/yoanpetrov/dnd-character-creator/server/engine/resolve.py
- /Users/yoanpetrov/dnd-character-creator/server/engine/class_choices_2024.py
- /Users/yoanpetrov/dnd-character-creator/server/catalog/reference_data.py
- /Users/yoanpetrov/dnd-character-creator/server/tests/test_c_series_golden.py
- /Users/yoanpetrov/dnd-character-creator/server/catalog/official/subclasses.py
- Also central: /Users/yoanpetrov/dnd-character-creator/server/engine/class_resources.py, /Users/yoanpetrov/dnd-character-creator/server/catalog/official/feats.py, /Users/yoanpetrov/dnd-character-creator/server/catalog/official/equipment.py, /Users/yoanpetrov/dnd-character-creator/server/catalog/choices.py, /Users/yoanpetrov/dnd-character-creator/server/engine/feat_effects.py, /Users/yoanpetrov/dnd-character-creator/server/tests/kitchen_sink.py, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ClassPage.tsx, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ExportPage.tsx, /Users/yoanpetrov/dnd-character-creator/docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md
