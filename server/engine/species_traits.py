"""VF2: the `reference_data` rows (keyed by trait id) of the traits a species holds -- the race's own and the subrace's -- minus
the race traits a subrace replaces (`overwrites_traits`, F1.2). Pure; used by the Armor Class (VF2.1) and the initiative (VF2.2)
readers."""
from __future__ import annotations


def rows(race: dict | None, subrace: dict | None, table: dict) -> list[dict]:
    if not race:
        return []
    replaced = set((subrace or {}).get("overwrites_traits") or [])
    out, seen = [], set()
    for ref in list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or []):
        spec = table.get(ref.get("index"))
        if spec and ref["index"] not in seen and ref.get("name") not in replaced:
            seen.add(ref["index"])
            out.append(spec)
    return out
