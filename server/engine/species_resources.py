"""W5a (F2): ``derived.speciesResources``, species traits with a use count, a rest rule or numbers.

Pure: driven by ``reference_data.SPECIES_RESOURCES`` (keyed by catalog trait id, quote-pinned by the tests) and the
species the character holds. The entry shape is the class / feat resource shape minus ``classId``, plus ``traitId``
and ``speciesId``, with ``source = {kind: "species", id: <species id>, label: <species name>}``. Breath Weapon-like
traits are resources with ``dc`` / ``dice`` and ``details`` (decision D-2), never attack rows."""
from __future__ import annotations

from catalog import reference_data


def _slug(text: str) -> str:
    return "-".join("".join(ch if ch.isalnum() else " " for ch in text.lower()).split())


def _dice_for(table: tuple, level: int) -> str:
    dice = table[0][1]
    for first, value in table:
        if level >= first:
            dice = value
    return dice


def resources(catalog, race: dict | None, race_id: str | None, subrace: dict | None, variant: dict | None,
              total_level: int, pb: int, modifiers: dict, walk_speed: int | None) -> list[dict]:
    """One entry per table trait the species (race + subrace trait refs) holds at the character's total level."""
    if not race or not race_id:
        return []
    refs = list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or [])
    out: list[dict] = []
    seen: set[str] = set()
    for ref in refs:
        tid = ref.get("index")
        spec = reference_data.SPECIES_RESOURCES.get(tid)
        if not spec or tid in seen or spec["race"] != race_id or tid not in catalog.traits:
            continue
        seen.add(tid)
        if total_level < spec.get("level", 1):
            continue
        con_mod = modifiers.get("CON", 0)
        values = {"pb": pb, "two_pb": 2 * pb, "level": total_level, "con_mod": con_mod,
                  "speed_part": f" ({walk_speed} feet)" if walk_speed else ""}
        details: dict = {}
        entry = {"id": f"species:{race_id}:{_slug(spec['name'])}", "speciesId": race_id, "traitId": tid,
                 "source": {"kind": "species", "id": race_id, "label": race.get("name") or race_id},
                 "name": spec["name"], "uses": pb if spec["uses"] == "pb" else spec["uses"],
                 "recharge": spec["recharge"]}
        if spec.get("dc"):
            entry["dc"] = 8 + modifiers.get(spec["dc"], 0) + pb
            details["save"] = spec["save"]
        if spec.get("dice_by_level"):
            entry["dice"] = values["dice"] = _dice_for(spec["dice_by_level"], total_level)
        if spec.get("die"):
            entry["die"] = spec["die"]
        if spec.get("shape"):
            details["shape"] = values["shape"] = spec["shape"]
        if spec.get("damage_type") == "ancestry":
            picked = ((variant or {}).get("resist") or [None])[0]
            details["damageType"] = picked
            values["damage_type"] = picked.capitalize() if picked else "the Draconic Ancestry's type (choose the ancestry)"
        if spec.get("heal"):
            details["heal"] = spec["heal"].format(**values)
        if spec.get("giant_ancestry"):
            boon = reference_data.GIANT_ANCESTRY_2024.get((variant or {}).get("id"))
            values["ancestry"] = (f"{boon['name']}: {boon['note'].format(**values)}" if boon
                                  else "choose a Giant Ancestry")
        details["note"] = spec["note"].format(**values)
        entry["details"] = details
        out.append(entry)
    return out
