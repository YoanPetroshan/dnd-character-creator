# Architecture: known gaps and open questions

_What a reader should not mistake for a bug, and the design questions with their status (answered ones keep their recorded answer). Moved verbatim._

## Known gaps / things a fresh reader should NOT assume are bugs

- **CLOSED by RP14 (2026-10-23):** the SPA now renders `sheet.senses`, `damageModifiers`, `conditionImmunities` and `innateSpells` (Export page, `SheetTraitsSummary`). Statements elsewhere that the SPA shows none of them are superseded; the Species and Class pages still show no such block.

- **Known gaps after RP22 (2026-10-23), the real remaining list** (everything else the older bullets name is closed or superseded):
  - **Closed by the W series (2026-10-24 .. 11-03), no longer gaps:** F1 Dwarven Toughness for official dwarves (W1); F2 species trait resources, `derived.speciesResources` (W5a / W5b, 56 book traits plus the SRD ones); F3 heavy armor below its Strength requirement lowers speed by 10 ft, dwarves exempt by trait text (W1); F4 the 2014 class / subclass use-limit tail (W6 SRD classes, W7 SRD subclasses, W8 book subclasses, WG fixes); F5 the three backgrounds without an origin feat (W4: Genie Touched restored, Mist Wanderer and Spirit Medium get a Dark Gift pick); F6 / F7 / F8 ability scores clamp to 1..30, class levels are verified (an out-of-range level gives `level-unsupported` and falls back to level 1; there is no clamp), non-object bodies are a 400 (W2); F9 the non-settling fill (W3: a species feat grant whose feats are all hidden by sources is `unavailable`); the fuzz harness (W3), the export completeness audit (W9), the frontend functional audit (W10), pinned dependencies and the DATA_OVERRIDES registry (W11), tests that assume the 5etools data now skip without it (W12). Stale statements elsewhere in this file that call these open are history.
  - Wild Shape known forms and the Beast Master companion stat block are not in the data (a label / count only).
  - Per-attack riders (Brutal Strike, Cunning Strike, Tactical Master, Eldritch Smite, Lifedrinker, Thirsting Blade attack count) are notes, not attack-row options.
  - Choices that last one rest (Planar Adaptation, Zhentarim Tactics and similar) are notes, not editable cards (decided: they stay notes).
  - Feat spell riders of the Greater Marks of Detection / Finding / Passage / Storm / Sentinel / Scribing / Hospitality / Handling, Potent Dragonmark's preparation, Rune Shaper, Boon of Magic School Mastery, Magic Connoisseur and Seeking / Transmuted Spell metamagic are notes or absent.
  - XPHB subclass `innate` only for the seven records of RP18; FRHoF (ruleset 2024, not XPHB) Banneret / Moon / Scion of the Three innate blocks are not read. **Superseded by G5 (2026-11-06): Banneret and Moon are read; Scion and the cantrip picks stay unmodelled.**
  - Fighting Initiate keeps the six SRD styles under 2024 (see question 24); Mercy has no replacement skill card (question 23).
  - Species and Class pages show no senses / damage-modifier block (only the Export page does, RP14).
  - No automated frontend tests (build + the 375 px browser checks only); the real-device checks are in `REAL-DEVICE-CHECKLIST.md`.
  - **Deferred by the gap-audit batch (W1-W5b, WF), nothing here is guessed:** (a) Haunted One / Investigator (RHW) either-or "Survivor / Sharp Eye or a Dark Gift feat": no Dark Gift card (W4; **done by G7, 2026-11-06**); (b) CLOSED by X2 (2026-11-03): per-turn / per-combat / per-rage limits are a recharge value, see "X2" (Lucky Footwork has no limit text and stays a note); (c) innate-spell use tracking (species / feat innate spells show uses text only); (d) the PHB Dragonborn Breath Weapon save and area need a real Draconic Ancestry pick (the PHB species has only the resistance pick), so they stay a note; (e) the Ravenloft prerequisite on Dark Gift feats is not checked; (f) CLOSED by X1 (2026-11-03): fly speeds banned in armor by the species text are removed, see "X1"; (g) taking `speciesResources` out of the golden `STRIP` tuple is a policy change for the user.
  - **Deferred by W6-W8 (nothing guessed):** (a) 2014 Metamagic option costs are text only, no resource wiring; (b) a merged Cleric + Paladin Channel Divinity keeps only the winning class's note; (c) the Divine Intervention 7-day lockout is note-only; (d) Hunter picks (Hunter's Prey, Defensive Tactics, ...) and the Totem Warrior Elk DC are not read; (e) untracked picks: the Lunar phase, the Four Elements disciplines, runes; (f) the 1d4-long-rest recharges (Limited Wish, Necrotic Husk) have no recharge value; (g) Power Surge is a note-only entry (its pool resets to one, not to the maximum); (h) id reuse across rulesets: the W6 shared ids `barbarian:relentless-rage`, `monk:slow-fall`, `monk:stunning-strike`, `cleric:divine-intervention`, `rogue:stroke-of-luck` have a different shape under 2014 and 2024, which matters only if a client keys stored state by resource id; (i) splitting the 2014 tables out of `reference_data.py` (5425 lines) is an optional follow-up.
  - **Explicit deferred list (gap audit, as of W12; nothing here is guessed):** Haunted One / Investigator Dark Gift either-or card; (per-turn / per-combat riders closed by X2) innate-spell uses tracking; the PHB Dragonborn Breath Weapon save and area; the Ravenloft prerequisite on Dark Gift feats; `speciesResources` in the golden `STRIP` tuple (policy change); 2014 Metamagic option costs; Hunter picks and the Totem Warrior Elk DC [Superseded: done 2026-11-05, see "G1"]; splitting the 2014 tables out of `reference_data.py`; **D-5** deleting the legacy v1 root files (app.py, storage.py, sheet_derive.py, markdown_render.py, pdf_fill.py, templates/, static/, their root tests) [Superseded: done 2026-11-03, see "D5"]; **D-6** adding pytest-xdist (W12 measured what it would save, see "W12") [Superseded: done 2026-11-03, see "D6"]; **D-7** rate limiting / auth; pushing the commits; the real-device check.
  - The remaining design questions are the "Still open" list in "Open design questions" and the "Open questions for the user" paragraph at the end.

