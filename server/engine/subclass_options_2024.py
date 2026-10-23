"""RP13 (F2, E13): editable build-time option cards of XPHB subclass features (Hunter's Prey, Defensive Tactics,
Aspect of the Wilds, Elemental Affinity, Primal Companion, Feywild Gifts), ruleset "2024" only.

The data is `reference_data.SUBCLASS_OPTIONS_2024` (verbatim quotes pinned by tests). A card needs the XPHB feature
record in the catalog, the selected subclass and the class level at the record's level, so an SRD-only catalog, a
2014 twin or mixed / 2014 gives nothing (a stored pick there is a stale cid and lands in `pruned`). Pure: resolve()
wires the templates, the effects, and `class_resources` the notes."""
from __future__ import annotations

import re

from catalog import reference_data

_CARD_RE = re.compile(r"^class:([^:]+):\d+:feature:(.+)$")
# The class-effect keys an option may carry (same readers as CLASS_FEATURE_EFFECTS_2024).
_EFFECT_KEYS = ("senses_additive", "climb_equals_walk", "swim_equals_walk", "resist")


def _join(desc) -> str:
    return "\n".join(str(d) for d in desc or [])


def option_id(feature_id: str, key: str) -> str:
    return f"{feature_id}--{key}"


def _line_description(record: dict, name: str) -> str | None:
    prefix = name + ". "
    for line in record.get("desc") or []:
        if isinstance(line, str) and line.startswith(prefix):
            return line[len(prefix):]
    return None


def _options(record: dict, spec: dict, feature_id: str) -> list[dict] | None:
    """The card options, or None when the record's text no longer carries them (a changed catalog)."""
    text = _join(record.get("desc"))
    out = []
    for key, o in spec["options"].items():
        if "quote" in o and o["quote"] not in text:
            return None
        if "quote" not in o and not any(o["name"] in q for q in spec["quotes"]):
            return None
        option = {"id": option_id(feature_id, key), "label": o["name"]}
        if o.get("line"):
            desc = _line_description(record, o["name"])
            if desc is None:
                return None
            option["description"] = desc
        out.append(option)
    return out


def templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """One required pick (count 1) per option feature of the class's selected XPHB subclass whose level is reached."""
    cls_id, sub_id = rc.get("cls_id"), rc.get("subclass_id")
    if ruleset != "2024" or not rc.get("cls") or not cls_id or not sub_id:
        return []
    out = []
    for fid, spec in reference_data.SUBCLASS_OPTIONS_2024.items():
        if spec["class"] != cls_id or spec["subclass"] != sub_id:
            continue
        record = catalog.features.get(fid)
        if not record or rc["level"] < (record.get("level") or 1):
            continue
        options = _options(record, spec, fid)
        if not options:
            continue
        level = record.get("level") or 1
        out.append({
            "id": f"class:{cls_id}:{level}:feature:{fid}",
            "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": level},
            "label": spec["label"],
            "description": _join(record.get("desc")),
            "count": 1,
            "options": options,
        })
    return out


def spec_for_card(c: dict) -> tuple[str, dict] | None:
    """(feature id, SUBCLASS_OPTIONS_2024 entry) a class card was built from, or None."""
    if (c.get("source") or {}).get("kind") != "class":
        return None
    m = _CARD_RE.match(c.get("id", ""))
    if not m:
        return None
    spec = reference_data.SUBCLASS_OPTIONS_2024.get(m.group(2))
    return (m.group(2), spec) if spec and spec["class"] == m.group(1) else None


def selected(choices) -> list[tuple[str, int, str, dict, str, dict]]:
    """[(class id, card level, feature id, spec, option key, option)] of the resolved cards, in choice order."""
    out = []
    if not isinstance(choices, list):
        return out
    for c in choices:
        found = spec_for_card(c)
        if not found or not c.get("selected"):
            continue
        fid, spec = found
        key = c["selected"][0][len(fid) + 2:] if c["selected"][0].startswith(fid + "--") else None
        option = spec["options"].get(key) if key else None
        if option is not None:
            out.append((c["source"]["id"], c["source"].get("level") or 1, fid, spec, key, option))
    return out


def effects(choices) -> list[tuple[str, int, dict]]:
    """Class-effect triples (class id, class level, effect) of the picked options, for `features.class_effects`
    readers (senses, speeds, resistances)."""
    out = []
    for cls_id, level, fid, _spec, _key, option in selected(choices):
        effect = {k: option[k] for k in _EFFECT_KEYS if k in option}
        if effect:
            out.append((cls_id, level, {**effect, "feature_id": fid, "feature_name": option["name"]}))
    return out


def note_name(spec: dict, option: dict) -> str:
    return f"{spec['label']}: {option['name']}"
