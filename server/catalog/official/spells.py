"""5etools spell files -> SRD-shaped spell records (Slice 11a).

`spells/index.json` maps a source code to a file; each file is {"spell": [...]}.
Records carry no class list: class membership lives in `spells/sources.json`
as {SOURCE: {SpellName: {"class": [{name, source}], "classVariant": [...]}}}.
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


def load_raw_spells(spell_dir) -> list[dict]:
    """Every raw spell of every book in `spell_dir/index.json`, in index
    order. [] when the directory or index is missing; a file that is missing
    or not valid JSON is skipped."""
    if not spell_dir:
        return []
    spell_dir = Path(spell_dir)
    index = _read_json(spell_dir / "index.json")
    if not isinstance(index, dict):
        return []
    out: list[dict] = []
    for filename in index.values():
        if not isinstance(filename, str):
            continue
        data = _read_json(spell_dir / filename)
        if isinstance(data, dict):
            out.extend(s for s in data.get("spell", []) if isinstance(s, dict))
    return out


def load_spell_class_lookup(spell_dir) -> dict:
    """`spells/sources.json` as-is ({SOURCE: {SpellName: {...}}}); {} when missing."""
    if not spell_dir:
        return {}
    data = _read_json(Path(spell_dir) / "sources.json")
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Slice 11a.2: converter (5etools spell -> the SRD spell dict shape)
# ---------------------------------------------------------------------------

import re

from catalog.reference_data import ruleset_for_feat
from .common import slug
from .innate_spells import _SPELL_SCHOOL_CODES

# Spells the SRD 5.1 prints under a shorter name than the PHB: the slug of
# the PHB/5etools name -> the SRD index. Verified by script against the
# `srd: "<SRD name>"` strings 5etools puts on exactly these 17 PHB records.
SRD_SPELL_ALIASES: dict[str, str] = {
    "bigbys-hand": "arcane-hand",
    "drawmijs-instant-summons": "instant-summons",
    "evards-black-tentacles": "black-tentacles",
    "leomunds-secret-chest": "secret-chest",
    "leomunds-tiny-hut": "tiny-hut",
    "melfs-acid-arrow": "acid-arrow",
    "mordenkainens-faithful-hound": "faithful-hound",
    "mordenkainens-magnificent-mansion": "magnificent-mansion",
    "mordenkainens-private-sanctum": "private-sanctum",
    "mordenkainens-sword": "arcane-sword",
    "nystuls-magic-aura": "arcanists-magic-aura",
    "otilukes-freezing-sphere": "freezing-sphere",
    "otilukes-resilient-sphere": "resilient-sphere",
    "ottos-irresistible-dance": "irresistible-dance",
    "rarys-telepathic-bond": "telepathic-bond",
    "tashas-hideous-laughter": "hideous-laughter",
    "tensers-floating-disk": "floating-disk",
}

_SCHOOL_NAMES = {code: (index, index.capitalize()) for code, index in _SPELL_SCHOOL_CODES.items()}

_TAG_RE = re.compile(r"\{@(\w+)(?: ([^{}]*))?\}")
_ATTACK_WORDS = {
    "mw": "Melee Weapon Attack:", "rw": "Ranged Weapon Attack:", "ms": "Melee Spell Attack:",
    "rs": "Ranged Spell Attack:", "m": "Melee Attack:", "r": "Ranged Attack:",
    "mw,rw": "Melee or Ranged Weapon Attack:", "ms,rs": "Melee or Ranged Spell Attack:",
}
# Tags whose later "|" segments are not display text.
_FIRST_SEGMENT_TAGS = {"filter", "scaledamage", "scaledice", "dice", "damage", "d20", "autodice", "note", "footnote", "book", "i", "b", "u", "s"}


def _tag_repl(m: re.Match) -> str:
    tag, body = m.group(1), m.group(2) or ""
    parts = body.split("|")
    first = parts[0]
    if tag == "dc":
        return f"DC {first}"
    if tag == "hit":
        return first if first[:1] in "+-" else f"+{first}"
    if tag == "h":
        return "Hit: "
    if tag == "atk":
        return _ATTACK_WORDS.get(first, first)
    if tag == "chance":
        return f"{first} percent"
    if tag == "quickref":
        return parts[3] if len(parts) > 3 and parts[3] else first
    if tag in _FIRST_SEGMENT_TAGS:
        return first
    return parts[2] if len(parts) >= 3 and parts[2] else first


def _strip_tags(text: str) -> str:
    """Flattens 5etools `{@tag a|b|c}` markup (innermost first) to plain text."""
    previous = None
    while previous != text:
        previous = text
        text = _TAG_RE.sub(_tag_repl, text)
    return text


def _cell(cell) -> str:
    if isinstance(cell, str):
        return _strip_tags(cell)
    if isinstance(cell, dict):
        roll = cell.get("roll")
        if isinstance(roll, dict):
            if "exact" in roll:
                return str(roll["exact"])
            if "min" in roll and "max" in roll:
                return f"{roll['min']}-{roll['max']}"
        if "entry" in cell:
            return _cell(cell["entry"])
    return str(cell)


def _flatten_entries(entries) -> list[str]:
    """Rich 5etools entries -> plain paragraphs (named sub-entries get
    "Name. " prefixed, list items become their own lines, table rows are
    " | " joined); no markup survives."""
    out: list[str] = []
    for entry in entries or []:
        if isinstance(entry, str):
            out.append(_strip_tags(entry))
        elif isinstance(entry, dict):
            kind = entry.get("type")
            if kind == "list":
                for item in entry.get("items", []):
                    out.extend(_flatten_entries([item]))
            elif kind == "item":
                body = _flatten_entries(entry.get("entries") or ([entry["entry"]] if "entry" in entry else []))
                name = entry.get("name")
                if name and body:
                    body[0] = f"{_strip_tags(name)}. {body[0]}"
                elif name:
                    body = [f"{_strip_tags(name)}."]
                out.extend(body)
            elif kind == "table":
                if entry.get("caption"):
                    out.append(_strip_tags(entry["caption"]))
                if entry.get("colLabels"):
                    out.append(" | ".join(_cell(c) for c in entry["colLabels"]))
                for row in entry.get("rows", []):
                    out.append(" | ".join(_cell(c) for c in row))
            else:  # entries / quote / inset / ...
                body = _flatten_entries(entry.get("entries", []))
                name = entry.get("name")
                if name and body:
                    body[0] = f"{_strip_tags(name)}. {body[0]}"
                out.extend(body)
    return out


def _plural(amount, unit: str) -> str:
    return f"{amount} {unit}" if amount == 1 else f"{amount} {unit}s"


def _casting_time(times) -> tuple[str, str | None]:
    """(text, condition) from `time[0]`: {"number": 1, "unit": "bonus"} ->
    "1 bonus action"; a reaction's `condition` text is returned separately."""
    if not times:
        return "", None
    t = times[0]
    unit = t.get("unit", "")
    number = t.get("number", 1)
    if unit in ("action", "reaction"):
        text = _plural(number, unit)
    elif unit == "bonus":
        text = _plural(number, "bonus action")
    else:
        text = _plural(number, unit)
    return text, t.get("condition")