- **Added by FE12 (2026-10-12), feat known gaps. Superseded by RP22 (2026-10-23), see "Known gaps after RP22" above:** TCE fighting styles stay out (decided: a DM-permission rule, Extra 5 = no); Seeking / Transmuted Spell metamagic are still not imported; XPHB invocations ARE now in Eldritch Adept's pool under ruleset 2024 (RP20); the FE11 spell-grant tail is mostly resolved (Arcane Adept tables RP19, Marks' spells RP19; Rune Shaper, Boon of Magic School Mastery, Magic Connoisseur and Potent Dragonmark's preparation stay notes).

- **Added by F3b (2026-10-11), the 2024 chassis known gaps. Superseded by RP22 (2026-10-23):** the E11 2014 counterparts (RP7, RP15, RP16, RPX1), the E12 background placeholder items (RP9) and the E13 subclass build-time choices (RP12, RP13, RP17, RP18) are DONE. Still true: Wild Shape forms (a count and note only), per-attack options (Brutal Strike, Cunning Strike, Tactical Master, Eldritch Smite and Lifedrinker damage on rows are notes, not attack-row options).

- Frontend `types.ts` types are hand-maintained, not generated — they periodically drift from the real backend shape until a review catches it. **Superseded (F3a-10, extended by RP22): a structural guard exists**, `server/tests/test_types_drift.py` (resolved keys of the sheet, derived, choices, attacks, resources, features, feats, spells, innate spells, and since RP22 the equipment entries, weapon masteries, carrying capacity and always-prepared / spellbook rows, over EVERY kitchen-sink draft and every class at 5 / 11 / 20; `UNTYPED_ALLOWLIST` empty). It checks key names only, not value types.
- No automated frontend test suite exists — all frontend verification is `tsc` type-checking plus manual/browser checks.
- The `_class_label()` string-formatting helper is intentionally duplicated (not shared) between `markdown_export.py` and `pdf_export.py`, matching this project's established convention of these two files mirroring each other's content-selection logic independently rather than sharing a common renderer.
- `sheet.proficiencies.armor/weapons/tools` now render in `markdown_export.py`/`pdf_export.py` ("Владеене" section) — closed in the follow-up cleanups below.
- ~~A secondary class showing its level-1 proficiency card~~ — CLOSED (verified 2026-10-09 with Bard, Ranger, Rogue and Wizard as the second class): a secondary class offers only its `multi_classing.proficiency_choices` (`class:<id>:multiclass-prof-choice-N`; Bard has two, Ranger and Rogue one, Wizard none), never the level-1 `prof-choice-0` card.
- ~~Slot-selection logic split between resolve.py and spells.py~~ — CLOSED (Slice 12): `spells.spell_slots_for(catalog, [(class_id, level)])` returns the shared pool and the Warlock pool; `resolve()` just calls it.
- **`Resolution.pruned` count-shrink staleness for spell choices — CLOSED (2026-10-08).** A spellcaster's cantrip/known-spell selections that no longer fit (level-down, a lower casting modifier, or spells above the class's highest slot level) are truncated to the first N valid ones and reported as a non-blocking `pruned` entry (`_is_count_variable_choice` in `resolve.py`) instead of a blocking `over-selected-*` problem. Other choices keep the blocking `over-selected` behavior.

