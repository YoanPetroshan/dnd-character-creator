from catalog import reference_data


def test_languages_has_sixteen_entries_with_unique_ids():
    ids = [lang["index"] for lang in reference_data.LANGUAGES]
    assert len(ids) == 16
    assert len(set(ids)) == 16
    assert "common" in ids
    assert "draconic" in ids


def test_skill_ability_has_eighteen_entries_all_valid_abilities():
    assert len(reference_data.SKILL_ABILITY) == 18
    for ability in reference_data.SKILL_ABILITY.values():
        assert ability in reference_data.ABILITIES


def test_skill_ability_known_mappings():
    assert reference_data.SKILL_ABILITY["skill-athletics"] == "STR"
    assert reference_data.SKILL_ABILITY["skill-stealth"] == "DEX"
    assert reference_data.SKILL_ABILITY["skill-arcana"] == "INT"
    assert reference_data.SKILL_ABILITY["skill-perception"] == "WIS"
    assert reference_data.SKILL_ABILITY["skill-persuasion"] == "CHA"


def test_abilities_are_the_six_srd_abilities_uppercase():
    assert reference_data.ABILITIES == ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
