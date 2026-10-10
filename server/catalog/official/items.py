"""5etools `items-base.json` -> SRD-shaped mundane weapon/armor records (Slice 11c).

Only `baseitem` records of the weapon (M, R) and armor (LA, MA, HA, S) types
with no magic rarity are read; everything the SRD equipment list already has
(by `srd`/`srd52` flag or by name) and the 2024 reprints of kept 2014 items
are skipped. Reload and burst-fire are not modelled; weapon mastery is attached
afterwards by `attach_masteries` (C1).
"""
from __future__ import annotations

import json
from pathlib import Path

from catalog.reference_data import RULESET_2024_SOURCES

from .common import slug
from .equipment import _find_srd_equipment_item

_WEAPON_TYPES = {"M", "R"}
_ARMOR_TYPES = {"LA": "Light", "MA": "Medium", "HA": "Heavy", "S": "Shield"}
_SKIPPED_AGES = {"modern", "futuristic"}  # firearms of a different genre; renaissance (musket, pistol) stay
_DAMAGE_TYPES = {
    "B": "bludgeoning", "P": "piercing", "S": "slashing", "R": "radiant", "O": "force", "F": "fire",
    "N": "necrotic", "C": "cold", "L": "lightning", "I": "poison", "A": "acid", "Y": "psychic", "T": "thunder",
}
_PROPERTIES = {
    "F": "finesse", "L": "light", "H": "heavy", "2H": "two-handed", "T": "thrown", "V": "versatile",
    "R": "reach", "A": "ammunition", "AF": "ammunition", "LD": "loading", "S": "special",
}


