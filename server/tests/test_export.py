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
            "spellSlots": {},
            "warlockSpellSlots": {},
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
        "spellSaveDC": 13,
        "spellAttackBonus": 5,
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
        "spellSaveDC": 12,
        "spellAttackBonus": 4,
    }]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert len(doc["spells"]) == 1
    assert doc["spells"][0]["classId"] == "wizard"


def test_to_yaml_includes_spell_save_dc_and_attack_bonus_for_a_caster():
    # As of Phase 3b-ii, spellSaveDC/spellAttackBonus live on each
    # sheet["spells"][i] entry (not as a top-level `derived` scalar) —
    # each caster uses its own spellcasting ability.
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "cleric", "name": "Cleric", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "cleric",
        "cantrips": [{"id": "sacred-flame", "name": "Sacred Flame", "level": 0}],
        "known": [],
        "spellSaveDC": 13,
        "spellAttackBonus": 5,
    }]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spells"][0]["spellSaveDC"] == 13
    assert doc["spells"][0]["spellAttackBonus"] == 5


def test_to_yaml_includes_each_casters_own_spell_save_dc_and_attack_bonus_for_a_multiclass_character():
    # A multiclass character's casters each use their own spellcasting
    # ability, so a Wizard/Cleric multiclass must round-trip TWO distinct
    # DC/attack-bonus pairs, one per caster, not a single shared value.
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "wizard", "name": "Wizard", "level": 3, "subclass": None},
        {"id": "cleric", "name": "Cleric", "level": 2, "subclass": None},
    ]
    resolution["sheet"]["spells"] = [
        {"classId": "wizard", "cantrips": [], "known": [], "spellSaveDC": 14, "spellAttackBonus": 6},
        {"classId": "cleric", "cantrips": [], "known": [], "spellSaveDC": 13, "spellAttackBonus": 5},
    ]
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spells"][0]["classId"] == "wizard"
    assert doc["spells"][0]["spellSaveDC"] == 14
    assert doc["spells"][0]["spellAttackBonus"] == 6
    assert doc["spells"][1]["classId"] == "cleric"
    assert doc["spells"][1]["spellSaveDC"] == 13
    assert doc["spells"][1]["spellAttackBonus"] == 5


def test_to_yaml_includes_spell_slots_and_warlock_spell_slots():
    resolution = _sample_resolution()
    resolution["derived"]["spellSlots"] = {"1": 4, "2": 3}
    resolution["derived"]["warlockSpellSlots"] = {"3": 2}
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSlots"] == {"1": 4, "2": 3}
    assert doc["warlockSpellSlots"] == {"3": 2}


def test_to_yaml_shows_empty_spell_slots_for_a_non_caster():
    resolution = _sample_resolution()
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSlots"] == {}
    assert doc["warlockSpellSlots"] == {}


def test_to_yaml_end_to_end_for_a_real_multiclass_caster():
    # Integration test through the REAL resolve() (not a hand-rolled
    # fixture) — closes the gap where the export test suite could stay
    # green over a broken export.py despite no test ever exercising a
    # real spellcasting character's Resolution shape.
    from catalog.loader import load
    from engine.resolve import resolve

    catalog = load()
    draft = {
        "name": "Multi Test", "sources": ["srd"],
        "classes": [
            {"classId": "wizard", "level": 3, "choices": {}},
            {"classId": "cleric", "level": 2, "choices": {}},
        ],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 14, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": True},
        "details": {},
    }
    resolution = resolve(draft, catalog)
    text = to_yaml(resolution)
    doc = yaml.safe_load(text)
    assert doc["spellSlots"] == {"1": 4, "2": 3, "3": 2}
    assert doc["warlockSpellSlots"] == {}
    wizard_entry = next(s for s in doc["spells"] if s["classId"] == "wizard")
    cleric_entry = next(s for s in doc["spells"] if s["classId"] == "cleric")
    assert wizard_entry["spellSaveDC"] == 14
    assert wizard_entry["spellAttackBonus"] == 6
    assert cleric_entry["spellSaveDC"] == 13
    assert cleric_entry["spellAttackBonus"] == 5


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
