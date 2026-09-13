#!/usr/bin/env python3
"""char_state_validate.py — reject unknown catalog names before they can be
written into a character's YAML. Every push command that accepts an item,
spell, or condition name funnels it through here first.

Two things this module does beyond a yes/no check:

1. **Canonical names.** `lookup_record` matches fuzzily and case-
   insensitively, so `--item-add "scale mail"` validates fine against the
   record whose real name is "Scale Mail". Callers used to then store the
   raw user string, which made `--equip "Scale Mail"` fail with
   "not in inventory" against the stored "scale mail", and let two rows
   differing only in case coexist. Every validator therefore returns the
   matched record's OWN `name` field, and mutators store that.

2. **Missing-dataset tolerance.** `skills/dnd/data/dnd5e_srd_2024.json` is
   not bundled. `lookup.lookup_record(..., ruleset="2024")` short-circuits
   to None for EVERY query when a ruleset's dataset is absent (see
   lookup.py's `if not _data_by_rs.get(rs): return None`), which is
   indistinguishable here from "you typed a nonsense name". The result was
   that --item-add / --spell-add / --condition-add were completely unusable
   on any 2024-ruleset campaign, rejecting even perfectly valid names.

   So: when the requested ruleset misses, re-probe the same query against
   2014 before concluding the name is bad. A 2014 hit means the name is
   real and the requested ruleset's dataset simply isn't on disk — allow it
   through, but record a fallback notice so the CLI can warn the DM on
   stderr rather than degrading silently. Only both rulesets missing is a
   genuine typo, and that still raises.

   Deliberately implemented here rather than in lookup.py: lookup.py is
   pre-existing shared infrastructure well outside this feature's scope,
   and rewiring its dataset-loading/fallback logic is a far bigger and
   riskier change than this narrow gap warrants.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import lookup  # noqa: E402


class ValidationError(ValueError):
    pass


@dataclass
class ValidationResult:
    """What a validator hands back on success.

    `name` is the CANONICAL catalog name (the record's own `name` field),
    which is what callers must store — never the raw user string.
    `ruleset_fallback` is True when the requested ruleset had no dataset and
    the name was confirmed against 2014 instead.
    """
    name: str
    record: dict
    ruleset_fallback: bool = False
    requested_ruleset: str = "2014"


# Fallback notices accumulated since the last drain. The mutation layer
# (char_state_mutate) is a set of pure functions returning a Character, so
# there is no return channel from there back up to the CLI; the CLI drains
# this instead and prints one stderr warning per notice. Kept module-level
# and explicitly drained rather than logged, so tests can assert on it.
_fallback_notices: list[str] = []


def take_fallback_notices() -> list[str]:
    """Return and clear every fallback notice recorded so far."""
    notices = list(_fallback_notices)
    _fallback_notices.clear()
    return notices


def _canonical(record: dict, fallback_name: str) -> str:
    name = (record or {}).get("name")
    return name if isinstance(name, str) and name.strip() else fallback_name


def _validate(name: str, category: str, label: str, ruleset: str) -> ValidationResult:
    record = lookup.lookup_record(name, category=category, ruleset=ruleset)
    if record is not None:
        return ValidationResult(
            name=_canonical(record, name), record=record,
            ruleset_fallback=False, requested_ruleset=ruleset,
        )

    # Miss in the requested ruleset. Before calling it a typo, check whether
    # this ruleset has a dataset at all by re-probing the same query against
    # 2014 — a hit there means the dataset is missing, not the name.
    if ruleset != "2014":
        record = lookup.lookup_record(name, category=category, ruleset="2014")
        if record is not None:
            canonical = _canonical(record, name)
            _fallback_notices.append(
                f"validated {canonical!r} against the 2014 dataset — no "
                f"{ruleset} dataset is bundled for this campaign's ruleset"
            )
            return ValidationResult(
                name=canonical, record=record,
                ruleset_fallback=True, requested_ruleset=ruleset,
            )

    raise ValidationError(f"unknown {label}: {name!r} — not found in the SRD dataset")


def validate_item_name(name: str, ruleset: str = "2014") -> ValidationResult:
    return _validate(name, category="item", label="item", ruleset=ruleset)


def validate_spell_name(name: str, ruleset: str = "2014") -> ValidationResult:
    return _validate(name, category="spell", label="spell", ruleset=ruleset)


def validate_condition_name(name: str, ruleset: str = "2014") -> ValidationResult:
    return _validate(name, category="condition", label="condition", ruleset=ruleset)
