"""RPF: Carouser (ABH) stores `{"gaming set": true}` (a generic category as a fixed grant) although its text says
"Choose one kind of Gaming Set". The converter turns it into a one-pick Gaming Sets card in every ruleset; no other
background or race has a generic tool key as a fixed grant (scan below)."""
import json
from pathlib import Path

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official.proficiencies import _proficiencies_from_5etools, _proficiency_choices_from_5etools
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not official_source.has_official(), reason="official data not fetched")


def test_converter_turns_the_generic_key_into_a_pick():
    raw = {"toolProficiencies": [{"gaming set": True}]}
    assert _proficiencies_from_5etools(raw) == []
    assert _proficiency_choices_from_5etools(raw) == [
        {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "any_tool", "tool_category": "Gaming Sets"}}]


def test_a_concrete_tool_is_still_a_fixed_grant():
    raw = {"toolProficiencies": [{"thieves' tools": True}]}
    assert [p["index"] for p in _proficiencies_from_5etools(raw)] == ["thieves-tools"]
    assert _proficiency_choices_from_5etools(raw) == []


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_carouser_has_a_gaming_set_card_in_every_ruleset(ruleset):
    catalog = load()
    bg = catalog.backgrounds["carouser-abh"]
    assert "gaming-set" not in [p["index"] for p in bg["starting_proficiencies"]]
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
         "background": {"id": "carouser-abh", "choices": {}}, "species": {"id": "human", "choices": {}},
         "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
         "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}}
    card = next(c for c in resolve(d, catalog)["choices"] if c["id"] == "background:carouser-abh:proficiency-choice-0")
    assert card["status"] == "pending" and card["count"] == 1 and {"dice-set", "playing-card-set"} <= {o["id"] for o in card["options"]}


@needs_data
def test_no_other_background_or_race_has_a_generic_tool_key_as_a_fixed_grant():
    from catalog.official.paths import official_dir
    root = official_dir()  # the bundle by default (B2); no machine-specific path
    generic = {"gaming set", "musical instrument", "artisan's tools", "artisan tool", "tool"}
    hits = []
    for name, keys in (("backgrounds.json", ("background",)), ("races.json", ("race", "subrace"))):
        data = json.loads((root / name).read_text())
        for k in keys:
            for rec in data.get(k, []):
                for entry in rec.get("toolProficiencies") or []:
                    hits += [(rec.get("name"), key) for key, v in entry.items() if v is True and key in generic]
    assert hits == [("Carouser", "gaming set")]  # raw data; the converter now handles it
