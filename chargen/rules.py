"""D&D 5e rules engine — pure functions for character mechanics.

This module implements the core 5e SRD rules for character advancement,
ability calculations, and spell mechanics. All functions are pure and
deterministic with no I/O or side effects.
"""


def ability_modifier(score: int) -> int:
    """Compute ability modifier from ability score.

    Standard 5e formula: (score - 10) // 2 using floor division.

    Args:
        score: Ability score (typically 1-20, but supports any int).

    Returns:
        Ability modifier (e.g. 10→0, 16→+3, 7→-2).
    """
    return (score - 10) // 2


def proficiency_bonus(total_level: int) -> int:
    """Compute proficiency bonus based on character level.

    Breakpoints (character level, summed across all classes for multiclass):
    - levels 1-4 → +2
    - levels 5-8 → +3
    - levels 9-12 → +4
    - levels 13-16 → +5
    - levels 17-20 → +6

    Args:
        total_level: Total character level (sum of all class levels for multiclass).

    Returns:
        Proficiency bonus (+2 to +6).
    """
    if total_level < 5:
        return 2
    elif total_level < 9:
        return 3
    elif total_level < 13:
        return 4
    elif total_level < 17:
        return 5
    else:
        return 6


def hit_points(hit_die: int, con_mod: int, level: int, method: str = "max_then_average") -> int:
    """Compute total hit points.

    Two calculation methods:
    - "max_then_average": L1 takes max die + con_mod; each level after adds
      average_die + con_mod where average_die = hit_die // 2 + 1 (d6→4, d8→5, d10→6, d12→7).
    - "max_then_max": every level takes max die + con_mod (house rule).

    Result is clamped to minimum 1 (even with extreme negative CON mod).

    Args:
        hit_die: Hit die size (typically 6, 8, 10, or 12).
        con_mod: Constitution modifier.
        level: Character level.
        method: "max_then_average" (default) or "max_then_max".

    Returns:
        Total hit points (at least 1).
    """
    if method == "max_then_max":
        total = level * (hit_die + con_mod)
    else:  # max_then_average (default)
        average_die = hit_die // 2 + 1
        total = hit_die + con_mod + (level - 1) * (average_die + con_mod)

    return max(1, total)


def armor_class(
    dex_mod: int,
    armor: dict | None,
    shield: bool,
    class_features: dict | None = None,
) -> int:
    """Compute Armor Class.

    Rules:
    - No armor: 10 + dex_mod, or 10 + dex_mod + class_feature (if unarmored_defense).
    - Light armor: base_ac + dex_mod (full dex bonus, uncapped).
    - Medium armor: base_ac + min(dex_mod, 2) (dex capped at +2).
    - Heavy armor: base_ac (no dex bonus, even negative dex is ignored).
    - Shield: +2 to the result (works with any armor state).
    - class_features: dict with optional "unarmored_defense_ability_mod" (e.g. CON for Barbarian,
      WIS for Monk); only applies when armor is None.

    Args:
        dex_mod: Dexterity modifier.
        armor: None or dict with {"category": "light"|"medium"|"heavy", "base_ac": int}.
        shield: True if using a shield.
        class_features: Optional dict with unarmored defense overrides.

    Returns:
        Armor Class (10 or higher).
    """
    if armor is None:
        # Unarmored defense
        ac = 10 + dex_mod
        if class_features and "unarmored_defense_ability_mod" in class_features:
            ac += class_features["unarmored_defense_ability_mod"]
    else:
        category = armor["category"]
        base_ac = armor["base_ac"]

        if category == "light":
            ac = base_ac + dex_mod
        elif category == "medium":
            ac = base_ac + min(dex_mod, 2)
        else:  # heavy
            ac = base_ac

    if shield:
        ac += 2

    return ac


def spell_save_dc(prof: int, ability_mod: int) -> int:
    """Compute spell save DC.

    Formula: 8 + proficiency_bonus + ability_modifier.

    Args:
        prof: Proficiency bonus.
        ability_mod: Relevant ability modifier (e.g. WIS for Cleric).

    Returns:
        Spell save DC.
    """
    return 8 + prof + ability_mod


