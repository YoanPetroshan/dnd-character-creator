"""Class resources (derived.classResources): rages, sneak attack dice, ... as a
flat, ordered list shown on the class page and in the exports. Pure: callers
pass the resolved classes and the numbers they already computed.

Numbers come from the SRD level rows (`rc["level_row"]["class_specific"]`)
and, only under ruleset "2024" (decision U9; "mixed" and "2014" stay on the SRD
chassis, D2), from the XPHB class tables (`catalog.class_2024_tables`). When the
2024 tables are missing the SRD numbers are used and the warning
`class-2024-tables-missing` is added once.

Adding a class (slices R2-R6): write `_name(ctx, rc) -> list[dict]` using the
helpers `_resource(...)` and `ctx.table(...)`, then register it in `_BUILDERS`
(or `_SUBCLASS_BUILDERS`, keyed by subclass id, for R6).

Resource shape (see the plan, "Resource shape"):
  id, classId, source {kind, id, label}, name, uses, unlimited?, recharge
  ("long" | "short" | "short-or-long" | None), die?, dice?, pool?, bonus?, dc?,
  details?
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from catalog import reference_data
from engine import class_choices_2024

UNLIMITED_ROW_VALUE = 9999  # SRD level rows store "unlimited" as 9999 (Barbarian 20 rages)


@dataclass
class Ctx:
    catalog: object
    ruleset: str
    modifiers: dict
    prof_bonus: int
    choices: dict
    warnings_out: list | None = None
    _warned: bool = field(default=False, repr=False)
    _warned_sub: bool = field(default=False, repr=False)

    def table(self, cls_id: str, column: str, level: int):
        """The 2024 table value for a class column at a class level, or None
        when the ruleset is not "2024" or the table has no such column (the
        caller then uses the SRD number). Warns once when the whole 2024 table
        set is missing."""
        if self.ruleset != "2024":
            return None
        tables = getattr(self.catalog, "class_2024_tables", None)
        if not tables:
            if not self._warned and self.warnings_out is not None:
                self.warnings_out.append({
                    "id": "class-2024-tables-missing",
                    "message": "The 2024 class tables are not available; class resources use the 2014 numbers.",
                })
            self._warned = True
            return None
        values = (tables.get(cls_id) or {}).get(column)
        return values[level - 1] if values and 0 < level <= len(values) else None

    def subclass_table(self, sub_id: str, column: str, level: int):
        """The 2024 subclass table value, or None when the ruleset is not "2024"
        or the table is missing (the caller then uses the formula). Warns once
        when the whole subclass table set is missing."""
        if self.ruleset != "2024":
            return None
        tables = getattr(self.catalog, "subclass_2024_tables", None)
        if not tables:
            if not self._warned_sub and self.warnings_out is not None:
                self.warnings_out.append({
                    "id": "subclass-2024-tables-missing",
                    "message": "The 2024 subclass tables are not available; subclass resources use the 2014 formulas.",
                })
            self._warned_sub = True
            return None
        values = (tables.get(sub_id) or {}).get(column)
        return values[level - 1] if values and 0 < level <= len(values) else None


def _class_specific(rc: dict) -> dict:
    return (rc.get("level_row") or {}).get("class_specific") or {}


def _slug(text: str) -> str:
    return "-".join("".join(ch if ch.isalnum() else " " for ch in text.lower()).split())


def _resource(rc: dict, name: str, *, kind: str = "class", recharge: str | None = None, uses: int | None = None,
              unlimited: bool = False, **fields) -> dict:
    """One resource entry; optional fields that are None are left out."""
    cls_id = rc["cls_id"]
    if kind == "subclass":
        source = {"kind": "subclass", "id": rc.get("subclass_id"), "label": (rc.get("subclass") or {}).get("name") or ""}
    else:
        source = {"kind": "class", "id": cls_id, "label": (rc.get("cls") or {}).get("name") or cls_id}
    out: dict = {"id": f"{cls_id}:{_slug(name)}", "classId": cls_id, "source": source, "name": name,
                 "uses": None if unlimited else uses}
    if unlimited:
        out["unlimited"] = True
    out["recharge"] = recharge
    for key, value in fields.items():
        if value is not None:
            out[key] = value
    return out


def _picked_option_ids(ctx: Ctx, class_id: str) -> set[str]:
    """Selected ids of the class's feature-text choices (cid class:<cls>:<lvl>:feature:<id>).
    `ctx.choices` is the resolved choice list from resolve() (a dict or None in unit tests)."""
    if not isinstance(ctx.choices, list):
        return set()
    return {sel for c in ctx.choices if (c.get("source") or {}).get("id") == class_id and ":feature:" in c.get("id", "")
            for sel in c.get("selected") or []}


def _barbarian(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    cs = _class_specific(rc)
    uses = ctx.table("barbarian", "rages", level)
    from_table = uses is not None  # 2024 (XPHB): one use back on a short rest, all on a long rest
    bonus = ctx.table("barbarian", "rage-damage", level)
    if uses is None:
        uses = cs.get("rage_count")
    if bonus is None:
        bonus = cs.get("rage_damage_bonus")
    if uses is None:
        return []
    unlimited = uses >= UNLIMITED_ROW_VALUE
    resistances = ["bludgeoning", "piercing", "slashing"]
    if reference_data.TOTEM_BEAR_OPTION_ID in _picked_option_ids(ctx, "barbarian"):
        # 2014 Totem Warrior Bear: every damage type except psychic. The 2024
        # Wild Heart per-rage options are listed in details.perRageOptions.
        resistances = [t for t in reference_data.DAMAGE_TYPES if t != "psychic"]
    details = {"damageBonus": bonus, "resistances": resistances}
    if from_table:
        details["shortRestRegains"] = 1
    options = _wild_heart_rage_options(ctx, rc)
    if options:
        details["perRageOptions"] = options
    return [_resource(rc, "Rage", uses=uses, unlimited=unlimited, recharge="long", details=details)]


# G1: (feature id, minimum Barbarian level) of the XPHB Wild Heart features that
# give a choice of one option each time the Rage is activated.
_WILD_HEART_RAGE_FEATURES = (
    ("wild-heart-xphb-3-rage-of-the-wilds", 3),
    ("wild-heart-xphb-14-power-of-the-wilds", 14),
)


def _wild_heart_rage_options(ctx: Ctx, rc: dict) -> list[dict]:
    """[{name, effect}] from the catalog text of Rage of the Wilds / Power of the Wilds
    ("Bear. While your Rage is active, ..."); 2024 ruleset and the Wild Heart only."""
    if ctx.ruleset != "2024" or rc.get("subclass_id") != "wild-heart-xphb":
        return []
    out = []
    for fid, min_level in _WILD_HEART_RAGE_FEATURES:
        feature = ctx.catalog.features.get(fid)
        if not feature or rc["level"] < min_level:
            continue
        for line in feature.get("desc") or []:
            m = re.match(r"^([A-Z][a-z]+)\. (.+)$", line)
            if m:
                out.append({"name": m.group(1), "effect": m.group(2)})
    return out


def _rogue(ctx: Ctx, rc: dict) -> list[dict]:
    dice = ctx.table("rogue", "sneak-attack", rc["level"])
    if dice is None:
        sa = _class_specific(rc).get("sneak_attack") or {}
        dice = f"{sa['dice_count']}d{sa['dice_value']}" if sa.get("dice_count") else None
    if dice is None:
        return []
    return [_resource(rc, "Sneak Attack", dice=dice)]


def _fighter(ctx: Ctx, rc: dict) -> list[dict]:
    # Second Wind: 2014 = 1 use; 2024 = XPHB table (2/3/4). Heal 1d10 + fighter level in both.
    level = rc["level"]
    cs = _class_specific(rc)
    out = []
    wind = ctx.table("fighter", "second-wind", level)
    details = {"heal": f"1d10+{level}"}
    if wind is not None:  # 2024 (XPHB): one use back on a short rest, all on a long rest
        details["shortRestRegains"] = 1
    out.append(_resource(rc, "Second Wind", uses=1 if wind is None else wind,
                         recharge="short-or-long" if wind is None else "long", details=details))
    if cs.get("action_surges"):
        out.append(_resource(rc, "Action Surge", uses=cs["action_surges"], recharge="short-or-long"))
    if cs.get("indomitable_uses"):
        out.append(_resource(rc, "Indomitable", uses=cs["indomitable_uses"], recharge="long"))
    return out


def _martial_arts_die(ctx: Ctx, rc: dict) -> str | None:
    """"d6" etc. for a Monk class entry: the XPHB table under 2024, else the SRD row."""
    value = ctx.table("monk", "martial-arts", rc["level"])
    if value:
        return "d" + str(value).split("d", 1)[1]
    ma = _class_specific(rc).get("martial_arts") or {}
    return f"d{ma['dice_value']}" if ma.get("dice_value") else None


def _monk(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    out = []
    die = _martial_arts_die(ctx, rc)
    if die:
        out.append(_resource(rc, "Martial Arts", die=die))
    focus = ctx.table("monk", "focus-points", level)
    if focus is not None:
        name = "Focus Points"
    else:
        name, focus = "Ki", _class_specific(rc).get("ki_points")
    if focus:  # none at level 1
        out.append(_resource(rc, name, uses=focus, recharge="short",
                             dc=8 + ctx.prof_bonus + ctx.modifiers.get("WIS", 0)))
    return out


# ---- Cleric / Paladin / Druid (R3) ----------------------------------------

def _cr_text(value) -> str:
    return reference_data.CR_TEXT.get(value) or str(int(value))


def _channel_divinity(ctx: Ctx, rc: dict, srd_uses: int | None) -> dict | None:
    """One class's Channel Divinity entry; resources_for merges several into one
    (PHB 164). 2024: regain one use on a short rest, all on a long rest."""
    uses = ctx.table(rc["cls_id"], "channel-divinity", rc["level"])
    if uses is not None:
        if not uses:
            return None
        return _resource(rc, "Channel Divinity", uses=uses, recharge="long", details={"shortRestRegains": 1})
    if not srd_uses:
        return None
    return _resource(rc, "Channel Divinity", uses=srd_uses, recharge="short-or-long")


def _cleric(ctx: Ctx, rc: dict) -> list[dict]:
    cs = _class_specific(rc)
    out = []
    cd = _channel_divinity(ctx, rc, cs.get("channel_divinity_charges"))
    if cd:
        out.append(cd)
    # Destroy Undead is 2014 only; the 2024 Cleric has Sear Undead (no CR column).
    if ctx.ruleset != "2024" and cs.get("destroy_undead_cr"):
        out.append(_resource(rc, "Destroy Undead", details={"maxCr": _cr_text(cs["destroy_undead_cr"])}))
    return out + _class_strikes(ctx, rc)


def _class_strikes(ctx: Ctx, rc: dict) -> list[dict]:
    """C6c-2 (decision E3): the picked 2024 Blessed Strikes / Elemental Fury option as a resource. Divine
    Strike / Primal Strike carry `dice` (the attack-row notes read them) and Potent Spellcasting a `bonus`
    (the WIS modifier added to the class's cantrip damage) with the improved text from level 14 / 15 in
    `details.note`. Nothing outside ruleset 2024 or without the pick."""
    if ctx.ruleset != "2024":
        return []
    cls_id, level = rc["cls_id"], rc["level"]
    out = []
    for key, name, usage in (("divine_strike", "Divine Strike", "once per turn, when you hit with a weapon"),
                             ("primal_strike", "Primal Strike", "once per turn, when you hit with a weapon or a Wild Shape Beast form")):
        effect = class_choices_2024.strike_effect(ctx.choices, cls_id, key)
        dice = effect and class_choices_2024.dice_at_level(effect["dice_by_level"], level)
        if dice:
            out.append(_resource(rc, name, dice=dice, details={"note": usage, "damageTypes": effect["types"]}))
    potent = class_choices_2024.strike_effect(ctx.choices, cls_id, "potent_spellcasting")
    if potent:
        wis = ctx.modifiers.get("WIS", 0)
        note = f"add WIS modifier to the damage of any {potent['class']} cantrip"
        if level >= potent["improved_level"]:
            if cls_id == "cleric":
                note += f"; a damaging cantrip can grant temporary hit points equal to twice WIS modifier ({2 * wis}) within 60 feet"
            else:
                note += "; cantrips with range 10 feet or more gain +300 feet of range"
        out.append(_resource(rc, "Potent Spellcasting", bonus=wis, details={"note": note}))
    return out


def _paladin(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    out = [_resource(rc, "Lay on Hands", pool=5 * level, recharge="long")]
    if ctx.ruleset != "2024":  # 2024 Divine Sense is a Channel Divinity effect
        out.append(_resource(rc, "Divine Sense", uses=max(1, 1 + ctx.modifiers.get("CHA", 0)), recharge="long"))
    pcd = reference_data.PALADIN_2014_CHANNEL_DIVINITY
    cd = _channel_divinity(ctx, rc, pcd["uses"] if level >= pcd["minLevel"] else None)
    if cd:
        out.append(cd)
    return out


def _druid(ctx: Ctx, rc: dict) -> list[dict]:
    return _wild_shape(ctx, rc) + _class_strikes(ctx, rc)


def _wild_shape(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    uses = ctx.table("druid", "wild-shape", level)
    if uses is not None:
        if not uses:
            return []
        shape = next((s for s in reversed(reference_data.WILD_SHAPE_2024_BEAST_SHAPES) if level >= s[0]), None)
        details = {"shortRestRegains": 1}
        if shape:
            details.update(maxCr=shape[2], fly=shape[3], knownForms=shape[1])
        return [_resource(rc, "Wild Shape", uses=uses, recharge="long", details=details)]
    cs = _class_specific(rc)
    if not cs.get("wild_shape_max_cr"):
        return []
    # SRD feature `archdruid` (level 20): unlimited Wild Shape.
    unlimited = level >= 20
    return [_resource(
        rc, "Wild Shape", uses=reference_data.WILD_SHAPE_2014_USES, unlimited=unlimited, recharge="short-or-long",
        details={"maxCr": _cr_text(cs["wild_shape_max_cr"]), "swim": bool(cs.get("wild_shape_swim")),
                 "fly": bool(cs.get("wild_shape_fly"))},
    )]


# ---- Bard / Sorcerer / Wizard / Ranger (R4) --------------------------------

def _bard(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    die = ctx.table("bard", "bardic-die", level)  # "1d8"
    if die:
        die = "d" + str(die).split("d", 1)[1]
    else:
        value = _class_specific(rc).get("bardic_inspiration_die")
        die = f"d{value}" if value else None
    if die is None:
        return []
    # Uses = CHA modifier (minimum 1), both editions; Font of Inspiration (level 5) adds the short rest.
    recharge = "short-or-long" if level >= reference_data.FONT_OF_INSPIRATION_LEVEL else "long"
    details = {"spellSlotRegainsUse": True} if ctx.ruleset == "2024" and recharge == "short-or-long" else None
    return [_resource(rc, "Bardic Inspiration", uses=max(1, ctx.modifiers.get("CHA", 0)), recharge=recharge,
                      die=die, details=details)]


def _sorcerer(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    cs = _class_specific(rc)
    points = ctx.table("sorcerer", "sorcery-points", level)
    if points is None:
        points = cs.get("sorcery_points")
    if not points:  # none at level 1
        return []
    if ctx.table("sorcerer", "sorcery-points", level) is not None:
        costs = {lvl: cost for lvl, cost, min_level in reference_data.SORCERER_2024_CREATING_SLOTS if level >= min_level}
    else:
        costs = {s["spell_slot_level"]: s["sorcery_point_cost"] for s in cs.get("creating_spell_slots") or []}
    details = {"slotCosts": costs} if costs else {}
    if ctx.ruleset == "2024":  # C6c-1: picked Metamagic options and their costs
        picked = class_choices_2024.metamagic_details(ctx.catalog, ctx.choices)
        if picked:
            details["metamagic"] = picked
    return [_resource(rc, "Sorcery Points", uses=points, recharge="long", details=details or None)]


def _wizard(ctx: Ctx, rc: dict) -> list[dict]:
    # Same number in both editions: half the wizard level, rounded up (SRD row equals it at all 20 levels).
    level = rc["level"]
    pool = _class_specific(rc).get("arcane_recovery_levels") if ctx.ruleset != "2024" else None
    return [_resource(rc, "Arcane Recovery", pool=pool or -(-level // 2), recharge="long",
                      details={"maxSlotLevel": reference_data.ARCANE_RECOVERY_MAX_SLOT_LEVEL, "onShortRest": True})]


def _ranger(ctx: Ctx, rc: dict) -> list[dict]:
    # 2024 only: Favored Enemy is Hunter's Mark with free casts. The 2014 one is a choice, not a resource.
    uses = ctx.table("ranger", "favored-enemy", rc["level"])
    if uses is None:
        return []
    return [_resource(rc, "Favored Enemy (Hunter's Mark)", uses=uses, recharge="long")]


def _warlock(ctx: Ctx, rc: dict) -> list[dict]:
    """R8: resource entries for invocations with a number or a text-only effect
    (Agonizing Blast: CHA modifier; Thirsting Blade, Repelling Blast, Book of
    Ancient Secrets: notes). `ctx.choices` is read after the invocation gate."""
    if not isinstance(ctx.choices, list):
        return []
    out = []
    for c in ctx.choices:
        if (c.get("source") or {}).get("id") != "warlock" or ":invocations:" not in c.get("id", ""):
            continue
        for sel in (s.split("~", 1)[0] for s in c.get("selected") or []):  # C7a: strip repeat-instance suffix
            eff = reference_data.INVOCATION_EFFECTS.get(sel) or {}
            bonus = eff.get("resource_bonus")
            if bonus:
                out.append(_resource(rc, bonus["name"], bonus=ctx.modifiers.get(bonus["ability"], 0),
                                     details={"spell": bonus["spell"]}))
            elif eff.get("note") and "innate_spell" not in eff:
                label = (ctx.catalog.features.get(sel) or {}).get("name", sel).replace("Eldritch Invocation: ", "")
                out.append(_resource(rc, label, details={"note": eff["note"]}))
    return out


_BUILDERS: dict[str, Callable[[Ctx, dict], list[dict]]] = {
    "warlock": _warlock,
    "barbarian": _barbarian,
    "rogue": _rogue,
    "fighter": _fighter,
    "monk": _monk,
    "cleric": _cleric,
    "paladin": _paladin,
    "druid": _druid,
    "bard": _bard,
    "sorcerer": _sorcerer,
    "wizard": _wizard,
    "ranger": _ranger,
}

# ---- Subclass resources (R6) -----------------------------------------------
# Ruleset choice: a 2024 table is read only under ruleset "2024" (`ctx.subclass_table`
# returns None otherwise), exactly like the class tables. A subclass record from
# either edition can sit in a draft under any ruleset, so the record's own edition
# picks the data when it can: the XPHB record uses its table under "2024" and the
# 2014 formula otherwise; the TCE record always uses the formula.

def _by_level(table: list[tuple[int, object]], level: int):
    value = None
    for min_level, v in table:
        if level >= min_level:
            value = v
    return value


def _psionic_dice(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    if level < reference_data.SUBCLASS_RESOURCE_MIN_LEVEL:
        return []
    sub_id = rc.get("subclass_id")
    count = ctx.subclass_table(sub_id, "number", level) if sub_id.endswith("-xphb") else None
    die = ctx.subclass_table(sub_id, "die-size", level) if sub_id.endswith("-xphb") else None
    if count and die:
        # 2024: one die back on a short rest, all on a long rest.
        return [_resource(rc, "Psionic Energy Dice", kind="subclass", uses=count, die=die, recharge="long",
                          details={"shortRestRegains": 1})]
    # 2014 formula (TCE): twice the proficiency bonus; all on a long rest, plus a
    # bonus action to regain one (once per short or long rest).
    return [_resource(rc, "Psionic Energy Dice", kind="subclass",
                      uses=reference_data.PSIONIC_DICE_PB_MULTIPLIER_2014 * ctx.prof_bonus,
                      die=_by_level(reference_data.PSIONIC_DIE_BY_LEVEL_2014, level), recharge="long",
                      details={"bonusActionRegainsOne": True})]


def _battle_master(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    if level < reference_data.SUBCLASS_RESOURCE_MIN_LEVEL:
        return []
    mods = ctx.modifiers
    dc = reference_data.MANEUVER_DC_BASE + ctx.prof_bonus + max(mods.get("STR", 0), mods.get("DEX", 0))
    return [_resource(rc, "Superiority Dice", kind="subclass",
                      uses=_by_level(reference_data.SUPERIORITY_DICE_COUNT, level),
                      die=_by_level(reference_data.SUPERIORITY_DIE_BY_LEVEL, level),
                      recharge="short-or-long", dc=dc)]


def _arcane_archer(ctx: Ctx, rc: dict) -> list[dict]:
    if rc["level"] < reference_data.SUBCLASS_RESOURCE_MIN_LEVEL:
        return []
    return [_resource(rc, "Arcane Shot", kind="subclass", uses=reference_data.ARCANE_SHOT_USES,
                      recharge="short-or-long")]


_SUBCLASS_BUILDERS: dict[str, Callable[[Ctx, dict], list[dict]]] = {
    "psi-warrior-tce": _psionic_dice,
    "psi-warrior-xphb": _psionic_dice,
    "soulknife-tce": _psionic_dice,
    "soulknife-xphb": _psionic_dice,
    "battle-master-phb": _battle_master,
    "battle-master-xphb": _battle_master,
    "arcane-archer-xge": _arcane_archer,
}

# Extra Attack features that are not in the Fighter's `extra_attacks` level
# column: feature id -> (class id, subclass id or None, level). Verified against
# the catalog by script (R2): every feature named "Extra Attack" is listed here.
EXTRA_ATTACK_FEATURES: dict[str, tuple[str, str | None, int]] = {
    "barbarian-extra-attack": ("barbarian", None, 5),
    "monk-extra-attack": ("monk", None, 5),
    "paladin-extra-attack": ("paladin", None, 5),
    "ranger-extra-attack": ("ranger", None, 5),
    "valor-phb-6-extra-attack": ("bard", "valor-phb", 6),
    "swords-xge-6-extra-attack": ("bard", "swords-xge", 6),
    "valor-xphb-6-extra-attack": ("bard", "valor-xphb", 6),
    "bladesinging-tce-6-extra-attack": ("wizard", "bladesinging-tce", 6),
    "bladesinger-frhof-6-extra-attack": ("wizard", "bladesinger-frhof", 6),
}


def attacks_per_action(resolved_classes: list[dict]) -> int:
    """1 + the largest number of extra attacks any one source gives. PHB 164:
    Extra Attack from more than one class does not add together. The Fighter
    reads `extra_attacks` from its level row (1/2/3 at 5/11/20); every other
    source gives one extra attack."""
    best = 0
    for rc in resolved_classes:
        if not rc.get("cls"):
            continue
        if rc["cls_id"] == "fighter":
            best = max(best, _class_specific(rc).get("extra_attacks") or 0)
        for cls_id, sub_id, level in EXTRA_ATTACK_FEATURES.values():
            if cls_id == rc["cls_id"] and rc["level"] >= level and (sub_id is None or sub_id == rc.get("subclass_id")):
                best = max(best, 1)
    return 1 + best


def resources_for(catalog, resolved_classes: list[dict], modifiers: dict, prof_bonus: int, ruleset: str,
                  choices: dict | None = None, warnings_out: list | None = None) -> list[dict]:
    """Every class's resources in class order; a class's subclass entries
    follow its own. `warnings_out` receives non-blocking warnings."""
    ctx = Ctx(catalog, ruleset, modifiers or {}, prof_bonus, choices or {}, warnings_out)
    out: list[dict] = []
    for rc in resolved_classes:
        if not rc.get("cls"):
            continue
        builder = _BUILDERS.get(rc["cls_id"])
        if builder:
            out += builder(ctx, rc)
        sub_builder = _SUBCLASS_BUILDERS.get(rc.get("subclass_id") or "")
        if sub_builder:
            out += sub_builder(ctx, rc)
    # G1: the 2024 Multiclassing chapter has no merge rule and every class text
    # says "this class's Channel Divinity", so 2024 keeps separate per-class pools.
    return out if ruleset == "2024" else _merge_channel_divinity(out)


def _merge_channel_divinity(resources: list[dict]) -> list[dict]:
    """PHB 164: Channel Divinity from several classes is one feature; the extra
    class adds effect options, not uses. Keep one entry, uses = max over the
    classes (first class on a tie), at the position of the winning class."""
    cds = [r for r in resources if r["name"] == "Channel Divinity"]
    if len(cds) < 2:
        return resources
    best = cds[0]
    for r in cds[1:]:
        if (r["uses"] or 0) > (best["uses"] or 0):
            best = r
    best = {**best, "details": {**(best.get("details") or {}), "classes": [r["classId"] for r in cds]}}
    return [best if r["name"] == "Channel Divinity" and r["classId"] == best["classId"] else r
            for r in resources if r["name"] != "Channel Divinity" or r["classId"] == best["classId"]]


def annotate_attacks(attacks: list[dict], resources: list[dict], items: list[dict]) -> list[dict]:
    """D5: attack-row notes from class resources. A Barbarian's Rage adds
    "Rage: +N damage" to melee rows that use Strength (PHB: melee weapon attack
    using Strength); a Rogue's Sneak Attack adds "Sneak Attack Xd6" to finesse
    and ranged weapon rows; under 2024 a picked Divine Strike / Primal Strike adds
    "Divine Strike: +1d8 necrotic or radiant (once per turn)" to every weapon row (C6c-2). Rows with no catalog weapon (the Monk's unarmed
    strike) get neither. The notes are information; the damage number is unchanged."""
    by_id = {r["id"]: r for r in resources}
    rage = (by_id.get("barbarian:rage") or {}).get("details", {}).get("damageBonus")
    sneak = (by_id.get("rogue:sneak-attack") or {}).get("dice")
    strikes = [(r["name"], r["dice"], r["details"]["damageTypes"].lower())
               for r in (by_id.get("cleric:divine-strike"), by_id.get("druid:primal-strike")) if r]  # C6c-2
    if not rage and not sneak and not strikes:
        return attacks
    weapons = {i["index"]: i for i in items}
    out = []
    for a in attacks:
        item = weapons.get(a["itemId"])
        notes = list(a["notes"])
        if item:
            ranged = item.get("weapon_range") == "Ranged"
            finesse = any(p["index"] == "finesse" for p in item.get("properties", []))
            if rage and a["ability"] == "STR" and not ranged:
                notes.append(f"Rage: +{rage} damage")
            if sneak and (finesse or ranged):
                notes.append(f"Sneak Attack {sneak}")
            for name, dice, types in strikes:
                notes.append(f"{name}: +{dice} {types} (once per turn)")
        out.append({**a, "notes": notes})
    return out
