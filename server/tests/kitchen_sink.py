from __future__ import annotations

"""Shared by the S6 export sweep (test_export_fields.py, test_app.py): fully chosen
real-catalog drafts that put every R/C-slice field on the sheet at once."""
import copy

_BASE = {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}
_WL_INV = "class:warlock:2:invocations:eldritch-invocations"
_WL_INV_2024 = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
_P = "eldritch-invocation-"


def _sub(index, level, ruleset="mixed", sub=None, overrides=None, equip=(), marks=(), origin=None, feats=False):
    spec = {"classes": [(index, level, sub)], "ruleset": ruleset, "overrides": overrides or {},
            "equip": list(equip), "marks": marks}
    if feats:  # FE12: a feat-holding draft (the golden adds it once, under `sources` [])
        spec["feats"] = True
    if origin:  # F3b: (species id, background id) instead of the SRD Human / Acolyte
        spec["origin"] = origin
    return spec


_XPHB_ORIGIN = ("human-xphb", "soldier-xphb")


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
    "warlock7-2024": _sub("warlock", 7, "2024", marks=("classes", "official", "spells"), overrides={
        "class:warlock:spells-cantrips": ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
        _WL_INV_2024: ["opt-pact-of-the-tome-xphb", "opt-pact-of-the-blade-xphb", "opt-thirsting-blade-xphb",
                       "opt-agonizing-blast-xphb", "opt-lessons-of-the-first-ones-xphb", "opt-devils-sight-xphb"],
        "class:warlock:invocation:opt-agonizing-blast-xphb:cantrip": ["eldritch-blast-xphb"],
        "class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon": ["longsword"]},
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
    # F3b: the C6b..C9b / R9 stages, 2024 origin (Human, Soldier) so the origin language card is present
    "rogue6-2024": _sub("rogue", 6, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN, overrides={
        "class:rogue:1:expertise-choice:xphb-rogue-1-expertise": ["skill-stealth", "skill-sleight-of-hand"],
        "class:rogue:6:expertise-choice:xphb-rogue-6-expertise": ["skill-perception", "skill-acrobatics"],
        "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-sleight-of-hand", "skill-perception", "skill-acrobatics"]}),
    "sorcerer17-2024": _sub("sorcerer", 17, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    "cleric7-2024": _sub("cleric", 7, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:cleric:7:feature:xphb-cleric-7-blessed-strikes": ["opt-divine-strike-xphb"]}),
    "wizard20-2024": _sub("wizard", 20, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:wizard:spellbook": ["fireball-xphb", "counterspell-xphb", "fly-xphb", "haste-xphb", "scorching-ray-xphb"],
        "class:wizard:spells-known": ["burning-hands-xphb", "scorching-ray-xphb", "fireball-xphb"],
        "class:wizard:20:signature-spells": ["fireball-xphb", "counterspell-xphb"]}),
    "ranger9-2024": _sub("ranger", 9, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    "barbarian3-2024": _sub("barbarian", 3, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN),
    "fighter4-2024": _sub("fighter", 4, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN),
    # FE12: feat-holding drafts (ASI feat picks as overrides; every feat card is filled with its first option)
    "feats-mixed-fighter14": _sub("fighter", 14, "mixed", marks=("classes", "official"), feats=True, overrides={
        "class:fighter:4:asi": ["feat:alert-phb"], "class:fighter:6:asi": ["feat:tough-phb"],
        "class:fighter:8:asi": ["feat:great-weapon-master-phb"], "class:fighter:12:asi": ["feat:lucky-phb"],
        "class:fighter:14:asi": ["feat:observant-phb"]},
        equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}, {"itemId": "longbow", "qty": 1, "equipped": True}]),
    "feats-2014-rogue16": _sub("rogue", 16, "2014", marks=("classes", "official"), feats=True, overrides={
        "class:rogue:4:asi": ["feat:keen-mind-phb"], "class:rogue:8:asi": ["feat:weapon-master-phb"],
        "class:rogue:10:asi": ["feat:resilient-phb"], "class:rogue:12:asi": ["feat:elemental-adept-phb"],
        "class:rogue:16:asi": ["feat:elemental-adept-phb"]},
        equip=[{"itemId": "rapier", "qty": 1, "equipped": True}]),
    "feats-mixed-wizard8": _sub("wizard", 8, "mixed", marks=("classes", "official", "spells"), feats=True, overrides={
        "class:wizard:4:asi": ["feat:martial-adept-phb"], "class:wizard:8:asi": ["feat:eldritch-adept-tce"]}),
    "feats-2024-fighter19": _sub("fighter", 19, "2024", marks=("classes", "official"), feats=True,
                                 origin=("human-xphb", "criminal-xphb"), overrides={
        "class:fighter:4:asi": ["feat:tough-xphb"], "class:fighter:6:asi": ["feat:great-weapon-master-xphb"],
        "class:fighter:8:asi": ["feat:lucky-xphb"], "class:fighter:12:asi": ["feat:observant-xphb"],
        "class:fighter:14:asi": ["feat:keen-mind-xphb"], "class:fighter:16:asi": ["feat:weapon-master-xphb"],
        "class:fighter:19:asi": ["feat:boon-of-fortitude-xphb"]},
        equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}]),
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
            "species": {"id": spec.get("origin", ("human", "acolyte"))[0], "choices": {}},
            "background": {"id": spec.get("origin", ("human", "acolyte"))[1], "choices": {}},
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
        todo = [c for c in res["choices"] if c["status"] == "pending"]  # F3a: "unavailable" cards cannot be filled
        if not todo:
            return draft
        # spell cards first, then re-resolve: invocation prerequisites (Agonizing Blast needs
        # eldritch blast) read the stored spell picks
        spell_cards = [c for c in todo if ":spells-" in c["id"] and c["options"]]
        # F3b: then proficiency cards, so an Expertise card (options gated to proficient skills) sees them
        prof_cards = [c for c in todo if ("prof-choice" in c["id"] or "proficiency-choice" in c["id"]) and c["options"]]
        for c in spell_cards or prof_cards or todo:
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
