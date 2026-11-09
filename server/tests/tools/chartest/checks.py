"""The ORACLE. Recomputes sheet numbers from the raw vendored data and compares them with a resolution.

Independence rule: this module imports NOTHING from the engine (no ``engine``, ``catalog``, ``export``...). It reads
the raw JSON in server/data/official (5etools) and chargen/data/srd (SRD) with ``json``, and the draft/resolution it is
given. Each check is a small function registered with a rule id; it returns a list of results
``{check, ok, expected, actual, cite}`` (no result = not applicable). ``run_checks(draft, res)`` runs them all.
"""
from __future__ import annotations

import functools
import json
import math
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[4]
OFFICIAL = ROOT / "server" / "data" / "official"
SRD = ROOT / "chargen" / "data" / "srd"
PHB_MD = pathlib.Path(os.environ.get("CHARTEST_PHB_MD", "")) if os.environ.get("CHARTEST_PHB_MD") else None

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
CLASSES = ("barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
           "sorcerer", "warlock", "wizard")
SKILL_ABILITY = {  # PHB 2014 p.174 / PHB 2024 p.27 (skills and the ability each one uses)
    "skill-acrobatics": "DEX", "skill-animal-handling": "WIS", "skill-arcana": "INT", "skill-athletics": "STR",
    "skill-deception": "CHA", "skill-history": "INT", "skill-insight": "WIS", "skill-intimidation": "CHA",
    "skill-investigation": "INT", "skill-medicine": "WIS", "skill-nature": "INT", "skill-perception": "WIS",
    "skill-performance": "CHA", "skill-persuasion": "CHA", "skill-religion": "INT", "skill-sleight-of-hand": "DEX",
    "skill-stealth": "DEX", "skill-survival": "WIS"}
ARMOR_STR = {"scale-mail": None}


def available() -> bool:
    return (OFFICIAL / "class" / "class-fighter.json").exists() and (SRD / "5e-SRD-Levels.json").exists()


# ---------------------------------------------------------------- raw data
@functools.lru_cache(maxsize=None)
def _json(path: str):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def raw_class_file(name: str) -> dict:
    return _json(str(OFFICIAL / "class" / f"class-{name}.json"))


def edition_source(ruleset: str) -> str:
    return "XPHB" if ruleset == "2024" else "PHB"


def raw_class(name: str, ruleset: str) -> dict | None:
    src = edition_source(ruleset)
    for c in raw_class_file(name)["class"]:
        if c["name"].lower() == name and c["source"] == src:
            return c
    return None


def raw_subclass(cls: str, sub_name: str | None, ruleset: str) -> dict | None:
    """The fullest raw record of that name (5etools also has _copy stubs), the edition's book first."""
    if not sub_name:
        return None
    cands = [s for s in raw_class_file(cls).get("subclass", []) if s["name"].lower() == sub_name.lower() and "_copy" not in s]
    cands.sort(key=lambda s: ((s["source"] in ("XPHB", "FRHoF")) != (ruleset == "2024"), -len(s)))
    return cands[0] if cands else None


def raw_subclass_features(cls: str, sub: dict | None) -> list[dict]:
    if not sub:
        return []
    return [f for f in raw_class_file(cls).get("subclassFeature", [])
            if f.get("subclassShortName") == sub["shortName"] and f.get("subclassSource") == sub["source"]]


@functools.lru_cache(maxsize=None)
def srd_levels() -> dict:
    out = {}
    for row in _json(str(SRD / "5e-SRD-Levels.json")):
        out[(row["class"]["index"], row["level"])] = row if "subclass" not in row else out.get((row["class"]["index"], row["level"]), row)
    return out


@functools.lru_cache(maxsize=None)
def base_items() -> dict:
    out = {}
    for i in _json(str(OFFICIAL / "items-base.json"))["baseitem"]:
        out.setdefault(i["name"].lower(), {})[i["source"]] = i
    return out


def item_by_id(item_id: str, ruleset: str) -> dict | None:
    """Engine item ids are kebab-case names ('scale-mail', 'half-plate')."""
    names = base_items()
    key = item_id.replace("-", " ")
    for name, by_src in names.items():
        if name.replace("'", "").replace(",", "") == key or name.replace(" armor", "") == key or name == key:
            return by_src.get(edition_source(ruleset)) or by_src.get("PHB") or next(iter(by_src.values()))
    return None


@functools.lru_cache(maxsize=None)
def raw_races() -> dict:
    return _json(str(OFFICIAL / "races.json"))


def raw_feat(name: str, ruleset: str) -> dict | None:
    cands = [f for f in _json(str(OFFICIAL / "feats.json"))["feat"] if f["name"].lower() == name.lower()]
    pref = edition_source(ruleset)
    return next((f for f in cands if f["source"] == pref), cands[0] if cands else None)


