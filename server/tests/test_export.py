import yaml

from export import to_yaml


def _sample_resolution():
    return {
        "sheet": {
            "name": "Тестов Герой",
            "level": 1,
            "classes": [{"id": "fighter", "name": "Fighter", "level": 1, "subclass": None}],
            "background": {"id": "acolyte", "name": "Acolyte"},
            "species": {"id": "human", "name": "Human", "subspecies": None},
            "abilities": {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9},
            "proficiencies": {"skills": ["skill-athletics"], "savingThrows": ["STR", "CON"], "languages": ["common"]},
            "equipment": {"granted": [], "chosen": [], "added": []},
            "spells": [],
            "details": None,
        },
        "derived": {
            "abilityModifiers": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
            "proficiencyBonus": 2,
            "hitPointMax": 12,
            "hitDice": "1d10",
            "armorClass": 12,
            "speed": 30,
            "savingThrows": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
            "skills": {"skill-athletics": 5},
            "passivePerception": 11,
            "spellSaveDC": None,
            "spellAttackBonus": None,
        },
        "choices": [], "problems": [], "warnings": [], "pruned": [],
    }


def test_to_yaml_produces_parseable_yaml_with_expected_fields():
    text = to_yaml(_sample_resolution())
    doc = yaml.safe_load(text)
    assert doc["name"] == "Тестов Герой"
    assert doc["level"] == 1
    assert doc["classes"] == [{"id": "fighter", "name": "Fighter", "level": 1, "subclass": None}]
    assert doc["abilities"]["STR"] == 17
    assert doc["hitPointMax"] == 12
    assert doc["armorClass"] == 12
    assert doc["proficiencies"]["skills"] == ["skill-athletics"]


def test_to_yaml_does_not_escape_unicode_names():
    text = to_yaml(_sample_resolution())
    assert "Тестов Герой" in text
    assert "\\u" not in text


def test_to_yaml_includes_no_spells_section_for_a_non_caster():
    resolution = _sample_resolution()
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spells"] == []


def test_to_yaml_includes_cantrips_and_known_spells_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spells"][0]["cantrips"][0]["name"] == "Fire Bolt"
    assert doc["spells"][0]["known"][0]["name"] == "Magic Missile"
    assert "Fire Bolt" in text
    assert "Magic Missile" in text


def test_to_yaml_includes_a_spells_entry_per_caster_for_a_multiclass_character():
    # Regression for the "secondary caster's spells vanish" bug — the YAML
    # export just passes sheet["spells"] straight through, so a
    # multi-caster list must round-trip with every class's entry intact.
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert len(doc["spells"]) == 1
    assert doc["spells"][0]["classId"] == "wizard"


def test_to_yaml_includes_spell_save_dc_and_attack_bonus_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "cleric", "name": "Cleric", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "cleric",
        "cantrips": [{"id": "sacred-flame", "name": "Sacred Flame", "level": 0}],
        "known": [],
    }]
    resolution["derived"]["spellSaveDC"] = 13
    resolution["derived"]["spellAttackBonus"] = 5
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSaveDC"] == 13
    assert doc["spellAttackBonus"] == 5


def test_to_yaml_includes_spell_save_dc_and_attack_bonus_for_a_wizard():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }]
    resolution["derived"]["spellSaveDC"] = 14
    resolution["derived"]["spellAttackBonus"] = 6
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSaveDC"] == 14
    assert doc["spellAttackBonus"] == 6


def test_to_yaml_shows_null_spell_save_dc_and_attack_bonus_for_a_non_caster():
    resolution = _sample_resolution()
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSaveDC"] is None
    assert doc["spellAttackBonus"] is None


def test_to_yaml_includes_details_when_present():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"alignment": "Lawful Neutral"}
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["details"]["alignment"] == "Lawful Neutral"
    assert "Lawful Neutral" in text


def test_to_yaml_shows_null_details_when_none_submitted():
    resolution = _sample_resolution()
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["details"] is None


def test_to_yaml_includes_equipment():
    resolution = _sample_resolution()
    resolution["sheet"]["equipment"] = {
        "granted": [{"itemId": "chain-mail", "name": "Chain Mail", "qty": 1}],
        "chosen": [],
        "added": [],
    }
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["equipment"]["granted"][0]["name"] == "Chain Mail"
    assert "Chain Mail" in text


def test_to_yaml_includes_every_class_for_a_multiclass_character():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["classes"] == [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    assert "Fighter" in text
    assert "Wizard" in text
