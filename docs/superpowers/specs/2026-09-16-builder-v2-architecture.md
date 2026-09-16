# Character Builder v2 — Architecture

**Goal:** Rebuild the app as a D&D Beyond-style, choice-driven character builder:
`HOME → CLASS → BACKGROUND → SPECIES → ABILITIES → EQUIPMENT → EXPORT`,
with live recalculation, per-feature expandable cards, and inline choice
resolution.

**Kept from the old app:** only `chargen/data/srd/*.json`. Everything else
(rules engine, storage, derive, renderers, Flask app, template) is rewritten.

---

## 1. Data inventory — measured, not assumed

Counts taken directly from the bundled files.

| File | Count | Carries choices? |
|---|---|---|
| Classes | 12 | `proficiency_choices`, `starting_equipment_options`, `multi_classing.prerequisite_options` |
| Levels | 290 rows | per class/level: `features[]`, `ability_score_bonuses`, `prof_bonus`, `class_specific`, `spellcasting{cantrips_known, spell_slots_level_1..9}` |
| Features | 407 | **120 carry `feature_specific.subfeature_options`**; 88 are tied to a subclass |
| Subclasses | 12 (exactly 1 per class) | `spells[]` (domain spells); per-level features come from Features filtered by `subclass.index` |
| Races | 9 | `ability_bonuses`, `traits[]`, `starting_proficiency_options` |
| Subraces | 4 | `ability_bonuses`, `racial_traits[]` |
| Traits | 38 | `trait_specific.subtrait_options` (Draconic Ancestry, High Elf Cantrip, Tool Proficiency, Skill Versatility, Tinker, Extra Language) |
| Backgrounds | **1 (Acolyte)** | `language_options`, `starting_equipment_options` |
| Spells | 319 | — |
| Equipment | 237 (37 weapons, 13 armor, 116 gear, 31 tools, 40 mounts) | armor: `armor_category`, `armor_class{base,dex_bonus,max_bonus}`, `str_minimum`, `stealth_disadvantage` |
| Feats | **none** | SRD 5.1 ships no feat list |

**The decisive finding:** every "choose N of these" in the data uses one
shape:

```jsonc
{ "desc": "...", "choose": 2, "type": "proficiencies",
  "from": { "option_set_type": "options_array",
            "options": [ { "option_type": "reference", "item": {...} } ] } }
```

`option_type` varies (`reference`, `counted_reference`, `multiple`,
`score_prerequisite`), but the envelope is constant. That means one
normalizer, one `Choice` type, one React component — for class skills,
fighting styles, racial ancestry, starting kits, and languages alike. This
is what makes the D&D Beyond UI reproducible rather than 40 special cases.

---

## 2. The central abstraction

Everything the builder shows — the "!" badge, the "2 Choices" label, the
dropdown inside a feature card — is one concept:

```ts
Choice = {
  id: string            // stable: "class:fighter:1:prof-skills"
  source: { kind: 'class'|'subclass'|'background'|'species'|'feature'|'equipment',
            id, label, level?: number }
  label, description
  count: number
  options: { id, label, description?, disabled?, disabledReason? }[]
  selected: string[]
  status: 'pending' | 'resolved' | 'invalid'
}
```

The UI never reads the catalog to build a choice list. **Choices are always
produced by the engine**, because their options depend on the rest of the
draft (see §4b).

---

## 3. Engine contract

One pure function, re-entrant, no step state machine:

```
resolve(draft, catalog) -> Resolution
```

```ts
Draft = {
  name, portrait?, sources: string[], preferences: Preferences,
  classes: [{ classId, level, subclassId?, choices: Record<choiceId, string[]> }],
  background: { id?, choices },
  species:    { id?, subspeciesId?, choices },
  abilities:  { method: 'standard'|'roll'|'pointbuy'|'manual',
                base: Record<Ability, number>, rollGroups?: RollGroup[] },
  equipment:  { startingChoice?, added: [{itemId, qty, equipped}], skipped },
  details:    { alignment?, faith?, lifestyle?, physical, personality, notes },
}

Resolution = {
  sheet,                    // the full derived character
  choices: Choice[],        // every choice, pending and resolved, with provenance
  derived,                  // ac, hp, hitDice, profBonus, skills, saves, slots, dc, passives
  problems: Problem[],      // blocking (illegal)
  warnings: Warning[],      // informational (e.g. mixed editions)
  pruned: Pruned[],         // selections dropped because they became invalid
}
```