# ---------------------------------------------------------------- helpers
def mod(score: int) -> int:
    return (score - 10) // 2


def ordinal(v) -> int:
    if isinstance(v, int):
        return v
    m = re.search(r"(\d+)(?:st|nd|rd|th)", str(v))
    return int(m.group(1)) if m else int(re.search(r"\d+", str(v)).group())


def cell_value(v):
    """A class-table cell as a number/str: dice dict -> 'NdM', bonus dict -> value, '{@...}' -> text."""
    if isinstance(v, dict):
        if v.get("type") == "dice":
            t = v["toRoll"][0]
            return f"{t['number']}d{t['faces']}"
        return v.get("value")
    return v


def table_column(raw: dict, label: str, source: str = "class") -> list | None:
    """Values per level of the class-table column whose label contains ``label`` (case-insensitive)."""
    groups = raw.get("classTableGroups") if source == "class" else raw.get("subclassTableGroups")
    for g in groups or []:
        for i, lab in enumerate(g.get("colLabels", [])):
            if label.lower() in re.sub(r"\{@\w+ ([^|}]*).*?\}", r"\1", lab).lower() and "rows" in g:
                return [cell_value(row[i]) for row in g["rows"]]
    return None


def slot_rows(raw: dict, subclass: bool = False) -> list | None:
    for g in (raw.get("subclassTableGroups") if subclass else raw.get("classTableGroups")) or []:
        if "rowsSpellProgression" in g:
            return g["rowsSpellProgression"]
    return None


class Ctx:
    def __init__(self, draft: dict, res: dict):
        self.draft, self.res = draft, res
        self.sheet, self.der = res["sheet"], res["derived"]
        self.ruleset = draft.get("ruleset", "mixed")
        self.classes = [(c["id"], c["level"], (c.get("subclass") or {}).get("name") if isinstance(c.get("subclass"), dict) else c.get("subclass"))
                        for c in self.sheet["classes"]]
        self.level = sum(c[1] for c in self.classes)
        self.ab = self.sheet["abilities"]
        self.mods = {a: mod(self.ab[a]) for a in ABILITIES}
        self.pb = 2 + (self.level - 1) // 4
        self.raw = [raw_class(c[0], self.ruleset) for c in self.classes]
        self.sub = [raw_subclass(c[0], c[2], self.ruleset) for c in self.classes]
        self.feat_names = {f["name"].lower() for f in self.sheet.get("feats", [])}
        self.feature_names = {f["name"].lower() for f in self.sheet.get("features", [])}
        self.prefs = draft.get("preferences") or {}
        picks = [v for c in draft["classes"] for vs in (c.get("choices") or {}).values() if isinstance(vs, list) for v in vs]
        self.thaumaturge = any(isinstance(v, str) and ("thaumaturge" in v or "magician" in v) for v in picks)

    def has_feat(self, name: str) -> bool:
        return name.lower() in self.feat_names

    def class_level(self, cid: str) -> int:
        return sum(c[1] for c in self.classes if c[0] == cid)

    def subclass_is(self, cid: str, short: str) -> bool:
        return any(c[0] == cid and c[2] and short in c[2].lower() for c in self.classes)


REGISTRY: list[tuple[str, callable]] = []


def check(rule: str):
    def deco(fn):
        REGISTRY.append((rule, fn))
        fn.rule = rule
        return fn
    return deco


def R(rule, ok, expected, actual, cite):
    return {"check": rule, "ok": bool(ok), "expected": expected, "actual": actual, "cite": cite}


def _subset_sums(options: list[int]) -> set[int]:
    sums = {0}
    for o in options:
        sums |= {s + o for s in sums}
    return sums


# ---------------------------------------------------------------- checks
@check("PB")
def c_pb(x: Ctx):
    cite = "PHB 2014 p.15 / PHB 2024 p.27: proficiency bonus = 2 + (total level - 1) // 4; SRD Levels prof_bonus"
    exp = x.pb
    if len(x.classes) == 1:
        row = srd_levels().get((x.classes[0][0], x.level))
        if row:
            exp = row["prof_bonus"]
            cite = f"chargen/data/srd/5e-SRD-Levels.json {x.classes[0][0]}-{x.level} prof_bonus"
    return [R("PB", x.der["proficiencyBonus"] == exp, exp, x.der["proficiencyBonus"], cite)]


@check("ABIL-MOD")
def c_abil_mod(x: Ctx):
    return [R("ABIL-MOD", x.der["abilityModifiers"] == x.mods, x.mods, x.der["abilityModifiers"],
              "PHB p.13 ability modifier = floor((score - 10) / 2), on sheet.abilities")]


