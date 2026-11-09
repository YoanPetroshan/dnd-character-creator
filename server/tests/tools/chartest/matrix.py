"""Deterministic tier lists. ``generate(tier, seed, n=None, catalog=None)`` -> list[CharSpec]; same arguments, same specs.

T1 single class (180), T2 two classes (150), T3 targeted hand-written cases (about 60), T4 three classes (9).
Species / background / subclass choices walk global round-robin pointers so every class, subclass, species and
background appears somewhere in T1..T4 (``coverage`` reports what is left)."""
from __future__ import annotations

import random

from .spec import CharSpec, load_catalog

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"]
RULESETS = ["2014", "2024", "mixed"]
LEVEL_POOLS = [[1, 3, 5, 11, 20], [2, 4, 7, 12, 17], [1, 6, 9, 15, 20], [3, 5, 8, 13, 19]]
METHODS = ["standard", "pointbuy", "roll", "manual"]
FILLERS = ["first", "seeded", "last", "alldiff"]
PRIMARY = {  # abilities a class needs at 13 to multiclass into / out of (PHB 2014 p.163, PHB 2024 primary abilities)
    "barbarian": ["STR"], "bard": ["CHA"], "cleric": ["WIS"], "druid": ["WIS"], "fighter": ["STR"],  # fighter: STR or DEX
    "monk": ["DEX", "WIS"], "paladin": ["STR", "CHA"], "ranger": ["DEX", "WIS"], "rogue": ["DEX"],
    "sorcerer": ["CHA"], "warlock": ["CHA"], "wizard": ["INT"]}
SPLITS = [(1, 1), (3, 2), (2, 3), (5, 5), (6, 2), (10, 10), (1, 19), (19, 1), (4, 3), (11, 9)]
NAMED_PAIRS = [("paladin", "warlock"), ("sorcerer", "warlock"), ("fighter", "wizard"), ("rogue", "ranger"), ("ranger", "sorcerer"),
               ("barbarian", "monk"), ("monk", "sorcerer"), ("fighter", "barbarian"), ("fighter", "paladin"), ("cleric", "druid"),
               ("bard", "paladin"), ("wizard", "cleric"), ("warlock", "bard"), ("rogue", "fighter"), ("cleric", "paladin")]
SUB_HINT = {  # named pair members that want a specific subclass (by record name)
    ("fighter", "wizard"): ["Eldritch Knight", None], ("rogue", "ranger"): ["Arcane Trickster", None],
    ("monk", "sorcerer"): [None, "Draconic Sorcery"], ("fighter", "barbarian"): ["Eldritch Knight", None]}
_SALT = {"T1": 11, "T2": 22, "T3": 33, "T4": 44}


