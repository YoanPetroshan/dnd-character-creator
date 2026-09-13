"""Tests for chargen.build — Draft in, playable character sheet out.

The single most important test here is `RoundTripTest`: it takes a real
draft, runs it through `build()`, hands the result to the *real*
`library.save()` / `copy_to_campaign()`, and then asserts the *real* running
game's own parsers (`engine.state.party_names`, `engine.local_context.read_hp`)
read it back correctly. Everything else in this file is unit-level; that one
is the proof the whole chain connects.

`chargen/` itself may not import `library` or `engine` (tests/test_chargen_
isolation.py enforces the first two, the plan's architecture the third) —
this file is outside `chargen/`, so it is where those imports belong.
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from chargen.build import _dedup, build
from chargen.catalog import Catalog
from chargen.model import AbilityChoice, Background, ItemRef, Race, Subrace, Trait
from chargen.validate import apply_ability_bonuses

SCRIPTS = str(Path(__file__).resolve().parent.parent / "skills" / "dnd" / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


# ── draft helpers ───────────────────────────────────────────────────────

def dwarf_fighter_draft(**overrides) -> dict:
    """A legal level-1 Hill Dwarf Fighter, standard array, 2014."""
    draft = {
        "name": "Torvin Bracewell",
        "player": "Yoan",
        "race_id": "dwarf",
        "subrace_id": "hill-dwarf",
        "background_id": "acolyte",
        "class_id": "fighter",
        "subclass_id": "champion",
        "level": 1,
        "ability_method": "standard_array",
        "ability_scores": {"STR": 15, "DEX": 14, "CON": 13,
                           "INT": 10, "WIS": 12, "CHA": 8},
        "ability_choice_index": None,
        "ability_choice_assignment": None,
        "skill_picks": ["Athletics", "Perception"],
        "equipped_armor_id": "chain-mail",
        "shield": True,
        "hp_method": "max_then_average",
        "spells_known": [],
        "spells_prepared": [],
        "alignment": "LG",
        "backstory": "Raised in a mountain temple.",
    }
    draft.update(overrides)
    return draft


def cleric_draft(**overrides) -> dict:
    draft = {
        "name": "Sylwen Nightbrook",
        "player": "",
        "race_id": "human",
        "subrace_id": None,
        "background_id": "acolyte",
        "class_id": "cleric",
        "subclass_id": None,
        "level": 1,
        "ability_method": "standard_array",
        "ability_scores": {"STR": 10, "DEX": 12, "CON": 14,
                           "INT": 8, "WIS": 15, "CHA": 13},
        "ability_choice_index": None,
        "ability_choice_assignment": None,
        "skill_picks": ["History", "Medicine"],
        "equipped_armor_id": None,
        "shield": False,
        "hp_method": "max_then_average",
        "spells_known": [],
        "spells_prepared": ["Bless", "Cure Wounds", "Sacred Flame"],
        "alignment": "NG",
        "backstory": "",
    }
    draft.update(overrides)
    return draft


# ── 2024 fixtures (no real 2024 data exists on disk until Task 10) ───────

def fixture_2024_background(**overrides) -> Background:
    kwargs = {
        "id": "acolyte-xphb",
        "name": "Acolyte",
        "source": "XPHB",
        "ruleset": "2024",
        "skill_proficiencies": ["Insight", "Religion"],
        "tool_proficiencies": ["Calligrapher's Supplies"],
        "languages": [],
        "starting_equipment": [ItemRef(id=None, name="Holy Symbol", quantity=1)],
        "feature": None,
        "origin_feat": "Magic Initiate (Cleric)",
        "ability_choice": [
            AbilityChoice(options=["INT", "WIS", "CHA"], weights=[2, 1]),
            AbilityChoice(options=["INT", "WIS", "CHA"], weights=[1, 1, 1]),
        ],
    }
    kwargs.update(overrides)
    return Background(**kwargs)


def fixture_2024_race(**overrides) -> Race:
    """A 2024 race carries NO ability bonuses — the background does.

    `**overrides` exists so a test can build the same record labelled with a
    different `ruleset`, which is what the mixed-edition comparison needs
    (see mixed_edition_warning() — the record-vs-draft ruleset check it
    replaced, validate_record_rulesets(), is gone, along with the Draft's
    own ruleset field)."""
    kwargs = {
        "id": "dwarf",
        "name": "Dwarf",
        "source": "XPHB",
        "ruleset": "2024",
        "size": "M",
        "speed": 30,
        "ability_bonuses": {},
        "ability_choice": None,
        "traits": [Trait(name="Darkvision", text="You can see in the dark.")],
        "subraces": [],
        "languages": ["Common", "Dwarvish"],
    }
    kwargs.update(overrides)
    return Race(**kwargs)


class FakeCatalog:
    """Real catalog for classes/spells/equipment, fixture race+background.

    Task 10 fetches the real 2024 data; until then this is the only way to
    exercise the 2024 branch end-to-end through `build()`.
    """

    def __init__(self, real: Catalog, race: Race, background: Background,
                 subraces: list[Subrace] | None = None):
        self._real = real
        self._race = race
        self._background = background
        self._subraces = list(subraces or [])

    # -- overridden --
    def race(self, id):
        if id == self._race.id:
            return self._race
        raise KeyError(f"no race {id!r} in catalog")

    def subraces(self, race_id):
        return [s for s in self._subraces if s.parent_race_id == race_id]

    def background(self, id):
        if id == self._background.id:
            return self._background
        raise KeyError(f"no background {id!r} in catalog")

    def starting_equipment(self, class_id, background_id):
        self._real.class_(class_id)
        return list(self._background.starting_equipment)

    # -- delegated --
    def class_(self, id):
        return self._real.class_(id)

    def subclasses(self, class_id):
        return self._real.subclasses(class_id)

    def level_row(self, class_id, level):
        return self._real.level_row(class_id, level)

    def spells(self, **kw):
        return self._real.spells(**kw)

    def armor(self):
        return self._real.armor()

    def weapons(self, category=None):
        return self._real.weapons(category)

    def gear(self):
        return self._real.gear()


# ── the happy path ──────────────────────────────────────────────────────

class LegalDraftTest(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog.load("2014")

    def test_a_legal_fighter_draft_has_no_problems(self):
        sheet, problems, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(problems, [])
        self.assertTrue(sheet)

    def test_the_sheet_carries_the_identity_fields_the_renderer_needs(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(sheet["name"], "Torvin Bracewell")
        self.assertEqual(sheet["player"], "Yoan")
        self.assertEqual(sheet["race"], "Hill Dwarf")   # subrace display name
        self.assertEqual(sheet["background"], "Acolyte")
        self.assertEqual(sheet["alignment"], "LG")
        self.assertEqual(sheet["classes"],
                         [{"cls": "Fighter", "subclass": "Champion", "level": 1}])

    def test_race_display_name_falls_back_to_the_race_without_a_subrace(self):
        sheet, problems, _ = build(cleric_draft(), self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sheet["race"], "Human")

    def test_2014_race_and_subrace_bonuses_both_apply(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(sheet["ability_scores"],
                         {"STR": 15, "DEX": 14, "CON": 15,     # +2 Dwarf
                          "INT": 10, "WIS": 13, "CHA": 8})     # +1 Hill Dwarf

    def test_derived_combat_numbers(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        combat = sheet["combat"]
        # d10 hit die, CON 15 -> +2, level 1 -> 10 + 2
        self.assertEqual(combat["hp_max"], 12)
        self.assertEqual(combat["hp_current"], 12)
        self.assertEqual(combat["hp_temp"], 0)
        self.assertEqual(combat["speed"], 25)                  # Dwarf
        self.assertEqual(combat["death_saves"], {"successes": 0, "failures": 0})
        self.assertEqual(combat["hit_dice"], [{"cls": "Fighter", "die": 10, "used": 0}])

    def test_proficiencies_come_from_the_class_and_the_draft(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        profs = sheet["proficiencies"]
        self.assertEqual(profs["saving_throws"], ["STR", "CON"])
        # class picks first, then what the Acolyte background grants outright
        self.assertEqual(profs["skills"],
                         ["Athletics", "Perception", "Insight", "Religion"])
        self.assertIn("All armor", profs["armor"])
        self.assertIn("Martial Weapons", profs["weapons"])
        self.assertIn("Common", profs["languages"])
        self.assertIn("Dwarvish", profs["languages"])
        self.assertEqual(len(profs["languages"]), len(set(profs["languages"])))

    def test_background_skill_grants_join_the_class_picks(self):
        """Acolyte grants Insight and Religion outright. Dropping them means
        char_state_derive never adds the proficiency bonus to those checks,
        silently, for the life of the character."""
        sheet, problems, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(problems, [])
        self.assertIn("Insight", sheet["proficiencies"]["skills"])
        self.assertIn("Religion", sheet["proficiencies"]["skills"])

    def test_the_merged_skill_list_never_repeats_a_proficiency(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        skills = sheet["proficiencies"]["skills"]
        self.assertEqual(len(skills), len(set(skills)))

    def test_the_merge_itself_drops_an_overlap(self):
        """Validation rejects picking a skill the background already grants,
        so the merge should never see an overlap — but it must not produce a
        double entry if one ever reaches it."""
        self.assertEqual(_dedup(["Religion", "Athletics"], ["Insight", "Religion"]),
                         ["Religion", "Athletics", "Insight"])

    def test_features_come_from_race_subrace_background_and_every_class_level(self):
        sheet, problems, _ = build(dwarf_fighter_draft(level=3), self.cat)
        self.assertEqual(problems, [])
        by_name = {f["name"]: f for f in sheet["features_traits"]}
        self.assertEqual(by_name["Darkvision"]["source"], "Race")
        self.assertTrue(by_name["Darkvision"]["description"])
        self.assertEqual(by_name["Dwarven Toughness"]["source"], "Race")   # subrace
        self.assertEqual(by_name["Shelter of the Faithful"]["source"], "Background")
        self.assertEqual(by_name["Second Wind"]["source"], "Class")        # level 1
        self.assertIn("Action Surge (1 use)", by_name)                     # level 2
        self.assertIn("Martial Archetype", by_name)                        # level 3

    def test_equipment_includes_the_equipped_armor_and_shield(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        equipped = {e["name"]: e for e in sheet["equipment"] if e["equipped"]}
        self.assertIn("Chain Mail", equipped)
        self.assertIn("Shield", equipped)
        carried = {e["name"] for e in sheet["equipment"] if not e["equipped"]}
        self.assertIn("Clothes, common", carried)   # from the Acolyte background
        for entry in sheet["equipment"]:
            self.assertEqual(set(entry), {"name", "equipped", "quantity"})

    def test_a_non_caster_gets_no_spellcasting_block(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(sheet["spellcasting"], [])
        self.assertEqual(sheet["spells"], [])
        self.assertEqual(sheet["spell_slots"], {})
        self.assertIsNone(sheet["pact_magic_slots"])

    def test_a_prepared_caster_gets_slots_spells_and_a_casting_ability(self):
        sheet, problems, _ = build(cleric_draft(), self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sheet["spellcasting"], [{"cls": "Cleric", "ability": "WIS"}])
        self.assertEqual(sheet["spell_slots"], {1: {"max": 2, "used": 0}})
        self.assertEqual(
            sorted(s["name"] for s in sheet["spells"]),
            ["Bless", "Cure Wounds", "Sacred Flame"],
        )
        self.assertTrue(all(s["prepared"] for s in sheet["spells"]))
        self.assertTrue(all(s["cls"] == "Cleric" for s in sheet["spells"]))

    def test_higher_level_slots_convert_to_the_library_shape(self):
        sheet, problems, _ = build(cleric_draft(
            level=5, spells_prepared=["Bless", "Cure Wounds"]), self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sheet["spell_slots"],
                         {1: {"max": 4, "used": 0},
                          2: {"max": 3, "used": 0},
                          3: {"max": 2, "used": 0}})

    def test_the_flat_default_blocks_are_present_and_empty(self):
        sheet, _, _ = build(dwarf_fighter_draft(), self.cat)
        self.assertEqual(sheet["conditions"], {"inspiration": False, "exhaustion": 0,
                                               "active": [], "attunement": [],
                                               "weapon_mastery": []})
        self.assertEqual(sheet["personality"],
                         {"traits": "", "ideals": "", "bonds": "", "flaws": ""})
        self.assertEqual(sheet["currency"],
                         {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0})
        self.assertEqual(sheet["misc_items"], [])
        self.assertEqual(sheet["backstory"], "Raised in a mountain temple.")


# ── per-piece ability bonuses (Global Finding 1 redesign) ────────────────

class RulesetBranchTest(unittest.TestCase):
    """Each chosen piece contributes its own ability-bonus mechanic,
    independent of any global ruleset: a race/subrace's fixed
    ability_bonuses apply if present, and a background's weighted
    ability_choice applies if the background carries one — and, per the
    redesign, a single call can now legally draw bonuses from BOTH a
    2014-style race/subrace and a 2024-style background's ability_choice
    at once. Replaces the old ruleset-gated branch this class used to
    test — apply_ability_bonuses() no longer takes a ruleset argument at
    all; see docs/superpowers/specs/2026-08-25-character-builder-v2-
    design.md §B.1/§B.2."""

    BASE = {"STR": 15, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 8}

    def setUp(self):
        self.cat = Catalog.load("2014")

    def test_a_2014_race_and_subraces_fixed_bonuses_apply(self):
        """A 2014-style race+subrace's fixed bonuses apply; a background
        with no ability_choice (acolyte, 2014-style) contributes nothing."""
        race = self.cat.race("dwarf")
        subrace = self.cat.subraces("dwarf")[0]
        background = self.cat.background("acolyte")
        final = apply_ability_bonuses(self.BASE, race, subrace, background, None, None)
        self.assertEqual(final, {"STR": 15, "DEX": 14, "CON": 15,     # +2 Dwarf
                                 "INT": 10, "WIS": 13, "CHA": 8})     # +1 Hill Dwarf

    def test_a_2024_backgrounds_weighted_choice_applies_independent_of_race(self):
        final = apply_ability_bonuses(
            self.BASE, None, None, fixture_2024_background(),
            0, {"WIS": 2, "INT": 1})
        self.assertEqual(final, {"STR": 15, "DEX": 14, "CON": 13,
                                 "INT": 11, "WIS": 14, "CHA": 8})

    def test_a_2024_backgrounds_second_choice_pattern_spreads_one_point_each(self):
        final = apply_ability_bonuses(
            self.BASE, None, None, fixture_2024_background(),
            1, {"INT": 1, "WIS": 1, "CHA": 1})
        self.assertEqual(final, {"STR": 15, "DEX": 14, "CON": 13,
                                 "INT": 11, "WIS": 13, "CHA": 9})

    def test_a_2014_races_bonuses_and_a_2024_backgrounds_choice_both_apply_at_once(self):
        """The genuinely new case this redesign exists for: a 2014-style
        race/subrace's fixed bonuses and a 2024-style background's
        weighted ability_choice can both land on the same character in
        one call — impossible under the old ruleset-gated branch, which
        took bonuses from exactly one source or the other, never both."""
        race = self.cat.race("dwarf")
        subrace = self.cat.subraces("dwarf")[0]
        final = apply_ability_bonuses(
            self.BASE, race, subrace, fixture_2024_background(),
            0, {"WIS": 2, "INT": 1})
        self.assertEqual(final, {"STR": 15, "DEX": 14, "CON": 15,    # +2 Dwarf
                                 "INT": 11,                          # +1 background
                                 "WIS": 15,                          # +1 subrace, +2 background
                                 "CHA": 8})

    def test_a_background_with_no_ability_choice_ignores_a_stray_choice_index(self):
        """A background that carries no ability_choice (any 2014-style
        one, e.g. acolyte) ignores a stray choice_index/assignment if one
        is passed anyway — not an error, just ignored. Mirrors the old
        ruleset-gated test's intent: which source a piece contributes
        from is decided per-piece now, never by a global flag."""
        race = self.cat.race("dwarf")
        background = self.cat.background("acolyte")
        final = apply_ability_bonuses(
            self.BASE, race, None, background, 0, {"WIS": 2, "INT": 1})
        self.assertEqual(final["WIS"], 12)
        self.assertEqual(final["CON"], 15)


class Ruleset2024ValidationTest(unittest.TestCase):
    """A 2024 build must reject a draft with no/invalid background pick —
    never silently produce an unbonused sheet."""

    def setUp(self):
        real = Catalog.load("2014")
        self.cat = FakeCatalog(real, fixture_2024_race(), fixture_2024_background())

    def draft(self, **overrides):
        d = dwarf_fighter_draft(
            subrace_id=None,
            background_id="acolyte-xphb",
            ability_choice_index=0,
            ability_choice_assignment={"WIS": 2, "INT": 1},
        )
        d.update(overrides)
        return d

    def test_a_valid_2024_draft_builds(self):
        sheet, problems, _ = build(self.draft(), self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sheet["ability_scores"]["WIS"], 14)
        self.assertEqual(sheet["ability_scores"]["INT"], 11)
        self.assertEqual(sheet["ability_scores"]["CON"], 13)   # race gives nothing

    def test_no_ability_pick_at_all_is_a_problem_not_a_silent_zero(self):
        sheet, problems, _ = build(
            self.draft(ability_choice_index=None, ability_choice_assignment=None),
            self.cat)
        self.assertEqual(sheet, {})
        self.assertTrue(any("ability_choice_index" in p for p in problems), problems)

    def test_an_out_of_range_choice_index_is_a_problem(self):
        _, problems, _ = build(self.draft(ability_choice_index=9), self.cat)
        self.assertTrue(any("ability_choice_index" in p for p in problems), problems)

    def test_an_ability_outside_the_chosen_options_is_a_problem(self):
        _, problems, _ = build(
            self.draft(ability_choice_assignment={"STR": 2, "INT": 1}), self.cat)
        self.assertTrue(any("STR" in p for p in problems), problems)

    def test_the_same_bonus_cannot_go_to_two_abilities(self):
        _, problems, _ = build(
            self.draft(ability_choice_assignment={"WIS": 2, "INT": 2}), self.cat)
        self.assertTrue(problems)

    def test_too_few_abilities_for_the_chosen_pattern_is_a_problem(self):
        _, problems, _ = build(self.draft(ability_choice_assignment={"WIS": 2}), self.cat)
        self.assertTrue(problems)

    def test_a_missing_assignment_with_an_index_is_still_a_problem(self):
        _, problems, _ = build(self.draft(ability_choice_assignment=None), self.cat)
        self.assertTrue(problems)


# ── validation ──────────────────────────────────────────────────────────

class ValidationTest(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog.load("2014")

    def build(self, **overrides):
        return build(dwarf_fighter_draft(**overrides), self.cat)

    def test_an_illegal_draft_yields_an_empty_sheet_and_problems(self):
        sheet, problems, _ = self.build(skill_picks=["Arcana", "Perception"])
        self.assertEqual(sheet, {})
        self.assertTrue(problems)
        self.assertTrue(any("Arcana" in p and "Fighter" in p for p in problems), problems)

    def test_the_wrong_number_of_skills_is_a_problem(self):
        _, problems, _ = self.build(skill_picks=["Athletics"])
        self.assertTrue(any("2" in p for p in problems), problems)

    def test_duplicate_skill_picks_are_a_problem(self):
        _, problems, _ = self.build(skill_picks=["Athletics", "Athletics"])
        self.assertTrue(any("duplicate" in p.lower() for p in problems), problems)

    def test_standard_array_must_be_exactly_the_standard_array(self):
        _, problems, _ = self.build(ability_scores={"STR": 15, "DEX": 15, "CON": 13,
                                                 "INT": 10, "WIS": 12, "CHA": 8})
        self.assertTrue(any("standard array" in p.lower() for p in problems), problems)

    def test_the_standard_array_may_be_assigned_in_any_order(self):
        _, problems, _ = self.build(ability_scores={"STR": 8, "DEX": 10, "CON": 12,
                                                 "INT": 13, "WIS": 14, "CHA": 15})
        self.assertEqual(problems, [])

    def test_rolled_scores_stay_inside_3_to_18(self):
        _, problems, _ = self.build(ability_method="roll",
                                 ability_scores={"STR": 19, "DEX": 14, "CON": 13,
                                                 "INT": 10, "WIS": 12, "CHA": 2})
        self.assertEqual(len(problems), 2, problems)

    def test_point_buy_at_exactly_27_points_is_legal(self):
        # 15/15/15/8/8/8 -> 9+9+9+0+0+0 = 27
        _, problems, _ = self.build(ability_method="point_buy",
                                 ability_scores={"STR": 15, "DEX": 15, "CON": 15,
                                                 "INT": 8, "WIS": 8, "CHA": 8})
        self.assertEqual(problems, [])

    def test_point_buy_at_28_points_is_not(self):
        # 15/15/15/9/8/8 -> 9+9+9+1+0+0 = 28
        _, problems, _ = self.build(ability_method="point_buy",
                                 ability_scores={"STR": 15, "DEX": 15, "CON": 15,
                                                 "INT": 9, "WIS": 8, "CHA": 8})
        self.assertTrue(any("27" in p for p in problems), problems)

    def test_point_buy_scores_stay_inside_8_to_15(self):
        _, problems, _ = self.build(ability_method="point_buy",
                                 ability_scores={"STR": 16, "DEX": 14, "CON": 13,
                                                 "INT": 10, "WIS": 12, "CHA": 8})
        self.assertTrue(any("16" in p for p in problems), problems)

    def test_an_unknown_ability_method_is_a_problem(self):
        _, problems, _ = self.build(ability_method="ouija_board")
        self.assertTrue(any("ouija_board" in p for p in problems), problems)

    def test_a_missing_ability_score_is_a_problem(self):
        scores = dwarf_fighter_draft()["ability_scores"]
        scores.pop("CHA")
        _, problems, _ = self.build(ability_scores=scores)
        self.assertTrue(any("CHA" in p for p in problems), problems)

    def test_an_unknown_race_is_a_problem(self):
        _, problems, _ = self.build(race_id="tabaxi", subrace_id=None)
        self.assertTrue(any("tabaxi" in p for p in problems), problems)

    def test_a_subrace_from_another_race_is_a_problem(self):
        _, problems, _ = self.build(race_id="elf", subrace_id="hill-dwarf")
        self.assertTrue(any("hill-dwarf" in p for p in problems), problems)

    def test_an_unknown_background_is_a_problem(self):
        _, problems, _ = self.build(background_id="pirate-king")
        self.assertTrue(any("pirate-king" in p for p in problems), problems)

    def test_an_unknown_class_is_a_problem(self):
        _, problems, _ = self.build(class_id="artificer")
        self.assertTrue(any("artificer" in p for p in problems), problems)

    def test_a_subclass_from_another_class_is_a_problem(self):
        _, problems, _ = self.build(subclass_id="life")
        self.assertTrue(any("life" in p for p in problems), problems)

    def test_level_must_be_inside_1_to_20(self):
        for bad in (0, 21, -3):
            _, problems, _ = self.build(level=bad)
            self.assertTrue(any("level" in p.lower() for p in problems), (bad, problems))

    def test_unknown_armor_is_a_problem(self):
        _, problems, _ = self.build(equipped_armor_id="mithral-plate")
        self.assertTrue(any("mithral-plate" in p for p in problems), problems)

    def test_a_skill_the_background_already_grants_is_a_wasted_pick(self):
        _, problems, _ = self.build(skill_picks=["Athletics", "Insight"])
        self.assertTrue(any("Insight" in p and "Acolyte" in p for p in problems),
                        problems)

    def test_a_2014_race_ability_choice_is_reported_not_silently_dropped(self):
        """Half-Elf is CHA +2 *and* two more scores of the player's choice at
        +1 each. The Draft has no field for those two picks, so building
        clean would quietly hand the player a weaker character than the
        rules give them."""
        sheet, problems, _ = self.build(race_id="half-elf", subrace_id=None)
        self.assertEqual(sheet, {})
        self.assertTrue(
            any("Half-Elf" in p and "ability score choice" in p for p in problems),
            problems)

    def test_a_race_without_an_ability_choice_builds_clean(self):
        _, problems, _ = self.build()
        self.assertEqual(problems, [])

    def test_a_nameless_character_is_a_problem(self):
        _, problems, _ = self.build(name="   ")
        self.assertTrue(any("name" in p.lower() for p in problems), problems)

    # -- spells --

    def test_a_non_caster_with_spells_is_a_problem(self):
        _, problems, _ = self.build(spells_known=["Fireball"])
        self.assertTrue(any("Fighter" in p and "spell" in p.lower() for p in problems),
                        problems)

    def test_a_non_caster_with_prepared_spells_is_a_problem(self):
        _, problems, _ = self.build(spells_prepared=["Bless"])
        self.assertTrue(problems)

    def test_a_spell_off_the_class_list_is_a_problem(self):
        _, problems, _ = build(cleric_draft(spells_prepared=["Fireball"]), self.cat)
        self.assertTrue(any("Fireball" in p for p in problems), problems)

    def test_an_unknown_spell_name_is_a_problem(self):
        _, problems, _ = build(cleric_draft(spells_prepared=["Sudden Onset Of Wisdom"]),
                            self.cat)
        self.assertTrue(any("Sudden Onset Of Wisdom" in p for p in problems), problems)

    def test_a_spell_above_the_available_slot_level_is_a_problem(self):
        _, problems, _ = build(cleric_draft(spells_prepared=["Revivify"]), self.cat)
        self.assertTrue(any("Revivify" in p for p in problems), problems)

    def test_too_many_prepared_spells_is_a_problem(self):
        # level 1 Cleric, WIS 15 + 1 (Human) = 16 -> +3 -> limit 1 + 3 = 4.
        # All five are LEVELLED spells: the prepared limit counts only those
        # (cantrips have their own, separate cap), so a list padded out with
        # cantrips would be legal and would not test this limit at all.
        _, problems, _ = build(cleric_draft(
            spells_prepared=["Bless", "Cure Wounds", "Guiding Bolt",
                             "Healing Word", "Shield of Faith"]),
            self.cat)
        self.assertTrue(any("prepare" in p.lower() for p in problems), problems)

    def test_a_known_caster_is_measured_against_the_known_limit(self):
        base = cleric_draft(class_id="sorcerer", subclass_id=None,
                            skill_picks=["Arcana", "Deception"],
                            spells_prepared=[],
                            ability_scores={"STR": 8, "DEX": 14, "CON": 13,
                                            "INT": 10, "WIS": 12, "CHA": 15})
        ok, problems, _ = build(dict(base, spells_known=["Mage Hand", "Magic Missile"]),
                             self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(s["name"] for s in ok["spells"]),
                         ["Mage Hand", "Magic Missile"])
        self.assertFalse(any(s["prepared"] for s in ok["spells"]))
        self.assertEqual(ok["spellcasting"], [{"cls": "Sorcerer", "ability": "CHA"}])

        # Three LEVELLED spells against a known limit of 2. (Mage Hand, the
        # cantrip in the legal list above, does not count towards it.)
        _, problems, _ = build(dict(base, spells_known=[
            "Magic Missile", "Shield", "Burning Hands"]), self.cat)
        self.assertTrue(any("know" in p.lower() for p in problems), problems)

    # -- cantrips and duplicates (final-fix-wave) ------------------------

    def test_cantrips_do_not_count_against_the_prepared_limit(self):
        """The bug this reproduces: a level 3 Cleric with WIS 16 may prepare
        6 levelled spells AND knows 3 cantrips, but the two shared one Draft
        list and one limit, so the legal character was rejected with "9 were
        chosen" against a limit of 6."""
        _, problems, _ = build(cleric_draft(
            level=3,
            ability_scores={"STR": 13, "DEX": 12, "CON": 14,
                            "INT": 10, "WIS": 15, "CHA": 8},
            skill_picks=["Medicine", "Persuasion"],
            spells_prepared=["Guidance", "Sacred Flame", "Spare the Dying",
                             "Bless", "Cure Wounds", "Guiding Bolt",
                             "Healing Word", "Hold Person", "Spiritual Weapon"]),
            self.cat)
        self.assertEqual(problems, [])

    def test_cantrips_do_not_count_against_the_known_limit_either(self):
        base = cleric_draft(class_id="sorcerer", subclass_id=None,
                            skill_picks=["Arcana", "Deception"],
                            spells_prepared=[],
                            ability_scores={"STR": 8, "DEX": 14, "CON": 13,
                                            "INT": 10, "WIS": 12, "CHA": 15})
        # Sorcerer 1: knows 2 levelled spells and 4 cantrips.
        _, problems, _ = build(dict(base, spells_known=[
            "Magic Missile", "Shield",
            "Mage Hand", "Light", "Prestidigitation", "Fire Bolt"]), self.cat)
        self.assertEqual(problems, [])

    def test_too_many_cantrips_is_its_own_problem(self):
        _, problems, _ = build(cleric_draft(
            level=3,
            ability_scores={"STR": 13, "DEX": 12, "CON": 14,
                            "INT": 10, "WIS": 15, "CHA": 8},
            skill_picks=["Medicine", "Persuasion"],
            spells_prepared=["Guidance", "Sacred Flame", "Spare the Dying",
                             "Light", "Bless"]),
            self.cat)
        self.assertTrue(any("cantrip" in p for p in problems), problems)
        self.assertFalse(any("can prepare" in p for p in problems), problems)

    def test_an_unknown_spell_name_still_reports_only_once(self):
        """A name the catalog can't resolve has no level, so it is counted
        against neither limit — one message about it, not two."""
        _, problems, _ = build(cleric_draft(spells_prepared=["Sudden Onset Of Wisdom"]),
                            self.cat)
        self.assertEqual(len(problems), 1, problems)

    def test_duplicate_prepared_spells_are_a_problem(self):
        """Naming one spell three times used to burn three prepared slots on
        it and list it three times on the sheet."""
        sheet, problems, _ = build(cleric_draft(
            spells_prepared=["Bless", "Bless", "Bless"]), self.cat)
        self.assertEqual(sheet, {})
        self.assertTrue(any("duplicate spell picks" in p and "Bless" in p
                            for p in problems), problems)

    def test_duplicate_known_spells_are_a_problem(self):
        _, problems, _ = build(cleric_draft(
            class_id="sorcerer", subclass_id=None,
            skill_picks=["Arcana", "Deception"], spells_prepared=[],
            ability_scores={"STR": 8, "DEX": 14, "CON": 13,
                            "INT": 10, "WIS": 12, "CHA": 15},
            spells_known=["Magic Missile", "Magic Missile"]), self.cat)
        self.assertTrue(any("duplicate spell picks" in p for p in problems), problems)

    def test_a_prepared_caster_may_not_use_the_known_list(self):
        _, problems, _ = build(cleric_draft(spells_prepared=[], spells_known=["Bless"]),
                            self.cat)
        self.assertTrue(any("spells_known" in p for p in problems), problems)

    # -- hp_method (final-fix-wave) --------------------------------------

    def test_an_hp_method_typo_is_a_problem_rather_than_a_silent_default(self):
        """rules.hit_points() dispatches with an if/else, so a misspelling
        used to fall through to max_then_average and produce a real, wrong
        number with nothing said about it."""
        sheet, problems, _ = self.build(hp_method="max_then_avarage")
        self.assertEqual(sheet, {})
        self.assertTrue(any("hp_method" in p for p in problems), problems)
        self.assertTrue(any("max_then_avarage" in p for p in problems), problems)

    def test_both_real_hp_methods_are_accepted(self):
        for method in ("max_then_average", "max_then_max"):
            with self.subTest(method=method):
                _, problems, _ = self.build(hp_method=method)
                self.assertEqual(problems, [])

    def test_an_absent_hp_method_is_the_documented_default_not_a_problem(self):
        draft = dwarf_fighter_draft()
        del draft["hp_method"]
        sheet, problems, _ = build(draft, self.cat)
        self.assertEqual(problems, [])
        self.assertEqual(sheet["combat"]["hp_max"], 12)

    def test_several_problems_are_all_reported_at_once(self):
        _, problems, _ = self.build(skill_picks=["Arcana"], level=0,
                                 equipped_armor_id="nonesuch")
        self.assertGreaterEqual(len(problems), 3, problems)


