"""Tests for chargen.rules — D&D 5e rules engine."""

import pytest
from chargen.rules import (
    ability_modifier,
    proficiency_bonus,
    hit_points,
    armor_class,
    spell_save_dc,
    spell_attack_bonus,
    carrying_capacity,
    spells_prepared_limit,
    known_spells_limit,
    skill_bonus,
)


class TestAbilityModifier:
    """Test ability_modifier(score) → (score - 10) // 2."""

    def test_score_10_returns_0(self):
        assert ability_modifier(10) == 0

    def test_score_11_returns_0(self):
        """Odd score rounds down."""
        assert ability_modifier(11) == 0

    def test_score_15_returns_2(self):
        """Odd score 15 → (15-10)//2 = 5//2 = 2."""
        assert ability_modifier(15) == 2

    def test_score_16_returns_3(self):
        assert ability_modifier(16) == 3

    def test_score_8_returns_minus_1(self):
        assert ability_modifier(8) == -1

    def test_score_7_returns_minus_2(self):
        """Odd score 7 → (7-10)//2 = -3//2 = -2 (floor division)."""
        assert ability_modifier(7) == -2

    def test_score_9_returns_minus_1(self):
        """Odd score 9 → (9-10)//2 = -1//2 = -1."""
        assert ability_modifier(9) == -1

    def test_score_1_returns_minus_5(self):
        assert ability_modifier(1) == -5

    def test_score_30_returns_plus_10(self):
        assert ability_modifier(30) == 10

    def test_score_0_returns_minus_5(self):
        """Score 0 (theoretical edge) → (0-10)//2 = -10//2 = -5."""
        assert ability_modifier(0) == -5

    def test_negative_score_minus_5_returns_minus_8(self):
        """Negative score (theoretical) → (-5-10)//2 = -15//2 = -8."""
        assert ability_modifier(-5) == -8


class TestProficiencyBonus:
    """Test proficiency_bonus(total_level) with breakpoints."""

    def test_level_1_returns_plus_2(self):
        assert proficiency_bonus(1) == 2

    def test_level_4_returns_plus_2(self):
        """Boundary: levels 1-4 → +2."""
        assert proficiency_bonus(4) == 2

    def test_level_5_returns_plus_3(self):
        """Boundary: exactly 4/5. Level 5 jumps to +3."""
        assert proficiency_bonus(5) == 3

    def test_level_8_returns_plus_3(self):
        """Levels 5-8 → +3."""
        assert proficiency_bonus(8) == 3

    def test_level_9_returns_plus_4(self):
        """Levels 9-12 → +4."""
        assert proficiency_bonus(9) == 4

    def test_level_12_returns_plus_4(self):
        assert proficiency_bonus(12) == 4

    def test_level_13_returns_plus_5(self):
        """Levels 13-16 → +5."""
        assert proficiency_bonus(13) == 5

    def test_level_16_returns_plus_5(self):
        """Boundary: exactly 16/17."""
        assert proficiency_bonus(16) == 5

    def test_level_17_returns_plus_6(self):
        """Boundary: exactly 16/17. Level 17 jumps to +6."""
        assert proficiency_bonus(17) == 6

    def test_level_20_returns_plus_6(self):
        """Levels 17-20 → +6."""
        assert proficiency_bonus(20) == 6

    def test_multiclass_total_level_5_returns_plus_3(self):
        """3rd-level Fighter / 2nd-level Wizard = total 5 → +3."""
        assert proficiency_bonus(5) == 3


