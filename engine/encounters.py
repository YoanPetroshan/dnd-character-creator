"""Encounter scaling — DMG 2024 XP budgets, computed rather than estimated.

Run:
    python3 -m engine.encounters budget --level 4 --players 2
    python3 -m engine.encounters encounter --level 4 --players 2 \
        --monsters "Goblin Boss,Goblin Warrior,Goblin Warrior"
"""
from __future__ import annotations

import argparse
import sys

from engine.rules.cr import cr_key
from engine.rules.lookup import fetch_record, find

# DMG 2024, Chapter 4 — "XP Budget per Character", transcribed in full from
# the book (levels 1–20). Each number is a CEILING: step 3 of the procedure is
# "Spend as much of your XP budget as you can without going over."
XP_BUDGET: dict[int, dict[str, int]] = {
    1: {"low": 50, "moderate": 75, "high": 100},
    2: {"low": 100, "moderate": 150, "high": 200},
    3: {"low": 150, "moderate": 225, "high": 400},
    4: {"low": 250, "moderate": 375, "high": 500},
    5: {"low": 500, "moderate": 750, "high": 1100},
    6: {"low": 600, "moderate": 1000, "high": 1400},
    7: {"low": 750, "moderate": 1300, "high": 1700},
    8: {"low": 1000, "moderate": 1700, "high": 2100},
    9: {"low": 1300, "moderate": 2000, "high": 2600},
    10: {"low": 1600, "moderate": 2300, "high": 3100},
    11: {"low": 1900, "moderate": 2900, "high": 4100},
    12: {"low": 2200, "moderate": 3700, "high": 4700},
    13: {"low": 2600, "moderate": 4200, "high": 5400},
    14: {"low": 2900, "moderate": 4900, "high": 6200},
    15: {"low": 3300, "moderate": 5400, "high": 7800},
    16: {"low": 3800, "moderate": 6100, "high": 9800},
    17: {"low": 4500, "moderate": 7200, "high": 11700},
    18: {"low": 5000, "moderate": 8700, "high": 14200},
    19: {"low": 5500, "moderate": 10700, "high": 17200},
    20: {"low": 6400, "moderate": 13200, "high": 22000},
}
MIN_LEVEL, MAX_LEVEL = min(XP_BUDGET), max(XP_BUDGET)

CR_XP: dict[str, int] = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100, "5": 1800,
    "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900,
    "11": 7200, "12": 8400, "13": 10000, "14": 11500, "15": 13000,
    "16": 15000, "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000,
    "26": 90000, "27": 105000, "28": 120000, "29": 135000, "30": 155000,
}


def party_budget(level: int, players: int) -> dict[str, int]:
    if level not in XP_BUDGET:
        raise ValueError(
            f"level {level} is outside the supported range {MIN_LEVEL}–{MAX_LEVEL}"
        )
    if players < 1:
        raise ValueError("players must be at least 1")
    per = XP_BUDGET[level]
    return {band: value * players for band, value in per.items()}


def monster_xp(name: str) -> int | None:
    entry = find(name, kind="monster")
    if entry is None:
        return None
    rec = fetch_record(entry)
    if not rec:
        return None
    return CR_XP.get(cr_key(rec.get("cr")))


def encounter_xp(names: list[str]) -> tuple[int, list[str]]:
    total = 0
    missing: list[str] = []
    for name in names:
        xp = monster_xp(name.strip())
        if xp is None:
            missing.append(name.strip())
        else:
            total += xp
    return total, missing


def classify(total_xp: int, budget: dict[str, int]) -> str:
    """Which difficulty band an encounter's XP total actually falls in.

    The DMG's budgets are CEILINGS — "Spend as much of your XP budget as you
    can without going over" — so a total belongs to the first band whose
    budget it does not exceed. Treating them as floors for the next band up
    (the previous behaviour) under-reported danger by a whole band: at level 4
    with 2 players (low 500 / moderate 750 / high 1000), 999 XP was called
    "Moderate" even though it blows through the Moderate ceiling, and only the
    exact value 1000 was ever called "High".

    There is deliberately no "under Low" band: the DMG defines three
    difficulties and no floor beneath Low, so any total within the Low ceiling
    is a Low-difficulty encounter.
    """
    if total_xp <= budget["low"]:
        return "Low"
    if total_xp <= budget["moderate"]:
        return "Moderate"
    if total_xp <= budget["high"]:
        return "High"
    return "над High"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="engine.encounters")
    ap.add_argument("command", choices=["budget", "encounter"])
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--players", type=int, required=True)
    ap.add_argument("--monsters", default="", help="comma-separated names")
    args = ap.parse_args(argv)

    try:
        budget = party_budget(args.level, args.players)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"XP бюджет — ниво {args.level}, {args.players} героя:")
    print(f"  Low {budget['low']} | Moderate {budget['moderate']} | High {budget['high']}")

    if args.command == "budget":
        return 0

    names = [n for n in args.monsters.split(",") if n.strip()]
    if not names:
        print("encounter requires --monsters", file=sys.stderr)
        return 2

    total, missing = encounter_xp(names)
    print(f"\nСреща: {', '.join(names)}")
    print(f"  Общо XP: {total} → {classify(total, budget)}")
    if missing:
        print(f"  НЕНАМЕРЕНИ (не влизат в сумата): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
