# Plan: backend completion (Opus planner, 2026-11-05, HEAD 32ab489)

Condensed from the planner report. Sequential execution only (one Sonnet executor at a time; engine/resolve.py, catalog/reference_data.py, engine/class_resources.py and the golden are shared).

## Facts from the probes
- 2014 Hunter picks are cards already (hunters-prey, defensive-tactics, multiattack, superior-hunters-defense) but the picked option produces no resource/note; same for Totem Warrior Elk (no DC). 2024 Hunter already does it (RP13 SUBCLASS_PICKS_2024).
- Four Elements disciplines and Rune Knight runes are cards; cost/uses are not tied to the pick.
- 2014 Sorcerer: `sorcery-points` has `details.slotCosts` only, no metamagic costs.
- PHB Dragonborn: only the resistance pick; Breath Weapon has damageType None and a note; the 10-row Draconic Ancestry table is in the PHB race entry (area/save are data-backed, damage type alone does not pick the dragon).
- tiefling-phb 2014 innateSpells lacks the Thaumaturgy cantrip (candidate finding; verify).
- VC0 has not started (`server/tests/tools/` absent).

## Global rules for every slice
Sequential. TDD (rule matrix quoting the data/book first; quote-pin test per new reference_data entry). Golden: dry-run first; mixed/2014 moves need append-only `REBASELINES["<slice>"]` with a path regex written from the rule, `--rebaseline <id> --dry-run`, then real; update the tuple pin test; new cases via `--append`; NEVER `--regenerate`; 2024-only changes stay behind ruleset == "2024". Other frozen artifacts (messages_en_snapshot, export_baseline, service_baseline, O1 Node test) are handled explicitly. Every new message/label: en+bg catalog entries (T1 rule: Bulgarian + English in brackets). New sheet/derived keys go into types.ts and export_fields.py (W9 audit) in the same commit. resolve() < 50 ms. Gates: server `-n auto`, `env DND_OFFICIAL_DATA=none`, root suite, `npm run build` + vitest if types.ts changes. Each slice: dated ARCHITECTURE section, one commit with explicit paths, no push.

## (A) Needs no owner input (order: T0 -> T0b -> G1 -> G2 -> G3 -> G4 -> G6 -> G5 -> G7 -> G8)
- **T0 (S)** snapshot rebaseline tooling: `i18n_zoo.py --rebaseline <SLICE> [--dry-run]`, append-only `SNAPSHOT_REBASELINES {cases, paths regex, why}` mirroring the golden tool; tests: unlisted change fails, listed change writes, cases never removed, tuple pin.
- **T0b (S)** test hygiene: move the flaky `test_resolve_stays_as_fast_as_with_the_srd_only_catalog` to perf_helpers; silence the Y2 allowlist FutureWarning via a test warnings filter (do not edit the existing REBASELINES entry).
- **G1 (M)** 2014 Hunter and Totem Warrior pick effects as note-only subclass resources (mirror RP13; Colossus Slayer once per turn, Giant Killer, Horde Breaker, Multiattack Defense, Uncanny Dodge / Stand Against the Tide, Volley/Whirlwind; Elk Totemic Attunement DC 8 + PB + STR only where the text gives it). Golden: REBASELINES["G1"] for ranger primaries; --append a totem-elk14 case.
- **G2 (S)** 2014 Metamagic costs: `sorcery-points details.metamagicCosts` for picked options; verify whether Seeking/Transmuted Spell are imported (20 MM records). Golden: REBASELINES["G2"] sorcerer cases.
- **G3 (S)** merged Cleric+Paladin Channel Divinity keeps both notes; Divine Intervention 7-day lockout note (2014) and Greater Divine Intervention note (2024). Golden: REBASELINES["G3"] cleric 11/20.
- **G4 (M)** irregular recharges (Limited Wish, Necrotic Husk "1d4 long rests" -> recharge other); Power Surge as a resource; Four Elements discipline ki costs in Ki details; Rune Knight runes as resources (1 use, 2 at Fighter 15; DC from Rune Magic). Lunar phase stays a note (Q17).
- **G6 (S/M)** innate spells: additive `usesMax` and `recharge` parsed from the uses text; verify the PHB Tiefling Thaumaturgy cantrip. Golden: REBASELINES["G6"] `^result[.]sheet[.]innateSpells[[][^]]+[]][.](usesMax|recharge)$`.
- **G5 (M)** FRHoF Banneret/Moon/Scion of the Three innate blocks (2024 only); Magic Connoisseur follows Magic Initiate variant; Rune Shaper and Boon of Magic School Mastery only where the data gives a literal list; others stay notes.
- **G7 (S/M)** Haunted One / Investigator either-or: first verify the RHW records; if text-only, move to (B).
- **G8 (S, optional)** remove the two dead i18n re-check sites (`level-unsupported`, `ability-invalid-*`); lower the zoo floor.
- **G9 (M, optional, last)** split 2014 tables out of reference_data.py into reference_data_2014.py (pure refactor; every baseline byte-identical; update the offline build manifest test if it lists files).

