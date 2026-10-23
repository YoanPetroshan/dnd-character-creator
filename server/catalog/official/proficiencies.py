"""Split from official_source.py (Slice 11.0), unchanged code: proficiencies."""
from __future__ import annotations

from catalog.reference_data import SKILL_NAMES, TOOLS
from .common import _tool_display_name, slug


def _pluralize(slug: str) -> str:
    return slug if slug.endswith("s") else f"{slug}s"


# Task 3b's review of resolve.py found that engine/resolve.py's own
# _categorize_proficiency (and its _SPECIFIC_WEAPON_PROFICIENCY_IDS set)
# recognizes "crossbows-light" for the light crossbow, not the naive
# pluralize-and-strip-source result ("light-crossbows") the generic
# _pluralize path below would produce for 5etools' "light crossbow|phb".
# Without this override, that one weapon would silently land in the
# `tools` bucket instead of `weapons` for any sourcebook race granting
# it. This is a small, disclosed, non-exhaustive lookup for the ONE
# concrete mismatch found and verified — further undiscovered id
# mismatches, if any, are the same kind of narrow, disclosed gap this
# project already accepts elsewhere (a mismatched id lands the grant in
# the wrong bucket, visibly, not lost data).
_WEAPON_ID_OVERRIDES = {
    "light-crossbow": "crossbows-light",
    # Phase 4c-i Task 3: feats (never races/backgrounds — confirmed
    # empirically, real feats.json) grant broad weapon CATEGORIES rather
    # than specific named weapons — "martial"/"simple" match
    # 5e-SRD-Classes.json's own top-level proficiency ids verbatim (e.g.
    # Fighter: "simple-weapons", "martial-weapons"); the generic
    # _pluralize path below would otherwise produce "martials"/"simples".
    # "improvised" (Tavern Brawler/XPHB) has no bundled-SRD precedent —
    # no class or race ever grants it — but follows the identical
    # "-weapons" suffix convention, disclosed here rather than guessed at
    # silently.
    "martial": "martial-weapons",
    "simple": "simple-weapons",
    "improvised": "improvised-weapons",
}


def _category_display_name(slug: str) -> str:
    # Matches the BUNDLED SRD data's own sentence-case convention for
    # proficiency-category display names (5e-SRD-Traits.json's
    # dwarven-combat-training trait names its grants "Battleaxes",
    # "Light hammers" — first word capitalized only, not full title case).
    return slug.replace("-", " ").capitalize()


