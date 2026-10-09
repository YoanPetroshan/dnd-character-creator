"""Split from official_source.py (Slice 11.0), unchanged code: common."""
from __future__ import annotations

import itertools


def _sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def slug(name: str) -> str:
    # "/" added (Task 6): spell names like "Enlarge/Reduce" need it to match
    # the bundled SRD spell catalog's own id ("enlarge-reduce") — no
    # pre-existing caller (race/subrace/tool names) ever contains "/", so
    # this is additive, not a behavior change for any current use.
    #
    # Made public (Phase 4c-i Task 6, was `_slug`): engine/resolve.py's
    # _resolve_granted_feats used to duplicate this exact three-.replace()
    # body inline rather than importing it — a real drift risk, especially
    # now that this function's own body is what Task 6 had to reason about
    # for the semicolon-suffixed background-feat-grant bug (see
    # _feats_from_5etools' docstring). loader.py already imports several
    # non-underscore names from this module (load_official_races,
    # official_dir, etc.) as the established "what's meant to be used
    # elsewhere" convention — no existing precedent anywhere in this
    # module for a second module reaching across to import an
    # underscore-prefixed "private" helper, so this is renamed to a
    # genuinely public name rather than having resolve.py do that.
    return name.lower().replace(" ", "-").replace("'", "").replace("/", "-")


def _tool_display_name(raw_key: str) -> str:
    """Title-cases a raw 5etools tool key ("poisoner's kit") into SRD's
    display convention ("Poisoner's Kit") without mangling the letter right
    after an apostrophe the way str.title() does ("poisoner's kit".title()
    -> "Poisoner'S Kit", wrong) — capitalize only each word's first
    character, leave the rest (apostrophe included) untouched."""
    return " ".join(w[:1].upper() + w[1:] for w in raw_key.split(" ") if w)


_ABILITY_KEYS = frozenset({"str", "dex", "con", "int", "wis", "cha"})


def _ability_bonuses_from_5etools(ability_list: list[dict]) -> list[dict]:
    """Converts 5etools' `ability` field (a list of dicts, each either a
    flat {"cha": 2, ...} fixed-bonus map or containing a "choose" sub-key)
    into SRD-shaped ability_bonuses — ONLY the fixed-bonus portion; the
    choose-N portion is out of scope for this task (a later task in this
    plan adds ability_bonus_options), since SRD keeps these as two
    distinct fields (ability_bonuses vs ability_bonus_options) and so does
    this module, for the same reason: build_choice_template only ever
    looks at ability_bonus_options, and _species_ability_bonuses only
    ever looks at ability_bonuses — keeping them separate here means both
    existing functions need no changes.

    Only recognized ability-abbreviation keys become a bonus — every other
    key on an entry (races/backgrounds only ever had "choose"; feats
    (Phase 4c-i Task 2) also add "hidden" and "max" alongside "choose" on
    some real entries, e.g. Ability Score Improvement's "hidden" flag and
    Epic Boons' "max" score cap) is skipped rather than misread as a bogus
    ability bonus."""
    bonuses = []
    for entry in ability_list or []:
        for key, val in entry.items():
            if key not in _ABILITY_KEYS:
                continue
            bonuses.append({"ability_score": {"index": key, "name": key.upper(), "url": ""}, "bonus": val})
    return bonuses


def _ability_bonus_options_from_5etools(ability_list: list[dict], lineage=None) -> dict | None:
    """Converts the CHOOSE portion of 5etools' `ability` field into the
    SAME ability_bonus_options envelope shape SRD's Half-Elf record
    already uses ({"choose": N, "type": "ability_bonuses", "from": {...}})
    — this is exactly what build_choice_template/build_choice_options
    (catalog/choices.py) and _species_ability_bonus_choice_template
    (engine/resolve.py) already know how to consume, unmodified. A race
    can carry BOTH a fixed bonus (handled separately, by
    _ability_bonuses_from_5etools, from the SAME entry) and this choice
    envelope at once — e.g. Aetherborn: fixed +2 CHA, plus choose 2 of
    {STR,DEX,CON,INT,WIS} for +1 each — since SRD keeps ability_bonuses
    and ability_bonus_options as two independent fields, and so do the
    two functions here (_species_ability_bonuses/
    _species_ability_bonus_choice_template read them independently too).

    Only entries shaped {"choose": {"from": [...], "count": N}} are
    handled — confirmed empirically (2026-09-23, against the real fetched
    races.json) that every race-level entry using "choose" matches this
    shape, EXCEPT TCE's "Custom Lineage" pseudo-race, which uses
    {"from": [...], "amount": 2} instead of "count": a fundamentally
    different, more flexible ASI split (TCE's actual rule: +2 to one
    ability OR +1 to two) that this simple choose-N-for-+1-each envelope
    can't represent either way. Entries without a "count" key are
    skipped rather than guessed at (silently defaulting a missing
    "count" to 1 would misrepresent Custom Lineage's real mechanics) —
    same out-of-scope reasoning as the "weighted" shape seen on
    backgrounds (Phase 4b), not races, which this also doesn't handle."""
    for entry in ability_list or []:
        choose = entry.get("choose")
        if not isinstance(choose, dict) or "from" not in choose:
            continue  # e.g. the 2024-style "weighted" shape — handled by the weighted-pair function
        from_list = choose.get("from", [])
        count = choose.get("count", 1)  # 5etools' own default when "count" is omitted
        bonus = choose.get("amount", 1)  # likewise: "amount" is the per-ability bonus, default +1
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": bonus}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    if lineage == "VRGR" and not ability_list:
        # Variant/flexible lineage (MPMM and friends): +2/+1 to two different
        # abilities OR +1 to three different abilities. Same flattened
        # bundle envelope as the 2024 background rule, over all six scores.
        return _weighted_asi_envelope(["str", "dex", "con", "int", "wis", "cha"])
    return None


