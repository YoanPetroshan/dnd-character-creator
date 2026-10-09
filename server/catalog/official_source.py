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
import itertools
import json
import re
import sys

_repo_root = Path(__file__).resolve().parents[2]  # server/catalog/official_source.py -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    # Appended, not prepended: the root also holds the v1 app.py/storage.py,
    # which must never shadow the server's own modules (only `chargen` is needed).
    sys.path.append(str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402  (must follow the sys.path fix above)
from catalog.reference_data import SKILL_NAMES, TOOLS, LANGUAGES, ruleset_for_edition, ruleset_for_feat  # noqa: E402  (same reason)

_LANGUAGES_BY_INDEX = {lang["index"]: lang for lang in LANGUAGES}

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


def _sentence_case(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


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
        if granted is True:
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


def _species_feat_grants_from_5etools(raw: dict) -> list[dict]:
    """5etools race `feats`: `{"any": n}` (a feat of any eligible category:
    Custom Lineage, Variant Human) -> `{"count": n, "category": None}`;
    `{"anyFromCategory": {"category": [c], "count": n}}` (Human/XPHB's
    Versatile: an Origin feat) -> `{"count": n, "category": c}`. Any other
    shape is ignored. Only three real records carry the field."""
    grants = []
    for entry in raw.get("feats") or []:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("any"), int) and not isinstance(entry["any"], bool):
            grants.append({"count": entry["any"], "category": None})
            continue
        spec = entry.get("anyFromCategory")
        if isinstance(spec, dict):
            cats = [c for c in spec.get("category") or [] if isinstance(c, str)]
            count = spec.get("count", 1)
            if len(cats) == 1 and isinstance(count, int) and not isinstance(count, bool):
                grants.append({"count": count, "category": cats[0]})
    return grants


def _variant_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _mod_replaces_entry(version: dict) -> bool:
    """True when an explicit `_versions` item swaps out a base trait
    (`_mod.entries` mode replaceArr), i.e. it is one alternative among
    several rather than an optional addition (appendArr)."""
    mods = (version.get("_mod") or {}).get("entries")
    mods = mods if isinstance(mods, list) else [mods]
    return any(isinstance(m, dict) and m.get("mode") == "replaceArr" for m in mods)


def _variant_from_source(vid: str, name: str, src: dict, resist: list[str]) -> dict:
    """One variant: only the structured data keys a version can change.
    A key explicitly set to null is recorded in `removes`."""
    removes = [k for k in ("skillProficiencies", "darkvision", "additionalSpells", "speed") if k in src and src[k] is None]
    walk, _ = _speed_from_5etools(src.get("speed"))
    return {
        "id": vid, "name": name,
        "speed": walk,
        "darkvision": _darkvision_from_5etools(src),
        "resist": resist,
        "innate_spells": _innate_spells_from_5etools({"additionalSpells": src.get("additionalSpells") or []}),
        "skill_proficiencies": src.get("skillProficiencies") if isinstance(src.get("skillProficiencies"), list) else None,
        "removes": removes,
    }


def _race_variants_from_5etools(raw: dict) -> list[dict]:
    """Mutually exclusive alternatives of a race from its `_versions`:
    explicit versions that REPLACE a base trait (name = the text after "; ",
    e.g. "Drow Lineage") and abstract versions with `_implementations`
    (Dragonborn colours; name = the abstract name with `{{var}}` filled in,
    resist from the implementation or its `_variables`). Races without
    `_versions` (almost all) get []."""
    variants: list[dict] = []
    for version in raw.get("_versions") or []:
        if not isinstance(version, dict):
            continue
        if isinstance(version.get("_abstract"), dict):
            template = str(version["_abstract"].get("name") or raw["name"])
            for impl in version.get("_implementations") or []:
                if not isinstance(impl, dict):
                    continue
                variables = impl.get("_variables") or {}
                name = re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), m.group(0))), template)
                resist = [r for r in (impl.get("resist") or variables.get("resist") or []) if isinstance(r, str)]
                variants.append(_variant_from_source(_variant_slug(name), name, impl, resist))
        elif isinstance(version.get("name"), str) and _mod_replaces_entry(version):
            name = version["name"].split("; ", 1)[-1]
            resist = [r for r in (version.get("resist") or []) if isinstance(r, str)]
            variants.append(_variant_from_source(_variant_slug(name), name, version, resist))
    return variants


def _resist_options_from_5etools(raw: dict) -> dict | None:
    """The `resist: [{"choose": {"from": [...]}}]` shape (Dragonborn
    ancestry, 2024 Tiefling legacy, Reborn) as a Choice envelope of
    damage-type strings; fixed string entries stay in `resist`."""
    for entry in raw.get("resist") or []:
        if not isinstance(entry, dict):
            continue
        choose = entry.get("choose")
        if not isinstance(choose, dict) or not choose.get("from"):
            continue
        options = [{"option_type": "string", "string": str(t).capitalize()} for t in choose["from"] if isinstance(t, str)]
        if options:
            return {"choose": choose.get("count", 1), "type": "damage_resistances",
                    "from": {"option_set_type": "options_array", "options": options}}
    return None


_NAMELESS_SKIP_KEYS = frozenset({
    "source", "raceName", "raceSource", "page", "srd", "basicRules", "reprintedAs", "hasFluff",
    "hasFluffImages", "_versions", "_copy", "otherSources", "alias", "soundClip", "name", "overwrite",
})


