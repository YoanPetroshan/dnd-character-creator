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
from engine import class_choices_2024, subclass_options_2024

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
    out = [_resource(rc, "Arcane Recovery", pool=pool or -(-level // 2), recharge="long",
                     details={"maxSlotLevel": reference_data.ARCANE_RECOVERY_MAX_SLOT_LEVEL, "onShortRest": True})]
    if ctx.ruleset != "2024":
        out += _signature_spells(ctx, rc)  # RP15: SRD Signature Spell (2024 builds it in the tail)
    return out


def _ranger(ctx: Ctx, rc: dict) -> list[dict]:
    # 2024 only: Favored Enemy is Hunter's Mark with free casts. The 2014 one is a choice, not a resource.
    uses = ctx.table("ranger", "favored-enemy", rc["level"])
    if uses is None:
        return []
    return [_resource(rc, "Favored Enemy (Hunter's Mark)", uses=uses, recharge="long")]


def _warlock(ctx: Ctx, rc: dict) -> list[dict]:
    """Warlock resources. R8/C7b: entries for invocations with a number or a text-only effect (Agonizing Blast:
    CHA modifier; Thirsting Blade, Repelling Blast, ...: notes), one per repeat instance ("Agonizing Blast (2)").
    2024 (C7b): Magical Cunning and Contact Patron. `ctx.choices` is read after the invocation gate."""
    out = _warlock_features_2024(ctx, rc)
    if not isinstance(ctx.choices, list):
        return out
    cha = ctx.modifiers.get("CHA", 0)
    for c in ctx.choices:
        feat_pick = (c.get("source") or {}).get("kind") == "feat" and c.get("id", "").endswith(":invocation")  # FE9 Eldritch Adept
        if not feat_pick and ((c.get("source") or {}).get("id") != "warlock" or ":invocations:" not in c.get("id", "")):
            continue
        for inst in c.get("selected") or []:  # C7a: `<id>~k` repeat instances
            sel = class_choices_2024.invocation_base_id(inst)
            k = class_choices_2024.invocation_instance(inst)
            suffix = f" ({k})" if k > 1 else ""
            eff = class_choices_2024.invocation_effect(ctx.catalog, sel) or {}
            bonus = eff.get("resource_bonus")
            target = class_choices_2024.instance_target(  # C7c: the picked cantrip (RP20: the feat card is the holder)
                ctx.choices, inst, c["id"] + ":" if feat_pick else class_choices_2024.DEPENDENT_PREFIX)
            target_spell = (ctx.catalog.spells.get(target) or {}) if target else {}
            if bonus:
                if bonus.get("spell"):
                    details = {"spell": bonus["spell"]}
                elif target_spell:
                    details = {"spell": target, "note": f"Add your Charisma modifier to the damage rolls of {target_spell['name']}."}
                else:
                    details = {"note": "Add your Charisma modifier to the damage rolls of one known Warlock cantrip that deals damage."}
                out.append(_resource(rc, bonus["name"] + suffix, bonus=cha, details=details))
            elif eff.get("note") and "innate_spell" not in eff and "swim_equals_walk" not in eff:
                label = (ctx.catalog.features.get(sel) or {}).get("name", sel).replace("Eldritch Invocation: ", "") + suffix
                note = eff["note"].format(cha_names=max(1, cha), cha_names_word="name" if max(1, cha) == 1 else "names",
                                          spear_range=30 * rc["level"])
                details = {"note": note}
                if target_spell:
                    details = {"spell": target, "note": _target_note(sel, target_spell, rc["level"], note)}
                out.append(_resource(rc, label, details=details))
    return out


def _target_note(invocation_id: str, spell: dict, warlock_level: int, generic: str) -> str:
    """C7c: the note of Eldritch Spear / Repelling Blast once the target cantrip is picked."""
    if invocation_id == class_choices_2024.SPEAR_ID:
        base = class_choices_2024.spell_range_feet(spell) or 0
        extra = 30 * warlock_level
        return f"{spell['name']}: range {base} ft + {extra} ft (30 x Warlock level {warlock_level}) = {base + extra} ft."
    if invocation_id == class_choices_2024.REPELLING_ID:
        return f"{spell['name']}: when you hit a Large or smaller creature you can push it up to 10 feet straight away from you."
    return generic


def _pact_slot_count(rc: dict) -> int:
    from engine.spells import warlock_pact_magic_slots
    return sum(warlock_pact_magic_slots((rc.get("level_row") or {}).get("spellcasting")).values())


def _warlock_features_2024(ctx: Ctx, rc: dict) -> list[dict]:
    """Magical Cunning (2) and Contact Patron (9), 2024 only, when the XPHB feature records exist. Texts
    (XPHB): Magical Cunning "regain expended Pact Magic spell slots but no more than a number equal to half your
    maximum (round up) ... until you finish a Long Rest"; Contact Patron "cast [Contact Other Plane] without
    expending a spell slot ... can't do so in this way again until you finish a Long Rest"."""
    if ctx.ruleset != "2024":
        return []
    features = getattr(ctx.catalog, "features", {}) or {}
    out = []
    if rc["level"] >= 2 and "xphb-warlock-2-magical-cunning" in features:
        slots = _pact_slot_count(rc)
        note = (f"1 minute rite: regain expended Pact Magic slots, up to half your maximum Pact Magic slots ({slots}) "
                f"rounded up = {-(-slots // 2)}") if slots else "1 minute rite: regain up to half your maximum Pact Magic slots, rounded up"
        if rc["level"] >= 20 and "xphb-warlock-20-eldritch-master" in features:  # F3a-7: "you regain all your expended Pact Magic spell slots"
            note = (f"1 minute rite: regain ALL your expended Pact Magic slots (Eldritch Master; maximum {slots})" if slots
                    else "1 minute rite: regain ALL your expended Pact Magic slots (Eldritch Master)")
        out.append(_resource(rc, "Magical Cunning", uses=1, recharge="long", details={"note": note}))
    if rc["level"] >= 9 and "xphb-warlock-9-contact-patron" in features:
        out.append(_resource(rc, "Contact Patron", uses=1, recharge="long", details={
            "note": "Cast Contact Other Plane without a spell slot to contact your patron; you automatically succeed on its saving throw."}))
    return out


def _feature_level(ctx: Ctx, feature_id: str) -> int | None:
    """The level of an XPHB feature record in the catalog, or None when the record is missing."""
    feature = (getattr(ctx.catalog, "features", None) or {}).get(feature_id)
    return (feature.get("level") or 1) if feature else None


def _note_vars(ctx: Ctx, rc: dict) -> dict:
    """Variables for the `{name}` fields of the 2024 note templates (RESOURCE_TAIL_2024 / RESOURCE_NOTES_2024 and the
    RP11 subclass tables): the class level, the final ability modifiers and the class-specific numbers the XPHB texts
    name. `dc_*` is the save DC "8 plus your <ability> modifier and Proficiency Bonus"."""
    level, mods, pb = rc["level"], ctx.modifiers, ctx.prof_bonus
    wis, dex, cha = mods.get("WIS", 0), mods.get("DEX", 0), mods.get("CHA", 0)
    int_, str_ = mods.get("INT", 0), mods.get("STR", 0)
    con = mods.get("CON", 0)
    spark = 1
    for first, dice in reference_data.DIVINE_SPARK_DICE_2024:
        if level >= first:
            spark = dice
    zealot = lands = 0
    for first, dice in reference_data.ZEALOT_WARRIOR_DICE_2024:
        if level >= first:
            zealot = dice
    for first, dice in reference_data.LANDS_AID_DICE_2024:
        if level >= first:
            lands = dice
    cha_min1, int_min1 = max(1, cha), max(1, int_)
    return {"level": level, "half_level": level // 2, "twice_level": 2 * level, "five_level": 5 * level,
            "wis": wis, "dex": dex, "cha": cha, "wis_min1": max(1, wis), "cha_min1": cha_min1,
            "dex_level": dex + level, "dc_wis": 8 + pb + wis, "dc_cha": 8 + pb + cha, "dc_dex": 8 + pb + dex,
            "ma_die": (_martial_arts_die(ctx, rc) or "d6") if rc["cls_id"] == "monk" else "d6",
            "spark_dice": spark,
            # RP11
            "int": int_, "int_min1": int_min1, "dc_str": 8 + pb + str_, "dc_int": 8 + pb + int_, "pb": pb,
            "level_plus1": level + 1, "third_level": level // 3, "three_level": 3 * level,
            "half_level_up": (level + 1) // 2, "cha_pb": cha + pb, "moon_ac": 13 + wis, "ward_hp": 2 * level + int_,
            "zealot_dice": zealot, "lands_aid": lands,
            "cha_creatures": f"{cha_min1} creature" + ("s" if cha_min1 != 1 else ""),
            "int_creatures": f"{int_min1} creature" + ("s" if int_min1 != 1 else ""),
            "cha_dice": f"{cha_min1} " + ("dice" if cha_min1 != 1 else "die"),
            # W6 / W7 (2014)
            "con": con, "survivor": 5 + con, "blessing": max(1, cha + level),
            "pact_slots": _pact_slot_count(rc) if rc["cls_id"] == "warlock" else 0,
            # W8 (2014 book subclasses)
            "con_min1": max(1, con), "str_min1": max(1, str_), "cha_min2": max(2, cha), "four_level": 4 * level,
            "five_plus_level": 5 + level, "five_plus_twice_level": 5 + 2 * level, "twenty_level": 20 * level,
            "dc_con": 8 + pb + con, "echo_ac": 14 + pb,
            # W8c
            "wis_level_min1": max(1, wis + level), "five_plus_wis": 5 + wis,
            "wails": f"{(((level + 1) // 2) + 1) // 2}d6"}


def _staged(ctx: Ctx, level: int, default, stages):
    """The value of the last listed (feature id, value) whose XPHB record level the class has reached, else `default`."""
    value = default
    for stage_id, stage_value in stages or ():
        stage_level = _feature_level(ctx, stage_id)
        if stage_level is not None and level >= stage_level:
            value = stage_value
    return value


def _render_note(ctx: Ctx, rc: dict, spec: dict) -> str:
    """The note of a 2024 table entry: its template with the variables, the spec's own `vars` (the value of the
    last listed feature record whose level the class has reached, else the default) and the `extras`
    (feature id, template) whose record level has been reached appended with "; "."""
    level = rc["level"]
    values = _note_vars(ctx, rc)
    for name, (default, stages) in (spec.get("vars") or {}).items():
        values[name] = _staged(ctx, level, default, stages)
    for name, table in (spec.get("level_vars") or {}).items():  # W7: tables that live only in the text
        values[name] = next((v for first, v in reversed(table) if level >= first), None)
    note = spec["note"].format(**values)
    for extra_id, text in spec.get("extras") or ():
        extra_level = _feature_level(ctx, extra_id)
        if extra_level is not None and level >= extra_level:
            note += "; " + text.format(**values)
    return note


def _tail_2024(ctx: Ctx, rc: dict) -> list[dict]:
    """R9 (decision E14) and RP10: XPHB class features with a use count, a recharge or numbers that no class table
    carries (`reference_data.RESOURCE_TAIL_2024`), plus Wizard Signature Spells from the picked spells. Ruleset
    "2024" only; an entry needs its XPHB feature record in the catalog and the class level at that record's level,
    so an SRD-only catalog gives nothing. Appended after the class's own entries (Sorcery Points stay first)."""
    if ctx.ruleset != "2024":
        return []
    level, cls_id = rc["level"], rc["cls_id"]
    out = []
    for spec in reference_data.RESOURCE_TAIL_2024:
        if spec["class"] != cls_id:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or level < first:
            continue
        note = _render_note(ctx, rc, spec)
        details = {"note": note}
        if spec.get("heal_martial_arts"):
            die = _martial_arts_die(ctx, rc)
            if die:
                details["heal"] = f"1{die}+{level}"
        uses = max(1, ctx.modifiers.get("WIS", 0)) if spec["uses"] == "wis_min1" else spec["uses"]
        out.append(_resource(rc, spec["name"], uses=uses, recharge=spec["recharge"], details=details))
    if cls_id == "wizard":
        out += _signature_spells(ctx, rc)
    return out


def _attach_notes_2024(ctx: Ctx, rc: dict, resources: list[dict]) -> None:
    """RP10: add the `reference_data.RESOURCE_NOTES_2024` sentences to the class's existing resources (mutates the
    given list's dicts). Ruleset "2024" only; skipped when the target resource or the feature record is missing or
    the class level is below the record's level. An existing note is kept and extended with "; "."""
    if ctx.ruleset != "2024":
        return
    for spec in reference_data.RESOURCE_NOTES_2024:
        if spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        target = next((r for r in resources if r["id"] == spec["target"]), None)
        if first is None or rc["level"] < first or target is None:
            continue
        note = _render_note(ctx, rc, spec)
        details = dict(target.get("details") or {})
        details["note"] = f"{details['note']}; {note}" if details.get("note") else note
        target["details"] = details


def _field_2014(ctx: Ctx, rc: dict, spec: dict, key: str, values: dict):
    """A W6 / W7 spec field: a literal, an "@name" variable (`_note_vars` / `vars` / `level_vars`) or a staged tuple
    (default, ((feature id, value), ...))."""
    raw = spec.get(key)
    if isinstance(raw, str) and raw.startswith("@"):
        return values[raw[1:]]
    if isinstance(raw, tuple):
        return _staged(ctx, rc["level"], raw[0], raw[1])
    return raw


def _values_2014(ctx: Ctx, rc: dict, spec: dict) -> dict:
    values = _note_vars(ctx, rc)
    for name, (default, stages) in (spec.get("vars") or {}).items():
        values[name] = _staged(ctx, rc["level"], default, stages)
    for name, table in (spec.get("level_vars") or {}).items():
        values[name] = next((v for first, v in reversed(table) if rc["level"] >= first), None)
    return values


def _entry_2014(ctx: Ctx, rc: dict, spec: dict, *, kind: str = "class") -> dict:
    values = _values_2014(ctx, rc, spec)
    fields = {key: _field_2014(ctx, rc, spec, key, values) for key in ("die", "dice", "pool")}
    return _resource(rc, spec["name"], kind=kind, uses=_field_2014(ctx, rc, spec, "uses", values),
                     recharge=_field_2014(ctx, rc, spec, "recharge", values),
                     details={"note": _render_note(ctx, rc, spec)}, **fields)


def _add_note(resources: list[dict], target_id: str, note: str) -> bool:
    target = next((r for r in resources if r["id"] == target_id), None)
    if target is None:
        return False
    details = dict(target.get("details") or {})
    details["note"] = f"{details['note']}; {note}" if details.get("note") else note
    target["details"] = details
    return True


def _tail_2014(ctx: Ctx, rc: dict) -> list[dict]:
    """W6 (finding F4): SRD class features with a use count, a rest rule or a computed number
    (`reference_data.RESOURCE_TAIL_2014`). Rulesets "mixed" and "2014" only; an entry needs its SRD feature record in
    the catalog and the class level at that record's level. Appended after the class's own entries."""
    if ctx.ruleset == "2024":
        return []
    out = []
    for spec in reference_data.RESOURCE_TAIL_2014:
        if spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or rc["level"] < first:
            continue
        out.append(_entry_2014(ctx, rc, spec))
    return out


def _attach_notes_2014(ctx: Ctx, rc: dict, resources: list[dict]) -> None:
    """W6: add the `reference_data.RESOURCE_NOTES_2014` sentences to the class's existing resources. Rulesets "mixed"
    and "2014" only; skipped when the target resource or the feature record is missing or the class level is below the
    record's level. An existing note is kept and extended with "; "."""
    if ctx.ruleset == "2024":
        return
    for spec in reference_data.RESOURCE_NOTES_2014:
        if spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or rc["level"] < first:
            continue
        _add_note(resources, spec["target"], _render_note(ctx, rc, spec))


def _subclass_tail_2014(ctx: Ctx, rc: dict, resources: list[dict]) -> list[dict]:
    """W7 / W8 (finding F4): subclass features with a use count, a rest rule or a computed number
    (`reference_data.SUBCLASS_TAIL_2014` / `SUBCLASS_NOTES_2014` for the 12 SRD subclass ids, `SUBCLASS_TAIL_2014_BOOKS` /
    `SUBCLASS_NOTES_2014_BOOKS` for the imported book subclass ids). Rulesets "mixed" and "2014" only and only for the
    class's selected subclass; an entry needs its SRD feature record in the
    catalog and the class level at that record's level. New resources (source kind "subclass") are returned; the notes
    are added to the matching resource of `resources` (an existing note is kept and extended with "; ")."""
    sub_id = rc.get("subclass_id")
    if ctx.ruleset == "2024" or not sub_id:
        return []
    level = rc["level"]
    out: list[dict] = []
    for spec in reference_data.SUBCLASS_TAIL_2014 + reference_data.SUBCLASS_TAIL_2014_BOOKS:  # W7 SRD ids, W8 book ids
        if spec["subclass"] != sub_id or spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or level < first:
            continue
        out.append(_entry_2014(ctx, rc, spec, kind="subclass"))
    for spec in reference_data.SUBCLASS_NOTES_2014 + reference_data.SUBCLASS_NOTES_2014_BOOKS:
        if spec["subclass"] != sub_id or spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or level < first:
            continue
        _add_note(resources, spec["target"], _render_note(ctx, rc, spec))
    return out


def _subclass_tail_2024(ctx: Ctx, rc: dict, resources: list[dict]) -> list[dict]:
    """RP11: XPHB subclass features with a use count, a recharge or numbers that spend a resource
    (`reference_data.SUBCLASS_TAIL_2024` / `SUBCLASS_NOTES_2024`). Ruleset "2024" only and only for the class's
    selected subclass; an entry needs its XPHB feature record in the catalog and the class level at that record's
    level, so an SRD-only catalog gives nothing. New resources (source kind "subclass") are returned; the notes
    are added to the matching resource of `resources` (the class's own and the R6 subclass entries; an existing
    note is kept and extended with "; ")."""
    sub_id = rc.get("subclass_id")
    if ctx.ruleset != "2024" or not sub_id:
        return []
    level = rc["level"]
    out: list[dict] = []
    for spec in reference_data.SUBCLASS_TAIL_2024:
        if spec["subclass"] != sub_id or spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        if first is None or level < first:
            continue
        values = _note_vars(ctx, rc)
        uses = spec["uses"]
        uses = values[uses] if isinstance(uses, str) else _staged(ctx, level, uses, spec.get("uses_stages"))
        recharge = _staged(ctx, level, spec["recharge"], spec.get("recharge_stages"))
        out.append(_resource(rc, spec["name"], kind="subclass", uses=uses, recharge=recharge, die=spec.get("die"),
                             details={"note": _render_note(ctx, rc, spec)}))
    for spec in reference_data.SUBCLASS_NOTES_2024:
        if spec["subclass"] != sub_id or spec["class"] != rc["cls_id"]:
            continue
        first = _feature_level(ctx, spec["feature"])
        target = next((r for r in resources if r["id"] == spec["target"]), None)
        if first is None or level < first or target is None:
            continue
        note = _render_note(ctx, rc, spec)
        details = dict(target.get("details") or {})
        details["note"] = f"{details['note']}; {note}" if details.get("note") else note
        target["details"] = details
    return out


def _subclass_pick_notes_2024(ctx: Ctx, rc: dict) -> list[dict]:
    """RP12: the number that rides on a 2024 subclass proficiency pick (Fey Wanderer's Otherworldly Glamour: the
    Wisdom bonus to Charisma checks), as a note-only subclass resource (`SUBCLASS_PICKS_2024[*]["note"]`). Ruleset
    "2024" only and only for the selected subclass; needs the XPHB feature record at or below the class level."""
    sub_id = rc.get("subclass_id")
    if ctx.ruleset != "2024" or not sub_id:
        return []
    out = []
    for spec in reference_data.SUBCLASS_PICKS_2024:
        first = _feature_level(ctx, spec["feature"])
        if "note" not in spec or spec["subclass"] != sub_id or spec["class"] != rc["cls_id"] or first is None or rc["level"] < first:
            continue
        out.append(_resource(rc, spec["label"], kind="subclass", details={"note": _render_note(ctx, rc, spec)}))
    return out


def _subclass_option_notes_2024(ctx: Ctx, rc: dict) -> list[dict]:
    """RP13: a note-only subclass resource per picked option that carries a `note` (Hunter's Prey, Defensive Tactics,
    Elemental Affinity with the Charisma modifier). Ruleset "2024" only and only for the selected subclass of this
    class entry; the picked options come from the resolved cards, so an option the card no longer offers gives
    nothing."""
    sub_id = rc.get("subclass_id")
    if ctx.ruleset != "2024" or not sub_id:
        return []
    out = []
    for cls_id, _level, _fid, spec, _key, option in subclass_options_2024.selected(ctx.choices):
        if cls_id != rc["cls_id"] or spec["subclass"] != sub_id or "note" not in option:
            continue
        out.append(_resource(rc, subclass_options_2024.note_name(spec, option), kind="subclass",
                             details={"note": option["note"].format(**_note_vars(ctx, rc))}))
    return out


def _signature_spells(ctx: Ctx, rc: dict) -> list[dict]:
    """Wizard 20 Signature Spells: one cast per picked spell per Short or Long Rest; nothing while unpicked."""
    sig = reference_data.SIGNATURE_SPELLS_2024 if ctx.ruleset == "2024" else reference_data.SIGNATURE_SPELLS_2014
    first = _feature_level(ctx, sig["feature"])
    if first is None or rc["level"] < first or not isinstance(ctx.choices, list):
        return []
    picked = next((c.get("selected") or [] for c in ctx.choices if c.get("id") == sig["choice"]), [])
    spells = getattr(ctx.catalog, "spells", {}) or {}
    names = [(spells.get(sid) or {}).get("name", sid) for sid in picked]
    if not names:
        return []
    return [_resource(rc, "Signature Spells", uses=len(names), recharge=sig["recharge"], details={
        "note": f"Cast each of {', '.join(names)} once at {'level 3' if ctx.ruleset == '2024' else '3rd level'} "
                f"without a spell slot"})]


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
        mine = builder(ctx, rc) if builder else []
        mine += _tail_2024(ctx, rc)  # R9 / RP10: 2024 only
        _attach_notes_2024(ctx, rc, mine)  # RP10: 2024 only
        mine += _tail_2014(ctx, rc)  # W6: mixed / 2014 only
        _attach_notes_2014(ctx, rc, mine)  # W6: mixed / 2014 only
        sub_builder = _SUBCLASS_BUILDERS.get(rc.get("subclass_id") or "")
        sub = sub_builder(ctx, rc) if sub_builder else []
        out += mine + sub
        out += _subclass_tail_2024(ctx, rc, mine + sub)  # RP11: 2024 only, after the class and R6 entries
        out += _subclass_tail_2014(ctx, rc, mine + sub)  # W7: mixed / 2014 only
        out += _subclass_pick_notes_2024(ctx, rc)  # RP12: 2024 only
        out += _subclass_option_notes_2024(ctx, rc)  # RP13: 2024 only
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


def _picked_attack_notes(by_id: dict) -> list[tuple[dict, dict]]:
    """RP13: the (spec, option) pairs whose note-only resource exists and whose option adds an attack-row note."""
    out = []
    for spec in reference_data.SUBCLASS_OPTIONS_2024.values():
        for option in spec["options"].values():
            rid = f"{spec['class']}:{_slug(subclass_options_2024.note_name(spec, option))}"
            if "attack_note" in option and rid in by_id:
                out.append((spec, option))
    return out


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
    prey = [spec_option["attack_note"] for spec, spec_option in _picked_attack_notes(by_id)]  # RP13 Colossus Slayer
    if not rage and not sneak and not strikes and not prey:
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
            notes += prey
        out.append({**a, "notes": notes})
    return out
