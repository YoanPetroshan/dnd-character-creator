"""Feat prerequisite text in Bulgarian (`feat_prerequisite_text(..., lang="bg")`, catalog keys `feat-prereq-*`)."""
from __future__ import annotations

import json
import re

import pytest

import service
from i18n.catalog import feat_prereq
from i18n.messages import validate_catalog
from sheet_data import feat_prerequisite_text

needs_official = pytest.mark.skipif("athlete-xphb" not in service._catalog.feats, reason="needs the official data")


def both(*alts, feats=None):
    feat = {"prerequisite": list(alts)}
    return feat_prerequisite_text(feat, feats or {}, "en"), feat_prerequisite_text(feat, feats or {}, "bg")


CASES = [
    ({"level": 4}, "Level 4", "Ниво 4 или по-високо"),
    ({"level": {"level": 1, "class": {"name": "Wizard"}}}, "Wizard level 1", "Wizard ниво 1 или по-високо"),
    ({"level": 4, "ability": [{"str": 13}]}, "Level 4, Strength 13", "Ниво 4 или по-високо, Strength 13 или повече"),
    ({"ability": [{"int": 13}, {"wis": 13}]}, "Intelligence 13 or Wisdom 13", "Intelligence 13 или повече или Wisdom 13 или повече"),
    ({"race": [{"name": "elf", "subrace": "drow"}]}, "Drow Elf", "Drow Elf"),
    ({"race": [{"name": "elf"}, {"name": "half-elf"}]}, "Elf, Half-Elf", "Elf, Half-Elf"),
    ({"background": [{"name": "Rune Carver", "displayEntry": "{@background Rune Carver|BGG}"}]}, "Rune Carver", "Rune Carver"),
    ({"feat": ["magic initiate|xphb"]}, "Magic Initiate feat", "Талант (Feat): Magic Initiate"),
    ({"feat": ["a|x", "b|x"]}, "A or B feat", "Талант (Feat): A или B"),
    ({"feature": ["Fighting Style"]}, "Fighting Style feature", "Способност (Feature): Fighting Style"),
    ({"feature": ["Spellcasting", "Pact Magic"]}, "Spellcasting or Pact Magic feature", "Способност (Feature): Spellcasting или Pact Magic"),
    ({"spellcasting2020": True}, "Spellcasting or Pact Magic feature", "Способност (Feature): Spellcasting или Pact Magic"),
    ({"spellcastingFeature": True}, "Spellcasting or Pact Magic feature", "Способност (Feature): Spellcasting или Pact Magic"),
    ({"spellcasting": True}, "The ability to cast at least one spell", "Способност да изричаш поне едно заклинание"),
    ({"proficiency": [{"armor": "medium"}]}, "Proficiency with medium armor", "Владеене (Proficiency) на средна броня"),
    ({"proficiency": [{"armor": "light"}]}, "Proficiency with light armor", "Владеене (Proficiency) на лека броня"),
    ({"proficiency": [{"armor": "heavy"}]}, "Proficiency with heavy armor", "Владеене (Proficiency) на тежка броня"),
    ({"proficiency": [{"armor": "shield"}]}, "Proficiency with shield", "Владеене (Proficiency) на щитове"),
    ({"proficiency": [{"weapon": "martial"}]}, "Proficiency with martial weapons", "Владеене (Proficiency) на бойни оръжия"),
    ({"proficiency": [{"weaponGroup": "martial"}]}, "Proficiency with martial weapons", "Владеене (Proficiency) на бойни оръжия"),
    ({"proficiency": [{"armor": "exotic"}]}, "Proficiency with exotic armor", "Владеене (Proficiency) на броня: exotic"),
    ({"featCategory": ["D"]}, "A Dragonmark feat", "Талант (Feat) Dragonmark"),
    ({"featCategory": ["O"]}, "A feat of a required category", "Талант (Feat) от изискваната категория"),
    ({"other": "No other dragonmark"}, "No other dragonmark", "Без друг драконов знак (Dragonmark)"),
    ({"other": "Something new"}, "Something new", "Something new"),  # unknown free text falls back to English
    ({"otherSummary": {"entry": "When Gaining ...", "entrySummary": "Special"}}, "Special", "Специално"),
    ({"campaign": ["Eberron"]}, "Campaign: Eberron", "Кампания: Eberron"),
    ({"campaign": ["A", "B"]}, "Campaign: A, B", "Кампания: A, B"),
]


@pytest.mark.parametrize("alt,en,bg", CASES)
def test_pattern_family(alt, en, bg):
    assert both(alt) == (en, bg)


def test_alternatives_join_and_dedupe():
    en, bg = both({"level": 4, "ability": [{"str": 13}]}, {"level": 4, "ability": [{"dex": 13}]})
    assert en == "Level 4, Strength 13; or Level 4, Dexterity 13"
    assert bg == "Ниво 4 или по-високо, Strength 13 или повече; или Ниво 4 или по-високо, Dexterity 13 или повече"
    assert both({"level": 4}, {"level": 4}) == ("Level 4", "Ниво 4 или по-високо")


def test_no_prerequisite_is_empty():
    assert both() == ("", "")
    assert feat_prerequisite_text({}, {}, "bg") == ""


def test_default_lang_is_english_and_bad_lang_raises():
    assert feat_prerequisite_text({"prerequisite": [{"level": 4}]}, {}) == "Level 4"
    with pytest.raises(ValueError):
        feat_prerequisite_text({}, {}, "de")


def test_catalog_valid_and_has_bulgarian():
    assert validate_catalog(feat_prereq.MESSAGES, require_bg=True) == []


@needs_official
def test_every_catalog_feat_renders():
    feats = service._catalog.feats
    assert len(feats) > 300
    for key, feat in feats.items():
        en = feat_prerequisite_text(feat, feats, "en")
        bg = feat_prerequisite_text(feat, feats, "bg")
        assert bool(bg) == bool(en), key
        assert not re.search(r"\b(Level|Proficiency with|Campaign:|feature|feat)\b", bg.replace("(Feature)", "").replace("(Feat)", "")), (key, bg)


@needs_official
def test_route_serves_bulgarian_prerequisite():
    def get(path, query):
        status, _ct, _h, body = service.handle("GET", path, query)
        return json.loads(body)
    assert get("/api/feats/athlete-xphb", "lang=bg")["prerequisite"].startswith("Ниво 4 или по-високо, Strength 13 или повече")
    assert get("/api/feats/athlete-xphb", "lang=en")["prerequisite"] == "Level 4, Strength 13; or Level 4, Dexterity 13"