# ── the round trip: build() -> library -> the real running game ─────────

@unittest.skip(
    "Integration test for library.py/engine — those live in the source "
    "repo's skills/dnd/scripts/, which this standalone repo deliberately "
    "does not include (see docs/superpowers/specs/2026-09-13-character-creator-app-design.md). "
    "Not a chargen bug."
)
class RoundTripTest(unittest.TestCase):
    """build() -> library.save() -> library.load() -> copy_to_campaign()
    -> engine.state.party_names() / engine.local_context.read_hp().

    If this passes, a sheet this module produces is genuinely playable.
    """

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["DND_CAMPAIGN_ROOT"] = self.tmp.name
        os.environ.pop("DND_RUNTIME_DIR", None)
        import paths
        importlib.reload(paths)
        import library
        self.lib = importlib.reload(library)

        self.sheet, problems, _ = build(dwarf_fighter_draft(), Catalog.load("2014"))
        self.assertEqual(problems, [], "the fixture draft must be legal")

    def test_the_sheet_survives_a_save_load_round_trip(self):
        self.lib.save(self.sheet["name"], self.sheet)
        loaded = self.lib.load(self.sheet["name"])
        self.assertEqual(loaded, self.sheet)

    def test_the_sheet_is_plain_yaml_safe_data(self):
        """No dataclasses, no tuples, no enums — library dumps with
        yaml.safe_dump, which refuses anything else."""
        text = yaml.safe_dump(self.sheet, allow_unicode=True, sort_keys=False)
        self.assertEqual(yaml.safe_load(text), self.sheet)

    def test_the_archive_snapshots_it_at_its_level(self):
        self.lib.save(self.sheet["name"], self.sheet)
        self.assertEqual(self.lib.archived_levels(self.sheet["name"]), [1])

    def test_the_running_game_reads_back_the_recruited_character(self):
        from engine.local_context import read_hp
        from engine.state import party_names

        name = self.sheet["name"]
        self.lib.save(name, self.sheet)
        (Path(self.tmp.name) / "campaigns" / "testcamp" / "characters").mkdir(
            parents=True)
        dest = self.lib.copy_to_campaign(name, "testcamp")
        self.assertTrue(dest.exists())

        # 1. the engine finds the party by the sheet's own `# Name` heading
        self.assertEqual(party_names("testcamp"), [name])
        # 2. and reads HP off the same markdown file
        self.assertEqual(read_hp("testcamp", name),
                         (self.sheet["combat"]["hp_current"],
                          self.sheet["combat"]["hp_max"]))

    def test_the_campaign_yaml_is_the_sheet_we_built(self):
        name = self.sheet["name"]
        self.lib.save(name, self.sheet)
        (Path(self.tmp.name) / "campaigns" / "testcamp" / "characters").mkdir(
            parents=True)
        dest = self.lib.copy_to_campaign(name, "testcamp")
        self.assertEqual(yaml.safe_load(dest.read_text(encoding="utf-8")), self.sheet)

    def test_the_games_own_character_state_tooling_loads_the_sheet(self):
        """Beyond library.py: the sheet must satisfy char_state_schema's
        loader, and its equipment list must be enough for the game to derive
        an AC — which is why build() stores no armor_class of its own."""
        import char_state_derive as derive
        import char_state_schema as schema

        name = self.sheet["name"]
        self.lib.save(name, self.sheet)
        (Path(self.tmp.name) / "campaigns" / "testcamp" / "characters").mkdir(
            parents=True)
        self.lib.copy_to_campaign(name, "testcamp")

        char = schema.load_character("testcamp", "torvin-bracewell")
        self.assertEqual(char.name, name)
        self.assertEqual(char.race, "Hill Dwarf")
        self.assertEqual(derive.compute_proficiency_bonus(char), 2)
        # Chain Mail 16, +2 shield — derived from the equipped items alone.
        self.assertEqual(derive.compute_ac(char), 18)

    def test_the_library_listing_shows_the_built_character(self):
        self.lib.save(self.sheet["name"], self.sheet)
        row = self.lib.list_characters()[0]
        self.assertEqual(row["name"], "Torvin Bracewell")
        self.assertEqual(row["race"], "Hill Dwarf")
        self.assertEqual(row["classes"], "Fighter 1")
        self.assertEqual(row["level"], 1)
        self.assertEqual(row["hp_max"], 12)


