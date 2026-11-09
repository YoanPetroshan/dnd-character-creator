"""W11: one test per DATA_OVERRIDES entry. Each asserts the RAW 5etools record still has the defect the override
corrects (an upstream fix fails loudly: remove the override and its registry entry) and that the registry's `where`
symbol still exists. Skipped when the official data is not synced."""
import importlib
import json

import pytest

from catalog.official_source import has_official, official_dir
from catalog.reference_data import DATA_OVERRIDES

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


def _load(name: str, key: str | None = None):
    data = json.loads((official_dir() / name).read_text())
    return data[key] if key else data


def _find(records, name, source):
    return next(r for r in records if r["name"] == name and r["source"] == source)


def _bg(name, source):
    return _find(_load("backgrounds.json", "background"), name, source)


def _feat(name, source):
    return _find(_load("feats.json", "feat"), name, source)


def test_registry_entries_are_complete_and_where_exists():
    assert set(DATA_OVERRIDES) == set(CHECKS)
    for key, entry in DATA_OVERRIDES.items():
        assert set(entry) == {"what", "where", "raw_record_pin", "reason"}, key
        assert set(entry["raw_record_pin"]) == {"file", "record", "defect"}, key
        module, _, symbol = entry["where"].partition(":")
        assert hasattr(importlib.import_module(module), symbol), f"{key}: {entry['where']} no longer exists"


def check_cleric():
    cls = _find(_load("class/class-cleric.json", "class"), "Cleric", "XPHB")
    se = cls["startingEquipment"]
    assert se["defaultData"][0]["A"][-1] == {"value": 7000}
    assert "7 GP; or (B) 110 GP" in se["entries"][0]


def check_mulhorandi():
    se = _bg("Mulhorandi Tomb Raider", "FRHoF")["startingEquipment"][0]["A"]
    assert {"item": "waterskin|xphb", "displayName": "Waterskin 26 GP"} in se
    assert not any(isinstance(m, dict) and "value" in m for m in se)


def check_scribe():
    se = _bg("Scribe", "XPHB")["startingEquipment"][0]["A"]
    assert {"item": "oil|xphb"} in se and {"item": "parchment|xphb"} in se


def check_carouser():
    assert _bg("Carouser", "ABH")["toolProficiencies"] == [{"gaming set": True}]


def check_elemental_adept():
    assert "repeatable" not in _feat("Elemental Adept", "PHB")


def check_echoing_soul():
    feat = _feat("Echoing Soul", "RHW")
    assert feat["skillProficiencies"] == [{"any": 1}]
    assert "proficiency in two skills of your choice" in json.dumps(feat["entries"])


def check_harper():
    assert _feat("Harper Agent", "FRHoF")["languageProficiencies"] == [{"thieves' cant": True}]


def check_genie():
    bg = _bg("Genie Touched", "FRHoF")
    assert "feats" not in bg
    assert "Magic Initiate|XPHB} (Wizard)" in json.dumps(bg["entries"])


def check_scc_students():
    from catalog.reference_data import BACKGROUND_FEAT_VARIANT_FROM_TEXT as table
    for key, row in table.items():
        name, _, source = key.partition("|")
        bg = _bg(name.title(), source.upper())
        assert bg["feats"] == [{"strixhaven initiate|scc": True}]
        assert row["quote"] in json.dumps(bg["entries"])


def check_srd_paladin():
    import pathlib
    path = pathlib.Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd" / "5e-SRD-Classes.json"
    paladin = next(c for c in json.loads(path.read_text(encoding="utf-8")) if c["index"] == "paladin")
    env = paladin["starting_equipment_options"][1]
    nested = next(o["choice"] for o in env["from"]["options"] if o["option_type"] == "choice")
    assert env["desc"] == "(a) five javelins or (b) any simple melee weapon"
    assert nested["from"]["equipment_category"]["index"] == "simple-weapons" and nested["desc"] == "any simple weapon"


def check_chain():
    opt = _find(_load("optionalfeatures.json", "optionalfeature"), "Pact of the Chain", "XPHB")
    assert opt["additionalSpells"][0]["innate"]["_"] == {"ritual": ["find familiar|xphb"]}
    assert "without expending a spell slot" in json.dumps(opt["entries"])


CHECKS = {
    "cleric-2024-gold": check_cleric,
    "mulhorandi-tomb-raider-gold": check_mulhorandi,
    "scribe-item-counts": check_scribe,
    "carouser-generic-gaming-set": check_carouser,
    "elemental-adept-phb-repeatable": check_elemental_adept,
    "echoing-soul-skill-count": check_echoing_soul,
    "harper-agent-thieves-cant": check_harper,
    "genie-touched-feat": check_genie,
    "scc-student-feat-college": check_scc_students,
    "srd-paladin-simple-melee-weapon": check_srd_paladin,
    "pact-of-the-chain-ritual": check_chain,
}


@pytest.mark.parametrize("key", sorted(CHECKS))
def test_raw_record_still_has_the_defect(key):
    CHECKS[key]()
