"""G6: the structured use limit of an innate spell, parsed ONLY from its `uses` text.

`sheet.innateSpells[].uses` is free text ("1/day", "at-will", "3/long rest", "always prepared", "1 Focus Point" ...). Where the
text states a count and a rest, the entry also gets two additive fields in the class-resource vocabulary:

  usesMax   int, the number of casts
  recharge  "long" | "short" | "short-or-long"

  "N/day"                  N, "long"   (a day is a long rest in these sources)
  "N/long rest"            N, "long"
  "N/short rest"           N, "short"
  "N/short or long rest"   N, "short-or-long"

Everything else gets neither field: "at-will", "prepared", "always prepared", "ritual", "ritual only", "1 Focus Point" (a
resource cost, no rest) and any text that does not match. A count that depends on the proficiency bonus or an ability
modifier is already a number when it reaches the sheet (RP5 Greater Mark of Healing "{pb}/long rest" and the Glamour Bard
"{cha_min1}/long rest" are formatted from the character before the entry is built), so the parse sees "3/long rest". Pure."""
from __future__ import annotations

import re

_USES = re.compile(r"^(\d+)\s*/\s*(day|long rest|short rest|short or long rest)$", re.IGNORECASE)
_RECHARGE = {"day": "long", "long rest": "long", "short rest": "short", "short or long rest": "short-or-long"}


def parse_uses(text) -> tuple[int, str] | None:
    """(usesMax, recharge) for a use-limited text, else None."""
    match = _USES.match(text.strip()) if isinstance(text, str) else None
    if not match or int(match.group(1)) < 1:
        return None
    return int(match.group(1)), _RECHARGE[match.group(2).lower()]


def with_limit(entry: dict) -> dict:
    """The sheet entry with `usesMax` and `recharge` added when its `uses` text states a limit (a new dict; absent otherwise)."""
    parsed = parse_uses(entry.get("uses"))
    return entry if parsed is None else {**entry, "usesMax": parsed[0], "recharge": parsed[1]}
