"""T1 (owner decision 2026-11-05): a Bulgarian rules term is followed by its English term in brackets, "Талант (Feat)".

What is checked here (the per-term coverage and the old-wording ban live in test_terms_table.py, the Latin guard of the web
UI in frontend/src/copyGuards.test.ts):

* every Latin bracket in the Bulgarian server messages, export labels, glossary and web UI copy is a registered term
  (`i18n/bracket_terms.py`), spelled exactly, and every registered term is used somewhere;
* the frontend guard holds the same list;
* the glossary `bg` of every decided term ends with its bracket (and `Spell Slots` has none);
* inside one Bulgarian text a term's bracket appears once (the first occurrence), except where one text has two branches;
* the English side carries no bracket and no Cyrillic: EN mode is untouched.
"""
from __future__ import annotations

import pathlib
import re

import export_labels
from i18n import glossary
from i18n.bracket_terms import BRACKET_TERMS, bracket_problems
from i18n.catalog import MESSAGES
from i18n.review_table import _copy_text, _flatten_labels
from i18n.terms_table import TERMS, _corpus
from i18n.ts_copy import COPY_DIR, flatten, parse_catalog

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CYRILLIC = re.compile("[Ѐ-ӿ]")
BRACKET = re.compile(r"\(([^()]*)\)")


def test_every_latin_bracket_of_the_bulgarian_texts_is_a_registered_term():
    problems = []
    for surface, key, text in _corpus():
        problems += [f"{surface}:{key}: {p}" for p in bracket_problems(text) if "${" not in p]
    assert problems == []


def test_every_registered_term_is_used_and_none_is_misspelled():
    used = set()
    for _surface, _key, text in _corpus():
        for inner in BRACKET.findall(text):
            used.update(p.strip() for p in inner.split(","))
    assert sorted(BRACKET_TERMS - used) == [], "registered but never used: remove it from i18n/bracket_terms.py"


def test_the_frontend_guard_holds_the_same_list():
    src = (REPO / "frontend" / "src" / "copyGuards.test.ts").read_text(encoding="utf-8")
    block = src.split("// BRACKET_TERMS_START", 1)[1].split("// BRACKET_TERMS_END", 1)[0]
    assert set(re.findall(r'"([^"]+)"', block)) == set(BRACKET_TERMS)


# The decided glossary terms: bg = "<Bulgarian> (<English>)". The glossary terms outside the 29 rows of the proposal
# (initiative, speed, passive*, preparedSpells, spellbook, languages, equipment, size, feet, gold) are unchanged.
DECIDED = ("abilityScores", "armorClass", "hitPoints", "hitPointDice", "proficiencyBonus", "savingThrows", "skills",
           "spellSaveDc", "spellAttackBonus", "cantrips", "species", "background", "originFeat", "feats", "classFeatures",
           "weaponMastery", "senses", "darkvision", "blindsight", "tremorsense", "truesight", "resistance", "immunity",
           "vulnerability", "shortRest", "longRest", "carryingCapacity")


def test_the_decided_glossary_terms_end_with_their_english_term():
    data = glossary.load()
    for tid in DECIDED:
        m = re.search(r" \(([^()]*)\)$", data[tid]["bg"])
        assert m, tid
        assert bracket_problems(data[tid]["bg"]) == [] and not CYRILLIC.search(m.group(1)), tid
        assert any(p.strip() in BRACKET_TERMS for p in m.group(1).split(",")), tid
    assert data["spellSlots"]["bg"] == "Spell Slots"  # English only, no brackets (owner decision)
    for tid in set(data) - set(DECIDED) - {"spellSlots"}:
        assert "(" not in data[tid]["bg"], tid  # the rest of the glossary is outside the 29 rows and unchanged


def test_the_glossary_term_is_the_bulgarian_noun_of_its_row():
    """Every TERMS row with a glossary id: the glossary bg matches the row's decided noun check."""
    data = glossary.load()
    for t in TERMS:
        if t.gloss and t.gloss in DECIDED and t.checks:
            noun, bracket = t.checks[0]
            assert re.search(noun, data[t.gloss]["bg"], re.IGNORECASE), (t.en, data[t.gloss]["bg"])
            assert re.search(bracket, " ".join(BRACKET.findall(data[t.gloss]["bg"])), re.IGNORECASE), (t.en, data[t.gloss]["bg"])


# one Bulgarian text with two branches of a conditional prints the bracket in each branch
ONE_BRACKET_PER_TEXT_EXCEPTIONS = {
    "UI:sheet.resources.text.shortRestRegains": "singular and plural branch of one template",
}


def test_a_term_bracket_appears_once_per_text():
    again = []
    for surface, key, text in _corpus():
        if f"{surface}:{key}" in ONE_BRACKET_PER_TEXT_EXCEPTIONS:
            continue
        seen: dict[str, int] = {}
        for inner in BRACKET.findall(text):
            for part in (p.strip() for p in inner.split(",")):
                if part in BRACKET_TERMS:
                    seen[part] = seen.get(part, 0) + 1
        again += [f"{surface}:{key}: ({p}) x{n}" for p, n in seen.items() if n > 1]
    assert again == []


def test_the_english_side_has_no_brackets_of_terms_and_no_cyrillic():
    """EN mode is unchanged: the English catalogs, labels and copy carry no bracketed term and no Cyrillic."""
    texts = [(f"msg:{k}", v["en"]) for k, v in MESSAGES.items()]
    texts += [(f"exp:{k}", t) for k, t in _flatten_labels(export_labels.LABELS["en"])]
    gloss = glossary.load()
    en = flatten(parse_catalog(COPY_DIR / "en.ts", "en"))
    texts += [(f"UI:{k}", _copy_text(leaf, gloss, "en")) for k, leaf in en.items()]
    texts += [(f"gloss:{k}", d["en"]) for k, d in gloss.items()]
    for where, text in texts:
        assert not CYRILLIC.search(text), where
        for inner in BRACKET.findall(text):
            assert not any(p.strip() in BRACKET_TERMS for p in inner.split(",")), (where, inner)
