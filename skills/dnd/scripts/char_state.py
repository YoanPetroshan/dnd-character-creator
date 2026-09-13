#!/usr/bin/env python3
"""
char_state.py — the ONLY way to read or write a character's state.

Pull (read only what you need, not the whole sheet every turn):
    python3 char_state.py <campaign> <slug> --get combat|inventory|spells|proficiencies|all

Push (deltas and validated sets — never a raw overwrite):
    python3 char_state.py <campaign> <slug> --hp-delta -5
    python3 char_state.py <campaign> <slug> --hp-set 12
    python3 char_state.py <campaign> <slug> --rest long
    python3 char_state.py <campaign> <slug> --slot-use 1
    python3 char_state.py <campaign> <slug> --equip "Chain Mail"
    python3 char_state.py <campaign> <slug> --item-add "Chain Mail:1"
    python3 char_state.py <campaign> <slug> --currency-delta gp:-15
    python3 char_state.py <campaign> <slug> --condition-add Poisoned
    python3 char_state.py <campaign> <slug> --multiclass-add "Wizard:Evocation:1"

Every push writes the canonical YAML, regenerates the markdown view, and
pushes to the live display panel, atomically — see char_state_sync.write_all.
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import paths  # noqa: E402
import char_state_derive as derive  # noqa: E402
import char_state_mutate as mutate  # noqa: E402
import char_state_sync as sync  # noqa: E402
import char_state_validate as validate  # noqa: E402
from char_state_schema import load_character  # noqa: E402


def _split2(spec: str) -> tuple[str, str]:
    a, _, b = spec.partition(":")
    return a, b


# Every push-type flag's argparse dest. Deliberately excludes campaign, slug,
# get, display_port (not mutations) and slot_restore_count / force (modifiers
# that only matter alongside another mutation flag, never triggers by
# themselves) — used only to detect "--get combined with a mutation" below.
_MUTATION_FLAG_DESTS = [
    "hp_delta", "hp_set", "temp_hp_set", "death_save_success", "death_save_failure",
    "death_save_reset", "rest",
    "slot_use", "slot_restore", "pact_slot_use", "pact_slot_restore",
    "spell_add", "spell_remove", "prepare", "unprepare",
    "item_add", "item_remove", "equip", "unequip", "misc_add", "misc_remove",
    "currency_delta",
    "condition_add", "condition_remove", "inspiration", "exhaustion",
    "attunement_add", "attunement_remove",
    "multiclass_add", "level_set",
]


def _has_mutation_flags(args: argparse.Namespace) -> bool:
    for dest in _MUTATION_FLAG_DESTS:
        val = getattr(args, dest)
        if val is True or (not isinstance(val, bool) and val is not None):
            return True
    return False


def _fmt_get(char, ruleset: str, section: str) -> str:
    if section in ("combat", "all"):
        ac = derive.compute_ac(char, ruleset=ruleset)
        print(f"HP: {char.combat.hp_current}/{char.combat.hp_max} (temp {char.combat.hp_temp})  AC: {ac}  "
              f"Speed: {char.combat.speed}ft  Prof: +{derive.compute_proficiency_bonus(char)}")
        for atk in derive.compute_attacks(char, ruleset=ruleset):
            print(f"  {atk['name']}: {atk['attack_bonus']:+d} to hit, {atk['damage']} {atk['damage_type']}")
    if section in ("inventory", "all"):
        c = char.currency
        print(f"Currency: {c.gp}gp {c.sp}sp {c.cp}cp {c.ep}ep {c.pp}pp")
        for item in char.equipment:
            print(f"  [{'x' if item.equipped else ' '}] {item.name} x{item.quantity}")
        for item in char.misc_items:
            print(f"  - {item.name} x{item.quantity}" + (f" ({item.note})" if item.note else ""))
    if section in ("spells", "all"):
        slots = derive.compute_spell_slots(char, ruleset=ruleset)
        for lvl in sorted(slots):
            print(f"  Level {lvl} slots: {slots[lvl].used}/{slots[lvl].max}")
        pact = derive.compute_pact_magic_slots(char)
        if pact:
            print(f"  Pact Magic slots: {pact.used}/{pact.max}")
        for s in char.spells:
            print(f"  {'[P]' if s.prepared else '[ ]'} {s.name} ({s.cls})")
    if section in ("proficiencies", "all"):
        p = char.proficiencies
        print(f"Saves: {', '.join(p.saving_throws)}  Skills: {', '.join(p.skills)}")
        print(f"Armor: {', '.join(p.armor)}  Weapons: {', '.join(p.weapons)}  Languages: {', '.join(p.languages)}")
    return ""


def main() -> int:
    p = argparse.ArgumentParser(description="Read or mutate a character's canonical state.")
    p.add_argument("campaign")
    p.add_argument("slug")
    p.add_argument("--get", choices=["combat", "inventory", "spells", "proficiencies", "all"])
    p.add_argument("--display-port", type=int, default=5001)

    p.add_argument("--hp-delta", type=int)
    p.add_argument("--hp-set", type=int)
    p.add_argument("--temp-hp-set", type=int)
    p.add_argument("--death-save-success", action="store_true")
    p.add_argument("--death-save-failure", action="store_true")
    p.add_argument("--death-save-reset", action="store_true")
    p.add_argument("--rest", choices=["short", "long"])

    p.add_argument("--slot-use", type=int, metavar="LEVEL")
    p.add_argument("--slot-restore", type=int, metavar="LEVEL")
    p.add_argument("--slot-restore-count", type=int, default=1)
    p.add_argument("--pact-slot-use", action="store_true")
    p.add_argument("--pact-slot-restore", action="store_true")
    p.add_argument("--spell-add", metavar="NAME:CLASS[:prepared]")
    p.add_argument("--spell-remove", metavar="NAME")
    p.add_argument("--prepare", metavar="NAME")
    p.add_argument("--unprepare", metavar="NAME")

    p.add_argument("--item-add", metavar="NAME:QTY")
    p.add_argument("--item-remove", metavar="NAME[:QTY]")
    p.add_argument("--equip", metavar="NAME")
    p.add_argument("--unequip", metavar="NAME")
    p.add_argument("--misc-add", metavar="NAME:QTY:NOTE")
    p.add_argument("--misc-remove", metavar="NAME[:QTY]")
    p.add_argument("--currency-delta", metavar="DENOM:AMOUNT")

    p.add_argument("--condition-add", metavar="NAME")
    p.add_argument("--condition-remove", metavar="NAME")
    p.add_argument("--inspiration", choices=["true", "false"])
    p.add_argument("--exhaustion", type=int)
    p.add_argument("--attunement-add", metavar="NAME")
    p.add_argument("--attunement-remove", metavar="NAME")

    p.add_argument("--multiclass-add", metavar="CLASS:SUBCLASS:LEVEL")
    p.add_argument("--level-set", metavar="CLASS:LEVEL")
    p.add_argument("--force", action="store_true")

    args = p.parse_args()

    ruleset = paths.campaign_ruleset(args.campaign)
    char = load_character(args.campaign, args.slug)

    # Reconcile derived spell slots into the loaded object BEFORE anything
    # else reads or mutates it. `max` per level is a derived value (from the
    # class table via the multiclass effective-caster-level formula) that is
    # never authored by hand, but `slot_use`/`slot_restore`/`apply_rest` all
    # operate on `char.spell_slots` as STORED state. Without this step the
    # stored dict stays whatever the YAML happened to have (usually `{}`), so
    # `--get spells` printed correct derived maxes while `--slot-use 1`
    # immediately errored "no level-1 slots remaining" against the empty dict,
    # and `--rest long`'s reset looped over nothing. compute_spell_slots
    # preserves each level's existing `used` count (clamped to the new `max`),
    # so this is safe to run unconditionally on every invocation.
    char.spell_slots = derive.compute_spell_slots(char, ruleset=ruleset)
    pact = derive.compute_pact_magic_slots(char)
    if pact is not None:
        char.pact_magic_slots = pact

    if args.get and _has_mutation_flags(args):
        print(
            "error: --get cannot be combined with a mutation flag in the same "
            "invocation — pull and push are separate calls",
            file=sys.stderr,
        )
        return 1

    if args.get:
        _fmt_get(char, ruleset, args.get)
        return 0

    try:
        if args.hp_delta is not None:
            mutate.hp_delta(char, args.hp_delta)
        if args.hp_set is not None:
            mutate.hp_set(char, args.hp_set)
        if args.temp_hp_set is not None:
            mutate.temp_hp_set(char, args.temp_hp_set)
        if args.death_save_success:
            mutate.death_save_increment(char, True)
        if args.death_save_failure:
            mutate.death_save_increment(char, False)
        if args.death_save_reset:
            mutate.death_save_reset(char)
        if args.rest:
            mutate.apply_rest(char, args.rest)

        if args.slot_use is not None:
            mutate.slot_use(char, args.slot_use)
        if args.slot_restore is not None:
            mutate.slot_restore(char, args.slot_restore, args.slot_restore_count)
        if args.pact_slot_use:
            mutate.pact_slot_use(char)
        if args.pact_slot_restore:
            mutate.pact_slot_restore(char)
        if args.spell_add:
            parts = args.spell_add.split(":")
            if len(parts) < 2:
                raise ValueError(f"--spell-add needs NAME:CLASS, got {args.spell_add!r}")
            name, cls = parts[0], parts[1]
            prepared = len(parts) > 2 and parts[2].lower() == "prepared"
            mutate.spell_add(char, name, cls, prepared=prepared, ruleset=ruleset)
        if args.spell_remove:
            mutate.spell_remove(char, args.spell_remove)
        if args.prepare:
            mutate.spell_set_prepared(char, args.prepare, True)
        if args.unprepare:
            mutate.spell_set_prepared(char, args.unprepare, False)

        if args.item_add:
            name, qty = _split2(args.item_add)
            mutate.item_add(char, name, int(qty or 1), ruleset=ruleset)
        if args.item_remove:
            name, qty = _split2(args.item_remove)
            mutate.item_remove(char, name, int(qty) if qty else None)
        if args.equip:
            mutate.equip(char, args.equip)
        if args.unequip:
            mutate.unequip(char, args.unequip)
        if args.misc_add:
            parts = args.misc_add.split(":", 2)
            name = parts[0]
            qty = int(parts[1]) if len(parts) > 1 and parts[1] else 1
            note = parts[2] if len(parts) > 2 else ""
            mutate.misc_add(char, name, qty, note)
        if args.misc_remove:
            name, qty = _split2(args.misc_remove)
            mutate.misc_remove(char, name, int(qty) if qty else None)
        if args.currency_delta:
            denom, amount = _split2(args.currency_delta)
            mutate.currency_delta(char, denom, int(amount))

        if args.condition_add:
            mutate.condition_add(char, args.condition_add, ruleset=ruleset)
        if args.condition_remove:
            mutate.condition_remove(char, args.condition_remove)
        if args.inspiration:
            mutate.set_inspiration(char, args.inspiration == "true")
        if args.exhaustion is not None:
            mutate.set_exhaustion(char, args.exhaustion)
        if args.attunement_add:
            mutate.attunement_add(char, args.attunement_add)
        if args.attunement_remove:
            mutate.attunement_remove(char, args.attunement_remove)

        if args.multiclass_add:
            cls, subclass, level = args.multiclass_add.split(":")
            mutate.multiclass_add(char, cls, subclass, int(level), force=args.force)
        if args.level_set:
            cls, level = args.level_set.split(":")
            mutate.level_set(char, cls, int(level))

    except (ValueError, validate.ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Surface any name that could only be confirmed against the 2014 dataset
    # because this campaign's ruleset has no dataset bundled. The mutation
    # still stands — but the DM must see that the check was weaker than it
    # looks, rather than the degradation being invisible.
    for notice in validate.take_fallback_notices():
        print(f"warning: {notice}", file=sys.stderr)

    # The YAML/markdown writes are what "success" means here; a failed
    # display push is reported but never turns into a non-zero exit, so a
    # down panel can't block a real state save.
    display_ok = sync.write_all(
        args.campaign, args.slug, char, ruleset=ruleset, display_port=args.display_port,
    )
    print("OK" if display_ok else "OK (display sync failed — panel may be stale)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
