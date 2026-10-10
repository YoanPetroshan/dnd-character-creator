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

_CLASS_CHOICE_ID = re.compile(r"^class:([^:]+):\d+:(?:feature|expertise-choice|enemy-type|terrain-type|invocations|languages):(.+)$")


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


# C5: SRD choice-bearing class feature -> the XPHB feature it belongs to under ruleset 2024,
# as (class, SRD feature id) -> (XPHB feature name, n-th XPHB feature of that name in the
# class, counted in level order). Several SRD cards may share one XPHB row (the three
# Favored Enemy cards) and the SRD card levels differ from the XPHB ones (Bard Expertise
# 3/10 vs 2/9, Metamagic 3/10/17 vs 2/10/17, Invocations 2 vs 1), so the match is by name and
# ordinal, never by level. Every other class-level SRD feature with a choice is NOT mapped
# (Pact Boon and Natural Explorer 1-3 do not exist in the 2024 class lists): those keep
# their SRD row, name and level, with the choice attached, so no pick disappears.
# Not here: the Fighting Style feat cards (cid `class:<cls>:<lvl>:fighting-style`, C3) and the
# Weapon Mastery cards (cid `class:<cls>:weapon-mastery`, C2), which attach by cid below, and
# every subclass feature (unchanged).
SRD_TO_XPHB_FEATURE: dict[tuple[str, str], tuple[str, int]] = {
    ("bard", "bard-expertise-1"): ("Expertise", 0), ("bard", "bard-expertise-2"): ("Expertise", 1),
    ("rogue", "rogue-expertise-1"): ("Expertise", 0), ("rogue", "rogue-expertise-2"): ("Expertise", 1),
    ("sorcerer", "metamagic-1"): ("Metamagic", 0), ("sorcerer", "metamagic-2"): ("Metamagic", 1),
    ("sorcerer", "metamagic-3"): ("Metamagic", 2),
    ("warlock", "eldritch-invocations"): ("Eldritch Invocations", 0),
    ("ranger", "favored-enemy-1-type"): ("Favored Enemy", 0), ("ranger", "favored-enemy-2-types"): ("Favored Enemy", 0),
    ("ranger", "favored-enemy-3-enemies"): ("Favored Enemy", 0),
    ("fighter", "fighter-fighting-style"): ("Fighting Style", 0),
    ("paladin", "paladin-fighting-style"): ("Fighting Style", 0),
    ("ranger", "ranger-fighting-style"): ("Fighting Style", 0),
}
SRD_CHOICE_FEATURES_WITHOUT_XPHB = ("pact-boon",)
# C6b-1: under ruleset 2024 with the XPHB Ranger imported these cards are no longer offered
# (Deft Explorer replaces Natural Explorer), so their rows are unreachable there; mixed / 2014
# and an SRD-only catalog still show them with the SRD row.
SRD_CHOICE_FEATURES_REPLACED_2024 = ("natural-explorer-1-terrain-type", "natural-explorer-2-terrain-types",
                                     "natural-explorer-3-terrain-types")
_FS_FEATURE_IDS = frozenset({"fighter-fighting-style", "paladin-fighting-style", "ranger-fighting-style",
                             "additional-fighting-style", "champion-xphb-7-additional-fighting-style"})
_FS_CARD_ID = re.compile(r"^class:([^:]+):(\d+):fighting-style$")
_MASTERY_CARD_ID = re.compile(r"^class:([^:]+):weapon-mastery$")
_ORDER_CARD_ID = re.compile(r"^class:([^:]+):1:(?:divine|primal)-order$")  # C6a, XPHB row "Divine Order" / "Primal Order"


def _fighting_style_labels(choices: list[dict]) -> dict[tuple[str, int], list[str]]:
    out: dict[tuple[str, int], list[str]] = {}
    for c in choices:
        m = _FS_CARD_ID.match(c["id"]) if c["source"]["kind"] == "class" else None
        if m and c["selected"]:
            out.setdefault((m.group(1), int(m.group(2))), []).extend(_labels(c))
    return out


