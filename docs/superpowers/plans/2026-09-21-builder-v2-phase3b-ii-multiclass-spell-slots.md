# Phase 3b-ii — Multiclass Spell Slots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add spell slot tracking to the Resolution for the first time (it currently exists nowhere, not even for a single-class caster), computed via 5e's combined-caster-level formula so it correctly shares a pool across multiple non-Warlock casters, while keeping Warlock's own Pact Magic slots entirely separate. Also reshape `derived.spellSaveDC`/`spellAttackBonus` from primary-class-only scalars into per-caster values living inside each `sheet.spells` entry.

**Architecture:** Two new pure functions in `server/engine/spells.py` (combined caster level; shared-pool slot lookup), reusing the EXISTING `catalog.class_level_row` method and requiring **no new hardcoded reference table** — the standard multiclass slot table is number-for-number identical to any full caster's own single-class slot progression at the same level (verified directly against the bundled SRD data while writing the design spec: Wizard's own per-level `spell_slots_level_N` values for levels 1-20 exactly match the known PHB multiclass table). `resolve()` wires these in, moving `spellSaveDC`/`spellAttackBonus` into each `sheet.spells` entry. Three export consumers and the frontend's types get updated to match.

**Tech Stack:** Same as every prior phase — Python/Flask backend, React/TypeScript frontend, no new dependencies.

## Global Constraints

- **No new hardcoded spell-slot table.** The shared multiclass pool is looked up via `catalog.class_level_row(<a full-caster class id>, combined_level)["spellcasting"]` — the anchor class id is arbitrary (any full caster works, since the table is class-agnostic at a given level, confirmed empirically), not tied to which casters the resolving character actually has.
- **Full casters** (Bard, Cleric, Druid, Sorcerer, Wizard) contribute their own class level to the combined total; **half casters** (`HALF_CASTER_CLASSES` in `catalog/reference_data.py` — Paladin, Ranger) contribute `level // 2`; **Warlock contributes zero** and is excluded entirely, keeping its own separate Pact Magic slots (already read correctly by existing single-class code, unchanged by this plan — only newly EXPOSED via a dedicated `derived` field).
- **Empty-collection-not-null convention**: `derived.spellSlots`/`derived.warlockSpellSlots` are always dicts (never `null`) — empty `{}` when no applicable caster is present, matching how `sheet.proficiencies.skills` defaults to `[]` not `null` elsewhere in this codebase.
- **Breaking change, no dual-shape support** (consistent with every prior phase): `derived.spellSaveDC`/`spellAttackBonus` (currently top-level scalars) are REMOVED from `derived` and added to each entry of `sheet.spells` (the `SheetClassSpells`/per-class-spells list, already established in Phase 3b-i) instead.
- **No interactive slot-tracking UI in this phase** — the Resolution is a from-scratch-computed snapshot on every request, not a mutable play-state tracker (matching how HP is shown as a max, not a "currently remaining" value). This plan adds the computed numbers to the Resolution and keeps the frontend types correct; it does NOT add slot-checkbox widgets or any "mark a slot used" interaction.
- **Every fix verified against real bundled SRD data** — this project's standing discipline, unbroken across 8+ phases so far.

---

### Task 1: Pure spell-slot math — `combined_caster_level` and `multiclass_spell_slots`

**Files:**
- Modify: `server/engine/spells.py`
- Test: `server/tests/test_engine_spells.py`

**Interfaces:**
- Consumes: `HALF_CASTER_CLASSES` (already exists in `catalog/reference_data.py`).
- Produces: `combined_caster_level(class_entries: list[tuple[str, int]]) -> int`, `multiclass_spell_slots(catalog: Catalog, combined_level: int) -> dict[str, int]`, `warlock_pact_magic_slots(level_row: dict | None) -> dict[str, int]`.

- [ ] **Step 1: Write the failing tests**

