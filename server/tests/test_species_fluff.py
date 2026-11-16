"""DESIGN-J-49: GET /api/catalog/species/<id> carries the species lore (`fluff`) and the trait texts (`traitDetails`)."""
import json

import pytest

import service
from catalog.official.race_fluff import MAX_CHARS, MAX_PARAGRAPHS, _strip_tags, species_fluff


def species(sid):
    status, _, _, body = service.handle("GET", f"/api/catalog/species/{sid}")
    assert status == 200
    return json.loads(body)


def test_elf_xphb_has_short_lore_without_sublineage_blocks_or_tags():
    data = species("elf-xphb")
    assert 1 <= len(data["fluff"]) <= MAX_PARAGRAPHS
    assert data["fluff"][0].startswith("Created by the god Corellon")
    assert all(len(p) <= MAX_CHARS + 1 and "{@" not in p for p in data["fluff"])
    assert not any(p.startswith(("Drow.", "High Elves.", "Wood Elves.")) for p in data["fluff"])


def test_old_phb_species_keep_named_blocks_as_name_dot_text():
    data = species("dwarf-phb")
    assert any(p.startswith("Short and Stout. ") for p in data["fluff"])
    assert not any(p.startswith(("Hill Dwarves.", "Mountain Dwarves.")) for p in data["fluff"])


def test_trait_details_are_plain_text_and_nonempty():
    details = species("elf-xphb")["traitDetails"]
    names = [d["name"] for d in details]
    assert "Darkvision" in names and "Trance" in names
    for d in details:
        assert d["desc"] and all(isinstance(t, str) and "{@" not in t for t in d["desc"])


def test_species_without_fluff_get_an_empty_list():
    assert species("kobold-dmg")["fluff"] == []


def test_srd_species_fall_back_to_phb_text_and_unknown_is_404():
    assert species("dwarf")["fluff"]
    assert service.handle("GET", "/api/catalog/species/nope")[0] == 404


def test_tag_stripping_uses_the_display_text():
    assert _strip_tags("a {@sense Darkvision|XPHB} b {@spell fire bolt|phb|Fire Bolt}") == "a Darkvision b Fire Bolt"
    assert species_fluff("Nonexistent", "PHB") == []