class TestHitPoints:
    """Test hit_points(hit_die, con_mod, level, method)."""

    def test_level_1_d6_con_mod_0_max_then_average(self):
        """L1 always takes max die: d6 + 0 = 6."""
        assert hit_points(6, 0, 1) == 6

    def test_level_1_d8_con_mod_plus_2_max_then_average(self):
        """L1: d8 + 2 = 8 + 2 = 10."""
        assert hit_points(8, 2, 1) == 10

    def test_level_2_d6_con_mod_0_max_then_average(self):
        """L2: L1(6) + avg_d6(4) + 0 = 6 + 4 = 10."""
        assert hit_points(6, 0, 2) == 10

    def test_level_3_d6_con_mod_minus_1_max_then_average(self):
        """L1: 6 + (-1) = 5.
        L2: avg(4) + (-1) = 3.
        L3: avg(4) + (-1) = 3.
        Total: 5 + 3 + 3 = 11.
        """
        assert hit_points(6, -1, 3) == 11

    def test_level_5_d8_con_mod_plus_1_max_then_average(self):
        """L1: 8 + 1 = 9.
        L2-5: each adds avg_d8(5) + 1 = 6.
        Total: 9 + 6 + 6 + 6 + 6 = 33.
        """
        assert hit_points(8, 1, 5) == 33

    def test_level_1_d10_con_mod_plus_3_max_then_average(self):
        """L1: 10 + 3 = 13."""
        assert hit_points(10, 3, 1) == 13

    def test_level_2_d12_con_mod_0_max_then_average(self):
        """L1: 12 + 0 = 12.
        L2: avg_d12(7) + 0 = 7.
        Total: 12 + 7 = 19.
        """
        assert hit_points(12, 0, 2) == 19

    def test_level_1_d6_con_mod_minus_5_clamps_to_1(self):
        """L1: 6 + (-5) = 1 (minimum, not 0)."""
        assert hit_points(6, -5, 1) == 1

    def test_level_3_d6_con_mod_minus_5_clamps_to_min_1(self):
        """L1: 6 - 5 = 1.
        L2-3: each adds 4 - 5 = -1, clamped to... wait, this is per level.
        Actually, the spec says "Never let the result go below 1", so we clamp the TOTAL, not per level.
        L1: 1
        L2: 1 + (-1) = 0, but clamped to 1
        L3: 1 + (-1) = 0, but clamped to 1
        Actually, I need to re-read the spec.

        The spec says: "Never let the result go below 1 (a level-1 character with a very negative CON mod,
        e.g. CON 1 = -5 mod with a d6 hit die, would math out to 6-5=1, which is fine and the actual 5e-legal minimum;
        but if any combination could theoretically produce less than 1, clamp to 1 — write a test for this edge case
        with an extreme negative CON mod)."

        So the final result should never be less than 1. Let me think about the formula again:
        level 1: hit_die + con_mod
        level N: hit_die + con_mod + (level - 1) * (avg_die + con_mod)

        If con_mod is -5 and d6, then:
        L1: 6 - 5 = 1
        L2: 1 + (4 - 5) = 1 - 1 = 0
        L3: 1 + (4 - 5) + (4 - 5) = 1 - 1 - 1 = -1

        So the final result could be less than 1, and we need to clamp it. Let me test this.
        """
        result = hit_points(6, -5, 3)
        assert result >= 1  # Must be clamped to at least 1

    def test_max_then_max_method_level_1_d6_con_mod_0(self):
        """Method max_then_max: level 1 = 1 * (6 + 0) = 6."""
        assert hit_points(6, 0, 1, method="max_then_max") == 6

    def test_max_then_max_method_level_5_d8_con_mod_plus_1(self):
        """Method max_then_max: level 5 = 5 * (8 + 1) = 5 * 9 = 45."""
        assert hit_points(8, 1, 5, method="max_then_max") == 45

    def test_max_then_max_method_level_2_d6_con_mod_minus_1(self):
        """Method max_then_max: level 2 = 2 * (6 - 1) = 2 * 5 = 10."""
        assert hit_points(6, -1, 2, method="max_then_max") == 10

    def test_average_die_d6_is_4(self):
        """d6 // 2 + 1 = 3 + 1 = 4."""
        # This is implicitly tested by L2 d6 results
        assert hit_points(6, 0, 2) == 6 + 4

    def test_average_die_d8_is_5(self):
        """d8 // 2 + 1 = 4 + 1 = 5."""
        assert hit_points(8, 0, 2) == 8 + 5

    def test_average_die_d10_is_6(self):
        """d10 // 2 + 1 = 5 + 1 = 6."""
        assert hit_points(10, 0, 2) == 10 + 6

    def test_average_die_d12_is_7(self):
        """d12 // 2 + 1 = 6 + 1 = 7."""
        assert hit_points(12, 0, 2) == 12 + 7