# ── per-piece ability bonuses; build() gains warnings ────────────────────

def test_mixed_edition_draft_builds_clean_with_a_warning():
    """A 2024-edition race combined with a differently-tagged background —
    a real mismatch, per mixed_edition_warning() comparing each chosen
    piece's own .ruleset — used to be refused outright
    (validate_record_rulesets, final fix wave). Now it must build with
    zero problems and a warning naming the mix.

    Real official 2024 data is installed on disk, but every test in this
    suite runs under tests/conftest.py's autouse isolate_campaign_root
    fixture, which points DND_CAMPAIGN_ROOT — and so
    chargen.sources.official_dir() — at a throwaway temp dir. build()'s
    default `Catalog.load()` therefore can never see the real 2024
    records here, so this uses the same FakeCatalog/fixture_2024_*
    pattern the rest of this file already relies on to exercise a
    2024-tagged pick end to end."""
    real = Catalog.load("2014")
    race = fixture_2024_race(id="aasimar-xphb", name="Aasimar", ruleset="2024")
    background = fixture_2024_background(ruleset="2014")
    cat = FakeCatalog(real, race, background)
    draft = {
        "name": "test", "race_id": "aasimar-xphb", "subrace_id": None,
        "background_id": "acolyte-xphb", "class_id": "cleric",
        "subclass_id": None, "level": 3, "ability_method": "roll",
        "ability_scores": {"STR": 13, "DEX": 12, "CON": 14, "INT": 10,
                            "WIS": 15, "CHA": 8},
        "ability_choice_index": 0, "ability_choice_assignment": {"WIS": 2, "INT": 1},
        "skill_picks": ["Medicine", "Persuasion"], "equipped_armor_id": None,
        "shield": False, "hp_method": "max_then_average",
        "spells_known": [], "spells_prepared": [],
        "alignment": "Lawful Good", "backstory": "",
    }
    sheet, problems, warnings = build(draft, cat)
    assert problems == []
    assert any("2024" in w and "Aasimar" in w for w in warnings)


