"""Converts the wider, multi-sourcebook 5etools-src race/subrace/background
data (fetched by `python3 -m chargen.sync --official` into
chargen.sources.official_dir(), never committed to this repo — see that
module and chargen/sync.py for the fetch/licensing details this module
inherits without re-litigating) into the SAME dict shape
catalog/loader.py already produces for the bundled 2014 SRD data. This is
a from-scratch v2-native normalizer — it does NOT reuse chargen.catalog's
own normalizer (chargen.normalise.race_from_5etools etc.), because that
targets chargen's own frozen dataclasses, a different, incompatible
object model from the raw dicts catalog/choices.py and engine/resolve.py
read throughout. Only chargen.sources' pure path/existence helpers are
shared.

Every record's id is source-qualified (e.g. "aasimar-vgm") using the raw
5etools "source" field lowercased, so a reprint across multiple books
(Aasimar in VGM, then MPMM, then XPHB) produces multiple distinct
records, and nothing here can ever collide with a bundled SRD id (SRD ids
have no source suffix at all).

Subrace ids are additionally scoped by their parent race's own id (e.g.
"aasimar-vgm-fallen-vgm"), not just their own (name, source) — empirically
confirmed against the real fetched data that (name, source) alone is NOT
globally unique for subraces: "Ixalan"/PSX names a subrace of both
Goblin/PSZ and Vampire/PSZ, and "Variant; Mark of Finding"/ERLW names a
subrace of both Half-Orc/PHB and Human/PHB. Scoping by parent race id
resolves both collisions.

_copy/_mod-based records (5etools' own "defined as another record plus a
diff" shorthand) are skipped — real, but a bounded, disclosed cut, same
scope decision v1's own chargen/normalise.py already made for the same
reason (see that module's docstring). Subrace records with no "name"
field are also skipped: empirically these are "SRD-complete" placeholder
markers (e.g. for Human/Half-Elf/Half-Orc/Tiefling/Dragonborn in the PHB)
that carry no selectable content of their own, not real subraces.

chargen lives at the repo root, a SIBLING of server/ — not a subpackage
of it. Every real way this server runs (`cd server && python app.py` in
production, `cd server && pytest` for tests) has `server/` as the
working directory, which does not put the repo root on sys.path. The
insert below is what makes `from chargen.sources import ...` resolve —
this module is the ONLY place in the whole codebase that imports
chargen.sources directly; official_dir/has_official are re-exported
from here (see the import line right below) so every caller (loader.py,
every test) imports them FROM catalog.official_source instead, and
never needs to know chargen lives one level up at all.

Innate spellcasting (Task 6, 2026-09-24): `additionalSpells[].innate`
converts to each race/subrace's new `innate_spells` field — see
_innate_spells_from_5etools' docstring for the full shape/scope
grounding. Resolvability measurement (2026-09-24, re-measured after a
code review caught two bugs in the first pass: a "rest"-wrapper entry
was being silently dropped instead of counted, and the original count
included races/subraces filtered out by the "_copy" check below and so
never actually reached this code): running the REAL shipped pipeline —
load_official_races() followed by resolving each returned innate-spell
reference against catalog.spells, exactly what
engine.resolve._species_innate_spells does — over the real fetched
races.json produces 102 total innate-spell references (races AND
subraces, since subraces carry the field independently too), of which
93/102 (91.2%) resolve cleanly against the bundled 2014 SRD spell
catalog once 5etools' own nested "{level: {"daily"|"rest": {"1":
[...]}}}" shape and "name|source"/"name#N" decorations are correctly
stripped before slugging — most sourcebook races' innate spells
genuinely are 2014-era SRD spells. The remaining 9/102 (8.8%) reference
spells this project has no data for at all (Hex, Tenser's Floating Disk,
Ice Knife, Wall of Water, Crown of Madness, Ray of Sickness x2, Armor of
Agathys, Searing Smite) — a real, disclosed gap (this project has not
imported spell DATA beyond the bundled SRD list, an explicitly
out-of-scope decision predating this task), handled by
engine.resolve._species_innate_spells degrading gracefully: spellId is
null but the spell's name is still shown, never silently dropped.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

_repo_root = Path(__file__).resolve().parents[2]  # server/catalog/official_source.py -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402  (must follow the sys.path fix above)
from catalog.reference_data import SKILL_NAMES, TOOLS, LANGUAGES  # noqa: E402  (same reason)

_LANGUAGES_BY_INDEX = {lang["index"]: lang for lang in LANGUAGES}


def _slug(name: str) -> str:
    # "/" added (Task 6): spell names like "Enlarge/Reduce" need it to match
    # the bundled SRD spell catalog's own id ("enlarge-reduce") — no
    # pre-existing caller (race/subrace/tool names) ever contains "/", so
    # this is additive, not a behavior change for any current use.
    return name.lower().replace(" ", "-").replace("'", "").replace("/", "-")


def _tool_display_name(raw_key: str) -> str:
    """Title-cases a raw 5etools tool key ("poisoner's kit") into SRD's
    display convention ("Poisoner's Kit") without mangling the letter right
    after an apostrophe the way str.title() does ("poisoner's kit".title()
    -> "Poisoner'S Kit", wrong) — capitalize only each word's first
    character, leave the rest (apostrophe included) untouched."""
    return " ".join(w[:1].upper() + w[1:] for w in raw_key.split(" ") if w)


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
    subrace names already get via _slug (e.g. "poisoner's kit" ->
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
            index = f"skill-{_slug(skill_id)}"
            name = f"Skill: {SKILL_NAMES.get(index, skill_id.title())}"
            profs.append({"index": index, "name": name, "url": ""})

    for tool_key, granted in (race_raw.get("toolProficiencies") or [{}])[0].items():
        if granted is True:
            index = _slug(tool_key)
            profs.append({"index": index, "name": _tool_display_name(tool_key), "url": ""})

    for weapon_key, granted in (race_raw.get("weaponProficiencies") or [{}])[0].items():
        if granted is True:
            weapon_slug = _slug(weapon_key.split("|", 1)[0].strip())
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
                index = _slug(armor_key)
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
            index = f"skill-{_slug(name)}"
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
            {"option_type": "reference", "item": {"index": _slug(name), "name": _tool_display_name(name), "url": ""}}
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
    return [{"option_type": "reference", "item": {"index": _slug(name), "name": _tool_display_name(name), "url": ""}}]


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
    version can't be reused as-is here."""
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
        trait_id = f"{id_prefix}-trait-choice-{_slug(label)}"
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
    existing functions need no changes."""
    bonuses = []
    for entry in ability_list or []:
        for key, val in entry.items():
            if key == "choose":
                continue
            bonuses.append({"ability_score": {"index": key, "name": key.upper(), "url": ""}, "bonus": val})
    return bonuses


def _ability_bonus_options_from_5etools(ability_list: list[dict]) -> dict | None:
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
        if not choose or "count" not in choose:
            continue
        from_list = choose.get("from", [])
        count = choose["count"]
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": 1}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    return None


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
    options.append({"option_type": "multiple", "items": [bonus_item(ab, 1) for ab in pool]})

    return {"choose": 1, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}


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


def _condition_immunities_from_5etools(raw: dict) -> list[str]:
    """Converts 5etools' conditionImmune field into a plain string list —
    confirmed empirically (2026-09-24) that all 7 races/reprints carrying
    this field use plain strings only, no choice/conditional shape."""
    return [entry for entry in (raw.get("conditionImmune") or []) if isinstance(entry, str)]


def _clean_innate_spell_name(raw: str) -> str:
    """Strips 5etools' spell-reference decorations from an
    additionalSpells.innate spell-name string: a trailing "|source" (e.g.
    "light|xphb", confirmed against Elf/XPHB's Drow legacy) and a trailing
    "#c"/"#<digit>" render tag (e.g. "hellish rebuke#2", confirmed against
    Tiefling/PHB — 5etools uses this to mark "display as a cantrip" vs.
    "display as cast at a specific slot level"; it does not change which
    catalog spell this resolves to, so it's dropped along with "|source").
    Confirmed empirically (2026-09-24) against every real innate-spell
    reference in races.json that both decorations only ever appear as a
    SUFFIX, never combined with anything else worth preserving."""
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


def _innate_spell_uses_and_names(level_value) -> tuple[str, list[str]]:
    """Converts ONE additionalSpells[].innate[level] value into a
    (uses-label, raw spell-name list) pair.

    Confirmed empirically (2026-09-24, re-verified 2026-09-24 after a code
    review caught a counterexample the first pass missed) against every
    real race AND subrace innate-spell entry in races.json: three shapes
    exist at this level —
    - a plain list of spell-name strings (e.g. Firbolg/MPMM's level-1
      entry, `["detect magic", "disguise self"]`) — no frequency wrapper
      at all means the real 5e rule is "at will" (e.g. Firbolg can cast
      Detect Magic/Disguise Self on itself at will; Yuan-Ti's Animal
      Friendship at will), confirmed against 5etools' own convention and
      cross-checked against the actual PHB/MPMM rules text for several of
      these races.
    - `{"daily": {"1": [...]}}` — usable a limited number of times per
      long rest. This is the overwhelming majority shape (96/97 real
      dict-wrapped entries across races AND subraces).
    - `{"rest": {"1": [...]}}` — the ONE real exception (Mark of
      Scribing/ERLW, a subrace of Gnome/PHB, level 1: `{"rest": {"1":
      ["comprehend languages"]}}`). The PREVIOUS version of this
      docstring claimed the wrapper key was "ALWAYS daily" — that claim
      was false, disproven by this exact record in this exact file.
      Mark of Scribing's own flavor text ("you can also cast comprehend
      languages once with this trait, and you regain the ability to cast
      it when you finish a short OR long rest") confirms "rest" means a
      short-or-long-rest recharge, a real but slightly more generous
      mechanic than "daily"'s long-rest-only cadence. This module still
      only models two uses-labels ("at-will" and "1/day"), so "rest" is
      treated identically to "daily" here — "1/day" undercounts the true
      short-rest cadence slightly but is far more accurate than the
      previous behavior (silently dropping the spell entirely). Modeling
      a distinct "short rest" uses-label is out of scope for this pass.
      In both shapes the inner count key is ALWAYS "1" for every real
      `innate` entry in the whole dataset — so this module only needs to
      model "1/day", not a general N/day. (5etools' OTHER field, `known`,
      also uses a "rest" wrapper on a few races — e.g. Firbolg/VGM,
      Eladrin/DMG, Mark of Handling/ERLW — but `known` is a different
      mechanic, out of scope for this task; see module-level Task 6
      docstring.)

    A shape this doesn't recognize (defensively, not seen in real data)
    returns ("at-will", []) rather than raising, so a future data update
    with an unanticipated shape silently contributes zero spells instead
    of crashing the whole conversion."""
    if isinstance(level_value, list):
        return "at-will", [n for n in level_value if isinstance(n, str)]
    if isinstance(level_value, dict):
        wrapper = level_value.get("daily")
        if not isinstance(wrapper, dict):
            wrapper = level_value.get("rest")
        if isinstance(wrapper, dict):
            names = wrapper.get("1")
            if isinstance(names, list):
                return "1/day", [n for n in names if isinstance(n, str)]
    return "at-will", []


def _innate_spell_ability(ability_raw) -> str | dict | None:
    """Converts additionalSpells[].ability — the spellcasting ability
    innate spells use for save DC/attack bonus — into either a fixed
    ability index string ("CHA") or, for the MAJORITY real shape
    (confirmed empirically, 2026-09-24: roughly three-quarters of real
    innate-spell-carrying entries use this, not the fixed-string form),
    a `{"choose": [...]}` list of candidate abilities the player picks
    from (e.g. Aarakocra/MPMM: `{"choose": ["int", "wis", "cha"]}`).

    Resolving that choice into a single committed ability is out of scope
    here — same "record the real data, don't build new choice-resolution
    machinery" line Task 5 drew for choice-shaped resistances — so the
    candidate list is carried through as descriptive data for display,
    not wired into catalog/choices.py's Choice machinery."""
    if isinstance(ability_raw, str):
        return ability_raw.upper()
    if isinstance(ability_raw, dict) and isinstance(ability_raw.get("choose"), list):
        options = [a.upper() for a in ability_raw["choose"] if isinstance(a, str)]
        if options:
            return {"choose": options}
    return None


def _innate_spells_from_5etools(race_raw: dict) -> list[dict]:
    """Converts 5etools' `additionalSpells` field into a flat list of
    innate-spell grants — ONLY the `innate` sub-key of each entry (this
    task's actual scope, "Innate spellcasting"); the sibling `known`/
    `prepared`/`expanded` sub-keys are a real but DIFFERENT mechanic
    (always-known cantrips/spells, Warlock-style always-prepared lists,
    and Mark-of-X's "adds spells to your class spell list" respectively —
    confirmed present in the real data, e.g. Aasimar's Light cantrip
    lives in `known`, not `innate`) and are a disclosed, narrower cut,
    not modeled by this function.

    `additionalSpells` is a LIST, not a single dict — confirmed
    empirically (2026-09-24) that most real races have exactly one entry,
    but a real few (Elf/XPHB: Drow/High Elf/Wood Elf; Tiefling/XPHB:
    Abyssal/Chthonic/Infernal — both reviewer-confirmed to actually reach
    this code and exercise this path end-to-end) have MULTIPLE entries,
    each carrying a "name" tag, representing mutually exclusive
    player-chosen variants (2024-style "lineage" options folded into one
    race record rather than modeled as separate subraces — confirmed no
    subrace records exist for these). Elf/LFL (Lorwyn/Shadowmoor) also has
    this multi-entry shape in the raw data, but it's a "_copy"-based
    record (see module docstring / _race_from_5etools) that
    _race_from_5etools filters out before this function is ever called on
    it — it was wrongly cited here as a "confirmed" example in an earlier
    pass despite never actually being exercised by this pipeline; dropped
    from this list for that reason. Silently flattening every entry's
    grants together would misrepresent a character as having ALL variants
    at once, which is worse than a disclosed cut. Instead, every grant is
    tagged with its source entry's `variant` name (None for the ordinary
    single-entry case, which is the overwhelming majority) so a consumer
    can group/filter by variant — this still doesn't build real choice-
    resolution machinery (same scope line as _innate_spell_ability), it
    just avoids losing or misrepresenting the data.

    Each returned dict: {"name" (title-cased fallback display name,
    catalog.spells is not imported by this module — see engine/resolve.py
    for the final catalog-backed name/spellId resolution), "spell_id"
    (naive slug guess), "level" (character level it becomes available),
    "uses" ("at-will" | "1/day"), "ability" (see
    _innate_spell_ability), "variant" (str | None)}."""
    results: list[dict] = []
    for entry in race_raw.get("additionalSpells") or []:
        if not isinstance(entry, dict):
            continue
        innate = entry.get("innate")
        if not isinstance(innate, dict):
            continue
        variant = entry.get("name") if isinstance(entry.get("name"), str) else None
        ability = _innate_spell_ability(entry.get("ability"))
        for level_key, level_value in innate.items():
            try:
                level = int(level_key)
            except (TypeError, ValueError):
                continue  # defensive — every real level key is a plain int string
            uses, raw_names = _innate_spell_uses_and_names(level_value)
            for raw_name in raw_names:
                clean = _clean_innate_spell_name(raw_name)
                if not clean:
                    continue
                results.append({
                    "name": clean.title(),
                    "spell_id": _slug(clean),
                    "level": level,
                    "uses": uses,
                    "ability": ability,
                    "variant": variant,
                })
    return results


def _trait_refs_from_entries(entries: list, id_prefix: str, race_ref: list[dict], subrace_ref: list[dict],
                              traits_by_index: dict[str, dict]) -> list[dict]:
    """Mints one synthetic trait per top-level `entries` item, added to
    traits_by_index (mutated in place, mirroring how the SRD loader builds
    one shared traits_by_index dict up front) so the existing
    trait-rendering/proficiency-scanning code in resolve.py (which already
    reads catalog.traits by id, already handles a trait with no
    `proficiencies` field correctly per Phase 3b-i) picks these up with
    zero changes. Subsequent tasks in this plan ADD proficiencies/resist/
    spells fields onto these same synthetic trait dicts — this task only
    creates them with description text."""
    trait_refs = []
    for i, entry in enumerate(entries or []):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue  # skip bare strings / unnamed entries — not real traits
        trait_id = f"{id_prefix}-trait-{i}"
        desc_lines = [e for e in entry.get("entries", []) if isinstance(e, str)]
        traits_by_index[trait_id] = {
            "index": trait_id, "races": race_ref, "subraces": subrace_ref,
            "name": entry["name"], "desc": desc_lines, "proficiencies": [], "url": "",
        }
        trait_refs.append({"index": trait_id, "name": entry["name"], "url": ""})
    return trait_refs


def _race_from_5etools(raw: dict, traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    index = f"{_slug(raw['name'])}-{source}"

    size_map = {"S": "Small", "M": "Medium", "L": "Large"}
    sizes = raw.get("size") or ["M"]
    size = size_map.get(sizes[0], "Medium")

    race_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, race_ref, [], traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, race_ref, [], traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, race_ref, [], traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)

    return {
        "index": index, "name": raw["name"],
        "speed": raw.get("speed") if isinstance(raw.get("speed"), int) else 30,
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", [])),
        "alignment": "", "age": "", "size": size, "size_description": "",
        "languages": [], "language_desc": "",
        "traits": trait_refs,
        "source": raw.get("source", ""),  # NEW field, SRD races don't have it (implicitly "SRD") — Task 6 uses this for filtering/labeling
        # NEW fields (Task 5), 5etools' own field names — see
        # _damage_modifiers_from_5etools/_condition_immunities_from_5etools
        # docstrings for the shape confirmed against real data.
        "resist": resist, "immune": immune, "vulnerable": vulnerable,
        "condition_immune": _condition_immunities_from_5etools(raw),
        # NEW field (Task 6) — see _innate_spells_from_5etools' docstring
        # for the shape and its empirically-grounded scope (innate only,
        # not known/prepared/expanded). engine.resolve._species_innate_spells
        # merges this with the subrace's own innate_spells and resolves
        # spell_id against catalog.spells (this module has no Catalog
        # access, by design — see module docstring).
        "innate_spells": _innate_spells_from_5etools(raw),
    }


def _subrace_from_5etools(raw: dict, race_ids: set[str], traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw or "name" not in raw:
        return None
    race_name = raw.get("raceName")
    race_source = raw.get("raceSource")
    if not race_name or not race_source:
        return None
    race_index = f"{_slug(race_name)}-{race_source.lower()}"
    if race_index not in race_ids:
        return None  # dangling reference — not seen in real data, but skip rather than crash

    source = (raw.get("source") or "unknown").lower()
    index = f"{race_index}-{_slug(raw['name'])}-{source}"

    subrace_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, [], subrace_ref, traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, [], subrace_ref, traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, [], subrace_ref, traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)

    return {
        "index": index, "name": raw["name"],
        "race": {"index": race_index, "name": race_name, "url": ""},
        "desc": "",
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "racial_traits": trait_refs,
        "url": "",
        # NEW fields (Task 5) — subraces carry resist/immune/vulnerable/
        # conditionImmune independently of their parent race (e.g. each
        # Genasi subrace grants a different elemental resistance; Stout
        # Halfling grants poison resistance) — see
        # engine.resolve._species_damage_modifiers, which merges race and
        # subrace values together.
        "resist": resist, "immune": immune, "vulnerable": vulnerable,
        "condition_immune": _condition_immunities_from_5etools(raw),
        # NEW field (Task 6) — subraces carry their OWN additionalSpells
        # independently of their parent race (confirmed empirically,
        # 2026-09-24: 50/98 real subraces carry the field, e.g. all nine
        # real Tiefling MTF fiend-patron subraces and Duergar/MTF — the
        # same race-then-subrace-additions relationship Task 5 already
        # established for resist/immune/vulnerable).
        "innate_spells": _innate_spells_from_5etools(raw),
    }


def _language_ref_from_key(key: str) -> dict | None:
    """Looks up a 5etools language slug (a fixed-grant object key like
    "giant", or a choose.from list entry like "deep speech") against
    reference_data.LANGUAGES, returning the SRD-shaped {index, name, url}
    reference, or None if it isn't a recognized language slug (not seen in
    real data — every real key/entry confirmed, 2026-09-26, against the
    brief's own dump command, resolves to a LANGUAGES index once run
    through the same _slug() every other name in this module already
    uses — e.g. "Deep Speech"/"deep speech" -> "deep-speech", matching
    LANGUAGES' own entry)."""
    lang = _LANGUAGES_BY_INDEX.get(_slug(key))
    if lang is None:
        return None
    return {"index": lang["index"], "name": lang["name"], "url": ""}


def _language_choice_option_from_5etools(name: str) -> dict:
    """Converts ONE entry of a background language choice's `choose.from`
    list into an options_array 'reference' option — the SAME mechanism
    _skill_choice_envelope_from_5etools/_tool_choice_envelope_from_5etools
    already use for their own enumerated lists. A literal "other" entry (4
    of 8 real choose.from lists carry it, e.g. Boros Legionnaire/GGR)
    means "or any other language of your choice" in the source text;
    since this Choice model has no free-text option, it's represented as
    its own distinctly labeled "Other" option (per the brief's own
    guidance), not silently dropped or folded into the full language
    list, which would make it indistinguishable from a real anyStandard
    wildcard option."""
    if name.lower() == "other":
        return {"option_type": "reference", "item": {"index": "other", "name": "Other", "url": ""}}
    lang = _language_ref_from_key(name)
    if lang is not None:
        return {"option_type": "reference", "item": lang}
    # Unrecognized language name — not seen in real data (every non-"other"
    # choose.from entry matches a reference_data.LANGUAGES slug exactly,
    # confirmed empirically, 2026-09-26) — best-effort slug/title-case
    # rather than silently dropping the option, same "disclosed, not
    # exercised" fallback discipline as e.g. the armor-category branch in
    # _proficiencies_from_5etools above.
    return {"option_type": "reference", "item": {"index": _slug(name), "name": name.title(), "url": ""}}


def _language_grants_from_5etools(raw: dict) -> tuple[list[dict], dict | None]:
    """Converts a background's `languageProficiencies` field into
    (fixed_grants, language_options_envelope) — the SRD-shaped
    `bg["languages"]` / `bg["language_options"]` fields resolve.py already
    reads (engine/resolve.py's fixed_languages list-comprehension and
    _background_choice_templates' language_options handling — confirmed
    UNCHANGED by this task, see this module's test coverage and
    test_resolve.py's own background-language tests).

    `languageProficiencies` is a list of dicts; confirmed empirically
    (2026-09-26, via the brief's own dump command against the real
    fetched backgrounds.json, 56 of 56 real records with this field) to
    combine three key shapes, sometimes on the SAME dict entry:
      - a literal language slug -> True: a FIXED grant (e.g.
        {"giant": True} — Rune Carver/BGG, Giant Foundling/BGG).
      - "anyStandard": N: a WILDCARD choice ("choose N of any language",
        49/56 records) — semantically identical to SRD's own bundled
        Acolyte language_options, so it reuses that SAME resource_list
        mechanism verbatim (zero new catalog/choices.py code).
      - "choose": {"from": [...]}: an ENUMERATED choice of N (N default
        1) — 8/56 records; 6 of those 8 carry NO "anyStandard" on the same
        entry and become a plain options_array envelope, the same
        mechanism every other enumerated choice in this module already
        uses.
    Multiple dict entries in the outer list combine ADDITIVELY (e.g. Clan
    Crafter/SCAG: {"dwarvish": True} + {"anyStandard": 1} as TWO separate
    list entries — fixed Dwarvish AND a free pick), mirroring races' own
    Aetherborn-style fixed+choice precedent (Phase 4a Task 2) the brief
    points at.

    KNOWN, DISCLOSED DATA-FIDELITY GAP (found during this task, 2026-09-26
    — NOT one of the brief's three claimed shapes, and NOT a resolve.py
    consumption-path bug, so NOT subject to this plan's Task-1b/2b
    "spin off a dedicated follow-up task" precedent): exactly 2 of 56 real
    records — Feylost/WBtW and Haunted One/VRGR — combine "anyStandard"
    AND "choose" on the SAME dict entry, a FOURTH shape the brief never
    describes. Their real published "Languages:" flavor text (read
    directly off their own `entries`, not inferred) gives this identical
    JSON shape CONTRADICTORY meanings:
      - Haunted One/VRGR: "Choose two, one of which must be Abyssal,
        Celestial, ... or Undercommon" — an ADDITIVE combination (1 free
        pick + 1 pick constrained to the list = 2 total), matching this
        function's general combining rule below exactly.
      - Feylost/WBtW: "One of your choice of Elvish, Gnomish, Goblin, or
        Sylvan" — a SINGLE pick from just the 4-item list; here the
        accompanying "anyStandard": 1 key does NOT represent an
        independent second grant — the real text has no second pick at
        all.
    No rule derivable from the JSON shape alone satisfies both (checked:
    neither "always additive" nor "choose's own count overrides
    anyStandard" fits both records). This function treats the combination
    as ADDITIVE (total = anyStandard + choose's count, sourced via the
    SAME resource_list mechanism as a plain anyStandard wildcard) —
    correct for Haunted One, but produces an over-generous choose:2 (of
    all 16 languages) for Feylost instead of its real choose:1 (of
    exactly its 4 named languages). This is the one known exception,
    affecting exactly 1 of 56 real background records with a
    languageProficiencies field. Note the underlying flat "choose N from
    set S" Choice model can't express Haunted One's real "at least one
    from subset X" sub-constraint under EITHER reading, so neither record
    is fully representable in this model regardless of which reading is
    picked — disclosed here, and in the Task 3 report, for the controller
    to decide whether it's worth a dedicated follow-up."""
    fixed: list[dict] = []
    any_count = 0
    choose_count = 0
    choose_options: list[dict] = []
    saw_choice = False

    for entry in raw.get("languageProficiencies") or []:
        if not isinstance(entry, dict):
            continue
        for key, value in entry.items():
            if key in ("anyStandard", "choose"):
                continue
            if value is True:
                lang = _language_ref_from_key(key)
                if lang is not None:
                    fixed.append(lang)

        any_n = entry.get("anyStandard")
        if isinstance(any_n, int) and not isinstance(any_n, bool):
            any_count += any_n
            saw_choice = True

        choose = entry.get("choose")
        if isinstance(choose, dict):
            choose_count += choose.get("count", 1)
            saw_choice = True
            choose_options.extend(_language_choice_option_from_5etools(name) for name in choose.get("from", []))

    if not saw_choice:
        return fixed, None

    total = any_count + choose_count
    if any_count == 0 and choose_options:
        # A pure enumerated list, no wildcard slot at all — the common
        # "choose N of {named list}" shape (6 of 8 real 'choose' records).
        envelope = {"choose": total, "type": "languages",
                    "from": {"option_set_type": "options_array", "options": choose_options}}
    else:
        # A wildcard is present, alone or combined with a named list (see
        # this function's own docstring for the combined case's known,
        # disclosed fidelity gap) — reuses SRD's own bundled Acolyte
        # language_options mechanism verbatim.
        envelope = {"choose": total, "type": "languages",
                    "from": {"option_set_type": "resource_list", "resource_list_url": "/api/2014/languages"}}
    return fixed, envelope


def _background_from_5etools(raw: dict) -> dict | None:
    """Converts one raw 5etools background record into the SAME dict shape
    catalog/loader.py already produces for the bundled SRD Acolyte
    background (confirmed empirically, Step 1: index, name,
    starting_proficiencies, language_options, languages,
    starting_equipment, starting_gold, starting_equipment_options,
    feature, source) — plus two NEW fields: `feats` (mirroring races' own
    `source` precedent, populated by this plan's later Task 6), and
    `starting_proficiency_choices` (Task 2 — the CHOICE portion of
    skillProficiencies/toolProficiencies, as opposed to the fixed grants
    `starting_proficiencies` already carries; see
    _proficiency_choices_from_5etools).

    Unlike races, backgrounds carry skillProficiencies/toolProficiencies
    as the exact same length-1-list-of-booleans shape
    _proficiencies_from_5etools already converts for races (confirmed
    empirically, Step 1, against a real XPHB Acolyte record) — that
    function reads only skillProficiencies/toolProficiencies/
    weaponProficiencies/armorProficiencies off whatever dict it's given
    (via .get, all optional) and was never actually race-specific despite
    its `race_raw` parameter name, so it's called here UNCHANGED, no
    signature change needed. (Backgrounds carry no weapon/armor
    proficiency fields in the real data, so those two loops simply no-op
    for every background record — confirmed empirically, Step 1: no
    weaponProficiencies/armorProficiencies key appears on any real
    background.)

    `language_options`/`languages` (Task 3 — fixed and choice-shaped
    language grants; see _language_grants_from_5etools for the full shape
    grounding, including a disclosed data-fidelity gap on 1 of 56 real
    records) are now populated. `ability_bonus_options` (Task 4 — the
    2024-style weighted ability-score-improvement choice; see
    _ability_bonus_options_from_5etools_weighted_pair) is now populated
    too. `starting_equipment`/`starting_gold`/`starting_equipment_options`
    (equipment package choices) and `feats` are still deliberately left as
    placeholders — separate follow-up tasks in this same plan (Tasks 5-6).
    `feature` is left empty: engine/resolve.py never reads a
    background's `feature` field for anything mechanical today (confirmed
    by grep, Step 1) — SRD's own bundled backgrounds carry rich flavor
    text there that resolve.py still never consumes, so leaving it empty
    here is consistent with the existing bundled-data behavior, not a new
    gap this task introduces.

    _copy-based records are skipped, same reasoning as races (see module
    docstring)."""
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    slug = _slug(raw["name"])
    index = f"{slug}-{source}"
    fixed_languages, language_options = _language_grants_from_5etools(raw)

    return {
        "index": index,
        "name": raw["name"],
        "starting_proficiencies": _proficiencies_from_5etools(raw),
        "starting_proficiency_choices": _proficiency_choices_from_5etools(raw),
        "language_options": language_options,
        "languages": fixed_languages,
        "starting_equipment": [],  # Task 5
        "starting_gold": None,  # Task 5
        "starting_equipment_options": [],  # Task 5
        "feature": {"name": "", "desc": []},  # not read mechanically by resolve.py today, see docstring above
        "ability_bonus_options": _ability_bonus_options_from_5etools_weighted_pair(raw.get("ability", [])),
        "source": raw.get("source", ""),
        "feats": [],  # Task 6
    }


def load_official_backgrounds(official_dir: Path) -> list[dict]:
    bg_path = official_dir / "backgrounds.json"
    if not bg_path.exists():
        return []
    with open(bg_path, encoding="utf-8") as f:
        data = json.load(f)
    backgrounds = []
    for raw in data.get("background", []):
        converted = _background_from_5etools(raw)
        if converted is not None:
            backgrounds.append(converted)
    return backgrounds


def load_official_races(official_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]:
    races_path = official_dir / "races.json"
    if not races_path.exists():
        return [], [], {}
    with open(races_path, encoding="utf-8") as f:
        data = json.load(f)

    traits_by_index: dict[str, dict] = {}
    races = []
    for raw in data.get("race", []):
        converted = _race_from_5etools(raw, traits_by_index)
        if converted is not None:
            races.append(converted)

    race_ids = {r["index"] for r in races}
    subraces = []
    for raw in data.get("subrace", []):
        converted = _subrace_from_5etools(raw, race_ids, traits_by_index)
        if converted is not None:
            subraces.append(converted)

    return races, subraces, traits_by_index