class TestArmorClass:
    """Test armor_class(dex_mod, armor, shield, class_features)."""

    def test_no_armor_no_shield_dex_plus_1(self):
        """10 + dex_mod = 10 + 1 = 11."""
        assert armor_class(1, None, False) == 11

    def test_no_armor_no_shield_dex_plus_3(self):
        """10 + 3 = 13."""
        assert armor_class(3, None, False) == 13

    def test_no_armor_with_shield_dex_plus_1(self):
        """10 + 1 + 2 (shield) = 13."""
        assert armor_class(1, None, True) == 13

    def test_light_armor_leather_dex_plus_3(self):
        """Leather: base 11. Light armor: base + dex = 11 + 3 = 14."""
        armor = {"category": "light", "base_ac": 11}
        assert armor_class(3, armor, False) == 14

    def test_light_armor_with_shield_dex_plus_2(self):
        """Light armor (base 11) + dex (2) + shield (2) = 15."""
        armor = {"category": "light", "base_ac": 11}
        assert armor_class(2, armor, True) == 15

    def test_medium_armor_chain_shirt_dex_plus_4_capped_to_2(self):
        """Chain shirt: base 13. Medium armor: base + min(dex, 2) = 13 + 2 = 15 (NOT 17)."""
        armor = {"category": "medium", "base_ac": 13}
        assert armor_class(4, armor, False) == 15

    def test_medium_armor_chain_shirt_dex_plus_1(self):
        """Chain shirt (base 13) + dex (1) = 14."""
        armor = {"category": "medium", "base_ac": 13}
        assert armor_class(1, armor, False) == 14

    def test_medium_armor_with_shield_dex_plus_0(self):
        """Chain shirt (base 13) + dex (0) + shield (2) = 15."""
        armor = {"category": "medium", "base_ac": 13}
        assert armor_class(0, armor, True) == 15

    def test_heavy_armor_chain_mail_dex_plus_3_ignored(self):
        """Chain mail: base 16. Heavy armor: base only = 16 (dex ignored)."""
        armor = {"category": "heavy", "base_ac": 16}
        assert armor_class(3, armor, False) == 16

    def test_heavy_armor_chain_mail_dex_minus_1_ignored(self):
        """Chain mail (base 16). Dex ignored, even negative = 16."""
        armor = {"category": "heavy", "base_ac": 16}
        assert armor_class(-1, armor, False) == 16

    def test_heavy_armor_with_shield_dex_plus_2(self):
        """Chain mail (base 16) + shield (2) = 18."""
        armor = {"category": "heavy", "base_ac": 16}
        assert armor_class(2, armor, True) == 18

    def test_unarmored_defense_no_armor_dex_plus_1_con_mod_plus_2(self):
        """No armor with unarmored_defense_ability_mod=2: 10 + 1 + 2 = 13."""
        assert armor_class(1, None, False, {"unarmored_defense_ability_mod": 2}) == 13

    def test_unarmored_defense_no_armor_dex_plus_0_wis_mod_plus_3(self):
        """No armor, dex 0, WIS mod +3 (Monk): 10 + 0 + 3 = 13."""
        assert armor_class(0, None, False, {"unarmored_defense_ability_mod": 3}) == 13

    def test_unarmored_defense_ignored_if_wearing_armor(self):
        """Light armor (base 11) with unarmored_defense should IGNORE it: 11 + dex."""
        armor = {"category": "light", "base_ac": 11}
        result = armor_class(3, armor, False, {"unarmored_defense_ability_mod": 2})
        # Should be light armor math (11 + 3), NOT unarmored (10 + 3 + 2)
        assert result == 14

    def test_unarmored_defense_with_shield_no_armor(self):
        """Unarmored + shield: 10 + dex + ability + 2."""
        result = armor_class(1, None, True, {"unarmored_defense_ability_mod": 2})
        assert result == 15  # 10 + 1 + 2 + 2


class TestSpellSaveDC:
    """Test spell_save_dc(prof, ability_mod) → 8 + prof + ability_mod."""

    def test_prof_plus_2_ability_plus_3(self):
        """8 + 2 + 3 = 13."""
        assert spell_save_dc(2, 3) == 13

    def test_prof_plus_3_ability_plus_4(self):
        """8 + 3 + 4 = 15."""
        assert spell_save_dc(3, 4) == 15

    def test_prof_plus_2_ability_minus_1(self):
        """8 + 2 - 1 = 9."""
        assert spell_save_dc(2, -1) == 9

    def test_prof_plus_6_ability_plus_5(self):
        """8 + 6 + 5 = 19."""
        assert spell_save_dc(6, 5) == 19