Each of the seven UI steps renders `choices.filter(c => c.source.kind === …)`.
That is the entire page logic.

---

## 4. Dependency graph and the interactions that actually bite

```
sources (HOME)
  └─ filters the catalog for every later step
      ├─ CLASS  classId, level ─┬─ features by level → feature choices
      │                         ├─ skill choices (must exclude background's)
      │                         ├─ spellcasting slots/cantrips → SPELLS
      │                         └─ multiclass prerequisites ── needs FINAL scores ↓
      ├─ BACKGROUND  skills/tools/langs (+2024: ability bonuses, origin feat) ─┐
      ├─ SPECIES     speed/size/traits (+2014: ability bonuses) ──────────────┤
      ├─ ABILITIES   base scores + those bonuses = final ←────────────────────┘
      │                └─ modifiers → AC, HP, skills, saves, spell DC, passive perception
      └─ EQUIPMENT   kit A/B from class+background; armor → AC (needs DEX) ; weapons → attacks
```

Three interactions need deliberate handling; everything else falls out.

**(a) The ability-score cycle.** Multiclass prerequisites depend on final
scores; final scores depend on background/species bonuses chosen elsewhere.
Resolved by making `resolve()` a **single fixed-order pass** —
sources → species/background bonuses → abilities → derived → class and
multiclass validation. Never iterate to a fixpoint. A failed prerequisite is
a `problem`, not a hidden option (matches D&D Beyond's behaviour when
"Use Prerequisites" is on).

**(b) Option lists are contextual, never static.** A Fighter's "choose 2
skills" must not offer skills the background already granted. Those options
come back `disabled: true, disabledReason: "already granted by Sage"`. This
is precisely why choices must come from `resolve()` and never be assembled
in the frontend from raw catalog JSON.

**(c) Lowering a level is destructive.** Fighter 5 → 2 invalidates the L4 ASI
and L3 subclass selections. The engine prunes orphaned selections and
returns them in `pruned[]` so the UI can warn before committing
("this removes 3 selections"). Unhandled, this silently corrupts characters.

---

## 5. Where the computation runs

**The engine stays in Python, on the server; React calls `POST /api/resolve`,
debounced ~150 ms.**

Rationale: the rules must exist in exactly one place. A TypeScript engine in
the browser plus a Python one for PDF/YAML/Markdown export means two rule
sets that drift — the single most reliable way for this project to rot. The
app runs on localhost, so a resolve round-trip is a few milliseconds.

React holds the `Draft` in local state plus `localStorage` (so typing is
instant and a refresh never loses work), and treats the returned
`Resolution` as authoritative. Purely cosmetic feedback (an ability modifier
updating as a number is typed) may be mirrored client-side, but it is never
the source of truth.

---

## 6. API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/sources` | available sources + enabled state |
| GET | `/api/catalog?sources=…` | classes, species, backgrounds (list view: id, name, source, blurb, icon) |
| GET | `/api/catalog/class/<id>` | full class incl. level table and features |
| GET | `/api/catalog/species/<id>`, `/background/<id>`, `/item/<id>` | detail panels |
| GET | `/api/items?type=&source=&q=&proficient=` | equipment browser (filter pills) |
| GET | `/api/spells?class=&level=` | spell picker |
| POST | `/api/resolve` | **the hot path** — draft in, Resolution out |
| POST | `/api/roll` | server-side dice for roll groups (auditable) |
| GET/POST | `/api/characters…` | list / save / load drafts |
| POST | `/api/export/{yaml,md,pdf}` | final artefacts |

---

## 7. Frontend

Vite + React + TypeScript + React Router. State: one `DraftProvider`
(reducer + localStorage) and a `useResolution()` hook wrapping the debounced
resolve call.

Component inventory (small, because the data is uniform):

| Component | Used by |
|---|---|
| `<ChoiceCard>` | every feature/trait/proficiency choice — header, level tag, "N Choices" badge, `!` pending dot, expand, inline `<ChoicePicker>` |
| `<ChoicePicker>` | dropdown (searchable when long), disabled options with reasons |
| `<CollapsibleSection>` | Character Details, Physical, Personality, Notes, Dice Roll Groups |
| `<SourceGroupedList>` | class / species / background pickers grouped under source headings, with search + Collapse/Expand all |
| `<SelectWithDetail>` | background & alignment: pick → description renders beneath |
| `<ConfirmModal>` | species confirmation before committing |
| `<StatBlock>` | expandable item/spell/feature detail |
| `<NotesSection>` | Organizations / Allies / Enemies / Backstory / Other |
| `<AbilityScoreTable>` | Total/Modifier/Base/Bonus/Set/Stacking + Other Modifier & Override |
| `<FilterPills>` | equipment type + source filters |
| `<StepNav>` | the seven tabs, each showing its own pending-choice count |

