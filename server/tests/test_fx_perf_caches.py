"""FX1: the cached source set and visible-spell set give the same answers as the uncached checks."""
import pytest

from catalog.official_source import has_official
from catalog.loader import load
from engine import resolve as R

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.mark.parametrize("sources", [[], ["PHB"], ["XPHB", "srd"], ["phb", 3, None]])
@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_visible_spell_ids_match_per_spell_check(catalog, sources, ruleset):
    expected = {i for i, sp in catalog.spells.items() if R._spell_visible(catalog, sp, sources, ruleset)}
    assert R._visible_spell_ids(catalog, sources, ruleset) == expected
    flt = {"level": [0, 1]}
    got = [o["item"]["index"] for o in R._spell_filter_options(catalog, flt, sources, ruleset)]
    assert set(got) <= expected and all(catalog.spells[i]["level"] in (0, 1) for i in got)


def test_keep_still_offers_hidden_spell(catalog):
    hidden = next(i for i, sp in catalog.spells.items() if not R._spell_visible(catalog, sp, ["PHB"], "2014")
                  and sp["level"] == 1)
    got = [o["item"]["index"] for o in R._spell_filter_options(catalog, {"level": [1]}, ["PHB"], "2014", {hidden})]
    assert hidden in got


def test_unhashable_sources_do_not_crash(catalog):
    assert R._source_allowed({"source": "PHB"}, [["x"], "phb"]) is True
    assert R._source_allowed({"source": "XPHB"}, [["x"], "phb"]) is False