def _proficiencies_from_5etools(race_raw: dict) -> list[dict]:
    """Converts 5etools' skillProficiencies/toolProficiencies/
    weaponProficiencies/armorProficiencies fields — each, per Step 1's
    empirical confirmation against the real fetched races.json
    (2026-09-23), a length-1 list holding one boolean/mixed-value map —
    into SRD's proficiencies: [{index, name, url}] shape. ONLY fixed
    (value is True) grants are converted: choice-shaped envelopes use a
    dict ("choose": {"from": [...]}) or an int ("any": 2,
    "anyArtisansTool": 2, "anyMusicalInstrument": 1) as their value, never
    True, so the `is True` check below excludes them without needing to
    special-case those key names (confirmed empirically: no real entry's
    value is anything other than True, a dict, or an int).

    DISCLOSED, DELIBERATE SIMPLIFICATION (named explicitly by Finding 2 of
    the final whole-branch review, 2026-09-27, for CONSISTENCY with how
    _feats_from_5etools/_language_grants_from_5etools now handle their own
    "multiple entries means alternatives, not simultaneous" cases): this
    function and _proficiency_choices_from_5etools below both index
    `toolProficiencies` (and every other of these four fields) with a bare
    `[0]`, reading only the FIRST outer-list entry. For races and for
    every real background's toolProficiencies except one, that's a
    no-op — the field is always length-1 in real data (Step 1's own
    confirmation above). The one real exception is House Agent/ERLW's
    background, whose toolProficiencies is a 12-entry list, one pair per
    Eberron dragonmarked house (confirmed 2026-09-27) — 5etools' own
    "alternatives, not simultaneous" convention again, exactly like
    Rewarded/Ruined's feats and Clan Crafter's languages, but this ONE
    real case is deliberately NOT resolved the same way those two were:
    which of the 12 pairs actually applies depends on which dragonmarked
    house the player's character belongs to, narrative context this data
    model has no slot for at all (unlike feats/languages, where "grant
    nothing mechanical, disclose the choice" or "keep just the one real
    fixed grant" were both clean, context-free resolutions). So this
    keeps the existing `[0]` behavior (silently correct for every record
    but this one, silently wrong — always resolves to House Cannith's
    pair regardless of the player's actual house — for House Agent) but
    now DISCLOSED here rather than silent, matching this project's
    "disclose rather than silently drop/guess" discipline even where the
    underlying narrow gap isn't itself being fixed.

    Skill ids get the "skill-" prefix + hyphenation
    reference_data.SKILL_ABILITY/SKILL_NAMES already use (e.g.
    "skill-intimidation") — resolve.py's existing trait-proficiency-
    scanning code (engine/resolve.py, Phase 3b-i) filters on exactly this
    prefix.

    Weapon ids carry a "|source" suffix in the raw data (e.g.
    "battleaxe|phb", confirmed against Dwarf/PHB) that's stripped before
    conversion, then PLURALIZED to match the id convention the BUNDLED SRD
    data's own race traits already use for this identical kind of grant
    (chargen/data/srd/5e-SRD-Traits.json's dwarven-combat-training trait:
    "battleaxes"/"handaxes"/"light-hammers"/"warhammers"; elf-weapon-
    training: "longswords"/"shortswords"/"shortbows"/"longbows") —
    catalog.items' own equipment ids are SINGULAR ("battleaxe"), a
    DIFFERENT id namespace (specific purchasable items, not proficiency
    categories), so matching against catalog.items would be the wrong
    target despite the surface resemblance.

    Tool ids need only the same apostrophe/space normalization race/
    subrace names already get via slug() (e.g. "poisoner's kit" ->
    "poisoners-kit", confirmed to match catalog.items' own
    "poisoners-kit" id exactly).

    Armor ids use the bare category word ("light", "medium", "heavy",
    "shield") in the raw data; converted to match the SRD class-
    proficiency convention ("light-armor", ..., "shields") — confirmed
    against every SRD class's own top-level `proficiencies` field
    (5e-SRD-Classes.json).

    FORMERLY a known, disclosed gap (fixed by Task 3b, 2026-09-23):
    engine/resolve.py's trait-proficiency-scanning code used to forward
    only "skill-"-prefixed entries from trait.get("proficiencies", [])
    into proficient_skills — there was no code path that read
    tool-/weapon-/armor- category ids out of RACE or SUBRACE traits into
    sheet.proficiencies.tools/weapons/armor. This was NOT a gap
    introduced by this module — it predated this whole plan and silently
    affected the BUNDLED SRD data too (confirmed: SRD Dwarf's "Dwarven
    Combat Training" trait and Rock Gnome's "Tinker" trait sat unconsumed
    the exact same way). Task 3b extended resolve.py's trait-scanning to
    call the existing `_categorize_proficiency` for every non-skill trait
    proficiency entry, so the tool/weapon/armor entries produced here now
    flow all the way to sheet.proficiencies, verified end-to-end just
    like the skill entries always were."""
    profs: list[dict] = []

    for skill_id, granted in (race_raw.get("skillProficiencies") or [{}])[0].items():
        if granted is True:
            index = f"skill-{slug(skill_id)}"
            name = f"Skill: {SKILL_NAMES.get(index, skill_id.title())}"
            profs.append({"index": index, "name": name, "url": ""})

    for tool_key, granted in (race_raw.get("toolProficiencies") or [{}])[0].items():
        if granted is True and tool_key not in _GENERIC_TOOL_KEYS:  # RPF: not a real tool, a pick (see the envelope)
            index = slug(tool_key)
            profs.append({"index": index, "name": _tool_display_name(tool_key), "url": ""})

    for weapon_key, granted in (race_raw.get("weaponProficiencies") or [{}])[0].items():
        if granted is True:
            weapon_slug = slug(weapon_key.split("|", 1)[0].strip())
            index = _WEAPON_ID_OVERRIDES.get(weapon_slug) or _pluralize(weapon_slug)
            profs.append({"index": index, "name": _category_display_name(index), "url": ""})

    _ARMOR_CATEGORY_SUFFIX = {"light", "medium", "heavy", "all"}
    for armor_key, granted in (race_raw.get("armorProficiencies") or [{}])[0].items():
        if granted is True:
            if armor_key == "shield":
                index = "shields"
            elif armor_key in _ARMOR_CATEGORY_SUFFIX:
                index = f"{armor_key}-armor"
            else:
                # Unrecognized armor category key — best-effort slug rather
                # than silently dropping the grant; not seen in real data
                # (only "light" appears there), so disclosed rather than
                # guessed at further.
                index = slug(armor_key)
            profs.append({"index": index, "name": _category_display_name(index), "url": ""})

    return profs


