# Phase 4 — Full Sourcebook Integration (Races & Backgrounds): Design

**Revision note:** this spec originally proposed a reduced-fidelity ("descriptive text only" for most traits) scope. The user explicitly rejected that: "искам всичко да е вътре... измисли как... това беше задачата от началото" (I want everything in there — figure out how — this was the task from the beginning). This revision targets **full mechanical fidelity**, grounded in a second, deeper empirical pass over the real fetched data that found the data supports it — the original "traits are just free text" read was wrong; most mechanically-relevant traits DO have structured fields, just not the exact ones SRD uses.

## Context (unchanged from the first pass)

The v1 archive (`chargen/`) already has infrastructure for fetching the wider, multi-sourcebook official dataset via `chargen/sync.py --official`, from `5etools-mirror-3/5etools-src` (MIT-licensed). Already fetched on this machine: `~/.claude/dnd/.data/official/races.json` (160 races) and `backgrounds.json` (161 backgrounds), spanning ~20 sourcebooks.

**Still the load-bearing architectural finding:** v1's `chargen.catalog.Catalog` converts this into its own dataclasses, incompatible with v2's engine (which reads raw SRD-JSON-shaped dicts directly throughout `catalog/choices.py`/`engine/resolve.py`). The task is new v2-native normalizers targeting the SAME dict shape the engine already consumes — reusing `chargen.sources.official_dir()`/`has_official()` (pure path helpers, no object-model coupling) but NOT `chargen.catalog`'s dataclasses.

## What the second empirical pass found (correcting the first pass)

Scanned every key that appears across all 160 race records and all 161 background records (not just one sample record, which is what led to the too-pessimistic first read). Real, structured, machine-parseable fields exist for nearly everything:

**Races** (field name → record count out of 160 → shape, confirmed against real records):
- `ability` (74) — fixed bonuses AND `{"choose": {"from": [...], "count": N}}` shapes (6 records) — same conceptual pattern as SRD's `ability_bonus_options`, already solved for Half-Elf in Phase 3b.
- `skillProficiencies` (60) — `[{"intimidation": true}]`, a boolean-map, same shape as `languageProficiencies` (75, already need to convert this shape today).
- `toolProficiencies` (10), `weaponProficiencies` (5), `armorProficiencies` (1) — same boolean-map shape, sometimes with an `{"any": N}` "choose N of any" wildcard instead of named items.
- `resist` (38) / `immune` (5) / `vulnerable` (1) / `conditionImmune` (7) — plain string lists of damage/condition types (e.g. `["necrotic", "radiant"]`).
- `additionalSpells` (30) — innate spellcasting, e.g. `{"innate": {"3": ["gust of wind"]}, "ability": {"choose": ["int", "wis", "cha"]}}` — a spell known innately starting at a given character level, cast using a (sometimes player-chosen) ability.
- `speed`, `size`, `darkvision` — scalar fields, map directly onto v2's existing Race shape.
- `entries` — free-text trait descriptions (Age/Size fluff mixed with real traits) — used as the DISPLAY text for every trait, structured or not; a trait with no matching structured field above still shows here, just grants nothing mechanical (a genuinely rare residual case now, not the common case the first pass assumed).

**Backgrounds** (field name → record count out of 161):
- `skillProficiencies` (136), `toolProficiencies` (114), `languageProficiencies` (56) — same boolean-map shapes as races.
- `startingEquipment` (134) — an `{"a": [...], "b": [...]}` package-choice shape (a fixed gear package vs. a gold-value alternative) — conceptually the same "choose one starting-equipment envelope" pattern `_equipment_choice_templates` already handles for SRD, needs its own shape-specific conversion.
- `ability` (60) — **background-granted ability score bonuses, including a `{"choose": {"weighted": {"from": [...], "weights": [...]}}}` shape** (2024-ruleset backgrounds grant ability bonuses; 2014 ones don't — confirmed this is why `resolve.py`'s existing comment says "backgrounds don't grant ability bonuses in this ruleset," a true statement about 2014 content that stops being universally true once 2024-sourced backgrounds are imported).
- `feats` (74) — background-granted feats. **v2 has no Feat concept anywhere in the Draft/Resolution model today.** This is a genuinely new game mechanic, not an extension of an existing one.
- `additionalSpells` (15) — same innate-spellcasting shape as races.