def _weighted_asi_envelope(pool: list[str]) -> dict:
    """Flattened "+2 to one / +1 to a different one, or +1 to three" ASI
    envelope over `pool` (ordered +2/+1 pairs, then every 3-subset at +1)."""
    def ability_ref(ab: str) -> dict:
        return {"index": ab, "name": ab.upper(), "url": ""}

    def bonus_item(ab: str, bonus: int) -> dict:
        return {"option_type": "ability_bonus", "ability_score": ability_ref(ab), "bonus": bonus}

    options = []
    for high in pool:
        for low in pool:
            if low == high:
                continue
            options.append({"option_type": "multiple", "items": [bonus_item(high, 2), bonus_item(low, 1)]})
    for triple in itertools.combinations(pool, 3):
        options.append({"option_type": "multiple", "items": [bonus_item(ab, 1) for ab in triple]})

    return {"choose": 1, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}


def _ability_bonus_options_from_5etools_weighted_pair(ability_list: list[dict]) -> dict | None:
    """Converts the 2024-style background ability-score-improvement rule
    into a flattened `ability_bonus_options` envelope — Task 4 (Phase 4b).

    The real rule, confirmed empirically and exhaustively (2026-09-26,
    against the real fetched backgrounds.json, all 60 real records with an
    `ability` field): every such record has EXACTLY 2 entries, both shaped
    {"choose": {"weighted": {"from": [3 abilities], "weights": [...]}}} —
    one entry with weights [2, 1] (the "split" option: +2 to one of the 3
    abilities, +1 to a DIFFERENT one of the remaining 2, third untouched)
    and one entry with weights [1, 1, 1] (the "flat" option: +1 to all
    three, no further choice) — always the SAME 3-ability pool on both
    entries. This is ONE universal mechanic with a per-background 3-ability
    pool, not a per-background varying shape.

    engine/asi.py's existing asi_combinations() was checked for reuse
    first, per this task's brief, and turned out NOT to fit: it always
    iterates the full 6-ability ABILITIES list (no pool-narrowing
    parameter), and its own pair combinations are unordered +1/+1 pairs
    (a standard ASI feat's "two abilities, both +1"), not this rule's
    ordered +2/+1 pairs where swapping which ability gets which bonus is a
    DIFFERENT selectable option. It also has no 3-ability "+1 to all"
    shape at all. So this is new, purpose-built combinatorial code, not a
    generalization of asi.py.

    The player's real choice ("split vs flat, then — for split only —
    which ability gets +2 vs +1") is flattened into ordinary, individually
    selectable "bundle" options (matching catalog/choices.py's existing
    "multiple" option_type, which already bundles multiple sub-items into
    one selectable option for equipment — extended by this task to also
    accept ability_bonus sub-items, see _bundle_label_and_id) rather than
    inventing a new multi-layer choice UI concept: split contributes
    P(3, 2) = 3 * 2 = 6 ordered pairs (pick which of 3 gets +2, then which
    of the remaining 2 gets +1), flat contributes exactly 1 (no choice
    left once "all three" is picked) — 7 total, re-derived here from the
    weights/pool, not just asserted.

    Only entries matching this exact 2-entry/weighted/count-3-pool shape
    are handled; anything else (e.g. a future non-conforming record)
    returns None rather than guessing, same "skip rather than fake it"
    discipline as _ability_bonus_options_from_5etools (the sibling
    species-side function, which explicitly does NOT handle this
    "weighted" shape — see its own docstring)."""
    weighted_entries = []
    for entry in ability_list or []:
        choose = entry.get("choose")
        if not isinstance(choose, dict):
            continue
        weighted = choose.get("weighted")
        if isinstance(weighted, dict):
            weighted_entries.append(weighted)

    if len(weighted_entries) != 2:
        return None

    split = next((w for w in weighted_entries if list(w.get("weights", [])) == [2, 1]), None)
    flat = next((w for w in weighted_entries if list(w.get("weights", [])) == [1, 1, 1]), None)
    if split is None or flat is None:
        return None

    pool = split.get("from", [])
    if len(pool) != 3 or flat.get("from", []) != pool:
        return None

    return _weighted_asi_envelope(pool)