def load_raw_base_items(path) -> list[dict]:
    """Every `baseitem` record of `items-base.json`; [] when missing or broken."""
    if not path:
        return []
    try:
        with open(Path(path), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return [i for i in data.get("baseitem", []) if isinstance(i, dict)] if isinstance(data, dict) else []


def _type_code(raw: dict) -> str:
    return str(raw.get("type") or "").split("|")[0]


def _eligible(raw: dict) -> bool:
    """A mundane weapon or armor that is not part of the SRD."""
    if _type_code(raw) not in _WEAPON_TYPES | set(_ARMOR_TYPES):
        return False
    if raw.get("rarity") not in (None, "none") or raw.get("srd") or raw.get("srd52") or "name" not in raw:
        return False
    return raw.get("age") not in _SKIPPED_AGES


def _cost(value) -> dict:
    value = int(value or 0)
    if value and value % 100 == 0:
        return {"quantity": value // 100, "unit": "gp"}
    if value and value % 10 == 0:
        return {"quantity": value // 10, "unit": "sp"}
    return {"quantity": value, "unit": "cp"}


def _range(text) -> dict | None:
    try:
        normal, _, long_ = str(text).partition("/")
        out = {"normal": int(normal)}
        if long_:
            out["long"] = int(long_)
        return out
    except ValueError:
        return None


def _item_from_5etools(raw: dict) -> dict | None:
    """SRD-shaped item (without an id; see `convert_items`) or None."""
    if not _eligible(raw):
        return None
    code = _type_code(raw)
    source = raw.get("source", "PHB")
    out: dict = {"name": raw["name"], "source": source,
                 "ruleset": "2024" if source in RULESET_2024_SOURCES else "2014",
                 "weight": raw.get("weight", 0), "cost": _cost(raw.get("value"))}
    if code in _WEAPON_TYPES:
        props = [p for p in dict.fromkeys(_PROPERTIES.get(str(c).split("|")[0]) for c in raw.get("property") or []) if p]
        ranged = code == "R"
        category = "Martial" if raw.get("weaponCategory") == "martial" else "Simple"
        out.update({
            "equipment_category": {"index": "weapon", "name": "Weapon"},
            "weapon_category": category, "weapon_range": "Ranged" if ranged else "Melee",
            "category_range": f"{category} {'Ranged' if ranged else 'Melee'}",
            "properties": [{"index": p, "name": p.replace("-", " ").title()} for p in props],
        })
        dmg_type = _DAMAGE_TYPES.get(raw.get("dmgType"))
        if raw.get("dmg1") and dmg_type:
            out["damage"] = {"damage_dice": raw["dmg1"], "damage_type": {"index": dmg_type, "name": dmg_type.title()}}
            if raw.get("dmg2"):
                out["two_handed_damage"] = {"damage_dice": raw["dmg2"],
                                            "damage_type": {"index": dmg_type, "name": dmg_type.title()}}
        reach = _range(raw.get("range")) if raw.get("range") else None
        if ranged:
            out["range"] = reach or {"normal": 5}
        else:
            out["range"] = {"normal": 10 if "reach" in props else 5}
            if "thrown" in props and reach:
                out["throw_range"] = reach
    else:
        armor_category = _ARMOR_TYPES[code]
        ac: dict = {"base": int(raw.get("ac") or 0), "dex_bonus": code in ("LA", "MA")}
        if code == "MA":
            ac["max_bonus"] = 2
        out.update({
            "equipment_category": {"index": "armor", "name": "Armor"}, "armor_category": armor_category,
            "armor_class": ac, "str_minimum": int(raw.get("strength") or 0),
            "stealth_disadvantage": bool(raw.get("stealth")),
        })
        if code == "S":
            out["armor_class"] = {"base": ac["base"], "dex_bonus": False}
    return out


def convert_items(raw_items, existing_ids) -> dict[str, dict]:
    """index -> SRD-shaped item for every importable base item. Skips the
    eligible-by-type records the SRD list already has by name ("Light
    Crossbow" vs "Crossbow, light"), and 2024 reprints of kept 2014 items
    (by name or `reprintedAs`). Ids: the bare slug, `slug-source` on a clash;
    a 2024 item with no 2014 counterpart always gets `slug-source`."""
    candidates = [r for r in raw_items if _eligible(r) and not _find_srd_equipment_item(r["name"])]
    kept_2014 = [r for r in candidates if r.get("source") not in RULESET_2024_SOURCES]
    twin_names = {r["name"] for r in kept_2014}
    for r in kept_2014:
        for ref in r.get("reprintedAs") or []:
            if isinstance(ref, str):
                twin_names.add(ref.split("|")[0])
    out: dict[str, dict] = {}
    for raw in candidates:
        is_2024 = raw.get("source") in RULESET_2024_SOURCES
        if is_2024 and raw["name"] in twin_names:
            continue
        item = _item_from_5etools(raw)
        if item is None:
            continue
        base = slug(raw["name"])
        index = f"{base}-{raw['source'].lower()}" if is_2024 else base
        if index in out or index in existing_ids:
            index = f"{base}-{raw['source'].lower()}"
        if index in out or index in existing_ids:
            continue
        item["index"] = index
        out[index] = item
    return out


def load_raw_item_masteries(path) -> list[dict]:
    """Every `itemMastery` record of `items-base.json`; [] when missing or broken."""
    if not path:
        return []
    try:
        with open(Path(path), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return [m for m in data.get("itemMastery", []) if isinstance(m, dict)] if isinstance(data, dict) else []


def convert_item_masteries(raw_masteries) -> dict[str, list[str]]:
    """{mastery name: desc paragraphs} from the XPHB `itemMastery` records."""
    from .spells import _flatten_entries

    return {m["name"]: _flatten_entries(m.get("entries") or [])
            for m in raw_masteries or [] if m.get("name") and m.get("source") == "XPHB"}


def _normalize_weapon_name(name: str) -> str:
    """"Crossbow, light" -> "light crossbow"; everything else lowercased."""
    name = str(name or "").strip().lower()
    head, comma, tail = name.partition(",")
    return f"{tail.strip()} {head.strip()}" if comma else name


def attach_masteries(items: dict[str, dict], raw_items, masteries) -> int:
    """Sets `item["mastery"] = "<Name>"` on every weapon in `items` whose
    normalized name equals that of an XPHB base item with a known mastery
    (the SRD "Crossbow, light" matches "Light Crossbow"). Weapons XPHB gives no
    mastery (Net, Double-Bladed Scimitar, Hoopak, Yklwa) are left alone.
    Returns the number of items changed."""
    by_name: dict[str, str] = {}
    for raw in raw_items or []:
        if raw.get("source") != "XPHB" or _type_code(raw) not in _WEAPON_TYPES:
            continue
        first = next((str(m).split("|")[0] for m in raw.get("mastery") or []), None)
        if first in masteries:
            by_name.setdefault(_normalize_weapon_name(raw.get("name")), first)
    changed = 0
    for item in items.values():
        if item.get("equipment_category", {}).get("index") != "weapon":
            continue
        mastery = by_name.get(_normalize_weapon_name(item.get("name")))
        if mastery:
            item["mastery"] = mastery
            changed += 1
    return changed