## Revised scope: full fidelity, decomposed into sub-phases

Given the real size of "full fidelity" (comparable to or larger than Phase 3b's multiclassing effort), this follows the same established pattern: one spec (this document), multiple sub-phase plans, each its own SDD cycle.

- **Phase 4a — Races & subraces, full fidelity.** Ability bonuses (fixed + choice), speed, size, darkvision, languages, skill/tool/weapon/armor proficiencies (fixed + `{"any": N}` choice), damage resistances/immunities/vulnerabilities, condition immunities, innate spellcasting, trait display text. Every mechanical dimension the data supports for races.
- **Phase 4b — Backgrounds, full fidelity EXCEPT feat-granting mechanics.** Skill/tool/language proficiencies, starting equipment (package-choice shape), background-granted ability bonuses (the 2024 mechanic — extends `resolve.py`'s existing 2014-only ability-bonus pipeline to also read background-sourced bonuses when present, not just species-sourced ones), innate spellcasting, trait display text. Feat-GRANTING data is imported and stored (not silently dropped) but its MECHANICAL EFFECT is inert until Phase 4c exists — matching this project's established "known field, structured for later completion" pattern (e.g. how several Draft fields have existed unused since Phase 0 until their consuming phase arrived).
- **Phase 4c — Feats as a first-class mechanic.** A genuinely new concept: a Feat has its own prerequisites (ability score minimums, proficiency requirements), its own granted effects (which can themselves be ability bonuses, proficiencies, or entirely bespoke rules text), and needs its own place in the Draft/Resolution/sheet shape and its own UI. This is real, separate scope — not a natural extension of "importing more races" — and is why it's split out rather than bundled into 4b. The data for it (`feats.json`, not yet fetched — a NEW `--official` target chargen/sync.py doesn't currently pull) needs its own fetch + normalizer pass, informed by what 4a/4b's race/background feat-REFERENCES look like once those land.

This spec covers 4a and 4b's design in full; 4c gets its own follow-up spec once 4a/4b are built (its shape depends on exactly how 4a/4b store the "this race/background grants feat X" reference, which isn't fully known until those are implemented).

## Design per mechanical dimension

**Ability bonuses (races + 2024 backgrounds).** Both the fixed shape and the `{"choose": {...}}` shape (including the WEIGHTED variant backgrounds use, e.g. "+2 to one of STR/CON/CHA, +1 to a different one" — a strict generalization of Half-Elf's existing "+1 to two of five" pattern, which itself generalizes ASI's "+2 to one OR +1 to two" pattern) all normalize into the SAME `ability_bonus_options`-shaped envelope `catalog/choices.py`'s `build_choice_template` already parses (Phase 3b already extended it once for `option_type: "ability_bonus"` — the weighted case needs a further small extension, since "+2 to X, +1 to a DIFFERENT Y" is a genuinely new combinatorial shape none of ASI/Half-Elf's existing combinations produce). For BACKGROUNDS specifically: `resolve()`'s ability-score pipeline currently only reads `_species_ability_bonuses(race, subrace)` before `final_scores` — this needs a parallel `_background_ability_bonuses(bg)` step, applied in the same early pass, for the (now real, 2024-only) case where a background contributes ability bonuses.

**Skill/tool/weapon/armor proficiencies (fixed).** Same boolean-map-to-list conversion for all four categories; skills feed the existing `proficient_skills` mechanism, tools/weapons/armor feed the `sheet.proficiencies.armor`/`weapons`/`tools` fields ALREADY BUILT in Phase 3b-i for multiclass proficiency grants — this is a fortunate, direct reuse of very recent work, not a new sheet shape.

**Skill/tool proficiency CHOICES (including `{"any": N}`).** A named skill/tool list becomes a normal `options_array`-shaped Choice (same mechanism as everything else). The `{"any": N}` wildcard (choose N from EVERY tool in the game, not a named subset) needs a new `build_choice_options` branch reading the full tool list from `catalog.items` (or wherever v2 indexes tools) rather than a fixed `options` array in the source data — a genuinely new envelope shape, but a small, well-bounded addition to the same generic choice-building function that's been extended several times already (reference/counted_reference/string/multiple/ability_bonus so far).

