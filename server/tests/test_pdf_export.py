import io

from pypdf import PdfReader

from pdf_export import to_pdf


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
            "skills": {
                "skill-acrobatics": 2, "skill-animal-handling": 1, "skill-arcana": 0, "skill-athletics": 5,
                "skill-deception": -1, "skill-history": 0, "skill-insight": 1, "skill-intimidation": -1,
                "skill-investigation": 0, "skill-medicine": 1, "skill-nature": 0, "skill-perception": 1,
                "skill-performance": -1, "skill-persuasion": -1, "skill-religion": 0,
                "skill-sleight-of-hand": 2, "skill-stealth": 2, "skill-survival": 1,
            },
            "passivePerception": 11,
            "spellSlots": {},
            "warlockSpellSlots": {},
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
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
        "spellSaveDC": 13,
        "spellAttackBonus": 5,
    }]
    text = _extract_text(to_pdf(resolution))
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "13" in text


def test_each_casters_spell_save_dc_and_attack_bonus_render_labeled_by_class():
    # Phase 3b-ii: spellSaveDC/spellAttackBonus moved off derived (a
    # single, ambiguous top-level value attributable only to the primary
    # caster) and onto each sheet["spells"][i] entry — a multiclass
    # character's casters each use their own spellcasting ability, so
    # both must render, each clearly labeled by its own class.
    resolution = _sample_resolution()
    resolution["sheet"]["level"] = 5
    resolution["sheet"]["classes"] = [
        {"id": "wizard", "name": "Wizard", "level": 3, "subclass": None},
        {"id": "cleric", "name": "Cleric", "level": 2, "subclass": None},
    ]
    resolution["sheet"]["spells"] = [
        {"classId": "wizard", "cantrips": [], "known": [], "spellSaveDC": 14, "spellAttackBonus": 6},
        {"classId": "cleric", "cantrips": [], "known": [], "spellSaveDC": 13, "spellAttackBonus": 5},
    ]
    text = _extract_text(to_pdf(resolution))
    lines = text.splitlines()
    wizard_line = next(l for l in lines if "Wizard" in l and "14" in l)
    cleric_line = next(l for l in lines if "Cleric" in l and "13" in l)
    assert wizard_line != cleric_line
    assert "6" in wizard_line
    assert "5" in cleric_line


def test_spell_slots_render_as_a_compact_line():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 3, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard", "cantrips": [], "known": [],
        "spellSaveDC": 14, "spellAttackBonus": 6,
    }]
    resolution["derived"]["spellSlots"] = {"1": 4, "2": 3}
    text = _extract_text(to_pdf(resolution))
    slot_line = next(l for l in text.splitlines() if "Spell Slots" in l)
    assert "4" in slot_line
    assert "3" in slot_line


def test_warlock_spell_slots_render_separately_from_shared_pool():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "wizard", "name": "Wizard", "level": 3, "subclass": None},
        {"id": "warlock", "name": "Warlock", "level": 2, "subclass": None},
    ]
    resolution["sheet"]["spells"] = [
        {"classId": "wizard", "cantrips": [], "known": [], "spellSaveDC": 14, "spellAttackBonus": 6},
        {"classId": "warlock", "cantrips": [], "known": [], "spellSaveDC": 13, "spellAttackBonus": 5},
    ]
    resolution["derived"]["spellSlots"] = {"1": 4, "2": 3}
    resolution["derived"]["warlockSpellSlots"] = {"1": 2}
    text = _extract_text(to_pdf(resolution))
    lines = text.splitlines()
    shared_line = next(l for l in lines if "Spell Slots" in l and "Pact Magic" not in l)
    pact_line = next(l for l in lines if "Pact Magic Slots" in l)
    assert shared_line != pact_line


def test_no_spell_slots_line_when_a_caster_has_no_slots_yet():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [], "spellSaveDC": 13, "spellAttackBonus": 5,
    }]
    text = _extract_text(to_pdf(resolution))
    assert "Spell Slots" not in text
    assert "Pact Magic" not in text


def test_end_to_end_for_a_real_multiclass_caster():
    # Integration test through the REAL resolve() (not a hand-rolled
    # fixture) — closes the gap where the export test suite could stay
    # green over broken PDF export despite no test ever exercising a
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
    text = _extract_text(to_pdf(resolution))
    lines = text.splitlines()
    wizard_line = next(l for l in lines if "Wizard" in l and "14" in l)
    cleric_line = next(l for l in lines if "Cleric" in l and "13" in l)
    assert wizard_line != cleric_line
    slot_line = next(l for l in lines if "Spell Slots" in l)
    assert "4" in slot_line and "3" in slot_line and "2" in slot_line


def test_includes_spells_for_every_caster_in_a_multiclass_character():
    # Regression for the "secondary caster's spells vanish" bug: a
    # multi-entry sheet["spells"] list must render every class's spells.
    resolution = _sample_resolution()
    resolution["sheet"]["level"] = 5
    resolution["sheet"]["classes"] = [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    resolution["sheet"]["spells"] = [
        {
            "classId": "fighter",
            "cantrips": [],
            "known": [{"id": "hunters-mark", "name": "Hunter's Mark", "level": 1}],
            "spellSaveDC": None,
            "spellAttackBonus": None,
        },
        {
            "classId": "wizard",
            "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
            "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
            "spellSaveDC": 13,
            "spellAttackBonus": 5,
        },
    ]
    text = _extract_text(to_pdf(resolution))
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "Hunter" in text


def test_includes_subclass_name_when_present():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [
        {"id": "cleric", "name": "Cleric", "level": 1, "subclass": {"id": "life", "name": "Life"}}
    ]
    text = _extract_text(to_pdf(resolution))
    assert "Life" in text
    assert "Cleric" in text


def test_includes_every_class_for_a_multiclass_character():
    resolution = _sample_resolution()
    resolution["sheet"]["level"] = 5
    resolution["sheet"]["classes"] = [
        {"id": "fighter", "name": "Fighter", "level": 3, "subclass": None},
        {"id": "wizard", "name": "Wizard", "level": 2, "subclass": None},
    ]
    text = _extract_text(to_pdf(resolution))
    assert "Fighter 3" in text
    assert "Wizard 2" in text


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
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": f"cantrip-{i}", "name": f"Cantrip Spell {i}", "level": 0} for i in range(10)],
        "known": [{"id": f"spell-{i}", "name": f"Known Spell {i}", "level": 1} for i in range(15)],
        "spellSaveDC": 15,
        "spellAttackBonus": 7,
    }]
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


def test_detail_and_equipment_sections_match_markdown_export():
    # pdf_export.py and markdown_export.py are two renderings of one
    # content contract (same fields, same order — see this plan's Global
    # Constraints), duplicated rather than shared because PDF's imperative
    # layout API can't share a string-building function with Markdown's.
    # Nothing else enforces that the two stay in sync — a future field
    # added to one and not the other would pass every existing test in
    # both files (they use deliberately separate fixtures) and only show
    # up as a silently incomplete PDF or Markdown export. This guard
    # exists purely to make that drift loud.
    import markdown_export

    import pdf_export

    assert pdf_export._DETAIL_SECTIONS == markdown_export._DETAIL_SECTIONS
    assert pdf_export._EQUIPMENT_SECTIONS == markdown_export._EQUIPMENT_SECTIONS