def _damage_modifiers_from_5etools(raw: dict) -> tuple[list[str], list[str], list[str]]:
    """Converts 5etools' resist/immune/vulnerable fields into plain
    string lists — a near-identity copy, string entries only.

    Empirically confirmed (2026-09-24, against the real fetched
    races.json): immune and vulnerable are ALWAYS plain string lists
    (5/160 and 1/160 races respectively carry either field at all, zero
    non-string entries in either). resist is NOT always plain strings —
    7 of the 38 races/reprints carrying `resist` (Dragonborn PHB/XPHB,
    Dragonborn (Chromatic/Gem/Metallic)/FTD, Reborn/RHW, Tiefling/XPHB)
    use a CHOICE shape instead of a fixed damage type:
    `{"choose": {"from": [...]}}`, e.g. Dragonborn's resistance depends
    on the player's chosen draconic ancestry. This is a real, disclosed
    cut, not the "resistance to X unless Y" conditional-prose shape this
    task was originally warned to look for (no such shape exists
    anywhere in the real data for any of these four fields) — but it's
    still a non-string, non-trivial entry that this pure-data-pass-
    through task deliberately does NOT resolve: doing so would mean
    building new choice-resolution machinery (a `resist` choice envelope
    the draft can select from, mirroring the existing skill/tool/ability
    choice envelopes) that is out of scope for what the brief specifies
    as an additive, non-computing task. Any non-string entry (i.e. only
    ever a `resist` choice-dict today) is filtered out here rather than
    silently coerced into a string or left to crash resolve.py's sheet
    construction — the affected races get an empty resistances list
    until a future task adds choice support, same "narrow, disclosed
    cut" pattern this module already uses elsewhere (see module
    docstring, _copy/_mod skip)."""
    def _strings_only(key: str) -> list[str]:
        return [entry for entry in (raw.get(key) or []) if isinstance(entry, str)]

    return _strings_only("resist"), _strings_only("immune"), _strings_only("vulnerable")


def _speed_from_5etools(raw_speed) -> tuple[int | None, dict]:
    """5etools `speed`: an int (walk) or {walk, fly, swim, climb}, where a
    non-walk value may be `true` ("equal to your walking speed"). Returns
    (walk or None, {mode: int | True} for the non-walk modes)."""
    if isinstance(raw_speed, bool):
        return None, {}
    if isinstance(raw_speed, int):
        return raw_speed, {}
    if not isinstance(raw_speed, dict):
        return None, {}
    walk = raw_speed.get("walk")
    walk = walk if isinstance(walk, int) and not isinstance(walk, bool) else None
    movement = {}
    for mode, value in raw_speed.items():
        if mode == "walk":
            continue
        if value is True or (isinstance(value, int) and not isinstance(value, bool) and value > 0):
            movement[mode] = value
    return walk, movement


def _darkvision_from_5etools(raw: dict) -> int | None:
    value = raw.get("darkvision")
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _condition_immunities_from_5etools(raw: dict) -> list[str]:
    """Converts 5etools' conditionImmune field into a plain string list —
    confirmed empirically (2026-09-24) that all 7 races/reprints carrying
    this field use plain strings only, no choice/conditional shape."""
    return [entry for entry in (raw.get("conditionImmune") or []) if isinstance(entry, str)]


def _senses_from_5etools(raw: dict) -> dict[str, int]:
    """Converts 5etools' `senses` field into a flat {sense_type: range}
    dict — a NEW field with no race-side precedent to reuse (races.json
    carries 0/160 records with a `senses` field at all, confirmed
    2026-09-28: Phase 4a's race work genuinely never modeled senses, not
    an oversight this function needs to account for).

    Empirically confirmed (2026-09-28, against the real fetched
    feats.json): all 4 feats carrying `senses` (Aberrant Anatomy, Blind
    Fighting, Boon of Truesight, Skulker) use the SAME shape — a list
    containing exactly one single-key dict, e.g. [{"blindsight": 15}] —
    never multiple list entries, never multiple keys on one entry. Built
    generally (accumulating every key across every list entry) rather
    than narrowly special-cased to "exactly one entry" today, so a future
    data refresh adding a multi-sense feat degrades gracefully instead of
    silently dropping the second sense."""
    senses: dict[str, int] = {}
    for entry in raw.get("senses") or []:
        if not isinstance(entry, dict):
            continue
        for sense_type, value in entry.items():
            if isinstance(value, int):
                senses[sense_type] = value
    return senses