**Damage resistances/immunities/vulnerabilities, condition immunities.** New `sheet` fields (candidate shape: `sheet.damageModifiers: {resistances: string[], immunities: string[], vulnerabilities: string[]}`, `sheet.conditionImmunities: string[]`) — pure data pass-through from the race record, no interaction with any other computed field (this app computes a character SNAPSHOT, not live combat — there's no damage-taking simulation anywhere to interact with, so this is genuinely just "carry the data to the sheet," not a deep mechanical integration).

**Innate spellcasting.** A new per-source entry, parallel to how `sheet.spells` already carries one entry per CLASS-sourced caster (Phase 3b-ii) — either extend that same list with a `"species"`-sourced entry (reusing the existing `{classId, cantrips, known, spellSaveDC, spellAttackBonus}` shape loosely, or a adjacent dedicated `sheet.innateSpells` list — exact shape a plan-writing decision) carrying the specific spell(s), the level each becomes available, and the resolved ability (fixed or player-chosen via a Choice, mirroring the `{"ability": {"choose": [...]}}` shape).

**Starting equipment package choice (backgrounds).** The `{"a": [...], "b": [...]}` shape is a "pick package A OR package B" choice — normalize into the SAME equipment-choice-envelope shape `_equipment_choice_templates` already builds from SRD's own (differently-shaped) envelopes, so the existing equipment-choice UI/resolution code needs zero changes, only a new source-shape-to-envelope converter.

**Feat-granting (background, data-only in 4b).** Store the referenced feat id(s) on the resolved background/sheet somewhere inert (not silently dropped, not yet mechanically applied) — exact field TBD at 4b's plan-writing time, informed by whatever shape reads most naturally once 4c needs to consume it.

## Source labeling and selection (unchanged from the first pass)

Every imported record carries its own source book; `GET /api/catalog` exposes it for frontend grouping (matching the D&D Beyond reference captures in `Resurses/`). `Draft.sources: string[]` (existing since Phase 0, never read until now) becomes the source-selection mechanism — empty/absent means "everything available" (permissive default), non-empty filters selectable records to that list plus the SRD baseline.

## Licensing (unchanged, not re-litigated)

Data stays at `chargen.sources.official_dir()`, outside the repo, never committed — same storage decision v1 already made and this project inherits.

## Explicitly still out of scope

- Classes/subclasses/spells/equipment items from other sourcebooks (v1 never built normalizers for these shapes either; separate future phase).
- A 2014-vs-2024 "ruleset" toggle as a distinct global switchboard (XPHB content imports as just another labeled source in 4a/4b, per the original spec's reasoning — unchanged).
- Phase 4c (Feats as a mechanic) — its own future spec, informed by 4a/4b's actual shape once built.

## Testing strategy

- Every normalizer tested against the REAL fetched data (this project's unbroken discipline).
- A real end-to-end `resolve()` test per new mechanical dimension: a race with resistances, a race with innate spellcasting (fixed ability), a race with innate spellcasting (chosen ability, exercising the new Choice), a race with a `{"any": N}` tool choice, a 2024 background with ability bonuses, a background with the package-choice equipment shape.
- The official-data-absent no-op regression check (unchanged from the first pass) — critical given how much MORE surface area this revision adds; every single new code path must degrade to exactly today's behavior when `has_official()` is `False`.

## Self-review

- **Placeholder scan:** every mechanical dimension names its target sheet/Choice shape concretely; the two genuinely open decisions (innate-spell sheet shape, feat-reference field shape) are named as explicit plan-writing/4c decisions, not left vague.
- **Internal consistency:** the reuse of Phase 3b-i's `sheet.proficiencies.armor/weapons/tools` and Phase 3b's `ability_bonus_options`/Choice machinery is stated consistently across every dimension that touches them.
- **Scope check:** 4a/4b/4c decomposition mirrors the established 3a/3b-i/3b-ii/3c pattern; Feats' genuine novelty (not an extension of anything existing) is the stated reason it's split into its own phase rather than a scope-creep risk inside 4b.
- **Ambiguity check:** the "why 2014 backgrounds don't grant ability bonuses but 2024 ones do" distinction is stated explicitly with its data-grounding (60/161 background records have `ability`), not left as an unexplained special case.