def test_same_edition_draft_never_warns():
    draft = {
        "name": "test", "race_id": "human", "subrace_id": None,
        "background_id": "acolyte", "class_id": "cleric",
        "subclass_id": None, "level": 3, "ability_method": "roll",
        "ability_scores": {"STR": 13, "DEX": 12, "CON": 14, "INT": 10,
                            "WIS": 15, "CHA": 8},
        "ability_choice_index": None, "ability_choice_assignment": None,
        "skill_picks": ["Medicine", "Persuasion"], "equipped_armor_id": None,
        "shield": False, "hp_method": "max_then_average",
        "spells_known": [], "spells_prepared": [],
        "alignment": "Lawful Good", "backstory": "",
    }
    sheet, problems, warnings = build(draft)
    assert problems == []
    assert warnings == []


# ── regression: validate_ability_choice() must not become a no-op ───────
# (found in review of the change above: it used to gate its whole body on
# draft["ruleset"] == "2024", a field this task removed from the schema —
# so with no fix it silently validated nothing, forever, for every
# schema-compliant draft. Confirmed against the real installed catalog
# before the fix: an out-of-range index crashed apply_ability_bonuses()
# with an uncaught IndexError instead of being caught here first.)

def _mixed_ability_choice_catalog():
    real = Catalog.load("2014")
    return FakeCatalog(real, real.race("human"), fixture_2024_background())


