"""Builds sheet.features / sheet.feats: what the character can do, as a flat
list for the sheet and the exports. Pure; resolve() passes in everything.

A feature is {source: {kind, id, label}, name, level, choice?}:
 * class / subclass features up to the current class level, `level` being the
   class level that grants them; ASI rows are left out (they show up as
   ability scores or feats);
 * `choice` = the labels of what the player picked for that feature (Fighting
   Style, Metamagic, Pact Boon, Expertise, favored enemy, invocations, a
   species trait's ancestry...), attached to the parent feature;
 * species traits (race + subrace), the background feature, and feats.
Order: per class its class features then its subclass features (by level),
then species, background, feats.
"""
from __future__ import annotations

import re

_CLASS_CHOICE_ID = re.compile(r"^class:([^:]+):\d+:(?:feature|expertise-choice|enemy-type|terrain-type|invocations):(.+)$")


def _labels(choice: dict) -> list[str]:
    by_id = {o["id"]: o["label"] for o in choice["options"]}
    return [by_id.get(s, s) for s in choice["selected"]]


def _strip_prefix(label: str, feature_name: str) -> str:
    prefix = f"{feature_name}: "
    return label[len(prefix):] if label.startswith(prefix) else label


def _class_choice_labels(choices: list[dict]) -> dict[tuple[str, str], list[str]]:
    out: dict[tuple[str, str], list[str]] = {}
    for c in choices:
        m = _CLASS_CHOICE_ID.match(c["id"]) if c["source"]["kind"] == "class" else None
        if m and (c["selected"] or c.get("granted")):
            # Automatically granted options (Elemental Attunement) are listed first.
            out.setdefault((m.group(1), m.group(2)), []).extend([g["label"] for g in c.get("granted") or []] + _labels(c))
    return out


def _prefixed_labels(choices: list[dict], kind: str, prefix: str) -> list[str]:
    out: list[str] = []
    for c in choices:
        if c["source"]["kind"] == kind and (c["id"] == prefix or c["id"].startswith(prefix + ":")):
            out.extend(_labels(c))
    return out


def _entry(source: dict, name: str, level, choice: list[str]) -> dict:
    entry = {"source": source, "name": name, "level": level}
    if choice:
        entry["choice"] = choice
    return entry


def build_features(catalog, resolved_classes, refs_by_class, race, race_id, subrace, bg, bg_id, feats, choices) -> list[dict]:
    out: list[dict] = []
    class_choices = _class_choice_labels(choices)

    for rc in resolved_classes:
        if not rc["cls"] or not rc["cls_id"]:
            continue
        cls_id = rc["cls_id"]
        seen: set[str] = set()
        class_entries, subclass_entries = [], []
        for lvl, ref in sorted(refs_by_class.get(cls_id, []), key=lambda r: r[0]):
            feature = catalog.features.get(ref["index"])
            if not feature or ref["index"] in seen or feature["name"].startswith("Ability Score Improvement"):
                continue
            sub = feature.get("subclass")
            if sub and sub.get("index") != rc["subclass_id"]:
                continue
            seen.add(ref["index"])
            labels = [_strip_prefix(l, feature["name"]) for l in class_choices.get((cls_id, ref["index"]), [])]
            if sub:
                source = {"kind": "subclass", "id": rc["subclass_id"], "label": rc["subclass"]["name"]}
                subclass_entries.append(_entry(source, feature["name"], lvl, labels))
            else:
                source = {"kind": "class", "id": cls_id, "label": rc["cls"]["name"]}
                class_entries.append(_entry(source, feature["name"], lvl, labels))
        out += class_entries + subclass_entries

    if race:
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        seen_traits: set[str] = set()
        for ref in refs:
            trait = catalog.traits.get(ref["index"])
            if not trait or not trait.get("name") or ref["index"] in seen_traits:
                continue
            seen_traits.add(ref["index"])
            labels = [_strip_prefix(l, trait["name"]) for l in
                      _prefixed_labels(choices, "species", f"species:{race_id}:trait:{ref['index']}")]
            out.append(_entry(source, trait["name"], None, labels))

    feature = (bg or {}).get("feature") or {}
    if bg and feature.get("name"):
        out.append(_entry({"kind": "background", "id": bg_id, "label": bg["name"]}, feature["name"], None, []))

    for feat in feats_summary(feats, choices):
        out.append(_entry({"kind": "feat", "id": feat["id"], "label": feat["name"]}, feat["name"], feat["level"], feat.get("choice", [])))
    return out


def feats_summary(feats: list[dict], choices: list[dict]) -> list[dict]:
    """sheet.feats: [{id, name, origin: "background"|"species"|"asi", level, choice?}]."""
    out = []
    for feat in feats:
        prefix = feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"
        labels = _prefixed_labels(choices, "feat", prefix)
        entry = {
            "id": feat["index"], "name": feat["name"],
            "origin": "asi" if feat.get("_asi_cid") else "species" if feat.get("_species_origin") else "background",
            "level": feat.get("_asi_level"),
        }
        if labels:
            entry["choice"] = labels
        out.append(entry)
    return out