def _merge_nameless_subraces(data: dict) -> tuple[list[dict], list[dict]]:
    """5etools models a race's default form as a nameless subrace (PHB
    Human: the +1-to-everything lives there; Dragonborn/Half-Elf/
    Half-Orc/Tiefling carry only reprint metadata). Fold each into its
    parent race and return (races, named subraces). Because the nameless
    form is the ALTERNATIVE to any named subrace, a parent that gained
    ability scores this way has them replaced (overwrite.ability) by every
    named subrace, as in 5etools."""
    races = [dict(r) for r in data.get("race", [])]
    by_key = {(r.get("name"), r.get("source")): r for r in races}
    named = []
    ability_merged_parents = set()
    for sub in data.get("subrace", []):
        if sub.get("name"):
            named.append(sub)
            continue
        parent = by_key.get((sub.get("raceName"), sub.get("raceSource")))
        if parent is None or "_copy" in parent:
            continue
        for key, value in sub.items():
            if key in _NAMELESS_SKIP_KEYS:
                continue
            if key not in parent:
                parent[key] = value
            elif isinstance(parent[key], list) and isinstance(value, list):
                parent[key] = parent[key] + value
            elif key == "darkvision" and isinstance(value, int) and isinstance(parent[key], int):
                parent[key] = max(parent[key], value)
            if key == "ability":
                ability_merged_parents.add((parent.get("name"), parent.get("source")))
    for i, sub in enumerate(named):
        if (sub.get("raceName"), sub.get("raceSource")) in ability_merged_parents:
            named[i] = {**sub, "overwrite": {**(sub.get("overwrite") or {}), "ability": True}}
    return races, named


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

    Race candidate lists are carried through as descriptive data. For feats
    the list is resolved by engine.resolve's `{prefix}:spell-ability`
    Choice (see _feat_spell_choice_templates); feat text can also override
    it via _feat_spell_ability_override."""
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
                    "spell_id": slug(clean),
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
    index = f"{slug(raw['name'])}-{source}"

    size_map = {"S": "Small", "M": "Medium", "L": "Large"}
    sizes = raw.get("size") or ["M"]
    size = size_map.get(sizes[0], "Medium")
    # More than one listed size (30 races, always ["S","M"]): the player picks.
    size_options = list(dict.fromkeys(size_map[s] for s in sizes if s in size_map)) if len(sizes) > 1 else []

    race_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, race_ref, [], traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, race_ref, [], traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, race_ref, [], traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)
    walk, movement = _speed_from_5etools(raw.get("speed"))

    return {
        "index": index, "name": raw["name"],
        "speed": walk if walk is not None else 30,
        "movement": movement,  # non-walk modes: {fly|swim|climb: int | True (= walking speed)}
        "darkvision": _darkvision_from_5etools(raw),
        "resist_options": _resist_options_from_5etools(raw),
        "feat_grants": _species_feat_grants_from_5etools(raw),
        "variants": _race_variants_from_5etools(raw),
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", []), raw.get("lineage")),
        "alignment": "", "age": "", "size": size, "size_options": size_options, "size_description": "",
        "languages": [], "language_desc": "",
        "traits": trait_refs,
        "source": raw.get("source", ""),  # NEW field, SRD races don't have it (implicitly "SRD") — Task 6 uses this for filtering/labeling
        "ruleset": ruleset_for_edition(raw),
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
    race_index = f"{slug(race_name)}-{race_source.lower()}"
    if race_index not in race_ids:
        return None  # dangling reference — not seen in real data, but skip rather than crash

    source = (raw.get("source") or "unknown").lower()
    index = f"{race_index}-{slug(raw['name'])}-{source}"

    subrace_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, [], subrace_ref, traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, [], subrace_ref, traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, [], subrace_ref, traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)
    walk, movement = _speed_from_5etools(raw.get("speed"))

    return {
        "index": index, "name": raw["name"],
        "race": {"index": race_index, "name": race_name, "url": ""},
        "source": raw.get("source", ""),
        "desc": "",
        "speed": walk,  # walk-speed override of the parent race, None = inherit
        "movement": movement,
        "darkvision": _darkvision_from_5etools(raw),
        "resist_options": _resist_options_from_5etools(raw),
        "feat_grants": _species_feat_grants_from_5etools(raw),
        # 5etools `overwrite.ability`: this subrace's scores REPLACE the race's.
        "overwrite_ability": bool((raw.get("overwrite") or {}).get("ability")),
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", [])),
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
    through the same slug() every other name in this module already
    uses — e.g. "Deep Speech"/"deep speech" -> "deep-speech", matching
    LANGUAGES' own entry)."""
    lang = _LANGUAGES_BY_INDEX.get(slug(key))
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
    return {"option_type": "reference", "item": {"index": slug(name), "name": name.title(), "url": ""}}


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
    Multiple dict entries in the outer list do NOT always combine
    additively — CORRECTED by Finding 2 of the final whole-branch review
    (2026-09-27), which disproved this docstring's own previous claim
    that Clan Crafter/SCAG's {"dwarvish": True} + {"anyStandard": 1}, as
    TWO separate list entries, means "fixed Dwarvish AND a free pick".
    Clan Crafter's real published "Languages:" text (read directly off
    its own `entries`, not inferred) is "Dwarvish or one of your choice
    if you already speak Dwarvish" — a SINGLE grant, conditionally
    SUBSTITUTED, not an additional pick stacked on top. Confirmed
    empirically that Clan Crafter is the ONLY real background whose
    languageProficiencies has more than one OUTER-LIST entry at all (every
    other multi-key combination, e.g. Giant Foundling/BGG below, packs
    everything onto a SINGLE dict entry instead) — so this correction
    changes behavior for exactly the one record it was wrong about, and
    cannot affect any other real record. The distinguishing signal used
    below: when a SEPARATE list entry contributes ONLY a fixed grant (no
    wildcard/choose of its own on that same entry) and another separate
    entry contributes a wildcard/choose, that split-across-entries shape
    reads as "X, or Y if condition" — only the fixed grant is kept, the
    wildcard is dropped entirely. A fixed grant COMBINED WITH a wildcard
    on the SAME dict entry (Giant Foundling/BGG: {"giant": True,
    "anyStandard": 1}, real text "Giant AND one other language of your
    choice") is unaffected by this change and still combines additively,
    exactly as before — see
    test_fixed_grant_combined_with_any_standard_on_the_same_entry.

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
    saw_fixed_only_entry = False  # a separate list entry granting a fixed language with no wildcard/choose of its own on that same entry — see docstring

    for entry in raw.get("languageProficiencies") or []:
        if not isinstance(entry, dict):
            continue
        entry_granted_fixed = False
        for key, value in entry.items():
            if key in ("anyStandard", "choose"):
                continue
            if value is True:
                lang = _language_ref_from_key(key)
                if lang is not None:
                    fixed.append(lang)
                    entry_granted_fixed = True

        entry_has_wildcard = False
        # "anyStandard" is backgrounds' own wildcard key; "any" is the
        # feat-side synonym (Task 4 grounding, 2026-09-28, against the real
        # fetched feats.json — every one of the 7 real feats with a
        # languageProficiencies wildcard uses "any", never "anyStandard";
        # confirmed 0/56 real background records use "any" either, so
        # reading both keys here is collision-free for the already-covered
        # background path).
        any_n = entry.get("anyStandard", entry.get("any"))
        if isinstance(any_n, int) and not isinstance(any_n, bool):
            any_count += any_n
            saw_choice = True
            entry_has_wildcard = True

        choose = entry.get("choose")
        if isinstance(choose, dict):
            choose_count += choose.get("count", 1)
            saw_choice = True
            entry_has_wildcard = True
            choose_options.extend(_language_choice_option_from_5etools(name) for name in choose.get("from", []))

        if entry_granted_fixed and not entry_has_wildcard:
            saw_fixed_only_entry = True

    if saw_fixed_only_entry and saw_choice:
        # "X, or Y if you already know X" (Clan Crafter/SCAG, the only real
        # record this fires for) — the wildcard/enumerated portion read
        # from a DIFFERENT entry than the fixed grant is a conditional
        # SUBSTITUTE for it, not an additional pick — see docstring above.
        return fixed, None

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


def _feats_from_5etools(raw: dict) -> tuple[list[str], list[str], list[str]]:
    """Converts a background's `feats` field — confirmed empirically
    (Step 1, 2026-09-27) to be a list of single-key boolean-map dicts,
    `{"<feat name>|<source>": True}`, the SAME convention
    skillProficiencies/toolProficiencies already use — into a plain list
    of feat ids: `|source` stripped, the remaining name run through the
    same `slug()` every other |source-suffixed field already gets.

    Pure inert data pass-through: no resolution against a feat catalog
    (none exists in this app yet), no prerequisite checking, no effect
    application.

    Semicolon-suffixed spell-list variant names (Phase 4c-i Task 6 fix,
    found by Task 5's own review): 4 real records (Acolyte/XPHB, Guide/
    XPHB, Moonwell Pilgrim/FRHoF, Sage/XPHB) grant not plain "magic
    initiate|xphb" but a spell-list-restricted variant, e.g. "magic
    initiate; cleric|xphb" — confirmed against the real fetched
    backgrounds.json (2026-09-28) to be the ONLY grant keys in the whole
    dataset containing a literal ";" (checked exhaustively, not assumed
    from this one case). catalog.feats has no record named "Magic
    Initiate; Cleric" at all — the real Magic Initiate feat record is
    named plain "Magic Initiate" in both PHB and XPHB (confirmed against
    feats.json) — so slugging the ";"-suffixed grant key verbatim used to
    produce "magic-initiate;-cleric", which matched ZERO catalog feats
    and was silently dropped by engine.resolve._resolve_granted_feats'
    own "no match" path (a DIFFERENT failure mode from that function's
    disclosed "ambiguous source, more than one match" guard — this was
    "wrong slug, no match at all"). The "; <spell list>" suffix names
    which spell list the grant is restricted to — modeling that
    restriction would mean granting specific spells/cantrips, which
    `additionalSpells` being out of scope for this plan (design
    spec; feats' spell grants were later added separately, see
    _feat_spells_from_5etools) already rules out — so the fix here is only to recover the
    grant as PLAIN "Magic Initiate" (stripping everything from the first
    ";" onward before slugging), not to model the restriction itself.
    Once fixed, these 4 records resolve exactly like the OTHER plain
    "magic initiate|xphb"/"magic initiate|phb" grants already do: still
    silently skipped, but via the SAME already-disclosed "matches feats
    in more than one source" ambiguity guard every other plain Magic
    Initiate grant hits (Magic Initiate has both a PHB and an XPHB
    record) — not a new, separate zero-match gap. No effect on this
    task's own ability_bonuses/proficiencies/languages/resist/immune/
    senses/expertise_skills/saving_throw_proficiencies output either way
    (confirmed: neither real Magic Initiate record carries any of those
    fields today), but fixing the slug itself (rather than only
    documenting the gap) keeps this function's output honest about what
    the grant actually names, and avoids the same ";"-suffix pattern
    silently breaking a FUTURE feat variant that does carry one of those
    fields.

    Returns (feats, feat_options, feat_refs) — fixed a "one true grant"
    alternatives split, Finding 2 of the final whole-branch review
    (2026-09-27):
    Task 6's original version combined EVERY `is True` entry additively
    into one `feats` list, which is correct for 69 of 71 real records
    (exactly one `is True` entry each) but wrong for the other two —
    Rewarded/BMT: `[{"lucky|phb": True}, {"magic initiate|phb": True},
    {"skilled|phb": True}]`, whose real published text is "You gain the
    Lucky, Magic Initiate, or Skilled feat (your choice)" — a CHOICE of
    one, not a grant of all three; Ruined/BMT is the identical shape
    (Alert/Skilled/Tough). Additive combination was silently over-
    granting both — inert today (feats aren't a mechanic yet, Phase 4c's
    job) but would silently over-grant once Phase 4c starts consuming
    this data for real. `feat_options` carries the "one of these"
    alternatives for that 2-record case, mirroring the fixed-vs-choice
    field pairs this same module already uses everywhere else
    (starting_proficiencies/starting_proficiency_choices, languages/
    language_options, ability_bonuses/ability_bonus_options) rather than
    inventing a new convention. `feats` stays a single-element list for
    every real record with exactly one grant (unchanged from before), and
    both lists are empty together only when the background has no `feats`
    field, or only a wildcard entry (see below), at all.

    Only `is True` entries are considered in the first place — the SAME
    filter _proficiencies_from_5etools already applies to exclude choice/
    wildcard envelopes without needing to special-case their key names.
    This matters here too: 4 real records (Haunted One/RHW, Investigator/
    RHW, Mist Wanderer, Spirit Medium) carry a SECOND entry alongside
    their plain grant, `{"anyFromCategory": {"category": [...]}}` — a
    "pick any feat from category X" wildcard whose value is a dict, not
    True. That entry is excluded by this same `is True` check, not by
    name — a wildcard feat grant like this has nothing to resolve against
    without a feat catalog, so it's silently dropped rather than guessed
    at (disclosed here, not a bug: still out of scope).

    Returns a THIRD value, `feat_refs` (Finding 1 of the final whole-branch
    review, 2026-09-28): a source-qualified reference list, parallel to
    `feats` (empty whenever `feats` itself is empty, e.g. the alternatives
    branch below), built as `slug(bare_name) + "-" + source.lower()` — the
    EXACT SAME "slug(name)-source" convention this module already uses to
    build every catalog feat's own `index` (see _feat_from_5etools) —
    rather than the bare, source-stripped slug `true_feat_ids` above
    throws the source away to produce.

    Root cause this fixes: the raw grant key ALREADY names the source
    (e.g. "tavern brawler|xphb"), but `true_feat_ids` above discards
    everything after "|" before slugging, leaving engine.resolve.
    _resolve_granted_feats nothing to disambiguate with when a bare slug
    matches feats in more than one source (9 real slugs do — see that
    function's own docstring) — 28 of 70 real unambiguous single-feat
    grants were hitting that ambiguity guard and being silently skipped
    even though the source was known all along. `feat_refs` recovers it:
    resolve.py tries an exact match against catalog.feats by this
    "slug-source" id FIRST, falling back to the existing bare-slug/
    ambiguity logic only when no ref is available (hand-authored test
    data built without this field) or the ref doesn't match any real
    catalog feat.

    One real grant key is capitalized ("Skilled|xphb", Noble/XPHB,
    confirmed 2026-09-28) — `slug()` lowercases unconditionally, so
    `slug("Skilled")` -> "skilled" and the resulting ref ("skilled-xphb")
    matches catalog.feats' own index exactly, same as every lowercase
    grant key."""
    true_feat_ids: list[str] = []
    true_feat_refs: list[str] = []
    for entry in raw.get("feats") or []:
        for feat_key, granted in entry.items():
            if granted is True:
                # "|" splits the source suffix off FIRST (kept for
                # feat_refs below), then ";"-strip BEFORE slugging (see
                # docstring above): recovers the base feat name from a
                # spell-list-restricted variant like "magic initiate;
                # cleric" -> "magic initiate", the only real pattern this
                # dataset uses a literal ";" for.
                name_part, _, source_part = feat_key.partition("|")
                bare_name = name_part.split(";", 1)[0].strip()
                bare_slug = slug(bare_name)
                true_feat_ids.append(bare_slug)
                source_part = source_part.strip().lower()
                true_feat_refs.append(f"{bare_slug}-{source_part}" if source_part else "")

    if len(true_feat_ids) > 1:
        # More than one simultaneous True-valued entry means ALTERNATIVES
        # ("one of these"), not a simultaneous grant of every one of them
        # — see docstring above. Rewarded/Ruined (BMT) are the only two
        # real records this branch is exercised by. feat_refs stays empty
        # here too, mirroring `feats` itself — these candidates are
        # unresolved alternatives, not an actual grant to resolve against
        # the catalog (see engine.resolve._resolve_granted_feats' own
        # "feat_options candidates are NOT resolved for effects" comment).
        return [], true_feat_ids, []
    return true_feat_ids, [], true_feat_refs


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
    records, and a Finding-2 correction to that function's own additive-
    combination rule) are now populated. `ability_bonus_options` (Task 4 —
    the 2024-style weighted ability-score-improvement choice; see
    _ability_bonus_options_from_5etools_weighted_pair) is now populated
    too. `starting_equipment_options` (Task 5 — the A/B-style starting
    equipment PACKAGE CHOICE; see _starting_equipment_options_from_5etools
    for the full shape grounding, including a disclosed gap in what
    happens after a bundle with a synthetic/non-catalog member is
    selected) is now populated. `starting_equipment`/`starting_gold` (the
    FIXED, no-choice `"_"`-keyed equipment list 74/135 real backgrounds
    carry — e.g. Anthropologist/ToA has ONLY this, no package choice at
    all) — a real, disclosed gap Task 5 deliberately left as a follow-up
    (its own brief scoped it to the package CHOICE specifically) — are now
    also populated, fixed by Finding 1 of the final whole-branch review
    (2026-09-27); see _fixed_starting_equipment_from_5etools for the full
    shape grounding. That same function also returns this record's fixed-
    grant NARRATIVE items (flavor-only gear / category placeholders /
    no-catalog-match items from the `"_"` list), carried on the new
    `starting_narrative_items` field — engine/resolve.py merges this with
    its own selection-driven narrative items (previously the ONLY source
    of sheet.equipment.narrativeItems) into one list. `feats`/
    `feat_options` (Task 6, corrected by Finding 2 — see
    _feats_from_5etools for the full shape grounding, including a
    disclosed exclusion of a non-boolean "anyFromCategory" wildcard entry
    this app has no feat catalog to resolve against, and the fixed-vs-
    alternatives split that replaces Task 6's original always-additive
    behavior) are now populated too — pure inert data, no mechanical
    effect. `feature` is left empty: engine/resolve.py
    never reads a
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
    name_slug = slug(raw["name"])
    index = f"{name_slug}-{source}"
    fixed_languages, language_options = _language_grants_from_5etools(raw)
    fixed_equipment, fixed_gold, fixed_narrative_items = _fixed_starting_equipment_from_5etools(raw)
    feats, feat_options, feat_refs = _feats_from_5etools(raw)

    return {
        "index": index,
        "name": raw["name"],
        "starting_proficiencies": _proficiencies_from_5etools(raw),
        "starting_proficiency_choices": _proficiency_choices_from_5etools(raw),
        "language_options": language_options,
        "languages": fixed_languages,
        "starting_equipment": fixed_equipment,
        "starting_gold": fixed_gold,
        "starting_equipment_options": _starting_equipment_options_from_5etools(raw),
        "starting_narrative_items": fixed_narrative_items,
        "feature": {"name": "", "desc": []},  # not read mechanically by resolve.py today, see docstring above
        "ability_bonus_options": _ability_bonus_options_from_5etools_weighted_pair(raw.get("ability", [])),
        "source": raw.get("source", ""),
        "ruleset": ruleset_for_edition(raw),
        "feats": feats,
        "feat_options": feat_options,
        # Finding 1 of the final whole-branch review (2026-09-28): a
        # source-qualified parallel to `feats` — see _feats_from_5etools'
        # own docstring. engine.resolve._resolve_granted_feats tries this
        # FIRST (exact match against catalog.feats), falling back to the
        # bare-slug/ambiguity logic only when it's absent or doesn't match
        # (e.g. hand-authored test data built without this field).
        "feat_refs": feat_refs,
        # feat-additional-spells plan: {feat ref: variant name} for
        # spell-list-restricted grants ("magic initiate; cleric|xphb").
        "feat_variant_hints": _feat_variant_hints_from_5etools(raw),
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
    raw_races, raw_subraces = _merge_nameless_subraces(data)
    for raw in raw_races:
        converted = _race_from_5etools(raw, traits_by_index)
        if converted is not None:
            races.append(converted)

    race_ids = {r["index"] for r in races}
    race_rulesets = {r["index"]: r["ruleset"] for r in races}
    subraces = []
    for raw in raw_subraces:
        converted = _subrace_from_5etools(raw, race_ids, traits_by_index)
        if converted is not None:
            converted["ruleset"] = race_rulesets[converted["race"]["index"]]  # subspecies inherit the species' ruleset
            subraces.append(converted)

    return races, subraces, traits_by_index


# --- Feats (Phase 4c-i) ---
#
# UNLIKE races/subraces/traits/backgrounds above, there is NO bundled SRD
# feats file at all — the 2014 SRD has no feats mechanic — so
# load_official_feats() has no SRD counterpart to merge against in
# loader.py's load(): Catalog.feats is populated purely from this official
# data, and is simply an empty dict when official data hasn't been fetched
# on this machine (load_official_feats returns [] when feats.json is
# missing, see below), not a partial merge.
#
# Step 1 grounding (2026-09-27, against the real fetched feats.json): 305
# raw records, 0 carrying a "_copy" key — unlike races/backgrounds, this
# dataset has no _copy/_mod reprint shorthand at all, so every record is
# already complete and none are skipped for that reason (the `_copy` check
# below is kept anyway, matching every other loader in this module, in case
# a future data refresh introduces one). 47 feat names repeat across
# sourcebooks (e.g. "Alert" in both PHB and XPHB), but EVERY repeat is a
# distinct-source pair — confirmed exhaustively, not sampled, that no two
# records share both the same name AND the same source — so the same
# source-qualified index scheme races/backgrounds already use
# ("alert-phb", "alert-xphb") is collision-free here too.


def _feat_from_5etools(raw: dict) -> dict | None:
    """Task 1 (this task) is scaffolding ONLY: the shape below carries every
    field a later task in this same plan will populate (ability bonuses —
    Task 2; proficiencies — Task 3; languages — Task 4; resistances/
    immunities/senses — Task 5; expertise/saving-throw proficiencies/
    prerequisite checking — Task 6), each left as an empty/None placeholder
    for now, mirroring the exact scaffold-first-populate-later pattern both
    Phase 4a's load_official_races() and Phase 4b's load_official_backgrounds()
    used for their own first tasks. `entries` is carried through raw and
    unconverted — display-only for now, same "pure data pass-through" scope
    line _damage_modifiers_from_5etools' docstring draws elsewhere in this
    module."""
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    name_slug = slug(raw["name"])
    index = f"{name_slug}-{source}"
    fixed_languages, language_options = _language_grants_from_5etools(raw)
    # Task 5: resist/immune/senses — reuses the SAME race-side
    # _damage_modifiers_from_5etools/_condition_immunities_from_5etools
    # conversion machinery UNCHANGED (both already read off a generic raw
    # dict via .get, nothing race-specific despite living next to
    # race-only code — see _background_from_5etools' own docstring for
    # this same reuse precedent). Feats carry no `vulnerable` field in the
    # real data (0/305, confirmed 2026-09-28), so that third return value
    # is discarded here rather than added to the scaffold. `senses` has no
    # race-side counterpart to reuse — see _senses_from_5etools' own
    # docstring.
    feat_resist, feat_immune, _feat_vulnerable = _damage_modifiers_from_5etools(raw)
    feat_innate_spells, feat_spell_choices, feat_spell_variants = _feat_spells_from_5etools(raw, index)

    return {
        "index": index,
        "name": raw["name"],
        "source": raw.get("source", ""),
        "ruleset": ruleset_for_feat(raw),
        "category": raw.get("category", ""),
        "repeatable": bool(raw.get("repeatable")),
        "entries": raw.get("entries", []),
        "prerequisite": raw.get("prerequisite", []),  # Task 6 (prerequisite checking)
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _feat_ability_bonus_options_from_5etools(raw.get("ability", [])),
        # Task 3: skill/tool/weapon/armor proficiencies — reuses the SAME
        # race/background-side conversion machinery UNCHANGED
        # (_proficiencies_from_5etools/_proficiency_choices_from_5etools
        # read generic dicts, never actually race/background-specific
        # despite their parameter names — see _background_from_5etools'
        # own docstring for this same precedent). The background-side
        # list-returning _proficiency_choices_from_5etools (not races'
        # trait-attaching _attach_choice_proficiencies, which needs a
        # traits list feats don't have) is the right fit here: a feat can
        # carry a skill choice AND a tool choice simultaneously (Prodigy/
        # XGE, confirmed real), so a flat list of envelopes is required,
        # exactly what that function already returns. One real, disclosed
        # gap: Weapon Master (PHB)'s weaponProficiencies uses a
        # "choose"/"fromFilter" filter-query DSL shape no existing choice
        # machinery models (see _WEAPON_ID_OVERRIDES' own comment for the
        # fixed-grant side of this same weapon-category divergence) — left
        # unconverted, not guessed at; see test_official_source.py's
        # Task 3 section docstring for the full reasoning.
        "proficiencies": _proficiencies_from_5etools(raw),
        "proficiency_choices": _proficiency_choices_from_5etools(raw),
        # Task 4: language grants — reuses the SAME background-side
        # _language_grants_from_5etools conversion machinery directly (see
        # that function's own docstring for the "any"/"anyStandard" key
        # variant this reuse required, and test_official_source.py's Task 4
        # section for the full real-data grounding, including the one
        # disclosed unrecognized-language gap, Harper Agent's "thieves'
        # cant").
        "languages": fixed_languages,
        "language_options": language_options,
        "resist": feat_resist,
        "immune": feat_immune,
        "condition_immune": _condition_immunities_from_5etools(raw),
        "senses": _senses_from_5etools(raw),
        "expertise_skills": _expertise_skills_from_5etools(raw),
        "saving_throw_proficiencies": _saving_throw_proficiencies_from_5etools(raw),
        "expertise_choices": _expertise_choices_from_5etools(raw),
        "saving_throw_choices": _saving_throw_choices_from_5etools(raw),
        # feat-additional-spells plan: fixed spell-name grants only (see
        # _feat_innate_spells_from_5etools).
        "innate_spells": feat_innate_spells,
        "spell_choices": feat_spell_choices,
        "spell_variants": feat_spell_variants,
    }


# Rune Shaper lists 14 runes but the rule is "know half your proficiency
# bonus" — a flat list would misrepresent it, so it is skipped.
_FEAT_SPELLS_SKIP = {"rune-shaper-bgg"}

# The feat's own text decides which spellcasting-ability rule applies, since
# the raw additionalSpells `ability` is often missing or a generic choose list.
_INHERIT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?\bis the ability increased by this feat", re.I)
_SAME_AS_FEAT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?chosen for your [^.]*?feat", re.I)


def _feat_spell_ability_override(raw: dict, index: str | None = None) -> str | dict | None:
    """Returns {"sameAsFeat": "<feat index>"} when the feat text says its
    spellcasting ability is the one chosen for another feat (and its
    prerequisites name exactly one feat), "inherit" when the text says it is
    the ability increased by this feat (and the feat has an ability
    increase), else None (no override)."""
    text = json.dumps(raw.get("entries") or [])
    if _SAME_AS_FEAT_ABILITY_RE.search(text):
        refs = [ref for prereq in (raw.get("prerequisite") or []) if isinstance(prereq, dict)
                for ref in (prereq.get("feat") or []) if isinstance(ref, str)]
        if len(refs) == 1:
            name, _, src = refs[0].partition("|")
            return {"sameAsFeat": f"{slug(name)}-{src.strip().lower()}"}
    if _INHERIT_ABILITY_RE.search(text) and raw.get("ability"):
        return "inherit"
    return None


def _feat_spell_uses_and_items(mechanism: str, level_value) -> list[tuple[str, list]]:
    """Feat-side counterpart of _innate_spell_uses_and_names (left
    untouched for races): returns (uses, items) pairs for ONE
    additionalSpells[mechanism][level_key] value. A plain list means
    at-will for innate/known and "prepared" for prepared; dict wrappers
    "will", "daily"/"rest" (every count key, including "1e") and "ritual"
    are recognised; anything else is skipped."""
    if isinstance(level_value, list):
        return [("prepared" if mechanism == "prepared" else "at-will", level_value)]
    out: list[tuple[str, list]] = []
    if isinstance(level_value, dict):
        for wrapper, value in level_value.items():
            if wrapper == "will" and isinstance(value, list):
                out.append(("at-will", value))
            elif wrapper in ("daily", "rest") and isinstance(value, dict):
                for items in value.values():
                    if isinstance(items, list):
                        out.append(("1/day", items))
            elif wrapper == "ritual" and isinstance(value, list):
                out.append(("ritual", value))
    return out


_SPELL_SCHOOL_CODES = {
    "A": "abjuration", "C": "conjuration", "D": "divination", "E": "enchantment",
    "V": "evocation", "I": "illusion", "N": "necromancy", "T": "transmutation",
}


def _parse_spell_filter(text: str) -> dict | None:
    """Parses a 5etools spell query ("level=1|school=E;D") into
    {"level": [int], "class": [lowercase], "school": [full lowercase
    names], "ritual": True}. Any unrecognised key (or malformed value)
    makes the whole filter unusable -> None."""
    result: dict = {}
    for part in text.split("|"):
        if "=" not in part:
            return None
        key, value = part.split("=", 1)
        key = key.strip().lower()
        values = [v.strip().lower() for v in value.split(";") if v.strip()]
        if key == "level":
            try:
                result["level"] = [int(v) for v in values]
            except ValueError:
                return None
        elif key == "class":
            result["class"] = values
        elif key == "school":
            schools = [_SPELL_SCHOOL_CODES.get(v.upper()) for v in values]
            if not schools or None in schools:
                return None
            result["school"] = schools
        elif key == "components & miscellaneous":
            if "ritual" not in values:
                return None
            result["ritual"] = True
        else:
            return None
    return result or None


def _feat_spells_from_5etools(raw: dict, index: str) -> tuple[list[dict], list[dict], list[str]]:
    """Converts a feat's additionalSpells into (innate_spells,
    spell_choices, spell_variants). innate_spells: race-shaped entries for
    fixed spell names (string items) under innate/known/prepared with
    level key "_" or a character-level digit. spell_choices: one entry
    per {"choose": ...} item: {variant, level, uses, ability, count,
    filter, from} — a query string becomes `filter`, a
    {"from": [names], "count": n} dict becomes `from` (slugs). Multi-entry
    feats whose entries ALL carry a "name" are mutually exclusive variants
    (Magic Initiate's spell lists...): every grant/choice is tagged with
    its entry name and spell_variants lists the names. A multi-entry feat
    without names (Cold Caster) keeps only its first entry (disclosed).
    Skipped: `expanded`, slot-level "sN" keys, unparseable filters, and
    the _FEAT_SPELLS_SKIP feats."""
    if index in _FEAT_SPELLS_SKIP:
        return [], [], []
    entries = [e for e in (raw.get("additionalSpells") or []) if isinstance(e, dict)]
    variants: list[str] = []
    if len(entries) > 1:
        if all(isinstance(e.get("name"), str) for e in entries):
            variants = [e["name"] for e in entries]
        else:
            entries = entries[:1]
    results: list[dict] = []
    choices: list[dict] = []
    folded: dict[tuple, dict] = {}
    override = _feat_spell_ability_override(raw, index)
    for entry in entries:
        variant = entry["name"] if variants else None
        ability = "inherit" if entry.get("ability") == "inherit" else _innate_spell_ability(entry.get("ability"))
        if isinstance(override, dict):
            ability = override
        elif override == "inherit" and (ability is None or isinstance(ability, dict)):
            ability = "inherit"
        for mechanism in ("innate", "known", "prepared"):
            block = entry.get(mechanism)
            if not isinstance(block, dict):
                continue
            for key, level_value in block.items():
                if key == "_":
                    level = None
                elif key.isdigit():
                    level = int(key)
                else:
                    continue
                for uses, items in _feat_spell_uses_and_items(mechanism, level_value):
                    for item in items:
                        if isinstance(item, dict) and "choose" in item:
                            spec = item["choose"]
                            base = {"variant": variant, "level": level, "uses": uses, "ability": ability}
                            if isinstance(spec, str):
                                parsed = _parse_spell_filter(spec)
                                if parsed is None:
                                    pass
                                elif mechanism == "prepared" and key.isdigit():
                                    # Level-scaled picks (Ritual Caster XPHB: keys 1/5/9/13/17)
                                    # fold into ONE choice whose count grows with level.
                                    fold_key = (variant, uses, repr(parsed))
                                    if fold_key in folded:
                                        folded[fold_key]["count_by_level"][key] = item.get("count", 1)
                                    else:
                                        folded[fold_key] = {
                                            **base, "level": None, "count": item.get("count", 1),
                                            "filter": parsed, "from": None,
                                            "count_by_level": {key: item.get("count", 1)},
                                        }
                                        choices.append(folded[fold_key])
                                else:
                                    choices.append({**base, "count": item.get("count", 1), "filter": parsed, "from": None})
                            elif isinstance(spec, dict) and isinstance(spec.get("from"), list):
                                names = [slug(_clean_innate_spell_name(n)) for n in spec["from"] if isinstance(n, str)]
                                choices.append({**base, "count": spec.get("count", 1), "filter": None, "from": names})
                            continue
                        if not isinstance(item, str):
                            continue
                        clean = _clean_innate_spell_name(item)
                        if not clean:
                            continue
                        results.append({
                            "name": clean.title(), "spell_id": slug(clean), "level": level,
                            "uses": uses, "ability": ability, "variant": variant,
                        })
    return results, choices, variants


def _feat_variant_hints_from_5etools(raw: dict) -> dict[str, str]:
    """A background grant like "magic initiate; cleric|xphb" names a
    spell-list-restricted variant. Returns {feat ref: "<Name> Spells"}
    (e.g. {"magic-initiate-xphb": "Cleric Spells"}) for those grants."""
    hints: dict[str, str] = {}
    for entry in raw.get("feats") or []:
        for feat_key, granted in entry.items():
            if granted is not True:
                continue
            name_part, _, source_part = feat_key.partition("|")
            base, sep, variant = name_part.partition(";")
            if not sep or not variant.strip() or not source_part.strip():
                continue
            hints[f"{slug(base.strip())}-{source_part.strip().lower()}"] = f"{variant.strip().title()} Spells"
    return hints


def _expertise_skills_from_5etools(raw: dict) -> list[str]:
    """Converts feats.json's `expertise` field — a list of single-key
    dicts, either {"<skill>": True} (a FIXED grant) or
    {"anyProficientSkill": N} (a CHOICE of N already-proficient skills to
    gain expertise in) — into a plain list of skill ids, `skill-{slug}`
    (the SAME id shape _proficiencies_from_5etools already produces for
    sheet.proficiencies.skills, so sheet.expertiseSkills entries line up
    with them 1:1, and both can be rendered/compared the same way).

    Only `is True` fixed entries convert; the anyProficientSkill choice
    portion has no choice mechanism to resolve against today and is
    silently excluded here — the same "pure data pass-through, no choice
    resolution" scope line _ability_bonuses_from_5etools already draws
    for its own choose-N sibling field (ability_bonus_options). Feats
    themselves ARE fully player-selectable as of the ASI-or-feat plan
    (2026-09-28+) — via a background's fixed/chosen `feats` grant (see
    engine.resolve._resolve_granted_feats) AND via free selection of any
    of the 94 General feats at a class level that grants an Ability Score
    Improvement (see engine.resolve._resolve_asi_selected_feats) — this
    docstring previously said no feat-selection UI existed at all, which
    predates that plan and is now stale; only the anyProficientSkill
    CHOICE within an already-selected feat is unconverted, not feat
    selection itself.

    The anyProficientSkill CHOICE portion is converted separately by
    _expertise_choices_from_5etools (closes the Skill Expert gap the
    ASI-or-feat final review disclosed).

    Confirmed against the real fetched feats.json (2026-09-28): 7 real
    records carry this field (Aberrant Anatomy/RHW, Boon of Skill/XPHB,
    Boon of Terror/FRHoF, Echoing Soul/RHW, Prodigy/XGE, Skill Expert/TCE,
    Skill Expert/XPHB) — only 2 (Aberrant Anatomy: perception; Boon of
    Terror: intimidation) are fixed; the other 5 are exclusively
    anyProficientSkill and contribute nothing here."""
    skills = []
    for entry in raw.get("expertise") or []:
        for key, val in entry.items():
            if val is True:
                skills.append(f"skill-{slug(key)}")
    return skills


def _expertise_choices_from_5etools(raw: dict) -> list[dict]:
    """The CHOICE portion of feats.json's `expertise` field —
    `{"anyProficientSkill": N}` — as a `proficiency_choices`-style envelope
    ({"choose": N, "from": {"option_set_type": "any_skill"}}) that
    engine.resolve._feat_choice_templates turns into a real, selectable
    Choice. Closes the gap _expertise_skills_from_5etools' docstring
    discloses (Skill Expert, Prodigy, Boon of Skill, Echoing Soul).

    The options here are every skill; they are gated to proficient skills
    by engine.resolve._gate_expertise_choices."""
    envelopes = []
    for entry in raw.get("expertise") or []:
        n = entry.get("anyProficientSkill")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            envelopes.append({"choose": n, "type": "proficiencies", "from": {"option_set_type": "any_skill"}})
    return envelopes


def _saving_throw_choices_from_5etools(raw: dict) -> list[dict]:
    """The CHOICE portion of feats.json's `savingThrowProficiencies` field —
    `{"choose": {"from": ["str", ...], "count"?: N}}` (Resilient/PHB and
    /XPHB) — as an options_array envelope whose option ids are the bare
    lowercase ability keys; engine.resolve uppercases a selection before
    merging it into the saving-throw proficiency list."""
    envelopes = []
    for entry in raw.get("savingThrowProficiencies") or []:
        choose = entry.get("choose")
        if not isinstance(choose, dict):
            continue
        options = [
            {"option_type": "reference", "item": {"index": k, "name": SAVE_ABILITY_NAMES[k], "url": ""}}
            for k in choose.get("from", [])
            if k in SAVE_ABILITY_NAMES
        ]
        if options:
            envelopes.append({
                "choose": choose.get("count", 1),
                "type": "proficiencies",
                "from": {"option_set_type": "options_array", "options": options},
            })
    return envelopes


SAVE_ABILITY_NAMES = {
    "str": "Strength", "dex": "Dexterity", "con": "Constitution",
    "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma",
}


def _saving_throw_proficiencies_from_5etools(raw: dict) -> list[str]:
    """Converts feats.json's `savingThrowProficiencies` field into a plain
    list of ability ids ("STR", "DEX", ...) for a FIXED grant — only an
    `is True` ability-keyed entry counts; a `{"choose": {"from": [...]}}`
    entry (a CHOICE of which ability gains the proficiency) is out of
    scope, the same reasoning _expertise_skills_from_5etools' own
    anyProficientSkill exclusion uses just above.

    The choice-shaped portion (Resilient) is converted separately by
    _saving_throw_choices_from_5etools (closes the gap the ASI-or-feat
    final review disclosed).

    Confirmed against the real fetched feats.json (2026-09-28): only 2
    real records carry this field at all (Resilient/PHB, Resilient/XPHB),
    and BOTH are exclusively choice-shaped (`[{"choose": {"from": ["str",
    ... ]}}]` — pick one of six) with no fixed entry at all. This
    function's fixed-only conversion therefore returns [] for every real
    feat today — mirrors _background_ability_bonuses' own "always {}
    today, kept for symmetry and to make the merge point explicit"
    precedent: the conversion is implemented generally (not narrowly
    special-cased to today's all-choice reality) so a future sourcebook
    feat that DOES carry a fixed saving-throw grant is picked up without
    any further code change here."""
    throws = []
    for entry in raw.get("savingThrowProficiencies") or []:
        for key, val in entry.items():
            if val is True and key in _ABILITY_KEYS:
                throws.append(key.upper())
    return throws


def _feat_ability_bonus_options_from_5etools(ability_list: list[dict]) -> dict | None:
    """Feat-side counterpart to _ability_bonus_options_from_5etools (races)
    — reuses the SAME output envelope shape, but with a small necessary
    variant on which "choose" entries it accepts, grounded against the
    real fetched feats.json (2026-09-28, Task 2):

    - Entries marked "hidden": true are skipped entirely. The only real
      case is "Ability Score Improvement" itself, which carries TWO such
      entries (one "amount": 2, one "count": 2) — both describing the
      EXISTING class-level ASI mechanic, not a feat-granted bonus; wiring
      that connection is explicitly out of scope for this slice (design
      spec).
    - Both "amount" and "count" are accepted as the count key (unlike
      races' _ability_bonus_options_from_5etools, which only accepts
      "count" — races' one real "amount" case, Custom Lineage, is
      genuinely ambiguous at amount=2, between +2-to-one and +1-to-two).
      For feats, once hidden entries are excluded, every surviving
      amount/count value in the real data is 1 — no live ambiguity to
      guess at, confirmed exhaustively.
    - A missing amount/count key (common on Epic Boon feats, which only
      carry "from" plus a separate top-level "max" score cap this simple
      envelope doesn't model) defaults to 1 — "pick one ability from this
      list, +1" — matching every such real entry's actual text."""
    for entry in ability_list or []:
        if entry.get("hidden"):
            continue
        choose = entry.get("choose")
        if not isinstance(choose, dict):
            continue
        from_list = choose.get("from", [])
        if not from_list:
            continue
        count = choose.get("amount", choose.get("count", 1))
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": 1}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    return None


def load_official_feats(official_dir: Path) -> list[dict]:
    feats_path = official_dir / "feats.json"
    if not feats_path.exists():
        return []
    with open(feats_path, encoding="utf-8") as f:
        data = json.load(f)
    feats = []
    for raw in data.get("feat", []):
        converted = _feat_from_5etools(raw)
        if converted is not None:
            feats.append(converted)
    return feats
