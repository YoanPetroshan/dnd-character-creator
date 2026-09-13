"""CR (challenge rating) key normalization, shared across the rules modules.

5etools JSON represents CR three ways: a plain string ("1/8"), an occasional
bare number, and — critically — a dict for lair/variant monsters
({"cr": "14", "xpLair": 13000}, confirmed on 7% of the bestiary, essentially
every Adult/Ancient dragon). `engine.encounters.CR_XP` and the DMG's
"Monster Statistics by Challenge Rating" table (msbcr.json, looked up via
`engine.rules.monster_stats`) both key off the same string form ("0", "1/8",
..., "30"), so this one normalizer backs both lookups. This project has a
documented history of CR-as-dict/CR-as-fraction bugs from treating CR
normalization as a one-off — a second, possibly-inconsistent implementation
is exactly how that happens again.
"""
from __future__ import annotations


def cr_key(cr) -> str:
    if isinstance(cr, dict):
        cr = cr.get("cr", "")
    return str(cr).strip()
