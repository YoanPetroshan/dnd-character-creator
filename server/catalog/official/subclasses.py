"""5etools class files -> SRD-shaped subclass records (Slice 11b).

`class/index.json` maps a class id to a file; each file is
{"class": [...], "subclass": [...], "subclassFeature": [...]}. Only the
`subclass` and `subclassFeature` arrays are read here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_raw_class_data(class_dir) -> tuple[list[dict], list[dict]]:
    """(raw subclasses, raw subclass features) of every file named in
    `class_dir/index.json`, in index order. ([], []) when the directory or
    index is missing; a file that is missing or not valid JSON is skipped."""
    if not class_dir:
        return [], []
    class_dir = Path(class_dir)
    index = _read_json(class_dir / "index.json")
    if not isinstance(index, dict):
        return [], []
    subclasses: list[dict] = []
    features: list[dict] = []
    for filename in index.values():
        if not isinstance(filename, str):
            continue
        data = _read_json(class_dir / filename)
        if isinstance(data, dict):
            subclasses.extend(s for s in data.get("subclass", []) if isinstance(s, dict))
            features.extend(f for f in data.get("subclassFeature", []) if isinstance(f, dict))
    return subclasses, features


def load_class_2024_progressions(class_dir) -> dict[str, dict]:
    """XPHB class records -> {class id: {"caster": casterProgression,
    "cantrips": [20 ints] or [], "prepared": [20 ints]}} for the 2024 spell
    counts (cantripProgression / preparedSpellsProgression), read from the
    same class files as the subclasses. Only SRD-class XPHB records that carry
    a `casterProgression` and a 20-entry prepared table; {} when the directory
    or index is missing."""
    if not class_dir:
        return {}
    class_dir = Path(class_dir)
    index = _read_json(class_dir / "index.json")
    if not isinstance(index, dict):
        return {}
    out: dict[str, dict] = {}
    for filename in index.values():
        data = _read_json(class_dir / filename) if isinstance(filename, str) else None
        for raw in (data.get("class", []) if isinstance(data, dict) else []):
            if not isinstance(raw, dict) or raw.get("source") != "XPHB":
                continue
            cls_id = str(raw.get("name", "")).lower()
            prepared, cantrips = raw.get("preparedSpellsProgression"), raw.get("cantripProgression") or []
            if (cls_id in SRD_CLASS_IDS and raw.get("casterProgression")
                    and isinstance(prepared, list) and len(prepared) == 20
                    and all(isinstance(n, int) for n in prepared)):
                out[cls_id] = {"caster": raw["casterProgression"],
                               "cantrips": list(cantrips) if len(cantrips) == 20 else [],
                               "prepared": list(prepared)}
    return out


_TAG = re.compile(r"\{@(?:filter|tip) ([^|}]*)[^}]*\}")
_DICE_TAG = re.compile(r"\{@dice ([^|}]*)[^}]*\}")


def _column_slug(label) -> str | None:
    """A table column label -> slug ('{@filter Invocations|optionalfeatures|...}'
    -> 'invocations'); None for the spell columns (`|spells|` filters, 'Spell
    Slots', 'Slot Level') that the spell machinery already reads."""
    if not isinstance(label, str) or "|spells|" in label:
        return None
    text = _TAG.sub(r"\1", label).strip()
    if text.lower() in ("spell slots", "slot level", ""):
        return None
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or None


def _table_value(value):
    """One table cell -> int / 'NdF' / 'dF' / the text itself."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = _DICE_TAG.sub(lambda m: m.group(1).strip().lower(), value).strip()
        return int(text) if re.fullmatch(r"-?\d+", text) else text
    if isinstance(value, dict):
        if value.get("type") in ("bonus", "bonusSpeed"):
            return value.get("value", 0)
        if value.get("type") == "dice":
            rolls = value.get("toRoll") or []
            if rolls:
                return "+".join(f"{r.get('number', 1)}d{r['faces']}" for r in rolls)
    return None


def _table_columns(groups) -> dict[str, list]:
    """classTableGroups / subclassTableGroups -> {column slug: [20 values]};
    spell-progression groups and spell columns are skipped, the first column
    with a given slug wins."""
    out: dict[str, list] = {}
    for group in groups or []:
        rows = group.get("rows") if isinstance(group, dict) else None
        if not isinstance(rows, list) or len(rows) != 20:
            continue
        for i, label in enumerate(group.get("colLabels") or []):
            slug_ = _column_slug(label)
            if slug_ is None or slug_ in out:
                continue
            values = [_table_value(r[i]) if isinstance(r, list) and i < len(r) else None for r in rows]
            if all(v is not None for v in values):
                out[slug_] = values
    return out


def load_class_2024_tables(class_dir) -> dict[str, dict[str, list]]:
    """XPHB class records -> {class id: {column slug: [20 values]}} for the
    non-spell columns of the class table (Rages, Rage Damage, Sneak Attack,
    Weapon Mastery, Channel Divinity, ...). Values are ints, 'NdF' dice
    strings or text; {} when the directory or index is missing."""
    out: dict[str, dict[str, list]] = {}
    for raw in _raw_class_records(class_dir, "class"):
        if raw.get("source") == "XPHB":
            cols = _table_columns(raw.get("classTableGroups"))
            if cols:
                out[str(raw.get("name", "")).lower()] = cols
    return out


def load_subclass_2024_tables(class_dir) -> dict[str, dict[str, list]]:
    """Subclass records with their own `subclassTableGroups` (Psi Warrior,
    Soulknife XPHB) -> {subclass id: {column slug: [20 values]}}; the spell
    tables of the third casters are skipped."""
    out: dict[str, dict[str, list]] = {}
    for raw in _raw_class_records(class_dir, "subclass"):
        if "_copy" in raw or raw.get("source") != "XPHB" or not raw.get("name"):
            continue
        cols = _table_columns(raw.get("subclassTableGroups"))
        if cols:
            out[_sub_id(raw)] = cols
    return out


def load_class_2024_records(class_dir) -> dict[str, dict]:
    """XPHB class records of the 12 SRD classes -> {class id: {"feat_progression":
    raw featProgression list, "features": [{"name", "level", "ref"}] (the
    `classFeatures` refs in order, placeholders included), "starting_proficiencies",
    "multiclassing", "starting_equipment": the raw 5etools values, plus C9a's "saving_throws" (the
    raw `proficiency` list) and "primary_ability" (the raw `primaryAbility` list)}} (C1, data only).
    {} when the directory or index is missing."""
    out: dict[str, dict] = {}
    for raw in _raw_class_records(class_dir, "class"):
        cls_id = str(raw.get("name", "")).lower()
        if raw.get("source") != "XPHB" or cls_id not in SRD_CLASS_IDS:
            continue
        features = []
        for entry in raw.get("classFeatures") or []:
            ref = entry.get("classFeature") if isinstance(entry, dict) else entry
            parts = ref.split("|") if isinstance(ref, str) else []
            if len(parts) >= 4 and parts[3].isdigit():
                features.append({"name": parts[0], "level": int(parts[3]), "ref": ref})
        out[cls_id] = {
            "feat_progression": list(raw.get("featProgression") or []),
            "features": features,
            "starting_proficiencies": raw.get("startingProficiencies") or {},
            "multiclassing": raw.get("multiclassing") or {},
            "starting_equipment": raw.get("startingEquipment") or {},
            "saving_throws": list(raw.get("proficiency") or []),  # C9a: ["str", "con"]
            "primary_ability": list(raw.get("primaryAbility") or []),  # C9a: [{"str": True}, {"dex": True}]
            "optional_feature_progression": list(raw.get("optionalfeatureProgression") or []),  # C6c-1
        }
    return out


def load_raw_class_features_2024(class_dir) -> list[dict]:
    """Every XPHB `classFeature` record of the 12 SRD classes (C1)."""
    return [r for r in _raw_class_records(class_dir, "classFeature")
            if r.get("source") == "XPHB" and str(r.get("className", "")).lower() in SRD_CLASS_IDS
            and r.get("classSource", "XPHB") == "XPHB"]


def _raw_class_records(class_dir, key: str) -> list[dict]:
    if not class_dir:
        return []
    class_dir = Path(class_dir)
    index = _read_json(class_dir / "index.json")
    if not isinstance(index, dict):
        return []
    records: list[dict] = []
    for filename in index.values():
        data = _read_json(class_dir / filename) if isinstance(filename, str) else None
        if isinstance(data, dict):
            records.extend(r for r in data.get(key, []) if isinstance(r, dict))
    return records


def load_raw_optional_features(path) -> list[dict]:
    """Every record of `optionalfeatures.json`; [] when missing or broken."""
    if not path:
        return []
    data = _read_json(Path(path))
    if not isinstance(data, dict):
        return []
    return [o for o in data.get("optionalfeature", []) if isinstance(o, dict)]


# --------------------------------------------------------------- conversion

import re  # noqa: E402

from catalog.reference_data import FEATURE_TEXT_CHOICES, RULESET_2024_SOURCES, ruleset_for_edition  # noqa: E402

from .common import slug  # noqa: E402
from .spells import _flatten_entries  # noqa: E402

SRD_CLASS_IDS = frozenset({
    "barbarian", "bard", "cleric", "druid", "fighter", "monk",
    "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
})
_CLASS_SOURCES = ("PHB", "XPHB")
_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)$")


def _strip_paren(short: str) -> str:
    return _TRAILING_PAREN.sub("", short or "")


def _sub_id(raw: dict) -> str:
    return f"{slug(_strip_paren(raw.get('shortName') or raw['name']))}-{str(raw.get('source', 'PHB')).lower()}"


def _in_scope(raw: dict) -> bool:
    """A subclass this importer converts: not a `_copy`, one of the 12 SRD
    classes, attached to a PHB/XPHB class."""
    return ("_copy" not in raw
            and str(raw.get("className", "")).lower() in SRD_CLASS_IDS
            and raw.get("classSource", "PHB") in _CLASS_SOURCES)


def _feature_key(name, cls, cls_src, short, sub_src, level) -> tuple:
    return (name, cls, cls_src or "PHB", short, sub_src or "PHB", int(level))


def _parse_feature_ref(ref: str):
    parts = (ref or "").split("|")
    if len(parts) < 6:
        return None
    try:
        return _feature_key(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
    except ValueError:
        return None


def _raw_feature_key(raw: dict) -> tuple | None:
    try:
        return _feature_key(raw["name"], raw["className"], raw.get("classSource"),
                            raw["subclassShortName"], raw.get("subclassSource"), raw["level"])
    except (KeyError, ValueError, TypeError):
        return None


def _option_name(ref: dict) -> str:
    return ref.get("name") or str(ref.get("optionalfeature", "")).split("|")[0]


_SPELL_BLOCK_MODES = (("prepared", "always"), ("known", "always"), ("expanded", "expanded"))
_SN_KEY = re.compile(r"^s(\d)$")


def _clean_spell_name(text: str) -> str:
    """"toll the dead|xge" / "guidance#c" -> the bare spell name."""
    return text.split("|")[0].split("#")[0].strip()


def _spell_level_key(key: str, class_id: str):
    """Class level a spell-block key stands for: "3" -> 3; "sN" (an expanded
    list keyed by SPELL level, Warlock patrons only) -> 2N-1, the warlock
    level that first casts spells of level N. None for anything else."""
    if key.isdigit():
        return int(key)
    m = _SN_KEY.match(key)
    if m:
        if class_id != "warlock":
            raise ValueError(f"spell-level key {key!r} on a {class_id} subclass")
        return 2 * int(m.group(1)) - 1
    return None


def _subclass_spell_entries(raw: dict, class_id: str, is_2024: bool, resolve_spell, unresolved=None) -> list[dict]:
    """SRD-shaped `spells` entries of a subclass: the string spell lists of
    `prepared`/`known` (mode "always") and `expanded` (mode "expanded"), keyed
    by class level. Skipped: object values ({all}, {choose}, {"_": ...}),
    innate/daily/ritual blocks, and every block of a subclass with several
    named blocks (Land, Divine Soul, Genie, Giant, Arcane Archer)."""
    blocks = raw.get("additionalSpells") or []
    if len(blocks) != 1 or not isinstance(blocks[0], dict):
        return []
    entries: list[dict] = []
    seen: set[str] = set()
    for key, mode in _SPELL_BLOCK_MODES:
        by_level = blocks[0].get(key)
        if not isinstance(by_level, dict):
            continue
        rows = []
        for level_key, names in by_level.items():
            level = _spell_level_key(str(level_key), class_id)
            if level is not None and isinstance(names, list):
                rows.append((level, names))
        for level, names in sorted(rows, key=lambda r: r[0]):
            for name in names:
                if not isinstance(name, str):
                    continue
                clean = _clean_spell_name(name)
                base = slug(clean)
                spell_id = (resolve_spell(base + "-xphb") if is_2024 else None) or resolve_spell(base)
                if not spell_id:
                    if unresolved is not None:
                        unresolved.append(clean)
                    continue
                if spell_id in seen:
                    continue
                seen.add(spell_id)
                entries.append({"prerequisites": [{"type": "level", "index": f"{class_id}-{level}"}],
                                "spell": {"index": spell_id}, "mode": mode})
    return entries


def unresolved_spell_refs(raw_subs, resolve_spell) -> list[str]:
    """Spell names the converter would drop because the catalog has no such
    spell, over every in-scope non-SRD subclass (empty on real data)."""
    missing: list[str] = []
    for raw in raw_subs:
        if _in_scope(raw) and not raw.get("srd"):
            _subclass_spell_entries(raw, raw["className"].lower(), ruleset_for_edition(raw) == "2024",
                                    resolve_spell, missing)
    return missing


OPTION_FEATURE_TYPES = frozenset({"MV:B", "FS:B", "AS", "RN", "ED"})


def _option_prereq_level(raw: dict):
    """Class level an optional feature requires (Rune Knight runes, Four
    Elements disciplines), or None."""
    for pre in raw.get("prerequisite") or []:
        level = pre.get("level") if isinstance(pre, dict) else None
        if isinstance(level, dict):
            level = level.get("level")
        if isinstance(level, int):
            return level
    return None


def convert_optional_features(raw_options) -> dict[str, dict]:
    """`opt-{name}-{source}` records for the optional features subclasses
    grant picks of (maneuvers, arcane shots, runes, elemental disciplines,
    bard fighting styles)."""
    out: dict[str, dict] = {}
    for raw in raw_options or []:
        if not OPTION_FEATURE_TYPES & set(raw.get("featureType") or []):
            continue
        source = raw.get("source", "PHB")
        fid = f"opt-{slug(raw['name'])}-{source.lower()}"
        out.setdefault(fid, {
            "index": fid, "name": raw["name"], "desc": _flatten_entries(raw.get("entries") or []),
            "source": source, "ruleset": "2024" if source in RULESET_2024_SOURCES else "2014",
            "prerequisite_level": _option_prereq_level(raw),
            "feature_types": list(raw.get("featureType") or []),
        })
    return out


def _opt_id(ref) -> str:
    name, _, src = str(ref).partition("|")
    return f"opt-{slug(name)}-{(src or 'XPHB').lower()}"


def _has_repeatable(entries) -> bool:
    for e in entries or []:
        if isinstance(e, dict) and (e.get("name") == "Repeatable" or _has_repeatable(e.get("entries"))):
            return True
    return False


def _prerequisite_2024(raw: dict) -> dict:
    """XPHB EI prerequisite -> {level, optional_features [opt ids], cantrip "damage"|"attack"|None}."""
    out = {"level": None, "optional_features": [], "cantrip": None}
    for pre in raw.get("prerequisite") or []:
        if not isinstance(pre, dict):
            continue
        level = pre.get("level")
        level = level.get("level") if isinstance(level, dict) else level
        if isinstance(level, int):
            out["level"] = level
        refs = pre.get("optionalfeature")
        if isinstance(refs, list):
            out["optional_features"] += [_opt_id(r) for r in refs if isinstance(r, str)]
        spells = pre.get("spell")
        if isinstance(spells, list):
            for sp in spells:
                if isinstance(sp, dict):
                    out["cantrip"] = "attack" if "attack roll" in str(sp.get("entry", "")).lower() else "damage"
    return out


_INNATE_USES = {"daily": "1/long rest", "rest": "1/long rest", "ritual": "ritual"}


def _spells_2024(raw_blocks, resolve_spell) -> dict:
    """additionalSpells of an EI -> {innate [{spell, uses}], known_choose / prepared_choose
    [{filter, count}], ability?}. Unresolvable names and unparsable filters are dropped."""
    from .feats import _parse_spell_filter

    out: dict = {"innate": [], "known_choose": [], "prepared_choose": []}

    def add_names(names, uses):
        for name in names:
            if not isinstance(name, str):
                continue
            base = slug(_clean_spell_name(name))
            spell_id = resolve_spell(base + "-xphb") or resolve_spell(base)
            if spell_id:
                out["innate"].append({"spell": spell_id, "uses": uses})

    for block in raw_blocks if isinstance(raw_blocks, list) else []:
        if not isinstance(block, dict):
            continue
        if isinstance(block.get("ability"), str):
            out["ability"] = block["ability"]
        innate = (block.get("innate") or {}).get("_") if isinstance(block.get("innate"), dict) else None
        if isinstance(innate, list):
            add_names(innate, "at-will")
        elif isinstance(innate, dict):
            for wrapper, value in innate.items():
                if wrapper == "ritual" and isinstance(value, list):
                    add_names(value, "ritual")
                elif wrapper in ("daily", "rest") and isinstance(value, dict):
                    for names in value.values():
                        add_names(names if isinstance(names, list) else [], _INNATE_USES[wrapper])
        for key, target in (("known", "known_choose"), ("prepared", "prepared_choose")):
            items = (block.get(key) or {}).get("_") if isinstance(block.get(key), dict) else None
            for item in items if isinstance(items, list) else []:
                if isinstance(item, dict) and isinstance(item.get("choose"), str):
                    parsed = _parse_spell_filter(item["choose"])
                    if parsed:
                        out[target].append({"filter": parsed, "count": int(item.get("count", 1))})
    return out


def convert_class_optional_features_2024(raw_options, resolve_spell) -> dict[str, dict]:
    """C6c-1: `opt-<slug>-xphb` records for the XPHB Eldritch Invocations (EI) and Metamagic (MM).
    Kept apart from convert_optional_features / OPTION_FEATURE_TYPES so the subclass path is unchanged.
    Record: {index, name, desc, source, ruleset, feature_types, repeatable, prerequisite_2024, spells,
    senses, feat_progression, cost}."""
    out: dict[str, dict] = {}
    for raw in raw_options or []:
        if not isinstance(raw, dict) or raw.get("source") != "XPHB" or not raw.get("name"):
            continue
        types = raw.get("featureType") or []
        if not {"EI", "MM"} & set(types):
            continue
        fid = f"opt-{slug(raw['name'])}-xphb"
        consumes = raw.get("consumes") if isinstance(raw.get("consumes"), dict) else {}
        senses: dict = {}
        for sense in raw.get("senses") or []:
            if isinstance(sense, dict):
                senses.update({k: v for k, v in sense.items() if isinstance(v, int)})
        out.setdefault(fid, {
            "index": fid, "name": raw["name"], "desc": _flatten_entries(raw.get("entries") or []),
            "source": "XPHB", "ruleset": "2024", "feature_types": list(types),
            "repeatable": _has_repeatable(raw.get("entries")),
            "prerequisite_2024": _prerequisite_2024(raw),
            "spells": _spells_2024(raw.get("additionalSpells"), resolve_spell),
            "senses": senses,
            "feat_progression": list(raw.get("featProgression") or []),
            "cost": int(consumes.get("amount", 1)) if consumes else 1,
        })
    return out


def _required_option_ids(raw_required, options: dict) -> dict[str, list[str]]:
    """`{"3": ["Elemental Attunement|PHB"]}` -> `{"3": ["opt-elemental-attunement-phb"]}`
    (the id rule of convert_optional_features); unknown options are dropped."""
    out: dict[str, list[str]] = {}
    if not isinstance(raw_required, dict):
        return out
    for lvl, refs in raw_required.items():
        if not str(lvl).isdigit() or not isinstance(refs, list):
            continue
        ids = []
        for ref in refs:
            name, _, src = str(ref).partition("|")
            fid = f"opt-{slug(name)}-{(src or 'PHB').lower()}"
            if fid in options:
                ids.append(fid)
        if ids:
            out[str(lvl)] = ids
    return out


_EXPANDED_ALL_CLASS = re.compile(r"class=([A-Za-z]+)")


def _third_caster_block(raw: dict) -> dict | None:
    """The `spellcasting` block of a 1/3-caster subclass (Eldritch Knight,
    Arcane Trickster): ability, spell-list class (the first `{all: "...class=X"}`
    in `additionalSpells[*].expanded`, else wizard), known/prepared kind and the
    per-class-level cantrip / spell counts and slot rows from the subclass's own
    tables. None for every other subclass."""
    if raw.get("casterProgression") != "1/3":
        return None
    list_class = "wizard"
    for block in raw.get("additionalSpells") or []:
        expanded = block.get("expanded") if isinstance(block, dict) else None
        found = None
        for refs in (expanded or {}).values():
            for ref in refs if isinstance(refs, list) else []:
                match = _EXPANDED_ALL_CLASS.search(ref.get("all", "")) if isinstance(ref, dict) else None
                if match:
                    found = match.group(1).lower()
                    break
            if found:
                break
        if found:
            list_class = found
            break
    slots: list[list[int]] = []
    for group in raw.get("subclassTableGroups") or []:
        if isinstance(group, dict) and isinstance(group.get("rowsSpellProgression"), list):
            slots = [list(row) for row in group["rowsSpellProgression"]]
            break
    kind = "known" if "spellsKnownProgression" in raw else "prepared"
    return {
        "ability": str(raw.get("spellcastingAbility") or "int").upper(),
        "progression": "1/3", "list_class": list_class, "kind": kind,
        "cantrips": list(raw.get("cantripProgression") or []),
        "spells": list(raw.get("spellsKnownProgression") or raw.get("preparedSpellsProgression") or []),
        "slots": slots,
    }


def convert_subclasses(raw_subs, raw_feats, srd_subclass_ids, resolve_spell, raw_options=()):
    """5etools subclasses + subclass features -> (subclasses, features,
    level_rows) in the SRD shapes. Skips `_copy` records (2014 subclasses
    re-attached to the XPHB class: pure duplicates), classes outside the 12
    SRD ones, non-PHB/XPHB class sources and `srd: true` subclasses (the SRD
    record stays). A subclass's features are its `subclassFeatures` refs, each
    expanded depth-first into its `refSubclassFeature` children (the real
    features); children inside an `options` block are inlined as text.
    `resolve_spell` maps a spell slug to a catalog spell id or None (subclass
    spells: a 2024 subclass tries `slug-xphb` first)."""
    index: dict[tuple, dict] = {}
    for raw in raw_feats:
        if "_copy" in raw:
            continue
        key = _raw_feature_key(raw)
        if key is not None:
            index.setdefault(key, raw)

    subclasses: dict[str, dict] = {}
    features: dict[str, dict] = {}
    rows: list[dict] = []
    options = convert_optional_features(raw_options)
    for raw in raw_subs:
        if not _in_scope(raw) or raw.get("srd"):
            continue
        sub_id = _sub_id(raw)
        if sub_id in subclasses or sub_id in srd_subclass_ids:
            raise ValueError(f"duplicate subclass id {sub_id!r}")
        cls_name = raw["className"]
        cls_ref = {"index": cls_name.lower(), "name": cls_name}
        sub_ref = {"index": sub_id, "name": raw["name"]}
        record = {
            "index": sub_id, "name": raw["name"], "short_name": raw.get("shortName") or raw["name"],
            "class": cls_ref, "source": raw.get("source", "PHB"),
            "ruleset": ruleset_for_edition(raw), "desc": [],
            "spells": _subclass_spell_entries(raw, cls_ref["index"], ruleset_for_edition(raw) == "2024", resolve_spell),
        }
        third = _third_caster_block(raw)
        if third:
            record["spellcasting"] = third
        subclasses[sub_id] = record

        by_level: dict[int, list[dict]] = {}

        def register(feat: dict) -> None:
            fid = f"{sub_id}-{feat['level']}-{slug(feat['name'])}"
            if fid in features:
                return
            slot = {"index": fid, "name": feat["name"], "level": feat["level"], "class": cls_ref,
                    "subclass": sub_ref, "prerequisites": [], "desc": [], "source": feat.get("source", record["source"])}
            features[fid] = slot  # claim the id (and the document order) before the children
            by_level.setdefault(feat["level"], []).append({"index": fid, "name": feat["name"]})
            slot["desc"] = _flatten_entries(prepare(feat.get("entries") or [], False))
            if fid in FEATURE_TEXT_CHOICES:
                text_options = _text_options(fid, feat.get("entries") or [])
                if text_options:
                    slot["feature_specific"] = {"text_options": text_options}

        def _text_options(fid: str, entries) -> dict | None:
            """The first top-level `options` block of an allowlisted feature as
            {"count", "options": [{id, name, desc}]}; ids are stable
            `<featureId>--<slug(name)>` (slice R5 keys effects off them)."""
            for entry in entries:
                if not (isinstance(entry, dict) and entry.get("type") == "options"):
                    continue
                found = []
                for ref in entry.get("entries") or []:
                    child = index.get(_parse_feature_ref(ref.get("subclassFeature", ""))) if isinstance(ref, dict) else None
                    if child is None:
                        continue
                    desc = _flatten_entries(prepare(child.get("entries") or [], True))
                    option = {"id": f"{fid}--{slug(child['name'])}", "name": child["name"], "desc": desc}
                    if child.get("source") and child["source"] != record["source"]:
                        option["source"] = child["source"]  # G1: e.g. Elk/Tiger (SCAG) inside a PHB subclass
                    found.append(option)
                if found:
                    return {"count": entry.get("count") or 1, "options": found}
            return None

        def prepare(entries, in_options: bool):
            out = []
            for entry in entries:
                if not isinstance(entry, dict):
                    out.append(entry)
                    continue
                kind = entry.get("type")
                if kind == "refSubclassFeature":
                    child = index.get(_parse_feature_ref(entry.get("subclassFeature", "")))
                    if child is None:
                        continue
                    if in_options:
                        out.append({"type": "entries", "name": child["name"],
                                    "entries": prepare(child.get("entries") or [], True)})
                    else:
                        register(child)
                elif kind == "refOptionalfeature":
                    if in_options:
                        out.append(_option_name(entry))  # a bare line: an empty named block would vanish when flattened
                elif isinstance(kind, str) and kind.startswith("ref"):
                    continue
                else:
                    copy = dict(entry)
                    for field_name in ("entries", "items"):
                        if isinstance(copy.get(field_name), list):
                            copy[field_name] = prepare(copy[field_name], in_options or kind == "options")
                    out.append(copy)
            return out

        for ref in raw.get("subclassFeatures") or []:
            top = index.get(_parse_feature_ref(ref))
            if top is not None:
                register(top)
        for prog in raw.get("optionalfeatureProgression") or []:
            progression = {str(k): v for k, v in (prog.get("progression") or {}).items()
                           if str(k).isdigit() and isinstance(v, int)}
            types = set(prog.get("featureType") or [])
            first = min((int(k) for k in progression), default=None)
            if first is None or not by_level.get(first):
                continue
            pool = [o["index"] for o in options.values()
                    if types & set(o["feature_types"]) and o["ruleset"] == record["ruleset"]]
            if pool:
                spec = {"progression": progression, "options": pool}
                required = _required_option_ids(prog.get("required"), options)
                if required:
                    spec["required"] = required
                features[by_level[first][0]["index"]].setdefault("feature_specific", {})["optional_progression"] = spec
        for level in sorted(by_level):
            rows.append({"index": f"{sub_id}-{level}", "level": level, "class": cls_ref,
                         "subclass": sub_ref, "features": by_level[level]})
    for fid, opt in options.items():
        features[fid] = {k: v for k, v in opt.items() if k != "feature_types"}
    return subclasses, features, rows


def subclass_twins_from(raw_subs, known_ids) -> dict[str, str]:
    """Symmetric subclass id -> id map of 2014/2024 reprints, from each
    record's `reprintedAs` (`short|class|classSrc|src`). Shorter names are
    unreliable (Totem Warrior -> Wild Heart), so only `reprintedAs` is used.
    An `srd: true` record stands for its bare SRD id."""
    def own_id(raw):
        return slug(raw.get("shortName") or raw["name"]) if raw.get("srd") else _sub_id(raw)

    twins: dict[str, str] = {}
    for raw in raw_subs:
        if not _in_scope(raw):
            continue
        a = own_id(raw)
        for ref in raw.get("reprintedAs") or []:
            if not isinstance(ref, str):
                continue
            parts = ref.split("|")
            if len(parts) < 4:
                continue
            b = f"{slug(_strip_paren(parts[0]))}-{parts[3].lower()}"
            if a in known_ids and b in known_ids and a != b:
                twins[a] = b
                twins[b] = a
    return twins


_CLASS_FEATURE_PLACEHOLDERS = frozenset({"Subclass Feature", "Ability Score Improvement", "Epic Boon"})


def _is_placeholder_feature(raw: dict) -> bool:
    """Rows that only mark a level: the subclass grant ("<Class> Subclass",
    "Subclass Feature"), "Ability Score Improvement" and "Epic Boon"."""
    name = raw.get("name")
    return (name in _CLASS_FEATURE_PLACEHOLDERS
            or name == f"{raw.get('className')} Subclass")


def convert_class_features_2024(raw_features, class_records=None):
    """(features, level_features): `xphb-<class>-<level>-<slug(name)>` ->
    {index, name, level, class, desc, source "XPHB", ruleset "2024"} for every
    non-placeholder XPHB class feature (child records such as Protector or Turn
    Undead included, so entry references can be resolved later), and
    {class: {level: [ids]}} listing only the features the class record's
    `classFeatures` refs name (the real per-level list). Ids that clash are
    skipped (first wins)."""
    features: dict[str, dict] = {}
    for raw in raw_features or []:
        if _is_placeholder_feature(raw) or not raw.get("name") or not isinstance(raw.get("level"), int):
            continue
        cls = str(raw["className"]).lower()
        fid = f"xphb-{cls}-{raw['level']}-{slug(raw['name'])}"
        features.setdefault(fid, {
            "index": fid, "name": raw["name"], "level": raw["level"], "class": {"index": cls, "name": raw["className"]},
            "desc": _flatten_entries(raw.get("entries") or []), "source": "XPHB", "ruleset": "2024",
        })
    level_features: dict[str, dict[int, list[str]]] = {}
    for cls, rec in (class_records or {}).items():
        for ref in rec.get("features", []):
            fid = f"xphb-{cls}-{ref['level']}-{slug(ref['name'])}"
            if fid in features and fid not in level_features.setdefault(cls, {}).setdefault(ref["level"], []):
                level_features[cls][ref["level"]].append(fid)
    return features, level_features
