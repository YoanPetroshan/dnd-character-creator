import pytest

from catalog.loader import load
from engine.resolve import _DETAIL_FIELDS, resolve


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
    assert sheet["class"] == {"id": "fighter", "name": "Fighter", "subclass": None}
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


def test_species_trait_proficiencies_are_applied(catalog):
    # Elf's Keen Senses trait grants Perception proficiency automatically,
    # with no choice involved.
    draft = _fighter_acolyte_human_draft(species={"id": "elf", "choices": {}})
    resolution = resolve(draft, catalog)
    assert "skill-perception" in resolution["sheet"]["proficiencies"]["skills"]


def test_a_race_with_no_automatic_skill_grant_gets_none(catalog):
    # Human has no trait granting an automatic skill proficiency — confirm
    # this fix doesn't spuriously grant one. With the fixture's default
    # empty choices, Fighter's own skill-proficiency choice is left
    # unresolved (pending) and Acolyte's own two FIXED skills (Insight,
    # Religion — background.starting_proficiencies, not a choice) are the
    # only ones that resolve — confirmed empirically while writing this
    # plan. Nothing should be attributable to Human.
    draft = _fighter_acolyte_human_draft()  # already uses Human
    resolution = resolve(draft, catalog)
    assert set(resolution["sheet"]["proficiencies"]["skills"]) == {"skill-insight", "skill-religion"}


def test_multiclass_draft_produces_a_problem_and_uses_only_the_first_class(catalog):
    draft = _fighter_acolyte_human_draft(classes=[
        {"classId": "fighter", "level": 1, "choices": {}},
        {"classId": "wizard", "level": 1, "choices": {}},
    ])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])
    assert resolution["sheet"]["class"]["id"] == "fighter"


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


def test_half_elf_ability_bonus_choice_no_longer_blocks_export(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "half-elf", "choices": {"species:half-elf:ability-bonus": ["str", "dex"]}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "species-ability-choice-unsupported" for p in resolution["problems"])


def test_half_elf_selected_ability_bonuses_are_applied(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "half-elf", "choices": {"species:half-elf:ability-bonus": ["str", "dex"]}},
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    scores = resolution["sheet"]["abilities"]
    assert scores["STR"] == 15  # 14 base + 1 from the ability-bonus choice
    assert scores["DEX"] == 13  # 12 base + 1
    assert scores["CHA"] == 10  # 8 base + 2 fixed Half-Elf bonus (unrelated to this choice, unaffected)


def test_half_elf_duplicate_ability_selection_does_not_double_apply(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "half-elf", "choices": {"species:half-elf:ability-bonus": ["str", "str"]}},
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    scores = resolution["sheet"]["abilities"]
    assert scores["STR"] == 15  # 14 base + 1, not +2 — duplicate selection must not double the bonus
    choice = next(c for c in resolution["choices"] if c["id"] == "species:half-elf:ability-bonus")
    assert choice["selected"] == ["str"]  # deduplicated, not ["str", "str"]


def test_half_elf_choice_is_pending_when_unresolved(catalog):
    draft = _fighter_acolyte_human_draft(species={"id": "half-elf", "choices": {}})
    resolution = resolve(draft, catalog)
    choice = next(c for c in resolution["choices"] if c["id"] == "species:half-elf:ability-bonus")
    assert choice["status"] == "pending"
    assert choice["count"] == 2


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


def test_paladin_granted_chain_mail_is_counted_toward_ac(catalog):
    draft = {
        "name": "Test Paladin", "sources": ["srd"],
        "classes": [{"classId": "paladin", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }
    resolution = resolve(draft, catalog)
    granted_ids = {g["itemId"] for g in resolution["sheet"]["equipment"]["granted"]}
    assert "chain-mail" in granted_ids
    assert resolution["derived"]["armorClass"] == 16  # chain mail base, heavy armor ignores DEX


def test_unhashable_added_item_id_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": ["shield"], "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_dict_added_item_id_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {}, "added": [{"itemId": {"a": 1}, "qty": 1, "equipped": True}], "skipped": False},
    )
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["equipment"]["added"] == []


