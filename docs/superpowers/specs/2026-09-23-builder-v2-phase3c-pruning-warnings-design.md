# Phase 3c — Pruning Warnings: Design

## Context

Since Phase 0, `Resolution.pruned` has existed in the response shape (`list[{choiceId, reason}]`, both backend `frontend/src/types.ts` and the Python side) but has NEVER been written to — `resolve()` always returns `"pruned": []`. The architecture already makes stale selections SAFE by construction: every phase since Phase 1 has relied on the fact that a choice template is only generated for a level/class/subclass/species actually currently reached, so a selection stored in the Draft for a choice that no longer exists (because the player leveled down, switched subclass, removed a class, changed species) simply stops being read by the generic choice-resolution loop — it's never deleted, never causes a crash, just silently inert. This has been explicitly relied upon and tested (e.g. Phase 3a's own design spec §7, "no pruning needed" — verified by a level-up/level-down round-trip producing byte-identical results).

Phase 3c is NOT about correctness — the architecture is already correct. It's purely about **visibility**: telling the player "this choice you made no longer applies and was ignored" instead of leaving them to wonder why, say, an ASI they picked at a higher level silently stopped applying after they lowered their level, or a subclass-gated feature choice they made silently stopped applying after they cleared that subclass.

## Goal

Populate `Resolution.pruned` for the first time: one entry per stale-but-still-present selection in the Draft, surfaced to the player as a dismissible-feeling (but not actually dismissible — the Draft itself isn't mutated) informational list, similar in spirit to `warnings` but distinct (a `warning` is about the CURRENT state being incomplete/ambiguous; a `pruned` entry is about something the player did in the PAST that no longer matters).

## Detection — no new data structure needed

`resolve()` already builds `all_selections: dict[str, list[str]]` — a merged dict of every submitted choice selection across every source (every resolved class, background, species, equipment), immediately before the generic choice-resolution loop that reads from it. This is already, structurally, "everything the Draft currently claims to have selected, across every source" — built once, in one place, right before it's needed.

`choice_templates` (built just before `all_selections`) is the complete list of choice templates that exist FOR THE CURRENT DRAFT STATE — i.e., everything that's actually reachable right now.

**Detection is a single set comparison:** for every key in `all_selections` whose value is a non-empty list, if that key is NOT in `{tpl["id"] for tpl in choice_templates}`, that selection is stale — add a `pruned` entry. This requires no new tracking, no history, no comparison against a "previous" Draft state — it's purely a function of the CURRENT Draft, computed once per `resolve()` call, exactly like everything else in this stateless, from-scratch-computed engine.

**Ordering:** this check must run AFTER `choice_templates` is fully assembled (all sources) and using the SAME `all_selections` dict the generic resolution loop itself uses — so it can simply run right before that loop, or right after it (order doesn't matter for correctness, since neither mutates the other).

## What the `reason` string says

Keep it simple and generic — this project's established practice is to avoid over-engineering. A reason like:

> `"'{choice_id}' no longer applies to the current character and was ignored."`

is sufficient — it's traceable (names the exact stale choice id) without requiring the engine to reconstruct WHY it became stale (that would require diffing against some remembered prior state, which the architecture deliberately doesn't keep). No per-cause branching (leveled down vs. switched class vs. removed a class, etc.) — a single generic template covers every case uniformly, matching how `warnings`/`problems` already use a single flat `{id, message}` shape without a cause taxonomy.

## What does NOT change

- No mutation of the Draft — `pruned` is purely informational output, exactly like `problems`/`warnings`. The stale selection stays in the Draft's `localStorage` copy untouched (consistent with the existing, already-relied-upon "never delete, just stop reading" architecture) — a player could, in principle, level back up and have their old selection silently resurface, which is correct RAW-agnostic UX (undo-friendly), not a bug to fix.
- No change to the actual resolution logic anywhere else — this is a pure, additive read-only pass over already-computed data.

## Explicitly out of scope

This phase detects staleness where a choice's ID entirely disappears from the current `choice_templates` — the ID that used to be generated for the Draft's prior state simply isn't generated anymore. It does NOT detect the separate case where a choice's ID survives but its allowed COUNT shrinks — e.g. a spellcaster levels down while still having more spells selected than the lower level now allows. Spell choice ids are deliberately level-agnostic (see `server/engine/resolve.py`, `_spell_choice_templates`: "No `level` in source — these choices span every level a spellcaster has reached"), so `class:<id>:spells-known` stays present in `choice_templates` across a level change; only its `choose` count shrinks. That case already produces a blocking `over-selected-*` problem (pre-existing behavior, not introduced by this phase) rather than a `pruned` entry. It's a known, separate gap — tracked as follow-up work, not addressed here.

## Frontend

**Confirmed by direct grep while writing this spec:** `resolution.warnings` already renders on `frontend/src/pages/HomePage.tsx` (a plain `<ul>{resolution.warnings.map(w => <li key={w.id}>{w.message}</li>)}</ul>`, right below the loading/error handling for the `/api/resolve` call — the page's general "Resolution" overview section). `resolution.problems` separately already renders on `frontend/src/pages/ExportPage.tsx` (gating whether export is allowed).

`pruned` is closer in spirit to `warnings` (informational, not blocking) and is Draft-wide rather than export-specific, so the natural placement is HomePage.tsx, immediately mirroring the existing `warnings` list — same `<ul>`/`<li>` shape, keyed by `choiceId` instead of `id`, rendering `reason` instead of `message`. No new component needed; this is a small, additive JSX block right next to the existing `warnings` rendering.

## Testing strategy

**Reachable scenarios** (verified against the real frontend reducer — only these two actions leave `choices` untouched while changing what's reachable):
- A real level-down scenario (e.g. a Fighter leveled to 5 with a level-5 ASI selected, then leveled back down to 3) — confirm the level-5 ASI choice id appears in `pruned` with a reason naming it, and confirms `resolve()` doesn't crash or otherwise change any OTHER behavior.
- A subclass-clearing scenario (a feature choice tied to the now-cleared subclass) — confirm staleness detected, and that a BASE (non-subclass-gated) feature choice on the same class stays unaffected.
- A regression check: a character with NO stale selections (a fresh, freely-built one) has `pruned == []`.
- Confirm a stale selection with an EMPTY list (`[]`) is NOT flagged — only non-empty stale selections matter (an empty list contributes nothing regardless of staleness, so flagging it would be noise).
- A multiclass independence check: one class's selection going stale must not affect any OTHER class's own choices in the same `resolve()` call (the flat `all_selections` merge must not cause cross-class interference).

**Explicitly NOT reachable, do not write a test expecting these to produce `pruned` entries:** a class-removal scenario (removing a class deletes its whole `choices` dict WITH it — nothing left to go stale) and a background/species-change scenario (`SET_BACKGROUND`/`SET_SPECIES`/`SET_SUBSPECIES` all reset `choices: {}` on the new entry) — both confirmed unreachable via the real `DraftContext.tsx` reducer, consistent with the `## Explicitly out of scope` and `## What does NOT change` sections above.

## Self-review

- **Placeholder scan:** the one open plan-writing decision (exact frontend placement/component) is named explicitly as a decision to make once `warnings`' own current rendering state is checked, not left vague without a concrete resolution path.
- **Internal consistency:** the "no new data structure, one set comparison, using the exact all_selections dict the resolution loop itself already uses" claim is the core insight, stated once and not contradicted elsewhere.
- **Scope check:** deliberately excludes any Draft mutation, any "clean up my draft" button, any historical diffing — purely additive, read-only detection matching the existing architecture's own stated design (Phase 3a §7).
- **Ambiguity check:** the generic (not per-cause) reason string is an explicit, stated choice with its rationale (matches `warnings`/`problems`' own flat shape), not left for the plan to silently decide.
