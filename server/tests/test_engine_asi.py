from engine.asi import ASI_CAP, apply_asi, asi_combinations, asi_exceeds_cap


def test_produces_21_combinations():
    combos = asi_combinations()
    assert len(combos) == 21


def test_six_single_ability_plus_two_options():
    combos = dict(asi_combinations())
    assert combos["str-plus-2"] == [("STR", 2)]
    assert combos["cha-plus-2"] == [("CHA", 2)]
    single_options = [c for c in combos.values() if len(c) == 1]
    assert len(single_options) == 6


def test_fifteen_two_ability_plus_one_options_no_duplicate_pairs():
    combos = dict(asi_combinations())
    two_ability = {oid: deltas for oid, deltas in combos.items() if len(deltas) == 2}
    assert len(two_ability) == 15
    assert combos["str-dex-plus-1-1"] == [("STR", 1), ("DEX", 1)]
    # every two-ability option grants exactly +1/+1, no ability repeated within one option
    for deltas in two_ability.values():
        assert deltas[0][1] == 1 and deltas[1][1] == 1
        assert deltas[0][0] != deltas[1][0]


def test_asi_cap_is_20():
    assert ASI_CAP == 20


def test_exceeds_cap_true_when_a_plus_2_would_cross_20():
    assert asi_exceeds_cap([("STR", 2)], {"STR": 19}) is True
    assert asi_exceeds_cap([("STR", 2)], {"STR": 18}) is False


def test_exceeds_cap_checks_every_ability_in_a_two_ability_option():
    deltas = [("STR", 1), ("DEX", 1)]
    assert asi_exceeds_cap(deltas, {"STR": 20, "DEX": 10}) is True
    assert asi_exceeds_cap(deltas, {"STR": 10, "DEX": 20}) is True
    assert asi_exceeds_cap(deltas, {"STR": 19, "DEX": 19}) is False


def test_exceeds_cap_defaults_missing_ability_to_10():
    assert asi_exceeds_cap([("WIS", 2)], {}) is False


def test_apply_asi_increments_and_does_not_mutate_input():
    scores = {"STR": 14, "DEX": 12}
    result = apply_asi([("STR", 2)], scores)
    assert result == {"STR": 16, "DEX": 12}
    assert scores == {"STR": 14, "DEX": 12}  # original untouched


def test_apply_asi_two_ability_option():
    scores = {"STR": 10, "DEX": 10, "CON": 10}
    result = apply_asi([("STR", 1), ("DEX", 1)], scores)
    assert result == {"STR": 11, "DEX": 11, "CON": 10}


def test_apply_asi_defaults_missing_ability_to_10_before_adding():
    result = apply_asi([("CHA", 2)], {})
    assert result == {"CHA": 12}
