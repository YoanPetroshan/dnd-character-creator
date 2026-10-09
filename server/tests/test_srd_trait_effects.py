"""Slice 4: mechanics of SRD racial traits (the bundled SRD JSON only
describes them in prose, so reference_data.SRD_TRAIT_EFFECTS encodes them)."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, classes=None, **overrides):
    draft = {
        "name": "T", "sources": ["srd"],
        "classes": classes or [{"classId": "wizard", "level": 5, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": species,
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    draft.update(overrides)
    return draft


def _run(catalog, race, sub=None, choices=None, **kw):
    sp = {"id": race, "choices": choices or {}}
    if sub:
        sp["subspeciesId"] = sub
    return resolve(_draft(sp, **kw), catalog)


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def test_hill_dwarf_gets_one_hp_per_level(catalog):
    # Wizard 5, CON 10 + 2 (dwarf) = 12 (+1): 7 + 4 * (4 + 1) = 27, plus Dwarven Toughness 5.
    assert _run(catalog, "dwarf", "hill-dwarf")["derived"]["hitPointMax"] == 32
    mountain = _run(catalog, "dwarf", "mountain-dwarf")
    assert mountain["derived"]["hitPointMax"] == 27


def test_hill_dwarf_toughness_is_per_level_not_flat(catalog):
    lvl1 = _run(catalog, "dwarf", "hill-dwarf", classes=[{"classId": "wizard", "level": 1, "choices": {}}])
    base = _run(catalog, "dwarf", "mountain-dwarf", classes=[{"classId": "wizard", "level": 1, "choices": {}}])
    assert lvl1["derived"]["hitPointMax"] - base["derived"]["hitPointMax"] == 1


def test_dwarf_resists_poison_and_tiefling_resists_fire(catalog):
    assert _run(catalog, "dwarf")["sheet"]["damageModifiers"]["resistances"] == ["poison"]
    assert _run(catalog, "tiefling")["sheet"]["damageModifiers"]["resistances"] == ["fire"]
    assert _run(catalog, "human")["sheet"]["damageModifiers"]["resistances"] == []


def test_draconic_ancestry_selects_the_resistance(catalog):
    cid = "species:dragonborn:trait:draconic-ancestry"
    assert _run(catalog, "dragonborn")["sheet"]["damageModifiers"]["resistances"] == []
    r = _run(catalog, "dragonborn", choices={cid: ["draconic-ancestry-black"]})
    assert r["sheet"]["damageModifiers"]["resistances"] == ["acid"]
    r = _run(catalog, "dragonborn", choices={cid: ["draconic-ancestry-gold"]})
    assert r["sheet"]["damageModifiers"]["resistances"] == ["fire"]


def test_tiefling_infernal_legacy_innate_spells(catalog):
    spells = {s["spellId"]: s for s in _run(catalog, "tiefling")["sheet"]["innateSpells"]}
    assert set(spells) == {"thaumaturgy", "hellish-rebuke", "darkness"}
    assert spells["thaumaturgy"]["uses"] == "at-will" and spells["thaumaturgy"]["level"] == 1
    assert spells["hellish-rebuke"]["uses"] == "1/day" and spells["hellish-rebuke"]["level"] == 3
    assert spells["darkness"]["level"] == 5
    assert all(s["ability"] == "CHA" for s in spells.values())


def test_high_elf_cantrip_choice_lands_on_the_sheet(catalog):
    cid = "species:elf:trait:high-elf-cantrip:cantrip"
    r = _run(catalog, "elf", "high-elf")
    ch = _choice(r, cid)
    assert ch["status"] == "pending" and ch["count"] == 1
    assert "light" in {o["id"] for o in ch["options"]}
    r = _run(catalog, "elf", "high-elf", choices={cid: ["mage-hand"]})
    entry = next(s for s in r["sheet"]["innateSpells"] if s["spellId"] == "mage-hand")
    assert entry["ability"] == "INT" and entry["uses"] == "at-will"


def test_high_elf_extra_language_choice(catalog):
    cid = "species:elf:trait:extra-language:languages"
    r = _run(catalog, "elf", "high-elf")
    assert _choice(r, cid)["status"] == "pending"
    assert "dwarvish" not in r["sheet"]["proficiencies"]["languages"]
    r = _run(catalog, "elf", "high-elf", choices={cid: ["dwarvish"]})
    assert "dwarvish" in r["sheet"]["proficiencies"]["languages"]


def test_plain_races_have_no_new_choices_or_effects(catalog):
    r = _run(catalog, "elf")
    assert r["sheet"]["innateSpells"] == []
    assert not [c for c in r["choices"] if c["source"]["kind"] == "species" and c["status"] == "pending"]