def _ability_choice_draft(**overrides):
    draft = {
        "name": "test", "race_id": "human", "subrace_id": None,
        "background_id": "acolyte-xphb", "class_id": "cleric",
        "subclass_id": None, "level": 1, "ability_method": "roll",
        "ability_scores": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10,
                            "WIS": 10, "CHA": 10},
        "ability_choice_index": 0, "ability_choice_assignment": {"WIS": 2, "INT": 1},
        "skill_picks": ["Medicine", "Persuasion"], "equipped_armor_id": None,
        "shield": False, "hp_method": "max_then_average",
        "spells_known": [], "spells_prepared": [],
        "alignment": "", "backstory": "",
    }
    draft.update(overrides)
    return draft


def test_a_valid_ability_choice_still_builds_clean_with_the_bonus_applied():
    """Sanity check the fixture/helpers above before testing the illegal
    cases: a legal pick must still work exactly as before."""
    sheet, problems, warnings = build(_ability_choice_draft(), _mixed_ability_choice_catalog())
    assert problems == []
    # base 10 + Human's +1 to everything + the {"WIS": 2, "INT": 1} pick.
    assert sheet["ability_scores"]["WIS"] == 13
    assert sheet["ability_scores"]["INT"] == 12


def test_an_out_of_range_ability_choice_index_is_a_problem_not_a_crash():
    draft = _ability_choice_draft(ability_choice_index=9)
    sheet, problems, warnings = build(draft, _mixed_ability_choice_catalog())
    assert sheet == {}
    assert any("ability_choice_index" in p for p in problems)