def _mastery_labels(choices: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in choices:
        m = _MASTERY_CARD_ID.match(c["id"]) if c["source"]["kind"] == "class" else None
        if m and c["selected"]:
            out.setdefault(m.group(1), []).extend(_labels(c))
    return out


def _order_labels(choices: list[dict]) -> dict[str, tuple[str, list[str]]]:
    """{class id: (card label, option labels)} of the Divine / Primal Order cards (C6a)."""
    out: dict[str, tuple[str, list[str]]] = {}
    for c in choices:
        m = _ORDER_CARD_ID.match(c["id"]) if c["source"]["kind"] == "class" else None
        if m and c["selected"]:
            out[m.group(1)] = (c["label"], _labels(c))
    return out


def _xphb_class_rows(catalog, cls_id: str, class_level: int) -> list[tuple[int, str, int, str]]:
    """[(level, name, ordinal, XPHB feature id)] of the XPHB class feature list up to class_level,
    in level order; ordinal = how many features of the same name came before (Indomitable
    9/13/17)."""
    by_level = (getattr(catalog, "class_2024_level_features", None) or {}).get(cls_id) or {}
    seen: dict[str, int] = {}
    rows: list[tuple[int, str, int, str]] = []
    for lvl in sorted(by_level):
        for fid in by_level[lvl]:
            feature = catalog.features.get(fid)
            if not feature:
                continue
            ordinal = seen.get(feature["name"], 0)
            seen[feature["name"]] = ordinal + 1
            if lvl <= class_level:
                rows.append((lvl, feature["name"], ordinal, fid))
    return rows


def build_features(catalog, resolved_classes, refs_by_class, race, race_id, subrace, bg, bg_id, feats, choices,
                   ruleset: str = "mixed") -> list[dict]:
    out: list[dict] = []
    class_choices = _class_choice_labels(choices)
    fs_labels = _fighting_style_labels(choices) if ruleset == "2024" else {}
    mastery_labels = _mastery_labels(choices) if ruleset == "2024" else {}
    order_labels = _order_labels(choices) if ruleset == "2024" else {}

    for rc in resolved_classes:
        if not rc["cls"] or not rc["cls_id"]:
            continue
        cls_id = rc["cls_id"]
        class_source = {"kind": "class", "id": cls_id, "label": rc["cls"]["name"]}
        xphb_rows = _xphb_class_rows(catalog, cls_id, rc["level"]) if ruleset == "2024" else []
        overlay = bool(xphb_rows)
        seen: set[str] = set()
        class_entries, subclass_entries = [], []
        consumed: set[str] = set()  # SRD feature ids whose choice was attached somewhere
        fs_used: set[tuple[str, int]] = set()
        srd_levels: dict[str, int] = {}
        for lvl, ref in sorted(refs_by_class.get(cls_id, []), key=lambda r: r[0]):
            feature = catalog.features.get(ref["index"])
            if not feature or ref["index"] in seen or feature["name"].startswith("Ability Score Improvement"):
                continue
            sub = feature.get("subclass")
            if sub and sub.get("index") != rc["subclass_id"]:
                continue
            seen.add(ref["index"])
            srd_levels[ref["index"]] = lvl
            if sub:
                labels = [_strip_prefix(l, feature["name"]) for l in class_choices.get((cls_id, ref["index"]), [])]
                consumed.add(ref["index"])
                if ref["index"] in _FS_FEATURE_IDS and (cls_id, lvl) in fs_labels:
                    labels += fs_labels[(cls_id, lvl)]
                    fs_used.add((cls_id, lvl))
                source = {"kind": "subclass", "id": rc["subclass_id"], "label": rc["subclass"]["name"]}
                subclass_entries.append(_entry(source, feature["name"], lvl, labels))
            elif not overlay:
                labels = [_strip_prefix(l, feature["name"]) for l in class_choices.get((cls_id, ref["index"]), [])]
                class_entries.append(_entry(class_source, feature["name"], lvl, labels))
        if overlay:
            # Choices that belong to an XPHB row, in SRD level order.
            by_target: dict[tuple[str, int], list[str]] = {}
            for srd_id, lvl in sorted(srd_levels.items(), key=lambda kv: kv[1]):
                target = SRD_TO_XPHB_FEATURE.get((cls_id, srd_id))
                if target and class_choices.get((cls_id, srd_id)):
                    name = catalog.features[srd_id]["name"]
                    by_target.setdefault(target, []).extend(
                        _strip_prefix(l, name) for l in class_choices[(cls_id, srd_id)])
            class_fs = sorted(k for k in fs_labels if k[0] == cls_id and k not in fs_used)
            fs_rows = [r for r in xphb_rows if r[1] == "Fighting Style"]
            # C6b-1: a card whose cid ends in an XPHB feature id of this class attaches to that
            # row (expertise, and later languages / invocations / metamagic cards).
            row_fids = {r[3] for r in xphb_rows}
            by_fid = {fid: labels for (c_id, fid), labels in class_choices.items()
                      if c_id == cls_id and fid in row_fids}
            for key in class_fs:  # the class's own Fighting Style feat card(s)
                row = next((r for r in fs_rows if r[0] == key[1]), None)
                if row:
                    by_target.setdefault((row[1], row[2]), []).extend(fs_labels[key])
                    fs_used.add(key)
            if cls_id in mastery_labels:
                by_target.setdefault(("Weapon Mastery", 0), []).extend(mastery_labels[cls_id])
            if cls_id in order_labels:
                by_target.setdefault((order_labels[cls_id][0], 0), []).extend(order_labels[cls_id][1])
            placed: set[tuple[str, int]] = set()
            for lvl, name, ordinal, fid in xphb_rows:
                labels = by_target.get((name, ordinal), []) + by_fid.get(fid, [])
                if labels:
                    placed.add((name, ordinal))
                class_entries.append(_entry(class_source, name, lvl, labels))
            # Anything that found no XPHB row keeps its SRD row (nothing is dropped).
            for srd_id, lvl in sorted(srd_levels.items(), key=lambda kv: kv[1]):
                if srd_id in consumed or not class_choices.get((cls_id, srd_id)):
                    continue
                if SRD_TO_XPHB_FEATURE.get((cls_id, srd_id)) in placed:
                    continue
                name = catalog.features[srd_id]["name"]
                class_entries.append(_entry(class_source, name, lvl, [_strip_prefix(l, name) for l in class_choices[(cls_id, srd_id)]]))
            for key in class_fs:
                if key not in fs_used:
                    class_entries.append(_entry(class_source, "Fighting Style", key[1], fs_labels[key]))
            if cls_id in mastery_labels and ("Weapon Mastery", 0) not in placed:
                class_entries.append(_entry(class_source, "Weapon Mastery", 1, mastery_labels[cls_id]))
            if cls_id in order_labels and (order_labels[cls_id][0], 0) not in placed:
                class_entries.append(_entry(class_source, order_labels[cls_id][0], 1, order_labels[cls_id][1]))
            class_entries.sort(key=lambda e: e["level"])  # stable: XPHB order within a level
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
    """sheet.feats: [{id, name, origin: "background"|"species"|"asi"|"fighting-style", level, choice?}]."""
    out = []
    for feat in feats:
        prefix = feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"
        labels = _prefixed_labels(choices, "feat", prefix)
        entry = {
            "id": feat["index"], "name": feat["name"],
            "origin": "asi" if feat.get("_asi_cid") else "fighting-style" if feat.get("_fs_cid") else "species" if feat.get("_species_origin") else "background",
            "level": feat.get("_asi_level"),
        }
        if labels:
            entry["choice"] = labels
        out.append(entry)
    return out