def test_truncated_equipment_choice_notes_the_limitation_in_its_description(catalog):
    draft = {
        "name": "Test Cleric", "sources": ["srd"],
        "classes": [{"classId": "cleric", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }
    resolution = resolve(draft, catalog)
    equipment_choices = [c for c in resolution["choices"] if c["source"]["kind"] == "equipment"]
    # Find the one with only 1 real option resolved (the "a light crossbow
    # and 20 bolts OR any simple weapon" envelope, per the final review's
    # own finding) — verify it live first rather than assuming which index.
    truncated = [c for c in equipment_choices if len(c["options"]) == 1]
    assert truncated, "expected at least one truncated equipment choice for Cleric"
    assert "not available yet" in truncated[0]["description"] or "aren't available yet" in truncated[0]["description"]


def test_chosen_equipment_appears_on_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        equipment={"choices": {"class:fighter:1:equipment-choice-0": ["chain-mail"]}, "added": [], "skipped": False},
    )
    resolution = resolve(draft, catalog)
    chosen_ids = {c["itemId"] for c in resolution["sheet"]["equipment"]["chosen"]}
    assert "chain-mail" in chosen_ids


def test_unhashable_choice_selection_element_is_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 1, "choices": {"class:fighter:1:prof-choice-0": [["skill-athletics"], "skill-history"]}}],
    )
    resolution = resolve(draft, catalog)  # must not raise
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    assert skill_choice["selected"] == ["skill-history"]  # the unhashable element is skipped, the valid one kept


def _wizard_draft(int_score=10, **overrides):
    draft = {
        "name": "Test Wizard", "sources": ["srd"],
        "classes": [{"classId": "wizard", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {
            "method": "manual",
            "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": int_score, "WIS": 10, "CHA": 10},
        },
        "equipment": {"added": [], "skipped": False}, "details": {},
    }
    draft.update(overrides)
    return draft


def _bare_class_draft(cls_id, **overrides):
    draft = {
        "name": "Test Character", "sources": ["srd"],
        "classes": [{"classId": cls_id, "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {
            "method": "manual",
            "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        },
        "equipment": {"added": [], "skipped": False}, "details": {},
    }
    draft.update(overrides)
    return draft


def test_wizard_gets_cantrip_and_prepared_spell_choices(catalog):
    resolution = resolve(_wizard_draft(int_score=16), catalog)
    cantrip_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-cantrips")
    assert cantrip_choice["count"] == 3
    assert cantrip_choice["label"] == "Cantrips Known"
    assert all(opt["id"] in catalog.spells for opt in cantrip_choice["options"])
    known_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-known")
    assert known_choice["count"] == 4  # INT mod +3, class level 1 -> max(1, 3+1)
    assert known_choice["label"] == "Prepared Spells"


def test_wizard_cantrip_options_are_level_zero_wizard_spells_only(catalog):
    resolution = resolve(_wizard_draft(), catalog)
    cantrip_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-cantrips")
    for opt in cantrip_choice["options"]:
        spell = catalog.spells[opt["id"]]
        assert spell["level"] == 0
        assert any(c["index"] == "wizard" for c in spell["classes"])


def test_bard_known_choice_uses_explicit_spells_known_not_a_formula(catalog):
    resolution = resolve(_bare_class_draft("bard"), catalog)
    known_choice = next(c for c in resolution["choices"] if c["id"] == "class:bard:spells-known")
    assert known_choice["count"] == 4  # bard's level-1 spells_known, regardless of CHA modifier
    assert known_choice["label"] == "Spells Known"


def test_paladin_gets_no_spell_choices_at_level_1(catalog):
    resolution = resolve(_bare_class_draft("paladin"), catalog)
    spell_choice_ids = [c["id"] for c in resolution["choices"] if "spells" in c["id"]]
    assert spell_choice_ids == []
    assert resolution["sheet"]["spells"] is None
    assert resolution["derived"]["spellSaveDC"] is None
    assert resolution["derived"]["spellAttackBonus"] is None


def test_fighter_has_no_spell_choices_or_derived_spell_stats(catalog):
    resolution = resolve(_bare_class_draft("fighter"), catalog)
    spell_choice_ids = [c["id"] for c in resolution["choices"] if "spells" in c["id"]]
    assert spell_choice_ids == []
    assert resolution["sheet"]["spells"] is None
    assert resolution["derived"]["spellSaveDC"] is None


def test_selected_cantrips_and_known_spells_appear_in_the_sheet(catalog):
    # Fireball is level 3, so it's never offered at level 1 — look up real
    # level-appropriate wizard spells/cantrips programmatically rather than
    # hardcoding names that haven't been verified against the loaded data.
    cantrip_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 0 and any(c["index"] == "wizard" for c in s["classes"])
    )
    spell_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 1 and any(c["index"] == "wizard" for c in s["classes"])
    )
    draft = _wizard_draft(
        int_score=16,
        classes=[{
            "classId": "wizard", "level": 1,
            "choices": {
                "class:wizard:spells-cantrips": [cantrip_id],
                "class:wizard:spells-known": [spell_id],
            },
        }],
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["spells"]["cantrips"][0]["id"] == cantrip_id
    assert resolution["sheet"]["spells"]["known"][0]["id"] == spell_id


def test_derived_spell_save_dc_and_attack_bonus_use_the_spellcasting_ability(catalog):
    resolution = resolve(_wizard_draft(int_score=16), catalog)
    # INT 16 -> +3 modifier, prof bonus 2 at level 1
    assert resolution["derived"]["spellSaveDC"] == 13  # 8 + 2 + 3
    assert resolution["derived"]["spellAttackBonus"] == 5  # 2 + 3


def test_sheet_details_passes_through_submitted_fields_only(catalog):
    draft = _fighter_acolyte_human_draft(
        details={"alignment": "Chaotic Good", "backstory": "Раснал в Невървинтър."},
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] == {"alignment": "Chaotic Good", "backstory": "Раснал в Невървинтър."}


def test_sheet_details_is_none_when_missing(catalog):
    draft = _fighter_acolyte_human_draft()
    del draft["details"]
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] is None


def test_sheet_details_is_none_when_explicitly_null(catalog):
    draft = _fighter_acolyte_human_draft(details=None)
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] is None


