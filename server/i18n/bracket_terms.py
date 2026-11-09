"""T1 (owner decision 2026-11-05): a Bulgarian rules term is followed by its English term in brackets, "Талант (Feat)".

`BRACKET_TERMS` is the one list of English terms that may stand in such brackets, in the Bulgarian server messages, the
Bulgarian export labels, the glossary and the Bulgarian web UI copy. The frontend guard (`copyGuards.test.ts`,
`BRACKET_TERMS` there) holds the same list and a test (`test_t1_brackets.py`) compares the two. Casing is the glossary's /
the PHB's (Title Case), also where the Bulgarian word is lower case: "кратка почивка (Short Rest)".

A bracket may also hold a Bulgarian head and the term ("(експертиза, Expertise)", the tag after a skill) or the term
and the abbreviation ("(Armor Class, AC)", "(Tool Proficiency, {category})").
"""
from __future__ import annotations

import re

BRACKET_TERMS = frozenset({
    "Ability", "Ability Checks", "Ability Score", "Ability Score Improvement", "Ability Score Increase", "Ability Scores",
    "Armor Class", "Background", "Blindsight", "Bonus Action", "Breath Weapon", "Cantrip", "Cantrips", "Cantrips Known",
    "Carrying Capacity", "Class Features", "Darkvision", "Devil's Sight", "Disadvantage", "Draconic Ancestry", "Expertise", "Feat",
    "Feat Prerequisites", "Feats", "Feature", "Features", "General Feats", "Hit Point Dice", "Hit Points", "Immunities",
    "Immunity", "Long Rest", "Origin Feat", "Origin Feats", "Other Expertise", "Proficiencies", "Proficiency",
    "Proficiency Bonus", "Resistance", "Saving Throw", "Saving Throws", "Senses", "Short Rest", "Skill",
    "Skill Proficiencies", "Skill Proficiency", "Skill or Tool Proficiency", "Skills", "Species", "Spell Attack Modifier",
    "Spell Mastery", "Spell Save DC", "Spellcasting Ability", "Tool Proficiencies", "Tool Proficiency", "Tremorsense",
    "Truesight", "Vulnerability", "Weapon Mastery", "Weapon Proficiencies",
})

# Latin words in brackets that are not rules terms (abbreviations, codes, other glosses the app always had).
NON_TERM_BRACKETS = frozenset({
    "AC", "DC", "STR", "DEX", "CON", "INT", "WIS", "CHA", "JSON", "Sources", "Intelligence", "Wisdom", "Charisma",
})

_BRACKET = re.compile(r"\(([^()]*)\)")
_CYRILLIC = re.compile("[Ѐ-ӿ]")
_FOLDED = {t.casefold() for t in BRACKET_TERMS}


def bracket_problems(text: str) -> list[str]:
    """Brackets in `text` that look like a rules term but are not a registered one (a typo in case or wording)."""
    out = []
    for inner in _BRACKET.findall(text):
        if not re.search("[A-Za-z]", inner):
            continue
        for part in (p.strip() for p in inner.split(",")):
            if (not part or _CYRILLIC.search(part) or part.startswith("{") or part in BRACKET_TERMS
                    or part in NON_TERM_BRACKETS or not re.search("[A-Za-z]", part)):
                continue
            if part.casefold() in _FOLDED:
                out.append(f"({inner}): '{part}' is a registered term with other casing")
            elif re.match(r"^[A-Z][A-Za-z' ]*$", part):
                out.append(f"({inner}): '{part}' is not a registered bracket term")
    return out


def strip_term_brackets(text: str) -> str:
    """`text` without the bracket groups made of registered terms (what is left must obey the older Latin rules)."""
    def drop(m: re.Match) -> str:
        parts = [p.strip() for p in m.group(1).split(",")]
        ok = all(p in BRACKET_TERMS or p in NON_TERM_BRACKETS or _CYRILLIC.search(p) or p.startswith("{") for p in parts)
        has_term = any(p in BRACKET_TERMS for p in parts)
        return "" if ok and has_term else m.group(0)
    return _BRACKET.sub(drop, text)
