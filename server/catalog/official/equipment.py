"""Split from official_source.py (Slice 11.0), unchanged code: equipment."""
from __future__ import annotations

import json
import re
from .common import _sentence_case, _tool_display_name, slug
from .paths import _repo_root


# Task 5 (starting equipment package choice): loaded directly from the
# bundled SRD file itself, the SAME data catalog/loader.py's Catalog.items
# is built from (chargen/data/srd/5e-SRD-Equipment.json) — NOT re-derived
# via a Catalog instance, since load_official_backgrounds() runs before
# catalog/loader.py builds one (see loader.py's load(): official
# backgrounds are converted before `items` is indexed) and this module
# already has its own direct-file-read precedent for exactly this reason
# (LANGUAGES above is a hand-maintained table for the same structural
# reason: the resource this module needs isn't available as a Catalog
# object yet at conversion time). Matched against 5etools item names via
# _find_srd_equipment_item's word-set comparison, not a naive slug — see
# that function's own docstring for why a naive slug (the convention
# Phase 4a's weapon-id work used for PROFICIENCY CATEGORY ids, a
# different, unrelated id namespace) does not work for specific equipment
# ITEM ids.
with open(_repo_root / "chargen" / "data" / "srd" / "5e-SRD-Equipment.json", encoding="utf-8") as _f:
    _SRD_EQUIPMENT = json.load(_f)


def _equipment_name_words(name: str) -> frozenset[str]:
    """Normalizes an equipment name into a bag-of-words for matching,
    stripping parenthetical qualifiers (SRD's "Ink (1 ounce bottle)" vs
    5etools' bare "ink") and punctuation (commas, apostrophes — SRD names
    equipment "Clothes, traveler's" while 5etools calls the same item
    "traveler's clothes"; word ORDER differs too, which is exactly why
    this compares as a set/frozenset, not a normalized string)."""
    name = re.sub(r"\(.*?\)", " ", name.lower())
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return frozenset(w for w in name.split() if w)


_SRD_EQUIPMENT_WORDS = [(_equipment_name_words(item["name"]), item) for item in _SRD_EQUIPMENT]
_SRD_EQUIPMENT_BY_WORDS = {words: item for words, item in _SRD_EQUIPMENT_WORDS}  # exact-match fast path


def _find_srd_equipment_item(name: str) -> dict | None:
    """Looks up a 5etools equipment item name against the bundled SRD
    237-item equipment list. Two passes: an exact word-set match first
    (covers most items, e.g. "dagger" -> "Dagger", "disguise kit" ->
    "Disguise Kit"), then a SUBSET pass (this item's words all appear
    somewhere in the SRD entry's words) for the real cases an exact match
    misses — a bare 5etools name that's short for a longer SRD one
    ("costume" -> "Clothes, costume", "ink" -> "Ink (1 ounce bottle)").
    Ties (5etools' bare "rope" is a word-subset of BOTH "Rope, hempen (50
    feet)" and "Rope, silk (50 feet)" — the only real ambiguity found,
    Task 5 grounding) are broken by taking the FIRST match in the
    bundled file's own order, which happens to be the cheaper/more
    standard "hempen" option here — a narrow, disclosed tie-break, not a
    generically correct disambiguation rule.

    Returns None for names with no catalog equivalent at all — confirmed
    against the real data (Task 5 grounding, 2026-09-26): 8 of 91 real
    distinct item names are generic category placeholders the 237-item
    SRD equipment list was never meant to cover ("arcane focus",
    "gaming set", "holy symbol", "musical instrument") or items simply
    outside the bundled SRD subset ("arrows (20)", "bolts (20)", "iron
    spikes", "robe") — callers synthesize a non-catalog reference for
    these rather than dropping them; see
    _equipment_bundle_member_from_5etools's docstring for the full,
    disclosed consumption-path consequence of doing so."""
    words = _equipment_name_words(name)
    if not words:
        return None
    exact = _SRD_EQUIPMENT_BY_WORDS.get(words)
    if exact is not None:
        return exact
    for item_words, item in _SRD_EQUIPMENT_WORDS:
        if words <= item_words:
            return item
    return None


