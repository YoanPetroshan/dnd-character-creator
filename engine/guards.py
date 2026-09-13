"""Post-turn correctness checks. These are what make the loop trustworthy."""
from __future__ import annotations

import re

from engine import display
from engine.log import log_event

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def cyrillic_ratio(text: str) -> float:
    letters = _LETTER.findall(text)
    if not letters:
        return 0.0
    cyr = sum(1 for ch in letters if _CYRILLIC.match(ch))
    return cyr / len(letters)


def check_language(text: str, expect: str = "bg", threshold: float = 0.35) -> bool:
    """Bulgarian narration keeps English proper nouns, so the bar is a ratio,
    not a hard requirement that every word be Cyrillic."""
    if expect != "bg":
        return True
    if len(text.strip()) < 20:
        return True
    ok = cyrillic_ratio(text) >= threshold
    if not ok:
        log_event("guard_language_failed", ratio=round(cyrillic_ratio(text), 3))
    return ok


# A roll announcement's actor sits at the start of the announcement, directly
# adjacent to the roll marker — see engine/dice.py's enemy_attack() `line`
# field (f"{attacker}: d20({r.d20}) ...") and skills/dnd/SKILL-commands.md's
# `[Name]: d20(N) + DEX = total`. "Start" means: the very start of the text,
# right after a newline, right after sentence-ending punctuation, or right
# after the 🎲 marker. A name that merely appears somewhere nearby (e.g. as
# the target of an enemy's attack, or mentioned in an earlier sentence) is
# not the actor and must not be flagged.
_ANNOUNCEMENT_START = r"(?:\A|\n|(?<=[.!?—])|(?<=🎲))"


def find_pc_autorolls(text: str, pc_names: list[str], requested: set[str]) -> list[str]:
    """Detect a PC d20 the engine never asked the phone for.

    Rule 1 of the dice protocol: the DM never rolls for a player character.
    Only flags a name when it is the ACTOR of the roll — i.e. the name
    announcing the roll at the start of the announcement — not merely a name
    mentioned somewhere before the `d20(` marker (see _ANNOUNCEMENT_START).
    """
    offenders = []
    # The requested set is assembled from `pc_roll` log events, whose
    # character string comes from whatever the agent typed on the command
    # line. Compare case-insensitively so "sylwen nightbrook" still counts as
    # the legitimately requested "Sylwen Nightbrook".
    requested_folded = {r.casefold() for r in requested}
    for name in pc_names:
        if name.casefold() in requested_folded:
            continue
        pattern = re.compile(
            rf"{_ANNOUNCEMENT_START}\s*{re.escape(name)}\b\s*:\s*d20\s*\(",
            re.IGNORECASE,
        )
        if pattern.search(text):
            offenders.append(name)
    if offenders:
        log_event("guard_pc_autoroll", characters=offenders)
    return offenders


def ensure_display_pushed(before, after, fallback_text: str) -> bool:
    """If the model forgot send.py, push its final text ourselves.

    `before`/`after` are opaque markers of the display log's state, taken from
    state.text_log_fingerprint() on either side of the turn. They are compared
    for INEQUALITY, never ordered: the display keeps only the last 60 entries,
    so a growth check silently stops detecting pushes once the log saturates,
    and every later turn would then double-push the narration.

    Returns True when the fallback fired.
    """
    if after != before:
        return False
    text = (fallback_text or "").strip()
    if not text:
        return False
    log_event("guard_display_fallback", chars=len(text))
    display.send_narration(text)
    return True