def _skill_choice_envelope_from_5etools(skill_entry: dict) -> dict | None:
    """Converts the CHOICE portion of a race's skillProficiencies[0] entry
    (never both at once — confirmed empirically, 2026-09-24: no real entry
    mixes a fixed `True` grant with a choice-shape, or mixes two
    choice-shapes together) into a `proficiency_choices`-shaped envelope
    ({"choose": N, "type": "proficiencies", "from": {...}}) — the SAME
    envelope shape the bundled SRD data's own class-level and trait-level
    proficiency_choices already use, so build_choice_template/
    build_choice_options (catalog/choices.py) consume it unmodified.

    Two real shapes, confirmed against races.json (2026-09-24):
    - {"any": N}: a wildcard, not an enumerated list — no real bundled or
      official skill data lists "every skill" out explicitly, so this
      sources catalog/choices.py's NEW "any_skill" option_set_type instead
      of a fixed options list.
    - {"choose": {"from": [...], "count": N}}: an enumerated list of skill
      NAME strings (5etools' plain-English form, e.g. "animal handling",
      NOT an id) — converted to the existing options_array/reference shape
      every other enumerated choice in this codebase already uses. "count"
      is absent for every real single-choice entry (confirmed empirically)
      and defaults to 1 — unlike the ability_bonus_options "amount" shape
      (Task 2), there is no competing meaning for a missing count here."""
    any_n = skill_entry.get("any")
    if isinstance(any_n, int) and not isinstance(any_n, bool):
        return {"choose": any_n, "type": "proficiencies", "from": {"option_set_type": "any_skill"}}

    choose = skill_entry.get("choose")
    if isinstance(choose, dict):
        options = []
        for name in choose.get("from", []):
            index = f"skill-{slug(name)}"
            options.append({
                "option_type": "reference",
                "item": {"index": index, "name": f"Skill: {SKILL_NAMES.get(index, name.title())}", "url": ""},
            })
        return {"choose": choose.get("count", 1), "type": "proficiencies",
                "from": {"option_set_type": "options_array", "options": options}}

    return None


def _tool_choice_envelope_from_5etools(tool_entry: dict) -> dict | None:
    """Same idea as _skill_choice_envelope_from_5etools, for
    toolProficiencies[0]. Tools additionally carry TWO narrowed wildcard
    shapes skills never do — "anyArtisansTool": N and
    "anyMusicalInstrument": N (confirmed empirically, 2026-09-24: these are
    the only three int-valued keys — "any"/"anyArtisansTool"/
    "anyMusicalInstrument" — seen anywhere in the real fetched data; no
    "anyGamingSet" or similar exists) — both resolved via choices.py's
    "any_tool" option_set_type with an added "tool_category" filter key,
    matching reference_data.TOOLS' own `category` field verbatim
    ("Artisan's Tools" / "Musical Instrument") rather than inventing a
    separate option_set_type per narrowed category."""
    any_n = tool_entry.get("any")
    if isinstance(any_n, int) and not isinstance(any_n, bool):
        return {"choose": any_n, "type": "proficiencies", "from": {"option_set_type": "any_tool"}}

    any_artisan = tool_entry.get("anyArtisansTool")
    if isinstance(any_artisan, int) and not isinstance(any_artisan, bool):
        return {"choose": any_artisan, "type": "proficiencies",
                "from": {"option_set_type": "any_tool", "tool_category": "Artisan's Tools"}}

    any_instrument = tool_entry.get("anyMusicalInstrument")
    if isinstance(any_instrument, int) and not isinstance(any_instrument, bool):
        return {"choose": any_instrument, "type": "proficiencies",
                "from": {"option_set_type": "any_tool", "tool_category": "Musical Instrument"}}

    choose = tool_entry.get("choose")
    if isinstance(choose, dict):
        options = [
            {"option_type": "reference", "item": {"index": slug(name), "name": _tool_display_name(name), "url": ""}}
            for name in choose.get("from", [])
        ]
        return {"choose": choose.get("count", 1), "type": "proficiencies",
                "from": {"option_set_type": "options_array", "options": options}}

    return None