## Open design questions (consolidated 2026-10-10; final reconciliation 2026-10-23, RP22)

**Superseded: the lists that stood here (F3b, 2026-10-11) and the per-slice "Resolved" tags are replaced by this reconciliation. The numbers below are the numbering of the former "Still open" list (1-22); the one-line "Closed" list that sat above it used an OLDER numbering and is kept in the next paragraph by name only.** Nothing is guessed: a question stays open only when the books and data cannot settle it.

Closed in the older numbering, by name (G1 / G2 / E-series, 2026-10-10 / 11): Channel Divinity multiclass (G1-1), Elk / Tiger source filter (G1-4), Armor of Shadows vs worn armor (G2), SRD Fighting Style vs same-named feat (G1-3), Wild Heart per-rage options (G1-7), Ranger 2024 Natural Explorer (C6b-1), repeatable feats (G1-2), Arcane Warrior (G1-5), spell-slot note in the SPA (G1-6), E1-E10 and E14 (answered 2026-10-10, built).

### Status of every question 1-22 (final)

| # | Question | Status | Where / owner |
|---|---|---|---|
| 1 | Thaumaturge and Magician Arcana bonuses stack | **Closed by decision** (2026-10-24, Q1): they stack, keep | user answer, no change (C6a) |
| 2 | Weapon Mastery per class in a multiclass (same weapon twice) | **Closed by decision** (2026-10-24, Q2): a card per class, keep | user answer, no change (C2) |
| 3 | Agonizing Blast / Potent Spellcasting with a negative CHA / WIS modifier | **Open**, default = negative stays (RAW "add your modifier") | user, low priority (R8, C6c-2) |
| 4 | Tireless: `max(1, WIS modifier)` for uses and the 1d8 + modifier note | **Open**, default = as built | user, low priority (R9) |
| 5 | Repeat-instance renumbering of invocations | **Closed**, RP21 (decision D3) | picks follow the instance, "RP21" |
| 6 | Feat effects on derived stats | **Closed**, FE0-FE12 | "Feat effects (FE) overview" |
| 7 | Notes-only features (Evergreen Wild Shape, Perfect Focus, Superior Inspiration ...) | **Closed**, RP10 + RP11: numbers are notes on the resources, the 173 XPHB class features were re-read; what has no verifiable number stays a feature line by design | "RP10", "RP11" |
| 8 | 2024 pack contents | **Closed**, RP8 (PHB 2024 contents and weight); the SRD packs under mixed / 2014 weigh their contents since RPX2, `contents` is not shown there | "RP8", "RPX2" |
| 9 | E11, the 2014 counterparts | **Closed**: Monk tool RP7, Spell Mastery / Signature Spells RP15, Magical Secrets RP16, Lore Bard Bonus Proficiencies + Additional Magical Secrets RPX1 | "RP7", "RP15", "RP16", "RPX1" |
| 10 | E12, background placeholder items | **Closed**, RP9 (real catalog items with quantities under 2024; the gaming-set picks are cards) | "RP9" |
| 11 | E13, 2024 subclass build-time choices | **Closed**: proficiency picks RP12, option cards RP13, spell picks RP17, innate spells RP18; the two judgment calls that remain are questions 23 and 24 | "RP12", "RP13", "RP17", "RP18" |
| 12 | Naming and UX of the `unavailable` status | **Open**, UX only (checked at 375 px in F3b and RP22: never blocks export) | user, with the visual design pass |
| 13 | Cult of the Dragon Initiate replacement language | **Closed**, RP3 | "RP3" |
| 14 | Arcane Adept slot-keyed tables | **Closed**, RP19 (tables resolved against the highest slot level, Spells of the Mark added) | "RP19" |
| 15 | Eldritch Adept target-cantrip cards | **Closed**, RP20 (2024 only; the sub-question about Fighting Initiate is question 24) | "RP20" |
| 16 | 2024 Fighting Style feat card vs a Fighting Initiate style | **Closed**, RP4 | "RP4" |
| 17 | Choices that last one rest are notes | **Closed by decision** (2026-10-22): they stay notes | plan Decisions |
| 18 | Martial Adept d6 separate from Battle Master dice | **Closed by decision** (2026-10-22): a separate resource | plan Decisions |
| 19 | Monk with Unarmed Fighting / Tavern Brawler uses the better of STR / DEX | **Closed by decision** (2026-10-22): keeps the better | plan Decisions |
| 20 | Weapon Master (PHB) offers Musket and Pistol | **Closed by decision** (2026-10-22): keeps them | plan Decisions |
| 21 | Cross-feat modifications beyond FX3 | **Partly closed**, RP5 (Greater Mark of Healing / Making / Shadow, shared spellcasting ability); the spell riders of Detection / Finding / Passage / Storm / Sentinel / Scribing / Hospitality / Handling and Potent Dragonmark's slot stay notes | user, only if wanted |
| 22 | Silent clamp of other ability increases | **Closed for 2024** (RP1: a background increase cannot raise a score above 20, the lost part is a `pruned` entry; FX7 does the same for feats); **by design** under mixed / 2014 (a species / background bonus is never clamped) | "RP1", FX7 |

