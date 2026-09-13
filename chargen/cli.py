"""`python -m chargen <subcommand> ...` — the whole engine, usable with no
server and no browser.

This is the plan's own "prove it before wiring it in" checkpoint: every
subcommand here is a thin, formatting-only wrapper around `chargen.catalog`
(Task 5) and `chargen.build` (Task 6) — this module makes no rules
decisions of its own. The one exception is `build`'s skill auto-pick, which
is a CLI convenience (deterministic, not a rule) documented on `cmd_build`.

The committed SRD data has exactly one background — `acolyte` — so every
example in this file's own `--help` text and the tests use it, not the plan
brief's original "outlander" example (which does not exist in
`chargen/data/srd/5e-SRD-Backgrounds.json`). Machines that have run
`python3 -m chargen.sync --official` see a far wider catalog than that, but
the examples stay on the ids that are guaranteed to be present everywhere.

`library` (the game's save mechanism) is imported lazily, inside the
function that actually needs it for `--save`, so `python -m chargen races`
and friends never pay that import cost or risk its `sys.path` side effect.
"""

from __future__ import annotations

import argparse
import json
import sys

from chargen import validate as V
from chargen.build import build
from chargen.catalog import Catalog
from chargen.sources import has_official

ABILITY_ORDER = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


# ---------------------------------------------------------------------------
# argument helpers
# ---------------------------------------------------------------------------

def _parse_scores(raw: str) -> dict[str, int]:
    """`"16,13,15,8,12,10"` -> `{"STR": 16, "DEX": 13, ...}`, in the
    STR/DEX/CON/INT/WIS/CHA order this repo uses everywhere else."""
    parts = raw.split(",")
    if len(parts) != len(ABILITY_ORDER):
        raise argparse.ArgumentTypeError(
            f"--scores needs exactly {len(ABILITY_ORDER)} comma-separated "
            f"integers ({','.join(ABILITY_ORDER)}), got {raw!r}")
    try:
        values = [int(p.strip()) for p in parts]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--scores values must all be whole numbers, got {raw!r}")
    return dict(zip(ABILITY_ORDER, values))


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_id_qty_list(raw: str | None) -> list[dict]:
    """"longsword,dagger:2" -> [{"id": "longsword", "quantity": 1},
    {"id": "dagger", "quantity": 2}] — the shape build()'s chosen_weapons/
    chosen_gear Draft fields expect (Task 4).

    Used as an argparse `type=`, so a non-numeric quantity
    (`--weapons longsword:abc`) becomes argparse's own usage error rather
    than a bare ValueError traceback — the same way `--scores` and
    `--ability-choice-assignment` already report a malformed value."""
    out = []
    for part in _split_csv(raw):
        if ":" in part:
            item_id, qty = part.split(":", 1)
            try:
                quantity = int(qty.strip())
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"quantity must be a whole number, got {qty.strip()!r} "
                    f"for {item_id.strip()!r} (expected ID or ID:QUANTITY)")
            out.append({"id": item_id.strip(), "quantity": quantity})
        else:
            out.append({"id": part.strip(), "quantity": 1})
    return out


def _parse_ability_choice_assignment(raw: str) -> dict[str, int]:
    """`"WIS:2,INT:1"` -> `{"WIS": 2, "INT": 1}` — the shape
    `apply_ability_bonuses()`/`validate_ability_choice()` expect for a
    2024-style background's weighted ability_choice pick."""
    out: dict[str, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise argparse.ArgumentTypeError(
                f"--ability-choice-assignment entries must be ABILITY:BONUS, "
                f"got {pair!r}")
        ability, _, bonus = pair.partition(":")
        ability = ability.strip()
        try:
            bonus_value = int(bonus.strip())
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"--ability-choice-assignment bonus must be a whole number, "
                f"got {bonus!r} for {ability!r}")
        out[ability] = bonus_value
    return out


# ---------------------------------------------------------------------------
# listing subcommands
# ---------------------------------------------------------------------------