Read `server/tests/test_engine_spells.py` first to see its existing conventions — it already tests `spellcasting_ability`/`known_spell_count`/`spell_save_dc`/`spell_attack_bonus`, but ALL of its existing tests use hand-built dicts (e.g. `_WIZARD`, `_BARD_ROW`), not the real catalog — there is no `catalog` fixture in this file today, and no shared one in `server/tests/conftest.py` either (confirmed: `conftest.py` only sets up `sys.path`, nothing else). The new tests below for `multiclass_spell_slots`/`warlock_pact_magic_slots` need real bundled SRD data (per this project's standing discipline), so add a module-scoped fixture at the top of this file, mirroring `test_resolve.py`'s exact pattern:

```python
import pytest
from catalog.loader import load

@pytest.fixture(scope="module")
def catalog():
    return load()
```

(`combined_caster_level`'s own tests don't need the catalog — they're pure integer math — only the `multiclass_spell_slots`/`warlock_pact_magic_slots` tests take the `catalog` fixture parameter.)

```python
def test_combined_caster_level_single_full_caster_equals_its_own_level():
    assert combined_caster_level([("wizard", 5)]) == 5


def test_combined_caster_level_two_full_casters_sums_directly():
    assert combined_caster_level([("wizard", 3), ("sorcerer", 2)]) == 5


def test_combined_caster_level_half_caster_contributes_floor_half():
    assert combined_caster_level([("paladin", 5)]) == 2  # 5 // 2 == 2
    assert combined_caster_level([("paladin", 1)]) == 0  # 1 // 2 == 0, no special-case needed


def test_combined_caster_level_full_plus_half_caster():
    assert combined_caster_level([("cleric", 4), ("paladin", 4)]) == 4 + (4 // 2)  # == 6


def test_combined_caster_level_excludes_warlock_entirely():
    assert combined_caster_level([("wizard", 3), ("warlock", 5)]) == 3


def test_combined_caster_level_excludes_non_caster_classes():
    assert combined_caster_level([("wizard", 3), ("fighter", 5)]) == 3


def test_combined_caster_level_empty_list_is_zero():
    assert combined_caster_level([]) == 0


def test_multiclass_spell_slots_matches_a_full_caster_own_table(catalog):
    # Regression anchor: at combined level 5, the shared pool must equal
    # Wizard's own real level-5 slots from the bundled SRD data — not a
    # hand-typed guess, read directly from the catalog.
    wizard_lvl5 = catalog.class_level_row("wizard", 5)["spellcasting"]
    expected = {str(n): wizard_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl5[f"spell_slots_level_{n}"] > 0}
    assert multiclass_spell_slots(catalog, 5) == expected


def test_multiclass_spell_slots_zero_combined_level_is_empty(catalog):
    assert multiclass_spell_slots(catalog, 0) == {}


def test_warlock_pact_magic_slots_reads_directly_from_its_own_level_row(catalog):
    # Confirmed directly against the bundled data while writing this plan:
    # Warlock at character level 3 has 2 slots at 2nd spell level, zero
    # elsewhere — Pact Magic's real, non-obvious curve (fewer, higher-level
    # slots than a full caster of the same level), not a hand-typed guess.
    warlock_lvl3 = catalog.class_level_row("warlock", 3)["spellcasting"]
    result = warlock_pact_magic_slots(warlock_lvl3)
    assert result == {"2": 2}
    assert result == {"2": warlock_lvl3["spell_slots_level_2"]}


def test_warlock_pact_magic_slots_none_row_is_empty():
    assert warlock_pact_magic_slots(None) == {}
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_spells.py -v -k "combined_caster or multiclass_spell_slots or warlock_pact_magic"`
Expected: FAIL (functions don't exist yet — `ImportError` or `NameError`).

- [ ] **Step 3: Implement**

In `server/engine/spells.py`, add near the top (after the existing `HALF_CASTER_CLASSES` import):

```python
from catalog.loader import Catalog

# Warlock's Pact Magic is the ONLY spell-slot progression in the bundled
# SRD data that is NOT part of the shared multiclass pool — it stays
# entirely separate per RAW. A set (not a single string) for the same
# reason HALF_CASTER_CLASSES is a set: extensible if a future data
# source adds another Pact-Magic-style class.
PACT_MAGIC_CLASSES = {"warlock"}

# Any full-caster class id works as a lookup anchor for the shared
# multiclass slot table below — verified empirically (Phase 3b-ii design
# spec) that the standard multiclass table is number-for-number
# identical to any full caster's own single-class slot progression at
# the same level. This class doesn't need to be present in the
# resolving character's own classes; it's a pure data-lookup anchor.
_MULTICLASS_SLOT_TABLE_ANCHOR_CLASS = "wizard"


def combined_caster_level(class_entries: list[tuple[str, int]]) -> int:
    """Sum each class's contribution to 5e's combined multiclass caster
    level: full casters contribute their own level, half casters
    (HALF_CASTER_CLASSES) contribute level // 2, Warlock (and any other
    PACT_MAGIC_CLASSES) and any non-caster class contribute 0."""
    total = 0
    for cls_id, level in class_entries:
        if cls_id in PACT_MAGIC_CLASSES:
            continue
        if cls_id in HALF_CASTER_CLASSES:
            total += level // 2
        else:
            total += level
    return total


def multiclass_spell_slots(catalog: Catalog, combined_level: int) -> dict[str, int]:
    """The shared spell-slot pool for every non-Warlock caster, looked
    up at the combined caster level. Only nonzero slot levels are
    included. combined_level <= 0 (no full/half casters present, or
    they're all below their first spell-granting level) returns {}."""
    if combined_level <= 0:
        return {}
    row = catalog.class_level_row(_MULTICLASS_SLOT_TABLE_ANCHOR_CLASS, combined_level)
    if not row:
        return {}
    spellcasting = row.get("spellcasting") or {}
    return {
        str(n): spellcasting[f"spell_slots_level_{n}"]
        for n in range(1, 10)
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0
    }


def warlock_pact_magic_slots(level_row: dict | None) -> dict[str, int]:
    """Warlock's own Pact Magic slots, read directly from its OWN level
    row (not the shared multiclass table) — pass catalog.class_level_row
    ("warlock", <warlock's own class level>)["spellcasting"] as the level
    argument's dict, or None if no Warlock is present."""
    if not level_row:
        return {}
    return {
        str(n): level_row[f"spell_slots_level_{n}"]
        for n in range(1, 10)
        if level_row.get(f"spell_slots_level_{n}", 0) > 0
    }
```

Fix the import placement if `Catalog` isn't already importable this way — check `server/engine/resolve.py`'s own `from catalog.loader import Catalog` line for the exact correct import path before assuming this snippet's import is right.

- [ ] **Step 4: Fix the placeholder test and run to verify all pass**

Fix `test_multiclass_spell_slots_zero_combined_level_is_empty` to use the real `catalog` fixture parameter (`def test_multiclass_spell_slots_zero_combined_level_is_empty(catalog): assert multiclass_spell_slots(catalog, 0) == {}`).

Run: `cd server && .venv/bin/python -m pytest tests/test_engine_spells.py -v`
Expected: PASS, all cases.

- [ ] **Step 5: Empirically sweep a few real multiclass combinations**

From `server/`:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.spells import combined_caster_level, multiclass_spell_slots, warlock_pact_magic_slots
catalog = load()
print('Wizard3/Sorcerer2:', multiclass_spell_slots(catalog, combined_caster_level([('wizard',3),('sorcerer',2)])))
print('Cleric4/Paladin4:', multiclass_spell_slots(catalog, combined_caster_level([('cleric',4),('paladin',4)])))
print('Fighter5/Rogue5 (no casters):', multiclass_spell_slots(catalog, combined_caster_level([('fighter',5),('rogue',5)])))
wl_row = catalog.class_level_row('warlock', 5)['spellcasting']
print('Warlock5 pact slots:', warlock_pact_magic_slots(wl_row))
"
```

Confirm the Fighter/Rogue case prints `{}` and the Warlock case shows a real, nonzero slot dict at the correct spell level for character level 5 (cross-check against the bundled data directly if the number looks surprising, don't just assume it's right).

- [ ] **Step 6: Commit**

```bash
git add server/engine/spells.py server/tests/test_engine_spells.py
git commit -m "$(cat <<'EOF'
feat: combined caster level and multiclass spell-slot lookup

Pure math only, no resolve() wiring yet. combined_caster_level() sums
each class's contribution per RAW (full casters their own level, half
casters level//2, Warlock excluded entirely). multiclass_spell_slots()
looks up the shared pool via any full caster's own level row — no new
hardcoded table needed, since the standard multiclass table is
identical to a full caster's own single-class progression at the same
level (verified against the bundled SRD data). warlock_pact_magic_slots()
exposes Warlock's already-existing, entirely separate slot data.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Wire spell slots and per-caster DC/attack bonus into `resolve()`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `combined_caster_level`, `multiclass_spell_slots`, `warlock_pact_magic_slots` (Task 1), `PACT_MAGIC_CLASSES` (Task 1).
- Produces: `derived["spellSlots"]: dict[str, int]`, `derived["warlockSpellSlots"]: dict[str, int]` (new fields). Each entry of the existing `spells_summary` list (which becomes `sheet["spells"]`) gains `"spellSaveDC"`/`"spellAttackBonus"`. `derived["spellSaveDC"]`/`derived["spellAttackBonus"]` (the old top-level scalars) are REMOVED.

- [ ] **Step 1: Read the current code precisely**

Read `server/engine/resolve.py` in full, focusing on:
- The `spells_summary` loop (search for `spells_summary: list[dict] = []` — currently builds `{"classId", "cantrips", "known"}` per caster, no DC/attack-bonus).
- The current top-level `spell_save_dc`/`spell_attack_bonus` computation (search for `spell_save_dc = None` — currently primary-class-only, using `cls`/`spell_ability`/`prof_bonus`).
- The `derived = {...}` dict construction (search for `"spellSaveDC": spell_save_dc,` and `"spellAttackBonus": spell_attack_bonus,` — these two lines get REMOVED, replaced by two NEW lines for `spellSlots`/`warlockSpellSlots`).
- `prof_bonus_lookup_cls_id`/`total_level` (already computed above this section — reuse `total_level` directly, it's already the correct, validated total across every class).

- [ ] **Step 2: Write the failing tests**

Add to `server/tests/test_resolve.py` (read the file first to match its conventions — `_fighter_acolyte_human_draft`, real `catalog` fixture, etc.):

```python
def test_single_caster_spell_slots_match_their_own_level_table(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    wizard_lvl5 = catalog.class_level_row("wizard", 5)["spellcasting"]
    expected = {str(n): wizard_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl5[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_two_full_casters_share_a_combined_slot_pool(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 3, "choices": {}},
            {"classId": "sorcerer", "level": 2, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 14, "WIS": 10, "CHA": 14}},
    )
    resolution = resolve(draft, catalog)
    wizard_lvl5 = catalog.class_level_row("wizard", 5)["spellcasting"]  # combined level 3+2=5
    expected = {str(n): wizard_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl5[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected


def test_warlock_alongside_a_full_caster_keeps_pact_magic_separate(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 3, "choices": {}},
            {"classId": "warlock", "level": 3, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 14, "WIS": 10, "CHA": 14}},
    )
    resolution = resolve(draft, catalog)
    # Combined pool should reflect ONLY Wizard's level (3), Warlock excluded.
    wizard_lvl3 = catalog.class_level_row("wizard", 3)["spellcasting"]
    expected_shared = {str(n): wizard_lvl3[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl3[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected_shared
    warlock_lvl3 = catalog.class_level_row("warlock", 3)["spellcasting"]
    expected_warlock = {str(n): warlock_lvl3[f"spell_slots_level_{n}"] for n in range(1, 10) if warlock_lvl3[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["warlockSpellSlots"] == expected_warlock
    assert resolution["derived"]["spellSlots"] != resolution["derived"]["warlockSpellSlots"]


def test_non_caster_multiclass_has_empty_spell_slots(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "rogue", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["spellSlots"] == {}
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_derived_no_longer_has_top_level_spell_save_dc_or_attack_bonus(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert "spellSaveDC" not in resolution["derived"]
    assert "spellAttackBonus" not in resolution["derived"]


def test_each_caster_in_sheet_spells_carries_its_own_save_dc_and_attack_bonus(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 3, "choices": {
                "class:wizard:spells-cantrips": ["fire-bolt"],
                "class:wizard:spells-known": ["magic-missile"],
            }},
        ],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    wizard_entry = next(s for s in resolution["sheet"]["spells"] if s["classId"] == "wizard")
    # INT 16 -> +3 modifier; prof bonus at level 3 is 2 -> DC 8+2+3=13, attack +2+3=5.
    assert wizard_entry["spellSaveDC"] == 13
    assert wizard_entry["spellAttackBonus"] == 5
```

(Verify the exact valid cantrip/spell ids for Wizard — `fire-bolt`/`magic-missile` — against the real catalog before trusting them; substitute real valid ids if these aren't actually available at Wizard level 3 in the bundled data.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "spell_slots or pact_magic or save_dc_or_attack_bonus or spells_share"`
Expected: FAIL.

- [ ] **Step 4: Implement**

Add the import at the top of `server/engine/resolve.py` (alongside the existing `from . import spells as spells_mod`):

```python
from .spells import combined_caster_level, multiclass_spell_slots, warlock_pact_magic_slots, PACT_MAGIC_CLASSES
```

(Adjust to match whatever the existing import style is — this file may import the whole `spells` module as `spells_mod` rather than individual names; if so, call these as `spells_mod.combined_caster_level(...)` etc. instead, matching the established pattern.)

Find the `spells_summary` loop (from Task 5/3b-i) and extend each appended dict with per-caster DC/attack bonus:

```python
    spells_summary: list[dict] = []
    for rc in resolved_classes:
        rc_cls, rc_cls_id = rc["cls"], rc["cls_id"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_cantrip_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-cantrips"), None)
        rc_known_spells_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-known"), None)
        if not (rc_cantrip_choice or rc_known_spells_choice):
            continue
        rc_spell_ability = spells_mod.spellcasting_ability(rc_cls)
        rc_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        rc_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        spells_summary.append({
            "classId": rc_cls_id,
            "cantrips": _spell_summaries(rc_cantrip_choice),
            "known": _spell_summaries(rc_known_spells_choice),
            "spellSaveDC": rc_save_dc,
            "spellAttackBonus": rc_attack_bonus,
        })
```

Remove (or repurpose) the OLD top-level computation:

```python
    spell_ability = spells_mod.spellcasting_ability(cls) if cls else None
    has_spellcasting_this_level = bool(cantrip_choice or known_spells_choice)
    spell_save_dc = None
    spell_attack_bonus = None
    if has_spellcasting_this_level and spell_ability:
        spell_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[spell_ability])
        spell_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[spell_ability])
```

Delete this block entirely — `spell_save_dc`/`spell_attack_bonus` are no longer used anywhere once the `derived = {...}` dict's two lines referencing them are also removed (next step). If `cantrip_choice`/`known_spells_choice` (the OLD primary-only lookups, from before Task 5/3b-i's `spells_summary` loop existed) are now completely unused elsewhere in the function after this removal, delete them too — grep the rest of the file for `cantrip_choice`/`known_spells_choice` to confirm before deleting.

Add the new spell-slot computation, placed after `modifiers`/`total_level` are both available and after `resolved_classes` is fully built (any point after both, before the `derived = {...}` dict construction):

```python
    caster_level_entries = [(rc["cls_id"], rc["level"]) for rc in resolved_classes if rc["cls"]]
    shared_combined_level = combined_caster_level(caster_level_entries)
    spell_slots = multiclass_spell_slots(catalog, shared_combined_level)
    warlock_entry = next((rc for rc in resolved_classes if rc["cls_id"] in PACT_MAGIC_CLASSES and rc["cls"]), None)
    warlock_level_row = catalog.class_level_row(warlock_entry["cls_id"], warlock_entry["level"])["spellcasting"] if warlock_entry else None
    warlock_slots = warlock_pact_magic_slots(warlock_level_row)
```

In the `derived = {...}` dict, replace:

```python
        "spellSaveDC": spell_save_dc,
        "spellAttackBonus": spell_attack_bonus,
```

with:

```python
        "spellSlots": spell_slots,
        "warlockSpellSlots": warlock_slots,
```

Finally, find where `sheet["spells"]` is assigned (should already be `spells_summary` from Phase 3b-i) — confirm this still works unchanged now that `spells_summary`'s entries carry two more keys.

- [ ] **Step 5: Run to verify new tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "spell_slots or pact_magic or save_dc_or_attack_bonus or spells_share"`
Expected: PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `cd server && .venv/bin/python -m pytest -v`

Expected: some EXISTING tests will fail — specifically any that assert `resolution["derived"]["spellSaveDC"]`/`resolution["derived"]["spellAttackBonus"]` as top-level fields (this is expected fallout from the deliberate breaking change, not a regression; investigate each failure to confirm it's exactly this class of expected change — an old assertion checking the now-removed top-level field — before updating it to check the new per-caster location inside `sheet["spells"]` instead). Fix each such test, matching this plan's Global Constraints. No OTHER test should need a changed expected value.

- [ ] **Step 7: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: wire multiclass spell slots into resolve(), move DC/attack to per-caster

derived.spellSlots (shared pool, every non-Warlock caster) and
derived.warlockSpellSlots (Warlock's own, entirely separate Pact Magic)
are new — spell slots were not exposed anywhere in the Resolution
before this, not even for a single-class caster. derived.spellSaveDC/
spellAttackBonus (previously single, primary-class-only scalars) move
into each sheet.spells entry as per-caster values, since a multiclass
character's casters each have their own save DC/attack bonus based on
their own spellcasting ability.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Update export consumers for the new spell-slot and per-caster DC/attack shape

**Files:**
- Modify: `server/export.py`, `server/markdown_export.py`, `server/pdf_export.py`
- Test: `server/tests/test_export.py`, `server/tests/test_markdown_export.py`, `server/tests/test_pdf_export.py`

**Interfaces:**
- Consumes: `derived["spellSlots"]`, `derived["warlockSpellSlots"]`, each `sheet["spells"][i]["spellSaveDC"]`/`["spellAttackBonus"]` (Task 2).

- [ ] **Step 1: Read all three export consumers' current spell-rendering logic in full**

`server/export.py` passes the whole `resolution` dict through to YAML — confirm this needs NO code change (verify by reading it; if it dumps `resolution` or `sheet`/`derived` wholesale, the new fields already flow through automatically — just needs a new/updated test asserting they appear).

`server/markdown_export.py`/`server/pdf_export.py` (per Phase 3b-i's final review, these currently print ONE top-level "Spell Save DC / Attack Bonus" line, attributable only to the primary caster, ambiguous once multiple casters exist) — read their current spell-section rendering code in full before editing.

- [ ] **Step 2: Write failing tests**

For `test_markdown_export.py` and `test_pdf_export.py` (mirror the exact pattern each file already uses for its OTHER multiclass tests from Phase 3b-i — hand-built `Resolution`-shaped fixture dicts, not going through `resolve()`, per this project's established convention for these two files):

```python
def test_each_casters_spell_save_dc_and_attack_bonus_render_labeled_by_class():
    resolution = {
        "sheet": {
            # ...existing fixture shape, plus:
            "spells": [
                {"classId": "wizard", "cantrips": [], "known": [], "spellSaveDC": 13, "spellAttackBonus": 5},
                {"classId": "cleric", "cantrips": [], "known": [], "spellSaveDC": 14, "spellAttackBonus": 6},
            ],
            # ...
        },
        "derived": {
            # ...existing fixture shape, plus:
            "spellSlots": {"1": 3, "2": 1},
            "warlockSpellSlots": {},
            # ...
        },
        # ...
    }
    result = to_markdown(resolution)  # or to_pdf + pypdf text extraction, matching this file's existing pattern
    assert "13" in result and "wizard" in result.lower()  # adjust to the real rendered format once written
    assert "14" in result and "cleric" in result.lower()
```

(This is a sketch — read each file's EXISTING multiclass test fixture from Phase 3b-i in full first and extend it precisely rather than writing a new fixture from scratch, matching each file's established conventions for asserting on rendered text.)

Also add a slot-tracker rendering test (e.g. `"1st: 3"` / `"2nd: 1"` or however the plan's Step 3 implementation ends up formatting it — write the test to match whatever format you implement, keeping it simple and readable) and a Warlock-slots-shown-separately test when `warlockSpellSlots` is non-empty.

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_markdown_export.py tests/test_pdf_export.py -v -k "slot or save_dc"`
Expected: FAIL.

- [ ] **Step 4: Implement**

In both `markdown_export.py` and `pdf_export.py` (matching their established mirrored-duplication convention — the same logic written twice, once per file, not shared):
- Replace the old single ambiguous "Spell Save DC / Attack Bonus" line with per-caster lines, one per entry in `sheet["spells"]`, each labeled with that class's name (look up the display name from `sheet["classes"]` by matching `classId`, or from the catalog if that's more consistent with how `_class_label` already works — check the existing pattern before choosing).
- Render `derived["spellSlots"]` as a simple "Spell Slots: 1st 4, 2nd 3, ..." line (or whatever format matches each file's existing style for compact key-value data — check how e.g. currency or other small dicts are already rendered in these files for a consistent precedent) — only when non-empty.
- Render `derived["warlockSpellSlots"]` as a SEPARATE, clearly-labeled line (e.g. "Pact Magic Slots: ...") — only when non-empty.

- [ ] **Step 5: Update `test_export.py`**

Add a test confirming `to_yaml`'s output (parsed back) contains `derived["spellSlots"]`/`["warlockSpellSlots"]` and each `sheet["spells"][i]["spellSaveDC"]`/`["spellAttackBonus"]` — should require no production code change to `export.py` itself if Step 1 confirmed it's a pure pass-through; this test exists to PROVE that, not to drive new code.

- [ ] **Step 6: Run to verify all export tests pass**

Run: `cd server && .venv/bin/python -m pytest tests/test_export.py tests/test_markdown_export.py tests/test_pdf_export.py -v`
Expected: PASS. Also fix any OTHER existing test in these three files that referenced the old top-level `spellSaveDC`/`spellAttackBonus` fixture shape (same class of expected fallout as Task 2's Step 6).

- [ ] **Step 7: Run the full backend suite**

Run: `cd server && .venv/bin/python -m pytest -v`
Expected: all passing, no unexpected failures.

- [ ] **Step 8: Empirical end-to-end check**

From `server/`, resolve a real multi-caster draft (e.g. Wizard 3 / Cleric 2) and generate all three export formats directly, confirming each caster's DC/attack bonus and the shared slot pool render correctly and distinguishably:

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf
catalog = load()
draft = {
    'name': 'Multi Test', 'sources': ['srd'],
    'classes': [
        {'classId': 'wizard', 'level': 3, 'choices': {}},
        {'classId': 'cleric', 'level': 2, 'choices': {}},
    ],
    'background': {'choices': {}}, 'species': {'choices': {}},
    'abilities': {'method': 'manual', 'base': {'STR': 10, 'DEX': 10, 'CON': 10, 'INT': 16, 'WIS': 14, 'CHA': 10}},
    'equipment': {'choices': {}, 'added': [], 'skipped': True},
    'details': {},
}
r = resolve(draft, catalog)
print('spellSlots:', r['derived']['spellSlots'])
print('sheet.spells:', r['sheet']['spells'])
print(to_markdown(r))
"
```

- [ ] **Step 9: Commit**

```bash
git add server/export.py server/markdown_export.py server/pdf_export.py server/tests/test_export.py server/tests/test_markdown_export.py server/tests/test_pdf_export.py
git commit -m "$(cat <<'EOF'
feat: render multiclass spell slots and per-caster DC/attack in exports

Replaces the old single, ambiguous top-level Spell Save DC/Attack Bonus
line (attributable to whichever class happened to be primary) with one
labeled line per caster, plus the shared spell-slot pool and Warlock's
separate Pact Magic slots when present.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Frontend type sync

**Files:**
- Modify: `frontend/src/types.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Derived.spellSlots: Record<string, number>`, `Derived.warlockSpellSlots: Record<string, number>` (new); `Derived.spellSaveDC`/`spellAttackBonus` (removed); `SheetClassSpells.spellSaveDC: number | null`, `SheetClassSpells.spellAttackBonus: number | null` (new).

- [ ] **Step 1: Update `SheetClassSpells`**

In `frontend/src/types.ts`, find:

```typescript
export interface SheetClassSpells {
  classId: string;
  cantrips: SheetSpellSummary[];
  known: SheetSpellSummary[];
}
```

Replace with:

```typescript
export interface SheetClassSpells {
  classId: string;
  cantrips: SheetSpellSummary[];
  known: SheetSpellSummary[];
  spellSaveDC: number | null;
  spellAttackBonus: number | null;
}
```

- [ ] **Step 2: Update `Derived`**

Find:

```typescript
  spellSaveDC: number | null;
  spellAttackBonus: number | null;
```

(inside the `Derived` interface) and replace with:

```typescript
  spellSlots: Record<string, number>;
  warlockSpellSlots: Record<string, number>;
```

- [ ] **Step 3: Grep for consumers of the removed fields**

Run: `grep -rn "\.spellSaveDC\|\.spellAttackBonus\|derived\.spellSaveDC\|derived\.spellAttackBonus" frontend/src`

Fix any consumer reading these as top-level `Derived` fields — Phase 3b-i's final review confirmed there were ZERO frontend consumers of `sheet.spells`/`Derived` spell fields at that point, but re-verify this is still true now (a later small change might have added one) rather than assuming.

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: PASS with zero errors. If any consumer WAS found in Step 3 and needs more than a trivial fix, use judgment matching this project's established "minimal fix now, no full UI feature" scope for this plan (per the Global Constraints — no interactive slot UI is in scope here).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts
git commit -m "$(cat <<'EOF'
refactor: sync frontend types with the new spell-slot/per-caster DC shape

Derived.spellSlots/warlockSpellSlots replace the removed top-level
spellSaveDC/spellAttackBonus scalars; SheetClassSpells gains its own
per-caster spellSaveDC/spellAttackBonus fields, matching the backend
shape change in server/engine/resolve.py.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- Task 1's tests are pure-function tests with no `resolve()` involvement — fast, isolated, and they anchor the "no new hardcoded table" claim directly against real catalog data (the `test_multiclass_spell_slots_matches_a_full_caster_own_table` test literally reads Wizard's own row and asserts equality, rather than hardcoding expected numbers by hand).
- Task 2 is the only task that touches `resolve()`'s core — kept as narrow as possible (one new computation block, one dict-key swap, no changes to the per-class loop structure Phase 3b-i built).
- Task 3's export-consumer test sketches are intentionally left less exhaustively pre-written than earlier phases' plans (e.g. Phase 3b-i's Task 5) — this project's history shows export-consumer rendering-format decisions (exact wording, exact layout) are better left to the implementer matching each file's existing established conventions than dictated in the plan, since dictating exact rendered strings in a plan has previously drifted from what implementers found cleanest against the real surrounding code (see Phase 3b-i's Task 3/Task 7 review notes on implementers correctly deviating from over-specified brief snippets).
- Task 4 is deliberately tiny and type-only, matching Phase 3b-i's own Task 6's frontend-type-sync scope.
