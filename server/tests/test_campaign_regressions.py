"""Regressions for the REAL-BUG findings of the verification campaign (VF slices, docs/CAMPAIGN-PROTOCOL.md).

Each test was written failing first (the failing spec of the finding), then the engine was fixed. One section per fix;
the data quotes are pinned against the vendored 5etools records so a data refresh that changes a rule fails here."""
from __future__ import annotations

import json
import pathlib

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="official data not fetched")

DATA = pathlib.Path(__file__).resolve().parents[1] / "data" / "official"
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2014", species="human", subspecies=None, scores=None, background="acolyte", sources=(), added=(),
           class_choices=None):
    entries = []
    for i, spec in enumerate(classes):
        e = {"classId": spec[0], "level": spec[1], "choices": dict((class_choices or {}).get(i, {}))}
        if len(spec) > 2 and spec[2]:
            e["subclassId"] = spec[2]
        entries.append(e)
    base = {a: 10 for a in ABS}
    base.update(scores or {})
    sp = {"id": species, "choices": {}}
    if subspecies:
        sp["subraceId"] = subspecies
    return {"name": "t", "ruleset": ruleset, "sources": list(sources), "classes": entries,
            "background": {"id": background, "choices": {}}, "species": sp,
            "abilities": {"method": "manual", "base": base},
            "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": False},
            "details": {}}


# ---------------------------------------------------------------- VF1.1 TCE Glory Paladin 7 Aura of Alacrity
def test_vf1_1_data_quote_tce_aura_of_alacrity():
    recs = json.load(open(DATA / "class" / "class-paladin.json"))["subclassFeature"]
    tce = next(r for r in recs if r["name"] == "Aura of Alacrity" and r["source"] == "TCE")
    assert tce["level"] == 7 and tce["subclassShortName"] == "Glory"
    assert "Your walking speed increases by 10 feet." in tce["entries"][1]


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_vf1_1_glory_tce_7_adds_ten_feet_of_walking_speed(catalog, ruleset):
    base = _draft([("paladin", 7, "glory-tce")], ruleset=ruleset)
    other = _draft([("paladin", 7, "devotion")], ruleset=ruleset)
    glory = resolve(base, catalog)["derived"]["speeds"]
    plain = resolve(other, catalog)["derived"]["speeds"]
    assert glory["walk"] == plain["walk"] + 10


def test_vf1_1_glory_tce_6_has_no_bonus(catalog):
    a = resolve(_draft([("paladin", 6, "glory-tce")]), catalog)["derived"]["speeds"]
    b = resolve(_draft([("paladin", 6, "devotion")]), catalog)["derived"]["speeds"]
    assert a["walk"] == b["walk"]


# ---------------------------------------------------------------- VF1.2 a spell id starting with "skill-" is not a skill
def _skill_ids(catalog):
    from catalog import reference_data
    return set(reference_data.SKILL_ABILITY)


def test_vf1_2_skill_empowerment_is_a_spell_not_a_skill(catalog):
    """spells-xge.json Skill Empowerment is a spell; the engine took every selected id starting with 'skill-' as a skill."""
    spells = json.load(open(DATA / "spells" / "spells-xge.json"))["spell"]
    assert any(s["name"] == "Skill Empowerment" and s["level"] == 5 for s in spells)
    for ruleset in ("2014", "mixed", "2024"):
        d = _draft([("bard", 9)], ruleset=ruleset)
        d["classes"][0]["choices"] = {"class:bard:spells-known": ["skill-empowerment"]}
        res = resolve(d, catalog)
        card = next(c for c in res["choices"] if c["id"] == "class:bard:spells-known")
        assert "skill-empowerment" in card["selected"], ruleset
        skills = res["sheet"]["proficiencies"]["skills"]
        assert "skill-empowerment" not in skills, ruleset
        assert set(skills) <= _skill_ids(catalog), ruleset
        assert "skill-empowerment" not in {k for k in res["derived"]["skills"]}, ruleset


def test_vf1_2_no_skill_option_of_a_proficiency_card_is_blocked_by_a_spell_id(catalog):
    """The duplicate-skill gate reads the picked skills of other cards: a Bard 9 with the spell picked offers the same
    skill options (none disabled for a 'duplicate' of the spell id) as without it."""
    def options(pick):
        d = _draft([("bard", 9)], ruleset="2014")
        if pick:
            d["classes"][0]["choices"] = {"class:bard:spells-known": ["skill-empowerment"]}
        res = resolve(d, catalog)
        return {c["id"]: [(o["id"], o.get("disabled")) for o in c["options"]] for c in res["choices"]
                if c["options"] and all(o["id"].startswith("skill-") and o["id"] != "skill-empowerment" for o in c["options"])}
    assert options(True) == options(False)
