"""Slice 8d: species whose 5etools `size` lists more than one value
(["S", "M"]) let the player pick the size.

Verified against races.json: of the 144 non-`_copy` races 95 are ["M"], 30 are
["S","M"], 18 are ["S"] and one is ["V"] (varies; the converter keeps its
Medium fallback). No subrace has a `size`."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

SOURCES = ["srd", "phb", "mpmm", "tce", "scag", "erlw", "mtf", "xphb", "ftd", "egw", "vgm", "psk"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _run(catalog, species_id, choices=None, sources=None, base=None):
    draft = {
        "name": "T", "sources": SOURCES if sources is None else sources,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": species_id, "choices": choices or {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **(base or {})}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    return resolve(draft, catalog)


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


official = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@official
def test_thirty_races_offer_a_size_choice(catalog):
    multi = [r["index"] for r in catalog.races.values() if r.get("size_options")]
    assert len(multi) == 30
    assert catalog.races["human-xphb"]["size_options"] == ["Small", "Medium"]
    assert catalog.races["human-xphb"]["size"] == "Small"  # first value stays the plain size
    assert catalog.races["elf-xphb"].get("size_options") == []


@official
def test_human_xphb_offers_small_and_medium(catalog):
    res = _run(catalog, "human-xphb")
    ch = _choice(res, "species:human-xphb:size")
    assert [o["id"] for o in ch["options"]] == ["small", "medium"] and ch["status"] == "pending"
    assert res["sheet"]["species"]["size"] is None  # unpicked


@official
def test_selecting_small_sets_the_sheet_size(catalog):
    res = _run(catalog, "human-xphb", {"species:human-xphb:size": ["small"]})
    assert res["sheet"]["species"]["size"] == "Small"
    assert _choice(res, "species:human-xphb:size")["status"] == "resolved"
    res = _run(catalog, "human-xphb", {"species:human-xphb:size": ["medium"]})
    assert res["sheet"]["species"]["size"] == "Medium"


@official
def test_invalid_size_is_ignored(catalog):
    res = _run(catalog, "human-xphb", {"species:human-xphb:size": ["large"]})
    assert res["sheet"]["species"]["size"] is None


def test_srd_dwarf_is_medium_without_a_choice(catalog):
    res = _run(catalog, "dwarf", sources=["srd"])
    assert res["sheet"]["species"]["size"] == "Medium"
    assert _choice(res, "species:dwarf:size") is None
    assert _run(catalog, "halfling", sources=["srd"])["sheet"]["species"]["size"] == "Small"


def test_carrying_capacity_reads_the_selected_size(catalog, monkeypatch):
    # No real race offers Tiny or Large, so give one to prove the wiring.
    fake = {**catalog.races["dwarf"], "index": "dwarf", "size": "Medium", "size_options": ["Tiny", "Large"]}
    monkeypatch.setitem(catalog.races, "dwarf", fake)
    none = _run(catalog, "dwarf", sources=["srd"], base={"STR": 13})  # dwarf +2 CON only: STR 13
    assert none["derived"]["carryingCapacity"]["capacity"] == 195  # unpicked: the race's own size, x1
    large = _run(catalog, "dwarf", {"species:dwarf:size": ["large"]}, sources=["srd"], base={"STR": 13})
    assert large["sheet"]["species"]["size"] == "Large"
    assert large["derived"]["carryingCapacity"]["capacity"] == 390
    tiny = _run(catalog, "dwarf", {"species:dwarf:size": ["tiny"]}, sources=["srd"], base={"STR": 13})
    assert tiny["derived"]["carryingCapacity"]["capacity"] == 97.5
