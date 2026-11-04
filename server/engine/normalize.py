"""normalize_draft(draft) -> (clean_draft, problems)

A type-coercion pass run at the top of resolve(). The draft arrives as
arbitrary JSON (hand-edited, imported, or stale from localStorage), so
this guarantees every container resolve() reads has the expected JSON
type, and reports every value it had to replace instead of silently
guessing. It never mutates its input.
"""
from __future__ import annotations

import re

from i18n.messages import msg

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
_INT_STR = re.compile(r"^\s*[+-]?\d+\s*$")


def coerce_int(value):
    """Return an int for int / integral float / integer string, else None
    (bools and fractional values are rejected)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str) and _INT_STR.match(value):
        return int(value)
    return None


def _dict(value, key: str, problems: list, label: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        problems.append({"id": f"malformed-{key}", "message": msg("malformed-object", label=label)})
        return {}
    return dict(value)


def _id(value, key: str, problems: list, label: str):
    if value is None or isinstance(value, str):
        return value
    problems.append({"id": f"malformed-{key}", "message": msg("malformed-text", label=label)})
    return None


def _selections(raw, problems: list, label: str) -> dict:
    """choices dict: every value must be a list of strings."""
    raw = _dict(raw, "choices", problems, label)
    clean = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            problems.append({"id": "malformed-choice-selection", "message": msg("malformed-selection-not-list", key=k)})
            continue
        strs = [s for s in v if isinstance(s, str)]
        if len(strs) != len(v):
            problems.append({"id": "malformed-choice-selection", "message": msg("malformed-selection-entries", key=k)})
        clean[k] = strs
    return clean


def normalize_draft(draft) -> tuple[dict, list[dict]]:
    problems: list[dict] = []
    if not isinstance(draft, dict):
        problems.append({"id": "malformed-draft", "message": msg("malformed-draft")})
        return {}, problems
    out = dict(draft)

    if not isinstance(out.get("name"), str):
        if out.get("name") is not None:
            problems.append({"id": "malformed-name", "message": msg("malformed-name")})
        out["name"] = ""

    sources = out.get("sources")
    if sources is not None and not isinstance(sources, list):
        problems.append({"id": "malformed-sources", "message": msg("malformed-sources")})
        out.pop("sources")

    prefs = _dict(out.get("preferences"), "preferences", problems, "preferences")
    use_prereq = prefs.get("usePrerequisites")
    if use_prereq is not None and not isinstance(use_prereq, dict):
        problems.append({"id": "malformed-use-prerequisites", "message": msg("malformed-use-prerequisites")})
        prefs["usePrerequisites"] = {}
    if not isinstance(prefs.get("hitPointType"), str):
        prefs.pop("hitPointType", None)
    out["preferences"] = prefs

    abilities = _dict(out.get("abilities"), "abilities", problems, "abilities")
    base = abilities.get("base")
    if base is not None and not isinstance(base, dict):
        problems.append({"id": "malformed-abilities-base", "message": msg("malformed-abilities-base")})
        base = {}
    base = dict(base or {})
    for ab in ABILITIES:
        if ab not in base:
            continue
        n = coerce_int(base[ab])
        if n is None:
            problems.append({"id": f"ability-invalid-{ab}", "message": msg("ability-invalid-whole", ab=ab, value=base[ab])})
            n = 10
        elif not 1 <= n <= 30:  # W2 / F6: a base score outside 1..30 is clamped and reported
            problems.append({"id": f"ability-out-of-range-{ab}", "message": msg("ability-out-of-range-clamped", ab=ab, n=n, clamped=max(1, min(30, n)))})
            n = max(1, min(30, n))
        base[ab] = n
    abilities["base"] = base
    out["abilities"] = abilities

    classes = out.get("classes")
    if isinstance(classes, list):
        clean_classes = []
        for entry in classes:
            if not isinstance(entry, dict):
                clean_classes.append(entry)  # resolve() reports malformed-class-entry
                continue
            e = dict(entry)
            e["classId"] = _id(e.get("classId"), "class-id", problems, "classId")
            e["subclassId"] = _id(e.get("subclassId"), "subclass-id", problems, "subclassId")
            if "level" in e:
                n = coerce_int(e["level"])
                if n is None:
                    problems.append({"id": "level-unsupported", "message": msg("level-invalid-whole", value=e["level"], cls=e["classId"])})
                    n = 1
                e["level"] = n
            e["choices"] = _selections(e.get("choices"), problems, "class choices")
            clean_classes.append(e)
        out["classes"] = clean_classes

    for key, id_key, label in (("background", "background-id", "background.id"), ("species", "species-id", "species.id")):
        raw = out.get(key)
        if raw is None or not isinstance(raw, dict):
            continue  # resolve() reports malformed-background / malformed-species
        d = dict(raw)
        d["id"] = _id(d.get("id"), id_key, problems, label)
        if key == "species":
            d["subspeciesId"] = _id(d.get("subspeciesId"), "subspecies-id", problems, "species.subspeciesId")
        d["choices"] = _selections(d.get("choices"), problems, f"{key} choices")
        out[key] = d

    equipment = out.get("equipment")
    if equipment is not None and not isinstance(equipment, dict):
        problems.append({"id": "malformed-equipment", "message": msg("malformed-equipment")})
        equipment = {}
    if isinstance(equipment, dict):
        equipment = dict(equipment)
        if isinstance(equipment.get("choices"), dict):
            equipment["choices"] = _selections(equipment["choices"], problems, "equipment choices")
        added = equipment.get("added")
        if isinstance(added, list):
            clean_added = []
            for entry in added:
                if not isinstance(entry, dict):
                    continue
                e = dict(entry)
                if not isinstance(e.get("itemId"), str):
                    continue
                if "qty" in e:
                    n = coerce_int(e["qty"])
                    if n is None or n < 1:
                        problems.append({"id": "equipment-qty-invalid", "message": msg("equipment-qty-invalid", value=e["qty"], item=e["itemId"])})
                        n = 1
                    e["qty"] = n
                clean_added.append(e)
            equipment["added"] = clean_added
        for key, fields in (("worn", ("armor", "shield")), ("wielded", ("main", "off"))):
            raw = equipment.get(key)
            if raw is None:
                equipment.pop(key, None)
                continue
            if not isinstance(raw, dict):
                problems.append({"id": f"malformed-equipment-{key}", "message": msg("malformed-equipment-slot-object", key=key)})
                equipment.pop(key)
                continue
            clean = dict(raw)
            for f in fields:
                v = clean.get(f)
                ok = v is None or isinstance(v, bool) if f == "shield" else v is None or isinstance(v, str)
                if f in clean and not ok:
                    problems.append({"id": f"malformed-equipment-{key}", "message": msg("malformed-equipment-slot-type", key=key, field=f)})
                    clean.pop(f)
            equipment[key] = clean
        out["equipment"] = equipment

    return out, problems