def test_a_non_int_ability_choice_index_is_a_problem_not_a_crash():
    draft = _ability_choice_draft(ability_choice_index="0")
    sheet, problems, warnings = build(draft, _mixed_ability_choice_catalog())
    assert sheet == {}
    assert any("ability_choice_index" in p for p in problems)


def test_ability_choice_weights_that_dont_match_the_pattern_are_a_problem():
    """{"WIS": 99, "INT": 99} ignores option 0's real weights ([2, 1]) —
    must be rejected, not built clean with WIS 109/INT 109."""
    draft = _ability_choice_draft(ability_choice_assignment={"WIS": 99, "INT": 99})
    sheet, problems, warnings = build(draft, _mixed_ability_choice_catalog())
    assert sheet == {}
    assert any("do not match" in p for p in problems)


def test_an_ability_outside_the_chosen_options_is_a_problem_not_dropped():
    draft = _ability_choice_draft(ability_choice_assignment={"STR": 2, "DEX": 1})
    sheet, problems, warnings = build(draft, _mixed_ability_choice_catalog())
    assert sheet == {}
    assert any("is not one of the abilities" in p for p in problems)


def test_no_ability_choice_pick_at_all_is_a_problem_not_zero_bonuses():
    draft = _ability_choice_draft(ability_choice_index=None, ability_choice_assignment=None)
    sheet, problems, warnings = build(draft, _mixed_ability_choice_catalog())
    assert sheet == {}
    assert any("ability_choice_index" in p for p in problems)