class Pools:
    def __init__(self, catalog):
        from catalog.reference_data import ruleset_allows, subclass_unlock_level  # generator only; the oracle never does this
        self.allows, self.unlock = ruleset_allows, subclass_unlock_level
        self.subs = {c: [] for c in CLASSES}
        for k in sorted(catalog.subclasses):
            r = catalog.subclasses[k]
            self.subs[r["class"]["index"]].append(r)
        self.races = [catalog.races[k] for k in sorted(catalog.races)]
        self.subraces = {k: v for k, v in catalog.subraces.items()}
        self.backgrounds = [catalog.backgrounds[k] for k in sorted(catalog.backgrounds)]
        self.species_combos: list[tuple[dict, dict | None]] = [(r, None) for r in self.races]
        for r in self.races:
            for sr in r.get("subraces", []) or []:
                rec = self.subraces.get(sr.get("index") if isinstance(sr, dict) else sr)
                if rec:
                    self.species_combos.append((r, rec))
        self.ptr = {"species": 0, "background": 0}
        self.seen = {"species": set(), "background": set()}
        self.sub_ptr = {c: 0 for c in CLASSES}
        self.used = {"species": set(), "background": set(), "subclass": set(), "class": set(), "subspecies": set()}

    def _next(self, key, items, ok):
        """First allowed item at or after the pointer that no spec used yet; else the first allowed one (cycling)."""
        n = len(items)
        start = self.ptr[key]
        first_ok = None
        for d in range(n):
            i = (start + d) % n
            if not ok(items[i]):
                continue
            first_ok = first_ok if first_ok is not None else i
            ident = items[i][0]["index"] + ("/" + items[i][1]["index"] if items[i][1] else "") if isinstance(items[i], tuple) else items[i]["index"]
            if ident not in self.seen[key]:
                self.seen[key].add(ident)
                self.ptr[key] = i + 1
                return items[i]
        i = first_ok if first_ok is not None else start % n
        self.ptr[key] = i + 1
        return items[i]

    def species(self, ruleset: str, srd_only: bool):
        def ok(c):
            r, sr = c
            return self.allows(r, "species", ruleset) and (sr is None or self.allows(sr, "species", ruleset)) and \
                (not srd_only or (r.get("source") in (None, "SRD", "PHB") and r["index"] in _SRD_RACES))
        r, sr = self._next("species", self.species_combos, ok)
        self.used["species"].add(r["index"])
        if sr:
            self.used["subspecies"].add(sr["index"])
        return r["index"], (sr["index"] if sr else None)

    def background(self, ruleset: str, srd_only: bool):
        r = self._next("background", self.backgrounds,
                       lambda b: self.allows(b, "background", ruleset) and (not srd_only or b["index"] == "acolyte"))
        self.used["background"].add(r["index"])
        return r["index"]

    def subclass(self, cls: str, level: int, ruleset: str, srd_only: bool = False, want: str | None = None):
        unlock = self.unlock(cls, ruleset)
        if unlock is None or level < unlock:
            return None
        pool = self.subs[cls]
        if want:
            for r in pool:
                if r["name"] == want and self.allows(r, "subclass", ruleset) and (ruleset == "2024") == (r.get("ruleset") == "2024"):
                    self.used["subclass"].add(r["index"])
                    return r["index"]
        def ok(r):
            return self.allows(r, "subclass", ruleset) and (not srd_only or r.get("source") == "SRD") and \
                (ruleset != "2014" or r.get("ruleset") != "2024")
        cands = [r for r in pool[self.sub_ptr[cls] % len(pool):] + pool[:self.sub_ptr[cls] % len(pool)] if ok(r)]
        if not cands:
            return None
        r = next((r for r in cands if r["index"] not in self.used["subclass"]), cands[0])
        self.sub_ptr[cls] = pool.index(r) + 1
        self.used["subclass"].add(r["index"])
        return r["index"]


_SRD_RACES = {"dwarf", "elf", "halfling", "human", "dragonborn", "gnome", "half-elf", "half-orc", "tiefling"}


def _abilities(classes, i: int, method: str):
    prim: list[str] = []
    need = []
    for c, _l, _s in classes:
        need += PRIMARY[c]
    for a in need + ["CON", "DEX"]:
        if a not in prim:
            prim.append(a)
    if len(classes) > 1:
        base = {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}
        for a in need:
            base[a] = 14
        base["CON"] = max(base["CON"], 14)
        if "fighter" in [c[0] for c in classes] and base["STR"] < 13 and base["DEX"] < 13:
            base["STR"] = 14
        return {"method": "manual", "base": base, "priority": []}
    if method == "manual":
        return {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}, "priority": []}
    return {"method": method, "base": None, "priority": prim}


def _make(pools: Pools, tier: str, n: int, ruleset: str, classes_in, i: int, seed: int, tags=(), hints=None) -> CharSpec:
    srd_only = (n % 9 == 0) and len(classes_in) == 1
    classes = []
    for k, (c, lvl) in enumerate(classes_in):
        want = hints[k] if hints and k < len(hints) else None
        classes.append([c, lvl, pools.subclass(c, lvl, ruleset, srd_only, want)])
    sp, sub = pools.species(ruleset, srd_only)
    bg = pools.background(ruleset, srd_only)
    method = METHODS[(n + i) % 4]
    hp_manual = n % 3 == 1
    for c, _l, _s in classes:
        pools.used["class"].add(c)
    return CharSpec(
        id=f"{tier.lower()}-{n:03d}-" + "-".join(f"{c[0][:3]}{c[1]}" for c in classes) + f"-{ruleset}",
        ruleset=ruleset, classes=classes, species=sp, subspecies=sub, background=bg,
        abilities=_abilities(classes, i, method),
        hp={"type": "manual" if hp_manual else "fixed", "rolls": f"seed:{seed + n}" if hp_manual else None},
        sources=["srd"] if srd_only else [], filler={"mode": FILLERS[n % 4], "seed": seed + n},
        prereqs=len(classes) > 1 and n % 2 == 0, tags=[tier, *tags])


def _t1(pools, seed):
    out, n = [], 0
    for ci, cls in enumerate(CLASSES):
        for ri, rs in enumerate(RULESETS):
            for li, lvl in enumerate(LEVEL_POOLS[(ci + ri) % 4]):
                out.append(_make(pools, "T1", n, rs, [(cls, lvl)], li, seed))
                n += 1
    return out


