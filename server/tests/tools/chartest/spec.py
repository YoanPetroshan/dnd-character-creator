"""Character specs (JSON-line) and the deterministic filler that turns a spec into a fully chosen draft."""
from __future__ import annotations

import copy
import json
import random
from dataclasses import asdict, dataclass, field

RULESETS = ("2014", "2024", "mixed")
ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
POINT_BUY = [15, 14, 13, 12, 10, 8]  # costs 9+7+5+4+2+0 = 27
ROLLED = [17, 15, 14, 12, 10, 8]


@dataclass
class CharSpec:
    id: str
    ruleset: str = "mixed"
    classes: list = field(default_factory=lambda: [["fighter", 1, None]])  # [[class, level, subclass|None]]
    species: str | None = None  # None -> the ruleset default (human / human-xphb)
    subspecies: str | None = None
    background: str | None = None
    abilities: dict = field(default_factory=lambda: {"method": "manual", "base": None, "priority": []})
    hp: dict = field(default_factory=lambda: {"type": "fixed", "rolls": None})  # rolls: None | "seed:N" | {level: roll}
    sources: list = field(default_factory=list)
    overrides: dict = field(default_factory=dict)
    equip: list = field(default_factory=list)  # [{"itemId", "qty", "equipped"}]
    filler: dict = field(default_factory=lambda: {"mode": "first", "seed": 0})  # first | last | seeded | alldiff
    prereqs: bool = False  # preferences.usePrerequisites {multiclass, feats}
    tags: list = field(default_factory=list)
    weird: dict = field(default_factory=dict)  # weird.py mutations, see weird.apply
    name: str = "Тестов герой"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_json(text: str | dict) -> "CharSpec":
        data = json.loads(text) if isinstance(text, str) else dict(text)
        known = {f for f in CharSpec.__dataclass_fields__}
        return CharSpec(**{k: v for k, v in data.items() if k in known})

    @property
    def total_level(self) -> int:
        return sum(c[1] for c in self.classes)


def default_origin(ruleset: str) -> tuple[str, str]:
    return ("human-xphb", "soldier-xphb") if ruleset == "2024" else ("human", "acolyte")


def ability_scores(abilities: dict) -> dict:
    """Base scores of a spec: an explicit ``base`` dict wins, else the method's array assigned by ``priority``."""
    if abilities.get("base"):
        return {a: int(abilities["base"].get(a, 10)) for a in ABILITIES}
    arr = {"standard": STANDARD_ARRAY, "pointbuy": POINT_BUY, "roll": ROLLED}.get(abilities.get("method"), STANDARD_ARRAY)
    order = list(abilities.get("priority") or []) + [a for a in ("CON", "DEX", "WIS", "STR", "INT", "CHA") if a not in (abilities.get("priority") or [])]
    seen: list[str] = []
    for a in order:
        if a not in seen:
            seen.append(a)
    return {a: arr[i] for i, a in enumerate(seen)}


def base_draft(spec: CharSpec) -> dict:
    sp, bg = default_origin(spec.ruleset)
    classes = []
    for index, level, sub in spec.classes:
        c = {"classId": index, "level": level, "choices": {}}
        if sub:
            c["subclassId"] = sub
        classes.append(c)
    species = {"id": spec.species or sp, "choices": {}}
    if spec.subspecies:
        species["subspeciesId"] = spec.subspecies
    method = spec.abilities.get("method", "manual")
    draft = {"name": spec.name, "ruleset": spec.ruleset, "sources": list(spec.sources),
             "abilities": {"method": method, "base": ability_scores(spec.abilities)},
             "species": species, "background": {"id": spec.background or bg, "choices": {}},
             "equipment": {"choices": {}, "added": copy.deepcopy(spec.equip), "skipped": False},
             "classes": classes, "preferences": {"hitPointType": spec.hp.get("type", "fixed")}}
    if spec.prereqs:
        draft["preferences"]["usePrerequisites"] = {"multiclass": True, "feats": True}
    rolls = spec.hp.get("rolls")
    if spec.hp.get("type") == "manual" and rolls is not None:
        for i, c in enumerate(classes):
            die = {"barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10, "bard": 8, "cleric": 8, "druid": 8,
                   "monk": 8, "rogue": 8, "warlock": 8, "sorcerer": 6, "wizard": 6}.get(c["classId"], 8)
            if isinstance(rolls, dict):
                c["hpRolls"] = {str(k): v for k, v in rolls.items()}
            else:
                rng = random.Random(f"{spec.id}:{rolls}:{i}")
                c["hpRolls"] = {str(l): rng.randint(1, die) for l in range(1, c["level"] + 1)}
    return draft


def _store(draft: dict, source: dict, cid: str) -> dict:
    """Same routing as kitchen_sink._store (frontend ClassPage / SpeciesPage / BackgroundPage)."""
    import kitchen_sink as ks
    return ks._store(draft, source, cid)


class FillStuck(AssertionError):
    """The filler could not settle every pending card (a legal draft that cannot be finished)."""


def fill(draft: dict, catalog, resolve, filler: dict, overrides: dict | None = None) -> dict:
    """Fill every pending card. Order mirrors kitchen_sink.fill (spell cards, then proficiency cards, then the rest)."""
    mode = filler.get("mode", "first")
    rng = random.Random(filler.get("seed", 0))
    overrides = overrides or {}
    used: set[str] = set()
    for _ in range(12):
        res = resolve(draft, catalog)
        todo = [c for c in res["choices"] if c["status"] == "pending"]
        if not todo:
            return draft
        spell_cards = [c for c in todo if ":spells-" in c["id"] and c["options"]]
        prof_cards = [c for c in todo if ("prof-choice" in c["id"] or "proficiency-choice" in c["id"]) and c["options"]]
        for c in spell_cards or prof_cards or todo:
            ids = [o["id"] for o in c["options"] if not o.get("disabled")]
            picked = [i for i in overrides.get(c["id"], []) if i in ids]
            rest = [i for i in ids if i not in picked]
            if mode == "last":
                rest.reverse()
            elif mode == "seeded":
                rng.shuffle(rest)
            elif mode == "alldiff":
                rest = [i for i in rest if i not in used] + [i for i in rest if i in used]
            picked = (picked + rest)[:c["count"]]
            used.update(picked)
            _store(draft, c["source"], c["id"])[c["id"]] = picked
    stuck = [c["id"] for c in resolve(draft, catalog)["choices"] if c["status"] == "pending"]
    raise FillStuck(f"choices did not settle: {stuck[:6]}")


def build_draft(spec: CharSpec, catalog, resolve) -> dict:
    return fill(base_draft(spec), catalog, resolve, spec.filler, spec.overrides)


def resolve_spec(spec: CharSpec, catalog, resolve=None):
    """(draft, resolution) of a spec. The ONLY place the harness calls the engine besides weird.py's export probes."""
    if resolve is None:
        from engine.resolve import resolve
    draft = build_draft(spec, catalog, resolve)
    if spec.weird:
        from . import weird
        weird.apply(spec, draft)
    return draft, resolve(draft, catalog)


def load_catalog():
    from catalog.loader import load
    return load()


def have_data() -> bool:
    from catalog import official_source as o
    return bool(o.has_official() and o.has_official_classes())