def test_malformed_details_is_none_and_not_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(details="not a dict")
    resolution = resolve(draft, catalog)  # must not raise
    assert resolution["sheet"]["details"] is None
    assert not any(p["id"].startswith("malformed-details") or "details" in p["id"] for p in resolution["problems"])


def test_sheet_details_drops_unknown_keys_and_non_string_values(catalog):
    draft = _fighter_acolyte_human_draft(
        details={"alignment": "Chaotic Good", "unknownField": "ignored", "faith": 12345},
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] == {"alignment": "Chaotic Good"}


def test_sheet_details_is_none_for_explicitly_empty_dict(catalog):
    draft = _fighter_acolyte_human_draft(details={})
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] is None


def test_sheet_details_is_none_when_nothing_survives_filtering(catalog):
    draft = _fighter_acolyte_human_draft(
        details={"alignment": 1, "faith": [], "lifestyle": None},
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] is None


def test_detail_fields_contract_is_pinned(catalog):
    # Guards against a frontend/backend field-name drift silently dropping
    # data at export time — if types.ts gains/renames a details field
    # without a matching update here, this fails loudly.
    assert _DETAIL_FIELDS == (
        "alignment", "faith", "lifestyle",
        "age", "height", "weight", "eyes", "skin", "hair",
        "personalityTraits", "ideals", "bonds", "flaws",
        "backstory", "organizations", "allies", "enemies", "notes",
    )


def test_sheet_details_drops_whitespace_only_values(catalog):
    draft = _fighter_acolyte_human_draft(
        details={"alignment": "   ", "faith": "Deity of Wind"},
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["details"] == {"faith": "Deity of Wind"}


def test_sheet_details_output_order_is_canonical_regardless_of_submission_order(catalog):
    draft = _fighter_acolyte_human_draft(
        details={"notes": "Some notes", "alignment": "Chaotic Good", "faith": "Deity of Wind"},
    )
    resolution = resolve(draft, catalog)
    assert list(resolution["sheet"]["details"].keys()) == ["alignment", "faith", "notes"]


def test_level_2_to_20_is_no_longer_a_problem(catalog):
    for level in (2, 5, 10, 20):
        draft = _fighter_acolyte_human_draft(
            classes=[{"classId": "fighter", "level": level, "choices": {}}],
        )
        resolution = resolve(draft, catalog)
        assert not any(p["id"] == "level-unsupported" for p in resolution["problems"])
        assert resolution["sheet"]["level"] == level


def test_level_0_or_above_20_is_still_a_problem(catalog):
    for bad_level in (0, 21, -1):
        draft = _fighter_acolyte_human_draft(
            classes=[{"classId": "fighter", "level": bad_level, "choices": {}}],
        )
        resolution = resolve(draft, catalog)
        assert any(p["id"] == "level-unsupported" for p in resolution["problems"])


def test_level_1_character_is_byte_identical_to_before_this_phase(catalog):
    # Regression anchor: every choice id, sheet shape, and derived stat
    # for a level-1 Fighter must be unchanged from Phase 2's behavior.
    draft = _fighter_acolyte_human_draft()
    resolution = resolve(draft, catalog)
    choice_ids = {c["id"] for c in resolution["choices"]}
    assert "class:fighter:1:prof-choice-0" in choice_ids  # proficiency choice, unchanged
    # feature choices at level 1 keep their level-1 id shape
    assert any(cid.startswith("class:fighter:1:feature:") for cid in choice_ids)
    assert resolution["derived"]["proficiencyBonus"] == 2
    assert resolution["derived"]["hitPointMax"] == 12  # d10 + CON mod 1, matches existing fixture's expected value
    assert resolution["derived"]["hitDice"] == "1d10"


def test_cumulative_feature_choices_appear_as_level_increases(catalog):
    # Wizard gains a feature choice-worthy pick at level 2 (arcane-tradition
    # triggers subclass selection, not a Choice — but other classes have
    # real per-level feature choices; use a level where a NEW choice
    # genuinely appears). Verify structurally: resolving at level 3 must
    # include every choice id that resolving at level 1 includes, plus
    # possibly more — never fewer.
    draft_l1 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 1, "choices": {}}])
    draft_l3 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 3, "choices": {}}])
    ids_l1 = {c["id"] for c in resolve(draft_l1, catalog)["choices"] if c["source"]["kind"] == "class"}
    ids_l3 = {c["id"] for c in resolve(draft_l3, catalog)["choices"] if c["source"]["kind"] == "class"}
    assert ids_l1.issubset(ids_l3)