@check("ABIL-RANGE")
def c_abil_range(x: Ctx):
    cap = 30 if (x.class_level("barbarian") >= 20 or any(n.startswith("boon of") for n in x.feat_names)) else 20
    if x.class_level("monk") >= 20 and x.ruleset != "2014":
        cap = max(cap, 25)  # 2024 Monk 20 Body and Mind: DEX and WIS +4, max 25
    bad = {a: v for a, v in x.ab.items() if not 1 <= v <= cap}
    return [R("ABIL-RANGE", not bad, f"every score in 1..{cap}", bad or "ok",
              "PHB p.13 scores cap at 20 (Primal Champion / Epic Boon raise the cap)")]


def _hp_allowances(x: Ctx) -> list[int]:
    opts = []
    if x.has_feat("tough"):
        opts.append(2 * x.level)
    sp = x.sheet["species"]
    sid = (sp.get("id") or "") + " " + str(sp.get("subspecies") or "")
    if "dwarf" in sid.lower():
        opts.append(x.level)
    if x.subclass_is("sorcerer", "draconic"):
        opts.append(x.class_level("sorcerer"))
    return opts


@check("HP")
def c_hp(x: Ctx):
    rolls = [c.get("hpRolls") or {} for c in x.draft["classes"]]
    manual = x.prefs.get("hitPointType") == "manual"
    cm = x.mods["CON"]
    total = 0
    for i, (cid, lvl, _s) in enumerate(x.classes):
        faces = x.raw[i]["hd"]["faces"]
        for l in range(1, lvl + 1):
            if i == 0 and l == 1:
                total += faces + cm
                continue
            r = rolls[i].get(str(l)) if manual else None
            if isinstance(r, int) and not isinstance(r, bool) and 1 <= r <= faces:
                total += max(1, r + cm)
            else:
                total += max(1, faces // 2 + 1 + cm)
    actual = x.der["hitPointMax"]
    allowed = {total + s for s in _subset_sums(_hp_allowances(x))}
    return [R("HP", actual in allowed, f"{total} (+ optional {sorted(allowed - {total})})", actual,
              "PHB p.15 / PHB 2024 p.28: level 1 of the FIRST class = hit die max + CON; later levels roll or average (die // 2 + 1) + CON, min 1; Tough / Dwarven Toughness / Draconic Resilience add per level")]


@check("HIT-DICE")
def c_hit_dice(x: Ctx):
    exp: dict[int, int] = {}
    for i, (_c, lvl, _s) in enumerate(x.classes):
        exp[x.raw[i]["hd"]["faces"]] = exp.get(x.raw[i]["hd"]["faces"], 0) + lvl
    act: dict[int, int] = {}
    for n, f in re.findall(r"(\d+)d(\d+)", x.der["hitDice"]):
        act[int(f)] = act.get(int(f), 0) + int(n)
    return [R("HIT-DICE", exp == act, exp, act, "class JSON hd.faces per class, one die per class level (PHB p.163 multiclass hit dice)")]


@check("SAVE-PROF")
def c_save_prof(x: Ctx):
    first = {a.upper() for a in x.raw[0]["proficiency"]}
    have = set(x.sheet["proficiencies"]["savingThrows"])
    extra_ok = set()
    if x.has_feat("resilient"):
        extra_ok |= set(ABILITIES)
    if x.class_level("monk") >= 14:
        extra_ok |= set(ABILITIES)
    if x.class_level("rogue") >= 15:
        extra_ok |= {"WIS", "CHA"}  # Slippery Mind (2014: WIS; 2024: WIS and CHA)
    if x.class_level("fighter") >= 7 and x.subclass_is("fighter", "psi"):
        pass
    if any("proficiency" in f.lower() and "save" in f.lower() for f in x.feature_names):
        extra_ok |= set(ABILITIES)
    ok = first <= have and have <= first | extra_ok
    return [R("SAVE-PROF", ok, f"{sorted(first)} from the first class only (+ explained extras)", sorted(have),
              f"class-{x.classes[0][0]}.json proficiency; PHB p.164: multiclassing never grants saving throws")]


@check("SAVES")
def c_saves(x: Ctx):
    profs = set(x.sheet["proficiencies"]["savingThrows"])
    aura = max(1, x.mods["CHA"]) if x.class_level("paladin") >= 6 else 0
    bad = {}
    for a in ABILITIES:
        e = x.mods[a] + (x.pb if a in profs else 0) + aura
        if x.der["savingThrows"][a] != e:
            bad[a] = (e, x.der["savingThrows"][a])
    return [R("SAVES", not bad, "mod + PB if proficient (+ Aura of Protection)", bad or "ok",
              "PHB p.179 saving throw = ability modifier + proficiency bonus if proficient; Paladin 6 Aura of Protection adds CHA")]


@check("SKILLS")
def c_skills(x: Ctx):
    profs = set(x.sheet["proficiencies"]["skills"])
    exp_s = set(x.sheet.get("expertiseSkills") or [])
    half = x.pb // 2
    bad = {}
    jack = x.class_level("bard") >= 2
    for sk, ab in SKILL_ABILITY.items():
        base = x.mods[ab]
        e = base + (x.pb if sk in profs else 0) + (x.pb if sk in exp_s else 0)
        allowed = {e}
        if sk not in profs and jack:
            allowed.add(e + half)
        if sk not in profs and x.subclass_is("fighter", "champion") and x.class_level("fighter") >= 7 and ab in ("STR", "DEX", "CON"):
            allowed.add(e + (x.pb + 1) // 2)  # Remarkable Athlete rounds UP (PHB 2014 p.72)
        if x.thaumaturge and sk in ("skill-arcana", "skill-religion", "skill-nature"):
            allowed.add(e + max(1, x.mods["WIS"]))  # 2024 Thaumaturge / Magician order
        a = x.der["skills"].get(sk)
        if a not in allowed:
            bad[sk] = (e, a)
    return [R("SKILLS", not bad, "mod + PB (proficient) + PB (expertise) (+ half PB: Jack of All Trades / Remarkable Athlete)", bad or "ok",
              "PHB p.174-175 skill bonus; Rogue / Bard expertise doubles PB")]


@check("PASSIVES")
def c_passives(x: Ctx):
    bad = {}
    for key, sk in (("passivePerception", "skill-perception"), ("passiveInsight", "skill-insight"), ("passiveInvestigation", "skill-investigation")):
        e = 10 + x.der["skills"][sk]
        allowed = {e}
        if x.has_feat("observant") and sk in ("skill-perception", "skill-investigation"):
            allowed.add(e + 5)
        if x.der[key] not in allowed:
            bad[key] = (e, x.der[key])
    return [R("PASSIVES", not bad, "10 + skill bonus (+5 Observant)", bad or "ok", "PHB p.175 passive checks = 10 + modifiers")]


@check("INITIATIVE")
def c_init(x: Ctx):
    opts = []
    if x.has_feat("alert"):
        opts += [5] if x.ruleset == "2014" else [5, x.pb]  # 2014 Alert +5; 2024 Alert adds PB (mixed may hold either)
    if x.class_level("bard") >= 2 and x.ruleset != "2024":
        opts.append(x.pb // 2)
    if x.class_level("fighter") >= 7 and x.subclass_is("fighter", "champion"):
        opts.append(x.pb // 2)
    if x.subclass_is("rogue", "swashbuckler"):
        opts.append(x.mods["CHA"])
    if x.subclass_is("ranger", "gloom"):
        opts.append(x.mods["WIS"])  # Dread Ambusher
    if x.class_level("fighter") >= 7 and x.subclass_is("fighter", "champion"):
        opts.append((x.pb + 1) // 2)  # Remarkable Athlete (DEX-based initiative), rounded up
    if x.subclass_is("barbarian", "") and x.class_level("barbarian") >= 7:
        opts.append(0)
    if x.subclass_is("wizard", "") and any(c[2] and "war" in c[2].lower() for c in x.classes):
        opts.append(x.mods["INT"])
    if x.subclass_is("fighter", "") and any(c[2] and "psi" in c[2].lower() for c in x.classes):
        opts.append(0)
    allowed = {x.mods["DEX"] + s for s in _subset_sums(opts)}
    return [R("INITIATIVE", x.der["initiative"] in allowed, f"DEX mod {x.mods['DEX']} (+ explained bonuses)", x.der["initiative"],
              "PHB p.177 initiative = DEX modifier; Alert / Jack of All Trades / Tactical Wit add")]


def _caster_kind(raw: dict | None, sub: dict | None) -> str | None:
    if raw and raw.get("casterProgression"):
        return raw["casterProgression"]
    if sub and sub.get("casterProgression"):
        return sub["casterProgression"]
    return None


def expected_slots(x: Ctx) -> dict:
    contributors = []  # (class id, kind, own rows, level)
    for i, (cid, lvl, _s) in enumerate(x.classes):
        kind = _caster_kind(x.raw[i], x.sub[i])
        if kind in (None, "pact"):
            continue
        rows = slot_rows(x.raw[i]) if x.raw[i].get("casterProgression") else slot_rows(x.sub[i], True)
        contributors.append((cid, kind, rows, lvl))
    live = [c for c in contributors if c[2] and any(c[2][c[3] - 1])]
    if not live:
        return {}
    if len(live) == 1:
        row = live[0][2][live[0][3] - 1]
    else:
        total = 0
        for cid, kind, _rows, lvl in contributors:
            if kind == "full":
                total += lvl
            elif kind == "1/2":  # PHB 2014 data: half casters round down
                total += lvl // 2
            elif kind == "artificer":  # 5etools code of the XPHB Paladin / Ranger: half caster, rounded UP
                total += math.ceil(lvl / 2)
            elif kind == "1/3":
                total += lvl // 3
        total = min(total, 20)
        if total == 0:
            return {}
        row = slot_rows(raw_class("wizard", "2014"))[total - 1]
    return {str(i + 1): n for i, n in enumerate(row) if n}


@check("SLOTS")
def c_slots(x: Ctx):
    exp = expected_slots(x)
    act = {k: v for k, v in x.der["spellSlots"].items() if v}
    return [R("SLOTS", exp == act, exp, act,
              "PHB 2014 p.164-165 / PHB 2024 multiclassing: a single caster uses its class table; several casters sum full + half (down in 2014, up in 2024) + third (down) levels on the Wizard progression")]


@check("PACT")
def c_pact(x: Ctx):
    lvl = x.class_level("warlock")
    exp = {}
    if lvl:
        raw = x.raw[[c[0] for c in x.classes].index("warlock")]
        n = table_column(raw, "Spell Slots")
        lv = table_column(raw, "Slot Level")
        if n and lv:
            exp = {str(ordinal(lv[lvl - 1])): int(n[lvl - 1])}
    return [R("PACT", exp == x.der["warlockSpellSlots"], exp, x.der["warlockSpellSlots"],
              "class-warlock.json class table columns 'Spell Slots' and 'Slot Level'; Pact Magic slots are separate from Spellcasting")]


@check("SPELL-DC")
def c_spell_dc(x: Ctx):
    out = []
    for entry in x.sheet.get("spells", []):
        cid = entry["classId"]
        idx = [c[0] for c in x.classes].index(cid)
        ability = (x.raw[idx].get("spellcastingAbility") or (x.sub[idx] or {}).get("spellcastingAbility"))
        if not ability or "spellSaveDC" not in entry:
            continue
        m = x.mods[ability.upper()]
        out.append(R("SPELL-DC", (entry["spellSaveDC"], entry["spellAttackBonus"]) == (8 + x.pb + m, x.pb + m),
                     {"dc": 8 + x.pb + m, "attack": x.pb + m}, {"dc": entry["spellSaveDC"], "attack": entry["spellAttackBonus"]},
                     f"{cid} spellcasting ability {ability.upper()}; PHB p.205: DC 8 + PB + mod, attack PB + mod"))
    return out


def _card(x: Ctx, cid: str, suffix: str):
    for c in x.res["choices"]:
        if c["id"] == f"class:{cid}:{suffix}":
            return c
    return None


@check("CANTRIPS")
def c_cantrips(x: Ctx):
    out = []
    for i, (cid, lvl, _s) in enumerate(x.classes):
        prog = x.raw[i].get("cantripProgression") or (x.sub[i] or {}).get("cantripProgression")
        col = table_column(x.raw[i], "Cantrips")
        exp = prog[lvl - 1] if prog else (col[lvl - 1] if col else None)
        card = _card(x, cid, "spells-cantrips")
        if exp is None or (exp == 0 and not card):
            continue
        act = card["count"] if card else 0
        if x.thaumaturge and cid == "cleric" or x.thaumaturge and cid == "druid":
            exp += 1  # 2024 Thaumaturge / Magician: one extra cantrip
        out.append(R("CANTRIPS", act == exp, exp, act, f"class-{cid}.json cantripProgression / 'Cantrips' column at level {lvl}"))
    return out


def _formula(text: str, lvl: int, mods: dict) -> int:
    t = text.replace("<$level$>", str(lvl))
    for a in ABILITIES:
        t = t.replace(f"<${a.lower()}_mod$>", str(mods[a]))
    t = t.replace("/", "//")
    return max(1, eval(t, {"__builtins__": {}}))  # noqa: S307 (formula from vendored data: digits + - //)


@check("SPELLS-KNOWN")
def c_known(x: Ctx):
    out = []
    for i, (cid, lvl, _s) in enumerate(x.classes):
        raw, sub = x.raw[i], x.sub[i]
        card = _card(x, cid, "spells-known")
        if not card:
            continue
        exp = src = None
        if raw.get("spellsKnownProgression"):
            exp, src = raw["spellsKnownProgression"][lvl - 1], "spellsKnownProgression"
        elif sub and sub.get("spellsKnownProgression"):
            exp, src = sub["spellsKnownProgression"][lvl - 1], "subclass spellsKnownProgression"
        elif raw.get("preparedSpellsProgression"):
            exp, src = raw["preparedSpellsProgression"][lvl - 1], "preparedSpellsProgression"
        elif raw.get("preparedSpells") and x.ruleset != "2024":
            exp, src = _formula(raw["preparedSpells"], lvl, x.mods), "preparedSpells formula " + raw["preparedSpells"]
        if exp is None or src is None:
            continue
        out.append(R("SPELLS-KNOWN", card["count"] == exp, exp, card["count"], f"class-{cid}.json {src} at level {lvl}"))
    return out


@check("SPELLBOOK")
def c_spellbook(x: Ctx):
    lvl = x.class_level("wizard")
    card = _card(x, "wizard", "spellbook")
    if not lvl or not card:
        return []
    return [R("SPELLBOOK", card["count"] == 6 + 2 * (lvl - 1), 6 + 2 * (lvl - 1), card["count"],
              "PHB p.114 / PHB 2024 p.185 Wizard Spellbook: 6 spells at level 1, +2 per level")]


def _armor_ac(x: Ctx):
    slots = (x.sheet.get("equipment") or {}).get("slots") or {}
    cur = slots.get("current") or {}
    armor = None
    if cur.get("armor"):
        armor = item_by_id(cur["armor"], x.ruleset)
    return armor, bool(cur.get("shield")), cur


@check("AC")
def c_ac(x: Ctx):
    armor, shield, cur = _armor_ac(x)
    dex = x.mods["DEX"]
    opts = {}
    if armor:
        t = str(armor.get("type", "")).split("|")[0]
        base = armor["ac"]
        opts["armor"] = base + (dex if t == "LA" else min(dex, 2) if t == "MA" else 0)
    else:
        opts["unarmored"] = 10 + dex
        if x.class_level("barbarian"):
            opts["barbarian"] = 10 + dex + x.mods["CON"]
        if x.class_level("monk") and not shield:
            opts["monk"] = 10 + dex + x.mods["WIS"]
        if x.subclass_is("sorcerer", "draconic") and not x.subclass_is("sorcerer", "draconic sorcery"):
            opts["draconic"] = 13 + dex  # PHB 2014 / SRD Draconic Resilience
        if x.subclass_is("sorcerer", "draconic sorcery") and x.class_level("sorcerer") >= 3:
            opts["draconic"] = 10 + dex + x.mods["CHA"]  # XPHB Draconic Sorcery, Draconic Resilience
    best = max(opts.values())
    best += 2 if shield else 0
    allowed = {best}
    picks = [v for c in x.draft["classes"] for vs in (c.get("choices") or {}).values() if isinstance(vs, list) for v in vs]
    if armor and any(isinstance(v, str) and "defense" in v and ("style" in v or v.startswith("feat:")) for v in picks):
        allowed.add(best + 1)
    return [R("AC", x.der["armorClass"] in allowed, f"{best} best of {opts}{' + shield 2' if shield else ''}", x.der["armorClass"],
              "PHB p.14, 144-145, class Unarmored Defense; one formula at a time, the best applies (Defense style +1 in armor)")]


@check("SPEED")
def c_speed(x: Ctx):
    sp = x.sheet["species"]
    race = None
    rid = sp.get("id") or ""
    for r in raw_races()["race"]:
        key = r["name"].lower().replace(" ", "-")
        if rid == key and r["source"] in ("PHB", "XPHB") or rid == f"{key}-{r['source'].lower()}":
            race = r
            break
    if race is None or sp.get("subspecies") or sp.get("variant"):
        return []  # lineages / variants restate or change the speed in their own text: not modelled by this check
    s = race.get("speed")
    base = s.get("walk") if isinstance(s, dict) else s
    if not isinstance(base, int):
        return []
    # trait texts may restate the walking speed ("Your base walking speed is 35 feet"): accept those too
    text = json.dumps(race.get("entries", []))
    bases = {base} | {int(n) for n in re.findall(r"walking speed (?:is|increases to|becomes) (\d+) feet", text)}
    if len(bases) > 1:
        base = max(bases) if x.der["speed"] >= max(bases) else base
    armor, shield, cur = _armor_ac(x)
    heavy = bool(armor and str(armor.get("type", "")).split("|")[0] == "HA")
    exp = base
    if x.class_level("barbarian") >= 5 and not heavy:
        exp += 10
    if x.class_level("monk") and not armor and not shield:
        col = table_column(x.raw[[c[0] for c in x.classes].index("monk")], "Unarmored Movement")
        if col:
            exp += int(col[x.class_level("monk") - 1])
    if not heavy and x.ruleset != "2014":
        if x.class_level("ranger") >= 6 and x.ruleset == "2024":
            exp += 10  # XPHB Ranger 6 Roving
    if x.subclass_is("paladin", "glory") and x.class_level("paladin") >= 7:
        exp += 10  # Oath of Glory, Aura of Alacrity
    allowed = {exp}
    if heavy and armor.get("strength") and x.ab["STR"] < int(armor["strength"]):
        allowed = {exp - 10}
        if "dwarf" in rid:
            allowed.add(exp)
    return [R("SPEED", x.der["speed"] in allowed, sorted(allowed), x.der["speed"],
              "races.json speed; Barbarian Fast Movement +10 from level 5 (not in heavy armor); Monk Unarmored Movement column; PHB p.144 heavy armor below its STR minimum -10 ft")]


@check("ATTACKS-PER-ACTION")
def c_attacks(x: Ctx):
    best = 1
    for i, (cid, lvl, _s) in enumerate(x.classes):
        names = []
        for f in x.raw[i]["classFeatures"]:
            s = f if isinstance(f, str) else f.get("classFeature", "")
            parts = s.split("|")
            if "Extra Attack" in parts[0]:
                names.append((parts[0], int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 99))
        for n, l in names:
            if l <= lvl:
                m = re.search(r"\((\d)\)", n)
                words = {"Two": 3, "Three": 4}.get(n.split()[0])
                best = max(best, int(m.group(1)) + 1 if m else words or 2)
        for f in raw_subclass_features(cid, x.sub[i]):
            if f["name"].startswith("Extra Attack") and f["level"] <= lvl:
                best = max(best, 2)
    act = x.der["attacksPerAction"]
    ok = act == best or (act == 2 and best == 1 and x.class_level("warlock") >= 5)
    return [R("ATTACKS-PER-ACTION", ok, best, act, "class JSON Extra Attack features (Fighter 5/11/20 = 2/3/4); Extra Attack does not stack across classes (PHB p.164)")]


def _norm(n: str) -> str:
    return re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", n.lower()))


@check("FEATURES-LEVEL")
def c_features(x: Ctx):
    out = []
    for i, (cid, lvl, _s) in enumerate(x.classes):
        later = []
        for f in x.sheet.get("features", []):
            src = f.get("source") or {}
            if src.get("kind") == "class" and src.get("id") == cid and isinstance(f.get("level"), int) and f["level"] > lvl:
                later.append((f["name"], f["level"]))
        out.append(R("FEATURES-LEVEL", not later, f"no {cid} feature above level {lvl}", later or "ok",
                     f"class-{cid}.json classFeatures levels"))
    return out


@check("FEATURES-PRESENT")
def c_features_present(x: Ctx):
    out = []
    for i, (cid, lvl, _s) in enumerate(x.classes):
        have = {_norm(f["name"]) for f in x.sheet.get("features", [])}
        missing = []
        for f in x.raw[i]["classFeatures"]:
            if not isinstance(f, str):
                continue  # {"classFeature": ..., "gainSubclassFeature": true}: the subclass slot, not a named feature
            parts = f.split("|")
            try:
                l = int(parts[3])
            except (IndexError, ValueError):
                continue
            if len(parts) > 4 and parts[4]:
                continue  # an optional feature from another book (TCE ...): not part of the base chassis
            name = parts[0]
            if name.endswith("Subclass") or name.endswith("Subclass Feature"):
                continue
            if l <= lvl and not any(h == _norm(name) or h.startswith(_norm(name)) or _norm(name).startswith(h) and len(h) > 6 for h in have):
                if name in ("Ability Score Improvement", "Epic Boon") or "Martial Versatility" in name:
                    continue
                missing.append((name, l))
        out.append(R("FEATURES-PRESENT", not missing, f"every {cid} feature up to level {lvl} listed", missing or "ok",
                     f"class-{cid}.json classFeatures ({edition_source(x.ruleset)})"))
    return out


RESOURCE_COLUMNS = {  # class -> [(table column label, resource name regex)]
    "barbarian": [("Rages", r"^rage$")],
    "monk": [("Ki Points", r"^ki"), ("Focus Points", r"focus")],
    "sorcerer": [("Sorcery Points", r"sorcery")],
    "cleric": [("Channel Divinity", r"^channel divinity")],
}


@check("RESOURCES")
def c_resources(x: Ctx):
    out = []
    for i, (cid, lvl, _s) in enumerate(x.classes):
        for label, rx in RESOURCE_COLUMNS.get(cid, []):
            col = table_column(x.raw[i], label)
            if not col:
                continue
            raw_v = col[lvl - 1]
            if isinstance(raw_v, str) and not raw_v.isdigit():
                continue
            exp = int(raw_v)
            res = [r for r in x.der["classResources"] if r["classId"] == cid and re.search(rx, r["name"].lower())]
            if exp == 0:
                continue
            act = res[0]["uses"] if res else None
            out.append(R("RESOURCES", act == exp, exp, act, f"class-{cid}.json class table column '{label}' at level {lvl}"))
    return out


def _requirement_met(req: dict, scores: dict) -> bool:
    ok = all(scores[k.upper()] >= v for k, v in req.items() if k not in ("or", "and") and isinstance(v, int))
    for alt in req.get("or", []):
        ok = ok and any(scores[k.upper()] >= v for k, v in alt.items())
    return ok


@check("MC-PREREQ")
def c_mc_prereq(x: Ctx):
    if len(x.classes) < 2 or not (x.prefs.get("usePrerequisites") or {}).get("multiclass"):
        return []
    out = []
    problems = {p["id"] for p in x.res["problems"]}
    for i, (cid, _l, _s) in enumerate(x.classes):
        if x.ruleset == "2024":
            prim = x.raw[i].get("primaryAbility") or []
            # 2024 primaryAbility: a list of alternatives, each a dict whose keys are ALL required ({str} or {dex}; {dex, wis})
            met = any(all(x.ab[k.upper()] >= 13 for k in p) for p in prim) if prim else True
            cite = f"class-{cid}.json primaryAbility ({prim})"
        else:
            req = (x.raw[i].get("multiclassing") or {}).get("requirements") or {}
            met = _requirement_met(req, x.ab)
            cite = f"class-{cid}.json multiclassing.requirements {req}"
        flagged = f"multiclass-prerequisite-unmet-{cid}" in problems
        out.append(R("MC-PREREQ", flagged == (not met), "problem iff a requirement is below 13", f"problem={flagged}, met={met}", cite))
    return out


@check("MC-PROF")
def c_mc_prof(x: Ctx):
    if len(x.classes) < 2:
        return []
    allowed_heavy = x.raw[0].get("startingProficiencies", {}).get("armor", [])
    heavy_ok = any("heavy" in a for a in allowed_heavy)
    for i in range(1, len(x.classes)):
        gained = (x.raw[i].get("multiclassing") or {}).get("proficienciesGained", {}).get("armor", [])
        heavy_ok = heavy_ok or any("heavy" in a for a in gained)
    explained = heavy_ok or x.has_feat("heavily armored") or any(
        c[2] and any(k in c[2].lower() for k in ("life", "forge", "war", "tempest", "order", "twilight", "death", "grave", "nature"))
        for c in x.classes) or x.sheet["species"].get("id", "").startswith("mountain")
    has = "heavy-armor" in x.sheet["proficiencies"]["armor"]
    return [R("MC-PROF", not has or explained, "heavy armor only from the first class's start, a multiclass grant, a feat or a subclass",
              "heavy-armor listed" if has else "ok", "PHB p.164 multiclass proficiencies table (proficienciesGained)")]


@check("DUPLICATES")
def c_dups(x: Ctx):
    bad = {}
    for k, v in x.sheet["proficiencies"].items():
        if isinstance(v, list) and len(set(map(str, v))) != len(v):
            bad[k] = [i for i in v if v.count(i) > 1][:3]
    ids = [f["id"] for f in x.sheet.get("feats", [])]
    dup_feats = {i for i in ids if ids.count(i) > 1}
    feats = [(f["source"]["id"], f["name"], f.get("level")) for f in x.sheet.get("features", []) if "source" in f]
    dup_f = {f for f in feats if feats.count(f) > 1}
    if dup_feats:
        bad["feats"] = sorted(dup_feats)
    if dup_f:
        bad["features"] = sorted(map(str, dup_f))[:3]
    return [R("DUPLICATES", not bad, "no duplicate skills / tools / languages / feats / features", bad or "ok",
              "PHB p.175: a duplicate proficiency is replaced by another choice; a feature is listed once")]


@check("FEAT-PREREQ")
def c_feat_prereq(x: Ctx):
    if not (x.prefs.get("usePrerequisites") or {}).get("feats"):
        return []
    out = []
    for f in x.sheet.get("feats", []):
        if f.get("origin") != "asi":
            continue
        raw = raw_feat(f["name"], x.ruleset)
        pre = (raw or {}).get("prerequisite")
        if not pre:
            continue
        ok_any, relevant = False, False
        for alt in pre:
            if "ability" not in alt and "level" not in alt:
                continue
            relevant = True
            ok = x.level >= alt.get("level", 0)
            if alt.get("ability"):
                ok = ok and any(all(x.ab[k.upper()] >= v for k, v in a.items()) for a in alt["ability"])
            ok_any = ok_any or ok
        if relevant:
            out.append(R("FEAT-PREREQ", ok_any, f"{f['name']} prerequisite {pre}", "met" if ok_any else "unmet",
                         f"feats.json {f['name']} ({raw['source']}) prerequisite"))
    return out


def run_checks(draft: dict, res: dict, only: set | None = None) -> list[dict]:
    x = Ctx(draft, res)
    out = []
    for rule, fn in REGISTRY:
        if only and rule not in only:
            continue
        try:
            out += fn(x)
        except Exception as e:  # an oracle crash is reported, never hidden
            out.append(R(rule, False, "check runs", f"oracle exception {type(e).__name__}: {e}", "checks.py"))
    return out


def failures(draft: dict, res: dict) -> list[dict]:
    return [r for r in run_checks(draft, res) if not r["ok"]]


def rule_ids() -> list[str]:
    return [r for r, _ in REGISTRY]
