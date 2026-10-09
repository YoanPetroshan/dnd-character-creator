"""Round-2 audit F3: a selected species/subspecies/background hidden by the
Sources filter still resolves, with a warning (like ruleset-hidden records);
only ids absent from the full catalog are `unknown-*` problems."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, sub, background, sources):
    return {
        "name": "T", "sources": sources,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": background, "choices": {}},
        "species": {"id": species, "subspeciesId": sub, "choices": {}},
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _ids(items):
    return [i["id"] for i in items]


def test_source_hidden_species_and_subspecies_still_resolve_with_warnings(catalog):
    r = resolve(_draft("goblin-psz", "goblin-psz-ixalan-psx", "acolyte", ["srd"]), catalog)
    assert _ids(r["problems"]) == []
    assert r["sheet"]["species"]["id"] == "goblin-psz"
    assert r["sheet"]["species"]["subspecies"]["id"] == "goblin-psz-ixalan-psx"
    assert {"source-hidden-species", "source-hidden-subspecies"} <= set(_ids(r["warnings"]))


def test_source_hidden_background_still_resolves_with_warning(catalog):
    r = resolve(_draft("dwarf", "hill-dwarf", "urchin-phb", ["srd"]), catalog)
    assert _ids(r["problems"]) == []
    assert r["sheet"]["background"]["id"] == "urchin-phb"
    assert "source-hidden-background" in _ids(r["warnings"])


def test_source_hidden_subspecies_under_visible_species(catalog):
    r = resolve(_draft("tiefling-phb", "tiefling-phb-dispater-mtf", "acolyte", ["phb", "xge", "tce"]), catalog)
    assert _ids(r["problems"]) == []
    assert r["sheet"]["species"]["subspecies"]["id"] == "tiefling-phb-dispater-mtf"
    assert "source-hidden-subspecies" in _ids(r["warnings"])


def test_visible_records_produce_no_source_hidden_warning(catalog):
    r = resolve(_draft("dwarf", "hill-dwarf", "acolyte", ["srd"]), catalog)
    assert not [w for w in r["warnings"] if w["id"].startswith("source-hidden")]


def test_nonexistent_ids_are_still_unknown_and_never_cascade_to_mismatch(catalog):
    r = resolve(_draft("no-such-species", "goblin-psz-ixalan-psx", "no-such-bg", ["srd"]), catalog)
    ids = _ids(r["problems"])
    assert "unknown-species" in ids and "unknown-background" in ids
    assert "subspecies-mismatch" not in ids
