import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _fighter_acolyte_human_draft(**overrides):
    draft = {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    draft.update(overrides)
    return draft


def _empty_draft():
    return {
        "name": "", "sources": ["srd"], "classes": [],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "standard", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }


def test_empty_draft_resolves_without_error_or_problems(catalog):
    resolution = resolve(_empty_draft(), catalog)
    assert resolution["problems"] == []
    assert resolution["choices"] == []
    assert resolution["sheet"]["name"] == ""
    assert resolution["sheet"]["level"] == 0
    assert resolution["sheet"]["class"] is None


def test_fighter_acolyte_human_produces_expected_sheet_and_derived(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["problems"] == []
    sheet = resolution["sheet"]
    assert sheet["name"] == "Torvin Bracewell"
    assert sheet["level"] == 1
    assert sheet["class"] == {"id": "fighter", "name": "Fighter"}
    assert sheet["background"] == {"id": "acolyte", "name": "Acolyte"}
    assert sheet["species"]["id"] == "human"
    assert sheet["species"]["subspecies"] is None
    # Human's +1 to every ability (chargen/data/srd/5e-SRD-Races.json)
    assert sheet["abilities"] == {"STR": 17, "DEX": 15, "CON": 15, "INT": 11, "WIS": 13, "CHA": 9}

    derived = resolution["derived"]
    assert derived["abilityModifiers"] == {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1}
    assert derived["proficiencyBonus"] == 2
    assert derived["hitPointMax"] == 12  # Fighter hit_die 10 + CON mod 2
    assert derived["hitDice"] == "1d10"
    assert derived["armorClass"] == 12  # 10 + DEX mod 2, unarmored
    assert derived["speed"] == 30
    # Fighter is proficient in STR and CON saves
    assert derived["savingThrows"]["STR"] == 5
    assert derived["savingThrows"]["CON"] == 4
    assert derived["savingThrows"]["DEX"] == 2  # not proficient
    assert derived["passivePerception"] == 10 + derived["skills"]["skill-perception"]


def test_fighter_class_skill_choice_disables_options_already_granted_by_background(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    skill_choice = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Skill Proficiencies"
    )
    insight = next(o for o in skill_choice["options"] if o["id"] == "skill-insight")
    assert insight.get("disabled") is True
    assert "Acolyte" in insight["disabledReason"]
    athletics = next(o for o in skill_choice["options"] if o["id"] == "skill-athletics")
    assert not athletics.get("disabled")


def test_fighting_style_choice_is_present_and_pending_by_default(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    fighting_style = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Fighting Style"
    )
    assert fighting_style["count"] == 1
    assert fighting_style["selected"] == []
    assert fighting_style["status"] == "pending"
    # The subfeature_options envelope itself carries no description — this
    # must be sourced from the parent feature's own 'desc', or it silently
    # renders blank in the UI.
    assert "specialty" in fighting_style["description"]
    option_ids = {o["id"] for o in fighting_style["options"]}
    assert "fighter-fighting-style-archery" in option_ids


def test_selecting_a_choice_marks_it_resolved(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"]},
        }],
    )
    resolution = resolve(draft, catalog)
    fighting_style = next(
        c for c in resolution["choices"]
        if c["source"]["kind"] == "class" and c["label"] == "Fighting Style"
    )
    assert fighting_style["selected"] == ["fighter-fighting-style-archery"]
    assert fighting_style["status"] == "resolved"


