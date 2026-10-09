"""Slice 10.1: draft.sources filters subspecies by their OWN book."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, sub, sources):
    return {
        "name": "T", "sources": sources,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": species, "subspeciesId": sub, "choices": {}},
        "abilities": {"method": "standard", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _ids(r):
    return [p["id"] for p in r["problems"]]


def test_subrace_carries_source(catalog):
    assert catalog.subraces["dwarf-phb-hill-phb"]["source"] == "PHB"
    assert catalog.subraces["dwarf-phb-duergar-mtf"]["source"] == "MTF"


def test_other_book_subspecies_filtered(catalog):
    base = resolve(_draft("dwarf-phb", None, ["phb"]), catalog)["sheet"]["abilities"]["STR"]
    r = resolve(_draft("dwarf-phb", "dwarf-phb-duergar-mtf", ["phb"]), catalog)
    assert "unknown-subspecies" in _ids(r)
    assert r["sheet"]["abilities"]["STR"] == base


def test_subspecies_allowed_when_book_enabled(catalog):
    r = resolve(_draft("dwarf-phb", "dwarf-phb-duergar-mtf", ["phb", "mtf"]), catalog)
    assert "unknown-subspecies" not in _ids(r)
    assert r["sheet"]["abilities"]["STR"] == 11


def test_srd_subrace_always_allowed(catalog):
    r = resolve(_draft("dwarf", "hill-dwarf", ["phb"]), catalog)
    assert "unknown-subspecies" not in _ids(r)
