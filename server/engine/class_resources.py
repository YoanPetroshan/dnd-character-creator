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

from dataclasses import dataclass, field
from typing import Callable

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
        if self.ruleset != "2024":
            return None
        values = ((getattr(self.catalog, "subclass_2024_tables", None) or {}).get(sub_id) or {}).get(column)
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


def _barbarian(ctx: Ctx, rc: dict) -> list[dict]:
    level = rc["level"]
    cs = _class_specific(rc)
    uses = ctx.table("barbarian", "rages", level)
    bonus = ctx.table("barbarian", "rage-damage", level)
    if uses is None:
        uses = cs.get("rage_count")
    if bonus is None:
        bonus = cs.get("rage_damage_bonus")
    if uses is None:
        return []
    unlimited = uses >= UNLIMITED_ROW_VALUE
    return [_resource(
        rc, "Rage", uses=uses, unlimited=unlimited, recharge="long",
        details={"damageBonus": bonus, "resistances": ["bludgeoning", "piercing", "slashing"]},
    )]


def _rogue(ctx: Ctx, rc: dict) -> list[dict]:
    dice = ctx.table("rogue", "sneak-attack", rc["level"])
    if dice is None:
        sa = _class_specific(rc).get("sneak_attack") or {}
        dice = f"{sa['dice_count']}d{sa['dice_value']}" if sa.get("dice_count") else None
    if dice is None:
        return []
    return [_resource(rc, "Sneak Attack", dice=dice)]


_BUILDERS: dict[str, Callable[[Ctx, dict], list[dict]]] = {
    "barbarian": _barbarian,
    "rogue": _rogue,
}
_SUBCLASS_BUILDERS: dict[str, Callable[[Ctx, dict], list[dict]]] = {}


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
    return out
