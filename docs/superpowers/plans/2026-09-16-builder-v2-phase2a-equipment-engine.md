# Builder v2 Phase 2a — Equipment Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the `resolve()` engine real equipment support — the one major piece of the architecture spec's §8 EQUIPMENT step that Phase 1a deliberately deferred. Concretely: resolve a class's and background's starting-equipment choices into real `Choice`s wherever the bundled SRD data actually supports it (some options genuinely can't be — see Global Constraints), surface fixed (non-choice) starting gear on the sheet, accept manually-added items from the Draft, and compute Armor Class from whatever armor/shield is actually equipped instead of always assuming unarmored. This is backend-only — the frontend Equipment page (browsing/adding/equipping items) is a separate, later plan (Phase 2b), the same two-part split Phase 1 used.

**Architecture:** Extends the existing `server/catalog/` and `server/engine/` packages from Phase 1a — no new top-level packages. `catalog/loader.py` gains an `items` index. `catalog/choices.py` gains one more resolvable option shape (`multiple`, a fixed bundle of items — e.g. "leather armor, a longbow, and 20 arrows" as a single pickable option). A new `engine/equipment.py` holds pure AC-from-armor math, mirroring `engine/derived.py`'s style. `engine/resolve.py` gains equipment choice-template generation and wires the new AC computation in. `server/app.py` gains one read endpoint, `GET /api/items`.

**Tech Stack:** Same as Phase 1a — Python 3, Flask, pytest. No new dependencies.

## Global Constraints

- **Not every starting-equipment choice can be represented as a `Choice` yet — some are dropped entirely, not faked.** The SRD's `starting_equipment_options` envelopes sometimes nest an `option_type: "choice"` *inside* another option (e.g. Fighter's "(a) a martial weapon and a shield or (b) two martial weapons" — picking "a martial weapon" is itself a sub-choice from a whole weapon category). The flat `Choice` model (one `count`, one flat `options[]` list) has no way to represent a choice nested inside a choice. `catalog/choices.py`'s `build_choice_options` must recognize this shape and skip that one option (or, if every option in the envelope has this shape, skip the whole choice) — never flatten it into something misleading, and never crash. This is the same "return `None` rather than fake it" discipline Phase 1a already established for `equipment_category` — extend it, don't relax it. `option_set_type: "equipment_category"` itself (e.g. "any martial weapon", "any holy symbol") stays unresolved in this phase too, for the same reason Phase 1a left it unresolved: mapping the SRD's many named sub-categories ("martial-weapons", "holy-symbols", "artisans-tools", ...) onto the bundled `Equipment.json`'s own category fields (`weapon_category`, `armor_category`, top-level `equipment_category`) is real, maintenance-heavy work with low payoff here — every case that would benefit from it in the bundled data is *also* nested inside a `choice`-in-`choice` shape this phase already can't represent, so there is nothing to gain by solving only half the problem. Leave it for whenever a richer data source (Phase 4) makes the category structure explicit.
- **Items obtained via a starting-equipment `Choice` are always treated as equipped.** There is no per-item equip/unequip toggle for kit items in this phase — that UI concept (per the architecture spec's "Current Inventory" section) applies to items added later through the item browser (`draft.equipment.added`, which already carries an explicit `equipped: boolean` per Phase 0's `Draft` type), not to what a class/background choice starts you with. Don't build a toggle for kit items; there is nowhere in the Draft shape to store it yet, and inventing one is out of scope.
- **A bundle choice option's `id` is the `+`-joined list of its constituent item indices** (e.g. `"leather-armor+longbow+arrow"`), never a synthetic/opaque id. This is deliberate, not a shortcut: it lets the engine parse a selected bundle id back into real item lookups for AC computation without inventing a second storage location for "what's actually in this bundle." SRD item indices are lowercase-hyphenated and never contain `+` (verified directly against `chargen/data/srd/5e-SRD-Equipment.json` — no exceptions), so splitting on `+` is safe. Quantities are dropped from the id (kept only in the display label) — this is acceptable because the only per-choice-bundle item that ever matters for this phase's computation is armor/shields, and every SRD armor/weapon in a starting bundle has a fixed count of 1; only ammunition (arrows, bolts) has count > 1, and ammunition never affects AC.
- **`resolve()` still never throws on an incomplete or malformed draft**, extending the same guarantee Phase 1a built. `draft.equipment` may be entirely absent, `draft.equipment.choices` may be absent or non-dict, `draft.equipment.added` may be absent, non-list, or contain entries with an unknown `itemId` — every one of these degrades gracefully (missing/invalid pieces are just empty/skipped), never an exception.
- **The `Resolution` JSON shape's existing fields are unchanged.** This phase adds NEW keys under `sheet.equipment` and extends `derived.armorClass`'s *computation* (no longer hardcoded to unarmored), but does not rename or remove anything Phase 1a already returns. `choices[]` entries with `source.kind: "equipment"` follow the exact same `{id, source, label, description, count, options, selected, status}` shape as every other choice kind — nothing equipment-specific leaks into that contract.
- **No frontend changes in this plan.** `frontend/src/types.ts`'s `Draft.equipment` type does not yet have a `choices` field — this plan's engine reads `draft.get("equipment", {}).get("choices", {})` defensively (missing key → `{}`, never a crash), and Phase 2b is responsible for adding that field to the TS `Draft` type and building the UI that populates it. Until Phase 2b lands, no real frontend ever sends equipment choice selections — that's fine and expected, exactly like Phase 1a's engine work landing before Phase 1b's UI did.

