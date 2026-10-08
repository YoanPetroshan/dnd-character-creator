"""normalize_draft(draft) -> (clean_draft, problems)

A type-coercion pass run at the top of resolve(). The draft arrives as
arbitrary JSON (hand-edited, imported, or stale from localStorage), so
this guarantees every container resolve() reads has the expected JSON
type, and reports every value it had to replace instead of silently
guessing. It never mutates its input.
"""
from __future__ import annotations

import re

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
        problems.append({"id": f"malformed-{key}", "message": f"'{label}' must be an object; it was ignored."})
        return {}
    return dict(value)


def _id(value, key: str, problems: list, label: str):
    if value is None or isinstance(value, str):
        return value
    problems.append({"id": f"malformed-{key}", "message": f"'{label}' must be text; it was ignored."})
    return None


def _selections(raw, problems: list, label: str) -> dict:
    """choices dict: every value must be a list of strings."""
    raw = _dict(raw, "choices", problems, label)
    clean = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            problems.append({"id": "malformed-choice-selection", "message": f"The selection for '{k}' must be a list; it was ignored."})
            continue
        strs = [s for s in v if isinstance(s, str)]
        if len(strs) != len(v):
            problems.append({"id": "malformed-choice-selection", "message": f"Non-text entries in the selection for '{k}' were ignored."})
        clean[k] = strs
    return clean


def normalize_draft(draft) -> tuple[dict, list[dict]]:
    problems: list[dict] = []
    if not isinstance(draft, dict):
        problems.append({"id": "malformed-draft", "message": "The draft must be a JSON object; it was ignored."})
        return {}, problems
    out = dict(draft)

    if not isinstance(out.get("name"), str):
        if out.get("name") is not None:
            problems.append({"id": "malformed-name", "message": "'name' must be text; it was ignored."})
        out["name"] = ""

    sources = out.get("sources")
    if sources is not None and not isinstance(sources, list):
        problems.append({"id": "malformed-sources", "message": "'sources' must be a list; it was ignored."})
        out.pop("sources")

    prefs = _dict(out.get("preferences"), "preferences", problems, "preferences")
    use_prereq = prefs.get("usePrerequisites")
    if use_prereq is not None and not isinstance(use_prereq, dict):
        problems.append({"id": "malformed-use-prerequisites", "message": "'preferences.usePrerequisites' must be an object; it was ignored."})
        prefs["usePrerequisites"] = {}
    if not isinstance(prefs.get("hitPointType"), str):
        prefs.pop("hitPointType", None)
    out["preferences"] = prefs

    abilities = _dict(out.get("abilities"), "abilities", problems, "abilities")
    base = abilities.get("base")
    if base is not None and not isinstance(base, dict):
        problems.append({"id": "malformed-abilities-base", "message": "'abilities.base' must be an object; it was ignored."})
        base = {}
    base = dict(base or {})
    for ab in ABILITIES:
        if ab not in base:
            continue
        n = coerce_int(base[ab])
        if n is None:
            problems.append({"id": f"ability-invalid-{ab}", "message": f"{ab} score {base[ab]!r} isn't a valid whole number; using 10 instead."})
            n = 10
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
                    problems.append({"id": "level-unsupported", "message": f"Level {e['level']!r} for '{e['classId']}' isn't a valid whole number; using 1 instead."})
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
        problems.append({"id": "malformed-equipment", "message": "'equipment' must be an object; it was ignored."})
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
                        problems.append({"id": "equipment-qty-invalid", "message": f"Quantity {e['qty']!r} for '{e['itemId']}' isn't a positive whole number; using 1 instead."})
                        n = 1
                    e["qty"] = n
                clean_added.append(e)
            equipment["added"] = clean_added
        out["equipment"] = equipment

    return out, problems