# 5etools' three "pick a category, not a specific item" equipmentType
# tokens seen in real startingEquipment bundles (Task 5 grounding,
# 2026-09-26: setGaming x8, toolArtisan x6, instrumentMusical x6, across
# all 135 real backgrounds — exhaustive, not a guess). Each is a nested
# sub-choice smuggled inside what's otherwise a flat equipment bundle
# (e.g. "a gaming set of your choice") — see
# _equipment_bundle_member_from_5etools's docstring for why this is
# represented as a synthetic, non-catalog reference rather than expanded
# into its own nested choice (which catalog/choices.py's "multiple"
# bundle mechanism has no way to represent at all — a bundle containing
# its own sub-choice is exactly the "unrepresentable in this phase's flat
# Choice model" case that module's own docstring already describes).
_EQUIPMENT_TYPE_LABELS = {
    "toolArtisan": "Artisan's Tools",
    "setGaming": "Gaming Set",
    "instrumentMusical": "Musical Instrument",
}


def _counted_reference_for_item_name(name: str, count: int = 1, display_label: str | None = None) -> dict:
    """Builds one options_array 'counted_reference' sub-item for an
    equipment bundle member that's (or names) a specific item, resolving
    against the bundled SRD equipment list when possible so the id
    matches a REAL catalog.items entry (so the granted item correctly
    reaches the sheet once selected — see engine/resolve.py's
    _gather_equipped_items/_chosen_equipment, both UNCHANGED by this
    task). Falls back to a synthetic, non-catalog id/name for the ~9% of
    real item names with no SRD equivalent (Task 5 grounding) — flagged
    via this synthetic "unlisted-" id prefix rather than silently
    dropping the member, matching this module's established fallback
    discipline (e.g. _language_choice_option_from_5etools' own
    unrecognized-name branch)."""
    match = _find_srd_equipment_item(name)
    if match is not None:
        return {"option_type": "counted_reference", "count": count,
                "of": {"index": match["index"], "name": display_label or match["name"]}}
    return {"option_type": "counted_reference", "count": count,
            "of": {"index": f"unlisted-{slug(name)}", "name": display_label or _tool_display_name(name)}}