## VC verification campaign (final quality gate)
VC0 harness `server/tests/tools/chartest/` (spec.py, matrix.py, checks.py oracle independent of the engine except resolve, weird.py, cli.py; harness tests) -> T3 (~60 targeted) -> T4 (9 three-class) -> T2 (150 two-class) -> T1 (180 single-class), cap 600. One Sonnet tester per 10 specs; findings.jsonl S1/S2/S3; Opus deep review of every 5th character, every unclear finding and ~20% of oracle findings. Stop: a tier stops after 3 batches with no new S1/S2; pause at >= 5 open S1. VF<n> fix slices: failing spec becomes a pytest in `tests/test_campaign_regressions.py` first; mixed/2014 changes need REBASELINES["VF<n>"]; oracle bugs are fixed in the harness; unclear rules go to "Campaign deferred". Order: after (A) and the owner-approved (B) slices, then regression rerun, then G9, then final consolidation (ARCHITECTURE headline, Known gaps rewrite, read-only Opus review).

## (B) Needs an owner decision (question; default)
1. B1 PHB Dragonborn: add a "dragon colour" card so breath shape/save are correct? Default YES (golden dragonborn6-2014 moves via REBASELINES["B1"]).
2. B2 species/feat resources out of the golden STRIP (guard them)? Default YES, done before B1/G6 if approved.
3. B3 Ravenloft prerequisite on Dark Gift feats: warn / enforce / ignore? Default warn only when RHW is off.
4. B4 Thirsting Blade extra attack: note on the pact weapon row or part of the attack count? Default note.
5. B5 Q3/Q4: negative CHA with Agonizing Blast subtracts (RAW); Tireless uses = max(1, WIS). Default keep.
6. B6 Greater Dragonmark feat spells: model? Default no.
7. B7 Dockerfile untested: delete or CI-test? Default delete unless Flask will be hosted.
8. B8 D-7 auth/rate limiting: will the Flask server be public? Default no -> deferred.
9. B9 Wild Shape forms / Beast Master companion (needs a bestiary import)? Default no.
10. B10 per-attack riders (Brutal Strike, Cunning Strike...) as attack-row options? Default no (notes).

## (C) Stays deferred / closed
Fighting Initiate six SRD styles under 2024 (Q24) and Mercy replacement skill (Q23): closed by owner (2026-10-24). One-rest choices (Planar Adaptation, Lunar phase): Q17. Resource id reuse across rulesets. Species/Class pages senses block, Q12: frontend/design phase. O4 PWA and O5 hosting + CI: frontend/hosting (offline plan). SK11 random picks, link sharing: cancelled. Conditions, current HP, encumbrance variants, magic items: out of scope (play state).
