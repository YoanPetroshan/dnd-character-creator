import pytest

from engine import encounters


def test_budget_matches_dmg_2024_table():
    assert encounters.party_budget(4, 2) == {"low": 500, "moderate": 750, "high": 1000}
    assert encounters.party_budget(1, 4) == {"low": 200, "moderate": 300, "high": 400}
    assert encounters.party_budget(8, 3) == {"low": 3000, "moderate": 5100, "high": 6300}


def test_budget_rejects_unsupported_level():
    with pytest.raises(ValueError):
        encounters.party_budget(21, 2)
    with pytest.raises(ValueError):
        encounters.party_budget(0, 2)


def test_budget_rejects_zero_players():
    with pytest.raises(ValueError):
        encounters.party_budget(4, 0)


@pytest.mark.parametrize("cr,xp", [("0", 10), ("1/8", 25), ("1/4", 50),
                                   ("1/2", 100), ("1", 200), ("5", 1800)])
def test_cr_xp_table(cr, xp):
    assert encounters.CR_XP[cr] == xp


def test_monster_xp_uses_the_corpus(monkeypatch):
    monkeypatch.setattr(encounters, "find",
                        lambda name, kind=None: {"kind": "monster", "name": name})
    monkeypatch.setattr(encounters, "fetch_record", lambda entry: {"cr": "1"})
    assert encounters.monster_xp("Goblin Boss") == 200


def test_monster_xp_handles_dict_shaped_cr_for_lair_monsters(monkeypatch):
    monkeypatch.setattr(encounters, "find",
                        lambda name, kind=None: {"kind": "monster", "name": name})
    monkeypatch.setattr(encounters, "fetch_record",
                        lambda entry: {"cr": {"cr": "14", "xpLair": 13000}})
    assert encounters.monster_xp("Adult Black Dragon") == encounters.CR_XP["14"]


def test_monster_xp_unknown_returns_none(monkeypatch):
    monkeypatch.setattr(encounters, "find", lambda name, kind=None: None)
    assert encounters.monster_xp("Nonexistent") is None


def test_encounter_xp_sums_and_reports_unresolved(monkeypatch):
    table = {"Goblin Boss": "1", "Goblin Warrior": "1/4"}
    monkeypatch.setattr(encounters, "find",
                        lambda name, kind=None: {"name": name} if name in table else None)
    monkeypatch.setattr(encounters, "fetch_record",
                        lambda entry: {"cr": table[entry["name"]]})
    total, missing = encounters.encounter_xp(
        ["Goblin Boss", "Goblin Warrior", "Goblin Warrior", "Ghost Of Nothing"]
    )
    assert total == 200 + 50 + 50
    assert missing == ["Ghost Of Nothing"]


def test_classify_bands():
    """The DMG's numbers are ceilings ("spend as much as you can without going
    over"), so each band ends AT its budget. The previous expectations encoded
    the opposite (floors for the next band up), which under-reported danger by
    a full band — 760 XP against a 750 Moderate ceiling was called "Moderate".
    """
    budget = {"low": 500, "moderate": 750, "high": 1000}
    assert encounters.classify(300, budget) == "Low"
    assert encounters.classify(500, budget) == "Low"
    assert encounters.classify(501, budget) == "Moderate"
    assert encounters.classify(750, budget) == "Moderate"
    assert encounters.classify(760, budget) == "High"
    assert encounters.classify(999, budget) == "High"
    assert encounters.classify(1000, budget) == "High"
    assert encounters.classify(1001, budget) == "над High"
    assert encounters.classify(1500, budget) == "над High"


def test_budget_covers_levels_1_to_20():
    """DMG 2024 publishes the full 1–20 table; the engine used to stop at 8
    and hard-raise beyond it."""
    assert sorted(encounters.XP_BUDGET) == list(range(1, 21))
    assert encounters.party_budget(9, 1) == {"low": 1300, "moderate": 2000, "high": 2600}
    assert encounters.party_budget(15, 1) == {"low": 3300, "moderate": 5400, "high": 7800}
    assert encounters.party_budget(20, 2) == {"low": 12800, "moderate": 26400, "high": 44000}