def _equipment_bundle_member_from_5etools(item) -> dict:
    """Converts ONE member of an equipment package bundle (one entry of a
    background's startingEquipment `a`/`b`/... list) into an
    options_array 'counted_reference' sub-item — catalog/choices.py's
    _bundle_label_and_id requires EVERY member of a "multiple" bundle to
    be uniformly one option_type (counted_reference or ability_bonus, see
    that function's own docstring), so every real member shape found
    (Task 5 grounding, 2026-09-26, exhaustive over all 135 real
    backgrounds' a/b/c/d-keyed bundles: plain item-name strings, {item},
    {item, displayName}, {item, quantity}, {displayName, item, quantity},
    {special}, {special, quantity}, {value} gold, {equipmentType},
    {displayName, equipmentType}) is normalized to this ONE shape here,
    never represented as its own distinct option_type.

    Three of these ten shapes ({value} gold, {special} flavor-only gear
    with no catalog equivalent, {equipmentType} category placeholders
    like "an artisan's tool of your choice") synthesize a NON-CATALOG
    "of" reference — a stable id that deliberately does not match
    anything in catalog.items. This is a disclosed, known consumption-
    path gap, not fixed inline here (this plan's established
    disclose-and-defer rule, Task 1->1b/Task 2->2b precedent): the CHOICE
    OFFERED to the player is fully accurate (correct label/flavor text
    for every member), but engine/resolve.py's existing, UNCHANGED
    _gather_equipped_items/_chosen_equipment (which build the final
    sheet's granted-equipment list from a SELECTED choice) look every
    compound id's "+"-separated parts up against catalog.items and
    silently skip whichever parts don't resolve — so selecting a bundle
    containing one of these three shapes correctly shows/offers the full
    bundle but silently drops JUST that one synthetic member (never the
    whole bundle) from the final sheet. Two separate root causes, both
    genuinely pre-existing and outside this task's own files: (1) this
    engine has NO currency/gold field anywhere at all (confirmed by
    grep, Task 5 investigation — not even SRD's own bundled Acolyte's
    starting_gold, {"quantity": 15, "unit": "gp"}, is ever read by
    resolve.py), so a gold amount has nowhere real to go; (2) there is no
    mechanism anywhere in this codebase for official_source.py to
    register a NEW item into catalog.items (unlike languages, which
    reference_data.py hand-maintains as open SRD content — equipment
    items are the bundled SRD file's own closed 237-item list). See the
    Task 5 report for the full disclosure."""
    if isinstance(item, str):
        name = item.split("|", 1)[0].strip()
        return _counted_reference_for_item_name(name)

    if "value" in item or "containsValue" in item:
        # Confirmed copper pieces, Task 5 grounding, corrected 2026-09-27:
        # every real "value" INSIDE an a/b/c/d choice bundle (27 distinct
        # values, 100-5000) is exactly divisible by 100 — but this is NOT
        # true of every "containsValue"/"value" across the whole dataset:
        # two "_"-keyed fixed entries (Haunted One/VRGR, Investigator/VRGR)
        # carry a real "value": 10 (1 silver piece), only reachable once
        # Finding 1 of the final whole-branch review wired the "_" list
        # into this function at all. Floor division below intentionally
        # rounds a sub-100cp amount down to "gp-0" — the caller
        # (_fixed_starting_equipment_from_5etools) is responsible for NOT
        # treating a "gp-0" id as "0 gp granted" (that would be the exact
        # "fabricated zero is worse than absent" problem Finding 1 itself
        # exists to fix, just for a different amount) — sub-gp coinage
        # simply isn't tracked by this app, a disclosed, narrow gap.
        #
        # SRD's own bundled Acolyte pouch (containsValue 1500 in the raw
        # 5etools data) matches SRD's own starting_gold of 15 gp exactly
        # at a 100:1 ratio, confirming the conversion ratio itself.
        # "containsValue" (always on a container, `{"item": "pouch|phb",
        # "containsValue": N}` or `{"special": "purse", "containsValue":
        # N}`) appears ONLY inside "_"-keyed fixed lists, never inside an
        # a/b/c/d choice bundle, where the bare `{"value": N}` shape is
        # the only one seen — so merging both into this one branch is
        # additive, not a behavior change for any existing a/b/c/d choice
        # this function already handles. The container's own name
        # (pouch/purse) is discarded exactly like a bare gold value's
        # non-existent container would be — it's flavor for "here is
        # where your money is", not a trackable inventory item in its
        # own right.
        cp = item["value"] if "value" in item else item["containsValue"]
        gp = cp // 100
        return {"option_type": "counted_reference", "count": 1,
                "of": {"index": f"gp-{gp}", "name": f"{gp} GP"}}

    if "equipmentType" in item:
        label = item.get("displayName") or _EQUIPMENT_TYPE_LABELS.get(item["equipmentType"], item["equipmentType"])
        return {"option_type": "counted_reference", "count": 1,
                "of": {"index": f"category-{slug(label)}", "name": label}}

    if "special" in item:
        label = item.get("displayName") or _sentence_case(item["special"])
        return {"option_type": "counted_reference", "count": item.get("quantity", 1),
                "of": {"index": f"flavor-{slug(label)}", "name": label}}

    # {"item": "name|source"}, optionally with "displayName" and/or "quantity".
    name = item["item"].split("|", 1)[0].strip()
    return _counted_reference_for_item_name(name, count=item.get("quantity", 1), display_label=item.get("displayName"))


