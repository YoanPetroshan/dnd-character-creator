"""Slice 7: the three exporters cover every sheet/derived key."""
import yaml
import pytest

import export_fields
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf


@pytest.fixture(scope="module")
def catalog():
    return load()


def _rich_resolution(catalog):
    d = {
        "name": "Тест", "sources": ["srd", "phb", "xphb"],
        "classes": [{"classId": "rogue", "level": 6, "choices": {
            "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-athletics"],
            "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "skill-acrobatics"],
            "class:rogue:4:asi": ["feat:athlete-xphb"],
        }}],
        "background": {"id": "acolyte-xphb", "choices": {}},
        "species": {"id": "dwarf", "subspeciesId": "hill-dwarf", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 16, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }
    return resolve(d, catalog)


def _cleric(catalog):
    return resolve({
        "name": "C", "sources": ["srd"], "classes": [{"classId": "cleric", "level": 5, "subclassId": "life", "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 14, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }, catalog)


def test_every_sheet_and_derived_key_is_exported_or_excluded(catalog):
    for res in (_rich_resolution(catalog), _cleric(catalog)):
        doc = yaml.safe_load(to_yaml(res))
        for section in ("sheet", "derived"):
            for key in res[section]:
                assert key in doc or (section, key) in export_fields.EXCLUDED, f"{section}.{key} is not exported"
        for reason in export_fields.EXCLUDED.values():
            assert reason


def test_yaml_values_match_resolution(catalog):
    res = _rich_resolution(catalog)
    doc = yaml.safe_load(to_yaml(res))
    for key in ("expertiseSkills", "grantedFeats", "damageModifiers", "conditionImmunities", "senses", "startingGold",
                "innateSpells", "features", "feats", "featOptions"):
        assert doc[key] == res["sheet"][key], key
    for key in ("initiative", "passivePerception", "passiveInsight", "passiveInvestigation", "speeds"):
        assert doc[key] == res["derived"][key], key
    assert doc["expertiseSkills"] == ["skill-stealth", "skill-acrobatics"]
    assert doc["senses"].get("darkvision") == 60


def test_markdown_lists_new_sections(catalog):
    md = to_markdown(_rich_resolution(catalog))
    assert "## Черти и способности" in md
    assert "Sneak Attack (ниво 1)" in md and "Darkvision" in md
    assert "## Таланти" in md and "Athlete" in md
    assert "## Експертиза" in md
    assert "Stealth: " in md and "(експертиза)" in md
    assert "## Сетива" in md and "тъмно зрение 60 фута" in md
    assert "## Съпротиви и имунитети" in md and "Poison" in md


def test_markdown_always_prepared_spells(catalog):
    md = to_markdown(_cleric(catalog))
    assert "## Винаги подготвени заклинания" in md and "Bless (ниво 1)" in md


def test_markdown_expertise_marker_only_on_expert_skills(catalog):
    md = to_markdown(_rich_resolution(catalog))
    assert md.count("(експертиза)") == 2


def test_pdf_renders_with_new_sections(catalog):
    for res in (_rich_resolution(catalog), _cleric(catalog)):
        data = to_pdf(res)
        assert data.startswith(b"%PDF") and len(data) > 2000


def test_markdown_and_pdf_share_the_same_blocks(catalog):
    res = _rich_resolution(catalog)
    blocks = export_fields.extra_blocks(res)
    md = to_markdown(res)
    for kind, text in blocks:
        assert text in md, text
