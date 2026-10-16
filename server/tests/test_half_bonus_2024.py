"""F-D9 (FE12, refined in FX): Jack of All Trades off Initiative under ruleset 2024 only.

Governing XPHB texts (catalog ``features``, tags stripped):

  xphb-bard-2-jack-of-all-trades   "You can add half your Proficiency Bonus (round down) to any ability check you
                                    make that uses a skill proficiency you lack and that doesn't otherwise use
                                    your Proficiency Bonus."
  champion-xphb-3-remarkable-athlete   "you have Advantage on Initiative rolls and Strength (Athletics) checks."

Rule matrix:
  * 2024 Jack of All Trades: half PB (rounded down) on skill checks of skills the character lacks; NOT on
    Initiative (a plain Dexterity check, no skill proficiency) -> initiative = DEX modifier.
  * Remarkable Athlete: unchanged in every ruleset (FX refinement). The XPHB Champion text has no proficiency-bonus
    clause, but only the SRD id `remarkable-athlete` is mapped, so the SRD / 2014 `champion` keeps its half PB.
  * mixed and 2014 keep the 2014 (SRD) texts: Jack of All Trades adds half PB to every check without the
    proficiency bonus, Remarkable Athlete half PB (rounded up) to STR / DEX / CON checks; both reach Initiative.
  * The skill list of a proficient skill is untouched everywhere (full PB, Expertise double)."""
import re

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(text):
    return re.sub(r"\{@\w+ ([^}|]*)[^}]*\}", r"\1", " ".join(text) if isinstance(text, list) else text)


def _res(catalog, cls, level, ruleset, sub=None, dex=14):
    scores = {a: 10 for a in ABS}
    scores["DEX"] = dex
    xphb = ruleset == "2024"
    return resolve({
        "name": "t", "ruleset": ruleset, "sources": [],
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}],
        # soldier-xphb grants Savage Attacker, not Alert: initiative stays a pure Dexterity roll
        "background": {"id": "soldier-xphb" if xphb else "acolyte", "choices": {}},
        "species": {"id": "human-xphb" if xphb else "human", "choices": {}},
        "abilities": {"method": "manual", "base": scores},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}, "preferences": {},
    }, catalog)


def _dex_mod(r):
    return (r["sheet"]["abilities"]["DEX"] - 10) // 2


def test_quotes_match_the_catalog(catalog):
    jack = _plain(catalog.features["xphb-bard-2-jack-of-all-trades"]["desc"])
    assert ("any ability check you make that uses a skill proficiency you lack and that doesn't otherwise use "
            "your Proficiency Bonus") in jack
    assert "initiative" not in jack.lower()
    remarkable = _plain(catalog.features["champion-xphb-3-remarkable-athlete"]["desc"])
    assert "you have Advantage on Initiative rolls and Strength (Athletics) checks" in remarkable
    assert "Proficiency Bonus" not in remarkable
    # the 2014 (SRD) texts that mixed / 2014 keep
    assert "any ability check you make that doesn't already include your proficiency bonus" in _plain(
        catalog.features["jack-of-all-trades"]["desc"])
    assert "add half your proficiency bonus (round up) to any Strength, Dexterity, or Constitution check" in _plain(
        catalog.features["remarkable-athlete"]["desc"])


def test_2024_jack_of_all_trades_is_not_added_to_initiative(catalog):
    r = _res(catalog, "bard", 2, "2024")
    assert r["derived"]["initiative"] == _dex_mod(r)


def test_2024_jack_of_all_trades_still_helps_skills_without_proficiency(catalog):
    r = _res(catalog, "bard", 2, "2024")
    d = r["derived"]
    assert "skill-stealth" not in r["sheet"]["proficiencies"]["skills"]
    assert d["skills"]["skill-stealth"] == _dex_mod(r) + 1          # half of PB 2
    assert d["passiveInvestigation"] == 10 + (r["sheet"]["abilities"]["INT"] - 10) // 2 + 1


def test_2024_jack_of_all_trades_leaves_proficient_skills_at_full_bonus(catalog):
    r = _res(catalog, "bard", 2, "2024")
    prof = r["sheet"]["proficiencies"]["skills"][0]
    # proficient skills never get the half bonus on top: same value as before Jack of All Trades (level 1)
    assert r["derived"]["skills"][prof] == _res(catalog, "bard", 1, "2024")["derived"]["skills"][prof]


def test_2024_remarkable_athlete_of_the_srd_champion_is_left_alone(catalog):
    # FX (4): only the Jack of All Trades initiative bonus is dropped under 2024. The SRD / 2014 `champion`
    # subclass keeps its own Remarkable Athlete half bonus in every ruleset (the XPHB Champion never had it;
    # only the SRD id `remarkable-athlete` is mapped).
    r = _res(catalog, "fighter", 7, "2024", "champion")
    plain = _res(catalog, "fighter", 7, "2024")
    assert r["derived"]["initiative"] == _dex_mod(r) + 2
    assert r["derived"]["skills"]["skill-acrobatics"] == plain["derived"]["skills"]["skill-acrobatics"] + 2


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_keep_the_half_bonus_on_initiative(catalog, ruleset):
    bard = _res(catalog, "bard", 2, ruleset)
    assert bard["derived"]["initiative"] == _dex_mod(bard) + 1       # Jack of All Trades, PB 2 // 2
    champ = _res(catalog, "fighter", 7, ruleset, "champion")
    assert champ["derived"]["initiative"] == _dex_mod(champ) + 2     # Remarkable Athlete, PB 3 rounded up
    assert champ["derived"]["skills"]["skill-acrobatics"] == _dex_mod(champ) + 2


def test_2024_without_the_features_is_unchanged(catalog):
    r = _res(catalog, "fighter", 7, "2024")
    assert r["derived"]["initiative"] == _dex_mod(r)
