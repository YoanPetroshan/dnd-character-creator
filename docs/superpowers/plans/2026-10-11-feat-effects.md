# Plan: feat effects for every feat source (FE series)

This plan was written by the Opus planner on 2026-10-11. Suggested file name: `docs/superpowers/plans/2026-10-11-feat-effects.md`.

I only read code and data. Nothing in the repo was changed, and no files were written (the scratch scripts were run through stdin heredocs). Numbers marked **verified** come from those runs against the real catalog (`catalog.loader.load()`, 5etools `feats.json` in `~/.claude/dnd/.data/official`).

**VERIFY** means the executor checks it again with a script before writing the test. If a script and this plan disagree, the script wins and the deviation goes into the slice's ARCHITECTURE section.

**Copyright note for executors.** This plan paraphrases feat rules. Each test docstring must quote the governing sentence itself, read from the local `catalog.feats[...]["entries"]`. Each data entry pins its quote with a "quote matches catalog text" test, the same pattern as R9's `test_reference_values_match_catalog_text`.

The user's 2024 PHB markdown is not usable for feat texts. In chapter 5, every feat body is a 5etools embed placeholder ("Loading ..."; 0 hits for "Initiative Proficiency" or "Luck Points"). The chapter is still the authority for:
- the category list;
- the Repeatable rule;
- the multiclass AC rule ("only one way to calculate AC at a time");
- the "advantage doesn't stack" rule.

The XPHB catalog text is the authority for the 2024 feat bodies.

---

## 0. Conventions

Everything from the 2026-10-09 and 2026-10-10 plans still applies, plus the points below.

**TDD.**
- Write the tests first. Each test file's docstring holds the rule matrix, quoting the feat sentence from the catalog.
- Then write the smallest implementation that passes.
- The matrix keeps "which rule applies" separate from "which number" (the Phase 3b-ii lesson).

**Gate after every slice.**
- `cd server && ../.venv/bin/python -m pytest -q`: baseline **2979 passed**.
- `cd <root> && .venv/bin/python -m pytest -q`: **405 passed, 8 skipped**.
- `cd frontend && npm run build` whenever `frontend/` is touched.
- Record the new totals in the slice's ARCHITECTURE section.

**Edition policy (settled here, not a user question).**
- A feat's effect follows **its own edition's text**, under every ruleset in which the character holds it.
  - Effects are keyed by feat index, so `alert-phb` (+5) and `alert-xphb` (+Proficiency Bonus) are different entries.
  - There is no branching on `draft.ruleset` inside feat effects.
- 2014 feats are legal under `2014` and `mixed`, and their effects are now implemented there. This is the user-approved exception to "mixed/2014 byte-identical".
- A feat kept selected while hidden by ruleset or sources (A2) keeps its effects.
- The only ruleset-dependent behaviour stays where it already lives: the class-feature side (Jack of All Trades etc.). See side findings in section 8.

**Golden F0 (`server/tests/test_c_series_golden.py`) policy.**
- Verified: all 228 golden cases are SRD Human + Acolyte, with every ASI filled by an ability combo, and **0 cases hold a feat**. So no feat effect can move them.
- Every FE slice must keep the golden green **without regeneration**.
- Generic signatures (initiative, AC, speed, attacks) get new parameters with defaults that reproduce today's output. The golden proves it.
- **The one additive key is `derived.featResources`** (FE3). It goes into the golden's `STRIP` tuple with a note: "FE3 additive key, empty for feat-less drafts, user-approved feat-effects series".
  - `sheet.feats[].notes` appears only when non-empty, so it needs no strip.
- **FE12 regenerates additively.**
  - New mixed/2014 feat-holding kitchen-sink drafts are added to the golden.
  - The regeneration script must first assert that the previous 228 entries are byte-identical after regeneration (old vs new JSON diff == only the added names).
  - The reason is documented in ARCHITECTURE ("FE12: additive golden cases for feat effects; no existing case changed").
  - Nothing else may change in the golden, ever.

**Other conventions.**
- **Degrade.** With no official data, `catalog.feats` is empty, so every FE path is a no-op. Each slice has one empty-catalog test.
- **Speed.** `resolve()` must stay under 50 ms. Time Fighter 20 (mixed and 2024), Wizard 20 and the FE12 feat-heavy drafts.
- **Commits.** One commit per slice, `feat(feats): ... (FE<n>)`. Stage explicit paths only and never stage `Resurses/`. Use the trailer from the executing session.
- **Frontend.** Plain markup, no CSS. Check at 375px that `document.documentElement.scrollWidth === 375`.
  - Every new sheet/derived key goes into `types.ts` (optional) and `export_fields.py` in the same commit.
  - `test_types_drift.py` must stay green with an empty `UNTYPED_ALLOWLIST`.
- **Executors run one at a time** (shared repo).

---

## Decisions (user, 2026-10-11)

User said: finish what is open, then do the next big step (this plan), with maximum RAW fidelity. F-D1..F-D7 = the recommended defaults below (executors do not re-ask). F-D8 (FE11 spell-grant tail) = skipped (notes only). F-D9 (Jack of All Trades / Remarkable Athlete under ruleset 2024) = INCLUDED as a 2024-only fix in FE12 (mixed/2014 unchanged), because the XPHB text no longer applies them to Initiative.

## 1. Decision points for the user

These are the only questions the books and data cannot settle. Ask them in one message. Each has a default, which the executor uses unless the user overrides it.

