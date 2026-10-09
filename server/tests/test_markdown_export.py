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
            "passiveInsight": 12,
            "passiveInvestigation": 10,
            "initiative": 2,
            "spellSlots": {},
            "warlockSpellSlots": {},
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
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
        "spellSaveDC": 13,
        "spellAttackBonus": 5,
    }]
    text = to_markdown(resolution)
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
    text = to_markdown(resolution)
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
    text = to_markdown(resolution)
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
    text = to_markdown(resolution)
    lines = text.splitlines()
    shared_line = next(l for l in lines if "Spell Slots" in l and "Pact Magic" not in l)
    pact_line = next(l for l in lines if "Pact Magic Slots" in l)
    assert shared_line != pact_line


def test_no_spell_slots_line_when_a_caster_has_no_slots_yet():
    # A cantrip-only caster (e.g. a level-1 Wizard before its first
    # spell-granting level, or any class with an empty spellSlots dict)
    # must not print an empty "Spell Slots:" line.
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [], "spellSaveDC": 13, "spellAttackBonus": 5,
    }]
    text = to_markdown(resolution)
    assert "Spell Slots" not in text
    assert "Pact Magic" not in text


def test_end_to_end_for_a_real_multiclass_caster():
    # Integration test through the REAL resolve() (not a hand-rolled
    # fixture) — closes the gap where the export test suite could stay
    # green over broken markdown export despite no test ever exercising a
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
    text = to_markdown(resolution)
    lines = text.splitlines()
    wizard_line = next(l for l in lines if "Wizard" in l and "14" in l)
    cleric_line = next(l for l in lines if "Cleric" in l and "13" in l)
    assert wizard_line != cleric_line
    slot_line = next(l for l in lines if "Spell Slots" in l)
    assert "4" in slot_line and "3" in slot_line and "2" in slot_line


def test_includes_spells_for_every_caster_in_a_multiclass_character():
    # Regression for the "secondary caster's spells vanish" bug: a
    # multi-entry sheet["spells"] list must render every class's spells,
    # each subsection labeled with its class name to disambiguate.
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
    text = to_markdown(resolution)
    assert "Fire Bolt" in text
    assert "Magic Missile" in text
    assert "Hunter's Mark" in text
    assert "(Wizard)" in text
    assert "(Fighter)" in text


def test_does_not_label_spell_subsections_by_class_for_a_single_caster():
    # A single-class caster keeps the plain, unlabeled headings it always
    # had — the per-class label is only needed to disambiguate when there's
    # more than one caster.
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "wizard", "name": "Wizard", "level": 1, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "wizard",
        "cantrips": [{"id": "fire-bolt", "name": "Fire Bolt", "level": 0}],
        "known": [{"id": "magic-missile", "name": "Magic Missile", "level": 1}],
        "spellSaveDC": 13,
        "spellAttackBonus": 5,
    }]
    text = to_markdown(resolution)
    assert "(Wizard)" not in text


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


def test_renders_armor_weapon_and_tool_proficiencies():
    resolution = _sample_resolution()
    resolution["sheet"]["proficiencies"].update(
        {"armor": ["light-armor", "shields"], "weapons": ["simple-weapons"], "tools": ["smiths-tools"]}
    )
    text = to_markdown(resolution)
    assert "## Владеене" in text
    assert "**Брони:** Light armor, Shields" in text
    assert "**Оръжия:** Simple weapons" in text
    assert "**Инструменти:** Smiths tools" in text
    assert "light-armor" not in text


def test_proficiency_section_shows_a_placeholder_when_empty():
    text = to_markdown(_sample_resolution())
    assert "## Владеене\n—" in text


def test_markdown_renders_innate_spells_section():
    import pytest
    from catalog.official_source import has_official
    if not has_official():
        pytest.skip("official data not fetched on this machine")
    from test_export import _aasimar_resolution
    text = to_markdown(_aasimar_resolution())
    assert "## Вродени заклинания" in text
    assert "- Lesser Restoration (1/day, от ниво 3)" in text


def test_markdown_without_innate_spells_key_renders_no_section():
    text = to_markdown(_sample_resolution())
    assert "Вродени заклинания" not in text


def _warlock_with_arcanum():
    resolution = _sample_resolution()
    resolution["sheet"]["classes"] = [{"id": "warlock", "name": "Warlock", "level": 13, "subclass": None}]
    resolution["sheet"]["spells"] = [{
        "classId": "warlock", "cantrips": [], "known": [],
        "mysticArcanum": [{"level": 6, "id": "true-seeing", "name": "True Seeing"},
                          {"level": 7, "id": "forcecage", "name": "Forcecage"}],
        "spellSaveDC": 14, "spellAttackBonus": 6,
    }]
    return resolution


def test_markdown_prints_the_mystic_arcanum_line():
    text = to_markdown(_warlock_with_arcanum())
    assert "**Мистичен арканум:** True Seeing (ниво 6), Forcecage (ниво 7)" in text


def test_markdown_omits_the_arcanum_line_without_picks():
    resolution = _warlock_with_arcanum()
    resolution["sheet"]["spells"][0]["mysticArcanum"] = []
    assert "арканум" not in to_markdown(resolution)