def test_prof_bonus_scales_with_level(catalog):
    # SRD prof bonus table: +2 at 1-4, +3 at 5-8, +4 at 9-12, +5 at 13-16, +6 at 17-20
    expectations = {1: 2, 5: 3, 9: 4, 13: 5, 17: 6, 20: 6}
    for level, expected in expectations.items():
        draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": level, "choices": {}}])
        resolution = resolve(draft, catalog)
        assert resolution["derived"]["proficiencyBonus"] == expected, f"level {level}"


def test_asi_choices_appear_at_the_right_levels_for_fighter(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 19, "choices": {}}])
    resolution = resolve(draft, catalog)
    asi_ids = sorted(c["id"] for c in resolution["choices"] if c["id"].endswith(":asi"))
    assert asi_ids == [
        "class:fighter:12:asi", "class:fighter:14:asi", "class:fighter:16:asi",
        "class:fighter:19:asi", "class:fighter:4:asi", "class:fighter:6:asi", "class:fighter:8:asi",
    ]


def test_asi_choices_do_not_appear_above_the_selected_level(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    asi_ids = [c["id"] for c in resolution["choices"] if c["id"].endswith(":asi")]
    assert asi_ids == ["class:fighter:4:asi"]  # not 6 or 8, since level is only 5


def test_asi_option_disabled_when_it_would_exceed_the_cap(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 19, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    asi_choice = next(c for c in resolution["choices"] if c["id"] == "class:fighter:4:asi")
    str_plus_2 = next(o for o in asi_choice["options"] if o["id"] == "str-plus-2")
    assert str_plus_2.get("disabled") is True
    dex_plus_2 = next(o for o in asi_choice["options"] if o["id"] == "dex-plus-2")
    assert not dex_plus_2.get("disabled")


def test_selecting_an_asi_actually_increases_the_final_ability_score(catalog):
    # The fixture's Human species already gives +1 to every ability score
    # (verified directly against 5e-SRD-Races.json's human entry), so
    # final STR before any ASI is 16 (fixture base) + 1 (species) = 17,
    # not the base score alone — don't forget this term when computing
    # expected values for any ASI test that uses the standard fixture.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": ["str-plus-2"]}}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["abilities"]["STR"] == 19  # 16 base + 1 species + 2 from ASI


def test_asi_cap_check_uses_the_running_score_including_earlier_asis(catalog):
    # Fixture base STR 16 + Human's +1 = 17 final before any ASI. Pick
    # str-plus-2 at level 4 -> STR 19. At level 8, str-plus-2 must be
    # disabled (19+2=21 > 20) even though a check against only the
    # base+species score (17+2=19) would have wrongly shown it as still
    # available — this is the actual distinguishing case for "stacked
    # scores, not base scores" (a check using 19 as the starting override
    # would already be at/above the interesting boundary regardless of
    # stacking, so it wouldn't prove anything about the ordering bug this
    # test exists to catch).
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 8, "choices": {
            "class:fighter:4:asi": ["str-plus-2"],
        }}],
    )
    resolution = resolve(draft, catalog)
    asi_choice_8 = next(c for c in resolution["choices"] if c["id"] == "class:fighter:8:asi")
    str_plus_2_at_8 = next(o for o in asi_choice_8["options"] if o["id"] == "str-plus-2")
    assert str_plus_2_at_8.get("disabled") is True
    assert resolution["sheet"]["abilities"]["STR"] == 19  # 16 base + 1 species + 2 from the level-4 pick


def test_subclass_selection_at_the_correct_level(catalog):
    # Cleric unlocks its subclass at level 1
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "cleric", "level": 1, "subclassId": "life", "choices": {}}],
        background={"id": "acolyte", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "subclass-mismatch" for p in resolution["problems"])


def test_subclass_mismatch_is_a_problem(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 3, "subclassId": "life", "choices": {}}],  # "life" belongs to cleric, not fighter
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "subclass-mismatch" for p in resolution["problems"])


def test_spell_choice_ids_are_level_agnostic_now(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 1, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    choice_ids = {c["id"] for c in resolution["choices"]}
    assert "class:wizard:spells-cantrips" in choice_ids
    assert "class:wizard:1:spells-cantrips" not in choice_ids  # old, level-suffixed id must be gone


def test_spell_options_expand_with_level(catalog):
    # A level-5 Wizard has 3rd-level slots — the "known" spell choice's
    # options must include 3rd-level spells, not just 1st-level ones.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    known_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-known")
    option_ids = {o["id"] for o in known_choice["options"]}
    fireball_present = "fireball" in option_ids  # fireball is a real 3rd-level wizard spell, verified earlier this session
    assert fireball_present


def test_hit_point_max_grows_with_level(catalog):
    draft_l1 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 1, "choices": {}}])
    draft_l5 = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    hp_l1 = resolve(draft_l1, catalog)["derived"]["hitPointMax"]
    hp_l5 = resolve(draft_l5, catalog)["derived"]["hitPointMax"]
    assert hp_l5 > hp_l1


def test_manual_hp_rolls_are_used_when_present(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 2, "hpRolls": {"2": 10}, "choices": {}}],
        preferences={"advancementType": "milestone", "hitPointType": "manual", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    # CON mod is 2, not 1 — fixture base CON 14 + Human's +1 species bonus
    # = 15, and (15-10)//2 = 2 (matches the existing level-1 regression
    # test's own hitPointMax == 12 assertion: 10 + 2 = 12). Don't assume
    # the base score's own modifier without the species bonus applied.
    # level 1: 10 (d10 max) + 2 (CON mod) = 12; level 2 manual roll 10 + 2 = 12 -> 24
    assert resolution["derived"]["hitPointMax"] == 24


def test_hit_dice_string_reflects_the_level(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "fighter", "level": 5, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["hitDice"] == "5d10"


def test_warlock_level_3_still_gets_a_spells_known_choice(catalog):
    # Regression for the Critical finding: Warlock's Pact Magic moves
    # slots up out of spell_slots_level_1 starting at level 3, and the
    # gate in known_spell_count used to key specifically on
    # spell_slots_level_1, silently zeroing out Warlock's spell choice
    # from level 3 onward.
    draft = _bare_class_draft("warlock", classes=[{"classId": "warlock", "level": 3, "choices": {}}])
    resolution = resolve(draft, catalog)
    known_choice = next(c for c in resolution["choices"] if c["id"] == "class:warlock:spells-known")
    assert known_choice["count"] > 0


def test_cleric_with_subclass_puts_it_on_the_resolved_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "cleric", "level": 1, "subclassId": "life", "choices": {}}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["class"]["subclass"] == {"id": "life", "name": "Life"}


def test_class_with_no_subclass_selected_has_a_null_subclass_on_the_sheet(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["sheet"]["class"]["subclass"] is None


def test_species_chosen_languages_appear_on_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        species={"id": "human", "choices": {"species:human:languages": ["draconic"]}},
    )
    resolution = resolve(draft, catalog)
    assert "draconic" in resolution["sheet"]["proficiencies"]["languages"]


def test_background_chosen_languages_still_appear_no_regression(catalog):
    # Acolyte's own language choice — confirm this plan's fix doesn't
    # accidentally drop background-sourced languages while adding
    # species-sourced ones.
    draft = _fighter_acolyte_human_draft(
        background={"id": "acolyte", "choices": {"background:acolyte:languages": ["celestial", "infernal"]}},
    )
    resolution = resolve(draft, catalog)
    languages = resolution["sheet"]["proficiencies"]["languages"]
    assert "celestial" in languages and "infernal" in languages