def cmd_races(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    if args.official and not has_official():
        print("(--official requested, but no official data is installed on "
              "this machine — showing SRD only. Run `python3 -m chargen.sync "
              "--official` to fetch it.)")
    for race in catalog.races():
        print(f"{race.id} — {race.name} ({race.size}, {race.speed} ft)")
    return 0


def cmd_backgrounds(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    for bg in catalog.backgrounds():
        skills = ", ".join(bg.skill_proficiencies) or "none"
        print(f"{bg.id} — {bg.name} ({skills})")
    return 0


def cmd_classes(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    for cls in catalog.classes():
        print(f"{cls.id} — {cls.name} (d{cls.hit_die})")
    return 0


def cmd_spells(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    spells = catalog.spells(cls=args.cls, level=args.level,
                            school=args.school, search=args.search)
    for spell in spells:
        print(f"{spell.name} (level {spell.level}, {spell.school})")
    return 0


def cmd_weapons(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    for weapon in catalog.weapons(category=args.category):
        dice = weapon.damage_dice or "-"
        if weapon.versatile_damage_dice:
            dice = f"{dice}/{weapon.versatile_damage_dice} versatile"
        props = ", ".join(weapon.properties) or "none"
        print(f"{weapon.name} — {weapon.category}, {dice}, {props}")
    return 0


def cmd_armor(args: argparse.Namespace) -> int:
    catalog = Catalog.load("2014")
    for a in catalog.armor():
        print(f"{a['name']} — {a['category']}, AC {a['base_ac']}")
    return 0


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def _auto_skill_picks(catalog: Catalog, class_id: str) -> list[str]:
    """Deterministic default: the first N options from the class's own
    skill_choice, where N is skill_choice["count"]. Not random — the bare
    example command from the plan brief must produce the same result every
    run, and must not require the caller to already know the class's exact
    skill list. If the class id doesn't resolve, return [] and let
    build()'s own validation report the bad class id."""
    try:
        char_class = catalog.class_(class_id)
    except KeyError:
        return []
    choice = char_class.skill_choice or {}
    count = choice.get("count") or 0
    options = list(choice.get("options") or [])
    return options[:count]


def _save_to_library(sheet: dict) -> dict:
    """Imported lazily — see module docstring. Replicates the exact
    sys.path pattern tests/test_library.py uses to import the non-package
    skills/dnd/scripts/library.py."""
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parent.parent / "skills" / "dnd" / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import library

    return library.save(sheet["name"], sheet)


def cmd_build(args: argparse.Namespace) -> int:
    catalog = Catalog.load()

    if args.skills:
        skill_picks = _split_csv(args.skills)
    else:
        skill_picks = _auto_skill_picks(catalog, args.class_id)

    draft = {
        "name": args.name,
        "player": args.player or "",
        "race_id": args.race_id,
        "subrace_id": args.subrace_id,
        "background_id": args.background_id,
        "class_id": args.class_id,
        "subclass_id": args.subclass_id,
        "level": args.level,
        "ability_method": "roll",
        "ability_scores": args.scores,
        "ability_choice_index": args.ability_choice_index,
        "ability_choice_assignment": args.ability_choice_assignment,
        "skill_picks": skill_picks,
        "equipped_armor_id": args.armor_id,
        "shield": args.shield,
        "hp_method": args.hp_method,
        "spells_known": [],
        "spells_prepared": [],
        "alignment": args.alignment or "",
        "backstory": args.backstory or "",
        "chosen_weapons": args.weapons or [],
        "chosen_gear": args.gear or [],
    }

    sheet, problems, warnings = build(draft, catalog)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"⚠ {warning}")

    if args.save:
        _save_to_library(sheet)
        print(f"Saved {sheet['name']} to the library.")
        return 0

    print(json.dumps(sheet, indent=2))
    return 0


# ---------------------------------------------------------------------------
# argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m chargen",
        description="Deterministic D&D 5e character builder — no server, no browser.",
    )
    sub = parser.add_subparsers(dest="command")

    p_races = sub.add_parser("races", help="list playable races")
    p_races.add_argument("--official", action="store_true",
                         help="report whether the official (non-SRD) race "
                              "data is installed. Installed official data is "
                              "always merged into the catalog, with or "
                              "without this flag; passing it only prints a "
                              "note when there is none to merge")
    p_races.set_defaults(func=cmd_races)

    p_backgrounds = sub.add_parser("backgrounds", help="list backgrounds")
    p_backgrounds.set_defaults(func=cmd_backgrounds)

    p_classes = sub.add_parser("classes", help="list classes")
    p_classes.set_defaults(func=cmd_classes)

    p_spells = sub.add_parser("spells", help="list/filter spells")
    p_spells.add_argument("--class", dest="cls", default=None,
                          help="filter by class name, e.g. Wizard (optional "
                               "— omit to list all spells)")
    p_spells.add_argument("--level", type=int, default=None,
                          help="filter by spell level (0 = cantrip)")
    p_spells.add_argument("--school", default=None, help="filter by school, e.g. Evocation")
    p_spells.add_argument("--search", default=None, help="filter by substring of the name")
    p_spells.set_defaults(func=cmd_spells)

    p_weapons = sub.add_parser("weapons", help="list weapons")
    p_weapons.add_argument("--category", default=None,
                           help="filter by category, e.g. martial or simple")
    p_weapons.set_defaults(func=cmd_weapons)

    p_armor = sub.add_parser("armor", help="list armor")
    p_armor.set_defaults(func=cmd_armor)

    p_build = sub.add_parser("build", help="build a character from a draft")
    p_build.add_argument("--name", required=True)
    p_build.add_argument("--race", dest="race_id", required=True)
    p_build.add_argument("--subrace", dest="subrace_id", default=None)
    p_build.add_argument("--class", dest="class_id", required=True)
    p_build.add_argument("--subclass", dest="subclass_id", default=None)
    p_build.add_argument("--level", type=int, required=True)
    p_build.add_argument("--background", dest="background_id", required=True)
    p_build.add_argument("--scores", type=_parse_scores, required=True,
                         help="STR,DEX,CON,INT,WIS,CHA e.g. 16,13,15,8,12,10 "
                              "(each must be 3-18)")
    p_build.add_argument("--skills", default=None,
                         help="comma-separated skill names; omit to "
                              "auto-pick the class's first N legal options")
    p_build.add_argument("--weapons", type=_parse_id_qty_list, default=None,
                         help="comma-separated weapon ids to add on top of "
                              "the class/background starting kit, optionally "
                              "with :QUANTITY, e.g. longsword,dagger:2")
    p_build.add_argument("--gear", type=_parse_id_qty_list, default=None,
                         help="comma-separated gear ids to add on top of "
                              "the class/background starting kit, optionally "
                              "with :QUANTITY, e.g. rope-hempen-50-feet")
    p_build.add_argument("--ability-choice-index", dest="ability_choice_index",
                         type=int, default=None,
                         help="which of the chosen background's ability_choice "
                              "options to use (0-based) — only meaningful for "
                              "a 2024-style background that carries one; a "
                              "2014-style background ignores this")
    p_build.add_argument("--ability-choice-assignment",
                         dest="ability_choice_assignment",
                         type=_parse_ability_choice_assignment, default=None,
                         help="ABILITY:BONUS,ABILITY:BONUS e.g. WIS:2,INT:1 — "
                              "how to spread the chosen ability_choice "
                              "option's weights across abilities")
    p_build.add_argument("--player", default=None)
    p_build.add_argument("--alignment", default=None)
    p_build.add_argument("--backstory", default=None)
    p_build.add_argument("--hp-method", dest="hp_method",
                         choices=V.HP_METHODS, default="max_then_average",
                         help="'max_then_average' (default: max die at level "
                              "1, average after) or 'max_then_max' (house "
                              "rule: max die every level)")
    p_build.add_argument("--shield", action="store_true")
    p_build.add_argument("--armor", dest="armor_id", default=None,
                         help="an armor id to equip, e.g. chain-mail")
    p_build.add_argument("--save", action="store_true",
                         help="save the built character to the library "
                              "instead of printing it")
    p_build.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
