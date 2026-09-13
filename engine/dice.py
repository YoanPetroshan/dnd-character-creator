"""Dice_Rolling_Protocol_v3.0 encoded as code.

Two invariants:
  1. Players roll for their own characters — the DM never rolls a PC d20.
     PC rolls are requested through the phone widget (`request_pc_roll`).
  2. Every DM roll uses a real RNG. No averages, no "choosing" a number.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from dataclasses import dataclass, field

from engine import display, state
from engine.log import log_event

_RNG = random.SystemRandom()
# The display writes the resolved roll as
#   f"{character} rolls {spec}{mod_str}: {breakdown} = {total}{suffix}"
# (skills/dnd/display/dnd-display-app.py, /player-input/dice), where suffix is
# an optional " — {label}". `breakdown` never contains "=", so the FIRST "= N"
# in the line is always the total, and any label text after it is ignored.
_TOTAL = re.compile(r"=\s*(-?\d+)")
_SPEC = re.compile(r"^(\d*)d(\d+)$")


def _d(sides: int) -> int:
    """Single die roll. Patched in tests; the only source of randomness."""
    return _RNG.randint(1, sides)


@dataclass
class RollResult:
    d20: int
    total: int
    crit: bool = False
    fumble: bool = False
    rolls: list[int] = field(default_factory=list)
    detail: str = ""


def roll_dice(count: int, sides: int) -> list[int]:
    return [_d(sides) for _ in range(max(0, count))]


def roll_d20(modifier: int = 0, advantage: str = "normal") -> RollResult:
    if advantage == "advantage":
        a, b = _d(20), _d(20)
        picked, rolls = max(a, b), [a, b]
    elif advantage == "disadvantage":
        a, b = _d(20), _d(20)
        picked, rolls = min(a, b), [a, b]
    else:
        picked = _d(20)
        rolls = [picked]
    total = picked + modifier
    return RollResult(
        d20=picked,
        total=total,
        crit=picked == 20,
        fumble=picked == 1,
        rolls=rolls,
        detail=f"d20({'/'.join(map(str, rolls))}) + {modifier} = {total}",
    )


def resolve_attack(total: int, target_ac: int, nat20: bool = False, nat1: bool = False) -> str:
    """Natural 20/1 apply ONLY to attack rolls. Equal to AC hits."""
    if nat20:
        return "КРИТИЧЕН УДАР"
    if nat1:
        return "КРИТИЧЕН ПРОПУСК"
    return "УДАР" if total >= target_ac else "ПРОПУСК"


def enemy_attack(
    attacker: str, atk_mod: int, target_ac: int, num_dice: int, die: int, dmg_mod: int
) -> dict:
    r = roll_d20(modifier=atk_mod)
    status = resolve_attack(r.total, target_ac, nat20=r.crit, nat1=r.fumble)

    if status == "КРИТИЧЕН УДАР":
        damage_dice = roll_dice(num_dice * 2, die)  # double the DICE, not the modifier
    elif status == "УДАР":
        damage_dice = roll_dice(num_dice, die)
    else:
        damage_dice = []

    damage = sum(damage_dice) + dmg_mod if damage_dice else 0
    out = {
        "attacker": attacker,
        "d20": r.d20,
        "total": r.total,
        "target_ac": target_ac,
        "status": status,
        "damage_dice": damage_dice,
        "damage": damage,
        "line": (
            f"{attacker}: d20({r.d20}) + {atk_mod} = {r.total} vs AC {target_ac} — {status}"
        ),
    }
    log_event("dm_roll", kind="attack", **{k: out[k] for k in ("attacker", "d20", "total", "status", "damage")})
    return out


from engine.rules_2024 import concentration_dc  # noqa: F401  (re-exported)


def normalize_spec(spec: str) -> str:
    """`d20` → `1d20`, `1D20` → `1d20`.

    The display only accepts `NdM` (lowercased) and records exactly that
    string in the text log, so the spec we send must be the spec we search
    the log for.
    """
    text = (spec or "").strip().lower().replace(" ", "")
    m = _SPEC.match(text)
    if not m:
        return text
    count = m.group(1) or "1"
    return f"{int(count)}d{int(m.group(2))}"


def resolved_pc_roll(character: str, spec: str) -> int | None:
    """Read the player's resolved total back out of the display's text log.

    `send.py --dice-request --wait` prints only the hex request_id on stdout —
    every status line goes to stderr, and the resolved value never round-trips
    through the request endpoint at all: the phone POSTs to
    /player-input/dice, which broadcasts and appends to text_log.json. So the
    total has to be read from that log, exactly the way the production
    wrapper skills/dnd/scripts/dice_player.py::_find_resolved_roll does it —
    newest entry backward, `dice` flag set, text starting with
    "<character> rolls <spec>". Entries carry no timestamp, so "newest match
    wins" is the only available ordering, same as upstream.
    """
    path = state.runtime_dir() / "text_log.json"
    try:
        log = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(log, list):
        return None

    needle = f"{character} rolls {spec}"
    for entry in reversed(log):
        if not isinstance(entry, dict) or not entry.get("dice"):
            continue
        text = entry.get("text", "")
        if not isinstance(text, str) or not text.startswith(needle):
            continue
        m = _TOTAL.search(text)
        return int(m.group(1)) if m else None
    return None


def request_pc_roll(
    character: str,
    spec: str = "1d20",
    modifier: int = 0,
    label: str = "",
    dc: int | None = None,
    advantage: str = "normal",
) -> int | None:
    """Ask the player for their own roll via the phone widget. Returns the TOTAL."""
    spec = normalize_spec(spec)
    request_id = display.dice_request(
        character=character, spec=spec, modifier=modifier,
        label=label, dc=dc, advantage=advantage, wait=True,
    )
    if request_id is None:
        log_event("pc_roll_timeout", character=character, label=label)
        return None
    value = resolved_pc_roll(character, spec)
    if value is None:
        # The wait returned, but no matching resolved entry landed in the log.
        log_event("pc_roll_unparsed", character=character, spec=spec,
                  request_id=str(request_id)[:32])
        return None
    log_event("pc_roll", character=character, label=label, total=value)
    return value


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="engine.dice",
        description="Request a player character's own d20 through the display.",
    )
    ap.add_argument("command", choices=["pc"], help="pc: ask a player to roll")
    ap.add_argument("--character", required=True, help="exact character name")
    ap.add_argument("--spec", default="1d20", help="dice spec, e.g. 1d20 or 2d6")
    ap.add_argument("--modifier", type=int, default=0)
    ap.add_argument("--label", default="", help='e.g. "Stealth check"')
    ap.add_argument("--dc", type=int, default=None)
    ap.add_argument("--advantage", default="normal",
                    choices=["normal", "advantage", "disadvantage"])
    args = ap.parse_args(argv)

    total = request_pc_roll(
        character=args.character, spec=args.spec, modifier=args.modifier,
        label=args.label, dc=args.dc, advantage=args.advantage,
    )
    if total is None:
        print("TIMEOUT: няма отговор от играча. Попитай на глас за числото.")
        return 1
    print(total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