def _all_pairs():
    pairs = list(NAMED_PAIRS)
    for a in CLASSES:
        for b in CLASSES:
            if a != b and (a, b) not in pairs and len(pairs) < 30 and (hash_pair(a, b) % 4 == 0):
                pairs.append((a, b))
    for a in CLASSES:  # top up deterministically
        for b in CLASSES:
            if a != b and (a, b) not in pairs and len(pairs) < 30:
                pairs.append((a, b))
    return pairs


def hash_pair(a, b):
    return sum(map(ord, a)) * 31 + sum(map(ord, b))


def _t2(pools, seed):
    out, n = [], 0
    for pi, (a, b) in enumerate(_all_pairs()):
        for k in range(5):
            la, lb = SPLITS[(pi + 2 * k) % 10]
            rs = RULESETS[(pi + k) % 3]
            out.append(_make(pools, "T2", n, rs, [(a, la), (b, lb)], k, seed, hints=SUB_HINT.get((a, b))))
            n += 1
    return out


def _t4(pools, seed):
    combos = [[("fighter", 5), ("rogue", 4), ("wizard", 3)], [("paladin", 6), ("warlock", 3), ("sorcerer", 3)],
              [("barbarian", 5), ("monk", 5), ("cleric", 2)]]
    hints = [["Eldritch Knight", "Arcane Trickster", None], [None, None, None], [None, None, None]]
    out, n = [], 0
    for ci, combo in enumerate(combos):
        for rs in RULESETS:
            out.append(_make(pools, "T4", n, rs, combo, ci, seed, hints=hints[ci]))
            n += 1
    return out