# Maps a generic category PLACEHOLDER string, as it appears literally
# inside a background's enumerated `choose.from` list, to the matching
# reference_data.TOOLS `category` value. Confirmed empirically (2026-09-26,
# against the real fetched backgrounds.json) that 9 of the 10 real
# enumerated tool choices mix literal tool names ("thieves' tools",
# "disguise kit") with these generic placeholders — a shape races never
# had (races' own enumerated tool choices are always literal names only,
# per _tool_choice_envelope_from_5etools' docstring). "anyartisanstool"
# (lowercased) is real, confirmed data too (e.g. Prismari Student/SCC,
# Selesnya Initiate/GGR): the SAME string used as a top-level wildcard KEY
# elsewhere is here reused as a from-list VALUE with an identical meaning.
_TOOL_CHOICE_CATEGORY_PLACEHOLDERS = {
    "musical instrument": "Musical Instrument",
    "gaming set": "Gaming Sets",
    "anyartisanstool": "Artisan's Tools",
}


def _background_tool_choice_option_from_5etools(name: str) -> list[dict]:
    """Converts ONE entry of a background tool choice's `choose.from` list
    into one or more options_array 'reference' option dicts. A literal tool
    name (the common case, and the ONLY case races ever had) becomes exactly
    one option, identical to _tool_choice_envelope_from_5etools' own
    'choose' handling. A recognized generic category placeholder (see
    _TOOL_CHOICE_CATEGORY_PLACEHOLDERS) is expanded into EVERY real,
    concrete tool of that category from reference_data.TOOLS instead —
    "choose 1 of {gaming set, musical instrument}" becomes "choose 1 of
    {Dice Set, Playing Card Set, Bagpipes, Drum, ...}" — so the resulting
    envelope is still a plain options_array of real, selectable catalog
    tools, never a fake "Musical Instrument" option that doesn't exist as
    an item. This is the SAME any_tool/tool_category filtering idea
    choices.py's any_tool option_set_type already applies for the wildcard
    case, just pre-expanded here into literal options since this shape is
    an enumerated list, not a wildcard."""
    category = _TOOL_CHOICE_CATEGORY_PLACEHOLDERS.get(name.lower())
    if category is not None:
        return [
            {"option_type": "reference", "item": {"index": t["index"], "name": t["name"], "url": ""}}
            for t in TOOLS if t["category"] == category
        ]
    return [{"option_type": "reference", "item": {"index": slug(name), "name": _tool_display_name(name), "url": ""}}]


# The three real int-valued tool wildcard keys seen anywhere in the real
# fetched background data (2026-09-26) — the same "any"/"anyArtisansTool"/
# "anyMusicalInstrument" trio races have, PLUS "anyGamingSet", a wildcard
# key that appears on 17 real backgrounds (e.g. Noble/PHB, Criminal/PHB,
# Soldier/PHB, Guard/XPHB) and that races NEVER carry (confirmed against
# _tool_choice_envelope_from_5etools' own docstring, which enumerates
# exactly the other three). Resolved via the SAME any_tool option_set_type
# + tool_category filter races' wildcards already use, pointed at
# reference_data.TOOLS' existing "Gaming Sets" category — no changes to
# catalog/choices.py needed.
# RPF: a generic category name stored as a fixed grant (`{"gaming set": true}`, only Carouser/ABH in the data, whose
# text says "Choose one kind of Gaming Set"). It is not a tool: it becomes a one-pick card of that category.
_GENERIC_TOOL_KEYS = {"gaming set": "Gaming Sets"}


