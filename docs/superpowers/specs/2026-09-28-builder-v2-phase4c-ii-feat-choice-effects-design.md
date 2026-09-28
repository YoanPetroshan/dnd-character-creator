# Phase 4c-ii — Close the Feat Choice-Effects Gap: Design

## Context

Phase 4c-i (feats catalog + granted effects for background-granted feats) is merged to main. Its own final whole-branch review found a real, disclosed gap (Finding 3): `official_source.py`'s catalog conversion correctly builds `ability_bonus_options`/`proficiency_choices`/`language_options` envelopes for a feat that has choice-shaped content, but `resolve()` never turns any of the three into a selectable `Choice` — so a background-granted feat whose ONLY content is choice-shaped currently gives the player nothing. Confirmed real, unambiguous cases: Artisan/XPHB → Crafter/XPHB (choose 3 of 8 artisan's tools), Entertainer/XPHB → Musician/XPHB, Harper/FRHoF → Harper Agent, Purple Dragon Squire/FRHoF → Purple Dragon Rook.

This is deliberately the FIRST of two slices (per user direction, 2026-09-28: "do the small one, then immediately the big one"). The second slice — feats becoming player-SELECTABLE via the "ASI or feat" class-level mechanic — is a separate, larger, still-undesigned piece of work that will REUSE everything built here (any freely-chosen feat can have the exact same choice-shaped content this slice handles), but this slice's own scope is bounded to background-granted feats only, exactly matching Phase 4c-i's own disclosed gap.

## Goal

A background-granted feat with `ability_bonus_options`/`proficiency_choices`/`language_options` produces a real, selectable `Choice` in `resolution.choices`, and a player's selection actually applies its effect to the sheet — closing the exact gap Phase 4c-i's docstrings (`_feat_ability_bonuses`/`_feat_proficiency_ids`/`_feat_languages`) already name and point at.

## Architecture

Directly mirrors the EXISTING `_background_choice_templates`/`_species_choice_templates` pattern in `server/engine/resolve.py` — no new choice-building mechanism, no new merge architecture. A new `_feat_choice_templates(feats: list[dict]) -> list[dict]` function iterates every resolved granted feat and builds a `Choice` template for each of its three choice-shaped fields that's present, using the SAME `build_choice_template` call every other choice type already uses. Three merge-site extensions (found by grepping every place `c["source"]["kind"]` is checked — confirmed exactly 3 real sites in the current code) add a `"feat"` kind alongside the existing `"species"`/`"background"` ones, mirroring their exact conditions.

### Choice template shape

For each resolved feat with `ability_bonus_options`:
```python
cid = f"feat:{feat['index']}:ability-bonus"
source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
```
Reuses the EXISTING `_background_ability_bonus_deltas`-style bundle-flattening logic (built in Phase 4b for the 2024 background ASI's "+2/+1 split or +1/+1/+1" shape) — a feat's `ability_bonus_options` uses the SAME envelope shape (confirmed: `official_source._ability_bonus_options_from_5etools` is shared machinery, built once and reused by races/backgrounds/feats alike since Phase 4c-i Task 2). A new `_feat_ability_bonus_deltas(envelope, built_options)` mirrors `_background_ability_bonus_deltas` exactly (same bundle-id-to-deltas mapping), since a feat's ability-bonus choice could in principle be either the races' simple "+1 to one of N abilities" shape OR the backgrounds' "+2/+1 split" shape — the existing `build_choice_template`/`build_choice_options` machinery already handles both uniformly; only the DELTAS-back-out-of-a-selected-bundle-id step needs a feat-specific (but structurally identical) helper, since `_background_ability_bonus_deltas` is currently sized/named for the background-specific call site.

For `proficiency_choices` and `language_options`: identical to `_background_choice_templates`' own existing skill/tool-choice and language-choice blocks — `cid = f"feat:{feat['index']}:proficiency-choice-{i}"` / `f"feat:{feat['index']}:languages"`, same `":proficiency-choice"` substring convention (load-bearing for the merge-site fix, exactly as documented in the existing species/background code).

### The three merge-site extensions

1. `proficient_skills` merge (currently `if c["source"]["kind"] in ("class", "species", "background"):`) → add `"feat"`.
2. `_categorize_proficiency` merge (currently two `elif` branches for `"species"`/`"background"`, each gated on `"proficiency-choice" in c["id"]`) → add a third `elif` for `"feat"`.
3. Language merge (currently `if c["source"]["kind"] in ("background", "species") and c["id"].endswith(":languages")`) → add `"feat"`.

### Where `_feat_choice_templates`'s output gets applied

Wired into `choice_templates` alongside `_background_choice_templates(bg, bg_id)`'s own existing call site, fed `resolved_feats` (already computed earlier in `resolve()` by the existing `_resolve_granted_feats` bridge from Phase 4c-i — no new resolution step needed, this task only consumes what already exists).

## What does NOT change

- `_feat_ability_bonuses`/`_feat_proficiency_ids`/`_feat_languages` (the FIXED-grant functions, Phase 4c-i) are untouched — they continue to read only fixed grants; the new choice-driven grants flow through the SAME merge points via the generic Choice-selection mechanism, not through these functions.
- No change to `_resolve_granted_feats` or any Phase 4c-i prerequisite-checking code.
- No change to how a background's OWN choices (skill/tool/language/ability-bonus) work — this is purely additive, a new `kind` value alongside existing ones.

## Testing strategy

Real data throughout: Artisan/XPHB → Crafter/XPHB (proficiency_choices, "choose 3 of 8 artisan's tools" — ground the exact real shape before writing the test) is the primary end-to-end case. Cross-check against the SAME real background/feat pairs the Phase 4c-i final review already named (Musician/XPHB, Harper Agent, Purple Dragon Rook) for at least one more real proficiency-choice case if the shapes differ meaningfully. If a real feat with `ability_bonus_options` or `language_options` (not just `proficiency_choices`) is reachable via a real background grant, ground and test that path too — otherwise disclose that only the proficiency-choice path has real-data coverage and the other two are verified via the SAME kind of synthetic-feat monkeypatch technique Phase 4c-i's own test file already established (clearly labeled as such, not presented as real coverage).

A no-choice-feat draft (e.g. any background granting a feat with only fixed content, or no feat at all) must be completely unaffected — safe no-op, matching this whole plan's established discipline.

## Self-review

- **Placeholder scan:** none — every new function's shape is grounded against real, already-read current code (the exact 3 merge sites, the exact `_background_ability_bonus_deltas` pattern to mirror).
- **Internal consistency:** the `":proficiency-choice"` substring convention is stated once and applied consistently, matching the EXISTING established convention exactly (not a new one invented for feats).
- **Scope check:** deliberately bounded to background-granted feats' existing choice-shaped content — explicitly NOT the ASI-or-feat mechanic (a separate, larger, later design), though this slice's output (the choice-template-building machinery) is exactly what that later slice will need to reuse.
- **Ambiguity check:** the ability-bonus-options case's exact envelope shape (simple race-style vs. background-style weighted bundle) is explicitly named as something to verify per-feat at implementation time, not assumed uniform.
