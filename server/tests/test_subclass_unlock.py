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
