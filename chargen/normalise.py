"""Convert vendor JSON into the shared chargen.model schema.

Two vendors, kept deliberately separate — never interleaved in one function:

- 5e-bits (2014 ruleset): real files under chargen/data/srd/*.json, synced by
  chargen/sync.py. Uses `{"index","name","url"}` reference objects.
  Functions: `*_from_5ebits`.
- 5etools (official, mixed 2014+2024 editions): real files under
  `chargen.sources.official_dir()` (outside the repo, never committed),
  fetched by `python3 -m chargen.sync --official` and merged into the
  catalog when present. NOT fetched here (Global Constraint: no network at
  runtime). Uses `{@tag visible text|extra}` inline markup strings and
  different key names entirely. Functions: `*_from_5etools`. Exercised both
  against inline fixture dicts in tests/test_chargen_normalise.py and
  against the real omnibus files on disk.

A record missing a field the schema expects yields None (or the field's
declared empty collection) — never a fabricated value.
"""

import re

from chargen.model import (
    AbilityChoice,
    Background,
    CharClass,
    ClassLevelRow,
    ItemRef,
    Race,
    Spell,
    Subrace,
    Trait,
    Weapon,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _title(text: str) -> str:
    """Title-case that survives apostrophes: str.title() turns "healer's kit"
    into "Healer'S Kit", which is what the vendor's lowercase item keys would
    otherwise render as on a character sheet."""
    return re.sub(r"(^|[\s(/])([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


# 5etools inline markup: {@tagname visible text|extra|extra}. Keep only the
# "visible text" segment (the tag's own name and everything after the first
# `|` are discarded). Plain prose with no tags passes through unchanged.
_TAG_RE = re.compile(r"\{@(\w+)\s+([^{}]*?)\}")


def _strip_5etools_tags(text: str) -> str:
    def _replace(match: re.Match) -> str:
        body = match.group(2)
        return body.split("|", 1)[0]

    return _TAG_RE.sub(_replace, text)


# ===========================================================================
# 5e-bits (2014)
# ===========================================================================


def _ability_bonuses_from_5ebits(entries: list[dict]) -> dict[str, int]:
    """entries: [{"ability_score": {"name": "CON", ...}, "bonus": 2}, ...]"""
    return {e["ability_score"]["name"]: e["bonus"] for e in entries or []}


def _resolve_trait_5ebits(ref: dict, traits_by_index: dict[str, dict]) -> Trait:
    """ref: {"index","name","url"} — resolve the real description text from
    the separate Traits.json file (races/subraces only carry refs)."""
    full = traits_by_index.get(ref["index"])
    text = "\n\n".join(full.get("desc", [])) if full else ""
    return Trait(name=ref["name"], text=text)


def race_from_5ebits(
    raw: dict,
    traits_by_index: dict[str, dict],
    subraces: list[Subrace] | None = None,
) -> Race:
    ability_bonuses = _ability_bonuses_from_5ebits(raw.get("ability_bonuses", []))

    ability_choice = None
    options = raw.get("ability_bonus_options")
    if options:
        first_bonus = options["from"]["options"][0]["bonus"]
        ability_choice = {"count": options["choose"], "amount": first_bonus}

    traits = [_resolve_trait_5ebits(t, traits_by_index) for t in raw.get("traits", [])]
    languages = [lang["name"] for lang in raw.get("languages", [])]

    own_subraces = [s for s in (subraces or []) if s.parent_race_id == raw["index"]]

    return Race(
        id=raw["index"],
        name=raw["name"],
        source="5e-SRD",
        ruleset="2014",
        size=raw.get("size"),
        speed=raw.get("speed"),
        ability_bonuses=ability_bonuses,
        ability_choice=ability_choice,
        traits=traits,
        subraces=own_subraces,
        languages=languages,
    )


def subrace_from_5ebits(raw: dict, traits_by_index: dict[str, dict]) -> Subrace:
    ability_bonuses = _ability_bonuses_from_5ebits(raw.get("ability_bonuses", []))
    traits = [_resolve_trait_5ebits(t, traits_by_index) for t in raw.get("racial_traits", [])]
    return Subrace(
        id=raw["index"],
        # 2014 subrace records already carry the full display name
        # ("Hill Dwarf") — unlike 5etools, there is nothing to compose.
        name=raw["name"],
        source="5e-SRD",
        ruleset="2014",
        parent_race_id=raw["race"]["index"],
        ability_bonuses=ability_bonuses,
        traits=traits,
    )


_SKILL_PREFIX = "Skill: "
_TOOL_PREFIX = "Tool: "


def _split_background_proficiencies(raw_profs: list[dict]) -> tuple[list[str], list[str]]:
    skills, tools = [], []
    for p in raw_profs or []:
        name = p["name"]
        if name.startswith(_SKILL_PREFIX):
            skills.append(name[len(_SKILL_PREFIX) :])
        elif name.startswith(_TOOL_PREFIX):
            tools.append(name[len(_TOOL_PREFIX) :])
        elif any(w in name.lower() for w in ("tool", "kit", "supplies", "instrument")):
            tools.append(name)
        # else: armor/weapon proficiencies essentially never show up on a
        # background in the SRD; silently drop rather than misclassify.
    return skills, tools


def background_from_5ebits(raw: dict) -> Background:
    skill_profs, tool_profs = _split_background_proficiencies(raw.get("starting_proficiencies", []))

    if "language_options" in raw:
        languages: int | list[str] = raw["language_options"].get("choose", 0)
    else:
        languages = []

    starting_equipment = [
        ItemRef(
            id=e["equipment"]["index"],
            name=e["equipment"]["name"],
            quantity=e.get("quantity", 1),
        )
        for e in raw.get("starting_equipment", [])
    ]

    feature_raw = raw.get("feature")
    feature = (
        Trait(name=feature_raw["name"], text="\n\n".join(feature_raw.get("desc", [])))
        if feature_raw
        else None
    )

    return Background(
        id=raw["index"],
        name=raw["name"],
        source="5e-SRD",
        ruleset="2014",
        skill_proficiencies=skill_profs,
        tool_proficiencies=tool_profs,
        languages=languages,
        starting_equipment=starting_equipment,
        feature=feature,
        origin_feat=None,  # 2014 backgrounds never carry an origin feat
        ability_choice=[],  # 2014 backgrounds never carry ability choices
    )


_SPELL_SLOT_LEVELS = range(1, 10)


def class_level_row_from_5ebits(raw: dict) -> ClassLevelRow:
    spellcasting = raw.get("spellcasting") or {}

    # Convention: a spell-slot level with 0 slots is dropped from the dict
    # entirely, rather than kept as {level: 0}. Pinned by
    # test_wizard_level_5_row_2014_real_file.
    spell_slots = {
        lvl: spellcasting[f"spell_slots_level_{lvl}"]
        for lvl in _SPELL_SLOT_LEVELS
        if spellcasting.get(f"spell_slots_level_{lvl}", 0) > 0
    }
    cantrips_known = spellcasting.get("cantrips_known")

    features = [f["name"] for f in raw.get("features", [])]
    extras = dict(raw.get("class_specific", {}))

    return ClassLevelRow(
        level=raw["level"],
        proficiency_bonus=raw["prof_bonus"],
        features=features,
        spell_slots=spell_slots,
        cantrips_known=cantrips_known,
        extras=extras,
    )


def _classify_class_proficiency(name: str) -> str | None:
    lname = name.lower()
    if "saving throw" in lname:
        return None  # captured separately via raw["saving_throws"]
    if "armor" in lname or "shield" in lname:
        return "armor"
    if "weapon" in lname:
        return "weapons"
    return "tools"


def class_level_rows_from_5ebits(levels_raw: list[dict], class_index: str) -> list[ClassLevelRow]:
    """Filter chargen's Levels.json down to one class's 20 main level rows.

    The file also carries SUBCLASS level rows under the same class index and
    level number (e.g. Fighter/Champion features at level 3) — those carry a
    "subclass" key and lack "prof_bonus"/"class_specific" entirely. They are
    a different record shape, not a missing-field case, so they're excluded
    here rather than fed through class_level_row_from_5ebits."""
    return [
        class_level_row_from_5ebits(r)
        for r in levels_raw
        if r["class"]["index"] == class_index and "subclass" not in r
    ]


def class_from_5ebits(raw: dict, levels: list[ClassLevelRow]) -> CharClass:
    armor, weapons, tools = [], [], []
    for p in raw.get("proficiencies", []):
        bucket = _classify_class_proficiency(p["name"])
        if bucket == "armor":
            armor.append(p["name"])
        elif bucket == "weapons":
            weapons.append(p["name"])
        elif bucket == "tools":
            tools.append(p["name"])

    saving_throws = [s["name"] for s in raw.get("saving_throws", [])]

    skill_choice = None
    proficiency_choices = raw.get("proficiency_choices") or []
    if proficiency_choices:
        pc = proficiency_choices[0]
        pc_options = []
        for opt in pc.get("from", {}).get("options", []):
            item_name = opt.get("item", {}).get("name", "")
            if item_name.startswith(_SKILL_PREFIX):
                item_name = item_name[len(_SKILL_PREFIX) :]
            pc_options.append(item_name)
        skill_choice = {"count": pc.get("choose"), "options": pc_options}

    return CharClass(
        id=raw["index"],
        name=raw["name"],
        source="5e-SRD",
        ruleset="2014",
        hit_die=raw["hit_die"],
        armor=armor,
        weapons=weapons,
        tools=tools,
        saving_throws=saving_throws,
        skill_choice=skill_choice,
        levels=levels,
    )


def spell_from_5ebits(raw: dict) -> Spell:
    component_letters = raw.get("components", [])
    components = {
        "v": "V" in component_letters,
        "s": "S" in component_letters,
        "m": raw.get("material") if "M" in component_letters else False,
    }

    dc = raw.get("dc")
    save = dc["dc_type"]["name"] if dc else None

    return Spell(
        id=raw["index"],
        name=raw["name"],
        level=raw["level"],
        school=raw["school"]["name"],
        casting_time=raw["casting_time"],
        range=raw["range"],
        duration=raw["duration"],
        components=components,
        concentration=raw["concentration"],
        ritual=raw["ritual"],
        classes=[c["name"] for c in raw.get("classes", [])],
        subclasses=[c["name"] for c in raw.get("subclasses", [])],
        description="\n\n".join(raw.get("desc", [])),
        higher_level="\n\n".join(raw.get("higher_level", [])),
        damage=raw.get("damage"),
        save=save,
    )


def weapon_from_5ebits(raw: dict) -> Weapon:
    damage = raw.get("damage") or {}
    two_handed = raw.get("two_handed_damage") or {}
    cost = raw.get("cost")
    return Weapon(
        id=raw["index"],
        name=raw["name"],
        source="5e-SRD",
        category=raw.get("weapon_category"),
        damage_dice=damage.get("damage_dice"),
        damage_type=(damage.get("damage_type") or {}).get("name"),
        versatile_damage_dice=two_handed.get("damage_dice"),
        properties=[p["name"] for p in raw.get("properties", [])],
        weight=raw.get("weight"),
        cost=f"{cost['quantity']} {cost['unit']}" if cost else None,
    )


# ===========================================================================
# 5etools (2024/official) — real files fetched by chargen/sync.py --official
# into chargen.sources.official_dir(), read and merged by
# chargen/catalog.py's _merge_official(). Originally fixture-tested only;
# Task 10 verified these functions against the real races.json/backgrounds.json
# omnibus (160 races / 98 subraces / 161 backgrounds across every sourcebook
# and edition) and fixed several bugs real data exposed that small synthetic
# fixtures never would have (see the three helpers below and their callers).
# ===========================================================================


def _ruleset_from_5etools(raw: dict) -> str:
    """The omnibus races.json/backgrounds.json files mix every sourcebook and
    edition in one file — only records with edition == "one" are genuinely
    2024-ruleset content (confirmed against real data: such records carry
    zero race ability bonuses and the weighted background ability-choice
    shape, exactly Global Finding 1's pattern). A missing/absent "edition"
    key means pre-2024 (2014-ruleset) content. Do NOT hardcode "2024" here —
    that would silently mislabel ~90% of the real omnibus (only 10/160 races
    and 16/161 backgrounds are actually XPHB)."""
    return "2024" if raw.get("edition") == "one" else "2014"


def _qualified_id_5etools(name: str, source: str) -> str:
    """Source-qualify every official id: bare _slug(name) collides both
    within the omnibus file (37 duplicate race names, 13 duplicate
    background names — e.g. "Dwarf" from PHB vs "Dwarf" from XPHB are two
    distinct records) and against the SRD baseline already in the catalog
    (dwarf/elf/halfling/human/dragonborn/gnome/half-elf/half-orc/tiefling/
    acolyte are all already unqualified SRD ids). Qualifying makes the merge
    additive instead of silently overwriting via key collision."""
    return f"{_slug(name)}-{_slug(source or '')}"


def _entries_to_traits_5etools(entries: list) -> list[Trait]:
    """Walk a 5etools 'entries' array, turning each dict entry that carries a
    'name' key into one Trait, with markup stripped from its text. Bare
    strings in the array (flavor text with no heading) are not traits."""
    traits = []
    for entry in entries or []:
        if isinstance(entry, dict) and "name" in entry:
            lines = [
                _strip_5etools_tags(line) if isinstance(line, str) else str(line)
                for line in entry.get("entries", [])
            ]
            traits.append(Trait(name=entry["name"], text="\n\n".join(lines)))
    return traits


_SPEED_MODE_LABELS = {"fly": "Fly", "swim": "Swim", "climb": "Climb", "burrow": "Burrow"}


def _speed_from_5etools(raw_speed) -> tuple[int | None, Trait | None]:
    """Split 5etools' two speed shapes into the one `Race.speed` declares
    (an int) plus, when there is one, a trait carrying the modes that shape
    would otherwise lose.

    Real data carries speed either as a bare int (115 of the 144 non-_copy
    races) or as a dict of movement modes — `{"walk": 20, "fly": 50}`,
    `{"walk": 35, "climb": true}` — for the other 29. Everything downstream
    treats speed as a number: the sheet's `combat.speed`, the CLI's
    "30 ft", the builder's `${r.speed} ft`. A dict reaching those renders as
    "[object Object] ft". Take the walking speed as the number, and surface
    the other modes as one extra Trait rather than dropping them. A mode
    given as `true` instead of a number is 5etools' shorthand for "equal to
    your walking speed"."""
    if isinstance(raw_speed, dict):
        walk = raw_speed.get("walk")
        walk = walk if isinstance(walk, int) and not isinstance(walk, bool) else None
        extras = []
        for mode, value in raw_speed.items():
            if mode == "walk":
                continue
            label = _SPEED_MODE_LABELS.get(mode, _title(mode))
            if value is True:
                extras.append(f"{label} speed equal to your walking speed")
            elif isinstance(value, int) and not isinstance(value, bool):
                extras.append(f"{label} speed {value} ft.")
        trait = Trait(name="Speed", text=", ".join(extras)) if extras else None
        return walk, trait
    return raw_speed, None


def _language_names_from_5etools(groups: list) -> list[str]:
    """`Race.languages` is `list[str]` — names only, with no room for the
    "and one of your choice" counts `Background.languages` can also hold. 74
    of the 144 non-_copy official races name real languages here (Common on
    66 of them); those used to be dropped on the floor with a hardcoded [].
    """
    names = _languages_from_5etools(groups)
    return names if isinstance(names, list) else []


def race_from_5etools(raw: dict) -> Race | None:
    """Returns None for records that use 5etools' internal _copy/_mod
    inheritance mechanism instead of embedding their own data directly
    (16/160 real races) — e.g. {"name": "Amonkhet", "source": "PSA",
    "_copy": {"name": "Variant", "source": "PHB", "raceName": "Human", ...}}
    with no direct ability/entries of its own. Resolving _copy/_mod
    generically is a real JSON-patch engine and disproportionate here; this
    is a disclosed, deliberate cut, not an oversight — see races_from_5etools.
    """
    if "_copy" in raw:
        return None

    # 2024 races carry no "ability" key at all (Global Finding 1) — treat a
    # missing key as "grants nothing", not a parse error.
    ability_field = raw.get("ability")
    ability_bonuses: dict[str, int] = {}
    if isinstance(ability_field, list) and ability_field:
        first = ability_field[0]
        ability_bonuses = {
            k.upper(): v for k, v in first.items() if k != "choose" and isinstance(v, int)
        }

    size_field = raw.get("size")
    size = size_field[0] if isinstance(size_field, list) and size_field else size_field

    traits = _entries_to_traits_5etools(raw.get("entries", []))

    speed, speed_trait = _speed_from_5etools(raw.get("speed"))
    # 4 of the 29 dict-speed races already spell their movement modes out in
    # a trait of their own literally named "Speed" ("...and you have a
    # swimming speed equal to your walking speed") — don't print it twice.
    if speed_trait is not None and not any(t.name == speed_trait.name for t in traits):
        traits.append(speed_trait)

    return Race(
        id=_qualified_id_5etools(raw["name"], raw.get("source", "")),
        name=raw["name"],
        source=raw.get("source", ""),
        ruleset=_ruleset_from_5etools(raw),
        size=size,
        speed=speed,
        ability_bonuses=ability_bonuses,
        # 2024 races don't carry a race-level ability CHOICE either — that
        # lives on the background (Global Finding 2). None, not a guess.
        ability_choice=None,
        traits=traits,
        # Empty by design at THIS layer: a 5etools race record does not
        # contain its subraces (they are separate records in the same file's
        # "subrace" array, linked back by raceName/raceSource). The parent
        # link is resolved once both lists exist —
        # `Catalog._attach_subraces()` fills this field in for every race,
        # SRD and official alike.
        subraces=[],
        languages=_language_names_from_5etools(raw.get("languageProficiencies", [])),
    )


def races_from_5etools(raws: list[dict]) -> list[Race]:
    result = []
    for raw in raws:
        race = race_from_5etools(raw)
        if race is not None:
            result.append(race)
    return result


def subrace_from_5etools(raw: dict) -> Subrace | None:
    """Returns None for the ~5% of 5etools subrace records with no 'name'
    key (the base variant), and for records using _copy/_mod inheritance
    (1/98 real subraces) — same disclosed cut as race_from_5etools. Callers
    must skip both, not emit a blank Subrace."""
    if "_copy" in raw:
        return None

    variant_name = raw.get("name")
    if not variant_name:
        return None

    race_name = raw.get("raceName", "")
    race_source = raw.get("raceSource", "")
    display_name = f"{variant_name} {race_name}".strip()

    ability_bonuses = {}
    for entry in raw.get("ability", []):
        for key, value in entry.items():
            if key == "choose":
                continue
            if isinstance(value, int):
                ability_bonuses[key.upper()] = value

    return Subrace(
        id=_qualified_id_5etools(display_name, raw.get("source", "")),
        name=display_name,
        # The subrace variant's OWN book (e.g. "EGW" for the Draconblood
        # dragonborn subrace), not the parent race's book (raceSource, e.g.
        # "PHB") — those are frequently different real books.
        source=raw.get("source", ""),
        ruleset=_ruleset_from_5etools(raw),
        # Qualify with the PARENT race's own source (raceSource), matching
        # the id race_from_5etools() produces for that same parent race —
        # not the subrace's own source, which is usually a different book.
        parent_race_id=_qualified_id_5etools(race_name, race_source),
        ability_bonuses=ability_bonuses,
        # Real subrace records carry the same "entries" array shape races
        # do, with real named trait content — wire them through the same
        # helper races already use, instead of hardcoding an empty list.
        traits=_entries_to_traits_5etools(raw.get("entries", [])),
    )


def subraces_from_5etools(raws: list[dict]) -> list[Subrace]:
    result = []
    for raw in raws:
        subrace = subrace_from_5etools(raw)
        if subrace is not None:
            result.append(subrace)
    return result


def _names_from_proficiency_group_5etools(group: dict) -> list[str]:
    """group: {"insight": True, "religion": True} -> ["Insight", "Religion"].
    camelCase keys (e.g. "cartographersTools") get a space before each
    interior capital, then title-cased: "Cartographers Tools"."""
    names = []
    for key, value in group.items():
        if value is not True:
            continue
        spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", key)
        names.append(spaced[:1].upper() + spaced[1:])
    return names


def _origin_feat_name_5etools(feats: list[dict]) -> str | None:
    """feats: [{"magic initiate; cleric|xphb": True}] — an odd shape where
    the feat's name+source is baked into the single dict key. Extract the
    name before the first '|', and turn a '; '-joined qualifier into a
    parenthetical: "magic initiate; cleric" -> "Magic Initiate (Cleric)"."""
    if not feats:
        return None
    first_entry = feats[0]
    raw_key = next(iter(first_entry.keys()), None)
    if not raw_key:
        return None
    raw_name = raw_key.split("|", 1)[0]
    if ";" in raw_name:
        main, _, qualifier = raw_name.partition(";")
        return f"{main.strip().title()} ({qualifier.strip().title()})"
    return raw_name.strip().title()


# -- background equipment / feature / languages (5etools) -------------------
# The three fields below were `[]`/`None` placeholders until the final fix
# wave; the shapes each parser handles were read off the real 161-record
# backgrounds.json omnibus before being written, and the coverage each one
# actually achieves is stated on it — including what it deliberately leaves
# empty and why.

_EQUIPMENT_ALWAYS_KEY = "_"

# The only three equipmentType values in the whole real file (14 + 13 + 10
# occurrences). They name a category the player picks one item from, not an
# item; these are 5e's own names for those categories. An unknown key falls
# back to its camelCase split rather than being dropped.
_EQUIPMENT_TYPE_NAMES_5ETOOLS = {
    "toolArtisan": "Artisan's tools (any one)",
    "setGaming": "Gaming set (any one)",
    "instrumentMusical": "Musical instrument (any one)",
}


def _coin_name_5etools(value: int) -> str:
    """5etools money is an integer count of COPPER pieces — Acolyte|XPHB's
    `{"value": 800}` is the "8 GP" its own prose names. Render the largest
    clean denomination; there is no currency field on ItemRef to put it in,
    and dropping it would lose a real part of the kit."""
    if value % 100 == 0:
        return f"{value // 100} gp"
    if value % 10 == 0:
        return f"{value // 10} sp"
    return f"{value} cp"


def _item_name_5etools(ref: str) -> str:
    """`"common clothes|phb"` -> `"Common Clothes"`. Everything from the
    first "|" on is the vendor's source tag, not part of the name."""
    return _title(ref.split("|", 1)[0].strip())


def _item_ref_from_5etools_equipment(entry) -> ItemRef | None:
    """One entry of a startingEquipment block -> one ItemRef.

    `id` is always None, deliberately: the ids in these records are 5etools
    item slugs ("holy symbol|phb"), which are NOT catalog ids — the only
    equipment ids this catalog can resolve are the SRD's 5e-bits indices
    ("holy-symbol"), and the two vocabularies do not line up record for
    record. A plausible-looking id nothing can look up is exactly the kind
    of fabrication this layer must not emit; the display name is real and
    is what every consumer of Background.starting_equipment actually shows.
    """
    if isinstance(entry, str):
        return ItemRef(id=None, name=_item_name_5etools(entry), quantity=1)
    if not isinstance(entry, dict):
        return None

    if "item" in entry:
        name = entry.get("displayName") or _item_name_5etools(entry["item"])
    elif "special" in entry:
        # Free prose the vendor wrote by hand ("Azorius insignia", "your
        # inheritance") — kept verbatim, only the first letter raised below.
        name = str(entry["special"]).strip()
    elif "equipmentType" in entry:
        kind = entry["equipmentType"]
        name = entry.get("displayName") or _EQUIPMENT_TYPE_NAMES_5ETOOLS.get(
            kind, _title(re.sub(r"(?<!^)(?=[A-Z])", " ", kind).lower()))
    elif "value" in entry:
        name = _coin_name_5etools(entry["value"])
    else:
        return None

    contains = entry.get("containsValue")
    if contains:
        name = f"{name} (containing {_coin_name_5etools(contains)})"
    worth = entry.get("worthValue")
    if worth:
        name = f"{name} (worth {_coin_name_5etools(worth)})"

    quantity = entry.get("quantity", 1)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        quantity = 1
    # Vendor `displayName`/`special` prose is written mid-sentence and so is
    # frequently lowercase ("hooded lantern made of wrought iron"); raise the
    # first letter only, leaving the rest of the author's wording alone.
    return ItemRef(id=None, name=name[:1].upper() + name[1:], quantity=quantity)


def _starting_equipment_from_5etools(blocks: list) -> list[ItemRef]:
    """`startingEquipment` is a list of blocks. A block is either
    `{"_": [...]}` — granted outright — or an either/or kit keyed by option
    letter (`{"a": [...], "b": [...]}`, `{"A": [...], "B": [...]}`).

    Only the "_" blocks are resolved. An either/or kit is a *player* choice
    and the Draft has no field recording which branch was taken, so
    materialising one branch here would be the engine deciding for the
    player — the same disclosed cut `Catalog.starting_equipment()` already
    documents for the SRD classes' choice-based
    `starting_equipment_options`.

    Coverage against the real file, counted before writing this: of the 135
    non-_copy backgrounds, 134 carry a `startingEquipment` array; 74 of
    those carry at least one "_" block and get real equipment here, and 60
    carry ONLY either/or blocks (nearly all of them 2024 "Choose A or B"
    records) and still come back empty. That remainder is disclosed, not
    silently dropped: it needs a Draft field for the choice, not a better
    parser.
    """
    out: list[ItemRef] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        for entry in block.get(_EQUIPMENT_ALWAYS_KEY) or []:
            item = _item_ref_from_5etools_equipment(entry)
            if item is not None:
                out.append(item)
    return out


_FEATURE_PREFIX_5ETOOLS = "Feature:"


def _feature_from_entries_5etools(entries: list) -> Trait | None:
    """The background's one 2014-era feature entry, or None.

    A record's `entries` array holds several named entries — the
    proficiency summary list, the feature, "Suggested Characteristics" and
    its d8 tables — so `_entries_to_traits_5etools()` (which turns *every*
    named entry into a Trait) is the wrong tool here: `Background.feature`
    is a single Trait, and the flavor tables are not it. The feature is
    marked two ways in the real data, and the two agree exactly across all
    135 non-_copy records (75 each, same records): `data.isFeature: true`,
    and a name literally prefixed "Feature: ". Both are accepted; the
    prefix is stripped so the Trait is named "Shelter of the Faithful",
    not "Feature: Shelter of the Faithful".

    The other 60 records are all `edition == "one"` (2024) and genuinely
    have no background feature — 2024 replaced it with the origin feat,
    which `origin_feat` already carries — so None there is the correct
    answer rather than a parse gap.
    """
    for entry in entries or []:
        if not isinstance(entry, dict) or "name" not in entry:
            continue
        name = str(entry["name"])
        flagged = bool((entry.get("data") or {}).get("isFeature"))
        if not flagged and not name.startswith(_FEATURE_PREFIX_5ETOOLS):
            continue
        if name.startswith(_FEATURE_PREFIX_5ETOOLS):
            name = name[len(_FEATURE_PREFIX_5ETOOLS):].strip()
        lines = [_strip_5etools_tags(line)
                 for line in entry.get("entries", []) if isinstance(line, str)]
        return Trait(name=name, text="\n\n".join(lines))
    return None


def _languages_from_5etools(groups: list) -> int | list[str]:
    """`languageProficiencies` -> the `int | list[str]` Background declares.

    The shapes in the real files: `{"anyStandard": 2}` (a count of free
    picks), `{"choose": {"from": [...]}}` (one pick from a short list),
    `{"other": true}` (also a free pick — "one language of your choice",
    which is a count, not a name) and `{"dwarvish": true}` (a named
    language).

    The field is a count OR names, never both, so a record granting both
    yields the names — the free pick it also grants is not representable
    here and is dropped rather than invented into a name.
    """
    named: list[str] = []
    free = 0
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if key == "choose":
                free += (value or {}).get("count", 1) if isinstance(value, dict) else 1
            elif key == "other" or key.startswith("any"):
                free += value if isinstance(value, int) and not isinstance(value, bool) else 1
            elif value is True:
                named.append(_title(key))
    if named:
        return named
    return free if free else []


def background_from_5etools(raw: dict) -> Background | None:
    """Returns None for _copy/_mod-based records (26/161 real backgrounds) —
    same disclosed cut as race_from_5etools/subrace_from_5etools."""
    if "_copy" in raw:
        return None

    skill_profs = []
    for group in raw.get("skillProficiencies", []):
        skill_profs.extend(_names_from_proficiency_group_5etools(group))

    tool_profs = []
    for group in raw.get("toolProficiencies", []):
        tool_profs.extend(_names_from_proficiency_group_5etools(group))

    ability_choice = []
    for entry in raw.get("ability", []):
        weighted = (entry.get("choose") or {}).get("weighted")
        if weighted:
            ability_choice.append(
                AbilityChoice(
                    options=[a.upper() for a in weighted.get("from", [])],
                    weights=list(weighted.get("weights", [])),
                )
            )

    origin_feat = _origin_feat_name_5etools(raw.get("feats", []))

    return Background(
        id=_qualified_id_5etools(raw["name"], raw.get("source", "")),
        name=raw["name"],
        source=raw.get("source", ""),
        ruleset=_ruleset_from_5etools(raw),
        skill_proficiencies=skill_profs,
        tool_proficiencies=tool_profs,
        languages=_languages_from_5etools(raw.get("languageProficiencies", [])),
        starting_equipment=_starting_equipment_from_5etools(
            raw.get("startingEquipment", [])),
        feature=_feature_from_entries_5etools(raw.get("entries", [])),
        origin_feat=origin_feat,
        ability_choice=ability_choice,
    )


def backgrounds_from_5etools(raws: list[dict]) -> list[Background]:
    result = []
    for raw in raws:
        background = background_from_5etools(raw)
        if background is not None:
            result.append(background)
    return result
