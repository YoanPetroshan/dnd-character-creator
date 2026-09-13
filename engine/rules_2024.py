"""D&D 5e 2024 rules that are pure computation.

Encoded here so they are identical every session, instead of being recalled.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

SKILL_DC: dict[str, int] = {
    "лесно": 10,
    "средно": 15,
    "трудно": 20,
    "много трудно": 25,
    "почти невъзможно": 30,
}


@dataclass(frozen=True)
class DeathSaveState:
    successes: int = 0
    failures: int = 0
    stable: bool = False
    dead: bool = False
    awake: bool = False


def _settle(state: DeathSaveState) -> DeathSaveState:
    if state.failures >= 3:
        return replace(state, failures=3, dead=True)
    if state.successes >= 3:
        # PHB 2024, Death Saving Throws: "The number of both is reset to zero
        # when you regain any Hit Points or become Stable." Carrying failures
        # across stabilization would let a single later hit (which adds one
        # failure) finish off a character who is supposed to start over at 0.
        return replace(state, successes=0, failures=0, stable=True)
    return state


def apply_death_save(state: DeathSaveState, d20: int) -> DeathSaveState:
    if state.dead or state.stable or state.awake:
        return state
    if d20 == 20:
        return replace(state, successes=0, failures=0, stable=True, awake=True)
    if d20 == 1:
        return _settle(replace(state, failures=state.failures + 2))
    if d20 >= 10:
        return _settle(replace(state, successes=state.successes + 1))
    return _settle(replace(state, failures=state.failures + 1))


def apply_damage_at_zero(state: DeathSaveState, crit: bool = False) -> DeathSaveState:
    if state.dead or state.awake:
        return state
    added = 2 if crit else 1
    return _settle(replace(state, failures=state.failures + added, stable=False))


def is_instant_death(overflow_damage: int, hp_max: int) -> bool:
    """Leftover damage after dropping to 0 that meets or exceeds HP maximum."""
    return overflow_damage >= hp_max > 0


def concentration_dc(damage: int) -> int:
    return min(30, max(10, damage // 2))


def long_rest_hit_dice_regained(total_hit_dice: int) -> int:
    """A long rest returns half a character's total Hit Dice, minimum one."""
    return max(1, total_hit_dice // 2)