def _t3(pools, seed):
    """Targeted special cases. Each entry: (tag, ruleset, [(class, level)], extra CharSpec fields)."""
    P = []

    def add(tag, rs, classes, **kw):
        P.append((tag, rs, classes, kw))

    base16 = {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}
    for rs in RULESETS:
        add("warlock-invocations", rs, [("warlock", 12)])
        add("warlock-mystic-arcanum", rs, [("warlock", 17)])
    for rs in ("2014", "2024"):
        add("metamagic-counts", rs, [("sorcerer", 17)])
        add("spellbook-size", rs, [("wizard", 20)])
        add("monk-armor-shield", rs, [("monk", 5)], equip=[{"itemId": "chain-mail", "qty": 1, "equipped": True}, {"itemId": "shield", "qty": 1, "equipped": True}])
        add("barbarian-armor-shield", rs, [("barbarian", 7)], equip=[{"itemId": "half-plate", "qty": 1, "equipped": True}, {"itemId": "shield", "qty": 1, "equipped": True}])
        add("paladin-ranger-rounding", rs, [("paladin", 5), ("ranger", 5)])
        add("paladin-ranger-rounding-3-3", rs, [("paladin", 3), ("ranger", 3)])
        add("eldritch-knight-levels", rs, [("fighter", 3)], hints=["Eldritch Knight"])
        add("eldritch-knight-levels-19", rs, [("fighter", 19)], hints=["Eldritch Knight"])
        add("arcane-trickster-levels", rs, [("rogue", 3)], hints=["Arcane Trickster"])
        add("arcane-trickster-levels-13", rs, [("rogue", 13)], hints=["Arcane Trickster"])
        add("extra-attack-no-stack", rs, [("fighter", 5), ("paladin", 5)])
        add("thirsting-blade", rs, [("warlock", 5)])
        add("feat-asi-caps", rs, [("fighter", 12)], abilities={"method": "manual", "base": {"STR": 19, "DEX": 19, "CON": 19, "INT": 8, "WIS": 8, "CHA": 8}, "priority": []})
        add("half-feat-at-cap", rs, [("fighter", 8)], abilities={"method": "manual", "base": {"STR": 20, "DEX": 20, "CON": 20, "INT": 8, "WIS": 8, "CHA": 8}, "priority": []})
        add("heavy-armor-under-str", rs, [("fighter", 3)], abilities={"method": "manual", "base": {"STR": 8, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}, "priority": []},
            equip=[{"itemId": "plate", "qty": 1, "equipped": True}])
        add("duplicate-proficiencies", rs, [("rogue", 3), ("bard", 2)])
        add("duplicate-proficiencies-2", rs, [("ranger", 3), ("rogue", 1)])
        add("rolled-hp-edge-min", rs, [("wizard", 10)], hp={"type": "manual", "rolls": {str(l): 1 for l in range(1, 11)}})
        add("rolled-hp-edge-max", rs, [("barbarian", 10)], hp={"type": "manual", "rolls": {str(l): 12 for l in range(1, 11)}})
        add("rolled-hp-edge-invalid", rs, [("fighter", 6)], hp={"type": "manual", "rolls": {"2": 0, "3": 11, "4": 10, "5": 1}})
        add("narrow-sources-srd", rs, [("cleric", 5)], sources=["srd"])
        add("narrow-sources-phb", rs, [("druid", 5)], sources=["phb"])
        add("prereq-negative", rs, [("paladin", 3), ("wizard", 2)], prereqs=True, abilities={"method": "manual", "base": {"STR": 8, "DEX": 10, "CON": 12, "INT": 14, "WIS": 10, "CHA": 10}, "priority": []})
        add("prereq-negative-2", rs, [("monk", 2), ("ranger", 2)], prereqs=True, abilities={"method": "manual", "base": {"STR": 10, "DEX": 15, "CON": 12, "INT": 10, "WIS": 9, "CHA": 10}, "priority": []})
        add("ability-limits-high", rs, [("barbarian", 20)], abilities={"method": "manual", "base": {"STR": 20, "DEX": 20, "CON": 20, "INT": 20, "WIS": 20, "CHA": 20}, "priority": []})
        add("ability-limits-low", rs, [("wizard", 4)], abilities={"method": "manual", "base": {"STR": 3, "DEX": 3, "CON": 3, "INT": 3, "WIS": 3, "CHA": 3}, "priority": []})
    for rs in ("2024",):
        add("background-only-asi", rs, [("cleric", 4)])
        add("background-only-asi-2", rs, [("rogue", 8)])
    add("level-1-all-low", "mixed", [("sorcerer", 1)], abilities={"method": "manual", "base": {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}, "priority": []})
    add("level-20-capstone", "mixed", [("monk", 20)])
    add("wis-multiclass-prereq", "mixed", [("cleric", 5), ("druid", 5)])
    add("fighter-dex-multiclass", "2014", [("fighter", 1), ("rogue", 1)], abilities={"method": "manual", "base": {"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}, "priority": []}, prereqs=True)
    out = []
    for n, (tag, rs, classes, kw) in enumerate(P):
        kw = dict(kw)
        hints = kw.pop("hints", None)
        spec = _make(pools, "T3", n, rs, classes, n, seed, tags=[tag], hints=hints)
        for k, v in kw.items():
            setattr(spec, k, v)
        if tag.startswith("prereq-negative") or "multiclass" in tag or tag == "fighter-dex-multiclass":
            spec.prereqs = kw.get("prereqs", True)
        if "prereq-negative" in tag:
            spec.tags.append("prereq-negative")
        spec.id = f"t3-{n:03d}-{tag}-{rs}"
        out.append(spec)
    return out


_BUILDERS = {"T1": _t1, "T2": _t2, "T3": _t3, "T4": _t4}
TIERS = list(_BUILDERS)


def generate(tier: str, seed: int = 0, n: int | None = None, catalog=None) -> list[CharSpec]:
    catalog = catalog or load_catalog()
    pools = Pools(catalog)
    pools.ptr["species"] = _SALT[tier] * 7 + seed
    pools.ptr["background"] = _SALT[tier] * 5 + seed
    specs = _BUILDERS[tier](pools, seed)
    return specs[:n] if n else specs


def generate_all(seed: int = 0, catalog=None) -> dict[str, list[CharSpec]]:
    """All tiers with shared pointers (best coverage); tier order T3, T4, T2, T1 like the campaign."""
    catalog = catalog or load_catalog()
    pools = Pools(catalog)
    out = {}
    for t in ("T3", "T4", "T2", "T1"):
        out[t] = _BUILDERS[t](pools, seed)
    out["_pools"] = pools
    return out


def batch(tier: str, number: int, size: int = 10, seed: int = 0, catalog=None) -> list[CharSpec]:
    """Batch N (0-based) of ``size`` specs of a tier."""
    specs = generate(tier, seed, catalog=catalog)
    return specs[number * size:(number + 1) * size]


def coverage(catalog=None, seed: int = 0) -> dict:
    """What generate_all leaves uncovered: {kind: sorted ids}."""
    catalog = catalog or load_catalog()
    allt = generate_all(seed, catalog)
    pools = allt.pop("_pools")
    want = {"class": set(CLASSES), "species": set(catalog.races), "background": set(catalog.backgrounds),
            "subclass": set(catalog.subclasses)}
    return {k: sorted(v - pools.used[k]) for k, v in want.items()}
