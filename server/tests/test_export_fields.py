"""Slice 7: the three exporters cover every sheet/derived key."""
import io

import yaml
import pytest
from pypdf import PdfReader

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


# ---- Slice 9: attacks and carrying capacity in every export ----------------


def _rogue_1(catalog):
    return resolve({
        "name": "R", "sources": ["srd"], "classes": [{"classId": "rogue", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 16, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [{"itemId": "longsword", "qty": 1, "equipped": True}], "skipped": False}, "details": {},
    }, catalog)


def test_yaml_carries_attacks_and_capacity(catalog):
    res = _rogue_1(catalog)
    doc = yaml.safe_load(to_yaml(res))
    assert doc["attacks"] == res["derived"]["attacks"]
    assert doc["carryingCapacity"] == res["derived"]["carryingCapacity"]
    assert doc["stealthDisadvantage"] is False
    dagger = next(a for a in doc["attacks"] if a["itemId"] == "dagger")
    assert dagger["attackBonus"] == 5 and dagger["damage"] == "1d4+3"


def test_markdown_and_pdf_list_attacks_and_capacity(catalog):
    res = _rogue_1(catalog)
    carried, capacity = res["derived"]["carryingCapacity"]["carried"], res["derived"]["carryingCapacity"]["capacity"]
    assert capacity == 165  # STR 10 + 1 (human) = 11, x 15
    md = to_markdown(res)
    assert "## Атаки" in md
    assert "- Dagger: +5, 1d4+3 piercing" in md
    # STR 11 (+0), rogue is proficient with longswords: +2, bare dice
    assert "- Longsword: +2, 1d8 slashing (versatile 1d10)" in md
    assert "## Носимост" in md and f"{carried}/{capacity} lb" in md
    assert "## Броня" not in md  # leather armor: no stealth disadvantage
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "Атаки" in text and "Dagger: +5, 1d4+3 piercing" in text and f"{carried}/{capacity} lb" in text


def test_over_capacity_and_stealth_armor_are_flagged(catalog):
    res = _rogue_1(catalog)
    res["derived"]["carryingCapacity"] = {"capacity": 100, "pushDragLift": 200, "carried": 130, "overCapacity": True}
    res["derived"]["stealthDisadvantage"] = True
    md = to_markdown(res)
    assert "130/100 lb (претоварен)" in md
    assert "## Броня" in md and "Недостатък при Скритост" in md


def test_markdown_and_pdf_show_dueling_damage(catalog):
    res = _rogue_1(catalog)
    for a in res["derived"]["attacks"]:
        if a["itemId"] == "longsword":
            a["duelingDamage"] = "1d8+2"
    md = to_markdown(res)
    assert "- Longsword: +2, 1d8 slashing (versatile 1d10), с Дуел 1d8+2" in md
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "с Дуел 1d8+2" in text