def _starting_equipment_options_from_5etools(raw: dict) -> list[dict]:
    """Converts a background's `startingEquipment` field into SRD-shaped
    `starting_equipment_options` envelopes (one per independent A/B-style
    choice) — `resolve.py`'s existing, UNCHANGED `_equipment_choice_
    templates` reads this field the exact same way for every background
    (confirmed by re-reading it fresh, Task 5 investigation: it iterates
    `starting_equipment_options` by index and calls the generic
    `build_choice_template`, no background-specific branch at all), and
    `catalog/choices.py`'s existing, UNCHANGED "multiple" option-bundling
    mechanism (`build_choice_options`/`_bundle_label_and_id`) already
    resolves an options_array of "multiple" bundles once every bundle
    member is uniformly counted_reference — which
    _equipment_bundle_member_from_5etools guarantees for every real shape
    found (see that function's own docstring). Zero resolve.py/choices.py
    changes needed for the CHOICE ITSELF to be offered and rendered
    correctly — see this function's own docstring above for the separate,
    disclosed gap in what happens AFTER a bundle containing a synthetic
    member is selected.

    `startingEquipment` is a LIST of entries (Task 5 grounding corrects
    the plan's own "exactly one entry" assumption, 2026-09-26): 75/135
    real backgrounds carry ONLY a `"_"`-keyed entry (fixed equipment, no
    package choice at all — e.g. Anthropologist/ToA) and produce NO
    envelope here at all (that background's `starting_equipment_options`
    stays an empty list; its FIXED equipment, and every background's
    `starting_gold`, remain separate, still-unpopulated placeholders —
    disclosed, out of this task's own stated scope, see the Task 5
    report). A record can also carry MORE THAN ONE independent a/b-keyed
    entry (Athlete/MOT: pick a discus-or-ball, AND separately pick a
    charm-or-trophy) — each a/b-keyed entry in the list produces its OWN
    envelope, never flattened together into one bigger choice (that would
    misrepresent two independent 2-option choices as one 4-option
    choice). Key casing varies too: lowercase `a`/`b` (most records) or
    uppercase `A`/`B` (2024-era XPHB-sourced records) — handled
    case-insensitively; one record (Charlatan/PHB) has FOUR options
    (`a`/`b`/`c`/`d`), handled generically rather than hardcoding 2."""
    envelopes = []
    for entry in raw.get("startingEquipment") or []:
        bundle_keys = [k for k in entry if k.lower() in ("a", "b", "c", "d")]
        if not bundle_keys:
            continue
        bundle_keys.sort(key=str.lower)
        options = [
            {"option_type": "multiple", "items": [_equipment_bundle_member_from_5etools(i) for i in entry[key]]}
            for key in bundle_keys
        ]
        envelopes.append({
            "choose": 1, "type": "equipment",
            "from": {"option_set_type": "options_array", "options": options},
        })
    return envelopes


