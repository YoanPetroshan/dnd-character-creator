"""W5a (gap audit F2): ``derived.speciesResources`` from the pinned ``SPECIES_RESOURCES`` table.

Every table entry quotes the catalog trait text (tags stripped) it models; the Giant Ancestry boon list is dropped by the
catalog trait, so those quotes are pinned against the raw 5etools race entry. Breath Weapon-like traits are resources with
``dc`` / ``dice`` / ``details`` (decision D-2), never attack rows.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import export_fields
from catalog import reference_data as ref
from catalog.loader import load
from catalog.official_source import has_official, official_dir
from engine import species_resources
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

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


def _res(catalog, species, level=1, ruleset="2024", variant=None, cls="fighter", base=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    choices = {f"species:{species}:variant": [variant]} if variant else {}
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": "soldier-xphb", "choices": {}}, "species": {"id": species, "choices": choices},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}, "preferences": {}}
    return resolve(d, catalog)


def _by_name(res):
    return {r["name"]: r for r in res["derived"]["speciesResources"]}


# ---------------------------------------------------------------- data pins

@pytest.mark.parametrize("tid", list(ref.SPECIES_RESOURCES))
def test_table_entry_quotes_match_catalog_trait_text(catalog, tid):
    spec = ref.SPECIES_RESOURCES[tid]
    trait = catalog.traits[tid]
    assert trait["name"] == spec["name"]
    text = _plain(trait["desc"])
    assert spec["quotes"], tid
    for quote in spec["quotes"]:
        assert quote in text, (tid, quote)
    race = catalog.races[spec["race"]]
    assert race["ruleset"] == "2024"  # only ruleset-2024 species records change
    assert tid in [t["index"] for t in race["traits"]]


def test_giant_ancestry_boons_pinned_against_raw_race_entry(catalog):
    raw = json.loads((Path(official_dir()) / "races.json").read_text())["race"]
    goliath = next(r for r in raw if r["name"] == "Goliath" and r["source"] == "XPHB")
    text = _plain([json.dumps(goliath["entries"], ensure_ascii=False)])
    variants = {v["id"] for v in catalog.races["goliath-xphb"]["variants"]}
    assert set(ref.GIANT_ANCESTRY_2024) == variants
    for vid, boon in ref.GIANT_ANCESTRY_2024.items():
        assert boon["quote"] in text, vid
        assert boon["name"] in text, vid


def test_scan_every_2024_species_trait_with_a_rest_or_use_rule_is_modelled_or_listed_skipped(catalog):
    """Scan of catalog.traits for the 2024 species: nothing with a use count / rest rule is silently missed."""
    skipped = {  # trait id -> why (no use count; a rest only changes what the trait lets you swap or do)
        "elf-xphb-trait-1": "Elven Lineage: innate spells already modelled", "tiefling-xphb-trait-1": "Fiendish Legacy: innate spells already modelled",
        "elf-xphb-trait-4": "Trance: 4-hour rest, no uses", "reborn-rhw-trait-1": "Everlasting: 4-hour rest, no uses",
        "warforged-efa-trait-2": "Sentry's Rest: 6-hour rest, no uses",
        "kalashtar-efa-trait-3": "Severed from Dreams: skill swap per Long Rest, no uses",
        "khoravar-efa-trait-2": "Fey Gift: cantrip swap per Long Rest, no uses",
        "khoravar-efa-trait-4": "Skill Versatility: proficiency swap per Long Rest, no uses",
    }
    pat = re.compile(r"Long Rest|Short Rest|expended|times equal|can't (?:do so|use it) again", re.I)
    for race in catalog.races.values():
        if race.get("ruleset") != "2024":
            continue
        for r in race.get("traits") or []:
            tid = r["index"]
            t = catalog.traits.get(tid)
            if t and pat.search(_plain(t["desc"])):
                assert tid in ref.SPECIES_RESOURCES or tid in skipped, (tid, t["name"])


# ---------------------------------------------------------------- behaviour

@pytest.mark.parametrize("level,dice", [(1, "1d10"), (4, "1d10"), (5, "2d10"), (10, "2d10"), (11, "3d10"), (16, "3d10"), (17, "4d10"), (20, "4d10")])
def test_dragonborn_breath_weapon_dice_dc_and_uses(catalog, level, dice):
    res = _res(catalog, "dragonborn-xphb", level, variant="dragonborn-blue", base={"CON": 16})
    bw = _by_name(res)["Breath Weapon"]
    pb = res["derived"]["proficiencyBonus"]
    con = res["derived"]["abilityModifiers"]["CON"]
    assert bw["dice"] == dice and bw["dc"] == 8 + con + pb and bw["uses"] == pb and bw["recharge"] == "long"
    assert bw["details"]["damageType"] == "lightning" and bw["details"]["save"] == "DEX"
    assert dice in bw["details"]["note"] and "Lightning" in bw["details"]["note"]
    assert bw["traitId"] == "dragonborn-xphb-trait-1" and bw["speciesId"] == "dragonborn-xphb"
    assert bw["source"] == {"kind": "species", "id": "dragonborn-xphb", "label": "Dragonborn"}
    assert not any("Breath" in a.get("name", "") for a in res["derived"]["attacks"])  # D-2: not an attack row


def test_dragonborn_without_ancestry_pick_says_to_choose(catalog):
    bw = _by_name(_res(catalog, "dragonborn-xphb", 1))["Breath Weapon"]
    assert bw["details"]["damageType"] is None and "choose the ancestry" in bw["details"]["note"]


def test_level_gated_traits_appear_at_their_level(catalog):
    for sp, name, lvl in [("dragonborn-xphb", "Draconic Flight", 5), ("goliath-xphb", "Large Form", 5),
                          ("aasimar-xphb", "Celestial Revelation", 3)]:
        assert name not in _by_name(_res(catalog, sp, lvl - 1)), name
        r = _by_name(_res(catalog, sp, lvl))[name]
        assert r["uses"] == 1 and r["recharge"] == "long", name


def test_draconic_flight_note_carries_the_walk_speed(catalog):
    note = _by_name(_res(catalog, "dragonborn-xphb", 5))["Draconic Flight"]["details"]["note"]
    assert "(30 feet)" in note


@pytest.mark.parametrize("level,pb", [(1, 2), (5, 3), (9, 4), (13, 5), (17, 6)])
def test_pb_scaled_uses(catalog, level, pb):
    assert _by_name(_res(catalog, "orc-xphb", level))["Adrenaline Rush"]["uses"] == pb
    assert _by_name(_res(catalog, "dwarf-xphb", level))["Stonecunning"]["uses"] == pb
    assert _by_name(_res(catalog, "goliath-xphb", level))["Giant Ancestry"]["uses"] == pb


def test_orc_adrenaline_rush_and_relentless_endurance(catalog):
    res = _by_name(_res(catalog, "orc-xphb", 5))
    rush, rel = res["Adrenaline Rush"], res["Relentless Endurance"]
    assert rush["recharge"] == "short-or-long" and "3 Temporary Hit Points" in rush["details"]["note"]
    assert rel["uses"] == 1 and rel["recharge"] == "long"


def test_aasimar_healing_hands_is_pb_d4s_once_per_long_rest(catalog):
    for level, pb in [(1, 2), (9, 4)]:
        hh = _by_name(_res(catalog, "aasimar-xphb", level))["Healing Hands"]
        assert hh["uses"] == 1 and hh["recharge"] == "long" and hh["details"]["heal"] == f"{pb}d4"


@pytest.mark.parametrize("vid", list(ref.GIANT_ANCESTRY_2024))
def test_goliath_giant_ancestry_note_names_the_picked_boon(catalog, vid):
    boon = ref.GIANT_ANCESTRY_2024[vid]
    note = _by_name(_res(catalog, "goliath-xphb", 1, variant=vid, base={"CON": 14}))["Giant Ancestry"]["details"]["note"]
    assert note.startswith(boon["name"])
    if vid == "stone-giant-ancestry":
        assert "+2" in note


def test_goliath_without_pick_says_to_choose(catalog):
    assert "choose a Giant Ancestry" in _by_name(_res(catalog, "goliath-xphb", 1))["Giant Ancestry"]["details"]["note"]


def test_human_and_halfling_notes(catalog):
    hum = _by_name(_res(catalog, "human-xphb", 1))["Resourceful"]
    assert hum["uses"] is None and hum["recharge"] == "long" and "Heroic Inspiration" in hum["details"]["note"]
    hl = _by_name(_res(catalog, "halfling-xphb", 1))["Luck"]
    assert hl["uses"] is None and "reroll" in hl["details"]["note"]


def test_species_without_table_traits_and_older_rulesets_have_empty_list(catalog):
    assert _res(catalog, "elf-xphb", 5)["derived"]["speciesResources"] == []
    assert _res(catalog, "human", 5, ruleset="2014")["derived"]["speciesResources"] == []
    assert _res(catalog, "elf", 5, ruleset="2014")["derived"]["speciesResources"] == []  # W5b models the 2014 Dragonborn


def test_entries_use_the_resource_shape_minus_class_id(catalog):
    for r in _res(catalog, "dragonborn-xphb", 11, variant="dragonborn-red")["derived"]["speciesResources"]:
        assert "classId" not in r and r["id"].startswith("species:dragonborn-xphb:")
        assert {"id", "name", "uses", "recharge", "source", "speciesId", "traitId", "details"} <= set(r)


def test_pure_module_returns_empty_without_a_race():
    assert species_resources.resources(None, None, None, None, None, 5, 3, {}, 30) == []


def test_wiring_removed_gives_no_resources(catalog, monkeypatch):
    monkeypatch.setattr(ref, "SPECIES_RESOURCES", {})
    assert _res(catalog, "dragonborn-xphb", 5)["derived"]["speciesResources"] == []


# ---------------------------------------------------------------- exports

def test_extra_blocks_list_species_resources(catalog):
    blocks = export_fields.extra_blocks(_res(catalog, "dragonborn-xphb", 5, variant="dragonborn-blue"))
    idx = blocks.index(("h2", "Ресурси от расата"))
    lines = [t for kind, t in blocks[idx + 1:] if kind == "bullet"]
    assert any("Breath Weapon" in l and "2d10" in l for l in lines)