def _range_text(rng: dict) -> str:
    kind = rng.get("type")
    dist = rng.get("distance") or {}
    dtype = dist.get("type")
    amount = dist.get("amount")
    if kind == "special":
        return "Special"
    if kind == "point":
        if dtype == "self":
            return "Self"
        if dtype == "touch":
            return "Touch"
        if dtype == "sight":
            return "Sight"
        if dtype == "unlimited":
            return "Unlimited"
        if dtype in ("feet", "miles") and amount is not None:
            return f"{amount} feet" if dtype == "feet" else _plural(amount, "mile")
        return "Special"
    if dtype in ("feet", "miles") and amount is not None:
        return f"Self ({amount}-{'foot' if dtype == 'feet' else 'mile'} {kind})"
    return "Self"


def _duration_text(durations) -> tuple[str, bool]:
    """(text, concentration): SRD style - a concentration spell reads
    "Up to 1 minute"; permanent spells "Until dispelled"."""
    texts = []
    concentration = False
    for d in durations or []:
        kind = d.get("type")
        if kind == "instant":
            texts.append("Instantaneous")
        elif kind == "timed":
            inner = d.get("duration") or {}
            span = _plural(inner.get("amount", 1), inner.get("type", "round"))
            if d.get("concentration"):
                concentration = True
                span = f"Up to {span}"
            texts.append(span)
        elif kind == "permanent":
            ends = d.get("ends") or []
            if "dispel" in ends and "trigger" in ends:
                texts.append("Until dispelled or triggered")
            elif "trigger" in ends:
                texts.append("Until triggered")
            else:
                texts.append("Until dispelled")
        else:
            texts.append("Special")
    return " or ".join(texts) or "Instantaneous", concentration


def _components(comp: dict) -> tuple[list[str], str | None]:
    out = []
    material = None
    if comp.get("v"):
        out.append("V")
    if comp.get("s"):
        out.append("S")
    m = comp.get("m")
    if m:
        out.append("M")
        text = m.get("text") if isinstance(m, dict) else m
        if isinstance(text, str) and text.strip():
            text = _strip_tags(text.strip())
            material = text[0].upper() + text[1:]
            if not material.endswith("."):
                material += "."
    return out, material


def _spell_classes(raw: dict, class_lookup: dict) -> list[dict]:
    entry = ((class_lookup or {}).get(raw.get("source"), {}) or {}).get(raw.get("name"), {}) or {}
    classes: list[dict] = []
    seen = set()
    # `classVariant` is where XGE/TCE/FTD/BMT keep their class lists (all 95 XGE
    # spells have no `class` at all), so both lists count.
    for c in list(entry.get("class", []) or []) + list(entry.get("classVariant", []) or []):
        name = c.get("name")
        index = slug(name) if isinstance(name, str) else None
        if index and index not in seen:
            seen.add(index)
            classes.append({"index": index, "name": name})
    return classes


