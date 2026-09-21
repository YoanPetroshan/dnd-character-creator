from markdown_export import to_markdown


def _sample_resolution():
    resolution = {
        "sheet": {
            "name": "Тестов Герой",
            "level": 1,
            "classes": [{"id": "fighter", "name": "Fighter", "level": 1, "subclass": None}],
            "background": {"id": "acolyte", "name": "Acolyte"},
            "species": {"id": "human", "name": "Human", "subspecies": None},
            "abilities": {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9},
            "proficiencies": {"skills": ["skill-athletics"], "savingThrows": ["STR", "CON"], "languages": ["common"]},
            "equipment": {"granted": [], "chosen": [], "added": []},
            "spells": None,
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
            "skills": {
                "skill-acrobatics": 2, "skill-animal-handling": 1, "skill-arcana": 0, "skill-athletics": 5,
                "skill-deception": -1, "skill-history": 0, "skill-insight": 1, "skill-intimidation": -1,
                "skill-investigation": 0, "skill-medicine": 1, "skill-nature": 0, "skill-perception": 1,
                "skill-performance": -1, "skill-persuasion": -1, "skill-religion": 0,
                "skill-sleight-of-hand": 2, "skill-stealth": 2, "skill-survival": 1,
            },
            "passivePerception": 11,
            "spellSaveDC": None,
            "spellAttackBonus": None,
        },
        "choices": [], "problems": [], "warnings": [], "pruned": [],
    }
    return resolution


def test_includes_name_and_header_line():
    text = to_markdown(_sample_resolution())
    assert text.startswith("# Тестов Герой")
    assert "Ниво 1 Fighter" in text
    assert "Acolyte" in text
    assert "Human" in text


def test_includes_combat_stats():
    text = to_markdown(_sample_resolution())
    assert "12" in text  # armorClass and hitPointMax are both 12 in the fixture — presence check
    assert "1d10" in text
    assert "30" in text  # speed
    assert "+2" in text  # DEX modifier used as initiative


def test_includes_ability_scores():
    text = to_markdown(_sample_resolution())
    assert "STR" in text and "17" in text and "+3" in text


def test_proficient_save_is_marked_differently_from_non_proficient():
    text = to_markdown(_sample_resolution())
    # STR and CON are proficient saves in the fixture; DEX is not.
    # Whatever exact marker the implementation uses, a proficient and a
    # non-proficient save line must render visibly differently.
    lines = [l for l in text.splitlines() if "**STR**" in l or "**DEX**" in l]
    str_line = next(l for l in lines if "**STR**" in l)
    dex_line = next(l for l in lines if "**DEX**" in l)
    assert str_line != dex_line.replace("DEX", "STR")  # not just the ability letter differs


def test_skill_names_are_human_readable_not_raw_ids():
    text = to_markdown(_sample_resolution())
    assert "Sleight of Hand" in text
    assert "skill-sleight-of-hand" not in text
    assert "Athletics" in text


def test_includes_languages_or_a_placeholder():
    text = to_markdown(_sample_resolution())
    assert "common" in text.lower() or "Common" in text


def test_language_names_are_human_readable_not_raw_ids():
    resolution = _sample_resolution()
    resolution["sheet"]["proficiencies"]["languages"] = ["deep-speech"]
    text = to_markdown(resolution)
    assert "Deep Speech" in text
    assert "deep-speech" not in text


def test_omits_spells_section_for_a_non_caster():
    text = to_markdown(_sample_resolution())
    assert "Заклинания" not in text


def test_includes_spells_section_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }
    resolution["derived"]["spellSaveDC"] = 13
    resolution["derived"]["spellAttackBonus"] = 5
    text = to_markdown(resolution)
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "13" in text


def test_omits_equipment_subsections_that_are_empty():
    text = to_markdown(_sample_resolution())  # all three equipment lists are empty in the fixture
    assert "Получена екипировка" not in text
    assert "Избрана екипировка" not in text
    assert "Инвентар" not in text


def test_includes_populated_equipment_subsections():
    resolution = _sample_resolution()
    resolution["sheet"]["equipment"] = {
        "granted": [{"itemId": "chain-mail", "name": "Chain Mail", "qty": 1}],
        "chosen": [{"itemId": "handaxe", "name": "Handaxe", "qty": 1}],
        "added": [{"itemId": "torch", "name": "Torch", "qty": 2, "equipped": False}],
    }
    text = to_markdown(resolution)
    assert "Chain Mail" in text
    assert "Handaxe" in text
    assert "Torch" in text
    assert "x2" in text


def test_omits_details_sections_when_none():
    text = to_markdown(_sample_resolution())
    assert "Мирогледие" not in text
    assert "Предистория" not in text


def test_includes_only_submitted_details_fields():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"alignment": "Chaotic Good", "backstory": "Роден в планините."}
    text = to_markdown(resolution)
    assert "Chaotic Good" in text
    assert "Роден в планините." in text
    assert "Вяра" not in text  # faith wasn't submitted, its label shouldn't appear


def test_includes_subclass_name_when_present():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "cleric", "name": "Cleric", "level": 1, "subclass": {"id": "life", "name": "Life"}}
    ]
    text = to_markdown(resolution)
    assert "Life" in text
    assert "Ниво 1 Cleric (Life)" in text


def test_includes_every_class_for_a_multiclass_character():
    resolution = _sample_resolution()
    resolution["sheet"]["level"] = 5
    resolution["sheet"]["classes"] = [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    text = to_markdown(resolution)
    assert "Fighter 3" in text
    assert "Wizard 2" in text
    assert "Ниво 5 Fighter 3 / Wizard 2" in text


def test_multiline_detail_value_stays_intact_and_does_not_break_list_structure():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"backstory": "Първи ред.\n\nВтори абзац."}
    text = to_markdown(resolution)
    assert "Първи ред." in text and "Втори абзац." in text
    # The value must not be embedded as a bullet's own line (a "\n" inside a
    # bullet breaks out of the Markdown list structure), so the backstory
    # label should not be on the same line as the value's first line.
    assert "- **Предистория:** Първи ред." not in text