| # | Question | Recommended default |
|---|---|---|
| F-D1 | Where do feat resources (Lucky points, Martial Adept die, "Proficiency Bonus times per Long Rest" uses) live? | A new `derived.featResources` list. It has the `classResources` entry shape, minus `classId`, plus `featId`, with `source.kind: "feat"`. Golden: add it to `STRIP` (additive). The alternative is to put them into `classResources` with `classId: null`; it avoids the new key but mislabels them. |
| F-D2 | Optional or conditional damage riders: GWM 2024 "+PB on a Heavy hit", Savage Attacker, Charger 1d8, GWM/Sharpshooter 2014 "-5/+10". | Never fold them into `damage`. Use a row note with the computed number, e.g. "Great Weapon Master: +3 damage (Heavy, Attack action)". Same pattern as E3 / Divine Strike. |
| F-D3 | Conditional AC (Dual Wielder PHB +1 with two melee weapons; Revenant Blade +1 holding the double-bladed scimitar two-handed). | Apply only when `equipment.wielded` (G2) proves the condition. Otherwise a feat note. Same logic as Dueling under G2. |
| F-D4 | Keen Mind XPHB / Observant XPHB: "proficiency, or Expertise if already proficient". When is "already proficient" checked? | Position-aware, like F3a and Primal Knowledge. Count proficiencies from sources at or before the feat's position (origin feats first, then by class index and level). A later grant of the same skill does not convert it. |
| F-D5 | Dual Wielder XPHB's extra attack with a non-Light weapon plus the Two-Weapon Fighting style: does TWF add the modifier? | Yes. The extra attack results from attacking with a Light weapon, which is TWF's trigger. If the user reads it otherwise, flip one flag. |
| F-D6 | Feats that improve the unarmed strike (Tavern Brawler PHB/XPHB, Unarmed Fighting, Dragon Hide claws) for non-Monks. | Add an "Unarmed Strike" attack row only when such a feat is held. For a Monk: one row with the best die, and the alternatives in notes. |
| F-D7 | Choices that the text lets you change on a rest (Boon of Energy Resistance, Weapon Master XPHB mastery, Echoing Soul Expertise, Zhentarim Tactics, Planar Wanderer). | A build-time card that stays editable (D10 / C6a precedent). Planar Wanderer and Zhentarim Tactics are notes only (their pick lasts one rest). |
| F-D8 | FE11, the spell-grant tail (8 AU "Adept" slot-keyed spell tables, Potent Dragonmark's extra slot, Rune Shaper runes, Boon of Magic School Mastery, Magic Connoisseur list). Most are Unearthed Arcana. | Skip. Notes only. Build FE11 only if asked. |
| F-D9 | Jack of All Trades / Remarkable Athlete under ruleset 2024 (side finding: the XPHB texts no longer apply to Initiative; the engine still adds them). | Out of this plan. Offer as a separate 2024-only fix. Mixed/2014 are unchanged. |

Not a question, settled by the books: notes are in English (same as every resource and attack note today), and section headings are in Bulgarian.

---

## 2. Verified facts: data and current engine

### Catalog

- **305 feats.**
  - By source: XPHB 77, PHB 42, FRHoF 34, AU 29, EFA 28, ABH 16, TCE 15, XGE 15, RHW 11, DSotDQ 9, BGG 8, SatO 7, FTD 3, ERLW 2, LFL 2, PSK 2, SCC 2, BMT 1, MTF 1, PSX 1.
  - By category: `''` 108, G 95, O 35, EB 32, D 13, FS 11, DG 9, FS:P 1, FS:R 1.
  - `ruleset` 2024: 157, 2014: 148.
- **5etools carries no structured key** for initiative, HP, speed, AC, passive, resources or attack riders. Every such effect is prose, so a hand table is unavoidable.
  - Structured keys present (raw counts): `ability` 178, `additionalSpells` 86, `skillProficiencies` 12, `resist` 11, `toolProficiencies` 10, `expertise` 7, `languageProficiencies` 7, `armorProficiencies` 6, `repeatable` 5, `senses` 4, `optionalfeatureProgression` 4, `weaponProficiencies` 4, `immune` 2, `conditionImmune` 2, `savingThrowProficiencies` 2, `skillToolLanguageProficiencies` 2, `_versions` 2, `bonusSenses` 1, `traitTags` 8.
- **Already applied today, for all sources:**
  - ability bonuses (fixed and choice);
  - skill/tool/weapon/armor proficiencies;
  - languages;
  - resist/immune/condition immunities;
  - `senses`;
  - fixed and choice Expertise (Skill Expert, Boon of Skill, Prodigy, Echoing Soul);
  - Resilient save choice;
  - Skilled picks;
  - `additionalSpells` (innate entries, spell choices, variants, spellcasting-ability cards);
  - the 2024 Fighting Style feats through `CLASS_FEATURE_EFFECTS` (archery, defense, dueling, GWF, TWF, thrown, plus Blind Fighting's blindsight). That is 10 of 13 FS-category feats; Interception, Protection and Unarmed Fighting are not done.
- **`optionalfeatureProgression` feats** (no card today): Eldritch Adept TCE (EI ×1), Fighting Initiate TCE (FS:F ×1), Martial Adept PHB (MV:B ×2), Metamagic Adept TCE (MM ×2).
  - `catalog.features` holds 114 `opt-*` records: maneuvers PHB/TCE/XPHB, runes, arrows, XPHB EI/MM, and `opt-dueling-phb` / `opt-two-weapon-fighting-phb`.
  - The 2014 fighting styles, metamagic and invocations live as SRD features (`fighter-fighting-style-*`, sorcerer metamagic subfeature options, `eldritch-invocation-*`).

### Bugs and gaps found (verified by code reading and data)

- **B1. The Epic Boon cap of 30 is ignored.**
  - All 32 EB records carry `ability[].max: 30` (31 `choose`+`max`, 1 fixed `cha`+`max`). No other feat has `max`.
  - `_ability_bonuses_from_5etools` drops `max`.
  - `_apply_asi_progression` calls `asi_mod.asi_exceeds_cap(deltas, running)` with `ASI_CAP = 20`, so a Boon at STR 20 is skipped although RAW allows 21–30.
- **B2. Background- and species-feat ability bonuses are uncapped.** `feat_bonuses` is added flat into `final_scores` (resolve ~4289–4373). Example: a Variant Human PHB half-feat at 20 gives 21. The `_apply_asi_progression` docstring already admits this.
- **B3. Echoing Soul RHW data says `skillProficiencies: [{"any": 1}]`, but the text says two skills.** Text wins: override the count to 2.
- **B4. Harper Agent FRHoF `languageProficiencies: [{"thieves' cant": true}]` is dropped** (disclosed in Phase 4c-i; the C6b-2 language tables now have a Thieves' Cant id).
- **B5. Keenness of the Stone Giant `bonusSenses: [{darkvision: 60}]` is not converted.** Rule: darkvision 60, or +60 if you already have it.
- **B6. Keen Mind XPHB / Observant XPHB:** picking an already-proficient skill does nothing today. RAW gives Expertise.
- **B7. The "not already Expertise" rule is enforced only under ruleset 2024.**
  - Skill Expert TCE and Prodigy XGE text forbids a skill that already benefits from Expertise.
  - Boon of Skill and Skill Expert XPHB say "lack Expertise".
  - The `lacksExpertise` gate applies only under ruleset 2024 (decision E1 revised). These are the feats' own rules, so they apply under every ruleset.
- **B8. Weapon Master PHB's 4 weapon picks are dropped** (5etools `fromFilter`). Weapon Master XPHB's mastery pick does not exist.
- **B9. Feat sub-choice options are not disabled at the cap** ("already at maximum"). This is a disclosed Phase 4c gap.

### Engine anchors (resolve.py, 5473 lines)

- `resolved_feats = background_feats + species_feats + fs_feats + lessons_feats + asi_selected_feats` at ~4488.
  - Instance tags: `_asi_cid`, `_asi_origin`, `_asi_level`, `_species_origin`, `_fs_cid`, `_inv_cid`.
  - `_feat_cid_prefix(feat)` is the per-instance cid prefix.
  - `_feat_spell_ability(feat, "inherit", choices)` resolves "the ability increased by this feat".
- Derived block ~5235–5347:
  - `effects = features_mod.active_effects(...) + invocation_effects`;
  - `derived_mod.initiative(modifiers, prof_bonus, jack, remarkable)`;
  - HP = `hit_point_max_multiclass + features_mod.hp_bonus + SRD trait hp_per_level × total level`;
  - speeds via `_species_speeds` → `_raise_walk_speed` (Unarmored Movement, Fast Movement) → Gift of the Depths swim;
  - AC via `equipment_mod.armor_class_from_gear(items, dex_mod, formulas, modifiers, armored_bonus)`;
  - attacks via `attacks_mod.attacks_from_gear(...)` → `class_resources_mod.annotate_attacks` → `annotate_mastery`;
  - `armor_warnings` gives `stealthDisadvantage`.
- Senses ~5384–5390. `sheet_feats = sheet_features_mod.feats_summary(resolved_feats, choices)` ~5402.
- Feat sub-choice template sites, where every new feat card must also be emitted:
  - background (default prefix `feat:<index>`, selections in `background.choices`);
  - species (`_species_origin`, in `species.choices`);
  - FS feats ~4450;
  - Lessons ~4443;
  - ASI ~4474–4485.

### Kitchen sink (verified)

- 12 of the 2024 drafts hold feats.
  - Human XPHB with Alert XPHB (species origin feat) and Soldier XPHB with Savage Attacker XPHB: rogue6, sorcerer17, cleric7, wizard20, ranger9, barbarian3, fighter4.
  - warlock7-2024 holds Alert XPHB via Lessons.
- These drafts' initiative (+Proficiency Bonus) and attack-row notes **will change on purpose** in FE1 and FE5. Each slice lists the edited expectations (`test_export_fields.py` `_EXPECT`, `test_types_drift`).
- No mixed/2014 kitchen-sink draft holds a feat.

### Useful real grants for tests

- XPHB backgrounds:
  - Criminal and Guard → Alert XPHB;
  - Farmer → Tough XPHB;
  - Merchant and Wayfarer → Lucky XPHB;
  - Sailor → Tavern Brawler XPHB;
  - Soldier → Savage Attacker XPHB;
  - Hermit → Healer XPHB;
  - Entertainer → Musician;
  - Artisan → Crafter;
  - Charlatan, Noble and Scribe → Skilled;
  - Acolyte, Guide and Sage → Magic Initiate XPHB.
- Species feat grants: `human-xphb` (Origin), `custom-lineage-tce` (any), subrace `human-phb-variant-phb` (any).
- 2014 feats can be picked at a mixed ASI: `class:fighter:4:asi: ["feat:alert-phb"]`.
- `double-bladed-scimitar` exists in `catalog.items`.

---

## 3. Scan: all 305 feats by effect kind

A feat can be in several kinds. "New" means work in this plan. The FE0 table encodes this per index, and the exhaustiveness test enforces it.

**A. Ability score increases (data-carried, 178 raw records).**
- Applied today. Fixes needed: EB cap 30 (32 feats, B1), origin-feat cap (B2), option-level "at maximum" reasons (B9).
- VERIFY V3: no Origin, FS, FS:P or FS:R feat has `ability`. The Lessons and fighting-style paths skip ASI today, so this guards that assumption.

**B. Numeric derived stats (new, 19 feats).**

| Kind | Feats | Rule (paraphrase) |
|---|---|---|
| Initiative | `alert-phb` (+5), `alert-xphb` (+PB) | XPHB adds your Proficiency Bonus to Initiative, so Jack of All Trades / Remarkable Athlete half-bonuses don't add on top. PHB is a flat +5 on top of everything. |
| Hit point max | `tough-phb`, `tough-xphb` (+2 × character level, retroactive); `boon-of-fortitude-xphb` (+40) | |
| Walking speed | `mobile-phb` +10, `speedy-xphb` +10, `boon-of-speed-xphb` +30, `squat-nimbleness-xge` +5 ("walking speed"), `mark-of-passage-efa` +5, `transmuted-anatomy-au` +5 | |
| Climb speed | `athlete-xphb` | Climb Speed equals your Speed, after all walk bonuses. |
| AC | `dragon-hide-xge` (alternative formula 13+DEX, shield allowed, no armor); `medium-armor-master-phb` / `-xphb` (medium armor DEX cap 3 when DEX **score** ≥ 16); `dual-wielder-phb` (+1, conditional, F-D3); `revenant-blade-erlw` (+1, conditional, F-D3) | |
| Stealth | `medium-armor-master-phb` | Medium armor no longer imposes Stealth disadvantage. The XPHB text drops this clause (VERIFY V11). |
| Passive | `observant-phb` | +5 to passive Perception and passive Investigation. |
| Senses | `keenness-of-the-stone-giant-bgg` | `bonusSenses`, B5. |

**C. Choice-shaped gaps (new cards or rules, 22 feats).**
- Proficiency-or-Expertise: `keen-mind-xphb`, `observant-xphb` (B6).
- Lacks-Expertise under every ruleset: `skill-expert-tce`, `prodigy-xge`, `skill-expert-xphb`, `boon-of-skill-xphb` (B7).
- Data fixes: `echoing-soul-rhw` (2 skills, B3), `harper-agent-frhof` (Thieves' Cant, B4).
- Weapons: `weapon-master-phb` (4 Simple/Martial weapon proficiencies, B8), `weapon-master-xphb` (one weapon kind's mastery; must be proficient).
- Resistance picks:
  - `dragonscarred-frhof`: 1 of acid/cold/fire/lightning/poison;
  - `boon-of-energy-resistance-xphb`: 2 of 9;
  - `portal-jumper-au`: 1 of necrotic/psychic/radiant;
  - `spell-resistant-au`: 1 of necrotic/psychic/radiant/thunder;
  - `scion-of-the-outer-planes-sato`: resistance bound to the existing plane-variant pick (Chaotic poison, Evil necrotic, Good radiant, Lawful force, Outlands psychic; from the feat's own table).
- Damage-type picks (note effect, plus a "different type each time" rule across repeats): `elemental-adept-phb`, `elemental-adept-xphb`.
- Variant pick: `strike-of-the-giants-bgg` (6 `_versions`: Cloud/Fire/Frost/Hill/Stone/Storm; the effect is a note per type).
- Option-progression picks: `fighting-initiate-tce` (1 fighter Fighting Style, with effects through `CLASS_FEATURE_EFFECTS`), `martial-adept-phb` (2 maneuvers + 1 d6 superiority die), `metamagic-adept-tce` (2 Metamagic + 2 sorcery points), `eldritch-adept-tce` (1 invocation with no prerequisite, or Warlock-met; effects through `features.invocation_effects`).

**D. Attack rows (new, 32 feats).**
- Unarmed row: `tavern-brawler-phb` (d4), `tavern-brawler-xphb` (1d4+STR, reroll 1s, push), `unarmed-fighting-xphb` (1d6+STR, 1d8 with no weapon/shield held), `dragon-hide-xge` (claws 1d4+STR slashing).
- Off-hand damage:
  - `dual-wielder-phb`: off-hand for non-Light one-handed melee weapons;
  - `dual-wielder-xphb`: extra attack with a non-2H melee weapon after a Light attack;
  - `crossbow-expert-xphb`: modifier on the Light crossbow extra attack.
- Ability change: `revenant-blade-erlw` (double-bladed scimitar gains Finesse).
- Row notes with numbers:
  - `savage-attacker-phb` (melee) / `-xphb` (any weapon);
  - `great-weapon-master-phb` (heavy melee, proficient: -5/+10) / `-xphb` (+PB on Heavy hits);
  - `sharpshooter-phb` (-5/+10, long range, cover) / `-xphb`;
  - `crossbow-expert-phb` / `-xphb` (loading, melee range);
  - `piercer-tce` / `-xphb` (piercing);
  - `slasher-tce` / `-xphb` (slashing);
  - `crusher-tce` / `-xphb` (bludgeoning);
  - `polearm-master-phb` (glaive, halberd, quarterstaff, spear; reaction also pike) / `-xphb` (quarterstaff, spear, Heavy+Reach);
  - `charger-phb` (+5) / `-xphb` (1d8);
  - `gunner-tce` (firearms);
  - `elven-accuracy-xge` (DEX/INT/WIS/CHA attacks);
  - `orcish-fury-xge` (+1 weapon die, 1/short rest);
  - `poisoner-tce` / `-xphb` (dose DC);
  - `bomber-abh` (thrown);
  - `boon-of-irresistible-offense-xphb` (ignore B/P/S resistance; crit extra = the increased ability's score).

**E. Resources with uses (new, about 82 feats; VERIFY V4 each).**
- Counted: "number of times equal to your Proficiency/proficiency bonus" (41), "regain expended ... when you finish a" (45), "can't use it again until you finish ..." (34). The union, minus spell-only grants already shown as innate spells (Fey/Shadow Touched etc.), is 82.
- Members: `aberrant-dragonmark-efa`, `adept-of-the-red-robes-dsotdq`, `agent-of-order-sato`, `arcane-artist-au`, `arcane-infiltrator-au`, `arcane-omens-au`, `arcane-overload-au`, `arcane-safeguard-au`, `arcane-undertaker-au`, `baleful-scion-sato`, `bloodlust-abh`, `boon-of-erupting-spellpower-au`, `boon-of-exquisite-radiance-frhof`, `boon-of-fate-xphb`, `boon-of-fluid-forms-frhof`, `boon-of-misty-escape-abh`, `boon-of-recovery-xphb` (Last Stand 1/LR + Recover Vitality pool of ten d10), `boon-of-terror-frhof`, `boon-of-the-soul-drinker-frhof`, `cult-of-the-dragon-initiate-frhof`, `delicious-pain-abh`, `divination-adept-au`, `ember-of-the-fire-giant-bgg`, `fade-away-xge`, `fairy-trickster-frhof`, `familiar-friend-au`, `fury-of-the-frost-giant-bgg`, `gathered-whispers-rhw`, `genie-magic-frhof`, `gift-of-the-chromatic-dragon-ftd` (2 resources), `gift-of-the-gem-dragon-ftd`, `gift-of-the-metallic-dragon-ftd`, `greater-aberrant-mark-efa`, `greater-mark-of-handling-efa`, `greater-mark-of-healing-efa`, `greater-mark-of-hospitality-efa`, `greater-mark-of-scribing-efa`, `greater-mark-of-warding-efa`, `guile-of-the-cloud-giant-bgg`, `keenness-of-the-stone-giant-bgg`, `knight-of-the-crown-dsotdq`, `knight-of-the-rose-dsotdq`, `knight-of-the-sword-dsotdq`, `light-bringer-abh`, `living-shadow-rhw`, `lordly-resolve-frhof`, `love-bites-abh`, **`lucky-phb` (3 points, long rest)**, **`lucky-xphb` (PB points, long rest)**, `mage-slayer-xphb` (Guarded Mind 1/short or long rest), `mark-of-sentinel-efa`, **`martial-adept-phb` (1 superiority die d6, short or long rest; separate from Battle Master dice because the die size differs)**, **`metamagic-adept-tce` (2 sorcery points, Metamagic only, long rest)**, `mist-walker-rhw`, `mythal-touched-frhof`, `orcish-fury-xge`, `planar-wanderer-sato`, `portal-jumper-au`, `potent-dragonmark-efa`, `purple-dragon-commandant-frhof`, `purple-dragon-rook-frhof`, `putrefy-abh`, `rebuke-abh`, `righteous-heritor-sato`, `ritual-caster-xphb` (Quick Ritual), `rune-shaper-bgg`, **`second-chance-xge` (1, until initiative or a short/long rest)**, `sharp-eye-rhw`, `soul-of-the-storm-giant-bgg`, `spell-resistant-au`, `spell-subterfuge-au` (uses = modifier of the increased ability), `spellfire-spark-frhof`, `squire-of-solamnia-dsotdq`, `strike-of-the-giants-bgg`, `strixhaven-mascot-scc`, `survivor-rhw`, `symbiotic-being-rhw`, `tireless-reveler-abh`, `transmuted-anatomy-au`, `vampire-hunter-abh`, `vampires-plaything-abh`, `vampiric-exultation-psx`.

**F. Notes only (161 feats remain, after removing 7 already-done FS feats).**
- About 15 carry a computed number in the note:
  - Inspiring Leader PHB (THP = level + CHA) / XPHB (THP = character level + modifier of the increased ability);
  - Heavy Armor Master PHB (-3) / XPHB (-PB);
  - Durable PHB (minimum = 2 × CON modifier, at least 2);
  - Chef TCE/XPHB (treats = PB, THP = PB, meals for 4 + PB);
  - Musician (allies = PB);
  - Healer PHB/XPHB (1d6 + 4 + Hit Dice / die + PB);
  - Defensive Duelist PHB/XPHB (+PB AC reaction);
  - Shield Master PHB (+shield AC on single-target DEX saves) / XPHB (Shield Bash DC 8 + STR + PB);
  - Telekinetic, Poisoner, Actor XPHB, Boon of Energy Resistance (DCs);
  - Interception (1d10 + PB).
- The rest are pure advantage/reaction/narrative notes.
- Already data-covered spell feats get no new effect beyond a note where the text adds one (e.g. "no Concentration" riders).

**VERIFY list (scripts before tests).**
- V1: Echoing Soul text vs data (two skills).
- V2: all 32 EB have `max: 30`, and no other feat has `max`.
- V3: no O/FS/FS:P/FS:R feat has `ability`.
- V4: every resource's uses/recharge text.
  - Pin each quote in a test.
  - Special recharges: "until you roll Initiative or finish a Short or Long Rest" (Second Chance, Boon of Fate, Erupting Spellpower) maps to recharge `short-or-long` plus `details.note`.
  - "but no more than once per turn" stays in the note.
- V5: Martial Adept pool = MV:B maneuvers of the feat's edition (PHB + TCE `opt-*`).
  - Check which catalog field carries `featureType`. It read empty in my scan; the Battle Master path (`_optional_progression_template`) shows the working filter.
- V6: Fighting Initiate pool = SRD fighter Fighting Style options (6). The TCE FS:F styles (Blind Fighting, Interception, Thrown, Unarmed, Superior Technique) are not imported, so disclose that.
- V7: Metamagic Adept pool = SRD Metamagic options (8). Seeking/Transmuted TCE are not imported, so disclose that.
- V8: Eldritch Adept pool = SRD invocations whose prerequisite is empty, or met by a Warlock (reuse `_invocation_unmet`).
- V9: Weapon Master PHB: the text says Simple or Martial weapons. Use the per-weapon proficiency ids from `reference_data.weapon_proficiency_id` and ignore the 5etools filter string.
- V10: Keenness: darkvision 60, or existing + 60; Devil's Sight unaffected.
- V11: MAM PHB vs XPHB stealth clause.
- V12: how G2 represents "double-bladed scimitar held with two hands".
- V13: 2014 unarmed base 1 + STR; Tavern Brawler PHB is a d4.
- V14/V15: Squat Nimbleness says "walking speed"; Mobile's "speed" is walk only (F1-6 precedent).
- V16: Alert XPHB with JoaT/RA: no double counting.
- V17: which kitchen-sink expectations move.
- V18: the golden holds 0 feats today (verified). FE0 adds a guard test that counts golden feats.

---

## 4. Engine design

### 4.1 Where effects live

**New data module `server/catalog/feat_effects_data.py`.**
- Pure data, one entry per feat index. The quoted sentence goes in a comment, pinned by a test.
- Keyed by feat index, so edition-aware by construction.
- `reference_data.py` (983 lines) stays the home of class/species data. Feats get their own file because about 305 entries would double it.

**New pure engine module `server/engine/feat_effects.py`.**
- No catalog import. Callers pass the resolved feat instances, choices and numbers.
- Same style as `features.py` / `class_resources.py`.
- `resolve.py` only wires (it is already 5473 lines).

**Effect vocabulary (entry keys; every key optional).**
- `initiative`: `int` | `"pb"`.
- `hp_per_level`: int; `hp_flat`: int.
- `walk_bonus`: int; `climb_equals_walk`: bool.
- `ac_formula`: `{base, abilities, allows_shield}` (same shape as `CLASS_FEATURE_EFFECTS`).
- `medium_armor_dex_cap`: `{cap: 3, min_dex_score: 16}`; `medium_armor_stealth_ok`: bool.
- `ac_bonus_if`: `{bonus, wielded: "two-melee" | {item: "double-bladed-scimitar", two_hands: true}}`.
- `passive_bonus`: `{"skill-perception": 5, "skill-investigation": 5}`.
- `senses_additive`: `{darkvision: 60}` (Keenness; catalog field `bonus_senses`).
- `prof_or_expertise`: true (marks the feat's skill card).
- `lacks_expertise`: true (marks the feat's Expertise card under every ruleset).
- Resistance pick: `resist_choice` `{count, options}` or `resist_by_variant` `{variant: type}`; `damage_type_choice` `{options, distinct_across_repeats: true}`.
- `weapon_proficiency_choice` `{count: 4, categories: ["simple", "martial"]}`; `mastery_choice` `{count: 1}`.
- `option_picks` `{kind: "fighting-style" | "maneuver" | "metamagic" | "invocation", count, pool}`.
- `unarmed` `{die, die_free_hands?, type, ability: "STR", notes}`.
- `offhand` `{"non_light_one_handed_melee": true}` | `{"light_crossbow_mod": true}` | `{"dw2024": true}`; `finesse_items` `["double-bladed-scimitar"]`.
- `attack_notes`: `[{when: {...predicate}, text}]`.
  - Predicate keys: `melee`, `ranged`, `weapon`, `properties` (all/any), `damage_types`, `items`, `proficient`, `ability_in`.
  - `{pb}`, `{mod:ABILITY}`, `{inc_mod}` placeholders are formatted by the engine.
- `resources`: `[{name, uses: int | "pb" | "inc_mod" | "half_pb", recharge, die?, dice?, pool?, dc?: "inc"|"STR"|..., note}]`.
- `notes`: `[text]` (placeholders allowed).
- `data_only`: true (everything is carried by the catalog fields, e.g. Heavily Armored).

**Coverage ratchet.** `FEAT_PENDING: frozenset[str]` holds the indexes not yet classified. FE0 fills it with every feat that has no entry; each slice removes the ones it covers; FE10 empties it. `test_feat_effects_coverage.py` asserts:
- every catalog feat index is in exactly one of `FEAT_EFFECTS` | `FEAT_PENDING`;
- every key in `FEAT_EFFECTS` is a catalog feat;
- every entry uses only known vocabulary keys;
- `FEAT_PENDING` is empty from FE10 on.

**Catalog-additive fields** (`catalog/official/feats.py::_feat_from_5etools`; never reach mixed/2014 output for feat-less drafts):
- `ability_cap` (from `max`, default 20);
- `bonus_senses` (from `bonusSenses`);
- `REPEATABLE`-style override tables in `reference_data` for B3 (Echoing Soul skills `any: 2`) and B4 (Harper Agent Thieves' Cant id from the C6b-2 language table).

### 4.2 Aggregating effect sources (feat instances)

`feat_effects.instances(resolved_feats, choices) -> list[FeatInstance]`.

`FeatInstance = (feat, prefix, origin, position, increased_ability, effect)`:
- `prefix` = `_feat_cid_prefix(feat)`, per instance, so a repeatable feat taken twice gives two instances with their own picks.
- `origin` = background | species | fighting-style | invocation | asi (same rule as `feats_summary`).
- `position` = `_feat_build_position(feat, class_order)`. Origin feats get None, which sorts first.
- `increased_ability`:
  - the single fixed `ability_bonuses` key;
  - else the selected `<prefix>:ability-bonus` pick (reuse the logic of `_feat_spell_ability(feat, "inherit", choices)`; expose a small shared helper instead of duplicating);
  - else None, which gives a pending marker in notes ("(choose the ability)").
- `effect` = `FEAT_EFFECTS.get(feat["index"], {})`.

Sources covered automatically: background grants, species grants (Human XPHB / Variant Human / Custom Lineage), 2024 Fighting Style cards, Lessons of the First Ones, and ASI picks, all through `resolved_feats`.
- Kept-but-hidden picks (A2) are included.
- Prerequisite-blocked ASI picks and duplicates are not (they never reach `resolved_feats`).
- `featOptions` (Rewarded/Ruined alternatives) stay unresolved, as before.

**Stacking rules** (in `feat_effects`, each tested):
- **Same feat twice** is impossible unless repeatable (S2/G1-2, cross-edition by name key). Defensively, numeric effects are deduplicated by `_feat_name_key`, so a stray duplicate never doubles Alert/Tough/Mobile.
- **Initiative.**
  - `bonus = sum(flat ints)` (only Alert PHB +5).
  - `proficient = any("pb")`.
  - `initiative = DEX + (PB if proficient else JoaT/RA half bonus) + bonus`.
  - The PHB +5 stacks with JoaT. Alert XPHB replaces the half bonus (a check that adds PB doesn't add half-PB).
- **HP.** `hp_per_level × total character level` plus `hp_flat`. It adds to Dwarven Toughness / Draconic Resilience (different features). Tough is retroactive: twice your level when gained plus 2 per later level equals 2 × current level.
- **Walk speed.** Different named bonuses add, applied walk-only after Unarmored Movement and Fast Movement. Then Gift of the Depths swim = walk and Athlete climb = max(existing climb, walk), both reading the final walk. Feat bonuses apply in armor; heavy-armor speed loss stays unmodelled.
- **AC.**
  - Alternative formulas (Dragon Hide, Unarmored Defense, Draconic Resilience, Armor of Shadows) are best-of, never summed. Source: PHB 2024 Multiclassing "Armor Class" paragraph, which says one AC calculation applies at a time.
  - MAM changes the medium armor's DEX cap only.
  - Flat bonuses (Defense, Dual Wielder, Revenant Blade) add when their condition holds.
- **Senses.** Highest range per type wins (existing). Keenness is the only additive one: `darkvision = 60 if none else existing + 60`, applied after every other darkvision source.
- **Resistances** are a set union (existing).
- **Passive** bonuses add to the passive scores only, never to `derived.skills`.
- **Advantage / disadvantage** are notes only. RAW: advantage doesn't stack, so there is nothing numeric.
- **Resources** are separate per feat instance. Martial Adept's d6 never merges into the Battle Master dice resource (the note says "added to your superiority dice; it stays a d6"). Metamagic Adept's points are a separate pool, restricted to Metamagic.

### 4.3 Ability scores (feat ASI before derived stats)

Today:
- Background and species feat bonuses (fixed + chosen) go into `feat_bonuses` and then `final_scores` (uncapped, B2).
- ASI feats go through `_apply_asi_progression` (cap 20 for all, B1).
- FS and Lessons feats have none (V3).
- Primal Champion runs after, then modifiers.

FE2 changes:
1. `asi_mod.asi_exceeds_cap(deltas, scores, cap=20)` gets a `cap` parameter. `_apply_asi_progression` passes `feat.get("ability_cap", 20)` for feat picks; combos keep 20.
2. Origin feats: compute the pre-feat score (base + species + background bonuses, already built for species-feat prerequisites as `pre_feat_scores`). Apply each feat delta as `min(delta, max(0, cap - running))` per ability, in background-then-species order. For +1 deltas, clamping equals the skip rule.
3. Option-level reasons: `_feat_ability_bonus_choice_templates(..., scores=)` disables an option whose ability is already at the feat's cap ("already at maximum (20)" / "(30)"). ASI instances read `scores_by_level[lvl]`; origin feats read the pre-feat scores. A stored pick of a disabled option is dropped through the generic pass with a `pruned` entry (F3a-1 behaviour).
4. `_feat_prerequisite_problems`' chosen-delta subtraction must use the **applied** (clamped) delta, not the raw one. Otherwise it repeats the "subtracting a delta never applied" false positive the ASI-or-feat review found.

### 4.4 Interplay with existing choices

- Skilled (skill-or-tool picks), Resilient (`:save-choice-`), Skill Expert, Boon of Skill, Prodigy and Echoing Soul (`:expertise-choice-`), and Magic Initiate (spell cards, `spell-ability`) already cascade from every origin. Verified in the ARCHITECTURE "Follow-up cleanups", "Feat skill-or-tool picks" and C7c sections.
- FE6 adds:
  - the prof-or-expertise conversion (the stored cid stays the same, so no migration);
  - `lacksExpertise` on the feat cards of B7 under every ruleset. This is a template flag, already stripped from output.
- The 2024 E1 gate is unchanged.
- New cards follow the cid convention `<prefix>:<kind>`: `:resistance-choice`, `:damage-type`, `:giant-type` (Strike of the Giants maps to a `spell_variants`-like pick), `:weapon-choice`, `:weapon-mastery`, `:fighting-style`, `:maneuvers`, `:metamagic`, `:invocation`.
- They are emitted by one new helper `_feat_extra_templates(feat, origin, catalog, ctx)`. It is called at **all five** feat template sites, and a matrix test covers background, species, FS, Lessons and ASI.
- Cards are feat-kind, so the existing page filters (by cid prefix) route them with **no frontend change**.
- Duplicate rules:
  - Fighting Initiate's style reads the S2/G1 `taken` name map ("already taken (Dueling, SRD)").
  - Elemental Adept repeats must pick distinct types: a later instance's option is disabled "already chosen for Elemental Adept (n)".
  - Weapon Master XPHB's mastery joins `sheet.weaponMasteries` (`annotate_mastery`). A weapon already mastered by a class card is disabled "already mastered".

### 4.5 Output surfaces

- **`derived`**:
  - `initiative`, `hitPointMax`, `speed`/`speeds`, `armorClass`, `passivePerception`/`passiveInvestigation` and `stealthDisadvantage` get the numbers. No new keys.
  - `derived.featResources` is the only new key (F-D1).
  - `derived.attacks` rows: notes, off-hand damage, the unarmed row, and Finesse via Revenant Blade.
- **`sheet`**:
  - `sheet.feats[].notes?: string[]` holds notes for effects not folded into numbers, with placeholders formatted.
  - `sheet.senses`, `damageModifiers`, `proficiencies`, `expertiseSkills` and `weaponMasteries` get the choice results.
- **Exports** (`export_fields.py`, mirrored by Markdown/PDF through `extra_blocks`):
  - the feat bullet appends `": " + choice` (existing) and `" — " + "; ".join(notes)`;
  - a new h2 "Ресурси от таланти" uses `resource_line` (reuse; feat resources share the shape);
  - YAML: `DERIVED_FIELDS += ("featResources", [])`.
- **`types.ts`**: `SheetFeat.notes?`, `Derived.featResources?: FeatResource[]` (shape = `ClassResource` with `featId` instead of `classId`, `source.kind: "feat"`). Attack rows are unchanged.
- **SPA** (plain): ExportPage lists the feats with their notes and renders `featResources` with `ClassResourcesList` (pass the list; the component already takes `resources`). The new feat cards render through the generic `ChoiceCard`.

---

## 5. Slices (smallest valuable first)

### FE0 Scan table, coverage ratchet and data guards (S, data and tests only, no behaviour change). Depends on nothing.

**Goal.** Encode section 3 so later slices fill a table instead of re-deriving it.

**Files.**
- New `server/catalog/feat_effects_data.py`: the vocabulary docstring, `FEAT_EFFECTS = {}` (FS feats keep using `CLASS_FEATURE_EFFECTS` and are listed as `data_only` with a pointer), and `FEAT_PENDING = frozenset(all 305 minus classified)`.
- New `server/tests/test_feat_effects_coverage.py`:
  - the ratchet asserts from 4.1;
  - data guards V2 (EB `max` 30, nobody else), V3 (no ASI on O/FS), the B5 `bonusSenses` holder, and B3 (the Echoing Soul data count);
  - a golden guard: the number of golden cases holding feats is 0 (FE12 updates it to its new count).

**Acceptance.** Suite +N tests, golden green, no `resolve()` change.

### FE1 Initiative, hit points, walk/climb speed (S–M). Depends on FE0.

**Files.**
- New `engine/feat_effects.py` with `instances`, `initiative_parts`, `hp_bonus`, `walk_bonus`, `climb_equals_walk`.
- `engine/derived.py::initiative(..., bonus=0, proficient=False)`. Defaults keep today's numbers.
- `resolve.py` derived block: build instances once after the final choices (near ~5261).
- Speed order: species walk → Unarmored Movement → Fast Movement → feat walk bonus → Gift of the Depths swim → Athlete climb.
- Data entries: `alert-phb`, `alert-xphb`, `tough-phb`, `tough-xphb`, `boon-of-fortitude-xphb`, `mobile-phb`, `speedy-xphb`, `boon-of-speed-xphb`, `squat-nimbleness-xge`, `mark-of-passage-efa`, `transmuted-anatomy-au`, `athlete-xphb`. Remove them from `FEAT_PENDING`.

**TDD matrix** (`tests/test_feat_effects_numeric.py`; quote each feat's sentence from the catalog):
- Initiative:
  - Alert PHB via mixed Fighter 4 ASI, DEX 14, PB 2 → 2 + 5 = 7.
  - Plus Bard 2 multiclass (JoaT SRD) → 2 + 1 + 5 = 8.
  - Alert XPHB via Criminal XPHB, 2024 Rogue 1 → 2 + 2 = 4.
  - Alert XPHB + mixed Bard 2 → 4, not 5.
  - Alert XPHB + mixed Champion 7 (RA ceil) → DEX + PB.
  - Alert XPHB at total level 5 → + 3.
  - Alert XPHB kept under ruleset 2014 (hidden) → still + PB.
- HP:
  - Tough XPHB via Farmer, Fighter 1, CON 14 → 12 + 2 = 14.
  - Fighter 5 → base + 10.
  - Tough PHB picked at Fighter 4 of Fighter 8 → + 16 (retroactive).
  - Tough + SRD Hill Dwarf → both add.
  - Fighter 4 / Wizard 3 with Tough → + 14.
  - Boon of Fortitude at 2024 Fighter 19 → + 40.
  - Manual HP mode → the feat still adds.
- Speed:
  - Mobile on Human 30 → 40.
  - Monk 6 + Mobile, unarmored → 30 + 15 + 10 = 55; in armor 40.
  - Barbarian 5 + Mobile → 50.
  - Speedy + Mobile (mixed) → both add.
  - Boon of Speed + 30.
  - Athlete XPHB on a 2024 Human → climb 30; with Mobile → climb 40.
  - Triton Barbarian 5 + Mobile → walk 50, swim 30 (walk-only, F1-6).
  - Gift of the Depths + Mobile → swim = walk including Mobile.
- No feat → identical (golden).
- Empty catalog → no crash.

**Changed expectations (on purpose).** The 2024 kitchen-sink drafts with Alert XPHB (initiative + PB). List every edited test in the commit message.

**Risks.** The kitchen-sink `_EXPECT` values; the shift from Gift of the Depths ordering is 2024-only and needs a test.

### FE2 Ability-score caps (S). Depends on FE0.

**Files.**
- `catalog/official/feats.py` (`ability_cap`);
- `engine/asi.py` (`cap` parameter);
- `resolve.py`: `_apply_asi_progression`, the origin-feat bonus loop (~4289–4373), `_feat_ability_bonus_choice_templates(scores=)`, and `_feat_prerequisite_problems` (applied delta).

**TDD** (`tests/test_feat_ability_caps.py`):
- 2024 Fighter 19, STR 20, Boon of Fortitude +1 STR → 21.
- The same at 30 → stays 30, and the option is disabled "already at maximum (30)".
- Resilient XPHB at a level where CON is 20 → no increase, option disabled.
- Mixed Variant Human, base STR 20 (manual), Athlete PHB STR → 20 (was 21: B2; a mixed change, allowed and listed).
- Custom Lineage + half-feat, same check.
- Background feat with no ASI → unchanged.
- The prerequisite self-bonus case still passes.
- A stored pick of a disabled option → `pruned`.
- 1–30 range problem unchanged.

**Risk.** The clamp must not touch the species/background ASI passes, which are not feats.

### FE3 Output surfaces: notes, `derived.featResources`, Lucky (M). Depends on FE1.

**Files.**
- `engine/feat_effects.py`: `notes(instances, numbers)` and `resources(instances, numbers)`, where numbers = modifiers, PB, total level, final scores and the increased-ability modifier.
- `engine/sheet_features.py::feats_summary(..., notes_by_instance)`.
- `resolve.py` `derived["featResources"]`.
- `export_fields.py` (feat bullet notes, the "Ресурси от таланти" block, `DERIVED_FIELDS`).
- `frontend/src/types.ts`, `frontend/src/pages/ExportPage.tsx` (plain list).
- `tests/test_c_series_golden.py`: `STRIP = ("derived.featResources",)` with the comment from section 0.

**Data.**
- Lucky PHB (3, long) and Lucky XPHB (PB, long).
- Notes for every PHB / XPHB General and Origin feat in section 3F (with numbers: Inspiring Leader, Heavy Armor Master, Durable, Chef, Musician, Healer, Defensive Duelist, Shield Master, War Caster, Mage Slayer, Sentinel, Skulker, ...).
- Mage Slayer XPHB Guarded Mind resource; Second Chance; Fade Away; Orcish Fury.

**TDD** (`tests/test_feat_resources.py`):
- Merchant XPHB, Rogue 5 → Lucky uses 3, long.
- Mixed Fighter 4 Lucky PHB → 3.
- Inspiring Leader XPHB with WIS picked, level 8, WIS 16 → note "8 + 3 = 11 Temporary Hit Points".
- Pending ability → "(choose the ability)".
- Export: the Markdown and PDF text contains the resource line and the notes; the YAML carries `featResources`.
- `test_types_drift` green.
- `test_export_fields` key test green.
- Golden green (with STRIP).

**Acceptance.** Browser check at 375px on ExportPage (Wayfarer XPHB Lucky).

### FE4 AC, passive scores, stealth, senses (S–M). Depends on FE3 (notes for the conditional cases).

**Files.**
- `engine/equipment.py::armor_class_from_gear(..., medium_dex_cap=None)` and `armor_warnings(..., medium_armor_stealth_ok=False)`.
- `engine/feat_effects.py`: `ac_formulas`, `ac_bonus(hands, items)`, `passive_bonus`, `senses_additive`.
- `resolve.py`: feat formulas join `features_mod.ac_formulas(effects)`; add passive bonuses after `passive_perception`; Keenness last in senses.
- Data: Dragon Hide, MAM PHB/XPHB, Dual Wielder PHB, Revenant Blade, Observant PHB, Keenness (`bonus_senses`).

**TDD** (`tests/test_feat_defense.py`):
- Dragon Hide, no armor, DEX 14 → 15; with a shield 17.
- Dragon Hide + Monk Unarmored Defense → best of the two.
- Dragon Hide in armor → armor.
- MAM: half plate, DEX 16 → 18; DEX 15 → 17 (score rule).
- MAM PHB → `stealthDisadvantage` false with half plate; MAM XPHB → stays true (V11).
- Dual Wielder with `wielded` longsword + shortsword → +1; with a shield → 0; no `wielded` → note.
- Revenant Blade with `wielded` main double-bladed scimitar and off-hand empty → +1 (V12).
- Observant PHB → passive Perception and Investigation +5; skills unchanged; Insight unchanged.
- Keenness on a no-darkvision species → 60; on a Dwarf → 120; Devil's Sight untouched.

### FE5 Attack rows (M). Depends on FE3.

**Files.**
- `engine/attacks.py`:
  - `attack_styles` gains feat flags (`offhand_non_light`, `offhand_light_crossbow`, `dw2024`, `finesse_items`);
  - `weapon_attack` reads them;
  - `unarmed_strike(..., feat_die=None, damage_type=...)`.
- `engine/feat_effects.py::annotate_attacks(attacks, items, instances, numbers, hands)`, which applies the predicate notes.
- `resolve.py`: the unarmed row is added when a feat grants it (merged with the Monk row: best die, others in notes; F-D6); call `annotate_attacks` after `class_resources_mod.annotate_attacks`.

**Data.** All 32 feats of section 3D.

**TDD** (`tests/test_feat_attacks.py`):
- Soldier XPHB Savage Attacker → note on every weapon row.
- PHB version → melee only.
- GWM XPHB, greataxe, PB 3 → "+3 damage (Heavy, Attack action)" note; `damage` unchanged.
- GWM PHB → "-5 attack / +10 damage" only on proficient heavy melee.
- Sharpshooter PHB on a longbow only.
- Crossbow Expert XPHB: the hand crossbow row gains `offhandDamage` with the modifier.
- Dual Wielder PHB: longsword row gains `offhandDamage` = dice + min(mod, 0); + mod with TWF.
- Dual Wielder XPHB: non-Light one-handed melee row gets off-hand; TWF adds mod (F-D5).
- Tavern Brawler XPHB on a Fighter → Unarmed Strike row 1d4 + STR, proficient.
- Unarmed Fighting → 1d6 + STR, with the note "1d8 with no weapon or Shield held"; with `wielded` both empty → 1d8.
- Monk 5 + Tavern Brawler → one row, the Martial Arts die wins, note.
- Dragon Hide claws → slashing 1d4 + STR.
- Revenant Blade → double-bladed scimitar uses DEX when better.
- Piercer, Slasher, Crusher by damage type.
- Polearm Master PHB vs XPHB item lists.
- No feat → rows identical.

**Changed expectations.** The 2024 kitchen-sink rows get the Savage Attacker note (list the edited `_EXPECT` strings).

### FE6 Skills and Expertise (S–M). Depends on FE0.

**Files.**
- `resolve.py` proficiency merge (~4972–5030):
  - cards marked `prof_or_expertise` (template key, stripped like `lacksExpertise`);
  - a selected skill already proficient at the feat's position (F-D4) goes to the expertise list instead of proficiency;
  - under 2024 it is also gated by "already has Expertise".
- `_gate_expertise_choices`: honour the feat flag `lacks_expertise` under every ruleset.
- Catalog override (B3: Echoing Soul `any: 2`) and the Harper Agent language (B4).

**TDD** (`tests/test_feat_skill_choices.py`):
- Keen Mind XPHB, History, Sage XPHB (History proficient) → Expertise.
- Arcana not proficient → proficiency.
- A later class skill grant does not convert (position).
- Observant XPHB Perception with species Perception → Expertise.
- Skill Expert TCE under mixed → option "already has Expertise" disabled for a Rogue Expertise skill.
- Prodigy, same.
- Echoing Soul → two skill picks.
- Harper Agent → Thieves' Cant in `sheet.proficiencies.languages`, and the language gate sees it.

**Risk.** C6b-2 language gate ordering for Harper Agent (an origin feat comes first).

### FE7 Resistance, damage-type and variant picks (S–M). Depends on FE3.

**Files.**
- `_feat_extra_templates` (new) at the five sites.
- Merge `:resistance-choice` picks into `chosen_resistances` (~5365).
- Scion `resist_by_variant` reads the `<prefix>:spell-variant` pick.
- The Elemental Adept type pick feeds notes ("spells ignore Resistance to fire; treat 1s as 2s").
- Strike of the Giants `:giant-type` drives the note and resource text.

**TDD** (`tests/test_feat_resist_choices.py`):
- Dragonscarred: 5 options, the pick reaches `damageModifiers.resistances`.
- Boon of Energy Resistance: count 2 of 9.
- Scion "Good Outer Plane" → radiant, with no extra card.
- Elemental Adept XPHB taken twice → the second instance's same type is disabled.
- A pending card blocks export like any other.
- Background / species / ASI origin matrix.

### FE8 Weapon picks (S–M). Depends on FE5.

**Files.**
- Weapon Master PHB `:weapon-choice` (count 4, Simple and Martial catalog weapons, ids via `weapon_proficiency_id`, V9). The picks feed `proficient_weapons` before the C2 mastery gate.
- Weapon Master XPHB `:weapon-mastery` (count 1, proficient weapons only, gated in `_gate_mastery_choices`). It joins `weaponMasteries`.

**TDD.**
- A Wizard with Weapon Master PHB picking longsword → longsword row proficient.
- Weapon Master XPHB on a Wizard: a non-proficient weapon is disabled; picking dagger → mastery Nick on the dagger row.
- Duplicate with a class mastery card → "already mastered".

### FE9 Option-pick feats (L). Depends on FE5 and FE7.

**Files.**
- `_feat_extra_templates` pools (V5–V8), reusing the Battle Master `_optional_progression_template` filter, the sorcerer Metamagic options, `_invocation_unmet` and `_srd_style_options`.
- Effects:
  - Fighting Initiate → append the option id to `_class_feature_list` (so `CLASS_FEATURE_EFFECTS` applies Archery/Defense/Dueling/TWF);
  - Eldritch Adept → `features.invocation_effects`-compatible input (selected id list), so Armor of Shadows / Devil's Sight / Beguiling Influence work;
  - Martial Adept → feat resource "Superiority Die (Martial Adept)", d6, short-or-long, dc 8 + PB + max(STR, DEX), note listing the maneuvers;
  - Metamagic Adept → 2 points, long, note listing the options.

**TDD.**
- Wizard 4 Fighting Initiate Defense, chain mail → AC + 1.
- An SRD Fighter with the Dueling style picking Dueling again → disabled "already taken".
- Eldritch Adept Armor of Shadows on a Wizard → AC 13 + DEX formula and the innate Mage Armor.
- An invocation with a prerequisite on a non-Warlock → disabled.
- Martial Adept on a Battle Master 3 → two separate resources.
- Metamagic Adept on a Sorcerer → separate 2-point pool.
- Each pick prunes when the feat is removed.

**Risk.** Origin-site coverage. The four feats are 2014 (`''` category), so they come via mixed/2014 ASI picks or Variant Human / Custom Lineage.

### FE10 Resource and note tail for the remaining books (M). Depends on FE3.

**Data.**
- Every section 3E resource not done in FE3, with uses/recharge from V4.
- Every 3F note for FRHoF, AU, EFA, ABH, RHW, DSotDQ, BGG, SatO, FTD, ERLW, PSK, SCC, BMT, MTF, PSX.
- Empty `FEAT_PENDING`.

**Tests.**
- The quote-pin test over all entries.
- A parametrized resolve over every feat that has resources: each is granted through a synthetic ASI or background patch and must produce a resource with the expected uses at PB 2 and PB 4. Use the existing patched-catalog pattern, since many feats have race/feat prerequisites.

### FE11 (optional, F-D8) Spell-grant tail. Skipped by default.

AU Adept slot-keyed spells, Potent Dragonmark extra slot (resource), Rune Shaper, Boon of Magic School Mastery, Magic Connoisseur list.

### FE12 Consolidation (M). Last.

1. **ARCHITECTURE.**
   - A "Feat effects (FE) overview" table.
   - Close open question 6.
   - Supersede the "Not modelled" sentences in C3, C7c and Slice 9 (feat attacks) and the Phase 4c "uncapped" disclosures.
   - Update Known gaps (TCE fighting styles / metamagic not imported; FE11 if skipped).
2. **Kitchen sink.** New drafts:
   - `feats-mixed-fighter12`: Variant Human PHB + Alert PHB; ASI Tough 4, Mobile 6, Lucky PHB 8, Observant PHB 12; MAM; Dual Wielder with `wielded`.
   - `feats-2014-rogue8`: Elven Accuracy, Skill Expert TCE, Weapon Master PHB.
   - `feats-2024-fighter19`: Farmer XPHB Tough, Human XPHB Alert, Speedy 4, GWM 6, Boon of Fortitude 19.
   - `feats-mixed-wizard8`: Fighting Initiate, Eldritch Adept Armor of Shadows, Martial Adept.
   - `test_export_fields` per-draft expectations: notes, resource lines, initiative, HP, speed.
3. **Golden.** Additive regeneration for the new non-2024 drafts only, with the script assert from section 0. Update the FE0 golden-feat-count guard.
4. **`test_types_drift`.** `UNTYPED_ALLOWLIST` stays empty.
5. **Review checklist (cross-slice).**
   - FE2 × prerequisite self-bonus.
   - FE1 × JoaT / Remarkable Athlete.
   - FE1 × F1-6 walk-only.
   - FE4 × G2 worn/wielded.
   - FE5 × S5 Dueling / G2 hands / C7c pact row.
   - FE6 × E1-revised 2024 gate and F3a-3 expertise order.
   - FE7 × S2 repeatables.
   - FE8 × C2 mastery gate order (F1-5).
   - FE9 × G1-3 SRD style duplicates and R6 Battle Master.
   - All × A2 hidden-kept picks.
   - All × the five feat template sites.
   - Golden byte-identical for the old cases.
6. **Re-timing.** Fighter 20, Monk 20, Wizard 20 (mixed and 2024) plus the four new drafts, each under 50 ms.
7. **Gates.** Final gates, frontend build, and a 375px check of ExportPage and ClassPage (Fighter 12 mixed feats, Wizard 8 option picks).

---

## 6. Global order (test gate after each)

FE0 → FE1 → FE2 → FE3 → FE4 → FE5 → FE6 → FE7 → FE8 → FE9 → FE10 → (FE11) → FE12.

FE2 and FE6 only depend on FE0, so they may move earlier if a reviewer prefers. The golden must stay green at every step: never regenerated before FE12, and then only additively.

## 7. Cross-cutting risks

- **The five feat template sites** (background, species, FS, Lessons, ASI). A missing call silently drops a card. One helper plus one origin matrix test.
- **Kitchen-sink 2024 drafts change on purpose** (Alert XPHB, Savage Attacker). Each slice lists edited expectations. The golden is unaffected.
- **"Increased ability" lookups** must reuse the existing `:ability-bonus` resolution, not a copy.
- **`resolve.py` size.** Logic goes into `engine/feat_effects.py`; `resolve()` only wires.
- **2014 data quirks** (Echoing Soul, Weapon Master's filter, unimported TCE options). Text wins, and each deviation is recorded.
- **Count-variable picks.** Rune Shaper's half-PB count (if FE11 is built) must be count-variable.

## 8. Side findings (out of scope, report only)

- **2024 Initiative.** XPHB Jack of All Trades applies only to checks using a skill proficiency you lack, so not to Initiative. XPHB Champion's Remarkable Athlete gives Advantage on Initiative instead of half Proficiency Bonus. The engine adds both half-bonuses to `derived.initiative` under 2024, because effects still read the SRD refs. A 2024-only fix; mixed/2014 are unchanged (F-D9).
- The 2024 Light property allows the extra attack with ranged Light weapons too. Today `offhandDamage` exists only for melee Light weapons; FE5 covers it only when Crossbow Expert XPHB is held.

### Critical Files for Implementation
- /Users/yoanpetrov/dnd-character-creator/server/engine/resolve.py (feat assembly ~4002–4488, origin-feat ASI ~4289–4373, `_apply_asi_progression` ~1168, `_resolve_asi_selected_feats` ~1275, feat template sites ~4443–4485, proficiency merge ~4972–5030, derived block ~5235–5347, senses ~5384)
- /Users/yoanpetrov/dnd-character-creator/server/engine/feat_effects.py (new) and /Users/yoanpetrov/dnd-character-creator/server/catalog/feat_effects_data.py (new)
- /Users/yoanpetrov/dnd-character-creator/server/catalog/official/feats.py (`ability_cap`, `bonus_senses`, data overrides), /Users/yoanpetrov/dnd-character-creator/server/engine/asi.py, /Users/yoanpetrov/dnd-character-creator/server/engine/derived.py, /Users/yoanpetrov/dnd-character-creator/server/engine/equipment.py, /Users/yoanpetrov/dnd-character-creator/server/engine/attacks.py
- /Users/yoanpetrov/dnd-character-creator/server/export_fields.py, /Users/yoanpetrov/dnd-character-creator/server/engine/sheet_features.py, /Users/yoanpetrov/dnd-character-creator/frontend/src/types.ts, /Users/yoanpetrov/dnd-character-creator/frontend/src/pages/ExportPage.tsx
- /Users/yoanpetrov/dnd-character-creator/server/tests/test_c_series_golden.py (STRIP in FE3, additive regeneration in FE12), /Users/yoanpetrov/dnd-character-creator/server/tests/kitchen_sink.py, /Users/yoanpetrov/dnd-character-creator/server/tests/test_export_fields.py, /Users/yoanpetrov/dnd-character-creator/server/tests/test_types_drift.py
