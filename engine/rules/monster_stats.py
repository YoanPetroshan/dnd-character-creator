"""Look up the DMG 2024 "Monster Statistics by Challenge Rating" table.

Gives the realistic target numbers for a CR — AC, HP range, attack bonus,
DPR range, save DC — so the DM can sanity-check or improvise a stat block
instead of inventing one from memory (DMG 2024, Chapter 2, "Creating a
Monster Stat Block").

Run:
    python3 -m engine.rules.monster_stats --cr 9
    python3 -m engine.rules.monster_stats --cr 1/8
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.config import json_dir
from engine.rules.cr import cr_key


def load_table(directory: Path | None = None) -> list[dict]:
    directory = Path(directory) if directory is not None else json_dir()
    path = directory / "msbcr.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("cr", [])


def find_row(cr, directory: Path | None = None) -> dict | None:
    """Match a CR (string, number, or 5etools CR-as-dict) against the table.

    Reuses cr_key — the same normalizer engine.encounters uses for CR_XP
    lookups — rather than a second parser, so a lair/variant CR dict like
    {"cr": "14", "xpLair": 13000} resolves identically in both places.
    """
    key = cr_key(cr)
    for row in load_table(directory):
        if cr_key(row.get("_cr")) == key:
            return row
    return None


def format_row(row: dict) -> str:
    return "\n".join([
        f"# Monster Stats by CR — CR {row.get('_cr', '?')}  [DMG 2024]",
        f"Proficiency Bonus: +{row.get('pb', '?')}",
        f"AC: {row.get('ac', '?')}",
        f"HP: {row.get('hpMin', '?')}–{row.get('hpMax', '?')}",
        f"Attack Bonus: +{row.get('attackBonus', '?')}",
        f"DPR: {row.get('dprMin', '?')}–{row.get('dprMax', '?')}",
        f"Save DC: {row.get('saveDc', '?')}",
    ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="engine.rules.monster_stats")
    ap.add_argument("--cr", required=True,
                     help='CR, e.g. "9", "1/8", "1/4", "1/2", "0"')
    args = ap.parse_args(argv)

    row = find_row(args.cr)
    if row is None:
        print(f"Няма запис за CR „{args.cr}“ в msbcr.json. "
              f"Провери стойността (0–30) или импровизирай по DMG 2024, "
              f"Chapter 2 „Creating a Monster Stat Block“.")
        return 1

    print(format_row(row))
    print("\n[Справка: DMG 2024 — Monster Statistics by Challenge Rating]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
