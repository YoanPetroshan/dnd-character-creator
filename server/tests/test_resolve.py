import pytest

from catalog.loader import load
# has_official is imported FROM official_source (a re-export), not from
# chargen.sources directly — see official_source.py's own docstring for
# why every caller in this plan does it this way.
from catalog.official_source import has_official
from engine.derived import hit_point_max_multiclass
from engine.resolve import _DETAIL_FIELDS, _feat_senses, _resolve_granted_feats, resolve


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
    assert resolution["sheet"]["classes"] == []
    assert resolution["sheet"]["grantedFeats"] == []


def test_fighter_acolyte_human_produces_expected_sheet_and_derived(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["problems"] == []
    sheet = resolution["sheet"]
    assert sheet["name"] == "Torvin Bracewell"
    assert sheet["level"] == 1
    assert sheet["classes"] == [{"id": "fighter", "name": "Fighter", "level": 1, "subclass": None}]
    assert sheet["background"] == {"id": "acolyte", "name": "Acolyte"}
    # Bundled SRD Acolyte carries no `feats` field — always present as []
    # rather than null, mirroring Task 5's damageModifiers precedent.
    assert sheet["grantedFeats"] == []
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


def test_dwarf_dwarven_combat_training_weapon_proficiencies_reach_the_sheet(catalog):
    # PRE-EXISTING bug (predates this plan, affects bundled SRD data
    # unconditionally): resolve()'s trait-scanning only ever forwarded
    # skill- prefixed proficiency ids out of race/subrace traits, so
    # Dwarven Combat Training's weapon grants (chargen/data/srd/
    # 5e-SRD-Traits.json, index "dwarven-combat-training") never reached
    # sheet.proficiencies.weapons for any Dwarf. Ids confirmed directly
    # against that file: battleaxes, handaxes, light-hammers, warhammers.
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    weapons = set(resolution["sheet"]["proficiencies"]["weapons"])
    assert {"battleaxes", "handaxes", "light-hammers", "warhammers"} <= weapons


def test_half_elf_skill_versatility_choice_is_offered_and_flows_through_resolve(catalog):
    # PRE-EXISTING gap (predates this plan, affects bundled SRD data
    # unconditionally): _species_choice_templates never read a trait's
    # proficiency_choices field, so Half-Elf's real "Skill Versatility"
    # trait (chargen/data/srd/5e-SRD-Traits.json, index "skill-versatility",
    # choose 2 of every skill) never produced a Choice the player could even
    # see.
    draft = _fighter_acolyte_human_draft(species={"id": "half-elf", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    versatility_cid = next((cid for cid in cids if "skill-versatility" in cid), None)
    assert versatility_cid is not None, f"expected a Skill Versatility choice, got choice ids: {cids}"

    # Re-resolve with a real selection for it and confirm it lands on the sheet.
    draft["species"]["choices"][versatility_cid] = ["skill-arcana", "skill-history"]
    resolution2 = resolve(draft, catalog)
    assert {"skill-arcana", "skill-history"} <= set(resolution2["sheet"]["proficiencies"]["skills"])


def test_dwarf_tool_proficiency_choice_flows_into_sheet_tools(catalog):
    # PRE-EXISTING gap (predates this plan, affects bundled SRD data
    # unconditionally): same root cause as the Half-Elf test above, for
    # Dwarf's real "Tool Proficiency" trait (index "tool-proficiency",
    # choose 1 of smith's/brewer's/mason's tools).
    draft = _fighter_acolyte_human_draft(species={"id": "dwarf", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    tool_cid = next((cid for cid in cids if "tool-proficiency" in cid), None)
    assert tool_cid is not None, f"expected a Tool Proficiency choice, got choice ids: {cids}"

    draft["species"]["choices"][tool_cid] = ["smiths-tools"]
    resolution2 = resolve(draft, catalog)
    assert "smiths-tools" in resolution2["sheet"]["proficiencies"]["tools"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_background_tool_proficiency_reaches_the_sheet(catalog):
    # PRE-EXISTING gap (predates this plan, genuinely separate from the
    # race/subrace trait-scanning bug the two tests above cover): resolve()'s
    # background-scanning code only ever forwarded skill- prefixed entries
    # out of a background's starting_proficiencies, so tool/weapon/armor
    # grants never reached sheet.proficiencies. SRD's own bundled Acolyte has
    # no such grant (only skill-insight/skill-religion — confirmed directly
    # against chargen/data/srd/5e-SRD-Backgrounds.json), so this bug is only
    # reachable via sourcebook data: acolyte-xphb's real Calligrapher's
    # Supplies grant (confirmed against the real fetched official data,
    # 2026-09-26: catalog.backgrounds["acolyte-xphb"]["starting_proficiencies"]
    # == [skill-insight, skill-religion, calligraphers-supplies]).
    draft = _fighter_acolyte_human_draft(sources=["xphb"], background={"id": "acolyte-xphb", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    tools = set(resolution["sheet"]["proficiencies"]["tools"])
    assert "calligraphers-supplies" in tools


def test_human_has_no_extra_weapon_tool_armor_from_traits(catalog):
    # Human has zero traits (chargen/data/srd/5e-SRD-Races.json: traits ==
    # []), so this confirms the new trait-scanning pass doesn't leak
    # anything extra in — Fighter's own class grants (simple/martial
    # weapons, all-armor, shields) are untouched.
    draft = _fighter_acolyte_human_draft()
    resolution = resolve(draft, catalog)
    profs = resolution["sheet"]["proficiencies"]
    assert set(profs["weapons"]) == {"simple-weapons", "martial-weapons"}
    assert set(profs["armor"]) == {"all-armor", "shields"}
    assert set(profs["tools"]) == set()


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


def test_rogue_class_skill_choice_disables_option_already_granted_by_species(catalog):
    # Elf's Keen Senses trait grants Perception for free, and Rogue's own
    # skill-proficiency choice list includes skill-perception as one of its
    # options — without the species-overlap guard, a player could spend one
    # of Rogue's 4 skill picks on a skill they already have for free.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "rogue", "level": 1, "choices": {}}],
        species={"id": "elf", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["id"] == "class:rogue:1:prof-choice-0")
    perception = next(o for o in skill_choice["options"] if o["id"] == "skill-perception")
    assert perception.get("disabled") is True
    assert "Elf" in perception["disabledReason"]


def test_disabled_species_granted_skill_is_excluded_from_valid_selections(catalog):
    # Submitting the disabled option anyway must not count toward the
    # choice's resolution, matching how a disabled background-granted
    # option already behaves.
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "rogue", "level": 1,
            "choices": {"class:rogue:1:prof-choice-0": ["skill-perception", "skill-stealth", "skill-acrobatics", "skill-athletics"]},
        }],
        species={"id": "elf", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["id"] == "class:rogue:1:prof-choice-0")
    assert "skill-perception" not in skill_choice["selected"]
    assert skill_choice["status"] == "pending"  # only 3 of 4 required picks were valid
    assert set(skill_choice["selected"]) == {"skill-stealth", "skill-acrobatics", "skill-athletics"}


def test_species_overlap_does_not_affect_a_race_with_no_automatic_skill_grant(catalog):
    # Human grants no automatic skill proficiency, so the species-overlap
    # guard shouldn't disable anything on Rogue's own skill choice (the
    # fixture's Acolyte background DOES overlap with Rogue's Insight
    # option via the pre-existing background-overlap guard, so this checks
    # specifically that nothing is attributed to Human, not that nothing
    # is disabled at all).
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "rogue", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["id"] == "class:rogue:1:prof-choice-0")
    assert not any("Human" in (o.get("disabledReason") or "") for o in skill_choice["options"])


def test_multiclass_draft_sheet_reflects_every_class(catalog):
    # Multiclassing is now resolved for real, and sheet assembly (Task 5)
    # renders every class in draft.classes — not just the first — so no
    # multiclass-unsupported problem is produced and both classes appear.
    draft = _fighter_acolyte_human_draft(classes=[
        {"classId": "fighter", "level": 1, "choices": {}},
        {"classId": "wizard", "level": 1, "choices": {}},
    ])
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])
    class_ids = [c["id"] for c in resolution["sheet"]["classes"]]
    assert class_ids == ["fighter", "wizard"]


def test_two_classes_no_longer_produce_multiclass_unsupported(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "multiclass-unsupported" for p in resolution["problems"])


def test_total_level_over_20_is_a_problem_not_silently_truncated(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 15, "choices": {}},
            {"classId": "wizard", "level": 10, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "total-level-exceeded" for p in resolution["problems"])


def test_duplicate_class_id_is_a_problem_and_only_first_occurrence_counted(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "fighter", "level": 5, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "duplicate-class" for p in resolution["problems"])
    # Only ONE Fighter's worth of level-1 proficiency choices should exist
    # — not two — confirming the duplicate was dropped, not merged/summed.
    prof_choices = [c for c in resolution["choices"] if c["id"] == "class:fighter:1:prof-choice-0"]
    assert len(prof_choices) == 1


def test_non_primary_class_choice_selections_reach_all_selections(catalog):
    # Review finding 1: all_selections was only ever populated from
    # classes[0]'s own submitted choices, so a second/third class's own
    # choice selections (here, Rogue's multiclass skill-proficiency pick,
    # submitted on classes[1]) could never be read back — leaving that
    # choice stuck "pending" no matter what was submitted.
    #
    # Uses Rogue's multiclass-prof-choice-0 (not a primary-only
    # 1:prof-choice-0 id) because the final-review fix wave made
    # 1:prof-choice-0 PRIMARY-only — a secondary class no longer gets that
    # template at all, so asserting on it here would conflate this
    # all_selections-merging behavior with that separate, already-covered
    # gating behavior.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 1, "choices": {}},
            {
                "classId": "rogue", "level": 1,
                "choices": {"class:rogue:multiclass-prof-choice-0": ["skill-stealth"]},
            },
        ],
    )
    resolution = resolve(draft, catalog)
    rogue_skill_choice = next(c for c in resolution["choices"] if c["id"] == "class:rogue:multiclass-prof-choice-0")
    assert rogue_skill_choice["selected"] == ["skill-stealth"]
    assert rogue_skill_choice["status"] == "resolved"


def test_invalid_large_level_does_not_spuriously_trigger_total_level_exceeded(catalog):
    # Review finding 2: total_level (feeding the total-level-exceeded
    # problem) was summed from RAW, unvalidated per-entry levels, before
    # the per-class loop clamps an out-of-range level like 25 down to 1.
    # A single class with a garbage level of 25 must not trigger
    # total-level-exceeded, since the REAL resolved level is 1.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 25, "choices": {}}],
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "total-level-exceeded" for p in resolution["problems"])
    assert any(p["id"] == "level-unsupported" for p in resolution["problems"])


def test_total_level_exceeded_still_fires_for_two_genuinely_valid_classes(catalog):
    # Regression guard for the finding-2 fix: two VALID classes whose real
    # summed level legitimately exceeds 20 must still produce
    # total-level-exceeded, computed from the clamped/validated levels.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 15, "choices": {}},
            {"classId": "wizard", "level": 10, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "total-level-exceeded" for p in resolution["problems"])
    assert not any(p["id"] == "level-unsupported" for p in resolution["problems"])


def test_unknown_class_id_produces_a_problem_not_a_crash(catalog):
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "not-a-class", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "unknown-class" for p in resolution["problems"])
    assert resolution["sheet"]["classes"] == []


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


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_ability_bonus_choice_flows_through_resolve(catalog):
    # Aetherborn (PSK, official_source.py's own id "aetherborn-psk"): a
    # fixed +2 CHA plus a SEPARATE choose-2-of-{STR,DEX,CON,INT,WIS}
    # choice for +1 each — confirmed against the real fetched data
    # (2026-09-23). This exercises Phase 3b's Half-Elf-built ability-bonus
    # Choice machinery end to end for a Task 2/official_source.py-produced
    # envelope, with zero changes to resolve.py or catalog/choices.py.
    draft = _fighter_acolyte_human_draft(
        sources=["psk"],
        species={"id": "aetherborn-psk", "choices": {"species:aetherborn-psk:ability-bonus": ["str", "dex"]}},
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    scores = resolution["sheet"]["abilities"]
    assert scores["STR"] == 15  # 14 base + 1 from the choice
    assert scores["DEX"] == 13  # 12 base + 1 from the choice
    assert scores["CHA"] == 10  # 8 base + 2 fixed Aetherborn bonus, unrelated to the choice
    assert scores["CON"] == 14  # unaffected — not selected

    choice = next(c for c in resolution["choices"] if c["id"] == "species:aetherborn-psk:ability-bonus")
    assert choice["status"] == "resolved"
    assert choice["count"] == 2
    assert choice["selected"] == ["str", "dex"]
    assert {o["id"] for o in choice["options"]} == {"str", "dex", "con", "int", "wis"}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_race_damage_modifiers_carry_through_to_the_sheet(catalog):
    # Aasimar/VGM ("aasimar-vgm"): fixed necrotic/radiant resistance — no
    # choice-shape involved, confirmed against the real fetched races.json
    # (2026-09-24). resist/immune/vulnerable/conditionImmune are otherwise
    # empty for this race, so this also exercises the always-empty-list
    # (never null/missing) branches for immunities/conditionImmunities.
    draft = _fighter_acolyte_human_draft(sources=["vgm"], species={"id": "aasimar-vgm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["necrotic", "radiant"]
    assert resolution["sheet"]["damageModifiers"]["immunities"] == []
    assert resolution["sheet"]["conditionImmunities"] == []


def test_a_race_with_no_damage_modifiers_gets_empty_lists(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)  # Human, no resistances
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}
    assert resolution["sheet"]["conditionImmunities"] == []
    # Phase 4c-i Task 5: a character with no granted feats (bundled SRD
    # Acolyte carries no `feats` field at all) must be a complete safe
    # no-op — sheet.senses defaults to an empty dict, same "always
    # present, empty when absent" convention damageModifiers/
    # conditionImmunities already use.
    assert resolution["sheet"]["senses"] == {}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_background_granted_feat_resistance_reaches_the_sheet(catalog):
    # House Lyrandar Heir/EFA grants the Mark of Storm/EFA feat (fixed,
    # not a choice — confirmed against the real fetched backgrounds.json/
    # feats.json, 2026-09-28), which itself grants a fixed lightning
    # resistance. This is the ONLY way resolve() has today to know a
    # character "has" a feat at all — no ASI-feat-choice or standalone
    # feat-selection mechanic exists yet (grep-confirmed) — so it's the
    # real path this task's merge logic is exercised through end to end.
    draft = _fighter_acolyte_human_draft(
        sources=["phb", "efa"], background={"id": "house-lyrandar-heir-efa", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["grantedFeats"] == ["mark-of-storm"]
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["lightning"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_feat_resistance_adds_to_an_existing_race_resistance_not_replacing_it(catalog):
    # Aasimar/VGM already grants necrotic+radiant resistance (see
    # test_race_damage_modifiers_carry_through_to_the_sheet above);
    # stacking House Lyrandar Heir/EFA's Mark of Storm (lightning) on top
    # must ADD to that list, not replace it — the exact behavior this
    # task's brief called out by name. Order: race-then-subrace-then-feats
    # (the same left-to-right merge _species_damage_modifiers/
    # _species_condition_immunities already use for race+subrace).
    draft = _fighter_acolyte_human_draft(
        sources=["vgm", "phb", "efa"],
        species={"id": "aasimar-vgm", "choices": {}},
        background={"id": "house-lyrandar-heir-efa", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["necrotic", "radiant", "lightning"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_ambiguous_granted_feat_slug_does_not_crash_or_guess_a_source(catalog):
    # Aberrant Heir/EFA grants "aberrant-dragonmark" — a bare, source-less
    # slug that matches FEATS in two different real sourcebooks (EFA and
    # ERLW, confirmed 2026-09-28), so which source-variant is actually
    # meant can't be determined from the grant alone. Must not crash and
    # must not silently pick one arbitrarily — see _resolve_granted_feats'
    # own docstring. (Neither variant carries resist/immune/senses data
    # today, so this also confirms the ambiguity guard doesn't silently
    # drop something that WOULD have mattered.)
    draft = _fighter_acolyte_human_draft(sources=["phb", "efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["grantedFeats"] == ["aberrant-dragonmark"]
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}
    assert resolution["sheet"]["senses"] == {}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_resolve_granted_feats_matches_an_unambiguous_bare_slug(catalog):
    # Direct unit test of the slug-matching helper itself — a background's
    # granted-feat id is bare/source-less ("mark-of-storm"), but
    # catalog.feats is keyed "slug-source" ("mark-of-storm-efa"; see
    # _feats_from_5etools' own docstring in official_source.py for why).
    # "mark-of-storm" matches exactly one real feat (EFA only), so it must
    # resolve to that feat's own dict, carrying its resist data.
    resolved = _resolve_granted_feats(["mark-of-storm"], catalog)
    assert len(resolved) == 1
    assert resolved[0]["index"] == "mark-of-storm-efa"
    assert resolved[0]["resist"] == ["lightning"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_resolve_granted_feats_skips_an_ambiguous_bare_slug(catalog):
    # "alert" matches feats in BOTH PHB and XPHB (confirmed 2026-09-28) —
    # which source-variant a bare grant means can't be determined from the
    # id alone, so it's skipped rather than guessing.
    resolved = _resolve_granted_feats(["alert"], catalog)
    assert resolved == []


def test_resolve_granted_feats_with_no_catalog_match_is_a_safe_no_op(catalog):
    resolved = _resolve_granted_feats(["not-a-real-feat"], catalog)
    assert resolved == []


def test_feat_senses_merges_multiple_granted_feats():
    feats = [{"senses": {"blindsight": 15}}, {"senses": {"truesight": 60}}]
    assert _feat_senses(feats) == {"blindsight": 15, "truesight": 60}


def test_feat_senses_same_type_resolves_to_the_higher_range_not_additive():
    # RAW: multiple sources of the same sense type (e.g. two sources of
    # darkvision/blindsight) don't stack additively — the higher range
    # wins, unless a specific ability explicitly says otherwise (none of
    # the real granted-feat senses data does). Order-independent: the
    # higher value wins regardless of which feat is processed first.
    lower_then_higher = [{"senses": {"blindsight": 10}}, {"senses": {"blindsight": 15}}]
    higher_then_lower = [{"senses": {"blindsight": 15}}, {"senses": {"blindsight": 10}}]
    assert _feat_senses(lower_then_higher) == {"blindsight": 15}
    assert _feat_senses(higher_then_lower) == {"blindsight": 15}


def test_feat_senses_with_no_feats_is_an_empty_dict():
    assert _feat_senses([]) == {}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_subrace_only_resistance_flows_through_to_the_sheet(catalog):
    # Stout Halfling/PHB's poison resistance lives on the SUBRACE record,
    # not the parent Halfling race (confirmed against the real fetched
    # races.json, 2026-09-24) — exercises _species_damage_modifiers'
    # race+subrace merge, not just the race-only path the brief's own
    # example test covers.
    draft = _fighter_acolyte_human_draft(
        sources=["phb"], species={"id": "halfling-phb", "subspeciesId": "halfling-phb-stout-phb", "choices": {}}
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["poison"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_choice_shaped_resistance_is_a_disclosed_cut_not_a_crash(catalog):
    # Dragonborn/PHB's `resist` entry is a CHOICE shape
    # ({"choose": {"from": [...]}}) tied to the player's draconic
    # ancestry, not a fixed damage type — confirmed against the real
    # fetched races.json (2026-09-24). Resolving that choice is out of
    # scope for this pure-data-pass-through task (see
    # _damage_modifiers_from_5etools' docstring), so it must not crash
    # and must not be silently mis-modeled as an unconditional
    # resistance — it's simply filtered out, leaving an empty list.
    draft = _fighter_acolyte_human_draft(sources=["phb"], species={"id": "dragonborn-phb", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["damageModifiers"]["resistances"] == []


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_race_innate_spells_resolve_against_the_bundled_srd_catalog(catalog):
    # Aasimar/DMG: level-3 Lesser Restoration (1/day), level-5 Daylight
    # (1/day), fixed CHA ability — both spells ARE in the bundled 2014 SRD
    # catalog (confirmed against the real fetched races.json, 2026-09-24;
    # part of Task 6's re-measured Step 2 finding 93/102 real innate
    # references resolve cleanly). spellId/name come from catalog.spells
    # itself, not official_source.py's raw-fallback name, when resolved.
    draft = _fighter_acolyte_human_draft(sources=["dmg"], species={"id": "aasimar-dmg", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    grants = {g["name"]: g for g in resolution["sheet"]["innateSpells"]}
    assert grants["Lesser Restoration"] == {
        "spellId": "lesser-restoration", "name": "Lesser Restoration",
        "level": 3, "uses": "1/day", "ability": "CHA", "variant": None,
    }
    assert grants["Daylight"]["spellId"] == "daylight"
    assert grants["Daylight"]["level"] == 5


def test_a_race_with_no_innate_spells_gets_an_empty_list(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)  # Human, no innate spells
    assert resolution["sheet"]["innateSpells"] == []


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_unresolvable_innate_spell_still_shows_its_name_with_a_null_spell_id(catalog):
    # Triton/VGM's level-5 innate spell references "wall of water|xge" — a
    # real spell this project has no bundled DATA for (only the SRD 2014
    # spell list is bundled; confirmed empirically, 2026-09-24, one of
    # Task 6's re-measured Step 2's 9/102 unresolvable real references).
    # Must degrade gracefully: spellId null, but name still shown, not
    # silently dropped from the sheet and not a crash.
    draft = _fighter_acolyte_human_draft(sources=["vgm"], species={"id": "triton-vgm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    grants = {g["name"]: g for g in resolution["sheet"]["innateSpells"]}
    assert grants["Wall Of Water"]["spellId"] is None
    assert grants["Wall Of Water"]["level"] == 5
    assert grants["Wall Of Water"]["uses"] == "1/day"
    # Sibling grants on the SAME race still resolve normally, unaffected.
    assert grants["Fog Cloud"]["spellId"] == "fog-cloud"


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_rest_wrapped_innate_spell_resolves_on_the_sheet_not_silently_dropped(catalog):
    # Mark of Scribing/ERLW (subrace of Gnome/PHB) is the one real record
    # whose level-1 innate entry uses 5etools' "rest" wrapper key instead
    # of "daily" (confirmed against the real fetched races.json,
    # 2026-09-24 code review). Before the fix, this fell through
    # official_source._innate_spell_uses_and_names' unrecognized-shape
    # fallback and Comprehend Languages never appeared anywhere on the
    # sheet — no problem, no trace. It's a real, resolvable 2014 SRD
    # spell and must show up with a resolved spellId like any other
    # "daily"-wrapped grant.
    draft = _fighter_acolyte_human_draft(
        sources=["phb"], species={"id": "gnome-phb", "subspeciesId": "gnome-phb-mark-of-scribing-erlw", "choices": {}}
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    grants = {g["name"]: g for g in resolution["sheet"]["innateSpells"]}
    assert grants["Comprehend Languages"]["spellId"] == "comprehend-languages"
    assert grants["Comprehend Languages"]["level"] == 1
    assert grants["Comprehend Languages"]["uses"] == "1/day"


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_subrace_innate_spells_merge_with_the_parent_race_on_the_sheet(catalog):
    # Duergar/MTF (subrace of Dwarf/PHB) grants its own innate spells; the
    # parent Dwarf/PHB race has none of its own (confirmed against the
    # real fetched races.json, 2026-09-24) — exercises
    # _species_innate_spells' race+subrace merge, mirroring the
    # damage-modifiers race+subrace merge test above.
    draft = _fighter_acolyte_human_draft(
        sources=["phb"], species={"id": "dwarf-phb", "subspeciesId": "dwarf-phb-duergar-mtf", "choices": {}}
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    grants = {g["name"]: g for g in resolution["sheet"]["innateSpells"]}
    assert grants["Enlarge/Reduce"]["spellId"] == "enlarge-reduce"
    assert grants["Enlarge/Reduce"]["level"] == 3
    assert grants["Invisibility"]["level"] == 5


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_choice_shaped_innate_ability_is_a_disclosed_candidate_list_not_a_crash(catalog):
    # Aarakocra/MPMM's innate-spell ability is {"choose": ["int", "wis",
    # "cha"]} — the majority real shape (confirmed empirically,
    # 2026-09-24). Not resolved to a single committed ability (no new
    # choice-resolution machinery — same scope line Task 5 drew for
    # choice-shaped resistances), but carried through as a candidate list,
    # not dropped or crashed on.
    draft = _fighter_acolyte_human_draft(sources=["mpmm"], species={"id": "aarakocra-mpmm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    grants = resolution["sheet"]["innateSpells"]
    assert len(grants) == 1
    assert grants[0]["name"] == "Gust of Wind"
    assert grants[0]["ability"] == {"choose": ["INT", "WIS", "CHA"]}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_draft_sources_rejects_a_race_from_an_unlisted_sourcebook(catalog):
    # aasimar-vgm's 'source' field is "VGM" (raw 5etools casing) — a
    # draft.sources of just ["phb"] must reject it exactly like an
    # unrecognized id: same problem id, race treated as absent (no
    # damage modifiers/ability bonuses/etc. applied for it).
    draft = _fighter_acolyte_human_draft(sources=["phb"], species={"id": "aasimar-vgm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == [{"id": "unknown-species", "message": "Unknown species 'aasimar-vgm'."}]
    assert resolution["sheet"]["species"] is None
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_draft_sources_allows_a_race_whose_book_is_listed(catalog):
    draft = _fighter_acolyte_human_draft(sources=["phb", "vgm"], species={"id": "aasimar-vgm", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["species"]["id"] == "aasimar-vgm"
    assert resolution["sheet"]["damageModifiers"]["resistances"] == ["necrotic", "radiant"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_source_filtered_race_does_not_leak_its_orphaned_subrace_grants(catalog):
    # Whole-branch review finding: Dwarf/PHB ("dwarf-phb") filtered out by
    # draft.sources (here, ["mtf"] — PHB isn't listed) sets `race` to None
    # and adds "unknown-species", exactly like an unresolvable race should.
    # But the draft still names Duergar/MTF ("dwarf-phb-duergar-mtf") as
    # its subspeciesId, and that subrace's OWN "race.index" field still
    # says "dwarf-phb" (the string id, untouched by the source filter) —
    # so the subspecies-mismatch guard right after the source filter
    # (which only compared subrace.race.index against race_id) let the
    # orphaned subrace survive even though its parent race resolved to
    # None. _species_damage_modifiers/_species_condition_immunities/
    # _species_innate_spells then merged from that orphaned subrace
    # regardless, leaking Duergar's innate spells (Enlarge/Reduce,
    # Invisibility) onto a sheet that simultaneously reports "no species
    # selected" via problems. Confirmed against the SAME dwarf-phb /
    # dwarf-phb-duergar-mtf pairing test_subrace_innate_spells_merge_with_
    # the_parent_race_on_the_sheet already uses with an allowed source.
    draft = _fighter_acolyte_human_draft(
        sources=["mtf"], species={"id": "dwarf-phb", "subspeciesId": "dwarf-phb-duergar-mtf", "choices": {}}
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "unknown-species" for p in resolution["problems"])
    assert resolution["sheet"]["species"] is None
    assert resolution["sheet"]["innateSpells"] == []
    assert resolution["sheet"]["damageModifiers"] == {"resistances": [], "immunities": [], "vulnerabilities": []}
    assert resolution["sheet"]["conditionImmunities"] == []


def test_empty_draft_sources_allows_every_race_unaffected(catalog):
    # Today's default behavior, unaffected by the new filter — an
    # empty/absent 'sources' list means no restriction at all.
    draft = _fighter_acolyte_human_draft(sources=[])
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["species"]["id"] == "human"


def test_bundled_srd_race_is_always_allowed_regardless_of_draft_sources(catalog):
    # SRD races have no 'source' field at all (implicitly bundled/SRD) —
    # they must never be filtered out even when draft.sources names only
    # unrelated official books.
    draft = _fighter_acolyte_human_draft(sources=["vgm"])  # human is bundled SRD, not "vgm"
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["species"]["id"] == "human"


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_draft_sources_rejects_a_background_from_an_unlisted_sourcebook(catalog):
    # aberrant-heir-efa's 'source' field is "EFA" (raw 5etools casing) — a
    # draft.sources of just ["phb"] must reject it exactly like an
    # unrecognized id: same problem id (mirrors Phase 4a Task 7's race-side
    # test), background treated as absent (no ability bonuses/feats/etc.
    # applied for it).
    draft = _fighter_acolyte_human_draft(sources=["phb"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == [{"id": "unknown-background", "message": "Unknown background 'aberrant-heir-efa'."}]
    assert resolution["sheet"]["background"] is None
    assert resolution["sheet"]["grantedFeats"] == []


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_draft_sources_allows_a_background_whose_book_is_listed(catalog):
    draft = _fighter_acolyte_human_draft(sources=["phb", "efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["background"]["id"] == "aberrant-heir-efa"
    assert resolution["sheet"]["grantedFeats"] == ["aberrant-dragonmark"]


def test_empty_draft_sources_allows_every_background_unaffected(catalog):
    # Today's default behavior, unaffected by the new filter — an
    # empty/absent 'sources' list means no restriction at all.
    draft = _fighter_acolyte_human_draft(sources=[])
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["background"]["id"] == "acolyte"


def test_bundled_srd_background_is_always_allowed_regardless_of_draft_sources(catalog):
    # SRD backgrounds have no 'source' field at all (implicitly bundled/
    # SRD) — they must never be filtered out even when draft.sources names
    # only unrelated official books.
    draft = _fighter_acolyte_human_draft(sources=["vgm"])  # acolyte is bundled SRD, not "vgm"
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["background"]["id"] == "acolyte"


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


def test_srd_acolyte_starting_gold_reaches_the_sheet(catalog):
    # SRD Acolyte's own bundled starting_gold field is
    # {"quantity": 15, "unit": "gp"} (chargen/data/srd/5e-SRD-Backgrounds.json,
    # confirmed live) — this fixed field, present on every SRD/official
    # background, was never read anywhere before this task.
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["sheet"]["startingGold"] == 15


def test_background_with_no_gold_gets_a_zero_not_null(catalog):
    # No background selected at all (starting_gold field absent, no
    # selected gold bundle member) should show startingGold == 0, not
    # absent/None, matching this project's always-present-empty convention.
    resolution = resolve(_empty_draft(), catalog)
    assert resolution["sheet"]["startingGold"] == 0


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_selecting_a_gold_bundle_member_reaches_the_sheet(catalog):
    # Aberrant Heir (EFA)'s own equipment choice (confirmed live): bundle A
    # is "dagger+disguise-kit+clothes-costume+clothes-travelers+gp-16",
    # bundle B is "gp-50" (gold-only). Its own starting_gold field is None,
    # so all 50 gold here comes from the selected bundle member alone.
    draft = _fighter_acolyte_human_draft(sources=["efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    equip_cid = next(c["id"] for c in resolution["choices"] if c["id"] == "background:aberrant-heir-efa:equipment-choice-0")
    draft["background"]["choices"][equip_cid] = ["gp-50"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["sheet"]["startingGold"] == 50


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_acolyte_phb_fixed_equipment_and_gold_reach_the_sheet(catalog):
    # Finding 1 of the final whole-branch review (2026-09-27): Acolyte
    # (PHB, sourcebook variant, id "acolyte-phb")'s startingEquipment has
    # ONLY a "_"-keyed fixed entry (no a/b/c/d package choice at all is
    # relevant to gold here — its a/b choice is prayer book vs. prayer
    # wheel, neither of which carries gold). Before this fix,
    # official_source.py hardcoded starting_equipment/starting_gold to
    # []/None regardless of real data, so this record's sheet showed
    # startingGold == 0 (a WRONG, actively misleading zero — the field
    # didn't even exist before this whole plan) and no fixed equipment at
    # all. The real published Acolyte text grants 15 gp (a pouch
    # containing 1500 "copper" in the raw 5etools data, the same 100:1
    # copper-to-gp ratio Task 5 already established) plus a holy symbol,
    # sticks of incense, vestments, and a set of common clothes.
    draft = _fighter_acolyte_human_draft(sources=["phb"], background={"id": "acolyte-phb", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["startingGold"] == 15
    granted_ids = {g["itemId"] for g in resolution["sheet"]["equipment"]["granted"]}
    assert "clothes-common" in granted_ids
    assert resolution["sheet"]["equipment"]["narrativeItems"] == [
        "holy symbol (a gift to you when you entered the priesthood)",
        "Sticks of incense",
        "Vestments",
    ]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_rewarded_bmt_feat_alternatives_do_not_all_land_in_granted_feats(catalog):
    # Finding 2 of the final whole-branch review (2026-09-27): Rewarded/
    # BMT's real text is "You gain the Lucky, Magic Initiate, or Skilled
    # feat (your choice)" — a choice of one, not a simultaneous grant of
    # all three. Before this fix, sheet.grantedFeats would have been
    # ["lucky", "magic-initiate", "skilled"] (inert today, but silently
    # over-granting once Phase 4c starts consuming this data for real).
    draft = _fighter_acolyte_human_draft(sources=["phb", "bmt"], background={"id": "rewarded-bmt", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["sheet"]["grantedFeats"] == []
    assert resolution["sheet"]["featOptions"] == ["lucky", "magic-initiate", "skilled"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_clan_crafter_language_choice_does_not_grant_a_free_wildcard_pick(catalog):
    # Finding 2 of the final whole-branch review (2026-09-27): Clan
    # Crafter/SCAG's real text is "Dwarvish or one of your choice if you
    # already speak Dwarvish" — a single, conditionally-substituted grant,
    # not Dwarvish PLUS an unconditional free pick. Before this fix, this
    # background would also have offered a "Languages" Choice (any
    # language, count 1) alongside the fixed Dwarvish grant.
    draft = _fighter_acolyte_human_draft(sources=["phb", "scag"], background={"id": "clan-crafter-scag", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert "dwarvish" in resolution["sheet"]["proficiencies"]["languages"]
    language_choices = [c for c in resolution["choices"] if c["id"] == "background:clan-crafter-scag:languages"]
    assert language_choices == []


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_flavor_bundle_member_shows_up_as_narrative_text_not_silently_dropped(catalog):
    # Acolyte (PHB, sourcebook variant, id "acolyte-phb")'s own equipment
    # choice (confirmed live) is "book" (a real catalog item, "prayer
    # book") vs. "flavor-prayer-wheel" (a synthetic flavor-text member,
    # display label "Prayer wheel") — selecting the flavor option must
    # surface its label in narrativeItems, not silently vanish.
    #
    # Acolyte/PHB's FIXED "_"-keyed list (holy symbol, incense, vestments —
    # see test_acolyte_phb_fixed_equipment_and_gold_reach_the_sheet below,
    # Finding 1 of the final whole-branch review) now ALSO contributes its
    # own narrative items unconditionally, ahead of whatever the player
    # separately selected — this test's expected list grew to include them
    # (it used to assert just ["Prayer wheel"], back when the fixed list
    # contributed nothing at all).
    draft = _fighter_acolyte_human_draft(sources=["phb"], background={"id": "acolyte-phb", "choices": {}})
    resolution = resolve(draft, catalog)
    equip_cid = next(c["id"] for c in resolution["choices"] if c["id"] == "background:acolyte-phb:equipment-choice-0")
    draft["background"]["choices"][equip_cid] = ["flavor-prayer-wheel"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["sheet"]["equipment"]["narrativeItems"] == [
        "holy symbol (a gift to you when you entered the priesthood)",
        "Sticks of incense",
        "Vestments",
        "Prayer wheel",
    ]
    # Confirm it's not ALSO silently added to granted/chosen as a fake item.
    assert "flavor-prayer-wheel" not in {c["itemId"] for c in resolution2["sheet"]["equipment"]["chosen"]}


def test_no_narrative_items_selected_gets_an_empty_list_not_null(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["sheet"]["equipment"]["narrativeItems"] == []


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
    # sheet["spells"] is a LIST (one entry per class with spellcasting this
    # level) as of the Phase 3b-i final-review fix — a character with no
    # spellcaster classes gets an empty list, not None.
    assert resolution["sheet"]["spells"] == []
    # spellSaveDC/spellAttackBonus moved into each sheet.spells entry as of
    # Phase 3b-ii — with no spellcasting classes, sheet["spells"] is already
    # empty (asserted above), so there's no per-caster entry to check. The
    # combined slot pool is also empty for a non-caster.
    assert resolution["derived"]["spellSlots"] == {}
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_fighter_has_no_spell_choices_or_derived_spell_stats(catalog):
    resolution = resolve(_bare_class_draft("fighter"), catalog)
    spell_choice_ids = [c["id"] for c in resolution["choices"] if "spells" in c["id"]]
    assert spell_choice_ids == []
    assert resolution["sheet"]["spells"] == []
    assert resolution["derived"]["spellSlots"] == {}


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
    # sheet["spells"] is a list of one entry per spellcasting class; a
    # single-class Wizard draft has exactly one entry.
    spells = resolution["sheet"]["spells"]
    assert len(spells) == 1
    assert spells[0]["classId"] == "wizard"
    assert spells[0]["cantrips"][0]["id"] == cantrip_id
    assert spells[0]["known"][0]["id"] == spell_id


def test_derived_spell_save_dc_and_attack_bonus_use_the_spellcasting_ability(catalog):
    # spellSaveDC/spellAttackBonus moved from top-level derived scalars into
    # each sheet.spells entry as of Phase 3b-ii.
    resolution = resolve(_wizard_draft(int_score=16), catalog)
    wizard_entry = next(s for s in resolution["sheet"]["spells"] if s["classId"] == "wizard")
    # INT 16 -> +3 modifier, prof bonus 2 at level 1
    assert wizard_entry["spellSaveDC"] == 13  # 8 + 2 + 3
    assert wizard_entry["spellAttackBonus"] == 5  # 2 + 3


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
    assert resolution["sheet"]["classes"][0]["subclass"] == {"id": "life", "name": "Life"}


def test_class_with_no_subclass_selected_has_a_null_subclass_on_the_sheet(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert resolution["sheet"]["classes"][0]["subclass"] is None


def test_sheet_classes_is_a_list_with_one_entry_per_class(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    classes = resolution["sheet"]["classes"]
    assert len(classes) == 2
    assert classes[0]["id"] == "fighter" and classes[0]["level"] == 3
    assert classes[1]["id"] == "wizard" and classes[1]["level"] == 2


def test_sheet_classes_is_empty_list_when_no_class_selected(catalog):
    resolution = resolve(_empty_draft(), catalog)
    assert resolution["sheet"]["classes"] == []


def test_sheet_classes_single_class_still_carries_subclass(catalog):
    # Regression check: a single-class draft's subclass info (already
    # tested elsewhere for the OLD sheet["class"] shape) must survive
    # the list-shape change identically.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 3, "subclassId": "champion", "choices": {}}],
    )
    resolution = resolve(draft, catalog)
    classes = resolution["sheet"]["classes"]
    assert len(classes) == 1
    assert classes[0]["subclass"] == {"id": "champion", "name": "Champion"}


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


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_fixed_language_reaches_the_sheet_no_choice_offered(catalog):
    # Phase 4b Task 3: Rune Carver/BGG grants a FIXED Giant language
    # (languageProficiencies: [{"giant": True}], no choice at all).
    # engine/resolve.py's fixed_languages list-comprehension (around line
    # 1324) already reads bg.get("languages", []) unconditionally — this
    # proves that existing, UNMODIFIED consumption path genuinely works for
    # a real sourcebook (not just bundled SRD) background, with zero
    # resolve.py changes needed for this task.
    draft = _fighter_acolyte_human_draft(sources=["bgg"], background={"id": "rune-carver-bgg", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert "giant" in resolution["sheet"]["proficiencies"]["languages"]
    cids = {c["id"] for c in resolution["choices"]}
    assert not any(cid.endswith(":languages") for cid in cids if cid.startswith("background:"))


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_language_choice_reaches_the_sheet(catalog):
    # Phase 4b Task 3: Giant Foundling/BGG combines a fixed Giant grant
    # WITH a 1-language wildcard choice on the same languageProficiencies
    # entry ({"giant": True, "anyStandard": 1}). Confirms
    # _background_choice_templates' EXISTING bg.get("language_options")
    # handling (engine/resolve.py, reused via _background_choice_templates)
    # builds a real, selectable Choice for a sourcebook background exactly
    # like it already does for SRD's own bundled Acolyte — proving the
    # brief's "zero resolve.py changes needed" claim end-to-end, not just
    # via the SRD-only test above.
    draft = _fighter_acolyte_human_draft(sources=["bgg"], background={"id": "giant-foundling-bgg", "choices": {}})
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    cid = next(c["id"] for c in resolution["choices"] if c["id"] == "background:giant-foundling-bgg:languages")
    languages_choice = next(c for c in resolution["choices"] if c["id"] == cid)
    assert languages_choice["count"] == 1
    assert len(languages_choice["options"]) == 16

    draft["background"]["choices"][cid] = ["elvish"]
    resolution2 = resolve(draft, catalog)
    languages = resolution2["sheet"]["proficiencies"]["languages"]
    assert "giant" in languages  # the fixed grant
    assert "elvish" in languages  # the chosen wildcard pick


# --- Phase 4b Task 4: the 2024-style background ability-score-improvement
# choice. Aberrant Heir/EFA (official_source.py's own id
# "aberrant-heir-efa") has a STR/CON/CHA pool, confirmed against the real
# fetched data — see test_official_source.py's own grounding tests for the
# full empirical derivation (60/60 real ability-field backgrounds share
# this exact universal mechanic).

@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_ability_bonus_choice_is_offered_with_7_options(catalog):
    draft = _fighter_acolyte_human_draft(
        sources=["efa"], background={"id": "aberrant-heir-efa", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    choice = next(c for c in resolution["choices"] if c["id"] == "background:aberrant-heir-efa:ability-bonus")
    assert choice["count"] == 1
    assert choice["status"] == "pending"
    assert len(choice["options"]) == 7
    ids = {o["id"] for o in choice["options"]}
    assert "str-2+con-1" in ids  # split bundle
    assert "str-1+con-1+cha-1" in ids  # flat bundle


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_ability_bonus_split_bundle_applies_plus_2_plus_1(catalog):
    draft = _fighter_acolyte_human_draft(
        sources=["efa"],
        background={
            "id": "aberrant-heir-efa",
            "choices": {"background:aberrant-heir-efa:ability-bonus": ["str-2+con-1"]},
        },
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    scores = resolution["sheet"]["abilities"]
    # _fighter_acolyte_human_draft's default species is Human (+1 to every
    # ability), unrelated to this background choice — accounted for below.
    assert scores["STR"] == 17  # 14 base + 1 (Human) + 2 (background split)
    assert scores["CON"] == 16  # 14 base + 1 (Human) + 1 (background split)
    assert scores["DEX"] == 13  # 12 base + 1 (Human only) — unaffected by the background choice
    assert scores["CHA"] == 9  # 8 base + 1 (Human only) — not part of this bundle

    choice = next(c for c in resolution["choices"] if c["id"] == "background:aberrant-heir-efa:ability-bonus")
    assert choice["status"] == "resolved"
    assert choice["selected"] == ["str-2+con-1"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_ability_bonus_flat_bundle_applies_plus_1_to_all_three(catalog):
    draft = _fighter_acolyte_human_draft(
        sources=["efa"],
        background={
            "id": "aberrant-heir-efa",
            "choices": {"background:aberrant-heir-efa:ability-bonus": ["str-1+con-1+cha-1"]},
        },
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    scores = resolution["sheet"]["abilities"]
    # Default species is Human (+1 to every ability) — accounted for below.
    assert scores["STR"] == 16  # 14 base + 1 (Human) + 1 (background flat)
    assert scores["CON"] == 16  # 14 base + 1 (Human) + 1 (background flat)
    assert scores["CHA"] == 10  # 8 base + 1 (Human) + 1 (background flat)
    assert scores["DEX"] == 13  # 12 base + 1 (Human only) — unaffected by the background choice


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_ability_bonus_choice_combines_with_species_bonus(catalog):
    # Species and background ability bonuses both flow into the SAME early
    # ability-score pass — this exercises them stacking on the same
    # ability rather than one silently overwriting the other.
    draft = _fighter_acolyte_human_draft(
        sources=["efa"],
        species={"id": "human", "choices": {}},  # Human: +1 to every ability
        background={
            "id": "aberrant-heir-efa",
            "choices": {"background:aberrant-heir-efa:ability-bonus": ["str-2+con-1"]},
        },
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    scores = resolution["sheet"]["abilities"]
    assert scores["STR"] == 17  # 14 base + 1 (Human) + 2 (background split)
    assert scores["CON"] == 16  # 14 base + 1 (Human) + 1 (background split)
    assert scores["DEX"] == 13  # 12 base + 1 (Human only)


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_sourcebook_background_ability_bonus_duplicate_selection_does_not_double_apply(catalog):
    draft = _fighter_acolyte_human_draft(
        sources=["efa"],
        background={
            "id": "aberrant-heir-efa",
            "choices": {"background:aberrant-heir-efa:ability-bonus": ["str-2+con-1", "str-2+con-1"]},
        },
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    scores = resolution["sheet"]["abilities"]
    # 14 base + 1 (Human) + 2 (background split) = 17, NOT 19 — duplicate
    # selection must not double the background bonus.
    assert scores["STR"] == 17
    choice = next(c for c in resolution["choices"] if c["id"] == "background:aberrant-heir-efa:ability-bonus")
    assert choice["selected"] == ["str-2+con-1"]


def test_srd_only_acolyte_background_gets_no_ability_bonus_choice_safe_no_op(catalog):
    # SRD's own bundled Acolyte has no ability_bonus_options field at all
    # (2014-rules background, no ASI) — confirms this task's new machinery
    # is a genuine no-op for it, not just "happens not to break" it.
    draft = _fighter_acolyte_human_draft()
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    cids = {c["id"] for c in resolution["choices"]}
    assert not any(cid.endswith(":ability-bonus") and cid.startswith("background:") for cid in cids)
    # Acolyte's own base scores (from the fixture) pass through unmodified
    # by any background ability bonus.
    assert resolution["sheet"]["abilities"]["STR"] == 17  # 16 base + 1 (Human only)


def test_wizard_duplicate_cantrip_selection_is_deduplicated(catalog):
    # Regression test for dedup fix in commit 1aa299b: submitting the same
    # valid cantrip id multiple times (e.g. ["fire-bolt", "fire-bolt",
    # "fire-bolt"]) must resolve with only one copy, not three. The generic
    # choice-resolution loop (for tpl in choice_templates:) dedupes all
    # choice types, not just Half-Elf's ability bonus (which was the only
    # one covered by the original review). This test verifies Wizard's
    # cantrip choice gets deduplicated correctly.
    draft = _wizard_draft(
        int_score=16,  # INT 16 -> +3 mod, so cantrip count = 3
        classes=[{
            "classId": "wizard", "level": 1,
            "choices": {"class:wizard:spells-cantrips": ["fire-bolt", "fire-bolt", "fire-bolt"]},
        }],
    )
    resolution = resolve(draft, catalog)
    cantrip_choice = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-cantrips")
    # Verify the selection is deduplicated
    assert cantrip_choice["selected"] == ["fire-bolt"]
    # Status must be "pending" (only 1 of 3 cantrips selected), not
    # "resolved" from padding with duplicates
    assert cantrip_choice["status"] == "pending"
    # Confirm no spurious over-selected problem appears (the duplicate
    # selection should be silently dropped before the over-select check)
    assert not any(p["id"].startswith("over-selected-") for p in resolution["problems"])


def test_fighter_duplicate_skill_selection_is_deduplicated(catalog):
    # Regression test for dedup fix in commit 1aa299b: submitting the same
    # valid skill id twice (e.g. ["skill-athletics", "skill-athletics"])
    # must resolve with only one copy. Fighter's proficiency choice has
    # count=2, so selecting one unique skill leaves it pending.
    draft = _fighter_acolyte_human_draft(
        classes=[{
            "classId": "fighter", "level": 1,
            "choices": {"class:fighter:1:prof-choice-0": ["skill-athletics", "skill-athletics"]},
        }],
    )
    resolution = resolve(draft, catalog)
    skill_choice = next(c for c in resolution["choices"] if c["label"] == "Skill Proficiencies")
    # Verify the selection is deduplicated to a single copy
    assert skill_choice["selected"] == ["skill-athletics"]
    # Status must be "pending" (only 1 of 2 skills selected), not
    # "resolved" from padding with duplicates
    assert skill_choice["status"] == "pending"
    # Confirm no spurious over-selected problem appears
    assert not any(p["id"].startswith("over-selected-") for p in resolution["problems"])


def test_a_fully_dropped_equipment_envelope_produces_a_warning(catalog):
    # Paladin has 4 starting-equipment envelopes in the bundled SRD data,
    # of which only 2 survive build_choice_template (confirmed empirically
    # while writing this plan) — the other 2 are genuinely dropped.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "paladin", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert any("equipment" in w["id"] for w in resolution["warnings"])


def test_a_class_with_no_dropped_envelopes_has_no_such_warning(catalog):
    # Wizard has 3 starting-equipment envelopes, all 3 survive
    # build_choice_template (confirmed empirically while writing this
    # plan) — zero dropped, so no CLASS-level equipment warning should
    # appear. Scoped to the class-specific warning id (rather than "any
    # equipment warning at all") because the bundled SRD data's only
    # background, Acolyte (the default from _fighter_acolyte_human_draft),
    # itself has a genuinely-dropped envelope (1 total, 0 survived) and so
    # always contributes its own equipment-envelope-dropped-background-*
    # warning — that's correct, separate behavior, not something this
    # class-focused test is about.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "wizard", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert not any(w["id"] == "equipment-envelope-dropped-class-wizard" for w in resolution["warnings"])


def test_a_genuinely_clean_resolution_has_zero_warnings(catalog):
    # Coverage gap from review: no test asserts a fully clean
    # resolution["warnings"] == []. Wizard has 0 dropped equipment
    # envelopes (3 total, all 3 survive). Passing background with no "id"
    # key (e.g. {"choices": {}}) makes bg_id become None and skips the
    # entire background-equipment block, avoiding Acolyte's own dropped
    # envelope entirely. Result: warnings == [] everywhere.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 1, "choices": {}}],
        background={"choices": {}},
    )
    resolution = resolve(draft, catalog)
    assert resolution["warnings"] == []


def test_multiclass_proficiency_bonus_comes_from_total_level(catalog):
    # Fighter 1 alone -> prof bonus 2. Add Wizard 4 -> total level 5 ->
    # prof bonus 3, even though Fighter's OWN level (1) would only be 2.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 1, "choices": {}},
            {"classId": "wizard", "level": 4, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["proficiencyBonus"] == 3


def test_multiclass_hit_point_max_matches_hit_point_max_multiclass(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    con_mod = (14 - 10) // 2
    expected = hit_point_max_multiclass(
        [{"hit_die": 10, "level": 3, "hp_rolls": {}}, {"hit_die": 6, "level": 2, "hp_rolls": {}}],
        con_modifier=con_mod, hp_type="fixed",
    )
    assert resolution["derived"]["hitPointMax"] == expected


def test_multiclass_hit_dice_lists_every_class(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "wizard", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["hitDice"] == "3d10 + 2d6"


def test_secondary_class_multiclass_proficiency_choice_is_generated(catalog):
    # Rogue's multi_classing.proficiency_choices grants a skill choice
    # when taken as a SECONDARY class (confirmed empirically: choose 1
    # from an 11-skill list) — distinct from Rogue's own level-1
    # proficiency_choices (a bigger 4-skill choice), which only applies
    # when Rogue is the FIRST class.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    mc_choice = next((c for c in resolution["choices"] if c["id"] == "class:rogue:multiclass-prof-choice-0"), None)
    assert mc_choice is not None
    assert mc_choice["count"] == 1
    assert any(o["id"] == "skill-stealth" for o in mc_choice["options"])


def test_primary_class_does_not_get_a_multiclass_proficiency_choice(catalog):
    # Rogue as the FIRST class should NOT also get the multiclass-only
    # choice template — only its normal level-1 prof-choice-0.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "rogue", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    assert not any(c["id"] == "class:rogue:multiclass-prof-choice-0" for c in resolution["choices"])


def test_secondary_class_fixed_multiclass_proficiencies_appear_on_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    profs = resolution["sheet"]["proficiencies"]
    assert "light-armor" in profs["armor"]
    assert "thieves-tools" in profs["tools"]
    # Fighter (primary) should contribute ITS full level-1 grant too:
    assert "martial-weapons" in profs["weapons"]


def test_multiclass_prerequisite_unmet_is_a_problem_when_preference_on(catalog):
    # Wizard requires INT >= 13 to multiclass in/out of. Give a low INT.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "wizard", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 8, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    assert any(p["id"] == "multiclass-prerequisite-unmet-wizard" for p in resolution["problems"])
    # The class must still be FULLY resolved despite the unmet prerequisite
    # (never hidden) — confirmed via Wizard's hit die (1d6) still showing up
    # in the combined hitDice string.
    assert resolution["derived"]["hitDice"] == "2d10 + 1d6"


def test_multiclass_prerequisite_check_skipped_when_preference_off(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "wizard", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 8, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": False}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"].startswith("multiclass-prerequisite-unmet") for p in resolution["problems"])


def test_fighter_secondary_class_prerequisite_options_str_or_dex(catalog):
    # Fighter's multiclass prereq is "choose 1 of STR>=13 / DEX>=13" —
    # confirm meeting DEX alone (not STR) is sufficient.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 2, "choices": {}},
            {"classId": "fighter", "level": 1, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 8, "DEX": 14, "CON": 14, "INT": 14, "WIS": 12, "CHA": 8}},
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"] == "multiclass-prerequisite-unmet-fighter" for p in resolution["problems"])


# --- Task 4 review-fix regression tests ---
#
# Finding 1: the proficiency-bucketing loop gated only on
# `c["source"]["kind"] == "class"`, which also covers feature subfeature
# choices, ASI choices, and spell choices — not just proficiency choices.
# `_categorize_proficiency`'s substring check ("armor" in prof_id) then
# miscategorized a selected spell like `mage-armor` into
# sheet.proficiencies.armor right alongside real armor proficiencies.
#
# Finding 2: `_multiclass_prerequisite_problems` ran for every resolved
# class with no guard for "this character only has one class, so
# multiclassing prerequisites don't apply" — a single-class Wizard with
# low INT and the preference on produced a spurious
# multiclass-prerequisite-unmet-wizard problem.

def test_non_proficiency_class_choices_do_not_pollute_proficiency_buckets(catalog):
    # Fighter 4 / Wizard 1 with REAL selections in every non-proficiency
    # class-choice slot: an ASI, a feature subfeature (fighting style), and
    # both wizard spell choices (including mage-armor, the exact spell the
    # reviewer found leaking into `armor`). None of these ids should ever
    # land in armor/weapons/tools — only genuine proficiency ids may.
    cantrip_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 0 and any(c["index"] == "wizard" for c in s["classes"])
    )
    draft = _fighter_acolyte_human_draft(
        classes=[
            {
                "classId": "fighter", "level": 4,
                "choices": {
                    "class:fighter:4:asi": ["str-plus-2"],
                    "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-defense"],
                },
            },
            {
                "classId": "wizard", "level": 1,
                "choices": {
                    "class:wizard:spells-cantrips": [cantrip_id],
                    "class:wizard:spells-known": ["mage-armor"],
                },
            },
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 16, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    profs = resolution["sheet"]["proficiencies"]
    leaking_ids = {"mage-armor", cantrip_id, "str-plus-2", "fighter-fighting-style-defense"}
    for bucket in ("armor", "weapons", "tools"):
        assert not (leaking_ids & set(profs[bucket])), f"{bucket} leaked a non-proficiency id: {profs[bucket]}"
    # The real proficiencies must still be there — this is a fix for the
    # pollution, not a regression on genuine grants.
    assert "all-armor" in profs["armor"]
    assert "shields" in profs["armor"]
    assert "martial-weapons" in profs["weapons"]
    assert "simple-weapons" in profs["weapons"]


def test_single_class_draft_never_gets_a_multiclass_prerequisite_problem(catalog):
    # A single-class Wizard with INT 10 (below the multiclass prerequisite
    # of INT >= 13) and the preference ON. Multiclassing prerequisites
    # apply only when actually multiclassing — a lone class should never
    # trigger this problem, no matter the preference or ability scores.
    draft = _bare_class_draft(
        "wizard",
        preferences={"advancementType": "milestone", "hitPointType": "fixed", "usePrerequisites": {"feats": True, "multiclass": True}},
    )
    resolution = resolve(draft, catalog)
    assert not any(p["id"].startswith("multiclass-prerequisite-unmet") for p in resolution["problems"])


# --- Final-review fix wave (Phase 3b-i) ---
#
# Finding 1: `_class_choice_templates` (the PRIMARY-only level-1
# proficiency CHOICE, e.g. Rogue's "choose 4 skills") was called
# unconditionally for every resolved class, including secondary ones —
# even though the FIXED-grant path 30 lines below was already correctly
# gated on `rc["index"] == 0`. A secondary Wizard (which grants no skill
# proficiencies at all when multiclassed into) wrongly got a
# choose-2-skills card, and a secondary Rogue got BOTH its primary
# choose-4 card AND the correct multiclass choose-1 card.
#
# Finding 2: the cantrip/known-spell Choice lookup used only the PRIMARY
# class's cls_id, so a secondary spellcaster's fully-selected spells never
# reached sheet["spells"] or any export, even though the Choice itself was
# resolved in resolution["choices"].

def test_secondary_wizard_does_not_get_the_primary_level_1_proficiency_choice(catalog):
    # Fighter 2 / Wizard 1: Wizard has proficiency_choices (a level-1
    # choose-2-skills grant) but NO multi_classing.proficiency_choices, so
    # as a secondary class it should get neither choice template at all.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "wizard", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    choice_ids = [c["id"] for c in resolution["choices"]]
    assert "class:wizard:1:prof-choice-0" not in choice_ids
    assert "class:wizard:multiclass-prof-choice-0" not in choice_ids


def test_secondary_rogue_gets_only_the_multiclass_proficiency_choice(catalog):
    # Fighter 2 / Rogue 1: Rogue as a SECONDARY class must get only its
    # multiclass-prof-choice-0 (choose 1) — not also its primary-only
    # 1:prof-choice-0 (choose 4), which would grant 5 skills instead of 1.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    choice_ids = [c["id"] for c in resolution["choices"]]
    assert "class:rogue:1:prof-choice-0" not in choice_ids
    mc_choice = next(c for c in resolution["choices"] if c["id"] == "class:rogue:multiclass-prof-choice-0")
    assert mc_choice["count"] == 1


def test_secondary_class_does_not_get_the_primary_proficiency_choice(catalog):
    # Mirror of test_primary_class_does_not_get_a_multiclass_proficiency_choice:
    # confirms the gating is symmetric in both directions, using Rogue (which
    # has both a primary-only and a multiclass-only choice) as the primary
    # class this time — Rogue as PRIMARY must keep its normal prof-choice-0.
    draft = _fighter_acolyte_human_draft(classes=[{"classId": "rogue", "level": 1, "choices": {}}])
    resolution = resolve(draft, catalog)
    choice_ids = [c["id"] for c in resolution["choices"]]
    assert "class:rogue:1:prof-choice-0" in choice_ids
    assert "class:rogue:multiclass-prof-choice-0" not in choice_ids


def test_single_class_spellcaster_spells_appear_as_a_list_of_one(catalog):
    # Regression, in the new shape: a single-class caster's spells still
    # reach the sheet, just as one entry in a list rather than a bare object.
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
    spells = resolution["sheet"]["spells"]
    assert isinstance(spells, list)
    assert len(spells) == 1
    assert spells[0]["classId"] == "wizard"
    assert spells[0]["cantrips"][0]["id"] == cantrip_id
    assert spells[0]["known"][0]["id"] == spell_id


def test_secondary_class_spellcaster_spells_appear_in_the_sheet(catalog):
    # The bug fix itself: Fighter 3 / Wizard 2, with Wizard's cantrips and
    # known spells fully selected. Before the fix, sheet["spells"] never
    # found Wizard's choices because the lookup only checked the primary
    # class's cls_id ("fighter") — the selections silently vanished from the
    # sheet and every export despite being `status: "resolved"` in
    # resolution["choices"].
    cantrip_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 0 and any(c["index"] == "wizard" for c in s["classes"])
    )
    spell_id = next(
        s["index"] for s in catalog.spells.values()
        if s["level"] == 1 and any(c["index"] == "wizard" for c in s["classes"])
    )
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {
                "classId": "wizard", "level": 2,
                "choices": {
                    "class:wizard:spells-cantrips": [cantrip_id],
                    "class:wizard:spells-known": [spell_id],
                },
            },
        ],
        abilities={"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 16, "WIS": 12, "CHA": 8}},
    )
    resolution = resolve(draft, catalog)
    spells = resolution["sheet"]["spells"]
    wizard_entry = next((e for e in spells if e["classId"] == "wizard"), None)
    assert wizard_entry is not None, f"wizard's spells never made it into sheet['spells']: {spells}"
    assert wizard_entry["cantrips"][0]["id"] == cantrip_id
    assert wizard_entry["known"][0]["id"] == spell_id
    # spellSaveDC/spellAttackBonus moved into each sheet.spells entry as of
    # Phase 3b-ii — Wizard (secondary) is a real caster and gets its own
    # values, using its own spellcasting ability (INT) and the character's
    # total-level proficiency bonus. Total level 5 (Fighter 3 + Wizard 2) ->
    # prof bonus +3; INT 16 -> +3 modifier -> DC 8+3+3=14, attack +3+3=6.
    assert wizard_entry["spellSaveDC"] == 14
    assert wizard_entry["spellAttackBonus"] == 6


def test_non_caster_secondary_class_adds_no_spurious_spell_entry(catalog):
    # Fighter 2 / Rogue 1: neither class is a spellcaster, so
    # sheet["spells"] must be an empty list — not an entry with empty
    # cantrips/known for a class that was never a caster in the first place.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 2, "choices": {}},
            {"classId": "rogue", "level": 1, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["sheet"]["spells"] == []


def test_single_caster_spell_slots_match_their_own_level_table(catalog):
    # Sorcerer, not Wizard: Wizard is the hardcoded internal anchor class
    # (_MULTICLASS_SLOT_TABLE_ANCHOR_CLASS in engine/spells.py) that
    # multiclass_spell_slots looks up under the hood, so a single-class
    # Wizard test would compare the implementation's own lookup against
    # itself and could never fail regardless of correctness. Sorcerer is a
    # different full-caster class with (confirmed empirically) the exact
    # same slot progression as Wizard at level 5, so this is a real,
    # non-tautological regression check.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "sorcerer", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 16}},
    )
    resolution = resolve(draft, catalog)
    sorcerer_lvl5 = catalog.class_level_row("sorcerer", 5)["spellcasting"]
    expected = {str(n): sorcerer_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if sorcerer_lvl5[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_two_full_casters_share_a_combined_slot_pool(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 3, "choices": {}},
            {"classId": "sorcerer", "level": 2, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 14, "WIS": 10, "CHA": 14}},
    )
    resolution = resolve(draft, catalog)
    wizard_lvl5 = catalog.class_level_row("wizard", 5)["spellcasting"]  # combined level 3+2=5
    expected = {str(n): wizard_lvl5[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl5[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected


def test_warlock_alongside_a_full_caster_keeps_pact_magic_separate(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "wizard", "level": 3, "choices": {}},
            {"classId": "warlock", "level": 3, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 14, "WIS": 10, "CHA": 14}},
    )
    resolution = resolve(draft, catalog)
    # Combined pool should reflect ONLY Wizard's level (3), Warlock excluded.
    wizard_lvl3 = catalog.class_level_row("wizard", 3)["spellcasting"]
    expected_shared = {str(n): wizard_lvl3[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl3[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected_shared
    warlock_lvl3 = catalog.class_level_row("warlock", 3)["spellcasting"]
    expected_warlock = {str(n): warlock_lvl3[f"spell_slots_level_{n}"] for n in range(1, 10) if warlock_lvl3[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["warlockSpellSlots"] == expected_warlock
    assert resolution["derived"]["spellSlots"] != resolution["derived"]["warlockSpellSlots"]


def test_non_caster_multiclass_has_empty_spell_slots(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 3, "choices": {}},
            {"classId": "rogue", "level": 2, "choices": {}},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["derived"]["spellSlots"] == {}
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_single_half_caster_at_odd_level_uses_its_own_slot_table(catalog):
    # PHB 164: the combined multiclass table (half casters contributing
    # level // 2 to a shared level, looked up in a full caster's own
    # table) applies ONLY when more than one class grants spell slots. A
    # single-class Paladin at an odd level must use Paladin's own level-5
    # row directly, NOT round level 5 down to combined level 2 and look
    # that up in the shared table (which would silently undercount).
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "paladin", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 16}},
    )
    resolution = resolve(draft, catalog)
    paladin_lvl5 = catalog.class_level_row("paladin", 5)["spellcasting"]
    expected = {str(n): paladin_lvl5.get(f"spell_slots_level_{n}", 0) for n in range(1, 10) if paladin_lvl5.get(f"spell_slots_level_{n}", 0) > 0}
    assert expected == {"1": 4, "2": 2}  # Paladin's real level-5 row, per PHB.
    assert resolution["derived"]["spellSlots"] == expected
    assert resolution["derived"]["warlockSpellSlots"] == {}


def test_non_caster_class_alongside_one_half_caster_still_uses_its_own_table(catalog):
    # Fighter grants no spell slots at all, so Paladin remains the ONLY
    # slot-granting class here — Fighter's presence must not change the
    # result at all compared to a single-class Paladin 5.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 5, "choices": {}},
            {"classId": "paladin", "level": 5, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 16}},
    )
    resolution = resolve(draft, catalog)
    paladin_lvl5 = catalog.class_level_row("paladin", 5)["spellcasting"]
    expected = {str(n): paladin_lvl5.get(f"spell_slots_level_{n}", 0) for n in range(1, 10) if paladin_lvl5.get(f"spell_slots_level_{n}", 0) > 0}
    assert expected == {"1": 4, "2": 2}
    assert resolution["derived"]["spellSlots"] == expected


def test_two_slot_granting_classes_still_use_the_combined_round_down_table(catalog):
    # Genuine two-caster case (Cleric, a full caster + Paladin, a half
    # caster): the round-down combined-level table is exactly the right
    # rule here, and must keep applying — this is not touched by the
    # single-slot-granting-class fix above.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "cleric", "level": 4, "choices": {}},
            {"classId": "paladin", "level": 4, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 10, "CON": 12, "INT": 10, "WIS": 16, "CHA": 13}},
    )
    resolution = resolve(draft, catalog)
    combined_level = 4 + 4 // 2  # Cleric full (4) + Paladin half (4 // 2 = 2) = 6
    wizard_lvl6 = catalog.class_level_row("wizard", combined_level)["spellcasting"]
    expected = {str(n): wizard_lvl6[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl6[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected


def test_level_1_half_caster_alongside_another_half_caster_is_not_double_counted(catalog):
    # Regression for the final-review finding: slot-granting classification
    # was done by class-id SET MEMBERSHIP (cls_id in FULL_CASTER_CLASSES |
    # HALF_CASTER_CLASSES) rather than by an ACTUAL current-level grant. A
    # level-1 Paladin has NO Spellcasting feature yet (half casters gain it
    # at level 2 per RAW) and so grants ZERO slots — Ranger 5 is therefore
    # the ONLY class actually granting slots here, and its own real
    # level-5 row must be used directly rather than the combined
    # round-down table ((1 // 2) + 5 = 5, which would wrongly produce
    # Wizard's level-5 row of {"1": 4, "2": 3, "3": 2}).
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "paladin", "level": 1, "choices": {}},
            {"classId": "ranger", "level": 5, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 13, "CHA": 13}},
    )
    resolution = resolve(draft, catalog)
    ranger_lvl5 = catalog.class_level_row("ranger", 5)["spellcasting"]
    expected = {str(n): ranger_lvl5.get(f"spell_slots_level_{n}", 0) for n in range(1, 10) if ranger_lvl5.get(f"spell_slots_level_{n}", 0) > 0}
    assert expected == {"1": 4, "2": 2}  # Ranger's real level-5 row, per PHB — pinned as a literal.
    assert resolution["derived"]["spellSlots"] == expected


def test_warlock_only_character_has_empty_shared_pool_and_its_own_pact_magic(catalog):
    # No test previously resolved a single-class Warlock in isolation —
    # confirm the shared pool stays empty (Warlock is never a
    # slot-granting class for the combined/single-class table, per RAW)
    # while warlockSpellSlots reflects Warlock's own real level-5 Pact
    # Magic row from the catalog.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "warlock", "level": 5, "choices": {}}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 16}},
    )
    resolution = resolve(draft, catalog)
    warlock_lvl5 = catalog.class_level_row("warlock", 5)["spellcasting"]
    expected_warlock = {str(n): warlock_lvl5.get(f"spell_slots_level_{n}", 0) for n in range(1, 10) if warlock_lvl5.get(f"spell_slots_level_{n}", 0) > 0}
    assert resolution["derived"]["spellSlots"] == {}
    assert resolution["derived"]["warlockSpellSlots"] == expected_warlock


def test_three_caster_classes_combined_pool_and_independent_pact_magic(catalog):
    # No genuine 3-class test previously existed. Cleric 4 (full) + Paladin
    # 4 (half) + Warlock 3 (Pact Magic, entirely separate per RAW): the
    # shared pool must reflect ONLY Cleric+Paladin's combined level
    # (4 + 4 // 2 = 6, a full caster's own level-6 row), completely
    # unaffected by Warlock's presence, and warlockSpellSlots must reflect
    # Warlock's own level-3 row, completely independent of the other two.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "cleric", "level": 4, "choices": {}},
            {"classId": "paladin", "level": 4, "choices": {}},
            {"classId": "warlock", "level": 3, "choices": {}},
        ],
        abilities={"method": "manual", "base": {"STR": 14, "DEX": 10, "CON": 12, "INT": 10, "WIS": 16, "CHA": 13}},
    )
    resolution = resolve(draft, catalog)
    combined_level = 4 + 4 // 2  # Cleric full (4) + Paladin half (4 // 2 = 2) = 6
    wizard_lvl6 = catalog.class_level_row("wizard", combined_level)["spellcasting"]
    expected_shared = {str(n): wizard_lvl6[f"spell_slots_level_{n}"] for n in range(1, 10) if wizard_lvl6[f"spell_slots_level_{n}"] > 0}
    assert resolution["derived"]["spellSlots"] == expected_shared

    warlock_lvl3 = catalog.class_level_row("warlock", 3)["spellcasting"]
    expected_warlock = {str(n): warlock_lvl3.get(f"spell_slots_level_{n}", 0) for n in range(1, 10) if warlock_lvl3.get(f"spell_slots_level_{n}", 0) > 0}
    assert resolution["derived"]["warlockSpellSlots"] == expected_warlock


def test_derived_no_longer_has_top_level_spell_save_dc_or_attack_bonus(catalog):
    resolution = resolve(_fighter_acolyte_human_draft(), catalog)
    assert "spellSaveDC" not in resolution["derived"]
    assert "spellAttackBonus" not in resolution["derived"]


def test_each_caster_in_sheet_spells_carries_its_own_save_dc_and_attack_bonus(catalog):
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "wizard", "level": 3, "choices": {
            "class:wizard:spells-cantrips": ["fire-bolt"],
            "class:wizard:spells-known": ["magic-missile"],
        }}],
        abilities={"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 10, "CHA": 10}},
    )
    resolution = resolve(draft, catalog)
    wizard_entry = next(s for s in resolution["sheet"]["spells"] if s["classId"] == "wizard")
    # INT 16 -> +3 modifier; prof bonus at level 3 is 2 -> DC 8+2+3=13, attack +2+3=5.
    assert wizard_entry["spellSaveDC"] == 13
    assert wizard_entry["spellAttackBonus"] == 5


def test_leveling_down_prunes_a_now_unreachable_asi_choice(catalog):
    # Fighter's ASI-granting levels include level 4. A level-4 ASI
    # selection, then leveled back down to 3, should be pruned. Confirmed
    # directly against the real catalog while writing this plan: at
    # level 4 the choice class:fighter:4:asi exists in `choices`; at
    # level 3 it doesn't, while the raw selection is still sitting in
    # classes[0]["choices"] (SET_CLASS_LEVEL never touches `choices`).
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 4, "choices": {
            "class:fighter:4:asi": ["str-plus-2"],
        }}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []  # not stale yet, level 4 is current

    draft["classes"][0]["level"] = 3  # level back down, selection left in place
    resolution = resolve(draft, catalog)
    pruned_ids = [p["choiceId"] for p in resolution["pruned"]]
    assert "class:fighter:4:asi" in pruned_ids
    pruned_entry = next(p for p in resolution["pruned"] if p["choiceId"] == "class:fighter:4:asi")
    assert "class:fighter:4:asi" in pruned_entry["reason"]


def test_clearing_a_subclass_prunes_its_subclass_gated_feature_choice(catalog):
    # Champion (Fighter's only bundled subclass) grants a SECOND Fighting
    # Style choice at level 10 (class:fighter:10:feature:additional-
    # fighting-style) on top of the base class's level-1 one — confirmed
    # directly against the real catalog while writing this plan. Clearing
    # subclassId (SET_SUBCLASS with undefined, e.g. re-picking "no
    # subclass") leaves the old selection in place but the level-10
    # feature choice stops being generated, since it's subclass-gated;
    # the base level-1 Fighting Style choice (not subclass-specific)
    # correctly stays reachable and unpruned.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 10, "subclassId": "champion", "choices": {
            "class:fighter:1:feature:fighter-fighting-style": ["fighting-style-defense"],
            "class:fighter:10:feature:additional-fighting-style": ["fighting-style-dueling"],
        }}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []

    draft["classes"][0]["subclassId"] = None  # clear the subclass, selections left in place
    resolution = resolve(draft, catalog)
    pruned_ids = [p["choiceId"] for p in resolution["pruned"]]
    assert "class:fighter:10:feature:additional-fighting-style" in pruned_ids
    assert "class:fighter:1:feature:fighter-fighting-style" not in pruned_ids  # base class feature, still reachable


def test_pruning_a_multiclass_choice_does_not_disturb_the_other_class(catalog):
    # all_selections is a flat dict merged across every resolved class, so
    # this pins that a stale selection on ONE class in a multiclass draft
    # is detected in isolation — it neither leaks into the other class's
    # own choice ids nor disturbs that class's own resolution. Fighter
    # 4/Wizard 3: Fighter's level-4 ASI selection, Wizard's own cantrips
    # and prepared spells submitted normally (with the base draft's INT
    # 10 -> +0 modifier, Wizard 3's known-spell count is 3). Confirmed
    # directly against the real catalog while writing this test.
    draft = _fighter_acolyte_human_draft(
        classes=[
            {"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": ["str-plus-2"]}},
            {"classId": "wizard", "level": 3, "choices": {
                "class:wizard:spells-cantrips": ["acid-splash", "chill-touch", "dancing-lights"],
                "class:wizard:spells-known": ["alarm", "burning-hands", "charm-person"],
            }},
        ],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []  # level 4 is current, ASI still reachable

    draft["classes"][0]["level"] = 3  # level Fighter down, selection left in place
    resolution = resolve(draft, catalog)
    pruned_ids = [p["choiceId"] for p in resolution["pruned"]]
    assert pruned_ids == ["class:fighter:4:asi"]  # only Fighter's stale ASI, nothing Wizard-related

    wizard_cantrips = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-cantrips")
    wizard_known = next(c for c in resolution["choices"] if c["id"] == "class:wizard:spells-known")
    assert wizard_cantrips["status"] == "resolved"
    assert wizard_cantrips["selected"] == ["acid-splash", "chill-touch", "dancing-lights"]
    assert wizard_known["status"] == "resolved"
    assert wizard_known["selected"] == ["alarm", "burning-hands", "charm-person"]


def test_a_stale_choice_id_with_an_empty_selection_is_not_flagged_as_pruned(catalog):
    # Locks in the `if selected and ...` guard in the pruned list
    # comprehension: an empty list contributes nothing regardless of
    # staleness, so it shouldn't be flagged. A future refactor to a
    # simpler-looking `if choice_id not in current_template_ids` (dropping
    # the truthiness check) would flag this and fail here.
    draft = _fighter_acolyte_human_draft(
        classes=[{"classId": "fighter", "level": 3, "choices": {"class:fighter:4:asi": []}}],
    )
    resolution = resolve(draft, catalog)
    assert resolution["pruned"] == []


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 2) — skill/tool proficiency CHOICES, including
# the "any N" wildcard, flowing from _background_choice_templates all the
# way through to sheet.proficiencies. Mirrors the species-side coverage
# above (test_dwarf_tool_proficiency_choice_flows_into_sheet_tools) — the
# same generic-choice-selection pass in resolve() needed a background-kind
# branch added alongside the existing class/species ones, confirmed by
# tracing it end to end here rather than assumed from the Choice template
# existing.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_enumerated_background_skill_choice_appears_as_a_resolvable_choice(catalog):
    # Cloistered Scholar/SCAG: fixed History + choose 1 of {arcana, nature,
    # religion}. The fixed skill must NOT itself appear as a choice option
    # set member choice; only the "choose" portion becomes a Choice.
    draft = _fighter_acolyte_human_draft(
        sources=["scag"], background={"id": "cloistered-scholar-scag", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    prof_cid = next((cid for cid in cids if cid.startswith("background:cloistered-scholar-scag:") and "proficiency-choice" in cid), None)
    assert prof_cid is not None, f"expected a background proficiency choice, got: {cids}"
    choice = next(c for c in resolution["choices"] if c["id"] == prof_cid)
    assert choice["count"] == 1
    assert {o["id"] for o in choice["options"]} == {"skill-arcana", "skill-nature", "skill-religion"}
    assert choice["status"] == "pending"


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_selecting_a_background_skill_choice_option_lands_it_on_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(
        sources=["scag"], background={"id": "cloistered-scholar-scag", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    prof_cid = next(cid for cid in {c["id"] for c in resolution["choices"]}
                     if cid.startswith("background:cloistered-scholar-scag:") and "proficiency-choice" in cid)

    draft["background"]["choices"][prof_cid] = ["skill-arcana"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    skills = resolution2["sheet"]["proficiencies"]["skills"]
    assert "skill-arcana" in skills
    assert "skill-history" in skills  # the fixed grant, unaffected


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_selecting_an_enumerated_background_tool_choice_option_lands_it_on_the_sheet(catalog):
    # Archaeologist/ToA: choose 1 of {navigator's tools, cartographer's
    # tools} — a purely literal-name enumerated tool choice.
    draft = _fighter_acolyte_human_draft(
        sources=["toa"], background={"id": "archaeologist-toa", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    prof_cid = next(cid for cid in {c["id"] for c in resolution["choices"]}
                     if cid.startswith("background:archaeologist-toa:") and "proficiency-choice" in cid)

    draft["background"]["choices"][prof_cid] = ["cartographers-tools"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    assert "cartographers-tools" in resolution2["sheet"]["proficiencies"]["tools"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_any_n_wildcard_skill_choice_on_a_background_offers_every_skill(catalog):
    # Custom Background/PHB: {"any": 2} — no enumerated list, sourced from
    # reference_data.SKILL_NAMES via choices.py's any_skill option_set_type,
    # the SAME mechanism Phase 4a built for races, reused unmodified.
    from catalog.reference_data import SKILL_NAMES
    draft = _fighter_acolyte_human_draft(
        sources=["phb"], background={"id": "custom-background-phb", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    prof_cid = next(cid for cid in cids if cid.startswith("background:custom-background-phb:") and "proficiency-choice" in cid)
    choice = next(c for c in resolution["choices"] if c["id"] == prof_cid)
    assert choice["count"] == 2
    assert {o["id"] for o in choice["options"]} == set(SKILL_NAMES.keys())

    draft["background"]["choices"][prof_cid] = ["skill-athletics", "skill-persuasion"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    assert {"skill-athletics", "skill-persuasion"} <= set(resolution2["sheet"]["proficiencies"]["skills"])


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_any_gaming_set_wildcard_tool_choice_on_a_background_offers_only_gaming_sets(catalog):
    # Noble/PHB: {"anyGamingSet": 1} — the wildcard shape races never had
    # (Phase 4a's any_tool + tool_category filter, reused unmodified, just
    # pointed at reference_data.TOOLS' existing "Gaming Sets" category).
    draft = _fighter_acolyte_human_draft(
        sources=["phb"], background={"id": "noble-phb", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    prof_cid = next(cid for cid in cids if cid.startswith("background:noble-phb:") and "proficiency-choice" in cid)
    choice = next(c for c in resolution["choices"] if c["id"] == prof_cid)
    assert choice["count"] == 1
    assert {o["id"] for o in choice["options"]} == {"dice-set", "playing-card-set"}

    draft["background"]["choices"][prof_cid] = ["dice-set"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    assert "dice-set" in resolution2["sheet"]["proficiencies"]["tools"]


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_background_with_two_simultaneous_wildcard_choices_produces_two_selectable_choices(catalog):
    # Vizier/PSA: {"anyArtisansTool": 1, "anyMusicalInstrument": 1} on one
    # raw entry — must surface as TWO independent, independently-selectable
    # Choices, not one overwriting the other.
    draft = _fighter_acolyte_human_draft(
        sources=["psa"], background={"id": "vizier-psa", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    prof_cids = [c["id"] for c in resolution["choices"]
                 if c["id"].startswith("background:vizier-psa:") and "proficiency-choice" in c["id"]]
    assert len(prof_cids) == 2

    draft["background"]["choices"][prof_cids[0]] = ["smiths-tools"]
    draft["background"]["choices"][prof_cids[1]] = ["lute"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    tools = set(resolution2["sheet"]["proficiencies"]["tools"])
    assert {"smiths-tools", "lute"} <= tools


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 5) — the starting equipment PACKAGE CHOICE (A
# or B), end to end through resolve(). Confirms the brief's own central
# claim (needs zero resolve.py/choices.py changes) genuinely holds: the
# EXISTING _equipment_choice_templates/starting_equipment_options pathway
# (unchanged) and catalog/choices.py's EXISTING "multiple" bundle mechanism
# (unchanged) already produce a correct, selectable Choice from what
# official_source.py now populates.
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_equipment_package_choice_becomes_a_two_option_multiple_bundle_choice(catalog):
    draft = _fighter_acolyte_human_draft(sources=["efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    equip_cid = next((cid for cid in cids if cid.startswith("background:aberrant-heir-efa:") and "equipment-choice" in cid), None)
    assert equip_cid is not None, f"expected an equipment package choice, got: {cids}"
    equip_choice = next(c for c in resolution["choices"] if c["id"] == equip_cid)
    assert len(equip_choice["options"]) == 2  # package A, package B
    assert equip_choice["status"] == "pending"


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_selecting_the_item_heavy_equipment_package_lands_its_real_items_on_the_sheet(catalog):
    # Selecting bundle A (dagger, disguise kit, costume, traveler's
    # clothes, 16 GP) must land the four REAL catalog items on the sheet's
    # chosen equipment — confirms the compound "+"-joined id genuinely
    # round-trips through engine/resolve.py's existing, unchanged
    # _chosen_equipment/_gather_equipped_items.
    draft = _fighter_acolyte_human_draft(sources=["efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    equip_cid = next(cid for cid in {c["id"] for c in resolution["choices"]}
                      if cid.startswith("background:aberrant-heir-efa:") and "equipment-choice" in cid)
    equip_choice = next(c for c in resolution["choices"] if c["id"] == equip_cid)
    item_bundle_option = next(o for o in equip_choice["options"] if "+" in o["id"])

    draft["background"]["choices"][equip_cid] = [item_bundle_option["id"]]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    chosen_ids = {i["itemId"] for i in resolution2["sheet"]["equipment"]["chosen"]}
    assert {"dagger", "disguise-kit", "clothes-costume", "clothes-travelers"} <= chosen_ids
    # The synthetic "16 GP" bundle member is deliberately NOT among the
    # real catalog item ids above (it isn't a real item — see
    # test_selecting_a_gold_bundle_member_reaches_the_sheet, Task 5b: it
    # reaches the sheet instead via sheet["startingGold"]).
    assert "gp-16" not in chosen_ids


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_selecting_the_gold_only_equipment_package_produces_no_problems(catalog):
    # Bundle B (50 GP only) is a single-member "multiple" bundle — selecting
    # it must resolve cleanly (no crash, no reported problem). The gold
    # itself lands on sheet["startingGold"] (Task 5b), not as a fake
    # catalog item in "chosen" — see test_selecting_a_gold_bundle_member_
    # reaches_the_sheet.
    draft = _fighter_acolyte_human_draft(sources=["efa"], background={"id": "aberrant-heir-efa", "choices": {}})
    resolution = resolve(draft, catalog)
    equip_cid = next(cid for cid in {c["id"] for c in resolution["choices"]}
                      if cid.startswith("background:aberrant-heir-efa:") and "equipment-choice" in cid)
    equip_choice = next(c for c in resolution["choices"] if c["id"] == equip_cid)
    gold_only_option = next(o for o in equip_choice["options"] if o["id"] == "gp-50")

    draft["background"]["choices"][equip_cid] = [gold_only_option["id"]]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []


@pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")
def test_athlete_mot_two_independent_equipment_choices_are_both_selectable(catalog):
    # Athlete/MOT: two independent a/b entries in its raw startingEquipment
    # must surface as two independent, independently-selectable Choices —
    # the same "don't flatten independent choices together" pattern already
    # proven for proficiency wildcards
    # (test_background_with_two_simultaneous_wildcard_choices_produces_two_selectable_choices).
    draft = _fighter_acolyte_human_draft(
        sources=["mot"], background={"id": "athlete-mot", "choices": {}},
    )
    resolution = resolve(draft, catalog)
    equip_cids = [c["id"] for c in resolution["choices"]
                  if c["id"].startswith("background:athlete-mot:") and "equipment-choice" in c["id"]]
    assert len(equip_cids) == 2
    for cid in equip_cids:
        choice = next(c for c in resolution["choices"] if c["id"] == cid)
        assert len(choice["options"]) == 2