---

## 8. The seven steps

1. **HOME** — Sources (checkbox per source, filters everything downstream);
   preferences: Advancement (Milestone/XP), Hit Point Type (Fixed/Manual),
   Use Prerequisites (Feats / Multiclass), Encumbrance, Ability/Modifier
   display order. Character name + portrait.
2. **CLASS** — source-grouped searchable list → class panel: level selector,
   HP/Hit Dice summary, `CLASS FEATURES` / `SPELLS` tabs, one `<ChoiceCard>`
   per feature by level, "Available at Higher Levels (N)", `+ Add Another
   Class` (multiclass; already-taken classes greyed out, prerequisites
   enforced per preference, mixed-edition warning).
3. **BACKGROUND** — source-grouped dropdown → description, granted
   skills/tools, then choice cards (languages; on 2024 data: ability
   allocation and origin feat). Character Details / Physical / Personality /
   Notes collapsibles live here.
4. **SPECIES** — grid → `<ConfirmModal>` → inline panel with trait cards and
   their choices (ancestry, cantrip, tool), "Change Species".
5. **ABILITIES** — method selector driving three distinct editors:
   *Standard Array* (six dropdowns over one shared pool, values consumed),
   *Point Buy* (27-point budget, live "Points Remaining", per-option cost
   labels), *Manual/Rolled* (inputs + Dice Roll Groups: add group, roll
   4d6-drop-lowest, assign each result to an ability, Reset / Apply).
   Below: the six ability cards with the full derivation breakdown.
6. **EQUIPMENT** — starting kit `(A) bundle or (B) gold` from class and
   background, Skip / Clear All; item browser with text search, type pills,
   Proficient/Common/Magical/Container checkboxes, source pills; each row
   expands to a stat block with quantity stepper and Add; Current Inventory
   with weight total, equip/unequip and remove.
7. **EXPORT** — validation summary, then YAML / Markdown / filled official
   PDF.

---

## 9. Content and licensing

SRD 5.1 (bundled) is openly licensed and ships in the repo. It gives 12
classes but only **1 background, 1 subclass per class, and no feats** — the
2024 material D&D Beyond shows (16 backgrounds, origin feats, weapon
mastery) is not in it.

Therefore the catalog is **multi-source with one adapter per format**:
`srd-5e-bits` (bundled) and `5etools` (optional). Additional packs are read
from a local data directory — the machine already has one at
`~/.claude/dnd/.data/official` with 161 backgrounds and 160 species — and
are **never committed to the repo**, since that material comes from paid
sourcebooks. The HOME "Sources" step is exactly the switchboard for this:
SRD always present, local packs appear when found.

---

## 10. Phasing

* **Phase 0 — skeleton.** Vite+React+Router shell, seven routed steps,
  `DraftProvider`, `POST /api/resolve` returning a stub Resolution,
  `<ChoiceCard>` rendering hardcoded choices. Nothing real, everything wired.
* **Phase 1 — vertical slice.** Catalog loader + normalizer, real `resolve()`
  for a single-class level‑1 character, CLASS/BACKGROUND/SPECIES/ABILITIES
  steps, YAML export.
* **Phase 2 — completeness.** Equipment browser and kit A/B, derived stats
  (AC/skills/saves/slots/DC), spells step, Markdown + PDF export, notes and
  details.
* **Phase 3 — depth.** Levels above 1 with all intermediate choices,
  subclasses, ASIs, multiclassing (incl. multiclass spell-slot table),
  prerequisite enforcement, pruning warnings.
* **Phase 4 — breadth.** 5etools adapter, 2024 mechanics (background ability
  allocation, origin feats, weapon mastery), source switchboard.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Two rules engines drift | Engine only in Python; React never computes rules |
| Level-down corrupts characters | `pruned[]` contract + UI warning, covered by tests |
| Choice IDs unstable across edits | IDs derived from `source:level:kind`, never array index |
| SRD content feels empty (1 background) | Source adapters + local packs; set expectations early |
| 2014/2024 schema divergence | Adapter boundary; the engine only ever sees normalized types |
| Scope | Strict phase gates; Phase 0 skeleton exists before any rule is written |
