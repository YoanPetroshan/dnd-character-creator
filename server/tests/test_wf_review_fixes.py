"""WF: fixes for the read-only review of W1-W5b."""
from __future__ import annotations

import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, species, sub=None, cls="fighter", level=5, ruleset="mixed", base=None, added=(), background="acolyte",
         species_choices=None, bg_choices=None, class_choices=None, extra=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    sp = {"id": species, "choices": species_choices or {}}
    if sub:
        sp["subspeciesId"] = sub
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": class_choices or {}}],
         "background": {"id": background, "choices": bg_choices or {}}, "species": sp,
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": True},
         "details": {}, "preferences": {}}
    d.update(extra or {})
    return resolve(d, catalog)


# ---------------------------------------------------------------- (1) equal-to-walk species modes

EQUAL_MODES = [
    ("aarakocra-mpmm", None, "fly"), ("dhampir-rhw", None, "climb"), ("dhampir-vrgr", None, "climb"),
    ("fairy-mpmm", None, "fly"), ("fairy-wbtw", None, "fly"), ("giff-aag", None, "swim"),
    ("hadozee-aag", None, "climb"), ("lizardfolk-mpmm", None, "swim"), ("owlin-scc", None, "fly"),
    ("sea-elf-mpmm", None, "swim"), ("tabaxi-mpmm", None, "climb"), ("triton-mpmm", None, "swim"),
    ("genasi-mpmm", "genasi-mpmm-water-mpmm", "swim"),
]


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_follows_heavy_armor_penalty(catalog, species, sub, mode):
    base = _res(catalog, species, sub)["derived"]["speeds"]["walk"]
    s = _res(catalog, species, sub, added=["chain-mail"], base={"STR": 12})["derived"]["speeds"]
    assert s["walk"] == base - 10 and s[mode] == base - 10, s


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_follows_walk_bonus(catalog, species, sub, mode):
    base = _res(catalog, species, sub)["derived"]["speeds"]["walk"]
    s = _res(catalog, species, sub, cls="barbarian", level=5)["derived"]["speeds"]
    assert s["walk"] == base + 10 and s[mode] == base + 10, s


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_plain(catalog, species, sub, mode):
    s = _res(catalog, species, sub)["derived"]["speeds"]
    assert s[mode] == s["walk"]


def test_equal_mode_floor_zero_and_unaffected_numeric(catalog):
    s = _res(catalog, "sea-elf-mpmm", added=["plate-armor"], base={"STR": 8})["derived"]["speeds"]
    assert s["walk"] == 20 and s["swim"] == 20
    # a numeric swim (Triton-like numbers are not "equal to walk") keeps its value
    s2 = _res(catalog, "human", added=["chain-mail"], base={"STR": 12})["derived"]["speeds"]
    assert "swim" not in s2
