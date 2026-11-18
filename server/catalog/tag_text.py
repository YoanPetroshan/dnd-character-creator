"""5etools inline ``{@tag a|b|c}`` markup -> plain text: the one shared implementation (spells, feats, class and
species text, the sheet / PDF / Markdown exports)."""
from __future__ import annotations

import re

TAG_RE = re.compile(r"\{@(\w+)(?: ([^{}]*))?\}")
ATTACK_WORDS = {
    "mw": "Melee Weapon Attack:", "rw": "Ranged Weapon Attack:", "ms": "Melee Spell Attack:",
    "rs": "Ranged Spell Attack:", "m": "Melee Attack:", "r": "Ranged Attack:",
    "mw,rw": "Melee or Ranged Weapon Attack:", "ms,rs": "Melee or Ranged Spell Attack:",
}
# Tags whose later "|" segments are not display text.
FIRST_SEGMENT_TAGS = {"filter", "dice", "damage", "d20", "autodice", "note", "footnote", "book", "i", "b", "u", "s"}


def tag_repl(m: re.Match) -> str:
    tag, body = m.group(1), m.group(2) or ""
    parts = body.split("|")
    first = parts[0]
    if tag == "dc":
        return f"DC {first}"
    if tag == "hit":
        return first if first[:1] in "+-" else f"+{first}"
    if tag == "h":
        return "Hit: "
    if tag == "atk":
        return ATTACK_WORDS.get(first, first)
    if tag == "recharge":
        return f"(Recharge {first or 6})"
    if tag == "chance":
        return f"{first} percent"
    if tag == "quickref":
        return parts[3] if len(parts) > 3 and parts[3] else first
    if tag in ("scaledamage", "scaledice"):
        # {@scaledamage base|levels|per-level|display}: the text shows the per-level amount
        if len(parts) > 3 and parts[3]:
            return parts[3]
        return parts[2] if len(parts) >= 3 and parts[2] else first
    if tag in FIRST_SEGMENT_TAGS:
        return first
    return parts[2] if len(parts) >= 3 and parts[2] else first


def strip_tags(text: str) -> str:
    """Flattens 5etools `{@tag a|b|c}` markup (innermost first) to plain text."""
    previous = None
    while previous != text:
        previous = text
        text = TAG_RE.sub(tag_repl, text)
    return text
