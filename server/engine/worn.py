"""G2: the worn / wielded equipment model (decision D3 option c). Pure, no I/O.

Draft shape (both OPTIONAL; when a key is absent the engine behaves exactly as before G2:
every granted, chosen and `equipped` added item counts, best armor and shield auto-detected):

    equipment.worn    = {"armor": <item id | null>, "shield": <bool | null>}
    equipment.wielded = {"main": <item id | null>, "off": <item id | null>}

`worn`: a missing `armor` key means auto; `null` means no body armor is worn (so Unarmored
Defense, Armor of Shadows, Draconic Resilience, Unarmored Movement compete or apply); an item id
means only that suit counts. `shield`: missing or `null` = auto, `true` = the shield from the
inventory is worn, `false` = none. Chosen items need only be in the inventory (granted, chosen or
added), the `equipped` flag of added items is not needed for them.
`wielded`: the dict being present means both hands are specified (a missing key = empty hand).
Wielded weapons always get an attack row.

Ids that are unknown to the catalog give a `*-unknown-item` warning, ids that are not in the
inventory a `*-not-in-inventory` warning plus a `pruned` entry; both are ignored (worn: back to
auto, wielded: empty hand). Other warnings: `worn-armor-not-body-armor`, `worn-shield-missing`,
`wielded-{main,off}-not-holdable` (body armor in a hand), `wielded-main-shield`,
`wielded-two-handed-conflict`, `wielded-two-handed-shield`, `wielded-same-item-twice`,
`wielded-shield-not-worn`.

Dueling (RAW 2014 "wielding a melee weapon in one hand and no other weapons"; XPHB "holding a
Melee weapon in one hand and no other weapons"): the engine's rule is main hand = the rated
weapon, off hand empty or anything that is not a weapon (a shield is allowed).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from i18n.messages import msg


def _kind_msg(kind: str):
    """"worn" / "wielded" as a nested message (renders as the same English word)."""
    return msg("slot-kind-worn") if kind == "worn" else msg("slot-kind-wielded")


def _slot_msg(slot: str):
    """"armor" / "main" / "off" as a nested message."""
    if slot == "armor":
        return msg("slot-armor")
    return msg("slot-main") if slot == "main" else msg("slot-off")


def _cat(item: dict) -> str | None:
    return (item.get("equipment_category") or {}).get("index")


def is_shield(item: dict) -> bool:
    return item.get("armor_category") == "Shield"


def is_body_armor(item: dict) -> bool:
    return _cat(item) == "armor" and not is_shield(item)


def is_weapon(item: dict) -> bool:
    return _cat(item) == "weapon"


def is_two_handed(item: dict) -> bool:
    return any(p.get("index") == "two-handed" for p in item.get("properties", []))


@dataclass
class Gear:
    items: list[dict]
    worn: dict | None = None
    wielded: dict | None = None
    hands: dict | None = None  # for attacks.weapon_attack: {"main", "off", "dueling_ok"}
    slots: dict = field(default_factory=dict)
    warnings: list[dict] = field(default_factory=list)
    pruned: list[dict] = field(default_factory=list)


def slot_options(inventory: dict[str, dict]) -> dict:
    """What the Equipment page can offer in its selectors, from the resolved inventory."""
    items = [e["item"] for e in inventory.values()]
    ref = lambda i: {"itemId": i["index"], "name": i["name"]}  # noqa: E731
    return {
        "armor": [ref(i) for i in items if is_body_armor(i)],
        "shield": [ref(i) for i in items if is_shield(i)],
        "hands": [
            {**ref(i), "kind": "shield" if is_shield(i) else "weapon", "twoHanded": is_two_handed(i)}
            for i in items if is_weapon(i) or is_shield(i)
        ],
    }


def apply(equipped_items: list[dict], equipment: dict, inventory: dict[str, dict], lookup: dict) -> Gear:
    """`inventory`: item id -> {"item": catalog item, "qty": int} over granted + chosen + added.
    Returns the effective list of equipped items plus the resolved worn/wielded state."""
    gear = Gear(items=equipped_items, slots=slot_options(inventory))
    first_body = next((i for i in equipped_items if is_body_armor(i)), None)
    # what the engine counts now (auto-detected), to seed the manual selectors
    gear.slots["current"] = {"armor": first_body and first_body["index"], "shield": any(is_shield(i) for i in equipped_items)}
    worn_raw = equipment.get("worn") if isinstance(equipment.get("worn"), dict) else None
    wielded_raw = equipment.get("wielded") if isinstance(equipment.get("wielded"), dict) else None
    if worn_raw is None and wielded_raw is None:
        return gear
    warnings, pruned = gear.warnings, gear.pruned

    def lookup_slot(item_id, kind: str, slot: str) -> dict | None:
        if item_id is None:
            return None
        if item_id not in lookup:
            warnings.append({"id": f"{kind}-{slot}-unknown-item", "message": msg("slot-unknown-item", kind=_kind_msg(kind), slot=_slot_msg(slot), item=item_id)})
            return None
        if item_id not in inventory:
            name = lookup[item_id].get("name", item_id)
            warnings.append({"id": f"{kind}-{slot}-not-in-inventory", "message": msg("slot-not-in-inventory", name=name, kind=_kind_msg(kind), slot=_slot_msg(slot))})
            pruned.append({"choiceId": f"equipment:{kind}:{slot}", "reason": f"{name} is no longer in the inventory and was removed from the {kind} {slot} slot."})
            return None
        return lookup[item_id]

    # hands first: a shield in the off hand also counts as a worn shield unless worn.shield is false
    main = off = None
    if wielded_raw is not None:
        main = lookup_slot(wielded_raw.get("main"), "wielded", "main")
        off = lookup_slot(wielded_raw.get("off"), "wielded", "off")
        for slot, item in (("main", main), ("off", off)):
            if item is not None and is_body_armor(item):
                warnings.append({"id": f"wielded-{slot}-not-holdable", "message": msg("wielded-not-holdable", name=item["name"])})
                if slot == "main":
                    main = None
                else:
                    off = None
        if main is not None and is_shield(main):
            warnings.append({"id": "wielded-main-shield", "message": msg("wielded-main-shield", name=main["name"])})
            main = None
        if main is not None and off is not None and main["index"] == off["index"] and inventory[main["index"]]["qty"] < 2:
            warnings.append({"id": "wielded-same-item-twice", "message": msg("wielded-same-item-twice", name=main["name"])})
        two = [i for i, other in ((main, off), (off, main)) if i is not None and other is not None and is_weapon(i) and is_two_handed(i)]
        if two:
            warnings.append({"id": "wielded-two-handed-conflict", "message": msg("wielded-two-handed-conflict", name=two[0]["name"])})

    worn = worn_raw or {}
    non_armor = [i for i in equipped_items if _cat(i) != "armor"]
    bodies = [i for i in equipped_items if is_body_armor(i)]
    shields = [i for i in equipped_items if is_shield(i)]

    if "armor" in worn:
        if worn["armor"] is None:
            bodies = []
        else:
            chosen = lookup_slot(worn["armor"], "worn", "armor")
            if chosen is not None and not is_body_armor(chosen):
                warnings.append({"id": "worn-armor-not-body-armor", "message": msg("worn-armor-not-body-armor", name=chosen["name"])})
                chosen = None
            if chosen is not None:
                bodies = [chosen]  # else: a dropped id means auto
    shield_flag = worn.get("shield")
    if shield_flag is True:
        first = next((e["item"] for e in inventory.values() if is_shield(e["item"])), None)
        if first is None:
            warnings.append({"id": "worn-shield-missing", "message": msg("worn-shield-missing")})
        shields = [first] if first else []
    elif shield_flag is False:
        shields = []
        if off is not None and is_shield(off):
            warnings.append({"id": "wielded-shield-not-worn", "message": msg("wielded-shield-not-worn", name=off["name"])})
    elif off is not None and is_shield(off) and not any(s["index"] == off["index"] for s in shields):
        shields = shields + [off]
    if worn_raw is not None and shield_flag is True and any(i is not None and is_weapon(i) and is_two_handed(i) for i in (main, off)):
        warnings.append({"id": "wielded-two-handed-shield", "message": msg("wielded-two-handed-shield")})

    items = non_armor + bodies + shields
    held_ids = set()
    for held in (main, off):
        if held is not None and not is_shield(held):
            held_ids.add(held["index"])
            if all(i["index"] != held["index"] for i in items):
                items.append(held)
    gear.items = items

    if worn_raw is not None:
        gear.worn = {"armor": bodies[0]["index"] if bodies else None, "shield": bool(shields), "manual": True}
    if wielded_raw is not None:
        gear.wielded = {"main": main and main["index"], "off": off and off["index"], "manual": True}
        gear.hands = {
            "main": main and main["index"], "off": off and off["index"],
            "dueling_ok": off is None or not is_weapon(off),
        }
    return gear
