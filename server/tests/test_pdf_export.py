import io

from pypdf import PdfReader

from pdf_export import to_pdf


def _sample_resolution():
    resolution = {
        "sheet": {
            "name": "Тестов Герой",
            "level": 1,
            "class": {"id": "fighter", "name": "Fighter"},
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


def _extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def test_produces_valid_pdf_bytes():
    pdf_bytes = to_pdf(_sample_resolution())
    assert pdf_bytes[:4] == b"%PDF"
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_includes_name_and_header_line():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Тестов Герой" in text
    assert "Fighter" in text
    assert "Acolyte" in text


def test_includes_combat_stats_and_ability_scores():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "12" in text  # armorClass/hitPointMax
    assert "1d10" in text
    assert "STR" in text and "17" in text


def test_skill_and_language_names_are_human_readable():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Sleight of Hand" in text
    assert "skill-sleight-of-hand" not in text


def test_omits_spells_section_for_a_non_caster():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Заклинания" not in text


def test_includes_spells_for_a_caster():
    resolution = _sample_resolution()
    resolution["sheet"]["class"] = {"id": "wizard", "name": "Wizard"}
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
    }
    resolution["derived"]["spellSaveDC"] = 13
    resolution["derived"]["spellAttackBonus"] = 5
    text = _extract_text(to_pdf(resolution))
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "13" in text


def test_includes_multiline_detail_values_intact():
    resolution = _sample_resolution()
    resolution["sheet"]["details"] = {"backstory": "Първи ред.\n\nВтори абзац с още текст."}
    text = _extract_text(to_pdf(resolution))
    assert "Първи ред." in text
    assert "Втори абзац с още текст." in text


def test_omits_details_sections_when_none():
    text = _extract_text(to_pdf(_sample_resolution()))
    assert "Мирогледие" not in text


def test_handles_a_long_character_spanning_multiple_pages():
    # A character with every optional section populated should not crash
    # even if it overflows one page — fpdf2's auto page break should
    # handle it transparently.
    resolution = _sample_resolution()
    resolution["sheet"]["class"] = {"id": "wizard", "name": "Wizard"}
    resolution["sheet"]["spells"] = {
        "cantrips": [{"id": f"cantrip-{i}", "name": f"Cantrip Spell {i}", "level": 0} for i in range(10)],
        "known": [{"id": f"spell-{i}", "name": f"Known Spell {i}", "level": 1} for i in range(15)],
    }
    resolution["sheet"]["equipment"] = {
        "granted": [{"itemId": f"item-{i}", "name": f"Granted Item {i}", "qty": 1} for i in range(10)],
        "chosen": [{"itemId": f"item2-{i}", "name": f"Chosen Item {i}", "qty": 1} for i in range(10)],
        "added": [{"itemId": f"item3-{i}", "name": f"Added Item {i}", "qty": 1, "equipped": False} for i in range(10)],
    }
    resolution["sheet"]["details"] = {
        "alignment": "Chaotic Good", "faith": "—", "lifestyle": "—",
        "age": "30", "height": "180cm", "weight": "70kg", "eyes": "—", "skin": "—", "hair": "—",
        "personalityTraits": "Дълъг текст. " * 30,
        "ideals": "Още дълъг текст. " * 30,
        "bonds": "—", "flaws": "—",
        "backstory": "Много дълга предистория. " * 50,
        "organizations": "—", "allies": "—", "enemies": "—", "notes": "—",
    }
    pdf_bytes = to_pdf(resolution)
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 2  # confirms auto page break actually engaged