class TestSpellAttackBonus:
    """Test spell_attack_bonus(prof, ability_mod) → prof + ability_mod."""

    def test_prof_plus_2_ability_plus_3(self):
        """2 + 3 = 5."""
        assert spell_attack_bonus(2, 3) == 5

    def test_prof_plus_3_ability_plus_4(self):
        """3 + 4 = 7."""
        assert spell_attack_bonus(3, 4) == 7

    def test_prof_plus_2_ability_minus_1(self):
        """2 - 1 = 1."""
        assert spell_attack_bonus(2, -1) == 1

    def test_prof_plus_6_ability_plus_5(self):
        """6 + 5 = 11."""
        assert spell_attack_bonus(6, 5) == 11


class TestCarryingCapacity:
    """Test carrying_capacity(str_score) → str_score * 15."""

    def test_str_10(self):
        """10 * 15 = 150."""
        assert carrying_capacity(10) == 150

    def test_str_16(self):
        """16 * 15 = 240."""
        assert carrying_capacity(16) == 240

    def test_str_8(self):
        """8 * 15 = 120."""
        assert carrying_capacity(8) == 120

    def test_str_20(self):
        """20 * 15 = 300."""
        assert carrying_capacity(20) == 300


class TestSpellsPreparedLimit:
    """Test spells_prepared_limit(cls, level, ability_mod)."""

    def test_cleric_level_1_wis_mod_plus_2(self):
        """Cleric: max(1, level + ability_mod) = max(1, 1+2) = 3."""
        assert spells_prepared_limit("Cleric", 1, 2) == 3

    def test_cleric_level_5_wis_mod_plus_3(self):
        """Cleric: max(1, 5+3) = 8."""
        assert spells_prepared_limit("Cleric", 5, 3) == 8

    def test_druid_level_1_wis_mod_plus_0(self):
        """Druid: max(1, 1+0) = 1."""
        assert spells_prepared_limit("Druid", 1, 0) == 1

    def test_druid_level_10_wis_mod_plus_4(self):
        """Druid: max(1, 10+4) = 14."""
        assert spells_prepared_limit("Druid", 10, 4) == 14

    def test_wizard_level_1_int_mod_minus_1(self):
        """Wizard: max(1, 1-1) = 1 (minimum floor)."""
        assert spells_prepared_limit("Wizard", 1, -1) == 1

    def test_wizard_level_5_int_mod_plus_3(self):
        """Wizard: max(1, 5+3) = 8."""
        assert spells_prepared_limit("Wizard", 5, 3) == 8

    def test_paladin_level_5_cha_mod_plus_3(self):
        """Paladin: max(1, (level // 2) + ability_mod) = max(1, 2+3) = 5."""
        assert spells_prepared_limit("Paladin", 5, 3) == 5

    def test_paladin_level_17_cha_mod_plus_4(self):
        """Paladin: max(1, 17//2 + 4) = max(1, 8+4) = 12."""
        assert spells_prepared_limit("Paladin", 17, 4) == 12

    def test_paladin_level_1_cha_mod_plus_2(self):
        """Paladin: max(1, 1//2 + 2) = max(1, 0+2) = 2."""
        assert spells_prepared_limit("Paladin", 1, 2) == 2

    def test_sorcerer_returns_none(self):
        """Sorcerer is a known caster, not prepared."""
        assert spells_prepared_limit("Sorcerer", 5, 3) is None

    def test_bard_returns_none(self):
        """Bard is a known caster, not prepared."""
        assert spells_prepared_limit("Bard", 10, 2) is None

    def test_ranger_returns_none(self):
        """Ranger is a known caster, not prepared."""
        assert spells_prepared_limit("Ranger", 7, 1) is None

    def test_warlock_returns_none(self):
        """Warlock is a known caster, not prepared."""
        assert spells_prepared_limit("Warlock", 12, 3) is None

    def test_barbarian_returns_none(self):
        """Barbarian is not a caster."""
        assert spells_prepared_limit("Barbarian", 5, 0) is None

    def test_fighter_returns_none(self):
        """Fighter is not a caster."""
        assert spells_prepared_limit("Fighter", 10, 1) is None

    def test_monk_returns_none(self):
        """Monk is not a caster."""
        assert spells_prepared_limit("Monk", 8, 2) is None

    def test_rogue_returns_none(self):
        """Rogue is not a caster."""
        assert spells_prepared_limit("Rogue", 9, 1) is None