def test_background_language_choice_offers_sixteen_languages(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    languages = next(c for c in resolution["choices"] if c["source"]["kind"] == "background")
    assert languages["label"] == "Languages"
    assert languages["count"] == 2
    assert len(languages["options"]) == 16
    assert languages["description"] == "Choose 2 languages of your choice."


def test_species_trait_choice_for_dragonborn_ancestry(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dragonborn", "choices": {}})
    resolution = resolve(draft, catalog)
    ancestry = next(c for c in resolution["choices"] if c["source"]["kind"] == "species")
    assert ancestry["label"] == "Draconic Ancestry"
    assert ancestry["count"] == 1
    # subtrait_options itself carries no description — must come from the
    # parent trait's own 'desc'.
    assert "draconic ancestry" in ancestry["description"].lower()
    option_ids = {o["id"] for o in ancestry["options"]}
    assert "draconic-ancestry-black" in option_ids


def test_subrace_ability_bonus_stacks_with_race(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "subspeciesId": "hill-dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    # Dwarf +2 CON, Hill Dwarf subrace +1 WIS (chargen/data/srd/5e-SRD-Races.json,
    # 5e-SRD-Subraces.json)
    assert resolution["sheet"]["abilities"]["CON"] == 16  # base 14 + 2
    assert resolution["sheet"]["abilities"]["WIS"] == 13  # base 12 + 1
    assert resolution["sheet"]["species"]["subspecies"] == {"id": "hill-dwarf", "name": "Hill Dwarf"}


def test_multiclass_draft_produces_a_problem_and_uses_only_the_first_class(catalog):
    draft = _fighter_acolyte_human_draft(classes=[
        {"classId": "fighter", "level": 1, "choices": {}},
        {"classId": "wizard", "level": 1, "choices": {}},
    ])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])
    assert resolution["sheet"]["class"]["id"] == "fighter"


def test_level_other_than_one_produces_a_problem_but_still_resolves(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "level-unsupported" for p in resolution["problems"])
    assert resolution["sheet"]["level"] == 1
    assert resolution["derived"]["proficiencyBonus"] == 2


def test_unknown_class_id_produces_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "not-a-class", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "unknown-class" for p in resolution["problems"])
    assert resolution["sheet"]["class"] is None


def test_ability_score_out_of_range_produces_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(abilities={
        "method": "manual",
        "base": {"STR": 99, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
    })
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "ability-out-of-range-STR" for p in resolution["problems"])


def test_mismatched_subspecies_is_a_problem_and_subspecies_is_ignored(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "human", "subspeciesId": "hill-dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "subspecies-mismatch" for p in resolution["problems"])
    assert resolution["sheet"]["species"]["subspecies"] is None


def test_bard_instrument_choice_does_not_pollute_skill_proficiencies(catalog):
    draft = {
        "name": "Test Bard", "sources": ["srd"],
        "classes": [{
            "classId": "bard", "level": 1,
            "choices": {
                "class:bard:1:prof-choice-0": ["skill-acrobatics", "skill-arcana", "skill-athletics"],
                "class:bard:1:prof-choice-1": ["bagpipes", "drum", "dulcimer"],
            },
        }],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }
    resolution = resolve(draft, catalog)
    skills = resolution["sheet"]["proficiencies"]["skills"]
    assert all(s.startswith("skill-") for s in skills)
    assert "bagpipes" not in skills
    tool_choice = next(c for c in resolution["choices"] if c["label"] == "Tool Proficiencies")
    assert tool_choice["selected"] == ["bagpipes", "drum", "dulcimer"]
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    assert all(o["id"].startswith("skill-") for o in skill_choice["options"])


def test_non_numeric_ability_score_becomes_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(abilities={
        "method": "manual",
        "base": {"STR": "not-a-number", "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
    })
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "ability-invalid-STR" for p in resolution["problems"])
    assert resolution["sheet"]["abilities"]["STR"] == 11  # fallback 10 + human's +1


def test_null_ability_score_becomes_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(abilities={
        "method": "manual",
        "base": {"STR": None, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
    })
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "ability-invalid-STR" for p in resolution["problems"])


def test_over_selecting_a_choice_truncates_and_records_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:prof-choice-0": [
                "skill-acrobatics", "skill-athletics", "skill-history", "skill-intimidation", "skill-perception",
            ]},
        }],
    )
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    assert len(skill_choice["selected"]) == 2
    assert skill_choice["status"] == "resolved"
    assert any(p["id"].startswith("over-selected-") for p in resolution["problems"])
    # Only the truncated 2 (plus Acolyte's own unconditional skill-insight/
    # skill-religion grants) may land in the sheet — the 3 over-submitted
    # ids (history, intimidation, perception) must never leak through.
    assert resolution["sheet"]["proficiencies"]["skills"] == [
        "skill-acrobatics", "skill-athletics", "skill-insight", "skill-religion",
    ]


def test_selecting_a_disabled_option_does_not_count_toward_the_choice(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:prof-choice-0": ["skill-insight", "skill-athletics"]},
        }],
    )
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    # skill-insight is disabled (Acolyte already grants it) — must not be selectable
    assert "skill-insight" not in skill_choice["selected"]
    assert skill_choice["selected"] == ["skill-athletics"]
    assert skill_choice["status"] == "pending"  # only 1 of 2 actually landed