def test_half_elf_ability_choice_is_still_a_blocking_problem_not_a_warning():
    """This existing check (Task 6, original plan) must not get swept into
    warnings by this change — it is a real gap in what the Draft can
    express, not an edition mismatch."""
    draft = {
        "name": "test", "race_id": "half-elf", "subrace_id": None,
        "background_id": "acolyte", "class_id": "cleric",
        "subclass_id": None, "level": 1, "ability_method": "roll",
        "ability_scores": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10,
                            "WIS": 10, "CHA": 10},
        "ability_choice_index": None, "ability_choice_assignment": None,
        "skill_picks": [], "equipped_armor_id": None,
        "shield": False, "hp_method": "max_then_average",
        "spells_known": [], "spells_prepared": [],
        "alignment": "", "backstory": "",
    }
    sheet, problems, warnings = build(draft)
    assert any("Half-Elf" in p and "ability score choice" in p for p in problems)


# ── chosen_weapons / chosen_gear (Task 4) ──────────────────────────────

def test_chosen_weapons_and_gear_appear_in_the_built_sheet():
    draft = cleric_draft(
        chosen_weapons=[{"id": "longsword", "quantity": 1}],
        chosen_gear=[{"id": "rope-hempen-50-feet", "quantity": 2}],
    )
    sheet, problems, warnings = build(draft)
    assert problems == []
    names = {(i["name"], i["quantity"]) for i in sheet["equipment"]}
    assert ("Longsword", 1) in names
    assert ("Rope, hempen (50 feet)", 2) in names


