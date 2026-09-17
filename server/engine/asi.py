"""Pure ability-score-improvement (ASI) math: the 21 valid ASI
combinations for six abilities, and cap-checking/application against a
character's current final ability scores. No I/O, no catalog access —
matches engine/derived.py's and engine/equipment.py's style. See the
Phase 3a design spec §4 for why this fits the existing generic Choice
model rather than needing a new mechanism: options here are
pre-computed combination strings (a pure 5e rule, not SRD catalog
content), not resolved from any bundled JSON envelope.
"""
from __future__ import annotations

from catalog.reference_data import ABILITIES

ASI_CAP = 20


def asi_combinations() -> list[tuple[str, list[tuple[str, int]]]]:
    """Returns [(option_id, [(ability, delta), ...]), ...] — 6 "+2 to
    one ability" options plus 15 "+1 to two abilities" options
    (C(6,2)), 21 total, in a stable, deterministic order (single-ability
    options first, then two-ability options in ABILITIES order)."""
    combos: list[tuple[str, list[tuple[str, int]]]] = []
    for ab in ABILITIES:
        combos.append((f"{ab.lower()}-plus-2", [(ab, 2)]))
    for i, ab1 in enumerate(ABILITIES):
        for ab2 in ABILITIES[i + 1:]:
            combos.append((f"{ab1.lower()}-{ab2.lower()}-plus-1-1", [(ab1, 1), (ab2, 1)]))
    return combos


def asi_exceeds_cap(deltas: list[tuple[str, int]], current_scores: dict[str, int]) -> bool:
    return any(current_scores.get(ab, 10) + delta > ASI_CAP for ab, delta in deltas)


def apply_asi(deltas: list[tuple[str, int]], scores: dict[str, int]) -> dict[str, int]:
    result = dict(scores)
    for ab, delta in deltas:
        result[ab] = result.get(ab, 10) + delta
    return result