_TOOL_WILDCARD_KEY_CATEGORY = {
    "any": None,
    "anyArtisansTool": "Artisan's Tools",
    "anyMusicalInstrument": "Musical Instrument",
    "anyGamingSet": "Gaming Sets",
}


def _background_tool_choice_envelopes_from_5etools(tool_entry: dict) -> list[dict]:
    """Background equivalent of _tool_choice_envelope_from_5etools, EXTENDED
    (not reused unmodified — verified against real data, Step 1, that races'
    version would silently mishandle backgrounds in two ways):

    1. races' version checks each wildcard key in turn and RETURNS on the
       first match, so a background carrying two wildcard keys at once
       would silently lose the second. Confirmed real (2026-09-26): Vizier/
       PSA is {"anyArtisansTool": 1, "anyMusicalInstrument": 1} — both must
       produce their own choice. This version collects every match instead
       of returning early — this list is why starting_proficiency_choices
       is a list, not a single optional envelope.
    2. races' version has no "anyGamingSet" branch at all (see
       _TOOL_WILDCARD_KEY_CATEGORY's docstring above) and its 'choose'
       branch treats every `from` entry as a literal tool name, which would
       invent fake "Musical Instrument"/"Gaming Set" options for 9 of the
       10 real enumerated tool choices (see
       _background_tool_choice_option_from_5etools).

    Empirically confirmed a background entry never mixes a wildcard key
    with 'choose' (checked against every real entry, 2026-09-26), so
    checking wildcards first and falling back to 'choose' only when none
    matched (same ordering races' version uses) cannot drop a choice
    either way."""
    envelopes = []
    for key, category in _GENERIC_TOOL_KEYS.items():
        if tool_entry.get(key) is True:
            envelopes.append({"choose": 1, "type": "proficiencies",
                              "from": {"option_set_type": "any_tool", "tool_category": category}})
    if envelopes:
        return envelopes
    for key, category in _TOOL_WILDCARD_KEY_CATEGORY.items():
        n = tool_entry.get(key)
        if isinstance(n, int) and not isinstance(n, bool):
            from_field = {"option_set_type": "any_tool"}
            if category is not None:
                from_field["tool_category"] = category
            envelopes.append({"choose": n, "type": "proficiencies", "from": from_field})
    if envelopes:
        return envelopes

    choose = tool_entry.get("choose")
    if isinstance(choose, dict):
        options = []
        for name in choose.get("from", []):
            options.extend(_background_tool_choice_option_from_5etools(name))
        return [{"choose": choose.get("count", 1), "type": "proficiencies",
                 "from": {"option_set_type": "options_array", "options": options}}]

    return []


def _proficiency_choices_from_5etools(raw: dict) -> list[dict]:
    """Collects a background's skill/tool proficiency CHOICE envelope(s) —
    as opposed to _proficiencies_from_5etools' fixed grants — into a flat
    list, the shape engine/resolve.py's _background_choice_templates reads
    (one Choice per list entry). At most one skill-choice envelope ever
    exists per background (the skill side needs no background-specific
    handling at all: _skill_choice_envelope_from_5etools, built for races,
    is reused UNMODIFIED — confirmed empirically that background
    skillProficiencies entries use only the same "any"/"choose" shapes
    races already have, no generic placeholder or multi-wildcard
    surprises). The tool side can contribute 0, 1, or 2 envelopes (2 only
    for Vizier/PSA's simultaneous double-wildcard, confirmed real) via
    _background_tool_choice_envelopes_from_5etools above, which IS
    background-specific — see that function's own docstring for why races'
    version can't be reused as-is here.

    Reads only entry `[0]` of `toolProficiencies` too, the SAME disclosed,
    deliberate simplification _proficiencies_from_5etools' own docstring
    explains in full (House Agent/ERLW's 12 narrative-context-dependent
    dragonmarked-house alternatives) — not repeated here."""
    skill_entry = (raw.get("skillProficiencies") or [{}])[0]
    tool_entry = (raw.get("toolProficiencies") or [{}])[0]

    choices: list[dict] = []
    skill_envelope = _skill_choice_envelope_from_5etools(skill_entry)
    if skill_envelope is not None:
        choices.append(skill_envelope)
    choices.extend(_background_tool_choice_envelopes_from_5etools(tool_entry))
    return choices


