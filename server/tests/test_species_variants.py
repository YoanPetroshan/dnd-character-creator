"""Slice 8b: species whose 5etools record lists mutually exclusive `_versions`
(2024 lineages, ancestries, legacies) get a required variant choice.

Verified against the fetched races.json: 14 non-`_copy` races carry
`_versions` - 10 explicit (Aasimar/MPMM, Aetherborn/PSK, Custom Lineage/TCE,
Elf/XPHB, Gnome/XPHB, Goliath/XPHB, Kobold/MPMM, Shifter/EFA, Shifter/MPMM,
Tiefling/XPHB) and 4 abstract (Dragonborn/XPHB with 10 colours, Dragonborn
Chromatic/Gem/Metallic FTD with 5 each). Aetherborn's single version only
appends a trait (no alternative to choose between), so 13 races get a
variant choice. The plan's "17" included three `_copy` Lorwyn races, which
the converter skips."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

SOURCES = ["srd", "phb", "mpmm", "tce", "scag", "erlw", "mtf", "xphb", "ftd", "egw", "vgm", "psk", "efa"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _run(catalog, species_id, choices=None):
    draft = {
        "name": "T", "sources": SOURCES,
        "classes": [{"classId": "wizard", "level": 5, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": species_id, "choices": choices or {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    return resolve(draft, catalog)


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _spell_names(res):
    return sorted(s["name"] for s in res["sheet"]["innateSpells"])


# --- catalog ---------------------------------------------------------------

def test_elf_xphb_variants(catalog):
    variants = catalog.races["elf-xphb"]["variants"]
    assert [v["id"] for v in variants] == ["drow-lineage", "high-elf-lineage", "wood-elf-lineage"]
    wood = variants[2]
    assert wood["speed"] == 35 and variants[0]["speed"] is None
    assert variants[0]["darkvision"] == 120
    assert sorted(s["name"] for s in variants[0]["innate_spells"]) == ["Dancing Lights", "Darkness", "Faerie Fire"]  # G6: + the `known` cantrip


def test_tiefling_xphb_variants_carry_resistance_and_spells(catalog):
    by_id = {v["id"]: v for v in catalog.races["tiefling-xphb"]["variants"]}
    assert set(by_id) == {"abyssal-legacy", "chthonic-legacy", "infernal-legacy"}
    assert by_id["infernal-legacy"]["resist"] == ["fire"]
    assert by_id["abyssal-legacy"]["resist"] == ["poison"] and by_id["chthonic-legacy"]["resist"] == ["necrotic"]


def test_dragonborn_variants_come_from_the_abstract_version(catalog):
    xphb = catalog.races["dragonborn-xphb"]["variants"]
    assert len(xphb) == 10
    black = next(v for v in xphb if v["id"] == "dragonborn-black")
    assert black["name"] == "Dragonborn (Black)" and black["resist"] == ["acid"]
    chromatic = catalog.races["dragonborn-(chromatic)-ftd"]["variants"]  # resist lives in _variables here
    assert len(chromatic) == 5 and {v["resist"][0] for v in chromatic} == {"acid", "lightning", "poison", "fire", "cold"}
    assert len(catalog.races["dragonborn-(gem)-ftd"]["variants"]) == 5
    assert len(catalog.races["dragonborn-(metallic)-ftd"]["variants"]) == 5


def test_goliath_variants_carry_no_data_keys(catalog):
    variants = catalog.races["goliath-xphb"]["variants"]
    assert len(variants) == 6
    assert all(not v["resist"] and not v["innate_spells"] and v["speed"] is None and v["darkvision"] is None for v in variants)


def test_thirteen_races_have_variants(catalog):
    with_variants = sorted(r["index"] for r in catalog.races.values() if r.get("variants"))
    assert len(with_variants) == 13
    assert "aetherborn-psk" not in with_variants  # appendArr only: nothing to choose between
    assert catalog.races["aetherborn-psk"]["variants"] == []
    assert catalog.races["dwarf"].get("variants", []) == []


# --- engine ---------------------------------------------------------------

def test_unpicked_lineage_is_pending_and_grants_no_lineage_spells(catalog):
    res = _run(catalog, "elf-xphb")
    ch = _choice(res, "species:elf-xphb:variant")
    assert ch["status"] == "pending" and ch["count"] == 1 and ch["source"]["kind"] == "species"
    assert [o["id"] for o in ch["options"]] == ["drow-lineage", "high-elf-lineage", "wood-elf-lineage"]
    assert _spell_names(res) == []
    assert res["derived"]["speed"] == 30
    assert res["sheet"]["species"]["variant"] is None


def test_drow_lineage_grants_only_its_spells_and_darkvision(catalog):
    res = _run(catalog, "elf-xphb", {"species:elf-xphb:variant": ["drow-lineage"]})
    assert _spell_names(res) == ["Dancing Lights", "Darkness", "Faerie Fire"]  # G6: Dancing Lights is the lineage's `known` cantrip
    assert res["sheet"]["species"]["variant"] == {"id": "drow-lineage", "name": "Drow Lineage"}
    assert res["sheet"]["senses"]["darkvision"] == 120
    assert _choice(res, "species:elf-xphb:variant")["status"] == "resolved"


def test_wood_elf_lineage_raises_speed(catalog):
    res = _run(catalog, "elf-xphb", {"species:elf-xphb:variant": ["wood-elf-lineage"]})
    assert res["derived"]["speed"] == 35 and res["derived"]["speeds"] == {"walk": 35}
    assert _spell_names(res) == ["Druidcraft", "Longstrider", "Pass Without Trace"]  # G6: Druidcraft is the lineage's `known` cantrip
    assert res["sheet"]["senses"]["darkvision"] == 60


def test_tiefling_legacy_replaces_the_resistance_choice(catalog):
    res = _run(catalog, "tiefling-xphb", {"species:tiefling-xphb:variant": ["infernal-legacy"]})
    assert _choice(res, "species:tiefling-xphb:resistance") is None  # the legacy decides it
    assert res["sheet"]["damageModifiers"]["resistances"] == ["fire"]
    assert _spell_names(res) == ["Darkness", "Fire Bolt", "Hellish Rebuke", "Thaumaturgy"]  # G6: + the legacy's `known` cantrips


def test_dragonborn_colour_sets_the_resistance(catalog):
    res = _run(catalog, "dragonborn-xphb", {"species:dragonborn-xphb:variant": ["dragonborn-red"]})
    assert res["sheet"]["damageModifiers"]["resistances"] == ["fire"]
    assert _choice(res, "species:dragonborn-xphb:resistance") is None
    ftd = _run(catalog, "dragonborn-(gem)-ftd", {"species:dragonborn-(gem)-ftd:variant": ["dragonborn-gem-emerald"]})
    assert ftd["sheet"]["damageModifiers"]["resistances"] == ["psychic"]


def test_races_with_only_a_resistance_choice_keep_it(catalog):
    res = _run(catalog, "dragonborn-phb")
    assert _choice(res, "species:dragonborn-phb:resistance") is not None
    assert _choice(res, "species:dragonborn-phb:variant") is None


def test_srd_race_has_no_variant_choice(catalog):
    res = _run(catalog, "elf")
    assert _choice(res, "species:elf:variant") is None
    assert res["sheet"]["species"]["variant"] is None


def test_unknown_variant_id_is_ignored(catalog):
    res = _run(catalog, "elf-xphb", {"species:elf-xphb:variant": ["moon-lineage"]})
    assert res["sheet"]["species"]["variant"] is None
    assert _choice(res, "species:elf-xphb:variant")["status"] == "pending"
    assert _spell_names(res) == []


def test_changing_the_species_drops_nothing_for_unrelated_races(catalog):
    res = _run(catalog, "gnome-xphb", {"species:gnome-xphb:variant": ["rock-gnome-lineage"]})
    assert res["sheet"]["species"]["variant"]["name"] == "Rock Gnome Lineage"
    assert res["problems"] == []


def test_exports_name_the_lineage(catalog):
    from markdown_export import _species_label as md_label
    from pdf_export import _species_label as pdf_label
    res = _run(catalog, "elf-xphb", {"species:elf-xphb:variant": ["drow-lineage"]})
    assert md_label(res["sheet"]["species"]) == "Elf - Drow Lineage"
    assert pdf_label(res["sheet"]["species"]) == "Elf - Drow Lineage"
    assert md_label(_run(catalog, "elf-xphb")["sheet"]["species"]) == "Elf"


# --- 8e: a version that nulls a data key removes that part of the base race -----------

def _skill_choice(res):
    return next((c for c in res["choices"] if c["source"]["kind"] == "species" and "trait-choice-skill-proficiency" in c["id"]), None)


def test_custom_lineage_variants_split_darkvision_from_the_skill(catalog):
    ids = [v["id"] for v in catalog.races["custom-lineage-tce"]["variants"]]
    assert ids == ["darkvision", "skill-proficiency"]
    unpicked = _run(catalog, "custom-lineage-tce")
    assert _skill_choice(unpicked) is not None and unpicked["sheet"]["senses"].get("darkvision") == 60

    dark = _run(catalog, "custom-lineage-tce", {"species:custom-lineage-tce:variant": ["darkvision"]})
    assert _skill_choice(dark) is None
    assert dark["sheet"]["senses"]["darkvision"] == 60

    skill = _run(catalog, "custom-lineage-tce", {"species:custom-lineage-tce:variant": ["skill-proficiency"]})
    assert _skill_choice(skill) is not None
    assert "darkvision" not in skill["sheet"]["senses"]


def test_kobold_legacies_remove_the_skill_choice_where_the_data_says_so(catalog):
    base = "species:kobold-mpmm:variant"
    assert [v["id"] for v in catalog.races["kobold-mpmm"]["variants"]] == ["craftiness", "defiance", "draconic-sorcery"]
    assert _skill_choice(_run(catalog, "kobold-mpmm", {base: ["craftiness"]})) is not None
    assert _skill_choice(_run(catalog, "kobold-mpmm", {base: ["defiance"]})) is None
    assert _skill_choice(_run(catalog, "kobold-mpmm", {base: ["draconic-sorcery"]})) is None
    assert _run(catalog, "kobold-mpmm", {base: ["defiance"]})["sheet"]["senses"]["darkvision"] == 60


def test_a_removed_skill_choice_selection_is_pruned(catalog):
    first = _run(catalog, "kobold-mpmm", {"species:kobold-mpmm:variant": ["craftiness"]})
    cid = _skill_choice(first)["id"]
    sel = {"species:kobold-mpmm:variant": ["defiance"], cid: ["skill-arcana"]}
    res = _run(catalog, "kobold-mpmm", sel)
    assert cid in [p["choiceId"] for p in res["pruned"]]
    assert "skill-arcana" not in res["sheet"]["proficiencies"]["skills"]