def test_unknown_chosen_weapon_id_is_a_problem():
    draft = cleric_draft(
        chosen_weapons=[{"id": "not-a-real-weapon", "quantity": 1}],
        chosen_gear=[],
    )
    sheet, problems, warnings = build(draft)
    assert any("not-a-real-weapon" in p for p in problems)
    assert sheet == {}


def test_chosen_item_matching_an_auto_granted_one_sums_quantity():
    """Acolyte's own starting_equipment already grants a Pouch. Choosing
    another Pouch must produce quantity 2 on one row, not two rows."""
    draft = cleric_draft(
        chosen_weapons=[],
        chosen_gear=[{"id": "pouch", "quantity": 1}],
    )
    sheet, problems, warnings = build(draft)
    assert problems == []
    pouch_rows = [i for i in sheet["equipment"] if i["name"] == "Pouch"]
    assert len(pouch_rows) == 1
    assert pouch_rows[0]["quantity"] == 2


# ── malformed chosen_weapons/chosen_gear are problems, never crashes ────
#
# Same bug class as test_a_non_int_ability_choice_index_is_a_problem_not_a_
# crash above: a hand-written Draft (CLI, or a direct POST to
# /api/chargen/preview) can carry any shape at all, and every one of these
# used to raise straight out of validate_equipment()/_equipment() as an
# uncaught 500 instead of coming back as a problems entry.


def test_a_bare_string_chosen_weapon_entry_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons=["longsword"], chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("chosen_weapons" in p and "longsword" in p for p in problems)


def test_chosen_weapons_that_is_not_a_list_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons="longsword", chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("chosen_weapons must be a list" in p for p in problems)


def test_chosen_gear_that_is_not_a_list_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons=[], chosen_gear={"id": "pouch"})
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("chosen_gear must be a list" in p for p in problems)


def test_a_bare_string_chosen_gear_entry_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons=[], chosen_gear=["pouch"])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("chosen_gear" in p and "pouch" in p for p in problems)


def test_a_non_int_quantity_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons=[{"id": "longsword", "quantity": "abc"}],
                         chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("invalid quantity" in p and "longsword" in p for p in problems)


def test_an_explicitly_null_quantity_is_a_problem_not_a_crash():
    draft = cleric_draft(chosen_weapons=[{"id": "longsword", "quantity": None}],
                         chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("invalid quantity" in p and "longsword" in p for p in problems)


def test_a_negative_quantity_is_a_problem_not_a_negative_equipment_row():
    """Not a crash — worse, this used to build clean and put
    {"name": "Longsword", "quantity": -5} on the sheet."""
    draft = cleric_draft(chosen_weapons=[{"id": "longsword", "quantity": -5}],
                         chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("invalid quantity" in p and "-5" in p for p in problems)


def test_a_zero_quantity_is_a_problem():
    draft = cleric_draft(chosen_weapons=[{"id": "longsword", "quantity": 0}],
                         chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("invalid quantity" in p for p in problems)


def test_an_entry_with_no_id_is_a_problem():
    draft = cleric_draft(chosen_weapons=[{"quantity": 1}], chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert sheet == {}
    assert any("no usable 'id'" in p for p in problems)


def test_quantity_stays_optional_and_defaults_to_one():
    """The shape check must reject only a quantity that is present AND
    invalid — an entry that simply omits it is legal and means 1."""
    draft = cleric_draft(chosen_weapons=[{"id": "longsword"}], chosen_gear=[])
    sheet, problems, warnings = build(draft)
    assert problems == []
    rows = [i for i in sheet["equipment"] if i["name"] == "Longsword"]
    assert rows == [{"name": "Longsword", "equipped": False, "quantity": 1}]


def test_chosen_fields_left_out_entirely_are_still_fine():
    draft = cleric_draft()
    draft.pop("chosen_weapons", None)
    draft.pop("chosen_gear", None)
    sheet, problems, warnings = build(draft)
    assert problems == []


if __name__ == "__main__":
    unittest.main()
