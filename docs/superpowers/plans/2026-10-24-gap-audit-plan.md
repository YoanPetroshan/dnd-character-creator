# Plan: gap audit follow-up (W series), after RP22

Opus planner audit of 2026-10-24 (read-only), condensed. Baseline when written: server 5132 passed, root 405 passed + 8 skipped, golden 241 cases, frontend builds.

## Decisions (user, 2026-10-24)

The user said: do everything I can verify myself; anything uncertain is DEFERRED until the user interrupts to ask. Open questions 1-4, 12, 21 residue, 23 (Mercy), 24 (Fighting Initiate) keep their current defaults and stay user-owned. TCE fighting styles for Fighting Initiate = NO. No visual design work.

Applied recommended defaults (RAW-backed; reversible; recorded so the user can overrule tomorrow): D-1 species resources also under mixed/2014 via `--rebaseline`; D-2 Breath Weapon-like traits are resources with DC and dice in `details` (not attack rows); D-3 heavy-armor speed penalty applies to derived speed under every ruleset (dwarf exemption per trait text); D-4 manual ability scores clamp to 1..30 with a non-blocking warning above 20.

DEFERRED (do not do without the user): D-5 deleting the legacy v1 root files (app.py, storage.py, sheet_derive.py, markdown_render.py, pdf_fill.py, templates/, static/, their root tests); D-6 adding pytest-xdist; D-7 rate limiting/auth; pushing commits; the real-device check; all user-owned open questions.

## Conventions

Same as docs/superpowers/plans/2026-10-22-remaining-program.md section 0: TDD (rule matrix quoting catalog text, quote-pin test per data entry), one Sonnet executor at a time, gates (server suite, root suite, `npm run build` if frontend touched; full runs are slow: run in background), one commit per slice, explicit `git add` paths (never `Resurses/`), dated ARCHITECTURE section per slice, `--rebaseline <SLICE>` with an allowlist whenever mixed/2014 output moves (never `--regenerate`; `--append` for new cases), new sheet/derived keys in `types.ts` + `export_fields.py` in the same commit, resolve() < 50 ms. Read-only Opus review after W4, W8 and W12.

## Findings (verified by the planner)

F1 Dwarven Toughness missing for official (5etools) dwarves: SRD_TRAIT_EFFECTS is keyed by SRD trait ids only (dwarf-xphb-trait-2, dwarf-phb-hill-phb-trait-0, dwarf-(kaladesh)-psk-trait-6, human-(innistrad)-psi-stensia-psi-trait-1 "Tough" lack hp_per_level). F2 no species trait with uses/numbers is a resource (157 traits with use/rest/HP text; Breath Weapon, Relentless Endurance, Adrenaline Rush, Stonecunning, Giant Ancestry, Large Form, Healing Hands, Celestial Revelation, Draconic Flight...). F3 heavy armor below its Strength requirement does not reduce speed (armor_warnings says "not applied to the sheet"); dwarves exempt (SRD dwarf, dwarf-phb), dwarf-xphb is not. F4 the 2014 class/subclass use-limit tail has no resources (18 SRD class features, 5 SRD subclass features, 117 non-SRD 2014 subclass features carry use-limit text). F5 three ruleset-2024 backgrounds grant no origin feat on the sheet (genie-touched-frhof, mist-wanderer-rhw, spirit-medium-rhw): VERIFY raw data. F6 ability scores not clamped (99999999999999999999 accepted). F7 class level 999 accepted (VERIFY). F8 non-object JSON body returns 200 (acceptable; optional 400). F9 one fill loop failed to settle in fuzz (seed 11, sorcerer+wizard 2024 with a random species/background): investigate. Fuzz baseline: 550 random drafts, 0 exceptions, idempotent. Legacy root v1 code is unused by v2 (deferred D-5). Requirements unpinned; data overrides lack a central registry with pins.

## Slices

