"""VF2: the `reference_data` rows (keyed by trait id) of the traits a species holds -- the race's own and the subrace's -- minus
the race traits a subrace replaces (`overwrites_traits`, F1.2). Pure; used by the Armor Class (VF2.1) and the initiative (VF2.2)
readers."""
from __future__ import annotations

import re


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


_ONE_SIZE_LARGER = re.compile(r"\bcount as one size larger when determining your carrying (?:capacity|weight)\b", re.I)


def counts_as_one_size_larger(race: dict | None, subrace: dict | None, traits: dict) -> bool:
    """VF2.3: does a trait the species holds say "you count as one size larger when determining your carrying capacity" (Powerful
    Build, Equine Build, Hippo Build, Little Giant)? Read from the catalog trait text, not from a name list. The MPMM Goliath
    text says "carrying weight" for "carrying capacity" (a typo of the record, same sentence). Several such traits do not stack."""
    if not race:
        return False
    replaced = set((subrace or {}).get("overwrites_traits") or [])
    for ref in list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or []):
        if ref.get("name") in replaced:
            continue
        text = " ".join(str(line) for line in ((traits.get(ref.get("index")) or {}).get("desc") or []))
        if _ONE_SIZE_LARGER.search(text):
            return True
    return False