### Still open (genuinely)

1. to 4. and 12. and the residue of 21, as in the table (all user-owned; the defaults are what the engine does today).
23. **Mercy replacement skill** (RP12; **decided 2026-10-24, Q3: no replacement card, keep**): the XPHB Implements of Mercy text ("You gain proficiency in the Insight and Medicine skills and proficiency with the Herbalism Kit.") has no replacement clause, so a Mercy grant after an earlier pick of the same skill is listed once and no "choose another skill" card appears. Owner: user (a replacement card needs a rule that is not in the catalog text).
24. **Fighting Initiate under ruleset 2024** (RP20; **decided 2026-10-24, Q4: explained, the default of six SRD styles stays**): it keeps the six SRD styles; the 2024 Fighting Style FEATS exist (category FS, XPHB) but they are feats with their own effects and prerequisites, not option records, so offering them inside a feat was NOT done. Owner: user.

### Answers of 2026-10-24 (Q1-Q5 of the gap audit)

| Q | Question | Answer | Where |
|---|---|---|---|
| Q1 | Thaumaturge and Magician Arcana bonuses | stack, keep (question 1 closed) | C6a |
| Q2 | Weapon Mastery per class in a multiclass | a card per class, keep (question 2 closed) | C2 |
| Q3 | Mercy replacement skill | no replacement card, keep (question 23) | RP12 |
| Q4 | Fighting Initiate under 2024 | explained; the default (the six SRD styles) stays, SRD styles kept (question 24) | RP20 |
| Q5 | Per-turn / per-combat riders | stay notes, no resource kind, keep. **Superseded by X2 (user approved 2026-11-03): recharge values `turn` / `combat` / `rage` / `other`** | W5 / Known gaps / X2 |

Still open and user-owned after these answers: questions 3, 4, 12 and the residue of 21.

Also decided (Extras, 2026-10-22, not questions any more): Extras 1-4 (RPX1-RPX4) are built; Extra 5 (TCE fighting styles for Fighting Initiate under mixed) = NO, a DM-permission rule.