---

### Task 1: Catalog item index + bundle-choice resolution

**Files:**
- Modify: `server/catalog/loader.py`
- Modify: `server/catalog/choices.py`
- Modify: `server/tests/test_loader.py`
- Modify: `server/tests/test_choices.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `Catalog.items: dict[str, dict]` (every `chargen/data/srd/5e-SRD-Equipment.json` entry indexed by `index`) — Task 3 is the consumer. `catalog.choices.build_choice_options` now also resolves `option_type: "multiple"` bundles inside an `options_array` — Task 3 is the consumer (indirectly, via `build_choice_template`, unchanged).

- [ ] **Step 1: Write the failing loader test**

Add to `server/tests/test_loader.py`:

```python
def test_items_indexed_by_srd_index_covers_all_categories():
    catalog = load()
    assert len(catalog.items) == 237
    assert catalog.items["chain-mail"]["armor_category"] == "Heavy"
    assert catalog.items["longbow"]["weapon_category"] == "Martial"
    assert catalog.items["dungeoneers-pack"]["equipment_category"]["index"] == "adventuring-gear"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_loader.py::test_items_indexed_by_srd_index_covers_all_categories -v`
Expected: FAIL — `Catalog` has no `items` field yet.

- [ ] **Step 3: Add the `items` index to `server/catalog/loader.py`**

In the `Catalog` dataclass, add a new field (alongside the existing `classes`, `levels`, etc.):

```python
    items: dict[str, dict] = field(default_factory=dict)
```

In `load()`, add it to the returned `Catalog(...)` call:

```python
        items=_index_by(_load("5e-SRD-Equipment.json")),
```

(Both edits go into the existing `Catalog` dataclass and `load()` function — do not restructure either; this is a one-field addition to each, following the exact pattern every other indexed field already uses.)

- [ ] **Step 4: Run the loader test to verify it passes**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_loader.py -v`
Expected: all PASS (the new test plus every pre-existing one, unaffected).

- [ ] **Step 5: Write the failing bundle-resolution tests**

Add to `server/tests/test_choices.py`:

```python
def test_multiple_bundle_of_counted_references_resolves_to_one_option():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][0]  # "(a) chain mail or (b) leather armor, longbow, and 20 arrows"
    options = build_choice_options(envelope["from"])
    assert options is not None
    assert len(options) == 2
    ids = {o["id"] for o in options}
    assert "chain-mail" in ids
    assert "leather-armor+longbow+arrow" in ids
    bundle = next(o for o in options if o["id"] == "leather-armor+longbow+arrow")
    assert "Leather Armor" in bundle["label"]
    assert "Longbow" in bundle["label"]
    assert "20x Arrow" in bundle["label"]


def test_multiple_bundle_with_a_nested_choice_is_dropped_not_faked():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][1]  # "(a) a martial weapon and a shield or (b) two martial weapons"
    # Both options in this envelope nest an option_type "choice" somewhere —
    # neither is resolvable in this phase, so the whole envelope resolves to
    # no options at all, which build_choice_options reports as None (its
    # established "nothing resolvable" signal, same as an all-empty
    # options_array).
    assert build_choice_options(envelope["from"]) is None


def test_simple_multiple_bundle_alongside_a_plain_counted_reference():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][2]  # "(a) a light crossbow and 20 bolts or (b) two handaxes"
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert "crossbow-light+crossbow-bolt" in ids
    assert "handaxe" in ids


def test_two_plain_counted_reference_options_both_resolve():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][3]  # "(a) a dungeoneer's pack or (b) an explorer's pack"
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert ids == {"dungeoneers-pack", "explorers-pack"}
```

