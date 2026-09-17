# Builder v2 Phase 3a — Single-Class Leveling (1-20) Design

**Status:** approved by user 2026-09-17, ready for implementation planning.

## 1. Scope

This is the first of three sub-phases decomposing the architecture spec's
"Phase 3 — depth" item (§10), the same way Phase 2 was decomposed into
2a-2g. In scope here: **a single class, levels 1-20** — level selection,
every intermediate feature/proficiency choice along the way, subclass
selection at the correct level per class, ability-score-improvement (ASI)
choices, and hit-point growth per level. Explicitly **out of scope**,
deferred to their own future specs:

- **3b — Multiclassing.** Adding a second/third class, the multiclass
  spell-slot table, multiclass prerequisite enforcement
  (`Draft.preferences.usePrerequisites.multiclass`, already stubbed in
  the type system but unused). `resolve()` continues to reject more than
  one class entry exactly as it does today (`multiclass-unsupported`
  problem) — this spec does not touch that check.
- **3c — Pruning warnings.** Surfacing an explicit warning when a
  higher-level choice becomes stale (e.g. the user picks level 8, makes
  choices, then drops back to level 5). See §7 for why 3a is already
  *safe* without this — 3c only adds the user-facing warning on top of
  behavior this spec already gets for free.
- **Feats.** The bundled SRD has no feat data at all (no
  `5e-SRD-Feats.json` exists in `chargen/data/srd/`) — origin feats are
  explicitly Phase 4 (2024 mechanics) scope per the architecture spec's
  phasing. ASI choices in this spec are ability-score-only, matching
  what SRD 5.1 actually supports.

## 2. Data model

`frontend/src/types.ts`'s `ClassSelection` already anticipated this work:

```ts
export interface ClassSelection {
  classId: string;
  level: number;
  subclassId?: string;
  choices: Record<string, string[]>;
}
```

`level` and `subclassId` already exist and are already partially read by
the backend (`resolve.py` reads `cls_entry.get("level", 1)` only to
reject anything but 1, and reads `subclassId` to gate subclass-specific
features — see §3). This spec removes the level-1-only restriction and
wires `subclassId` into a real, dispatchable selection instead of a
field nothing ever writes to.

**New field needed:** hit-point rolls for manual mode. Add to
`ClassSelection`:

```ts
hpRolls?: Record<string, number>;  // level (as string) -> rolled value, only meaningful when preferences.hitPointType === "manual"
```

Keyed by level as a string (`"2"`, `"3"`, ...) since object keys are
always strings in JS/JSON anyway — matches the existing convention
`choices: Record<string, string[]>` already uses for choice ids.

**No new field needed for ASI or subclass** — see §4 and §5.

## 3. Fixing the `level_row` ambiguity

Empirically confirmed while writing this spec: `5e-SRD-Levels.json`
contains two row shapes under the same `class.index`. Base-class rows
(`level`, `prof_bonus`, `ability_score_bonuses`, `features`, optional
`spellcasting`, optional `class_specific`) have no `subclass` key.
Subclass-feature rows (a specific subclass's own features gained at a
level) carry a `subclass` key instead and lack `prof_bonus`/
`ability_score_bonuses` entirely. E.g. Wizard has 20 base rows (levels
1-20) plus 4 Evocation-subclass rows (levels 2, 6, 10, 14) — same
`class.index: "wizard"`, different shape, and until now `level_row` was
only ever called with `level=1`, where no subclass row exists yet to
collide.

`server/catalog/loader.py`'s `Catalog.level_row(class_id, level)` must
be replaced (or supplemented) with a version that explicitly excludes
subclass rows:

```python
def class_level_row(self, class_id: str, level: int) -> dict | None:
    for row in self.levels:
        if (row.get("class", {}).get("index") == class_id
                and row.get("level") == level
                and "subclass" not in row):
            return row
    return None
```

A second lookup is needed for subclass-granted features at a given
level (needed once a subclass is selected, to surface e.g. Evocation's
own level-6 "Potent Cantrip"):

```python
def subclass_level_row(self, subclass_id: str, level: int) -> dict | None:
    for row in self.levels:
        if row.get("subclass", {}).get("index") == subclass_id and row.get("level") == level:
            return row
    return None
```

Every existing call site that currently calls `level_row(class_id, 1)`
gets updated to `class_level_row(class_id, level)` (the previously
hardcoded `1` becomes the draft's actual selected level).

## 4. ASI: a standard Choice, not a new mechanism

Empirically confirmed: `ability_score_bonuses` in each level row is a
**cumulative count**, not a per-level flag — it stays nonzero at every
level once earned, so the actual ASI-granting levels are found by
diffing consecutive levels' values, not by checking `> 0`. Verified
across all 12 classes:

- Standard progression (10 of 12 classes): **4, 8, 12, 16, 19**
- **Fighter**: 4, 6, 8, 12, 14, 16, 19 (extra at 6 and 14)
- **Rogue**: 4, 8, 10, 12, 16, 19 (extra at 10)

This matches real 5e RAW exactly, confirming the bundled data is
trustworthy here.

**Design decision (refined from the initial verbal sketch, during
spec-writing):** ASI does not need a new `Choice` "kind" or a new
frontend component. It fits the existing generic Choice shape
(`id/source/label/description/count/options/selected/status`,
rendered by the unmodified `<ChoiceCard>`/`<ChoicePicker>`) if the
options are pre-computed as the 21 valid combinations for six
abilities: 6 "+2 to one ability" options (`str-plus-2`, `dex-plus-2`,
...) plus C(6,2)=15 "+1 to two abilities" options
(`str-dex-plus-1-1`, `str-con-plus-1-1`, ...). `count: 1` — the
existing single-select ChoicePicker behavior (picking a new option at
`count === selected.length` replaces the previous pick) handles this
natively, the same way a class's single-pick feature choices already
work.

**The 20-point cap** (a combination that would push any involved
ability above 20 is invalid) reuses the existing
`option.disabled`/`disabledReason` mechanism already used elsewhere
(e.g. background/class skill-proficiency overlap) — no new mechanism,
just a new reason to set it. This must be computed against the
character's **current final ability scores at the ASI's level**, not
base scores — i.e. after species bonuses and any lower-level ASIs
already selected are applied, since ASI increases stack across levels
and a stacked score could cross 20 partway through a build.

Choice id: `class:<classId>:<level>:asi` (matches the existing
`class:<classId>:1:...` id pattern, generalized to the actual level).
Label: `"Ability Score Improvement"`. Source: `{kind: "class", id:
classId, label: className, level}`.

## 5. Subclass selection: a dedicated field, like subspecies

Empirically confirmed, directly from each class's own `features` list
at levels 1-3 (not from a structured "choose subclass" envelope — no
such envelope exists in the bundled data; the unlock level is
identified by which named feature first appears):

| Level | Classes |
|---|---|
| 1 | Cleric (`divine-domain`), Sorcerer (`sorcerous-origin`), Warlock (`otherworldly-patron`) |
| 2 | Wizard (`arcane-tradition`), Druid (`druid-circle`) |
| 3 | Barbarian, Bard, Fighter, Monk, Paladin, Ranger, Rogue |

This must be a small hardcoded reference table (`SUBCLASS_UNLOCK_LEVEL:
dict[str, int]` in `server/catalog/reference_data.py`, matching the
existing `SKILL_ABILITY`/`LANGUAGES`/`SKILL_NAMES` precedent for "open
SRD/RAW facts not exposed structurally in the bundled JSON") — there is
no way to derive it purely from data without hardcoding *something*,
and this table is the smallest, most direct encoding of the fact.

**Design decision (refined from the initial verbal sketch):** rather
than a generic Choice, subclass selection reuses the exact pattern
already established for species subspecies
(`Draft.species.subspeciesId` + a dedicated `SET_SUBSPECIES` action +
a plain `<select>` in `SpeciesPage.tsx`) — not a `Choice` at all. This
is more consistent with existing precedent than treating it as a
Choice: `classes[0].subclassId` already exists in the type, `resolve()`
already reads it (currently just to gate subclass-specific feature
visibility), and there is exactly one subclass per class in the
bundled data (confirmed: `Counter({...: 1, ...: 1, ...})` for all 12
classes) — so unlike a real Choice, there's never more than one option
to pick from, which is exactly the shape a dedicated dropdown fits
better than a generic `ChoiceCard`.

New action: `SET_SUBCLASS` (`{type: "SET_SUBCLASS", subclassId:
string}`), dispatched from a `<select>` that only renders once
`classes[0].level >= SUBCLASS_UNLOCK_LEVEL[classId]`. `ClassPage.tsx`
needs the unlock-level table too (mirrored from the backend's
`reference_data.py` table — both must agree; add a backend test
asserting the frontend and backend tables are the same 12 entries, the
same discipline Phase 2e's `_DETAIL_FIELDS` contract-pin test and Phase
2g's shared-sections guard test already established for exactly this
"two independent copies must not drift" risk).

## 6. Hit points per level

Level 1 is unchanged (`hit_die` max + CON modifier, already correct
today). For levels 2 through the selected level, per-level HP gain
depends on `Draft.preferences.hitPointType`:

- **`"fixed"`** (RAW's "take the average" option): `floor(hit_die / 2)
  + 1 + CON modifier` per level (d6→4, d8→5, d10→6, d12→7, before the
  CON modifier).
- **`"manual"`** (RAW's "roll it" option): the value from
  `classes[0].hpRolls[level]`, clamped to `[1, hit_die]` server-side
  (defensive — a client bug or direct API call could submit anything).
  **If a level's roll is missing** (not yet entered by the user), fall
  back to the fixed-average value for that level rather than treating
  it as 0 or raising a blocking problem — matches this project's
  established pattern of "sensible default, no blocking problem for a
  gap that isn't load-bearing" (e.g. `details`' malformed-input
  handling in Phase 2e). The frontend should visually distinguish a
  real entered roll from a defaulted-average display (e.g. the input
  shows a greyed placeholder of the average until the user types a
  real value), so the estimate is never mistaken for a confirmed roll.

Total `hitPointMax` = level-1 HP + sum of per-level gains for levels 2
through the selected level.

## 7. Why level-down is already safe without 3c

`resolve()`'s existing choice-resolution loop (`for tpl in
choice_templates: ... raw_selected = all_selections.get(tpl["id"]) or
[]`) only ever looks up a selection **for a choice template that was
actually generated**. Once level generation is cumulative (§8) and a
choice's template is only generated for levels the draft has actually
reached, dropping the draft's level from, say, 8 back to 5 means the
level-6/7/8 choice templates simply aren't generated on the next
resolve — their stored selections in `classes[0].choices` are never
looked up, never validated, and **never deleted**. If the user goes
back up to level 8 later, the same choice ids resolve against the same
stored selections and reappear exactly as they were.

This means 3a needs **zero pruning logic** — the existing
template-generation-is-the-source-of-truth architecture already makes
level-down non-destructive. 3c's future job is purely additive: detect
that `classes[0].choices` contains keys for a level higher than the
current selection (a cheap set-difference) and surface a warning like
"you have unused choices saved from level 8" — a UX nicety, not a data
safety fix, since there is nothing to protect against data loss here.

## 8. Cumulative choice generation

`_class_choice_templates` and `_feature_choice_templates` currently
read only `catalog.level_row(cls_id, 1)`. Both become loops from level
1 through `cls_entry.get("level", 1)`, accumulating templates from
every level's `features` list (via `class_level_row`, §3) plus, once a
subclass is selected, every level's subclass-feature list (via
`subclass_level_row`, §3) up to the current level — mirroring exactly
how `_equipment_choice_templates`/`_spell_choice_templates` already
iterate a fixed structure and append; this is the same pattern, just
iterating levels instead of a flat list.

The architecture spec's own CLASS-step UI language ("one `<ChoiceCard>`
per feature by level", "Available at Higher Levels (N)") already
assumes exactly this shape — a single flat, cumulative list of choices
across all reached levels, with a teaser count for what's still locked
above the current level. `ClassPage.tsx` needs a level selector (a
number input or slider, 1-20, dispatching `SET_CLASS_LEVEL`) and the
"Available at Higher Levels (N)" counter — computed client-side by
counting `catalog`-derived feature entries above the current level for
the selected class (needs a new lightweight catalog endpoint or a
richer `/api/catalog/class/<id>` response exposing the full level-by-
level feature list, not just the current flat class object — see the
implementation plan for the exact shape).

## 9. Derived stats at higher levels

`derived.proficiencyBonus` (currently hardcoded `2`) becomes
`class_level_row(cls_id, level)["prof_bonus"]` — already present per
level in the bundled data, no new logic needed beyond reading the
right row. Spellcasting classes' cantrips/known-spells/slots (Phase
2c/2d) already read from a `level_row` call gated to level 1 — these
become `class_level_row(cls_id, level)` too, picking up the real
per-level spell progression the bundled data already has (verified
earlier this session: e.g. Wizard's level-20 row already has the full
9-spell-level slot table). Spell *options* (`_spell_options`) currently
filter to `spell_level <= 1` (a Phase 2c constraint tied to the
level-1-only scope) — this becomes `spell_level <= <highest available
slot level at the current class level>`, computed from the same level
row's `spell_slots_level_N` fields.

## 10. Testing strategy

Mirrors this project's established discipline throughout every prior
phase: empirically verify against real bundled data (not hand-typed
fixtures) for anything level/class-shaped, sweep all 12 classes (not
just one or two) in both per-task and final reviews — this project's
history has repeatedly found real bugs that only a full-class sweep
catches (Phase 2a's granted-armor bug, Phase 2c's Paladin/Ranger
zero-slots edge case). Specific cases worth calling out for the
implementation plan: a level-1 character must resolve byte-identical
to before this phase (regression safety — every existing Phase 1/2
test exercises level 1 only); Fighter and Rogue's extra ASI levels;
each of the three subclass-unlock levels (1/2/3); an ASI combination
that would push an ability above 20 is correctly disabled, and
correctly re-enabled if an earlier ASI choice changes; a spellcaster's
spell options correctly expand as the class levels up past its
1st-level-only starting slots.

## 11. Self-review

- **Placeholder scan:** none — every section has concrete values,
  formulas, and code sketches grounded in data read during this
  session, not left as TBD.
- **Internal consistency:** §7's "no pruning needed" claim depends on
  §8's "templates are only generated for reached levels" — both
  sections are consistent with each other and with the existing
  `resolve()` selection-lookup pattern read directly from the current
  codebase.
- **Scope check:** appropriately sized for one implementation plan —
  comparable in surface area to Phase 2a+2b combined, which is the
  right ballpark for "3a" given 3b/3c were split out specifically to
  keep this piece bounded.
- **Ambiguity check:** the ASI-cap-computation ordering (§4, "current
  final ability scores at the ASI's level, not base scores") was the
  one place two readings were possible (cap against base score vs.
  cap against the stacked score including lower-level ASIs already
  picked) — resolved explicitly in favor of the stacked reading, since
  that's what RAW actually requires and the alternative would let a
  character exceed 20 by picking lower ASIs after a higher one in the
  wrong order.