### Batch 1: cheap, fully verifiable
- **W1 (F1, F3):** official-race Dwarven Toughness (+1 HP/level via trait id or name+quote match) and the heavy-armor speed penalty (-10 ft when STR < requirement; exempt SRD dwarf and dwarf-phb ("speed is not reduced by wearing heavy armor"); apply after all walk bonuses, floor 0; update the warning text). Golden: dry-run; rebaseline W1 if heavy-armor/dwarf cases move.
- **W2 (F6, F7, F8):** clamp base ability scores to 1..30 (non-numeric -> 10, problem `ability-out-of-range`; warning above 20), clamp class level 1..20 and report `level-total-over-20`, 400 for non-object body on /api/resolve and /api/export.
- **W3 (fuzz harness, F9):** server/tests/test_resolve_fuzz.py, seeded random.Random, N=60 default (FUZZ_N for more, slow marker); properties: no exception, resolve idempotent, kitchen_sink.fill settles within 10 rounds (print seed + oscillating cards), mutations (level-down, class reorder, ruleset/species switch) never crash and stale picks land in pruned/problems, exports return 200 on 10 settled drafts, slowest resolve < 50 ms. Reproduce F9, fix its root cause in its own commit, keep the seed as a regression case.
- **W4 (F5):** the three backgrounds without feat: VERIFY raw feats shape; convert if dropped by the converter, else pin "no feat by data". Then Opus review.

### Batch 2: species fidelity
- **W5a:** `derived.speciesResources` (new key, in types.ts/exports/SPA list) from a `SPECIES_RESOURCES` table keyed by trait id with quote pins: XPHB Breath Weapon (PB uses, long rest, DC 8+CON+PB, dice by level - VERIFY), Draconic Flight, Adrenaline Rush, Relentless Endurance, Stonecunning, Giant Ancestry (picked boon numbers), Large Form, Healing Hands, Celestial Revelation, Luck/Resourceful notes.
- **W5b:** 2014 species: first commit SRD (Dragonborn Breath Weapon with DC, Half-Orc Relentless Endurance, Halfling Lucky note), second commit the PB-uses traits from the 157-trait scan (only numbers present in the text; list the rest). Golden: VERIFY whether any golden case uses these species; else `--append` a dragonborn case; rebaseline if they move.

### Batch 3: 2014 class/subclass tail
- **W6/W7:** `RESOURCE_TAIL_2014` and `SUBCLASS_TAIL_2014` mirroring RP10/RP11 (`_render_note` machinery), gate ruleset != 2024, SRD ids: Stroke of Luck, Cleansing Touch, Eldritch Master, Song of Rest die, Brutal Critical dice, Wholeness of Body, Quivering Palm, Dark One's Blessing / Own Luck, Hurl Through Hell, Preserve Life, Disciple of Life, Divine Strike dice, Holy Nimbus, Overchannel, Potent Cantrip / Empowered Evocation, Sacred Weapon, Frenzy. Rebaseline W7 over the SRD subclass golden cases.
- **W8 (a-d):** the 117 non-SRD 2014 subclass features by class, only numbers present in the text; rebaseline per commit if kitchen sinks move. Then Opus review.

### Batch 4: quality
- **W9:** export completeness audit: a test walks every sheet/derived leaf on KITCHEN_SINK drafts and asserts it appears in Markdown and PDF text or is in an explicit EXPORT_OMITTED allowlist with reason; PDF long-list page breaks, no cell-edge cut text, Cyrillic/× glyphs for new keys.
- **W10:** frontend functional audit (no visual work): resolve failure shows an error line + retry keeping last good resolution; draft upload parse/version errors; ErrorBoundary on all routes; labels/keyboard; stale-selection clearing; localStorage quota handling; long lists; tap targets via min-height only; browser pass at 375px and desktop incl. server-stopped state.
- **W11:** hygiene: pin server/requirements.txt (direct deps from .venv), root requirements.txt -> `-r server/requirements.txt`, VERIFY frontend/package-lock.json committed; DATA_OVERRIDES registry in reference_data.py with a test per override asserting the raw defect still exists; README update.
- **W12:** test-suite health (durations, slow markers, skip counts, modules without tests), ARCHITECTURE W overview, Known gaps, final Opus review.

## Not worth doing
Conditions/exhaustion/death saves/current HP tracking (play state); variant encumbrance; starting-gold wealth roll; magic items/attunement (no data); Wild Shape forms / Beast Master stat blocks (no data); per-attack rider options; generated TS types; frontend unit-test framework.