def _fixed_starting_equipment_from_5etools(raw: dict) -> tuple[list[dict], dict | None, list[str]]:
    """Converts a background's FIXED, always-granted startingEquipment
    members — every `"_"`-keyed entry (5etools' convention for "granted
    regardless of the A/B/C/D package choice", as opposed to
    _starting_equipment_options_from_5etools' CHOICE-shaped a/b/c/d
    entries) — into SRD's own starting_equipment/starting_gold shape.
    Fixes Finding 1 of the final whole-branch review (2026-09-27):
    `_background_from_5etools` used to hardcode `starting_equipment: []`/
    `starting_gold: None` regardless of the real data, silently zeroing
    out equipment AND gold for the 74/135 real backgrounds that carry a
    `"_"` entry (58 with ONLY a `"_"` entry, no a/b choice at all; 16 more
    with BOTH a choice AND a `"_"` entry, whose fixed part was lost) —
    most visibly, `sheet.startingGold` actively reporting a wrong `0`
    where before this whole plan the field simply didn't exist.

    `startingEquipment` can carry MORE THAN ONE `"_"`-keyed entry —
    confirmed real, 2026-09-27: Prismari Student/SCC has one `"_"` entry
    BEFORE its artisan's-tools-or-instrument a/b choice (ink + ink pen)
    and a SECOND `"_"` entry AFTER it (school uniform + a 10gp pouch).
    Every `"_"`-keyed entry's members are collected, not just the first,
    matching the "don't silently drop a second occurrence" discipline
    _starting_equipment_options_from_5etools already applies to a/b/c/d
    entries.

    Each member is converted through the SAME
    _equipment_bundle_member_from_5etools every a/b/c/d CHOICE bundle
    member already goes through (Task 5, extended by this fix to also
    recognize the `"containsValue"` gold shape — see that function's own
    updated docstring), so a real catalog item, a gold value, a category
    placeholder, and flavor-only gear are all recognized identically
    whether they're offered as a choice or granted outright.

    The resulting per-member triage mirrors engine/resolve.py's OWN
    _selected_gold_and_narrative_items exactly, by synthetic-id prefix:
    "gp-*" sums into `starting_gold`; ("flavor-", "category-",
    "unlisted-")-prefixed members become narrative text (an UNLISTED/
    no-catalog-match real item — e.g. Acolyte/PHB's "holy symbol", one of
    the ~9% of real item names with no SRD equivalent, Task 5 grounding —
    is treated the SAME as a flavor/category placeholder here: it has no
    catalog entry to land on, so showing its label as narrative text is
    the only way it doesn't silently vanish, exactly the outcome
    _selected_gold_and_narrative_items already gives an unlisted CHOSEN
    member); everything else is a genuine catalog match, converted to
    SRD's own `starting_equipment` shape (`[{"equipment": {index, name},
    "quantity": N}, ...]`) that engine/resolve.py's existing, UNCHANGED
    `_fixed_equipment` already consumes (confirmed by reading it first:
    it looks up `entry["equipment"]["index"]` against `catalog.items` and
    reads `entry["quantity"]` — exactly what's produced here; already
    wired at this function's call site in resolve(), `granted_equipment
    += _fixed_equipment(bg.get("starting_equipment", []), ...)`, so no
    resolve.py change is needed for the equipment/gold half of this fix —
    only the narrative-item half needs new resolve.py wiring, since
    narrativeItems was previously built ONLY from selected equipment-
    choice members).

    `starting_gold` is only ever a populated `{"quantity": N, "unit":
    "gp"}` dict when at least one gold-shaped member was actually seen —
    a background whose `"_"` list carries no gold at all (not observed in
    real data, but not assumed away either) stays `None`, the same
    "no data means no data, not a fabricated zero" distinction SRD's own
    bundled field already draws."""
    members: list = []
    for entry in raw.get("startingEquipment") or []:
        underscore = entry.get("_")
        if isinstance(underscore, list):
            members.extend(underscore)

    starting_equipment: list[dict] = []
    narrative_items: list[str] = []
    gold_total = 0
    saw_gold = False

    for member in members:
        bundle_item = _equipment_bundle_member_from_5etools(member)
        of_ref = bundle_item["of"]
        item_id = of_ref["index"]
        if item_id.startswith("gp-"):
            amount = item_id[len("gp-"):]
            # A sub-1-gp amount (e.g. 10cp = 1sp) floors to "gp-0" in
            # _equipment_bundle_member_from_5etools, which has no
            # sub-gp unit to represent it in. Confirmed real, 2026-09-27:
            # Haunted One/VRGR and Investigator/VRGR both end their fixed
            # gear with "...and 1 sp". Setting saw_gold here regardless
            # would reintroduce the exact "wrong explicit 0 is worse than
            # absent" problem this whole function exists to fix — so a
            # gp-0 member is treated as "no gp-trackable amount", not "0
            # gp", leaving starting_gold None rather than a fabricated
            # zero. The amount itself is simply not tracked below 1 gp; a
            # disclosed, narrow gap, not a silent wrong answer.
            if amount.isdigit() and int(amount) > 0:
                saw_gold = True
                gold_total += int(amount)
        elif item_id.startswith(("flavor-", "category-", "unlisted-")):
            narrative_items.append(of_ref["name"])
        else:
            starting_equipment.append({
                "equipment": {"index": item_id, "name": of_ref["name"]},
                "quantity": bundle_item.get("count", 1),
            })

    starting_gold = {"quantity": gold_total, "unit": "gp"} if saw_gold else None
    return starting_equipment, starting_gold, narrative_items