def test_monk_second_proficiency_choice_does_not_appear_as_a_broken_empty_choice(catalog):
    draft = {
        "name": "Test Monk", "sources": ["srd"],
        "classes": [{"classId": "monk", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }
    resolution = resolve(draft, catalog)
    class_choices = [c for c in resolution["choices"] if c["source"]["kind"] == "class"]
    labels = [c["label"] for c in class_choices]
    assert labels.count("Skill Proficiencies") == 1  # not duplicated
    assert all(len(c["options"]) > 0 for c in class_choices)  # no empty/unsatisfiable choice


def test_human_bonus_language_choice_is_offered(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    bonus_lang = next(c for c in resolution["choices"] if c["label"] == "Bonus Language")
    assert bonus_lang["source"]["kind"] == "species"
    assert bonus_lang["count"] == 1
    assert len(bonus_lang["options"]) > 0


def test_half_elf_ability_bonus_choice_is_flagged_as_unsupported(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "half-elf", "choices": {}})
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "species-ability-choice-unsupported" for p in resolution["problems"])


def test_non_list_classes_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(classes={"classId": "fighter"})
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-classes" for p in resolution["problems"])


def test_string_classes_entries_are_ignored_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(classes=["fighter"])
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-class-entry" for p in resolution["problems"])


def test_string_background_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(background="acolyte")
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-background" for p in resolution["problems"])


def test_string_species_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(species="human")
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-species" for p in resolution["problems"])


def test_null_choice_selection_value_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 1, "choices": {"class:fighter:1:prof-choice-0": None}}],
    )
    resolution = resolve(draft, catalog)  # must not raise
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    assert skill_choice["selected"] == []


def test_fighter_equipment_choices_are_offered(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    equipment_choices = [c for c in resolution["choices"] if c["source"]["kind"] == "equipment"]
    labels = {c["label"] for c in equipment_choices}
    # 3 of Fighter's 4 starting_equipment_options entries are resolvable in
    # this phase (see Task 1) — the "martial weapon and a shield or two
    # martial weapons" one is not, and must not appear at all.
    assert len(equipment_choices) == 3
    armor_choice = next(c for c in equipment_choices if any(o["id"] == "chain-mail" for o in c["options"]))
    ids = {o["id"] for o in armor_choice["options"]}
    assert ids == {"chain-mail", "leather-armor+longbow+arrow"}


def test_selecting_chain_mail_computes_heavy_armor_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:prof-choice-0": ["skill-athletics", "skill-history"]},
        }],
        equipment={
            "choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]},
            "added": [], "skipped": False,
        },
    )
    resolution = resolve(draft, catalog)
    # Fighter/Human draft has DEX 14 -> +2 human bonus... reuse the fixture's
    # own DEX (14) + Human's +1 = 15 -> +2 mod; chain mail ignores DEX.
    assert resolution["derived"]["armorClass"] == 16  # chain mail base, no DEX


def test_selecting_leather_bundle_computes_light_armor_ac_with_dex(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={
            "choices": {"class:fighter:1:equipment-choice-0": ["leather-armor+longbow+arrow"]},
            "added": [], "skipped": False,
        },
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 11 + dex_mod


def test_sheet_lists_acolytes_granted_fixed_equipment(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    granted = resolution["sheet"]["equipment"]["granted"]
    granted_ids = {g["itemId"] for g in granted}
    assert "clothes-common" in granted_ids
    assert "pouch" in granted_ids


def test_draft_added_equipped_shield_adds_to_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "shield", "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 10 + dex_mod + 2


def test_draft_added_unequipped_item_does_not_affect_ac(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "shield", "qty": 1, "equipped": False}], "skipped": False},
    )
    resolution = resolve(draft, catalog)
    dex_mod = resolution["derived"]["abilityModifiers"]["DEX"]
    assert resolution["derived"]["armorClass"] == 10 + dex_mod
    added = resolution["sheet"]["equipment"]["added"]
    assert any(a["itemId"] == "shield" and a["equipped"] is False for a in added)


def test_unknown_added_item_id_is_dropped_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": "not-a-real-item", "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_missing_equipment_field_entirely_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft()
    del draft["equipment"]
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_non_list_added_equipment_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(equipment={"choices": {}, "added": "not-a-list", "skipped": False})
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-equipment-added" for p in resolution["problems"])


def test_non_dict_equipment_choices_is_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(equipment={"choices": "not-a-dict", "added": [], "skipped": False})
    resolution = resolve(draft, catalog)  # must not raise
    assert any(p["id"] == "malformed-equipment-choices" for p in resolution["problems"])


def test_non_dict_equipment_field_itself_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(equipment="not-a-dict")
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []
