"""W5b (gap audit F2): ``derived.speciesResources`` for the non-2024 species (SRD species, then the book species).

Every ``SPECIES_RESOURCES_2014`` entry quotes the catalog trait text (tags stripped) it models. Breath Weapon-like
traits are resources with ``dc`` / ``dice`` / ``details`` (decision D-2), never attack rows. The module is the W5a
``engine/species_resources.py``; these tests cover the table W5b added.
"""
from __future__ import annotations

import re

import pytest

import export_fields
from catalog import reference_data as ref
from catalog.loader import load
from engine.resolve import resolve

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(node):
    text = " ".join(node) if isinstance(node, list) else str(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\s+", " ", re.sub(r"\{@(\w+) ([^}]*)\}", tag, text))


def _res(catalog, species, level=1, ruleset="2014", picks=None, cls="fighter", base=None, subrace=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    choices = dict(picks or {})
    if subrace:
        choices["species:subspecies"] = [subrace]
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": species, "choices": choices},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}, "preferences": {}}
    return resolve(d, catalog)


def _by_name(res):
    return {r["name"]: r for r in res["derived"]["speciesResources"]}


def _anc(color):
    return {"species:dragonborn:trait:draconic-ancestry": [f"draconic-ancestry-{color}"]}


SRD_IDS = ("breath-weapon", "relentless-endurance", "lucky")


# ---------------------------------------------------------------- SRD data pins

@pytest.mark.parametrize("tid", SRD_IDS)
def test_srd_entry_quotes_match_catalog_trait_text(catalog, tid):
    spec = ref.SPECIES_RESOURCES_2014[tid]
    trait = catalog.traits[tid]
    assert trait["name"] == spec["name"]
    text = _plain(trait["desc"])
    assert spec["quotes"], tid
    for quote in spec["quotes"]:
        assert quote in text, (tid, quote)
    race = catalog.races[spec["race"]]
    assert race["ruleset"] == "2014" and "source" not in race  # an SRD record
    assert tid in [t["index"] for t in race["traits"]]


def test_srd_breath_weapon_structured_data_agrees_with_the_pinned_text(catalog):
    """The picked ancestry's structured breath weapon (area, save, damage) must agree with the dice progression and the
    once-per-rest rule pinned from the text."""
    spec = ref.SPECIES_RESOURCES_2014["breath-weapon"]
    progression = {str(lvl): dice for lvl, dice in spec["dice_by_level"]}
    colors = [k for k in catalog.traits if k.startswith("draconic-ancestry-")]
    assert len(colors) == 10
    for k in colors:
        bw = catalog.traits[k]["trait_specific"]["breath_weapon"]
        assert bw["damage"][0]["damage_at_character_level"] == progression, k
        assert bw["usage"] == {"type": "per rest", "times": spec["uses"]}, k
        assert bw["dc"]["dc_type"]["index"] in ("dex", "con") and bw["dc"]["success_type"] == "half", k


def test_scan_every_srd_species_trait_with_a_use_or_rest_rule_is_modelled_or_listed_skipped(catalog):
    skipped = {  # trait id -> why
        "infernal-legacy": "Tiefling: innate spells (hellish rebuke, darkness) are modelled as innate spells",
        "trance": "Elf: 4-hour rest, no uses",
        "tinker": "Rock Gnome: constructs a device, no use count or rest rule",
    }
    pat = re.compile(r"long rest|short rest|short or long rest|expended|times equal|can't (?:do so|use it) again|"
                     r"cannot use|per day|once per", re.I)
    srd_races = [r for r in catalog.races.values() if r.get("ruleset") == "2014" and "source" not in r]
    assert {r["index"] for r in srd_races} >= {"dragonborn", "half-orc", "halfling", "tiefling", "elf", "dwarf"}
    seen = 0
    for race in srd_races:
        refs = [t["index"] for t in race.get("traits") or []]
        for sub in catalog.subraces.values():
            if (sub.get("race") or {}).get("index") == race["index"]:
                refs += [t["index"] for t in sub.get("racial_traits") or []]
        for tid in refs:
            t = catalog.traits.get(tid)
            if t and pat.search(_plain(t["desc"])):
                seen += 1
                assert tid in ref.SPECIES_RESOURCES_2014 or tid in skipped, (tid, t["name"])
    assert seen >= 3


# ---------------------------------------------------------------- SRD behaviour

COLORS = {  # color -> (damage type, save, area), pinned from the SRD Draconic Ancestry table
    "black": ("acid", "DEX", "30-foot line"), "blue": ("lightning", "DEX", "30-foot line"),
    "brass": ("fire", "DEX", "30-foot line"), "bronze": ("lightning", "DEX", "30-foot line"),
    "copper": ("acid", "DEX", "30-foot line"), "gold": ("fire", "DEX", "15-foot cone"),
    "green": ("poison", "CON", "15-foot cone"), "red": ("fire", "DEX", "15-foot cone"),
    "silver": ("cold", "CON", "15-foot cone"), "white": ("cold", "CON", "15-foot cone"),
}


@pytest.mark.parametrize("color", sorted(COLORS))
def test_srd_dragonborn_breath_weapon_follows_the_picked_ancestry(catalog, color):
    dmg, save, area = COLORS[color]
    res = _res(catalog, "dragonborn", 6, picks=_anc(color), base={"CON": 16})
    bw = _by_name(res)["Breath Weapon"]
    pb = res["derived"]["proficiencyBonus"]
    assert bw["details"]["damageType"] == dmg and bw["details"]["save"] == save
    assert bw["details"]["shape"] == f"a {area}"
    assert bw["dc"] == 8 + 3 + pb and bw["dice"] == "3d6"
    assert bw["uses"] == 1 and bw["recharge"] == "short-or-long"
    assert dmg.capitalize() in bw["details"]["note"] and "3d6" in bw["details"]["note"]
    assert bw["traitId"] == "breath-weapon" and bw["speciesId"] == "dragonborn"
    assert bw["source"] == {"kind": "species", "id": "dragonborn", "label": "Dragonborn"}
    assert not any("Breath" in a.get("name", "") for a in res["derived"]["attacks"])  # D-2: not an attack row


@pytest.mark.parametrize("level,dice", [(1, "2d6"), (5, "2d6"), (6, "3d6"), (10, "3d6"), (11, "4d6"), (15, "4d6"),
                                        (16, "5d6"), (20, "5d6")])
def test_srd_dragonborn_breath_weapon_dice_by_level(catalog, level, dice):
    bw = _by_name(_res(catalog, "dragonborn", level, picks=_anc("red")))["Breath Weapon"]
    assert bw["dice"] == dice


def test_srd_dragonborn_without_a_pick_says_to_choose_the_ancestry(catalog):
    bw = _by_name(_res(catalog, "dragonborn", 1))["Breath Weapon"]
    assert bw["details"]["damageType"] is None and "shape" not in bw["details"] and "save" not in bw["details"]
    assert "Draconic Ancestry" in bw["details"]["note"] and "choose the ancestry" in bw["details"]["note"]
    assert bw["dc"] == 8 + 0 + 2 and bw["dice"] == "2d6"


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_srd_resources_appear_under_2014_and_mixed(catalog, ruleset):
    assert "Breath Weapon" in _by_name(_res(catalog, "dragonborn", 1, ruleset=ruleset))
    assert "Relentless Endurance" in _by_name(_res(catalog, "half-orc", 1, ruleset=ruleset))


def test_half_orc_relentless_endurance_and_halfling_lucky(catalog):
    rel = _by_name(_res(catalog, "half-orc", 1))["Relentless Endurance"]
    assert rel["uses"] == 1 and rel["recharge"] == "long" and "1 Hit Point" in rel["details"]["note"]
    lucky = _by_name(_res(catalog, "halfling", 1))["Lucky"]
    assert lucky["uses"] is None and lucky["recharge"] is None and "reroll" in lucky["details"]["note"]


def test_species_without_table_traits_have_an_empty_list_under_2014(catalog):
    for sp in ("human", "elf", "dwarf", "tiefling", "gnome"):
        assert _res(catalog, sp, 5)["derived"]["speciesResources"] == [], sp


def test_wiring_removed_gives_no_resources(catalog, monkeypatch):
    monkeypatch.setattr(ref, "SPECIES_RESOURCES_2014", {})
    assert _res(catalog, "dragonborn", 5, picks=_anc("red"))["derived"]["speciesResources"] == []


def test_degrades_when_the_picked_ancestry_trait_is_missing_from_the_catalog(catalog, monkeypatch):
    patched = dict(catalog.traits)
    patched.pop("draconic-ancestry-red")
    monkeypatch.setattr(catalog, "traits", patched)
    bw = _by_name(_res(catalog, "dragonborn", 6, picks=_anc("red")))["Breath Weapon"]
    assert bw["details"]["damageType"] is None and bw["dice"] == "3d6"


def test_degrades_when_the_trait_is_missing_from_the_catalog(catalog, monkeypatch):
    patched = dict(catalog.traits)
    patched.pop("relentless-endurance")
    monkeypatch.setattr(catalog, "traits", patched)
    assert "Relentless Endurance" not in _by_name(_res(catalog, "half-orc", 1))


def test_extra_blocks_list_the_srd_resources(catalog):
    blocks = export_fields.extra_blocks(_res(catalog, "dragonborn", 6, picks=_anc("green")))
    idx = blocks.index(("h2", "Ресурси от расата"))
    lines = [t for kind, t in blocks[idx + 1:] if kind == "bullet"]
    assert any("Breath Weapon" in l and "3d6" in l and "ТС" in l for l in lines)