class TestKnownSpellsLimit:
    """Test known_spells_limit(cls, level) using fixed table."""

    def test_sorcerer_level_1(self):
        """Sorcerer level 1 knows 2 spells."""
        assert known_spells_limit("Sorcerer", 1) == 2

    def test_sorcerer_level_5(self):
        """Sorcerer level 5 knows 6 spells."""
        assert known_spells_limit("Sorcerer", 5) == 6

    def test_sorcerer_level_11(self):
        """Sorcerer level 11 knows 12 spells."""
        assert known_spells_limit("Sorcerer", 11) == 12

    def test_sorcerer_level_20(self):
        """Sorcerer level 20 knows 15 spells."""
        assert known_spells_limit("Sorcerer", 20) == 15

    def test_bard_level_1(self):
        """Bard level 1 knows 2 spells (uses same table)."""
        assert known_spells_limit("Bard", 1) == 2

    def test_bard_level_10(self):
        """Bard level 10 knows 11 spells."""
        assert known_spells_limit("Bard", 10) == 11

    def test_ranger_level_1(self):
        """Ranger level 1 knows 2 spells."""
        assert known_spells_limit("Ranger", 1) == 2

    def test_ranger_level_5(self):
        """Ranger level 5 knows 6 spells."""
        assert known_spells_limit("Ranger", 5) == 6

    def test_warlock_level_1(self):
        """Warlock level 1 knows 2 spells."""
        assert known_spells_limit("Warlock", 1) == 2

    def test_warlock_level_20(self):
        """Warlock level 20 knows 15 spells."""
        assert known_spells_limit("Warlock", 20) == 15

    def test_cleric_returns_none(self):
        """Cleric prepares, doesn't know."""
        assert known_spells_limit("Cleric", 5) is None

    def test_wizard_returns_none(self):
        """Wizard prepares, doesn't know (well, copies to spellbook, but doesn't have a 'known' limit)."""
        assert known_spells_limit("Wizard", 10) is None

    def test_druid_returns_none(self):
        """Druid prepares, doesn't know."""
        assert known_spells_limit("Druid", 7) is None

    def test_paladin_returns_none(self):
        """Paladin prepares, doesn't know."""
        assert known_spells_limit("Paladin", 12) is None

    def test_barbarian_returns_none(self):
        """Barbarian is not a caster."""
        assert known_spells_limit("Barbarian", 5) is None

    def test_fighter_returns_none(self):
        """Fighter is not a caster."""
        assert known_spells_limit("Fighter", 10) is None

    def test_monk_returns_none(self):
        """Monk is not a caster."""
        assert known_spells_limit("Monk", 8) is None

    def test_rogue_returns_none(self):
        """Rogue is not a caster."""
        assert known_spells_limit("Rogue", 9) is None

    def test_known_spells_table_boundary_level_12(self):
        """Level 12 in known table is 12 (caps at 12 for mid-levels)."""
        assert known_spells_limit("Sorcerer", 12) == 12

    def test_known_spells_table_boundary_level_13(self):
        """Level 13 in known table is 13."""
        assert known_spells_limit("Sorcerer", 13) == 13

    def test_known_spells_table_boundary_level_14(self):
        """Level 14 in known table is 13 (stays at 13)."""
        assert known_spells_limit("Sorcerer", 14) == 13


class TestSkillBonus:
    """Test skill_bonus(ability_mod, proficient, expertise, prof)."""

    def test_mod_plus_2_no_proficiency(self):
        """2 + 0 + 0 = 2."""
        assert skill_bonus(2, False, False, 3) == 2

    def test_mod_plus_2_proficient(self):
        """2 + 3 + 0 = 5."""
        assert skill_bonus(2, True, False, 3) == 5

    def test_mod_plus_2_expertise(self):
        """2 + 0 + 3 = 5 (expertise without proficiency is allowed here, though unusual in 5e)."""
        assert skill_bonus(2, False, True, 3) == 5

    def test_mod_plus_2_proficient_and_expertise(self):
        """2 + 3 + 3 = 8 (expertise ADDS to proficiency, doesn't replace)."""
        assert skill_bonus(2, True, True, 3) == 8

    def test_mod_minus_1_proficient(self):
        """(-1) + 2 + 0 = 1."""
        assert skill_bonus(-1, True, False, 2) == 1

    def test_mod_plus_4_no_proficiency(self):
        """4 + 0 + 0 = 4."""
        assert skill_bonus(4, False, False, 2) == 4

    def test_mod_plus_3_proficient_prof_plus_5(self):
        """3 + 5 + 0 = 8."""
        assert skill_bonus(3, True, False, 5) == 8

    def test_mod_plus_1_proficient_expertise_prof_plus_3(self):
        """1 + 3 + 3 = 7."""
        assert skill_bonus(1, True, True, 3) == 7
