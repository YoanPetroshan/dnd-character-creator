"""5etools class files -> SRD-shaped subclass records (Slice 11b).

`class/index.json` maps a class id to a file; each file is
{"class": [...], "subclass": [...], "subclassFeature": [...]}. Only the
`subclass` and `subclassFeature` arrays are read here.
"""
from __future__ import annotations

import json
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

from catalog.reference_data import ruleset_for_edition  # noqa: E402

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


def convert_subclasses(raw_subs, raw_feats, srd_subclass_ids, resolve_spell):
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
        for level in sorted(by_level):
            rows.append({"index": f"{sub_id}-{level}", "level": level, "class": cls_ref,
                         "subclass": sub_ref, "features": by_level[level]})
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
