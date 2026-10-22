"""RP1 (X1): under ruleset 2024 a background's ability score increase cannot raise a score above 20.
Governing text (PHB 2024, background step of character creation, and the Ability Scores chapter):
"None of these increases can raise a score above 20."

Rule matrix (ruleset x number x source):
  2024, +2 / +1 / +1 each, bundle         the background step is clamped per ability to max(0, 20 - base)
  2024, 20 + 2                              stays 20, non-blocking `pruned` entry (choiceId = the background card)
  2024, 19 + 2                              20, the 1 point lost is reported the same way
  2024, 18 + 2                              20, nothing lost, no entry
  2024, +1/+1/+1 with one score at 20       the other two apply, one entry
  2024, a background from a later book      same code path (carouser-abh), same clamp
  mixed / 2014                              unchanged (the 2014 rules have no such sentence): 20 + 2 stays 22
  order                                     the clamp is on the background step only; later ASIs and origin feats
                                            keep their own caps (FE2), they read the clamped score
  problems                                  unchanged (empty); the entry is `pruned`, never a problem"""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
SOLDIER = "background:soldier-xphb:ability-bonus"
CAROUSER = "background:carouser-abh:ability-bonus"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(base, pick, ruleset="2024", bg="soldier-xphb", cid=SOLDIER):
    scores = {a: 10 for a in ABS}
    scores.update(base)
    return {"name": "T", "sources": [], "ruleset": ruleset,
            "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
            "background": {"id": bg, "choices": {cid: [pick]}},
            "species": {"id": "human-xphb", "choices": {}},
            "abilities": {"method": "manual", "base": scores}}


def _bg_pruned(r, cid=SOLDIER):
    return [p for p in r["pruned"] if p["choiceId"] == cid and "maximum" in p["reason"]]


def test_20_plus_2_stays_20_with_a_pruned_entry(catalog):
    r = resolve(_draft({"STR": 20}, "str-2+dex-1"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["DEX"]) == (20, 11)
    notes = _bg_pruned(r)
    assert len(notes) == 1
    assert notes[0]["reason"] == "Soldier: STR is already at maximum (20) and the increase was ignored."
    assert r["problems"] == []


def test_19_plus_2_gives_20_and_reports_the_lost_point(catalog):
    r = resolve(_draft({"STR": 19}, "str-2+dex-1"), catalog)
    assert r["sheet"]["abilities"]["STR"] == 20
    assert len(_bg_pruned(r)) == 1


def test_18_plus_2_loses_nothing(catalog):
    r = resolve(_draft({"STR": 18}, "str-2+dex-1"), catalog)
    assert r["sheet"]["abilities"]["STR"] == 20
    assert _bg_pruned(r) == []


def test_plus_one_each_with_one_score_at_20(catalog):
    r = resolve(_draft({"STR": 20}, "str-1+dex-1+con-1"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["DEX"], a["CON"]) == (20, 11, 11)
    assert len(_bg_pruned(r)) == 1
    assert "STR" in _bg_pruned(r)[0]["reason"]


def test_two_scores_over_the_cap_give_two_entries(catalog):
    r = resolve(_draft({"STR": 20, "DEX": 20}, "str-2+dex-1"), catalog)
    a = r["sheet"]["abilities"]
    assert (a["STR"], a["DEX"]) == (20, 20)
    assert len(_bg_pruned(r)) == 2


def test_background_from_a_later_book_is_clamped_too(catalog):
    r = resolve(_draft({"DEX": 20}, "dex-2+int-1", bg="carouser-abh", cid=CAROUSER), catalog)
    a = r["sheet"]["abilities"]
    assert (a["DEX"], a["INT"]) == (20, 11)
    assert len(_bg_pruned(r, CAROUSER)) == 1


def test_mixed_and_2014_are_unchanged(catalog):
    r = resolve(_draft({"STR": 20}, "str-2+dex-1", ruleset="mixed"), catalog)
    assert r["sheet"]["abilities"]["STR"] == 22
    assert _bg_pruned(r) == []
    # 2014 ignores the 2024 background increase altogether (base stays)
    r = resolve(_draft({"STR": 20}, "str-2+dex-1", ruleset="2014"), catalog)
    assert r["sheet"]["abilities"]["STR"] == 20
    assert _bg_pruned(r) == []


def test_later_asi_reads_the_clamped_score(catalog):
    d = _draft({"STR": 19}, "str-2+dex-1")
    d["classes"] = [{"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": ["str-plus-2"]}}]
    r = resolve(d, catalog)
    assert r["sheet"]["abilities"]["STR"] == 20  # background clamped to 20, the ASI still stops at 20
    assert r["problems"] == []
