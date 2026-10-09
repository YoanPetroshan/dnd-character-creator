"""Slice 3 (official race conversion gaps): ability scores for nameless
subraces / VRGR lineages / `amount` choices / subrace choose-entries,
darkvision -> senses, speed dict with subrace override, resist choices."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

SOURCES = ["srd", "phb", "mpmm", "tce", "scag", "erlw", "mtf", "xphb", "ftd", "egw", "vgm", "psk"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, **overrides):
    draft = {
        "name": "T", "sources": SOURCES,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": species,
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    draft.update(overrides)
    return draft


def _run(catalog, species_id, sub=None, choices=None):
    sp = {"id": species_id, "choices": choices or {}}
    if sub:
        sp["subspeciesId"] = sub
    return resolve(_draft(sp), catalog)


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


# --- nameless subraces merge into the parent race -------------------------

def test_phb_human_gets_plus_one_to_every_ability(catalog):
    r = _run(catalog, "human-phb")
    assert r["sheet"]["abilities"] == {a: 11 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}
    assert r["problems"] == []


def test_nameless_subraces_are_not_in_the_subrace_list(catalog):
    assert not [s for s in catalog.subraces_of("human-phb") if not s.get("name")]


def test_variant_human_replaces_the_default_plus_one_all(catalog):
    r = _run(catalog, "human-phb", "human-phb-variant-phb")
    assert r["sheet"]["abilities"]["STR"] == 10  # not +1 across the board
    ch = _choice(r, "species:human-phb:ability-bonus")
    assert ch["count"] == 2 and ch["status"] == "pending"
    r = _run(catalog, "human-phb", "human-phb-variant-phb",
             {"species:human-phb:ability-bonus": ["str", "dex"]})
    ab = r["sheet"]["abilities"]
    assert (ab["STR"], ab["DEX"], ab["CON"]) == (11, 11, 10)


# --- VRGR lineage ---------------------------------------------------------

def test_vrgr_lineage_offers_plus2_plus1_or_three_plus1(catalog):
    r = _run(catalog, "aarakocra-mpmm")
    ch = _choice(r, "species:aarakocra-mpmm:ability-bonus")
    assert ch and ch["status"] == "pending" and ch["count"] == 1
    ids = {o["id"] for o in ch["options"]}
    assert len(ids) == 30 + 20  # 6*5 ordered +2/+1 pairs, C(6,3) triples
    assert "str-2+dex-1" in ids and "str-1+dex-1+con-1" in ids
    assert r["sheet"]["abilities"]["STR"] == 10


def test_vrgr_selection_is_applied(catalog):
    r = _run(catalog, "aarakocra-mpmm", choices={"species:aarakocra-mpmm:ability-bonus": ["str-2+dex-1"]})
    assert (r["sheet"]["abilities"]["STR"], r["sheet"]["abilities"]["DEX"]) == (12, 11)
    r = _run(catalog, "goblin-mpmm", choices={"species:goblin-mpmm:ability-bonus": ["int-1+wis-1+cha-1"]})
    ab = r["sheet"]["abilities"]
    assert (ab["INT"], ab["WIS"], ab["CHA"], ab["STR"]) == (11, 11, 11, 10)


# --- `amount` choices -----------------------------------------------------

def test_custom_lineage_is_plus_two_to_one_ability(catalog):
    r = _run(catalog, "custom-lineage-tce")
    ch = _choice(r, "species:custom-lineage-tce:ability-bonus")
    assert ch["count"] == 1 and {o["id"] for o in ch["options"]} == {"str", "dex", "con", "int", "wis", "cha"}
    r = _run(catalog, "custom-lineage-tce", choices={"species:custom-lineage-tce:ability-bonus": ["con"]})
    assert r["sheet"]["abilities"]["CON"] == 12


# --- subrace choose entries / overwrite -----------------------------------

def test_subrace_choose_entry_adds_to_fixed_bonus_and_replaces_race_ability(catalog):
    sub = "human-phb-mark-of-handling-erlw"  # wis +2, choose 1 of the other five
    r = _run(catalog, "human-phb", sub, {"species:human-phb:ability-bonus": ["str"]})
    ab = r["sheet"]["abilities"]
    assert (ab["WIS"], ab["STR"], ab["DEX"]) == (12, 11, 10)
    assert _choice(r, "species:human-phb:ability-bonus")["status"] == "resolved"


def test_tiefling_variant_amount_two_choice(catalog):
    sub = "tiefling-phb-variant;-infernal-legacy-scag"  # int +1, dex OR cha +2; replaces cha+2/int+1
    r = _run(catalog, "tiefling-phb", sub, {"species:tiefling-phb:ability-bonus": ["dex"]})
    ab = r["sheet"]["abilities"]
    assert (ab["INT"], ab["DEX"], ab["CHA"]) == (11, 12, 10)


def test_subrace_overwrite_ability_replaces_race_bonuses(catalog):
    r = _run(catalog, "dragonborn-phb", "dragonborn-phb-draconblood-egw")  # int +2 cha +1 instead of str+2
    ab = r["sheet"]["abilities"]
    assert (ab["STR"], ab["INT"], ab["CHA"]) == (10, 12, 11)


def test_ordinary_subrace_still_stacks_on_race(catalog):
    r = _run(catalog, "elf-phb", "elf-phb-high-phb")
    ab = r["sheet"]["abilities"]
    assert (ab["DEX"], ab["INT"]) == (12, 11)


# --- darkvision -> senses -------------------------------------------------

def test_official_race_darkvision_reaches_senses(catalog):
    assert _run(catalog, "aasimar-vgm")["sheet"]["senses"] == {"darkvision": 60}


def test_subrace_darkvision_higher_range_wins(catalog):
    assert _run(catalog, "elf-phb", "elf-phb-drow-phb")["sheet"]["senses"] == {"darkvision": 120}


def test_srd_darkvision_trait_reaches_senses(catalog):
    assert _run(catalog, "dwarf")["sheet"]["senses"] == {"darkvision": 60}
    assert _run(catalog, "human")["sheet"]["senses"] == {}


# --- speed ----------------------------------------------------------------

def test_subrace_speed_overrides_race_walk(catalog):
    r = _run(catalog, "elf-phb", "elf-phb-wood-phb")
    assert r["derived"]["speed"] == 35
    assert r["derived"]["speeds"] == {"walk": 35}


def test_non_walk_speeds_are_kept(catalog):
    r = _run(catalog, "elf-phb", "elf-phb-sea-mtf")
    assert r["derived"]["speed"] == 30
    assert r["derived"]["speeds"] == {"walk": 30, "swim": 30}


def test_true_movement_flag_means_walk_speed(catalog):
    sp = next(k for k, v in catalog.races.items()
              if isinstance(v.get("movement"), dict) and v["movement"].get("swim") is True)
    r = resolve(_draft({"id": sp, "choices": {}}, sources=[catalog.races[sp]["source"].lower()]), catalog)
    assert r["derived"]["speeds"]["swim"] == r["derived"]["speeds"]["walk"]


def test_srd_race_speed_unchanged(catalog):
    r = _run(catalog, "dwarf")
    assert r["derived"]["speed"] == 25 and r["derived"]["speeds"] == {"walk": 25}


# --- resist choices -------------------------------------------------------

def test_dragonborn_resist_choice_is_offered_and_applied(catalog):
    r = _run(catalog, "dragonborn-phb")
    ch = _choice(r, "species:dragonborn-phb:resistance")
    assert ch["status"] == "pending" and ch["count"] == 1
    assert {o["id"] for o in ch["options"]} == {"acid", "cold", "fire", "lightning", "poison"}
    assert r["sheet"]["damageModifiers"]["resistances"] == []
    r = _run(catalog, "dragonborn-phb", choices={"species:dragonborn-phb:resistance": ["cold"]})
    assert r["sheet"]["damageModifiers"]["resistances"] == ["cold"]


def test_xphb_tiefling_resistance_is_decided_by_the_legacy_variant(catalog):
    # Slice 8b: the three legacies fix the resistance, so the converted
    # `resist_options` (poison/necrotic/fire) no longer becomes its own choice.
    assert catalog.races["tiefling-xphb"]["resist_options"] is not None
    r = _run(catalog, "tiefling-xphb")
    assert _choice(r, "species:tiefling-xphb:resistance") is None
    assert {o["id"] for o in _choice(r, "species:tiefling-xphb:variant")["options"]} == {
        "abyssal-legacy", "chthonic-legacy", "infernal-legacy"}