def _attach_choice_proficiencies(race_raw: dict, trait_refs: list[dict], id_prefix: str,
                                  race_ref: list[dict], subrace_ref: list[dict],
                                  traits_by_index: dict[str, dict]) -> None:
    """Attaches this race/subrace's skill/tool proficiency CHOICE(s) (as
    opposed to _attach_fixed_proficiencies' fixed grants) onto dedicated
    synthetic traits — one per choice, mutating trait_refs/traits_by_index
    in place, mirroring _attach_fixed_proficiencies' own signature and
    calling convention.

    Unlike _attach_fixed_proficiencies, this does NOT try to attach onto an
    existing named trait whose prose describes the grant: the bundled SRD
    data's own trait-level `proficiency_choices` field is a single dict per
    trait (confirmed against 5e-SRD-Traits.json's tool-proficiency/
    skill-versatility traits — unlike the class-level shape, which is a
    LIST of envelopes), and a real race can have BOTH a skill choice AND a
    tool choice described by the SAME prose entry (e.g. Warforged/EFA's
    "Specialized Design": "You gain one skill proficiency and one tool
    proficiency of your choice.") — reusing the fixed-grant heuristic here
    would make both choices collide on one trait and silently overwrite
    each other. At most one skill-choice and one tool-choice envelope ever
    exist per race (confirmed empirically), so two deterministically-named
    dedicated traits ("Skill Proficiency" / "Tool Proficiency") are always
    enough — no need to enumerate/number them."""
    skill_entry = (race_raw.get("skillProficiencies") or [{}])[0]
    tool_entry = (race_raw.get("toolProficiencies") or [{}])[0]

    for label, envelope in (
        ("Skill Proficiency", _skill_choice_envelope_from_5etools(skill_entry)),
        ("Tool Proficiency", _tool_choice_envelope_from_5etools(tool_entry)),
    ):
        if envelope is None:
            continue
        trait_id = f"{id_prefix}-trait-choice-{slug(label)}"
        traits_by_index[trait_id] = {
            "index": trait_id, "races": race_ref, "subraces": subrace_ref,
            "name": label, "desc": [], "proficiencies": [],
            "proficiency_choices": envelope, "url": "",
        }
        trait_refs.append({"index": trait_id, "name": label, "url": ""})


def _attach_fixed_proficiencies(profs: list[dict], trait_refs: list[dict], id_prefix: str,
                                 race_ref: list[dict], subrace_ref: list[dict],
                                 traits_by_index: dict[str, dict]) -> None:
    """Attaches this race/subrace's fixed proficiency grants onto ONE of
    its already-minted synthetic traits (mutates trait_refs/traits_by_index
    in place) — preferring whichever trait's own prose text actually names
    the grant (e.g. Aetherborn's "Menacing" trait text is literally "You
    have proficiency in the {@skill Intimidation} skill.", matching the
    SRD's own identically-named "menacing" trait exactly), so the grant
    shows up next to its real in-fiction description rather than an
    arbitrary trait like "Age". Falls back to the first synthetic trait,
    then (only if the race has no named entries at all) mints a dedicated
    "Automatic Proficiencies" trait so the grant is never silently
    dropped. Empirically confirmed (2026-09-23) that every one of the 66
    real races/subraces carrying any of the four proficiency fields has at
    least one named entries item whose text contains "proficien" — so the
    dedicated-trait fallback is defensive, not exercised by real data
    today."""
    if not profs:
        return

    target_id = None
    for ref in trait_refs:
        desc_text = " ".join(traits_by_index[ref["index"]].get("desc", []))
        if "proficien" in desc_text.lower():
            target_id = ref["index"]
            break
    if target_id is None and trait_refs:
        target_id = trait_refs[0]["index"]
    if target_id is None:
        target_id = f"{id_prefix}-trait-auto-profs"
        traits_by_index[target_id] = {
            "index": target_id, "races": race_ref, "subraces": subrace_ref,
            "name": "Automatic Proficiencies", "desc": [], "proficiencies": [], "url": "",
        }
        trait_refs.append({"index": target_id, "name": "Automatic Proficiencies", "url": ""})

    traits_by_index[target_id]["proficiencies"].extend(profs)
