from __future__ import annotations

"""Shared by the S6 export sweep (test_export_fields.py, test_app.py): fully chosen
real-catalog drafts that put every R/C-slice field on the sheet at once."""
import copy

_BASE = {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}
_WL_INV = "class:warlock:2:invocations:eldritch-invocations"
_P = "eldritch-invocation-"


def _sub(index, level, ruleset="mixed", sub=None, overrides=None, equip=(), marks=()):
    return {"classes": [(index, level, sub)], "ruleset": ruleset, "overrides": overrides or {},
            "equip": list(equip), "marks": marks}


# id -> spec. `marks` name the skip markers the draft needs (see needs()).
KITCHEN_SINK: dict[str, dict] = {
    "barbarian20-2014": _sub("barbarian", 20, "2014", marks=("classes",)),
    "barbarian20-2024": _sub("barbarian", 20, "2024", marks=("classes", "official"),
                             equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}]),
    "monk14": _sub("monk", 14, marks=("classes",)),
    "paladin6": _sub("paladin", 6, marks=("classes",)),
    "cleric6": _sub("cleric", 6, marks=("classes",)),
    "warlock17": _sub("warlock", 17, marks=("classes", "spells"), overrides={
        "class:warlock:spells-cantrips": ["eldritch-blast"],
        _WL_INV: [_P + n for n in ("agonizing-blast", "armor-of-shadows", "devils-sight",
                                   "misty-visions", "mask-of-many-faces")]}),
    "fighter10-2024": _sub("fighter", 10, "2024", marks=("classes", "official"), overrides={
        "class:fighter:1:fighting-style": ["feat:dueling-xphb"],
        "class:fighter:weapon-mastery": ["longsword"]},
        equip=[{"itemId": "longsword", "qty": 1, "equipped": True}]),
    "wizard5-2014": _sub("wizard", 5, "2014", marks=("classes",)),
    "wizard5-2024": _sub("wizard", 5, "2024", marks=("classes", "official")),
    "psi-warrior11": _sub("fighter", 11, "mixed", sub="psi-warrior-tce", marks=("classes",)),
    "totem-bear6": _sub("barbarian", 6, "mixed", sub="totem-warrior-phb", marks=("classes",), overrides={
        "class:barbarian:3:feature:totem-warrior-phb-3-totem-spirit": ["totem-warrior-phb-3-totem-spirit--bear"],
        "class:barbarian:6:feature:totem-warrior-phb-6-aspect-of-the-beast": [
            "totem-warrior-phb-6-aspect-of-the-beast--bear"]}),
    "cleric1-thaumaturge-2024": _sub("cleric", 1, "2024", marks=("classes", "official"), overrides={
        "class:cleric:1:divine-order": ["xphb-cleric-1-thaumaturge"]}),
}


def base_draft(spec: dict) -> dict:
    classes = []
    for index, level, sub in spec["classes"]:
        c = {"classId": index, "level": level, "choices": {}}
        if sub:
            c["subclassId"] = sub
        classes.append(c)
    return {"name": "Кухненска мивка", "ruleset": spec["ruleset"], "sources": [],
            "abilities": {"method": "manual", "base": dict(_BASE)},
            "species": {"id": "human", "choices": {}}, "background": {"id": "acolyte", "choices": {}},
            "equipment": {"choices": {}, "added": copy.deepcopy(spec["equip"]), "skipped": False},
            "classes": classes}


def _store(draft: dict, source: dict) -> dict:
    kind = source["kind"]
    if kind == "class":
        return next(c for c in draft["classes"] if c["classId"] == source["id"])["choices"]
    if kind == "background":
        return draft["background"]["choices"]
    if kind == "species":
        return draft["species"]["choices"]
    return draft["equipment"]["choices"]


def fill(draft: dict, catalog, overrides: dict, resolve) -> dict:
    """Pick every pending choice: the override ids first, then the first enabled options."""
    for _ in range(10):
        res = resolve(draft, catalog)
        todo = [c for c in res["choices"] if c["status"] != "resolved"]
        if not todo:
            return draft
        # spell cards first, then re-resolve: invocation prerequisites (Agonizing Blast needs
        # eldritch blast) read the stored spell picks
        spell_cards = [c for c in todo if ":spells-" in c["id"] and c["options"]]
        for c in spell_cards or todo:
            ids = [o["id"] for o in c["options"] if not o.get("disabled")]
            picked = [i for i in overrides.get(c["id"], []) if i in ids]
            picked += [i for i in ids if i not in picked]
            _store(draft, c["source"])[c["id"]] = picked[:c["count"]]
    raise AssertionError("choices did not settle")


def skip_reason(spec: dict) -> str | None:
    """Why the draft cannot run here (missing 5etools data), else None."""
    from catalog import official_source as o
    checks = {"classes": o.has_official_classes, "official": o.has_official, "spells": o.has_official_spells}
    missing = [m for m in spec["marks"] if not checks[m]()]
    return f"5etools data missing: {', '.join(missing)}" if missing else None


def build(sid: str, catalog, resolve) -> dict:
    spec = KITCHEN_SINK[sid]
    return fill(base_draft(spec), catalog, spec["overrides"], resolve)