def spell_attack_bonus(prof: int, ability_mod: int) -> int:
    """Compute spell attack bonus.

    Formula: proficiency_bonus + ability_modifier.

    Args:
        prof: Proficiency bonus.
        ability_mod: Relevant ability modifier (e.g. DEX for ranged attacks).

    Returns:
        Spell attack bonus.
    """
    return prof + ability_mod


def carrying_capacity(str_score: int) -> int:
    """Compute carrying capacity in pounds.

    Formula: str_score * 15 per SRD.

    Args:
        str_score: Strength score.

    Returns:
        Carrying capacity in pounds.
    """
    return str_score * 15


def spells_prepared_limit(cls: str, level: int, ability_mod: int) -> int | None:
    """Compute prepared spells limit.

    Returns None for classes that don't prepare spells (non-casters and known-caster classes).

    Prepared casters use: max(1, level + ability_mod)
    Exception: Paladin uses half-level formula: max(1, (level // 2) + ability_mod)

    Prepared casters: Cleric, Druid, Wizard, Paladin
    Known casters (returns None): Bard, Ranger, Sorcerer, Warlock
    Non-casters (returns None): Barbarian, Fighter, Monk, Rogue

    Args:
        cls: Class name (exact match, e.g. "Cleric", "Paladin").
        level: Character level in this class.
        ability_mod: Relevant ability modifier (WIS for Cleric/Druid, INT for Wizard, CHA for Paladin).

    Returns:
        Prepared spells limit (at least 1), or None if class doesn't prepare.
    """
    prepared_casters = {"Cleric", "Druid", "Wizard", "Paladin"}

    if cls not in prepared_casters:
        return None

    if cls == "Paladin":
        return max(1, (level // 2) + ability_mod)
    else:
        return max(1, level + ability_mod)


def known_spells_limit(cls: str, level: int) -> int | None:
    """Compute known spells limit.

    Returns None for prepared casters and non-casters.

    For known-caster classes (Bard, Ranger, Sorcerer, Warlock), returns a fixed
    lookup table. Uses a unified Sorcerer table across all four classes as a
    simplified placeholder; once chargen/catalog.py exists with verified per-class
    5e-SRD-Levels.json data, this should be replaced with individual class tables.

    Known-casters table (spells known by level 1-20):
    {1:2, 2:3, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9, 9:10, 10:11, 11:12, 12:12,
     13:13, 14:13, 15:14, 16:14, 17:15, 18:15, 19:15, 20:15}

    Args:
        cls: Class name (exact match, e.g. "Sorcerer", "Bard").
        level: Character level in this class.

    Returns:
        Known spells limit, or None if class prepares or doesn't cast.
    """
    known_casters = {"Bard", "Ranger", "Sorcerer", "Warlock"}

    if cls not in known_casters:
        return None

    # TODO: replace with per-class real tables once chargen/catalog.py exists
    # to look them up from 5e-SRD-Levels.json — for now this shared placeholder
    # is deliberately conservative/approximate, not vendor-verified per class.
    known_spells_table = {
        1: 2,
        2: 3,
        3: 4,
        4: 5,
        5: 6,
        6: 7,
        7: 8,
        8: 9,
        9: 10,
        10: 11,
        11: 12,
        12: 12,
        13: 13,
        14: 13,
        15: 14,
        16: 14,
        17: 15,
        18: 15,
        19: 15,
        20: 15,
    }

    return known_spells_table.get(level, 15)  # default to 15 if level > 20 (shouldn't happen)


def skill_bonus(ability_mod: int, proficient: bool, expertise: bool, prof: int) -> int:
    """Compute skill check bonus.

    Formula: ability_mod + (prof if proficient else 0) + (prof if expertise else 0)

    Note: expertise adds to a proficient bonus rather than replacing it.
    A character with both proficient=True and expertise=True gets
    ability_mod + prof + prof (double proficiency), not just prof once.

    Args:
        ability_mod: Relevant ability modifier.
        proficient: True if the character is proficient in this skill.
        expertise: True if the character has expertise (doubles proficiency; requires proficiency in real 5e, but validated elsewhere).
        prof: Proficiency bonus.

    Returns:
        Skill check bonus.
    """
    return ability_mod + (prof if proficient else 0) + (prof if expertise else 0)
