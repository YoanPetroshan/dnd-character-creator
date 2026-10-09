"""Round-2 audit F4: a subclass below its unlock level is ignored (level-down
keeps `subclassId` in the draft because the UI only hides the select)."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls, sub, level):
    return {
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}],
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def test_fighter_level_1_ignores_champion(catalog):
    r = resolve(_draft("fighter", "champion", 1), catalog)
    assert r["sheet"]["classes"][0]["subclass"] is None
    assert [p for p in r["pruned"] if p["choiceId"] == "class:fighter:subclass"]
    assert r["problems"] == []


def test_fighter_level_3_keeps_champion(catalog):
    r = resolve(_draft("fighter", "champion", 3), catalog)
    assert r["sheet"]["classes"][0]["subclass"]["id"] == "champion"
    assert not [p for p in r["pruned"] if p["choiceId"] == "class:fighter:subclass"]


def test_wizard_level_1_bladesinging_grants_no_armor(catalog):
    r = resolve(_draft("wizard", "bladesinging-tce", 1), catalog)
    assert "light-armor" not in r["sheet"]["proficiencies"]["armor"]
    assert r["sheet"]["classes"][0]["subclass"] is None


def test_wizard_level_2_bladesinging_grants_light_armor(catalog):
    r = resolve(_draft("wizard", "bladesinging-tce", 2), catalog)
    assert "light-armor" in r["sheet"]["proficiencies"]["armor"]


# ----------------------------------------------------- O2: ruleset-dependent unlock
# All 12 XPHB class records place the subclass feature at level 3 (verified by script).

def _ruleset_draft(cls, sub, level, ruleset):
    return {**_draft(cls, sub, level), "ruleset": ruleset}


@pytest.mark.parametrize("cls,sub", [
    ("wizard", "evocation"), ("cleric", "life"), ("sorcerer", "draconic"), ("warlock", "fiend"), ("druid", "land"),
])
def test_2024_early_unlock_classes_wait_until_level_3(catalog, cls, sub):
    low = resolve(_ruleset_draft(cls, sub, 2, "2024"), catalog)
    assert low["sheet"]["classes"][0]["subclass"] is None
    assert [p for p in low["pruned"] if p["choiceId"] == f"class:{cls}:subclass" and "level 3" in p["reason"]]
    assert resolve(_ruleset_draft(cls, sub, 3, "2024"), catalog)["sheet"]["classes"][0]["subclass"]["id"] == sub


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_other_rulesets_keep_the_class_unlock_level(catalog, ruleset):
    assert resolve(_ruleset_draft("wizard", "evocation", 2, ruleset), catalog)["sheet"]["classes"][0]["subclass"]["id"] == "evocation"
    assert resolve(_ruleset_draft("cleric", "life", 1, ruleset), catalog)["sheet"]["classes"][0]["subclass"]["id"] == "life"


def test_2024_does_not_change_classes_already_unlocking_at_3(catalog):
    assert resolve(_ruleset_draft("fighter", "champion", 3, "2024"), catalog)["sheet"]["classes"][0]["subclass"]["id"] == "champion"


def test_unlock_level_helper():
    from catalog.reference_data import subclass_unlock_level
    assert subclass_unlock_level("wizard", "2024") == 3
    assert subclass_unlock_level("wizard", "2014") == 2 and subclass_unlock_level("wizard", "mixed") == 2
    assert subclass_unlock_level("cleric", "2024") == 3 and subclass_unlock_level("cleric", "mixed") == 1
    assert subclass_unlock_level("fighter", "2024") == 3
    assert subclass_unlock_level("nope", "2024") is None


def test_class_api_reports_the_unlock_level_by_ruleset():
    from app import app
    client = app.test_client()
    assert client.get("/api/catalog/class/wizard?ruleset=2024").get_json()["subclassUnlockLevel"] == 3
    assert client.get("/api/catalog/class/wizard?ruleset=2014").get_json()["subclassUnlockLevel"] == 2
    assert client.get("/api/catalog/class/wizard").get_json()["subclassUnlockLevel"] == 2
    assert client.get("/api/catalog/class/cleric?ruleset=2024").get_json()["subclassUnlockLevel"] == 3