def _spell_index(raw: dict, srd_indices, taken) -> str:
    """The ID rule. 2024-ruleset books always get `<slug>-<source>`. Other
    books use the bare slug, except that a spell already in the SRD (same
    slug, or one of the 17 renames) keeps the SRD index, and a bare slug
    already taken by an earlier non-SRD record gets `-<source>`."""
    base = slug(raw["name"])
    source = raw["source"].lower()
    if ruleset_for_feat(raw) == "2024":
        return f"{base}-{source}"
    base = SRD_SPELL_ALIASES.get(base, base)
    if base in srd_indices:
        return base
    if base in taken:
        return f"{base}-{source}"
    return base


def _spell_from_5etools(raw: dict, class_lookup: dict, srd_indices=frozenset(), taken=()) -> dict | None:
    if not isinstance(raw, dict) or not raw.get("name") or not raw.get("source") or "_copy" in raw:
        return None
    school_index, school_name = _SCHOOL_NAMES.get(raw.get("school"), (None, None))
    casting_time, casting_condition = _casting_time(raw.get("time"))
    duration, concentration = _duration_text(raw.get("duration"))
    components, material = _components(raw.get("components") or {})
    record = {
        "index": _spell_index(raw, srd_indices, taken),
        "name": raw["name"],
        "level": raw.get("level", 0),
        "school": {"index": school_index, "name": school_name} if school_index else {},
        "casting_time": casting_time,
        "range": _range_text(raw.get("range") or {}),
        "components": components,
        "ritual": bool((raw.get("meta") or {}).get("ritual")),
        "duration": duration,
        "concentration": concentration,
        "desc": _flatten_entries(raw.get("entries")),
        "classes": _spell_classes(raw, class_lookup),
        "source": raw["source"],
        "ruleset": ruleset_for_feat(raw),
    }
    if material:
        record["material"] = material
    if casting_condition:
        record["casting_condition"] = _strip_tags(casting_condition)
    higher = []  # the "At Higher Levels" heading is dropped, like the SRD records
    for entry in raw.get("entriesHigherLevel") or []:
        higher.extend(_flatten_entries(entry.get("entries") if isinstance(entry, dict) else [entry]))
    if higher:
        record["higher_level"] = higher
    return record


def load_official_spells(spell_dir, srd_indices=None) -> list[dict]:
    """All converted official spells, ids assigned by the ID rule against
    `srd_indices` (default: the bundled SRD list). A record whose index is an
    SRD index is the same spell as the SRD record - the caller merges its
    `classes` into it instead of adding it. [] when the data is missing."""
    raw_spells = load_raw_spells(spell_dir)
    if not raw_spells:
        return []
    if srd_indices is None:
        srd_indices = _bundled_srd_spell_indices()
    lookup = load_spell_class_lookup(spell_dir)
    taken: set[str] = set()
    out: list[dict] = []
    for raw in raw_spells:
        record = _spell_from_5etools(raw, lookup, srd_indices, taken)
        if record is None:
            continue
        if record["index"] not in srd_indices:
            taken.add(record["index"])
        out.append(record)
    return out


def _bundled_srd_spell_indices() -> frozenset[str]:
    from .paths import _repo_root
    with open(_repo_root / "chargen" / "data" / "srd" / "5e-SRD-Spells.json", encoding="utf-8") as f:
        return frozenset(s["index"] for s in json.load(f))


def build_spell_aliases(spells: dict[str, dict]) -> dict[str, str]:
    """id -> id fallbacks for references that name a spell by its bare slug:
    the 17 SRD renames, and 2024-only spells (`divine-smite` ->
    `divine-smite-xphb`) when no 2014 spell has that slug."""
    aliases = dict(SRD_SPELL_ALIASES)
    for sid, spell in spells.items():
        if spell.get("ruleset") != "2024":
            continue
        base = slug(spell["name"])
        if base not in spells and base not in aliases:
            aliases[base] = sid
    return aliases


def link_spell_versions(spells: dict[str, dict]) -> dict[str, str]:
    """Pairs each 2024-ruleset spell with the 2014 spell of the same name
    (symmetric id -> id): the 2014 record's index or slug(name) equals the
    2024 spell's slug(name). Spells without a counterpart are absent."""
    keys_2014: dict[str, str] = {}
    for sid, spell in spells.items():
        if spell.get("ruleset") != "2024":
            keys_2014.setdefault(sid, sid)
            keys_2014.setdefault(slug(spell["name"]), sid)
    for old_name, srd_index in SRD_SPELL_ALIASES.items():  # 2024 books keep e.g. "Bigby's Hand"
        if srd_index in spells:
            keys_2014.setdefault(old_name, srd_index)
    twins: dict[str, str] = {}
    for sid, spell in spells.items():
        if spell.get("ruleset") == "2024":
            older = keys_2014.get(slug(spell["name"]))
            if older:
                twins[sid] = older
                twins[older] = sid
    return twins
