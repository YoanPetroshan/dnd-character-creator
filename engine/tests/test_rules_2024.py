import pytest

from engine.rules_2024 import (
    DeathSaveState,
    SKILL_DC,
    apply_damage_at_zero,
    apply_death_save,
    concentration_dc,
    is_instant_death,
    long_rest_hit_dice_regained,
)


def test_ten_or_more_is_a_success():
    s = apply_death_save(DeathSaveState(), 10)
    assert s.successes == 1 and s.failures == 0


def test_nine_or_less_is_a_failure():
    s = apply_death_save(DeathSaveState(), 9)
    assert s.failures == 1 and s.successes == 0


def test_natural_twenty_wakes_at_one_hp():
    s = apply_death_save(DeathSaveState(), 20)
    assert s.awake is True
    assert s.dead is False


def test_natural_one_is_two_failures():
    s = apply_death_save(DeathSaveState(), 1)
    assert s.failures == 2


def test_three_successes_stabilise():
    s = DeathSaveState()
    for _ in range(3):
        s = apply_death_save(s, 12)
    assert s.stable is True and s.dead is False


def test_three_failures_kill():
    s = DeathSaveState()
    for _ in range(3):
        s = apply_death_save(s, 5)
    assert s.dead is True


def test_natural_one_twice_kills():
    s = apply_death_save(DeathSaveState(), 1)
    s = apply_death_save(s, 1)
    assert s.dead is True


def test_damage_at_zero_adds_one_failure():
    assert apply_damage_at_zero(DeathSaveState()).failures == 1


def test_crit_at_zero_adds_two_failures():
    assert apply_damage_at_zero(DeathSaveState(), crit=True).failures == 2


def test_damage_at_zero_can_kill():
    s = DeathSaveState(failures=1)
    assert apply_damage_at_zero(s, crit=True).dead is True


@pytest.mark.parametrize("overflow,hp_max,expected", [
    (30, 25, True), (25, 25, True), (24, 25, False), (0, 25, False),
])
def test_instant_death(overflow, hp_max, expected):
    assert is_instant_death(overflow, hp_max) is expected


@pytest.mark.parametrize("damage,dc", [(0, 10), (19, 10), (20, 10), (22, 11), (61, 30), (100, 30)])
def test_concentration_dc(damage, dc):
    assert concentration_dc(damage) == dc


@pytest.mark.parametrize("total,regained", [(1, 1), (2, 1), (5, 2), (8, 4)])
def test_long_rest_hit_dice(total, regained):
    assert long_rest_hit_dice_regained(total) == regained


def test_damage_at_zero_unstabilizes_and_death_saves_resume():
    # Stabilize via 3 successes.
    s = DeathSaveState()
    for _ in range(3):
        s = apply_death_save(s, 12)
    assert s.stable is True and s.successes == 0

    # A non-crit hit while stable ends the stable condition (dying resumes).
    s = apply_damage_at_zero(s)
    assert s.stable is False

    # apply_death_save must actually process a new roll now, not be a no-op.
    s2 = apply_death_save(s, 12)
    assert s2.successes == s.successes + 1


def test_stabilising_resets_failures_too():
    """PHB 2024: "The number of both is reset to zero when you regain any Hit
    Points or become Stable."

    Regression: `_settle` used to reset only the successes, so the realistic
    sequence below (fail, fail, then three successes) stabilised the character
    while silently leaving `failures=2` on the sheet. The next single non-crit
    hit then added one more failure and killed them outright.
    """
    s = DeathSaveState()
    s = apply_death_save(s, 5)   # fail
    s = apply_death_save(s, 5)   # fail
    assert s.failures == 2
    for _ in range(3):           # three successes → Stable
        s = apply_death_save(s, 12)

    assert s.stable is True
    assert s.successes == 0
    assert s.failures == 0, "becoming Stable must reset failures, not just successes"

    # And the consequence that made this a Critical: one ordinary hit while
    # down must NOT be lethal for a character who just stabilised.
    hit = apply_damage_at_zero(s)
    assert hit.dead is False, "a single non-crit hit must not kill a just-stabilised PC"
    assert hit.failures == 1


def test_skill_dc_ladder():
    assert SKILL_DC == {"лесно": 10, "средно": 15, "трудно": 20,
                        "много трудно": 25, "почти невъзможно": 30}
