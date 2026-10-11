"""Feat effects (FE series, docs/superpowers/plans/2026-10-11-feat-effects.md).

Pure: no catalog import. Callers pass the resolved feat instances (``resolve.resolved_feats``)
and the effect table (``catalog.feat_effects_data.FEAT_EFFECTS``). A feat follows its own
edition's text under every ruleset (entries are keyed by feat index), so nothing here looks at
the ruleset.

FE1 covers the numeric derived stats: initiative, hit point maximum, walking speed and the
Athlete climb speed. Numeric effects are deduplicated by the feat's edition-independent name
key, so a stray duplicate (the S2 rules already forbid one) can never double Alert or Tough.
"""
from __future__ import annotations

import re


def _name_key(feat: dict) -> str:
    """Same identity as resolve._feat_name_key: the lowercased name without a trailing (...)."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", feat.get("name") or "").strip().lower()


def _origin(feat: dict) -> str:
    return ("asi" if feat.get("_asi_cid") else "invocation" if feat.get("_inv_cid")
            else "fighting-style" if feat.get("_fs_cid") else "species" if feat.get("_species_origin")
            else "background")


def instances(resolved_feats, table: dict) -> list[dict]:
    """One entry per held feat instance that has an effect entry:
    ``{feat, index, prefix, origin, effect}``. Kept-but-hidden picks (A2) are included because
    they are in ``resolved_feats``; ``data_only`` entries carry nothing for the engine."""
    out = []
    for feat in resolved_feats:
        effect = table.get(feat["index"])
        if not effect:
            continue
        prefix = feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"
        out.append({"feat": feat, "index": feat["index"], "prefix": prefix,
                    "origin": _origin(feat), "effect": effect})
    return out


def _numeric(insts: list[dict], key: str) -> list:
    """Effect values for ``key``, one per feat name (first instance wins)."""
    seen, values = set(), []
    for inst in insts:
        if key not in inst["effect"]:
            continue
        name = _name_key(inst["feat"])
        if name in seen:
            continue
        seen.add(name)
        values.append(inst["effect"][key])
    return values


def initiative_parts(insts: list[dict]) -> tuple[int, bool]:
    """(flat bonus, adds the Proficiency Bonus). Alert (PHB) is a flat +5 on top of everything;
    Alert (XPHB) lets you add the Proficiency Bonus, which replaces the Jack of All Trades /
    Remarkable Athlete half bonus (a roll that adds the full bonus gains nothing from half)."""
    values = _numeric(insts, "initiative")
    return sum(v for v in values if isinstance(v, int)), any(v == "pb" for v in values)


def hp_bonus(insts: list[dict], total_level: int) -> int:
    """Tough: twice the character level when gained plus 2 per later level = 2 x current level."""
    return (sum(_numeric(insts, "hp_per_level")) * total_level) + sum(_numeric(insts, "hp_flat"))


def walk_bonus(insts: list[dict]) -> int:
    return sum(_numeric(insts, "walk_bonus"))


def climb_equals_walk(insts: list[dict]) -> bool:
    return any(_numeric(insts, "climb_equals_walk"))