- [ ] **Step 6: Run them to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_choices.py -v -k bundle`
Expected: the first three FAIL (no `multiple` handling yet — a bundle currently produces no options since `_option_label` returns `None` for `option_type: "multiple"`, making `build_choice_options` treat the whole entry as unresolvable already by accident, not by design — the fourth test should already pass, since plain `counted_reference` options were already handled in Phase 1a).

- [ ] **Step 7: Add bundle resolution to `server/catalog/choices.py`**

First, update the module docstring's now-stale claim. Find this sentence (it's part of the file's top docstring, right before the closing `"""`):

```
`equipment_category`-based option sets (used by starting_equipment_options)
are NOT resolved here — equipment choices are out of scope until Phase 2,
so any envelope needing that path returns None, and every caller must skip
a None result entirely rather than emit a partial or broken choice.
```

and replace it with:

```
`equipment_category`-based option sets (used by starting_equipment_options)
are still NOT resolved here — every case that would need it in the bundled
data is also nested inside an unrepresentable option_type "choice" (see
build_choice_options' "multiple" handling below), so there's nothing to
gain by solving only half of that problem in Phase 2a. A "multiple" bundle
(e.g. "leather armor, a longbow, and 20 arrows") IS resolved, as one
combined option, but only when every item inside it is a plain
counted_reference — a bundle containing its own nested sub-choice returns
None for that one option, same "skip rather than fake it" discipline as
everything else in this module.
```

Then add this function above `build_choice_options`:

```python
def _bundle_label_and_id(items: list[dict]) -> tuple[str, str] | None:
    """A 'multiple' option's items are themselves option-shaped. Only
    resolvable if EVERY sub-item is a plain counted_reference — a nested
    'choice' (e.g. "a martial weapon and a shield", where "a martial
    weapon" is its own sub-choice) makes the whole bundle unrepresentable
    in this phase's flat Choice model, so this returns None rather than
    silently dropping the sub-choice's meaning.
    """
    label_parts = []
    id_parts = []
    for sub in items:
        if sub.get("option_type") != "counted_reference":
            return None
        of = sub["of"]
        count = sub.get("count", 1)
        label_parts.append(f"{count}x {of['name']}" if count != 1 else of["name"])
        id_parts.append(of["index"])  # quantities are not part of the id — see plan's Global Constraints
    return " + ".join(label_parts), "+".join(id_parts)
```

Then, inside `build_choice_options`'s `options_array` branch, handle `multiple` before falling through to `_option_label`:

```python
    if set_type == "options_array":
        options = []
        for opt in from_field.get("options", []):
            if opt.get("option_type") == "multiple":
                bundle = _bundle_label_and_id(opt.get("items", []))
                if bundle is None:
                    continue
                label, option_id = bundle
                options.append({"id": option_id, "label": label})
                continue
            label = _option_label(opt)
            if label is None:
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
        return options if options else None
```

(This replaces the existing `options_array` branch's loop body — the `for opt in from_field.get("options", []):` loop — with the version above, which adds the `multiple` case as an early branch inside the same loop and otherwise keeps the existing per-option logic exactly as Phase 1a wrote it.)

- [ ] **Step 8: Run the full choices test suite to verify everything passes**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_choices.py -v`
Expected: all PASS, including every pre-existing Phase 1a test (nothing about `options_array`'s non-`multiple` handling changed).

- [ ] **Step 9: Run the full server suite to confirm no regressions**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all PASS (63 pre-existing + this task's new tests).

- [ ] **Step 10: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/catalog/loader.py server/catalog/choices.py server/tests/test_loader.py server/tests/test_choices.py
git commit -m "$(cat <<'EOF'
feat: add item catalog index + bundle-equipment choice resolution

Catalog.items indexes all 237 bundled equipment entries. choices.py
now resolves option_type "multiple" bundles (e.g. "leather armor, a
longbow, and 20 arrows") into a single pickable Choice option, using
the bundle's item indices joined by "+" as the option id — verified
against the real Fighter SRD data: 3 of Fighter's 4 starting-equipment
envelopes are now resolvable, the 4th (nested martial-weapon sub-
choice) correctly resolves to no options rather than a fake one.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Pure AC-from-equipment math

**Files:**
- Create: `server/engine/equipment.py`
- Create: `server/tests/test_engine_equipment.py`

**Interfaces:**
- Consumes: nothing (pure functions over plain dicts — no catalog/draft access)
- Produces: `equipment.armor_class_from_gear(equipped_items: list[dict], dex_modifier: int) -> int` — Task 3 is the consumer.

- [ ] **Step 1: Write the failing tests**

```python
# server/tests/test_engine_equipment.py
from engine.equipment import armor_class_from_gear

_LEATHER = {"equipment_category": {"index": "armor"}, "armor_category": "Light", "armor_class": {"base": 11, "dex_bonus": True}}
_HIDE = {"equipment_category": {"index": "armor"}, "armor_category": "Medium", "armor_class": {"base": 12, "dex_bonus": True, "max_bonus": 2}}
_CHAIN_MAIL = {"equipment_category": {"index": "armor"}, "armor_category": "Heavy", "armor_class": {"base": 16, "dex_bonus": False}}
_SHIELD = {"equipment_category": {"index": "armor"}, "armor_category": "Shield", "armor_class": {"base": 2, "dex_bonus": False}}


def test_unarmored_is_ten_plus_full_dex():
    assert armor_class_from_gear([], dex_modifier=3) == 13
    assert armor_class_from_gear([], dex_modifier=-1) == 9


def test_light_armor_adds_full_dex_uncapped():
    assert armor_class_from_gear([_LEATHER], dex_modifier=5) == 16  # 11 + 5, no cap


def test_medium_armor_caps_dex_at_max_bonus():
    assert armor_class_from_gear([_HIDE], dex_modifier=5) == 14  # 12 + min(5, 2)
    assert armor_class_from_gear([_HIDE], dex_modifier=1) == 13  # 12 + min(1, 2)


def test_heavy_armor_ignores_dex_entirely():
    assert armor_class_from_gear([_CHAIN_MAIL], dex_modifier=5) == 16
    assert armor_class_from_gear([_CHAIN_MAIL], dex_modifier=-3) == 16


def test_shield_adds_a_flat_bonus_on_top_of_body_armor():
    assert armor_class_from_gear([_LEATHER, _SHIELD], dex_modifier=2) == 15  # 11 + 2 + 2


def test_shield_adds_a_flat_bonus_while_unarmored():
    assert armor_class_from_gear([_SHIELD], dex_modifier=1) == 13  # 10 + 1 + 2


def test_multiple_body_armor_items_use_only_the_first_found():
    # Not a realistic draft, but resolve() must not crash on one — pick
    # deterministically rather than summing nonsensically.
    result = armor_class_from_gear([_LEATHER, _CHAIN_MAIL], dex_modifier=2)
    assert result in (13, 16)  # whichever is "first" per the function's own iteration order — just must not crash or double-stack
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_engine_equipment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine.equipment'`

- [ ] **Step 3: Write `server/engine/equipment.py`**

```python
"""Pure Armor Class math from a list of equipped items. No I/O, no catalog
access — every function here takes plain Equipment.json-shaped dicts and is
independently testable. Mirrors engine/derived.py's style.
"""
from __future__ import annotations


def armor_class_from_gear(equipped_items: list[dict], dex_modifier: int) -> int:
    """equipped_items are raw catalog item dicts (the same shape
    Catalog.items values have) for whatever's actually worn/held —
    resolve() is responsible for gathering that list; this function only
    does the arithmetic.
    """
    body_armor = next(
        (i for i in equipped_items if i.get("equipment_category", {}).get("index") == "armor" and i.get("armor_category") != "Shield"),
        None,
    )
    shield = next((i for i in equipped_items if i.get("armor_category") == "Shield"), None)

    if body_armor:
        ac_data = body_armor["armor_class"]
        base = ac_data["base"]
        if ac_data.get("dex_bonus"):
            max_bonus = ac_data.get("max_bonus")
            dex_contribution = dex_modifier if max_bonus is None else min(dex_modifier, max_bonus)
            base += dex_contribution
    else:
        base = 10 + dex_modifier

    if shield:
        base += shield["armor_class"]["base"]  # a shield's own "base" (2) is a flat bonus, not a base AC

    return base
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_engine_equipment.py -v`
Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/equipment.py server/tests/test_engine_equipment.py
git commit -m "$(cat <<'EOF'
feat: add pure Armor Class math for equipped armor/shields

Handles unarmored (10+DEX), light (base+DEX uncapped), medium
(base+DEX capped at max_bonus), heavy (base only, no DEX), and a
shield's flat +2 stacking on top of any of those — verified against
every armor_category present in the bundled SRD Equipment.json.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Wire equipment into `resolve()`

**Files:**
- Modify: `server/engine/resolve.py`
- Modify: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `Catalog.items` (Task 1), `build_choice_options`/`build_choice_template` (Task 1's extension, unchanged interface), `equipment.armor_class_from_gear` (Task 2)
- Produces: `sheet.equipment.granted`, `sheet.equipment.added`, `choices[]` entries with `source.kind: "equipment"`, and `derived.armorClass` now genuinely reflecting equipped gear — Task 4 (`server/app.py`) and any later frontend work are the consumers.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_resolve.py`:

```python
def test_fighter_equipment_choices_are_offered(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    equipment_choices = [c for c in resolution["choices"] if c["source"]["kind"] == "equipment"]
    labels = {c["label"] for c in equipment_choices}
    # 3 of Fighter's 4 starting_equipment_options entries are resolvable in
    # this phase (see Task 1) — the "martial weapon and a shield or two
    # martial weapons" one is not, and must not appear at all.
    assert len(equipment_choices) == 3
    armor_choice = next(c for c in equipment_choices if any(o["id"] == "chain-mail" for o in c["options"]))
    ids = {o["id"] for o in armor_choice["options"]}
    assert ids == {"chain-mail", "leather-armor+longbow+arrow"}


def test_selecting_chain_mail_computes_heavy_armor_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:prof-choice-0": ["skill-athletics", "skill-history"]},
        }],
        equipment={
            "choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]},
            "added": [], "skipped": False,
        },
    )
    resolution = resolve(draft, catalog)
    # Fighter/Human draft has DEX 14 -> +2 human bonus... reuse the fixture's
    # own DEX (14) + Human's +1 = 15 -> +2 mod; chain mail ignores DEX.
    assert resolution["derived"]["armorClass"] == 16  # chain mail base, no DEX


def test_selecting_leather_bundle_computes_light_armor_ac_with_dex(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={
            "choices": {"class:fighter:1:equipment-choice-0": ["leather-armor+longbow+arrow"]},
            "added": [], "skipped": False,
        },
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 11 + dex_mod


def test_sheet_lists_acolytes_granted_fixed_equipment(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    granted = resolution["sheet"]["equipment"]["granted"]
    granted_ids = {g["itemId"] for g in granted}
    assert "clothes-common" in granted_ids
    assert "pouch" in granted_ids


def test_draft_added_equipped_shield_adds_to_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "shield", "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 10 + dex_mod + 2


def test_draft_added_unequipped_item_does_not_affect_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "shield", "qty": 1, "equipped": False}], "skipped": False},
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 10 + dex_mod
    added = resolution["sheet"]["equipment"]["added"]
    assert any(a["itemId"] == "shield" and a["equipped"] is False for a in added)


def test_unknown_added_item_id_is_dropped_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "not-a-real-item", "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_missing_equipment_field_entirely_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft()
    del draft["equipment"]
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_non_list_added_equipment_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(equipment={"choices": {}, "added": "not-a-list", "skipped": False})
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-equipment-added" for p in resolution["problems"])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_resolve.py -v -k equipment`
Expected: FAIL — no `equipment`-kind choices exist yet, `sheet["equipment"]` key doesn't exist yet, AC is still always unarmored.

- [ ] **Step 3: Add equipment choice templates and gear-gathering to `server/engine/resolve.py`**

Add these imports at the top (alongside the existing ones):

```python
from . import equipment as equipment_mod
```

Add this function near the other `_..._choice_templates` functions:

```python
def _equipment_choice_templates(entity: dict, source_kind: str, source_id: str, source_label: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if tpl:
            templates.append(tpl)
    return templates
```

Add this function to resolve fixed (non-choice) starting equipment into sheet-ready entries:

```python
def _fixed_equipment(entries: list[dict], item_lookup: dict) -> list[dict]:
    result = []
    for entry in entries:
        equipment_ref = entry.get("equipment") or {}
        item_id = equipment_ref.get("index")
        item = item_lookup.get(item_id) if item_id else None
        if not item:
            continue
        result.append({"itemId": item_id, "name": item["name"], "qty": entry.get("quantity", 1)})
    return result
```

Add this function to gather every actually-equipped item (from resolved equipment choices, plus `draft.equipment.added` entries marked equipped):

```python
def _gather_equipped_items(
    equipment_choices: list[dict], added_entries: list[dict], item_lookup: dict,
) -> list[dict]:
    equipped: list[dict] = []
    for choice in equipment_choices:
        for selected_id in choice["selected"]:
            for item_id in selected_id.split("+"):
                item = item_lookup.get(item_id)
                if item:
                    equipped.append(item)
    for entry in added_entries:
        if not isinstance(entry, dict) or not entry.get("equipped"):
            continue
        item = item_lookup.get(entry.get("itemId"))
        if item:
            equipped.append(item)
    return equipped
```

Now wire these into `resolve()` itself. First, add equipment choice templates to the existing `choice_templates` list. Find this exact block:

```python
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
```

and insert the new lines between the species block and the `_apply_background_overlap` call (ordering relative to `_apply_background_overlap` doesn't matter functionally — it only touches `class`-kind templates — but insert it in this exact position so the diff stays easy to read):

```python
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)
    if cls and cls_id:
        choice_templates += _equipment_choice_templates(cls, "class", cls_id, cls["name"])
    if bg and bg_id:
        choice_templates += _equipment_choice_templates(bg, "background", bg_id, bg["name"])

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
```

Next, extend the `all_selections` merge to also read equipment choices. Find the exact existing block (it uses the already-computed local `background_dict`/`species` variables, not fresh `draft.get(...)` calls — match it precisely):

```python
    all_selections: dict[str, list[str]] = {}
    if cls_entry:
        all_selections.update(cls_entry.get("choices") or {})
    all_selections.update(background_dict.get("choices") or {})
    all_selections.update(species.get("choices") or {})
```

and add one more line immediately after it:

```python
    all_selections.update((draft.get("equipment") or {}).get("choices") or {})
```

(Equipment has no pre-existing local dict variable the way `background_dict`/`species` do, since this is the first task to read `draft.get("equipment")` at all — reading it fresh here, defensively, is correct and matches how `cls_entry.get("choices")` is read directly above it.)

Now, after the `choices` list is fully built and before the "Derived stats" section, add equipment gathering and validation. Find this exact junction — the end of the `choices` loop immediately followed by the `# Derived stats.` comment:

```python
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    # Derived stats.
    proficient_skills: set[str] = set()
```

and insert the new block between the `choices.append(...)` line and the `# Derived stats.` comment (leave both of those exact lines exactly where they are — insert only the new code between them):

```python
    equipment_dict = draft.get("equipment") or {}
    added_raw = equipment_dict.get("added")
    if added_raw is None:
        added_raw = []
    elif not isinstance(added_raw, list):
        problems.append({"id": "malformed-equipment-added", "message": "'equipment.added' must be a list."})
        added_raw = []

    added_resolved = []
    for entry in added_raw:
        if not isinstance(entry, dict):
            continue
        item = catalog.items.get(entry.get("itemId"))
        if not item:
            continue
        added_resolved.append({
            "itemId": entry["itemId"], "name": item["name"],
            "qty": entry.get("qty", 1), "equipped": bool(entry.get("equipped", False)),
        })

    equipment_choices = [c for c in choices if c["source"]["kind"] == "equipment"]
    equipped_items = _gather_equipped_items(equipment_choices, added_raw if isinstance(added_raw, list) else [], catalog.items)

    granted_equipment = []
    if cls:
        granted_equipment += _fixed_equipment(cls.get("starting_equipment", []), catalog.items)
    if bg:
        granted_equipment += _fixed_equipment(bg.get("starting_equipment", []), catalog.items)
```

Then update the `derived["armorClass"]` line — find:

```python
        "armorClass": derived_mod.armor_class(modifiers["DEX"]),
```

and replace it with:

```python
        "armorClass": equipment_mod.armor_class_from_gear(equipped_items, modifiers["DEX"]),
```

Finally, add `"equipment"` to the `sheet` dict. Find its exact closing lines:

```python
            "languages": sorted(set(fixed_languages + chosen_languages)),
        },
    }
```

and insert the new key between the `"proficiencies"` block's closing `},` and the `sheet` dict's own closing `}`:

```python
            "languages": sorted(set(fixed_languages + chosen_languages)),
        },
        "equipment": {"granted": granted_equipment, "added": added_resolved},
    }
```

- [ ] **Step 4: Run the equipment-related tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_resolve.py -v -k equipment`
Expected: all PASS.

- [ ] **Step 5: Run the full server suite to confirm no regressions**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all PASS — every Phase 1a test plus every test from Tasks 1-2 of this plan plus this task's new tests, no regressions.

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: wire equipment choices, granted gear, and real AC into resolve()

Class and background starting_equipment_options now produce real
"equipment"-kind Choices wherever the bundled data supports it (see
Task 1's bundle resolution). Fixed (non-choice) starting gear — e.g.
Acolyte's clothes and pouch — lands in sheet.equipment.granted.
draft.equipment.added is validated against the item catalog (unknown
itemIds silently dropped, a non-list value becomes a
malformed-equipment-added problem, never a crash) and surfaced as
sheet.equipment.added. derived.armorClass is now computed from
whatever's actually equipped (kit choices + added-and-equipped items)
instead of always assuming unarmored.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: `GET /api/items` endpoint

**Files:**
- Modify: `server/app.py`
- Modify: `server/tests/test_app.py`

**Interfaces:**
- Consumes: `Catalog.items` (Task 1)
- Produces: `GET /api/items` — a later frontend plan (Phase 2b) is the consumer; nothing in this plan depends on it being consumed.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_app.py`:

```python
def test_items_endpoint_lists_every_bundled_item(client):
    resp = client.get("/api/items")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 237
    chain_mail = next(i for i in body["items"] if i["id"] == "chain-mail")
    assert chain_mail["name"] == "Chain Mail"
    assert chain_mail["category"] == "armor"


def test_items_endpoint_filters_by_category(client):
    resp = client.get("/api/items?category=armor")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 13
    assert all(i["category"] == "armor" for i in body["items"])


def test_items_endpoint_filters_by_search_query(client):
    resp = client.get("/api/items?q=longbow")
    assert resp.status_code == 200
    body = resp.get_json()
    names = [i["name"].lower() for i in body["items"]]
    assert any("longbow" in n for n in names)
    assert all("longbow" in n for n in names)


def test_equipment_choice_appears_in_resolve_response(client):
    resp = client.post("/api/resolve", json={
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    equipment_choices = [c for c in body["choices"] if c["source"]["kind"] == "equipment"]
    assert len(equipment_choices) == 3
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_app.py -v -k items`
Expected: FAIL — `/api/items` doesn't exist yet (404).

- [ ] **Step 3: Add the endpoint to `server/app.py`**

Add this route (placing it near the other `GET /api/catalog*` routes is fine, order doesn't matter to Flask):

```python
@app.route("/api/items")
def api_items():
    category = request.args.get("category")
    query = (request.args.get("q") or "").lower()
    results = []
    for item in _catalog.items.values():
        item_category = item.get("equipment_category", {}).get("index")
        if category and item_category != category:
            continue
        if query and query not in item["name"].lower():
            continue
        results.append({"id": item["index"], "name": item["name"], "category": item_category})
    return jsonify({"items": results})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/test_app.py -v -k items`
Expected: all PASS.

- [ ] **Step 5: Run the full server suite one more time**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/app.py server/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat: add GET /api/items endpoint for the (future) equipment browser

Lists all 237 bundled items with optional category/q filtering. Not
yet consumed by any frontend code — Phase 2b is the eventual consumer,
the same lag Phase 1a's /api/catalog endpoint had before Phase 1b's
pickers landed.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: End-to-end verification

**Files:** none created or modified — this task is pure verification, run by the controller.

**Interfaces:** none — consumes the finished Task 1-4 system as a whole.

- [ ] **Step 1: Run the full backend test suite one more time**

Run: `cd /Users/yoanpetrov/dnd-character-creator/server && .venv/bin/pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 2: Run the v1 test suite to confirm total isolation held**

Run: `cd /Users/yoanpetrov/dnd-character-creator && .venv/bin/pytest tests/ -q`
Expected: 396 passed, 8 skipped (unaffected — this plan touches nothing under `chargen/`, `app.py`, or any other v1 file).

- [ ] **Step 3: Live curl verification of a full equipment round trip**

```bash
cd /Users/yoanpetrov/dnd-character-creator/server
.venv/bin/python3 app.py &
sleep 1

echo "--- items ---"
curl -s "http://127.0.0.1:8000/api/items?category=armor" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['items']))"

echo "--- resolve with chain mail chosen ---"
curl -s -X POST http://127.0.0.1:8000/api/resolve -H "Content-Type: application/json" -d '{
  "name": "Torvin Bracewell",
  "classes": [{"classId": "fighter", "level": 1, "choices": {
    "class:fighter:1:prof-choice-0": ["skill-athletics", "skill-history"],
    "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"]
  }}],
  "background": {"id": "acolyte", "choices": {"background:acolyte:languages": ["draconic", "deep-speech"]}},
  "species": {"id": "human", "choices": {"species:human:languages": ["dwarvish"]}},
  "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
  "equipment": {"choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]}, "added": [], "skipped": false}
}' | python3 -m json.tool | grep -A3 armorClass

kill %1
```

Expected: `/api/items?category=armor` returns 13 items; the resolve call's `armorClass` shows `16` (chain mail's fixed heavy-armor AC, ignoring the character's DEX 14/+2 modifier entirely) — proving the whole equipment-choice-to-AC pipeline works end to end through the real HTTP API, not just in isolated unit tests.

- [ ] **Step 4: Confirm no stray server process is left running**

```bash
ps aux | grep -E "app\.py" | grep -v grep
```

Expected: empty output.
